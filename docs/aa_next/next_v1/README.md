# Next v1 — what we do after v6, why, and how we know it worked

> **Opened 2026-04-24** after v6's PR #8 merged to main. This folder is the **executable forward plan** — each step has a *what*, a *why* (with cited evidence), and a *success criterion* (measurable, not vibes).
>
> **Relation to other docs.**
> - `docs/next/ingestion_tunningv2.md` — the v6 plan that just shipped (phases 0–6).
> - `docs/next/ingestionfix_v6.md` — the forward **backlog** (30+ ideas ranked). That's the inventory; this folder is the **next-10 execution plan**.
> - `docs/learnings/` — the non-obvious invariants every step below must respect.
>
> **Why the `aa_next/` prefix.** Sorts above `next/` alphabetically — "active-active" reading order. If this folder exists and isn't empty, it's what engineers work on next.

---

## §1 The principle behind the ordering

**Diagnostic plumbing first, then quality lifts.** Phase 6 on 2026-04-24 landed a clean contamination-gate pass (4/4 non-negotiable) but several measurement fields (`seed_article_keys=0/30`, mean `primary_article_count=1.6`) are either wrong or under-recorded. Until we can *measure* retrieval depth honestly, every subsequent quality-lift PR would be flying blind. So: **steps 1–3 close measurement + corpus gaps. Steps 4–10 improve quality on top of that.** Do not parallelize the two groups until step 3 is done.

---

## §2 The ten steps

### Step 01 — [P0 · ~1 hr] Fix the `seed_article_keys=0/30` diagnostic gap

**What.** Phase 1 (commit `7d966ce`) lifted `seed_article_keys` from `evidence.diagnostics` to top-level `response.diagnostics`. Post-phase-6 panel shows 0/30 rows populate this field. Either the retriever path doesn't emit it in `falkor_live` mode, or the harness reads it wrong. Investigate + fix.

**Why.** Without this field we can't tell which articles the planner actually anchored BFS on — blocks every downstream retrieval-depth investigation (step 02). Cited evidence: phase 6 scorecard in `docs/next/ingestionfix_v6.md §1`.

**Success.** Next A/B re-run shows `seed_article_keys` non-empty in ≥ 20/30 rows. Specifically measurable: `len(seed_article_keys) >= 1` for every row with `primary_article_count >= 1`.

**Deep dive:** [`01-seed-article-keys-debug.md`](./01-seed-article-keys-debug.md).

---

### Step 02 — [P0 · ~1 day] Investigate why mean `primary_article_count` is 1.6 (target 3.0)

**What.** Phase 6 showed 15/30 rows have `primary_article_count >= 1` but the mean is 1.6 — meaning the non-zero rows only average ~3.2 articles. The v5-era bet was that TEMA-first retrieval + graph BFS would return 3–5 anchor articles per answer. Read-only investigation of the 15 zero-primary rows + the 15 low-count rows. Fix the dominant cause.

**Why.** Retrieval depth is the upstream input to answer quality. Thin evidence → thin answers. Cited evidence: phase 6 measured 1.6 mean vs plan §1.5 target 3.0. Plan §2.2 in `ingestionfix_v6.md`.

**Success.** Post-fix A/B re-run: mean `primary_article_count` in NEW mode ≥ 3.0 AND `primary_article_count >= 1` rate ≥ 20/30 (target) AND `tema_first_anchor_count >= 1` rate ≥ 20/30.

**Deep dive:** [`02-retrieval-depth-investigation.md`](./02-retrieval-depth-investigation.md).

---

### Step 03 — [P0 · ~2 days] Ingest late-2024 / 2025 reforms

**What.** v1 investigation I4 found 7 gold-referenced articles missing from the corpus. Land them: `LEY_2466_2025`, `LEY_1819_2016`, `CONCEPTO_DIAN_006483_2024`, `DECRETO_2616_2013`, `DECRETO_957_2019`, `DECRETO_1650`, `LEY_2277_2022` (some articles). Add to `knowledge_base/`, run additive delta.

