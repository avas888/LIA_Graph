"""fix_v13_may — constants + env knobs for the dedicated práctica lane."""

from __future__ import annotations

import os


DEFAULT_RESERVED_SLOTS = 3
"""Top-K práctica chunks reserved for `build_recommendations`. Matches
the section's natural bullet cap (`build_recommendations` returns
`tuple(lines[:3])`). Raise via `LIA_PRACTICA_RESERVED_SLOTS` only after
SME validation shows follow-up bubbles still read normative-voiced —
see fix_v13_may §7."""

DEFAULT_TOPIC_BOOST = 1.5
"""Multiplicative RRF boost on chunks whose `topic` matches the routed
topic. The dedicated lane already hard-filters on
`knowledge_class='practica_erp'`, so this boost is purely a within-
class topic-coherence tiebreaker. Floors at 1.0 per Invariant I5 (never
penalize)."""

MATCH_COUNT_MULTIPLIER = 4
"""`hybrid_search.match_count = max(top_k * 4, MIN_MATCH_COUNT)` so the
quality-gate stack (vigencia demotion, topic gate, citation allow-list)
has enough headroom to drop dropped/contested chunks without starving
the reserved slots."""

MIN_MATCH_COUNT = 24
"""Floor for `match_count` so RRF has a workable candidate pool even
when reserved slots are small."""


def resolve_reserved_slots() -> int:
    """Read `LIA_PRACTICA_RESERVED_SLOTS` env; default `DEFAULT_RESERVED_SLOTS`.

    Floors at 0 (disable) and caps at 8 (above 8 the lane starts
    competing with normative-anchored bullets the section also needs).
    """
    raw = os.getenv("LIA_PRACTICA_RESERVED_SLOTS")
    if raw is None or not str(raw).strip():
        return DEFAULT_RESERVED_SLOTS
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_RESERVED_SLOTS
    if parsed < 0:
        return 0
    if parsed > 8:
        return 8
    return parsed


__all__ = [
    "DEFAULT_RESERVED_SLOTS",
    "DEFAULT_TOPIC_BOOST",
    "MATCH_COUNT_MULTIPLIER",
    "MIN_MATCH_COUNT",
    "resolve_reserved_slots",
]
