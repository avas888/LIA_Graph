# Corpus Guide

## Purpose

This guide explains where the LIA corpus lives, what each root is for, how we materialize a local working snapshot, and how to run the audit-first ingestion flow for Phase 2.

## Source Of Truth

- Dropbox source root: `/Users/ava-sensas/Library/CloudStorage/Dropbox/AAA_LOGGRO Ongoing/AI/LIA_contadores/Corpus`
- Canonical roots we currently ingest:
  - `CORE ya Arriba`
  - `to upload`
  - `to_upload_graph/` — admin drag-to-ingest bucket populated by `POST /api/ingest/intake` (since `v2026-04-20-ui15`)

We intentionally do not ingest the whole Dropbox parent directory in one pass. The parent also contains clearly operational or improvement-only material such as planning notes, self-improvement folders, deprecated upload mirrors, and other non-corpus control files.

## Local Snapshot

- Local snapshot root: `knowledge_base/`
- Snapshot command: `scripts/ingestion/sync_corpus_snapshot.sh`
- Current filtered snapshot size:
  - `knowledge_base/CORE ya Arriba`: 1255 files
  - `knowledge_base/to upload`: 64 files
  - total scanned by the latest ingest run: 1319 files
  - Dropbox source files intentionally left outside the snapshot: 79, all classified as `exclude_internal`

The snapshot is a filtered local copy used for repeatable ingest runs. It is intentionally excluded from git and can be rebuilt from Dropbox at any time.

The sync keeps:

- accountant-facing corpus documents under `CORE ya Arriba`
- candidate revision material under `to upload`

The sync excludes obvious non-corpus/control files such as:

- `.DS_Store`
- `state.md` and `estado.md`
- `README.md` and `README-*`
- gap-analysis and audit-analysis working notes
- vocabulary/governance notes such as `vocabulario-canonico*`
- `CLAUDE.md` and `updator.md`
- self-improvement and improvement-only working folders
- summary text files such as `*resumen*.txt`

The exclusion rule is intentionally conservative: keep revision candidates and real corpus material, strip only files that are clearly working state, governance, or operational scaffolding. As of the latest pass, the snapshot also keeps accountant-facing docs that live under `Documents to branch and improve/`, `to update/`, and `to upload/URLS-PIPELINE-DIAN/`; the audit gate, not the sync filter, now decides whether each of those files is corpus, revision material, or internal control text.

## Corpus Layers

The project uses three distinct layers:

- Source assets: the raw Dropbox material we inherit and curate
- Canonical corpus: the admitted set after audit plus revision linkage
- Graph-parse-ready reasoning inputs: the subset of admitted normative documents that can be parsed into graph structure

`to upload` is important to keep visible because it contains revision candidates and pending additions, but its files are not automatically treated as canonical corpus documents. The Phase 2 audit decides whether each file is:

- `include_corpus`
- `revision_candidate`
- `exclude_internal`

## Corpus Families

The ingest model keeps three evidence families visible from day one:

- `normativa`: legal and normative base documents
- `interpretacion`: expert or interpretative guidance
- `practica`: operational/accounting practice material, often Loggro-oriented

Inside `CORE ya Arriba`, many domains already expose these as sibling folders such as:

- `NORMATIVA`
- `EXPERTOS`
- `LOGGRO`

These are not just filing conventions. They help the audit and inventory step preserve the difference between legal authority, interpretative support, and practical workflow guidance.

## Taxonomy Operations

