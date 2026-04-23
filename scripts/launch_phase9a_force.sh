#!/usr/bin/env bash
# Phase 9.A additive reingest launcher — FORCE FULL CLASSIFY variant.
# Bypasses the fingerprint-based prematch shortcut so the full classifier
# + sink + Falkor write phases all run. Used to catch up state left in limbo
# by a prior crashed run.
#
# Detached: nohup ignores SIGHUP, disown removes from job table, redirects
# break the tee pipe fragility that killed earlier runs.
set -euo pipefail

cd "$(dirname "$0")/.."

LOG="logs/reingest-$(date -u +%Y%m%dT%H%M%SZ).log"

nohup bash -c '
  set -a
  source .env.staging
  set +a
  exec env PYTHONPATH=src:. uv run python -m lia_graph.ingest \
    --corpus-dir knowledge_base \
    --artifacts-dir artifacts \
    --additive \
    --supabase-sink \
    --supabase-target production \
    --supabase-generation-id gen_active_rolling \
    --execute-load \
    --allow-unblessed-load \
    --strict-falkordb \
    --allow-non-local-env \
    --force-full-classify \
    --json
' > "$LOG" 2>&1 < /dev/null &

BG_PID=$!
disown "$BG_PID" 2>/dev/null || true

echo "LOG=$LOG"
echo "BG_PID=$BG_PID"
sleep 3
ps -p "$BG_PID" -o pid,ppid,etime,stat,command 2>&1 | head -5 || echo "process not visible yet"
