"""Graph load scaffolds for parsed regulatory content."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from ..graph.client import GraphClient, GraphQueryResult, GraphWriteStatement
from ..graph.schema import (
    GraphEdgeRecord,
    GraphNodeRecord,
    GraphSchema,
    NodeKind,
    default_graph_schema,
)
from ..graph.validators import GraphValidationReport, validate_graph_records
from .classifier import ClassifiedEdge
from .parser import ParsedArticle


@dataclass(frozen=True)
class GraphLoadPlan:
    schema: GraphSchema
    nodes: tuple[GraphNodeRecord, ...]
    edges: tuple[GraphEdgeRecord, ...]
    statements: tuple[GraphWriteStatement, ...]
    validation: GraphValidationReport
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema.to_dict(),
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "statements": [statement.to_dict() for statement in self.statements],
            "validation": self.validation.to_dict(),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class GraphLoadExecution:
    requested_execution: bool
    executed: bool
    results: tuple[GraphQueryResult, ...]
    plan: GraphLoadPlan
    connection: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        success_count = sum(1 for result in self.results if result.ok and not result.skipped)
        failure_count = sum(1 for result in self.results if not result.ok)
        skipped_count = sum(1 for result in self.results if result.skipped)
        return {
            "requested_execution": self.requested_execution,
            "executed": self.executed,
            "statement_count": len(self.plan.statements),
            "success_count": success_count,
            "failure_count": failure_count,
            "skipped_count": skipped_count,
            "connection": dict(self.connection),
            "results": [result.to_dict() for result in self.results],
            "plan": self.plan.to_dict(),
        }


def build_graph_load_plan(
    articles: tuple[ParsedArticle, ...] | list[ParsedArticle],
    classified_edges: tuple[ClassifiedEdge, ...] | list[ClassifiedEdge],
    *,
    schema: GraphSchema | None = None,
    graph_client: GraphClient | None = None,
) -> GraphLoadPlan:
    graph_schema = schema or (graph_client.schema if graph_client is not None else default_graph_schema())
    client = graph_client or GraphClient(schema=graph_schema)
    normalized_edges = normalize_classified_edges(articles, classified_edges)

    nodes = _dedupe_nodes(
        list(_build_article_nodes(articles))
        + list(_build_reform_nodes(articles, normalized_edges))
    )
    edges = _dedupe_edges(edge.record for edge in normalized_edges)
    validation = validate_graph_records(nodes, edges, schema=graph_schema)

    statements = tuple(client.stage_node(node) for node in nodes) + tuple(
        client.stage_edge(edge) for edge in edges
    )
    warnings: list[str] = []
    skipped_edge_count = len(classified_edges) - len(normalized_edges)
    if skipped_edge_count:
        warnings.append(
            "Skipped "
            f"{skipped_edge_count} unresolved ArticleNode edge(s) whose targets are not materialized "
            "in the current corpus snapshot."
        )
    if not client.config.is_configured:
        warnings.append("FALKORDB_URL is not configured; load plan is staged only.")
    return GraphLoadPlan(
        schema=graph_schema,
        nodes=nodes,
        edges=edges,
        statements=statements,
        validation=validation,
        warnings=tuple(warnings),
    )


def load_graph_plan(
    plan: GraphLoadPlan,
    *,
    graph_client: GraphClient | None = None,
    execute: bool = False,
    strict: bool = False,
) -> GraphLoadExecution:
    client = graph_client or (
        GraphClient.from_env(schema=plan.schema) if execute else GraphClient(schema=plan.schema)
    )
    if not execute:
        return GraphLoadExecution(
            requested_execution=False,
            executed=False,
            results=(),
            plan=plan,
            connection=client.config.to_dict(),
        )
    results = client.execute_many(plan.statements, strict=strict)
    return GraphLoadExecution(
        requested_execution=True,
        executed=any(not result.skipped and result.ok for result in results),
        results=results,
        plan=plan,
        connection=client.config.to_dict(),
    )


def _build_article_nodes(
    articles: tuple[ParsedArticle, ...] | list[ParsedArticle],
) -> tuple[GraphNodeRecord, ...]:
    return tuple(
        GraphNodeRecord(
            kind=NodeKind.ARTICLE,
            key=article.article_key,
            properties={
                "article_number": article.article_number,
                "heading": article.heading,
                "text_current": article.body or article.full_text,
                "status": article.status,
                "source_path": article.source_path,
                "paragraph_markers": list(article.paragraph_markers),
                "reform_references": list(article.reform_references),
                "annotations": list(article.annotations),
            },
        )
        for article in articles
    )


def _build_reform_nodes(
    articles: tuple[ParsedArticle, ...] | list[ParsedArticle],
    classified_edges: tuple[ClassifiedEdge, ...] | list[ClassifiedEdge],
) -> tuple[GraphNodeRecord, ...]:
    citations_by_key: dict[str, str] = {}
    for article in articles:
        for citation in article.reform_references:
            citations_by_key.setdefault(_normalize_reform_key(citation), citation)
    for edge in classified_edges:
        if edge.record.target_kind is not NodeKind.REFORM:
            continue
        raw_reference = str(edge.record.properties.get("raw_reference", "") or "").strip()
        citations_by_key.setdefault(edge.record.target_key, raw_reference or edge.record.target_key)
    return tuple(
        GraphNodeRecord(
            kind=NodeKind.REFORM,
            key=key,
            properties={"citation": citation},
        )
        for key, citation in sorted(citations_by_key.items())
    )


def normalize_classified_edges(
    articles: tuple[ParsedArticle, ...] | list[ParsedArticle],
    classified_edges: tuple[ClassifiedEdge, ...] | list[ClassifiedEdge],
) -> tuple[ClassifiedEdge, ...]:
    article_keys = {article.article_key for article in articles}
    return tuple(
        edge
        for edge in classified_edges
        if not (
            edge.record.target_kind is NodeKind.ARTICLE
            and edge.record.target_key not in article_keys
        )
    )


def _normalize_reform_key(citation: str) -> str:
    match = re.search(
        r"(?i)\b(?P<prefix>Ley|Decreto|Resoluci[oó]n)\s+(?P<number>\d+)(?:\s+de\s+(?P<year>\d{4}))?",
        citation,
    )
    if match is None:
        compact = "-".join(part for part in citation.upper().replace(".", " ").split())
        return compact.replace("Ó", "O")
    prefix = match.group("prefix").upper().replace("Ó", "O")
    number = match.group("number")
    year = match.group("year") or "s_f"
    return f"{prefix}-{number}-{year}"


def _dedupe_nodes(records: list[GraphNodeRecord]) -> tuple[GraphNodeRecord, ...]:
    dedup: dict[tuple[str, str], GraphNodeRecord] = {}
    for record in records:
        dedup[(record.kind.value, record.key)] = record
    return tuple(
        dedup[key] for key in sorted(dedup, key=lambda item: (item[0], item[1]))
    )


def _dedupe_edges(records: tuple[GraphEdgeRecord, ...] | list[GraphEdgeRecord]) -> tuple[GraphEdgeRecord, ...]:
    dedup: dict[tuple[str, str, str, str, str], GraphEdgeRecord] = {}
    for record in records:
        dedup[
            (
                record.kind.value,
                record.source_kind.value,
                record.source_key,
                record.target_kind.value,
                record.target_key,
            )
        ] = record
    return tuple(
        dedup[key]
        for key in sorted(dedup, key=lambda item: (item[2], item[0], item[4]))
    )
