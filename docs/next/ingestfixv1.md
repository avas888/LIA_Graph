# Ingest Fix v1 — Drag-to-Ingest UX, AUTOGENERAR Topic Assignment, End-to-End Visibility

**Last edited:** 2026-04-20 (plan authored)
**Execution owner:** awaiting approval (plan-only — no code yet)
**Goal:** restore the drag-folder-to-ingest UX from Lia_contadores **inside** Lia_Graph's `make phase2-graph-artifacts-supabase` orchestration model, with full visibility (per-stage progress, AUTOGENERAR topic assignment, log tail) and the WIP → cloud (Supabase + Falkor) promotion flow exercised end-to-end.

> This document is both a **plan** and a **decision ledger**. Every phase has a status block to update in-place during execution. If interrupted, the state of this file is the resumption pointer — read the dashboard, find the first non-`DONE` phase, inspect its `State Notes`, resume from the last checkmark.

---

## 1. Executive Summary

**Problem.** The Sesiones surface I shipped in `v2026-04-20-ui14` is honest about Lia_Graph's batch-CLI architecture (single button → `make phase2-graph-artifacts-supabase` → polled job_id) but **does not match the drag-and-watch UX the user remembers from Lia_contadores**. Specifically missing:

1. **Drag-folder-to-ingest** — no drop zone exists in the new Sesiones panel; documents must already be in `knowledge_base/`.
2. **AUTOGENERAR topic assignment** — Lia_contadores's two-stage classifier (N1 keyword/filename heuristic → N2 LLM resolution against the canonical 40+ topic list, with synonym detection + new-topic minting + per-doc accept/edit gate when confidence < 0.95) is **not exercised**. The Lia_Graph contracts already carry the six `autogenerar_*` fields verbatim (`src/lia_graph/contracts/ingestion.py:67-76, 119-128`) but no code populates them.
3. **Per-stage visual progress** — the UI shows only `queued / running / active / failed` for the whole job. No audit-done / sink-done / falkor-done / embeddings-done breakdown. No log tail in the UI.
4. **Embedding chain** — embeddings are still a separate `python -m lia_graph.embedding_ops` pass not auto-triggered by the run (per `CLAUDE.md` "one concern stays in one place"). For the interactive UX we need an opt-in chain.
5. **WIP → Cloud promotion exercised from the same surface** — Promoción works but lives in a separate sub-tab; the Sesiones run does not link out or hand off.

**Strategy.** Port **concepts** (AUTOGENERAR algorithm, per-doc kanban states, dedup workflow) from Lia_contadores; reimplement them **against Lia_Graph's pipeline** (`SupabaseCorpusSink`, `corpus_generations` table, FalkorDB graph load, `LIA_CORPUS_SOURCE` / `LIA_GRAPH_MODE` mode-aware dispatch). Do not port the legacy `IngestionRuntime` filesystem-kanban verbatim — its `sync_to_supabase_targets` predates the `SupabaseCorpusSink`, has no FalkorDB awareness, and assumes a single global Supabase target.

**Order.** Decisions first (§4), backend primitives (§5 Phases 1-3), wire UI to primitives (§5 Phase 4-5), embedding + promotion auto-chain (§5 Phase 6), tests + observability (§5 Phase 7), final verification (§5 Phase 8).

**Non-goals.**
- Not porting `_IngestionWorkerMixin` or the on-disk `ledger.json` checksum cache verbatim — Lia_Graph dedups via Supabase `documents.checksum` lookup against the active generation, no FS ledger needed.
- Not reviving the 7-phase `ingestion_gates.py` chain as-is — Lia_Graph's gates are simpler (audit gate + manifest blessing + sink + falkor load + embedding pass), already proven in the SUIN flow.
- Not building a per-document "accept/edit/discard" wizard for AUTOGENERAR until N1+N2 confidence is shown in production to be wrong often enough to need it. Phase 1 ships **classify-and-commit** with a "review needed" flag for low-confidence rows; the wizard is Phase 6 (deferred).

---

## 2. State Dashboard (update in-place during execution)

**Meta**

| Field | Value |
|---|---|
| Plan status | ☑ DRAFT · ☐ APPROVED · ☐ EXECUTING · ☐ COMPLETE |
| Current phase | — |
| Last completed phase | — |
| Blockers | — |
| Working tree | clean baseline `feat/suin-ingestion` @ post-`v2026-04-20-ui14` |

