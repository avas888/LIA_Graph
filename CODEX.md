# CODEX.md

Execution guide for Codex-family agents working in `Lia_Graph`.

## Canonical Guidance

Start with:

1. `AGENTS.md`
2. `docs/guide/orchestration.md`
3. `docs/guide/chat-response-architecture.md`

`AGENTS.md` is the canonical repo-level agent guide.
`docs/guide/orchestration.md` is the main critical runtime map.

## Working Rules

- make changes in the narrowest module that owns the behavior
- prefer the stable `main chat` facades over direct deep imports when consuming behavior
- do not default to `src/lia_graph/pipeline_d/orchestrator.py` for answer-shaping work
- keep “senior accountant guiding you” as the north star for response work
- keep legal grounding tied inline to practical advice
- preserve clear surface boundaries between `main chat`, `Normativa`, and future `Interpretación`

## Layer Cheat Sheet

- request knobs -> `src/lia_graph/chat_response_modes.py`, `src/lia_graph/pipeline_c/contracts.py`
- retrieval intent -> `src/lia_graph/pipeline_d/planner.py`, `retriever.py`
- practical enrichment -> `src/lia_graph/pipeline_d/answer_support.py`
- synthesis policy -> `src/lia_graph/pipeline_d/answer_policy.py`, `answer_synthesis*.py`
- visible rendering -> `src/lia_graph/pipeline_d/answer_assembly.py`, `answer_first_bubble.py`, `answer_inline_anchors.py`, `answer_historical_recap.py`, `answer_shared.py`
- runtime flow -> `src/lia_graph/pipeline_d/orchestrator.py`

## Sync Requirement

If you change the runtime information architecture, update the same truth in:

1. `docs/guide/orchestration.md`
2. `docs/guide/chat-response-architecture.md`
3. the `/orchestration` frontend map

## Future-Surface Rule

When working on `Normativa`:

- reuse shared graph logic where appropriate
- keep deterministic Normativa UX authoritative
- build a Normativa-specific orchestration and assembly path
- do not reuse `main chat` assembly as the hidden modal contract

If a planned change makes it harder to explain “where this behavior lives,” stop and simplify the architecture first.
