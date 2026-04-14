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
    executed: bool
    results: tuple[GraphQueryResult, ...]
    plan: GraphLoadPlan

    def to_dict(self) -> dict[str, object]:
        return {
            "executed": self.executed,
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
    graph_schema = schema or default_graph_schema()
    client = graph_client or GraphClient(schema=graph_schema)

    nodes = _dedupe_nodes(
        list(_build_article_nodes(articles))
        + list(_build_reform_nodes(articles, classified_edges))
    )
    edges = _dedupe_edges(edge.record for edge in classified_edges)
    validation = validate_graph_records(nodes, edges, schema=graph_schema)

    statements = tuple(client.stage_node(node) for node in nodes) + tuple(
        client.stage_edge(edge) for edge in edges
    )
    warnings: list[str] = []
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
) -> GraphLoadExecution:
    client = graph_client or GraphClient(schema=plan.schema)
    if not execute:
        return GraphLoadExecution(executed=False, results=(), plan=plan)
    results = tuple(client.execute(statement) for statement in plan.statements)
    return GraphLoadExecution(executed=True, results=results, plan=plan)


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
