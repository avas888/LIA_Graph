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


# -----------------------------------------------------------------------------
# Regression (2026-04-23 Phase 9.A crash #3): parser fallback articles that
# carry ``article_number=""`` must not crash the Falkor staging pipeline.
# Root cause: ``graph/schema.py`` declares ArticleNode.required_fields =
# ("article_number", "heading", "text_current", "status"); two parser paths
# (_section_fallback, _whole_document_fallback) emit articles with an empty
# article_number for docs without a numbered-article structure. Fix: filter
# those out of the Falkor node + article-sourced edge builders.
# -----------------------------------------------------------------------------


def _fallback_article(key: str, source_path: str) -> ParsedArticle:
    """Simulates a parser fallback output: has a slug key but no article_number.

    Mirrors what ``_section_fallback`` / ``_whole_document_fallback`` in
    ``parser.py`` emit for heading-only or prose-only docs.
    """
    return ParsedArticle(
        article_key=key,
        article_number="",  # THE KEY BIT: empty, would fail schema validation
        heading=f"Section: {key}",
        body=f"Section body for {key}",
        full_text=f"## Section: {key}\nbody",
        status="vigente",
        source_path=source_path,
        paragraph_markers=(),
        reform_references=(),
        annotations=(),
    )


def test_falkor_staging_includes_prose_only_articles_with_whole_keys() -> None:
    """v4: prose-only articles (article_number="") are now ELIGIBLE.

    They become ArticleNodes keyed by `whole::{source_path}` (doc-scoped so
    prose docs don't collide on the shared `WHOLE_DOC_ARTICLE_KEY`) and
    carry `is_prose_only=True`. Proper numbered articles keep their
    article_key-based graph key unchanged.

    See docs/next/ingestionfix_v4.md §5 Phase 1.
    """
    proper = _article("123", source_path="docs/proper.md")
    fallback_section = _fallback_article("1-norma-base", source_path="docs/norma_base.md")
    fallback_doc = _fallback_article("doc", source_path="docs/whole_doc.md")
    plan = build_graph_delta_plan(
        _delta_with(added=("docs/proper.md", "docs/norma_base.md", "docs/whole_doc.md")),
        delta_articles=(proper, fallback_section, fallback_doc),
        delta_edges=(),
    )
    article_nodes = [n for n in plan.nodes if n.kind is NodeKind.ARTICLE]
    # v4: all three articles land as ArticleNodes.
    assert len(article_nodes) == 3
    by_key = {n.key: n for n in article_nodes}
    assert "123" in by_key
    assert "whole::docs/norma_base.md" in by_key
    assert "whole::docs/whole_doc.md" in by_key
    assert by_key["123"].properties["is_prose_only"] is False
    assert by_key["whole::docs/norma_base.md"].properties["is_prose_only"] is True
    assert by_key["whole::docs/whole_doc.md"].properties["is_prose_only"] is True


def test_falkor_staging_tema_edges_include_prose_only_with_graph_key() -> None:
    """v4: TEMA + HAS_SUBTOPIC edges fire for both numbered AND prose-only
    articles. Prose-only edges use the `whole::{source_path}` graph key.

    Callers must key `article_topics` / `article_subtopics` by
    `_graph_article_key(article)`, not by the raw `article.article_key`
    (the latter would orphan against the remapped ArticleNode.key).
    """
    from lia_graph.ingestion.loader import SubtopicBinding, _graph_article_key

    proper = _article("123", source_path="docs/proper.md")
    fallback = _fallback_article("1-norma-base", source_path="docs/norma_base.md")
    proper_gkey = _graph_article_key(proper)          # "123"
    fallback_gkey = _graph_article_key(fallback)      # "whole::docs/norma_base.md"

    plan = build_graph_delta_plan(
        _delta_with(added=("docs/proper.md", "docs/norma_base.md")),
        delta_articles=(proper, fallback),
        delta_edges=(),
        article_topics={proper_gkey: "laboral", fallback_gkey: "laboral"},
        article_subtopics={
            proper_gkey: SubtopicBinding(
                sub_topic_key="contrato_laboral",
                parent_topic="laboral",
                label="Contrato laboral",
            ),
            fallback_gkey: SubtopicBinding(
                sub_topic_key="contrato_laboral",
                parent_topic="laboral",
                label="Contrato laboral",
            ),
        },
    )
    tema_edges = [e for e in plan.edges if e.kind is EdgeKind.TEMA]
    has_subtopic_edges = [e for e in plan.edges if e.kind is EdgeKind.HAS_SUBTOPIC]
    # Both articles get TEMA and HAS_SUBTOPIC edges in v4.
    assert {e.source_key for e in tema_edges} == {proper_gkey, fallback_gkey}
    assert {e.source_key for e in has_subtopic_edges} == {proper_gkey, fallback_gkey}


