from __future__ import annotations

from dataclasses import dataclass
import re

from .answer_shared import (
    anchor_query_tokens,
    line_has_legal_reference,
    neutralize_non_imputative_language,
    normalize_text,
)
from .contracts import GraphEvidenceItem


@dataclass(frozen=True)
class PreparedAnswerLine:
    text: str
    anchors: tuple[str, ...] = ()


def prepare_first_bubble_lines(
    raw_lines: tuple[str, ...],
    *,
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
    limit: int,
) -> tuple[PreparedAnswerLine, ...]:
    prepared: list[PreparedAnswerLine] = []
    seen: set[str] = set()
    for line in raw_lines:
        clean = strip_legacy_anchor_tail(str(line or ""))
        clean = neutralize_non_imputative_language(clean)
        if not clean:
            continue
        key = line_identity_key(clean)
        if key in seen:
            continue
        seen.add(key)
        anchors = select_inline_anchors(
            clean,
            primary_articles=primary_articles,
            connected_articles=connected_articles,
        )
        rendered = append_inline_anchor(clean, anchors=anchors)
        if not rendered:
            continue
        prepared.append(PreparedAnswerLine(text=rendered, anchors=anchors))
        if len(prepared) >= limit:
            break
    return tuple(prepared)


def line_identity_key(value: str) -> str:
    stripped = re.sub(r"\s+Base:\s+arts?\.[^.]+\.?$", "", str(value or ""), flags=re.IGNORECASE)
    stripped = re.sub(r"\s+\(arts?\.[^)]+\)\.?$", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"[.!?]+$", "", stripped)
    return normalize_text(stripped)


def strip_legacy_anchor_tail(value: str) -> str:
    return re.sub(
        r"\s+Ap[oó]yate aqu[ií] en los arts?\.[^.]+\.?$",
        "",
        str(value or ""),
        flags=re.IGNORECASE,
    ).strip()


def append_inline_anchor(
    value: str,
    *,
    anchors: tuple[str, ...],
) -> str:
    line = re.sub(r"\s+", " ", str(value or "")).strip()
    if not line:
        return ""
    if not anchors or line_has_legal_reference(line):
        return line
    return line.rstrip(".") + f" ({render_article_anchor_phrase(anchors)})."


def select_inline_anchors(
    value: str,
    *,
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
    max_refs: int = 2,
) -> tuple[str, ...]:
    candidate_rows = (*primary_articles[:5], *connected_articles[:3])
    if not candidate_rows:
        return ()
    normalized_line = normalize_text(value)
    line_tokens = anchor_query_tokens(normalized_line)
    scored: list[tuple[float, str]] = []
    primary_limit = len(primary_articles[:5])
    for index, item in enumerate(candidate_rows):
        article_key = str(item.node_key or "").strip()
        if not article_key:
            continue
        title_tokens = anchor_query_tokens(normalize_text(item.title))
        excerpt_tokens = anchor_query_tokens(normalize_text(str(item.excerpt or ""))) or ()
        score = 0.0
        if article_key.lower() in normalized_line:
            score += 5.0
        score += float(len(line_tokens.intersection(title_tokens)) * 2.2)
        score += float(len(line_tokens.intersection(excerpt_tokens)) * 0.5)
        if index < primary_limit:
            score += max(0.2, 0.9 - (index * 0.15))
        if int(item.hop_distance or 0) == 0:
            score += 0.4
        scored.append((score, article_key))
    ranked = [key for score, key in sorted(scored, key=lambda item: (-item[0], item[1])) if score > 0.75]
    if not ranked:
        ranked = [
            str(item.node_key or "").strip()
            for item in primary_articles[:max_refs]
            if str(item.node_key or "").strip()
        ]
    return tuple(dict.fromkeys(ranked[:max_refs]))


def render_article_anchor_phrase(anchors: tuple[str, ...]) -> str:
    values = [str(anchor).strip() for anchor in anchors if str(anchor or "").strip()]
    if not values:
        return ""
    if len(values) == 1:
        return f"art. {values[0]} ET"
    if len(values) == 2:
        return f"arts. {values[0]} y {values[1]} ET"
    return f"arts. {', '.join(values[:-1])} y {values[-1]} ET"


__all__ = [
    "PreparedAnswerLine",
    "append_inline_anchor",
    "line_identity_key",
    "prepare_first_bubble_lines",
    "render_article_anchor_phrase",
    "select_inline_anchors",
    "strip_legacy_anchor_tail",
]