**Phase ledger** — tick each box as it happens. Allowed statuses: `NOT_STARTED`, `IN_PROGRESS`, `PASSED_TESTS`, `COMMITTED`, `DONE`, `BLOCKED`.

| # | Phase | Status | Files touched (target) | Commit SHA |
|---|---|---|---|---|
| 0 | Decisions ratified by user (§4) | NOT_STARTED | — | — |
| 1 | Port `ingestion_classifier.py` — N1 keyword/filename + N2 LLM AUTOGENERAR | NOT_STARTED | new module, tests | — |
| 2 | New backend: `POST /api/ingest/intake` (multipart upload + classify preview) | NOT_STARTED | `ui_ingest_run_controllers.py`, new helper, tests | — |
| 3 | New backend: per-stage progress + log tail endpoints | NOT_STARTED | `ui_ingest_run_controllers.py`, structured log emit | — |
| 4 | Frontend atoms/molecules: `progressDot`, `fileChip`, `intakeFileRow`, `stageProgressItem`, `logTailViewer` | NOT_STARTED | atomic-design under `shared/ui/`, tests | — |
| 5 | Frontend organisms: `intakeDropZone`, `runProgressTimeline`, `runLogConsole`; controller wiring | NOT_STARTED | new organisms, `ingestController.ts` extended | — |
| 6 | Embedding + Promoción auto-chain (opt-in checkbox) | NOT_STARTED | `ingest.py` flag OR run-orchestrator script, controller, tests | — |
| 7 | Observability: trace events at every stage, log line schema | NOT_STARTED | `ui_ingest_run_controllers.py`, `instrumentation.py` if needed | — |
| 8 | E2E verification — drop the 3 UGPP docs, watch through to active production | NOT_STARTED | manual script + log review | — |

**Tests baseline** (set in Phase 0)

| Suite | Pre-plan | Post-plan target |
|---|---|---|
| Python (`tests/test_ui_ingest_run_controllers.py`) | 17 pass | 17 + new (estimated +12) |
| Frontend (`tests/ingest{Atoms,Molecules,Organisms}.test.ts`) | 34 pass | 34 + new (estimated +20) |
| New: `tests/test_ingest_classifier.py` | n/a | new (estimated 15) |
| New: `tests/test_ingest_intake_controller.py` | n/a | new (estimated 10) |
| Atomic discipline guard (`tests/atomicDiscipline.test.ts`) | green | green |

---

## 3. What We Learned From Lia_contadores (read-only audit, 2026-04-20)

Full citations available in conversation transcript; condensed here:

### 3.1 Drag-to-ingest flow (the working reference)
- **Drop binding:** `opsIngestionController.ts:1848-1887` (drag-{enter,over,leave,drop}); folder walk via `webkitGetAsEntry` + recursive `readEntries` (`opsIngestionController.ts:515-580`).
- **Per-file relative path** preserved in `state.folderRelativePaths` and sent as `X-Upload-Relative-Path` header (line 1362) — load-bearing for the classifier (file-path hints feed scoring).
- **Filtering:** client = `.pdf|.md|.txt|.docx`, drop hidden + `__MACOSX`. Server = `_SUPPORTED_EXTENSIONS = {.md .txt .json .pdf .docx}` (`ingestion_runtime.py:57`) + a second pre-flight reject list (`state.md`, `readme.md`, `claude.md`, `_manifest_*`, `__pycache__`, `node_modules`, `derogadas/`, etc.) at `ingestion_preflight.py:60-114`.
- **Pipeline:** drop → debounced `schedulePreflight` → SHA-256 hash via `crypto.subtle.digest` → `POST /api/ingestion/preflight` → server returns `{artifacts, duplicates, revisions, new_files}` → UI partitions intake into `willIngest` and `bounced`.

