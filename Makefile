.PHONY: reset-c eval-c-gold eval-c-full eval-retrieval eval-faithfulness eval-alignment eval-taxonomy-v2 ralph-loop supabase-start supabase-stop supabase-reset supabase-status smoke-deps test-batched phase2-graph-artifacts phase2-graph-artifacts-supabase phase2-graph-artifacts-smoke phase2-corpus-additive phase2-promote-snapshot phase2-reap-stalled-jobs phase2-suin-harvest-et phase2-suin-harvest-tributario phase2-suin-harvest-laboral phase2-suin-harvest-laboral-tributario phase2-suin-harvest-jurisprudencia phase2-suin-harvest-full phase2-regrandfather-corpus phase2-collect-subtopic-candidates phase3-mine-subtopic-candidates phase2-promote-subtopic-taxonomy phase2-backfill-subtopic phase2-sync-subtopic-taxonomy debug-query

PHASE2_CORPUS_DIR ?= knowledge_base
PHASE2_ARTIFACTS_DIR ?= artifacts

reset-c:
	./scripts/reset_pipeline_c_state.sh

eval-c-gold:
	PYTHONPATH=src:. uv run python scripts/eval_pipeline_c_gold.py --threshold 90

# next_v3 §6 — SME taxonomy v2 validation suite (30 questions).
# Threshold 27/30 per next_v3 §6 step 5b (chat-resolver accuracy).
# Runs lexical router + full resolver; does NOT require cloud / LLM.
eval-taxonomy-v2:
	# --use-llm is required: chat-resolver path is the canonical gate-8 measurement
	# (next_v3 §6 / §13.4). Without it, this target measures router-only and bottoms
	# out at 15/30 instead of the actual chat-resolver baseline of 23/30 (see §13.4).
	PYTHONPATH=src:. uv run python scripts/evaluations/run_taxonomy_v2_validation.py \
		--gold evals/gold_taxonomy_v2_validation.jsonl \
		--threshold 27 --verbose --use-llm

eval-c-full:
	PYTHONPATH=src:. LIA_BATCHED_RUNNER=1 uv run pytest -q
	PYTHONPATH=src:. uv run python -m evals.run_retrieval_eval --dataset evals/rag_retrieval_benchmark.jsonl --index artifacts/document_index.jsonl --profile hybrid_rerank
	PYTHONPATH=src:. uv run python scripts/eval_pipeline_c_gold.py --threshold 90

