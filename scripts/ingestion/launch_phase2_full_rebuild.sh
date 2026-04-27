#!/usr/bin/env bash
# Full-rebuild cloud ingest launcher (detached, audit-gated).
#
# Mirrors launch_phase9a.sh / launch_phase9b.sh shape: nohup + disown + direct
# redirects (NO tee pipe). Survives terminal close, Claude exit, shell
# disconnect. Reparenting to PPID=1 is the success signal.
#
# Targets `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production`,
# which auto-sources .env.staging and runs the canonical full-rebuild path
# (build artifacts + SupabaseCorpusSink + Falkor execute-load). This is the
# path where the §J TEMA-cleanup helper added in 2026-04-24 actually fires —
# delta path skips unchanged docs, full rebuild MERGEs every node + edge.
#
# Defaults LIA_INGEST_CLASSIFIER_WORKERS=4 per the rule promoted to default in
# `docs/learnings/ingestion/parallelism-and-rate-limits.md` after the
# 2026-04-24 §J rebuild measured 27.5% silent N1-only degradation at workers=8.
# Override by exporting LIA_INGEST_CLASSIFIER_WORKERS before invoking this
# script — but workers > 4 against production requires either the TokenBudget
# primitive being live or knowingly accepting the degradation.
#
# After the rebuild exits, the launcher invokes scripts/diagnostics/audit_rebuild.py
# inline. The audit's exit code is recorded as PHASE2_AUDIT_VERDICT=clean|degraded
# at the bottom of the log — that is the trustworthy success signal, not the
# rebuild's own exit code (which can be 0 even with a 27.5% degraded classifier
# pass — the silent-degradation trap documented in
# docs/learnings/process/cloud-sink-execution-notes.md).
#
# Usage:
#   bash scripts/ingestion/launch_phase2_full_rebuild.sh
#
# Reads LOG path back to caller for cron arming + post-run inspection.
set -euo pipefail

cd "$(dirname "$0")/.."

START_UTC="$(date -u +%Y-%m-%dT%H:%M:%S)"
LOG="logs/phase2_full_rebuild_$(date -u -d "$START_UTC" +%Y%m%dT%H%M%SZ 2>/dev/null || date -u +%Y%m%dT%H%M%SZ).log"
WORKERS="${LIA_INGEST_CLASSIFIER_WORKERS:-4}"
TAXONOMY_AWARE="${LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE:-off}"

nohup bash -c "
  set +e
  export LIA_INGEST_CLASSIFIER_WORKERS=\"$WORKERS\"
  export LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE=\"$TAXONOMY_AWARE\"
  # Emit a launch marker into events.jsonl so the operator can confirm which
  # prompt mode the rebuild is actually using (verifies env propagation after
  # a 2026-04-25 incident where a detached nohup did not inherit the flag).
  printf '{\"ts_utc\": \"%s\", \"event_type\": \"phase2.rebuild.launch\", \"payload\": {\"workers\": \"%s\", \"taxonomy_aware_mode\": \"%s\"}}\n' \"\$(date -u +%%Y-%%m-%%dT%%H:%%M:%%S.%%N%%z | sed 's/\\([+-][0-9][0-9]\\)\\([0-9][0-9]\\)\\$/\\1:\\2/')\" \"$WORKERS\" \"$TAXONOMY_AWARE\" >> logs/events.jsonl
  make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production
  echo \"PHASE2_FULL_REBUILD_EXIT=\$?\" >> \"$LOG\"
  echo '' >> \"$LOG\"
  echo '=== POST-REBUILD AUDIT (scripts/diagnostics/audit_rebuild.py) ===' >> \"$LOG\"
  PYTHONPATH=src:. uv run python scripts/diagnostics/audit_rebuild.py \
    --log \"$LOG\" \
    --start-utc \"$START_UTC\" \
    --events-log logs/events.jsonl >> \"$LOG\" 2>&1
  audit_rc=\$?
  if [ \"\$audit_rc\" -eq 0 ]; then
    echo \"PHASE2_AUDIT_VERDICT=clean\" >> \"$LOG\"
  else
    echo \"PHASE2_AUDIT_VERDICT=degraded\" >> \"$LOG\"
  fi
" > "$LOG" 2>&1 < /dev/null &

BG_PID=$!
disown "$BG_PID" 2>/dev/null || true

echo "LOG=$LOG"
echo "BG_PID=$BG_PID"
echo "START_UTC=$START_UTC"
echo "LIA_INGEST_CLASSIFIER_WORKERS=$WORKERS"
echo "LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE=$TAXONOMY_AWARE"
sleep 3
ps -p "$BG_PID" -o pid,ppid,etime,stat,command 2>&1 | head -5 || echo "process not visible yet"
