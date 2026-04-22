"""Tests for the additive Falkor delta loader (Phase 5)."""

from __future__ import annotations

from typing import Any

from lia_graph.graph.client import GraphClient
from lia_graph.graph.schema import (
    EdgeKind,
    GraphEdgeRecord,
    GraphNodeRecord,
    NodeKind,
    default_graph_schema,
)
from lia_graph.ingestion.baseline_snapshot import BaselineDocument
from lia_graph.ingestion.classifier import ClassifiedEdge
from lia_graph.ingestion.delta_planner import CorpusDelta, DeltaEntry, DiskDocument
from lia_graph.ingestion.loader import build_graph_delta_plan
from lia_graph.ingestion.parser import ParsedArticle


def _article(key: str, source_path: str) -> ParsedArticle:
    return ParsedArticle(
        article_key=key,
        article_number=key,
        heading=f"Art {key}",
        body=f"Body {key}",
        full_text=f"# {key}\nBody",
        status="vigente",
        source_path=source_path,
        paragraph_markers=(),
        reform_references=(),
        annotations=(),
    )


def _edge(source: str, target: str, kind: EdgeKind = EdgeKind.REFERENCES, target_kind: NodeKind = NodeKind.ARTICLE) -> ClassifiedEdge:
    return ClassifiedEdge(
        record=GraphEdgeRecord(
            kind=kind,
            source_kind=NodeKind.ARTICLE,
            source_key=source,
            target_kind=target_kind,
            target_key=target,
            properties={"raw_reference": f"ref_{source}_{target}"},
        ),
        confidence=0.9,
        rule="test_rule",
    )


def _baseline_doc(relative_path: str, doc_id: str) -> BaselineDocument:
    return BaselineDocument(
        doc_id=doc_id,
        relative_path=relative_path,
        content_hash="h",
        doc_fingerprint="fp",
        retired_at=None,
        last_delta_id=None,
        sync_generation="gen_active_rolling",
    )


def _delta_with(
    *,
    added: tuple[str, ...] = (),
    modified: tuple[tuple[str, str], ...] = (),
    removed: tuple[tuple[str, str], ...] = (),
) -> CorpusDelta:
    return CorpusDelta(
        delta_id="delta_test",
        baseline_generation_id="gen_active_rolling",
        added=tuple(
            DeltaEntry(relative_path=p, disk=DiskDocument(relative_path=p, content_hash="h"), baseline=None)
            for p in added
        ),
        modified=tuple(
            DeltaEntry(
                relative_path=p,
                disk=DiskDocument(relative_path=p, content_hash="h"),
                baseline=_baseline_doc(p, doc_id),
            )
            for p, doc_id in modified
        ),
        removed=tuple(
            DeltaEntry(
                relative_path=p,
                disk=None,
                baseline=_baseline_doc(p, doc_id),
            )
            for p, doc_id in removed
        ),
        unchanged=(),
    )


# (a) empty delta → empty plan.
def test_empty_delta_plan_is_empty() -> None:
    plan = build_graph_delta_plan(
        _delta_with(),
        delta_articles=[],
        delta_edges=[],
    )
    assert plan.statements == ()
    assert plan.nodes == ()
    assert plan.edges == ()


# (b) added-only → only MERGE statements for new nodes + edges.
def test_added_only_delta_plan_emits_merges_only() -> None:
    delta = _delta_with(added=("a.md",))
    articles = [_article("art1", "/abs/a.md"), _article("art2", "/abs/a.md")]
    edges = [_edge("art1", "art2")]
    plan = build_graph_delta_plan(
        delta,
        delta_articles=articles,
        delta_edges=edges,
    )
    kinds = [s.description.split(":")[0].split(" ")[0] for s in plan.statements]
    # No DETACH, no Delete-outbound — only Upsert (MERGE).
    for stmt in plan.statements:
        assert "DETACH DELETE" not in stmt.query
        assert "DELETE rel" not in stmt.query
    assert all("MERGE" in s.query for s in plan.statements)


# (c) modified-only → DELETE outbound + MERGE.
def test_modified_only_emits_delete_outbound_then_merges() -> None:
    delta = _delta_with(modified=(("a.md", "doc_a"),))
    # Orchestrator passes in the set of article keys whose outbound edges
    # should be wiped before re-MERGE. We stash that on the delta object via
    # a duck-typed attribute (see delta_planner.CorpusDelta's API — Phase 6
    # orchestrator computes this). For Phase 5 tests we set it directly.
    object.__setattr__(delta, "modified_article_keys", ("artA", "artB"))
    articles = [_article("artA", "/abs/a.md"), _article("artB", "/abs/a.md")]
    edges = [_edge("artA", "artB")]
    plan = build_graph_delta_plan(
        delta,
        delta_articles=articles,
        delta_edges=edges,
    )
    # Statement order: all DELETEs before any MERGE.
    saw_merge = False
    for stmt in plan.statements:
        if "MERGE" in stmt.query:
            saw_merge = True
        elif "DELETE rel" in stmt.query:
            assert not saw_merge, "DELETE must precede MERGE in the plan"
    # At least two DELETE outbound statements (one per modified article key).
    delete_count = sum(1 for s in plan.statements if "DELETE rel" in s.query)
    assert delete_count == 2


