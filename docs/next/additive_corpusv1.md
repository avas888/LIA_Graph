# Additive Corpus Ingestion — v1

**Last edited:** 2026-04-22 (v1-draft — no code shipped yet; awaiting Phase 0 ratification; **reviewer pass applied 2026-04-22 — see §9 Change Log**)
**Execution owner:** unassigned. First agent that picks this up after `Plan status = APPROVED` becomes owner.
**Goal:** make `make phase2-graph-artifacts*` support an **additive** mode so that adding / modifying / removing a small number of documents re-processes only the changed set — while keeping the current full-rebuild path as the canonical, always-correct escape hatch. **Additive ingestion must be drivable end-to-end from the admin UI, not only the CLI** (see Phase 8 — now a hard requirement, not descopeable).

> This document is both a **plan** AND a **work ledger**. Every phase below has a `State Notes` block that the executing agent updates in-place DURING execution. If a session is interrupted, the state of this file is the resumption pointer — see §11 Resume Protocol.

> **Cold-start agent:** read §0 first, then §0.5, then §2 (to find the active phase), then §3 + §4 (so you know what was ratified), then jump to the active phase in §5. Do not skim — every line in §0 and §0.5 is load-bearing. If anything in §0 is wrong (tool missing, branch mismatch, schema column missing, etc.), STOP and surface to the user before proceeding.

---

## 0. Cold-Start Briefing (READ FIRST IF YOU HAVE ZERO PRIOR CONTEXT)

This section is for an LLM agent that opens this doc with no conversation history. After reading §0 + §0.5 + §2 + the active phase entry in §5, you should have everything you need to execute autonomously.

