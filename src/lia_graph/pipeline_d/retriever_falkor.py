"""Falkor-backed replacement for the artifact BFS in `retriever.py`.

Signature matches `retriever.retrieve_graph_evidence(plan, artifacts_dir=None)`.
Orchestrator dispatches based on `LIA_GRAPH_MODE`:

- `artifacts` (dev default) -> `retriever.retrieve_graph_evidence`
- `falkor_live` (staging default) -> this module

The rule of this module is simple: run a bounded, parameterized Cypher BFS
against cloud FalkorDB and hand the result back in the same
`GraphEvidenceBundle` shape synthesis/assembly already consumes. If FalkorDB
errors, the error propagates — operators must see outages; we never silently
fall back to artifacts.

This module complements `retriever_supabase`:

- `retriever_supabase` owns `support_documents`/`citations` (the chunk-level
  retrieval)
- `retriever_falkor` owns `primary_articles`/`connected_articles`/
  `related_reforms` (the graph traversal)

Orchestrator assembles both halves into one `GraphEvidenceBundle` when both
flags say cloud-live.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..graph.client import GraphClient, GraphClientError, GraphWriteStatement
from .contracts import (
    GraphEvidenceBundle,
    GraphEvidenceItem,
    GraphPathStep,
    GraphRetrievalPlan,
    PlannerEntryPoint,
)
from .planner import with_resolved_entry_points
from .retrieval_support import _MODE_EDGE_PREFERENCES


def retrieve_graph_evidence(
    plan: GraphRetrievalPlan,
    *,
    artifacts_dir: Path | str | None = None,  # compatibility — Falkor never reads disk
    graph_client: GraphClient | None = None,
) -> tuple[GraphRetrievalPlan, GraphEvidenceBundle]:
    del artifacts_dir
    client = graph_client if graph_client is not None else GraphClient.from_env()
    if not client.config.is_configured:
        raise GraphClientError(
            "FALKORDB_URL is not configured — live graph traversal cannot run. "
            "Set FALKORDB_URL or switch LIA_GRAPH_MODE=artifacts."
        )

    explicit_article_keys = _explicit_article_keys(plan)
    explicit_reform_keys = _explicit_reform_keys(plan)

    # ingestfix-v2 Phase 6: when planner detected a subtopic intent, lift
    # articles bound to that SubTopic into the primary anchors. Falls back
    # to the explicit-article-keys path when no bindings exist.
    sub_topic_intent = getattr(plan, "sub_topic_intent", None)
    subtopic_article_keys: tuple[str, ...] = ()
    if sub_topic_intent:
        subtopic_article_keys = _retrieve_subtopic_bound_article_keys(
            client=client,
            sub_topic_key=sub_topic_intent,
            limit=max(plan.evidence_bundle_shape.primary_article_limit, 1),
        )
        if not subtopic_article_keys:
            try:
                from ..instrumentation import emit_event as _emit

                _emit(
                    "subtopic.retrieval.fallback_to_topic",
                    {
                        "sub_topic_intent": sub_topic_intent,
                        "parent_topic_hint": (plan.topic_hints[0] if plan.topic_hints else None),
                        "fallback_node_count": len(explicit_article_keys),
                    },
                )
            except Exception:  # noqa: BLE001 — observability never blocks
                pass

    # Merge subtopic-anchored keys with explicit article keys (explicit first).
    if subtopic_article_keys:
        seen: set[str] = set(explicit_article_keys)
        merged = list(explicit_article_keys)
        for key in subtopic_article_keys:
            if key not in seen:
                seen.add(key)
                merged.append(key)
        effective_article_keys = tuple(merged)
    else:
        effective_article_keys = explicit_article_keys

    # v5 Phase 3 — TEMA-first retrieval. When LIA_TEMA_FIRST_RETRIEVAL is
    # on or shadow, expand the candidate article-key set with
    # TopicNode<-[:TEMA]- articles for the routed topic hint. This is the
    # first time the 1,943 TEMA edges v4 populated actually steer retrieval.
    tema_first_mode = _tema_first_mode()
    tema_article_keys: tuple[str, ...] = ()
    topic_for_tema = (plan.topic_hints[0] if plan.topic_hints else None)
    if tema_first_mode in ("on", "shadow") and topic_for_tema:
        tema_article_keys = _retrieve_tema_bound_article_keys(
            client=client,
            topic_key=topic_for_tema,
            limit=max(plan.evidence_bundle_shape.primary_article_limit, 1),
        )
        try:
            from ..instrumentation import emit_event as _emit
            event_name = (
                "retrieval.tema_first.live"
                if tema_first_mode == "on"
                else "retrieval.tema_first.shadow"
            )
            _emit(
                event_name,
                {
                    "topic_key": topic_for_tema,
                    "tema_bound_count": len(tema_article_keys),
                    "explicit_count": len(explicit_article_keys),
                    "subtopic_count": len(subtopic_article_keys),
                },
            )
        except Exception:  # noqa: BLE001 — observability never blocks
            pass
        if tema_first_mode == "on" and tema_article_keys:
            # Merge: explicit anchors first, then subtopic, then TEMA-scoped.
            seen2: set[str] = set(effective_article_keys)
            merged2 = list(effective_article_keys)
            for key in tema_article_keys:
                if key not in seen2:
                    seen2.add(key)
                    merged2.append(key)
            effective_article_keys = tuple(merged2)

    primary_articles = _retrieve_primary_articles(
        client=client,
        plan=plan,
        article_keys=effective_article_keys,
    )
    connected_articles = _retrieve_connected_articles(
        client=client,
        plan=plan,
        article_keys=effective_article_keys,
    )
    related_reforms = _retrieve_reforms(
        client=client,
        plan=plan,
        reform_keys=explicit_reform_keys,
        article_keys=effective_article_keys,
    )
    hydrated_plan = with_resolved_entry_points(
        plan,
        _hydrated_entries(plan=plan, resolved_article_keys={item.node_key for item in primary_articles}),
    )
    diagnostics = {
        "graph_backend": "falkor_live",
        "resolved_entry_count": sum(
            1 for entry in hydrated_plan.entry_points if entry.resolved_key
        ),
        "primary_article_count": len(primary_articles),
        "connected_article_count": len(connected_articles),
        "related_reform_count": len(related_reforms),
        "graph_name": client.config.graph_name,
        "planner_query_mode": plan.query_mode,
        "temporal_context": plan.temporal_context.to_dict(),
        "seed_article_keys": list(effective_article_keys),
        "retrieval_sub_topic_intent": sub_topic_intent,
        "subtopic_anchor_keys": list(subtopic_article_keys),
        # v5 Phase 3: surface the TEMA-first contribution so /orchestration
        # + unit tests can verify the feature is actually steering retrieval.
        "tema_first_mode": tema_first_mode,
        "tema_first_topic_key": topic_for_tema,
        "tema_first_anchor_count": len(tema_article_keys),
    }
    if not primary_articles:
        diagnostics.update(
            _diagnose_empty_primary(
                client=client,
                article_keys=explicit_article_keys,
            )
        )
    else:
        diagnostics["empty_reason"] = "ok"
    evidence = GraphEvidenceBundle(
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        related_reforms=related_reforms,
        support_documents=(),
        citations=(),
        diagnostics=diagnostics,
    )
    return hydrated_plan, evidence


# --- helpers ----------------------------------------------------------------


def _diagnose_empty_primary(
    *,
    client: GraphClient,
    article_keys: tuple[str, ...],
) -> dict[str, Any]:
    """Classify *why* the primary lookup came back empty.

    Emits `empty_reason` plus enough counters for an operator to tell
    schema-drift, graph-not-seeded, and planner-no-anchor apart without
    needing shell access.
    """
    probe: dict[str, Any] = {}
    if not article_keys:
        probe["empty_reason"] = "no_explicit_article_keys_in_plan"
        return probe

    # How many ArticleNodes exist at all? Differentiates "graph is empty" from
    # "graph is seeded but our query found nothing".
    try:
        total_rows = _execute(
            client,
            GraphWriteStatement(
                description="empty_reason_probe article_node_total",
                query="MATCH (n:ArticleNode) RETURN count(n) AS total",
                parameters={},
            ),
        )
        article_node_total = int((total_rows[0] or {}).get("total") or 0) if total_rows else 0
    except GraphClientError:
        probe["empty_reason"] = "graph_probe_failed"
        return probe
    probe["article_node_total"] = article_node_total
    if article_node_total == 0:
        probe["empty_reason"] = "graph_not_seeded"
        return probe

    # Does ANY node match by the canonical property for the requested keys?
    # If this is also zero, either keys are wrong *or* the canonical property
    # drifted. A second probe against the legacy `article_key` predicate catches
    # the drift case so operators see it instead of mystery silence.
    canonical_rows = _execute(
        client,
        GraphWriteStatement(
            description="empty_reason_probe match_by_article_number",
            query=(
                "UNWIND $keys AS key\n"
                "MATCH (n:ArticleNode {article_number: key})\n"
                "RETURN count(n) AS matches"
            ),
            parameters={"keys": list(article_keys)},
        ),
    )
    canonical_matches = int((canonical_rows[0] or {}).get("matches") or 0) if canonical_rows else 0
    probe["article_node_matches_by_article_number"] = canonical_matches

    legacy_rows = _execute(
        client,
        GraphWriteStatement(
            description="empty_reason_probe match_by_article_key_legacy",
            query=(
                "UNWIND $keys AS key\n"
                "MATCH (n:ArticleNode {article_key: key})\n"
                "RETURN count(n) AS matches"
            ),
            parameters={"keys": list(article_keys)},
        ),
    )
    legacy_matches = int((legacy_rows[0] or {}).get("matches") or 0) if legacy_rows else 0
    probe["article_node_matches_by_article_key"] = legacy_matches

    if canonical_matches == 0 and legacy_matches > 0:
        probe["empty_reason"] = "schema_drift:retriever_expects_article_number_but_data_uses_article_key"
    elif canonical_matches == 0:
        probe["empty_reason"] = "no_matching_article_numbers"
    else:
        # Canonical property had matches but the upstream query still returned
        # zero — means the fetch path itself is broken (column aliasing, etc.).
        probe["empty_reason"] = "primary_fetch_zero_despite_canonical_matches"
    return probe


def _retrieve_subtopic_bound_article_keys(
    *,
    client: GraphClient,
    sub_topic_key: str,
    limit: int,
) -> tuple[str, ...]:
    """Fetch article keys linked to a curated SubTopic via HAS_SUBTOPIC.

    Invariant I2 — errors propagate; we never silently degrade.
    """
    if not sub_topic_key or limit <= 0:
        return ()
    statement = GraphWriteStatement(
        description=f"subtopic_bound_articles key={sub_topic_key} limit={limit}",
        query=(
            "MATCH (a:ArticleNode)-[:HAS_SUBTOPIC]->(s:SubTopicNode {sub_topic_key: $key})\n"
            "RETURN a.article_number AS article_key\n"
            "LIMIT $limit\n"
        ),
        parameters={"key": sub_topic_key, "limit": int(limit)},
    )
    rows = _execute(client, statement)
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        candidate = str(row.get("article_key") or "").strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            keys.append(candidate)
    return tuple(keys)


# v5 Phase 3 — TEMA-first retrieval ----------------------------------------


_TEMA_FIRST_ENV = "LIA_TEMA_FIRST_RETRIEVAL"
_TEMA_FIRST_VALID_MODES: frozenset[str] = frozenset({"off", "shadow", "on"})


def _tema_first_mode() -> str:
    # Default `on` 2026-04-25 — re-flipped per gate_9_threshold_decision.md §7
    # + "no off flags" directive. Aligns Python default with launcher + Railway.
    raw = str(os.getenv(_TEMA_FIRST_ENV, "on") or "").strip().lower()
    return raw if raw in _TEMA_FIRST_VALID_MODES else "on"


def _retrieve_tema_bound_article_keys(
    *,
    client: GraphClient,
    topic_key: str,
    limit: int,
) -> tuple[str, ...]:
    """Fetch article_number values for articles with a TEMA edge to ``topic_key``.

    v5 Phase 3: starts at TopicNode → <-[:TEMA]-(ArticleNode) → returns
    article_number (which is the effective article_key consumed by the
    rest of the retriever). Ordered by article_number for determinism.

    Empty topic_key or non-positive limit return ``()``. Errors propagate
    (Invariant I2).
    """
    if not topic_key or limit <= 0:
        return ()
    statement = GraphWriteStatement(
        description=f"tema_bound_articles topic={topic_key} limit={limit}",
        query=(
            "MATCH (t:TopicNode {topic_key: $topic})<-[:TEMA]-(a:ArticleNode)\n"
            "WHERE a.article_number IS NOT NULL AND a.article_number <> ''\n"
            "RETURN DISTINCT a.article_number AS article_key\n"
            "ORDER BY article_key\n"
            "LIMIT $limit\n"
        ),
        parameters={"topic": topic_key, "limit": int(limit)},
    )
    rows = _execute(client, statement)
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        candidate = str(row.get("article_key") or "").strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            keys.append(candidate)
    return tuple(keys)


def _explicit_article_keys(plan: GraphRetrievalPlan) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for entry in plan.entry_points:
        if entry.kind == "article" and entry.lookup_value and entry.lookup_value not in seen:
            seen.add(entry.lookup_value)
            ordered.append(entry.lookup_value)
    return tuple(ordered)


def _explicit_reform_keys(plan: GraphRetrievalPlan) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for entry in plan.entry_points:
        if entry.kind == "reform" and entry.lookup_value and entry.lookup_value not in seen:
            seen.add(entry.lookup_value)
            ordered.append(entry.lookup_value)
    return tuple(ordered)


def _mode_edge_preference(plan: GraphRetrievalPlan) -> tuple[str, ...]:
    return _MODE_EDGE_PREFERENCES.get(
        plan.query_mode,
        ("REFERENCES", "REQUIRES", "MODIFIES"),
    )


def _execute(client: GraphClient, statement: GraphWriteStatement) -> list[dict[str, Any]]:
    result = client.execute(statement, strict=True)
    return [dict(row) for row in result.rows]


def _retrieve_primary_articles(
    *,
    client: GraphClient,
    plan: GraphRetrievalPlan,
    article_keys: tuple[str, ...],
) -> tuple[GraphEvidenceItem, ...]:
    limit = plan.evidence_bundle_shape.primary_article_limit
    if not article_keys or limit <= 0:
        return ()
    statement = GraphWriteStatement(
        description=f"primary_articles limit={limit}",
        query=(
            "UNWIND $keys AS key\n"
            # Canonical node property is `article_number` (see graph/schema.py).
            # Historical code wrote `article_key` but no live graph carries that
            # property — querying it was a silent no-op across the whole corpus.
            "MATCH (node:ArticleNode {article_number: key})\n"
            "RETURN key AS article_key, node.heading AS heading, node.text_current AS text_current,"
            " node.source_path AS source_path, node.status AS status,"
            # v5 §1.A — multi-topic metadata. Falkor returns NULL when the
            # property hasn't been written (pre-§1.A nodes); the parser
            # below normalises that to ().
            " node.secondary_topics AS secondary_topics\n"
        ),
        parameters={"keys": list(article_keys[:limit])},
    )
    rows = _execute(client, statement)
    items: list[GraphEvidenceItem] = []
    for index, row in enumerate(rows):
        article_key = str(row.get("article_key") or "")
        if not article_key:
            continue
        text_current = str(row.get("text_current") or "")
        excerpt = text_current[: plan.evidence_bundle_shape.snippet_char_limit]
        # v5 §1.A — defensive parse: Falkor may return None, "", or a list.
        sec_raw = row.get("secondary_topics")
        secondary_topics: tuple[str, ...] = ()
        if isinstance(sec_raw, (list, tuple)):
            secondary_topics = tuple(
                str(t).strip() for t in sec_raw if isinstance(t, str) and str(t).strip()
            )
        items.append(
            GraphEvidenceItem(
                node_kind="ArticleNode",
                node_key=article_key,
                title=str(row.get("heading") or f"Articulo {article_key}"),
                excerpt=excerpt,
                source_path=str(row.get("source_path") or "") or None,
                score=float(len(rows) - index),
                hop_distance=0,
                why=None,
                relation_path=(),
                secondary_topics=secondary_topics,
            )
        )
    return tuple(items)


def _retrieve_connected_articles(
    *,
    client: GraphClient,
    plan: GraphRetrievalPlan,
    article_keys: tuple[str, ...],
) -> tuple[GraphEvidenceItem, ...]:
    limit = plan.evidence_bundle_shape.connected_article_limit
    if not article_keys or limit <= 0:
        return ()
    max_hops = max(1, int(plan.traversal_budget.max_hops))
    edge_preference = list(_mode_edge_preference(plan))
    statement = GraphWriteStatement(
        description=f"connected_articles hops<={max_hops}",
        query=(
            "UNWIND $keys AS seed_key\n"
            "MATCH (seed:ArticleNode {article_number: seed_key})\n"
            f"MATCH path = (seed)-[rel*1..{max_hops}]-(other:ArticleNode)\n"
            "WHERE other.article_number <> seed_key AND NOT other.article_number IN $keys\n"
            "WITH other, relationships(path) AS rels, length(path) AS hop\n"
            "WITH other, hop, [r IN rels | type(r)] AS edge_kinds\n"
            "WITH other.article_number AS article_key,"
            " other.heading AS heading,"
            " other.text_current AS text_current,"
            " other.source_path AS source_path,"
            " min(hop) AS hop_distance,"
            " head(edge_kinds) AS first_edge_kind\n"
            "WITH article_key, heading, text_current, source_path, hop_distance, first_edge_kind,\n"
            " CASE\n"
            + "\n".join(
                f"  WHEN first_edge_kind = '{edge}' THEN {index}"
                for index, edge in enumerate(edge_preference)
            )
            + f"\n  ELSE {len(edge_preference) + 1}\n END AS edge_rank\n"
            "ORDER BY hop_distance ASC, edge_rank ASC, article_key ASC\n"
            "LIMIT $limit\n"
            "RETURN article_key, heading, text_current, source_path, hop_distance, first_edge_kind\n"
        ),
        parameters={"keys": list(article_keys), "limit": int(limit)},
    )
    rows = _execute(client, statement)
    items: list[GraphEvidenceItem] = []
    for row in rows:
        article_key = str(row.get("article_key") or "")
        if not article_key:
            continue
        text_current = str(row.get("text_current") or "")
        excerpt = text_current[: plan.evidence_bundle_shape.snippet_char_limit]
        first_edge_kind = str(row.get("first_edge_kind") or "")
        relation_path: tuple[GraphPathStep, ...] = ()
        if first_edge_kind:
            relation_path = (
                GraphPathStep(
                    edge_kind=first_edge_kind,
                    direction="out",
                    from_node_kind="ArticleNode",
                    from_node_key=article_keys[0],
                    to_node_kind="ArticleNode",
                    to_node_key=article_key,
                ),
            )
        hop = int(row.get("hop_distance") or 1)
        items.append(
            GraphEvidenceItem(
                node_kind="ArticleNode",
                node_key=article_key,
                title=str(row.get("heading") or f"Articulo {article_key}"),
                excerpt=excerpt,
                source_path=str(row.get("source_path") or "") or None,
                score=float(limit - len(items)),
                hop_distance=hop,
                why=None,
                relation_path=relation_path,
            )
        )
    return tuple(items)


def _retrieve_reforms(
    *,
    client: GraphClient,
    plan: GraphRetrievalPlan,
    reform_keys: tuple[str, ...],
    article_keys: tuple[str, ...],
) -> tuple[GraphEvidenceItem, ...]:
    limit = plan.evidence_bundle_shape.related_reform_limit
    if limit <= 0:
        return ()
    items: list[GraphEvidenceItem] = []
    seen: set[str] = set()

    if reform_keys:
        statement = GraphWriteStatement(
            description="related_reforms explicit",
            query=(
                "UNWIND $keys AS key\n"
                "MATCH (node:ReformNode {reform_key: key})\n"
                "RETURN key AS reform_key, node.citation AS citation\n"
            ),
            parameters={"keys": list(reform_keys[:limit])},
        )
        for row in _execute(client, statement):
            key = str(row.get("reform_key") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            items.append(
                GraphEvidenceItem(
                    node_kind="ReformNode",
                    node_key=key,
                    title=str(row.get("citation") or key),
                    excerpt="Reforma referenciada por el planner.",
                    source_path=None,
                    score=float(limit - len(items)),
                    hop_distance=0,
                    why=None,
                    relation_path=(),
                )
            )

    remaining = limit - len(items)
    if remaining > 0 and article_keys:
        statement = GraphWriteStatement(
            description="related_reforms via article neighborhood",
            query=(
                "UNWIND $keys AS seed_key\n"
                "MATCH (:ArticleNode {article_number: seed_key})-[rel]-(reform:ReformNode)\n"
                "WHERE NOT reform.reform_key IN $seen_keys\n"
                "RETURN reform.reform_key AS reform_key, reform.citation AS citation,"
                " count(rel) AS hits\n"
                "ORDER BY hits DESC, reform.reform_key ASC\n"
                "LIMIT $limit\n"
            ),
            parameters={
                "keys": list(article_keys),
                "seen_keys": sorted(seen),
                "limit": int(remaining),
            },
        )
        for row in _execute(client, statement):
            key = str(row.get("reform_key") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            items.append(
                GraphEvidenceItem(
                    node_kind="ReformNode",
                    node_key=key,
                    title=str(row.get("citation") or key),
                    excerpt="Reforma vecina en el grafo.",
                    source_path=None,
                    score=float(row.get("hits") or 0.0),
                    hop_distance=1,
                    why=None,
                    relation_path=(),
                )
            )
    return tuple(items)


def _hydrated_entries(
    *,
    plan: GraphRetrievalPlan,
    resolved_article_keys: set[str],
) -> tuple[PlannerEntryPoint, ...]:
    hydrated: list[PlannerEntryPoint] = []
    for entry in plan.entry_points:
        if entry.kind == "article" and entry.lookup_value:
            resolved_key = entry.lookup_value if entry.lookup_value in resolved_article_keys else None
            hydrated.append(
                PlannerEntryPoint(
                    kind=entry.kind,
                    lookup_value=entry.lookup_value,
                    source=entry.source,
                    confidence=entry.confidence,
                    label=entry.label,
                    resolved_key=resolved_key,
                )
            )
        else:
            hydrated.append(entry)
    return tuple(hydrated)


__all__ = ["retrieve_graph_evidence"]