# Structural backlog item #1 — retrieval eval harness against
# `evals/gold_retrieval_v1.jsonl`. Fires each gold entry (and each
# sub-question of M-type entries) through `resolve_chat_topic`
# → `run_pipeline_d` and scores against the curator-annotated
# `expected_article_keys` + resolver topic labels.
#
# CI gate: **regression vs committed baseline** (`evals/baseline.json`)
# at 2pp tolerance. Absolute red lines are reported as aspirational but
# NOT gated at n=30 — 95% CI on r@10 is ±~18pp at that sample size, so
# a 0.70 floor would false-fail clean PRs and false-pass real regressions.
# Switch to absolute gating once the gold hits ~80 entries and the
# metric stabilizes.
#
# Metrics are reported in a 2×2 matrix:
#   (primary_only | with_connected) × (strict | loose normalizer)
# The deltas are diagnostic — loose−strict shows the "parent container"
# looseness cost; with_connected−primary_only shows graph-expansion rescue.
# `subtopic_accuracy` is intentionally not reported until the accountant
# re-indexes gold `expected_subtopic` slugs against
# `config/subtopic_taxonomy.json`. See `docs/next/package_expert.md`.
#
# Usage:
#   make eval-retrieval                          # regression gate (CI default)
#   make eval-retrieval FAIL_ON_REGRESSION=0     # report only, no gate
#   make eval-retrieval ASPIRATIONAL=1           # also gate on red lines (human-run)
#   make eval-retrieval UPDATE_BASELINE=1        # overwrite evals/baseline.json
#   make eval-retrieval JSON=1                   # JSON-only output
#   make eval-retrieval GOLD=evals/other.jsonl
#   make eval-retrieval TOLERANCE_PP=3           # looser regression gate
#
# Reranker stays in `shadow` by default so the eval exercises the same
# diagnostic path the served runtime uses. `RERANKER_MODE=off` for a
# pure hybrid baseline; `RERANKER_MODE=live` once a sidecar is wired.
# `SKIP_SUBQ=1` is the default so the eval runs consistently with the
# committed `evals/baseline.json` methodology. Full sub-question fanout
# is a future baseline — see the methodology-mismatch guard in the
# harness, which refuses to gate if CI and baseline disagree on flags.
FAIL_ON_REGRESSION ?= 1
ASPIRATIONAL ?=
UPDATE_BASELINE ?=
TOLERANCE_PP ?= 2
RERANKER_MODE ?= live
SKIP_SUBQ ?= 1
# V2-2 query decomposition. Baselines are imprinted with DECOMPOSE=on,
# matching the staging runtime default. Local `npm run dev` still ships
# with LIA_QUERY_DECOMPOSE=off so engineers can A/B manually; the eval
# harnesses always run with DECOMPOSE=on for methodology consistency.
DECOMPOSE ?= on
eval-retrieval:
	LIA_RERANKER_MODE=$(RERANKER_MODE) LIA_QUERY_DECOMPOSE=$(DECOMPOSE) PYTHONPATH=src:. uv run python scripts/eval_retrieval.py $(if $(GOLD),--gold $(GOLD),) $(if $(BASELINE),--baseline $(BASELINE),) --tolerance-pp $(TOLERANCE_PP) $(if $(filter 1,$(FAIL_ON_REGRESSION)),--fail-on-regression,) $(if $(ASPIRATIONAL),--fail-under-red-lines,) $(if $(UPDATE_BASELINE),--update-baseline,) $(if $(JSON),--json,) $(if $(OUTPUT),--output $(OUTPUT),) $(if $(filter 1,$(SKIP_SUBQ)),--skip-sub-questions,) $(if $(TOP_K),--top-k $(TOP_K),)

# Citation-faithfulness harness — sibling to `eval-retrieval`. Asks
# whether the answer we show the accountant is grounded in the evidence
# the retriever returned. Two metrics, gold-free (no new curator
# annotations needed): `citation_precision` (anti-hallucination) and
# `primary_anchor_recall` (anti-orphan-evidence), plus an observability
# `abstention_rate`. Same CI-gate shape as eval-retrieval:
# regression-vs-`evals/faithfulness_baseline.json` at 2pp tolerance.
#
# Usage:
#   make eval-faithfulness                       # regression gate (CI default)
#   make eval-faithfulness ASPIRATIONAL=1        # also gate red lines
#   make eval-faithfulness UPDATE_BASELINE=1     # re-freeze baseline
#   make eval-faithfulness JSON=1
eval-faithfulness:
	LIA_RERANKER_MODE=$(RERANKER_MODE) LIA_QUERY_DECOMPOSE=$(DECOMPOSE) PYTHONPATH=src:. uv run python scripts/eval_citations.py $(if $(GOLD),--gold $(GOLD),) $(if $(BASELINE),--baseline $(BASELINE),) --tolerance-pp $(TOLERANCE_PP) $(if $(filter 1,$(FAIL_ON_REGRESSION)),--fail-on-regression,) $(if $(ASPIRATIONAL),--fail-under-red-lines,) $(if $(UPDATE_BASELINE),--update-baseline,) $(if $(JSON),--json,) $(if $(OUTPUT),--output $(OUTPUT),) $(if $(TOP_K),--top-k $(TOP_K),)

