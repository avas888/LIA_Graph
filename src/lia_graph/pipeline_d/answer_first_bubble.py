from __future__ import annotations

import re

from ..pipeline_c.contracts import PipelineCRequest
from .answer_historical_recap import build_historical_recap_lines
from .answer_inline_anchors import PreparedAnswerLine, prepare_first_bubble_lines
from .answer_policy import (
    FIRST_BUBBLE_RISK_LIMIT,
    FIRST_BUBBLE_ROUTE_LIMIT,
    FIRST_BUBBLE_SUPPORT_LIMIT,
    PLANNING_FIRST_BUBBLE_CHECKLIST_LIMIT,
    PLANNING_FIRST_BUBBLE_CRITERIA_LIMIT,
    PLANNING_FIRST_BUBBLE_SETUP_LIMIT,
    PLANNING_FIRST_BUBBLE_STRATEGY_LIMIT,
    build_tax_planning_first_bubble_sources,
)
from .answer_shared import (
    has_explicit_change_intent,
    is_recent_ag_period,
    normalize_text,
    render_bullet_section,
)
from .contracts import GraphEvidenceItem, GraphSupportDocument
from .planner import _looks_like_tax_planning_case


def compose_first_bubble_answer(
    *,
    request: PipelineCRequest,
    answer_mode: str,
    planner_query_mode: str,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
    reforms: tuple[GraphEvidenceItem, ...],
    support_documents: tuple[GraphSupportDocument, ...],
    article_insights: dict[str, tuple[str, ...]],
    support_insights: dict[str, tuple[str, ...]],
    recommendations: tuple[str, ...],
    procedure: tuple[str, ...],
    paperwork: tuple[str, ...],
    precautions: tuple[str, ...],
    direct_answers: tuple[tuple[str, tuple[str, ...]], ...] = (),
) -> str:
    sections: list[str] = []
    normalized_message = normalize_text(request.message)
    requested_period_label = str(temporal_context.get("requested_period_label") or "").strip()
    if _looks_like_tax_planning_case(normalized_message):
        planning_answer = _compose_tax_planning_first_bubble_answer(
            temporal_context=temporal_context,
            primary_articles=primary_articles,
            connected_articles=connected_articles,
            support_documents=support_documents,
            article_insights=article_insights,
            support_insights=support_insights,
        )
        if planning_answer:
            return planning_answer

    route_source = _interleave_lines(recommendations, procedure)
    if requested_period_label and not is_recent_ag_period(requested_period_label):
        route_source = (
            f"Trabaja el caso sobre {requested_period_label}; valida que base, porcentaje y soportes correspondan a esa vigencia.",
            *route_source,
        )
    if (
        bool(temporal_context.get("historical_query_intent"))
        or planner_query_mode in {"reform_chain", "historical_reform_chain", "historical_graph_research"}
        or has_explicit_change_intent(normalized_message)
    ):
        route_source = tuple(
            line
            for line in route_source
            if "vigente hoy" not in normalize_text(line)
        )

    route_lines = prepare_first_bubble_lines(
        route_source,
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        limit=FIRST_BUBBLE_ROUTE_LIMIT,
    )
    risk_lines = prepare_first_bubble_lines(
        precautions,
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        limit=FIRST_BUBBLE_RISK_LIMIT,
    )
    support_lines = prepare_first_bubble_lines(
        paperwork,
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        limit=FIRST_BUBBLE_SUPPORT_LIMIT,
    )
    recap_lines = build_historical_recap_lines(
        request=request,
        planner_query_mode=planner_query_mode,
        temporal_context=temporal_context,
        primary_articles=primary_articles,
        reforms=reforms,
    )

    if direct_answers:
        sections.append(_render_direct_answers_section(direct_answers))
    if route_lines:
        sections.append(render_prepared_section("Ruta sugerida", route_lines, numbered=True))
    if risk_lines:
        sections.append(render_prepared_section("Riesgos y condiciones", risk_lines))
    if support_lines:
        sections.append(render_prepared_section("Soportes clave", support_lines))
    if recap_lines:
        sections.append(render_bullet_section("Recap histórico", recap_lines))

    substantive_sections = [s for s in sections if s and len(s.strip()) > 80]
    if (
        len(substantive_sections) < 2
        and len(primary_articles) >= 2
        and not direct_answers
        and answer_mode == "graph_native"
    ):
        sub_questions = re.findall(r"¿[^?]+\?", request.message or "")
        if sub_questions:
            bullets = [f"- **{q.strip()}**" for q in sub_questions]
        else:
            bullets = [f"- **{(request.message or '').strip()}**"]
        return "**Respuestas directas**\n" + "\n".join(bullets)

    if not sections:
        lead = "Con la evidencia disponible todavía no alcanzo una recomendación operativa suficientemente confiable."
        if answer_mode == "graph_native_partial":
            lead = (
                "Usa esta salida solo como orientación inicial y confirma el expediente antes de convertirla en instrucción cerrada para el cliente."
            )
        sections.append(lead)
    return "\n\n".join(section for section in sections if section.strip())


