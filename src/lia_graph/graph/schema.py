"""Typed schema scaffolds for the shared regulatory graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

DEFAULT_GRAPH_NAME = "LIA_REGULATORY_GRAPH"


class NodeKind(str, Enum):
    ARTICLE = "ArticleNode"
    REFORM = "ReformNode"
    CONCEPT = "ConceptNode"
    PARAMETER = "ParameterNode"


class EdgeKind(str, Enum):
    REFERENCES = "REFERENCES"
    MODIFIES = "MODIFIES"
    SUPERSEDES = "SUPERSEDES"
    EXCEPTION_TO = "EXCEPTION_TO"
    COMPUTATION_DEPENDS_ON = "COMPUTATION_DEPENDS_ON"
    REQUIRES = "REQUIRES"
    DEFINES = "DEFINES"
    PART_OF = "PART_OF"


@dataclass(frozen=True)
class GraphNodeType:
    label: NodeKind
    key_field: str
    description: str
    required_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class GraphEdgeType:
    label: EdgeKind
    source_kinds: tuple[NodeKind, ...]
    target_kinds: tuple[NodeKind, ...]
    description: str


@dataclass(frozen=True)
class GraphNodeRecord:
    kind: NodeKind
    key: str
    properties: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "key": self.key,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class GraphEdgeRecord:
    kind: EdgeKind
    source_kind: NodeKind
    source_key: str
    target_kind: NodeKind
    target_key: str
    properties: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "source_kind": self.source_kind.value,
            "source_key": self.source_key,
            "target_kind": self.target_kind.value,
            "target_key": self.target_key,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class GraphSchema:
    graph_name: str
    node_types: Mapping[NodeKind, GraphNodeType]
    edge_types: Mapping[EdgeKind, GraphEdgeType]

    def node_type(self, kind: NodeKind) -> GraphNodeType:
        return self.node_types[kind]

    def edge_type(self, kind: EdgeKind) -> GraphEdgeType:
        return self.edge_types[kind]

    def validate_node_record(self, record: GraphNodeRecord) -> None:
        if not record.key.strip():
            raise ValueError("Graph node keys must be non-empty.")
        node_type = self.node_type(record.kind)
        missing = [
            field_name
            for field_name in node_type.required_fields
            if record.properties.get(field_name) in (None, "", ())
        ]
        if missing:
            raise ValueError(
                f"Node {record.kind.value}:{record.key} missing required fields: {missing}"
            )

    def validate_edge_record(self, record: GraphEdgeRecord) -> None:
        if not record.source_key.strip() or not record.target_key.strip():
            raise ValueError("Graph edge endpoints must be non-empty.")
        edge_type = self.edge_type(record.kind)
        if record.source_kind not in edge_type.source_kinds:
            raise ValueError(
                f"{record.kind.value} cannot start from {record.source_kind.value}"
            )
        if record.target_kind not in edge_type.target_kinds:
            raise ValueError(
                f"{record.kind.value} cannot target {record.target_kind.value}"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "graph_name": self.graph_name,
            "node_types": {
                kind.value: {
                    "key_field": node_type.key_field,
                    "description": node_type.description,
                    "required_fields": list(node_type.required_fields),
                }
                for kind, node_type in self.node_types.items()
            },
            "edge_types": {
                kind.value: {
                    "source_kinds": [source_kind.value for source_kind in edge_type.source_kinds],
                    "target_kinds": [target_kind.value for target_kind in edge_type.target_kinds],
                    "description": edge_type.description,
                }
                for kind, edge_type in self.edge_types.items()
            },
        }


def default_graph_schema() -> GraphSchema:
    node_types = {
        NodeKind.ARTICLE: GraphNodeType(
            label=NodeKind.ARTICLE,
            key_field="article_id",
            description="Versionable normative unit from the shared regulatory corpus.",
            required_fields=("article_number", "heading", "text_current", "status"),
        ),
        NodeKind.REFORM: GraphNodeType(
            label=NodeKind.REFORM,
            key_field="reform_id",
            description="Normative act that changes or contextualizes article text.",
            required_fields=("citation",),
        ),
        NodeKind.CONCEPT: GraphNodeType(
            label=NodeKind.CONCEPT,
            key_field="concept_id",
            description="Canonical tax concept anchor used by graph traversal.",
            required_fields=("name",),
        ),
        NodeKind.PARAMETER: GraphNodeType(
            label=NodeKind.PARAMETER,
            key_field="parameter_id",
            description="Versioned fiscal or accounting parameters such as UVT values.",
            required_fields=("name", "value"),
        ),
    }

    article_targets = (NodeKind.ARTICLE, NodeKind.REFORM, NodeKind.CONCEPT, NodeKind.PARAMETER)
    edge_types = {
        EdgeKind.REFERENCES: GraphEdgeType(
            label=EdgeKind.REFERENCES,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM, NodeKind.CONCEPT),
            target_kinds=article_targets,
            description="Generic normative or conceptual reference.",
        ),
        EdgeKind.MODIFIES: GraphEdgeType(
            label=EdgeKind.MODIFIES,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            target_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            description="A reform chain or article text change.",
        ),
        EdgeKind.SUPERSEDES: GraphEdgeType(
            label=EdgeKind.SUPERSEDES,
            source_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            target_kinds=(NodeKind.ARTICLE, NodeKind.REFORM),
            description="A repeal or full replacement relationship.",
        ),
        EdgeKind.EXCEPTION_TO: GraphEdgeType(
            label=EdgeKind.EXCEPTION_TO,
            source_kinds=(NodeKind.ARTICLE,),
            target_kinds=(NodeKind.ARTICLE,),
            description="One article behaves as an exception to another.",
        ),
        EdgeKind.COMPUTATION_DEPENDS_ON: GraphEdgeType(
            label=EdgeKind.COMPUTATION_DEPENDS_ON,
            source_kinds=(NodeKind.ARTICLE,),
            target_kinds=(NodeKind.ARTICLE, NodeKind.PARAMETER),
            description="Computation order or formula dependency.",
        ),
        EdgeKind.REQUIRES: GraphEdgeType(
            label=EdgeKind.REQUIRES,
            source_kinds=(NodeKind.ARTICLE,),
            target_kinds=(NodeKind.ARTICLE, NodeKind.CONCEPT, NodeKind.PARAMETER),
            description="A requirement or prerequisite relationship.",
        ),
        EdgeKind.DEFINES: GraphEdgeType(
            label=EdgeKind.DEFINES,
            source_kinds=(NodeKind.ARTICLE, NodeKind.CONCEPT),
            target_kinds=(NodeKind.CONCEPT, NodeKind.ARTICLE),
            description="A legal or vocabulary definition relationship.",
        ),
        EdgeKind.PART_OF: GraphEdgeType(
            label=EdgeKind.PART_OF,
            source_kinds=(NodeKind.ARTICLE,),
            target_kinds=(NodeKind.CONCEPT,),
            description="Structural grouping between articles and topic anchors.",
        ),
    }

    return GraphSchema(
        graph_name=DEFAULT_GRAPH_NAME,
        node_types=node_types,
        edge_types=edge_types,
    )
