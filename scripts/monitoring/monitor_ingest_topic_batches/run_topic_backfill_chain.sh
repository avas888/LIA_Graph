#!/usr/bin/env bash
# ingestionfix_v3 Phase 3 — topic-coverage backfill chain supervisor (SKELETON).
#
# This Phase-2 skeleton ships the gate-enforcement and `--gate-only` pieces
# the plan requires. The full autonomous batch loop (STOP_BACKFILL sentinel,
# 30-second yield, state-file checkpointing, atomic rewrites) lands in
# Phase 3 proper — by that point the Quality Gate artifact must already
# exist + be `status: passed`.
#
# Exit codes:
#   0 = success (gate-only batch completed, or chain progressed)
#   2 = gate prerequisite failed (missing or status != passed)
#   3 = plan.json missing or invalid
#   1 = any other failure
#
# Usage:
#   bash scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh --gate-only
#     → run ONLY batch 1 (Quality Gate batch), then stop
#
#   bash scripts/monitoring/monitor_ingest_topic_batches/run_topic_backfill_chain.sh
#     → run batches 2..N (autonomous). Refuses unless the gate file shows
#       status=passed.
#
# See docs/next/ingestionfix_v3.md §5 Phase 2 + §5 Phase 3 for the full
# contract.

set -euo pipefail

# Walk three dirs up so repo-root paths resolve whether the script lives at
# scripts/monitoring/monitor_ingest_topic_batches/ or is symlinked elsewhere.
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

PLAN_FILE="${PLAN_FILE:-artifacts/fingerprint_bust/plan.json}"
GATE_FILE="${GATE_FILE:-artifacts/batch_1_quality_gate.json}"
STATE_FILE="${STATE_FILE:-artifacts/backfill_state.json}"
STOP_FILE="${STOP_FILE:-artifacts/STOP_BACKFILL}"

MODE="chain"
for arg in "$@"; do
  case "$arg" in
    --gate-only)
      MODE="gate-only"
      ;;
    -h|--help)
      sed -n '2,30p' "$0"
      exit 0
      ;;
    *)
      echo "[chain] unknown flag: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$PLAN_FILE" ]]; then
  echo "[chain] ERROR: plan file not found at $PLAN_FILE" >&2
  exit 3
fi

# --- Gate enforcement -------------------------------------------------
# Autonomous chain mode (batches 2..N) requires a passed gate file. The
# --gate-only mode skips this check because its whole job is to produce
# the batch-1 data the gate then validates.
if [[ "$MODE" == "chain" ]]; then
  if [[ ! -f "$GATE_FILE" ]]; then
    cat >&2 <<EOF
[chain] REFUSED: gate file not found at $GATE_FILE

Before the autonomous chain can run, you must:
  1. Run batch 1 via: bash scripts/run_topic_backfill_chain.sh --gate-only
  2. Run validator:   python scripts/validate_batch.py --batch 1 --gate
  3. Complete M1-M3 + U1-U4 manually; set status=passed in $GATE_FILE

See docs/next/ingestionfix_v3.md §5 Phase 3.0 for the full check inventory.
EOF
    exit 2
  fi

  # The gate file must report status=passed. jq is required; if not
  # present, fall back to a lean python -c parse so CI envs don't need jq.
  GATE_STATUS=""
  if command -v jq >/dev/null 2>&1; then
    GATE_STATUS="$(jq -r '.status // "missing"' "$GATE_FILE" 2>/dev/null || echo "unreadable")"
  else
    GATE_STATUS="$(python3 -c "import json,sys; print(json.load(open('$GATE_FILE')).get('status','missing'))" 2>/dev/null || echo "unreadable")"
  fi

  if [[ "$GATE_STATUS" != "passed" ]]; then
    cat >&2 <<EOF
[chain] REFUSED: $GATE_FILE status is '$GATE_STATUS' (expected 'passed').

The autonomous chain will not advance past batch 1 until the operator
has completed M1-M3 + U1-U4 and marked the gate file status: passed.

See docs/next/ingestionfix_v3.md §5 Phase 3.0.
EOF
    exit 2
  fi
fi

# --- Phase 2 stops here -----------------------------------------------
# The full batch loop (STOP_BACKFILL poll, fingerprint_bust per batch,
# launch_phase9a, 30s yield, state-file checkpoint, done_batches_log
# append) lands in Phase 3 proper. The skeleton ships the plumbing that
# the unit tests need to lock the gate-refusal contract.

case "$MODE" in
  gate-only)
    cat >&2 <<'EOF'
[chain] --gate-only: the Phase 2 skeleton does not yet run batches.
        Wire-up lands in ingestionfix_v3 Phase 3 proper. For now, run
        batch 1 manually via the per-batch launcher:

          bash scripts/launch_batch.sh --batch 1 --dry-run    # preview
          bash scripts/launch_batch.sh --batch 1              # real run
          # ... wait for ingest.delta.cli.done in logs/events.jsonl ...
          python scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py \
            --batch 1 --gate --manifest <latest bust manifest> \
            --delta-id <delta_id> --delta-elapsed-ms <ms>

        Then fill M1-M3 + U1-U4 in the gate file and set status: passed.
EOF
    exit 0
    ;;
  chain)
    cat >&2 <<'EOF'
[chain] gate passed. Autonomous batch loop (batches 2..N) lands in
        Phase 3 proper. For now, run each batch manually per the
        fingerprint_bust/launch_phase9a/validate_batch pattern above.
EOF
    exit 0
    ;;
esac
