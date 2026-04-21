"""Canonical-template validator for LIA legal-doc markdown.

Phase 1.7 of `docs/next/ingestfixv1.md`. Port of Lia_contadores's
`validate_renta_corpus` semantics: a document conforms to the canonical
template when it carries, in order, the eight H2 sections; when its
``Identificacion`` bullet list exposes the seven required keys with real
values; and (in strict mode) when it also carries a ``Metadata v2`` block
exposing the fourteen canonical keys.

Heading comparison is accent-insensitive and case-insensitive so authors may
write ``## Identificación`` and still match.

NOTE on the "(sin datos)" sentinel:
- For the seven ``Identificacion`` keys this sentinel is treated as a MISSING
  value (the accountant needs real data before the doc is useful).
- For the fourteen ``Metadata v2`` keys this sentinel is ACCEPTED as a
  known-gap marker (the ingestion pipeline deliberately writes it when it
  cannot infer a field and we want the gap visible but non-blocking).

This module is pure (no I/O) except for the optional ``emit_events`` hook,
which delegates to ``lia_graph.instrumentation.emit_event``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from lia_graph import instrumentation

__all__ = [
    "ValidationResult",
    "CANONICAL_SECTIONS",
    "REQUIRED_IDENTIFICATION_KEYS",
    "REQUIRED_METADATA_V2_KEYS",
    "MISSING_VALUE_SENTINEL",
    "validate_canonical_template",
]

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

REQUIRED_IDENTIFICATION_KEYS: tuple[str, ...] = (
    "titulo",
    "autoridad",
    "numero",
    "fecha_emision",
    "fecha_vigencia",
    "ambito_tema",
    "doc_id",
)

REQUIRED_METADATA_V2_KEYS: tuple[str, ...] = (
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

MISSING_VALUE_SENTINEL = "(sin datos)"

_H2_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)
_BULLET_RE = re.compile(r"^\s*[-*]\s+(?P<body>.+?)\s*$")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ValidationResult:
    """Structured outcome of a canonical-template validation run."""

    ok: bool
    missing_sections: tuple[str, ...]
    sections_out_of_order: tuple[str, ...]
    missing_keys: tuple[str, ...]
    missing_metadata: tuple[str, ...]
    sections_found: tuple[str, ...]
    strict: bool


def _normalize(text: str) -> str:
    """Strip accents, lowercase, and collapse whitespace for comparison."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    collapsed = _WHITESPACE_RE.sub(" ", stripped).strip().lower()
    return collapsed


_CANONICAL_BY_NORM: dict[str, str] = {
    _normalize(name): name for name in CANONICAL_SECTIONS
}


def _extract_headings(markdown: str) -> list[tuple[int, str, str]]:
    """Return (position, canonical_name, raw_title) for each H2 that matches
    a canonical section. Non-canonical H2s are ignored."""
    out: list[tuple[int, str, str]] = []
    for match in _H2_RE.finditer(markdown):
        raw = match.group("title").strip()
        canonical = _CANONICAL_BY_NORM.get(_normalize(raw))
        if canonical is not None:
            out.append((match.start(), canonical, raw))
    return out


def _slice_section(markdown: str, start: int, end: int | None) -> str:
    body = markdown[start:end] if end is not None else markdown[start:]
    # Drop the heading line itself so bullet scanning starts in the body.
    newline = body.find("\n")
    return body[newline + 1 :] if newline != -1 else ""


def _parse_bullet_pairs(body: str) -> dict[str, str]:
    """Parse ``- key: value`` bullets into a dict (first-wins)."""
    pairs: dict[str, str] = {}
    for line in body.splitlines():
        m = _BULLET_RE.match(line)
        if not m:
            continue
        raw_body = m.group("body")
        if ":" not in raw_body:
            continue
        key, _, value = raw_body.partition(":")
        key_norm = key.strip().lower().replace(" ", "_")
        if key_norm and key_norm not in pairs:
            pairs[key_norm] = value.strip()
    return pairs


def _find_metadata_v2_span(markdown: str) -> tuple[int, int] | None:
    """Locate the ``## Metadata v2`` block (case/accent-insensitive)."""
    for match in _H2_RE.finditer(markdown):
        if _normalize(match.group("title")) == "metadata v2":
            start = match.start()
            # End at the next H2 heading, whatever it is.
            nxt = _H2_RE.search(markdown, match.end())
            end = nxt.start() if nxt else len(markdown)
            return start, end
    return None


def _identification_span(
    headings: list[tuple[int, str, str]],
    markdown: str,
) -> tuple[int, int] | None:
    for idx, (pos, canonical, _raw) in enumerate(headings):
        if canonical == "Identificacion":
            next_pos = headings[idx + 1][0] if idx + 1 < len(headings) else None
            return pos, next_pos if next_pos is not None else len(markdown)
    return None


