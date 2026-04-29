#!/usr/bin/env bash
# next_v7 §3.1 P1 — comprehensive cloud promotion orchestrator.
# Loops through every non-empty veredicto batch dir under
# evals/vigencia_extraction_v1/, calling ingest_vigencia_veredictos.py
# against the production cloud target. Idempotent (UPSERT on norm_id +
# row exists check on (norm_id, idempotency_key) so re-runs are no-ops).
#
# Heartbeat lives in scripts/cloud_promotion/heartbeat.py; this script
# only writes:
#   * logs/cloud_promotion_<TS>/<batch>.log     (per-batch stdout/stderr)
#   * logs/cloud_promotion_<TS>/audit.jsonl     (combined audit log)
#   * logs/cloud_promotion_<TS>/state.json      (current batch + counts)
#   * logs/cloud_promotion_<TS>/cli.done        (sentinel on success)

set -uo pipefail
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"

TS="${PROMOTION_TS:-$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_ID="v6-cloud-promotion-${TS}"
RUN_DIR="${ROOT}/logs/cloud_promotion_${TS}"
AUDIT_LOG="${RUN_DIR}/audit.jsonl"
STATE_FILE="${RUN_DIR}/state.json"
DRIVER_LOG="${RUN_DIR}/driver.log"

mkdir -p "${RUN_DIR}"
echo "${TS}" > "${RUN_DIR}/started_at_utc"

log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "${DRIVER_LOG}"; }

# Activate cloud env.
set -a
. "${ROOT}/.env.staging"
set +a
export LIA_SUPABASE_TARGET=production

# Discover non-empty batch dirs (Bash 3.2 compatible — no mapfile).
BATCHES=()
while IFS= read -r name; do
  BATCHES+=("$name")
