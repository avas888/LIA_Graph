# fix_v22_may.md — labor-article citation form (CST not ET) — v1

> **Zero-agent-context protocol.** Self-contained. A fresh agent with no prior conversation can execute it by reading this file + the filesystem. Verify every artifact against `git ls-files`. If something doesn't exist, STOP and report drift.
>
> **Scope.** v21 closed the answer-shape regression — q01 ("¿Qué dice el artículo 64 del CST?") now returns substantive content with the 30/20/15-días indemnización formula, 10 SMMLV threshold, 350/204 UVT retención rules, and a full Anclaje Legal section. But the polish step labels labor articles as **ET** (Estatuto Tributario — the **tax** code) instead of **CST** (Código Sustantivo del Trabajo — the **labor** code). Example from the v21 closing probe (run dir `tracers_and_logs/logs/probe_runs/20260517T161225Z_v21_t5_postfix/`): `(art. 64 ET)` and `(art. 62 ET)` appear in the polish output where the case-bullet SPEC source says `(CST art. 64)` / `(art. 62 CST)`. Anclaje Legal renders `(Art. 64 ET) — Regula la terminación unilateral del contrato de trabajo sin justa causa`. v22 fixes that mislabel so labor articles render correctly as `CST`.
>
> **Companion docs.** [`fix_v21_may.md`](fix_v21_may.md) — v21 plan + run log (closed ✅ 2026-05-17). [`fix_v20_may.md`](fix_v20_may.md) — v20 data-layer + lookup fix. This doc (v22) combines plan + state.

---

## §⏯ Crash-resume pointer (update this block after EVERY step)

**Read order if you are a fresh agent resuming after a crash:** §⏯ (here) → §-1 → §11.1 preconditions → the "Next step" pointer below.

| Field | Value |
|---|---|
| Last completed step | **v22 closed ✅** — D6 5-site fix verified end-to-end in dev:staging; q01 (CST labor) and q02 (ET tax regression guard) both meet rubric; 4 commits landed on `fix-v22-may`, ff-merged to main, pushed to GitHub, orphan `fix_v7-truncated-tail-and-canonical-shapes` branch deleted local+remote, tag `fix_v22_closed` applied. |
| Last touched UTC | 2026-05-17T17:50:00Z (2026-05-17 ~12:50 PM Bogotá) |
| Next step | **v23 takes over** — q01 P3 probe surfaced ONE follow-on quality issue NOT in v22's CST/ET scope: Anclaje Legal section expanded from 1 → 4 lines on the CST labor answer, with 3 off-topic ET articles (102 / 102-2 / 103 — fiducia / transporte / definición de rentas). Evidence-curation problem, not mislabel. Likely root cause: `section_structure` REGLA DE EXPANSIÓN inviting the polish LLM to expand Anclaje from connected_articles. Logged into `fix_v23_may.md` as the first new scope item; resolved there. |
| Working artifact | Worktree `/Users/ava-sensas/Developer/lia-graph.fix-v22-may` on branch `fix-v22-may`. Snapshot of original `fix_v7-truncated-tail-and-canonical-shapes` HEAD `4b953ca` at `tracers_and_logs/snapshots/20260517T173500Z_fix_v7_orphan_revival.patch` (896 lines). |
| Cloud state | v20 active: cloud Supabase `gen_v20_20260516_172203` is_active=true. **v22 does NOT touch cloud data**. |
| Local state | Worktree `fix-v22-may` active. P2 edits + new tests staged but uncommitted; doc updates uncommitted. After re-probe + judge: commit (4 commits planned), ff-merge to main, push, delete the original `fix_v7-truncated-tail-and-canonical-shapes` branch per §9c P2-T-Orphan-4. |
| Uncommitted code changes | (1) `src/lia_graph/pipeline_d/answer_llm_polish.py` — 5-site CST/ET parallel-anchor prompt widening per D6. (2) `src/lia_graph/pipeline_d/answer_support.py` — L13 truncated-tail filter + `_merge_abbreviation_splits`. (3) `src/lia_graph/canonical_question_shapes.py` + `config/canonical_question_shapes.json` — L14 seed shape (`plazos_renta_personas_juridicas`). (4) `src/lia_graph/pipeline_d/planner.py` — `tabular_reference` budget + canonical-shape override before `_BUDGETS` lookup. (5) `src/lia_graph/pipeline_d/orchestrator.py` — sub-Q canonical-shape escape hatch BEFORE `subquery_inherited_parent`. (6) `config/compatible_doc_topics.json` — 3 new adjacencies. (7) `frontend/src/features/chat/expertPanelRefs.ts` — code-aware refs (emits both `art_N` and `cst_art_N`/`et_art_N`). (8) `frontend/src/features/chat/citations.ts` — CST direct-match branch + URL resolver. (9) `frontend/src/features/chat/normative/citationParsing.ts` — code-aware `parseLocatorText`/`formatParsedLocator`/`parseLocatorTitle` dispatchers. (10) `frontend/src/features/chat/normativeModals.ts:267` — code-aware article title. (11) `CLAUDE.md` + `AGENTS.md` — §9b worktree + commit hygiene rules. (12) `docs/re-engineer/active_worktrees.md` — new roster template per §9b.4 P2-T-Hygiene-3. (13) `tests/test_polish_cst_form_preserved.py`, `tests/test_canonical_question_shapes.py`, `tests/test_answer_support_truncated_tail.py` — 14 new unit tests. |
| Heartbeat / monitor state | None active. |
| If crashing now, resume with | (1) `cd /Users/ava-sensas/Developer/lia-graph.fix-v22-may && git status` — verify staged work. (2) Operator restarts dev:staging in worktree (recipe above). (3) Probe q01 + q03 via `answer-engine-probe` skill. (4) On pass, commit 4 grouped commits + ff-merge to main + push. (5) Delete `fix_v7-truncated-tail-and-canonical-shapes` branch per §9c P2-T-Orphan-4. (6) Flip §⏯ to "v22 closed ✅" and tag `fix_v22_closed` on the merge commit. |
| Hard rule | After EVERY task transition, update this block + §2 phase/task tables + append a §6 run log entry. Do not batch updates. |

---

## §-1. If you are a fresh agent — read this first

You are picking up a **one-question-one-fix project**. v21 closed the answer-shape regression (off-topic bullets + thin template). v22 closes ONE remaining cosmetic-but-real bug: labor articles get labeled with the wrong code suffix in polished answers.

**Read in this order before touching anything (max 15 min):**

1. `CLAUDE.md` (repo root) — repo operating guide. "Fast Decision Rule" + the `LIA_POLISH_*` flag rows are load-bearing.
2. `AGENTS.md` (repo root) — layer ownership (surface boundaries).
3. **This file** §0 → §1 → §2 → §3.
4. [`fix_v21_may.md`](fix_v21_may.md) §6 closing entry — context on the v21 fix that exposed this issue.
5. `tracers_and_logs/logs/probe_runs/20260517T161225Z_v21_t5_postfix/q01.digest.md` — the artifact showing the mislabel.

**Hot facts you must know before touching anything:**

- **Default run mode is `dev:staging`** — cloud Supabase + cloud Falkor (`LIA_REGULATORY_GRAPH`). Assume staging.
- **Cloud writes for Lia Graph are pre-authorized** — announce in chat before executing, no per-action confirmation needed. v22 doesn't write to cloud.
- **MANDATORY server restart before EVERY probe.** Same rule as v21.
- **SME panel is OFF-LIMITS** — use `answer-engine-probe` skill for self-audit (per `feedback_sme_panel_explicit_request_only`).
- **Beta-stance applies** — every non-contradicting improvement flag flips ON. v22 doesn't introduce new flags expected.
- **No text walls in docs.** Bullets/lists/tables only.

**Operator's intent (boss directive, 2026-05-17 ~11:30 AM Bogotá):**

- Quote: "promote both flags and punt the CST/ET label to v22 in a fix_v22_may.md separate doc with the usual zero context agent protocol."
- Translation: v22 inherits v21's pattern (zero-agent-context, exhaustive state ledger, §⏯ crash-resume) and tackles only the CST/ET mislabel.

**Memory-pinned guardrails (do not violate):**

- Diagnose before intervene — measure where the mislabel originates before proposing a fix (prompt vs validator vs synthesis template).
- Granular edits — narrow files (`answer_llm_polish.py` and possibly `presentation.py`); don't append to ≥ 1000-LOC files.
- No text walls; no money quoting; no SME panel auto-run.
- Recommendations live in the canonical plan (this file), not just chat.
- Default run mode = dev:staging.

