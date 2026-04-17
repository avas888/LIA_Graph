from __future__ import annotations

import re

from ..pipeline_c.contracts import PipelineCRequest
from .answer_policy import FIRST_BUBBLE_RECAP_LIMIT
from .answer_shared import (
    append_unique,
    extract_change_mentions,
    has_explicit_change_intent,
    normalize_text,
    should_surface_change_context,
)
from .contracts import GraphEvidenceItem

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_NORMATIVE_CHANGE_RE = re.compile(
    r"\b(?:Ley|Decreto|Resoluci[oó]n)\s+\d+\s+de\s+\d{4}\b",
    re.IGNORECASE,
)


def build_historical_recap_lines(
    *,
    request: PipelineCRequest,
    planner_query_mode: str,
    temporal_context: dict[str, object],
    primary_articles: tuple[GraphEvidenceItem, ...],
    reforms: tuple[GraphEvidenceItem, ...],
) -> tuple[str, ...]:
    normalized_message = normalize_text(request.message)
    requested_period_label = str(temporal_context.get("requested_period_label") or "").strip()
    allow_change_context = should_surface_change_context(
        normalized_message=normalized_message,
        temporal_context=temporal_context,
        planner_query_mode=planner_query_mode,
        requested_period_label=requested_period_label,
    )
    if not allow_change_context:
        return ()

    anchor_labels = tuple(
        str(item).strip()
        for item in (temporal_context.get("anchor_reform_labels") or ())
        if str(item).strip()
    )
    reform_titles = tuple(str(item.title or "").strip() for item in reforms if str(item.title or "").strip())
    global_mentions = sorted_history_mentions(
        tuple((*reform_titles, *extract_change_mentions(primary_articles, reforms)))
    )
    has_explicit_history_intent = bool(temporal_context.get("historical_query_intent")) or planner_query_mode in {
        "reform_chain",
        "historical_reform_chain",
        "historical_graph_research",
    } or has_explicit_change_intent(normalized_message)
    if not has_explicit_history_intent:
        return ()
    if not global_mentions and not str(temporal_context.get("cutoff_date") or "").strip():
        global_mentions = anchor_labels

    lines: list[str] = []
    cutoff_date = str(temporal_context.get("cutoff_date") or "").strip()
    if cutoff_date and has_explicit_history_intent:
        if anchor_labels:
            append_unique(
                lines,
                f"Corte histórico: para esta respuesta, toma la regla vigente hasta {cutoff_date} antes de {anchor_labels[0]}.",
            )
        else:
            append_unique(
                lines,
                f"Corte histórico: para esta respuesta, toma la regla vigente hasta {cutoff_date}.",
            )
    elif anchor_labels:
        append_unique(
            lines,
            f"Reforma ancla de esta lectura: {anchor_labels[0]}.",
        )

    for item in primary_articles[:3]:
        mentions = sorted_history_mentions(
            tuple((*reform_titles, *_NORMATIVE_CHANGE_RE.findall(str(item.excerpt or ""))))
        )
        if not mentions:
            mentions = global_mentions
        line = format_historical_recap_line(article_key=str(item.node_key or "").strip(), mentions=mentions)
        if not line:
            continue
        append_unique(lines, line)
        if len(lines) >= FIRST_BUBBLE_RECAP_LIMIT:
            break
    return tuple(lines[:FIRST_BUBBLE_RECAP_LIMIT])


def sorted_history_mentions(mentions: tuple[str, ...]) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for raw in mentions:
        clean = re.sub(r"\s+", " ", str(raw or "")).strip(" .")
        if not clean:
            continue
        key = normalize_text(clean)
        if key in seen:
            continue
        seen.add(key)
        unique.append(clean)
    ranked = sorted(unique, key=lambda item: (-extract_normative_year(item), item))
    return tuple(ranked)


def extract_normative_year(value: str) -> int:
    match = _YEAR_RE.search(str(value or ""))
    if not match:
        return 0
    try:
        return int(match.group(0))
    except ValueError:
        return 0


def format_historical_recap_line(
    *,
    article_key: str,
    mentions: tuple[str, ...],
) -> str:
    if not article_key or not mentions:
        return ""
    if len(mentions) == 1:
        return f"Art. {article_key} ET: la última modificación relevante detectada en esta ruta es {mentions[0]}."
    if len(mentions) == 2:
        return f"Art. {article_key} ET: la cadena reciente recuperada pasa por {mentions[0]} y antes por {mentions[1]}."
    return (
        f"Art. {article_key} ET: la cadena reciente recuperada pasa por {mentions[0]}, "
        f"antes por {mentions[1]} y luego por {mentions[2]}."
    )


__all__ = [
    "build_historical_recap_lines",
    "extract_normative_year",
    "format_historical_recap_line",
    "sorted_history_mentions",
]
