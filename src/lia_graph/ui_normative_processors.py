from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

# build_normative_analysis_payload accessed via _ui() so monkeypatch works

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
# Module-level constants (moved from ui_server during granularize-v1 1C)
# ---------------------------------------------------------------------------

_LEY_RELATED_MAX_PER_CATEGORY = 1

# These are defined in ui_server but their default value is computed at
# import time.  We replicate the WORKSPACE_ROOT derivation so the constant
# is self-contained — callers can override the path via function parameter.
_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
ET_ARTICLE_ADDITIONAL_DEPTH_PATH = _WORKSPACE_ROOT / "artifacts" / "runtime" / "et_article_additional_depth.json"
_ET_ARTICLE_ADDITIONAL_DEPTH_CACHE: dict[str, Any] = {"mtime_ns": None, "payload": {}}


# ---------------------------------------------------------------------------
# Normative processor functions (extracted from ui_server, Phase 1C)
# ---------------------------------------------------------------------------


def _is_broad_normative_reference_title(title: str) -> bool:
    normalized_title = _ui()._normalize_source_reference_text(title)
    if not normalized_title:
        return True
    if normalized_title in _ui()._GENERIC_SOURCE_TITLES:
        return True
    if re.fullmatch(r"estatuto tributario(?:\s*\(?suin\s*\d+\)?)?", normalized_title):
        return True
    if re.fullmatch(r"dur 1625(?:\s*\(?de\s*2016\)?)?", normalized_title):
        return True
    if re.fullmatch(r"decreto unico reglamentario 1625(?:\s*\(?de\s*2016\)?)?", normalized_title):
        return True
    return False


def _resolve_et_locator_row(context: dict[str, Any]) -> dict[str, Any] | None:
    citation = dict(context.get("citation") or {})
    if not _ui()._citation_targets_et_article(citation):
        return None

    row_doc_id = f"renta_corpus_a_et_art_{_ui()._citation_et_locator_key(citation)}"
    rows_by_doc_id = dict(context.get("rows_by_doc_id") or {})
    candidate = rows_by_doc_id.get(row_doc_id)
    if isinstance(candidate, dict) and _ui()._row_is_active_or_canonical(candidate):
        return dict(candidate)

    reference_keys = set(_ui()._citation_locator_reference_keys(citation))
    if not reference_keys:
        # Supabase fallback — rows_by_doc_id may be empty when JSONL index
        # is not deployed (e.g. Railway production).
        sb_row = _ui()._sb_find_document_row(row_doc_id)
        if isinstance(sb_row, dict) and _ui()._row_is_active_or_canonical(sb_row):
            return dict(sb_row)
        return None
    for row in rows_by_doc_id.values():
        if not isinstance(row, dict) or not _ui()._row_is_active_or_canonical(row):
            continue
        doc_id = str(row.get("doc_id") or "").strip()
        if doc_id == row_doc_id:
            return dict(row)
        row_refs = {
            str(item).strip().lower()
            for item in list(row.get("normative_refs") or []) + list(row.get("reference_identity_keys") or [])
            if str(item).strip()
        }
        if reference_keys.intersection(row_refs):
            return dict(row)

    # Supabase fallback — rows_by_doc_id may be empty when JSONL index
    # is not deployed (e.g. Railway production).
    sb_row = _ui()._sb_find_document_row(row_doc_id)
    if isinstance(sb_row, dict) and _ui()._row_is_active_or_canonical(sb_row):
        return dict(sb_row)
    return None


def _resolve_et_locator_analysis(context: dict[str, Any]) -> dict[str, Any] | None:
    row = _resolve_et_locator_row(context)
    if row is None:
        return None
    analysis = _ui()._build_source_view_candidate_analysis(row, view="normalized")
    # Supabase chunks fallback — in dev/staging/prod the `documents` row has
    # `absolute_path=None` because knowledge_base files only live on the
    # ingestion host. Reassemble the document markdown from `document_chunks`
    # so the modal body can extract the vigente article text.
    if not str(analysis.get("raw_text") or "").strip():
        doc_id = str(row.get("doc_id") or "").strip()
        if doc_id:
            sb_text = _ui()._sb_assemble_document_markdown(doc_id)
            if sb_text:
                analysis["raw_text"] = sb_text
    return analysis


