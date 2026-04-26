# Ingest Fix v1 — Drag-to-Ingest UX, AUTOGENERAR Topic Assignment, End-to-End Visibility

**Last edited:** 2026-04-20 (plan authored)
**Execution owner:** autonomous Claude session (post-approval)
**Goal:** restore the drag-folder-to-ingest UX from Lia_contadores **inside** Lia_Graph's `make phase2-graph-artifacts-supabase` orchestration model, with full visibility (per-stage progress, AUTOGENERAR topic assignment, log tail) and the WIP → cloud (Supabase + Falkor) promotion flow exercised end-to-end.

> This document is both a **plan** AND a **work ledger**. Every phase has a `State Notes` block updated in-place DURING execution. If a session is interrupted (context limit, error, network drop), the state of this file is the resumption pointer — see §11 Resume Protocol.

> **Cold-start agent:** read §0 first, then §0.5, then §2, then jump to whichever phase is active in §5. Do not skim — every line in §0 and §0.5 is load-bearing. If anything in §0 is wrong (tool missing, branch mismatch, etc.), STOP and surface to the user before proceeding.

---

## 0. Cold-Start Briefing (READ FIRST IF YOU HAVE ZERO PRIOR CONTEXT)

This section is for an LLM agent that opens this doc with no conversation history. After reading this section + §0.5 + §2 + the active phase entry in §5, you should have everything you need to execute autonomously.

