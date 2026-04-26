# aa_next — the ongoing "what we do next" surface

> **This folder is permanent and persists across releases.** It's not a one-shot plan that gets archived after execution. Every time a major ship lands, the current `next_vN.md` here is either updated in-place or superseded by `next_vN+1.md`, with the previous version preserved for historical context.
>
> **Why the `aa_` prefix.** Sorts to the top of `docs/` alphabetically so `ls docs/` shows this first. New engineers and returning agents always find the current forward plan without having to know folder names.

## ⚠ Policy — idea vs. verified improvement (mandatory across this folder)

**RAG is complex science. "Improvements" misbehave and regress all the time.** Every proposed change in any `aa_next/**` document is treated as an **idea of improvement**, never a confirmed improvement, until its stated success criterion has actually been measured against real data AND validated from the end-user's perspective, with the result recorded in-file.

**Mandatory six-gate lifecycle** for every pipeline change (step / item / proposed fix) in any `aa_next/**` document. **Every gate must be written explicitly in the plan doc before any code is written.** A plan missing any gate is not a plan.

1. **Describe the "good idea."** One sentence: what the change is + what behavior it's supposed to alter. No jargon. If the idea can't survive the sentence, it's not ready.
2. **Plan how to implement.** Name the narrowest module(s) that own the behavior + the specific edits or new primitives. Reference the existing architecture (`docs/guide/orchestration.md`, related learnings).
3. **Define a minimum success criterion.** Measurable, with numbers, at a specific layer. No vibes ("better answers"), no proxies-only ("tests pass"). If the criterion is "mean primary_article_count ≥ 3.0 on the 30-gold A/B", that's the gate.
4. **Define HOW to test the criterion — the test plan is part of the plan, not an afterthought.** This gate is about the *test* itself. For each of the two required signals (technical + end-user, see gate 5), spell out:
   - **Development needed.** What code has to be written for the test to even exist? New harness? Extended fixture? New diagnostic field? (E.g., "the A/B harness must capture `coherence_misaligned` before step 04 is testable.")
   - **Conceptualization.** What is the test actually measuring, and why does that number mean the criterion was met? If the mapping from "number X" to "users are better served" isn't obvious, write it down.
   - **Running environment.** Where does the test execute? Unit harness (pytest)? Local artifact-mode mini-A/B? Full cloud A/B against staging Supabase+Falkor? Full-corpus classifier sweep against paid-tier Gemini? Each has different cost / latency / access requirements — name them.
   - **Actors + interventions required.** Who has to push the button? The engineer (trivial)? A platform operator with prod credentials (medium)? A subject-matter expert (SME accountant / lawyer for content review)? An end-user accountant actually answering questions with the system? If a test requires a human actor besides the engineer, it must be named + the hand-off mechanism specified.
   - **Decision rule.** What numeric band / signal makes the test pass vs. fail? The step-04 example: `would-refuse ∈ [4, 12] → flip · <4 → defer · >12 → tune threshold first` — that's a test plan, not a wish.
5. **Greenlight requires TWO independent signals, both passing:**
   - **Technical tests** — unit + integration tests pin the code contract. Gate 4 names them.
   - **End-user validation** — the criterion measured against real data at the layer an accountant would experience (retrieval output / answer shape / latency / whatever the criterion names). Gate 4 names *how to run this*, including actor hand-offs. A green unit test without end-user validation is **never** sufficient to greenlight.
6. **Refine-or-discard.** If end-user validation fails the criterion, either iterate until it passes OR **explicitly discard the change** (with the regression record kept in-file). No "it's mostly working" middle state. No silent rollback without documentation. Gate-6 discard is a legitimate, encouraged outcome — the learning is the artifact.

**Status lifecycle** tracked inline on every step:

| Status | Meaning |
|---|---|
| 💡 **idea** | Described (gate 1) + planned (gate 2) + criterion set (gate 3). No code. |
| 🛠 **code landed** | Implementation shipped + unit tests green (gate 4a passed). **Not** an improvement yet — gate 4b still open. |
| 🧪 **verified locally** | End-user criterion measured against real data with a local proxy (artifact-mode / mini-harness). Results recorded inline. |
| ✅ **verified in target environment** | End-user criterion measured in the environment the criterion names (staging / production / full-corpus / cloud A/B). Results recorded. |
| ↩ **regressed — discarded** | Verification showed the change made things worse or flat. Kept in the doc as a learning; code reverted per gate 5. |

