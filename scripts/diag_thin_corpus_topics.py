"""Diagnostic — measure how many topics show the "thin-corpus + cross-topic
primary articles" pattern that blocks coherence-gate from passing.

Per `docs/aa_next/next_v5.md §1` (calibration diagnostic) + the operator's
2026-04-26 ask after the FIRMEZA verification round surfaced the pattern.

Read-only against staging cloud. No writes.

Phase 1 (this script): for every registered topic in topic_taxonomy.json,
count (a) Supabase chunks tagged with the topic, (b) Falkor ArticleNodes
whose source-path's owning doc carries that topic. Topics where (a) is
non-trivial but (b) is near-zero are the candidates for the FIRMEZA-class
refusal pattern.

Output:
  * Ranked table to stdout (csv-ish for easy grep).
  * Sample article keys per thin-corpus topic.
  * Verdict: concentration vs distribution → which intervention path.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


# Thresholds for classifying a topic.
# - thin_corpus: native_articles < THIN_NATIVE_ARTICLES AND chunks > THIN_CHUNKS_FLOOR
# - empty: chunks == 0 (won't be reached in retrieval anyway → not interesting)
# - healthy: native_articles >= THIN_NATIVE_ARTICLES OR chunks just-low
THIN_NATIVE_ARTICLES = 5   # < 5 means the topic has almost no canonical articles of its own
THIN_CHUNKS_FLOOR = 10     # but it must have ≥ 10 chunks to be at risk of refusal at all


def _load_registered_topics(
    path: Path = Path("config/topic_taxonomy.json"),
) -> list[str]:
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    keys: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "key" and isinstance(v, str):
                    keys.add(v)
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return sorted(keys)


def main() -> int:
    from lia_graph.supabase_client import get_supabase_client
    from lia_graph.graph.client import GraphClient, GraphWriteStatement

    sb = get_supabase_client()
    gc = GraphClient.from_env()

    # 1. Active generation.
    gen_resp = (
        sb.table("corpus_generations")
        .select("generation_id")
        .eq("is_active", True)
        .order("activated_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = list(gen_resp.data or [])
    if not rows:
        print("ERR: no active generation")
        return 1
    active_gen = str(rows[0]["generation_id"])
    print(f"Active generation: {active_gen}")

    # 2. Registered topics from taxonomy.
    topics = _load_registered_topics()
    print(f"Registered topics in taxonomy: {len(topics)}\n")

    # 3. Per-topic Supabase chunk counts.
    print("Pulling per-topic chunk counts from Supabase …")
    topic_chunk_counts: dict[str, int] = {}
    for t in topics:
        try:
            resp = (
                sb.table("document_chunks")
                .select("chunk_id", count="exact")
                .eq("topic", t)
                .eq("sync_generation", active_gen)
                .range(0, 0)
                .execute()
            )
            topic_chunk_counts[t] = int(getattr(resp, "count", None) or 0)
        except Exception as exc:  # noqa: BLE001
            topic_chunk_counts[t] = -1
            print(f"  {t}: ERR {exc}")
    print(f"  {sum(1 for v in topic_chunk_counts.values() if v > 0):,} topics with ≥1 chunks")
    print(f"  {sum(1 for v in topic_chunk_counts.values() if v == 0):,} topics with 0 chunks")
    print()

    # 4. Per-topic Falkor "native" article count — articles whose source-path
    # belongs to a doc with this topic.
    # Strategy: query Supabase documents to build path→topic map, then walk
    # Falkor ArticleNodes paginated and bucket by their source_path's topic.
    print("Pulling Supabase documents → relative_path/topic map …")
    path_to_topic: dict[str, str] = {}
    page = 0
    while True:
        start = page * 1000
        end = start + 999
        resp = (
            sb.table("documents")
            .select("relative_path, topic")
            .range(start, end)
            .execute()
        )
        batch = list(resp.data or [])
        for r in batch:
            rp = (r.get("relative_path") or "").strip()
            tp = (r.get("topic") or "").strip()
            if rp and tp:
                path_to_topic[rp] = tp
        if len(batch) < 1000:
            break
        page += 1
    print(f"  {len(path_to_topic):,} doc paths with topic assigned\n")

    print("Pulling Falkor ArticleNode source_paths (paginated) …")
    PAGE = 5000
    topic_native_articles: Counter = Counter()
    sample_articles_by_topic: dict[str, list[str]] = defaultdict(list)
    skip = 0
    seen_paths: set[str] = set()
    while True:
        q = (
            "MATCH (a:ArticleNode) "
            "RETURN a.article_id AS aid, a.source_path AS sp "
            f"ORDER BY id(a) SKIP {skip} LIMIT {PAGE}"
        )
        res = gc.execute(
            GraphWriteStatement(description="probe", query=q, parameters={}),
            strict=False,
        )
        rows_ = list(res.rows or ())
        for row in rows_:
            sp = str(row.get("sp") or "")
            aid = str(row.get("aid") or "")
            if not sp or not aid:
                continue
            # Strip leading 'knowledge_base/' if present so it matches
            # `relative_path` form in `documents` (which usually omits it).
            sp_norm = sp.replace("knowledge_base/", "", 1)
            t = path_to_topic.get(sp_norm) or path_to_topic.get(sp)
            if t:
                topic_native_articles[t] += 1
                if len(sample_articles_by_topic[t]) < 3:
                    sample_articles_by_topic[t].append(aid)
        print(f"  page skip={skip:>6} got {len(rows_):,}", flush=True)
        if len(rows_) < PAGE:
            break
        skip += PAGE
    print(f"  {sum(topic_native_articles.values()):,} ArticleNodes mapped to a topic\n")

    # 5. Classify each topic.
    rows_out: list[dict[str, Any]] = []
    for t in topics:
        chunks = topic_chunk_counts.get(t, 0)
        native = topic_native_articles.get(t, 0)
        is_empty = chunks == 0
        is_thin = (
            native < THIN_NATIVE_ARTICLES
            and chunks >= THIN_CHUNKS_FLOOR
        )
        is_healthy = native >= THIN_NATIVE_ARTICLES
        cls = (
            "empty" if is_empty
            else "thin-corpus" if is_thin
            else "low-chunk" if chunks < THIN_CHUNKS_FLOOR
            else "healthy"
        )
        rows_out.append({
            "topic": t,
            "chunks": chunks,
            "native_articles": native,
            "class": cls,
            "samples": list(sample_articles_by_topic.get(t, [])),
        })

    # 6. Report.
    print("=" * 70)
    print("RESULTS — thin-corpus topic inventory")
    print("=" * 70)
    cls_counts: Counter = Counter(r["class"] for r in rows_out)
    print(f"Total topics                : {len(rows_out)}")
    for cls in ("healthy", "thin-corpus", "low-chunk", "empty"):
        print(f"  {cls:12s}              : {cls_counts.get(cls, 0)}")
    print()

    print("== THIN-CORPUS TOPICS (chunks ≥ {}, native_articles < {}) ==".format(
        THIN_CHUNKS_FLOOR, THIN_NATIVE_ARTICLES,
    ))
    thin = [r for r in rows_out if r["class"] == "thin-corpus"]
    thin.sort(key=lambda r: (-r["chunks"], r["topic"]))
    print(f"{'topic':<55s}  {'chunks':>7s}  {'native_arts':>11s}  samples")
    for r in thin:
        samples = ",".join(r["samples"][:3]) or "—"
        print(f"  {r['topic']:<53s}  {r['chunks']:>7,}  {r['native_articles']:>11,}  {samples}")
    print()

    # 7. Decision rule.
    print("=" * 70)
    print("DECISION (Phase-1 only — Phase-2 cross-topic-deps will refine)")
    print("=" * 70)
    n_thin = len(thin)
    if n_thin == 0:
        print("No thin-corpus topics detected at the chosen thresholds.")
        print("FIRMEZA pattern is rare or non-existent → coherence-gate calibration not needed.")
    elif n_thin <= 5:
        print(f"CONCENTRATION ({n_thin} thin-corpus topics) — curation path.")
        print("Recommended: per-topic multi-topic article tagging on the canonical")
        print("articles of these {n_thin} topics. Bounded, surgical work.")
    elif n_thin <= 20:
        print(f"MIXED ({n_thin} thin-corpus topics) — hybrid.")
        print("Curate the top 5-10 by chunk count; defer the long tail to a")
        print("recalibration pass.")
    else:
        print(f"DISTRIBUTION ({n_thin} thin-corpus topics) — recalibration path.")
        print("Curating one-by-one is unbounded. Need either multi-topic ArticleNode")
        print("metadata or coherence-gate recalibration to handle the structural")
        print("cross-topic case.")
    print()
    print(f"Top thin-corpus topics by chunk volume:")
    for r in thin[:10]:
        print(f"  {r['topic']:<53s}  chunks={r['chunks']:,}  native={r['native_articles']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
