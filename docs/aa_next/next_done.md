# next_done — closed forward-plan archive (next_v1 + v2 + v3)

> **Opened 2026-04-25** to consolidate the three closed forward-plan cycles. The full execution detail is preserved in git history (`git log -- docs/aa_next/next_v1/ docs/aa_next/next_v2.md docs/aa_next/next_v3.md`) and in the standalone decision/process docs that remain in this folder. **This file is the digest** — what each cycle was about, what landed, what got deferred to next_v4.

## Active artifacts (not consolidated, still in use)

- **`next_v4.md`** — active forward plan. Item §1: coherence-gate calibration diagnostic against the 11 measurement-set questions (operator-scoped 2026-04-25).
- **`gate_9_threshold_decision.md`** — operator's 2026-04-25 decision record on the §8.4 qualitative-pass + binding conditions (verbatim change-log row, no threshold-lowering, gates evaluate independently).
- **`taxonomy_v2_sme_response.md`** — Alejandro's 2026-04-25 SME deliverable on the v2 taxonomy spec.
- **`taxonomy_v2_sme_spot_review.md`** — the 7-question packet that closed gate 8 (after Alejandro's reply).
- **`taxonomy_v2_expert_brief.md`** — context doc shipped to Alejandro before the SME conversation.
- **`structural_groundtruth_v1.md`** — first-principles audit that opened the next_v3 work.
- **`README.md`** — six-gate lifecycle policy that governs every change to the served runtime.

## Cycle 1 — `next_v1` (closed 2026-04-24)

**Mission.** Investigate why TEMA-first retrieval (`LIA_TEMA_FIRST_RETRIEVAL=on`) produced empty seeds on 9/30 gold questions, and either fix or discard the flag's promotion.

**What landed:**
- **Step 01** (seed-article-keys debug): root-caused as a missing-diagnostic problem (planner returned topic but seeds went unrecorded). Fix landed; six-gate verification at 21/30 non-zero seeds with 30/30 invariant `primary_article_count ≥ 1 ⇒ seed_article_keys non-empty`.
- **Step 02** (retrieval-depth investigation): characterized the 9 still-zero questions; deferred to a corpus + planner work-stream that became next_v2 §H/§I.
- **Step 06** (TPM token budget): scoped the `TokenBudget` + `TPMRateLimitError` primitive needed to safely run workers=8 against production. Code primitive landed; runtime wiring deferred to next_v2 §7.

**Outcome:** TEMA-first briefly flipped `shadow → on` 2026-04-24, then reverted same day after staging A/B showed Q27 contamination (`art. 148 ET` leaking into a SAGRILAFT answer). The +15-row retrieval lift was real; the contamination risk made `on` premature.

## Cycle 2 — `next_v2` (closed 2026-04-25)

**Mission.** Close the contamination risk and the structural debt next_v1 surfaced. Specifically: (§J) Falkor TEMA-edge cleanup + loader hardening; (§H) ingest pipeline parallelism + audit guard; (§I) test-flake purges; (§K) sketch the rule-based path-veto layer (Option K2) the SME said was likely needed atop the LLM classifier.

**What landed:**
- **§J cleanup**: Falkor loader hardening — TEMA edges now MERGE not REPLACE; catch-all topic preservation; tested in cloud rebuild. Closed gate 2 of next_v3 §9.
- **§H pipeline parallelism**: workers=4 default for production rebuilds (workers=8 deferred until TokenBudget primitive ships); audit guardrail (`scripts/diagnostics/audit_rebuild.py`) hooked into the launcher. The `PHASE2_AUDIT_VERDICT={clean|degraded}` line is now the trustworthy success signal. Closed gate 6.
- **§I Q24 flake**: closed as flake (intermittent Falkor read race); re-tested clean.
- **§K2 sketch**: rule-based path-veto layer designed but not implemented. Carried into next_v3 §13.7 and shipped there.

**Outcome:** Foundation ready for the next_v3 substantive taxonomy + classifier rewrite. Re-flip still gated.

## Cycle 3 — `next_v3` (closed 2026-04-25)

**Mission.** Land the substantive RAG lift: taxonomy v2 (89 topics, 6 mutex rules, 11 new top-levels), taxonomy-aware classifier prompt, K2 path-veto layer, SME 30Q validation, A/B re-run, and **the re-flip itself** if all 9 gates clear.

**Build track (items 1–7 of §1):**
- **Taxonomy v2**: `config/topic_taxonomy.json` v2026_04_25_v2_taxonomy — 89 topics from SME deliverable, 6 mutex rules, 11 new top-levels, 5 renames, 1 deprecation-split (NIIF). 57 schema tests green.
- **Router keywords**: 19 new/renamed buckets in `topic_router_keywords.py`.
- **Allow-list for non-ET topics**: `allowed_norm_anchors` field on 7 non-ET topics; 14 tests green.
- **Gold + alignment CI gate**: drift fixed; `tests/test_gold_taxonomy_alignment.py` green.
- **SME 30Q encoded**: `evals/gold_taxonomy_v2_validation.jsonl` + `make eval-taxonomy-v2`.
- **Classifier prompt rewrite**: taxonomy-aware enumeration + 6 mutex rules + path-veto clause. `LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE` flag.
- **Audit-gated rebuild #5**: `PHASE2_AUDIT_VERDICT=clean`, 0 tracebacks, 0 HTTP 429s, 12 path-veto applications fired.

**Verify track (items 8–10):**
- **Cypher 6/6 PASS** against the clean rebuild — including the 5 historic flip rows (art. 148 → costos_deducciones_renta, Libro 4 Timbre → impuesto_timbre, Libro 1 T2 → patrimonio_fiscal_renta, Libro 1 T1 Cap 1 → ingresos_fiscales_renta, Libro 5 → procedimiento_tributario) plus the unchanged GMF row.
- **A/B v10**: 4-criteria scorecard 2/4 strict pass; **strict improvement vs v9** (+4 questions seeded, 0 regressed, contamination 4/4 clean, mean primary 1.53→1.93). Operator accepted on **qualitative** basis per `gate_9_threshold_decision.md §7` with binding conditions (don't lower thresholds; per-exception memos; gates evaluate independently).
- **SME 30Q at 30/30** post Alejandro's spot-review (`taxonomy_v2_sme_spot_review.md`) + applier (`artifacts/sme_pending/apply_sme_decisions.py`) + 3 surgical router fixes + the **generic LLM-deferral intervention** in `topic_router.py` (trigger-phrase deferral list + magnet-topic deferral set + `_should_defer_to_llm` helper). The intervention generalizes: future queries of the same shape resolve themselves without per-question patches.

**Re-flip executed 2026-04-25**: `LIA_TEMA_FIRST_RETRIEVAL` flipped `shadow → on` across all 5 mirror surfaces (`scripts/dev-launcher.mjs`, `docs/guide/orchestration.md`, `docs/guide/env_guide.md`, `CLAUDE.md`, `frontend/src/app/orchestration/shell.ts`). Env-matrix tag bumped to `v2026-04-25-temafirst-readdressed`. Change-log row landed verbatim per gate_9 §7. Same session: operator's "no off flags" directive applied — `LIA_EVIDENCE_COHERENCE_GATE=enforce`, `LIA_POLICY_CITATION_ALLOWLIST=enforce`, `LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE=enforce` (Python defaults + launcher), aligned with the existing `LIA_RERANKER_MODE=live` + `LIA_QUERY_DECOMPOSE=on` + `LIA_TEMA_FIRST_RETRIEVAL=on` + `LIA_LLM_POLISH_ENABLED=1` defaults.

**What got deferred to next_v4 (§1):** coherence-gate calibration diagnostic — measure whether the 11 `coherence_misaligned=True` questions concentrate in thin-corpus topics (fix = corpus expansion, free) or distribute across topics (fix = gate recalibration). Diagnose-before-intervene.

## Decision genealogy — what to look up where

| If you need... | Look at |
|---|---|
| The verbatim re-flip change-log row | `gate_9_threshold_decision.md §7` condition 1 |
| The 7 SME 30Q decisions (which letter, why) | `taxonomy_v2_sme_spot_review.md` + Alejandro's response captured in `next_v3 §13.11` (git history of `next_v3.md`) |
| The full taxonomy v2 spec (89 topics + mutex rules + scope_in/out) | `taxonomy_v2_sme_response.md` + `config/topic_taxonomy.json` |
| Why Cypher 6/6 was the gate 7 measurement | `next_v3 §8.2` (preserved in git) — 5 flip rows + 1 unchanged from the structural audit |
| Why we deprecated `retencion_en_la_fuente` | `next_v3 §13.10.7` item 3 (preserved in git) + `taxonomy_v2_sme_response.md` line 184 |
| The 3-conjunct retención model (q15 follow-up) | `artifacts/sme_pending/README.md` + `apply_sme_decisions.py`'s q15 follow-up message |
| The router LLM-deferral architecture | `src/lia_graph/topic_router.py` `_should_defer_to_llm` docstring + `docs/learnings/retrieval/router-llm-deferral-architecture.md` |
| The "operates not defines" meta-rule | `src/lia_graph/topic_router.py` `_build_classifier_prompt` (managed by applier marker `SME_META_RULE_OP_VS_DEF`) + `docs/learnings/retrieval/operates-not-defines-heuristic.md` |
| The six-gate lifecycle policy | `README.md` (this folder) — still active, governs every change |

## What's NOT in this archive (deliberately)

- **Blow-by-blow execution logs** (rebuild #1-#5 timing tables, every Cypher probe output, every A/B per-question delta) — preserved in git history. Pull `git show <commit>:docs/aa_next/next_v3.md` if needed.
- **Cycle-internal status indicators** (which step was "in-progress", which six-gate state each item was at) — irrelevant post-close.
- **Pre-rewrite versions of the SME packet** — superseded by Alejandro's reply and the applier; only the final state matters.

---

*Archived 2026-04-25. Next active doc is `next_v4.md`.*
