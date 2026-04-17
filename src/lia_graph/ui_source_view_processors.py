from __future__ import annotations

import html
import json
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

from .contracts import DocumentRecord
from .contracts.advisory import _notes_is_internal
from .expert_providers import (
    provider_from_domain,
    provider_labels as normalize_provider_labels,
    provider_names_from_label,
)
from .form_guides import find_official_form_pdf_source
# generate_llm_strict accessed via _ui() so monkeypatch in tests works
from .source_tiers import (
    DEFAULT_SOURCE_TIER_LABEL,
    SOURCE_TIER_KEY_EXPERTOS,
    SOURCE_TIER_KEY_NORMATIVO,
    is_practical_override_source,
    source_tier_key_for_row,
    source_tier_label_for_key,
)

# ---------------------------------------------------------------------------
# Lazy-import helpers -- functions that still live in ui_server today.
# Using a deferred accessor avoids circular imports.
# ---------------------------------------------------------------------------


def _ui() -> Any:
    """Lazy accessor for lia_graph.ui_server (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


# ---------------------------------------------------------------------------
# Module-level constants (moved from ui_server during granularize-v1 1B)
# ---------------------------------------------------------------------------

_SOURCE_VIEW_CONTENT_MARKERS = (
    "contenido de la página",
    "contenido principal",
)
_SOURCE_VIEW_NON_USABLE_HINTS = (
    "resumen tecnico inicial para seed documental",
    "este scaffold debe evolucionar",
    "claim en construccion",
    "claim en construcción",
    "regla operativa para lia",
    "condiciones de aplicacion",
    "condiciones de aplicación",
    "riesgos de interpretacion",
    "riesgos de interpretación",
    "relaciones normativas",
    "checklist de vigencia",
    "historico de cambios",
    "histórico de cambios",
    "ambito:",
    "ámbito:",
    "uso permitido:",
    "fuente principal enlazada:",
    "migrado desde",
)
_SOURCE_VIEW_HTML_NOISE_HINTS = (
    "¿sabes que es gov.co?",
    "conócelo aquí",
    "icono twitter",
    "icono youtube",
    "icono linkedin",
    "icono facebook",
    "icono instagram",
    "icono tiktok",
    "parece que el explorador no tiene javascript habilitado",
    "active javascript e inténtelo de nuevo",
    "active javascript e intentelo de nuevo",
    "icono cambio de idioma",
    "icono aumento de tamaño de texto",
    "icono aumento de tamano de texto",
    "icono tamaño de texto normal",
    "icono tamano de texto normal",
    "icono disminución del tamaño de texto",
    "icono disminucion del tamano de texto",
    "alto contraste",
    "portal dian",
    "actualmente seleccionado",
    "atención y servicios a la ciudadanía",
    "atencion y servicios a la ciudadania",
    "la ubicación de esta página es",
    "la ubicacion de esta pagina es",
    "<option value=",
    "</option>",
    "bookmarkaj",
    "javascript:insrow",
    "concordancias",
    "doctrina concordante",
    "legislación anterior",
    "legislacion anterior",
    "jurisprudencia vigencia",
    "notas de vigencia",
)
_SOURCE_VIEW_USEFUL_HINT_RE = re.compile(
    r"\b(formulario|declaraci[oó]n|renta|impuesto|impuestos|diligenciar|presentar|pagar|"
    r"persona(?:s)?\s+jur[ií]dica(?:s)?|no\s+residentes|ingresos\s+y\s+patrimonio|"
    r"resoluci[oó]n|obligaciones?\s+tributarias?)\b",
    re.IGNORECASE,
)
_SOURCE_VIEW_SECTION_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("que_hace", "Qué hace", False),
    ("por_que_sirve", "Por qué le sirve al contador", False),
    ("puntos_clave", "Puntos clave", True),
    ("tips", "Tips / comentarios", True),
    ("alertas", "Alertas", True),
    ("sustento", "Sustento", True),
)
_SOURCE_FORM_REFERENCE_RE = re.compile(r"\b(?:formulario|formato|form\.?|f\.)\s*([0-9]{2,5}[A-Z]?)\b", re.IGNORECASE)
_SOURCE_RESOLUTION_REFERENCE_RE = re.compile(r"\b(resoluci[oó]n\s+[0-9A-Za-z\-]+(?:\s+de\s+\d{4})?)\b", re.IGNORECASE)
_SOURCE_DECREE_REFERENCE_RE = re.compile(r"\b(decreto\s+[0-9A-Za-z\-]+(?:\s+de\s+\d{4})?)\b", re.IGNORECASE)
_SOURCE_LAW_REFERENCE_RE = re.compile(r"\b(ley\s+[0-9A-Za-z\-]+(?:\s+de\s+\d{4})?)\b", re.IGNORECASE)
_SOURCE_ARTICLE_ID_LINE_RE = re.compile(r"^\s*-\s*article_id:\s*(.+?)\s*$", re.IGNORECASE)
_SOURCE_HEADING_LINE_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
_SOURCE_SECTION_LINE_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:Secci[oó]n\s+\d+|\d+(?:\.\d+){0,4}\.?)\s*[—\-:\.]?\s+.+$",
    re.IGNORECASE,
)
_SUMMARY_EXERCISE_HINT_RE = re.compile(
    r"\b(pregunta\s+\d+|test\s+pr[aá]ctico|caso\s+pr[aá]ctico|ejercicio)\b",
    re.IGNORECASE,
)
_SUMMARY_MONEY_HINT_RE = re.compile(
    r"(\$\s*\d+|\b\d+\s*(?:millones|millon|mil)\b)",
    re.IGNORECASE,
)
_SUMMARY_EXAMPLE_HINTS = (
    "ejemplo",
    "ejemplos",
    "caso",
    "casos",
    "simulacion",
    "simulación",
    "escenario",
    "escenarios",
)


# ---------------------------------------------------------------------------
# Source view processor functions
# ---------------------------------------------------------------------------


def _guide_primary_source_payload(package: Any) -> dict[str, str]:
    source = find_official_form_pdf_source(package)
    if source is not None:
        url = _ui()._coerce_http_url(getattr(source, "url", ""))
        authority = str(getattr(source, "authority", "") or "DIAN").strip() or "DIAN"
        if url:
            return {
                "official_url": url,
                "authority": authority,
                "source_provider": authority,
            }
    return {"official_url": "", "authority": "DIAN", "source_provider": "DIAN"}


def _source_view_provenance_uri(row: dict[str, Any]) -> str:
    return _ui()._sanitize_url_candidate(
        str(row.get("provenance_uri") or row.get("url") or "").strip()
    )


def _collect_source_view_candidate_rows(
    *,
    doc_id: str,
    requested_row: dict[str, Any],
    index_file: Path | None = None,
) -> list[dict[str, Any]]:
    if index_file is None:
        index_file = _ui().INDEX_FILE_PATH
    rows: list[dict[str, Any]] = [dict(requested_row)]
    if not index_file.exists():
        return rows

    try:
        rows_by_doc_id = _ui()._load_index_rows_by_doc_id(index_file)
    except OSError:
        return rows

    seen_doc_ids = {str(requested_row.get("doc_id", "")).strip()}
    requested_logical_doc_id = _ui()._logical_doc_id(str(requested_row.get("doc_id", "")).strip())
    provenance_uri = _source_view_provenance_uri(requested_row)
    if provenance_uri:
        for candidate in rows_by_doc_id.values():
            candidate_doc_id = str(candidate.get("doc_id", "")).strip()
            if not candidate_doc_id or candidate_doc_id in seen_doc_ids:
                continue
            if _source_view_provenance_uri(candidate) != provenance_uri:
                continue
            if not _ui()._row_is_active_or_canonical(candidate):
                continue
            rows.append(dict(candidate))
            seen_doc_ids.add(candidate_doc_id)

    if requested_logical_doc_id:
        for candidate in rows_by_doc_id.values():
            candidate_doc_id = str(candidate.get("doc_id", "")).strip()
            if not candidate_doc_id or candidate_doc_id in seen_doc_ids:
                continue
            if _ui()._logical_doc_id(candidate_doc_id) != requested_logical_doc_id:
                continue
            if not _ui()._row_is_active_or_canonical(candidate):
                continue
            rows.append(dict(candidate))
            seen_doc_ids.add(candidate_doc_id)
    return rows


def _load_source_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _pick_local_source_file(
    *,
    normalized_file: Path | None,
    upload_artifact: Path | None,
    view: str,
) -> tuple[Path | None, str]:
    normalized = normalized_file if normalized_file and normalized_file.exists() else None
    original = upload_artifact if upload_artifact and upload_artifact.exists() else None
    normalized_first = "normalized"
    original_first = "original"
    if view == original_first:
        if original is not None:
            return original, original_first
        if normalized is not None:
            return normalized, normalized_first
        return None, normalized_first
    if normalized is not None:
        return normalized, normalized_first
    if original is not None:
        return original, original_first
    return None, normalized_first


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


def _trim_source_view_content_markers(text: str) -> str:
    clean = str(text or "").strip()
    if not clean:
        return ""
    lowered = clean.lower()
    for marker in _SOURCE_VIEW_CONTENT_MARKERS:
        idx = lowered.find(marker)
        if idx >= 0:
            trimmed = clean[idx + len(marker) :].strip(" :.-\n")
            if trimmed:
                clean = trimmed
                lowered = clean.lower()
                break
    return clean


def _is_source_view_noise_text(text: str) -> bool:
    lowered = re.sub(r"\s+", " ", str(text or "").lower()).strip()
    if not lowered:
        return True
    if any(hint in lowered for hint in _SOURCE_VIEW_NON_USABLE_HINTS):
        return True
    if any(hint in lowered for hint in _SOURCE_VIEW_HTML_NOISE_HINTS):
        return True
    if lowered.count("icono ") >= 2:
        return True
    if "portal dian" in lowered and not _SOURCE_VIEW_USEFUL_HINT_RE.search(lowered):
        return True
    return False


def _extract_source_view_usable_text(public_text: str) -> str:
    normalized = str(public_text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.strip():
        return ""

    if _ui()._looks_like_html_document(normalized):
        normalized = _ui()._extract_visible_text_from_html(normalized)

    normalized = html.unescape(normalized).replace("\xa0", " ")
    normalized = _trim_source_view_content_markers(normalized)
    paragraphs: list[str] = []
    seen: set[str] = set()

    for block in re.split(r"\n{2,}", normalized):
        clean = _ui()._clean_markdown_inline(_trim_source_view_content_markers(block))
        clean = re.sub(r"\s+", " ", clean).strip(" -:\n\t")
        if not clean:
            continue
        if _ui()._SOURCE_METADATA_LINE_RE.match(clean):
            continue
        if _ui()._SOURCE_INTERNAL_BOUNDARY_RE.match(clean):
            break
        if _is_source_view_noise_text(clean):
            continue
        if len(clean) < 30 and not _SOURCE_VIEW_USEFUL_HINT_RE.search(clean):
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        paragraphs.append(clean)
        if len(paragraphs) >= 12:
            break

    if not paragraphs:
        sentence_candidates = re.split(r"(?<=[\.\!\?])\s+", normalized)
        for sentence in sentence_candidates:
            clean = _ui()._clean_markdown_inline(_trim_source_view_content_markers(sentence))
            clean = re.sub(r"\s+", " ", clean).strip(" -:\n\t")
            if not clean or _is_source_view_noise_text(clean):
                continue
            if len(clean) < 24 and not _SOURCE_VIEW_USEFUL_HINT_RE.search(clean):
                continue
            key = clean.lower()
            if key in seen:
                continue
            seen.add(key)
            paragraphs.append(clean)
            if len(paragraphs) >= 12:
                break

    return "\n\n".join(paragraphs).strip()


def _build_source_view_candidate_analysis(
    row: dict[str, Any],
    *,
    view: str,
) -> dict[str, Any]:
    candidate_doc_id = str(row.get("doc_id", "")).strip()
    source_url = str(row.get("url", "")).strip()
    normalized_file = _ui()._resolve_knowledge_file(str(row.get("absolute_path", "")).strip())
    upload_artifact = _ui()._resolve_local_upload_artifact(doc_id=candidate_doc_id, source_url=source_url)
    source_file, selected_view = _pick_local_source_file(
        normalized_file=normalized_file,
        upload_artifact=upload_artifact,
        view=view,
    )
    raw_text = ""
    read_error = False
    if source_file is not None:
        try:
            raw_text = _ui()._load_source_text(source_file)
        except (OSError, UnicodeDecodeError):
            raw_text = ""
            read_error = True
    extracted_base = _ui()._extract_visible_text_from_html(raw_text) if _ui()._looks_like_html_document(raw_text) else raw_text
    public_text = _ui()._extract_public_reference_text(extracted_base)
    usable_text = _extract_source_view_usable_text(public_text)
    readable_score = min(len(usable_text), 12000)
    return {
        "row": dict(row),
        "doc_id": candidate_doc_id,
        "source_file": source_file,
        "selected_view": selected_view,
        "upload_artifact": upload_artifact,
        "read_error": read_error,
        "raw_text": raw_text,
        "public_text": public_text,
        "usable_text": usable_text,
        "rank": (
            1 if usable_text else 0,
            readable_score,
            _ui()._row_lifecycle_rank(row),
            _ui()._row_curation_rank(row),
        ),
    }


def _resolve_source_view_material(
    *,
    doc_id: str,
    view: str,
    index_file: Path | None = None,
) -> dict[str, Any] | None:
    if index_file is None:
        index_file = _ui().INDEX_FILE_PATH
    requested_row = _ui()._find_document_index_row(doc_id, index_file=index_file)
    if requested_row is None:
        return None

    candidates = _collect_source_view_candidate_rows(
        doc_id=doc_id,
        requested_row=requested_row,
        index_file=index_file,
    )
    analyses: list[dict[str, Any]] = []
    for row in candidates:
        analyses.append(_build_source_view_candidate_analysis(row, view=view))

    if not analyses:
        return None

    def _sort_key(item: dict[str, Any]) -> tuple[int, int, int, int]:
        rank = item.get("rank") or (0, 0, 0, 0)
        return (
            int(rank[0]),
            int(rank[1]),
            int(rank[2]),
            int(rank[3]),
        )

    resolved = max(analyses, key=_sort_key)
    return {
        "requested_row": dict(requested_row),
        "resolved_row": dict(resolved.get("row") or requested_row),
        "source_file": resolved.get("source_file"),
        "selected_view": str(resolved.get("selected_view") or view or "normalized"),
        "upload_artifact": resolved.get("upload_artifact"),
        "read_error": bool(resolved.get("read_error")),
        "raw_text": str(resolved.get("raw_text") or ""),
        "public_text": str(resolved.get("public_text") or ""),
        "usable_text": str(resolved.get("usable_text") or ""),
    }


def _build_source_query_profile(
    *,
    question_context: str,
    citation_context: str,
) -> dict[str, Any]:
    q_clean = _ui()._sanitize_question_context(question_context, max_chars=320)
    cq_clean = _ui()._sanitize_question_context(citation_context, max_chars=240)
    q_tokens = _ui()._tokenize_relevance_text(q_clean)
    cq_tokens = _ui()._tokenize_relevance_text(cq_clean)
    merged_text = f"{q_clean} {cq_clean}".strip()
    intent_tags = sorted(_ui()._detect_intent_tags(merged_text))
    need_examples = any(hint in merged_text.lower() for hint in _SUMMARY_EXAMPLE_HINTS)
    return {
        "question_context": q_clean,
        "citation_context": cq_clean,
        "q_tokens": q_tokens,
        "cq_tokens": cq_tokens,
        "intent_tags": intent_tags,
        "need_examples": need_examples,
    }


def _extract_source_chunks(text: str, *, max_items: int = 24) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    seen: set[str] = set()
    current_heading = ""

    for block in re.split(r"\n{2,}", str(text or "")):
        raw_lines = [line for line in block.splitlines() if str(line or "").strip()]
        clean_lines = [_ui()._clean_markdown_inline(line) for line in raw_lines]
        clean_lines = [line for line in clean_lines if line]
        if not clean_lines:
            continue

        first_line = clean_lines[0]
        if len(clean_lines) == 1 and (_SOURCE_SECTION_LINE_RE.match(first_line) or first_line.endswith(":")):
            current_heading = first_line
            continue

        heading = current_heading
        body_lines = list(clean_lines)
        if _SOURCE_SECTION_LINE_RE.match(first_line) and len(clean_lines) > 1:
            heading = first_line
            body_lines = clean_lines[1:]

        body = _ui()._clean_markdown_inline(" ".join(body_lines))
        if len(body) < 45:
            continue

        key = f"{heading.lower()}::{body.lower()[:260]}"
        if key in seen:
            continue
        seen.add(key)
        merged = f"{heading} {body}".strip()
        lower = merged.lower()
        is_exercise_chunk = bool(_SUMMARY_EXERCISE_HINT_RE.search(lower))
        has_money_example = bool(_SUMMARY_MONEY_HINT_RE.search(lower))
        intent_tags = sorted(_ui()._detect_intent_tags(merged))
        chunks.append(
            {
                "heading": heading,
                "text": body,
                "intent_tags": intent_tags,
                "is_exercise_chunk": is_exercise_chunk,
                "has_money_example": has_money_example,
                "is_reference_dense": _ui()._looks_like_reference_list(body),
                "signature": re.sub(r"\s+", " ", lower)[:140],
            }
        )
        if len(chunks) >= max_items:
            break
    return chunks


def _build_user_source_profile(row: dict[str, Any], public_text: str) -> dict[str, Any]:
    knowledge_class = str(row.get("knowledge_class", "")).strip().lower()
    source_type = str(row.get("source_type", "")).strip().lower()
    source_url = _ui()._sanitize_url_candidate(str(row.get("url", "")).strip())
    authority = str(row.get("authority", "")).strip()

    tier_key = source_tier_key_for_row(knowledge_class=knowledge_class, source_type=source_type, source_url=source_url)
    reason_code = f"knowledge_class:{knowledge_class or 'unknown'}"
    if is_practical_override_source(knowledge_class=knowledge_class, source_type=source_type, source_url=source_url):
        reason_code = "loggro:practical_internal"

    tier_label = source_tier_label_for_key(tier_key)
    provider_label = authority or "Fuente no identificada"
    provider_url = source_url if source_url.lower().startswith(("http://", "https://")) else None
    warning = None

    if tier_key == SOURCE_TIER_KEY_EXPERTOS:
        expert_link = _ui()._find_expert_provider_link(public_text)
        if expert_link is not None:
            provider_label = str(expert_link.get("provider", "")).strip() or provider_label
            outbound_url = _ui()._sanitize_url_candidate(str(expert_link.get("url", "")))
            provider_url = outbound_url or provider_url
            reason_code = "expertos:expert_outbound_link"
        else:
            provider_label = authority or DEFAULT_SOURCE_TIER_LABEL
            if provider_url:
                reason_code = "expertos:metadata_http_url"
            else:
                warning = "No se encontró URL pública; se muestra soporte local"
                reason_code = "expertos:no_public_url"
    elif tier_key == SOURCE_TIER_KEY_NORMATIVO:
        provider_label = authority or "Fuente oficial"
    else:
        provider_label = "Fuente Loggro"

    return {
        "tier_key": tier_key,
        "tier_label": tier_label,
        "provider_label": provider_label,
        "provider_url": provider_url,
        "warning": warning,
        "reason_code": reason_code,
    }


def _normalize_source_view_field_value(value: Any, *, as_list: bool) -> list[str] | str:
    if as_list:
        items = value if isinstance(value, list) else [value]
        normalized: list[str] = []
        seen: set[str] = set()
        for item in items:
            clean = _ui()._clip_session_content(_ui()._clean_markdown_inline(str(item or "").strip()), max_chars=240)
            if not clean:
                continue
            lowered = clean.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(clean)
            if len(normalized) >= 5:
                break
        return normalized
    return _ui()._clip_session_content(_ui()._clean_markdown_inline(str(value or "").strip()), max_chars=420)


def _normalize_source_reference_text(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def _infer_source_reference_anchor(source_title: str) -> str:
    clean_title = _ui()._clean_markdown_inline(str(source_title or "").strip())
    if not clean_title:
        return "el documento seleccionado"

    form_match = _SOURCE_FORM_REFERENCE_RE.search(clean_title)
    if form_match:
        form_label = f"Formulario {form_match.group(1)}"
        lowered_title = _normalize_source_reference_text(clean_title)
        if "guia" in lowered_title:
            return f"la guía operativa del {form_label}"
        return f"el {form_label}"

    for pattern, article in (
        (_SOURCE_RESOLUTION_REFERENCE_RE, "la"),
        (_SOURCE_DECREE_REFERENCE_RE, "el"),
        (_SOURCE_LAW_REFERENCE_RE, "la"),
    ):
        match = pattern.search(clean_title)
        if match:
            return f"{article} {match.group(1)}"

    return f'el documento "{clean_title}"'


def _text_refers_to_source_document(text: str, *, source_title: str, source_anchor: str) -> bool:
    normalized_text = _normalize_source_reference_text(text)
    if not normalized_text:
        return False

    candidates = {
        _normalize_source_reference_text(source_title),
        _normalize_source_reference_text(source_anchor),
    }
    form_match = _SOURCE_FORM_REFERENCE_RE.search(source_title or "")
    if form_match:
        candidates.add(f"formulario {form_match.group(1).lower()}")

    return any(candidate and candidate in normalized_text for candidate in candidates)


def _anchor_source_view_text(text: str, *, source_title: str, field_key: str, max_chars: int) -> str:
    clean_text = _ui()._clean_markdown_inline(str(text or "").strip())
    if not clean_text:
        return ""

    source_anchor = _infer_source_reference_anchor(source_title)
    if source_anchor == "el documento seleccionado":
        return _ui()._clip_session_content(clean_text, max_chars=max_chars)
    if _text_refers_to_source_document(clean_text, source_title=source_title, source_anchor=source_anchor):
        return _ui()._clip_session_content(clean_text, max_chars=max_chars)

    prefix = f"Sobre {source_anchor}, "
    if field_key == "sustento":
        prefix = f"Sobre {source_anchor}, la fuente indica: "
    return _ui()._clip_session_content(f"{prefix}{clean_text}", max_chars=max_chars)


def _anchor_source_view_summary_payload(payload: dict[str, Any], *, source_title: str) -> dict[str, Any]:
    anchored: dict[str, Any] = {}
    for key, _label, as_list in _SOURCE_VIEW_SECTION_SPECS:
        value = payload.get(key)
        if as_list:
            items = [str(item).strip() for item in list(value or []) if str(item).strip()]
            if not items:
                continue
            anchored_items = [
                _anchor_source_view_text(item, source_title=source_title, field_key=key, max_chars=240)
                for item in items
            ]
            anchored_items = [item for item in anchored_items if item]
            if anchored_items:
                anchored[key] = anchored_items
            continue

        text = str(value or "").strip()
        if not text:
            continue
        anchored_text = _anchor_source_view_text(text, source_title=source_title, field_key=key, max_chars=420)
        if anchored_text:
            anchored[key] = anchored_text
    return anchored


def _build_source_view_summary_prompt(
    *,
    source_profile: dict[str, Any],
    source_title: str,
    usable_text: str,
    evidence_chunks: list[dict[str, Any]],
) -> str:
    evidence_lines: list[str] = []
    for chunk in evidence_chunks[:6]:
        heading = _ui()._clean_markdown_inline(str(chunk.get("heading", "")).strip())
        text = _ui()._clip_session_content(_ui()._clean_markdown_inline(str(chunk.get("text", "")).strip()), max_chars=320)
        if not text:
            continue
        if heading:
            evidence_lines.append(f"- {heading}: {text}")
        else:
            evidence_lines.append(f"- {text}")

    evidence_text = "\n".join(evidence_lines) or "- Sin extractos priorizados."
    tier_label = str(source_profile.get("tier_label", "")).strip()
    provider_label = str(source_profile.get("provider_label", "")).strip()
    source_anchor = _infer_source_reference_anchor(source_title)
    focused_body_segments = [
        _ui()._clip_session_content(_ui()._clean_markdown_inline(str(chunk.get("text") or "").strip()), max_chars=320)
        for chunk in evidence_chunks[:12]
        if str(chunk.get("text") or "").strip()
    ]
    focused_body = "\n".join(f"- {segment}" for segment in focused_body_segments if segment).strip()
    body = focused_body or _ui()._clip_session_content(usable_text, max_chars=7000)
    return (
        "Eres un editor tecnico para contadores.\n"
        "Tu tarea es resumir una fuente documental en terminos utiles para un contador.\n"
        "Debes responder sobre el documento seleccionado identificado en `titulo_fuente`.\n"
        "Si `titulo_fuente` es un formulario, guia, resolucion o concepto, responde sobre ese documento mismo y su uso practico.\n"
        "No des una respuesta general sobre el tema ni sobre documentos relacionados; enfocate en el documento seleccionado.\n"
        "Responde SOLO JSON valido con estas llaves opcionales:\n"
        '{"que_hace":"","por_que_sirve":"","puntos_clave":[],"tips":[],"alertas":[],"sustento":[]}\n'
        "Reglas:\n"
        "- Usa solo informacion explicita del texto fuente.\n"
        "- No inventes hechos, consejos ni conclusiones legales que no esten en la fuente.\n"
        "- No escribas frases de insuficiencia, disculpas ni fallback.\n"
        "- Omite campos vacios o dejalos como string/lista vacia.\n"
        "- Todo campo poblado debe referirse explicitamente al documento seleccionado usando `referente_documental` o el nombre literal del documento.\n"
        "- Si el documento es un formulario, guia o norma concreta, mencionalo dentro de cada texto; evita pronombres ambiguos como `este documento` sin anclarlo.\n"
        "- `puntos_clave`, `tips`, `alertas` y `sustento` deben ser listas breves.\n"
        "- `sustento` debe citar o parafrasear muy de cerca fragmentos del texto fuente y dejar clara su relacion con `referente_documental`.\n\n"
        "Sentido esperado de cada campo:\n"
        "- `que_hace`: explica que hace `referente_documental` (por ejemplo, que hace el Formulario 110 o la guia operativa del Formulario 110).\n"
        "- `por_que_sirve`: explica por que `referente_documental` le sirve al contador en la practica.\n"
        "- `puntos_clave`: resume puntos clave de `referente_documental`, no del tema en abstracto.\n"
        "- `tips`: da tips operativos solo si surgen de `referente_documental`.\n"
        "- `alertas`: da alertas de `referente_documental` o de su uso.\n"
        "- `sustento`: frases o ideas del texto fuente que respalden lo anterior y digan a que documento aplican.\n\n"
        f"titulo_fuente={source_title}\n"
        f"referente_documental={source_anchor}\n"
        f"tier={tier_label}\n"
        f"proveedor={provider_label}\n"
        "extractos_priorizados:\n"
        f"{evidence_text}\n\n"
        "texto_fuente:\n"
        f"{body}\n"
    )


def _llm_source_view_summary_payload(
    *,
    source_profile: dict[str, Any],
    source_title: str,
    usable_text: str,
    evidence_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    if not usable_text.strip():
        return {}
    prompt = _build_source_view_summary_prompt(
        source_profile=source_profile,
        source_title=source_title,
        usable_text=usable_text,
        evidence_chunks=evidence_chunks,
    )
    try:
        text, _diag = _ui().generate_llm_strict(
            prompt,
            runtime_config_path=_ui().LLM_RUNTIME_CONFIG_PATH,
            trace_id=None,
        )
    except Exception:  # noqa: BLE001
        return {}
    parsed = _ui()._safe_json_obj(text)
    if not parsed:
        return {}

    normalized: dict[str, Any] = {}
    for key, _label, as_list in _SOURCE_VIEW_SECTION_SPECS:
        if key not in parsed:
            continue
        value = _normalize_source_view_field_value(parsed.get(key), as_list=as_list)
        if as_list:
            if value:
                normalized[key] = value
        elif value:
                normalized[key] = value
    return _anchor_source_view_summary_payload(normalized, source_title=source_title)


def _build_et_article_source_view_markdown(
    *,
    doc_id: str,
    source_title: str,
    public_text: str,
) -> str:
    if not _ui()._ET_ARTICLE_DOC_ID_RE.match(str(doc_id or "").strip()):
        return ""

    section_map = _ui()._markdown_section_map(public_text)
    normative_text = (
        section_map.get("texto normativo vigente")
        or section_map.get("texto normativo vigente.")
        or _ui()._extract_named_plain_section_body(public_text, "texto normativo vigente", "texto normativo vigente.")
        or ""
    ).strip()
    metadata = _ui()._extract_et_article_metadata(public_text)
    article_number = str(metadata.get("article_number_display") or "").strip()
    article_title = str(metadata.get("article_title") or "").strip()
    display_normative_text = normative_text
    if normative_text and article_number:
        heading_text = f"ARTICULO {article_number}."
        if article_title:
            heading_text = f"{heading_text} {article_title}."
        if not _ui()._article_heading_pattern(article_number).search(normative_text):
            display_normative_text = f"{heading_text}\n\n{normative_text}".strip()
    heading = str(source_title or "").strip()
    if not heading:
        if article_number and article_title:
            heading = f"ET Artículo {article_number} — {article_title}"
        elif article_number:
            heading = f"ET Artículo {article_number}"
        else:
            heading = "Artículo ET"

    lines: list[str] = [f"# {heading}"]
    if display_normative_text:
        lines.extend(["", "## Texto normativo vigente", "", display_normative_text])

    additional_sections = _ui()._et_article_additional_depth_for_doc_id(doc_id).get("additional_sections")
    if isinstance(additional_sections, list):
        valid_sections = [section for section in additional_sections if isinstance(section, dict)]
    else:
        valid_sections = []
    if valid_sections:
        lines.extend(["", "## Normativa adicional"])
        for section in valid_sections:
            title = str(section.get("title") or "").strip()
            items = section.get("items")
            if not title or not isinstance(items, list):
                continue
            lines.extend(["", f"### {title}", ""])
            for item in items:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or "").strip()
                url = _ui()._coerce_http_url(item.get("url"))
                if not label:
                    continue
                if url:
                    lines.append(f"- [{label}]({url})")
                else:
                    lines.append(f"- {label}")
    return "\n".join(lines).strip()


def _render_source_view_summary_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, label, as_list in _SOURCE_VIEW_SECTION_SPECS:
        value = payload.get(key)
        if as_list:
            items = [str(item).strip() for item in list(value or []) if str(item).strip()]
            if not items:
                continue
            lines.append(f"## {label}")
            lines.append("")
            lines.extend(f"- {item}" for item in items)
            lines.append("")
            continue
        text = str(value or "").strip()
        if not text:
            continue
        lines.append(f"## {label}")
        lines.append("")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).strip()


def _build_source_view_summary_markdown(
    *,
    doc_id: str = "",
    source_profile: dict[str, Any],
    source_title: str,
    question_context: str,
    citation_context: str,
    full_guide_href: str,
    public_text: str,
) -> str:
    del doc_id
    del full_guide_href
    usable_text = _extract_source_view_usable_text(public_text)
    if not usable_text:
        return ""

    query_profile = _build_source_query_profile(
        question_context=question_context,
        citation_context=citation_context,
    )
    chunks = _extract_source_chunks(usable_text, max_items=12)
    if not chunks:
        chunks = [
            {
                "heading": "",
                "text": paragraph,
                "intent_tags": [],
                "is_exercise_chunk": False,
                "has_money_example": False,
                "is_reference_dense": False,
                "signature": paragraph.lower()[:140],
            }
            for paragraph in _ui()._extract_candidate_paragraphs(usable_text, max_items=6)
        ]
    if not chunks:
        return ""

    if query_profile.get("q_tokens") or query_profile.get("cq_tokens") or query_profile.get("intent_tags"):
        scored_rows = []
        for idx, chunk in enumerate(chunks):
            score_payload = _ui()._score_chunk_relevance(chunk, query_profile=query_profile)
            scored_rows.append(
                {
                    "index": idx,
                    "chunk": chunk,
                    "score": float(score_payload.get("score", 0.0)),
                }
            )
        evidence_chunks = _ui()._select_diverse_chunks(scored_rows=scored_rows, chunks=chunks, max_items=6)
    else:
        evidence_chunks = chunks[:6]

    summary_payload = _llm_source_view_summary_payload(
        source_profile=source_profile,
        source_title=source_title,
        usable_text=usable_text,
        evidence_chunks=evidence_chunks,
    )
    if not summary_payload:
        return ""
    return _render_source_view_summary_markdown(summary_payload)


def _sanitize_source_view_href(value: str) -> str:
    href = str(value or "").strip()
    if not href:
        return ""
    if href.startswith("/"):
        return href
    if re.match(r"^https?://", href, re.IGNORECASE):
        return href
    if re.match(r"^(mailto|tel):", href, re.IGNORECASE):
        return href
    return ""


def _render_source_view_inline_markdown(text: str) -> str:
    source = str(text or "")
    placeholders: dict[str, str] = {}

    def reserve(rendered: str) -> str:
        token = f"@@MDTOKEN{len(placeholders)}@@"
        placeholders[token] = rendered
        return token

    def replace_code(match: re.Match[str]) -> str:
        return reserve(f"<code>{html.escape(match.group(1))}</code>")

    source = re.sub(r"`([^`\n]+)`", replace_code, source)

    def replace_link(match: re.Match[str]) -> str:
        label = str(match.group(1) or "").strip()
        href = _sanitize_source_view_href(match.group(2))
        if not href:
            return reserve(html.escape(label))
        rel = " target='_blank' rel='noopener noreferrer'" if href.startswith(("http://", "https://")) else ""
        return reserve(f"<a href='{html.escape(href)}'{rel}>{html.escape(label)}</a>")

    source = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", replace_link, source)

    rendered = html.escape(source)
    rendered = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", rendered)
    rendered = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"<em>\1</em>", rendered)
    for token, replacement in placeholders.items():
        rendered = rendered.replace(token, replacement)
    return rendered


def _render_source_view_markdown_html(text: str) -> str:
    source = str(text or "").replace("\r\n", "\n").strip()
    if not source:
        return ""

    blocks: list[str] = []
    paragraph_lines: list[str] = []
    list_items: list[str] = []
    list_tag: str | None = None
    quote_lines: list[str] = []
    code_lines: list[str] = []
    in_code_block = False

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if not paragraph_lines:
            return
        text_value = " ".join(line.strip() for line in paragraph_lines if line.strip())
        if text_value:
            blocks.append(f"<p>{_render_source_view_inline_markdown(text_value)}</p>")
        paragraph_lines = []

    def flush_list() -> None:
        nonlocal list_items, list_tag
        if not list_items or not list_tag:
            list_items = []
            list_tag = None
            return
        items_html = "".join(f"<li>{_render_source_view_inline_markdown(item)}</li>" for item in list_items)
        blocks.append(f"<{list_tag}>{items_html}</{list_tag}>")
        list_items = []
        list_tag = None

    def flush_quote() -> None:
        nonlocal quote_lines
        if not quote_lines:
            return
        text_value = " ".join(line.strip() for line in quote_lines if line.strip())
        if text_value:
            blocks.append(f"<blockquote><p>{_render_source_view_inline_markdown(text_value)}</p></blockquote>")
        quote_lines = []

    def flush_code() -> None:
        nonlocal code_lines
        if not code_lines:
            return
        blocks.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
        code_lines = []

    for raw_line in source.split("\n"):
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            flush_quote()
            if in_code_block:
                flush_code()
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(raw_line)
            continue

        if not stripped:
            flush_paragraph()
            flush_list()
            flush_quote()
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            flush_paragraph()
            flush_list()
            flush_quote()
            level = min(len(heading_match.group(1)), 6)
            content = _render_source_view_inline_markdown(heading_match.group(2).strip())
            blocks.append(f"<h{level}>{content}</h{level}>")
            continue

        if re.match(r"^([-*_])\1{2,}$", stripped):
            flush_paragraph()
            flush_list()
            flush_quote()
            blocks.append("<hr>")
            continue

        quote_match = re.match(r"^>\s?(.*)$", stripped)
        if quote_match:
            flush_paragraph()
            flush_list()
            quote_lines.append(quote_match.group(1))
            continue

        list_match = re.match(r"^([-*]|\d+\.)\s+(.+)$", stripped)
        if list_match:
            flush_paragraph()
            flush_quote()
            current_tag = "ol" if list_match.group(1).endswith(".") and list_match.group(1)[0].isdigit() else "ul"
            if list_tag and list_tag != current_tag:
                flush_list()
            list_tag = current_tag
            list_items.append(list_match.group(2).strip())
            continue

        flush_list()
        flush_quote()
        paragraph_lines.append(stripped)

    if in_code_block:
        flush_code()
    else:
        flush_paragraph()
        flush_list()
        flush_quote()

    return "".join(blocks)


def _build_source_view_html(
    *,
    title: str,
    doc_id_html: str,
    tier_label_html: str,
    provider_label_html: str,
    reference_link_html: str,
    artifact_label: str,
    download_href: str,
    switch_view_html: str,
    official_link_html: str,
    rendered_content_html: str,
    raw_fallback_html: str,
    show_meta_card: bool = True,
    viewer_note: str = "Visor de cliente final: muestra resumen estructurado y enlaces de soporte.",
) -> str:
    """Return a user-facing HTML page for citation support content."""
    heading = "Contenido de Apoyo Proveido por Loggro"
    meta_card_html = ""
    if show_meta_card:
        meta_card_html = (
            "<section class='meta-card'>"
            "<div class='chip-row'>"
            f"<span class='chip'>Fuente: {tier_label_html}</span>"
            f"<span class='chip'>Proveedor: {provider_label_html}</span>"
            f"<span class='chip'>Documento: {artifact_label}</span>"
            "</div>"
            f"<p class='meta-link'>{reference_link_html}</p>"
            f"<p class='viewer-note'>{html.escape(viewer_note)}</p>"
            "</section>"
        )
    download_md_href = download_href.replace("&format=pdf", "&format=md")
    actions_html = (
        "<div class='actions'>"
        f"<a class='btn primary' href='{html.escape(download_href)}'>Descargar PDF</a>"
        f"<a class='btn' href='{html.escape(download_md_href)}'>Descargar Markdown</a>"
        f"{switch_view_html}"
        f"{official_link_html}"
        "</div>"
    )
    if "view=original" in download_href:
        normalized_md_href = (
            download_href.replace("view=original", "view=normalized").replace("&format=original", "&format=md")
        )
        actions_html = (
            "<div class='actions'>"
            f"<a class='btn primary' href='{html.escape(download_href)}'>Descargar original</a>"
            f"<a class='btn' href='{html.escape(normalized_md_href)}'>Descargar Markdown</a>"
            f"{switch_view_html}"
            f"{official_link_html}"
            "</div>"
        )

    return (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title>"
        "<style>"
        "*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}"
        "body{font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;background:#f3f0eb;color:#1a1a1a;}"
        ".page-wrapper{max-width:900px;margin:0 auto;padding:20px 16px 28px;}"
        ".support-title{font-size:1.32rem;font-weight:700;color:#143f32;margin:0 0 14px;}"
        ".page{background:#fff;border:1px solid #d4cfc8;border-radius:10px;"
        "box-shadow:0 2px 8px rgba(0,0,0,.04);padding:26px 24px;min-height:520px;"
        "line-height:1.75;font-size:.95rem;color:#2a2520;}"
        ".meta-card{border:1px solid #d8d2ca;background:#f8f5f0;padding:12px 14px;border-radius:8px;margin-bottom:12px;}"
        ".chip-row{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;}"
        ".chip{display:inline-flex;border:1px solid #c8d3cd;background:#edf4f1;color:#184437;border-radius:999px;padding:3px 10px;font-size:.78rem;font-weight:600;}"
        ".meta-link{font-size:.84rem;color:#595349;}"
        ".viewer-note{font-size:.8rem;color:#6a645b;}"
        ".actions{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px;}"
        ".btn{display:inline-flex;align-items:center;justify-content:center;border:1px solid #b8c9c2;border-radius:8px;padding:7px 12px;font-size:.82rem;font-weight:700;color:#15513f;background:#f4faf7;text-decoration:none;}"
        ".btn.primary{background:#0f5a47;color:#fff;border-color:#0f5a47;}"
        ".page h1{font-size:1.55rem;font-weight:700;color:#1a1714;margin:0 0 18px;"
        "padding-bottom:10px;border-bottom:2px solid #e8e3db;}"
        ".page h2{font-size:1.25rem;font-weight:700;color:#2c2620;margin:28px 0 12px;"
        "padding-bottom:6px;border-bottom:1px solid #ede8e0;}"
        ".page h3{font-size:1.08rem;font-weight:600;color:#3a3228;margin:22px 0 8px;}"
        ".page h4{font-size:.96rem;font-weight:600;color:#4a4238;margin:18px 0 6px;}"
        ".page p{margin:0 0 14px;}"
        ".page ul,.page ol{margin:0 0 14px;padding-left:26px;}"
        ".page li{margin:0 0 6px;}"
        ".page li>ul,.page li>ol{margin:4px 0 4px;}"
        ".page strong{font-weight:700;color:#1a1714;}"
        ".page em{font-style:italic;}"
        ".page code{font-family:'SF Mono','Fira Code',Consolas,monospace;"
        "font-size:.86em;background:#f5f2ed;border:1px solid #e5e0d8;"
        "border-radius:4px;padding:1px 5px;color:#8b4513;}"
        ".page pre{background:#faf8f5;border:1px solid #e5e0d8;border-radius:8px;"
        "padding:14px 18px;overflow-x:auto;margin:0 0 14px;}"
        ".page pre code{background:none;border:none;padding:0;font-size:.84rem;"
        "line-height:1.5;}"
        ".page blockquote{border-left:3px solid #d4cfc8;margin:0 0 14px;"
        "padding:8px 16px;color:#5a534b;background:#faf9f7;border-radius:0 6px 6px 0;}"
        ".page hr{border:none;border-top:1px solid #e5e0d8;margin:24px 0;}"
        ".page table{border-collapse:collapse;width:100%;margin:0 0 14px;"
        "font-size:.88rem;}"
        ".page th,.page td{border:1px solid #e0dbd3;padding:8px 12px;text-align:left;}"
        ".page th{background:#f5f2ed;font-weight:600;color:#2c2620;}"
        ".page a{color:#4a6cf7;text-decoration:none;}"
        ".page a:hover{text-decoration:underline;}"
        ".page-raw{white-space:pre-wrap;word-wrap:break-word;"
        "font-family:'SF Mono','Fira Code',Consolas,monospace;"
        "font-size:.86rem;line-height:1.55;}"
        "@media(max-width:700px){.page-wrapper{padding:16px 10px 20px;}.page{padding:18px 14px;}}"
        "</style>"
        "</head><body>"
        "<div class='page-wrapper'>"
        f"<h1 class='support-title'>{html.escape(heading)}</h1>"
        f"<p class='meta-link' style='margin:0 0 8px'>doc_id: {doc_id_html}</p>"
        "<div class='page' id='doc-content'>"
        f"{meta_card_html}"
        f"{actions_html}"
        f"<div id='rendered-content'>{rendered_content_html}</div>"
        f"{raw_fallback_html}"
        "</div>"
        "</div>"
        "</body></html>"
    )


def _build_source_view_href(
    *,
    doc_id: str,
    view: str = "normalized",
    question_context: str = "",
    citation_context: str = "",
    full: bool = False,
) -> str:
    params: dict[str, str] = {"doc_id": str(doc_id or "").strip()}
    normalized_view = str(view or "normalized").strip().lower() or "normalized"
    if normalized_view == "original":
        params["view"] = "original"
    q_clean = _ui()._sanitize_question_context(question_context)
    if q_clean:
        params["q"] = q_clean
    cq_clean = _ui()._sanitize_question_context(citation_context, max_chars=240)
    if cq_clean:
        params["cq"] = cq_clean
    if full:
        params["full"] = "1"
    return f"/source-view?{urlencode(params)}"


# ---------------------------------------------------------------------------
# Functions extracted from ui_server (Phase 1G)
# ---------------------------------------------------------------------------

_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]{1,180})\]\((https?://[^)\s]+)\)", re.IGNORECASE)
_RAW_URL_RE = re.compile(r"https?://[^\s<>'\"`]+", re.IGNORECASE)


def _classify_provider(url: str, *, label_hint: str | None = None) -> str:
    label_names = provider_names_from_label(label_hint) if label_hint else []
    if label_names:
        return label_names[0]
    domain_provider = provider_from_domain(url)
    if domain_provider:
        return domain_provider
    try:
        domain = urlparse(str(url or "").strip()).netloc.lower().replace("www.", "")
    except ValueError:
        domain = ""
    if domain:
        return domain
    return "Fuente profesional"


def _extract_outbound_links(text: str, *, max_links: int = 12) -> list[dict[str, str]]:
    raw_text = str(text or "")
    if not raw_text:
        return []

    links: list[dict[str, str]] = []
    seen: set[str] = set()

    def _add(url: str, label: str | None = None) -> None:
        clean = _ui()._sanitize_url_candidate(url)
        if not clean or not clean.lower().startswith(("http://", "https://")):
            return
        lowered = clean.lower()
        if lowered in seen:
            return
        try:
            parsed = urlparse(clean)
        except ValueError:
            return
        seen.add(lowered)
        domain = parsed.netloc.lower().replace("www.", "")
        readable = str(label or "").strip() or domain or clean
        provider = _classify_provider(clean, label_hint=readable)
        links.append(
            {
                "url": clean,
                "label": readable[:180],
                "provider": provider,
                "domain": domain,
            }
        )

    for label, url in _MARKDOWN_LINK_RE.findall(raw_text):
        _add(url=url, label=label)
        if len(links) >= max_links:
            return links

    for match in _RAW_URL_RE.findall(raw_text):
        _add(url=match)
        if len(links) >= max_links:
            return links
    return links


def _filter_provider_links(
    text: str,
    *,
    providers: list[dict[str, Any]] | None = None,
    max_links: int = 12,
) -> list[dict[str, str]]:
    links = _extract_outbound_links(text, max_links=max_links * 3)
    provider_names = set(normalize_provider_labels(providers or []))
    if not provider_names:
        return links[:max_links]
    filtered = [item for item in links if str(item.get("provider") or "").strip() in provider_names]
    return (filtered or links)[:max_links]


def _summarize_snippet(text: str, *, max_chars: int = 300) -> str:
    detail_excerpt = _ui()._expert_detail_excerpt(text, max_chars=max(max_chars, 520))
    if detail_excerpt:
        return detail_excerpt
    cleaned = _ui()._flatten_markdown_to_text(_ui()._extract_public_reference_text(str(text or "")), max_chars=max(max_chars * 4, 1800))
    if not cleaned:
        return ""
    return _ui()._clip_expert_summary(cleaned, max_chars=max_chars)


def _dedupe_interpretation_docs(docs: list[DocumentRecord], *, limit: int) -> list[DocumentRecord]:
    kept: list[DocumentRecord] = []
    seen: set[str] = set()
    for doc in docs:
        logical = _ui()._logical_doc_id(doc.doc_id)
        if not logical or logical in seen:
            continue
        seen.add(logical)
        kept.append(doc)
        if len(kept) >= limit:
            break
    return kept
