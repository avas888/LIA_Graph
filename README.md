# LIA_Graph

Graph-based RAG pipeline (Pipeline D) for Colombian accounting — inspired by [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Built from a selectively inherited product shell: frontend, auth, RBAC, streaming, contracts, and shared corpus research. Retrieval and composition are being replaced with a graph-native reasoning stack over a shared Colombian accountant corpus, where normative materials feed the regulatory graph and interpretive/practical materials remain first-class evidence layers.

## Steering Kernel

LIA_Graph is meant to be a graph-native tax reasoning product shell.

We are not to let the old RAG influence us. Our duty is to think different and RAG with graph.

That means:
- Reuse frontend, auth, RBAC, and product shell behavior.
- Reuse corpus research and domain knowledge already gathered.
- Phase 2 must materialize the whole shared corpus view in one pass so `normativa`, `interpretacion`, and `practica` stay visible from day one; the graph starts with the family whose structure fits typed graph relations first.
- Corpus admission is audit-first across the whole source-asset surface: not every file is corpus, and working files or patch instructions must be filtered before inventory or graphization.
- Canonical trust is reconnaissance-gated: admission into the canonical layer is not the same as blessing a document set as durable graph/retrieval input.
- The ingestion architecture now distinguishes source assets, canonical corpus documents, and graph-parse-ready reasoning inputs; parse surface is narrower than audit surface, and graph surface is narrower than parse surface.
- `topic` and `subtopic` are supportive metadata, not the primary normative truth model; reforms, exceptions, dependencies, definitions, and vigencia belong in graph structure.
- Do **not** inherit old assumptions for indexing, tagging, vocab design, retrieval, reranking, chunk orchestration, or cache strategy just because they existed in Pipeline C.
- Treat old-RAG docs as historical context only, not active steering.

## Architecture

```
Query → Intake (shared) → Topic Router (shared) → Graph Planner (new)
  → FalkorDB Graph Retriever (new) → Subgraph Composer (new)
  → Verifier → Safety (shared) → PipelineCResponse (shared)
```

## Status

Build V1 Phases 1–3 are live: the graph is green, `pipeline_d` is the served default, `dev:staging` walks cloud Supabase + cloud FalkorDB on every request, and the corpus sink + Gemini embeddings round-trip through one `make phase2-graph-artifacts-supabase` run. See `docs/guide/orchestration.md` (env matrix + change log) for the authoritative live-state map, and `docs/state/STATE.md` for the broader repo ledger.

## Dev Commands

- `npm run dev`
  Runs the local UI server after preflighting the repo, rebuilding the public UI bundle, setting `LIA_CORPUS_SOURCE=artifacts` + `LIA_GRAPH_MODE=artifacts`, and checking the local Docker FalkorDB on `redis://127.0.0.1:6389` plus the local Supabase stack on `127.0.0.1:54321`. Storage backend is always `supabase` (the filesystem backend was removed with the April 2026 env cut).
- `npm run dev:staging`
  Runs the same local UI server against cloud infrastructure — sets `LIA_CORPUS_SOURCE=supabase` + `LIA_GRAPH_MODE=falkor_live`. The orchestrator routes retrieval through `retriever_supabase.py` (chunks) and `retriever_falkor.py` (graph BFS) on every request. A `FalkorDB node_count ≥ LIA_FALKOR_MIN_NODES` gate blocks boot when the cloud graph is empty.
- `npm run dev:production`
  Exits with a Railway notice — production is deployed via `railway up`, not locally.
- `npm run dev:check` / `npm run dev:staging:check`
  Preflight only.

Notes:
- Every `PipelineCResponse.diagnostics` carries `retrieval_backend` + `graph_backend` (and `retrieval_sub_topic_intent` when the planner detects a curated subtopic) so you can confirm which adapter served a turn without guessing.
- Optional post-assembly polish is gated by `LIA_LLM_POLISH_ENABLED` (default `1`); the deterministic template answer remains the safety net and polish failures surface in `response.llm_runtime.skip_reason`.

## Docs

- `docs/guide/orchestration.md` — End-to-end live runtime map + authoritative env matrix & change log (read this first)
- `docs/guide/chat-response-architecture.md` — How the `main chat` answer is shaped
- `docs/guide/env_guide.md` — Run modes, env files, migration baseline, test accounts, corpus refresh
- `docs/guide/corpus.md` — Corpus layers, ingestion audit gate, latest run stats
- `AGENTS.md` — Canonical operating guide for AI agents (mirrors of the env matrix)
- `docs/README.md` — Active docs map and reading order
- `docs/architecture/FORK-BOUNDARY.md` — Steering boundary for what we reuse vs. rethink
- `docs/state/STATE.md` — Broader repo state tracker
- `docs/DEPENDENCIES.md` — External services needed
- `docs/next/decouplingv1.md` — Forward-looking plan for the last two oversized modules
- `docs/done/` — Executed task records (subtopic generation v1, ingestfix v1 + v2, corpus cutover, curator decisions)
- `docs/deprecated/old-RAG/` — Historical material quarantined so it does not steer current design

## Origin

Historical planning documents from the earlier shell can still be useful as archaeology, but they are not active steering for LIA_Graph. If they conflict with the active docs in this repo, the local graph-first docs win.
