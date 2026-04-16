from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from ..contracts import Citation, DocumentRecord
from .contracts import (
    GraphEvidenceBundle,
    GraphEvidenceItem,
    GraphPathStep,
    GraphRetrievalPlan,
    GraphSupportDocument,
    PlannerEntryPoint,
)
from .planner import with_resolved_entry_points
from .retrieval_support import (
    _FAMILY_RANK,
    article_excerpt,
    article_temporal_bonus,
    build_relation_path,
    explain_article_relevance,
    lexical_article_matches,
    manifest_row_to_document,
    neighbor_bonus,
    reform_priority_rank,
    reform_why,
    should_keep_connected_article,
    snippet,
    sorted_neighbors,
    support_doc_query_overlap,
    support_doc_query_tokens,
)

_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_ARTIFACTS_DIR = _WORKSPACE_ROOT / "artifacts"


@dataclass(frozen=True)
class _EdgeRecord:
    kind: str
    source_kind: str
    source_key: str
    target_kind: str
    target_key: str
    properties: dict[str, Any]


@dataclass(frozen=True)
class _Neighbor:
    edge: _EdgeRecord
    other_kind: str
    other_key: str
    direction: str


@dataclass(frozen=True)
class _ResolvedEntry:
    kind: str
    key: str
    label: str
    source: str
    confidence: float


@dataclass(frozen=True)
class GraphArtifactSnapshot:
    artifacts_dir: Path
    manifest: dict[str, Any]
    articles: dict[str, dict[str, Any]]
    reforms: dict[str, dict[str, Any]]
    docs_by_source_path: dict[str, dict[str, Any]]
    ready_docs_by_topic: dict[str, tuple[dict[str, Any], ...]]
    adjacency: dict[tuple[str, str], tuple[_Neighbor, ...]]


def retrieve_graph_evidence(
    plan: GraphRetrievalPlan,
    *,
    artifacts_dir: Path | str | None = None,
) -> tuple[GraphRetrievalPlan, GraphEvidenceBundle]:
    snapshot = load_graph_artifact_snapshot(artifacts_dir)
    resolved_entries, planned_entries = _resolve_entry_points(snapshot=snapshot, plan=plan)
    hydrated_plan = with_resolved_entry_points(plan, planned_entries)
    evidence_bundle = _retrieve_from_resolved_entries(
        snapshot=snapshot,
        plan=hydrated_plan,
        resolved_entries=resolved_entries,
    )
    return hydrated_plan, evidence_bundle


def load_graph_artifact_snapshot(
    artifacts_dir: Path | str | None = None,
) -> GraphArtifactSnapshot:
    resolved_dir = Path(artifacts_dir) if artifacts_dir is not None else _DEFAULT_ARTIFACTS_DIR
    return _load_graph_artifact_snapshot_cached(str(resolved_dir.resolve()))


