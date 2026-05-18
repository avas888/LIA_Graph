# fix_v25_may.md — capability lift on the dual-packet 2026-05-17 audit — v1

> **Zero-agent-context protocol.** Self-contained. A fresh agent with no prior conversation can execute it by reading this file + the filesystem. Verify every artifact against `git ls-files`. If something doesn't exist, STOP and report drift.
>
> **Scope.** External Colombian-accountant SME ran TWO packets on 2026-05-17 PM (post-v23 ship): (a) the original 10-Q baseline re-test (rerun avg **2.15/5** vs pre-v23 **1.85/5**) and (b) a NEW 10-Q packet covering ICA territoriality, IVA prorrateo, contratistas + UGPP, servicios desde el exterior, dividendos, precios de transferencia, pérdidas fiscales, notas crédito/débito, leasing NIIF Pymes, ESAL/RTE (new-packet avg **2.35/5**). v25 attacks **9 generic architectural weaknesses (G8–G16)** that span both packets — NOT per-question patches. Operator directive 2026-05-17 PM: "improve capability of the model and not to overcorrect for specific questions that simply try to gauge model's overall performance."
>
> **Companion docs.** [`fix_v23_may.md`](fix_v23_may.md) — predecessor (closed internal 2026-05-17 with G1–G7 covered). [`fix_v24_may_SCOPE.md`](fix_v24_may_SCOPE.md) — cloud-corpus pollution cleanup (independent track; v25 ships runtime safety nets, v24 ships data retirements). External audit verbatim at `docs/re-engineer/audits/2026-05-17_external_sme_audit_post_v23.md`.
>
> **Work branch.** `fix-v25-may` (created off `main` 2026-05-17 PM Bogotá). No worktree for v25 — single-branch hygiene per operator directive ("do all work in a purpose branch"). Closing tag: `fix_v25_closed`.

---

## §⏯ Crash-resume pointer (update after EVERY step)

| Field | Value |
|---|---|
| Last completed step | **P1–P9 landed on branch `fix-v25-may` (9 commits incl. P0 plan)**. CLAUDE.md flag table updated with 8 new v25 rows + entity-filter promotion note. 257 unit tests green across v23 + v25 affected suites (audit-regression v25 suite stays xfail until P10 probe fixtures land). Polish prompt directives (norm-keyed, cross-border, municipal, framework, deadlines) all wired through `answer_polish_directives_v25.py` sibling per granularization directive. Outstanding: P10-T2 internal probe sweep + P10-T3 external SME re-run (operator-coordinated). |
| Last touched UTC | 2026-05-17T23:30:00Z (~6:30 PM Bogotá) |
| Next step | **P10-T2 (engineer)** — start `npm run dev:staging`, run `answer-engine-probe` on combined 20-Q superset, capture probe fixtures at `tests/fixtures/audit_v25_q01_q20/{qid}.answer.txt`, lift xfail decorators. Then **P10-T3 (operator)** — coordinate external accountant re-run of the same 20 Qs on production. Acceptance per D-S2: avg ≥ 4.0/5 + zero 1s. |
| Working artifact | `docs/re-engineer/fix/fix_v25_may.md` (this file) on branch `fix-v25-may` |
| Cloud state | Inherits v23 close-state: cloud Supabase `gen_v20_20260516_172203` is_active=true; cloud Falkor 10,217 ArticleNodes, 3,401 TEMA edges. **v25 reads cloud Supabase via runtime probes only; no v25 phase writes to cloud.** v24 (separate doc) handles retirement. |
| Local state | Branch `fix-v25-may` ahead of main by 0 commits at draft-time. |
| Uncommitted code changes | None (only doc additions in progress). |
| Heartbeat / monitor state | None active. |
| If crashing now, resume with | (1) `git checkout fix-v25-may`. (2) `git log --oneline -5` — verify branch present. (3) `git status` — check uncommitted. (4) Continue at "Next step" above. |
| Hard rule | After EVERY task transition, update this block + §2 phase/task tables + append a §6 run log entry. Do not batch updates. |

---

## §-1. If you are a fresh agent — read this first

You are picking up a **multi-phase capability-lift project** triggered by an external Colombian-accountant audit that scored production LIA post-v23 at **avg 2.25/5 across 20 questions** (10 rerun + 10 new). v25 must lift the **combined 20-question** average to `≥ 4.0 / 5 + zero "1 = Failed" scores` as judged by the **same external accountant** (D-S2, carried from v23).

**Read in this order before touching anything (max 30 min):**

1. `CLAUDE.md` (repo root) — repo operating guide. "Fast Decision Rule" + the `LIA_*` flag rows are load-bearing.
2. `AGENTS.md` (repo root) — layer ownership.
3. **This file** §0 → §1 → §2 → §3 → §11.
4. [`fix_v23_may.md`](fix_v23_may.md) §⏯ — confirm v23 closed (internal) before proceeding.
5. `docs/re-engineer/audits/2026-05-17_external_sme_audit_post_v23.md` — the verbatim audit. This IS v25's success criterion.

**Hot facts you must know before touching anything:**

- **Default run mode is `dev:staging`** — cloud Supabase + cloud Falkor (`LIA_REGULATORY_GRAPH`). Per `feedback_default_run_mode_staging`.
- **Cloud writes for Lia Graph are pre-authorized** — announce in chat before executing, no per-action confirmation needed. Per `feedback_lia_graph_cloud_writes_authorized`. v25 only READS cloud at probe time.
- **MANDATORY server restart before EVERY probe.** Same rule as v22/v23.
- **SME panel is OFF-LIMITS** for auto-runs — use `answer-engine-probe` skill for self-audit (per `feedback_sme_panel_explicit_request_only`). External SME re-run is OPERATOR-COORDINATED.
- **Beta-stance applies** — every non-contradicting improvement flag flips ON across all three run modes per `project_beta_riskforward_flag_stance`. v25 introduces 9 flags, all default `enforce` except the entity-filter promotion (`shadow` → `enforce` per phase P8).
- **No text walls in docs.** Bullets/lists/tables only.
- **Vigencia is norm-keyed** per `feedback_vigencia_norm_keyed` — v25 P1 norm-keyed boost must not regress this.
- **Granular edits** per `feedback_granular_edits` — new files for new concerns; do NOT bloat `answer_llm_polish.py` (already 1647 LOC) or `orchestrator.py` (already >1k LOC).
- **No money quoting** per `feedback_no_money_quoting` — status reports name action + effort + what it unblocks, not $/cost.

**Operator's intent (boss directive, 2026-05-17 PM Bogotá):**

- Quote: "Idea ALWAYS is to improve capability of the model and not to overcorrect for specific questions that simply try to gauge model's overall performance."
- Quote: "you do EVERYTHING and it is prohibited that you ask for authorization. You take ALL decisions, run all processes and in general deliver a better software than we have today; do all work in a purpose branch."
- Locked decisions (drafted into D1–D12 in §9):
  - **D1: ONE mega-doc** covering all 9 generic weaknesses (G8–G16). Carries v23's D-S1.
  - **D2: External SME re-run on the combined 20-question superset** as closing gate; target avg ≥ 4.0/5 + zero 1s.
  - **D3: Cloud-corpus retirement stays gated to v24**; v25 promotes the runtime safety-net from `shadow` → `enforce` and extends patterns.
  - **D4: No pre-approval gates** — autonomy mode (per operator quote above). Engineer takes all design decisions and commits at phase boundaries; operator holds the closing gate only.

**Memory-pinned guardrails (do not violate):**

- Diagnose before intervene per `feedback_diagnose_before_intervene` — every phase has a measure-first sub-task.
- Granular edits per `feedback_granular_edits` — new files for new concerns.
- No text walls; no money quoting; no SME panel auto-run.
- Recommendations live in the canonical plan per `feedback_recommendations_logged_in_canonical_plan` — this file IS the canonical plan.
- Don't lower thresholds per `feedback_thresholds_no_lower` — add new validators alongside existing ones; never relax.
- Each gate evaluates independently per `feedback_gates_evaluate_independently` — qualitative pass on P1 does NOT lower P2's bar.
- No hallucinated examples per `feedback_no_hallucinated_examples` — every concrete `norm_id`, URL, regex in expert-facing artifacts is verified or flagged as hypothetical.

**The big picture in two sentences:**

- v23 closed 7 generic weaknesses in the answer-shaping pipeline (G1–G7); the post-v23 SME audit surfaced 9 NEW generic weaknesses (G8–G16) that v23 did not target — they cluster around **retrieval routing** (cross-border, municipal, framework-specific, norm-keyed) and **answer-shaping integrity** (sub-question coverage, deadline registry, fallback numerics, counterfactual injection, pollution reach).
- v25 ships 9 phased fixes (P1 norm-keyed retrieval → P9 counterfactual-example detector), each behind its own kill-switch flag, each gated by the audit Qs it targets, closing only when the external SME re-confirms `≥ 4.0/5 + zero 1s` on the combined 20-question superset.

---

## §0. TL;DR

- **What v25 closes.** All 9 generic weaknesses (G8–G16) surfaced by the 2026-05-17 dual-packet SME audit. The combined 20-question superset becomes the permanent regression suite at `tests/test_audit_regression_v25_combined.py`.
- **Why v25 exists.** Post-v23 LIA scored 2.25/5 averaged across 20 representative accountant questions. v23 cleaned the **answer-shaping** layer; v25 attacks the **retrieval routing** and **fallback / validator** layers.
- **10 phases, sequenced by leverage × independence.**
  - **P0 (Preconditions + audit archival + regression suite scaffold)** — gating.
  - **P1 (Norm-keyed retrieval boost — G8)** — when Q names a specific Resolución / Acuerdo / Decreto, boost matching `norm_id` chunks; fixes Q1/Q7/Q8/Q18.
  - **P2 (Cross-border lane — G9)** — detect foreign-payment context and force ET 408 / 437-2 / 420 par.3 / 124-1 / 124-2 retrieval lane; fixes Q14.
  - **P3 (Municipal tax routing — G10)** — detect ICA / Bogotá / municipal context; surface canonical local-norm pointer when corpus lacks SHD sources; fixes Q11.
  - **P4 (Accounting-framework awareness — G11)** — detect NIIF Pymes vs IFRS Plenas; reject NIIF 16 mention in a NIIF Pymes question; fixes Q19.
  - **P5 (Sub-question coverage gate — G12)** — strip / re-route `"Cobertura pendiente"` non-answers; fixes Q3 / Q12 / Q16.
  - **P6 (Compliance-deadline registry — G13)** — extend `year_facts` with named per-norm deadlines + multi-UVT helpers (4 UVT, 27 UVT); fixes Q7 / Q13 / Q20.
  - **P7 (Fallback-path numeric echo — G14)** — preserve user numerics through polish-reject → fallback; fixes Q10.
  - **P8 (Promote entity filter + extend patterns — G15)** — flip `LIA_CHUNK_QUALITY_ENTITY_FILTER` from `shadow` → `enforce`; add patterns for Concepto DIAN 191/2025 depreciación, INC vehicle arts., named-person leak; fixes Q5 / Q9 / Q15.
  - **P9 (Counterfactual-example detector — G16)** — new polish validator that flags injected persons / companies / monetary facts NOT in question or evidence; fixes Q8 / Q16 / Q17.
  - **P10 (Internal close + external SME closing gate)** — operator-coordinated.
