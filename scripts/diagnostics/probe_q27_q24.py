"""Throwaway Cypher probe for next_v2 §3 (Q27 art. 148 leak) and §4 (Q24 4x1000 regression).

Reads cloud Falkor connection from environment (set by sourcing .env.staging).
Prints raw results so the operator/engineer can decide ingest vs. retriever bug.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, "src")

from lia_graph.graph.client import GraphClient, GraphClientConfig, GraphWriteStatement


def main() -> int:
    url = os.environ.get("FALKORDB_URL", "")
    graph = os.environ.get("FALKORDB_GRAPH", "")
    if not url or not graph:
        print("FALKORDB_URL / FALKORDB_GRAPH unset", file=sys.stderr)
        return 2
    print(f"# probing graph={graph} via cloud falkor")

    cfg = GraphClientConfig.from_env()
    client = GraphClient(config=cfg)

    probes: list[tuple[str, str]] = [
        (
            "Q27 §3 — sagrilaft_ptee TEMA-bound articles (does art. 148 appear?)",
            (
                "MATCH (t:TopicNode {topic_key: 'sagrilaft_ptee'})<-[:TEMA]-(a:ArticleNode) "
                "RETURN a.article_number AS article_number, a.article_key AS article_key, "
                "a.source_path AS source_path, a.doc_key AS doc_key "
                "ORDER BY a.article_number LIMIT 50"
            ),
        ),
        (
            "Q27 §3 supplemental — does an ArticleNode with article_number='148' exist on any topic?",
            (
                "MATCH (a:ArticleNode {article_number: '148'})-[:TEMA]->(t:TopicNode) "
                "RETURN a.article_key AS article_key, a.source_path AS source_path, "
                "a.doc_key AS doc_key, collect(t.topic_key) AS topic_keys LIMIT 20"
            ),
        ),
        (
            "Q24 §4 — gravamen_movimiento_financiero_4x1000 TEMA edge count",
            (
                "MATCH (t:TopicNode {topic_key: 'gravamen_movimiento_financiero_4x1000'})"
                "<-[:TEMA]-(a:ArticleNode) RETURN count(a) AS tema_edge_count"
            ),
        ),
        (
            "Q24 §4 — full TEMA-bound article list for 4x1000",
            (
                "MATCH (t:TopicNode {topic_key: 'gravamen_movimiento_financiero_4x1000'})"
                "<-[:TEMA]-(a:ArticleNode) "
                "RETURN a.article_number AS article_number, a.article_key AS article_key, "
                "a.source_path AS source_path, a.doc_key AS doc_key "
                "ORDER BY a.article_number LIMIT 50"
            ),
        ),
        (
            "context — TopicNode existence for both keys",
            (
                "MATCH (t:TopicNode) WHERE t.topic_key IN ['sagrilaft_ptee', "
                "'gravamen_movimiento_financiero_4x1000'] "
                "RETURN t.topic_key AS topic_key, t.label AS label"
            ),
        ),
    ]

    for desc, cypher in probes:
        print()
        print(f"## {desc}")
        print(f"   query: {cypher}")
        stmt = GraphWriteStatement(description=desc, query=cypher, parameters={})
        result = client.execute(stmt, strict=False)
        if not result.ok:
            print(f"   ERROR: {result.error}")
            print(f"   diagnostics: {json.dumps(dict(result.diagnostics), default=str)}")
            continue
        print(f"   rows ({len(result.rows)}):")
        for row in result.rows:
            print(f"     - {json.dumps(dict(row), default=str)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
