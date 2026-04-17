from __future__ import annotations

import re
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs

from .contracts import Citation, DocumentRecord


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def handle_citation_get(handler: Any, path: str, parsed: Any, *, deps: dict[str, Any]) -> bool:
    """Handles GET /api/citation-profile and /api/normative-analysis.

    ``deps`` must provide the citation-profile infrastructure that remains in
    ``ui_server``:

        collect_citation_profile_context,
        collect_citation_profile_context_by_reference_key,
        build_fallback_citation_profile_payload,
        apply_citation_profile_request_context,
        should_skip_citation_profile_llm,
        llm_citation_profile_payload,
        build_citation_profile_lead,
        build_citation_profile_facts,
        build_citation_profile_sections,
        render_citation_profile_payload,
        render_normative_analysis_payload,
        index_file_path,
    """
    if path == "/api/citation-profile":
        query = parse_qs(parsed.query)
        doc_id = str((query.get("doc_id") or [""])[0]).strip()
        reference_key = str((query.get("reference_key") or [""])[0]).strip()
        message_context = str((query.get("message_context") or [""])[0]).strip()
        locator_text = str((query.get("locator_text") or [""])[0]).strip()
        locator_kind = str((query.get("locator_kind") or [""])[0]).strip()
        locator_start = str((query.get("locator_start") or [""])[0]).strip()
        locator_end = str((query.get("locator_end") or [""])[0]).strip()
        phase = str((query.get("phase") or [""])[0]).strip().lower()
        if not doc_id and not reference_key:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`doc_id` o `reference_key` es obligatorio."})
            return True

        # Resolve ET article references: reference_key="et" + locator_start="720"
        # → doc_id="renta_corpus_a_et_art_720"
        if not doc_id and reference_key.strip().lower() == "et" and locator_start:
            _et_key = re.sub(r"[_\-.]+", "_", locator_start).strip("_")
            if _et_key:
                doc_id = f"renta_corpus_a_et_art_{_et_key}"

        # Resolve ley references: reference_key="ley:2277:2022"
        # → doc_id="co_ley_2277_2022"
        if not doc_id and reference_key.strip().lower().startswith("ley:"):
            _ley_parts = reference_key.strip().lower().split(":")
            if len(_ley_parts) >= 3 and _ley_parts[1].strip() and _ley_parts[2].strip():
                doc_id = f"co_ley_{_ley_parts[1].strip()}_{_ley_parts[2].strip()}"
            elif len(_ley_parts) == 2 and _ley_parts[1].strip():
                doc_id = f"co_ley_{_ley_parts[1].strip()}"

        index_file = deps["index_file_path"]
        _collect = deps["collect_citation_profile_context"]
        _collect_by_ref = deps["collect_citation_profile_context_by_reference_key"]
        _build_fallback = deps.get("build_fallback_citation_profile_payload")
        _apply_req_ctx = deps["apply_citation_profile_request_context"]
        _skip_llm = deps["should_skip_citation_profile_llm"]
        _llm_payload = deps["llm_citation_profile_payload"]
        _lead = deps["build_citation_profile_lead"]
        _facts = deps["build_citation_profile_facts"]
        _sections = deps["build_citation_profile_sections"]
        _render = deps["render_citation_profile_payload"]

        allow_remote_fallback = phase != "instant"
        context = (
            _collect(doc_id, index_file=index_file, allow_remote_fallback=allow_remote_fallback)
            if doc_id
            else _collect_by_ref(
                reference_key,
                index_file=index_file,
                allow_remote_fallback=allow_remote_fallback,
            )
        )
        if context is None and not allow_remote_fallback:
            context = (
                _collect(doc_id, index_file=index_file, allow_remote_fallback=True)
                if doc_id
                else _collect_by_ref(
                    reference_key,
                    index_file=index_file,
                    allow_remote_fallback=True,
                )
            )
        # Fallback: if doc_id resolution missed (e.g. GUI-uploaded doc with
        # non-canonical doc_id), try reference_key catalog lookup.
        if context is None and doc_id and reference_key:
            context = _collect_by_ref(
                reference_key,
                index_file=index_file,
                allow_remote_fallback=allow_remote_fallback,
            )
            if context is None and not allow_remote_fallback:
                context = _collect_by_ref(
                    reference_key,
                    index_file=index_file,
                    allow_remote_fallback=True,
                )
        if context is None:
            fallback_payload = (
                _build_fallback(
                    doc_id=doc_id,
                    reference_key=reference_key,
                    message_context=message_context,
                    locator_text=locator_text,
                    locator_kind=locator_kind,
                    locator_start=locator_start,
                    locator_end=locator_end,
                )
                if callable(_build_fallback)
                else {}
            )
            if fallback_payload:
                if phase == "llm":
                    handler._send_json(HTTPStatus.OK, {"ok": True, "phase": "llm", "skipped": True})
                    return True
                handler._send_json(HTTPStatus.OK, {"ok": True, "needs_llm": False, **fallback_payload})
                return True
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "Documento no encontrado."})
            return True
        context = _apply_req_ctx(
            context,
            message_context=message_context,
            locator_text=locator_text,
            locator_kind=locator_kind,
            locator_start=locator_start,
            locator_end=locator_end,
        )

        skip_llm = _skip_llm(context)

        if phase == "llm":
            if skip_llm:
                handler._send_json(HTTPStatus.OK, {"ok": True, "phase": "llm", "skipped": True})
                return True
            llm_result = _llm_payload(context)
            llm_lead = _lead(context, llm_payload=llm_result)
            llm_facts = _facts(context, llm_payload=llm_result)
            llm_sections = _sections(context, llm_payload=llm_result)
            response_payload: dict[str, Any] = {
                "ok": True,
                "phase": "llm",
                "lead": llm_lead,
                "facts": llm_facts,
                "sections": llm_sections,
            }
            _targets_et = deps.get("citation_targets_et_article")
            _vigencia_detail_fn = deps.get("build_structured_vigencia_detail")
            _vigencia_llm = deps.get("summarize_vigencia_llm")
            citation = dict(context.get("citation") or {})
            if _targets_et and _targets_et(citation) and _vigencia_detail_fn and _vigencia_llm:
                vigencia_detail = _vigencia_detail_fn(context)
                if isinstance(vigencia_detail, dict):
                    article_label = str(locator_text or locator_start or "").strip()
                    summary = _vigencia_llm(vigencia_detail, article_label)
                    if summary:
                        vigencia_detail["summary"] = summary
                    response_payload["vigencia_detail"] = vigencia_detail
            handler._send_json(HTTPStatus.OK, response_payload)
            return True

        if phase == "instant":
            llm_result = {}
        else:
            llm_result = _llm_payload(context) if not skip_llm else {}

        profile_payload = _render(context, llm_payload=llm_result)
        needs_llm = phase == "instant" and not skip_llm
        handler._send_json(HTTPStatus.OK, {"ok": True, "needs_llm": needs_llm, **profile_payload})
        return True

    if path == "/api/normative-analysis":
        query = parse_qs(parsed.query)
        doc_id = str((query.get("doc_id") or [""])[0]).strip()
        locator_text = str((query.get("locator_text") or [""])[0]).strip()
        locator_kind = str((query.get("locator_kind") or [""])[0]).strip()
        locator_start = str((query.get("locator_start") or [""])[0]).strip()
        locator_end = str((query.get("locator_end") or [""])[0]).strip()
        if not doc_id:
            handler._send_json(HTTPStatus.BAD_REQUEST, {"error": "`doc_id` es obligatorio."})
            return True

        index_file = deps["index_file_path"]
        _collect = deps["collect_citation_profile_context"]
        _apply_req_ctx = deps["apply_citation_profile_request_context"]
        _render_normative = deps["render_normative_analysis_payload"]

        context = _collect(doc_id, index_file=index_file)
        if context is None:
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": "Documento no encontrado."})
            return True
        context = _apply_req_ctx(
            context,
            locator_text=locator_text,
            locator_kind=locator_kind,
            locator_start=locator_start,
            locator_end=locator_end,
        )

        analysis_payload = _render_normative(context)
        handler._send_json(HTTPStatus.OK, {"ok": True, **analysis_payload})
        return True

    return False


