#!/usr/bin/env bash
# launch_batch.sh — drive ONE canonicalizer batch end-to-end.
#
# Per `docs/re-engineer/canonicalizer_runv1.md` §0, every batch follows the
# same protocol: pre-tests → detached extract → ingest → falkor sync →
# post-tests → score. This launcher composes those steps.
#
# Detachment shape (per CLAUDE.md long-running-job convention):
#   * extract launches via `nohup ... > LOG 2>&1 &` then `disown`
#   * NO tee pipes (tee dies on SIGHUP — has crashed prior runs)
#   * the process must reparent to init (PPID=1) — printed at exit
#   * heartbeat is launched separately by the operator via cron, pointed at
#     `scripts/canonicalizer/heartbeat.py --batch-id <X> --run-id <RID>`
#     every 3 minutes; we print the exact cron prompt for them.
#
# Stage targets:
#   * `wip` (default) — local docker Supabase + Falkor (canonicalizer_runv1
#     §9.2 — the work surface). Veredictos land in `evals/vigencia_extraction_v1/<batch_id>/`.
#   * `production` (= cloud staging per supabase_client config) — only after
#     the local docker exit gate passes (§9.3).
#
# Idempotency: each invocation gets a NEW run_id derived from --batch-id +
# UTC ts. Re-running the same run_id is a no-op at the writer.
#
# Run-once guard: `extract_vigencia.py --guard-against-rerun` (default ON)
# refuses to launch when `evals/vigencia_extraction_v1/<batch_id>/` already
# has JSONs. To replay-only, pass `--skip-extract`. To force a re-extraction
# (operator-explicit only), pass `--allow-rerun`.
#
# Usage:
#   scripts/canonicalizer/launch_batch.sh --batch A1
#   scripts/canonicalizer/launch_batch.sh --batch A2 --skip-pre        # skip baseline
#   scripts/canonicalizer/launch_batch.sh --batch A1 --skip-extract    # replay-only
#   scripts/canonicalizer/launch_batch.sh --batch A1 --target wip      # explicit target
#   scripts/canonicalizer/launch_batch.sh --batch A1 --dry-run         # plan only
#
# Required env: GEMINI_API_KEY (or legacy alias LIA_GEMINI_API_KEY),
# SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (sourced from .env.local for target=wip).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

# ── Defaults ──────────────────────────────────────────────────────────
BATCH=""
TARGET="wip"
ENV_FILE=".env.local"
SKIP_PRE=""
SKIP_EXTRACT=""
SKIP_INGEST=""
SKIP_SYNC=""
SKIP_POST=""
SKIP_SCORE=""
ALLOW_RERUN=""
DRY_RUN=""
BASE_URL="http://127.0.0.1:8787"
BATCHES_CONFIG="config/canonicalizer_run_v1/batches.yaml"

# ── Args ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --batch)            BATCH="$2"; shift 2 ;;
    --target)           TARGET="$2"; shift 2 ;;
    --env-file)         ENV_FILE="$2"; shift 2 ;;
    --base-url)         BASE_URL="$2"; shift 2 ;;
    --batches-config)   BATCHES_CONFIG="$2"; shift 2 ;;
    --skip-pre)         SKIP_PRE=1; shift ;;
    --skip-extract)     SKIP_EXTRACT=1; shift ;;
    --skip-ingest)      SKIP_INGEST=1; shift ;;
    --skip-sync)        SKIP_SYNC=1; shift ;;
    --skip-post)        SKIP_POST=1; shift ;;
    --skip-score)       SKIP_SCORE=1; shift ;;
    --allow-rerun)      ALLOW_RERUN=1; shift ;;
    --dry-run)          DRY_RUN=1; shift ;;
    -h|--help)          sed -n '1,40p' "$0"; exit 0 ;;
    *) echo "[launch_batch] unknown flag: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$BATCH" ]]; then
  echo "[launch_batch] ERROR: pass --batch <id>  (e.g. A1, B7, D5)" >&2
  exit 2
fi

if [[ ! -f "$BATCHES_CONFIG" ]]; then
  echo "[launch_batch] ERROR: batches config not found: $BATCHES_CONFIG" >&2
  exit 2
fi

# ── Run identity ──────────────────────────────────────────────────────
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
START_UTC="$(date -u +%Y-%m-%dT%H:%M:%S)"
RUN_ID="canonicalizer-${BATCH}-${TS_UTC}"
OUTPUT_DIR="evals/vigencia_extraction_v1/${BATCH}"
LEDGER="evals/canonicalizer_run_v1/ledger.jsonl"
RUN_DIR="evals/canonicalizer_run_v1/${BATCH}"
EXTRACT_LOG="logs/canonicalizer_${BATCH}_${TS_UTC}.log"
PID_FILE="${RUN_DIR}/run.pid"
STATE_FILE="${RUN_DIR}/run_state.json"

