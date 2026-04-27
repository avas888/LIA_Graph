#!/usr/bin/env bash
# run_parallel_extract.sh — fan out the EXTRACT phase across N batches.
#
# Per `feedback_runners_full_best_practices.md`: this orchestrator does
# NOT re-implement any of the launcher's best-practice surface. It
# delegates to `scripts/canonicalizer/launch_batch.sh` exclusively, via
# the existing skip-flag composition:
#
#   * Extract phase (parallel-able):  --skip-ingest --skip-sync --skip-post --skip-score
#   * Post phase (serialized):        --skip-pre --skip-extract
#
# Every preflight, run-once guard, atomic state write, heartbeat-cron
# prompt, fast-finish detection, partial-ingest tolerance, rollback
# recipe, and Bogotá time render fires through the canonical launcher
# code path. There is exactly ONE implementation; this script just
# orchestrates calls into it.
#
# Why split the pipeline this way:
#   The wall time is dominated by Gemini API calls during extract
#   (~25-35 sec per norm). Ingest + Falkor sync + post-verify + score
#   together take only 2-3 min per batch. Running extracts in parallel
#   compresses total wall time; serializing the post phase keeps the
#   shared `norms` / `norm_vigencia_history` / `(:Norm)` writes from
#   racing.
#
# Concurrency safety analysis (delegated to launch_batch.sh's own
# guarantees per spec, plus this orchestrator's discipline):
#   * Per-batch artifacts (JSONs, ledger row, heartbeat, run-state) are
#     batch_id-keyed → safe to parallel during extract.
#   * Postgres ingest + Falkor sync — STRICTLY serialized in phase 2.
#   * `logs/events.jsonl` — POSIX atomic per-line append (lines < 4 KB).
#   * `var/scraper_cache.db` — SQLite WAL mode; concurrent reads + write
#     serialization at the DB level. Acceptable.
#   * **Gemini API rate — TWO layers of protection.**
#       - Process-level: `--max-concurrent` cap (default 2). Caps how
#         many harnesses can be IN-FLIGHT simultaneously.
#       - Project-level: `src/lia_graph/gemini_throttle.py` token
#         bucket. ALL harnesses pass through it via a file-locked state
#         at `var/gemini_throttle_state.json`. Default 80 RPM (the
#         practical ceiling under the 1M TPM cap given our ~12K-token
#         call size, well under the 150 RPM raw cap). Configure with
#         `LIA_GEMINI_GLOBAL_RPM`.
#         The combined effect: even if you launch 10 batches with
#         --max-concurrent=10, the throttle keeps the project-wide RPS
#         under cap. The per-process concurrency cap is just a softer
#         coarse-grain limiter for predictability.
#       - Adapter-level: `gemini_runtime.py` retries 5xx/429 with
#         backoff (4 attempts, 0/4/12/30s). Catches transients the
#         throttle can't preempt.
#
# Official Gemini Tier 1 (paid) limits for `gemini-2.5-pro`:
#   * 150 RPM (requests per minute)
#   * 1,000 RPD (requests per day) — track this manually if running
#     more than ~7 batches × 150 norms/day
#   * 1M TPM (tokens per minute) — not currently throttled by us;
#     each call is ~16 KB prompt + ~2 KB response = ~10K tokens, so
#     150 RPM × 10K = 1.5M TPM — ABOVE the 1M cap, watch for tokens
#     limit on big-prompt batches.
#   Source: https://ai.google.dev/gemini-api/docs/rate-limits
#   See also: https://discuss.ai.google.dev/t/clarification-about-gemini-2-5-pro-tier-1-pricing-and-api-limits/129410
#
# Stop conditions inherited from per-batch protocol (via launch_batch.sh):
#   * run.failed in events → that batch's launcher exits non-zero.
#   * Per-batch FAIL after score → that batch's ledger row says FAIL;
#     this orchestrator does NOT halt the remaining batches (phase-level
#     halt rule lives in `run_phase.sh`).
#   * Duplicate batch_id in args → orchestrator errors out (run-once
#     invariant).
#
# Usage:
#   bash scripts/canonicalizer/run_parallel_extract.sh A1 A2 A3 A4
#   bash scripts/canonicalizer/run_parallel_extract.sh --max-concurrent 2 B1 B2 B3 B4 B5
#   bash scripts/canonicalizer/run_parallel_extract.sh --dry-run B1 B2 B3
#
# Required env: GEMINI_API_KEY (or legacy alias LIA_GEMINI_API_KEY) in
# .env.local — checked by launch_batch.sh's preflight, NOT here.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

