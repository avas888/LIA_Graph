from __future__ import annotations

from typing import Any

from .policy import (
    NORMATIVA_CONNECTED_ANCHOR_LIMIT,
    NORMATIVA_PRIMARY_ANCHOR_LIMIT,
    NORMATIVA_RELATION_LIMIT,
    NORMATIVA_SUPPORT_LIMIT,
)
from .shared import clean_text, first_sentence


def collect_anchor_lines(evidence: object) -> tuple[str, ...]:
    lines: list[str] = []
    for item in list(getattr(evidence, "primary_articles", ()) or ())[:NORMATIVA_PRIMARY_ANCHOR_LIMIT]:
        line = first_sentence(getattr(item, "excerpt", ""), max_chars=260)
        if line:
            lines.append(line)
    for item in list(getattr(evidence, "connected_articles", ()) or ())[:NORMATIVA_CONNECTED_ANCHOR_LIMIT]:
        title = clean_text(getattr(item, "title", ""), max_chars=120)
        excerpt = first_sentence(getattr(item, "excerpt", ""), max_chars=220)
        if title and excerpt:
            lines.append(f"{title}: {excerpt}")
        elif excerpt:
            lines.append(excerpt)
    return tuple(lines)


def collect_relation_lines(evidence: object) -> tuple[str, ...]:
    lines: list[str] = []
    for item in list(getattr(evidence, "related_reforms", ()) or ())[:NORMATIVA_RELATION_LIMIT]:
        title = clean_text(getattr(item, "title", ""), max_chars=140) or clean_text(
            getattr(item, "node_key", ""),
            max_chars=140,
        )
        why = clean_text(getattr(item, "why", ""), max_chars=180)
        if title and why:
            lines.append(f"{title}: {why}")
        elif title:
            lines.append(title)
    return tuple(lines)


def collect_support_lines(evidence: object) -> tuple[str, ...]:
    lines: list[str] = []
    for item in list(getattr(evidence, "support_documents", ()) or ())[:NORMATIVA_SUPPORT_LIMIT]:
        title = clean_text(getattr(item, "title_hint", ""), max_chars=140)
        reason = clean_text(getattr(item, "reason", ""), max_chars=180)
        if title and reason:
            lines.append(f"{title}: {reason}")
        elif title:
            lines.append(title)
    return tuple(lines)


def binding_force_from_context(context: dict[str, object]) -> str:
    document_profile = dict(context.get("document_profile") or {})
    return clean_text(document_profile.get("binding_force"), max_chars=120)


def build_normativa_diagnostics(
    *,
    query_mode: str,
    evidence: object,
) -> dict[str, Any]:
    return {
        "query_mode": query_mode,
        "primary_articles": len(list(getattr(evidence, "primary_articles", ()) or ())),
        "connected_articles": len(list(getattr(evidence, "connected_articles", ()) or ())),
        "related_reforms": len(list(getattr(evidence, "related_reforms", ()) or ())),
        "support_documents": len(list(getattr(evidence, "support_documents", ()) or ())),
    }