def _article_heading_pattern(locator_start: str) -> re.Pattern[str]:
    clean = str(locator_start or "").strip()
    trailing_guard = r"(?![-_]\d)" if "-" not in clean else ""
    return re.compile(rf"\bart[íi]culo(?:s)?\s+{re.escape(clean)}{trailing_guard}\b", re.IGNORECASE)


def _extract_et_article_quote_from_markdown(
    markdown_text: str,
    *,
    citation: dict[str, Any],
    max_chars: int = 1100,
) -> str:
    locator_start = _ui()._citation_et_locator_label(citation)
    if not locator_start:
        return ""

    section_map = _ui()._markdown_section_map(markdown_text)
    normative_text = (
        section_map.get("texto normativo vigente")
        or section_map.get("texto normativo vigente.")
        or ""
    )
    if not normative_text:
        return ""

    if _ui()._is_source_view_noise_text(normative_text):
        return ""

    paragraphs: list[str] = []
    for block in re.split(r"\n{2,}", normative_text):
        clean = _ui()._clean_markdown_inline(block)
        clean = html.unescape(clean).replace("\xa0", " ")
        clean = re.sub(r"\s+", " ", clean).strip()
        if not clean:
            continue
        lowered = clean.lower()
        if lowered.startswith("*fuente original compilada:") or lowered.startswith("fuente original compilada:"):
            continue
        if any(token in lowered for token in ("<option", "</option>", "bookmarkaj", "javascript:insrow")):
            return ""
        if _ui()._is_source_view_noise_text(clean):
            continue
        paragraphs.append(clean)

    if not paragraphs:
        return ""

    heading_re = _article_heading_pattern(locator_start)
    start_index = -1
    for idx, paragraph in enumerate(paragraphs):
        if heading_re.search(paragraph):
            start_index = idx
            break
    if start_index < 0:
        start_index = 0

    selected: list[str] = []
    total_chars = 0
    if start_index == 0 and paragraphs and not heading_re.search(paragraphs[0]):
        metadata = _extract_et_article_metadata(markdown_text)
        article_number = str(metadata.get("article_number_display") or locator_start).strip()
        article_title = str(metadata.get("article_title") or "").strip()
        if article_number:
            heading_text = f"ARTICULO {article_number}."
            if article_title:
                heading_text = f"{heading_text} {article_title}."
            selected.append(heading_text)
            total_chars += len(heading_text)
    for paragraph in paragraphs[start_index:]:
        if selected and re.match(r"^ART[ÍI]CULO\s+\d", paragraph, re.IGNORECASE) and not heading_re.search(paragraph):
            break
        selected.append(paragraph)
        total_chars += len(paragraph)
        if total_chars >= max_chars:
            break

    if not selected:
        return ""
    quote = "\n\n".join(selected).strip()
    if len(quote) > max_chars:
        quote = _ui()._clip_session_content(quote, max_chars=max_chars)
    return quote


def _extract_et_article_metadata(markdown_text: str) -> dict[str, str]:
    section_map = _ui()._markdown_section_map(markdown_text)
    metadata: dict[str, str] = {}
    for section_name in ("identificacion", "identificación", "checklist de vigencia"):
        metadata.update(_ui()._extract_markdown_bullet_metadata(section_map.get(section_name, "")))
    return metadata


def _extract_et_article_summary(markdown_text: str) -> str:
    section_map = _ui()._markdown_section_map(markdown_text)
    summary_text = (
        section_map.get("texto base referenciado (resumen tecnico)")
        or section_map.get("texto base referenciado (resumen técnico)")
        or ""
    )
    clean_summary = _ui()._clean_markdown_inline(summary_text)
    clean_summary = html.unescape(clean_summary).replace("\xa0", " ")
    clean_summary = re.sub(r"\s+", " ", clean_summary).strip()
    if not clean_summary:
        return ""
    sentences = _ui()._split_sentences(clean_summary)
    if sentences:
        return sentences[0].strip()
    return clean_summary


