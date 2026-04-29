# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Quickstart for Claude-family agents working in `Lia_Graph`, a graph-native RAG product shell for Colombian accounting.

## Canonical Guidance

Read these before changing the served runtime:

1. `AGENTS.md` — canonical repo-level operating guide (layer ownership, surface boundaries, doc discipline)
2. `docs/orchestration/orchestration.md` — end-to-end runtime map + **authoritative** versioned env/flag matrix + change log
3. `docs/guide/chat-response-architecture.md` — companion source of truth for how the `main chat` answer is shaped
4. `docs/guide/env_guide.md` — operational counterpart: run modes, env files, squashed migration baseline, test accounts, corpus refresh

If code and docs disagree, reconcile to `docs/orchestration/orchestration.md` — never the other way around.

## Commands

### Run the app

- `npm run dev` — local app, local Supabase docker, local FalkorDB docker. Fully offline. `LIA_CORPUS_SOURCE=artifacts`, `LIA_GRAPH_MODE=artifacts`.
- `npm run dev:staging` — local app against cloud Supabase + cloud FalkorDB. `LIA_CORPUS_SOURCE=supabase`, `LIA_GRAPH_MODE=falkor_live`.
- `npm run dev:production` — Railway-hosted. Script exits locally; deploy via `railway up`.
- `npm run dev:check` / `npm run dev:staging:check` — run the preflight only (no server).

The launcher (`scripts/dev-launcher.mjs`) owns the per-mode env flags — **do not hardcode `LIA_CORPUS_SOURCE` / `LIA_GRAPH_MODE` into `.env.local` or `.env.staging`**.

### Tests

- `npm run test:health` — golden health: build public UI bundle + focused backend smokes + frontend health vitest + e2e playwright.
- `npm run test:health:fast` — same minus e2e.
- `npm run test:backend` — the curated backend smoke set (`test_background_jobs.py`, `test_phase1_runtime_seams.py`, `test_phase2_graph_scaffolds.py`, `test_phase3_graph_planner_retrieval.py`, `test_ui_server_http_smokes.py`).
- `npm run test:frontend` / `npm run test:frontend:all` / `npm run test:e2e` — frontend-only vitest / full vitest / playwright.
- `make test-batched` — **the only sanctioned way to run the full Python suite.** Runs pytest in 120 batches with stall detection. There is a `conftest` guard that aborts if >20 test files are collected without `LIA_BATCHED_RUNNER=1`, to prevent OOM.
- Single Python test: `PYTHONPATH=src:. uv run pytest tests/test_retriever_falkor.py -q` (or `-k <pattern>` for a single case).
- Evals: `make eval-c-gold` (threshold 90), `make eval-c-full` (batched + retrieval eval + gold).
- Preflight / dependency probe only: `make smoke-deps`.

### Build artifacts and Supabase sync

- `make phase2-graph-artifacts` — build the artifact bundle from `knowledge_base/` into `artifacts/`.
- `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` — same build + run `SupabaseCorpusSink`. **Required before `dev:staging` can serve answers from cloud.** Idempotent; embeddings stay `NULL` (filled by `embedding_ops.py` on a follow-up pass).

### Supabase local stack

`make supabase-start` / `supabase-stop` / `supabase-reset` / `supabase-status`. After a fresh `db reset`, run `PYTHONPATH=src:. uv run python scripts/seed_local_passwords.py` (every `@lia.dev` user → password `Test123!`).

## Repository Layout

- `src/lia_graph/` — Python backend. Entrypoints via `pyproject.toml`: `lia-ui` (`ui_server.py`), `lia-graph-artifacts` (`ingest.py`), `lia-deps-check` (`dependency_smoke.py`).
  - `pipeline_d/` — the served runtime; see "Hot Path" below.
  - `pipeline_c/` — legacy pipeline, still wired for contracts and shared plumbing. `pipeline_router.py` routes between them.
  - `normativa/` and `interpretacion/` — **surface-specific** orchestration/synthesis/assembly. These are parallel to `pipeline_d`'s `main chat` facades, not hidden behind them.
  - `ingestion/` — build-time corpus ingestion (includes `supabase_sink.py`).
  - top-level modules — auth (`password_auth.py`, `platform_auth.py`, `service_account_auth.py`), `ui_*_controllers.py` (HTTP handlers fanning out from `ui_server.py`), storage (`supabase_client.py`, `*_store.py`), domain helpers.
