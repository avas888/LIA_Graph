from __future__ import annotations

import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from .citation_resolution import (
    CANONICAL_REFERENCE_RELATION_TYPES,
    document_reference_semantics,
)
from .form_guides import resolve_guide
from .normative_taxonomy import classify_normative_document
from .pipeline_c.orchestrator import generate_llm_strict
from .ui_article_annotations import (
    ANNOTATION_LABELS as _ARTICLE_ANNOTATION_LABELS,
    clean_annotation_body as _clean_article_annotation_body,
    split_article_annotations as _split_article_annotations,
)
from .ui_expert_extractors import _extract_expert_document_metadata
from .ui_form_citation_profile import (
    _deterministic_form_citation_profile,
    _extract_citation_profile_form_number,
    _format_form_reference_title,
    _resolve_form_guide_package_for_context,
    _row_looks_like_guide,
    _spanish_title_case,
)

# ---------------------------------------------------------------------------
# Module-level constants (moved from ui_server during granularize-v1 1A)
# ---------------------------------------------------------------------------

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_PARSED_ARTICLES_PATH = _WORKSPACE_ROOT / "artifacts" / "parsed_articles.jsonl"

# parsed_articles.jsonl aggregates articles from every corpus file — Ley 80,
# Ley 100, CST, ET Libros, etc. — all keyed by bare `article_number`. The ET
# lookup must restrict to ET-corpus source files or it will first-write-wins
# into an unrelated law (e.g. ET Art 1 collided with Ley 80 Art 1 about
# "contratos que celebren las entidades estatales").
_ET_CORPUS_SOURCE_MARKER = "RENTA/NORMATIVA/Normativa/"
_MONTHS_ES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)
_CITATION_PROFILE_BANNED_HINTS = (
    "doc_id",
    "checksum",
    "storage_partition",
    "pipeline",
    "metadata interna",
    "source_tier",
    "provider",
)
_CITATION_PROFILE_GUIDE_PROMPT = "¿Quieres una guía sobre cómo llenarlo?"
_CITATION_PROFILE_GUIDE_UNAVAILABLE = "Esta guía aún no está disponible"
_CITATION_PROFILE_ORIGINAL_LABEL = "Ir a documento original"
_CITATION_PROFILE_ORIGINAL_DOWNLOAD_HELPER = "Se descargará el archivo fuente original disponible en el repositorio."
_CITATION_PROFILE_ORIGINAL_FALLBACK_HELPER = "No se encontró el original; se abrirá el PDF normalizado disponible en LIA."

# Spanish stop-words that, if left dangling at the end of a truncated string,
# make the result look broken (e.g. "…de la Ley." or "…del 26 de."). These are
# peeled off during `_tidy_truncated_citation_text` before an ellipsis is added.
_CITATION_PROFILE_TRAILING_STOPWORDS = frozenset({
    "a", "al", "ante", "bajo", "con", "contra", "de", "del", "desde",
    "durante", "e", "el", "en", "entre", "hacia", "hasta", "la", "las",
    "lo", "los", "mediante", "o", "para", "por", "pues", "que", "segun",
    "según", "si", "sin", "so", "sobre", "su", "sus", "tras", "u", "un",
    "una", "unas", "unos", "y", "ya",
})
_CITATION_PROFILE_TRAILING_TRIM_CHARS = " \t\n,;:.-—–"

# Inline ET-article annotation parsing (labels, regex, splitter) lives in
# `ui_article_annotations.py` — pure, side-effect-free, reusable. The names
# are imported above for back-compat with the callers below and with tests
# that referenced the underscored symbols before the granularize extraction.

# ---------------------------------------------------------------------------
# Lazy-import helpers -- these functions live in ui_server today and will
# migrate to their own modules in later granularize phases (1B-1F).
# Using a deferred accessor keeps this module free of circular imports.
# ---------------------------------------------------------------------------

def _ui() -> Any:
    """Lazy accessor for lia_graph.ui_server (avoids circular import)."""
    from . import ui_server as _mod
    return _mod


def _artifact_file_signature(path: Path) -> str:
    try:
        stat = path.stat()
    except OSError:
        return "missing"
    return f"{int(stat.st_mtime_ns)}:{int(stat.st_size)}"


def _normalize_et_article_lookup_key(value: Any) -> str:
    clean = re.sub(r"\s+", "", str(value or "")).strip(" ,:;")
    if not clean:
        return ""
    return clean.replace(".", "-").replace("_", "-")


@lru_cache(maxsize=4)
def _load_parsed_articles_by_key_cached(path_str: str, signature: str) -> dict[str, dict[str, Any]]:
    del signature
    path = Path(path_str)
    rows_by_key: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return rows_by_key
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                # ET-only filter: the sole caller (`_lookup_parsed_et_article`)
                # resolves ET article references. Without this, the bare article
                # numbers collide across laws and first-write-wins returns the
                # wrong source (see `_ET_CORPUS_SOURCE_MARKER` comment above).
                if _ET_CORPUS_SOURCE_MARKER not in str(row.get("source_path", "")):
                    continue
                for candidate in (row.get("article_key"), row.get("article_number")):
                    key = _normalize_et_article_lookup_key(candidate)
                    if key and key not in rows_by_key:
                        rows_by_key[key] = dict(row)
    except OSError:
        return {}
    return rows_by_key


def _load_parsed_articles_by_key(path: Path = _PARSED_ARTICLES_PATH) -> dict[str, dict[str, Any]]:
    return dict(_load_parsed_articles_by_key_cached(str(path.resolve()), _artifact_file_signature(path)))


def _lookup_parsed_et_article(locator_start: str) -> dict[str, Any] | None:
    key = _normalize_et_article_lookup_key(locator_start)
    if not key:
        return None
    row = _load_parsed_articles_by_key().get(key)
    return dict(row) if isinstance(row, dict) else None


def _tidy_truncated_citation_text(original: str, truncated: str) -> str:
    """Polish a clipped citation-profile string.

    When `_clip_session_content` had to shorten the text, its boundary-detection
    can still leave dangling short words (e.g. `…de la Ley.` or `…del 26 de.`)
    that make the modal look broken. This helper drops trailing Spanish
    stop-words that survive a clip and appends a single ellipsis so the reader
    sees an explicit truncation marker instead of a fragment. If the clipped
    text already ends on legitimate punctuation or a substantive word, it is
    returned unchanged.
    """
    if not truncated:
        return ""
    if len(truncated) >= len(original):
        return truncated
    polished = truncated.rstrip(_CITATION_PROFILE_TRAILING_TRIM_CHARS)
    # Peel off dangling stop-words one at a time (bounded loop so a pathological
    # all-stop-words fragment does not run away).
    for _ in range(8):
        match = re.search(r"(?:^|\s)(\S+)$", polished)
        if not match:
            break
        token = match.group(1).strip(_CITATION_PROFILE_TRAILING_TRIM_CHARS).lower()
        if not token or token not in _CITATION_PROFILE_TRAILING_STOPWORDS:
            break
        polished = polished[: match.start()].rstrip(_CITATION_PROFILE_TRAILING_TRIM_CHARS)
        if not polished:
            break
    if not polished:
        return ""
    if not polished.endswith(("…", "...", ".", "!", "?")):
        polished = f"{polished}…"
    return polished


def _normalize_citation_profile_text(value: Any, *, max_chars: int = 280) -> str:
    prepared = _ui()._clean_markdown_inline(str(value or "").strip())
    clean = _ui()._clip_session_content(prepared, max_chars=max_chars)
    if not clean:
        return ""
    lowered = clean.lower()
    if any(hint in lowered for hint in _CITATION_PROFILE_BANNED_HINTS):
        return ""
    if re.search(r"\bpart[_\s-]?\d+\b", lowered):
        return ""
    if re.search(r"\b[0-9a-f]{8}\b", lowered):
        return ""
    return _tidy_truncated_citation_text(prepared, clean)


def _extract_expert_body_metadata(context: dict[str, Any]) -> dict[str, str]:
    """Extract structured metadata from expert document body text in the context."""
    material = context.get("material") or {}
    for candidate in (
        str(material.get("public_text") or ""),
        str(material.get("usable_text") or ""),
        str(material.get("raw_text") or ""),
    ):
        if not candidate.strip():
            continue
        meta = _extract_expert_document_metadata(candidate)
        if meta:
            return meta
    return {}


