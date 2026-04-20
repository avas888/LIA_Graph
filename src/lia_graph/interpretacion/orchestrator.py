from __future__ import annotations

import json
from http import HTTPStatus
from urllib.parse import quote
from uuid import uuid4

from ..contracts.document import DocumentRecord
from .catalog import list_local_interpretation_rows
from .assembly import (
    build_citation_interpretations_payload,
    build_expert_panel_enhancements_payload,
    build_expert_panel_explore_payload,
    build_expert_panel_payload,
    build_interpretation_summary_payload,
)
from .policy import (
    CITATION_INTERPRETATIONS_DEFAULT_PROCESS_LIMIT,
    CITATION_INTERPRETATIONS_DEFAULT_TOP_K,
    CITATION_INTERPRETATIONS_MAX_TOP_K,
    EXPERT_PANEL_ENHANCE_FALLBACK_MODE,
    EXPERT_PANEL_ENHANCE_MAX_CARDS,
    EXPERT_PANEL_EXPLORE_FALLBACK_MODE,
    EXPERT_PANEL_EXPLORE_MAX_SNIPPETS,
    EXPERT_PANEL_LOAD_MORE_LIMIT,
    EXPERT_PANEL_PROCESS_LIMIT,
    EXPERT_PANEL_TOP_K,
    INTERPRETATION_SUMMARY_FALLBACK_MODE,
    build_expert_enhance_prompt,
    build_expert_explore_prompt,
    build_interpretation_summary_prompt,
)
from .rerank import rerank_runtimes
from .rerank.applier import apply_to_surface as apply_rerank_to_surface
from .shared import ExpertEnhancement, InterpretationDocRuntime, InterpretationSummarySurface
from .synthesis import synthesize_citation_interpretations, synthesize_expert_panel
from .synthesis_helpers import (
    build_decision_frame,
    build_expert_query_seed,
    build_fallback_expert_enhancements,
    build_fallback_expert_explore_content,
    extract_article_refs,
    normalize_text,
)

_QUERY_TOKEN_STOPWORDS = {
    "art",
    "articulo",
    "artículos",
    "et",
    "de",
    "del",
    "la",
    "el",
    "los",
    "las",
    "que",
    "como",
    "para",
    "con",
    "por",
    "una",
    "uno",
    "sobre",
    "segun",
    "según",
    "fiscales",
}


def _coerce_non_negative_int(value, *, default: int) -> int:
    if not isinstance(value, int) or value < 0:
        return default
    return value


def _snippet_source_view_url(doc_id: str) -> str | None:
    clean = str(doc_id or "").strip()
    return f"/source-view?doc_id={quote(clean, safe='')}" if clean else None


def _sanitize_http_url(value: str) -> str:
    clean = str(value or "").strip()
    return clean if clean.startswith(("http://", "https://")) else ""


