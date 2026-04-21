# subtopic_generationv1 — Data Contracts (internal)

This file pins the artifact schemas across Phase 2 → 3 → 4 → 6 so parallel
implementation work does not drift. Generated 2026-04-21 during execution.

## Collection JSONL row (Phase 2 output, Phase 3 input)

One line per doc, written to `artifacts/subtopic_candidates/collection_<UTC>.jsonl`.

Fields:
- `collection_batch_id`: str — e.g. `collection_20260421T142200Z`
- `collected_at`: str — ISO-8601 UTC
- `corpus_relative_path`: str — path relative to `knowledge_base/`, e.g. `laboral/NOM-liquidacion.md`
- `doc_id`: str — stable per-(path, content_hash) id, `sha256:<hex>[:16]` of `"<relpath>:<content_hash>"`
- `filename`: str — file basename
- `content_hash`: str — `sha256:<hex>` of raw bytes
- `parent_topic`: str | null — derived from top-level directory under `knowledge_base/`; if absent, the classifier's `detected_topic`
- `autogenerar_label`: str | null — LLM-generated free-form Spanish label (2-5 words)
- `autogenerar_rationale`: str | null
- `detected_topic`: str | null — classifier verdict
- `detected_type`: str | null — `normative_base | interpretative_guidance | practica_erp | null`
- `topic_confidence`: float
- `combined_confidence`: float
- `classification_source`: str — `keywords | filename | llm`
- `is_raw`: bool
- `llm_used`: bool — whether N2 actually fired
- `error`: str | null — exception repr for per-doc failures (row still emitted)

Pointer file: `artifacts/subtopic_candidates/_latest.json`:
```json
{
  "collection_batch_id": "collection_20260421T142200Z",
  "collection_path": "artifacts/subtopic_candidates/collection_20260421T142200Z.jsonl",
  "collected_at": "2026-04-21T14:22:00Z",
  "docs_processed": 1246,
  "docs_failed": 0,
  "total_llm_calls": 1246
}
```

## Proposal JSON (Phase 3 output, Phase 4 input)

One file per mining run: `artifacts/subtopic_proposals_<UTC>.json`.

```json
{
  "version": "2026-04-21-v1",
  "generated_at": "2026-04-21T14:30:00Z",
  "source_collection_paths": ["artifacts/subtopic_candidates/collection_20260421T142200Z.jsonl"],
  "cluster_threshold": 0.78,
  "min_cluster_size": 3,
  "proposals": {
    "laboral": [
      {
        "proposal_id": "laboral::001",
        "proposed_key": "presuncion_costos_independientes",
        "proposed_label": "Presunción de costos para independientes",
        "candidate_labels": ["presuncion_costos_independientes", "costos_presuntos_indep"],
        "evidence_doc_ids": ["sha256:abc123", "..."],
        "evidence_count": 23,
        "intra_similarity_min": 0.81,
        "intra_similarity_max": 0.95
      }
    ]
  },
  "singletons": {
    "laboral": [
      {"label": "foo_unica", "doc_id": "sha256:...", "corpus_relative_path": "laboral/..."}
    ]
  },
  "summary": {
    "total_proposals": 42,
    "total_singletons": 87,
    "parent_topics_with_proposals": 11
  }
}
```

## Decisions JSONL row (Phase 4 output, Phase 6 input)

Append-only `artifacts/subtopic_decisions.jsonl`. Last-write-wins per
`(proposal_id, action)` tuple for idempotency.

```json
{
  "ts": "2026-04-21T14:50:00Z",
  "curator": "admin@lia.dev",
  "parent_topic": "laboral",
  "proposal_id": "laboral::001",
  "action": "accept",
  "final_key": "presuncion_costos_independientes",
  "final_label": "Presunción de costos para independientes",
  "aliases": ["presuncion_costos_ugpp"],
  "merged_into": null,
  "reason": null,
  "evidence_count": 23
}
```

Valid actions: `accept | reject | merge | rename | split`.
- `accept`: final_key + final_label required; aliases optional.
- `reject`: reason required.
- `merge`: merged_into (another proposal_id within same parent_topic) required.
- `rename`: final_label required; final_key may change too.
- `split`: aliases list (2+) required — each becomes its own mini-proposal for re-review in a future mining pass (v1 persists the split intent but does not auto-reprocess).

## Taxonomy JSON (Phase 6 output)

`config/subtopic_taxonomy.json`:

```json
{
  "version": "2026-04-21-v1",
  "generated_from": "artifacts/subtopic_decisions.jsonl",
  "generated_at": "2026-04-21T15:00:00Z",
  "subtopics": {
    "laboral": [
      {
        "key": "presuncion_costos_independientes",
        "label": "Presunción de costos para independientes",
        "aliases": ["presuncion_costos_ugpp", "costos_presuntos_indep"],
        "evidence_count": 23,
        "curated_at": "2026-04-21T14:50:00Z",
        "curator": "admin@lia.dev"
      }
    ]
  }
}
```

Ordering: parent_topic keys sorted alphabetically; subtopics within each
parent sorted by `evidence_count` desc then `key` asc.

## Slug / doc_id derivation

- `doc_id`: `"sha256:" + hashlib.sha256(f"{corpus_relative_path}:{content_hash}".encode()).hexdigest()[:32]`
- `proposal_id`: `f"{parent_topic}::{zero-padded index}"` — stable for given input file
- slug normalization (mining): lowercase → strip accents (NFKD) → replace non-word runs with `_` → strip `_` → stem common Spanish plural/adjective suffixes `_independientes` → `_independiente`, etc.

## Trace event namespace

All script + endpoint events emitted via `lia_graph.instrumentation.emit_event`:
- `subtopic.collect.*` — `start`, `doc.processed`, `doc.failed`, `done`
- `subtopic.mine.*` — `start`, `cluster.formed`, `done`
- `subtopic.curation.*` — `proposals.requested`, `proposals.served`, `decision.recorded`, `decision.rejected_payload`, `evidence.requested`
- `subtopic.promote.*` — `start`, `merge_resolved`, `done`

Full schema ratified in Phase 7 (§13 of the plan).