**Rules:**

1. Never mark a step "done" / "shipped" / "fixed" based on test-green alone. Unit tests are gate 4a; gate 4b (end-user) is mandatory.
2. Every step's *Outcome* block must cite the success criterion verbatim AND the measured number. If no measurement was taken, the step is at best 🛠 code landed.
3. When cloud/target-env verification is infeasible locally, mark 🧪 explicitly with the scope of the local proxy, and record the *specific run still needed* to reach ✅.
4. A step verification shows as ↩ regressed stays in the doc. The record of what was tried and what failed is this folder's highest-value artifact — it's what prevents the next engineer from re-proposing the same idea.
5. Gate-5 discard is a legitimate, encouraged outcome. "We tried it, it didn't work, here's the data, we're removing the code" is strictly better than "we kept it in because it was almost working."

## Current version

**[`next_v5.md`](./next_v5.md)** — forward plan opened 2026-04-26. Carries the still-pending verifications from v4 (conversational-memory L2 staging harness, comparative-regime SME validation, 100-Q first baseline + judge spot-check) plus the deferred-but-still-relevant items (Falkor parity follow-ups in correct diagnose-before-intervene order, v3 §10 carries) and §7: retrieval-depth envelope calibration through the 100-Q gauge — a new operator-surfaced design question.

**Archives (read-only records):**
- [`next_v4.md`](./next_v4.md) — record of the 2026-04-25/26 ship cycle (conversational-memory L1+L2 shipped, comparative-regime mode shipped, 100-Q gauge code landed, parity-probe diagnostic + 10k cap audit closed).
- [`next_v1/README.md`](./next_v1/README.md) — historical + outcome record of the 2026-04-24 work.

Don't update v4 / v1 for new work; update v5 (or open v6 if it supersedes).

## The pattern

1. **After any major ship** (a v-numbered execution plan completes, like `ingestion_tunningv2.md` did), open or update the current `next_vN.md` here.
2. **Each `next_vN.md` is a single self-contained document.** It holds the full what / why / success-criterion for every step. No sub-folders, no per-step files — one file so a reader can see the whole plan in one scroll.
3. **Each step inside `next_vN.md`** follows the same template: *what* (one-line scope), *why* (motivation + cited evidence), *success criterion* (measurable, not vibes), *deep-dive section* if the step warrants one.
4. **When a new version opens**, rename the old to `next_v{N-1}_archive.md` (keep it in this folder) and open a fresh `next_vN.md`. The archive is read-only; the current file is the live plan.
5. **Deep-dive content** stays inline in `next_vN.md` as sub-sections — NOT split across separate files.

## What belongs here vs. elsewhere

| Artifact | Where it lives |
|---|---|
| **The current forward plan** (top-10 steps with why + success) | `docs/aa_next/next_vN.md` (this folder) |
| **The full idea backlog** (30+ items, ranked) | `docs/done/next/ingestionfix_vN.md` (last live: `ingestionfix_v6.md`, archived 2026-04-25 after the next_v1+v2+v3 cycles absorbed it) |
| **Execution plans** (when a step-group becomes a 6-phase execution cycle) | `docs/done/next/ingestion_tunningvN.md` (last live: `ingestion_tunningv2.md`, the v6 phases 0-6 plan that closed 2026-04-24) |
| **Learnings** (non-obvious invariants earned through incidents) | `docs/learnings/` |
| **Historical executed plans** | `docs/done/` |

The layering is intentional:

- `aa_next/next_vN.md` answers "what am I working on next week?" (current + prioritized + actionable).
- `next/ingestionfix_vN.md` answers "what's the full idea pool?" (inventory).
- `next/ingestion_tunningvN.md` answers "here's the 6-phase plan I'm executing right now" (when work moves from idea → commitment).

## When this folder is empty

If `aa_next/` has no current `next_vN.md`, it means no major ship has happened recently OR the previous version has been executed and archived but no new plan has been written yet. That's a signal: **someone should open `next_vN+1.md`** summarizing the top-10 items from the latest `ingestionfix_vN.md` backlog.
