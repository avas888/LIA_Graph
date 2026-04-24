"""Tests for ``lia_graph.ingestion.delta_job_store``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from lia_graph.ingestion import delta_job_store as store


@dataclass
class _Execute:
    data: list[dict[str, Any]]


class _Query:
    def __init__(self, parent: "_Table", op: str, payload: Any = None) -> None:
        self._parent = parent
        self._op = op
        self._payload = payload
        self._filters: list[tuple[str, str, Any]] = []
        self._range: tuple[int, int] | None = None

    @property
    def not_(self) -> "_NegatedProxy":
        return _NegatedProxy(self)

    def eq(self, column: str, value: Any) -> "_Query":
        self._filters.append(("eq", column, value))
        return self

    def in_(self, column: str, values: list[Any]) -> "_Query":
        self._filters.append(("in_", column, list(values)))
        return self

    def lt(self, column: str, value: Any) -> "_Query":
        self._filters.append(("lt", column, value))
        return self

    def order(self, column: str) -> "_Query":
        return self

    def limit(self, n: int) -> "_Query":
        self._range = (0, max(0, n - 1))
        return self

    def range(self, start: int, end: int) -> "_Query":
        self._range = (start, end)
        return self

    def _match(self, row: dict[str, Any]) -> bool:
        for op, column, value in self._filters:
            v = row.get(column)
            if op == "eq" and v != value:
                return False
            if op == "in_" and v not in value:
                return False
            if op == "not_in_" and v in value:
                return False
            if op == "lt" and (v is None or not (v < value)):
                return False
        return True

    def execute(self) -> _Execute:
        rows = self._parent.rows
        if self._op == "select":
            out = [dict(r) for r in rows if self._match(r)]
            if self._range is not None:
                s, e = self._range
                out = out[s : e + 1]
            return _Execute(out)
        if self._op == "insert":
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            for payload in payloads:
                target = payload.get("lock_target")
                stage = payload.get("stage", "queued")
                if stage not in store.TERMINAL_STAGES:
                    for existing in rows:
                        if (
                            existing.get("lock_target") == target
                            and existing.get("stage") not in store.TERMINAL_STAGES
                        ):
                            raise RuntimeError(
                                "duplicate key value violates unique constraint "
                                "idx_ingest_delta_jobs_live_target"
                            )
                rows.append(dict(payload))
            return _Execute([])
        if self._op == "update":
            for r in rows:
                if self._match(r):
                    r.update(self._payload or {})
            return _Execute([])
        return _Execute([])


class _NegatedProxy:
    def __init__(self, query: _Query) -> None:
        self._query = query

    def in_(self, column: str, values: list[Any]) -> _Query:
        self._query._filters.append(("not_in_", column, list(values)))
        return self._query


class _Table:
    def __init__(self, name: str, rows: list[dict[str, Any]]) -> None:
        self.name = name
        self.rows = rows

    def select(self, columns: str, count: str | None = None) -> _Query:
        return _Query(self, "select")

    def insert(self, rows: Any) -> _Query:
        return _Query(self, "insert", payload=rows)

    def update(self, payload: dict[str, Any]) -> _Query:
        return _Query(self, "update", payload=dict(payload))


class _FakeClient:
    def __init__(self) -> None:
        self._rows: list[dict[str, Any]] = []

    def table(self, name: str) -> _Table:
        return _Table(name, self._rows)

    @property
    def rows(self) -> list[dict[str, Any]]:
        return self._rows


# (a) create_job writes all columns; get_job round-trips.
def test_create_job_and_get_job_roundtrip() -> None:
    client = _FakeClient()
    row = store.create_job(
        client,
        job_id="job_1",
        lock_target="production",
        stage="queued",
        delta_id="delta_1",
        created_by="admin@lia.dev",
    )
    assert row.job_id == "job_1"
    assert row.stage == "queued"
    assert row.lock_target == "production"
    row2 = store.get_job(client, job_id="job_1")
    assert row2.job_id == "job_1"
    assert row2.created_by == "admin@lia.dev"


# (b) list_live_jobs_by_target excludes terminal-stage rows.
def test_list_live_jobs_excludes_terminal() -> None:
    client = _FakeClient()
    store.create_job(client, job_id="j1", lock_target="production", stage="parsing")
    client._rows.append(
        {"job_id": "j2", "lock_target": "production", "stage": "completed"}
    )
    live = store.list_live_jobs_by_target(client, lock_target="production")
    assert {r.job_id for r in live} == {"j1"}


# (c) request_cancel flips cancel_requested = true.
def test_request_cancel_flips_flag() -> None:
    client = _FakeClient()
    store.create_job(client, job_id="j1", lock_target="production")
    row = store.request_cancel(client, job_id="j1")
    assert row.cancel_requested is True


# (d) update_stage moves the stage forward and heartbeats.
def test_update_stage_moves_stage() -> None:
    client = _FakeClient()
    store.create_job(client, job_id="j1", lock_target="production")
    row = store.update_stage(client, job_id="j1", stage="supabase", progress_pct=50)
    assert row.stage == "supabase"
    assert row.progress_pct == 50


# (e) Duplicate live target raises the partial-unique-index violation.
def test_duplicate_live_target_raises() -> None:
    client = _FakeClient()
    store.create_job(client, job_id="j1", lock_target="production")
    with pytest.raises(RuntimeError) as exc_info:
        store.create_job(client, job_id="j2", lock_target="production")
    assert "idx_ingest_delta_jobs_live_target" in str(exc_info.value)


# (f) finalize transitions to a terminal stage and records error fields.
def test_finalize_records_terminal_state_and_error() -> None:
    client = _FakeClient()
    store.create_job(client, job_id="j1", lock_target="production")
    row = store.finalize(
        client,
        job_id="j1",
        stage="failed",
        error_class="ValueError",
        error_message="boom",
    )
    assert row.is_terminal()
    assert row.stage == "failed"
    assert row.error_class == "ValueError"
    assert row.error_message == "boom"
