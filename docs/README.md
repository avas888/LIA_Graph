# LIA_Graph Docs Map

This is the active reading order for the repo.

If you are reorienting after an interruption, read these in order:

1. `docs/guide/orchestration.md` — end-to-end live runtime map + authoritative versioned env matrix + change log
2. `docs/guide/chat-response-architecture.md` — how the `main chat` answer is shaped (and the surface boundary with `Normativa` / `Interpretación`)
3. `docs/guide/env_guide.md` — run modes, env files, migration baseline, test accounts, corpus refresh
4. `docs/guide/corpus.md` — corpus layers, ingest audit gate, taxonomy operations, latest run status
5. `AGENTS.md` (root) — operating guide for AI agents (mirrors env matrix)
6. `docs/architecture/FORK-BOUNDARY.md` — what we reuse vs. rethink
7. `docs/state/STATE.md` — broader repo state tracker
8. `docs/DEPENDENCIES.md` — external services needed
9. `docs/next/decouplingv1.md` — the last active forward-looking work ledger (`ui_server.py` + `opsIngestionController.ts` graduation)

## Purpose of Each Doc

- `docs/guide/orchestration.md` — the main critical file: end-to-end runtime map, HTTP controller topology, information-architecture contracts, build-time ingestion lane (single-pass subtopic-aware classifier + sink + Falkor loader), serve-time retrieval dispatch, versioned per-mode env matrix + change log.
- `docs/guide/chat-response-architecture.md` — primary source of truth for how `main chat` answers are shaped. Stable facades (`answer_synthesis.py`, `answer_assembly.py`) vs. focused submodules; surface-boundary rules that keep `Normativa` and `Interpretación` from drifting back into `main chat` assembly; optional LLM polish (`answer_llm_polish.py`).
- `docs/guide/env_guide.md` — operational counterpart: three run modes, env files, preflight checks, seed-users workflow, squashed migration baseline, corpus refresh commands, file pointers.
- `docs/guide/corpus.md` — source-of-truth for corpus layers (source assets → canonical → reasoning inputs), audit-first admission, taxonomy operations (topic + curated subtopic, version `2026-04-21-v2`), latest run status, refresh procedure.
- `docs/architecture/FORK-BOUNDARY.md` — steering doc: what we inherit as product-shell reuse vs. what must be rethought for graph-native reasoning.
- `docs/state/STATE.md` — broader repo state tracker; the current phase picture and active fronts.
- `docs/DEPENDENCIES.md` — external services required to run the repo autonomously.
- `docs/next/decouplingv1.md` — forward-looking executable plan for the final two oversized modules (`ui_server.py` ≈ 1847 LOC, `opsIngestionController.ts` ≈ 2377 LOC). Self-healing state ledger; update in-place during execution.

## Executed / Archival Material

These directories describe tasks already executed — read them for archaeology, don't treat them as steering:

- `docs/done/` — executed tasks: ingest v1 + v2 (maximalist), corpus Supabase cutover, SUIN harvest v1 + v2, ingestion (DIAN / MINTRABAJO / SUIN / UGPP), subtopic generation v1, curator decisions April 2026.
- `docs/state/TASK-01`…`TASK-04` — per-task state with checkpoints for the early build phases.
- `docs/build/buildV1.md` and `docs/build/buildv1/` — the original Build V1 executive plan + phase decomposition (largely materialized; read as the product rationale).
- `docs/guide/orchestration1.md` — archived older runtime snapshot, kept for comparison only.
- `docs/next/env_fixv1.md`, `docs/next/ingestfixv1-design-notes.md`, `docs/next/granularization_v1.md`, `docs/next/subtopic_generationv1.md`, `docs/next/subtopic_generationv1-contracts.md` — forward-looking planning docs whose underlying work has shipped. Kept for reference.
- `docs/quality_tests/EVALUACION-CORPUS-30-PREGUNTAS-RESPUESTAS.md` — batch evaluation output.
- `docs/deprecated/old-RAG/` — historical pre-graph-native material.

## Rule Of Thumb

- If the task is **understanding the live system**, read the guides (`docs/guide/*`).
- If the task is **changing the served runtime**, re-read `orchestration.md` and `chat-response-architecture.md` first; update them in the same diff if behavior shifts.
- If the task is **ingesting / graph-build / corpus work**, read `corpus.md` + `orchestration.md` §Lane 0 (Build-Time Ingestion).
- If the task is **env / launcher / preflight**, read `env_guide.md` + `orchestration.md` §Runtime Env Matrix.
