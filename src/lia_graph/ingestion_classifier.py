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
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from .topic_guardrails import get_supported_topics, get_topic_label
from .topic_router import detect_topic_from_text
from .topic_taxonomy import iter_topic_taxonomy_entries

logger = logging.getLogger(__name__)

_CONFIDENCE_THRESHOLD = 0.95
_SYNONYM_HIGH = 0.80
_SYNONYM_MEDIUM = 0.50
_BODY_PREVIEW_CHARS = 2048

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


_AUTOGENERAR_PROMPT_TEMPLATE = """\
Eres un clasificador de documentos para el corpus legal y contable colombiano.

PASO 1: Lee el fragmento del documento y genera UNA etiqueta de tema principal \
(2-5 palabras, en espanol) que describe el proposito del documento. \
No te limites a temas existentes; describe el contenido real.

PASO 2: Compara tu etiqueta generada contra esta lista de temas existentes:
{topic_list_with_labels}

Si tu etiqueta es sinonimo o subconjunto de un tema existente, mapea a ese tema.
Si es genuinamente distinto de TODOS los existentes, declara "nuevo".

PASO 3: Determina el tipo de documento:
- normative_base: leyes, decretos, resoluciones, articulos del ET
- interpretative_guidance: conceptos DIAN, doctrina, analisis experto
- practica_erp: guias practicas, checklists, paso a paso, plantillas

Responde SOLO JSON valido:
{{"generated_label": "...", "rationale": "...", "resolved_to_existing": "topic_key_o_null", \
"synonym_confidence": 0.0, "is_new_topic": false, \
"suggested_key": "slug_si_es_nuevo_o_null", "detected_type": "normative_base"}}

Archivo: {filename}
Fragmento:
{body_preview}
"""


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


# ---------------------------------------------------------------------------
# N2 — LLM cascade (synonym detection + type classification)
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Normalize free-form Spanish text into a topic-key slug.

    Lowercase, strip accents, collapse non-word runs to underscores,
    trim leading/trailing underscores, cap length at 60 chars.
    """
    if not text:
        return ""
    stripped = unicodedata.normalize("NFKD", text.lower())
    stripped = "".join(ch for ch in stripped if not unicodedata.combining(ch))
    stripped = re.sub(r"[^\w\s-]", "", stripped)
    stripped = re.sub(r"[\s\-]+", "_", stripped.strip())
    stripped = stripped.strip("_")
    return stripped[:60]


def _build_topic_list_for_prompt() -> str:
    """Build the ``- key: label`` block fed to the N2 prompt.

    Merges ``topic_guardrails.get_supported_topics()`` with the labels
    declared in ``topic_taxonomy.iter_topic_taxonomy_entries()`` so the
    LLM sees both scopes and curated display labels.
    """
    labels: dict[str, str] = {}
    for entry in iter_topic_taxonomy_entries():
        labels[entry.key] = entry.label
    for key in get_supported_topics():
        if key not in labels:
            labels[key] = get_topic_label(key)
    lines = [f"- {key}: {label}" for key, label in sorted(labels.items())]
    return "\n".join(lines)


def _build_n2_prompt(filename: str, body_text: str) -> str:
    body_preview = (body_text or "")[:_BODY_PREVIEW_CHARS]
    return _AUTOGENERAR_PROMPT_TEMPLATE.format(
        topic_list_with_labels=_build_topic_list_for_prompt(),
        filename=filename,
        body_preview=body_preview,
    )


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
                prompt, temperature=0.0, max_tokens=300, timeout_seconds=10.0
            )
            return str((result or {}).get("content") or "").strip()
        except Exception:
            logger.warning(
                "ingestion_classifier: generate_with_options fallo, cayendo a generate()",
                exc_info=True,
            )
    return str(adapter.generate(prompt) or "").strip()


def _parse_n2_response(raw: str) -> _N2Result | None:
    """Parse the strict-JSON N2 response into a ``_N2Result`` or None."""
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

    return _N2Result(
        generated_label=generated_label,
        rationale=rationale,
        resolved_to_existing=resolved_to_existing,
        synonym_confidence=synonym_confidence,
        is_new_topic=is_new_topic,
        suggested_key=suggested_key,
        detected_type=detected_type,
    )


def _apply_post_llm_sanity(n2: _N2Result, n1: _N1Result) -> _N2Result:
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

    return _N2Result(
        generated_label=n2.generated_label,
        rationale=n2.rationale,
        resolved_to_existing=resolved,
        synonym_confidence=synonym_confidence,
        is_new_topic=is_new_topic,
        suggested_key=suggested_key,
        detected_type=n2.detected_type,
    )


def _fuse_autogenerar_confidence(n1: _N1Result, n2: _N2Result | None) -> float:
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
            ``docs/next/subtopic_generationv1.md``) where the goal is to
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

    is_raw = combined < _CONFIDENCE_THRESHOLD
    exact_match = combined >= _CONFIDENCE_THRESHOLD
    requires_review = is_raw and not exact_match

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
    )


__all__ = [
    "AutogenerarResult",
    "classify_ingestion_document",
]
