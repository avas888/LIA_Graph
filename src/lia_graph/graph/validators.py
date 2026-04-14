"""Validation helpers for graph schema and staged graph records."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Mapping

from .schema import GraphEdgeRecord, GraphNodeRecord, GraphSchema, default_graph_schema


@dataclass(frozen=True)
class GraphValidationIssue:
    code: str
    message: str
    severity: str = "error"
    details: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class GraphValidationReport:
    ok: bool
    graph_name: str
    node_count: int
    edge_count: int
    node_counts: Mapping[str, int]
    edge_counts: Mapping[str, int]
    orphan_node_keys: tuple[str, ...]
    issues: tuple[GraphValidationIssue, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "graph_name": self.graph_name,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "node_counts": dict(self.node_counts),
            "edge_counts": dict(self.edge_counts),
            "orphan_node_keys": list(self.orphan_node_keys),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def validate_graph_schema(schema: GraphSchema | None = None) -> tuple[GraphValidationIssue, ...]:
    graph_schema = schema or default_graph_schema()
    issues: list[GraphValidationIssue] = []
    for edge_kind, edge_type in graph_schema.edge_types.items():
        for node_kind in edge_type.source_kinds + edge_type.target_kinds:
            if node_kind not in graph_schema.node_types:
                issues.append(
                    GraphValidationIssue(
                        code="schema_unknown_node_kind",
                        message=(
                            f"{edge_kind.value} references missing node type {node_kind.value}."
                        ),
                        details={"edge_kind": edge_kind.value, "node_kind": node_kind.value},
                    )
                )
    return tuple(issues)


def validate_graph_records(
    nodes: tuple[GraphNodeRecord, ...] | list[GraphNodeRecord],
    edges: tuple[GraphEdgeRecord, ...] | list[GraphEdgeRecord],
    *,
    schema: GraphSchema | None = None,
) -> GraphValidationReport:
    graph_schema = schema or default_graph_schema()
    issues: list[GraphValidationIssue] = list(validate_graph_schema(graph_schema))

    seen_nodes: set[tuple[str, str]] = set()
    node_index: dict[tuple[str, str], GraphNodeRecord] = {}
    node_counts = Counter()
    edge_counts = Counter()
    incident_counts: defaultdict[tuple[str, str], int] = defaultdict(int)

    for record in nodes:
        key = (record.kind.value, record.key)
        node_counts[record.kind.value] += 1
        if key in seen_nodes:
            issues.append(
                GraphValidationIssue(
                    code="duplicate_node",
                    message=f"Duplicate node detected for {record.kind.value}:{record.key}.",
                    details={"kind": record.kind.value, "key": record.key},
                )
            )
            continue
        seen_nodes.add(key)
        node_index[key] = record
        try:
            graph_schema.validate_node_record(record)
        except ValueError as exc:
            issues.append(
                GraphValidationIssue(
                    code="invalid_node",
                    message=str(exc),
                    details={"kind": record.kind.value, "key": record.key},
                )
            )

    for record in edges:
        edge_counts[record.kind.value] += 1
        try:
            graph_schema.validate_edge_record(record)
        except ValueError as exc:
            issues.append(
                GraphValidationIssue(
                    code="invalid_edge",
                    message=str(exc),
                    details={
                        "kind": record.kind.value,
                        "source_key": record.source_key,
                        "target_key": record.target_key,
                    },
                )
            )
        source_ref = (record.source_kind.value, record.source_key)
        target_ref = (record.target_kind.value, record.target_key)
        if source_ref not in node_index:
            issues.append(
                GraphValidationIssue(
                    code="missing_edge_source",
                    message=(
                        f"Edge {record.kind.value} points to missing source "
                        f"{record.source_kind.value}:{record.source_key}."
                    ),
                    details={
                        "kind": record.kind.value,
                        "source_kind": record.source_kind.value,
                        "source_key": record.source_key,
                    },
                )
            )
        else:
            incident_counts[source_ref] += 1
        if target_ref not in node_index:
            issues.append(
                GraphValidationIssue(
                    code="missing_edge_target",
                    message=(
                        f"Edge {record.kind.value} points to missing target "
                        f"{record.target_kind.value}:{record.target_key}."
                    ),
                    details={
                        "kind": record.kind.value,
                        "target_kind": record.target_kind.value,
                        "target_key": record.target_key,
                    },
                )
            )
        else:
            incident_counts[target_ref] += 1

    orphan_node_keys = tuple(
        f"{kind}:{key}"
        for kind, key in sorted(seen_nodes)
        if incident_counts[(kind, key)] == 0
    )

    ok = not any(issue.severity == "error" for issue in issues)
    return GraphValidationReport(
        ok=ok,
        graph_name=graph_schema.graph_name,
        node_count=len(seen_nodes),
        edge_count=len(edges),
        node_counts=dict(sorted(node_counts.items())),
        edge_counts=dict(sorted(edge_counts.items())),
        orphan_node_keys=orphan_node_keys,
        issues=tuple(issues),
    )