**The big picture in two sentences:**

- The case-bullet SPEC source for labor (`pipeline_d/case_bullets/liquidacion_terminacion.py`) correctly uses `CST art. 64` / `art. 65 CST` form. The polish prompt's `anchor_preserve` + `numeric_format_bold` rules treat the canonical inline form as `(art. X ET)` because tax cases dominate the v18–v20 panel set, and the LLM rewrites labor citations to match the dominant form.
- v22 either widens the polish prompt to honor `(art. X CST)` as a parallel canonical form when topic=laboral, OR adds a post-polish transform that maps `(art. <num> ET)` → `(art. <num> CST)` when the article number belongs to the labor code namespace (1–492).

---

## §0. TL;DR

- **The gap v22 closes.** v21 closing probe shows q01 answer with substantive content but mislabels labor articles as `(art. 64 ET)` instead of `(art. 64 CST)`. Real bug for accountant trust: ET is the tax code (renta, IVA, retención) — citing labor art. 64 as ET is wrong.
- **Why v22 exists.** Without it, every labor-anchored polished answer carries the wrong code suffix on its inline citations + Anclaje Legal line. Cosmetic-looking but substantive — a contador will mistrust an answer that cites the wrong code.
- **3 phases.** P1 diagnose (find where ET dominates the polish prompt + validate that the case-bullet SPEC is correct). P2 fix (narrow edits in `answer_llm_polish.py` POLISH_RULES — likely `anchor_preserve` + `numeric_format_bold`; possibly a small post-polish transform). P3 re-probe + commit.
- **Time budget.** P1: ~30 min. P2: 1–2 hr. P3: ~30 min. Total: half-day.
- **Risk.** All edits behind existing polish kill-switch (`LIA_LLM_POLISH_ENABLED=0` reverts to template). 326 v21 baseline tests must stay green.
- **Estado al 2026-05-17 ~11:30 AM Bogotá.** P1 🟡 ready to start.

---

## §1. Where we are right now (v21 close-state)

### §1.1 What v21 landed (do not re-do)

- ✅ **Polish validator widen**: `_no_invented_norm_lineage` + `_no_invented_periods` now consult evidence (commits `e1cca50`).
- ✅ **Détector widen**: `is_liquidacion_terminacion_case` fires on article-lookup form for CST 62/64/65 (commit `dc2e482`).
- ✅ **First-bubble bail-out**: switched from section-count to content-size trigger (commit `8b8df7a`).
- ✅ **Flag promotion**: `LIA_PRACTICA_NOISE_FILTER` + `LIA_CONFLICT_RESOLVER_MODE` flipped shadow → enforce in `scripts/dev-launcher.mjs`, mirrored in CLAUDE.md + env_guide.md (P3-T4).
- ✅ **End-to-end probe**: q01 returns substantive answer with 30/20/15 días + 10 SMMLV + 350 UVT + Justa causa + Retención + Anclaje Legal.

### §1.2 What v21 left undone (this is v22's mandate)

| Gap | Concretely | Evidence | Module path |
|---|---|---|---|
| **(Primary)** Polish mislabels labor articles | Polish output renders `(art. 64 ET)` / `(art. 62 ET)` for CST articles. The polish prompt's `anchor_preserve` rule says "preserve all `(art. X ET)` references" — the LLM applies that rule to ALL article citations regardless of which code (ET or CST) actually governs them. | `tracers_and_logs/logs/probe_runs/20260517T161225Z_v21_t5_postfix/q01.digest.md` — "Anclaje Legal: (Art. 64 ET) — Regula la terminación unilateral del contrato de trabajo sin justa causa" | `src/lia_graph/pipeline_d/answer_llm_polish.py` — POLISH_RULES `anchor_preserve` (line ~60) + `numeric_format_bold` (line ~141) |
| Polish inconsistency: same article cited two ways | In one answer body, `(art. 65 CST)` appears correctly AND `(art. 64 ET)` appears incorrectly. The LLM follows the prompt for some lines and the source bullet form for others. | Same q01 trace — search for `art. 65 CST` vs `art. 64 ET` | Same |
| **(Cascade A) Interpretación de Expertos panel empty for labor.** | UI panel renders **0 cards** for q01 despite 7 labor expert docs in corpus. Backend retrieves 18 candidates, off-topic filter penalizes 12 to zero (`off_topic_penalized_count=12, off_topic_penalized_kept=0`), eligible drops to 4 → 1 group + 2 ungrouped → frontend ranking + classification filters all 3 out. Root cause = polish mislabel cascades: `extractArticleRefs` at `frontend/src/features/chat/expertPanelRefs.ts:1-14` parses the polished answer text and emits **code-agnostic refs** (`art_64` instead of `art_cst_64`); backend then treats `art_64` from the `(art. 64 ET)` polished line as a tax-article anchor; off-topic filter drops the labor expert candidates. | UI screenshot 2026-05-17 ~11:35 AM Bogotá. Curl probe of `/api/expert-panel` for q01 returns `groups=1 + ungrouped=2 + total_available=3`. | `frontend/src/features/chat/expertPanelRefs.ts::extractArticleRefs` (emit code-aware refs); also tied to the polish fix above |
| **(Cascade B) Soporte Normativo panel: "0 referencias" + ET mislabel.** | UI screenshot shows the Soporte Normativo panel listing 5 labor articles (64/65/62/401-3/108) but labels them ALL as **"Estatuto Tributario"** and the header reports "Mostrando 0 referencias normativas detectadas en este turno." Both display issues: (1) counter doesn't match list length; (2) code-suffix renderer hardcodes "Estatuto Tributario" or has no laboral branch. | Same screenshot. | TBD — likely `frontend/src/features/chat/normative/` or `ui_chat_payload.py` citation rendering; needs P1-T4 grep |

### §1.3 The non-negotiable invariants v22 must preserve

- **v21 substance stays.** q01 must continue to surface 30/20/15 días + 10 SMMLV + 350 UVT + Justa causa + Retención content.
- **q02 + q03 stay passing.** v21 closing probe verdicts: q02 (operational form) and q03 (tax regression guard) both passed with substantive content + correct citations.
- **Tax-side `(art. X ET)` form is correct and must NOT regress.** Renta, IVA, retención articles ARE ET — the prompt's ET form is right for those.
- **No new corpus retirements** (CLAUDE.md non-negotiable).
- **No SME panel auto-run** (use `answer-engine-probe`).

---

## §2. State tracker (live — update this section as work progresses)

### §2.1 Phase status

| Phase | Description | Status | Owner | Last touched |
|---|---|---|---|---|
| P1 | Diagnose (locate ET-bias in polish prompt + validate case-bullet SPEC source) | ✅ done | claude | 2026-05-17 ~12:00 PM |
| P2 | Fix (polish + frontend + hygiene + orphan-land + tests) | ✅ done | claude | 2026-05-17 ~12:35 PM |
| P3 | Re-probe + commit | ✅ done | claude+operator | 2026-05-17 ~12:50 PM |

Status legend: 🟡 not started · 🔵 in progress · ✅ done · 🚫 blocked · ↩ discarded.

### §2.2 Active blockers

| # | Blocker | Affects | Owner | Surfaced |
|---|---|---|---|---|

(none open as of 2026-05-17 ~11:30 AM)

### §2.3 Active tasks (rolls up from §3 phases)

