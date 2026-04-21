"""Hybrid heuristic + LLM section coercer (Phase 1.5 of ingestfixv1).

Rewrites arbitrary legal-document markdown into the canonical 8-section
template used by the rest of the ingestion pipeline. The coercer has
three cascading strategies:

1. **native** — input already matches the 8 canonical headings exactly;
   we simply re-emit in canonical order with metadata prepended.
2. **heuristic** — input uses alias headings (``## Vigencia``, ``## Cadena
   normativa``, etc.); the heuristic mapping table rewrites them. If at
   least 6/8 canonical sections resolve after mapping, we keep the
   heuristic output and fill any remaining gaps with ``(sin datos)``.
3. **llm** — fewer than 6/8 canonical sections resolve via heuristic and
   an LLM adapter is available; we ask the adapter to rewrite the body
   into the strict 8-section template and parse the response. If the
   adapter is unavailable or its response is malformed we fall back to
   the heuristic output with placeholders.

The canonical template:

    ## Identificacion
    ## Texto base referenciado (resumen tecnico)
    ## Regla operativa para LIA
    ## Condiciones de aplicacion
    ## Riesgos de interpretacion
    ## Relaciones normativas
    ## Checklist de vigencia
    ## Historico de cambios

Identification must carry a bullet list with seven keys:
``titulo``, ``autoridad``, ``numero``, ``fecha_emision``,
``fecha_vigencia``, ``ambito_tema``, ``doc_id``.

A ``## Metadata v2`` block with 14 keys is always emitted at the top of
the document (fields default to empty strings if not supplied; the
Phase 1.7 validator will flag missing values later).

Phase 1.6 (section chunker) and Phase 2 (corpus rebuild) import
``coerce_to_canonical_template`` from this module. The function is
side-effect-free except for emitting ``ingest.coerce.*`` trace events
via ``instrumentation.emit_event``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from .instrumentation import emit_event

__all__ = [
    "CoerceResult",
    "coerce_to_canonical_template",
    "CANONICAL_SECTIONS",
    "IDENTIFICATION_KEYS",
    "METADATA_V2_KEYS",
]


# ---------------------------------------------------------------------------
# Canonical template constants
# ---------------------------------------------------------------------------

#: The 8 canonical headings, in the exact order they must be emitted.
CANONICAL_SECTIONS: tuple[str, ...] = (
    "Identificacion",
    "Texto base referenciado (resumen tecnico)",
    "Regla operativa para LIA",
    "Condiciones de aplicacion",
    "Riesgos de interpretacion",
    "Relaciones normativas",
    "Checklist de vigencia",
    "Historico de cambios",
)

#: The 7 identification-bullet keys that must appear inside
#: ``## Identificacion`` as a ``- key: value`` list.
IDENTIFICATION_KEYS: tuple[str, ...] = (
    "titulo",
    "autoridad",
    "numero",
    "fecha_emision",
    "fecha_vigencia",
    "ambito_tema",
    "doc_id",
)

#: The 14 keys that must appear inside the top-of-document
#: ``## Metadata v2`` block.
METADATA_V2_KEYS: tuple[str, ...] = (
    "version_canonical_template",
    "coercion_method",
    "coercion_confidence",
    "source_tier",
    "authority_level",
    "parse_strategy",
    "source_type",
    "corpus_family",
    "vocabulary_labels",
    "review_priority",
    "country_scope",
    "language",
    "generated_at",
    "source_relative_path",
)

_PLACEHOLDER = "(sin datos)"


# ---------------------------------------------------------------------------
# Heuristic mapping table
# ---------------------------------------------------------------------------
#
# Each entry maps a case+accent-insensitive regex fragment matched against
# a candidate heading to one of the canonical section titles. The first
# canonical section whose pattern matches wins. Patterns are partial — we
# only require the fragment to appear somewhere in the normalized
# (lowercased, accent-folded) heading text.

_HEURISTIC_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "Identificacion",
        re.compile(r"(identificacion|encabezado|datos generales)"),
    ),
    (
        "Texto base referenciado (resumen tecnico)",
        re.compile(
            r"(texto base referenciado"
            r"|texto base"
            r"|texto normativo"
            r"|articulo(s)?"
            r"|contenido normativo"
            r"|considerandos"
            r"|cuerpo)"
        ),
    ),
    (
        "Regla operativa para LIA",
        re.compile(
            r"(regla operativa"
            r"|regla de uso"
            r"|regla lia"
            r"|regla para lia"
            r"|aplicacion practica)"
        ),
    ),
    (
        "Condiciones de aplicacion",
        re.compile(
            r"(condiciones de aplicacion"
            r"|condiciones"
            r"|criterios de aplicacion"
            r"|supuestos"
            r"|requisitos de aplicacion)"
        ),
    ),
    (
        "Riesgos de interpretacion",
        re.compile(
            r"(riesgos de interpretacion"
            r"|riesgos"
            r"|interpretacion"
            r"|advertencias"
            r"|alertas"
            r"|controversias)"
        ),
    ),
    (
        "Relaciones normativas",
        re.compile(
            r"(relaciones normativas"
            r"|cadena normativa"
            r"|normas referenciadas"
            r"|modificatorias"
            r"|jerarquia"
            r"|normas vinculadas)"
        ),
    ),
    (
        "Checklist de vigencia",
        re.compile(
            r"(checklist de vigencia"
            r"|estado de vigencia"
            r"|vigencia"
            r"|derogacion)"
        ),
    ),
    (
        "Historico de cambios",
        re.compile(
            r"(historico de cambios"
            r"|historico"
            r"|historia"
            r"|cambios"
            r"|modificaciones"
            r"|antecedentes)"
        ),
    ),
)


# ---------------------------------------------------------------------------
# Result dataclass + public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoerceResult:
    """Result of coercing a document into the canonical 8-section template."""

    coerced_markdown: str
    coercion_method: str
    sections_matched_count: int
    confidence: float
    missing_sections: tuple[str, ...]
    missing_keys: tuple[str, ...]
    llm_used: bool


def coerce_to_canonical_template(
    markdown: str,
    *,
    identification_hints: dict[str, str] | None = None,
    metadata_hints: dict[str, str] | None = None,
    adapter: Any | None = None,
    skip_llm: bool = False,
    filename: str | None = None,
) -> CoerceResult:
    """Coerce arbitrary markdown into the canonical 8-section template.

    Parameters
    ----------
    markdown:
        The raw document body (may or may not already be in canonical
        shape).
    identification_hints:
        Optional mapping from identification-key name (``titulo``,
        ``autoridad``, ...) to the value that should be emitted in the
        identification bullet list. Missing keys default to ``(sin datos)``.
    metadata_hints:
        Optional mapping from metadata-v2 key name to its value. Missing
        keys default to the empty string (Phase 1.7 validator flags those).
    adapter:
        Optional LLM adapter (any object that exposes
        ``generate_with_options`` or ``generate``). If ``None`` and the
        heuristic falls short, we resolve one via
        ``llm_runtime.resolve_llm_adapter``.
    skip_llm:
        If ``True``, never invoke the LLM — force the heuristic path.
    filename:
        Optional filename propagated into trace events.
    """

    identification_hints = dict(identification_hints or {})
    metadata_hints = dict(metadata_hints or {})
    filename_value = filename or ""

    sections, original_order = _parse_sections(markdown)
    canonical_map, matched_count = _apply_heuristic_mapping(sections, original_order)

    emit_event(
        "ingest.coerce.heuristic.start",
        {
            "filename": filename_value,
            "sections_matched_count": matched_count,
        },
    )

    # Native path — caller already produced the canonical shape.
    if _is_native_shape(canonical_map, matched_count):
        markdown_out = _render(
            canonical_map,
            identification_hints=identification_hints,
            metadata_hints=metadata_hints,
            coercion_method="native",
            coercion_confidence=1.0,
        )
        emit_event(
            "ingest.coerce.heuristic.done",
            {
                "filename": filename_value,
                "sections_matched_count": 8,
                "confidence": 1.0,
            },
        )
        return _build_result(
            markdown_out=markdown_out,
            coercion_method="native",
            matched_count=8,
            confidence=1.0,
            canonical_map=canonical_map,
            identification_hints=identification_hints,
            llm_used=False,
        )

    # Heuristic path when enough sections resolved.
    if matched_count >= 6:
        confidence = matched_count / 8.0
        markdown_out = _render(
            canonical_map,
            identification_hints=identification_hints,
            metadata_hints=metadata_hints,
            coercion_method="heuristic",
            coercion_confidence=confidence,
        )
        emit_event(
            "ingest.coerce.heuristic.done",
            {
                "filename": filename_value,
                "sections_matched_count": matched_count,
                "confidence": confidence,
            },
        )
        return _build_result(
            markdown_out=markdown_out,
            coercion_method="heuristic",
            matched_count=matched_count,
            confidence=confidence,
            canonical_map=canonical_map,
            identification_hints=identification_hints,
            llm_used=False,
        )

    # Low-confidence heuristic — try LLM unless forbidden.
    emit_event(
        "ingest.coerce.heuristic.done",
        {
            "filename": filename_value,
            "sections_matched_count": matched_count,
            "confidence": matched_count / 8.0,
        },
    )

    if not skip_llm:
        effective_adapter = adapter if adapter is not None else _resolve_adapter()
        if effective_adapter is None:
            emit_event(
                "ingest.coerce.llm.fallback",
                {
                    "filename": filename_value,
                    "reason": "adapter_unavailable",
                },
            )
        else:
            emit_event(
                "ingest.coerce.llm.start",
                {
                    "filename": filename_value,
                    "reason": "heuristic_confidence_low",
                },
            )
            llm_sections = _try_llm_rewrite(effective_adapter, markdown)
            if llm_sections is not None:
                llm_matched = sum(1 for key in CANONICAL_SECTIONS if llm_sections.get(key, "").strip())
                confidence = llm_matched / 8.0
                markdown_out = _render(
                    llm_sections,
                    identification_hints=identification_hints,
                    metadata_hints=metadata_hints,
                    coercion_method="llm",
                    coercion_confidence=confidence,
                )
                emit_event(
                    "ingest.coerce.llm.done",
                    {
                        "filename": filename_value,
                        "confidence": confidence,
                    },
                )
                return _build_result(
                    markdown_out=markdown_out,
                    coercion_method="llm",
                    matched_count=llm_matched,
                    confidence=confidence,
                    canonical_map=llm_sections,
                    identification_hints=identification_hints,
                    llm_used=True,
                )

            emit_event(
                "ingest.coerce.llm.fallback",
                {
                    "filename": filename_value,
                    "reason": "malformed_response",
                },
            )

    # Fallback: heuristic output with placeholders.
    confidence = matched_count / 8.0
    markdown_out = _render(
        canonical_map,
        identification_hints=identification_hints,
        metadata_hints=metadata_hints,
        coercion_method="heuristic",
        coercion_confidence=confidence,
    )
    return _build_result(
        markdown_out=markdown_out,
        coercion_method="heuristic",
        matched_count=matched_count,
        confidence=confidence,
        canonical_map=canonical_map,
        identification_hints=identification_hints,
        llm_used=False,
    )


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_sections(markdown: str) -> tuple[dict[str, str], list[str]]:
    """Split ``markdown`` on H2 boundaries.

    Returns a ``(sections, order)`` pair where ``sections`` maps the raw
    heading text (stripped, as it appeared in the source) to the body
    below it, and ``order`` preserves insertion order so callers can walk
    headings in document order when needed.
    """
    if not markdown:
        return {}, []

    sections: dict[str, str] = {}
    order: list[str] = []

    # Normalize line endings.
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")

    # Prepend a newline so the leading heading (if any) matches the
    # ``\n## `` boundary regex uniformly.
    working = "\n" + text

    heading_re = re.compile(r"\n##[ \t]+([^\n]+)\n", re.MULTILINE)
    matches = list(heading_re.finditer(working))
    if not matches:
        return {}, []

    for idx, match in enumerate(matches):
        raw_heading = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(working)
        body = working[start:end].strip("\n")
        # If duplicate heading, keep the first occurrence; append later body.
        if raw_heading in sections:
            sections[raw_heading] = (sections[raw_heading] + "\n\n" + body).strip()
        else:
            sections[raw_heading] = body
            order.append(raw_heading)

    return sections, order


def _normalize_heading(raw: str) -> str:
    """Lowercase + NFKD accent-fold + collapse whitespace."""
    text = unicodedata.normalize("NFKD", raw or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _apply_heuristic_mapping(
    sections: dict[str, str],
    order: list[str],
) -> tuple[dict[str, str], int]:
    """Map raw headings to canonical ones using :data:`_HEURISTIC_PATTERNS`.

    The return value is ``(canonical_map, matched_count)``. ``canonical_map``
    always contains all 8 canonical keys; sections that had no match map
    to ``""``.
    """
    canonical_map: dict[str, str] = {key: "" for key in CANONICAL_SECTIONS}
    used_canonical: set[str] = set()
    matched = 0

    for raw_heading in order:
        normalized = _normalize_heading(raw_heading)
        body = sections[raw_heading]
        for canonical_name, pattern in _HEURISTIC_PATTERNS:
            if canonical_name in used_canonical:
                continue
            if pattern.search(normalized):
                canonical_map[canonical_name] = body
                used_canonical.add(canonical_name)
                matched += 1
                break

    return canonical_map, matched


def _is_native_shape(canonical_map: dict[str, str], matched_count: int) -> bool:
    """True iff every canonical section had a matching heading."""
    if matched_count != 8:
        return False
    return all(key in canonical_map for key in CANONICAL_SECTIONS)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _format_bullet_list(pairs: list[tuple[str, str]]) -> str:
    return "\n".join(f"- {key}: {value}" for key, value in pairs)


def _ensure_identification_body(
    body: str,
    identification_hints: dict[str, str],
) -> str:
    """Ensure the identification body carries the 7 required bullet keys.

    If the incoming body already has ``- key: value`` lines for a key,
    they are preserved (first match wins). Anything missing is filled
    from ``identification_hints`` or ``(sin datos)``.
    """
    existing: dict[str, str] = {}
    for line in (body or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        remainder = stripped[2:]
        if ":" not in remainder:
            continue
        key, _, value = remainder.partition(":")
        key_norm = key.strip().lower().replace(" ", "_")
        if key_norm in IDENTIFICATION_KEYS and key_norm not in existing:
            existing[key_norm] = value.strip()

    pairs: list[tuple[str, str]] = []
    for key in IDENTIFICATION_KEYS:
        # Explicit hints take precedence over bullets already in the
        # source body — callers use hints to correct stale / partial
        # identification metadata.
        if key in identification_hints and identification_hints[key]:
            value = identification_hints[key]
        elif key in existing and existing[key]:
            value = existing[key]
        else:
            value = _PLACEHOLDER
        pairs.append((key, value))

    return _format_bullet_list(pairs)


def _build_metadata_block(
    *,
    metadata_hints: dict[str, str],
    coercion_method: str,
    coercion_confidence: float,
) -> str:
    overrides = {
        "coercion_method": coercion_method,
        "coercion_confidence": f"{coercion_confidence:.2f}",
    }
    pairs: list[tuple[str, str]] = []
    for key in METADATA_V2_KEYS:
        if key in overrides:
            value = overrides[key]
            # Allow caller to pin metadata_hints over our defaults when provided.
            if key in metadata_hints and metadata_hints[key]:
                value = metadata_hints[key]
        else:
            value = metadata_hints.get(key, "") or ""
        pairs.append((key, value))
    body = _format_bullet_list(pairs)
    return f"## Metadata v2\n{body}"


def _render(
    canonical_map: dict[str, str],
    *,
    identification_hints: dict[str, str],
    metadata_hints: dict[str, str],
    coercion_method: str,
    coercion_confidence: float,
) -> str:
    identification_body = _ensure_identification_body(
        canonical_map.get("Identificacion", ""),
        identification_hints,
    )

    out_blocks: list[str] = [
        _build_metadata_block(
            metadata_hints=metadata_hints,
            coercion_method=coercion_method,
            coercion_confidence=coercion_confidence,
        )
    ]

    for canonical_name in CANONICAL_SECTIONS:
        if canonical_name == "Identificacion":
            body = identification_body
        else:
            raw_body = canonical_map.get(canonical_name, "") or ""
            body = raw_body.strip() if raw_body.strip() else _PLACEHOLDER
        out_blocks.append(f"## {canonical_name}\n{body}")

    return "\n\n".join(out_blocks).rstrip() + "\n"


# ---------------------------------------------------------------------------
# LLM plumbing
# ---------------------------------------------------------------------------


_LLM_PROMPT_TEMPLATE = (
    "Eres un editor legal. Reescribe el siguiente documento en ESPANOL colombiano respetando\n"
    "EXACTAMENTE esta estructura markdown de 8 secciones (sin anadir ni quitar):\n\n"
    "## Identificacion\n"
    "## Texto base referenciado (resumen tecnico)\n"
    "## Regla operativa para LIA\n"
    "## Condiciones de aplicacion\n"
    "## Riesgos de interpretacion\n"
    "## Relaciones normativas\n"
    "## Checklist de vigencia\n"
    "## Historico de cambios\n\n"
    "Reglas:\n"
    "- Preserva el contenido legal; no inventes articulos ni decretos.\n"
    "- En \"Identificacion\" incluye una lista de vinetas con las claves: titulo, autoridad,"
    " numero, fecha_emision, fecha_vigencia, ambito_tema, doc_id (usa \"(sin datos)\" si falta).\n"
    "- Si una seccion no tiene contenido en el original, emite \"(sin datos)\".\n"
    "- Responde SOLO con el markdown final, sin explicaciones.\n\n"
    "Documento original:\n"
    "---\n"
    "{body}\n"
    "---\n"
)

_LLM_BODY_CHAR_LIMIT = 12000


def _resolve_adapter() -> Any | None:
    try:
        from .llm_runtime import resolve_llm_adapter
    except Exception:  # pragma: no cover - defensive
        return None
    try:
        adapter, _meta = resolve_llm_adapter()
    except Exception:
        return None
    return adapter


def _invoke_adapter(adapter: Any, prompt: str) -> str | None:
    """Call ``adapter`` using ``generate_with_options`` when available."""
    try:
        if hasattr(adapter, "generate_with_options"):
            result = adapter.generate_with_options(
                prompt,
                temperature=0.0,
                max_tokens=4096,
                timeout_seconds=30,
            )
            if isinstance(result, dict):
                content = result.get("content")
                if isinstance(content, str) and content.strip():
                    return content
                return None
            if isinstance(result, str) and result.strip():
                return result
            return None
        if hasattr(adapter, "generate"):
            out = adapter.generate(prompt)
            if isinstance(out, str) and out.strip():
                return out
            return None
    except Exception:
        return None
    return None


def _try_llm_rewrite(adapter: Any, markdown: str) -> dict[str, str] | None:
    """Send ``markdown`` through the LLM and parse the response.

    Returns a ``canonical_map`` if the response contains all 8 canonical
    headings; otherwise ``None`` so the caller can fall back.
    """
    body = (markdown or "")[:_LLM_BODY_CHAR_LIMIT]
    prompt = _LLM_PROMPT_TEMPLATE.format(body=body)

    response = _invoke_adapter(adapter, prompt)
    if not response:
        return None

    sections, _order = _parse_sections(response)
    if not sections:
        return None

    canonical_map, matched = _apply_heuristic_mapping(sections, list(sections.keys()))
    if matched < 8:
        return None
    return canonical_map


# ---------------------------------------------------------------------------
# Result assembly
# ---------------------------------------------------------------------------


def _build_result(
    *,
    markdown_out: str,
    coercion_method: str,
    matched_count: int,
    confidence: float,
    canonical_map: dict[str, str],
    identification_hints: dict[str, str],
    llm_used: bool,
) -> CoerceResult:
    missing_sections = tuple(
        name
        for name in CANONICAL_SECTIONS
        if not (canonical_map.get(name) or "").strip() and name != "Identificacion"
    )
    missing_keys = _compute_missing_identification_keys(
        canonical_map.get("Identificacion", ""),
        identification_hints,
    )
    return CoerceResult(
        coerced_markdown=markdown_out,
        coercion_method=coercion_method,
        sections_matched_count=matched_count,
        confidence=confidence,
        missing_sections=missing_sections,
        missing_keys=missing_keys,
        llm_used=llm_used,
    )


def _compute_missing_identification_keys(
    body: str,
    identification_hints: dict[str, str],
) -> tuple[str, ...]:
    """Keys that would have to fall back to ``(sin datos)``."""
    present: set[str] = set()
    for line in (body or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, _, value = stripped[2:].partition(":")
        key_norm = key.strip().lower().replace(" ", "_")
        if key_norm in IDENTIFICATION_KEYS and value.strip():
            present.add(key_norm)
    for key, value in identification_hints.items():
        if key in IDENTIFICATION_KEYS and value:
            present.add(key)
    return tuple(key for key in IDENTIFICATION_KEYS if key not in present)
