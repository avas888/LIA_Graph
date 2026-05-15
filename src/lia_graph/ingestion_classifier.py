"""Per-document AUTOGENERAR classifier (N1 deterministic + N2 LLM cascade).

Ported from ``Lia_contadores/src/lia_contador/ingestion_classifier.py`` (pre
v1.3 era, before the N2 cascade was retired upstream) into Lia_Graph. Pure
module: no filesystem reads, no network calls unless a caller supplies an
``LLMAdapter``; if no adapter is resolvable, the module degrades gracefully
to an N1-only verdict with ``is_raw=True`` whenever N1 cannot reach 0.95.

Public surface consumed by ``ui_ingest_run_controllers`` +
``ingestion_runtime`` is the single entry point
``classify_ingestion_document`` plus the frozen ``AutogenerarResult``
dataclass. Everything else is a leading-underscore helper that tests may
monkeypatch but callers should treat as private.

Convenciones:
- Identificadores en ingles
- Prompts + comentarios internos en espanol (es-CO)
"""

from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .subtopic_taxonomy_loader import (
    SubtopicEntry,
    SubtopicTaxonomy,
    load_taxonomy as load_subtopic_taxonomy,
)
from .topic_guardrails import get_supported_topics, get_topic_label
from .topic_router import detect_topic_from_text
from .topic_taxonomy import (
    DEFAULT_TOPIC_TAXONOMY_PATH,
    iter_topic_taxonomy_entries,
)

logger = logging.getLogger(__name__)

_CONFIDENCE_THRESHOLD = 0.95
_BODY_PREVIEW_CHARS = 2048

# Path-veto + corpusfix playbook override + N2 parsing/sanity/fusion all live
# in focused sibling modules so this orchestrator file doesn't grow each time
# a new BRECHAS-SEMANA trilogy, playbook batch, or N2 contract knob ships.
from .ingestion_classifier_path_veto import _PATH_VETO_RULES, _apply_path_veto
from .ingestion_classifier_playbook import (
    _PLAYBOOK_FILENAME_TO_TOPIC,
    _playbook_filename_topic_override,
)
from .ingestion_classifier_parsing import (  # noqa: F401  — re-exported
    VALID_TYPES,
    _TYPE_ALIASES,
    _SYNONYM_HIGH,
    _SYNONYM_MEDIUM,
    _annotate_subtopic_parent as _annotate_subtopic_parent_impl,
    _apply_post_llm_sanity as _apply_post_llm_sanity_impl,
    _fuse_autogenerar_confidence,
    _fuse_subtopic_confidence,
    _invoke_adapter,
    _parse_n2_response as _parse_n2_response_impl,
    _safe_json_parse,
)

# Filename → document-type patterns (Rubrica 0). First match wins; order
# matters — higher-confidence easy-detect conventions come first.
_FILENAME_TYPE_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"interpretaci[oó]n(es)?", re.I), "interpretative_guidance", 0.97),
    (re.compile(r"fuentes[\-_]secundarias", re.I), "interpretative_guidance", 0.97),
    (re.compile(r"marco[\-_]legal", re.I), "normative_base", 0.97),
    (re.compile(r"gu[ií]a[\-_]pr[aá]ctica", re.I), "practica_erp", 0.97),
    (re.compile(r"^(ET_art_|DUR_|Ley_|Decreto_|Res_)", re.I), "normative_base", 0.95),
    (re.compile(r"(concepto_dian|oficio_dian)", re.I), "interpretative_guidance", 0.85),
    (re.compile(r"^(L0|guia_|plantilla_|checklist_)", re.I), "practica_erp", 0.90),
    (re.compile(r"(erp|loggro|paso_a_paso)", re.I), "practica_erp", 0.85),
    (re.compile(r"(?:^|[_-])normativa(?:[_-]|$|\.)", re.I), "normative_base", 0.95),
    (re.compile(r"(?:^|[_-])expertos?(?:[_-]|$|\.)", re.I), "interpretative_guidance", 0.95),
    (re.compile(r"(?:^|[_-])practica(?:[_-]|$|\.)", re.I), "practica_erp", 0.95),
    # fix_v16_may §3.2 — expert-authored playbooks. Path/filename signals:
    #   - file in a `PLAYBOOKS/` directory, or
    #   - filename prefix `playbook_`.
    # Classified as interpretative_guidance — playbooks blend article
    # text + senior-contador operational judgment, closer to "doctrina"
    # than to checklist-only ERP guidance.
    (re.compile(r"(?:^|[/_-])playbooks?(?:[/_-]|$|\.)", re.I), "interpretative_guidance", 0.96),
]