@lru_cache(maxsize=4)
def _load_graph_artifact_snapshot_cached(artifacts_dir: str) -> GraphArtifactSnapshot:
    root = Path(artifacts_dir)
    manifest = json.loads((root / "canonical_corpus_manifest.json").read_text(encoding="utf-8"))

    articles: dict[str, dict[str, Any]] = {}
    with (root / "parsed_articles.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            articles[str(row["article_key"])] = row

    reforms: dict[str, dict[str, Any]] = {}
    adjacency_lists: dict[tuple[str, str], list[_Neighbor]] = defaultdict(list)
    with (root / "typed_edges.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            edge = _EdgeRecord(
                kind=str(row["kind"]),
                source_kind=str(row["source_kind"]),
                source_key=str(row["source_key"]),
                target_kind=str(row["target_kind"]),
                target_key=str(row["target_key"]),
                properties=dict(row.get("properties") or {}),
            )
            adjacency_lists[(edge.source_kind, edge.source_key)].append(
                _Neighbor(
                    edge=edge,
                    other_kind=edge.target_kind,
                    other_key=edge.target_key,
                    direction="out",
                )
            )
            adjacency_lists[(edge.target_kind, edge.target_key)].append(
                _Neighbor(
                    edge=edge,
                    other_kind=edge.source_kind,
                    other_key=edge.source_key,
                    direction="in",
                )
            )
            if edge.source_kind == "ReformNode":
                reforms.setdefault(edge.source_key, {"citation": edge.properties.get("raw_reference") or edge.source_key})
            if edge.target_kind == "ReformNode":
                reforms.setdefault(edge.target_key, {"citation": edge.properties.get("raw_reference") or edge.target_key})

    docs_by_source_path: dict[str, dict[str, Any]] = {}
    ready_docs_by_topic_lists: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in manifest.get("documents", []):
        docs_by_source_path[str(row.get("source_path") or "")] = row
        if row.get("canonical_blessing_status") != "ready":
            continue
        topic_key = str(row.get("topic_key") or "").strip()
        if topic_key:
            ready_docs_by_topic_lists[topic_key].append(row)

    ready_docs_by_topic = {
        key: tuple(
            sorted(
                rows,
                key=lambda row: (
                    _FAMILY_RANK.get(str(row.get("family") or ""), 9),
                    str(row.get("relative_path") or ""),
                ),
            )
        )
        for key, rows in ready_docs_by_topic_lists.items()
    }
    adjacency = {
        key: tuple(
            sorted(
                values,
                key=lambda neighbor: (
                    neighbor.other_kind != "ArticleNode",
                    neighbor.edge.kind,
                    neighbor.other_key,
                ),
            )
        )
        for key, values in adjacency_lists.items()
    }
    return GraphArtifactSnapshot(
        artifacts_dir=root,
        manifest=manifest,
        articles=articles,
        reforms=reforms,
        docs_by_source_path=docs_by_source_path,
        ready_docs_by_topic=ready_docs_by_topic,
        adjacency=adjacency,
    )


def _resolve_entry_points(
    *,
    snapshot: GraphArtifactSnapshot,
    plan: GraphRetrievalPlan,
) -> tuple[tuple[_ResolvedEntry, ...], tuple[PlannerEntryPoint, ...]]:
    resolved: list[_ResolvedEntry] = []
    hydrated: list[PlannerEntryPoint] = []
    seen: set[tuple[str, str]] = set()
    article_search_count = sum(1 for entry in plan.entry_points if entry.kind == "article_search")

    for entry in plan.entry_points:
        if entry.kind == "article" and entry.lookup_value in snapshot.articles:
            resolved_entry = _ResolvedEntry(
                kind="ArticleNode",
                key=entry.lookup_value,
                label=entry.label or f"Art. {entry.lookup_value}",
                source=entry.source,
                confidence=entry.confidence,
            )
            if (resolved_entry.kind, resolved_entry.key) not in seen:
                seen.add((resolved_entry.kind, resolved_entry.key))
                resolved.append(resolved_entry)
            hydrated.append(entry)
            continue
        if entry.kind == "reform" and entry.lookup_value in snapshot.reforms:
            reform_label = str(snapshot.reforms[entry.lookup_value].get("citation") or entry.lookup_value)
            resolved_entry = _ResolvedEntry(
                kind="ReformNode",
                key=entry.lookup_value,
                label=entry.label or reform_label,
                source=entry.source,
                confidence=entry.confidence,
            )
            if (resolved_entry.kind, resolved_entry.key) not in seen:
                seen.add((resolved_entry.kind, resolved_entry.key))
                resolved.append(resolved_entry)
            hydrated.append(entry)
            continue
        if entry.kind == "article_search":
            hydrated.append(entry)
            lexical_limit = max(plan.evidence_bundle_shape.primary_article_limit * 4, 12)
            lexical_matches = lexical_article_matches(
                snapshot=snapshot,
                query=entry.lookup_value,
                topic_hints=plan.topic_hints,
                limit=lexical_limit,
            )
            lexical_score_floor = 0.0
            if lexical_matches:
                lexical_score_floor = max(2.5, lexical_matches[0][1] * 0.6)
            per_query_limit = lexical_limit
            if article_search_count >= 4:
                per_query_limit = 1
            elif article_search_count >= 2:
                per_query_limit = 2
            selected_for_query = 0
            for article_key, score in lexical_matches:
                if score < lexical_score_floor:
                    continue
                resolved_entry = _ResolvedEntry(
                    kind="ArticleNode",
                    key=article_key,
                    label=f"Art. {article_key}",
                    source=entry.source,
                    confidence=min(0.95, 0.18 + score / 14.0),
                )
                if (resolved_entry.kind, resolved_entry.key) in seen:
                    continue
                seen.add((resolved_entry.kind, resolved_entry.key))
                resolved.append(resolved_entry)
                selected_for_query += 1
                hydrated.append(
                    PlannerEntryPoint(
                        kind="article",
                        lookup_value=article_key,
                        source=entry.source,
                        confidence=resolved_entry.confidence,
                        label=f"Art. {article_key}",
                        resolved_key=article_key,
                    )
                )
                if selected_for_query >= per_query_limit:
                    break
            continue
        hydrated.append(entry)

    return tuple(resolved), tuple(hydrated)


def _retrieve_from_resolved_entries(
    *,
    snapshot: GraphArtifactSnapshot,
    plan: GraphRetrievalPlan,
    resolved_entries: tuple[_ResolvedEntry, ...],
) -> GraphEvidenceBundle:
    if not resolved_entries:
        diagnostics = {
            "artifacts_dir": str(snapshot.artifacts_dir),
            "resolved_entry_count": 0,
            "planner_query_mode": plan.query_mode,
            "temporal_context": plan.temporal_context.to_dict(),
        }
        return GraphEvidenceBundle(
            primary_articles=(),
            connected_articles=(),
            related_reforms=(),
            support_documents=(),
            citations=(),
            diagnostics=diagnostics,
        )

    predecessors: dict[tuple[str, str], tuple[tuple[str, str], _Neighbor] | None] = {}
    distances: dict[tuple[str, str], int] = {}
    discovery_scores: dict[tuple[str, str], float] = {}
    queue: deque[tuple[tuple[str, str], int]] = deque()
    discovered_edges = 0

    for entry in resolved_entries:
        node = (entry.kind, entry.key)
        predecessors[node] = None
        distances[node] = 0
        discovery_scores[node] = max(discovery_scores.get(node, 0.0), entry.confidence + 2.0)
        queue.append((node, 0))

    while queue and len(distances) < plan.traversal_budget.max_nodes and discovered_edges < plan.traversal_budget.max_edges:
        node, depth = queue.popleft()
        if depth >= plan.traversal_budget.max_hops:
            continue
        for neighbor in sorted_neighbors(snapshot=snapshot, node=node, plan=plan):
            discovered_edges += 1
            other = (neighbor.other_kind, neighbor.other_key)
            candidate_score = discovery_scores.get(node, 0.0) + neighbor_bonus(
                plan=plan,
                neighbor=neighbor,
            )
            if other not in distances:
                distances[other] = depth + 1
                predecessors[other] = (node, neighbor)
                discovery_scores[other] = candidate_score
                if len(distances) >= plan.traversal_budget.max_nodes:
                    break
                queue.append((other, depth + 1))
            elif candidate_score > discovery_scores.get(other, 0.0):
                predecessors[other] = (node, neighbor)
                discovery_scores[other] = candidate_score
        if len(distances) >= plan.traversal_budget.max_nodes:
            break

    seed_articles = tuple(
        entry.key
        for entry in resolved_entries
        if entry.kind == "ArticleNode" and entry.key in snapshot.articles
    )
    primary_articles = _select_article_evidence(
        snapshot=snapshot,
        article_keys=seed_articles,
        distances=distances,
        predecessors=predecessors,
        discovery_scores=discovery_scores,
        limit=plan.evidence_bundle_shape.primary_article_limit,
        plan=plan,
    )
    primary_source_paths = tuple(
        item.source_path
        for item in primary_articles
        if str(item.source_path or "").strip()
    )
    primary_topic_keys = tuple(
        dict.fromkeys(
            str(manifest_row.get("topic_key") or "").strip()
            for item in primary_articles
            for manifest_row in (
                snapshot.docs_by_source_path.get(str(item.source_path or "")) or {},
            )
            if str(manifest_row.get("topic_key") or "").strip()
        )
    )
    connected_articles = _select_article_evidence(
        snapshot=snapshot,
        article_keys=tuple(
            key
            for kind, key in distances
            if kind == "ArticleNode" and key not in seed_articles
        ),
        distances=distances,
        predecessors=predecessors,
        discovery_scores=discovery_scores,
        limit=plan.evidence_bundle_shape.connected_article_limit,
        plan=plan,
        primary_source_paths=primary_source_paths,
        primary_topic_keys=primary_topic_keys,
    )
    related_reforms = _select_reform_evidence(
        snapshot=snapshot,
        distances=distances,
        predecessors=predecessors,
        discovery_scores=discovery_scores,
        limit=plan.evidence_bundle_shape.related_reform_limit,
        plan=plan,
    )

    support_documents, citations = _select_support_documents(
        snapshot=snapshot,
        plan=plan,
        primary_articles=primary_articles,
        connected_articles=connected_articles,
    )
    diagnostics = {
        "artifacts_dir": str(snapshot.artifacts_dir),
        "resolved_entry_count": len(resolved_entries),
        "resolved_entries": [
            {
                "kind": entry.kind,
                "key": entry.key,
                "label": entry.label,
                "source": entry.source,
                "confidence": round(float(entry.confidence), 4),
            }
            for entry in resolved_entries
        ],
        "discovered_node_count": len(distances),
        "planner_query_mode": plan.query_mode,
        "temporal_context": plan.temporal_context.to_dict(),
    }
    return GraphEvidenceBundle(
        primary_articles=primary_articles,
        connected_articles=connected_articles,
        related_reforms=related_reforms,
        support_documents=support_documents,
        citations=citations,
        diagnostics=diagnostics,
    )


def _select_article_evidence(
    *,
    snapshot: GraphArtifactSnapshot,
    article_keys: tuple[str, ...],
    distances: dict[tuple[str, str], int],
    predecessors: dict[tuple[str, str], tuple[tuple[str, str], _Neighbor] | None],
    discovery_scores: dict[tuple[str, str], float],
    limit: int,
    plan: GraphRetrievalPlan,
    primary_source_paths: tuple[str, ...] = (),
    primary_topic_keys: tuple[str, ...] = (),
) -> tuple[GraphEvidenceItem, ...]:
    rows: list[GraphEvidenceItem] = []
    seen: set[str] = set()
    primary_source_path_set = {
        str(path).strip()
        for path in primary_source_paths
        if str(path or "").strip()
    }
    primary_topic_key_set = {
        str(topic).strip()
        for topic in primary_topic_keys
        if str(topic or "").strip()
    }
    ordered_keys = list(
        dict.fromkeys(
            sorted(
                article_keys,
                key=lambda key: (
                    distances.get(("ArticleNode", key), 99),
                    -article_temporal_bonus(
                        article=snapshot.articles.get(key, {}),
                        temporal_context=plan.temporal_context,
                    ),
                    -discovery_scores.get(("ArticleNode", key), 0.0),
                    key,
                ),
            )
        )
    )
    if article_keys:
        explicit_order = {key: index for index, key in enumerate(article_keys)}
        ordered_keys.sort(
            key=lambda key: (
                explicit_order.get(key, len(explicit_order) + distances.get(("ArticleNode", key), 99)),
                distances.get(("ArticleNode", key), 99),
                -article_temporal_bonus(
                    article=snapshot.articles.get(key, {}),
                    temporal_context=plan.temporal_context,
                ),
                -discovery_scores.get(("ArticleNode", key), 0.0),
                key,
            )
        )
    for article_key in ordered_keys:
        if article_key in seen or article_key not in snapshot.articles:
            continue
        relation_path = build_relation_path(
            node=("ArticleNode", article_key),
            predecessors=predecessors,
        )
        if primary_source_path_set and not should_keep_connected_article(
            snapshot=snapshot,
            article_key=article_key,
            relation_path=relation_path,
            plan=plan,
            primary_source_paths=primary_source_path_set,
            primary_topic_keys=primary_topic_key_set,
        ):
            continue
        seen.add(article_key)
        rows.append(
            _article_evidence_item(
                snapshot=snapshot,
                article_key=article_key,
                distance=distances.get(("ArticleNode", article_key), 0),
                predecessor=predecessors.get(("ArticleNode", article_key)),
                predecessors=predecessors,
                score=discovery_scores.get(("ArticleNode", article_key), 0.0),
                plan=plan,
                relation_path=relation_path,
            )
        )
        if len(rows) >= limit:
            break
    return tuple(rows)


def _article_evidence_item(
    *,
    snapshot: GraphArtifactSnapshot,
    article_key: str,
    distance: int,
    predecessor: tuple[tuple[str, str], _Neighbor] | None,
    predecessors: dict[tuple[str, str], tuple[tuple[str, str], _Neighbor] | None],
    score: float,
    plan: GraphRetrievalPlan,
    relation_path: tuple[GraphPathStep, ...] | None = None,
) -> GraphEvidenceItem:
    article = snapshot.articles[article_key]
    if relation_path is None:
        relation_path = build_relation_path(
            node=("ArticleNode", article_key),
            predecessors=predecessors,
        )
    why = explain_article_relevance(
        article=article,
        relation_path=relation_path,
        plan=plan,
    )
    return GraphEvidenceItem(
        node_kind="ArticleNode",
        node_key=article_key,
        title=str(article.get("heading") or f"Articulo {article_key}"),
        excerpt=article_excerpt(
            article=article,
            temporal_context=plan.temporal_context,
            limit=plan.evidence_bundle_shape.snippet_char_limit,
        ),
        source_path=str(article.get("source_path") or "") or None,
        score=score,
        hop_distance=distance,
        why=why,
        relation_path=relation_path,
    )


def _select_reform_evidence(
    *,
    snapshot: GraphArtifactSnapshot,
    distances: dict[tuple[str, str], int],
    predecessors: dict[tuple[str, str], tuple[tuple[str, str], _Neighbor] | None],
    discovery_scores: dict[tuple[str, str], float],
    limit: int,
    plan: GraphRetrievalPlan,
) -> tuple[GraphEvidenceItem, ...]:
    reforms = sorted(
        (
            key
            for kind, key in distances
            if kind == "ReformNode"
        ),
        key=lambda key: (
            reform_priority_rank(
                reform_key=key,
                temporal_context=plan.temporal_context,
            ),
            distances.get(("ReformNode", key), 99),
            -discovery_scores.get(("ReformNode", key), 0.0),
            key,
        ),
    )
    rows: list[GraphEvidenceItem] = []
    for reform_key in reforms[:limit]:
        relation_path = build_relation_path(
            node=("ReformNode", reform_key),
            predecessors=predecessors,
        )
        rows.append(
            GraphEvidenceItem(
                node_kind="ReformNode",
                node_key=reform_key,
                title=str(snapshot.reforms.get(reform_key, {}).get("citation") or reform_key),
                excerpt=snippet(
                    "Ruta normativa relacionada por cadena de modificaciones o referencias.",
                    limit=180,
                ),
                source_path=None,
                score=discovery_scores.get(("ReformNode", reform_key), 0.0),
                hop_distance=distances.get(("ReformNode", reform_key), 0),
                why=reform_why(
                    reform_key=reform_key,
                    temporal_context=plan.temporal_context,
                ),
                relation_path=relation_path,
            )
        )
    return tuple(rows)


def _select_support_documents(
    *,
    snapshot: GraphArtifactSnapshot,
    plan: GraphRetrievalPlan,
    primary_articles: tuple[GraphEvidenceItem, ...],
    connected_articles: tuple[GraphEvidenceItem, ...],
) -> tuple[tuple[GraphSupportDocument, ...], tuple[Citation, ...]]:
    candidate_docs: list[tuple[int, str, dict[str, Any], str]] = []
    seen_paths: set[str] = set()
    topic_hints = {
        str(topic).strip()
        for topic in plan.topic_hints
        if str(topic or "").strip()
    }
    ordered_topic_hints = tuple(
        str(topic).strip()
        for topic in plan.topic_hints
        if str(topic or "").strip()
    )
    query_tokens = support_doc_query_tokens(plan)
    primary_source_paths = {
        str(item.source_path).strip()
        for item in primary_articles
        if str(item.source_path or "").strip()
    }
    primary_topic_keys = {
        str(manifest_row.get("topic_key") or "").strip()
        for item in primary_articles
        for manifest_row in (
            snapshot.docs_by_source_path.get(str(item.source_path or "")) or {},
        )
        if str(manifest_row.get("topic_key") or "").strip()
    }

    for evidence in (*primary_articles, *connected_articles):
        if not evidence.source_path:
            continue
        manifest_row = snapshot.docs_by_source_path.get(evidence.source_path)
        if not manifest_row or manifest_row.get("canonical_blessing_status") != "ready":
            continue
        source_path = str(manifest_row.get("source_path") or "")
        if source_path in seen_paths:
            continue
        seen_paths.add(source_path)
        candidate_docs.append((0, source_path, manifest_row, "source_doc_for_graph_article"))

    expansion_topics = set(topic_hints)
    if not expansion_topics:
        expansion_topics.update(primary_topic_keys)
    for topic_key in sorted(topic for topic in expansion_topics if topic):
        for topic_doc in snapshot.ready_docs_by_topic.get(topic_key, ()):
            topic_source = str(topic_doc.get("source_path") or "")
            if topic_source in seen_paths:
                continue
            if (
                plan.temporal_context.historical_query_intent
                and str(topic_doc.get("family") or "") != "normativa"
            ):
                continue
            topic_doc_topic = str(topic_doc.get("topic_key") or "").strip()
            if (
                topic_source not in primary_source_paths
                and topic_key not in topic_hints
                and topic_doc_topic not in primary_topic_keys
            ):
                continue
            seen_paths.add(topic_source)
            reason = "topic_support_doc"
            if topic_key in topic_hints:
                reason = "topic_hint_support_doc"
            candidate_docs.append((1, topic_source, topic_doc, reason))

    candidate_docs.sort(
        key=lambda item: (
            item[0],
            _FAMILY_RANK.get(str(item[2].get("family") or ""), 9),
            -support_doc_query_overlap(item[2], query_tokens),
            str(item[2].get("relative_path") or ""),
        )
    )
    candidate_docs = _diversify_support_candidates(
        candidate_docs=candidate_docs,
        limit=plan.evidence_bundle_shape.support_document_limit,
        preferred_topics=ordered_topic_hints,
        query_tokens=query_tokens,
        reserve_enrichment_slots=(
            not plan.temporal_context.historical_query_intent
            and plan.query_mode in {"obligation_chain", "computation_chain", "general_graph_research"}
        ),
    )
    selected_docs: list[GraphSupportDocument] = []
    citations: list[Citation] = []
    for _, _, manifest_row, reason in candidate_docs:
        selected_docs.append(
            GraphSupportDocument(
                relative_path=str(manifest_row.get("relative_path") or ""),
                source_path=str(manifest_row.get("source_path") or ""),
                title_hint=str(manifest_row.get("title_hint") or manifest_row.get("relative_path") or ""),
                family=str(manifest_row.get("family") or "") or None,
                knowledge_class=str(manifest_row.get("knowledge_class") or "") or None,
                topic_key=str(manifest_row.get("topic_key") or "") or None,
                subtopic_key=str(manifest_row.get("subtopic_key") or "") or None,
                canonical_blessing_status=str(manifest_row.get("canonical_blessing_status") or "") or None,
                graph_target=bool(manifest_row.get("graph_target")),
                reason=reason,
            )
        )
        citations.append(
            Citation.from_document(
                manifest_row_to_document(manifest_row, workspace_root=_WORKSPACE_ROOT)
            )
        )
        if len(selected_docs) >= plan.evidence_bundle_shape.support_document_limit:
            break
    return tuple(selected_docs), tuple(citations)


def _diversify_support_candidates(
    *,
    candidate_docs: list[tuple[int, str, dict[str, Any], str]],
    limit: int,
    preferred_topics: tuple[str, ...],
    query_tokens: tuple[str, ...],
    reserve_enrichment_slots: bool,
) -> list[tuple[int, str, dict[str, Any], str]]:
    if limit <= 0 or len(candidate_docs) <= 1:
        return candidate_docs

    selected_paths: set[str] = set()
    diversified: list[tuple[int, str, dict[str, Any], str]] = []

    source_docs = [item for item in candidate_docs if item[3] == "source_doc_for_graph_article"]
    topic_docs = [item for item in candidate_docs if item[3] != "source_doc_for_graph_article"]
    family_picks: list[tuple[int, str, dict[str, Any], str]] = []

    if reserve_enrichment_slots:
        for family in ("practica", "interpretacion"):
            family_pick = _pick_family_doc(
                topic_docs=topic_docs,
                selected_paths=selected_paths,
                family=family,
                preferred_topics=preferred_topics,
                query_tokens=query_tokens,
            )
            if family_pick is None:
                continue
            family_picks.append(family_pick)
            selected_paths.add(family_pick[1])

    source_cap = limit
    if family_picks:
        source_cap = max(1, limit - len(family_picks))

    for item in source_docs:
        diversified.append(item)
        selected_paths.add(item[1])
        if len(diversified) >= source_cap:
            break

    for family_pick in family_picks:
        diversified.append(family_pick)
        if len(diversified) >= limit:
            return diversified

    for item in topic_docs:
        if item[1] in selected_paths:
            continue
        diversified.append(item)
        selected_paths.add(item[1])
        if len(diversified) >= limit:
            break

    return diversified


def _pick_family_doc(
    *,
    topic_docs: list[tuple[int, str, dict[str, Any], str]],
    selected_paths: set[str],
    family: str,
    preferred_topics: tuple[str, ...],
    query_tokens: tuple[str, ...],
) -> tuple[int, str, dict[str, Any], str] | None:
    preferred_rank = {topic: index for index, topic in enumerate(preferred_topics)}
    candidates = [
        item
        for item in topic_docs
        if item[1] not in selected_paths and str(item[2].get("family") or "") == family
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            _family_doc_relevance_score(
                row=item[2],
                query_tokens=query_tokens,
                preferred_rank=preferred_rank,
            ),
            -item[0],
            str(item[2].get("relative_path") or ""),
        ),
    )


