# `scripts/monitoring` — long-running ingest babysitter

Durability pattern + live heartbeat for any Lia_Graph background process that
takes more than a couple of minutes. Built for the Phase 9.A reingest and
generalized so future runs (9.B embedding backfill, Phase 8 overnight
subtopic-miner batches, full corpus rebuilds) can reuse it.

**All user-facing times render as Bogotá AM/PM** (`America/Bogota`, UTC-5,
no DST). Machine comparisons stay UTC.

## Why this exists

A prior 9.A run wedged silently: the bash pipeline was a child of the Claude
Code CLI, so closing the terminal triggered SIGHUP → tee exited → python got
SIGPIPE mid-classification → no final JSON summary, no error event, just
silence. The next run then crashed invisibly in a sink URL-length bug that
only surfaced in the traceback at the very end.

This directory standardizes three things so neither failure mode repeats:

1. **Detached launch** — the process survives CLI close, Claude exit, and
   shell disconnect.
2. **Event-stream anchored progress** — we read `logs/events.jsonl`, not
   stdout, because `--json` buffers the summary until the very end.
3. **Phase-aware monitoring** — silence during the sink or Falkor phase is
   expected (those emit a single start/done pair); silence during the
   classifier phase is a stall signal.

## Files

- `ingest_heartbeat.py` — one-shot heartbeat renderer. Computes progress /
  rate / ETA from events.jsonl, polls Supabase + Falkor for row counts,
  prints one markdown block to stdout. First output line is a
  machine-parseable `STATE=...|PHASE=...|RUN_DONE=...` status so a cron can
  grep it for loop-stop decisions.
- `../launch_phase9a.sh` / `../launch_phase9a_force.sh` — detached launchers
  (`nohup` + `disown`, redirects instead of a tee pipe, inherits `.env.staging`).
  Keep the same shape when adding new long-running launchers.

## One-time per-run steps after launching

1. **Launch detached**:
   ```bash
   bash scripts/launch_phase9a.sh          # normal additive run
   bash scripts/launch_phase9a_force.sh    # bypass the fingerprint shortcut
   ```

2. **Capture the delta_id + start timestamp** once the run emits its first
   event:
   ```bash
   grep 'ingest.delta.run.start' logs/events.jsonl | tail -1
   ```
   Copy the `delta_id` and `ts_utc` fields.

3. **Capture pre-run baselines** so delta counters are meaningful:
   ```bash
   set -a; source .env.staging; set +a
   PYTHONPATH=src:. uv run --group dev python -c "
   from lia_graph.supabase_client import create_supabase_client_for_target
   c = create_supabase_client_for_target('production')
   print('docs=', c.table('documents').select('doc_id', count='exact').execute().count)
   print('chunks=', c.table('document_chunks').select('chunk_id', count='exact').execute().count)
   "
   PYTHONPATH=src:. uv run --group dev python -c "
   from lia_graph.graph.client import GraphClient, GraphWriteStatement
   c = GraphClient.from_env()
   def q(cy):
       s = GraphWriteStatement(description=cy, query=cy, parameters={})
       return list(c.execute(s, strict=True).rows)[0]['n']
   print('Article=', q('MATCH (a:ArticleNode) RETURN count(a) AS n'))
   "
   ```

4. **Smoke the script once**:
   ```bash
   set -a; source .env.staging; set +a
   PYTHONPATH=src:. uv run --group dev python scripts/monitoring/ingest_heartbeat.py \
       --delta-id delta_YYYYMMDD_HHMMSS_xxxxxx \
       --start-utc 2026-04-23T17:02:09 \
       --total 1280 \
       --title "Phase 9.A Reingest (force-full)" \
       --supa-base-docs 6730 \
       --supa-base-chunks 19507 \
       --falk-base-article 8106
   ```

## Cron prompt template

Feed this to `CronCreate` with `cron: "*/3 * * * *"` and `recurring: true`.
Swap the four `--delta-id`, `--start-utc`, `--total`, `--title` values and
the six baseline flags for the current run.

````
Ingest heartbeat. Run the heartbeat script, then apply the transition logic
and render its markdown.

