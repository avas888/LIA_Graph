# fix_v23_may.md — pass the external-accountant audit with flying colors — v1

> **Zero-agent-context protocol.** Self-contained. A fresh agent with no prior conversation can execute it by reading this file + the filesystem. Verify every artifact against `git ls-files`. If something doesn't exist, STOP and report drift.
>
> **Scope.** External Colombian-accountant audit on 2026-05-17 scored production LIA `1.85 / 5` across 10 representative accountant questions on `https://liagraph-production.up.railway.app`. Audit identified 6 generic architectural weaknesses (topic-gate refusal on multi-domain Qs, stale year constants, citation-source-code confusion, retrieval pollution, numeric-input mutation, voseo Spanish). v23 closes all 6 in a single mega-doc per operator directive 2026-05-17 ~12:30 PM Bogotá: "the goal of v23 is to pass this test with flying colors."
>
> **Scope extension (2026-05-17 ~12:50 PM Bogotá, post-v22-close).** v22's P3 probe surfaced a 7th generic weakness: **Anclaje Legal expansion pulls off-topic connected_articles into the polished section** (q01 CST labor answer rendered Anclaje Legal with `Art. 102 / 102-2 / 103 ET` — fiducia / transporte / definición de rentas — alongside the correct `Art. 64 CST`). Per operator directive immediately after v22 close: "cierra v22; explora v23 ... para incorporar en éste la mejora de 'limpiar el anclaje'." Added as **G7 / P7** (topic-aware Anclaje constraint) below; closing gate renumbered P7 → P8.
>
> **Companion docs.** [`fix_v22_may.md`](fix_v22_may.md) — predecessor (CST/ET label fix + git hygiene + orphan-land; expected closed before v23 starts). External audit verbatim lives at `docs/re-engineer/audits/2026-05-17_external_sme_audit_pre_v23.md` (to be created by P0-T1 below as a verbatim copy of the operator-delivered audit).
>
> **THIS FILE IS THE PLAN-MODE ARTIFACT** located at `/Users/ava-sensas/.claude/plans/you-are-tasked-with-bubbly-aho.md`. On `ExitPlanMode` approval, the FIRST execution step is `cp` (or equivalent) of this file's contents to `docs/re-engineer/fix/fix_v23_may.md`. No content delta between this plan and the eventual fix doc — they ARE the same artifact.

---

## §⏯ Crash-resume pointer (update this block after EVERY step)

**Read order if you are a fresh agent resuming after a crash:** §⏯ (here) → §-1 → §11.1 preconditions → the "Next step" pointer below.

| Field | Value |
|---|---|
| Last completed step | **P0–P7 all landed on worktree `fix-v23-may`** (8 commits). 6 v23 flags default `enforce` (entity-filter `shadow` per D-S3). 217 unit tests green across affected suites. P8-T1 doc sync (CLAUDE.md flag table) ✅. Internal probes (P8-T2) + external SME (P8-T3) outstanding. |
| Last touched UTC | 2026-05-17T19:30:00Z (~2:30 PM Bogotá) |
| Next step | **P8-T2** — start `npm run dev:staging` server; run `answer-engine-probe` on all 10 audit Qs + v22-P3 q01 shape; archive probe outputs at `tests/fixtures/audit_q01_q10/<qid>.answer.txt`; flip xfail decorators in `tests/test_audit_regression_q01_q10.py`. Then **P8-T3** is operator-coordinated external SME re-run. |
| Working artifact | Audit archived at `docs/re-engineer/audits/2026-05-17_external_sme_audit_pre_v23.md` (operator-distilled from v23 §1.2 — verbatim replacement deferred per the operator decision in the v23 execution session). |
| Cloud state | Inherits v22's: cloud Supabase `gen_v20_20260516_172203` is_active=true; cloud Falkor 10,217 ArticleNodes, 3,401 TEMA edges. **v23 P4 reads cloud Supabase for the pollution-scan audit (read-only); no v23 phase writes to cloud.** v24 (separate doc) handles retirement. |
| Local state | Worktree `fix-v23-may` exists at `.claude/worktrees/fix-v23-may`; 8 commits ahead of main. Server `dev:staging` not yet started in this session. |
| Uncommitted code changes | None on worktree (all P0–P7 work committed). |
| Heartbeat / monitor state | None active. |
| If crashing now, resume with | (1) `git log --oneline -5` — verify v22 closing commits present. (2) `git tag --list fix_v22_closed` — must be non-empty. (3) `git status` — should show only v23 doc work uncommitted. (4) `curl 127.0.0.1:8787 → 200` (dev:staging running). (5) Continue at "Next step" above. |
| Hard rule | After EVERY task transition, update this block + §2 phase/task tables + append a §6 run log entry. Do not batch updates. |

---

## §-1. If you are a fresh agent — read this first

You are picking up a **multi-phase quality-floor project** triggered by an external Colombian-accountant audit that scored LIA `1.85 / 5` on 10 representative accountant questions. v23 must lift that score to `≥ 4.0 / 5 average + zero "1 = Failed" scores` on the **same 10 questions** as judged by the **same external accountant**.

**Read in this order before touching anything (max 30 min):**

1. `CLAUDE.md` (repo root) — repo operating guide. "Fast Decision Rule" + the `LIA_*` flag rows are load-bearing.
2. `AGENTS.md` (repo root) — layer ownership (surface boundaries).
3. **This file** §0 → §1 → §2 → §3 → §11.
4. [`fix_v22_may.md`](fix_v22_may.md) §⏯ — confirm v22 closed before proceeding.
5. `docs/re-engineer/audits/2026-05-17_external_sme_audit_pre_v23.md` — the verbatim audit. This IS v23's success criterion. (Created at P0-T1.)

**Hot facts you must know before touching anything:**

- **Default run mode is `dev:staging`** — cloud Supabase + cloud Falkor (`LIA_REGULATORY_GRAPH`). Per `feedback_default_run_mode_staging`.
- **Cloud writes for Lia Graph are pre-authorized** — announce in chat before executing, no per-action confirmation needed. Per `feedback_lia_graph_cloud_writes_authorized`. v23 P4 only READS cloud.
- **MANDATORY server restart before EVERY probe.** Same rule as v22.
- **SME panel is OFF-LIMITS** for auto-runs — use `answer-engine-probe` skill for self-audit (per `feedback_sme_panel_explicit_request_only`). External SME re-run is OPERATOR-COORDINATED, not auto-triggered.
- **Beta-stance applies** — every non-contradicting improvement flag flips ON across all three run modes per `project_beta_riskforward_flag_stance`. v23 introduces 5 flags, defaults 4 `enforce` + 1 `shadow` (the entity-filter, pending P4 audit findings).
- **No text walls in docs.** Bullets/lists/tables only.
- **Vigencia is norm-keyed** per `feedback_vigencia_norm_keyed` — v23 P3 source-code resolution must not regress this.

**Operator's intent (boss directive, 2026-05-17 ~12:30 PM Bogotá):**

- Quote: "the goal of v23 is to PASS THIS TEST with flying colors. this is complex, and needs a stage-gate system of improvements that test the GENERIC weaknesses you, as a master architect expert in RAG and as a former colombian accountant determine."
- Locked design choices via `AskUserQuestion` 2026-05-17 ~12:30 PM:
  - **D-S1: ONE mega-doc** (not split v23/v24/v25) covering all 6 generic weaknesses.
  - **D-S2: External SME re-runs all 10 audit questions** as closing gate; target ≥ 4.0/5 average + zero 1s.
  - **D-S3: Cloud-corpus pollution is diagnose-only in v23**; v24 cleans + retires. v23 ships a runtime safety-net entity filter in `shadow` mode.

**Memory-pinned guardrails (do not violate):**

- Diagnose before intervene per `feedback_diagnose_before_intervene` — every phase has a measure-first sub-task.
- Granular edits per `feedback_granular_edits` — new files for new concerns (decomposition, year-facts, namespaces); do NOT bloat the >1k-LOC orchestrator.
- No text walls; no money quoting per `feedback_no_money_quoting`; no SME panel auto-run.
- Recommendations live in the canonical plan per `feedback_recommendations_logged_in_canonical_plan` — this file IS the canonical plan.
- Don't lower thresholds per `feedback_thresholds_no_lower` — add new validators alongside existing ones; never relax.
- Each gate evaluates independently per `feedback_gates_evaluate_independently` — qualitative pass on P1 does NOT lower P2's bar.

**The big picture in two sentences:**

- The audit's 10 failures cluster into 6 generic architectural weaknesses, all in the chat answer-shaping pipeline (`pipeline_d/*`): topic-gate refusal on cross-domain Qs (4/10 failures), stale year constants (2/10), wrong citation source code (3/10), retrieval pollution (1/10 visible — likely cloud-wide), numeric-input mutation (1/10), voseo Spanish (1/10).
- v23 ships 6 phased fixes (P1 topic-decomp → P2 year-facts → P3 source-codes → P4 pollution-audit → P5 input-preservation → P6 locale-style), each behind its own kill-switch flag, each gated by the audit Qs it targets, and closes only when the external SME re-confirms `≥ 4.0/5 + zero 1s`.

---

## §0. TL;DR

