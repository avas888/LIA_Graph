from __future__ import annotations

from dataclasses import dataclass
import re

from ..pipeline_c.contracts import PipelineCRequest
from .answer_policy import guidance_for_item
from .answer_shared import (
    anchor_query_tokens,
    append_unique,
    line_has_legal_reference,
    normalize_text,
)
from .answer_support import clean_support_line_for_answer
from .contracts import GraphEvidenceItem
from .planner import _looks_like_loss_compensation_case, _looks_like_refund_balance_case

_FOLLOWUP_LIMIT_MARKERS = (
    "limite",
    "tope",
    "maximo",
    "maxima",
    "porcentaje",
    "porcentual",
    "cuanto",
    "cuanta",
    "cuantos",
    "cuantas",
)
_FOLLOWUP_DEADLINE_MARKERS = (
    "plazo",
    "termino",
    "venc",
    "dias",
    "dia",
    "meses",
    "mes",
    "anos",
    "ano",
    "hasta cuando",
    "antes de",
    "dentro de",
)
_FOLLOWUP_EXCEPTION_MARKERS = (
    "excepto",
    "salvo",
    "solo si",
    "solo cuando",
    "en que caso",
    "en que casos",
    "cuando cambia",
    "cuando aplica",
    "cuando no aplica",
    "bajo que",
    "como cambia",
    "como cambiaria",
    "cambiaria si",
    "cambia esto",
    "cambia eso",
    "si viene de",
    "si proviene de",
)
_FOLLOWUP_PROCEDURE_MARKERS = (
    "como",
    "paso a paso",
    "que hago",
    "que reviso",
    "procedimiento",
    "requisito",
    "requisitos",
    "checklist",
)
_FOLLOWUP_EXPLANATION_MARKERS = (
    "explicame",
    "explica",
    "cuentame",
    "que significa",
    "a que te refieres",
    "como funciona",
    "como opera",
    "por que",
)
_FOLLOWUP_CATEGORICAL_MARKERS = (
    "hay",
    "existe",
    "aplica",
    "procede",
    "puedo",
    "puede",
    "debo",
    "corresponde",
    "tengo que",
)
_FOLLOWUP_QUOTED_DRILLDOWN_MARKERS = (
    "cuentame",
    "hablame",
    "explicame",
    "profundiza",
    "desarrolla",
    "a que te refieres",
    "que significa eso",
    "como opera eso",
    "como funciona eso",
    "de esto",
    "de eso",
    "sobre esto",
    "sobre eso",
    "sobre ese punto",
    "sobre este punto",
)
_EMBEDDED_ANSWER_STARTERS = (
    "no,",
    "si,",
    "sí,",
    "depende",
    "solo cambia",
    "en la practica",
    "en la práctica",
    "recuerda que",
    "ojo con",
    "para ",
    "el limite",
    "el límite",
    "la regla",
    "en concreto",
    "precauciones",
    "anclaje legal",
)
_EMBEDDED_ANSWER_MARKERS = (
    "en la practica",
    "en la práctica",
    "solo cambia",
    "en concreto",
    "precauciones",
    "anclaje legal",
    "(art.",
    "(arts.",
    " art. ",
    " arts. ",
)


@dataclass(frozen=True)
class FollowupFocus:
    shape_text: str
    ranking_text: str
    quoted_text: str = ""
    has_embedded_answer_echo: bool = False


def extend_from_support_insights(
    bucket: list[str],
    lines: tuple[str, ...],
) -> None:
    for line in lines:
        cleaned = clean_support_line_for_answer(line)
        if cleaned:
            append_unique(bucket, cleaned)


def extend_from_guidance(
    bucket: list[str],
    field: str,
    items: tuple[GraphEvidenceItem, ...],
) -> None:
    for item in items:
        guidance = guidance_for_item(item)
        for line in guidance.get(field, ()):
            append_unique(bucket, line)


def fallback_recommendation(
    *,
    request: PipelineCRequest,
    primary_articles: tuple[GraphEvidenceItem, ...],
) -> str:
    anchor = best_matching_primary_article(
        request=request,
        primary_articles=primary_articles,
    )
    if anchor is None:
        return ""
    normalized_title = normalize_text(anchor.title)
    if "anticipo" in normalized_title:
        return (
            "Define primero cuál es el impuesto neto de renta que sirve de base del anticipo "
            "y qué porcentaje aplica según la antigüedad del contribuyente."
        )
    return ""


def fallback_procedure_step(
    *,
    request: PipelineCRequest,
    primary_articles: tuple[GraphEvidenceItem, ...],
) -> str:
    anchor = best_matching_primary_article(
        request=request,
        primary_articles=primary_articles,
    )
    if anchor is None:
        return ""
    normalized_title = normalize_text(anchor.title)
    if "anticipo" in normalized_title:
        return (
            "Liquida el anticipo del año siguiente sobre el impuesto neto de renta del año base "
            "y aplica 25 %, 50 % o 75 % según corresponda por la antigüedad del contribuyente."
        )
    return ""


