# TASK-01: Corpus Ingestion & Graph Build

> **Status**: NOT STARTED
> **Depends on**: Phase 0 complete, FalkorDB credentials, Corpus files in workspace
> **Produces**: Populated FalkorDB graph with ~1,084 ArticleNodes + typed edges

---

## Last Checkpoint

```
step: 0
description: Task not yet started
next_action: Download ET Markdown files from Dropbox, begin article parsing
artifacts_produced: none
```

---

## Steps

### Step 1: Acquire Corpus Files
- Download all 24 ET `.md` files from Dropbox Corpus folder
- Path: `CORE ya Arriba / RENTA / NORMATIVA / Normativa/`
- Also download: `CATALOGO-LEYES-ET.md`, `vocabulario-canonico-v1.md`, `RELACIONES-CROSS-DOMAIN-RECOMENDACIONES.md`
- Save to: `corpus/et/` in this repo

### Step 2: Parse Articles from Markdown
- Input: 24 chapter-level `.md` files
- Output: Individual `ArticleNode` JSON objects
- Parser: `src/lia_graph/ingestion/parser.py`
- Strategy:
  - Split on `## Artículo NNN` boundaries (regex)
  - Extract: article number, heading, full text, parágrafos
  - Handle sub-articles (e.g., 12-1, 240-1) — hyphenated numbering
  - Handle `<Artículo modificado por...>` annotations → reform metadata
  - Handle `<Artículo derogado por...>` → status = derogado
- Validation: total nodes should be ~1,084 ± 50
- Artifact: `artifacts/parsed_articles.jsonl`

### Step 3: Extract Cross-References
- Input: Parsed articles (text field)
- Output: Edge candidates (source_article, target_article, raw_context)
- Linker: `src/lia_graph/ingestion/linker.py`
- Strategy:
  - Regex patterns: `artículo \d+`, `art\. \d+`, `Art\. \d+ E\.T\.`, `numeral \d+ del artículo \d+`
  - Also extract: `Ley \d+ de \d+`, `Decreto \d+`, `Resolución \d+` → ReformNode / DecretoNode candidates
  - Deduplicate: same (source, target) pair → keep richest context
- Validation: expect ~3,000–5,000 raw edge candidates
- Artifact: `artifacts/raw_edges.jsonl`

### Step 4: Classify Edges (LLM-Assisted)
- Input: Raw edge candidates with surrounding text context
- Output: Typed edges (MODIFIES, REFERENCES, EXCEPTION_TO, COMPUTATION_DEPENDS_ON, REQUIRES, DEFINES, SUPERSEDES)
- Classifier: `src/lia_graph/ingestion/classifier.py`
- Strategy:
  - Batch edges in groups of 20
  - Prompt LLM with source article snippet + target article snippet + reference context
  - LLM classifies edge type from fixed taxonomy
  - Confidence threshold: ≥ 0.7 to accept
- Cost estimate: ~2,500 edges × ~500 tokens each = ~1.25M tokens ≈ $2-5 depending on model
- Artifact: `artifacts/typed_edges.jsonl`

### Step 5: Build Supplementary Nodes
- Reform nodes from `CATALOGO-LEYES-ET.md`
- Concept nodes from `vocabulario-canonico-v1.md`
- UVT parameter nodes (hardcoded for 2025/2026 values)
- Artifact: `artifacts/supplementary_nodes.jsonl`

### Step 6: Load into FalkorDB
- Loader: `src/lia_graph/ingestion/loader.py`
- Create graph: `ET_GRAPH`
- Load nodes: ArticleNode, ReformNode, ConceptNode, ParameterNode
- Load edges: all typed edges from Step 4 + structural PART_OF edges
- Validate: node count, edge count, connected components, orphan check
- Artifact: `artifacts/graph_load_report.json`

### Step 7: Validate Graph Quality
- Run test queries against known multi-hop paths:
  - "Art. 336 → Art. 241 → Art. 258-1" (income computation chain)
  - "Art. 115 → Ley 2277 Art. 19" (amendment chain)
  - "Art. 240-1 → Art. 240" (exception relationship)
- Measure: path exists, correct edge types, no broken links
- Artifact: `artifacts/graph_validation_report.json`

---

## Resumption Guide

If this task is interrupted:
1. Check `last_checkpoint.step` above
2. Steps 1-2 are idempotent (re-running is safe)
3. Steps 3-4 produce JSONL artifacts — check last line count vs. expected
4. Step 5 is idempotent
5. Step 6 can be re-run (drops and recreates graph)
6. Step 7 is read-only
