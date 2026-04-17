# 01 — Target Architecture

## Architectural Thesis

The target system is a purpose-led GraphRAG architecture with:

- one shared accountant corpus for all tenants
- one shared regulatory graph in FalkorDB built first from the normative backbone of that corpus
- one complementary shared retrieval layer for lexical/vector support when needed
- one multi-tenant runtime layer for sessions, history, permissions, company context and traceability

The graph is the normative reasoning core. Tenant separation belongs to the application runtime, not to the knowledge base.

## Corpus Layers

The shared corpus must be treated as a layered evidence system, not as "ET only":

- `normative_base`: normativa y doctrina oficial que puede convertirse en graph structure or graph-linked authorities
- `interpretative_guidance`: interpretaciones de expertos y proveedores profesionales
- `practica_erp`: guias operativas, walkthroughs y material practico antes llamado "Loggro"

This is not a value hierarchy. Accountants need all three families. Phase 2 graph construction starts with the normative backbone because vigencia, reforma, excepcion, definicion, and parameter dependency are naturally graph-shaped. Interpretative and practical materials must still be inventoried, retrievable, and measurable in the same Phase 2 corpus pass.

Before any graph build or retrieval-support materialization, the system must execute a corpus audit gate over the whole shared corpus root. The audit gate exists to distinguish accountant-facing corpus documents from working files, patch instructions, roadmap notes, crawler utilities, and deprecated mirrors. Phase 2 only graphizes or inventories documents that survive that gate.

After audit admission, the system must execute a reconnaissance quality gate before treating the canonical manifest as durable truth. Admitted documents can still remain `review_required` or `blocked` when authority shape is unclear, revisions are unresolved, or the asset is valuable but not yet trustworthy as reasoning input.

Topic and subtopic naming should follow the ratified vocabulary canon when it fits, while backward aliases remain available for runtime compatibility. If a valid corpus domain falls outside the current ratified vocabulary version, the document may still enter as a custom pending-vocabulary topic rather than being force-fit into the wrong canonical bucket.

## Knowledge Layers

The ingestion and retrieval architecture must distinguish three layers:

- `source_asset_layer`: every scanned file that the audit gate sees
- `canonical_corpus_layer`: accountant-facing documents admitted by the audit gate, with revision candidates attached to their base documents
- `canonical_blessing_state`: review signal over the canonical layer indicating whether documents are ready, require manual review, or are blocked before durable ingestion
- `reasoning_layer`: graph-parse-ready normative text plus complementary retrieval support drawn from the canonical layer

There is also a separate surface-package lane for deterministic UI assets such as
interactive form guides. Those packages may live under `knowledge_base/` for
local runtime convenience, but they are not automatically part of the shared
graph-admission or blessing counts unless they are explicitly promoted into the
canonical corpus workflow.

This separation is critical. The audit surface is wider than the parse surface, and the parse surface is wider than the graph surface.

## Core Components

- `Graph Planner`: selects query mode, entry points, time scope, company context usage, and lane weights
- `Graph Retriever`: walks the regulatory graph for norms, reforms, dependencies, exceptions, parameters, and provenance
- `Shared Retrieval Support`: retrieves complementary passages from the same shared corpus across normative, interpretive, and practical layers when graph evidence alone is insufficient, and keeps non-graphized families first-class in the evidence bundle
- `Runtime Context Layer`: stores sessions, chat runs, permissions, company context and interaction history by tenant
- `Composer`: turns the evidence bundle into an answer with citations and next action
- `Verifier`: enforces grounding, temporal correctness, tenant isolation, and response quality
- `Compiled Cache`: stores selective compiled answers with lineage-aware invalidation, while respecting runtime access and context

## Query Modes

- `local_normative`: direct article, concept, parameter, or reform lookup
- `chain_reasoning`: multi-hop normative traversal
- `contextual_runtime`: regulatory answer shaped by company and interaction context without changing the shared corpus
- `global_pattern`: broad synthesis across many connected clusters
- `fallback_semantic`: vector fallback when graph anchors are weak

## Evidence Contract

Public compatibility remains:

- `PipelineCRequest`
- `PipelineCResponse`
- shared SSE streaming contract

Internal execution should add a graph-native evidence object carrying:

- selected query mode
- selected corpus lanes / knowledge classes
- graph entry points
- graph subgraph
- time filters and vigencia criteria
- shared retrieval support evidence across normativa, interpretacion, and practica
- runtime context evidence
- provenance IDs

## Ingestion Principles

- graph structure is the primary normative truth model; topic and subtopic labels are supportive metadata
- mandatory admission metadata is small and operational: file identity, audit decision, family, knowledge class, source type, graph-target status, and vocabulary status
- admitted assets also need file-shape metadata such as extension, text extractability, parse strategy, and document archetype so the system knows what is inventory-only versus graph-parse-ready
- canonical manifests need reconnaissance metadata such as authority level, source tier, ambiguity flags, revision linkage, and blessing status before they are trusted as durable reasoning inputs
- topic and subtopic labels remain useful but optional at admission time when the domain is valid and the vocabulary fit is still pending
- reform chains, exceptions, requirements, computation dependencies, legal definitions, concept grounding, and vigencia must be derived from graph structure rather than asserted as flat labels
- revision candidates live in the canonical layer as attachments to base docs rather than standalone corpus evidence
- planner and retriever may use labels as hints for entry points and lane weights, but normative reasoning should ride on graph anchors whenever the graph has enough structure

## Operating Constraints

- no tenant-specific corpus partition in v1
- no graph-only retrieval
- no uncited normative answer path
- no default cutover before shadow mode and comparative eval
