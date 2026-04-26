# LIA_Graph — Master State

> **Last updated**: 2026-04-25
> **Env matrix version**: `v2026-04-25-comparative-regime` (see `docs/guide/orchestration.md`)
> **Status**: Build V1 fully materialized; pipeline_d is the served default in every mode; Railway production deploy is the only externally-blocked follow-up (see `docs/DEPENDENCIES.md` §6)

## Current Truth

LIA_Graph is past repository bootstrap. The served product path is live in two modes, and Build V1's graph-native reasoning core is the default:

- `src/lia_graph/ui_server.py` (dispatch + auth + 16 sibling `ui_*_controllers.py` for domain logic)
- `src/lia_graph/pipeline_router.py` (resolves the served route — `pipeline_d`)
- `src/lia_graph/pipeline_d/orchestrator.py` (reads `LIA_CORPUS_SOURCE` + `LIA_GRAPH_MODE`, dispatches to the right adapters)
- `src/lia_graph/pipeline_d/retriever*.py` — artifact / Supabase `hybrid_search` / Falkor Cypher BFS
- `src/lia_graph/pipeline_d/answer_synthesis.py` + `answer_assembly.py` (+ optional `answer_llm_polish.py`)
- `dev:staging` walks cloud Supabase + cloud FalkorDB live on every request
- the `/public` GUI is open for the anonymous accountant flow

The canonical reading order is now:

1. `docs/guide/orchestration.md` — authoritative live-runtime + env matrix
2. `docs/guide/chat-response-architecture.md` — visible answer shaping
3. `docs/guide/env_guide.md` — run modes, preflight, corpus refresh
4. `docs/guide/corpus.md` — corpus audit gate + taxonomy operations

If older pre-Build-V1 notes disagree with the four guides above, the guides win.

## Steering Rules

- Shared corpus, shared graph knowledge layer; tenant separation stays in runtime, permissions, sessions, history.
- Practical, interpretive, and normative evidence families remain first-class.
- The served chat route is `pipeline_d`.
- The visible answer must be practical-first and free of system meta-thinking.
- `main chat`, `Normativa`, and `Interpretación` are isolated visible surfaces — shared retrieval, separate synthesis/assembly.
- `/orchestration` must depict the current runtime only.
- The curated subtopic taxonomy (`config/subtopic_taxonomy.json`) is supportive retrieval metadata; alias lists are deliberately wide and should not be auto-tightened.

## What Is Live

