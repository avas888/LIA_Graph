# Ingestion Fix v2 — Full Reingest Implementation Plan

**Status:** DRAFT — awaiting operator sign-off. Do NOT begin coding until this doc is approved.
**Owner:** Lia_Graph engineering.
**Created:** 2026-04-23.
**Companion:** `docs/next/ingestfixv1-design-notes.md` (historical).

---

## §0 Cold-Start Briefing

*Everything a fresh LLM needs to pick this up with zero conversation context. Read top-to-bottom before any action.*

### 0.1 What Lia_Graph is

Lia_Graph is a **graph-native RAG product** serving Colombian SMB accountants. Natural-language Q&A over a curated legal + operational corpus; answers cite inline. Backend: Python. Frontend: Vite + TypeScript. Storage: Supabase (Postgres + pgvector) for `documents` / `document_chunks` / `normative_edges`; FalkorDB for regulatory-graph overlay. Classification: Gemini. Embeddings: OpenAI-compatible provider via `embedding_ops.py`.

### 0.2 Repo layout (essentials only)

| Path | Purpose |
|---|---|
| `src/lia_graph/` | Python backend. |
| `src/lia_graph/ingest.py` | Full-ingest entry point (CLI: `lia-graph-artifacts`). |
| `src/lia_graph/ingestion/` | Parser, delta planner, Supabase sink, FalkorDB loader, edge extractor. |
| `src/lia_graph/pipeline_d/` | Served runtime (retriever / planner / orchestrator / synthesis / assembly). |
| `src/lia_graph/ui_*.py` | HTTP handlers fan-out from `ui_server.py`. |
| `src/lia_graph/ui_ingest_delta_controllers.py` | Phase-8 admin delta endpoints. |
| `frontend/src/app/` | App shells per surface (`ingest`, `ops`, `chat`, `orchestration`, `subtopics`). |
| `frontend/src/features/` | Feature modules (`ingest/`, `ops/`, `subtopics/`, `admin/`). |
| `frontend/src/shared/ui/{atoms,molecules,organisms}/` | Atomic-design component library. |
| `config/topic_taxonomy.json` | 50-entry topic catalog (`draft_v1_2026_04_15c`). |
| `config/subtopic_taxonomy.json` | 106-entry subtopic catalog (frozen at 2026-04-21T15:07:13Z). |
| `supabase/migrations/` | Squashed baseline + post-baseline migrations. |
| `knowledge_base/` | ~1,287 live `.md` files. Corpus source on disk. |
| `artifacts/` | Built corpus bundle (dev mode serves from here). |
| `tests/` | Pytest. **Run only via `make test-batched`** (conftest aborts on > 20 files without `LIA_BATCHED_RUNNER=1`). |
| `evals/` | Retrieval / gold benchmarks. |
| `docs/guide/orchestration.md` | **Canonical** runtime map + versioned env/flag matrix. Reconcile code to this doc, never the reverse. |
| `docs/guide/chat-response-architecture.md` | Main-chat answer shape. |
| `docs/guide/env_guide.md` | Run modes, env files, test accounts, corpus refresh. |
| `AGENTS.md`, `CLAUDE.md` | Repo operating guides. |
| `logs/events.jsonl` | Append-only structured event log (server-side). |

### 0.3 Tooling

- **Python:** `uv` (not pip). Every command: `PYTHONPATH=src:. uv run --group dev python <...>`.
- **Node:** `npm` against `frontend/` via root scripts (`npm run frontend:build` etc.).
- **DB local:** `make supabase-start` / `supabase-stop` / `supabase-reset` / `supabase-status`. After reset: `PYTHONPATH=src:. uv run python scripts/seed_local_passwords.py` (every `@lia.dev` user → password `Test123!`).
- **Dev modes:** `npm run dev` (artifacts on disk + local docker), `npm run dev:staging` (cloud Supabase + cloud FalkorDB), `npm run dev:production` (Railway). Launcher `scripts/dev-launcher.mjs` owns env flags — **do not hardcode `LIA_CORPUS_SOURCE` / `LIA_GRAPH_MODE` in `.env.local`**.
- **Full corpus rebuild:** `make phase2-graph-artifacts` (local artifacts) / `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` (cloud).
- **Test runs:** `npm run test:health` (golden), `npm run test:health:fast` (skip e2e), single py file `PYTHONPATH=src:. uv run pytest tests/test_x.py -q`, full suite `make test-batched`.
- **Evals:** `make eval-c-gold`, `make eval-c-full`.
- **Preflight only:** `make smoke-deps`, `npm run dev:check`.

### 0.4 Auth + env

- Cloud Supabase target name `production` → credentials come from `.env.production` (NOT committed). Accessed via `create_supabase_client_for_target("production")` from `src/lia_graph/supabase_client.py`.
- Admin UI uses bearer-token auth (session stored in localStorage). SSE endpoints must fall back to polling because EventSource can't send Authorization header.
- Local tests: default `@lia.dev` users; seed via `scripts/seed_local_passwords.py`.
- **Lineage:** Lia_Graph is branched from Lia_Contador. DO NOT mutate `LIA_contadores` cloud resources — this repo evolves separately.

### 0.5 Test data + fixtures

- Canonical corpus live on disk at `knowledge_base/`.
- Three reference doc shapes for parser tests:
  - `knowledge_base/CORE ya Arriba/Corpus de Contabilidad/NORMATIVA/N-INC-impuesto-nacional-consumo.md` — classic normativa, 16 `## Art.` headers.
  - `knowledge_base/retencion_en_la_fuente/RET-N03-decreto-572-2025-agentes-bases-tarifas.md` — v2-template normativa (no article headers, many `## H2` sections).
  - `knowledge_base/retencion_en_la_fuente/RET-E02-decreto-572-vs-art368-interpretaciones.md` — interpretación doc, mostly placeholder sections.
- Evals ground-truth: `evals/` (see `make eval-c-gold` threshold 90).

### 0.6 Glossary

| Term | Meaning |
|---|---|
| **Generation** (`gen_<UTC>` or `gen_active_rolling`) | A versioned snapshot of the corpus in Supabase. One row in `corpus_generations`; `is_active=true` flips atomically via `promote_generation()` RPC. |
| **Rolling generation** | Whichever generation currently has `is_active=true`. Additive deltas land here. |
| **Delta** (`delta_<UTC>_<rand>`) | A diff (added/modified/removed docs) applied to the rolling gen by the Phase-8 admin UI. |
| **Chunk** | A row in `document_chunks`. Primary retrieval unit. `chunk_id = <doc_id>::<article_key>`. One chunk per parsed article (or section / whole-doc via fallback). |
| **Doc fingerprint** | `sha256(content_hash || canonical_classifier_json)`. Persisted on `documents.doc_fingerprint` for delta diffing. |
| **Content hash** | `sha256(markdown)`. Persisted on `documents.content_hash`. Drives the content-hash shortcut in delta planning. |
| **PASO 4 classifier** | Gemini-based subtopic classifier in `ingest_subtopic_pass.py`. Rate-limited ~1 doc/sec. |
| **`graph_parse_ready`** | Boolean flag on `CorpusDocument`; true when `family=normativa` AND `parse_strategy=markdown_graph_parse`. Gates article extraction. |
| **Article key** | Slug identifying a chunk within its doc. Numeric (`"512-1"`) for statutory articles, section slug (`"regla-operativa-para-lia"`) for fallback sections, `"doc"` for whole-doc fallback. |
| **Orphan doc** | A row in `documents` with zero matching rows in `document_chunks`. Invisible to retrieval. |
| **Family** | Corpus-level classification: `normativa`, `practica`, `interpretacion`, `expertos`. Derived by filename prefix + heuristics in `ingest_classifiers.py`. |
| **Tags** | Umbrella for `topic` + `subtema` + `authority` + `source_type`. Stored on `documents` row and propagated to `document_chunks`. |

### 0.7 Source-of-truth pointers

- Runtime semantics → `docs/guide/orchestration.md`.
- Hot path (main chat) → §Hot Path in `CLAUDE.md`.
- Decision log for additive-corpus-v1 → `docs/next/additive_corpusv1.md`.
- Surface boundaries (main chat vs normativa vs interpretación) → `AGENTS.md` + `CLAUDE.md`.
- Layered repo rules → `AGENTS.md`.

