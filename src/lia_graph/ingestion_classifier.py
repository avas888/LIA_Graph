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
_SYNONYM_HIGH = 0.80
_SYNONYM_MEDIUM = 0.50
_BODY_PREVIEW_CHARS = 2048

# next_v3 §7 — taxonomy-aware classifier prompt (redesigned per SME §1.3 mutex
# rules + §2 per-topic definitions). Off-by-default flag; promote via
# ``LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE={off|shadow|enforce}``. Note per
# ``docs/learnings/ingestion/parallelism-and-rate-limits.md`` — the new prompt
# is heavier (full taxonomy enumeration + 6 mutex rules + path-veto clause),
# so any full-corpus rebuild with this flag enabled should stay at
# ``--classifier-workers 4`` until the TokenBudget primitive lands.
_TAXONOMY_AWARE_FLAG = "LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE"


def classifier_taxonomy_mode() -> str:
    # Default `enforce` 2026-04-25 — validated through 5 rebuilds in next_v3 §13
    # (Cypher 6/6 binding, audit-clean rebuild). Operator's "no off flags"
    # directive applied. Heavier prompt → keep workers=4 until TokenBudget lands.
    raw = (os.getenv(_TAXONOMY_AWARE_FLAG) or "enforce").strip().lower()
    return raw if raw in ("off", "shadow", "enforce") else "enforce"


# ---------------------------------------------------------------------------
# next_v3 §13.6 Option K2 — rule-based path-veto layer above the LLM.
#
# 2026-04-25 Cypher verification (§13.3) showed the taxonomy-aware prompt
# couldn't override pre-existing wrong verdicts on 4 of 5 flip rows — the
# LLM treats the PATH VETO clause as guidance, not a hard constraint. This
# is the SME-predicted Option K2 (next_v2.md §K): a deterministic post-LLM
# sanity check that forces the correct topic when the source_path carries
# unambiguous signal.
#
# Rules fire only when the path substring is present. Outside of the
# RENTA/NORMATIVA/Normativa/ tree the LLM verdict is left untouched.
# ---------------------------------------------------------------------------

# Tuples of (path-substring, canonical_topic). Most-specific patterns MUST
# appear before less-specific ones — first match wins.
_PATH_VETO_RULES: tuple[tuple[str, str], ...] = (
    # --- ET Libro 1 (renta family), chapter-by-chapter ---
    ("02_Libro1_T1_Cap1_Ingresos",              "ingresos_fiscales_renta"),
    ("03_Libro1_T1_Cap2_Costos",                "costos_deducciones_renta"),
    ("04_Libro1_T1_Cap3_Renta_Bruta",           "declaracion_renta"),
    ("05_Libro1_T1_Cap4_Renta_Liquida",         "renta_liquida_gravable"),
    ("06_Libro1_T1_Cap5_Deducciones",           "costos_deducciones_renta"),
    ("07_Libro1_T1_Cap6_Rentas_Especiales_Presuntiva", "renta_presuntiva"),
    ("08_Libro1_T1_Cap7_Rentas_Exentas",        "rentas_exentas"),
    ("09_Libro1_T1_Caps8a11",                   "declaracion_renta"),
    ("10_Libro1_T2_Patrimonio",                 "patrimonio_fiscal_renta"),
    ("11_Libro1_T3_Ganancias_Ocasionales",      "ganancia_ocasional"),
    ("12_Libro1_T4_Remesas",                    "declaracion_renta"),
    ("13_Libro1_T5_Ajustes_Inflacion",          "declaracion_renta"),
    ("14_Libro1_T6_Regimen_Especial",           "regimen_tributario_especial_esal"),
    ("01_Libro1_T1_Sujetos_Pasivos",            "declaracion_renta"),
    ("00_Titulo_Preliminar",                    "declaracion_renta"),
    # --- ET other books ---
    ("15_Libro2_Retencion_Fuente",              "retencion_fuente_general"),
    ("16_Libro3_IVA",                           "iva"),
    ("17_Libro4_Timbre",                        "impuesto_timbre"),
    ("18_Libro5_Procedimiento_P1",              "procedimiento_tributario"),
    ("19_Libro5_Procedimiento_P2",              "procedimiento_tributario"),
    ("20_Libro6_GMF",                           "gravamen_movimiento_financiero_4x1000"),
    ("21_Libro7_ECE_CHC",                       "declaracion_renta"),
    ("22_Libro8_SIMPLE",                        "regimen_simple"),
)


