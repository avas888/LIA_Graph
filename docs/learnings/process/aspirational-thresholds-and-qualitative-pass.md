# Aspirational thresholds + qualitative-pass policy

> **Captured 2026-04-25** from the operator's binding decision in `docs/aa_next/gate_9_threshold_decision.md §7`. This is process knowledge: how to handle a measurement that misses an absolute threshold without normalizing the miss into a new (lower) threshold.

## The setup

A multi-gate change (e.g. a re-flip, a promotion, a flag enforcement) often has gates with **absolute numeric thresholds** — "≥ 27/30 SME validation", "seeds non-empty ≥ 20/30", "mean primary ≥ 2.5", etc. These thresholds get written when the work is opened. They're **forward-looking aspirational** — what we'd like the system to be at, not what it is today.

When a measurement comes back **just below threshold** (18 vs 20, 1.93 vs 2.5), the natural temptation is two-fold:

1. Block the change indefinitely (strict reading).
2. Lower the threshold to match what we got (qualitative reading, but the wrong way).

Both are wrong. The right pattern is the third option below.

## The right pattern — qualitative-pass + per-exception memo + threshold preserved

Three rules, all binding:

### Rule 1 — Keep the threshold

Do **not** change the original numeric threshold in the policy doc. The threshold is what we're aiming for; missing it once doesn't redefine the goal. Lowering it normalizes the exception and erodes the next iteration ("well, last time we accepted 18, so 17 should be fine too").

### Rule 2 — Document each exception individually

Write a per-exception memo (e.g. `docs/aa_next/gate_9_threshold_decision.md`) with:

- The actual measurement (what we got vs the threshold)
- Strict-vs-qualitative reading laid out side by side
- The qualitative case — what evidence supports passing despite the miss
- The recommendation + the operator's binding decision
- **What gets deferred and to where** — name a follow-up item in a future cycle that should close the threshold gap

The memo is the precedent. Future operators look at memos, not at lowered thresholds.

### Rule 3 — Each gate evaluates against its own criteria

When multiple gates exist (gate 8, gate 9, etc.) and one is granted qualitative-pass, **do not** import that interpretive flexibility into the other gates. Each gate is scored cleanly against its own published threshold.

> *"Cuando llegue la respuesta SME, evalúala contra sus propios criterios, no contra 'ya pasamos qualitative en gate 9 entonces seamos consistentes'. Cada gate vive aparte."* — operator, 2026-04-25

## Why this works

The strict reading punishes good-faith work that strictly improved the system but missed an aspirational target. The naive qualitative reading erodes the bar. The right pattern preserves both:

- **Future operators inherit the original target** — the threshold doc is unchanged. The aspiration stays.
- **Past exceptions are auditable** — every memo is named, dated, and linked from the policy doc as a precedent record (NOT as a new bar).
- **The deferred debt is named and tracked** — the memo says exactly what work would close the threshold gap and where it lives. Future cycles can pick it up or revisit the call.

## Required pieces in every per-exception memo

Adapted from `gate_9_threshold_decision.md` §7 conditions:

1. **Numeric measurement** — what we got, what the threshold was, by how much we missed.
2. **The strict vs qualitative reading** — both presented, no rhetorical thumb on the scale.
3. **The diagnostic that makes qualitative defensible** — *why* the miss is acceptable. In our case: 11 of 12 still-zero questions were correctly routed but rejected by the v6 coherence gate (the same mechanism that keeps contamination clean — you can't ratchet one without trading the other).
4. **The verbatim language to ship in the change-log** — exact wording, including the enumerated deferred-debt items (e.g. specific question IDs, specific topics).
5. **The follow-up commitment** — name the future cycle item that closes the gap (e.g. `next_v4 §1 — coherence-gate calibration diagnostic`).
6. **Operator's signature decision** — one word ("qualitative" / "strict") + binding conditions.

## What this is NOT

- **Not** a license to skip threshold measurement. You still measure; you still publish the number; the threshold gate still exists.
- **Not** a way to ship known-broken behavior. Qualitative-pass requires evidence the change is a strict improvement (no regressions, contamination clean, etc.). Misses with regressions get blocked.
- **Not** something to do casually. If this pattern is invoked more than 1-2 times per cycle, the thresholds are mis-calibrated for the actual system maturity — bigger conversation needed.

## Cross-references

- `docs/aa_next/gate_9_threshold_decision.md` — the canonical example: 4-criteria §8.4 A/B scorecard, 2/4 missed, qualitative-pass granted with 3 binding conditions
- `docs/aa_next/done/next_v3.md §13.10 / §13.11` — the cycle where the policy was first applied
- `~/.claude/projects/.../memory/feedback_thresholds_no_lower.md` — same pattern, encoded as user-feedback memory for future Claude sessions in this repo
- `~/.claude/projects/.../memory/feedback_gates_evaluate_independently.md` — Rule 3 specifically
