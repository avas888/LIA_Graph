#!/usr/bin/env bash
# next_v7 post-P1 launcher — fires P5 (Falkor sync), P4 (embedding
# backfill), and P6 (refusal rerun) in the right order/parallelism
# once P1 (cloud promotion) lands its cli.done sentinel.
#
# Run this AFTER P1 cli.done is observed:
#   bash scripts/cloud_promotion/launch_post_p1.sh
#
# Sequencing:
#   1. P5 (Falkor sync, single-writer) — synchronous, ~5 min.
#   2. P4 (embedding backfill, cloud DB writes) — detached, 1-2 hr.
#   3. P6 (refusal rerun, LLM API + local JSONs) — detached, ~3 hr.
#      P4 and P6 write to different surfaces (cloud DB vs local
#      JSON+LLM API) so they parallelize cleanly.

set -uo pipefail
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

POST_DIR="${ROOT}/logs/post_p1_${TS}"
mkdir -p "${POST_DIR}"

set -a
. "${ROOT}/.env.staging"
set +a
export LIA_SUPABASE_TARGET=production
export LIA_FALKOR_TARGET=production

log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "${POST_DIR}/launch.log"; }

# ---------------------------------------------------------------
# Step 1 — P5 Falkor sync (single-writer, synchronous)
# ---------------------------------------------------------------
log "P5 — sync_vigencia_to_falkor.py --target production (foreground)"
PYTHONPATH=src:. uv run python scripts/canonicalizer/sync_vigencia_to_falkor.py \
    --target production \
    > "${POST_DIR}/p5_falkor_sync.log" 2>&1
P5_RC=$?
if [[ ${P5_RC} -ne 0 ]]; then
  log "P5 failed (rc=${P5_RC}) — see p5_falkor_sync.log. Halting before launching P4/P6."
  exit ${P5_RC}
fi
log "P5 ok"

# ---------------------------------------------------------------
# Step 2 — P4 embedding backfill (detached, ~1-2 hr)
# ---------------------------------------------------------------
log "P4 — embedding backfill (detached) → ${POST_DIR}/p4_embedding_backfill.log"
nohup env PYTHONPATH=src:. uv run python scripts/ingestion/embedding_ops.py \
    --target production \
    --generation "next_v7_p1_${TS}" \
    --batch-size 100 \
    </dev/null > "${POST_DIR}/p4_embedding_backfill.log" 2>&1 &
P4_PID=$!
echo "${P4_PID}" > "${POST_DIR}/p4.pid"
disown ${P4_PID} 2>/dev/null || true
log "P4 launched PID=${P4_PID}"

# ---------------------------------------------------------------
# Step 3 — P6 refusal rerun (detached, ~3 hr)
# ---------------------------------------------------------------
log "P6 — cascade rerun --rerun-only-refusals --max-source-chars 32000 (detached)"
EXTRA_EXTRACT_FLAGS="--rerun-only-refusals --max-source-chars 32000" \
LIA_EXTRACT_WORKERS=8 \
LLM_DEEPSEEK_RPM=240 \
LIA_LIVE_SCRAPER_TESTS=1 \
nohup bash scripts/canonicalizer/run_cascade_v5.sh \
    </dev/null > "${POST_DIR}/p6_cascade_v6_2.log" 2>&1 &
P6_PID=$!
echo "${P6_PID}" > "${POST_DIR}/p6.pid"
disown ${P6_PID} 2>/dev/null || true
log "P6 launched PID=${P6_PID}"

log "All launched. P4 + P6 running concurrently in background. Monitor heartbeats independently."
log "P4 log: ${POST_DIR}/p4_embedding_backfill.log"
log "P6 log: ${POST_DIR}/p6_cascade_v6_2.log"
echo "${POST_DIR}" > "${ROOT}/logs/post_p1_latest_dir"
