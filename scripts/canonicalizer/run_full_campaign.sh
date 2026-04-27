#!/usr/bin/env bash
# run_full_campaign.sh — autonomous multi-phase canonicalizer driver.
#
# Goal: run Phases B-rerun-weak through K with no human supervision,
# producing a clear campaign log the operator can read on return.
#
# Per `feedback_runners_full_best_practices.md`, this script does NOT
# re-implement any best-practice surface. It is a thin loop over
# `scripts/canonicalizer/run_parallel_extract.sh`, which itself
# delegates to `scripts/canonicalizer/launch_batch.sh`. The full
# best-practice chain (preflights, run-once guard, atomic state writes,
# heartbeat, partial-ingest tolerance, rollback recipe, Bogotá times,
# project-wide Gemini throttle, adapter retry) fires through that
# canonical path.
#
# What it does for each phase:
#   1. Resolve the phase's batch_ids from
#      `config/canonicalizer_run_v1/batches.yaml` in dependency order.
#   2. Run them through `run_parallel_extract.sh --max-concurrent 2`.
#   3. Inspect `evals/canonicalizer_run_v1/ledger.jsonl` for any batch
#      in this phase whose latest verdict is FAIL with success rate
#      < 80% — flag as weak.
#   4. Re-run weak batches (cleaning their state first, since
#      `--allow-rerun` would otherwise overwrite); the new run picks up
#      the latest prompt + parser fixes.
#   5. Append a phase summary to
#      `evals/canonicalizer_run_v1/campaign_log.md`.
#   6. Auto-stop if 2 consecutive phases have >50% refusal rate
#      (signals API daily-quota exhaustion or systemic issue).
#
# Stop conditions:
#   * Phase succeeds (>=80% extract rate) → advance.
#   * Phase mixed (60-80%) → re-run weak batches once, then advance.
#   * Phase weak (<60%) → flagged in campaign log; advance anyway
#     (operator triages on return).
#   * Two consecutive phases <50% extract → STOP entire campaign;
#     write campaign-halted entry to log; assume API quota issue.
#
# Phases run, in order:
#   B-rerun-weak  (only the Phase B batches with <80% from the prior run)
#   C, D, E, F, G, H, I, J, K
#   (Phase L is SME-led — never autonomous)
#
# Output:
#   * `evals/canonicalizer_run_v1/campaign_log.md` — per-phase summary
#     with success rate, weak-batch list, re-run results.
#   * `evals/canonicalizer_run_v1/campaign_state.json` — machine-
#     readable progress (current phase, last completed phase,
#     timestamp). Atomic temp+rename per write.
#
# Usage:
#   bash scripts/canonicalizer/run_full_campaign.sh
#   bash scripts/canonicalizer/run_full_campaign.sh --skip-b-rerun
#   bash scripts/canonicalizer/run_full_campaign.sh --phases C D E
#   bash scripts/canonicalizer/run_full_campaign.sh --max-concurrent 1   (very conservative)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

PARALLEL="scripts/canonicalizer/run_parallel_extract.sh"
LEDGER="evals/canonicalizer_run_v1/ledger.jsonl"
CAMPAIGN_LOG="evals/canonicalizer_run_v1/campaign_log.md"
CAMPAIGN_STATE="evals/canonicalizer_run_v1/campaign_state.json"
BATCHES_YAML="config/canonicalizer_run_v1/batches.yaml"

DEFAULT_PHASES=(B-rerun-weak C D E F G H I J K)
PHASES=()
SKIP_B_RERUN=""
MAX_CONCURRENT=2
WEAK_THRESHOLD=80      # batches below this success rate get re-run
QUOTA_HALT_THRESHOLD=50 # phase < this success rate counts as quota-warning
DRY_RUN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --phases)         shift; while [[ $# -gt 0 && "$1" != --* ]]; do PHASES+=("$1"); shift; done ;;
    --skip-b-rerun)   SKIP_B_RERUN=1; shift ;;
    --max-concurrent) MAX_CONCURRENT="$2"; shift 2 ;;
    --weak-threshold) WEAK_THRESHOLD="$2"; shift 2 ;;
    --dry-run)        DRY_RUN=1; shift ;;
    -h|--help)        sed -n '1,55p' "$0"; exit 0 ;;
    *)                echo "[campaign] unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ ${#PHASES[@]} -eq 0 ]]; then
  PHASES=("${DEFAULT_PHASES[@]}")
