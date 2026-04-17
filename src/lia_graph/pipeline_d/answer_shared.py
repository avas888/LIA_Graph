from __future__ import annotations

from datetime import date
import re
import unicodedata

from ..chat_response_modes import FIRST_RESPONSE_MODE_FAST_ACTION, normalize_first_response_mode
from ..pipeline_c.contracts import PipelineCRequest
from .contracts import GraphEvidenceItem

_NORMATIVE_CHANGE_RE = re.compile(
    r"\b(?:Ley|Decreto|Resoluci[oó]n)\s+\d+\s+de\s+\d{4}\b",
    re.IGNORECASE,
)
_DISPLAY_META_PATTERNS = (
    "empieza por las normas principales",
    "toma las normas principales del caso",
    "antes de pasar al detalle legal fino",
    "antes de recomendar algo al cliente",
    "si quieres bajar esto a operacion",
    "hay espacio para volver esto mas eficiente",
    "nuestra evaluacion:",
)
_CHANGE_INTENT_PATTERNS = (
    "que ha modificado",
    "qué ha modificado",
    "que modifico",
    "qué modificó",
    "que modificaciones",
    "qué modificaciones",
    "cambios ha sufrido",
    "como ha cambiado",
    "cómo ha cambiado",
    "historicamente",
    "históricamente",
    "evolucion",
    "evolución",
    "version anterior",
    "versión anterior",
    "que decia",
    "qué decía",
    "texto original",
)
_AG_YEAR_RE = re.compile(r"\bAG\s*(\d{4})\b", re.IGNORECASE)
_NON_IMPUTATIVE_LANGUAGE_REWRITES = (
    (
        r"que el cliente puede cumplir de verdad",
        "que el cliente puede cumplir efectivamente",
    ),
    (
        r"A un contador nuevo yo le dir[ií]a que persiga solo palancas",
        "A un contador nuevo yo le diría que priorice solo palancas",
    ),
    (
        r"cualquier ahorro que dependa de arreglar papeles despu[eé]s",
        "cualquier ahorro que dependa de completar o reconstruir soportes después del cierre",
    ),
    (
        r"pero no inventarte entregas, notas cr[eé]dito o contratos de papel para mover la base",
        "pero no reconocer entregas, notas crédito o contratos sin soporte suficiente para alterar la base",
    ),
    (
        r"no maquillando enero desde contabilidad",
        "sin trasladar a diciembre hechos económicos que corresponden a enero ni presentar inexactitudes contables",
    ),
    (
        r"El cierre sano se juega revisando",
        "El cierre sano se trabaja revisando",
    ),
    (
        r"no de inventarse una capa jur[ií]dica de [úu]ltima hora para bajar el impuesto",
        "no de adoptar una estructura jurídica de última hora que no refleje adecuadamente la sustancia económica",
    ),
    (
        r"la lean sin simpat[ií]a en una fiscalizaci[oó]n",
        "la revisen con un estándar exigente de fiscalización",
    ),
    (
        r"ya entraste en zona de pelea",
        "se incrementa de forma importante el riesgo de cuestionamiento",
    ),
    (
        r"etiqueta bonita",
        "calificación formal",
    ),
    (
        r"todav[ií]a no est[aá] lista para venderse como ahorro",
        "todavía no está lista para presentarse como ahorro consolidado",
    ),
    (
        r"una defensa simple, barata y muy poderosa",
        "una defensa sencilla, de bajo costo y muy útil",
    ),
    (
        r"acto de papel armado al final del a[nñ]o",
        "acto formal documentado al final del año sin ejecución económica demostrable",
    ),
)


def should_use_first_bubble_format(request: PipelineCRequest) -> bool:
    if normalize_first_response_mode(request.first_response_mode) != FIRST_RESPONSE_MODE_FAST_ACTION:
        return False
    state = request.conversation_state
    if isinstance(state, dict):
        return int(state.get("turn_count") or 0) <= 0
    return not str(request.conversation_context or "").strip()


def render_bullet_section(title: str, lines: tuple[str, ...]) -> str:
    return f"**{title}**\n" + "\n".join(f"- {line}" for line in lines if line)


def render_numbered_section(title: str, lines: tuple[str, ...]) -> str:
    return f"**{title}**\n" + "\n".join(f"{idx}. {line}" for idx, line in enumerate(lines, start=1) if line)


def filter_published_lines(
    lines: tuple[str, ...],
    *,
    allow_change_lines: bool,
) -> tuple[str, ...]:
    published: list[str] = []
    for line in lines:
        value = neutralize_non_imputative_language(line)
        if not value:
            continue
        normalized = normalize_text(value)
        if any(pattern in normalized for pattern in _DISPLAY_META_PATTERNS):
            continue
        if not allow_change_lines and looks_like_change_context_line(value):
            continue
        append_unique(published, value)
    return tuple(published)


