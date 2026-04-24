# Step 02 — Investigate why mean `primary_article_count` is 1.6 (target 3.0)

**Priority:** P0 · **Estimated effort:** 1 day investigation + fix of the dominant cause · **Blocked by:** step 01 (need `seed_article_keys` populated first)

## §1 What

Phase 6 on 2026-04-24 measured mean `primary_article_count = 1.6` across 30 questions in NEW mode (target: 3.0, hard gate: 2.0). The distribution:

- **15/30 rows** return **0 primary articles** — either planner anchored nothing, or BFS found nothing, or graph is empty for that topic.
- **15/30 rows** return ≥ 1 — their **mean is ~3.2**, close to target.

The headline (1.6 mean) is dominated by the zero-count half. The fix depends on *why* those 15 rows return zero. This step is a read-only investigation that partitions the 30 rows by failure mode, then targets the dominant one.

## §2 Why

1. **Retrieval depth is the upstream input to answer quality.** Thin evidence → thin answers. A classifier that correctly routes but returns 0 primary articles produces a "coverage pending" response — honest, but useless for an accountant who needed a real answer.
2. **Contamination is already solved.** Phase 6 proved this (4/4 zero-hit). The next quality lever is depth, not defense.
3. **We've spent v6 on throughput + correctness. Now we spend on reach.** Rebuilt corpus is in, classifier is in, the gates are in. The gap is "what reaches the synthesizer."

## §3 The four hypotheses for why depth is thin

Each of the 15 zero-primary rows is in exactly one of these buckets. Find the dominant bucket, fix that.

| # | Hypothesis | Signal | Fix shape |
|---|---|---|---|
| **H1** | **Planner anchored no explicit articles.** The planner builds `entry_points` from article refs in the query. If the user didn't mention an article number, entry_points might be empty → no BFS seed → 0 primary. | `seed_article_keys == []` AND `plan.entry_points` (from `plan.to_dict()`) has no `kind=article` entries. | Extend planner to anchor via topic+subtopic when no article ref is present. Likely 2 days. |
| **H2** | **Planner anchored explicit keys but BFS traversal budget killed them.** `entry_points` has article keys but Cypher BFS returns empty because `max_hops` is too tight or the graph doesn't have outbound edges from those seeds. | `seed_article_keys` non-empty AND `primary_article_count == 0`. | Bump `traversal_budget.max_hops`, audit edge coverage from the seed set. Likely 1 day. |
| **H3** | **Graph is genuinely sparse in the domain.** The topic is real but the graph has few ArticleNodes under that topic (e.g., sector_puertos only has 5 articles). | Cypher `MATCH (t:TopicNode {topic_key: $x})<-[:TEMA]-(a:ArticleNode) RETURN count(a)` returns <5 for the failing topics. | Content work — ingest more articles for under-covered topics. Overlaps with step 03. |
| **H4** | **TEMA-first seed list is empty for the routed topic.** Phase 6 showed `tema_first_anchor_count >= 1` in only 15/30 rows — 4 of the 15 zero-primary rows correlate with zero TEMA anchors. The topic has no TEMA edges because the classifier never stamped it, or the classifier stamped it but the Falkor MERGE didn't reach that graph node. | `tema_first_anchor_count == 0` AND topic exists in taxonomy. | Fix TEMA-edge coverage — either re-run classifier with the topic gate, or directly Cypher-write the missing edges. Likely 1 day. |

**Prior belief (highest to lowest likelihood):** H1 ≈ H4 > H2 >> H3. Most procedural tax questions in the gold set don't name an ET article number explicitly — they describe a situation ("un cliente tuvo ingresos X, ¿cómo aplica Y?"), so H1 is the natural suspect.

## §4 Method

### Step A — partition the 30 rows by failure mode

Once step 01 is done and `seed_article_keys` is populated, run this partitioner on the phase-6 output:

```python
# /tmp/partition_depth.py — investigation only, don't commit
import json
rows = [json.loads(l) for l in open("artifacts/eval/ab_comparison_20260424T183902Z_v6_rebuild.jsonl")]

buckets = {"H1_no_seed": [], "H2_seed_but_empty_bfs": [], "H4_no_tema_anchor": [], "ok": []}
for r in rows:
    new = r.get("new", {})
    pac = new.get("primary_article_count", 0) or 0
    seed = new.get("seed_article_keys") or []
    tfa = new.get("tema_first_anchor_count", 0) or 0
    if pac >= 1:
        buckets["ok"].append(r["qid"])
    elif not seed and tfa == 0:
        buckets["H1_no_seed"].append(r["qid"])
    elif seed and pac == 0:
        buckets["H2_seed_but_empty_bfs"].append(r["qid"])
    elif tfa == 0:
        buckets["H4_no_tema_anchor"].append(r["qid"])
    else:
        buckets["other"].append(r["qid"])

for k, v in buckets.items():
    print(f"{k}: {len(v)}  {v}")
```

**The bucket counts dictate the fix.** Whichever bucket has the most rows is the highest-leverage target.

### Step B — for the dominant bucket, pick 3 representative qids and deep-trace

For each qid in the dominant bucket, run the query end-to-end with full diagnostics:

```python
from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.planner import build_graph_retrieval_plan
from lia_graph.pipeline_d.orchestrator import run_pipeline_d

req = PipelineCRequest(message=GOLD_QUERY, topic=GOLD_TOPIC, requested_topic=GOLD_TOPIC)
plan = build_graph_retrieval_plan(req)
print("plan.entry_points:", [e.to_dict() for e in plan.entry_points])
print("plan.traversal_budget:", plan.traversal_budget)

resp = run_pipeline_d(req)
print("primary_article_count:", resp.diagnostics.get("primary_article_count"))
print("seed_article_keys:", resp.diagnostics.get("seed_article_keys"))
# ... etc
```

Compare the plan structure + seed list across the 3 qids. Identify the common failure — that's the fix target.

### Step C — for H3 (sparse graph), direct Cypher audit

```cypher
MATCH (t:TopicNode)
OPTIONAL MATCH (t)<-[:TEMA]-(a:ArticleNode)
RETURN t.topic_key, count(a) AS articles
ORDER BY articles ASC
LIMIT 10
```

Any topic with <5 articles is a content gap. Cross-reference against the gold's failing qids.

### Step D — fix the dominant cause, rerun

Once the dominant bucket's cause is found, fix the narrowest module (planner for H1, retriever_falkor for H2, ingest for H3/H4). Re-run phase 6. Repeat only if another bucket becomes dominant post-fix.

## §5 Success criteria

**Hard gates (all must hit):**

1. Post-fix A/B re-run: mean `primary_article_count` in NEW mode **≥ 3.0**.
2. `primary_article_count >= 1` rate **≥ 20/30** (target), ≥ 15/30 (hard gate — already met but must not regress).
3. Contamination still 4/4 zero-hits on Q11/Q16/Q22/Q27 (non-negotiable).

**Soft gates (lift but don't block):**

4. `tema_first_anchor_count >= 1` rate lifts to ≥ 20/30.
5. No bucket above has > 5 qids in the next run (no single failure mode dominates).

## §6 Out of scope

- Improving the answer synthesizer (quality of wording given evidence). We're only fixing *how much evidence reaches synthesis*.
- Reranker tuning (that's a separate item in `ingestionfix_v6.md §2.4`).
- Ingesting new articles (that's step 03 + §3.1; this step only fixes retrieval over the existing corpus).

## §7 What could go wrong

- **H3 turns out to be the dominant cause.** Then this step bleeds into step 03 (content work). Step 03 scope grows from 2 days to a week. Acceptable — the content was always going to need to be added.
- **Partitioner shows no dominant bucket** (~equal split across H1/H2/H4). Then we have a structural depth problem, not a tuning problem. Escalate to a paired planner/retriever review. Elevated risk of a 2-week detour before step 03 starts.
- **The fix for H1 shifts rows into H3.** Planner suddenly anchors topic/subtopic → BFS runs → graph is sparse → still 0 primary articles. Net zero. That tells us H3 was always the real problem; step 03's scope absorbs it.

## §8 Rollback

Same as step 01 — pure investigation, targeted fix, `git revert` if anything regresses. No cloud writes, no migrations. Safe.