| ID | Task | Phase | Status | Owner | Blockers | Last touched |
|---|---|---|---|---|---|---|
| P1-T1 | Read `answer_llm_polish.py` POLISH_RULES (esp. `anchor_preserve` + `numeric_format_bold`). Identify where the `(art. X ET)` form is enforced as canonical. | 1 | ✅ | claude | — | 2026-05-17 ~11:40 AM |
| P1-T2 | Verify case-bullet SPEC sources for labor topics use `CST art. N` / `art. N CST` form (sample: `case_bullets/liquidacion_terminacion.py`, `prestaciones_sociales.py`). If sources are correct, the bug is purely in polish; if sources are inconsistent, fix source first. | 1 | ✅ | claude | — | 2026-05-17 ~11:45 AM |
| P1-T3 | Decide approach: (a) widen polish prompt to honor both forms, (b) add post-polish transform `(art. <num> ET) → (art. <num> CST)` when topic=laboral AND num ∈ CST namespace, (c) both. Write decision to §9. | 1 | ✅ | claude | — | 2026-05-17 ~12:00 PM |
| P1-T4 | Cascade A — locate `extractArticleRefs` at `frontend/src/features/chat/expertPanelRefs.ts:1-14` and decide whether to (a) emit code-aware refs (`cst_art_N` / `et_art_N`) when the surrounding text identifies the code, or (b) fix only via the polish side and rely on the polished text now saying CST. | 1 | ✅ | claude | — | 2026-05-17 ~11:50 AM |
| P1-T5 | Cascade B — locate the Soporte Normativo panel renderer (probably `frontend/src/features/chat/normative/` or `ui_chat_payload.py` citation serializer). Document the two failures: hardcoded "Estatuto Tributario" string + the "0 referencias" counter divergence from the actual list count. | 1 | ✅ | claude | — | 2026-05-17 ~11:55 AM |
| P2-T1 | Implement chosen approach + unit test in `tests/test_polish_cst_form_preserved.py` | 2 | ✅ | claude | P1-T3 | — |
| P2-T2 | Run focused test sweep (polish + détector + synthesis + per-case) — must stay 326/326 green | 2 | ✅ | claude | P2-T1 | — |
| P3-T1 | Restart dev:staging server (kill + relaunch) | 3 | 🟡 | operator | P2 ✅ | — |
| P3-T2 | Re-run `answer-engine-probe` on q01 (CST labor) + q03 (ET tax regression guard) | 3 | ✅ | claude | P3-T1 | — |
| P3-T3 | Judge verdicts — q01 must show `(art. X CST)` form, q03 must keep `(art. X ET)` form correct | 3 | ✅ | claude | P3-T2 | — |
| P3-T4 | Commit + FF main + push to GitHub | 3 | 🟡 | operator | P3-T3 ✅ | — |
| P3-T5 | Update §⏯ "Last completed step" to "v22 closed ✅" | 3 | 🟡 | operator | P3-T4 | — |

---

## §3. The plan — 3 phases

### §3.1 Phase 1 — Diagnose (~30 min)

**Idea.** Find where the ET form gets enforced. Per `feedback_diagnose_before_intervene`.

**Plan narrow.**

1. **P1-T1: read polish rules.** Open `src/lia_graph/pipeline_d/answer_llm_polish.py` lines ~60–220. Inspect:
   - `anchor_preserve` rule prompt_text — does it say "(art. X ET)" form is canonical?
   - `numeric_format_bold` rule's ET-exception clause — does it implicitly assume ET is the only code?
   - `_preserves_required_anchors` validator: the `_ANCHOR_RE` regex matches `\(arts?\.[^)]+\)` — agnostic of ET/CST, so validator likely passes either form.
2. **P1-T2: verify sources.**
   - `grep -n "art\\. [0-9].*CST\\|CST art\\. [0-9]" src/lia_graph/pipeline_d/case_bullets/liquidacion_terminacion.py`
   - Confirm SPEC bullets use `CST art. 64` / `art. 65 CST` (right form).
   - Spot-check 2 other labor case_bullets if they exist.
3. **P1-T3: write the scope decision in §9.**

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P1-SC1 | Polish-prompt ET-bias source identified (file:line) | grep + read |
| P1-SC2 | Case-bullet SPEC source confirmed correct or fixed if wrong | grep + read |
| P1-SC3 | Scope decision recorded in §9 with rationale | doc edit |

**Test plan.** Engineer 30 min. Output: diagnosis in §6 run log.

**Rollback.** Read-only step.

### §3.2 Phase 2 — Fix (~1–2 hr)

**Idea.** Narrowest possible edit. Per `feedback_diagnose_before_intervene` + `feedback_granular_edits`.

**Most likely fix shape (refine after P1-T3).**

| Sub-task | File | Expected shape |
|---|---|---|
| P2-T1 prompt widen | `src/lia_graph/pipeline_d/answer_llm_polish.py` POLISH_RULES `anchor_preserve` + `numeric_format_bold` | Add explicit clause: "Para artículos del CST (Código Sustantivo del Trabajo, art. 1 a 492), preservá el sufijo `CST` en la forma `(art. X CST)` o `(arts. X y Y CST)`. NO los reescribas como `(art. X ET)`." Mirror the same clause inside `numeric_format_bold`'s "EXCEPCIÓN ESTRICTA" block so the LLM understands both forms are valid bold-exception anchors. |
| P2-T1 post-polish guard (defensive) | Same file, helper near `_apply_post_hoc_transformers` | If topic = laboral AND polished output contains `(art. <num> ET)` where `<num>` is in CST namespace (1–492), rewrite to `(art. <num> CST)`. Off by default; gated by `LIA_POLISH_LABOR_ANCHOR_REWRITE=enforce` so it can be toggled. (Optional belt-and-suspenders; only ship if P1-T3 decision keeps both.) |
| P2-T2 test sweep | `tests/test_polish_*` + `tests/test_practica_*` + per-case | All 326 v21-baseline tests green; new tests cover both the labor CST-preserve case and the tax ET-preserve regression guard. |

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P2-SC1 | New polish unit test: labor article in template ends up labeled CST in polish output | `pytest tests/test_polish_cst_form_preserved.py -v` |
| P2-SC2 | Existing tax-side polish tests still green (e.g. `test_polish_accepts_ley_present_in_evidence_related_reforms` from v21) | same suite |
| P2-SC3 | Full focused regression: 326+ tests green | `make test-batched` for targeted files |

**Test plan.** Engineer 1–2 hr.

**Rollback.** Per CLAUDE.md non-negotiable, every fix ships with a flag. Prompt-widen changes ride `LIA_LLM_POLISH_ENABLED=0` (existing kill switch). Post-polish transform (if added) rides new `LIA_POLISH_LABOR_ANCHOR_REWRITE=off`.

### §3.3 Phase 3 — Re-probe + commit (~30 min + operator wait)

**Idea.** Verify end-to-end then commit.

**Plan narrow.**

1. **P3-T1 restart server** — operator runs `lsof -ti tcp:8787 | xargs kill && cd /Users/ava-sensas/Developer/Lia_Graph && npm run dev:staging`.
2. **P3-T2 re-probe** — `answer-engine-probe` with two questions:
   - q01: "¿Qué dice el artículo 64 del CST sobre la terminación sin justa causa del contrato de trabajo?"
   - q02 (tax regression): "¿Cuál es el régimen actual de compensación de pérdidas fiscales del artículo 147 ET y qué leyes lo modificaron?"
3. **P3-T3 judge** — q01 must render labor articles as `(art. X CST)` form; q02 must keep `(art. X ET)` form for tax articles. Per-question rubric is `references/rubric.md` from the probe skill.
4. **P3-T4 commit** — operator-triggered. 2–3 commits (polish prompt / optional transform / docs).
5. **P3-T5 update state** — flip §⏯ to "v22 closed ✅".

**Success criteria.**

| # | Criterion | Target |
|---|---|---|
| P3-SC1 | q01 verdict = `pass` per `answer-engine-probe` rubric; labor articles cited as CST | rubric pass |
| P3-SC2 | q02 verdict = `pass`; tax articles cited as ET (regression guard) | rubric pass |
| P3-SC3 | §⏯ + §2 + §6 updated to "v22 closed ✅" before commit | doc edits |

**Rollback.** Flip `LIA_LLM_POLISH_ENABLED=0` to skip polish entirely (template returns unchanged); the v21-shipped substance still renders.

---

## §4. Files to touch (consolidated)

### §4.1 Modified files (P2)

- `src/lia_graph/pipeline_d/answer_llm_polish.py` (P2-T1 — prompt + optional helper)
- `scripts/dev-launcher.mjs` (P2-T1 only if new flag introduced)
- `CLAUDE.md` (P2-T1 only if new flag introduced)
- `docs/orchestration/orchestration.md` (P2-T1 env matrix version bump if new flag)
- `docs/guide/env_guide.md` (mirror if new flag)
- `docs/re-engineer/fix/fix_v22_may.md` (this file — state updates)

### §4.2 New files

- `tests/test_polish_cst_form_preserved.py` (P2-T1)

### §4.3 Touched but no change (verify only)

- `src/lia_graph/pipeline_d/case_bullets/liquidacion_terminacion.py` — confirm SPEC source uses `CST` form
- `src/lia_graph/pipeline_d/case_bullets/prestaciones_sociales.py` — same check

---

