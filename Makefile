.PHONY: reset-c eval-c-gold eval-c-full ralph-loop supabase-start supabase-stop supabase-reset supabase-status smoke-deps test-batched phase2-graph-artifacts phase2-graph-artifacts-supabase phase2-suin-harvest-et phase2-suin-harvest-tax-laws phase2-suin-harvest-jurisprudence phase2-suin-harvest-full

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
#
# --execute-load + --allow-unblessed-load + --strict-falkordb are critical:
# without them the Falkor half of the cutover is never written. See
# `docs/next/ingestion_suin.md` health-check Gap #3.
#
# INGEST_SUIN, when set, passes --include-suin <scope> so SUIN JSONL artifacts
# at `artifacts/suin/<scope>/` merge into the same ingest run.
PHASE2_SUPABASE_TARGET ?= production
INGEST_SUIN ?=
PHASE2_SUPABASE_SINK_FLAGS = --supabase-sink --supabase-target $(PHASE2_SUPABASE_TARGET) --execute-load --allow-unblessed-load --strict-falkordb
PHASE2_SUIN_FLAG = $(if $(INGEST_SUIN),--include-suin $(INGEST_SUIN),)
phase2-graph-artifacts-supabase:
	PYTHONPATH=src:. uv run python -m lia_graph.ingest --corpus-dir $(PHASE2_CORPUS_DIR) --artifacts-dir $(PHASE2_ARTIFACTS_DIR) $(PHASE2_SUPABASE_SINK_FLAGS) $(PHASE2_SUIN_FLAG) --json

# ---- SUIN harvest targets (Phase A) ----------------------------------------
# These walk SUIN sitemaps and materialize artifacts/suin/<scope>/*.jsonl.
# The harvest is cache-keyed by URL (cache/suin/, gitignored) so re-runs are cheap.
SUIN_ARTIFACTS_DIR ?= artifacts/suin
SUIN_RPS ?= 1.0

phase2-suin-harvest-et:
	PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest --scope et --out $(SUIN_ARTIFACTS_DIR)/et --rps $(SUIN_RPS) --json

phase2-suin-harvest-tax-laws:
	PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest --scope tax-laws --out $(SUIN_ARTIFACTS_DIR)/tax-laws --rps $(SUIN_RPS) --json

phase2-suin-harvest-jurisprudence:
	PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest --scope jurisprudence --out $(SUIN_ARTIFACTS_DIR)/jurisprudence --rps $(SUIN_RPS) --json

phase2-suin-harvest-full:
	PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest --scope full --out $(SUIN_ARTIFACTS_DIR)/full --rps $(SUIN_RPS) --json
