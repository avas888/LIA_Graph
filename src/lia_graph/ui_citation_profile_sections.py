"""Analysis excerpts + section builders for the citation-profile modal.

Extracted from `ui_citation_profile_builders.py` during granularize-v2
round 12d. This cluster owns the "deep content" of the modal — the
pieces that render below the facts strip:

  * ``_citation_profile_analysis_candidates`` — orders related-analysis
    rows by source-tier + authority relevance so the top excerpts
    surface in the original-text and expert sections.
  * ``_extract_locator_excerpt_from_text`` / ``_summarize_analysis_excerpt``
    — pull a locator-aware excerpt (article N paragraph) from the
    analysis body, then clip to a short, readable snippet.
  * ``_build_citation_profile_original_text_section`` — "Texto
    Normativo" section with the article body + source link.
  * ``_build_citation_profile_expert_section`` — "Interpretación
    Experta" section; the largest builder (206 LOC) — stitches
    expert-panel snippets + normativa-surface enrichment into a
    coherent prose block.
  * ``_build_citation_profile_sections`` — the orchestrator that
    combines the above into the final `sections` payload rendered by
    the modal's section cards.

All functions flow through the lazy ``_ui()`` accessor.
"""

from __future__ import annotations

import re
from typing import Any


def _ui() -> Any:
    """Lazy accessor for `lia_graph.ui_server` (avoids circular import)."""
    from . import ui_server as _mod
    return _mod



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
