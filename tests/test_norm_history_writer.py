"""Tests for the norm-history writer — fixplan_v3 sub-fix 1B-γ.

Uses a fake in-memory Supabase client. No live DB required.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping

import pytest

from lia_graph.persistence.norm_history_writer import (
    NormHistoryWriter,
    PreparedHistoryRow,
    WriteResult,
    build_norm_row,
)
from lia_graph.vigencia import (
    AppliesToPayload,
    ChangeSource,
    ChangeSourceType,
    ExtractionAudit,
    InterpretiveConstraint,
    Vigencia,
    VigenciaState,
)


# ---------------------------------------------------------------------------
# Fake Supabase client
# ---------------------------------------------------------------------------


@dataclass
class _FakeResponse:
    data: list[dict[str, Any]] = field(default_factory=list)


class _FakeQuery:
    def __init__(self, table: "_FakeTable") -> None:
        self._table = table
        self._filters: list[tuple[str, str, Any]] = []
        self._select: str | None = None

    def select(self, columns: str) -> "_FakeQuery":
        self._select = columns
        return self

    def eq(self, column: str, value: Any) -> "_FakeQuery":
        self._filters.append(("eq", column, value))
        return self

    def is_(self, column: str, value: Any) -> "_FakeQuery":
        # "null" sentinel from the writer
        self._filters.append(("is", column, value))
        return self

    def execute(self) -> _FakeResponse:
        rows = self._table.rows
        out: list[dict[str, Any]] = []
        for r in rows:
            keep = True
            for kind, col, val in self._filters:
                if kind == "eq":
                    if r.get(col) != val:
                        keep = False
                        break
                elif kind == "is":
                    if val == "null":
                        if r.get(col) is not None:
                            keep = False
                            break
                    else:
                        if r.get(col) != val:
                            keep = False
                            break
            if keep:
                out.append(dict(r))
        return _FakeResponse(data=out)


class _FakeUpsert:
    def __init__(self, table: "_FakeTable", rows: list[dict[str, Any]], on_conflict: str | None) -> None:
        self._table = table
        self._rows = rows
        self._on_conflict = on_conflict

    def execute(self) -> _FakeResponse:
        out: list[dict[str, Any]] = []
        for row in self._rows:
            self._table.upsert_row(row, on_conflict=self._on_conflict)
            out.append(dict(row))
        return _FakeResponse(data=out)


class _FakeInsert:
    def __init__(self, table: "_FakeTable", row: dict[str, Any]) -> None:
        self._table = table
        self._row = dict(row)

    def execute(self) -> _FakeResponse:
        if "record_id" not in self._row:
            self._row["record_id"] = str(uuid.uuid4())
        self._table.rows.append(self._row)
        return _FakeResponse(data=[dict(self._row)])


class _FakeTable:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def upsert(self, payload: Any, on_conflict: str | None = None) -> _FakeUpsert:
        if isinstance(payload, list):
            rows = list(payload)
        else:
            rows = [payload]
        return _FakeUpsert(self, rows, on_conflict)

    def insert(self, row: Mapping[str, Any]) -> _FakeInsert:
        return _FakeInsert(self, dict(row))

    def select(self, columns: str) -> _FakeQuery:
        return _FakeQuery(self).select(columns)

    def upsert_row(self, row: dict[str, Any], *, on_conflict: str | None) -> None:
        if on_conflict:
            for existing in self.rows:
                if existing.get(on_conflict) == row.get(on_conflict):
                    existing.update(row)
                    return
        self.rows.append(dict(row))


class FakeSupabase:
    def __init__(self) -> None:
        self.tables: dict[str, _FakeTable] = defaultdict(_FakeTable)

    def table(self, name: str) -> _FakeTable:
        return self.tables[name]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> FakeSupabase:
    return FakeSupabase()


@pytest.fixture
def writer(client: FakeSupabase) -> NormHistoryWriter:
    return NormHistoryWriter(client)


def _ec_veredicto() -> Vigencia:
    return Vigencia(
        state=VigenciaState.EC,
        state_from=date(2023, 10, 2),
        state_until=None,
        applies_to_kind="per_period",
        applies_to_payload=AppliesToPayload(
            impuesto="renta",
            period_start=date(2023, 1, 1),
            art_338_cp_shift=True,
        ),
        change_source=ChangeSource(
            type=ChangeSourceType.SENTENCIA_CC,
            source_norm_id="sent.cc.C-384.2023",
            effect_type="pro_futuro",
            effect_payload={
                "fecha_sentencia": "2023-10-02",
                "condicionamiento_literal": "EXEQUIBLES, en el entendido que...",
            },
        ),
        interpretive_constraint=InterpretiveConstraint(
            sentencia_norm_id="sent.cc.C-384.2023",
            fecha_sentencia=date(2023, 10, 2),
            texto_literal="EXEQUIBLES, en el entendido que el régimen tarifario...",
            fuente_verificada_directo=True,
        ),
        extraction_audit=ExtractionAudit(
            skill_version="vigencia-checker@2.0",
            model="gemini-2.5-pro",
            run_id="20260501T120000Z",
            method="manual_sme",
        ),
    )


def _v_veredicto() -> Vigencia:
    return Vigencia(
        state=VigenciaState.V,
        state_from=date(2017, 1, 1),
        state_until=None,
        applies_to_kind="always",
        applies_to_payload=AppliesToPayload(),
        change_source=None,
        extraction_audit=ExtractionAudit(
            skill_version="vigencia-checker@2.0",
            run_id="20260501T120000Z",
            method="manual_sme",
        ),
    )


# ---------------------------------------------------------------------------
# build_norm_row
# ---------------------------------------------------------------------------


def test_build_norm_row_for_et_article():
    row = build_norm_row("et.art.689-3")
    assert row["norm_id"] == "et.art.689-3"
    assert row["norm_type"] == "articulo_et"
    assert row["parent_norm_id"] == "et"
    assert row["is_sub_unit"] is False
    assert row["sub_unit_kind"] is None
    assert row["emisor"] == "Congreso"


def test_build_norm_row_for_sub_unit():
    row = build_norm_row("et.art.689-3.par.2")
    assert row["is_sub_unit"] is True
    assert row["sub_unit_kind"] == "parágrafo"
    assert row["parent_norm_id"] == "et.art.689-3"


def test_build_norm_row_for_concepto_dian_numeral():
    row = build_norm_row("concepto.dian.100208192-202.num.20")
    assert row["norm_type"] == "concepto_dian_numeral"
    assert row["parent_norm_id"] == "concepto.dian.100208192-202"
    assert row["emisor"] == "DIAN"


# ---------------------------------------------------------------------------
# upsert_norm — recursive parent walk
# ---------------------------------------------------------------------------


def test_upsert_norm_walks_parents(writer: NormHistoryWriter, client: FakeSupabase):
    written = writer.upsert_norm("et.art.689-3.par.2")
    norms = client.table("norms").rows
    ids = {r["norm_id"] for r in norms}
    assert "et" in ids
    assert "et.art.689-3" in ids
    assert "et.art.689-3.par.2" in ids
    assert written == 3


def test_upsert_norm_idempotent(writer: NormHistoryWriter, client: FakeSupabase):
    writer.upsert_norm("ley.2277.2022.art.96")
    writer.upsert_norm("ley.2277.2022.art.96")
    rows = client.table("norms").rows
    ids = [r["norm_id"] for r in rows]
    # Should still have only one row per norm_id
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# prepare_row + insert_history_row
# ---------------------------------------------------------------------------


def test_prepare_row_for_ec_state(writer: NormHistoryWriter):
    veredicto = _ec_veredicto()
    prepared = writer.prepare_row(
        norm_id="ley.2277.2022.art.11",
        veredicto=veredicto,
        extracted_by="ingest@v1",
        run_id="run-1",
    )
    assert prepared.state == "EC"
    assert prepared.change_source["source_norm_id"] == "sent.cc.C-384.2023"
    assert prepared.interpretive_constraint is not None
    assert "EXEQUIBLES" in prepared.interpretive_constraint["texto_literal"]
    assert prepared.extracted_via["run_id"] == "run-1"


def test_prepare_row_for_v_state_uses_inaugural_change_source(writer: NormHistoryWriter):
    veredicto = _v_veredicto()
    prepared = writer.prepare_row(
        norm_id="et.art.290.num.5",
        veredicto=veredicto,
        extracted_by="manual_sme:alejandro@example.com",
    )
    assert prepared.state == "V"
    assert prepared.change_source["type"] == "inaugural"


def test_prepare_row_rejects_forbidden_extracted_by(writer: NormHistoryWriter):
    veredicto = _v_veredicto()
    with pytest.raises(ValueError, match="forbidden"):
        writer.prepare_row(
            norm_id="et.art.290.num.5",
            veredicto=veredicto,
            extracted_by="synthesis@v1",
        )


def test_prepare_row_rejects_unknown_extracted_by(writer: NormHistoryWriter):
    veredicto = _v_veredicto()
    with pytest.raises(ValueError):
        writer.prepare_row(
            norm_id="et.art.290.num.5",
            veredicto=veredicto,
            extracted_by="ad-hoc@me",
        )


def test_insert_history_row_writes_norms_and_history(
    writer: NormHistoryWriter, client: FakeSupabase
):
    veredicto = _ec_veredicto()
    prepared = writer.prepare_row(
        norm_id="ley.2277.2022.art.11",
        veredicto=veredicto,
        extracted_by="ingest@v1",
        run_id="run-A",
    )
    result = writer.insert_history_row(prepared)
    assert result.history_rows_inserted == 1
    norm_ids = {r["norm_id"] for r in client.table("norms").rows}
    # Both the affected norm + the source sentencia get cataloged
    assert "ley.2277.2022.art.11" in norm_ids
    assert "ley.2277.2022" in norm_ids
    assert "sent.cc.C-384.2023" in norm_ids
    history = client.table("norm_vigencia_history").rows
    assert len(history) == 1
    assert history[0]["state"] == "EC"


def test_bulk_insert_run_idempotent(
    writer: NormHistoryWriter, client: FakeSupabase
):
    veredicto = _ec_veredicto()
    prepared = writer.prepare_row(
        norm_id="ley.2277.2022.art.11",
        veredicto=veredicto,
        extracted_by="ingest@v1",
        run_id="run-X",
    )
    res1 = writer.bulk_insert_run([prepared], run_id="run-X")
    res2 = writer.bulk_insert_run([prepared], run_id="run-X")
    assert res1.history_rows_inserted == 1
    assert res2.history_rows_skipped == 1
    history = client.table("norm_vigencia_history").rows
    assert len(history) == 1


def test_writer_rejects_non_canonical_source_norm_id(writer: NormHistoryWriter):
    bad_cs = ChangeSource(
        type=ChangeSourceType.DEROGACION_EXPRESA,
        source_norm_id="Ley 2277",  # not canonical — missing year
        effect_type="pro_futuro",
        effect_payload={},
    )
    veredicto = Vigencia(
        state=VigenciaState.DE,
        state_from=date(2023, 1, 1),
        state_until=None,
        applies_to_kind="always",
        applies_to_payload=AppliesToPayload(),
        change_source=bad_cs,
    )
    with pytest.raises(ValueError, match="not a canonical norm_id"):
        writer.prepare_row(
            norm_id="et.art.158-1",
            veredicto=veredicto,
            extracted_by="ingest@v1",
        )


# ---------------------------------------------------------------------------
# The 7 fixtures upgrade smoke (v2 → v3)
# ---------------------------------------------------------------------------


def test_seven_fixtures_round_trip_through_writer(writer: NormHistoryWriter, client: FakeSupabase):
    """The 7 Activity 1.5/1.6/1.7 veredictos must land cleanly via the writer.

    This is the smallest 1B-γ smoke per fixplan_v3 §0.11.5.
    """

    seeds = [
        # V — Art. 290 #5 ET
        (
            "et.art.290.num.5",
            _v_veredicto(),
        ),
        # EC — Art. 11 Ley 2277/2022 zonas francas
        (
            "ley.2277.2022.art.11",
            _ec_veredicto(),
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
            ),
        ),
    ]

    rows: list[PreparedHistoryRow] = []
    for norm_id, veredicto in seeds:
        prepared = writer.prepare_row(
            norm_id=norm_id,
            veredicto=veredicto,
            extracted_by="v2_to_v3_upgrade",
            run_id="upgrade-7-fixtures",
        )
        rows.append(prepared)

    result = writer.bulk_insert_run(rows, run_id="upgrade-7-fixtures")
    assert result.history_rows_inserted == len(seeds)
    history = client.table("norm_vigencia_history").rows
    assert len(history) == len(seeds)
    states = {r["state"] for r in history}
    assert states == {"V", "EC", "DE", "IE"}
