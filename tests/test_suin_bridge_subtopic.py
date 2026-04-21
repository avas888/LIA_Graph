"""Phase 5 bridge tests — SubTopic node/edge emission in graph load plan.

The name ``suin_bridge_subtopic`` follows the plan's naming; the actual
injection point is :func:`build_graph_load_plan` which is the canonical
graph-plan builder for both regular ingestion and SUIN-merged ingestion.
"""

from __future__ import annotations

from lia_graph.graph.schema import EdgeKind, NodeKind
from lia_graph.ingestion.loader import (
    SubtopicBinding,
    build_graph_load_plan,
)
from lia_graph.ingestion.parser import ParsedArticle


def _article(key: str, source_path: str = "/abs/doc.md") -> ParsedArticle:
    return ParsedArticle(
        article_key=key,
        article_number=key,
        heading=f"Art {key}",
        body="body",
        full_text=f"# Art {key}\nbody",
        status="vigente",
        source_path=source_path,
        paragraph_markers=(),
        reform_references=(),
        annotations=(),
    )


def test_article_with_subtopic_emits_subtopic_node_and_edge() -> None:
    articles = [_article("1")]
    bindings = {
        "1": SubtopicBinding(
            sub_topic_key="nomina_electronica",
            parent_topic="iva",
            label="Nómina electrónica",
        )
    }
    plan = build_graph_load_plan(
        articles, [], article_subtopics=bindings
    )
    subtopic_nodes = [n for n in plan.nodes if n.kind is NodeKind.SUBTOPIC]
    subtopic_edges = [e for e in plan.edges if e.kind is EdgeKind.HAS_SUBTOPIC]
    assert len(subtopic_nodes) == 1
    assert subtopic_nodes[0].key == "nomina_electronica"
    assert subtopic_nodes[0].properties["parent_topic"] == "iva"
    assert subtopic_nodes[0].properties["label"] == "Nómina electrónica"
    assert len(subtopic_edges) == 1
    assert subtopic_edges[0].source_key == "1"
    assert subtopic_edges[0].target_key == "nomina_electronica"


def test_article_without_subtopic_emits_no_subtopic_records() -> None:
    plan = build_graph_load_plan([_article("1")], [], article_subtopics={})
    assert [n for n in plan.nodes if n.kind is NodeKind.SUBTOPIC] == []
    assert [e for e in plan.edges if e.kind is EdgeKind.HAS_SUBTOPIC] == []


def test_multiple_articles_sharing_subtopic_dedupe_to_one_node() -> None:
    articles = [_article(str(i)) for i in range(1, 6)]
    bindings = {
        str(i): SubtopicBinding(
            sub_topic_key="parafiscales_icbf",
            parent_topic="laboral",
            label="Parafiscales ICBF",
        )
        for i in range(1, 6)
    }
    plan = build_graph_load_plan(articles, [], article_subtopics=bindings)
    subtopic_nodes = [n for n in plan.nodes if n.kind is NodeKind.SUBTOPIC]
    subtopic_edges = [e for e in plan.edges if e.kind is EdgeKind.HAS_SUBTOPIC]
    assert len(subtopic_nodes) == 1
    assert len(subtopic_edges) == 5


def test_plan_rebuild_is_idempotent() -> None:
    articles = [_article("1")]
    bindings = {
        "1": SubtopicBinding(
            sub_topic_key="retencion_fuente_honorarios",
            parent_topic="retencion",
            label="Retención fuente honorarios",
        )
    }
    first = build_graph_load_plan(articles, [], article_subtopics=bindings)
    second = build_graph_load_plan(articles, [], article_subtopics=bindings)
    first_edge_keys = sorted(
        (e.kind.value, e.source_key, e.target_key) for e in first.edges
    )
    second_edge_keys = sorted(
        (e.kind.value, e.source_key, e.target_key) for e in second.edges
    )
    assert first_edge_keys == second_edge_keys
    assert len([n for n in first.nodes if n.kind is NodeKind.SUBTOPIC]) == 1
    assert len([n for n in second.nodes if n.kind is NodeKind.SUBTOPIC]) == 1
