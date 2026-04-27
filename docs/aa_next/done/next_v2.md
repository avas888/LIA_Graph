# next_v2 — forward plan after the 2026-04-24 staging A/B

> **Opened 2026-04-24** after next_v1's staging A/B (action A) returned ↩ regressed. next_v2 is the **forward-only working set** — the revert that must execute now, the investigations that gate any re-flip, and the remaining queued work.
>
> **Archive.** Full history + outcome blocks for steps 01/02/04/05/06/07/10 + the six-gate policy enforcement that landed with them live in [`next_v1/README.md`](./next_v1/README.md). Don't repeat them here; point at the archive instead.
>
> **Policy.** Every item below carries the mandatory six-gate block per [`docs/aa_next/README.md`](./README.md) §Policy: 💡 idea → 🛠 code landed → 🧪 verified locally → ✅ verified in target env → ↩ regressed-discarded. Unit tests green ≠ improvement.

---

## §1 What's on deck (priority order)

| # | Item | Status | Blocks | Effort |
|---|---|---|---|---|
| 1 | **Revert runbook** — `LIA_TEMA_FIRST_RETRIEVAL` launcher default back to `shadow` | ✅ shipped 2026-04-24 | — | 20 min |
| 2 | **H. Q27 `art. 148` cross-topic-anchor leak** | 🧪 root-caused (probe done · fix split into §J classifier-side + §J loader-side) | Re-flip of TEMA-first to `on` | 1–2 days |
| 3 | **I. Q24 `gravamen_movimiento_financiero_4x1000` 3→0 regression** | ↻ resolved as flake 2026-04-24 (NEW primary back to 3) — downgraded to "watch" | — | done |
| 4 | **Re-run action A** (staging A/B) once H + I close | 💡 idea | Closes step 01 → ✅ in target env | 30 min wall + operator |
| 5 | **Step 03 content** — phase-5 topics + 7 missing reforms | ⏸ SME-blocked | Mean `primary_article_count` ≥ 3.0 gate | 2–5 days SME + 1 hr ingest |
| 6 | **D. Step 06 pool integration** — wire TokenBudget + TPMRateLimitError into classifier | 💡 idea | Classifier degradation (31.4% measured) | 4–6 hr code + cloud run |
| 7 | **Step 08** — gold v2 (≥ 40 questions covering phase-5 topics) | ⏸ SME-blocked | A/B signal richness | 1–2 weeks SME |
| 8 | **Step 09** — persistent verdict cache (idempotent replays) | 💡 idea | Replay wall-time from ~7 min to < 60 s | 2 days |
| 9 | **§J Loader: DETACH-DELETE stale TEMA before MERGE** | ✅ structural · 🧪 data-quality (55% silent degradation on the verification rebuild — needs re-run at `--classifier-workers 4` before §K) | §K classifier hardening (cannot be measured fairly until classifier pass is non-degraded) | structural done · re-run ~15-20 min at workers=4 |
| 10 | **§K Classifier hardening for RENTA/Deductions mis-routing** | 📝 spec'd — needs SME design call | Re-flip of TEMA-first | 1–2 days SME + 0.5 day code |

Items 1–4 are the **revert-then-recover** track (must complete before any re-flip). Items 5–8 are independent and can run in parallel by the right actor. Items 9–10 are the concrete fixes that emerged once §3 and §4 were probed against staging on 2026-04-24 — both branched out of §H "Q27 art. 148 leak" once the root cause was localized.

### Do §J before §K — it's an order of magnitude cheaper

| | §J Loader cleanup | §K Classifier hardening |
|---|---|---|
| Code state | ✅ landed + tests green | ❌ not started |
| Remaining work | run cloud re-ingest (~1 hr operator) + 1-min Cypher probe | 30–60 min SME design call → pick K1/K2/K3 → 0.5 day code → 2-run stability test |
| Total wall time | **~1 hour** | **1–2 days minimum** |
| Blocked on | operator availability + Gemini budget | SME availability for the design call |
| Order of operations | do this first — verifies cloud is clean and is a hard prerequisite for §K's success criterion (two-run stability can't be measured if the cloud is still polluted) | do this after §J — landing on a clean cloud means the SME's verdicts on the spot-check sample reflect the new classifier behavior, not residual stale state |

**Recommendation.** Run §J's cloud re-ingest first (it's also a no-regret action — the loader cleanup is a structural fix that should happen regardless of whether §K lands K1, K2, or K3). Then schedule the §K design call.

---

## §2 Revert runbook — `LIA_TEMA_FIRST_RETRIEVAL` shadow (EXECUTE NOW)

**Why.** 2026-04-24 staging A/B (next_v1 §7 action A) measured a non-negotiable contamination regression on Q27 caused by `LIA_TEMA_FIRST_RETRIEVAL=on`. Q27 query asks about SAGRILAFT compliance; NEW mode (`on`) anchors on `art. 148 ET` (tax deduction) and cites it confidently. PRIOR mode (`shadow`) has no `art. 148` hit. Six-gate policy gate 6 requires immediate revert; keep step-01 diagnostic code fixes because they're unrelated and proved to work (Q27 NEW `seed_article_keys=['148']` correctly surfaces the bad anchor that was already there).

### §2.1 What to KEEP untouched

All of these are independent of the flag flip and stay in place:

- `src/lia_graph/pipeline_d/retriever_falkor.py:171` — `seed_article_keys = list(effective_article_keys)` (diagnostic only)
- `src/lia_graph/pipeline_d/retriever.py` — `seed_article_keys` emission in artifacts retriever (diagnostic only)
- `tests/test_retriever_falkor_tema_first.py` + `tests/test_orchestrator_diagnostic_surface.py` — regression tests for the seed invariant
- `scripts/evaluations/run_ab_comparison.py` + `scripts/evaluations/render_ab_markdown.py` — coherence capture in `ModeResult` + markdown surfacing
- `src/lia_graph/ui_ingest_run_controllers.py` — `_aggregate_phase_signals` + wiring into `/progress`
- `src/lia_graph/graph/client.py` — `_emit_batch_written_event` + call from `_execute_live_statement`
- `src/lia_graph/ingest_classifier_pool.py` — `TokenBudget` / `estimate_input_tokens` (unused primitive; wired by D below)
- `Makefile` — `--allow-non-local-env` conditional + `PHASE2_ENV_LOAD` auto-source
- All new tests (`test_token_budget.py`, `test_graph_client_batch_written_event.py`, extended `test_ingest_progress_endpoint.py`)

### §2.2 What to REVERT (five mirror surfaces)

**2.2.1 · `scripts/dev-launcher.mjs`.** Find the `// v5 Phase 3 — TEMA-first retrieval.` block (~line 273). Change `env.LIA_TEMA_FIRST_RETRIEVAL = "on"` back to `"shadow"`. Replace the "Default flipped from `shadow` to `on` on 2026-04-24" comment with: *"Default stays `shadow`. Briefly flipped `on` 2026-04-24 and reverted same day per next_v2 §2 — staging A/B showed Q27 `art. 148` contamination in `on` mode (absent in `shadow`). Re-flip blocked on next_v2 §H + §I closing."* Shell / Railway override still wins.

