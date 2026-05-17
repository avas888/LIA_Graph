# fix_v21_may.md — answer-shape fix (close the gap v20's probe exposed) — v1

> **Zero-agent-context protocol.** Self-contained. A fresh agent with no prior conversation can execute it by reading this file + the filesystem. Verify every artifact against `git ls-files`. If something doesn't exist, STOP and report drift.
>
> **Scope.** v20 fixed the *data layer* (collision-free `norm_id`-stamped corpus in cloud) and the *lookup layer* (planner emits dotted ids, retriever MATCHes on `norm_id`). v20's closing probe proved the retrieval works end-to-end. But the *user-visible answer* was still wrong: polish rejected with `invented_norm_lineage`, and the rejection-fallback grabbed off-topic práctica bullets (cesación codes 54-58 + recargos nocturnos) instead of CST 64's terminación-indemnización specifics. v21 fixes that downstream answer-shape regression so an accountant asking "¿Qué dice el artículo 64 del CST?" gets the right answer.
>
> **Companion docs.** [`fix_v20_may.md`](fix_v20_may.md) — v20 plan + run log. [`fix_v19_may.md`](fix_v19_may.md) — v19 plan (schema + loader + 1,300-node migration). [`../state_fix_v19_may.md`](../state_fix_v19_may.md) — v19's execution ledger. This doc (v21) combines plan + state.

---

## §⏯ Crash-resume pointer (update this block after EVERY step)

**Read order if you are a fresh agent resuming after a crash:** §⏯ (here) → §-1 → §11.1 preconditions → the "Next step" pointer below.

| Field | Value |
|---|---|
| Last completed step | **v21 doc drafted (initial)** — plan + state-tracker scaffolded. No code edits yet. |
| Last touched UTC | 2026-05-17T01:50:00Z (2026-05-16 ~08:50 PM Bogotá) |
| Next step | **P1-T1** — open `q01.digest.md` + `q01.json` from `tracers_and_logs/logs/probe_runs/20260517T013419Z_v20_labor_collision/` and inspect the polish prompt + the `_no_invented_norm_lineage` validator decision. Decide whether the rejection is right-but-overreaching, or wrong-and-buggy. |
| Working artifact | Probe run `tracers_and_logs/logs/probe_runs/20260517T013419Z_v20_labor_collision/` — the failing q01 trace is the input to diagnose the polish + práctica bugs. |
| Cloud state | v20 active: cloud Supabase `gen_v20_20260516_172203` is_active=true; cloud Falkor 10,217 ArticleNodes (2,177 with norm_id, 0 duplicates), 3,401 TEMA edges. **v21 does NOT touch cloud data** — only the served-answer pipeline. |
| Local state | iter2 bundle still frozen + chmod -w at `artifacts/v20/local_rehearsal_iter2/`. Local Falkor has the same iter2 graph state. |
| Uncommitted code changes | v20 P4 work in `src/lia_graph/pipeline_d/{planner,retriever,retriever_falkor}.py` + `case_bullets/_registry.py` + tests. Will be committed before v21 P1-T1 fires (per operator directive). |
| Heartbeat / monitor state | None active. |
| If crashing now, resume with | (1) `git log --oneline -5` — verify v20 P4 commit landed (look for `ship(v20)` ref). (2) `git status` — should show only v21 doc work uncommitted. (3) `curl 127.0.0.1:8787 → 200` (dev:staging running). (4) Open `tracers_and_logs/logs/probe_runs/20260517T013419Z_v20_labor_collision/q01.digest.md` — the failing-probe artifact. (5) Continue at "Next step" above. |
| Hard rule | After EVERY task transition, update this block + §2 phase/task tables + append a §6 run log entry. Do not batch updates. |

---

## §-1. If you are a fresh agent — read this first

You are picking up a **one-question-one-fix project**. v20 closed the whole-corpus collision fix. v21 closes ONE remaining gap that v20's closing probe surfaced: the served answer for a labor article lookup is wrong because of two downstream bugs.

**Read in this order before touching anything (max 20 min):**

