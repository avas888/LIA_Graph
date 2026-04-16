# Build V1 — Master State

> **Last updated**: 2026-04-16T00:01:09-04:00
> **Program**: Purpose-led Shared-Corpus Graph Runtime for LIA
> **Status**: PHASE_3_IN_PROGRESS
> **Current phase**: 3 — Graph Planner, Retrieval, and Productization
> **Next action**: Harden the first visible accountant answer by advancing retrieval precision, practical workflows, and published answer quality together

## Current Snapshot

- Phases 1 and 2 are complete enough to support the live product path.
- Phase 3 is live and user-testable in the GUI.
- `pipeline_router` now defaults to `pipeline_d`.
- The served answer path is graph-first and artifact-backed.
- The public GUI on `/public` can ask a question and receive a real corpus-backed answer.
- The published answer contract is now practical-first and hides planner/retrieval/meta-thinking from the visible reply.
- The orchestration markdown guide now covers the current runtime plus the build-time ingestion path that feeds it, while the `/orchestration` HTML page remains focused on the served runtime.
- Supabase is runtime persistence, not the live retrieval engine.
- Falkor is environment parity / graph ops, not the live per-request answer source.
- The local corpus snapshot now mirrors the Dropbox source state after the editorial revision tranche was merged into base docs and archived under `deprecated/`, with shared-path labels in parity with source.

## Corpus and Graph Health

- Active local corpus root: `/Users/ava-sensas/Developer/Lia_Graph/knowledge_base`
- Preserved working snapshot outside repo:
  - `/Users/ava-sensas/Library/CloudStorage/Dropbox/AAA_LOGGRO Ongoing/AI/LIA_contadores/Lia_Graph_Working_Snapshots/knowledge_base_snapshot_2026-04-15_19-01-13`
- Taxonomy state:
  - `taxonomy_version = draft_v1_2026_04_15c`
  - Dropbox audited source files under `CORE ya Arriba` + `to upload`: `1398`
  - local snapshot files copied into `knowledge_base`: `1319`
  - source files intentionally left unsynced by snapshot filter: `79`, all classified as `exclude_internal`
  - shared-path audit mismatches between Dropbox and `knowledge_base`: `0`
  - `include_corpus = 1246`
  - `revision_candidate = 0`
  - `exclude_internal = 73`
  - `canonical_ready_count = 1246`
  - `review_required_count = 0`
  - `documents_with_pending_revisions = 0`
  - `unresolved_revision_candidate_count = 0`
  - `manual_review_queue_count = 0`
  - the prior 18 patch/upsert/errata files were merged into their 17 base docs in Dropbox source and then archived under `deprecated/`; the admitted corpus has no label mismatches or vocabulary-unassigned rows
- Graph validation state:
  - `artifacts/graph_validation_report.json -> ok = true`
  - `node_count = 2617`
  - `edge_count = 20345`
- Falkor parity:
  - local Docker Falkor: green
  - cloud Falkor baseline: green

## Active Parallel Fronts

### 1. Retrieval Precision and Historical Fidelity

**Status:** first-response hardening active

- `temporal_context` exists and historical questions route into `historical_reform_chain`
- reform-year false positives are fixed
- procedural `antes de ...` phrasing no longer needs to imply historical mode
- remaining work:
  - exact `effective_date` / vigencia use
  - duplicate/versioned `article_key` disambiguation
  - cleaner historical connected-article ranking
  - explicit as-of-date tests

### 2. Practical Accountant Workflows

**Status:** first lane green, broader first-response rollout active

- the first natural-language refund / saldo a favor workflow now works without lawyer-style prompts
- router and planner now treat practical accountant language as a valid retrieval entry path
- mixed correction / firmeza / devolución prompts now seed dedicated planner searches instead of relying only on the refund lane
- remaining work:
  - extend the same treatment to more workflows
  - improve topic-specific practical/interpretive support selection

### 3. Published Answer Quality

**Status:** new answer contract live, first-response enrichment active

- visible reply now follows a strict practical-first structure
- visible reply now hides system meta-thinking
- support-document insights can now feed:
  - procedure
  - supporting documents / working papers
  - context
  - precautions
- primary article excerpts now also feed the first answer when they contain useful operational facts
- remaining work:
  - richer procedure detail by topic
  - stronger practical line selection from support docs

### 4. GUI and Managed Chat Surfaces

**Status:** core chat path green, managed layer partial

- `/public` ask/get-answer flow is live again
- `?message=...` public handoff works again
- public chat mounts correctly and can hit the real runtime
- remaining work:
  - evidence drill-down
  - saved-history / managed-chat surfaces
  - some admin and secondary surfaces

### 5. Orchestration Docs and HTML Parity

**Status:** freshly realigned

- `docs/guide/orchestration.md` now documents the current runtime plus the raw-corpus ingestion lane that produces its artifacts
- `frontend/src/features/orchestration/graph/pipelineGraph.ts` still renders the current served runtime only
- orchestration frontend test now guards the live-route depiction from drifting
- remaining work:
  - keep docs + HTML + runtime synchronized whenever the product path changes

### 6. Dev / Staging Runtime and Automated Health

**Status:** useful baseline in place

- `npm run dev`, `npm run dev:check`, `npm run dev:staging`, and `npm run dev:staging:check` exist
- frontend fast health suite is green
- browser E2E infrastructure exists
- remaining work:
  - deeper staging smoke
  - broader end-to-end coverage as richer surfaces return

