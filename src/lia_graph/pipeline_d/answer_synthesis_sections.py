from __future__ import annotations

import re

from ..pipeline_c.contracts import PipelineCRequest
from .answer_shared import (
    anchor_query_tokens,
    append_unique,
    extract_change_mentions,
    line_has_legal_reference,
    normalize_text,
    published_context_lines,
    should_surface_change_context,
)
from .contracts import GraphEvidenceItem
from .answer_synthesis_helpers import (
    build_followup_focus,
    classify_followup_question_shape,
    clean_title,
    extend_from_guidance,
    extend_from_support_insights,
    fallback_procedure_step,
    fallback_recommendation,
    is_loss_compensation_case,
    is_refund_balance_case,
    looks_like_tax_treatment_question,
    pepper_legal_anchor_into_procedure,
    should_surface_connected_anchor,
    tax_treatment_subject_label,
)


def build_recommendations(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    lines: list[str] = []
    normalized_message = normalize_text(request.message)
    extend_from_support_insights(
        lines,
        _build_direct_position_lines(
            request=request,
            temporal_context=temporal_context,
            primary_articles=primary_articles,
        ),
    )
    if is_refund_balance_case(normalized_message):
        append_unique(
            lines,
            "Ordena el caso como devolución / compensación de saldo a favor y no como un problema principal de facturación electrónica.",
        )
    if is_loss_compensation_case(normalized_message):
        append_unique(
            lines,
            "El régimen base del art. 147 ET es que la sociedad compensa la pérdida fiscal contra la renta líquida ordinaria de años siguientes; no es un trámite de devolución o compensación de saldo a favor ante la DIAN.",
        )
        if any(
            marker in normalized_message
            for marker in (
                "firmeza",
                "termino de firmeza",
                "término de firmeza",
                "termino de revision",
                "término de revisión",
                "revision",
                "revisión",
                "beneficio de auditoria",
                "beneficio de auditoría",
            )
        ):
            append_unique(
                lines,
                "Si la declaración origina o compensa pérdidas, léela con la regla especial de revisión de 6 años y solo después analiza si hay beneficio de auditoría u otra firmeza especial.",
            )
    if bool(temporal_context.get("historical_query_intent")):
        cutoff_date = str(temporal_context.get("cutoff_date") or "").strip()
        if cutoff_date:
            append_unique(
                lines,
                f"Define primero la fecha de análisis: para este caso conviene trabajar con corte {cutoff_date} antes de cerrar una posición para el cliente.",
            )
    extend_from_guidance(lines, "recommendation", primary_articles)
    extend_from_guidance(lines, "recommendation", connected_articles)
    if not lines:
        fallback = fallback_recommendation(
            request=request,
            primary_articles=primary_articles,
        )
        if fallback:
            append_unique(lines, fallback)
    return tuple(lines[:3])


def build_procedure_steps(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
    article_insights: dict[str, tuple[str, ...]],
    support_insights: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    steps: list[str] = []
    normalized_message = normalize_text(request.message)
    if is_loss_compensation_case(normalized_message):
        append_unique(
            steps,
            "Para pérdidas sujetas al régimen vigente, la regla operativa es 12 períodos gravables y sin tope porcentual anual; revisa el art. 290 ET solo si el saldo viene de años anteriores bajo régimen de transición.",
        )
        append_unique(
            steps,
            "Arma un cuadro por año de origen, régimen aplicable, fecha de expiración, saldo pendiente y renta líquida ordinaria disponible antes de decidir cuánto absorber.",
        )
        append_unique(
            steps,
            "Compensa solo contra renta líquida ordinaria del período; lo que no uses en ese año se sigue arrastrando hasta el vencimiento de su propio término.",
        )
    extend_from_guidance(steps, "procedure", primary_articles)
    extend_from_support_insights(steps, article_insights.get("procedure", ()))
    extend_from_support_insights(steps, support_insights.get("procedure", ()))
    if bool(temporal_context.get("historical_query_intent")):
        cutoff_date = str(temporal_context.get("cutoff_date") or "").strip()
        if cutoff_date:
            append_unique(
                steps,
                f"Separa en tu análisis la versión vigente hasta {cutoff_date} de cualquier cambio posterior para no mezclar reglas.",
            )
    if not steps:
        fallback = fallback_procedure_step(
            request=request,
            primary_articles=primary_articles,
        )
        if fallback:
            append_unique(steps, fallback)
    anchored_steps = pepper_legal_anchor_into_procedure(steps, primary_articles)
    return tuple(anchored_steps[:6])


def build_paperwork_lines(
    *,
    request: PipelineCRequest,
    article_insights: dict[str, tuple[str, ...]],
    support_insights: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    lines: list[str] = []
    normalized_message = normalize_text(request.message)
    if is_loss_compensation_case(normalized_message):
        append_unique(
            lines,
            "Deja un papel de trabajo por vigencia con saldo inicial de la pérdida, compensación usada en el año y saldo final arrastrable.",
        )
        append_unique(
            lines,
            "Conserva por al menos 6 años la declaración de origen, F.110, F.2516, conciliación fiscal y soportes que expliquen el nacimiento de la pérdida.",
        )
    extend_from_support_insights(lines, article_insights.get("paperwork", ()))
    extend_from_support_insights(lines, support_insights.get("paperwork", ()))
    return tuple(lines[:4])


def build_legal_anchor_lines(
    *,
    request: PipelineCRequest,
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    lines: list[str] = []
    normalized_message = normalize_text(request.message)
    query_tokens = anchor_query_tokens(normalized_message)
    for item in primary_articles[:5]:
        append_unique(lines, f"Art. {item.node_key} — {clean_title(item.title)}")
    for item in connected_articles[:2]:
        if not should_surface_connected_anchor(
            title=item.title,
            normalized_message=normalized_message,
            query_tokens=query_tokens,
        ):
            continue
        append_unique(lines, f"Art. {item.node_key} — {clean_title(item.title)}")
    return tuple(lines)


def build_context_lines(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    planner_query_mode: str,
    primary_articles: tuple[GraphEvidenceItem, ...],
    reforms: tuple[GraphEvidenceItem, ...],
    article_insights: dict[str, tuple[str, ...]],
    support_insights: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    lines: list[str] = []
    cutoff_date = str(temporal_context.get("cutoff_date") or "").strip()
    requested_period_label = str(temporal_context.get("requested_period_label") or "").strip()
    allow_change_context = should_surface_change_context(
        normalized_message=normalize_text(request.message),
        temporal_context=temporal_context,
        planner_query_mode=planner_query_mode,
        requested_period_label=requested_period_label,
    )
    anchor_labels = tuple(
        str(item)
        for item in (temporal_context.get("anchor_reform_labels") or ())
        if str(item).strip()
    )
    if cutoff_date:
        if anchor_labels:
            append_unique(
                lines,
                f"Para este análisis conviene tomar como referencia temporal {cutoff_date} con apoyo en {anchor_labels[0]}.",
            )
        else:
            append_unique(
                lines,
                f"Para este análisis conviene trabajar con corte temporal {cutoff_date}.",
            )
    elif requested_period_label:
        append_unique(
            lines,
            f"El caso viene planteado para {requested_period_label}; valida que plazos, declaración base y soportes correspondan exactamente a ese período.",
        )
    modifications = extract_change_mentions(primary_articles, reforms)
    if modifications and allow_change_context:
        append_unique(
            lines,
            "Las normas principales de este tema muestran cambios o reformas relevantes en: "
            + ", ".join(modifications[:3])
            + ".",
        )
    extend_from_support_insights(
        lines,
        published_context_lines(
            article_insights.get("context", ()),
            allow_change_context=allow_change_context,
        ),
    )
    extend_from_support_insights(
        lines,
        published_context_lines(
            support_insights.get("context", ()),
            allow_change_context=allow_change_context,
        ),
    )
    if planner_query_mode == "historical_reform_chain":
        append_unique(
            lines,
            "La lectura histórica debe hacerse sobre el texto previo a la reforma y no sobre la versión vigente hoy.",
        )
    return tuple(lines[:4])


def build_precautions(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
    answer_mode: str,
    article_insights: dict[str, tuple[str, ...]],
    support_insights: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    lines: list[str] = []
    extend_from_guidance(lines, "precaution", primary_articles)
    extend_from_guidance(lines, "precaution", connected_articles)
    extend_from_support_insights(lines, article_insights.get("precaution", ()))
    extend_from_support_insights(lines, support_insights.get("precaution", ()))
    normalized_message = normalize_text(request.message)
    if is_refund_balance_case(normalized_message):
        append_unique(
            lines,
            "Que el cliente esté al día en facturación electrónica no cambia por sí solo la naturaleza del trámite de devolución; úsalo solo como condición de cumplimiento complementaria.",
        )
    if is_loss_compensation_case(normalized_message):
        append_unique(
            lines,
            "No mezcles compensación de pérdidas fiscales con compensación de saldos a favor: comparten la palabra 'compensación', pero jurídicamente no son el mismo problema del cliente.",
        )
    if bool(temporal_context.get("historical_query_intent")):
        append_unique(
            lines,
            "Si vas a usar esta respuesta para un cierre actual, confirma que el caso no haya quedado bajo una versión normativa posterior.",
        )
    if answer_mode == "graph_native_partial":
        append_unique(
            lines,
            "La cobertura quedó parcial; valida el expediente antes de convertir esta salida en instrucción definitiva para el cliente.",
        )
    return tuple(lines[:4])


def build_opportunities(
    *,
    request: PipelineCRequest,
    primary_articles: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    lines: list[str] = []
    extend_from_guidance(lines, "opportunity", primary_articles)
    normalized_message = normalize_text(request.message)
    if is_refund_balance_case(normalized_message):
        append_unique(
            lines,
            "Si el cliente tiene obligaciones pendientes, compara devolución frente a compensación con apoyo en el art. 815 ET antes de definir la salida de caja.",
        )
    return tuple(lines[:2])


def build_followup_resolution(
    *,
    request: PipelineCRequest,
    recommendations: tuple[str, ...],
    procedure: tuple[str, ...],
    paperwork: tuple[str, ...],
    precautions: tuple[str, ...],
    opportunities: tuple[str, ...],
    context_lines: tuple[str, ...],
) -> tuple[str, str, str]:
    followup_focus = build_followup_focus(request.message)
    normalized_shape_message = normalize_text(followup_focus.shape_text)
    normalized_ranking_message = normalize_text(followup_focus.ranking_text or followup_focus.shape_text)
    question_shape = classify_followup_question_shape(normalized_shape_message)
    direct_answer = _select_followup_direct_answer(
        question_shape=question_shape,
        normalized_message=normalized_ranking_message,
        raw_message=request.message,
        avoid_echoed_lines=followup_focus.has_embedded_answer_echo,
        recommendations=recommendations,
        procedure=procedure,
        precautions=precautions,
        opportunities=opportunities,
        context_lines=context_lines,
    )
    seen = {normalize_text(direct_answer)} if direct_answer else set()
    main_exception = _select_followup_main_exception(
        question_shape=question_shape,
        normalized_message=normalized_ranking_message,
        raw_message=request.message,
        avoid_echoed_lines=followup_focus.has_embedded_answer_echo,
        procedure=procedure,
        precautions=precautions,
        context_lines=context_lines,
        recommendations=recommendations,
        seen=seen,
    )
    if main_exception:
        seen.add(normalize_text(main_exception))
    practical_next_step = _select_followup_next_step(
        normalized_message=normalized_shape_message,
        raw_message=request.message,
        avoid_echoed_lines=followup_focus.has_embedded_answer_echo,
        procedure=procedure,
        paperwork=paperwork,
        recommendations=recommendations,
        seen=seen,
    )
    return direct_answer, main_exception, practical_next_step


def _build_direct_position_lines(
    *,
    request: PipelineCRequest,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    if bool(temporal_context.get("historical_query_intent")):
        return ()
    normalized_message = normalize_text(request.message)
    primary_keys = {
        str(item.node_key).strip()
        for item in primary_articles
        if str(item.node_key or "").strip()
    }
    lines: list[str] = []
    if "115" in primary_keys and looks_like_tax_treatment_question(normalized_message):
        subject = tax_treatment_subject_label(normalized_message)
        append_unique(
            lines,
            f"Para el tratamiento en renta de {subject}, revísalo primero bajo el art. 115 ET: no lo lleves como una deducción genérica y evita tomar el mismo valor simultáneamente como descuento tributario y como costo o gasto.",
        )
    return tuple(lines[:2])


def _select_followup_direct_answer(
    *,
    question_shape: str,
    normalized_message: str,
    raw_message: str,
    avoid_echoed_lines: bool,
    recommendations: tuple[str, ...],
    procedure: tuple[str, ...],
    precautions: tuple[str, ...],
    opportunities: tuple[str, ...],
    context_lines: tuple[str, ...],
) -> str:
    ranked: list[tuple[float, str]] = []
    ranked.extend(
        _score_followup_resolution_lines(
            question_shape=question_shape,
            normalized_message=normalized_message,
            lines=recommendations,
            source="recommendation",
        )
    )
    ranked.extend(
        _score_followup_resolution_lines(
            question_shape=question_shape,
            normalized_message=normalized_message,
            lines=procedure,
            source="procedure",
        )
    )
    ranked.extend(
        _score_followup_resolution_lines(
            question_shape=question_shape,
            normalized_message=normalized_message,
            lines=opportunities,
            source="opportunity",
        )
    )
    ranked.extend(
        _score_followup_resolution_lines(
            question_shape=question_shape,
            normalized_message=normalized_message,
            lines=precautions,
            source="precaution",
        )
    )
    ranked.extend(
        _score_followup_resolution_lines(
            question_shape=question_shape,
            normalized_message=normalized_message,
            lines=context_lines,
            source="context",
        )
    )
    if not ranked:
        return ""
    sorted_ranked = sorted(ranked, key=lambda item: (-item[0], item[1]))
    for _score, line in sorted_ranked:
        if avoid_echoed_lines and _line_is_echoed_in_message(line, raw_message):
            continue
        return line
    return sorted_ranked[0][1]


def _select_followup_main_exception(
    *,
    question_shape: str,
    normalized_message: str,
    raw_message: str,
    avoid_echoed_lines: bool,
    procedure: tuple[str, ...],
    precautions: tuple[str, ...],
    context_lines: tuple[str, ...],
    recommendations: tuple[str, ...],
    seen: set[str],
) -> str:
    ranked: list[tuple[float, str]] = []
    for source, lines, base in (
        ("procedure", procedure, 4.1),
        ("precaution", precautions, 4.0),
        ("context", context_lines, 3.6),
        ("recommendation", recommendations, 3.2),
    ):
        for index, raw_line in enumerate(lines):
            line = str(raw_line or "").strip()
            normalized_line = normalize_text(line)
            if not line or normalized_line in seen:
                continue
            if avoid_echoed_lines and _line_is_echoed_in_message(line, raw_message):
                continue
            score = base - (index * 0.12)
            if _looks_like_exception_line(normalized_line):
                score += 2.2
            if question_shape == "exception":
                score += 0.9
            if any(token in normalized_line for token in ("transicion", "histor", "vigencia", "reforma")):
                score += 0.45
            if source == "context" and question_shape not in {"deadline", "amount_limit", "exception"}:
                score -= 0.35
            ranked.append((score, line))
    if not ranked:
        return ""
    best_score, best_line = max(ranked, key=lambda item: (item[0], item[1]))
    return best_line if best_score >= 4.2 else ""


def _select_followup_next_step(
    *,
    normalized_message: str,
    raw_message: str,
    avoid_echoed_lines: bool,
    procedure: tuple[str, ...],
    paperwork: tuple[str, ...],
    recommendations: tuple[str, ...],
    seen: set[str],
) -> str:
    ranked: list[tuple[float, str]] = []
    for source, lines, base in (
        ("procedure", procedure, 4.2),
        ("paperwork", paperwork, 4.0),
        ("recommendation", recommendations, 2.9),
    ):
        for index, raw_line in enumerate(lines):
            line = str(raw_line or "").strip()
            normalized_line = normalize_text(line)
            if not line or normalized_line in seen:
                continue
            if avoid_echoed_lines and _line_is_echoed_in_message(line, raw_message):
                continue
            score = base - (index * 0.12)
            if _looks_like_action_step(normalized_line):
                score += 1.9
            if any(marker in normalized_message for marker in ("que hago", "que reviso", "checklist", "requisito")):
                score += 0.5
            ranked.append((score, line))
    if not ranked:
        return ""
    return max(ranked, key=lambda item: (item[0], item[1]))[1]


def _score_followup_resolution_lines(
    *,
    question_shape: str,
    normalized_message: str,
    lines: tuple[str, ...],
    source: str,
) -> list[tuple[float, str]]:
    base_weight = {
        "recommendation": 4.2,
        "procedure": 4.0,
        "opportunity": 3.0,
        "precaution": 2.8,
        "context": 2.4,
    }.get(source, 2.5)
    query_tokens = anchor_query_tokens(normalized_message)
    ranked: list[tuple[float, str]] = []
    for index, raw_line in enumerate(lines):
        line = str(raw_line or "").strip()
        if not line:
            continue
        normalized_line = normalize_text(line)
        score = base_weight - (index * 0.14)
        overlap = len(query_tokens.intersection(anchor_query_tokens(normalized_line)))
        score += float(overlap) * 1.4
        if question_shape == "amount_limit":
            if any(marker in normalized_line for marker in ("limite", "tope", "maximo", "porcentaje", "anual", "periodo", "ano", "anos", "mes", "dia", "plazo")):
                score += 2.1
            if any(marker in normalized_line for marker in ("sin tope", "sin limite", "sin tope porcentual", "sin tope anual")):
                score += 1.1
        elif question_shape == "deadline":
            if any(marker in normalized_line for marker in ("plazo", "termino", "dias", "meses", "anos", "antes de", "dentro de", "venc")):
                score += 2.0
        elif question_shape == "categorical":
            if any(marker in normalized_line for marker in ("no ", "sin ", "si ", "procede", "aplica", "puede", "corresponde")):
                score += 1.2
        elif question_shape == "exception":
            if _looks_like_exception_line(normalized_line):
                score += 1.7
        if _looks_like_exception_line(normalized_line) and question_shape in {"categorical", "amount_limit", "deadline"}:
            score -= 1.1
        if source == "precaution" and question_shape in {"categorical", "amount_limit", "deadline"}:
            score -= 0.45
        if line_has_legal_reference(line):
            score += 0.2
        ranked.append((score, line))
    return ranked


def _looks_like_exception_line(normalized_line: str) -> bool:
    text = str(normalized_line or "")
    return text.startswith(("si ", "solo si", "excepto", "salvo", "cuando ", "bajo ")) or any(
        marker in text
        for marker in (
            " regimen de transicion",
            " regimen congelado",
            " si el ",
            " si la ",
            " si viene ",
            " siempre que ",
        )
    )


def _looks_like_action_step(normalized_line: str) -> bool:
    text = str(normalized_line or "")
    return text.startswith(
        (
            "arma ",
            "haz ",
            "define ",
            "revisa ",
            "valida ",
            "confirma ",
            "separa ",
            "ordena ",
            "conserva ",
            "controla ",
            "liquida ",
            "compensa ",
            "deja ",
        )
    )


def _line_is_echoed_in_message(line: str, raw_message: str) -> bool:
    normalized_line = normalize_text(
        re.sub(
            r"\s+\(arts?\.[^)]+\)\.?$",
            "",
            str(line or ""),
            flags=re.IGNORECASE,
        )
    ).strip(" .")
    normalized_message = normalize_text(raw_message)
    if not normalized_line or len(normalized_line.split()) < 6:
        return False
    return normalized_line in normalized_message


__all__ = [
    "build_context_lines",
    "build_followup_resolution",
    "build_legal_anchor_lines",
    "build_opportunities",
    "build_paperwork_lines",
    "build_precautions",
    "build_procedure_steps",
    "build_recommendations",
]
