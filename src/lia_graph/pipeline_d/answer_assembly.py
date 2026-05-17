from __future__ import annotations

from .answer_comparative_regime import (
    compose_comparative_regime_answer,
    match_regime_pair_for_request,
)
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
from .answer_topic_gate import filter_template_bullets
from .contracts import GraphEvidenceBundle

# Trace seam — no-op when the tracer isn't loaded (e.g. unit tests that
# import this module without the orchestrator context).
try:
    from tracers_and_logs import pipeline_trace as _trace
except ImportError:  # pragma: no cover - tracer always present in served runtime
    _trace = None  # type: ignore[assignment]


def _trace_step(step_name: str, *, status: str = "ok", **details):
    if _trace is None:
        return
    _trace.step(step_name, status=status, **details)


def compose_main_chat_answer(
    *,
    request: PipelineCRequest,
    answer_mode: str,
    planner_query_mode: str,
    temporal_context: dict[str, object],
    evidence: GraphEvidenceBundle,
    answer_parts: GraphNativeAnswerParts,
) -> str:
    # next_v4 §5 — comparative-regime mode produces a side-by-side
    # markdown table directly from the matched pair config; bypass the
    # first-bubble / followup paths whose prose-merging dissolves the
    # comparative structure. If the planner classified the turn as
    # comparative but no pair config matches the request anymore (e.g.
    # config drift between planner and synthesis), fall through to the
    # standard composer rather than emit an empty answer. fix_v8 §3d
    # adds explicit trace events on both branches so Q10-shape hangs are
    # diagnosable from the trace alone.
    if planner_query_mode == "comparative_regime_chain":
        pair = match_regime_pair_for_request(request)
        if pair is not None:
            _trace_step(
                "comparative_regime.pair_matched",
                pair_key=str(pair.get("domain") or "(unknown)"),
                cutoff_year=pair.get("cutoff_year"),
                dimension_count=len(pair.get("dimensions") or ()),
            )
            # Comparative-regime answers are table renderings driven by a
            # hand-curated pair config; the cross-topic content gate is
            # not relevant here (no template bullets to filter).
            return compose_comparative_regime_answer(request=request, pair=pair)
        _trace_step(
            "comparative_regime.no_pair_match",
            status="warn",
            primary_topic=getattr(request, "topic", None),
            message_preview=str(getattr(request, "message", "") or "")[:160],
        )

    if should_use_first_bubble_format(request):
        composed = compose_first_bubble_answer(
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
            direct_answers=answer_parts.direct_answers,
        )
    else:
        composed = compose_followup_answer(
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

    # fix_v7 §3c — cross-topic content gate. Runs on the assembled template
    # BEFORE the polish LLM ever sees it; drops bullets that cite norms
    # outside the primary topic's allowlist
    # (`config/topic_norm_allowlist.json`). The gate is a no-op when the
    # primary topic has no entry, so the worst-case is "no behavior change".
    # `LIA_TOPIC_GATE_MODE=off` short-circuits without removing the config.
    filtered, _gate_diag = filter_template_bullets(
        composed,
        primary_topic=request.topic,
        secondary_topics=tuple(request.secondary_topics or ()),
    )

    # v25 P3 — municipal tax routing (G10). When the question is about ICA /
    # reteICA in a Colombian municipality and the corpus did not surface
    # municipal-level evidence, prepend a deterministic pointer block so the
    # accountant knows WHICH Acuerdo / Decreto Distrital to consult.
    try:
        from .municipal_tax_routing import (
            detect_municipal_context as _mt_detect,
            municipal_pointer_block as _mt_block,
            routing_enabled as _mt_enabled,
        )
        if _mt_enabled():
            hint = _mt_detect(getattr(request, "message", "") or "")
            if hint.detected:
                pointer = _mt_block(hint)
                if pointer:
                    filtered = pointer + "\n\n" + filtered
    except Exception:  # noqa: BLE001 - routing must never raise into composer
        pass

    return filtered

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
