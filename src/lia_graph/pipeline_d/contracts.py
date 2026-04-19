from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..contracts import Citation


@dataclass(frozen=True)
class PlannerEntryPoint:
    kind: str
    lookup_value: str
    source: str
    confidence: float = 0.0
    label: str | None = None
    resolved_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "lookup_value": self.lookup_value,
            "source": self.source,
            "confidence": round(float(self.confidence), 4),
            "label": self.label,
            "resolved_key": self.resolved_key,
        }


@dataclass(frozen=True)
class TraversalBudget:
    max_hops: int
    max_nodes: int
    max_edges: int
    max_paths: int
    max_support_documents: int

    def to_dict(self) -> dict[str, int]:
        return {
            "max_hops": int(self.max_hops),
            "max_nodes": int(self.max_nodes),
            "max_edges": int(self.max_edges),
            "max_paths": int(self.max_paths),
            "max_support_documents": int(self.max_support_documents),
        }


@dataclass(frozen=True)
class EvidenceBundleShape:
    primary_article_limit: int
    connected_article_limit: int
    related_reform_limit: int
    support_document_limit: int
    snippet_char_limit: int = 280

    def to_dict(self) -> dict[str, int]:
        return {
            "primary_article_limit": int(self.primary_article_limit),
            "connected_article_limit": int(self.connected_article_limit),
            "related_reform_limit": int(self.related_reform_limit),
            "support_document_limit": int(self.support_document_limit),
            "snippet_char_limit": int(self.snippet_char_limit),
        }


@dataclass(frozen=True)
class GraphTemporalContext:
    consulta_date: str | None = None
    operation_date: str | None = None
    cutoff_date: str | None = None
    cutoff_source: str | None = None
    scope_mode: str = "current"
    historical_query_intent: bool = False
    requested_period_label: str | None = None
    requested_period_source: str | None = None
    anchor_reform_keys: tuple[str, ...] = ()
    anchor_reform_labels: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "consulta_date": self.consulta_date,
            "operation_date": self.operation_date,
            "cutoff_date": self.cutoff_date,
            "cutoff_source": self.cutoff_source,
            "scope_mode": self.scope_mode,
            "historical_query_intent": bool(self.historical_query_intent),
            "requested_period_label": self.requested_period_label,
            "requested_period_source": self.requested_period_source,
            "anchor_reform_keys": list(self.anchor_reform_keys),
            "anchor_reform_labels": list(self.anchor_reform_labels),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class GraphRetrievalPlan:
    query_mode: str
    entry_points: tuple[PlannerEntryPoint, ...]
    traversal_budget: TraversalBudget
    evidence_bundle_shape: EvidenceBundleShape
    temporal_context: GraphTemporalContext = field(default_factory=GraphTemporalContext)
    topic_hints: tuple[str, ...] = ()
    planner_notes: tuple[str, ...] = ()
    sub_questions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_mode": self.query_mode,
            "entry_points": [item.to_dict() for item in self.entry_points],
            "traversal_budget": self.traversal_budget.to_dict(),
            "evidence_bundle_shape": self.evidence_bundle_shape.to_dict(),
            "temporal_context": self.temporal_context.to_dict(),
            "topic_hints": list(self.topic_hints),
            "planner_notes": list(self.planner_notes),
            "sub_questions": list(self.sub_questions),
        }


@dataclass(frozen=True)
class GraphPathStep:
    edge_kind: str
    direction: str
    from_node_kind: str
    from_node_key: str
    to_node_kind: str
    to_node_key: str

    def to_dict(self) -> dict[str, str]:
        return {
            "edge_kind": self.edge_kind,
            "direction": self.direction,
            "from_node_kind": self.from_node_kind,
            "from_node_key": self.from_node_key,
            "to_node_kind": self.to_node_kind,
            "to_node_key": self.to_node_key,
        }


@dataclass(frozen=True)
class GraphEvidenceItem:
    node_kind: str
    node_key: str
    title: str
    excerpt: str
    source_path: str | None
    score: float
    hop_distance: int
    why: str | None = None
    relation_path: tuple[GraphPathStep, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_kind": self.node_kind,
            "node_key": self.node_key,
            "title": self.title,
            "excerpt": self.excerpt,
            "source_path": self.source_path,
            "score": round(float(self.score), 4),
            "hop_distance": int(self.hop_distance),
            "why": self.why,
            "relation_path": [step.to_dict() for step in self.relation_path],
        }


@dataclass(frozen=True)
class GraphSupportDocument:
    relative_path: str
    source_path: str
    title_hint: str
    family: str | None
    knowledge_class: str | None
    topic_key: str | None
    subtopic_key: str | None
    canonical_blessing_status: str | None
    graph_target: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "source_path": self.source_path,
            "title_hint": self.title_hint,
            "family": self.family,
            "knowledge_class": self.knowledge_class,
            "topic_key": self.topic_key,
            "subtopic_key": self.subtopic_key,
            "canonical_blessing_status": self.canonical_blessing_status,
            "graph_target": self.graph_target,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class GraphEvidenceBundle:
    primary_articles: tuple[GraphEvidenceItem, ...]
    connected_articles: tuple[GraphEvidenceItem, ...]
    related_reforms: tuple[GraphEvidenceItem, ...]
    support_documents: tuple[GraphSupportDocument, ...]
    citations: tuple[Citation, ...]
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_articles": [item.to_dict() for item in self.primary_articles],
            "connected_articles": [item.to_dict() for item in self.connected_articles],
            "related_reforms": [item.to_dict() for item in self.related_reforms],
            "support_documents": [item.to_dict() for item in self.support_documents],
            "citations": [citation.to_public_dict() for citation in self.citations],
            "diagnostics": dict(self.diagnostics),
        }