**Why.** Some phase-6 questions return low primary-article counts specifically because the expected anchor doesn't exist in the corpus. No retrieval tuning helps if the answer isn't in the index. Cited evidence: `ingestion_tunningv1.md §0` I4 findings + phase-6 gold-ref match rate.

**Success.** `parsed_articles.jsonl` grows to include all 7 missing refs (verify via `grep -c "LEY_2466_2025\|ET_ART_147\|..." artifacts/parsed_articles.jsonl`). Next A/B re-run's per-row `expected_article_keys` hit rate lifts by ≥ 10 %.

---

### Step 04 — [P1 · 30 min] Flip coherence gate shadow → enforce

**What.** Phase 3 (`60829f0`) added `LIA_EVIDENCE_COHERENCE_GATE`. It's been in shadow mode since ship. Phase 6 shadow-mode telemetry gives us 30 data points on what would-have-refused. If that count is 4–12, flip the launcher default to `enforce`.

**Why.** Shadow → enforce is the point at which the defensive gate actually protects users. Holding it in shadow indefinitely adds code without adding safety. Cited evidence: `ingestion_tunningv2.md §5.6` calibration band.

**Success.** Parse phase 6 jsonl for `topic_safety.coherence.misaligned == True` count. If between 4 and 12, update `scripts/dev-launcher.mjs` to set `LIA_EVIDENCE_COHERENCE_GATE=enforce` for staging + production modes. Next A/B re-run: refusal rate in NEW mode 5–15 %, contamination still 4/4 zero-hits.

**Inline spec (small step, no deep dive).**
```python
# scripts/evaluations/count_would_refuse.py — one-off, don't commit
import json
rows = [json.loads(l) for l in open("artifacts/eval/ab_comparison_20260424T183902Z_v6_rebuild.jsonl")]
count = sum(1 for r in rows
    if ((r.get("new", {}).get("diagnostics", {}).get("topic_safety", {}) or {}).get("coherence") or {})
       .get("misaligned") == True)
print(f"would-refuse: {count}/30")
```
If 4–12: flip the flag in launcher + rerun phase 6. If <4: coherence gate is too permissive, defer. If >12: too aggressive, tune the threshold in `_coherence_gate.py` first.

---

### Step 05 — [P1 · ~2 days] GUI P0 remediation — Makefile `--allow-non-local-env` + events.jsonl progress endpoint

**What.** Two gaps from `docs/next/gui_ingestion_v1.md §13.1 + §13.2`:
1. Makefile conditional to append `--allow-non-local-env` when `PHASE2_SUPABASE_TARGET=production`.
2. Replace `/api/ingest/job/{id}/log/tail` (stdout-tail) with `/api/ingest/job/{id}/progress` (events.jsonl-aggregated JSON). The monitoring-trace spec in `gui_ingestion_v1.md §13b` is the response shape.

**Why.** The current GUI path will fail its first production-Supabase ingest on the env posture guard, or will surface free-text logs containing Spanish legal content that trips operators' error-filter instincts. Cited evidence: 2026-04-24 cloud sink stall taught us the CLI path lesson; GUI still hasn't inherited it. `heartbeat-monitoring.md` failure mode #1.

**Success.** Admin triggers a full-production UI ingest without manually editing env; the progress panel shows phase-labeled counters (classifier/bindings/sink/falkor) instead of free-text log tail; next UI-triggered phase-2-class rebuild reaches end-to-end with exit 0.

**Deep dive:** none needed; spec already in `gui_ingestion_v1.md §13b`. This step is just an execution PR.

---

### Step 06 — [P1 · ~3 days] TPM-aware token-budget limiter

**What.** Add a `TokenBudget` sibling to `TokenBucket` in `ingest_classifier_pool.py`. Estimate input tokens from the prompt + body; debit pre-call; refund on 429. Global budget matches Gemini Flash's 1 M TPM ceiling.