### 3.2 AUTOGENERAR — the actual algorithm (this is the core port)
- **UI choice:** dropdown value `"autogenerar"` is sent to backend literally; server-side detection only fires when `X-Upload-Batch-Type: autogenerar` (`ui_write_controllers.py:823, 856-883`).
- **N1 cascade** (`ingestion_classifier.py:277-311`):
  - `_FILENAME_TYPE_PATTERNS` (lines 37-52): `^(ET_art_|DUR_|Ley_|Decreto_|Res_)` → `normative_base @ 0.95`; `concepto_dian|oficio_dian` → `interpretative_guidance @ 0.85`; etc.
  - `_FILENAME_TOPIC_PATTERNS` (lines 56-92): uppercase prefixes `IVA-`, `ICA-`, `GMF-`, `RET-`, `NIIF-`, `NOM-` (laboral), `FE-`, `EXO-`, `RFL-` (reforma laboral 2466), `RST-`, `SAG-` (sagrilaft) — each at 0.95.
  - Body-text scoring via `topic_router.detect_topic_from_text(body_preview, filename=...)`.
  - Combined confidence = `min(topic, type)` if both present, else `max`.
- **N2 LLM cascade** (`ingestion_classifier.py:358-451`) — fires when N1 combined < 0.95. One LLM call, three jobs:
  1. Generate free-form 2-5-word topic label.
  2. Compare against `get_supported_topics()` and decide: synonym OR genuinely new.
  3. Classify type into `normative_base | interpretative_guidance | practica_erp`.
  Returns strict JSON: `generated_label, rationale, resolved_to_existing, synonym_confidence, is_new_topic, suggested_key, detected_type`.
- **Post-LLM sanity** (lines 408-437):
  - If `resolved_to_existing` not in registry → flip to `is_new_topic=True`.
  - If LLM said "new" but keywords find a topic with confidence > 0.7 → override to that topic.
  - For new topics, `suggested_key = _slugify(generated_label)`.
- **Confidence fusion** (`_fuse_autogenerar_confidence`, lines 460-493):
  - new topic → 0.70
  - synonym ≥ 0.80 → base 0.85 + 0.10 if N1 agrees + 0.05 if synonym ≥ 0.90
  - synonym 0.50-0.79 → 0.0 (forces manual review)
  - synonym < 0.50 → 0.0
- **`is_raw` flag:** combined < 0.95 → status flips to `"raw"`, kanban card surfaces accept/edit-suggestion controls. `accept_synonym` writes `detected_topic = autogenerar_resolved_topic`; `accept_new_topic` calls `register_corpus(...)` to mint a brand-new corpus entry on the fly, then re-queues.
- **Resolution moment in Lia_contadores:** `ingestion_runtime.py:431-440` swaps `session.corpus = autogenerar` → `effective_corpus = doc.detected_topic` at processing time, used for KB paths, doc_id prefix, manifest rows. **Critical for the Lia_Graph port** — see decision §4.E.

### 3.3 Parse → chunk → persist (Lia_contadores pre-FalkorDB)
- Per-doc state machine: `queued → classifying → uploading → extracting (15%) → etl (55%) → writing (72%) → gates → done (100%)` (`ingestion_runtime.py:362-525`); kanban card mappings at `opsKanbanView.ts:51-67`.
- 8-section "normalized markdown article" template hard-coded in `ingestion_runtime.py:122-131` (`## Identificacion`, `## Texto base referenciado`, `## Regla operativa para LIA`, etc.) — feeds the chunker.
- Chunker (`ingestion_chunker.py:20-79`) splits on `\n\s*\n+` and `## ` headings, classifies chunks `vigente | historical | operational | metadata` (`_SECTION_TYPE_MAP`).
- Batch-level gates (`ingestion_gates.py:21-202`): `validating → manifest → indexing → syncing → ledger → archive`.
- **Embeddings happened inline** in the Phase 4 `syncing` gate via `sync_to_supabase_targets`. Lia_Graph deliberately pulled this out to `embedding_ops.py` (per `CLAUDE.md`).
- **No graph load.** Lia_contadores has zero FalkorDB / Cypher mentions — graph is brand-new in Lia_Graph.

