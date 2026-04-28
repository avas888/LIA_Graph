#!/usr/bin/env bash
# run_cascade_v5.sh — drive the fixplan_v5 §4.B cascade sequentially.
#
# Iterates the 22 remaining batches in §4.B order, launching each via
# launch_batch.sh --allow-rerun --skip-post. After each batch:
#   * Parses the new ledger row.
#   * Appends a one-line campaign-log entry.
#   * Halts if two consecutive batches return 0 veredictos
#     (kill-switch per fixplan_v4 §6.A).
#
# Per memory `feedback_canonicalizer_autonomous_progression`, runs without
# check-ins until a stop condition fires.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

BATCHES=(
  J6 J7 K4
  J1 J2 J3 J4
  K3
  G1
  G6
  F2
  E5
  E6b E6c
  E1a E1b E1d
  E2a E2c
  E3b
  J8b
  D5
)

CAMPAIGN_LOG="logs/cascade_v5_campaign.md"
LEDGER="evals/canonicalizer_run_v1/ledger.jsonl"

bog() { TZ='America/Bogota' date '+%Y-%m-%d %I:%M:%S %p Bogotá'; }

echo "" >> "$CAMPAIGN_LOG"
echo "## Cascade v5 — started $(bog)" >> "$CAMPAIGN_LOG"
echo "" >> "$CAMPAIGN_LOG"
echo "| # | batch | started | wall | norms | veredictos | refusals | errors | top_refusal |" >> "$CAMPAIGN_LOG"
echo "|---|---|---|---:|---:|---:|---:|---:|---|" >> "$CAMPAIGN_LOG"

zero_streak=0
total_started_bog="$(bog)"

for i in "${!BATCHES[@]}"; do
  b="${BATCHES[$i]}"
  step=$((i + 1))
  start_bog="$(bog)"

  echo "════════════════════════════════════════════════════════════════════"
  echo "  CASCADE step $step/${#BATCHES[@]}: batch $b · start $start_bog"
  echo "════════════════════════════════════════════════════════════════════"

  pre_lines=$(wc -l < "$LEDGER" 2>/dev/null || echo 0)

  bash scripts/canonicalizer/launch_batch.sh \
    --batch "$b" --allow-rerun --skip-post \
    > "logs/cascade_v5_${b}.log" 2>&1
  rc=$?

  post_lines=$(wc -l < "$LEDGER" 2>/dev/null || echo 0)

  if [[ "$post_lines" -gt "$pre_lines" ]]; then
    row=$(tail -1 "$LEDGER")
    summary=$(echo "$row" | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
top = next(iter((d.get('refusal_reasons_top') or {}).items()), ('—', 0))
print(f\"{d.get('wall_seconds','?')}s|{d.get('norms_targeted','?')}|{d.get('veredictos','?')}|{d.get('refusals','?')}|{d.get('errors','?')}|{top[0]}({top[1]})\")")
    IFS='|' read -r wall norms ver refs errs top <<< "$summary"
    echo "| $step | $b | $start_bog | ${wall}s | $norms | $ver | $refs | $errs | $top |" >> "$CAMPAIGN_LOG"
    if [[ "$ver" == "0" || "$ver" == "None" ]]; then
      zero_streak=$((zero_streak + 1))
    else
      zero_streak=0
    fi
  else
    echo "| $step | $b | $start_bog | ?s | ? | LAUNCHER_RC=$rc | ? | ? | (no ledger row) |" >> "$CAMPAIGN_LOG"
    zero_streak=$((zero_streak + 1))
  fi

  if [[ "$zero_streak" -ge 2 ]]; then
    echo "" >> "$CAMPAIGN_LOG"
    echo "🛑 **KILL-SWITCH: 2 consecutive batches returned 0 veredictos. Halting cascade at step $step ($b).**" >> "$CAMPAIGN_LOG"
    echo "" >> "$CAMPAIGN_LOG"
    exit 5
  fi
done

echo "" >> "$CAMPAIGN_LOG"
echo "✅ **Cascade v5 complete at $(bog).** Started $total_started_bog." >> "$CAMPAIGN_LOG"
echo "" >> "$CAMPAIGN_LOG"
