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

## Runtime Read Path (Env v2026-04-18)

| Mode | `LIA_CORPUS_SOURCE` | `LIA_GRAPH_MODE` | Where chunks come from | Where graph traversal runs |
|---|---|---|---|---|
| `npm run dev` | `artifacts` | `artifacts` | filesystem artifacts | local docker FalkorDB (parity only) |
| `npm run dev:staging` | `supabase` | `falkor_live` | cloud Supabase (`hybrid_search` RPC) | cloud FalkorDB (`LIA_REGULATORY_GRAPH`) |
| `npm run dev:production` | inherits Railway env | inherits Railway env | mirrors staging | mirrors staging |

Every `PipelineCResponse.diagnostics` carries `retrieval_backend` and `graph_backend`, so you can confirm which adapters served a turn without guessing. The orchestration guide owns the authoritative version history — update it if you change what the launcher sets.

## Fast Decision Rule

Use this shortcut when deciding where to work:

- wrong norms or wrong workflow -> planner or retriever
- right evidence but weak practical substance -> `answer_support.py`
- wrong tone, shape, or visible organization -> `answer_policy.py` or the `main chat` assembly modules
- runtime wiring change -> `orchestrator.py`
- which adapter served a turn or why staging looks different from dev -> check `response.diagnostics.retrieval_backend` / `graph_backend`, then `scripts/dev-launcher.mjs` + the version table in `docs/guide/orchestration.md`

## Retrieval Adapters (Env-Gated)

- `src/lia_graph/pipeline_d/retriever.py` — artifact BFS. Active when `LIA_CORPUS_SOURCE=artifacts` AND `LIA_GRAPH_MODE=artifacts` (dev default).
- `src/lia_graph/pipeline_d/retriever_supabase.py` — cloud Supabase `hybrid_search` RPC + `documents` lookup. Active when `LIA_CORPUS_SOURCE=supabase`.
- `src/lia_graph/pipeline_d/retriever_falkor.py` — cloud FalkorDB bounded Cypher BFS. Active when `LIA_GRAPH_MODE=falkor_live`. Errors propagate — **never silently falls back to artifacts**.
- `src/lia_graph/pipeline_d/orchestrator.py` — reads the two flags, dispatches to the right adapters, and merges halves when both are cloud-live.

## Ingestion Sink (Build-Time)

- `src/lia_graph/ingestion/supabase_sink.py` — `SupabaseCorpusSink` mirrors the corpus snapshot into `documents` / `document_chunks` / `corpus_generations` / `normative_edges`. Run with `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` (or the `--supabase-sink` CLI flag on `python -m lia_graph.ingest`). Idempotent, additive, never touches embeddings.
- Required before `dev:staging` can serve answers — the Supabase retriever reads what the sink wrote.

## Non-Negotiables

- keep docs, code, and the `/orchestration` architecture page aligned
- prefer focused module edits over monolithic rewrites
- do not let `main chat` become the hidden rendering layer for `Normativa`
- if architecture changes, update `docs/guide/orchestration.md` (including the env/flag version table)
- if you flip a launcher flag or introduce a new env-driven branch, bump the env version in the orchestration guide and in this file
- the Falkor adapter must keep surfacing cloud outages — do not re-introduce silent artifact fallback

If there is any doubt, follow `AGENTS.md` and treat it as the repo-level operating guide.