1. `CLAUDE.md` (repo root) — repo operating guide. "Fast Decision Rule" + the `LIA_POLISH_REJECTED_FALLBACK_*` flag rows are load-bearing.
2. `AGENTS.md` (repo root) — layer ownership (surface boundaries between `main chat` / `Normativa` / `Interpretación`).
3. **This file** §0 → §1 → §2 → §3.
4. [`fix_v20_may.md`](fix_v20_may.md) §6 "08:35 PM Bogotá" entry — diagnoses the same two bugs from the v20 perspective.
5. `tracers_and_logs/logs/probe_runs/20260517T013419Z_v20_labor_collision/q01.digest.md` — the failing trace.

**Hot facts you must know before touching anything:**

- **Default run mode is `dev:staging`** — cloud Supabase + cloud Falkor (`LIA_REGULATORY_GRAPH`). Assume staging.
- **Cloud writes for Lia Graph are pre-authorized** — announce in chat before executing, no per-action confirmation needed. v21 doesn't write to cloud — only restarts the dev:staging server when probing post-fix.
- **MANDATORY server restart before EVERY probe.** A long-running `npm run dev:staging` pins yesterday's code; my v21 fixes won't take effect until the server is killed + re-launched.
- **SME panel is OFF-LIMITS** — use `answer-engine-probe` skill for self-audit (per `feedback_sme_panel_explicit_request_only` + operator directive 2026-05-16 PM).
- **Polish path is fragile.** Three flags (`LIA_POLISH_REJECTED_FALLBACK_MODE`, `LIA_POLISH_REJECTED_FALLBACK_FILTER`, `LIA_POLISH_UVT_VALIDATOR`) gate the polish-rejection behavior. Toggle these to isolate which one fires the bug.
- **Beta-stance applies** — every non-contradicting improvement flag flips ON across all three run modes. v21 follows this in P3.
- **No text walls in docs.** Per `feedback_no_text_walls` — bullets/lists/tables only.

**Operator's intent (boss directive, 2026-05-16 ~08:50 PM Bogotá):**

- Quote: "input status and advancement and next steps into new document fix_v21_may.md — use zero context agent protocol, manage state with detail."
- Translation: v21 inherits v20's pattern (zero-agent-context protocol, exhaustive state ledger, §⏯ crash-resume block kept fresh) and tackles the one user-visible bug v20's probe exposed.

**Memory-pinned guardrails (do not violate):**

- Diagnose before intervene — measure where failures concentrate before proposing a fix.
- Granular edits — don't append helpers to ≥1000-LOC files; extract to a focused sibling module.
- No text walls; no money quoting; no SME panel auto-run.
- Recommendations live in the canonical plan (this file), not just chat.
- Default run mode = dev:staging.

**The big picture in two sentences:**

- The v20 retrieval fix delivers the right article anchor (`cst.art.64`) and the right citations (CST + Ley 50/1990 + Ley 2466/2025) to the synthesis layer. The synthesis layer then drops the ball: polish rejects the LLM output with `invented_norm_lineage`, and the rejection-fallback path serves off-topic práctica bullets.
- v21 fixes the polish over-rejection and the práctica chunk-selection so that an accountant asking about a labor article gets a substantive labor answer, not a fallback dump of unrelated playbook bullets.

---

## §0. TL;DR

- **The gap v21 closes.** v20's closing probe (`q01: ¿Qué dice el artículo 64 del CST?`) passed retrieval but failed user-visible answer. Polish rejected for `invented_norm_lineage`; rejection-fallback grabbed off-topic práctica chunks. Both fixable in `pipeline_d/answer_*` modules.
- **Why v21 exists.** Without it, v20's data + lookup fix doesn't translate into a better accountant experience — the answer reads as wrong even though the article anchor is correct.
- **3 phases.** P1 diagnose (read probe trace, isolate which path emits the bad bullets). P2 fix (narrow edits in `answer_llm_polish.py` + `answer_synthesis_practica.py`). P3 re-probe + flag promotion (push the v18 b1/b2 práctica + conflict-resolver flags from shadow to enforce if the bug is gone).
- **Time budget.** P1: ~30 min reading + 1 hr code trace. P2: 2-4 hrs engineering + tests. P3: probe + flag promotion ~30 min. Total: half-day to one day.
- **Risk.** All edits are reversible by env-flag toggle (the polish + práctica behaviors are already feature-flagged). 301 v18 baseline tests must stay green.
- **Estado al 2026-05-16 ~08:50 PM Bogotá.** P1 🟡 ready to start.

---

## §1. Where we are right now (v20 close-state)