### 0.8 Design-skill invocation

When the work includes a **visible frontend surface** (new panel, new tab, new organism), invoke the `frontend-design:frontend-design` skill with a precise brief before touching shared/ui/. Skill location: `~/.claude/plugins/cache/claude-plugins-official/frontend-design/`. Keeps atomic-discipline guard (`frontend/tests/atomicDiscipline.test.ts`) green — no raw hex, no inline SVG outside `shared/ui/icons.ts`, tokens-only CSS.

### 0.9 Git conventions

- Branch per phase: `feat/ingestionfix-v2-phase<N>-<slug>`.
- Commit messages in imperative Spanish or English, scoped: `feat(ingestion): …` / `fix(parser): …` / `chore(docs): …`.
- One PR per phase, merged via squash. Main is always deployable.
- **Never** run `git push --force` against `main`. **Never** use `--no-verify`.
- Full suite never in one process — `make test-batched` only.

### 0.10 Non-negotiables (from `CLAUDE.md`)

- Never inherit old-RAG assumptions from `docs/deprecated/`.
- Falkor adapter propagates errors; no silent artifact fallback on staging.
- `PipelineCResponse.diagnostics` always carries `retrieval_backend` + `graph_backend`.
- Doc + code + `/orchestration` HTML map stay aligned. Env-flag matrix bump = same task as the code change.

---

## §1 Problem summary (TL;DR)

On 2026-04-23 the operator ran a Phase-8 additive delta that completed cleanly but wrote 0 chunks and 0 edges for 53 added docs. Root-cause: the markdown parser assumed every graph-parseable doc contains `## Artículo N` statutory headers. Audit of cloud Supabase: **1,152 of 1,287 docs (89.5 %) are orphan — present in `documents` but absent from `document_chunks`**. The corpus has been serving retrieval on ~10 % of its nominal surface.

Parser fix (section-level H2 + whole-doc fallback) is already in tree at `src/lia_graph/ingestion/parser.py`. It is **NOT yet deployed** — the cloud corpus still reflects the pre-fix pipeline. This plan ships the fix end-to-end: adjacent cleanup + full rebuild + embedding backfill + atomic promotion + verification.

Three dimensions need attention beyond chunks:

1. **Graph:** non-normativa docs need to enter FalkorDB with typed edges (`PRACTICA_DE`, `INTERPRETA_A`, `MENCIONA`) plus thematic edges to topic/subtopic nodes (`TEMA`, `SUBTEMA`).
2. **Tags:** 2,523 events in `logs/events.jsonl` carry `requires_subtopic_review=true`. No UI surfaces these. A new `Tags` admin tab with an LLM-backed report is required.
3. **Catalog freshness:** all 106 subtopic entries have `curated_at: 2026-04-21T15:07:13Z` — the catalog is frozen. Many reingested docs will classify with `null` subtopic unless the miner runs fresh.

---

## §2 Scope + phasing overview

Twelve phases. Each is independently shippable and leaves the system in a consistent state. Phases 1–8 are preparation; Phase 9 is the cloud rebuild; Phases 10–12 are verification + cosmetic cleanup.

| # | Phase | Deliverable |
|---|---|---|
| 1 | Parser fallback + unit coverage | Ship parser fix (already partial) + full test suite. |
| 2 | Chunk `source_type` semantics | Per-chunk source_type derivation in sink. |
| 3 | Topic null coercion (path-inferred) | Fallback topic from filename path when classifier returns null. |
| 4 | Edge extraction gating + typed edges | `MODIFICA`/`DEROGA`/`CITA` only for normativa; `PRACTICA_DE`/`INTERPRETA_A`/`MENCIONA` for others; weights. |
| 5 | Thematic graph edges (TEMA / SUBTEMA) | Topic + subtopic nodes in FalkorDB; edges from every chunk. |
| 6 | `doc_fingerprint` persistence on sink | Sink writes the column; drop reliance on `scripts/backfill_doc_fingerprint.py`. |
| 7a | `Tags` admin endpoints (backend only) | Migration + 5 HTTP endpoints + LLM report builder + sink skeleton-insert. **Frontend deferred → 7b.** |
| 7b | `Tags` admin tab (frontend) | New tab in Ops shell; curation UI for the 7a endpoints. **Deferred to follow-up.** |
| 8 | Subtopic-miner (partial pass: `laboral` only; 38 topics cataloged for overnight batch) | Taxonomy unchanged (current 106-entry snapshot deemed fresh for Phase 9). See §4 Phase 8 for the punted topic list. |
| 9 | Full cloud reingest + embeddings + promotion | The CLI sequence in §5 below. |
| 10 | Verification + smoke | Coverage query + retrieval smoke + e2e chat. |
| 11 | UI terminal-banner field-path fix | Cosmetic. |
| 12 | Close-out | Handoff notes + env matrix bump. |

Out of scope: reranker changes, retriever weighting tuning (covered in `docs/next/structuralwork_v*.md`), new corpus content (covered in `docs/next/commission_dian_procedure_slate.md`).

---

## §3 Pre-flight checklist (run before Phase 1)

- [ ] `git status` clean on `main`.
- [ ] `npm run dev:check` and `npm run dev:staging:check` both pass.
- [ ] `make smoke-deps` passes.
- [ ] Cloud Supabase `production` target reachable: `PYTHONPATH=src:. uv run --group dev python -c "from lia_graph.supabase_client import create_supabase_client_for_target; c = create_supabase_client_for_target('production'); print(c.table('documents').select('doc_id', count='exact').execute().count)"` returns 1,287 (± new deltas).
- [ ] `logs/events.jsonl` tail accessible.
- [ ] FalkorDB `LIA_REGULATORY_GRAPH` reachable via the adapter smoke: `PYTHONPATH=src:. uv run --group dev python -c "from lia_graph.graph_client import probe_falkor; probe_falkor()"` (or the equivalent probe entry-point in the repo; grep `def probe_falkor` to locate).
- [ ] Baseline snapshot of orphan counts captured (**the "before" number**): `docs: 1287 / chunks: 2073 / orphans: 1152`. Record into §7 state ledger.

---

## §4 Phases

Each phase has identical sub-structure: **Goal**, **Files**, **Tests**, **Acceptance**, **State log** (populated as work progresses — this is the "state aware" field).

---

### Phase 1 — Parser fallback + unit coverage

**Goal.** Ship the two-tier parser fallback so any doc without `## Artículo N` headers produces retrievable chunks. Fix is already in tree; this phase adds the tests that lock the behavior in.

**Files — modify.**
- `src/lia_graph/ingestion/parser.py` — already modified; validate final shape (H2 section fallback + whole-doc fallback, metadata-section skip, empty-placeholder skip).

**Files — create.**
- `tests/test_ingestion_parser.py` — new. Cases:
  - `test_classic_normativa_unchanged` — `N-INC…` → 16 articles.
  - `test_v2_template_section_chunks` — `RET-N03…` → 2 chunks (non-empty sections only), `article_key` slugs match headings.
  - `test_v2_placeholder_only_produces_identificacion_chunk` — `RET-E02…` → 1 chunk.
  - `test_empty_markdown_returns_empty` — `""` → `()`.
  - `test_duplicate_section_headings_get_index_suffix` — synthetic markdown with two `## Identificacion` sections.
  - `test_metadata_v2_section_is_skipped` — `## Metadata v2` does not produce a chunk.
  - `test_article_key_uniqueness_under_fallback` — chunk_id formula never collides.

**Tests — run.**
- `PYTHONPATH=src:. uv run pytest tests/test_ingestion_parser.py -q`

**Acceptance.**
- All 7 cases pass.
- `make test-batched` still green.
- No existing test regressed (grep `parse_articles` usage across `tests/` and re-run those files individually).

**State log.**
```
status: pending
started_at:
completed_at:
branch:
commit:
tests_added: [ ]
tests_passing: [ ]
notes:
```

---

### Phase 2 — Chunk `source_type` semantics

**Goal.** Derive `source_type` per chunk based on `article_key` shape, so downstream filtering / ranking can tell statutory articles, prose sections, and whole-doc chunks apart.

