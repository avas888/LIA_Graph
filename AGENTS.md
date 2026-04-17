# AGENTS.md

Canonical operating guide for AI agents working in `Lia_Graph`.

## Start Here

Before changing the served runtime, read these in order:

1. `docs/guide/orchestration.md`
2. `docs/guide/chat-response-architecture.md`
3. `frontend/src/app/orchestration/shell.ts`
4. `frontend/src/features/orchestration/orchestrationApp.ts`

`docs/guide/orchestration.md` is the main critical file for agents.
It is the end-to-end map of the live runtime, the information architecture, and the boundary between shared graph logic and surface-specific orchestration.

`docs/guide/chat-response-architecture.md` is the companion source of truth for how the `main chat` answer is shaped.

If those docs and the code disagree, fix the mismatch instead of silently following whichever one you happened to read first.

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
4. `src/lia_graph/pipeline_d/orchestrator.py`
5. `src/lia_graph/pipeline_d/planner.py`
6. `src/lia_graph/pipeline_d/retriever.py`
7. `src/lia_graph/pipeline_d/answer_support.py`
8. `src/lia_graph/pipeline_d/answer_synthesis.py`
9. `src/lia_graph/pipeline_d/answer_assembly.py`

## Stable Facades vs Implementation Detail

Treat these as the stable `main chat` entrypoints:

- `src/lia_graph/pipeline_d/answer_synthesis.py`
- `src/lia_graph/pipeline_d/answer_assembly.py`

Treat these as focused implementation modules behind those facades:

- `src/lia_graph/pipeline_d/answer_synthesis_sections.py`
- `src/lia_graph/pipeline_d/answer_synthesis_helpers.py`
- `src/lia_graph/pipeline_d/answer_first_bubble.py`
- `src/lia_graph/pipeline_d/answer_inline_anchors.py`
- `src/lia_graph/pipeline_d/answer_historical_recap.py`
- `src/lia_graph/pipeline_d/answer_shared.py`

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
- `src/lia_graph/pipeline_d/retriever.py`
- `src/lia_graph/pipeline_d/retrieval_support.py`

Use this layer when the answer is grounded on the wrong norm, wrong workflow, or wrong support corpus.

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
- `docs/guide/orchestration.md` still describes reality
- `docs/guide/chat-response-architecture.md` still matches the live `main chat`
- the `/orchestration` page still maps the same architecture
- `Normativa` and `Interpretación` boundaries did not get blurred by convenience edits

If an agent can answer “where does this behavior live?” in one minute, the architecture is probably healthy.
