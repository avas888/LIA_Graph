.PHONY: reset-c eval-c-gold eval-c-full ralph-loop supabase-start supabase-stop supabase-reset supabase-status smoke-deps test-batched phase2-graph-artifacts phase2-graph-artifacts-supabase phase2-graph-artifacts-smoke phase2-suin-harvest-et phase2-suin-harvest-tributario phase2-suin-harvest-laboral phase2-suin-harvest-laboral-tributario phase2-suin-harvest-jurisprudencia phase2-suin-harvest-full phase2-regrandfather-corpus phase2-collect-subtopic-candidates phase3-mine-subtopic-candidates phase2-promote-subtopic-taxonomy phase2-backfill-subtopic phase2-sync-subtopic-taxonomy debug-query

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

# Preflight canary for the single-pass ingest. Runs against the committed
# mini_corpus fixture (3 docs) and asserts the subtopic invariant
# ((topic_key, subtopic_key) in taxonomy) on every classified doc + that
# Falkor emitted at least one SubTopicNode + HAS_SUBTOPIC edge. ~30 seconds,
# ~$0.01 in LLM cost. Run this BEFORE a full-corpus ingest — it is the
# canary that would have caught the B3 topic_override bug in seconds.
phase2-graph-artifacts-smoke:
	LIA_INTEGRATION=1 PYTHONPATH=src:. uv run --group dev pytest tests/integration/test_single_pass_ingest.py tests/integration/test_subtema_taxonomy_consistency.py -v -m integration

# ---- SUIN harvest targets (Phase A) ----------------------------------------
# These walk SUIN sitemaps and materialize artifacts/suin/<scope>/*.jsonl.
# The harvest is cache-keyed by URL (cache/suin/, gitignored) so re-runs are cheap.
SUIN_ARTIFACTS_DIR ?= artifacts/suin
SUIN_RPS ?= 1.0

phase2-suin-harvest-et:
	@echo "[deprecated: use phase2-suin-harvest-tributario]"
	PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest --scope et --out $(SUIN_ARTIFACTS_DIR)/tributario --rps $(SUIN_RPS) --json

phase2-suin-harvest-tributario:
	PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest --scope tributario --out $(SUIN_ARTIFACTS_DIR)/tributario --rps $(SUIN_RPS) --json

phase2-suin-harvest-laboral:
	PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest --scope laboral --out $(SUIN_ARTIFACTS_DIR)/laboral --rps $(SUIN_RPS) --json

phase2-suin-harvest-laboral-tributario:
	PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest --scope laboral-tributario --out $(SUIN_ARTIFACTS_DIR)/laboral-tributario --rps $(SUIN_RPS) --json

phase2-suin-harvest-jurisprudencia:
	PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest --scope jurisprudencia --out $(SUIN_ARTIFACTS_DIR)/jurisprudencia --rps $(SUIN_RPS) --json

phase2-suin-harvest-full:
	PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest --scope full --out $(SUIN_ARTIFACTS_DIR)/full --rps $(SUIN_RPS) --json

# ---- Phase 5c regrandfather pass -------------------------------------------
# One-time re-chunk of the existing corpus under the canonical 8-section
# template. `DRY_RUN=1` is the safe default lever; omit it (or set to empty)
# to actually mutate files under `knowledge_base/`.
#
# Usage:
#   make phase2-regrandfather-corpus DRY_RUN=1
#   make phase2-regrandfather-corpus LIMIT=10 SKIP_LLM=1
#   make phase2-regrandfather-corpus ONLY_TOPIC=laboral
phase2-regrandfather-corpus:
	PYTHONPATH=src:. uv run python scripts/regrandfather_corpus.py $(if $(DRY_RUN),--dry-run,--commit) $(if $(LIMIT),--limit $(LIMIT),) $(if $(ONLY_TOPIC),--only-topic $(ONLY_TOPIC),) $(if $(SKIP_LLM),--skip-llm,)

# ---- subtopic_generationv1 ------------------------------------------------
# Phase 2: one-shot collection pass that records `autogenerar_label` for every
# corpus document. Writes `artifacts/subtopic_candidates/collection_<UTC>.jsonl`.
# DRY_RUN=1 is the safe default lever; omit it to actually write files.
#
# Usage:
#   make phase2-collect-subtopic-candidates DRY_RUN=1 LIMIT=10
#   make phase2-collect-subtopic-candidates LIMIT=10 SKIP_LLM=1   # fast smoke, no LLM
#   make phase2-collect-subtopic-candidates ONLY_TOPIC=laboral    # scoped run
#   make phase2-collect-subtopic-candidates                       # full corpus commit
phase2-collect-subtopic-candidates:
	PYTHONPATH=src:. uv run python scripts/collect_subtopic_candidates.py $(if $(DRY_RUN),--dry-run,--commit) $(if $(LIMIT),--limit $(LIMIT),) $(if $(ONLY_TOPIC),--only-topic $(ONLY_TOPIC),) $(if $(SKIP_LLM),--skip-llm,) $(if $(BATCH_ID),--batch-id $(BATCH_ID),) $(if $(RESUME_FROM),--resume-from $(RESUME_FROM),) $(if $(RATE_LIMIT_RPM),--rate-limit-rpm $(RATE_LIMIT_RPM),)

