# LIA_Graph — Master State

> **Last updated**: 2026-04-13T22:40-04:00
> **Phase**: 0 — Repository Bootstrap
> **Status**: IN_PROGRESS

---

## Current Phase

### Phase 0: Repository Bootstrap
- [x] Create GitHub repo `avas888/LIA_Graph`
- [x] Define fork boundary (what to copy vs. build new)
- [x] Create state management docs
- [ ] Copy shared modules from Lia_contadores
- [ ] Create dependency manifest
- [ ] Initial commit with skeleton

### Phase 1: Corpus Ingestion & Graph Build (NOT STARTED)
- [ ] Parse ET articles from 24 Markdown files → individual ArticleNodes
- [ ] Extract cross-references (regex) → edge candidates
- [ ] LLM-assisted edge classification (MODIFIES, REFERENCES, EXCEPTION_TO, etc.)
- [ ] Load into FalkorDB
- [ ] Validate graph integrity (node count, edge count, orphan check)
- See: `docs/state/TASK-01-corpus-ingestion.md`

### Phase 2: Pipeline D Core (NOT STARTED)
- [ ] Graph-first retriever (FalkorDB query → subgraph → context)
- [ ] Graph-aware planner (concept entry points → walk strategy)
- [ ] Composer (subgraph-grounded answer generation)
- [ ] Wire into shared contracts (PipelineCRequest/Response compatible)
- See: `docs/state/TASK-02-pipeline-d-core.md`

### Phase 3: Integration & Eval (NOT STARTED)
- [ ] Header-based routing (`X-Lia-Pipeline: d`)
- [ ] Dual eval harness (Pipeline C golden set → Pipeline D)
- [ ] Comparative metrics report
- See: `docs/state/TASK-03-integration-eval.md`

### Phase 4: Deploy & Shadow Mode (NOT STARTED)
- [ ] Railway deployment config
- [ ] Shadow mode (dual-run, log both, serve Pipeline C)
- [ ] Per-tenant beta toggle
- See: `docs/state/TASK-04-deploy.md`

---

## Fork Boundary

### COPIED from Lia_contadores (shared, not modified)

These modules are **identical** to the parent repo and must stay in sync:

| Module | Purpose | Why shared |
|--------|---------|------------|
| `platform_auth.py` | JWT auth, token issuance | Auth must be identical |
| `supabase_client.py` | Supabase connection | Same DB (or parallel) |
| `ui_server.py` | HTTP server + route dispatch | Frontend serves from here |
| `ui_chat_controller.py` | Chat endpoint handler | Calls `deps["run_pipeline"]` |
| `pipeline_c/contracts.py` | PipelineCRequest, PipelineCResponse | Pipeline D must conform |
| `pipeline_c/streaming.py` | SSE streaming, StructuredMarkdownStreamAssembler | Shared streaming infra |
| `pipeline_c/safety.py` | Content safety checks | Shared safety layer |
| `pipeline_c/telemetry.py` | Timing + diagnostics | Shared observability |
| `pipeline_c/intake.py` | Query classification, topic routing | Shared intake |
| `topic_router.py` | Topic classification | Shared routing |
| `env_loader.py` | Environment config | Shared config |
| `rate_limiter.py` | Rate limiting | Shared infra |
| `frontend/` (entire) | Vite + TS UI | Identical frontend |
| `supabase/migrations/` | All existing migrations | Schema compatibility |
| `evals/` | Golden evaluation sets | Comparison baseline |

### NEW in LIA_Graph (Pipeline D specific)

| Module | Purpose |
|--------|---------|
| `src/lia_graph/pipeline_d/orchestrator.py` | Pipeline D orchestrator (graph-first) |
| `src/lia_graph/pipeline_d/retriever.py` | FalkorDB graph retrieval |
| `src/lia_graph/pipeline_d/planner.py` | Graph-aware query planning |
| `src/lia_graph/pipeline_d/composer.py` | Subgraph-grounded answer composition |
| `src/lia_graph/pipeline_d/compiled_cache.py` | Compiled answer cache with graph-linked invalidation |
| `src/lia_graph/graph/schema.py` | FalkorDB node/edge type definitions |
| `src/lia_graph/graph/client.py` | FalkorDB connection + query helpers |
| `src/lia_graph/graph/validators.py` | Graph integrity checks |
| `src/lia_graph/ingestion/parser.py` | ET Markdown → ArticleNode extraction |
| `src/lia_graph/ingestion/linker.py` | Cross-reference extraction |
| `src/lia_graph/ingestion/classifier.py` | LLM-assisted edge typing |
| `src/lia_graph/ingestion/loader.py` | FalkorDB bulk loader |

### NOT COPIED (Pipeline C specific, replaced by Pipeline D)

| Module | Why excluded |
|--------|-------------|
| `pipeline_c/orchestrator.py` | Replaced by Pipeline D orchestrator |
| `pipeline_c/retriever.py` | Replaced by graph retriever |
| `pipeline_c/planner.py` | Replaced by graph-aware planner |
| `pipeline_c/composer.py` | Replaced by subgraph composer |
| `pipeline_c/reranker.py` | Graph scoring replaces vector reranking |
| `pipeline_c/semantic_cache.py` | Replaced by compiled cache |
| `pipeline_c/knowledge_bundle.py` | Replaced by graph subgraph extraction |
| `pipeline_c/retrieval_scoring.py` | Replaced by graph traversal scoring |
| All `ingestion_*.py` files | New ingestion pipeline for graph |

---

## External Dependencies Needed

| Service | Purpose | Status | Notes |
|---------|---------|--------|-------|
| **Supabase** (2nd project) | Postgres + pgvector for vectors, sessions, auth tables | NEEDED | Free tier OK for dev |
| **FalkorDB Cloud** | Knowledge graph store | NEEDED | Free tier: 1 graph, 1 GB |
| **OpenAI API** | Embeddings + LLM calls | NEEDED | Same key as Lia_contadores |
| **Railway** | Deployment | LATER | Phase 4 |
| **Dropbox** | Corpus source files | CONNECTED via shared link | 24 ET .md files needed |

---

## Key Design Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-13 | Fork as separate repo, not branch | Clean separation; independent deploy; no risk to production Pipeline C |
| 2026-04-13 | Reuse contracts.py (PipelineCRequest/Response) | Frontend doesn't change; A/B routing via header |
| 2026-04-13 | FalkorDB over Neo4j | Lower latency, better LLM integration, free tier sufficient |
| 2026-04-13 | Start with Libro I (Renta) only | ~400 articles, 60%+ of queries, densest cross-references |
| 2026-04-13 | Cloud services over local Docker | Agent can operate autonomously; no local machine dependency |

---

## How to Resume After Crash

1. Read this file (`docs/state/STATE.md`) — it tells you the current phase
2. Read the task-specific file for the current phase (e.g., `TASK-01-corpus-ingestion.md`)
3. Each task file has a `## Last Checkpoint` section with exact resumption instructions
4. All intermediate artifacts are saved to `artifacts/` with timestamps
5. All decisions are logged in this file's "Key Design Decisions Log"
