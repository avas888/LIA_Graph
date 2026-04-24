"""Tests for v4 loader changes: prose-only ArticleNode eligibility.

Pins the v4 contract:
1. `_is_article_node_eligible` accepts articles with empty article_number
   when heading/text/status are all present.
2. `_graph_article_key` returns a unique-per-doc key for prose-only articles
   (via `whole::{source_path}`) and the bare article_key for numbered ones.
3. `_build_article_nodes` emits `is_prose_only=True` when article_number is empty.
4. `_build_article_tema_edges` uses the graph key so TEMA edges land on the
   correct ArticleNode (not a collapsed-by-key collision).

See docs/next/ingestionfix_v4.md §5 Phase 1.
"""

from __future__ import annotations

from lia_graph.ingestion.loader import (
    _graph_article_key,
    _is_article_node_eligible,
    _is_prose_only,
    _build_article_nodes,
    _build_article_tema_edges,
)
from lia_graph.ingestion.parser import ParsedArticle


def _make_article(
    *,
    article_key: str = "1",
    article_number: str = "1",
    heading: str = "Sample",
    body: str = "body text",
    status: str = "vigente",
    source_path: str | None = "CORE/Ley-100-2026.md",
) -> ParsedArticle:
    return ParsedArticle(
        article_key=article_key,
        article_number=article_number,
        heading=heading,
        body=body,
        full_text=body,
        status=status,
        source_path=source_path,
    )


# ── Eligibility ──────────────────────────────────────────────────────


def test_numbered_article_is_eligible():
    a = _make_article(article_number="5", article_key="5")
    assert _is_article_node_eligible(a) is True


def test_prose_only_article_is_now_eligible():
    """v4: empty article_number is OK as long as heading/text/status exist."""
    a = _make_article(article_number="", article_key="doc")
    assert _is_article_node_eligible(a) is True


def test_missing_heading_still_rejects():
    a = _make_article(heading="")
    assert _is_article_node_eligible(a) is False


def test_missing_text_still_rejects():
    a = _make_article(body="")
    # body falls through to full_text in the check; make it empty too
    a2 = ParsedArticle(
        article_key="1",
        article_number="1",
        heading="H",
        body="",
        full_text="",
        status="vigente",
        source_path="p",
    )
    assert _is_article_node_eligible(a2) is False


def test_missing_status_still_rejects():
    a = _make_article(status="")
    assert _is_article_node_eligible(a) is False


def test_none_article_rejects():
    assert _is_article_node_eligible(None) is False  # type: ignore[arg-type]


# ── Graph key ────────────────────────────────────────────────────────


def test_numbered_article_graph_key_unchanged():
    a = _make_article(article_number="5", article_key="5")
    assert _graph_article_key(a) == "5"


def test_prose_only_article_graph_key_scoped_by_source_path():
    a = _make_article(
        article_number="",
        article_key="doc",
        source_path="CORE/Ley-109-1985.md",
    )
    assert _graph_article_key(a) == "whole::CORE/Ley-109-1985.md"


def test_two_prose_only_articles_get_distinct_graph_keys():
    """Cross-doc collision — the pre-v4 catastrophe this fix prevents."""
    a = _make_article(
        article_number="",
        article_key="doc",
        source_path="CORE/Ley-100-1990.md",
    )
    b = _make_article(
        article_number="",
        article_key="doc",
        source_path="CORE/Ley-300-2020.md",
    )
    assert _graph_article_key(a) != _graph_article_key(b)
    assert _graph_article_key(a).startswith("whole::")
    assert _graph_article_key(b).startswith("whole::")


def test_prose_only_with_missing_source_path_falls_back_to_unknown():
    a = _make_article(article_number="", article_key="doc", source_path=None)
    assert _graph_article_key(a) == "whole::unknown"


# ── is_prose_only property ───────────────────────────────────────────


def test_is_prose_only_true_when_article_number_empty():
    a = _make_article(article_number="")
    assert _is_prose_only(a) is True


def test_is_prose_only_false_when_article_number_present():
    a = _make_article(article_number="5")
    assert _is_prose_only(a) is False


def test_is_prose_only_true_when_whitespace_only():
    a = _make_article(article_number="   ")
    assert _is_prose_only(a) is True


# ── _build_article_nodes ─────────────────────────────────────────────


def test_build_article_nodes_emits_is_prose_only_property():
    prose = _make_article(
        article_number="",
        article_key="doc",
        source_path="CORE/Ley-109.md",
    )
    numbered = _make_article(article_number="5", article_key="5")
    nodes = _build_article_nodes([prose, numbered])
    assert len(nodes) == 2
    by_key = {n.key: n for n in nodes}
    assert "whole::CORE/Ley-109.md" in by_key
    assert "5" in by_key
    assert by_key["whole::CORE/Ley-109.md"].properties["is_prose_only"] is True
    assert by_key["5"].properties["is_prose_only"] is False


def test_build_article_nodes_distinct_keys_for_many_prose_docs():
    articles = [
        _make_article(
            article_number="",
            article_key="doc",
            source_path=f"CORE/Ley-{i}.md",
        )
        for i in range(5)
    ]
    nodes = _build_article_nodes(articles)
    keys = [n.key for n in nodes]
    assert len(set(keys)) == 5  # all distinct


# ── _build_article_tema_edges ────────────────────────────────────────


def test_tema_edge_uses_graph_key_for_prose_only():
    """Given a prose-only article and a topic mapping keyed by graph key,
    the emitted TEMA edge's source_key matches the ArticleNode's MERGE key.
    """
    prose = _make_article(
        article_number="",
        article_key="doc",
        source_path="CORE/Ley-109.md",
    )
    graph_key = _graph_article_key(prose)
    edges = _build_article_tema_edges([prose], {graph_key: "zonas_francas"})
    assert len(edges) == 1
    assert edges[0].source_key == graph_key
    assert edges[0].target_key == "zonas_francas"


def test_tema_edge_skipped_if_topic_keyed_by_wrong_identity():
    """Regression guard: if a caller mistakenly keys article_topics by the
    raw `article.article_key` for a prose-only doc, the edge should NOT land
    (the graph keys would mismatch and the node wouldn't resolve in Cypher).
    """
    prose = _make_article(
        article_number="",
        article_key="doc",
        source_path="CORE/Ley-109.md",
    )
    # Caller bug simulation — keyed by the pre-v4 colliding key
    edges = _build_article_tema_edges([prose], {"doc": "zonas_francas"})
    assert edges == ()


def test_tema_edges_for_mixed_prose_and_numbered():
    prose = _make_article(
        article_number="",
        article_key="doc",
        source_path="CORE/Ley-109.md",
    )
    numbered = _make_article(article_number="5", article_key="5")
    topics = {
        _graph_article_key(prose): "zonas_francas",
        _graph_article_key(numbered): "iva",
    }
    edges = _build_article_tema_edges([prose, numbered], topics)
    targets = {e.target_key for e in edges}
    assert targets == {"zonas_francas", "iva"}