def test_falkor_staging_all_fallback_articles_get_unique_nodes() -> None:
    """v4: a delta of prose-only docs lands two DISTINCT ArticleNodes —
    each scoped by source_path — not one collapsed `article_key="doc"`
    node as the pre-v4 behavior would have produced if eligibility had
    allowed it through."""
    articles = (
        _fallback_article("1-norma-base", source_path="docs/a.md"),
        _fallback_article("doc", source_path="docs/b.md"),
    )
    plan = build_graph_delta_plan(
        _delta_with(added=("docs/a.md", "docs/b.md")),
        delta_articles=articles,
        delta_edges=(),
    )
    article_nodes = [n for n in plan.nodes if n.kind is NodeKind.ARTICLE]
    assert len(article_nodes) == 2
    keys = {n.key for n in article_nodes}
    assert keys == {"whole::docs/a.md", "whole::docs/b.md"}


def test_falkor_staging_whitespace_article_number_treated_as_prose_only() -> None:
    """v4: whitespace-only article_number is semantically equivalent to
    empty — the article is eligible, gets a `whole::{source_path}` graph
    key, and is flagged `is_prose_only=True`."""
    whitespace_article = ParsedArticle(
        article_key="ws_art",
        article_number="   ",
        heading="Heading",
        body="body",
        full_text="body",
        status="vigente",
        source_path="docs/x.md",
        paragraph_markers=(),
        reform_references=(),
        annotations=(),
    )
    plan = build_graph_delta_plan(
        _delta_with(added=("docs/x.md",)),
        delta_articles=(whitespace_article,),
        delta_edges=(),
    )
    article_nodes = [n for n in plan.nodes if n.kind is NodeKind.ARTICLE]
    assert len(article_nodes) == 1
    assert article_nodes[0].key == "whole::docs/x.md"
    assert article_nodes[0].properties["is_prose_only"] is True


# =============================================================================
# Expert-review edge cases (Falkor staging, consulted 2026-04-23)
# =============================================================================

# (l) #1 SubTopicNode: a SubtopicBinding with empty parent_topic/label must
# NOT reach stage_node — same crash class as the ArticleNode bug.
def test_subtopic_with_empty_parent_topic_is_skipped() -> None:
    from lia_graph.ingestion.loader import SubtopicBinding

    proper = _article("123", source_path="docs/proper.md")
    plan = build_graph_delta_plan(
        _delta_with(added=("docs/proper.md",)),
        delta_articles=(proper,),
        delta_edges=(),
        article_subtopics={
            "123": SubtopicBinding(
                sub_topic_key="contrato_laboral",
                parent_topic="",          # empty — would crash schema validator
                label="Contrato laboral",
            )
        },
    )
    subtopic_nodes = [n for n in plan.nodes if n.kind is NodeKind.SUBTOPIC]
    assert subtopic_nodes == []


def test_subtopic_with_whitespace_label_is_skipped() -> None:
    from lia_graph.ingestion.loader import SubtopicBinding

    proper = _article("123", source_path="docs/proper.md")
    plan = build_graph_delta_plan(
        _delta_with(added=("docs/proper.md",)),
        delta_articles=(proper,),
        delta_edges=(),
        article_subtopics={
            "123": SubtopicBinding(
                sub_topic_key="x",
                parent_topic="laboral",
                label="   ",    # whitespace-only
            )
        },
    )
    assert not [n for n in plan.nodes if n.kind is NodeKind.SUBTOPIC]