def render_prepared_section(
    title: str,
    lines: tuple[PreparedAnswerLine, ...],
    *,
    numbered: bool = False,
) -> str:
    prefix = "{idx}. " if numbered else "- "
    body: list[str] = []
    for idx, line in enumerate(lines, start=1):
        marker = prefix.format(idx=idx)
        body.append(f"{marker}{line.text}")
    return f"**{title}**\n" + "\n".join(body)


def _render_direct_answers_section(
    direct_answers: tuple[tuple[str, tuple[str, ...]], ...],
) -> str:
    lines: list[str] = ["**Respuestas directas**"]
    for question, bullets in direct_answers:
        lines.append(f"- **{question}**")
        for bullet in bullets:
            lines.append(f"  - {bullet}")
    return "\n".join(lines)


def _compose_tax_planning_first_bubble_answer(
    *,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
    support_documents: tuple[GraphSupportDocument, ...],
    article_insights: dict[str, tuple[str, ...]],
    support_insights: dict[str, tuple[str, ...]],
) -> str:
    sections: list[str] = []
    period_label = str(temporal_context.get("requested_period_label") or "").strip() or "el AG consultado"
    support_signal = normalize_text(
        " ".join(
            (
                *(str(doc.title_hint or "") for doc in support_documents),
                *(line for bucket in support_insights.values() for line in bucket),
                *(line for bucket in article_insights.values() for line in bucket),
            )
        )
    )
    policy_sources = build_tax_planning_first_bubble_sources(
        period_label=period_label,
        support_signal=support_signal,
    )

    how_i_would_work_it = prepare_first_bubble_lines(
        policy_sources["setup"],
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        limit=PLANNING_FIRST_BUBBLE_SETUP_LIMIT,
    )
    strategy_lines = prepare_first_bubble_lines(
        policy_sources["strategy"],
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        limit=PLANNING_FIRST_BUBBLE_STRATEGY_LIMIT,
    )
    criteria_lines = prepare_first_bubble_lines(
        policy_sources["criteria"],
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        limit=PLANNING_FIRST_BUBBLE_CRITERIA_LIMIT,
    )
    checklist_lines = prepare_first_bubble_lines(
        policy_sources["checklist"],
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        limit=PLANNING_FIRST_BUBBLE_CHECKLIST_LIMIT,
    )

    if how_i_would_work_it:
        sections.append(render_prepared_section("Cómo La Trabajaría", how_i_would_work_it))
    if strategy_lines:
        sections.append(render_prepared_section("Estrategias Legítimas A Modelar", strategy_lines))
    if criteria_lines:
        sections.append(render_prepared_section("Qué Mira DIAN Y La Jurisprudencia", criteria_lines))
    if checklist_lines:
        sections.append(render_prepared_section("Papeles De Trabajo", checklist_lines))
    return "\n\n".join(section for section in sections if section.strip())


def _interleave_lines(left: tuple[str, ...], right: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    max_len = max(len(left), len(right))
    for index in range(max_len):
        if index < len(left):
            merged.append(left[index])
        if index < len(right):
            merged.append(right[index])
    return tuple(merged)


__all__ = [
    "PreparedAnswerLine",
    "compose_first_bubble_answer",
]
