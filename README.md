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

See `docs/build/buildv1/NEXT.md` for the short "what we do next" sheet, `docs/build/buildv1/STATE.md` for durable Build V1 implementation state, and `docs/state/STATE.md` for the broader repo ledger.

## Dev Commands

- `npm run dev`
  Runs the local UI server after preflighting the repo, rebuilding the public UI bundle, forcing `LIA_STORAGE_BACKEND=filesystem`, and checking a local Docker FalkorDB on `redis://127.0.0.1:6389`.
- `npm run dev:staging`
  Runs the same local UI server after preflighting the repo, rebuilding the public UI bundle, forcing `LIA_STORAGE_BACKEND=supabase`, and checking the cloud FalkorDB + cloud Supabase credentials from your env files.
- `npm run dev:check`
  Runs the local preflight only.
- `npm run dev:staging:check`
  Runs the staging-backed preflight only.

Notes:
- The current GUI/chat runtime is still artifact-backed for `pipeline_d`, so FalkorDB is preflighted for environment parity and graph ops rather than serving the live chat answer path directly.
- Local dev intentionally uses filesystem persistence to avoid depending on cloud Supabase for everyday browser testing.

## Docs

- `docs/README.md` — Active docs map and reading order
- `AGENT.md` — Repo-level ingestion and retrieval guardrails for future coding sessions
- `docs/build/buildv1/NEXT.md` — Rolling next-step sheet for the active Build V1 package
- `docs/build/buildv1/STATE.md` — Durable Build V1 implementation ledger
- `docs/state/STATE.md` — Broader repo state tracker and older phase bridge
- `docs/architecture/FORK-BOUNDARY.md` — Active steering boundary for what we reuse vs. rethink
- `docs/state/TASK-*.md` — Per-task state with checkpoints
- `docs/DEPENDENCIES.md` — External services needed
- `docs/deprecated/old-RAG/` — Historical docs quarantined so they do not steer current design

## Origin

Historical planning documents from the earlier shell can still be useful as archaeology, but they are not active steering for LIA_Graph. If they conflict with the active docs in this repo, the local graph-first docs win.
