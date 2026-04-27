"""Tests for the cascade orchestrator — fixplan_v3 sub-fix 1F §0.7."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Mapping

import pytest

from lia_graph.pipeline_d.vigencia_cascade import (
    CascadeQueueEntry,
    InconsistencyReport,
    NormVigenciaHistoryRow,
    VigenciaCascadeOrchestrator,
)


# ---------------------------------------------------------------------------
# Fake Supabase client (cascade-shaped subset)
# ---------------------------------------------------------------------------


@dataclass
class _Resp:
    data: list[dict[str, Any]] = field(default_factory=list)


class _Q:
    def __init__(self, table: "_T") -> None:
        self._t = table
        self._select = "*"
        self._filters: list[Any] = []

    def select(self, columns: str) -> "_Q":
        self._select = columns
        return self

    def eq(self, col: str, val: Any) -> "_Q":
        self._filters.append(("eq", col, val))
        return self

    def is_(self, col: str, val: Any) -> "_Q":
        self._filters.append(("is", col, val))
        return self

    def order(self, *args: Any, **kw: Any) -> "_Q":
        return self

    def limit(self, n: int) -> "_Q":
        return self

    def execute(self) -> _Resp:
        out = []
        for r in self._t.rows:
            keep = True
            for kind, col, val in self._filters:
                if kind == "eq" and r.get(col) != val:
                    keep = False
                if kind == "is" and val == "null" and r.get(col) is not None:
                    keep = False
            if keep:
                out.append(dict(r))
        return _Resp(data=out)


class _T:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def select(self, *args: Any, **kw: Any) -> _Q:
        return _Q(self)

    def insert(self, payload: Any) -> "_Insert":
        if isinstance(payload, list):
            return _Insert(self, payload)
        return _Insert(self, [payload])

    def update(self, payload: Any) -> "_Update":
        return _Update(self, payload)


class _Insert:
    def __init__(self, t: _T, rows: list[dict[str, Any]]) -> None:
        self._t = t
        self._rows = rows

    def execute(self) -> _Resp:
        for row in self._rows:
            row = dict(row)
            row.setdefault("queue_id", str(uuid.uuid4()))
            self._t.rows.append(row)
        return _Resp(data=list(self._rows))


class _Update:
    def __init__(self, t: _T, payload: Any) -> None:
        self._t = t
        self._payload = payload
        self._filters: list[Any] = []

    def eq(self, col: str, val: Any) -> "_Update":
        self._filters.append((col, val))
        return self

    def execute(self) -> _Resp:
        for row in self._t.rows:
            keep = True
            for col, val in self._filters:
                if row.get(col) != val:
                    keep = False
                    break
            if keep:
                row.update(self._payload)
        return _Resp()


class _Client:
    def __init__(self) -> None:
        self.tables: dict[str, _T] = defaultdict(_T)

    def table(self, name: str) -> _T:
        return self.tables[name]


@pytest.fixture
def client() -> _Client:
    return _Client()


@pytest.fixture
def orchestrator(client: _Client) -> VigenciaCascadeOrchestrator:
    return VigenciaCascadeOrchestrator(client)


# ---------------------------------------------------------------------------
# Reviviscencia handler
# ---------------------------------------------------------------------------


def _seed_history(client: _Client) -> None:
    """Seed three norms previously modified by Ley 1943/2018."""

    rows = [
        {
            "record_id": str(uuid.uuid4()),
            "norm_id": f"et.art.{n}",
            "state": "VM",
            "state_from": "2019-01-01",
            "state_until": None,
            "change_source": {
                "type": "reforma",
                "source_norm_id": "ley.1943.2018",
                "effect_type": "pro_futuro",
                "effect_payload": {},
            },
            "extracted_by": "ingest@v1",
            "extracted_at": "2019-01-15T00:00:00Z",
        }
        for n in (240, 245, 246)
    ]
    client.table("norm_vigencia_history").rows.extend(rows)


def test_reviviscencia_cascade_enqueues_affected_norms(client, orchestrator):
    _seed_history(client)

    new_row = NormVigenciaHistoryRow(
        record_id="rec-c-481",
        norm_id="ley.1943.2018",
        state="IE",
        state_from=date(2019, 10, 3),
        state_until=None,
        change_source={
            "type": "sentencia_cc",
            "source_norm_id": "sent.cc.C-481.2019",
            "effect_type": "pro_futuro",
        },
        extracted_by="cron@v1",
        extracted_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
    )

    result = orchestrator.on_history_row_inserted(new_row)
    queued_norms = {e.norm_id for e in result.queue_entries}
    assert queued_norms == {"et.art.240", "et.art.245", "et.art.246"}
    assert all(e.supersede_reason == "cascade_reviviscencia" for e in result.queue_entries)
    # Persisted to queue table
    queue_rows = client.table("vigencia_reverify_queue").rows
    assert len(queue_rows) == 3


def test_reviviscencia_idempotent(client, orchestrator):
    _seed_history(client)
    new_row = NormVigenciaHistoryRow(
        record_id="rec-c-481",
        norm_id="ley.1943.2018",
        state="IE",
        state_from=date(2019, 10, 3),
        state_until=None,
        change_source={
            "type": "sentencia_cc",
            "source_norm_id": "sent.cc.C-481.2019",
            "effect_type": "pro_futuro",
        },
        extracted_by="cron@v1",
        extracted_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
    )
    r1 = orchestrator.on_history_row_inserted(new_row)
    r2 = orchestrator.on_history_row_inserted(new_row)
    # Both runs return the same set of cascading norms
    norms1 = {e.norm_id for e in r1.queue_entries}
    norms2 = {e.norm_id for e in r2.queue_entries}
    assert norms1 == norms2


def test_non_sentencia_cc_no_cascade(client, orchestrator):
    new_row = NormVigenciaHistoryRow(
        record_id="rec-de",
        norm_id="et.art.158-1",
        state="DE",
        state_from=date(2023, 1, 1),
        state_until=None,
        change_source={
            "type": "derogacion_expresa",
            "source_norm_id": "ley.2277.2022.art.96",
            "effect_type": "pro_futuro",
        },
        extracted_by="ingest@v1",
        extracted_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
    )
    result = orchestrator.on_history_row_inserted(new_row)
    assert result.queued == 0
    assert result.queue_entries == ()


# ---------------------------------------------------------------------------
# Periodic flip notifier
# ---------------------------------------------------------------------------


def test_periodic_tick_notifies_upcoming_state_until(client, orchestrator):
    today = date(2026, 4, 27)
    soon = (today + timedelta(days=15)).isoformat()
    client.table("norm_vigencia_history").rows.extend([
        {
            "record_id": "rec-soon",
            "norm_id": "ley.9999.2026",
            "state": "DI",
            "state_from": "2025-01-01",
            "state_until": soon,
            "change_source": {"type": "sentencia_cc", "source_norm_id": "sent.cc.C-100.2025", "effect_type": "diferido"},
            "extracted_by": "ingest@v1",
            "extracted_at": "2025-01-01T00:00:00Z",
        },
        {
            "record_id": "rec-far",
            "norm_id": "ley.8888.2026",
            "state": "DI",
            "state_from": "2025-01-01",
            "state_until": "2027-12-31",  # outside window
            "change_source": {"type": "sentencia_cc", "source_norm_id": "sent.cc.C-200.2025", "effect_type": "diferido"},
            "extracted_by": "ingest@v1",
            "extracted_at": "2025-01-01T00:00:00Z",
        },
    ])

    result = orchestrator.on_periodic_tick(now=datetime(2026, 4, 27, tzinfo=timezone.utc), flip_window_days=30)
    queued_norms = {e.norm_id for e in result.queue_entries}
    assert "ley.9999.2026" in queued_norms
    assert "ley.8888.2026" not in queued_norms


def test_periodic_tick_notifies_future_dated_state_from(client, orchestrator):
    today = date(2026, 4, 27)
    rige = (today + timedelta(days=20)).isoformat()
    client.table("norm_vigencia_history").rows.extend([
        {
            "record_id": "rec-vl",
            "norm_id": "ley.7777.2026",
            "state": "VL",
            "state_from": rige,
            "state_until": None,
            "change_source": {"type": "vacatio", "source_norm_id": "ley.7777.2026", "effect_type": "pro_futuro"},
            "extracted_by": "ingest@v1",
            "extracted_at": "2026-04-01T00:00:00Z",
        },
    ])

    result = orchestrator.on_periodic_tick(now=datetime(2026, 4, 27, tzinfo=timezone.utc), flip_window_days=30)
    assert any(e.norm_id == "ley.7777.2026" for e in result.queue_entries)


# ---------------------------------------------------------------------------
# Inconsistency detector (read-only)
# ---------------------------------------------------------------------------


def test_inconsistency_detector_flags_divergent_states(orchestrator):
    citations = [
        {"norm_id": "et.art.158-1", "role": "anchor", "anchor_state": "V"},
        {"norm_id": "et.art.158-1", "role": "anchor", "anchor_state": "DE"},
    ]
    report = orchestrator.detect_inconsistency(citations, as_of=date(2026, 4, 27))
    assert report is not None
    assert report.norm_id == "et.art.158-1"
    assert report.fallback_reason == "vigencia_inconsistency"
    assert "DE" in report.detail["states_seen"]


def test_inconsistency_detector_silent_on_consistent_anchors(orchestrator):
    citations = [
        {"norm_id": "et.art.689-3", "role": "anchor", "anchor_state": "VM"},
        {"norm_id": "et.art.689-3", "role": "reference", "anchor_state": "VM"},
    ]
    assert orchestrator.detect_inconsistency(citations, as_of=date(2026, 4, 27)) is None


def test_inconsistency_detector_does_not_write(client, orchestrator):
    citations = [
        {"norm_id": "et.art.158-1", "role": "anchor", "anchor_state": "V"},
        {"norm_id": "et.art.158-1", "role": "anchor", "anchor_state": "DE"},
    ]
    orchestrator.detect_inconsistency(citations, as_of=date(2026, 4, 27))
    # Detector is read-only — no queue rows produced.
    assert client.table("vigencia_reverify_queue").rows == []


# ---------------------------------------------------------------------------
# Public queue_reverify API (used by Fix 3 partial-coverage hook)
# ---------------------------------------------------------------------------


def test_queue_reverify_writes_one_row(client, orchestrator):
    orchestrator.queue_reverify(
        "et.art.689-3",
        reason="partial_coverage_followup",
        triggering_norm_id="et.art.689-3",
    )
    rows = client.table("vigencia_reverify_queue").rows
    assert len(rows) == 1
    assert rows[0]["supersede_reason"] == "partial_coverage_followup"
    assert rows[0]["norm_id"] == "et.art.689-3"