### §1.1 What v20 landed (do not re-do)

- ✅ **Cloud data layer**: 10,217 ArticleNodes (2,177 with `norm_id`, 0 duplicates). 3,401 TEMA edges (was 0 pre-v20). Generation `gen_v20_20260516_172203` active in cloud Supabase.
- ✅ **Lookup layer**: `pipeline_d/planner.py` emits dotted `norm_id`s (`cst.art.64`, `et.art.115`). `pipeline_d/retriever_falkor.py` does property-split dual-mode MATCH (norm_id pass + article_number pass, indexed both ways). `pipeline_d/retriever.py` (artifact-mode) accepts either form via codec-stripping fallback.
- ✅ **Test suite**: 447/448 curated tests pass. 1 known failure (`test_phase3_pipeline_d_tax_planning_prompt_uses_rich_advisory_first_bubble`) is a polish-content quirk, not a retrieval regression.
- ✅ **End-to-end probe confirms retrieval**: `q01` trace shows `retriever.supabase.entry.query_text_preview = "Articulo cst.art.64 laboral"` — the planner emits dotted norm_id, retriever queries correctly, 3 primary + 3 connected articles surface.

### §1.2 What v20 left undone (this is v21's mandate)

| Gap | Concretely | Evidence | Module path |
|---|---|---|---|
| Polish over-rejection on labor context | `polish.applied.skip_reason = "invented_norm_lineage"` fired on `q01` even though the polish output was a fair summary of CST 64. The structural validator (`_no_invented_norm_lineage` or similar) was tuned for tax/UVT cases and over-fires on labor citations that legitimately reference Ley 50/1990 + Ley 2466/2025. | `q01.digest.md` line `polish.applied … skip_reason=invented_norm_lineage … polished_chars=128` | `src/lia_graph/pipeline_d/answer_llm_polish.py` |
| Práctica chunk-selection grabs wrong bullets | Rejection-fallback served cesación codes 54-58 + recargos nocturnos bullets from `playbook_laboral_liquidacion_terminacion.md` — the playbook DOES live under the right topic but the chunk-selector grabbed unrelated sections. | `q01.digest.md` "answer_concise" + "answer_markdown" — bullets about codes 54-58 and recargos jornada nocturna, not terminación-indemnización | `src/lia_graph/pipeline_d/answer_synthesis_practica.py::_candidate_lines_from_chunk` |
| SubTopicNode parity gap (carryover from v20 known-gap) | Replay-script-built `article_subtopics` is empty because `canonical_corpus_manifest.json` carries `subtopic_key` from the legacy audit pass only, NOT from the v6 classifier's enriched output. Cloud has 94 SubTopicNodes (25 surplus from pre-v20 runs); local iter2 has 69. Bit-identity broken. | `fix_v20_may.md` §6 "12:23 PM Bogotá" entry, "Known gap" line. | `src/lia_graph/ingest_reports.py::_build_canonical_corpus_manifest` (manifest builder) OR a sidecar artifact built from `events.jsonl` |
| P5-T1/T2 carryover from v20 (A2 validator + shadow harness) | v20 plan had P5-T1 (numeric validator on `answer_conflict_resolver.py::resolve_via_a2`) + P5-T2 (`scripts/shadow_diff_harness.py`). Neither shipped because P4 closure took longer than budgeted. | `fix_v20_may.md` §3.5 (defined) + §2.3 (status: 🟡 not started). | `src/lia_graph/pipeline_d/answer_conflict_resolver.py` + `scripts/` |

### §1.3 The non-negotiable invariants v21 must preserve

- **Cloud data stays as-is.** v21 does NOT re-ingest, re-replay, or modify any Falkor / Supabase data. Only `answer_*.py` and possibly `ingest_reports.py` / a new sidecar script.
- **The v20 collision fix remains active.** `retriever.supabase.entry.query_text_preview` MUST continue to say `Articulo cst.art.64 laboral` (or equivalent dotted form) for labor probes.
- **v18 baseline tests must stay green** — 301 tests + the 447 from v20 P4. Same `make test-batched` rule.
- **Polish flags are kill-switches.** `LIA_POLISH_REJECTED_FALLBACK_MODE`, `LIA_POLISH_REJECTED_FALLBACK_FILTER`, `LIA_POLISH_UVT_VALIDATOR` must remain togglable per CLAUDE.md non-negotiables.
- **No new corpus retirements.** Standing rule per CLAUDE.md.