def _apply_path_veto(
    filename: str, llm_verdict: str | None
) -> tuple[str | None, str | None, bool]:
    """Force the canonical topic for clear path-based signals.

    Returns ``(final_topic, veto_reason, rule_matched)``.

    - ``rule_matched`` is True when ANY rule in ``_PATH_VETO_RULES`` matches
      the filename, regardless of whether the LLM verdict was already correct.
      Downstream consumers MUST honor a matched rule by treating
      ``final_topic`` as authoritative against the document's legacy
      ``topic_key`` (which may carry stale path-inferred or alias-inferred
      values from before classification).
    - ``veto_reason`` is non-None only when the rule actually overrode a
      different LLM verdict — that is the signal to emit the
      ``classifier.path_veto_applied`` instrumentation event.
    """
    if not filename:
        return llm_verdict, None, False
    for needle, canonical in _PATH_VETO_RULES:
        if needle in filename:
            if llm_verdict == canonical:
                # Rule matched but LLM already correct — assert canonical
                # topic anyway so the doc.topic_key gets propagated.
                return canonical, None, True
            return canonical, f"path_veto:{needle}:{canonical}", True
    return llm_verdict, None, False

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

PASO 4: Si PASO 2 resolvio a un tema EXISTENTE, considera los subtemas candidatos \
disponibles para ese tema en esta lista (formato: tema -> subtemas):
{subtopic_list_with_labels}

Resuelve el subtema del documento bajo el tema resuelto en PASO 2:
- Si el documento encaja con UN subtema existente, mapea a ese sub_topic_key.
- Si es genuinamente nuevo bajo el tema resuelto, marca subtopic_is_new=true y propone un slug.
- Si el documento NO tiene subtema identificable (texto muy general o mezcla de subtemas), devuelve null.
- Importante: el subtema DEBE pertenecer al mismo tema resuelto en PASO 2.

Responde SOLO JSON valido con todos estos campos:
{{"generated_label": "...", "rationale": "...", "resolved_to_existing": "topic_key_o_null", \
"synonym_confidence": 0.0, "is_new_topic": false, \
"suggested_key": "slug_si_es_nuevo_o_null", "detected_type": "normative_base", \
"subtopic_resolved_to_existing": "sub_key_o_null", "subtopic_synonym_confidence": 0.0, \
"subtopic_is_new": false, "subtopic_suggested_key": "slug_subtopic_o_null", \
"subtopic_label": "etiqueta_humana_o_null"}}

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


_SUBTOPIC_TAXONOMY_CACHE: dict[str, SubtopicTaxonomy] = {}


def _get_cached_subtopic_taxonomy() -> SubtopicTaxonomy | None:
    """Return the singleton taxonomy, or None if it can't be loaded.

    Cached in module state to avoid re-reading the JSON on every classify
    call. Tests clear the cache by reassigning ``_SUBTOPIC_TAXONOMY_CACHE``.
    """
    cached = _SUBTOPIC_TAXONOMY_CACHE.get("default")
    if cached is not None:
        return cached
    try:
        loaded = load_subtopic_taxonomy()
    except (FileNotFoundError, ValueError):
        logger.info(
            "ingestion_classifier: subtopic taxonomy not available — "
            "PASO 4 will omit candidate list"
        )
        return None
    _SUBTOPIC_TAXONOMY_CACHE["default"] = loaded
    return loaded


def _build_subtopic_list_for_prompt(
    taxonomy: SubtopicTaxonomy | None,
) -> str:
    """Build the ``topic -> [sub_key: label]`` block fed to PASO 4.

    Compact format — one line per parent with pipe-separated children — so
    the prompt stays within the 500-token budget even with 86 subtopics.
    """
    if taxonomy is None or taxonomy.total_entries() == 0:
        return "(no hay subtemas curados disponibles)"
    lines: list[str] = []
    for parent in taxonomy.parents():
        children = taxonomy.get_candidates_for(parent)
        if not children:
            continue
        fragments = [
            f"{entry.key}: {entry.label}"
            for entry in sorted(children, key=lambda e: e.key)
        ]
        lines.append(f"- {parent} -> " + " | ".join(fragments))
    return "\n".join(lines) if lines else "(no hay subtemas curados disponibles)"


