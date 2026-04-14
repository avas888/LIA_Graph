# Evals

Ultima verificacion contra codigo: 2026-03-22.

Este directorio concentra datasets y rubricas offline para las superficies con suite evaluable hoy. No reemplaza la cobertura automatizada de `pytest`, `vitest` y `Playwright`; la complementa.

Snapshot de cobertura automatizada auditado hoy:

- `91` archivos Python `test_*.py` en `tests/`
- `18` pruebas frontend en `frontend/`
- `8` specs Playwright en `e2e/`

## Cobertura evaluada

### Chat principal

- dataset: [`pipeline_c_golden.jsonl`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/evals/pipeline_c_golden.jsonl)
- rubrica: [`pipeline_c_rubric.yaml`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/evals/pipeline_c_rubric.yaml)
- runner: [`../scripts/eval_pipeline_c_gold.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/scripts/eval_pipeline_c_gold.py)
- loop: [`../scripts/ralph_loop_pipeline_c.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/scripts/ralph_loop_pipeline_c.py)

### Analisis normativo

- dataset: [`normative_analysis_suite.jsonl`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/evals/normative_analysis_suite.jsonl)
- rubrica: [`normative_analysis_rubric.yaml`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/evals/normative_analysis_rubric.yaml)
- runner: [`../scripts/eval_normative_analysis.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/scripts/eval_normative_analysis.py)
- loop: [`../scripts/ralph_loop_normativa.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/scripts/ralph_loop_normativa.py)

### Retrieval benchmark

- benchmark de queries: [`rag_retrieval_benchmark.jsonl`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/evals/rag_retrieval_benchmark.jsonl)
- runner base: [`run_retrieval_eval.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/evals/run_retrieval_eval.py)
- diagnosticos extendidos: [`../scripts/benchmark_retrieval_speed.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/scripts/benchmark_retrieval_speed.py)

## Cobertura automatizada relacionada fuera de `evals/`

- taxonomia y payload normativo: [`../tests/test_normative_taxonomy.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/tests/test_normative_taxonomy.py), [`../tests/test_normative_analysis.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/tests/test_normative_analysis.py)
- contrato HTTP: [`../tests/test_ui_server_routes.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/tests/test_ui_server_routes.py)
- retrieval y stores Supabase: [`../tests/test_supabase_retriever.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/tests/test_supabase_retriever.py), [`../tests/test_supabase_stores.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/tests/test_supabase_stores.py), [`../tests/test_retrieval_profiles.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/tests/test_retrieval_profiles.py)
- grounding y referencias normativas: [`../tests/test_citation_metadata.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/tests/test_citation_metadata.py), [`../tests/test_normative_grounding_units.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/tests/test_normative_grounding_units.py), [`../tests/test_normative_references.py`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/tests/test_normative_references.py)
- frontend chat, form guides y normativa: [`../frontend/tests/chatActions.test.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/frontend/tests/chatActions.test.ts), [`../frontend/tests/chatEmptyState.test.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/frontend/tests/chatEmptyState.test.ts), [`../frontend/tests/chatFormatting.test.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/frontend/tests/chatFormatting.test.ts), [`../frontend/tests/citations.test.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/frontend/tests/citations.test.ts), [`../frontend/tests/requestController.test.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/frontend/tests/requestController.test.ts), [`../frontend/tests/transcriptController.test.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/frontend/tests/transcriptController.test.ts), [`../frontend/tests/expertPanelController.test.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/frontend/tests/expertPanelController.test.ts), [`../frontend/tests/formGuideApp.test.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/frontend/tests/formGuideApp.test.ts), [`../frontend/tests/normativeAnalysisApp.test.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/frontend/tests/normativeAnalysisApp.test.ts), [`../frontend/tests/opsApp.test.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/frontend/tests/opsApp.test.ts)
- E2E: [`../e2e/chat-streaming.spec.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/e2e/chat-streaming.spec.ts), [`../e2e/expert-panel.spec.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/e2e/expert-panel.spec.ts), [`../e2e/form-guide.spec.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/e2e/form-guide.spec.ts), [`../e2e/gui-evidence.spec.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/e2e/gui-evidence.spec.ts), [`../e2e/normative-analysis.spec.ts`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/e2e/normative-analysis.spec.ts)

## Lo que aun no existe como suite offline separada

- dataset dedicado para `form-guides/chat`
- benchmark offline propio para browser shell `/` y backstage
- suite offline dedicada para `source-view/source-download`
- suite offline dedicada para persistencia multi-sesion del chat

## Artefactos complementarios

- chequeo de soporte/ranking mas reciente: [`../artifacts/reviews/ranking_support_window_check_latest.json`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/artifacts/reviews/ranking_support_window_check_latest.json)
- audit de integridad practica: [`../artifacts/runtime/practical_doc_anchor_audit.json`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/artifacts/runtime/practical_doc_anchor_audit.json)
- resumen de calidad de indice: [`../artifacts/runtime/index_quality_report.json`](/Users/ava-sensas/Developer/Lia-contadores/Lia_contadores/artifacts/runtime/index_quality_report.json)

## Comandos

```bash
cd /Users/ava-sensas/Developer/Lia-contadores/Lia_contadores
uv run python scripts/eval_pipeline_c_gold.py --dataset evals/pipeline_c_golden.jsonl
uv run python scripts/eval_normative_analysis.py --dataset evals/normative_analysis_suite.jsonl
PYTHONPATH=src:. uv run python -m evals.run_retrieval_eval --dataset evals/rag_retrieval_benchmark.jsonl --index artifacts/document_index.jsonl --profile hybrid_rerank
```