def _collect_citation_profile_texts(context: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    material = context.get("material") or {}
    for candidate in (
        str(material.get("usable_text") or ""),
        str(material.get("public_text") or ""),
    ):
        clean = _ui()._extract_source_view_usable_text(candidate) or _ui()._normalize_citation_profile_text(candidate, max_chars=7000)
        if clean:
            texts.append(clean)
    # Supplement with structured sections from RAG-ready markdown when
    # the primary sources yielded thin text (decreto/resolucion docs).
    # Prefer requested_raw_text (the actual document) over material raw_text
    # which may be from a different document due to provenance_uri collisions.
    if all(len(t) < 200 for t in texts):
        raw_text = str(context.get("requested_raw_text") or "") or str(material.get("raw_text") or "")
        if raw_text:
            section_map = _ui()._markdown_section_map(raw_text)
            for section_key in (
                "texto base referenciado (resumen tecnico)",
                "texto base referenciado (resumen técnico)",
                "condiciones de aplicacion",
                "condiciones de aplicación",
                "riesgos de interpretacion",
                "riesgos de interpretación",
                "regla operativa para lia",
            ):
                section_text = section_map.get(section_key, "")
                # Skip scaffold placeholder text
                if "scaffold debe evolucionar" in section_text.lower():
                    continue
                clean = _ui()._normalize_citation_profile_text(section_text, max_chars=2000)
                if clean:
                    texts.append(clean)
    for analysis in list(context.get("related_analyses") or []):
        clean = _ui()._extract_source_view_usable_text(str(analysis.get("public_text") or "")) or str(analysis.get("usable_text") or "").strip()
        if clean:
            texts.append(clean)
    return texts


def _find_grounded_profile_sentence(
    texts: list[str],
    *,
    keywords: tuple[str, ...],
    max_chars: int = 240,
) -> str:
    best_sentence = ""
    best_score = 0
    for text in texts:
        for sentence in _ui()._split_sentences(text):
            lowered = sentence.lower()
            score = sum(1 for keyword in keywords if keyword in lowered)
            if score > best_score:
                best_score = score
                best_sentence = sentence
    if best_score <= 0:
        return ""
    return _ui()._normalize_citation_profile_text(best_sentence, max_chars=max_chars)


def _classify_document_family(citation: dict[str, Any], row: dict[str, Any] | None = None) -> str:
    return classify_normative_document(
        citation if isinstance(citation, dict) else {},
        row if isinstance(row, dict) else {},
    ).document_family


def _format_citation_profile_date(value: Any) -> str:
    clean = str(value or "").strip()
    if not clean:
        return ""
    try:
        parsed = datetime.fromisoformat(clean)
    except ValueError:
        return clean
    d = parsed.date()
    return f"{_MONTHS_ES[d.month - 1]} {d.day}, {d.year}"


def _latest_identified_citation_profile_date(rows: list[dict[str, Any]]) -> str:
    iso_dates = []
    for row in rows:
        for field in ("publish_date", "effective_date"):
            raw = str(row.get(field) or "").strip()
            if not raw:
                continue
            try:
                iso_dates.append(datetime.fromisoformat(raw).date().isoformat())
            except ValueError:
                pass
    return _ui()._format_citation_profile_date(max(iso_dates)) if iso_dates else ""


_LEY_YEAR_RE = re.compile(r"(?:ley|decreto|resolucion|circular)[:\s_]+\d+[:\s_]+(\d{4})", re.IGNORECASE)
_LEY_TITLE_YEAR_RE = re.compile(r"(?:Ley|Decreto|Resolución|Circular)\s+\d+\s+de\s+(\d{4})", re.IGNORECASE)
_DOC_ID_YEAR_RE = re.compile(r"co_(?:ley|decreto|resolucion|circular)_\d+_(\d{4})")


def _extract_normative_year(context: dict[str, Any]) -> str:
    """Extract the official year of a normative document from reference_key, doc_id, or title.

    Returns a 4-digit year string or "" if not determinable.
    """
    citation = dict(context.get("citation") or {})
    for source in (
        str(citation.get("reference_key") or ""),
        str(context.get("doc_id") or citation.get("doc_id") or ""),
    ):
        m = _LEY_YEAR_RE.search(source)
        if m:
            return m.group(1)
        m = _DOC_ID_YEAR_RE.search(source)
        if m:
            return m.group(1)
    for source in (
        str(context.get("title") or ""),
        str(dict(context.get("requested_row") or {}).get("notes") or ""),
    ):
        m = _LEY_TITLE_YEAR_RE.search(source)
        if m:
            return m.group(1)
    return ""


def _official_publish_date_or_year(publish_date_raw: str, normative_year: str) -> str:
    """Return the formatted publish_date if its year matches the normative year.

    When the publish_date year doesn't match (i.e. it's the ingestion date, not
    the law's real date), fall back to "Año {year}".  Returns "" if neither is
    available.
    """
    clean = str(publish_date_raw or "").strip()
    if clean and normative_year:
        try:
            pd_year = str(datetime.fromisoformat(clean).year)
        except ValueError:
            pd_year = ""
        if pd_year == normative_year:
            return _ui()._format_citation_profile_date(clean)
        return f"Año {normative_year}"
    if clean:
        return _ui()._format_citation_profile_date(clean)
    if normative_year:
        return f"Año {normative_year}"
    return ""


def _resolve_superseded_label(row: dict[str, Any], rows_by_doc_id: dict[str, dict[str, Any]]) -> str:
    superseded_by = str(row.get("superseded_by", "")).strip()
    if not superseded_by:
        return ""
    replacement = rows_by_doc_id.get(superseded_by)
    if not replacement:
        return "Tiene reemplazo registrado."
    replacement_material = _ui()._resolve_source_view_material(doc_id=superseded_by, view="normalized")
    if replacement_material:
        return _ui()._pick_source_display_title(
            requested_row=replacement,
            resolved_row=dict(replacement_material.get("resolved_row") or replacement),
            doc_id=superseded_by,
            raw_text=str(replacement_material.get("raw_text") or ""),
            public_text=str(replacement_material.get("public_text") or ""),
        )
    return _ui()._normalize_citation_profile_text(str(replacement.get("notes") or replacement.get("title") or "").strip(), max_chars=120)


def _collect_citation_profile_context(
    doc_id: str,
    *,
    index_file: Path | None = None,
    allow_remote_fallback: bool = True,
) -> dict[str, Any] | None:
    if index_file is None:
        index_file = _ui().INDEX_FILE_PATH
    rows_by_doc_id = _ui()._load_index_rows_by_doc_id(index_file)
    requested_row = rows_by_doc_id.get(doc_id)
    if requested_row is None and allow_remote_fallback:
        requested_row = _ui()._sb_find_document_row(doc_id)
    if requested_row is None:
        return None

    citation_payload = _ui()._build_public_citation_from_row(requested_row)
    # Promote locator_start from reference_detail for ET article resolution
    if not str(citation_payload.get("locator_start") or "").strip():
        _ref_detail = citation_payload.get("reference_detail")
        if isinstance(_ref_detail, dict):
            _locator = str(_ref_detail.get("locator_start") or "").strip()
            if _locator:
                citation_payload["locator_start"] = _locator
    material = _ui()._resolve_source_view_material(doc_id=doc_id, view="normalized", index_file=index_file)
    # Supabase text fallback for the requested row. In dev/staging/prod the
    # `documents.absolute_path` column is NULL (knowledge_base files live only
    # on the ingestion host), so `_resolve_source_view_material` returns a
    # material dict with empty `raw_text`/`public_text`/`usable_text` and the
    # modal body falls back to "No se encontró texto original verificable...".
    # Reassemble the document markdown from `document_chunks` to hydrate the
    # material for the requested row only — we deliberately do NOT touch
    # related_analyses / ranking to avoid rank-tuple displacement.
    if isinstance(material, dict):
        _material_raw = str(material.get("raw_text") or "").strip()
        if not _material_raw:
            _material_doc_id = str(
                (material.get("resolved_row") or {}).get("doc_id")
                or str(requested_row.get("doc_id") or "")
            ).strip()
            if _material_doc_id:
                _sb_text = _ui()._sb_assemble_document_markdown(_material_doc_id)
                if _sb_text:
                    material["raw_text"] = _sb_text
                    _extracted_base = (
                        _ui()._extract_visible_text_from_html(_sb_text)
                        if _ui()._looks_like_html_document(_sb_text)
                        else _sb_text
                    )
                    _public = _ui()._extract_public_reference_text(_extracted_base)
                    material["public_text"] = _public
                    material["usable_text"] = _ui()._extract_source_view_usable_text(_public)
    requested_logical_doc_id = _ui()._logical_doc_id(str(requested_row.get("doc_id", "")).strip())
    requested_semantics = document_reference_semantics(requested_row)
    requested_entity_id = str(requested_semantics.get("entity_id") or "").strip()
    requested_identity_keys = {
        str(item).strip()
        for item in list(requested_semantics.get("reference_identity_keys") or [])
        if str(item).strip()
    }
    related_rows: list[dict[str, Any]] = []
    related_analyses: list[dict[str, Any]] = []
    seen_doc_ids: set[str] = set()

    def _register_row(candidate: dict[str, Any]) -> None:
        candidate_doc_id = str(candidate.get("doc_id", "")).strip()
        if not candidate_doc_id or candidate_doc_id in seen_doc_ids:
            return
        seen_doc_ids.add(candidate_doc_id)
        related_rows.append(dict(candidate))
        related_analyses.append(_ui()._build_source_view_candidate_analysis(candidate, view="normalized"))

    _register_row(requested_row)
    if requested_logical_doc_id:
        for candidate in rows_by_doc_id.values():
            candidate_doc_id = str(candidate.get("doc_id", "")).strip()
            if not candidate_doc_id or candidate_doc_id in seen_doc_ids:
                continue
            if _ui()._logical_doc_id(candidate_doc_id) != requested_logical_doc_id:
                continue
            if not _ui()._row_is_active_or_canonical(candidate):
                continue
            _register_row(candidate)

    _COMPANION_RELATION_TYPES = CANONICAL_REFERENCE_RELATION_TYPES | {
        "interprets", "implements", "companion_to",
    }
    if requested_entity_id:
        for candidate in rows_by_doc_id.values():
            candidate_doc_id = str(candidate.get("doc_id", "")).strip()
            if not candidate_doc_id or candidate_doc_id in seen_doc_ids:
                continue
            candidate_semantics = document_reference_semantics(candidate)
            if str(candidate_semantics.get("entity_id") or "").strip() != requested_entity_id:
                continue
            relation_type = str(candidate_semantics.get("relation_type") or "").strip().lower()
            if relation_type not in _COMPANION_RELATION_TYPES:
                continue
            if not _ui()._row_is_active_or_canonical(candidate):
                continue
            _register_row(candidate)

    # Supabase fallback for Ley companion layers not yet in JSONL index
    if allow_remote_fallback and len(related_rows) < 3 and requested_logical_doc_id:
        for _suffix in ("_expertos", "_practica"):
            _companion_id = f"{requested_logical_doc_id}{_suffix}"
            if _companion_id in seen_doc_ids:
                continue
            _sb_row = _ui()._sb_find_document_row(_companion_id)
            if isinstance(_sb_row, dict) and _ui()._row_is_active_or_canonical(_sb_row):
                _register_row(_sb_row)

    if len(related_rows) < 8 and requested_identity_keys:
        catalog = _ui()._reference_doc_catalog(index_file)
        for reference_key in sorted(requested_identity_keys):
            for candidate_doc_id in catalog.get(reference_key, ()):
                candidate = rows_by_doc_id.get(candidate_doc_id)
                if not isinstance(candidate, dict):
                    continue
                if not _ui()._row_is_active_or_canonical(candidate):
                    continue
                _register_row(candidate)
                if len(related_rows) >= 8:
                    break
            if len(related_rows) >= 8:
                break

    resolved_row = dict(material.get("resolved_row") or requested_row) if material else dict(requested_row)
    # When material resolved to a different document (provenance_uri collision),
    # also load the requested row's own markdown so that title/lead/section
    # extraction uses the correct document's structured content.
    requested_raw_text = ""
    resolved_doc_id = str(resolved_row.get("doc_id") or "").strip()
    if resolved_doc_id and resolved_doc_id != str(requested_row.get("doc_id") or "").strip():
        _req_abs = str(requested_row.get("absolute_path") or "").strip()
        if _req_abs:
            try:
                requested_raw_text = Path(_req_abs).read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
        if not requested_raw_text:
            _req_sb = _ui()._sb_assemble_document_markdown(doc_id)
            if _req_sb:
                requested_raw_text = _req_sb
    title = _ui()._pick_source_display_title(
        requested_row=dict(requested_row),
        resolved_row=resolved_row,
        doc_id=doc_id,
        raw_text=requested_raw_text or str((material or {}).get("raw_text") or ""),
        public_text=str((material or {}).get("public_text") or ""),
    )
    document_profile = classify_normative_document(citation_payload, requested_row)
    family = document_profile.document_family
    return {
        "doc_id": str(doc_id).strip(),
        "title": title,
        "citation": citation_payload,
        "document_family": family,
        "document_profile": document_profile.to_public_dict(),
        "requested_row": dict(requested_row),
        "resolved_row": resolved_row,
        "material": material or {},
        "requested_raw_text": requested_raw_text,
        "related_rows": related_rows,
        "related_analyses": related_analyses,
        "reference_key": str(citation_payload.get("reference_key", "")).strip(),
        "reference_identity_keys": sorted(requested_identity_keys),
        "mentioned_reference_keys": [
            str(item).strip()
            for item in list(requested_semantics.get("mentioned_reference_keys") or [])
            if str(item).strip()
        ],
        "entity_id": requested_entity_id,
        "entity_type": str(requested_semantics.get("entity_type") or "").strip(),
        "relation_type": str(requested_semantics.get("relation_type") or "").strip(),
        "logical_doc_id": requested_logical_doc_id,
        "rows_by_doc_id": rows_by_doc_id,
    }


def _collect_citation_profile_context_by_reference_key(
    reference_key: str,
    *,
    index_file: Path | None = None,
    allow_remote_fallback: bool = True,
) -> dict[str, Any] | None:
    if index_file is None:
        index_file = _ui().INDEX_FILE_PATH
    normalized = str(reference_key or "").strip()
    if not normalized:
        return None

    candidate_doc_id = _ui()._find_reference_doc_id(normalized, index_file=index_file)
    if candidate_doc_id:
        return _ui()._collect_citation_profile_context(
            candidate_doc_id,
            index_file=index_file,
            allow_remote_fallback=allow_remote_fallback,
        )

    normalized_form_key = normalized.lower()
    guide_package = resolve_guide(normalized_form_key, root=_ui().FORM_GUIDES_ROOT)
    if guide_package is None and not normalized_form_key.startswith("formulario:"):
        return None

    manifest = getattr(guide_package, "manifest", None)
    raw_manifest_title = _ui()._normalize_citation_profile_text(
        getattr(manifest, "title", "") if manifest is not None else "",
        max_chars=160,
    )
    title = _ui()._format_form_reference_title(
        _ui()._reference_label_from_key(normalized_form_key),
        raw_manifest_title,
    )
    if not title:
        title = raw_manifest_title or _ui()._reference_label_from_key(normalized_form_key)
    label = _ui()._reference_label_from_key(normalized_form_key)
    source_payload = _ui()._guide_primary_source_payload(guide_package)
    requested_row = {
        "doc_id": "",
        "title": title,
        "relative_path": (
            f"form_guides/{normalized_form_key.replace(':', '_')}/{getattr(manifest, 'profile_id', 'default')}/guide_manifest.json"
        ),
        "status": "active",
        "source_type": "official_primary" if source_payload.get("official_url") else "official_secondary",
        "authority": source_payload.get("authority") or "DIAN",
        "topic": "declaracion_renta",
        "pais": "colombia",
        "knowledge_class": "normative_base",
        "tipo_de_documento": "formulario",
        "notes": title,
        "reference_key": normalized_form_key,
        "entity_id": normalized_form_key,
        "entity_type": "formulario",
        "relation_type": "canonical_for",
        "reference_identity_keys": [normalized_form_key],
        "mentioned_reference_keys": [],
        "admissible_surfaces": ["canonical_card", "analytical_qa"],
        "supports_fields": [
            "lead",
            "purpose_text",
            "mandatory_when",
            "latest_identified",
            "professional_impact",
        ],
    }
    citation = {
        "doc_id": "",
        "reference_key": normalized_form_key,
        "reference_type": "formulario" if normalized_form_key.startswith("formulario:") else "",
        "source_label": label,
        "legal_reference": title,
        "authority": source_payload.get("authority") or "DIAN",
        "source_provider": source_payload.get("source_provider") or "DIAN",
        "official_url": source_payload.get("official_url") or "",
        "download_url": "",
        "download_original_url": "",
    }
    document_profile = classify_normative_document(citation, requested_row).to_public_dict()
    return {
        "doc_id": "",
        "title": title,
        "citation": citation,
        "document_family": str(document_profile.get("document_family") or "generic").strip(),
        "document_profile": document_profile,
        "requested_row": requested_row,
        "resolved_row": dict(requested_row),
        "material": {},
        "related_rows": [dict(requested_row)],
        "related_analyses": [],
        "reference_key": normalized_form_key,
        "reference_identity_keys": [normalized_form_key],
        "mentioned_reference_keys": [],
        "entity_id": normalized_form_key,
        "entity_type": "formulario",
        "relation_type": "canonical_for",
        "logical_doc_id": "",
        "rows_by_doc_id": _ui()._load_index_rows_by_doc_id(index_file),
    }


def _build_fallback_citation_profile_payload(
    *,
    doc_id: str = "",
    reference_key: str = "",
    message_context: str = "",
    locator_text: str = "",
    locator_kind: str = "",
    locator_start: str = "",
    locator_end: str = "",
) -> dict[str, Any]:
    del doc_id, message_context, locator_text, locator_kind, locator_end

    normalized_reference_key = str(reference_key or "").strip().lower()
    locator_display = _normalize_et_article_lookup_key(locator_start)
    if normalized_reference_key != "et" or not locator_display:
        return {}

    citation = {
        "reference_key": "et",
        "reference_type": "et",
        "locator_start": locator_display,
        "locator_text": f"Artículo {locator_display}",
        "source_label": "Estatuto Tributario",
        "legal_reference": "Estatuto Tributario",
    }
    document_profile = classify_normative_document(citation, {}).to_public_dict()

    parsed_article = _lookup_parsed_et_article(locator_display)
    heading = _normalize_citation_profile_text((parsed_article or {}).get("heading"), max_chars=180).rstrip(".")
    if heading:
        lead = _normalize_citation_profile_text(
            f"El Artículo {locator_display} del Estatuto Tributario regula {heading.lower()}.",
            max_chars=320,
        )
    else:
        lead = _normalize_citation_profile_text(
            f"Revisa el Artículo {locator_display} del Estatuto Tributario como referencia normativa base para esta consulta.",
            max_chars=320,
        )

    facts = [
        {
            "label": "Artículo consultado",
            "value": f"ET Artículo {locator_display}" + (f". {heading}." if heading else ""),
        }
    ]

    original_text: dict[str, Any] | None = None
    raw_quote = str((parsed_article or {}).get("full_text") or (parsed_article or {}).get("body") or "").strip()
    if raw_quote:
        raw_quote = raw_quote.split("\n---\n", 1)[0].strip()
        raw_body, annotations = _split_article_annotations(raw_quote)
        cleaned_body = _ui()._clean_markdown_inline(raw_body)
        clipped_body = _ui()._clip_session_content(cleaned_body, max_chars=1100)
        quote = _tidy_truncated_citation_text(cleaned_body, clipped_body)
        if quote:
            original_text = {
                "title": "Texto Normativo",
                "quote": quote,
                "annotations": annotations,
                "source_url": _ui()._prefer_normograma_mintic_mirror(
                    f"https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm#{locator_display}"
                ),
                "evidence_status": "verified",
            }

    source_url = _ui()._prefer_normograma_mintic_mirror(
        f"https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm#{locator_display}"
    )
    source_action = {
        "label": _CITATION_PROFILE_ORIGINAL_LABEL,
        "state": "available",
        "url": source_url,
        "helper_text": None,
    }

    corpus_gap = original_text is None
    caution_banner: dict[str, Any] | None = dict(document_profile.get("caution_banner") or {}) or None
    if corpus_gap:
        lead = _normalize_citation_profile_text(
            f"No tenemos el texto del Artículo {locator_display} del Estatuto Tributario en el corpus "
            "local. Consulta la fuente oficial para el contenido verbatim.",
            max_chars=320,
        )
        caution_banner = {
            "title": "Texto no disponible en el corpus",
            "body": (
                f"El texto del Artículo {locator_display} del Estatuto Tributario no está en el "
                "corpus local de Lia. Puedes abrirlo en la fuente oficial (DIAN / Normograma) con "
                "el botón «Ir a documento original»."
            ),
            "tone": "warning",
        }

    return {
        "title": f"Estatuto Tributario, Artículo {locator_display}",
        "document_family": str(document_profile.get("document_family") or "et_dur").strip(),
        "family_subtype": str(document_profile.get("family_subtype") or "").strip(),
        "hierarchy_tier": str(document_profile.get("hierarchy_tier") or "").strip(),
        "binding_force": str(document_profile.get("binding_force") or "").strip(),
        "binding_force_rank": int(document_profile.get("binding_force_rank") or 0),
        "analysis_template_id": str(document_profile.get("analysis_template_id") or "").strip(),
        "ui_surface": str(document_profile.get("ui_surface") or "").strip(),
        "allowed_secondary_overlays": list(document_profile.get("allowed_secondary_overlays") or []),
        "lead": lead,
        "facts": facts,
        "sections": [],
        "original_text": original_text,
        "vigencia_detail": None,
        "expert_comment": None,
        "additional_depth_sections": None,
        "caution_banner": caution_banner,
        "corpus_gap": corpus_gap,
        "analysis_action": {
            "label": "Abrir análisis normativo",
            "state": "not_applicable",
            "url": None,
            "helper_text": None,
        },
        "companion_action": {
            "label": _CITATION_PROFILE_GUIDE_PROMPT,
            "state": "not_applicable",
            "url": None,
            "helper_text": None,
        },
        "source_action": source_action,
    }


def _build_citation_profile_prompt(context: dict[str, Any]) -> str:
    family = str(context.get("document_family") or "generic").strip()
    title = str(context.get("title") or "Documento").strip()
    citation = dict(context.get("citation") or {})
    requested_row = dict(context.get("requested_row") or {})
    material = dict(context.get("material") or {})
    texts = _ui()._collect_citation_profile_texts(context)
    snippets = []
    for text in texts[:5]:
        for sentence in _ui()._split_sentences(text)[:2]:
            snippets.append(f"- {sentence}")
            if len(snippets) >= 6:
                break
        if len(snippets) >= 6:
            break
    snippets_block = "\n".join(snippets) or "- Sin extractos utilizables."

    focus = {
        "formulario": (
            "explica para qué sirve el formulario, "
            "indica desde qué año gravable o periodo fiscal empezó a ser obligatorio (fecha concreta o resolución que lo prescribió), "
            "y cómo impacta el trabajo del contador"
        ),
        "constitucion": "explica qué principio o marco constitucional aporta y por qué importa para la lectura tributaria",
        "ley": "explica qué regula la ley, su propósito regulatorio y el impacto para la profesión contable",
        "decreto": "explica qué regula el decreto, su propósito regulatorio y el impacto para la profesión contable",
        "resolucion": "explica qué fija la resolución, su propósito regulatorio y el impacto para la profesión contable",
        "et_dur": "explica qué regula la norma compilada o estatutaria y el impacto para la profesión contable",
        "concepto": "explica qué criterio fija el documento y qué implica para contadores",
        "circular": "explica qué lineamiento fija la circular y qué implica para contadores",
        "jurisprudencia": "explica qué problema jurídico resolvió, cuál fue la decisión central y su relevancia vigente",
        "generic": "explica qué es el documento y por qué le sirve a un contador",
    }.get(family, "explica el documento seleccionado de forma útil para un contador")

    metadata_lines = [
        f"titulo={title}",
        f"familia={family}",
        f"source_label={citation.get('source_label') or ''}",
        f"legal_reference={citation.get('legal_reference') or ''}",
        f"authority={citation.get('authority') or requested_row.get('authority') or ''}",
        f"publish_date={requested_row.get('publish_date') or ''}",
        f"effective_date={requested_row.get('effective_date') or ''}",
        f"vigencia={requested_row.get('vigencia') or ''}",
        f"notes={requested_row.get('notes') or ''}",
    ]
    source_text = _ui()._clip_session_content(
        str(material.get("usable_text") or material.get("public_text") or "\n\n".join(texts)).strip(),
        max_chars=7000,
    )
    return (
        "Eres editor legal y tributario para contadores.\n"
        "Tu tarea es construir una ficha breve y creíble del documento seleccionado.\n"
        f"Enfócate en: {focus}.\n"
        "Usa únicamente metadata explícita y extractos del documento seleccionado o de sus variantes lógicas.\n"
        "No menciones corpus, pipeline, metadata interna, checksums, part_XX, doc_id, provider ni source_tier.\n"
        "Si un dato no está soportado, omítelo.\n"
        "Responde SOLO JSON válido con llaves opcionales entre estas:\n"
        '{"lead":"","purpose_text":"","mandatory_when":"","regulatory_purpose":"","criterion_text":"","problem_resolved":"","decision_core":"","relevance_text":"","professional_impact":""}\n'
        "mandatory_when: para formularios debe indicar DESDE CUÁNDO es obligatorio (año gravable, periodo, o resolución que lo prescribió), NO para quién.\n"
        "Cada valor debe ser breve, directo y anclado al documento seleccionado.\n\n"
        "metadata:\n"
        f"{chr(10).join(metadata_lines)}\n\n"
        "extractos:\n"
        f"{snippets_block}\n\n"
        "texto_fuente:\n"
        f"{source_text}\n"
    )


def _llm_citation_profile_payload(context: dict[str, Any]) -> dict[str, Any]:
    try:
        from .normativa.assembly import build_normativa_modal_payload
        from .normativa.orchestrator import run_normativa_surface

        _diagnostics, runtime_payload = run_normativa_surface(context)
        synthesis = runtime_payload.get("synthesis")
    except Exception:  # noqa: BLE001
        return {}
    if synthesis is None:
        return {}
    payload = build_normativa_modal_payload(synthesis)
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        if key == "sections_payload" and isinstance(value, list):
            sections: list[dict[str, str]] = []
            for item in value:
                if not isinstance(item, dict):
                    continue
                title = _ui()._normalize_citation_profile_text(item.get("title"), max_chars=120)
                body = str(item.get("body") or "").strip()
                body = re.sub(r"\n{3,}", "\n\n", body)
                if not title or not body:
                    continue
                sections.append(
                    {
                        "id": str(item.get("id") or "").strip() or "normativa_section",
                        "title": title,
                        "body": body,
                    }
                )
            if sections:
                normalized["sections_payload"] = sections
            continue
        clean = _ui()._normalize_citation_profile_text(value, max_chars=320)
        if clean:
            normalized[str(key)] = clean
    return normalized


def _should_skip_citation_profile_llm(context: dict[str, Any]) -> bool:
    family = str(context.get("document_family") or "").strip().lower()
    if not family:
        profile = dict(context.get("document_profile") or {})
        family = str(profile.get("document_family") or "").strip().lower()
    if not family:
        family = _ui()._classify_document_family(
            dict(context.get("citation") or {}),
            dict(context.get("requested_row") or {}),
        ).strip().lower()
    return family == "formulario"


def _append_citation_profile_fact(facts: list[dict[str, str]], label: str, value: str) -> None:
    clean_value = _ui()._normalize_citation_profile_text(value, max_chars=180)
    if not clean_value:
        return
    if any(item.get("label") == label for item in facts):
        return
    facts.append({"label": label, "value": clean_value})


def _build_citation_profile_facts(context: dict[str, Any], llm_payload: dict[str, str] | None = None) -> list[dict[str, str]]:
    payload = dict(llm_payload or {})
    row = dict(context.get("requested_row") or {})
    rows = list(context.get("related_rows") or [row])
    rows_by_doc_id = dict(context.get("rows_by_doc_id") or {})
    family = str(context.get("document_family") or "generic").strip()
    texts = _ui()._collect_citation_profile_texts(context)
    citation = dict(context.get("citation") or {})

    latest_identified = _ui()._latest_identified_citation_profile_date(rows)
    publish_date = _ui()._format_citation_profile_date(row.get("publish_date")) or _ui()._format_citation_profile_date(row.get("effective_date"))
    normative_year = _ui()._extract_normative_year(context)
    official_date = _ui()._official_publish_date_or_year(
        row.get("publish_date") or row.get("effective_date") or "", normative_year,
    )
    vigencia = str(row.get("vigencia", "")).strip().lower()
    vigencia_text = ""
    if vigencia and vigencia != "desconocida":
        if vigencia == "vigente":
            vigencia_text = "Vigente"
        elif vigencia == "derogada":
            replacement = _ui()._resolve_superseded_label(row, rows_by_doc_id)
            vigencia_text = f"No vigente. {replacement}".strip() if replacement else "No vigente"
        else:
            vigencia_text = vigencia.capitalize()
    elif str(row.get("superseded_by", "")).strip():
        replacement = _ui()._resolve_superseded_label(row, rows_by_doc_id)
        vigencia_text = f"Tiene reemplazo registrado. {replacement}".strip() if replacement else "Tiene reemplazo registrado."

    facts: list[dict[str, str]] = []
    if _ui()._citation_targets_et_article(citation):
        et_row = _ui()._resolve_et_locator_row(context)
        et_meta: dict[str, str] = {}
        if et_row is not None:
            et_analysis = _ui()._build_source_view_candidate_analysis(et_row, view="normalized")
            et_meta = _ui()._extract_et_article_metadata(str(et_analysis.get("raw_text") or ""))
        article_display = (
            str(et_meta.get("article_number_display") or "").strip()
            or _ui()._citation_et_locator_label(citation)
        )
        article_title = str(et_meta.get("article_title") or "").strip()
        vigencia_detail = _ui()._build_et_article_vigencia_detail(context)
        if article_display:
            label = f"Artículo consultado"
            value = f"ET Artículo {article_display}"
            if article_title:
                value = f"{value}. {article_title}."
            _ui()._append_citation_profile_fact(facts, label, value)
        _ui()._append_citation_profile_fact(
            facts,
            "Vigencia específica",
            "\n".join(
                item
                for item in (
                    vigencia_detail.get("label"),
                    vigencia_detail.get("basis"),
                    vigencia_detail.get("notes"),
                    f"Última verificación del corpus: {vigencia_detail.get('last_verified_date')}"
                    if str(vigencia_detail.get("last_verified_date") or "").strip()
                    else "",
                )
                if str(item or "").strip()
            ),
        )
        return facts

    if family == "formulario":
        purpose_text = payload.get("purpose_text") or _ui()._find_grounded_profile_sentence(
            texts,
            keywords=(
                "sirve",
                "report",
                "liquid",
                "impuesto",
                "declaración",
                "declaracion",
                "presentar",
            ),
        )
        mandatory_when = payload.get("mandatory_when") or _ui()._find_grounded_profile_sentence(
            texts,
            keywords=(
                "prescrit",
                "resoluci",
                "año gravable",
                "ano gravable",
                "obligad",
                "debe",
                "deberá",
                "debera",
                "aplica",
                "utilizar",
            ),
        )
        if mandatory_when and vigencia_text == "Vigente" and "vigente" not in mandatory_when.lower():
            mandatory_when = f"{mandatory_when} Sigue vigente."
        _ui()._append_citation_profile_fact(facts, "Para qué sirve", purpose_text)
        _ui()._append_citation_profile_fact(facts, "Desde cuándo es obligatorio", mandatory_when)
        _ui()._append_citation_profile_fact(facts, "Última actualización identificada", latest_identified)
        return facts

    if family == "constitucion":
        constitutional_anchor = payload.get("regulatory_purpose") or _ui()._find_grounded_profile_sentence(
            texts,
            keywords=("constitución", "constitucion", "principio", "garantiza", "reserva", "debido proceso"),
        )
        _ui()._append_citation_profile_fact(facts, "Marco constitucional", constitutional_anchor)
        _ui()._append_citation_profile_fact(facts, "Fecha de referencia", publish_date)
        _ui()._append_citation_profile_fact(facts, "Vigencia", vigencia_text or "Vigente")
        return facts

    if family in {"ley", "decreto", "resolucion", "et_dur"}:
        regulatory_purpose = payload.get("regulatory_purpose") or _ui()._find_grounded_profile_sentence(
            texts,
            keywords=("objeto", "finalidad", "propósito", "proposito", "regula", "establece", "define", "compila"),
        )
        _ui()._append_citation_profile_fact(facts, "Fecha de expedición", official_date)
        _ui()._append_citation_profile_fact(facts, "Propósito regulatorio", regulatory_purpose)
        if vigencia_text:
            _ui()._append_citation_profile_fact(facts, "Vigencia", vigencia_text)
        return facts

    if family in {"concepto", "circular"}:
        _ui()._append_citation_profile_fact(facts, "Emisión", official_date)
        _ui()._append_citation_profile_fact(facts, "Estado de vigencia/reemplazo", vigencia_text)
        _ui()._append_citation_profile_fact(facts, "Última actualización identificada", latest_identified)
        return facts

    if family == "jurisprudencia":
        decision_core = payload.get("decision_core") or _ui()._find_grounded_profile_sentence(
            texts,
            keywords=("decid", "resolv", "declaró", "declaro", "determin", "conclu"),
        )
        relevance = payload.get("relevance_text") or vigencia_text
        _ui()._append_citation_profile_fact(facts, "Fecha", official_date)
        _ui()._append_citation_profile_fact(facts, "Decisión central", decision_core)
        _ui()._append_citation_profile_fact(facts, "Relevancia vigente", relevance)
        return facts

    # Expert/interpretative documents: extract structured metadata from body text
    expert_meta = _extract_expert_body_metadata(context)
    if expert_meta:
        normas = expert_meta.get("normas_base", "").strip()
        if normas:
            _ui()._append_citation_profile_fact(facts, "Normas base", normas)
        ambito = expert_meta.get("ambito_aplicacion", "").strip()
        if ambito:
            _ui()._append_citation_profile_fact(facts, "Ámbito de aplicación", ambito)
        fecha_verif = expert_meta.get("fecha_verificacion", "").strip()
        if fecha_verif:
            _ui()._append_citation_profile_fact(facts, "Fecha de última verificación", fecha_verif)
        if not normas and not ambito:
            _ui()._append_citation_profile_fact(facts, "Fecha identificada", official_date or latest_identified)
            _ui()._append_citation_profile_fact(facts, "Vigencia", vigencia_text)
        return facts

    _ui()._append_citation_profile_fact(facts, "Fecha identificada", official_date or latest_identified)
    _ui()._append_citation_profile_fact(facts, "Vigencia", vigencia_text)
    return facts


def _resolve_companion_action(context: dict[str, Any]) -> dict[str, Any]:
    family = str(context.get("document_family") or "").strip()
    label = _CITATION_PROFILE_GUIDE_PROMPT
    if family != "formulario":
        return {"label": label, "state": "not_applicable", "url": None, "helper_text": None}

    row = dict(context.get("requested_row") or {})
    citation = dict(context.get("citation") or {})
    if _ui()._row_looks_like_guide(row):
        # The document IS a guide — link to the interactive form-guide page if available
        form_number = _ui()._extract_citation_profile_form_number(
            citation.get("reference_key"),
            citation.get("source_label"),
            citation.get("legal_reference"),
            row.get("relative_path"),
            row.get("notes"),
        )
        guide_reference_key = f"formulario:{form_number}" if form_number else ""
        guide_package = resolve_guide(guide_reference_key, root=_ui().FORM_GUIDES_ROOT) if guide_reference_key else None
        if guide_package is not None:
            guide_url = f"/form-guide?reference_key={quote(guide_reference_key, safe='')}"
            return {
                "label": "Ver guía interactiva",
                "state": "available",
                "url": guide_url,
                "helper_text": None,
            }
        return {"label": label, "state": "not_applicable", "url": None, "helper_text": None}

    requested_key = str(citation.get("reference_key", "")).strip()
    form_number = _ui()._extract_citation_profile_form_number(
        citation.get("reference_key"),
        citation.get("source_label"),
        citation.get("legal_reference"),
        row.get("relative_path"),
        row.get("notes"),
    )
    guide_reference_key = f"formulario:{form_number}" if form_number else requested_key
    direct_package = resolve_guide(guide_reference_key, root=_ui().FORM_GUIDES_ROOT) if guide_reference_key else None
    if direct_package is not None:
        guide_url = f"/form-guide?reference_key={quote(guide_reference_key, safe='')}"
        return {
            "label": label,
            "state": "available",
            "url": guide_url,
            "helper_text": None,
        }
    return {
        "label": label,
        "state": "not_applicable",
        "url": None,
        "helper_text": None,
    }


def _resolve_analysis_action(context: dict[str, Any]) -> dict[str, Any]:
    profile_payload = dict(context.get("document_profile") or {})
    ui_surface = str(profile_payload.get("ui_surface") or "").strip().lower()
    family = str(context.get("document_family") or "").strip().lower()
    if not ui_surface:
        ui_surface = "form_guide" if family == "formulario" else "deep_analysis"
    doc_id = str(context.get("doc_id") or "").strip()
    if not doc_id or ui_surface != "deep_analysis":
        return {
            "label": "Abrir análisis normativo",
            "state": "not_applicable",
            "url": None,
            "helper_text": None,
        }
    params = {"doc_id": doc_id}
    citation = dict(context.get("citation") or {})
    for field in ("locator_text", "locator_kind", "locator_start", "locator_end"):
        value = str(citation.get(field) or "").strip()
        if value:
            params[field] = value
    return {
        "label": "Abrir análisis normativo",
        "state": "available",
        "url": f"/normative-analysis?{urlencode(params)}",
        "helper_text": None,
    }


_decreto_official_urls: dict[str, str] | None = None


def _load_decreto_official_urls() -> dict[str, str]:
    """Load decreto number:year -> official URL mapping, caching after first read."""
    global _decreto_official_urls
    if _decreto_official_urls is not None:
        return _decreto_official_urls
    cfg_path = Path(__file__).resolve().parents[2] / "config" / "decreto_official_urls.json"
    if cfg_path.exists():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            _decreto_official_urls = {k: v for k, v in raw.items() if not k.startswith("_")}
        except Exception:
            _decreto_official_urls = {}
    else:
        _decreto_official_urls = {}
    return _decreto_official_urls


def _lookup_decreto_official_url(context: dict[str, Any]) -> str:
    """Look up the official Función Pública URL for a decreto-family document.

    Returns an empty string if the decree number+year cannot be extracted
    or no mapping exists in config/decreto_official_urls.json.
    """
    citation = dict(context.get("citation") or {})
    ref_key = str(citation.get("reference_key") or "").strip().lower()
    m = re.match(r"^decreto:(\d+):(\d{4})$", ref_key)
    if not m:
        doc_id = str(context.get("doc_id") or citation.get("doc_id") or "").strip().lower()
        m = re.search(r"decreto_0*(\d+)_(\d{4})", doc_id)
    if not m:
        return ""
    number, year = m.group(1).lstrip("0") or "0", m.group(2)
    return _load_decreto_official_urls().get(f"{number}:{year}", "")


def _synthesize_ley_official_url(context: dict[str, Any]) -> str:
    """Construct a Secretaría del Senado URL for ley-family documents.

    Returns an empty string if the reference_key or doc_id doesn't contain
    enough info to build a reliable URL.  Pattern:
    https://www.secretariasenado.gov.co/senado/basedoc/ley_NUMBER_YEAR.html
    """
    citation = dict(context.get("citation") or {})
    ref_key = str(citation.get("reference_key") or "").strip().lower()
    # Try reference_key first (ley:NUMBER:YEAR)
    m = re.match(r"^ley:(\d+):(\d{4})$", ref_key)
    if not m:
        # Fallback: extract from doc_id (e.g. …ley_1819_2016…)
        doc_id = str(context.get("doc_id") or citation.get("doc_id") or "").strip().lower()
        m = re.search(r"ley_(\d+)_(\d{4})", doc_id)
    if not m:
        return ""
    number, year = m.group(1), m.group(2)
    # Secretaría del Senado zero-pads law numbers shorter than 4 digits
    padded = number.zfill(4)
    return f"https://www.secretariasenado.gov.co/senado/basedoc/ley_{padded}_{year}.html"


def _resolve_source_action(context: dict[str, Any]) -> dict[str, Any]:
    citation = dict(context.get("citation") or {})
    family = str(context.get("document_family") or "").strip().lower()
    official_url = _ui()._coerce_http_url(citation.get("official_url"))
    # Prefer MinTIC mirror for DIAN Normograma URLs: the DIAN host does not
    # honor article fragment anchors like #807 on the compiled ET page, but
    # the MinTIC mirror at normograma.mintic.gov.co/mintic/compilacion/docs
    # hosts identical content with working anchors. No-op for non-Normograma
    # URLs. See docs/next/retriever_plusv5.md Part E·3 for context.
    if official_url:
        official_url = _ui()._prefer_normograma_mintic_mirror(official_url)
    # For ET articles, ensure the fragment anchor matches the locator_start
    # (the specific article being viewed). The official_url in the citation
    # may carry a stale or missing anchor when material resolution or data
    # propagation resolved to a different row's URL.
    if official_url and _ui()._citation_targets_et_article(citation):
        _locator = _ui()._citation_et_locator_label(citation)
        if _locator:
            official_url = official_url.split("#")[0] + f"#{_locator}"
    # For ley-family documents without an official_url in the corpus,
    # synthesize one from the reference_key / doc_id pointing to the
    # Secretaría del Senado (the legislature's canonical repository).
    if not official_url and family == "ley":
        official_url = _synthesize_ley_official_url(context)
    if not official_url and family == "decreto":
        official_url = _lookup_decreto_official_url(context)
    download_original_url = _ui()._sanitize_url_candidate(str(citation.get("download_original_url") or "").strip())
    download_url = _ui()._sanitize_url_candidate(str(citation.get("download_url") or "").strip())

    if family == "ley":
        label = "Ver ley original"
    elif family == "decreto":
        label = "Ver decreto original"
    else:
        label = _CITATION_PROFILE_ORIGINAL_LABEL

    if official_url:
        return {
            "label": label,
            "url": official_url,
            "mode": "official_link",
            "helper_text": None,
        }
    if download_original_url:
        return {
            "label": label,
            "url": download_original_url,
            "mode": "original_download",
            "helper_text": _CITATION_PROFILE_ORIGINAL_DOWNLOAD_HELPER,
        }
    return {
        "label": label,
        "url": download_url,
        "mode": "normalized_pdf_fallback",
        "helper_text": _CITATION_PROFILE_ORIGINAL_FALLBACK_HELPER if download_url else None,
    }


def _build_citation_profile_lead(context: dict[str, Any], llm_payload: dict[str, str] | None = None) -> str:
    payload = dict(llm_payload or {})
    family = str(context.get("document_family") or "generic").strip()
    title = _ui()._normalize_citation_profile_text(context.get("title"), max_chars=140) or "El documento seleccionado"
    citation = dict(context.get("citation") or {})
    # For ET articles, prefer the deterministic lead (based on locator
    # resolution) over the LLM lead.  The LLM prompt receives `material`
    # text which may come from a different ET row due to provenance-URI
    # collisions, producing a lead about the wrong article.  The locator
    # analysis resolves by doc_id + locator_start and always finds the
    # correct article text.
    if _ui()._citation_targets_et_article(citation):
        analysis = _ui()._resolve_et_locator_analysis(context)
        raw_text = str((analysis or {}).get("raw_text") or "")
        metadata = _ui()._extract_et_article_metadata(raw_text) if analysis else {}
        article_display = str(metadata.get("article_number_display") or _ui()._citation_et_locator_label(citation)).strip()
        summary_text = _ui()._extract_et_article_summary(raw_text) if raw_text else ""
        if article_display:
            if summary_text:
                clean_summary = summary_text.strip().rstrip(".")
                if clean_summary:
                    normalized_summary = (
                        f"{clean_summary[:1].lower()}{clean_summary[1:]}"
                        if clean_summary[:1].isupper()
                        else clean_summary
                    )
                    return f"El Artículo {article_display} del Estatuto Tributario establece que {normalized_summary}."
            return f"El Artículo {article_display} del Estatuto Tributario es la referencia normativa consultada."

    lead = _ui()._normalize_citation_profile_text(payload.get("lead"), max_chars=320)
    if lead:
        return lead
    # For decreto/ley/resolucion: try extracting the "resumen tecnico" summary
    # from the RAG-ready markdown, which is a curated one-liner about
    # what the document does — much better than generic sentence grounding.
    if family in {"decreto", "ley", "resolucion"}:
        raw_text = str(context.get("requested_raw_text") or "") or str((context.get("material") or {}).get("raw_text") or "")
        if raw_text:
            section_map = _ui()._markdown_section_map(raw_text)
            resumen = (
                section_map.get("texto base referenciado (resumen tecnico)")
                or section_map.get("texto base referenciado (resumen técnico)")
                or ""
            )
            if resumen and "scaffold debe evolucionar" not in resumen.lower():
                # Extract a clean summary sentence from the resumen section
                resumen_lead = _ui()._find_grounded_profile_sentence(
                    [resumen],
                    keywords=("establece", "reglamenta", "modifica", "fija", "plazos", "obligación", "obligacion", "define"),
                    max_chars=320,
                )
                if resumen_lead:
                    return resumen_lead

    texts = _ui()._collect_citation_profile_texts(context)
    keywords_by_family = {
        "formulario": ("sirve", "utiliza", "diligenciar", "presentar", "declaración", "declaracion", "formulario"),
        "constitucion": ("constitución", "constitucion", "principio", "garantiza", "reserva", "debido proceso"),
        "ley": ("regula", "establece", "define", "dispone", "objeto"),
        "decreto": ("regula", "establece", "define", "dispone", "objeto"),
        "resolucion": ("establece", "define", "regula", "fija", "dispone"),
        "et_dur": ("regula", "establece", "define", "compila", "dispone"),
        "concepto": ("criterio", "aclara", "precisa", "interpreta", "indica"),
        "circular": ("lineamiento", "instruye", "indica", "establece"),
        "jurisprudencia": ("problema", "controversia", "resolv", "decid", "analiza"),
        "generic": ("establece", "define", "explica", "sirve"),
    }
    grounded = _ui()._find_grounded_profile_sentence(texts, keywords=keywords_by_family.get(family, ("establece", "sirve")))
    if grounded:
        return grounded

    fallback_by_family = {
        "formulario": f"{title} es el formulario seleccionado para esta consulta tributaria.",
        "constitucion": f"{title} es la referencia constitucional seleccionada para revisar el marco superior aplicable.",
        "ley": f"{title} es la ley seleccionada para revisar el marco aplicable a esta consulta.",
        "decreto": f"{title} es el decreto seleccionado para revisar el marco aplicable a esta consulta.",
        "resolucion": f"{title} es la resolución seleccionada para revisar el marco aplicable a esta consulta.",
        "et_dur": f"{title} es la referencia normativa seleccionada para revisar el marco aplicable a esta consulta.",
        "concepto": f"{title} es el criterio administrativo seleccionado para esta consulta.",
        "circular": f"{title} es la circular seleccionada como soporte para esta consulta.",
        "jurisprudencia": f"{title} es la decisión judicial seleccionada como soporte.",
        "generic": f"{title} es el documento seleccionado como soporte de esta consulta.",
    }
    return fallback_by_family.get(family, fallback_by_family["generic"])


def _citation_profile_display_title(context: dict[str, Any]) -> str:
    citation = dict(context.get("citation") or {})
    citation_title = _ui()._normalize_citation_profile_text(
        citation.get("legal_reference") or citation.get("source_label") or context.get("title"),
        max_chars=180,
    )
    context_title = _ui()._normalize_citation_profile_text(context.get("title"), max_chars=180)
    base_title = citation_title
    if context_title and _ui()._is_broad_normative_reference_title(citation_title):
        base_title = context_title
    locator_text = _ui()._normalize_citation_profile_text(citation.get("locator_text"), max_chars=80)
    if base_title and locator_text and locator_text.lower() not in base_title.lower():
        return f"{base_title}, {locator_text}"
    if base_title:
        return base_title
    # Fallback: extract "Tema principal" from expert document body text
    expert_meta = _extract_expert_body_metadata(context)
    tema = expert_meta.get("tema_principal", "").strip()
    if tema:
        return tema[:180] if len(tema) > 180 else tema
    # Last resort: humanize the technical context title
    raw_title = str(context.get("title") or "").strip()
    if raw_title:
        humanized = _ui()._humanize_technical_title(raw_title)
        if humanized:
            return humanized
    return "Documento"


def _citation_locator_reference_keys(citation: dict[str, Any]) -> tuple[str, ...]:
    reference_key = str(citation.get("reference_key") or "").strip().lower()
    locator_start = str(citation.get("locator_start") or "").strip().lower()
    if reference_key.startswith("ley:"):
        return (reference_key,)
    if reference_key != "et" or not locator_start:
        return ()

    variants: list[str] = []
    canonical = re.sub(r"[_\-.]+", "_", locator_start).strip("_")
    for candidate in (
        f"et_art_{canonical}",
        f"et_art_{locator_start}",
        f"et_art_{locator_start.replace('-', '.')}",
    ):
        clean = candidate.strip()
        if clean and clean not in variants:
            variants.append(clean)
    return tuple(variants)


def _citation_profile_analysis_candidates(context: dict[str, Any]) -> list[dict[str, Any]]:
    material = dict(context.get("material") or {})
    requested_row = dict(context.get("requested_row") or {})
    resolved_row = dict(context.get("resolved_row") or {})
    candidates = list(context.get("related_analyses") or [])
    if material:
        candidates.append(
            {
                "row": dict(material.get("resolved_row") or resolved_row or requested_row),
                "doc_id": str(context.get("doc_id") or "").strip(),
                "raw_text": str(material.get("raw_text") or ""),
                "public_text": str(material.get("public_text") or ""),
                "usable_text": str(material.get("usable_text") or ""),
                "rank": (1 if str(material.get("usable_text") or "").strip() else 0, len(str(material.get("usable_text") or "")), 0, 0),
            }
        )

    def _sort_key(item: dict[str, Any]) -> tuple[int, int, int, int]:
        rank = item.get("rank") or (0, 0, 0, 0)
        return (
            int(rank[0]),
            int(rank[1]),
            int(rank[2]),
            int(rank[3]),
        )

    return sorted(
        [dict(item) for item in candidates if isinstance(item, dict)],
        key=_sort_key,
        reverse=True,
    )


def _extract_locator_excerpt_from_text(text: str, *, citation: dict[str, Any], max_chars: int = 360) -> str:
    clean_text = re.sub(r"\s+", " ", _ui()._clean_markdown_inline(str(text or ""))).strip()
    locator_start = str(citation.get("locator_start") or "").strip()
    if not clean_text or not locator_start:
        return ""

    reference_key = str(citation.get("reference_key") or "").strip().lower()
    if reference_key != "et":
        return ""

    pattern = re.compile(rf"\bart[íi]culo(?:s)?\s+{re.escape(locator_start)}\b", re.IGNORECASE)
    match = pattern.search(clean_text)
    if match is None:
        pattern = re.compile(rf"\b{re.escape(locator_start)}\.\s", re.IGNORECASE)
        match = pattern.search(clean_text)
    if match is None:
        return ""

    snippet = clean_text[match.start(): match.start() + max_chars].strip(" -:;,.")
    sentences = _ui()._split_sentences(snippet)
    if sentences:
        return _ui()._clip_session_content(" ".join(sentences[:2]), max_chars=max_chars)
    return _ui()._clip_session_content(snippet, max_chars=max_chars)


def _summarize_analysis_excerpt(
    analysis: dict[str, Any],
    *,
    question_context: str,
    citation_context: str,
    max_chars: int = 360,
) -> str:
    usable_text = str(analysis.get("usable_text") or analysis.get("public_text") or "").strip()
    if not usable_text:
        return ""

    query_profile = _ui()._build_source_query_profile(
        question_context=question_context,
        citation_context=citation_context,
    )
    chunks = _ui()._extract_source_chunks(usable_text, max_items=10)
    if not chunks:
        paragraphs = _ui()._extract_candidate_paragraphs(usable_text, max_items=4)
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
            for paragraph in paragraphs
        ]
    if not chunks:
        return ""

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
    selected = _ui()._select_diverse_chunks(scored_rows=scored_rows, chunks=chunks, max_items=2)
    sentences = _ui()._pick_summary_sentences(selected, query_profile=query_profile, max_items=2)
    if sentences:
        return _ui()._clip_session_content(" ".join(sentences), max_chars=max_chars)
    return _ui()._clip_session_content(str(selected[0].get("text") or "").strip(), max_chars=max_chars) if selected else ""


