# Chat Response Architecture

## Purpose

This guide explains where the live chat-answer behavior is defined in the repo and how to tune it without creating drift, duplication, or contradictory rules.

This markdown file is the primary documentation source of truth for chat-response shaping in the served runtime.
If code and old docs seem to disagree, this file should explain which module owns the live behavior and where the mismatch must be fixed.

The target product behavior is:

- a response that feels like a senior accountant guiding another accountant
- practical advice first
- legal grounding inline, not as detached legal theater
- workflow-aware structure that changes by question type
- a repo layout where tone, sectioning, and retrieval heuristics are easy to find and change

This guide is about the served runtime only.

## The Four Layers

There are four different kinds of “instructions” in the runtime. They should not be mixed.

### 1. Request-Level Knobs

These decide the coarse response envelope exposed by the API and UI.

Source of truth:

- `src/lia_graph/chat_response_modes.py`
- `src/lia_graph/pipeline_c/contracts.py`

This layer owns:

- `response_depth`
- `first_response_mode`
- allowed values and defaults

Rule:

- if a new response knob is added, define it once in `chat_response_modes.py` and import it everywhere else

Consumers:

- `src/lia_graph/ui_validation_helpers.py`
- `src/lia_graph/ui_chat_payload.py`
- `src/lia_graph/ui_chat_persistence.py`
- `src/lia_graph/chat_run_runtime.py`
- `src/lia_graph/ui_server.py`

### 2. Retrieval Intent And Workflow Routing

These decide what evidence we try to bring before we compose the answer.

Source of truth (planner + shared support):

- `src/lia_graph/pipeline_d/planner.py`
- `src/lia_graph/pipeline_d/planner_query_modes.py` — query-mode classifier + `_detect_sub_topic_intent`
- `src/lia_graph/pipeline_d/retrieval_support.py`

Source of truth (retrieval adapters — orchestrator picks per request based on `LIA_CORPUS_SOURCE` + `LIA_GRAPH_MODE`; see `docs/orchestration/orchestration.md` for the versioned env matrix):

- `src/lia_graph/pipeline_d/retriever.py` — artifact BFS. Active in `dev`.
- `src/lia_graph/pipeline_d/retriever_supabase.py` — cloud Supabase `hybrid_search` RPC + `documents` lookup. Active in `dev:staging` for the chunks half. Passes `filter_subtopic` + `subtopic_boost` (floor 1.0, default 1.5 from `LIA_SUBTOPIC_BOOST_FACTOR`) when the planner emits `sub_topic_intent`.
- `src/lia_graph/pipeline_d/retriever_falkor.py` — cloud FalkorDB bounded Cypher BFS. Active in `dev:staging` for the graph half. Runs a preferential `HAS_SUBTOPIC → SubTopicNode` probe when `sub_topic_intent` fires and merges those article keys with explicit anchors. Propagates errors — never silently falls back to artifacts.

The three adapters return the same `GraphEvidenceBundle` shape (now including `subtopic_anchor_keys`) so synthesis and assembly do not need to know which one ran. The orchestrator merges the Supabase chunks half with the Falkor graph half when both staging flags are set.

This layer owns:

- query-mode classification
- workflow detection
- focused follow-up continuity anchoring
- lexical graph searches
- support-doc reservation and diversification
- graph traversal priorities

Rule:

- if the answer is wrong because it is grounded on the wrong norms or support docs, fix this layer first

### 3. Practical Enrichment Extraction

This layer turns retrieved evidence into reusable practical signals before final formatting.

Source of truth:

- `src/lia_graph/pipeline_d/answer_support.py`

This layer owns:

- marker vocabularies
- support-line cleaning
- extraction buckets such as `procedure`, `precaution`, `strategy`, `jurisprudence`, `checklist`

Rule:

- if the grounding is right but the answer still feels thin, dry, or unhelpful, tune this layer before adding more hardcoded copy

### 4. Published Answer Policy

This is the layer that should define how the answer feels to the user.

Source of truth:

- `src/lia_graph/pipeline_d/answer_policy.py`
- `src/lia_graph/pipeline_d/answer_synthesis.py`
- `src/lia_graph/pipeline_d/answer_synthesis_sections.py`
- `src/lia_graph/pipeline_d/answer_synthesis_helpers.py`
- `src/lia_graph/pipeline_d/answer_assembly.py`
- `src/lia_graph/pipeline_d/answer_first_bubble.py`
- `src/lia_graph/pipeline_d/answer_followup.py`
- `src/lia_graph/pipeline_d/answer_inline_anchors.py`
- `src/lia_graph/pipeline_d/answer_historical_recap.py`
- `src/lia_graph/pipeline_d/answer_comparative_regime.py` (next_v4 §5 — pre/post-reform table renderer for `comparative_regime_chain`)
- `src/lia_graph/pipeline_d/answer_shared.py`
- `src/lia_graph/pipeline_d/answer_llm_polish.py` (optional post-assembly polish; gated by `LIA_LLM_POLISH_ENABLED=1`)
- `src/lia_graph/pipeline_d/orchestrator.py`