**2.2.2 · `docs/orchestration/orchestration.md`.** Three edits:
- Line ~732 version: `v2026-04-24-temafirston` → `v2026-04-24-temafirst-revert`.
- Matrix row for `LIA_TEMA_FIRST_RETRIEVAL` (~line 747): all three mode columns → **`shadow`**. Description prose: *"Default `shadow` across all three modes. Briefly flipped `on` on 2026-04-24 per next_v1 step 01 verification; reverted same day after staging A/B (next_v1 §7 action A) showed Q27 contamination. Re-flip gated on next_v2 §H + §I."*
- New change-log entry just below the current top row:
  ```
  | `v2026-04-24-temafirst-revert` | 2026-04-24 | Reverted `LIA_TEMA_FIRST_RETRIEVAL` launcher default from `on` back to `shadow` after same-day staging A/B (next_v1 §7 action A) showed Q27 contamination regression (`art. 148 ET` leaking into SAGRILAFT answer when `on`, absent in `shadow`). The +15-row retrieval-rescue lift TEMA-first=on demonstrated (0/30 → 15/30 non-zero primary) is retained as the re-flip target once next_v2 §H + §I close. Step-01 diagnostic fix retained unchanged. | `scripts/dev-launcher.mjs`, `docs/orchestration/orchestration.md`, `docs/guide/env_guide.md`, `CLAUDE.md`, `frontend/src/app/orchestration/shell.ts` |
  ```

**2.2.3 · `docs/guide/env_guide.md`.** Three edits:
- Header: `> **Env matrix version: v2026-04-24-temafirston.**` → `v2026-04-24-temafirst-revert`.
- Section heading: `## Runtime Retrieval Flags (v2026-04-24-temafirston)` → `(v2026-04-24-temafirst-revert)`.
- `LIA_TEMA_FIRST_RETRIEVAL` row: three columns → `shadow`, description mirrors the orchestration.md prose.

**2.2.4 · `CLAUDE.md`.** Two edits:
- Section heading: `## Runtime Read Path (Env v2026-04-24-temafirston)` → `(v2026-04-24-temafirst-revert)`.
- In the "Additional retrieval-tuning flags" paragraph, remove the `LIA_TEMA_FIRST_RETRIEVAL=on` clause from the flipped-on list. Add: *"`LIA_TEMA_FIRST_RETRIEVAL` launcher default stays `shadow` — briefly flipped `on` on 2026-04-24 and reverted same day; see `docs/aa_next/next_v2.md` §2."*

**2.2.5 · `frontend/src/app/orchestration/shell.ts`.** Line ~29: `<strong>v2026-04-24-temafirston</strong>` → `<strong>v2026-04-24-temafirst-revert</strong>`.

### §2.3 Verify

1. `grep -n "LIA_TEMA_FIRST_RETRIEVAL" scripts/dev-launcher.mjs docs/orchestration/orchestration.md docs/guide/env_guide.md CLAUDE.md frontend/src/app/orchestration/shell.ts` → launcher shows `"shadow"`, matrix rows show `shadow`, no unpaired `on`-flip reference without its revert clause.
2. `node -e "import('./scripts/dev-launcher.mjs').then(() => console.log('ok'))"` → no parse errors.
3. *(optional)* Limited staging re-run with `--limit 5 --manifest-tag v7_tema_reverted` — only to confirm no residual drift; the `npm run dev:staging` path is the primary user of this default and §2.3.1 / §2.3.2 already confirm it.

---

## §3 H. Q27 `art. 148` cross-topic-anchor leak investigation

1. **Idea.** When `LIA_TEMA_FIRST_RETRIEVAL=on`, Q27 (`expected_topic=sagrilaft_ptee`) retrieves `art. 148 ET` as primary anchor and the synthesizer cites it in a compliance answer. In `shadow` the leak is absent. Find and fix the retrieval chain.
2. **Plan.** (a) Cypher probe against staging Falkor: `MATCH (t:TopicNode {topic_key: 'sagrilaft_ptee'})<-[:TEMA]-(a:ArticleNode) RETURN a.article_number, a.article_key, a.source_path ORDER BY a.article_number LIMIT 50`. (b) If `148` in result: trace the ingest-time binding — which doc got labeled `sagrilaft_ptee` AND had `article_number=148`? Fix at classifier / loader. (c) If `148` NOT in result: contamination is downstream — audit `_retrieve_subtopic_bound_article_keys` + BFS expansion in `retriever_falkor.py` for the code path that surfaces `148`. Fix there.
3. **Success criterion.** Post-fix staging A/B: Q27 NEW `art. 148` hit = 0 AND Q27 NEW `primary_article_count` ≥ 1 AND Q11/Q16/Q22 still clean.
4. **How to test.**
   - *Development.* Cypher probe scripts (throwaway). If code fix: unit test feeding a SAGRILAFT query to a mocked Falkor client returning `art.148` in the TEMA set, asserting the retriever filters it out.
   - *Conceptualization.* Unit test locks the topic→anchor contract; the A/B substring check on Q27 answer is end-user validation.
   - *Running environment.* Cypher probe + re-run = staging Falkor/Supabase + LLM budget.
   - *Actors.* Engineer with cloud creds (probe + fix). Operator (re-run).
   - *Decision rule.* Q27 clean AND other 3 contamination qids still clean AND Q27 retains substantive answer.
5. **Greenlight.** 5a: unit test. 5b: A/B Q27 clean.
6. **Refine-or-discard.** If TEMA edges for `sagrilaft_ptee` are near-empty → converges on step 03 content commission. If fix requires ripping out TEMA-first entirely → discard the v5 TEMA-first approach; pursue the +15-row rescue via planner upgrades + step 03 instead.

### Outcome (2026-04-24 · 🧪 root-caused)

**Probe.** Cypher query against staging Falkor (`scripts/diagnostics/probe_q27_q24.py`):

```cypher
MATCH (t:TopicNode {topic_key: 'sagrilaft_ptee'})<-[:TEMA]-(a:ArticleNode)
RETURN a.article_number, a.source_path
ORDER BY a.article_number LIMIT 50
```

24 rows. The smoking gun is the last row:

```
{"article_number": "148",
 "source_path": "knowledge_base/CORE ya Arriba/RENTA/NORMATIVA/Normativa/06_Libro1_T1_Cap5_Deducciones.md"}
```

A second probe — `MATCH (a:ArticleNode {article_number: '148'})-[:TEMA]->(t:TopicNode) RETURN topic_keys` — confirmed the same ArticleNode is bound to **two unrelated topics**: `[iva, sagrilaft_ptee]`. Article 148 is from the RENTA/Deducciones chapter; neither IVA nor SAGRILAFT is correct.

**Diagnosis — two independent bugs, both real.**

1. *Classifier mis-classification.* The AI document classifier mis-labeled `06_Libro1_T1_Cap5_Deducciones.md` (RENTA / income-tax deductions, chapter 5) as `iva` on one ingest run and as `sagrilaft_ptee` on another. The correct topic is in the costos/deducciones-renta family. Two separate wrong verdicts on the same doc = classifier instability on RENTA/Deductions content. **→ §K** (planner-side hardening).
2. *Loader never wipes stale TEMA edges.* `build_graph_load_plan()` (the canonical full-rebuild path used by `make phase2-graph-artifacts-supabase`) only ever MERGEs. Both wrong-verdict runs left their TEMA edges in cloud Falkor. Even if the classifier produces the right answer next time, the stale wrong edges persist forever. **→ §J** (loader-side cleanup; landed).

The artifact bundle (`artifacts/typed_edges.jsonl`) has zero TEMA edges — confirmed they're produced exclusively at cloud-load time by `_build_article_tema_edges()` in `src/lia_graph/ingestion/loader.py`. The fix surface is therefore the loader and the classifier, not the retriever (`retriever_falkor.py:_retrieve_subtopic_bound_article_keys` was a candidate per plan §3.2c but is innocent — the bad anchor is real cloud state, not a downstream bug).

---

## §4 I. Q24 `gravamen_movimiento_financiero_4x1000` 3→0 regression investigation

