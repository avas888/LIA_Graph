from __future__ import annotations

import re

from ..pipeline_c.contracts import PipelineCRequest
from .answer_inline_anchors import (
    PreparedAnswerLine,
    line_identity_key,
    prepare_first_bubble_lines,
)
from .answer_shared import (
    anchor_query_tokens,
    line_has_legal_reference,
    normalize_text,
    render_bullet_section,
    render_numbered_section,
)
from .answer_synthesis_helpers import build_followup_focus, classify_followup_question_shape
from .contracts import GraphEvidenceItem

_FOLLOWUP_DRILLDOWN_MARKERS = (
    "cuentame mas",
    "cuentame mejor",
    "hablame mas",
    "explicame",
    "profundiza",
    "desarrolla",
    "amplia esto",
    "amplia ese punto",
    "sobre ese punto",
    "sobre esto",
    "de esto",
    "de eso",
    "ese punto",
    "este punto",
    "a que te refieres",
    "que significa eso",
    "como opera eso",
    "como funciona eso",
)
_FOLLOWUP_PAPERWORK_MARKERS = (
    "soporte",
    "soportes",
    "papeles",
    "papeles de trabajo",
    "documento",
    "documentos",
    "anexo",
    "anexos",
    "formato",
    "formulario",
    "certificacion",
    "certificado",
    "expediente",
)
_FOLLOWUP_CONTEXT_MARKERS = (
    "vigencia",
    "histor",
    "cambio",
    "modific",
    "reforma",
)
_FOLLOWUP_OPTION_MARKERS = (
    "conviene",
    "mejor",
    "alternativa",
    "devolucion",
    "compensacion",
    "caja",
)
_FOLLOWUP_EFFECT_MARKERS = (
    "firmeza",
    "revision",
    "termino",
    "reinicia",
    "efecta",
    "impacta",
    "plazo",
    "precaucion",
    "riesgo",
)


def compose_followup_answer(
    *,
    request: PipelineCRequest,
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
    recommendations: tuple[str, ...],
    procedure: tuple[str, ...],
    paperwork: tuple[str, ...],
    legal_anchor: tuple[str, ...],
    precautions: tuple[str, ...],
    opportunities: tuple[str, ...],
    context_lines: tuple[str, ...],
    followup_direct_answer: str,
    followup_main_exception: str,
    followup_practical_next_step: str,
) -> str:
    followup_focus = build_followup_focus(request.message)
    question_shape = classify_followup_question_shape(normalize_text(followup_focus.shape_text))
    if _looks_like_drilldown_followup(request, focus_text=followup_focus.shape_text):
        if question_shape in {"categorical", "amount_limit", "deadline", "exception"}:
            resolved = _compose_resolved_followup_answer(
                request=request,
                question_shape=question_shape,
                primary_articles=primary_articles,
                connected_articles=connected_articles,
                direct_answer=followup_direct_answer,
                main_exception=followup_main_exception,
                practical_next_step=followup_practical_next_step,
            )
            if resolved:
                return resolved
        focused = _compose_focused_followup_answer(
            request=request,
            primary_articles=primary_articles,
            connected_articles=connected_articles,
            recommendations=recommendations,
            procedure=procedure,
            legal_anchor=legal_anchor,
            precautions=precautions,
            opportunities=opportunities,
        )
        if focused:
            return focused
    return _compose_expanded_followup_answer(
        request=request,
        recommendations=recommendations,
        procedure=procedure,
        paperwork=paperwork,
        legal_anchor=legal_anchor,
        precautions=precautions,
        opportunities=opportunities,
        context_lines=context_lines,
    )


def _compose_resolved_followup_answer(
    *,
    request: PipelineCRequest,
    question_shape: str,
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
    direct_answer: str,
    main_exception: str,
    practical_next_step: str,
) -> str:
    parts: list[str] = []
    verdict_line = _rewrite_followup_verdict_line(
        value=direct_answer,
        question_shape=question_shape,
    )
    verdict_lines = prepare_first_bubble_lines(
        (verdict_line,) if verdict_line else (),
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        limit=1,
    )
    if verdict_lines:
        parts.append(verdict_lines[0].text)

    exception_line = _rewrite_followup_exception_line(main_exception)
    exception_lines = prepare_first_bubble_lines(
        (exception_line,) if exception_line else (),
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        limit=1,
    )
    if exception_lines:
        parts.append(exception_lines[0].text)

    next_step_line = _rewrite_followup_next_step_line(practical_next_step)
    next_step_lines = prepare_first_bubble_lines(
        (next_step_line,) if next_step_line else (),
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        limit=1,
    )
    if next_step_lines:
        parts.append(next_step_lines[0].text)

    return "\n\n".join(part for part in parts if part.strip())