## What Is Healthy Right Now

- `pipeline_d` is the served default
- `/api/chat` and `/public` both reach the same graph-native runtime
- graph-native answers are working for current-corpus accountant questions
- the historical ET slice is live
- the first practical refund lane is live
- the orchestration page is now truthful to the current runtime
- the full local corpus snapshot is now parity-checked against Dropbox for all admitted docs and attached revision candidates

Representative healthy query classes:

- factura electrónica / soportes
- RUB / beneficiario final
- historical ET reform questions
- refund / saldo a favor / devolución questions

## What Is Still Not Healthy

- exact temporal precision is still weaker than desired
- duplicate article-version handling is still imperfect
- practical support-doc ranking is improved but not perfect
- some visible lines are still more mechanical than ideal and need richer synthesis
- managed chat surfaces are still only partially restored
- staging needs deeper product-level smoke, not just boot/health confidence
- the corpus blessing gate is green again, so future editorial deltas need to be merged or archived promptly to keep it that way

## Latest Verification Baseline

These commands were rerun green in the latest pass:

```bash
python3 -m py_compile src/lia_graph/pipeline_d/orchestrator.py src/lia_graph/pipeline_d/retriever.py
PYTHONPATH=src:. uv run --group dev pytest tests/test_phase3_graph_planner_retrieval.py -q
PYTHONPATH=src:. uv run --group dev pytest tests/test_phase1_runtime_seams.py -q
cd frontend && npm run test:health
cd frontend && npm run build:public
```

Also rechecked directly in-process:

- `run_pipeline_d(...)` returns `graph_native` for:
  - factura electrónica support question
  - refund / saldo a favor prompt
  - correction / firmeza / devolución mixed prompt

Also rerun green:

```bash
PYTHONPATH=src:. uv run --group dev pytest tests/test_phase3_graph_planner_retrieval.py -q
```

## Phase Summary

| Phase | Status | Next action | Notes |
|------|--------|-------------|-------|
| 1 | COMPLETE | keep shell/runtime seams stable as Phase 3 advances | backend routing seam and runtime contract preserved |
| 2 | COMPLETE | rerun artifact build only when corpus changes materially | graph artifacts and Falkor parity are green |
| 3 | IN_PROGRESS | advance retrieval quality, practical workflows, managed surfaces, orchestration parity, and health coverage in parallel | this is the active product phase |
| 4 | PLANNED | runtime context/history controls after Phase 3 hardens | depends on Phase 3 stabilization |
| 5 | PLANNED | composition/cache/verification expansion | not started |
| 6 | PLANNED | dual-run and eval orchestration | not started |
| 7 | PLANNED | rollout and governance | not started |

## Files Most Central To The Current Runtime

- `src/lia_graph/ui_server.py`
- `src/lia_graph/pipeline_router.py`
- `src/lia_graph/topic_router.py`
- `src/lia_graph/topic_guardrails.py`
- `src/lia_graph/pipeline_c/temporal_intent.py`
- `src/lia_graph/pipeline_d/contracts.py`
- `src/lia_graph/pipeline_d/planner.py`
- `src/lia_graph/pipeline_d/retriever.py`
- `src/lia_graph/pipeline_d/orchestrator.py`
- `docs/guide/orchestration.md`
- `frontend/src/features/orchestration/graph/pipelineGraph.ts`
- `tests/test_phase3_graph_planner_retrieval.py`

## Decision Ledger

| Date | Decision | Impact |
|------|----------|--------|
| 2026-04-14 | Shared corpus + shared graph is the target knowledge architecture | all later phases assume shared knowledge, tenant-scoped runtime |
| 2026-04-14 | Topic/subtopic labels are supportive metadata, not the load-bearing retrieval engine | protects graph-first retrieval design |
| 2026-04-14 | The first weak-anchor fallback in Phase 3 is lexical graph matching over articles, not label-first document retrieval | keeps low-friction entry without collapsing into flat RAG |
| 2026-04-15 | Temporal behavior lives inside the planner contract and graph-first retrieval, not in a second historical path | all historical improvements must extend `pipeline_d` |
| 2026-04-15 | The served chat runtime now defaults to `pipeline_d` | GUI and API both exercise the graph runtime by default |
| 2026-04-15 | Practical accountant prompts must work without article-quote phrasing | router/planner/retriever must support natural-language accountant workflows |
| 2026-04-15 | Published answers must be practical-first and must not leak meta-thinking | visible answer quality is now a product rule |
| 2026-04-15 | Orchestration docs and `/orchestration` HTML must stay truthful to the current system; the markdown guide may also document the build-time ingestion lane when it is clearly separated from the served runtime | prevents stale architecture explanations from drifting back in |
| 2026-04-15 | Support-doc selection must preserve lexical practical context from natural-language prompts | improves practical answer quality without requiring law citations |

## Resume Protocol

1. Read `docs/build/buildv1/NEXT.md`
2. Read this `STATE.md`
3. Read `docs/guide/orchestration.md`
4. Inspect the active Phase 3 files:
   - planner
   - retriever
   - orchestrator
5. Re-run the verification baseline before new work
6. Choose a front explicitly instead of drifting across all fronts at once

## Change Logging Rule

Any material implementation session should update:

- `docs/build/buildv1/NEXT.md`
- `docs/build/buildv1/STATE.md`
- the active phase file if the checkpoint or active workstream meaningfully changed