# Topic-alignment harness — third sibling. Measures whether the answer
# body discusses the same topic the router chose and whether it matches
# the gold's expected_topic. Also measures safety_abstention_rate (the
# rate at which topic_safety.py router-silent / misalignment checks fire)
# as a band metric — too low = safety checks are missing wrong answers;
# too high = safety is over-firing on valid queries.
#
# Same gate pattern. CI runs the regression-vs-baseline at 2pp tolerance.
#
# Usage:
#   make eval-alignment                      # regression gate (CI default)
#   make eval-alignment ASPIRATIONAL=1       # also gate aspirational floors
#   make eval-alignment UPDATE_BASELINE=1    # re-freeze baseline
eval-alignment:
	LIA_RERANKER_MODE=$(RERANKER_MODE) LIA_QUERY_DECOMPOSE=$(DECOMPOSE) PYTHONPATH=src:. uv run python scripts/eval_topic_alignment.py $(if $(GOLD),--gold $(GOLD),) $(if $(BASELINE),--baseline $(BASELINE),) --tolerance-pp $(TOLERANCE_PP) $(if $(filter 1,$(FAIL_ON_REGRESSION)),--fail-on-regression,) $(if $(ASPIRATIONAL),--fail-under-red-lines,) $(if $(UPDATE_BASELINE),--update-baseline,) $(if $(JSON),--json,) $(if $(OUTPUT),--output $(OUTPUT),) $(if $(TOP_K),--top-k $(TOP_K),)

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
# gui_ingestion_v1 §13.1 (next_v1 step 05): append --allow-non-local-env when
# targeting production, because env_posture.py aborts runs whose cloud creds
# didn't arrive via local .env files. Regression-safe: only fires on production.
PHASE2_SUPABASE_SINK_FLAGS = --supabase-sink --supabase-target $(PHASE2_SUPABASE_TARGET) --execute-load --allow-unblessed-load --strict-falkordb $(if $(filter production,$(PHASE2_SUPABASE_TARGET)),--allow-non-local-env,)
PHASE2_SUIN_FLAG = $(if $(INGEST_SUIN),--include-suin $(INGEST_SUIN),)

# next_v1 step 10: auto-source .env.staging when targeting production so
# `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production`
# works in a bare shell without the operator prepending `set -a; source
# .env.staging; set +a`. 2026-04-24 cloud-sink session proved the manual
# prefix is easy to forget; Makefile owns the target → Makefile owns the
# env load. No-op for non-production targets. Bash is required for
# `source`; Make's default shell is `/bin/sh` but the recipe line uses
# `bash -c` implicitly via `.SHELLFLAGS`/`SHELL` if overridden. To avoid
# a hard dependency on the operator's `SHELL` override, we invoke bash
# explicitly inside the recipe command string.
PHASE2_ENV_LOAD = $(if $(filter production,$(PHASE2_SUPABASE_TARGET)),set -a && . ./.env.staging && set +a &&,)

phase2-graph-artifacts-supabase:
	$(PHASE2_ENV_LOAD) PYTHONPATH=src:. uv run python -m lia_graph.ingest --corpus-dir $(PHASE2_CORPUS_DIR) --artifacts-dir $(PHASE2_ARTIFACTS_DIR) $(PHASE2_SUPABASE_SINK_FLAGS) $(PHASE2_SUIN_FLAG) --json

