# TASK-03: Integration & Eval

> **Status**: NOT STARTED
> **Depends on**: TASK-02 complete (working Pipeline D)
> **Produces**: Comparative eval report, header-based routing

---

## Last Checkpoint

```
step: 0
description: Task not yet started
next_action: Wire header-based routing
artifacts_produced: none
```

---

## Steps

### Step 1: Header-Based Routing
- Modify `ui_server.py` to read `X-Lia-Pipeline` header
- Default: Pipeline C (existing behavior)
- `X-Lia-Pipeline: d` → inject `run_pipeline_d` into deps
- `X-Lia-Pipeline: dual` → run both, log both, serve Pipeline C response

### Step 2: Dual Eval Harness
- Adapt `eval_pipeline_c_gold.py` to run both pipelines against golden set
- Metrics per pipeline:
  - `answer_accuracy` (rubric-based)
  - `citation_correctness` (cited articles are relevant)
  - `citation_completeness` (no missing critical articles)
  - `response_time_ms`
  - `response_bubble_highlighted_ms` (critical KPI)
- Output: side-by-side comparison table

### Step 3: Run Comparative Eval
- Execute against `evals/pipeline_c_golden.jsonl`
- Document wins/losses per question
- Identify Pipeline D failure patterns (if any)
- Artifact: `artifacts/eval/pipeline_d_vs_c_comparison.json`

### Step 4: Quality Gap Analysis
- For each Pipeline D loss: root cause (missing edge? wrong traversal? composer issue?)
- Prioritized fix list
- Iterate: fix → re-eval → measure improvement

---

## Resumption Guide

If this task is interrupted:
1. Check `last_checkpoint.step` above
2. Eval runs are idempotent — safe to re-run
3. Comparison artifacts are cumulative — append new runs, don't overwrite