# Filename prefix → topic (Rubrica 0b). Topics are Lia-canonical keys.
_FILENAME_TOPIC_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"^IVA[\-_]", re.I), "iva", 0.95),
    (re.compile(r"^ICA[\-_]", re.I), "ica", 0.95),
    (re.compile(r"^GMF[\-_]", re.I), "gmf", 0.95),
    (re.compile(r"^RET[\-_]", re.I), "retencion", 0.95),
    (re.compile(r"^NIIF[\-_]", re.I), "niif", 0.95),
    (re.compile(r"^NOM[\-_]", re.I), "laboral", 0.95),
    (re.compile(r"^FE[\-_]", re.I), "facturacion", 0.95),
    (re.compile(r"^EXO[\-_]", re.I), "exogena", 0.95),
    (re.compile(r"^RFL[\-_]", re.I), "reforma_laboral_2466", 0.95),
    (re.compile(r"^RST[\-_]", re.I), "rst_regimen_simple", 0.95),
    (re.compile(r"^SAG[\-_]", re.I), "sagrilaft_ptee", 0.95),
]


# N2 prompt builders + taxonomy-aware mode flag moved to focused sibling.
from .ingestion_classifier_prompts import (  # noqa: F401  — re-exported
    _AUTOGENERAR_PROMPT_TEMPLATE,
    _TAXONOMY_AWARE_PROMPT_TEMPLATE,
    _SUBTOPIC_TAXONOMY_CACHE,
    _TAXONOMY_AWARE_FLAG,
    _build_mutex_block,
    _build_n2_prompt,
    _build_numbered_taxonomy_block,
    _build_subtopic_list_for_prompt,
    _build_taxonomy_aware_prompt,
    _build_topic_list_for_prompt,
    _get_cached_subtopic_taxonomy,
    _load_taxonomy_payload,
    _slugify,
    classifier_taxonomy_mode,
)


@dataclass(frozen=True)
class _N1Result:
    detected_topic: str | None
    topic_confidence: float
    topic_source: str | None  # "keywords" | "filename" | None
    detected_type: str | None
    type_confidence: float
    type_source: str | None  # "filename" | None
    combined_confidence: float


@dataclass(frozen=True)
class _N2Result:
    generated_label: str
    rationale: str
    resolved_to_existing: str | None
    synonym_confidence: float
    is_new_topic: bool
    suggested_key: str | None
    detected_type: str | None
    # --- PASO 4 subtopic fields (ingestfix-v2) ---
    subtopic_resolved_to_existing: str | None = None
    subtopic_synonym_confidence: float = 0.0
    subtopic_is_new: bool = False
    subtopic_suggested_key: str | None = None
    subtopic_label: str | None = None
    # Parent-topic key under which the LLM emitted the subtopic. Populated
    # post-sanity-check; None when PASO 4 skipped or parent couldn't be
    # determined. Invariant I4 uses this to drop cross-parent subtopics.
    subtopic_parent_topic: str | None = None


@dataclass(frozen=True)
class AutogenerarResult:
    """Outcome of the two-stage AUTOGENERAR cascade for one document.

    Fields mirror the six ``autogenerar_*`` columns already declared on
    ``IngestionDocumentState`` / ``documents`` plus the derived fields the
    UI kanban needs to render the accept/edit affordance.
    """

    generated_label: str | None
    rationale: str | None
    resolved_to_existing: str | None
    synonym_confidence: float
    is_new_topic: bool
    suggested_key: str | None
    detected_type: str | None
    # --- derived ---
    detected_topic: str | None
    topic_confidence: float
    type_confidence: float
    combined_confidence: float
    classification_source: str  # "keywords" | "llm" | "filename"
    is_raw: bool
    requires_review: bool
    # --- ingestfix-v2 subtopic verdict (Phase 3) ---
    subtopic_key: str | None = None
    subtopic_label: str | None = None
    subtopic_confidence: float = 0.0
    subtopic_is_new: bool = False
    subtopic_suggested_key: str | None = None
    subtopic_resolved_to_existing: str | None = None
    subtopic_synonym_confidence: float = 0.0
    requires_subtopic_review: bool = False


