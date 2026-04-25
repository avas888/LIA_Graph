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


def _is_article_node_eligible(article: ParsedArticle) -> bool:
    """Return True iff the article meets the Falkor ArticleNode schema.

    v4: ``article_number`` is no longer required — prose-only docs (whole-doc
    fallback parser output with empty article_number) are now eligible and
    get a doc-scoped graph key via ``_graph_article_key`` plus an
    ``is_prose_only=True`` property so Cypher consumers can filter cleanly.

    ``heading`` / ``text_current`` / ``status`` remain required; a blank on
    any of them still indicates a malformed parse that shouldn't enter the
    graph. See docs/next/ingestionfix_v4.md §5 Phase 1.
    """
    if not article:
        return False
    heading = str(article.heading or "").strip()
    text = str(article.body or article.full_text or "").strip()
    status = str(article.status or "").strip()
    return bool(heading and text and status)


def _graph_article_key(article: ParsedArticle) -> str:
    """Unique-per-doc key used as ``ArticleNode.key`` in Falkor.

    Distinct from ``ParsedArticle.article_key`` (which scopes Supabase
    ``chunk_id`` and must stay stable across v4 to avoid chunk churn).

    Behavior:

    * Prose-only articles (empty ``article_number``) — return
      ``f"whole::{source_path}"`` so each prose doc gets its own
      ArticleNode rather than colliding on the shared ``WHOLE_DOC_ARTICLE_KEY``
      ("doc") across the whole corpus.
    * Numbered articles — return ``article.article_key`` unchanged to preserve
      the existing 8,106 ArticleNodes' identity. Cross-doc collisions on
      numbered articles (e.g. Article 5 of Ley 100 vs Ley 300) are a
      separate pre-existing issue tracked as followup F8 in
      ``docs/next/ingestionfix_v4.md §8``.
    """
    number = str(getattr(article, "article_number", "") or "").strip()
    if not number:
        source = str(getattr(article, "source_path", "") or "").strip() or "unknown"
        return f"whole::{source}"
    return article.article_key


def _is_prose_only(article: ParsedArticle) -> bool:
    """True if the article is a whole-doc / section-fallback without an article number."""
    return not str(getattr(article, "article_number", "") or "").strip()


def _orphaning_article_keys(
    articles: "tuple[ParsedArticle, ...] | list[ParsedArticle]",
) -> set[str]:
    """Compute the set of ``article.article_key`` values whose endpoints
    would orphan in Cypher if used by a classified or promoted edge.

    Two distinct orphan cases:

    1. **Ineligible** — the article failed ``_is_article_node_eligible``, so
       no ArticleNode was staged. Any classified edge using its
       ``article_key`` (or its ``_graph_article_key``) hits a silent no-op
       MATCH in Cypher. Drop.
    2. **Remapped** (v4 new case) — the article is eligible, but its graph
       MERGE key differs from ``article.article_key`` (prose-only path:
       classifier sees ``"doc"``, graph uses ``"whole::source_path"``). An
       edge with endpoint = ``article.article_key`` would MATCH no node.
       Drop those too.

    Returning a single set means the existing filter helper can stay a simple
    "endpoint key ∈ set → drop" check without learning the new distinction.
    """
    out: set[str] = set()
    for a in articles:
        if not _is_article_node_eligible(a):
            # Pre-v4 case — both keys orphan.
            out.add(a.article_key)
            out.add(_graph_article_key(a))
            continue
        gkey = _graph_article_key(a)
        if gkey != a.article_key:
            # v4 remap case — only the raw key orphans; graph key resolves.
            out.add(a.article_key)
    return out


def _is_subtopic_binding_eligible(binding: "SubtopicBinding | None") -> bool:
    """Return True iff the SubtopicBinding meets the Falkor SubTopicNode schema.

    ``graph/schema.py`` declares SubTopicNode.required_fields =
    ``("sub_topic_key", "parent_topic", "label")``; a caller that passes a
    binding with any of those empty/whitespace would crash the same way the
    original ArticleNode bug did. We filter at build time to make the failure
    mode loud (surfaced via ``ingest.graph.subtopics_skipped_nonschema``) but
    non-fatal.
    """
    if not binding:
        return False
    return bool(
        str(binding.sub_topic_key or "").strip()
        and str(binding.parent_topic or "").strip()
        and str(binding.label or "").strip()
    )