# ---------------------------------------------------------------------------
# Usage-context utilities (moved from ui_server.py)
# ---------------------------------------------------------------------------

def _extract_usage_context_from_diagnostics(
    *,
    diagnostics: dict[str, Any] | None,
    doc_id: str,
) -> str:
    from lia_graph.ui_server import _clip_session_content, _flatten_markdown_to_text

    if not isinstance(diagnostics, dict):
        return ""
    retrieval = diagnostics.get("retrieval")
    if not isinstance(retrieval, dict):
        return ""
    candidate_blocks: list[Any] = []
    for key in (
        "top_rows",
        "selected_rows",
        "selected_docs",
        "docs",
        "evidence",
        "chunks",
    ):
        value = retrieval.get(key)
        if isinstance(value, list):
            candidate_blocks.extend(value)
    for item in candidate_blocks:
        if not isinstance(item, dict):
            continue
        if str(item.get("doc_id", "")).strip() != doc_id:
            continue
        for field in ("chunk_text", "summary", "snippet", "text", "content", "citation"):
            snippet = _clip_session_content(_flatten_markdown_to_text(str(item.get(field, ""))), max_chars=220)
            if snippet:
                return snippet
    return ""


def _extract_usage_context_from_answer(
    *,
    citation: dict[str, Any],
    answer_text: str,
) -> str:
    from lia_graph.ui_server import (
        _clip_session_content,
        _flatten_markdown_to_text,
        _looks_like_reference_list,
        _split_sentences,
        _tokenize_relevance_text,
    )
    from lia_graph.ui_server import (
        _extract_reference_identities_from_citation_payload,
        _extract_reference_identities_from_text,
    )

    plain_answer = _flatten_markdown_to_text(answer_text, max_chars=8000)
    if not plain_answer:
        return ""
    answer_sentences = _split_sentences(plain_answer)
    if not answer_sentences:
        return _clip_session_content(plain_answer, max_chars=220)
    citation_locator_identities = {
        identity for identity in _extract_reference_identities_from_citation_payload(citation) if "::" in identity
    }
    if citation_locator_identities:
        answer_locator_identities = _extract_reference_identities_from_text(plain_answer)
        if not citation_locator_identities.intersection(answer_locator_identities):
            return ""
    hint_tokens: set[str] = set()
    for field in ("source_label", "legal_reference", "authority"):
        hint_tokens.update(_tokenize_relevance_text(str(citation.get(field, ""))))
    best_sentence = answer_sentences[0]
    best_score = -1.0
    for sentence in answer_sentences:
        if citation_locator_identities:
            sentence_locator_identities = _extract_reference_identities_from_text(sentence)
            if not citation_locator_identities.intersection(sentence_locator_identities):
                continue
        sentence_tokens = set(_tokenize_relevance_text(sentence))
        overlap = len(sentence_tokens.intersection(hint_tokens)) if hint_tokens else 0
        score = float(overlap)
        if citation_locator_identities:
            score += 5.0
        if _looks_like_reference_list(sentence):
            score -= 0.6
        if score > best_score:
            best_score = score
            best_sentence = sentence
    if citation_locator_identities and best_score < 0:
        return ""
    return _clip_session_content(best_sentence, max_chars=220)