def _build_runtime_for_doc(doc, *, deps) -> InterpretationDocRuntime | None:
    doc_id = str(getattr(doc, "doc_id", "") or "").strip()
    if not doc_id:
        return None
    fallback_row = deps["find_document_index_row"](doc_id)
    corpus_text, resolved_row = deps["load_doc_corpus_text"](doc_id, prefer_original=True)
    row_payload = resolved_row if isinstance(resolved_row, dict) else fallback_row or {}
    if row_payload is not None:
        citation_payload = deps["build_public_citation_from_row"](row_payload)
    else:
        citation_payload = deps["citation_cls"].from_document(doc).to_public_dict()
    providers = deps["resolve_doc_expert_providers"](
        row=row_payload,
        text=corpus_text or "",
        authority=str(citation_payload.get("authority", "")).strip(),
    )
    provider_links = deps["filter_provider_links"](corpus_text or "", providers=providers, max_links=12)
    official = _sanitize_http_url(str(citation_payload.get("official_url", "")).strip())
    if not provider_links and official:
        provider_links = [
            {
                "url": official,
                "label": "Fuente profesional",
                "provider": deps["classify_provider"](official),
                "domain": official.split("//", 1)[-1].split("/", 1)[0].lower().replace("www.", ""),
            }
        ]
    if not providers and provider_links:
        providers = deps["resolve_doc_expert_providers"](
            row=row_payload,
            text=" ".join(
                f"{item.get('provider', '')} {item.get('label', '')} {item.get('url', '')}"
                for item in provider_links
            ),
            authority=str(citation_payload.get("authority", "")).strip(),
        )
    citation_payload = dict(citation_payload)
    citation_payload.setdefault("source_view_url", _snippet_source_view_url(doc_id))
    citation_payload.setdefault("open_url", citation_payload.get("official_url") or citation_payload.get("source_view_url"))
    return InterpretationDocRuntime(
        doc=doc,
        row=row_payload,
        corpus_text=corpus_text or "",
        citation_payload=citation_payload,
        providers=tuple(dict(item) for item in providers or ()),
        provider_links=tuple(dict(item) for item in provider_links or ()),
    )


def _retrieve_interpretation_docs(*, query: str, top_k: int, pais: str, topic: str | None, deps):
    del deps
    query_tokens = tuple(
        token
        for token in normalize_text(query).split()
        if len(token) >= 3 and token not in _QUERY_TOKEN_STOPWORDS
    )
    query_refs = set(extract_article_refs(query))
    scored_rows: list[tuple[float, dict[str, object]]] = []

    for row in list_local_interpretation_rows():
        row_pais = str(row.get("pais") or "colombia").strip().lower() or "colombia"
        if pais and row_pais and row_pais != str(pais).strip().lower():
            continue
        row_topic = str(row.get("topic") or row.get("topic_key") or "").strip().lower()

        preview_text = str(row.get("__catalog_preview") or "")
        normalized_preview = normalize_text(
            " ".join(
                [
                    str(row.get("source_label") or ""),
                    str(row.get("authority") or ""),
                    str(row.get("relative_path") or ""),
                    str(row.get("topic") or row.get("topic_key") or ""),
                    " ".join(str(item) for item in row.get("provider_labels", ()) or ()),
                    " ".join(str(item) for item in row.get("normative_refs", ()) or ()),
                    preview_text,
                ]
            )
        )
        token_hits = sum(1.0 for token in query_tokens if token in normalized_preview)
        row_refs = set(str(item).strip() for item in row.get("normative_refs", ()) or () if str(item).strip())
        ref_hits = len(query_refs.intersection(row_refs))
        phrase_bonus = 0.8 if normalize_text(query) and normalize_text(query)[:140] in normalized_preview else 0.0
        normalized_topic = str(topic or "").strip().lower()
        topic_bonus = 0.0
        if normalized_topic and row_topic:
            if row_topic == normalized_topic:
                topic_bonus = 1.4
            elif normalized_topic in row_topic or row_topic in normalized_topic:
                topic_bonus = 0.7
        provider_bonus = 0.25 if row.get("provider_labels") else 0.0
        raw_score = (2.5 * ref_hits) + token_hits + phrase_bonus + topic_bonus + provider_bonus
        if raw_score <= 0:
            continue
        scored_rows.append((raw_score, dict(row)))

    scored_rows.sort(
        key=lambda item: (
            -item[0],
            str(item[1].get("source_label") or item[1].get("relative_path") or ""),
        )
    )
    candidate_rows = scored_rows[: max(top_k * 3, 12)]
    if not candidate_rows:
        candidate_rows = [
            (1.0, dict(row))
            for row in list_local_interpretation_rows()[: max(top_k, 8)]
        ]

    max_score = max((score for score, _row in candidate_rows), default=1.0) or 1.0
    docs_selected: list[DocumentRecord] = []
    for score, row in candidate_rows:
        doc_payload = dict(row)
        doc_payload["retrieval_score"] = round(min(1.0, float(score) / float(max_score)), 4)
        doc_payload["trust_tier"] = str(doc_payload.get("trust_tier") or "medium").strip() or "medium"
        docs_selected.append(DocumentRecord.from_dict(doc_payload))

    return type(
        "InterpretationKnowledgeBundle",
        (),
        {
            "docs_selected": docs_selected[: max(top_k, 1)],
            "retrieval_diagnostics": {
                "mode": "local_interpretation_catalog",
                "candidate_rows": len(scored_rows),
                "selected_docs": len(docs_selected[: max(top_k, 1)]),
                "query_tokens": list(query_tokens),
                "query_refs": sorted(query_refs),
            },
        },
    )()


