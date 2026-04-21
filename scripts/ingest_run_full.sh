#!/usr/bin/env bash
# Full ingest chain: make phase2-graph-artifacts-supabase → embeddings → optional Promoción.
#
# Invoked by ``ui_ingest_run_controllers._spawn_ingest_subprocess`` when
# `INGEST_AUTO_EMBED` or `INGEST_AUTO_PROMOTE` env vars are truthy. Preserves
# the single-source orchestration rule: each step delegates to its canonical
# entry point (`make`, `scripts/embedding_ops.py`) so there is no duplicated
# pipeline knowledge.
#
# Env contract (all optional; sensible defaults):
#   PHASE2_SUPABASE_TARGET   wip | production   (required; no default)
#   INGEST_SUIN              scope name or empty
#   INGEST_AUTO_EMBED        "1" to run embeddings after sink (default: 0)
#   INGEST_AUTO_PROMOTE      "1" to also run against production after WIP (default: 0)
#   LIA_INGEST_JOB_ID        opaque job id forwarded to ingest.py for trace tagging
#
# Exit codes:
#   0 — every enabled step succeeded
#   non-zero — propagated from the failing step

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

ts() { date -u +'%Y-%m-%dT%H:%M:%SZ'; }
log() { printf '[%s] %s\n' "$(ts)" "$*"; }

target="${PHASE2_SUPABASE_TARGET:-}"
if [[ -z "$target" ]]; then
  echo "ingest_run_full.sh: PHASE2_SUPABASE_TARGET is required (wip|production)" >&2
  exit 64
fi
if [[ "$target" != "wip" && "$target" != "production" ]]; then
  echo "ingest_run_full.sh: PHASE2_SUPABASE_TARGET must be wip or production, got: $target" >&2
  exit 64
fi

suin_scope="${INGEST_SUIN:-}"
auto_embed="${INGEST_AUTO_EMBED:-0}"
auto_promote="${INGEST_AUTO_PROMOTE:-0}"

log ">> Step 1 — make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=$target INGEST_SUIN=$suin_scope"
make phase2-graph-artifacts-supabase \
  PHASE2_SUPABASE_TARGET="$target" \
  INGEST_SUIN="$suin_scope"

if [[ "$auto_embed" == "1" ]]; then
  log ">> Step 2 — scripts/embedding_ops.py --target $target"
  # --generation is discovered from the most recent corpus_generations row by
  # the CLI; passing the explicit flag is optional. We keep the call minimal
  # to avoid divergence from fire_suin_cloud.sh's known-good shape.
  PYTHONPATH=src:. uv run python scripts/embedding_ops.py \
    --target "$target" --json
else
  log ">> Step 2 — embeddings skipped (INGEST_AUTO_EMBED=0)"
fi

if [[ "$auto_promote" == "1" && "$target" == "wip" ]]; then
  log ">> Step 3 — make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production"
  make phase2-graph-artifacts-supabase \
    PHASE2_SUPABASE_TARGET=production \
    INGEST_SUIN="$suin_scope"
  if [[ "$auto_embed" == "1" ]]; then
    log ">> Step 4 — embeddings on production"
    PYTHONPATH=src:. uv run python scripts/embedding_ops.py \
      --target production --json
  fi
else
  log ">> Step 3 — promotion skipped (INGEST_AUTO_PROMOTE=$auto_promote, target=$target)"
fi

log "ingest_run_full.sh: done"