mkdir -p "$RUN_DIR" "$OUTPUT_DIR" "logs"

bog() { TZ='America/Bogota' date '+%Y-%m-%d %I:%M:%S %p Bogotá'; }

echo "════════════════════════════════════════════════════════════════════"
echo "  Canonicalizer batch launcher"
echo "════════════════════════════════════════════════════════════════════"
echo "  batch_id      : $BATCH"
echo "  run_id        : $RUN_ID"
echo "  start (Bogotá): $(bog)"
echo "  target        : $TARGET"
echo "  env file      : $ENV_FILE"
echo "  base url      : $BASE_URL"
echo "  output dir    : $OUTPUT_DIR"
echo "  extract log   : $EXTRACT_LOG"
echo "  ledger        : $LEDGER"
echo "  run state     : $STATE_FILE"
echo "════════════════════════════════════════════════════════════════════"
echo ""

if [[ -n "$DRY_RUN" ]]; then
  echo "[launch_batch] --dry-run: printed plan only; no commands executed."
  exit 0
fi

# ── Load env ──────────────────────────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
  set -a; . "$ENV_FILE"; set +a
fi

# ── Preflight: Gemini key (skipped when --skip-extract is set) ────────
if [[ -z "$SKIP_EXTRACT" ]]; then
  GEMINI_KEY_HIT=""
  if [[ -n "${GEMINI_API_KEY:-}" ]]; then
    GEMINI_KEY_HIT="GEMINI_API_KEY"
  elif [[ -n "${LIA_GEMINI_API_KEY:-}" ]]; then
    GEMINI_KEY_HIT="LIA_GEMINI_API_KEY (legacy alias)"
  fi
  if [[ -z "$GEMINI_KEY_HIT" ]]; then
    cat >&2 <<EOF
[launch_batch] ❌ no Gemini key in env after sourcing $ENV_FILE.
  Set GEMINI_API_KEY in $ENV_FILE (or export it in your shell). The
  legacy alias LIA_GEMINI_API_KEY is also accepted.
  To run replay-only against pre-extracted JSONs, pass --skip-extract.
EOF
    exit 3
  fi
  echo "[launch_batch] ✓ Gemini key bound from \$$GEMINI_KEY_HIT"
fi

# ── Resolve batch's expected total norms (for the heartbeat) ──────────
TOTAL="$(PYTHONPATH=src:. uv run python -c "
import sys, json
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path
ids = _resolve_batch_input_set(
    batches_config=Path('${BATCHES_CONFIG}'),
    batch_id='${BATCH}',
    corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
    limit=None,
)
print(len(ids))
" 2>/dev/null || echo 0)"
echo "[launch_batch] resolved total norms in slice: $TOTAL"

write_state() {
  local phase="$1"
  python3 -c "
import json, datetime as _dt
from pathlib import Path
p = Path('${STATE_FILE}')
existing = {}
if p.exists():
    try:
        existing = json.loads(p.read_text())
    except Exception:
        existing = {}
existing.update({
    'batch_id': '${BATCH}',
    'run_id': '${RUN_ID}',
    'phase': '${phase}',
    'target': '${TARGET}',
    'total': ${TOTAL:-0},
    'output_dir': '${OUTPUT_DIR}',
    'extract_log': '${EXTRACT_LOG}',
    'pid_file': '${PID_FILE}',
    'updated_utc': _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'updated_bogota': _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=-5))).strftime('%Y-%m-%d %I:%M:%S %p Bogotá'),
})
tmp = p.with_suffix('.json.tmp')
tmp.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
tmp.replace(p)
"
}

write_state "starting"

# ── 1. Pre-baseline ───────────────────────────────────────────────────
if [[ -z "$SKIP_PRE" ]]; then
  echo ""
  echo "── [1/6] Pre-baseline · running batch's test_questions BEFORE extraction ──"
  echo ""
  write_state "pre_running"
  if ! PYTHONPATH=src:. uv run python scripts/canonicalizer/run_batch_tests.py \
        --batch-id "$BATCH" \
        --mode pre \
        --base-url "$BASE_URL" \
        --run-id "baseline-${BATCH}-${TS_UTC}" \
        --batches-config "$BATCHES_CONFIG"; then
    echo "[launch_batch] ⚠ pre-baseline failed; continuing anyway (batch can still extract)."
  fi
  write_state "pre_done"
else
  echo "[launch_batch] [1/6] pre-baseline SKIPPED (--skip-pre)"
