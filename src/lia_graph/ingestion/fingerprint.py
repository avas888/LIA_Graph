"""Composite document fingerprint (Decision C1 + K1 + prompt_version amendment).

This module implements the fingerprint used by the additive-corpus-v1 plan to
decide whether a document has changed between deltas. See
``docs/done/next/additive_corpusv1.md`` §0.8 and §4 Decisions C1 + K1.

**Contract.**

    doc_fingerprint = sha256(content_hash || "|" || canonical_classifier_json)

where the canonical classifier JSON is the sorted-key JSON of the classifier
output restricted to ``CLASSIFIER_FINGERPRINT_FIELDS`` with a stable default
for missing keys. A ``prompt_version`` field is included so that PASO 4 prompt
bumps manifest as a corpus-wide fingerprint change (controlled full-rebuild)
rather than silent drift.

**Why this specific shape** (all rationale is plan-ratified; keep the inline
comment minimal, defer to the plan for detail):

* ``source_tier`` is dropped per Decision K1 — it is not persisted on the
  ``documents`` table and K2 (widening schema) / K3 (classifier re-run) are
  both worse tradeoffs than dropping it.
* ``prompt_version`` defaults to ``"paso4_v1"`` (the effective value as of
  2026-04-22). If the PASO 4 classifier later exposes a live version string,
  both ingest and backfill paths should feed the same value in.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


# The field set that enters the fingerprint. Order does not matter (canonical
# JSON sorts keys); what matters is the exact membership.
CLASSIFIER_FINGERPRINT_FIELDS: tuple[str, ...] = (
    "topic_key",
    "subtopic_key",
    "requires_subtopic_review",
    "authority_level",
    "document_archetype",
    "knowledge_class",
    "source_type",
    "prompt_version",
)


# Stable sentinel for fields missing from the classifier output. Using a
# concrete string (rather than ``None``) means the canonical JSON stays
# deterministic across Python versions.
_MISSING_SENTINEL: str = "__absent__"


# Fallback used by both ingest and backfill paths when the classifier does
# not supply a live prompt version. Bumping this string triggers a corpus-wide
# fingerprint change on the next delta — which is the intended behavior per
# Decision C1's reviewer amendment.
DEFAULT_PROMPT_VERSION: str = "paso4_v1"


def _coerce(value: Any) -> Any:
    """Normalize a value into a JSON-serializable canonical form.

    Booleans stay booleans; strings are stripped; None becomes the missing
    sentinel. Anything else is coerced to its ``str()``.
    """
    if value is None:
        return _MISSING_SENTINEL
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    return text if text else _MISSING_SENTINEL


def canonical_classifier_json(output: Mapping[str, Any]) -> str:
    """Return a stable JSON string for the fingerprint field subset."""
    normalized: dict[str, Any] = {}
    for field in CLASSIFIER_FINGERPRINT_FIELDS:
        if field == "prompt_version":
            raw = output.get("prompt_version")
            normalized[field] = str(raw).strip() if raw else DEFAULT_PROMPT_VERSION
            continue
        normalized[field] = _coerce(output.get(field))
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_doc_fingerprint(
    *,
    content_hash: str,
    classifier_output: Mapping[str, Any],
) -> str:
    """Return sha256 fingerprint for a single document."""
    if not content_hash:
        raise ValueError("compute_doc_fingerprint requires a non-empty content_hash")
    canonical = canonical_classifier_json(classifier_output)
    payload = f"{content_hash}|{canonical}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def classifier_output_from_document_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Reconstruct a classifier-output shape from a persisted ``documents`` row.

    Used by ``scripts/ingestion/backfill_doc_fingerprint.py``. Per Decision K1, some
    source fields collapse during persistence:

    * ``document_archetype`` is stored in ``tipo_de_documento`` (fallback
      ``source_type``).
    * ``authority_level`` is stored in ``authority``.
    * ``topic_key`` is stored in ``topic`` (with ``tema`` as fallback; ingest
      writes both identically).
    * ``source_tier`` is dropped (Decision K1).

    The returned dict is the input to ``canonical_classifier_json`` — it only
    needs the fields in ``CLASSIFIER_FINGERPRINT_FIELDS``.
    """
    topic = row.get("topic") or row.get("tema")
    document_archetype = row.get("tipo_de_documento") or row.get("source_type")
    return {
        "topic_key": topic,
        "subtopic_key": row.get("subtema"),
        "requires_subtopic_review": bool(row.get("requires_subtopic_review") or False),
        "authority_level": row.get("authority"),
        "document_archetype": document_archetype,
        "knowledge_class": row.get("knowledge_class"),
        "source_type": row.get("source_type"),
        "prompt_version": row.get("prompt_version") or DEFAULT_PROMPT_VERSION,
    }


def classifier_output_from_corpus_document(document: Mapping[str, Any]) -> dict[str, Any]:
    """Reconstruct a classifier-output shape from a live ``CorpusDocument``-style mapping.

    The live-ingest path has access to the full classifier output in memory
    (see ``src/lia_graph/ingest_constants.py`` and the sink's payload build in
    ``supabase_sink.py``). This helper picks the same field subset so the
    fingerprint stays byte-identical to the backfill path (asserted in
    ``tests/test_fingerprint.py`` case (f)).
    """
    return {
        "topic_key": document.get("topic_key") or document.get("topic"),
        "subtopic_key": document.get("subtopic_key") or document.get("subtema"),
        "requires_subtopic_review": bool(
            document.get("requires_subtopic_review") or False
        ),
        "authority_level": document.get("authority_level") or document.get("authority"),
        "document_archetype": (
            document.get("document_archetype")
            or document.get("tipo_de_documento")
            or document.get("source_type")
        ),
        "knowledge_class": document.get("knowledge_class"),
        "source_type": document.get("source_type"),
        "prompt_version": document.get("prompt_version") or DEFAULT_PROMPT_VERSION,
    }


__all__ = [
    "CLASSIFIER_FINGERPRINT_FIELDS",
    "DEFAULT_PROMPT_VERSION",
    "canonical_classifier_json",
    "compute_doc_fingerprint",
    "classifier_output_from_document_row",
    "classifier_output_from_corpus_document",
]
