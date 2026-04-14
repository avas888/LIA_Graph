.PHONY: reset-c eval-c-gold eval-c-full ralph-loop supabase-start supabase-stop supabase-reset supabase-status test-batched

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

# Run full test suite in batches to avoid OOM.
# Stall detection: if a batch takes >6× the median of previous batches,
# the runner kills it and re-runs each file individually to isolate the culprit.
BATCH_COUNT ?= 120
test-batched:
	PYTHONPATH=src:. uv run python scripts/run_tests_batched.py --batches $(BATCH_COUNT) --cov --fail-under 90
