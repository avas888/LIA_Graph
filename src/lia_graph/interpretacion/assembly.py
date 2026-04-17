from __future__ import annotations

from typing import Any

from .shared import (
    CitationInterpretationsSurface,
    ExpertEnhancement,
    ExpertPanelSurface,
    InterpretationSummarySurface,
)


def build_expert_panel_payload(
    *,
    surface: ExpertPanelSurface,
    trace_id: str | None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "groups": [group.to_dict() for group in surface.groups],
        "ungrouped": [card.to_dict() for card in surface.ungrouped],
        "total_available": surface.total_available,
        "has_more": surface.has_more,
        "next_offset": surface.next_offset,
        "retrieval_diagnostics": dict(surface.retrieval_diagnostics),
        "trace_id": trace_id or None,
    }


def build_citation_interpretations_payload(
    *,
    surface: CitationInterpretationsSurface,
    citation_doc_id: str,
    query_seed: str,
    trace_id: str | None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "citation_doc_id": citation_doc_id,
        "query_seed": query_seed,
        "interpretations": [card.to_dict() for card in surface.interpretations],
        "total_available": surface.total_available,
        "has_more": surface.has_more,
        "next_offset": surface.next_offset,
        "retrieval_diagnostics": dict(surface.retrieval_diagnostics),
        "trace_id": trace_id or None,
    }


def build_interpretation_summary_payload(
    *,
    surface: InterpretationSummarySurface,
    trace_id: str | None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "mode": surface.mode,
        "summary_markdown": surface.summary_markdown,
        "grounding": dict(surface.grounding),
        "llm_runtime": dict(surface.llm_runtime),
        "trace_id": trace_id or None,
    }


def build_expert_panel_enhancements_payload(
    *,
    enhancements: tuple[ExpertEnhancement, ...],
    llm_runtime: dict[str, Any],
    trace_id: str | None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "enhancements": [item.to_dict() for item in enhancements],
        "llm_runtime": dict(llm_runtime),
        "trace_id": trace_id or None,
    }


def build_expert_panel_explore_payload(
    *,
    mode: str,
    content: str,
    llm_runtime: dict[str, Any],
    trace_id: str | None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "mode": mode,
        "content": content,
        "llm_runtime": dict(llm_runtime),
        "trace_id": trace_id or None,
    }