def _build_et_article_vigencia_detail(context: dict[str, Any]) -> dict[str, str]:
    citation = dict(context.get("citation") or {})
    locator_label = _ui()._citation_et_locator_label(citation)
    missing = {
        "label": "Vigencia específica",
        "basis": "",
        "notes": "Vigencia específica no disponible en corpus.",
        "last_verified_date": "",
        "evidence_status": "missing",
    }
    analysis = _resolve_et_locator_analysis(context)
    if analysis is None:
        return missing

    metadata = _extract_et_article_metadata(str(analysis.get("raw_text") or ""))
    vigencia_status = str(metadata.get("vigencia_status") or "").strip()
    vigencia_basis = str(metadata.get("vigencia_basis") or "").strip()
    vigencia_notes = str(metadata.get("vigencia_notes") or "").strip()
    last_verified_date = str(metadata.get("last_verified_date") or "").strip()
    if not (vigencia_status and vigencia_basis and vigencia_notes and last_verified_date):
        return missing
    return {
        "label": vigencia_status or f"Texto vigente del Artículo {locator_label}",
        "basis": vigencia_basis,
        "notes": vigencia_notes,
        "last_verified_date": last_verified_date,
        "evidence_status": "verified",
    }


def _summarize_vigencia_llm(vigencia_detail: dict[str, str], article_label: str) -> str:
    label = str(vigencia_detail.get("label") or "").strip()
    basis = str(vigencia_detail.get("basis") or "").strip()
    notes = str(vigencia_detail.get("notes") or "").strip()
    last_verified = str(vigencia_detail.get("last_verified_date") or "").strip()
    evidence_status = str(vigencia_detail.get("evidence_status") or "").strip()
    if evidence_status != "verified" or not (label and (basis or notes)):
        return ""
    sentences = [
        f"El artículo {article_label or 'consultado'} aparece como {label.lower()}."
    ]
    if basis:
        sentences.append(f"La base reportada para esa lectura es: {basis}.")
    if notes:
        sentences.append(notes.rstrip(".") + ".")
    if last_verified:
        sentences.append(f"Última verificación registrada: {last_verified}.")
    return " ".join(sentences).strip()


