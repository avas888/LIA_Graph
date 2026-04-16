# Appendix D — Corpus Audit And Labeling Policy

This appendix is the operational policy for admitting corpus files, labeling them safely, and preventing the old label-first retrieval model from leaking back into Build V1.

## Three-Layer View Of Reality

Build V1 should not collapse everything into one abstract "corpus" bucket. It must distinguish:

- `source_asset_layer`: every scanned file under the corpus roots
- `canonical_corpus_layer`: accountant-facing documents admitted by the audit gate, with pending revisions attached to their base docs
- `reasoning_layer`: graph-parse-ready normative text plus complementary retrieval support drawn from the canonical layer

The audit surface is wider than the parse surface. The parse surface is wider than the graph surface.

## Why This Exists

The previous stack leaned too heavily on `rotulos`, `vocabulario`, `topic`, and `subtopic` as the main narrowing mechanism. That made flat labels do work that really belonged to legal structure, provenance, vigencia, and multi-hop normative relations.

Build V1 starts fresh by changing the load-bearing layer:

- graph structure becomes primary for normative reasoning
- labels remain useful for naming, compatibility, routing hints, and governance
- the full shared corpus remains visible even when only one family is graphized first

## Audit Gate

Phase 2 does not ingest files directly from the source trees without review. Every scanned file, not just markdown, must land in exactly one decision:

- `include_corpus`: accountant-facing document that belongs in the shared corpus
- `revision_candidate`: patch, update, or merge instruction that refers to a base document and must not enter as standalone corpus
- `exclude_internal`: working file, state file, implementation note, deprecated copy, helper artifact, or other non-corpus material

`to upload` is in scope for the same audit gate. It is not auto-admitted and it is not auto-ignored.

## Reconnaissance Gate

Audit alone is not enough. Before the canonical manifest is treated as durably blessed, Phase 2 must materialize a reconnaissance report that reviews the corpus by:

- file archetype
- authority level
- family
- ambiguity flags
- revision linkage

This reconnaissance layer exists to stop the old label-first RAG habit of admitting documents too quickly just because they look routable.

## Family And Knowledge-Class Mapping

The corpus is not ET-only and not normativa-only. The shared accountant corpus must keep these sibling families visible:

- `normativa` -> `normative_base`
- `interpretacion` / `expertos` -> `interpretative_guidance`
- `practica` / `Loggro` -> `practica_erp`

Phase 2 graphizes `normativa` first because reforms, exceptions, definitions, and parameter dependencies are graph-shaped. This is an encoding choice, not a value hierarchy.

## Mandatory Metadata

### Mandatory For Every Scanned File

- `source_origin`
- `source_path`
- `relative_path`
- `extension`
- `text_extractable`
- `parse_strategy`
- `document_archetype`
- `ingestion_decision`
- `decision_reason`

### Mandatory For Every `include_corpus` Document

- `family`
- `knowledge_class`
- `source_type`
- `graph_target`
- `graph_parse_ready`
- `vocabulary_status`

### Mandatory For Every `revision_candidate`

- `base_doc_target` when identifiable
- revision rationale sufficient for a later merge decision

These fields are the minimum needed to reopen the source, explain admission, and keep the corpus measurable without overcommitting to premature taxonomy fit.

## Canonical Layer Policy

`revision_candidate` material does not become standalone corpus evidence. It belongs in the canonical layer as an attachment to a base document when the target is resolvable, or as an unresolved revision queue item when the target is still ambiguous.

This canonical layer exists so the system can keep valuable delta material visible without pretending it has already been merged into clean final text.

The canonical manifest should therefore expose blessing state, not just inclusion state. A document can be admitted to the corpus and still remain `review_required` or `blocked` for canonical blessing.

## Optional Or Supportive Labels

These remain useful, but they are no longer the primary truth model:

- `topic_key`
- `subtopic_key`
- display labels
- synonyms
- keyword tags
- routing cues
- vocabulary anchors used as naming hints

Missing or provisional topic/subtopic labels must not by themselves block corpus admission when the document is otherwise valid.

## Graph-Derived, Not Flat-Labeled

These semantics should be derived from parsing, linking, edge typing, or traversal rather than asserted as simple static labels:

- reform chain membership
- supersedes or repeals
- exception relationships
- requirements and prerequisites
- computation dependencies
- definition relationships
- concept grounding to article nodes
- vigencia across versions
- multi-hop neighborhoods relevant to a query

If graph evidence and flat labels conflict, graph evidence wins for normative reasoning.

## Vocabulary Policy

Use the ratified vocabulary canon as the naming authority when it fits the document.

Keep backward aliases only for runtime compatibility.

Do not force-fit a valid document into an unrelated canonical topic just to satisfy the current vocabulary snapshot. When the domain is real but outside the ratified canon, the document may enter with a custom topic or subtopic marked as pending vocabulary ratification.

## Default Exclusions

Exclude by default unless a human review explicitly promotes them:

- `state.md`
- working `README.md`
- `.DS_Store`
- crawler scripts and helper code
- `deprecated/`
- roadmap notes
- implementation notes
- plain text summaries that are not accountant-facing corpus evidence
- vocabulary governance files that describe the taxonomy but are not corpus evidence themselves

Patch-style markdown such as `PATCH` or `UPSERT` is not standalone corpus. It belongs in `revision_candidate` unless it has already been merged into a stable accountant-facing document.

## Required Audit Artifacts

Before graph interpretation begins, the ingestion pipeline should be able to materialize:

- `artifacts/corpus_audit_report.json`
- `artifacts/corpus_reconnaissance_report.json`
- `artifacts/revision_candidates.json`
- `artifacts/excluded_files.json`
- `artifacts/canonical_corpus_manifest.json`
- `artifacts/corpus_inventory.json`

Graph artifacts build on top of those audit outputs rather than replacing them.

`corpus_reconnaissance_report.json` is the quality gate that tells us whether the canonical manifest is:

- `ready_for_canonical_blessing`
- `review_required`
- `blocked`

Non-markdown or otherwise non-parse-ready assets may still appear in the audit report and canonical manifest. They should remain visible there until a dedicated extractor exists, rather than being forced through the markdown parser path.

## Retrieval Consequence

Planner and retriever behavior should follow this rule:

- labels help choose entry points and lane weights
- graph structure carries normative reasoning when the graph has enough anchors
- interpretive and practical documents remain complementary evidence lanes, not hidden leftovers

This is how Build V1 starts fresh instead of rebuilding the old label-heavy RAG in new packaging.