def run_expert_panel_request(payload: dict, *, deps: dict):
    trace_id = str(payload.get("trace_id", "")).strip()
    message = str(payload.get("message", "")).strip()
    assistant_answer = payload.get("assistant_answer")
    if not trace_id:
        return HTTPStatus.BAD_REQUEST, {"error": "Campo `trace_id` requerido."}, None
    if not message:
        return HTTPStatus.BAD_REQUEST, {"error": "Campo `message` requerido."}, None
    if assistant_answer is not None and not isinstance(assistant_answer, str):
        return HTTPStatus.BAD_REQUEST, {"error": "Campo `assistant_answer` debe ser texto si se envia."}, None
    normative_article_refs = payload.get("normative_article_refs", [])
    if not isinstance(normative_article_refs, list):
        normative_article_refs = []
    search_seed = payload.get("search_seed")
    if search_seed is not None and not isinstance(search_seed, str):
        return HTTPStatus.BAD_REQUEST, {"error": "Campo `search_seed` debe ser texto si se envia."}, None
    search_seed_origin = payload.get("search_seed_origin")
    if search_seed_origin is not None and not isinstance(search_seed_origin, str):
        return HTTPStatus.BAD_REQUEST, {"error": "Campo `search_seed_origin` debe ser texto si se envia."}, None

    topic = payload.get("topic")
    pais = str(payload.get("pais", "colombia") or "colombia").strip().lower()
    top_k = payload.get("top_k", EXPERT_PANEL_TOP_K)
    if not isinstance(top_k, int) or top_k < 1:
        top_k = EXPERT_PANEL_TOP_K
    process_limit = payload.get("process_limit", EXPERT_PANEL_PROCESS_LIMIT)
    if not isinstance(process_limit, int) or process_limit < 0:
        process_limit = EXPERT_PANEL_PROCESS_LIMIT
    offset = _coerce_non_negative_int(payload.get("offset", 0), default=0)
    requested_refs = deps["expand_expert_panel_requested_refs"](normative_article_refs)
    if str(search_seed or "").strip():
        expert_query_seed = str(search_seed).strip()
        expert_query_seed_origin = str(search_seed_origin or "").strip() or "deterministic"
    else:
        expert_query_seed = build_expert_query_seed(
            message=message,
            assistant_answer=str(assistant_answer or ""),
            normative_article_refs=[str(item).strip() for item in normative_article_refs if str(item).strip()],
        )
        expert_query_seed_origin = "enriched" if expert_query_seed else "legacy_combined"
        if not expert_query_seed:
            expert_query_seed = "\n\n".join(part.strip() for part in (message, str(assistant_answer or "")) if part.strip())

    search_top_k = max(top_k, offset + (process_limit if process_limit > 0 else top_k) + 12, 18)
    decision_frame = build_decision_frame(
        question=message,
        assistant_answer=str(assistant_answer or ""),
        citation_label=" | ".join(str(item).strip() for item in normative_article_refs if str(item).strip()),
        requested_refs=requested_refs,
    )
    topic_key = deps["normalize_topic_key"](str(topic).strip()) if str(topic or "").strip() else None
    if topic_key and topic_key not in deps["supported_topics"]:
        topic_key = None

    try:
        knowledge = _retrieve_interpretation_docs(
            query=expert_query_seed,
            top_k=search_top_k,
            pais=pais,
            topic=topic_key,
            deps=deps,
        )
    except Exception as exc:  # noqa: BLE001
        return HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "expert_panel_failed", "details": str(exc)}, None

    prioritized_docs = deps["prioritize_expert_panel_docs"](list(knowledge.docs_selected), requested_refs=requested_refs)
    deduped = deps["dedupe_interpretation_docs"](prioritized_docs, limit=search_top_k)
    runtimes = [runtime for doc in deduped if (runtime := _build_runtime_for_doc(doc, deps=deps)) is not None]

    rerank_result = rerank_runtimes(
        runtimes=runtimes,
        question=message,
        assistant_answer=str(assistant_answer or ""),
        expert_query_seed=expert_query_seed,
        trace_id=trace_id or str(uuid4()),
        deps=deps,
    )
    runtimes = list(rerank_result.ordered_runtimes)

    surface = synthesize_expert_panel(
        runtimes=runtimes,
        frame=decision_frame,
        requested_refs=requested_refs,
        offset=offset,
        process_limit=process_limit,
        logical_doc_id=deps["logical_doc_id"],
        expert_card_summary=deps["expert_card_summary"],
        summarize_snippet=deps["summarize_snippet"],
        extended_excerpt=deps.get("extended_excerpt"),
    )
    surface = apply_rerank_to_surface(
        surface=surface,
        summaries=rerank_result.summaries,
        composite_scores=rerank_result.composite_scores,
    )
    diagnostics = dict(surface.retrieval_diagnostics)
    diagnostics.update(dict(knowledge.retrieval_diagnostics or {}))
    diagnostics["expert_query_seed"] = expert_query_seed
    diagnostics["expert_query_seed_origin"] = expert_query_seed_origin
    diagnostics["expert_search_top_k"] = search_top_k
    diagnostics["expert_rerank"] = dict(rerank_result.diagnostics)
    surface = surface.__class__(
        groups=surface.groups,
        ungrouped=surface.ungrouped,
        total_available=surface.total_available,
        has_more=surface.has_more,
        next_offset=surface.next_offset,
        retrieval_diagnostics=diagnostics,
    )
    return HTTPStatus.OK, build_expert_panel_payload(surface=surface, trace_id=trace_id), None