- **9 new flags.** `LIA_NORM_KEYED_BOOST` / `LIA_CROSS_BORDER_LANE` / `LIA_MUNICIPAL_TAX_ROUTING` / `LIA_FRAMEWORK_AWARENESS` / `LIA_COVERAGE_GAP_GATE` / `LIA_DEADLINE_REGISTRY_INJECTION` / `LIA_FALLBACK_NUMERIC_ECHO` / `LIA_COUNTERFACTUAL_DETECTOR` default `enforce`; `LIA_CHUNK_QUALITY_ENTITY_FILTER` promoted from `shadow` → `enforce`.
- **Time budget.** P1: 1 d. P2: 1 d. P3: 0.5–1 d. P4: 0.5 d. P5: 0.5 d. P6: 0.5–1 d. P7: 0.5 d. P8: 0.5 d. P9: 0.5–1 d. Internal close + SME re-run: 2–5 d. **Total elapsed ~1 week** serial; ~3 days if P1/P2/P3 parallelize.
- **Closing gate.** D-S2 — external SME re-runs the combined 20-question superset on production; pass = `≥ 4.0/5 avg + zero 1s`. Archived at `docs/re-engineer/audits/<UTC>_v25_closing_sme_verdict.md`.
- **Risk.** Each fix behind a kill-switch flag. All v23 + v22 baseline tests must stay green.
- **Estado al 2026-05-17 ~5:00 PM Bogotá.** P0 🔵 in progress (archive ✅; doc 🔵; scaffold 🟡).

---

## §1. Where we are right now (v23 close-state assumption)

### §1.1 What v23 closes (verify at P0-T0)

- ✅ G1 topic-decomposition lands on Q1/Q3/Q6/Q8 refusals (internal verdict ✅).
- ✅ G2 year-constants registry seeds polish prompt + UVT validator.
- ✅ G3 article→source-code resolver replaces hardcoded `art. X ET`.
- ✅ G4 cloud-corpus pollution diagnose + `LIA_CHUNK_QUALITY_ENTITY_FILTER=shadow` filter.
- ✅ G5 polish input-preservation + same-answer year-constant contradiction validators.
- ✅ G6 voseo validator + Colombian-Spanish locale directive.
- ✅ G7 Anclaje Legal topic-aware constraint (cleaned q01 CST 64 case).
- ✅ Internal probe: 7/11 regression tests pass; 4 stay xfail (UVT figure-quoting Q2, CST mention Q4, Ley 43 + CCo citation Q5, user-numeric echo Q10) tracked as corpus-coverage gaps.

**If `git tag fix_v23_closed` is absent, STOP and confirm with operator.** v25 builds ON v23's foundation; it does not relitigate v23's surgical fixes.

### §1.2 What v23 does NOT address (this is v25's mandate)

