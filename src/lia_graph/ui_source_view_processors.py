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
# Title resolver extracted during granularize-v2 — re-imported so eager
# `from .ui_source_view_processors import _pick_source_display_title` style
# imports keep working (the ui_server lazy registry points lookups at the
# new sibling directly). The reference-anchor cluster below still uses
# `_SOURCE_FORM_REFERENCE_RE` and `_normalize_source_reference_text`.
from .ui_source_title_resolver import (  # noqa: F401  — re-exported
    _SOURCE_ARTICLE_ID_LINE_RE,
    _SOURCE_FORM_REFERENCE_RE,
    _SOURCE_HEADING_LINE_RE,
    _TECHNICAL_PREFIX_TOKEN_RE,
    _build_source_download_filename,
    _extract_source_title_from_raw_text,
    _humanize_technical_title,
    _infer_source_title_from_url_or_path,
    _is_generic_source_title,
    _looks_like_technical_title,
    _normalize_source_reference_text,
    _pick_source_display_title,
    _resolve_source_display_title,
    _source_url_label_for_filename,
    _title_from_normative_identity,
)
# HTML rendering extracted during granularize-v2 round 7. Re-imported so
# eager `from .ui_source_view_processors import _build_source_view_html`
# style imports in ui_server.py keep working; ui_server lazy registry now
# points lookups at the new sibling directly.
from .ui_source_view_html import (  # noqa: F401  — re-exported
    _build_source_view_href,
    _build_source_view_html,
    _render_source_view_inline_markdown,
    _render_source_view_markdown_html,
    _sanitize_source_view_href,
)
# Noise filtering + content-marker trimming extracted round 8 — graduates
# the host below 1000 LOC. Constants/functions still re-exported for
# back-compat.
from .ui_source_view_noise_filter import (  # noqa: F401  — re-exported
    _SOURCE_VIEW_CONTENT_MARKERS,
    _SOURCE_VIEW_HTML_NOISE_HINTS,
    _SOURCE_VIEW_NON_USABLE_HINTS,
    _SOURCE_VIEW_USEFUL_HINT_RE,
    _extract_source_view_usable_text,
    _is_source_view_noise_text,
    _trim_source_view_content_markers,
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

_SOURCE_VIEW_SECTION_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("que_hace", "Qué hace", False),
    ("por_que_sirve", "Por qué le sirve al contador", False),
    ("puntos_clave", "Puntos clave", True),
    ("tips", "Tips / comentarios", True),
    ("alertas", "Alertas", True),
    ("sustento", "Sustento", True),
)
_SOURCE_RESOLUTION_REFERENCE_RE = re.compile(r"\b(resoluci[oó]n\s+[0-9A-Za-z\-]+(?:\s+de\s+\d{4})?)\b", re.IGNORECASE)
_SOURCE_DECREE_REFERENCE_RE = re.compile(r"\b(decreto\s+[0-9A-Za-z\-]+(?:\s+de\s+\d{4})?)\b", re.IGNORECASE)
_SOURCE_LAW_REFERENCE_RE = re.compile(r"\b(ley\s+[0-9A-Za-z\-]+(?:\s+de\s+\d{4})?)\b", re.IGNORECASE)
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
