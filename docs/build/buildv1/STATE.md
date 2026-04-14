# Build V1 — Master State

> **Last updated**: 2026-04-14T12:35:39-04:00
> **Program**: Purpose-led Shared-Corpus GraphRAG for LIA
> **Status**: PHASE_2_IN_PROGRESS
> **Current phase**: 2 — Shared Regulatory Graph
> **Next action**: Point the audit-first runner at the real shared corpus roots, review `corpus_audit_report.json`, `canonical_corpus_manifest.json`, `revision_candidates.json`, and `excluded_files.json`, then run the graph path on graph-parse-ready normative docs

## Current Snapshot

- The repo shell is present and reusable.
- `pipeline_router` now resolves baseline, graph, and future dual-run routes behind the existing shell seam.
- `pipeline_d` now has a compat stub orchestrator that preserves the shared response contract.
- The current inherited path still exposes compatibility behavior in key places, but no longer depends on a hardcoded pipeline call.
- Local smoke checks passed for `/api/chat` and `/api/chat/stream` on both baseline and `pipeline_d` override when the server runs with `LIA_STORAGE_BACKEND=filesystem`.
- Async persistence job scheduling still degrades gracefully in scaffold mode because `run_job_async` does not yet match the current caller signature.
- Build V1 documentation is now the active implementation package for this effort.
- The shared corpus model must stay broad: `normative_base`, `interpretative_guidance`, and `practica_erp` are sibling evidence families in the repo.
- Phase 2 scaffolds now exist for graph schema, staged FalkorDB writes, graph validators, and deterministic parser/linker/classifier/loader seams.
- A focused Phase 2 smoke test now proves the scaffold path can parse sample markdown, derive typed edges, and stage a graph load plan without live FalkorDB credentials.
- Phase 2 now also has an artifact materializer at `python -m lia_graph.ingest` plus a `make phase2-graph-artifacts` target for inventorying the whole shared corpus in one pass and writing graph outputs from the normative family first.
- ET remains a major normative slice, but it is not the whole corpus and should not be used as shorthand for the entire knowledge base.
- All three document families are valuable to accountants in their own right; graph-first sequencing is an encoding choice, not a value judgment.
- Build V1 now documents Phase 2 as audit-first: working files, patch instructions, and internal notes must be separated from corpus admission before any inventory or graph interpretation.
- Build V1 now documents topic/subtopic as supportive metadata, while reforms, exceptions, dependencies, definitions, and vigencia belong to graph structure.
- Build V1 now distinguishes three layers in ingestion: source assets, canonical corpus, and graph-parse-ready reasoning inputs.
- The Phase 2 runner now audits all files, emits a canonical corpus manifest, and keeps non-parse-ready assets visible without sending them to the parser.
- `docs/build/` is documentation-only; code changes described here belong in the normal project tree.

## Phase Summary

