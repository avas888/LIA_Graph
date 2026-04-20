"""Post-synthesis surface mutator.

Synthesis already produced an `ExpertPanelSurface` with cards whose
`card_summary` came from the corpus head-slice (the bunching path). This
module replaces those slices with the LLM-written one-sentence summaries and
re-orders groups + ungrouped by composite score.

Kept separate from `composer` and `runner` because surface mutation is a
distinct concern: it knows about `InterpretationCard` / `ExpertGroup` /
`ExpertPanelSurface` shapes, while composer/judge stay generic.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from ..shared import ExpertGroup, ExpertPanelSurface, InterpretationCard


_SUMMARY_ORIGIN_LLM = "llm_rerank"
_SUMMARY_QUALITY_HIGH = "high"


def apply_to_surface(
    *,
    surface: ExpertPanelSurface,
    summaries: Mapping[str, str],
    composite_scores: Mapping[str, float],
) -> ExpertPanelSurface:
    """Returns a new `ExpertPanelSurface` with rewritten card summaries and
    composite-driven order. Original surface is not mutated (frozen dataclasses)."""
    rewritten_groups = tuple(
        _rewrite_group(group, summaries=summaries, composite_scores=composite_scores)
        for group in surface.groups
    )
    rewritten_ungrouped = tuple(
        _rewrite_card(card, summaries=summaries, composite_scores=composite_scores)
        for card in surface.ungrouped
    )

    sorted_groups = _sort_groups(rewritten_groups)
    sorted_ungrouped = _sort_cards(rewritten_ungrouped)
    ranked_groups = tuple(replace(group, panel_rank=index) for index, group in enumerate(sorted_groups, start=1))
    ranked_ungrouped = tuple(replace(card, panel_rank=index) for index, card in enumerate(sorted_ungrouped, start=1))

    return replace(surface, groups=ranked_groups, ungrouped=ranked_ungrouped)


# --- group / card rewriting -------------------------------------------------


def _rewrite_group(
    group: ExpertGroup,
    *,
    summaries: Mapping[str, str],
    composite_scores: Mapping[str, float],
) -> ExpertGroup:
    rewritten_snippets = tuple(
        _rewrite_card(card, summaries=summaries, composite_scores=composite_scores)
        for card in group.snippets
    )
    sorted_snippets = _sort_cards(rewritten_snippets)
    primary_summary = _primary_llm_summary(sorted_snippets, summaries)
    summary_signal = primary_summary or group.summary_signal
    summary_origin = _SUMMARY_ORIGIN_LLM if primary_summary else group.summary_origin
    summary_quality = _SUMMARY_QUALITY_HIGH if primary_summary else group.summary_quality
    relevance_score = max(
        (composite_scores.get(card.doc_id, card.relevance_score) for card in sorted_snippets),
        default=group.relevance_score,
    )
    return replace(
        group,
        snippets=sorted_snippets,
        summary_signal=summary_signal,
        summary_origin=summary_origin,
        summary_quality=summary_quality,
        relevance_score=float(relevance_score),
    )


def _rewrite_card(
    card: InterpretationCard,
    *,
    summaries: Mapping[str, str],
    composite_scores: Mapping[str, float],
) -> InterpretationCard:
    llm_summary = (summaries.get(card.doc_id) or "").strip()
    composite = composite_scores.get(card.doc_id)
    updates: dict[str, object] = {}
    if llm_summary:
        updates["card_summary"] = llm_summary
        updates["summary_origin"] = _SUMMARY_ORIGIN_LLM
        updates["summary_quality"] = _SUMMARY_QUALITY_HIGH
    if composite is not None:
        updates["relevance_score"] = float(composite)
    if not updates:
        return card
    return replace(card, **updates)


def _primary_llm_summary(
    snippets: tuple[InterpretationCard, ...],
    summaries: Mapping[str, str],
) -> str:
    """The primary card's LLM summary becomes the group's visible body. Falls
    back to empty string so the caller keeps the deterministic summary_signal."""
    if not snippets:
        return ""
    primary = snippets[0]
    return (summaries.get(primary.doc_id) or "").strip()


# --- ordering ---------------------------------------------------------------


def _sort_groups(groups: tuple[ExpertGroup, ...]) -> tuple[ExpertGroup, ...]:
    return tuple(
        sorted(
            groups,
            key=lambda group: (
                not bool(group.requested_match),
                -float(group.relevance_score or 0.0),
                str(group.article_ref or ""),
            ),
        )
    )


def _sort_cards(cards: tuple[InterpretationCard, ...]) -> tuple[InterpretationCard, ...]:
    return tuple(
        sorted(
            cards,
            key=lambda card: (
                not bool(card.requested_match),
                -float(card.relevance_score or 0.0),
                str(card.doc_id or ""),
            ),
        )
    )