---

## §2. State tracker (live — update this section as work progresses)

### §2.1 Phase status

| Phase | Description | Status | Owner | Last touched |
|---|---|---|---|---|
| P1 | Diagnose (read probe trace + isolate paths) | 🟡 not started | — | — |
| P2 | Fix (polish over-rejection + práctica chunk-selection + optional subtopic parity) | 🟡 not started | — | — |
| P3 | Re-probe + flag promotion + commit | 🟡 not started | — | — |

Status legend: 🟡 not started · 🔵 in progress · ✅ done · 🚫 blocked · ↩ discarded.

### §2.2 Active blockers

| # | Blocker | Affects | Owner | Surfaced |
|---|---|---|---|---|

(none open as of 2026-05-16 ~08:50 PM)

### §2.3 Active tasks (rolls up from §3 phases)

| ID | Task | Phase | Status | Owner | Blockers | Last touched |
|---|---|---|---|---|---|---|
| P1-T1 | Read `q01.digest.md` + `q01.json` from the v20-closing probe; understand WHICH `invented_norm_lineage`-style validator fired and WHY | 1 | 🟡 | — | — | — |
| P1-T2 | Trace the rejection-fallback path → identify which chunks the práctica-selector pulled and why those instead of terminación-indemnización bullets | 1 | 🟡 | — | P1-T1 | — |
| P1-T3 | Decide scope: (a) just fix the polish over-reject, (b) just fix the práctica selector, (c) fix both. Write decision to §9. | 1 | 🟡 | — | P1-T1, P1-T2 | — |
| P2-T1 | Polish over-rejection fix — narrow edit in `answer_llm_polish.py` + new unit test in `tests/test_polish_*.py` (or extend an existing one) | 2 | 🟡 | — | P1-T3 | — |
| P2-T2 | Práctica chunk-selection fix — narrow edit in `answer_synthesis_practica.py::_candidate_lines_from_chunk` + unit test | 2 | 🟡 | — | P1-T3 | — |
| P2-T3 | Optional: SubTopicNode parity fix — events.jsonl-based sidecar enrichment OR `_build_canonical_corpus_manifest` patch to include classifier-output subtopic_key | 2 | 🟡 | operator | P2-T1, P2-T2 | — |
| P2-T4 | Re-run focused test subset (planner, retriever, polish, práctica) — must stay green | 2 | 🟡 | — | P2-T1, P2-T2 | — |
| P3-T1 | Restart dev:staging server (kill + relaunch); confirm fresh PID + start-time | 3 | 🟡 | operator | P2 ✅ | — |
| P3-T2 | Re-run `answer-engine-probe` skill with same q01 + a second labor case (q02 from v20 probe — indemnización days for 5-year contract) | 3 | 🟡 | — | P3-T1 | — |
| P3-T3 | Judge verdicts vs rubric — both must pass. If pass → P3-T4. If fail → return to P1-T3. | 3 | 🟡 | — | P3-T2 | — |
| P3-T4 | Flag promotion — flip `LIA_PRACTICA_NOISE_FILTER` + `LIA_CONFLICT_RESOLVER_MODE` from `shadow` to `enforce` per beta-stance (only if both probes pass) | 3 | 🟡 | — | P3-T3 ✅ | — |
| P3-T5 | Commit v21 work + update §⏯ "Last completed step" to "v21 closed ✅" | 3 | 🟡 | operator | P3-T4 | — |

---

## §3. The plan — 3 phases

### §3.1 Phase 1 — Diagnose (~1.5 hr)

**Idea.** Read the failing probe artifact + the related code paths. Confirm root causes BEFORE writing any fix. Per `feedback_diagnose_before_intervene`.

**Plan narrow.**

1. **P1-T1: read `q01.digest.md`** — surface the polish event payload:
   - `polish.applied.skip_reason` value (exact string)
   - `polish.applied.adapter_class` / `model` (which LLM produced the rejected output)
   - `polish.applied.polished_chars` (output size — 128 chars in v20-closing probe = practically empty)