Division of responsibility:

- `answer_policy.py` owns declarative response-shaping policy:
  - section limits
  - article/title guidance
  - workflow-specific blueprint copy
- `answer_synthesis.py` is the stable synthesis facade for main chat.
- `answer_synthesis_sections.py` owns section builders:
  - recommendation/procedure/paperwork/context candidate lines
  - procedural fallbacks
  - legal-anchor candidate sections
- `answer_synthesis_helpers.py` owns shared synthesis helpers:
  - support-line cleanup handoff
  - anchor matching
  - tax-treatment heuristics
  - procedure-anchor helpers
- `answer_assembly.py` is the stable assembly facade for main chat.
- `answer_first_bubble.py` owns chat-main first-bubble composition:
  - which answer shape applies
  - first-bubble assembly
- `answer_followup.py` owns chat-main second-plus publication:
  - focused double-click routing
  - direct-answer lead selection
  - broader follow-up section assembly
- `answer_inline_anchors.py` owns inline legal anchoring for first-bubble lines:
  - line cleanup
  - anchor selection
  - anchor rendering
  - prepared line shaping
- `answer_historical_recap.py` owns historical recap formatting for first-bubble output:
  - reform-chain summary lines
  - chronological ordering
  - recap line wording
- `answer_comparative_regime.py` (next_v4 §5, 2026-04-25) owns the `comparative_regime_chain` rendering path:
  - cue detection (`detect_comparative_regime_cue` — runs before the standard query-mode classifier)
  - pair lookup against `config/comparative_regime_pairs.json`
  - verdict line ("Sí cambia" / "No cambia") + side-by-side markdown table (≥3 rows: plazo / fórmula-o-tope / reajuste-o-ajuste) + Riesgos + Soportes wrapping below
  - LLM polish preserves the table verbatim
- `answer_shared.py` owns shared publication/rendering helpers for main chat:
  - normalization
  - publication filters
  - dedup keys
  - common section rendering
  - change-intent detection
- `answer_llm_polish.py` owns the optional post-assembly polish pass:
  - senior-accountant voice rewrite of the deterministic template answer
  - `(art. X ET)` inline-anchor preservation invariant
  - `Respuestas directas` structural preservation when the planner emitted sub-questions
  - loud failure in `response.llm_runtime.skip_reason`, silent fallback in visible output
- `orchestrator.py` owns Pipeline D runtime flow only:
  - build retrieval plan
  - fetch graph evidence
  - hand off to synthesis + assembly
  - optionally hand assembly output to `answer_llm_polish.py`
  - package the response contract

Rule:

- if you are changing the visible personality or structure of the answer, prefer `answer_policy.py`
- if you are changing how evidence becomes section candidates, use `answer_synthesis_sections.py` or `answer_synthesis_helpers.py`
- if you are changing first-bubble structure, second-plus follow-up publication, inline anchors, or markdown section rendering, use `answer_first_bubble.py`, `answer_followup.py`, or `answer_shared.py`
- only edit `orchestrator.py` when the hot-path runtime flow itself changes

## Current Source Of Truth For “Senior Accountant Guides You”

Today the clearest implementation of that product behavior is:

- general normative/practical shaping: `src/lia_graph/pipeline_d/answer_policy.py`
- tax-planning advisory shaping: `build_tax_planning_first_bubble_sources()` in `src/lia_graph/pipeline_d/answer_policy.py`
- graph-evidence-to-answer synthesis for main chat: `src/lia_graph/pipeline_d/answer_synthesis.py` plus `answer_synthesis_sections.py`
- first-bubble and second-plus assembly for main chat: `src/lia_graph/pipeline_d/answer_assembly.py` plus `answer_first_bubble.py` and `answer_followup.py`
- inline anchors for main chat first bubble: `src/lia_graph/pipeline_d/answer_inline_anchors.py`
- historical recap for main chat first bubble: `src/lia_graph/pipeline_d/answer_historical_recap.py`
- shared publication filters and text utilities for main chat: `src/lia_graph/pipeline_d/answer_shared.py`
- request execution and Pipeline D wiring: `src/lia_graph/pipeline_d/orchestrator.py`

That means the repo now has one explicit place for:

- “what should this answer sound like?”
- “which sections should appear?”
- “how many items should each section allow?”
- “what kind of practical guidance belongs to a workflow?”
- “how does the main chat surface synthesize graph evidence before rendering?”

## Turn-Based Publication Contract