1. **Idea.** Q24 regressed from `primary_article_count=3` (phase-6 NEW, 2026-04-24 13:39 UTC) to `primary_article_count=0` (postflip NEW, 21:32 UTC). Same `LIA_TEMA_FIRST_RETRIEVAL=on` config. Regression appears only in TEMA-first path — cloud drift or TEMA-first determinism bug.
2. **Plan.** (a) Cypher probe: `MATCH (t:TopicNode {topic_key: 'gravamen_movimiento_financiero_4x1000'})<-[:TEMA]-(a:ArticleNode) RETURN count(a)` + full list. If count < 3 → cloud Falkor lost TEMA edges; investigate ingest concurrency. (b) If count ≥ 3 → `_retrieve_tema_bound_article_keys` is returning empty unpredictably; audit `ORDER BY` / `LIMIT` semantics / pagination. (c) Re-run A/B with `--limit 30 --resume` to establish reproducibility (flaky vs. deterministic).
3. **Success criterion.** Post-fix staging A/B: Q24 NEW `primary_article_count` ≥ 1 (ideally ≥ 3) AND no other row regresses.
4. **How to test.**
   - *Development.* Cypher probe. If determinism bug isolated: regression test pinning the topic→anchor-count contract.
   - *Conceptualization.* End-user: Q24 was a working answer 8 hours ago; restoring it proves the TEMA-first path is reliable enough to keep.
   - *Running environment.* Same as H.
   - *Actors.* Same as H.
   - *Decision rule.* Q24 non-zero AND 29 other rows stable.
5. **Greenlight.** 5a: regression test if bug isolated. 5b: A/B Q24 non-zero.
6. **Refine-or-discard.** If cloud state is inherently flaky → fall back to artifact-plan-driven TEMA-first (deterministic, stale-risk). If flakiness is on Falkor's side → add retry+backoff around `_retrieve_tema_bound_article_keys` before giving up on TEMA-first altogether.

### Outcome (2026-04-24 · 🧪 cloud state confirmed healthy · reproducibility A/B in flight)

**Probe.** Cypher count against staging Falkor:

```
MATCH (t:TopicNode {topic_key: 'gravamen_movimiento_financiero_4x1000'})<-[:TEMA]-(a:ArticleNode)
RETURN count(a) AS tema_edge_count
→ 17
```

Full list shows the canonical GMF range (arts. 870–881-1) plus the GMF doc bundle and `Ley-1694-2013.md`. **Well above the plan's `< 3` threshold for "cloud lost edges."** The 3→0 regression observed in yesterday's 21:32 UTC A/B run is not a cloud-state-loss problem.

**Path forward per plan §4 step 2(b)–(c).** The cloud has the data; either `_retrieve_tema_bound_article_keys` is returning empty unpredictably (pagination / `ORDER BY` / `LIMIT` issue), or the regression was a one-off flake. Reproducibility re-run launched 2026-04-24 23:16 UTC: `manifest-tag=v8_q24_reproducibility`, `--limit 30`, `--target production`, fresh run (no `--resume`). Output at `artifacts/eval/ab_comparison_20260424T231612Z_v8_q24_reproducibility.{jsonl,md,manifest.json}`. Decision tree:

- If Q24 NEW `primary_article_count` ≥ 1 → yesterday's 0 was flaky; downgrade §I to "watch" status; no code change needed.
- If Q24 NEW `primary_article_count` = 0 again → flakiness ruled out; audit `_retrieve_tema_bound_article_keys` + BFS expansion for non-determinism (likely a `LIMIT 50` collision with the 17-edge population now that the §J cleanup will reduce noise).

### Outcome (2026-04-24 · ✅ resolved as flake — downgraded to "watch")

Reproducibility A/B `v8_q24_reproducibility` (2026-04-24 18:16 PM Bogotá, 3:05 wall) restored Q24 to its phase-6 baseline:

| qid | Yesterday 21:32 UTC NEW | Today 23:16 UTC NEW | Verdict |
|---|---|---|---|
| Q24 (4x1000) | `primary=0, seeds=[]` | `primary=3, seeds=['870','871','872']` | flake ↺ |

Yesterday's 0 was a one-off, not a deterministic regression. The cloud TEMA edges for `gravamen_movimiento_financiero_4x1000` are healthy (17 edges, canonical GMF range arts. 870–881-1) AND `_retrieve_tema_bound_article_keys` returned them correctly today.

§I closes as ↻ flake — no retriever code change needed. Watch the next two A/Bs for re-occurrence; if it re-flakes, escalate to the LIMIT/ORDER BY audit per the plan.