2. **Find the validator that emitted `invented_norm_lineage`** — `grep -rn "invented_norm_lineage" src/lia_graph/pipeline_d/`. Likely lives in `answer_llm_polish.py` near `_no_invented_norm_lineage` or similar. Read it. Understand the regex / structural rule it enforces.
3. **P1-T2: trace the rejection-fallback** — `grep -rn "polish_rejected_fallback\|polish_skip_reason\|GraphNativeAnswerParts" src/lia_graph/pipeline_d/`. Find `answer_polish_rejected_fallback.py`. Read the chunk-selection path it uses. Cross-check with `answer_synthesis_practica.py::_candidate_lines_from_chunk`.
4. **P1-T3: write the scope decision in §9**.

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P1-SC1 | Validator path identified (file:line) — what triggered `invented_norm_lineage` for q01's polish output | grep + read |
| P1-SC2 | Práctica chunk-selector path identified (file:line) — why cesación codes 54-58 + recargos won over terminación-indemnización bullets | grep + read |
| P1-SC3 | Scope decision recorded in §9 with rationale | doc edit |

**Test plan.** Engineer 1.5 hr. Output: diagnosis written to §6 run log.

**Rollback.** Read-only step. Nothing to roll back.

### §3.2 Phase 2 — Fix (~3-4 hr)

**Idea.** Make the narrowest possible edits to (a) the over-firing validator and (b) the práctica chunk-selector. Each edit gets a unit test that locks in the fix.

**Plan narrow per the P1-T3 scope decision.** Concrete file targets:

| Sub-task | File | Expected shape |
|---|---|---|
| P2-T1 polish validator | `src/lia_graph/pipeline_d/answer_llm_polish.py` | Narrow the `invented_norm_lineage` regex/structural rule to fire only for tax-context UVT/ET claims, NOT for labor context where Ley 50/1990 + Ley 2466/2025 citations are legitimate |
| P2-T2 práctica selector | `src/lia_graph/pipeline_d/answer_synthesis_practica.py::_candidate_lines_from_chunk` | Filter práctica bullets by case-detector intent (terminación-unilateral cue) when the playbook doc carries multiple topic sections (cesación + recargos + indemnización can all coexist in one playbook) |
| P2-T3 optional subtopic parity | `src/lia_graph/ingest_reports.py::_build_canonical_corpus_manifest` OR new sidecar `scripts/build_subtopic_sidecar.py` | Either patch the manifest builder to include classifier-enriched `subtopic_key` per doc, OR build a sidecar from `events.jsonl` and have `replay_local_artifacts_to_cloud.py` consume it |
| P2-T4 test sweep | `tests/test_polish_*.py`, `tests/test_practica_*.py`, `tests/test_planner_*.py` | All curated subsets green; no regressions in v18 baseline 301 + v20 P4 447 |

**Success criteria.**

| # | Criterion | How |
|---|---|---|
| P2-SC1 | Polish over-rejection unit test in place + green: polish output for q01-shape input does NOT trigger `invented_norm_lineage` | `pytest tests/test_polish_*.py -k labor` |
| P2-SC2 | Práctica chunk-selector unit test in place + green: for `liquidacion_terminacion` case, the selected bullets are about indemnización (not cesación codes / recargos) | `pytest tests/test_practica_*.py -k terminacion` |
| P2-SC3 | (Optional, if P1-T3 includes T3) SubTopicNode parity verified via offline-replay against iter2 bundle: predicted `article_subtopics` size matches iter2 actual (~301 bindings) | `scripts/cloud_promotion/replay_local_artifacts_to_cloud.py --dry-run` |
| P2-SC4 | Curated test suite stays at 447/448 (or better) | `make test-batched` (full) OR focused subset matching v20 P4-T7 |

**Test plan.** Engineer 3-4 hr. Each sub-task is a separate logical commit (per the v18/v20 split discipline).

**Rollback.** Each fix is behind an env flag where possible:
- Polish: `LIA_POLISH_UVT_VALIDATOR=shadow` (kill switch — existing flag from fix_v15 §3)
- Práctica: `LIA_PRACTICA_NOISE_FILTER=legacy` (existing flag from fix_v18 b1 §1.1)
- Subtopic: feature-flag the sidecar consumption in `replay_local_artifacts_to_cloud.py`

### §3.3 Phase 3 — Re-probe + flag promotion + commit (~30 min + operator wait)

**Idea.** Verify the fix end-to-end via `answer-engine-probe`, then promote relevant flags per beta-stance, then commit.

