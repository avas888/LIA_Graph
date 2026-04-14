# LIA_Graph

Graph-based RAG pipeline (Pipeline D) for Colombian accounting — inspired by [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Forked selectively from [Lia_contadores](https://github.com/avas888/Lia_contadores). Reuses the product shell: frontend, auth, RBAC, streaming, contracts, and shared corpus research. Replaces retrieval and composition with a graph-native reasoning stack over a shared Colombian accountant corpus, where normative materials feed the regulatory graph and interpretive/practical materials remain first-class evidence layers.

## Steering Kernel

LIA_Graph is meant to be "Lia Contador's product shell with a graph-native tax reasoning engine underneath."

We are not to let the old RAG influence us. Our duty is to think different and RAG with graph.

That means:
- Reuse frontend, auth, RBAC, and product shell behavior.
- Reuse corpus research and domain knowledge already gathered.
- Phase 2 must materialize the whole shared corpus view in one pass so `normativa`, `interpretacion`, and `practica` stay visible from day one; the graph starts with the family whose structure fits typed graph relations first.
- Corpus admission is audit-first across the whole source-asset surface: not every file is corpus, and working files or patch instructions must be filtered before inventory or graphization.
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

See `docs/state/STATE.md` for current progress.

## Docs

- `docs/README.md` — Active docs map and reading order
- `AGENT.md` — Repo-level ingestion and retrieval guardrails for future coding sessions
- `docs/state/STATE.md` — Master state tracker (start here after any interruption)
- `docs/architecture/FORK-BOUNDARY.md` — Active steering boundary for what we reuse vs. rethink
- `docs/state/TASK-*.md` — Per-task state with checkpoints
- `docs/DEPENDENCIES.md` — External services needed
- `docs/deprecated/old-RAG/` — Historical docs quarantined so they do not steer current design

## Origin

Historical planning documents from the parent repo may still be useful as archaeology, but they are not active steering for LIA_Graph. If they conflict with the active docs in this repo, the local graph-first docs win:
- [Karpathy Wiki RAG Design](https://github.com/avas888/Lia_contadores/blob/main/docs/perplexity/karpathy-wiki-rag-multitenant-design.md)
- [Parallel RAG Integration Plan](https://github.com/avas888/Lia_contadores/blob/main/docs/perplexity/parallel-rag-integration-plan.md)
- [ET Corpus Graph Suitability Analysis](https://github.com/avas888/Lia_contadores/blob/main/docs/perplexity/et-corpus-graph-suitability-analysis.md)