**Files — modify.**
- `src/lia_graph/ingestion/supabase_sink.py` — `write_chunks` (~line 344). Replace hardcoded `"source_type": "article"` with a derivation:

  ```python
  def _derive_source_type(article_key: str, article_number: str) -> str:
      if article_number and article_key == article_number:
          return "article"
      if article_key == "doc":
          return "document"
      return "section"
  ```
- `src/lia_graph/pipeline_d/retriever_supabase.py` — confirm `hybrid_search` / filters do not hard-exclude `source_type in {"section", "document"}`. If they do, widen.

**Files — create.**
- None.

**Tests — add to `tests/test_ingestion_supabase_sink.py`.**
- `test_chunk_source_type_numeric_article_key` — numeric article_key → `"article"`.
- `test_chunk_source_type_slug_section_key` — slug key like `"identificacion"` → `"section"`.
- `test_chunk_source_type_whole_doc_key` — `"doc"` → `"document"`.

**Tests — run.**
- `PYTHONPATH=src:. uv run pytest tests/test_ingestion_supabase_sink.py -q`
- `PYTHONPATH=src:. uv run pytest tests/test_retriever_supabase*.py -q` (if any exist) to confirm no retrieval regression.

**Acceptance.**
- 3 new sink tests pass.
- Retriever smoke returns hits with mixed `source_type` values.

**State log.** *(identical template to Phase 1)*

---

### Phase 3 — Topic null coercion from path

**Goal.** When the classifier returns `topic=null`, infer topic from the disk path (first segment of `relative_path`) before falling back to `"unknown"`. Avoids tag-null docs being silently unfilterable.

**Files — modify.**
- `src/lia_graph/ingest_classifiers.py` — post-classifier hook: if `topic_key is None`, derive from `path.parts[0]` cross-referenced against `topic_taxonomy.json` aliases. Only override when the path-inferred topic is a known taxonomy key.
- `src/lia_graph/ingest_subtopic_pass.py` — ensure the post-hook runs before `subtopic.ingest.classified` event is emitted.

**Files — create.**
- None.

**Tests — add to `tests/test_ingest_classifiers.py` (create if absent).**
- `test_path_inferred_topic_when_classifier_returns_null` — mock classifier returning null, assert topic = `"retencion_en_la_fuente"` for a `retencion_en_la_fuente/X.md` path.
- `test_path_inferred_topic_respects_taxonomy_aliases` — `declaracion_renta/...` maps to `declaracion_renta` key.
- `test_path_inferred_topic_unknown_folder_returns_none` — unknown top-level folder → topic stays null (no false positive).

**Tests — run.**
- `PYTHONPATH=src:. uv run pytest tests/test_ingest_classifiers.py -q`

**Acceptance.**
- All cases pass.
- Re-classifying the 53 docs from the 2026-04-23 delta (via a dry-run) shows `topic != null` for every path whose folder matches a taxonomy key.

**State log.** *(template)*

---

### Phase 4 — Edge extraction gating + typed edges

**Goal.** Differentiate authoritative statutory references (normativa → normativa) from operational / interpretive references (práctica → normativa, expertos → normativa) in the graph. Add `MENCIONA` for casual prose references with explicit low weight.

**Files — modify.**
- `src/lia_graph/ingestion/edge_extractor.py` — extend `extract_edge_candidates` and `classify_edge_candidates`:
  - Input: list of `ParsedArticle` + their origin family.
  - Output: list of `ClassifiedEdge` with a new field `edge_type ∈ {MODIFICA, DEROGA, CITA, PRACTICA_DE, INTERPRETA_A, MENCIONA}` and `weight` float.
  - Rules:
    - `family=normativa` source + authority keyword nearby → `MODIFICA` / `DEROGA` / `CITA` (weight 1.0).
    - `family=practica` source → `PRACTICA_DE` (weight 0.6).
    - `family in {interpretacion, expertos}` source → `INTERPRETA_A` (weight 0.6).
    - Any source, no authority-keyword context → `MENCIONA` (weight 0.2).
- `src/lia_graph/ingestion/loader_falkor.py` (or wherever Falkor MERGE lives; grep `MERGE`) — emit the typed edge with `edge_type` and `weight` properties.
- `src/lia_graph/ingestion/supabase_sink.py` — `normative_edges` insert: include `edge_type`, `weight`.
- `supabase/migrations/<UTC>_normative_edges_typed.sql` — add columns `edge_type text`, `weight double precision` with sensible defaults for back-compat.

**Files — create.**
- `supabase/migrations/<UTC>_normative_edges_typed.sql` — the migration above.

**Tests — add.**
- `tests/test_edge_extractor.py` (extend if exists):
  - `test_normativa_source_produces_modifica_edge` — "Modifícase el Art. 37" in normativa → `MODIFICA`.
  - `test_practica_source_produces_practica_de_edge` — práctica doc citing "Art. 651 ET" → `PRACTICA_DE`, weight 0.6.
  - `test_casual_mention_gets_menciona_type` — prose mentioning "Ley 1429 de 2010" without authority context → `MENCIONA`, weight 0.2.
- `tests/test_supabase_sink_delta.py` (extend): assert `normative_edges` row includes `edge_type` + `weight`.

**Tests — run.**
- `PYTHONPATH=src:. uv run pytest tests/test_edge_extractor.py tests/test_supabase_sink_delta.py -q`

**Acceptance.**
- All new tests pass.
- Migration applied to local Supabase without data loss: `make supabase-reset && PYTHONPATH=src:. uv run python scripts/seed_local_passwords.py`.
- Dry-run delta against local produces a mix of edge types in the expected proportions.

**State log.** *(template)*

---

### Phase 5 — Thematic graph edges (TEMA / SUBTEMA)

**Goal.** Every chunk emits an edge to its topic node and (when non-null) its subtopic node. Enables query-time BFS from "what topic is the user asking about?" → chunks.

**Files — modify.**
- `src/lia_graph/ingestion/loader_falkor.py` — during MERGE pass:
  - Ensure Topic nodes exist (one per entry in `topic_taxonomy.json`, MERGE on `key`).
  - Ensure Subtopic nodes exist (one per entry in `subtopic_taxonomy.json`, MERGE on `key`).
  - Ensure static `SUBTEMA_DE` edges from Subtopic → Topic.
  - For every Article / Section / Document node written: MERGE `-[:TEMA]->` Topic node, MERGE `-[:SUBTEMA]->` Subtopic node when `subtopic_key` non-null.
- `src/lia_graph/pipeline_d/retriever_falkor.py` — extend the Cypher to optionally fan out through `TEMA`/`SUBTEMA` when the query planner flags a topic-first strategy.

**Files — create.**
- None (nodes/edges emitted by existing MERGE pass).

**Tests — add.**
- `tests/test_falkor_loader.py` (extend or create):
  - `test_topic_nodes_merged_from_taxonomy` — after loader runs, topic node count equals taxonomy count.
  - `test_subtopic_nodes_merged_with_static_subtema_de` — subtopic→topic edges present.
  - `test_chunk_tema_edge_created` — chunk with topic="laboral" has `[:TEMA]->(:Topic {key:'laboral'})`.
  - `test_chunk_subtema_edge_skipped_when_null` — chunk with `subtopic_key=null` has no `SUBTEMA` edge.

**Tests — run.**
- `PYTHONPATH=src:. uv run pytest tests/test_falkor_loader.py -q`
- Manual Cypher probe: `MATCH (:Topic)-[:SUBTEMA_DE]-()  RETURN count(*)` against local Falkor.

**Acceptance.**
- All new tests pass.
- Local Falkor has 39+ topic nodes, 106 subtopic nodes, and `SUBTEMA_DE` edges match the taxonomy parent→child mapping.

**State log.** *(template)*

---

### Phase 6 — `doc_fingerprint` persistence on sink

**Goal.** Guarantee every doc in the new generation has `doc_fingerprint` populated at write-time, so future deltas can use the content-hash shortcut without a separate backfill.

**Files — modify.**
- `src/lia_graph/ingestion/supabase_sink.py` — `write_documents`: call `compute_doc_fingerprint(content_hash, classifier_output)` inline and set `doc_fingerprint` on every row.
- `src/lia_graph/ingestion/fingerprint.py` — audit `compute_doc_fingerprint` + `classifier_output_from_document_row` for parity with the sink input shape (Decision K1 requires equivalence; cross-check test `test_fingerprint.py` case (f)).

**Files — create.**
- None.