# (d) removed-only → DETACH DELETE for removed article nodes only.
def test_removed_only_emits_detach_deletes_only() -> None:
    delta = _delta_with(removed=(("gone.md", "doc_gone"),))
    plan = build_graph_delta_plan(
        delta,
        delta_articles=[],
        delta_edges=[],
        retired_article_keys=["art_gone_1", "art_gone_2"],
    )
    detach_count = sum(1 for s in plan.statements if "DETACH DELETE" in s.query)
    assert detach_count == 2
    # No MERGE or DELETE-rel statements when nothing is being added/modified.
    for stmt in plan.statements:
        assert "MERGE" not in stmt.query
        assert "DELETE rel" not in stmt.query


# (e) mixed → statements in dependency order (deletes before merges).
def test_mixed_plan_statement_order() -> None:
    delta = _delta_with(
        added=("new.md",),
        modified=(("mod.md", "doc_mod"),),
        removed=(("gone.md", "doc_gone"),),
    )
    object.__setattr__(delta, "modified_article_keys", ("artM",))
    articles = [_article("artM", "/abs/mod.md"), _article("artN", "/abs/new.md")]
    edges = [_edge("artN", "artM")]
    plan = build_graph_delta_plan(
        delta,
        delta_articles=articles,
        delta_edges=edges,
        retired_article_keys=["artG"],
    )
    # Classify each statement by kind.
    kinds: list[str] = []
    for stmt in plan.statements:
        if "DETACH DELETE" in stmt.query:
            kinds.append("detach")
        elif "DELETE rel" in stmt.query:
            kinds.append("delete_rel")
        elif "MERGE" in stmt.query and "-[rel:" in stmt.query:
            kinds.append("merge_edge")
        elif "MERGE" in stmt.query:
            kinds.append("merge_node")
        else:
            kinds.append("other")
    # Order: all detaches, all delete_rels, then merge_nodes, then merge_edges.
    order_priority = {"detach": 0, "delete_rel": 1, "merge_node": 2, "merge_edge": 3, "other": 4}
    prev = -1
    for k in kinds:
        this = order_priority[k]
        assert this >= prev, f"out-of-order statement: saw {k} after priority {prev}"
        prev = this


# (f) promoted dangling edges included in MERGE set.
def test_promoted_dangling_edges_are_merged() -> None:
    delta = _delta_with(added=("new.md",))
    articles = [_article("new_art_A", "/abs/new.md")]
    promoted = (
        GraphEdgeRecord(
            kind=EdgeKind.REFERENCES,
            source_kind=NodeKind.ARTICLE,
            source_key="old_art_X",
            target_kind=NodeKind.ARTICLE,
            target_key="new_art_A",
            properties={"promoted_from": "dangling"},
        ),
    )
    plan = build_graph_delta_plan(
        delta,
        delta_articles=articles,
        delta_edges=[],
        promoted_dangling_edges=promoted,
    )
    edge_keys = {(e.source_key, e.target_key, e.kind.value) for e in plan.edges}
    assert ("old_art_X", "new_art_A", EdgeKind.REFERENCES.value) in edge_keys


# (g) no DETACH DELETE for DocumentNode keys still in the active corpus.
def test_detach_is_article_scoped_only() -> None:
    delta = _delta_with(added=("new.md",))
    articles = [_article("artN", "/abs/new.md")]
    plan = build_graph_delta_plan(
        delta,
        delta_articles=articles,
        delta_edges=[],
    )
    for stmt in plan.statements:
        assert "DETACH DELETE" not in stmt.query


# (h) plan re-applied twice → same statement shape (Falkor MERGE-idempotent).
def test_plan_is_deterministic_for_same_inputs() -> None:
    delta = _delta_with(added=("new.md",))
    articles = [_article("artN", "/abs/new.md")]
    edges = [_edge("artN", "artN")]
    plan1 = build_graph_delta_plan(delta, delta_articles=articles, delta_edges=edges)
    plan2 = build_graph_delta_plan(delta, delta_articles=articles, delta_edges=edges)
    assert [s.query for s in plan1.statements] == [s.query for s in plan2.statements]
    assert [s.description for s in plan1.statements] == [s.description for s in plan2.statements]


# ---- Graph client stage helpers ----


def test_stage_detach_delete_generates_cypher() -> None:
    client = GraphClient(schema=default_graph_schema())
    stmt = client.stage_detach_delete(NodeKind.ARTICLE, "art_x")
    assert "DETACH DELETE" in stmt.query
    assert "Article" in stmt.query  # kind.value
    assert stmt.parameters.get("key") == "art_x"


def test_stage_delete_outbound_edges_with_relation_subset() -> None:
    client = GraphClient(schema=default_graph_schema())
    stmt = client.stage_delete_outbound_edges(
        NodeKind.ARTICLE, "art_x", relation_subset=[EdgeKind.REFERENCES, EdgeKind.MODIFIES]
    )
    assert "DELETE rel" in stmt.query
    # Relation subset alphabetically sorted.
    assert "[rel:MODIFIES|REFERENCES]" in stmt.query
    assert stmt.parameters.get("source_key") == "art_x"


def test_stage_delete_outbound_edges_without_subset_is_all_kinds() -> None:
    client = GraphClient(schema=default_graph_schema())
    stmt = client.stage_delete_outbound_edges(NodeKind.ARTICLE, "art_x")
    assert "[rel]" in stmt.query
