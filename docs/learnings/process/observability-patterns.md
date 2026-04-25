# Observability patterns for long-running ingest

**Source:** `CLAUDE.md` "Long-running Python processes" section; v6 execution 2026-04-24; `docs/done/next/ingestion_tunningv2.md` §16 Appendix D §§5, 7.

## The problem class

Ingest runs are long (6–25 min locally, more in delta or cloud-sink modes). They survive CLI close, Claude exit, shell disconnect. The operator should never have to ask "is it still alive? what's it doing? did it succeed?" — the process itself should say.

## Launch pattern (required, not optional)

```bash
LOGFILE="logs/phase2_full_rebuild_$(date +%Y%m%dT%H%M%SZ).log"
nohup bash -c "PYTHONPATH=src:. uv run python -m lia_graph.ingest \
  --corpus-dir knowledge_base --artifacts-dir artifacts --json \
  > $LOGFILE 2>&1; echo 'PHASE2_EXIT='\$? >> $LOGFILE" \
  > /dev/null 2>&1 &
disown
```

Three requirements:
1. **`nohup` + `disown`** — process survives SIGHUP on CLI close.
2. **Direct `> log 2>&1`** — NO `| tee`. Tee has broken at least one run on SIGHUP in this repo.
3. **Explicit `PHASE_*_EXIT=$?` marker in the log** — the one signal every heartbeat script can key on for "definitely finished."

## Heartbeat contract

| Rule | Why |
|---|---|
| **3-minute cadence.** | Tight enough to catch a 10-min stall; loose enough not to crowd the chat. |
| **One line per tick, ≤ 120 chars.** | Scan-readable. No multi-line dumps. |
| **Carries `elapsed / progress / pace / failures / ETA`.** | Four of five numbers must make sense at a glance. ETA can be `?` if pace=0. |
| **Delta-based error detection.** | Grep-count tracebacks, alert only when count > last_count. A monitor that re-alerts on the same error every tick trains you to ignore it. |
| **Silent-death stop.** | If the process is gone AND no `PHASE_EXIT=` marker is present, emit `ALERT` and stop. Never silently retry. |
| **Timeout cap at ~1.5× plan estimate.** | Long enough to cover variance, short enough that a runaway surfaces. |
| **Visual separator (`█░` bar) for progress.** | Eye catches the bar; brain parses counts. |
| **Phase-aware silence.** | `sink_writing` and `falkor_writing` legitimately emit zero per-item events. Do not alarm during those phases; alarm only in `classifying` phase. |

## Source-of-truth for progress

**Anchor on `logs/events.jsonl`, not on the `--json` summary log.** The summary only flushes on termination. Events are append-only, line-per-event. A heartbeat tail on events.jsonl survives a kill -9.

Good event markers for phase boundaries:
- `subtopic.ingest.audit_start` / `subtopic.ingest.audit_done` — classifier phase boundaries.
- `subtopic.graph.bindings_summary` — binding pass done.
- `corpus.sink_summary` — Supabase upload done (bulk event, not per-item).
- `graph.load_report` — Falkor load done.

## Trust signals for phases with no events

When classifier is done and sink + Falkor are doing bulk uploads with no per-item events, you still need liveness checks:

```bash
# TCP session health — expected endpoints
lsof -p "$PID" | grep -E "TCP.*(supabase\.co|falkor|cloudflare)"

# Process state — SN/S + growing RSS = healthy I/O-wait
ps -p "$PID" -o pid,etime,stat,%cpu,rss

# Last event-log activity — stale means real stall
stat -f "%Sm" logs/events.jsonl
```

If all three show healthy I/O-wait and the process is within its timeout budget, **silence is not a stall.** Only escalate when: TCP sessions in CLOSE_WAIT/TIME_WAIT with no new ones, OR RSS stopped growing AND %CPU is 0 AND events.jsonl hasn't been appended in > 180 s AND phase is `classifying`.

## Kill-switches (the caller must enforce)

Three conditions that stop the monitor loop:
- **Process gone + no `cli.done` or `PHASE_EXIT=` marker.** Silent death → STOP loop, surface events + log, do NOT retry.
- **`run.failed` event OR `ERRORS > 0` in summary.** STOP loop, surface, do NOT retry.
- **`cli.done` OR `PHASE_EXIT=0` marker.** STOP loop, declare complete.

Never retry on any of these — the whole point is to surface the condition to the operator, not to mask it with a retry loop.

## Counter-examples (things that went wrong in v6)

- **"0% CPU means stuck."** — False positive. At 60 RPM classifier pace, the process is in `recv()` 95 % of the time. TCP session state is the better liveness probe. (Phase 2 pre-2a, 2026-04-24.)
- **Monitor re-fires on same 92 tracebacks every tick.** — My cloud-sink monitor filtered `grep -c Traceback` without tracking a baseline. Fix: snapshot count at monitor start, alert only when current > baseline. (Cloud sink, tick #3, 2026-04-24.)
- **Grep filter matches Spanish legal text.** — My first rebuild monitor filtered on `Error|FAILED` and fired on "ERRORES CONTABLES" in the Colombian tax code. Always use structured-event markers (`"event_type": "..."`), not free-text regex. (Phase 2 rebuild, 2026-04-24.)

## See also

- `CLAUDE.md` — "Long-running Python processes" section (authoritative).
- `scripts/monitoring/ingest_heartbeat.py` — the canonical heartbeat script (has the same delta-error bug as my inline monitor had; follow-up item in `docs/done/next/ingestion_tunningv2.md` §16 Appendix D §9).
- `docs/done/next/ingestion_tunningv2.md` §16 Appendix D §5 for the tabular rules.