**Tests — add / extend.**
- `tests/test_ingestion_supabase_sink.py`:
  - `test_write_documents_populates_fingerprint` — newly-written row has non-null `doc_fingerprint`.
  - `test_fingerprint_stable_across_full_and_delta_paths` — full-rebuild fingerprint == delta-path fingerprint for the same doc.
- `tests/test_fingerprint.py` (existing — ensure case (f) still green).

**Tests — run.**
- `PYTHONPATH=src:. uv run pytest tests/test_fingerprint.py tests/test_ingestion_supabase_sink.py -q`

**Acceptance.**
- New tests pass. Existing fingerprint tests still green.
- Dry-run against a handful of docs shows `doc_fingerprint` populated with the expected hex string.

**State log.** *(template)*

---

### Phase 7a — `Tags` admin endpoints (backend only; ingestionfix_v2 §4 Phase 7a, **shipped 2026-04-23**)

**Scope note.** After implementation review, the full Phase 7 scope (backend + frontend) was split into **7a (backend)** — shipped today, operable via curl / Postman — and **7b (frontend Tags tab)** — deferred to a follow-up so Phase 9 (cloud reingest) lands sooner. Primary success criterion for `ingestionfix_v2` (app serving on the full corpus) does not require the UI, only the backend scaffolding.

**What ships in 7a:**
- Migration `supabase/migrations/20260423000001_document_tag_reviews.sql` — `document_tag_reviews` table with pending-queue partial unique index (one open review per doc).
- `src/lia_graph/tag_report_generator.py` — deterministic Markdown brief builder (title + first-500-words + top-3 alternatives + neighborhood + extracted legal refs) with optional LLM polish via `llm_runtime.resolve_llm_adapter`.
- `src/lia_graph/ui_tags_controllers.py` — five admin endpoints:
  - `GET  /api/tags/review?min_confidence=&reason=&topic=` — pending queue
  - `GET  /api/tags/review/{doc_id}` — detail + review row + topic-matched neighbors
  - `POST /api/tags/review/{doc_id}/report` — triggers LLM brief, persists `report_id` + `report_markdown`
  - `GET  /api/tags/review/{doc_id}/report/{report_id}` — fetch persisted brief
  - `POST /api/tags/review/{doc_id}/decision` — persist expert decision (`approve` / `override` / `promote_new_subtopic` / `reject`), mirrors onto `documents` row.
- Integration in `src/lia_graph/ingestion/supabase_sink.py`: `write_documents` buffers a skeleton review row for every doc with `requires_subtopic_review=True` and flushes after the documents upsert (FK safe).
- Route dispatch wired in `src/lia_graph/ui_server_handler_dispatch.py`.
- Tests: `tests/test_ui_tags_controllers.py` (9 cases) + `tests/test_tag_report_generator.py` (8 cases). All green.

**Acceptance (7a).** Backend tests green. After Phase 9 reingest, `document_tag_reviews` auto-populates with flagged docs; all five endpoints operable via curl. No UI yet.

---

### Phase 7b — `Tags` admin tab **(frontend; DEFERRED, not yet shipped)**

Everything in this subsection is explicitly punted to a follow-up. Phase 7a backend is fully functional without it; you can operate the review workflow via curl / Postman meanwhile. Listed here so the follow-up has a clean checklist.

**Files to create (frontend, atoms/molecules/organisms — design-skill-assisted).**
- `frontend/src/app/ops/tagsShell.ts` — shell for the new tab.
- `frontend/src/features/ops/tagsController.ts` — state machine + API bindings.
- `frontend/src/shared/ui/organisms/tagsReviewBoard.ts` — table: Archivo / Topic actual / Subtopic + confianza / Motivo / Última clasificación / Acciones.
- `frontend/src/shared/ui/molecules/tagsRowActions.ts` — button row per doc (Aprobar / Sobrescribir / Promover / Rechazar / Reporte con LLM).
- `frontend/src/shared/ui/molecules/tagsLlmReportPanel.ts` — pane to display the generated Markdown brief.
- `frontend/src/shared/ui/molecules/tagsNeighborhoodCard.ts` — shows 3 similar docs per candidate tag.
- `frontend/src/styles/admin/tags.css` — tokens-only CSS.

**Files to modify (frontend).**
- `frontend/src/app/ops/shell.ts` — register new tab `Tags` between `Ingesta` and `Promoción` (or wherever it fits by surface-boundary rules). Note: shell is already 650 lines, so tab registration must be additive and must not duplicate existing markup.

**Design-skill invocation.** Before touching frontend, invoke `frontend-design:frontend-design` with a brief that describes: "Bandeja de revisión de tags para expertos en contabilidad colombiana; pestaña dentro del Ops shell; tabla con filtros, botón `Reporte con LLM` por fila, modal con el brief Markdown, acciones de aprobar/sobrescribir/promover/rechazar; estilo tokens-only, IBM Plex stack". Keep atomic-discipline guard green.

**Tests (frontend, to add).**
- `frontend/tests/tagsController.test.ts` — vitest.
- `frontend/tests/tagsReviewBoard.test.ts` — organism render + action-click.
- `frontend/tests/atomicDiscipline.test.ts` — must stay green (no raw hex, no inline SVG outside `shared/ui/icons.ts`, tokens-only CSS).

**Tests to run for 7b acceptance.**
- `npm run test:frontend -- tagsController tagsReviewBoard atomicDiscipline`
- Manual smoke: against local Supabase, navigate to the new `Tags` tab, see the queue populated from `requires_subtopic_review=true` rows, generate a report for one doc, apply an override, confirm `documents` row updated.

**Upgrade opportunities to consider during 7b.**
- The 7a neighborhood lookup uses a simple `topic`-match filter. Swap in the `hybrid_search` RPC for true embedding-based similarity once Phase 9's embedding backfill is stable.
- 7a stores `classifier_alternatives` only if `deps["classifier_alternatives_for"]` is injected. Phase 7b should persist alternatives at classification time (write to `document_tag_reviews.decision_payload` or a sidecar column) so the brief reliably shows the top-3.

---

### Phase 7 (historical spec — original full-scope; superseded by 7a + 7b above)

**Goal.** Single surface where an expert can review low-confidence tag bindings and new-subtopic proposals, generate an LLM report per doc for decision support, and persist expert decisions back into the taxonomy + document rows.

**Files — create (backend).**
- `src/lia_graph/ui_tags_controllers.py` — HTTP handlers:
  - `GET /api/tags/review` — list with filters `?min_confidence=&reason=&topic=`.
  - `GET /api/tags/review/{doc_id}` — detail: current tags + classifier alternatives + similar-doc neighbors (via embedding lookup, top-3 per candidate tag).
  - `POST /api/tags/review/{doc_id}/report` — trigger LLM brief generation. Returns `report_id` immediately; report async-writes to `document_tag_reviews.report_markdown`.
  - `GET /api/tags/review/{doc_id}/report/{report_id}` — fetch brief.
  - `POST /api/tags/review/{doc_id}/decision` — persist expert decision: `{action: "approve"|"override"|"promote_new_subtopic"|"reject", new_topic?, new_subtopic?, reason, expert_id}`.
- `src/lia_graph/tag_report_generator.py` — builds the LLM brief: title + first 500 words + current tags + top-3 alternatives + neighborhood samples + extracted legal refs. Calls a `llm_client` abstraction that picks provider from env (reuse what `answer_synthesis.py` already uses).
- `supabase/migrations/<UTC>_document_tag_reviews.sql` — new table:

  ```sql
  CREATE TABLE document_tag_reviews (
      review_id         text PRIMARY KEY,
      doc_id            text NOT NULL REFERENCES documents(doc_id),
      report_id         text,
      report_markdown   text,
      report_generated_at timestamptz,
      decision_action   text CHECK (decision_action IN ('approve','override','promote_new_subtopic','reject')),
      decision_payload  jsonb,
      decided_by        text,
      decided_at        timestamptz,
      created_at        timestamptz DEFAULT now()
  );
  CREATE INDEX ON document_tag_reviews(doc_id);
  CREATE INDEX ON document_tag_reviews(decided_at) WHERE decided_at IS NULL;
  ```