def _compose_focused_followup_answer(
    *,
    request: PipelineCRequest,
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
    recommendations: tuple[str, ...],
    procedure: tuple[str, ...],
    legal_anchor: tuple[str, ...],
    precautions: tuple[str, ...],
    opportunities: tuple[str, ...],
) -> str:
    sections: list[str] = []
    direct_raw = _take_ranked_lines(
        request=request,
        primary_articles=primary_articles,
        recommendation_lines=recommendations,
        procedure_lines=procedure,
        precaution_lines=precautions,
        opportunity_lines=opportunities,
        limit=2,
    )
    direct_raw = tuple(_rewrite_direct_followup_line(line) for line in direct_raw)
    direct_lines = prepare_first_bubble_lines(
        direct_raw,
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        limit=2,
    )
    seen_keys = {_followup_identity_key(line) for line in direct_raw}
    if direct_lines:
        sections.append("\n\n".join(line.text for line in direct_lines if line.text))

    detail_raw = _take_ranked_lines(
        request=request,
        primary_articles=primary_articles,
        recommendation_lines=recommendations,
        procedure_lines=procedure,
        precaution_lines=(),
        opportunity_lines=(),
        limit=3,
        seen_keys=seen_keys,
    )
    detail_lines = prepare_first_bubble_lines(
        detail_raw,
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        limit=3,
    )
    seen_keys.update(_followup_identity_key(line) for line in detail_raw)
    if detail_lines:
        sections.append(_render_prepared_section("En concreto", detail_lines, numbered=True))

    risk_raw = _take_ranked_lines(
        request=request,
        primary_articles=primary_articles,
        recommendation_lines=(),
        procedure_lines=(),
        precaution_lines=precautions,
        opportunity_lines=(),
        limit=2,
        seen_keys=seen_keys,
    )
    risk_lines = prepare_first_bubble_lines(
        risk_raw,
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        limit=2,
    )
    if risk_lines:
        sections.append(_render_prepared_section("Precauciones", risk_lines))

    if legal_anchor:
        sections.append(render_bullet_section("Anclaje Legal", legal_anchor[:2]))

    return "\n\n".join(section for section in sections if section.strip())


def _compose_expanded_followup_answer(
    *,
    request: PipelineCRequest,
    recommendations: tuple[str, ...],
    procedure: tuple[str, ...],
    paperwork: tuple[str, ...],
    legal_anchor: tuple[str, ...],
    precautions: tuple[str, ...],
    opportunities: tuple[str, ...],
    context_lines: tuple[str, ...],
) -> str:
    normalized_message = normalize_text(request.message)
    sections: list[str] = []

    if recommendations:
        sections.append(render_bullet_section("Qué Haría Primero", recommendations[:2]))
    if procedure:
        sections.append(render_numbered_section("Procedimiento Sugerido", procedure[:4]))
    if legal_anchor:
        sections.append(render_bullet_section("Anclaje Legal", legal_anchor[:3]))
    if precautions:
        sections.append(render_bullet_section("Precauciones", precautions[:3]))
    if paperwork and _followup_requests_paperwork(normalized_message):
        sections.append(render_bullet_section("Soportes y Papeles de Trabajo", paperwork[:3]))
    if opportunities and _followup_requests_options(normalized_message):
        sections.append(render_bullet_section("Oportunidades", opportunities[:2]))
    if context_lines and _followup_requests_context(normalized_message):
        sections.append(render_bullet_section("Cambios y Contexto Legal", context_lines[:2]))
    if not sections and paperwork:
        sections.append(render_bullet_section("Soportes y Papeles de Trabajo", paperwork[:2]))
    return "\n\n".join(section for section in sections if section.strip())