fi

# ── 2. Extract (detached) ─────────────────────────────────────────────
EXTRACT_PID=""
if [[ -z "$SKIP_EXTRACT" ]]; then
  echo ""
  echo "── [2/6] Extract · launching detached Gemini extraction ──"
  echo ""
  write_state "extracting"

  GUARD_FLAG="--guard-against-rerun"
  if [[ -n "$ALLOW_RERUN" ]]; then
    GUARD_FLAG="--allow-rerun"
    echo "[launch_batch] ⚠ --allow-rerun set; bypassing run-once guard."
  fi

  # Detached launch — nohup + direct redirect, NO tee pipe.
  # The subshell re-sources env so the detached process is independent of
  # the parent's environment after disown.
  # LIA_LIVE_SCRAPER_TESTS=1 unlocks live HTTP fetching from the foundational
  # gov.co primary-source sites (Senado, DIAN normograma, SUIN-Juriscol, CC,
  # CE). Without it, the scrapers only return cache hits — which is empty
  # before the first run. See docs/learnings/sites/README.md.
  nohup bash -c "
    set -a
    [[ -f '${ENV_FILE}' ]] && . '${ENV_FILE}'
    export LIA_LIVE_SCRAPER_TESTS=1
    set +a
    exec env PYTHONPATH=src:. uv run python scripts/canonicalizer/extract_vigencia.py \\
        --batch-id '${BATCH}' \\
        --run-id '${RUN_ID}' \\
        --output-dir 'evals/vigencia_extraction_v1' \\
        --batches-config '${BATCHES_CONFIG}' \\
        ${GUARD_FLAG}
  " > "$EXTRACT_LOG" 2>&1 < /dev/null &

  EXTRACT_PID=$!
  disown "$EXTRACT_PID" 2>/dev/null || true
  echo "$EXTRACT_PID" > "$PID_FILE"

  echo "  pid           : $EXTRACT_PID"
  echo "  log           : $EXTRACT_LOG"
  echo "  events feed   : logs/events.jsonl  (filter run_id=$RUN_ID)"
  echo ""
  sleep 3
  if ps -p "$EXTRACT_PID" > /dev/null 2>&1; then
    echo "  ✅ process alive (reparented to init):"
    ps -p "$EXTRACT_PID" -o pid,ppid,etime,stat,command | sed 's/^/    /' | head -3
  else
    # Process exited within 3s. Distinguish two cases via events.jsonl:
    #   (a) cli.done event for our run_id  → the run was just very fast (small batch
    #                                        / all refusals). NOT a crash.
    #   (b) no cli.done and no run.failed → silent death. Bail.
    if grep -qE "\"kind\": ?\"cli.done\"" \
         <(grep "\"run_id\": ?\"${RUN_ID}\"" logs/events.jsonl 2>/dev/null) 2>/dev/null; then
      echo "  ✅ process exited within 3s with cli.done (fast-finish — likely small slice or all-refusals)."
      echo "    Inspect $EXTRACT_LOG and the audit log to confirm legitimacy."
    else
      echo "  ❌ process died within 3s without cli.done — inspect $EXTRACT_LOG"
      exit 4
    fi
  fi

  # ── Auto-arm the verbose 3-min heartbeat as a sidecar ────────────────
  # Per CLAUDE.md long-running-job protocol, the 3-min heartbeat is
  # MANDATORY for any process expected to take >2 min. Earlier we
  # printed the cron prompt for the operator to arm by hand; the
  # autonomous campaign needs it fired automatically. The sidecar:
  #   * Runs `heartbeat.py` every 180s while the extract pid is alive.
  #   * Each tick rewrites `evals/canonicalizer_run_v1/<batch>/heartbeat_stats.json`
  #     atomically (handled by heartbeat.py).
  #   * Appends a verbose markdown block to a per-batch heartbeat log so
  #     the operator can `tail -f` and see live state.
  #   * Exits when the extract pid is gone (no cron polling forever).
  HEARTBEAT_LOG="logs/heartbeat_${BATCH}_${TS_UTC}.md"
  echo ""
  echo "── auto-arming 3-min heartbeat sidecar ──"
  echo "  log: $HEARTBEAT_LOG"
  echo "  snapshot: ${RUN_DIR}/heartbeat_stats.json (rewritten each tick)"
  nohup bash -c "
    while kill -0 ${EXTRACT_PID} 2>/dev/null; do
      {
        echo
        echo '────── tick at '\$(TZ=America/Bogota date '+%Y-%m-%d %I:%M:%S %p Bogota')' ──────'
        PYTHONPATH=src:. uv run python scripts/canonicalizer/heartbeat.py \\
          --batch-id '${BATCH}' \\
          --run-id '${RUN_ID}' \\
          --start-utc '${START_UTC}' \\
          --pid '${EXTRACT_PID}' \\
          --total '${TOTAL}' 2>&1
      } >> '${HEARTBEAT_LOG}' 2>&1
      sleep 180
    done
    # Final tick after extract exits — captures the cli.done summary.
    {
      echo
      echo '────── final tick at '\$(TZ=America/Bogota date '+%Y-%m-%d %I:%M:%S %p Bogota')' ──────'
      PYTHONPATH=src:. uv run python scripts/canonicalizer/heartbeat.py \\
        --batch-id '${BATCH}' \\
        --run-id '${RUN_ID}' \\
        --start-utc '${START_UTC}' \\
        --total '${TOTAL}' 2>&1
    } >> '${HEARTBEAT_LOG}' 2>&1
  " > /dev/null 2>&1 < /dev/null &
  HEARTBEAT_PID=$!
  disown "$HEARTBEAT_PID" 2>/dev/null || true
  echo "  pid: $HEARTBEAT_PID"
  echo ""

  echo "── waiting for extraction to finish ──"
  echo "  (this script blocks until pid $EXTRACT_PID exits OR cli.done is seen)"

  # Wait loop — poll every 30s. We don't sleep between polls because the
  # extract is already detached; we're just blocking the launcher.
  while kill -0 "$EXTRACT_PID" 2>/dev/null; do
    sleep 30
    if [[ -f logs/events.jsonl ]] && grep -q "\"run_id\": \"${RUN_ID}\"" logs/events.jsonl 2>/dev/null \
       && grep -q "\"kind\": \"cli.done\"" <(grep "\"run_id\": \"${RUN_ID}\"" logs/events.jsonl); then
      break
    fi
  done

  # Final status
  if grep -q "\"kind\": \"run.failed\"" <(grep "\"run_id\": \"${RUN_ID}\"" logs/events.jsonl 2>/dev/null) 2>/dev/null; then
    echo "  ❌ run.failed event observed."
    write_state "extract_failed"
    exit 5
  fi
  if [[ ! -f logs/events.jsonl ]] || ! grep -q "\"run_id\": \"${RUN_ID}\"" logs/events.jsonl 2>/dev/null; then
    echo "  ⚠ no events for run_id=$RUN_ID — extract may have died silently."
    write_state "extract_silent"
    exit 5
  fi
  echo "  ✅ extraction phase complete."
  write_state "extracted"

  # Capture the final heartbeat snapshot — the score step reads it for §4 stats.
  PYTHONPATH=src:. uv run python scripts/canonicalizer/heartbeat.py \
      --batch-id "$BATCH" \
      --run-id "$RUN_ID" \
      --start-utc "$START_UTC" \
      --total "$TOTAL" \
      --quiet-state-line >/dev/null 2>&1 || true
  echo "  ✅ heartbeat snapshot saved → ${RUN_DIR}/heartbeat_stats.json"
