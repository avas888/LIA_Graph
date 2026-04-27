#!/usr/bin/env bash
# launch_batch.sh — run ONE topic-backfill batch and detach.
#
# The morning 9.A reingest ran against the whole 1,280-doc corpus because
# `--force-full-classify` bypasses the fingerprint shortcut for every row.
# That's an expensive default for v3 backfills, where the goal is to
# re-classify one topic slice (~5-80 docs) at a time. This launcher
# composes the two steps that together achieve "batch N only":
#
#   1. scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py
#      nulls documents.doc_fingerprint for every doc whose tema is in the
#      batch's topic list. The additive ingestion path then sees exactly
#      those docs as "changed" and skips all others.
#
#   2. python -m lia_graph.ingest --additive ...
#      runs the standard additive reingest. Because every OTHER doc still
#      has a matching fingerprint, the planner classifies only the freshly
#      busted slice. No --force-full-classify needed.
#
# The difference vs launch_phase9a.sh is the scope: full-corpus vs one
# batch. Same detachment pattern (nohup + disown + direct redirect, no
# tee pipe) so the process survives CLI close.
#
# ── Durability contract (mirrors v3 §5 Phase 3) ──────────────────────
#
# Prior successful batches are written in stone. Only the failed-or-stopped
# batch has to be repeated. Three invariants make this hold:
#
# 1. **Topic-level cross-batch isolation**: fingerprint_bust filters by
#    `tema IN (this_batch_topics)` — it is STRUCTURALLY INCAPABLE of
#    touching another batch's docs. Prior batches' doc_fingerprints
#    remain freshly stamped by their own successful runs, so the additive
#    planner keeps seeing them as "unchanged" and never reclassifies them.
#
# 2. **Row-level idempotency**: every write layer is idempotent on its
#    natural key — documents on doc_id, document_chunks on chunk_id,
#    normative_edges on (source_key,target_key,relation,generation_id),
#    Falkor via MERGE. A mid-batch crash, a kill -9, and an orderly retry
#    all converge on the same final state.
#
# 3. **State-file checkpoint BEFORE destructive work**: this launcher
#    writes `artifacts/launch_batch_state_<N>.json` with
#    `status=in_flight` BEFORE the nohup fires. A retry sees the
#    in_flight marker, prints a loud warning, and proceeds (since the
#    reingest itself is idempotent, re-running is safe — the warning is
#    just so the operator knows they're covering for a crash, not
#    double-running).
#
# What to do when a batch fails:
#   1. Inspect logs/launch-batch-<N>-*.log and logs/events.jsonl.
#   2. If the crash is fixable in-code, patch + retest.
#   3. Re-run `bash scripts/ingestion/launch_batch.sh --batch <N>`. Prior batches
#      are untouched; only batch <N> re-processes.
#
# Usage:
#   bash scripts/ingestion/launch_batch.sh --batch 1                 # bust + run batch 1
#   bash scripts/ingestion/launch_batch.sh --batch 3 --dry-run       # plan only, no writes
#   bash scripts/ingestion/launch_batch.sh --topics laboral,iva      # ad-hoc multi-topic
#                                                          #   (skips plan.json lookup)
#
# Requires:
#   * .env.staging sourceable (production Supabase + Falkor creds)
#   * jq (optional — falls back to python -c for plan.json reads)
#   * artifacts/fingerprint_bust/plan.json (when using --batch)
#
# See docs/next/ingestionfix_v3.md §5 Phase 2 for the canonical flow and
# §5 Phase 3 for the full durability contract.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

PLAN_FILE="${PLAN_FILE:-artifacts/fingerprint_bust/plan.json}"
BATCH=""
TOPICS=""
DRY_RUN=""
TARGET="production"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --batch)
      BATCH="$2"; shift 2 ;;
    --topics)
      TOPICS="$2"; shift 2 ;;
    --dry-run)
      DRY_RUN="1"; shift ;;
    --target)
      TARGET="$2"; shift 2 ;;
    -h|--help)
      sed -n '1,30p' "$0"; exit 0 ;;
    *)
      echo "[launch_batch] unknown flag: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$BATCH" && -z "$TOPICS" ]]; then
  echo "[launch_batch] ERROR: pass --batch <N> or --topics a,b,c" >&2
  exit 1
fi

# --- Resolve the topic list for this batch ---------------------------
if [[ -n "$BATCH" && -z "$TOPICS" ]]; then
  if [[ ! -f "$PLAN_FILE" ]]; then
    echo "[launch_batch] ERROR: plan file not found at $PLAN_FILE" >&2
    exit 3
  fi
  if command -v jq >/dev/null 2>&1; then
    TOPICS="$(jq -r \
      --argjson batch "$BATCH" \
      '.batches[] | select(.batch == $batch) | .topics | join(",")' \
      "$PLAN_FILE")"
  else
    TOPICS="$(python3 -c "
import json, sys
p = json.load(open('$PLAN_FILE'))
for b in p['batches']:
    if b['batch'] == $BATCH:
        print(','.join(b['topics'])); break
")"
  fi
  if [[ -z "$TOPICS" ]]; then
    echo "[launch_batch] ERROR: batch $BATCH not found in $PLAN_FILE" >&2
    exit 3
  fi
fi

# Count topics for the --force-multi decision.
TOPIC_COUNT="$(awk -F, '{print NF}' <<< "$TOPICS")"
FORCE_MULTI_FLAG=""
if [[ "$TOPIC_COUNT" -gt 1 ]]; then
  FORCE_MULTI_FLAG="--force-multi"
fi

DRY_FLAG=""
CONFIRM_FLAG="--confirm"
if [[ -n "$DRY_RUN" ]]; then
  DRY_FLAG="--dry-run"
  CONFIRM_FLAG=""