| Phase | Status | Next action | Last checkpoint | Files already touched | Tests already run | Blockers | Decisions taken | Artifacts produced |
|------|--------|-------------|-----------------|-----------------------|-------------------|----------|-----------------|-------------------|
| 1 | COMPLETE | Carry forward persistence-job follow-up separately while phase 2 starts | step 5 - live smoke passed | `src/lia_graph/pipeline_router.py`, chat runtime/controller files, compat scaffold shims, `tests/test_phase1_runtime_seams.py` | `python3 -m py_compile ...`; custom `python3` harness over `tests/test_phase1_runtime_seams.py`; live `/api/chat` + `/api/chat/stream` smoke in filesystem mode | no phase blocker | keep shell contract stable; route in backend; dual-run serves primary + shadow metadata only in phase 1 | routed seam, compat Pipeline D stub, backend tests, live smoke result |
| 2 | IN_PROGRESS | Point the runner at the real corpus roots, review audit + canonical outputs, and then run graph materialization from graph-parse-ready normativa | step 5 - all-file audit, canonical manifest, and graph-parse-ready gating implemented; awaiting real corpus roots | `src/lia_graph/graph/__init__.py`, `src/lia_graph/graph/schema.py`, `src/lia_graph/graph/client.py`, `src/lia_graph/graph/validators.py`, `src/lia_graph/ingestion/__init__.py`, `src/lia_graph/ingestion/parser.py`, `src/lia_graph/ingestion/linker.py`, `src/lia_graph/ingestion/classifier.py`, `src/lia_graph/ingestion/loader.py`, `src/lia_graph/ingest.py`, `src/lia_graph/corpus_ops.py`, `tests/test_phase2_graph_scaffolds.py`, `Makefile` | `python3 -m py_compile ...`; `uv run --group dev python -m pytest tests/test_phase2_graph_scaffolds.py`; `uv run python -m lia_graph.ingest --corpus-dir <tmp>/knowledge_base --artifacts-dir <tmp>/artifacts --json` | shared corpus roots not yet present locally; audit/canonical outputs not yet reviewed on the real Dropbox trees; FalkorDB credentials/runtime still unvalidated | start Phase 2 with deterministic scaffolds before live graph connectivity; audit all source assets before ingest; materialize a canonical corpus layer; graphize normativa first without hiding interpretacion or practica; treat vocabulary as naming authority and compatibility layer, not as substitute for legal structure | graph scaffolds, audit-first artifact path, canonical corpus manifest path, staged load plan path, phase 2 smoke tests |
| 3 | PLANNED | Start planner/retrieval after graph base exists | step 0 - not started | docs only | none | phase 2 not executed | retrieval is mode-aware, not graph-only | build docs |
| 4 | PLANNED | Add runtime context and history controls after planner/retrieval path exists | step 0 - not started | docs only | none | phase 3 not executed | tenant is runtime isolation, not knowledge partition | build docs |
| 5 | PLANNED | Add composition, verification, cache | step 0 - not started | docs only | none | phase 4 not executed | compiled answers are selective and invalidated by source lineage | build docs |
| 6 | PLANNED | Add dual-run and evaluation orchestration | step 0 - not started | docs only | none | phase 5 not executed | shadow mode before default flip | build docs |
| 7 | PLANNED | Add operational rollout and governance | step 0 - not started | docs only | none | phase 6 not executed | rollout is reversible and observable | build docs |

## Resume Protocol

1. Read this file first.
2. Open the phase named in `Current phase`.
3. Resume from `Checkpoint Log.current_step`.
4. Confirm `blocked_by` is still accurate.
5. Record any new decision in both the phase file and this file if it affects later phases.

## Decision Ledger

| Date | Decision | Impact |
|------|----------|--------|
| 2026-04-14 | Build V1 lives under `docs/build/` and not `docs/next/` | centralizes this effort in one package |
| 2026-04-14 | Shared corpus + shared graph is the target knowledge architecture | constrains all later phases |
| 2026-04-14 | Tenant applies to runtime, history, permissions and context, not to corpus partitioning | reshapes phase 4 and cache model |
| 2026-04-14 | No code implementation starts until documentation is approved | phases remain executable but not yet executed |
| 2026-04-14 | Pipeline selection can be overridden server-side via request metadata while the frontend contract stays unchanged | phase 1 can route variants without UI changes |
| 2026-04-14 | `dual_run` resolves to a primary served runner plus shadow metadata, but does not execute the shadow path yet | phase 6 can build on the seam without changing phase 1 behavior |
| 2026-04-14 | Phase 1 smoke is accepted in `filesystem` mode for local scaffold validation when Supabase is unavailable in the shell runtime | keeps phase progress unblocked by missing local package/runtime wiring |
| 2026-04-14 | Phase 2 starts with deterministic graph scaffolds and staged writes before live FalkorDB execution | lets schema and ingestion contracts settle before external connectivity work |
| 2026-04-14 | Phase 2 artifact materialization lives in `python -m lia_graph.ingest` and is exposed via `make phase2-graph-artifacts` | gives the repo an executable path now without waiting on a future `scripts/` directory |
| 2026-04-14 | The shared corpus model for Build V1 is broader than ET: Phase 2 must materialize the whole shared corpus view in one pass, while graphizing the normative family first | prevents later phases from collapsing expert/practical evidence into the wrong abstraction or hiding them behind future-tense wording |
| 2026-04-14 | Phase 2 now requires a corpus audit gate before inventory or graphization, and Build V1 treats labels as supportive metadata while graph structure carries normative semantics | prevents working files and label-first retrieval habits from leaking into the new architecture |
| 2026-04-14 | Build V1 now distinguishes source assets, canonical corpus, and graph-parse-ready reasoning inputs, with a canonical manifest attaching revisions to base docs | keeps valuable assets visible without pretending every file is parser-ready or graph-ready |

## Change Logging Rule

Every implementation session must update:

- this `STATE.md`
- the active phase document
- the active phase `Checkpoint Log`

If an implementation session fails mid-flight, the last valid checkpoint must be written before closing the session.
