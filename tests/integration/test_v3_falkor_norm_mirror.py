"""Live FalkorDB smoke for the v3 (:Norm) mirror — sub-fix 1B-γ §0.3.2.

Uses the project's stdlib raw-socket GraphClient — no redis-py required.

Flow:
  1. Seed local Postgres with norms + history rows via NormHistoryWriter.
  2. Read them back, build the merge Cypher list from
     `scripts/sync_vigencia_to_falkor` helpers.
  3. Execute against an isolated test graph (LIA_REGULATORY_GRAPH_TEST_V3)
     using GraphClient.execute_many — never touches the production graph.
  4. Assert (:Norm) nodes + edges land with the expected shape.

Gate: LIA_INTEGRATION=1 + reachable Falkor at FALKORDB_URL.
"""

from __future__ import annotations

import os
import uuid
from datetime import date

import pytest

pytestmark = pytest.mark.integration


_TEST_GRAPH_NAME = "LIA_REGULATORY_GRAPH_TEST_V3"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _graph_client():
    """Build a GraphClient pointed at the dedicated test graph."""

    from lia_graph.graph.client import GraphClient, GraphClientConfig
    from lia_graph.graph.schema import default_graph_schema

    schema = default_graph_schema()
    cfg = GraphClientConfig.from_env(graph_name=_TEST_GRAPH_NAME)
    return GraphClient(config=cfg, schema=schema)


def _exec_cypher(client, description: str, query: str):
    from lia_graph.graph.client import GraphWriteStatement
    return client.execute(GraphWriteStatement(description=description, query=query))


def _query_rows(client, query: str) -> list:
    """Run a read query and return decoded rows."""

    res = _exec_cypher(client, description="read", query=query)
    return list(res.rows or [])


