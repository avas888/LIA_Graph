#!/usr/bin/env bash
# fire_suin_cloud.sh — the single production-push orchestrator for SUIN.
#
# Runs the seven-step sequence documented in
# docs/next/suin_harvestv1.md Phase 7:
#
#   1. Four sequential --include-suin calls under the same --supabase-generation-id
#      (one per scope: laboral-tributario, laboral, tributario, jurisprudencia).
#   2. Cumulative generation-row update (true documents/chunks counts from
#      the tables themselves — fixes the "last call wins" subtlety).
#   3. Cloud verification (scripts/ingestion/verify_suin_merge.py --target production).
#   4. Cloud embedding backfill (scripts/ingestion/embedding_ops.py --target production).
#   5. Null-embedding gate (SELECT count(*) WHERE embedding IS NULL → 0).
#   6. Activation flip (scripts/ingestion/supabase_flip_active_generation.py).
#   7. Post-activation regression (10-question suite). On failure, auto-roll
#      back the activation flip (re-activate the prior generation).
#
# Refuses to run without --confirm AND --activate. Any non-zero exit halts.

set -euo pipefail

DEFAULT_SCOPES="laboral-tributario,laboral,tributario,jurisprudencia"
DEFAULT_ARTIFACTS_DIR="artifacts/suin"
DEFAULT_REGRESSIONS_DIR="tests/fixtures/chat_regressions"

TARGET=""
GENERATION=""
SCOPES="$DEFAULT_SCOPES"
ACTIVATE="false"
CONFIRM="false"
ROLLBACK="false"
PREVIOUS_GENERATION=""
ARTIFACTS_DIR="$DEFAULT_ARTIFACTS_DIR"
REGRESSIONS_DIR="$DEFAULT_REGRESSIONS_DIR"

usage() {
  cat <<EOF >&2
usage: $0 --target {wip|production} --generation <id> --confirm --activate
          [--scopes csv] [--rollback --previous-generation <id>]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --generation) GENERATION="$2"; shift 2 ;;
    --scopes) SCOPES="$2"; shift 2 ;;
    --activate) ACTIVATE="true"; shift ;;
    --confirm) CONFIRM="true"; shift ;;
    --rollback) ROLLBACK="true"; shift ;;
    --previous-generation) PREVIOUS_GENERATION="$2"; shift 2 ;;
    --artifacts-dir) ARTIFACTS_DIR="$2"; shift 2 ;;
    --regressions-dir) REGRESSIONS_DIR="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown flag: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$TARGET" || -z "$GENERATION" ]]; then
  usage
  exit 2
fi

if [[ "$CONFIRM" != "true" ]]; then
  echo "refusing to run: --confirm is required for $TARGET push" >&2
  exit 1
fi

if [[ "$ROLLBACK" == "true" ]]; then
  if [[ -z "$PREVIOUS_GENERATION" ]]; then
    echo "--rollback requires --previous-generation" >&2
    exit 2
  fi
  echo ">> ROLLBACK path — reactivating $PREVIOUS_GENERATION on $TARGET"
  PYTHONPATH=src:. uv run python scripts/ingestion/supabase_flip_active_generation.py \
    --target "$TARGET" \
    --generation "$GENERATION" \
    --previous-generation "$PREVIOUS_GENERATION" \
    --rollback --confirm --json
  exit $?
fi

if [[ "$ACTIVATE" != "true" ]]; then
  echo "refusing to run: --activate is required on forward pushes" >&2
  exit 1
fi

IFS=',' read -ra SCOPE_ARRAY <<< "$SCOPES"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="$ARTIFACTS_DIR"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/_production_push_${TS}.log"
echo ">> logging to $LOG"

log() { echo "[$(date -u +%H:%M:%SZ)] $*" | tee -a "$LOG"; }

log "target=$TARGET generation=$GENERATION scopes=${SCOPE_ARRAY[*]}"

# Step 1: sequential scope merges under the same generation_id.
FIRST="true"
for scope in "${SCOPE_ARRAY[@]}"; do
  log ">> Step 1.$scope — merging into $GENERATION"
  if [[ "$FIRST" == "true" ]]; then
    # First call writes the generation row.
    PYTHONPATH=src:. uv run python -m lia_graph.ingest \
      --corpus-dir knowledge_base --artifacts-dir artifacts \
      --supabase-sink --supabase-target "$TARGET" \
      --execute-load --allow-unblessed-load --strict-falkordb \
      --include-suin "$scope" \
      --supabase-generation-id "$GENERATION" \
      --no-supabase-activate \
      --json 2>&1 | tee -a "$LOG"
    FIRST="false"
  else
    # Subsequent calls overwrite corpus_generations metadata with their own
    # per-scope counts. Step 2 repairs this after all scopes land.
    PYTHONPATH=src:. uv run python -m lia_graph.ingest \
      --corpus-dir knowledge_base --artifacts-dir artifacts \
      --supabase-sink --supabase-target "$TARGET" \
      --execute-load --allow-unblessed-load --strict-falkordb \
      --include-suin "$scope" \
      --supabase-generation-id "$GENERATION" \
      --no-supabase-activate \
      --json 2>&1 | tee -a "$LOG"
  fi
