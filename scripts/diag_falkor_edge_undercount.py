"""Diagnostic — bucket the −5,229 edges Supabase has but Falkor doesn't.

Read-only probe. Per `docs/aa_next/next_v4.md §6.5.B`:

* (a) endpoints not materialized in Falkor → expected loss (loader filter)
* (b) both endpoints exist in Falkor but edge missing → silent drop (problem)

Decision rule: if (b) ≤ 50 → close §6.5.B as "expected loss". If > 50 →
escalate to §6.5.C with its own six gates.
"""

from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict
from typing import Any

# Mapping Supabase normative_edges.relation (lowercase legacy) → Falkor EdgeKind label.
# Sourced by reading `src/lia_graph/graph/schema.py::EdgeKind` and the legacy
# relation values declared in `supabase/migrations/20260417000000_baseline.sql`
# (line 1129). Anything not in the map is bucketed as "unknown_relation".
RELATION_TO_EDGEKIND: dict[str, str] = {
    "references": "REFERENCES",
    "modifies": "MODIFIES",
    "complements": "REFERENCES",  # legacy synonym
    "exception_for": "EXCEPTION_TO",
    "derogates": "DEROGATES",
    "supersedes": "SUPERSEDES",
    "suspends": "SUSPENDS",
    "struck_down_by": "STRUCK_DOWN_BY",
    "revokes": "DEROGATES",  # legacy synonym
    "cross_domain": "REFERENCES",  # legacy synonym
}