**Plan narrow.**

1. **P3-T1 restart server** — operator runs `! kill <pid> && npm run dev:staging` in their terminal so the freshly-edited code loads.
2. **P3-T2 re-probe** — same skill, same two questions as v20-closing probe:
   - q01: "¿Qué dice el artículo 64 del CST sobre la terminación sin justa causa del contrato de trabajo?"
   - q02: "¿Cuáles son los días que tengo que pagar de indemnización si despido sin justa causa a un trabajador con contrato a término indefinido y 5 años de antigüedad?"
3. **P3-T3 judge** — both must pass the rubric in `references/rubric.md`. q01 must cite CST 64 terminación-unilateral text + correct labor citations. q02 must cite CST 64 + the 30-days + 20-days/year indemnización formula.
4. **P3-T4 flag promotion** — if both pass, flip in `scripts/dev-launcher.mjs` + mirror in CLAUDE.md:
   - `LIA_PRACTICA_NOISE_FILTER`: `shadow` → `enforce`
   - `LIA_CONFLICT_RESOLVER_MODE`: `shadow` → `enforce`
   Both have been on shadow since v18 b1/b2 with no regressions observed.
5. **P3-T5 commit** — operator-triggered. Per CLAUDE.md commit discipline: 3-4 logical commits (polish fix / práctica fix / docs).

**Success criteria.**

| # | Criterion | Target |
|---|---|---|
| P3-SC1 | q01 verdict = `pass` per `answer-engine-probe` rubric | rubric pass |
| P3-SC2 | q02 verdict = `pass` per `answer-engine-probe` rubric | rubric pass |
| P3-SC3 | Curated test suite stays green after flag flips | `make test-batched` |
| P3-SC4 | §⏯ + §2 + §6 updated to reflect "v21 closed ✅" before commit | doc edits |

**Rollback (if probe still fails).**

| Situation | Recipe |
|---|---|
| q01 fails because polish still over-rejects | Flip `LIA_POLISH_UVT_VALIDATOR=shadow`; restart server; rerun probe |
| q01 fails because práctica still picks wrong bullets | Flip `LIA_PRACTICA_NOISE_FILTER=legacy`; restart server; rerun probe |
| q02 fails on the day-count formula (CST 64 indemnización calc) | Open `answer_synthesis_practica.py` candidate-line builder + verify the indemnización playbook is in the corpus; if missing, this needs corpus content not code |

---

## §4. Files to touch (consolidated)

### §4.1 Modified files (P2)

- `src/lia_graph/pipeline_d/answer_llm_polish.py` (P2-T1)
- `src/lia_graph/pipeline_d/answer_synthesis_practica.py` (P2-T2)
- `src/lia_graph/pipeline_d/answer_polish_rejected_fallback.py` (P2-T1 indirect — may need a corresponding loosening)
- `src/lia_graph/ingest_reports.py` (P2-T3, optional)
- `scripts/cloud_promotion/replay_local_artifacts_to_cloud.py` (P2-T3, optional — sidecar consumption)
- `scripts/dev-launcher.mjs` (P3-T4 flag flips)
- `CLAUDE.md` (P3-T4 runtime flags table mirror)
- `docs/orchestration/orchestration.md` (P3-T4 env matrix version bump)
- `docs/guide/env_guide.md` (P3-T4 mirror table)

### §4.2 New files

- `tests/test_polish_invented_norm_lineage_labor.py` (P2-T1)
- `tests/test_practica_terminacion_chunk_selection.py` (P2-T2)
- (P2-T3 optional) `scripts/build_subtopic_sidecar.py` + `tests/test_subtopic_sidecar.py`

### §4.3 Touched but no change (verify only)

- `src/lia_graph/pipeline_d/retriever_falkor.py` — confirm v20 P4 dual-mode MATCH unchanged
- `src/lia_graph/pipeline_d/planner.py` — confirm v20 P4 norm_id emission unchanged
- `config/topic_norm_allowlist.json` — confirm laboral allow-list still permits art:64

---

