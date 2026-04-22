"""Contract guard: Python ``record.key`` must be written under the schema's
``key_field`` for every NodeKind, and a MATCH query must be able to
retrieve the node by that field.

Motivation: during the B3 rerun on 2026-04-21, a repair script queried
``a.article_key`` on ``ArticleNode`` and got 0 matches — because Falkor
stores the key under ``article_id`` (per ``default_graph_schema()``). The
divergence between the Python attribute name (``ParsedArticle.article_key``)
and the Falkor property name (``ArticleNode.article_id``) is a footgun that
this test catches for every NodeKind without needing a live Falkor.
"""
from __future__ import annotations

import re

from lia_graph.graph.client import GraphClient
from lia_graph.graph.schema import (
    EdgeKind,
    GraphEdgeRecord,
    GraphNodeRecord,
    NodeKind,
    default_graph_schema,
)


def test_every_node_kind_has_a_key_field_in_schema() -> None:
    schema = default_graph_schema()
    for kind, node_type in schema.node_types.items():
        assert node_type.key_field, (
            f"NodeKind.{kind.name} is missing key_field in default schema; "
            "every node kind must declare which property stores its identity."
        )


def test_stage_node_merges_on_schema_key_field_for_every_node_kind() -> None:
    """Contract: for every NodeKind, ``GraphClient.stage_node`` emits a
    MERGE that sets the schema-declared ``key_field`` — NOT the Python
    attribute name. Regression guard for the ``article_key`` vs
    ``article_id`` divergence.
    """
    schema = default_graph_schema()
    client = GraphClient(schema=schema)
    for kind, node_type in schema.node_types.items():
        # Satisfy the schema validator by filling required fields with
        # sentinel values — we only care about what the emitted MERGE
        # query looks like.
        properties = {field: "X" for field in node_type.required_fields}
        record = GraphNodeRecord(
            kind=kind,
            key="SENTINEL_KEY",
            properties=properties,
        )
        stmt = client.stage_node(record)
        query = stmt.query
        # The MERGE must reference the schema's key_field, not any
        # alternative name.
        expected_fragment = f"{node_type.key_field}: $key"
        assert expected_fragment in query, (
            f"NodeKind.{kind.name} stage_node should MERGE on "
            f"{node_type.key_field!r}, but query was: {query!r}"
        )
        # And the parameter binding must carry the raw key value.
        assert stmt.parameters.get("key") == "SENTINEL_KEY"


def test_article_node_key_field_is_article_id_specifically() -> None:
    """Narrow regression test for the exact B3 repair-script bug.

    External tooling (repair scripts, one-off queries, diagnostics) must
    query ``a.article_id`` to retrieve an ArticleNode's key. If someone
    renames this field in the schema, they should see this test fail and
    update every downstream consumer — this test is the canary.
    """
    schema = default_graph_schema()
    article_type = schema.node_types[NodeKind.ARTICLE]
    assert article_type.key_field == "article_id", (
        "ArticleNode key_field changed — update all external queries that "
        "use `a.article_id` (including scripts/repair_falkor_subtopic.py)."
    )


def test_stage_edge_references_source_and_target_key_fields() -> None:
    """Contract: stage_edge MATCHes both endpoints via their schema key_fields.

    Same pattern as stage_node — catches any future schema divergence
    between ``GraphNodeRecord.key`` (Python) and the emitted Cypher
    property name.
    """
    schema = default_graph_schema()
    client = GraphClient(schema=schema)
    record = GraphEdgeRecord(
        kind=EdgeKind.HAS_SUBTOPIC,
        source_kind=NodeKind.ARTICLE,
        source_key="ARTICLE_SENTINEL",
        target_kind=NodeKind.SUBTOPIC,
        target_key="SUBTOPIC_SENTINEL",
        properties={},
    )
    stmt = client.stage_edge(record)
    article_kf = schema.node_types[NodeKind.ARTICLE].key_field
    subtopic_kf = schema.node_types[NodeKind.SUBTOPIC].key_field
    assert f"{article_kf}: $source_key" in stmt.query
    assert f"{subtopic_kf}: $target_key" in stmt.query


def test_no_script_or_module_queries_article_key_as_cypher_property() -> None:
    """Lint test: scan repo for ``a.article_key`` or ``article_key:`` in
    Cypher queries. These are almost always bugs — Falkor stores the
    identity as ``article_id``.

    Exceptions: the Python attribute name ``article.article_key`` is fine,
    so we look for ``a.article_key`` specifically (property access on the
    Cypher variable ``a``) or ``article_key: $`` (Cypher MERGE/MATCH
    pattern).
    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    targets = [
        repo_root / "src" / "lia_graph",
        repo_root / "scripts",
    ]
    offenders: list[tuple[Path, int, str]] = []
    cypher_pattern = re.compile(
        r"\b[a-zA-Z_]\.article_key\b|\barticle_key\s*:\s*\$"
    )
    for target in targets:
        if not target.exists():
            continue
        for path in target.rglob("*.py"):
            # Skip this test itself (it contains the forbidden strings
            # inside string literals as examples).
            if path.name == "test_graph_node_key_contract.py":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), start=1):
                # Skip comments + docstrings — Python code using `a.article_key`
                # on a ParsedArticle object is totally fine. We only care
                # about STRING LITERALS that look like Cypher (query,
                # description=, triple-quoted) — those are where bugs live.
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                # Heuristic: the match is inside a string literal (has an
                # unescaped quote before it on the same line).
                m = cypher_pattern.search(line)
                if not m:
                    continue
                prefix = line[: m.start()]
                # Count quotes in the prefix — odd count means we're inside
                # a string literal.
                if (prefix.count('"') - prefix.count('\\"')) % 2 == 1 or (
                    prefix.count("'") - prefix.count("\\'")
                ) % 2 == 1:
                    offenders.append((path, lineno, line.strip()))
    if offenders:
        lines = "\n".join(
            f"  {p}:{ln}: {text}" for p, ln, text in offenders[:10]
        )
        raise AssertionError(
            "Found Cypher references to `article_key` — ArticleNode's key "
            "field in Falkor is `article_id` (see default_graph_schema()). "
            "Update these to `article_id`:\n" + lines
        )
