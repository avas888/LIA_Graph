"""Context collection for the citation-profile modal.

Extracted from `ui_citation_profile_builders.py` during granularize-v2
round 12b. Two entry points:

  * ``_collect_citation_profile_context(doc_id)`` — primary collector:
    looks up the requested row (index + Supabase fallback), resolves
    source-view material (with chunk-reassembly fallback when
    ``absolute_path`` is NULL), walks the rows_by_doc_id catalog to
    gather companion/related rows (logical_doc_id + entity_id +
    reference_identity_keys), and returns the full context dict the
    downstream builders consume.
  * ``_collect_citation_profile_context_by_reference_key(key)`` —
    reference-first collector: if ``key`` resolves to a doc_id we
    delegate; otherwise (synthetic form-guide references like
    ``formulario:110``) we build a stub context from the form-guide
    manifest so the modal still renders.

Host re-imports both names for back-compat; the ui_server lazy
registry picks them up unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .citation_resolution import (
    CANONICAL_REFERENCE_RELATION_TYPES,
    document_reference_semantics,
)
from .form_guides import resolve_guide
from .normative_taxonomy import classify_normative_document


def _ui() -> Any:
    """Lazy accessor for `lia_graph.ui_server` (avoids circular import)."""
    from . import ui_server as _mod
    return _mod



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