def run_citation_interpretations_request(payload: dict, *, deps: dict):
    deps["warn_missing_active_index_generation"]()
    citation_payload = payload.get("citation")
    if not isinstance(citation_payload, dict):
        return HTTPStatus.BAD_REQUEST, {"error": "`citation` es obligatorio y debe ser objeto."}, None
    citation_doc_id = str(citation_payload.get("doc_id", "")).strip()
    if not citation_doc_id:
        return HTTPStatus.BAD_REQUEST, {"error": "`citation.doc_id` es obligatorio."}, None
    citation_row = deps["find_document_index_row"](citation_doc_id)
    if citation_row is None:
        return HTTPStatus.NOT_FOUND, {"error": "citation_not_found"}, None
    raw_message_context = payload.get("message_context")
    if raw_message_context is not None and not isinstance(raw_message_context, str):
        return HTTPStatus.BAD_REQUEST, {"error": "`message_context` debe ser texto si se envia."}, None
    message_context = str(raw_message_context or "").strip()
    assistant_answer = payload.get("assistant_answer")
    if assistant_answer is not None and not isinstance(assistant_answer, str):
        return HTTPStatus.BAD_REQUEST, {"error": "`assistant_answer` debe ser texto si se envia."}, None
    assistant_answer = str(assistant_answer or "").strip()
    top_k = payload.get("top_k", CITATION_INTERPRETATIONS_DEFAULT_TOP_K)
    if not isinstance(top_k, int):
        top_k = CITATION_INTERPRETATIONS_DEFAULT_TOP_K
    top_k = min(max(top_k, 1), CITATION_INTERPRETATIONS_MAX_TOP_K)
    process_limit = _coerce_non_negative_int(payload.get("process_limit", CITATION_INTERPRETATIONS_DEFAULT_PROCESS_LIMIT), default=CITATION_INTERPRETATIONS_DEFAULT_PROCESS_LIMIT)
    offset = _coerce_non_negative_int(payload.get("offset", 0), default=0)

    query_seed = deps["build_interpretation_query_seed"](
        citation=citation_payload,
        index_row=citation_row,
        message_context=message_context,
        assistant_answer=assistant_answer,
    )
    if not query_seed:
        query_seed = str(citation_row.get("relative_path", "")).strip() or citation_doc_id
    requested_refs: list[str] = []
    for bucket in (
        citation_row.get("normative_refs", ()) or (),
        citation_row.get("reference_identity_keys", ()) or (),
        citation_row.get("mentioned_reference_keys", ()) or (),
    ):
        for item in bucket:
            clean = str(item or "").strip()
            if clean:
                requested_refs.append(clean)
    decision_frame = build_decision_frame(
        question=message_context,
        assistant_answer=assistant_answer,
        citation_label=str(
            citation_payload.get("source_label")
            or citation_payload.get("legal_reference")
            or citation_row.get("relative_path")
            or citation_doc_id
        ).strip(),
        requested_refs=requested_refs,
    )
    topic_raw = str(citation_payload.get("topic") or citation_row.get("topic") or payload.get("topic") or "").strip()
    topic_key = deps["normalize_topic_key"](topic_raw) if topic_raw else None
    if topic_key and topic_key not in deps["supported_topics"]:
        topic_key = None
    pais = deps["normalize_pais"](
        citation_payload.get("pais") or citation_row.get("pais") or payload.get("pais") or "colombia"
    ) or "colombia"
    trace_id = str(payload.get("trace_id", "")).strip() or None

    try:
        knowledge = _retrieve_interpretation_docs(
            query=query_seed,
            top_k=max(top_k, offset + (process_limit if process_limit > 0 else top_k) + 12, 18),
            pais=pais,
            topic=topic_key,
            deps=deps,
        )
    except Exception as exc:  # noqa: BLE001
        return HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "citation_interpretations_failed", "details": str(exc)}, None

    docs = deps["dedupe_interpretation_docs"](list(knowledge.docs_selected), limit=max(top_k, 18))
    runtimes = [runtime for doc in docs if (runtime := _build_runtime_for_doc(doc, deps=deps)) is not None]
    surface = synthesize_citation_interpretations(
        runtimes=runtimes,
        frame=decision_frame,
        offset=offset,
        process_limit=process_limit,
        logical_doc_id=deps["logical_doc_id"],
        expert_card_summary=deps["expert_card_summary"],
        summarize_snippet=deps["summarize_snippet"],
        extended_excerpt=deps.get("extended_excerpt"),
    )
    diagnostics = dict(surface.retrieval_diagnostics)
    diagnostics.update(dict(knowledge.retrieval_diagnostics or {}))
    surface = surface.__class__(
        interpretations=surface.interpretations,
        total_available=surface.total_available,
        has_more=surface.has_more,
        next_offset=surface.next_offset,
        retrieval_diagnostics=diagnostics,
    )
    return HTTPStatus.OK, build_citation_interpretations_payload(
        surface=surface,
        citation_doc_id=citation_doc_id,
        query_seed=query_seed,
        trace_id=trace_id,
    ), None


