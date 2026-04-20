"""Pure score blending — no I/O, no side effects.

Given per-doc_id LLM scores, graph proximity, supabase hybrid scores, and
the lexical retrieval score, produce a single composite per doc_id and an
ordering. Weights live in `interpretacion.policy` so they can be tuned
without touching this module.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from ..policy import (
    EXPERT_RERANK_GRAPH_WEIGHT,
    EXPERT_RERANK_LEXICAL_WEIGHT,
    EXPERT_RERANK_LLM_WEIGHT,
    EXPERT_RERANK_SUPABASE_WEIGHT,
)
from .contracts import LLMScoredCandidate


def compose_scores(
    *,
    doc_ids: Iterable[str],
    llm_scored: Iterable[LLMScoredCandidate],
    graph_scores: Mapping[str, float],
    supabase_scores: Mapping[str, float],
    lexical_scores: Mapping[str, float],
) -> dict[str, float]:
    """Returns `{doc_id: composite 0..1}`. Doc IDs missing from a signal map
    contribute 0 for that signal — the composer doesn't penalize, just
    rewards what fired."""
    llm_by_doc = {item.doc_id: _normalize_llm_score(item.score) for item in llm_scored}
    composed: dict[str, float] = {}
    for doc_id in doc_ids:
        composite = (
            EXPERT_RERANK_LLM_WEIGHT * llm_by_doc.get(doc_id, 0.0)
            + EXPERT_RERANK_GRAPH_WEIGHT * _clamp_unit(graph_scores.get(doc_id, 0.0))
            + EXPERT_RERANK_SUPABASE_WEIGHT * _clamp_unit(supabase_scores.get(doc_id, 0.0))
            + EXPERT_RERANK_LEXICAL_WEIGHT * _clamp_unit(lexical_scores.get(doc_id, 0.0))
        )
        composed[doc_id] = _clamp_unit(composite)
    return composed


def order_by_composite(
    *,
    doc_ids: Iterable[str],
    composite_scores: Mapping[str, float],
) -> tuple[str, ...]:
    """Stable sort: descending composite score, ties broken by doc_id ascending
    so the ordering is deterministic across runs (helps caching / snapshots)."""
    materialized = list(doc_ids)
    return tuple(
        sorted(
            materialized,
            key=lambda doc_id: (-composite_scores.get(doc_id, 0.0), doc_id),
        )
    )


def _normalize_llm_score(raw: float) -> float:
    """LLM score is 0..100 by prompt contract; bring to 0..1 for blending."""
    return _clamp_unit(float(raw) / 100.0)


def _clamp_unit(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return float(value)
