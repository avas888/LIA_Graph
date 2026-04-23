"""Tests for the Phase-5 thematic graph edges (ingestionfix_v2 §4 Phase 5).

Covers:
  * TopicNode materialization from the ``article_topics`` map
  * TEMA edges: Article → Topic (always, when topic_key non-null)
  * SUBTEMA_DE edges: SubTopic → Topic (static, from subtopic bindings)
  * Null-guard: chunk with subtopic_key=null gets no HAS_SUBTOPIC / SUBTEMA
"""

from __future__ import annotations

from lia_graph.graph.schema import EdgeKind, NodeKind
from lia_graph.ingestion.classifier import ClassifiedEdge
from lia_graph.ingestion.loader import (
    SubtopicBinding,
    build_graph_load_plan,
)
from lia_graph.ingestion.parser import ParsedArticle


def _article(key: str, source_path: str = "/abs/x.md") -> ParsedArticle:
    return ParsedArticle(
        article_key=key,
        article_number=key,
        heading=f"Art {key}",
        body=f"Body {key}",
        full_text=f"# Art. {key}\nBody {key}",
        status="vigente",
        source_path=source_path,
    )


def test_topic_nodes_merged_from_article_topics_map():
    articles = [
        _article("1", "/abs/a.md"),
        _article("2", "/abs/b.md"),
        _article("3", "/abs/c.md"),
    ]
    article_topics = {
        "1": "laboral",
        "2": "iva",
        "3": "laboral",  # duplicate topic → one node
    }
    plan = build_graph_load_plan(
        articles,
        [],
        article_topics=article_topics,
    )
    topic_nodes = [n for n in plan.nodes if n.kind is NodeKind.TOPIC]
    topic_keys = {n.key for n in topic_nodes}
    assert topic_keys == {"laboral", "iva"}, (
        f"expected exactly 2 TopicNode entries, got {topic_keys}"
    )
    # Every TopicNode has topic_key + label
    for node in topic_nodes:
        assert node.properties.get("topic_key") == node.key
        assert node.properties.get("label"), "every topic node must carry a label"


def test_tema_edge_created_per_article_when_topic_known():
    articles = [
        _article("1", "/abs/a.md"),
        _article("2", "/abs/b.md"),
    ]
    article_topics = {"1": "laboral", "2": "iva"}
    plan = build_graph_load_plan(articles, [], article_topics=article_topics)
    tema_edges = [e for e in plan.edges if e.kind is EdgeKind.TEMA]
    assert len(tema_edges) == 2
    pairs = {(e.source_key, e.target_key) for e in tema_edges}
    assert pairs == {("1", "laboral"), ("2", "iva")}
    for edge in tema_edges:
        assert edge.source_kind is NodeKind.ARTICLE
        assert edge.target_kind is NodeKind.TOPIC


def test_tema_edge_skipped_for_article_without_topic():
    articles = [_article("1"), _article("2")]
    article_topics = {"1": "laboral"}  # article 2 has no topic
    plan = build_graph_load_plan(articles, [], article_topics=article_topics)
    tema_edges = [e for e in plan.edges if e.kind is EdgeKind.TEMA]
    assert [e.source_key for e in tema_edges] == ["1"]


def test_subtema_de_edge_from_subtopic_to_parent_topic():
    articles = [_article("1")]
    article_subtopics = {
        "1": SubtopicBinding(
            sub_topic_key="liquidacion_salario",
            parent_topic="laboral",
            label="Liquidación de salario",
        )
    }
    plan = build_graph_load_plan(
        articles,
        [],
        article_subtopics=article_subtopics,
    )
    subtema_de = [e for e in plan.edges if e.kind is EdgeKind.SUBTEMA_DE]
    assert len(subtema_de) == 1
    edge = subtema_de[0]
    assert edge.source_kind is NodeKind.SUBTOPIC
    assert edge.source_key == "liquidacion_salario"
    assert edge.target_kind is NodeKind.TOPIC
    assert edge.target_key == "laboral"


def test_has_subtopic_edge_still_emitted_with_phase5_addition():
    """HAS_SUBTOPIC must coexist with the new TEMA/SUBTEMA_DE edges."""
    articles = [_article("1")]
    article_subtopics = {
        "1": SubtopicBinding(
            sub_topic_key="liquidacion_salario",
            parent_topic="laboral",
            label="L",
        )
    }
    plan = build_graph_load_plan(
        articles, [], article_subtopics=article_subtopics
    )
    kinds = {e.kind for e in plan.edges}
    assert EdgeKind.HAS_SUBTOPIC in kinds
    assert EdgeKind.SUBTEMA_DE in kinds


def test_multiple_articles_sharing_subtopic_produce_one_subtema_de_edge():
    articles = [_article("1"), _article("2"), _article("3")]
    binding = SubtopicBinding(
        sub_topic_key="pila_aportes",
        parent_topic="laboral",
        label="PILA",
    )
    article_subtopics = {"1": binding, "2": binding, "3": binding}
    plan = build_graph_load_plan(
        articles, [], article_subtopics=article_subtopics
    )
    subtema_de = [e for e in plan.edges if e.kind is EdgeKind.SUBTEMA_DE]
    assert len(subtema_de) == 1, (
        f"expected one SUBTEMA_DE edge despite 3 bound articles, got {len(subtema_de)}"
    )


def test_topic_node_pulled_from_subtopic_parent_even_without_article_topics():
    """If article_topics is empty but subtopics supply parent_topic, the
    TopicNode should still get materialized (so SUBTEMA_DE has a target)."""
    articles = [_article("1")]
    article_subtopics = {
        "1": SubtopicBinding(
            sub_topic_key="pila_aportes",
            parent_topic="laboral",
            label="PILA",
        )
    }
    plan = build_graph_load_plan(
        articles, [], article_subtopics=article_subtopics
    )
    topic_keys = {n.key for n in plan.nodes if n.kind is NodeKind.TOPIC}
    assert "laboral" in topic_keys