- `frontend/` — Vite + TypeScript UI. Built with `npm run frontend:build` (which is `npm --prefix frontend run build:public`). Tested with vitest + Playwright.
- `scripts/dev-launcher.mjs` — the run-mode entrypoint. Owns env selection, preflight, and the `LIA_*` flag matrix.
- `supabase/migrations/` — squashed baseline (`20260417000000_baseline.sql` + `20260417000001_seed_users.sql`) plus post-baseline files (e.g. `20260418000000_normative_edges_unique.sql`). Pre-squash files are in `_archive/` for reference — **do not replay them**.
- `artifacts/` — filesystem corpus bundle served in dev mode (`canonical_corpus_manifest.json`, `parsed_articles.jsonl`, `typed_edges.jsonl`, etc.).
- `tests/` — pytest suite. Run via `make test-batched` for the full run; single files directly with `uv run pytest`.
- `evals/` — retrieval/gold benchmarks.
- `docs/` — `guide/` (canonical runtime docs), `architecture/FORK-BOUNDARY.md`, `build/buildv1/` (ingestion/graph-build docs), `state/` (task state ledgers), `deprecated/old-RAG/` (historical, not active steering).

## Runtime Read Path (Env v2026-04-26-additive-no-retire)

| Mode | `LIA_CORPUS_SOURCE` | `LIA_GRAPH_MODE` | Where chunks come from | Where graph traversal runs |
|---|---|---|---|---|
| `npm run dev` | `artifacts` | `artifacts` | filesystem artifacts | local docker FalkorDB (parity only) |
| `npm run dev:staging` | `supabase` | `falkor_live` | cloud Supabase (`hybrid_search` RPC) | cloud FalkorDB (`LIA_REGULATORY_GRAPH`) |
| `npm run dev:production` | inherits Railway env | inherits Railway env | mirrors staging | mirrors staging |

Every `PipelineCResponse.diagnostics` carries `retrieval_backend` and `graph_backend` — use them to confirm which adapters served a turn. If staging ever returns `retrieval_backend=artifacts`, the launcher flags drifted.