def published_context_lines(
    lines: tuple[str, ...],
    *,
    allow_change_context: bool,
) -> tuple[str, ...]:
    published: list[str] = []
    for line in lines:
        value = neutralize_non_imputative_language(line)
        if not value:
            continue
        if not allow_change_context and looks_like_change_context_line(value):
            continue
        append_unique(published, value)
    return tuple(published)


def should_surface_change_context(
    *,
    normalized_message: str,
    temporal_context: dict[str, object],
    planner_query_mode: str,
    requested_period_label: str,
) -> bool:
    if bool(temporal_context.get("historical_query_intent")):
        return True
    if planner_query_mode == "historical_reform_chain":
        return True
    if has_explicit_change_intent(normalized_message):
        return True
    if is_recent_ag_period(requested_period_label):
        return True
    return any(
        marker in normalized_message
        for marker in (
            "antes de la ley",
            "despues de la ley",
            "después de la ley",
        )
    )


def extract_change_mentions(
    primary_articles: tuple[GraphEvidenceItem, ...],
    reforms: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    mentions: list[str] = []
    for reform in reforms:
        append_unique(mentions, reform.title)
    for item in primary_articles:
        for match in _NORMATIVE_CHANGE_RE.findall(str(item.excerpt or "")):
            append_unique(mentions, match)
    return tuple(mentions)


def take_new_lines(lines: tuple[str, ...], seen: set[str]) -> tuple[str, ...]:
    fresh: list[str] = []
    for line in lines:
        key = re.sub(
            r"[.!?]+$",
            "",
            normalize_text(
                re.sub(
                    r"\s+ap[oó]yate aqu[ií] en los arts?\.[^.]+\.?$",
                    "",
                    str(line or ""),
                    flags=re.IGNORECASE,
                )
            ),
        )
        if not key or key in seen:
            continue
        seen.add(key)
        fresh.append(line)
    return tuple(fresh)


def line_has_legal_reference(value: str) -> bool:
    normalized = normalize_text(value)
    return any(
        marker in normalized
        for marker in (
            "art.",
            "arts.",
            "art ",
            "arts ",
            "articulo",
            "articulos",
            "par. ",
            "paragrafo",
            "et ",
            "ley ",
            "decreto ",
            "dur ",
            "resolucion ",
            "resolucion",
        )
    )


def has_explicit_change_intent(normalized_message: str) -> bool:
    return any(
        re.search(rf"\b{re.escape(pattern)}\b", normalized_message, flags=re.IGNORECASE)
        for pattern in _CHANGE_INTENT_PATTERNS
    )


def is_recent_ag_period(requested_period_label: str) -> bool:
    match = _AG_YEAR_RE.search(str(requested_period_label or ""))
    if not match:
        return False
    try:
        ag_year = int(match.group(1))
    except ValueError:
        return False
    current_year = date.today().year
    return ag_year in {current_year - 1, current_year - 2}


def append_unique(bucket: list[str], line: str) -> None:
    value = re.sub(r"\s+", " ", str(line or "")).strip()
    if not value:
        return
    if value not in bucket:
        bucket.append(value)


def neutralize_non_imputative_language(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    for pattern, replacement in _NON_IMPUTATIVE_LANGUAGE_REWRITES:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def looks_like_change_context_line(value: str) -> bool:
    normalized = normalize_text(value)
    return any(
        marker in normalized
        for marker in (
            "ha cambiado",
            "cambio desde",
            "cambios o reformas",
            "actualizo",
            "actualizó",
            "actualizar",
            "modificado por",
            "modificada por",
            "modificaciones",
            "reforma",
            "resolucion",
            "resolución",
            "sentencia",
            "texto original",
            "version anterior",
            "versión anterior",
            "vigencia",
            "articulo adicionado por",
            "artículo adicionado por",
            "historica",
            "histórica",
            "historico",
            "histórico",
        )
    )


def anchor_query_tokens(normalized_message: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", normalized_message)
        if len(token) >= 3
        and token
        not in {
            "que",
            "como",
            "para",
            "con",
            "sin",
            "del",
            "las",
            "los",
            "una",
            "uno",
            "unos",
            "unas",
            "declaracion",
            "renta",
            "persona",
            "juridica",
            "pagado",
            "pagados",
            "impuesto",
            "impuestos",
        }
    }


__all__ = [
    "anchor_query_tokens",
    "append_unique",
    "extract_change_mentions",
    "filter_published_lines",
    "has_explicit_change_intent",
    "is_recent_ag_period",
    "line_has_legal_reference",
    "looks_like_change_context_line",
    "neutralize_non_imputative_language",
    "normalize_text",
    "published_context_lines",
    "render_bullet_section",
    "render_numbered_section",
    "should_surface_change_context",
    "should_use_first_bubble_format",
    "take_new_lines",
]
