"""Tests for ``lia_graph.ingestion.dangling_store``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from lia_graph.ingestion.dangling_store import (
    DanglingCandidate,
    DanglingStore,
)


@dataclass
class _Execute:
    data: list[dict[str, Any]]


class _Query:
    def __init__(self, parent: "_Table", op: str, payload: Any = None, on_conflict: str | None = None) -> None:
        self._parent = parent
        self._op = op
        self._payload = payload
        self._on_conflict = on_conflict
        self._filters: list[tuple[str, str, Any]] = []
        self._columns: str | None = None

    def select(self, columns: str) -> "_Query":
        self._columns = columns
        return self

    def eq(self, column: str, value: Any) -> "_Query":
        self._filters.append(("eq", column, value))
        return self

    def in_(self, column: str, values: list[Any]) -> "_Query":
        self._filters.append(("in_", column, list(values)))
        return self

    def lt(self, column: str, value: Any) -> "_Query":
        self._filters.append(("lt", column, value))
        return self

    def _matches(self, row: dict[str, Any]) -> bool:
        for op, column, value in self._filters:
            if op == "eq":
                if row.get(column) != value:
                    return False
            elif op == "in_":
                if row.get(column) not in value:
                    return False
            elif op == "lt":
                v = row.get(column)
                if v is None or not (v < value):
                    return False
        return True

    def execute(self) -> _Execute:
        rows = self._parent.rows
        if self._op == "select":
            return _Execute([dict(r) for r in rows if self._matches(r)])
        if self._op == "delete":
            to_delete = [r for r in rows if self._matches(r)]
            for r in to_delete:
                rows.remove(r)
            return _Execute(to_delete)
        if self._op == "upsert":
            for p in self._payload or []:
                key = (p["source_key"], p["target_key"], p["relation"])
                match = next(
                    (r for r in rows if (r["source_key"], r["target_key"], r["relation"]) == key),
                    None,
                )
                if match:
                    match.update(p)
                else:
                    rows.append(dict(p))
            return _Execute([])
        return _Execute([])


class _Table:
    def __init__(self, name: str, rows: list[dict[str, Any]]) -> None:
        self.name = name
        self.rows = rows

    def select(self, columns: str) -> _Query:
        q = _Query(self, "select")
        q.select(columns)
        return q

    def upsert(self, rows: list[dict[str, Any]], on_conflict: str | None = None) -> _Query:
        return _Query(self, "upsert", payload=list(rows), on_conflict=on_conflict)

    def delete(self) -> _Query:
        return _Query(self, "delete")


class _FakeClient:
    def __init__(self, seed: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self._rows: dict[str, list[dict[str, Any]]] = {}
        for name, rows in (seed or {}).items():
            self._rows[name] = [dict(r) for r in rows]

    def table(self, name: str) -> _Table:
        if name not in self._rows:
            self._rows[name] = []
        return _Table(name, self._rows[name])

    def rows(self, name: str) -> list[dict[str, Any]]:
        return self._rows.get(name, [])


TABLE = DanglingStore.TABLE_NAME


# (a) empty load.
def test_empty_load_returns_empty_dict() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    assert store.load_for_target_keys([]) == {}
    # Target keys with no rows also returns empty dict.
    assert store.load_for_target_keys(["nonexistent"]) == {}


# (b) upsert N candidates → N rows; re-upsert same → still N, last_seen advanced.
def test_upsert_is_idempotent_and_advances_last_seen_delta_id() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    candidates = [
        DanglingCandidate(
            source_key="src_a",
            target_key="tgt_x",
            relation="references",
            source_doc_id="doc_1",
            raw_reference="art 10",
        ),
        DanglingCandidate(
            source_key="src_b",
            target_key="tgt_y",
            relation="complements",
        ),
    ]
    n1 = store.upsert_candidates(candidates, delta_id="delta_1")
    assert n1 == 2
    rows = client.rows(TABLE)
    assert len(rows) == 2
    for r in rows:
        assert r["first_seen_delta_id"] == "delta_1"
        assert r["last_seen_delta_id"] == "delta_1"

    # Re-upsert: first_seen preserved, last_seen advanced.
    n2 = store.upsert_candidates(candidates, delta_id="delta_2")
    assert n2 == 2
    rows_after = client.rows(TABLE)
    assert len(rows_after) == 2
    for r in rows_after:
        assert r["first_seen_delta_id"] == "delta_1"
        assert r["last_seen_delta_id"] == "delta_2"


# (c) load_for_target_keys returns only matching rows.
def test_load_for_target_keys_filters() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    store.upsert_candidates(
        [
            DanglingCandidate("s1", "t1", "references"),
            DanglingCandidate("s2", "t2", "references"),
            DanglingCandidate("s3", "t1", "complements"),
        ],
        delta_id="delta_1",
    )
    grouped = store.load_for_target_keys(["t1"])
    assert set(grouped.keys()) == {"t1"}
    assert {r.source_key for r in grouped["t1"]} == {"s1", "s3"}


# (d) delete_promoted removes exactly the named rows.
def test_delete_promoted_removes_exact_rows() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    store.upsert_candidates(
        [
            DanglingCandidate("s1", "t1", "references"),
            DanglingCandidate("s2", "t2", "references"),
        ],
        delta_id="delta_1",
    )
    removed = store.delete_promoted(
        [DanglingCandidate("s1", "t1", "references")]
    )
    assert removed == 1
    remaining = client.rows(TABLE)
    assert len(remaining) == 1
    assert remaining[0]["source_key"] == "s2"


# (e) gc_older_than removes rows with last_seen_delta_id < threshold.
def test_gc_older_than_filters_by_delta_id_threshold() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    # Manually seed rows with explicit last_seen_delta_id values.
    store.upsert_candidates(
        [DanglingCandidate("s_old", "t", "references")],
        delta_id="delta_20260101_000000_aaa",
    )
    store.upsert_candidates(
        [DanglingCandidate("s_new", "t", "references")],
        delta_id="delta_20260422_120000_bbb",
    )
    removed = store.gc_older_than("delta_20260201_000000_000")
    assert removed == 1
    remaining = client.rows(TABLE)
    assert len(remaining) == 1
    assert remaining[0]["source_key"] == "s_new"


# (f) unique-key dedup enforced at upsert time (same key merges, no duplicate rows).
def test_upsert_dedups_on_primary_key() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    payload = [
        DanglingCandidate("s", "t", "references"),
        DanglingCandidate("s", "t", "references", raw_reference="updated"),
    ]
    store.upsert_candidates(payload, delta_id="delta_1")
    rows = client.rows(TABLE)
    # Despite two payload entries with the same PK, we end up with one row.
    assert len(rows) == 1
    assert rows[0]["raw_reference"] == "updated"


# Extra: incomplete candidates are skipped.
def test_upsert_skips_incomplete_candidates() -> None:
    client = _FakeClient()
    store = DanglingStore(client)
    payload = [
        DanglingCandidate("", "t", "references"),
        DanglingCandidate("s", "", "references"),
        DanglingCandidate("s", "t", ""),
        DanglingCandidate("s", "t", "references"),
    ]
    n = store.upsert_candidates(payload, delta_id="delta_1")
    assert n == 1
    rows = client.rows(TABLE)
    assert len(rows) == 1