fi

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="logs/launch-batch-${BATCH:-custom}-${TS}.log"
STATE_FILE="artifacts/launch_batch_state_${BATCH:-custom}.json"

# --- Retry detection --------------------------------------------------
# Durability contract, invariant #3: a pre-existing in_flight marker
# means a prior launch didn't finish cleanly. The retry is STILL SAFE
# because fingerprint_bust + the additive planner are both idempotent;
# we just want the operator to see the warning so they know they're
# covering for a crash, not accidentally double-running.
if [[ -n "$BATCH" && -f "$STATE_FILE" && -z "$DRY_RUN" ]]; then
  PRIOR_STATUS="$(python3 -c "
import json, sys
try:
    print(json.load(open('$STATE_FILE')).get('status', 'unknown'))
except Exception:
    print('unreadable')
")"
  case "$PRIOR_STATUS" in
    in_flight|launched)
      echo "[launch_batch] ⚠ retry detected — $STATE_FILE shows status=$PRIOR_STATUS" >&2
      echo "[launch_batch]   this usually means a prior launch crashed mid-ingest." >&2
      echo "[launch_batch]   proceeding (fingerprint_bust + additive planner are" >&2
      echo "[launch_batch]   idempotent; prior batches are untouched by design)." >&2
      ;;
    completed)
      echo "[launch_batch] ⚠ batch $BATCH already marked completed in $STATE_FILE" >&2
      echo "[launch_batch]   re-running will re-null the fingerprints and re-sink." >&2
      echo "[launch_batch]   this is safe (idempotent) but usually not what you want." >&2
      ;;
  esac
fi

echo "[launch_batch] target=$TARGET batch=${BATCH:-custom} topics=[$TOPICS] dry_run=${DRY_RUN:-0}"
echo "[launch_batch] log=$LOG"
echo "[launch_batch] state=$STATE_FILE"

write_state() {
  local status="$1"
  local extra="${2:-}"
  mkdir -p "$(dirname "$STATE_FILE")"
  python3 -c "
import json, os, sys, datetime as _dt
payload = {
    'batch': ${BATCH:-null} if '${BATCH:-}' else None,
    'topics': '$TOPICS'.split(','),
    'status': '$status',
    'target': '$TARGET',
    'log_path': '$LOG',
    'updated_at_utc': _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
}
extra_raw = '''${extra}'''
if extra_raw:
    try:
        payload.update(json.loads(extra_raw))
    except Exception:
        payload['extra'] = extra_raw
tmp = '$STATE_FILE' + '.tmp'
with open(tmp, 'w') as f:
    json.dump(payload, f, indent=2)
os.replace(tmp, '$STATE_FILE')  # atomic
"
}

# --- Step 1: fingerprint bust (inline, so we see errors immediately) --
# State: in_flight BEFORE any destructive work. Atomic temp+rename so a
# kill mid-write cannot leave a corrupt state file.
if [[ -n "$BATCH" && -z "$DRY_RUN" ]]; then
  write_state "in_flight"
fi

set -a; source .env.staging; set +a
PYTHONPATH=src:. uv run python scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py \
  --topics "$TOPICS" \
  --target "$TARGET" \
  $CONFIRM_FLAG \
  $DRY_FLAG \
  $FORCE_MULTI_FLAG \
  --tag "batch_${BATCH:-custom}"

if [[ -n "$DRY_RUN" ]]; then
  echo "[launch_batch] dry-run complete; skipping detached ingest launch."
  exit 0
fi

# --- Step 2: detached additive reingest ------------------------------
# No --force-full-classify: the fingerprint bust above is the only thing
# that makes the planner see any docs as changed, so the classifier pass
# naturally scopes to just the batch's slice.
nohup bash -c '
  set -a
  source .env.staging
  set +a
  exec env PYTHONPATH=src:. uv run python -m lia_graph.ingest \
    --corpus-dir knowledge_base \
    --artifacts-dir artifacts \
    --additive \
    --supabase-sink \
    --supabase-target '"$TARGET"' \
    --supabase-generation-id gen_active_rolling \
    --execute-load \
    --allow-unblessed-load \
    --strict-falkordb \
    --allow-non-local-env \
    --json
' > "$LOG" 2>&1 < /dev/null &

BG_PID=$!
disown "$BG_PID" 2>/dev/null || true

# Update state: launched (ingest process detached; fingerprint bust already
# written). Operator / validator will flip this to `completed` or `failed`
# after cli.done / run.failed.
if [[ -n "$BATCH" ]]; then
  write_state "launched" "{\"pid\": \"$BG_PID\"}"
fi

echo "LOG=$LOG"
echo "BG_PID=$BG_PID"
sleep 3
ps -p "$BG_PID" -o pid,ppid,etime,stat,command 2>&1 | head -5 \
  || echo "[launch_batch] process not visible yet"

echo ""
echo "[launch_batch] durability: prior batches untouched (topic-filter"
echo "  isolation + row-level idempotency). See script header for the"
echo "  full contract."
echo ""
echo "[launch_batch] next:"
echo "  1. wait for ingest.delta.run.start in logs/events.jsonl"
echo "  2. arm heartbeat cron with --chain-state-file if running the chain"
echo "  3. once cli.done fires, validate with:"
echo "     python scripts/monitoring/monitor_ingest_topic_batches/validate_batch.py \\"
echo "       --batch ${BATCH:-N} --gate --manifest <latest manifest>"
echo "  4. after validator passes, mark state: completed"
echo "     python -c \"import json; p='$STATE_FILE'; d=json.load(open(p)); d['status']='completed'; open(p,'w').write(json.dumps(d, indent=2))\""