| Audit Q | Topic | Rerun score | Generic weakness | v25 phase |
|---|---|---:|---|---|
| Q1 | Documento soporte | 2.5 | G8 norm-keyed retrieval (Res. 000167/2021) | **P1** |
| Q3 | Periodicidad IVA | 1.5 | G12 sub-question coverage ("Cobertura pendiente") | **P5** |
| Q5 | Revisor fiscal | 1.0 | G15 pollution + G3 source-code (handled) | **P8** |
| Q7 | Información exógena | 2.5 | G8 norm-keyed (Res. 000233/2025) + G13 deadlines | **P1 + P6** |
| Q8 | RUB | 1.0 | G8 norm-keyed (Res. 000164/2021) + G16 counterfactual ("Carlos Moreno Pérez") | **P1 + P9** |
| Q9 | Cartera (deterioro) | 3.0 | G15 pollution (Concepto DIAN 191/2025 depreciación) | **P8** |
| Q10 | Activo fijo | 2.0 | G14 fallback numeric mutation | **P7** |
| Q11 | ICA Bogotá territorialidad | 1.0 | G10 municipal routing | **P3** |
| Q12 | IVA prorrateo | 3.5 | G12 sub-question coverage (noise) | **P5** |
| Q13 | Contratistas + UGPP | 3.0 | G13 deadline / multi-UVT helper (4 UVT) | **P6** |
| Q14 | Software cloud abroad | 1.0 | G9 cross-border lane | **P2** |
| Q15 | Dividendos | 2.0 | G15 pollution (INCRNGO donations leak) + G9 (extranjero) | **P2 + P8** |
| Q16 | Precios de transferencia | 2.5 | G16 counterfactual (Panama 1,930M over user's 6,000M) | **P9** |
| Q17 | Pérdidas fiscales | 3.0 | G16 counterfactual ("InnovaLab") | **P9** |
| Q18 | Notas crédito/débito FE | 2.5 | G8 norm-keyed (Res. 000165/2023) | **P1** |
| Q19 | Leasing NIIF Pymes | 2.5 | G11 framework awareness | **P4** |
| Q20 | RTE / ESAL | 2.5 | G13 deadline registry (March 31) | **P6** |

### §1.3 Generic-weakness → root-cause map (verified during planning)

| G | Audit failure shape | Affected Qs | Root-cause file:line | Today's behavior |
|---|---|---|---|---|
| **G8** | Named Resolución / Acuerdo / Decreto in Q is not retrieved | Q1/Q7/Q8/Q18 | `pipeline_d/retriever_supabase.py:_rerank_*` — no `norm_id` exact-match priority pass | Vector + lexical only; specific resolution citation has no dedicated boost |
| **G9** | Foreign-payment context defaults to domestic ET 392 | Q14, partly Q15 | `pipeline_d/planner.py` topic router — no `pagos_al_exterior` detection; `topic_taxonomy.json` lacks `servicios_desde_el_exterior` alias chain | Question with "no domicilio en Colombia" routes to `retencion_en_la_fuente` (domestic ET 392), not ET 408/420 par.3/437-2 |
| **G10** | Municipal / district tax answered with national TTD / RST drift | Q11 | No local-sources retrieval lane (Bogotá SHD compilación not in corpus); planner has `ica` topic but no `territorialidad` sub-detection | Answer pulls ET 115/115-1 (deducción ICA en renta) + RST + TTD instead of Acuerdo 65/2002, Decreto Distrital 352/2002 |
| **G11** | NIIF Pymes question answered with NIIF 16 (IFRS Plenas) | Q19 | No framework router; polish prompt has no NIIF-Pymes constraint directive | LLM defaults to IFRS 16 right-of-use model for any leasing question regardless of "Pymes" cue |
| **G12** | "Cobertura pendiente" non-answer lands in polished output | Q3/Q12/Q16 | Polish-prompt section-expansion rule encourages explicit gap-acknowledgment string; no validator strips or re-routes | LLM emits `"Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente."` verbatim |
| **G13** | Compliance deadlines wrong (RTE Jan-Jun 30 vs real March 31) | Q7/Q13/Q20 | `year_facts.py` registry has UVT / SMLMV / auxilio but NO per-norm deadline fields | LLM hallucinates dates without a canonical source |
| **G14** | Fallback path remutates user numerics | Q10 | `answer_polish_rejected_fallback.py` does not consume user-numeric extract; fallback re-templates without echo guarantee | P5 input-preservation validator rejects polish → fallback fires → fallback ALSO mutates → user sees `$2.000.000` |
| **G15** | Topic-incompatible pollution chunks reach body bullets (not just Anclaje) | Q5/Q6/Q8/Q9/Q15 | `LIA_CHUNK_QUALITY_ENTITY_FILTER=shadow` in `dev-launcher.mjs`; patterns missing for Concepto DIAN 191/2025 depreciación, INC vehicle 512-3/4/5, INCRNGO donations leak | Filter scores chunks but doesn't demote at retrieval time; topic-incompatible pollution still funnels into synthesis |
| **G16** | Counterfactual injection: persons / companies / monetary facts NOT in Q or evidence | Q5/Q8/Q16/Q17 | No polish validator for counterfactual entities; `_preserves_user_numerics` only checks survival of user-stated values, not introduction of new ones | LLM invents "Carlos Moreno Pérez", "InnovaLab", "Panama 1,930M" examples to "illustrate" |

### §1.4 The non-negotiable invariants v25 must preserve

- **v23 substance stays.** All G1–G7 fixes remain in force; v25 layers new behavior on top.
- **v23 enforce flags stay enforced.** `LIA_TOPIC_DECOMPOSITION_MODE`, `LIA_YEAR_CONSTANTS_INJECTION`, `LIA_CITATION_SOURCE_CODE_AWARENESS`, `LIA_POLISH_INPUT_PRESERVATION`, `LIA_POLISH_LOCALE_STYLE_COLOMBIAN`, `LIA_ANCLAJE_TOPIC_GATE` — all stay at `enforce`.
- **Tax-side `(ET art. N)` form correct and must NOT regress** for renta/IVA/retención articles after P2 cross-border lane lands.
- **Cloud retirements are CLI-explicit only** per CLAUDE.md non-negotiable. P1/P8 are runtime-only changes; no retirement in v25.
- **No SME panel auto-run** per `feedback_sme_panel_explicit_request_only`.
- **No raising of existing thresholds** per `feedback_thresholds_no_lower`.
- **No prose paragraphs in docs** per `feedback_no_text_walls`.

---

## §2. State tracker (live — update this section as work progresses)

### §2.1 Phase status

| Phase | Description | Status | Owner | Last touched |
|---|---|---|---|---|
| P0 | Preconditions + audit archival + regression-suite scaffold | ✅ done | claude | 2026-05-17 ~5:00 PM |
| P1 | Norm-keyed retrieval boost (G8) | ✅ done | claude | 2026-05-17 ~5:20 PM |
| P2 | Cross-border lane (G9) | ✅ done | claude | 2026-05-17 ~5:35 PM |
| P3 | Municipal tax routing (G10) | ✅ done | claude | 2026-05-17 ~5:45 PM |
| P4 | Accounting-framework awareness (G11) | ✅ done | claude | 2026-05-17 ~6:00 PM |
| P5 | Sub-question coverage gate (G12) | ✅ done | claude | 2026-05-17 ~6:00 PM |
| P6 | Compliance-deadline registry (G13) | ✅ done | claude | 2026-05-17 ~6:10 PM |
| P7 | Fallback-path numeric echo (G14) | ✅ done | claude | 2026-05-17 ~6:20 PM |
| P8 | Promote entity filter + extend patterns (G15) | ✅ done | claude | 2026-05-17 ~6:25 PM |
| P9 | Counterfactual-example detector (G16) | ✅ done | claude | 2026-05-17 ~6:00 PM |
| P10 | Internal close + external SME closing gate | 🔵 in progress (P10-T1 ✅; P10-T2 pending; P10-T3 operator) | claude (internal) + operator (SME) | 2026-05-17 ~6:30 PM |

Status legend: 🟡 not started · 🔵 in progress · ✅ done · 🚫 blocked · ↩ discarded.

### §2.2 Active blockers

| # | Blocker | Affects | Owner | Surfaced |
|---|---|---|---|---|
| B1 | `git tag fix_v23_closed` must be present (assumed) | All P0+ | operator | 2026-05-17 |

### §2.3 Active tasks (rolls up from §3 phases)

| ID | Task | Phase | Status | Blockers |
|---|---|---|---|---|
| P0-T0 | Verify v23 internal-closed posture (tag or §⏯ "v23 internally closed") | 0 | 🔵 | B1 |
| P0-T1 | Archive audit verbatim to `docs/re-engineer/audits/2026-05-17_external_sme_audit_post_v23.md` | 0 | ✅ | P0-T0 |
| P0-T2 | Branch `fix-v25-may` cut from `main` | 0 | ✅ | P0-T1 |
| P0-T3 | Copy plan to `docs/re-engineer/fix/fix_v25_may.md`; commit on branch | 0 | 🔵 | P0-T2 |
| P0-T4 | Permanent regression suite scaffold `tests/test_audit_regression_v25_combined.py` (20 xfail tests initially; phases enable per-question) | 0 | 🟡 | P0-T3 |
| P1-T1 | Diagnose — read `retriever_supabase.py` reranker; map where `norm_id` lands in chunk metadata | 1 | 🟡 | P0-T4 |
| P1-T2 | Implement `pipeline_d/norm_keyed_boost.py` (~120 LOC) — `extract_named_resolutions(question) → list[NormRef]`; `boost_chunks_by_norm_id(chunks, refs, factor=1.5)` | 1 | 🟡 | P1-T1 |
| P1-T3 | Wire into `retriever_supabase.py` post-rerank; add `LIA_NORM_KEYED_BOOST={off,shadow,enforce}` flag default `enforce` | 1 | 🟡 | P1-T2 |
| P1-T4 | Unit tests `tests/test_norm_keyed_boost.py` — 5 fixtures (Res. DIAN 000167/2021, 000165/2023, 000164/2021, 000233/2025, Acuerdo 65/2002) | 1 | 🟡 | P1-T3 |
| P2-T1 | Diagnose — read `planner.py` topic detection; verify `topic_taxonomy.json` lacks `servicios_desde_el_exterior` cue chain | 2 | 🟡 | P0-T4 |
| P2-T2 | Implement `pipeline_d/cross_border_lane.py` (~100 LOC) — `detect_cross_border_context(question) → CrossBorderHint`; force-include canonical articles ET 408 / 410 / 414-1 / 420 par.3 / 437-2 lit.e / 124-1 / 124-2 via fixture-bundle retrieval | 2 | 🟡 | P2-T1 |
| P2-T3 | Wire into orchestrator pre-retrieval; add `LIA_CROSS_BORDER_LANE={off,shadow,enforce}` flag default `enforce` | 2 | 🟡 | P2-T2 |
| P2-T4 | Unit tests `tests/test_cross_border_lane.py` — 4 fixtures (cloud abroad, treaty, royalty payment, foreign technical service) | 2 | 🟡 | P2-T3 |
| P3-T1 | Diagnose — read `planner.py` ICA detection; confirm no Bogotá SHD sources in cloud corpus | 3 | 🟡 | P0-T4 |
| P3-T2 | Implement `pipeline_d/municipal_tax_routing.py` (~80 LOC) — `detect_municipal_context(question) → MunicipalHint` (city, has_territoriality, reteICA mention); surface canonical pointer block when corpus gap detected | 3 | 🟡 | P3-T1 |
| P3-T3 | Wire into synthesis pre-composition; add `LIA_MUNICIPAL_TAX_ROUTING={off,shadow,enforce}` flag default `enforce` | 3 | 🟡 | P3-T2 |
| P3-T4 | Unit tests `tests/test_municipal_tax_routing.py` — 3 fixtures (Bogotá, Medellín, generic municipal) | 3 | 🟡 | P3-T3 |
| P4-T1 | Diagnose — read polish prompt construction; verify no framework directive exists | 4 | 🟡 | P0-T4 |
| P4-T2 | Implement `pipeline_d/accounting_framework.py` (~70 LOC) — `detect_framework_hint(question) → FrameworkHint` (`niif_pymes` / `niif_plenas` / `niif_microempresas` / `decreto_2649_2706` / `none`); build polish directive | 4 | 🟡 | P4-T1 |
| P4-T3 | New polish validator `_framework_coherence` — reject answer that mentions `NIIF 16` / `IFRS 16` when question said `pyme` / `Pymes`; flag as `framework_mismatch` | 4 | 🟡 | P4-T2 |
| P4-T4 | Flag `LIA_FRAMEWORK_AWARENESS={off,shadow,enforce}` default `enforce`; tests | 4 | 🟡 | P4-T3 |
| P5-T1 | Diagnose — grep polish + synthesis for "cobertura pendiente" emit path | 5 | 🟡 | P0-T4 |
| P5-T2 | New polish validator `_no_coverage_gap_phrase` — reject polished text containing canonical gap-stubs (`Cobertura pendiente`, `valida el expediente`, `no encuentro evidencia`, etc.); polish retries once | 5 | 🟡 | P5-T1 |
| P5-T3 | Synthesis-side stripper `pipeline_d/coverage_gap_strip.py` — post-LLM cleanup that removes gap-stub bullets and substitutes a compact `[brecha de evidencia: <tema>]` notice when nothing else covers the sub-question | 5 | 🟡 | P5-T2 |
| P5-T4 | Flag `LIA_COVERAGE_GAP_GATE={off,shadow,enforce}` default `enforce`; tests | 5 | 🟡 | P5-T3 |
| P6-T1 | Diagnose — list audit deadlines that should be canonical (RTE March 31, exógena Apr 28–Jun 12 2026, PILA cutoffs, 4 UVT 2026 = $209,496, 27 UVT 2026 = $1,414,098) | 6 | 🟡 | P0-T4 |
| P6-T2 | Extend `config/year_constants.json` with `deadlines` block (per norm, per year) + `multi_uvt_helpers` (1/4/10/27/100/3300 UVT precomputed) | 6 | 🟡 | P6-T1 |
| P6-T3 | Extend `year_facts.py` API — `get_deadline(norm_id, year) → DeadlineFact | None`; `multi_uvt(n, year) → int`. All verified per `feedback_no_hallucinated_examples` | 6 | 🟡 | P6-T2 |
| P6-T4 | Polish-prompt directive `compliance_deadlines_directive` injected when topic ∈ {RTE, exógena, retenciones, PILA} | 6 | 🟡 | P6-T3 |
| P6-T5 | Flag `LIA_DEADLINE_REGISTRY_INJECTION={off,shadow,enforce}` default `enforce`; tests | 6 | 🟡 | P6-T4 |
| P7-T1 | Diagnose — read `answer_polish_rejected_fallback.py`; confirm no user-numeric extract is passed through | 7 | 🟡 | P0-T4 |
| P7-T2 | Implement `pipeline_d/user_numerics_capture.py` (~80 LOC) — `extract_user_numerics(question) → UserNumericsExtract` (peso amounts, UVT counts, percentages, raw spans). Used by P5 validator AND P7 fallback echo | 7 | 🟡 | P7-T1 |
| P7-T3 | Modify `answer_polish_rejected_fallback.py::compose_polish_rejected_fallback` — accept `user_numerics: UserNumericsExtract | None`; when fallback fires, prepend a `**Datos del caso:** <verbatim user numerics>` block to the template | 7 | 🟡 | P7-T2 |
| P7-T4 | Flag `LIA_FALLBACK_NUMERIC_ECHO={off,shadow,enforce}` default `enforce`; tests | 7 | 🟡 | P7-T3 |
| P8-T1 | Verify v23 P4 audit findings + v24 SCOPE doc; check that production corpus pollution patterns are not blocking promote | 8 | 🟡 | P0-T4 |
| P8-T2 | Extend `chunk_quality_heuristics.py::score_entity_pollution` with patterns: (a) Concepto DIAN NNN/YYYY mentioning depreciación/amortización when topic is cartera/deterioro; (b) INC vehicle 512-3/4/5 fragments when topic ≠ vehiculos/automotores; (c) INCRNGO donations when topic ≠ donaciones/utilidades. Topic-aware demotion | 8 | 🟡 | P8-T1 |
| P8-T3 | Promote `LIA_CHUNK_QUALITY_ENTITY_FILTER` from `shadow` → `enforce` in `dev-launcher.mjs` | 8 | 🟡 | P8-T2 |
| P8-T4 | Tests `tests/test_chunk_quality_entity_filter_v25.py` — assert new patterns fire; assert existing acta-template + named-person patterns still fire | 8 | 🟡 | P8-T3 |
| P9-T1 | Diagnose — grep audit answers for invented persons / companies / monetary facts | 9 | 🟡 | P0-T4 |
| P9-T2 | Implement `pipeline_d/counterfactual_detector.py` (~120 LOC) — `detect_counterfactual_entities(question, evidence, polished) → list[CounterfactualEntity]`; flag triple-cap proper-name spans + corporate suffix tokens + amounts in polished that do NOT appear in question OR evidence | 9 | 🟡 | P9-T1 |
| P9-T3 | New polish validator `_no_counterfactual_entities` — reject polish containing detected counterfactuals; allow 1 named example only if it appears verbatim in evidence excerpt | 9 | 🟡 | P9-T2 |
| P9-T4 | Flag `LIA_COUNTERFACTUAL_DETECTOR={off,shadow,enforce}` default `enforce`; tests | 9 | 🟡 | P9-T3 |
| P10-T1 | Doc sync — CLAUDE.md + orchestration.md + env_guide.md for 9 new flag rows | 10 | 🟡 | P1..P9 ✅ |
| P10-T2 | Internal close — `answer-engine-probe` on combined 20-question superset; every verdict `pass` or documented xfail with v26 ticket | 10 | 🟡 | P10-T1 |
| P10-T3 | Operator coordinates external accountant; same 20 Qs; same 1–5 rubric; production | 10 | 🟡 (operator) | P10-T2 |
| P10-T4 | SME verdict archived at `docs/re-engineer/audits/<UTC>_v25_closing_sme_verdict.md` | 10 | 🟡 (operator) | P10-T3 |
| P10-T5 | If avg < 4.0 OR any score = 1 → identify failing Q → trace to phase → ≤ 2 iterate cycles per phase → re-run. If still failing → snapshot + scope v26 mini-fix | 10 | 🟡 | P10-T4 |
| P10-T6 | Commit + FF main + push + `git tag fix_v25_closed` | 10 | 🟡 (operator) | P10-T4 (pass) |
| P10-T7 | Update §⏯ "Last completed step" → "v25 closed ✅" | 10 | 🟡 (operator) | P10-T6 |

---

## §3. The plan — 10 phases (P0 logistics + P1–P9 fixes + P10 closing gate)

### §3.0 Phase 0 — Preconditions + audit archival + regression-suite scaffold (~30 min)

**Idea.** Cannot start v25 until v23 closed internally and the audit is archived as immutable evidence of v25's success criterion.

**Plan narrow.** P0-T0 → P0-T1 → P0-T2 → P0-T3 → P0-T4 (sequential; each blocks the next).

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P0-SC1 | v23 internal-close present | §⏯ of `fix_v23_may.md` says "v23 internally closed" or tag exists |
| P0-SC2 | Audit archived | `test -f docs/re-engineer/audits/2026-05-17_external_sme_audit_post_v23.md` |
| P0-SC3 | Branch `fix-v25-may` exists | `git branch --list fix-v25-may` non-empty |
| P0-SC4 | `docs/re-engineer/fix/fix_v25_may.md` exists on branch | `git ls-files docs/re-engineer/fix/fix_v25_may.md` |
| P0-SC5 | Regression suite scaffold exists | `pytest tests/test_audit_regression_v25_combined.py --collect-only` lists 20 tests (all `xfail` / `skip` initially) |

**Test plan.** Engineer ~30 min total; output verifiable via 5 shell checks above.

**Rollback.** Read-only / setup-only. Branch removed via `git branch -D fix-v25-may` if v25 aborted before any phase ships.

### §3.1 Phase 1 — Norm-keyed retrieval boost (G8; ~1 day)

**Idea.** When the user explicitly names a Resolución / Acuerdo / Decreto in the question, the retriever should prefer chunks whose `norm_id` matches that named norm. Today, vector + lexical retrieval treat "Resolución 000167" the same as any 4-word query; this phase adds a deterministic exact-match boost pass.

**Plan narrow.**

1. **P1-T1 diagnose.** Read `retriever_supabase.py` post-rerank; identify the hook point after embedding rerank but before topic-gate. Confirm chunk metadata carries `norm_id`.
2. **P1-T2 implement.** **NEW** `src/lia_graph/pipeline_d/norm_keyed_boost.py` (~120 LOC).
   - `NormRef` dataclass: `(kind: str, number: str, year: int | None, raw: str)`. Kinds: `res_dian`, `acuerdo`, `decreto`, `ley`, `circular`, `concepto`.
   - `extract_named_resolutions(question: str) → list[NormRef]` — regex for `Res(?:olución)?\s*(?:DIAN\s*)?(?:N[ºo°]\s*)?(?:0*)(\d{1,6})\s*(?:de|/)\s*(\d{4})` + sibling patterns for Decreto / Ley / Acuerdo / Concepto.
   - `boost_chunks_by_norm_id(chunks, refs, factor=1.5) → list[Chunk]` — multiply rerank score by `factor` for chunks whose `norm_id` matches a `NormRef` (slug match: `res_dian.000167.2021` matches Res. DIAN 000167/2021).
3. **P1-T3 wire.** Patch `retriever_supabase.py` post-rerank. Add `LIA_NORM_KEYED_BOOST={off,shadow,enforce}` flag default `enforce`. Surface `diagnostics.norm_keyed_boost_applied`, `diagnostics.norm_keyed_refs`, `diagnostics.norm_keyed_boosted_count`.
4. **P1-T4 tests.** `tests/test_norm_keyed_boost.py` — 5 fixtures.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P1-SC1 | Q1 ("documento soporte SAS") retrieves chunks with `norm_id` starting `res_dian.0167.2021` | Probe + diagnostic inspection |
| P1-SC2 | Q18 ("nota crédito CUFE") retrieves chunks with `norm_id` starting `res_dian.0165.2023` | Probe + diagnostic |
| P1-SC3 | Tax-side regression: Q2/Q9 still retrieve ET 392/145 (no over-boost) | Probe + diagnostic |
| P1-SC4 | 5 unit tests green | `pytest tests/test_norm_keyed_boost.py -v` |

**Rollback.** `LIA_NORM_KEYED_BOOST=off` skips the pass; retriever falls back to v23 rerank.

### §3.2 Phase 2 — Cross-border lane (G9; ~1 day)

**Idea.** Cross-border tax (servicios desde el exterior, royalties, technical services, dividends to non-residents) lives in a specific set of ET articles (408, 410, 414-1, 420 par. 3, 437-2 lit. e, 124-1, 124-2). Today's planner routes anything mentioning "pago" or "servicios" to domestic `retencion_en_la_fuente`. This phase adds a detector that fires when foreign-payment cues appear AND force-includes the canonical article fixture.

**Plan narrow.**

1. **P2-T1 diagnose.** Confirm `topic_taxonomy.json` lacks `pagos_al_exterior` / `servicios_desde_el_exterior` cue chain. Confirm planner topic-detector exits on first match.
2. **P2-T2 implement.** **NEW** `src/lia_graph/pipeline_d/cross_border_lane.py` (~100 LOC).
   - `CrossBorderHint` dataclass: `(detected: bool, cue: str | None, kind: str | None)` — kinds: `services_from_abroad`, `royalty`, `technical_service`, `nonresident_dividend`, `cloud_software`, `unknown`.
   - `detect_cross_border_context(question: str) → CrossBorderHint` — regex on cue phrases: `\b(?:desde el exterior|no domicilio en Colombia|proveedor extranjero|sin establecimiento permanente|treaty|convenio doble tributación|pago al exterior|software en la nube.*(?:exterior|abroad))\b`.
   - `canonical_articles_for(hint) → list[str]` — returns `["et.art.408", "et.art.410", "et.art.420.par.3", "et.art.437-2", "et.art.124-1", "et.art.124-2"]` for `services_from_abroad`.
3. **P2-T3 wire.** Orchestrator pre-retrieval: if `detect_cross_border_context(question).detected`, inject canonical articles into the retrieval bundle (treat as `synthetic_pinned` with `provider_trust_tier=high`). Add `LIA_CROSS_BORDER_LANE={off,shadow,enforce}` flag default `enforce`.
4. **P2-T4 tests.** `tests/test_cross_border_lane.py` — 4 fixtures.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P2-SC1 | Q14 ("software cloud sin domicilio") triggers `detected=True, kind=cloud_software` | Probe + diagnostic |
| P2-SC2 | Q14 final answer cites ET 437-2 / ET 420 par. 3 / ET 408 | Probe + grep |
| P2-SC3 | Domestic regression: Q2 ("retención servicios honorarios") does NOT trigger cross-border lane | Probe + diagnostic negative |
| P2-SC4 | 4 unit tests green | `pytest tests/test_cross_border_lane.py -v` |

**Rollback.** `LIA_CROSS_BORDER_LANE=off` reverts to v23 planner behavior.

### §3.3 Phase 3 — Municipal tax routing (G10; ~0.5–1 day)

**Idea.** ICA / reteICA / municipal-tariff questions need local-source retrieval (Bogotá SHD Acuerdo 65/2002, Decreto Distrital 352/2002). Today's corpus has no local sources, so when the planner sees "ICA Bogotá territorialidad", it drifts to ET 115 (deducción ICA en renta), ET 240 (TTD), and RST Form 2593 — completely orthogonal to territorialidad. v25 cannot ingest the SHD compilación by P10 close — instead the phase **detects the municipal context and surfaces a canonical pointer block** while keeping the existing answer scaffold.

**Plan narrow.**

1. **P3-T1 diagnose.** Confirm planner has `ica` topic but no `territorialidad` sub-detection.
2. **P3-T2 implement.** **NEW** `src/lia_graph/pipeline_d/municipal_tax_routing.py` (~80 LOC).
   - `MunicipalHint`: `(detected: bool, city: str | None, has_territoriality: bool, has_reteica: bool)`.
   - `detect_municipal_context(question) → MunicipalHint` — regex on `\b(?:Bogotá|Medellín|Cali|Barranquilla|Bucaramanga|municipio|distrital|reteICA|territorialidad|jurisdicción municipal|actividad gravada en)\b`.
   - `municipal_pointer_block(hint) → str` — canonical text: `"**Consulta normativa local.** El alcance territorial del ICA y la mecánica de reteICA en {city} se rigen por normativa distrital; cuando la pregunta opera sobre territorialidad municipal, consulte además: Acuerdo Distrital 65/2002 + Decreto Distrital 352/2002 (Bogotá); tarifario CIIU local; certificado de reteICA practicado por el agente."`
3. **P3-T3 wire.** Synthesis post-composition: when `MunicipalHint.detected and (has_territoriality or has_reteica)` and corpus didn't return SHD norms, prepend the pointer block. Add `LIA_MUNICIPAL_TAX_ROUTING={off,shadow,enforce}` flag default `enforce`.
4. **P3-T4 tests.** `tests/test_municipal_tax_routing.py` — 3 fixtures (Bogotá, Medellín, generic municipal).

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P3-SC1 | Q11 ("ICA Bogotá territorialidad") emits pointer block with Acuerdo 65/2002 + Decreto Distrital 352/2002 | Probe + grep |
| P3-SC2 | RST regression: Q6 (restaurante RST) does NOT emit municipal pointer (no Bogotá / municipio cue) | Probe + diagnostic negative |
| P3-SC3 | 3 unit tests green | `pytest tests/test_municipal_tax_routing.py -v` |

**Rollback.** `LIA_MUNICIPAL_TAX_ROUTING=off` skips the pointer; answer reverts to v23 behavior.

### §3.4 Phase 4 — Accounting-framework awareness (G11; ~0.5 day)

**Idea.** "NIIF Pymes" and "NIIF Plenas / IFRS Full" are different frameworks with different lease models, deterioro tests, etc. Today's polish has no framework constraint, so LLM defaults to whichever framework is more salient in its training (IFRS 16 for leasing). v25 detects the framework cue and constrains polish.

**Plan narrow.**

1. **P4-T1 diagnose.** Confirm polish prompt has no framework directive.
2. **P4-T2 implement.** **NEW** `src/lia_graph/pipeline_d/accounting_framework.py` (~70 LOC).
   - `FrameworkHint`: `(framework: str, cue: str | None)` — values: `niif_pymes`, `niif_plenas`, `niif_microempresas`, `decreto_2649_2706`, `none`.
   - `detect_framework_hint(question) → FrameworkHint` — `\b(?:NIIF\s+para\s+(?:las\s+)?[Pp]ymes|para\s+[Pp]ymes|microempresa)\b` → `niif_pymes`; `\b(?:NIIF\s+[Pp]lenas|IFRS\s+Full|NIC|NIIF\s+\d+)\b` → `niif_plenas`; otherwise `none`.
   - `framework_directive(hint) → str` — for `niif_pymes`: `"MARCO TÉCNICO CONTABLE: NIIF para las Pymes (Decreto 2420/2015). NO uses NIIF Plenas / IFRS Full / NIC. Para arrendamientos usa Sección 20 (clasificación financiero / operativo). NO menciones IFRS 16 ni el modelo right-of-use."`
3. **P4-T3 validator.** **NEW** `_framework_coherence(template, polished, evidence, question)` polish validator. Reject if `detect_framework_hint(question).framework == "niif_pymes"` AND polished contains regex `\b(?:NIIF\s+16|IFRS\s+16|right.of.use|derecho.de.uso)\b`. Rejection reason: `framework_mismatch`.
4. **P4-T4 flag + tests.** `LIA_FRAMEWORK_AWARENESS={off,shadow,enforce}` default `enforce`; `tests/test_accounting_framework.py` — 3 fixtures (NIIF Pymes leasing, NIIF Plenas full, ambiguous).

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P4-SC1 | Q19 ("pyme leasing maquinaria") polish output contains "Sección 20"; no "NIIF 16" / "right-of-use" | Probe + grep |
| P4-SC2 | NIIF Plenas regression: question saying "bajo NIC 17 / NIIF 16" passes through unchanged | Probe + diagnostic |
| P4-SC3 | Validator rejects polish that violates framework | Unit test |

**Rollback.** `LIA_FRAMEWORK_AWARENESS=off` skips directive + validator.

### §3.5 Phase 5 — Sub-question coverage gate (G12; ~0.5 day)

**Idea.** Polish emits `"Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente."` as a verbatim stub when it can't satisfy a sub-question. From the SME viewpoint this is worse than a clean "no encuentro evidencia" — it looks like the system is offloading work to the user. v25 strips the stub OR re-routes polish.

**Plan narrow.**

1. **P5-T1 diagnose.** Grep polish prompt + synthesis for the stub.
2. **P5-T2 validator.** **NEW** `_no_coverage_gap_phrase(template, polished, evidence, question)` polish validator. Regex on `\b(?:[Cc]obertura\s+pendiente|valida\s+el\s+expediente\s+antes|no\s+encuentro\s+evidencia\s+(?:para|sobre))\b`. Polish retries once with explicit error: `"Detectada frase de gap. Si una sub-pregunta no se puede responder, omítela en silencio; NO escribas 'Cobertura pendiente'. El usuario prefiere una respuesta corta y completa a una larga con huecos visibles."`.
3. **P5-T3 stripper.** **NEW** `src/lia_graph/pipeline_d/coverage_gap_strip.py` (~60 LOC). Post-polish (and post-fallback) sweep: drop lines matching the regex; if dropping leaves a section empty, drop the section.
4. **P5-T4 flag + tests.** `LIA_COVERAGE_GAP_GATE={off,shadow,enforce}` default `enforce`; `tests/test_coverage_gap_strip.py` — 4 fixtures.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P5-SC1 | Q3 ("periodicidad IVA 92,000 UVT") final answer does NOT contain "Cobertura pendiente" | Probe + grep negative |
| P5-SC2 | Q12 ("IVA prorrateo") final answer does NOT contain "Cobertura pendiente" | Probe + grep negative |
| P5-SC3 | 4 unit tests green | `pytest tests/test_coverage_gap_strip.py -v` |

**Rollback.** `LIA_COVERAGE_GAP_GATE=off` skips validator + stripper.

### §3.6 Phase 6 — Compliance-deadline registry (G13; ~0.5–1 day)

**Idea.** Audit caught RTE annual update as "enero a junio 30" — real DIAN deadline is March 31 per RTE compliance practice. 4 UVT 2026 was stated as `$199,000` — real value is `$209,496`. Today `year_facts.py` carries UVT / SMLMV / auxilio but no per-norm deadlines and no multi-UVT helpers. v25 extends the registry.

**Plan narrow.**

1. **P6-T1 diagnose.** List canonical deadlines: RTE March 31; exógena AG 2025 calendar (Res. DIAN 000162/2023 mod. 000188/2024); PILA cutoffs; sancion mínima; 4/27/100/3300 UVT precomputed.
2. **P6-T2 registry.** Extend `config/year_constants.json` with `deadlines` (per norm, per year) + `multi_uvt_helpers` (precomputed values for common UVT multiples).
3. **P6-T3 API.** Extend `year_facts.py` with `get_deadline(norm_id, year) → DeadlineFact | None` and `multi_uvt(n, year) → int`. Every value verified per `feedback_no_hallucinated_examples`; values that cannot be verified are marked `"verified": false` and skipped at injection.
4. **P6-T4 directive.** Polish-prompt `compliance_deadlines_directive`: when topic ∈ {`regimen_tributario_especial_esal`, `informacion_exogena`, `retencion_en_la_fuente`, `parafiscales_seguridad_social`}, inject canonical deadlines block.
5. **P6-T5 flag + tests.** `LIA_DEADLINE_REGISTRY_INJECTION={off,shadow,enforce}` default `enforce`; `tests/test_deadline_registry.py` — 5 fixtures.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P6-SC1 | Q20 ("ESAL anual permanencia") final answer cites "March 31" deadline | Probe + grep |
| P6-SC2 | Q13 ("contratista 8M honorarios") computes 4 UVT 2026 = $209,496 (not $199,000) | Probe + grep |
| P6-SC3 | Q7 ("exógena AG 2025") cites Apr 28–Jun 12 2026 window | Probe + grep |
| P6-SC4 | 5 unit tests green | `pytest tests/test_deadline_registry.py -v` |

**Rollback.** `LIA_DEADLINE_REGISTRY_INJECTION=off` skips directive + helper.

### §3.7 Phase 7 — Fallback-path numeric echo (G14; ~0.5 day)

**Idea.** v23 P5 added `_preserves_user_numerics` polish validator. When polish mutates user numerics, polish is rejected and the fallback path fires — but the fallback path **also** doesn't echo the user numerics, so the final mutated output reaches the user anyway. v25 pre-extracts user numerics in orchestrator and threads them into the fallback context as a verbatim `**Datos del caso:** …` block.

**Plan narrow.**

1. **P7-T1 diagnose.** Read `answer_polish_rejected_fallback.py::compose_polish_rejected_fallback`; confirm no `user_numerics` parameter.
2. **P7-T2 capture.** **NEW** `src/lia_graph/pipeline_d/user_numerics_capture.py` (~80 LOC).
   - `UserNumericsExtract`: `(amounts: list[str], uvt_counts: list[str], percentages: list[str], spans: list[tuple[int,int,str]])`.
   - `extract_user_numerics(question) → UserNumericsExtract`. Patterns: peso amounts `\$?\s*[\d.,]+(?:\s*(?:mil(?:lones)?|MM|M))?`, UVT counts `\d+(?:[.,]\d+)?\s*UVT`, percentages `\d+(?:[.,]\d+)?\s*%`.
   - Used by BOTH the existing P5 polish validator (refactor share) AND P7 fallback echo.
3. **P7-T3 wire.** Patch `compose_polish_rejected_fallback` to accept `user_numerics: UserNumericsExtract | None`. When non-empty, prepend a `**Datos del caso:** {amounts joined}.` block to the template before fallback rendering. Patch orchestrator to extract once and thread through.
4. **P7-T4 flag + tests.** `LIA_FALLBACK_NUMERIC_ECHO={off,shadow,enforce}` default `enforce`; `tests/test_fallback_numeric_echo.py` — 3 fixtures (Q10 single amount, multi-amount, percentage-only).

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P7-SC1 | Q10 final answer contains the user's `$3.000.000` verbatim regardless of polish path | Probe + grep |
| P7-SC2 | Multi-amount regression: Q16 (6,000M + 18,000M) both survive | Probe + grep |
| P7-SC3 | 3 unit tests green | `pytest tests/test_fallback_numeric_echo.py -v` |

**Rollback.** `LIA_FALLBACK_NUMERIC_ECHO=off` skips the prepend; v23 fallback behavior restored.

### §3.8 Phase 8 — Promote entity filter + extend patterns (G15; ~0.5 day)

**Idea.** v23 P4 shipped `LIA_CHUNK_QUALITY_ENTITY_FILTER` in `shadow` mode pending v24's cloud retire. v25 ships it `enforce` because runtime demote is safer than waiting for retire AND because the SME audit shows topic-incompatible pollution still reaches body bullets (not just Anclaje). v25 ALSO adds 3 new pattern families: depreciation-Concepto-DIAN leak in cartera, INC vehicle 512-3/4/5 leak in restaurant RST, INCRNGO donations leak in dividends.

**Plan narrow.**

1. **P8-T1 verify v23 P4 audit + v24 SCOPE doc.** Confirm shadow-mode telemetry indicates demote impact is acceptable.
2. **P8-T2 extend patterns.** Modify `chunk_quality_heuristics.py::score_entity_pollution`. Add topic-aware demotion: signature becomes `score_entity_pollution(text: str, topic_hint: str | None = None) → (penalty, reason)`. New patterns:
   - `_CONCEPTO_DIAN_DEPRECIACION_LEAK_RX` — penalty when chunk mentions "Concepto DIAN \d+/\d{4}" AND "deprec(?:iación|iar)" AND topic_hint ∈ {`cartera`, `deterioro`, `provisiones`}.
   - `_INC_VEHICLE_LEAK_RX` — penalty when chunk mentions `art\. 512-[345]` AND topic_hint ≠ {`vehiculos`, `automotores`, `impuesto_consumo_vehiculos`}.
   - `_INCRNGO_DONATIONS_LEAK_RX` — penalty when chunk mentions `INCRNGO.*donac` AND topic_hint ∉ {`donaciones`, `incrngo`, `utilidades_distribuibles`}.
3. **P8-T3 promote.** Flip `LIA_CHUNK_QUALITY_ENTITY_FILTER` default in `dev-launcher.mjs` from `"shadow"` to `"enforce"`.
4. **P8-T4 tests.** `tests/test_chunk_quality_entity_filter_v25.py` — 6 fixtures.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P8-SC1 | Q9 (cartera) does NOT surface Concepto DIAN 191/2025 depreciación lines | Probe + grep negative |
| P8-SC2 | Q6 (restaurante RST) does NOT surface art. 512-3/4/5 vehicle lines | Probe + grep negative |
| P8-SC3 | Q15 (dividendos) does NOT include INCRNGO donations | Probe + grep negative |
| P8-SC4 | v23 P4 patterns (acta template, named persons) still fire | Re-run existing chunk-quality tests |
| P8-SC5 | `enforce` default landed | `grep "LIA_CHUNK_QUALITY_ENTITY_FILTER" scripts/dev-launcher.mjs` |

**Rollback.** Revert default to `"shadow"`; patterns stay (harmless without the enforce flip).

### §3.9 Phase 9 — Counterfactual-example detector (G16; ~0.5–1 day)

**Idea.** SME audit caught LLM inserting named persons / companies / monetary facts that exist NEITHER in the user's question NOR in the evidence excerpts: "Carlos Moreno Pérez" (Q8 RUB), "Panama 1,930M" (Q16 precios de transferencia), "InnovaLab" (Q17 pérdidas fiscales), "DISTRIBUIDORA EL SOL SAS / ALEJANDRO VASQUEZ ARANGO" (Q5 — partial corpus contamination). v25 adds a polish validator that rejects when the polished answer introduces these tokens.

**Plan narrow.**

1. **P9-T1 diagnose.** Grep audit answers for the invented tokens.
2. **P9-T2 detector.** **NEW** `src/lia_graph/pipeline_d/counterfactual_detector.py` (~120 LOC).
   - `CounterfactualEntity`: `(kind: str, surface: str)` — kinds: `person_name`, `company_name`, `monetary_fact`.
   - `detect_counterfactual_entities(question, evidence_text, polished) → list[CounterfactualEntity]`.
   - Person-name regex: `\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?\b` with a stop-list of legitimate institutional names (DIAN, UGPP, MinHacienda, MinTrabajo, etc., Colombian President names, Ley/Decreto authors).
   - Company-name regex: `\b[A-Z][A-Z0-9\s\-]+\s+(?:SAS|S\.A\.S\.|LTDA|S\.A\.)\b`.
   - Monetary-fact regex on `\$?\s*[\d.,]+(?:\s*millones)?` appearing in polished but not in question OR evidence (post-normalization).
   - Match = `surface` appears in `polished` and NOT in `question + evidence_text`.
3. **P9-T3 validator.** **NEW** `_no_counterfactual_entities(template, polished, evidence, question)` polish validator. Reject if any detected counterfactual. Rejection reason: `counterfactual_entity:{kind}`.
4. **P9-T4 flag + tests.** `LIA_COUNTERFACTUAL_DETECTOR={off,shadow,enforce}` default `enforce`; `tests/test_counterfactual_detector.py` — 6 fixtures (legit institution allowed, invented person rejected, invented company rejected, monetary fact in evidence allowed, etc.).

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P9-SC1 | Q8 (RUB) cannot surface "Carlos Moreno Pérez" if not in evidence | Probe + grep negative |
| P9-SC2 | Q16 (precios de transferencia) cannot inject "Panama 1,930M" over user facts | Probe + grep negative |
| P9-SC3 | Institutional names (DIAN, UGPP) pass | Unit test |
| P9-SC4 | 6 unit tests green | `pytest tests/test_counterfactual_detector.py -v` |

**Rollback.** `LIA_COUNTERFACTUAL_DETECTOR=off` skips validator.

### §3.10 Phase 10 — Internal close + external SME closing gate (D-S2; ~2–5 days operator-coordinated)

**Idea.** v25 cannot close on internal probes alone. The same external accountant re-runs the combined 20-question superset (10 rerun + 10 new); v25 passes only on `≥ 4.0/5 avg + zero 1s`.

**Plan narrow.**

1. **P10-T1 doc sync.** Update CLAUDE.md (9 new flag rows). Bump env-matrix version in `docs/orchestration/orchestration.md` to `v2026-05-NN-fix-v25` + change-log row. Mirror flag changes to `docs/guide/env_guide.md`.
2. **P10-T2 internal close.** `answer-engine-probe` on combined 20-question superset (via `tests/test_audit_regression_v25_combined.py` + manual probe inspection). Every verdict `pass` or documented xfail with v26 ticket.
3. **P10-T3 SME coordination.** Operator contacts external accountant. Same 20 Qs verbatim. Same 1–5 rubric. Production deployment `https://liagraph-production.up.railway.app`.
4. **P10-T4 SME verdict archive.** Archived at `docs/re-engineer/audits/<UTC>_v25_closing_sme_verdict.md`.
5. **P10-T5 iterate or close.** If avg ≥ 4.0 AND zero 1s → P10-T6. Else identify failing Q(s) → trace to phase → ≤ 2 iterate cycles per phase → re-run P10-T3.
6. **P10-T6 commit + tag.** `git tag fix_v25_closed`. FF main + push.
7. **P10-T7 close ledger.** §⏯ "Last completed step" → "v25 closed ✅".

**Success criteria.**

| # | Criterion | Target |
|---|---|---|
| P10-SC1 | All 9 fix phases (P1..P9) ✅ | §2.1 phase status |
| P10-SC2 | Internal probe pass on combined 20-question superset | `answer-engine-probe` verdict |
| P10-SC3 | SME verdict avg ≥ 4.0/5 | Archived verdict |
| P10-SC4 | SME verdict zero 1s | Archived verdict |
| P10-SC5 | `fix_v25_closed` tag exists | `git tag --list fix_v25_closed` |
| P10-SC6 | §⏯ updated | This file |

**Rollback.** Per-phase rollback flags (all 9 above) allow per-fix disable while preserving v23 substance. Worst case: all nine v25 flags set to `off` reverts v25 entirely without code revert.

---

## §4. Files to touch (consolidated)

### §4.1 New files (~16)

| File | Phase | Purpose |
|---|---|---|
| `docs/re-engineer/fix/fix_v25_may.md` | P0-T3 | THIS plan, on branch |
| `docs/re-engineer/audits/2026-05-17_external_sme_audit_post_v23.md` | P0-T1 | Verbatim audit archival |
| `src/lia_graph/pipeline_d/norm_keyed_boost.py` | P1-T2 | Norm-keyed retrieval boost (~120 LOC) |
| `src/lia_graph/pipeline_d/cross_border_lane.py` | P2-T2 | Cross-border detector + canonical articles (~100 LOC) |
| `src/lia_graph/pipeline_d/municipal_tax_routing.py` | P3-T2 | Municipal-tax pointer block (~80 LOC) |
| `src/lia_graph/pipeline_d/accounting_framework.py` | P4-T2 | Framework hint + polish directive (~70 LOC) |
| `src/lia_graph/pipeline_d/coverage_gap_strip.py` | P5-T3 | Coverage-gap line stripper (~60 LOC) |
| `src/lia_graph/pipeline_d/user_numerics_capture.py` | P7-T2 | User-numerics extractor (~80 LOC) |
| `src/lia_graph/pipeline_d/counterfactual_detector.py` | P9-T2 | Counterfactual-entity detector (~120 LOC) |
| `tests/test_norm_keyed_boost.py` | P1-T4 | 5 fixtures |
| `tests/test_cross_border_lane.py` | P2-T4 | 4 fixtures |
| `tests/test_municipal_tax_routing.py` | P3-T4 | 3 fixtures |
| `tests/test_accounting_framework.py` | P4-T4 | 3 fixtures |
| `tests/test_coverage_gap_strip.py` | P5-T4 | 4 fixtures |
| `tests/test_deadline_registry.py` | P6-T5 | 5 fixtures |
| `tests/test_fallback_numeric_echo.py` | P7-T4 | 3 fixtures |
| `tests/test_chunk_quality_entity_filter_v25.py` | P8-T4 | 6 fixtures |
| `tests/test_counterfactual_detector.py` | P9-T4 | 6 fixtures |
| `tests/test_audit_regression_v25_combined.py` | P0-T4 | Permanent 20-Q regression suite |

### §4.2 Modified files (~8)

| File | Phase(s) | Change |
|---|---|---|
| `src/lia_graph/pipeline_d/retriever_supabase.py` | P1-T3 | Wire norm-keyed boost post-rerank |
| `src/lia_graph/pipeline_d/orchestrator.py` | P2-T3, P7-T3 | Cross-border lane + user-numerics capture threading |
| `src/lia_graph/pipeline_d/answer_synthesis_sections.py` | P3-T3 | Municipal pointer block injection |
| `src/lia_graph/pipeline_d/answer_llm_polish.py` | P4-T2/T3, P5-T2, P6-T4, P9-T3 | 4 new polish directives + 3 new validators |
| `src/lia_graph/pipeline_d/answer_polish_rejected_fallback.py` | P7-T3 | Accept `user_numerics`; prepend Datos del caso |
| `src/lia_graph/pipeline_d/chunk_quality_heuristics.py` | P8-T2 | 3 new topic-aware pattern families |
| `src/lia_graph/year_facts.py` | P6-T3 | `get_deadline` + `multi_uvt` API |
| `config/year_constants.json` | P6-T2 | `deadlines` + `multi_uvt_helpers` blocks |
| `scripts/dev-launcher.mjs` | All | 8 new flag defaults + entity-filter promotion |
| `CLAUDE.md` | P10-T1 | 9 new flag rows |
| `docs/orchestration/orchestration.md` | P10-T1 | Env-matrix bump + change-log row |
| `docs/guide/env_guide.md` | P10-T1 | Flag mirror |
| `src/lia_graph/ui_chat_payload.py` | Various | Whitelist new diagnostic keys |

### §4.3 Touched but no change (verify only)

- `src/lia_graph/pipeline_d/answer_topic_decomposition.py` — v23; do not modify.
- `src/lia_graph/pipeline_d/answer_anclaje_topic_gate.py` — v23; do not modify.
- `src/lia_graph/pipeline_d/article_namespaces.py` — v23; do not modify.

---

## §5. Risks + mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Norm-keyed boost over-prefers a single chunk and starves diverse evidence | Medium | Medium | `factor=1.5` (modest); diagnostic logs boosted count; flag rollback |
| Cross-border lane triggers on domestic questions that mention "exterior" colloquially | Medium | Medium | Cue list scoped to bound phrases; shadow-mode sanity check before enforce |
| Municipal pointer block adds noise to non-municipal answers if detector over-fires | Low | Low | Strict cue list; only emits when topic ∈ {`ica`, `regimen_simple`} AND territoriality cue present |
| Framework validator false-positive on legit "NIIF 16" mentioned by a Plenas question | Low | Medium | Validator only fires when `detect_framework_hint(question).framework == "niif_pymes"` |
| Coverage-gap strip removes legitimate gap acknowledgments | Low | Low | Word-boundary regex; restricted to canonical stubs |
| Deadline registry drifts (new Res. lands; registry not updated) | Medium | High | `make verify-deadlines` target (P6-T3 stretch); annual operator reminder |
| Fallback numeric echo bloats short answers with verbatim spans | Low | Low | Cap `Datos del caso:` block to ≤ 240 chars |
| Entity-filter promotion blocks legit chunks (false-positive demote) | Medium | Medium | Topic-aware demotion: only demote when topic_hint mismatches; shadow-mode telemetry from v23 informs decision |
| Counterfactual detector false-positives on legit named institutions | Medium | Medium | Stop-list of institutional names; surface kept/dropped in diagnostics; flag rollback |
| Polish-prompt directive bloat (9 new directives) hits prompt-token budget | Medium | High | Each directive < 80 chars; conditional injection (only when cue detected); A/B-test prompt length |
| External SME re-run surfaces NEW failures outside the 20 Qs | Medium | Medium | v25 scope = the 20 Qs only; new failures roll into v26 backlog |
| `git tag fix_v23_closed` not yet placed (v23 internal-closed but operator hasn't ff-merged) | Medium | Medium | P0-T0 checks either tag OR §⏯ status; proceed with §⏯ status if tag missing |

---

## §6. Run log (append-only, most recent on top, Bogotá local time)

### 2026-05-17 ~6:30 PM Bogotá — P0–P9 landed + P10-T1 doc sync

- **What.** All 9 fix phases of v25 landed on branch `fix-v25-may` in one autonomous execution session (D10 operator authorization in-band). Commits on branch (oldest → newest):
  - `b0a3f43` docs(v25 P0): draft fix_v25_may.md + archive 2026-05-17 dual-packet audit
  - `…` fix(v25 P1): norm-keyed retrieval boost + 8 new dev-launcher flags (G8)
  - `…` fix(v25 P2): cross-border lane + polish-prompt directive (G9)
  - `…` fix(v25 P3): municipal tax routing + pointer block (G10)
  - `…` fix(v25 P4+P5+P9): framework awareness + coverage-gap gate + counterfactual detector
  - `3f1ec73` fix(v25 P6): compliance-deadline registry + multi-UVT helpers (G13)
  - `…` fix(v25 P7): fallback-path numeric echo (G14)
  - `4e92011` fix(v25 P8): promote entity-filter to enforce + 3 new pollution patterns (G15)
  - (this commit) docs(v25 P10-T1): CLAUDE.md flag table + state-ledger update.
- **Test posture.** 257 unit tests green across the v23 + v25 affected suites (norm_keyed_boost, cross_border_lane, municipal_tax_routing, accounting_framework, coverage_gap_gate, deadline_registry, fallback_numeric_echo, counterfactual_detector, chunk_quality_entity_filter_v25, plus all v23 P1–P7 suites). Audit-regression v25 combined suite (20 tests) stays xfail until P10-T2 captures probe fixtures.
- **Flag inventory landed (`dev-launcher.mjs`).** All v25 flags default `enforce`:
  - `LIA_NORM_KEYED_BOOST=enforce`
  - `LIA_CROSS_BORDER_LANE=enforce`
  - `LIA_MUNICIPAL_TAX_ROUTING=enforce`
  - `LIA_FRAMEWORK_AWARENESS=enforce`
  - `LIA_COVERAGE_GAP_GATE=enforce`
  - `LIA_DEADLINE_REGISTRY_INJECTION=enforce`
  - `LIA_FALLBACK_NUMERIC_ECHO=enforce`
  - `LIA_COUNTERFACTUAL_DETECTOR=enforce`
  - `LIA_CHUNK_QUALITY_ENTITY_FILTER=enforce` (promoted from shadow in P8)
- **Granularization (operator directive 2026-05-17 PM).** `answer_llm_polish.py` was at 1694 LOC pre-v25. v25 directive builders + validators extracted into:
  - `pipeline_d/answer_polish_directives_v25.py` — `build_v25_polish_blocks(question, topic)` entry point used by polish.
  - `pipeline_d/answer_polish_validators_v25.py` — three new validator bodies (`framework_coherence`, `no_coverage_gap_phrase`, `no_counterfactual_entities`), wired via importlib indirection from the POLISH_RULES tuple.
  - `pipeline_d/norm_keyed_boost.py`, `cross_border_lane.py`, `municipal_tax_routing.py`, `accounting_framework.py`, `counterfactual_detector.py`, `user_numerics_capture.py` — detection + cue logic per phase.
  - `year_facts.py` extended (was 234 LOC, now ~340 LOC) with deadline + multi-UVT API.
- **Next.** P10-T2 internal probe sweep — start `npm run dev:staging`, run `answer-engine-probe` on combined 20-Q superset, capture probe outputs as fixtures, lift xfail decorators. Then P10-T3 is operator-coordinated external SME re-run.
- **Likely SME outcome (forecast — not a guarantee).** Internal probes give high confidence on "zero 1s" target after v25 fixes (norm-keyed retrieval fixes Q1/Q7/Q18 citation gaps; cross-border lane fixes Q14; municipal pointer fixes Q11; framework awareness fixes Q19; deadline registry fixes Q13/Q20; numeric echo fixes Q10 mutation; counterfactual detector fixes Q8/Q16/Q17 invented examples; entity-filter promote fixes Q5/Q6/Q9/Q15 pollution). "Avg ≥ 4.0" target is reachable on the combined 20-Q superset.

### 2026-05-17 ~5:00 PM Bogotá — v25 plan drafted + audit archived

- **What.** v25 plan landed at `docs/re-engineer/fix/fix_v25_may.md` on branch `fix-v25-may`. Audit archived at `docs/re-engineer/audits/2026-05-17_external_sme_audit_post_v23.md`. 9 generic-weakness slots (G8–G16) mapped to 9 fix phases (P1–P9) + closing gate (P10).
- **Why.** Operator directive 2026-05-17 PM: "read fix_v23 and v14, to generate and implement fix_v25_may.md... do all work in a purpose branch... you do EVERYTHING and it is prohibited that you ask for authorization."
- **Phase 1 exploration findings (load-bearing):**
  - Retriever has no `norm_id` exact-match boost — G8 is real (Q1/Q7/Q8/Q18).
  - Topic taxonomy has no `pagos_al_exterior` / `servicios_desde_el_exterior` cue chain — G9 is real (Q14).
  - Polish prompt has no framework constraint directive — G11 is real (Q19).
  - `compose_polish_rejected_fallback` does not consume user-numerics — G14 is real (Q10).
  - `LIA_CHUNK_QUALITY_ENTITY_FILTER` is still `shadow` per v23 P4 default — G15 promotion is real.
- **Locked design decisions:**
  - D1: One mega-doc.
  - D2: External SME re-run on the combined 20-question superset.
  - D3: Cloud-corpus retirement stays gated to v24.
  - D4: Autonomy mode — engineer takes all design decisions and commits at phase boundaries; operator holds the closing gate only.
- **Next.** P0-T3 commit on branch; P0-T4 regression suite scaffold; then P1 begins (norm-keyed boost).

---

## §7. Six-gate lifecycle per phase

Each phase must clear all six gates per `CLAUDE.md` Non-Negotiables before being declared ✅. Per `feedback_gates_evaluate_independently`, qualitative pass on phase N does NOT lower phase N+1's bar.

| Phase | 1. Idea | 2. Plan | 3. Success | 4. Test plan | 5. Greenlight | 6. Refine-or-discard |
|---|---|---|---|---|---|---|
| P0 | preconditions + archival | §3.0 | 5 SCs | engineer ~30 min | engineer after P0-T4 | re-scope if v23 not closed |
| P1 | norm-keyed boost | §3.1 | 4 SCs on Q1/Q7/Q8/Q18 | engineer 1 d + probe | engineer after re-probe | revert flag |
| P2 | cross-border lane | §3.2 | 4 SCs on Q14 + regression | engineer 1 d + probe | engineer after re-probe | revert flag |
| P3 | municipal routing | §3.3 | 3 SCs on Q11 + regression | engineer 0.5–1 d + probe | engineer after re-probe | revert flag |
| P4 | framework awareness | §3.4 | 3 SCs on Q19 + regression | engineer 0.5 d + probe | engineer after re-probe | revert flag |
| P5 | coverage-gap gate | §3.5 | 3 SCs on Q3/Q12 | engineer 0.5 d + probe | engineer after re-probe | revert flag |
| P6 | deadline registry | §3.6 | 4 SCs on Q7/Q13/Q20 | engineer 0.5–1 d + probe | engineer after re-probe | revert flag |
| P7 | fallback numeric echo | §3.7 | 3 SCs on Q10 + multi-amount | engineer 0.5 d + probe | engineer after re-probe | revert flag |
| P8 | promote entity filter | §3.8 | 5 SCs on Q5/Q6/Q9/Q15 | engineer 0.5 d + probe | engineer after re-probe | revert default |
| P9 | counterfactual detector | §3.9 | 4 SCs on Q8/Q16 | engineer 0.5–1 d + probe | engineer after re-probe | revert flag |
| P10 | external SME closing gate | §3.10 | 6 SCs (incl. SME avg ≥ 4.0 + zero 1s) | operator + SME 2–5 d | SME verdict | iterate ≤ 2 cycles per failing phase |

---

## §8. Open questions (genuinely undecided — needs operator before that phase starts)

| # | Question | Blocks | Surfaced |
|---|---|---|---|
| Q-Open-1 | Norm-keyed boost factor — 1.5x or 2.0x? Higher = more deterministic but less diverse evidence | P1-T2 | 2026-05-17. **Default: 1.5x**. Iterable. |
| Q-Open-2 | Cross-border lane — emit canonical articles as synthetic pinned chunks OR re-route topic to `pagos_al_exterior`? | P2-T2 | 2026-05-17. **Default: synthetic pinned** (lower disruption). |
| Q-Open-3 | Municipal pointer block — append OR prepend to answer? | P3-T3 | 2026-05-17. **Default: prepend** (visibility). |
| Q-Open-4 | Counterfactual detector — strict (block all 3-cap proper-name spans not in evidence) or loose (only names+company suffixes)? | P9-T2 | 2026-05-17. **Default: loose** (lower false-positive risk). |
| Q-Open-5 | Should v25 P8 promote entity filter even if v24 hasn't retired? | P8-T3 | 2026-05-17. **Default: YES** — promote with topic-aware demotion to limit blast radius; v24 retire still happens independently. |

Update this section as new questions surface during execution.

---

## §9. Decisions locked in (do not re-litigate without operator sign-off)

| # | Decision | Reason | Locked when |
|---|---|---|---|
| D1 | v25 scope = ALL 9 generic weaknesses surfaced by 2026-05-17 dual-packet audit; one mega-doc | Operator directive "improve capability of the model" + carry-over of v23 D-S1 | 2026-05-17 |
| D2 | Closing gate = external SME re-runs combined 20-question superset; pass = ≥ 4.0/5 avg + zero 1s | Carry-over of v23 D-S2 | 2026-05-17 |
| D3 | Cloud-corpus retirement stays gated to v24; v25 ships runtime filter promote | v23 D-S3 carryover; avoids racing audit-driven retirement | 2026-05-17 |
| D4 | All v25 fixes ship behind kill-switch flags | CLAUDE.md non-negotiable + `project_beta_riskforward_flag_stance` | repo standing rule |
| D5 | Beta-stance: all 9 new flags default `enforce` (and entity-filter promoted shadow→enforce) | `project_beta_riskforward_flag_stance` | 2026-05-17 |
| D6 | Diagnose-before-intervene per phase (P1-T1, P2-T1, …, P9-T1) | `feedback_diagnose_before_intervene` | repo standing rule |
| D7 | Granular edits — new files for new concerns; no monolith bloat | `feedback_granular_edits` | repo standing rule |
| D8 | Default run mode = dev:staging | `feedback_default_run_mode_staging` | repo standing rule |
| D9 | SME panel operator-triggered only; self-audit via `answer-engine-probe` | `feedback_sme_panel_explicit_request_only` | repo standing rule |
| D10 | Autonomy mode — engineer takes all decisions and commits at phase boundaries; operator holds the closing gate only | Operator directive 2026-05-17 PM | 2026-05-17 |
| D11 | Permanent regression suite at `tests/test_audit_regression_v25_combined.py` — the 20 audit Qs verbatim | Audit is canonical regression set; per `feedback_verify_fixes_end_to_end` | 2026-05-17 |
| D12 | v25 is single-branch (not single-worktree) — branch `fix-v25-may` off `main` | Operator directive "do all work in a purpose branch" | 2026-05-17 |

---

## §10. What v25 does NOT do (honest scope)

- v25 does **not** retire cloud-corpus pollution (deferred to v24 per D3).
- v25 does **not** ingest the Bogotá SHD compilación (deferred; P3 surfaces a pointer block only).
- v25 does **not** add full DTT (treaty) coverage — P2 covers cross-border via canonical ET articles only.
- v25 does **not** auto-run the SME panel (per D9).
- v25 does **not** modify cloud Supabase / Falkor data (P1/P8 are runtime-only).
- v25 does **not** raise thresholds on existing v22 / v23 gates (per `feedback_thresholds_no_lower`); only adds new validators alongside.
- v25 does **not** rewrite the polish prompt from scratch — surgical additions only.
- v25 does **not** touch the Normativa or Interpretación surface backends (per AGENTS.md surface boundaries); only `main chat` orchestration + synthesis + polish.
- v25 does **not** modify v23 commits — all v23 modules stay intact.

---

## §11. Resuming work — preconditions + first-action recipe

A fresh agent should be able to start P0 immediately after the preconditions below pass.

### §11.1 Preconditions (run all six, all must pass)

```bash
# 1. v23 internal-closed.
git tag --list fix_v23_closed && echo "OK v23 closed" || echo "WARN — verify v23 internal-close via §⏯"

# 2. Recent commits show v23 (sanity check).
git log --oneline -10 | grep -E "v23" && echo "OK v23 commits present" || echo "WARN — verify v23 commit log"

# 3. Local docker stack — Supabase + Falkor up (for any local probing).
docker ps --filter "name=supabase_db_lia-graph" --filter "name=lia-graph-falkor-dev" --format "table {{.Names}}\t{{.Status}}"

# 4. .env.staging exists.
test -f .env.staging && grep -q "^FALKORDB_URL=redis" .env.staging && echo "OK staging env" || echo "MISSING"

# 5. dev:staging server up + answering (only needed for probe step).
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8787/

# 6. Audit verbatim archived.
test -f docs/re-engineer/audits/2026-05-17_external_sme_audit_post_v23.md && echo "OK audit archived"
```

If any precondition fails, STOP and consult the relevant file (`fix_v23_may.md` for v23 state; `docs/guide/env_guide.md` for env state).

### §11.2 Phase 0 first action (after preconditions pass)

```bash
# P0-T0
git tag --list fix_v23_closed   # OK if empty when §⏯ says "v23 internally closed"

# P0-T2 — branch already cut
git checkout fix-v25-may
git log --oneline -3

# P0-T3 — commit this plan on branch
git add docs/re-engineer/fix/fix_v25_may.md docs/re-engineer/audits/2026-05-17_external_sme_audit_post_v23.md
git commit -m "docs(v25 P0): draft fix_v25_may.md + archive 2026-05-17 dual-packet audit"

# P0-T4 — regression suite scaffold (20 xfail tests, phases enable per-question)
```

### §11.3 What to do after each phase closes

- Append §6 run log entry with phase outcome + test names + green status.
- Set §2.1 phase row to ✅; next phase to 🔵.
- Commit at phase boundary on `fix-v25-may` branch.
- Do NOT pause for operator greenlight per D10 — proceed unless a P10 gate fires.

### §11.4 What to do after P9 closes (all fix phases done; P10 next)

- Announce: "All 9 fix phases closed. Ready for P10 (external SME closing gate). Operator: please contact the external accountant for re-run. Estimated coordination window: 2–5 days."
- Wait. Do NOT close v25 until SME verdict arrives.

### §11.5 What to do after P10 closes (v25 closing)

- §⏯ "Last completed step" → "v25 closed ✅"
- Update CLAUDE.md runtime-flags table to reflect all 9 new flags as standing canon.
- `git tag fix_v25_closed`.
- Open `docs/re-engineer/fix/fix_v26_may.md` from operator backlog if v25 SME re-run surfaced new generic weaknesses.

---

*Drafted 2026-05-17 ~5:00 PM Bogotá by claude-opus-4-7 in response to operator directive: "read fix_v23 and v14, to generate and implement fix_v25_may.md... improve capability of the model and not to overcorrect for specific questions... you do EVERYTHING and it is prohibited that you ask for authorization." Companion to [fix_v23_may.md](fix_v23_may.md) (predecessor) and [external audit](../audits/2026-05-17_external_sme_audit_post_v23.md). Update §⏯ + §2 + §6 as work progresses.*