def _build_citation_profile_original_text_section(context: dict[str, Any]) -> dict[str, str] | None:
    citation = dict(context.get("citation") or {})
    if _ui()._citation_targets_et_article(citation):
        analysis = _ui()._resolve_et_locator_analysis(context)
        quote = ""
        source_url = ""
        if analysis is not None:
            quote = _ui()._extract_et_article_quote_from_markdown(
                str(analysis.get("raw_text") or ""),
                citation=citation,
            )
            metadata = _ui()._extract_et_article_metadata(str(analysis.get("raw_text") or ""))
            source_url = str(metadata.get("source_url_text") or metadata.get("source_url") or "").strip()
        body = (
            quote
            if quote
            else "No se encontró texto original verificable para este artículo."
        )
        payload = {
            "id": "texto_original_relevante",
            "title": "Texto Vigente del Artículo",
            "body": body,
        }
        if source_url:
            payload["source_url"] = source_url
        payload["evidence_status"] = "verified" if quote else "missing"
        return payload

    question_context = _ui()._sanitize_question_context(str(context.get("message_context") or ""), max_chars=320)
    citation_context = _ui()._citation_profile_display_title(context)

    for analysis in _ui()._citation_profile_analysis_candidates(context):
        excerpt = _ui()._extract_locator_excerpt_from_text(
            str(analysis.get("usable_text") or analysis.get("public_text") or analysis.get("raw_text") or ""),
            citation=citation,
        )
        if not excerpt:
            excerpt = _ui()._summarize_analysis_excerpt(
                analysis,
                question_context=question_context,
                citation_context=citation_context,
            )
        clean_excerpt = _ui()._normalize_citation_profile_text(excerpt, max_chars=360)
        if clean_excerpt:
            # For non-ET documents this body is always a summary produced by
            # `_summarize_analysis_excerpt` (the verbatim-quote branch in
            # `_extract_locator_excerpt_from_text` short-circuits unless
            # reference_key == "et"). Label it honestly so the modal does not
            # claim it is the original text of the law/decree.
            return {
                "id": "texto_original_relevante",
                "title": "Resumen del pasaje relevante",
                "body": clean_excerpt,
            }
    return None


