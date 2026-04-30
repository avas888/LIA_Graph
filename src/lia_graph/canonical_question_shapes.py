"""Canonical question-shape matcher.

Loads `config/canonical_question_shapes.json` and exposes a single
``match_canonical_shape`` entry point. Used by:

* ``orchestrator`` (sub-query topic resolution): when a shape matches,
  the keyword-fallback result is upgraded so the
  ``fix_v5_phase6b:subquery_inherited_parent`` branch does not steamroll
  it with the parent topic.
* ``planner.build_graph_retrieval_plan``: when a shape matches, the
  planner picks the ``tabular_reference`` evidence budget so calendar /
  table data survives the chunk-truncation limit.

The matcher is deliberately deterministic and config-driven so SMEs can
extend the table without code changes.
"""

from __future__ import annotations

import json
import re
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "canonical_question_shapes.json"
)
_LOAD_LOCK = threading.Lock()
_CACHED_SHAPES: tuple["CanonicalShape", ...] | None = None


@dataclass(frozen=True)
class CanonicalShape:
    id: str
    description: str
    topic: str
    secondary_topics: tuple[str, ...]
    subtopic_hint: str | None
    question_words_any: tuple[str, ...]
    subject_phrases_any: tuple[str, ...]
    qualifier_phrases_any: tuple[str, ...]
    evidence_shape_override: dict[str, object]
    render_hint: str | None


def _normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", ascii_text).lower().strip()


def _tuple_of_normalized(values: Iterable[object]) -> tuple[str, ...]:
    return tuple(
        _normalize_text(str(v))
        for v in (values or ())
        if str(v or "").strip()
    )


def _load_shapes_uncached(path: Path = _CONFIG_PATH) -> tuple[CanonicalShape, ...]:
    if not path.exists():
        return ()
    raw = json.loads(path.read_text(encoding="utf-8"))
    shapes: list[CanonicalShape] = []
    for entry in raw.get("shapes", ()):
        trigger = entry.get("trigger", {}) or {}
        shapes.append(
            CanonicalShape(
                id=str(entry.get("id") or "").strip(),
                description=str(entry.get("description") or ""),
                topic=str(entry.get("topic") or "").strip(),
                secondary_topics=_tuple_of_normalized(entry.get("secondary_topics") or ()),
                subtopic_hint=(str(entry.get("subtopic_hint")).strip() or None)
                if entry.get("subtopic_hint")
                else None,
                question_words_any=_tuple_of_normalized(trigger.get("question_words_any") or ()),
                subject_phrases_any=_tuple_of_normalized(trigger.get("subject_phrases_any") or ()),
                qualifier_phrases_any=_tuple_of_normalized(trigger.get("qualifier_phrases_any") or ()),
                evidence_shape_override=dict(entry.get("evidence_shape_override") or {}),
                render_hint=(str(entry.get("render_hint")).strip() or None)
                if entry.get("render_hint")
                else None,
            )
        )
    return tuple(shapes)


def load_canonical_shapes(*, force_reload: bool = False) -> tuple[CanonicalShape, ...]:
    global _CACHED_SHAPES
    if _CACHED_SHAPES is not None and not force_reload:
        return _CACHED_SHAPES
    with _LOAD_LOCK:
        if _CACHED_SHAPES is None or force_reload:
            _CACHED_SHAPES = _load_shapes_uncached()
    return _CACHED_SHAPES


def _group_satisfied(group: tuple[str, ...], normalized_message: str) -> bool:
    if not group:
        return True
    return any(phrase in normalized_message for phrase in group if phrase)


def match_canonical_shape(
    message: str,
    *,
    classified_topic: str | None = None,
) -> CanonicalShape | None:
    """Return the first canonical shape matching ``message``.

    A shape matches when every non-empty trigger group has at least one
    phrase present in the normalized message. When ``classified_topic``
    is provided, the shape's ``topic`` must additionally equal it (the
    canonical match is a *confidence boost* on a classifier decision,
    not an override of it). Pass ``classified_topic=None`` to ignore the
    topic gate (useful for first-cut routing in places that haven't
    classified yet).
    """
    if not message or not str(message).strip():
        return None
    normalized = _normalize_text(message)
    if not normalized:
        return None
    classified_norm = _normalize_text(classified_topic) if classified_topic else None
    for shape in load_canonical_shapes():
        if classified_norm is not None and shape.topic and shape.topic != classified_norm:
            continue
        if not _group_satisfied(shape.question_words_any, normalized):
            continue
        if not _group_satisfied(shape.subject_phrases_any, normalized):
            continue
        if not _group_satisfied(shape.qualifier_phrases_any, normalized):
            continue
        return shape
    return None


__all__ = [
    "CanonicalShape",
    "load_canonical_shapes",
    "match_canonical_shape",
]
