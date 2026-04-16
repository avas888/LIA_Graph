# AGENT.md

Repo-level guidance for future coding sessions in `LIA_Graph`.

## Read This Before Touching Ingestion Or Retrieval

If the task touches corpus ingestion, graph build, labeling, routing, retrieval, or FalkorDB integration, read these first:

1. `docs/build/buildv1/STATE.md`
2. `docs/build/buildv1/01-target-architecture.md`
3. `docs/build/buildv1/03-phase-2-shared-regulatory-graph.md`
4. `docs/build/buildv1/appendix-d-corpus-audit-and-labeling-policy.md`
5. `docs/architecture/FORK-BOUNDARY.md`

## Ingestion Principles

### 1. Graph Structure Is Load-Bearing

The old Lia Contadores stack over-relied on `rotulos`, `vocabulario`, `topic`, and `subtopic` as the primary narrowing mechanism.

In `LIA_Graph`, graph structure is the primary truth model for normative reasoning. Labels remain useful, but they are supportive metadata, not the main substrate of legal meaning.

### 2. Audit The Whole Source-Asset Surface Before Ingest

Do not assume every file under the source trees is corpus, and do not assume the audit surface is the same as the parse surface.

Every scanned file must be classified as exactly one of:

- `include_corpus`
- `revision_candidate`
- `exclude_internal`

Patch files, upsert files, implementation notes, `state.md`, crawler helpers, deprecated mirrors, and other working files must not enter the corpus as standalone documents.

The audit surface should include all source assets. The parser may still be narrower than that.

Before treating a run as canonically trustworthy, review `artifacts/corpus_reconnaissance_report.json`. The canonical manifest is not the first quality gate; it is downstream of reconnaissance.

### 3. All Three Corpus Families Are First-Class

The shared accountant corpus has at least three sibling families:

- `normativa` -> `normative_base`
- `interpretacion` / `expertos` -> `interpretative_guidance`
- `practica` / `Loggro` -> `practica_erp`

Phase 2 graphizes `normativa` first because it best fits typed graph structure, not because the other families matter less.

### 4. Three Layers, Not One

Treat the knowledge base as three layers:

- source asset layer: every scanned file we possess
- canonical corpus layer: admitted accountant-facing documents plus pending revision attachment state
- reasoning layer: graph + retrieval support built from canonical documents, not from raw files

Parse surface is narrower than audit surface. Graph surface is narrower than parse surface.

### 5. Mandatory Metadata vs Optional Labels

Mandatory metadata for admitted corpus documents:

- stable file identity: `source_origin`, `source_path`, `relative_path`
- asset form: `extension`, `text_extractable`, `parse_strategy`, `document_archetype`
- audit status: `ingestion_decision`, `decision_reason`
- corpus lane: `family`, `knowledge_class`
- document form: `source_type`
- graph intent: whether the document is graph-targeted in the current phase
- graph parse readiness: whether the current parser can safely graphize it
- vocabulary status: whether any applied topic/subtopic label is ratified or pending

Optional or supportive metadata:

- `topic_key`
- `subtopic_key`
- display labels
- synonyms
- routing hints
- keyword tags
- vocabulary anchors used for naming or compatibility

Do not block corpus admission just because a document lacks a clean canonical topic/subtopic assignment on day one.

Revision candidates belong in the canonical layer as attachments to base documents. They do not become standalone corpus evidence.

The reconnaissance layer must review the corpus by file archetype, authority level, family, ambiguity flags, and revision linkage before any canonical manifest is treated as durably blessed.

### 6. What Must Be Derived From Graph Structure

Do not hand-author or over-trust flat labels for relationships that belong in the graph. These should be derived from parsing, linking, edge typing, or graph traversal:

- reform chains
- supersession or repeal
- exceptions
- requirements and prerequisites
- computation dependencies
- legal definitions
- concept-to-article grounding
- vigencia across versions
- multi-hop normative neighborhoods

If graph evidence and a flat label disagree, the graph evidence wins.

### 7. Vocabulary Is Naming Authority, Not The Bottleneck

Use the ratified vocabulary canon as the naming authority for `topic` and `subtopic` when it fits.

Keep backward aliases only for runtime compatibility.

If a valid corpus domain falls outside the current ratified vocabulary, admit it as a custom pending-vocabulary topic instead of force-fitting it into the wrong bucket.

### 8. Retrieval Consequence

The planner and retriever should use labels as hints for entry points and lane weighting, but normative reasoning should be grounded in graph nodes, edges, provenance, and time scope whenever the graph has enough structure to answer.

Non-markdown or non-parse-ready assets may still be worth auditing and inventorying. Do not pretend they are graph-parseable until an explicit extractor exists.