### 3.4 Endpoint surface (Lia_contadores writes)
The 17 POST endpoints the kanban controller uses. Lia_Graph subset to port:
- `POST /api/ingestion/preflight` — batch hash + dedup + artifact scan **(KEEP)**
- `POST /api/ingestion/sessions/{id}/files` — per-file upload + classify + dedup-tag **(REPLACE with `/api/ingest/intake` batched multipart)**
- `POST /api/ingestion/sessions/{id}/documents/{doc_id}/accept-autogenerar` — accept synonym | new topic **(KEEP, deferred to Phase 6)**
- `POST /api/ingestion/sessions/{id}/documents/{doc_id}/resolve-duplicate` — replace | add_new | discard **(KEEP, deferred to Phase 6)**
- `POST /api/ingestion/sessions/{id}/process` — start worker **(REPLACE with existing `/api/ingest/run`)**
- `POST /api/ingestion/sessions/{id}/validate-batch` — gate-only re-run **(SKIP — Lia_Graph runs gates inline in `make phase2-graph-artifacts-supabase`)**

---

## 4. Decision Points (RATIFY BEFORE PHASE 1)

These are the architectural calls. They are NOT defaults I'll silently pick — each needs an explicit yes/no/modify from the user before code lands.

### Decision A — Drop target directory

When the user drops a folder, where do the files land on disk before the make target picks them up?

**Option A1 (recommended):** Files land in `knowledge_base/<dropped_folder_name>/` directly. The classifier reads tier from `NORMATIVA/`/`EXPERTOS/`/`LOGGRO/` subdirectories AS-IS. This means the user's dropped folder needs to follow the convention OR a flat folder will get default-tier classification. Pro: zero bookkeeping, the existing `make phase2-graph-artifacts-supabase` picks up new files on next run. Con: writes directly into the synced snapshot directory.

**Option A2:** Files land in `knowledge_base/_drop_inbox/<batch_id>/<original_path>/`. The make target is extended to also walk `_drop_inbox/`. After successful sink commit, the batch is moved to `knowledge_base/<resolved_topic>/` (resolved by AUTOGENERAR). Pro: cleaner audit trail. Con: requires the make target to learn a second source root.

**Option A3:** Files land in a brand-new sibling directory `knowledge_base_uploads/<batch_id>/`, never merged. The Sesiones runner invokes a new `python -m lia_graph.ingest --extra-corpus-dir knowledge_base_uploads/<batch_id>` flag. Pro: total isolation. Con: divergent pipeline path; files need a second move to enter the canonical corpus.

**My recommendation: A1** — matches Lia_contadores's mental model (drop → classify → it's just part of the corpus). Lower complexity, preserves the canonical Lane 0 invariant ("`knowledge_base/` is the source of truth"). Need user sign-off because it writes directly to a versioned-but-not-git-tracked directory.

**RATIFIED 2026-04-20: A1.** Files placed directly at `knowledge_base/<resolved_topic>/<original_filename>` at intake time. Open thread for Question 2: the Dropbox persistence story (so dropped files survive the next `sync_corpus_snapshot.sh` run).

### Decision B — `to_upload_graph/` Dropbox bucket

The user dropped 3 test docs in `to_upload_graph/` — outside `scripts/sync_corpus_snapshot.sh`'s scope. Two options:

**B1 (recommended):** Add `"to_upload_graph"` to `sync_corpus_snapshot.sh:48`. Document as the **Lia_Graph-specific** Dropbox upload bucket (vs. shared `to upload/`). Reason: signals separation per the Lia_Graph ↔ Lia_contadores boundary in user memory.

**B2:** Use existing `to upload/` instead. Cleaner if no separation needed.

**RATIFIED 2026-04-20: B1.** `to_upload_graph/` is the Lia_Graph-specific Dropbox bucket. Action items: (1) add `"to_upload_graph"` to `scripts/sync_corpus_snapshot.sh:48`; (2) intake endpoint dual-writes (knowledge_base/ + Dropbox/to_upload_graph/); (3) document the bucket in `orchestration.md` Lane 0 section.

### Decision C — Chunker model

Lia_contadores's chunker assumes the 8-section "normalized article" template (`ingestion_runtime.py:122-131`). Lia_Graph's RAG path uses chunks emitted by SUIN ingestion (`src/lia_graph/ingestion/parser.py` + `loader.py`) and rewritten by `ui_chunk_assembly.py` for the citation-profile modal. Cannot run both — they produce incompatible chunk types.

