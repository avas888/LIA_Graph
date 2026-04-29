#!/usr/bin/env bash
# next_v7 P4 — fire 4 concurrent embedding-backfill shards.
# Each shard processes ~1/4 of the rows whose chunk_text_embedding is
# NULL, deterministically partitioned by md5(chunk_id) % 4. Wins ~4×
# throughput over single-shard mode.
#
# Use AFTER killing any single-shard P4 process started by
# launch_post_p1.sh — running both at once would just race, the cursor
# advance is per-process so they wouldn't corrupt each other but they'd
# duplicate API calls.

set -uo pipefail
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
GEN="next_v7_p4_${TS}"

set -a
. "${ROOT}/.env.staging"
set +a
export LIA_SUPABASE_TARGET=production

mkdir -p logs
echo "Launching 4 shards (generation=${GEN})..."
for x in 0 1 2 3; do
  log="logs/p4_shard${x}_${TS}.log"
  nohup env PYTHONPATH=src:. uv run python scripts/ingestion/embedding_ops.py \
      --target production \
      --generation "${GEN}" \
      --batch-size 100 \
      --shard "${x}/4" \
      </dev/null > "${log}" 2>&1 &
  pid=$!
  disown ${pid} 2>/dev/null || true
  echo "  shard ${x}/4  PID=${pid}  log=${log}"
done
echo "All 4 shards launched. Monitor via:"
echo "  for x in 0 1 2 3; do tail -1 logs/p4_shard\${x}_${TS}.log; done"