# ---------------------------------------------------------------------------
# N1 — deterministic filename + body keyword scoring
# ---------------------------------------------------------------------------


def _apply_filename_patterns(
    filename: str,
) -> tuple[str | None, float, str | None, str | None, float]:
    """Apply filename type + topic regex patterns.

    Returns ``(detected_type, type_conf, type_source, fn_topic, fn_topic_conf)``.
    """
    detected_type: str | None = None
    type_conf = 0.0
    type_source: str | None = None
    for pattern, doc_type, conf in _FILENAME_TYPE_PATTERNS:
        if pattern.search(filename):
            detected_type = doc_type
            type_conf = conf
            type_source = "filename"
            break

    fn_topic: str | None = None
    fn_topic_conf = 0.0
    for pattern, topic, conf in _FILENAME_TOPIC_PATTERNS:
        if pattern.search(filename):
            fn_topic = topic
            fn_topic_conf = conf
            break

    return detected_type, type_conf, type_source, fn_topic, fn_topic_conf


def _run_n1_cascade(filename: str, body_text: str) -> _N1Result:
    """Level-1 deterministic classification: filename + body keywords.

    Topic comes from ``topic_router.detect_topic_from_text``; filename
    prefix override wins if its confidence beats the body keyword score.
    Type comes exclusively from filename patterns. Combined confidence is
    ``min`` when both fired, ``max`` when only one did, else ``0.0``.
    """
    body_preview = body_text[:_BODY_PREVIEW_CHARS] if body_text else ""
    topic_detection = detect_topic_from_text(body_preview, filename=filename)
    detected_topic = topic_detection.topic
    topic_confidence = float(topic_detection.confidence or 0.0)
    topic_source: str | None = "keywords" if detected_topic else None

    (
        detected_type,
        type_confidence,
        type_source,
        fn_topic,
        fn_topic_conf,
    ) = _apply_filename_patterns(filename)

    if fn_topic and fn_topic_conf > topic_confidence:
        detected_topic = fn_topic
        topic_confidence = fn_topic_conf
        topic_source = "filename"

    if detected_topic and detected_type:
        combined = min(topic_confidence, type_confidence)
    elif detected_topic or detected_type:
        combined = max(topic_confidence, type_confidence)
    else:
        combined = 0.0

    return _N1Result(
        detected_topic=detected_topic,
        topic_confidence=topic_confidence,
        topic_source=topic_source,
        detected_type=detected_type,
        type_confidence=type_confidence,
        type_source=type_source,
        combined_confidence=combined,
    )



def _parse_n2_response(raw: str) -> "_N2Result | None":
    """Thin wrapper around ingestion_classifier_parsing._parse_n2_response.

    Binds the local ``_N2Result`` dataclass so the parsing module stays free
    of orchestrator imports (avoids a circular import).
    """
    return _parse_n2_response_impl(raw, n2_cls=_N2Result)


def _apply_post_llm_sanity(n2: "_N2Result", n1: "_N1Result") -> "_N2Result":
    """Thin wrapper binding ``_N2Result`` for the parsing module."""
    return _apply_post_llm_sanity_impl(n2, n1, n2_cls=_N2Result)


def _annotate_subtopic_parent(
    n2: "_N2Result | None",
    final_topic: str | None,
    taxonomy: "SubtopicTaxonomy | None",
) -> "_N2Result | None":
    """Thin wrapper binding ``_N2Result`` for the parsing module."""
    return _annotate_subtopic_parent_impl(
        n2, final_topic, taxonomy, n2_cls=_N2Result
    )