fi

mkdir -p "$(dirname "$CAMPAIGN_LOG")" logs

bog() { TZ='America/Bogota' date '+%Y-%m-%d %I:%M:%S %p Bogotá'; }
campaign_started_bogota="$(bog)"
campaign_started_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── Resolve a phase's batch_ids in dep order ───────────────────────────
resolve_phase_batches() {
  local phase="$1"
  PYTHONPATH=src:. uv run python -c "
import sys, yaml
from collections import defaultdict, deque
blobs = yaml.safe_load(open('$BATCHES_YAML').read()) or []
in_phase = [b for b in blobs if str(b.get('phase') or '').strip() == '$phase']
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
print(' '.join(out))
" 2>/dev/null
}

# ── Identify weak batches in a list (latest run < WEAK_THRESHOLD%) ─────
find_weak_batches() {
  local -a candidates=("$@")
  PYTHONPATH=src:. uv run python -c "
import json, sys
from pathlib import Path

THRESHOLD = $WEAK_THRESHOLD
cands = set('''${candidates[@]}'''.split())
ledger = Path('$LEDGER')
latest = {}
if ledger.is_file():
    with ledger.open() as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except:
                continue
            bid = row.get('batch_id')
            if bid in cands:
                latest[bid] = row  # last write wins
weak = []
for bid in cands:
    row = latest.get(bid)
    if row is None:
        weak.append(bid)  # never run — treat as weak
        continue
    v, t = row.get('veredictos') or 0, row.get('norms_targeted') or 0
    pct = 100 * v / max(1, t)
    if pct < THRESHOLD:
        weak.append(bid)
print(' '.join(sorted(weak)))
" 2>/dev/null
}

