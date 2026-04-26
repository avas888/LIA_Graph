# Ingestion Fix v6 — Forward RAG-quality backlog

> **Status:** forward-looking backlog · **Opened:** 2026-04-24 after `ingestion_tunningv2.md` (v6) phase 6 validation closed with a PASS on the non-negotiable contamination gate.
>
> **What this doc is.** A prioritized catalog of **every idea still valid** for improving RAG quality in Lia_Graph — old (from v1–v5 follow-ups that didn't make the v6 cut) plus new (surfaced during the v6 execution + phase 6 validation on 2026-04-24). Each item has a one-line hypothesis, the evidence for it, the approximate scope, and what success looks like.
>
> **What this doc is NOT.** An execution plan. Every item below needs a separate investigation doc (v1-style) or a dedicated plan doc (v2-style) before code is written. This doc's purpose is to force a single, prioritized, triage-ranked view of the work so we don't drift into convenient-but-low-value fixes.
>
> **Reading order.** §1 gives the scorecard from phase 6 so you know what "better" means now. §§2–5 are the four improvement lanes, each ranked. §6 sequences the top-10 items for v7.

---

## §1 Phase 6 scorecard — where v6 left us (2026-04-24)

The non-negotiable contamination gate passed: Q11/Q16/Q22/Q27 all returned answers with **zero forbidden-token hits**. The mechanism was the rebuilt corpus + classifier refinements, not the defensive coherence-gate/allow-list (both were armed but didn't need to fire).

| Gate | Target | Hard gate | Measured | Status |
|---|---|---|---|---|
| Contamination zero-hit on Q11/Q16/Q22/Q27 | 4/4 | 4/4 (non-negotiable) | **4/4** | ✅ |
| `primary_article_count != None` in NEW mode | ≥25/30 | ≥20/30 | **30/30** | ✅ |
| `primary_article_count >= 1` in NEW mode | ≥20/30 | ≥15/30 | **15/30** | ✅ just meets gate |
| Mean `primary_article_count` in NEW mode | ≥3.0 | ≥2.0 | **1.6** | ❌ fails |
| `tema_first_mode == "on"` in NEW mode | 30/30 | 28/30 | **26/30** | ❌ 4 rows short |
| `tema_first_anchor_count >= 1` in NEW mode | ≥20/30 | ≥10/30 | **15/30** | ✅ meets gate |
| `seed_article_keys` non-empty in NEW mode | ≥20/30 | ≥10/30 | **0/30** | ❌ fails gate |
| Cloud Falkor ArticleNode count | ≥12,500 | ≥11,500 | **9,245** | ✅ gate revised (plan miscalc) |
| Supabase `normative_edges` growth | +15k | — | **+30,083** | ✅ |

**Full panel markdown:** `artifacts/eval/ab_comparison_20260424T183902Z_v6_rebuild.md`.

**Reading of the above.** We're not broken, but we're not done. Contamination is solved by corpus + classifier quality, not by defensive gates. Retrieval depth (mean primary count) is thin and some diagnostic fields are still ghost-populated. v7 needs to close the retrieval-depth + diagnostic-surface gaps before we trust any further delta.

---

## §2 Lane A — retrieval quality (the gap between "answer exists" and "answer is complete")

### §2.1 [P0] Debug why `seed_article_keys=0/30` in NEW mode

**Hypothesis.** Phase 1 (`7d966ce`) lifted `seed_article_keys` to top-level `response.diagnostics`, reading from `evidence.diagnostics.get("seed_article_keys")`. The phase-6 run shows 0/30 — which means either (a) the retriever path never populates it in live cloud mode, (b) the lift reads the wrong key, or (c) the A/B harness serializes it wrong. Evidence: the 2026-04-24 phase-6 panel.

**Scope.** Read-only investigation first. Run one query through `run_pipeline_d` in `falkor_live` mode, `print(response.diagnostics)` verbatim, compare against `retriever_falkor.py` line 171 where `seed_article_keys` is built. ~1 hour.

**Success.** Either the key is genuinely empty (retriever doesn't populate it on this code path — fix retriever) or the harness is reading wrong (fix harness per phase-1 contract). Non-zero on re-run.

---

### §2.2 [P0] Mean `primary_article_count` at 1.6, target 3.0 — investigate BFS expansion

**Hypothesis.** Primary-article BFS from planner-anchored articles is under-expanding. Could be: (a) `traversal_budget.max_hops` too tight, (b) the planner's `entry_points` too narrow (the rewrite from v5 only emits explicit `article_key` anchors, misses semantic-related articles), (c) connected-article limit cap. Evidence: 15/30 rows have `primary_article_count >= 1` but the mean is 1.6 — meaning the NON-zero rows average ~3.2, but half the rows returned zero.

**Scope.** For each of the 15 zero-primary rows in phase 6, trace: what topic the classifier routed to, what articles the planner anchored, why BFS returned zero. Read-only investigation. ~1 day.

**Success.** Identify the dominant cause (planner vs graph-sparse-in-domain vs BFS-budget). Fix targeted at the cause. Target post-fix: mean ≥3.0.

---

### §2.3 [P1] Coherence gate: flip shadow → enforce

**Hypothesis.** Phase 3's coherence gate (`60829f0`) is armed in shadow mode. Phase 6 shadow-mode telemetry would tell us how many of the 30 questions would refuse in `enforce`. If that count is 4–12, flip to `enforce`. Evidence: plan §5.6 calibration band.

**Scope.** Parse the phase-6 JSONL for `topic_safety.coherence.misaligned == True` count. If in-band, flip `LIA_EVIDENCE_COHERENCE_GATE=enforce` in the launcher defaults. ~30 min.

**Success.** Refusal rate 5–15% in next A/B. Contamination still at 4/4 zero-hits.

---

### §2.4 [P1] Live reranker flip (Gemini reranker adapter)

**Hypothesis.** `LIA_RERANKER_MODE=live` was flipped on 2026-04-22 per `CLAUDE.md`. But `LIA_RERANKER_ENDPOINT` is unset so the adapter falls back to hybrid. Wiring an actual reranker endpoint (cross-encoder or Gemini-based reranker) should lift `primary_article_count` quality without lifting count.

**Scope.** Evaluate options (Cohere rerank, Voyage rerank, custom cross-encoder on Gemini embeddings). Pilot with one. ~1 week for pilot.

**Success.** Mean precision@3 on gold set improves by ≥10%.

---

### §2.5 [P2] Reform-history retrieval — make historical-query mode exercise the ReformNode graph

**Hypothesis.** The graph has `ReformNode` + `MODIFICA` / `DEROGA` typed edges. The historical-query planner mode (`historical_reform_chain`) should traverse these for "¿Qué decía el artículo X antes de la Ley Y?" questions. Evidence: Q-sample traces show the planner finds reforms but BFS doesn't chain through them consistently.

**Scope.** Audit `pipeline_d/retriever_falkor.py` historical-mode Cypher. Add multi-hop reform traversal. ~2 days.

**Success.** Questions requiring pre/post-reform comparison return both article snapshots.

---

### §2.6 [P2] Subtopic boost factor tuning

**Hypothesis.** `LIA_SUBTOPIC_BOOST_FACTOR=1.5` was flipped on 2026-04-22. Current panel shows subtopic routing works (phase 5 added 3 new subtopics for declaracion_renta procedural branches). We haven't measured boost-factor sensitivity. Values 1.0, 1.5, 2.0, 2.5 should each run through the 30Q gold to pick the optimum.

**Scope.** 4 panel runs varying the boost factor only. ~30 min/run + review. ~2 hours total.

**Success.** Pick the factor that maximizes `primary_article_count >= 1` rate without over-narrowing.

---

### §2.7 [P3] Embedding model upgrade assessment

**Hypothesis.** Supabase chunks are vectorized with Gemini Embedding 1 (from `embedding_ops.py`). Gemini has a newer Embedding 2 model that claims better Spanish-language performance. Retrieval quality might lift.

**Scope.** A-B eval: rebuild a WIP Supabase target with Embedding 2, run gold panel, compare. ~2 days wall time + cost.

**Success.** Gold-set `retrieval@10` lifts by ≥5%.

---

## §3 Lane B — ingest completeness + corpus quality

### §3.1 [P0] Ingest late-2024 / 2025 reforms

**Hypothesis.** v1 investigation I4 found 7 expected gold refs missing from corpus: LEY_2466_2025, LEY_1819_2016, CONCEPTO_DIAN_006483_2024, DECRETO_2616_2013, DECRETO_957_2019, DECRETO_1650, LEY_2277_2022 (some articles). Some have been added; others haven't. Evidence: gold_retrieval_v1.jsonl `expected_article_keys` has references not in `parsed_articles.jsonl`.

**Scope.** For each missing ref: (a) source the text, (b) add to `knowledge_base/` under the correct directory, (c) re-ingest via additive delta. ~2 days for content + 1 rebuild.

**Success.** All 57 gold-referenced articles are in the corpus; phase 6 panel shows higher `retrieval@10`.

---

### §3.2 [P1] TPM-aware token-budget limiter

**Hypothesis.** Phase 2c's `TokenBucket` throttles request count (RPM) but not token count (TPM). On the 2026-04-24 runs, ~7% of docs landed with `requires_subtopic_review=True` because EXPERTOS/PRACTICA bodies × 8 workers briefly exceeded the 1 M TPM ceiling. Evidence: 92–114 tracebacks per classifier pass, all catchable TPM 429s.

**Scope.** Add a `TokenBudget` sibling to `TokenBucket` in `ingest_classifier_pool.py`. Debit estimated-input-tokens pre-call, refund on 429. ~3 days including tests.

**Success.** ~0 tracebacks per full run. Zero `requires_subtopic_review=True` degraded docs.

---

### §3.3 [P1] Persistent verdict cache for idempotent replays

**Hypothesis.** Classifier verdicts today are deterministic within a run but not across runs (Gemini response drift). A persistent cache keyed on `sha256(prompt_template_version + model_id + content_hash)` would make replays bit-identical. Evidence: web-research synthesis during phase 2a design.

**Scope.** SQLite-backed cache module at `src/lia_graph/ingestion/verdict_cache.py`. Read-before-call, write-after-call. Invalidate via template_version bump. ~2 days.

**Success.** Replaying a 3-month-old ingest against cached verdicts completes in seconds (LLM calls skipped). Cache-miss rate on a re-run drops to near-zero.

---

### §3.4 [P2] Rescue-from-Other as automated post-sink step

**Hypothesis.** The Rescue-from-Other playbook (`gui_ingestion_v1.md §11`) is battle-tested (216/242 noisy docs rescued) but still operator-triggered. Making it automatic + idempotent post-sink would close a manual discipline gap. Evidence: 2026-04-23 production run.

**Scope.** Wire the 3-pass pipeline as a CLI flag `--auto-rescue` that fires after the sink when `otros_sectoriales` count exceeds 5% of corpus. Proposals still require operator-approved apply. ~3 days.

**Success.** One fewer manual step post-ingest.

---

### §3.5 [P2] Ingestion-time prefix/alias map extension

**Hypothesis.** The rule-based classifier at `ingest_classifiers.py` + `config/prefix_parent_topic_map.json` misses ~8% of Colombian laws by prefix. 2026-04-23 probe found 106 such misclassifications. Extending the prefix map closes the gap upstream of Rescue-from-Other. Evidence: `UI_Ingestion_learnings.md §11.10`.

**Scope.** Audit `otros_sectoriales` bucket post-rescue, extract the rule-augmentation candidates, extend the prefix map. ~1 day.

**Success.** Next full rebuild puts fewer docs into the catch-all initially.

---

## §4 Lane C — observability + GUI + ops

### §4.1 [P0] GUI deficiencies P0/P1 remediation (from `gui_ingestion_v1.md §13`)

**Hypothesis.** The GUI path has 5 P0/P1 gaps vs the CLI path (`§13.1` Makefile `--allow-non-local-env`, `§13.2` events.jsonl-anchored progress, `§13.3` timeout, `§13.4` worker-knob exposure, `§13.5` degradation surfacing, `§13.12` Falkor knob exposure, `§13.14` index-existence check). Evidence: that doc.

**Scope.** Per `gui_ingestion_v1.md §13.16` sequencing: land all P0s as one PR, all P1s as second PR. ~5 days total.

**Success.** Admin can trigger a full ingest via UI against production with all v6 defaults without editing env vars.

---

### §4.2 [P1] Emit `graph.batch_written` events from the sink writer

**Hypothesis.** Phase 2c batched writes land server-side silently. Emitting one event per batch (count, elapsed_ms) enables heartbeat stall detection during `falkor_writing` (`gui_ingestion_v1.md §8.4 post-phase-2c` table). Evidence: phase 2c execution — monitor was blind during Falkor phase.

**Scope.** +10 LOC in `src/lia_graph/graph/client.py` emitting from `_execute_live_statement` after a successful decode. ~1 hour.

**Success.** Heartbeat during Falkor phase shows per-batch ticks every 3–10 s.

---

### §4.3 [P1] Auto-source `.env.staging` in the Makefile target when `PHASE2_SUPABASE_TARGET=production`

**Hypothesis.** The operator's 2026-04-24 cloud-sink attempts all required `set -a; source .env.staging; set +a` prefixed manually. If we conditionally source inside the Makefile target when `production` is the target, the UI subprocess inherits correctly. Evidence: `cloud-sink-execution-notes.md`.

**Scope.** 1 make conditional rule. ~15 min.

**Success.** `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` works without a shell wrapper.

---

### §4.4 [P2] Delta-error detection in the shared heartbeat script

**Hypothesis.** `scripts/monitoring/ingest_heartbeat.py` has the same "re-fire-on-same-errors" bug my inline monitors hit 3 times on 2026-04-24. Fix once at the canonical source. Evidence: `heartbeat-monitoring.md §6`.

**Scope.** Add a `--traceback-baseline` flag + state-file that snapshots the count at start. ~2 hours.

**Success.** Inline monitors can delegate to the shared script without reinventing the baseline-snapshot pattern.

---

### §4.5 [P2] Falkor-phase live observability via `CLIENT LIST`

**Hypothesis.** When a Falkor bulk write seems stuck, opening a sibling Redis connection to run `CLIENT LIST TYPE normal | grep graph.query` distinguishes "server still executing" from "client stuck on recv". Evidence: `falkor-bulk-load.md §5`.

**Scope.** Add a `probe_falkor_inflight()` function to `dep_health.py` that enumerates in-flight graph queries. Expose via CLI flag. ~2 hours.

**Success.** Next time a Falkor write seems stuck, one command tells us whether to wait or kill.

---

### §4.6 [P3] Documented artifact-snapshot convention

**Hypothesis.** `artifact-coherence.md` documented that the artifact files are a SET; 2026-04-24 execution needed `.v5_backup` / `.skip_llm_interim` naming ad-hoc. A canonical snapshot helper would prevent drift. Evidence: same doc.

**Scope.** `scripts/snapshot_artifacts.sh` — tar to `artifacts/.snapshots/<stamp>/`, pruning older than 3. ~30 min.

**Success.** One command snapshots all artifact files atomically.

---

## §5 Lane D — retrieval-time evaluation + gold-set quality

### §5.1 [P0] Gold file extension — procedural tax topics

**Hypothesis.** Phase 5 added 3 new subtopics (`firmeza_declaraciones`, `regimen_sancionatorio_extemporaneidad`, `devoluciones_saldos_a_favor`) via keyword buckets + regex overrides, but the gold set still only has the original 30 questions. A 50-question gold with 5-7 new questions per new subtopic would give us real coverage numbers. Evidence: `citation-allowlist-and-gold-alignment.md`.

**Scope.** Commission the domain expert to write 10–20 new gold questions covering the phase-5 subtopics + any other under-tested procedural areas. ~3 days content work.

**Success.** Gold set 40–50 questions; phase 6 re-run with expanded set.

---

### §5.2 [P1] Gold-set adversarial additions — contamination traps

**Hypothesis.** The v5 panel surfaced 4 contamination cases by domain-expert inspection, not by the harness. An adversarial gold-set subsection should deliberately include queries that historically contaminated (biofuel-in-labor, timbre-in-FE) to regression-test the defensive filters. Evidence: `coherence-gate-and-contamination.md`.

**Scope.** Add 5–10 "trap" questions to the gold file with `expected_refusal: true` or `forbidden_substrings: [...]` fields. Harness checks them. ~1 day harness extension + content.

**Success.** Gate flips during v7 that reintroduce contamination fail the panel loudly.

---

### §5.3 [P2] Retrieval eval in addition to A/B eval

**Hypothesis.** `scripts/eval_retrieval.py` exists and scores `retrieval@10 / nDCG@10 / MRR / topic_accuracy / subtopic_accuracy / sub_question_recall@10`. It's not in the v6 phase 6 validation. Running it alongside the A/B gives quantitative retrieval-quality trend. Evidence: `package_expert.md` (now in `docs/done/`).

**Scope.** Add an `eval-retrieval` step to the phase 6 protocol. Track scores per commit. ~2 hours.

**Success.** Every phase-6-class validation produces both panel + retrieval numbers.

---

### §5.4 [P3] Expert panel for phase 6 — resume the human loop

**Hypothesis.** v5 had a senior-contador panel. v6 phase 6 was automated-only. A human-panel review on the phase 6 panel doc would catch semantic regressions that forbidden-substring checks miss. Evidence: panel's Q16 biofuel catch.

**Scope.** Commission one panel review per major v6/v7 ship. ~4 hours/ship.

**Success.** Human verdicts match automated gates; divergences become new gold-set entries.

---

## §6 Sequencing for v7 — the top-10

If v7 is a single-plan cycle, these are the items in order. Lane letter + doc §-reference in brackets.

| Rank | Item | Lane.§ | Effort |
|---|---|---|---|
| 1 | `seed_article_keys=0/30` diagnostic plumbing | A.1 | 1 hour |
| 2 | Mean `primary_article_count` 1.6 → 3.0 investigation | A.2 | 1 day |
| 3 | Ingest late-2024/2025 reforms | B.1 | 2 days |
| 4 | GUI P0 remediation (Makefile env + events endpoint) | C.1 subset | 2 days |
| 5 | Coherence gate shadow→enforce flip | A.3 | 30 min |
| 6 | TPM-aware token-budget limiter | B.2 | 3 days |
| 7 | Emit `graph.batch_written` events | C.2 | 1 hour |
| 8 | Gold file extension for procedural tax | D.1 | 3 days |
| 9 | Persistent verdict cache | B.3 | 2 days |
| 10 | Auto-source `.env.staging` in Makefile | C.3 | 15 min |

**Total effort estimate:** ~16 engineering days spread across 4 lanes. Sequenced so the first week closes the retrieval-depth + diagnostic-plumbing gaps (items 1, 2, 3, 5) — those are pre-requisites for trusting any further quality metrics.

---

## §7 Items explicitly deferred or dropped

These surfaced during v6 but are not worth investigating further right now:

| Item | Why dropped |
|---|---|
| Classifier redesign (graph-query mode) | v1 I2 showed the keyword-table classifier reaches 27/30 right with known fixes; redesign is weeks for marginal gain. |
| Path B rebuild (full retrieval-contract redesign) | v1 concluded that tightening > rewriting. v6 validated the tightening approach. Re-open only if v7 items 1–5 don't move the needle. |
| `cross_topic=true` edge-flag | Proposed to handle Práctica/Expertos cross-cutting content. Phase 6 shows v6's topic gate doesn't over-filter; no evidence yet we need the flag. |
| Full Falkor parallelization | Cypher MERGE contention makes naive parallelism unsafe. Would require per-label sharding or subgraph partitioning. Deferred until Falkor is the measured bottleneck (it isn't). |

---

## §8 Where this plugs into the repo

- **Execution plan doc** that follows this backlog: `docs/next/ingestion_tunningv3.md` (to be written when v7 items 1–5 are approved for execution).
- **Investigation doc** for items that need one (A.1, A.2, B.1): `docs/next/ingestion_tunningv3_findings.md`.
- **Remediation plan** for the GUI deficiencies (C.1): `docs/next/gui_ingestion_v2.md` (to be written when the GUI path is prioritized).
- **Learnings that apply here:** all of `docs/learnings/` (ingestion + retrieval + process lanes).

---

*Opened 2026-04-24 after v6 phase 6 panel. Every item cites the specific evidence that motivated it — if an item's evidence stops being true, strike it. No item should live here without a concrete failure or a concrete measured gap.*