def _build_citation_profile_expert_section(context: dict[str, Any]) -> dict[str, str] | None:
    citation = dict(context.get("citation") or {})
    rows_by_doc_id = dict(context.get("rows_by_doc_id") or {})
    question_context = _ui()._sanitize_question_context(str(context.get("message_context") or ""), max_chars=320)
    citation_context = _ui()._citation_profile_display_title(context)
    specific_keys = set(_ui()._citation_locator_reference_keys(citation))
    base_key = str(citation.get("reference_key") or "").strip().lower()

    if _ui()._citation_targets_et_article(citation):
        best_payload: tuple[float, dict[str, str]] | None = None
        for row in rows_by_doc_id.values():
            if not isinstance(row, dict) or not _ui()._row_is_active_or_canonical(row):
                continue
            if str(row.get("knowledge_class") or "").strip().lower() != "interpretative_guidance":
                continue

            row_keys = {
                str(item).strip().lower()
                for item in list(row.get("normative_refs") or []) + list(row.get("mentioned_reference_keys") or [])
                if str(item).strip()
            }
            if specific_keys and not specific_keys.intersection(row_keys):
                continue

            analysis = _ui()._build_source_view_candidate_analysis(row, view="normalized")
            raw_text = str(analysis.get("raw_text") or "")
            chunks = _ui()._expert_chunk_candidates(raw_text)
            if not chunks:
                continue

            best_chunk = ""
            best_score = -1.0
            for chunk_text in chunks:
                if not _ui()._expert_chunk_matches_article(chunk_text, citation=citation):
                    continue
                if not _ui()._expert_chunk_matches_topic(chunk_text, question_context=question_context, row=row):
                    continue

                query_profile = _ui()._build_source_query_profile(
                    question_context=question_context,
                    citation_context=f"{citation_context} {' '.join(sorted(specific_keys))}".strip(),
                )
                chunk_payload = {
                    "heading": "",
                    "text": chunk_text,
                    "intent_tags": [],
                    "is_exercise_chunk": False,
                    "has_money_example": False,
                    "is_reference_dense": False,
                    "signature": chunk_text.lower()[:140],
                }
                score = float(_ui()._score_chunk_relevance(chunk_payload, query_profile=query_profile).get("score", 0.0))
                if score > best_score:
                    best_score = score
                    best_chunk = chunk_text

            if not best_chunk:
                continue

            clean_excerpt = _ui()._normalize_citation_profile_text(best_chunk, max_chars=520)
            if not clean_excerpt:
                continue
            source_title = _ui()._resolve_source_display_title(
                row=dict(row),
                doc_id=str(row.get("doc_id") or "").strip(),
                raw_text=raw_text,
                public_text=str(analysis.get("public_text") or ""),
            )
            source_url = _ui()._sanitize_url_candidate(str(row.get("url") or "").strip())
            payload = {
                "id": "comentario_experto_relevante",
                "title": "Comentario experto relevante",
                "topic_label": _ui()._derive_expert_topic_label(best_chunk, row=row, question_context=question_context),
                "body": clean_excerpt,
                "source_label": source_title,
                "evidence_status": "verified",
                "accordion_default": "closed",
            }
            if source_url:
                payload["source_url"] = source_url
            total_score = 10.0 + max(best_score, 0.0)
            if best_payload is None or total_score > best_payload[0]:
                best_payload = (total_score, payload)

        if best_payload is not None:
            return dict(best_payload[1])
        return {
            "id": "comentario_experto_relevante",
            "title": "Comentario experto relevante",
            "topic_label": "No se encontró",
            "body": "No se encontró comentario experto directamente relacionado con el artículo consultado.",
            "evidence_status": "missing",
            "accordion_default": "closed",
        }

    # Ley-specific: match companions by logical_doc_id prefix (more robust than
    # reference key matching for Kanban-ingested documents)
    if _ui()._citation_targets_ley(citation):
        ley_logical_id = str(context.get("logical_doc_id") or "").strip()
        if ley_logical_id:
            for row in rows_by_doc_id.values():
                if not isinstance(row, dict) or not _ui()._row_is_active_or_canonical(row):
                    continue
                if str(row.get("knowledge_class") or "").strip().lower() != "interpretative_guidance":
                    continue
                row_doc_id = str(row.get("doc_id") or "").strip()
                row_logical = _ui()._logical_doc_id(row_doc_id)
                if row_logical != ley_logical_id and not row_doc_id.startswith(f"{ley_logical_id}_"):
                    continue
                analysis = _ui()._build_source_view_candidate_analysis(row, view="normalized")
                expert_excerpt = _ui()._summarize_analysis_excerpt(
                    analysis,
                    question_context=question_context,
                    citation_context=citation_context,
                )
                clean_excerpt = _ui()._normalize_citation_profile_text(expert_excerpt, max_chars=520)
                if not clean_excerpt:
                    continue
                source_title = _ui()._resolve_source_display_title(
                    row=dict(row),
                    doc_id=row_doc_id,
                    raw_text=str(analysis.get("raw_text") or ""),
                    public_text=str(analysis.get("public_text") or ""),
                )
                source_url = _ui()._sanitize_url_candidate(str(row.get("url") or "").strip())
                payload = {
                    "id": "comentario_experto_relevante",
                    "title": "Comentario experto relevante",
                    "topic_label": _ui()._derive_expert_topic_label(clean_excerpt, row=row, question_context=question_context),
                    "body": clean_excerpt,
                    "source_label": source_title,
                    "evidence_status": "verified",
                    "accordion_default": "open",
                }
                if source_url:
                    payload["source_url"] = source_url
                return payload

    best_payload: tuple[float, dict[str, str]] | None = None
    for row in rows_by_doc_id.values():
        if not isinstance(row, dict) or not _ui()._row_is_active_or_canonical(row):
            continue
        if str(row.get("knowledge_class") or "").strip().lower() != "interpretative_guidance":
            continue

        row_keys = {
            str(item).strip().lower()
            for item in list(row.get("normative_refs") or []) + list(row.get("mentioned_reference_keys") or [])
            if str(item).strip()
        }
        has_specific_match = bool(specific_keys.intersection(row_keys))
        if specific_keys and not has_specific_match:
            continue
        if not specific_keys and base_key and base_key not in row_keys:
            continue

        analysis = _ui()._build_source_view_candidate_analysis(row, view="normalized")
        expert_excerpt = _ui()._extract_locator_excerpt_from_text(
            str(analysis.get("usable_text") or analysis.get("public_text") or ""),
            citation=citation,
        )
        if not expert_excerpt:
            expert_excerpt = _ui()._summarize_analysis_excerpt(
                analysis,
                question_context=question_context,
                citation_context=f"{citation_context} {' '.join(sorted(specific_keys))}".strip(),
            )
        clean_excerpt = _ui()._normalize_citation_profile_text(expert_excerpt, max_chars=320)
        if not clean_excerpt:
            continue

        source_title = _ui()._resolve_source_display_title(
            row=dict(row),
            doc_id=str(row.get("doc_id") or "").strip(),
            raw_text=str(analysis.get("raw_text") or ""),
            public_text=str(analysis.get("public_text") or ""),
        )
        body = _ui()._normalize_citation_profile_text(f"{source_title}: {clean_excerpt}", max_chars=360)
        if not body:
            continue

        score = 10.0 if has_specific_match else 2.0
        if question_context:
            query_profile = _ui()._build_source_query_profile(
                question_context=question_context,
                citation_context=citation_context,
            )
            chunks = _ui()._extract_source_chunks(str(analysis.get("usable_text") or ""), max_items=8)
            if chunks:
                scored = max(
                    float(_ui()._score_chunk_relevance(chunk, query_profile=query_profile).get("score", 0.0))
                    for chunk in chunks
                )
                score += scored

        payload = {
            "id": "comentario_experto_relevante",
            "title": "Comentario experto relevante",
            "body": body,
        }
        if best_payload is None or score > best_payload[0]:
            best_payload = (score, payload)

    return dict(best_payload[1]) if best_payload is not None else None