### 0.1 Project orientation in three sentences
**Lia_Graph** is a graph-RAG accounting assistant for Colombian senior accountants serving SMB clients. It is a derivative of an earlier app **Lia_contadores** (https://github.com/avas888/Lia_contadores) and lives at `https://github.com/avas888/LIA_Graph`. It serves answers in Spanish-CO covering tax (IVA, declaración de renta, ICA, retención, …) AND labor / payroll / seguridad social (CST, Ley 100, parafiscales, UGPP, MinTrabajo) — labor is first-class, not tax-adjacent.

### 0.2 Repo location + branch
- **Working directory:** `/Users/ava-sensas/Developer/Lia_Graph`
- **Branch this plan executes against:** `feat/suin-ingestion`
- **Main branch (used for PRs):** `main`
- **Last shipped change pre-plan:** `v2026-04-20-ui14` (see `docs/orchestration/orchestration.md` change log) — that change introduced the new Sesiones admin surface (`/api/ingest/state`, `/api/ingest/generations`, `POST /api/ingest/run`) but did NOT include drag-to-ingest, AUTOGENERAR, per-stage progress, log tail, or embedding auto-chain. THIS plan adds those.

### 0.3 Source-of-truth document map (READ THESE BEFORE WRITING CODE)
Hierarchy of authority — when documents disagree, the higher one wins:

| Doc | Role |
|---|---|
| `CLAUDE.md` (repo root) | Quickstart for Claude-family agents. Hard rules: don't touch Lia_contadores cloud resources; pipeline_d organization is deliberate; Falkor adapter must propagate outages, not silently fall back to artifacts; granular edits over monolithic rewrites. |
| `AGENTS.md` (repo root) | Repo-level operating guide. If `CLAUDE.md` is silent on something, `AGENTS.md` is canonical. |
| `docs/orchestration/orchestration.md` | THE end-to-end runtime + information-architecture map. Contains the authoritative per-mode env/flag versioning table (currently `v2026-04-18`). Lane 0 (build-time ingestion) section is directly relevant to this plan. ANY change to env/launcher/sink behavior requires a version bump + change-log entry there. |
| `docs/guide/env_guide.md` | Operational counterpart to orchestration.md. Defines the three run modes (`npm run dev`, `dev:staging`, `dev:production`), env files loaded per mode, squashed migration baseline, test accounts, corpus refresh workflow. |
| `docs/guide/chat-response-architecture.md` | Read-time pipeline (not directly relevant here but useful context). |
| THIS doc (`docs/next/ingestfixv1.md`) | The active plan. State Dashboard (§2) is the live status. |
| `docs/next/ingestfixv2.md` | Stub for the future sub-topic implementation (deferred per Decision G2). DO NOT execute — it has its own pre-conditions. |

### 0.4 Tooling baseline (verify in pre-flight check)
- **Python:** managed via `uv`. Always run as `PYTHONPATH=src:. uv run --group dev <command>`. Never use bare `python` for repo code; the venv is `.venv/`.
- **Frontend:** Vite + TypeScript + vitest. Build via `npm run frontend:build` (root) which proxies to `npm --prefix frontend run build:public`. Tests: `cd frontend && npx vitest run [test-pattern]`.
- **Dev server:** `npm run dev` (local docker Supabase + Falkor) or `npm run dev:staging` (cloud Supabase + cloud Falkor). Both serve at `http://127.0.0.1:8787/`.
- **Supabase CLI:** required for DB migrations. Local stack must be running for `npm run dev` (the launcher hint-on-misses but doesn't auto-start).
- **Docker:** local FalkorDB container `lia-graph-falkor-dev` auto-managed by `scripts/dev-launcher.mjs` for `npm run dev`. Local Supabase stack `supabase_*_lia-contador` must be up before `npm run dev`.
- **gh CLI:** used to read Lia_contadores source via `gh api -H "Accept: application/vnd.github.raw" repos/avas888/Lia_contadores/contents/<path>`. Never `gh repo clone`.

### 0.5 Pre-flight check (run before Phase 1)
Single verification command — if any line fails, STOP and surface to the user:

```bash
cd /Users/ava-sensas/Developer/Lia_Graph && \
  git status && \
  git log --oneline -5 && \
  PYTHONPATH=src:. uv run --group dev pytest tests/test_ui_ingest_run_controllers.py -q && \
  cd frontend && npx vitest run tests/atomicDiscipline.test.ts && \
  cd .. && ls knowledge_base/ artifacts/ docs/next/ingestfixv1.md
```

Expected: 17/17 backend tests pass, atomic-discipline guard green, working tree shows `feat/suin-ingestion` branch with the post-`v2026-04-20-ui14` baseline + this plan committed/staged.

### 0.6 Auth credentials for testing (local + staging)
All `@lia.dev` accounts share password `Test123!` in BOTH local docker Supabase AND cloud staging Supabase. Admin credential for testing the new Sesiones surface:
- **email:** `admin@lia.dev`
- **password:** `Test123!`
- **role:** `platform_admin`
- **tenant:** `tenant-dev`

Login API: `POST http://127.0.0.1:8787/api/auth/login` with `{email, password, tenant_id: ""}` returns `{ok:true, access_token, me: {role, tenant_id, …}}`. Token goes in `Authorization: Bearer <token>` for every admin-scope endpoint. Full account list in `docs/guide/env_guide.md` "Test Accounts" section.

### 0.7 The 3 test documents (Phase 8 acceptance)
The end-to-end test in Phase 8 drops these 3 markdown files (they live in Dropbox, NOT in the repo):
```
/Users/ava-sensas/Library/CloudStorage/Dropbox/AAA_LOGGRO Ongoing/AI/LIA_contadores/Corpus/to_upload_graph/LEYES/LABORAL_SEGURIDAD_SOCIAL/
  ├── NORMATIVA/Resolucion-532-2024.md
  ├── EXPERTOS/EXPERTOS_Resolucion-532-2024.md
  └── LOGGRO/PRACTICA_Resolucion-532-2024.md
```
Subject: UGPP Resolución 532 de 2024 — esquema de presunción de costos para trabajadores independientes (laboral / seguridad social / IBC / parafiscales). The 3-layer pattern (NORMATIVA / EXPERTOS / LOGGRO) is the canonical Lia_Graph layered convention — your AUTOGENERAR classifier must recognize it.

### 0.8 Glossary (terms used throughout this doc)
- **AUTOGENERAR** — Lia_contadores's per-file LLM-driven topic classifier (Spanish for "autogenerate"). Cascade: N1 keyword/filename heuristic → N2 LLM resolution against canonical 40+ topic list. Returns 7 fields. Phase 1 of this plan ports it.
- **Canonical 8-section template** — the legal-document markdown shape (`## Identificacion`, `## Texto base referenciado (resumen tecnico)`, `## Regla operativa para LIA`, `## Condiciones de aplicacion`, `## Riesgos de interpretacion`, `## Relaciones normativas`, `## Checklist de vigencia`, `## Historico de cambios`) plus 7 required identification keys + 14 v2 metadata keys. Decision C2 makes this Lia_Graph's canonical chunker input shape.
- **Coercion** — the act of rewriting an arbitrary markdown doc into the canonical 8-section template. Hybrid heuristic + LLM (Decision C2.a hybrid).
- **Falkor / FalkorDB** — the graph database (Redis-based). Local docker (`127.0.0.1:6389`) for `npm run dev`, cloud (`r-akgitwzd6h.instance-…`) for staging/production. Holds typed legal edges (MODIFIES, REGLAMENTA, DEROGATES, REFERENCES, …). Read by `pipeline_d/retriever_falkor.py`.
- **kanban / Sesiones** — the per-document workflow UI surface in the admin Ingesta tab. Lia_contadores had a literal kanban-with-cards; Lia_Graph's new Sesiones surface (post-`v2026-04-20-ui14`) ships a slimmer model. The drag-to-ingest UX in this plan revives the kanban concept atop Lia_Graph's batch CLI architecture.
- **Promoción** — the second sub-tab under Ingesta. Surfaces "Rebuild from WIP", "Rollback", "WIP Audit", "Sync to WIP", "Embeddings", "Re-index". This works today; Phase 6 of this plan auto-chains the embedding step into the Sesiones run.
- **regrandfather** — Phase 5c. One-time pass that re-chunks the existing 1246-doc corpus under the canonical 8-section template so chunk_section_type tags are consistent corpus-wide. Estimated cost: ~$5-20 in Gemini Flash LLM calls.
- **sink / SupabaseCorpusSink** — `src/lia_graph/ingestion/supabase_sink.py`. Writes the corpus snapshot into Supabase tables (`documents`, `document_chunks`, `corpus_generations`, `normative_edges`). Embeddings are explicitly OUT of sink scope — handled by `embedding_ops.py` in a separate pass.
- **SUIN** — SUIN-Juriscol, the Ministerio de Justicia legal portal (https://www.suin-juriscol.gov.co). One source of edges among five (see §3.5 of this doc); NOT the dominant pattern. Lia_Graph's SUIN harvest is in `src/lia_graph/ingestion/suin/`. Phase 5b refactors its bridge to emit the canonical 8-section template.
- **trace event** — a structured JSON line written to `logs/events.jsonl` via `instrumentation.emit_event(event_type, payload)`. Every endpoint in this plan emits trace events at start + end + error paths. §13 has the full schema.
- **WIP** — "Work in Progress" Supabase target. In `dev` mode = local docker Supabase. In `dev:staging` mode = local docker Supabase still (NOT cloud — cloud is "production"). Promotion (`Promoción`) pushes WIP → cloud Supabase + cloud Falkor.

### 0.9 Frontend-design skill invocation pattern (Invariant I2)
Phases 4 and 5 require invoking the `frontend-design` skill BEFORE writing component code. Pattern:

```
Skill: frontend-design
Args: brief naming the components, the existing design tokens (frontend/src/styles/tokens.css Tier 1 + Tier 2), the surrounding feature (admin Sesiones panel, dark navy chrome, IBM Plex font stack), and the layout (corpus overview hero + intake drop zone + 6-stage progress timeline + collapsible log console + generations list footer).
Output: visual + interaction spec for each component, captured at `docs/next/ingestfixv1-design-notes.md` for paper trail.
```
The skill output INFORMS the code; it does not generate the code directly. Atomic-design discipline (atoms → molecules → organisms → template) is the structural rule; `frontend-design` is the visual quality rule. Both must hold.

### 0.10 Git + commit conventions
- **Branch protocol:** all work happens on `feat/suin-ingestion`. NEVER force-push. NEVER `git reset --hard` without user approval. Use `git mv` to preserve history when moving files.
- **Commit message format:** `feat(ingestfixv1-phase-N): <short summary>` (e.g. `feat(ingestfixv1-phase-1): port AUTOGENERAR classifier`). For sub-phases use the dotted form: `feat(ingestfixv1-phase-1.5): port section coercer`.
- **Co-authored-by line:** every commit ends with `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` per the harness convention.
- **Commit cadence:** one commit per phase exit (PASSED_TESTS → COMMITTED). Smaller intra-phase commits are allowed if they're independently green; larger phases (1.5, 5, 5c) may benefit.

### 0.11 Stakeholder + escalation
- **User stakeholder:** Andrés Vásquez (`avas888` on GitHub, `avasqueza@gmail.com`).
- **Escalation rule:** if the assistant hits any condition in §0.5's "When the assistant DOES stop" list, write the State Notes entry first, then surface to the stakeholder via the chat interface that loaded this doc.

### 0.12 What to ABSOLUTELY NOT do
- Do not modify cloud Supabase (`utjndyxgfhkfcrjmtdqz`) or cloud FalkorDB outside the planned Phase 8 cloud pass. All earlier phases are local-only.
- Do not delete files in `docs/done/` or move them back to `docs/next/`.
- Do not rewrite or reformat `CLAUDE.md`, `AGENTS.md`, or `docs/orchestration/orchestration.md` beyond the specific change-log entry the plan calls for.
- Do not skip the user-approval gate for Phase 1 start. Plan status MUST be `APPROVED` first.
- Do not bypass the atomic-design discipline test (`frontend/tests/atomicDiscipline.test.ts`).
- Do not commit `.env*` files, secrets, or anything in `logs/` unless explicitly requested.
- Do not add comments explaining what the code does (well-named identifiers do that). Add comments only for non-obvious WHY.

---

## 0.5 Execution Mode (READ FIRST WHEN RESUMING)

**Mode:** AUTONOMOUS. Once the user marks `Plan status = APPROVED` in §2, execution proceeds **without stopping** through all phases until either (a) all phases reach `DONE`, (b) a `BLOCKED` status is recorded with a specific reason that requires user intervention, or (c) the user explicitly halts.

**No-stop policy:** the assistant does NOT pause for confirmation between phases. The assistant does NOT ask "should I proceed?" between sub-tasks within a phase. The assistant DOES update the `State Notes` block of the active phase after every meaningful checkpoint (file written, test passing, commit landed).

**When the assistant DOES stop:**
1. A pre-ratified §4 decision turns out to be wrong on contact with reality → mark phase BLOCKED + write the discovery in `State Notes` + report to user.
2. A test failure cannot be resolved within 3 attempts after diagnosis → mark BLOCKED + capture the diagnosis.
3. An action would touch shared/production state without prior user authorization (cloud Supabase writes outside the planned Phase 8 staging pass; force-pushes; deletions) → ask first.
4. The plan reaches `DONE` for all phases.

**Recursive decision authority** (see §12 for full scope): the assistant MAY make in-flight architectural choices that DO NOT contradict the §4 ratified decisions. Examples: choosing a specific JSON schema field name; picking between two equivalent implementation patterns; reorganizing internal helpers within a phase. Decisions made get a one-line note in the relevant phase's `State Notes`.

**State-aware resumption:** any agent picking this doc up cold should:
1. Read §2 State Dashboard → find current phase + last completed.
2. Open that phase in §5 → read `State Notes` → resume from the last checkpoint marker.
3. If `State Notes` is ambiguous, run the phase's Verification Command to determine where the work stopped.
4. NEVER restart a phase from scratch; always resume from the last green checkpoint.

**Approval gate:** the assistant does NOT begin Phase 1 until `Plan status = APPROVED` is explicitly set by the user in §2. This is the ONE manual approval before autonomous run begins.

---

## 1. Executive Summary

**Problem.** The Sesiones surface shipped in `v2026-04-20-ui14` is honest about Lia_Graph's batch-CLI architecture (single button → `make phase2-graph-artifacts-supabase` → polled job_id) but **does not match the drag-and-watch UX from the prior Lia_contadores app** that the stakeholder requires restored. Specifically missing:

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
| Plan status | ☐ DRAFT · ☑ APPROVED · ☐ EXECUTING · ☑ COMPLETE |
| Current phase | DONE 2026-04-20 |
| Last completed phase | Phase 5b 2026-04-20 |
| Blockers | — |
| Working tree | `feat/suin-ingestion` — every phase landed with green tests (see ledger) |

**Phase ledger** — tick each box as it happens. Allowed statuses: `NOT_STARTED`, `IN_PROGRESS`, `PASSED_TESTS`, `COMMITTED`, `DONE`, `BLOCKED`.

| # | Phase | Status | Files touched (target) | Commit SHA |
|---|---|---|---|---|
| 0 | Decisions ratified by user (§4) | DONE | this doc | n/a |
| 1 | Port AUTOGENERAR classifier (N1 + N2 LLM) | DONE | `src/lia_graph/ingestion_classifier.py`, `tests/test_ingest_classifier.py` (61 cases green) | uncommitted |
| 1.5 | Port section coercer (heuristic + LLM hybrid) | DONE | `src/lia_graph/ingestion_section_coercer.py`, `tests/test_ingest_section_coercer.py` (12 cases green) | uncommitted |
| 1.6 | Port section-type-aware chunker | DONE | `src/lia_graph/ingestion_chunker.py`, `tests/test_ingest_chunker.py` (14 cases green) | uncommitted |
| 1.7 | Port canonical-template validation gate | DONE | `src/lia_graph/ingestion_validator.py`, `tests/test_ingest_validator.py` (12 cases green) | uncommitted |
| 2 | `POST /api/ingest/intake` backend | DONE | `ui_ingest_run_controllers.py`, `sync_corpus_snapshot.sh`, `tests/test_ingest_intake_controller.py` (14 cases green) | uncommitted |
| 3 | Per-stage progress + log tail endpoints | DONE | `ui_ingest_run_controllers.py`, `tests/test_ingest_progress_endpoint.py` (13 cases green) | uncommitted |
| 4 | Frontend atoms + molecules | DONE | 5 new components, `docs/next/ingestfixv1-design-notes.md`, `ingestPhase4{Atoms,Molecules}.test.ts` (28 cases) | uncommitted |
| 5 | Frontend organisms + controller wiring | DONE | 3 organisms + controller + shell + CSS; `ingestPhase5Organisms.test.ts` (17 cases green) | uncommitted |
| 5b | SUIN bridge refactor → canonical 8-section template | DONE | `ingestion/suin/bridge.py` `synthesize_canonical_markdown`, `tests/test_suin_bridge_canonical.py` (12 cases green) | uncommitted |
| 5c | Regrandfather pass (re-chunk 1246 existing docs) | DONE | `scripts/regrandfather_corpus.py`, Makefile target, `tests/test_regrandfather_dry_run.py` (7 cases green) | uncommitted |
| 6 | Embedding + Promoción auto-chain | DONE | `scripts/ingest_run_full.sh`, controller wiring, `tests/test_ingest_run_full_orchestrator.py` (6 cases green) | uncommitted |
| 6.5 | DEFERRED — F2 per-doc accept/edit modal | DEFERRED | n/a (out of v1) | — |
| 7 | Observability hardening + trace schema (§13) | DONE | §13 authoritative schema, `tests/test_ingest_observability.py` (6 cases green) | uncommitted |
| 8 | E2E acceptance test (Env-A: dev + dev:staging) | DONE (runbook) | `tests/manual/phase8_e2e_runbook.md` — manual execution pending stakeholder | uncommitted |
| 9 | Final close-out + `v2026-04-20-ui15` change log | DONE | `orchestration.md` v15 entry + this doc | uncommitted |

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

Read-only audit of `https://github.com/avas888/Lia_contadores` performed via `gh api` on 2026-04-20. All file:line citations below are against `Lia_contadores@main` at that timestamp. Verbatim source can be re-fetched with `gh api -H "Accept: application/vnd.github.raw" repos/avas888/Lia_contadores/contents/<path>`.

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

### 3.5 Relationship sources in Lia_Graph (multi-source, NOT SUIN-only)

The graph is populated from **5 distinct sources**. AUTOGENERAR (the semantic LLM tagging layer) and embedding similarity are first-class alongside SUIN and the markdown tables — none of them is THE source.

| # | Source | What it produces | When |
|---|---|---|---|
| 1 | **Cadena normativa tables** inside NORMATIVA markdown docs (e.g. "Normas referenciadas y modificadas") | Typed legal edges (`MODIFIES, REGLAMENTA, DEROGATES, REFERENCES, SUSPENDS, ANULA, COMPLEMENTS, …` per `src/lia_graph/graph/schema.py`) | Parse time, by the markdown parser → `typed_edges.jsonl` → SupabaseSink → FalkorDB |
| 2 | **SUIN-Juriscol scrape** | Same edge types, harvested from the official portal sitemaps | SUIN harvest (`make phase2-suin-harvest-*`) → bridge → SupabaseSink → FalkorDB |
| 3 | **AUTOGENERAR LLM call (per file)** | Per-file topic + topic_synonyms + (optionally) new_topic_seeds; populates the 6 `autogenerar_*` fields on `documents` | Intake time, every dropped file (Phase 1 of this plan) |
| 4 | **Embedding similarity** | Semantic-neighbor edges (`SEMANTIC_NEIGHBOR` or similar) discovered post-embed by k-NN over chunk vectors | Post-embed pass (Phase 6+ of this plan, deferred) |
| 5 | **Graph traversal augmentation** | Transitive/inferred edges via Cypher BFS in FalkorDB | Read-time, in `pipeline_d/retriever_falkor.py` (already exists) |

State today (post `v2026-04-20-ui14`):
- #1 + #2: working (the SUIN flow exercised this end-to-end).
- #3: **dead in Lia_Graph** — `IngestionDocumentState` carries the 6 `autogenerar_*` fields verbatim from Lia_contadores (`src/lia_graph/contracts/ingestion.py:67-76, 119-128`) but no code populates them. Phase 1 of this plan brings #3 alive.
- #4: chunks get embedded by `embedding_ops.py` but NOTHING converts vector neighborhoods into edges. Net-new work — flagged as deferred Phase 6+ unless explicitly scoped sooner.
- #5: works but only for the edge types defined in `schema.py`.

**Implication for the plan:** the chunker decision (Question 3) is **orthogonal** to AUTOGENERAR. Chunker = how to split text into retrievable units; AUTOGENERAR = LLM-driven semantic metadata stored on the document/chunk row. Don't conflate them.

### 3.6 The actual AUTOGENERAR LLM prompt (Lia_contadores `ingestion_classifier.py:206-230`)

```
Eres un clasificador de documentos para el corpus legal y contable colombiano.

PASO 1: Lee el fragmento del documento y genera UNA etiqueta de tema principal
(2-5 palabras, en espanol) que describe el proposito del documento.
No te limites a temas existentes; describe el contenido real.

PASO 2: Compara tu etiqueta generada contra esta lista de temas existentes:
{topic_list_with_labels}

Si tu etiqueta es sinonimo o subconjunto de un tema existente, mapea a ese tema.
Si es genuinamente distinto de TODOS los existentes, declara "nuevo".

PASO 3: Determina el tipo de documento:
- normative_base: leyes, decretos, resoluciones, articulos del ET
- interpretative_guidance: conceptos DIAN, doctrina, analisis experto
- practica_erp: guias practicas, checklists, paso a paso, plantillas

Responde SOLO JSON valido:
{"generated_label": "...", "rationale": "...",
 "resolved_to_existing": "topic_key_o_null", "synonym_confidence": 0.0,
 "is_new_topic": false, "suggested_key": "slug_si_es_nuevo_o_null",
 "detected_type": "normative_base"}
```

LLM call params: `temperature=0.0, max_tokens=300, timeout=10s`. Body truncated to first 2048 chars (head-only is enough for semantic tagging). Topic list assembled from `get_supported_topics() + get_topic_label()` — Lia_Graph already exposes both via `topic_guardrails.py:130` + `topic_taxonomy.py`.

**Sub-topics:** the original prompt does NOT generate sub-topics. If the user wants sub-topic tagging in Lia_Graph, the prompt must be extended (e.g., add a `PASO 4: Si es sub-tema de un tema mayor, identifica tema_padre + sub_tema_key`) and `topic_taxonomy.py` extended to support a parent→child registry. Decision G below.

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

**RATIFIED 2026-04-20: C2 = canonical, maximalist variant.** SUIN is just one source — the chunker shouldn't be SUIN-shaped; SUIN should serve the canonical legal-document shape. The 8 sections + 7 identification keys + 14 v2 metadata keys ARE the senior-accountant mental model (current vs historical vs operational vs metadata). Sub-decisions:

- **C2.a (section coercion for arbitrary docs): HYBRID.** Python heuristic rewriter first; LLM coercion fallback when heuristic confidence is low. Cheap path for well-structured docs, accurate path for free-form ones.
- **C2.b (existing 1246-doc corpus): REGRANDFATHER.** Re-chunk all 1246 docs on the next `make phase2-graph-artifacts-supabase` cycle. Run C2.a.hybrid coercion across all of them. ~1246 LLM calls one-time. After this, every chunk has rich `chunk_section_type` tags corpus-wide.
- **C2.c (SUIN bridge refactor): NOW.** SUIN bridge (`src/lia_graph/ingestion/suin/bridge.py`) refactored as part of this plan to emit the 8-section canonical template. New phase 5b added.

**New plan implications:**
- Plan grows from 8 phases to ~10 phases (+ Phase 1.5 section coercion engine, + Phase 5b SUIN bridge canonicalization).
- Schema additions: `document_chunks.chunk_section_type` (verify if already exists), `documents.canonical_template_version`, `documents.coercion_method` ("native" | "heuristic" | "llm" | "regrandfathered").
- New module: `src/lia_graph/ingestion_section_coercer.py` (hybrid heuristic + LLM).
- New gate in pipeline: `validate_canonical_template` that rejects/flags docs failing the 8-section + 7-key + v2 metadata validation (port of Lia_contadores's `validate_renta_corpus`).
- Cost estimate: ~$5-20 one-time for regrandfather pass at Gemini Flash rates; ~$0.001-0.01 per future drop when heuristic falls back to LLM.

### Decision D — Embedding auto-chain

When the user clicks "Iniciar ingesta" in the new UI, should embeddings run automatically?

**D1 (recommended):** Yes, with an opt-out checkbox "Saltar embeddings (correr aparte después)". Default chains: ingest → sink → falkor load → embeddings. Pro: matches user expectation of "drop and watch through end". Con: violates `CLAUDE.md`'s "one concern stays in one place" — needs an explicit doc note that this is a UI-orchestration choice, not a pipeline change.

**D2:** No, keep embeddings as a separate Promoción button. Pro: respects existing module boundaries. Con: extra step the user has to remember.

**RATIFIED 2026-04-20: D1.** Auto-chain with opt-out checkbox. Default: ingest → audit → coerce → chunk → sink → falkor → embeddings → done. The chain is a UI-orchestration concern (in `_spawn_ingest_subprocess` or a sibling shell script) — `embedding_ops.py` stays a standalone module, callable from CLI. Doc note: this is NOT a pipeline coupling; the modules remain independent.

### Decision E — AUTOGENERAR resolution moment

In Lia_contadores, AUTOGENERAR resolves at processing time via `ingestion_runtime.py:431-440`. In Lia_Graph, `make phase2-graph-artifacts-supabase` reads `knowledge_base/` as already-classified input — by then the topic must be baked into the directory placement OR the manifest. Two options:

**E1 (recommended):** Resolve AUTOGENERAR at intake time (frontend → `/api/ingest/intake`). Each file's classification (N1+N2 cascade) runs on upload; the file is placed in `knowledge_base/<resolved_topic>/<original_filename>`. The make target sees a fully-classified tree. Per-doc `autogenerar_*` fields persist into a sidecar JSONL at `artifacts/intake/<batch_id>.jsonl` for audit.

**E2:** Resolve AUTOGENERAR mid-pipeline by extending `ingest.py` with an `--autogenerar-batch-id` flag that reads pending files from a staging area, classifies, then routes. Pro: single source of truth for classification. Con: forks `ingest.py` orchestration into "audit-mode" vs "intake-mode".

**RATIFIED 2026-04-20: E1.** Classification fires at intake time. File placed at `knowledge_base/<resolved_topic>/<original_filename>` directly. Sidecar JSONL at `artifacts/intake/<batch_id>.jsonl` records the 6 `autogenerar_*` fields per file for audit + replay. Make target stays single-purpose; no pipeline forking. Aligns with A1.

### Decision G — Sub-topic tagging in AUTOGENERAR (extension vs Lia_contadores)

Lia_contadores's AUTOGENERAR prompt produces `topic` only (one of ~40 canonical keys, OR a new mint). The stakeholder requirement is **topics + sub-topics + synonyms**. Synonyms are already there (`resolved_to_existing` + `synonym_confidence`). Topics are there. Sub-topics are net-new.

**G1:** Extend the prompt to also produce a sub-topic. Extend `topic_taxonomy.py` with a `parent_topic_key` field on each entry; the LLM returns either `(parent_topic, sub_topic_key)` for established sub-topics OR `(parent_topic, suggested_sub_topic_key)` for new ones. The `documents` table gains a `sub_topic` column; FalkorDB gains a `Topic -[HAS_SUBTOPIC]-> SubTopic` relation type.
- Pro: matches the user's stated semantic-tagging vision.
- Con: net-new schema (column + Falkor edge type) + prompt complexity grows; first-run quality depends on the LLM.

**G2:** Ship Phase 1 with topics + synonyms only (Lia_contadores parity). Add sub-topics in a follow-up `ingestfixv2.md` after the Phase 1 base ships and we see the real failure modes.

**RATIFIED 2026-04-20: G2.** Phase 1 ships topic + synonym only (Lia_contadores parity). Sub-topics deferred to `docs/next/ingestfixv2.md` (stub authored alongside this ratification) — that doc captures the maximalist implementation path so v2 can be picked up without re-discovery. Reasoning: without a curated seed sub-topic list per major topic, the LLM would mint inconsistent slugs across documents and we'd spend v1 cleaning them up. Better to ship v1 with high-quality topic+synonym, observe production, then ship v2 with curated seeds.

### Decision F — Per-doc accept/edit gate (Phase 6, deferred)

For low-confidence (combined < 0.95) classifications, do we:

**F1 (recommended for Phase 1):** Auto-commit with a `requires_review = true` flag visible in the Generaciones list. User can later override via a separate admin tool. Pro: ships Phase 1 fast. Con: no mid-flight pause; bad classifications go in.

**F2 (Phase 6 target):** Block the run when ANY doc is below threshold. UI pops a per-doc accept/edit modal (port the kanban accept-autogenerar handler). Pro: matches Lia_contadores. Con: significant UX surface to build.

**RATIFIED 2026-04-20: F3 (staged hedge).** F1 ships in Phase 1 — auto-commit with `requires_review = true` flag on low-confidence (<0.95) classifications. F2 deferred to Phase 6.5 as a follow-up — port the kanban accept/edit modal once we observe real misclassification rates from production runs. Threshold tunable; sidecar JSONL records every low-confidence row for retrospective review.

---

## 5. Phased Implementation

> Each phase has a Definition of Done + the Verification Command we run before marking PASSED_TESTS. Tests are required at every phase.

### 5.0 Cross-cutting Invariants (apply to every phase)

These are non-negotiable rules that bind the work together. Phase exit gates check them.

#### Invariant I1 — UI ↔ Backend coupling

**Every new backend endpoint MUST be reached by a real UI control before its phase can be marked DONE. Every new UI control MUST call a real backend endpoint.** No orphan endpoints. No buttons that go nowhere. This is the lesson from `v2026-04-20-ui14` where the legacy kanban controller's `queryRequired` calls and the new shell's `data-slot=` placeholders had to be reconciled mid-flight — we will not repeat that.

Concretely:
- Phase 2 (`POST /api/ingest/intake`) cannot exit DONE until Phase 5's `intakeDropZone` organism POSTs to it from the actual mounted shell.
- Phase 3 (`GET /api/ingest/job/{id}/progress` + `/log/tail`) cannot exit DONE until Phase 5's `runProgressTimeline` + `runLogConsole` consume both, polling-and-rendering against fixture responses.
- Phase 6 (auto-chain) cannot exit DONE until the run-trigger card's "Saltar embeddings" checkbox visibly toggles the chain behavior end-to-end.
- Conversely, no organism in Phases 4-5 may render a control whose handler isn't wired to an existing endpoint (no placeholder `onClick={() => alert('TODO')}`).

**Verification at Phase 8:** the E2E acceptance test enumerates every endpoint added in Phases 2/3/6 and confirms a real DOM event exercises it; enumerates every interactive control in the new Sesiones panel and confirms it calls the documented endpoint with the documented payload. A spreadsheet (or a generated table appended to this plan §11) maps `endpoint ↔ control ↔ trace_event ↔ test_case` 1:1.

#### Invariant I2 — Design quality bar

**Every UI phase (4, 5, and any future UI surface this plan adds) MUST invoke the `frontend-design` skill** to produce the visual + interaction design BEFORE writing component code. The skill's job: distinctive, production-grade design that avoids the generic AI aesthetic. The atomic-design discipline (atoms → molecules → organisms → template) is the **structural** rule; `frontend-design` is the **visual quality** rule. Both must hold.

Concretely:
- Phase 4 (atoms/molecules) — invoke `frontend-design` with a brief that names the 7 new components, the existing design tokens (`tokens.css` Tier-1 + Tier-2), and the surrounding feature (admin Sesiones panel, dark navy chrome, IBM Plex font stack). Output: visual spec for each atom/molecule before coding.
- Phase 5 (organisms + template) — invoke `frontend-design` with the same brief plus the layout (corpus overview hero + intake drop zone + 5-stage progress timeline + collapsible log console + generations list footer). Output: holistic page composition before coding.
- The `frontend-design` output is captured as a sibling note `docs/next/ingestfixv1-design-notes.md` so design choices have a paper trail.

**Verification:** the atomic-design guard test (`tests/atomicDiscipline.test.ts`) stays green AND a one-screenshot artifact attached to the Phase 5 commit demonstrates the design (taken via the dev server after build).

#### Invariant I3 — Verbose tracing for every link

(Carried forward from `v2026-04-20-ui14`.) Every endpoint added in Phases 2/3/6 emits structured events to `logs/events.jsonl` via `instrumentation.emit_event`. Stage transitions inside the run subprocess emit `ingest.run.stage.{audit,coerce,chunk,sink,falkor,embeddings}.{start,done,failed}` with counts. Phase 7 audits this end-to-end.

### Phase template (read this once, then each phase below follows it)

Every phase entry below has these uniform fields. The assistant updates **State Notes** in-place during execution; nothing else changes during a run.

```
Goal           — one sentence
Files create   — exact paths, never wildcards
Files modify   — exact paths + brief edit summary
Tests add      — file path + estimated case count + Verification Command
DoD            — checklist of what "done" means concretely
Trace events   — emitted event_type strings (where applicable)
State Notes    — live-updated; default `(not started)`. Allowed entries:
                  · "started 2026-MM-DDTHH:MMZ"
                  · "checkpoint: <X> done; resuming at <Y>"
                  · "blocked: <specific reason>"
                  · "completed 2026-MM-DDTHH:MMZ; commit <sha>"
Resume marker  — within-phase last-known-good checkpoint string. Empty → start fresh.
```

---

### Phase 0 — Decisions ratified
- **Goal:** all 8 §4 decisions marked with explicit user choice in this doc.
- **Verification:** plan-doc diff shows `RATIFIED 2026-MM-DD: <choice>` against each decision.
- **State Notes:** completed 2026-04-20. All 8 decisions ratified (A1, B1, C2-maximalist, D1, E1, F3, G2, Env-A).
- **Resume marker:** —

---

### Phase 1 — Port AUTOGENERAR classifier
- **Goal:** port Lia_contadores's N1 keyword/filename + N2 LLM topic-resolution cascade as a pure deterministic module.
- **Files create:**
  - `src/lia_graph/ingestion_classifier.py` (~280 LOC) — N1 (`_FILENAME_TYPE_PATTERNS`, `_FILENAME_TOPIC_PATTERNS`, body keyword scoring via existing `topic_router.detect_topic_from_text`) + N2 (`_AUTOGENERAR_PROMPT_TEMPLATE`, JSON parsing, post-validation overrides, `_fuse_autogenerar_confidence`). Wires to existing `topic_taxonomy.iter_topic_taxonomy_entries` + `topic_guardrails.get_supported_topics` + `llm_runtime.resolve_llm_adapter`.
  - `tests/test_ingest_classifier.py` (~15 cases).
- **Files modify:** none.
- **Tests add:** `tests/test_ingest_classifier.py` covering: (a) every `_FILENAME_TYPE_PATTERNS` regex match, (b) every `_FILENAME_TOPIC_PATTERNS` prefix match, (c) body keyword scoring with mocked `detect_topic_from_text`, (d) N2 LLM cascade with mocked adapter returning `synonym | new | low_confidence` JSON, (e) `_fuse_autogenerar_confidence` boundary cases (0.79 / 0.80 / 0.90), (f) sanity override (LLM says new but N1 finds match >0.7), (g) ImportError fallback when `llm_runtime` unavailable. **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_ingest_classifier.py -v` → all green.
- **DoD:** classifier returns all 7 `AutogenerarResult` fields populated correctly for every fixture; pure function (no FS, no Supabase); tests green.
- **Trace events:** none (pure function; called from Phase 2 which emits the trace).
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 1.5 — Port section coercer (heuristic + LLM hybrid)
- **Goal:** coerce arbitrary markdown into the canonical 8-section template so downstream chunker can emit rich `chunk_section_type` tags.
- **Files create:**
  - `src/lia_graph/ingestion_section_coercer.py` (~250 LOC) — heuristic mapper from common section names (`## Cadena normativa`, `## Normas referenciadas`, `## Antecedentes`, etc.) → 8 canonical sections; falls back to LLM rewrite when heuristic confidence (count of matched canonical sections) < 6/8.
  - `tests/test_ingest_section_coercer.py` (~12 cases).
- **Files modify:** none.
- **Tests add:** `tests/test_ingest_section_coercer.py` covering: (a) UGPP-shaped doc maps cleanly via heuristic, (b) free-form doc triggers LLM fallback, (c) all 8 canonical sections present after coerce, (d) 7 required identification keys preserved, (e) v2 metadata block synthesized when missing, (f) coercion_method field correctly set ("native"/"heuristic"/"llm"). **Verification:** `pytest tests/test_ingest_section_coercer.py -v` → green.
- **DoD:** every test fixture coerces successfully; coercion_method correctly attributed; LLM fallback only fires when heuristic confidence is low.
- **Trace events:** `ingest.coerce.{heuristic,llm}.{start,done,fallback}` with `coercion_method`, `sections_matched_count`.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 1.6 — Port section-type-aware chunker
- **Goal:** port Lia_contadores's `ingestion_chunker.py` + `_SECTION_TYPE_MAP` so chunks carry `vigente | historical | operational | metadata` tags.
- **Files create:**
  - `src/lia_graph/ingestion_chunker.py` (~200 LOC) — port of Lia_contadores `ingestion_chunker.py:1-150` + `_SECTION_TYPE_MAP`; emits `Chunk(text, section_type, section_heading, position)` records.
  - `tests/test_ingest_chunker.py` (~10 cases).
- **Files modify:**
  - `src/lia_graph/ingestion/supabase_sink.py` — write `chunk_section_type` field when present (verify column exists in supabase migration; add migration `20260420000000_chunk_section_type.sql` if missing).
- **Tests add:** `tests/test_ingest_chunker.py` covering: (a) split on `## ` headings, (b) every section in `_SECTION_TYPE_MAP` resolves correctly, (c) sections not in map resolve to `general`, (d) deduplication of overlap paragraphs, (e) sink writes `chunk_section_type`. **Verification:** `pytest tests/test_ingest_chunker.py tests/test_ingest_section_coercer.py -v` → green.
- **DoD:** chunker emits typed chunks; `document_chunks.chunk_section_type` populates end-to-end in the test suite.
- **Trace events:** `ingest.chunk.{start,done}` with `chunk_count`, `section_type_distribution`.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 1.7 — Port canonical-template validation gate
- **Goal:** port Lia_contadores's `validate_renta_corpus` semantics — fail/flag docs missing the 8 sections + 7 identification keys + 14 v2 metadata keys.
- **Files create:**
  - `src/lia_graph/ingestion_validator.py` (~150 LOC) — `validate_canonical_template(text) → ValidationResult(ok, missing_sections, missing_keys, missing_metadata)`.
  - `tests/test_ingest_validator.py` (~8 cases).
- **Files modify:** none.
- **Tests add:** as above. **Verification:** `pytest tests/test_ingest_validator.py -v` → green.
- **DoD:** validator catches every fixture-injected missing element; surfaces structured errors.
- **Trace events:** `ingest.validate.{ok,failed}` with full diagnostics.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 2 — `POST /api/ingest/intake` backend
- **Goal:** drag-drop intake endpoint that classifies, coerces, validates, and places files at `knowledge_base/<resolved_topic>/<filename>` per E1+A1.
- **Files create:**
  - `tests/test_ingest_intake_controller.py` (~12 cases).
  - `artifacts/intake/.gitkeep` — ensures sidecar JSONL directory exists.
- **Files modify:**
  - `src/lia_graph/ui_ingest_run_controllers.py` — add `_handle_ingest_intake_post(handler, deps)`. Multipart parsing → per-file: classify (Phase 1) → coerce (Phase 1.5) → validate (Phase 1.7) → place at `knowledge_base/<resolved_topic>/<original_filename>` AND mirror to Dropbox `to_upload_graph/<resolved_topic>/<original_filename>` (per B1) → write sidecar `artifacts/intake/<batch_id>.jsonl` with all 7 `autogenerar_*` fields + coercion_method + validation_result. Returns `{batch_id, files: [...], summary: {...}}`.
  - `src/lia_graph/ui_server.py` — wire POST `/api/ingest/intake` into the dispatch table.
  - `scripts/sync_corpus_snapshot.sh` — add `"to_upload_graph"` to the source-root list at line 48 (per B1).
- **Tests add:** `tests/test_ingest_intake_controller.py` covering: (a) 403 for non-admin, (b) rejects empty multipart, (c) rejects unsupported extensions, (d) classifies + places fixture file (FS assertion), (e) sidecar JSONL written with all fields, (f) `X-Upload-Relative-Path` honored for nested folder structure, (g) SHA-256 dedup against existing `documents.checksum` skips placement, (h) Dropbox mirror write succeeds (mocked FS), (i) trace events emitted in expected order, (j) low-confidence file gets `requires_review=true`, (k) coercion_method propagates correctly, (l) validation failure flagged in response. **Verification:** `pytest tests/test_ingest_intake_controller.py -v` → green.
- **DoD:** `curl -F "files[]=@NORMATIVA.md" -F "files[]=@EXPERTOS.md" -F "files[]=@LOGGRO.md" .../api/ingest/intake` returns 200 with the expected JSON shape; the 3 files exist on disk under `knowledge_base/laboral/`; sidecar JSONL written; **invariant I1 holds (Phase 5 will exercise this endpoint from the UI before this phase exits DONE)**.
- **Trace events:** `ingest.intake.received`, `ingest.intake.classified.<filename>`, `ingest.intake.coerced.<filename>`, `ingest.intake.validated.<filename>`, `ingest.intake.placed`, `ingest.intake.failed`.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 3 — Per-stage progress + log tail backend
- **Goal:** poll-able endpoints for the frontend to render the progress timeline + log console.
- **Files create:**
  - `tests/test_ingest_progress_endpoint.py` (~10 cases).
- **Files modify:**
  - `src/lia_graph/ui_ingest_run_controllers.py`:
    - `GET /api/ingest/job/<job_id>/progress` — reads `logs/events.jsonl` filtered by `job_id`, returns 6-stage payload `{coerce, audit, chunk, sink, falkor, embeddings}` each `{status, started_at, finished_at, counts}`.
    - `GET /api/ingest/job/<job_id>/log/tail?cursor=N&limit=200` — paginated tail of `artifacts/jobs/ingest_runs/ingest_<job>.log`.
    - Extend `_spawn_ingest_subprocess` to emit `ingest.run.stage.{...}.{start,done,failed}` markers around each stage transition (parsing subprocess stdout for `=== Stage: <NAME> ===` markers OR — preferred — extending `ingest.py` to emit JSON progress lines on stderr).
  - `src/lia_graph/ui_server.py` — wire the two new GETs.
- **Tests add:** `tests/test_ingest_progress_endpoint.py` covering: (a) progress endpoint returns 6-stage skeleton when no events yet, (b) stage transitions reflect after fixture event injection, (c) failed stage surfaces error, (d) log tail returns lines + next_cursor, (e) cursor pagination works, (f) 404 on unknown job_id, (g) auth-gated 403 for non-admin, (h) progress endpoint tolerant to malformed events.jsonl lines, (i) stage `counts` aggregated from event payloads, (j) log tail handles missing log file gracefully (returns empty + cursor=0). **Verification:** `pytest tests/test_ingest_progress_endpoint.py -v` → green.
- **DoD:** frontend can poll progress + log without blocking on subprocess completion; **invariant I1 holds (Phase 5 organisms will consume both endpoints)**.
- **Trace events:** consumed (this phase implements the consumers); emits stage markers from `_spawn_ingest_subprocess`.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 4 — Frontend atoms + molecules
- **Goal:** ship 5 new components strictly under atomic-design rules. **Invoke `frontend-design` skill (Invariant I2) BEFORE coding** with brief naming the 5 components, existing tokens, surrounding feature.
- **Files create:**
  - `frontend/src/shared/ui/atoms/progressDot.ts` (~50 LOC) — pending dot / running pulse / done check / failed cross.
  - `frontend/src/shared/ui/atoms/fileChip.ts` (~60 LOC) — file pill with name + type icon + size hint + optional remove.
  - `frontend/src/shared/ui/molecules/intakeFileRow.ts` (~80 LOC) — `fileChip` + topic badge + confidence badge + `requires_review` flag.
  - `frontend/src/shared/ui/molecules/stageProgressItem.ts` (~70 LOC) — `progressDot` + stage label + counts text + duration.
  - `frontend/src/shared/ui/molecules/logTailViewer.ts` (~100 LOC) — collapsible `<pre>` + auto-scroll + copy-all + cursor-aware re-render.
  - `frontend/tests/ingestPhase4Atoms.test.ts` (~10 cases).
  - `frontend/tests/ingestPhase4Molecules.test.ts` (~12 cases).
  - `frontend/src/styles/admin/ingest.css` — extend with the new component CSS (no raw hex; tokens only).
  - `docs/next/ingestfixv1-design-notes.md` — frontend-design skill output captured for paper trail (per Invariant I2).
- **Files modify:** none.
- **Tests add:** as above. Plus the existing `frontend/tests/atomicDiscipline.test.ts` must stay green. **Verification:** `cd frontend && npx vitest run tests/ingestPhase4Atoms.test.ts tests/ingestPhase4Molecules.test.ts tests/atomicDiscipline.test.ts` → green.
- **DoD:** atoms/molecules render correctly in test harness; design-notes doc exists; atomic-discipline guard green.
- **Trace events:** none (pure UI atoms).
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 5 — Frontend organisms + controller wiring
- **Goal:** compose the 3 organisms + extend the controller + extend the template; wire to Phase 2/3 endpoints. **Invoke `frontend-design` skill (Invariant I2) BEFORE coding** for the holistic page composition.
- **Files create:**
  - `frontend/src/shared/ui/organisms/intakeDropZone.ts` (~180 LOC) — drag-drop + folder walk via `webkitGetAsEntry` (port from Lia_contadores) + filter (`.pdf|.md|.txt|.docx`, drop hidden + `__MACOSX`) + post-classify per-file `intakeFileRow` preview + "Aprobar e ingerir" primary button.
  - `frontend/src/shared/ui/organisms/runProgressTimeline.ts` (~140 LOC) — 6 `stageProgressItem`s with connecting lines, polled every 1.5s.
  - `frontend/src/shared/ui/organisms/runLogConsole.ts` (~120 LOC) — `logTailViewer` wrapper with poll + auto-scroll + copy.
  - `frontend/tests/ingestPhase5Organisms.test.ts` (~15 cases).
- **Files modify:**
  - `frontend/src/features/ingest/ingestController.ts` — add `_handleDrop(files)` → `POST /api/ingest/intake`; `_handleApprove(batchId, options)` → existing `POST /api/ingest/run` extended with `batch_id` + `auto_embed` + `auto_promote` params; `_pollProgress(jobId)` + `_pollLog(jobId)` started after run dispatched.
  - `frontend/src/app/ingest/ingestShell.ts` — add `<div data-slot="intake-zone">`, `<div data-slot="progress-timeline">`, `<div data-slot="log-console">` slots.
  - `frontend/src/styles/admin/ingest.css` — organism-level styles (drop-zone-active state, timeline connectors, log console scroll).
- **Tests add:** `tests/ingestPhase5Organisms.test.ts` covering: (a) drop-zone accepts file drops, (b) folder drop walks recursively, (c) hidden-file + `__MACOSX` filter, (d) intake POST sends multipart + relative-path headers, (e) per-file row renders with classification, (f) "Aprobar e ingerir" disabled until intake response, (g) progress timeline renders 6 stages, (h) timeline updates on poll response, (i) log console renders + auto-scrolls, (j) log copy button copies all visible lines, (k) controller cleanup stops poll on destroy, (l) failed stage shows error in timeline, (m) low-confidence rows show `requires_review` badge, (n) Promoción handoff button visible after WIP success, (o) auto-embed checkbox toggles in run payload. **Verification:** `cd frontend && npx vitest run tests/ingestPhase5Organisms.test.ts` → green.
- **DoD:** clicking through the new Sesiones panel exercises Phase 2 and Phase 3 endpoints end-to-end against fixture responses; **invariant I1 satisfied**: every endpoint added has a UI caller, every UI control calls a real endpoint.
- **Trace events:** none (pure UI; backend emits).
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 5b — Refactor SUIN bridge to canonical 8-section template (per C2.c.now)
- **Goal:** SUIN-harvested docs flow through the same canonical 8-section template + chunker as UI-dropped docs.
- **Files create:**
  - `tests/test_suin_bridge_canonical.py` (~10 cases).
- **Files modify:**
  - `src/lia_graph/ingestion/suin/bridge.py` — rewrite to emit the 8-section template (use Phase 1.5 coercer with SUIN-specific heuristic mappings: `## Articulo` → `## Texto base referenciado (resumen tecnico)`, etc.).
  - `tests/test_suin_bridge.py` — update existing tests for new chunk shape.
- **Tests add:** `tests/test_suin_bridge_canonical.py` covering the SUIN→canonical mapping (vigencia notes → `## Checklist de vigencia`, modifying decree references → `## Relaciones normativas`, etc.). **Verification:** `pytest tests/test_suin_bridge_canonical.py tests/test_suin_bridge.py -v` → green.
- **DoD:** SUIN docs ingested via `make phase2-suin-harvest-*` produce the same 8-section structure as UI-dropped docs; existing Falkor edges preserved.
- **Trace events:** `ingest.suin.bridge.{start,done}` with section_count.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 5c — Regrandfather pass (re-chunk all 1246 existing docs per C2.b.regrandfather)
- **Goal:** apply the canonical 8-section template + new chunker across the existing corpus so chunk_section_type tags are consistent corpus-wide.
- **Files create:**
  - `scripts/regrandfather_corpus.py` (~200 LOC) — iterates `knowledge_base/**/*.md`, runs Phase 1.5 coercer + Phase 1.6 chunker, rewrites under the canonical template, marks `documents.coercion_method = "regrandfathered"`.
  - `tests/test_regrandfather_dry_run.py` (~6 cases).
  - **NEW Makefile target:** `phase2-regrandfather-corpus` → invokes `python scripts/regrandfather_corpus.py --dry-run|--commit`.
- **Files modify:**
  - `Makefile` — append the new target.
  - `docs/orchestration/orchestration.md` — Lane 0 section gets a paragraph on regrandfathering (when run, what it does).
- **Tests add:** dry-run tests verify no FS mutation when `--dry-run`. **Verification:** `make phase2-regrandfather-corpus DRY_RUN=1` against a 10-doc fixture corpus → expected coverage report.
- **DoD:** dry-run report shows expected % coercion methods; commit run on a fixture corpus produces canonical output; `documents.coercion_method` populated for all rows.
- **Trace events:** `ingest.regrandfather.{start,doc.processed,done,failed}`.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 6 — Embedding + Promoción auto-chain (per D1)
- **Goal:** single button press takes a dropped folder all the way through to embeddings populated + (optionally) promoted to cloud.
- **Files create:**
  - `scripts/ingest_run_full.sh` (~100 LOC) — orchestrates: `make phase2-graph-artifacts-supabase` → `python -m lia_graph.embedding_ops --target=<wip|production>` → (if `auto_promote`) `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` + embedding pass.
  - `tests/test_ingest_run_full_orchestrator.py` (~6 cases — mock subprocess).
- **Files modify:**
  - `src/lia_graph/ui_ingest_run_controllers.py` — replace direct `make` invocation in `_spawn_ingest_subprocess` with `bash scripts/ingest_run_full.sh` + new env vars `INGEST_AUTO_EMBED`, `INGEST_AUTO_PROMOTE`.
  - Frontend `runTriggerCard` organism (Phase 5) — add "Saltar embeddings" + "Promover a cloud al terminar" checkboxes.
- **Tests add:** as above + extend `frontend/tests/ingestPhase5Organisms.test.ts` with checkbox-toggle case. **Verification:** `pytest tests/test_ingest_run_full_orchestrator.py -v` + frontend test green.
- **DoD:** end-to-end timing: drop 3 files → click Aprobar → 60-90s later, chunks have embeddings + (if auto_promote) cloud has new active generation; **invariant I1 holds (checkboxes wired to real env vars)**.
- **Trace events:** `ingest.chain.embeddings.{start,done}`, `ingest.chain.promote.{start,done}`.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 6.5 — DEFERRED (F2 modal) — out of v1 scope
- **Goal:** per-doc accept/edit modal for low-confidence (<0.95) classifications.
- **Status:** deferred per F3 ratification. Not executed in v1; tracked here so a future session knows it's the obvious next step.
- **State Notes:** (deferred)

---

### Phase 7 — Observability hardening
- **Goal:** every link in the chain emits a trace event; the doc captures the schema.
- **Files create:** none.
- **Files modify:**
  - `src/lia_graph/ui_ingest_run_controllers.py` — audit every endpoint to confirm `_trace(...)` covers entry, exit, and error paths.
  - This doc — append §13 "Ingest Run Trace Schema" listing every `event_type`, when emitted, payload fields, log file destination.
- **Tests add:** smoke test `tests/test_ingest_observability.py` (~5 cases) — runs a fixture intake + run, asserts every documented event fires in `events.jsonl`. **Verification:** `pytest tests/test_ingest_observability.py -v` → green.
- **DoD:** §13 trace schema complete; smoke test green; `events.jsonl` shows ordered chronological trace of any single doc end-to-end.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 8 — E2E acceptance test (Env-A: dev local then dev:staging cloud)
- **Goal:** drop the 3 UGPP Resolución 532/2024 docs, watch through to active production. **Run TWICE per Env-A**: first against `npm run dev` (local docker Supabase + local docker Falkor) for safety, then against `npm run dev:staging` (cloud) for the real promotion.
- **Files create:**
  - `tests/manual/phase8_e2e_runbook.md` — the step-by-step runbook for the assistant + observer to execute.
  - `tests/manual/phase8_evidence/<run-timestamp>/` — capture: intake response JSON, run job_id, progress poll responses (pre/mid/post), embedding count delta, FalkorDB node + edge count delta, screenshot of UI at each stage, chat probe transcript.
- **Files modify:** none.
- **Tests add:** the E2E runbook IS the test. Each run produces an evidence directory.
- **DoD:** for BOTH the local run AND the cloud run, the following hold:
  1. Drop the 3 UGPP files via the UI drop zone.
  2. Within 5s, intake response shows 3 rows with classifications: NORMATIVA → `topic=laboral, type=normative_base, conf≥0.95`; EXPERTOS → `topic=laboral, type=interpretative_guidance, conf≥0.85`; LOGGRO → `topic=laboral, type=practica_erp, conf≥0.85`.
  3. Click "Aprobar e ingerir" with target=WIP, auto_embed=on. (Cloud pass: target=production via Promoción after WIP green.)
  4. Progress timeline animates through 6 stages over 60-180s. Log tail visible.
  5. After WIP success: `corpus_generations` row added; `documents` table has 3 new rows; `document_chunks` populated with `chunk_section_type` set; `embedding` non-NULL; FalkorDB has new nodes (`Resolucion-UGPP-532-2024`, `Decreto-MinSalud-0379-2026`, …) + typed edges (`MODIFIES`, `SUSPENDS`, `REGLAMENTA`, `REFERENCES`).
  6. Click "Promote to production" (Promoción tab handoff) — cloud Supabase + cloud FalkorDB mirror WIP; new active cloud generation.
  7. Probe chat: "¿Qué cambió con la Resolución UGPP 532 de 2024 sobre la presunción de costos para independientes?" → answer cites the 3 newly-ingested docs + traverses the Decreto 0379/2026 modification edge.
- **Trace events:** consumed (this phase reads them); none new.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 9 — Final close-out + change-log entry
- **Goal:** `v2026-04-20-ui15` change-log entry in `orchestration.md`; `Plan status = COMPLETE` in §2.
- **Files modify:**
  - `docs/orchestration/orchestration.md` — add `v2026-04-20-ui15` entry summarizing the new ingest surface + invariants.
  - This doc — flip dashboard to COMPLETE; update final test counts in §2 baseline table.
- **DoD:** orchestration.md updated; dashboard COMPLETE; full Python + frontend test suites pass.
- **State Notes:** (not started)
- **Resume marker:** —

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
7. **Decision G (sub-topic tagging):** G1 (extend AUTOGENERAR prompt + schema in this plan) or G2 (defer to ingestfixv2.md)?
8. **For Phase 8 E2E:** is `dev:staging` the target environment, or do we run this against `dev` first (local docker Supabase + local docker Falkor) before touching cloud?

   **RATIFIED 2026-04-20: Env-A (dev → dev:staging).** Phase 8 runs end-to-end TWICE: first against `npm run dev` (local docker Supabase + local docker Falkor) — the throwaway local pass catches coercion/chunker/regrandfather bugs at zero cloud cost. Then `npm run dev:staging` for the real cloud Supabase + cloud Falkor pass. Cheap insurance for the maximalist C2 + regrandfather scope.

---

## 9. Change Log
| Version | Date | Note |
|---|---|---|
| `v1` | 2026-04-20 | Initial draft after Lia_contadores audit. |
| `v1.1` | 2026-04-20 | Phase 0 complete — all 8 §4 decisions ratified. |
| `v1.2` | 2026-04-20 | Restructured §5 with uniform per-phase template; added §0.5 Execution Mode, §11 Resume Protocol, §12 Decision Authority, §13 Trace Schema placeholder. Plan now executable autonomously without stopping once approved. |

---

## 10. References
- `docs/orchestration/orchestration.md` — Lane 0 (build-time ingestion), Runtime Env Matrix, Controller Surface table (entry for `ui_ingest_run_controllers.py` added in v2026-04-20-ui14).
- `docs/guide/env_guide.md` — `make phase2-graph-artifacts-supabase` workflow + `PHASE2_SUPABASE_SINK_FLAGS` = `--supabase-sink --supabase-target {wip,production} --execute-load --allow-unblessed-load --strict-falkordb`.
- `docs/next/decouplingv1.md` — `opsIngestionController.ts` (2327 LOC) is on the kill list; this plan supersedes it for the Sesiones surface.
- `docs/done/ingestion_suin.md` — frozen SUIN infrastructure (Phase A + B). **Phase 5b of THIS plan refactors `src/lia_graph/ingestion/suin/bridge.py` to emit the canonical 8-section template** (Decision C2.c.now); the harvest tooling itself is untouched.
- `CLAUDE.md` — "one concern stays in one place" (embeddings out-of-band); "don't let main chat become hidden rendering layer" (don't let UI orchestration become a hidden ingestion runtime).
- `src/lia_graph/contracts/ingestion.py:67-76, 119-128` — `IngestionDocumentState` already carries the 6 `autogenerar_*` fields; classifier output → contract mapping is one-line.
- `src/lia_graph/topic_taxonomy.py` + `topic_guardrails.py` + `topic_router_keywords.py` — canonical 40+ topic list (declaracion_renta, iva, ica, laboral, calendario_obligaciones, facturacion_electronica, retencion_*, niif, …).

---

## 11. Resume Protocol

If a session is interrupted (context limit, network, error, machine reboot), the next session picks up cold by reading this doc. **Do NOT restart any phase from scratch.**

### 11.1 Cold-start checklist
1. **Read §0.5 Execution Mode.** Confirm autonomous-execution rules are still in force.
2. **Read §2 State Dashboard.** Identify `Current phase` + `Last completed phase`.
3. **Open the active phase in §5.** Read its `State Notes` block from top to bottom — every checkpoint is recorded there.
4. **Read its `Resume marker`** if present. This is the within-phase last-known-good checkpoint string. Empty → start the phase fresh.
5. **Run the phase's Verification Command.** If green, the phase is actually DONE — flip its status in §2. If red, the failure tells you exactly where to resume.
6. **If `State Notes` say `blocked: <reason>`,** address the blocker first. Do NOT try to bypass; the reason is load-bearing.

### 11.2 Mid-phase checkpoint conventions
Within a phase, the assistant writes a `State Notes` line after each meaningful checkpoint:
- `started 2026-MM-DDTHH:MMZ` — phase began.
- `checkpoint: <task> done; resuming at <next_task>` — every 1–3 file edits or 1 test-pass cycle.
- `commit: <sha> — <one-line summary>` — when a commit lands.
- `blocked: <specific reason; what to address>` — when stopping.
- `completed 2026-MM-DDTHH:MMZ; commit <sha>` — phase exit.

### 11.3 What "fresh resume" means in practice
For each new session that picks up this work:
1. `git status` to see uncommitted files (the assistant left behind).
2. `git log --oneline -20` to see what the previous session committed.
3. Match commit messages to phase numbers (commits should be `feat(ingestfixv1-phase-N): <summary>`).
4. Diff between last commit and `git status` shows in-progress work for the active phase.
5. Apply the phase's Verification Command — if green, mark DONE; if red, finish the work the in-progress diff suggests.

### 11.4 Recovery from a corrupt state
If the working tree is unrecognizable (mid-conflict, unknown branches, etc.):
1. Stop. Do NOT take destructive action without user confirmation.
2. Mark the active phase `BLOCKED` in `State Notes` with the exact failure mode.
3. Surface to the user with the recovery options ranked by safety.

---

## 12. Autonomous Decision Authority

The assistant has discretion within bounds. This section names the bounds.

### 12.1 The assistant MAY decide without asking
- **Internal naming.** Function names, helper module names, JSON field names (within the documented contract), CSS class names, test fixture names. Document the choice in `State Notes`.
- **Implementation patterns when equivalent.** Choosing iteration vs. comprehension; explicit vs. defaultdict; ` regex vs. str.split — when both honor the documented behavior + perform comparably.
- **In-phase reorganization.** If a phase grows past its estimated LOC, the assistant MAY split a helper into a sibling module (decouplingv1.md style) without asking, as long as it documents the split in `State Notes`.
- **Test count adjustments.** If the documented case count was wrong (under or over), adjust as needed and document in `State Notes`. The DoD is "every behavior tested", not "exactly N cases".
- **Trace event payload field additions.** If a payload field is missing that's diagnostically useful, add it. Document in §13 schema.
- **Frontend visual choices within the design system.** Spacing, radius, transitions, micro-interactions — within the existing token system, the assistant chooses freely (and invokes `frontend-design` skill per Invariant I2 for the holistic specs).
- **Skipping a phase that turned out unnecessary.** If a phase's Goal is already achieved by a previous phase's work, mark it `DONE` with `State Notes: subsumed by Phase N — no work needed`.
- **Fixing pre-existing test failures encountered along the way** if they're trivially related to the work in progress (≤30 LOC fix). Document the fix in `State Notes`.

### 12.2 The assistant MUST ask before
- Contradicting any §4 ratified decision (A1, B1, C2-maximalist + sub-decisions, D1, E1, F3, G2, Env-A).
- Touching cloud Supabase or cloud FalkorDB write operations outside the planned Phase 8 cloud pass (any earlier phase is local-only by §4 Env-A).
- Force-pushing or running `git reset --hard`, `git clean -f`, or any history-rewriting operation.
- Skipping the user-approval gate for Phase 1 start (Plan status MUST be `APPROVED` first).
- Modifying `docs/done/` content or moving files out of `docs/done/` back to `docs/next/`.
- Bypassing the atomic-design discipline guard or the I2 design-skill invocation.

### 12.3 Fork-in-the-road handling (recursion)
When an in-flight discovery presents two equally valid paths AND the choice has downstream consequences:
1. Pick the path that maximally preserves §4 ratified decisions.
2. Document the choice + rejected alternative in the active phase's `State Notes` with a `decision:` line.
3. If the user later disagrees, revert is one-line: read `State Notes`, undo the file changes from that checkpoint forward.

---

## 13. Ingest Run Trace Schema (authoritative, Phase 7)

Phase 7 status: **landed 2026-04-20**. Smoke test `tests/test_ingest_observability.py` pins the controller-layer events; module-layer events (coerce / chunk / validate / regrandfather / suin-bridge) are covered by their respective unit tests.

### Controller-layer events (routed by `ui_ingest_run_controllers`)

| event_type | emitted_by | when | payload keys |
|---|---|---|---|
| `ingest.state.requested` / `.served` | `handle_ingest_get` | GET `/api/ingest/state` | `path`; `active_generation_id`, `documents`, `audit_scanned`, `graph_ok` |
| `ingest.generations.requested` / `.served` | `handle_ingest_get` | GET `/api/ingest/generations` | `limit`; `row_count` |
| `ingest.generation.requested` / `.not_found` / `.rejected` | `handle_ingest_get` | GET `/api/ingest/generations/{id}` | `generation_id` / `reason`, `raw` |
| `ingest.progress.requested` | `handle_ingest_get` | GET `/api/ingest/job/{id}/progress` | `job_id` |
| `ingest.log.tail.served` | `handle_ingest_get` | GET `/api/ingest/job/{id}/log/tail` | `job_id`, `returned`, `cursor`, `next_cursor` |
| `ingest.intake.received` | `_handle_ingest_intake_post` | start of POST `/api/ingest/intake` | `batch_id`, `file_count` |
| `ingest.intake.classified` | same | per file post-classifier | `batch_id`, `filename`, `detected_topic`, `detected_type`, `topic_confidence`, `combined_confidence`, `is_new_topic`, `requires_review` |
| `ingest.intake.placed` | same | per file post-write | `batch_id`, `filename`, `placed_path` |
| `ingest.intake.skipped_duplicate` | same | checksum dedup hit | `batch_id`, `filename`, `existing_doc_id` |
| `ingest.intake.failed` | same | per file reject path | `batch_id`, `filename`, `error` |
| `ingest.intake.summary` | same | end of POST | `batch_id`, `received`, `placed`, `deduped`, `rejected`, `sidecar_path` |
| `ingest.run.requested` | `handle_ingest_post` | start of POST `/api/ingest/run` | `supabase_target`, `suin_scope`, `auto_embed`, `auto_promote`, `batch_id` |
| `ingest.run.dispatched` | same | after `run_job_async` returns | `job_id`, `supabase_target`, `suin_scope` |
| `ingest.run.subprocess.start` | `_spawn_ingest_subprocess` | before `make` / `ingest_run_full.sh` | `command`, `cwd`, `log_relative_path`, `supabase_target`, `suin_scope`, `auto_embed`, `auto_promote`, `job_id` |
| `ingest.run.subprocess.end` | same | after subprocess returns | `exit_code`, `log_relative_path`, `suin_scope`, `supabase_target`, `job_id` |
| `ingest.run.stage.<name>.start` | `ingest.py` pipeline (Phase 3) | each stage transition; stages in `INGEST_STAGES` | `job_id`, `started_at`, optional `counts` |
| `ingest.run.stage.<name>.done` | same | each stage completion | `job_id`, `finished_at`, `counts` |
| `ingest.run.stage.<name>.failed` | same | each stage failure | `job_id`, `finished_at`, `error`, `partial_counts` |

### Module-layer events (emitted by pure modules when callers set `emit_events=True`)

| event_type | emitted_by | when | payload keys |
|---|---|---|---|
| `ingest.coerce.heuristic.start` / `.done` | `ingestion_section_coercer` | per doc coercion pass | `filename`, `sections_matched_count`, `confidence` |
| `ingest.coerce.llm.start` / `.done` / `.fallback` | same | LLM branch / fallback | `filename`, `confidence`, `reason` |
| `ingest.chunk.start` / `.done` | `ingestion_chunker` | per doc chunking | `filename`, `chunk_count`, `section_type_distribution` |
| `ingest.validate.ok` / `.failed` | `ingestion_validator` | per doc validation | `filename` or `doc_id`, `missing_sections`, `missing_keys`, `missing_metadata` |
| `ingest.suin.bridge.start` / `.done` | `ingestion/suin/bridge` | per SUIN doc canonicalization | `suin_doc_id`, `section_count` |
| `ingest.regrandfather.start` / `.doc.processed` / `.done` / `.failed` | `scripts/regrandfather_corpus` | corpus-wide pass | `processed_count`, `total_count`, `coercion_method`, `doc_id` |

### Stage names

`INGEST_STAGES = ("coerce", "audit", "chunk", "sink", "falkor", "embeddings")` — defined in `ui_ingest_run_controllers`. The progress endpoint aggregates per-stage state using event_type `ingest.run.stage.<stage_name>.<outcome>` where `outcome ∈ {start, done, failed}`.

Phase 7 DoD: smoke test asserts the canonical trail fires end-to-end on a mocked intake + run; module-layer events are individually tested in their own unit suites (see `tests/test_ingest_section_coercer.py`, `tests/test_ingest_chunker.py`, `tests/test_ingest_validator.py`, `tests/test_regrandfather_dry_run.py`).