else
  echo "[launch_batch] [2/6] extract SKIPPED (--skip-extract — replay-only mode)"
fi

# ── 3. Ingest to local docker Supabase ────────────────────────────────
if [[ -z "$SKIP_INGEST" ]]; then
  echo ""
  echo "── [3/6] Ingest · replay veredicto JSONs → Supabase ($TARGET) ──"
  echo ""
  write_state "ingesting"
  if ! PYTHONPATH=src:. uv run python scripts/canonicalizer/ingest_vigencia_veredictos.py \
        --target "$TARGET" \
        --run-id "$RUN_ID" \
        --extracted-by ingest@v1 \
        --input-dir "$OUTPUT_DIR"; then
    # Partial-failure tolerance: ingest_vigencia_veredictos returns 1 if any
    # row errored. We continue to falkor sync + post + score because the
    # rows that DID insert still carry signal — only bail if zero made it.
    # ingest_vigencia_veredictos.py logs `inserted=N` to stderr/stdout; we
    # don't have a clean way to read the count back from a non-zero exit
    # without re-querying. Falkor sync and post-verify will surface the
    # actual state. Treat ingest non-zero as a soft warning here.
    echo "[launch_batch] ⚠ ingest reported errors; continuing to falkor sync + verify."
    echo "    (some veredictos may not have inserted — see the log above)"
    write_state "ingested_partial"
  else
    write_state "ingested"
  fi
else
  echo "[launch_batch] [3/6] ingest SKIPPED (--skip-ingest)"
fi

