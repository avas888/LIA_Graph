# Step 01 — Debug `seed_article_keys = 0/30` in NEW mode

**Priority:** P0 · **Estimated effort:** 1 hour investigation + fix · **Blocks:** step 02 (retrieval-depth investigation)

## §1 What

Phase 1 of v6 (commit `7d966ce`) lifted nine retrieval-diagnostic fields to the top level of `response.diagnostics`. Eight are populating correctly. The ninth, `seed_article_keys`, reports empty in every row of the phase 6 panel (0/30), even though the retriever reports non-empty seed lists in internal logs.

## §2 Why

Three reasons this matters:

1. **Step 02 depends on it.** Retrieval-depth investigation needs to see *which* article keys were used as BFS seeds to separate "planner anchored nothing" from "planner anchored something but BFS found nothing". Without this field we can't trace.
2. **It's a phase-1 contract violation.** The lifted-keys invariant (`tests/test_orchestrator_diagnostic_surface.py`) says every lifted field is either present with a real value or explicitly `None`. Seeing 0/30 means one of: retriever doesn't emit it on the live path (bug), harness reads it from the wrong nesting level (regression of the original harness bug phase 1 was built to fix), or serialization drops it (JSONL writer edge case).
3. **Silent measurement gaps compound.** If one lifted field ghost-populates, others might follow. A regression test that catches this today is cheap; rebuilding trust in the diagnostic surface after three more silent regressions is expensive.

## §3 Hypothesis tree

Before writing code, rank the hypotheses and test each in order:

| # | Hypothesis | Test | Cost |
|---|---|---|---|
| H1 | **Retriever doesn't populate `seed_article_keys` in `falkor_live` mode.** The field is built at `src/lia_graph/pipeline_d/retriever_falkor.py:171` but maybe only on a specific code path. | Run `run_pipeline_d` against Q3 (known-healthy) in `falkor_live` mode, print `evidence.diagnostics.get("seed_article_keys")`. | 5 min |
| H2 | **Retriever populates it but orchestrator lift reads wrong key.** `orchestrator.py` lifts `seed_article_keys` from `(evidence.diagnostics or {}).get("seed_article_keys")`. Verify the key name matches. | `diff` orchestrator's lift block (line ~483) against retriever_falkor's emit block (line ~171). | 2 min |
| H3 | **Orchestrator lifts correctly but A/B harness reads wrong key.** Pre-v6 the harness read `primary_article_count` from top-level via `diag.get(...)` and got None because fields were nested. Phase 1 fixed that — but maybe only for the fields phase 1 specifically tested. | `grep "seed_article_keys" scripts/evaluations/run_ab_comparison.py` + trace its dict-path. | 2 min |
| H4 | **Harness reads correctly but JSONL serialization drops the field.** `seed_article_keys` is a `list[str]`; maybe an empty list is being serialized as `null` somewhere and the harness treats `null` as missing. | `head -1 artifacts/eval/ab_comparison_*.jsonl \| python3 -c "import json,sys; r=json.loads(sys.stdin.read()); print(r['new'].get('seed_article_keys', '<MISSING>'))"`. | 2 min |
| H5 | **All of the above are fine, but the retriever's seed list is genuinely empty on 30/30 rows.** Unlikely — would mean the planner never anchors any articles, which contradicts `primary_article_count >= 1` in 15/30 rows. | Run a healthy Q3 directly, check if seed_article_keys is empty or populated. | 5 min |

Most likely: **H1 or H5**. The orchestrator's lift code is straightforward and was verified working for the other eight fields. The retriever-falkor emission is the more-likely regression site.

## §4 Method

### Step A — repro the gap

```bash
set -a; source .env.staging; set +a
export LIA_TEMA_FIRST_RETRIEVAL=on
export LIA_GRAPH_MODE=falkor_live
export LIA_CORPUS_SOURCE=supabase

PYTHONPATH=src:. uv run python - <<'PY'
from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.orchestrator import run_pipeline_d

req = PipelineCRequest(
    message="¿Qué artículo regula el anticipo del impuesto de renta?",
    topic="declaracion_renta",
    requested_topic="declaracion_renta",
)
resp = run_pipeline_d(req)
d = dict(resp.diagnostics)

# Top-level lifted
print("top-level seed_article_keys:", d.get("seed_article_keys"))

# Nested in evidence_bundle.diagnostics
ev = (d.get("evidence_bundle") or {}).get("diagnostics") or {}
print("nested   seed_article_keys:", ev.get("seed_article_keys"))

# retrieval_health sibling
rh = d.get("retrieval_health") or {}
print("health   seed_article_keys:", rh.get("seed_article_keys"))
PY
```

Expected outcome: **at least one of the three reads is non-empty**. The one that's non-empty tells us where the field lives; the ones that are empty tell us which reader is broken.

### Step B — verify against the harness

Run the same query through the A/B harness with `--limit 1`:

```bash
PYTHONPATH=src:. uv run python scripts/evaluations/run_ab_comparison.py \
  --gold evals/gold_retrieval_v1.jsonl \
  --output-dir /tmp/seed_debug \
  --manifest-tag seed_debug \
  --target production --limit 3
python3 -c "import json; rows=[json.loads(l) for l in open('/tmp/seed_debug/ab_comparison_*.jsonl')]; [print(r['qid'], r['new'].get('seed_article_keys')) for r in rows]"
```

Compare what step A printed against what step B captured. Divergence tells us the harness is the break point.

### Step C — fix in the narrowest module

Based on where the break is (H1 vs H2 vs H3 vs H4), fix in the correspondingly narrow module. Do NOT fix in multiple places — one root cause, one fix.

## §5 Success criteria

1. **Step A script** prints a non-empty `seed_article_keys` at top-level for Q3.
2. **Step B jsonl** shows `seed_article_keys` non-empty on ≥ 2 of the 3 probed rows.
3. **Next full phase-6-class A/B run** produces `seed_article_keys` non-empty on ≥ 20/30 rows (target) OR ≥ every row that also has `primary_article_count >= 1` (stronger invariant).
4. **New regression test** in `tests/test_orchestrator_diagnostic_surface.py`: one test asserting that for a query with `primary_article_count >= 1`, `seed_article_keys` is a non-empty list. This is the regression-guard the original phase-1 tests forgot to pin.

## §6 Out of scope

- Fixing the mean `primary_article_count` (that's step 02).
- Adding new diagnostic fields.
- Changing the retriever's actual seed-selection logic (we're only fixing the wire contract, not the content).

## §7 Rollback

Pure read-only investigation + a surgical fix. Rollback = `git revert <sha>`. No cloud writes, no migrations, no corpus changes. Safe.