def _looks_like_drilldown_followup(
    request: PipelineCRequest,
    *,
    focus_text: str | None = None,
) -> bool:
    normalized_message = normalize_text(focus_text or request.message)
    if not normalized_message:
        return False
    if not _is_followup_turn(request):
        return False
    if any(marker in normalized_message for marker in _FOLLOWUP_DRILLDOWN_MARKERS):
        return True
    token_count = len([token for token in normalized_message.split() if token])
    if ":" in str(focus_text or request.message or "") and token_count <= 40:
        return True
    return token_count <= 22


def _is_followup_turn(request: PipelineCRequest) -> bool:
    state = request.conversation_state
    if isinstance(state, dict) and int(state.get("turn_count") or 0) > 0:
        return True
    return bool(str(request.conversation_context or "").strip())


def _take_ranked_lines(
    *,
    request: PipelineCRequest,
    primary_articles: tuple[GraphEvidenceItem, ...],
    recommendation_lines: tuple[str, ...],
    procedure_lines: tuple[str, ...],
    precaution_lines: tuple[str, ...],
    opportunity_lines: tuple[str, ...],
    limit: int,
    seen_keys: set[str] | None = None,
) -> tuple[str, ...]:
    ranked = _rank_followup_candidates(
        request=request,
        primary_articles=primary_articles,
        recommendation_lines=recommendation_lines,
        procedure_lines=procedure_lines,
        precaution_lines=precaution_lines,
        opportunity_lines=opportunity_lines,
    )
    seen = set(seen_keys or set())
    selected: list[str] = []
    for _score, line in ranked:
        key = _followup_identity_key(line)
        if not key or key in seen:
            continue
        seen.add(key)
        selected.append(line)
        if len(selected) >= limit:
            break
    return tuple(selected)


def _rank_followup_candidates(
    *,
    request: PipelineCRequest,
    primary_articles: tuple[GraphEvidenceItem, ...],
    recommendation_lines: tuple[str, ...],
    procedure_lines: tuple[str, ...],
    precaution_lines: tuple[str, ...],
    opportunity_lines: tuple[str, ...],
) -> list[tuple[float, str]]:
    normalized_message = normalize_text(request.message)
    query_tokens = anchor_query_tokens(normalized_message)
    primary_keys = {
        str(item.node_key).strip().lower()
        for item in primary_articles
        if str(item.node_key or "").strip()
    }
    ranked: list[tuple[float, str]] = []
    ranked.extend(
        _score_section_lines(
            lines=recommendation_lines,
            normalized_message=normalized_message,
            query_tokens=query_tokens,
            primary_keys=primary_keys,
            base_weight=4.2,
        )
    )
    ranked.extend(
        _score_section_lines(
            lines=procedure_lines,
            normalized_message=normalized_message,
            query_tokens=query_tokens,
            primary_keys=primary_keys,
            base_weight=3.9,
        )
    )
    ranked.extend(
        _score_section_lines(
            lines=precaution_lines,
            normalized_message=normalized_message,
            query_tokens=query_tokens,
            primary_keys=primary_keys,
            base_weight=4.0,
        )
    )
    ranked.extend(
        _score_section_lines(
            lines=opportunity_lines,
            normalized_message=normalized_message,
            query_tokens=query_tokens,
            primary_keys=primary_keys,
            base_weight=3.2,
        )
    )
    return sorted(ranked, key=lambda item: (-item[0], item[1]))


def _score_section_lines(
    *,
    lines: tuple[str, ...],
    normalized_message: str,
    query_tokens: set[str],
    primary_keys: set[str],
    base_weight: float,
) -> list[tuple[float, str]]:
    ranked: list[tuple[float, str]] = []
    for index, raw_line in enumerate(lines):
        line = str(raw_line or "").strip()
        if not line:
            continue
        normalized_line = normalize_text(line)
        line_tokens = anchor_query_tokens(normalized_line)
        overlap = len(query_tokens.intersection(line_tokens))
        score = base_weight + (overlap * 1.7) - (index * 0.15)
        if any(marker in normalized_message and marker in normalized_line for marker in _FOLLOWUP_EFFECT_MARKERS):
            score += 0.8
        if any(key and key in normalized_line for key in primary_keys):
            score += 0.35
        if line_has_legal_reference(line):
            score += 0.2
        ranked.append((score, line))
    return ranked


def _followup_requests_paperwork(normalized_message: str) -> bool:
    return any(marker in normalized_message for marker in _FOLLOWUP_PAPERWORK_MARKERS)


