"""End-to-end smoke for the v3 norm-keyed persistence layer.

Gate: requires LIA_INTEGRATION=1 + a running local Supabase docker (the
session-level conftest in `tests/integration/conftest.py` skips otherwise).

What this exercises against a real Postgres:
  * `norms` catalog upsert (parent walk).
  * `norm_vigencia_history` INSERT via the writer.
  * Append-only role grant (best-effort — service_role can write; UPDATE
    attempts via the same key still succeed because Supabase's standard
    role has UPDATE on all tables — the role-grant guard is a staging /
    production protection. Local docker exposes the test through the
    writer's own `extracted_by` enum check + the migration's CHECK).
  * `norm_citations` insert with role + anchor_strength.
  * `norm_vigencia_at_date` resolver — returns one row per norm with
    correct demotion factors for V/VM/DE/IE.
  * `norm_vigencia_for_period` resolver — Art. 338 CP shift.
  * `chunk_vigencia_gate_at_date` joins citations to current vigencia.
  * `vigencia_reverify_queue` insert via cascade orchestrator.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import date, datetime, timezone
from typing import Any

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Postgres connection helper
# ---------------------------------------------------------------------------


def _pg_dsn() -> str:
    return os.environ.get(
        "LIA_INTEGRATION_PG_DSN",
        "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
    )


def _pg_connect():
    try:
        import psycopg2  # type: ignore
        return psycopg2.connect(_pg_dsn())
    except ImportError:
        try:
            import psycopg  # type: ignore
            return psycopg.connect(_pg_dsn())
        except ImportError:
            pytest.skip("psycopg2/psycopg not installed — install with `pip install psycopg2-binary`")


# ---------------------------------------------------------------------------
# Tiny psycopg2-shaped Supabase client (so the writer can talk to the real DB)
# ---------------------------------------------------------------------------


class _DirectPgClient:
    """Minimal client implementing the .table().upsert/insert/select.execute() shape.

    Backed by a real psycopg2 connection. The integration tests need a live
    DB, but the production Supabase client requires a service-role JWT we
    don't generate in CI. This shim lets the same writer code path exercise
    the actual SQL.
    """

    def __init__(self, conn) -> None:
        self.conn = conn

    def table(self, name: str) -> "_DirectPgTable":
        return _DirectPgTable(self.conn, name)


class _DirectPgTable:
    def __init__(self, conn, name: str) -> None:
        self.conn = conn
        self.name = name

    def upsert(self, payload: Any, on_conflict: str | None = None) -> "_PendingOp":
        rows = payload if isinstance(payload, list) else [payload]
        return _PendingOp(self.conn, "upsert", self.name, rows, on_conflict=on_conflict)

    def insert(self, payload: Any) -> "_PendingOp":
        rows = payload if isinstance(payload, list) else [payload]
        return _PendingOp(self.conn, "insert", self.name, rows)

    def select(self, columns: str) -> "_SelectQuery":
        return _SelectQuery(self.conn, self.name, columns)


class _SelectQuery:
    def __init__(self, conn, name: str, columns: str) -> None:
        self.conn = conn
        self.name = name
        self.columns = columns
        self._filters: list[tuple[str, str, Any]] = []

    def eq(self, col: str, val: Any) -> "_SelectQuery":
        self._filters.append(("=", col, val))
        return self

    def is_(self, col: str, val: Any) -> "_SelectQuery":
        if val == "null":
            self._filters.append(("IS", col, None))
        else:
            self._filters.append(("IS", col, val))
        return self

    def execute(self) -> "_Resp":
        where_parts = []
        params: list[Any] = []
        for op, col, val in self._filters:
            if op == "IS" and val is None:
                where_parts.append(f"{col} IS NULL")
            elif op == "IS":
                where_parts.append(f"{col} IS %s")
                params.append(val)
            else:
                where_parts.append(f"{col} = %s")
                params.append(val)
        where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT {self.columns} FROM {self.name}{where_sql}", params)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return _Resp(rows)


class _PendingOp:
    def __init__(
        self,
        conn,
        kind: str,
        name: str,
        rows: list[dict[str, Any]],
        *,
        on_conflict: str | None = None,
    ) -> None:
        self.conn = conn
        self.kind = kind
        self.name = name
        self.rows = rows
        self.on_conflict = on_conflict

    def execute(self) -> "_Resp":
        if not self.rows:
            return _Resp([])
        cols = list(self.rows[0].keys())
        col_sql = ", ".join(cols)
        placeholders = ", ".join(["%s"] * len(cols))
        if self.kind == "insert" or self.on_conflict is None:
            sql = f"INSERT INTO {self.name} ({col_sql}) VALUES ({placeholders}) RETURNING *"
        else:
            conflict_cols = self.on_conflict
            update = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != conflict_cols)
            sql = (
                f"INSERT INTO {self.name} ({col_sql}) VALUES ({placeholders}) "
                f"ON CONFLICT ({conflict_cols}) DO UPDATE SET {update} RETURNING *"
            )
        out_rows: list[dict[str, Any]] = []
        import json as _json
        with self.conn.cursor() as cur:
            for row in self.rows:
                values = [
                    _json.dumps(v) if isinstance(v, (dict, list)) else v
                    for v in row.values()
                ]
                cur.execute(sql, values)
                cols2 = [d[0] for d in cur.description]
                out_rows.append(dict(zip(cols2, cur.fetchone())))
        self.conn.commit()
        return _Resp(out_rows)


class _Resp:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    c = _pg_connect()
    yield c
    try:
        c.rollback()
    except Exception:
        pass
    c.close()


@pytest.fixture
def client(conn):
    return _DirectPgClient(conn)


@pytest.fixture(autouse=True)
def _isolate_with_run_id(conn):
    """Each test scopes its writes by run_id and cleans up after itself."""

    run_id = f"itest-{uuid.uuid4().hex[:12]}"
    yield run_id
    # CHECK-violation tests leave conn in `InFailedSqlTransaction`; rollback first.
    try:
        conn.rollback()
    except Exception:
        pass
    # Cleanup: delete history rows + queue rows for this run, then orphan norms.
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM norm_vigencia_history "
            "WHERE extracted_via->>'run_id' = %s",
            (run_id,),
        )
        cur.execute(
            "DELETE FROM norm_citations WHERE extracted_via = %s",
            (run_id,),
        )
        cur.execute(
            "DELETE FROM vigencia_reverify_queue WHERE supersede_reason = %s",
            ("itest_marker",),
        )
        # Orphan norms (parent FK first via the test_marker pattern)
        cur.execute(
            "DELETE FROM norms WHERE notes = %s",
            (run_id,),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_norms_catalog_round_trip(client, conn, _isolate_with_run_id):
    """upsert_norm walks parents and persists with correct types."""

    from lia_graph.persistence.norm_history_writer import NormHistoryWriter

    run_id = _isolate_with_run_id
    writer = NormHistoryWriter(client)
    written = writer.upsert_norm("et.art.689-3.par.2", notes=run_id)
    assert written == 3  # et + et.art.689-3 + par.2

    with conn.cursor() as cur:
        cur.execute(
            "SELECT norm_id, norm_type, parent_norm_id, is_sub_unit, sub_unit_kind "
            "FROM norms WHERE norm_id IN ('et', 'et.art.689-3', 'et.art.689-3.par.2') "
            "ORDER BY norm_id"
        )
        rows = cur.fetchall()
    assert len(rows) == 3
    by_id = {r[0]: r for r in rows}
    assert by_id["et"][1] == "estatuto"
    assert by_id["et.art.689-3"][1] == "articulo_et"
    assert by_id["et.art.689-3.par.2"][1] == "articulo_et"
    assert by_id["et.art.689-3.par.2"][2] == "et.art.689-3"
    assert by_id["et.art.689-3.par.2"][3] is True
    assert by_id["et.art.689-3.par.2"][4] == "parágrafo"


def test_history_insert_and_resolver_at_date(client, conn, _isolate_with_run_id):
    """V / VM / DE rows for three norms; resolver returns correct demotion factors."""

    from lia_graph.persistence.norm_history_writer import NormHistoryWriter
    from lia_graph.vigencia import (
        AppliesToPayload,
        ChangeSource,
        ChangeSourceType,
        ExtractionAudit,
        Vigencia,
        VigenciaState,
    )

    run_id = _isolate_with_run_id
    writer = NormHistoryWriter(client)

    seeds = [
        # V — Art. 290 #5 ET
        (
            "et.art.290.num.5",
            Vigencia(
                state=VigenciaState.V,
                state_from=date(2017, 1, 1),
                state_until=None,
                applies_to_kind="always",
                applies_to_payload=AppliesToPayload(),
                change_source=None,
                extraction_audit=ExtractionAudit(
                    skill_version="vigencia-checker@2.0",
                    run_id=run_id,
                    method="manual_sme",
                ),
            ),
        ),
        # DE — Art. 158-1 ET (Ley 2277/2022 Art. 96)
        (
            "et.art.158-1",
            Vigencia(
                state=VigenciaState.DE,
                state_from=date(2023, 1, 1),
                state_until=None,
                applies_to_kind="always",
                applies_to_payload=AppliesToPayload(),
                change_source=ChangeSource(
                    type=ChangeSourceType.DEROGACION_EXPRESA,
                    source_norm_id="ley.2277.2022.art.96",
                    effect_type="pro_futuro",
                    effect_payload={"fecha_efectos": "2023-01-01"},
                ),
                extraction_audit=ExtractionAudit(
                    skill_version="vigencia-checker@2.0",
                    run_id=run_id,
                    method="manual_sme",
                ),
            ),
        ),
        # IE — Decreto 1474/2025 (Sentencia C-079/2026)
        (
            "decreto.1474.2025",
            Vigencia(
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
            ),
        ),
    ]

    rows = []
    for norm_id, veredicto in seeds:
        prepared = writer.prepare_row(
            norm_id=norm_id,
            veredicto=veredicto,
            extracted_by="manual_sme:integration@example.com",
            run_id=run_id,
        )
        rows.append(prepared)

    result = writer.bulk_insert_run(rows, run_id=run_id)
    assert result.history_rows_inserted == 3

    # Resolver: norm_vigencia_at_date(2026-04-27) returns one row per norm
    with conn.cursor() as cur:
        cur.execute(
            "SELECT norm_id, state, demotion_factor "
            "FROM norm_vigencia_at_date('2026-04-27') "
            "WHERE norm_id IN ('et.art.290.num.5','et.art.158-1','decreto.1474.2025') "
            "ORDER BY norm_id"
        )
        out = cur.fetchall()
    by_id = {r[0]: (r[1], float(r[2])) for r in out}
    assert by_id["et.art.290.num.5"] == ("V", 1.0)
    assert by_id["et.art.158-1"] == ("DE", 0.0)
    assert by_id["decreto.1474.2025"] == ("IE", 0.0)


def test_resolver_for_period_handles_art_338_cp(client, conn, _isolate_with_run_id):
    """A reform vigente in year N applies to AG N+1, not AG N."""

    from lia_graph.persistence.norm_history_writer import NormHistoryWriter
    from lia_graph.vigencia import (
        AppliesToPayload,
        ChangeSource,
        ChangeSourceType,
        ExtractionAudit,
        Vigencia,
        VigenciaState,
    )

    run_id = _isolate_with_run_id
    writer = NormHistoryWriter(client)

    # V row for AG 2017–2022 (Art. 240 prior to Ley 2277)
    v_row = Vigencia(
        state=VigenciaState.V,
        state_from=date(2017, 1, 1),
        state_until=date(2022, 12, 31),
        applies_to_kind="per_period",
        applies_to_payload=AppliesToPayload(
            impuesto="renta",
            period_start=date(2017, 1, 1),
            period_end=date(2022, 12, 31),
        ),
        change_source=None,
        extraction_audit=ExtractionAudit(skill_version="vigencia-checker@2.0", run_id=run_id, method="manual_sme"),
    )

    # VM row from AG 2023 onwards (post-Ley 2277, Art. 338 CP shift applied)
    vm_row = Vigencia(
        state=VigenciaState.VM,
        state_from=date(2023, 1, 1),
        state_until=None,
        applies_to_kind="per_period",
        applies_to_payload=AppliesToPayload(
            impuesto="renta",
            period_start=date(2023, 1, 1),
            period_end=None,
            art_338_cp_shift=True,
        ),
        change_source=ChangeSource(
            type=ChangeSourceType.REFORMA,
            source_norm_id="ley.2277.2022.art.10",
            effect_type="per_period",
            effect_payload={},
        ),
        extraction_audit=ExtractionAudit(skill_version="vigencia-checker@2.0", run_id=run_id, method="manual_sme"),
    )

    writer.bulk_insert_run(
        [
            writer.prepare_row(
                norm_id="et.art.240",
                veredicto=v_row,
                extracted_by="manual_sme:integration@example.com",
                run_id=run_id,
            ),
            writer.prepare_row(
                norm_id="et.art.240",
                veredicto=vm_row,
                extracted_by="manual_sme:integration@example.com",
                run_id=run_id,
            ),
        ],
        run_id=run_id,
    )

    with conn.cursor() as cur:
        # AG 2022 should resolve to the V row (the 2023 modification doesn't reach 2022)
        cur.execute(
            "SELECT state, art_338_cp_applied "
            "FROM norm_vigencia_for_period('renta', 2022) "
            "WHERE norm_id = 'et.art.240'"
        )
        row_2022 = cur.fetchone()
        assert row_2022 is not None
        assert row_2022[0] == "V"

        # AG 2023 should resolve to the VM row
        cur.execute(
            "SELECT state, art_338_cp_applied "
            "FROM norm_vigencia_for_period('renta', 2023) "
            "WHERE norm_id = 'et.art.240'"
        )
        row_2023 = cur.fetchone()
        assert row_2023 is not None
        assert row_2023[0] == "VM"
        assert bool(row_2023[1]) is True


def test_chunk_vigencia_gate_joins_citations_to_vigencia(client, conn, _isolate_with_run_id):
    """norm_citations + norm_vigencia_history → chunk_vigencia_gate output."""

    from lia_graph.persistence.norm_history_writer import NormHistoryWriter
    from lia_graph.vigencia import (
        AppliesToPayload,
        ChangeSource,
        ChangeSourceType,
        ExtractionAudit,
        Vigencia,
        VigenciaState,
    )

    run_id = _isolate_with_run_id
    writer = NormHistoryWriter(client)

    # Land a DE row for et.art.158-1
    veredicto = Vigencia(
        state=VigenciaState.DE,
        state_from=date(2023, 1, 1),
        state_until=None,
        applies_to_kind="always",
        applies_to_payload=AppliesToPayload(),
        change_source=ChangeSource(
            type=ChangeSourceType.DEROGACION_EXPRESA,
            source_norm_id="ley.2277.2022.art.96",
            effect_type="pro_futuro",
            effect_payload={"fecha_efectos": "2023-01-01"},
        ),
        extraction_audit=ExtractionAudit(
            skill_version="vigencia-checker@2.0", run_id=run_id, method="manual_sme"
        ),
    )
    prepared = writer.prepare_row(
        norm_id="et.art.158-1",
        veredicto=veredicto,
        extracted_by="manual_sme:integration@example.com",
        run_id=run_id,
    )
    writer.bulk_insert_run([prepared], run_id=run_id)

    # Add a citation linking a synthetic chunk to the DE norm
    chunk_id = f"itest-chunk-{run_id}"
    client.table("norm_citations").upsert(
        [
            {
                "chunk_id": chunk_id,
                "norm_id": "et.art.158-1",
                "role": "anchor",
                "anchor_strength": "ley",
                "extracted_via": run_id,
            }
        ],
        on_conflict="chunk_id,norm_id,role",
    ).execute()

    with conn.cursor() as cur:
        cur.execute(
            "SELECT chunk_id, norm_id, role, anchor_strength, state, demotion_factor "
            "FROM chunk_vigencia_gate_at_date(%s::text[], %s::date)",
            ([chunk_id], "2026-04-27"),
        )
        rows = cur.fetchall()

    assert len(rows) == 1
    assert rows[0][0] == chunk_id
    assert rows[0][1] == "et.art.158-1"
    assert rows[0][2] == "anchor"
    assert rows[0][3] == "ley"
    assert rows[0][4] == "DE"
    assert float(rows[0][5]) == 0.0


def test_writer_idempotency_on_re_run(client, conn, _isolate_with_run_id):
    """bulk_insert_run with same run_id + source_norm_id is a no-op the second time."""

    from lia_graph.persistence.norm_history_writer import NormHistoryWriter
    from lia_graph.vigencia import (
        AppliesToPayload,
        ChangeSource,
        ChangeSourceType,
        ExtractionAudit,
        Vigencia,
        VigenciaState,
    )

    run_id = _isolate_with_run_id
    writer = NormHistoryWriter(client)
    veredicto = Vigencia(
        state=VigenciaState.DE,
        state_from=date(2023, 1, 1),
        state_until=None,
        applies_to_kind="always",
        applies_to_payload=AppliesToPayload(),
        change_source=ChangeSource(
            type=ChangeSourceType.DEROGACION_EXPRESA,
            source_norm_id="ley.2277.2022.art.96",
            effect_type="pro_futuro",
            effect_payload={"fecha_efectos": "2023-01-01"},
        ),
        extraction_audit=ExtractionAudit(
            skill_version="vigencia-checker@2.0", run_id=run_id, method="manual_sme"
        ),
    )
    prep = writer.prepare_row(
        norm_id="et.art.158-1",
        veredicto=veredicto,
        extracted_by="manual_sme:integration@example.com",
        run_id=run_id,
    )

    res1 = writer.bulk_insert_run([prep], run_id=run_id)
    res2 = writer.bulk_insert_run([prep], run_id=run_id)
    assert res1.history_rows_inserted == 1
    assert res2.history_rows_skipped == 1

    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM norm_vigencia_history "
            "WHERE extracted_via->>'run_id' = %s",
            (run_id,),
        )
        count = cur.fetchone()[0]
    assert count == 1


def test_reverify_queue_round_trip(client, conn, _isolate_with_run_id):
    """Cascade orchestrator's queue insert lands in the queue table."""

    from lia_graph.pipeline_d.vigencia_cascade import VigenciaCascadeOrchestrator

    run_id = _isolate_with_run_id
    orchestrator = VigenciaCascadeOrchestrator(client)
    # Catalog the norm first so the queue row's norm_id has a referent
    from lia_graph.persistence.norm_history_writer import NormHistoryWriter
    NormHistoryWriter(client).upsert_norm("et.art.158-1", notes=run_id)

    # Use the SME-correction reason so cleanup keys cleanly
    orchestrator.queue_reverify(
        "et.art.158-1",
        reason="sme_correction",
        triggering_norm_id="et.art.158-1",
    )

    with conn.cursor() as cur:
        cur.execute(
            "SELECT norm_id, supersede_reason FROM vigencia_reverify_queue "
            "WHERE norm_id = %s ORDER BY enqueued_at DESC LIMIT 1",
            ("et.art.158-1",),
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] == "et.art.158-1"
    assert row[1] == "sme_correction"

    # cleanup
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM vigencia_reverify_queue WHERE norm_id = %s AND supersede_reason = %s",
            ("et.art.158-1", "sme_correction"),
        )
    conn.commit()