=== BASH 1: Heartbeat script ===
```
set -a; source .env.staging; set +a
PYTHONPATH=src:. uv run --group dev python scripts/monitoring/ingest_heartbeat.py \
    --delta-id delta_20260423_170209_322c84 \
    --start-utc 2026-04-23T17:02:09 \
    --total 1280 \
    --title "Phase 9.A Reingest (force-full)" \
    --supa-base-docs 6730 \
    --supa-base-chunks 19507 \
    --falk-base-article 8106
```

=== TRANSITION LOGIC (apply in order) ===

Parse the FIRST line of output: `STATE=<...>|PHASE=<...>|RUN_DONE=<...>|RUN_FAILED=<...>|ERRORS=<...>|DELTA_ID=<...>`

- PHASE=complete → STATE_FINAL=complete. CronDelete this job. Alert user:
  "9.A done. 9.B (embedding backfill) is the next decision. 9.C is a no-op
  for additive." Surface the final JSON from the reingest log.
- PHASE=failed OR RUN_FAILED=True OR ERRORS>0 → STATE_FINAL=failed.
  CronDelete this job. Surface `tail -40 logs/reingest-<ts>.log` and the
  error events.
- STATE=STOPPED AND PHASE not in {complete,failed} → STATE_FINAL=crashed
  (silent death). CronDelete this job. Surface the last 5 events.jsonl
  entries + log tail. DO NOT retry.
- Otherwise → echo the heartbeat markdown (everything after the first line)
  verbatim to the user. The script already encodes phase-aware verdicts
  (sink_writing and falkor_writing silence is expected, not a stall).

HARD RULES: never run embedding_ops, never run promote-snapshot, never
touch §7 ledger without asking, never retry on crash/failure.
````

## Design notes

### Phase inference

The heartbeat derives `PHASE` from event-stream watermarks:

| Phase | Trigger | Caller's take |
|---|---|---|
| `startup` | process alive, 0 classifier events | new run, pre-first-tick |
| `classifying` | 1 ≤ done < total | report progress; stall if FRESH > 180s |
| `classifier_done_waiting_sink` | done == total, no sink.start | brief transition; stall if FRESH > 300s |
| `sink_writing` | sink.start seen, sink.done not yet | silence normal; Supabase delta = progress signal |
| `post_sink` | sink.done seen, falkor.start not yet | transition to Falkor phase |
| `falkor_writing` | falkor.start seen, falkor.done not yet | silence normal |
| `finalizing` | falkor.done seen, run.done not yet | brief close-out |
| `complete` | cli.done emitted | caller stops the loop |
| `failed` | run.failed emitted or errors > 0 | caller stops the loop, surfaces log |

### Kill-switches

Only the CALLER (the Claude session running the cron) decides to stop. The
script itself never blocks and never exits non-zero on in-progress states.
That keeps the cron idempotent: a missed tick is a no-op.

Stop conditions the caller should enforce:

1. `PHASE=complete` → normal finish.
2. `PHASE=failed` → unhandled exception / explicit failed event.
3. `STATE=STOPPED` with no terminal event → silent death (the failure mode
   that cost us hours on 2026-04-23). Surface events + log and stop.
4. `PHASE=classifying` with `FRESH > 180s` for 2 consecutive ticks → stall.
   Surface and let the operator decide.

### Time policy

Script converts every user-facing timestamp to Bogotá (UTC-5) and renders
12-hour with AM/PM (e.g. `12:37 PM` not `17:37 UTC`). Machine-readable
log entries and comparison timestamps stay UTC ISO, since that's what's in
`events.jsonl` and DB columns.

### When to use force-full

The `--force-full-classify` flag on `lia_graph.ingest` bypasses the
fingerprint-based prematch shortcut. Use it when:

- A prior crashed run already wrote fingerprints but left the Falkor or
  edge-writing phase incomplete (the "partial completion" hazard).
- You need to re-materialize thematic edges (TEMA / SUBTEMA_DE /
  PRACTICA_DE) that the delta planner would otherwise skip as "unchanged".

Without it, the delta planner correctly treats previously-fingerprinted
docs as unchanged, which is what you want on normal incremental runs but
NOT what you want after a partial-failure cleanup.
