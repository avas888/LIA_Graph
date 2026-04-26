"""Phase-2 of the §1 calibration diagnostic — cross-topic dependency.

Per `docs/aa_next/next_v5.md §1`. Phase 1 (`diag_thin_corpus_topics.py`)
identified 12 thin-corpus topics — non-trivial chunk count, near-zero native
ArticleNodes. Phase 2 measures, for each thin-corpus topic, **which articles
its chunks reference and what topic each referenced article belongs to**.

Goal: tell concentrated vs distributed apart.

* **Concentrated** — most thin-corpus topics need just 1-3 specific articles
  to be re-tagged (e.g., beneficio_auditoria needs Art. 689-3 ET tagged).
  Surgical multi-topic curation fix.

* **Distributed** — each thin-corpus topic needs many articles re-tagged,
  spread across the ET. Curation becomes unbounded; recalibration of the
  coherence-gate or multi-topic-tagging schema is the right fix.

Read-only against Supabase + Falkor. No writes.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from typing import Any


# Same thin-corpus topics from Phase-1 (chunks ≥ 10, native_articles < 5).
# Hardcoded here to avoid re-running Phase-1 every time. If Phase-1 changes,
# re-run and update this list.
THIN_CORPUS_TOPICS = (
    "precios_de_transferencia",
    "impuesto_patrimonio_personas_naturales",
    "regimen_cambiario",
    "perdidas_fiscales_art147",
    "beneficio_auditoria",
    "normas_internacionales_auditoria",
    "conciliacion_fiscal",
    "impuestos_saludables",
    "sector_telecomunicaciones",
    "dividendos_y_distribucion_utilidades",
    "parafiscales_seguridad_social",
    "sector_economia",
)

# Lightweight "Art. N" extractor — same regex family as `linker.py`.
ARTICLE_REF_RE = re.compile(
    r"(?i)\b(?:art(?:[ií]culo)?|art\.)\s*(?P<n>\d+(?:-\d+)?)\b"
)


def main() -> int:
    from lia_graph.supabase_client import get_supabase_client
    from lia_graph.graph.client import GraphClient, GraphWriteStatement

    sb = get_supabase_client()
    gc = GraphClient.from_env()

    # Active gen.
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
        return 1
    active_gen = str(rows[0]["generation_id"])

    # Build path → topic lookup (for what topic owns each article).
    print("Loading documents.relative_path → topic …")
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
    print(f"  {len(path_to_topic):,} doc paths\n")

    # For each ArticleNode, capture (article_id, source_path, owner_topic).
    print("Pulling Falkor ArticleNode → topic map …")
    PAGE = 5000
    article_owner_topic: dict[str, str] = {}
    skip = 0
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
            aid = str(row.get("aid") or "")
            sp = str(row.get("sp") or "")
            if not aid or not sp:
                continue
            sp_norm = sp.replace("knowledge_base/", "", 1)
            t = path_to_topic.get(sp_norm) or path_to_topic.get(sp)
            if t:
                article_owner_topic[aid] = t
        if len(rows_) < PAGE:
            break
        skip += PAGE
    print(f"  {len(article_owner_topic):,} articles owner-topic-mapped\n")

    # For each thin-corpus topic, pull its chunks (chunk_text), extract
    # article references, classify each ref by its owner topic.
    print("=" * 70)
    print("Per-topic cross-topic dependency analysis")
    print("=" * 70)

    rows_out: list[dict[str, Any]] = []
    for topic in THIN_CORPUS_TOPICS:
        print(f"\n--- {topic} ---")
        # Pull chunk texts (limited sample — 100 max, paginated).
        chunks_text: list[str] = []
        page = 0
        while True:
            start = page * 50
            end = start + 49
            resp = (
                sb.table("document_chunks")
                .select("chunk_text")
                .eq("topic", topic)
                .eq("sync_generation", active_gen)
                .range(start, end)
                .execute()
            )
            batch = list(resp.data or [])
            for r in batch:
                ct = str(r.get("chunk_text") or "")
                if ct:
                    chunks_text.append(ct)
            if len(batch) < 50 or len(chunks_text) >= 100:
                break
            page += 1
        print(f"  pulled {len(chunks_text)} chunks")

        # Extract Art. N references, count occurrences, classify by owner topic.
        ref_counter: Counter = Counter()
        for txt in chunks_text:
            for m in ARTICLE_REF_RE.finditer(txt):
                ref_counter[m.group("n").strip()] += 1

        # Top 12 most-referenced articles in this topic's chunks.
        top_refs = ref_counter.most_common(12)
        if not top_refs:
            print("  no Art. N refs found in chunks")
            continue

        # For each top-ref, find its owner topic in Falkor.
        cross_topic_count: Counter = Counter()
        same_topic_count = 0
        unknown_count = 0
        per_ref_rows: list[dict[str, Any]] = []
        for art_id, n_mentions in top_refs:
            owner = article_owner_topic.get(art_id, "?unknown?")
            same = (owner == topic)
            if owner == "?unknown?":
                unknown_count += n_mentions
            elif same:
                same_topic_count += n_mentions
            else:
                cross_topic_count[owner] += n_mentions
            per_ref_rows.append({
                "art_id": art_id,
                "mentions": n_mentions,
                "owner_topic": owner,
                "same_topic": same,
            })

        # Aggregate counts.
        total_mentions = sum(n for _, n in top_refs)
        same_pct = (100 * same_topic_count / total_mentions) if total_mentions else 0
        cross_pct = (100 * sum(cross_topic_count.values()) / total_mentions) if total_mentions else 0
        unknown_pct = (100 * unknown_count / total_mentions) if total_mentions else 0

        rows_out.append({
            "topic": topic,
            "chunks_sampled": len(chunks_text),
            "distinct_refs": len(ref_counter),
            "total_mentions": total_mentions,
            "same_topic_pct": round(same_pct, 1),
            "cross_topic_pct": round(cross_pct, 1),
            "unknown_pct": round(unknown_pct, 1),
            "top_cross_owners": dict(cross_topic_count.most_common(5)),
            "per_ref_top": per_ref_rows[:8],
        })

        print(f"  distinct refs: {len(ref_counter)}, total mentions (top-12): {total_mentions}")
        print(f"  → same-topic: {same_pct:.1f}%, cross-topic: {cross_pct:.1f}%, unknown: {unknown_pct:.1f}%")
        print(f"  top cross-topic owners:")
        for owner, n in cross_topic_count.most_common(5):
            print(f"    • {owner}: {n} mentions")
        print(f"  top referenced articles:")
        for r in per_ref_rows[:5]:
            marker = "✓ same" if r["same_topic"] else (
                f"→ {r['owner_topic']}" if r["owner_topic"] != "?unknown?" else "? unknown"
            )
            print(f"    • Art. {r['art_id']:<8s}  {r['mentions']:>3} mentions  [{marker}]")

    # Aggregate verdict.
    print("\n" + "=" * 70)
    print("AGGREGATE — concentration vs distribution")
    print("=" * 70)
    n_high_cross = sum(1 for r in rows_out if r["cross_topic_pct"] >= 60)
    n_low_cross = sum(1 for r in rows_out if r["cross_topic_pct"] < 30)
    print(f"Topics with cross-topic ≥ 60%        : {n_high_cross} / {len(rows_out)}")
    print(f"Topics with cross-topic < 30%        : {n_low_cross} / {len(rows_out)}")

    # Look at how concentrated the cross-topic owners are.
    all_cross_owners: Counter = Counter()
    for r in rows_out:
        for owner, n in r["top_cross_owners"].items():
            all_cross_owners[owner] += n
    print(f"\nCross-topic owners across the 12 thin-corpus topics:")
    for owner, n in all_cross_owners.most_common(10):
        print(f"  {owner:<50s}  {n} mentions")
    n_distinct_owners = len(all_cross_owners)
    print(f"\nTotal distinct cross-topic owners: {n_distinct_owners}")

    print("\nDECISION:")
    if n_distinct_owners <= 5:
        print("→ CONCENTRATED. The thin-corpus topics overwhelmingly depend on a")
        print("  small set of canonical owners (≤ 5). Curation path is bounded:")
        print("  multi-topic-tag a limited list of high-traffic articles.")
    elif n_distinct_owners <= 15:
        print("→ MIXED. Curation buys most of the win on the top 5-10 owners;")
        print("  long-tail thin-corpus topics need recalibration.")
    else:
        print("→ DISTRIBUTED. Cross-topic deps spread across many owners.")
        print("  Curation is unbounded. Need multi-topic ArticleNode metadata")
        print("  or coherence-gate recalibration to fix structurally.")

    # Write JSON for programmatic consumption.
    out_path = "artifacts/diag_thin_corpus_xref.json"
    with open(out_path, "w") as fp:
        json.dump({"rows": rows_out, "all_cross_owners": dict(all_cross_owners)}, fp, indent=2)
    print(f"\nFull report saved to: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
