# Environment Guide

> **Env matrix version: `v2026-04-26-additive-no-retire`.**
> This file is the operational short view. The authoritative per-mode matrix + change log lives in [`docs/orchestration/orchestration.md`](./orchestration.md#runtime-env-matrix-versioned). If the tables disagree, the orchestration guide wins — reconcile this file to match.
>
> **2026-04-25 cumulative ship state (next_v3 close + next_v4 §3/§4/§5):**
> - **All "no off flags" promotions in effect.** `LIA_TEMA_FIRST_RETRIEVAL=on`, `LIA_EVIDENCE_COHERENCE_GATE=enforce`, `LIA_POLICY_CITATION_ALLOWLIST=enforce`, `LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE=enforce`, `LIA_RERANKER_MODE=live`, `LIA_QUERY_DECOMPOSE=on`, `LIA_LLM_POLISH_ENABLED=1` — all three modes.
> - **Conversational-memory staircase Levels 1+2 (next_v4 §3 + §4).** No env flag. FE forwards `payload.topic` from prior assistant turn; `ConversationState` carries `prior_topic` / `prior_subtopic` / `topic_trajectory` / `prior_secondary_topics`; `resolve_chat_topic` consumes `conversation_state` as a soft tiebreaker.
> - **`comparative_regime_chain` query mode (next_v4 §5).** No env flag. New planner mode + `config/comparative_regime_pairs.json` + `pipeline_d/answer_comparative_regime.py`.
> - **v6 additions (2026-04-24, see `docs/done/next/ingestion_tunningv2.md`):**
>   - **Runtime flags.** `LIA_EVIDENCE_COHERENCE_GATE={off|shadow|enforce}` default `enforce` (phase 3 — catches contamination the misalignment detector misses; flipped `shadow → enforce` 2026-04-25). `LIA_POLICY_CITATION_ALLOWLIST={off|enforce}` default `enforce` (phase 4 — per-topic defensive citation filter; flipped `off → enforce` 2026-04-25).
>   - **Ingest-pipeline flags** (apply at `python -m lia_graph.ingest` time). `LIA_INGEST_CLASSIFIER_WORKERS` default 4 (phase 2a parallel classifier pool; held at 4 until `TokenBudget` primitive ships). `LIA_INGEST_CLASSIFIER_RPM` default **bumped 60→300** (phase 2a). `LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE` default `enforce` (next_v3 §7 — taxonomy-aware classifier prompt + K2 path-veto). `LIA_SUPABASE_SINK_WORKERS` default 4 (phase 2b parallel sink). `FALKORDB_QUERY_TIMEOUT_SECONDS` default 30 (phase 2c — per-query server-side TIMEOUT + client socket read timeout). `FALKORDB_BATCH_NODES` default 500. `FALKORDB_BATCH_EDGES` default 1000.
>   - **Diagnostic surface.** Nine retrieval-diagnostic keys lifted to top level of `response.diagnostics` (phase 1). Always present; `None` when the retriever path doesn't populate them.

## Purpose

This guide defines the three run modes of `Lia_Graph`, the env files they load, the workflow for seeding users, the corpus refresh that primes the cloud retriever, and the migration baseline. It is the operational counterpart to `docs/orchestration/orchestration.md`.

## Run Modes

| Command | App | Supabase | FalkorDB | Env files loaded | Retrieval read path (v2026-04-18) |
|---|---|---|---|---|---|
| `npm run dev` | local | local docker (`127.0.0.1:54321`) | local docker (`127.0.0.1:6389`) | `.env`, `.env.local`, `.env.dev.local` | artifacts + local Falkor (parity only) |
| `npm run dev:staging` | local | cloud (`utjndyxgfhkfcrjmtdqz`) | cloud Falkor | `.env`, `.env.local`, `.env.staging` | cloud Supabase `hybrid_search` + cloud Falkor live BFS |
| `npm run dev:production` | Railway | cloud | cloud | n/a — exits locally | inherits staging via Railway env |

Launcher source: `scripts/dev-launcher.mjs`.

Rules:

- `dev` is fully local. No cloud traffic. Safe to run without internet.
- `dev:staging` is a local app against shared cloud infra. Any DML (password reset, user updates, retrieval) hits production-adjacent data.
- `dev:production` is not a local run mode. Production executes on Railway. The script prints a notice and exits code 2.

Storage backend is `supabase` in every mode (the `filesystem` backend has been removed — auth requires Supabase).

## Runtime Retrieval Flags (v2026-04-26-additive-no-retire)

`scripts/dev-launcher.mjs` sets these flags per mode; the orchestrator and downstream modules read them on every request:

| Flag | `dev` | `dev:staging` | `dev:production` | Consumer |
|---|---|---|---|---|
| `LIA_CORPUS_SOURCE` | `artifacts` | `supabase` | inherits Railway | `retriever.py` vs `retriever_supabase.py` |
| `LIA_GRAPH_MODE` | `artifacts` | `falkor_live` | inherits Railway | `retriever.py` vs `retriever_falkor.py` |
| `LIA_LLM_POLISH_ENABLED` | `1` | `1` | `1` | `answer_llm_polish.py` — set to `0` to compare template vs polished |
| `LIA_SUBTOPIC_BOOST_FACTOR` | `1.5` default (unused in dev) | `1.5` default | inherits Railway | `retriever_supabase.py` + `retriever_falkor.py` when planner detects subtopic intent |
| `LIA_RERANKER_MODE` | **`live`** | **`live`** | **`live`** | `pipeline_d/reranker.py` — all modes flipped `live` on 2026-04-22 (internal-beta risk-forward). Adapter falls back to hybrid when `LIA_RERANKER_ENDPOINT` is unset; served answers unchanged until the sidecar lands. |
| `LIA_QUERY_DECOMPOSE` | **`on`** | **`on`** | **`on`** | `pipeline_d/query_decomposer.py` — multi-`¿…?` queries fan out per sub-question; evidence merges at synthesis. |
| `LIA_TEMA_FIRST_RETRIEVAL` | **`on`** | **`on`** | **`on`** | `pipeline_d/retriever_falkor.py` — **re-flipped `shadow` → `on` 2026-04-25** after taxonomy v2 + K2 path-veto + SME 30Q at 30/30 + qualitative-pass on §8.4 gate 9 (`docs/aa_next/gate_9_threshold_decision.md`). The 2026-04-24 contamination regression is no longer reproducible (Q11/Q16/Q22/Q27 are 4/4 clean in v10 A/B). |
| `LIA_EVIDENCE_COHERENCE_GATE` | **`enforce`** | **`enforce`** | **`enforce`** | `pipeline_d/_coherence_gate.py` — defensive refusal gate. **Flipped `shadow → enforce` 2026-04-25** per operator's "no off flags" directive. ~3% refusal rate; revert to `shadow` if regressions surface. |
| `LIA_POLICY_CITATION_ALLOWLIST` | **`enforce`** | **`enforce`** | **`enforce`** | `pipeline_d/_citation_allowlist.py` — per-topic defensive citation filter. **Flipped `off → enforce` 2026-04-25** per operator's "no off flags" directive. Higher-risk flip (not end-to-end verified per the original six-gate policy); risk-forward internal-beta posture accepts the trade-off. |
| `LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE` | **`enforce`** | **`enforce`** | **`enforce`** | `ingestion_classifier.py` — taxonomy-aware classifier prompt + 6 mutex rules + K2 path-veto. Affects ingest only; runtime ignores it. |
| `LIA_RERANKER_ENDPOINT` | unset | unset | unset | `pipeline_d/reranker.py` — base URL of the bge-reranker-v2-m3 sidecar (`POST {url}/rerank`). Unset until the sidecar is deployed. |
| `LIA_FALKOR_MIN_NODES` | unset (smoke skipped) | `500` default | required | `dependency_smoke.py` — boots-block when cloud graph is empty |

Every chat response carries the active values under `response.diagnostics.retrieval_backend`, `response.diagnostics.graph_backend`, and — when the planner detects a curated subtopic — `response.diagnostics.retrieval_sub_topic_intent` + `response.diagnostics.subtopic_anchor_keys`. If staging ever returns `retrieval_backend=artifacts`, the launcher flags drifted — fix the env before shipping.

Full table with every `LIA_*` env, owners, and version history lives in [`docs/orchestration/orchestration.md`](./orchestration.md#runtime-env-matrix-versioned).

## Env Files

- **`.env.local`** — personal baseline. Per developer, gitignored. Live secrets (Gemini API key, anything else you don't want to commit) live here.
- **`.env.dev.local`** — local Supabase URL and well-known demo keys, plus local Falkor URL. Loaded for `dev`. Checked in; safe to commit because the keys are the same across every Supabase CLI install.
- **`.env.staging`** — cloud Supabase URL, cloud Falkor URL, service-role key, and optional `LIA_FALKOR_MIN_NODES` override. Loaded for `dev:staging`. Checked in so staging doesn't silently inherit whatever a developer put in `.env.local`.

Later files override earlier ones, but `GEMINI_API_KEY` is intentionally absent from the mode-specific files, so `.env.local` always wins for it. The launcher also hardcodes safe local fallbacks in `buildRuntimeEnv`, so `npm run dev` still boots if `.env.dev.local` is accidentally deleted.

`LIA_CORPUS_SOURCE` and `LIA_GRAPH_MODE` should NOT be committed in `.env.staging` or `.env.local` — the launcher sets them deterministically per mode so the values stay tied to the run command, not to a developer's shell.

## Preflight (v2026-04-18)

Each mode runs `scripts/dev-launcher.mjs` → `src/lia_graph/dependency_smoke.py` before starting the server. The checks are mode-aware:

| Check | `dev` | `dev:staging` | `dev:production` | Source |
|---|---|---|---|---|
| Local Falkor docker up | yes (auto-starts `lia-graph-falkor-dev`) | n/a | n/a | `ensureLocalFalkorDocker` |
| Local Supabase Kong gateway on `127.0.0.1:54321` | yes (hint-on-miss) | n/a | n/a | `ensureLocalSupabaseStack` |
| FalkorDB PING + GRAPH.LIST | yes | yes | yes | `_check_falkordb` |
| FalkorDB node count ≥ `LIA_FALKOR_MIN_NODES` | skipped (flag unset) | **required** (default 500; because `LIA_GRAPH_MODE=falkor_live`) | required | `_check_falkordb` runs `MATCH (n) RETURN count(n)` against `FALKORDB_GRAPH` |
| Supabase PostgREST reachability + key acceptance | yes | yes | yes | `_check_supabase` |
| Gemini embedding endpoint probe | yes | yes | yes | `_check_gemini` |
| Required artifacts present in `artifacts/` | yes | yes | yes | `ensureArtifactsExist` |

If `dev:staging` preflight fails on the node-count gate, run `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` against the staging env first — see [Corpus Refresh](#corpus-refresh).

## Test Accounts

All 11 `@lia.dev` users share the password `Test123!` in both local and cloud Supabase:

| Email | Role | Tenant |
|---|---|---|
| `admin@lia.dev` | `platform_admin` | `tenant-dev` |
| `usuario1@lia.dev` | `tenant_user` | `tenant-alfa` |
| `usuario2@lia.dev` | `tenant_user` | `tenant-beta` |
| `usuario3@lia.dev` | `tenant_user` | `tenant-gamma` |
| `usuario4@lia.dev` | `tenant_user` | `tenant-alfa` |
| `usuario5@lia.dev` | `tenant_user` | `tenant-beta` |
| `usuario6@lia.dev` | `tenant_user` | `tenant-gamma` |
| `usuario7@lia.dev` … `usuario10@lia.dev` | `tenant_user` | `tenant-dev` |

### Reseeding passwords

`scripts/seed_local_passwords.py` resets every `@lia.dev` row to `Test123!` using the `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` found in the environment. It targets whichever Supabase those variables point at, so the same script works for local or cloud:

```
# Local
set -a && source .env.dev.local && set +a
PYTHONPATH=src:. uv run python scripts/seed_local_passwords.py

# Cloud (staging)
set -a && source .env.staging && set +a
PYTHONPATH=src:. uv run python scripts/seed_local_passwords.py
```

Pass `--password <value>` to override.

## Migrations — Squashed Baseline

As of 2026-04-17, the 45 pre-existing migrations under `supabase/migrations/` were squashed into:

- `supabase/migrations/20260417000000_baseline.sql` — full schema dump of the local `public` schema at head, with the required `vector`, `unaccent`, and `pg_trgm` extensions prepended.
- `supabase/migrations/20260417000001_seed_users.sql` — consolidated from the three prior seed migrations.

Since the baseline, the following migrations apply on top:

- `supabase/migrations/20260418000000_normative_edges_unique.sql` — adds the `normative_edges_idempotency` unique index keyed on `(source_key, target_key, relation, generation_id)`. Required before `SupabaseCorpusSink.write_normative_edges` can upsert without tripping the `normative_edges_relation_check` constraint.

The pre-squash files live in `supabase/migrations/_archive/` for historical reference. Do not move them back; the CLI would apply them twice against a fresh DB.

### Workflow

- **Fresh local DB:** `supabase db reset`. Plays the two baseline files plus `20260418000000_normative_edges_unique.sql`, then run `scripts/seed_local_passwords.py`.
- **New schema change:** add a new migration file dated after `20260418000000`. Do not edit the baseline.
- **Cloud sync:** cloud (`utjndyxgfhkfcrjmtdqz`) already carries a compatible schema. Migrating its history to match the repo requires `supabase link --password <db_password>` and a `migration repair` pass. See `docs/done/next/env_fixv1.md` for the exact commands.

## Corpus Refresh

The served runtime has two possible read paths:

- **Artifact mode (default in `dev`).** The retriever reads `artifacts/canonical_corpus_manifest.json`, `artifacts/parsed_articles.jsonl`, and `artifacts/typed_edges.jsonl`. Local FalkorDB is loaded the same way it always has been. No cloud traffic is required.
- **Supabase mode (default in `dev:staging`).** The retriever reads `documents`/`document_chunks` through the `hybrid_search` RPC, and the graph traversal resolves against cloud FalkorDB (`LIA_REGULATORY_GRAPH`). Switching to this mode requires the rows to already exist in cloud Supabase, so the corpus must be refreshed before `dev:staging` can serve answers.

The refresh is additive to the usual artifact build:

```
# Fresh artifact bundle + sync rows into cloud Supabase. Writes
# documents, document_chunks, corpus_generations (one active row), and
# normative_edges; embeddings stay NULL until embedding_ops.py runs.
set -a && source .env.staging && set +a
make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production
```

Rerunning the target is safe — every write is keyed for idempotency and a
single `corpus_generations` row ends up marked `is_active=true`. The sink
never activates without a prior `write_generation()` call, so partial runs
cannot leave the cloud with two active generations.

The CLI flags on `python -m lia_graph.ingest` are:

- `--supabase-sink` / `--no-supabase-sink` — toggles the sink (also controlled by `LIA_INGEST_SUPABASE=1`).
- `--supabase-target {production,wip}` — picks which Supabase project to write to (also controlled by `LIA_INGEST_SUPABASE_TARGET`).
- `--supabase-generation-id <id>` — override the auto-generated `gen_<UTC timestamp>` tag. Useful for reruns during testing.
- `--no-supabase-activate` — write rows but leave `corpus_generations.is_active = false`. Use this when you want to stage a dry run.
- `--skip-llm` — bypass the PASO 4 subtopic classifier (fast dev-loop / CI smoke). Documents land with `subtema = null` + `requires_subtopic_review = false`. Added in `v2026-04-21-stv2b`.
- `--rate-limit-rpm N` — cap the PASO 4 classifier at N requests per minute (default `60`; Gemini Flash tolerates ~1000 if you raise it). Also controlled by `LIA_INGEST_CLASSIFIER_RPM`. Added in `v2026-04-21-stv2b`.
- `--allow-non-local-env` — bypass the `env_posture.assert_local_posture()` guard. Required when you intentionally point a "local" ingest run at cloud Supabase / cloud Falkor. Added in `v2026-04-21-stv2b`.
- `--include-suin <scope>` / `--suin-artifacts-root <path>` — merge SUIN JSONL shards before the audit pass.

Local developers do NOT need to run the sink. `npm run dev` reads from the filesystem artifact bundle and the local FalkorDB docker; the cloud sink is only required before the staging runtime cutover.

### Env Posture Guard

`src/lia_graph/env_posture.py` is invoked at the top of `python -m lia_graph.ingest` unless `--allow-non-local-env` is passed. The guard classifies `SUPABASE_URL` / `FALKORDB_URL` by host — if either points at cloud during what the launcher considers a local-mode run, it raises `EnvPostureError` and emits `env.posture.asserted` with the offending host. Prevents the silent-risk mode where a misconfigured `.env.local` would write production rows while the developer believed they were running locally.

### Single-Pass Ingest (Since `v2026-04-21-stv2b`)

The bulk ingest runs the PASO 4 LLM subtopic classifier inline between audit and sink, so `documents.subtema` + Falkor `SubTopicNode` / `HAS_SUBTOPIC` edges land in the same `make phase2-graph-artifacts-supabase` run — no separate backfill step. See `docs/orchestration/orchestration.md` §0.4 for the full module decomposition. `scripts/ingestion/backfill_subtopic.py` is now maintenance-only (default filter: `requires_subtopic_review=true OR subtema IS NULL`).

### Embedding + Promotion Auto-Chain

Embeddings are populated by `src/lia_graph/embedding_ops.py` on a follow-up pass against the same Supabase target; the sink intentionally writes `embedding = NULL` so one concern stays in one place. Two env vars chain extra work onto `POST /api/ingest/run`:

- `INGEST_AUTO_EMBED=1` — after the sink completes, `scripts/ingestion/ingest_run_full.sh` invokes `embedding_ops.py` against the just-written generation.
- `INGEST_AUTO_PROMOTE=1` — after embeddings land, re-run the pipeline with `PHASE2_SUPABASE_TARGET=production` to promote WIP → production.

Both are opt-in and propagated from the admin `POST /api/ingest/run` body (`auto_embed`, `auto_promote`), not from launcher env.

## Verification

A healthy environment matches the following:

- `docker ps` shows `lia-graph-falkor-dev` and the `supabase_*_lia-contador` stack before invoking `npm run dev`.
- `npm run dev:check` prints `Preflight passed for local mode.`
- `npm run dev:staging:check` prints `Preflight passed for staging mode.` AND the FalkorDB smoke check shows `node_count ≥ LIA_FALKOR_MIN_NODES`.
- `POST http://127.0.0.1:8787/api/auth/login` with `admin@lia.dev` / `Test123!` returns HTTP 200 and `role=platform_admin`.
- The same login succeeds against `dev:staging`.
- A probe chat turn in `dev` shows `diagnostics.retrieval_backend == "artifacts"` and `diagnostics.graph_backend == "artifacts"`.
- A probe chat turn in `dev:staging` shows `diagnostics.retrieval_backend == "supabase"` and `diagnostics.graph_backend == "falkor_live"`.
- A probe chat turn that mentions a curated subtopic (e.g. "4x1000") shows `diagnostics.retrieval_sub_topic_intent != null` and non-empty `diagnostics.subtopic_anchor_keys` in `dev:staging`.
- `npm run dev:production` exits non-zero with the Railway notice.

## File Pointers

- Launcher: `scripts/dev-launcher.mjs`
- Backend guard: `src/lia_graph/supabase_client.py` `require_supabase_backend`
- Env posture guard: `src/lia_graph/env_posture.py`
- Preflight smoke: `src/lia_graph/dependency_smoke.py`
- Password hashing: `src/lia_graph/password_auth.py`
- Seed script: `scripts/seed_local_passwords.py`
- Corpus sink: `src/lia_graph/ingestion/supabase_sink.py`
- Ingest CLI: `src/lia_graph/ingest.py`
- Single-pass subtopic classifier: `src/lia_graph/ingest_subtopic_pass.py`
- Curated taxonomy loader: `src/lia_graph/subtopic_taxonomy_loader.py`
- Supabase retriever (subtopic-aware): `src/lia_graph/pipeline_d/retriever_supabase.py`
- Falkor retriever (subtopic-aware): `src/lia_graph/pipeline_d/retriever_falkor.py`
- Optional LLM polish: `src/lia_graph/pipeline_d/answer_llm_polish.py`
- Orchestrator dispatch: `src/lia_graph/pipeline_d/orchestrator.py`
- Migrations: `supabase/migrations/` (active) and `supabase/migrations/_archive/` (historical)
- Historical execution record for the env cut: `docs/done/next/env_fixv1.md` (Completed 2026-04-17)
