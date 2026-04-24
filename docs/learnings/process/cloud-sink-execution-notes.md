# Cloud-sink execution: env posture, degradation, recovery

**Source:** `docs/next/ingestion_tunningv2.md` §16 Appendix D §§2, 6; v6 execution 2026-04-24.

## Launching the cloud sink (the right way)

The `phase2-graph-artifacts-supabase` Make target writes to **production Supabase** and **cloud FalkorDB**. Two gotchas:

### 1. `.env.staging` is NOT auto-loaded by `uv run`

The cloud credentials (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `FALKORDB_URL`, `LIA_FALKORDB_*`) live in `.env.staging` — a file `uv run` does not source by default. The posture guard (`src/lia_graph/env_posture.py`) will abort the run:

```
env_posture: Local-env posture guard failed:
  SUPABASE_URL is not set; FALKORDB_URL is not set.
  Fix the .env file, or pass --allow-non-local-env to bypass.
```

### 2. The posture guard itself is deliberate safety

Even with the env vars loaded, the guard requires an **explicit opt-in** for cloud writes — `--allow-non-local-env`. Don't work around this quietly; if you're bypassing it, you're doing a cloud write.

### The idiomatic invocation

```bash
LOGFILE="logs/phase2_cloud_sink_$(date +%Y%m%dT%H%M%SZ).log"
nohup bash -c "set -a; source .env.staging; set +a; \
  PYTHONPATH=src:. uv run python -m lia_graph.ingest \
  --corpus-dir knowledge_base --artifacts-dir artifacts \
  --supabase-sink --supabase-target production --execute-load \
  --allow-unblessed-load --strict-falkordb --allow-non-local-env \
  --json > $LOGFILE 2>&1; echo 'PHASE2_SINK_EXIT='\$? >> $LOGFILE" \
  > /dev/null 2>&1 &
disown
```

Key elements:
- **`set -a; source .env.staging; set +a`** — exports each var automatically without listing them one by one.
- **`--allow-non-local-env`** — explicit bypass of the posture guard. Only use this for intentional cloud writes.
- **Detached + heartbeat** per the long-running-process pattern in `CLAUDE.md`.

A follow-up item in `docs/next/ingestion_tunningv2.md` §16 Appendix D §9: add the `source .env.staging` prefix to the Make target, guarded by `ifeq ($(PHASE2_SUPABASE_TARGET),production)`, so the idiomatic invocation becomes `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production`.

## "failed=0" under LLM backpressure — the silent-degradation trap

The classifier's inner `try/except` in `src/lia_graph/ingestion_classifier.py:_run_n2_cascade` catches Gemini 429s and returns a **degraded verdict** with `requires_subtopic_review=True` and no N2 override. From the pool's perspective, the call returned successfully — no exception, no slot marked as `_ClassifierError`. So `failed=0` at the pool boundary.

**This hides real degradation.** In the v6 cloud sink re-pass we saw 92 tracebacks in stderr all corresponding to 429s. None surfaced as pool failures. Result: ~7 % of docs landed with N1-only verdicts instead of N2-refined subtopic bindings.

### Audit for silent degradation

Post-run, **before trusting the result as FANTASTIC**:

```bash
# count requires_subtopic_review=True docs
PYTHONPATH=src:. uv run python -c "
import json
reviews = 0; total = 0
for line in open('artifacts/corpus_audit_report.json').readlines():
    pass  # audit report is a dict; inspect it properly
"

# simpler: grep events.jsonl
grep -c '"requires_subtopic_review": true' logs/events.jsonl
```

If the count is > ~5 % of total classified docs, you hit TPM pressure. Either:
- Accept the degradation (N1 verdict is still better than `--skip-llm`).
- Re-run with `--classifier-workers 4` (halves the per-worker token pressure; finishes in ~15 min).
- Ship the TPM-aware token-budget limiter before the next run (follow-up §9 in v6 Appendix D).

### What 429s look like in the logs

```
ingestion_classifier: adapter.generate fallo
Traceback (most recent call last):
  File ".../gemini_runtime.py", line 52, in _request
    raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc
RuntimeError: Gemini HTTP 429: {"error": {"code": 429,
  "status": "RESOURCE_EXHAUSTED",
  "message": "Quota exceeded for metric:
   generativelanguage.googleapis.com/generate_content_paid_tier_input_token_count,
   limit: 1000000, model: gemini-2.5-flash",
  "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo",
              "retryDelay": "53s"}]}}
```

Three-part signal: HTTP 429, metric `input_token_count`, `RESOURCE_EXHAUSTED`. The retry delay is advisory; the classifier's jitter-retry typically lands on a later slot.

## Post-sink verification

After the sink succeeds:

```bash
# graph load report
cat artifacts/graph_load_report.json | python3 -m json.tool | head -40

# Supabase row counts (via dashboard or psql)
psql -c "SELECT count(*) FROM documents"          # expect +3,400 vs pre
psql -c "SELECT count(*) FROM chunks"             # expect +15,000 chunks

# Falkor counts (via Cypher)
# Expected: ArticleNode ≥ 12,500, TEMA ≥ 2,700, HAS_SUBTOPIC ≥ 450
```

Explicit gates from `docs/next/ingestion_tunningv2.md` §4.7.

## Rollback

**Cloud rollback is expensive.** The Supabase sink is additive (upsert semantics). To roll back:
- (a) Drop the new `documents.doc_id` rows by manifest diff, OR
- (b) Promote a previously frozen `gen_<UTC>` snapshot via `promote_generation` RPC.

Do NOT improvise a cloud rollback. If you must roll back, open a new task and surface to operator.

## See also

- `docs/next/ingestion_tunningv2.md` §4 (phase 2 full rebuild).
- `src/lia_graph/env_posture.py` — the guard.
- `docs/guide/env_guide.md` — canonical env-file docs.
