"""LLM N2 prompt builders for the ingestion classifier.

Owns the two prompt templates (v1 / taxonomy-aware), the taxonomy + mutex
block builders, the topic / subtopic list formatters, and the cached
subtopic-taxonomy loader. Pure module — no LLM calls, no filesystem reads
beyond ``config/topic_taxonomy.json`` (``@lru_cache``-ed).

Module split per ``feedback_granular_edits``: prompts grow whenever a
taxonomy version ships, so they live in their own sibling rather than
bloating ``ingestion_classifier.py``.

Public surface (consumed by ``ingestion_classifier.classify_ingestion_document``
via the N2 cascade helpers):

* ``_AUTOGENERAR_PROMPT_TEMPLATE`` — v1 prompt (off-by-default since
  taxonomy-aware mode is now enforce-by-default).
* ``_TAXONOMY_AWARE_PROMPT_TEMPLATE`` — v2 prompt (default).
* ``_build_n2_prompt(filename, body_text)`` — top-level builder; routes to
  v1 or v2 based on the env flag handled by ``classifier_taxonomy_mode``.
* ``_slugify(text)`` — slug generator used by post-LLM sanity helpers.
* ``_get_cached_subtopic_taxonomy()`` — cached loader for PASO 4.
"""

from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from .subtopic_taxonomy_loader import (
    SubtopicTaxonomy,
    load_taxonomy as load_subtopic_taxonomy,
)
from .topic_guardrails import get_supported_topics, get_topic_label
from .topic_taxonomy import (
    DEFAULT_TOPIC_TAXONOMY_PATH,
    iter_topic_taxonomy_entries,
)


logger = logging.getLogger(__name__)


_BODY_PREVIEW_CHARS = 2048

_TAXONOMY_AWARE_FLAG = "LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE"


def classifier_taxonomy_mode() -> str:
    """Return ``off`` / ``shadow`` / ``enforce`` for the taxonomy-aware prompt.

    Default `enforce` 2026-04-25 — validated through 5 rebuilds in next_v3 §13
    (Cypher 6/6 binding, audit-clean rebuild). Operator's "no off flags"
    directive applied. Heavier prompt → keep workers=4 until TokenBudget lands.
    """
    raw = (os.getenv(_TAXONOMY_AWARE_FLAG) or "enforce").strip().lower()
    return raw if raw in ("off", "shadow", "enforce") else "enforce"


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


def _build_n2_prompt(filename: str, body_text: str) -> str:
    """Build the per-doc N2 prompt; routes to taxonomy-aware vs v1 by env flag."""
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


__all__ = [
    "_AUTOGENERAR_PROMPT_TEMPLATE",
    "_TAXONOMY_AWARE_PROMPT_TEMPLATE",
    "_BODY_PREVIEW_CHARS",
    "_SUBTOPIC_TAXONOMY_CACHE",
    "_TAXONOMY_AWARE_FLAG",
    "classifier_taxonomy_mode",
    "_slugify",
    "_build_topic_list_for_prompt",
    "_build_subtopic_list_for_prompt",
    "_get_cached_subtopic_taxonomy",
    "_load_taxonomy_payload",
    "_build_numbered_taxonomy_block",
    "_build_mutex_block",
    "_build_taxonomy_aware_prompt",
    "_build_n2_prompt",
]
