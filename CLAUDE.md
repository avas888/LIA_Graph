# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Quickstart for Claude-family agents working in `Lia_Graph`, a graph-native RAG product shell for Colombian accounting.

## Canonical Guidance

Read these before changing the served runtime:

1. `AGENTS.md` — canonical repo-level operating guide (layer ownership, surface boundaries, doc discipline)
2. `docs/guide/orchestration.md` — end-to-end runtime map + **authoritative** versioned env/flag matrix + change log
3. `docs/guide/chat-response-architecture.md` — companion source of truth for how the `main chat` answer is shaped
4. `docs/guide/env_guide.md` — operational counterpart: run modes, env files, squashed migration baseline, test accounts, corpus refresh

If code and docs disagree, reconcile to `docs/guide/orchestration.md` — never the other way around.

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

## Runtime Read Path (Env v2026-04-22-ac1)

| Mode | `LIA_CORPUS_SOURCE` | `LIA_GRAPH_MODE` | Where chunks come from | Where graph traversal runs |
|---|---|---|---|---|
| `npm run dev` | `artifacts` | `artifacts` | filesystem artifacts | local docker FalkorDB (parity only) |
| `npm run dev:staging` | `supabase` | `falkor_live` | cloud Supabase (`hybrid_search` RPC) | cloud FalkorDB (`LIA_REGULATORY_GRAPH`) |
| `npm run dev:production` | inherits Railway env | inherits Railway env | mirrors staging | mirrors staging |

Every `PipelineCResponse.diagnostics` carries `retrieval_backend` and `graph_backend` — use them to confirm which adapters served a turn. If staging ever returns `retrieval_backend=artifacts`, the launcher flags drifted.

Additional retrieval-tuning flags the launcher defaults to ON across all three modes (shell override still wins): `LIA_LLM_POLISH_ENABLED=1`, `LIA_RERANKER_MODE=live` (flipped from `shadow` on 2026-04-22 — internal-beta risk-forward; adapter falls back to hybrid when `LIA_RERANKER_ENDPOINT` is unset), `LIA_QUERY_DECOMPOSE=on` (multi-`¿…?` fan-out), `LIA_SUBTOPIC_BOOST_FACTOR=1.5`. Full table in `docs/guide/orchestration.md`.

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
`answer_synthesis_sections.py`, `answer_synthesis_helpers.py`, `answer_first_bubble.py`, `answer_inline_anchors.py`, `answer_historical_recap.py`, `answer_shared.py`, `answer_policy.py`.

## Fast Decision Rule

- wrong norms or wrong workflow → planner or retriever
- right evidence but weak practical substance → `answer_support.py`
- wrong tone, shape, or visible organization → `answer_policy.py` or the `main chat` assembly/synthesis modules
- runtime wiring change → `orchestrator.py` (and only then)
- dev ≠ staging → check `response.diagnostics.retrieval_backend` / `graph_backend`, then `scripts/dev-launcher.mjs` + the env matrix in `docs/guide/orchestration.md`
- `Normativa` / `Interpretación` UX work → their own packages (`src/lia_graph/normativa/`, `src/lia_graph/interpretacion/`). **Never** route their requirements into `main chat` assembly.

## Surface Boundaries

`main chat`, `Normativa`, and future `Interpretación` are **distinct surfaces** with parallel orchestration/synthesis/assembly modules. Shared graph/evidence utilities may stay shared; visible assembly must stay surface-specific. `answer_synthesis.py` / `answer_assembly.py` are not the backend for the Normativa modal.

## Non-Negotiables

- Keep docs, code, and the `/orchestration` HTML map (`frontend/src/app/orchestration/shell.ts`, `frontend/src/features/orchestration/orchestrationApp.ts`) aligned.
- Prefer focused module edits over monolithic rewrites. Make changes in the narrowest module that owns the behavior.
- If architecture changes, update `docs/guide/orchestration.md` (including the versioned env matrix) **in the same task** as the code change.
- If a `LIA_*` env or launcher flag changes, bump the env matrix version in the orchestration guide, add a change-log row, and update the mirror tables in `docs/guide/env_guide.md`, this file, and the `/orchestration` status card.
- The Falkor adapter must keep propagating cloud outages — **no silent artifact fallback** on staging.
- `PipelineCResponse.diagnostics` must always carry `retrieval_backend` and `graph_backend`.
- Never run the full pytest suite in one process — use `make test-batched`. The `tests/` conftest guard aborts without `LIA_BATCHED_RUNNER=1`.
- Do not inherit old-RAG assumptions (indexing, tagging, vocab design, reranking, chunk orchestration, cache strategy). Old-RAG docs under `docs/deprecated/` are archaeology, not active steering.

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
