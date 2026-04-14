# Appendix A — File Map

This appendix lists implementation targets in the real project tree. It does not propose storing source code inside `docs/build/`.

## Existing Files Likely To Change

- `src/lia_graph/ui_server.py`
- `src/lia_graph/ui_chat_controller.py`
- `src/lia_graph/ui_chat_payload.py`
- `src/lia_graph/pipeline_c/contracts.py`
- `src/lia_graph/chat_run_runtime.py`
- `src/lia_graph/chat_runs_store.py`
- `src/lia_graph/ingest.py`
- `src/lia_graph/corpus_ops.py`
- `src/lia_graph/topic_router.py`
- `src/lia_graph/pipeline_c/intake.py`
- `src/lia_graph/pipeline_c/norm_topic_index.py`
- `src/lia_graph/contracts/company.py`
- `src/lia_graph/access_guardrails.py`
- `src/lia_graph/conversation_store.py`
- `src/lia_graph/ui_chat_persistence.py`
- `src/lia_graph/user_management.py`
- `src/lia_graph/pipeline_c/safety.py`
- `src/lia_graph/pipeline_c/telemetry.py`
- `src/lia_graph/ui_reference_resolvers.py`
- `src/lia_graph/citation_resolution.py`
- `src/lia_graph/dependency_smoke.py`
- `src/lia_graph/orchestration_settings.py`
- `docs/README.md`
- `docs/state/STATE.md`

## New Files Likely To Be Created

- `src/lia_graph/pipeline_router.py`
- `src/lia_graph/graph/schema.py`
- `src/lia_graph/graph/client.py`
- `src/lia_graph/graph/validators.py`
- `src/lia_graph/ingestion/parser.py`
- `src/lia_graph/ingestion/linker.py`
- `src/lia_graph/ingestion/classifier.py`
- `src/lia_graph/ingestion/loader.py`
- `src/lia_graph/pipeline_d/orchestrator.py`
- `src/lia_graph/pipeline_d/planner.py`
- `src/lia_graph/pipeline_d/retriever.py`
- `src/lia_graph/pipeline_d/contracts.py`
- `src/lia_graph/pipeline_d/evidence_bundle.py`
- `src/lia_graph/pipeline_d/composer.py`
- `src/lia_graph/pipeline_d/verifier.py`
- `src/lia_graph/pipeline_d/compiled_cache.py`
- `evals/run_dual_pipeline_eval.py`
- `scripts/run_shadow_compare.py`

## Artifact Families

- `artifacts/corpus_audit_report.json`
- `artifacts/revision_candidates.json`
- `artifacts/excluded_files.json`
- `artifacts/canonical_corpus_manifest.json`
- `artifacts/corpus_inventory.json`
- `artifacts/parsed_articles.jsonl`
- `artifacts/raw_edges.jsonl`
- `artifacts/typed_edges.jsonl`
- `artifacts/graph_load_report.json`
- `artifacts/graph_validation_report.json`
- `artifacts/eval/*`
- `artifacts/shadow/*`

Corpus audit outputs are prerequisites for later inventory, manifest, or graph interpretation work.