# (m) #2 ReformNode: an empty citation must not reach stage_node.
def test_reform_node_with_empty_citation_is_skipped() -> None:
    # Article whose reform_references contains a bogus empty reference.
    article = ParsedArticle(
        article_key="123",
        article_number="123",
        heading="Art 123",
        body="Body",
        full_text="# 123\nBody",
        status="vigente",
        source_path="docs/x.md",
        paragraph_markers=(),
        reform_references=("",),   # empty reference survived upstream
        annotations=(),
    )
    plan = build_graph_delta_plan(
        _delta_with(added=("docs/x.md",)),
        delta_articles=(article,),
        delta_edges=(),
    )
    reform_nodes = [n for n in plan.nodes if n.kind is NodeKind.REFORM]
    # All reform nodes present must have non-empty citation.
    for n in reform_nodes:
        assert str(n.properties.get("citation", "")).strip(), (
            f"ReformNode {n.key!r} has empty citation, would crash schema validator"
        )


# (n) #3 classifier edges whose source is a fallback article must be dropped.
def test_classifier_edge_from_fallback_article_is_dropped() -> None:
    proper = _article("123", source_path="docs/proper.md")
    fallback = _fallback_article("1-norma-base", source_path="docs/fallback.md")
    # Edge that the classifier (hypothetically) emitted sourced AT the fallback
    # article. It must not survive into the stage_edge stream.
    bad_edge = _edge(source="1-norma-base", target="123")
    plan = build_graph_delta_plan(
        _delta_with(added=("docs/proper.md", "docs/fallback.md")),
        delta_articles=(proper, fallback),
        delta_edges=(bad_edge,),
    )
    sourced_at_fallback = [
        e for e in plan.edges
        if e.source_kind is NodeKind.ARTICLE and e.source_key == "1-norma-base"
    ]
    assert sourced_at_fallback == []
    # Warning should surface so we can count the drop in diagnostics.
    assert any("non-schema" in w for w in plan.warnings)


def test_classifier_edge_to_fallback_article_is_dropped() -> None:
    proper = _article("123", source_path="docs/proper.md")
    fallback = _fallback_article("1-norma-base", source_path="docs/fallback.md")
    bad_edge = _edge(source="123", target="1-norma-base")
    plan = build_graph_delta_plan(
        _delta_with(added=("docs/proper.md", "docs/fallback.md")),
        delta_articles=(proper, fallback),
        delta_edges=(bad_edge,),
    )
    pointed_at_fallback = [
        e for e in plan.edges
        if e.target_kind is NodeKind.ARTICLE and e.target_key == "1-norma-base"
    ]
    assert pointed_at_fallback == []


# (o) #4 promoted_dangling_edges must also respect the eligibility filter.
def test_promoted_dangling_edge_targeting_fallback_is_dropped() -> None:
    proper = _article("123", source_path="docs/proper.md")
    fallback = _fallback_article("1-norma-base", source_path="docs/fallback.md")
    # A dangling edge that was waiting for "1-norma-base" to arrive. It did,
    # but as a fallback article — no ArticleNode materialized for it.
    dangling = GraphEdgeRecord(
        kind=EdgeKind.REFERENCES,
        source_kind=NodeKind.ARTICLE,
        source_key="999",           # some historical article from a prior reingest
        target_kind=NodeKind.ARTICLE,
        target_key="1-norma-base",
        properties={"raw_reference": "ref"},
    )
    plan = build_graph_delta_plan(
        _delta_with(added=("docs/proper.md", "docs/fallback.md")),
        delta_articles=(proper, fallback),
        delta_edges=(),
        promoted_dangling_edges=(dangling,),
    )
    assert not [e for e in plan.edges if e.target_key == "1-norma-base"]


