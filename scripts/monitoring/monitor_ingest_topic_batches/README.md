# `scripts/monitoring/monitor_ingest_topic_batches/` — v3 topic-backfill pipeline

Three scripts + one canonical plan that together turn a 40-minute
full-corpus reingest into a safe, resumable, gated chain of ~10-minute
batches. Ships as part of `ingestionfix_v3` (see
`docs/next/ingestionfix_v3.md` for the canonical story).

## The flow in one screen

```
 ┌──────────────────────────────────────────────────────────────────┐
 │  artifacts/fingerprint_bust/plan.json                            │
 │  (8 batches covering all 39 taxonomy topics; batch 1 = gate)     │
 └──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │  fingerprint_bust.py          (1)                                │
 │   UPDATE documents SET doc_fingerprint=NULL WHERE tema IN (…)    │
 │   Guarded by --confirm, --force-multi, 200-row soft threshold.   │
 │   Writes an audit manifest BEFORE the UPDATE runs.               │
 └──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │  scripts/launch_batch.sh       (2)                                │
 │   nohup + disown the additive reingest for the busted slice.     │
 │   No --force-full-classify — the fingerprint bust is the only    │
 │   thing that makes docs look changed.                            │
 │   Produces logs/events.jsonl lines the heartbeat can read.       │
 └──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │  validate_batch.py             (3)                                │
 │   Runs G1-G10 automated checks (fingerprint applied, chunks      │
 │   written, Falkor TopicNode / TEMA edges, sink idempotency,      │
 │   walltime in range, chunk_text clean, …).                       │
 │   Writes artifacts/batch_<N>_quality_gate.json.                  │
 └──────────────────────────────────────────────────────────────────┘
                                │
                   status=passed │ (operator fills M1-M3 + U1-U4)
                                ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │  run_topic_backfill_chain.sh   (4)                                │
 │   Gate-enforced supervisor. Refuses to advance past batch 1      │
 │   until the gate file shows status: passed. Full autonomous      │
 │   loop (STOP_BACKFILL sentinel, 30s yield, atomic state writes)  │
 │   lands in Phase 3 proper — this file currently ships the        │
 │   --gate-only mode + refusal plumbing.                           │
 └──────────────────────────────────────────────────────────────────┘
```

## Files

| File | Role |
|---|---|
| `fingerprint_bust.py` | Null `documents.doc_fingerprint` for a topic / topic-set so the next additive run reclassifies only that slice. |
| `validate_batch.py` | Post-batch Quality Gate validator (G1–G10 automated checks). |
| `run_topic_backfill_chain.sh` | Gate-enforced chain supervisor (Phase-2 skeleton; full loop in Phase 3). |

Adjacent files at the repo level:

| Path | Role |
|---|---|
| `scripts/launch_batch.sh` | Detached per-batch reingest launcher — pairs with `fingerprint_bust.py`. |
| `scripts/launch_phase9a.sh` | Full-corpus detached reingest (use when a whole re-classification is truly needed). |
| `scripts/launch_phase9b.sh` | Detached embedding backfill. |
| `scripts/monitoring/ingest_heartbeat.py` | 3-minute heartbeat renderer (supports `--chain-state-file` for chain-aware output). |
| `artifacts/fingerprint_bust/plan.json` | Canonical 8-batch plan covering all 39 top-level topics. |

## Why this exists

The Phase 9.A reingest crashed three times on 2026-04-23 — each crash cost
~40 minutes because `--force-full-classify` re-runs the classifier on all
1,280 corpus docs. The fix is to move to **controlled** fingerprint
invalidation: bust a small slice, reingest only that slice, gate-check
it, repeat. A batch crash now costs ~10 minutes of rework, not 40, and
prior batches are written in stone.

## Typical session

```bash
set -a; source .env.staging; set +a

# 1. Dry-run batch 1 to see what would mutate.
bash scripts/launch_batch.sh --batch 1 --dry-run

# 2. Real run (fingerprint_bust + detached ingest).
bash scripts/launch_batch.sh --batch 1

# 3. Arm a 3-minute heartbeat cron for progress visibility.
#    See scripts/monitoring/README.md for the canonical cron prompt.

# 4. When ingest.delta.cli.done appears, validate.
PYTHONPATH=src:. uv run python \
  scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py \
    --batch 1 \
    --manifest artifacts/fingerprint_bust/<latest>.json \
    --delta-id delta_<id> \
    --delta-elapsed-ms <ms> \
    --gate

# 5. Fill M1-M3 + U1-U4 manually in the gate file; set status: passed.

# 6. Release the autonomous chain (batches 2-8).
bash scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh
```

## Durability contract (prior batches written in stone)

If a batch crashes mid-run, only that batch has to be repeated. Prior
successful batches are untouched. Three invariants together make this
work:

| Invariant | Mechanism |
|---|---|
| **Topic-level cross-batch isolation** | `fingerprint_bust` filters by `tema IN (this_batch_topics)` — it is structurally incapable of touching another batch's docs. Prior batches' `doc_fingerprint` stays freshly stamped from their successful runs, so the additive planner keeps seeing them as unchanged. |
| **Row-level idempotency** | Every write layer idempotents on its natural key: `documents.doc_id`, `document_chunks.chunk_id`, `normative_edges.(source_key,target_key,relation,generation_id)`, Falkor `MERGE`. A kill -9 mid-UPDATE and an orderly retry converge on the same final state. |
| **State-file checkpoint BEFORE destructive work** | `scripts/launch_batch.sh` writes `artifacts/launch_batch_state_<N>.json` with `status=in_flight` before calling `fingerprint_bust`. Atomic temp+rename so partial writes can't corrupt it. |

Failure / resume matrix:

| Scenario | What happens | On resume |
|---|---|---|
| **Clean success** | state: launched → operator flips to `completed` after validator passes. | No action needed; advance to the next batch. |
| **Mid-batch crash** (reingest dies, OOM, reboot) | state remains `launched` / `in_flight`; sink writes are idempotent upserts; Falkor uses MERGE. | Re-run `scripts/launch_batch.sh --batch <N>`. The retry warning fires; prior batches stay untouched. |
| **Operator nuke** (`pkill -f lia_graph.ingest`) | Same as mid-batch crash. | Same recovery path. |
| **`fingerprint_bust` crashes during UPDATE** | Manifest already written (safety rail: manifest-before-execute). UPDATE is idempotent: re-running on already-NULL rows is a no-op. | Re-run `scripts/launch_batch.sh --batch <N>`. |

This is the single-batch mirror of the autonomous chain's durability
contract documented in `docs/next/ingestionfix_v3.md` §5 Phase 3. Same
invariants; `launch_batch.sh` is what you use for manual per-batch work,
`run_topic_backfill_chain.sh` is what you'll use once the chain loop is
wired (Phase 3 proper).

## Safety rails

- **--dry-run** is the default safe mode for `fingerprint_bust`. Every run
  writes a manifest BEFORE any UPDATE issues, so a crash leaves an audit
  trail.
- **--confirm** is required for any real write. No exceptions.
- **--force-multi** is required when `--topics` holds more than one key.
- **200-row soft threshold** refuses huge mutations without `--confirm`
  regardless of intent.
- **Gate enforcement** in `run_topic_backfill_chain.sh` physically blocks
  the autonomous chain from advancing past batch 1 without operator sign-off.
