from __future__ import annotations

from dataclasses import dataclass, field

from ..pipeline_c.contracts import PipelineCRequest
from .answer_shared import (
    filter_published_lines,
    normalize_text,
    should_surface_change_context,
    take_new_lines,
)
from .answer_support import (
    extract_article_insights,
    extract_support_doc_insights,
)
from .answer_synthesis_sections import (
    build_context_lines,
    build_followup_resolution,
    build_legal_anchor_lines,
    build_opportunities,
    build_paperwork_lines,
    build_precautions,
    build_procedure_steps,
    build_recommendations,
)
from .contracts import GraphEvidenceBundle


@dataclass
class GraphNativeAnswerParts:
    article_insights: dict[str, tuple[str, ...]] = field(default_factory=dict)
    support_insights: dict[str, tuple[str, ...]] = field(default_factory=dict)
    recommendations: tuple[str, ...] = ()
    procedure: tuple[str, ...] = ()
    paperwork: tuple[str, ...] = ()
    legal_anchor: tuple[str, ...] = ()
    context_lines: tuple[str, ...] = ()
    precautions: tuple[str, ...] = ()
    opportunities: tuple[str, ...] = ()
    followup_direct_answer: str = ""
    followup_main_exception: str = ""
    followup_practical_next_step: str = ""


def build_graph_native_answer_parts(
    *,
    request: PipelineCRequest,
    answer_mode: str,
    planner_query_mode: str,
    temporal_context: dict[str, object],
    evidence: GraphEvidenceBundle,
) -> GraphNativeAnswerParts:
    allow_change_context = should_surface_change_context(
        normalized_message=normalize_text(request.message),
        temporal_context=temporal_context,
        planner_query_mode=planner_query_mode,
        requested_period_label=str(temporal_context.get("requested_period_label") or "").strip(),
    )
    support_insights = extract_support_doc_insights(
        request=request,
        support_documents=evidence.support_documents,
    )
    article_insights = extract_article_insights(
        request=request,
        temporal_context=temporal_context,
        primary_articles=evidence.primary_articles,
        connected_articles=evidence.connected_articles,
    )
    recommendations = filter_published_lines(
        build_recommendations(
            request=request,
            temporal_context=temporal_context,
            primary_articles=evidence.primary_articles,
            connected_articles=evidence.connected_articles,
        ),
        allow_change_lines=allow_change_context,
    )
    procedure = filter_published_lines(
        build_procedure_steps(
            request=request,
            temporal_context=temporal_context,
            primary_articles=evidence.primary_articles,
            article_insights=article_insights,
            support_insights=support_insights,
        ),
        allow_change_lines=allow_change_context,
    )
    paperwork = filter_published_lines(
        build_paperwork_lines(
            request=request,
            article_insights=article_insights,
            support_insights=support_insights,
        ),
        allow_change_lines=allow_change_context,
    )
    legal_anchor = build_legal_anchor_lines(
        request=request,
        primary_articles=evidence.primary_articles,
        connected_articles=evidence.connected_articles,
    )
    context_lines = filter_published_lines(
        build_context_lines(
            request=request,
            temporal_context=temporal_context,
            planner_query_mode=planner_query_mode,
            primary_articles=evidence.primary_articles,
            reforms=evidence.related_reforms,
            article_insights=article_insights,
            support_insights=support_insights,
        ),
        allow_change_lines=allow_change_context,
    )
    precautions = filter_published_lines(
        build_precautions(
            request=request,
            temporal_context=temporal_context,
            primary_articles=evidence.primary_articles,
            connected_articles=evidence.connected_articles,
            answer_mode=answer_mode,
            article_insights=article_insights,
            support_insights=support_insights,
        ),
        allow_change_lines=allow_change_context,
    )
    opportunities = filter_published_lines(
        build_opportunities(
            request=request,
            primary_articles=evidence.primary_articles,
        ),
        allow_change_lines=allow_change_context,
    )

    seen_answer_lines: set[str] = set()
    recommendations = take_new_lines(recommendations, seen_answer_lines)
    procedure = take_new_lines(procedure, seen_answer_lines)
    paperwork = take_new_lines(paperwork, seen_answer_lines)
    precautions = take_new_lines(precautions, seen_answer_lines)
    opportunities = take_new_lines(opportunities, seen_answer_lines)
    context_lines = take_new_lines(context_lines, seen_answer_lines)
    followup_direct_answer, followup_main_exception, followup_practical_next_step = build_followup_resolution(
        request=request,
        recommendations=recommendations,
        procedure=procedure,
        paperwork=paperwork,
        precautions=precautions,
        opportunities=opportunities,
        context_lines=context_lines,
    )

    return GraphNativeAnswerParts(
        article_insights=article_insights,
        support_insights=support_insights,
        recommendations=recommendations,
        procedure=procedure,
        paperwork=paperwork,
        legal_anchor=legal_anchor,
        context_lines=context_lines,
        precautions=precautions,
        opportunities=opportunities,
        followup_direct_answer=followup_direct_answer,
        followup_main_exception=followup_main_exception,
        followup_practical_next_step=followup_practical_next_step,
    )


__all__ = [
    "GraphNativeAnswerParts",
    "build_graph_native_answer_parts",
]
