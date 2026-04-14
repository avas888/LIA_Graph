# LIA_Graph

Graph-based RAG pipeline (Pipeline D) for Colombian accounting — inspired by [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Forked selectively from [Lia_contadores](https://github.com/avas888/Lia_contadores). Shares auth, UI, streaming, and contracts. Replaces retrieval and composition with a typed knowledge graph (FalkorDB) over the Estatuto Tributario.

## Architecture

```
Query → Intake (shared) → Topic Router (shared) → Graph Planner (new)
  → FalkorDB Graph Retriever (new) → Subgraph Composer (new)
  → Verifier → Safety (shared) → PipelineCResponse (shared)
```

## Status

See `docs/state/STATE.md` for current progress.

## Docs

- `docs/state/STATE.md` — Master state tracker (start here after any interruption)
- `docs/state/TASK-*.md` — Per-task state with checkpoints
- `docs/architecture/FORK-BOUNDARY.md` — What's shared vs. new
- `docs/DEPENDENCIES.md` — External services needed

## Origin

Analysis documents from the planning phase live in the parent repo:
- [Karpathy Wiki RAG Design](https://github.com/avas888/Lia_contadores/blob/main/docs/perplexity/karpathy-wiki-rag-multitenant-design.md)
- [Parallel RAG Integration Plan](https://github.com/avas888/Lia_contadores/blob/main/docs/perplexity/parallel-rag-integration-plan.md)
- [ET Corpus Graph Suitability Analysis](https://github.com/avas888/Lia_contadores/blob/main/docs/perplexity/et-corpus-graph-suitability-analysis.md)