def run_interpretation_summary_request(payload: dict, *, deps: dict):
    deps["warn_missing_active_index_generation"]()
    citation_payload = payload.get("citation")
    interpretation_payload = payload.get("interpretation")
    if not isinstance(citation_payload, dict):
        return HTTPStatus.BAD_REQUEST, {"error": "`citation` es obligatorio y debe ser objeto."}, None
    if not isinstance(interpretation_payload, dict):
        return HTTPStatus.BAD_REQUEST, {"error": "`interpretation` es obligatorio y debe ser objeto."}, None

    citation_doc_id = str(citation_payload.get("doc_id", "")).strip()
    interpretation_doc_id = str(interpretation_payload.get("doc_id", "")).strip()
    if not citation_doc_id:
        return HTTPStatus.BAD_REQUEST, {"error": "`citation.doc_id` es obligatorio."}, None
    if not interpretation_doc_id:
        return HTTPStatus.BAD_REQUEST, {"error": "`interpretation.doc_id` es obligatorio."}, None
    citation_row = deps["find_document_index_row"](citation_doc_id)
    if citation_row is None:
        return HTTPStatus.NOT_FOUND, {"error": "citation_not_found"}, None
    interpretation_row = deps["find_document_index_row"](interpretation_doc_id)
    if interpretation_row is None:
        return HTTPStatus.NOT_FOUND, {"error": "interpretation_not_found"}, None

    corpus_text, interpretation_row_with_view = deps["load_doc_corpus_text"](interpretation_doc_id, prefer_original=True)
    if not corpus_text:
        return HTTPStatus.NOT_FOUND, {"error": "interpretation_corpus_unavailable"}, None

    citation_public = deps["build_public_citation_from_row"](citation_row)
    interpretation_public = deps["build_public_citation_from_row"](interpretation_row)
    selected_external_link = _sanitize_http_url(
        str(payload.get("selected_link") or interpretation_payload.get("selected_link") or interpretation_payload.get("url") or "")
    )
    citation_label = str(
        citation_payload.get("source_label")
        or citation_payload.get("legal_reference")
        or citation_public.get("source_label")
        or citation_public.get("legal_reference")
        or citation_doc_id
    ).strip()
    interpretation_title = str(
        interpretation_payload.get("title")
        or interpretation_public.get("source_label")
        or interpretation_public.get("legal_reference")
        or interpretation_doc_id
    ).strip()
    message_context = str(payload.get("message_context", "")).strip()
    trace_id = str(payload.get("trace_id", "")).strip() or str(uuid4())
    corpus_excerpt = deps["clip_session_content"](corpus_text, max_chars=18000)
    prompt = build_interpretation_summary_prompt(
        citation_label=citation_label,
        interpretation_title=interpretation_title,
        message_context=message_context,
        selected_external_link=selected_external_link,
        corpus_excerpt=corpus_excerpt,
    )

    llm_runtime = {}
    try:
        llm_text, llm_diag = deps["generate_llm_strict"](
            prompt,
            runtime_config_path=deps["llm_runtime_config_path"],
            trace_id=trace_id,
        )
        summary_markdown = str(llm_text or "").strip()
        if not summary_markdown:
            raise ValueError("llm_empty")
        llm_runtime = {
            "model": llm_diag.get("selected_model"),
            "selected_type": llm_diag.get("selected_type"),
            "selected_provider": llm_diag.get("selected_provider"),
            "attempts": list(llm_diag.get("attempts") or []),
            "token_usage": dict(llm_diag.get("token_usage") or {}),
        }
        mode = "llm"
    except Exception:
        summary_markdown = deps["build_extractive_interpretation_summary"](
            corpus_text=corpus_text,
            citation_label=citation_label,
            interpretation_title=interpretation_title,
        )
        mode = INTERPRETATION_SUMMARY_FALLBACK_MODE

    surface = InterpretationSummarySurface(
        mode=mode,
        summary_markdown=summary_markdown,
        grounding={
            "citation": citation_public,
            "interpretation": interpretation_public,
            "selected_external_link": selected_external_link,
            "interpretation_view": str((interpretation_row_with_view or {}).get("__selected_view", "normalized")),
        },
        llm_runtime=llm_runtime,
    )
    return HTTPStatus.OK, build_interpretation_summary_payload(surface=surface, trace_id=trace_id), None