- The canonical topic taxonomy lives in repo config at `config/topic_taxonomy.json`; the curated subtopic taxonomy lives at `config/subtopic_taxonomy.json` (version `2026-04-21-v2`, **106 subtopics × 39 parent topics** since `v2026-04-21-stv2d`).
- The taxonomy is a living, versioned operational asset; legacy topic keys survive only as aliases. Subtopic entries carry optional `deprecated_aliases` for smooth key renames (Decision `v2026-04-21-stv2d`).
- `config/prefix_parent_topic_map.json` short-circuits filename-prefix → parent-topic inference inside the classifier (e.g., `II-1429-2010` → `impuestos_descontables_iva`; stops mis-routeos documented in the April curator memo).
- `python -m lia_graph.ingest` emits `taxonomy_version`, `topic_key_counts`, `subtopic_key_counts`, and `topic_subtopic_coverage` into the audit, reconnaissance, inventory, revision, and canonical-manifest artifacts.
- Parent/child materialization happens during ingest: direct parent matches keep `subtopic_key = null`, while child matches keep the parent in `topic_key` and materialize the child into `subtopic_key`. The invariant `(topic_key, subtopic_key) ∈ taxonomy.lookup_by_key` is enforced at the classifier boundary (`ingest_subtopic_pass.py`) — orphan pairs are nulled.
- Since `v2026-04-21-stv2b`, the PASO 4 LLM classifier runs **inline in the same ingest invocation**, between audit and sink. `documents.subtema` and Falkor `SubTopicNode` + `HAS_SUBTOPIC` edges land in the same pass — no separate backfill step. `scripts/ingestion/backfill_subtopic.py` is maintenance-only.
- `src/lia_graph/subtopic_taxonomy_builder.validate_no_empty_parents()` raises `EmptyParentTopicError` when a parent topic has zero subtopics (enforced at the end of `promote_subtopic_decisions.main`; bypass via `--allow-empty-parents`).

## Management Workflow

1. Curate or update documents in Dropbox.
2. Keep corpus documents in `CORE ya Arriba`.
3. Put patch, errata, and pending revision work in `to upload`.
4. Keep planning files, state files, and governance notes out of the corpus roots when possible.
5. Rebuild the local snapshot with `scripts/ingestion/sync_corpus_snapshot.sh`.
6. Run the audit-first materializer:
   `make phase2-graph-artifacts PHASE2_CORPUS_DIR=knowledge_base`
7. Review these artifacts first:
   - `artifacts/corpus_audit_report.json`
   - `artifacts/corpus_reconnaissance_report.json`
   - `artifacts/revision_candidates.json`
   - `artifacts/excluded_files.json`
   - `artifacts/canonical_corpus_manifest.json`
8. Only after the audit and reconnaissance review should we treat the run as canonically trustworthy.
9. Then inspect:
   - `artifacts/corpus_inventory.json`
   - `artifacts/parsed_articles.jsonl`
   - `artifacts/raw_edges.jsonl`
   - `artifacts/typed_edges.jsonl`
   - `artifacts/graph_load_report.json`
   - `artifacts/graph_validation_report.json`
10. When taxonomy behavior changes, inspect `taxonomy_version`, `topic_key_counts`, `subtopic_key_counts`, and `topic_subtopic_coverage` before assuming the canon is behaving correctly.
11. Before the cloud runtime (`dev:staging` / production) can serve the refreshed corpus, mirror the same run into Supabase via the sink:
    `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production`

    This is additive to step 6 — artifacts on disk remain authoritative for `npm run dev`. The sink writes `documents`, `document_chunks`, `corpus_generations` (marking one row `is_active=true`), and `normative_edges`; embeddings stay NULL until `embedding_ops.py` runs against the same target. See `docs/guide/env_guide.md#corpus-refresh` for the exact commands and flags.

## Latest Run Status

Latest single-pass ingest on `2026-04-21` (env matrix `v2026-04-21-stv2d`) produced:

- canonical manifest status:
  - `document_count`: 1227
  - `canonical_ready_count`: 1222
  - `review_required_count`: 0
  - `blocked_count`: 5 (binary / derogated / structural manifest assets rejected by the tightened admission gate)
  - `documents_with_pending_revisions`: 0
  - `unresolved_revision_candidate_count`: 0
- reconnaissance gate:
  - status: `ready_for_canonical_blessing`
  - blocker count: 0
  - manual review queue: 0 rows
- taxonomy coverage:
  - `subtopic_taxonomy_version`: `2026-04-21-v2`
  - `topic_key_count` (topics with documents): 42
  - `subtopic_key_count` (subtopics with documents): 93
  - total curated subtopics: 106 across 39 parent topics
  - 6 parent topics are currently empty (surfaced by `validate_no_empty_parents()`; not a blocker for runtime)
