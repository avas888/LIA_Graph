"""Supabase ↔ FalkorDB parity probe (Phase 7 — Decision H1).

See ``docs/done/next/additive_corpusv1.md`` §4 Decision H1 (reviewer-revised:
tolerance = max(5 rows, 0.2%) absolute, ``--strict-parity`` escalates).
Run before every ``--additive`` delta to detect drift early.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..instrumentation import emit_event


DEFAULT_GENERATION_ID = "gen_active_rolling"
DEFAULT_ABS_TOLERANCE = 5
DEFAULT_PCT_TOLERANCE = 0.002  # 0.2%


@dataclass
class ParityMismatch:
    field: str
    supabase_value: int
    falkor_value: int

    @property
    def delta(self) -> int:
        return int(self.supabase_value) - int(self.falkor_value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "supabase_value": int(self.supabase_value),
            "falkor_value": int(self.falkor_value),
            "delta": int(self.delta),
        }


@dataclass
class ParityReport:
    ok: bool
    generation_id: str
    abs_tolerance: int
    pct_tolerance: float
    supabase_docs: int
    falkor_docs: int
    supabase_chunks: int
    falkor_articles: int
    supabase_edges: int
    falkor_edges: int
    mismatches: list[ParityMismatch] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": bool(self.ok),
            "generation_id": self.generation_id,
            "abs_tolerance": int(self.abs_tolerance),
            "pct_tolerance": float(self.pct_tolerance),
            "supabase_docs": int(self.supabase_docs),
            "falkor_docs": int(self.falkor_docs),
            "supabase_chunks": int(self.supabase_chunks),
            "falkor_articles": int(self.falkor_articles),
            "supabase_edges": int(self.supabase_edges),
            "falkor_edges": int(self.falkor_edges),
            "mismatches": [m.to_dict() for m in self.mismatches],
        }


def _supabase_count(
    client: Any,
    table: str,
    *,
    generation_id_column: str,
    generation_id: str,
    extra_filters: dict[str, Any] | None = None,
) -> int:
    try:
        query = (
            client.table(table)
            .select("*", count="exact")
            .eq(generation_id_column, generation_id)
        )
        if extra_filters:
            for k, v in extra_filters.items():
                query = query.eq(k, v)
        resp = query.range(0, 0).execute()
    except Exception:  # noqa: BLE001
        return 0
    count = getattr(resp, "count", None)
    try:
        return int(count or 0)
    except (TypeError, ValueError):
        return 0


def _falkor_count(
    graph_client: Any,
    cypher: str,
) -> int:
    """Run a COUNT query against the graph adapter. Returns 0 on any error."""
    from ..graph.client import GraphWriteStatement

    if graph_client is None:
        return 0
    stmt = GraphWriteStatement(
        description="Parity count probe",
        query=cypher,
        parameters={},
    )
    try:
        result = graph_client.execute(stmt, strict=False)
    except Exception:  # noqa: BLE001
        return 0
    rows = getattr(result, "rows", ()) or ()
    if not rows:
        return 0
    first = rows[0]
    if isinstance(first, dict):
        for v in first.values():
            try:
                return int(v or 0)
            except (TypeError, ValueError):
                continue
    return 0


def _tolerance_allows(
    supabase_value: int,
    falkor_value: int,
    *,
    abs_tolerance: int,
    pct_tolerance: float,
) -> bool:
    diff = abs(int(supabase_value) - int(falkor_value))
    larger = max(abs(int(supabase_value)), abs(int(falkor_value)), 1)
    pct_allow = int(round(larger * pct_tolerance))
    allow = max(abs_tolerance, pct_allow)
    return diff <= allow


def check_parity(
    supabase_client: Any,
    graph_client: Any,
    *,
    generation_id: str = DEFAULT_GENERATION_ID,
    abs_tolerance: int = DEFAULT_ABS_TOLERANCE,
    pct_tolerance: float = DEFAULT_PCT_TOLERANCE,
) -> ParityReport:
    """Compare document / chunk / edge counts between Supabase and Falkor.

    Returns a ``ParityReport``. ``ok=True`` iff every field is within the
    tolerance band. Individual mismatches are surfaced in ``mismatches``
    even when ``ok`` is True — they become observability-only warnings.
    """
    emit_event(
        "ingest.parity.check.start",
        {"generation_id": generation_id},
    )

    supabase_docs = _supabase_count(
        supabase_client,
        "documents",
        generation_id_column="sync_generation",
        generation_id=generation_id,
        extra_filters=None,
    )
    # Exclude retired docs from the comparison — Falkor deletes them.
    try:
        resp = (
            supabase_client.table("documents")
            .select("*", count="exact")
            .eq("sync_generation", generation_id)
            .is_("retired_at", "null")
            .range(0, 0)
            .execute()
        )
        supabase_docs = int(getattr(resp, "count", None) or supabase_docs)
    except Exception:  # noqa: BLE001
        pass

    supabase_chunks = _supabase_count(
        supabase_client,
        "document_chunks",
        generation_id_column="sync_generation",
        generation_id=generation_id,
    )
    supabase_edges = _supabase_count(
        supabase_client,
        "normative_edges",
        generation_id_column="generation_id",
        generation_id=generation_id,
    )

    # Falkor counts — by label. Articles stand in for chunks at the graph side.
    falkor_docs = _falkor_count(
        graph_client,
        "MATCH (d:Document) RETURN count(d) AS n",
    )
    falkor_articles = _falkor_count(
        graph_client,
        "MATCH (a:Article) RETURN count(a) AS n",
    )
    falkor_edges = _falkor_count(
        graph_client,
        "MATCH ()-[r]->() RETURN count(r) AS n",
    )

    comparisons = (
        ("docs", supabase_docs, falkor_docs),
        ("chunks_vs_articles", supabase_chunks, falkor_articles),
        ("edges", supabase_edges, falkor_edges),
    )
    mismatches: list[ParityMismatch] = []
    for field_name, sb, fk in comparisons:
        if not _tolerance_allows(
            sb, fk, abs_tolerance=abs_tolerance, pct_tolerance=pct_tolerance
        ):
            mismatches.append(
                ParityMismatch(
                    field=field_name,
                    supabase_value=sb,
                    falkor_value=fk,
                )
            )
            emit_event(
                "ingest.parity.check.mismatch",
                {
                    "field": field_name,
                    "supabase_value": sb,
                    "falkor_value": fk,
                    "delta": int(sb) - int(fk),
                },
            )

    report = ParityReport(
        ok=not mismatches,
        generation_id=generation_id,
        abs_tolerance=abs_tolerance,
        pct_tolerance=pct_tolerance,
        supabase_docs=supabase_docs,
        falkor_docs=falkor_docs,
        supabase_chunks=supabase_chunks,
        falkor_articles=falkor_articles,
        supabase_edges=supabase_edges,
        falkor_edges=falkor_edges,
        mismatches=mismatches,
    )
    emit_event("ingest.parity.check.done", report.to_dict())
    return report


__all__ = [
    "DEFAULT_ABS_TOLERANCE",
    "DEFAULT_GENERATION_ID",
    "DEFAULT_PCT_TOLERANCE",
    "ParityMismatch",
    "ParityReport",
    "check_parity",
]