# Additive-corpus-v1 Phase 6 — delta run.
# Applies only the on-disk-vs-Supabase diff (added + modified + removed docs)
# onto gen_active_rolling. Full rebuild (phase2-graph-artifacts-supabase)
# stays canonical and is always the safe fallback.
#
#   make phase2-corpus-additive PHASE2_SUPABASE_TARGET=production
#   make phase2-corpus-additive PHASE2_SUPABASE_TARGET=production DELTA_DRY_RUN=1
#
# DELTA_ID, when set, pins the delta's identifier (otherwise auto-generated).
# DELTA_DRY_RUN=1 plans the delta but performs zero writes.
# STRICT_PARITY=1 escalates any Supabase<->Falkor parity mismatch to a hard block.
DELTA_ID ?=
DELTA_DRY_RUN ?=
STRICT_PARITY ?=
PHASE2_ADDITIVE_FLAGS = --additive --supabase-sink --supabase-target $(PHASE2_SUPABASE_TARGET) --supabase-generation-id gen_active_rolling --execute-load --allow-unblessed-load --strict-falkordb $(if $(filter production,$(PHASE2_SUPABASE_TARGET)),--allow-non-local-env,)
PHASE2_ADDITIVE_OPT_DELTA_ID = $(if $(DELTA_ID),--delta-id $(DELTA_ID),)
PHASE2_ADDITIVE_OPT_DRY_RUN = $(if $(DELTA_DRY_RUN),--dry-run-delta,)
PHASE2_ADDITIVE_OPT_STRICT_PARITY = $(if $(STRICT_PARITY),--strict-parity,)
phase2-corpus-additive:
	$(PHASE2_ENV_LOAD) PYTHONPATH=src:. uv run python -m lia_graph.ingest --corpus-dir $(PHASE2_CORPUS_DIR) --artifacts-dir $(PHASE2_ARTIFACTS_DIR) $(PHASE2_ADDITIVE_FLAGS) $(PHASE2_SUIN_FLAG) $(PHASE2_ADDITIVE_OPT_DELTA_ID) $(PHASE2_ADDITIVE_OPT_DRY_RUN) $(PHASE2_ADDITIVE_OPT_STRICT_PARITY) --json

# Promote a frozen `gen_<UTC>` snapshot into the active rolling position.
# Calls the promote_generation(text) RPC. The RPC body is a skeleton in Phase 1;
# the real promotion semantics (lock acquisition, is_active flip, diagnostics
# payload) land in Phase 6 tail work + Phase 9 rollback drill.
#
#   make phase2-promote-snapshot SNAPSHOT_GEN=gen_20260430120000
SNAPSHOT_GEN ?=
phase2-promote-snapshot:
	@if [ -z "$(SNAPSHOT_GEN)" ]; then \
		echo "error: SNAPSHOT_GEN=<gen_UTC> required"; exit 2; \
	fi
	PYTHONPATH=src:. uv run --group dev python -c "from lia_graph.supabase_client import create_supabase_client_for_target; import json, sys; c = create_supabase_client_for_target('$(PHASE2_SUPABASE_TARGET)'); r = c.rpc('promote_generation', {'target_gen': '$(SNAPSHOT_GEN)'}).execute(); print(json.dumps(getattr(r, 'data', None), ensure_ascii=False, indent=2))"

# Reap stalled ingest_delta_jobs rows (heartbeat older than 5 minutes).
# Phase 7 will expose a janitor helper; Phase 6 ships the SQL form directly.
phase2-reap-stalled-jobs:
	@docker exec supabase_db_lia-graph psql -U postgres -d postgres -c "UPDATE ingest_delta_jobs SET stage = 'failed', error_class = 'heartbeat_timeout', completed_at = NOW() WHERE stage NOT IN ('completed','failed','cancelled') AND last_heartbeat_at < NOW() - interval '5 minutes' RETURNING job_id, lock_target;"

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
	PYTHONPATH=src:. uv run python scripts/ingestion/regrandfather_corpus.py $(if $(DRY_RUN),--dry-run,--commit) $(if $(LIMIT),--limit $(LIMIT),) $(if $(ONLY_TOPIC),--only-topic $(ONLY_TOPIC),) $(if $(SKIP_LLM),--skip-llm,)

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
	PYTHONPATH=src:. uv run python scripts/ingestion/collect_subtopic_candidates.py $(if $(DRY_RUN),--dry-run,--commit) $(if $(LIMIT),--limit $(LIMIT),) $(if $(ONLY_TOPIC),--only-topic $(ONLY_TOPIC),) $(if $(SKIP_LLM),--skip-llm,) $(if $(BATCH_ID),--batch-id $(BATCH_ID),) $(if $(RESUME_FROM),--resume-from $(RESUME_FROM),) $(if $(RATE_LIMIT_RPM),--rate-limit-rpm $(RATE_LIMIT_RPM),)

