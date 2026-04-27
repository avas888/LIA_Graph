#!/usr/bin/env bash
# run_phase.sh — drive an entire canonicalizer Phase (A, B, C, ...) to its end.
#
# Reads `config/canonicalizer_run_v1/batches.yaml`, finds every batch with
# `phase: <X>`, sorts them by their `depends_on` graph (topological), and
# runs them through `scripts/canonicalizer/launch_batch.sh` one at a time.
#
# Stop conditions (per `docs/re-engineer/canonicalizer_runv1.md` §7):
#   * Per-batch FAIL → STOP the phase. Do NOT advance.
#   * Two consecutive FAILs in the phase → STOP and escalate (operator
#     decision; reassess slicing).
#   * --max-batches budget reached → STOP cleanly with a partial-phase
#     summary.
#
# Successful exit means every batch in the phase ended `verified_PASS`
# (or DEFERRED with no hard failures). The caller should then surface the
# phase to the SME for end-of-phase signoff per state §1.G.
#
# Usage:
#   bash scripts/canonicalizer/run_phase.sh --phase A
#   bash scripts/canonicalizer/run_phase.sh --phase B --max-batches 3
#   bash scripts/canonicalizer/run_phase.sh --phase A --start-from A2
#
# Env: same as launch_batch.sh (GEMINI_API_KEY, SUPABASE_URL, etc).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

PHASE=""
MAX_BATCHES=0
START_FROM=""
DRY_RUN=""
LAUNCH_FLAGS=""
BATCHES_CONFIG="config/canonicalizer_run_v1/batches.yaml"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --phase)            PHASE="$2"; shift 2 ;;
    --max-batches)      MAX_BATCHES="$2"; shift 2 ;;
    --start-from)       START_FROM="$2"; shift 2 ;;
    --dry-run)          DRY_RUN=1; shift ;;
    --batches-config)   BATCHES_CONFIG="$2"; shift 2 ;;
    --launch-flag)      LAUNCH_FLAGS="$LAUNCH_FLAGS $2"; shift 2 ;;
    -h|--help)          sed -n '1,30p' "$0"; exit 0 ;;
    *) echo "[run_phase] unknown flag: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$PHASE" ]]; then
  echo "[run_phase] ERROR: pass --phase <X>  (e.g. A, B, C, ..., L)" >&2
  exit 2
fi

# ── Resolve the phase's batch ids in dependency order ─────────────────
ORDERED_IDS=$(PYTHONPATH=src:. uv run python -c "
import sys, yaml
from collections import defaultdict, deque
blobs = yaml.safe_load(open('$BATCHES_CONFIG').read()) or []
in_phase = [b for b in blobs if str(b.get('phase') or '').strip() == '$PHASE']
ids = {b['batch_id']: set(b.get('depends_on') or []) for b in in_phase}
indeg = {bid: 0 for bid in ids}
graph = defaultdict(list)
for bid, deps in ids.items():
    for d in deps:
        if d in ids:
            graph[d].append(bid)
            indeg[bid] += 1
ready = deque(sorted(b for b, n in indeg.items() if n == 0))
out = []
while ready:
    cur = ready.popleft()
    out.append(cur)
    for nxt in graph[cur]:
        indeg[nxt] -= 1
        if indeg[nxt] == 0:
            ready.append(nxt)
print('\n'.join(out))
")

if [[ -z "$ORDERED_IDS" ]]; then
  echo "[run_phase] ERROR: phase $PHASE has no batches in $BATCHES_CONFIG" >&2
  exit 3
fi

bog() { TZ='America/Bogota' date '+%Y-%m-%d %I:%M:%S %p Bogotá'; }

echo "════════════════════════════════════════════════════════════════════"
echo "  Phase $PHASE driver"
echo "════════════════════════════════════════════════════════════════════"
echo "  start (Bogotá): $(bog)"
echo "  batches in order:"
echo "$ORDERED_IDS" | sed 's/^/    /'
echo "  max-batches  : ${MAX_BATCHES:-unlimited}"
echo "  start-from   : ${START_FROM:-(first)}"
echo "════════════════════════════════════════════════════════════════════"
echo ""

if [[ -n "$DRY_RUN" ]]; then
  echo "[run_phase] --dry-run: nothing executed."
  exit 0
fi

# ── Drive batches ─────────────────────────────────────────────────────
SUMMARY=()
PASS_COUNT=0
FAIL_COUNT=0
CONSEC_FAIL=0
SKIPPED_BEFORE_START=0
RAN_COUNT=0
BUDGET_HIT=""

# `<<<` is a here-string — gives us a clean for-loop without piping.
while IFS= read -r BID; do
  [[ -z "$BID" ]] && continue

  # Honor --start-from
  if [[ -n "$START_FROM" && "$BID" != "$START_FROM" ]]; then
    if [[ "$SKIPPED_BEFORE_START" -eq 1 ]]; then
      :  # already started — fall through
    else
      echo "[run_phase] skip $BID (before --start-from $START_FROM)"
      continue
    fi
  fi
  SKIPPED_BEFORE_START=1

  # Budget cap
  if [[ "$MAX_BATCHES" -gt 0 && "$RAN_COUNT" -ge "$MAX_BATCHES" ]]; then
    BUDGET_HIT="reached --max-batches $MAX_BATCHES"
    echo "[run_phase] budget cap hit; stopping."
    break
  fi

  echo ""
  echo "──────────────── $BID ─────────────────────────────────────────"
  echo ""

  RC=0
  bash scripts/canonicalizer/launch_batch.sh --batch "$BID" $LAUNCH_FLAGS || RC=$?

  RAN_COUNT=$((RAN_COUNT + 1))
  if [[ "$RC" -eq 0 ]]; then
    PASS_COUNT=$((PASS_COUNT + 1))
    CONSEC_FAIL=0
    SUMMARY+=("$BID PASS")
    echo ""
    echo "[run_phase] $BID PASS"
  else
    FAIL_COUNT=$((FAIL_COUNT + 1))
    CONSEC_FAIL=$((CONSEC_FAIL + 1))
    SUMMARY+=("$BID FAIL (rc=$RC)")
    echo ""
    echo "[run_phase] $BID FAIL (launcher rc=$RC) — STOP per per-batch-FAIL rule."
    if [[ "$CONSEC_FAIL" -ge 2 ]]; then
      echo "[run_phase] ⚠ two consecutive failures — escalate (operator decision)."
    fi
    break
  fi
done <<< "$ORDERED_IDS"

# ── Summary ───────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  Phase $PHASE summary @ $(bog)"
echo "════════════════════════════════════════════════════════════════════"
for line in "${SUMMARY[@]}"; do
  echo "    $line"
done
TOTAL_IN_PHASE=$(echo "$ORDERED_IDS" | wc -l | tr -d ' ')
echo ""
echo "  ran=$RAN_COUNT pass=$PASS_COUNT fail=$FAIL_COUNT (of $TOTAL_IN_PHASE in phase)"
[[ -n "$BUDGET_HIT" ]] && echo "  $BUDGET_HIT"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  echo "  status: ❌ phase did NOT complete cleanly"
  exit 1
fi
if [[ "$RAN_COUNT" -lt "$TOTAL_IN_PHASE" ]]; then
  echo "  status: ⚠ partial (budget cap or --start-from); remaining batches not run"
  exit 0
fi
echo "  status: ✅ phase $PHASE complete — surface to SME for §1.G signoff"
echo "════════════════════════════════════════════════════════════════════"