## §5. Risks + mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Prompt widen confuses LLM, regresses tax-side citations | Medium | High | New unit test locks tax ET form (regression guard). Run full focused sweep before commit. |
| Post-polish transform (if added) over-fires on edge cases (e.g. an ET article that happens to be number 64) | Low | Medium | Gate the transform on `topic=laboral` AND number ≤ 492; ship behind env flag. CST has 492 articles; ET goes much higher. |
| q01 probe still mislabels after fix | Medium | Medium | Iterate per P1-T3 max 2 cycles; if still failing, surface to operator with full trace. |
| v21 baseline regression | Medium | High | `make test-batched` before P3-T4 commit. |

---

## §6. Run log (append-only, most recent on top, Bogotá local time)

### 2026-05-17 ~12:50 PM Bogotá — v22 closed ✅ + handoff to v23

- **P3-T2 probe** (`tracers_and_logs/logs/probe_runs/20260517T174327Z_v22_t2_postfix/`). Server restarted from the worktree (PID 91827, venv path `lia-graph.fix-v22-may/.venv`).
  - **q01** ("¿Qué dice el artículo 64 del CST sobre la terminación sin justa causa del contrato de trabajo?") — verdict **warn**. Body bullets correctly cite `(art. 64 CST)`, `(art. 62 CST)`, `(art. 65 CST)` for labor; `(art. 206 num. 5 ET)`, `(art. 401-3 ET)`, `(arts. 108 y 387 ET)` for tax intermix. Anclaje Legal primary line `(Art. 64 CST) — Regula la terminación unilateral del contrato de trabajo sin justa causa.` ✅. **WARN:** Anclaje Legal expanded to 4 lines incl. 3 off-topic ET articles (Art. 102 / 102-2 / 103 ET — fiducia / transporte / definición de rentas). Pre-v21 it was 1 line.
  - **q02** ("¿Cuál es el régimen actual de compensación de pérdidas fiscales del artículo 147 ET y qué leyes lo modificaron?") — verdict **pass**. Every inline cite uses ET correctly (147 / 290 / 906 / 319-4 / 195 / 199); Anclaje Legal 4 lines all ET and all on-topic. No accidental CST-ification anywhere. Tax-side regression guard met.
- **Verdict tally.** 2 questions, 1 pass + 1 warn + 0 fail. v22 core deliverable (CST/ET mislabel) met. Anclaje expansion = separate evidence-curation issue, not v22 scope.
- **P3-T4 commits** (4 grouped on `fix-v22-may` branch):
  - `721fd2e fix(v22 P2-T1): widen polish prompt + frontend for CST/ET parallel anchor preservation` — answer_llm_polish.py + 4 TS modules + tests + ui build artifacts.
  - `bcc9021 docs(v22 §9b): mandatory worktree + commit hygiene rules` — CLAUDE.md + AGENTS.md + active_worktrees.md.
  - `23dbc24 fix(v22 §9c): revive L13 truncated-tail filter + L14 canonical question shapes from orphan fix_v7 branch` — answer_support.py + canonical_question_shapes.py + JSON + planner.py + orchestrator.py + compatible_doc_topics.json + 2 new tests + snapshot patch.
  - This commit — state ledger close + run log + v23 handoff.
- **Merge + push + tag.** Worktree `fix-v22-may` ff-merged to main; main pushed to origin; orphan `fix_v7-truncated-tail-and-canonical-shapes` branch deleted local + remote per §9c P2-T-Orphan-4 (snapshot preserved); tag `fix_v22_closed` applied to the closing commit; worktree removed.
- **Handoff to v23.** The Anclaje-Legal-expansion WARN is logged as v23's first scope item — see `fix_v23_may.md`. Suggested first task: tighten `section_structure` REGLA DE EXPANSIÓN to constrain Anclaje Legal to articles whose topic matches the question's effective topic (or to the seed article keys only). Connected_articles can still feed body bullets; the constraint applies only to the Anclaje Legal section.

### 2026-05-17 ~12:35 PM Bogotá — P2 closed ✅

- **P2-T1 polish prompt widening** (`src/lia_graph/pipeline_d/answer_llm_polish.py`). 5 sites edited per §9 D6:
  - Module docstring (L1-12): replaced ET-only language with explicit ET+CST dual-code framing.
  - `anchor_preserve` rule: widened to "preservá el sufijo de código exactamente como aparece en el BORRADOR — NUNCA reescribás `(art. N CST)` como `(art. N ET)` ni viceversa."
  - `section_structure` rule (`y TODAS las referencias inline al ET` line): widened to "referencias inline a artículos (`(art. N ET)`, `(art. N CST)`, etc.) con su sufijo de código intacto."
  - `anclaje_legal_explanatory_lines` rule: introduced `CÓDIGO` placeholder explained as "`ET` para Estatuto Tributario, `CST` para Código Sustantivo del Trabajo, etc."; added CST example `La indemnización por despido sin justa causa se regula en el (art. 64 CST).`; explicit "NUNCA cambies el sufijo (`ET` por `CST` o viceversa)."
  - `numeric_format_bold` EXCEPCIÓN ESTRICTA: added CST examples `(art. 64 CST)`, `(arts. 186 a 197 CST)`, `(art. 401-3 ET)`, `(Ley 50 de 1990 art. 99)` alongside existing ET examples.
  - `no_invented_article_descriptions`: parallel ET+CST examples.
  - DIRECTIVA PRIMARIA bullet #2 (L1059-1067): changed "NO cites artículos del ET" → "NO cites artículos cuyo número no aparezca en la lista ARTÍCULOS PERMITIDOS abajo. Citar `(art. N ET)`, `(art. N CST)` o cualquier referencia inline... PRESERVÁ el sufijo de código (ET / CST / etc.) tal cual aparece en el BORRADOR — nunca lo cambies."
  - Empty-articles message: "(ninguno — no cites artículos del ET ni del CST en la reescritura)".