# (p) External-article edges (target not in this delta at all) must be
# preserved — they refer to articles materialized by a prior reingest and
# Cypher's MATCH can still resolve them. The filter must NOT drop these.
def test_edge_to_external_article_not_in_delta_is_preserved() -> None:
    proper = _article("123", source_path="docs/proper.md")
    # normalize_classified_edges would normally drop edges whose ARTICLE target
    # isn't in the delta (they become dangling candidates). But promoted_dangling
    # edges are pre-resolved, so they legitimately reference external keys.
    pre_resolved = GraphEdgeRecord(
        kind=EdgeKind.REFERENCES,
        source_kind=NodeKind.ARTICLE,
        source_key="123",
        target_kind=NodeKind.ARTICLE,
        target_key="external_999",  # NOT in this delta, NOT ineligible
        properties={"raw_reference": "ref"},
    )
    plan = build_graph_delta_plan(
        _delta_with(added=("docs/proper.md",)),
        delta_articles=(proper,),
        delta_edges=(),
        promoted_dangling_edges=(pre_resolved,),
    )
    externals = [e for e in plan.edges if e.target_key == "external_999"]
    assert len(externals) == 1, (
        "External-article edge was dropped; filter should only skip endpoints "
        "we KNOW are ineligible, not everything outside the delta."
    )


# (q) #9 observability: the articles_skipped event payload must carry count +
# sample keys. Without this lock the bare-except earlier in the file could
# silently regress and mask a production issue.
#
# v4: the trigger shifted. Prose-only articles (empty article_number) no
# longer count as skipped — they're eligible via `whole::{source_path}`
# graph keys. The event now fires only for articles missing heading / text /
# status, which are the genuinely malformed cases the invariant targets.
def test_articles_skipped_event_payload_shape(monkeypatch) -> None:
    captured: list[tuple[str, dict]] = []

    def _capture(event_type: str, payload: dict) -> None:
        captured.append((event_type, payload))

    import lia_graph.instrumentation as instr
    monkeypatch.setattr(instr, "emit_event", _capture)

    proper = _article("123", source_path="docs/a.md")
    # Malformed articles — missing heading. These are what the event should
    # surface post-v4.
    malformed_1 = ParsedArticle(
        article_key="malf1", article_number="5", heading="", body="b",
        full_text="b", status="vigente", source_path="docs/b.md",
        paragraph_markers=(), reform_references=(), annotations=(),
    )
    malformed_2 = ParsedArticle(
        article_key="malf2", article_number="", heading="", body="b",
        full_text="b", status="vigente", source_path="docs/c.md",
        paragraph_markers=(), reform_references=(), annotations=(),
    )
    build_graph_delta_plan(
        _delta_with(added=("docs/a.md", "docs/b.md", "docs/c.md")),
        delta_articles=(proper, malformed_1, malformed_2),
        delta_edges=(),
    )
    events = [e for e in captured if e[0] == "ingest.graph.articles_skipped_nonschema"]
    assert len(events) == 1
    _, payload = events[0]
    assert payload["skipped"] == 2
    assert set(payload["sample_article_keys"]) <= {"malf1", "malf2"}
    assert "reason" in payload


# (r) #5 retired_article_keys with whitespace-only entries must not emit
# DETACH DELETE statements — those are unmatchable and hide orchestrator bugs.
def test_retired_article_keys_filter_whitespace_entries() -> None:
    plan = build_graph_delta_plan(
        _delta_with(removed=(("docs/x.md", "doc_x"),)),
        delta_articles=(),
        delta_edges=(),
        retired_article_keys=["", "   ", "\t", "real-key"],
    )
    detach_statements = [s for s in plan.statements if "DETACH DELETE" in s.query]
    # Only the single "real-key" should produce a DETACH DELETE. The key is
    # a bind parameter, not inlined into the Cypher string, so check params.
    assert len(detach_statements) == 1
    assert detach_statements[0].parameters.get("key") == "real-key"
