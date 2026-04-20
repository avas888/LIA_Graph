"""Resolve a human-friendly display title for any source document.

Extracted from `ui_source_view_processors.py` during granularize-v2
(2026-04-20). The host module was 1609 LOC of mixed source-view concerns;
this cluster has a single clear architectural identity and is consumed
across at least four modules (`ui_source_view_processors`,
`ui_citation_profile_builders`, `ui_normative_processors`,
`ui_expert_extractors`, plus `ui_server`'s routing layer), so it deserves
its own seam.

The pipeline, top-to-bottom:

  1. `_resolve_source_display_title` — given a row and optional raw text,
     walk an ordered candidate list (source_label → title → article_id →
     form-number inference → notes → subtema → first heading → filename
     stem → doc_id) and return the first one that is non-generic.
  2. `_pick_source_display_title` — orchestrates requested vs resolved
     rows, then falls back to `_title_from_normative_identity` (parses
     `entity_id` like `decreto:2229:2023` → `Decreto 2229 de 2023`), then
     tries to extract "Tema principal" from the document body, and only
     then surrenders to `_humanize_technical_title` on the raw slug.
  3. `_looks_like_technical_title` / `_humanize_technical_title` — the
     junk-title detector + Spanish-title-cased slug cleaner used to
     rescue filename-derived titles.

Also co-located here because the title pipeline uses them:

  * `_source_url_label_for_filename` + `_build_source_download_filename`
    — build the `.pdf`/`.md`/`.txt` filename the download button gets.
  * `_normalize_source_reference_text` — shared by the reference-anchor
    matcher in the host module; moved here because
    `_is_generic_source_title` depends on it and it's the smallest unit
    (5 LOC) to avoid a circular import.
  * `_SOURCE_FORM_REFERENCE_RE`, `_SOURCE_ARTICLE_ID_LINE_RE`,
    `_SOURCE_HEADING_LINE_RE` — regexes used for title inference; also
    re-used by the host's reference-anchor cluster, which re-imports
    them.

Cross-module dependencies kept as `_ui()` lazy accessors so the
monkeypatch-in-tests pattern used elsewhere continues to work:
`_sanitize_url_candidate`, `_slugify_filename_part`, `_clean_markdown_inline`
(all in `ui_text_utilities`); `_GENERIC_SOURCE_TITLES` (in `ui_server`).
`_extract_expert_document_metadata` is late-imported inside
`_pick_source_display_title` only; it is the only direct import into a
sibling UI module and the late binding avoids any circular load concern.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .contracts.advisory import _notes_is_internal


# ---------------------------------------------------------------------------
# Shared regexes for title inference + reference anchoring
# ---------------------------------------------------------------------------

_SOURCE_FORM_REFERENCE_RE = re.compile(
    r"\b(?:formulario|formato|form\.?|f\.)\s*([0-9]{2,5}[A-Z]?)\b", re.IGNORECASE
)
_SOURCE_ARTICLE_ID_LINE_RE = re.compile(r"^\s*-\s*article_id:\s*(.+?)\s*$", re.IGNORECASE)
_SOURCE_HEADING_LINE_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")

# Technical prefixes in document filenames (corpus type codes).
# Applied iteratively from the left until no more match.
_TECHNICAL_PREFIX_TOKEN_RE = re.compile(
    r"^(?:"
    r"t|pt|n|e|ref|san|dat|niif|pen|cam|eme|rut"           # corpus type codes
    r"|normativa|expertos|addendum"                          # knowledge layer words
    r"|[a-z]\d{2}"                                           # short codes like n01, e01, a01
    r"|ingest|corpus"                                        # ingestion scaffolding
    r")(?:[_\s-]|$)",
    re.IGNORECASE,
)


def _ui() -> Any:
    """Lazy accessor for `lia_graph.ui_server` (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


def _normalize_source_reference_text(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def _source_url_label_for_filename(source_url: str, *, max_len: int = 120) -> str:
    clean_url = _ui()._sanitize_url_candidate(str(source_url or "").strip())
    if not clean_url:
        return ""
    try:
        parsed = urlparse(clean_url)
    except ValueError:
        return ""
    host = _ui()._slugify_filename_part(parsed.netloc.replace("www.", ""), max_len=48)
    path = _ui()._slugify_filename_part(parsed.path, max_len=64)
    query = _ui()._slugify_filename_part(parsed.query, max_len=24)
    parts = [part for part in (host, path, query) if part]
    if not parts:
        return ""
    return "_".join(parts)[:max_len].strip("_")


def _build_source_download_filename(
    *,
    row: dict[str, Any],
    doc_id: str,
    download_format: str,
    fallback_title: str,
) -> str:
    extension = {"pdf": ".pdf", "md": ".md", "txt": ".txt"}.get(str(download_format or "").strip().lower(), ".bin")
    title_candidates = (
        str(fallback_title or "").strip(),
        str(row.get("title", "")).strip(),
        str(row.get("subtema", "")).strip(),
        str(doc_id or "").strip(),
        "Documento",
    )
    title_part = ""
    for candidate in title_candidates:
        title_part = _ui()._slugify_filename_part(candidate, max_len=84)
        if title_part:
            break
    if not title_part:
        title_part = "Documento"

    url_part = _source_url_label_for_filename(str(row.get("url", "")).strip(), max_len=112)
    if url_part:
        return f"{title_part}_{url_part}{extension}"
    return f"{title_part}{extension}"


def _is_generic_source_title(title: str, *, authority: str = "") -> bool:
    normalized_title = _normalize_source_reference_text(title)
    normalized_authority = _normalize_source_reference_text(authority)
    if not normalized_title:
        return True
    if normalized_title in _ui()._GENERIC_SOURCE_TITLES:
        return True
    if normalized_authority and normalized_title == normalized_authority:
        return True
    return normalized_title.isalpha() and len(normalized_title) <= 12


def _extract_source_title_from_raw_text(raw_text: str) -> str:
    text = str(raw_text or "")
    if not text.strip():
        return ""

    for line in text.splitlines()[:24]:
        article_match = _SOURCE_ARTICLE_ID_LINE_RE.match(line)
        if article_match:
            article_id = _ui()._clean_markdown_inline(article_match.group(1))
            if article_id:
                return article_id

    for line in text.splitlines()[:12]:
        heading_match = _SOURCE_HEADING_LINE_RE.match(line)
        if not heading_match:
            continue
        heading = _ui()._clean_markdown_inline(heading_match.group(1))
        heading = re.sub(r"\s*-\s*Plantilla t[eé]cnica\s*$", "", heading, flags=re.IGNORECASE)
        if heading:
            return heading
    return ""


def _infer_source_title_from_url_or_path(*, row: dict[str, Any], doc_id: str) -> str:
    candidates = [
        str(row.get("url") or "").strip(),
        str(row.get("provenance_uri") or "").strip(),
        str(row.get("relative_path") or "").strip(),
        str(doc_id or "").strip(),
    ]
    for candidate in candidates:
        form_match = _SOURCE_FORM_REFERENCE_RE.search(candidate)
        if form_match:
            if re.search(r"guia|como[-_\s]?diligenciar", candidate, re.IGNORECASE):
                return f"Guía operativa Formulario {form_match.group(1)}"
            return f"Formulario {form_match.group(1)}"
    return ""


def _resolve_source_display_title(
    *,
    row: dict[str, Any],
    doc_id: str,
    raw_text: str = "",
    public_text: str = "",
) -> str:
    del public_text
    authority = str(row.get("authority") or row.get("autoridad") or "").strip()
    candidates = (
        str(row.get("source_label") or "").strip(),
        str(row.get("title") or "").strip(),
        str(row.get("article_id") or "").strip(),
        _infer_source_title_from_url_or_path(row=row, doc_id=doc_id),
        "" if _notes_is_internal(str(row.get("notes") or "")) else str(row.get("notes") or "").strip(),
        str(row.get("subtema") or "").strip(),
        _extract_source_title_from_raw_text(raw_text),
        Path(str(row.get("relative_path") or "")).stem.replace("_", " ").strip(),
        str(doc_id or "").strip(),
    )
    for candidate in candidates:
        clean = _ui()._clean_markdown_inline(candidate)
        if not clean:
            continue
        if _is_generic_source_title(clean, authority=authority):
            continue
        return clean
    return authority or "Fuente"


def _title_from_normative_identity(row: dict[str, Any]) -> str:
    """Parse entity_id or reference_identity_keys into a human title.

    E.g. entity_id="decreto:2229:2023" → "Decreto 2229 de 2023"
         entity_id="resolucion_dian:238:2025" → "Resolución DIAN 238 de 2025"
    """
    _NORM_TYPES = {
        "decreto": "Decreto",
        "ley": "Ley",
        "resolucion": "Resolución",
        "resolucion_dian": "Resolución DIAN",
        "concepto": "Concepto",
        "concepto_dian": "Concepto DIAN",
        "circular": "Circular",
    }
    entity_id = str(row.get("entity_id") or "").strip().lower()
    if not entity_id:
        keys = list(row.get("reference_identity_keys") or [])
        if keys:
            entity_id = str(keys[0]).strip().lower()
    if not entity_id:
        return ""
    parts = entity_id.split(":")
    if len(parts) >= 3 and parts[0] in _NORM_TYPES:
        return f"{_NORM_TYPES[parts[0]]} {parts[1]} de {parts[2]}"
    if len(parts) == 2 and parts[0] in _NORM_TYPES:
        return f"{_NORM_TYPES[parts[0]]} {parts[1]}"
    return ""


def _pick_source_display_title(
    *,
    requested_row: dict[str, Any],
    resolved_row: dict[str, Any],
    doc_id: str,
    raw_text: str = "",
    public_text: str = "",
) -> str:
    requested_title = _resolve_source_display_title(
        row=requested_row,
        doc_id=doc_id,
        raw_text=raw_text,
        public_text=public_text,
    )
    requested_authority = str(requested_row.get("authority") or requested_row.get("autoridad") or "").strip()
    if not _is_generic_source_title(requested_title, authority=requested_authority):
        # Check if the resolved title is still a technical identifier
        if not _looks_like_technical_title(requested_title):
            return requested_title
    # Before trying the resolved_row (which may be a different document due to
    # provenance_uri collisions), try extracting a clean title from the
    # requested row's own normative identity keys.
    normative_title = _title_from_normative_identity(requested_row)
    if normative_title:
        return normative_title
    resolved_title = _resolve_source_display_title(
        row=resolved_row,
        doc_id=doc_id,
        raw_text=raw_text,
        public_text=public_text,
    )
    if not _looks_like_technical_title(resolved_title):
        return resolved_title
    # Fallback: try extracting "Tema principal" from document body
    from .ui_expert_extractors import _extract_expert_document_metadata
    meta = _extract_expert_document_metadata(public_text or raw_text)
    tema = meta.get("tema_principal", "").strip()
    if tema:
        return tema[:180] if len(tema) > 180 else tema
    # Last resort: humanize the technical filename
    humanized = _humanize_technical_title(resolved_title)
    return humanized or resolved_title


def _looks_like_technical_title(title: str) -> bool:
    """Detect titles that look like technical document identifiers."""
    clean = str(title or "").strip()
    if not clean:
        return False
    lowered = clean.lower()
    # Contains 8-character hex hashes
    if re.search(r"\b[0-9a-f]{8}\b", lowered):
        return True
    # Contains "part N" suffixes
    if re.search(r"\bpart[_\s-]?\d+\b", lowered):
        return True
    # "Ingesta RAG" / "rag ready" internal headings
    if "ingesta rag" in lowered or "rag ready" in lowered:
        return True
    # "Carga usuario" internal labels
    if lowered.startswith("carga usuario"):
        return True
    # Internal corpus "bloque NN" identifiers (e.g. "bloque 02 formularios y formalidades")
    if re.match(r"^bloque\s+\d", lowered):
        return True
    # File extensions (e.g. "conciliacion fiscal.md")
    if re.search(r"\.\w{1,4}$", lowered):
        return True
    return False


def _humanize_technical_title(title: str) -> str:
    """Clean a technical filename-derived title into a human-readable one.

    Strips hex hashes, 'part N' suffixes, technical prefixes, and applies
    Spanish title case.
    """
    clean = str(title or "").strip()
    if not clean:
        return ""
    # Strip file extensions (e.g. ".md", ".pdf")
    clean = re.sub(r"\.\w{1,4}$", "", clean)
    # Strip hex hashes (e.g. "e45ce62d")
    clean = re.sub(r"\b[0-9a-f]{8}\b", "", clean)
    # Strip "part N" / "parte N/M" suffixes
    clean = re.sub(r"\bpart[_\s-]?\d+\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\(?\bparte\s+\d+(?:/\d+)?\)?", "", clean, flags=re.IGNORECASE)
    # Normalize separators before prefix stripping
    clean = clean.replace("_", " ").replace("-", " ")
    clean = re.sub(r"\s+", " ", clean).strip()
    # Strip technical prefix tokens from the left (iteratively)
    for _ in range(6):
        m = _TECHNICAL_PREFIX_TOKEN_RE.match(clean)
        if not m:
            break
        clean = clean[m.end():].strip()
    clean = clean.strip(" .-:,;")
    if not clean:
        return ""
    # Title case: capitalize first letter of each word except small Spanish words
    words = clean.split()
    _SMALL = {
        "a", "al", "con", "de", "del", "desde", "e", "el", "en",
        "la", "las", "los", "o", "para", "por", "sin", "u", "un", "una", "y",
    }
    result: list[str] = []
    for i, word in enumerate(words):
        if i == 0 or word.lower() not in _SMALL:
            result.append(word.capitalize())
        else:
            result.append(word.lower())
    return " ".join(result)