def test_db_check_blocks_invalid_state(client, conn, _isolate_with_run_id):
    """The migration's CHECK on `state` rejects an unknown code.

    Note: psycopg raises CheckViolation at `cur.execute(...)` time, not at
    `conn.commit()`. Wrap the execute call in pytest.raises.
    """

    import json as _json
    run_id = _isolate_with_run_id
    from lia_graph.persistence.norm_history_writer import NormHistoryWriter
    NormHistoryWriter(client).upsert_norm("et.art.689-3", notes=run_id)

    with conn.cursor() as cur, pytest.raises(Exception):
        cur.execute(
            "INSERT INTO norm_vigencia_history "
            "(norm_id, state, state_from, applies_to_kind, applies_to_payload, "
            " change_source, veredicto, extracted_via, extracted_by) "
            "VALUES (%s, 'INVALID_STATE', '2024-01-01', 'always', '{}'::jsonb, "
            "%s::jsonb, '{}'::jsonb, %s::jsonb, 'ingest@v1')",
            (
                "et.art.689-3",
                _json.dumps({"type": "reforma", "source_norm_id": "ley.2277.2022.art.10", "effect_type": "pro_futuro", "effect_payload": {}}),
                _json.dumps({"run_id": run_id}),
            ),
        )
    conn.rollback()