def validate_canonical_template(
    markdown: str,
    *,
    strict: bool = True,
    emit_events: bool = False,
    filename: str | None = None,
) -> ValidationResult:
    """Validate ``markdown`` against the 8-section canonical template.

    Parameters
    ----------
    markdown:
        The full document text.
    strict:
        When True (default) the v2 metadata block must be present with all
        14 keys. When False, metadata is skipped entirely.
    emit_events:
        When True emit ``ingest.validate.ok`` / ``ingest.validate.failed``
        via :mod:`lia_graph.instrumentation`. Default False so tests and
        dry-runs do not pollute ``logs/events.jsonl``.
    filename:
        Optional filename used as a fallback for the event payload when the
        doc has no ``doc_id`` bullet.
    """

    headings = _extract_headings(markdown)
    found_in_order: list[str] = [canonical for _, canonical, _ in headings]

    # Missing sections (dedupe, preserve canonical order).
    seen = set(found_in_order)
    missing_sections = tuple(name for name in CANONICAL_SECTIONS if name not in seen)

    # Out-of-order: walk `found_in_order`, flag any section that appears
    # before a section that was already scheduled earlier in CANONICAL_SECTIONS.
    order_index = {name: idx for idx, name in enumerate(CANONICAL_SECTIONS)}
    out_of_order: list[str] = []
    highest_seen = -1
    for name in found_in_order:
        idx = order_index[name]
        if idx < highest_seen and name not in out_of_order:
            out_of_order.append(name)
        else:
            highest_seen = max(highest_seen, idx)

    # Identification keys
    missing_keys: list[str] = []
    id_span = _identification_span(headings, markdown)
    if id_span is None:
        # Whole section missing -> treat every key as missing.
        missing_keys = list(REQUIRED_IDENTIFICATION_KEYS)
    else:
        body = _slice_section(markdown, id_span[0], id_span[1])
        pairs = _parse_bullet_pairs(body)
        for key in REQUIRED_IDENTIFICATION_KEYS:
            value = pairs.get(key, "").strip()
            if not value or value.lower() == MISSING_VALUE_SENTINEL:
                missing_keys.append(key)

    # Metadata v2 (strict only)
    missing_metadata: list[str] = []
    if strict:
        md_span = _find_metadata_v2_span(markdown)
        if md_span is None:
            missing_metadata = list(REQUIRED_METADATA_V2_KEYS)
        else:
            # The v2 block must appear BEFORE the Identificacion H2.
            id_h2_pos = id_span[0] if id_span else None
            if id_h2_pos is not None and md_span[0] >= id_h2_pos:
                missing_metadata = list(REQUIRED_METADATA_V2_KEYS)
            else:
                body = _slice_section(markdown, md_span[0], md_span[1])
                pairs = _parse_bullet_pairs(body)
                for key in REQUIRED_METADATA_V2_KEYS:
                    if key not in pairs:
                        missing_metadata.append(key)
                    else:
                        value = pairs[key].strip()
                        # "(sin datos)" is accepted here as a known-gap marker;
                        # only an empty value counts as missing.
                        if not value:
                            missing_metadata.append(key)

    ok = (
        not missing_sections
        and not out_of_order
        and not missing_keys
        and (not strict or not missing_metadata)
    )

    result = ValidationResult(
        ok=ok,
        missing_sections=tuple(missing_sections),
        sections_out_of_order=tuple(out_of_order),
        missing_keys=tuple(missing_keys),
        missing_metadata=tuple(missing_metadata),
        sections_found=tuple(found_in_order),
        strict=strict,
    )

    if emit_events:
        doc_id = _doc_id_from_identification(markdown, id_span)
        label = doc_id or filename
        if ok:
            instrumentation.emit_event(
                "ingest.validate.ok",
                {
                    "doc_id": doc_id,
                    "filename": filename,
                    "label": label,
                    "sections_matched_count": len(found_in_order),
                },
            )
        else:
            instrumentation.emit_event(
                "ingest.validate.failed",
                {
                    "doc_id": doc_id,
                    "filename": filename,
                    "label": label,
                    "missing_sections": list(result.missing_sections),
                    "sections_out_of_order": list(result.sections_out_of_order),
                    "missing_keys": list(result.missing_keys),
                    "missing_metadata": list(result.missing_metadata),
                },
            )

    return result


def _doc_id_from_identification(
    markdown: str, id_span: tuple[int, int] | None
) -> str | None:
    if id_span is None:
        return None
    body = _slice_section(markdown, id_span[0], id_span[1])
    pairs = _parse_bullet_pairs(body)
    value = pairs.get("doc_id", "").strip()
    if not value or value.lower() == MISSING_VALUE_SENTINEL:
        return None
    return value