def run_expert_panel_enhance_request(payload: dict, *, deps: dict):
    trace_id = str(payload.get("trace_id", "")).strip() or str(uuid4())
    message = str(payload.get("message", "")).strip()
    assistant_answer = str(payload.get("assistant_answer", "")).strip()
    if not message:
        return HTTPStatus.BAD_REQUEST, {"error": "Campo `message` requerido."}, None
    cards = payload.get("cards", [])
    if not isinstance(cards, list) or len(cards) == 0:
        return HTTPStatus.BAD_REQUEST, {"error": "Campo `cards` requerido (array no vacío)."}, None

    clipped_message = message[:2000]
    clipped_answer = assistant_answer[:2000]
    card_blocks: list[str] = []
    card_ids: list[str] = []
    for idx, card in enumerate(cards[:EXPERT_PANEL_ENHANCE_MAX_CARDS], start=1):
        card_id = str(card.get("card_id", "")).strip() or f"card_{idx}"
        card_ids.append(card_id)
        snippets = card.get("snippets", [])
        if not isinstance(snippets, list):
            snippets = []
        excerpts = [
            str(item.get("card_summary", "") or item.get("snippet", "")).strip()[:300]
            for item in snippets[:3]
            if str(item.get("card_summary", "") or item.get("snippet", "")).strip()
        ]
        excerpts_block = "\n".join(f"  - {item}" for item in excerpts) if excerpts else "  (sin extractos)"
        card_blocks.append(
            f"TARJETA {idx} (id: {card_id}):\n"
            f"  clasificación: {str(card.get('classification', '')).strip() or 'N/A'}\n"
            f"  referencia: {str(card.get('article_ref', '')).strip() or 'N/A'}\n"
            f"  señal: {str(card.get('summary_signal', '')).strip() or 'N/A'}\n"
            f"  señal dominante: {str(card.get('dominant_signal', '')).strip() or 'neutral'}\n"
            f"  extractos fuente:\n{excerpts_block}"
        )
    prompt = build_expert_enhance_prompt(
        clipped_message=clipped_message,
        clipped_answer=clipped_answer,
        cards_context="\n\n".join(card_blocks),
    )
    llm_runtime = {}
    try:
        llm_text, llm_diag = deps["generate_llm_strict"](
            prompt,
            runtime_config_path=deps["llm_runtime_config_path"],
            trace_id=f"{trace_id}:expert-enhance",
        )
        cleaned = str(llm_text or "").strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.find("\n")
            if first_newline != -1:
                cleaned = cleaned[first_newline + 1 :]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        parsed = json.loads(cleaned)
        if not isinstance(parsed, list):
            parsed = [parsed]
        enhancements = []
        for idx, item in enumerate(parsed[:EXPERT_PANEL_ENHANCE_MAX_CARDS]):
            if not isinstance(item, dict):
                continue
            raw_relevante = item.get("es_relevante", True)
            es_relevante = bool(raw_relevante) if not isinstance(raw_relevante, str) else raw_relevante.lower().strip() not in {"false", "no", "0", ""}
            posible_relevancia_raw = str(item.get("posible_relevancia", "")).strip()
            if posible_relevancia_raw.lower().startswith("no aplica"):
                es_relevante = False
            enhancements.append(
                ExpertEnhancement(
                    card_id=str(item.get("card_id", card_ids[idx] if idx < len(card_ids) else f"card_{idx + 1}")).strip(),
                    es_relevante=es_relevante,
                    posible_relevancia=posible_relevancia_raw,
                    resumen_nutshell=str(item.get("resumen_nutshell", "")).strip(),
                )
            )
        llm_runtime = {
            "mode": "llm",
            "model": llm_diag.get("selected_model"),
            "token_usage": dict(llm_diag.get("token_usage") or {}),
        }
    except Exception:
        enhancements = tuple(
            ExpertEnhancement(
                card_id=str(item["card_id"]).strip(),
                es_relevante=bool(item["es_relevante"]),
                posible_relevancia=str(item["posible_relevancia"]).strip(),
                resumen_nutshell=str(item["resumen_nutshell"]).strip(),
            )
            for item in build_fallback_expert_enhancements(cards=cards)
        )
        llm_runtime = {"mode": EXPERT_PANEL_ENHANCE_FALLBACK_MODE}
        return HTTPStatus.OK, build_expert_panel_enhancements_payload(
            enhancements=enhancements,
            llm_runtime=llm_runtime,
            trace_id=trace_id,
        ), None

    return HTTPStatus.OK, build_expert_panel_enhancements_payload(
        enhancements=tuple(enhancements),
        llm_runtime=llm_runtime,
        trace_id=trace_id,
    ), None