def _build_citation_profile_sections(context: dict[str, Any], llm_payload: dict[str, str] | None = None) -> list[dict[str, str]]:
    payload = dict(llm_payload or {})
    explicit_sections = payload.get("sections_payload")
    if isinstance(explicit_sections, list):
        resolved: list[dict[str, str]] = []
        for item in explicit_sections:
            if not isinstance(item, dict):
                continue
            title = _ui()._normalize_citation_profile_text(item.get("title"), max_chars=120)
            body = str(item.get("body") or "").strip()
            body = re.sub(r"\n{3,}", "\n\n", body)
            if not title or not body:
                continue
            resolved.append(
                {
                    "id": str(item.get("id") or "").strip() or "normativa_section",
                    "title": title,
                    "body": body,
                }
            )
        if resolved:
            return resolved
    family = str(context.get("document_family") or "generic").strip()
    texts = _ui()._collect_citation_profile_texts(context)
    title_by_family = {
        "formulario": "Implicaciones para el contador",
        "constitucion": "Implicaciones para el contador",
        "ley": "Implicaciones para el contador",
        "decreto": "Implicaciones para el contador",
        "resolucion": "Implicaciones para el contador",
        "et_dur": "Implicaciones para el contador",
        "concepto": "Implicaciones para el contador",
        "circular": "Implicaciones para el contador",
        "jurisprudencia": "Implicaciones para el contador",
    }
    section_title = title_by_family.get(family, "")
    if not section_title:
        return []

    body = payload.get("professional_impact") or _ui()._find_grounded_profile_sentence(
        texts,
        keywords=("contador", "contable", "declaración", "declaracion", "presentación", "presentacion", "soporte", "registro"),
        max_chars=320,
    )
    clean_body = _ui()._normalize_citation_profile_text(body, max_chars=320)
    sections: list[dict[str, str]] = []
    if clean_body:
        sections.append({"id": "impacto_profesional", "title": section_title, "body": clean_body})

    original_section = _ui()._build_citation_profile_original_text_section(context)
    if original_section is not None:
        sections.insert(0, original_section)

    expert_section = _ui()._build_citation_profile_expert_section(context)
    if expert_section is not None:
        sections.append(expert_section)
    return sections


