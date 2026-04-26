"""One-shot — write `secondary_topics` from config onto existing :ArticleNodes
in Falkor without re-ingesting the source documents.

Per `docs/aa_next/next_v5.md §1.A`. The natural way to land secondary_topics
on a node is via re-ingest (loader.py reads the config and SETs the prop on
MERGE). But the curation pass touches ~30+ articles whose canonical owner
docs span the whole ET — touching all those docs would be heavy. This
script reads `config/article_secondary_topics.json` and updates each
ArticleNode directly via Cypher SET, skipping the re-ingest pipeline.

Idempotent. Safe to re-run. Only updates the `secondary_topics` property —
no edges, no other props, no node creation/deletion. Read-write only on
the property the §1.A schema declares.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def main() -> int:
    from lia_graph.graph.client import GraphClient, GraphWriteStatement

    config_path = Path(
        os.environ.get(
            "LIA_ARTICLE_SECONDARY_TOPICS_PATH",
            "config/article_secondary_topics.json",
        )
    )
    if not config_path.exists():
        print(f"ERR: {config_path} not found")
        return 1

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    entries = cfg.get("articles") or []
    if not isinstance(entries, list):
        print("ERR: 'articles' must be a list")
        return 1

    # Filter to entries with non-empty secondary_topics — the others are
    # informational anchors (canonical owner already correct, no override
    # needed for retrieval).
    rows: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        aid = str(entry.get("article_id") or "").strip()
        sec = entry.get("secondary_topics") or []
        if not aid or not isinstance(sec, list):
            continue
        cleaned = [str(t).strip() for t in sec if isinstance(t, str) and str(t).strip()]
        if cleaned:
            rows.append({"article_id": aid, "secondary_topics": cleaned})

    if not rows:
        print("Nothing to sync — every entry has empty secondary_topics.")
        return 0

    print(f"Syncing {len(rows)} entries to Falkor :ArticleNode.secondary_topics …")
    gc = GraphClient.from_env()

    # Single UNWIND batched MERGE-SET. Falkor handles 30-40 rows trivially.
    stmt = GraphWriteStatement(
        description="v5_§1.A_sync_secondary_topics",
        query=(
            "UNWIND $rows AS r "
            "MATCH (a:ArticleNode {article_id: r.article_id}) "
            "SET a.secondary_topics = r.secondary_topics "
            "RETURN r.article_id AS aid, count(a) AS matches"
        ),
        parameters={"rows": rows},
    )
    res = gc.execute(stmt, strict=True)
    rows_out = res.rows or ()

    n_matched = 0
    n_unmatched = 0
    print()
    print(f"{'article_id':<14s}  {'matches':>7s}  {'secondary_topics':<60s}")
    print("-" * 90)
    by_id = {r["article_id"]: r["secondary_topics"] for r in rows}
    for row in rows_out:
        aid = str(row.get("aid") or "")
        m = int(row.get("matches") or 0)
        sec = by_id.get(aid, [])
        flag = "✓" if m > 0 else "—"
        print(f"  {aid:<12s}{flag}  {m:>7d}  {','.join(sec)}")
        if m > 0:
            n_matched += 1
        else:
            n_unmatched += 1
    print()
    print(f"Total matched (article exists in Falkor): {n_matched}/{len(rows)}")
    if n_unmatched:
        print(
            f"Unmatched: {n_unmatched} — those articles haven't been ingested "
            "into Falkor yet (or their article_id collapsed to a different form). "
            "The config still applies to future ingests."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
