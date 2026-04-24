# Quality-of-results evaluation — designing an eval you can trust

**Source:** v5 30Q A/B expert panel (2026-04-22); `docs/next/ingestion_tunningv1.md` investigations I3, I5, I6; `docs/next/ingestion_tunningv2.md` §8 phase 6 design.

> **Why this doc exists.** The v5 panel's failure mode was **catastrophic and uninterpretable** — 60 result blocks all reporting `primary_article_count: 0`, `tema_first_mode: None`, three rubric categories that didn't match the actual system behavior. The week we spent rebuilding that eval taught us more about how to DESIGN an eval than about how to fix retrieval. This doc distills those rules.

## The six failure modes a RAG eval can exhibit

A RAG eval can fail in two fundamentally different ways — **the system is wrong**, or **the eval is wrong**. The v5 panel had all six of these happening simultaneously; we had to unwind them in order.

| # | Failure mode | Where it lives | v5 example |
|---|---|---|---|
| 1 | **Harness reads the wrong field** | eval harness | `primary_article_count` read from top-level `response.diagnostics` when the field lived nested |
| 2 | **Gold file keys don't match production taxonomy** | data | Q19 expected `obligaciones_mercantiles`, real taxonomy key is `comercial_societario` |
| 3 | **Expected-article refs are wrong/stale** | data | Q10 expected Res. DIAN 165/2023; that resolution exists in corpus but under different key |
| 4 | **Corpus missing the domain entirely** | upstream ingestion | EXPERTOS/PRACTICA not ingested → no hope of the answer being right regardless of retrieval |
| 5 | **Classifier misroute** | system | Q1 routed to `facturacion_electronica` at conf 1.00 instead of `declaracion_renta` |
| 6 | **Retrieval contamination** | system | Q16 labor → biofuel chunk from Ley 939/2004 |

Only #5 and #6 are "the system is wrong." The other four are eval bugs. **Diagnose all six before shipping any code change.**

## The rubric for a trustworthy eval

### 1. The eval measures what you think it measures

**Verify harness field-reads before trusting the output.** For every metric the eval reports:

```python
# one-liner diagnostic
from lia_graph.pipeline_d.orchestrator import run_pipeline_d
resp = run_pipeline_d(request)
print(resp.diagnostics)  # show the whole thing; don't trust selective reads
```

Compare the dict to what the harness reports for the same query. If they differ, fix the harness before anything else. This is phase 1 of `ingestion_tunningv2.md` — it took 30 min of coding and saved weeks of misinterpretation.

### 2. Gold file keys are strictly a subset of the live taxonomy

Add a CI gate:

```python
tax_keys = {t["key"] for t in load_json("config/topic_taxonomy.json")["topics"]}
for row in load_jsonl("evals/gold_retrieval_v1.jsonl"):
    assert row.get("expected_topic") in tax_keys or row.get("expected_topic") is None
```

If the taxonomy changes, re-run and patch the gold in the same PR. See [`citation-allowlist-and-gold-alignment.md`](citation-allowlist-and-gold-alignment.md) for details.

### 3. Expected-article refs are provable against the corpus

Before trusting `expected_article_keys`, confirm each key exists:

```python
keys_in_corpus = {
    json.loads(line)["article_key"]
    for line in open("artifacts/parsed_articles.jsonl")
}
for row in gold:
    missing = [k for k in row["expected_article_keys"] if k not in keys_in_corpus]
    if missing:
        print(f"{row['qid']}: missing from corpus: {missing}")
```

Missing keys = either the gold is stale (data bug) or the corpus lacks the document (ingestion gap). Both are diagnosed BEFORE running retrieval.

### 4. The eval's diagnostic signature tells you what broke without re-running

A useful eval row carries a **machine diagnostic** alongside the panel verdict:

```jsonl
{
  "qid": "Q16",
  "query": "...",
  "expected_topic": "laboral",
  "expected_article_keys": ["CST_Art_45", ...],

  "observed_topic": "laboral",
  "observed_confidence": 1.00,
  "primary_article_count": 0,           ← phase 1 lifted this
  "tema_first_mode": "on",              ← phase 1 lifted this
  "seed_article_keys": [...],           ← phase 1 lifted this
  "dropped_by_allowlist": [...],        ← phase 4 added this
  "coherence_refusal_reason": null,     ← phase 3 added this
  "answer_markdown": "..."
}
```

When a case fails, the diagnostic tells you which failure mode fired:
- Classifier wrong → `observed_topic != expected_topic`
- Retrieval empty → `primary_article_count == 0` AND coherence gate shows `no_evidence`
- Contamination → `primary_article_count > 0` AND dropped_by_allowlist non-empty
- Corpus gap → expected keys not in `seed_article_keys`

**Rule:** if you can't tell which failure mode fired from the diagnostic alone, the diagnostic is incomplete. Fix the diagnostic before re-running the panel.

### 5. The panel's rubric is stable across runs

Lia's v5 panel used three categories (`new_better`, `prior_better`, `tie`, `both_wrong`). When we re-run in phase 6, we compare against the same categories with the same definitions. A rubric that evolves between runs can't show trends.

