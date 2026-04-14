# LIA_Graph — Master State

> **Last updated**: 2026-04-14T00:00-04:00
> **Phase**: 0 — Repository Bootstrap
> **Status**: IN_PROGRESS

---

## Steering Kernel

LIA_Graph is meant to be "Lia Contador's product shell with a graph-native tax reasoning engine underneath."

We are not to let the old RAG influence us. Our duty is to think different and RAG with graph.

Active design rule:
- Reuse frontend, auth, RBAC, streaming, contracts, and prior corpus research.
- Keep LIA_Graph on its own Railway, FalkorDB, and Supabase.
- Rethink indexing, tagging, vocabulary, graph schema, retrieval, traversal, and composition from first principles.
- Treat old-RAG-oriented docs as deprecated context, not as implementation guidance.

Primary steering doc: `docs/architecture/FORK-BOUNDARY.md`

Active implementation package for the next architecture push:
- `docs/build/buildV1.md`
- `docs/build/buildv1/STATE.md`

Current architectural clarification for Build V1:
- the corpus is shared across all tenants
- the graph knowledge layer is shared across all tenants
- tenant separation applies to runtime, sessions, history, permissions and interaction context
- the broader shared corpus for accountants includes at least normative, interpretative, and practical layers
- ET remains an important normative slice, but it is not the whole corpus and should not be treated as shorthand for the complete knowledge base
- all three document families are valuable in their own right; if implementation starts with a graph backbone, the rest of the corpus still has to stay visible and measurable from the first materialization pass

---

## Current Phase

### Phase 0: Repository Bootstrap
- [x] Create GitHub repo `avas888/LIA_Graph`
- [x] Define fork boundary (what to copy vs. build new)
- [x] Create state management docs
- [x] Copy shared modules from Lia_contadores (55 Python files, 298 frontend files, 45 migrations)
- [x] Create dependency manifest
- [x] Initial commit with skeleton (434 files, 94,437 lines)
- [x] Pushed to https://github.com/avas888/LIA_Graph

### Phase 1: Corpus Ingestion & Graph Build (NOT STARTED)
- Bootstrap note: this older phase name is retained for continuity, but the active Build V1 interpretation is broader. The first executable pass must materialize the whole shared corpus under `knowledge_base/` and keep `normativa`, `interpretacion` and `practica` visible in artifacts from day one.
- [ ] Materialize the shared corpus root under `knowledge_base/` with normative, interpretative and practical families
- [ ] Build a corpus inventory artifact so all three families are visible and measurable in the first pass
- [ ] Parse graph-targeted normative authorities → individual ArticleNodes
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
- [ ] Shadow mode (dual-run, log both, serve baseline path)
- [ ] Per-tenant beta toggle
- See: `docs/state/TASK-04-deploy.md`

---

## Shared Surface vs Fresh Design

### COPIED from Lia_contadores (shared, not modified)

These modules are **identical** to the parent repo and must stay in sync:

| Module | Purpose | Why shared |
|--------|---------|------------|
| `platform_auth.py` | JWT auth, token issuance | Auth must be identical |
| `supabase_client.py` | Supabase connection | Same integration surface, different LIA_Graph project/env |
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
| `src/lia_graph/ingestion/parser.py` | Shared corpus inventory + normative ArticleNode extraction |
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

See also: `docs/architecture/FORK-BOUNDARY.md`

---

## External Dependencies Needed

| Service | Purpose | Status | Notes |
|---------|---------|--------|-------|
| **Supabase** (2nd project) | Postgres + pgvector for vectors, sessions, auth tables | NEEDED | Free tier OK for dev |
| **FalkorDB Cloud** | Knowledge graph store | NEEDED | Free tier: 1 graph, 1 GB |
| **OpenAI API** | Embeddings + LLM calls | NEEDED | Same key as Lia_contadores |
| **Railway** | Deployment | LATER | Phase 4 |
| **Dropbox** | Corpus source files | CONNECTED via shared link | Shared accountant corpus families needed: normativa, interpretacion, practica |

---

## Key Design Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-13 | Fork as separate repo, not branch | Clean separation; independent deploy; no risk to production Pipeline C |
| 2026-04-13 | Reuse contracts.py (PipelineCRequest/Response) | Frontend doesn't change; A/B routing via header |
| 2026-04-13 | FalkorDB over Neo4j | Lower latency, better LLM integration, free tier sufficient |
| 2026-04-13 | If bootstrapping starts from a dense normative slice, the shared corpus still must remain visible as normativa + interpretacion + practica in artifacts and docs | avoids letting a narrow bootstrap become the architecture by accident |
| 2026-04-13 | Cloud services over local Docker | Agent can operate autonomously; no local machine dependency |

---

## How to Resume After Crash

1. Read this file (`docs/state/STATE.md`) — it tells you the current phase
2. If working on the new GraphRAG build package, read `docs/build/buildv1/STATE.md`
3. Read the task-specific file for the current phase (e.g., `TASK-01-corpus-ingestion.md`)
4. Each task file has a `## Last Checkpoint` section with exact resumption instructions
5. All intermediate artifacts are saved to `artifacts/` with timestamps
6. All decisions are logged in this file's "Key Design Decisions Log"
