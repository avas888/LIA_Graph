# Measurement error vs feature break

**Source:** `docs/next/ingestion_tunningv1.md` §0 I5 findings; commit `7d966ce` (v6 phase 1).

## The mistake the v5 panel made

The v5 30Q A/B expert panel reported that "all 60 result blocks returned `primary_article_count: 0`, `tema_first_mode: None`, and empty `seed_article_keys`" — and concluded that "the new code path never actually executed." That conclusion seeded a week of wrong diagnosis and delayed the real fixes.

**What actually happened:** the A/B harness (`scripts/evaluations/run_ab_comparison.py:162-174`) reads these fields from the **top level** of `response.diagnostics` via `diag.get(...)`. But pre-v6, those fields lived **nested inside** `diagnostics["evidence_bundle"]["diagnostics"]` (or at `diagnostics["retrieval_health"]["primary_article_count"]`). Every read returned `None`. The harness fell back to `0` for the counts.

Retrieval was actually returning useful articles the whole time. Nobody could tell from the panel data.

## The lesson

**Before drawing conclusions from a metric, verify the metric reads the field it thinks it reads.** In Python: print the full `diagnostics` dict for one row and cross-check. In SQL: `SELECT * FROM row LIMIT 1` and read every column, don't trust the query's projection list.

## The fix

Phase 1 (v6) lifted **nine retrieval diagnostics** to the top level of `response.diagnostics`:

```python
# src/lia_graph/pipeline_d/orchestrator.py (post-phase-1)
diagnostics = {
    ...
    "primary_article_count": (evidence.diagnostics or {}).get("primary_article_count")
        if (evidence.diagnostics or {}).get("primary_article_count") is not None
        else len(evidence.primary_articles),
    "connected_article_count": ...,
    "related_reform_count": ...,
    "seed_article_keys": ...,
    "planner_query_mode": ...,  # falls back to plan.query_mode
    "tema_first_mode": ...,
    "tema_first_topic_key": ...,
    "tema_first_anchor_count": ...,
    "retrieval_sub_topic_intent": ...,
    "subtopic_anchor_keys": ...,
}
```

Count-style fields fall back to `len(evidence.*)` so artifact-mode runs (which don't populate the retriever-diag keys) still report real ints instead of `None`. Pinned by `tests/test_orchestrator_diagnostic_surface.py` (3 tests).

## Anti-pattern

"The harness reports 0 — retrieval must be broken." Before acting on that: run one query through `run_pipeline_d` directly, print the full response, and confirm the numbers the harness reports match the actual response. If they diverge, the harness has a diagnostic-reading bug; if they agree, retrieval has a real problem.

## Contract for future diagnostics

Any new retrieval-diagnostic field added to `evidence.diagnostics` by a retriever (`retriever.py`, `retriever_supabase.py`, `retriever_falkor.py`) must **also** be lifted to the top level of `response.diagnostics` in `orchestrator.py`, and a matching entry added to `_LIFTED_KEYS` in `tests/test_orchestrator_diagnostic_surface.py`. The test will fail on a new retriever field that isn't lifted — that's the guardrail.

## See also

- `docs/next/ingestion_tunningv1.md` §0 I5 findings — the investigation that traced this.
- `scripts/evaluations/run_ab_comparison.py:162-174` — the harness read site.
- `src/lia_graph/pipeline_d/orchestrator.py` lifted-keys block.