def best_matching_primary_article(
    *,
    request: PipelineCRequest,
    primary_articles: tuple[GraphEvidenceItem, ...],
) -> GraphEvidenceItem | None:
    if not primary_articles:
        return None
    normalized_message = normalize_text(request.message)
    query_tokens = anchor_query_tokens(normalized_message)
    best_item: GraphEvidenceItem | None = None
    best_score = -1.0
    for index, item in enumerate(primary_articles):
        title_tokens = {
            token
            for token in re.split(r"[^a-z0-9]+", normalize_text(item.title))
            if len(token) >= 3
        }
        score = float(len(query_tokens.intersection(title_tokens)) * 4)
        node_key = str(item.node_key or "").strip().lower()
        if node_key and node_key in normalized_message:
            score += 1.5
        score += max(0.0, 0.05 * (len(primary_articles) - index))
        if score > best_score:
            best_item = item
            best_score = score
    return best_item or primary_articles[0]


def pepper_legal_anchor_into_procedure(
    steps: list[str],
    primary_articles: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    anchor_tail = procedure_anchor_tail(primary_articles)
    if not anchor_tail:
        return tuple(steps)
    enriched: list[str] = []
    tail_used = False
    for step in steps:
        current = str(step or "").strip()
        if current and not tail_used and not line_has_legal_reference(current):
            current = current.rstrip(".") + f" {anchor_tail}"
            tail_used = True
        enriched.append(current)
    return tuple(enriched)


def procedure_anchor_tail(primary_articles: tuple[GraphEvidenceItem, ...]) -> str:
    article_keys = [item.node_key for item in primary_articles[:5] if str(item.node_key or "").strip()]
    if not article_keys:
        return ""
    if len(article_keys) == 1:
        joined = article_keys[0]
    elif len(article_keys) == 2:
        joined = f"{article_keys[0]} y {article_keys[1]}"
    else:
        joined = ", ".join(article_keys[:-1]) + f" y {article_keys[-1]}"
    return f"Apóyate aquí en los arts. {joined} ET."


def should_surface_connected_anchor(
    *,
    title: str,
    normalized_message: str,
    query_tokens: set[str],
) -> bool:
    normalized_title = normalize_text(title)
    title_tokens = {
        token
        for token in re.split(r"[^a-z0-9]+", normalized_title)
        if len(token) >= 3
    }
    if query_tokens.intersection(title_tokens):
        return True
    if looks_like_tax_treatment_question(normalized_message):
        return any(
            marker in normalized_title
            for marker in (
                "descuento",
                "costo",
                "gasto",
                "descontable",
                "iva",
            )
        )
    return False


def clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" .")


def is_refund_balance_case(normalized_message: str) -> bool:
    return _looks_like_refund_balance_case(normalized_message)


def is_loss_compensation_case(normalized_message: str) -> bool:
    return _looks_like_loss_compensation_case(normalized_message)


def looks_like_tax_treatment_question(normalized_message: str) -> bool:
    has_treatment = any(
        marker in normalized_message
        for marker in (
            "deducir",
            "deducible",
            "procedente",
            "procedencia",
            "descuento tributario",
            "costo o gasto",
            "impuesto pagado",
            "impuestos pagados",
        )
    )
    has_tax_subject = any(
        marker in normalized_message
        for marker in (
            "ica",
            "industria y comercio",
            "avisos y tableros",
            "gmf",
            "gravamen a los movimientos financieros",
            "movimientos financieros",
            "4x1000",
            "cuatro por mil",
            "impuesto",
            "impuestos",
        )
    )
    return has_treatment and has_tax_subject


def tax_treatment_subject_label(normalized_message: str) -> str:
    if any(
        marker in normalized_message
        for marker in (
            "ica",
            "industria y comercio",
            "avisos y tableros",
        )
    ):
        return "ese impuesto pagado, incluido ICA"
    if any(
        marker in normalized_message
        for marker in (
            "gmf",
            "gravamen a los movimientos financieros",
            "movimientos financieros",
            "4x1000",
            "cuatro por mil",
        )
    ):
        return "ese impuesto pagado, incluido GMF"
    return "ese impuesto pagado"


