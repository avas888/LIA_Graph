# CLAUDE.md

Quickstart for Claude-family agents working in `Lia_Graph`.

## Canonical Guidance

Read these before changing the served runtime:

1. `AGENTS.md`
2. `docs/guide/orchestration.md`
3. `docs/guide/chat-response-architecture.md`
4. `docs/guide/env_guide.md`

`docs/guide/orchestration.md` is the main critical file.
It is the end-to-end runtime and information-architecture map, and it carries the authoritative per-mode env/flag versioning table.

`docs/guide/env_guide.md` is the operational counterpart — it defines the three run modes (`npm run dev`, `dev:staging`, `dev:production`), their env files, the squashed migration baseline, and the test-account + corpus-refresh workflows.

## What To Internalize First

- the product target is “a senior accountant guiding another accountant”
- `main chat` uses stable facades:
  - `src/lia_graph/pipeline_d/answer_synthesis.py`
  - `src/lia_graph/pipeline_d/answer_assembly.py`
- `orchestrator.py` is runtime flow, not the default place to fix answer quality
- `Normativa` and future `Interpretación` should get their own orchestration boundaries
- retrieval is now **mode-aware**: `dev` reads artifacts from disk, `dev:staging` reads from cloud Supabase + cloud FalkorDB. The split is gated by `LIA_CORPUS_SOURCE` and `LIA_GRAPH_MODE`, wired by `scripts/dev-launcher.mjs`

## Runtime Read Path (Env v2026-04-21-stv2d)

| Mode | `LIA_CORPUS_SOURCE` | `LIA_GRAPH_MODE` | Where chunks come from | Where graph traversal runs |
|---|---|---|---|---|
| `npm run dev` | `artifacts` | `artifacts` | filesystem artifacts | local docker FalkorDB (parity only) |
| `npm run dev:staging` | `supabase` | `falkor_live` | cloud Supabase (`hybrid_search` RPC) | cloud FalkorDB (`LIA_REGULATORY_GRAPH`) |
| `npm run dev:production` | inherits Railway env | inherits Railway env | mirrors staging | mirrors staging |

Every `PipelineCResponse.diagnostics` carries `retrieval_backend` and `graph_backend`, so you can confirm which adapters served a turn without guessing. Since `v2026-04-21-stv2`, diagnostics also carry `retrieval_sub_topic_intent` + `subtopic_anchor_keys` when the planner detected a curated subtopic — the Supabase retriever boosts matching chunks by `LIA_SUBTOPIC_BOOST_FACTOR` (default 1.5) and the Falkor retriever prefers `HAS_SUBTOPIC → SubTopicNode` anchors. Since `v2026-04-21-stv2b`, the bulk ingest runs the PASO 4 classifier inline (via `src/lia_graph/ingest_subtopic_pass.py`) and emits `SubTopicNode` + `HAS_SUBTOPIC` to Falkor in the same single pass — no separate backfill required; pass `--skip-llm` on `python -m lia_graph.ingest` for fast dev-loop / CI smoke. Since `v2026-04-21-stv2d`, the subtopic taxonomy (`config/subtopic_taxonomy.json`) holds **106 subtopics × 39 parent topics** (version `2026-04-21-v2`); the classifier honors a prefix→parent lookup (`config/prefix_parent_topic_map.json`) and drops binary/derogated files at the admission gate. Post-assembly LLM polish (`answer_llm_polish.py`) is on by default via `LIA_LLM_POLISH_ENABLED=1` and fails loudly in diagnostics, safely in output. The orchestration guide owns the authoritative version history — update it if you change what the launcher sets.

## Fast Decision Rule

Use this shortcut when deciding where to work:

- wrong norms or wrong workflow -> planner or retriever
- right evidence but weak practical substance -> `answer_support.py`
- wrong tone, shape, or visible organization -> `answer_policy.py` or the `main chat` assembly modules
- runtime wiring change -> `orchestrator.py`
- which adapter served a turn or why staging looks different from dev -> check `response.diagnostics.retrieval_backend` / `graph_backend`, then `scripts/dev-launcher.mjs` + the version table in `docs/guide/orchestration.md`

## Retrieval Adapters (Env-Gated, Subtopic-Aware)

- `src/lia_graph/pipeline_d/retriever.py` — artifact BFS. Active when `LIA_CORPUS_SOURCE=artifacts` AND `LIA_GRAPH_MODE=artifacts` (dev default).
- `src/lia_graph/pipeline_d/retriever_supabase.py` — cloud Supabase `hybrid_search` RPC + `documents` lookup. Active when `LIA_CORPUS_SOURCE=supabase`. Passes `filter_subtopic` + `subtopic_boost` when planner emits `sub_topic_intent`; client-side post-rerank fallback for older DBs.
- `src/lia_graph/pipeline_d/retriever_falkor.py` — cloud FalkorDB bounded Cypher BFS. Active when `LIA_GRAPH_MODE=falkor_live`. Runs a preferential `HAS_SUBTOPIC → SubTopicNode` probe when planner emits `sub_topic_intent`. Errors propagate — **never silently falls back to artifacts**.
- `src/lia_graph/pipeline_d/orchestrator.py` — reads the two flags, dispatches to the right adapters, and merges halves when both are cloud-live.
- `src/lia_graph/pipeline_d/answer_llm_polish.py` — optional post-assembly polish, gated by `LIA_LLM_POLISH_ENABLED=1`. Template answer is the safety net; `response.llm_runtime.skip_reason` carries why the polish skipped (one of `polish_disabled_by_env`, `no_adapter_available`, `adapter_error:<Type>`, `empty_llm_output`, `anchors_stripped`).

## Ingestion Sink (Build-Time, Single-Pass)

- `src/lia_graph/ingestion/supabase_sink.py` — `SupabaseCorpusSink` mirrors the corpus snapshot into `documents` (now with `subtema` + `requires_subtopic_review`) / `document_chunks` / `corpus_generations` / `normative_edges` / `sub_topic_taxonomy`. Run with `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` (or the `--supabase-sink` CLI flag on `python -m lia_graph.ingest`). Idempotent, additive, never touches embeddings.
- `src/lia_graph/ingest_subtopic_pass.py` — runs the PASO 4 LLM classifier over every admitted doc between audit and sink. Honors `--rate-limit-rpm` (default 60) and `--skip-llm` (fast smoke). Drops any LLM subtopic key not in `config/subtopic_taxonomy.json` (Invariant: no orphan subtemas in graph).
- `src/lia_graph/ingestion/loader.py` — emits `SubTopicNode` + `HAS_SUBTOPIC` edges to Falkor in the **same single-pass run** (Decision F1: doc-level only). No separate `sync_subtopic_edges_to_falkor.py` step.
- `src/lia_graph/env_posture.py` — `assert_local_posture()` guards the CLI; pass `--allow-non-local-env` only when cloud writes are intended.
- Required before `dev:staging` can serve answers — the Supabase retriever reads what the sink wrote.
- Canary: `make phase2-graph-artifacts-smoke` runs the 30-second integration suite against the committed `mini_corpus` fixture.

## Non-Negotiables

- keep docs, code, and the `/orchestration` architecture page aligned
- prefer focused module edits over monolithic rewrites
- do not let `main chat` become the hidden rendering layer for `Normativa`
- if architecture changes, update `docs/guide/orchestration.md` (including the env/flag version table)
- if you flip a launcher flag or introduce a new env-driven branch, bump the env version in the orchestration guide and in this file
- the Falkor adapter must keep surfacing cloud outages — do not re-introduce silent artifact fallback

If there is any doubt, follow `AGENTS.md` and treat it as the repo-level operating guide.