def _try_emit_event(event_type: str, payload: dict) -> None:
    """Best-effort wrapper around ``instrumentation.emit_event``.

    Observability failures must never break ingest, but they also mustn't be
    silent: the wrapper degrades to stderr if the instrumentation module
    itself is unavailable, so a dropped event is still visible in logs.
    """
    try:
        from ..instrumentation import emit_event

        emit_event(event_type, payload)
    except Exception as exc:  # noqa: BLE001 — instrumentation must never break ingest
        import sys as _sys

        print(
            f"[loader] failed to emit {event_type}: {exc!r} payload={payload!r}",
            file=_sys.stderr,
        )


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
    raw_edges = (
        list(edge.record for edge in normalized_edges)
        + list(subtopic_edges)
        + list(tema_edges)
        + list(subtema_de_edges)
    )
    # Drop edges whose ARTICLE endpoint was filtered out by the eligibility
    # checks above. ``stage_edge`` uses MATCH for endpoints so these would
    # silently no-op in Cypher, but keeping them in the plan inflates stats
    # and hides real provenance loss. See the 2026-04-23 Phase 9.A triage.
    # v4: also filter edges whose classifier-view key (article.article_key)
    # differs from the graph MERGE key — prose-only remap case.
    ineligible_article_keys = _orphaning_article_keys(articles)
    edges, dropped_edges = _filter_edges_by_article_eligibility(
        raw_edges, ineligible_article_keys
    )
    edges = _dedupe_edges(edges)
    validation = validate_graph_records(nodes, edges, schema=graph_schema)

    # Phase 2c (v6): batched load plan. One UNWIND per N nodes + M edges,
    # preceded by idempotent CREATE INDEX statements for every MERGE label.
    # This replaces the pre-2c pattern of one GRAPH.QUERY per record, which
    # produced ~28,000 round-trips on the v6 corpus and stalled silently
    # on 2026-04-24 because each MERGE was doing an unindexed label scan.
    # See docs/learnings/ingestion/falkor-bulk-load.md.
    statements = _build_batched_statements(
        client=client,
        nodes=nodes,
        edges=edges,
    )
    warnings: list[str] = []
    skipped_edge_count = len(classified_edges) - len(normalized_edges)
    if skipped_edge_count:
        warnings.append(
            "Skipped "
            f"{skipped_edge_count} unresolved ArticleNode edge(s) whose targets are not materialized "
            "in the current corpus snapshot."
        )
    if dropped_edges:
        warnings.append(
            f"Skipped {dropped_edges} edge(s) whose ArticleNode endpoint was filtered "
            "as non-schema (e.g. parser-fallback article without article_number)."
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

    # (1) DETACH DELETE for retired articles. Filter empty AND
    # whitespace-only keys so stage_detach_delete (which rejects both) never
    # sees a malformed input — a whitespace-only key sneaking through would
    # mask an orchestrator bug.
    retired_keys = tuple(retired_article_keys or ())
    for key in sorted({str(k).strip() for k in retired_keys if k and str(k).strip()}):
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
    raw_edges = (
        list(edge.record for edge in normalized_edges)
        + list(promoted_dangling_edges)
        + list(_build_subtopic_edges(delta_articles, article_subtopics))
        + list(_build_article_tema_edges(delta_articles, article_topics))
        + list(_build_static_subtema_de_edges(article_subtopics))
    )
    # v4: same combined filter — ineligible + prose-only-remap.
    ineligible_article_keys = _orphaning_article_keys(delta_articles)
    filtered_edges, dropped_edges = _filter_edges_by_article_eligibility(
        raw_edges, ineligible_article_keys
    )
    edges = _dedupe_edges(filtered_edges)
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
    if dropped_edges:
        warnings.append(
            f"Skipped {dropped_edges} edge(s) whose ArticleNode endpoint was filtered "
            "as non-schema (e.g. parser-fallback article without article_number)."
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


def _build_batched_statements(
    *,
    client: GraphClient,
    nodes: tuple[GraphNodeRecord, ...] | list[GraphNodeRecord],
    edges: tuple[GraphEdgeRecord, ...] | list[GraphEdgeRecord],
) -> tuple[GraphWriteStatement, ...]:
    """Phase 2c (v6) — batched UNWIND load plan.

    Order matters: indexes first so subsequent MERGE statements are
    O(log N) instead of O(N). Then nodes grouped by label and batched
    at ``config.batch_size_nodes``. Then edges grouped by
    ``(source_kind, edge_kind, target_kind)`` and batched at
    ``config.batch_size_edges``. Groupings keep the Cypher shape
    constant within a batch so the planner can cache the plan across
    batches.
    """
    batch_nodes = max(1, int(client.config.batch_size_nodes))
    batch_edges = max(1, int(client.config.batch_size_edges))

    # 1. CREATE INDEX preludes — idempotent on FalkorDB.
    statements: list[GraphWriteStatement] = list(
        client.stage_indexes_for_merge_labels()
    )

    # 1b. TEMA cleanup pass — for every ArticleNode about to be MERGEd this
    # run, DELETE its existing outbound TEMA edges before the new ones get
    # MERGEd. Without this, classifier instability across runs accumulates
    # contradictory TEMA bindings (one ArticleNode bound to two unrelated
    # topics — the Q27 art. 148 → {iva, sagrilaft_ptee} root cause documented
    # in next_v2 §3). Scoped to ArticleNode; other edge kinds either come from
    # static taxonomy or have stable upstream provenance.
    article_keys_being_merged = sorted(
        {n.key for n in nodes if n.kind is NodeKind.ARTICLE and n.key}
    )
    if article_keys_being_merged:
        statements.append(
            client.stage_delete_outbound_edges_batch(
                NodeKind.ARTICLE,
                article_keys_being_merged,
                relation=EdgeKind.TEMA,
            )
        )

    # 2. Node batches grouped by kind.
    nodes_by_kind: dict[NodeKind, list[Mapping[str, object]]] = {}
    for node in nodes:
        nodes_by_kind.setdefault(node.kind, []).append(
            {"key": node.key, "properties": dict(node.properties)}
        )
    # Stable output order (predictable tests + readable logs).
    for kind in sorted(nodes_by_kind, key=lambda k: k.value):
        rows = nodes_by_kind[kind]
        for start in range(0, len(rows), batch_nodes):
            chunk = rows[start : start + batch_nodes]
            statements.append(client.stage_node_batch(kind, chunk))

    # 3. Edge batches grouped by (source_kind, edge_kind, target_kind).
    edges_by_triple: dict[
        tuple[NodeKind, EdgeKind, NodeKind], list[Mapping[str, object]]
    ] = {}
    for edge in edges:
        triple = (edge.source_kind, edge.kind, edge.target_kind)
        edges_by_triple.setdefault(triple, []).append(
            {
                "source_key": edge.source_key,
                "target_key": edge.target_key,
                "properties": dict(edge.properties),
            }
        )
    for triple in sorted(
        edges_by_triple,
        key=lambda t: (t[0].value, t[1].value, t[2].value),
    ):
        rows = edges_by_triple[triple]
        src_kind, edge_kind, dst_kind = triple
        for start in range(0, len(rows), batch_edges):
            chunk = rows[start : start + batch_edges]
            statements.append(
                client.stage_edge_batch(
                    edge_kind=edge_kind,
                    source_kind=src_kind,
                    target_kind=dst_kind,
                    rows=chunk,
                )
            )

    return tuple(statements)


def _build_article_nodes(
    articles: tuple[ParsedArticle, ...] | list[ParsedArticle],
) -> tuple[GraphNodeRecord, ...]:
    eligible = [a for a in articles if _is_article_node_eligible(a)]
    skipped = len(articles) - len(eligible)
    if skipped:
        # Best-effort observability — parser-fallback articles (no
        # article_number) are a known legitimate case; surface the count so
        # Phase 10 smokes can reconcile Supabase chunks vs Falkor articles.
        sample_keys = [
            a.article_key for a in articles if not _is_article_node_eligible(a)
        ][:5]
        _try_emit_event(
            "ingest.graph.articles_skipped_nonschema",
            {
                "skipped": skipped,
                "sample_article_keys": sample_keys,
                "reason": "ParsedArticle lacked required ArticleNode fields "
                "(article_number / heading / text / status). Typically a "
                "section-fallback or whole-doc-fallback output.",
            },
        )
    # Use _graph_article_key for the MERGE key so prose-only articles don't
    # collide on the shared WHOLE_DOC_ARTICLE_KEY across the corpus. Keep
    # `article_number` in properties even when empty so Cypher queries that
    # read the field stay compatible.
    return tuple(
        GraphNodeRecord(
            kind=NodeKind.ARTICLE,
            key=_graph_article_key(article),
            properties={
                "article_number": article.article_number,
                "heading": article.heading,
                "text_current": article.body or article.full_text,
                "status": article.status,
                "source_path": article.source_path,
                "paragraph_markers": list(article.paragraph_markers),
                "reform_references": list(article.reform_references),
                "annotations": list(article.annotations),
                "is_prose_only": _is_prose_only(article),
            },
        )
        for article in eligible
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
    """Emit TEMA edges: every article with a resolved topic → TopicNode.

    Scoped to the eligible (schema-meeting) article set; fallback articles
    that were filtered out of ``_build_article_nodes`` must not source a
    TEMA edge whose ArticleNode was never materialized. The edge's MATCH
    on the source node would silently no-op in Cypher, but we'd rather not
    pollute the statement stream with unreachable statements.
    """
    if not article_topics:
        return ()
    # Graph-layer key set — must match the ArticleNode.key MERGE values so
    # TEMA edges land on existing nodes. Callers populate article_topics
    # using the SAME _graph_article_key helper.
    article_keys = {
        _graph_article_key(article)
        for article in articles
        if _is_article_node_eligible(article)
    }
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
    skipped_bindings: list[str] = []
    for binding in article_subtopics.values():
        if not _is_subtopic_binding_eligible(binding):
            # Keep the sub_topic_key for observability even when the binding
            # is partially populated — helps diagnose upstream miners that
            # forgot to wire ``parent_topic`` / ``label``.
            if binding and binding.sub_topic_key:
                skipped_bindings.append(binding.sub_topic_key)
            continue
        unique.setdefault(binding.sub_topic_key, binding)
    if skipped_bindings:
        _try_emit_event(
            "ingest.graph.subtopics_skipped_nonschema",
            {
                "skipped": len(skipped_bindings),
                "sample_sub_topic_keys": skipped_bindings[:5],
                "reason": "SubtopicBinding lacked required SubTopicNode fields "
                "(sub_topic_key / parent_topic / label).",
            },
        )
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
    # Only articles that became ArticleNodes can source HAS_SUBTOPIC edges.
    # v4: use graph-layer keys so prose-only articles (whose article_key was
    # remapped from "doc" → "whole::{source_path}") match. Callers must key
    # article_subtopics by `_graph_article_key(article)`.
    article_keys = {
        _graph_article_key(article)
        for article in articles
        if _is_article_node_eligible(article)
    }
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
    # ReformNode.required_fields = ("citation",) per schema.py. Drop any
    # entry whose citation is empty/whitespace — same crash class as the
    # ArticleNode bug. Surface the count so the miner can notice when it's
    # emitting malformed references.
    nodes: list[GraphNodeRecord] = []
    skipped: list[str] = []
    for key, citation in sorted(citations_by_key.items()):
        if not str(citation or "").strip():
            skipped.append(key)
            continue
        nodes.append(
            GraphNodeRecord(
                kind=NodeKind.REFORM,
                key=key,
                properties={"citation": citation},
            )
        )
    if skipped:
        _try_emit_event(
            "ingest.graph.reforms_skipped_nonschema",
            {
                "skipped": len(skipped),
                "sample_reform_keys": skipped[:5],
                "reason": "ReformNode citation was empty/whitespace.",
            },
        )
    return tuple(nodes)


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


def _filter_edges_by_article_eligibility(
    edges: list[GraphEdgeRecord],
    ineligible_article_keys: set[str],
) -> tuple[list[GraphEdgeRecord], int]:
    """Drop edges whose ARTICLE endpoint is in the ``ineligible_article_keys``
    set (i.e., an article this delta filtered out of ArticleNode staging).

    Returns ``(kept, dropped_count)``. Only drops when we KNOW the endpoint
    was skipped by us — ARTICLE endpoints NOT in the delta's article list
    are assumed materialized by a prior reingest and left alone so ``MATCH``
    can find them.

    See the 2026-04-23 Phase 9.A triage: parser-fallback articles were
    filtered out of ArticleNode staging, leaving their classifier / dangling
    edges orphaned. ``stage_edge`` MATCH would silently no-op but the
    statement stream still inflated. Filtering here keeps the plan honest.
    """
    if not ineligible_article_keys:
        return list(edges), 0
    kept: list[GraphEdgeRecord] = []
    dropped = 0
    for record in edges:
        if (
            record.source_kind is NodeKind.ARTICLE
            and record.source_key in ineligible_article_keys
        ):
            dropped += 1
            continue
        if (
            record.target_kind is NodeKind.ARTICLE
            and record.target_key in ineligible_article_keys
        ):
            dropped += 1
            continue
        kept.append(record)
    return kept, dropped


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