**C1 (recommended):** Use existing Lia_Graph chunker (`SupabaseCorpusSink._sanitize_doc_id` + chunker in `ingestion/parser.py`). The dropped doc gets ingested by the same path SUIN docs use. Pro: single chunk schema, single retrieval path. Con: drops Lia_contadores's section-aware chunk-section-type tagging (`vigente / historical / operational / metadata`) UNLESS we port that classification logic too.

**C2:** Port the 8-section template + chunker. Pro: better legal-grade chunk type tags. Con: parallel ingestion stack — exactly the anti-pattern `CLAUDE.md` warns against.

### Decision D — Embedding auto-chain

When the user clicks "Iniciar ingesta" in the new UI, should embeddings run automatically?

**D1 (recommended):** Yes, with an opt-out checkbox "Saltar embeddings (correr aparte después)". Default chains: ingest → sink → falkor load → embeddings. Pro: matches user expectation of "drop and watch through end". Con: violates `CLAUDE.md`'s "one concern stays in one place" — needs an explicit doc note that this is a UI-orchestration choice, not a pipeline change.

**D2:** No, keep embeddings as a separate Promoción button. Pro: respects existing module boundaries. Con: extra step the user has to remember.

### Decision E — AUTOGENERAR resolution moment

In Lia_contadores, AUTOGENERAR resolves at processing time via `ingestion_runtime.py:431-440`. In Lia_Graph, `make phase2-graph-artifacts-supabase` reads `knowledge_base/` as already-classified input — by then the topic must be baked into the directory placement OR the manifest. Two options:

**E1 (recommended):** Resolve AUTOGENERAR at intake time (frontend → `/api/ingest/intake`). Each file's classification (N1+N2 cascade) runs on upload; the file is placed in `knowledge_base/<resolved_topic>/<original_filename>`. The make target sees a fully-classified tree. Per-doc `autogenerar_*` fields persist into a sidecar JSONL at `artifacts/intake/<batch_id>.jsonl` for audit.

**E2:** Resolve AUTOGENERAR mid-pipeline by extending `ingest.py` with an `--autogenerar-batch-id` flag that reads pending files from a staging area, classifies, then routes. Pro: single source of truth for classification. Con: forks `ingest.py` orchestration into "audit-mode" vs "intake-mode".

### Decision F — Per-doc accept/edit gate (Phase 6, deferred)

For low-confidence (combined < 0.95) classifications, do we:

**F1 (recommended for Phase 1):** Auto-commit with a `requires_review = true` flag visible in the Generaciones list. User can later override via a separate admin tool. Pro: ships Phase 1 fast. Con: no mid-flight pause; bad classifications go in.

**F2 (Phase 6 target):** Block the run when ANY doc is below threshold. UI pops a per-doc accept/edit modal (port the kanban accept-autogenerar handler). Pro: matches Lia_contadores. Con: significant UX surface to build.

---

## 5. Phased Implementation

> Each phase has a Definition of Done + the Verification Command we run before marking PASSED_TESTS. Tests are required at every phase.

### Phase 0 — Decisions ratified
**DoD:** all six decisions in §4 marked with explicit user choice in this doc.
**Verification:** plan-doc diff shows `(ratified 2026-MM-DD by user)` against each decision.

### Phase 1 — Port AUTOGENERAR classifier
**Why first:** every other phase depends on the classify call.

**Files to create:**
- `src/lia_graph/ingestion_classifier.py` — port of N1 cascade (`_FILENAME_TYPE_PATTERNS`, `_FILENAME_TOPIC_PATTERNS`, body keyword scoring) + N2 LLM cascade (prompt template, JSON parsing, post-validation, confidence fusion). Wire to existing `topic_router.detect_topic_from_text` + `topic_taxonomy.iter_topic_taxonomy_entries` for the canonical topic list (already ~40 topics in Lia_Graph).
- `tests/test_ingest_classifier.py` — 15+ cases covering: (a) every `_FILENAME_TYPE_PATTERNS` regex hits, (b) every `_FILENAME_TOPIC_PATTERNS` prefix hits, (c) body keyword scoring with mocked `detect_topic_from_text`, (d) N2 LLM cascade with mocked LLM returning `synonym | new | low_confidence`, (e) `_fuse_autogenerar_confidence` boundary cases (0.79 vs 0.80 vs 0.90 synonyms), (f) sanity overrides (LLM says new but N1 finds match > 0.7).

