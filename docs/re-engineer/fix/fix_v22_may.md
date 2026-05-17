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
| Last completed step | **v22 doc drafted (initial)** — plan + state-tracker scaffolded. No code edits yet. v21 closed ✅; cloud + main + GitHub all carry the v21 fixes. |
| Last touched UTC | 2026-05-17T16:30:00Z (2026-05-17 ~11:30 AM Bogotá) |
| Next step | **P1-T1** — read the polish prompt at `src/lia_graph/pipeline_d/answer_llm_polish.py` (lines 60–170 — the `POLISH_RULES` tuple, especially `anchor_preserve` and the `numeric_format_bold` ET-exception clauses) and identify where the prompt forces `(art. X ET)` as the canonical inline form. Decide whether the fix is in the PROMPT (loosen the rule to accept `(art. X CST)` when topic=laboral), in the VALIDATOR (`_preserves_required_anchors` regex `_ANCHOR_RE` matches `(arts?\. … )` agnostic of ET/CST already, so this may be a prompt-only issue), or in the SYNTHESIS template (whether the source bullets already carry the right form). |
| Working artifact | v21 closing probe `tracers_and_logs/logs/probe_runs/20260517T161225Z_v21_t5_postfix/q01.json` — the artifact where the CST→ET mislabel surfaces. Diff against case-bullet SPEC source `src/lia_graph/pipeline_d/case_bullets/liquidacion_terminacion.py` (which correctly uses `CST art. 64` / `art. 65 CST`). |
| Cloud state | v20 active: cloud Supabase `gen_v20_20260516_172203` is_active=true; cloud Falkor 10,217 ArticleNodes (3,410 with norm_id including `cst.art.64`), 3,401 TEMA edges. **v22 does NOT touch cloud data** — only the polish step + possibly the synthesis template. |
| Local state | Worktree `fix-v22-may` not yet created. Engineer should spin one via `EnterWorktree` (or fallback git worktree) before any code edit. |
| Uncommitted code changes | None expected at v22 start. v21 P3-T4 flag flips landed in `8b8df7a..177b3d8 + 8b8df7a` (3 commits): polish validator + détector widen + bail-out content-size + flag promotion. |
| Heartbeat / monitor state | None active. |
| If crashing now, resume with | (1) `git log --oneline -5` — verify v21 closing commits present (look for `fix(v21 P2-T5)` + `ship(v21 P3-T4)` refs). (2) `git status` — should show only v22 doc work uncommitted. (3) `curl 127.0.0.1:8787 → 200` (dev:staging running). (4) Open `tracers_and_logs/logs/probe_runs/20260517T161225Z_v21_t5_postfix/q01.digest.md` — the artifact carrying the CST→ET mislabel. (5) Continue at "Next step" above. |
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
| P1 | Diagnose (locate ET-bias in polish prompt + validate case-bullet SPEC source) | 🟡 not started | — | — |
| P2 | Fix (polish prompt widening for CST + tests) | 🟡 not started | — | — |
| P3 | Re-probe + commit | 🟡 not started | — | — |

Status legend: 🟡 not started · 🔵 in progress · ✅ done · 🚫 blocked · ↩ discarded.

### §2.2 Active blockers

| # | Blocker | Affects | Owner | Surfaced |
|---|---|---|---|---|

(none open as of 2026-05-17 ~11:30 AM)

### §2.3 Active tasks (rolls up from §3 phases)

| ID | Task | Phase | Status | Owner | Blockers | Last touched |
|---|---|---|---|---|---|---|
| P1-T1 | Read `answer_llm_polish.py` POLISH_RULES (esp. `anchor_preserve` + `numeric_format_bold`). Identify where the `(art. X ET)` form is enforced as canonical. | 1 | 🟡 | — | — | — |
| P1-T2 | Verify case-bullet SPEC sources for labor topics use `CST art. N` / `art. N CST` form (sample: `case_bullets/liquidacion_terminacion.py`, `prestaciones_sociales.py`). If sources are correct, the bug is purely in polish; if sources are inconsistent, fix source first. | 1 | 🟡 | — | — | — |
| P1-T3 | Decide approach: (a) widen polish prompt to honor both forms, (b) add post-polish transform `(art. <num> ET) → (art. <num> CST)` when topic=laboral AND num ∈ CST namespace, (c) both. Write decision to §9. | 1 | 🟡 | — | P1-T1, P1-T2 | — |
| P1-T4 | Cascade A — locate `extractArticleRefs` at `frontend/src/features/chat/expertPanelRefs.ts:1-14` and decide whether to (a) emit code-aware refs (`cst_art_N` / `et_art_N`) when the surrounding text identifies the code, or (b) fix only via the polish side and rely on the polished text now saying CST. | 1 | 🟡 | — | P1-T1 | — |
| P1-T5 | Cascade B — locate the Soporte Normativo panel renderer (probably `frontend/src/features/chat/normative/` or `ui_chat_payload.py` citation serializer). Document the two failures: hardcoded "Estatuto Tributario" string + the "0 referencias" counter divergence from the actual list count. | 1 | 🟡 | — | — | — |
| P2-T1 | Implement chosen approach + unit test in `tests/test_polish_cst_form_preserved.py` | 2 | 🟡 | — | P1-T3 | — |
| P2-T2 | Run focused test sweep (polish + détector + synthesis + per-case) — must stay 326/326 green | 2 | 🟡 | — | P2-T1 | — |
| P3-T1 | Restart dev:staging server (kill + relaunch) | 3 | 🟡 | operator | P2 ✅ | — |
| P3-T2 | Re-run `answer-engine-probe` on q01 (CST labor) + q03 (ET tax regression guard) | 3 | 🟡 | — | P3-T1 | — |
| P3-T3 | Judge verdicts — q01 must show `(art. X CST)` form, q03 must keep `(art. X ET)` form correct | 3 | 🟡 | — | P3-T2 | — |
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
