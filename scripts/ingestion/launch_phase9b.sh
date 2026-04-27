#!/usr/bin/env bash
# Phase 9.B — embedding backfill launcher (detached).
#
# Fills `document_chunks.embedding` for every NULL-embedding row against
# production. In-process sync job (not the detached subprocess path the GUI
# uses) so this script's exit code reflects success/failure.
#
# Detached launch: nohup ignores SIGHUP, disown removes from job table,
# direct redirect (NO tee pipe) so closing any parent terminal cannot
# SIGPIPE the python child.
#
# Exit codes (from scripts/ingestion/embedding_ops.py):
#   0  NULL-embedding count reached 0
#   1  completed but nulls remain
#   2  job failed
set -euo pipefail

cd "$(dirname "$0")/.."

LOG="logs/embed-$(date -u +%Y%m%dT%H%M%SZ).log"

nohup bash -c '
  set -a
  source .env.staging
  set +a
  exec env PYTHONPATH=src:. uv run python scripts/ingestion/embedding_ops.py \
    --target production \
    --generation gen_20260422005449 \
    --json
' > "$LOG" 2>&1 < /dev/null &

BG_PID=$!
disown "$BG_PID" 2>/dev/null || true

echo "LOG=$LOG"
echo "BG_PID=$BG_PID"
sleep 3
ps -p "$BG_PID" -o pid,ppid,etime,stat,command 2>&1 | head -5 || echo "process not visible yet"