**Files — modify (backend).**
- `src/lia_graph/ui_server.py` — register the new controller routes.
- `src/lia_graph/ingest_subtopic_pass.py` — on every classification with `requires_subtopic_review=true` OR `subtopic_confidence<0.7` OR `subtopic_is_new=true`, INSERT a skeleton row into `document_tag_reviews` (decision_action NULL) so the queue is always fresh.
- Apply expert decisions:
  - `override` / `approve` → update `documents` row (`topic`, `subtema`, `subtopic_confidence=1.0`, `tagged_by_expert=decided_by`, `tagged_at=decided_at`).
  - `promote_new_subtopic` → append entry to `config/subtopic_taxonomy.json` with `curator=decided_by`, `evidence_count=1`, `curated_at=now`. Commit-to-disk happens via a follow-up make target; the DB-level flag flips immediately.

**Files — create (frontend, atoms/molecules/organisms — design-skill-assisted).**
- `frontend/src/app/ops/tagsShell.ts` — shell for the new tab.
- `frontend/src/features/ops/tagsController.ts` — state machine + API bindings.
- `frontend/src/shared/ui/organisms/tagsReviewBoard.ts` — table: Archivo / Topic actual / Subtopic + confianza / Motivo / Última clasificación / Acciones.
- `frontend/src/shared/ui/molecules/tagsRowActions.ts` — button row per doc (Aprobar / Sobrescribir / Promover / Rechazar / Reporte con LLM).
- `frontend/src/shared/ui/molecules/tagsLlmReportPanel.ts` — pane to display the generated Markdown brief.
- `frontend/src/shared/ui/molecules/tagsNeighborhoodCard.ts` — shows 3 similar docs per candidate tag.
- `frontend/src/styles/admin/tags.css` — tokens-only CSS.

**Files — modify (frontend).**
- `frontend/src/app/ops/shell.ts` — register new tab `Tags` between `Ingesta` and `Promoción` (or wherever it fits by surface-boundary rules).

**Design-skill invocation.** Before touching frontend, invoke `frontend-design:frontend-design` with a brief that describes: "Bandeja de revisión de tags para expertos en contabilidad colombiana; pestaña dentro del Ops shell; tabla con filtros, botón `Reporte con LLM` por fila, modal con el brief Markdown, acciones de aprobar/sobrescribir/promover/rechazar; estilo tokens-only, IBM Plex stack". Keep atomic-discipline guard green.

**Tests — backend.**
- `tests/test_ui_tags_controllers.py`:
  - `test_list_review_queue_filters_by_confidence`
  - `test_get_doc_detail_includes_alternatives_and_neighbors`
  - `test_post_report_creates_review_row_with_report_id`
  - `test_post_decision_approve_updates_documents_row`
  - `test_post_decision_promote_new_subtopic_updates_taxonomy_json`
- `tests/test_tag_report_generator.py`:
  - `test_report_includes_title_and_first_500_words`
  - `test_report_lists_top3_classifier_alternatives`
  - `test_report_lists_neighbors_per_candidate_tag`

**Tests — frontend.**
- `frontend/tests/tagsController.test.ts` — vitest.
- `frontend/tests/tagsReviewBoard.test.ts` — organism render + action-click.
- `frontend/tests/atomicDiscipline.test.ts` — must stay green.

**Tests — run.**
- `PYTHONPATH=src:. uv run pytest tests/test_ui_tags_controllers.py tests/test_tag_report_generator.py -q`
- `npm run test:frontend -- tagsController tagsReviewBoard atomicDiscipline`

**Acceptance.**
- Full backend + frontend test passes.
- Manual smoke: against local Supabase, navigate to the new `Tags` tab, see the queue populated from `requires_subtopic_review=true` rows, generate a report for one doc, apply an override, confirm `documents` row updated.
- Atomic-discipline guard: no raw hex in shared/ui, no inline SVG outside `shared/ui/icons.ts`.

**State log.** *(template)*

---

### Phase 8 — Subtopic-miner (partial pass **shipped 2026-04-23**; 38 of 39 topics **punted to operator batch**)

**Scope note.** The full miner is a 6.5-hour LLM pass over all 1,381 docs (~17 s / doc real wall-time despite the 60-rpm rate-limit ceiling — Gemini inference latency dominates). Running the full pass in this session would have pushed Phase 9 out of reach. The operator elected to run **one representative topic (`laboral`)** as a sanity check, catalog the remaining 38 topics for a future overnight batch, and proceed to Phase 9 with the current 106-entry `config/subtopic_taxonomy.json` (curated 2026-04-21).