**DoD:** classifier returns the 6 `autogenerar_*` fields populated correctly for every fixture file. No Supabase or filesystem dependency — pure function.

**Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_ingest_classifier.py -v` → all green.

### Phase 2 — `POST /api/ingest/intake` backend
**Files to modify:**
- `src/lia_graph/ui_ingest_run_controllers.py` — add `_handle_ingest_intake_post` that accepts multipart, parses files + `X-Upload-Relative-Path` headers (matches Lia_contadores convention), runs Phase 1 classifier on each file, places file at the path determined by Decision E (`knowledge_base/<resolved_topic>/...` if E1), writes audit sidecar `artifacts/intake/<batch_id>.jsonl`, returns `{batch_id, files: [{relative_path, classification: {...autogenerar_*}, target_path}], summary: {...}}`.
- Trace events: `ingest.intake.received`, `ingest.intake.classified.{filename}`, `ingest.intake.placed`, `ingest.intake.failed`.
- Wire into `ui_server.py` POST dispatch.

**Files to create:**
- `tests/test_ingest_intake_controller.py` — 10+ cases: (a) returns 403 for non-admin, (b) rejects empty multipart, (c) rejects unsupported extensions, (d) classifies + places fixture file (filesystem assertion), (e) sidecar JSONL written, (f) `X-Upload-Relative-Path` honored for nested folder structure, (g) SHA-256 dedup against existing `documents.checksum` skips placement, (h) trace events emitted in expected order.

**DoD:** dropping 3 test files via curl multipart returns the JSON shape the frontend will consume; files exist on disk in classified locations.

**Verification:** test suite green + manual `curl` smoke against staging → 200 + on-disk files visible.

### Phase 3 — Per-stage progress + log tail backend
**Files to modify:**
- `src/lia_graph/ui_ingest_run_controllers.py`:
  - Add `GET /api/ingest/job/{job_id}/progress` — reads `events.jsonl` filtered by `job_id`, returns the 5-stage status: `{audit, sink, falkor, embeddings, promotion}` each `{status: pending|running|done|failed, started_at, finished_at, counts: {...}}`.
  - Add `GET /api/ingest/job/{job_id}/log/tail?cursor=N` — paginated tail of `artifacts/jobs/ingest_runs/ingest_<job>.log`, returns `{lines: [...], next_cursor}`.
  - Extend `_spawn_ingest_subprocess` to emit per-stage trace events around each pipeline stage transition (parse subprocess stdout for `=== Stage: AUDIT ===` markers OR fork `ingest.py` to emit JSON progress lines on stderr — see Phase 7 decision).
- Trace events: `ingest.run.stage.{audit,sink,falkor,embeddings,promotion}.{start,done,failed}` with counts.

**Files to create:**
- `tests/test_ingest_progress_endpoint.py` — 8+ cases: (a) progress endpoint returns 5-stage skeleton even when no events yet, (b) stage transitions reflected after fixture event injection, (c) failed stage reflected, (d) log tail returns lines + cursor, (e) cursor pagination works, (f) 404 on unknown job_id.

**DoD:** frontend can poll progress + log without blocking on subprocess completion.

### Phase 4 — Frontend atoms + molecules
Strictly atomic-design. Each new file ≤ 80 LOC.

**New atoms (`frontend/src/shared/ui/atoms/`):**
- `progressDot.ts` — small dot showing stage status (pending dot / running pulsing / done check / failed cross). Reuses `statusDot` tokens.
- `fileChip.ts` — file pill with name + type icon + size hint + optional remove button.

**New molecules (`frontend/src/shared/ui/molecules/`):**
- `intakeFileRow.ts` — `fileChip` + topic badge (from AUTOGENERAR result) + confidence badge + `requires_review` flag if low-confidence.
- `stageProgressItem.ts` — `progressDot` + stage label + counts text + duration.
- `logTailViewer.ts` — collapsible `<pre>` with auto-scroll-to-bottom + copy-all button + cursor-aware fetch.

**Tests:** `tests/ingestPhase4Atoms.test.ts` + `tests/ingestPhase4Molecules.test.ts` — 12+ cases each.

**DoD:** atomic-discipline guard stays green (no raw hex, no inline SVG outside `icons.ts`).

### Phase 5 — Frontend organisms + controller wiring
**New organisms (`frontend/src/shared/ui/organisms/`):**
- `intakeDropZone.ts` — drag-drop + folder walk (port `webkitGetAsEntry` recursion from Lia_contadores `opsIngestionController.ts:515-580`) + filter (`.pdf|.md|.txt|.docx`, drop hidden + `__MACOSX`) + per-file `intakeFileRow` preview after classify response + "Aprobar e ingerir" primary button.
- `runProgressTimeline.ts` — 5 `stageProgressItem`s with connecting lines, polled every 1.5s.
- `runLogConsole.ts` — `logTailViewer` wrapper with poll + auto-scroll + copy.

**Controller (`frontend/src/features/ingest/ingestController.ts` extended):**
- `_handleDrop(files)` → `POST /api/ingest/intake` → render `intakeFileRow`s in zone → enable Aprobar.
- `_handleApprove(batchId)` → `POST /api/ingest/run {batch_id, supabase_target, suin_scope, auto_embed, auto_promote}` → start polling `/progress` + `/log/tail`.
- `_renderTimeline(progress)` → mount `runProgressTimeline` into a new slot in the template.

**Template (`frontend/src/app/ingest/ingestShell.ts` extended):**
- Add `<div data-slot="intake-zone">` and `<div data-slot="progress-timeline">` and `<div data-slot="log-console">`.

**Tests:** `tests/ingestPhase5Organisms.test.ts` — 15+ cases.

### Phase 6 — Embedding + Promoción auto-chain (per Decision D)
If D1 ratified:
- Extend `_spawn_ingest_subprocess` to chain after `make phase2-graph-artifacts-supabase`:
  1. `python -m lia_graph.embedding_ops --target=<wip|production>` (only chunks where `embedding IS NULL`)
  2. If `auto_promote=true` AND target was `wip`: `python -m lia_graph.embedding_ops --target=production` after a `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production`.

OR extract the chain into a new orchestrator script `scripts/ingest_run_full.sh` that the controller invokes — cleaner separation. Decide in Phase 0.

**Defer to Phase 6.5 (NOT in Phase 1 scope):** the per-doc accept/edit modal for low-confidence classifications (Decision F2). Phase 1 ships F1 (auto-commit + flag).

### Phase 7 — Observability hardening
- Audit every trace line. Confirm `events.jsonl` shows the full path of any single doc end-to-end in chronological order.
- Confirm `logs/api_audit.jsonl` records every new endpoint call with status + duration_ms.
- Add a one-page "Ingest Run Trace Schema" section to this doc: every event_type, when emitted, what payload fields.

### Phase 8 — E2E verification (the user-facing acceptance test)
The 3 UGPP Resolución 532/2024 docs (NORMATIVA + EXPERTOS + LOGGRO):
1. User drops folder via UI.
2. Within 5s, intake response shows 3 rows with classifications: NORMATIVA → `topic=laboral, type=normative_base, conf≥0.95`; EXPERTOS → `topic=laboral, type=interpretative_guidance, conf≥0.85`; LOGGRO → `topic=laboral, type=practica_erp, conf≥0.85`.
3. User clicks Aprobar e ingerir with target=WIP, auto_embed=true.
4. Progress timeline animates through 4 stages (audit → sink → falkor → embeddings) over ~30-90s. Log tail visible.
5. After WIP success: `corpus_generations` (local docker Supabase) has a new row with the 3 docs included; `documents` table has 3 new rows; `document_chunks` has chunks; `chunks.embedding` is non-NULL; FalkorDB local has new nodes for `Resolucion-UGPP-532-2024`, `Decreto-MinSalud-0379-2026`, etc., and new typed edges `[MODIFIES, SUSPENDS, REGLAMENTA, REFERENCES]` per the cadena tables.
6. User clicks "Promote to production" (Promoción tab handoff). Cloud Supabase + cloud FalkorDB mirror WIP. New cloud generation activated.
7. Probe chat: "¿Qué cambió con la Resolución UGPP 532 de 2024 sobre la presunción de costos para independientes?" → answer cites the 3 newly-ingested docs + traverses the Decreto 0379/2026 modification edge.

**DoD:** every step above is checked off with a screenshot + log excerpt.

---

## 6. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM N2 cascade is slow (1-3s per doc) → UI feels frozen | High | Med | Run classify per-file in parallel (concurrency 3, like Lia_contadores's `FOLDER_UPLOAD_CONCURRENCY = 3`); show per-row spinner |
| FalkorDB load fails mid-run → corpus_generations stays in inconsistent state | Med | High | The existing `ingest.py --strict-falkordb` already aborts on Falkor failure; verify the rollback story for the WIP Supabase row |
| Embedding pass times out (1-hour subprocess cap is global) | Low | Med | Phase 6: split embedding job into chunks of ≤5000 rows; add a separate `--max-rows-per-call` flag |
| User drops 100+ files; classifier overruns LLM rate limit | Med | High | Fail fast with clear error message; suggest splitting the batch; cap intake at 50 files per call (config) |
| Auto-promote to production accidentally activates a bad generation | Low | Critical | Phase 6 must require an explicit second confirmation when `supabase_target=production`; prefer the WIP-then-Promoción two-stage default |
| `to_upload_graph/` becomes a "junk drawer" parallel to Dropbox `to upload/` | Med | Low | Document boundary in `orchestration.md`; consider auto-empty after successful ingest |

---

## 7. Out of Scope

- Re-implementing the legacy `ingestion_runtime.IngestionRuntime` filesystem-kanban verbatim (12 missing modules, ~2000 LOC of paradigm clash with batch CLI).
- Per-document live thumbnail rendering of dropped PDFs.
- A "schedule recurring ingest" feature (the `loop` skill can wrap this if needed at a higher layer).
- Migrating SUIN ingestion to use the new intake surface — SUIN remains its own Makefile target.

---

## 8. Open Questions for User (Phase 0 sign-off)

1. **Decision A (drop target):** A1, A2, or A3?
2. **Decision B (`to_upload_graph/`):** B1 (adopt + add to sync script) or B2 (use existing `to upload/`)?
3. **Decision C (chunker):** C1 (Lia_Graph SUIN-style chunker) or C2 (port 8-section template)?
4. **Decision D (embedding auto-chain):** D1 (auto-chain with opt-out) or D2 (separate Promoción button)?
5. **Decision E (AUTOGENERAR resolution moment):** E1 (intake-time, file routed to `knowledge_base/<topic>/`) or E2 (mid-pipeline via `--autogenerar-batch-id` flag)?
6. **Decision F (per-doc accept/edit gate):** F1 (Phase 1: auto-commit + flag) or F2 (Phase 1: blocking modal)?
7. **For Phase 8 E2E:** is `dev:staging` the target environment, or do we run this against `dev` first (local docker Supabase + local docker Falkor) before touching cloud?

---

## 9. Change Log
| Version | Date | Note |
|---|---|---|
| `v1` | 2026-04-20 | Initial draft after Lia_contadores audit. Awaiting Phase 0 ratification. |

---

## 10. References
- `docs/guide/orchestration.md` — Lane 0 (build-time ingestion), Runtime Env Matrix, Controller Surface table (entry for `ui_ingest_run_controllers.py` added in v2026-04-20-ui14).
- `docs/guide/env_guide.md` — `make phase2-graph-artifacts-supabase` workflow + `PHASE2_SUPABASE_SINK_FLAGS` = `--supabase-sink --supabase-target {wip,production} --execute-load --allow-unblessed-load --strict-falkordb`.
- `docs/next/decouplingv1.md` — `opsIngestionController.ts` (2327 LOC) is on the kill list; this plan supersedes it for the Sesiones surface.
- `docs/next/ingestion_suin.md` — frozen SUIN infrastructure (Phase A + B); this plan does not modify SUIN ingest.
- `CLAUDE.md` — "one concern stays in one place" (embeddings out-of-band); "don't let main chat become hidden rendering layer" (don't let UI orchestration become a hidden ingestion runtime).
- `src/lia_graph/contracts/ingestion.py:67-76, 119-128` — `IngestionDocumentState` already carries the 6 `autogenerar_*` fields; classifier output → contract mapping is one-line.
- `src/lia_graph/topic_taxonomy.py` + `topic_guardrails.py` + `topic_router_keywords.py` — canonical 40+ topic list (declaracion_renta, iva, ica, laboral, calendario_obligaciones, facturacion_electronica, retencion_*, niif, …).
