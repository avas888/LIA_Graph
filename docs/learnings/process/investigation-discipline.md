# Investigate before you execute

**Source:** `docs/done/next/ingestion_tunningv1.md` (the entire doc); v6 cycle 2026-04-24.

## The moment

After the v5 30Q A/B expert panel returned a devastating verdict ("the experiment was invalid because of a configuration mistake, and worse, it surfaced contamination — labor answers citing biofuels"), two forces pushed toward immediate code changes:

1. **The boss's concern** — "will a strict topic gate starve our Práctica/Expertos content?" demanded a quick yes/no.
2. **The natural engineer instinct** — obvious next-step is "add a topic filter" or "fix the classifier."

Instead we spent a week on a **read-only investigation document** (`ingestion_tunningv1.md`) that opened seven investigations (I1–I7) and shipped zero code. Every investigation was designed to answer a specific question with evidence, and the document's only output was a sharper diagnosis.

## What the investigation produced

Every investigation reshaped the v2 plan:

| Investigation | Headline result | Reshape |
|---|---|---|
| I1 — Tagging audit of Práctica/Expertos | Moot. Those docs aren't in the corpus at all. | Boss's concern answered; reframed as an ingestion gap. |
| I1b — Pipeline skip audit | Not a bug — stale artifact. Rebuild adds ~3,609 articles. | **Rebuild became the P0 fix.** |
| I2 — Classifier keyword coverage | Better than the panel suggested; 16/30 routed correctly on direct test. | Classifier redesign demoted from blocker to nice-to-have. |
| I3 — Fixed 30Q re-run | **Rescoped by I5.** Env was correct all along. | Phase 3 became "harness fix," not "env fix." |
| I4 — Corpus completeness | 87.7% of expected article refs present. | Minor gap, not architectural. |
| I5 — Contamination trace | Harness reads diagnostics from wrong nesting. "0 everywhere" was measurement error. | Phase 1 became the "diagnostic lift." |
| I6 — Refusal-rate simulation | Classifier-confidence gate catches 2/5 contamination cases. | Evidence-coherence gate became phase 3, not classifier-confidence. |
| I7 — Contadores principle audit | 3/5 mechanisms port cleanly. | Citation allow-list (phase 4), topic guardrails. |

Without this week, the v2 plan would have been "tighten classifier + add confidence gate" — a plausible-sounding approach that addresses **none** of the actual failures:

- Ingestion gap → plan would not touch this → corpus stays 2.7× undersized
- Measurement error → plan would keep trusting the wrong metric → re-run would look equally bad
- Evidence-unaware fallback → confidence gate fires on 20% of cases → 80% of contamination still ships

## The rule

**When an eval is catastrophic, the first week after is read-only.** No code. Write one investigation-per-open-question document. Each investigation has:

1. **The question it answers** — one sentence, specific.
2. **Why it matters** — what decision changes based on its result.
3. **Method** — read-only; no new tests, no new features.
4. **Deliverable** — a short report, not a PR.
5. **Decision impact** — how the outcome routes into the downstream plan.

The investigation document's **only output is another document**: the execution plan. The execution plan, in turn, is the first PR.

## Anti-patterns

- **"We have to ship something this week."** — then ship the investigation doc. It's the highest-leverage thing you can produce when you don't yet know what's wrong.
- **Diagnosing from the panel's narrative alone.** — the panel graded answer quality; it does not owe you root cause. The v5 panel said "retrieval broken." Real cause was 50% measurement error + 50% ingestion gap.
- **"This is fast, let's just try it."** — seven weeks of wrong execution cost more than one week of right investigation. Always.

## Template

See `docs/done/next/ingestion_tunningv1.md` for the shape. Each investigation fits on one page. Findings log (§0) updates as investigations close. Status table with one-line results is the first thing a reader sees.

## When to skip investigation

Never on a failed eval. But OK:

- Pure bugfix with a reproducing test case
- Single-file refactor under a green test suite
- Adding a new knob behind an off-by-default flag, with no eval change

## See also

- `docs/done/next/ingestion_tunningv1.md` §0 and §6 (investigations I1–I7).
- `docs/done/next/ingestion_tunningv2.md` §16 Appendix D §9 (follow-up items that came out of the v6 execution and will seed v7's investigations).
