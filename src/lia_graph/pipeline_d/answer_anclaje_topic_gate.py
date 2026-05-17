"""v23 P7 — Anclaje Legal topic-aware constraint (G7).

v22's P3 closing probe surfaced this: a CST 64 (terminación contrato) question
correctly rendered `(art. 64 CST)` in body bullets but Anclaje Legal also
expanded to include `Art. 102 ET — fiducia / Art. 102-2 ET — transporte
terrestre / Art. 103 ET — definición de rentas`. These ET articles are
off-topic for a labor question; they bled in from `connected_articles` (graph
neighbours) without a topic-relevance filter.

This module filters `connected_articles` (and optionally `primary_articles`)
against the active topic's compatibility allowlist before composing the
Anclaje Legal section. Body bullets and other sections are UNTOUCHED — the
gate is Anclaje-specific.

Allowlist source: ``config/compatible_doc_topics.json`` (introduced by v22
§9c to widen the coherence gate's topic-compatibility window).

Flag-gated by ``LIA_ANCLAJE_TOPIC_GATE={off,shadow,enforce}``, default
``enforce``.
"""

from __future__ import annotations

import os
from typing import Iterable

from .compatible_doc_topics import get_compatible_topics
from .contracts import GraphEvidenceItem


def gate_mode() -> str:
    raw = (os.getenv("LIA_ANCLAJE_TOPIC_GATE") or "enforce").strip().lower()
    return raw if raw in ("off", "shadow", "enforce") else "enforce"


def _allowed_topics_for(effective_topic: str) -> frozenset[str]:
    """Return the set of topics whose articles may appear in the Anclaje
    Legal section for ``effective_topic``. Built from the same allowlist
    the coherence gate uses, so anclaje compatibility ↔ coherence
    compatibility stays consistent.
    """
    if not effective_topic:
        return frozenset()
    compat = get_compatible_topics(effective_topic) or ()
    return frozenset({effective_topic, *compat})


def _article_topic_set(item: GraphEvidenceItem) -> tuple[str, ...]:
    """Return the union of topics declared by the article. ``secondary_topics``
    is the primary signal; we treat empty as "topic unknown" → keep
    (avoid penalising graph gaps)."""
    return tuple(getattr(item, "secondary_topics", ()) or ())


def filter_anclaje_articles(
    articles: Iterable[GraphEvidenceItem],
    effective_topic: str,
) -> tuple[tuple[GraphEvidenceItem, ...], tuple[GraphEvidenceItem, ...]]:
    """Return ``(kept, dropped)``. Drops articles whose declared topics
    don't intersect the allowed-topic set; keeps articles with no declared
    topics (graph gap → preserve evidence)."""
    if gate_mode() == "off" or not effective_topic:
        items = tuple(articles)
        return items, ()

    allowed = _allowed_topics_for(effective_topic)
    if not allowed:
        items = tuple(articles)
        return items, ()

    kept: list[GraphEvidenceItem] = []
    dropped: list[GraphEvidenceItem] = []
    for item in articles:
        topics = _article_topic_set(item)
        if not topics:
            kept.append(item)
            continue
        if set(topics) & allowed:
            kept.append(item)
        else:
            dropped.append(item)
    return tuple(kept), tuple(dropped)


def diagnostics_payload(
    *,
    kept: tuple[GraphEvidenceItem, ...],
    dropped: tuple[GraphEvidenceItem, ...],
    effective_topic: str,
) -> dict:
    """Compact diagnostic dict for the public response payload."""
    mode = gate_mode()
    return {
        "anclaje_topic_gate_mode": mode,
        "anclaje_topic_gate_applied": mode != "off",
        "anclaje_effective_topic": effective_topic or None,
        "anclaje_articles_kept": [str(i.node_key) for i in kept[:10]],
        "anclaje_articles_dropped": [str(i.node_key) for i in dropped[:10]],
        "anclaje_articles_dropped_count": len(dropped),
    }


__all__ = [
    "diagnostics_payload",
    "filter_anclaje_articles",
    "gate_mode",
]