def _build_n2_prompt(filename: str, body_text: str) -> str:
    body_preview = (body_text or "")[:_BODY_PREVIEW_CHARS]
    taxonomy = _get_cached_subtopic_taxonomy()
    if classifier_taxonomy_mode() != "off":
        return _build_taxonomy_aware_prompt(
            filename=filename,
            body_preview=body_preview,
            subtopic_taxonomy=taxonomy,
        )
    return _AUTOGENERAR_PROMPT_TEMPLATE.format(
        topic_list_with_labels=_build_topic_list_for_prompt(),
        subtopic_list_with_labels=_build_subtopic_list_for_prompt(taxonomy),
        filename=filename,
        body_preview=body_preview,
    )


# ---------------------------------------------------------------------------
# next_v3 §7 — taxonomy-aware prompt template (SME deliverable 2026-04-25).
#
# The v1 prompt is topic-label-only and path-blind; SME §4.2 identified three
# upgrades:
#   1. Pick-from-list with full taxonomy + one-line definition per topic (not
#      just the label) — the LLM sees scope prose, not just the key name.
#   2. 6 mutex rules encoded as HARD constraints (IVA vs procedimiento, IVA
#      vs renta, societario-fusion, FE vs timbre, RUB vs RUT, laboral family).
#   3. Path-aware sanity check — a doc rooted under ``RENTA/NORMATIVA/`` must
#      default to the renta-family topic unless the body clearly overrides.
#
# Output schema is identical to the v1 prompt so downstream parsers
# (``_parse_n2_verdict``) don't need to change.
# ---------------------------------------------------------------------------

_TAXONOMY_AWARE_PROMPT_TEMPLATE = """\
Eres un clasificador de documentos para el corpus legal y contable \
colombiano (taxonomía v2, 2026-04-25).

Tu tarea: asignar UN `topic_key` al documento, eligiéndolo de la lista \
enumerada más abajo. Sigue las 6 REGLAS DURAS de mutua exclusividad y el \
PATH VETO antes de emitir la etiqueta final.

═══ PASO 1 — Lee el fragmento y genera una etiqueta libre (2-5 palabras, \
es-CO) que describa el propósito del documento.

═══ PASO 2 — Elige el `topic_key` de la lista oficial (formato `N. key — \
label — definición`):

{numbered_taxonomy}

REGLA POR DEFECTO — si el documento abarca varios SUBTEMAS de un mismo padre \
top-level, devuelve el PADRE. No fuerces un subtema específico si el \
contenido es transversal.

═══ PASO 3 — REGLAS DURAS DE MUTUA EXCLUSIVIDAD (no son sugerencias).

{mutex_block}

═══ PASO 4 — PATH VETO (heurística del ruta-en-el-repositorio).

Si `filename` contiene `RENTA/NORMATIVA/Normativa/` y el número del artículo \
que ves en el fragmento está en ET Libro 1 (arts. 5-364-6), el topic DEBE ser \
de la familia renta (`declaracion_renta`, `costos_deducciones_renta`, \
`ingresos_fiscales_renta`, `patrimonio_fiscal_renta`, `rentas_exentas`, \
`renta_liquida_gravable`, `renta_presuntiva`, `tarifas_renta_y_ttd`, \
`descuentos_tributarios_renta`, `ganancia_ocasional`). NUNCA `iva` ni \
`sagrilaft_ptee` para documentos rooted en `RENTA/`.

Si el filename / path indica Libro 3 ET (IVA, arts. 420-513) → `iva`. \
Si Libro 4 (timbre, arts. 514-540) → `impuesto_timbre`. \
Si Libro 5 (procedimiento + sanciones) → `procedimiento_tributario`.

═══ PASO 5 — Tipo de documento (igual que v1):
- normative_base: leyes, decretos, resoluciones, artículos del ET
- interpretative_guidance: conceptos DIAN, doctrina, análisis experto
- practica_erp: guías prácticas, checklists, paso a paso, plantillas

═══ PASO 6 — Subtema (opcional) desde esta lista (formato: tema → subtemas):
{subtopic_list_with_labels}

Si encaja con un subtema existente, mapea a ese `sub_topic_key`. Si no, \
devuelve `subtopic_resolved_to_existing: null`. Si el doc es transversal al \
padre (varios subtemas), devuelve null — ver regla por defecto de PASO 2.

═══ RESPUESTA — SOLO JSON válido, exactos estos campos:

{{"generated_label": "...", "rationale": "indica qué regla / path / mutex \
aplicaste", "resolved_to_existing": "topic_key_o_null", \
"synonym_confidence": 0.0, "is_new_topic": false, \
"suggested_key": "slug_si_es_nuevo_o_null", "detected_type": "normative_base", \
"subtopic_resolved_to_existing": "sub_key_o_null", \
"subtopic_synonym_confidence": 0.0, "subtopic_is_new": false, \
"subtopic_suggested_key": "slug_subtopic_o_null", "subtopic_label": \
"etiqueta_humana_o_null"}}

Archivo: {filename}
Fragmento:
{body_preview}
"""