def _build_structured_original_text(context: dict[str, Any]) -> dict[str, Any] | None:
    citation = dict(context.get("citation") or {})
    if not _ui()._citation_targets_et_article(citation) and not _ui()._citation_targets_ley(citation):
        return None
    section = _ui()._build_citation_profile_original_text_section(context)
    if section is None:
        return None
    raw_body = str(section.get("body") or "").strip()
    body_text, annotations = _split_article_annotations(raw_body)
    quote = body_text.strip() if body_text else raw_body
    return {
        "title": "Texto Normativo",
        "quote": quote,
        "annotations": annotations,
        "source_url": str(section.get("source_url") or "").strip() or None,
        "evidence_status": str(section.get("evidence_status") or "missing").strip() or "missing",
    }


def _build_structured_vigencia_detail(context: dict[str, Any]) -> dict[str, Any] | None:
    citation = dict(context.get("citation") or {})
    if _ui()._citation_targets_et_article(citation):
        detail = _ui()._build_et_article_vigencia_detail(context)
        return {
            "label": str(detail.get("label") or "Vigencia específica").strip(),
            "basis": str(detail.get("basis") or "").strip(),
            "notes": str(detail.get("notes") or "").strip(),
            "last_verified_date": str(detail.get("last_verified_date") or "").strip(),
            "evidence_status": str(detail.get("evidence_status") or "missing").strip() or "missing",
        }
    if _ui()._citation_targets_ley(citation):
        return None
    return None


