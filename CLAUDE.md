# CLAUDE.md

Quickstart for Claude-family agents working in `Lia_Graph`.

## Canonical Guidance

Read these before changing the served runtime:

1. `AGENTS.md`
2. `docs/guide/orchestration.md`
3. `docs/guide/chat-response-architecture.md`

`docs/guide/orchestration.md` is the main critical file.
It is the end-to-end runtime and information-architecture map.

## What To Internalize First

- the product target is “a senior accountant guiding another accountant”
- `main chat` uses stable facades:
  - `src/lia_graph/pipeline_d/answer_synthesis.py`
  - `src/lia_graph/pipeline_d/answer_assembly.py`
- `orchestrator.py` is runtime flow, not the default place to fix answer quality
- `Normativa` and future `Interpretación` should get their own orchestration boundaries

## Fast Decision Rule

Use this shortcut when deciding where to work:

- wrong norms or wrong workflow -> planner or retriever
- right evidence but weak practical substance -> `answer_support.py`
- wrong tone, shape, or visible organization -> `answer_policy.py` or the `main chat` assembly modules
- runtime wiring change -> `orchestrator.py`

## Non-Negotiables

- keep docs, code, and the `/orchestration` architecture page aligned
- prefer focused module edits over monolithic rewrites
- do not let `main chat` become the hidden rendering layer for `Normativa`
- if architecture changes, update `docs/guide/orchestration.md`

If there is any doubt, follow `AGENTS.md` and treat it as the repo-level operating guide.