# Phase 3: mine collection JSONL(s) → proposal clusters per parent_topic.
# Writes `artifacts/subtopic_proposals_<UTC>.json`. Safe to run offline — the
# embedding seam falls back to one-hot vectors when --skip-embed is set.
#
# Usage:
#   make phase3-mine-subtopic-candidates INPUT=artifacts/subtopic_candidates/collection_*.jsonl
#   make phase3-mine-subtopic-candidates INPUT=... CLUSTER_THRESHOLD=0.85
#   make phase3-mine-subtopic-candidates INPUT=... ONLY_TOPIC=laboral SKIP_EMBED=1
phase3-mine-subtopic-candidates:
	PYTHONPATH=src:. uv run python scripts/ingestion/mine_subtopic_candidates.py --input '$(INPUT)' $(if $(OUTPUT),--output $(OUTPUT),) $(if $(CLUSTER_THRESHOLD),--cluster-threshold $(CLUSTER_THRESHOLD),) $(if $(MIN_CLUSTER_SIZE),--min-cluster-size $(MIN_CLUSTER_SIZE),) $(if $(ONLY_TOPIC),--only-topic $(ONLY_TOPIC),) $(if $(SLUG_STEM_RULES),--slug-stem-rules $(SLUG_STEM_RULES),) $(if $(SKIP_EMBED),--skip-embed,)

# Phase 6: promote `artifacts/subtopic_decisions.jsonl` → `config/subtopic_taxonomy.json`.
# DRY_RUN=1 prints a diff without writing. Stakeholder sign-off gate — see
# docs/next/subtopic_generationv1.md §0.11.
#
# Usage:
#   make phase2-promote-subtopic-taxonomy DRY_RUN=1
#   make phase2-promote-subtopic-taxonomy VERSION=2026-04-21-v1
phase2-promote-subtopic-taxonomy:
	PYTHONPATH=src:. uv run python scripts/ingestion/promote_subtopic_decisions.py $(if $(DRY_RUN),--dry-run,) $(if $(DECISIONS),--decisions $(DECISIONS),) $(if $(OUTPUT),--output $(OUTPUT),) $(if $(VERSION),--version $(VERSION),) $(if $(SYNC_SUPABASE),--sync-supabase $(SYNC_SUPABASE),)

# ---- ingestfix-v2 --------------------------------------------------------
# Phase 2 (v2) sync: mirror config/subtopic_taxonomy.json into Supabase.
# TARGET=wip|production.
#
# Usage:
#   make phase2-sync-subtopic-taxonomy DRY_RUN=1
#   make phase2-sync-subtopic-taxonomy TARGET=wip
#   make phase2-sync-subtopic-taxonomy TARGET=production
phase2-sync-subtopic-taxonomy:
	PYTHONPATH=src:. uv run python scripts/ingestion/sync_subtopic_taxonomy_to_supabase.py $(if $(DRY_RUN),--dry-run,) $(if $(TARGET),--target $(TARGET),) $(if $(TAXONOMY),--taxonomy $(TAXONOMY),)

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
	PYTHONPATH=src:. uv run python scripts/ingestion/backfill_subtopic.py $(if $(DRY_RUN),--dry-run,--commit) $(if $(LIMIT),--limit $(LIMIT),) $(if $(ONLY_TOPIC),--only-topic $(ONLY_TOPIC),) $(if $(RATE_LIMIT_RPM),--rate-limit-rpm $(RATE_LIMIT_RPM),) $(if $(GENERATION_ID),--generation-id $(GENERATION_ID),) $(if $(RESUME_FROM),--resume-from $(RESUME_FROM),) $(if $(REFRESH_EXISTING),--refresh-existing,) $(if $(ONLY_REQUIRES_REVIEW),--only-requires-review,) $(if $(NO_FALKOR),--no-falkor-emit,)

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
