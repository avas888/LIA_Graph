# Heartbeat monitoring — a tactical field manual

**Source:** `CLAUDE.md` "Long-running Python processes" section; `scripts/monitoring/ingest_heartbeat.py`; live experience 2026-04-24 (Phase 2 rebuild + cloud sink, tick #1 through #8+).

> Companion to [`observability-patterns.md`](observability-patterns.md). That doc gives the principles; this one gives the **script shape, the metric formulas, and the five failure modes** I actually encountered building heartbeats for v6.

## What a heartbeat is (and isn't)

**A heartbeat is one line per tick, scan-readable, that makes the operator's next decision obvious: wait, intervene, or declare done.**

It is not a progress log — don't stream every classifier event. It is not a dashboard — don't render multi-line tables. It is not a retry loop — on stop-condition it exits, leaving the operator to act.

## The anatomy of a good heartbeat line

```
💓 #5 | t=13m1s | phase=sink/falkor | [█████░░░░░░░░░░░░░░░] 28% | docs=1275/4500 | pace=309RPM | failed=0 | ETA~9m
```

| Field | Purpose | Why this form |
|---|---|---|
| `💓 #5` | Tick counter | Spot gaps (tick #5 → tick #8 without #6/#7 = something dropped ticks) |
| `t=13m1s` | Elapsed wall time | Compare against plan estimate for stall sniffing |
| `phase=...` | Current phase label | Different phases have different silence budgets |
| `[█████░░░]` | 20-char visual bar | Eye catches progress at glance |
| `docs=X/Y` | Numeric progress | Bar is imprecise, numbers are authoritative |
| `pace=N RPM` | Throughput | Drift from expected pace = rate-limit / latency / stall signal |
| `failed=N` | Per-item failure count | Non-zero = investigate; zero can still mean silent degradation (see caveats) |
| `ETA~Nm` | Projected completion | Set expectations; `?` if pace can't be computed yet |

Under ~120 chars. Emoji is not decoration; it's a **visual anchor** so the operator's eye locates the line in a crowded chat.

## The canonical script shape (copy-paste starter)

```bash
#!/usr/bin/env bash
set -euo pipefail

LOGFILE="logs/phase2_full_rebuild_20260424T110038Z.log"  # captured at launch
START_EPOCH="$(date +%s)"                                 # captured at launch
START_LINE="$(wc -l logs/events.jsonl | awk '{print $1}')"  # captured at launch
TB_BASELINE="$(grep -c 'Traceback' "$LOGFILE" 2>/dev/null || echo 0)"
TOTAL_DOCS=3900   # known-good denominator for %
TICK=0

while true; do
  # 1. TERMINAL EXIT — highest priority
  if grep -q "PHASE2_FULL_EXIT=" "$LOGFILE"; then
    EXIT_LINE="$(grep 'PHASE2_FULL_EXIT=' "$LOGFILE" | tail -1)"
    ELAPSED=$(($(date +%s) - START_EPOCH))
    CLASS="$(tail -n +$((START_LINE+1)) logs/events.jsonl | grep -c '"subtopic.ingest.classified"')"
    FAIL="$(tail -n +$((START_LINE+1)) logs/events.jsonl | grep -c '"status": "failed"')"
    echo "🏁 FINISHED | $EXIT_LINE | elapsed=$((ELAPSED/60))m$((ELAPSED%60))s | classified=${CLASS} | failed=${FAIL}"
    exit 0
  fi

  # 2. SILENT-DEATH STOP — second priority
  if ! ps -ef | grep -v grep | grep -q "lia_graph.ingest"; then
    echo "🚨 ALERT | process died without exit marker at $(($(date +%s) - START_EPOCH))s"
    exit 1
  fi

  # 3. DELTA ERROR DETECTION — only fire on NEW tracebacks
  TB_NOW="$(grep -c 'Traceback' "$LOGFILE" 2>/dev/null || echo 0)"
  TB_DELTA=$((TB_NOW - TB_BASELINE))
  if [ "$TB_DELTA" -gt 0 ]; then
    LAST_TB="$(grep -n 'Traceback' "$LOGFILE" | tail -1)"
    echo "🚨 NEW_ERRORS +${TB_DELTA} since last tick (total ${TB_NOW}) | latest: ${LAST_TB}"
    TB_BASELINE="$TB_NOW"
  fi

  # 4. NORMAL HEARTBEAT
  ELAPSED=$(($(date +%s) - START_EPOCH))
  MIN=$((ELAPSED / 60)); SEC=$((ELAPSED % 60))
  CLASS="$(tail -n +$((START_LINE+1)) logs/events.jsonl | grep -c '"subtopic.ingest.classified"')"
  FAIL="$(tail -n +$((START_LINE+1)) logs/events.jsonl | grep -c '"status": "failed"')"
  TICK=$((TICK+1))
  if [ "$CLASS" -gt 0 ] && [ "$ELAPSED" -gt 0 ]; then
    PCT=$(awk -v c="$CLASS" -v t="$TOTAL_DOCS" 'BEGIN{p=c*100/t;if(p>100)p=100;printf "%.0f",p}')
    RPM=$(awk -v c="$CLASS" -v e="$ELAPSED" 'BEGIN{printf "%.0f", c*60/e}')
    REM=$((TOTAL_DOCS - CLASS))
    ETA=$(awk -v r="$REM" -v rpm="$RPM" 'BEGIN{if(rpm>0) printf "%d", r*60/rpm/60; else print "?"}')
    # 20-char bar
    BAR_N=$((PCT/5)); BAR=""; i=0
    while [ $i -lt $BAR_N ] && [ $i -lt 20 ]; do BAR="${BAR}█"; i=$((i+1)); done
    while [ $i -lt 20 ]; do BAR="${BAR}░"; i=$((i+1)); done
    echo "💓 #${TICK} | t=${MIN}m${SEC}s | [${BAR}] ${PCT}% | docs=${CLASS}/${TOTAL_DOCS} | pace=${RPM}RPM | failed=${FAIL} | ETA~${ETA}m"
  else
    echo "💓 #${TICK} | t=${MIN}m${SEC}s | warming up"
  fi

  sleep 180
done
```

Adapt the `TOTAL_DOCS`, `classified` event-type name, and phase label per use case. Keep the structure.

## The five failure modes I actually hit

### 1. Spanish legal text matching your error filter

**Symptom:** monitor fires on Spanish text inside ingested legal-code articles containing strings like "ERRORES CONTABLES", "art. 651 sanción por no enviar información o enviarla con errores", "correción".

**Fix:** never match free text. Grep only on structured markers like `"event_type": "..."` or `PHASE_EXIT=`. If your log carries ingested content, consider logging to a dedicated file and keeping stdout structured-only.

**Incident:** 2026-04-24 Phase 2 rebuild, first Monitor arm. Filter was `"PHASE2_LOCAL_EXIT=|graph_target_document_count|articles_written|Traceback|Error:|FAILED|ERROR|Killed|OOM"`. The `Error|ERROR` part matched legal-text noise for ~50 events in 60 s.

### 2. Re-firing on the same errors every tick

**Symptom:** tick #3, #4, #5 all fire `🚨 ERROR_SIGNATURE detected — 3158:Traceback | 3206:Traceback | 3229:Traceback`. Same three line numbers.

**Fix:** snapshot `grep -c Traceback "$LOG"` at monitor start; alert only when current > baseline. Update the baseline after each alert so only NEW errors trigger.

**Incident:** 2026-04-24 cloud sink, ticks #3 and #4 fired identical tracebacks. Operator loses trust in alerts. (Appendix D §5 in `ingestion_tunningv2.md`.)

### 3. "0% CPU" false-positive stall

**Symptom:** `ps -o %cpu` shows 0.0, operator reports "it's hung."

**Fix:** at 1 req/1.5 s LLM pace, a sequential worker is in `recv()` 95% of the time — 0% CPU is normal. Check instead:

- `lsof -p $PID | grep TCP` — ESTABLISHED sessions to the expected host
- `events.jsonl` line-count delta since last tick — growing = alive
- `ps -o etime,rss` — growing RSS = alive

**Incident:** 2026-04-24 Phase 2 first rebuild, operator diagnosed "stuck" at t=14m with 0% CPU. Actually classifier was pacing through Gemini at 40 RPM, correct throttle behavior. Killed unnecessarily. See `ingestion/parallelism-and-rate-limits.md`.

### 4. `failed=0` while real degradation is happening

**Symptom:** pool reports `failed=0`, but post-run audit shows 7% of docs with `requires_subtopic_review=True`.

**Fix:** the pool's failure count is a **lower bound**. Inner try/except blocks in classifiers can catch and degrade without raising. Cross-check with:

- `grep -c '"status": "failed"'` in events.jsonl (catches structured failures)
- `grep -c '"requires_subtopic_review": true'` in events.jsonl (catches quiet degradation)
- `grep -c 'Traceback'` in stdout log (catches raised-but-swallowed exceptions)

**Incident:** 2026-04-24 cloud sink produced 92 tracebacks in the log but `failed=0` in pool boundary. Root cause: classifier's `_run_n2_cascade` catches Gemini 429s and returns N1-only verdicts. (`retrieval/diagnostic-surface.md` and `ingestion/parallelism-and-rate-limits.md` cover the root cause.)

### 5. Phase-aware silence misread as stall

**Symptom:** classifier phase done at t=6m; sink phase shows zero per-item events for the next 10 min; monitor would naively alert.

**Fix:** **phase-aware silence**. The `sink_writing` and `falkor_writing` phases legitimately emit batch-summary events, not per-item events. Don't alarm. Verify liveness via the trust triad:

```
ps -p $PID -o pid,etime,stat,%cpu,rss
lsof -p $PID | grep TCP
stat -f "%Sm" logs/events.jsonl
```

Alarm only when **all three** show unhealthy signals (CLOSE_WAIT sockets, RSS stopped growing, events.jsonl stale > 5 min).

### 6. Zsh arithmetic + `grep -c || echo 0` = double-zero

**Symptom:** monitor script exits immediately with `bad math expression: operator expected at '0'`. Stuck sink keeps running while the monitor is dead.

**Fix.** `grep -c X f` prints `0` on stdout **and** returns exit 1 when no matches. A `|| echo 0` composition then prints another `0` — the captured value is `"0\n0"`, and `$((A - B))` fails to parse it as an integer.

Defensive pattern — strip everything non-digit and fall back:

```bash
_safe_int() { local v="$1"; v="${v//[^0-9]/}"; echo "${v:-0}"; }
TB_NOW=$(_safe_int "$(grep -c 'Traceback' "$LOGFILE" 2>/dev/null)")
```

**Incident:** 2026-04-24 cloud-sink heartbeat v1 died at t=~30s. Sink process continued running fine. Fixed by rearming with the `_safe_int` helper (inline monitor v2).

### 7. Fragile dep-health probes you never validated

**Symptom:** monitor calls `scripts/monitoring/dep_health.py` periodically. The Falkor probe was silently returning `ok=False` because of a `ModuleNotFoundError` — wrong module path (`lia_graph.graph_client` instead of `lia_graph.graph.client`) and wrong API (`run_query(str)` doesn't exist; real shape is `execute(GraphWriteStatement)`). The probe reported Falkor red even while Falkor was at 779 ms latency.

**Fix.** Every monitoring probe needs its own regression test. Even a 3-line smoke (`assert dep_health.probe_falkor()["ok"] is True` when env is set) would have caught this.

**Incident:** 2026-04-24 — probe was broken from day one. Monitor never surfaced Falkor health because the probe never returned `ok=True`. Fixed post-stall.

### 8. Per-phase stall thresholds, post-phase-2c

Falkor bulk load (phase 2c, not yet landed as of 2026-04-24) will emit `graph.batch_written` events every 3–10 s. Update stall thresholds when phase 2c lands:

| Phase | Expected event cadence | Stall threshold |
|---|---|---|
| `classifier` | per-doc (`subtopic.ingest.classified`) | 180 s |
| `bindings` | per-binding (`subtopic.graph.binding_built`) | 120 s |
| `load_existing_tema` (phase 2b) | per batch (50 batches) | 60 s |
| `sink_writing` (phase 2b) | per batch upsert | 60 s |
| `falkor_writing` (phase 2c) | per `graph.batch_written` event | 120 s |

If no `graph.batch_written` event fires in 120 s during the Falkor phase **post-phase-2c**, escalate — the write is stuck server-side (`CLIENT LIST` probe on a sibling Redis connection confirms whether `cmd=graph.query` is still running).

Pre-phase-2c (today): Falkor phase is silent, can legitimately be 10–15 min long, monitor cannot distinguish slow-but-progressing from stuck. Don't wire a stall alert here until phase 2c instruments the batches.

## Timeout budgets

Cap every monitor at **1.5× the plan estimate**:

| Operation | Plan estimate | Monitor timeout |
|---|---|---|
| Classifier (parallel 8-worker) | 13 min | 20 min |
| Cloud sink | 25 min | 35–40 min |
| Delta reingest | 5 min | 10 min |

If the monitor times out, **do not re-arm silently**. Surface to operator with elapsed time, last heartbeat snapshot, and current trust-triad state.

## Heartbeat anti-patterns

- **Tail the log file and grep continuously.** You get an event stream, not heartbeats. Chat floods.
- **No `PHASE_EXIT=` marker.** Monitor has no terminal state to key on; guesses with timeouts and races the operator.
- **Progress bar without numeric counts.** Bar is imprecise. Numbers are authoritative. Always both.
- **One heartbeat per loop iteration without a `sleep`.** Eats CPU; floods chat.
- **Retry inside the monitor on stop-conditions.** The monitor exists to surface, not to recover. Retries belong to the operator's decision, not the monitor's logic.

## See also

- [`observability-patterns.md`](observability-patterns.md) — the principles behind these tactics.
- `CLAUDE.md` "Long-running Python processes" — authoritative.
- `scripts/monitoring/ingest_heartbeat.py` — existing shared script (has delta-error bug as of 2026-04-24; follow-up item in `ingestion_tunningv2.md` §16 Appendix D §9).
