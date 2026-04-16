# Fork Boundary: Prior Shell → LIA_Graph

> Active steering doc for what we inherit and what we must rethink.

---

## Steering Kernel

LIA_Graph is meant to be a graph-native tax reasoning product shell.

We are not to let the old RAG influence us. Our duty is to think different and RAG with graph.

This repo exists to preserve the mature shell we inherited while building a fundamentally different retrieval and reasoning engine.

---

## What We Reuse

Reuse these as shared product shell layers:
- frontend UX and page surfaces
- auth, tenancy, and RBAC
- HTTP routes and streaming contract
- request/response contracts
- safety and policy boundary checks
- operational shell and general product behavior
- corpus research already gathered

These are inheritance targets because they are product infrastructure, not retrieval ideology.

---

## What We Must Rethink

Rethink these from first principles for graph-native RAG:
- indexing model
- tagging strategy
- vocabulary and concept ontology
- node and edge schema
- graph construction and ingestion flow
- retrieval planning
- traversal heuristics
- evidence assembly
- answer composition
- cache and invalidation strategy

The old chunk-first Pipeline C architecture is not the default mental model here.

The old label-first narrowing model is not the default mental model either. In `LIA_Graph`, `topic`, `subtopic`, and vocabulary labels are supportive metadata. They may help naming, compatibility, and entry-point hints, but they must not become the main substitute for legal structure, provenance, vigencia, reform chains, exceptions, or dependency paths.

---

## Infra Boundary

LIA_Graph keeps its own runtime infrastructure:
- its own Railway deployment
- its own FalkorDB instance
- its own Supabase project

We inherit code shape from the prior shell, not production coupling.

---

## Practical Rule

When making a design choice, ask:

1. Is this product-shell reuse?
2. Or is this an old-RAG assumption sneaking back in?

If it is about retrieval, indexing, tagging, vocab, orchestration, reranking, or evidence assembly, default to fresh graph-first design.

## Ingestion Boundary

When touching corpus ingestion, assume these rules unless the active Build V1 docs explicitly revise them:

- audit the whole source-asset surface before corpus admission
- classify every scanned file as `include_corpus`, `revision_candidate`, or `exclude_internal`
- separate source assets, canonical corpus documents, and reasoning inputs instead of collapsing them into one layer
- keep `normativa`, `interpretacion`, and `practica` visible as sibling corpus families
- keep revision candidates attached to base documents in the canonical layer instead of letting them float as standalone corpus docs
- treat canonical admission and canonical blessing as different moments; review reconnaissance outputs before trusting the manifest as durable reasoning input
- graphize the graph-shaped normative layer first without demoting the other two families
- allow non-markdown or non-parse-ready assets to be inventoried without pretending they are graph-parseable yet
- treat the ratified vocabulary as naming authority, not as a hard gate that forces every valid document into the current canonical buckets
- derive reform, exception, dependency, definition, and vigencia semantics from graph structure rather than from flat labels

---

## Deprecated Guidance

Old-RAG-oriented architecture notes have been quarantined under:

`docs/deprecated/old-RAG/`

Those files may still help as historical context, migration archaeology, or rollback reference, but they are not active steering for implementation.
