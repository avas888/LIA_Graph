# TASK-02: Pipeline D Core

> **Status**: NOT STARTED
> **Depends on**: TASK-01 complete (populated FalkorDB graph)
> **Produces**: Working Pipeline D that answers queries using graph-first retrieval

---

## Last Checkpoint

```
step: 0
description: Task not yet started
next_action: Build graph retriever module
artifacts_produced: none
```

---

## Architecture

```
Query → Intake (shared) → Topic Router (shared) → Graph Planner → Graph Retriever
  → Subgraph Extraction → Composer → Verifier → Safety (shared) → Response
```

### What's Shared with Pipeline C
- Intake (query classification, language detection, safety pre-screen)
- Topic Router (map query to ET domain concepts)
- Safety (content safety post-check)
- Streaming (SSE, StructuredMarkdownStreamAssembler)
- Contracts (PipelineCRequest, PipelineCResponse)
- Telemetry (timing, diagnostics)

### What's New in Pipeline D
- **Graph Planner**: Maps query concepts to graph entry points, decides walk strategy
- **Graph Retriever**: Executes Cypher queries against FalkorDB, extracts relevant subgraph
- **Subgraph Composer**: Generates answer grounded in retrieved subgraph (with edge types as reasoning scaffolding)
- **Compiled Cache**: Pre-computed answers for frequent query patterns, invalidated by graph edge changes

---

## Steps

### Step 1: Graph Client
- FalkorDB connection wrapper
- Cypher query helpers
- Connection pooling + retry logic
- Health check endpoint

### Step 2: Graph Retriever
- Input: list of concept entry points (from Topic Router / Planner)
- Process:
  1. Find matching ArticleNodes by keyword/concept
  2. BFS walk (depth 2-3) following typed edges
  3. Score nodes by relevance (edge type weight × distance decay)
  4. Return top-K ArticleNodes with their connecting edges
- Output: Subgraph (nodes + edges + scores)

### Step 3: Graph Planner
- Input: PipelineCRequest (message, topic, company_context)
- Process:
  1. Extract key concepts from query (LLM-assisted or rule-based)
  2. Map concepts to ArticleNode entry points via:
     - Direct article number mentions ("artículo 336")
     - Concept vocabulary matching ("deducciones" → Art. 105-177)
     - Topic router output → concept mapping table
  3. Decide walk strategy: depth, edge type filters, scoring weights
- Output: Retrieval plan (entry points + strategy)

### Step 4: Subgraph Composer
- Input: Retrieved subgraph + original query
- Process:
  1. Order articles by computation dependency (COMPUTATION_DEPENDS_ON edges)
  2. Build context prompt with:
     - Articles in dependency order
     - Edge types as reasoning hints ("Art. 240-1 is EXCEPTION_TO Art. 240")
     - Supersession annotations ("Art. 336 was MODIFIED by Ley 2277")
  3. Generate answer with citations to specific articles
- Output: PipelineCResponse-compatible answer

### Step 5: Pipeline D Orchestrator
- Wire steps 1-4 together
- Conform to `run_pipeline_c()` signature
- Inject into `_chat_controller_deps()` via header routing
- Handle errors gracefully (fallback to Pipeline C if graph unavailable)

### Step 6: Compiled Answer Cache
- Pre-compute answers for top-100 query patterns (from eval golden set)
- Cache key: normalized query + relevant subgraph hash
- Invalidation: when any ArticleNode in the subgraph's `text_current` changes
  (detected by diff_checksums pipeline)
- Storage: Supabase table `compiled_answers`

---

## Resumption Guide

If this task is interrupted:
1. Check `last_checkpoint.step` above
2. Each step produces a standalone module — partially built modules are safe
3. Steps 1-4 can be tested independently with mock data
4. Step 5 integrates everything — needs steps 1-4 complete
5. Step 6 is optional optimization — Pipeline D works without it