def _resolve_adapter(adapter: Any | None) -> Any | None:
    """Return the adapter to use, resolving from llm_runtime if ``None``.

    The lazy import of ``llm_runtime`` is wrapped so this module can still
    be imported in environments where the runtime config / adapter stack
    is unavailable (unit test envs, static analysis, CI smoke).
    """
    if adapter is not None:
        return adapter
    try:
        from .llm_runtime import resolve_llm_adapter
    except ImportError:
        logger.info("ingestion_classifier: llm_runtime no disponible en este entorno")
        return None
    try:
        resolved, _runtime = resolve_llm_adapter()
    except Exception:
        logger.warning(
            "ingestion_classifier: resolve_llm_adapter fallo; degradando a N1-only",
            exc_info=True,
        )
        return None
    return resolved


def _run_n2_cascade(
    filename: str,
    body_text: str,
    n1: _N1Result,
    adapter: Any,
) -> _N2Result | None:
    """Build prompt, invoke adapter, parse response, apply post-LLM sanity."""
    prompt = _build_n2_prompt(filename=filename, body_text=body_text)
    try:
        raw_content = _invoke_adapter(adapter, prompt)
    except Exception:
        logger.warning("ingestion_classifier: adapter.generate fallo", exc_info=True)
        return None
    if not raw_content:
        return None

    parsed = _parse_n2_response(raw_content)
    if parsed is None:
        logger.warning(
            "ingestion_classifier: respuesta N2 no parseable, raw=%r",
            raw_content[:200],
        )
        return None

    return _apply_post_llm_sanity(parsed, n1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_ingestion_document(
    *,
    filename: str,
    body_text: str,
    adapter: Any | None = None,
    skip_llm: bool = False,
    always_emit_label: bool = False,
) -> AutogenerarResult:
    """Classify a single ingestion document via the N1 + (optional) N2 cascade.

    Args:
        filename: File name (relative path tail is fine). Drives filename
            regex scoring.
        body_text: Raw markdown/text body. Only the first ~2KB is fed to the
            LLM; body keyword scoring also scans this window.
        adapter: An object implementing the ``LLMAdapter`` protocol
            (``generate(prompt) -> str``) plus optional
            ``generate_with_options(prompt, *, temperature, max_tokens,
            timeout_seconds) -> dict``. When ``None``, the module tries to
            resolve the runtime-configured adapter via ``llm_runtime``; if
            that import or lookup fails, N2 is skipped entirely.
        skip_llm: When True, short-circuit past N2 even if N1 confidence
            < 0.95. Useful for fast tests and for the low-latency preflight
            path that only needs the N1 verdict.
        always_emit_label: When True, N2 fires even if N1 combined confidence
            is already ≥ 0.95. N1's primary assignment still wins when
            high-confidence; ``generated_label`` + ``rationale`` become
            pure metadata rather than a decision driver. Used by the
            subtopic-generation collection pass (see
            ``docs/done/next/subtopic_generationv1.md``) where the goal is to
            capture a free-form label on every doc, not to re-derive topic
            assignment. ``skip_llm=True`` wins over this flag — an
            explicit skip still skips.

    Returns:
        ``AutogenerarResult`` with N1-derived fields always populated and
        N2-derived fields populated only when the LLM path fired.
    """
    n1 = _run_n1_cascade(filename=filename, body_text=body_text)

    n2: _N2Result | None = None
    llm_invoked = False
    n1_high_confidence = n1.combined_confidence >= _CONFIDENCE_THRESHOLD

    should_invoke_llm = not skip_llm and (
        n1.combined_confidence < _CONFIDENCE_THRESHOLD or always_emit_label
    )

    if should_invoke_llm:
        resolved_adapter = _resolve_adapter(adapter)
        if resolved_adapter is not None:
            llm_invoked = True
            n2 = _run_n2_cascade(
                filename=filename,
                body_text=body_text,
                n1=n1,
                adapter=resolved_adapter,
            )

    # When ``always_emit_label`` forced N2 despite N1 being high-confidence,
    # keep N1's primary assignment intact. The LLM's generated_label + rationale
    # still flow through for the collection pass, but they must not override a
    # deterministic N1 verdict. Fusion is short-circuited back to N1.
    label_only_mode = always_emit_label and n1_high_confidence
    if label_only_mode and n2 is not None:
        combined = n1.combined_confidence
    else:
        combined = _fuse_autogenerar_confidence(n1, n2)

    # --- derive final topic + source + confidences ---
    detected_topic: str | None
    topic_confidence: float
    type_confidence: float
    classification_source: str

    if n2 is not None:
        if label_only_mode:
            # N1 already hit ≥ 0.95; LLM is label-only metadata here.
            detected_topic = n1.detected_topic
            topic_confidence = n1.topic_confidence
            classification_source = n1.topic_source or "keywords"
        elif n2.is_new_topic:
            detected_topic = n2.suggested_key or _slugify(n2.generated_label or "") or None
            topic_confidence = combined
            classification_source = "llm"
        elif n2.resolved_to_existing:
            detected_topic = n2.resolved_to_existing
            topic_confidence = combined if combined > 0 else n1.topic_confidence
            classification_source = "llm"
        else:
            # N2 parsed but neither resolved nor declared new — fall back to N1.
            detected_topic = n1.detected_topic
            topic_confidence = n1.topic_confidence
            classification_source = n1.topic_source or "keywords"
        type_confidence = n1.type_confidence
        detected_type = n2.detected_type or n1.detected_type
    else:
        detected_topic = n1.detected_topic
        topic_confidence = n1.topic_confidence
        type_confidence = n1.type_confidence
        detected_type = n1.detected_type
        # When LLM was invoked but returned nothing parseable, mark the
        # row raw-but-keywords so the UI knows N1 stands as the best guess.
        if llm_invoked:
            classification_source = "keywords"
        elif n1.topic_source == "filename":
            classification_source = "filename"
        else:
            classification_source = "keywords"

    # --- next_v3 §13.6 Option K2 — path-veto layer above the LLM --------
    # Applied regardless of the taxonomy-aware-prompt flag. The veto is a
    # deterministic safety net for cases the LLM mis-routes despite the
    # PATH VETO clause in the v2 prompt (SME-predicted in next_v2.md §K).
    #
    # When a rule matches we ALWAYS mark the verdict as path_veto-sourced —
    # not just when it overrode a wrong LLM verdict — because the document's
    # legacy `topic_key` (path-inferred / alias-inferred from the deterministic
    # pre-classifier pass) may still carry a stale value that the subtopic
    # pass would otherwise leave in place. Honoring the matched rule end-to-end
    # is the only way to guarantee the canonical topic propagates to Supabase.
    pre_veto_topic = detected_topic
    # corpusfix_v1 (2026-05-14) — explicit playbook stem → topic override.
    # Applied BEFORE the broader path-veto rules so the stem table wins on
    # match. Marks classification_source="path_veto" so the downstream
    # propagation in _assemble_doc_from_verdict fires.
    playbook_override = _playbook_filename_topic_override(filename)
    if playbook_override is not None and playbook_override != detected_topic:
        post_veto_topic: str | None = playbook_override
        veto_reason: str | None = f"playbook_filename:{playbook_override}"
        veto_rule_matched = True
    elif playbook_override is not None:
        # Stem match but LLM already correct — still assert the override
        # so doc.topic_key gets propagated even when N1/path inference
        # had drifted upstream.
        post_veto_topic = playbook_override
        veto_reason = None
        veto_rule_matched = True
    else:
        post_veto_topic, veto_reason, veto_rule_matched = _apply_path_veto(
            filename, detected_topic
        )
    if veto_rule_matched:
        detected_topic = post_veto_topic
        classification_source = "path_veto"
        # Bump confidence to signal the verdict is now deterministic, not
        # the blended N1/N2 fuse. Downstream `requires_review` logic uses
        # combined to decide if the row needs manual curation — a path-veto
        # match should ship without manual review.
        combined = max(combined, _CONFIDENCE_THRESHOLD)
        topic_confidence = max(topic_confidence, _CONFIDENCE_THRESHOLD)
        if veto_reason is not None:
            try:
                from .instrumentation import emit_event as _emit_veto

                _emit_veto(
                    "classifier.path_veto_applied",
                    {
                        "filename": filename,
                        "llm_verdict": pre_veto_topic,
                        "final_verdict": detected_topic,
                        "reason": veto_reason,
                    },
                )
            except Exception:  # pragma: no cover — instrumentation best-effort
                pass

    is_raw = combined < _CONFIDENCE_THRESHOLD
    exact_match = combined >= _CONFIDENCE_THRESHOLD
    requires_review = is_raw and not exact_match

    # --- PASO 4 subtopic verdict (ingestfix-v2) --------------------------
    taxonomy = _get_cached_subtopic_taxonomy()
    annotated_n2 = _annotate_subtopic_parent(n2, detected_topic, taxonomy)
    subtopic_key: str | None = None
    subtopic_label: str | None = None
    subtopic_conf = 0.0
    subtopic_is_new_flag = False
    subtopic_suggested: str | None = None
    subtopic_resolved: str | None = None
    subtopic_synonym: float = 0.0
    requires_subtopic_review = False

    if annotated_n2 is not None:
        subtopic_resolved = annotated_n2.subtopic_resolved_to_existing
        subtopic_synonym = annotated_n2.subtopic_synonym_confidence
        subtopic_is_new_flag = annotated_n2.subtopic_is_new
        subtopic_suggested = annotated_n2.subtopic_suggested_key
        subtopic_label = annotated_n2.subtopic_label
        subtopic_conf = _fuse_subtopic_confidence(n1, annotated_n2)

        # Invariant I4 — drop subtopic if parent mismatches final topic.
        parent = annotated_n2.subtopic_parent_topic
        cross_parent = (
            parent is not None
            and detected_topic is not None
            and parent != detected_topic
        )
        has_any_subtopic = bool(subtopic_resolved) or subtopic_is_new_flag

        if cross_parent:
            subtopic_key = None
            subtopic_label = None
            subtopic_conf = 0.0
            requires_subtopic_review = True
        elif subtopic_is_new_flag:
            # New subtopic — do not write until curator promotes it, but
            # surface the suggestion + flag for review.
            subtopic_key = None
            requires_subtopic_review = True
        elif subtopic_resolved and subtopic_conf >= _SYNONYM_HIGH:
            subtopic_key = subtopic_resolved
            if subtopic_label is None and taxonomy is not None:
                entry = None
                for children in taxonomy.subtopics_by_parent.values():
                    for child in children:
                        if child.key == subtopic_resolved:
                            entry = child
                            break
                    if entry is not None:
                        break
                if entry is not None:
                    subtopic_label = entry.label
        elif has_any_subtopic:
            # LLM emitted something but confidence too low — flag for review.
            subtopic_key = None
            requires_subtopic_review = True

    try:
        from .instrumentation import emit_event as _emit

        _emit(
            "subtopic.ingest.classified",
            {
                "filename": filename,
                "topic": detected_topic,
                "subtopic_key": subtopic_key,
                "subtopic_confidence": round(subtopic_conf, 4),
                "requires_subtopic_review": requires_subtopic_review,
                "subtopic_is_new": subtopic_is_new_flag,
            },
        )
    except Exception:
        # Observability must never break classification.
        logger.debug("ingestion_classifier: subtopic.ingest.classified emit failed", exc_info=True)

    return AutogenerarResult(
        generated_label=n2.generated_label if n2 else None,
        rationale=n2.rationale if n2 else None,
        resolved_to_existing=n2.resolved_to_existing if n2 else None,
        synonym_confidence=n2.synonym_confidence if n2 else 0.0,
        is_new_topic=bool(n2.is_new_topic) if n2 else False,
        suggested_key=n2.suggested_key if n2 else None,
        detected_type=detected_type,
        detected_topic=detected_topic,
        topic_confidence=topic_confidence,
        type_confidence=type_confidence,
        combined_confidence=combined,
        classification_source=classification_source,
        is_raw=is_raw,
        requires_review=requires_review,
        subtopic_key=subtopic_key,
        subtopic_label=subtopic_label,
        subtopic_confidence=subtopic_conf,
        subtopic_is_new=subtopic_is_new_flag,
        subtopic_suggested_key=subtopic_suggested,
        subtopic_resolved_to_existing=subtopic_resolved,
        subtopic_synonym_confidence=subtopic_synonym,
        requires_subtopic_review=requires_subtopic_review,
    )


__all__ = [
    "classifier_taxonomy_mode",
    "_apply_path_veto",
    "_PATH_VETO_RULES",
    "AutogenerarResult",
    "classify_ingestion_document",
]
