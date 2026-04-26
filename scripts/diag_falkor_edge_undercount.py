"""Diagnostic — bucket the −5,229 edges Supabase has but Falkor doesn't.

Read-only probe. Per `docs/aa_next/next_v5.md §6.2`:

Bucket (a) "endpoint not materialized in Falkor" splits into:
  * (a1) prose-only key mismatch — source/target is the legacy article_key slug
        but Falkor has the article under `whole::{source_path}`
  * (a2) genuinely orphaned — article was filtered out by loader's schema gate;
        edge correctly dropped
  * (a3) reform-side missing — key looks like `DECRETO-XXX-…` but no `:ReformNode`
        with that key exists in Falkor

Decision rule (Gate 3, v5 §6.2):
  * (a1) ≥ 70% of bucket (a)        → open §6.3 (classifier emits graph_article_key)
  * (a3) ≥ 50% of bucket (a)        → open §6.X (ReformNode hydration)
  * (a2) ≥ 50% AND (a1) < 30%       → close as "expected loss confirmed"
  * No single bucket > 50%          → close as "diffuse cause"
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
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


# Reform-id heuristic for sub-bucket (a3). Matches keys like:
#   DECRETO-624-s_f, LEY-1819-2016, RESOLUCION-000060, CIRCULAR-EXTERNA-100,
#   SENTENCIA-C-481-19, CONCEPTO-100208192-2023, ACUERDO-50.
# Case-insensitive on the prefix; the suffix is permissive.
_REFORM_ID_PATTERN = re.compile(
    r"^(DECRETO|LEY|RESOLUCION|RESOLUCIÓN|CIRCULAR|SENTENCIA|CONCEPTO|ACUERDO|ORDEN|AUTO|OFICIO)[-_]",
    re.IGNORECASE,
)


def _load_parsed_articles_lookup(
    path: Path = Path("artifacts/parsed_articles.jsonl"),
) -> dict[str, tuple[str, str]]:
    """Build `article_key → (article_number, source_path)` from the artifact.

    Returns empty dict if the file is absent (which would degrade the
    sub-bucketing to (a2)/(a3)-only — log a warning and continue).
    """
    out: dict[str, tuple[str, str]] = {}
    if not path.exists():
        print(f"  WARN: {path} not found — (a1) sub-bucket will be empty.")
        return out
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ak = str(row.get("article_key") or "").strip()
            if not ak:
                continue
            num = str(row.get("article_number") or "").strip()
            sp = str(row.get("source_path") or "").strip()
            out[ak] = (num, sp)
    return out


def _looks_like_reform_id(key: str) -> bool:
    return bool(_REFORM_ID_PATTERN.match(key.strip()))


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

    # 4b. Pull Falkor's `whole::*` keys (prose-only ArticleNode form) — used
    # for sub-bucket (a1) detection. Paginated.
    print("Pulling Falkor whole::* keys (paginated) …")
    fk_whole_keys: set[str] = set()
    skip = 0
    while True:
        q = (
            "MATCH (a:ArticleNode) "
            "WHERE a.article_id STARTS WITH 'whole::' "
            f"RETURN a.article_id AS k ORDER BY a.article_id SKIP {skip} LIMIT {PAGE}"
        )
        res = gc.execute(
            GraphWriteStatement(description="probe", query=q, parameters={}),
            strict=False,
        )
        rows = list(res.rows or ())
        for row in rows:
            k = str(row.get("k") or "")
            if k:
                fk_whole_keys.add(k)
        print(f"  page skip={skip:>6} got {len(rows):,}", flush=True)
        if len(rows) < PAGE:
            break
        skip += PAGE
    print(f"  total {len(fk_whole_keys):,} whole::* keys\n")

    # 4c. Pull Falkor's `:ReformNode.reform_id` set — used for sub-bucket (a3).
    # The reform endpoint is missing iff its source_key matches the reform-id
    # pattern AND the key isn't in this set.
    print("Pulling Falkor :ReformNode keys (paginated) …")
    fk_reform_keys: set[str] = set()
    skip = 0
    while True:
        q = (
            "MATCH (r:ReformNode) "
            f"RETURN r.reform_id AS k ORDER BY r.reform_id SKIP {skip} LIMIT {PAGE}"
        )
        res = gc.execute(
            GraphWriteStatement(description="probe", query=q, parameters={}),
            strict=False,
        )
        rows = list(res.rows or ())
        for row in rows:
            k = str(row.get("k") or "")
            if k:
                fk_reform_keys.add(k)
        print(f"  page skip={skip:>6} got {len(rows):,}", flush=True)
        if len(rows) < PAGE:
            break
        skip += PAGE
    print(f"  total {len(fk_reform_keys):,} :ReformNode keys\n")

    # 4d. Load parsed_articles.jsonl lookup for (a1) detection.
    print("Loading artifacts/parsed_articles.jsonl lookup …")
    chunks_lookup = _load_parsed_articles_lookup()
    prose_only_count = sum(
        1 for (num, _) in chunks_lookup.values() if not num.strip()
    )
    print(
        f"  loaded {len(chunks_lookup):,} article_key entries, "
        f"of which {prose_only_count:,} are prose-only\n"
    )

    # 5. Bucket missing edges.
    print("Bucketing missing edges …")
    bucket_a_endpoint_missing = 0  # at least one endpoint not in Falkor
    bucket_b_silent_drop = 0  # both endpoints in Falkor, edge missing
    bucket_c_relation_mismatch = 0  # endpoints + edge exist, but rel differs
    bucket_d_unknown_relation = 0  # Supabase relation not in mapping
    bucket_present = 0  # actually in Falkor (these are NOT missing)

    # v5 §6.2 sub-buckets within bucket (a):
    sub_a1_prose_mismatch = 0
    sub_a2_genuinely_orphaned = 0
    sub_a3_reform_missing = 0

    by_relation_missing: Counter = Counter()
    by_endpoint_missing_kind: Counter = Counter()
    samples_a: list[dict[str, Any]] = []
    samples_a1: list[dict[str, Any]] = []
    samples_a2: list[dict[str, Any]] = []
    samples_a3: list[dict[str, Any]] = []
    samples_b: list[dict[str, Any]] = []
    samples_c: list[dict[str, Any]] = []

    def _classify_missing_key(k: str) -> str:
        """Return 'a1' | 'a2' | 'a3' for a missing endpoint key."""
        # (a1) prose-only key mismatch
        meta = chunks_lookup.get(k)
        if meta is not None:
            num, sp = meta
            if not num.strip() and sp:
                whole_key = f"whole::{sp}"
                if whole_key in fk_whole_keys:
                    return "a1"
        # (a3) reform-side missing
        if _looks_like_reform_id(k) and k not in fk_reform_keys:
            return "a3"
        # (a2) default: genuinely orphaned (article never made it to Falkor
        # under any keying — or non-prose article that was filtered).
        return "a2"

    def _classify_edge_subbucket(
        sk: str, tk: str, s_in: bool, t_in: bool
    ) -> str:
        """Priority: a1 > a3 > a2. Examine each missing endpoint."""
        verdicts: list[str] = []
        if not s_in:
            verdicts.append(_classify_missing_key(sk))
        if not t_in:
            verdicts.append(_classify_missing_key(tk))
        # Priority order
        if "a1" in verdicts:
            return "a1"
        if "a3" in verdicts:
            return "a3"
        return "a2"

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
            # v5 §6.2 sub-bucketing
            sub = _classify_edge_subbucket(sk, tk, s_in, t_in)
            if sub == "a1":
                sub_a1_prose_mismatch += 1
                if len(samples_a1) < 8:
                    meta_s = chunks_lookup.get(sk)
                    meta_t = chunks_lookup.get(tk)
                    samples_a1.append({
                        "source_key": sk, "target_key": tk,
                        "relation": rel, "edge_type": et, "kind": kind,
                        "source_meta": meta_s, "target_meta": meta_t,
                    })
            elif sub == "a3":
                sub_a3_reform_missing += 1
                if len(samples_a3) < 8:
                    samples_a3.append({
                        "source_key": sk, "target_key": tk,
                        "relation": rel, "edge_type": et, "kind": kind,
                    })
            else:
                sub_a2_genuinely_orphaned += 1
                if len(samples_a2) < 8:
                    samples_a2.append({
                        "source_key": sk, "target_key": tk,
                        "relation": rel, "edge_type": et, "kind": kind,
                    })
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
    print(f"  (b) silent drop (both endpoints) : {bucket_b_silent_drop:,}  ← v5 §6.4 watchlist")
    print(f"  (c) relation type mismatch       : {bucket_c_relation_mismatch:,}")
    print(f"  (d) unknown relation in mapping  : {bucket_d_unknown_relation:,}")
    print()

    # v5 §6.2 sub-bucketing of bucket (a)
    a_total = bucket_a_endpoint_missing
    pct = lambda n: (100.0 * n / a_total) if a_total > 0 else 0.0
    print("Bucket (a) sub-buckets (v5 §6.2):")
    print(f"  (a1) prose-only key mismatch     : {sub_a1_prose_mismatch:,}  ({pct(sub_a1_prose_mismatch):.1f}%)")
    print(f"  (a2) genuinely orphaned          : {sub_a2_genuinely_orphaned:,}  ({pct(sub_a2_genuinely_orphaned):.1f}%)")
    print(f"  (a3) reform-side missing         : {sub_a3_reform_missing:,}  ({pct(sub_a3_reform_missing):.1f}%)")
    print(f"  sum                              : {sub_a1_prose_mismatch + sub_a2_genuinely_orphaned + sub_a3_reform_missing:,}  (must = {a_total:,})")
    print()

    print("Missing edges by relation type:")
    for rel, n in by_relation_missing.most_common():
        print(f"  {rel:24s} : {n:,}")
    print()

    # v5 §6.2 Gate 3 decision rule
    print("=" * 64)
    print("DECISION (v5 §6.2 Gate 3)")
    print("=" * 64)
    a1_pct = pct(sub_a1_prose_mismatch)
    a2_pct = pct(sub_a2_genuinely_orphaned)
    a3_pct = pct(sub_a3_reform_missing)
    if a1_pct >= 70.0:
        decision = (
            "(a1) ≥ 70% → OPEN §6.3: classifier emits _graph_article_key() "
            "for prose-only edges. "
            f"Recovery upside ≤ {sub_a1_prose_mismatch:,} edges in Falkor."
        )
    elif a3_pct >= 50.0:
        decision = (
            "(a3) ≥ 50% → OPEN §6.X: ReformNode hydration. "
            f"Reform-side missing edges: {sub_a3_reform_missing:,}."
        )
    elif a2_pct >= 50.0 and a1_pct < 30.0:
        decision = (
            "(a2) ≥ 50% AND (a1) < 30% → CLOSE §6.2 as 'expected loss "
            "confirmed'. Loader filter is doing the right thing."
        )
    elif max(a1_pct, a2_pct, a3_pct) <= 50.0:
        decision = (
            "No single bucket > 50% → CLOSE §6.2 as 'diffuse cause'. "
            "No single intervention recovers most of the loss."
        )
    else:
        decision = (
            "Boundary case (no Gate-3 rule fires cleanly). "
            "Document numbers and decide manually."
        )
    print(decision)
    print()
    print(f"Side-finding: bucket (b) = {bucket_b_silent_drop} (watchlist threshold 100, qualitative-pass per case at 54).")
    print()

    if samples_a1:
        print("Sample sub-bucket (a1) — prose-only key mismatch:")
        for s in samples_a1:
            print(f"  {s}")
        print()
    if samples_a2:
        print("Sample sub-bucket (a2) — genuinely orphaned:")
        for s in samples_a2:
            print(f"  {s}")
        print()
    if samples_a3:
        print("Sample sub-bucket (a3) — reform-side missing:")
        for s in samples_a3:
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