## §5. Risks + mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Polish-validator fix breaks tax UVT validation | Medium | High | Narrow the regex to require an ET/UVT cue context; add a regression test for the tarifa-tarifaria case that fix_v15 §3 was meant to catch |
| Práctica chunk-selector fix breaks other labor cases (liquidación mensual, prestaciones, etc.) | Medium | High | Each `liquidacion_*` case_bullet ships with `keywords` for the off-topic filter; cross-check the new selector against all 13 labor case_bullets before flipping enforce |
| Subtopic sidecar (P2-T3) overcomplicates the replay script | Low | Medium | Keep P2-T3 strictly optional — fallthrough to current empty-bindings behavior if sidecar missing |
| Probe still fails after both fixes | Medium | Medium | Iterate per P1-T3 max 2 cycles; if still failing, surface to operator with full trace for triage |
| v18/v20 baseline tests regress | Medium | High | Run `make test-batched` (full) before P3-T5 commit. If anything fails, isolate via focused subset, fix, repeat |
| Operator forgets to restart server before probe | Low | Critical | The skill enforces this gate — verifies new PID + recent start-time before judging |

---

## §6. Run log (append-only, most recent on top, Bogotá local time)

### 2026-05-16 ~08:50 PM Bogotá — v21 plan drafted

- **What.** Drafted `docs/re-engineer/fix/fix_v21_may.md` v1 — full zero-agent-context plan with §⏯ crash-resume + 3 phases (P1 diagnose, P2 fix, P3 re-probe + promote + commit).
- **Why.** v20 closing probe surfaced two downstream bugs (polish over-rejection + práctica chunk-selection) that v20's scope didn't cover. v21 narrows on those specifically.
- **Next.** P1-T1 — read the failing q01 probe artifact + grep the validator implementation.

---

## §7. Six-gate lifecycle per phase

Each phase must clear all six gates per `CLAUDE.md` Non-Negotiables before being declared ✅.

| Phase | 1. Idea | 2. Plan | 3. Success | 4. Test plan | 5. Greenlight | 6. Refine-or-discard |
|---|---|---|---|---|---|---|
| P1 | diagnose before intervene | §3.1 | 3 SCs measurable | engineer ~1.5 hr | operator after diagnosis written | re-read if scope unclear |
| P2 | narrow code fixes | §3.2 | 4 SCs measurable | engineer ~3-4 hr | operator after each sub-task | revert specific fix if regression |
| P3 | probe + flag flip + commit | §3.3 | 4 SCs measurable | probe + manual flag review | operator triggers commit | flip flag back if probe regresses |

---

## §8. Open questions (genuinely undecided — needs operator before that phase starts)

| # | Question | Blocks | Surfaced |
|---|---|---|---|
| Q1 | Is P2-T3 (subtopic sidecar) in scope for v21 or deferred to v22? | P2-T3 | 2026-05-16 PM (mentioned in v20 known-gap) |
| Q2 | Should P3-T4 flag flips include `LIA_TOPIC_GATE_MODE` change? (currently `enforce`, no v20-era regression observed) | P3-T4 | 2026-05-16 PM |

Update this section as new questions surface during execution.

---

## §9. Decisions locked in (do not re-litigate without operator sign-off)

| # | Decision | Reason | Locked when |
|---|---|---|---|
| D1 | v21 scope = answer-shape fix only (polish + práctica). NOT corpus changes, NOT cloud re-replay, NOT P5 carryover work | v20 closed the data + lookup layers; v21 doesn't need to revisit them. P5 carryovers (A2 validator, shadow harness) deferred to v22 unless explicitly requested | 2026-05-16 PM (this doc) |
| D2 | Fixes ride existing kill-switch env flags where possible | CLAUDE.md non-negotiables: every behavior change ships with rollback flag. `LIA_POLISH_UVT_VALIDATOR` + `LIA_PRACTICA_NOISE_FILTER` already serve this purpose | repo standing rule |
| D3 | SME panel is operator-triggered only — `answer-engine-probe` skill is the v21 self-audit mechanism | `feedback_sme_panel_explicit_request_only` + 2026-05-16 operator directive | repo standing rule |
| D4 | Diagnose-before-intervene applies to every v21 phase | `feedback_diagnose_before_intervene` | repo standing rule |
| D5 | Server restart is mandatory before every post-fix probe | `answer-engine-probe` skill non-negotiable; was burned by this in v20 | repo standing rule |

---

## §10. What v21 does NOT do (honest scope)

