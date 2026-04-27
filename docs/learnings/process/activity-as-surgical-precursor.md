# Activities as surgical precursors to Fixes

**Source:** Activity 1 (`docs/learnings/retrieval/vigencia-binary-flag-too-coarse.md`), Activity 1.5 (`docs/re-engineer/activity_1_5_outcome.md`), Activity 1.6 (3 veredicto fixtures in `evals/activity_1_5/`). Workstream pattern in `fixplan_v2.md §8`.

## What an Activity is

In the re-engineering plan, an **Activity** is a small, isolated, measurable ship that proves a structural Fix's hypothesis BEFORE the full Fix lands. Activities are not throwaway — they integrate cleanly into the corresponding Fix. They earn their place by:

1. Costing < 1 engineer-day to ship.
2. Producing a numeric measurement that updates our prior on whether the structural Fix will work.
3. Touching the same surface the Fix will eventually rewrite (no parallel codepaths, no wasted work).

## Three Activities in this round

| Activity | Hypothesis tested | Cost | Measurement | Lesson |
|---|---|---|---|---|
| **Activity 1** (2026-04-29) | The vigencia bypass is a real bug; turning on the existing filter improves things | 3 hrs (1 SQL migration + measurement script) | `art. 689-1` citations −85% in targeted answers; auto-rubric flat; `6 años firmeza` regressed +46% | Binary flag is too coarse to bite at scale; proves Fix 1B-β necessity |
| **Activity 1.5** (2026-04-26 ev) | Wholesale-flagging Decreto 1474/2025 as suspendida is safe + impactful | 2 hrs (manual skill protocol + WebSearch verification) | Found corpus has hallucinated content (`EME-A01` cites a non-existent sentencia); skill correctly refused the wholesale flag | Skill's burden-of-proof discipline catches what flag-only approaches hide; proves Fix 1B-β + Fix 6 priority |
| **Activity 1.6** (2026-04-26 ev) | Skill protocol works on canonical V/VM/DE cases | 30 min (3 norms × WebSearch) | 3 clean veredictos: VM (Art. 689-3 ET), DE (Art. 158-1 ET), V-with-transition (Art. 290 #5 ET). Each pre-validated as a Fix 5 skill-eval-set seed | Skill produces correct outputs on the canonical state distribution; seeds 3 of the 30-case skill eval set without waiting for Fix 1B-α |

**Total Activity cost this round: ~6 hrs of engineering + WebSearch.** Total information value: validated the structural hypothesis behind Fix 1B-α + Fix 1B-β + Fix 6 + Fix 5; produced 4 reusable veredicto fixtures; found a critical corpus hallucination. **Without Activities, we would have spent ~$80K building Fix 1B-α + Fix 1B-β before knowing whether the approach worked.**

## The Activity → Fix mapping (binding)

Each Activity must point at a specific Fix sub-component it pre-validates:

| Activity | Pre-validates |
|---|---|
| Activity 1 (SQL bypass fix) | Fix 1C (2D vigencia retrieval) — the migration shape, the env matrix bump, the deploy flow |
| Activity 1.5 (skill on Decreto 1474) | Fix 1B-β (skill-guided extractor) — the skill invocation pattern, the veredicto JSON shape, the dual-source-verification refusal path |
| Activity 1.6 (skill on 3 canonical norms) | Fix 5 (golden judge) — the expected-state-per-norm test cases; Fix 1B-β extractor's cost/throughput per norm |

If a proposed Activity doesn't map to a specific downstream Fix, it's not an Activity — it's a side quest. Reject it.

## The "Activity reveals a bigger problem" pattern

Activity 1.5 was scoped as "wholesale flag the document, re-run §1.G, measure citation drop." It produced a different and more valuable outcome: **discovered that the corpus contains fabricated content with a verification stamp.** This is the upgrade case — an Activity that finds a structural issue larger than the one it set out to test.

When this happens:
1. Document the upgraded finding in the Activity's outcome report.
2. Update the downstream Fix's scope to address it (Activity 1.5 → Fix 6 gains a corpus-wide hallucination audit subscope).
3. Adjust the budget if needed (Activity 1.5 → Re-Verify Cron moves from week 13 to week 4 priority).
4. Do NOT pretend the original Activity goal succeeded if it didn't. Activity 1.5 did not produce the §1.G citation drop it was scoped for; the right call was to NOT apply the UPDATE because the skill couldn't safely produce a wholesale veredicto. That's a successful Activity outcome.

## The "Activity confirms the boring case" pattern

Activity 1.6 was scoped to verify the skill works on canonical V/VM/DE cases. It did, exactly. No surprises. **This is also a successful Activity outcome** — the skill works as designed; we have evidence to commit to Fix 1B-α scrapers + Fix 1B-β extractor at scale.

Boring outcomes are fine. The Activity earned its 30 minutes by giving us 3 reusable veredicto fixtures + 3 pre-validated Fix 5 test cases + confidence to greenlight the next $60K of work.

## The rule that survives

**Before committing to a multi-week structural Fix, ship a < 1-day Activity that measures the structural hypothesis on real data.** The Activity's measurement is the gate-3 evidence that authorizes the Fix's scope. If the Activity shows the hypothesis is wrong, the Fix doesn't ship — saving weeks of wrong work. If the Activity confirms the hypothesis, the Fix ships with a documented baseline + clear before/after measurement frame.

Two anti-patterns to avoid:

1. **Skipping Activities because "we know the answer."** If we knew the answer, we wouldn't need a $500K rebuild. Every structural Fix has at least one assumption that should be tested cheaply first.
2. **Activities that don't produce measurements.** "Run the skill manually" is not an Activity unless the manual run produces a JSON fixture, a citation count, or a refusal-rate datum that updates priors. If the output is just "felt right" — it's not an Activity.

## What this motivates downstream

- The Activity → Fix mapping table above becomes part of the weekly checkpoint review. Each Activity's measurement is recorded; the corresponding Fix's scope is updated based on what the Activity revealed.
- Future activities (1.7, 1.8, etc.) follow the same shape: < 1 day, measurable, points at a specific Fix sub-component, can find a bigger problem and update scope.
- The exec_summary's `⚡ Latest update` block surfaces Activity outcomes prominently — they're the strongest evidence of execution rigor we have for the founder.