**Why.** Every v6 classifier run (including phase 6) emitted 92–114 TPM-429 tracebacks. Classifier's inner try/except absorbs them as degraded N1-only verdicts (`requires_subtopic_review=True`). Net cost: ~7 % of docs land with degraded classification. Cited evidence: post-phase-6 reported tracebacks + `docs/learnings/ingestion/parallelism-and-rate-limits.md` §"TPM ceiling bit us".

**Success.** Post-fix ingest runs produce **0 Traceback lines** in the classifier phase (vs 92–114 today) AND 0 rows with `requires_subtopic_review=True`. Wall time within 10 % of today's 6m30s (no throughput regression).

**Deep dive:** [`06-tpm-token-budget.md`](./06-tpm-token-budget.md).

---

### Step 07 — [P1 · ~1 hr] Emit `graph.batch_written` events from the sink writer

**What.** Post-phase-2c, the Falkor writer still runs silently (no per-batch events). Add emission from `src/lia_graph/graph/client.py::_execute_live_statement` — payload `{description, stats, elapsed_ms}` — so the heartbeat can tick during `falkor_writing`.

**Why.** `gui_ingestion_v1.md §13b.4` stall thresholds depend on this signal. Without it the Falkor phase is indistinguishable from "silent 3 min" vs "actually stuck". Cited evidence: 2026-04-24 phase-2c monitors couldn't distinguish the two without manual `ps`/`lsof` triads.

**Success.** During the next production sink, `grep -c graph.batch_written logs/events.jsonl` grows steadily during `falkor_writing`; heartbeat `evt_age` stays < 30 s for the whole phase.

**Inline spec.** In `_execute_live_statement`, after the successful decode, emit:
```python
from ..instrumentation import emit_event
emit_event("graph.batch_written", {
    "description": statement.description,
    "stats": dict(stats),
    "elapsed_ms": elapsed_ms,
})
```
Only for statements where `stats` contains `nodes_created`/`relationships_created`/`properties_set` (filters out probes). Gate behind an env var `LIA_GRAPH_EMIT_BATCH_EVENTS=1` defaulting on.

---

### Step 08 — [P1 · ~3 days] Gold-file extension for procedural tax topics

**What.** Phase 5 added 3 new subtopics (`firmeza_declaraciones`, `regimen_sancionatorio_extemporaneidad`, `devoluciones_saldos_a_favor`). Gold still has only the original 30 questions from v5. Commission 10–20 new questions covering the new subtopics + other under-tested procedural areas (beneficio_auditoria, ganancia_ocasional, rentas_exentas).

**Why.** A fixed 30-question gold at a 2.7× expanded corpus gives a weaker signal each cycle. We need fresh adversarial + procedural questions to exercise the phase-5 additions and the corpus content. Cited evidence: `ingestionfix_v6.md §5.1`.

**Success.** `evals/gold_retrieval_v1.jsonl` → `v2` with ≥ 40 questions; all `expected_topic` values match the taxonomy; the CI gate in `eval-c-gold` passes ≥ 90 on v2. Next A/B re-run operates on v2.

---

### Step 09 — [P2 · ~2 days] Persistent verdict cache for idempotent replays

**What.** SQLite-backed cache at `src/lia_graph/ingestion/verdict_cache.py` keyed on `sha256(prompt_template_version + model_id + content_hash)`. Read-before-call, write-after-call. Invalidate via `prompt_template_version` bump.

**Why.** Classifier verdicts today are deterministic within a run but not across runs (LLM response drift, plus TPM-pressure degradation). A cache makes replays bit-identical and cuts re-ingest wall time from ~7 min to seconds when nothing changed. Cited evidence: research note in `parallelism-and-rate-limits.md` + Stripe idempotency pattern.

**Success.** Re-running a full ingest with no code/config change completes in < 60 s (cache-hit on every classifier call) AND produces byte-identical `parsed_articles.jsonl` vs the first run.

---

### Step 10 — [P2 · 15 min] Auto-source `.env.staging` in Makefile target when production

**What.** Add a conditional in `Makefile` that sources `.env.staging` and exports its vars when `PHASE2_SUPABASE_TARGET=production`. Trivial change; blocks no one.

