"""Tests for ``lia_graph.ingestion.baseline_snapshot``.

Fake-client-based; no live Supabase required.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lia_graph.ingestion.baseline_snapshot import (
    BaselineSnapshot,
    DEFAULT_GENERATION_ID,
    load_baseline_snapshot,
)


@dataclass
class _Execute:
    data: list[dict[str, Any]]
    count: int | None = None


class _Query:
    def __init__(
        self,
        parent: "_Table",
        op: str,
        columns: str | None = None,
        count: str | None = None,
    ) -> None:
        self._parent = parent
        self._op = op
        self._columns = columns
        self._count = count
        self._filters: list[tuple[str, str, Any]] = []
        self._order: str | None = None
        self._range: tuple[int, int] | None = None

    def eq(self, column: str, value: Any) -> "_Query":
        self._filters.append(("eq", column, value))
        return self

    def order(self, column: str) -> "_Query":
        self._order = column
        return self

    def range(self, start: int, end: int) -> "_Query":
        self._range = (start, end)
        return self

    def execute(self) -> _Execute:
        rows = list(self._parent.rows)
        for op, column, value in self._filters:
            if op == "eq":
                rows = [r for r in rows if r.get(column) == value]
        if self._order:
            rows.sort(key=lambda r: str(r.get(self._order or "", "")))
        full_count = len(rows)
        if self._range is not None:
            start, end = self._range
            rows = rows[start : end + 1]
        return _Execute(
            data=rows,
            count=full_count if self._count == "exact" else None,
        )


class _Table:
    def __init__(self, name: str, rows: list[dict[str, Any]]) -> None:
        self.name = name
        self.rows = rows

    def select(self, columns: str, count: str | None = None) -> _Query:
        return _Query(self, "select", columns=columns, count=count)


class _FakeClient:
    def __init__(self, seed: dict[str, list[dict[str, Any]]]) -> None:
        self._rows = {k: list(v) for k, v in seed.items()}

    def table(self, name: str) -> _Table:
        if name not in self._rows:
            self._rows[name] = []
        return _Table(name, self._rows[name])


def _doc(
    *,
    doc_id: str,
    relative_path: str,
    sync_generation: str = DEFAULT_GENERATION_ID,
    content_hash: str = "h1",
    doc_fingerprint: str | None = "fp1",
    retired_at: str | None = None,
    last_delta_id: str | None = None,
) -> dict[str, Any]:
    return {
        "doc_id": doc_id,
        "relative_path": relative_path,
        "content_hash": content_hash,
        "doc_fingerprint": doc_fingerprint,
        "retired_at": retired_at,
        "last_delta_id": last_delta_id,
        "sync_generation": sync_generation,
    }


# (a) empty DB → empty snapshot.
def test_empty_db_produces_empty_snapshot() -> None:
    client = _FakeClient(seed={})
    snap = load_baseline_snapshot(client)
    assert snap.generation_id == DEFAULT_GENERATION_ID
    assert snap.total_docs == 0
    assert snap.total_chunks == 0
    assert snap.total_edges == 0
    assert snap.is_empty is True


# (b) 3 non-retired docs → 3 snapshot entries.
def test_three_docs_populate_snapshot() -> None:
    client = _FakeClient(
        seed={
            "documents": [
                _doc(doc_id="a", relative_path="normativa/iva/a.md"),
                _doc(doc_id="b", relative_path="normativa/iva/b.md"),
                _doc(doc_id="c", relative_path="normativa/laboral/c.md"),
            ]
        }
    )
    snap = load_baseline_snapshot(client)
    assert snap.total_docs == 3
    assert snap.retired_docs == 0
    assert set(snap.documents_by_relative_path.keys()) == {
        "normativa/iva/a.md",
        "normativa/iva/b.md",
        "normativa/laboral/c.md",
    }
    a = snap.get("normativa/iva/a.md")
    assert a is not None
    assert a.doc_id == "a"
    assert a.doc_fingerprint == "fp1"
    assert a.retired_at is None


# (c) 1 retired doc → entry with retired_at set, still present in snapshot.
def test_retired_doc_still_present() -> None:
    client = _FakeClient(
        seed={
            "documents": [
                _doc(
                    doc_id="gone",
                    relative_path="normativa/iva/gone.md",
                    retired_at="2026-04-22T10:00:00+00:00",
                ),
                _doc(doc_id="live", relative_path="normativa/iva/live.md"),
            ]
        }
    )
    snap = load_baseline_snapshot(client)
    assert snap.total_docs == 2
    assert snap.retired_docs == 1
    gone = snap.get("normativa/iva/gone.md")
    assert gone is not None
    assert gone.retired_at == "2026-04-22T10:00:00+00:00"


# (d) filters by generation_id — does not leak rows from other generations.
def test_generation_id_filter_excludes_other_generations() -> None:
    client = _FakeClient(
        seed={
            "documents": [
                _doc(doc_id="a", relative_path="a.md", sync_generation="gen_active_rolling"),
                _doc(doc_id="b", relative_path="b.md", sync_generation="gen_20260420"),
                _doc(doc_id="c", relative_path="c.md", sync_generation="gen_active_rolling"),
            ]
        }
    )
    snap = load_baseline_snapshot(client, generation_id="gen_active_rolling")
    assert snap.total_docs == 2
    assert set(snap.documents_by_relative_path.keys()) == {"a.md", "c.md"}
    # A different generation_id returns a disjoint snapshot.
    snap_other = load_baseline_snapshot(client, generation_id="gen_20260420")
    assert set(snap_other.documents_by_relative_path.keys()) == {"b.md"}


# (e) aggregate total_docs / total_chunks / total_edges populated.
def test_aggregate_counts_are_populated() -> None:
    client = _FakeClient(
        seed={
            "documents": [
                _doc(doc_id="a", relative_path="a.md"),
                _doc(doc_id="b", relative_path="b.md"),
            ],
            "document_chunks": [
                {"chunk_id": "a::art1", "doc_id": "a", "sync_generation": DEFAULT_GENERATION_ID},
                {"chunk_id": "a::art2", "doc_id": "a", "sync_generation": DEFAULT_GENERATION_ID},
                {"chunk_id": "b::art1", "doc_id": "b", "sync_generation": DEFAULT_GENERATION_ID},
            ],
            "normative_edges": [
                {"id": 1, "source_key": "a::art1", "target_key": "b::art1", "relation": "references", "generation_id": DEFAULT_GENERATION_ID},
                {"id": 2, "source_key": "a::art2", "target_key": "b::art1", "relation": "complements", "generation_id": DEFAULT_GENERATION_ID},
            ],
        }
    )
    snap = load_baseline_snapshot(client)
    assert snap.total_docs == 2
    assert snap.total_chunks == 3
    assert snap.total_edges == 2


# (f) handles pagination (mock >1000 rows).
def test_handles_pagination_over_1000_rows() -> None:
    seed_docs = [
        _doc(doc_id=f"doc_{i:05d}", relative_path=f"path/{i:05d}.md")
        for i in range(1250)
    ]
    client = _FakeClient(seed={"documents": seed_docs})
    snap = load_baseline_snapshot(client)
    assert snap.total_docs == 1250
    # Spot-check a row from each expected page.
    assert snap.get("path/00000.md") is not None
    assert snap.get("path/00999.md") is not None
    assert snap.get("path/01000.md") is not None
    assert snap.get("path/01249.md") is not None


# (g) tolerates missing columns (e.g. doc_fingerprint IS NULL on legacy rows).
def test_tolerates_missing_fingerprint_columns() -> None:
    client = _FakeClient(
        seed={
            "documents": [
                _doc(doc_id="legacy", relative_path="legacy.md", doc_fingerprint=None),
                # Also cover the case where retired_at / last_delta_id are
                # absent from the row entirely (not just None).
                {
                    "doc_id": "bare",
                    "relative_path": "bare.md",
                    "content_hash": "hash_bare",
                    "sync_generation": DEFAULT_GENERATION_ID,
                },
            ]
        }
    )
    snap = load_baseline_snapshot(client)
    assert snap.total_docs == 2
    legacy = snap.get("legacy.md")
    assert legacy is not None
    assert legacy.doc_fingerprint is None
    bare = snap.get("bare.md")
    assert bare is not None
    assert bare.doc_fingerprint is None
    assert bare.retired_at is None
    assert bare.last_delta_id is None


# Extra: rows with no doc_id or no relative_path are skipped (bad row guard).
def test_skips_rows_missing_identifiers() -> None:
    client = _FakeClient(
        seed={
            "documents": [
                _doc(doc_id="a", relative_path="a.md"),
                {"doc_id": "", "relative_path": "should_skip.md", "sync_generation": DEFAULT_GENERATION_ID},
                {"doc_id": "b", "relative_path": "", "sync_generation": DEFAULT_GENERATION_ID},
            ]
        }
    )
    snap = load_baseline_snapshot(client)
    assert snap.total_docs == 1
    assert set(snap.documents_by_relative_path.keys()) == {"a.md"}
