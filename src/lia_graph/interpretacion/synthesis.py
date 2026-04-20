from __future__ import annotations

from .shared import (
    CitationInterpretationsSurface,
    ExpertPanelSurface,
    InterpretationCard,
    InterpretationDocRuntime,
)
from .synthesis_helpers import (
    build_expert_panel_page,
    build_interpretation_candidate,
    classify_expert_groups,
    extract_position_signal,
    select_interpretation_candidates,
)


def _build_interpretation_card(
    *,
    runtime: InterpretationDocRuntime,
    ranked,
    logical_doc_id,
    expert_card_summary,
    summarize_snippet,
    extended_excerpt,
) -> InterpretationCard:
    citation = dict(runtime.citation_payload or {})
    title = str(
        citation.get("source_label")
        or citation.get("legal_reference")
        or runtime.doc.relative_path
        or runtime.doc.doc_id
    ).strip() or runtime.doc.doc_id
    card_summary = str(expert_card_summary(runtime.corpus_text or "", max_chars=240) or "").strip()
    snippet = str(summarize_snippet(runtime.corpus_text or "", max_chars=360) or "").strip()
    extended = str(extended_excerpt(runtime.corpus_text or "", max_chars=2500) or "").strip() if extended_excerpt else ""
    position_signal = extract_position_signal(f"{card_summary}\n{snippet}\n{runtime.corpus_text[:1200]}")
    return InterpretationCard(
        doc_id=runtime.doc.doc_id,
        source_doc_id=runtime.doc.doc_id,
        logical_doc_id=str(logical_doc_id(runtime.doc.doc_id) or "").strip(),
        authority=str(citation.get("authority", "") or runtime.doc.authority or "Fuente profesional").strip(),
        title=title,
        snippet=snippet,
        position_signal=position_signal,
        relevance_score=float(ranked.total_score or 0.0),
        trust_tier=str(runtime.doc.trust_tier or "medium").strip() or "medium",
        provider_links=tuple(dict(item) for item in runtime.provider_links),
        providers=tuple(dict(item) for item in runtime.providers),
        source_view_url=str(citation.get("source_view_url", "")).strip() or None,
        official_url=str(citation.get("official_url", "")).strip() or None,
        open_url=str(citation.get("open_url", "")).strip() or None,
        card_summary=card_summary,
        extended_excerpt=extended,
        requested_match=bool(ranked.requested_match),
        selection_reason=str(ranked.selection_reason or "").strip(),
        core_ref_matches=tuple(ranked.core_ref_matches or ()),
        knowledge_class=str(citation.get("knowledge_class", "")).strip(),
        source_type=str(citation.get("source_type", "")).strip(),
        expanded_refs=tuple(ranked.candidate.expanded_refs or ()),
    )


def synthesize_expert_panel(
    *,
    runtimes: list[InterpretationDocRuntime],
    frame,
    requested_refs: set[str],
    offset: int,
    process_limit: int,
    logical_doc_id,
    expert_card_summary,
    summarize_snippet,
    extended_excerpt=None,
) -> ExpertPanelSurface:
    candidates = [
        build_interpretation_candidate(
            doc=runtime.doc,
            row=runtime.row,
            corpus_text=runtime.corpus_text,
        )
        for runtime in runtimes
    ]
    selection = select_interpretation_candidates(candidates, frame=frame, offset=0, limit=0)
    runtime_by_doc_id = {runtime.doc.doc_id: runtime for runtime in runtimes}
    ordered_cards = [
        _build_interpretation_card(
            runtime=runtime_by_doc_id[ranked.candidate.doc.doc_id],
            ranked=ranked,
            logical_doc_id=logical_doc_id,
            expert_card_summary=expert_card_summary,
            summarize_snippet=summarize_snippet,
            extended_excerpt=extended_excerpt,
        )
        for ranked in selection.items
        if ranked.candidate.doc.doc_id in runtime_by_doc_id
    ]
    groups, ungrouped = classify_expert_groups(ordered_cards)
    page_groups, page_ungrouped, total_available, has_more, next_offset = build_expert_panel_page(
        groups=groups,
        ungrouped=ungrouped,
        requested_refs=requested_refs,
        offset=offset,
        limit=process_limit,
    )
    diagnostics = dict(selection.diagnostics)
    diagnostics["grouped_items"] = len(groups)
    diagnostics["ungrouped_items"] = len(ungrouped)
    return ExpertPanelSurface(
        groups=page_groups,
        ungrouped=page_ungrouped,
        total_available=total_available,
        has_more=has_more,
        next_offset=next_offset,
        retrieval_diagnostics=diagnostics,
    )


def synthesize_citation_interpretations(
    *,
    runtimes: list[InterpretationDocRuntime],
    frame,
    offset: int,
    process_limit: int,
    logical_doc_id,
    expert_card_summary,
    summarize_snippet,
    extended_excerpt=None,
) -> CitationInterpretationsSurface:
    candidates = [
        build_interpretation_candidate(
            doc=runtime.doc,
            row=runtime.row,
            corpus_text=runtime.corpus_text,
        )
        for runtime in runtimes
    ]
    selection = select_interpretation_candidates(candidates, frame=frame, offset=offset, limit=process_limit)
    runtime_by_doc_id = {runtime.doc.doc_id: runtime for runtime in runtimes}
    cards = tuple(
        _build_interpretation_card(
            runtime=runtime_by_doc_id[ranked.candidate.doc.doc_id],
            ranked=ranked,
            logical_doc_id=logical_doc_id,
            expert_card_summary=expert_card_summary,
            summarize_snippet=summarize_snippet,
            extended_excerpt=extended_excerpt,
        )
        for ranked in selection.page
        if ranked.candidate.doc.doc_id in runtime_by_doc_id
    )
    return CitationInterpretationsSurface(
        interpretations=cards,
        total_available=selection.total_available,
        has_more=selection.has_more,
        next_offset=selection.next_offset,
        retrieval_diagnostics=dict(selection.diagnostics),
    )