def _followup_requests_options(normalized_message: str) -> bool:
    return any(marker in normalized_message for marker in _FOLLOWUP_OPTION_MARKERS)


def _followup_requests_context(normalized_message: str) -> bool:
    return any(marker in normalized_message for marker in _FOLLOWUP_CONTEXT_MARKERS)


def _render_prepared_section(
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


def _rewrite_direct_followup_line(value: str) -> str:
    line = re.sub(r"\s+", " ", str(value or "")).strip()
    if not line:
        return ""
    line = re.sub(r"^Recuerda que\s+", "", line, flags=re.IGNORECASE)
    if line:
        line = line[:1].upper() + line[1:]
    return line


def _followup_identity_key(value: str) -> str:
    return line_identity_key(_rewrite_direct_followup_line(value))


def _rewrite_followup_verdict_line(
    *,
    value: str,
    question_shape: str,
) -> str:
    line = re.sub(r"\s+", " ", str(value or "")).strip()
    if not line:
        return ""
    normalized_line = normalize_text(line)
    stripped = _strip_followup_setup_clause(line)
    if question_shape == "amount_limit":
        if any(marker in normalized_line for marker in ("sin tope", "sin limite", "sin tope porcentual", "sin tope anual")):
            return f"No, no hay un tope o porcentaje anual adicional; {stripped[:1].lower() + stripped[1:]}"
        if any(marker in normalized_line for marker in ("limite temporal", "plazo", "periodo", "anos", "meses", "dias")):
            return f"El límite relevante es temporal; {stripped[:1].lower() + stripped[1:]}"
    if question_shape == "deadline" and any(
        marker in normalized_line for marker in ("plazo", "termino", "dias", "meses", "anos", "antes de", "dentro de")
    ):
        return f"El plazo relevante es este: {stripped[:1].lower() + stripped[1:]}"
    if question_shape == "exception":
        if normalized_line.startswith("solo cambia si "):
            return line
        if normalized_line.startswith("si "):
            return "Sí cambia si " + line[3:].rstrip(".") + "."
        if normalized_line.startswith(("excepto", "salvo")):
            return "Cambia en este escenario: " + line[:1].lower() + line[1:]
    if question_shape == "categorical":
        if _supports_negative_verdict(normalized_line):
            return f"No, {stripped[:1].lower() + stripped[1:]}"
        if _supports_positive_verdict(normalized_line):
            return f"Sí, {stripped[:1].lower() + stripped[1:]}"
    return line


def _rewrite_followup_exception_line(value: str) -> str:
    line = re.sub(r"\s+", " ", str(value or "")).strip()
    if not line:
        return ""
    normalized_line = normalize_text(line)
    if normalized_line.startswith("si "):
        return "Solo cambia si " + line[3:].rstrip(".") + "."
    if normalized_line.startswith("cuando "):
        return "Ojo con esta excepción: " + line[7:].rstrip(".") + "."
    if normalized_line.startswith(("excepto", "salvo")):
        return "Ojo con esta excepción: " + line[:1].lower() + line[1:]
    return "Ojo con esta excepción: " + line[:1].lower() + line[1:]


def _rewrite_followup_next_step_line(value: str) -> str:
    line = re.sub(r"\s+", " ", str(value or "")).strip()
    if not line:
        return ""
    return "En la práctica, " + line[:1].lower() + line[1:]


def _strip_followup_setup_clause(value: str) -> str:
    line = str(value or "").strip()
    if not line:
        return ""
    match = re.match(r"^([^,]{1,70}),\s+(.+)$", line)
    if not match:
        return line
    lead = normalize_text(match.group(1))
    if any(
        marker in lead
        for marker in (
            "para ",
            "si ",
            "cuando ",
            "respecto de ",
            "en este caso",
            "sobre ",
        )
    ):
        return match.group(2).strip()
    return line


def _supports_negative_verdict(normalized_line: str) -> bool:
    return any(
        marker in normalized_line
        for marker in (
            " no ",
            " no es ",
            " no aplica ",
            " no procede ",
            " sin ",
            " evita ",
        )
    )


def _supports_positive_verdict(normalized_line: str) -> bool:
    return any(
        marker in normalized_line
        for marker in (
            " si aplica ",
            " procede ",
            " aplica ",
            " puede ",
            " corresponde ",
        )
    )


__all__ = [
    "compose_followup_answer",
]