- Single-pass ingest — audit + PASO 4 classifier + artifacts + Supabase sink + Falkor `SubTopicNode` / `HAS_SUBTOPIC` emit in one invocation (`v2026-04-21-stv2b`).
- Subtopic-aware retrieval — Supabase `subtopic_boost` via the `hybrid_search` RPC; Falkor preferential `HAS_SUBTOPIC` probe (`v2026-04-21-stv2`).
- Env posture guard (`src/lia_graph/env_posture.py`) — prevents silent cloud writes from a "local" run.
- Admin drag-to-ingest surface — `POST /api/ingest/intake`, 6-stage progress, embedding + promotion auto-chain (`v2026-04-20-ui15`).
- 11 of 13 previously-oversized modules have been graduated to ≤1000 LOC under the granularization campaign.
- Graph validation green: 2633 nodes / 20495 edges / ok=true.
- Optional LLM polish on by default via `LIA_LLM_POLISH_ENABLED=1`; deterministic template is the safety net.
- **2026-04-25 ship state.** All "no off flags" promotions in effect: `LIA_TEMA_FIRST_RETRIEVAL=on`, `LIA_EVIDENCE_COHERENCE_GATE=enforce`, `LIA_POLICY_CITATION_ALLOWLIST=enforce`, `LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE=enforce`, `LIA_RERANKER_MODE=live`, `LIA_QUERY_DECOMPOSE=on`. Taxonomy v2 (89 topics, 6 mutex rules) loaded; K2 path-veto active in classifier.
- **2026-04-25 conversational-memory staircase Levels 1+2** (next_v4 §3 + §4) — FE forwards `payload.topic` from prior assistant turn; `ConversationState` carries `prior_topic` / `prior_subtopic` / `topic_trajectory` / `prior_secondary_topics`; `resolve_chat_topic` accepts `conversation_state` as a soft tiebreaker. 13 unit tests green; multi-turn harness shipped (`evals/multiturn_dialogue_v1.jsonl` + `scripts/evaluations/run_multiturn_dialogue_harness.py`); staging-cloud baseline run still pending.
- **2026-04-25 `comparative_regime_chain` query mode** (next_v4 §5) — pre/post-reform comparison cues route to a side-by-side markdown table renderer (`pipeline_d/answer_comparative_regime.py` + `config/comparative_regime_pairs.json`). Initial pair: `perdidas_fiscales_2017` (147 ↔ 290 #5). Test green; SME validation on adjacent pairs (depreciación, tarifa renta) pending.

## Active Parallel Fronts

### 1. Coherence-gate calibration diagnostic (next_v4 §1)

11 enumerated `coherence_misaligned=True` questions from the v10 A/B carry as deferred debt. Diagnose-before-intervene: per-topic density audit + sample-pair inspection + gate-score distribution before any threshold tuning. Operator-scoped 2026-04-25.

### 2. Multi-turn harness verification (next_v4 §3 + §4)

Conversational-memory staircase Levels 1+2 are 🛠 code landed; staging-cloud baseline run against `evals/multiturn_dialogue_v1.jsonl` still pending to verify ≤ 5% refusal rate target.

### 3. Comparative-regime SME validation (next_v4 §5)

`comparative_regime_chain` is 🧪 verified locally; SME pass on the binding `perdidas_fiscales_2017` case + adjacent pairs (depreciación, tarifa renta) pending. Pair config is one-entry — adding more is config-only once SME validates the structure.

### 4. Final two LOC graduations

`src/lia_graph/ui_server.py` and `frontend/src/features/ops/opsIngestionController.ts` are the last two files above the informal 1000-LOC threshold. Plan: `docs/done/decouplingv1.md` (closed cycle).

### 5. Railway production deploy

`npm run dev:production` exits with a Railway notice; the Railway project link is the remaining externally-blocked follow-up (see `docs/DEPENDENCIES.md` §6).

### 6. Retrieval precision

Historical and vigencia-aware retrieval is live; tuning the breadth of subtopic aliases and the Falkor traversal edge-preferences is ongoing maintenance, not a phase.

### 7. Practical accountant workflows

Refund, correction-firmness, loss-compensation, tax-planning / abuse / simulation, comparative-regime shapes are wired; coverage widens per new workflow via `answer_policy.py` blueprints.

### 8. Admin + managed surfaces

Sesiones (Lia_Graph-native rewire), Sub-temas curation board, 6-stage progress timeline, and log tail are live; richer history and eval coverage are incremental.

## Healthy Right Now

- Graph validation green.
- `pipeline_d` is the served default in every mode.
- Both preflights (`npm run dev:check`, `npm run dev:staging:check`) green.
- Login with `admin@lia.dev / Test123!` works on both local and cloud Supabase.
- `/public` end-to-end is live.
- Every chat response carries `retrieval_backend` + `graph_backend` + (when applicable) `retrieval_sub_topic_intent` + `subtopic_anchor_keys` in diagnostics.

## Primary Pointers

Start here when resuming:

1. `docs/guide/orchestration.md`
2. `docs/guide/chat-response-architecture.md`
3. `docs/guide/env_guide.md`

Then inspect:

- `src/lia_graph/pipeline_d/orchestrator.py`
- `src/lia_graph/pipeline_d/planner.py` + `planner_query_modes.py`
- `src/lia_graph/pipeline_d/retriever{,_supabase,_falkor}.py`
- `src/lia_graph/ingest.py` + `ingest_subtopic_pass.py`

## Historical Bridge

- `docs/build/buildV1.md` + `docs/build/buildv1/` — original plan, largely materialized; useful for product rationale.
- `docs/done/state/TASK-01..04` — per-task ledgers for the bootstrap phases (all done; TASK-03/04 archived 2026-04-25 once pipeline_d became the served default).
- `docs/done/next/env_fixv1.md`, `ingestfixv1-design-notes.md`, `granularization_v1.md`, `subtopic_generationv1.md`, `subtopic_generationv1-contracts.md`, `ingestionfix_v4.md`, `ingestionfix_v5.md`, `ingestionfix_v6.md` — forward-looking docs whose underlying work has shipped.
- `docs/aa_next/done/` — closed forward-plan cycles (next_v1, next_v2, next_v3, structural_groundtruth_v1). Reach via `docs/aa_next/next_done.md` digest.
- `docs/done/` — executed task records.
