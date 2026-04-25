# TASK-01: Corpus Ingestion & Graph Build

> **Status**: NOT STARTED
> **Depends on**: Phase 0 complete, FalkorDB credentials, Corpus files in workspace
> **Produces**: Shared corpus inventory + populated shared regulatory graph with typed edges

> **Historical note**: This older task file was drafted from an ET-first bootstrap assumption. The active Build V1 package now uses a broader shared accountant corpus model with normative, interpretative, and practical layers. Use this file only if it stays aligned with that model: the first materialization pass must keep all three families visible, even if graph construction starts with normativa.

---

## Last Checkpoint

```
step: 0
description: Task not yet started
next_action: Materialize the shared corpus root under `knowledge_base/`, generate corpus inventory, and begin graph-targeted normative parsing
artifacts_produced: none
```

---

## Design Rule

Task 01 is not "chunking for a better retriever."

It is graph construction:
- extract legal units that deserve node identity
- design edge semantics that capture tax reasoning structure
- build vocabulary and concept anchors that help graph traversal later
- preserve enough provenance to support grounded answers and future graph repair
- keep the non-graphized families visible in inventory and evidence planning from the start

Do not let old document-chunk assumptions decide the graph shape.

---

## Steps

### Step 1: Acquire Shared Corpus Files
- Materialize the accountant corpus under `knowledge_base/`
- Keep at least these families explicit in the path layout:
  - `knowledge_base/normativa/`
  - `knowledge_base/interpretacion/` or `knowledge_base/industry_guidance/`
  - `knowledge_base/practica/`
- Preserve any supporting catalogs, vocabularies, and reform references that help graph construction or evidence assembly
- Do not treat one ET slice as the whole corpus

### Step 2: Inventory The Shared Corpus
- Input: all markdown documents under `knowledge_base/`
- Output: corpus inventory with per-family counts and paths
- Artifact: `artifacts/corpus_inventory.json`
- Rule: `normativa`, `interpretacion`, and `practica` must all remain visible in this artifact from the first pass

### Step 3: Parse Graph-Targeted Normative Authorities
- Input: graph-targeted normative/offical-doctrine `.md` files
- Output: Individual `ArticleNode` JSON objects
- Parser: `src/lia_graph/ingestion/parser.py`
- Strategy:
  - Split on `## Artículo NNN` boundaries (regex)
  - Extract: article number, heading, full text, parágrafos
  - Handle sub-articles (e.g., 12-1, 240-1) — hyphenated numbering
  - Handle `<Artículo modificado por...>` annotations → reform metadata
  - Handle `<Artículo derogado por...>` → status = derogado
- Validation: node counts should be coherent with the normative slice actually materialized
- Artifact: `artifacts/parsed_articles.jsonl`

### Step 4: Extract Cross-References
- Input: Parsed articles (text field)
- Output: Edge candidates (source_article, target_article, raw_context)
- Linker: `src/lia_graph/ingestion/linker.py`
- Strategy:
  - Regex patterns: `artículo \d+`, `art\. \d+`, `Art\. \d+ E\.T\.`, `numeral \d+ del artículo \d+`
  - Also extract: `Ley \d+ de \d+`, `Decreto \d+`, `Resolución \d+` → ReformNode / DecretoNode candidates
  - Deduplicate: same (source, target) pair → keep richest context
- Validation: expect dense reference coverage for the normative slice actually loaded
- Artifact: `artifacts/raw_edges.jsonl`

### Step 5: Classify Edges (LLM-Assisted)
- Input: Raw edge candidates with surrounding text context
- Output: Typed edges (MODIFIES, REFERENCES, EXCEPTION_TO, COMPUTATION_DEPENDS_ON, REQUIRES, DEFINES, SUPERSEDES)
- Classifier: `src/lia_graph/ingestion/classifier.py`
- Strategy:
  - Batch edges in groups of 20
  - Prompt LLM with source article snippet + target article snippet + reference context
  - LLM classifies edge type from fixed taxonomy
  - Confidence threshold: ≥ 0.7 to accept
- Cost estimate: depends on the normative slice chosen for the first graph pass
- Artifact: `artifacts/typed_edges.jsonl`

### Step 6: Build Supplementary Nodes
- Reform nodes from available normative catalogs
- Concept nodes from canonical vocabulary files when available
- Parameter nodes (for example UVT and other structured fiscal parameters) when they materially affect traversal
- Artifact: `artifacts/supplementary_nodes.jsonl`

### Step 7: Load into FalkorDB
- Loader: `src/lia_graph/ingestion/loader.py`
- Create graph: `LIA_REGULATORY_GRAPH`
- Load nodes: ArticleNode, ReformNode, ConceptNode, ParameterNode
- Load edges: all typed edges from Step 5 + structural PART_OF edges
- Validate: node count, edge count, connected components, orphan check
- Artifact: `artifacts/graph_load_report.json`

### Step 8: Validate Graph Quality
- Run test queries against known multi-hop paths:
  - dense normative chains from the first graph-targeted slice
  - amendment chains
  - exception relationships
- Measure: path exists, correct edge types, no broken links
- Artifact: `artifacts/graph_validation_report.json`
- Rule: validation is not only about graph health; confirm the corpus inventory still reflects all three families so later phases do not pretend the corpus is only what fit the graph first

---

## Resumption Guide

If this task is interrupted:
1. Check `last_checkpoint.step` above
2. Steps 1-2 are idempotent (re-running is safe)
3. Steps 3-4 produce JSONL artifacts — check last line count vs. expected
4. Step 5 is idempotent
5. Step 6 can be re-run (drops and recreates graph)
6. Step 7 is read-only
