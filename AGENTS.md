# AGENTS.md

Canonical operating guide for AI agents working in `Lia_Graph`.

> **Env matrix version: `v2026-04-25-temafirst-readdressed`.** Authoritative per-mode env table lives in [`docs/guide/orchestration.md`](./docs/guide/orchestration.md#runtime-env-matrix-versioned). If you change launcher flags or introduce a new `LIA_*` env, bump the version and update the mirror tables in `docs/guide/env_guide.md`, `CLAUDE.md`, and the `/orchestration` HTML map. (Latest bump: `v2026-04-25-temafirst-readdressed` — operator's "no off flags" directive applied. `LIA_TEMA_FIRST_RETRIEVAL` flipped `shadow → on`, `LIA_EVIDENCE_COHERENCE_GATE` flipped `shadow → enforce`, `LIA_POLICY_CITATION_ALLOWLIST` flipped `off → enforce`, `LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE` default → `enforce`. All four after taxonomy v2 + K2 path-veto + SME 30Q at 30/30 + qualitative-pass on §8.4 gate 9. See `docs/aa_next/next_done.md` (digest of closed cycles next_v1+v2+v3) + `docs/aa_next/gate_9_threshold_decision.md`. Active backlog: `docs/aa_next/next_v4.md`. Closed-cycle archive: `docs/aa_next/done/`. Learnings from this cycle: `docs/learnings/retrieval/router-llm-deferral-architecture.md`, `docs/learnings/retrieval/operates-not-defines-heuristic.md`, `docs/learnings/process/aspirational-thresholds-and-qualitative-pass.md`, `docs/learnings/ingestion/path-veto-rule-based-classifier-correction.md`.)

## Start Here

Before changing the served runtime, read these in order:

1. `docs/guide/orchestration.md` (includes the versioned env matrix + change log)
2. `docs/guide/chat-response-architecture.md`
3. `docs/guide/env_guide.md`
4. `frontend/src/app/orchestration/shell.ts`
5. `frontend/src/features/orchestration/orchestrationApp.ts`

`docs/guide/orchestration.md` is the main critical file for agents.
It is the end-to-end map of the live runtime, the information architecture, the versioned per-mode env matrix, and the boundary between shared graph logic and surface-specific orchestration.

`docs/guide/chat-response-architecture.md` is the companion source of truth for how the `main chat` answer is shaped.

If those docs and the code disagree, fix the mismatch instead of silently following whichever one you happened to read first.

## Run Modes

Three environments, configured by `scripts/dev-launcher.mjs`:

- `npm run dev` — local app, local Supabase docker, local FalkorDB docker. Fully offline. Retrieval reads artifacts from disk.
- `npm run dev:staging` — local app against cloud Supabase (`utjndyxgfhkfcrjmtdqz`) and cloud FalkorDB. Retrieval reads cloud Supabase via `hybrid_search` and walks cloud FalkorDB live (`LIA_CORPUS_SOURCE=supabase`, `LIA_GRAPH_MODE=falkor_live`).
- `npm run dev:production` — Railway-hosted. Script exits locally; deploy via `railway up`. Inherits staging's cloud wiring.

Test accounts: every `@lia.dev` user carries password `Test123!` in both local and cloud Supabase. Reseed with `scripts/seed_local_passwords.py`. Full details in `docs/guide/env_guide.md`.

Migrations baseline: `20260417000000_baseline.sql` + `20260417000001_seed_users.sql`, plus `20260418000000_normative_edges_unique.sql` (idempotency index for the cloud sink). Pre-squash files live in `supabase/migrations/_archive/` for reference only — do not replay them.

## Retrieval Adapters (Env-Gated, Subtopic-Aware)

The hot path picks an adapter per request based on two env flags set by the launcher:

| Flag | `dev` | `dev:staging` / `dev:production` | Module selected |
|---|---|---|---|
| `LIA_CORPUS_SOURCE` | `artifacts` | `supabase` | `retriever.py` vs `retriever_supabase.py` |
| `LIA_GRAPH_MODE` | `artifacts` | `falkor_live` | `retriever.py` vs `retriever_falkor.py` |
| `LIA_LLM_POLISH_ENABLED` | `1` | `1` | `answer_llm_polish.py` (optional post-assembly polish) |
| `LIA_SUBTOPIC_BOOST_FACTOR` | `1.5` | `1.5` | `retriever_supabase.py` + `retriever_falkor.py` (subtopic boost) |

Since `v2026-04-21-stv2` the planner emits `GraphRetrievalPlan.sub_topic_intent` when the user message matches a curated subtopic (regex/alias index, longest-form tie-break). The Supabase retriever passes `filter_subtopic` + `subtopic_boost` to the `hybrid_search` RPC with a client-side post-rerank fallback; the Falkor retriever runs a preferential `HAS_SUBTOPIC → SubTopicNode` probe and merges those article keys with explicit anchors before traversal. Diagnostics carry `retrieval_sub_topic_intent` + `subtopic_anchor_keys`.

Rules:

- Every `PipelineCResponse.diagnostics` must carry `retrieval_backend`, `graph_backend`, and (when a subtopic fires) `retrieval_sub_topic_intent` / `subtopic_anchor_keys`. If they are missing, `orchestrator.py` regressed.
- The Falkor adapter must keep propagating errors — no silent fallback to artifacts on staging. Operators must see cloud outages.
- Do NOT hardcode `LIA_CORPUS_SOURCE` / `LIA_GRAPH_MODE` into `.env.local` or `.env.staging`. The launcher owns them so the values stay tied to the run command.
- Alias lists in `config/subtopic_taxonomy.json` are deliberately wide (semantic-expansion fuel). Do not auto-tighten them.
- Before changing a flag's default or adding a new one, bump the version in `docs/guide/orchestration.md` and update the mirror tables.

## Corpus Refresh (Required Before Staging Cutover)

The cloud Supabase retriever reads rows that the build-time sink must have populated:

- Run `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` against `.env.staging` before `dev:staging` can serve answers from cloud.
- Source: `src/lia_graph/ingestion/supabase_sink.py`. Writes `documents` (now including `subtema` + `requires_subtopic_review`) / `document_chunks` / `corpus_generations` (with exactly-one active row) / `normative_edges` / `sub_topic_taxonomy`. Leaves embeddings NULL; `embedding_ops.py` fills them on a follow-up pass.
- Since `v2026-04-21-stv2b` the ingest is **single-pass**: the PASO 4 subtopic classifier runs inline between audit and sink, and Falkor receives `SubTopicNode` + `HAS_SUBTOPIC` edges in the same invocation via `src/lia_graph/ingest_subtopic_pass.py`. No separate backfill required.
- `src/lia_graph/env_posture.py` guards against silent cloud writes from a "local" run — pass `--allow-non-local-env` on the CLI when intentional.
- `scripts/backfill_subtopic.py` is now maintenance-only (default filter: `requires_subtopic_review=true OR subtema IS NULL`); emits `SubTopicNode` + `HAS_SUBTOPIC` MERGE to Falkor per updated doc.
- `make phase2-graph-artifacts-smoke` is the 30-second canary against the committed `mini_corpus` fixture — run it before a full-corpus re-ingest.
- The refresh is additive, not a replacement — artifacts on disk stay authoritative for dev.

## Product Target

The served `main chat` should feel like:

- a senior accountant guiding another accountant
- practical-first, not citation theater
- legally grounded inline
- organized, confident, and not cluttered
- easy to tune later without hunting through a monolith

That target is the reason the runtime was reorganized.
Do not “organize for organization’s sake.” Keep the architecture easy to understand, easy to tune, and easy to port to future surfaces.

## Information Architecture In One View

The current `main chat` runtime is a chain of contracts:

1. request envelope and response knobs
2. topic routing and planner intent
3. graph retrieval and evidence bundle
4. practical enrichment extraction
5. `main chat` synthesis facade
6. `main chat` assembly facade
7. final `PipelineCResponse`

The hot path is:

1. `src/lia_graph/ui_server.py`
2. `src/lia_graph/pipeline_router.py`
3. `src/lia_graph/topic_router.py`
4. `src/lia_graph/pipeline_d/orchestrator.py` (reads `LIA_CORPUS_SOURCE` + `LIA_GRAPH_MODE` and dispatches)
5. `src/lia_graph/pipeline_d/planner.py`
6. retriever (one of the three, depending on flags):
   - `src/lia_graph/pipeline_d/retriever.py` — artifact BFS (dev default)
   - `src/lia_graph/pipeline_d/retriever_supabase.py` — Supabase `hybrid_search` + `documents` lookup (staging chunks half)
   - `src/lia_graph/pipeline_d/retriever_falkor.py` — cloud FalkorDB bounded Cypher BFS (staging graph half)
7. `src/lia_graph/pipeline_d/answer_support.py`
8. `src/lia_graph/pipeline_d/answer_synthesis.py`
9. `src/lia_graph/pipeline_d/answer_assembly.py`

## HTTP Controller Topology

`ui_server.py` owns dispatch + auth + response helpers only. Every `_handle_*` method on `LiaUIHandler` is a thin delegate to `handle_<domain>_<verb>(handler, …, *, deps)` in a sibling `ui_<domain>_controllers.py` module. Deps flow through `_<domain>_controller_deps()` helpers defined just above the class. **16 domain controllers** exist as of `v2026-04-21-stv2d` — see `docs/guide/orchestration.md` §HTTP Controller Topology for the full surface ↔ controller table. The original refactor play-by-play lives in `docs/next/granularization_v1.md` (executed task ledger).

## Stable Facades vs Implementation Detail

Treat these as the stable `main chat` entrypoints:

- `src/lia_graph/pipeline_d/answer_synthesis.py`
- `src/lia_graph/pipeline_d/answer_assembly.py`

Treat these as focused implementation modules behind those facades:

- `src/lia_graph/pipeline_d/answer_synthesis_sections.py`
- `src/lia_graph/pipeline_d/answer_synthesis_helpers.py`
- `src/lia_graph/pipeline_d/answer_first_bubble.py`
- `src/lia_graph/pipeline_d/answer_followup.py`
- `src/lia_graph/pipeline_d/answer_inline_anchors.py`
- `src/lia_graph/pipeline_d/answer_historical_recap.py`
- `src/lia_graph/pipeline_d/answer_shared.py`
- `src/lia_graph/pipeline_d/answer_policy.py`
- `src/lia_graph/pipeline_d/answer_llm_polish.py` (optional; gated by `LIA_LLM_POLISH_ENABLED`)

Best practice:

- if you are consuming `main chat` behavior, prefer the facades
- if you are changing a specific piece of `main chat` behavior, edit the narrow implementation module that owns it
- do not push new answer-shaping complexity back into `orchestrator.py`

## Layer Ownership

Use the right layer for the problem.

### Request envelope

Owns:

- `response_depth`
- `first_response_mode`
- shared defaults and allowed values

Main files:

- `src/lia_graph/chat_response_modes.py`
- `src/lia_graph/pipeline_c/contracts.py`

### Planner and retrieval intent

Owns:

- query mode
- workflow detection
- entry-point selection
- retrieval budgets
- graph search priorities

Main files:

- `src/lia_graph/pipeline_d/planner.py`
- `src/lia_graph/pipeline_d/retriever.py` (artifact path — dev default)
- `src/lia_graph/pipeline_d/retriever_supabase.py` (cloud Supabase `hybrid_search` — staging chunks half)
- `src/lia_graph/pipeline_d/retriever_falkor.py` (cloud FalkorDB Cypher BFS — staging graph half)
- `src/lia_graph/pipeline_d/retrieval_support.py`

Use this layer when the answer is grounded on the wrong norm, wrong workflow, or wrong support corpus. If the problem is "different answer between dev and staging", verify both adapters agree on the same underlying data before touching `retriever.py`.

### Practical enrichment extraction

Owns:

- support-line cleaning
- article insight extraction
- practical markers
- buckets like `procedure`, `precaution`, `strategy`, `jurisprudence`, `checklist`

Main file:

- `src/lia_graph/pipeline_d/answer_support.py`

Use this layer when the answer has relevant evidence but still feels dry, thin, or not useful enough.

### Published `main chat` policy and rendering

Owns:

- voice and structure
- workflow-specific blueprints
- first-bubble composition
- inline anchors
- historical recap
- shared section rendering

Main files:

- `src/lia_graph/pipeline_d/answer_policy.py`
- `src/lia_graph/pipeline_d/answer_synthesis.py`
- `src/lia_graph/pipeline_d/answer_synthesis_sections.py`
- `src/lia_graph/pipeline_d/answer_synthesis_helpers.py`
- `src/lia_graph/pipeline_d/answer_assembly.py`
- `src/lia_graph/pipeline_d/answer_first_bubble.py`
- `src/lia_graph/pipeline_d/answer_inline_anchors.py`
- `src/lia_graph/pipeline_d/answer_historical_recap.py`
- `src/lia_graph/pipeline_d/answer_shared.py`

Use this layer when the answer sounds wrong, is cluttered, has the wrong shape, or no longer feels like a senior accountant guiding another accountant.

### Pipeline runtime flow

Owns:

- wiring planner to retriever to synthesis to assembly
- packaging the final `PipelineCResponse`

Main file:

- `src/lia_graph/pipeline_d/orchestrator.py`

Only edit this file when the runtime flow itself changes.
Do not use it as the default place to fix visible answer quality.

## Main Chat Best Practices

When changing live chat behavior:

- start from `docs/guide/orchestration.md`, not from guesswork
- preserve the “senior accountant guiding you” target
- keep legal grounding inline with practical advice
- prefer small focused module changes over broad cross-cutting edits
- tune by workflow, evidence class, or information contract
- do not patch behavior around one single prompt unless the issue reveals a real workflow gap
- keep first-bubble UX intentional and not cluttered
- prefer declarative guidance in `answer_policy.py` when the change is about response shape or blueprint intent
- prefer `answer_synthesis_sections.py` and `answer_synthesis_helpers.py` when the issue is how evidence becomes candidate lines
- prefer `answer_first_bubble.py`, `answer_inline_anchors.py`, `answer_historical_recap.py`, and `answer_shared.py` when the issue is visible rendering

## Surface Boundaries

`main chat`, `Normativa`, and future `Interpretación` are not the same surface.

Rules:

- shared graph evidence utilities may stay shared
- visible answer assembly should stay surface-specific
- `main chat` facades are not the UI contract for `Normativa`
- do not quietly route `Normativa` UX requirements into `main chat` assembly modules
- if a new surface needs orchestration, give it its own synthesis and assembly boundary

This matters immediately for the `Normativa` port:

- preserve the old deterministic Normativa UX contract
- let graph-native enrichment plug in through a surface-specific adapter
- reuse shared retrieval and evidence contracts where they truly match
- do not make `answer_synthesis.py` or `answer_assembly.py` the hidden backend for the Normativa modal

## Documentation Discipline

If you change the runtime information architecture, update all three together in the same task:

1. `docs/guide/orchestration.md`
2. `docs/guide/chat-response-architecture.md`
3. the `/orchestration` HTML map:
   - `frontend/src/app/orchestration/shell.ts`
   - `frontend/src/features/orchestration/orchestrationApp.ts`

The docs and the architecture page should explain the same runtime truth.

If you change envs or launcher flags (anything under `LIA_*`, anything in `scripts/dev-launcher.mjs`, anything in `dependency_smoke.py` that gates preflight), you must:

1. Bump the env matrix version in `docs/guide/orchestration.md` → "Runtime Env Matrix (Versioned)".
2. Add a Change Log row with the exact files touched.
3. Update the mirror tables in `docs/guide/env_guide.md` and `CLAUDE.md`.
4. Update the status card in `frontend/src/app/orchestration/shell.ts`.

The orchestration guide's matrix is authoritative. If the mirrors disagree, reconcile them to the orchestration guide — never the other way around.

## Ingestion And Graph Build Guidance

If the task touches corpus ingestion, graph build, labeling, routing, retrieval, or FalkorDB integration, also read:

1. `docs/build/buildv1/STATE.md`
2. `docs/build/buildv1/01-target-architecture.md`
3. `docs/build/buildv1/03-phase-2-shared-regulatory-graph.md`
4. `docs/build/buildv1/appendix-d-corpus-audit-and-labeling-policy.md`
5. `docs/architecture/FORK-BOUNDARY.md`

Keep these ingestion principles in mind:

- graph structure is load-bearing
- audit the full source-asset surface before ingest
- the three corpus families are first-class
- treat source assets, canonical corpus, and reasoning graph as separate layers
- mandatory corpus metadata is more important than optional flat labels
- derive reform chains, vigencia, and normative neighborhoods from graph structure when possible
- use vocabulary as naming authority, not as the bottleneck
- use labels as retrieval hints, not as the primary substrate of legal meaning

## Before You Ship A Runtime Change

Check these before closing the task:

- the change lives in the correct layer
- no contradictory instructions were introduced
- `docs/guide/orchestration.md` still describes reality (including the versioned env matrix)
- `docs/guide/chat-response-architecture.md` still matches the live `main chat`
- the `/orchestration` page still maps the same architecture
- `Normativa` and `Interpretación` boundaries did not get blurred by convenience edits
- if a `LIA_*` env or launcher flag changed, the version was bumped and mirror tables updated
- the Falkor adapter still propagates errors (no silent artifact fallback on staging)
- `PipelineCResponse.diagnostics` still carries `retrieval_backend` and `graph_backend`

If an agent can answer “where does this behavior live?” in one minute, the architecture is probably healthy.
