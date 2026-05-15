"""N2 response parsing + post-LLM sanity + confidence fusion.

Pure helpers consumed by ``ingestion_classifier.classify_ingestion_document``
via the N2 cascade. Owns:

* JSON tolerance (``_safe_json_parse``).
* Structured-output parser (``_parse_n2_response``).
* Post-LLM invariants (``_apply_post_llm_sanity``) — invariant I3 from
  ingestionfix-v2: a ``resolved_to_existing`` not in the canonical registry
  flips to a new topic; an LLM "new topic" verdict that contradicts a
  high-confidence N1 keyword hit defers to N1.
* Confidence fusion (``_fuse_autogenerar_confidence`` topic,
  ``_fuse_subtopic_confidence`` subtopic) — Decision C1.
* Parent-topic stamping for PASO 4 subtopics (``_annotate_subtopic_parent``)
  — Invariant I4: cross-parent subtopics are dropped.

Module split per ``feedback_granular_edits``: these are pure functions
naturally grouped, so they live in their own sibling rather than bloating
``ingestion_classifier.py``.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .ingestion_classifier_prompts import _slugify
from .subtopic_taxonomy_loader import SubtopicTaxonomy
from .topic_guardrails import get_supported_topics


logger = logging.getLogger(__name__)


_SYNONYM_HIGH = 0.80
_SYNONYM_MEDIUM = 0.50


VALID_TYPES: frozenset[str] = frozenset(
    {"normative_base", "interpretative_guidance", "practica_erp"}
)

_TYPE_ALIASES: dict[str, str] = {
    "normativa": "normative_base",
    "norma": "normative_base",
    "interpretacion": "interpretative_guidance",
    "interpretación": "interpretative_guidance",
    "expertos": "interpretative_guidance",
    "secundaria": "interpretative_guidance",
    "practica": "practica_erp",
    "práctica": "practica_erp",
    "erp": "practica_erp",
    "loggro": "practica_erp",
    "terciaria": "practica_erp",
}


def _safe_json_parse(raw: str) -> dict[str, Any]:
    """Parse strict-JSON LLM response; tolerate leading/trailing noise."""
    cleaned = str(raw or "").strip()
    if not cleaned:
        return {}
    try:
        parsed = json.loads(cleaned)
        return dict(parsed) if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}


def _invoke_adapter(adapter: Any, prompt: str) -> str:
    """Call ``adapter.generate_with_options`` if available, else ``generate``."""
    if hasattr(adapter, "generate_with_options"):
        try:
            result = adapter.generate_with_options(
                prompt, temperature=0.0, max_tokens=500, timeout_seconds=10.0
            )
            return str((result or {}).get("content") or "").strip()
        except Exception:
            logger.warning(
                "ingestion_classifier: generate_with_options fallo, cayendo a generate()",
                exc_info=True,
            )
    return str(adapter.generate(prompt) or "").strip()


def _parse_n2_response(raw: str, *, n2_cls: Any) -> Any | None:
    """Parse the strict-JSON N2 response into an ``n2_cls`` instance or None.

    ``n2_cls`` is passed by the caller so this module doesn't need to import
    the dataclass from ``ingestion_classifier`` (avoids a circular import).
    """
    parsed = _safe_json_parse(raw)
    if not parsed:
        return None

    generated_label = str(parsed.get("generated_label") or "").strip()
    if not generated_label:
        return None

    rationale = str(parsed.get("rationale") or "").strip()
    resolved_raw = parsed.get("resolved_to_existing")
    resolved_to_existing: str | None = (
        str(resolved_raw).strip() if resolved_raw else None
    )
    if resolved_to_existing in {"", "null", "None"}:
        resolved_to_existing = None

    try:
        synonym_confidence = float(parsed.get("synonym_confidence") or 0.0)
    except (TypeError, ValueError):
        synonym_confidence = 0.0
    synonym_confidence = max(0.0, min(1.0, synonym_confidence))

    is_new_topic = bool(parsed.get("is_new_topic", False))

    suggested_raw = parsed.get("suggested_key")
    suggested_key: str | None = (
        str(suggested_raw).strip() if suggested_raw else None
    )
    if suggested_key in {"", "null", "None"}:
        suggested_key = None

    detected_type_raw = str(parsed.get("detected_type") or "").strip()
    detected_type = _TYPE_ALIASES.get(detected_type_raw, detected_type_raw) or None
    if detected_type and detected_type not in VALID_TYPES:
        detected_type = None

    # --- PASO 4 subtopic fields (ingestfix-v2) ---
    sub_resolved_raw = parsed.get("subtopic_resolved_to_existing")
    subtopic_resolved: str | None = (
        str(sub_resolved_raw).strip() if sub_resolved_raw else None
    )
    if subtopic_resolved in {"", "null", "None"}:
        subtopic_resolved = None

    try:
        subtopic_syn_conf = float(parsed.get("subtopic_synonym_confidence") or 0.0)
    except (TypeError, ValueError):
        subtopic_syn_conf = 0.0
    subtopic_syn_conf = max(0.0, min(1.0, subtopic_syn_conf))

    subtopic_is_new = bool(parsed.get("subtopic_is_new", False))

    sub_suggested_raw = parsed.get("subtopic_suggested_key")
    subtopic_suggested: str | None = (
        str(sub_suggested_raw).strip() if sub_suggested_raw else None
    )
    if subtopic_suggested in {"", "null", "None"}:
        subtopic_suggested = None

    sub_label_raw = parsed.get("subtopic_label")
    subtopic_label_parsed: str | None = (
        str(sub_label_raw).strip() if sub_label_raw else None
    )
    if subtopic_label_parsed in {"", "null", "None"}:
        subtopic_label_parsed = None

    return n2_cls(
        generated_label=generated_label,
        rationale=rationale,
        resolved_to_existing=resolved_to_existing,
        synonym_confidence=synonym_confidence,
        is_new_topic=is_new_topic,
        suggested_key=suggested_key,
        detected_type=detected_type,
        subtopic_resolved_to_existing=subtopic_resolved,
        subtopic_synonym_confidence=subtopic_syn_conf,
        subtopic_is_new=subtopic_is_new,
        subtopic_suggested_key=subtopic_suggested,
        subtopic_label=subtopic_label_parsed,
    )


def _apply_post_llm_sanity(n2: Any, n1: Any, *, n2_cls: Any) -> Any:
    """Enforce post-LLM invariants described in the plan §3.2.

    - ``resolved_to_existing`` not in the canonical registry → flip to a
      genuinely new topic.
    - LLM declared ``is_new_topic=True`` but N1 scored a topic above 0.7
      → override to N1 topic (N1 is deterministic and trustworthy there).
    - New topics without a ``suggested_key`` get a slug derived from the
      generated label.
    """
    supported = get_supported_topics()

    resolved = n2.resolved_to_existing
    is_new_topic = n2.is_new_topic
    synonym_confidence = n2.synonym_confidence
    suggested_key = n2.suggested_key

    if resolved and resolved not in supported:
        logger.info(
            "ingestion_classifier: resolved_to_existing '%s' not in registry — tratando como nuevo",
            resolved,
        )
        resolved = None
        is_new_topic = True
        synonym_confidence = 0.0

    if is_new_topic and n1.detected_topic and n1.topic_confidence > 0.7:
        logger.info(
            "ingestion_classifier: N1 override — keywords detectaron '%s' (%.2f), ignorando 'nuevo' del LLM",
            n1.detected_topic,
            n1.topic_confidence,
        )
        resolved = n1.detected_topic
        synonym_confidence = min(n1.topic_confidence, 0.95)
        is_new_topic = False
        suggested_key = None

    if is_new_topic and not suggested_key:
        suggested_key = _slugify(n2.generated_label) or None
    if not is_new_topic:
        suggested_key = None

    return n2_cls(
        generated_label=n2.generated_label,
        rationale=n2.rationale,
        resolved_to_existing=resolved,
        synonym_confidence=synonym_confidence,
        is_new_topic=is_new_topic,
        suggested_key=suggested_key,
        detected_type=n2.detected_type,
        subtopic_resolved_to_existing=n2.subtopic_resolved_to_existing,
        subtopic_synonym_confidence=n2.subtopic_synonym_confidence,
        subtopic_is_new=n2.subtopic_is_new,
        subtopic_suggested_key=n2.subtopic_suggested_key,
        subtopic_label=n2.subtopic_label,
        subtopic_parent_topic=n2.subtopic_parent_topic,
    )


def _fuse_autogenerar_confidence(n1: Any, n2: Any | None) -> float:
    """Fuse N1 + N2 into a single scalar confidence.

    Rules (plan §3.2):
      - N2 absent → N1 combined confidence.
      - N2 declared new topic → 0.70.
      - Synonym < 0.50 → 0.0 (forces manual review).
      - Synonym 0.50-0.79 → 0.0 (forces manual review).
      - Synonym >= 0.80 → base 0.85; +0.10 if N1 topic agrees with
        ``resolved_to_existing``; +0.05 if synonym >= 0.90.
    """
    if n2 is None:
        return n1.combined_confidence

    if n2.is_new_topic:
        return 0.70

    if n2.synonym_confidence < _SYNONYM_MEDIUM:
        return 0.0

    if n2.synonym_confidence < _SYNONYM_HIGH:
        return 0.0

    base = 0.85
    agreement_boost = 0.0
    high_syn_boost = 0.0
    if n1.detected_topic and n2.resolved_to_existing == n1.detected_topic:
        agreement_boost = 0.10
    if n2.synonym_confidence >= 0.90:
        high_syn_boost = 0.05

    return min(base + agreement_boost + high_syn_boost, 1.0)


def _fuse_subtopic_confidence(n1: Any, n2: Any | None) -> float:
    """Fuse subtopic confidence — mirrors :func:`_fuse_autogenerar_confidence`.

    Decision C1 (mirror topic-level fusion):
      - N2 absent or no subtopic verdict → 0.0.
      - Subtopic is new → 0.70.
      - synonym < 0.50 → 0.0 (review).
      - 0.50 <= synonym < 0.80 → 0.0 (review).
      - synonym >= 0.80 → base 0.85; +0.10 if N1 topic agrees with the
        parent that PASO 4 resolved under; +0.05 if synonym >= 0.90.
    """
    if n2 is None:
        return 0.0
    if not n2.subtopic_resolved_to_existing and not n2.subtopic_is_new:
        return 0.0
    if n2.subtopic_is_new:
        return 0.70
    syn = n2.subtopic_synonym_confidence
    if syn < _SYNONYM_HIGH:
        return 0.0
    base = 0.85
    agreement_boost = 0.0
    high_syn_boost = 0.0
    if (
        n1.detected_topic
        and n2.subtopic_parent_topic
        and n2.subtopic_parent_topic == n1.detected_topic
    ):
        agreement_boost = 0.10
    if syn >= 0.90:
        high_syn_boost = 0.05
    return min(base + agreement_boost + high_syn_boost, 1.0)


def _annotate_subtopic_parent(
    n2: Any | None,
    final_topic: str | None,
    taxonomy: SubtopicTaxonomy | None,
    *,
    n2_cls: Any,
) -> Any | None:
    """Stamp ``subtopic_parent_topic`` onto the parsed N2 result.

    When the LLM resolved to an existing subtopic, look it up in the
    taxonomy to find which parent it belongs to. Invariant I4: if that
    parent differs from ``final_topic``, the subtopic is dropped.

    For new-subtopic declarations, we trust the LLM's topic verdict from
    PASO 2 as the parent (same call guarantee — Decision A1).
    """
    if n2 is None:
        return n2
    resolved = n2.subtopic_resolved_to_existing
    parent: str | None = None
    if resolved and taxonomy is not None:
        for parent_topic, children in taxonomy.subtopics_by_parent.items():
            for entry in children:
                if entry.key == resolved:
                    parent = parent_topic
                    break
            if parent is not None:
                break
        # Subtopic key not present in taxonomy → treat as new.
        if parent is None:
            return n2_cls(
                generated_label=n2.generated_label,
                rationale=n2.rationale,
                resolved_to_existing=n2.resolved_to_existing,
                synonym_confidence=n2.synonym_confidence,
                is_new_topic=n2.is_new_topic,
                suggested_key=n2.suggested_key,
                detected_type=n2.detected_type,
                subtopic_resolved_to_existing=None,
                subtopic_synonym_confidence=0.0,
                subtopic_is_new=True,
                subtopic_suggested_key=n2.subtopic_suggested_key
                or (_slugify(n2.subtopic_label) if n2.subtopic_label else None),
                subtopic_label=n2.subtopic_label,
                subtopic_parent_topic=final_topic,
            )
    elif n2.subtopic_is_new:
        parent = final_topic
    return n2_cls(
        generated_label=n2.generated_label,
        rationale=n2.rationale,
        resolved_to_existing=n2.resolved_to_existing,
        synonym_confidence=n2.synonym_confidence,
        is_new_topic=n2.is_new_topic,
        suggested_key=n2.suggested_key,
        detected_type=n2.detected_type,
        subtopic_resolved_to_existing=n2.subtopic_resolved_to_existing,
        subtopic_synonym_confidence=n2.subtopic_synonym_confidence,
        subtopic_is_new=n2.subtopic_is_new,
        subtopic_suggested_key=n2.subtopic_suggested_key,
        subtopic_label=n2.subtopic_label,
        subtopic_parent_topic=parent,
    )


__all__ = [
    "VALID_TYPES",
    "_TYPE_ALIASES",
    "_SYNONYM_HIGH",
    "_SYNONYM_MEDIUM",
    "_safe_json_parse",
    "_invoke_adapter",
    "_parse_n2_response",
    "_apply_post_llm_sanity",
    "_fuse_autogenerar_confidence",
    "_fuse_subtopic_confidence",
    "_annotate_subtopic_parent",
]