LAUNCHER="scripts/canonicalizer/launch_batch.sh"

# Default 2 (not 3) — empirically `gemini-2.5-pro` returns HTTP 503
# ("model overloaded") under sustained 3-way concurrency, even within
# project quota. The Gemini adapter now retries on 5xx with back-off
# (gemini_runtime.py), but lowering the cap is the cheaper fix.
MAX_CONCURRENT=2
DRY_RUN=""
ENV_FILE=".env.local"
TARGET="wip"
EXTRA_LAUNCHER_FLAGS=()
BATCHES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-concurrent) MAX_CONCURRENT="$2"; shift 2 ;;
    --dry-run)        DRY_RUN=1; shift ;;
    --env-file)       ENV_FILE="$2"; shift 2 ;;
    --target)         TARGET="$2"; shift 2 ;;
    --launcher-flag)  EXTRA_LAUNCHER_FLAGS+=("$2"); shift 2 ;;
    -h|--help)        sed -n '1,55p' "$0"; exit 0 ;;
    --*)              echo "[run_parallel_extract] unknown flag: $1" >&2; exit 2 ;;
    *)                BATCHES+=("$1"); shift ;;
  esac
done

if [[ ${#BATCHES[@]} -eq 0 ]]; then
  echo "[run_parallel_extract] ERROR: pass at least one batch_id" >&2
  exit 2
fi

# Detect duplicates — these would race on the same output dir.
sorted=$(printf '%s\n' "${BATCHES[@]}" | sort)
unique=$(printf '%s\n' "${BATCHES[@]}" | sort -u)
if [[ "$sorted" != "$unique" ]]; then
  echo "[run_parallel_extract] ERROR: duplicate batch_id in args (run-once invariant)" >&2
  echo "  args sorted: $sorted" >&2
  exit 3
fi

bog() { TZ='America/Bogota' date '+%Y-%m-%d %I:%M:%S %p Bogotá'; }

mkdir -p logs

echo "════════════════════════════════════════════════════════════════════"
echo "  Parallel-extract runner (orchestrator over launch_batch.sh)"
echo "════════════════════════════════════════════════════════════════════"
echo "  start (Bogotá)  : $(bog)"
echo "  batches         : ${BATCHES[*]}"
echo "  max concurrent  : $MAX_CONCURRENT"
echo "  env file        : $ENV_FILE"
echo "  target          : $TARGET"
echo "  delegates to    : $LAUNCHER"
echo "════════════════════════════════════════════════════════════════════"
echo ""

if [[ -n "$DRY_RUN" ]]; then
  echo "[run_parallel_extract] --dry-run: nothing executed."
  exit 0
fi

# ── Phase 1: Parallel extracts (delegated to launch_batch.sh) ─────────
# Each call is a full launch_batch invocation with the post-extract
# steps skipped. The launcher itself does pre-baseline + detached
# extract + heartbeat snapshot + state-file ladder + rollback recipe
# print. We just orchestrate.
#
# bash 3.2-compat: macOS ships bash 3.2 (no associative arrays). We use
# parallel indexed arrays (BATCH_NAMES, BATCH_PIDS, BATCH_LOGS) keyed
# by index instead of `declare -A`.
echo "── PHASE 1: parallel extracts (max $MAX_CONCURRENT concurrent) ──"
echo ""

BATCH_NAMES=()
BATCH_PIDS=()
BATCH_LOGS=()

# Helper: lookup index of batch in BATCH_NAMES, return "" if not found.
batch_index() {
  local needle="$1"
  local i
  for i in "${!BATCH_NAMES[@]}"; do
    if [[ "${BATCH_NAMES[$i]}" == "$needle" ]]; then
      echo "$i"
      return 0
    fi
  done
}

launch_extract() {
  local batch="$1"
  local ts="$(date -u +%Y%m%dT%H%M%SZ)"
  local orchestrator_log="logs/parallel_extract_${batch}_${ts}.log"

  # The launcher's own log will be in its standard
  # logs/canonicalizer_<batch>_<ts>.log; the orchestrator log captures
  # the launcher's stdout/stderr.
  nohup bash "$LAUNCHER" \
        --batch "$batch" \
        --target "$TARGET" \
        --env-file "$ENV_FILE" \
        --skip-ingest --skip-sync --skip-post --skip-score \
        ${EXTRA_LAUNCHER_FLAGS[@]+"${EXTRA_LAUNCHER_FLAGS[@]}"} \
        > "$orchestrator_log" 2>&1 < /dev/null &

  local pid=$!
  disown "$pid" 2>/dev/null || true

  BATCH_NAMES+=("$batch")
  BATCH_PIDS+=("$pid")
  BATCH_LOGS+=("$orchestrator_log")
  echo "  [launch] $batch  pid=$pid  log=$orchestrator_log"
}

# Sliding-window concurrent launch.
in_flight=()
for batch in "${BATCHES[@]}"; do
  # Prune finished entries from in_flight; wait until window has space.
  while true; do
    new_in_flight=()
    for b in ${in_flight[@]+"${in_flight[@]}"}; do
      idx="$(batch_index "$b")"
      pid="${BATCH_PIDS[$idx]}"
      if kill -0 "$pid" 2>/dev/null; then
        new_in_flight+=("$b")
      else
        wait "$pid" 2>/dev/null || true
        echo "  [done  ] $b  pid=$pid"
      fi
    done
    in_flight=(${new_in_flight[@]+"${new_in_flight[@]}"})
    if [[ ${#in_flight[@]} -lt $MAX_CONCURRENT ]]; then
      break
    fi
    sleep 5
  done
  launch_extract "$batch"
  in_flight+=("$batch")
done

# Drain remaining.
for b in "${in_flight[@]}"; do
  idx="$(batch_index "$b")"
  pid="${BATCH_PIDS[$idx]}"
  while kill -0 "$pid" 2>/dev/null; do
    sleep 10
  done
  wait "$pid" 2>/dev/null || true
  echo "  [done  ] $b  pid=$pid"
done

echo ""
echo "── all extracts terminated. ──"
echo ""

# ── Phase 2: Serialized post-processing per batch ─────────────────────
# Each call is launch_batch.sh again, this time with --skip-pre
# --skip-extract so it picks up the already-written JSONs and runs
# ingest + falkor sync + post-verify + score with full best-practice
# coverage.
echo "── PHASE 2: serialized post-processing (ingest + sync + post + score) ──"
echo ""

for batch in "${BATCHES[@]}"; do
  echo ""
  echo "──────────── $batch · post-processing ────────────"
  bash "$LAUNCHER" \
    --batch "$batch" \
    --target "$TARGET" \
    --env-file "$ENV_FILE" \
    --skip-pre --skip-extract \
    ${EXTRA_LAUNCHER_FLAGS[@]+"${EXTRA_LAUNCHER_FLAGS[@]}"} \
    || echo "  ⚠ $batch post-processing returned non-zero (see ledger row)"
done

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  Parallel runner done @ $(bog)"
echo "  Persisted to:"
echo "    JSONs:    evals/vigencia_extraction_v1/<batch>/*.json"
echo "    Postgres: norm_vigencia_history (filter: extracted_via->>'run_id' LIKE 'canonicalizer-<batch>-*')"
echo "    Falkor:   (:Norm) subgraph + structured edges"
echo "    Ledger:   evals/canonicalizer_run_v1/ledger.jsonl"
echo "    State:    evals/canonicalizer_run_v1/<batch>/run_state.json"
echo "  Don't forget: git add evals/vigencia_extraction_v1 evals/canonicalizer_run_v1"
echo "════════════════════════════════════════════════════════════════════"