# Phase 3: mine collection JSONL(s) → proposal clusters per parent_topic.
# Writes `artifacts/subtopic_proposals_<UTC>.json`. Safe to run offline — the
# embedding seam falls back to one-hot vectors when --skip-embed is set.
#
# Usage:
#   make phase3-mine-subtopic-candidates INPUT=artifacts/subtopic_candidates/collection_*.jsonl
#   make phase3-mine-subtopic-candidates INPUT=... CLUSTER_THRESHOLD=0.85
#   make phase3-mine-subtopic-candidates INPUT=... ONLY_TOPIC=laboral SKIP_EMBED=1
phase3-mine-subtopic-candidates:
	PYTHONPATH=src:. uv run python scripts/mine_subtopic_candidates.py --input '$(INPUT)' $(if $(OUTPUT),--output $(OUTPUT),) $(if $(CLUSTER_THRESHOLD),--cluster-threshold $(CLUSTER_THRESHOLD),) $(if $(MIN_CLUSTER_SIZE),--min-cluster-size $(MIN_CLUSTER_SIZE),) $(if $(ONLY_TOPIC),--only-topic $(ONLY_TOPIC),) $(if $(SLUG_STEM_RULES),--slug-stem-rules $(SLUG_STEM_RULES),) $(if $(SKIP_EMBED),--skip-embed,)

# Phase 6: promote `artifacts/subtopic_decisions.jsonl` → `config/subtopic_taxonomy.json`.
# DRY_RUN=1 prints a diff without writing. Stakeholder sign-off gate — see
# docs/next/subtopic_generationv1.md §0.11.
#
# Usage:
#   make phase2-promote-subtopic-taxonomy DRY_RUN=1
#   make phase2-promote-subtopic-taxonomy VERSION=2026-04-21-v1
phase2-promote-subtopic-taxonomy:
	PYTHONPATH=src:. uv run python scripts/promote_subtopic_decisions.py $(if $(DRY_RUN),--dry-run,) $(if $(DECISIONS),--decisions $(DECISIONS),) $(if $(OUTPUT),--output $(OUTPUT),) $(if $(VERSION),--version $(VERSION),) $(if $(SYNC_SUPABASE),--sync-supabase $(SYNC_SUPABASE),)

# ---- ingestfix-v2 --------------------------------------------------------
# Phase 2 (v2) sync: mirror config/subtopic_taxonomy.json into Supabase.
# TARGET=wip|production.
#
# Usage:
#   make phase2-sync-subtopic-taxonomy DRY_RUN=1
#   make phase2-sync-subtopic-taxonomy TARGET=wip
#   make phase2-sync-subtopic-taxonomy TARGET=production
phase2-sync-subtopic-taxonomy:
	PYTHONPATH=src:. uv run python scripts/sync_subtopic_taxonomy_to_supabase.py $(if $(DRY_RUN),--dry-run,) $(if $(TARGET),--target $(TARGET),) $(if $(TAXONOMY),--taxonomy $(TAXONOMY),)

# Maintenance-only backfill of documents.subtema via PASO 4. After
# ingestfix-v2-maximalist (docs/next/ingestfixv2.md), the normal
# single-pass ingest populates subtema + Falkor SubTopic structure
# inline. Use this target to re-classify docs flagged
# requires_subtopic_review=true or after a taxonomy version bump.
# DRY_RUN=1 is the safe default.
#
# Usage:
#   make phase2-backfill-subtopic DRY_RUN=1 LIMIT=10
#   make phase2-backfill-subtopic DRY_RUN=1 ONLY_REQUIRES_REVIEW=1
#   make phase2-backfill-subtopic LIMIT=50            # --commit
phase2-backfill-subtopic:
	PYTHONPATH=src:. uv run python scripts/backfill_subtopic.py $(if $(DRY_RUN),--dry-run,--commit) $(if $(LIMIT),--limit $(LIMIT),) $(if $(ONLY_TOPIC),--only-topic $(ONLY_TOPIC),) $(if $(RATE_LIMIT_RPM),--rate-limit-rpm $(RATE_LIMIT_RPM),) $(if $(GENERATION_ID),--generation-id $(GENERATION_ID),) $(if $(RESUME_FROM),--resume-from $(RESUME_FROM),) $(if $(REFRESH_EXISTING),--refresh-existing,) $(if $(ONLY_REQUIRES_REVIEW),--only-requires-review,) $(if $(NO_FALKOR),--no-falkor-emit,)

# Trace a query through the lexical planner layers (topic router + subtopic
# classifier + sub-question splitter). No Supabase, no Falkor, no LLM — safe
# to run without cloud env vars. See docs/next/structuralwork_v1_SEENOW.md
# item E for background.
#
# Usage:
#   make debug-query Q="La DIAN le envió un requerimiento..."
#   make debug-query Q="..." FULL=1              # include GraphRetrievalPlan
#   make debug-query Q="..." PER_SUB_QUESTION=1  # trace each ¿…? separately
#   make debug-query Q="..." TOPIC=renta         # pin requested_topic
debug-query:
	@test -n "$(Q)" || (echo "Usage: make debug-query Q='your query here' [FULL=1] [PER_SUB_QUESTION=1] [TOPIC=renta]"; exit 1)
	PYTHONPATH=src:. uv run python scripts/debug_query.py $(if $(FULL),--full,) $(if $(PER_SUB_QUESTION),--per-sub-question,) $(if $(TOPIC),--topic $(TOPIC),) "$(Q)"