- v21 does **not** re-ingest or re-canonicalize the cloud corpus. v20's `gen_v20_20260516_172203` stays active.
- v21 does **not** touch the SUIN catalog, `:Norm` vigencia tables, or any v6-domain data.
- v21 does **not** modify the planner, retriever, or retriever_falkor — v20 P4's changes stand.
- v21 does **not** rewrite the polish prompt or práctica synthesis from scratch — narrow surgical edits only.
- v21 does **not** add new corpus content. The labor playbook + CST consolidated + Ley 50/1990 + Ley 2466/2025 already cover the q01/q02 question shape.
- v21 does **not** auto-run the SME panel. Self-audit only via `answer-engine-probe`.

---

## §11. Resuming work — preconditions + first-action recipe

A fresh agent should be able to start P1 immediately after the preconditions below pass.

### §11.1 Preconditions (run all five, all must pass)

```bash
# 1. v20 P4 has been committed.
git log --oneline -10 | grep -E "v20|P4" && echo "OK v20 commit landed" || echo "MISSING — operator must commit v20 P4 first"

# 2. Local docker stack — Supabase + Falkor must be up.
docker ps --filter "name=supabase_db_lia-graph" --filter "name=lia-graph-falkor-dev" --format "table {{.Names}}\t{{.Status}}"
# Expected: both rows present with "Up ..." status.

# 3. .env.staging exists.
test -f .env.staging && grep -q "^FALKORDB_URL=redis" .env.staging && echo "OK staging env" || echo "MISSING"

# 4. dev:staging server up + answering.
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8787/
# Expected: 200. If not, ask operator to run `npm run dev:staging`.

# 5. v20 closing-probe artifact exists.
ls -la tracers_and_logs/logs/probe_runs/20260517T013419Z_v20_labor_collision/q01.digest.md
# Expected: file present (this is the failing-probe artifact P1 reads)
```

If any precondition fails, STOP and consult the relevant file (`fix_v20_may.md` for v20 commit state, `docs/guide/env_guide.md` for env state). Do not skip preconditions.

### §11.2 Phase 1 first action (after preconditions pass)

Announce in chat: "Reading v20 q01 probe artifact + grepping for the `invented_norm_lineage` validator. Expected ~30 min."

Then run:

```bash
# P1-T1a: read the failing probe digest
cat tracers_and_logs/logs/probe_runs/20260517T013419Z_v20_labor_collision/q01.digest.md | head -80

# P1-T1b: locate the validator
grep -rn "invented_norm_lineage\|_no_invented_norm_lineage" src/lia_graph/pipeline_d/ | head -10

# P1-T1c: locate the rejection-fallback path
grep -rn "polish_skip_reason\|polish_rejected_fallback\|GraphNativeAnswerParts" src/lia_graph/pipeline_d/ | head -10

# P1-T1d: locate the práctica chunk-selector
grep -n "def _candidate_lines_from_chunk\|práctica\|liquidacion_terminacion" src/lia_graph/pipeline_d/answer_synthesis_practica.py | head -15
```

After reading the above output, document findings in §6 run log (append entry under today's date). Then move to P1-T2 (trace the rejection-fallback chunk-selection path).

### §11.3 What to do after P1 closes

- Append a §6 run log entry naming the validator + chunk-selector culprits with `file:line` refs.
- Set §2.1 P1 row to ✅, P2 row to 🔵.
- Announce in chat: "P1 closed — root causes identified. Ready for P2 fix sprint — operator greenlight?"
- DO NOT start P2 without explicit operator greenlight (P2 mutates served behavior).

### §11.4 What to do after P2 closes

- Append run log entry with the unit test names + green status.
- Run §3.3 (P3 re-probe) — restart server first, then probe q01 + q02.

### §11.5 What to do after P3 closes

- §⏯ "Last completed step" → "v21 closed ✅"
- Update CLAUDE.md runtime flags table for any flag flips.
- Propose commit shape to operator: 3 commits (polish fix / práctica fix / docs).

---

*Drafted 2026-05-16 ~08:50 PM Bogotá by claude-opus-4-7 in response to operator directive: "input status and advancement and next steps into new document fix_v21_may.md — use zero context agent protocol, manage state with detail; commit p4". Companion to [fix_v20_may.md](fix_v20_may.md) (predecessor, closed 2026-05-16 ~08:35 PM Bogotá). Update §⏯ + §2 + §6 as work progresses.*
