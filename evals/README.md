# Evals

This directory contains evaluation datasets and lightweight runners for LIA_Graph.

Its job is not to preserve old-RAG design assumptions. Its job is to measure:
- whether graph ingestion is healthy
- whether graph retrieval is finding the right legal structure
- whether composition is grounded in the retrieved subgraph
- whether Pipeline D is good enough to roll out safely

## Evaluation Roles

- `pipeline_c_golden.jsonl`: historical baseline dataset for comparison only
- `graph_edges_canary_v1.jsonl`: graph-specific canary cases
- `rag_retrieval_benchmark.jsonl`: retrieval benchmark input set
- `normative_analysis_suite.jsonl`: deeper legal-analysis scenarios
- `quality_quickcheck_v1.jsonl`: fast smoke-style quality checks
- `run_retrieval_eval.py`: retrieval evaluation runner
- `run_eval_stub.py`: placeholder harness for future graph-specific runners

## Current Reading of These Files

Use the datasets in two modes:

1. Regression protection:
compare Pipeline D against the current baseline behavior so we can roll out safely.

2. Graph-first learning:
look for missing node types, weak edge taxonomy, broken concept vocab, poor traversal choices, and composition gaps.

The second mode is more important for design.

## Baseline vs Graph-Native Success

Matching the old baseline is not enough.

Good Pipeline D evals should tell us:
- whether the graph captured the right legal units
- whether multi-hop links are actually useful
- whether article-level grounding improved
- whether edge types help answer quality
- whether the system surfaces the right computation or amendment chains

## Recommended Near-Term Focus

- `graph_edges_canary_v1.jsonl`
- `pipeline_c_golden.jsonl`
- `rag_retrieval_benchmark.jsonl`
- `normative_analysis_suite.jsonl`

## Suggested Commands

```bash
cd /Users/ava-sensas/Developer/Lia_Graph
PYTHONPATH=src:. uv run python -m evals.run_retrieval_eval --dataset evals/rag_retrieval_benchmark.jsonl --index artifacts/document_index.jsonl
PYTHONPATH=src:. uv run python evals/run_eval_stub.py
```

Add graph-native runners here as Pipeline D becomes real. Prefer local scripts and local datasets in this repo over inherited pointers back into `Lia_contadores`.