done

# Step 2: rewrite corpus_generations with true cumulative counts.
#
# PHASE 0 DECISION: we chose the "final-pass" approach over adding a
# --supabase-skip-generation-row-after-first flag to ingest.py. Simpler,
# keeps ingest.py's contract clean, and runs exactly once at the end.
log ">> Step 2 — rewriting cumulative counts on corpus_generations.$GENERATION"
PYTHONPATH=src:. uv run python - "$TARGET" "$GENERATION" <<'PY' 2>&1 | tee -a "$LOG"
import sys
from datetime import datetime, timezone
from lia_graph.supabase_client import create_supabase_client_for_target

target, generation = sys.argv[1], sys.argv[2]
client = create_supabase_client_for_target(target)

docs = client.table("documents").select("*", count="exact").eq(
    "sync_generation", generation
).limit(0).execute().count or 0
chunks = client.table("document_chunks").select("*", count="exact").eq(
    "sync_generation", generation
).limit(0).execute().count or 0

now = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
client.table("corpus_generations").update({
    "documents": docs,
    "chunks": chunks,
    "updated_at": now,
}).eq("generation_id", generation).execute()
print(f"corpus_generations.{generation}: documents={docs} chunks={chunks}")
PY

# Step 3: cloud verification.
log ">> Step 3 — verify_suin_merge"
SCOPE_DIR_ARGS=()
for scope in "${SCOPE_ARRAY[@]}"; do
  SCOPE_DIR_ARGS+=(--scope-dir "$ARTIFACTS_DIR/$scope")
done
PYTHONPATH=src:. uv run python scripts/ingestion/verify_suin_merge.py \
  --target "$TARGET" --generation "$GENERATION" \
  "${SCOPE_DIR_ARGS[@]}" --json 2>&1 | tee -a "$LOG"

# Step 4: cloud embedding backfill.
log ">> Step 4 — embedding_ops"
PYTHONPATH=src:. uv run python scripts/ingestion/embedding_ops.py \
  --target "$TARGET" --generation "$GENERATION" --json 2>&1 | tee -a "$LOG"

# Step 5: null-embedding gate (embedding_ops already exits non-zero if NULLs remain).
log ">> Step 5 — null-embedding gate cleared (embedding_ops ok)"

# Step 6: activation flip.
log ">> Step 6 — activation flip"
PREV_ACTIVE=$(PYTHONPATH=src:. uv run python - "$TARGET" <<'PY' 2>> "$LOG"
import sys
from lia_graph.supabase_client import create_supabase_client_for_target
client = create_supabase_client_for_target(sys.argv[1])
rows = client.table("corpus_generations").select("generation_id").eq("is_active", True).execute().data or []
print(rows[0]["generation_id"] if rows else "")
PY
)
log "   previous active: '${PREV_ACTIVE:-<none>}'"
PYTHONPATH=src:. uv run python scripts/ingestion/supabase_flip_active_generation.py \
  --target "$TARGET" --generation "$GENERATION" --confirm --json 2>&1 | tee -a "$LOG"

# Step 7: post-activation regression.
log ">> Step 7 — post-activation regression (${REGRESSIONS_DIR})"
if [[ ! -d "$REGRESSIONS_DIR" ]]; then
  log "   regressions dir missing — auto-rollback"
  if [[ -n "$PREV_ACTIVE" ]]; then
    PYTHONPATH=src:. uv run python scripts/ingestion/supabase_flip_active_generation.py \
      --target "$TARGET" --generation "$GENERATION" \
      --previous-generation "$PREV_ACTIVE" --rollback --confirm --json 2>&1 | tee -a "$LOG"
  fi
  exit 1
fi

set +e
PYTHONPATH=src:. uv run pytest -q "$REGRESSIONS_DIR" 2>&1 | tee -a "$LOG"
RC=$?
set -e

if [[ $RC -ne 0 ]]; then
  log "   regression FAILED rc=$RC — auto-rollback"
  if [[ -n "$PREV_ACTIVE" ]]; then
    PYTHONPATH=src:. uv run python scripts/ingestion/supabase_flip_active_generation.py \
      --target "$TARGET" --generation "$GENERATION" \
      --previous-generation "$PREV_ACTIVE" --rollback --confirm --json 2>&1 | tee -a "$LOG"
  else
    log "   WARNING: no previous active generation captured — manual intervention required"
  fi
  exit 1
fi

log ">> DONE — $GENERATION is active on $TARGET with regression green"