Additional retrieval-tuning flags the launcher defaults to ON across all three modes (shell override still wins): `LIA_LLM_POLISH_ENABLED=1`, `LIA_RERANKER_MODE=live` (flipped from `shadow` on 2026-04-22 — internal-beta risk-forward; adapter falls back to hybrid when `LIA_RERANKER_ENDPOINT` is unset), `LIA_QUERY_DECOMPOSE=on` (multi-`¿…?` fan-out), `LIA_SUBTOPIC_BOOST_FACTOR=1.5`, **`LIA_TEMA_FIRST_RETRIEVAL=on` (re-flipped 2026-04-25 — see `docs/aa_next/gate_9_threshold_decision.md` + `docs/aa_next/next_done.md`)**, **`LIA_EVIDENCE_COHERENCE_GATE=enforce` (flipped 2026-04-25 — operator's "no off flags" directive)**, **`LIA_POLICY_CITATION_ALLOWLIST=enforce` (flipped 2026-04-25 — same directive)**, **`LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE=enforce` (default 2026-04-25 — next_v3 §7 path-veto + 6 mutex rules)**. Ingest-pipeline knobs: `LIA_INGEST_CLASSIFIER_WORKERS=4` (held at 4 until `TokenBudget` primitive ships per next_v4 §10.1), `LIA_INGEST_CLASSIFIER_RPM=300`, `LIA_SUPABASE_SINK_WORKERS=4`, `FALKORDB_QUERY_TIMEOUT_SECONDS=30`, `FALKORDB_BATCH_NODES=500`, `FALKORDB_BATCH_EDGES=1000` (phases 2a/2b/2c). Nine retrieval-diagnostic keys lifted to top-level `response.diagnostics` (phase 1). **2026-04-25 runtime-shape additions (no env flag):** conversational-memory staircase Levels 1+2 (`ConversationState.prior_topic` / `prior_subtopic` / `topic_trajectory` / `prior_secondary_topics`; classifier soft-tiebreaker on `prior_topic`) per `next_v4 §3 + §4`; `comparative_regime_chain` query mode (`config/comparative_regime_pairs.json` + `pipeline_d/answer_comparative_regime.py`) per `next_v4 §5`. Full table in `docs/orchestration/orchestration.md`; closed forward-plans archived in `docs/aa_next/next_done.md`; active backlog in `docs/aa_next/next_v4.md`.

## Hot Path (main chat)

1. `src/lia_graph/ui_server.py`
2. `src/lia_graph/pipeline_router.py`
3. `src/lia_graph/topic_router.py`
4. `src/lia_graph/pipeline_d/orchestrator.py` — reads `LIA_CORPUS_SOURCE` + `LIA_GRAPH_MODE`, dispatches
5. `src/lia_graph/pipeline_d/planner.py`
6. Retriever (one of):
   - `pipeline_d/retriever.py` — artifact BFS (dev default)
   - `pipeline_d/retriever_supabase.py` — Supabase `hybrid_search` (staging chunks half)
   - `pipeline_d/retriever_falkor.py` — cloud FalkorDB Cypher BFS (staging graph half). Errors **propagate** — never silently falls back to artifacts.
7. `pipeline_d/answer_support.py` — practical enrichment extraction
8. `pipeline_d/answer_synthesis.py` — **stable facade** for synthesis
9. `pipeline_d/answer_assembly.py` — **stable facade** for assembly

Facade implementation modules (edit the narrow one that owns the behavior):
`answer_synthesis_sections.py`, `answer_synthesis_helpers.py`, `answer_first_bubble.py`, `answer_followup.py`, `answer_inline_anchors.py`, `answer_historical_recap.py`, `answer_comparative_regime.py` (next_v4 §5 — `comparative_regime_chain` table renderer), `answer_shared.py`, `answer_policy.py`.

## Fast Decision Rule

- wrong norms or wrong workflow → planner or retriever
- right evidence but weak practical substance → `answer_support.py`
- wrong tone, shape, or visible organization → `answer_policy.py` or the `main chat` assembly/synthesis modules
- runtime wiring change → `orchestrator.py` (and only then)
- dev ≠ staging → check `response.diagnostics.retrieval_backend` / `graph_backend`, then `scripts/dev-launcher.mjs` + the env matrix in `docs/orchestration/orchestration.md`
- `Normativa` / `Interpretación` UX work → their own packages (`src/lia_graph/normativa/`, `src/lia_graph/interpretacion/`). **Never** route their requirements into `main chat` assembly.

## Surface Boundaries

`main chat`, `Normativa`, and future `Interpretación` are **distinct surfaces** with parallel orchestration/synthesis/assembly modules. Shared graph/evidence utilities may stay shared; visible assembly must stay surface-specific. `answer_synthesis.py` / `answer_assembly.py` are not the backend for the Normativa modal.

## Non-Negotiables

- Keep docs, code, and the `/orchestration` HTML map (`frontend/src/app/orchestration/shell.ts`, `frontend/src/features/orchestration/orchestrationApp.ts`) aligned.
- Prefer focused module edits over monolithic rewrites. Make changes in the narrowest module that owns the behavior.
- If architecture changes, update `docs/orchestration/orchestration.md` (including the versioned env matrix) **in the same task** as the code change.
- If a `LIA_*` env or launcher flag changes, bump the env matrix version in the orchestration guide, add a change-log row, and update the mirror tables in `docs/guide/env_guide.md`, this file, and the `/orchestration` status card.
- The Falkor adapter must keep propagating cloud outages — **no silent artifact fallback** on staging.
- **Cloud retirements are CLI-explicit only.** Once a doc lives in cloud Supabase + Falkor, removing it requires `lia-graph-artifacts --additive --allow-retirements` from a CLI typed by an operator. The GUI additive flow (`/api/ingest/additive/preview` + `/apply`) and any non-explicit CLI invocation MUST pass `allow_retirements=False` (the default). Adding to the corpus is the friendly path; deletion is the deliberate one. Out-of-sync local `knowledge_base/`, partial Dropbox sync, machine swaps and similar local-disk drift must NEVER silently retire production docs. The disk-vs-baseline `removed` bucket surfaces as a yellow diagnostic in the preview, not as a delete action. Enforced at `src/lia_graph/ingestion/delta_runtime.py::materialize_delta` (parameter `allow_retirements`, defaults to False; strips `delta.removed` to `()` before sink + Falkor when False).
- `PipelineCResponse.diagnostics` must always carry `retrieval_backend` and `graph_backend`.
- Never run the full pytest suite in one process — use `make test-batched`. The `tests/` conftest guard aborts without `LIA_BATCHED_RUNNER=1`.
- Do not inherit old-RAG assumptions (indexing, tagging, vocab design, reranking, chunk orchestration, cache strategy). Old-RAG docs under `docs/deprecated/` are archaeology, not active steering.
- **Idea vs. verified improvement — mandatory six-gate lifecycle for every `docs/aa_next/**` step.** RAG is complex science; "improvements" misbehave and regress all the time. Unit tests green ≠ improvement. Every pipeline change must pass all six gates in the plan doc **before any code is written**: (1) describe the good idea in one sentence; (2) plan the implementation in the narrowest module; (3) define a measurable minimum success criterion with numbers; (4) define HOW to test the criterion — including development needed, conceptualization, running environment, actors/interventions required (engineer / operator / SME / end user), and the numeric decision rule; (5) greenlight requires BOTH technical tests AND end-user validation against real data at the layer an accountant experiences; (6) refine-or-discard — if validation fails, either iterate or explicitly discard (kept in record, never silently rolled back). Status lifecycle: 💡 idea → 🛠 code landed → 🧪 verified locally → ✅ verified in target environment → ↩ regressed-discarded. When target-env verification is infeasible locally, mark 🧪 and name the specific run still needed. Full policy in `docs/aa_next/README.md`.

## Fail Fast, Fix Fast — operations canon

For any operation against real systems that touches ≥100 records (cloud promotions, batch ingests, evals, embedding backfills, scraper cascades, migrations): instrument fail-fast thresholds **before** launching, treat the first abort as **diagnosis material** (not a blocker), fix the root cause, then re-run until **stable**. Do not let cascades crawl through thousands of rows accumulating errors.

Operating rules:

1. **Instrument before launching.** Every detached job that does ≥100 ops needs a fail-fast gate: an absolute error count AND an error-rate gate (default `>50 errors OR >10% rate after 100 ops → abort`). Check **between sub-batches**, not after the whole job. Surface the threshold + current error rate in the heartbeat so the operator sees how close it is.
2. **First abort = diagnosis signal, not retry signal.** When fail-fast trips, do NOT raise the threshold, NOT add `--continue-on-error`, NOT relaunch the same code. Read the audit log, group errors by root cause (failure-pattern Counter), fix the underlying issue (data shape, code bug, missing migration, drifted contract), dry-validate the fix on the full input set, then re-launch.
3. **"Stable" means past the prior failure point with the new error count at or below the dry-run prediction.** One clean heartbeat is not stable. One clean cycle past the bad spot is.
4. **Idempotency is mandatory.** Every long-running write op must be re-runnable with no harm to already-completed work (UPSERT on natural keys, idempotency-key checks, sentinel files, deterministic run-ids). Without it, "fail fast" becomes "lose work fast."
5. **Audit logs, not just stdout.** The heartbeat must read structured per-row audit (JSONL outcome rows), not just count log lines. Categorize errors; don't lump them. The error-pattern bucket IS the diagnosis.
6. **Diagnose at the audit layer, not the symptom.** A row exception saying "DB constraint violated" means: read the failing rows, find the data shape they share, fix the producer (writer / canon / extractor) — not the constraint, not the threshold.

This is paired with the six-gate lifecycle: gates 4 (test plan) and 6 (refine-or-discard) cover this loop for pipeline changes. For ops work (ingests, promotions, evals, backfills, cascades), this section IS the lifecycle. The reference implementation is `scripts/cloud_promotion/{run.sh,heartbeat.py}` (next_v7 P1).

## Long-running Python processes — always detached + heartbeat, never ad-hoc

For **any** background Python process expected to take more than ~2 minutes (reingests, embedding backfills, subtopic-miner batches, evals, long Gemini sweeps): the operator should never have to ask for progress monitoring. Default to this pattern, applied automatically:

1. **Launch detached.** Use the `scripts/launch_phase9a*.sh` shape — `nohup` + `disown` + direct `>log 2>&1` redirects (NO `| tee` pipe; tee breaks on SIGHUP and has already crashed one run this way). The process must survive CLI close, Claude exit, and shell disconnect. Reparenting to init (`PPID=1`) is the success signal.
2. **Arm a 3-minute heartbeat** via `CronCreate` that invokes `scripts/monitoring/ingest_heartbeat.py` with the run's `--delta-id`, `--start-utc`, `--total`, and pre-run baselines. See `scripts/monitoring/README.md` for the full cron prompt template, transition logic, and kill-switches.
3. **Anchor progress to `logs/events.jsonl`**, not the `--json` summary log (which buffers until termination and is useless mid-run).
4. **Render in Bogotá AM/PM** per the time-format memory, using the markdown table shape the heartbeat script already emits.
5. **Respect phase-aware silence**: the heartbeat knows `sink_writing` and `falkor_writing` legitimately emit no per-item events. Only `classifying` should tick continuously; only there does `FRESH > 180s` signal a stall.
6. **Kill-switches** (the caller must enforce): process gone + no `cli.done` → silent death → STOP loop and surface events/log, do NOT retry. `run.failed` / `ERRORS > 0` → STOP and surface. `cli.done` → STOP and declare complete.

Do not add a new `--json`/tee/background variant when launching a long Python job; copy the launcher + heartbeat shape instead.

If there is any doubt, follow `AGENTS.md` and treat it as the repo-level operating guide.