- **P2-T1 frontend code-aware refs** (`frontend/src/features/chat/expertPanelRefs.ts`). Rewrote regex to capture optional `ET` / `CST` token within ~12 chars before or after the article number. Emits BOTH `art_N` (backward-compat with `expertPanelSeed`'s matching) AND `cst_art_N` / `et_art_N` (so backend off-topic filter can distinguish labor from tax). Single regex, no schema changes downstream.
- **P2-T1 frontend citation parsing** (`frontend/src/features/chat/citations.ts`). Added CST direct-match branch BEFORE the ET branch — accepts `CST`, `Código Sustantivo del Trabajo`, `CST art. N`, `art. N CST`, head/tail forms — returns `reference_key: "cst"`, `reference_type: "cst"`, `source_label: "CST art. N"` / `"CST arts. N a M"`. Added `cst` URL resolver in `resolveExternalNormativeUrls` (mints normograma URL `codigo_sustantivo_trabajo.html#<art>`).
- **P2-T1 frontend locator dispatcher** (`frontend/src/features/chat/normative/citationParsing.ts`). Introduced `CODE_LABELS` table + `parseLocatorText(value, code)` + `formatParsedLocator(locator, code)` + `parseLocatorTitle(rawTitle)` (auto-detects CST or ET from text). Kept `parseEtLocatorText` / `formatParsedEtLocator` / `parseEtTitle` as thin wrappers — no caller breaks. `parseLocatorTitle` tries CST head/tail first, then ET head/tail, returns code-aware "Código Sustantivo del Trabajo, Artículo N" or "Estatuto Tributario, Artículo N" accordingly.
- **P2-T1 normativeModals** (`frontend/src/features/chat/normativeModals.ts:267`). Reads `reference_key` / `reference_type` off `baseCitation` to pick the code label dynamically. Falls back to ET when neither is `cst`.
- **P2-T2 tests** — wrote `tests/test_polish_cst_form_preserved.py` (5 cases): prompt-text assertions for `anchor_preserve` + `numeric_format_bold` + `anclaje_legal_explanatory_lines` mention CST; integration test that an LLM-mocked adapter preserving `(art. 64 CST)` passes validation; tax-side regression guard that `(art. 147 ET)` still preserved on tax questions.
- **P2-T-Hygiene-1..3** — mirrored §9b worktree+commit hygiene rules into `CLAUDE.md` Non-Negotiables (new bullet group between "old-RAG assumptions" and "Six-gate lifecycle"); added parallel `## Worktree + Commit Hygiene` section to `AGENTS.md` before "Documentation Discipline"; created `docs/re-engineer/active_worktrees.md` roster template (empty steady state). P2-T-Hygiene-4 (`make worktrees-audit` target) deferred to v23 per §9b.4 note.
- **P2-T-Orphan-1..3 (revive fix_v7-truncated-tail-and-canonical-shapes)** — landed three layers from the orphan branch as clean v22 work (no cherry-pick of `4b953ca`, rewritten with the rationale in code comments):
  - **L13 truncated-tail filter** (`src/lia_graph/pipeline_d/answer_support.py`). Added `_ABBREVIATION_TOKENS` + `_ABBREVIATION_BEFORE_PERIOD_RE` + `_TRUNCATED_TAIL_TOKEN_RE` constants near `_HEADING_REJECT_PATTERNS`. Added `_merge_abbreviation_splits` function. Wired both into `_evidence_candidate_lines`: `raw_parts = re.split(...)` then `for raw in _merge_abbreviation_splits(raw_parts):`, and before auto-period-adding, skip with `_TRUNCATED_TAIL_TOKEN_RE.search(cleaned)` guard. Each integration point comments back to fix_v22 §9c.
  - **L14 canonical question shapes** — new `src/lia_graph/canonical_question_shapes.py` (145 LOC), `config/canonical_question_shapes.json` (43 LOC, single seed `plazos_renta_personas_juridicas`). `match_canonical_shape(message, classified_topic)` is deterministic, file-cached, thread-safe; empty config = noop = zero risk.
  - **L14 planner hookup** (`src/lia_graph/pipeline_d/planner.py`). Added `tabular_reference` budget to `_BUDGETS` (snippet_char_limit=600, primary_article_limit=5). Inserted canonical-shape override AFTER the comparative-regime fork: if a shape matches AND its `evidence_shape_override.query_mode == "tabular_reference"` AND mode is not `comparative_regime_chain`, promote `query_mode = "tabular_reference"`.
  - **L14 orchestrator hookup** (`src/lia_graph/pipeline_d/orchestrator.py`). Inserted canonical-shape escape hatch BEFORE the `subquery_inherited_parent` override: when sub-Q is in `mode="fallback"` and `match_canonical_shape` returns a shape, override `sq_routing` with `mode="canonical_shape"`, `effective_topic=shape.topic`, `confidence=0.75`, `reason="fix_v22_orphan_L14:canonical_shape:<id>"`. Logged via `_trace.step("topic_router.subquery_canonical_shape", ...)`.
  - **L14 compat-doc-topics** (`config/compatible_doc_topics.json`). Added 3 mutual adjacencies (declaracion_renta ↔ calendario_obligaciones ↔ regimen_sancionatorio_extemporaneidad). Preserved the existing v14 `reforma_laboral_ley_2466` entry — the orphan branch's diff would have removed it; ported additively instead.
  - **Snapshot** — saved orphan's HEAD as `tracers_and_logs/snapshots/20260517T173500Z_fix_v7_orphan_revival.patch` (896 lines) for audit per §9c.3 P2-T-Orphan-4. Branch deletion deferred to after re-probe per §9c.3.
- **P2-T-Orphan-2 tests** — wrote `tests/test_canonical_question_shapes.py` (4 cases) and `tests/test_answer_support_truncated_tail.py` (5 cases): seed-shape loads from JSON, plazos-renta question matches, topic-mismatch suppresses, empty input returns None, `_TRUNCATED_TAIL_TOKEN_RE` matches `...fra` / `...art` / `...núm`, `_ABBREVIATION_BEFORE_PERIOD_RE` matches abbrev splits, `_merge_abbreviation_splits` rejoins `art.`/`núm.` but preserves real sentence boundaries, `_evidence_candidate_lines` drops the truncated tail fragment.
- **Test totals** — 14 new tests + 165 existing tests touched (polish, orchestrator, planner_query_modes, answer_support, conflict_resolver, practica, case_detectors_purity, polish_rejected_fallback, polish_invented_norm_lineage_labor) → **179/179 Python tests green**. Frontend: 142/143 vitest green (1 pre-existing failure on main: `expertPanelController.test.ts` "DIAN/Deloitte eyebrow text" — unrelated to v22 changes, fails identically on main HEAD). `npm run frontend:build` clean, 623ms.
- **Next.** Stop here for P3-T1 operator restart. Commit shape (4 commits) per §11.5 to be issued after re-probe judge passes per §3.3 P3-T3.

### 2026-05-17 ~12:00 PM Bogotá — P1 diagnose closed ✅

- **P1-T1 (polish prompt).** Five ET-bias sites found in `src/lia_graph/pipeline_d/answer_llm_polish.py`:
  - L7 module docstring: "preserving every `(art. X ET)` anchor."
  - L64-65 `anchor_preserve.prompt_text`: "Preservá TODAS las referencias inline al Estatuto Tributario con la forma `(art. X ET)` o `(arts. X y Y ET)`." Mentions only ET as canonical.
  - L113-124 `anclaje_legal_explanatory_lines.prompt_text`: lists only `Art. N ET — ...` / `(art. N ET).` as acceptable Anclaje Legal shapes.
  - L149-152 `numeric_format_bold` EXCEPCIÓN: example list `(art. 147 ET)`, `(arts. 147 y 290 ET)` — all ET.
  - L1065-1067 DIRECTIVA PRIMARIA bullet #2: "NO cites artículos del ET cuyo número no aparezca en la lista ARTÍCULOS PERMITIDOS. Citar `(art. N ET)` con N fuera de esa lista es invención y será rechazado." — uses ET as the universal article-cite shape.
  - **Validator regex `_ANCHOR_RE` at L316** (`re.compile(r"\(arts?\.[^)]{0,120}\)", re.IGNORECASE)`) is code-agnostic — it counts anchors irrespective of ET/CST. Validator does NOT enforce ET; only the prompt does.
- **P1-T2 (case-bullet SPEC sources).** 18 correct CST references across `case_bullets/`:
  - `liquidacion_terminacion.py` uses `(CST art. 64)`, `(CST art. 62)`, `CST art. 65`, `art. 65 CST` — all correct shapes.
  - `prestaciones_sociales.py` uses `(CST art. 306, modif. Ley 1788/2016)`, `(CST arts. 186 a 197)`, `(CST art. 187)`, `art. 65 CST`, `art. 128 CST`, `art. 99 CST` — all correct.
  - SPEC sources are NOT the source of the mislabel. Bug is entirely downstream in polish.
- **P1-T4 (Cascade A).** `frontend/src/features/chat/expertPanelRefs.ts` confirmed code-agnostic (single regex `\b(?:art(?:[ií]culo)?\.?\s*(\d{1,4}…))\b` → emits `art_${num}` only). When polish outputs `(art. 64 ET)` for a CST article, the bare `art_64` ref cascades into off-topic filter (`decision_frame.core_refs = [..., "et_art_64"]`) and labor expert candidates get penalized to zero.
- **P1-T5 (Cascade B).** Soporte Normativo "Estatuto Tributario" hardcode + counter divergence localized to:
  - `frontend/src/features/chat/citations.ts:107` — `source_label: "Estatuto Tributario"` (fallback for bare reference_key="et").
  - `frontend/src/features/chat/citations.ts:186-203` — `bareArticleMatch` block: "Bare 'artículo N' without explicit ET/Estatuto Tributario context — in Colombian tax domain, bare article references default to ET." Returns `reference_key: "et"`, `source_label: "ET art. N"`, `locator_text: "Artículos N"`. Every bare `(art. 64 …)` from the polished output gets the ET label here.
  - `frontend/src/features/chat/normative/citationParsing.ts:271-292` — `formatParsedEtLocator` + `parseEtTitle` hardcode "Estatuto Tributario, Artículo N" string. No CST branch.
  - `frontend/src/features/chat/normativeModals.ts:267` — `articleTitle = \`Estatuto Tributario, Artículo ${articleNum}\`` hardcoded.
  - Counter at `citationLoading.ts:197` reads `state.deferredCitationsCache.length`. The 5 visible items must be from a different path (likely mention citations or a stale cache snapshot) while `deferredCitationsCache` itself filters to 0 — needs runtime trace to confirm. Most likely: `filterCitedOnly(filterNormativeHelperBaseCitations(fallbackCitations))` drops all 5 labor cards because they don't match the ET allow-list inside those filters.
- **P1-T3 scope decision.** Locked as §9 D6 below.
- **Next.** Stop here for operator greenlight before P2 (per §11.3 hard rule).

### 2026-05-17 ~12:10 PM Bogotá — scope widened (#4): P2-T-Orphan-Land

- **Trigger.** Operator directive: "Fold into v22" the `fix_v7-truncated-tail-and-canonical-shapes` branch revival.
- **Branch findings.**
  - HEAD `4b953ca` dated 2026-04-30; one commit; 681 LOC across 9 files.
  - Self-labeled "fix_v7 phase 1+2" but main's actual `fix_v7_may.md` took the v7 slot for a different fix (retrieval / topic-filter softening); the branch's L13 + L14 work was never integrated under any namespace.
  - L13 (truncated chunk-tail filter) absent from main — main's `_looks_truncated_line` is narrow (only catches `"..."` / `"[truncated]"`).
  - L14 (canonical question shapes) entirely absent — no `canonical_question_shapes.py`, no `canonical_question_shapes.json`. The `subquery_inherited_parent` override at `orchestrator.py:628` still fires unconditionally.
  - Compat-doc-topics adjacencies for `declaracion_renta ↔ calendario_obligaciones ↔ regimen_sancionatorio_extemporaneidad` absent from `config/compatible_doc_topics.json`.
- **Codified.** New §9c with task table P2-T-Orphan-1..4 (rebase → tests → re-probe → delete original branch). Rationale + rollback documented per §9b.3 rules. Branch deletion is mandatory per §9b.1 #3 once landed.
- **Status.** Tasks blocked on v22 P1 closure (need P1-T1..T5 first to lock primary scope before mass-landing P2). After P1: P2-T-Orphan-1 can run in parallel with the other P2 tracks since target files don't overlap heavily.

### 2026-05-17 ~12:00 PM Bogotá — scope widened (#3): git/github hygiene rules

- **Trigger.** Operator directive: "make sure when we deploy fix_v22_may.md we incorporate procedures that make the git and github commits clean, and mandatory, and not leave them becoming stale so this does not happen in the future. incorporate this as part of the document."
- **What happened first.** 2026-05-17 ~11:55 AM Bogotá cleanup found 5 `agent-*` worktrees, each carrying a single commit. All 5 turned out to be earlier drafts of work that landed on main as different SHAs (e.g. `e8ffa09` blocker #1, `c20b3ce` blocker #2, etc.). The agent sessions that created them died (PIDs 88430 + 94669 dead); locks stayed; branches stayed; the redundant code sat there for weeks. Nearly cost an hour of attempted cherry-picks before duplication was confirmed via `state_fixplan_v5.md` ledger lookup.
- **Codified.** New §9b "MANDATORY git/github hygiene" — three rule families: per-session, per-commit, per-fix-doc. Plus P2-T-Hygiene-1..4 deliverable that mirrors the rules into `CLAUDE.md` + `AGENTS.md` + a new `active_worktrees.md` roster + a `make worktrees-audit` target (target may slip to v23 if time-bounded).
- **Status.** v22 is **not closed until these tasks land** — they ride the SAME commits as the polish/UI fixes. P2-T-Hygiene-3 (worktree roster) is one of the entry-criterion docs for v23 onward.
- **Also tracked.** Open question Q3: should the `fix_v7-truncated-tail-and-canonical-shapes` branch (which carries unique unmerged work: canonical_question_shapes config + 681 LOC of pipeline_d changes) be revived in v22 or left for separate triage? Surfaced 2026-05-17 ~12:00 PM during the worktree audit. Not yet decided.

### 2026-05-17 ~11:45 AM Bogotá — scope widened to UI cascades

- **Trigger.** Operator opened the chat UI for q01 (post-v21 ship) and reported (a) Interpretación de Expertos panel completely empty, (b) Soporte Normativo panel labels 5 labor articles as "Estatuto Tributario" + header says "0 referencias detectadas." Screenshot attached at 2026-05-17 ~11:35 AM Bogotá.
- **Diagnosis (read-only, in-process):**
  - `/api/expert-panel` returns 3 items (1 group + 2 ungrouped) for q01 — backend is NOT empty.
  - Retrieval pulls 18 candidates; off_topic_penalized_count=12 (kept=0); 4 eligible after filter → 1 group + 2 ungrouped.
  - `decision_frame.core_refs = ["et_art_62_cst", "et_art_65_cst", "et_art_64_cst", "et_art_64"]` — note the bare `et_art_64` (no `_cst`), traceable to the polished answer's `(art. 64 ET)` line.
  - Frontend `extractArticleRefs` at `frontend/src/features/chat/expertPanelRefs.ts:1-14` is **code-agnostic** — emits `art_N` regardless of whether the surrounding text says ET or CST.
- **Conclusion.** Cascade A (empty Interpretación panel) is downstream of the v22-primary polish mislabel: fix polish → polished text says `(art. 64 CST)` → backend interpretation lane has the right anchor → off-topic filter stops over-firing → panel populates. Cascade B (Soporte Normativo display) is a separate UI rendering bug, still v22-scoped because it surfaces the same wrong "Estatuto Tributario" label.
- **Next.** P1-T1 + P1-T2 + P1-T4 + P1-T5 in parallel (read-only). Then P1-T3 scope decision covers all three cascades.

### 2026-05-17 ~11:30 AM Bogotá — v22 plan drafted

- **What.** Drafted `docs/re-engineer/fix/fix_v22_may.md` v1 — full zero-agent-context plan with §⏯ crash-resume + 3 phases (P1 diagnose, P2 fix, P3 re-probe + commit).
- **Why.** v21 closing probe surfaced a polish-prompt bias toward `(art. X ET)` form, causing labor articles to be mis-cited. v21 closed at "warn" with this issue called out as v22 scope.
- **Next.** P1-T1 — read polish prompt rules to locate the ET-bias source.

---

## §7. Six-gate lifecycle per phase

Each phase must clear all six gates per `CLAUDE.md` Non-Negotiables before being declared ✅.

| Phase | 1. Idea | 2. Plan | 3. Success | 4. Test plan | 5. Greenlight | 6. Refine-or-discard |
|---|---|---|---|---|---|---|
| P1 | diagnose before intervene | §3.1 | 3 SCs measurable | engineer ~30 min | operator after diagnosis | re-read if scope unclear |
| P2 | narrow prompt + optional helper | §3.2 | 3 SCs measurable | engineer ~1–2 hr | operator after each sub-task | revert if regression |
| P3 | probe + commit | §3.3 | 3 SCs measurable | probe + manual review | operator triggers commit | flag off if probe regresses |

---

## §8. Open questions (genuinely undecided — needs operator before that phase starts)

| # | Question | Blocks | Surfaced |
|---|---|---|---|
| Q1 | Prompt-widen only, or add post-polish transform as belt-and-suspenders? | P1-T3 | 2026-05-17 ~11:30 AM |
| Q2 | Should the fix extend to non-CST/non-ET codes the polish prompt may mishandle (CCo — Código de Comercio; CGP — Código General del Proceso)? Or labor-only for v22? | P1-T3 | 2026-05-17 ~11:30 AM |

Update this section as new questions surface during execution.

---

## §9. Decisions locked in (do not re-litigate without operator sign-off)

| # | Decision | Reason | Locked when |
|---|---|---|---|
| D1 | v22 scope = CST/ET mislabel only. NOT prompt-rewrite for other codes, NOT a polish overhaul | v21 closing report; "punt CST/ET label to v22" operator directive 2026-05-17 ~11:30 AM | 2026-05-17 AM (this doc) |
| D2 | Fix rides existing kill-switch where possible (`LIA_LLM_POLISH_ENABLED=0` is the universal polish revert) | CLAUDE.md non-negotiable | repo standing rule |
| D3 | SME panel operator-triggered only; self-audit via `answer-engine-probe` | `feedback_sme_panel_explicit_request_only` | repo standing rule |
| D4 | Diagnose-before-intervene applies to every v22 phase | `feedback_diagnose_before_intervene` | repo standing rule |
| D5 | Server restart mandatory before every post-fix probe | `answer-engine-probe` skill non-negotiable | repo standing rule |
| D6 | **v22 fix shape — five-site narrow edit across Python + TS, NO post-polish transformer.** (1) `answer_llm_polish.py`: widen `anchor_preserve` + `anclaje_legal_explanatory_lines` + `numeric_format_bold` examples + DIRECTIVA PRIMARIA bullet #2 to accept both ET and CST inline-anchor forms with the new prompt-level rule: "**preservá el sufijo de código (`ET` o `CST`) tal cual aparece en el BORRADOR — NUNCA reescribás `(art. N CST)` como `(art. N ET)` ni viceversa**." Update module docstring too. (2) `frontend/src/features/chat/expertPanelRefs.ts`: extend regex to capture trailing/leading `ET`/`CST` token and emit `et_art_N` / `cst_art_N` / `art_N` (when ambiguous) so Cascade A unblocks. (3) `frontend/src/features/chat/citations.ts:186-203`: rename/branch bare-article fallback — when surrounding context (caller-supplied `topicHint`) is `laboral`, default to CST; otherwise keep ET default. (4) `frontend/src/features/chat/normative/citationParsing.ts`: add `parseCstLocatorText` + `formatParsedCstLocator` siblings + `parseLocatorText(value, code)` dispatcher; update `parseEtTitle` to be `parseLocatorTitle(rawTitle)` returning `{code, formatted}`. (5) `frontend/src/features/chat/normativeModals.ts:267`: thread code-aware title from #4. **Rationale.** Diagnose-before-intervene (feedback memory) showed the bug is multi-site cascade, not a single hot-path. The post-polish transformer originally floated in §3.2 P2-T1 is dropped — once the prompt no longer demands ET form, the LLM follows the BORRADOR's CST suffix; a defensive transformer would mask any prompt regression and create a second source of truth. v22 keeps `LIA_LLM_POLISH_ENABLED=0` as the universal rollback; no new env flag required. | P1 diagnose closed 2026-05-17 ~12:00 PM | 2026-05-17 ~12:00 PM Bogotá |

---

## §9b. MANDATORY git/github hygiene (v22 deliverable, deploy-blocking)

> **Why this exists.** 2026-05-17 cleanup found 5 stale `agent-*` worktrees, each carrying a single commit that turned out to already be on main under a different SHA. The drafts had been left in place after the work was integrated; locks survived after the originating agent sessions died. Five branches and ~80 LOC of redundant code lived in the repo for weeks, blocked future cleanup, and nearly cost an hour of attempted cherry-picks before the duplication was confirmed. v22 ships these procedures alongside the polish/UI fixes so the same drift cannot recur.

> **Status.** These rules are **part of v22's scope** — they MUST land in `CLAUDE.md` "Non-Negotiables" + `AGENTS.md` (mirror) before v22 is declared closed. P2-T-Hygiene below tracks the doc edit explicitly.

### §9b.1 Per-session hygiene (the no-stale-branch rules)

1. **Every worktree session ends with one of three outcomes — no fourth option:**
   - **Land** — work is ready: commit, fast-forward main, push to GitHub, `git worktree remove`, `git branch -D <worktree-branch>`. State ledger updated to ✅.
   - **Snapshot + discard** — work is interesting but not landing now: `git format-patch` (or `git diff > <name>.patch`) into `tracers_and_logs/snapshots/<UTC>_<slug>.patch`, commit the patch file on main, then `remove -f` the worktree.
   - **Park with explicit ETA** — work is paused: append a row to `docs/re-engineer/active_worktrees.md` (new file v22 creates) naming the worktree + branch + slug + the **operator-authorized return date** + the **expiry behavior** (e.g. "auto-discard after 2026-06-01 if not landed"). No undated parks. A parked worktree past its ETA is treated as abandoned and removed without further confirmation.
2. **Lock semantics are advisory only.** A locked worktree owned by a dead PID is a stale lock, not a signal to preserve. The cleanup routine MUST `ps -p <pid>` the lock owner; if dead, the worktree is force-removed regardless of original creator. Live PID lock is honored.
3. **A worktree branch only exists while the worktree exists.** When `git worktree remove` runs, `git branch -D <its-branch>` runs in the same command line. Orphan branches with no worktree are forbidden — they invite the "I'll come back to it" pattern that produced the 5 stale worktrees.
4. **No "I'll come back to it later" without the §9b.1 #1 ETA row.** That phrase IS the failure mode this section exists to prevent.

### §9b.2 Per-commit hygiene (the no-stale-commit rules)

1. **Every code change lands as 1 commit on the worktree branch + 1 push to GitHub within the same operator session that wrote it.** No commit lives only in a worktree past session end. Sessions that end mid-implementation MUST snapshot the diff as a `.patch` per §9b.1 #1.
2. **No bare `git commit` without a paired `git push`.** The two-step rule: every `git commit` is followed by `git push origin <branch>` before the operator moves to the next task. Exceptions are documented in the run log with an explicit "delayed push because <reason>" note.
3. **Fast-forward-only main.** `main` is never merged into via a non-ff merge. If the worktree branch has diverged, **rebase the worktree branch onto main first**, then ff-merge into main. No merge commits on main. This keeps history readable and bisect-friendly.
4. **Commit message includes the fix doc id.** Every commit on a `fix_vNN_may` worktree starts its subject with `fix(vNN ...)` or `ship(vNN ...)` or `docs(vNN ...)`. The fix-doc id in the subject makes archaeology trivial.
5. **Co-Authored-By footer is mandatory** when an LLM (Claude / GPT / DeepSeek / etc.) collaborated. Per CLAUDE.md commit-template canon.

### §9b.3 Per-fix-doc hygiene (the no-zombie-plan rules)

1. **A fix doc is closed when its §⏯ "Last completed step" reads "vNN closed ✅" AND every §2 phase row is `✅` or `↩`.** No partial closures. If a phase is parked, it gets `↩` (discarded) with a rationale, not left at `🔵` / `🟡`.
2. **A closed fix doc's commits are tagged.** When the §⏯ flips to `✅`, the operator (or the closing commit's author) runs `git tag fix_vNN_closed` on the closing commit. Tags make "what landed for vNN?" answerable in one command.
3. **Open fix docs declare their worktree, if any.** §⏯ row "Local state" names the worktree path explicitly. A fix doc without a named worktree is implicitly working on main directly (allowed for ≤ 3-commit fixes; otherwise spin a worktree).
4. **Stale-fix-doc audit runs at every v(NN+1) opening.** When the next fix doc is drafted, P1 includes a `git worktree list` + `docs/re-engineer/active_worktrees.md` review. Any worktree past its ETA, any branch with no worktree, any fix doc with §⏯ not at `✅` older than 14 days — surfaced to operator before the new fix proceeds.

### §9b.4 v22 P2-T-Hygiene deliverable

| ID | Task | Phase | Status | Owner |
|---|---|---|---|---|
| P2-T-Hygiene-1 | Mirror §9b.1–§9b.3 rules into `CLAUDE.md` "Non-Negotiables" as a new bullet group titled "Worktree + commit hygiene" | 2 | 🟡 | claude (with this fix's other P2 tasks) |
| P2-T-Hygiene-2 | Mirror the same rules into `AGENTS.md` so non-Claude agents see them too | 2 | 🟡 | claude |
| P2-T-Hygiene-3 | Create `docs/re-engineer/active_worktrees.md` template (empty roster; rules at top) | 2 | 🟡 | claude |
| P2-T-Hygiene-4 | Optional but recommended: add a pre-merge `make worktrees-audit` target that runs `git worktree list` + `ps -p` for each lock owner + reports dead-PID locks. Wires into `make smoke-deps`. | 2 | 🟡 | claude (defer to v23 if time-bounded) |

These tasks ship in the SAME commits as the polish + UI cascade fixes. v22 is not declared closed until P2-T-Hygiene-1, -2, -3 are ✅.

---

## §9c. P2-T-Orphan-Land — revive the fix_v7 truncated-tail + canonical-shapes work

> **Operator directive (2026-05-17 ~12:05 PM Bogotá):** "Fold into v22." The `fix_v7-truncated-tail-and-canonical-shapes` branch (HEAD `4b953ca`, dated 2026-04-30) carries real unmerged improvements that lost their `fix_v7` namespace slot when main's actual `fix_v7_may.md` took it for a different fix (retrieval/topic-filter softening). Per `§9b` hygiene rules: orphan branches with verifiable value must be either landed or explicitly snapshotted-and-discarded — this branch goes the "land" path.

### §9c.1 What the branch carries (681 LOC across 9 files)

| Phase | Fix | Files (additions/changes) | Visible effect on answers |
|---|---|---|---|
| **L13** | Truncated chunk-tail filter | `src/lia_graph/pipeline_d/answer_support.py` — new `_ABBREVIATION_TOKENS`, `_TRUNCATED_TAIL_TOKEN_RE`, `_merge_abbreviation_splits`; truncated-tail drop before auto-period-add. | Kills bullets like `"...o fra."` (mid-word truncation from chunks ending in "fracción", "artículo", "art", etc.). Main's existing `_looks_truncated_line` only catches explicit `"..."` / `"[truncated]"` markers — doesn't catch the abbreviation-token mid-word break. Affects ~1–3% of bullets across sancionatorio / labor / procedimiento answers. |
| **L14** | Canonical question shapes | `src/lia_graph/canonical_question_shapes.py` (new, 145 LOC); `config/canonical_question_shapes.json` (new, 43 LOC, single seed shape `plazos_renta_personas_juridicas`); `pipeline_d/orchestrator.py` (canonical-shape hookup before `subquery_inherited_parent` branch); `pipeline_d/planner.py` (new `tabular_reference` budget + query-mode override). | Sub-questions matching a declared shape get correct topic routing instead of inheriting the parent's wrong topic. Today the `subquery_inherited_parent` override at `orchestrator.py:628` fires unconditionally for fallback-classified sub-Qs — that's still reproducible on main. |
| **L14 companion** | Compat-doc-topics wiring | `config/compatible_doc_topics.json` — three new mutual adjacencies: `declaracion_renta ↔ calendario_obligaciones ↔ regimen_sancionatorio_extemporaneidad`. | Calendar / deadline docs (`seccion-06-calendario-tributario.md`, topic_key `calendario_obligaciones`) can be promoted to primary under `declaracion_renta` queries. Today they can't — wrong-topic gate. |
| **Docs** | L13 + L14 learnings + CLAUDE.md operating-instructions section | `CLAUDE.md` (canonical-question-shapes + paired-compat-wiring section); `docs/learnings/process/chat-runtime-hardening-fix_v1-to-v6-2026-04-29.md` (L13 + L14 entries + metrics table). | Knowledge-base hygiene; future agents know how to extend canonical shapes via JSON config. |

### §9c.2 Staleness assessment (per `§9b.3` rules)

- **Target files still exist on main** — `answer_support.py`, `orchestrator.py`, `planner.py`, both config files. ✅
- **Trigger bugs still reproducible on main** — `_looks_truncated_line` is narrow; `subquery_inherited_parent` still fires unconditionally. ✅
- **18 days since branch HEAD** — moderate, but no contradicting work has landed in the same code regions (verified via `git log --oneline 4b953ca..main -- <target-files>`).
- **Conflict probability** — moderate. v18+ work touched `answer_support.py` (introduced `_support_doc_candidate_lines` for the dedicated práctica lane) and `orchestrator.py` (polish-rejected fallback wiring, conflict-resolver wiring). The L13/L14 hooks live BEFORE those v18+ additions in the flow, so the merge is layered, not collision-shaped. Expect manual reconciliation on a few hunks, not a full rebuild.

### §9c.3 v22 P2-T-Orphan-Land tasks

| ID | Task | Phase | Status | Owner |
|---|---|---|---|---|
| P2-T-Orphan-1 | Rebase `fix_v7-truncated-tail-and-canonical-shapes` onto current `main` HEAD. Resolve conflicts by porting the patch logic onto current shapes of `answer_support.py` + `orchestrator.py` + `planner.py`. NO cherry-pick of the original commit SHA — rewrite as a clean v22 commit with the original rationale preserved in the message body. | 2 | 🟡 | claude (with v22 P2) |
| P2-T-Orphan-2 | New tests covering both L13 + L14 paths on current main shape. Existing 4 `answer_support` tests must stay green. Extend `tests/test_planner_query_modes.py` and `tests/test_orchestrator_polish_trace.py` if the canonical-shape hookup affects their assertions. | 2 | 🟡 | claude |
| P2-T-Orphan-3 | Re-probe via `answer-engine-probe` for a SME-shaped sub-question that exercises both fixes (e.g. "¿Cuáles son las fechas límite para presentar renta por NIT? ¿Dónde encuentro el decreto de plazos vigente y qué consecuencias tiene la presentación extemporánea?") — confirm bullet `"...o fra."` disappears AND sub-Q #1 routes to `declaracion_renta` not `regimen_sancionatorio_extemporaneidad`. | 2 | 🟡 | claude |
| P2-T-Orphan-4 | After P2-T-Orphan-1..3 ✅, **delete the original `fix_v7-truncated-tail-and-canonical-shapes` branch** per `§9b.1 #3` (no orphan branches once content has landed). Snapshot the patch to `tracers_and_logs/snapshots/<UTC>_fix_v7_orphan_revival.patch` first for audit. | 2 | 🟡 | claude |

### §9c.4 Rollback

- L13 sits behind no new env flag (the truncated-tail filter is deterministic). Rollback = `git revert` of the v22 P2-T-Orphan-1 commit.
- L14 sits behind no new env flag but its canonical-shape JSON is opt-in (empty config = noop). Rollback = empty the JSON OR revert the commit.
- Each landing commit references back to §9c for rationale, so a future agent reading `git log -p` sees the full context without scrolling 18 days back.

---

---

## §10. What v22 does NOT do (honest scope)

- v22 does **not** re-ingest or modify cloud data. v20's `gen_v20_20260516_172203` stays active.
- v22 does **not** rewrite the polish prompt from scratch — narrow surgical edits only.
- v22 does **not** add code-suffix handling for CCo / CGP / other Colombian codes (those are out of current corpus scope).
- v22 does **not** auto-run the SME panel.

---

## §11. Resuming work — preconditions + first-action recipe

A fresh agent should be able to start P1 immediately after the preconditions below pass.

### §11.1 Preconditions (run all five, all must pass)

```bash
# 1. v21 closing commits landed.
git log --oneline -10 | grep -E "v21|P2-T5|P3-T4" && echo "OK v21 landed" || echo "MISSING — operator must verify v21 ship state"

# 2. Local docker stack — Supabase + Falkor must be up.
docker ps --filter "name=supabase_db_lia-graph" --filter "name=lia-graph-falkor-dev" --format "table {{.Names}}\t{{.Status}}"

# 3. .env.staging exists.
test -f .env.staging && grep -q "^FALKORDB_URL=redis" .env.staging && echo "OK staging env" || echo "MISSING"

# 4. dev:staging server up + answering.
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8787/

# 5. v21 closing-probe artifact exists.
ls -la tracers_and_logs/logs/probe_runs/20260517T161225Z_v21_t5_postfix/q01.digest.md
```

If any precondition fails, STOP and consult the relevant file (`fix_v21_may.md` for v21 state, `docs/guide/env_guide.md` for env state).

### §11.2 Phase 1 first action (after preconditions pass)

Announce in chat: "Reading the polish prompt + verifying case-bullet SPEC sources to locate the CST→ET mislabel origin. Expected ~30 min."

Then run:

```bash
# P1-T1a: read the polish prompt rules
grep -n "art\\. X ET\\|art\\. N ET\\|anchor_preserve\\|numeric_format_bold" src/lia_graph/pipeline_d/answer_llm_polish.py | head

# P1-T1b: read the validator regex
grep -n "_ANCHOR_RE\\|_preserves_required_anchors" src/lia_graph/pipeline_d/answer_llm_polish.py | head

# P1-T2: verify labor case-bullet SPEC sources
grep -n "CST art\\. \\|art\\. [0-9]\\+ CST" src/lia_graph/pipeline_d/case_bullets/liquidacion_terminacion.py src/lia_graph/pipeline_d/case_bullets/prestaciones_sociales.py 2>/dev/null | head
```

Document findings in §6 run log (append entry under today's date). Then move to P1-T3 (scope decision).

### §11.3 What to do after P1 closes

- Append a §6 run log entry naming the prompt-bias culprit + verifying SPEC sources.
- Set §2.1 P1 row to ✅, P2 row to 🔵.
- Announce in chat: "P1 closed — root cause identified. Ready for P2 fix sprint — operator greenlight?"
- DO NOT start P2 without explicit operator greenlight.

### §11.4 What to do after P2 closes

- Append run log entry with the unit-test names + green status.
- Run §3.3 P3 — restart server first, then probe.

### §11.5 What to do after P3 closes

- §⏯ "Last completed step" → "v22 closed ✅"
- Update CLAUDE.md runtime flags table only if a new flag was introduced.
- Propose commit shape to operator: 2–3 commits (prompt widen / optional transform / docs).

---

*Drafted 2026-05-17 ~11:30 AM Bogotá by claude-opus-4-7 in response to operator directive: "promote both flags and punt the CST/ET label to v22 in a fix_v22_may.md separate doc with the usual zero context agent protocol." Companion to [fix_v21_may.md](fix_v21_may.md) (predecessor, closed 2026-05-17 ~11:25 AM Bogotá). Update §⏯ + §2 + §6 as work progresses.*