- graph validation (`artifacts/graph_validation_report.json`):
  - `ok: true`
  - `node_count`: 2633 (ArticleNode 1301, ReformNode 1316, SubTopicNode 16)
  - `edge_count`: 20495 (REFERENCES 13306, MODIFIES 5243, SUPERSEDES 1186, REQUIRES 364, COMPUTATION_DEPENDS_ON 175, HAS_SUBTOPIC 127, EXCEPTION_TO 66, DEFINES 28)
  - `issues`: 0

Single-pass ingest outcome:

- PASO 4 classifier ran inline across every admitted doc (`ingest_subtopic_pass.py`); `documents.subtema` + Falkor `SubTopicNode` + `HAS_SUBTOPIC` edges landed in the same pass.
- Classifier invariants held: every written `(topic, subtopic)` pair is in `subtopic_taxonomy.lookup_by_key`; orphan LLM keys were dropped; docs with transient classifier failures were flagged `requires_subtopic_review=true` instead of silently dropping.
- Admission gate rejected binaries (`.png/.svg/.jpg/.jpeg/.webp`), form-guides manifest JSONs, and `LEYES/DEROGADAS/` paths per the April curator memo.
- The `v2026-04-21-stv2b` regression (silent 100% NULL `documents.subtema` + 0 `SubTopicNode`s) is caught by `make phase2-graph-artifacts-smoke` against the committed `mini_corpus` fixture before a full re-ingest.

The next operational step is therefore routine maintenance rather than cleanup:

- when a future patch/upsert/errata file appears, merge it into the target doc promptly and archive the standalone revision file under `deprecated/`
- rerun `scripts/ingestion/sync_corpus_snapshot.sh` and `make phase2-graph-artifacts PHASE2_CORPUS_DIR=knowledge_base` after each editorial tranche so the blessing gate stays green

## Practical Rules

- Do not treat every markdown file under Dropbox as corpus.
- Do not store planning or implementation notes inside corpus folders unless they are intentionally meant to be audited and excluded.
- Keep revision instructions explicit so the audit can attach them to a base document.
- Prefer domain folders that separate `NORMATIVA`, `EXPERTOS`, and `LOGGRO` when all three exist.
- If a file is useful operationally but not corpus, keep it outside the ingest roots when possible.

## Corpus Index

The index below describes the filtered snapshot currently used for ingestion.

### Snapshot Roots

- `knowledge_base/CORE ya Arriba`: primary shared corpus by topic/domain, 1255 files
- `knowledge_base/to upload`: pending revision candidates and candidate additions awaiting audit, 64 files

### Domain Index

This index is organized by first-level directories under `knowledge_base/CORE ya Arriba` after filtering.