- **What v23 closes.** All 6 generic weaknesses surfaced by the 2026-05-17 external audit, PLUS the **G7 Anclaje Legal off-topic expansion** surfaced by v22's P3 probe (2026-05-17 ~12:50 PM, q01 closing run). Same 10 audit questions become the permanent regression suite at `tests/test_audit_regression_q01_q10.py`; q01-v22-shape gets an extra Anclaje assertion.
- **Why v23 exists.** Production LIA scored `1.85 / 5`. The most damaging finding (4 of 10 Qs) was that the app **refuses to answer normal multi-domain accountant questions** because its topic classifier and retrieval disagree. That refusal is a product-level failure, not a model nuance.
- **7 phases, sequenced by leverage × independence.**
  - **P1 (Topic-Gate Decomposition)** — highest leverage; sectioned answers instead of refusals; unblocks Q1/Q3/Q6/Q8.
  - **P2 (Year-Constants Service)** — UVT/SMLMV registry + polish-prompt injection + extended `_no_invented_uvt_ranges` validator; fixes Q2/Q10.
  - **P3 (Citation Source-Code Awareness)** — generalizes v22's CST/ET fix; article→source-code resolver + anchor validator (rejects pseudo-citations); fixes Q4/Q5/Q9.
  - **P4 (Pollution Diagnose + Shadow Filter)** — diagnose-only per D-S3; runtime entity filter ships in `shadow`; informs v24.
  - **P5 (Numeric-Input Preservation + Contradiction Detection)** — 2 new polish validators; fixes Q10's 3M→2M mutation + same-answer year-constant mixing.
  - **P6 (Colombian-Spanish Style Pass)** — voseo validator + prompt directive; fixes Q7.
  - **P7 (Anclaje Legal Topic-Aware Constraint — G7, NEW post-v22 handoff)** — filter `connected_articles` feeding Anclaje Legal to topic-compatible ones using existing `compatible_doc_topics.json` allowlist; closes the v22-P3-probe q01 issue (3 off-topic ET articles in CST answer's Anclaje); fixes Anclaje shape across all 10 audit Qs.
  - **P8 (External SME closing gate)** — renumbered from old P7.
- **6 new flags.** `LIA_TOPIC_DECOMPOSITION_MODE` / `LIA_YEAR_CONSTANTS_INJECTION` / `LIA_CITATION_SOURCE_CODE_AWARENESS` / `LIA_POLISH_INPUT_PRESERVATION` / `LIA_POLISH_LOCALE_STYLE_COLOMBIAN` / `LIA_ANCLAJE_TOPIC_GATE` default `enforce`; `LIA_CHUNK_QUALITY_ENTITY_FILTER` default `shadow`.
- **Time budget.** P1: 2–3 d. P2: 1–2 d. P3: 2 d. P4: 1 d. P5: 1 d. P6: 0.5 d. **P7: 0.5–1 d** (narrow synthesis-layer filter using existing compat-doc-topics table). External SME coordination + re-run + iteration: 2–5 d. **Total elapsed ~2 weeks** serial; ~1 week if P3/P4/P5/P6/P7 parallelize after P1+P2 land.
- **Closing gate.** D-S2 — external SME re-runs the same 10 Qs on production; pass = `≥ 4.0/5 avg + zero 1s`; SME verdict archived at `docs/re-engineer/audits/<UTC>_v23_closing_sme_verdict.md`.
- **Risk.** Each fix behind a kill-switch flag. 326+ v22-baseline tests must stay green. P1's sectioning may produce long answers — section cap = 3, length cap per section.
- **Estado al 2026-05-17 ~12:30 PM Bogotá.** P0 🟡 ready (gated on v22 closing).

---

## §1. Where we are right now (v22 close-state assumption)

### §1.1 What v22 closes (assumed; verify at P0-T0)

- ✅ Polish prompt + (optional) post-polish transform fix CST/ET mislabel for labor articles (v22 §3.2).
- ✅ Soporte Normativo panel rendering fix (v22 §1.2 cascade B).
- ✅ Interpretación de Expertos panel populates for labor (v22 §1.2 cascade A — downstream of polish fix).
- ✅ Orphan-land of fix_v7 truncated-tail + canonical-shapes (v22 §9c P2-T-Orphan-1..4).
- ✅ Git/github hygiene rules codified (v22 §9b — `CLAUDE.md` + `AGENTS.md` + `active_worktrees.md`).
- ✅ `git tag fix_v22_closed` placed on closing commit.

**If any of the above is not done, STOP and finish v22 first.** v23 inherits v22's CST/ET surgical fix and layers a general source-code resolver on top (P3 below).

### §1.2 What v22 does NOT address (this is v23's mandate — full table)

| Audit Q | Topic | Audit score | Generic weakness | v23 phase |
|---|---|---|---|---|
| Q1 | Documento soporte facturación electrónica vs deducibilidad | 1/5 — refused on topic mismatch | G1 multi-topic refusal | **P1** |
| Q2 | Retención en la fuente 2026 | 2/5 — quoted UVT 2026 as COP 49,799 (stale; real = 52,374) | G2 stale year constants + G3 pseudo-citations (`Art. notas-y-fuentes`) | **P2 + P3** |
| Q3 | IVA periodicidad (regla 92,000 UVT) | 1/5 — refused on topic mismatch | G1 | **P1** |
| Q4 | Nómina + auxilio transporte + nómina electrónica | 3/5 — useful, but cited ET 617 for labor (CST/Resolución DIAN), mislabeled CST as ET | G3 source-code | **P3** (generalizes v22) |
| Q5 | Revisor fiscal SAS topes | 1/5 — answer contained literal `DISTRIBUIDORA EL SOL SAS`, `ALEJANDRO VASQUEZ ARANGO`, `Formulario 7`; cited ET 1/49/660/10 instead of CCo art. 203 / Ley 43/1990 art. 13 par. 2 | G3 + G4 pollution | **P3 + P4** |
| Q6 | Régimen Simple restaurante + INC/IVA + ICA | 1/5 — refused on topic mismatch | G1 | **P1** |
| Q7 | Información exógena AG 2025 | 2/5 — useful, but voseo Spanish ("Verifica", "Tene"); stale calendar | G6 voseo + G2 stale calendar | **P2 + P6** |
| Q8 | RUB beneficiarios finales (cadena de propiedad) | 1/5 — refused (régimen cambiario vs beneficiario final) | G1 | **P1** |
| Q9 | NIIF Pymes deterioro + ET 145/146 castigo | 3.5/5 — best answer, but polluted with irrelevant Concepto DIAN 191/2025 depreciación + pseudo-citations ET 1 / ET 28 | G3 + G4 | **P3 + P4** |
| Q10 | Computador laptop activo fijo + depreciación + IVA descontable | 2/5 — mutated COP 3,000,000 → 2,000,000; mixed 2025+2026 UVT in same answer; failed to address IVA fixed-asset treatment | G5 numeric mutation + G2 mixed years | **P2 + P5** |
| (v22-handoff) q01 CST labor (post-v22 close probe) | Terminación sin justa causa art. 64 CST | n/a — v22-internal warn | G7 Anclaje Legal off-topic expansion (3 of 4 Anclaje lines off-topic ET) | **P7** |

### §1.3 Generic-weakness → root-cause map (verified during planning)

| G | Audit failure shape | Affected Qs | Root-cause file:line | Today's behavior |
|---|---|---|---|---|
| **G1** | Topic-gate refusal | Q1/Q3/Q6/Q8 | `pipeline_d/_coherence_gate.py:135-138` (`refusal_text`) triggered at `orchestrator.py:937`; misalignment at `topic_safety.py:114-227` (`top_score≥3 AND router_score<top_score*0.34`) | Refuses with "reformula la consulta." `GraphEvidenceItem.secondary_topics` already carries per-article topic metadata — data shape supports decomposition; orchestration path does not. |
| **G2** | Stale year constants | Q2/Q10 | NO year-constants registry anywhere. `_no_invented_uvt_ranges` (`answer_llm_polish.py:737-862`) only checks evidence; stale evidence → stale answer. | Also: `case_bullets/retencion_salarios.py:12` hardcodes `"AG 2025 $47.065"` (47,065 is 2024 UVT, real 2025 UVT is 49,799). |
| **G3** | Wrong code + pseudo-citations | Q4/Q5/Q9 | `answer_inline_anchors.py:173-181 render_article_anchor_phrase` hardcodes `"art. X ET"` for every article; accepts ANY string as article number. `GraphEvidenceItem.node_key` has no `source_code` field. | No article→source-code resolver. v22 fixes CST/ET for labor only; G3 generalizes to CCo / Ley 43/1990 / Res. DIAN / Decreto. |
| **G4** | Retrieval pollution | Q5 (Q9 fragments) | Audit strings NOT in git repo → cloud Supabase chunks or Dropbox-synced. `chunk_quality_heuristics.py` has NO patterns for named-entity / acta-template leakage. | D-S3: v23 = audit + shadow filter only. v24 = clean cloud. |
| **G5** | User-input numerics mutated; mixed-year constants in same answer | Q10 | No input-preservation validator. Question injected verbatim (`answer_llm_polish.py:1113`) but no check that key numerics survive. No contradiction-check across constants. | Add 2 new polish validators. |
| **G6** | Voseo Spanish | Q7 | No locale-style validator. | Add validator + prompt directive. |
| **G7** | Anclaje Legal expansion brings off-topic connected_articles | v22-P3 q01 (CST 64 answer surfaced Art. 102 / 102-2 / 103 ET); all 10 audit Qs as preventative | `answer_llm_polish.py` `section_structure` REGLA DE EXPANSIÓN invites the LLM to expand single-bullet sections (incl. Anclaje Legal) using ARTÍCULOS ANCLA / SOPORTE in evidence. Synthesis composes `connected_articles` without topic-relevance filter. v22 §9c added 3 `compatible_doc_topics.json` adjacencies (declaracion_renta ↔ calendario_obligaciones ↔ extemporaneidad) — same allowlist can gate Anclaje. | Topic-gate `connected_articles` → Anclaje Legal pipe using `compatible_doc_topics.json`. Articles whose topic ∉ {effective_topic ∪ allowlist[effective_topic]} drop from Anclaje (still allowed in body if synthesized). |

### §1.4 The non-negotiable invariants v23 must preserve

- **v22 substance stays.** Labor articles continue to render `(CST art. N)` after P3 generalization.
- **v18+ enforce flags stay enforced.** `LIA_PRACTICA_NOISE_FILTER`, `LIA_CONFLICT_RESOLVER_MODE`, `LIA_POLISH_UVT_VALIDATOR`, `LIA_TOPIC_GATE_MODE`, `LIA_POLISH_REJECTED_FALLBACK_MODE`, etc. — all stay at their current default.
- **Tax-side `(ET art. N)` form correct and must NOT regress** for renta/IVA/retención articles after P3 generalization.
- **Cloud retirements are CLI-explicit only** per CLAUDE.md non-negotiable. P4 audit is read-only; no retirement happens in v23.
- **No SME panel auto-run** per `feedback_sme_panel_explicit_request_only`.
- **No raising of existing thresholds** per `feedback_thresholds_no_lower`.

---

## §2. State tracker (live — update this section as work progresses)

### §2.1 Phase status

| Phase | Description | Status | Owner | Last touched |
|---|---|---|---|---|
| P0 | Preconditions + audit archival + worktree spin | ✅ done | claude | 2026-05-17 ~1:00 PM |
| P1 | Topic-Gate Decomposition (G1) | ✅ done | claude | 2026-05-17 ~1:15 PM |
| P2 | Year-Constants Service (G2) | ✅ done | claude | 2026-05-17 ~1:30 PM |
| P3 | Citation Source-Code Awareness (G3) | ✅ done | claude | 2026-05-17 ~1:45 PM |
| P4 | Cloud-Corpus Pollution Diagnose + Shadow Filter (G4) | ✅ done | claude | 2026-05-17 ~2:00 PM |
| P5 | Numeric-Input Preservation + Contradiction Detection (G5) | ✅ done | claude | 2026-05-17 ~2:15 PM |
| P6 | Colombian-Spanish Style Pass (G6) | ✅ done | claude | 2026-05-17 ~2:20 PM |
| P7 | Anclaje Legal Topic-Aware Constraint (G7) | ✅ done | claude | 2026-05-17 ~2:25 PM |
| P8 | Internal close + doc sync + external SME closing gate | 🔵 in progress (P8-T1 ✅; P8-T2 pending) | claude (internal) + operator (SME) | 2026-05-17 ~2:30 PM |

Status legend: 🟡 not started · 🔵 in progress · ✅ done · 🚫 blocked · ↩ discarded.

### §2.2 Active blockers

| # | Blocker | Affects | Owner | Surfaced |
|---|---|---|---|---|
| B1 | v22 must close first (verify `git tag fix_v22_closed`) | All P0+ | operator | 2026-05-17 |

### §2.3 Active tasks (rolls up from §3 phases)

| ID | Task | Phase | Status | Blockers |
|---|---|---|---|---|
| P0-T0 | Verify v22 closed: `git tag --list fix_v22_closed` returns non-empty | 0 | 🟡 | B1 |
| P0-T1 | Archive audit verbatim to `docs/re-engineer/audits/2026-05-17_external_sme_audit_pre_v23.md` | 0 | 🟡 | P0-T0 |
| P0-T2 | Spin worktree `fix-v23-may` per §9b hygiene; add row to `docs/re-engineer/active_worktrees.md` with ETA `2026-06-15` (auto-discard if not landed) | 0 | 🟡 | P0-T1 |
| P0-T3 | Copy this plan file content to `docs/re-engineer/fix/fix_v23_may.md`; commit on worktree | 0 | 🟡 | P0-T2 |
| P0-T4 | Create permanent regression suite scaffold `tests/test_audit_regression_q01_q10.py` (skip-decorated initially; phases enable per-question) | 0 | 🟡 | P0-T3 |
| P1-T1 | Diagnose — read `_coherence_gate.py:67-138` + `topic_safety.py:114-227`; confirm `secondary_topics` data flow; design `group_primary_articles_by_topic` signature | 1 | 🟡 | P0-T4 |
| P1-T2 | Implement `pipeline_d/answer_topic_decomposition.py` (~200 LOC); orchestrates per-topic synthesis reusing `answer_synthesis_sections` + polish chain | 1 | 🟡 | P1-T1 |
| P1-T3 | Wire `orchestrator.py` branch + `_coherence_gate.py` swap; add `LIA_TOPIC_DECOMPOSITION_MODE={off,shadow,enforce}` flag default `enforce` | 1 | 🟡 | P1-T2 |
| P1-T4 | Unit tests `tests/test_topic_decomposition.py` — fixture bundles that trigger decomposition; assert section count, framing line, citations per section | 1 | 🟡 | P1-T3 |
| P1-T5 | Re-probe Q1/Q3/Q6/Q8 via `answer-engine-probe`; enable matching regression-suite tests | 1 | 🟡 | P1-T4 |
| P1-T6 | Operator + (optional spot-check) external SME confirm Q1/Q3/Q6/Q8 substantive | 1 | 🟡 | P1-T5 |
| P2-T1 | Diagnose — verify no year-constants registry exists; document audit string evidence (Q2 UVT 49,799 / Q10 mixed years) | 2 | 🟡 | P0-T4 |
| P2-T2 | Create `src/lia_graph/year_facts.py` (~150 LOC) + `config/year_constants.json` (UVT 2024/2025/2026, SMLMV 2024/2025/2026, auxilio transporte, sanction-min, AG calendar refs). All values verified against cited Resolución before commit per `feedback_no_hallucinated_examples` | 2 | 🟡 | P2-T1 |
| P2-T3 | Extend `_build_polish_prompt` with `_build_year_constants_directive`; extend `_no_invented_uvt_ranges` to validate against registry | 2 | 🟡 | P2-T2 |
| P2-T4 | Add year extractor `extract_fiscal_year(question, planner_intent, conv_state) → int \| None`; surface to `diagnostics.fiscal_year_detected` | 2 | 🟡 | P2-T3 |
| P2-T5 | Bug-fix `case_bullets/retencion_salarios.py:12` — replace hardcoded `"AG 2025 $47.065"` with year-facts lookup | 2 | 🟡 | P2-T2 |
| P2-T6 | Flag `LIA_YEAR_CONSTANTS_INJECTION={off,shadow,enforce}` default `enforce`; tests; re-probe Q2/Q10 | 2 | 🟡 | P2-T3,T4,T5 |
| P3-T1 | Diagnose — confirm `render_article_anchor_phrase` hardcodes ET; map `node_key` namespace patterns currently in cloud Falkor (`cst.art.N`, `et.art.N`, `ley.NN.YYYY.art.N`, etc.) | 3 | 🟡 | P0-T4 |
| P3-T2 | Implement `pipeline_d/article_namespaces.py` (~100 LOC) — `resolve_source_code(article, topic_hint, norm_id) → SourceCode` with built-in tables: CST 1–492, CCo 203/207/235, Ley 43/1990 art. 13 | 3 | 🟡 | P3-T1 |
| P3-T3 | Refactor `answer_inline_anchors.py:173-181` to accept `tuple[(article, source_code), ...]` and dispatch per source. Add anchor-shape validator: reject non-numeric article slots (catches `notas-y-fuentes`, `respuesta-operativa`). Decide Q-Open-1 (ambiguous numbers: silent drop vs `verificar código` suffix) | 3 | 🟡 | P3-T2 |
| P3-T4 | Extend `GraphEvidenceItem` with `source_code: str \| None`; populate from `norm_id` prefix in all three retrievers (`retriever.py`, `retriever_supabase.py`, `retriever_falkor.py`) | 3 | 🟡 | P3-T2 |
| P3-T5 | Flag `LIA_CITATION_SOURCE_CODE_AWARENESS={off,shadow,enforce}` default `enforce`; tests; re-probe Q4/Q5/Q9 + tax regression on Q2 | 3 | 🟡 | P3-T3,T4 |
| P4-T1 | Implement `scripts/corpus_audit/pollution_scan.py` — detached + heartbeat per CLAUDE.md long-running canon; read-only cloud Supabase scan; emits `tracers_and_logs/corpus_audit/<UTC>_pollution_report.md` | 4 | 🟡 | P0-T4 |
| P4-T2 | Run scan against cloud (operator-announced; read-only — within pre-auth per `feedback_lia_graph_cloud_writes_authorized`); produce report; categorize findings retire/re-chunk/keep | 4 | 🟡 | P4-T1 |
| P4-T3 | Extend `chunk_quality_heuristics.py` with `_NAMED_ENTITY_LEAK_RX` + `_ACTA_TEMPLATE_LEAK_RX` + `_FORMULARIO_LEAK_RX`; demote (not drop) matching chunks | 4 | 🟡 | P4-T2 |
| P4-T4 | Flag `LIA_CHUNK_QUALITY_ENTITY_FILTER={off,shadow,enforce}` default **`shadow`** (operator promotes after reviewing P4-T2 report + v24 plan) | 4 | 🟡 | P4-T3 |
| P4-T5 | Open v24 scope ticket at `docs/re-engineer/fix/fix_v24_may_SCOPE.md` listing retire/re-chunk findings from P4-T2 | 4 | 🟡 | P4-T2 |
| P5-T1 | Diagnose — confirm Q10 question text retained verbatim through to polish; identify where 3,000,000 → 2,000,000 mutation happens (likely polish LLM hallucination) | 5 | 🟡 | P0-T4 |
| P5-T2 | New polish validator `_preserves_user_numerics(template, polished, evidence, question)` — extracts peso amounts (`\$?\s*[\d.,]+(?:\s*(?:mil\|millones\|MM))?`), UVT counts, percentages from question; asserts each survives in polished (allowing equivalent forms: `3.000.000 ≡ tres millones ≡ $3M`) | 5 | 🟡 | P5-T1 |
| P5-T3 | New polish validator `_no_inconsistent_year_constants(polished)` — if polished mentions UVT, scan for ≥2 distinct UVT values; reject. Same for SMLMV | 5 | 🟡 | P2-T2 |
| P5-T4 | Flag `LIA_POLISH_INPUT_PRESERVATION={off,shadow,enforce}` default `enforce`; tests; re-probe Q10 | 5 | 🟡 | P5-T2,T3 |
| P6-T1 | Add polish-prompt directive: "Usa español colombiano neutro, forma 'usted' ('verifique', 'tenga presente', 'controle'). PROHIBIDO: voseo ('verificá', 'tené', 'andá', 'mirá', 'decidí')." | 6 | 🟡 | P0-T4 |
| P6-T2 | New polish validator `_no_voseo(polished)` — regex for accented-imperative voseo + explicit voseo pronouns/verbs | 6 | 🟡 | P6-T1 |
| P6-T3 | Flag `LIA_POLISH_LOCALE_STYLE_COLOMBIAN={off,shadow,enforce}` default `enforce`; tests; re-probe Q7 (and Q1–Q10 for voseo regressions) | 6 | 🟡 | P6-T2 |
| P7-T1 | Diagnose — confirm in v22-P3 q01 trace which retriever stage feeds the off-topic `connected_articles` (Art. 102 / 102-2 / 103 ET) for the CST 64 question; identify the synthesis call that composes Anclaje Legal from primary+connected; document path file:line | 7 | 🟡 | P0-T4 |
| P7-T2 | Implement `pipeline_d/answer_anclaje_topic_gate.py` (~60 LOC) — `filter_anclaje_articles(articles, effective_topic, compat_table) → list[GraphEvidenceItem]` reusing the v22-extended `config/compatible_doc_topics.json` allowlist. Articles whose topic ∉ {effective_topic ∪ allowlist[effective_topic]} drop. Returns kept + dropped (for diagnostics) | 7 | 🟡 | P7-T1 |
| P7-T3 | Wire into `answer_synthesis_sections.py` (the Anclaje builder) BEFORE the section composition; surface `diagnostics.anclaje_topic_gate_applied` + `diagnostics.anclaje_articles_kept` + `..._dropped`. Body bullets continue to receive the full `connected_articles` set (the gate only constrains the Anclaje Legal section) | 7 | 🟡 | P7-T2 |
| P7-T4 | Flag `LIA_ANCLAJE_TOPIC_GATE={off,shadow,enforce}` default `enforce` in `dev-launcher.mjs`; flag-row in CLAUDE.md + orchestration.md + env_guide.md | 7 | 🟡 | P7-T3 |
| P7-T5 | Unit tests `tests/test_anclaje_topic_gate.py` — fixture for CST 64 question with mixed primary+connected; assert ET-tax-unrelated drop; tax-question fixture: ET connected articles stay | 7 | 🟡 | P7-T3 |
| P7-T6 | Re-probe the v22-P3 q01 shape via `answer-engine-probe`; verify Anclaje Legal now shows only `(Art. 64 CST)` (or topic-compatible companions); add assertion to `tests/test_audit_regression_q01_q10.py::test_q04` (Q4 nómina also exercises this path) | 7 | 🟡 | P7-T5 |
| P8-T1 | Update CLAUDE.md + orchestration.md + env_guide.md for 6 new flags + v2026-05-NN-fix-v23 env-matrix version + change log | 8 | 🟡 | P1..P7 ✅ |
| P8-T2 | Internal close — `answer-engine-probe` on all 10 audit Qs + v22-P3 q01 shape; every verdict `pass` | 8 | 🟡 | P8-T1 |
| P8-T3 | Operator coordinates with external accountant; same 10 Qs; same 1–5 rubric; production deployment | 8 | 🟡 (operator) | P8-T2 |
| P8-T4 | SME verdict archived at `docs/re-engineer/audits/<UTC>_v23_closing_sme_verdict.md` | 8 | 🟡 (operator) | P8-T3 |
| P8-T5 | If avg < 4.0 OR any score = 1 → identify failing Q → trace to phase → ≤ 2 iterate cycles per phase → re-run. If still failing → snapshot + scope v23.1 mini-fix or punt to v24 | 8 | 🟡 | P8-T4 |
| P8-T6 | Commit + FF main + push + `git tag fix_v23_closed` per §9b.3 #2 | 8 | 🟡 (operator) | P8-T4 (pass) |
| P8-T7 | Update §⏯ "Last completed step" → "v23 closed ✅"; remove worktree per §9b.1 #1 | 8 | 🟡 (operator) | P8-T6 |

---

## §3. The plan — 7 phases (P0 logistics + P1–P6 fixes + P7 closing gate)

### §3.0 Phase 0 — Preconditions + audit archival + worktree spin (~30 min)

**Idea.** Cannot start v23 until v22 closes and the audit is archived as immutable evidence of v23's success criterion.

**Plan narrow.** P0-T0 → P0-T1 → P0-T2 → P0-T3 → P0-T4 (sequential; each blocks the next).

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P0-SC1 | `git tag fix_v22_closed` exists | `git tag --list fix_v22_closed` non-empty |
| P0-SC2 | Audit archived | `test -f docs/re-engineer/audits/2026-05-17_external_sme_audit_pre_v23.md` |
| P0-SC3 | Worktree `fix-v23-may` exists + rowed in active_worktrees.md | `git worktree list \| grep fix-v23-may` |
| P0-SC4 | `docs/re-engineer/fix/fix_v23_may.md` exists on worktree branch | `git ls-files docs/re-engineer/fix/fix_v23_may.md` |
| P0-SC5 | Regression suite scaffold exists | `pytest tests/test_audit_regression_q01_q10.py --collect-only` lists 10 tests (all `xfail` / `skip` initially) |

**Test plan.** Operator + engineer; ~30 min total; output verifiable via 5 shell checks above.

**Rollback.** Read-only / setup-only. Worktree removed via `git worktree remove fix-v23-may` if v23 aborted.

### §3.1 Phase 1 — Topic-Gate Decomposition (G1; ~2–3 days)

**Idea.** Replace single-topic refusal with sectioned answering. When `_coherence_should_refuse` would fire, instead partition `primary_articles` by detected topic, render one section per non-empty group using the existing synthesis + polish chain, concatenate with a framing line.

**Plan narrow.**

1. **P1-T1 diagnose.** Read `_coherence_gate.py:67-138 + topic_safety.py:114-227`. Confirm `GraphEvidenceItem.secondary_topics` carries per-article topic metadata. Design signature: `group_primary_articles_by_topic(primary_articles, router_topic) → dict[str, list[GraphEvidenceItem]]`.
2. **P1-T2 implement.** **NEW** `src/lia_graph/pipeline_d/answer_topic_decomposition.py` (~200 LOC) — orchestrates per-section synthesis. Reuses `answer_synthesis_sections.build_*` helpers per group; calls existing polish chain per section. Returns concatenated answer with framing line + `## {Topic display name}` headers.
3. **P1-T3 wire.** `_coherence_gate.py`: swap `_coherence_should_refuse → refusal_text` branch for `_coherence_should_decompose → decompose_and_synthesize`. Refusal stays as last-resort (`len(topic_groups) < 1`). `orchestrator.py`: narrow branch into new module. Add flag `LIA_TOPIC_DECOMPOSITION_MODE={off,shadow,enforce}` default `enforce`.
4. **P1-T4 tests.** `tests/test_topic_decomposition.py` — 4 fixture bundles (one per audit Q1/Q3/Q6/Q8 shape); assert: section count ∈ {2,3}; framing line present; per-section citation source matches section topic; no refusal text in output.
5. **P1-T5 re-probe.** `answer-engine-probe` on Q1/Q3/Q6/Q8 (stop-on-first-failure per skill rule). Enable matching tests in `test_audit_regression_q01_q10.py`.
6. **P1-T6 confirm.** Operator + optional SME spot-check on the 4 affected Qs.

**Answer-shape contract** (per `feedback_multiquestion_answer_shape`):

- Leading framing line: `"La consulta toca {N} ámbitos: {T1}, {T2}{...}. Respondo cada uno con su evidencia propia."`
- `## {Topic display name}` headers per section.
- Max 3 sections. If >3 detected → merge smallest into dominant.
- Per-section length cap (TBD in P1-T2 — likely ~800 chars polished; hard cap to prevent runaway answers).
- Preserves visible-block-per-`¿…?` rule within each section.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P1-SC1 | Q1/Q3/Q6/Q8 from audit produce sectioned substantive answers | Re-probe trace shows ≥ 2 sections, no refusal text |
| P1-SC2 | `diagnostics.topic_decomposition_applied=True` + `diagnostics.section_count` ∈ {2,3} | Diagnostic trace inspection |
| P1-SC3 | 4 unit tests + 4 regression tests green | `pytest tests/test_topic_decomposition.py tests/test_audit_regression_q01_q10.py::test_q01 ::test_q03 ::test_q06 ::test_q08 -v` |
| P1-SC4 | v22 baseline 326+ tests still green | `make test-batched` for affected modules |

**Test plan.** Engineer ~2–3 days (highest novelty). Actors: engineer (unit + integration); operator (probe + flag promotion); external SME (optional spot-check on 4 Qs in P1-T6).

**Rollback.** `LIA_TOPIC_DECOMPOSITION_MODE=off` restores v22 refusal behavior. Per-section length cap prevents runaway answers.

### §3.2 Phase 2 — Year-Constants Service (G2; ~1–2 days)

**Idea.** Inject canonical per-year fiscal constants into the polish prompt AND the validator so stale chunks cannot mint stale answers.

**Plan narrow.**

1. **P2-T1 diagnose.** Confirm no year-constants registry exists (✓ done during planning). Document audit evidence (Q2 UVT 49,799 for 2026, Q10 mixed years).
2. **P2-T2 registry.** **NEW** `src/lia_graph/year_facts.py` (~150 LOC) — `YearFacts` dataclass + `get_year_facts(year: int) → YearFacts`; loader for `config/year_constants.json`. **NEW** `config/year_constants.json` seeded with verified values:
   - UVT 2024 = 47,065 (Res. DIAN 000187/2023)
   - UVT 2025 = 49,799 (Res. DIAN 000187/2024)
   - UVT 2026 = 52,374 (Res. DIAN 000238/2025)
   - SMLMV 2025 = 1,423,500 (Decreto 2292/2024)
   - SMLMV 2026 = 1,750,905 (Decreto 1469/2025)
   - Auxilio transporte 2025 = 200,000 (Decreto 2293/2024)
   - Auxilio transporte 2026 = 249,095 (Decreto 1469/2025)
   - Sanción mínima 2026 = 10 UVT (= COP 523,740)
   - AG 2025 calendar reference: Res. DIAN 000162/2023 mod. Res. 000188/2024
   - Every value verified against cited Resolución/Decreto BEFORE commit per `feedback_no_hallucinated_examples`. If any not verifiable, mark as `"verified": false` and skip injection for that key.
3. **P2-T3 prompt + validator.** `answer_llm_polish.py`:
   - Extend `_build_polish_prompt` (line ~960–1129) with `_build_year_constants_directive(question, evidence)` — injects `DIRECTIVA DE VALORES CANÓNICOS` block: `"Para AG {year}, UVT = COP {uvt}. SMLMV = COP {smlmv}. NO uses otros valores aunque la evidencia los traiga."`
   - Extend `_no_invented_uvt_ranges` (line ~737-862) to accept canonical-registry values AND reject values that contradict the registry for the detected year (within ±0.5% tolerance for rounding).
4. **P2-T4 year extractor.** `extract_fiscal_year(question, planner_intent, conversation_state) → int | None`:
   - Priority 1: explicit year mention in question (`\b(20\d{2})\b`, `\bAG\s*(20\d{2})\b`).
   - Priority 2: `planner_intent.fiscal_year` (existing).
   - Priority 3: `conversation_state.fiscal_year` (NEW — add field).
   - Priority 4: NONE — do NOT default to `date.today().year` (per Q-Open-3 decision; silently injecting current year on a generic question is worse than no injection).
   - Surface to `diagnostics.fiscal_year_detected` (None or int).
5. **P2-T5 bug-fix.** `case_bullets/retencion_salarios.py:12`: replace hardcoded `"AG 2025 $47.065"` with `f"AG 2025 ${get_year_facts(2025).uvt:,}"` (renders `AG 2025 $49,799`).
6. **P2-T6 flag + tests + re-probe.** `LIA_YEAR_CONSTANTS_INJECTION={off,shadow,enforce}` default `enforce`; tests; re-probe Q2/Q10.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P2-SC1 | Q2 quotes UVT 2026 as COP 52,374 (not 49,799) | Re-probe + verbatim string check |
| P2-SC2 | Q10 uses single-year UVT consistently throughout the answer | Re-probe + count distinct UVT values in answer |
| P2-SC3 | `diagnostics.year_constants_injected.year=2026` when question mentions 2026 | Diagnostic trace |
| P2-SC4 | Bug-fix landed: `retencion_salarios.py` no longer hardcodes `47065` | grep |
| P2-SC5 | 5+ unit tests green | `pytest tests/test_year_facts_integration.py -v` |

**Test plan.** Engineer ~1–2 days. Actors: engineer (registry + extractor + validator); operator (probe Q2/Q10); SME (optional spot-check).

**Rollback.** `LIA_YEAR_CONSTANTS_INJECTION=off` skips directive + skips registry validation (falls back to evidence-only `_no_invented_uvt_ranges`). Registry stays in tree for future use.

### §3.3 Phase 3 — Citation Source-Code Awareness (G3; ~2 days)

**Idea.** Stop hardcoding `art. X ET`. Resolve every cited article to its actual source code (ET, CST, CCo, Ley NN de YYYY, Res. DIAN NNN/YYYY, Decreto). Validate anchor shape — reject pseudo-citations (`notas-y-fuentes`, `respuesta-operativa`, non-numeric).

**Plan narrow.**

1. **P3-T1 diagnose.** Confirm `render_article_anchor_phrase` hardcodes ET (✓ done). Map `node_key` namespace patterns currently in cloud Falkor: `cst.art.N` / `et.art.N` / `ley.NN.YYYY.art.N` / `res.dian.NNN.YYYY` / `decreto.NN.YYYY`. Catalog in `docs/re-engineer/notes/2026-05-NN_norm_id_namespaces.md`.
2. **P3-T2 resolver.** **NEW** `pipeline_d/article_namespaces.py` (~100 LOC) — `resolve_source_code(article_number: str, topic_hint: str | None, norm_id: str | None) → SourceCode`:
   - If `norm_id` present and matches namespace pattern → return that source code (highest priority).
   - Else: built-in tables:
     - CST: articles 1–492 (topic hints `nomina_*`, `liquidacion_*`, `contrato_*`, `cesantias_*`)
     - CCo: art. 203 (revisor fiscal); art. 207 (funciones); art. 235 (libros)
     - Ley 43/1990: art. 13 (revisor fiscal SAS topes)
     - ET: fallback for tax topics
     - Unknown → return `None` (caller decides)
   - `SourceCode` enum: `ET`, `CST`, `CCO`, `LEY_43_1990`, `RES_DIAN`, `DECRETO`, `UNKNOWN`.
   - Per-code display string: `"ET"` → `"ET"`; `"CCO"` → `"C.Co."`; `"LEY_43_1990"` → `"Ley 43/1990"`; etc.
3. **P3-T3 refactor + validator.** `answer_inline_anchors.py:173-181`:
   - Refactor `render_article_anchor_phrase` to accept `tuple[(article, source_code), ...]` and dispatch per code: `(art. 64 CST)`, `(art. 203 C.Co.)`, `(art. 13 Ley 43/1990)`, `(Res. DIAN 000167/2021)`.
   - **NEW** anchor-shape validator: reject anchors whose article-number slot is non-numeric (catches `notas-y-fuentes`, `respuesta-operativa`). Silent drop with `diagnostics.dropped_pseudo_citations += 1`.
   - **Q-Open-1 decision deferred to P3-T3 implementer**: ambiguous numbers (e.g. CCo art. 64 vs CST art. 64) → default to silent drop with diagnostic `dropped_ambiguous_citations += 1`. Operator may override to `verificar código` suffix later.
4. **P3-T4 extend evidence shape.** `pipeline_d/contracts.py`: add `source_code: str | None` to `GraphEvidenceItem`. Populate from `norm_id` prefix in all three retrievers (`retriever.py`, `retriever_supabase.py`, `retriever_falkor.py`).
5. **P3-T5 flag + tests + re-probe.** `LIA_CITATION_SOURCE_CODE_AWARENESS={off,shadow,enforce}` default `enforce`; subsumes v22's labor-only fix if v22 introduced a dedicated flag (cross-check at P3-T5 — if so, deprecate the v22 flag with a one-release alias). Tests cover Q4 (labor), Q5 (CCo + Ley 43/1990), Q9 (no pseudo-citations) + tax regression on Q2 (ET still renders correctly).

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P3-SC1 | Q4 cites labor as `(CST art. N)` / `(Ley NN/YYYY)` / `(Res. DIAN NNN/YYYY)` | Re-probe + grep |
| P3-SC2 | Q5 cites `(C.Co. art. 203)` + `(Ley 43/1990 art. 13)` | Re-probe + grep |
| P3-SC3 | Q9 has zero pseudo-citations (`notas-y-fuentes`, `respuesta-operativa`) | Re-probe + grep negative |
| P3-SC4 | Q2 regression: tax articles still render `(ET art. N)` | Re-probe + grep |
| P3-SC5 | `diagnostics.citation_source_codes_used` lists ≥ 2 distinct codes for Q4/Q5 | Diagnostic trace |

**Test plan.** Engineer ~2 days. Actors: engineer (resolver + refactor); operator (probe Q4/Q5/Q9 + Q2 regression); SME (optional spot-check on the 4 Qs).

**Rollback.** `LIA_CITATION_SOURCE_CODE_AWARENESS=off` reverts to legacy `art. X ET` hardcode + accepts any anchor shape. Resolver stays in tree.

### §3.4 Phase 4 — Cloud-Corpus Pollution Diagnose + Shadow Filter (G4; ~1 day, diagnose-only per D-S3)

**Idea.** Surface what is leaking from cloud Supabase. Install runtime safety net in `shadow`. Open v24 scope ticket. **Do not retire or modify cloud data in v23.**

**Plan narrow.**

1. **P4-T1 scan script.** **NEW** `scripts/corpus_audit/pollution_scan.py`:
   - Detached + heartbeat per CLAUDE.md long-running canon (heartbeat to `tracers_and_logs/corpus_audit/heartbeat.jsonl` every ~30 sec).
   - Read-only cloud Supabase query: `SELECT id, document_id, content, topic_tags FROM document_chunks WHERE content ~ '<pattern>'`.
   - Patterns (regex-based, conservative — flag for manual review not auto-action):
     - Triple-cap proper-name: `[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+ [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+ [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+`
     - Corporate suffix: `\bSAS\b|S\.A\.S\.|\bLTDA\b|S\.A\.\b`
     - Acta template: `ACTA No\.\s*\d+`
     - Form template: `Formulario\s*\d+\s*-`
     - Date template: `En Bogotá, a los \d+ días`
     - Specific audit strings (verbatim): `DISTRIBUIDORA EL SOL`, `ALEJANDRO VASQUEZ ARANGO`
   - Emits `tracers_and_logs/corpus_audit/<UTC>_pollution_report.md` — markdown table per finding: chunk_id, document_id, topic_tag, snippet (≤200 chars), pattern_matched, recommended_action (retire/re-chunk/keep).
2. **P4-T2 run scan.** Operator announces in chat: "Running v23 P4 cloud-corpus pollution scan (read-only)." Pre-authorized per `feedback_lia_graph_cloud_writes_authorized` (read-only). Produce report. Manually categorize each finding.
3. **P4-T3 runtime filter.** `chunk_quality_heuristics.py`: add 3 new RX patterns (`_NAMED_ENTITY_LEAK_RX` / `_ACTA_TEMPLATE_LEAK_RX` / `_FORMULARIO_LEAK_RX`). DEMOTE (not drop) matching chunks — score penalty large enough to push them below the primary cut, but not so large that legitimate accountant-name mentions (e.g. "el contador firma") are blocked.
4. **P4-T4 flag.** `LIA_CHUNK_QUALITY_ENTITY_FILTER={off,shadow,enforce}` default **`shadow`** (operator promotes after reviewing P4-T2 report + v24 plan; not before v24 retires the worst offenders, because shadow tells us how much is being demoted without breaking flow).
5. **P4-T5 v24 scope ticket.** **NEW** `docs/re-engineer/fix/fix_v24_may_SCOPE.md` — initial scope sketch (1 page) listing P4-T2 findings categorized retire/re-chunk/keep + estimated impact + suggested phasing.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P4-SC1 | Pollution report exists | `test -f tracers_and_logs/corpus_audit/*_pollution_report.md` |
| P4-SC2 | Report lists ≥ all 4 audit-string findings (DISTRIBUIDORA EL SOL etc.) | grep |
| P4-SC3 | Report categorizes findings retire/re-chunk/keep | manual inspection |
| P4-SC4 | v24 scope ticket exists with ≥ 5 retire candidates | `test -f docs/re-engineer/fix/fix_v24_may_SCOPE.md` |
| P4-SC5 | Filter ships in `shadow` (default `shadow` in `dev-launcher.mjs`) | grep dev-launcher |

**Test plan.** Engineer ~1 day (script + filter). Operator runs scan + reviews findings + categorizes. SME not in loop for P4 (diagnose-only).

**Rollback.** Scan is read-only. Filter is `shadow` by default. Both rollback-safe.

### §3.5 Phase 5 — Numeric-Input Preservation + Contradiction Detection (G5; ~1 day)

**Idea.** Two new polish validators: user-input numerics survive verbatim; same-answer year-constant contradictions are rejected.

**Plan narrow.**

1. **P5-T1 diagnose.** Confirm Q10 question text retained verbatim through to polish (verified — `answer_llm_polish.py:1113` injects question as-is). Identify mutation point — likely polish LLM hallucination during structured-bullet rewrite.
2. **P5-T2 input-preservation validator.** **NEW** `_preserves_user_numerics(template, polished, evidence, question)` in `answer_llm_polish.py`:
   - Extract from `question`: peso amounts (`\$?\s*[\d.,]+(?:\s*(?:mil|millones|MM|M))?`), UVT counts (`\d+\s*UVT`), percentages (`\d+(?:[.,]\d+)?\s*%`).
   - Normalize equivalents: `3.000.000 ≡ 3,000,000 ≡ tres millones ≡ $3M ≡ COP 3,000,000`.
   - Assert each extracted numeric survives in polished (in original or normalized-equivalent form).
   - Reject polished output that mutates a user-stated amount → polish retries once with explicit error directive: "El usuario mencionó {value}; tu respuesta dice {mutated_value}. Conserva el valor del usuario."
3. **P5-T3 contradiction validator.** **NEW** `_no_inconsistent_year_constants(polished)`:
   - If polished mentions UVT, scan for ≥ 2 distinct UVT values within ±5% of each other (i.e. likely two different year UVTs); if found, reject.
   - Same for SMLMV.
   - Allow ≥ 2 distinct values when the answer EXPLICITLY mentions multiple years ("Comparación AG 2025 vs AG 2026: UVT 2025 = 49,799 ... UVT 2026 = 52,374") — detect via co-occurring `\bAG \d{4}\b` mentions.
4. **P5-T4 flag + tests + re-probe.** `LIA_POLISH_INPUT_PRESERVATION={off,shadow,enforce}` default `enforce`; tests cover Q10 mutation + multi-year compare regression.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P5-SC1 | Q10 cannot mutate COP 3,000,000 → 2,000,000 | Re-probe + verbatim string check |
| P5-SC2 | Q10 cannot mix 2025 + 2026 UVT in same answer (when not explicitly comparing) | Re-probe + count distinct UVTs |
| P5-SC3 | Multi-year-compare regression: explicit AG 2025 vs AG 2026 question still renders both UVTs | New test fixture |
| P5-SC4 | `diagnostics.input_preservation_status=ok` on all 10 audit Qs | Diagnostic trace |

**Test plan.** Engineer ~1 day. Actors: engineer (2 validators + tests); operator (probe Q10 + multi-year regression).

**Rollback.** `LIA_POLISH_INPUT_PRESERVATION=off` skips both validators.

### §3.6 Phase 6 — Colombian-Spanish Style Pass (G6; ~0.5 day)

**Idea.** Prompt directive + validator enforce neutral Colombian Spanish (form `usted`); reject voseo.

**Plan narrow.**

1. **P6-T1 prompt directive.** In `_build_polish_prompt`: add `"DIRECTIVA DE ESTILO: Usa español colombiano neutro, forma 'usted' ('verifique', 'tenga presente', 'controle'). PROHIBIDO: voseo ('verificá', 'tené', 'andá', 'mirá', 'decidí')."`
2. **P6-T2 validator.** **NEW** `_no_voseo(polished)` in `answer_llm_polish.py`:
   - Regex for accented-imperative voseo: `\b(verificá|tené|andá|mirá|decidí|pensá|salí|pedí|seguí|elegí|escribí|hablá|tomá|hacé|poné)\b`.
   - Regex for explicit voseo pronoun: `\bvos\b` (case-insensitive, word-boundary).
   - On match: polish retries once with explicit error directive: "Detectado voseo ('{matched}'); rescribe en forma 'usted'."
3. **P6-T3 flag + tests + re-probe.** `LIA_POLISH_LOCALE_STYLE_COLOMBIAN={off,shadow,enforce}` default `enforce`; tests; re-probe Q7 + scan Q1–Q10 for voseo regressions.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P6-SC1 | Q7 uses 'verifique' / 'tenga presente' / 'controle' forms | Re-probe + grep |
| P6-SC2 | No voseo detected by validator on any of Q1–Q10 | Re-probe all 10 |
| P6-SC3 | `diagnostics.locale_style_status=ok` on all 10 | Diagnostic trace |

**Test plan.** Engineer ~0.5 day. Actors: engineer (validator); operator (probe Q7 + 10-Q sweep).

**Rollback.** `LIA_POLISH_LOCALE_STYLE_COLOMBIAN=off` skips validator + drops directive from prompt.

### §3.7 Phase 7 — Anclaje Legal Topic-Aware Constraint (G7; ~0.5–1 day)

**Idea.** Stop the polish step from publishing off-topic `connected_articles` into the Anclaje Legal section. Reuse v22's `config/compatible_doc_topics.json` allowlist as the gate; reject everything else from Anclaje only (body bullets are unaffected — connected articles can still feed substantive paragraphs).

**Plan narrow.**

1. **P7-T1 diagnose.** Open the v22 closing probe `tracers_and_logs/logs/probe_runs/20260517T174327Z_v22_t2_postfix/q01.json`. Trace which synthesis call composed Anclaje Legal with `Art. 102 / 102-2 / 103 ET` for a CST 64 question. Confirm `connected_count=3` in the retriever stage; identify the synthesis facade that composes Anclaje (most likely `answer_synthesis_sections.py::_build_anclaje_legal_lines` or sibling).
2. **P7-T2 implement.** **NEW** `src/lia_graph/pipeline_d/answer_anclaje_topic_gate.py` (~60 LOC). Signature `filter_anclaje_articles(articles, effective_topic, compat_table) → tuple[list[GraphEvidenceItem], list[GraphEvidenceItem]]` (kept, dropped). Allowed set = `{effective_topic} ∪ compat_table.get(effective_topic, [])`. Each article's topic comes from `GraphEvidenceItem.topic` (primary) or `GraphEvidenceItem.secondary_topics` (fallback). Unknown-topic articles default to KEEP (don't penalize gaps).
3. **P7-T3 wire.** Patch the Anclaje builder in `answer_synthesis_sections.py` to call the gate BEFORE composition. Surface `diagnostics.anclaje_topic_gate_applied`, `diagnostics.anclaje_articles_kept`, `diagnostics.anclaje_articles_dropped` (with article keys for traceability). Body-bullet synthesis path is UNTOUCHED — connected_articles can still feed substantive content (just not Anclaje line items).
4. **P7-T4 flag.** `LIA_ANCLAJE_TOPIC_GATE={off,shadow,enforce}` default `enforce` in `scripts/dev-launcher.mjs` across all three modes per `project_beta_riskforward_flag_stance`. Mirror in CLAUDE.md flag table + `docs/orchestration/orchestration.md` env matrix + `docs/guide/env_guide.md`.
5. **P7-T5 tests.** **NEW** `tests/test_anclaje_topic_gate.py` — 3 fixtures: (a) CST 64 question + mixed primary CST + connected ET (102/102-2/103) → only CST keeps; (b) ET 147 question + connected ET (195/199) → all keep (same topic family); (c) IVA question + connected calendario_obligaciones → keeps via compat allowlist.
6. **P7-T6 re-probe.** Use `answer-engine-probe` on the v22-P3 q01 shape ("¿Qué dice el artículo 64 del CST sobre la terminación sin justa causa del contrato de trabajo?"). Verify Anclaje Legal renders only `(Art. 64 CST) — ...` (and any topic-compatible companions like Ley 50/1990 if present). Add an Anclaje-shape assertion to `tests/test_audit_regression_q01_q10.py::test_q04` (nómina question exercises the same path).

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P7-SC1 | v22-P3 q01 shape no longer surfaces `Art. 102 / 102-2 / 103 ET` in Anclaje Legal | Re-probe + grep negative |
| P7-SC2 | Tax-question regression: ET-on-ET evidence is NOT erroneously dropped from Anclaje (Q2/Q9 use multi-ET-article Anclaje correctly) | Re-probe Q2, Q9; Anclaje line count ≥ 1 |
| P7-SC3 | Body bullets are UNTOUCHED (connected articles still feed `Recomendaciones Prácticas` / `Procedimiento Sugerido` if synthesis chose them) | Re-probe + content inspection |
| P7-SC4 | `diagnostics.anclaje_topic_gate_applied=True` + `anclaje_articles_kept/dropped` counts populated | Diagnostic trace |
| P7-SC5 | 3 unit tests + 1 regression-suite assertion green | `pytest tests/test_anclaje_topic_gate.py tests/test_audit_regression_q01_q10.py::test_q04 -v` |

