"""Phase 2c (v6) — FalkorDB bulk-load hardening.

Pins the three contracts that prevent a silent stall from recurring:

1. ``stage_node_batch`` / ``stage_edge_batch`` emit UNWIND statements with
   the expected shape and parameter payload (one round-trip per batch, not
   one per row — the core 50–100× throughput gain).
2. ``stage_indexes_for_merge_labels`` returns one idempotent CREATE INDEX
   per schema label (the O(N) → O(log N) fix for MERGE at scale).
3. ``GraphClientConfig`` carries ``query_timeout_seconds`` + batch sizes,
   resolving from env with sensible defaults.

The actual socket + per-query TIMEOUT behavior can only be validated
end-to-end; we smoke those via the rendered statement's metadata.
"""

from __future__ import annotations

import pytest

from lia_graph.graph.client import (
    GraphClient,
    GraphClientConfig,
    GraphWriteStatement,
)
from lia_graph.graph.schema import EdgeKind, NodeKind, default_graph_schema


# ── Config + defaults ─────────────────────────────────────────────────


def test_config_default_query_timeout_is_30_seconds() -> None:
    cfg = GraphClientConfig()
    assert cfg.query_timeout_seconds == 30.0
    assert cfg.query_timeout_ms == 30_000


def test_config_env_override_query_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FALKORDB_QUERY_TIMEOUT_SECONDS", "45")
    cfg = GraphClientConfig.from_env()
    assert cfg.query_timeout_seconds == 45.0
    assert cfg.query_timeout_ms == 45_000


def test_config_default_batch_sizes() -> None:
    cfg = GraphClientConfig()
    assert cfg.batch_size_nodes == 500
    assert cfg.batch_size_edges == 1000


def test_config_env_override_batch_sizes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FALKORDB_BATCH_NODES", "250")
    monkeypatch.setenv("FALKORDB_BATCH_EDGES", "2000")
    cfg = GraphClientConfig.from_env()
    assert cfg.batch_size_nodes == 250
    assert cfg.batch_size_edges == 2000


def test_config_query_timeout_ms_floor() -> None:
    # query_timeout_seconds=0.05 would be too short to be meaningful;
    # the ms property enforces a 100ms floor regardless.
    cfg = GraphClientConfig(query_timeout_seconds=0.05)
    assert cfg.query_timeout_ms >= 100


# ── Index creation (the MERGE quadratic fix) ──────────────────────────


def test_stage_index_shape() -> None:
    client = GraphClient()
    stmt = client.stage_index(NodeKind.ARTICLE)
    assert "CREATE INDEX" in stmt.query
    assert "ArticleNode" in stmt.query
    assert "article_id" in stmt.query
    assert stmt.parameters == {}


def test_stage_indexes_covers_every_schema_label() -> None:
    client = GraphClient()
    stmts = client.stage_indexes_for_merge_labels()
    schema = default_graph_schema()
    assert len(stmts) == len(schema.node_types)
    # Every label in the schema must have a matching index statement.
    covered_labels = {
        _extract_label(s.query) for s in stmts
    }
    expected_labels = {kind.value for kind in schema.node_types.keys()}
    assert covered_labels == expected_labels


def _extract_label(query: str) -> str:
    # Pull "ArticleNode" out of "CREATE INDEX FOR (n:ArticleNode) ON (n.article_id)"
    start = query.index("(n:") + 3
    end = query.index(")", start)
    return query[start:end]


# ── Batch node writes ────────────────────────────────────────────────


def test_stage_node_batch_shape_and_params() -> None:
    client = GraphClient()
    rows = [
        {"key": "631-5", "properties": {"heading": "Beneficiario final"}},
        {"key": "631-6", "properties": {"heading": "Obligaciones RUB"}},
    ]
    stmt = client.stage_node_batch(NodeKind.ARTICLE, rows)
    # Shape
    assert "UNWIND $rows AS r" in stmt.query
    assert "MERGE (node:ArticleNode {article_id: r.key})" in stmt.query
    assert "SET node += r.properties" in stmt.query
    # Parameters
    assert list(stmt.parameters.keys()) == ["rows"]
    assert stmt.parameters["rows"][0]["key"] == "631-5"
    assert stmt.parameters["rows"][1]["properties"]["heading"] == "Obligaciones RUB"
    # Description has the batch count so logs are readable
    assert "x2" in stmt.description


def test_stage_node_batch_empty_is_noop_shape() -> None:
    client = GraphClient()
    stmt = client.stage_node_batch(NodeKind.ARTICLE, [])
    # An empty batch returns a no-op statement rather than an empty UNWIND
    # (which would be invalid Cypher). Description flags it so it's
    # observable in logs.
    assert "empty" in stmt.description.lower()
    assert "$rows" not in stmt.query


# ── Batch edge writes ────────────────────────────────────────────────


def test_stage_edge_batch_shape_and_params() -> None:
    client = GraphClient()
    rows = [
        {
            "source_key": "631-5",
            "target_key": "beneficiario_final_rub",
            "properties": {"confidence": 1.0},
        },
        {
            "source_key": "658-3",
            "target_key": "beneficiario_final_rub",
            "properties": {"confidence": 0.85},
        },
    ]
    stmt = client.stage_edge_batch(
        edge_kind=EdgeKind.TEMA,
        source_kind=NodeKind.ARTICLE,
        target_kind=NodeKind.TOPIC,
        rows=rows,
    )
    assert "UNWIND $rows AS r" in stmt.query
    assert "MATCH (source:ArticleNode" in stmt.query
    assert "MATCH (target:TopicNode" in stmt.query
    assert "MERGE (source)-[rel:TEMA]->(target)" in stmt.query
    assert stmt.parameters["rows"][0]["source_key"] == "631-5"


def test_stage_edge_batch_empty_is_noop() -> None:
    client = GraphClient()
    stmt = client.stage_edge_batch(
        edge_kind=EdgeKind.TEMA,
        source_kind=NodeKind.ARTICLE,
        target_kind=NodeKind.TOPIC,
        rows=(),
    )
    assert "empty" in stmt.description.lower()


# ── Determinism: batch output is independent of input iteration order ─


def test_node_batch_preserves_input_row_order() -> None:
    client = GraphClient()
    input_keys = ["a", "b", "c", "d", "e"]
    rows = [{"key": k, "properties": {"i": i}} for i, k in enumerate(input_keys)]
    stmt = client.stage_node_batch(NodeKind.ARTICLE, rows)
    assert [r["key"] for r in stmt.parameters["rows"]] == input_keys


# ── Executor injection still works for tests ─────────────────────────


def test_batch_statements_route_through_injected_executor() -> None:
    captured: list[GraphWriteStatement] = []

    def _fake(stmt: GraphWriteStatement, _config: GraphClientConfig):
        captured.append(stmt)
        from lia_graph.graph.client import GraphQueryResult

        return GraphQueryResult(
            description=stmt.description,
            query=stmt.query,
            parameters=stmt.parameters,
            ok=True,
            rows=(),
            stats={"nodes_created": len(stmt.parameters.get("rows") or [])},
        )

    client = GraphClient(executor=_fake)
    rows = [{"key": f"k{i}", "properties": {}} for i in range(10)]
    stmt = client.stage_node_batch(NodeKind.ARTICLE, rows)
    result = client.execute(stmt, strict=True)
    assert result.ok
    assert result.stats["nodes_created"] == 10
    assert len(captured) == 1