def main() -> int:
    from lia_graph.supabase_client import get_supabase_client
    from lia_graph.graph.client import GraphClient, GraphWriteStatement

    sb = get_supabase_client()
    gc = GraphClient.from_env()

    # 1. Find active generation.
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
        print("ERR: no active generation found")
        return 1
    active_gen = str(rows[0]["generation_id"])
    print(f"Active generation: {active_gen}\n")

    # 2. Pull every Supabase normative_edges row for active gen, paginated.
    print("Pulling Supabase normative_edges …")
    sb_edges: list[dict[str, Any]] = []
    page = 0
    while True:
        start = page * 1000
        end = start + 999
        resp = (
            sb.table("normative_edges")
            .select("source_key,target_key,relation,edge_type")
            .eq("generation_id", active_gen)
            .range(start, end)
            .execute()
        )
        batch = list(resp.data or [])
        sb_edges.extend(batch)
        if len(batch) < 1000:
            break
        page += 1
    print(f"  pulled {len(sb_edges):,} Supabase edges\n")

    # 3. Pull every Falkor edge as (source_id, target_id, type) — label-agnostic.
    # FalkorDB server caps RESP responses at 10k rows; paginate with SKIP/LIMIT.
    PAGE = 5000
    print("Pulling Falkor edges (paginated) …")
    fk_triples: set[tuple[str, str, str]] = set()
    fk_pairs: set[tuple[str, str]] = set()
    skip = 0
    while True:
        q = (
            "MATCH (s)-[r]->(t) "
            "RETURN coalesce(s.article_id, s.reform_id, s.concept_id, "
            "       s.parameter_id, s.sub_topic_key, s.topic_key) AS sk, "
            "       coalesce(t.article_id, t.reform_id, t.concept_id, "
            "       t.parameter_id, t.sub_topic_key, t.topic_key) AS tk, "
            f"       type(r) AS rel ORDER BY id(r) SKIP {skip} LIMIT {PAGE}"
        )
        res = gc.execute(
            GraphWriteStatement(description="probe", query=q, parameters={}),
            strict=False,
        )
        rows = list(res.rows or ())
        for row in rows:
            sk = str(row.get("sk") or "")
            tk = str(row.get("tk") or "")
            rel = str(row.get("rel") or "")
            if not sk or not tk:
                continue
            fk_triples.add((sk, tk, rel))
            fk_pairs.add((sk, tk))
        print(f"  page skip={skip:>6} got {len(rows):,}", flush=True)
        if len(rows) < PAGE:
            break
        skip += PAGE
    print(f"  total {len(fk_triples):,} Falkor (sk,tk,rel) triples")
    print(f"  unique (sk,tk) pairs: {len(fk_pairs):,}\n")

    # 4. Pull every Falkor node key — used to detect "endpoint not materialized".
    print("Pulling Falkor node keys (paginated) …")
    fk_node_keys: set[str] = set()
    skip = 0
    while True:
        q = (
            "MATCH (n) "
            "RETURN coalesce(n.article_id, n.reform_id, n.concept_id, "
            "       n.parameter_id, n.sub_topic_key, n.topic_key) AS k "
            f"ORDER BY id(n) SKIP {skip} LIMIT {PAGE}"
        )
        res = gc.execute(
            GraphWriteStatement(description="probe", query=q, parameters={}),
            strict=False,
        )
        rows = list(res.rows or ())
        for row in rows:
            k = str(row.get("k") or "")
            if k:
                fk_node_keys.add(k)
        print(f"  page skip={skip:>6} got {len(rows):,}", flush=True)
        if len(rows) < PAGE:
            break
        skip += PAGE
    print(f"  total {len(fk_node_keys):,} unique node keys\n")

    # 5. Bucket missing edges.
    print("Bucketing missing edges …")
    bucket_a_endpoint_missing = 0  # at least one endpoint not in Falkor
    bucket_b_silent_drop = 0  # both endpoints in Falkor, edge missing
    bucket_c_relation_mismatch = 0  # endpoints + edge exist, but rel differs
    bucket_d_unknown_relation = 0  # Supabase relation not in mapping
    bucket_present = 0  # actually in Falkor (these are NOT missing)

    by_relation_missing: Counter = Counter()
    by_endpoint_missing_kind: Counter = Counter()
    samples_a: list[dict[str, Any]] = []
    samples_b: list[dict[str, Any]] = []
    samples_c: list[dict[str, Any]] = []

    for e in sb_edges:
        sk = str(e.get("source_key") or "")
        tk = str(e.get("target_key") or "")
        rel = str(e.get("relation") or "")
        et = str(e.get("edge_type") or "")
        fk_rel = RELATION_TO_EDGEKIND.get(rel, "")

        if not fk_rel:
            bucket_d_unknown_relation += 1
            continue

        if (sk, tk, fk_rel) in fk_triples:
            bucket_present += 1
            continue

        # Edge not present. Diagnose why.
        s_in = sk in fk_node_keys
        t_in = tk in fk_node_keys

        if not s_in or not t_in:
            bucket_a_endpoint_missing += 1
            kind = (
                "both_missing"
                if (not s_in and not t_in)
                else ("source_missing" if not s_in else "target_missing")
            )
            by_endpoint_missing_kind[kind] += 1
            by_relation_missing[rel] += 1
            if len(samples_a) < 8:
                samples_a.append(
                    {"source_key": sk, "target_key": tk, "relation": rel,
                     "edge_type": et, "kind": kind}
                )
        elif (sk, tk) in fk_pairs:
            # endpoints + edge between them exist, but type differs
            bucket_c_relation_mismatch += 1
            if len(samples_c) < 8:
                # find the actual rel in Falkor
                actual = sorted({r for (a, b, r) in fk_triples
                                 if a == sk and b == tk})
                samples_c.append(
                    {"source_key": sk, "target_key": tk,
                     "supabase_rel": rel, "expected_falkor_rel": fk_rel,
                     "actual_falkor_rels": actual}
                )
        else:
            bucket_b_silent_drop += 1
            by_relation_missing[rel] += 1
            if len(samples_b) < 8:
                samples_b.append(
                    {"source_key": sk, "target_key": tk, "relation": rel,
                     "edge_type": et}
                )

    # 6. Report.
    print("=" * 64)
    print("RESULTS")
    print("=" * 64)
    print(f"Supabase edges (active gen)        : {len(sb_edges):,}")
    print(f"Falkor edges (gen-agnostic)        : {len(fk_triples):,}")
    print(f"  delta (sb − fk)                  : {len(sb_edges) - len(fk_triples):+,}")
    print()
    print("Buckets (each Supabase edge classified):")
    print(f"  present in Falkor                : {bucket_present:,}")
    print(f"  (a) endpoint not materialized    : {bucket_a_endpoint_missing:,}")
    for kind, n in by_endpoint_missing_kind.most_common():
        print(f"        {kind:18s} : {n:,}")
    print(f"  (b) silent drop (both endpoints) : {bucket_b_silent_drop:,}  ← decision metric")
    print(f"  (c) relation type mismatch       : {bucket_c_relation_mismatch:,}")
    print(f"  (d) unknown relation in mapping  : {bucket_d_unknown_relation:,}")
    print()
    print("Missing edges by relation type:")
    for rel, n in by_relation_missing.most_common():
        print(f"  {rel:24s} : {n:,}")
    print()
    print(f"Decision: bucket (b) = {bucket_b_silent_drop} → ", end="")
    if bucket_b_silent_drop <= 50:
        print("≤ 50, CLOSE §6.5.B as expected loss.")
    else:
        print("> 50, ESCALATE to §6.5.C.")
    print()

    if samples_a:
        print("Sample bucket (a) — endpoint not materialized:")
        for s in samples_a:
            print(f"  {s}")
        print()
    if samples_b:
        print("Sample bucket (b) — silent drop:")
        for s in samples_b:
            print(f"  {s}")
        print()
    if samples_c:
        print("Sample bucket (c) — relation mismatch:")
        for s in samples_c:
            print(f"  {s}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
