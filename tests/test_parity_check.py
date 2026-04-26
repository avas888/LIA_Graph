"""Tests for ``lia_graph.ingestion.parity_check``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lia_graph.ingestion.parity_check import (
    DEFAULT_ABS_TOLERANCE,
    DEFAULT_PCT_TOLERANCE,
    ParityReport,
    check_parity,
)


@dataclass
class _SbExecute:
    count: int
    data: list[Any] | None = None


class _SbQuery:
    def __init__(self, count: int) -> None:
        self._count = count

    def eq(self, *args, **kwargs) -> "_SbQuery":
        return self

    def is_(self, *args, **kwargs) -> "_SbQuery":
        return self

    def range(self, *args, **kwargs) -> "_SbQuery":
        return self

    def execute(self) -> _SbExecute:
        return _SbExecute(count=self._count, data=[])


class _SbTable:
    def __init__(self, count: int) -> None:
        self._count = count

    def select(self, *args, count: str | None = None) -> _SbQuery:
        return _SbQuery(self._count)


class _FakeSupabase:
    def __init__(self, counts: dict[str, int]) -> None:
        self._counts = counts

    def table(self, name: str) -> _SbTable:
        return _SbTable(self._counts.get(name, 0))


@dataclass
class _FalkorResult:
    rows: tuple[dict[str, int], ...]


class _FakeGraphClient:
    def __init__(self, label_counts: dict[str, int]) -> None:
        self._label_counts = label_counts

    def execute(self, statement, *, strict: bool = False):
        q = statement.query
        # Order matters: the DISTINCT-source_path query also matches
        # "(a:ArticleNode)", so check the docs proxy first.
        if "DISTINCT a.source_path" in q:
            return _FalkorResult(rows=({"n": self._label_counts.get("docs", 0)},))
        if "(a:ArticleNode)" in q:
            return _FalkorResult(rows=({"n": self._label_counts.get("articles", 0)},))
        if "()-[r]->()" in q:
            return _FalkorResult(rows=({"n": self._label_counts.get("edges", 0)},))
        return _FalkorResult(rows=())


# (a) identical counts → ok=True.
def test_identical_counts_ok() -> None:
    sb = _FakeSupabase(
        {"documents": 100, "document_chunks": 500, "normative_edges": 200}
    )
    fk = _FakeGraphClient({"docs": 100, "articles": 500, "edges": 200})
    report = check_parity(sb, fk)
    assert isinstance(report, ParityReport)
    assert report.ok is True
    assert report.mismatches == []


# (b) Supabase ahead by 1 within tolerance → ok=True (absolute-5 floor).
def test_off_by_one_within_tolerance() -> None:
    sb = _FakeSupabase(
        {"documents": 101, "document_chunks": 500, "normative_edges": 200}
    )
    fk = _FakeGraphClient({"docs": 100, "articles": 500, "edges": 200})
    report = check_parity(sb, fk)
    assert report.ok is True
    # Mismatches list is empty because the diff is within tolerance.
    assert report.mismatches == []


# (c) Large mismatch out of tolerance → ok=False with named field.
def test_large_mismatch_breaks_parity() -> None:
    sb = _FakeSupabase(
        {"documents": 100, "document_chunks": 500, "normative_edges": 200}
    )
    fk = _FakeGraphClient({"docs": 150, "articles": 500, "edges": 200})
    report = check_parity(sb, fk)
    assert report.ok is False
    fields = {m.field for m in report.mismatches}
    assert "docs" in fields


# (d) tighter pct tolerance can escalate otherwise-allowed mismatches.
def test_tight_tolerance_escalates() -> None:
    sb = _FakeSupabase(
        {"documents": 1000, "document_chunks": 500, "normative_edges": 200}
    )
    # Diff = 50 rows (5% of 1000); default tolerance allows 5 abs or 0.2%.
    fk = _FakeGraphClient({"docs": 950, "articles": 500, "edges": 200})
    report = check_parity(sb, fk)
    assert report.ok is False
    # 50-row diff on 1000 exceeds both absolute-5 and 0.2% (=2).
    assert any(m.field == "docs" for m in report.mismatches)


# (e) both sides empty → ok=True.
def test_both_empty_is_ok() -> None:
    sb = _FakeSupabase({})
    fk = _FakeGraphClient({})
    report = check_parity(sb, fk)
    assert report.ok is True
    assert report.supabase_docs == 0
    assert report.falkor_docs == 0
