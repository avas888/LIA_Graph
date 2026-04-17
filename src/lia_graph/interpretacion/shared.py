from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..contracts.document import DocumentRecord


@dataclass(frozen=True)
class DecisionFrame:
    question: str
    assistant_answer: str
    citation_label: str
    core_refs: tuple[str, ...]
    form_entities: tuple[str, ...]
    normalized_text: str
    detected_topic: str | None = None
    keyword_cluster: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "assistant_answer": self.assistant_answer,
            "citation_label": self.citation_label,
            "core_refs": list(self.core_refs),
            "form_entities": list(self.form_entities),
            "detected_topic": self.detected_topic,
            "keyword_cluster": list(self.keyword_cluster),
        }


@dataclass(frozen=True)
class InterpretationCandidate:
    doc: DocumentRecord
    row: dict[str, Any] | None
    corpus_text: str
    provider_key: str
    expanded_refs: tuple[str, ...]
    form_entities: tuple[str, ...]
    off_topic_tags: tuple[str, ...]
    actionability_score: float


@dataclass(frozen=True)
class RankedInterpretation:
    candidate: InterpretationCandidate
    total_score: float
    requested_match: bool
    core_ref_matches: tuple[str, ...]
    penalties: tuple[str, ...]
    selection_reason: str

    @property
    def provider_key(self) -> str:
        return self.candidate.provider_key


@dataclass(frozen=True)
class RankedSelection:
    total_available: int
    items: tuple[RankedInterpretation, ...]
    page: tuple[RankedInterpretation, ...]
    next_offset: int | None
    has_more: bool
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class InterpretationDocRuntime:
    doc: DocumentRecord
    row: dict[str, Any] | None
    corpus_text: str
    citation_payload: dict[str, Any]
    providers: tuple[dict[str, Any], ...] = ()
    provider_links: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class InterpretationCard:
    doc_id: str
    source_doc_id: str = ""
    logical_doc_id: str = ""
    authority: str = ""
    title: str = ""
    snippet: str = ""
    position_signal: str = "neutral"
    relevance_score: float = 0.0
    trust_tier: str = "medium"
    provider_links: tuple[dict[str, Any], ...] = ()
    providers: tuple[dict[str, Any], ...] = ()
    source_view_url: str | None = None
    official_url: str | None = None
    open_url: str | None = None
    card_summary: str = ""
    summary_origin: str = "deterministic"
    summary_quality: str = "medium"
    source_hash: str = ""
    coverage_axes: tuple[str, ...] = ()
    requested_match: bool = False
    selection_reason: str = ""
    core_ref_matches: tuple[str, ...] = ()
    panel_rank: int | None = None
    knowledge_class: str = ""
    source_type: str = ""
    expanded_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source_doc_id": self.source_doc_id,
            "logical_doc_id": self.logical_doc_id,
            "authority": self.authority,
            "title": self.title,
            "snippet": self.snippet,
            "position_signal": self.position_signal,
            "relevance_score": self.relevance_score,
            "trust_tier": self.trust_tier,
            "provider_links": [dict(item) for item in self.provider_links],
            "providers": [dict(item) for item in self.providers],
            "source_view_url": self.source_view_url,
            "official_url": self.official_url,
            "open_url": self.open_url,
            "card_summary": self.card_summary,
            "summary_origin": self.summary_origin,
            "summary_quality": self.summary_quality,
            "source_hash": self.source_hash,
            "coverage_axes": list(self.coverage_axes),
            "requested_match": self.requested_match,
            "selection_reason": self.selection_reason,
            "core_ref_matches": list(self.core_ref_matches),
            "panel_rank": self.panel_rank,
            "knowledge_class": self.knowledge_class,
            "source_type": self.source_type,
        }


@dataclass(frozen=True)
class ExpertGroup:
    article_ref: str
    classification: str
    snippets: tuple[InterpretationCard, ...]
    summary_signal: str
    providers: tuple[dict[str, Any], ...] = ()
    summary_origin: str = "deterministic"
    summary_quality: str = "medium"
    relevance_score: float = 0.0
    coverage_axes: tuple[str, ...] = ()
    requested_match: bool = False
    selection_reason: str = ""
    panel_rank: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "article_ref": self.article_ref,
            "classification": self.classification,
            "summary_signal": self.summary_signal,
            "summary_origin": self.summary_origin,
            "summary_quality": self.summary_quality,
            "providers": [dict(item) for item in self.providers],
            "snippets": [item.to_dict() for item in self.snippets],
            "relevance_score": self.relevance_score,
            "coverage_axes": list(self.coverage_axes),
            "requested_match": self.requested_match,
            "selection_reason": self.selection_reason,
            "panel_rank": self.panel_rank,
        }


@dataclass(frozen=True)
class ExpertPanelSurface:
    groups: tuple[ExpertGroup, ...] = ()
    ungrouped: tuple[InterpretationCard, ...] = ()
    total_available: int = 0
    has_more: bool = False
    next_offset: int | None = None
    retrieval_diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CitationInterpretationsSurface:
    interpretations: tuple[InterpretationCard, ...] = ()
    total_available: int = 0
    has_more: bool = False
    next_offset: int | None = None
    retrieval_diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InterpretationSummarySurface:
    mode: str
    summary_markdown: str
    grounding: dict[str, Any]
    llm_runtime: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExpertEnhancement:
    card_id: str
    es_relevante: bool
    posible_relevancia: str
    resumen_nutshell: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "card_id": self.card_id,
            "es_relevante": self.es_relevante,
            "posible_relevancia": self.posible_relevancia,
            "resumen_nutshell": self.resumen_nutshell,
        }
