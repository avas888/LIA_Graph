# Corpus Guide

## Purpose

This guide explains where the LIA corpus lives, what each root is for, how we materialize a local working snapshot, and how to run the audit-first ingestion flow for Phase 2.

## Source Of Truth

- Dropbox source root: `/Users/ava-sensas/Library/CloudStorage/Dropbox/AAA_LOGGRO Ongoing/AI/LIA_contadores/Corpus`
- Canonical roots we currently ingest:
  - `CORE ya Arriba`
  - `to upload`

We intentionally do not ingest the whole Dropbox parent directory in one pass. The parent also contains clearly operational or improvement-only material such as planning notes, self-improvement folders, deprecated upload mirrors, and other non-corpus control files.

## Local Snapshot

- Local snapshot root: `knowledge_base/`
- Snapshot command: `scripts/sync_corpus_snapshot.sh`
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

- The canonical topic taxonomy now lives in repo config at `config/topic_taxonomy.json`.
- The taxonomy is a living, versioned operational asset; legacy topic keys survive only as aliases.
- `python -m lia_graph.ingest` now emits `taxonomy_version`, `topic_key_counts`, `subtopic_key_counts`, and `topic_subtopic_coverage` into the audit, reconnaissance, inventory, revision, and canonical-manifest artifacts.
- Parent/child materialization now happens during ingest: direct parent matches keep `subtopic_key = null`, while child matches keep the parent in `topic_key` and materialize the child into `subtopic_key`.

## Management Workflow

1. Curate or update documents in Dropbox.
2. Keep corpus documents in `CORE ya Arriba`.
3. Put patch, errata, and pending revision work in `to upload`.
4. Keep planning files, state files, and governance notes out of the corpus roots when possible.
5. Rebuild the local snapshot with `scripts/sync_corpus_snapshot.sh`.
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

## Latest Run Status

Latest filtered snapshot ingest on `2026-04-16` produced:

- scanned files: 1319
- admitted corpus docs: 1246
- revision candidates: 0
- excluded internal files: 73
- family counts:
  - `normativa`: 1017
  - `interpretacion`: 104
  - `practica`: 125
- canonical manifest status:
  - `canonical_ready_count`: 1246
  - `review_required_count`: 0
  - `blocked_count`: 0
  - `documents_with_pending_revisions`: 0
  - `unresolved_revision_candidate_count`: 0
- reconnaissance gate:
  - status: ready_for_canonical_blessing in the latest materializer run
  - blocker count: 0
  - manual review queue: 0 rows
- taxonomy coverage:
  - `taxonomy_version`: `draft_v1_2026_04_15c`
  - `topic_key_count`: 39
  - remaining ambiguity flags on admitted docs: 0
  - `declaracion_renta`: 47 docs total, 24 docs now split across 9 child subtopics
- graph validation:
  - `ok: true`
  - nodes: 2617
  - edges: 20345
  - issues: 0

Triple-check status on the latest pass:

- the previously filtered accountant-facing docs from `Documents to branch and improve/`, `to update/`, and `to upload/URLS-PIPELINE-DIAN/` are now visible in the canonical layer
- every Dropbox path shared with `knowledge_base` has exact audit parity on decision, family, topic, subtopic, and taxonomy metadata
- there are `0` shared-path label mismatches between Dropbox and the local snapshot
- the prior `18` patch/upsert/errata files were merged into their `17` base docs in Dropbox source and then archived under `deprecated/`, leaving `0` pending revisions and a fully green blessing gate

The next operational step is therefore routine maintenance rather than cleanup:

- when a future patch/upsert/errata file appears, merge it into the target doc promptly and archive the standalone revision file under `deprecated/`
- rerun `scripts/sync_corpus_snapshot.sh` and `make phase2-graph-artifacts PHASE2_CORPUS_DIR=knowledge_base` after each editorial tranche so the blessing gate stays green

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

1. Run `scripts/sync_corpus_snapshot.sh`
2. Re-run `make phase2-graph-artifacts PHASE2_CORPUS_DIR=knowledge_base`
3. Review the audit and reconnaissance outputs before relying on any downstream graph artifacts