def _support_topic_exact_token_match(
    row: dict[str, Any],
    query_tokens: tuple[str, ...],
) -> int:
    topic_key = str(row.get("topic_key") or "").strip().lower()
    return int(bool(topic_key and topic_key in set(query_tokens)))


def _family_doc_relevance_score(
    *,
    row: dict[str, Any],
    query_tokens: tuple[str, ...],
    preferred_rank: dict[str, int],
) -> float:
    topic_key = str(row.get("topic_key") or "").strip()
    overlap = support_doc_query_overlap(row, query_tokens)
    primary_bonus = 1.0 if preferred_rank.get(topic_key) == 0 and overlap >= 2.0 else 0.0
    preferred_bonus = 0.25 if topic_key in preferred_rank else 0.0
    exact_topic_bonus = 0.25 * _support_topic_exact_token_match(row, query_tokens)
    rank_penalty = preferred_rank.get(topic_key, 99) * 0.05
    return overlap + primary_bonus + preferred_bonus + exact_topic_bonus - rank_penalty


def _best_support_doc_match(
    candidates: list[tuple[int, str, dict[str, Any], str]],
    query_tokens: tuple[str, ...],
) -> tuple[int, str, dict[str, Any], str] | None:
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            support_doc_query_overlap(item[2], query_tokens),
            -item[0],
            -_FAMILY_RANK.get(str(item[2].get("family") or ""), 9),
            str(item[2].get("relative_path") or ""),
        ),
    )


__all__ = [
    "GraphArtifactSnapshot",
    "load_graph_artifact_snapshot",
    "retrieve_graph_evidence",
]