@lru_cache(maxsize=1)
def _load_taxonomy_payload() -> dict[str, Any]:
    """Load the full taxonomy JSON (incl. definitions + mutex_rules)."""
    override = os.getenv("LIA_TOPIC_TAXONOMY_PATH", "").strip()
    path = Path(override) if override else DEFAULT_TOPIC_TAXONOMY_PATH
    if not path.exists():
        # Walk up from the module directory to find repo root copy.
        candidate = Path(__file__).resolve().parents[2] / DEFAULT_TOPIC_TAXONOMY_PATH
        if candidate.exists():
            path = candidate
    return json.loads(path.read_text(encoding="utf-8"))


def _build_numbered_taxonomy_block() -> str:
    """Numbered `N. key — label — definition` list of all active topics."""
    payload = _load_taxonomy_payload()
    lines: list[str] = []
    idx = 0
    for topic in payload.get("topics", []):
        if topic.get("status") == "deprecated":
            continue
        idx += 1
        key = topic.get("key", "").strip()
        label = topic.get("label", "").strip() or key
        definition = (topic.get("definition") or "").strip()
        parent = topic.get("parent_key")
        parent_note = f" (subtema de {parent})" if parent else ""
        if definition:
            # Keep the definition short — single line.
            short_def = definition.split("\n", 1)[0].strip()
            lines.append(f"{idx}. {key} — {label}{parent_note} — {short_def}")
        else:
            lines.append(f"{idx}. {key} — {label}{parent_note}")
    return "\n".join(lines)


def _build_mutex_block() -> str:
    """Render the 6 SME mutex rules as hard constraints numbered 1..6."""
    payload = _load_taxonomy_payload()
    rules = payload.get("mutex_rules", [])
    blocks: list[str] = []
    for rule in rules:
        rid = rule.get("id")
        name = rule.get("name", "").replace("_", " ")
        parts = [f"REGLA {rid} — {name}"]
        for key in ("when_iva", "when_procedimiento", "when_fe", "when_timbre",
                    "when_rub", "when_rut", "rule", "default", "exception",
                    "decision_rule"):
            val = rule.get(key)
            if val:
                parts.append(f"  · {key}: {val}")
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks)


def _build_taxonomy_aware_prompt(
    *,
    filename: str,
    body_preview: str,
    subtopic_taxonomy: SubtopicTaxonomy | None,
) -> str:
    """Assemble the taxonomy-aware prompt (next_v3 §7)."""
    return _TAXONOMY_AWARE_PROMPT_TEMPLATE.format(
        numbered_taxonomy=_build_numbered_taxonomy_block(),
        mutex_block=_build_mutex_block(),
        subtopic_list_with_labels=_build_subtopic_list_for_prompt(subtopic_taxonomy),
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
                prompt, temperature=0.0, max_tokens=500, timeout_seconds=10.0
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

    return _N2Result(
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
        subtopic_resolved_to_existing=n2.subtopic_resolved_to_existing,
        subtopic_synonym_confidence=n2.subtopic_synonym_confidence,
        subtopic_is_new=n2.subtopic_is_new,
        subtopic_suggested_key=n2.subtopic_suggested_key,
        subtopic_label=n2.subtopic_label,
        subtopic_parent_topic=n2.subtopic_parent_topic,
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


def _fuse_subtopic_confidence(n1: _N1Result, n2: _N2Result | None) -> float:
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
    n2: _N2Result | None,
    final_topic: str | None,
    taxonomy: SubtopicTaxonomy | None,
) -> _N2Result | None:
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
            return _N2Result(
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
    return _N2Result(
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