def _build_citation_usage_payload(
    *,
    citation: dict[str, Any],
    answer_text: str,
    diagnostics: dict[str, Any] | None,
) -> tuple[str | None, list[str] | None]:
    from lia_graph.ui_server import _detect_intent_tags, _sanitize_question_context

    doc_id = str(citation.get("doc_id", "")).strip()
    if not doc_id:
        return None, None
    usage_context = _extract_usage_context_from_diagnostics(diagnostics=diagnostics, doc_id=doc_id)
    if not usage_context:
        usage_context = _extract_usage_context_from_answer(citation=citation, answer_text=answer_text)
    usage_context = _sanitize_question_context(usage_context, max_chars=220)
    if not usage_context:
        return None, None
    detected_intents = sorted(tag for tag in _detect_intent_tags(usage_context) if tag != "ejemplos")
    return usage_context, detected_intents[:3] if detected_intents else None


def _enrich_citation_payloads_with_usage_context(
    *,
    citations_payload: list[dict[str, Any]],
    answer_text: str,
    diagnostics: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for citation in citations_payload:
        if not isinstance(citation, dict):
            continue
        usage_context, usage_intents = _build_citation_usage_payload(
            citation=citation,
            answer_text=answer_text,
            diagnostics=diagnostics,
        )
        cloned = dict(citation)
        cloned["usage_context"] = usage_context
        cloned["usage_intents"] = usage_intents
        enriched.append(cloned)
    return enriched


# ---------------------------------------------------------------------------
# Citation helpers (moved from ui_server.py)
# ---------------------------------------------------------------------------

def _load_doc_index_row(doc_id: str) -> tuple[dict[str, Any] | None, str]:
    from lia_graph.ui_server import _find_document_index_row

    clean_doc_id = str(doc_id or "").strip()
    if not clean_doc_id:
        return None, ""
    row = _find_document_index_row(clean_doc_id)
    if row is None:
        return None, clean_doc_id
    return row, clean_doc_id


def _load_doc_corpus_text(doc_id: str, *, prefer_original: bool = True) -> tuple[str | None, dict[str, Any] | None]:
    from lia_graph.ui_server import (
        _load_source_text,
        _pick_local_source_file,
        _resolve_knowledge_file,
        _resolve_local_upload_artifact,
    )

    row, clean_doc_id = _load_doc_index_row(doc_id)
    if row is None:
        return None, None
    # Try local filesystem first (fast, works in dev)
    source_url = str(row.get("url", "")).strip()
    normalized_file = _resolve_knowledge_file(str(row.get("absolute_path", "")).strip())
    upload_artifact = _resolve_local_upload_artifact(doc_id=clean_doc_id, source_url=source_url)
    preferred_view = "original" if prefer_original else "normalized"
    source_file, selected_view = _pick_local_source_file(
        normalized_file=normalized_file,
        upload_artifact=upload_artifact,
        view=preferred_view,
    )
    if source_file is not None:
        try:
            text = _load_source_text(source_file)
            row["__selected_view"] = selected_view
            row["__selected_file"] = str(source_file)
            return text, row
        except (OSError, UnicodeDecodeError):
            pass
    # Fallback: assemble text from Supabase chunks (production path)
    from lia_graph.ui_server import _sb_assemble_document_markdown  # lazy, test-monkeypatchable

    text = _sb_assemble_document_markdown(clean_doc_id)
    if text:
        row["__selected_view"] = "supabase_chunks"
        return text, row
    return None, row


def _build_public_citation_from_row(row: dict[str, Any]) -> dict[str, Any]:
    from lia_graph.ui_server import _build_download_href, _resolve_local_upload_artifact

    doc = DocumentRecord.from_dict(dict(row))
    citation = Citation.from_document(doc)
    payload = citation.to_public_dict()
    doc_id = str(payload.get("doc_id", "")).strip()
    if not doc_id:
        return payload
    payload["download_url"] = _build_download_href(doc_id=doc_id, view="normalized", fmt="pdf")
    payload["download_md_url"] = _build_download_href(doc_id=doc_id, view="normalized", fmt="md")
    source_url = str(row.get("url", "")).strip()
    upload_artifact = _resolve_local_upload_artifact(doc_id=doc_id, source_url=source_url)
    payload["download_original_url"] = (
        _build_download_href(doc_id=doc_id, view="original", fmt="original")
        if upload_artifact is not None and upload_artifact.exists()
        else None
    )
    return payload


def _hydrate_citation_download_urls(citations_payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from lia_graph.ui_server import _build_download_href, _find_document_index_row

    hydrated: list[dict[str, Any]] = []
    for citation in citations_payload:
        if not isinstance(citation, dict):
            continue
        row = _find_document_index_row(str(citation.get("doc_id", "")).strip())
        merged = dict(citation)
        if row is not None:
            row_payload = _build_public_citation_from_row(row)
            merged = row_payload | merged
            # Keep the canonical original-download URL from index hydration.
            merged["download_original_url"] = row_payload.get("download_original_url")
            merged.setdefault("download_url", _build_download_href(doc_id=str(row.get("doc_id", "")).strip(), view="normalized", fmt="pdf"))
        doc_id = str(merged.get("doc_id", "")).strip()
        if doc_id and not str(merged.get("download_url", "")).strip():
            merged["download_url"] = _build_download_href(doc_id=doc_id, view="normalized", fmt="pdf")
        if doc_id and not str(merged.get("download_md_url", "")).strip():
            merged["download_md_url"] = _build_download_href(doc_id=doc_id, view="normalized", fmt="md")
        hydrated.append(merged)
    return hydrated


def _build_interpretation_query_seed(
    *,
    citation: dict[str, Any],
    index_row: dict[str, Any] | None,
    message_context: str | None,
    assistant_answer: str | None = None,
) -> str:
    parts: list[str] = []
    for field in ("legal_reference", "source_label", "authority", "topic", "pais"):
        value = str(citation.get(field, "")).strip()
        if value:
            parts.append(value)
    if index_row:
        for field in ("tema", "subtema", "authority", "notes"):
            value = str(index_row.get(field, "")).strip()
            if value:
                parts.append(value)
    # Prioritize assistant_answer — richest semantic signal for interpretation retrieval
    answer = str(assistant_answer or "").strip()
    if answer:
        parts.append(answer[:250])
    context = str(message_context or "").strip()
    if context:
        parts.append(context[:300])
    seed = re.sub(r"\s+", " ", " | ".join(parts)).strip(" |")
    return seed[:800]


def _build_extractive_interpretation_summary(
    *,
    corpus_text: str,
    citation_label: str,
    interpretation_title: str,
) -> str:
    from lia_graph.ui_server import _clip_session_content

    normalized = _clip_session_content(corpus_text, max_chars=4000)
    paragraphs = [segment.strip() for segment in re.split(r"\n{2,}", normalized) if segment.strip()]
    sentences = [segment.strip() for segment in re.split(r"(?<=[\.\!\?])\s+", normalized) if segment.strip()]

    lectura = paragraphs[0] if paragraphs else "No evidenciado en el corpus."
    impacto = sentences[1] if len(sentences) > 1 else "No evidenciado en el corpus."
    riesgos = sentences[2] if len(sentences) > 2 else "No evidenciado en el corpus."
    contraste = (
        f"La lectura de `{interpretation_title}` complementa `{citation_label}`. "
        f"Evidencia puntual: {sentences[0]}"
        if sentences
        else "No evidenciado en el corpus."
    )
    checklist_items = []
    for sentence in sentences[:5]:
        checklist_items.append(f"- Verificar: {sentence[:180].rstrip()}")
    if not checklist_items:
        checklist_items = ["- Verificar literal aplicable en documento interpretativo.", "- Confirmar coherencia con la norma citada."]

    return "\n".join(
        [
            "## Lectura profesional",
            lectura,
            "",
            "## Impacto operativo para contador",
            impacto,
            "",
            "## Riesgos y controversias",
            riesgos,
            "",
            "## Contraste contra norma citada",
            contraste,
            "",
            "## Checklist de verificacion",
            *checklist_items,
        ]
    ).strip()
