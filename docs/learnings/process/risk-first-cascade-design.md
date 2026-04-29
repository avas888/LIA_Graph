# Risk-first cascade design — process learning (next_v7 P1, 2026-04-29 Bogotá)

**The pattern.** When a multi-batch cascade has heterogeneous risk
profiles, the default alphabetical / chronological / size-ordered
sweep is almost always WRONG. Process risk first, volume last.

> Companion to [`heartbeat-monitoring.md`](heartbeat-monitoring.md)
> and the canonicalizer-specific
> [`preflight-and-risk-first-batching-2026-04-29.md`](../canonicalizer/preflight-and-risk-first-batching-2026-04-29.md).
> Heartbeat tells you WHAT happened during the run; this doc tells you
> WHEN within the run different things should happen.

---

## The mistake we kept making

A cascade has 39 batches. They processed in the order they appeared
on disk (alphabetical). The first 30 batches are "things we've seen
before, low risk." The last 9 are "things with new shapes — new
data types, new constraint surfaces, new sources." A bug in the new
shape doesn't surface until ~25 minutes into the run. Fail-fast
trips, all 30 minutes of upstream work was wasted on validating
already-validated batches.

We did this **three times in a row** on the same P1 run before the
operator pointed out the pattern. The fail-fast doctrine was working
mechanically (it caught each bug). But our SEQUENCING was tail-blind.

The third attempt is the cleanest tell: the operator literally asked

> "did you test why they died and instead of waiting fix? why do
> we have to wait for run to get there so that run might be killed
> and a LONG run have to be re-run? why not batch and have the
> critical runs run separately so the fail fast fix fast?"

— and the answer was that we were treating the cascade as a single
sequential pipeline when it was actually a sequence of independent
sub-runs with very different risk profiles.

---

## The principle

**Order independent units of work by RISK, not the dimension that
happens to make them easy to enumerate.**

Two practical implementations:

### 1. Risk-first ordering of the main loop

For a cascade where you can identify batches that introduce novelty
(new types, new sources, historical failures), process them FIRST.
A failure in the first 5 minutes is recoverable. A failure in
minute 25 of a 30-minute run is not.

How to tag risk:

* **High-risk** = touches a code path / data shape / DB constraint
  that hasn't been exercised in this environment before. Examples:
  new norm_type prefixes, new resolución sources, new sentencia
  shapes, batches the previous attempt got stuck on.
* **Low-risk** = same shape as already-validated batches. Volume
  matters, but volume is what runs *after* the shapes are confirmed.

### 2. Preflight phase before the main loop

Run **one record per independent unit** through the full path
(writer + DB constraints + downstream sinks) BEFORE the main loop.
The preflight is bounded (N batches × 1 record each = ~1 minute);
the main loop is unbounded. If preflight discovers a problem, the
fix lands before any volume batch ran.

Preflight design rules:

* **Use the real writer + real DB** — not a dry-run client. The bugs
  that survive Python validation are DB-side (CHECK constraints,
  RLS, FK violations).
* **Same idempotency key as the main loop** — so the main loop
  skips already-ingested preflight rows. Don't use a separate
  `--preflight-run-id`; that creates duplicate audit trails.
* **Abort on any preflight error** — even one row error is enough.
  The fail-fast threshold (50 abs / 10% rate) is for the volume
  loop; preflight is binary pass/fail.

---

## What this displaced

Before this learning, the implicit assumption was: the fail-fast
threshold is the safety net. If the threshold is calibrated right,
"the cascade will trip safely when something goes wrong."

The threshold IS the safety net — but it's the **last** layer of
defense, not the only one. Letting it be the only layer means
paying a 25-minute tax every time something goes wrong, on top of
the 5 minutes it takes to actually fix the bug.

Risk-first + preflight push the safety net forward to where the
defects can be caught CHEAPLY.

---

## Anti-patterns

### "Just raise the fail-fast threshold so the run completes"

No. The threshold tripped because something is structurally broken.
Raising the threshold means the cascade churns through thousands
of bad rows before halting — by which point the audit log is full
of noise and the diagnosis is harder, not easier.

### "Run with --continue-on-error"

Same problem, with an extra layer of "now the bad rows are also
in the destination DB." UPSERT idempotency saves you on the rows
that succeed; nothing saves you on the rows that fail and never
get a retry.

### "Pre-validate everything in Python before the cascade"

Necessary but insufficient. Python validation catches code-level
bugs. DB-level bugs (CHECK, FK, RLS) only surface when the row
actually hits the DB. A 3-second probe (5-row UPSERT + cleanup)
covers what Python can't.

### "Just run the high-risk batches manually first, then kick off the cascade"

Works once. Doesn't scale, doesn't survive operator turnover,
doesn't get repeated when memory of the lesson fades. The
orchestrator should encode the discipline; the operator shouldn't
have to remember.

---

## Where to apply this

Any cascade with all three of these properties:

1. Multiple independent sub-runs (batches, files, generations).
2. Heterogeneous risk across sub-runs.
3. Total runtime longer than ~5 minutes.

Concretely, in this repo:

* Cloud promotion (`scripts/cloud_promotion/run.sh`) — already shipped.
* Canonicalizer cascade (`scripts/canonicalizer/run_cascade_v5.sh`) —
  candidate. Currently runs batches in declared order. Risk-first
  would put refusal-rerun batches (where new code paths fire) ahead
  of stable batches.
* Embedding backfill — single-pass, low novelty per batch — preflight
  not needed.
* Phase 2 graph-build (`make phase2-graph-artifacts`) — has phases,
  not batches; phase ordering already encodes risk (validate before
  build).

---

## Reference

* `scripts/cloud_promotion/run.sh` — `RISK_FIRST=1` / `PREFLIGHT=1`
  env-flag implementation.
* `docs/learnings/canonicalizer/preflight-and-risk-first-batching-2026-04-29.md` —
  the canonicalizer-specific technical companion.
* `CLAUDE.md` "Fail Fast, Fix Fast — operations canon" — rules 7+8
  (preflight + risk-first) added in this cycle.
