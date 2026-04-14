# Fork Boundary: Lia_contadores → LIA_Graph

> This document defines exactly what is shared between the two repos
> and where Pipeline D diverges from Pipeline C.

---

## Codebase Scale (Lia_contadores)

| Metric | Count |
|--------|-------|
| Total Python files | 204 |
| Pipeline C specific files | 62 |
| Total Python LoC | 83,218 |
| Frontend files (TS/CSS/HTML) | 276 |
| SQL migrations | 45 |
| Eval files | 20 |

## Fork Strategy: Selective Copy, Not Git Fork

**Why not `git fork`**: A git fork carries the full commit history and all
Pipeline C code. We want a clean repo that only contains what Pipeline D
needs, making it easier to reason about, test, and deploy independently.

**Strategy**: Copy shared modules verbatim. Build Pipeline D modules fresh.

---

## Layer-by-Layer Analysis

### Layer 1: HTTP Server + Routing (COPY)

```
ui_server.py              → COPY (modify _chat_controller_deps to inject pipeline_d)
ui_chat_controller.py     → COPY (already uses deps["run_pipeline_c"] — change key name)
ui_chat_payload.py        → COPY
ui_chat_persistence.py    → COPY
ui_chat_context.py        → COPY
ui_route_controllers.py   → COPY
```

**Key modification**: In `ui_server.py`, line 698:
```python
# Before (Pipeline C):
"run_pipeline_c": run_pipeline_c,

# After (Pipeline D):
"run_pipeline": run_pipeline_d,  # or router based on header
```

### Layer 2: Auth + Tenancy (COPY)

```
platform_auth.py          → COPY (JWT issuance, verification)
service_account_auth.py   → COPY
access_guardrails.py      → COPY
user_management.py        → COPY
turnstile.py              → COPY
```

Zero modifications needed. Auth is pipeline-agnostic.

### Layer 3: Contracts + Streaming (COPY)

```
pipeline_c/contracts.py   → COPY (PipelineCRequest, PipelineCResponse)
pipeline_c/streaming.py   → COPY (SSE, StructuredMarkdownStreamAssembler)
pipeline_c/safety.py      → COPY
pipeline_c/telemetry.py   → COPY
```

Pipeline D outputs a `PipelineCResponse`. The frontend doesn't know
which pipeline generated it.

### Layer 4: Intake + Topic Routing (COPY)

```
pipeline_c/intake.py      → COPY (query classification, language, safety pre-screen)
topic_router.py           → COPY (topic classification)
scope_guardrails.py       → COPY
topic_guardrails.py       → COPY
```

Query understanding is shared. Pipeline D diverges at retrieval.

### Layer 5: Infrastructure (COPY)

```
supabase_client.py        → COPY
env_loader.py             → COPY
runtime_env.py            → COPY
rate_limiter.py           → COPY
adapters/llm.py           → COPY
llm_runtime.py            → COPY
embeddings.py             → COPY (still need vector similarity for initial concept matching)
instrumentation.py        → COPY
```

### Layer 6: Retrieval (REPLACE — this is the core difference)

**Pipeline C** (NOT copied):
```
pipeline_c/retriever.py           → REPLACE with graph_retriever.py
pipeline_c/retrieval_scoring.py   → REPLACE with graph traversal scoring
pipeline_c/retrieval_filters.py   → REPLACE with graph edge filters
pipeline_c/reranker.py            → REPLACE (graph scoring replaces reranking)
pipeline_c/supabase_fetch.py      → REPLACE (FalkorDB queries replace Supabase vector queries)
pipeline_c/knowledge_bundle.py    → REPLACE with subgraph extraction
pipeline_c/retrieval_session_cache.py → REPLACE with compiled cache
pipeline_c/semantic_cache.py      → REPLACE with compiled answer cache
pipeline_c/graph_walk_service.py  → REPLACE (this was a prototype; Pipeline D is the full version)
pipeline_c/normative_edge_builder.py → REPLACE (edges pre-built in FalkorDB, not runtime-computed)
pipeline_c/norm_topic_index.py    → REPLACE with FalkorDB concept index
```

**Pipeline D** (NEW):
```
pipeline_d/retriever.py           → Graph-first retrieval via FalkorDB
pipeline_d/planner.py             → Graph-aware query planning
pipeline_d/composer.py            → Subgraph-grounded answer generation
pipeline_d/compiled_cache.py      → Pre-computed answers with graph-linked invalidation
graph/client.py                   → FalkorDB connection wrapper
graph/schema.py                   → Node/edge type definitions
graph/validators.py               → Graph integrity checks
```

### Layer 7: Planning + Composition (REPLACE)

**Pipeline C** (NOT copied):
```
pipeline_c/planner.py              → REPLACE with graph-aware planner
pipeline_c/composer.py             → REPLACE with subgraph composer
pipeline_c/compose_evidence.py     → REPLACE
pipeline_c/compose_quality.py      → REPLACE
pipeline_c/compose_ranking.py      → REPLACE
pipeline_c/composer_prompts.py     → REPLACE (new prompts for graph-grounded answers)
pipeline_c/composer_normalization.py → REPLACE
pipeline_c/quality_checks.py       → ADAPT (reuse quality criteria, change input format)
pipeline_c/quality_critic.py       → ADAPT
pipeline_c/verifier.py             → ADAPT (verify against graph subgraph, not flat chunks)
```

### Layer 8: Ingestion (ALL NEW)

Pipeline C's ingestion pipeline (20+ files) is designed for flat chunk + embed.
Pipeline D needs a completely different ingestion pipeline:

```
ingestion/parser.py       → Parse ET Markdown → ArticleNodes
ingestion/linker.py       → Extract cross-references → edge candidates
ingestion/classifier.py   → LLM-assisted edge typing
ingestion/loader.py       → FalkorDB bulk load
```

### Layer 9: Frontend (COPY ENTIRE)

```
frontend/                 → COPY (entire directory)
```

Zero modifications. The frontend talks to the same API endpoints.
The only difference is the response quality.

### Layer 10: Database + Migrations (COPY + EXTEND)

```
supabase/migrations/      → COPY all 45 existing migrations
```

New migrations for Pipeline D:
- `graph_compiled_answers` table
- `graph_ingestion_state` table
- `shadow_responses` table (for dual eval)

---

## Dependency Injection Point (The "One-Line Swap")

File: `ui_server.py`, function `_chat_controller_deps()`, line ~698

```python
def _chat_controller_deps() -> dict[str, Any]:
    return {
        # Pipeline C (original):
        # "run_pipeline_c": run_pipeline_c,
        
        # Pipeline D (graph-based):
        "run_pipeline_c": run_pipeline_d,  # same key, different function
    }
```

The key stays `"run_pipeline_c"` because `ui_chat_controller.py` reads
`deps["run_pipeline_c"]`. We inject a different implementation.

For header-based routing (A/B testing):

```python
def _chat_controller_deps() -> dict[str, Any]:
    return {
        "run_pipeline_c": run_pipeline_c,  # original
        "run_pipeline_d": run_pipeline_d,  # new
        # ui_chat_controller reads header to choose
    }
```