def _build_structured_expert_comment(context: dict[str, Any]) -> dict[str, Any] | None:
    citation = dict(context.get("citation") or {})
    if not _ui()._citation_targets_et_article(citation) and not _ui()._citation_targets_ley(citation):
        return None
    section = _ui()._build_citation_profile_expert_section(context)
    if section is None:
        return None
    return {
        "topic_label": str(section.get("topic_label") or section.get("source_label") or section.get("title") or "").strip(),
        "body": str(section.get("body") or "").strip(),
        "source_label": str(section.get("source_label") or "").strip() or None,
        "source_url": str(section.get("source_url") or "").strip() or None,
        "accordion_default": str(section.get("accordion_default") or "closed").strip() or "closed",
        "evidence_status": str(section.get("evidence_status") or "missing").strip() or "missing",
    }


def _apply_citation_profile_request_context(
    context: dict[str, Any],
    *,
    message_context: str = "",
    locator_text: str = "",
    locator_kind: str = "",
    locator_start: str = "",
    locator_end: str = "",
) -> dict[str, Any]:
    updated = dict(context)
    citation = dict(updated.get("citation") or {})
    reference_detail = {
        "reference_text": _ui()._reference_base_text_for_request_context(citation),
        "locator_text": locator_text,
        "locator_kind": locator_kind,
        "locator_start": locator_start,
        "locator_end": locator_end,
    }
    if any(str(reference_detail.get(field) or "").strip() for field in ("locator_text", "locator_kind", "locator_start", "locator_end")):
        citation = _ui()._apply_reference_detail_to_citation(citation, reference_detail=reference_detail)
        updated["title"] = _ui()._citation_profile_display_title({"citation": citation, "title": updated.get("title")})
    updated["citation"] = citation
    updated["message_context"] = _ui()._sanitize_question_context(message_context, max_chars=320)
    return updated