Write the rubric once, lock it, version it. `evals/100qs_rubric.yaml` is the canonical shape in this repo.

### 6. You can simulate the refusal rate before enforcing

Before flipping a gate from `shadow` to `enforce`, run the eval in shadow mode and count what would-have-refused:

```python
shadow_rows = run_eval_in_shadow_mode()
would_refuse = sum(1 for r in shadow_rows
                   if r["diagnostics"]["coherence"]["misaligned"])
print(f"Refusal rate at enforce: {would_refuse}/{len(shadow_rows)} = {would_refuse/len(shadow_rows):.0%}")
```

Acceptable range: **5–15%** for a well-calibrated coherence gate. Below 5% = gate doesn't fire on real contamination (false negatives). Above 25% = gate starves normal traffic (false positives). Investigation I6 established this calibration band empirically against the v5 production-like corpus.

## The minimum diagnostic surface every eval row should carry

After the v6 phase-1 diagnostic lift, each row in `artifacts/eval/ab_comparison_*.jsonl` carries:

| Field | Lifted by | What it tells you |
|---|---|---|
| `retrieval_backend` / `graph_backend` | existed pre-v5 | which retriever actually served the row |
| `primary_article_count` | phase 1 | did the graph return anchors? |
| `connected_article_count` | phase 1 | did BFS surface siblings? |
| `seed_article_keys` | phase 1 | which articles were considered |
| `tema_first_mode` / `tema_first_anchor_count` | phase 1 | did TEMA-first steer retrieval? |
| `planner_query_mode` | phase 1 | which query shape did the planner build? |
| `retrieval_sub_topic_intent` | phase 1 | did subtopic intent fire? |
| `subtopic_anchor_keys` | phase 1 | which subtopic anchors were used |
| `topic_safety.misalignment` | existed pre-v5 | did the primary misalignment detector fire? |
| `topic_safety.coherence` | phase 3 | did the coherence gate flag? |
| `dropped_by_allowlist` | phase 4 | what citations were filtered as leakage? |

That's the **minimum** surface. New features add fields; none are removed.

## Anti-patterns — things a bad eval does

- **Scoring only the final answer markdown.** Answer quality depends on retrieval, synthesis, and policy. Without a diagnostic surface, you can't tell which layer broke.
- **Expert panel grades semantic quality; harness grades field presence.** Don't collapse them. The panel's "new better / prior better" verdict is qualitative; the harness's `primary_article_count > 0` is quantitative. Report both.
- **Running the eval once, trusting the result.** One eval run is one data point. Run twice, compare. If they differ beyond noise, temperature+randomness are leaking into the eval (classifier LLM non-determinism, timeouts, rate limits).
- **Evaluating on the same corpus you trained on.** Not applicable to v6 (no training), but applicable to any future reranker / classifier tuning work. Keep a held-out eval set.
- **No negative examples.** The v5 panel had 30 questions that should succeed. Future evals must include questions that should **refuse** — to verify the coherence gate and citation allow-list don't over-block.

## The "am I done?" checklist for phase 6 (v6 validation)

From `docs/next/ingestion_tunningv2.md` §8.5 — the v6 plan's definition of victory:

- `primary_article_count != None` in ≥ 25/30 NEW-mode rows ✅ phase 1 delivers this unconditionally
- `tema_first_mode == "on"` in 30/30 NEW-mode rows ✅ environment set correctly
- Mean `primary_article_count` in NEW mode ≥ 3.0 — **data-dependent**, measured post-rebuild
- All 4 contamination cases (Q11, Q16, Q22, Q27) **refused OR cleanly answered OR allow-list-filtered** — non-negotiable
- Q4/Q7/Q9 (pre-existing bail cases) preserve protective behavior — non-negotiable
- `len(answer) > 400` in ≥ 18/30 rows — rough "substantial answer" proxy
- ≥ 1 citation in ≥ 22/30 answers

A failure on any non-negotiable stops phase 7 and surfaces to operator. Everything else is a gradient.

## Reading order when re-designing an eval

1. Read the existing eval harness end-to-end. Identify which fields it reads from which nesting level. Fix any mismatches.
2. Read the gold file. Validate every `expected_topic` against the live taxonomy. Validate every `expected_article_key` against the live corpus.
3. Read the rubric. Freeze it. Version it.
4. Read the diagnostic surface. If it can't distinguish the six failure modes above, extend it.
5. Only now run the eval. Report harness metrics + panel verdict + diagnostic signature together.

## See also

- `docs/next/ingestion_tunningv1.md` §0 I3/I5/I6 — investigation of v5 eval failures.
- `docs/next/ingestion_tunningv2.md` §8 (phase 6) and §1.5 (cumulative success criteria).
- [`diagnostic-surface.md`](diagnostic-surface.md) — phase 1 lifting in detail.
- [`coherence-gate-and-contamination.md`](coherence-gate-and-contamination.md) — phase 3 gate, rubric calibration.
- [`citation-allowlist-and-gold-alignment.md`](citation-allowlist-and-gold-alignment.md) — phase 4+5 alignment work.