# ── Append a phase row to the campaign log ─────────────────────────────
log_phase_summary() {
  local phase="$1"
  local batches="$2"
  local started="$3"
  local ended="$4"
  local result="$5"
  local notes="${6:-}"

  if [[ ! -f "$CAMPAIGN_LOG" ]]; then
    cat > "$CAMPAIGN_LOG" <<EOF
# Canonicalizer campaign log

> Auto-generated by \`scripts/canonicalizer/run_full_campaign.sh\`. Each row is
> one phase; weak-batch re-runs append a sub-row.

Started: $campaign_started_bogota

| Phase | Batches | Started (Bogotá) | Ended (Bogotá) | Verdict | Notes |
|---|---|---|---|---|---|
EOF
  fi
  echo "| $phase | $batches | $started | $ended | $result | $notes |" >> "$CAMPAIGN_LOG"
}

# ── Update campaign state file (atomic) ────────────────────────────────
write_state() {
  local phase="$1"
  local status="$2"
  python3 -c "
import json, datetime as _dt
from pathlib import Path
p = Path('$CAMPAIGN_STATE')
existing = {}
if p.exists():
    try:
        existing = json.loads(p.read_text())
    except:
        existing = {}
existing.update({
    'campaign_started_bogota': '$campaign_started_bogota',
    'current_phase': '$phase',
    'status': '$status',
    'updated_utc': _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'updated_bogota': _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=-5))).strftime('%Y-%m-%d %I:%M:%S %p Bogotá'),
})
tmp = p.with_suffix('.json.tmp')
tmp.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
tmp.replace(p)
"
}

# ── Compute success rate for a list of batches (their latest runs) ─────
phase_success_rate() {
  local -a batches=("$@")
  PYTHONPATH=src:. uv run python -c "
import json
from pathlib import Path
batches = set('''${batches[@]}'''.split())
ledger = Path('$LEDGER')
latest = {}
if ledger.is_file():
    with ledger.open() as fh:
        for line in fh:
            try: row = json.loads(line)
            except: continue
            if row.get('batch_id') in batches:
                latest[row['batch_id']] = row
total_v = total_t = 0
for row in latest.values():
    total_v += row.get('veredictos') or 0
    total_t += row.get('norms_targeted') or 0
print(f'{100*total_v/max(1,total_t):.0f}' if total_t else '0')
" 2>/dev/null
}

# ── Banner ─────────────────────────────────────────────────────────────
echo "════════════════════════════════════════════════════════════════════"
echo "  Canonicalizer full campaign"
echo "════════════════════════════════════════════════════════════════════"
echo "  start (Bogotá)   : $campaign_started_bogota"
echo "  phases           : ${PHASES[*]}"
echo "  max concurrent   : $MAX_CONCURRENT"
echo "  weak threshold   : ${WEAK_THRESHOLD}%"
echo "  campaign log     : $CAMPAIGN_LOG"
echo "  campaign state   : $CAMPAIGN_STATE"
echo "  delegates to     : $PARALLEL → launch_batch.sh"
echo "  Gemini throttle  : 80 RPM project-wide (LIA_GEMINI_GLOBAL_RPM=…)"
echo "                     150 RPM Tier 1 cap; 1M TPM binding for our prompt size"
echo "════════════════════════════════════════════════════════════════════"
echo ""

if [[ -n "$DRY_RUN" ]]; then
  for phase in "${PHASES[@]}"; do
    if [[ "$phase" == "B-rerun-weak" ]]; then
      weak_in_b=$(find_weak_batches B1 B2 B3 B4 B5 B6 B7 B8 B9 B10)
      echo "  [B-rerun-weak] would re-run: ${weak_in_b:-(none weak)}"
    else
      ids=$(resolve_phase_batches "$phase")
      echo "  [$phase] would run: $ids"
    fi
  done
  echo ""
  echo "[campaign] --dry-run: nothing executed."
  exit 0
fi

# ── Drive each phase ───────────────────────────────────────────────────
consecutive_low=0

for phase in "${PHASES[@]}"; do
  echo ""
  echo "════════════════════════════════════════════════════════════════════"
  echo "  Phase: $phase  ·  $(bog)"
  echo "════════════════════════════════════════════════════════════════════"
  write_state "$phase" "running"

  if [[ "$phase" == "B-rerun-weak" ]]; then
    if [[ -n "$SKIP_B_RERUN" ]]; then
      echo "[campaign] --skip-b-rerun: skipping."
      log_phase_summary "B-rerun-weak" "(skipped via flag)" "$(bog)" "$(bog)" "SKIPPED" "user flag"
      continue
    fi
    weak=$(find_weak_batches B1 B2 B3 B4 B5 B6 B7 B8 B9 B10)
    if [[ -z "$weak" ]]; then
      echo "[campaign] no weak Phase B batches — skipping rerun."
      log_phase_summary "B-rerun-weak" "(none weak)" "$(bog)" "$(bog)" "SKIPPED" "all Phase B batches ≥${WEAK_THRESHOLD}%"
      continue
    fi
    echo "[campaign] weak Phase B batches: $weak"
    # Clean their state so the run-once guard releases.
    for bid in $weak; do
      rm -rf "evals/vigencia_extraction_v1/$bid"
      rm -rf "evals/canonicalizer_run_v1/$bid"
    done
    rm -rf evals/vigencia_extraction_v1/_debug
    started="$(bog)"
    bash "$PARALLEL" --max-concurrent "$MAX_CONCURRENT" $weak \
      > "logs/campaign_${phase}_$(date -u +%Y%m%dT%H%M%SZ).log" 2>&1 \
      || echo "[campaign] B-rerun returned non-zero (continuing)"
    ended="$(bog)"
    rate=$(phase_success_rate $weak)
    log_phase_summary "B-rerun-weak" "$weak" "$started" "$ended" "${rate}%" ""
    [[ "$rate" -lt "$QUOTA_HALT_THRESHOLD" ]] && consecutive_low=$((consecutive_low+1)) || consecutive_low=0
  else
    ids=$(resolve_phase_batches "$phase")
    if [[ -z "$ids" ]]; then
      echo "[campaign] no batches in phase $phase (config gap?)"
      log_phase_summary "$phase" "(none)" "$(bog)" "$(bog)" "SKIPPED" "no batches in YAML"
      continue
    fi
    echo "[campaign] batches: $ids"
    started="$(bog)"
    bash "$PARALLEL" --max-concurrent "$MAX_CONCURRENT" $ids \
      > "logs/campaign_${phase}_$(date -u +%Y%m%dT%H%M%SZ).log" 2>&1 \
      || echo "[campaign] phase $phase parallel run returned non-zero (continuing)"
    ended="$(bog)"
    rate=$(phase_success_rate $ids)
    weak_after=$(find_weak_batches $ids)

    if [[ -n "$weak_after" ]]; then
      # Re-run weak batches in this phase (one extra pass, with the latest fixes).
      echo "[campaign] phase $phase weak batches after first pass: $weak_after"
      for bid in $weak_after; do
        rm -rf "evals/vigencia_extraction_v1/$bid"
        rm -rf "evals/canonicalizer_run_v1/$bid"
      done
      rm -rf evals/vigencia_extraction_v1/_debug
      bash "$PARALLEL" --max-concurrent "$MAX_CONCURRENT" $weak_after \
        > "logs/campaign_${phase}_rerun_$(date -u +%Y%m%dT%H%M%SZ).log" 2>&1 \
        || echo "[campaign] phase $phase rerun returned non-zero (continuing)"
      rate=$(phase_success_rate $ids)  # re-compute after rerun
      log_phase_summary "$phase" "$ids" "$started" "$(bog)" "${rate}%" "rerun: $weak_after"
    else
      log_phase_summary "$phase" "$ids" "$started" "$ended" "${rate}%" ""
    fi
    [[ "$rate" -lt "$QUOTA_HALT_THRESHOLD" ]] && consecutive_low=$((consecutive_low+1)) || consecutive_low=0
  fi

  # Quota-halt heuristic
  if [[ "$consecutive_low" -ge 2 ]]; then
    echo ""
    echo "[campaign] ⚠ two consecutive phases under ${QUOTA_HALT_THRESHOLD}% — halting."
    echo "  Likely cause: gemini-2.5-pro daily quota (1000 RPD) exhausted."
    echo "  Resume by re-running this script tomorrow (or set LIA_GEMINI_MODEL to a different tier)."
    write_state "$phase" "halted_quota"
    log_phase_summary "(halt)" "(n/a)" "$(bog)" "$(bog)" "HALT" "consecutive low rates ≥ 2; presumed quota"
    break
  fi
done

# ── Final summary ──────────────────────────────────────────────────────
write_state "(done)" "complete"
final_bogota="$(bog)"
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  Campaign done @ $final_bogota"
echo "  Started:           $campaign_started_bogota"
echo "  Phases run:        ${PHASES[*]}"
echo "  Campaign log:      $CAMPAIGN_LOG"
echo "  Catalog (refusals): evals/canonicalizer_run_v1/phase_*_failure_catalog.md"
echo "  Persisted to:"
echo "    JSONs:    evals/vigencia_extraction_v1/<batch>/*.json"
echo "    Postgres: norm_vigencia_history (filter: extracted_via->>'run_id' LIKE 'canonicalizer-%')"
echo "    Falkor:   (:Norm) subgraph + structured edges"
echo "    Ledger:   $LEDGER"
echo "  Don't forget: git add evals/vigencia_extraction_v1 evals/canonicalizer_run_v1"
echo "════════════════════════════════════════════════════════════════════"

# Append a closing line to the campaign log so the operator sees "done".
{
  echo ""
  echo "Campaign ended: $final_bogota"
} >> "$CAMPAIGN_LOG"
