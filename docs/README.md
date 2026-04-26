# LIA_Graph Docs Map

This is the active reading order for the repo.

If you are reorienting after an interruption, read these in order:

1. `docs/guide/orchestration.md` — end-to-end live runtime map + authoritative versioned env matrix + change log (currently **`v2026-04-25-comparative-regime`**)
2. `docs/guide/chat-response-architecture.md` — how the `main chat` answer is shaped (and the surface boundary with `Normativa` / `Interpretación`)
3. `docs/guide/env_guide.md` — run modes, env files, migration baseline, test accounts, corpus refresh
4. `docs/guide/corpus.md` — corpus layers, ingest audit gate, taxonomy operations, latest run status
5. `AGENTS.md` (root) — operating guide for AI agents (mirrors env matrix)
6. `docs/learnings/README.md` — distilled learnings (ingestion + retrieval + process) — **start here for non-obvious invariants**
7. `docs/aa_next/next_v4.md` — active forward plan (coherence-gate calibration diagnostic + parallel tracks + §3/§4/§5 ship-tracking)
8. `docs/aa_next/next_done.md` — digest of the closed next_v1+v2+v3 cycles (pointers to `docs/aa_next/done/` for full text)
9. `docs/aa_next/README.md` — six-gate lifecycle policy (mandatory for every change to the served runtime)
10. `docs/done/next/ingestion_tunningv2.md` — the v6 execution plan (all phases 0–6 landed 2026-04-24)
11. `docs/done/next/ingestionfix_v6.md` — RAG-quality backlog absorbed by next_v1+v2+v3 cycles (archived 2026-04-25)
12. `docs/done/next/gui_ingestion_v1.md` — canonical GUI-ingestion learnings + §13 deficiencies-vs-CLI gap analysis
13. `docs/architecture/FORK-BOUNDARY.md` — what we reuse vs. rethink
14. `docs/state/STATE.md` — broader repo state tracker
15. `docs/DEPENDENCIES.md` — external services needed

## Purpose of Each Doc

- `docs/guide/orchestration.md` — the main critical file: end-to-end runtime map, HTTP controller topology, information-architecture contracts, build-time ingestion lane (single-pass subtopic-aware classifier + sink + Falkor loader), serve-time retrieval dispatch, versioned per-mode env matrix + change log.
- `docs/guide/chat-response-architecture.md` — primary source of truth for how `main chat` answers are shaped. Stable facades (`answer_synthesis.py`, `answer_assembly.py`) vs. focused submodules; surface-boundary rules that keep `Normativa` and `Interpretación` from drifting back into `main chat` assembly; optional LLM polish (`answer_llm_polish.py`).
- `docs/guide/env_guide.md` — operational counterpart: three run modes, env files, preflight checks, seed-users workflow, squashed migration baseline, corpus refresh commands, file pointers.
- `docs/guide/corpus.md` — source-of-truth for corpus layers (source assets → canonical → reasoning inputs), audit-first admission, taxonomy operations (topic + curated subtopic, version `2026-04-21-v2`), latest run status, refresh procedure.
- `docs/architecture/FORK-BOUNDARY.md` — steering doc: what we inherit as product-shell reuse vs. what must be rethought for graph-native reasoning.
- `docs/state/STATE.md` — broader repo state tracker; the current phase picture and active fronts.
- `docs/DEPENDENCIES.md` — external services required to run the repo autonomously.
- **`docs/learnings/`** — 13 distilled learning docs across `ingestion/` (corpus completeness, parallelism + rate limits, Supabase sink parallelization, Falkor bulk load, artifact coherence), `retrieval/` (diagnostic surface, coherence gate + contamination, citation allow-list + gold alignment, quality-of-results evaluation), `process/` (investigation discipline, observability patterns, heartbeat monitoring, cloud-sink execution notes). Every rule names the incident that created it.
- **`docs/aa_next/next_v4.md`** — active forward plan after the 2026-04-25 gate-9 qualitative-pass. Items: coherence-gate calibration diagnostic (§1), carries from next_v3 (§2), conversational-memory staircase ship-tracking (§3 + §4), `comparative_regime_chain` ship-tracking (§5).
- **`docs/aa_next/next_done.md`** — digest of next_v1+v2+v3 (closed 2026-04-24/25). Each cycle's mission + what landed + where the full execution detail lives. Use this as the index into `docs/aa_next/done/`.
- **`docs/done/next/ingestionfix_v6.md`** — RAG-quality backlog (top-10 v7 items ranked across 4 lanes) whose contents were absorbed by next_v1+v2+v3 cycles. Archived 2026-04-25.
- **`docs/done/next/ingestion_tunningv2.md`** — v6 execution plan (phases 0–6 all landed 2026-04-24). Appendix D carries the execution retrospective.
- **`docs/done/next/gui_ingestion_v1.md`** — canonical GUI-ingestion doc (merged from `UI_Ingestion_learnings.md` + `deficienciesGUIingestion_v1.md`). 15-point pre-flight checklist, rescue-from-Other playbook, 15 deficiencies vs CLI path.

## Executed / Archival Material

These directories describe tasks already executed — read them for archaeology, don't treat them as steering:

- `docs/done/` — executed tasks: ingest v1 + v2 (maximalist), corpus Supabase cutover, SUIN harvest v1 + v2, ingestion (DIAN / MINTRABAJO / SUIN / UGPP), subtopic generation v1, curator decisions April 2026.
- `docs/done/state/TASK-01..04` — per-task state with checkpoints for the early build phases (TASK-03/04 archived 2026-04-25 once pipeline_d became the served default and Railway deploy moved into `DEPENDENCIES.md` as the only externally-blocked follow-up).
- `docs/build/buildV1.md` and `docs/build/buildv1/` — the original Build V1 executive plan + phase decomposition (largely materialized; read as the product rationale).
- `docs/done/guide/orchestration1.md` — archived older runtime snapshot, kept for comparison only.
- `docs/done/next/env_fixv1.md`, `docs/done/next/ingestfixv1-design-notes.md`, `docs/done/next/granularization_v1.md`, `docs/done/next/subtopic_generationv1.md`, `docs/done/next/subtopic_generationv1-contracts.md`, `docs/done/next/ingestionfix_v4.md`, `docs/done/next/ingestionfix_v5.md`, `docs/done/next/ingestionfix_v6.md` — forward-looking planning docs whose underlying work has shipped. Kept for reference.
- `docs/aa_next/done/` — closed forward-plan cycles: `next_v1/` (TEMA-first investigation), `next_v2.md` (Falkor cleanup + ingest parallelism), `next_v3.md` (taxonomy v2 + classifier rewrite + re-flip), `structural_groundtruth_v1.md` (first-principles audit). Reach via `docs/aa_next/next_done.md` digest.
- `docs/done/quality_tests/EVALUACION-CORPUS-30-PREGUNTAS-RESPUESTAS.md` — batch evaluation output.
- `docs/deprecated/old-RAG/` — historical pre-graph-native material.

## Rule Of Thumb

- If the task is **understanding the live system**, read the guides (`docs/guide/*`).
- If the task is **changing the served runtime**, re-read `orchestration.md` and `chat-response-architecture.md` first; update them in the same diff if behavior shifts.
- If the task is **ingesting / graph-build / corpus work**, read `corpus.md` + `orchestration.md` §Lane 0 (Build-Time Ingestion).
- If the task is **env / launcher / preflight**, read `env_guide.md` + `orchestration.md` §Runtime Env Matrix.