done < <(
  for d in "${ROOT}"/evals/vigencia_extraction_v1/*/; do
    name=$(basename "$d")
    [[ "$name" == _* ]] && continue
    n=$(find "$d" -maxdepth 1 -name '*.json' | wc -l | tr -d ' ')
    [[ "$n" -gt 0 ]] && echo "$name"
  done | sort
)

# --risk-first: reorder batches so high-novelty / historical-failure
# families run FIRST. With this, a fail-fast trip kills 5 minutes of
# work, not 25. High-risk = J* (CST), K* (CCo), F* (DIAN resoluciones),
# G* (DIAN conceptos) + B10 (sentencias). Default order keeps the
# alphabetical sweep (low-risk B10/C/D first, high-volume E* in the
# middle, J/K at the tail) — which is precisely the pattern we want
# to invert when we suspect new shapes.
RISK_FIRST="${RISK_FIRST:-0}"
if [[ "${RISK_FIRST}" == "1" ]]; then
  HIGH_RISK_PREFIXES=("B10" "J" "K" "F" "G")
  HIGH_RISK_BATCHES=()
  LOW_RISK_BATCHES=()
  for batch in "${BATCHES[@]}"; do
    is_high=0
    for prefix in "${HIGH_RISK_PREFIXES[@]}"; do
      if [[ "$batch" == "${prefix}"* ]]; then
        is_high=1
        break
      fi
    done
    if [[ ${is_high} -eq 1 ]]; then
      HIGH_RISK_BATCHES+=("$batch")
    else
      LOW_RISK_BATCHES+=("$batch")
    fi
  done
  BATCHES=("${HIGH_RISK_BATCHES[@]}" "${LOW_RISK_BATCHES[@]}")
fi

# --preflight: before the main loop, ingest 1 norm-with-veredicto per
# batch. Catches DB-side schema errors (CHECK constraints, missing
# tables) in minutes instead of after the volume batches run. Uses the
# SAME run_id as the main loop will use, so the writer's idempotency
# key matches and the main loop skips already-ingested rows. Counts
# preflight errors against fail-fast thresholds so a structural
# problem aborts before the cascade.
PREFLIGHT="${PREFLIGHT:-0}"

# Fail-fast thresholds. Override via env. Driver aborts BETWEEN batches when
# either threshold is exceeded — keeps the cascade from churning thousands
# of rows when something is structurally broken.
FAIL_FAST_MAX_ERRORS="${FAIL_FAST_MAX_ERRORS:-50}"          # absolute error count
FAIL_FAST_MIN_ROWS_FOR_RATE="${FAIL_FAST_MIN_ROWS_FOR_RATE:-100}"
FAIL_FAST_MAX_ERROR_RATE_PCT="${FAIL_FAST_MAX_ERROR_RATE_PCT:-10}"  # percent

TOTAL_BATCHES=${#BATCHES[@]}
log "ingest run_id=${RUN_ID} batches=${TOTAL_BATCHES}  fail_fast: max_errors=${FAIL_FAST_MAX_ERRORS} max_rate=${FAIL_FAST_MAX_ERROR_RATE_PCT}%@>=${FAIL_FAST_MIN_ROWS_FOR_RATE}rows  risk_first=${RISK_FIRST}  preflight=${PREFLIGHT}"
log "batch order: ${BATCHES[*]}"
printf '{"started_at_utc":"%s","run_id":"%s","total_batches":%d,"current_batch":null,"completed_batches":0}\n' \
  "${TS}" "${RUN_ID}" "${TOTAL_BATCHES}" > "${STATE_FILE}"

# ---------------------------------------------------------------------------
# PREFLIGHT (when --preflight / PREFLIGHT=1) — ingest one norm-with-veredicto
# from each batch BEFORE the volume cascade. Catches DB-side schema errors
# (CHECK constraint mismatches, missing tables, RLS failures) in minutes
# instead of after thousands of rows. Uses the SAME run_id as the main loop
# so the writer's idempotency_key matches and the main loop skips already-
# ingested rows.
# ---------------------------------------------------------------------------
if [[ "${PREFLIGHT}" == "1" ]]; then
  log "── preflight phase: 1 norm per batch (same run_id as main loop) ──"
  PREFLIGHT_DIR="${RUN_DIR}/_preflight"
  mkdir -p "${PREFLIGHT_DIR}"
  PREFLIGHT_AUDIT="${RUN_DIR}/preflight_audit.jsonl"
  : > "${PREFLIGHT_AUDIT}"
  PREFLIGHT_ERR=0
  for batch in "${BATCHES[@]}"; do
    # Pick the first JSON in the batch dir that has a non-null veredicto.
    SAMPLE=""
    while IFS= read -r p; do
      if PYTHONPATH=src:. uv run --quiet python -c "
import json, sys
d = json.loads(open('${p}').read())
v = (d.get('result') or {}).get('veredicto')
sys.exit(0 if v else 1)
" 2>/dev/null; then
        SAMPLE="$p"
        break
      fi
    done < <(find "${ROOT}/evals/vigencia_extraction_v1/${batch}" -maxdepth 1 -name '*.json' | sort | head -20)

    if [[ -z "${SAMPLE}" ]]; then
      log "  preflight ${batch}: no veredicto-bearing JSON in first 20 — skipping"
      continue
    fi

    # Materialize a single-norm input dir for the ingest script.
    SAMPLE_DIR="${PREFLIGHT_DIR}/${batch}"
    mkdir -p "${SAMPLE_DIR}"
    cp "${SAMPLE}" "${SAMPLE_DIR}/"

    PYTHONPATH=src:. uv run python scripts/canonicalizer/ingest_vigencia_veredictos.py \
      --target production \
      --run-id "${RUN_ID}-${batch}" \
      --extracted-by ingest@v1 \
      --input-dir "${SAMPLE_DIR}" \
      --audit-log "${PREFLIGHT_AUDIT}" \
      > "${PREFLIGHT_DIR}/${batch}.log" 2>&1
    rc=$?
    if [[ $rc -ne 0 ]]; then
      log "  preflight ${batch}: rc=${rc} — see ${PREFLIGHT_DIR}/${batch}.log"
      PREFLIGHT_ERR=$((PREFLIGHT_ERR + 1))
    fi
  done

  PRE_ROW_ERR=$(grep -c '"outcome": "error"' "${PREFLIGHT_AUDIT}" 2>/dev/null | tr -d '\n ' || echo 0)
  [[ -z "${PRE_ROW_ERR}" ]] && PRE_ROW_ERR=0
  log "preflight done: batch_rcs_failed=${PREFLIGHT_ERR} row_errors=${PRE_ROW_ERR}"
  if [[ "${PRE_ROW_ERR}" -gt 0 ]]; then
    log "PREFLIGHT FAIL — aborting cascade before volume batches. Categorize errors via:"
    log "  grep '\"outcome\": \"error\"' ${PREFLIGHT_AUDIT} | python3 -c 'import json,sys; from collections import Counter; print(Counter(json.loads(l)[\"reason\"][:200] for l in sys.stdin).most_common(10))'"
    touch "${RUN_DIR}/cli.failfast"
    exit 2
  fi
  log "preflight passed — proceeding to main cascade"
fi

ERRORS=0
COMPLETED=0
for batch in "${BATCHES[@]}"; do
  COMPLETED=$((COMPLETED + 1))
  BATCH_LOG="${RUN_DIR}/${batch}.log"
  log "── batch ${COMPLETED}/${TOTAL_BATCHES}: ${batch} ──"
  printf '{"started_at_utc":"%s","run_id":"%s","total_batches":%d,"current_batch":"%s","completed_batches":%d}\n' \
    "${TS}" "${RUN_ID}" "${TOTAL_BATCHES}" "${batch}" "$((COMPLETED - 1))" > "${STATE_FILE}"

  PYTHONPATH=src:. uv run python scripts/canonicalizer/ingest_vigencia_veredictos.py \
    --target production \
    --run-id "${RUN_ID}-${batch}" \
    --extracted-by ingest@v1 \
    --input-dir "evals/vigencia_extraction_v1/${batch}" \
    --audit-log "${AUDIT_LOG}" \
    > "${BATCH_LOG}" 2>&1
  rc=$?
  if [[ $rc -ne 0 ]]; then
    ERRORS=$((ERRORS + 1))
    log "WARN batch ${batch} exited rc=${rc} (row-level errors; see ${BATCH_LOG})"
  fi

  # Fail-fast check (between batches). Counts errors across the audit log.
  if [[ -f "${AUDIT_LOG}" ]]; then
    ROW_ERR=$(grep -c '"outcome": "error"' "${AUDIT_LOG}" 2>/dev/null | tr -d '\n ' || echo 0)
    [[ -z "${ROW_ERR}" ]] && ROW_ERR=0
    ROW_TOTAL=$(wc -l < "${AUDIT_LOG}" 2>/dev/null | tr -d '\n ' || echo 0)
    [[ -z "${ROW_TOTAL}" ]] && ROW_TOTAL=0
    if [[ "${ROW_ERR}" -gt "${FAIL_FAST_MAX_ERRORS}" ]]; then
      log "FAIL-FAST tripped: row errors ${ROW_ERR} > ${FAIL_FAST_MAX_ERRORS}. Aborting cascade."
      touch "${RUN_DIR}/cli.failfast"
      printf '{"started_at_utc":"%s","run_id":"%s","total_batches":%d,"current_batch":null,"completed_batches":%d,"errors":%d,"row_errors":%d,"row_total":%d,"fail_fast":"max_errors"}\n' \
        "${TS}" "${RUN_ID}" "${TOTAL_BATCHES}" "${COMPLETED}" "${ERRORS}" "${ROW_ERR}" "${ROW_TOTAL}" > "${STATE_FILE}"
      exit 2
    fi
    if [[ "${ROW_TOTAL}" -ge "${FAIL_FAST_MIN_ROWS_FOR_RATE}" ]]; then
      RATE=$(( ROW_ERR * 100 / ROW_TOTAL ))
      if [[ "${RATE}" -ge "${FAIL_FAST_MAX_ERROR_RATE_PCT}" ]]; then
        log "FAIL-FAST tripped: row error rate ${RATE}%% >= ${FAIL_FAST_MAX_ERROR_RATE_PCT}%% (errors=${ROW_ERR}, total=${ROW_TOTAL}). Aborting cascade."
        touch "${RUN_DIR}/cli.failfast"
        printf '{"started_at_utc":"%s","run_id":"%s","total_batches":%d,"current_batch":null,"completed_batches":%d,"errors":%d,"row_errors":%d,"row_total":%d,"fail_fast":"error_rate"}\n' \
          "${TS}" "${RUN_ID}" "${TOTAL_BATCHES}" "${COMPLETED}" "${ERRORS}" "${ROW_ERR}" "${ROW_TOTAL}" > "${STATE_FILE}"
        exit 2
      fi
    fi
  fi
done

printf '{"started_at_utc":"%s","run_id":"%s","total_batches":%d,"current_batch":null,"completed_batches":%d,"errors":%d}\n' \
  "${TS}" "${RUN_ID}" "${TOTAL_BATCHES}" "${COMPLETED}" "${ERRORS}" > "${STATE_FILE}"

if [[ $ERRORS -eq 0 ]]; then
  touch "${RUN_DIR}/cli.done"
  log "DONE all ${TOTAL_BATCHES} batches (0 errors)"
else
  touch "${RUN_DIR}/cli.partial"
  log "DONE with ${ERRORS} batch-level errors of ${TOTAL_BATCHES}"
fi