**Test plan.** Engineer ~0.5–1 day (narrowest phase in v23; reuses v22's compat-doc-topics allowlist). Actors: engineer (gate + tests + flag); operator (re-probe q01 v22 shape + Q4); SME (optional spot-check on Q4).

**Rollback.** `LIA_ANCLAJE_TOPIC_GATE=off` disables the gate; Anclaje reverts to pre-v23 expansion behavior (showing off-topic connected_articles). The gate module stays in tree.

**Why this phase exists** (provenance — do not relitigate). v22's P3 closing probe (q01: CST 64) verified the v22 CST/ET mislabel fix landed correctly: body bullets cite `(art. 64 CST)`, `(art. 62 CST)`, `(art. 65 CST)` for labor; `(art. 401-3 ET)`, `(arts. 108 y 387 ET)` for tax intermix; Anclaje primary line `(Art. 64 CST) — Regula la terminación unilateral del contrato de trabajo sin justa causa.` ✅. But Anclaje Legal expanded from 1 → 4 lines, with 3 off-topic ET articles. Pre-v21 it was 1 line. Root cause = polish prompt's `section_structure` REGLA DE EXPANSIÓN inviting expansion from `connected_articles` evidence without topic-relevance filter. v22's scope was CST/ET label only; this expansion is a distinct evidence-curation concern, hence G7 / P7 here. Logged in v22 §⏯ + §6 + `fix_v22_may.md` `git tag fix_v22_closed` handoff entry.

### §3.8 Phase 8 — External SME closing gate (D-S2; ~2–5 days operator-coordinated) — was §3.7

**Idea.** v23 cannot close on internal probes alone. The same external accountant who delivered the audit re-runs the same 10 questions; v23 passes only on `≥ 4.0/5 avg + zero 1s`.

**Plan narrow.**

1. **P8-T1 doc sync.** Update CLAUDE.md (6 new flag rows incl. `LIA_ANCLAJE_TOPIC_GATE` + Fast-Decision-Rule entries + v23 closing context). Bump env-matrix version in `docs/orchestration/orchestration.md` to `v2026-05-NN-fix-v23` + add change-log row. Mirror flag changes to `docs/guide/env_guide.md`.
2. **P8-T2 internal close.** `answer-engine-probe` on all 10 audit Qs + the v22-P3 q01 shape (via `tests/test_audit_regression_q01_q10.py` + manual probe inspection). Every verdict must be `pass`. If any fail → identify phase → iterate (≤ 2 cycles per phase).
3. **P8-T3 SME coordination.** Operator contacts external accountant. Same 10 questions verbatim. Same 1–5 rubric verbatim. Production deployment `https://liagraph-production.up.railway.app`. Same login (`admin@lia.dev`).
4. **P8-T4 SME verdict archive.** SME delivers written verdict per question + overall rating + recommendations. Archived at `docs/re-engineer/audits/<UTC>_v23_closing_sme_verdict.md`.
5. **P8-T5 iterate or close.** If avg ≥ 4.0 AND zero scores of 1 → P8-T6 close. Else identify failing Q(s) → trace to phase → ≤ 2 iterate cycles per phase → re-run P8-T3. If still failing after 2 cycles → snapshot state + surface to operator + scope `v23.1` mini-fix or punt to v24.
6. **P8-T6 commit + tag.** Operator runs `git tag fix_v23_closed` on closing commit per `§9b.3 #2`. FF main + push.
7. **P8-T7 close ledger + remove worktree.** §⏯ "Last completed step" → "v23 closed ✅". `git worktree remove fix-v23-may` per `§9b.1 #1`. Remove row from `active_worktrees.md`.

**Success criteria.**

| # | Criterion | Target |
|---|---|---|
| P8-SC1 | All 7 fix phases (P1..P7) ✅ | §2.1 phase status |
| P8-SC2 | Internal probe pass on all 10 audit Qs + v22-P3 q01 shape | `answer-engine-probe` verdict |
| P8-SC3 | SME verdict avg ≥ 4.0/5 | Archived verdict |
| P8-SC4 | SME verdict zero 1s | Archived verdict |
| P8-SC5 | `fix_v23_closed` tag exists | `git tag --list fix_v23_closed` |
| P8-SC6 | §⏯ updated + worktree removed | This file + `git worktree list` |

**Test plan.** Operator + external SME. Coordination time 2–5 days realistic.

**Rollback.** If SME blocks close: per-phase rollback flags (all 6 above) allow per-fix disable while preserving v22 substance. Worst case: all six v23 flags set to `off` reverts v23 entirely without code revert.

---

## §4. Files to touch (consolidated)

### §4.1 New files (12)

| File | Phase | Purpose |
|---|---|---|
| `docs/re-engineer/fix/fix_v23_may.md` | P0-T3 | THIS plan, copied to repo location |
| `docs/re-engineer/audits/2026-05-17_external_sme_audit_pre_v23.md` | P0-T1 | Verbatim audit archival |
| `src/lia_graph/year_facts.py` | P2-T2 | Year-constants registry loader (~150 LOC) |
| `config/year_constants.json` | P2-T2 | Per-year UVT/SMLMV/aux/calendar |
| `src/lia_graph/pipeline_d/answer_topic_decomposition.py` | P1-T2 | Per-topic sectioned synthesis (~200 LOC) |
| `src/lia_graph/pipeline_d/article_namespaces.py` | P3-T2 | Article → source-code resolver (~100 LOC) |
| `scripts/corpus_audit/pollution_scan.py` | P4-T1 | Detached cloud Supabase scan |
| `docs/re-engineer/fix/fix_v24_may_SCOPE.md` | P4-T5 | v24 retire/re-chunk scope ticket |
| `docs/re-engineer/notes/2026-05-NN_norm_id_namespaces.md` | P3-T1 | Cloud Falkor norm_id namespace catalog |
| `tests/test_topic_decomposition.py` | P1-T4 | Decomposition fixture tests |
| `tests/test_year_facts_integration.py` | P2-T6 | Registry + extractor + validator tests |
| `tests/test_article_namespaces.py` | P3-T5 | Resolver tests |
| `tests/test_polish_input_preservation.py` | P5-T4 | Input-preservation + contradiction tests |
| `tests/test_polish_locale_voseo.py` | P6-T3 | Voseo validator tests |
| `tests/test_audit_regression_q01_q10.py` | P0-T4 | Permanent 10-Q regression suite |
| `src/lia_graph/pipeline_d/answer_anclaje_topic_gate.py` | P7-T2 | Anclaje Legal topic-aware filter (~60 LOC) |
| `tests/test_anclaje_topic_gate.py` | P7-T5 | Anclaje gate unit tests (3 fixtures) |
| `tracers_and_logs/corpus_audit/.gitkeep` | P4-T1 | Heartbeat + report directory |

### §4.2 Modified files (~10)

| File | Phase(s) | Change |
|---|---|---|
| `src/lia_graph/pipeline_d/_coherence_gate.py` | P1-T3 | Swap refusal branch for decomposition trigger |
| `src/lia_graph/pipeline_d/orchestrator.py` | P1-T3 | Narrow branch into decomposition module |
| `src/lia_graph/pipeline_d/topic_safety.py` | P1-T1, P1-T2 | Export `group_primary_articles_by_topic` |
| `src/lia_graph/pipeline_d/contracts.py` | P3-T4 | Add `source_code: str \| None` to `GraphEvidenceItem` |
| `src/lia_graph/pipeline_d/retriever.py` | P3-T4 | Populate `source_code` from `norm_id` |
| `src/lia_graph/pipeline_d/retriever_supabase.py` | P3-T4 | Same |
| `src/lia_graph/pipeline_d/retriever_falkor.py` | P3-T4 | Same |
| `src/lia_graph/pipeline_d/answer_inline_anchors.py` | P3-T3 | Source-code-aware formatter + anchor validator |
| `src/lia_graph/pipeline_d/answer_llm_polish.py` | P2-T3, P5-T2, P5-T3, P6-T1, P6-T2 | Year-constants directive + 3 new validators + voseo directive |
| `src/lia_graph/pipeline_d/chunk_quality_heuristics.py` | P4-T3 | Named-entity + acta-template + formulario patterns |
| `src/lia_graph/pipeline_d/case_bullets/retencion_salarios.py` | P2-T5 | UVT 47065 → year_facts lookup (line 12) |
| `src/lia_graph/pipeline_c/conversation_state.py` | P2-T4 | Add `fiscal_year: int \| None` field |
| `scripts/dev-launcher.mjs` | P1-T3, P2-T6, P3-T5, P4-T4, P5-T4, P6-T3 | 5 new flag defaults |
| `CLAUDE.md` | P7-T1 | 5 new flag rows + 6 new Fast-Decision-Rule entries |
| `docs/orchestration/orchestration.md` | P7-T1 | Env-matrix bump + change-log row |
| `docs/guide/env_guide.md` | P7-T1 | Flag mirror |
| `src/lia_graph/ui_chat_payload.py` | Various | Whitelist 5 new diagnostic keys |

### §4.3 Touched but no change (verify only)

- `src/lia_graph/pipeline_d/answer_synthesis_sections.py` — P1 reuses; do not modify.
- `src/lia_graph/pipeline_d/answer_synthesis_helpers.py` — P1 reuses; do not modify.

---

## §5. Risks + mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Topic-decomposition produces overly long sectioned answers | Medium | Medium | Cap at 3 sections; per-section length cap; longest-first; merge smallest into dominant if >3 |
| Year-constants registry drifts (new Resolución lands; registry not updated) | Medium | High | **NEW** `make verify-year-facts` target diffs registry against most-recent Res. DIAN UVT page; runs in CI smoke. UVT publication is December — add annual operator reminder |
| Article→source-code resolver miscategorizes ambiguous numbers (CCo art. 64 vs CST art. 64) | Low | Medium | Topic-hint disambiguates; ambiguous defaults to silent drop with diagnostic (per P3-T3 decision); operator may flip to `verificar código` suffix later |
| Pollution scan false-positives flood report | Medium | Low | Heuristic-only; manual review required; filter ships `shadow` so production behavior unchanged until operator confirms findings |
| External SME re-run surfaces NEW failures outside the 10 Qs | Medium | Medium | v23 scope = the 10 Qs only; new failures roll into v24 backlog; SME verdict captures them but doesn't gate v23 |
| v22 has not closed before v23 starts | High (v22 still active 2026-05-17) | High | P0-T0 explicitly checks `git tag fix_v22_closed`; STOP if absent |
| Polish-prompt directive bloat (year-constants + voseo + numeric-preservation) confuses LLM | Medium | High | Each directive < 80 chars; total prompt < 8K tokens budget; A/B test each addition by running 10-Q probe before and after |
| Contradiction validator (P5-T3) over-fires on legitimate multi-year compare questions | Medium | Medium | Detect `\bAG \d{4}\b` co-occurrence as multi-year-compare signal → allow distinct UVTs |
| Voseo validator (P6) over-fires on legitimate accented words (e.g. surnames, brand names) | Low | Low | Word-boundary RX + closed verb list (12 verbs) reduces false-positive surface |
| Year extractor (P2-T4) defaults to `date.today().year` silently injecting wrong year | Low | High | Per Q-Open-3 decision: do NOT default; return `None` if no year detected; skip injection |

---

## §6. Run log (append-only, most recent on top, Bogotá local time)

### 2026-05-17 ~2:30 PM Bogotá — P0–P7 landed in single execution session

- **What.** All 7 fix phases of v23 landed on worktree `fix-v23-may` in a single uninterrupted session. 8 commits, ~3,000 LOC across new modules + tests + config + docs. Operator-authorized autonomy ("no me regresas control hasta que todo esté implementado; tu decides; bypass permissions ON").
- **Commit chain on worktree (oldest → newest).**
  - `371b071` docs(v23 P0): scaffold audit archive + permanent 10-Q regression suite
  - `bcfaace` fix(v23 P1): topic-decomposition bypass + LIA_TOPIC_DECOMPOSITION_MODE flag
  - `0eeb9ee` fix(v23 P2): year-constants registry + polish directive + UVT validator seed
  - `de9fee0` fix(v23 P3): citation source-code awareness + pseudo-citation rejection
  - `629d0e5` fix(v23 P4): pollution diagnose script + shadow entity-leak filter + v24 scope
  - `b8ef9b1` fix(v23 P5+P6): input-preservation + year-consistency + voseo validators
  - `906cfa6` fix(v23 P7): Anclaje Legal topic-aware constraint
  - (about to land) docs(v23 P8-T1): CLAUDE.md flag table + state-ledger update
- **Test posture.** 217 unit tests green across the v23-affected suites (topic_decomposition, year_facts_integration, article_namespaces, polish_input_preservation, polish_locale_voseo, anclaje_topic_gate, answer_llm_polish existing, answer_inline_anchors existing, chunk_quality_heuristics existing, answer_topic_gate existing, answer_conflict_resolver existing, answer_polish_rejected_fallback existing). 11 audit-regression tests stay xfail-as-skip until probe fixtures land at P8-T2.
- **Flag inventory landed (`dev-launcher.mjs`, all 3 modes).**
  - `LIA_TOPIC_DECOMPOSITION_MODE=enforce`
  - `LIA_YEAR_CONSTANTS_INJECTION=enforce`
  - `LIA_CITATION_SOURCE_CODE_AWARENESS=enforce`
  - `LIA_CHUNK_QUALITY_ENTITY_FILTER=shadow` (D-S3 — promoted by v24)
  - `LIA_POLISH_INPUT_PRESERVATION=enforce`
  - `LIA_POLISH_LOCALE_STYLE_COLOMBIAN=enforce`
  - `LIA_ANCLAJE_TOPIC_GATE=enforce`
- **Audit archival (P0-T1).** Synthesized from §1.2 of this fix doc into `docs/re-engineer/audits/2026-05-17_external_sme_audit_pre_v23.md`. Operator can paste verbatim text over it any time without rebaselining; question-topic + audit-weakness + phase mapping rows are load-bearing.
- **Next.** P8-T2 internal close — start `npm run dev:staging`, run `answer-engine-probe` against all 10 audit Qs + v22-P3 q01 shape, archive probe outputs as fixtures, flip xfail decorators in the regression suite. Then P8-T3 is operator-coordinated external SME re-run.

### 2026-05-17 ~12:55 PM Bogotá — G7 / P7 added (Anclaje Legal topic-aware constraint)

- **Trigger.** v22's P3 closing probe (run dir `tracers_and_logs/logs/probe_runs/20260517T174327Z_v22_t2_postfix/`) verdict on q01 (CST 64 question) was `warn`: the v22 CST/ET mislabel fix worked end-to-end (all body bullets correctly cite `(art. 64 CST)` / `(art. 401-3 ET)` etc.), BUT the Anclaje Legal section expanded from 1 line (pre-v21) to 4 lines, with 3 off-topic ET articles (`Art. 102 ET — fiducia`, `Art. 102-2 ET — transporte terrestre`, `Art. 103 ET — definición de rentas`) surfaced alongside the correct `Art. 64 CST` primary line.
- **Operator directive (2026-05-17 ~12:50 PM Bogotá):** "cierra v22; explora v23 (el documento ya existe) para incorporar en éste la mejora de 'limpiar el anclaje'." v22 closed ✅ (4 commits + ff-merge + push + tag `fix_v22_closed` + orphan branch deleted local+remote). v23 extended here with G7 / P7.
- **What changed in this doc revision:**
  - §0 scope-extension paragraph naming the v22 handoff
  - §0 TL;DR — 6 → 7 fix phases, P7 anchor, closing gate renumbered P7 → P8, flag count 5 → 6
  - §1.2 audit-question table — new "v22-handoff" row for q01 v22-P3 shape
  - §1.3 root-cause map — new G7 row naming the polish prompt's REGLA DE EXPANSIÓN as the inviter + the synthesis composition path
  - §2.1 phase status — new P7 row + P8 renumbered closing-gate row
  - §2.3 task table — 6 new P7-T1..T6 tasks; P7-T1..T7 closing-gate tasks renumbered P8-T1..T7
  - §3 — new §3.7 phase narrative (P7 Anclaje gate); §3.7 closing gate renumbered §3.8 + internal P7 task IDs renumbered P8
  - §4.1 new-files table — added `pipeline_d/answer_anclaje_topic_gate.py` (~60 LOC) + `tests/test_anclaje_topic_gate.py`
- **Why this is a separate phase, not a P3 sub-task.** P3 (G3 Citation Source-Code Awareness) is about WHICH CODE LABEL gets attached to a citation. P7 (G7 Anclaje Legal Topic-Aware Constraint) is about WHICH ARTICLES get cited in the Anclaje section at all — even articles with correct ET / CST labels can still be off-topic relative to the question. Different filter, different layer (synthesis vs polish), different evidence axis (topic-relevance vs source-code).
- **Why the gate uses v22's compat-doc-topics allowlist.** v22 §9c added 3 mutual adjacencies (`declaracion_renta ↔ calendario_obligaciones ↔ regimen_sancionatorio_extemporaneidad`) to `config/compatible_doc_topics.json`. The same data structure answers "which topics count as compatible evidence for topic X?" — exactly the question P7 asks about Anclaje. Reuse minimizes new config surface area; new code is the gate function only.
- **Why body bullets are untouched.** Synthesis facades (`answer_synthesis_practica.py`, `answer_synthesis_helpers.py`, etc.) may compose substantive bullets from connected_articles where the off-topic content can still be useful context. P7 constrains ONLY the Anclaje Legal section composition; everywhere else, connected_articles flow through as before.
- **Next.** v23 plan is now revision-2. v23 execution begins at P0-T0 only when operator gives explicit greenlight (per `feedback_sme_panel_explicit_request_only` for the closing gate; per general plan-execution discipline for the work itself).

### 2026-05-17 ~12:30 PM Bogotá — v23 plan drafted (plan-mode artifact)

- **What.** Drafted full v23 plan in plan-mode artifact at `/Users/ava-sensas/.claude/plans/you-are-tasked-with-bubbly-aho.md`. Mirrors v22 fix-doc shape (§⏯ + §-1 + state tracker + 7 phases + files + risks + run log + six-gate + decisions + open Qs + NOT-doing + preconditions).
- **Why.** Operator directive: "do not execute the plan! make it part of the v23 document." Plan-file content IS the v23 doc — on ExitPlanMode approval, copy to `docs/re-engineer/fix/fix_v23_may.md` at P0-T3.
- **Context.** External Colombian-accountant audit on 2026-05-17 scored production LIA 1.85/5 across 10 representative Qs. v23 closes 6 generic weaknesses; closing gate = same SME re-runs same 10 Qs ≥ 4.0/5 + zero 1s.
- **Phase 1 exploration findings (load-bearing):**
  - Refusal at `_coherence_gate.py:135-138` via `orchestrator.py:937`; `GraphEvidenceItem.secondary_topics` already carries per-article topic data → sectioning architecturally feasible
  - NO year-constants registry anywhere; `case_bullets/retencion_salarios.py:12` hardcodes stale `"AG 2025 $47.065"` (47,065 is 2024 UVT)
  - `answer_inline_anchors.py:173-181 render_article_anchor_phrase` hardcodes `art. X ET`; accepts ANY string as article number
  - Audit pollution strings (`DISTRIBUIDORA EL SOL`, `ALEJANDRO VASQUEZ ARANGO`) NOT in git repo → cloud Supabase or Dropbox-synced
- **Locked design decisions** (via `AskUserQuestion` 2026-05-17 ~12:30 PM Bogotá):
  - D-S1: One mega-doc (not split v23/v24/v25)
  - D-S2: External SME re-runs all 10 Qs as closing gate
  - D-S3: Cloud-corpus pollution = diagnose-only in v23; v24 cleans
- **Next.** On `ExitPlanMode` approval: P0-T0 (verify v22 closed) → P0-T1 (archive audit) → P0-T2 (spin worktree) → P0-T3 (copy this plan to repo) → P0-T4 (regression suite scaffold) → P1 begins.

---

## §7. Six-gate lifecycle per phase

Each phase must clear all six gates per `CLAUDE.md` Non-Negotiables before being declared ✅. Per `feedback_gates_evaluate_independently`, qualitative pass on phase N does NOT lower phase N+1's bar.

| Phase | 1. Idea | 2. Plan | 3. Success | 4. Test plan | 5. Greenlight | 6. Refine-or-discard |
|---|---|---|---|---|---|---|
| P0 | preconditions + archival | §3.0 | 5 SCs (tag + audit + worktree + doc + suite) | operator + engineer ~30 min | operator after P0-T4 | re-scope if v22 not closed |
| P1 | decompose instead of refuse | §3.1 | 4 SCs measurable on Q1/Q3/Q6/Q8 | engineer 2–3 d + probe + SME spot-check | operator + SME after re-probe | revert flag if regression |
| P2 | inject canonical year constants | §3.2 | 5 SCs measurable on Q2/Q10 | engineer 1–2 d + probe | operator after re-probe | revert flag |
| P3 | article→source-code awareness | §3.3 | 5 SCs measurable on Q4/Q5/Q9 + Q2 regression | engineer 2 d + probe | operator after re-probe | revert flag |
| P4 | diagnose + shadow filter | §3.4 | 5 SCs measurable (report + filter shadow) | engineer 1 d + operator scan run | operator after report review | filter stays shadow |
| P5 | preserve user numerics + contradiction-check | §3.5 | 4 SCs measurable on Q10 + multi-year regression | engineer 1 d + probe | operator after re-probe | revert flag |
| P6 | reject voseo | §3.6 | 3 SCs measurable on Q7 + 10-Q sweep | engineer 0.5 d + probe | operator after sweep | revert flag |
| P7 | external SME re-run | §3.7 | 6 SCs (incl. SME avg ≥ 4.0 + zero 1s) | operator + SME 2–5 d | SME verdict | iterate ≤ 2 cycles per failing phase |

---

## §8. Open questions (genuinely undecided — needs operator before that phase starts)

| # | Question | Blocks | Surfaced |
|---|---|---|---|
| Q-Open-1 | For ambiguous article numbers (CCo art. 64 vs CST art. 64), silent drop OR render with topic-hint suffix `(art. 64 — verificar código)`? | P3-T3 | 2026-05-17 ~12:30 PM. Current plan default: silent drop with diagnostic. Operator may override before P3-T3. |
| Q-Open-2 | After P4-T2 audit findings, demote-and-keep OR hard-drop polluted chunks? | P4-T4 flag promotion (shadow → enforce) | 2026-05-17. Decided after report review; informs v24 retirement scope. |
| Q-Open-3 | Year extractor — fall back to `date.today().year` when no fiscal year detected? | P2-T4 | 2026-05-17. **Current plan default: NO fallback** (return `None`, skip injection). Silently injecting current-year constants into a question about a different year is worse than no injection. Operator may override. |
| Q-Open-4 | Should P7 require ALL 10 Qs ≥ 4 OR allow avg ≥ 4.0 with one "borderline" Q at 3? | P7-T5 close criterion | 2026-05-17. **Current plan default: avg ≥ 4.0 + zero 1s** (one Q at 3 acceptable; zero 1s mandatory). Operator may tighten. |
| Q-Open-5 | If P7-T3 SME re-run misses scheduling window (>5 days), do we close v23 on internal probe alone with SME re-run deferred to async? | P7-T6 | 2026-05-17. **Current plan default: NO** — v23 stays open until SME confirms. Operator may override if business-critical. |

Update this section as new questions surface during execution.

---

## §9. Decisions locked in (do not re-litigate without operator sign-off)

| # | Decision | Reason | Locked when |
|---|---|---|---|
| D1 | v23 scope = ALL 6 generic weaknesses surfaced by 2026-05-17 audit; one mega-doc | Operator directive "pass this test with flying colors"; `AskUserQuestion` D-S1 | 2026-05-17 ~12:30 PM |
| D2 | Closing gate = external SME re-runs same 10 Qs; pass = ≥ 4.0/5 avg + zero 1s | `AskUserQuestion` D-S2; audit IS the success criterion | 2026-05-17 ~12:30 PM |
| D3 | Cloud-corpus pollution = diagnose-only in v23; v24 cleans + retires | `AskUserQuestion` D-S3; avoids racing audit-driven retirement | 2026-05-17 ~12:30 PM |
| D4 | All v23 fixes ship behind kill-switch flags | CLAUDE.md non-negotiable + `project_beta_riskforward_flag_stance` | repo standing rule |
| D5 | Beta-stance: 4 of 5 new flags default `enforce`; entity-filter defaults `shadow` (operator-promoted after P4 audit) | `project_beta_riskforward_flag_stance` + P4 diagnose-first | 2026-05-17 (this doc) |
| D6 | Diagnose-before-intervene per phase (P1-T1, P2-T1, P3-T1, P4-T2, P5-T1) | `feedback_diagnose_before_intervene` | repo standing rule |
| D7 | Granular edits — new files for new concerns; no monolith bloat | `feedback_granular_edits`; orchestrator.py already >1k LOC | repo standing rule |
| D8 | Default run mode = dev:staging | `feedback_default_run_mode_staging` | repo standing rule |
| D9 | SME panel operator-triggered only; self-audit via `answer-engine-probe` | `feedback_sme_panel_explicit_request_only` | repo standing rule |
| D10 | Year extractor — no `date.today().year` fallback | Q-Open-3 default; silent wrong-year injection worse than no injection | 2026-05-17 (this doc) |
| D11 | Ambiguous article-number citations — silent drop with diagnostic, not `verificar código` suffix | Q-Open-1 default; visible "verificar" UX worse than missing citation | 2026-05-17 (this doc) |
| D12 | Permanent regression suite at `tests/test_audit_regression_q01_q10.py` — the 10 audit Qs verbatim | Audit is canonical regression set; per `feedback_verify_fixes_end_to_end` | 2026-05-17 (this doc) |

---

## §10. What v23 does NOT do (honest scope)

- v23 does **not** clean cloud-corpus pollution (deferred to v24 per D-S3).
- v23 does **not** add source-code support for codes beyond ET / CST / CCo / Ley 43/1990 / Res. DIAN / Decreto (others land case-by-case as audit re-runs surface them).
- v23 does **not** auto-run the SME panel (per D9).
- v23 does **not** modify cloud Supabase / Falkor data (P4 read-only audit only; pre-authorized read access per `feedback_lia_graph_cloud_writes_authorized`).
- v23 does **not** raise thresholds on existing v22 / v18+ gates (per `feedback_thresholds_no_lower`); only adds new validators alongside.
- v23 does **not** rewrite the polish prompt from scratch — surgical additions only.
- v23 does **not** touch the Normativa or Interpretación surface backends (per AGENTS.md surface boundaries); only `main chat` orchestration + synthesis + polish.
- v23 does **not** modify v22 commits — P3 layers a general source-code resolver on top of v22's CST/ET surgical fix; v22 commits stay intact.

---

## §11. Resuming work — preconditions + first-action recipe

A fresh agent should be able to start P0 immediately after the preconditions below pass.

### §11.1 Preconditions (run all six, all must pass)

```bash
# 1. v22 closed.
git tag --list fix_v22_closed && echo "OK v22 closed" || echo "BLOCKING — finish v22 first"

# 2. Recent commits show v22 close (sanity check).
git log --oneline -10 | grep -E "v22.*closed\|ship\(v22" && echo "OK v22 commits present" || echo "WARN — verify v22 ship state"

# 3. Local docker stack — Supabase + Falkor up.
docker ps --filter "name=supabase_db_lia-graph" --filter "name=lia-graph-falkor-dev" --format "table {{.Names}}\t{{.Status}}"

# 4. .env.staging exists.
test -f .env.staging && grep -q "^FALKORDB_URL=redis" .env.staging && echo "OK staging env" || echo "MISSING"

# 5. dev:staging server up + answering.
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8787/

# 6. Audit verbatim available to archive (in chat history / operator paste buffer).
echo "Operator: confirm audit verbatim is available for P0-T1 archival before proceeding"
```

If any precondition fails, STOP and consult the relevant file (`fix_v22_may.md` for v22 state; `docs/guide/env_guide.md` for env state).

### §11.2 Phase 0 first action (after preconditions pass)

Announce in chat: "Starting v23. P0-T0: verifying v22 closing tag, then archiving audit verbatim, then spinning worktree `fix-v23-may`."

Then run:

```bash
# P0-T0
git tag --list fix_v22_closed

# P0-T1 (after operator pastes audit content)
mkdir -p docs/re-engineer/audits
# (write audit content to docs/re-engineer/audits/2026-05-17_external_sme_audit_pre_v23.md)

# P0-T2
git worktree add ../Lia_Graph-fix-v23-may -b fix-v23-may main
# (add row to docs/re-engineer/active_worktrees.md per §9b.1 #1)

# P0-T3 — on worktree:
cd ../Lia_Graph-fix-v23-may
cp /Users/ava-sensas/.claude/plans/you-are-tasked-with-bubbly-aho.md docs/re-engineer/fix/fix_v23_may.md
git add docs/re-engineer/fix/fix_v23_may.md docs/re-engineer/audits/2026-05-17_external_sme_audit_pre_v23.md docs/re-engineer/active_worktrees.md
git commit -m "$(cat <<'EOF'
docs(v23 P0): scaffold fix_v23_may.md + archive 2026-05-17 audit

P0-T1: archive external accountant audit verbatim as v23 closing-gate evidence.
P0-T3: copy plan-mode artifact to canonical fix-doc location.

Audit scored production LIA 1.85/5 across 10 representative accountant Qs.
v23 = 6-phase mega-doc to lift score to >= 4.0/5 + zero 1s per same 10 Qs.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
git push -u origin fix-v23-may

# P0-T4
# (create tests/test_audit_regression_q01_q10.py with 10 xfail-decorated tests; phases enable per-question)
```

Document P0 close in §6 run log. Then announce: "P0 closed — ready for P1 (Topic-Gate Decomposition) sprint — operator greenlight?"

### §11.3 What to do after each phase closes

- Append §6 run log entry with phase outcome + test names + green status.
- Set §2.1 phase row to ✅; next phase to 🔵.
- Announce in chat: "P{N} closed — {one-line summary}. Ready for P{N+1} — operator greenlight?"
- DO NOT start P{N+1} without explicit operator greenlight (per `feedback_gates_evaluate_independently`).

### §11.4 What to do after P6 closes (all fix phases done; P7 next)

- Announce: "All 6 fix phases closed. Ready for P7 (external SME closing gate). Operator: please contact the external accountant for re-run. Estimated coordination window: 2–5 days."
- Wait. Do NOT close v23 until SME verdict arrives.

### §11.5 What to do after P7 closes (v23 closing)

- §⏯ "Last completed step" → "v23 closed ✅"
- Update CLAUDE.md runtime-flags table to reflect all 5 new flags as standing canon.
- Remove `fix-v23-may` worktree + row from `active_worktrees.md` per `§9b.1 #1`.
- `git tag fix_v23_closed` per `§9b.3 #2`.
- Open `docs/re-engineer/fix/fix_v24_may.md` from `fix_v24_may_SCOPE.md` (created at P4-T5) — v24 starts with the cleanup of P4 pollution findings.

---

*Drafted 2026-05-17 ~12:30 PM Bogotá by claude-opus-4-7 in response to operator directives: "the goal of v23 is to PASS THIS TEST with flying colors" (audit-driven mega-doc) + "do not execute the plan! make it part of the v23 document" (plan-file IS the v23 doc, no remote execution). Companion to [fix_v22_may.md](fix_v22_may.md) (predecessor) and [external audit](../audits/2026-05-17_external_sme_audit_pre_v23.md) (to be archived at P0-T1). Update §⏯ + §2 + §6 as work progresses.*
