from __future__ import annotations

import html as _html_mod
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .pipeline_c.retrieval_scoring import load_index

# ---------------------------------------------------------------------------
# Lazy-import helpers -- functions that still live in ui_server today.
# Using a deferred accessor avoids circular imports and ensures that
# monkeypatch.setattr(ui_server, ...) in tests is honoured.
# ---------------------------------------------------------------------------


def _ui() -> Any:
    """Lazy accessor for lia_graph.ui_server (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


# ---------------------------------------------------------------------------
# Module-level constants (moved from ui_server during granularize-v1 1F)
# ---------------------------------------------------------------------------

# Summary/relevance-scoring constants (stopwords, intent keywords, sentence
# abbreviations, citation head/tail regexes) now live in
# `ui_chunk_relevance.py` alongside the scorer/selector functions. They are
# re-exported here via the ui_server lazy-attr bridge, so any external
# consumer that used to look them up on `ui_server` or on this module keeps
# working through `_ui()._SUMMARY_STOPWORDS` etc.
from .ui_chunk_relevance import (
    _CITATION_HEAD_RE,
    _CITATION_TAIL_RE,
    _SENTENCE_ABBR_PLACEHOLDER,
    _SENTENCE_ABBREVIATION_RE,
    _SUMMARY_INTENT_KEYWORDS,
    _SUMMARY_STOPWORDS,
    _detect_intent_tags,
    _extract_candidate_paragraphs,
    _first_substantive_sentence,
    _flatten_markdown_to_text,
    _looks_like_reference_list,
    _pick_summary_sentences,
    _sanitize_question_context,
    _score_chunk_relevance,
    _select_diverse_chunks,
    _split_sentences,
    _tokenize_relevance_text,
)

_MARKDOWN_BULLET_KV_RE = re.compile(r"^\s*-\s*([A-Za-z0-9_]+)\s*:\s*(.+?)\s*$")
_LOCAL_UPLOAD_URL_RE = re.compile(r"^local_upload://([^/]+)/(.+)$")
_NORMALIZED_INGEST_DOC_ID_RE = re.compile(r"^[a-z0-9_]+_ingest_(.+?)_([0-9a-f]{8})(?:_part_[0-9]+)?$")
_URL_TRAILING_PUNCT = ".,;:!?)]}>\"'"
_ACTIVE_INDEX_MISSING_WARNED = False


# ===================================================================
# Document index & lookup
# ===================================================================


def _find_document_index_row(doc_id: str, index_file: Path | None = None) -> dict[str, Any] | None:
    if not doc_id:
        return None
    if index_file is None:
        index_file = _ui().INDEX_FILE_PATH
    # Primary: Supabase (production source of truth)
    row = _sb_find_document_row(doc_id)
    if row is not None:
        return row
    # Fallback: local JSONL index (dev/offline)
    if not index_file.exists():
        try:
            from .interpretacion.catalog import find_local_interpretation_row

            local_row = find_local_interpretation_row(doc_id)
            if local_row is not None:
                return local_row
        except Exception:
            pass
        return None
    try:
        with index_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(row.get("doc_id", "")).strip() == doc_id:
                    return row
    except OSError:
        pass
    try:
        from .interpretacion.catalog import find_local_interpretation_row

        local_row = find_local_interpretation_row(doc_id)
        if local_row is not None:
            return local_row
    except Exception:
        pass
    return None


def _sb_find_document_row(doc_id: str) -> dict[str, Any] | None:
    """Look up a document by doc_id in Supabase (production primary)."""
    try:
        from .supabase_client import get_supabase_client
        client = get_supabase_client()
        res = client.table("documents").select("*").eq("doc_id", doc_id).limit(1).execute()
        if res.data:
            return res.data[0]
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Normograma DIAN → MinTIC mirror swap
# ---------------------------------------------------------------------------
#
# The DIAN Normograma compilation pages (e.g. `estatuto_tributario.htm`) are
# served from two canonical hosts with identical paths and content:
#
#   DIAN:    https://normograma.dian.gov.co/dian/compilacion/docs/...
#   MinTIC:  https://normograma.mintic.gov.co/mintic/compilacion/docs/...
#
# The ET article corpus stores DIAN URLs with fragment anchors like
# `estatuto_tributario.htm#807`, but the DIAN host does not reliably honor
# those fragments — clicking the link lands the user at the top of the page.
# The MinTIC mirror does honor them, so we prefer MinTIC for user-facing
# "Ir a documento original" actions.
#
# Known breakage (as of 2026-04-05): MinTIC's Let's Encrypt cert for
# `normograma.mintic.gov.co` expired on Apr 5 19:54:55 2026 GMT because
# auto-renewal failed on their side. Users must accept the expired-cert
# browser warning once; afterwards all MinTIC URLs work normally. We
# prefer MinTIC everywhere (backend + frontend) because DIAN does not
# honor fragment anchors (#807 etc.) while MinTIC does. The canonical
# DIAN→MinTIC swap also lives in `contracts/advisory.py` for the Citation
# model output path.
#
# Re-check cert validity before assuming this is still broken:
#   echo | openssl s_client -servername normograma.mintic.gov.co \
#     -connect normograma.mintic.gov.co:443 2>/dev/null \
#     | openssl x509 -noout -dates
#
# This helper was historically mirrored by the frontend helper
# `normogramaMirrorUrl` in `frontend/src/features/chat/citations.ts`, but
# that UI was retired in a7031e6e and its fallback URL no longer reaches a
# user-visible rendering surface today. The single source of truth for the
# user-clickable MinTIC URL is now this backend helper.

_NORMOGRAMA_DIAN_BASE = "https://normograma.dian.gov.co/dian/compilacion/docs"
_NORMOGRAMA_MINTIC_BASE = "https://normograma.mintic.gov.co/mintic/compilacion/docs"


def _prefer_normograma_mintic_mirror(url: str | None) -> str:
    """Swap a DIAN Normograma URL for its MinTIC mirror equivalent.

    Returns the input unchanged for non-Normograma URLs, URLs already on
    the MinTIC host, empty strings, or None. Fragment anchors (and any
    query string) are preserved so `#807` stays intact.

    This is used by the citation-profile "Ir a documento original" action
    because DIAN's compilation pages do not honor article fragments
    reliably, while MinTIC's mirror does.
    """
    if not url:
        return ""
    s = str(url).strip()
    if not s:
        return ""
    if s.startswith(_NORMOGRAMA_DIAN_BASE):
        return _NORMOGRAMA_MINTIC_BASE + s[len(_NORMOGRAMA_DIAN_BASE):]
    return s


# The Supabase chunk → markdown reassembler (plus the chunker's
# context-prefix regex and heading-label heuristics) moved to
# `ui_chunk_assembly.py` during granularize-v2. The rationale and gotchas
# live in that module's docstring. Re-imported here so eager
# `from .ui_text_utilities import _sb_assemble_document_markdown` consumers
# keep working; the ui_server lazy registry now points lookups at the new
# module.
from .ui_chunk_assembly import (  # noqa: F401  — re-exported for back-compat
    _CHUNK_CONTEXT_PREFIX_RE,
    _MAX_HEADING_LINE_CHARS,
    _match_heading_label,
    _reconstruct_chunk_markdown,
    _sb_assemble_document_markdown,
    _sb_assemble_document_markdown_cached,
    _sb_query_document_chunks,
    _strip_chunk_context_prefix,
)


def _index_file_signature(index_file: Path) -> str:
    try:
        stat = index_file.stat()
    except OSError:
        return "missing"
    return f"{int(stat.st_mtime_ns)}:{int(stat.st_size)}"


@lru_cache(maxsize=8)
def _load_index_rows_by_doc_id_cached(index_path: str, signature: str) -> dict[str, dict[str, Any]]:
    del signature
    index_file = Path(index_path)
    rows_by_doc_id: dict[str, dict[str, Any]] = {}
    for row in load_index(index_file=index_file):
        if not isinstance(row, dict):
            continue
        doc_id = str(row.get("doc_id", "")).strip()
        if not doc_id:
            continue
        rows_by_doc_id[doc_id] = dict(row)
    return rows_by_doc_id


def _load_index_rows_by_doc_id(index_file: Path | None = None) -> dict[str, dict[str, Any]]:
    if index_file is None:
        index_file = _ui().INDEX_FILE_PATH
    signature = _index_file_signature(index_file)
    return dict(_load_index_rows_by_doc_id_cached(str(index_file.resolve()), signature))


def _looks_like_html_document(text: str) -> bool:
    sample = str(text or "")[:2000].lower()
    if "<html" in sample or "<body" in sample:
        return True
    return bool(re.search(r"<(div|p|span|table|section|article|h[1-6]|li)\b", sample))


def _warn_missing_active_index_generation() -> None:
    global _ACTIVE_INDEX_MISSING_WARNED
    if _ACTIVE_INDEX_MISSING_WARNED:
        return
    try:
        from .ingest import load_active_index_generation
        from .supabase_client import get_storage_backend

        active_generation = load_active_index_generation(output_dir=_ui().INDEX_FILE_PATH.parent)
        storage_backend = str(get_storage_backend() or "").strip().lower() or "supabase"
    except Exception:
        active_generation = None
        storage_backend = "unknown"
    if active_generation:
        return
    location = "supabase://corpus_generations?is_active=true" if storage_backend == "supabase" else str(
        _ui().ACTIVE_INDEX_GENERATION_PATH
    )
    _ui().emit_event(
        "index.active_generation.missing",
        {
            "storage_backend": storage_backend,
            "location": location,
            "warning": "No existe una generación activa del corpus; se continua de forma no bloqueante.",
        },
    )
    _ACTIVE_INDEX_MISSING_WARNED = True


# ===================================================================
# File & URL handling
# ===================================================================


def _resolve_knowledge_file(path_value: str) -> Path | None:
    if not path_value:
        return None
    candidate = Path(path_value).expanduser().resolve()
    kb_root = _ui().KNOWLEDGE_BASE_ROOT
    if kb_root != candidate and kb_root not in candidate.parents:
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate


def _parse_local_upload_url(source_url: str) -> tuple[str, str] | None:
    match = _LOCAL_UPLOAD_URL_RE.match(str(source_url or "").strip())
    if not match:
        return None
    session_id = str(match.group(1)).strip()
    filename = Path(str(match.group(2)).strip()).name
    if not session_id or not filename:
        return None
    return session_id, filename


def _derive_ingestion_upload_doc_id(normalized_doc_id: str) -> str | None:
    match = _NORMALIZED_INGEST_DOC_ID_RE.match(str(normalized_doc_id or "").strip())
    if not match:
        return None
    stem = str(match.group(1)).strip()
    checksum8 = str(match.group(2)).strip()
    if not stem or not checksum8:
        return None
    return f"ing_{stem}_{checksum8}"


def _resolve_local_upload_artifact(doc_id: str, source_url: str) -> Path | None:
    parsed = _parse_local_upload_url(source_url)
    if parsed is None:
        return None
    session_id, _ = parsed
    upload_doc_id = _derive_ingestion_upload_doc_id(doc_id)
    if not upload_doc_id:
        return None

    for base_dir in (_ui().INGESTION_PROCESSED_ROOT, _ui().INGESTION_UPLOADS_ROOT):
        doc_dir = base_dir / session_id / upload_doc_id
        if not doc_dir.exists() or not doc_dir.is_dir():
            continue
        candidates = sorted(doc_dir.glob("original*"))
        if candidates:
            return candidates[0]
    return None


def _slugify_filename_part(text: str, *, max_len: int = 96) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", errors="ignore").decode("ascii")
    compact = re.sub(r"[^A-Za-z0-9]+", "_", ascii_value).strip("_")
    if not compact:
        return ""
    return compact[:max_len].strip("_")


def _build_download_href(*, doc_id: str, view: str, fmt: str) -> str:
    doc_id_q = quote(str(doc_id or "").strip(), safe="")
    view_q = quote(str(view or "normalized").strip().lower() or "normalized", safe="")
    fmt_q = quote(str(fmt or "pdf").strip().lower() or "pdf", safe="")
    return f"/source-download?doc_id={doc_id_q}&view={view_q}&format={fmt_q}"


def _sanitize_url_candidate(url: str) -> str:
    value = str(url or "").strip()
    if not value:
        return ""
    while value and value[-1] in _URL_TRAILING_PUNCT:
        value = value[:-1]
    return value


def _coerce_http_url(value: Any) -> str:
    clean = _sanitize_url_candidate(str(value or "").strip())
    if clean.lower().startswith(("http://", "https://")):
        return clean
    return ""


# ===================================================================
# Markdown processing
# ===================================================================


def _clean_markdown_inline(text: str) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"^\s{0,3}#{1,6}\s*", "", value)
    value = re.sub(r"^\s*[-*+]\s+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _parse_markdown_sections(text: str) -> list[tuple[str, str]]:
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not raw.strip():
        return []

    sections: list[tuple[str, str]] = []
    current_title = ""
    current_lines: list[str] = []
    for line in raw.split("\n"):
        match = re.match(r"^\s{0,3}##\s+(.+?)\s*$", line)
        if match:
            if current_title:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = _clean_markdown_inline(match.group(1))
            current_lines = []
            continue
        current_lines.append(line)
    if current_title:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return sections


def _markdown_section_map(text: str) -> dict[str, str]:
    return {
        str(title or "").strip().lower(): str(body or "").strip()
        for title, body in _parse_markdown_sections(text)
        if str(title or "").strip()
    }


def _extract_markdown_bullet_metadata(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in str(text or "").splitlines():
        match = _MARKDOWN_BULLET_KV_RE.match(line)
        if not match:
            continue
        key = str(match.group(1) or "").strip().lower()
        value = _clean_markdown_inline(match.group(2))
        if key and value:
            metadata[key] = value
    return metadata


def _extract_markdown_primary_body_text(text: str) -> str:
    section_map = _markdown_section_map(text)
    if not section_map:
        return _ui()._extract_source_view_usable_text(text)

    ordered_sections: list[str] = []
    for title, body in _parse_markdown_sections(text):
        normalized_title = str(title or "").strip().lower()
        if normalized_title in {
            "identificacion",
            "identificación",
            "regla operativa para lia",
            "condiciones de aplicacion",
            "condiciones de aplicación",
            "riesgos de interpretacion",
            "riesgos de interpretación",
            "relaciones normativas",
            "checklist de vigencia",
            "historico de cambios",
            "histórico de cambios",
        }:
            continue
        cleaned_lines: list[str] = []
        for line in str(body or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            if _ui()._SOURCE_METADATA_LINE_RE.match(line):
                continue
            if not line.strip():
                cleaned_lines.append("")
                continue
            cleaned_lines.append(_clean_markdown_inline(line))
        clean_body = "\n".join(cleaned_lines).strip()
        clean_body = re.sub(r"\n{3,}", "\n\n", clean_body)
        if clean_body:
            ordered_sections.append(clean_body)
    return "\n\n".join(ordered_sections).strip()


def _build_clean_guide_markdown(*, title: str, public_text: str) -> str:
    clean_title = _clean_markdown_inline(title)
    content = _clean_article_reader_markdown(public_text)
    if not content:
        content = _ui()._extract_source_view_usable_text(public_text) or str(public_text or "").strip()
    if not content:
        return f"# {clean_title or 'Documento'}".strip()

    first_line = _clean_markdown_inline(content.splitlines()[0] if content.splitlines() else "")
    generic_titles = {"dian", "suin", "minhacienda", "fuente"}
    title_lower = clean_title.lower()
    is_generic_title = title_lower in generic_titles or (title_lower.isalpha() and len(title_lower) <= 12)
    if clean_title and first_line and clean_title.lower() in first_line.lower():
        return _boldify_scannable_terms(content)
    if clean_title and not is_generic_title:
        return _boldify_scannable_terms(f"# {clean_title}\n\n{content}")
    return _boldify_scannable_terms(content)


# ---------------------------------------------------------------------------
# Expert-internal metadata lines to strip from user-facing article views.
# These are useful in backstage/debug views but confusing for accountants.
# ---------------------------------------------------------------------------

_EXPERT_INTERNAL_LINE_RE = re.compile(
    r"^\s*\*?\*?(?:Tipo de corpus|UVT\s+\d{4})\*?\*?\s*:",
    re.IGNORECASE,
)

# Blockquoted or bold-label metadata lines common in practica documents.
# Matches lines like "> **Serie:** ..." or "**Audiencia:** ..." or "**Corpus:** ..."
_PRACTICA_METADATA_LINE_RE = re.compile(
    r"^\s*>?\s*\*{0,2}\s*(?:Serie|Parte|Versi[oó]n|Audiencia|Eje temporal|Normas principales cubiertas|Corpus|Tipo|[UÚ]ltima verificaci[oó]n)\s*\*{0,2}\s*:",
    re.IGNORECASE,
)

# Sections to skip from the rendered article (internal headings)
_ARTICLE_SKIP_SECTIONS = {
    "identificacion",
    "identificación",
    "regla operativa para lia",
    "condiciones de aplicacion",
    "condiciones de aplicación",
    "riesgos de interpretacion",
    "riesgos de interpretación",
    "relaciones normativas",
    "checklist de vigencia",
    "historico de cambios",
    "histórico de cambios",
}

# Section headings that are technical scaffolding — include their body content
# but drop the heading itself from the rendered output.
_ARTICLE_TRANSPARENT_HEADINGS = {
    "texto base referenciado",
    "texto base referenciado (resumen tecnico)",
    "texto base referenciado (resumen técnico)",
}


def _clean_article_reader_markdown(public_text: str) -> str:
    """Clean source markdown for the article reader, preserving formatting.

    Unlike ``_extract_source_view_usable_text`` (which collapses whitespace
    for plain-text summaries), this function preserves markdown structure —
    headings, bullet lists, bold text — while removing internal metadata
    sections and technical labels.
    """
    raw = str(public_text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw:
        return ""

    sections = _parse_markdown_sections(raw)
    if not sections:
        # No ## headings — filter line-by-line on the raw text
        return _boldify_scannable_terms(_filter_article_metadata_lines(raw))

    kept: list[str] = []
    for title, body in sections:
        normalized = str(title or "").strip().lower()
        if normalized in _ARTICLE_SKIP_SECTIONS:
            continue
        if _ui()._SOURCE_INTERNAL_BOUNDARY_RE.match(str(title or "").strip()):
            continue
        cleaned = _filter_article_metadata_lines(body)
        if not cleaned:
            continue
        # Apply hierarchical sub-numbering (e.g. section "7." items → 7.1, 7.2)
        cleaned = _apply_section_subnumbering(str(title or "").strip(), cleaned)
        # Keep the heading unless it's a transparent scaffolding heading
        if normalized in _ARTICLE_TRANSPARENT_HEADINGS:
            kept.append(cleaned)
        else:
            kept.append(f"## {title}\n\n{cleaned}")
    result = "\n\n".join(kept).strip()
    return _boldify_scannable_terms(result)


# ---------------------------------------------------------------------------
# Boldify scannable terms — improve scannability for accountants by bolding
# legal references, form numbers, thresholds, and section numbers.
# ---------------------------------------------------------------------------

# 1. Section headings at start of line — bold the number AND the title:
#    - Dotted hierarchical numbers: "11.1.", "2.1.3.", "1.7.1"
#    - Single numbers with 2+ digits (avoids list items "1.", "2."): "11.", "42."
_SECTION_NUM_LINE_RE = re.compile(
    r"^(#{1,6}\s+)?(\d+(?:\.\d+)+\.?|\d{2,}\.)\s+(.+)$",
    re.MULTILINE,
)

# 2. Article references (e.g. "Art. 772-1 ET", "art. 21-1 ET", "arts. 1.7.1 a 1.7.5")
_ARTICLE_REF_RE = re.compile(
    r"(?<!\*)\b([Aa]rts?\.?\s+\d[\d.\-]+(?:\s+a\s+[\d.\-]+)?(?:\s+(?:ET|DUR\s+\d[\d/]*))\b)",
)

# 3. Ley / Decreto / Resolución references
_NORM_REF_RE = re.compile(
    r"(?<!\*)\b((?:Ley|Decreto|Resoluci[oó]n)\s+(?:DIAN\s+)?\d[\d.]*(?:\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+\d{1,2}\s+de\s+\d{4}|/\d{4}|\s+de\s+\d{4})?)\b",
    re.IGNORECASE,
)

# 4. Formato / Formulario / F.NNNN references
_FORM_REF_RE = re.compile(
    r"(?<!\*)\b([Ff]ormato\s+\d+|[Ff]ormulario\s+\d+|F\.\d+)\b",
)

# 5. UVT thresholds (e.g. "45.000 UVT")
_UVT_REF_RE = re.compile(
    r"(?<!\*)(\$?[\d.]+\s+UVT)\b",
)

# 6. AG year (e.g. "AG 2025")
_AG_YEAR_RE = re.compile(
    r"(?<!\*)\b(AG\s+\d{4})\b",
)

# Inline patterns applied left-to-right; order doesn't matter since
# we skip already-bold spans.
_INLINE_BOLD_PATTERNS: list[re.Pattern[str]] = [
    _ARTICLE_REF_RE,
    _NORM_REF_RE,
    _FORM_REF_RE,
    _UVT_REF_RE,
    _AG_YEAR_RE,
]


def _boldify_scannable_terms(text: str) -> str:
    """Wrap section numbers and key legal/fiscal terms in bold for scannability."""
    # Pass 1: inline legal/fiscal terms — run first so section headings can absorb them
    for pattern in _INLINE_BOLD_PATTERNS:
        def _replace_inline(m: re.Match, _t: str = text) -> str:  # type: ignore[type-arg]
            s = m.start(1)
            e = m.end(1)
            # Already wrapped in ** — skip
            if s >= 2 and _t[s - 2:s] == "**":
                return m.group(0)
            if e + 2 <= len(_t) and _t[e:e + 2] == "**":
                return m.group(0)
            return m.group(0)[:m.start(1) - m.start()] + f"**{m.group(1)}**" + m.group(0)[m.end(1) - m.start():]
        text = pattern.sub(_replace_inline, text)

    # Pass 2: section headings — bold the full line (number + title),
    # stripping any inner ** from Pass 1 to avoid nested bold.
    def _replace_section(m: re.Match) -> str:  # type: ignore[type-arg]
        prefix = m.group(1) or ""
        num = m.group(2)
        title = m.group(3).replace("**", "")
        return f"{prefix}**{num} {title}**"
    text = _SECTION_NUM_LINE_RE.sub(_replace_section, text)

    return text


_SECTION_NUMBER_RE = re.compile(r"^(\d+)\.\s")
_ORDERED_LIST_ITEM_RE = re.compile(r"^(\d+)\.\s")


def _apply_section_subnumbering(heading: str, body: str) -> str:
    """Renumber ordered list items using hierarchical sub-numbering.

    If the section heading starts with a number (e.g. ``7. Title``), then
    top-level ordered list items ``1. …``, ``2. …`` become ``7.1. …``,
    ``7.2. …``, etc.  Sub-section headings ``### N.M. Title`` are left as-is.
    """
    section_match = _SECTION_NUMBER_RE.match(heading)
    if not section_match:
        return body
    section_num = section_match.group(1)
    lines = body.split("\n")
    result: list[str] = []
    for line in lines:
        item_match = _ORDERED_LIST_ITEM_RE.match(line)
        if item_match:
            item_num = item_match.group(1)
            # Only renumber if this looks like a top-level list item (not indented)
            if not line.startswith((" ", "\t")):
                line = f"{section_num}.{item_num}. {line[item_match.end():]}"
        result.append(line)
    return "\n".join(result)


def _filter_article_metadata_lines(text: str) -> str:
    """Remove metadata and internal lines from article body, preserve formatting."""
    lines = str(text or "").split("\n")
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Filter structured metadata lines (doc_id:, authority:, etc.)
        if _ui()._SOURCE_METADATA_LINE_RE.match(stripped):
            continue
        # Filter expert-internal labels (Tipo de corpus, UVT)
        if _EXPERT_INTERNAL_LINE_RE.match(stripped):
            continue
        # Filter practica document metadata lines (> **Serie:** ..., **Audiencia:** ...)
        if _PRACTICA_METADATA_LINE_RE.match(stripped):
            continue
        # Filter legacy top-level ingestion headings (# Ingesta RAG - ...)
        if re.match(r"^\s*#\s+Ingesta RAG\b", stripped, re.IGNORECASE):
            continue
        result.append(line)
    text_out = "\n".join(result)
    # Collapse excessive blank lines but preserve single blanks
    text_out = re.sub(r"\n{3,}", "\n\n", text_out)
    return text_out.strip()


def _build_pdf_from_markdown(text: str, *, title: str) -> bytes:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("PDF generation unavailable: reportlab is not installed.") from exc

    clean_text = str(text or "").replace("\r\n", "\n")
    lines = [line.rstrip() for line in clean_text.split("\n")]
    if not lines:
        lines = ["Sin contenido disponible."]

    page_width, page_height = letter
    margin_x = 56
    margin_top = 56
    margin_bottom = 56
    usable_height = page_height - margin_top - margin_bottom
    line_height = 14
    max_lines_per_page = max(1, int(usable_height // line_height))

    from io import BytesIO

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle(str(title or "Documento"))

    page_line = 0
    y = page_height - margin_top
    pdf.setFont("Helvetica", 10)
    for raw_line in lines:
        line = raw_line if raw_line else " "
        while len(line) > 140:
            chunk = line[:140]
            pdf.drawString(margin_x, y, chunk)
            page_line += 1
            y -= line_height
            line = line[140:]
            if page_line >= max_lines_per_page:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                page_line = 0
                y = page_height - margin_top
        pdf.drawString(margin_x, y, line)
        page_line += 1
        y -= line_height
        if page_line >= max_lines_per_page:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            page_line = 0
            y = page_height - margin_top

    pdf.save()
    return buffer.getvalue()


# ===================================================================
# Text analysis & relevance
# ===================================================================


def _clip_session_content(content: str, *, max_chars: int) -> str:
    value = str(content or "").strip()
    if len(value) <= max_chars:
        return value
    candidate = value[:max_chars].strip()
    block_cut = candidate.rfind("\n\n")
    if block_cut >= int(max_chars * 0.6):
        return candidate[:block_cut].strip()
    sentence_cut = max(candidate.rfind("."), candidate.rfind("!"), candidate.rfind("?"))
    if sentence_cut >= int(max_chars * 0.6):
        return candidate[: sentence_cut + 1].strip()
    line_cut = candidate.rfind("\n")
    if line_cut >= int(max_chars * 0.6):
        return candidate[:line_cut].strip()
    space_cut = candidate.rfind(" ")
    if space_cut > 0:
        return candidate[:space_cut].strip()
    return candidate


# ===================================================================
# Functions extracted from ui_server (Phase 1G)
# ===================================================================

_SOURCE_BASE_SUMMARY_HEADING_RE = re.compile(
    r"^\s*(?:#+\s*)?Texto base referenciado\s*\(resumen t[eé]cnico\)\s*$",
    re.IGNORECASE,
)
_SOURCE_INTERNAL_BOUNDARY_RE = re.compile(
    r"^\s*(?:#+\s*)?(Regla operativa para LIA|Condiciones de aplicaci[oó]n|Riesgos de interpretaci[oó]n|Relaciones normativas|Checklist de vigencia|Hist[oó]rico de cambios)\s*$",
    re.IGNORECASE,
)
_SOURCE_METADATA_LINE_RE = re.compile(
    r"^\s*(?:(?:Archivo|Fuente|Vista|Ingesta RAG|Identificaci[oó]n)\b|(?:doc_id|authority|source_type|article_id|source_url|last_verified_date|validation_status)\s*:)",
    re.IGNORECASE,
)


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _reference_doc_catalog(index_file: Path | None = None) -> dict[str, tuple[str, ...]]:
    from .citation_resolution import reference_doc_catalog as _shared_reference_doc_catalog
    _WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
    _default_index = _WORKSPACE_ROOT / "artifacts" / "document_index.jsonl"
    return _shared_reference_doc_catalog(index_file or _default_index)


def _row_is_active_or_canonical(row: dict[str, Any]) -> bool:
    status = str(row.get("status", "")).strip().lower()
    curation_status = str(row.get("curation_status", "")).strip().lower()
    relative_path = str(row.get("relative_path", "")).strip().lower()
    if status == "active":
        return True
    if curation_status in {"normalized_active", "promoted_curated", "curated_active"}:
        return True
    return "rag_ready" in relative_path


def _extract_reference_keys_from_citation_payload(citation: dict[str, Any]) -> set[str]:
    from .citation_resolution import extract_reference_keys_from_citation_payload as _shared
    return _shared(citation)


def _reference_base_text_for_request_context(citation: dict[str, Any]) -> str:
    if not isinstance(citation, dict):
        return ""
    reference_key = str(citation.get("reference_key") or "").strip().lower()
    reference_type = str(citation.get("reference_type") or "").strip().lower()
    if reference_key == "et" or reference_type == "et":
        return "Estatuto Tributario"
    if reference_key == "dur:1625:2016" or reference_type == "dur":
        return "DUR 1625 de 2016"

    explicit = _clean_markdown_inline(str(citation.get("reference_text") or "").strip())
    if explicit:
        return explicit

    from .normative_references import extract_normative_reference_mentions

    for field in ("source_label", "legal_reference"):
        value = _clean_markdown_inline(str(citation.get(field) or "").strip())
        if not value:
            continue
        mentions = extract_normative_reference_mentions(value)
        for mention in mentions:
            mention_text = _clean_markdown_inline(str(mention.get("reference_text") or "").strip())
            if mention_text:
                return mention_text
        return value
    return ""


def _extract_public_reference_text(raw_text: str) -> str:
    text = str(raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return ""

    lines = text.split("\n")
    start_idx = 0
    for idx, line in enumerate(lines):
        if _SOURCE_BASE_SUMMARY_HEADING_RE.match(line):
            start_idx = idx + 1
            break

    if start_idx == 0:
        for idx, line in enumerate(lines):
            clean = _clean_markdown_inline(line)
            if clean.lower().startswith(("seccion ", "sección ", "introduccion", "introducción")):
                start_idx = idx
                break

    picked: list[str] = []
    for line in lines[start_idx:]:
        clean = _clean_markdown_inline(line)
        probe = re.sub(r"\s+", " ", clean).strip()
        metadata_probe = probe.lstrip("-*• ").strip()
        if _SOURCE_INTERNAL_BOUNDARY_RE.match(metadata_probe):
            break
        if metadata_probe.lower() in {"identificacion", "identificación"}:
            continue
        if _SOURCE_METADATA_LINE_RE.match(metadata_probe):
            continue
        picked.append(probe or line)

    candidate = "\n".join(picked).strip()
    if candidate:
        return candidate
    return text.strip()


def _extract_visible_text_from_html(raw_html: str) -> str:
    text = str(raw_html or "")
    if not text.strip():
        return ""
    text = re.sub(r"(?is)<(script|style|noscript|svg|head)\b.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|section|article|li|ul|ol|table|tr|h[1-6])>", "\n\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = _html_mod.unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _row_lifecycle_rank(row: dict[str, Any]) -> int:
    status = str(row.get("status", "")).strip().lower()
    if status == "active":
        return 2
    if status in {"pending", "draft"}:
        return 1
    return 0


def _row_curation_rank(row: dict[str, Any]) -> int:
    curation_status = str(row.get("curation_status", "")).strip().lower()
    relative_path = str(row.get("relative_path", "")).strip().lower()
    if curation_status in {"normalized_active", "promoted_curated", "curated_active"}:
        return 2
    if "rag_ready" in relative_path:
        return 1
    return 0


def _extract_named_plain_section_body(text: str, *section_titles: str) -> str:
    normalized_titles = {str(title or "").strip().lower().rstrip(".") for title in section_titles if str(title or "").strip()}
    if not normalized_titles:
        return ""
    lines = str(text or "").replace("\r\n", "\n").replace("\r", "\n").splitlines()
    current: list[str] = []
    collecting = False
    for line in lines:
        clean = _clean_markdown_inline(line)
        lowered = str(clean or "").strip().lower().rstrip(".")
        if lowered in normalized_titles:
            if collecting and current:
                break
            collecting = True
            current = []
            continue
        if collecting:
            if lowered in {
                "identificacion",
                "identificación",
                "texto normativo vigente",
                "texto base referenciado",
                "regla operativa para lia",
                "condiciones de aplicacion",
                "condiciones de aplicación",
                "riesgos de interpretacion",
                "riesgos de interpretación",
                "relaciones normativas",
                "checklist de vigencia",
                "historico de cambios",
                "histórico de cambios",
            }:
                break
            current.append(line)
    return "\n".join(current).strip()


def _logical_doc_id(doc_id: str) -> str:
    from .normative_references import logical_doc_id as _shared_logical_doc_id
    return _shared_logical_doc_id(doc_id)


def _coerce_optional_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_json_obj(raw: str) -> dict[str, Any]:
    cleaned = str(raw or "").strip()
    if not cleaned:
        return {}
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return {}
    try:
        parsed_match = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return dict(parsed_match) if isinstance(parsed_match, dict) else {}
