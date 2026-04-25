"""Q11 leak diagnostic — what topics are arts. 514/515/516 TEMA-bound to?

Sibling to probe_q27_q24.py. Q11 is "nota crédito factura electrónica"
(facturacion_electronica topic). The v9 A/B showed NEW seeds=['514','515','516']
which are impuesto-de-timbre articles, not factura-electrónica. This probe
identifies which TopicNode owns those TEMA edges in cloud Falkor — same pattern
as the Q27 art. 148 case, but for Q11 it's the current classifier verdict
(not accumulated stale state), so §K is the only fix.

Throwaway. See next_v2.md §J.4.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, "src")

from lia_graph.graph.client import GraphClient, GraphClientConfig, GraphWriteStatement


def main() -> int:
    if not os.environ.get("FALKORDB_URL"):
        print("FALKORDB_URL unset — source .env.staging first", file=sys.stderr)
        return 2

    cfg = GraphClientConfig.from_env()
    client = GraphClient(config=cfg)

    probes: list[tuple[str, str]] = [
        (
            "Q11 — which TopicNodes is each of arts. 514/515/516 TEMA-bound to?",
            (
                "MATCH (a:ArticleNode)-[:TEMA]->(t:TopicNode) "
                "WHERE a.article_number IN ['514', '515', '516'] "
                "RETURN a.article_number AS article_number, a.source_path AS source_path, "
                "collect(DISTINCT t.topic_key) AS topic_keys "
                "ORDER BY a.article_number"
            ),
        ),
        (
            "Q11 — what other articles is `facturacion_electronica` TEMA-bound to?",
            (
                "MATCH (t:TopicNode {topic_key: 'facturacion_electronica'})<-[:TEMA]-(a:ArticleNode) "
                "RETURN a.article_number AS article_number, a.source_path AS source_path "
                "ORDER BY a.article_number LIMIT 50"
            ),
        ),
        (
            "Q11 — does `impuesto_timbre` (the correct topic for arts. 514–516) exist as a TopicNode?",
            (
                "MATCH (t:TopicNode) WHERE t.topic_key CONTAINS 'timbre' "
                "RETURN t.topic_key AS topic_key, t.label AS label LIMIT 5"
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
            continue
        print(f"   rows ({len(result.rows)}):")
        for row in result.rows:
            print(f"     - {json.dumps(dict(row), default=str)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