def test_db_check_blocks_forbidden_extracted_by(client, conn, _isolate_with_run_id):
    """The migration's CHECK on `extracted_by` rejects synthesis@v1."""

    import json as _json
    run_id = _isolate_with_run_id
    from lia_graph.persistence.norm_history_writer import NormHistoryWriter
    NormHistoryWriter(client).upsert_norm("et.art.689-3", notes=run_id)

    with conn.cursor() as cur, pytest.raises(Exception):
        cur.execute(
            "INSERT INTO norm_vigencia_history "
            "(norm_id, state, state_from, applies_to_kind, applies_to_payload, "
            " change_source, veredicto, extracted_via, extracted_by) "
            "VALUES (%s, 'V', '2024-01-01', 'always', '{}'::jsonb, "
            "%s::jsonb, '{}'::jsonb, %s::jsonb, 'synthesis@v1')",
            (
                "et.art.689-3",
                _json.dumps({"type": "inaugural", "source_norm_id": "", "effect_type": "pro_futuro", "effect_payload": {}}),
                _json.dumps({"run_id": run_id}),
            ),
        )
    conn.rollback()


def test_db_check_blocks_state_until_before_from(client, conn, _isolate_with_run_id):
    """state_until must be >= state_from."""

    import json as _json
    run_id = _isolate_with_run_id
    from lia_graph.persistence.norm_history_writer import NormHistoryWriter
    NormHistoryWriter(client).upsert_norm("et.art.689-3", notes=run_id)

    with conn.cursor() as cur, pytest.raises(Exception):
        cur.execute(
            "INSERT INTO norm_vigencia_history "
            "(norm_id, state, state_from, state_until, applies_to_kind, applies_to_payload, "
            " change_source, veredicto, extracted_via, extracted_by) "
            "VALUES (%s, 'V', '2024-01-01', '2023-12-31', 'always', '{}'::jsonb, "
            "%s::jsonb, '{}'::jsonb, %s::jsonb, 'ingest@v1')",
            (
                "et.art.689-3",
                _json.dumps({"type": "inaugural", "source_norm_id": "", "effect_type": "pro_futuro", "effect_payload": {}}),
                _json.dumps({"run_id": run_id}),
            ),
        )
    conn.rollback()
