.PHONY: reset-c eval-c-gold eval-c-full ralph-loop supabase-start supabase-stop supabase-reset supabase-status smoke-deps test-batched phase2-graph-artifacts phase2-graph-artifacts-supabase

PHASE2_CORPUS_DIR ?= knowledge_base
PHASE2_ARTIFACTS_DIR ?= artifacts

reset-c:
	./scripts/reset_pipeline_c_state.sh

eval-c-gold:
	PYTHONPATH=src:. uv run python scripts/eval_pipeline_c_gold.py --threshold 90

eval-c-full:
	PYTHONPATH=src:. LIA_BATCHED_RUNNER=1 uv run pytest -q
	PYTHONPATH=src:. uv run python -m evals.run_retrieval_eval --dataset evals/rag_retrieval_benchmark.jsonl --index artifacts/document_index.jsonl --profile hybrid_rerank
	PYTHONPATH=src:. uv run python scripts/eval_pipeline_c_gold.py --threshold 90

ralph-loop:
	PYTHONPATH=src:. uv run python scripts/ralph_loop_pipeline_c.py --target 85 --max-iterations 8 --case-id C_GOLD_001

supabase-start:
	supabase start

supabase-stop:
	supabase stop

supabase-reset:
	supabase db reset

supabase-status:
	supabase status

smoke-deps:
	PYTHONPATH=src:. uv run python -m lia_graph.dependency_smoke

# Run full test suite in batches to avoid OOM.
# Stall detection: if a batch takes >6× the median of previous batches,
# the runner kills it and re-runs each file individually to isolate the culprit.
BATCH_COUNT ?= 120
test-batched:
	PYTHONPATH=src:. uv run python scripts/run_tests_batched.py --batches $(BATCH_COUNT) --cov --fail-under 90

phase2-graph-artifacts:
	PYTHONPATH=src:. uv run python -m lia_graph.ingest --corpus-dir $(PHASE2_CORPUS_DIR) --artifacts-dir $(PHASE2_ARTIFACTS_DIR) --json

# Same artifact build, plus the Supabase corpus sink. Required before
# dev:staging can serve answers off cloud Supabase (Phase B runtime cutover).
PHASE2_SUPABASE_TARGET ?= production
phase2-graph-artifacts-supabase:
	PYTHONPATH=src:. uv run python -m lia_graph.ingest --corpus-dir $(PHASE2_CORPUS_DIR) --artifacts-dir $(PHASE2_ARTIFACTS_DIR) --supabase-sink --supabase-target $(PHASE2_SUPABASE_TARGET) --json