def _load_et_article_additional_depth(
    path: Path = ET_ARTICLE_ADDITIONAL_DEPTH_PATH,
) -> dict[str, Any]:
    global _ET_ARTICLE_ADDITIONAL_DEPTH_CACHE
    try:
        stat = path.stat()
    except OSError:
        _ET_ARTICLE_ADDITIONAL_DEPTH_CACHE = {"mtime_ns": None, "payload": {}}
        return {}

    cached_mtime = _ET_ARTICLE_ADDITIONAL_DEPTH_CACHE.get("mtime_ns")
    if cached_mtime == stat.st_mtime_ns:
        payload = _ET_ARTICLE_ADDITIONAL_DEPTH_CACHE.get("payload")
        return dict(payload) if isinstance(payload, dict) else {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    _ET_ARTICLE_ADDITIONAL_DEPTH_CACHE = {"mtime_ns": stat.st_mtime_ns, "payload": payload}
    return dict(payload)


def _et_article_additional_depth_for_doc_id(doc_id: str) -> dict[str, Any]:
    clean_doc_id = str(doc_id or "").strip()
    if not clean_doc_id:
        return {}
    payload = _ui()._load_et_article_additional_depth()
    articles = payload.get("articles")
    if not isinstance(articles, dict):
        return {}
    entry = articles.get(clean_doc_id)
    return dict(entry) if isinstance(entry, dict) else {}


_ADDITIONAL_DEPTH_TITLE_MAP: dict[str, str] = {
    "Doctrina Concordante": "Doctrina que DIAN relaciona con éste ET",
}


def _resolve_et_additional_depth_sections(context: dict[str, Any]) -> list[dict[str, Any]]:
    row = _resolve_et_locator_row(context)
    if row is None:
        return []
    doc_id = str(row.get("doc_id") or "").strip()
    entry = _et_article_additional_depth_for_doc_id(doc_id)
    sections = entry.get("additional_sections")
    if not isinstance(sections, list):
        return []

    normalized: list[dict[str, Any]] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        raw_title = str(section.get("title") or "").strip()
        title = _ADDITIONAL_DEPTH_TITLE_MAP.get(raw_title, raw_title)
        raw_items = section.get("items")
        if not title or not isinstance(raw_items, list):
            continue
        items: list[dict[str, Any]] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            url = _ui()._coerce_http_url(item.get("url"))
            if not label:
                continue
            items.append(
                {
                    "label": label,
                    "url": url or None,
                    "kind": str(item.get("kind") or "").strip() or None,
                }
            )
        if items:
            normalized.append(
                {
                    "title": title,
                    "items": items,
                    "accordion_default": str(section.get("accordion_default") or "closed").strip() or "closed",
                }
            )
    prioritized_titles = {"Notas de Vigencia": 0}
    ordered_sections = list(enumerate(normalized))
    ordered_sections.sort(
        key=lambda pair: (
            prioritized_titles.get(str(pair[1].get("title") or "").strip(), 100),
            pair[0],
        )
    )
    return [section for _, section in ordered_sections]


_CATALOG_DOC_RE = re.compile(
    r"catalogo|catalog[_\-\s]|readme|\bindice\b|\bíndice\b|bloque[_\s]+\d"
    r"|rag[_\s]?ready|_ingest_|ingestion_rag",
    re.IGNORECASE,
)


def _resolve_ley_additional_depth_sections(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Find related resources for a ley across 3 knowledge classes.

    Returns a single section titled 'Contenido relacionado de posible utilidad'
    with up to 6 items (2 per category), ranked by normative-ref overlap.
    """
    citation = dict(context.get("citation") or {})
    rows_by_doc_id = dict(context.get("rows_by_doc_id") or {})
    cap = _LEY_RELATED_MAX_PER_CATEGORY

    # Collect reference keys for this ley
    ley_ref_keys: set[str] = set()
    for key in list(context.get("reference_identity_keys") or []) + list(context.get("mentioned_reference_keys") or []):
        k = str(key).strip().lower()
        if k:
            ley_ref_keys.add(k)
    for key in _ui()._citation_locator_reference_keys(citation):
        if key:
            ley_ref_keys.add(key)

    current_doc_id = str(citation.get("doc_id") or "").strip()

    # Buckets: (overlap_size, label, doc_id) per category
    normativa_hits: list[tuple[int, str, str]] = []
    practica_hits: list[tuple[int, str, str]] = []
    expertos_hits: list[tuple[int, str, str]] = []

    # Track practica groups for label cleaning
    practica_groups: dict[str, list[dict[str, Any]]] = {}

    for candidate in rows_by_doc_id.values():
        if not isinstance(candidate, dict) or not _ui()._row_is_active_or_canonical(candidate):
            continue
        candidate_doc_id = str(candidate.get("doc_id") or "").strip()
        if not candidate_doc_id or candidate_doc_id == current_doc_id:
            continue
        if str(candidate.get("curation_status") or "").strip().lower() == "raw":
            continue
        # Skip catalog/index/readme/structural documents — they overlap
        # with many norms but add no value as related content.
        _cand_text = " ".join(filter(None, [
            str(candidate.get("title") or ""),
            str(candidate.get("relative_path") or ""),
        ]))
        if _CATALOG_DOC_RE.search(candidate_doc_id) or _CATALOG_DOC_RE.search(_cand_text):
            continue

        knowledge_class = str(candidate.get("knowledge_class") or "").strip().lower()

        # Compute reference overlap (if we have ref keys)
        overlap_size = 0
        if ley_ref_keys:
            candidate_refs: set[str] = set()
            for item in (
                list(candidate.get("normative_refs") or [])
                + list(candidate.get("mentioned_reference_keys") or [])
            ):
                k = str(item).strip().lower()
                if k:
                    candidate_refs.add(k)
            overlap = ley_ref_keys.intersection(candidate_refs)
            overlap_size = len(overlap)
            if not overlap:
                continue

        if knowledge_class == "interpretative_guidance":
            label = _ui()._interpretive_display_label(candidate, candidate_doc_id)
        else:
            label = str(
                candidate.get("title")
                or candidate.get("source_label")
                or candidate.get("subtema")
                or candidate_doc_id
            ).strip()
            if not label:
                label = candidate_doc_id

        if knowledge_class == "normative_base":
            normativa_hits.append((overlap_size, label, candidate_doc_id))
        elif knowledge_class == "practica_erp":
            base_key = _ui()._DOC_PART_SUFFIX_RE.sub("", candidate_doc_id)
            if base_key not in practica_groups:
                practica_groups[base_key] = []
            practica_groups[base_key].append(candidate)
            practica_hits.append((overlap_size, label, candidate_doc_id))
        elif knowledge_class == "interpretative_guidance":
            expertos_hits.append((overlap_size, label, candidate_doc_id))

    # Sort by overlap descending, then label alphabetically
    normativa_hits.sort(key=lambda h: (-h[0], h[1]))
    practica_hits.sort(key=lambda h: (-h[0], h[1]))
    expertos_hits.sort(key=lambda h: (-h[0], h[1]))

    # Build items with dedup (doc-id base key + label similarity)
    def _to_items(hits: list[tuple[int, str, str]], kind: str) -> list[dict[str, Any]]:
        seen: set[str] = set()
        seen_labels: set[str] = set()
        items: list[dict[str, Any]] = []
        for _overlap, label, doc_id in hits:
            base_key = _ui()._DOC_PART_SUFFIX_RE.sub("", doc_id)
            if base_key in seen:
                continue
            seen.add(base_key)
            # Clean practica labels
            if kind == "practica_erp" and base_key in practica_groups:
                label = _ui()._best_practica_display_label(practica_groups[base_key])
            # Collapse entity-type variants (e.g. Personas Juridicas / Naturales)
            lbl_key = _label_dedup_key(label)
            if lbl_key in seen_labels:
                continue
            seen_labels.add(lbl_key)
            items.append({"label": _normalize_depth_item_label(label), "doc_id": doc_id, "kind": kind})
            if len(items) >= cap:
                break
        return items

    normativa_items = _to_items(normativa_hits, "normative_base")
    practica_items = _to_items(practica_hits, "practica_erp")
    expertos_items = _to_items(expertos_hits, "interpretative_guidance")

    # Fallback: if overlap yielded 0 practica but practica rows exist, take top 2 alphabetically
    if not practica_items and practica_groups:
        fallback: list[dict[str, Any]] = []
        seen_labels: set[str] = set()
        for _base_key, group_rows in sorted(practica_groups.items()):
            label = _ui()._best_practica_display_label(group_rows)
            label_key = label.lower().strip()
            if label_key in seen_labels:
                continue
            seen_labels.add(label_key)
            first_doc_id = str(group_rows[0].get("doc_id") or "").strip()
            fallback.append({"label": _normalize_depth_item_label(label), "doc_id": first_doc_id or None, "kind": "practica_erp"})
            if len(fallback) >= cap:
                break
        practica_items = fallback

    all_items = normativa_items + expertos_items + practica_items
    if not all_items:
        return []
    return [{
        "title": "Contenido relacionado de posible utilidad",
        "items": all_items,
        "accordion_default": "open",
    }]


def _render_normative_analysis_payload(context: dict[str, Any]) -> dict[str, Any]:
    citation_llm_payload = _ui()._llm_citation_profile_payload(context)
    preview_payload = _ui()._render_citation_profile_payload(context, llm_payload=citation_llm_payload)
    payload = _ui().build_normative_analysis_payload(
        context,
        preview_facts=list(preview_payload.get("facts") or []),
        source_action=dict(preview_payload.get("source_action") or {}) or None,
        companion_action=dict(preview_payload.get("companion_action") or {}) or None,
        runtime_config_path=str(_ui().LLM_RUNTIME_CONFIG_PATH),
    )
    # Merge cross-referenced content (decreto/resolucion) into related_documents
    # so the normative analysis page also surfaces practical guides.
    family = str(context.get("document_family") or "").strip()
    if family in {"decreto", "resolucion"}:
        depth_sections = _build_structured_additional_depth_sections(context)
        if depth_sections:
            existing_doc_ids = {
                str(doc.get("doc_id") or "").strip()
                for doc in list(payload.get("related_documents") or [])
            }
            related = list(payload.get("related_documents") or [])
            for section in depth_sections:
                for item in list(section.get("items") or []):
                    item_doc_id = str(item.get("doc_id") or "").strip()
                    if not item_doc_id or item_doc_id in existing_doc_ids:
                        continue
                    existing_doc_ids.add(item_doc_id)
                    kind = str(item.get("kind") or "").strip()
                    kind_label = {
                        "normative_base": "Norma relacionada",
                        "interpretative_guidance": "Contenido experto relacionado",
                        "practica_erp": "Guía práctica relacionada",
                    }.get(kind, "Contenido relacionado")
                    related.append({
                        "doc_id": item_doc_id,
                        "title": str(item.get("label") or "").strip(),
                        "document_family": kind,
                        "relation_type": "cross_reference",
                        "relation_label": kind_label,
                        "helper_text": "",
                        "url": f"/normative-analysis?doc_id={quote(item_doc_id, safe='')}",
                    })
                    if len(related) >= 8:
                        break
            payload["related_documents"] = related
    return payload


# ---------------------------------------------------------------------------
# Functions extracted from ui_server (Phase 1G)
# ---------------------------------------------------------------------------

_EXPERTOS_LEY_RE = re.compile(
    r"expertos[_ ](ley|decreto|resoluci[oó]n|concepto)[_ ](\d+)[_ ](\d{4})", re.IGNORECASE,
)
_DOCTRINA_DIAN_RE = re.compile(
    r"dian[_ ](concepto|oficio|resoluci[oó]n)[_ ](\d+)[_ ](\d{4})", re.IGNORECASE,
)


def _interpretive_display_label(candidate: dict[str, Any], fallback: str) -> str:
    """Build a human-readable label for an interpretative_guidance document.

    Falls back to *fallback* (usually the raw doc_id) only when no
    structured information can be extracted.
    """
    # 1. If the document already has a proper title, use it.
    title = str(candidate.get("title") or "").strip()
    if title:
        return title
    source_label = str(candidate.get("source_label") or "").strip()
    if source_label and not _EXPERTOS_LEY_RE.search(source_label) and not _DOCTRINA_DIAN_RE.search(source_label):
        return source_label

    # 2. Parse the subtema or doc_id for a structured norm reference.
    raw = str(candidate.get("subtema") or candidate.get("doc_id") or fallback).strip()
    providers = list(candidate.get("provider_labels") or [])
    provider_suffix = ""
    if providers:
        provider_suffix = " — " + ", ".join(str(p).strip() for p in providers[:3] if str(p).strip())

    m = _EXPERTOS_LEY_RE.search(raw)
    if m:
        kind = m.group(1).capitalize()
        return f"Expertos sobre {kind} {m.group(2)} de {m.group(3)}{provider_suffix}"
    m = _DOCTRINA_DIAN_RE.search(raw)
    if m:
        kind = m.group(1).capitalize()
        return f"{kind} DIAN {m.group(2)} de {m.group(3)}"

    # 3. Use source_label / subtema even if raw, but append providers.
    subtema = str(candidate.get("subtema") or "").strip()
    if subtema and provider_suffix:
        return f"{subtema}{provider_suffix}"
    return subtema or source_label or fallback


_DEPTH_LABEL_ET_RE = re.compile(
    r"^et\s+art\.?\s*(\d+(?:-\d+)?(?:-[a-z])?)\s*(.*)$",
    re.IGNORECASE,
)
_DEPTH_LABEL_FILE_EXT_RE = re.compile(r"\.(?:md|txt|json|html?)$", re.IGNORECASE)
_DEPTH_LABEL_SMALL_WORDS = frozenset({
    "a", "al", "con", "de", "del", "desde", "e", "el", "en",
    "la", "las", "los", "o", "para", "por", "sin", "u", "un", "una", "y",
})


_LABEL_DEDUP_ENTITY_RE = re.compile(
    r"\b(?:personas?\s+(?:jur[ií]dicas?|naturales?)|grandes?\s+contribuyentes?"
    r"|jur[ií]dicas?|naturales?|gc|pj|pn|rst|pes)\b",
    re.IGNORECASE,
)
_LABEL_DEDUP_YEAR_RE = re.compile(r"\b\d{4}\b")


def _label_dedup_key(label: str) -> str:
    """Collapse entity-type / year variants into a single dedup key."""
    key = _LABEL_DEDUP_ENTITY_RE.sub("", label.lower())
    key = _LABEL_DEDUP_YEAR_RE.sub("", key)
    return re.sub(r"\s+", " ", key).strip()


def _normalize_depth_item_label(label: str) -> str:
    """Normalize a depth-section item label for human readability.

    Handles ET article labels, technical filenames, file extensions,
    and applies Spanish title case.
    """
    clean = str(label or "").strip()
    if not clean:
        return clean

    # Strip file extensions
    clean = _DEPTH_LABEL_FILE_EXT_RE.sub("", clean).strip()

    # Preserve provider suffixes (e.g. " — Holland & Knight, Deloitte")
    provider_suffix = ""
    dash_pos = clean.find(" — ")
    if dash_pos > 0:
        provider_suffix = clean[dash_pos:]
        clean = clean[:dash_pos].strip()

    # ET article labels: "et art 129 concepto de obsolescencia"
    et_match = _DEPTH_LABEL_ET_RE.match(clean)
    if et_match:
        art_num = et_match.group(1)
        remainder = et_match.group(2).strip().lstrip("—–-:, ").strip()
        if remainder:
            remainder = _spanish_title_case_label(remainder)
            return f"ET Art. {art_num} — {remainder}{provider_suffix}"
        return f"ET Art. {art_num}{provider_suffix}"

    # Technical names with hex hashes or "part N" — humanize
    from .ui_source_view_processors import _looks_like_technical_title, _humanize_technical_title
    if _looks_like_technical_title(clean):
        humanized = _humanize_technical_title(clean)
        if humanized:
            return f"{humanized}{provider_suffix}"

    # General: apply title case if entirely lowercase
    if clean == clean.lower():
        clean = _spanish_title_case_label(clean)

    return f"{clean}{provider_suffix}" if provider_suffix else clean


def _spanish_title_case_label(text: str) -> str:
    """Apply Spanish title case to a label string."""
    words = text.split()
    if not words:
        return text
    result: list[str] = []
    for i, word in enumerate(words):
        if i == 0 or word.lower() not in _DEPTH_LABEL_SMALL_WORDS:
            result.append(word.capitalize())
        else:
            result.append(word.lower())
    return " ".join(result)


def _build_structured_additional_depth_sections(context: dict[str, Any]) -> list[dict[str, Any]] | None:
    citation = dict(context.get("citation") or {})
    if _ui()._citation_targets_et_article(citation):
        sections = _resolve_et_additional_depth_sections(context)
        # Enrich context with ET locator row's normative_refs for broader
        # corpus matching — the locator row may carry refs that the
        # context's reference_identity_keys lack.
        et_row = _resolve_et_locator_row(context)
        enriched = dict(context)
        if et_row:
            extra = set(enriched.get("reference_identity_keys") or [])
            for ref in list(et_row.get("normative_refs") or []):
                k = str(ref).strip()
                if k:
                    extra.add(k)
            enriched["reference_identity_keys"] = sorted(extra)
        corpus_sections = _resolve_ley_additional_depth_sections(enriched)
        if corpus_sections:
            sections.extend(corpus_sections)
        return sections or None
    # All other families (ley, decreto, resolucion, jurisprudencia,
    # concepto, circular, constitucion, generic) use the same
    # cross-reference logic to surface related 1x1x1 badge items.
    sections = _resolve_ley_additional_depth_sections(context)
    return sections or None


_PRACTICA_INTERNAL_LABEL_RE = re.compile(r"ingesta\s+gui|checksum=", re.IGNORECASE)
_PRACTICA_GENERIC_SUBTEMAS = frozenset({"ingestion_user_upload", "guia_practica_general", "guia practica", ""})
_PRACTICA_UNKNOWN_PREFIX_RE = re.compile(r"^unknown\s*[:—–\-]\s*", re.IGNORECASE)
_PRACTICA_CODE_PREFIX_RE = re.compile(r"^[a-z]{1,6}\s+[a-z]?\w{1,6}\s*[—–\-]\s*", re.IGNORECASE)
_PRACTICA_NUM_PREFIX_RE = re.compile(r"^\d{1,3}\s*[—–\-]\s*", re.IGNORECASE)
_PRACTICA_LEY_DOCID_RE = re.compile(r"practica[_\-\s]ley[_\-\s](\d+)[_\-\s](\d{4})", re.IGNORECASE)
_PRACTICA_EXT_SUFFIX_RE = re.compile(r"\.(?:md|txt|json|html?)$", re.IGNORECASE)


def _clean_practica_label(raw: str) -> str:
    label = _PRACTICA_CODE_PREFIX_RE.sub("", raw).strip()
    label = _PRACTICA_UNKNOWN_PREFIX_RE.sub("", label).strip()
    label = _PRACTICA_NUM_PREFIX_RE.sub("", label).strip()
    label = _PRACTICA_EXT_SUFFIX_RE.sub("", label).strip()
    label = label.replace("_", " ")
    label = re.sub(r"\s+", " ", label).strip()
    return label or raw


def _best_practica_display_label(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        title = str(row.get("title") or "").strip()
        if title and not _PRACTICA_INTERNAL_LABEL_RE.search(title):
            return _clean_practica_label(title)
    best_subtema = ""
    for row in rows:
        subtema = str(row.get("subtema") or "").strip()
        if (
            subtema
            and subtema.lower() not in _PRACTICA_GENERIC_SUBTEMAS
            and not _PRACTICA_INTERNAL_LABEL_RE.search(subtema)
            and len(subtema) > len(best_subtema)
        ):
            best_subtema = subtema
    if best_subtema:
        label = _clean_practica_label(best_subtema)
        if not label:
            label = best_subtema
        doc_id = str(rows[0].get("doc_id") or "")
        ley_m = _PRACTICA_LEY_DOCID_RE.search(doc_id)
        if ley_m and not re.search(r"ley\s+\d+", label, re.IGNORECASE):
            label = f"Ley {ley_m.group(1)} de {ley_m.group(2)} — {label}"
        return label[0].upper() + label[1:] if label else "Guía práctica"
    doc_id = str(rows[0].get("doc_id") or "").strip()
    if doc_id:
        ley_m = _PRACTICA_LEY_DOCID_RE.search(doc_id)
        if ley_m:
            return f"Ley {ley_m.group(1)} de {ley_m.group(2)} — Guía Práctica"
        slug = re.sub(r"^[a-z]+_ingest_", "", doc_id, flags=re.IGNORECASE)
        slug = re.sub(r"_[0-9a-f]{6,8}$", "", slug)
        slug = slug.replace("_", " ").replace("-", " ")
        slug = _PRACTICA_EXT_SUFFIX_RE.sub("", slug)
        slug = re.sub(r"\s+", " ", slug).strip()
        if slug:
            return slug[0].upper() + slug[1:]
    return "Guía práctica"