| Domain | Files | Family folders present |
|------|------:|------|
| `BENEFICIARIO_FINAL_RUB` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `CALENDARIO_TRIBUTARIO_CONSOLIDADO` | 1 | `LOGGRO` |
| `COMERCIAL_SOCIETARIO` | 1 | `-` |
| `CONTRATACION_ESTATAL` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `Corpus de Contabilidad` | 19 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `DESCUENTOS_INVENTARIOS_NIIF` | 2 | `LOGGRO`, `NORMATIVA` |
| `DEVOLUCIONES_SALDOS_FAVOR` | 2 | `EXPERTOS`, `LOGGRO` |
| `DIVIDENDOS_UTILIDADES` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `Documents to branch and improve` | 35 | `-` |
| `ECONOMIA_DIGITAL_PES_CRIPTO` | 1 | `EXPERTOS` |
| `EMERGENCIA_TRIBUTARIA_2026` | 1 | `NORMATIVA` |
| `EXPERTOS_LEYES` | 20 | `-` |
| `FACTURACION_ELECTRONICA_OPERATIVA` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `FIRMEZA_DECLARACIONES_ART714` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `GMF_4X1000` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `ICA_INDUSTRIA_COMERCIO` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `IMPUESTO_PATRIMONIO_PN` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `INFORMACION_EXOGENA_2026` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `INFORMACION_EXOGENA_FORMATOS` | 1 | `LOGGRO` |
| `IVA_CALENDARIO` | 1 | `LOGGRO` |
| `IVA_COMPLETO` | 6 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `LEYES` | 886 | `-` |
| `LOGGRO_LEYES` | 20 | `-` |
| `NIIF_PYMES_3RA_EDICION` | 1 | `EXPERTOS` |
| `NIIF_PYMES_GRUPO2` | 1 | `LOGGRO` |
| `NOMINA_SEGURIDAD_SOCIAL` | 5 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `NORMATIVA_LEYES` | 20 | `-` |
| `NUEVOS-DATOS-BRECHAS-MARZO-2026` | 35 | `-` |
| `OBLIGACIONES_MERCANTILES` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `OBLIGACIONES_PROFESIONALES_CONTADOR` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `PARAFISCAL_ESPECIAL` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `PERDIDAS_FISCALES_ART147` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `PRECIOS_TRANSFERENCIA_SIMPLIFICADO` | 1 | `EXPERTOS` |
| `PROTECCION_DATOS_RNBD` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `REFORMA_LABORAL_LEY_2466` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `REFORMA_PENSIONAL` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `REGIMEN_CAMBIARIO_PYME` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `REGIMEN_SANCIONATORIO` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `RENTA` | 113 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `RENTA_PRESUNTIVA_ART189` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `RETENCION_FUENTE_AGENTE` | 5 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `RST_REGIMEN_SIMPLE` | 2 | `EXPERTOS`, `LOGGRO` |
| `RUT_RESPONSABILIDADES` | 4 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `SAGRILAFT_PTEE` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `to update` | 6 | `-` |
| `TRABAJO_TIEMPO_PARCIAL` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |
| `ZOMAC_INCENTIVOS` | 3 | `EXPERTOS`, `LOGGRO`, `NORMATIVA` |

### Upload Index

`knowledge_base/to upload` should be read as a staging root, not as a guaranteed canonical corpus root.

Typical contents:

- patch files that target an existing base document
- errata
- pending additions that still need audit and family classification

Current upload batches in the filtered snapshot:

| Upload batch | Files |
|------|------:|
| `AGGRANDIZEMENT-ABRIL-2026` | 33 |
| `BRECHAS-SEMANA1-ABRIL-2026` | 7 |
| `BRECHAS-SEMANA2-ABRIL-2026` | 15 |
| `BRECHAS-SEMANA3-ABRIL-2026` | 6 |
| `TRABAJO_TIEMPO_PARCIAL` | 1 |
| `URLS-PIPELINE-DIAN` | 2 |

## Refresh Procedure

When the Dropbox corpus changes:

1. Run `scripts/ingestion/sync_corpus_snapshot.sh` (pulls `CORE ya Arriba` + `to upload` + `to_upload_graph/`).
2. Dry-smoke the canary: `make phase2-graph-artifacts-smoke`.
3. Re-run the full build: `make phase2-graph-artifacts PHASE2_CORPUS_DIR=knowledge_base` (local-only) or `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET={wip|production}` (cloud sink + Falkor load in the same pass).
4. Review the audit, reconnaissance, and subtopic-bindings outputs (`artifacts/corpus_audit_report.json`, `corpus_reconnaissance_report.json`, `canonical_corpus_manifest.json`, `graph_validation_report.json`, plus the `subtopic.graph.bindings_summary` trace in `logs/events.jsonl`) before relying on any downstream graph artifacts.
5. If `docs/guide/env_guide.md`'s `Corpus Refresh` section shows the staging runtime depends on cloud Supabase + cloud Falkor, promote WIP → production via the Promoción surface (`/api/ops/corpus/rebuild-from-wip`) or an explicit `PHASE2_SUPABASE_TARGET=production` rerun.
6. Embeddings are populated on a follow-up pass by `scripts/ingestion/embedding_ops.py` (or chain them automatically via `INGEST_AUTO_EMBED=1` on `POST /api/ingest/run`).
