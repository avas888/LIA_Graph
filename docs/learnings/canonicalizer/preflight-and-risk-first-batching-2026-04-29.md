# Preflight + risk-first batching — engineering learning (next_v7 P1, 2026-04-29 Bogotá)

**Context.** next_v7 §3.1 P1 cloud promotion against `production`
Supabase. Running 39 batches × ~107 norms each in alphabetical order
(B → C → D → E → F → G → J → K). Each of the first three attempts
ran for **~25-30 minutes** through the low-risk early batches before
fail-fast tripped on a NEW root cause that surfaced only when the
cascade hit a high-risk family at batch 31 (J1 CST).

By the time the third attempt hit J1+J2 at the same elapsed point
each time, the operator pointed out the obvious problem:

> "did you test why they died and instead of waiting fix? why do
> we have to wait for run to get there so that run might be killed
> and a LONG run have to be re-run? why not batch and have the
> critical runs run separately so the fail fast fix fast?"

The fail-fast doctrine was working — but it was tail-blind. We were
waiting for risk to surface itself instead of putting risk first.
Three concrete improvements followed.

---

## Lesson 1 — Order batches by RISK, not alphabet

**Problem.** Alphabetical order put the volume batches (E*: 16 dirs,
~1,800 norms) BEFORE the novelty batches (J*: CST, K*: CCo, F*: DIAN
res, G*: DIAN conceptos). Every fail-fast trip burned ~25 min of
already-validated E* batches before reaching the new shape.

**Why this happens.** Default file ordering is lexical. It correlates
with neither risk nor novelty. In our corpus:

* **Low risk** = batches with norm_types we've ingested before, no
  new prefixes, no new constraint shapes (B10 sentencias, C/D leyes
  / decretos, E DURs).
* **High risk** = batches that introduce shapes the writer / canon /
  DB has never seen (J* CST → first time `cst_articulo` hits cloud
  CHECK; K* CCo → similar; F*/G* → DIAN-specific).

**Fix (`scripts/cloud_promotion/run.sh::RISK_FIRST=1`).**
When `RISK_FIRST=1`, the orchestrator partitions BATCHES into a
high-risk prefix list (`B10 J K F G`) + a low-risk remainder, then
concatenates them before the main loop. A failure trips fail-fast
in the first 5 minutes, not the 25th.

---

## Lesson 2 — Preflight one row per batch BEFORE the volume run

**Problem.** Even with risk-first ordering, the first error in a new
shape requires re-running every batch already processed. UPSERT-on-
norm_id is idempotent, but the cycle still takes minutes per batch
to confirm "already there, skipped". Worse, the fail-fast threshold
catches failures at the AUDIT log level — a single row error on the
first new shape doesn't trip immediately because the threshold
requires `>50 errors OR >10% rate after 100 rows`.

**Fix (`scripts/cloud_promotion/run.sh::PREFLIGHT=1`).**
Before the main loop, the orchestrator iterates batches and ingests
exactly ONE veredicto-bearing JSON per batch. Same `--run-id` as the
main loop will use, so the writer's `_idempotency_key` matches and
the main loop skips the already-ingested probe row.

If ANY preflight ingest produces a row error, the orchestrator aborts
BEFORE the volume batches start. Total preflight cost: ~1 minute for
40 batches at ~1.5 sec/probe.

**The probe ingest must use the real writer + DB path** — not a
dry-run client. The DB CHECK constraints are what catch the bugs we
can't catch in Python (e.g. `norms_norm_type_valid` rejecting
`cst_articulo` because the migration baseline never enumerated it).

---

## Lesson 3 — Preflight the SCHEMA constraints with a one-row probe

**Problem.** The fail-fast trip in attempt 3 was a CHECK constraint
mismatch. The writer was happy. The local Postgres was happy
(constraint identical, but the row never reached cloud). The cloud
Postgres rejected. We didn't notice until 25 minutes of cascade had
run.

**Fix (independent of the orchestrator).** Before any cloud-write
cascade, run a one-shot direct UPSERT probe against the cloud DB
exercising every novel norm_type / state / change_source.type the
new code is expected to emit. Six rows; takes 3 seconds:

```python
from lia_graph.supabase_client import create_supabase_client_for_target
c = create_supabase_client_for_target('production')
probes = [
    ('preflight.test.cst', 'cst', 'Probe — bare cst whole-code'),
    ('preflight.test.cst.art.99999', 'cst_articulo', 'Probe — cst_articulo'),
    ('preflight.test.cco', 'cco', 'Probe — bare cco whole-code'),
    # ... one per new norm_type the code can emit
]
for norm_id, norm_type, label in probes:
    c.table('norms').upsert({...}).execute()  # raises if CHECK rejects
# Cleanup
for norm_id, _, _ in probes:
    c.table('norms').delete().eq('norm_id', norm_id).execute()
```

If the probe fails, the migration is missing. Apply it BEFORE
launching anything else.

---

## Why this matters beyond P1

These three patterns generalize to **every long-running cloud-write
cascade**: ingests, embedding backfills, scraper re-runs, evals.
The cost of not pre-flighting is N-shaped: linear in batches × time
per batch × number of attempts. The cost of pre-flighting is fixed
(~1 minute) regardless of corpus size.

The fail-fast doctrine in `CLAUDE.md` already required instrumenting
abs+rate thresholds. This learning extends it with two new rules:

7. **Preflight before volume.** Ingest 1 record per batch (or 1 row
   per novel schema-touching shape) before the main loop; abort on
   any preflight error.
8. **Risk-first ordering.** When the cascade has heterogeneous batches,
   process novelty / historical-failure-prone batches first.

Both shipped in `scripts/cloud_promotion/run.sh` as `RISK_FIRST=1` /
`PREFLIGHT=1` env-var flags (default off for backward compat).

---

## Three-attempt chronology that produced this learning

| Attempt | Elapsed before fail-fast | Root cause | Fix |
|---|---|---|---|
| 1st | 0:03 / 350 rows | Writer mutated frozen `ChangeSource` | Restructure normalize→thread-into-dict path |
| 2nd | 0:27 / 2,670 rows | Canon grammar required `cst.art.<N>`, LLM emitted bare `cst` | Make `.art.<N>` optional for cst/cco (mirror ET) |
| 3rd | 0:27 / 2,670 rows | Cloud `norms_norm_type_valid` CHECK didn't include `cst_articulo` etc. | Migration `20260501000006_norms_norm_type_extend.sql` |
| 4th | clean | — | preflight + risk-first added retroactively |

Attempt 2 and 3 wasted 25 minutes each by sitting through the same
22 low-risk batches before reaching J1+J2. Both root causes were
single-row-detectable. With `PREFLIGHT=1`, both would have surfaced
in <1 minute total.

---

## Reference

* `scripts/cloud_promotion/run.sh` — implementation
* `CLAUDE.md` "Fail Fast, Fix Fast — operations canon" — the broader
  doctrine these two rules extend
* `docs/learnings/process/risk-first-cascade-design.md` — the
  process-level companion to this technical learning
