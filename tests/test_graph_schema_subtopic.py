"""Phase 5 schema tests — SubTopic node + HAS_SUBTOPIC edge."""

from __future__ import annotations

import pytest

from lia_graph.graph.schema import (
    EdgeKind,
    GraphEdgeRecord,
    GraphNodeRecord,
    NodeKind,
    default_graph_schema,
)


def test_subtopic_node_kind_exists() -> None:
    assert NodeKind.SUBTOPIC.value == "SubTopicNode"


def test_has_subtopic_edge_kind_exists() -> None:
    assert EdgeKind.HAS_SUBTOPIC.value == "HAS_SUBTOPIC"


def test_default_schema_includes_subtopic_node_and_edge() -> None:
    schema = default_graph_schema()
    assert NodeKind.SUBTOPIC in schema.node_types
    assert EdgeKind.HAS_SUBTOPIC in schema.edge_types
    edge_type = schema.edge_type(EdgeKind.HAS_SUBTOPIC)
    assert NodeKind.ARTICLE in edge_type.source_kinds
    assert NodeKind.SUBTOPIC in edge_type.target_kinds


def test_article_to_subtopic_edge_validates() -> None:
    schema = default_graph_schema()
    record = GraphEdgeRecord(
        kind=EdgeKind.HAS_SUBTOPIC,
        source_kind=NodeKind.ARTICLE,
        source_key="ET_art_107",
        target_kind=NodeKind.SUBTOPIC,
        target_key="nomina_electronica",
    )
    # Should not raise.
    schema.validate_edge_record(record)


def test_subtopic_to_article_edge_rejected() -> None:
    """Reverse direction is not allowed — SubTopic is always a sink."""
    schema = default_graph_schema()
    record = GraphEdgeRecord(
        kind=EdgeKind.HAS_SUBTOPIC,
        source_kind=NodeKind.SUBTOPIC,
        source_key="nomina_electronica",
        target_kind=NodeKind.ARTICLE,
        target_key="ET_art_107",
    )
    with pytest.raises(ValueError, match="HAS_SUBTOPIC cannot start from"):
        schema.validate_edge_record(record)