def _render_citation_profile_payload(context: dict[str, Any], llm_payload: dict[str, str] | None = None) -> dict[str, Any]:
    document_profile = dict(context.get("document_profile") or {})
    if not document_profile:
        seed_citation = dict(context.get("citation") or {})
        if not str(seed_citation.get("reference_type") or "").strip():
            seed_citation["reference_type"] = str(context.get("document_family") or "").strip()
        document_profile = classify_normative_document(
            seed_citation,
            dict(context.get("requested_row") or {}),
        ).to_public_dict()

    deterministic_form = _ui()._deterministic_form_citation_profile(context)
    if deterministic_form is not None:
        lead = str(deterministic_form.get("lead") or "").strip()
        facts = list(deterministic_form.get("facts") or [])
        sections = list(deterministic_form.get("sections") or [])
        title = str(deterministic_form.get("title") or context.get("title") or "Documento").strip()
        supporting_source_ids = list(deterministic_form.get("supporting_source_ids") or [])
    else:
        lead = _ui()._build_citation_profile_lead(context, llm_payload=llm_payload)
        facts = _ui()._build_citation_profile_facts(context, llm_payload=llm_payload)
        sections = _ui()._build_citation_profile_sections(context, llm_payload=llm_payload)
        title = _ui()._citation_profile_display_title(context)
        supporting_source_ids = []
    original_text = _ui()._build_structured_original_text(context)
    vigencia_detail = _ui()._build_structured_vigencia_detail(context)
    expert_comment = _ui()._build_structured_expert_comment(context)
    additional_depth_sections = _ui()._build_structured_additional_depth_sections(context)
    return {
        "title": title,
        "document_family": str(context.get("document_family") or "generic").strip(),
        "family_subtype": str(document_profile.get("family_subtype") or "").strip(),
        "hierarchy_tier": str(document_profile.get("hierarchy_tier") or "").strip(),
        "binding_force": str(document_profile.get("binding_force") or "").strip(),
        "binding_force_rank": int(document_profile.get("binding_force_rank") or 0),
        "analysis_template_id": str(document_profile.get("analysis_template_id") or "").strip(),
        "ui_surface": str(document_profile.get("ui_surface") or "").strip(),
        "allowed_secondary_overlays": list(document_profile.get("allowed_secondary_overlays") or []),
        "lead": lead,
        "facts": facts,
        "sections": sections,
        "original_text": original_text,
        "vigencia_detail": vigencia_detail,
        "expert_comment": expert_comment,
        "additional_depth_sections": additional_depth_sections,
        "supporting_source_ids": supporting_source_ids or None,
        "caution_banner": dict(document_profile.get("caution_banner") or {}) or None,
        "analysis_action": _ui()._resolve_analysis_action(context),
        "companion_action": _ui()._resolve_companion_action(context),
        "source_action": _ui()._resolve_source_action(context),
    }