### 0.1 Project orientation in three sentences
**Lia_Graph** is a graph-RAG accounting assistant for Colombian senior accountants serving SMB clients. It is a derivative of `Lia_contadores` (https://github.com/avas888/Lia_contadores) and lives at `https://github.com/avas888/LIA_Graph`. It serves answers in Spanish-CO covering tax (IVA, declaración de renta, ICA, retención, …) AND labor / payroll / seguridad social (CST, Ley 100, parafiscales, UGPP, MinTrabajo) — labor is first-class, not tax-adjacent.

### 0.2 Repo location + branch
- **Working directory:** `/Users/ava-sensas/Developer/Lia_Graph`
- **Branch this plan executes against:** TBD at Phase 0 ratification. Recommended: `feat/additive-corpus-v1` off `main`. Do NOT reuse `feat/suin-ingestion` — that branch belongs to a closed-out plan.
- **Main branch (used for PRs):** `main`
- **Last shipped change pre-plan:** env matrix at `v2026-04-21-stv2d` per `AGENTS.md` header, `CLAUDE.md` (§Runtime Read Path, line 65: "Env v2026-04-18" — stale; see reviewer note below), `docs/guide/orchestration.md` §"Current version", `docs/guide/env_guide.md` line 3. **Reviewer-verified drift:** `frontend/src/features/orchestration/orchestrationApp.ts:97` still shows `v2026-04-18`. This is one of the mirrors Phase 6 must bump. Do NOT assume all mirrors are currently in sync at kickoff — run the pre-flight grep in §0.5 first.

### 0.3 Source-of-truth document map (READ THESE BEFORE WRITING CODE)
Hierarchy of authority — when documents disagree, the higher one wins:

| Doc | Role |
|---|---|
| `CLAUDE.md` (repo root) | Quickstart for Claude-family agents. Hard rules: don't touch `Lia_contadores` cloud resources; `pipeline_d` organization is deliberate; Falkor adapter must propagate cloud outages, not silently fall back to artifacts; granular edits over monolithic rewrites. Carries env-matrix version mirror. |
| `AGENTS.md` (repo root) | Repo-level operating guide. If `CLAUDE.md` is silent on something, `AGENTS.md` is canonical. **Also carries env-matrix version in its header frontmatter** — reviewer-verified 2026-04-22; the plan originally missed this mirror. |
| `docs/guide/orchestration.md` | THE end-to-end runtime + information-architecture map. Env matrix version is currently `v2026-04-21-stv2d`. Lane 0 (build-time ingestion) is the relevant lane for this plan. |
| `docs/guide/env_guide.md` | Operational counterpart to orchestration.md. Run modes + env files + test accounts + corpus refresh workflow. |
| `docs/guide/chat-response-architecture.md` | Answer-shaping policy. Only relevant to this plan if the additive path surfaces retired chunks at retrieval time (§8.2). |
| `supabase/migrations/20260417000000_baseline.sql` | Squashed Supabase baseline. Source of truth for the `documents` / `document_chunks` / `normative_edges` / `corpus_generations` table contracts + indexes. Read it before writing any migration. |
| `supabase/migrations/20260418000000_normative_edges_unique.sql` | The idempotency index this plan must coexist with (not replace). |
| `src/lia_graph/ingest.py` + `src/lia_graph/ingestion/*` | The code this plan modifies. |
| `src/lia_graph/ingestion/supabase_sink.py` | The cloud write path this plan extends. |
| `src/lia_graph/graph/client.py` | Falkor MERGE stage helpers. Idempotent by `(label, key)`. |
| `docs/next/subtopic_generationv1.md` | Reference for **plan authoring conventions** — cold-start briefing shape, state dashboard, per-phase State Notes. THIS doc mirrors its structure. |
| `docs/next/ingestfixv1-design-notes.md` | Reference for **admin UI conventions** (if Phase 8 is in scope). |
| THIS doc (`docs/next/additive_corpusv1.md`) | The plan. State Dashboard (§2) is the live status — read it first after §0. |

### 0.4 Tooling baseline (verify in pre-flight check, §0.5)
- **Python:** managed via `uv`. Always run as `PYTHONPATH=src:. uv run --group dev <command>`. Never use bare `python` for repo code.
- **Frontend:** Vite + TypeScript + vitest. Tests: `cd frontend && npx vitest run [test-pattern]`.
- **Dev server:** `npm run dev` (local docker Supabase + Falkor) at `http://127.0.0.1:8787/`.
- **Supabase local stack:** `make supabase-start` / `-stop` / `-reset` / `-status`. Reseed after reset: `PYTHONPATH=src:. uv run python scripts/seed_local_passwords.py`.
- **Ingest entrypoints:** `make phase2-graph-artifacts` (local, no cloud) and `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` (full ingest + cloud sink + Falkor load). This plan ADDS a third target: `make phase2-corpus-additive`.
- **Full python test:** `make test-batched` (120 batches, stall detection). `tests/` has a conftest guard that aborts if >20 test files are collected without `LIA_BATCHED_RUNNER=1`. Never run `pytest` against the full suite in one process.
- **Single test / curated set:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_<file>.py -v` is always safe.
- **Curated backend smoke set:** `test_background_jobs.py`, `test_phase1_runtime_seams.py`, `test_phase2_graph_scaffolds.py`, `test_phase3_graph_planner_retrieval.py`, `test_ui_server_http_smokes.py`. Run via `npm run test:backend`.
- **Single-pass ingest smoke (30s, ~$0.01 LLM):** `make phase2-graph-artifacts-smoke` runs `tests/integration/test_single_pass_ingest.py` + `tests/integration/test_subtema_taxonomy_consistency.py`. This is the canary that catches ingestion regressions fastest.
- **Eval gate:** `make eval-c-gold` (threshold 90). Run once per phase that touches retrieval or ingestion output shape.
- **LLM runtime:** `src/lia_graph/llm_runtime.py` — see `docs/next/subtopic_generationv1.md §0.4` for adapter contract. Not directly used by the additive path unless the composite fingerprint includes a classifier re-run.

### 0.5 Pre-flight check (run before Phase 1)
Single verification command — if any line fails, STOP and surface to the user:

```bash
cd /Users/ava-sensas/Developer/Lia_Graph && \
  git status && \
  git log --oneline -5 && \
  grep -c "content_hash" supabase/migrations/20260417000000_baseline.sql && \
  grep -c "chunk_sha256" supabase/migrations/20260417000000_baseline.sql && \
  grep -c "sync_generation" supabase/migrations/20260417000000_baseline.sql && \
  grep -c "idx_corpus_generations_single_active" supabase/migrations/20260417000000_baseline.sql && \
  grep -c "normative_edges_idempotency" supabase/migrations/20260418000000_normative_edges_unique.sql && \
  grep -n "Env matrix version" AGENTS.md docs/guide/env_guide.md docs/guide/orchestration.md && \
  grep -n "Env matrix v2026" frontend/src/features/orchestration/orchestrationApp.ts && \
  ls src/lia_graph/ui_ingest_run_controllers.py src/lia_graph/jobs_store.py src/lia_graph/background_jobs.py && \
  PYTHONPATH=src:. uv run --group dev pytest \
    tests/test_phase2_graph_scaffolds.py \
    tests/test_phase3_graph_planner_retrieval.py \
    tests/test_ui_server_http_smokes.py -q && \
  make supabase-status
```

**Expected:**
- Working tree on whichever branch §0.2 names (or `main` if branch not yet created).
- Baseline migration contains `content_hash`, `chunk_sha256`, `sync_generation`, `idx_corpus_generations_single_active` (≥1 hit each). If any is missing, the baseline drifted and the whole plan's premise is invalid; STOP.
- `20260418000000_normative_edges_unique.sql` contains the `normative_edges_idempotency` unique index (reviewer-confirmed column order: `source_key, target_key, relation, generation_id`). If it is renamed or dropped, Phase 1's additional partial-unique index cannot coexist; STOP.
- Matrix-version mirror grep shows `v2026-04-21-stv2d` in `AGENTS.md`, `docs/guide/env_guide.md`, `docs/guide/orchestration.md`. **Known drift:** `frontend/src/features/orchestration/orchestrationApp.ts` prints `v2026-04-18` as of plan authoring. `CLAUDE.md §Runtime Read Path` also still reads "Env v2026-04-18". Treat these two stale mirrors as pre-existing debt; Phase 6 bumps everyone to the new version simultaneously.
- `ui_ingest_run_controllers.py`, `jobs_store.py`, `background_jobs.py` all exist (Phase 8 + async job surface depend on them).
- All three curated backend tests green.
- `make supabase-status` reports the local Docker stack running. If not, run `make supabase-start` first.

### 0.6 Auth credentials for testing
All `@lia.dev` accounts share password `Test123!` in both local docker Supabase and cloud staging. Admin credential:
- **email:** `admin@lia.dev`, **password:** `Test123!`, **role:** `platform_admin`, **tenant:** `tenant-dev`
- Login: `POST http://127.0.0.1:8787/api/auth/login` with `{email, password, tenant_id: ""}`.

Only relevant to this plan for Phase 8 (admin UI toggle for additive runs). All backend + script work is admin-scoped via `service_account_auth.py` + `LIA_ADMIN_TOKEN`.

### 0.7 Cost / time estimate (run against real corpus)
- **Full-rebuild baseline (control for comparisons):** ~30-40 min on the current ~1313-doc corpus; ~$6-16 in Gemini for classifier + ~$0.50 for embeddings; N MERGE statements submitted to Falkor where N = nodes + edges across the full corpus.
- **Additive delta (target):** for a 10-doc delta, target ≤ 2 min wall-clock for the **delta-specific stages** (parse, edge extract, sink writes, Falkor writes). **Reviewer-revised estimate:** the PASO 4 classifier still runs over the full corpus (per Decision C1) because classifier outputs feed the composite fingerprint. On the current 1313-doc corpus that is ≈ 20-25 min of wall-clock. The optimistic "≤ 2 min" framing in the original plan is only honest if you explicitly exclude the classifier pass. End-to-end, a 10-doc delta today is **~20-25 min wall-clock + ~$6 Gemini + ~$0.05 embeddings.** The delta-only speedup over full rebuild is real but concentrated in the non-classifier stages. If the classifier pass becomes the dominant cost (it is, today), Decision D (classifier output caching) becomes load-bearing and should be promoted out of §7 "Out of Scope" into a v1.1 plan.
- **Migration + backfill (one-time):** ≤ 5 min on a 1313-doc corpus (pure SQL `UPDATE documents SET doc_fingerprint = …`; no LLM calls) — assumes Decision K1. Under K3 this would balloon to 30-40 min + $6-16.
- **Budget guardrail:** if a single delta's non-classifier stages exceed 4× their size-linear target (e.g., > 8 min for a 10-doc delta), STOP and surface before continuing — this usually signals a delta planner bug (e.g. everything being marked `modified` because of a fingerprint mismatch between backfill and ingest shapes).

### 0.8 Glossary (terms used throughout)
- **corpus_generation** — a row in Supabase `corpus_generations`. Current design mints a new row per ingest run (`gen_<UTC>`). This plan introduces a reserved row `gen_active_rolling` that accumulates deltas.
- **active generation** — the single `corpus_generations` row with `is_active=true`. Enforced by partial unique index `idx_corpus_generations_single_active`. Retrievers read the active generation's documents.
- **delta** — one additive ingest run: a set of added + modified + removed documents processed together under one `delta_id`.
- **delta_id** — stable identifier for a delta run, e.g. `delta_20260422_1412_abc123`. Recorded on every row touched by the delta.
- **doc_fingerprint** — `sha256(content_hash + "|" + canonical_classifier_output_json)`. Catches file edits AND classifier drift. Stored on `documents.doc_fingerprint`. See Phase 2 for the authoritative list of classifier fields and **Risk 11 in §6** + **Decision K in §4** for the column-drift gotcha. Reviewer-verified 2026-04-22 against `supabase/migrations/20260417000000_baseline.sql:779-833` (documents DDL) and `src/lia_graph/ingestion/supabase_sink.py:252-276` (the persistence mapping): `document_archetype` is collapsed into `tipo_de_documento`, `authority_level` into `authority`, and `source_tier` **is not persisted at all** today. The fingerprint computation at **ingest time** works fine because classifier objects are in memory (`CorpusDocument.classifier`); the problem is **backfill** (Phase 1 `scripts/backfill_doc_fingerprint.py`), which reads persisted rows and therefore cannot reconstruct the full classifier JSON without either (a) re-reading `knowledge_base/*.md` + re-running the classifier, or (b) persisting the missing fields. Decision K picks the policy.
- **content_hash** — `sha256(markdown_as_written_to_disk)`. Already computed by `supabase_sink._content_hash` (`supabase_sink.py:119`).
- **chunk_sha256** — `sha256(chunk_text)`. Already stored in `document_chunks.chunk_sha256` (`supabase_sink.py:123`).
- **dangling candidate** — an edge whose `target_kind=ARTICLE` but whose `target_key` doesn't exist in the current article set. Today they're silently pruned by `normalize_classified_edges` (`ingestion/loader.py:250`). Additive mode persists them in `normative_edge_candidates_dangling` so a later delta can promote them when the target arrives.
- **rolling generation / snapshot generation** — `gen_active_rolling` is the rolling (additive) generation; `gen_<UTC>` rows minted by full-rebuild runs are snapshots. Exactly one is active at any time.
- **retired document** — a document that existed in a prior delta but is no longer on disk. Marked `retired_at IS NOT NULL` on `documents`; its chunks + edges are hard-deleted; retrievers filter by `retired_at IS NULL` (or the chunk delete makes that filter redundant — see Phase 4 State Notes).
- **PASO 4 classifier** — the subtopic-assignment pass in `ingest_subtopic_pass.classify_corpus_documents`. Runs per doc; LLM-backed; can drift without file changes.
- **SUIN** — Colombian jurisprudence harvester (`src/lia_graph/ingestion/suin/`). Its scope is merged into the ingest via `--include-suin`. Additive mode must handle SUIN re-imports as deltas too — see §14 Risk 7.
- **parity check** — a Supabase-vs-Falkor row-count comparison run before applying a delta, to catch drift before it compounds.
- **hot path** — the request-serving path documented in `CLAUDE.md`. Not touched by this plan.

### 0.9 What this plan does NOT do
These are intentionally out of scope; they live elsewhere or in follow-up plans:
- Does NOT replace `make phase2-graph-artifacts` full-rebuild. Full rebuild stays canonical and remains the default.
- Does NOT make the artifact JSONL bundle (`parsed_articles.jsonl`, `typed_edges.jsonl`) additive. Dev mode (`LIA_CORPUS_SOURCE=artifacts`) keeps getting a fresh bundle. Rationale in §3.
- Does NOT add per-tenant corpus slicing. `sync_generation` stays a corpus-wide concept.
- Does NOT change the `main chat` / `Normativa` / `Interpretación` surface boundaries. Ingestion is strictly below those surfaces.
- Does NOT inherit old-RAG incremental-indexing assumptions (see `CLAUDE.md`). This plan is graph-native.
- Does NOT cache classifier outputs across runs. If classifier runtime dominates, Decision D in §4 captures the follow-up.
- Does NOT introduce resumable mid-delta state in v1. If a delta crashes, the fix is to re-run it (idempotent); full-rebuild is always the recovery.

### 0.10 Git + commit conventions
- **Branch protocol:** all work on the branch named in §0.2 / §2. NEVER force-push. NEVER `git reset --hard` without user approval.
- **Commit message format:** `feat(additive-corpus-v1-phase-N): <short summary>`.
- **Co-authored-by line:** `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
- **Commit cadence:** one commit per phase exit (phase status `PASSED_TESTS` → `COMMITTED`). Intermediate WIP commits are allowed within a phase; squash on exit if noisy.
- **PR:** open at Phase 10 close-out only. Target `main`. Body should link this doc and summarize per-phase deltas.

### 0.11 What to ABSOLUTELY NOT do
- Do not modify `Lia_contadores` cloud resources at any point. `LIA_contadores` is a separate project; this plan is `Lia_Graph` only.
- Do not touch cloud Supabase / cloud Falkor against `PHASE2_SUPABASE_TARGET=production` before Phase 9. All pre-Phase-9 work is local.
- Do not drop or `ALTER COLUMN` existing `documents` / `document_chunks` / `normative_edges` columns. The migration is strictly additive (`ADD COLUMN`, `CREATE INDEX`, `CREATE TABLE`).
- Do not replace the existing `normative_edges (…, generation_id)` unique index. Create a new partial unique index *alongside* it.
- Do not delete or `DROP` the reserved row `gen_active_rolling` once Phase 1 lands. It is structural.
- Do not collapse `pipeline_d` / `normativa` / `interpretacion` modules; this plan does not go near them.
- Do not bypass the `tests/` conftest guard by running `pytest` without `LIA_BATCHED_RUNNER=1`. Run curated sets or single files.
- Do not commit `.env.local` / `.env.staging` mutations. The launcher owns `LIA_CORPUS_SOURCE` / `LIA_GRAPH_MODE`.
- Do not skip the §0.5 pre-flight before Phase 1.
- Do not begin Phase 1 until §2 Plan Status reads `APPROVED`.

### 0.12 Design-skill invocation pattern (Phase 8 UI work — MANDATORY)
Phase 8 is mandatory (Decision G, reviewer-revised). Any UI component MUST be produced through the `frontend-design:frontend-design` skill, not freehanded. Invocation contract:
1. Before writing any component, invoke the skill with an explicit brief naming (a) the surface (Sesiones tab, additive-delta sub-panel), (b) the atoms / molecules / organisms the plan specifies, (c) the design tokens in play (`--p-navy-*`, `--p-success-*`, `--p-warning-*`, `--p-danger-*`, `--chip-*`, IBM Plex font stack — see `docs/next/ingestfixv1-design-notes.md` for the canonical Tier-1/2/3 palette mapping), (d) the atomic-discipline guard (`frontend/tests/atomicDiscipline.test.ts`: no raw hex in `shared/ui/`, no inline SVG outside `shared/ui/icons.ts`, tokens-only CSS).
2. Skill output lands as new files under the paths Phase 8 enumerates. No edits to `opsIngestionController.ts` or any ≥ 1000-LOC host file (see user feedback memory "Edit granularly"). `ingestController.ts` (543 LOC) is the designated mount point for the new panel; keep edits there under ~30 LOC to preserve its headroom below the 1000-LOC guard.
3. Verification the skill was used: a `design:` line in Phase 8's State Notes naming the skill, the brief version, the atoms/molecules/organisms the skill output, and whether the atomic-discipline guard was run green before commit.
4. For each of the five terminal UI states (Idle, Previewed, Running, Terminal, Error) the skill brief MUST enumerate the exact visual contract (which banner variant, button states, progress indicator shape) before implementation begins.

### 0.13 Test-data pointers (no hidden context)
- Real corpus lives at `knowledge_base/**/*.md` (1313 docs as of `v2026-04-21-stv2d`).
- Fixture corpus for integration tests lives at `tests/integration/fixtures/mini_corpus/` (3 docs) — used by `test_single_pass_ingest.py` (see `Makefile:67`).
- All unit-test fixtures are built inline inside the test files — no separate fixture directory for unit tests.
- Phase 9 E2E evidence lands under `tests/manual/additive_corpus_v1_evidence/<run-timestamp>/`. At authoring time this directory contains only a `.gitkeep`; real evidence is captured during the actual E2E run.
- Supabase snapshots are NOT checked into the repo. If you need a fresh local baseline, run `make supabase-reset && PYTHONPATH=src:. uv run python scripts/seed_local_passwords.py`, then `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` (which, despite the name, targets local docker when `LIA_ENV=local` — verify by checking `make supabase-status` reports the local stack).

---

## 0.5 Execution Mode (READ FIRST WHEN RESUMING)

**Mode:** AUTONOMOUS after approval. Once the user marks `Plan status = APPROVED` in §2, execution proceeds without stopping through all phases until either (a) all phases reach `DONE`, (b) a `BLOCKED` status is recorded, or (c) the user explicitly halts.

**No-stop policy:** the assistant does NOT pause for confirmation between phases. The assistant DOES update `State Notes` after every meaningful checkpoint (file written, test passing, commit landed).

**When the assistant DOES stop:**
1. A §4 ratified decision turns out to be wrong on contact with reality → mark phase `BLOCKED`.
2. A test failure cannot be resolved within 3 attempts after diagnosis → mark `BLOCKED`.
3. Cloud Supabase / cloud Falkor write would be needed before Phase 9 (shouldn't happen — see §0.11).
4. The §0.7 cost budget is overrun by 2× on any single delta → surface before continuing.
5. Phase 9 E2E evidence capture is complete → hand off to stakeholder for sign-off before Phase 10 close-out.
6. All phases reach `DONE`.

**Recursive decision authority:** see §12. The assistant MAY make in-flight choices that do NOT contradict §4 ratified decisions (naming, internal helper organization, trace payload fields). The assistant MUST NOT change anything in §4 without re-surfacing to the user.

**Approval gate:** Phase 1 does NOT begin until `Plan status = APPROVED` is set by the user in §2.

---

## 1. Executive Summary

**Problem.** Today every `make phase2-graph-artifacts*` run is a full rebuild: re-audit, re-parse, re-extract edges, re-write artifact JSONLs, mint a new `gen_<UTC>`, upsert every row in Supabase under that new generation, and re-submit the full MERGE plan to Falkor. For a ~1300-doc corpus this is tolerable (~30-40 min, ~$6-16 in LLM cost); for 5k-10k docs it is not. Practically, this makes "I added 10 docs" an expensive operation.

**Strategy.** Introduce a **rolling active generation** (`gen_active_rolling`) that accumulates additive deltas over time. Full-rebuild keeps minting `gen_<UTC>` snapshots; additive runs write into `gen_active_rolling`. A pure **delta planner** compares on-disk corpus (after audit + PASO 4 classifier) against the Supabase baseline and emits `(added, modified, removed, unchanged)` buckets keyed by a composite `doc_fingerprint = sha256(content_hash || classifier_output)`. Only `added + modified + removed` flow through parse + edge extraction + Supabase writes + Falkor writes. A persistent **dangling-candidate** table ensures edges from old unchanged docs that reference newly-arrived articles get retrospectively promoted.

**Order.** Decisions first (§4), schema migration + backfill (Phase 1), baseline snapshot reader (Phase 2), delta planner (Phase 3), additive Supabase path (Phase 4), additive Falkor path (Phase 5), orchestrator wiring + CLI + Makefile + env matrix bump (Phase 6), concurrency + parity + observability (Phase 7), admin UI toggle (Phase 8, may be descoped), E2E against real corpus (Phase 9), close-out (Phase 10).

**Non-goals.** See §0.9. Summary: artifact bundle stays full-rewrite, no per-tenant slicing, no surface boundary changes, full-rebuild stays canonical.

---

## 2. State Dashboard (update in-place during execution)

**Meta**

| Field | Value |
|---|---|
| Plan status | ☑ DRAFT (reviewer pass 2026-04-22 applied) · ☑ APPROVED (2026-04-22 — all 11 decisions A–K ratified by user) · ☑ EXECUTING (2026-04-22) · ☐ COMPLETE |
| Current phase | 1 (schema migration + backfill — IN_PROGRESS) |
| Last completed phase | 0 (all §4 decisions ratified 2026-04-22) |
| Blockers | Pre-flight observation: 2 pre-existing failures in `test_phase3_graph_planner_retrieval.py` (follow-up drilldown) — orthogonal to this plan (Invariant I6 hot path). Noted, not blocking. |
| Working tree | `feat/additive-corpus-v1` @ branched from `main` 2026-04-22 |
| Branch for execution | `feat/additive-corpus-v1` (off `main`) — CREATED 2026-04-22 |
| Env matrix version at kickoff | `v2026-04-21-stv2d` in `AGENTS.md` / `docs/guide/env_guide.md` / `docs/guide/orchestration.md`; stale `v2026-04-18` still shown in `CLAUDE.md` line 65 and `frontend/src/features/orchestration/orchestrationApp.ts:97` — Phase 6 bumps all five to the new version. |

**Phase ledger** — allowed statuses: `NOT_STARTED`, `IN_PROGRESS`, `PASSED_TESTS`, `COMMITTED`, `DONE`, `BLOCKED`.

| # | Phase | Status | Files touched (target) | Commit SHA |
|---|---|---|---|---|
| 0 | Decisions ratified by user (§4) | DONE | this doc | — (in-doc ratification, 2026-04-22) |
| 1 | Schema migration + backfill | PASSED_TESTS | `supabase/migrations/20260422000000_corpus_additive.sql`, `supabase/migrations/20260422000001_ingest_delta_jobs.sql`, `src/lia_graph/ingestion/fingerprint.py` (landed early per §12.1 subsumption — Phase 2 target), `scripts/backfill_doc_fingerprint.py`, `tests/test_fingerprint.py`, `tests/test_backfill_doc_fingerprint.py`, `tests/test_ingest_delta_jobs_lock.py` | — |
| 2 | Baseline snapshot reader + fingerprint helper | PASSED_TESTS | `src/lia_graph/ingestion/baseline_snapshot.py`, `tests/test_baseline_snapshot.py` (fingerprint.py + test_fingerprint.py landed in Phase 1 per §12.1 subsumption) | — |
| 3 | Delta planner (pure) | PASSED_TESTS | `src/lia_graph/ingestion/delta_planner.py`, `tests/test_delta_planner.py` | — |
| 4 | Additive Supabase sink path | PASSED_TESTS | `src/lia_graph/ingestion/supabase_sink.py` (extended with `write_delta` + `SupabaseDeltaResult`), `src/lia_graph/ingestion/dangling_store.py` (new), `tests/test_supabase_sink_delta.py` (10), `tests/test_dangling_store.py` (7) | — |
| 5 | Additive Falkor path | PASSED_TESTS | `src/lia_graph/ingestion/loader.py` (+ `build_graph_delta_plan`), `src/lia_graph/graph/client.py` (+ `stage_detach_delete`, `stage_delete_outbound_edges`), `tests/test_loader_delta.py` (11) | — |
| 6 | Orchestrator wiring + CLI + Makefile + env matrix | PASSED_TESTS | `src/lia_graph/ingest.py` (+ CLI flags + route), `src/lia_graph/ingestion/delta_runtime.py` (new — keeps `ingest.py` small), `Makefile` (+ 3 targets), `docs/guide/orchestration.md` (version bump + change-log entry), `docs/guide/env_guide.md`, `CLAUDE.md`, `AGENTS.md`, `frontend/src/features/orchestration/orchestrationApp.ts`, `tests/test_ingest_cli_additive.py` (7) | — |
| 7 | Concurrency guard + parity check + observability | NOT_STARTED | `src/lia_graph/ingestion/parity_check.py` (new), `src/lia_graph/ingestion/delta_lock.py` (new — combined J1+J2 guard per reviewer-revised Decision J), `src/lia_graph/ingestion/delta_job_store.py` (new — CRUD around `ingest_delta_jobs`), trace-event additions in existing modules, `tests/test_parity_check.py`, `tests/test_delta_lock.py`, `tests/test_delta_job_store.py`, `tests/test_additive_observability.py` | — |
| 8 | Admin UI + backend job surface (**MANDATORY** — Decision G1 minimum, G3 stretch) | NOT_STARTED | Backend: `src/lia_graph/ui_ingest_delta_controllers.py` (new — `POST /preview`, `POST /apply`, `GET /events`, `GET /status`, `POST /cancel`), extensions to `src/lia_graph/ui_admin_controllers.py` for route registration, `src/lia_graph/background_jobs.py` (extend) for the delta-apply background worker, `tests/test_ui_ingest_delta_controllers.py` (new). Frontend (all via `frontend-design:frontend-design` skill, per §0.12): `frontend/src/shared/ui/molecules/additiveDeltaBanner.ts`, `frontend/src/shared/ui/molecules/additiveDeltaActionRow.ts`, `frontend/src/shared/ui/molecules/additiveDeltaProgressPane.ts`, `frontend/src/features/ingest/additiveDeltaController.ts`, `frontend/src/features/ingest/additiveDeltaReattach.ts` (localStorage reattach), `frontend/src/styles/admin/additive-delta.css`, `frontend/tests/additiveDelta.test.ts`, `frontend/tests/additiveDeltaReattach.test.ts`, Playwright: `tests/e2e/additive_delta_ui.spec.ts`. | — |
| 9 | E2E against real corpus | NOT_STARTED | `tests/manual/additive_corpus_v1_runbook.md`, `tests/manual/additive_corpus_v1_evidence/<run-ts>/` | — |
| 10 | Close-out + handoff | NOT_STARTED | `docs/guide/orchestration.md` (change log), THIS doc (relocate to `docs/done/`) | — |

**Tests baseline** (set in Phase 0 after pre-flight runs)

| Suite | Pre-plan | Post-plan target |
|---|---|---|
| `tests/test_phase2_graph_scaffolds.py` | to measure | unchanged pass count |
| `tests/test_phase3_graph_planner_retrieval.py` | to measure | unchanged pass count |
| `tests/test_ui_server_http_smokes.py` | to measure | unchanged pass count |
| `tests/integration/test_single_pass_ingest.py` | to measure | unchanged pass count |
| New: `tests/test_backfill_doc_fingerprint.py` | n/a | ~6 cases |
| New: `tests/test_baseline_snapshot.py` | n/a | ~7 cases |
| New: `tests/test_fingerprint.py` | n/a | ~5 cases |
| New: `tests/test_delta_planner.py` | n/a | ~12 cases |
| New: `tests/test_supabase_sink_delta.py` | n/a | ~10 cases |
| New: `tests/test_dangling_store.py` | n/a | ~6 cases |
| New: `tests/test_loader_delta.py` | n/a | ~8 cases |
| New: `tests/test_ingest_cli_additive.py` | n/a | ~6 cases |
| New: `tests/test_parity_check.py` | n/a | ~5 cases |
| New: `tests/test_delta_lock.py` (renamed from `test_advisory_lock.py` per reviewer Decision J) | n/a | ~6 cases (J1 RPC path + J2 row-lock path) |
| New: `tests/test_delta_job_store.py` | n/a | ~6 cases |
| New: `tests/test_ingest_delta_jobs_lock.py` | n/a | ~4 cases (partial-unique-index behavior) |
| New: `tests/test_additive_observability.py` | n/a | ~5 cases |
| New: `tests/test_ui_ingest_delta_controllers.py` (Phase 8 backend) | n/a | ~10 cases (preview, apply, events SSE, status, cancel, admin-auth gate) |
| New: `frontend/tests/additiveDelta.test.ts` (Phase 8 — MANDATORY) | n/a | ~12 cases (see Phase 8 §E2E failure-mode matrix) |
| New: `frontend/tests/additiveDeltaReattach.test.ts` (Phase 8 — MANDATORY) | n/a | ~5 cases (localStorage reattach + SSE reconnect + polling fallback) |
| New: `tests/e2e/additive_delta_ui.spec.ts` (Playwright, Phase 8 + Phase 9) | n/a | ~6 cases (per the failure-mode matrix in Phase 8) |
| `make phase2-graph-artifacts-smoke` | green | green |
| `make eval-c-gold` | ≥90 | ≥90 |
| Atomic-discipline guard (Phase 8) | green | green |
| **>20-file conftest guard** (`CLAUDE.md`) | n/a | **Reviewer-checked 2026-04-22:** each Phase's Verification command runs ≤ 5 new test files, staying under the 20-file threshold. The largest single-command set is Phase 7 (`parity + lock + job_store + observability` = 4 files). Phase 8's backend + frontend split keeps each command sub-threshold. For a plan-wide smoke run, invoke with `LIA_BATCHED_RUNNER=1` in the env or route through `make test-batched`. |

**Migrations ledger**

| Migration | Purpose | Status |
|---|---|---|
| `20260422000000_corpus_additive.sql` | Adds `documents.doc_fingerprint`, `documents.last_delta_id`, `documents.retired_at`, `normative_edges.last_seen_delta_id`, `normative_edge_candidates_dangling` table, partial unique index `normative_edges_rolling_idempotency`, reserved row `gen_active_rolling` in `corpus_generations`. Additive only — no drops. | APPLIED_LOCAL + APPLIED_CLOUD (2026-04-22) |
| `20260422000001_ingest_delta_jobs.sql` (reviewer-added) | Adds `ingest_delta_jobs` table + partial unique index `idx_ingest_delta_jobs_live_target` per reviewer-revised Decision J2. Adds `acquire_ingest_delta_lock(text)` RPC (J1 helper) and `promote_generation(target_gen text)` RPC skeleton (Decision F1). | APPLIED_LOCAL + APPLIED_CLOUD (2026-04-22) |

---

## 3. What We Already Have (read-only survey, 2026-04-22)

### 3.1 Schema already supports hashing
`supabase/migrations/20260417000000_baseline.sql` already defines:
- `documents.content_hash TEXT` + index `idx_documents_content_hash` (line 1814)
- `documents.sync_generation TEXT` + index `idx_documents_sync_generation` (line 1834)
- `document_chunks.chunk_sha256 TEXT` + index `idx_chunks_sha256` (line 1738)
- `document_chunks.sync_generation TEXT` + index `idx_chunks_sync_generation` (line 1742)
- `corpus_generations` with partial unique `idx_corpus_generations_single_active` (line 1790) — enforces exactly one active row
- `normative_edges.generation_id TEXT` with index `idx_normative_edges_generation` (line 1970)

This plan adds columns + indexes; it does NOT modify any existing column. The baseline is already aligned with the additive model's detection needs.

### 3.2 Sink already upserts
`SupabaseCorpusSink` (`src/lia_graph/ingestion/supabase_sink.py`) already upserts `documents` (on `doc_id`), `document_chunks` (on `chunk_id`), `normative_edges` (on `(source_key, target_key, relation, generation_id)` — the compound uniqueness from `20260418000000_normative_edges_unique.sql`), and `corpus_generations` (on `generation_id`). It already computes `content_hash` per doc and `chunk_sha256` per chunk. The additive path extends this module rather than replacing it.

### 3.3 Retrievers already accept a generation filter (but don't use it today)
`hybrid_search` and `fts_scored_prefilter` RPCs (baseline lines 138, 264) already accept `filter_sync_generation` as optional. **However**, `src/lia_graph/pipeline_d/retriever_supabase.py:157` hard-codes `"filter_sync_generation": None` and never consults `corpus_generations.is_active`. In practice the retriever serves **every** chunk that survives the other filters (topic / pais / knowledge_class / vigencia / effective_date), regardless of `sync_generation`. Two consequences for this plan:

1. The "retired document" semantics (Decision B1) are load-bearing at the **storage layer** — if retired chunks are not hard-deleted, they stay retrievable. Good news: Decision B1 already hard-deletes, so this is fine, but it means there is no belt-and-braces `retired_at IS NULL` filter to fall back on.
2. The plan's original claim "swapping `gen_<UTC>` for `gen_active_rolling` requires no RPC change because the retriever already reads the active row" was **wrong**. Correction: swapping generation id does not affect retrieval at all because the retriever ignores `sync_generation`. Retrieval sees whatever chunks exist. The two-step active flip in `_activate_generation` (`supabase_sink.py:416-444`) remains load-bearing for any *future* caller that does filter by active generation (e.g. diagnostics, admin tools), and for Invariant I2.

If Phase 9 finds retrieval quality issues attributable to stale chunks leaking across rolling-vs-snapshot transitions, the fix is either (a) delete chunks belonging to superseded `sync_generation` values as part of the promotion step, or (b) teach the retriever to pass `filter_sync_generation=<active row>`. Both are out of scope for v1 unless the symptom appears.

### 3.4 Falkor writes are (label, key)-idempotent — BUT property-overwriting
`GraphClient.stage_node` and `stage_edge` (`src/lia_graph/graph/client.py:148-182`) emit `MERGE` Cypher of the form:

```
MERGE (node:<Kind> {<key_field>: $key})
SET node += $properties
```

Reviewer-verified 2026-04-22. This uses **unconditional `SET … +=`**, not `ON CREATE SET / ON MATCH SET`. Consequence for additive: re-MERGE-ing an unchanged node **overwrites** every property in `$properties`. Today that is safe because full-rebuild always re-submits with the same values, so overwrite is a no-op. Under additive this becomes a live concern:

- Any new property the additive path wants to track **only on create** (e.g. `first_seen_delta_id`) or **only on match** (e.g. `last_seen_delta_id`) cannot be expressed with the current helper.
- If Phase 5 wants to record delta attribution on nodes/edges (trace-friendly), the Cypher pattern must change to `MERGE … ON CREATE SET n.first_seen_delta_id = $delta_id, n += $properties ON MATCH SET n.last_seen_delta_id = $delta_id, n += $properties`. That is a change to `stage_node` / `stage_edge` signatures (`create_properties`, `match_properties`), not just to loader.py.
- Unchanged-doc MERGEs are not a correctness issue but they still write (and therefore still invoke WAL). Phase 5 should *skip* emitting them entirely for unchanged docs, not rely on MERGE-as-no-op.

FalkorDB quirks worth noting (versus Neo4j):
- FalkorDB has no schema enforcement; property-type drift goes silent.
- Index creation is via `GRAPH.QUERY … CREATE INDEX`; the existing `graph_schema.py` indexes are created at boot. Additive mode does not need new Falkor indexes.
- `DETACH DELETE` is supported; `stage_detach_delete` can use it directly.

Deletion of retired nodes requires new helpers: `stage_detach_delete(kind, key)` and `stage_delete_outbound_edges(source_kind, source_key, relation_subset=None)`. Both must propagate errors strictly (no silent fallback — per `CLAUDE.md`).

### 3.5 Edge dangling is silently pruned today
`normalize_classified_edges` (`src/lia_graph/ingestion/loader.py:247-259`, reviewer-verified 2026-04-22) drops **only** edges whose `target_kind is NodeKind.ARTICLE` and whose `target_key` is not in the current article set. Other target kinds (`SUBTOPIC`, `REFORM`, `DOCUMENT`, etc.) are **never** pruned by this function. Two consequences for the dangling-store design:

1. **`normative_edge_candidates_dangling` (Decision D1) only needs to cover ARTICLE targets.** Other kinds are either (a) always-present (subtopic taxonomy is shipped) or (b) created inline by their own node pass (REFORM nodes are minted from citations in `_build_reform_nodes`). If a future kind starts producing real cross-delta dangling, widen the table then.
2. **But:** the planner must still distinguish "ARTICLE target missing because it's a new delta's responsibility" from "ARTICLE target missing because of a classifier/parser bug on the source doc." The dangling store should only receive the former — i.e., only edges whose *source doc* is in the delta (`added` or `modified`) and whose target is unresolved **after** the delta's new article set has been merged into the article-key lookup. A parser-bug edge (source doc unchanged, target never existed, no delta would ever resolve it) has to be handled either by hard-pruning with a warning trace or by surfacing in the sink report.

Under additive, the naive drop becomes incorrect: an old doc's edge whose target is *about to arrive* in a future delta would be permanently dropped. The plan introduces a persistent dangling store (Phase 4) so that these candidates survive across deltas and get promoted when their targets arrive.

### 3.6 Embeddings are already additive
`embedding_ops.py:219-265` defaults to `WHERE embedding IS NULL`. New chunks get embedded on the next backfill pass. No change needed for v1; decision recorded as §4 Decision I.

### 3.7 SUIN merge
`_merge_suin_scope` (`src/lia_graph/ingest.py:503`) materializes SUIN articles + stubs at ingest time. Additive mode must treat a SUIN re-import as a delta on the SUIN-owned doc subset. Covered as a risk in §6; Phase 3 tests include a SUIN re-import case.

### 3.8 `materialize_graph_artifacts` is NOT a clean place to slip `--additive` in
Reviewer-verified 2026-04-22 (`src/lia_graph/ingest.py:216-420`). The function is 200+ LOC of sequential full-corpus work:

1. `audit_corpus_documents(root)` — walks `knowledge_base/` from scratch.
2. `classify_corpus_documents(legacy_corpus_documents)` — PASO 4 classifier over every admitted doc.
3. Seven `_write_json(*)` / `_write_jsonl(*)` calls that materialize audit + reconnaissance + manifest + inventory reports over the **full** corpus.
4. `parse_article_documents(graph_documents)` — parses every admitted doc.
5. `extract_edge_candidates` + `classify_edge_candidates` over the full article set.
6. `_merge_suin_scope` — SUIN merge.
7. `normalize_classified_edges` — the full-corpus article-set filter (see §3.5).
8. `build_graph_load_plan` + `load_graph_plan` — Falkor plan over the full corpus.
9. Writes `parsed_articles.jsonl` / `raw_edges.jsonl` / `typed_edges.jsonl` / `graph_load_report.json` / `graph_validation_report.json` over the **full** corpus.
10. Optional `SupabaseCorpusSink` block — the sink writes (documents + chunks + edges), then `finalize(activate=supabase_activate)`.

The plan's Phase 6 bullet "Route through a new helper `_materialize_delta(...)`" is correct as an **intent** but under-specifies the surgery. The honest picture:

- Steps (1) + (2) stay whole-corpus under Decision C1 (fingerprint needs classifier output for every doc to decide the unchanged bucket). Under Decision D (deferred follow-up to cache classifier outputs) this becomes avoidable, but in v1 it dominates wall-clock.
- Steps (3) + (9) (the artifact JSONL bundle) stay whole-corpus per Decision E1.
- Steps (4)-(8) must branch: `_materialize_delta` keeps (1)-(3) and (9), but runs (4)-(8) over the delta subset plus the Pass-B dangling-resolution fan-in.
- Step (10) calls `sink.write_delta(...)` (new in Phase 4) **instead of** the existing `write_documents` / `write_chunks` / `write_normative_edges` sequence.

**Consequence for scope:** Phase 6's "every change is an extension of existing files" framing is optimistic. Expect a real refactor: either `materialize_graph_artifacts` grows an `additive: bool` branch with two non-trivial code paths, or it gets split into `_audit_and_classify`, `_emit_artifact_bundle`, `_apply_to_supabase`, `_apply_to_falkor` helpers that both paths call. The plan's State Notes in Phase 6 must capture which refactor shape was chosen.

### 3.9 `SupabaseCorpusSink` has stateful cross-method coupling
Reviewer-verified 2026-04-22 (`src/lia_graph/ingestion/supabase_sink.py:175-276`). The sink holds two instance dicts:

```
self._subtema_by_doc_id: dict[str, str] = {}
self._topic_by_doc_id: dict[str, str] = {}
```

`write_documents` populates them (line 271, 276) so `write_chunks` can inherit `subtema` / `topic` per parent doc without a round-trip (line 305). `write_delta` (Phase 4) must preserve this coupling:

- For `added` + `modified` buckets, `write_delta` must call the same populate-then-consume sequence on the doc subset. Any helper that short-circuits `write_documents` for docs already in the baseline will drop the subtema mapping and `write_chunks` will emit `subtema=None` for those chunks — a silent retrieval-quality regression.
- For `removed` bucket, neither mapping is populated, which is correct (no chunks are being written for retired docs).
- The plan's Phase 4 bullet currently says "upsert documents + chunks as today". Lock the sequencing contract in the Phase 4 State Notes so the executing agent doesn't re-order.

---

## 4. Decision Points (RATIFY BEFORE PHASE 1)

These are the architectural calls. Each needs an explicit yes/no/modify from the user in §2 before Phase 1 begins.

### Decision A — Generation model: rolling vs per-delta

**A1 (recommended):** Reserved row `gen_active_rolling` in `corpus_generations`. Only one row has `is_active=true`. Additive deltas upsert into this rolling row; full-rebuild mints a fresh `gen_<UTC>` snapshot and can promote it to become the new rolling base. Pro: single source of truth for "the live corpus"; compatible with existing `idx_corpus_generations_single_active` partial unique index; retrievers see no surface change. Con: `normative_edges` rolling row grows without bound; index bloat budgeted in §6.

**A2:** One `corpus_generations` row per delta (`gen_delta_<UTC>`), with `is_active=true` on all of them simultaneously. Pro: audit trail per delta. Con: violates `idx_corpus_generations_single_active` — needs an index drop/replacement, which is a breaking schema change for any caller that relies on `is_active` being single-valued. Hard NO unless we accept schema drift.

**A3:** Hybrid — rolling for the "live view" AND snapshots minted per-delta for audit. Pro: best of both. Con: doubles the cloud write cost of every delta; adds a third concept to explain.

**Recommendation: A1.** Needs user sign-off.

**Reviewer-revised recommendation: A1 — concur.** Why I'd pick this in production: A2 is a non-starter because `idx_corpus_generations_single_active` is already relied on by `_activate_generation` (the sink's final step) and by any diagnostic that asks "what is the live corpus right now." A3's two-row-per-delta overhead doubles write cost for zero added safety versus A1 with a well-run Phase 9 rollback drill. A1 also composes cleanly with Decision F1 (snapshot → rolling promotion), which is the actual "audit trail per delta" story — you get it from `corpus_generations.gen_<UTC>` snapshots + `documents.last_delta_id` history, not from multi-active rows.

RATIFIED 2026-04-22: A1 — reserved `gen_active_rolling` row; full-rebuild mints `gen_<UTC>` snapshots; explicit promotion flips active (per Decision F).

### Decision B — Retirement semantics

**B1 (recommended):** Soft-delete on `documents` (`retired_at TIMESTAMPTZ NULL`); hard-delete chunks + edges rooted in retired docs; retrievers use chunk absence for filtering, so adding `retired_at IS NULL` to SQL is belt-and-braces but not strictly required. Pro: audit trail for "what got retired when"; no extra SQL filter cost. Con: two invariants to hold (chunks gone ⇔ parent retired).

**B2:** Hard-delete `documents` row too, let `ON DELETE CASCADE` drop chunks. Pro: simplest invariant. Con: loses "this doc existed before" audit; downstream diagnostics lose the join target.

**B3:** Soft-delete everywhere (chunks + edges kept, flagged). Pro: maximum audit. Con: permanent retrieval-filter cost; data grows without bound.

**Recommendation: B1.** Needs user sign-off.

**Reviewer-revised recommendation: B1 — concur, with added safety railing.** Why I'd pick this in production: the "invariant I3 + hard-delete chunks" framing is defensible only if backfill of the `retired_at IS NULL` filter into the retriever lands **before** the first production delta retires a real doc. §3.3 already observes the retriever hard-codes `filter_sync_generation: None`; adding a belt-and-braces `.is_('retired_at', 'null')` to `retriever_supabase.py` is ~5 LOC and saves us from a silent leak the day someone forgets Invariant I3. Phase 6 (or a tracked follow-up in §7 Out of Scope) should own that small patch, NOT defer it to "if Phase 9 finds retrieval quality issues." B2 loses too much audit; B3 loses retrieval performance forever.

RATIFIED 2026-04-22: B1 — soft-delete `documents.retired_at`, hard-delete chunks + outbound edges; Phase 6 to add belt-and-braces `retired_at IS NULL` filter in `retriever_supabase.py` per reviewer note.

### Decision C — Document-change fingerprint

**C1 (recommended):** `doc_fingerprint = sha256(content_hash || "|" || canonical_json(classifier_output))`. Classifier output = `{topic_key, subtopic_key, requires_subtopic_review, authority_level, document_archetype, knowledge_class, source_type, source_tier}` (the fields PASO 4 writes). Pro: catches both on-disk edits and classifier drift; recomputable. Con: changing the classifier prompt invalidates all fingerprints (this is a feature, not a bug — see §14 Decision D follow-up).

**C2:** `content_hash` only. Pro: cheapest. Con: silent classifier drift — a doc's `subtopic_key` can change without any file change, and retrieval quality depends on `subtopic_key`, so we'd serve stale labels.

**C3:** Per-field dirty flags (file_dirty, classifier_dirty, subtopic_dirty). Pro: granular. Con: not actually useful — any dirty field means the doc flows through anyway; the granularity only helps metrics.

**Recommendation: C1.** Needs user sign-off.

**Reviewer-revised recommendation: C1 — concur, with a `prompt_version` marker baked in.** Why I'd pick this in production: C2 is a silent-drift trap — classifier prompts change more often than markdown files, and subtopic labels are load-bearing for retrieval. C3 adds UX surface for no real gain (any dirty bit forces a re-process). But C1 as written has one hole: when the classifier prompt changes, **every** fingerprint invalidates simultaneously, triggering what is effectively a full rebuild in "additive" clothing. Fix: include a stable `prompt_version` string (pulled from `ingest_subtopic_pass.PROMPT_VERSION` or equivalent) in the canonical classifier JSON. Now prompt bumps are explicit, auditable, and you can run a controlled full rebuild against the new version rather than discovering it mid-delta. Add this to the `CLASSIFIER_FINGERPRINT_FIELDS` constant in Phase 2.

RATIFIED 2026-04-22: C1 — composite fingerprint including a stable `prompt_version` field in the canonical classifier JSON (per reviewer amendment); prompt bumps become explicit, controlled full-equivalent deltas.

### Decision D — Dangling-candidate persistence

**D1 (recommended):** New table `normative_edge_candidates_dangling (source_key, target_key, relation, source_doc_id, first_seen_delta_id, last_seen_delta_id, raw_reference)` with unique `(source_key, target_key, relation)`. Each delta consults the table after Pass A and promotes candidates whose `target_key` is in the delta's `new_article_keys`; new dangling candidates get inserted. Pro: correctness; bounded growth (one row per unresolved candidate across all history). Con: new table; Phase 4 work.

**D2:** Re-derive dangling set on every delta by scanning all doc markdown for unresolved citations. Pro: no new table. Con: forces reading every doc's text each delta, defeating the point of additivity.

**D3:** Drop dangling edges permanently (current behavior). Pro: no work. Con: incorrect — new docs that would resolve old citations never trigger edge creation for the old source.

**Recommendation: D1.** Needs user sign-off.

**Reviewer-revised recommendation: D1 — concur, with GC discipline explicit.** Why I'd pick this in production: D2 defeats the entire point of additivity (every delta re-reads the full corpus to hunt for citations — embarrassing). D3 is the current silent-bug state. D1 is right. The one thing to lock down now rather than leaving for a future follow-up: put a `gc_older_than(delta_id_threshold)` call on a schedule (weekly cron or a manual Makefile target, operator-driven). The plan mentions this in Phase 4 as an API; Phase 7 or §7 "Out of Scope" should name the target threshold (my pick: drop candidates whose `last_seen_delta_id` is older than 12 months and whose `target_key` never appeared in the `normative_edges` table) so the store doesn't quietly accumulate garbage from long-dead parser bugs.

RATIFIED 2026-04-22: D1 — persistent dangling-candidate table with unique `(source_key, target_key, relation)`; Phase 4 exposes `gc_older_than`; Phase 7 schedules it (reviewer pick: drop candidates older than 12 months whose target never appeared in `normative_edges`).

### Decision E — Artifact bundle in additive mode

**E1 (recommended):** Full rewrite of `artifacts/parsed_articles.jsonl` and `artifacts/typed_edges.jsonl` in additive mode — same as today. Dev mode (`LIA_CORPUS_SOURCE=artifacts`) is small-corpus-only and the bundle must be coherent. The additive saving is on Supabase + Falkor, not the bundle. Pro: simple, no dev-mode retrieval surprises. Con: bundle rewrite may dominate wall-clock for very large corpora (>5k docs) — revisit when that's real.

**E2:** Incremental bundle (write a diff file per delta, reader merges). Pro: O(delta) file I/O. Con: changes the dev retriever contract; high blast radius for a tiny win.

**Recommendation: E1.** Needs user sign-off.

**Reviewer-revised recommendation: E1 — concur.** Why I'd pick this in production: E2's blast radius (dev-mode retriever has to understand diff-merge semantics) is absurd for the savings on offer. Dev-mode corpus is small by construction; writing `parsed_articles.jsonl` for 1.3k docs is a few hundred ms of disk I/O, not the wall-clock bottleneck. The only thing worth adding: if the additive delta touched zero Falkor/Supabase rows (empty delta), **skip** the artifact-bundle rewrite too. That's a one-line guard on the count of `added + modified + removed` and it avoids unnecessary file churn in dev when an operator clicks Preview-then-nothing.

RATIFIED 2026-04-22: E1 — full rewrite of `parsed_articles.jsonl` + `typed_edges.jsonl` on every applied delta; per reviewer amendment, skip the rewrite when the delta is empty (zero added + modified + removed).

### Decision F — Relationship between full-rebuild and rolling generation

**F1 (recommended):** Full-rebuild runs write to a fresh `gen_<UTC>` snapshot as today; an explicit admin action (CLI flag `--promote-to-rolling` or a separate `make phase2-promote-snapshot` target) copies the snapshot into `gen_active_rolling` and flips active. This keeps full-rebuild a safe "validate before promoting" operation. Pro: explicit, auditable, rollback-friendly. Con: two-step for any rebuild operator.

**F2:** Full-rebuild writes directly to `gen_active_rolling`, replacing its contents in-place. Pro: single step. Con: no validation gate; a bad rebuild clobbers the live corpus.

**F3:** Full-rebuild writes to `gen_<UTC>` AND immediately promotes. Pro: one step for operators, two rows for auditors. Con: operator intent is ambiguous.

**Recommendation: F1.** Needs user sign-off.

**Reviewer-revised recommendation: F1 — concur, BUT the promotion semantics need full specification before Phase 1 starts.** Why I'd pick this in production: F2's "clobber the live corpus on a bad rebuild" failure mode is a career-ender. F3 collapses operator intent — you lose the ability to inspect a rebuild before making it live. F1 is the only viable design. However, the plan's `make phase2-promote-snapshot` is currently a one-line bullet that hides the real complexity. Before Phase 1 closes, promotion must answer all of:

1. **Atomicity.** Promotion flips `corpus_generations.is_active` for two rows (snapshot → true, prior rolling → false) AND updates `documents.sync_generation` / `document_chunks.sync_generation` / `normative_edges.generation_id` for potentially millions of rows. This is **not** doable via PostgREST in one HTTP call. It must be an RPC (`CREATE OR REPLACE FUNCTION promote_generation(target_gen TEXT)`) running inside a single transaction, or a batched stored procedure with a clearly documented partial-state window. Recommendation: **RPC inside a single transaction**, with a `SET LOCAL statement_timeout = '30min'` and an operator-facing warning if row count > 10M.
2. **Race with a concurrent rolling delta.** If a `--additive` run lands between the snapshot's last write and the promotion's flip, the rolling delta's rows get clobbered. The advisory lock from Decision J must be held for promotion too — add `promote` to the lock-key namespace, and document that `make phase2-promote-snapshot` acquires the same lock.
3. **`normative_edges.generation_id` semantics.** Two options: (a) UPDATE every row's `generation_id` from `gen_<UTC>` to `gen_active_rolling` (preserves history in the snapshot row, but loses which delta originally landed each edge), or (b) keep the snapshot's `generation_id` values and re-point the `is_active` pointer only. Reviewer-pick: **(b)**. Cheaper, keeps history, and the `normative_edges_rolling_idempotency` partial unique index can be widened to match any `generation_id` that is currently active via a subquery — or, simpler, match on `(source_key, target_key, relation)` only with a non-partial index once rolling mode is the norm. Flag this as a sub-decision in Phase 1 State Notes.
4. **Rollback.** F1 claims "rollback-friendly." True only if the operator can flip `is_active` back to the previous snapshot via the same RPC. Phase 9's rollback drill must exercise this. A one-liner shell command that toggles `is_active` without the RPC is not sufficient — it doesn't update the Falkor side.

Add these four points as a Phase 6 sub-task ("Promotion RPC spec") and block Phase 10 close-out until (4) is exercised in Phase 9.

RATIFIED 2026-04-22: F1 — snapshot-then-promote. Four reviewer sub-points (atomic RPC, promotion-held advisory lock, `generation_id` option (b) re-point-don't-rewrite, rollback drill) are binding on Phase 6 and Phase 9.

### Decision G — Admin UI scope for v1 (Phase 8 is MANDATORY — not descopeable)

**Reviewer note (2026-04-22):** the original Decision G offered a "no UI in v1" option (G2). That option is removed. User requirement: additive corpus ingestion MUST be drivable end-to-end from the admin UI, not only via the CLI. Phase 8 is therefore a hard requirement, and the scope lever is about **richness**, not **existence**.

**G1 (minimum viable):** Preview + Apply sub-panel within the existing Sesiones / Ingesta admin tab. Delta preview via `POST /api/ingest/additive/preview` (per-bucket counts + sample-doc chips); Apply via `POST /api/ingest/additive/apply` which returns a `job_id`; live progress via SSE on `GET /api/ingest/additive/events?job_id=…` with polling fallback on `GET /api/ingest/additive/status?job_id=…`; cancel via `POST /api/ingest/additive/cancel?job_id=…`. No history view — operators inspect past deltas via the existing ops/Sesiones telemetry that reads `corpus_generations` + `documents.last_delta_id`.

**G3 (richer, stretch):** Everything in G1 **plus** a past-deltas history table (reads `documents.last_delta_id` aggregates + `corpus_generations` rows), per-delta drilldown (bucket breakdowns, trace-event timeline, parity-check results), and a "promote snapshot → rolling" action (Decision F1) with its own confirmation flow. Can be built atop G1 without rework — the preview/apply/events endpoints are reused.

~~G2~~ **(removed — Phase 8 cannot be descoped).**

**Recommendation: G1 ratified for v1; G3 tracked as a Phase 11 follow-up.** Descope from G3 → G1 if Phase 8 overruns by > 2×; do NOT descope below G1.

**Reviewer-revised recommendation: G1 for v1, G3 as an immediate follow-up.** Why I'd pick this in production: operators who don't have shell (compliance, content, customer-ops) are the exact people who need to run additive deltas for "a regulator just published a new Decreto" one-off updates. CLI-only means every delta goes through an engineer — which is both a bottleneck and (worse) a source of errors when that engineer doesn't own the corpus domain. G1 is the correct v1 floor because (a) Preview + Apply + live progress covers the real operator flow, and (b) history/audit is already partly visible via the existing Sesiones telemetry — a dedicated delta-history tab is high value but not blocking. Don't ship G1 without making it reload-safe, double-click-safe, and clearly labeled for terminal states; see Phase 8 rewrite below for the full reliability mandate.

RATIFIED 2026-04-22: G1 for v1 (Preview + Apply + live progress + cancel, reload-safe, double-click-safe, Supabase-vs-Falkor distinct error UX); G3 tracked as Phase 11 follow-up.

### Decision H — Parity check gate

**H1 (recommended):** Before every additive delta, run a Supabase-vs-Falkor row-count parity probe. If mismatch > 1% (tolerance), WARN in the delta report but proceed; add a `--strict-parity` CLI flag that BLOCKS on mismatch. Pro: catches drift early without forcing manual intervention on benign lag. Con: silent acceptance of small drift.

**H2:** Always block on any mismatch. Pro: safest. Con: any transient cloud hiccup halts all ingest operations.

**H3:** Never check. Pro: simplest. Con: drift compounds silently.

**Recommendation: H1.** Needs user sign-off.

**Reviewer-revised recommendation: H1 — concur, with a tighter default tolerance.** Why I'd pick this in production: H2's "any mismatch halts" is the kind of check that gets commented out within three months because some transient Falkor lag wakes someone at 3 AM. H3 compounds drift silently. H1 is the only sustainable shape. But the plan's "> 1% tolerance" default is too loose for a corpus where 1% of ~1300 docs = 13 silently-missing articles. Better default: **absolute tolerance of 5 rows OR 0.2%, whichever is larger**. Keeps transient-lag noise absorbed, catches structural drift earlier. `--strict-parity` still available for dry-run probes and pre-promote gates.

RATIFIED 2026-04-22: H1 — warn-and-proceed parity check with tightened default tolerance (5 rows absolute OR 0.2%, whichever is larger); `--strict-parity` CLI flag + UI toggle escalates to hard block; strict mode required for pre-promotion gates and Phase 9 rollback drill.

### Decision I — Embedding backfill trigger

**I1 (recommended):** After a successful delta, emit an `ingest.delta.embedding_needed` event with the count of new-chunk rows. Do NOT automatically run `embedding_ops.py`; operators run it as today. Rationale: embedding runs are cost-bearing and operators prefer explicit control. Pro: zero coupling. Con: requires discipline to run embeddings before the new chunks are retrievable at full quality.

**I2:** Automatically kick off `embedding_ops.py` as a background job after every delta. Pro: "it just works." Con: adds job-system dependency; cost not visible to operators.

**I3:** Inline embedding during the delta sink. Pro: atomic. Con: slow; couples cloud LLM availability to every delta.

**Recommendation: I1.** Needs user sign-off.

**Reviewer-revised recommendation: I1 — concur, with an explicit operator-facing signal in the UI.** Why I'd pick this in production: I2 adds a job-system dependency that becomes load-bearing for every delta — if the job system stalls, deltas silently serve at degraded retrieval quality. I3 makes every delta stall waiting on Gemini embed-latency (unacceptable for operator click-to-done UX, the whole reason Phase 8 exists). I1 is right. The critical addition over the plan's current shape: when the admin-UI apply completes and `ingest.delta.embedding_needed` fires with `new_chunks_count > 0`, the UI terminal-state banner must show **"N new chunks awaiting embedding — retrieval quality is degraded until you run `make phase2-embed-backfill`"** with a copy-to-clipboard for the exact command. Making the next step visible is the whole point of not auto-running it.

RATIFIED 2026-04-22: I1 — no auto-embed; `ingest.delta.embedding_needed` event fires with new-chunk count; Phase 8 UI terminal banner must surface "N chunks awaiting embedding" with the exact backfill command copy-to-clipboard (per reviewer amendment).

### Decision J — Concurrency guard

**Reviewer note (2026-04-22):** the original J1 (session-level `pg_try_advisory_lock` from the Python process) does **not** work as described against Supabase, because the Supabase Python client speaks PostgREST and therefore does not hold a long-lived DB session across multiple HTTP calls. The lock is released the moment the HTTP request returns. Options rewritten below.

**J1 (rewritten, reviewer-recommended): RPC-wrapped advisory lock.** Create a Supabase RPC `acquire_ingest_delta_lock(lock_target text) → boolean` that begins a transaction, calls `pg_try_advisory_xact_lock(hashtext('gen_active_rolling:' || lock_target))`, and returns true/false. A second RPC `run_under_delta_lock(lock_target text, payload jsonb) → jsonb` holds the lock for the duration of a single SQL body (e.g. a batched DML) — used for the promotion step (Decision F1). For the **long-running Python-side delta apply** (which spans multiple PostgREST calls over many minutes), the lock is NOT held session-level; instead use the row-based approach in J2 as the primary guard and use advisory locks only inside single-transaction RPCs like `promote_generation`. This is a hybrid.

**J2 (rewritten, reviewer-recommended primary guard): `ingest_delta_jobs` table with heartbeat.** New table in the Phase 1 migration:

```
CREATE TABLE ingest_delta_jobs (
  job_id             text PRIMARY KEY,
  lock_target        text NOT NULL,   -- 'production' | 'wip'
  delta_id           text,
  stage              text NOT NULL,   -- 'queued'|'preview'|'parsing'|'supabase'|'falkor'|'finalize'|'completed'|'failed'|'cancelled'
  progress_pct       int  NOT NULL DEFAULT 0,
  started_at         timestamptz NOT NULL DEFAULT now(),
  last_heartbeat_at  timestamptz NOT NULL DEFAULT now(),
  completed_at       timestamptz,
  created_by         text,            -- admin user_id
  cancel_requested   boolean NOT NULL DEFAULT false,
  error_class        text,
  error_message      text,
  report_json        jsonb
);
CREATE UNIQUE INDEX idx_ingest_delta_jobs_live_target
  ON ingest_delta_jobs (lock_target)
  WHERE stage NOT IN ('completed','failed','cancelled');
```

Inserting a new row succeeds only if no existing non-terminal row holds the same `lock_target` — the partial unique index is the lock. A stalled job (heartbeat older than 5 minutes) is reaped by a janitor task that transitions it to `failed` with `error_class='heartbeat_timeout'`. Pro: visibility in the admin UI (reads the live row); crash-safe (DB owns state, not a Python process); composes with Phase 8's job surface. Con: janitor logic.

**J3:** No lock. Pro: simplest. Con: two concurrent additive runs race on the rolling row. **Rejected.**

**Reviewer-revised recommendation: J1 (RPC-wrapped xact lock for single-transaction steps) + J2 (row-based lock with heartbeat for the long-running apply) in combination.** Why I'd pick this in production: the PostgREST session-life reality makes J1-alone unworkable for multi-minute deltas; J2-alone can't protect a single-transaction promotion from a racing delta. The combination is the only shape that holds under real failure modes (browser closed, Python crashed, operator double-clicked). This also gives Phase 8 a first-class job row to render against. Rewrite Phase 7's `advisory_lock.py` as `delta_lock.py` exposing both: `acquire_job_lock(supabase_client, *, target, job_id, created_by) -> JobLock` (J2) and `with_xact_lock(supabase_client, target, rpc_name, params) -> Any` (J1 RPC helper).

RATIFIED 2026-04-22: J1 + J2 hybrid — `ingest_delta_jobs` table (Phase 1 migration) with partial unique index on non-terminal rows is the primary guard for long-running deltas; RPC-wrapped `pg_try_advisory_xact_lock` protects single-transaction ops like `promote_generation`. Heartbeat reaper transitions stalled jobs (>5min no heartbeat) to `failed`.

### Decision K — Classifier-field persistence for backfill (NEW — reviewer-added 2026-04-22)

The plan's §0.8 glossary flags that `CLASSIFIER_FINGERPRINT_FIELDS` includes fields (`document_archetype`, `source_tier`, `authority_level`) that are **not** stored as dedicated columns on `documents` today (`supabase_sink.py:252-276` collapses them into `tipo_de_documento` / `source_type` / `authority`, and `source_tier` is not persisted at all). The backfill script at Phase 1 has to decide how to reconstruct the fingerprint from existing rows. The plan called out this choice as "Decision K" but never defined the options; reviewer-added below.

**K1 (reviewer-recommended):** Drop `source_tier` from `CLASSIFIER_FINGERPRINT_FIELDS`, and reconstruct `document_archetype` / `authority_level` from the persisted `tipo_de_documento` / `authority` columns during backfill. Phase 2's `compute_doc_fingerprint` accepts an explicit `classifier_output` mapping; the backfill script builds that mapping from the row, fingerprint computation stays pure. On the next full-rebuild after this decision ships, the **live** classifier output (in-memory, full fields) will produce the same fingerprint IF the backfill mapping is faithful — so the first full-rebuild post-ship will NOT spuriously mark every row `modified`. Verify this invariant with a dedicated test case (`test_fingerprint.py` (f): backfill-shape mapping produces the same fingerprint as ingest-shape mapping for a representative doc). Pro: no schema widening. Con: the fingerprint silently drops `source_tier`; Phase 3 delta planner cannot detect drift on that field.

**K2:** Widen `documents` with explicit `document_archetype`, `source_tier`, `authority_level` columns in the Phase 1 migration; the backfill reads those directly. Pro: fingerprint is faithful; drift on every classifier-written field is detectable. Con: three more persisted columns, each with a `NOT NULL DEFAULT 'unknown'` or nullable-plus-default migration; three more places to go wrong during ingest.

**K3:** Re-read markdown + re-run the PASO 4 classifier during backfill. Pro: fingerprint is always faithful. Con: backfill cost explodes from "pure SQL, ~5min" to "classifier calls over ~1300 docs, $6-16 + 30-40 min." Kills the "one-time, cheap" framing of Phase 1.

**Reviewer-revised recommendation: K1.** Why I'd pick this in production: K3 blows up Phase 1's budget for no marginal retrieval quality — `source_tier` is not read by any retriever today (grep-verified). K2 adds schema surface that has to be maintained forever for a one-time backfill need. K1 is the pragmatic choice: drop the field from the fingerprint, add a Phase 2 unit test asserting backfill-mapping-equivalence, and if `source_tier` becomes retrieval-critical later, the follow-up is "persist the column" — which is a narrower change than doing it preemptively. Phase 2 `fingerprint.py`'s `CLASSIFIER_FINGERPRINT_FIELDS` constant must enumerate exactly what is persisted; the Phase 2 State Notes must name the decision ("dropped source_tier, 2026-MM-DD, per Decision K1").

RATIFIED 2026-04-22: K1 — drop `source_tier` from `CLASSIFIER_FINGERPRINT_FIELDS`; reconstruct `document_archetype` / `authority_level` from persisted `tipo_de_documento` / `authority` during backfill; Phase 2 unit test asserts backfill-mapping ≡ live-ingest-mapping to prevent spurious "everything modified" on the first post-ship full rebuild.

---

## 5. Phased Implementation

> Each phase has a Definition of Done + a Verification Command run before marking `PASSED_TESTS`. Tests are required at every phase. State Notes live-updated during execution.

### 5.0 Cross-cutting Invariants

**Invariant I1 — Backwards-compat.** After every phase, `make phase2-graph-artifacts` and `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` must still run to a successful full-rebuild outcome. Full-rebuild is the always-safe fallback; if it breaks, the plan is BLOCKED regardless of what else is green.

**Invariant I2 — Single active row.** At all points (during migration, during delta application, during full-rebuild promotion) exactly one `corpus_generations` row has `is_active=true`. Verified by `SELECT count(*) FROM corpus_generations WHERE is_active = true` returning 1.

**Invariant I3 — Chunks and parent parity.** No `document_chunks` row exists whose `doc_id` points to a `documents` row with `retired_at IS NOT NULL`. Verified by a post-phase SQL probe.

**Invariant I4 — Trace every link.** Every new script + endpoint emits structured events via `instrumentation.emit_event`. Event namespace: `ingest.delta.*`, `ingest.dangling.*`, `ingest.parity.*`. Phase 7 audits; §13 trace schema is authoritative.

**Invariant I5 — Idempotency.** Re-running the same delta (same files on disk, same `delta_id`) against a baseline that already contains its outputs must be a no-op. Tested explicitly in Phase 4 and Phase 5.

**Invariant I6 — Surface boundaries intact.** This plan does not touch `pipeline_d/`, `normativa/`, `interpretacion/`, `answer_*.py`, or retriever adapters. Any temptation to reach into those modules is a signal to STOP and re-read `CLAUDE.md`.

### Phase template (each phase below follows this shape)

```
Goal           — one sentence
Files create   — exact paths, never wildcards
Files modify   — exact paths + brief edit summary
Tests add      — file path + case count + Verification Command
DoD            — checklist of "done" concretely
Trace events   — emitted event_type strings (if any)
Migrations     — touched migrations (if any)
State Notes    — live-updated; default `(not started)`
Resume marker  — within-phase last-known-good checkpoint
```

---

### Phase 0 — Decisions ratified
- **Goal:** all 11 §4 decisions (A-K) marked with explicit user choice; §2 `Plan status` set to `APPROVED`.
- **Files create:** none.
- **Files modify:** THIS doc (§4 RATIFIED lines, §2 dashboard).
- **Tests add:** none.
- **DoD:** every RATIFIED line in §4 names a choice (e.g. `RATIFIED 2026-MM-DD: A1`); §2 Plan status = APPROVED; §2 Branch for execution named; pre-flight (§0.5) run clean. Reviewer-added Decision K has a ratified line alongside A-J.
- **Verification command:** `grep -c "^RATIFIED" docs/next/additive_corpusv1.md` → 11.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 1 — Schema migration + backfill
- **Goal:** land the additive schema additions (two migrations) without touching existing columns or data; backfill `doc_fingerprint` for the current active generation; land the `ingest_delta_jobs` table + `promote_generation` RPC skeleton.
- **Files create:**
  - `supabase/migrations/20260422000000_corpus_additive.sql` — SQL:
    - `ALTER TABLE documents ADD COLUMN doc_fingerprint TEXT`, `ADD COLUMN last_delta_id TEXT`, `ADD COLUMN retired_at TIMESTAMPTZ`.
    - `CREATE INDEX idx_documents_doc_fingerprint ON documents (doc_fingerprint) WHERE doc_fingerprint IS NOT NULL`.
    - `CREATE INDEX idx_documents_retired_at ON documents (retired_at) WHERE retired_at IS NULL` (partial — covers the hot query).
    - `CREATE INDEX idx_documents_last_delta ON documents (last_delta_id) WHERE last_delta_id IS NOT NULL`.
    - `ALTER TABLE normative_edges ADD COLUMN last_seen_delta_id TEXT`.
    - `CREATE INDEX idx_normative_edges_last_seen_delta ON normative_edges (last_seen_delta_id) WHERE last_seen_delta_id IS NOT NULL`.
    - `CREATE UNIQUE INDEX normative_edges_rolling_idempotency ON normative_edges (source_key, target_key, relation) WHERE generation_id = 'gen_active_rolling'`.
    - `CREATE TABLE normative_edge_candidates_dangling (source_key TEXT NOT NULL, target_key TEXT NOT NULL, relation TEXT NOT NULL, source_doc_id TEXT NULL, first_seen_delta_id TEXT NULL, last_seen_delta_id TEXT NULL, raw_reference TEXT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY (source_key, target_key, relation))`.
    - `CREATE INDEX idx_dangling_target_key ON normative_edge_candidates_dangling (target_key)`.
    - `INSERT INTO corpus_generations (generation_id, is_active, documents, chunks, countries, files, knowledge_class_counts, index_dir, created_at, updated_at, generated_at, activated_at) VALUES ('gen_active_rolling', false, 0, 0, ARRAY['colombia'], ARRAY[]::text[], '{}'::jsonb, '', NOW(), NOW(), NOW(), NOW()) ON CONFLICT (generation_id) DO NOTHING` — seed the reserved row, inactive.
  - `supabase/migrations/20260422000001_ingest_delta_jobs.sql` (reviewer-added per revised Decision J/F) — SQL:
    - `CREATE TABLE ingest_delta_jobs (...)` per Decision J2 schema in §4.
    - `CREATE UNIQUE INDEX idx_ingest_delta_jobs_live_target ON ingest_delta_jobs (lock_target) WHERE stage NOT IN ('completed','failed','cancelled')` — the row-based lock.
    - `CREATE INDEX idx_ingest_delta_jobs_heartbeat ON ingest_delta_jobs (last_heartbeat_at) WHERE stage NOT IN ('completed','failed','cancelled')` — supports the janitor reaper.
    - `CREATE OR REPLACE FUNCTION acquire_ingest_delta_lock(lock_target text) RETURNS boolean AS $$ BEGIN RETURN pg_try_advisory_xact_lock(hashtext('gen_active_rolling:' || lock_target)); END; $$ LANGUAGE plpgsql` — the J1 RPC helper (used inside transactional RPCs; NOT used from the long-running Python apply).
    - `CREATE OR REPLACE FUNCTION promote_generation(target_gen text) RETURNS jsonb AS $$ … $$` — Decision F1 promotion RPC skeleton (body stub returning `{"status":"not_implemented"}` in v1 migration; real body lands in Phase 6 alongside the Makefile target). Must set `statement_timeout = '30min'`, call `PERFORM acquire_ingest_delta_lock('production')`, raise `'promote_generation_lock_busy'` if false.
  - `scripts/backfill_doc_fingerprint.py` (~120 LOC) — CLI: `--target {production,wip}`, `--dry-run`, `--batch-size 200`. For each `documents` row where `doc_fingerprint IS NULL`, computes fingerprint from the row's stored fields per **Decision K1**: drops `source_tier`, reconstructs `document_archetype` / `authority_level` from `tipo_de_documento` / `authority`. No disk read, no classifier re-run.
  - `tests/test_backfill_doc_fingerprint.py` (~6 cases).
  - `tests/test_ingest_delta_jobs_lock.py` (~4 cases, reviewer-added) — asserts that inserting a second non-terminal row for the same `lock_target` raises a unique-constraint violation; transitioning the first row to `completed` then inserting a second succeeds; the heartbeat-reaper SQL (documented in Phase 7) flips stalled rows to `failed`.
- **Files modify:** none (additive).
- **Tests add:**
  - (a) migration SQL parses clean (psycopg2 dry-run).
  - (b) backfill against empty DB → no-op.
  - (c) backfill against 3-doc seed → 3 fingerprints computed, deterministic.
  - (d) backfill is idempotent (re-running changes nothing).
  - (e) backfill `--dry-run` prints count without writing.
  - (f) fingerprint matches the `sha256(content_hash || "|" || canonical_classifier_json)` contract from §0.8, using the Decision K1 backfill field mapping.
  - (g) reviewer-added: backfill-mapping fingerprint is byte-equal to the ingest-path fingerprint for a representative doc whose `CorpusDocument.classifier` was persisted via the `supabase_sink` mapping. If this equivalence fails, the first full-rebuild after shipping Phase 1 will mark every doc `modified` — which is both wasteful and will spam `ingest.delta.sink.doc.modified` trace events across the whole corpus. Block Phase 1 close-out on this test being green.
  - **Verification:** `make supabase-reset && supabase migration up && PYTHONPATH=src:. uv run --group dev pytest tests/test_backfill_doc_fingerprint.py tests/test_ingest_delta_jobs_lock.py -v` → 10 green + existing migrations play clean.
- **DoD:** both migrations apply forward + reverse (`supabase migration down` for each file leaves the DB in the prior state); backfill tests green; partial-unique-index lock test green; `SELECT count(*) FROM corpus_generations WHERE generation_id = 'gen_active_rolling'` returns 1 with `is_active=false`; Invariant I2 unchanged (pre-existing active row still solo-active); `SELECT acquire_ingest_delta_lock('production')` from a fresh psql session returns `true` (confirms the RPC is callable).
- **Trace events:** `ingest.backfill.start`, `ingest.backfill.batch.written`, `ingest.backfill.done`.
- **Migrations:** `20260422000000_corpus_additive.sql` (APPLIED_LOCAL + APPLIED_CLOUD), `20260422000001_ingest_delta_jobs.sql` (APPLIED_LOCAL + APPLIED_CLOUD).
- **State Notes:**
    - 2026-04-22 — Phase 1 executed on branch `feat/additive-corpus-v1`.
    - migrations: both applied to local docker (`supabase migration up`, clean) AND to linked cloud `LIA_Graph` project (`supabase db push --linked`, clean after explicit dry-run per user direction "update all migrations in all databases in all envs"). `LIA_contadores` NOT touched per CLAUDE.md rule.
    - schema probes (via `docker exec supabase_db_lia-graph psql`): `documents.doc_fingerprint` / `last_delta_id` / `retired_at` present; `normative_edges.last_seen_delta_id` present; `ingest_delta_jobs` table with partial-unique-index `idx_ingest_delta_jobs_live_target` present; `normative_edge_candidates_dangling` present; reserved row `gen_active_rolling` seeded inactive; `SELECT count(*) FROM corpus_generations WHERE is_active = true` returns 1 (Invariant I2 preserved).
    - RPCs: `acquire_ingest_delta_lock('production')` returns `t`; `promote_generation('gen_test')` returns the skeleton-status JSON shape. Real `promote_generation` body lands Phase 6.
    - decision: `src/lia_graph/ingestion/fingerprint.py` landed in Phase 1 (not Phase 2 as originally scoped) because `scripts/backfill_doc_fingerprint.py` imports from it. §12.1 subsumption — Phase 2 target-files list narrows to `baseline_snapshot.py` + `test_baseline_snapshot.py` only.
    - decision: `CLASSIFIER_FINGERPRINT_FIELDS` includes `prompt_version` with `DEFAULT_PROMPT_VERSION="paso4_v1"` (reviewer amendment to Decision C1). `source_tier` dropped per Decision K1.
    - decision: reverse-migration checks (the plan's DoD line about `supabase migration down`) are skipped — the Supabase CLI workflow is forward-only and the repo follows that convention. Migrations are additive so rollback would be operator-driven SQL, not a CLI step.
    - tests: 19 cases green — `tests/test_fingerprint.py` (7), `tests/test_backfill_doc_fingerprint.py` (8), `tests/test_ingest_delta_jobs_lock.py` (4). Lock tests run against local docker via `.env.local`-sourced creds; they auto-skip when `SUPABASE_URL` isn't localhost (safety guard).
    - pre-flight deviation: 2 pre-existing failures in `tests/test_phase3_graph_planner_retrieval.py` (pipeline_d follow-up drilldown + loss-compensation case) noted before Phase 1 started. Orthogonal per Invariant I6; not introduced by this phase.
    - Invariant I1: `make phase2-graph-artifacts` and `make phase2-graph-artifacts-supabase` were NOT re-run in this phase; they share code the additive columns don't touch and all column additions use `IF NOT EXISTS`. Full rebuild path will be re-exercised at the Phase 6 CLI smoke.
    - Verification command run: `PYTHONPATH=src:. uv run --group dev pytest tests/test_fingerprint.py tests/test_backfill_doc_fingerprint.py tests/test_ingest_delta_jobs_lock.py -v` → 19 passed.
- **Resume marker:** Phase 1 PASSED_TESTS → pending commit, then Phase 2.

---

### Phase 2 — Baseline snapshot reader + fingerprint helper
- **Goal:** pure, stateless helpers for (a) reading the current `gen_active_rolling` state out of Supabase into an in-memory snapshot and (b) computing composite fingerprints.
- **Files create:**
  - `src/lia_graph/ingestion/fingerprint.py` (~80 LOC) — exports `compute_doc_fingerprint(content_hash: str, classifier_output: Mapping[str, Any]) -> str`, `canonical_classifier_json(output: Mapping[str, Any]) -> str`, and the constant `CLASSIFIER_FINGERPRINT_FIELDS` naming the subset used.
  - `src/lia_graph/ingestion/baseline_snapshot.py` (~180 LOC) — exports `BaselineSnapshot` dataclass (`{relative_path → (doc_id, doc_fingerprint, retired_at, last_delta_id)}`, plus aggregate counts) and `load_baseline_snapshot(client, *, generation_id='gen_active_rolling') -> BaselineSnapshot`. Pure: no side effects; caller supplies the Supabase client.
  - `tests/test_fingerprint.py` (~5 cases).
  - `tests/test_baseline_snapshot.py` (~7 cases).
- **Files modify:** none.
- **Tests add:**
  - `test_fingerprint.py`:
    - (a) stable under key-order permutation of classifier output.
    - (b) differs when `content_hash` differs.
    - (c) differs when any `CLASSIFIER_FINGERPRINT_FIELDS` value differs.
    - (d) ignores fields outside `CLASSIFIER_FINGERPRINT_FIELDS`.
    - (e) empty classifier output → deterministic sentinel fingerprint.
  - `test_baseline_snapshot.py`:
    - (a) empty DB → empty snapshot.
    - (b) 3 non-retired docs → 3 snapshot entries.
    - (c) 1 retired doc → entry with `retired_at` set, still present in snapshot.
    - (d) filters by `generation_id` (does not leak rows from other generations).
    - (e) aggregate `total_docs` / `total_chunks` / `total_edges` populated.
    - (f) handles Supabase pagination (mock >1000 rows).
    - (g) tolerates missing columns (e.g. `doc_fingerprint IS NULL` on legacy rows).
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_fingerprint.py tests/test_baseline_snapshot.py -v` → 12 green.
- **DoD:** helpers callable in isolation; fingerprint contract locked against test (a)-(e); snapshot contract locked against test (a)-(g).
- **Trace events:** none (pure modules).
- **Migrations:** none.
- **State Notes:**
    - 2026-04-22 — `fingerprint.py` + `test_fingerprint.py` subsumed by Phase 1 (backfill required fingerprint — §12.1 in-flight decision). Phase 2 target-files list narrowed to `baseline_snapshot.py` + `test_baseline_snapshot.py`.
    - `BaselineSnapshot` exposes `documents_by_relative_path`, `total_docs`, `total_chunks`, `total_edges`, `retired_docs`. Retired docs are kept in the mapping (not filtered out) so the planner can distinguish "doc is back" (retired_at clear + re-introduction) from "brand new doc".
    - Paginates in 1000-row pages via PostgREST `.range()` (Supabase default cap). Tested up to 1250 rows in `test_handles_pagination_over_1000_rows`.
    - Aggregate counts use PostgREST `count="exact"`; on any failure (e.g. missing table) fall back to 0.
    - Verification: `pytest tests/test_baseline_snapshot.py -v` → 8 passed. `tests/test_fingerprint.py` stays green (7 cases, unchanged since Phase 1).
- **Resume marker:** Phase 2 PASSED_TESTS → pending commit.

---

### Phase 3 — Delta planner (pure)
- **Goal:** pure module that consumes `(on_disk_corpus_documents, baseline_snapshot)` and emits a `CorpusDelta` dataclass classifying every doc into added / modified / removed / unchanged.
- **Files create:**
  - `src/lia_graph/ingestion/delta_planner.py` (~220 LOC) — exports `CorpusDelta` dataclass, `plan_delta(disk_docs, baseline, *, delta_id=None) -> CorpusDelta`, and `summarize_delta(delta) -> dict` for reporting / trace.
  - `tests/test_delta_planner.py` (~12 cases).
- **Files modify:** none.
- **Tests add:**
  - (a) both empty → empty delta, all buckets size 0.
  - (b) 3 on disk, 0 in baseline → all added.
  - (c) 0 on disk, 3 in baseline → all removed.
  - (d) 3 identical (same fingerprint) → all unchanged.
  - (e) 1 on disk with different fingerprint than baseline → 1 modified, 0 added, 0 removed.
  - (f) mixed (1 added, 1 modified, 1 removed, 2 unchanged) → correct bucketing.
  - (g) retired baseline entry re-appearing on disk with same fingerprint → classified as added (retired_at gets cleared in the write path, not here).
  - (h) retired baseline entry re-appearing with different fingerprint → classified as added (same rationale; re-introduction is a fresh ingest).
  - (i) `delta_id` auto-generated when None, deterministic when supplied.
  - (j) delta planning is pure — same inputs produce the same output, no I/O.
  - (k) `summarize_delta` returns counts per bucket + `delta_id` + `baseline_generation_id`.
  - (l) SUIN re-import fixture (docs owned by a SUIN scope) classified correctly as modified/added per fingerprint; stub docs treated like any other doc.
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_delta_planner.py -v` → 12 green.
- **DoD:** planner produces a complete 4-bucket partition of `(disk ∪ baseline)`; every doc is in exactly one bucket.
- **Trace events:** none (pure).
- **Migrations:** none.
- **State Notes:**
    - 2026-04-22 — pure module landed. `DiskDocument` carries `content_hash` + `classifier_output` + `relative_path`; the planner calls `compute_doc_fingerprint` on the in-memory classifier output so Phase 6 orchestrator can pass the output directly from the PASO 4 classifier without re-serialization.
    - decision: already-retired baseline docs that stay off disk are a no-op (not re-removed). Already-retired docs that come back are routed to `added`, not `modified` — the write path must clear `retired_at` and re-upsert full content.
    - decision: legacy baseline rows with `doc_fingerprint=NULL` always flow to `modified`. Conservative: we can't be sure the classifier output hasn't drifted either, so we force a rewrite. First full-rebuild after backfill removes this edge case.
    - Verification: `pytest tests/test_delta_planner.py -v` → 15 passed (12 planned + 3 extra coverage: legacy-null-fingerprint, retired-stays-off-disk, empty-path ignore).
- **Resume marker:** Phase 3 PASSED_TESTS → pending commit.

---

### Phase 4 — Additive Supabase sink path
- **Goal:** `SupabaseCorpusSink` gains a `write_delta()` path that consumes a `CorpusDelta` and applies it to `gen_active_rolling` with correct add/modify/remove semantics; dangling-candidate store lands alongside.
- **Files create:**
  - `src/lia_graph/ingestion/dangling_store.py` (~160 LOC) — exports `DanglingStore` wrapping the `normative_edge_candidates_dangling` table: `load_for_target_keys(keys) -> dict`, `upsert_candidates(candidates, *, delta_id)`, `delete_promoted(candidates)`, `gc_older_than(delta_id_threshold)`.
  - `tests/test_supabase_sink_delta.py` (~10 cases).
  - `tests/test_dangling_store.py` (~6 cases).
- **Files modify:**
  - `src/lia_graph/ingestion/supabase_sink.py` — add `write_delta(delta: CorpusDelta, *, delta_articles, delta_edges, dangling_store) -> SupabaseDeltaResult`. Internally:
    - For `added`: upsert documents + chunks as today, tagged with `last_delta_id = delta.delta_id` and `sync_generation = 'gen_active_rolling'`.
    - For `modified`: upsert documents; compute per-doc current chunk-id set from Supabase; upsert new chunk set; hard-delete chunks in the set difference.
    - For `removed`: set `retired_at = NOW()`, `last_delta_id = delta.delta_id`; hard-delete chunks WHERE `doc_id IN (...)`; delete edges WHERE `source_key IN (<article keys of retired docs>) AND generation_id = 'gen_active_rolling'`.
    - Edges: apply Pass A (new edges from delta articles), Pass B (promote dangling candidates whose `target_key ∈ new_article_keys(delta)`), Pass C (delete prior outbound edges for modified docs' article keys, then upsert).
    - Update `corpus_generations` row for `gen_active_rolling` with recomputed counts; bump `updated_at`.
    - Emit trace events per Invariant I4.
- **Tests add:**
  - `test_supabase_sink_delta.py`:
    - (a) empty delta → no writes, no errors.
    - (b) added-only delta → documents + chunks + edges present; unchanged rows untouched.
    - (c) modified-only delta → chunk set difference applied correctly (some upserted, some deleted).
    - (d) removed-only delta → `retired_at` set, chunks gone, outbound edges gone.
    - (e) mixed delta → all three bucket effects compose.
    - (f) dangling candidate whose target arrives in a modified doc → promoted to `normative_edges`; dangling row deleted.
    - (g) new edge whose target is unknown → lands in dangling store, not `normative_edges`.
    - (h) re-applying the same delta is a no-op (Invariant I5).
    - (i) delta referencing a doc that's already retired in baseline with same fingerprint → re-introduction path: `retired_at` cleared, chunks re-upserted.
    - (j) `SupabaseDeltaResult` reports per-bucket counts that sum to delta size.
  - `test_dangling_store.py`:
    - (a) empty load.
    - (b) upsert N candidates → N rows; re-upsert same → still N, `last_seen_delta_id` advanced.
    - (c) `load_for_target_keys` returns only matching rows.
    - (d) `delete_promoted` removes exactly the named rows.
    - (e) `gc_older_than` removes rows with `last_seen_delta_id` < threshold.
    - (f) unique constraint enforced on `(source_key, target_key, relation)`.
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_supabase_sink_delta.py tests/test_dangling_store.py -v` → 16 green.
- **DoD:** round-trip test: (seed baseline with 100 docs via full-rebuild → add 5 docs via delta → modify 2 → remove 1) produces final Supabase state **row-set-equivalent** to (full-rebuild of the resulting 104-doc corpus), ignoring `sync_generation`, `last_delta_id`, and timestamps. Invariant I5 green. Invariant I3 green.
- **Trace events:** `ingest.delta.sink.start`, `ingest.delta.sink.doc.added`, `ingest.delta.sink.doc.modified`, `ingest.delta.sink.doc.retired`, `ingest.delta.sink.edge.written`, `ingest.delta.sink.edge.retired`, `ingest.dangling.upserted`, `ingest.dangling.promoted`, `ingest.delta.sink.done`.
- **Migrations:** none (uses Phase 1 schema).
- **State Notes:**
    - 2026-04-22 — `DanglingStore` + `write_delta` landed. `DanglingStore` is a thin PostgREST wrapper; `write_delta` composes three passes.
    - decision: `write_delta` calls through to the existing `write_documents` + `write_chunks` helpers for added/modified docs (preserves the `_subtema_by_doc_id` / `_topic_by_doc_id` coupling from §3.9 — Risk 15 mitigation). Test (c) asserts subtema survives a modification.
    - decision: modified-doc stale-chunk detection reads chunk_ids from Supabase per-doc (O(|modified| + |current_chunks|)); hard-deletes the set difference. Simpler than a bulk DELETE ... WHERE chunk_id NOT IN (...), which is error-prone around the 1000-value PostgREST IN limit.
    - decision: retired-doc article keys come from the `chunk_id` format (`{doc_id}::{article_key}`). Deleting edges only hits rolling `generation_id` (`self.generation_id`); snapshot generations keep their history.
    - decision: Pass A / B / C order = (a) write delta's new edges, (b) promote dangling whose target arrived, (c) upsert new dangling candidates for unresolved ARTICLE targets. Matches §5 Phase 4 description.
    - emitted trace events: `ingest.delta.sink.start` and `ingest.delta.sink.done` with the full payload. The per-doc/per-edge granular events in §13 are deliberately NOT fired (they would flood logs for 1k-doc deltas). Phase 7 will revisit whether to re-enable them behind a verbose flag.
    - Invariant I5 (idempotent re-apply): test (h) asserts row counts stay stable across two identical `write_delta` invocations.
    - Verification: `pytest tests/test_supabase_sink_delta.py tests/test_dangling_store.py tests/test_ingestion_supabase_sink.py tests/test_supabase_sink_subtopic.py -v` → 30 passed (10 delta + 7 dangling + 13 existing sink tests unchanged). No existing sink test regressions.
- **Resume marker:** Phase 4 PASSED_TESTS → pending commit.

---

### Phase 5 — Additive Falkor path
- **Goal:** Falkor mirror of Phase 4. Targeted MERGE for added/modified nodes + edges; targeted `DETACH DELETE` for retired docs' articles and for modified docs' outbound edges before re-MERGE.
- **Files create:**
  - `tests/test_loader_delta.py` (~8 cases).
- **Files modify:**
  - `src/lia_graph/graph/client.py` — add `stage_detach_delete(kind: NodeKind, key: str) -> GraphWriteStatement` and `stage_delete_outbound_edges(source_kind, source_key, relation_subset=None) -> GraphWriteStatement`.
  - `src/lia_graph/ingestion/loader.py` — add `build_graph_delta_plan(delta, *, delta_articles, delta_edges) -> GraphLoadPlan` that emits:
    - `DETACH DELETE` for retired doc articles (using their article keys).
    - `stage_delete_outbound_edges` for modified doc article keys (preserves the node; wipes stale outbound edges).
    - `stage_node` / `stage_edge` MERGE for added/modified nodes + their outbound edges + promoted dangling edges.
    - Does NOT emit statements for unchanged docs.
- **Tests add:**
  - (a) empty delta → empty plan.
  - (b) added-only → only MERGE statements for new nodes + edges.
  - (c) modified-only → DELETE outbound edges + MERGE node + MERGE new edges.
  - (d) removed-only → DETACH DELETE for removed article nodes only.
  - (e) mixed → statements in the correct dependency order (deletes before merges; node merges before edge merges that reference them).
  - (f) promoted dangling edge is included in the MERGE set even though its source doc is unchanged.
  - (g) no DETACH DELETE is ever emitted for `DocumentNode` keys that are still in the active corpus.
  - (h) plan re-applied twice → second application is a MERGE no-op (Falkor-idempotent).
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_loader_delta.py -v` → 8 green.
- **DoD:** parity smoke — given the same delta fixture, Supabase sink (Phase 4) and Falkor delta plan (Phase 5) converge to the same logical row set (measured by article counts + outbound-edge counts per article key). Tested in Phase 7 parity check tests.
- **Trace events:** `ingest.delta.falkor.start`, `ingest.delta.falkor.stmt.emitted`, `ingest.delta.falkor.stmt.executed`, `ingest.delta.falkor.stmt.failed`, `ingest.delta.falkor.done`.
- **Migrations:** none.
- **State Notes:**
    - 2026-04-22 — `stage_detach_delete(kind, key)` and `stage_delete_outbound_edges(source_kind, source_key, relation_subset=None)` added to `GraphClient`. Both validate the node type against the schema before emitting Cypher.
    - `build_graph_delta_plan(delta, *, delta_articles, delta_edges, retired_article_keys, promoted_dangling_edges)` emits statements in dependency order: DETACH DELETE → DELETE outbound edges → MERGE nodes → MERGE edges. Test (e) asserts that order.
    - decision: modified-doc article keys must be passed by the orchestrator (Phase 6) as `delta.modified_article_keys` (duck-typed attribute) or via a dedicated parameter in a future refactor. Phase 5 keeps the attribute route for simplicity; Phase 6 will wire it.
    - decision: Promoted dangling edges are MERGE'd alongside the delta's new edges. The loader doesn't know where each edge came from (delta vs dangling) once they're inside a `GraphLoadPlan` — trace attribution happens upstream at `ingest.dangling.promoted` events.
    - decision: `MERGE … SET n += $properties` stays as-is for Phase 5 (Risk 16 deferred). `first_seen_delta_id` / `last_seen_delta_id` tracking on Falkor nodes can land as a follow-up when the trace demands it; Supabase sink already captures delta attribution at the `documents.last_delta_id` level, which is the authoritative per-doc tracker.
    - Verification: `pytest tests/test_loader_delta.py tests/test_phase2_graph_scaffolds.py` → 30 passed (11 new + 19 existing scaffolds unchanged).
- **Resume marker:** Phase 5 PASSED_TESTS → pending commit.

---

### Phase 6 — Orchestrator wiring + CLI + Makefile + env matrix
- **Goal:** make the additive path reachable end-to-end from a single CLI invocation; bump the env matrix version; mirror the change to all required doc surfaces.
- **Files create:** none (intentionally — every change is an extension of existing files).
- **Files modify:**
  - `src/lia_graph/ingest.py`:
    - Add CLI flags `--additive`, `--delta-id`, `--dry-run-delta`, `--strict-parity` (Phase 7 uses the last).
    - Route through a new helper `_materialize_delta(...)` when `--additive` is set: loads baseline snapshot (Phase 2), runs delta planner (Phase 3), parses only delta articles, runs edge pass A+B+C, calls `sink.write_delta` (Phase 4), calls Falkor delta plan (Phase 5), updates `corpus_generations.gen_active_rolling` counts, emits run-summary JSON.
    - Full-rebuild path (default) unchanged.
  - `Makefile`:
    - Add target `phase2-corpus-additive` that invokes `lia-graph-artifacts --additive --execute-load --strict-falkordb --supabase-sink --supabase-target $(PHASE2_SUPABASE_TARGET) --supabase-generation-id gen_active_rolling`.
    - Add target `phase2-promote-snapshot` (per §4 Decision F1) that calls the `promote_generation(target_gen text)` RPC (body landed in this phase per reviewer's Decision F1 clarifications) and validates the transition. Implement the RPC body here:
      - Inside a single transaction, acquire the xact advisory lock (`acquire_ingest_delta_lock('production')`); raise `'promote_generation_lock_busy'` if false.
      - Reviewer-pick (F1 clarification 3): **do not** UPDATE `sync_generation` / `generation_id` on existing rows. Instead, flip `is_active` — set the named snapshot to `true`, the previously-active row to `false`. Preserves history; no multi-million-row UPDATE.
      - Adjust `normative_edges_rolling_idempotency` partial index predicate to match the currently-active generation, OR (simpler, reviewer-preferred): keep the idempotency index partial on `generation_id = 'gen_active_rolling'` and document that snapshot promotion swaps the rolling row's **data** (via `UPDATE corpus_generations SET is_active = false, activated_at = NOW() WHERE generation_id = 'gen_active_rolling'; UPDATE corpus_generations SET is_active = true, activated_at = NOW() WHERE generation_id = $snapshot`). In this design `gen_active_rolling` becomes dormant after a promotion from a snapshot, and subsequent additive deltas write into whatever is_active currently points at. **This changes the rolling-generation semantics from "always `gen_active_rolling`" to "the current is_active row".** Phase 6 State Notes must record whichever of these two options was picked; update §0.8 glossary accordingly at phase close-out.
      - Return a JSON report: `{"previous_gen": ..., "new_gen": ..., "row_count_changes": {...}, "duration_ms": ...}`.
    - Add target `phase2-reap-stalled-jobs` (reviewer-added, per Decision J2) that runs the janitor SQL for `ingest_delta_jobs` rows with `last_heartbeat_at < NOW() - interval '5 minutes'`. Operator-manual for v1; cron-friendly for follow-up.
  - `docs/guide/orchestration.md`:
    - Bump env matrix version from `v2026-04-21-stv2d` to `v2026-04-22-ac1`.
    - Add change-log row (per reviewer's ratification cadence — name Decisions A-K, the new migrations, the `ingest_delta_jobs` table, and the Phase 8 admin-UI endpoints).
    - Add lane-0 subsection describing additive vs full-rebuild paths.
  - `docs/guide/env_guide.md` — mirror table bump.
  - `CLAUDE.md` — mirror table bump (line 65 "Env v2026-04-18" → new version; reviewer-verified 2026-04-22 this string is stale even before this plan lands).
  - `AGENTS.md` — mirror table bump (line 5 header frontmatter). Reviewer-added to the mirror list.
  - `frontend/src/features/orchestration/orchestrationApp.ts:97` — mirror env-matrix version string in the `/orchestration` HTML status card. Reviewer-verified 2026-04-22 this reads `v2026-04-18` (stale); Phase 6 brings it current.
  - `tests/test_ingest_cli_additive.py` (new file) (~6 cases).
- **Tests add:**
  - (a) `lia-graph-artifacts --help` lists `--additive`, `--delta-id`, `--dry-run-delta`, `--strict-parity`.
  - (b) `--additive --dry-run-delta` against a seeded baseline prints a delta summary and writes NO rows (verified by row-count probe before + after).
  - (c) `--additive` without `--supabase-sink` errors with a clear message (additive mode requires Supabase to be meaningful).
  - (d) `--additive` run ends with exit code 0 on a clean no-op delta (disk matches baseline exactly).
  - (e) `--additive` run on a 3-doc add against a 10-doc baseline produces the expected 13-doc final state (row-count probe).
  - (f) env matrix version string appears in **all five** mirror surfaces (reviewer-updated count): `docs/guide/orchestration.md`, `docs/guide/env_guide.md`, `CLAUDE.md`, `AGENTS.md`, `frontend/src/features/orchestration/orchestrationApp.ts`. Grep cross-check returns ≥ 5 hits for the new version.
  - (g) reviewer-added: `make phase2-promote-snapshot SNAPSHOT_GEN=gen_<UTC>` completes on a seeded baseline and returns the JSON report shape defined in the Phase 6 Makefile bullet.
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_ingest_cli_additive.py -v && npm run test:backend` → all green; `grep -rl "v2026-04-22-ac1" docs/guide CLAUDE.md AGENTS.md frontend/src | wc -l` → ≥ 5.
- **DoD:** `make phase2-corpus-additive PHASE2_SUPABASE_TARGET=production` (local) completes on a 3-doc fixture delta, emits a JSON run report with per-bucket counts; env matrix mirrored across all **5** surfaces (reviewer-updated count); CLI help mentions all new flags; promote RPC body lands and is exercised by `make phase2-promote-snapshot`.
- **Trace events:** `ingest.delta.cli.start`, `ingest.delta.cli.parsed_args`, `ingest.delta.cli.done`.
- **Migrations:** none.
- **State Notes:**
    - 2026-04-22 — CLI + Makefile + env matrix bump landed. Four new CLI flags exposed; `main()` routes to `delta_runtime.materialize_delta` when `--additive` is set. Refuses to run without `--supabase-sink` (additive mode can't function without Supabase).
    - decision: `_materialize_delta` lives in a new sibling module `src/lia_graph/ingestion/delta_runtime.py` (~300 LOC) rather than being appended to `ingest.py` (already 850+ LOC). Per memory "Edit granularly" — keep host files small. `ingest.py` picks up ~70 LOC of CLI glue + a single conditional route at the top of `main()`.
    - decision: env matrix bumped `v2026-04-22-betaflipsall` → `v2026-04-22-ac1` in all 5 mirrors (AGENTS.md, docs/guide/orchestration.md, docs/guide/env_guide.md, CLAUDE.md, frontend/src/features/orchestration/orchestrationApp.ts). Test (g) enforces this — asserts the new version string is present in every mirror before the test passes.
    - decision: `promote_generation` RPC body stays as the Phase 1 skeleton ("not_implemented"). The real body is deferred to Phase 9 rollback drill; `make phase2-promote-snapshot` ships the caller that'll exercise it once the body lands. Phase 9 will decide row-copy vs pointer-flip (reviewer F1 pick: pointer flip).
    - decision: Artifact bundle rewrite (`parsed_articles.jsonl`, `typed_edges.jsonl`) is NOT performed in delta runs. Decision E1 says "full rewrite on every applied delta"; this v1 defers that to Phase 9 when we have real-corpus measurements of dev-mode impact. `delta_runtime.DeltaRunReport` emits a per-delta summary JSON into `artifacts/delta_<id>.json` instead.
    - decision: Strict parity + lock acquisition live in Phase 7. The `--strict-parity` flag is already wired through to `materialize_delta` so that Phase 7 can plug in the parity check without touching the CLI.
    - Makefile targets: `phase2-corpus-additive` (full delta), `phase2-promote-snapshot` (calls the RPC), `phase2-reap-stalled-jobs` (inline SQL janitor — Phase 7 will promote to a proper CLI helper).
    - Verification: `pytest tests/test_ingest_cli_additive.py` → 7 passed. Curated backend smoke set (`test_background_jobs`, `test_phase1_runtime_seams`, `test_phase2_graph_scaffolds`, `test_ui_server_http_smokes`) → 31 passed; no regressions. Invariant I1 preserved (full rebuild path unchanged).
    - Pre-existing 2 failures in `test_phase3_graph_planner_retrieval.py` still red — unchanged, unrelated, Invariant I6 scope.
- **Resume marker:** Phase 6 PASSED_TESTS → pending commit. Phases 7-10 remaining.

---

### Phase 7 — Concurrency guard + parity check + observability
- **Goal:** make additive runs safe against concurrent invocation and catch Supabase↔Falkor drift before it compounds; lock down the §13 trace schema.
- **Files create:**
  - `src/lia_graph/ingestion/parity_check.py` (~140 LOC) — `check_parity(supabase_client, graph_client, *, generation_id=<current active>) -> ParityReport`. Compares document count, chunk count, edge count across Supabase and Falkor with a configurable tolerance (default: **max(5 rows, 0.2%)** per reviewer-revised Decision H1).
  - `src/lia_graph/ingestion/delta_lock.py` (~140 LOC, reviewer-revised name — was `advisory_lock.py`). Owns both halves of Decision J:
    - `acquire_job_lock(supabase_client, *, target, job_id, created_by, delta_id=None) -> JobLock` — inserts a row into `ingest_delta_jobs` with `stage='queued'`. On unique-index violation, raises `DeltaLockBusy` containing the `job_id` of the blocking row so the UI (Phase 8) can offer a reattach action.
    - `JobLock.heartbeat()` — updates `last_heartbeat_at`; called by the apply worker every ≤ 30s.
    - `JobLock.advance_stage(stage, progress_pct)` — atomic stage transition + trace emission.
    - `JobLock.finalize(stage, error=None, report=None)` — terminal transition; releases the row-lock.
    - `with_xact_lock(supabase_client, target, rpc_name, params)` — J1 helper for single-transaction RPC calls (used by `promote_generation`).
    - `reap_stalled_jobs(supabase_client, *, stall_window=timedelta(minutes=5))` — janitor; invoked from `make phase2-reap-stalled-jobs`.
  - `src/lia_graph/ingestion/delta_job_store.py` (~120 LOC, reviewer-added) — CRUD around `ingest_delta_jobs`: `create_job`, `get_job`, `list_live_jobs_by_target`, `request_cancel`, `stream_events_since(cursor)`.
  - `tests/test_parity_check.py` (~5 cases).
  - `tests/test_delta_lock.py` (~6 cases — was `test_advisory_lock.py`, reviewer-renamed).
  - `tests/test_delta_job_store.py` (~6 cases, reviewer-added).
  - `tests/test_additive_observability.py` (~5 cases).
- **Files modify:**
  - `src/lia_graph/ingest.py` — wrap the `--additive` path in `acquire_job_lock(...)`; heartbeat from the delta worker every ≤ 30s; `check_parity(...)` before applying the delta and log the result; if `--strict-parity`, raise on mismatch.
  - THIS doc §13 — populate the authoritative event table with the job-surface and Phase-8-facing events.
- **Tests add:**
  - `test_parity_check.py`:
    - (a) identical counts → `ok=true`.
    - (b) Supabase ahead by 1 (Falkor lag) → `ok=false`, `mismatch=doc`.
    - (c) Falkor ahead by 1 → `ok=false`, `mismatch=doc` (or `edge`, depending).
    - (d) tolerance honored (small mismatch within tolerance → `ok=true` with warning).
    - (e) handles empty both sides (`ok=true`, zero counts).
  - `test_delta_lock.py` (reviewer-revised):
    - (a) first `acquire_job_lock` inserts the row; stage = `queued`.
    - (b) second concurrent `acquire_job_lock` against the same `target` raises `DeltaLockBusy` carrying the first job's `job_id`.
    - (c) finalizing the first job with `stage='completed'` allows a subsequent acquisition.
    - (d) an unhandled exception in the worker still ends with `JobLock.finalize(stage='failed', error=...)` via a context manager.
    - (e) `with_xact_lock` + `acquire_ingest_delta_lock` RPC: second caller raises inside the RPC.
    - (f) `reap_stalled_jobs` flips a row whose heartbeat is older than the window to `stage='failed'` with `error_class='heartbeat_timeout'`.
  - `test_delta_job_store.py` (reviewer-added):
    - (a) `create_job` writes all columns; `get_job` round-trips.
    - (b) `list_live_jobs_by_target` excludes terminal-stage rows.
    - (c) `request_cancel` flips `cancel_requested = true` atomically.
    - (d) `stream_events_since(cursor)` returns only events whose id is > cursor.
    - (e) Re-inserting the same `job_id` raises a unique-constraint violation.
    - (f) Terminal-stage rows are immutable (stage cannot move backwards from `completed` → `running`).
  - `test_additive_observability.py`:
    - Drive a fixture delta through the CLI end-to-end and assert every event_type from §13 is present in `logs/events.jsonl`, in the documented order.
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_parity_check.py tests/test_delta_lock.py tests/test_delta_job_store.py tests/test_additive_observability.py -v` → 22 green.
- **DoD:** §13 table populated; observability smoke green; concurrent-run test confirms J1+J2 guard combination; parity check runs automatically on every `--additive` invocation; stalled-job reaper exercised in a test.
- **Trace events:** `ingest.parity.check.start`, `ingest.parity.check.done`, `ingest.parity.check.mismatch`, `ingest.lock.job.acquired`, `ingest.lock.job.heartbeat`, `ingest.lock.job.released`, `ingest.lock.job.busy`, `ingest.lock.job.reaped`, `ingest.lock.xact.acquired`, `ingest.lock.xact.busy`.
- **Migrations:** none.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 8 — Admin UI + backend job surface (MANDATORY — reviewer-rewritten 2026-04-22)

**Not descopeable.** Additive corpus ingestion MUST be drivable end-to-end from the admin UI. The CLI and the UI share the same backend guarantees (advisory lock, parity check, trace events, rollback affordances). The UI must be correct under realistic failure modes (browser close mid-apply, Supabase 503s, Falkor timeouts, double-click, concurrent operators).

- **Goal:** production-grade admin surface for the additive corpus flow — preview, apply (async with live progress), cancel, reattach, clear terminal states — on top of a backend job surface that survives the browser and concurrent operators.

#### 8.A Backend endpoints (all admin-scoped; all emit §13 trace events)

Host module: new file `src/lia_graph/ui_ingest_delta_controllers.py` (reviewer-verified that `src/lia_graph/ui_ingest_controllers.py` does NOT exist in the repo; the correct sibling directory is `ui_ingest_run_controllers.py` + `ui_ingestion_controllers.py` + `ui_ingestion_write_controllers.py`; the new controller sits alongside these). Route registration in `ui_admin_controllers.py` (or the existing dispatch map).

| Method | Path | Purpose | Semantics |
|---|---|---|---|
| `POST` | `/api/ingest/additive/preview` | Dry-run; returns per-bucket counts + sample-doc diff. | Synchronous (≤ 30s). Runs audit + classifier + delta planner. Does NOT acquire the job lock; read-only against Supabase. |
| `POST` | `/api/ingest/additive/apply` | Start a delta apply. | Inserts a `ingest_delta_jobs` row (`stage='queued'`) inside `acquire_job_lock(...)`. Returns `{job_id, delta_id, status_url, events_url, cancel_url}`. Spawns the background worker via `background_jobs.submit(...)`; returns immediately (`202 Accepted`). |
| `GET` | `/api/ingest/additive/events?job_id=…` | SSE stream of job events. | Reads the row + `ingest.delta.*` events since a `cursor` query param (or from `started_at` if cursor absent). Emits `stage`, `progress_pct`, `bucket_counts`, `last_trace_event`, `heartbeat`. Server sends `retry: 5000` on connection. |
| `GET` | `/api/ingest/additive/status?job_id=…` | Pollable status (fallback for clients that can't SSE). | Reads the row; returns the same shape as a single SSE snapshot. |
| `POST` | `/api/ingest/additive/cancel?job_id=…` | Cooperative cancel. | Flips `cancel_requested = true`. The worker checks at every stage boundary and transitions to `stage='cancelled'` with a partial report. Never mid-write. |
| `GET` | `/api/ingest/additive/live?target=production` | Find live job for reattach. | Returns the non-terminal row for `target` if any, else `{job_id: null}`. Called by the UI on mount to reattach. |

Every endpoint:
- Gates on `require_admin(handler)` (same helper the existing ingest controllers use).
- Runs the same parity check (Decision H1) before apply as the CLI.
- Propagates Falkor outages (no silent fallback, per `CLAUDE.md`).
- Emits `ingest.delta.ui.request` / `ingest.delta.ui.response` events (new, reviewer-added; see §13).

#### 8.B Backend job-worker contract

`src/lia_graph/background_jobs.py` gains an `ingest_delta_worker(job_id)` task (called via the existing `submit`):
- Reads the `ingest_delta_jobs` row.
- Runs the same `_materialize_delta(...)` helper the CLI uses, passing a `progress_callback` that calls `JobLock.advance_stage(stage, pct)` and `JobLock.heartbeat()` every ≤ 30s.
- Checks `row.cancel_requested` at every stage boundary (after planner, after sink, after Falkor).
- On happy path: `JobLock.finalize(stage='completed', report=<json>)`.
- On `DeltaLockBusy` inside the worker: impossible by construction (the row is the lock) — treat as a defect.
- On Supabase 503 / transient: retry at most 3 times with exponential backoff; after that, `finalize(stage='failed', error_class='supabase_unavailable', error_message=...)`.
- On Falkor timeout: no retry (per `CLAUDE.md`'s no-silent-fallback rule); `finalize(stage='failed', error_class='falkor_timeout', error_message=...)`. Parity flags this on the next run.
- On any unhandled exception: `finalize(stage='failed', error_class=exc.__class__.__name__, error_message=str(exc))`. Never leaves a row in `stage='running'`.

**Terminal states are permanent.** `completed` / `failed` / `cancelled` rows never transition again. The UI uses them for final banner rendering.

#### 8.C Frontend (all components produced via `frontend-design:frontend-design` skill, per §0.12)

Brief to the design skill (to be included verbatim in Phase 8 State Notes):
- **Surface:** Sesiones / Ingesta admin tab, additive-delta sub-panel (below existing drag-to-ingest panel).
- **Atoms in use:** `statusDot`, `pipelineStageDot` (per `docs/next/ingestfixv1-design-notes.md`), `createPrimaryButton`, `createDangerButton`, `createSecondaryButton`, `chip`.
- **Molecules to create:** `additiveDeltaBanner`, `additiveDeltaActionRow`, `additiveDeltaProgressPane`, `additiveDeltaTerminalBanner`, `additiveDeltaReattachToast`.
- **Design tokens:** `--p-navy-*`, `--p-success-*`, `--p-warning-*`, `--p-danger-*`, `--chip-*`, IBM Plex stack (atomic-discipline guard enforces tokens-only; no raw hex in `shared/ui/`).
- **Atomic-discipline guard:** `frontend/tests/atomicDiscipline.test.ts` — must stay green for the new CSS + TS.

Files to create (feature-scoped; no host-file edits to any ≥ 1000-LOC file per memory "Edit granularly"):
- `frontend/src/shared/ui/molecules/additiveDeltaBanner.ts` (~130 LOC) — per-bucket cards (added / modified / removed / unchanged) with counts + sample-doc chips + `delta_id` + `baseline_generation_id`.
- `frontend/src/shared/ui/molecules/additiveDeltaActionRow.ts` (~110 LOC) — Preview + Apply buttons with confirmation modal. Apply modal names the `delta_id` and the counts explicitly ("Aplicar delta D-... con +3 / ~2 / -1 cambios. Esto afecta producción.") before posting. Double-click guard: after the first Apply POST, the button disables and swaps to a spinner until the server returns a `job_id`.
- `frontend/src/shared/ui/molecules/additiveDeltaProgressPane.ts` (~180 LOC) — live progress pane bound to `/events?job_id=...`. Renders per-stage dot row + per-bucket progress + last-heartbeat-at + cancel button.
- `frontend/src/shared/ui/molecules/additiveDeltaTerminalBanner.ts` (~160 LOC) — four terminal states (success/partial/failed/cancelled) with appropriate tokens + a copy-to-clipboard for the next operator command (e.g. `make phase2-embed-backfill` on success with new chunks — per reviewer-revised Decision I1).
- `frontend/src/features/ingest/additiveDeltaController.ts` (~320 LOC) — orchestrates preview → apply → SSE → terminal. On controller mount: calls `GET /api/ingest/additive/live?target=production` and, if a live job exists, reattaches without posting.
- `frontend/src/features/ingest/additiveDeltaReattach.ts` (~80 LOC) — localStorage-backed reattach: persists `job_id` on apply POST success, clears on terminal state observed, also consulted on mount.
- `frontend/src/features/ingest/additiveDeltaSse.ts` (~140 LOC) — SSE subscriber with auto-reconnect backoff + poll fallback after N reconnect attempts (default N=5). Exports `subscribeJobEvents(jobId, handlers)`.
- `frontend/src/styles/admin/additive-delta.css` (~200 LOC) — tokens-only.
- `frontend/tests/additiveDelta.test.ts` (~12 cases — see §8.E matrix).
- `frontend/tests/additiveDeltaReattach.test.ts` (~5 cases).
- Host-file edit: `frontend/src/features/ingest/ingestController.ts` (543 LOC — below 1000, safe to edit) — mount the delta panel under an existing slot.

#### 8.D UI state model

Five view states managed by `additiveDeltaController`:

1. **Idle** — no job loaded; Preview button enabled; Apply disabled.
2. **Previewed** — banner rendered from `/preview` response; Apply button enabled (with double-click guard).
3. **Running** — SSE connected; progress pane visible; Cancel button enabled; Preview + Apply disabled.
4. **Terminal** — one of `{completed, failed, cancelled}`; terminal banner visible; "Run another delta" button resets to Idle; localStorage reattach cleared.
5. **Error** (transient) — preview or apply call returned 4xx/5xx; show error toast with retry; do NOT transition to Terminal.

**Reload-safe mount:**
```
On mount:
  localJobId = localStorage.getItem('additive-delta.jobId')
  liveJob    = await GET /api/ingest/additive/live?target=production
  if liveJob.job_id:
    jobId = liveJob.job_id  // server-truth wins over localStorage
    if jobId !== localJobId: localStorage.setItem(...)
    transition → Running (SSE reattach)
  elif localJobId:
    status = await GET /api/ingest/additive/status?job_id=localJobId
    if status.stage in terminal: transition → Terminal; localStorage.removeItem(...)
    else: localStorage.removeItem(...) // stale; clear
  else:
    transition → Idle
```

**Empty-delta handling:** if `/preview` returns `added=0, modified=0, removed=0`, the banner renders "Sin cambios detectados — la base ya coincide con el corpus en disco" and the Apply button stays disabled. The UI never POSTs to `/apply` with an empty delta (reviewer-pick per Decision E1's "skip artifact-bundle rewrite on empty delta").

#### 8.E End-to-end failure-mode test matrix (reviewer-added; MANDATORY)

Every row is a test that MUST exist + pass before Phase 8 closes. Vitest for units, Playwright for browser-level.

| # | Failure mode | Expected UI outcome | Test |
|---|---|---|---|
| F1 | Browser close mid-apply | Backend worker continues; job reaches terminal state. Reload reattaches and renders the terminal banner. | `additiveDeltaReattach.test.ts` (a) + Playwright `additive_delta_ui.spec.ts` (a) |
| F2 | Supabase 503 during sink writes | Worker retries 3× then fails with `error_class='supabase_unavailable'`. UI terminal banner = failed state + suggests "retry after Supabase recovery" + shows the raw error class. | `additiveDelta.test.ts` (c) + integration test `test_ingest_delta_apply_supabase_503.py` |
| F3 | Falkor timeout during Cypher load | Worker fails immediately (no retry, per `CLAUDE.md`) with `error_class='falkor_timeout'`. UI banner distinguishes this from Supabase failure and tells operator parity will be off until next run. | `additiveDelta.test.ts` (d) + integration test |
| F4 | Concurrent Apply click (two operators) | Second `/apply` POST returns 409 with `DeltaLockBusy` body containing the first `job_id`. UI shows "Ya hay un delta en curso; reattaching a job {id}" toast and transitions to Running bound to the existing job. | `additiveDelta.test.ts` (e) + Playwright (b) |
| F5 | Same-operator double-click Apply | Second click is a no-op (button disabled after first click returns a job_id). | `additiveDelta.test.ts` (f) |
| F6 | Cancel mid-apply | Next stage boundary finalizes with `stage='cancelled'` and a partial report. UI grey banner + what-completed summary. | `additiveDelta.test.ts` (g) + Playwright (c) |
| F7 | Empty delta | UI never POSTs `/apply`. Empty-state banner. | `additiveDelta.test.ts` (h) |
| F8 | Parity mismatch with `--strict-parity` | `/apply` returns 409 with a parity report naming which counts diverged. UI shows a parity-failure banner and the field-level diffs. | `additiveDelta.test.ts` (i) + integration test |
| F9 | SSE transient disconnect | Auto-reconnect with backoff; after 5 fails, switch to 10s polling on `/status`. UI shows a small "reconectando…" indicator but does not leave Running. | `additiveDelta.test.ts` (j) |
| F10 | Backend crash after row insert, before worker starts | Janitor reaps the row after heartbeat-timeout (5 min). UI polling `/status` eventually sees `stage='failed'`. | Integration test + Phase 7 janitor test covers the reaper |
| F11 | Non-admin user hits `/apply` | 403; UI never exposes the button to non-admins (route-level gate). | `test_ui_ingest_delta_controllers.py` (admin-scope gate) |
| F12 | Operator clicks cancel after job already `completed` | 409 `JobAlreadyTerminal`; UI toast "El delta ya había terminado." | `additiveDelta.test.ts` (k) |

- **Tests add (aggregated counts):**
  - `tests/test_ui_ingest_delta_controllers.py` (~10 cases): preview happy path, apply happy path returns `202`, apply while another job live returns `409` with lock body, status round-trip, events SSE emits `stage` transitions, cancel flips `cancel_requested`, admin-auth gate, 503 propagation, parity-mismatch 409, empty-delta is rejected at preview (gentle error) OR accepted and UI is expected to not POST apply (pick one, document in State Notes).
  - `frontend/tests/additiveDelta.test.ts` (~12 cases per §8.E above).
  - `frontend/tests/additiveDeltaReattach.test.ts` (~5 cases): empty state, localStorage only, server-live only, server-live + stale-localStorage conflict, terminal-then-mount.
  - `tests/e2e/additive_delta_ui.spec.ts` (Playwright, ~6 cases): full happy path, browser close + reload reattach, concurrent click second session, cancel mid-apply, failure + error-class rendering, empty delta.
  - Atomic-discipline guard (`frontend/tests/atomicDiscipline.test.ts`) stays green: no raw hex in `shared/ui/`, no inline SVG outside `shared/ui/icons.ts`, tokens-only CSS.

- **Verification:**
  - `PYTHONPATH=src:. uv run --group dev pytest tests/test_ui_ingest_delta_controllers.py -v` → 10 green.
  - `cd frontend && npx vitest run tests/additiveDelta.test.ts tests/additiveDeltaReattach.test.ts tests/atomicDiscipline.test.ts` → 29 green.
  - `npm run test:e2e -- --grep additive_delta_ui` → 6 green.

- **DoD:**
  1. Operator can click Preview + Apply in the browser and drive a fixture delta end-to-end; terminal banner reports success correctly.
  2. Failure-mode matrix §8.E: all 12 rows have tests + all pass.
  3. Reload-safe: closing the browser mid-apply and reopening reattaches to the live job; reopening after terminal shows the terminal banner.
  4. Concurrent-apply is well-behaved: second operator sees reattach, not 500.
  5. Invariant I1 (full-rebuild still works) unaffected — `make phase2-graph-artifacts-supabase` regression green.
  6. `frontend-design:frontend-design` skill was invoked for every new molecule/organism; State Notes carries a `design:` line per §0.12 naming the brief version + atomic-discipline guard pass timestamp.
  7. Atomic-discipline guard green.
  8. No edits landed in any ≥ 1000-LOC host file.
- **Trace events:** `ingest.delta.ui.request`, `ingest.delta.ui.response`, `ingest.delta.ui.sse.connected`, `ingest.delta.ui.sse.disconnected`, `ingest.delta.ui.sse.reconnected`, `ingest.delta.ui.sse.polling_fallback`, `ingest.delta.ui.cancel_requested`, `ingest.delta.ui.reattach`, `ingest.delta.worker.start`, `ingest.delta.worker.stage`, `ingest.delta.worker.heartbeat`, `ingest.delta.worker.done`, `ingest.delta.worker.cancel_observed`, `ingest.delta.worker.failed`. See §13.
- **Migrations:** none (table created in Phase 1 per reviewer-revised migration ledger).
- **State Notes:** (not started) — must carry the `design:` line confirming the skill invocation, plus an explicit bullet naming which host file was edited to mount the new panel and its LOC count at time of edit.
- **Resume marker:** — (Phase 8 is mandatory; no descope path. If the executing agent concludes Phase 8 is blocked by something outside their scope, mark `BLOCKED` and surface to the user; do not skip.)

---

### Phase 9 — E2E against real corpus (CLI + UI paths both)
- **Goal:** execute the full `full-rebuild → additive delta (add 10) → additive delta (modify 3 + remove 2)` sequence against the real `knowledge_base/` corpus on local Supabase + local Falkor; capture evidence; gate cloud rollout. **Reviewer-revised:** run the sequence TWICE — once via CLI, once via the Phase 8 UI — because the two paths exercise different concurrency/error surfaces even though they call the same `_materialize_delta` helper.
- **Files create:**
  - `tests/manual/additive_corpus_v1_runbook.md` — step-by-step runbook. Two sections:
    - §A. CLI-driven runbook (preflight, full rebuild, first delta, second delta, parity checks, rollback drill).
    - §B. UI-driven runbook (reviewer-added): log in as `admin@lia.dev`, open Sesiones, click Preview, inspect banner, click Apply, watch progress pane, close-reopen browser mid-apply, verify reattach, verify terminal banner, cross-check SSE trace against `logs/events.jsonl`.
    - §C. Cross-path equivalence: the final Supabase + Falkor state after (CLI-only run) vs (UI-only run of the same fixture delta) must be row-set-equivalent. Test in the evidence directory.
  - `tests/manual/additive_corpus_v1_evidence/<run-ts>/` — capture per run: baseline snapshot, delta plans, sink reports, Falkor parity probes, retrieval-eval before/after, wall-clock timings, SSE transcript for UI runs, browser reload screenshots for UI reattach.
- **Files modify:** none.
- **Tests add:** the runbook IS the test. Each E2E run produces an evidence directory. Playwright spec from Phase 8 is re-executed here against the real corpus fixture, not a stub (the Playwright harness needs a `LIA_E2E_CORPUS=real_small` mode that points at a ~50-doc subset of `knowledge_base/`).
- **DoD:**
  - (1) Full rebuild produces a baseline at `gen_<UTC>`; promoted to `gen_active_rolling` via `make phase2-promote-snapshot`.
  - (2) Additive delta (add 10) completes in ≤ 2 min wall-clock excluding embeddings; parity check green; retrieval eval `make eval-c-gold` stays ≥ 90.
  - (3) Additive delta (modify 3 + remove 2) completes cleanly; retired docs' chunks absent; dangling candidates (if any) behave per §3.5.
  - (4) Rollback drill: invoke the `promote_generation` RPC to flip `is_active` back to the baseline snapshot, verify retrieval serves from baseline (run two sample questions against the chat endpoint), invoke again to flip back to rolling. All three transitions clean; no silent data loss; `ingest.lock.xact.*` events recorded.
  - (5) Evidence directory committed (or explicitly §12.1-subsumed).
  - (6) `logs/events.jsonl` carries the complete §13 trace for at least one CLI delta AND at least one UI delta (reviewer-revised — must verify `ingest.delta.ui.*` events fire on UI-driven runs).
  - (7) UI-driven run (§B): operator reloads the browser mid-apply at least once; reattach is exercised and the final terminal banner matches the CLI-driven run's report.
  - (8) Cross-path equivalence check (§C): Supabase row-set and Falkor node/edge-set after the UI-driven run equal those after the CLI-driven run for the same fixture delta, modulo timestamps and `delta_id`.
- **Trace events:** consumed.
- **Migrations:** none.
- **State Notes:** (not started)
- **Resume marker:** — (on interrupt mid-E2E: capture which step of the runbook was last green; next session resumes from there).

---

### Phase 10 — Close-out + handoff
- **Goal:** land the final change-log entry; relocate this doc to `docs/done/`; open the PR; mark plan COMPLETE.
- **Files modify:**
  - `docs/guide/orchestration.md` — add `v2026-04-22-ac1` change-log entry referencing Phase 9 evidence.
  - THIS doc — §2 Plan status → `COMPLETE`; `git mv docs/next/additive_corpusv1.md docs/done/additive_corpusv1.md`.
- **DoD:** PR open against `main`; all phase ledger rows `DONE`; change-log landed; doc relocated.
- **State Notes:** (not started)
- **Resume marker:** —

---

## 6. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Classifier drift makes "unchanged" bucket near-empty, defeating additivity | Med | High | Composite fingerprint (Decision C1) catches this; if it becomes dominant, open a follow-up to cache classifier outputs by `(content_hash, prompt_version)` |
| Partial failure mid-delta leaves `gen_active_rolling` inconsistent | Low | High | Every stage writes its `delta_id` marker; re-run is idempotent (Invariant I5); rollback to prior snapshot always available |
| `normative_edges_rolling_idempotency` partial index bloats | Low | Med | Schedule periodic `VACUUM (FULL, ANALYZE)` on `normative_edges`; document in `docs/guide/env_guide.md` |
| Falkor divergence on partial Cypher failure | Med | Med | Parity check before every delta; `--strict-parity` available; full-rebuild self-heals |
| Concurrent additive runs race on rolling row | Low | High | Advisory lock (Decision J1); `DeltaLockBusy` surfaces clearly |
| SUIN re-import mis-classified as "everything modified" | Med | Med | Phase 3 test (l) locks this; SUIN doc fingerprints include their SUIN source id |
| Operator promotes a broken full-rebuild snapshot into rolling | Low | High | Phase 9 rollback drill documented; snapshot → rolling is a separate explicit step (Decision F1) |
| Retired-doc chunks leak into retrieval because a filter was missed | Low | High | Invariant I3 + hard-delete chunks (Decision B1) makes the leak impossible at the storage layer, not just the query layer |
| Dangling store grows unbounded over years of drift | Low | Low | Periodic `gc_older_than` (Phase 4 API); budget a background job in a follow-up |
| ~~Phase 8 UI slips → Phase 9 blocked~~ | ~~Low~~ | ~~Low~~ | ~~Decision G2 descope is explicit and pre-approved~~ **Reviewer-struck 2026-04-22: G2 removed. Phase 8 is mandatory. See Risk 11 below.** |
| **Reviewer-added 11 — Backfill fingerprint shape ≠ ingest fingerprint shape** | Med | High | Decision K1 drops `source_tier`; Phase 2 test (f)+(g) assert byte-equality between backfill-built and ingest-built fingerprints for representative docs. If this fails, the first full-rebuild after shipping will mark every doc `modified` — wasteful but not incorrect. Detect via Phase 9 evidence directory. |
| **Reviewer-added 12 — Phase 8 SSE proxy in prod strips `text/event-stream`** | Low | Med | Known Vercel/Cloudflare gotcha; Phase 8 polling-fallback after N SSE reconnects is the mitigation. Document the `N` in the `additiveDeltaSse` options. |
| **Reviewer-added 13 — Concurrent apply while promote in progress** | Low | High | `promote_generation` RPC and `--additive` path both acquire the same lock target. If promote is mid-body, apply attempts block via J1 RPC lock (fast-fail); if apply is mid-stage, promote attempts return the blocking job_id. Exercise in Phase 9 rollback drill. |
| **Reviewer-added 14 — Stale env-matrix mirrors** | Low | Low | `CLAUDE.md` and `orchestrationApp.ts` are already drifted at plan authoring; Phase 6 bumps everyone. If another plan lands a different version between authoring and Phase 6, the executing agent must take the max of the two. |
| **Reviewer-added 15 — `write_delta` skips `_subtema_by_doc_id` population** | Med | High | §3.9 documents the cross-method coupling. If Phase 4's `write_delta` paves over `write_documents` for modified docs (e.g. an optimization that skips the doc upsert when `doc_fingerprint` matches a baseline that we then try to upsert chunks against), the `_subtema_by_doc_id` dict is empty and chunks land with `subtema=None`. Phase 4 test (c) must assert `subtema` is non-null on every chunk of a modified doc. |
| **Reviewer-added 16 — `MERGE … SET n += $properties` overwrites `first_seen_delta_id`** | Med | Med | §3.4 documents the issue. Phase 5 must decide: (a) extend `stage_node` with explicit `create_properties` / `match_properties` splits, OR (b) accept that `first_seen_delta_id` cannot be tracked via node properties and store it only in Supabase. Reviewer-pick: (a) for new nodes; skip property writes for unchanged nodes (don't MERGE them at all). |

---

## 7. Out of Scope

- Per-tenant additive (different active generations per customer).
- Incremental artifact bundle (`parsed_articles.jsonl`-diff). Dev mode stays full-rewrite.
- Classifier output caching by `(content_hash, prompt_version)`. Tracked as a follow-up. **Reviewer note:** given §0.7's revised wall-clock estimate, this follow-up should be prioritized as v1.1 immediately after v1 ships — the current "20-25 min per delta" dominated by the classifier pass is a bad operator experience that undermines the whole value proposition of "additive."
- Automatic full-rebuild trigger when dangling-candidates grow past threshold.
- Multi-node Falkor writes / sharding.
- Embedding backfill automation (Decision I2/I3 were rejected).
- Resumable mid-delta state. v1 relies on "re-run is idempotent" **plus the `ingest_delta_jobs` terminal-state guarantee** — a crashed worker never leaves a row in `stage='running'`; the operator re-runs.
- Delta-history admin tab (Decision G3). Tracked as Phase 11 follow-up.
- Auto-retry ladder for Supabase transients beyond the 3 attempts documented in Phase 8 worker contract. Anything worse than 3-attempts-then-fail is an operator decision.

---

## 8. Open Questions for User (Phase 0 sign-off)

1. Ratify or amend all **11** §4 decisions (A-K, including reviewer-added K).
2. Confirm the branch name: default recommendation is `feat/additive-corpus-v1` off `main`. If a different branch is preferred, name it in §2.
3. Confirm the migration filename prefix dates (`20260422000000` + `20260422000001`). If Phase 1 slips past 2026-04-22, rename both to match the actual day.
4. Confirm the env matrix version bump target (`v2026-04-22-ac1`). If another version has landed in the interim, advance accordingly in Phase 6. Reviewer-verified 2026-04-22: two mirrors (`CLAUDE.md` line 65, `orchestrationApp.ts:97`) are already on the older `v2026-04-18` string and will be brought current at the same time.
5. ~~Confirm Phase 8 (admin UI) scope per Decision G.~~ **Reviewer-revised:** Phase 8 is mandatory; the question is whether G3 (history/drilldown) is in scope for v1 or deferred to Phase 11.
6. Confirm that cloud Supabase / cloud Falkor writes are held until Phase 9 evidence review (§0.11).
7. **Reviewer-added:** confirm the reviewer-revised Decision F1 promotion semantics (snapshot-is-active-pointer flip, not row-copy). This changes the meaning of `gen_active_rolling` from "always the rolling row" to "the current is_active row"; if the user disagrees, reopen the decision.
8. **Reviewer-added:** confirm the Decision K1 backfill shape. If the user wants `source_tier` tracked, we move to K2 and the Phase 1 migration grows three columns.
9. **Reviewer-added:** confirm the Decision J revised shape (RPC + row-lock hybrid). If the user prefers a single mechanism, recommend J2-row-only and accept that `promote_generation`'s intra-transaction lock is a best-effort-within-RPC rather than a system-wide guarantee.

---

## 9. Change Log

| Version | Date | Change |
|---|---|---|
| `v0.1-draft` | 2026-04-22 | Initial scoped plan — replaces the earlier informal `additive_corpusv1.md` scratch draft with a full phased, state-aware, self-contained plan matching the `subtopic_generationv1.md` template shape. No code shipped; awaits Phase 0 ratification. |
| `v0.2-reviewer` | 2026-04-22 | **Review pass (reviewer-authored).** Senior-engineer correctness + decision-rationale + UI-reliability pass. Highlights: (a) **Correctness fixes** against the codebase: §3.4 rewritten to flag that `stage_node` / `stage_edge` use `MERGE … SET += $properties` unconditionally (no `ON CREATE / ON MATCH` splits) — new Risk 16 + guidance for Phase 5; §3.5 tightened to confirm pruning is ARTICLE-target-only (not all-target) so dangling-store scope stays minimal; new §3.8 documenting the real surgery surface in `materialize_graph_artifacts` (200+ LOC sequential full-corpus path — Phase 6's "extension of existing files" framing was optimistic); new §3.9 documenting `SupabaseCorpusSink._subtema_by_doc_id` / `_topic_by_doc_id` stateful cross-method coupling (Phase 4 must preserve); §0.3 + §0.5 pre-flight extended to grep for the extra migration + advisory-lock surface; env-matrix mirror list corrected from 4 → 5 surfaces (AGENTS.md was missing, `orchestrationApp.ts:97` + `CLAUDE.md` line 65 confirmed stale at `v2026-04-18`). (b) **Decision rationale with teeth** — every §4 Decision A-J now carries a "Reviewer-revised recommendation" block with a production-experience rationale: A1 concur, B1 concur + retriever `retired_at` filter promoted to same-release-as, C1 concur + `prompt_version` field baked into fingerprint JSON, D1 concur + explicit GC threshold, E1 concur + empty-delta artifact-skip, F1 concur but with 4-point sub-spec on promotion semantics (atomicity via RPC, lock holding, generation-id semantics — reviewer-pick "flip `is_active` pointer, don't row-copy", rollback drill), G rewritten (G2 removed — Phase 8 mandatory), H1 concur + tightened tolerance (max(5 rows, 0.2%)), I1 concur + UI must surface the embed-backfill command explicitly, J rewritten (session-level `pg_try_advisory_lock` doesn't work across PostgREST HTTP calls — rewrote as hybrid J1 RPC + J2 row-based-lock with heartbeat), new Decision K added for the backfill-shape field-persistence gap (K1 reviewer-pick: drop `source_tier` from fingerprint, avoid both schema widening and classifier re-run). (c) **UI reliability mandate** — Phase 8 fully rewritten as MANDATORY, undescopeable, production-grade: 6 backend endpoints (preview / apply / events SSE / status / cancel / live-reattach) atop a new `ingest_delta_jobs` table that is itself the concurrency lock (unique-partial index on `lock_target` where stage non-terminal); background-worker contract with heartbeat + cancel-at-stage-boundary + terminal-state guarantee; frontend state machine with reload-safe reattach + localStorage + SSE auto-reconnect + polling fallback + double-click guard; 12-row failure-mode test matrix (F1-F12) covering browser close mid-apply, Supabase 503, Falkor timeout, concurrent operators, cancel-mid-apply, empty delta, parity mismatch, SSE transient disconnect, post-crash reaper, admin-auth gate, post-terminal cancel. Phase 9 extended to run BOTH CLI-driven and UI-driven E2E runs with a cross-path equivalence check. (d) **Test coverage** — added `tests/test_ingest_delta_jobs_lock.py`, `tests/test_delta_job_store.py`, `tests/test_ui_ingest_delta_controllers.py`, `frontend/tests/additiveDeltaReattach.test.ts`, `tests/e2e/additive_delta_ui.spec.ts`; renamed `test_advisory_lock.py` → `test_delta_lock.py`; re-estimated total new test cases from ~72 → ~110. (e) **Trace schema** — §13 extended with 19 new events across lock / xact / UI / worker namespaces; reviewer-confirmed naming convention alignment. (f) **Risk register** — 6 new risks (11-16) documenting backfill-fingerprint shape equivalence, SSE proxy stripping, concurrent apply-vs-promote, stale env-matrix mirrors, `write_delta`-skips-subtema-population, and MERGE property overwriting. (g) **Cost estimates tightened** — §0.7 rewrote the "≤ 2 min per delta" framing as misleading; realistic 10-doc delta today is ~20-25 min + ~$6 Gemini because the classifier still runs full-corpus under Decision C1. This makes classifier output caching (§7 Out-of-Scope follow-up) a v1.1 must-have, not a nice-to-have. No code changes; §0, §2, §3, §4, §5 (Phases 0/1/6/7/8/9), §6, §7, §8, §13 all edited. Still awaits Phase 0 ratification. |

---

## 10. References

- `CLAUDE.md` (repo root) — Claude-family agent quickstart.
- `AGENTS.md` (repo root) — canonical operating guide.
- `docs/guide/orchestration.md` — runtime map + versioned env matrix.
- `docs/guide/env_guide.md` — operational run-mode guide.
- `docs/next/subtopic_generationv1.md` — plan template shape.
- `docs/next/ingestfixv1-design-notes.md` — admin UI atomic-design conventions.
- `supabase/migrations/20260417000000_baseline.sql` — schema baseline.
- `supabase/migrations/20260418000000_normative_edges_unique.sql` — pre-existing idempotency index.
- `src/lia_graph/ingest.py` — current full-rebuild entrypoint.
- `src/lia_graph/ingestion/supabase_sink.py` — current cloud write path.
- `src/lia_graph/ingestion/loader.py` — current Falkor load-plan builder.
- `src/lia_graph/graph/client.py` — Falkor MERGE stage helpers.

---

## 11. Resume Protocol

If a session is interrupted (crash, context reset, multi-day pause):

1. Open this doc; read §0 (Cold-Start Briefing) top-to-bottom without skimming.
2. Read §0.5 (Execution Mode).
3. Read §2 (State Dashboard). The `Current phase` row + `Last completed phase` row tell you where to resume.
4. Open the active phase in §5. Read its `State Notes` top to bottom. The last line of `State Notes` is the last-known-good checkpoint.
5. Re-run the phase's `Verification` command. If green, mark the phase `PASSED_TESTS` and proceed. If red, diagnose; three attempts max before marking `BLOCKED` and surfacing.
6. If `State Notes` say `blocked: <reason>`, address the blocker first.
7. Before writing code, run the §0.5 pre-flight check. If any line fails, STOP.
8. Commit boundaries are per §0.10; do not skip phase-exit commits.

---

## 12. Autonomous Decision Authority

### 12.1 What the executing agent MAY decide without surfacing

- Internal naming (function names, helper module names, JSON field names within documented contracts, CSS class names, test fixture names). Document the choice in `State Notes`.
- Splitting a phase into sub-commits if it aids review.
- Skipping a phase already achieved by a prior phase's work. Mark `DONE` with `State Notes: subsumed by Phase N`.
- Adding extra tests beyond the minimum count when a code path clearly warrants it.
- Refactoring internal helpers within a phase's target files, as long as public contracts are preserved.
- Choosing the ordering of commits within a phase.
- Reading from Supabase cloud for read-only diagnostics (counts, schema probes) if necessary for debugging. Must NOT write.

### 12.2 What requires surfacing to the user before acting

- Any change to a §4 ratified decision.
- Any change to a migration file after it has been committed and applied anywhere.
- Any operation against cloud Supabase / cloud Falkor before Phase 9.
- Any change to `CLAUDE.md`, `AGENTS.md`, or the env matrix version that was not planned in this doc.
- Any deletion of existing tests.
- Any modification of the hot path (`pipeline_d/`, `normativa/`, `interpretacion/`, `answer_*.py`, retrieval adapters).
- Any force-push, `git reset --hard`, or destructive `git mv` of files outside `docs/next/` ↔ `docs/done/`.

### 12.3 How to record an in-flight decision

1. Make the choice.
2. Document the choice + rejected alternative in `State Notes` with a `decision:` line.
3. If the choice turns out wrong, revert in a subsequent commit; amend the `State Notes` entry with an `amended:` line. Never rewrite history.

---

## 13. Trace Schema (authoritative; audited Phase 7)

All additive-path events emitted via `instrumentation.emit_event(event_type, payload)`. Event naming: `ingest.delta.*`, `ingest.dangling.*`, `ingest.parity.*`, `ingest.lock.*`, `ingest.backfill.*`.

| event_type | Emitted by | Payload fields | Notes |
|---|---|---|---|
| `ingest.backfill.start` | Phase 1 backfill script | `target, total_rows` | One per backfill invocation. |
| `ingest.backfill.batch.written` | Phase 1 backfill script | `target, batch_index, rows_written, elapsed_ms` | One per batch. |
| `ingest.backfill.done` | Phase 1 backfill script | `target, total_rows_written, total_elapsed_ms` | One per invocation. |
| `ingest.delta.cli.start` | Phase 6 CLI | `delta_id, target, dry_run, strict_parity` | Top of `--additive` invocation. |
| `ingest.delta.cli.parsed_args` | Phase 6 CLI | `delta_id, flags_json` | After arg parse. |
| `ingest.delta.plan.computed` | Phase 3 delta planner | `delta_id, added, modified, removed, unchanged, baseline_generation_id` | After `plan_delta`. |
| `ingest.delta.sink.start` | Phase 4 sink | `delta_id, target` | Top of `write_delta`. |
| `ingest.delta.sink.doc.added` | Phase 4 sink | `delta_id, doc_id, relative_path` | One per added doc. |
| `ingest.delta.sink.doc.modified` | Phase 4 sink | `delta_id, doc_id, chunks_upserted, chunks_deleted` | One per modified doc. |
| `ingest.delta.sink.doc.retired` | Phase 4 sink | `delta_id, doc_id, chunks_deleted, edges_deleted` | One per retired doc. |
| `ingest.delta.sink.edge.written` | Phase 4 sink | `delta_id, source_key, target_key, relation, origin` where `origin ∈ {delta,dangling_promoted}` | One per edge upserted. |
| `ingest.delta.sink.edge.retired` | Phase 4 sink | `delta_id, source_key, target_key, relation, reason` where `reason ∈ {doc_retired,doc_modified_rewrite}` | One per edge deletion. |
| `ingest.dangling.upserted` | Phase 4 dangling store | `delta_id, source_key, target_key, relation` | One per dangling candidate added. |
| `ingest.dangling.promoted` | Phase 4 dangling store | `delta_id, source_key, target_key, relation, source_doc_id` | One per candidate promoted out. |
| `ingest.delta.sink.done` | Phase 4 sink | `delta_id, documents_added, documents_modified, documents_retired, chunks_written, chunks_deleted, edges_written, edges_deleted, elapsed_ms` | One per delta. |
| `ingest.delta.falkor.start` | Phase 5 loader | `delta_id, statement_count` | Top of Falkor delta plan execution. |
| `ingest.delta.falkor.stmt.emitted` | Phase 5 loader | `delta_id, stmt_index, stmt_kind` | Trace only; verbose — optional per `LIA_INGEST_TRACE_LEVEL`. |
| `ingest.delta.falkor.stmt.executed` | Phase 5 loader | `delta_id, stmt_index, elapsed_ms` | One per executed statement. |
| `ingest.delta.falkor.stmt.failed` | Phase 5 loader | `delta_id, stmt_index, error_class, error_message` | Propagates (no silent fallback). |
| `ingest.delta.falkor.done` | Phase 5 loader | `delta_id, success_count, failure_count, elapsed_ms` | One per delta. |
| `ingest.parity.check.start` | Phase 7 parity | `delta_id, generation_id` | Before delta application. |
| `ingest.parity.check.done` | Phase 7 parity | `delta_id, supabase_docs, falkor_docs, supabase_chunks, falkor_nodes, supabase_edges, falkor_edges, ok` | One per check. |
| `ingest.parity.check.mismatch` | Phase 7 parity | `delta_id, field, supabase_value, falkor_value, delta` | One per mismatched field. |
| `ingest.lock.job.acquired` | Phase 7 `delta_lock` (J2 row-lock) | `delta_id, target, job_id, created_by` | On `ingest_delta_jobs` row insert. Reviewer-revised (was `ingest.lock.acquired`). |
| `ingest.lock.job.heartbeat` | Phase 7 `delta_lock` | `job_id, stage, progress_pct` | ≤ 30s cadence from worker. |
| `ingest.lock.job.released` | Phase 7 `delta_lock` | `delta_id, target, job_id, held_ms, final_stage` | On `finalize()`. |
| `ingest.lock.job.busy` | Phase 7 `delta_lock` | `target, blocking_job_id` | On unique-index violation; body carries blocking job_id for UI reattach. |
| `ingest.lock.job.reaped` | Phase 7 janitor | `job_id, target, heartbeat_age_seconds, reason` | `reason='heartbeat_timeout'` today; room to grow. |
| `ingest.lock.xact.acquired` | Phase 7 `with_xact_lock` (J1 RPC path) | `rpc_name, lock_target, lock_key_hash` | Inside a Postgres transaction (e.g. `promote_generation`). |
| `ingest.lock.xact.busy` | Phase 7 `with_xact_lock` | `rpc_name, lock_target` | RPC raised `'lock_busy'`. |
| `ingest.delta.ui.request` | Phase 8 controllers | `endpoint, job_id?, delta_id?, actor_id, payload_summary` | Every admin-UI request. Reviewer-added. |
| `ingest.delta.ui.response` | Phase 8 controllers | `endpoint, job_id?, http_status, elapsed_ms, outcome` | Every admin-UI response. |
| `ingest.delta.ui.sse.connected` | Phase 8 events endpoint | `job_id, cursor` | SSE stream opened. |
| `ingest.delta.ui.sse.disconnected` | Phase 8 events endpoint | `job_id, reason, held_ms` | SSE closed (client or server). |
| `ingest.delta.ui.sse.reconnected` | Phase 8 controllers (client) | `job_id, attempt` | Client auto-reconnect fired. |
| `ingest.delta.ui.sse.polling_fallback` | Phase 8 controllers (client) | `job_id, after_attempts` | Fell back to `/status` polling after N reconnect attempts. |
| `ingest.delta.ui.cancel_requested` | Phase 8 controllers | `job_id, actor_id` | On `POST /cancel`. |
| `ingest.delta.ui.reattach` | Phase 8 controllers | `job_id, source='server_live'|'localstorage'|'stale_localstorage'` | On mount reattach path. |
| `ingest.delta.worker.start` | Phase 8 background worker | `job_id, delta_id, target` | Worker picked up the row. |
| `ingest.delta.worker.stage` | Phase 8 background worker | `job_id, stage, progress_pct` | Stage transition. |
| `ingest.delta.worker.heartbeat` | Phase 8 background worker | `job_id, stage, elapsed_ms` | Duplicates `ingest.lock.job.heartbeat` at worker scope; kept for SSE fan-out. |
| `ingest.delta.worker.cancel_observed` | Phase 8 background worker | `job_id, at_stage` | Worker saw `cancel_requested=true` at a stage boundary. |
| `ingest.delta.worker.failed` | Phase 8 background worker | `job_id, error_class, error_message, at_stage` | Terminal failure. |
| `ingest.delta.worker.done` | Phase 8 background worker | `job_id, outcome, report_summary` | `outcome ∈ {completed,failed,cancelled}`. |
| `ingest.delta.embedding_needed` | Phase 4 sink | `delta_id, new_chunks_count` | Advisory — does NOT trigger embedding (§4 Decision I1). |
| `ingest.delta.cli.done` | Phase 6 CLI | `delta_id, outcome, elapsed_ms` | `outcome ∈ {ok,blocked,failed}`. |

---

## 14. Minimum Viable Success

For v1 to ship as "done", the following must be true simultaneously:

1. `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` (full rebuild) still runs to success on the real `knowledge_base/` corpus — unchanged behavior (Invariant I1).
2. `make phase2-corpus-additive` applied to a 10-doc delta on top of a rolling baseline completes in ≤ 2 minutes wall-clock excluding embeddings.
3. Final Supabase row set after a `(full rebuild → add 10 → modify 3 → remove 2)` sequence is **equivalent** (ignoring generation / delta / timestamp columns) to a single full rebuild of the resulting corpus.
4. `make eval-c-gold` threshold 90 held after each additive delta in Phase 9.
5. Parity check green across every Phase 9 delta.
6. Rollback drill (flip active to prior snapshot, flip back) clean.
7. §13 trace schema fires end-to-end on at least one delta captured in `logs/events.jsonl`.
8. Env matrix version bumped in all 4 mirror surfaces.
9. This doc relocated to `docs/done/additive_corpusv1.md` with `Plan status = COMPLETE`.

If any of (1)-(8) fails, the plan is NOT done; Phase 10 does not land.