**Miner output for `laboral` (ran 2026-04-23):**
- 11 docs collected, 11 classified labels captured in `artifacts/subtopic_candidates/phase8_laboral.jsonl`.
- Mining (`scripts/mine_subtopic_candidates.py --skip-embed`) produced **0 cluster proposals** + 11 singletons (didn't cluster because `--skip-embed` uses one-hot vectors).
- Manual inspection of singleton labels against the existing 5 laboral subtopics (`novedades_en_nomina_electronica`, `reforma_laboral_ley_2466_2025`, `contratacion_y_liquidacion_laboral_tiempo_parcial`, `marco_general_de_libranzas_y_descuentos_directos_de_nomina`, `aporte_parafiscales_icbf`): **every singleton is already covered**. No taxonomy change required.

**Implication.** Current laboral taxonomy is fresh. Other topics *probably* similar quality (taxonomy curated 2 days ago), but unverified until mined. Post-Phase-9, any mis-classified doc will land in the Phase-7a tag-review queue and can be resolved then.

#### Punted miner batches (cataloged so nothing gets lost)

Each of the 38 parent topics below has NOT been mined in 2026-04-23. When the operator runs the overnight pass, invoke one of the following per topic:

```bash
# Per-topic mining recipe:
set -a; source .env.local; set +a
PYTHONPATH=src:. uv run python scripts/collect_subtopic_candidates.py \
    --commit --only-topic <TOPIC> --rate-limit-rpm 120 \
    --batch-id phase8_<TOPIC>
PYTHONPATH=src:. uv run python scripts/mine_subtopic_candidates.py \
    --input artifacts/subtopic_candidates/phase8_<TOPIC>.jsonl \
    --only-topic <TOPIC>
# Review artifacts/subtopic_proposals_<UTC>.json, then if accepted:
# append to artifacts/subtopic_decisions.jsonl and run
make phase2-promote-subtopic-taxonomy
make phase2-sync-subtopic-taxonomy TARGET=production
```

**Topics still to mine (as of 2026-04-23), grouped by priority tier:**

*Tier A — high doc volume or recent regulatory activity (mine first when batching):*
- `retencion_en_la_fuente` (1 curated subtopic — likely missing Decreto 572 subdivisions)
- `declaracion_renta` (12 subtopics — needs validation against 2024/2025 reform churn)
- `procedimiento_tributario` (5 subtopics — heavy process doc set)
- `iva` (3 subtopics — core product)
- `facturacion_electronica` (4 subtopics)
- `informacion_exogena` (2 subtopics)
- `regimen_simple` (1 subtopic)
- `impuesto_patrimonio_personas_naturales` (1 subtopic)

*Tier B — moderate activity:*
- `calendario_obligaciones`, `reformas_tributarias`, `regimen_sancionatorio`, `comercial_societario`, `estados_financieros_niif`, `precios_de_transferencia`, `cambiario`, `sagrilaft_ptee`, `contratacion_estatal`, `dividendos_utilidades`, `obligaciones_profesionales_contador`, `impuesto_nacional_consumo`, `zonas_francas`, `activos_exterior`, `gravamen_movimiento_financiero_4x1000`, `ica`

*Tier C — smaller / niche topics:*
- `beneficiario_final_rub`, `datos_tecnologia`, `economia_digital_criptoactivos`, `emergencia_tributaria`, `exogena`, `impuestos_saludables`, `inversiones_incentivos`, `leyes_derogadas`, `otros_sectoriales`, `presupuesto_hacienda`, `regimen_tributario_especial`, `rentas_exentas`, `retencion`, `costos_deducciones_renta`, `reforma_pensional` (if present)

**Recommended overnight batch:** `parallel -j 1` the Tier-A list first (8 topics × ~30-90 min each = ~6-10 hours with `--rate-limit-rpm 120`). Tier B and C can wait a week.

**When mining resumes, also consider:**
- Re-run `laboral` with embeddings enabled (no `--skip-embed`) — the semantic clustering may surface sub-subtopic structure (nómina / reforma / trabajo doméstico) that one-hot vectors missed.
- Mine the combined `laboral + reforma_pensional` so PILA / ILD / SGSS adjacencies surface as proposals rather than singletons.
- Once the Phase-7b Tags admin UI ships, use it to approve/reject proposals interactively instead of editing `artifacts/subtopic_decisions.jsonl` by hand.

---

### Phase 8 (historical spec — original full-pass; superseded by partial mining above)

**Goal.** Refresh `config/subtopic_taxonomy.json` from the current corpus before the reingest, so docs don't classify against a frozen catalog and end up in `null` purgatory.

**Files — modify.**
- `src/lia_graph/subtopic_miner.py` — confirm it reads the latest corpus state; add a `--dry-run` flag that writes to a staging JSON (`config/subtopic_taxonomy.staging.json`) without touching the live file.

**Files — create / update.**
- `config/subtopic_taxonomy.staging.json` — output of dry-run. Reviewed by operator via `Tags` tab proposal cards.
- `config/subtopic_taxonomy.json` — replaced after expert review.

**Commands — run.**
```bash
make phase2-collect-subtopic-candidates
make phase3-mine-subtopic-candidates
# Expert review in Tags tab — approve / reject proposals.
make phase2-sync-subtopic-taxonomy  # writes config/subtopic_taxonomy.json
git diff config/subtopic_taxonomy.json  # review
git add config/subtopic_taxonomy.json && git commit
```

**Tests — run.**
- `PYTHONPATH=src:. uv run pytest tests/test_subtopic_miner.py -q` (if exists; else skip).

**Acceptance.**
- Delta between pre/post `subtopic_taxonomy.json` is small and reviewed line-by-line.
- Every new entry has `curator=<expert_id>` (not `auto_accept_v1`).
- `curated_at` timestamp updated.

**State log.** *(template)*

---

### Phase 9 — Full cloud reingest + embeddings + promotion

**Goal.** Execute the actual rebuild and bring the new generation into service.

**Prerequisites.**
- Phases 1–8 merged to `main` and deployed.
- Cold backup taken of current cloud Supabase (Supabase dashboard → backup point in time).
- Current active generation ID captured: `gen_20260421230241` (as of 2026-04-23).

**Commands (the operator runs these in sequence; each has its own wait-and-monitor block — see §5).**

```bash
# 9.A  Full rebuild → new gen_<UTC>, is_active=false.
make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production 2>&1 \
    | tee logs/reingest-$(date +%Y%m%d_%H%M%S).log

# Capture the new generation id from the JSON summary printed at the end.
export NEW_GEN=<paste from log>

# 9.B  Embedding backfill.
# (exact entry point to be confirmed in Phase 9 pre-flight — grep `Makefile` for "embed"
#  and `src/lia_graph/embedding_ops.py` for __main__.)
PYTHONPATH=src:. uv run python -m lia_graph.embedding_ops \
    --target production --generation "$NEW_GEN" 2>&1 \
    | tee logs/embed-$(date +%Y%m%d_%H%M%S).log

# 9.C  Promotion — atomic flip of is_active.
make phase2-promote-snapshot PHASE2_SUPABASE_TARGET=production SNAPSHOT_GEN=$NEW_GEN
```

**Acceptance.**
- 9.A completes without `--strict-falkordb` hard-blocking.
- 9.B leaves zero chunks with `embedding IS NULL`.
- 9.C returns success from the RPC; `corpus_generations` row for `$NEW_GEN` has `is_active=true`.

**State log.** *(template + add: `NEW_GEN:`, `reingest_log_path:`, `embed_log_path:`, `old_gen_retired_from:`)*

---

### Phase 10 — Verification + smoke

**Goal.** Prove the new generation serves retrieval correctly before closing the task.

**Commands — run.**

```sql
-- 10.1  Coverage
SELECT
  (SELECT count(*) FROM documents WHERE sync_generation = :new_gen AND retired_at IS NULL) AS docs,
  (SELECT count(DISTINCT doc_id) FROM document_chunks WHERE sync_generation = :new_gen) AS docs_with_chunks,
  (SELECT count(*) FROM document_chunks WHERE sync_generation = :new_gen) AS chunks_total,
  (SELECT count(*) FROM document_chunks WHERE sync_generation = :new_gen AND embedding IS NULL) AS chunks_without_embedding;
```

Expected: `docs_with_chunks ≈ docs` (delta of a handful = intentionally-empty docs); `chunks_total ≫ docs`; `chunks_without_embedding = 0`.

```bash
# 10.2  Retrieval smoke — previously-orphan doc surfaces.
PYTHONPATH=src:. uv run --group dev python -c "
from lia_graph.pipeline_d.retriever_supabase import hybrid_search
hits = hybrid_search('cómo se tramita un recurso contra sanción por no presentar exógena', k=10)
for h in hits: print(h.chunk_id, h.score)
"
# Expected: top-10 includes a chunk from PRO-L01-guia-practica-recurso-sancion-no-presentar-exogena.md
```

```bash
# 10.3  Graph smoke — typed + thematic edges present.
PYTHONPATH=src:. uv run --group dev python -c "
from lia_graph.graph_client import get_falkor_client
c = get_falkor_client()
print(c.query('MATCH (:Topic) RETURN count(*) AS n').result_set)
print(c.query('MATCH ()-[e:TEMA]->() RETURN count(e) AS n').result_set)
print(c.query('MATCH ()-[e:PRACTICA_DE]->() RETURN count(e) AS n').result_set)
"
# Expected: Topic count ≥ 39; TEMA count > 0; PRACTICA_DE count > 0.
```

```bash
# 10.4  End-to-end main chat.
npm run dev:staging &
# Open localhost:3000, ask a práctica-heavy question,
# confirm response.diagnostics.retrieval_backend == "supabase"
# AND citations include a chunk from formerly-orphan doc set.
```

```bash
# 10.5  Tags tab queue populated.
# Navigate to Ops → Tags. Confirm queue shows docs with requires_subtopic_review=true
# from the fresh reingest. Generate one LLM report. Apply one override. Re-query.
```

**Acceptance.**
- 10.1 through 10.5 all pass.
- `npm run test:health` green.
- `make eval-c-gold` threshold 90 still met (or, if it's now higher, record the new number — expected lift from 10 %→100 % corpus visibility).

**State log.** *(template + add query results inline)*

---

### Phase 11 — UI terminal-banner field-path fix

**Goal.** Cosmetic cleanup so the Phase-8 admin delta banner shows the correct `documents_added / modified / retired` counts from the nested `sink_result` payload.

**Files — modify.**
- `frontend/src/features/ingest/additiveDeltaController.ts` (line ~593) — when building the terminal VM, pass `ev.reportJson?.sink_result` (flattened) instead of `ev.reportJson` wholesale.
- OR: `frontend/src/shared/ui/molecules/additiveDeltaTerminalBanner.ts` (line 57-64) — read `vm.report.sink_result.documents_added` etc.
  Pick one location (prefer controller — keeps banner pure-data).

**Tests.**
- `frontend/tests/additiveDeltaControllerTerminalVm.test.ts` — asserts flattened VM shape.

**Run.**
- `npm run test:frontend -- additiveDeltaControllerTerminalVm`

**Acceptance.**
- Next delta run shows correct counts.

**State log.** *(template)*

---

### Phase 12 — Close-out

**Goal.** Bump docs + env matrix + hand off.

**Files — modify.**
- `docs/guide/orchestration.md` — bump env matrix version, note any new flags (e.g. `LIA_TAG_REPORT_LLM_PROVIDER` if Phase 7 introduced one). Add change-log row.
- `docs/guide/env_guide.md` — mirror the update.
- `CLAUDE.md` — mirror.
- `frontend/src/app/orchestration/shell.ts` + `frontend/src/features/orchestration/orchestrationApp.ts` — update the `/orchestration` HTML map status card.
- This doc (`docs/next/ingestionfix_v2.md`) — mark §7 state ledger `closed_out_at`.

**Acceptance.**
- All four doc surfaces aligned.
- `/orchestration` page renders without console errors.

**State log.** *(template)*

---

## §5 Final end-to-end reingest command with live monitoring (Phase 9 detail)

The operator should run this as one coordinated block, tailing four surfaces in parallel terminals. Only `9.A`, `9.B`, `9.C` are destructive-ish; the four tail commands are read-only observers.

### 5.1 Terminal A — the reingest itself

```bash
# Phase 9.A
make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production 2>&1 \
    | tee logs/reingest-$(date +%Y%m%d_%H%M%S).log
```

### 5.2 Terminal B — event-stream monitor

```bash
# Tail corpus events in real-time.
tail -f logs/events.jsonl | grep --line-buffered \
    -E 'ingest\.run|subtopic\.ingest|ingest\.sink|ingest\.falkor|ingest\.delta' \
    | jq -c 'select(.event_type) | {ts: .ts_utc, ev: .event_type, p: .payload}'
```

### 5.3 Terminal C — Supabase coverage (poll every 30 s)

```bash
PYTHONPATH=src:. uv run --group dev python -c "
import time, os
from lia_graph.supabase_client import create_supabase_client_for_target
c = create_supabase_client_for_target('production')
while True:
    docs = c.table('documents').select('doc_id', count='exact').execute().count
    chunks = c.table('document_chunks').select('chunk_id', count='exact').execute().count
    nil_embed = c.table('document_chunks').select('chunk_id', count='exact').is_('embedding', 'null').execute().count
    print(f'{time.strftime(\"%H:%M:%S\")}  docs={docs}  chunks={chunks}  embed_null={nil_embed}')
    time.sleep(30)
"
```

### 5.4 Terminal D — FalkorDB coverage (poll every 30 s)

```bash
PYTHONPATH=src:. uv run --group dev python -c "
import time
from lia_graph.graph_client import get_falkor_client
c = get_falkor_client()
while True:
    article = c.query('MATCH (a:Article) RETURN count(a) AS n').result_set[0][0]
    topic   = c.query('MATCH (t:Topic) RETURN count(t) AS n').result_set[0][0]
    sub     = c.query('MATCH (s:Subtopic) RETURN count(s) AS n').result_set[0][0]
    tema    = c.query('MATCH ()-[e:TEMA]->() RETURN count(e) AS n').result_set[0][0]
    practica= c.query('MATCH ()-[e:PRACTICA_DE]->() RETURN count(e) AS n').result_set[0][0]
    import time as t; print(f'{t.strftime(\"%H:%M:%S\")}  Article={article} Topic={topic} Sub={sub} TEMA={tema} PRACTICA_DE={practica}')
    t.sleep(30)
"
```

### 5.5 Terminal E — Tags queue depth (poll every 60 s)

```bash
PYTHONPATH=src:. uv run --group dev python -c "
import time
from lia_graph.supabase_client import create_supabase_client_for_target
c = create_supabase_client_for_target('production')
while True:
    pending = c.table('document_tag_reviews').select('review_id', count='exact').is_('decided_at', 'null').execute().count
    total = c.table('document_tag_reviews').select('review_id', count='exact').execute().count
    print(f'{time.strftime(\"%H:%M:%S\")}  tag_reviews_pending={pending}  total={total}')
    time.sleep(60)
"
```

### 5.6 After 9.A completes

- Record final `NEW_GEN` into §7 state ledger.
- Run 9.B (embedding backfill). Terminal C will show `embed_null` converging to 0.
- Run 9.C (promotion). Retrieval flips to new gen.
- Run Phase 10 verification (§4 Phase 10).

### 5.7 Monitoring checklist

- [ ] Terminal A finishes with outcome `ok` (not `ok_empty`, not `failed`).
- [ ] Terminal B shows `ingest.sink.documents.written` with expected count ≈ 1,287 ± intentional removals.
- [ ] Terminal C: `chunks` jumps from ~2,073 to ~10,000+ (estimate — depends on section counts); `embed_null` stays at 0 after 9.B.
- [ ] Terminal D: `Article` + `Section` + `Document` node counts match `chunks` total; `Topic`=39, `Subtopic` ≈ post-miner count; `TEMA` > 0; `PRACTICA_DE` > 0.
- [ ] Terminal E: `tag_reviews_pending` reflects docs classified with `requires_subtopic_review=true` — expected to be lower than today (because the Phase-8 catalog refresh shrinks the review set).

---

## §6 Rollback

Promotion (9.C) is atomic. If verification fails:

```bash
make phase2-promote-snapshot PHASE2_SUPABASE_TARGET=production \
    SNAPSHOT_GEN=gen_20260421230241
```

FalkorDB writes are additive under distinct `sync_generation` labels; leaving them is safe (queries scope by active gen). Optional cleanup once stable: `MATCH (n {sync_generation:$old_gen}) DETACH DELETE n`.

Phase-level rollback: each phase is a squash-merged PR; revert the merge commit if a phase regresses `npm run test:health` or `make eval-c-gold`.

---

## §7 Global state ledger

*This section is the source-of-truth for implementation status. Update at every phase transition. Commit each update.*

```
plan_version: 2.0
plan_last_updated: 2026-04-23
plan_signed_off_by:
plan_signed_off_at:

baseline_snapshot_2026_04_23:
  docs: 1287
  chunks: 2073
  orphan_docs: 1152
  active_generation: gen_20260421230241
  subtopic_catalog_curated_at: 2026-04-21T15:07:13Z
  subtopic_catalog_entries: 106

phase_01_parser_fallback:
  status: in_progress    # parser edit already applied; tests still to be added
  started_at: 2026-04-23
  completed_at:
  branch:
  commit:
  tests_added:
    - tests/test_ingestion_parser.py (pending)
  tests_passing: [ ]
  notes: "Parser fix in src/lia_graph/ingestion/parser.py committed in prior session; verified live against 3 doc shapes. Unit suite still pending."

phase_02_source_type:
  status: pending
  ...

phase_03_topic_null_coercion:
  status: pending
  ...

phase_04_edge_gating_and_typing:
  status: pending
  ...

phase_05_thematic_edges:
  status: pending
  ...

phase_06_fingerprint_persistence:
  status: pending
  ...

phase_07a_tags_admin_backend:
  status: shipped
  completed_at: 2026-04-23
  branch: feat/ingestionfix-v2-phase7-tags-tab
  migration: supabase/migrations/20260423000001_document_tag_reviews.sql
  backend_tests:
    - tests/test_tag_report_generator.py (8 cases, green)
    - tests/test_ui_tags_controllers.py (9 cases, green)
  endpoints:
    - "GET  /api/tags/review"
    - "GET  /api/tags/review/{doc_id}"
    - "POST /api/tags/review/{doc_id}/report"
    - "GET  /api/tags/review/{doc_id}/report/{report_id}"
    - "POST /api/tags/review/{doc_id}/decision"
  sink_integration: "SupabaseCorpusSink.write_documents now flushes tag-review skeletons after doc upsert"

phase_07b_tags_admin_frontend:
  status: deferred
  punt_reason: "Full spec too large to ship in same session without risking Phase 9 (cloud reingest). Scope preserved verbatim in §4 Phase 7b for follow-up."
  depends_on: phase_07a_tags_admin_backend (done)
  unblocked_by: nothing — can ship whenever the operator is ready
  frontend_tests_expected:
    - frontend/tests/tagsController.test.ts
    - frontend/tests/tagsReviewBoard.test.ts
    - frontend/tests/atomicDiscipline.test.ts (must stay green)
  design_skill_invocation: "required before first DOM write — see §4 Phase 7b for brief"

phase_08_subtopic_miner_refresh:
  status: partial_shipped
  completed_at: 2026-04-23
  branch: feat/ingestionfix-v2-phase8-subtopic-miner
  mined_topics:
    - laboral  # 11 docs, 0 cluster proposals, 11 singletons (already covered)
  mined_outputs:
    - artifacts/subtopic_candidates/phase8_laboral.jsonl
    - artifacts/subtopic_proposals_20260423T145816Z.json
  taxonomy_delta: none  # current 106 entries deemed fresh
  punted_topics_count: 38
  punted_topics_catalog: "see §4 Phase 8 (Tier A/B/C tables)"
  reason_punted: "Gemini wall-time ~17s/doc → full 1381-doc pass ~6.5 hours. Operator elected to ship Phase 9 today with current taxonomy and batch remaining topics overnight."
  next_step: "Operator overnight batch per §4 Phase 8 recipe. Consider parallelizing Tier A topics first."

phase_09_full_reingest:
  status: in_progress_as_of_2026_04_23
  mode_chosen: additive_delta  # not full_rebuild; see decision below
  decision_rationale: "Operator picked additive over full-rebuild to avoid a ~6.5h Gemini pass. Additive diffs on-disk corpus (1,381 docs) vs cloud (6,677 docs) and only processes added+modified+retired. Writes directly to gen_active_rolling — no atomic flip needed; Phase 9.C is a no-op."
  branch_tip: feat/ingestionfix-v2-phase8-subtopic-miner  # cascades 1→8 minus Phase 11 (frontend only)

  prerequisites_confirmed:
    migration_20260423000000_normative_edges_typed: applied 2026-04-23 via "supabase db push --linked --include-all"
    migration_20260423000001_document_tag_reviews: applied 2026-04-23 via same command
    normative_edges_edge_type_column: verified via supabase-py probe
    document_tag_reviews_table: verified (0 rows initially)
    supabase_cli_version: "2.90.0 (upgraded from 2.84.2 via brew upgrade)"
    linked_project_ref: utjndyxgfhkfcrjmtdqz
    env_source: ".env.staging"  # confusingly named; it has the SUPABASE_URL for production

  baseline_snapshot_cloud_2026_04_23_pre_reingest:
    documents: 6677
    chunks: 13742
    docs_with_chunks: 4067
    orphan_docs: 2610  # ~39%, down from plan's 1152/89.5% baseline
    chunks_without_embedding: 0
    active_generation: gen_20260422005449  # 2026-04-22 00:54 UTC

  command_to_run: >
    set -a; source .env.staging; set +a;
    PYTHONPATH=src:. uv run python -m lia_graph.ingest
    --corpus-dir knowledge_base --artifacts-dir artifacts
    --additive --supabase-sink --supabase-target production
    --supabase-generation-id gen_active_rolling
    --execute-load --allow-unblessed-load --strict-falkordb
    --allow-non-local-env --json

  dry_run_command: same as above + "--dry-run-delta" (previews plan without writes)

  resumption_instructions: |
    If this session dies mid-reingest:
    1. Re-source .env.staging.
    2. Check current cloud counts (documents / document_chunks) against baseline above.
    3. If counts moved: delta partially applied. Re-run the command above — sink is idempotent on
       doc_id, so re-running only touches docs whose fingerprint changed since last write.
    4. If counts unchanged: re-run the command from scratch.
    5. After command completes with outcome != "ok_empty", run embedding backfill:
         PYTHONPATH=src:. uv run python -m lia_graph.embedding_ops --target production
       (or `scripts/embedding_ops.py --target production` — grep for the entry-point).
    6. Verify no chunks with NULL embedding remain:
         supabase-py: c.table('document_chunks').select('chunk_id', count='exact').is_('embedding', 'null').execute().count
    7. Phase 10 verification (§4 Phase 10).

  NEW_GEN: null  # additive delta uses gen_active_rolling; no new gen created
  reingest_log_path: "logs/phase9_*.log"
  embed_log_path: null  # filled after 9.B
  promoted_at: null     # no promotion step (additive)
  old_gen_retired_from: null

phase_10_verification:
  status: pending
  coverage_query_result:
  retrieval_smoke_result:
  graph_smoke_result:
  e2e_result:
  tags_tab_result:
  eval_c_gold_score:
  ...

phase_11_banner_fix:
  status: pending
  ...

phase_12_close_out:
  status: pending
  orchestration_md_updated:
  env_guide_updated:
  claude_md_updated:
  orchestration_map_updated:
  ...

blockers_log: []

risks_log:
  - risk: "Full reingest may take >60 min; classifier rate-limit is tight. Mitigation: run during low-traffic window."
  - risk: "Subtopic miner might propose many new keys; expert review could bottleneck. Mitigation: set per-bucket cap (e.g. max 5 new subtopics per topic) and defer extras to next iteration."
  - risk: "Falkor adapter parity strictness may block on first TEMA/SUBTEMA rollout. Mitigation: Phase 5 tests locally before cloud."
```

---

## §8 Catalog inventory snapshot (2026-04-23)

### 8.1 Topics — `config/topic_taxonomy.json`

- Version: `draft_v1_2026_04_15c` · 50 entries.
- **39 top-level:** `declaracion_renta`, `iva`, `retencion_en_la_fuente`, `laboral`, `procedimiento_tributario`, `estados_financieros_niif`, `ica`, `calendario_obligaciones`, `facturacion_electronica`, `regimen_simple`, `regimen_sancionatorio`, `informacion_exogena`, `precios_de_transferencia`, `cambiario`, `impuesto_patrimonio_personas_naturales`, `comercial_societario`, `datos_tecnologia`, `inversiones_incentivos`, `presupuesto_hacienda`, `reformas_tributarias`, `otros_sectoriales`, `leyes_derogadas`, `beneficiario_final_rub`, `contratacion_estatal`, `dividendos_utilidades`, `economia_digital_criptoactivos`, `obligaciones_profesionales_contador`, `perdidas_fiscales_art147`, `reforma_pensional`, `sagrilaft_ptee`, `emergencia_tributaria`, `impuestos_saludables`, `regimen_tributario_especial`, `impuesto_nacional_consumo`, `normas_internacionales_auditoria`, `zonas_francas`, `activos_exterior`, `estatuto_tributario`, `gravamen_movimiento_financiero_4x1000`.
- **~11 hierarchical** (have `parent_key`): e.g. `patrimonio_fiscal_renta → declaracion_renta`.
- Per-topic fields: `key`, `label`, `aliases`, `ingestion_aliases`, `legacy_document_topics`, `allowed_path_prefixes`, `vocabulary_status`.

### 8.2 Subtopics — `config/subtopic_taxonomy.json`

- **106 entries / 39 parent-topic buckets.** All `curated_at: 2026-04-21T15:07:13Z`, `curator: auto_accept_v1`. Frozen since 2026-04-21.
- Top buckets: `comercial_societario` (9), `contratacion_estatal` (2), `calendario_obligaciones` (2). Singletons with rich aliases: `cambiario`, `beneficiario_final_rub`.
- Phase 8 will replace this snapshot; record the post-refresh count in §7.

### 8.3 Corpus families (implied from filename prefixes)

| Prefix | Family | Graph-parseable today | After Phase 1 (parser fallback) |
|---|---|---|---|
| `N-*`, `*-N01-*`, `CORE/.../NORMATIVA/…` | `normativa` | Yes (multi-article) | Yes — unchanged |
| `L-*`, `*-L0*-guia-practica-*`, `PRACTICA_*` | `practica` | No | Yes (section-level) |
| `E-*`, `*-E0*-interpretaciones-*`, `EXPERTOS_*` | `interpretacion` / `expertos` | No | Yes (section-level) |
| `EVALUACION-*`, `README-*` | inventory-only | No | Yes (whole-doc fallback) |

---

## §9 Connections to adjacent work

- **Additive-corpus-v1 (Phase 8):** unaffected. After Phase 9.C promotion, the Phase-8 delta surface automatically targets the new rolling gen via `delta_runtime.py:270-293`.
- **Existing subtopic curation board (`subtopicCurationBoard.ts`):** subsumed into the Phase 7 `Tags` tab. Reuse the organism as the "proposal card" sub-component.
- **Commission DIAN procedure slate (`docs/next/commission_dian_procedure_slate.md`):** tangential — once commissioned content ships, it'll flow through the parser fix + Tags tab cleanly.
- **Structural-v2 (`docs/next/structuralwork_v2.md`, commit `b92c803`):** the eval harness's real baseline lands after Phase 10.1 (chunks exist ≫ 2,073).

---

## §10 Sign-off

This plan is ready for operator review. Do NOT begin coding until:

- [ ] Operator has read §0–§9 and validated §2 phasing order.
- [ ] Operator has approved the §4 Phase 7 `Tags` tab spec (backend endpoints + frontend organism).
- [ ] Operator has approved §4 Phase 4 edge-type taxonomy.
- [ ] Operator has approved §5 monitoring plan.
- [ ] §7 `plan_signed_off_by` + `plan_signed_off_at` fields populated.

After sign-off, work sequentially Phase 1 → Phase 12. Update §7 state ledger at every transition. If blocked, populate `blockers_log` with root cause + proposed unblock.
