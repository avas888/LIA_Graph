from __future__ import annotations

from .answer_first_bubble import PreparedAnswerLine, compose_first_bubble_answer
from .answer_followup import compose_followup_answer
from .answer_shared import (
    append_unique,
    extract_change_mentions,
    filter_published_lines,
    has_explicit_change_intent,
    is_recent_ag_period,
    line_has_legal_reference,
    normalize_text,
    published_context_lines,
    render_bullet_section,
    render_numbered_section,
    should_surface_change_context,
    should_use_first_bubble_format,
    take_new_lines,
)
from ..pipeline_c.contracts import PipelineCRequest
from .answer_synthesis import GraphNativeAnswerParts
from .contracts import GraphEvidenceBundle


def compose_main_chat_answer(
    *,
    request: PipelineCRequest,
    answer_mode: str,
    planner_query_mode: str,
    temporal_context: dict[str, object],
    evidence: GraphEvidenceBundle,
    answer_parts: GraphNativeAnswerParts,
) -> str:
    if should_use_first_bubble_format(request):
        return compose_first_bubble_answer(
            request=request,
            answer_mode=answer_mode,
            planner_query_mode=planner_query_mode,
            temporal_context=temporal_context,
            primary_articles=evidence.primary_articles,
            connected_articles=evidence.connected_articles,
            reforms=evidence.related_reforms,
            support_documents=evidence.support_documents,
            article_insights=answer_parts.article_insights,
            support_insights=answer_parts.support_insights,
            recommendations=answer_parts.recommendations,
            procedure=answer_parts.procedure,
            paperwork=answer_parts.paperwork,
            precautions=answer_parts.precautions,
        )

    return compose_followup_answer(
        request=request,
        primary_articles=evidence.primary_articles,
        connected_articles=evidence.connected_articles,
        recommendations=answer_parts.recommendations,
        procedure=answer_parts.procedure,
        paperwork=answer_parts.paperwork,
        legal_anchor=answer_parts.legal_anchor,
        precautions=answer_parts.precautions,
        opportunities=answer_parts.opportunities,
        context_lines=answer_parts.context_lines,
        followup_direct_answer=answer_parts.followup_direct_answer,
        followup_main_exception=answer_parts.followup_main_exception,
        followup_practical_next_step=answer_parts.followup_practical_next_step,
    )

__all__ = [
    "PreparedAnswerLine",
    "append_unique",
    "compose_followup_answer",
    "compose_first_bubble_answer",
    "compose_main_chat_answer",
    "extract_change_mentions",
    "filter_published_lines",
    "has_explicit_change_intent",
    "is_recent_ag_period",
    "line_has_legal_reference",
    "normalize_text",
    "published_context_lines",
    "render_bullet_section",
    "render_numbered_section",
    "should_surface_change_context",
    "should_use_first_bubble_format",
    "take_new_lines",
]
