"""fixplan_v3 sub-fix 1B-ε — retriever-side vigencia demotion pass.

Layered on top of the existing `hybrid_search` RPC:

  1. The retriever calls `hybrid_search` (returns N candidate chunks).
  2. This module calls `chunk_vigencia_gate_at_date` (or `_for_period`) with
     the chunk_ids and the planner's vigencia query payload.
  3. Each chunk's RRF score is multiplied by the anchor's `demotion_factor`.
  4. Chunks whose anchor is `DE / SP / IE / VL / DI-expired` (factor 0) are
     filtered out.

This keeps the existing `hybrid_search` SQL untouched — once `norm_citations`
hits ≥95% coverage we flip the binary `vigencia` column filter off via
follow-up migration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

from lia_graph.pipeline_d.contracts import GraphRetrievalPlan
from lia_graph.pipeline_d.vigencia_resolver import ResolverQuery

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DemotionResult:
    """Per-chunk outcome of the demotion pass.

    `score_factor == 0.0` means the chunk should be dropped from the
    candidate set; the retriever filters on this.
    """

    chunk_id: str
    score_factor: float
    anchor_norm_id: str | None
    anchor_state: str | None
    anchor_strength: str | None
    interpretive_constraint: Mapping[str, Any] | None
    record_id: str | None
    art_338_cp_applied: bool = False


@dataclass(frozen=True)
class DemotionPassResult:
    """Aggregate result of running the demotion pass over a candidate set."""

    per_chunk: tuple[DemotionResult, ...]
    rpc_kind: str  # 'at_date' | 'for_period' | 'noop'
    rpc_payload: Mapping[str, Any]
    chunks_seen: int
    chunks_kept: int
    chunks_dropped: int
    chunks_demoted: int


# ---------------------------------------------------------------------------
# Demotion pass
# ---------------------------------------------------------------------------


def run_demotion_pass(
    *,
    plan: GraphRetrievalPlan,
    chunk_ids: Sequence[str],
    rpc_at_date_fn=None,
    rpc_for_period_fn=None,
    today: date | None = None,
) -> DemotionPassResult:
    """Run the v3 vigencia gate over a list of chunk_ids.

    `rpc_at_date_fn` and `rpc_for_period_fn` are pluggable callables — in
    production they invoke `chunk_vigencia_gate_at_date` /
    `chunk_vigencia_gate_for_period` via Supabase RPC. For tests, pass fakes
    that return canned rows.
    """

    if not chunk_ids:
        return DemotionPassResult(
            per_chunk=(),
            rpc_kind="noop",
            rpc_payload={},
            chunks_seen=0,
            chunks_kept=0,
            chunks_dropped=0,
            chunks_demoted=0,
        )

    query = ResolverQuery.from_plan(plan, default_today=today)

    if query.kind == "at_date":
        if rpc_at_date_fn is None:
            return _passthrough(chunk_ids, "at_date", query.payload, "no rpc_at_date_fn")
        rows = list(rpc_at_date_fn(list(chunk_ids), query.payload["as_of_date"]))
    elif query.kind == "for_period":
        if rpc_for_period_fn is None:
            return _passthrough(chunk_ids, "for_period", query.payload, "no rpc_for_period_fn")
        rows = list(
            rpc_for_period_fn(
                list(chunk_ids),
                query.payload.get("impuesto") or "renta",
                int(query.payload.get("periodo_year") or (today or date.today()).year),
                query.payload.get("periodo_label"),
            )
        )
    else:
        raise ValueError(f"Unknown vigencia_query_kind: {query.kind!r}")

    # Build a per-chunk decision: take the most-restrictive anchor across
    # all citations for the chunk (if any anchor returns 0.0 → drop chunk).
    by_chunk: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        cid = str(row.get("chunk_id"))
        by_chunk.setdefault(cid, []).append(row)

    out: list[DemotionResult] = []
    kept = dropped = demoted = 0
    for chunk_id in chunk_ids:
        rows_for_chunk = by_chunk.get(chunk_id) or []
        if not rows_for_chunk:
            # No norm_citations row — chunk has no anchor; pass through.
            out.append(
                DemotionResult(
                    chunk_id=chunk_id,
                    score_factor=1.0,
                    anchor_norm_id=None,
                    anchor_state=None,
                    anchor_strength=None,
                    interpretive_constraint=None,
                    record_id=None,
                )
            )
            kept += 1
            continue
        anchors_all = [r for r in rows_for_chunk if r.get("role") == "anchor"]
        # Drop anchors whose state is null — those are LEFT JOIN misses
        # (chunk cites a norm that has no `norm_vigencia_history` row yet).
        # Treat them as no-history → 1.0 factor with no annotation.
        anchors = [r for r in anchors_all if r.get("state") is not None]
        # If the chunk has no anchor citations, treat reference-only as 1.0
        # (the existing binary `vigencia` filter still catches the bulk).
        if not anchors:
            out.append(
                DemotionResult(
                    chunk_id=chunk_id,
                    score_factor=1.0,
                    anchor_norm_id=None,
                    anchor_state=None,
                    anchor_strength=None,
                    interpretive_constraint=None,
                    record_id=None,
                )
            )
            kept += 1
            continue
        # Take the smallest demotion factor (most restrictive). Use explicit
        # None check — `0.0 or 1.0` evaluates to 1.0 due to falsy semantics.
        def _f(row):
            v = row.get("demotion_factor")
            return float(v) if v is not None else 1.0
        worst = min(anchors, key=_f)
        factor = _f(worst)
        result = DemotionResult(
            chunk_id=chunk_id,
            score_factor=factor,
            anchor_norm_id=str(worst.get("norm_id") or ""),
            anchor_state=worst.get("state"),
            anchor_strength=worst.get("anchor_strength"),
            interpretive_constraint=worst.get("interpretive_constraint"),
            record_id=str(worst.get("record_id") or "") or None,
            art_338_cp_applied=bool(worst.get("art_338_cp_applied") or False),
        )
        out.append(result)
        if factor == 0.0:
            dropped += 1
        elif factor < 1.0:
            demoted += 1
            kept += 1
        else:
            kept += 1

    return DemotionPassResult(
        per_chunk=tuple(out),
        rpc_kind=query.kind,
        rpc_payload=query.payload,
        chunks_seen=len(chunk_ids),
        chunks_kept=kept,
        chunks_dropped=dropped,
        chunks_demoted=demoted,
    )


def apply_demotion(
    chunks: Iterable[Mapping[str, Any]],
    pass_result: DemotionPassResult,
    *,
    score_field: str = "rrf_score",
) -> list[dict[str, Any]]:
    """Multiply each chunk's RRF score by its demotion factor; drop zeros.

    Adds `vigencia_v3` annotation block to each kept chunk for downstream
    chip rendering (Fix 1D).
    """

    by_chunk = {r.chunk_id: r for r in pass_result.per_chunk}
    out: list[dict[str, Any]] = []
    for chunk in chunks:
        cid = str(chunk.get("chunk_id"))
        result = by_chunk.get(cid)
        if result is None:
            out.append(dict(chunk))
            continue
        if result.score_factor == 0.0:
            continue  # dropped
        new_chunk = dict(chunk)
        if score_field in new_chunk and new_chunk[score_field] is not None:
            try:
                new_chunk[score_field] = float(new_chunk[score_field]) * result.score_factor
            except (TypeError, ValueError):
                pass
        # Only annotate when the gate produced a real anchor state. Passthrough
        # chunks (no anchor citation) get no annotation — keeps doc-level
        # aggregation in `_collect_support` clean.
        if result.anchor_state is not None and result.anchor_norm_id is not None:
            new_chunk["vigencia_v3"] = {
                "anchor_norm_id": result.anchor_norm_id,
                "anchor_state": result.anchor_state,
                "anchor_strength": result.anchor_strength,
                "demotion_factor": result.score_factor,
                "interpretive_constraint": result.interpretive_constraint,
                "record_id": result.record_id,
                "art_338_cp_applied": result.art_338_cp_applied,
            }
        out.append(new_chunk)
    return out


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _passthrough(chunk_ids: Sequence[str], kind: str, payload: Mapping[str, Any], reason: str) -> DemotionPassResult:
    LOGGER.warning("vigencia_demotion: passthrough (%s) — chunks=%d", reason, len(chunk_ids))
    return DemotionPassResult(
        per_chunk=tuple(
            DemotionResult(
                chunk_id=cid,
                score_factor=1.0,
                anchor_norm_id=None,
                anchor_state=None,
                anchor_strength=None,
                interpretive_constraint=None,
                record_id=None,
            )
            for cid in chunk_ids
        ),
        rpc_kind=kind,
        rpc_payload=payload,
        chunks_seen=len(chunk_ids),
        chunks_kept=len(chunk_ids),
        chunks_dropped=0,
        chunks_demoted=0,
    )


__all__ = [
    "DemotionPassResult",
    "DemotionResult",
    "apply_demotion",
    "run_demotion_pass",
]
