"""Graph load scaffolds for parsed regulatory content."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable, Mapping

from ..graph.client import GraphClient, GraphQueryResult, GraphWriteStatement
from ..graph.schema import (
    EdgeKind,
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
class SubtopicBinding:
    """Lightweight tuple tying an article to a curated SubTopic anchor.

    Consumed by :func:`build_graph_load_plan` to emit one SubTopicNode +
    one HAS_SUBTOPIC edge per article that carries a resolved subtopic.
    Idempotency is handled by :func:`_dedupe_nodes` / :func:`_dedupe_edges`.
    """

    sub_topic_key: str
    parent_topic: str
    label: str


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
    article_subtopics: Mapping[str, SubtopicBinding] | None = None,
    article_topics: Mapping[str, str] | None = None,
) -> GraphLoadPlan:
    graph_schema = schema or (graph_client.schema if graph_client is not None else default_graph_schema())
    client = graph_client or GraphClient(schema=graph_schema)
    normalized_edges = normalize_classified_edges(articles, classified_edges)

    article_topics = article_topics or {}
    topic_keys_in_use = {
        str(v).strip() for v in article_topics.values() if v and str(v).strip()
    }
    for binding in (article_subtopics or {}).values():
        if binding and binding.parent_topic:
            topic_keys_in_use.add(str(binding.parent_topic).strip())

    nodes = _dedupe_nodes(
        list(_build_article_nodes(articles))
        + list(_build_reform_nodes(articles, normalized_edges))
        + list(_build_subtopic_nodes(article_subtopics or {}))
        + list(_build_topic_nodes(topic_keys_in_use))
    )
    subtopic_edges = _build_subtopic_edges(articles, article_subtopics or {})
    tema_edges = _build_article_tema_edges(articles, article_topics)
    subtema_de_edges = _build_static_subtema_de_edges(article_subtopics or {})
    edges = _dedupe_edges(
        list(edge.record for edge in normalized_edges)
        + list(subtopic_edges)
        + list(tema_edges)
        + list(subtema_de_edges)
    )
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


def build_graph_delta_plan(
    delta: object,
    *,
    delta_articles: tuple[ParsedArticle, ...] | list[ParsedArticle],
    delta_edges: tuple[ClassifiedEdge, ...] | list[ClassifiedEdge],
    retired_article_keys: Iterable[str] | None = None,
    promoted_dangling_edges: tuple[GraphEdgeRecord, ...] | list[GraphEdgeRecord] = (),
    schema: GraphSchema | None = None,
    graph_client: GraphClient | None = None,
    article_subtopics: Mapping[str, SubtopicBinding] | None = None,
    article_topics: Mapping[str, str] | None = None,
) -> GraphLoadPlan:
    """Build the targeted Falkor plan for a planned ``CorpusDelta``.

    Emits statements in dependency order:

    1. ``DETACH DELETE`` for every article key that belonged to a retired doc.
    2. ``DELETE`` outbound edges from every article key owned by a modified
       doc — preserves the node, wipes stale outbound references.
    3. MERGE for added + modified article nodes + reform nodes.
    4. MERGE for edges extracted from the delta articles, plus any edges
       promoted out of the dangling store.

    ``retired_article_keys`` is supplied by the orchestrator (Phase 6) after
    it queries Supabase for chunk-id prefixes owned by retired docs. Matches
    the approach used by the Supabase sink (`write_delta`'s Pass 2).

    Unchanged docs produce NO statements — that's the whole point of the
    additive path.
    """
    from .delta_planner import CorpusDelta  # local import to avoid cycle

    graph_schema = schema or (graph_client.schema if graph_client is not None else default_graph_schema())
    client = graph_client or GraphClient(schema=graph_schema)

    added_entries = tuple(getattr(delta, "added", ()) or ())
    modified_entries = tuple(getattr(delta, "modified", ()) or ())

    # Which article keys belong to modified docs? A fresh parse of the
    # modified doc yields its new article set; outbound edges for each of
    # those keys must be wiped before re-MERGE (Pass C in the sink).
    modified_doc_ids = {
        entry.doc_id for entry in modified_entries if entry.doc_id
    }
    modified_article_keys: set[str] = set()
    for article in delta_articles:
        # The loader doesn't know which doc_id an article belongs to without
        # help; callers must set article.source_path consistent with the
        # documents they passed to the sink. For Phase 5 purposes, every
        # article in `delta_articles` that also corresponds to a modified
        # doc will have its outbound edges wiped. Since the delta planner
        # uses relative_path as a key, we rely on the source_path <->
        # relative_path mapping being handled upstream: here we wipe every
        # article key that the caller named as belonging to a modified doc.
        pass
    # The orchestrator owns the source_path → doc_id mapping, so a stricter
    # design would have the caller pass in ``modified_article_keys`` too.
    # Phase 6 will wire this; Phase 5 accepts optional hints.
    modified_article_keys.update(
        getattr(delta, "modified_article_keys", ()) or ()
    )

    statements: list[GraphWriteStatement] = []

    # (1) DETACH DELETE for retired articles.
    retired_keys = tuple(retired_article_keys or ())
    for key in sorted({str(k) for k in retired_keys if k}):
        statements.append(client.stage_detach_delete(NodeKind.ARTICLE, key))

    # (2) DELETE outbound edges for modified-doc article keys.
    for key in sorted(modified_article_keys):
        statements.append(
            client.stage_delete_outbound_edges(NodeKind.ARTICLE, key)
        )

    # (3) + (4) MERGE nodes + edges for added + modified docs.
    normalized_edges = normalize_classified_edges(delta_articles, delta_edges)
    article_topics = article_topics or {}
    article_subtopics = article_subtopics or {}
    topic_keys_in_use = {
        str(v).strip() for v in article_topics.values() if v and str(v).strip()
    }
    for binding in article_subtopics.values():
        if binding and binding.parent_topic:
            topic_keys_in_use.add(str(binding.parent_topic).strip())
    nodes = _dedupe_nodes(
        list(_build_article_nodes(delta_articles))
        + list(_build_reform_nodes(delta_articles, normalized_edges))
        + list(_build_subtopic_nodes(article_subtopics))
        + list(_build_topic_nodes(topic_keys_in_use))
    )
    edges = _dedupe_edges(
        list(edge.record for edge in normalized_edges)
        + list(promoted_dangling_edges)
        + list(_build_subtopic_edges(delta_articles, article_subtopics))
        + list(_build_article_tema_edges(delta_articles, article_topics))
        + list(_build_static_subtema_de_edges(article_subtopics))
    )
    validation = validate_graph_records(nodes, edges, schema=graph_schema)

    for node in nodes:
        statements.append(client.stage_node(node))
    for edge in edges:
        statements.append(client.stage_edge(edge))

    warnings: list[str] = []
    if not retired_keys and not added_entries and not modified_entries:
        warnings.append(
            "build_graph_delta_plan received an empty delta; no statements emitted."
        )

    return GraphLoadPlan(
        schema=graph_schema,
        nodes=nodes,
        edges=edges,
        statements=tuple(statements),
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


def _build_topic_nodes(
    topic_keys: Iterable[str],
) -> tuple[GraphNodeRecord, ...]:
    """Emit one TopicNode per distinct key referenced by this run's articles.

    Pulls label + parent_key from ``topic_taxonomy.json`` via the canonical
    loader so the node properties match what the taxonomy module advertises.
    """
    from ..topic_taxonomy import get_topic_taxonomy_entry

    seen: dict[str, GraphNodeRecord] = {}
    for raw_key in topic_keys:
        if not raw_key:
            continue
        key = str(raw_key).strip()
        if not key or key in seen:
            continue
        entry = get_topic_taxonomy_entry(key)
        # Fall back to the raw key when the taxonomy hasn't heard of it —
        # the retriever can still use the anchor, and Phase-12 docs will
        # flag the orphan.
        label = getattr(entry, "label", None) or key
        parent = getattr(entry, "parent_key", None) or ""
        seen[key] = GraphNodeRecord(
            kind=NodeKind.TOPIC,
            key=key,
            properties={
                "topic_key": key,
                "label": label,
                "parent_key": parent,
            },
        )
    return tuple(seen[k] for k in sorted(seen))


def _build_static_subtema_de_edges(
    article_subtopics: Mapping[str, SubtopicBinding],
) -> tuple[GraphEdgeRecord, ...]:
    """Emit one static SubTopic→Topic edge per subtopic actually in use."""
    unique_pairs: dict[tuple[str, str], SubtopicBinding] = {}
    for binding in article_subtopics.values():
        if not binding.sub_topic_key or not binding.parent_topic:
            continue
        pair = (binding.sub_topic_key, binding.parent_topic)
        unique_pairs.setdefault(pair, binding)
    edges: list[GraphEdgeRecord] = []
    for (sub_key, parent) in sorted(unique_pairs):
        edges.append(
            GraphEdgeRecord(
                kind=EdgeKind.SUBTEMA_DE,
                source_kind=NodeKind.SUBTOPIC,
                source_key=sub_key,
                target_kind=NodeKind.TOPIC,
                target_key=parent,
                properties={},
            )
        )
    return tuple(edges)


def _build_article_tema_edges(
    articles: tuple[ParsedArticle, ...] | list[ParsedArticle],
    article_topics: Mapping[str, str],
) -> tuple[GraphEdgeRecord, ...]:
    """Emit TEMA edges: every article with a resolved topic → TopicNode."""
    if not article_topics:
        return ()
    article_keys = {article.article_key for article in articles}
    edges: list[GraphEdgeRecord] = []
    seen: set[tuple[str, str]] = set()
    for article_key, topic_key in article_topics.items():
        if not topic_key or article_key not in article_keys:
            continue
        pair = (article_key, str(topic_key))
        if pair in seen:
            continue
        seen.add(pair)
        edges.append(
            GraphEdgeRecord(
                kind=EdgeKind.TEMA,
                source_kind=NodeKind.ARTICLE,
                source_key=article_key,
                target_kind=NodeKind.TOPIC,
                target_key=str(topic_key),
                properties={},
            )
        )
    return tuple(edges)


def _build_subtopic_nodes(
    article_subtopics: Mapping[str, SubtopicBinding],
) -> tuple[GraphNodeRecord, ...]:
    unique: dict[str, SubtopicBinding] = {}
    for binding in article_subtopics.values():
        if not binding.sub_topic_key:
            continue
        unique.setdefault(binding.sub_topic_key, binding)
    nodes: list[GraphNodeRecord] = []
    for key, binding in sorted(unique.items()):
        nodes.append(
            GraphNodeRecord(
                kind=NodeKind.SUBTOPIC,
                key=binding.sub_topic_key,
                properties={
                    "sub_topic_key": binding.sub_topic_key,
                    "parent_topic": binding.parent_topic,
                    "label": binding.label,
                },
            )
        )
    return tuple(nodes)


def _build_subtopic_edges(
    articles: tuple[ParsedArticle, ...] | list[ParsedArticle],
    article_subtopics: Mapping[str, SubtopicBinding],
) -> tuple[GraphEdgeRecord, ...]:
    edges: list[GraphEdgeRecord] = []
    article_keys = {article.article_key for article in articles}
    for article_key, binding in article_subtopics.items():
        if not binding.sub_topic_key or article_key not in article_keys:
            continue
        edges.append(
            GraphEdgeRecord(
                kind=EdgeKind.HAS_SUBTOPIC,
                source_kind=NodeKind.ARTICLE,
                source_key=article_key,
                target_kind=NodeKind.SUBTOPIC,
                target_key=binding.sub_topic_key,
                properties={"parent_topic": binding.parent_topic},
            )
        )
    return tuple(edges)


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