**Why.** Every cloud sink run on 2026-04-24 needed the operator to manually prepend `set -a; source .env.staging; set +a`. Make owns the target; make should own the env load. Cited evidence: `docs/learnings/process/cloud-sink-execution-notes.md`.

**Success.** `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` works in a bare shell with no prefix. Regression test: same command in a subshell with no exported env vars passes the env posture guard.

**Inline spec.**
```make
PHASE2_ENV_LOAD = $(if $(filter production,$(PHASE2_SUPABASE_TARGET)),set -a && source .env.staging && set +a &&,)

phase2-graph-artifacts-supabase:
	$(PHASE2_ENV_LOAD) PYTHONPATH=src:. uv run python -m lia_graph.ingest ... \
	    --allow-non-local-env ...
```

---

## §3 Sequencing (wall-clock estimate)

Assuming one engineer:

| Week | Steps | Output |
|---|---|---|
| 1 | 01 + 02 + 03 | diagnostic gaps closed + late reforms ingested |
| 2 | 04 + 05 + 07 + 10 | coherence gate in enforce + GUI P0 shipped + Falkor events + Makefile clean |
| 3 | 06 | TPM limiter ends degradation; re-run gate in enforce mode confirms |
| 4 | 08 + 09 | gold extended + verdict cache lands |

End of week 4 = v7 plan ready for execution-phase-6 analog (a 40-question A/B against production with all improvements). That becomes `ingestion_tunningv3.md`.

---

## §4 Hard stop conditions

Abort this plan and reassess if any of these hit:

- **Step 01 finds retrieval genuinely isn't populating `seed_article_keys`** — not a harness bug. That would mean retriever refactor is needed; re-scope step 02.
- **Step 02 finds the mean 1.6 is actually a graph-sparsity problem** (not a planner/BFS tuning problem) — that means step 03's scope grows to a bigger content/ingest effort.
- **Step 06 shows even a perfect TPM limiter can't prevent degradation on the corpus** — means Gemini Flash is the wrong tier; pivot to Gemini Pro or a different provider for classifier calls.
- **Contamination gate regresses** — any v7 PR that reintroduces forbidden-token hits on Q11/Q16/Q22/Q27 blocks the merge. Non-negotiable stays non-negotiable.

---

## §5 What success looks like at the end of next_v1

**Hard gates.** All of these must be green before closing next_v1:
1. ✅ Contamination still 4/4 zero-hits on Q11/Q16/Q22/Q27 (non-negotiable, regression guard).
2. ✅ `seed_article_keys` non-empty ≥ 20/30 rows.
3. ✅ Mean `primary_article_count` ≥ 3.0 in NEW mode.
4. ✅ Classifier pass emits 0 Tracebacks (TPM limiter working).
5. ✅ UI-triggered production ingest completes without manual env prefix.

**Soft gates.** Lift but not block:
- Refusal rate in enforce mode 5–15 %.
- Gold v2 with ≥ 40 questions passing `eval-c-gold` at ≥ 90.
- `falkor_writing` phase visibly ticks in the heartbeat.
- Replay runs in < 60 s (cache hit).

---

## §6 Deep-dive files in this folder

- [`01-seed-article-keys-debug.md`](./01-seed-article-keys-debug.md) — investigation method, hypotheses to test, fix sketches.
- [`02-retrieval-depth-investigation.md`](./02-retrieval-depth-investigation.md) — how to partition the 30 questions by failure mode, what to measure per bucket, how to pick the highest-leverage fix.
- [`06-tpm-token-budget.md`](./06-tpm-token-budget.md) — `TokenBudget` design, token-estimation heuristic, interaction with existing `TokenBucket`, test strategy.

Everything else is inline above. Small steps (04, 07, 10) don't earn their own file.

---

*Opened 2026-04-24 after v6 shipped (PR #8, commit `6e5e842`). Owner: TBD on assignment. Status: pre-execution — review this file for priority changes before a single line of code is written.*
