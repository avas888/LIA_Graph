# LIA_Graph — Master State

> **Last updated**: 2026-04-15T21:50:00-04:00
> **Active program**: Build V1
> **Current phase**: 3 — Graph Planner, Retrieval, and Productization
> **Status**: IN_PROGRESS

## Current Truth

LIA_Graph is no longer at repository bootstrap.

The active product path already exists and is usable:

- `ui_server.py`
- `pipeline_router.py`
- `pipeline_d`
- local graph artifacts on disk
- public GUI on `/public`

The canonical state docs for this effort are now:

- `docs/build/buildv1/NEXT.md`
- `docs/build/buildv1/STATE.md`
- `docs/guide/orchestration.md`

If those files disagree with pre-Build-V1 notes, trust the Build V1 package.

## Steering Rules

- Shared corpus, shared graph knowledge layer
- Tenant separation applies to runtime, permissions, sessions, and history
- Practical, interpretive, and normative evidence families must all remain visible
- The served chat route is `pipeline_d`
- The visible answer must be practical-first and free of system meta-thinking
- The `/orchestration` page must depict the current runtime only

## Active Parallel Fronts

### 1. Retrieval precision

- historical and vigencia-aware retrieval is live
- exact temporal precision and duplicate article-version handling still need work

### 2. Practical accountant workflows

- the first natural-language refund workflow is green
- more workflows still need the same treatment

### 3. Published answer quality

- practical-first, no-meta answer formatting is live
- richer procedure detail and stronger support-doc extraction still need work

### 4. GUI and managed surfaces

- public ask/get-answer path is green
- richer evidence, history, and admin surfaces are still partial

### 5. Orchestration docs and HTML parity

- guide and `/orchestration` now match the live runtime
- that parity must be maintained as the runtime evolves

### 6. Dev/staging and health coverage

- dev and staging launchers exist and are useful
- fast health tests are green
- deeper staging smoke and broader E2E coverage remain open

## Healthy Right Now

- graph validation is green
- `pipeline_d` is the served default
- `/public` can ask/get-answer against the current corpus
- historical ET and practical refund examples work

## Primary Pointers

Start here when resuming:

1. `docs/build/buildv1/NEXT.md`
2. `docs/build/buildv1/STATE.md`
3. `docs/guide/orchestration.md`

Then inspect:

- `src/lia_graph/pipeline_d/planner.py`
- `src/lia_graph/pipeline_d/retriever.py`
- `src/lia_graph/pipeline_d/orchestrator.py`

## Notes

- Some repo notes predate the active execution map, but they are no longer the active execution map.
- Build V1 is the live planning package now.