def build_followup_focus(raw_message: str) -> FollowupFocus:
    text = re.sub(r"\s+", " ", str(raw_message or "")).strip()
    if not text:
        return FollowupFocus(shape_text="", ranking_text="")

    quoted = _extract_explicit_drilldown_quote(text)
    if quoted is not None:
        return quoted

    question_split = _split_question_from_embedded_answer(text)
    if question_split is not None:
        head, tail = question_split
        if _looks_like_exception_drilldown_tail(tail):
            return FollowupFocus(
                shape_text=head,
                ranking_text=tail,
                quoted_text=tail,
                has_embedded_answer_echo=False,
            )
        return FollowupFocus(
            shape_text=head,
            ranking_text=head,
            quoted_text=tail,
            has_embedded_answer_echo=True,
        )

    newline_split = _split_first_line_from_embedded_answer(raw_message)
    if newline_split is not None:
        head, tail = newline_split
        return FollowupFocus(
            shape_text=head,
            ranking_text=head,
            quoted_text=tail,
            has_embedded_answer_echo=True,
        )

    return FollowupFocus(shape_text=text, ranking_text=text)


def classify_followup_question_shape(normalized_message: str) -> str:
    message = str(normalized_message or "").strip()
    if not message:
        return "broad"
    token_count = len([token for token in message.split() if token])

    if any(marker in message for marker in _FOLLOWUP_EXPLANATION_MARKERS):
        return "explanation"
    if any(marker in message for marker in _FOLLOWUP_EXCEPTION_MARKERS):
        return "exception"
    if any(marker in message for marker in _FOLLOWUP_LIMIT_MARKERS):
        return "amount_limit"
    if any(marker in message for marker in _FOLLOWUP_DEADLINE_MARKERS):
        return "deadline"
    if any(marker in message for marker in _FOLLOWUP_PROCEDURE_MARKERS):
        return "procedure"
    if any(marker in message for marker in _FOLLOWUP_CATEGORICAL_MARKERS):
        return "categorical"
    if token_count <= 12:
        return "categorical"
    return "broad"


def _extract_explicit_drilldown_quote(text: str) -> FollowupFocus | None:
    match = re.match(r"^(?P<intro>[^:]{1,180}):\s*(?P<tail>.+)$", text)
    if not match:
        return None
    intro = match.group("intro").strip()
    tail = match.group("tail").strip()
    normalized_intro = normalize_text(intro)
    if not tail:
        return None
    if not any(marker in normalized_intro for marker in _FOLLOWUP_QUOTED_DRILLDOWN_MARKERS):
        return None
    return FollowupFocus(
        shape_text=intro,
        ranking_text=tail,
        quoted_text=tail,
        has_embedded_answer_echo=False,
    )


def _split_question_from_embedded_answer(text: str) -> tuple[str, str] | None:
    question_mark_index = text.find("?")
    if question_mark_index == -1:
        return None
    head = text[: question_mark_index + 1].strip(" :-")
    tail = text[question_mark_index + 1 :].strip(" :-")
    if not head or not tail:
        return None
    if not _looks_like_embedded_answer_text(tail):
        return None
    return head, tail


def _split_first_line_from_embedded_answer(raw_message: str) -> tuple[str, str] | None:
    lines = [str(line or "").strip() for line in str(raw_message or "").splitlines() if str(line or "").strip()]
    if len(lines) < 2:
        return None
    head = lines[0]
    tail = " ".join(lines[1:]).strip()
    if not head or not tail:
        return None
    if "?" not in head and len(head.split()) > 14:
        return None
    if not _looks_like_embedded_answer_text(tail):
        return None
    return head, tail


def _looks_like_embedded_answer_text(text: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "")).strip()
    normalized = normalize_text(raw)
    if not raw or len(normalized.split()) < 8:
        return False

    score = 0
    if any(normalized.startswith(marker) for marker in _EMBEDDED_ANSWER_STARTERS):
        score += 2
    if any(marker in normalized for marker in _EMBEDDED_ANSWER_MARKERS):
        score += 2
    if raw.count(".") >= 1 or raw.count("\n") >= 1:
        score += 1
    if line_has_legal_reference(raw):
        score += 1
    return score >= 3


def _looks_like_exception_drilldown_tail(text: str) -> bool:
    normalized = normalize_text(text)
    return any(
        marker in normalized
        for marker in (
            "solo cambia si",
            "solo cambia cuando",
            "si viene de",
            "si proviene de",
            "regimen congelado",
            "regimen de transicion",
        )
    )


__all__ = [
    "best_matching_primary_article",
    "FollowupFocus",
    "build_followup_focus",
    "clean_title",
    "classify_followup_question_shape",
    "extend_from_guidance",
    "extend_from_support_insights",
    "fallback_procedure_step",
    "fallback_recommendation",
    "is_loss_compensation_case",
    "is_refund_balance_case",
    "looks_like_tax_treatment_question",
    "pepper_legal_anchor_into_procedure",
    "should_surface_connected_anchor",
    "tax_treatment_subject_label",
]