def _wipe_test_graph(client) -> None:
    try:
        _exec_cypher(client, "wipe", "MATCH (n) DETACH DELETE n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_norm_node_merge_via_sync_helpers():
    """Seed Postgres → call sync helpers → MERGE in Falkor → verify nodes + edges."""

    from tests.integration.test_v3_persistence_e2e import (  # noqa: E402
        _DirectPgClient,
        _pg_connect,
    )
    from lia_graph.persistence.norm_history_writer import NormHistoryWriter
    from lia_graph.vigencia import (
        AppliesToPayload,
        ChangeSource,
        ChangeSourceType,
        ExtractionAudit,
        Vigencia,
        VigenciaState,
    )
    from scripts.sync_vigencia_to_falkor import (  # type: ignore
        _build_norm_merges,
        _build_edge_merges,
    )

    pg = _pg_connect()
    pg_client = _DirectPgClient(pg)
    writer = NormHistoryWriter(pg_client)

    run_id = f"falkor-itest-{uuid.uuid4().hex[:12]}"
    veredicto = Vigencia(
        state=VigenciaState.IE,
        state_from=date(2026, 4, 15),
        state_until=None,
        applies_to_kind="always",
        applies_to_payload=AppliesToPayload(),
        change_source=ChangeSource(
            type=ChangeSourceType.SENTENCIA_CC,
            source_norm_id="sent.cc.C-079.2026",
            effect_type="pro_futuro",
            effect_payload={"fecha_sentencia": "2026-04-15"},
        ),
        extraction_audit=ExtractionAudit(
            skill_version="vigencia-checker@2.0",
            run_id=run_id,
            method="manual_sme",
        ),
    )
    prepared = writer.prepare_row(
        norm_id="decreto.1474.2025",
        veredicto=veredicto,
        extracted_by="manual_sme:falkor-itest@example.com",
        run_id=run_id,
    )
    writer.bulk_insert_run([prepared], run_id=run_id)

    # Read back into the shape the sync helpers expect.
    with pg.cursor() as cur:
        cur.execute(
            "SELECT norm_id, norm_type, display_label, parent_norm_id, "
            "is_sub_unit, sub_unit_kind, emisor, fecha_emision, canonical_url "
            "FROM norms WHERE norm_id IN ('decreto.1474.2025','sent.cc.C-079.2026')"
        )
        cols = [d[0] for d in cur.description]
        norms_rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.execute(
            "SELECT record_id::text AS record_id, norm_id, state, state_from, "
            "state_until, change_source FROM norm_vigencia_history "
            "WHERE extracted_via->>'run_id' = %s",
            (run_id,),
        )
        cols = [d[0] for d in cur.description]
        history_rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    norm_cypher = _build_norm_merges(norms_rows)
    edge_cypher = _build_edge_merges(history_rows)

    # Execute against the test graph
    gc = _graph_client()
    if not gc.config.is_configured:
        pytest.skip("FALKORDB_URL not configured")
    _wipe_test_graph(gc)
    try:
        for i, stmt in enumerate(norm_cypher):
            _exec_cypher(gc, f"merge-norm-{i}", stmt)
        for i, stmt in enumerate(edge_cypher):
            _exec_cypher(gc, f"merge-edge-{i}", stmt)

        node_rows = _query_rows(
            gc, "MATCH (n:Norm) RETURN n.norm_id ORDER BY n.norm_id"
        )
        norm_ids = [_first(row) for row in node_rows]
        assert "decreto.1474.2025" in norm_ids
        assert "sent.cc.C-079.2026" in norm_ids

        edge_rows = _query_rows(
            gc,
            "MATCH (a:Norm {norm_id:'decreto.1474.2025'})-[r:INEXEQUIBLE_BY]->"
            "(b:Norm {norm_id:'sent.cc.C-079.2026'}) "
            "RETURN r.state_from, r.effect_type",
        )
        assert len(edge_rows) >= 1
        first = edge_rows[0]
        assert _at(first, 0) == "2026-04-15"
        assert _at(first, 1) == "pro_futuro"
    finally:
        _wipe_test_graph(gc)
        with pg.cursor() as cur:
            cur.execute(
                "DELETE FROM norm_vigencia_history WHERE extracted_via->>'run_id' = %s",
                (run_id,),
            )
            cur.execute(
                "DELETE FROM norms WHERE norm_id IN "
                "('decreto.1474.2025','sent.cc.C-079.2026')"
            )
        pg.commit()
        pg.close()


def test_sub_unit_emits_is_sub_unit_of_edge():
    """Sub-unit norm gets an IS_SUB_UNIT_OF edge to its parent."""

    from tests.integration.test_v3_persistence_e2e import (  # noqa: E402
        _DirectPgClient,
        _pg_connect,
    )
    from lia_graph.persistence.norm_history_writer import NormHistoryWriter
    from scripts.sync_vigencia_to_falkor import _build_norm_merges  # type: ignore

    pg = _pg_connect()
    pg_client = _DirectPgClient(pg)
    run_id = f"falkor-subunit-{uuid.uuid4().hex[:12]}"
    NormHistoryWriter(pg_client).upsert_norm("et.art.689-3.par.2", notes=run_id)

    with pg.cursor() as cur:
        cur.execute(
            "SELECT norm_id, norm_type, display_label, parent_norm_id, "
            "is_sub_unit, sub_unit_kind, emisor, fecha_emision, canonical_url "
            "FROM norms WHERE norm_id IN "
            "('et','et.art.689-3','et.art.689-3.par.2')"
        )
        cols = [d[0] for d in cur.description]
        norms_rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    cypher_list = _build_norm_merges(norms_rows)
    gc = _graph_client()
    if not gc.config.is_configured:
        pytest.skip("FALKORDB_URL not configured")
    _wipe_test_graph(gc)
    try:
        for i, stmt in enumerate(cypher_list):
            _exec_cypher(gc, f"merge-{i}", stmt)
        rows = _query_rows(
            gc,
            "MATCH (a:Norm {norm_id:'et.art.689-3.par.2'})-[:IS_SUB_UNIT_OF]->"
            "(b:Norm {norm_id:'et.art.689-3'}) RETURN a.norm_id, b.norm_id",
        )
        assert len(rows) == 1
        assert _at(rows[0], 0) == "et.art.689-3.par.2"
        assert _at(rows[0], 1) == "et.art.689-3"
    finally:
        _wipe_test_graph(gc)
        with pg.cursor() as cur:
            cur.execute(
                "DELETE FROM norms WHERE norm_id IN "
                "('et.art.689-3.par.2','et.art.689-3','et')"
            )
        pg.commit()
        pg.close()


# ---------------------------------------------------------------------------
# Result-row helpers (Falkor returns rows of dicts OR lists depending on version)
# ---------------------------------------------------------------------------


def _at(row, index):
    if isinstance(row, dict):
        # Falkor Python dict shape: {'col': val}
        keys = list(row.keys())
        return row[keys[index]] if index < len(keys) else None
    return row[index] if index < len(row) else None


def _first(row):
    return _at(row, 0)