- Turn 1 maps the case broadly through the first-bubble path.
- Turn 2 and onward publish through the follow-up path.
- Focused follow-ups should answer the quoted or double-clicked point directly, then give the operational implications.
- Broader later turns may stay sectioned, but they should not replay first-bubble framing by default.

## Information Architecture Map

The current `main chat` information architecture should be understood as a chain of contracts.

| Layer | Stable entrypoint | Produces | Consumed by | Scope |
| --- | --- | --- | --- | --- |
| Request envelope | `chat_response_modes.py` + `pipeline_c/contracts.py` | normalized response knobs | UI/runtime, `pipeline_d` | shared |
| Topic + planner | `planner.py` | retrieval plan, temporal context, query mode, follow-up continuity anchors | `retriever.py`, `orchestrator.py` | shared |
| Retrieval (env-gated) | `retriever.py` / `retriever_supabase.py` / `retriever_falkor.py` | `GraphEvidenceBundle` | `answer_synthesis.py` | shared |
| Enrichment extraction | `answer_support.py` | article insights and support insights | `answer_synthesis.py` | shared hot path |
| Main-chat synthesis facade | `answer_synthesis.py` | `GraphNativeAnswerParts` | `orchestrator.py`, `answer_assembly.py` | `main chat` |
| Main-chat assembly facade | `answer_assembly.py` | first-turn and second-plus visible markdown routes | `orchestrator.py` | `main chat` |
| Runtime packaging | `orchestrator.py` | `PipelineCResponse` | `ui_server.py` | shared runtime |

Under those stable contracts, the current `main chat` implementation modules are:

| Facade | Internal implementation modules |
| --- | --- |
| `answer_synthesis.py` | `answer_synthesis_sections.py`, `answer_synthesis_helpers.py` |
| `answer_assembly.py` | `answer_first_bubble.py`, `answer_followup.py`, `answer_inline_anchors.py`, `answer_historical_recap.py`, `answer_comparative_regime.py`, `answer_shared.py` |

Design rule:

- a caller should prefer the facade if the goal is to consume behavior
- a contributor should go into the deeper implementation module only when changing that behavior

## Surface Boundaries

The current split is intentionally `main chat` specific.

- `answer_policy.py` + `answer_synthesis.py` + `answer_assembly.py` are the stable entrypoints for live chat answer behavior.
- `answer_synthesis_sections.py`, `answer_synthesis_helpers.py`, `answer_first_bubble.py`, `answer_followup.py`, `answer_inline_anchors.py`, `answer_historical_recap.py`, `answer_comparative_regime.py`, and `answer_shared.py` hold the focused implementation modules behind those facades.
- `Normativa` now has its own surface package under `src/lia_graph/normativa/`.
- `Interpretación` now has its own surface package under `src/lia_graph/interpretacion/`.

Rule:

- do not keep adding `Normativa` or `Interpretación` UI-shaping logic into the main chat assembly modules just because the evidence source is shared
- shared graph retrieval and evidence utilities can stay shared; surface assembly should not

Practical consequence by surface:

- `Normativa` reuses planner/retriever/evidence contracts where that is actually shared
- `Normativa` must not treat `answer_synthesis.py` or `answer_assembly.py` as its own UI contract
- `Normativa` currently uses:
  - `src/lia_graph/normativa/orchestrator.py`
  - `src/lia_graph/normativa/synthesis.py`
  - `src/lia_graph/normativa/policy.py`
  - `src/lia_graph/normativa/synthesis_helpers.py`
  - `src/lia_graph/normativa/sections.py`
  - `src/lia_graph/normativa/assembly.py`
  - `src/lia_graph/normativa/shared.py`
- `Interpretación` currently uses:
  - `src/lia_graph/ui_analysis_controllers.py`
  - `src/lia_graph/interpretacion/orchestrator.py`
  - `src/lia_graph/interpretacion/synthesis.py`
  - `src/lia_graph/interpretacion/policy.py`
  - `src/lia_graph/interpretacion/synthesis_helpers.py`
  - `src/lia_graph/interpretacion/assembly.py`
  - `src/lia_graph/interpretacion/shared.py`
  - `src/lia_graph/interpretation_relevance.py` as compatibility facade

## Window Surface Map

The repo now has different orchestration ownership by visible surface:

- `main chat`: `src/lia_graph/pipeline_d/orchestrator.py` + `answer_*` modules
- `Normativa`: deterministic citation/profile stack plus `src/lia_graph/normativa/*`
- `Interpretación`: `ui_analysis_controllers.py` plus `src/lia_graph/interpretacion/*`
- source/document windows: deterministic document-reader path, not answer assembly

Inside the `Normativa` package, the current split now mirrors the same general idea as `main chat` without copying its visible structure:

- `orchestrator.py`, `synthesis.py`, and `assembly.py` are the stable surface seams
- `policy.py`, `synthesis_helpers.py`, `sections.py`, and `shared.py` are focused implementation modules behind those seams

The post-answer runtime order is:

1. publish the `main chat` bubble
2. prime the `Normativa` track
3. prime the `Interpretación` track

But that ordering does not mean deep blocking. `Normativa` and `Interpretación` should both start from the same minimal turn kernel (`trace_id`, user message, published answer, normalized topic/country, cited-anchor snapshot) and run independently. `Interpretación` must not wait for full `Normativa` retrieval to finish before starting its own retrieval. Full concurrency rules live in `docs/orchestration/orchestration.md` §Post-Answer Surface Concurrency.

Editing rule:

- if the visible behavior is wrong inside `main chat`, edit the `answer_*` path
- if the visible behavior is wrong inside `Normativa`, edit `src/lia_graph/normativa/*` or the deterministic citation/profile builders
- do not fix a `Normativa` modal problem by patching `main chat` first-bubble modules

## Editing Rules

Use this order when changing behavior:

1. If the wrong workflow is activated, edit `planner.py`.
2. If the right workflow is found but the support is weak, edit `answer_support.py` or `retriever.py`.
3. If the evidence is right but the answer parts are weak or badly prioritized, edit `answer_synthesis_sections.py` or `answer_synthesis_helpers.py`.
4. If the visible answer is too dry, too long, too legalistic, or badly structured, edit `answer_policy.py`, `answer_first_bubble.py`, `answer_followup.py`, `answer_inline_anchors.py`, `answer_historical_recap.py`, or `answer_shared.py`.
5. Only edit `orchestrator.py` when the issue is runtime flow rather than answer shaping.

## Module Map

Use this as the quickest reliable map when you need to tune the chat runtime:

- `orchestrator.py`: request enters Pipeline D, evidence is fetched, synthesis and assembly are called, response contract is returned.
- `answer_synthesis.py`: stable facade that turns evidence plus temporal context into structured answer parts.
- `answer_synthesis_sections.py`: section-specific candidate builders for recommendations, procedure, paperwork, anchors, context, precautions, and opportunities.
- `answer_synthesis_helpers.py`: reusable synthesis heuristics like fallback steps, support-line extension, anchor-tail injection, and tax-treatment detection.
- `answer_assembly.py`: stable facade for visible chat assembly and shared rendering exports.
- `answer_first_bubble.py`: decides first-bubble shape and assembles first-turn sections.
- `answer_followup.py`: publishes second-plus answers, distinguishing focused double-clicks from broader follow-ups.
- `answer_inline_anchors.py`: chooses which legal references should attach inline to each first-bubble line.
- `answer_historical_recap.py`: decides whether historical recap should appear and how reform chains are narrated.
- `answer_comparative_regime.py`: handles the `comparative_regime_chain` query mode (next_v4 §5) — detects pre/post-reform comparison cues, looks up the matching pair in `config/comparative_regime_pairs.json`, renders verdict + side-by-side markdown table.
- `answer_shared.py`: common normalization, publication filtering, deduplication, change-intent detection, and markdown section rendering.
- `answer_llm_polish.py`: optional senior-accountant voice rewrite of the deterministic template answer. Preserves inline legal anchors and `Respuestas directas` sub-question structure. Gated by `LIA_LLM_POLISH_ENABLED` (default `1`).
- `answer_policy.py`: declarative product voice and workflow blueprint policy.

Stability rule:

- other modules should prefer importing from the stable facades `answer_synthesis.py` and `answer_assembly.py`
- deeper modules are implementation detail for the `main chat` surface and can evolve faster

## Anti-Drift Rules

To keep the repo understandable over time:

- do not duplicate allowed enum values across UI/runtime files
- do not put large blocks of tone-defining copy directly in `planner.py` or `retriever*.py`
- do not add product-policy prose to tests; tests should assert behavior, not become the policy store
- do not keep two “current runtime” docs alive at the same time
- when a guide becomes historical, mark it explicitly as archived
- do not branch answer-shaping logic on `LIA_CORPUS_SOURCE` / `LIA_GRAPH_MODE` — those flags belong to retrieval dispatch only; synthesis and assembly must stay backend-agnostic
- when retrieval contract or env flags change, bump the env matrix version in `docs/orchestration/orchestration.md`

## Practical Tuning Checklist

When a future answer feels off, ask these in order:

1. Did the planner anchor the right legal regime?
2. Did support-doc selection preserve the practical/advisory context?
3. Did extraction capture the right practical lines?
4. Did the answer policy choose the right structure for that workflow?
5. Did assembly preserve the advice cleanly with inline legal support?

If all five are easy to answer, the architecture is doing its job.