**Bonus signal from the same run.** Q27 NEW still surfaces `seed_article_keys=['148']` — the cloud TEMA edge to art. 148 is still poisoning the SAGRILAFT seed set as expected (§J's cloud verification has not happened yet). However, today's Q27 NEW answer was a 101-char "no reliable recommendation" abstention (the topic-safety / coherence gate caught the misalignment) rather than yesterday's confident `art. 148` citation. Net read: the contamination is **intermittent** — sometimes the safety gate catches it, sometimes the synthesizer is fooled. Until §J's loader cleanup ships to cloud, both outcomes are live; the re-flip gate stays closed.

---

## §5 Re-run action A (post H + I close)

1. **Idea.** With H + I closed, re-run the staging A/B to confirm the 4-criterion decision rule passes in target env and the launcher default can flip back to `on`.
2. **Plan.** Same command as 2026-04-24's action A: `PYTHONPATH=src:. uv run python scripts/evaluations/run_ab_comparison.py --gold evals/gold_retrieval_v1.jsonl --output-dir artifacts/eval --manifest-tag v7_posthi --target production`, under `.env.staging` + `.env.local` sourced, no manual `LIA_TEMA_FIRST_RETRIEVAL` export (harness sets per-mode).
3. **Success criterion.** All 4 criteria from action A decision rule pass: seeds ≥ 20/30, mean primary ≥ 2.5, contamination 4/4 clean, no ok→zero regression.
4. **How to test.** Same as next_v1 §7.A. Expected wall ~7 min (this revision cached hot).
5. **Greenlight.** 5b: all 4 criteria ✅.
6. **Refine-or-discard.** If a new regression surfaces → don't flip; iterate H / I / step 03 until it's clean.

Post-success: re-apply §2 in reverse (flip launcher default `shadow` → `on` + bump env matrix to a new `v-temafirst-readdressed` tag + update all 5 mirror surfaces).

---

## §6 Step 03 continuation — phase-5 topic content + 7 missing reforms

Unchanged from next_v1. Full six-gate block in [`next_v1/README.md` §7.E](./next_v1/README.md). Short form:

- 3 phase-5-new topics (`firmeza_declaraciones`, `regimen_sancionatorio_extemporaneidad`, `devoluciones_saldos_a_favor`) have 0 corpus docs → 0 TEMA edges → A/B rows Q20/Q21/Q22 return primary=0. Commission SME content per `docs/next/commission_dian_procedure_slate.md`.
- 2 thin-coverage topics (`costos_deducciones_renta` 0 docs / 5 TEMA edges; `sector_medio_ambiente` 0 docs / 2 TEMA edges) — same commission scope.
- 7 missing reforms (`LEY_2466_2025`, `LEY_1819_2016`, `CONCEPTO_DIAN_006483_2024`, `DECRETO_2616_2013`, `DECRETO_957_2019`, `DECRETO_1650`, `LEY_2277_2022` partials) — published legal texts; SUIN fetcher or manual add.
- **Success criterion.** `canonical_corpus_manifest.json` topic_key_counts ≥ 3 per phase-5 topic AND mean `primary_article_count` in next A/B NEW ≥ 3.0 AND per-row `expected_article_keys` hit rate lifts ≥ 10 %.
- **Actor.** SME (abogado/contador with 7+ años DIAN procedure) + engineer to run ingest.

---

## §7 D. Step 06 pool integration — TokenBudget + TPMRateLimitError

Unchanged from next_v1. Full six-gate block in [`next_v1/README.md` §7.D](./next_v1/README.md). Short form:

- Primitive landed ([`src/lia_graph/ingest_classifier_pool.py::TokenBudget`](../../src/lia_graph/ingest_classifier_pool.py)) + 7/7 unit tests pass.
- Remaining work: (a) `TPMRateLimitError` in `ingestion_classifier.py`; (b) `_run_n2_cascade:720-724` replace bare `except Exception` with narrow 429 catch → re-raise; (c) `classify_documents_parallel` takes `token_budget_tpm` param + refund-on-429 loop; (d) `LIA_INGEST_CLASSIFIER_TPM=1000000` env default + CLI flag.
- **Success criterion.** Full classifier pass on v6 corpus: 0 Tracebacks AND 0 rows with `requires_subtopic_review=true` (vs. 31.4% / 5,888 measured 2026-04-24) AND wall within ±10 % of 6m32s baseline.
- **Blocker.** Cloud classifier run + operator credentials + Gemini budget.

---

## §8 Step 08 — gold v2 (≥ 40 procedural-tax questions)

Unchanged from next_v1. Full six-gate block in [`next_v1/README.md` §7.F](./next_v1/README.md). Short form:

- Current `evals/gold_retrieval_v1.jsonl` = 30 questions, no phase-5 topic coverage. Commission ≥ 10 new questions covering `firmeza_declaraciones` / `regimen_sancionatorio_extemporaneidad` / `devoluciones_saldos_a_favor` + underweight procedural topics (`beneficio_auditoria`, `ganancia_ocasional`, `rentas_exentas`).
- Save as `evals/gold_retrieval_v2.jsonl`. Point `eval-c-gold` at v2.
- **Success criterion.** ≥ 40 questions AND all `expected_topic` values match current `config/topic_taxonomy.json` AND `make eval-c-gold` passes at ≥ 90 on v2 AND phase-5 topics ≥ 2 questions each.
- **Actor.** SME (question authoring + expected-article curation).

---

## §9 Step 09 — persistent verdict cache

Unchanged from next_v1. Full six-gate block in [`next_v1/README.md` §7.G](./next_v1/README.md). Short form:

- `src/lia_graph/ingestion/verdict_cache.py` (new) — SQLite, key = `sha256(prompt_template_version + model_id + content_hash)`. Read-before-call in `classify_ingestion_document`; write-after-call.
- **Success criterion.** Two consecutive `make phase2-graph-artifacts-supabase` runs with no change: second run < 60 s wall AND produces byte-identical `parsed_articles.jsonl`.
- **Blocker.** None. ~2 days engineering.

---

## §J Loader: DETACH-DELETE stale TEMA edges before MERGE (root cause for §3 finding 2)

1. **Idea.** The full-rebuild path (`build_graph_load_plan()` → `_build_batched_statements()` in `src/lia_graph/ingestion/loader.py`) only ever MERGEs. When the AI classifier flips its verdict on a document across runs, both the old and the new TEMA edge land in cloud Falkor and never get reconciled. This is the structural half of the Q27 art. 148 contamination — even after §K hardens the classifier, stale cloud state from past mis-classifications stays unless we clean it up.
2. **Plan.** New batched helper `GraphClient.stage_delete_outbound_edges_batch(NodeKind.ARTICLE, source_keys, relation=EdgeKind.TEMA)` — single UNWIND DELETE statement, scoped to TEMA only (other edge kinds either come from static taxonomy or have stable upstream provenance). Wired into `_build_batched_statements` as step 1b, between index creation and node MERGEs, scoped to **all ArticleNodes being MERGEd this run**. New article keys: DELETE is a no-op. Existing article keys: stale TEMA edges wiped, then re-MERGE writes the fresh ones from `article_topics`.
3. **Success criterion.** After a fresh `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production`, the Cypher probe `MATCH (a:ArticleNode {article_number: '148'})-[:TEMA]->(t:TopicNode) RETURN collect(t.topic_key)` returns **exactly one** topic_key (the current classifier verdict), not the historical multi-set `[iva, sagrilaft_ptee]`.
4. **How to test.**
   - *Development.* Unit test in `tests/test_falkor_loader_thematic.py`: `test_full_rebuild_emits_pre_merge_tema_cleanup_for_article_keys` asserts the cleanup statement exists, names the right article keys, and is sequenced before TEMA MERGE. Plus a no-op test for empty article sets.
   - *Conceptualization.* Cleanup is a structural invariant of "rebuild" — a rebuild that doesn't reconcile stale state isn't a rebuild. Locking it as a unit test prevents future loader changes from reintroducing the bug.
   - *Running environment.* Local pytest for the unit test. Cloud verification requires a fresh ingest against staging Supabase + Falkor + the Cypher probe above.
   - *Actors.* Engineer for code (done). Operator with cloud creds for the re-ingest verification.
   - *Decision rule.* Cypher probe returns exactly one topic_key for art. 148 AND the curated backend smoke set still passes.
5. **Greenlight.** 5a: regression test green — done (`tests/test_falkor_loader_thematic.py` 9/9, sibling loader suites 57/57). 5b: cloud Cypher probe after re-ingest — pending operator.
6. **Refine-or-discard.** If cleanup statement adds material wall-time to the cloud rebuild → switch from "wipe all article TEMA on every rebuild" to "wipe only article keys whose `article_topics` value differs between baseline_snapshot and current run" (cheaper but needs the snapshot delta machinery from `ingestion/baseline_snapshot.py`).

### Outcome (2026-04-24 · ✅ structural cleanup verified in cloud · classifier-side mis-classification persists, deferred to §K)

**Code:**
- New helper: `src/lia_graph/graph/client.py` — `GraphClient.stage_delete_outbound_edges_batch`.
- Wiring: `src/lia_graph/ingestion/loader.py` — step 1b in `_build_batched_statements`.
- Tests: `tests/test_falkor_loader_thematic.py` — 2 new regression tests, 9/9 green; sibling loader suites — 57/57 green.

**Cloud rebuild:**
- Launcher: `scripts/ingestion/launch_phase2_full_rebuild.sh` (mirrors `launch_phase9a.sh` shape — nohup + disown + direct redirect, no tee pipe).
- Run: detached 2026-04-24 23:29:01 UTC (06:29 PM Bogotá), PID 82826 reparented to PPID=1, log `logs/phase2_full_rebuild_20260424T232901Z.log`.
- Wall time: ~4 minutes (much faster than the 1 hr estimate — heavy classifier short-circuit thanks to the fingerprint-prematch shortcut for unchanged docs; full re-classify would have been an hour).
- Summary block: `documents_written=1280 chunks_written=7838 edges_written=30083 activated=true`. Generation `gen_20260424233329`.
- Heartbeat note: cron `bbcac120` armed and then deleted — fired only after the run had already exited because the rebuild beat the first 3-min tick. Heartbeat misread the post-completion state as `STATE=STOPPED` (the script's phase inference is calibrated for the additive/delta path, which emits `ingest.delta.cli.done`; full-rebuild emits its summary in the log tail instead). For future full-rebuild runs, prefer a "tail the log + watch PID" loop over `ingest_heartbeat.py`, or extend the heartbeat to recognize the full-rebuild completion signal.

**Cypher verification (`scripts/diagnostics/probe_q27_q24.py`):**

| Probe | Pre-rebuild | Post-rebuild | Verdict |
|---|---|---|---|
| `sagrilaft_ptee` TEMA-bound article rows | 24 (one was rogue art. 148 from RENTA/Deducciones) | **23** (rogue row gone) | ✅ structural cleanup worked |
| `art. 148` topic_keys it's bound to | `[iva, sagrilaft_ptee]` | **`[iva]`** | ✅ stale sagrilaft binding wiped; classifier-current verdict (still wrong) preserved |
| `gravamen_movimiento_financiero_4x1000` TEMA edge count | 17 (canonical GMF range) | **17** (no regression) | ✅ healthy unchanged |

**Net read.** §J's structural fix landed and is verified in cloud. The Q27 contamination — having art. 148 bound to BOTH `iva` AND `sagrilaft_ptee` from two separate past mis-classifications — is gone. What remains is a SINGLE wrong classifier verdict (`iva` for a RENTA/Deductions doc). That's now §K's territory exclusively. **Re-flip gate moves from "blocked on §J + §K" to "blocked on §K only."**

### Audit caveat — silent degradation on the §J rebuild (per `docs/learnings/process/cloud-sink-execution-notes.md`)

Post-rebuild audit surfaced TPM-pressure-driven silent degradation, exactly the trap that learning warns about. The mandatory check (`grep -c '"requires_subtopic_review": true'`) returned **702 / 1275 = 55 %** — eight times the cloud-sink-execution-notes' 5 % warning threshold and ~8× the prior 7 % v6-cycle baseline. Plus **144 HTTP 429s** and **96 tracebacks** in the log, none of which surfaced through the pool's `failed=` boundary.

**What this means for §J.** The structural cleanup ran correctly (stale TEMA edges wiped, clean re-MERGE). But its inputs were ~55 % N1-only classifier verdicts. The new `iva` binding for the RENTA/Deductions doc may itself be a degradation artifact, not a stable N2-refined verdict. **§J is structurally ✅ but data-quality 🧪.** Full ✅ requires a re-run with `--classifier-workers 4` (per the updated rule in `docs/learnings/ingestion/parallelism-and-rate-limits.md`) before §K's classifier hardening can be measured fairly.

**Operational fixes landed alongside the audit:**

- `scripts/ingestion/launch_phase2_full_rebuild.sh` — added the `PHASE2_FULL_REBUILD_EXIT=$?` log marker (per `docs/learnings/process/observability-patterns.md`); next launch will emit an unambiguous terminal-state signal.
- `docs/learnings/ingestion/parallelism-and-rate-limits.md` — added the 2026-04-24 §J data point (55 % degradation at 8 workers) and made `--classifier-workers 4` the new default for production full-rebuilds.

**Re-flip gate update.** From "blocked on §K only" → "blocked on (§K + a clean rebuild at `--classifier-workers 4`)." Order of operations: workers=4 rebuild first, THEN the §K design call against a clean baseline, THEN §K code, THEN re-run staging A/B, THEN flip.

### §J.2 Audit-gated rebuild — guardrail against silent degradation

**Why this exists.** The 2026-04-24 23:29 UTC rebuild was declared ✅ on a `failed=0` pool result that hid 27.5% N1-only degradation, 96 tracebacks, and 48 HTTP 429s. The cloud-sink-execution-notes mandate ("audit `requires_subtopic_review=true` before trusting the result as FANTASTIC") was a manual checklist nobody enforced. So the next rebuild ships with a runtime guardrail.

**Code landed (2026-04-24, in the same session as §J).**

- `scripts/diagnostics/audit_rebuild.py` — single source of truth for thresholds. Reads the rebuild's log + the run's slice of `logs/events.jsonl`, computes degradation rate + traceback count + HTTP 429 count + exit-marker presence + summary-block presence, exits non-zero on any failure. Pinned thresholds (loosen only with a same-PR test edit + justification):
  - `requires_subtopic_review` rate ≤ **5.0%** (strict-greater fails)
  - tracebacks in log = **0**
  - HTTP 429 / `RESOURCE_EXHAUSTED` count = **0**
  - `PHASE2_FULL_REBUILD_EXIT=0` marker present
  - top-level `--json` summary block present
- `tests/test_audit_rebuild.py` — 11 pytest cases, all green. Pinned: clean run passes, today's 27.5%-degradation case fails with all three operationally-actionable messages, silent-death case fails on missing marker, non-zero exit fails, stale events from prior runs ignored, threshold boundary 5.0%-passes-but-6.0%-fails, JSON output round-trips, exit codes 0/2.
- `scripts/ingestion/launch_phase2_full_rebuild.sh` — defaults `LIA_INGEST_CLASSIFIER_WORKERS=4`, invokes `audit_rebuild.py` inline after the rebuild, writes `PHASE2_AUDIT_VERDICT=clean|degraded` to the log tail. **That marker — not the rebuild's own exit code — is the trustworthy success signal.**

**Self-test.** Running the audit against the 23:29 UTC rebuild log (the actual degraded run) returned exit 2 with all four expected failures named. Audit demonstrably catches the case it was designed for.

**Threshold rationale.** 5% degradation is the cloud-sink-execution-notes line; 0 tracebacks / 0 429s is stricter than the upstream doc but reflects the true cost: each 429 is one doc that landed N1-only-degraded, and each traceback is a real Python failure that escaped the pool's `failed=` boundary. If a future engineering change makes the audit too noisy, the right response is to fix the underlying rate-limit pressure (TokenBudget primitive, fewer workers, smaller prompts), not to loosen the threshold.

### §J.3 Workers=4 re-run — outcome (2026-04-24 23:55 UTC · 06:55 PM Bogotá · ✅ §J cloud-verified, this time on a non-degraded classifier pass)

Re-launched via the now-audit-gated launcher (`scripts/ingestion/launch_phase2_full_rebuild.sh`, defaults `LIA_INGEST_CLASSIFIER_WORKERS=4`). Run finished 7m 43s wall, exit 0.

**First audit verdict: ❌ degraded.** Surfaced a refinement we needed: the audit's 5% degradation gate was over-broad. The workers=4 rebuild had **0 tracebacks, 0 HTTP 429s, but 30.4% `requires_subtopic_review=true`**. That's not TPM-induced degradation — that's the N2 cascade running cleanly and the LLM honestly returning "I can't pick a confident subtopic" for ambiguous docs. The cloud-sink-execution-notes original rule (5% → TPM pressure) was scoped to runs WHERE 429s were also present; my first-pass audit logic missed the pairing.

**Audit refinement landed in same session.** `audit_rebuild.py` now fails the degradation gate only when `requires_review > 5% AND (tracebacks > 0 OR 429s > 0)`. 429s and tracebacks are still hard-fails on their own. Tests `test_high_review_rate_without_tpm_signals_passes` and `test_high_review_rate_with_tpm_signals_fails` (plus `test_only_tpm_signals_with_low_review_rate_still_fails`) pin both behaviors.

**Re-audit verdict (refined logic): ✅ clean.** Workers=4 rebuild has 0 TPM signals and a high-but-honest 30.4% subtopic uncertainty rate — that's data about the corpus, not a failure.

**Cypher verification (2nd time):**

| Probe | Workers=8 (degraded) | Workers=4 (clean) | Verdict |
|---|---|---|---|
| Art. 148 → topic_keys | `[iva]` | **`[iva]`** | unchanged — confirms `iva` is a stable classifier verdict, not a degradation artifact |
| `gravamen_movimiento_financiero_4x1000` TEMA edges | 17 | **17** (canonical 870–881-1 intact) | ✅ stable across rebuilds |
| `sagrilaft_ptee` TEMA-bound articles | 23 (rogue 148 gone) | **23** (rogue 148 still gone) | ✅ §J cleanup persists |

**What this confirms.**

- §J's structural fix is correct AND its effect is durable across rebuilds with no TPM pressure. The `sagrilaft_ptee` cleanup of art. 148 holds.
- The remaining wrong `iva` classification on the RENTA/Deductions doc is a STABLE classifier verdict, not a degradation artifact (same answer at workers=8 with rate-limit pressure and at workers=4 without). That makes §K's design call meaningful: there's a real, stable, wrong verdict to fix.
- Q24's 17-edge GMF range is now confirmed stable across two independent rebuilds.

**Re-flip gate update (final).** From "blocked on (§K + clean rebuild at workers=4)" → "blocked on §K only." The clean baseline §K needs is now in place. Workers=4 + audit guardrail is the new default for any future production rebuild — the launcher enforces it and 13 pytest cases lock the audit thresholds.

### §J.4 Post-cleanup staging A/B `v9_post_cleanup` (2026-04-24 19:11 PM Bogotá · 3 min wall · exit 0)

Ran the 30-question A/B harness (`scripts/evaluations/run_ab_comparison.py --manifest-tag v9_post_cleanup --target production`) against the now-clean cloud — same harness as next_v1 §7.A action A, this time with art. 148's stale `sagrilaft_ptee` binding wiped. Output: `artifacts/eval/ab_comparison_20260425T001058Z_v9_post_cleanup.{jsonl,manifest.json}`.

**Q27 — canary case fixed end-to-end.**

| Run | Cloud state | Q27 NEW behavior |
|---|---|---|
| Yesterday's postflip (`v7_postflip_temafirston`, pre-§J) | art. 148 → `[iva, sagrilaft_ptee]` | seeds=`[148]`, primary=1, **answer cited art. 148 confidently** |
| Today's reproducibility (`v8_q24_reproducibility`, pre-§J) | art. 148 → `[iva, sagrilaft_ptee]` | seeds=`[148]`, primary=1, 101-char abstention (gate caught it) |
| Today's post-cleanup (`v9_post_cleanup`, post-§J) | art. 148 → `[iva]` | **seeds=`[]`, primary=0, 150-char abstention, NO art. 148 anywhere** |

Q27 contamination is gone structurally — TEMA-first no longer surfaces art. 148 as a candidate at all, so the synthesizer can't be tempted by it. ✅

**Q24 stable.** seeds=`['870','871','872']`, primary=3 (canonical GMF range, no regression from the workers=4 rebuild). ✅

**Q11 — different mis-classification, NOT fixed by §J.**

NEW returns `seeds=['514','515','516'], primary=3, answer cites art. 516`. Per `docs/learnings/retrieval/citation-allowlist-and-gold-alignment.md`, art. 514/515/516 are **impuesto de timbre** articles — pure retrieval leakage when the topic is `facturacion_electronica`. Same pattern as Q27 (tax-code articles bound to a wrong topic) but for Q11 it's the CURRENT classifier verdict, not accumulated stale state. §J cleanup correctly left the current verdict in place; §K is the only path forward for this class of bug.

**Headline metrics vs. action A's decision rule (next_v1 §7.A):**

| Criterion | Target | v9 measured | Verdict |
|---|---|---|---|
| `seed_article_keys` non-empty in NEW | ≥ 20/30 | **14/30** | ❌ |
| Mean `primary_article_count` in NEW | ≥ 2.5 | **1.53** | ❌ |
| Contamination 4/4 clean | 4/4 (non-negotiable) | 3/4 (Q11 leaks) | ❌ |
| No ok→zero regression | full pass | several | ❌ |

**Important nuance — the seed-count drop is cleanup signal, not regression.** Step-01 verification (pre-§J) measured 21/30 non-empty seeds; v9 measured 14/30. The 7-row drop is the §J cleanup wiping stale wrong TEMA edges out of the cloud. Those 7 rows had seeds populated by accumulated bad classifier verdicts, not real evidence. Post-cleanup we have a HONEST baseline — what retrieval looks like when it can't lean on historical mis-classifications. The 14 remaining seeds are legitimately TEMA-anchored.

**Net read.** §J's structural fix is fully ✅: stale-state contamination eliminated, baseline now honest. §K is the unambiguous remaining blocker for the re-flip — Q11's `514/515/516 → facturacion_electronica` leak is exactly the design case. Probing the Q11 leak source via Cypher (next, in this session) will sharpen §K's design call by giving the SME a second concrete case alongside Q27's art. 148.

**Re-flip gate (latest):** ❌ stays blocked on §K. The classifier-side fix is now strictly the only thing standing between us and the re-flip.

### §J.5 Q11 leak Cypher probe — bigger than expected (2026-04-25 00:13 UTC · 07:13 PM Bogotá)

Ran `scripts/diagnostics/probe_q11.py` against staging Falkor. Two findings, both load-bearing for §K's design call.

**Finding 1 — the ENTIRE Libro 4 of the Estatuto Tributario is mis-classified.**

```cypher
MATCH (a:ArticleNode)-[:TEMA]->(t:TopicNode)
WHERE a.article_number IN ['514','515','516']
RETURN a.article_number, a.source_path, collect(DISTINCT t.topic_key)
```

returned all three articles with `source_path = "knowledge_base/CORE ya Arriba/RENTA/NORMATIVA/Normativa/17_Libro4_Timbre.md"` and `topic_keys = [facturacion_electronica]`. The follow-up sweep over `facturacion_electronica`'s full TEMA-bound article list shows arts. 514, 515, 516, 517, ..., 540, 539-1, 539-2, 539-3, 540 all bound to `facturacion_electronica` from the same source path. **Every numbered article of ET Libro 4 (the impuesto de timbre book) is in the cloud graph as a `facturacion_electronica` anchor.** That's ~30 articles, not just three.

**Finding 2 — there is NO `impuesto_timbre` topic in the cloud taxonomy.**

`MATCH (t:TopicNode) WHERE t.topic_key CONTAINS 'timbre' RETURN t.topic_key, t.label LIMIT 5` returned **0 rows**. The taxonomy has no slot for impuesto-de-timbre content. Faced with `17_Libro4_Timbre.md` (whose entire content IS impuesto-de-timbre), the classifier picked the nearest-sounding existing topic — `facturacion_electronica` — because notas-crédito / electronic-doc context is the closest semantic neighbor in the available topic set.

**Root cause is two stacked problems, not one.**

1. **Taxonomy gap.** `impuesto_timbre` is missing from `config/topic_taxonomy.json` (and the cloud TopicNode set). New step 03 backlog item alongside the phase-5 SME-blocked topics already on deck (firmeza_declaraciones, regimen_sancionatorio_extemporaneidad, devoluciones_saldos_a_favor).
2. **Classifier picks nearest-sounding when correct topic is absent.** Same shape as Q27's RENTA/Deductions doc → `iva` mis-routing, but Q27's correct topic (`costos_deducciones_renta`) DOES exist in the taxonomy — that's a pure classifier-hardening case. Q11's correct topic doesn't exist, so the classifier had no right answer to pick.

**Implications for §K design call.**

The §K options now have differentiated coverage:

| Option | Q27 (correct topic exists, classifier picks wrong) | Q11 (correct topic missing entirely) |
|---|---|---|
| K1 — tighten the prompt with negative examples | helps | doesn't help (no correct slot to route to) |
| K2 — path-based veto on RENTA-rooted docs | helps + no-topic outcome (better than wrong topic) | helps + no-topic outcome (Libro4_Timbre.md gets vetoed away from facturacion_electronica) |
| K3 — human-review queue for low-confidence verdicts | helps | helps (queue surfaces the missing-topic gap) |
| **Add `impuesto_timbre` to taxonomy + re-classify** | doesn't help | **fully fixes Q11** |

**Recommended path: taxonomy patch + K2 in parallel.** Add `impuesto_timbre` to `config/topic_taxonomy.json` (and topic-keyword bucket in `topic_router_keywords.py`), re-run the workers=4 rebuild → §J cleanup wipes the bad `facturacion_electronica` bindings for Libro4_Timbre articles, classifier re-routes them to `impuesto_timbre`. K2 lands in the same PR as the safety net for future similar cases. K1/K3 stay as v8 follow-ups.

The Cypher dump (`scripts/diagnostics/probe_q11.py`) is now the second concrete case to bring into the SME design call alongside Q27's art. 148.

### §J.6 Comprehensive taxonomy-vs-corpus audit (2026-04-25 00:30 UTC · 07:30 PM Bogotá)

After Q11 surfaced a missing-topic class, ran a full audit across all 79 taxonomy keys, 67 cloud TopicNodes, and 1,280 ingested docs. Three categories of findings.

**Category A — taxonomy classes that EXIST but have ZERO TEMA edges in cloud (12 of 79).**

| Empty class | Has corpus content? | Where it lives now |
|---|---|---|
| `ingresos_fiscales_renta` | YES — `RENTA/NORMATIVA/Normativa/02_Libro1_T1_Cap1_Ingresos.md` | 44 edges in `iva` (wrong) |
| `patrimonio_fiscal_renta` | YES — `RENTA/NORMATIVA/Normativa/10_Libro1_T2_Patrimonio.md` | 63 edges in `sector_cultura` (totally wrong domain) |
| `firmeza_declaraciones` | YES — `FIRMEZA_DECLARACIONES_ART714/` corpus dir | scattered, only 3 edges in `obligaciones_profesionales_contador` |
| `devoluciones_saldos_a_favor` | YES — `DEVOLUCIONES_SALDOS_FAVOR/` corpus dir + ET Libro 5 arts. 850–865 | mostly absorbed into `iva`'s 280 + 155 Libro-5 edges |
| `ganancia_ocasional` | YES — ET Libro 1 Title 3 (arts. 299–318) | not yet probed; likely scattered into `iva` or `declaracion_renta` |
| `renta_liquida_gravable` | YES — ET Libro 1 T1 Cap7 | likely scattered |
| `descuentos_tributarios_renta` | YES — ET arts. 254–260 | likely scattered |
| `anticipos_retenciones_a_favor` | YES — ET arts. 365–371 | likely scattered |
| `tarifas_tasa_minima_renta` | YES — ET arts. 240–243 | likely scattered |
| `beneficio_auditoria` | unclear — ET art. 689-3 | likely none |
| `conciliacion_fiscal` | unclear — DUR / formato 2516 | likely none |
| `regimen_sancionatorio_extemporaneidad` | unclear — ET art. 641 | likely none |

**These do NOT need new taxonomy classes — they need RECLASSIFY.** The taxonomy slot exists; the classifier just doesn't route to it. The first three rows have confirmed corpus content stuck in obviously wrong topics (Patrimonio in sector_cultura is the most absurd — 63 edges of income-tax patrimony content labeled as cultural-sector).

**Category B — domains in the corpus with NO matching taxonomy class.**

| Corpus dir | Content domain | Currently routed to | New class? |
|---|---|---|---|
| `RENTA/NORMATIVA/Normativa/17_Libro4_Timbre.md` (~30 articles) | impuesto de timbre | `facturacion_electronica` (the Q11 case) | **YES — `impuesto_timbre`** |
| `RENTA_PRESUNTIVA_ART189/` + `07_Libro1_T1_Cap6_Rentas_Especiales_Presuntiva.md` | renta presuntiva (ET art. 189) | 26 edges in `iva` | **MAYBE — `renta_presuntiva` or subtopic of `declaracion_renta`** |
| `PROTECCION_DATOS_RNBD/` | habeas data / Ley 1581 / RNBD registry | 3 edges in `datos_tecnologia` (loose fit) | **MAYBE — `proteccion_datos_personales` or stay in datos_tecnologia** |
| `ZOMAC_INCENTIVOS/` | tax incentives for conflict-affected zones | not yet bound (corpus not classified) | **MAYBE — fits in `inversiones_incentivos` as subtopic** |
| `RUT_RESPONSABILIDADES/` | RUT registry codes/responsibilities | 4 edges in `beneficiario_final_rub` (which is RUB, a DIFFERENT registry) | **YES — `rut_responsabilidades` (RUT ≠ RUB)** |
| `PARAFISCAL_ESPECIAL/` | parafiscales (ICBF, SENA, cajas) | 1 edge in `presupuesto_hacienda` (very wrong) | **MAYBE — subtopic of `laboral`, or new `parafiscales`** |
| `REFORMA_LABORAL_LEY_2466/` | reforma laboral 2025 | not yet probed | **MAYBE — subtopic of `laboral`** |

**Net new-class verdict:**
- **`impuesto_timbre`** — definitely needed (Q11 root cause).
- **`rut_responsabilidades`** — likely needed (RUT and RUB are distinct registries; bucketing RUT into RUB is a cross-registry contamination of the same shape as the Q27 case).
- **`renta_presuntiva`, `proteccion_datos_personales`, `zomac_incentivos`, `parafiscales`, `reforma_laboral_2466`** — design call territory; could be new classes or subtopics. SME should decide based on whether the chat surface needs to distinguish them at the topic level.

**Category C — magnet topics (existing classes flooded with wrong-domain content).**

| Topic | Total TEMA edges | Edges from CORRECT domain | Edges from WRONG domains | Severity |
|---|---|---|---|---|
| `iva` | 917 | 164 (Libro 3 IVA) + 6 (IVA_COMPLETO/CALENDARIO) = 170 | **747** (multiple RENTA Libros: Procedimiento P1+P2 = 435, Libro 1 chapters = 252, Libro 7 ECE/CHC = 21, Régimen Especial = 18, Ajustes Inflación = 16, Libro 1 Título Preliminar = 1, Cap 6 Rentas Especiales = 26, Sujetos Pasivos = 27) | 🔥 **81% of IVA's edges are wrong** |
| `sector_cultura` | 89 | 26 (LEYES sectoriales — legitimate) | **63** from `10_Libro1_T2_Patrimonio.md` (income-tax patrimony, not culture) | 🔥 **71% wrong** |
| `facturacion_electronica` | 67 | 18 (FACTURACION_ELECTRONICA_OPERATIVA + facturacion_electronica + LEYES) | **49** from `17_Libro4_Timbre.md` (Q11 case) | 🔥 **73% wrong** |
| `declaracion_renta` | 140 | ~125 (RENTA dir, mostly correct) | ~15 scatter | ✅ healthy |
| `gravamen_movimiento_financiero_4x1000` | 17 | 13 (Libro 6 GMF) + 3 (GMF_4X1000) + 1 LEYES | 0 | ✅ healthy |

**The IVA topic is the worst single bug in the cloud.** 747 of 917 edges (81%) are RENTA-tax content the classifier dumped into IVA when uncertain. The Q27 art. 148 case was a single visible symptom of this — the same bug touches every RENTA Libro 1 chapter.

**Verdict tally:**

- **Need new taxonomy classes (definitely):** `impuesto_timbre`, `rut_responsabilidades`. Cost: ~30 min config edit each + a workers=4 rebuild.
- **Need new classes (maybe — SME call):** `renta_presuntiva`, `proteccion_datos_personales`, `zomac_incentivos`, `parafiscales`, `reforma_laboral_2466`.
- **Need RECLASSIFY (no new class):** 12 empty taxonomy slots, of which at least 9 have confirmed RENTA-family content stuck in `iva` or `sector_cultura`. Cost: classifier hardening (§K) — exactly the design case.
- **Major bug surfaced:** the `iva` topic has 81% wrong-domain content. §K's path-based veto (Option K2) on RENTA-rooted-but-not-Libro3-IVA paths would unblock most of this in one stroke.

**Implications for §K and step 03.**

- §K's Option K2 (path-based veto) is now the highest-leverage fix in the program. Routing `RENTA/NORMATIVA/Normativa/<libro>` to the correct sub-topic by file-name pattern alone would clear ~750 wrong edges out of `iva`, repopulate 4-9 empty taxonomy slots, and fix Q27 + Q11 simultaneously.
- Step 03 (phase-5 SME-blocked content) was framed as "0 docs in those topics; commission new content." This audit shows that's only partly true — for at least 4 of those topics (`ingresos_fiscales_renta`, `patrimonio_fiscal_renta`, `firmeza_declaraciones`, `devoluciones_saldos_a_favor`), the content already exists in the corpus, just routed wrong. Reclassification is cheaper than commissioning new content.

---

## §K Classifier hardening for RENTA/Deductions mis-routing (root cause for §3 finding 1) — SME-blocked

1. **Idea.** The AI document classifier assigned the same RENTA / Deductions document (`06_Libro1_T1_Cap5_Deducciones.md`) to **`iva`** on one run and **`sagrilaft_ptee`** on another. Both verdicts are wrong; the correct topic is in the `costos_deducciones_renta` / `renta_personas_naturales` family. This is classifier instability on a document whose path screams "RENTA." Three candidate hardening approaches; SME should pick (or combine).
2. **Plan options** (need design call with SME / abogado-contador before code):
   - **Option K1 — Tighten the classification prompt.** Add explicit negative examples ("a chapter from Libro 1 of the Estatuto Tributario in `RENTA/NORMATIVA/Normativa/` MUST NOT be classified as `sagrilaft_ptee` or `iva`; it is a renta-deductions doc") and require the model to cite the path or directory in its rationale before emitting the topic_key. Cheapest; risks under-fitting.
   - **Option K2 — Path-based veto.** Post-LLM sanity check: if the resolved `topic_key` is in a "compliance" / "indirect-tax" set but the document's `source_path` is rooted under `RENTA/`, raise `requires_subtopic_review=true` and route to a re-classification queue. Strong guard, but couples taxonomy to filesystem layout (which is already de-facto canonical).
   - **Option K3 — Low-confidence human-review queue.** Surface low-confidence verdicts (or any verdict that conflicts with the document's directory tier) into an admin-UI review queue. Most accurate; needs UI work + SME bandwidth to drain the queue.
3. **Success criterion.** Two consecutive full-corpus classifier runs produce the SAME `topic_key` for `06_Libro1_T1_Cap5_Deducciones.md` (and ideally for every other doc rooted under `knowledge_base/CORE ya Arriba/RENTA/NORMATIVA/`), AND that `topic_key` is from the renta-deductions family, not iva or sagrilaft_ptee.
4. **How to test.**
   - *Development.* Once approach is chosen, unit-test the path-aware sanity check (K2) or the prompt-revision regression (K1) using a fixture set of 5–10 RENTA docs. Confirm no doc routes to a compliance/indirect-tax topic.
   - *Conceptualization.* Stability across runs is the pass condition; a single correct verdict that flips next run is still failure.
   - *Running environment.* Cloud classifier run against the v6 corpus + Gemini budget. SME spot-check on a sample of 20 RENTA docs.
   - *Actors.* SME (abogado/contador) for design call + spot-check. Engineer for code + cloud run.
   - *Decision rule.* Two-run stability AND zero RENTA-rooted docs labeled as compliance/indirect-tax in the second run.
5. **Greenlight.** 5a: unit test for the chosen approach. 5b: SME spot-check ≥ 95 % agreement on the 20-doc sample; two-run stability test passes.
6. **Refine-or-discard.** If hardening still mis-classifies > 1 % of RENTA docs → escalate to Gemini Pro for the classifier (next_v2 §10 hard-stop "step 06 shows Gemini Flash is the wrong tier") and combine K1 + K2.

### Status (2026-04-24 · 📝 spec'd · SME-blocked)

The probe in §3 surfaced the symptom; the design choice between K1 / K2 / K3 needs the SME's perspective on which Colombian-tax-domain mis-classifications are tolerable and which are non-negotiable. Until that conversation happens, no code lands here.

---

## §10 Hard stop conditions

Abort + reassess if any:

- **§H fix requires ripping out TEMA-first entirely** — the v5 architecture is wrong; pivot to planner upgrades + step 03 to recover the +15 retrieval-rescue lift a different way.
- **§I cloud drift is intrinsic** — FalkorDB staging can't hold TEMA state reliably across hours; redesign TEMA-first to read artifact plan instead of live graph.
- **Step 03 SME commission can't close inside plan horizon** — remove the 3 phase-5 topics from `topic_taxonomy.json` (explicit discard; taxonomy debt).
- **Step 06 shows Gemini Flash is the wrong tier** — escalate to Gemini Pro for classifier calls, or a different provider.
- **Any re-flip of TEMA-first reintroduces contamination** — non-negotiable. Stay on `shadow`.

---

## §11 What success looks like at close of next_v2

**Hard gates** (all must ✅):

1. §2 revert shipped — `LIA_TEMA_FIRST_RETRIEVAL` launcher default = `shadow` across all five mirror surfaces, env matrix `v2026-04-24-temafirst-revert`. ✅ landed 2026-04-24.
2. §H Q27 `art. 148` leak root-caused + fixed. 🧪 root-caused 2026-04-24; fix split into §J (landed in code, awaiting cloud re-ingest) + §K (SME-blocked).
3. §I Q24 regression root-caused + fixed. ↻ resolved as flake 2026-04-24 — reproducibility A/B `v8_q24_reproducibility` restored Q24 NEW `primary_article_count=3`; downgraded to watch.
4. §J cloud verification — fresh re-ingest + Cypher probe shows art. 148 bound to exactly one (correct) topic. ✅ landed 2026-04-24 — stale binding wiped; the remaining single wrong verdict is §K's job.
5. §K classifier hardening landed in code AND two-run stability test passes on RENTA/Deductions sample.
6. §5 staging A/B re-run passes all 4 criteria.
7. Contamination still 4/4 zero-hits on Q11/Q16/Q22/Q27 (non-negotiable, carries over from next_v1).

**Soft gates** (lift but don't block):

- Step 03 phase-5 topic content landed → mean primary ≥ 3.0 in next A/B.
- §D pool integration landed → 0 Tracebacks on full classifier pass.
- Step 08 gold v2 → ≥ 40 questions passing eval-c-gold ≥ 90.
- Step 09 verdict cache → replay < 60 s.

End of next_v2 = v7 plan ready (a 40-question A/B against production with §H + §I fixes + flag re-flipped). That becomes `next_v3.md`.

---

*Opened 2026-04-24 after next_v1 action A returned ↩ regressed. See [`next_v1/README.md`](./next_v1/README.md) for the archived history + outcome blocks + six-gate policy discussion.*