# ── 4. Falkor mirror sync ─────────────────────────────────────────────
if [[ -z "$SKIP_SYNC" ]]; then
  echo ""
  echo "── [4/6] Falkor sync · mirror (:Norm) subgraph ──"
  echo ""
  write_state "syncing_falkor"
  if ! PYTHONPATH=src:. uv run python scripts/canonicalizer/sync_vigencia_to_falkor.py \
        --target "$TARGET"; then
    echo "[launch_batch] ⚠ falkor sync returned non-zero; continuing to verify."
  fi
  write_state "synced_falkor"
else
  echo "[launch_batch] [4/6] falkor sync SKIPPED (--skip-sync)"
fi

# ── 5. Post-verify ────────────────────────────────────────────────────
if [[ -z "$SKIP_POST" ]]; then
  echo ""
  echo "── [5/6] Post-verify · re-run batch's test_questions AFTER ingestion ──"
  echo ""
  write_state "post_running"
  if ! PYTHONPATH=src:. uv run python scripts/canonicalizer/run_batch_tests.py \
        --batch-id "$BATCH" \
        --mode post \
        --base-url "$BASE_URL" \
        --run-id "verify-${BATCH}-${TS_UTC}" \
        --batches-config "$BATCHES_CONFIG"; then
    echo "[launch_batch] ⚠ post-verify failed; scoring may be incomplete."
  fi
  write_state "post_done"
else
  echo "[launch_batch] [5/6] post-verify SKIPPED (--skip-post)"
fi

# ── Score-skip implication ────────────────────────────────────────────
# When --skip-post is set, there are no post_*.json files for the score
# step to read; running it would crash with rc=4. Default SKIP_SCORE=1
# in that case (operator can still force --skip-score=0 via env override
# if they want the explicit failure). Closes fixplan_v5 §3 #5.
if [[ -n "$SKIP_POST" && -z "$SKIP_SCORE" ]]; then
  SKIP_SCORE=1
  SCORE_SKIPPED_BY_POST=1
  echo "[launch_batch] note: --skip-post implies --skip-score (no post_*.json to score)"
fi

# ── 6. Score + ledger append ──────────────────────────────────────────
if [[ -z "$SKIP_SCORE" ]]; then
  echo ""
  echo "── [6/6] Score · diff pre vs post + append ledger ──"
  echo ""
  write_state "scoring"
  SCORE_RC=0
  PYTHONPATH=src:. uv run python scripts/canonicalizer/run_batch_tests.py \
      --batch-id "$BATCH" \
      --mode score \
      --batches-config "$BATCHES_CONFIG" \
      --ledger "$LEDGER" \
      --extraction-stats "${RUN_DIR}/heartbeat_stats.json" \
      --extraction-run-id "$RUN_ID" \
      --attested-by "${USER:-claude-opus-4-7}" || SCORE_RC=$?
  if [[ "$SCORE_RC" -eq 0 ]]; then
    write_state "verified_PASS"
    echo "  ✅ batch PASS"
  else
    write_state "verified_FAIL"
    echo "  ❌ batch FAIL — see ledger.jsonl + per-question failures"
  fi
else
  echo "[launch_batch] [6/6] score SKIPPED (--skip-score)"
  # When score is skipped because of --skip-post, append an EXTRACT_ONLY
  # ledger row so the campaign roll-up still has a record of the run
  # (per fixplan_v5 §3 #5 — "ledger gaps confuse the campaign verdict").
  if [[ -n "${SCORE_SKIPPED_BY_POST:-}" ]]; then
    PYTHONPATH=src:. uv run python scripts/canonicalizer/append_extract_only_row.py \
        --batch-id "$BATCH" \
        --extraction-run-id "$RUN_ID" \
        --extraction-stats "${RUN_DIR}/heartbeat_stats.json" \
        --batches-config "$BATCHES_CONFIG" \
        --ledger "$LEDGER" \
        --attested-by "${USER:-claude-opus-4-7}" || \
      echo "[launch_batch] ⚠ failed to append EXTRACT_ONLY ledger row (non-fatal)"
    write_state "extract_only"
  fi
fi

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  Batch $BATCH done at $(bog)"
echo "  ledger: $LEDGER  (last line is this batch's verdict)"
echo "  state : $STATE_FILE"
echo "════════════════════════════════════════════════════════════════════"

# Recap rollback shape per state_canonicalizer_runv1.md §5
echo ""
echo "Rollback (R2 — undo just this run_id, preserve veredicto JSONs):"
echo "  docker exec supabase_db_lia-graph psql -U postgres -c \\"
echo "    \"DELETE FROM norm_vigencia_history WHERE extracted_via->>'run_id' = '${RUN_ID}'\""
echo ""