def run_expert_panel_explore_request(payload: dict, *, deps: dict):
    trace_id = str(payload.get("trace_id", "")).strip() or str(uuid4())
    mode = str(payload.get("mode", "summary")).strip().lower()
    if mode not in {"summary", "deep"}:
        mode = "summary"
    message = str(payload.get("message", "")).strip()
    if not message:
        return HTTPStatus.BAD_REQUEST, {"error": "Campo `message` requerido."}, None
    assistant_answer = str(payload.get("assistant_answer", "")).strip()
    classification = str(payload.get("classification", "")).strip()
    article_ref = str(payload.get("article_ref", "")).strip()
    summary_signal = str(payload.get("summary_signal", "")).strip()
    snippets = payload.get("snippets", [])
    if not isinstance(snippets, list):
        snippets = []
    source_excerpts = []
    for idx, snippet in enumerate(snippets[:EXPERT_PANEL_EXPLORE_MAX_SNIPPETS], start=1):
        authority = str(snippet.get("authority", "")).strip() or f"Fuente {idx}"
        card_summary = str(snippet.get("card_summary", "")).strip()
        snippet_text = str(snippet.get("snippet", "")).strip()
        position = str(snippet.get("position_signal", "")).strip()
        excerpt = card_summary or snippet_text
        if excerpt:
            source_excerpts.append(f"[Fuente {idx}: {authority}] (señal: {position or 'neutral'})\n{excerpt}")
    sources_block = "\n\n".join(source_excerpts) if source_excerpts else "Sin fuentes disponibles."
    prompt = build_expert_explore_prompt(
        mode=mode,
        message=message,
        assistant_answer=assistant_answer,
        classification=classification,
        article_ref=article_ref,
        summary_signal=summary_signal,
        sources_block=sources_block,
    )
    try:
        llm_text, llm_diag = deps["generate_llm_strict"](
            prompt,
            runtime_config_path=deps["llm_runtime_config_path"],
            trace_id=f"{trace_id}:expert-explore:{mode}",
        )
        content = str(llm_text or "").strip()
        if not content:
            raise ValueError("expert_explore_empty_response")
        llm_runtime = {
            "mode": "llm",
            "model": llm_diag.get("selected_model"),
            "token_usage": dict(llm_diag.get("token_usage") or {}),
        }
    except Exception:
        content = build_fallback_expert_explore_content(
            mode=mode,
            message=message,
            classification=classification,
            article_ref=article_ref,
            summary_signal=summary_signal,
            snippets=snippets,
        )
        llm_runtime = {"mode": EXPERT_PANEL_EXPLORE_FALLBACK_MODE}
    return HTTPStatus.OK, build_expert_panel_explore_payload(
        mode=mode,
        content=content,
        llm_runtime=llm_runtime,
        trace_id=trace_id,
    ), None
