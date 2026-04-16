# Build V1 — Next

## Cold-Start Handoff

Assume **zero thread context**.

This file is the resume point for another LLM starting cold in `/Users/ava-sensas/Developer/Lia_Graph`.
Trust this file over scattered intermediate notes.

The project is **not** at “bootstrap the graph from scratch” anymore.
The live product path already exists:

- `ui_server.py`
- `pipeline_router.py`
- `pipeline_d`
- local graph artifacts on disk
- public GUI on `/public`

The current job is to keep that product path healthy while advancing several parallel fronts.
The immediate first task is to harden the **first visible accountant answer** by working fronts 1, 2, and 3 together instead of treating them as isolated queues.

## Non-Negotiable Product Rules

These are current product rules, not suggestions:

- The served chat path is `pipeline_d`.
- The visible answer must be **accountant-facing only**.
- The visible answer must be **practical-first**:
  - what to do
  - procedure
  - supporting documents / working papers
  - legal anchors
  - changes / context
  - precautions
  - opportunities
- The visible answer must **not** expose planner/retrieval/meta-thinking text.
- Accountants should **not** have to quote the law to get a good answer.
- The `/orchestration` HTML page must depict the **current served runtime**.
- The orchestration markdown guide should stay truthful to the served runtime and may also document the build-time ingestion lane when it is clearly separated from the hot path.
- Do **not** create a second historical retrieval path; improve `pipeline_d`.

## Product Truth

### Served chat path

Every normal chat request currently follows this path:

1. `src/lia_graph/ui_server.py`
2. `src/lia_graph/pipeline_router.py`
3. `src/lia_graph/topic_router.py` + topic guardrails
4. `src/lia_graph/pipeline_d/planner.py`
5. `src/lia_graph/pipeline_d/retriever.py`
6. `src/lia_graph/pipeline_d/orchestrator.py`
7. `/api/chat` or `/api/chat/stream`

### Live answer source

The current served answer path reads local artifacts:

- `artifacts/canonical_corpus_manifest.json`
- `artifacts/parsed_articles.jsonl`
- `artifacts/typed_edges.jsonl`

### Corpus Truth

The current local corpus state is:

- `knowledge_base/` mirrors the current Dropbox corpus state after the open editorial revision tranche was merged into base docs and archived under `deprecated/`
- latest full snapshot counts: `1319` synced files, `1246` `include_corpus`, `0` `revision_candidate`, `73` `exclude_internal`
- `taxonomy_version = draft_v1_2026_04_15c`
- shared-path audit parity between Dropbox and `knowledge_base` is exact: `0` decision/label mismatches
- `79` Dropbox source files remain intentionally outside the snapshot, and all of them classify as `exclude_internal`
- the canonical manifest is fully blessable again: `1246` ready, `0` review required, `0` pending revisions

Before treating a future corpus change as durably green, inspect:

- `artifacts/corpus_reconnaissance_report.json`
- `artifacts/revision_candidates.json`
- `artifacts/canonical_corpus_manifest.json`

### What Supabase is for

Supabase is currently runtime persistence and ops state, including:

- conversations
- chat runs
- metrics
- feedback
- usage ledger
- auth nonces
- terms state
- active-generation state

It is **not** the live per-request retrieval engine for the served chat answer.

### What Falkor is for

Falkor matters for:

- local Docker parity in `npm run dev`
- cloud parity in `npm run dev:staging`
- graph ops / environment health

It is **not** currently the live per-request traversal source for the served answer path.

## Current Healthy Baseline

These are currently true and usable:

- `pipeline_router` defaults to `pipeline_d`
- `/api/chat` hits the graph-native runtime by default
- the public GUI can open and ask/get answers through the real corpus-backed path
- the first historical/vigencia slice is live
- the first practical accountant-style workflow without law-quote prompting is live
- the visible answer formatter now hides system meta-thinking
- the orchestration guide and `/orchestration` HTML view now depict the live runtime directly

Representative healthy query types:

- factura electrónica / soportes:
  - `771-2`, `616-1`, `617`
- RUB / beneficiario final:
  - `631-5`, `631-6`, `658-3`
- historical ET:
  - `¿Qué decía el artículo 115 antes de la Ley 2277 de 2022?`
- accountant-style refund workflow:
  - `Mi cliente tiene saldo a favor en renta del AG 2025...`

## Parallel Fronts

The next model should think in **parallel workstreams**, not one giant linear backlog.

### 1. Retrieval Precision and Historical Fidelity

**Status:** first-response hardening now active

**Healthy now:**

- `temporal_context` exists
- historical questions switch to `historical_reform_chain`
- reform-year false positives like `2277` as article anchors are fixed
- historical queries can surface a cutoff and reform anchor

**Not healthy yet:**

- historical cutoffs are still heuristic in key cases
- exact `effective_date` / vigencia is not yet used consistently
- duplicate/versioned `article_key` rows are not handled faithfully enough
- historical connected-article neighborhoods can still be noisy

**Next concrete work:**

- prefer exact artifact-backed dates when available
- improve article-version disambiguation
- add at least one explicit `consulta_date` or `operation_date` test
- tighten historical connected-article ranking
- keep procedural `antes de ...` phrasing from falsely triggering historical/reform behavior

**Primary files:**

- `src/lia_graph/pipeline_c/temporal_intent.py`
- `src/lia_graph/pipeline_d/contracts.py`
- `src/lia_graph/pipeline_d/planner.py`
- `src/lia_graph/pipeline_d/retriever.py`

### 2. Practical Accountant Workflows

**Status:** first lane green, first-response expansion active

**Healthy now:**

- refund / saldo a favor / devolución prompts work without explicit article quoting
- router now prefers `procedimiento_tributario` instead of getting hijacked by `facturacion_electronica`
- planner seeds lexical refund anchors for natural-language prompts

**Not healthy yet:**

- this treatment is still narrow
- more accountant workflows need the same planner + support-doc treatment
- support-doc selection for natural-language practical prompts is better, but still not perfect topic-by-topic

**Next concrete work:**

- extend the same approach to more workflows:
  - correction / firmeza
  - devolución vs compensación
  - benefit of audit interactions
  - other high-frequency accountant procedures
- keep practical prompts usable without requiring legal citations
- keep mixed prompts from losing the main workflow when practical sub-questions appear together

**Primary files:**

- `src/lia_graph/topic_router.py`
- `src/lia_graph/topic_guardrails.py`
- `src/lia_graph/pipeline_d/planner.py`
- `src/lia_graph/pipeline_d/retriever.py`

### 3. Published Answer Quality

**Status:** new contract live, first-response enrichment active

**Healthy now:**

- visible answer is practical-first
- visible answer no longer leaks planner/retrieval labels
- procedure can now absorb support-document insights
- a `Soportes y Papeles de Trabajo` section now exists in the formatter

**Not healthy yet:**

- some topics still produce thinner procedure detail than desired
- support-doc extraction can still surface generic lines instead of the best operational lines
- legal references are now “peppered in,” but not always as richly as they should be

**Next concrete work:**

- improve support-doc ranking by topic relevance
- pull more usable procedural facts straight from the anchored norms when they are already in the artifact text
- extract stronger procedural and paperwork detail from practice docs
- keep the visible answer useful first, legal second, never meta
- keep URLs, bibliography noise, and low-signal support lines out of the visible reply

**Primary files:**

- `src/lia_graph/pipeline_d/orchestrator.py`
- `src/lia_graph/pipeline_d/retriever.py`

### 4. GUI and Managed Chat Surfaces

**Status:** core ask/get-answer path green, richer managed surfaces partial

**Healthy now:**

- `/public` opens locally
- `?message=...` public handoff works again
- public chat can send and receive real corpus-backed answers
- thinking mascot preload path is restored

**Not healthy yet:**

- richer evidence drill-down is still partial
- saved history / managed-chat surfaces are not fully restored
- some admin or secondary surfaces still fail cleanly with stubs rather than full behavior

**Next concrete work:**

- restore richer evidence/history/admin surfaces that surround the core chat
- keep the simple ask/get-answer path stable while that work lands

**Primary files:**

- `src/lia_graph/ui_server.py`
- `frontend/src/app/public/main.ts`
- `frontend/src/features/chat/chatApp.ts`
- `frontend/src/features/chat/chatSurfaceController.ts`

### 5. Orchestration Docs and HTML Depiction

**Status:** freshly rewritten and aligned

**Healthy now:**

- `docs/guide/orchestration.md` describes the current runtime and the build-time ingestion lane that produces its artifact inputs
- `/orchestration` now depicts the live Pipeline D procedure only
- frontend test now guards the live-route depiction from drifting

**Not healthy yet:**

- this can drift again if runtime changes and docs/UI do not get updated together

**Next concrete work:**

- whenever the runtime path changes, update all three together:
  - markdown guide
  - `/orchestration` graph
  - orchestration frontend test

**Primary files:**

- `docs/guide/orchestration.md`
- `frontend/src/features/orchestration/graph/pipelineGraph.ts`
- `frontend/tests/orchestrationApp.test.ts`

### 6. Dev / Staging Runtime and Health Checks

**Status:** launchers exist and are useful

**Healthy now:**

- `npm run dev`
- `npm run dev:check`
- `npm run dev:staging`
- `npm run dev:staging:check`
- local GUI health tests are green

**Not healthy yet:**

- staging still needs deeper product smoke beyond boot and health endpoints
- cross-environment parity should keep being proven, not assumed

**Next concrete work:**

- do a deeper staging smoke when cloud creds and time permit
- keep environment health checks honest as runtime surfaces are restored

**Primary files:**

- `package.json`
- `scripts/dev-launcher.mjs`
- `src/lia_graph/ui_server.py`

### 7. Automated Health Testing

**Status:** real foundation exists

**Healthy now:**

- backend phase tests are green
- frontend fast health battery is green
- orchestration page is under test
- browser E2E infra exists

**Not healthy yet:**

- coverage is still concentrated on the core happy path
- richer evidence/history/admin surfaces need browser tests once restored

**Next concrete work:**

- add more real GUI scenario coverage as product surfaces come back
- keep tests focused on true product health, not brittle DOM trivia

**Primary files:**

- `tests/test_phase1_runtime_seams.py`
- `tests/test_phase3_graph_planner_retrieval.py`
- `frontend/tests/orchestrationApp.test.ts`
- `frontend/e2e/app-health.spec.ts`
- `frontend/vitest.config.ts`
- `frontend/playwright.config.ts`

## Latest Verification Baseline

These commands were rerun successfully in the latest pass:

```bash
python3 -m py_compile src/lia_graph/pipeline_d/orchestrator.py src/lia_graph/pipeline_d/retriever.py
PYTHONPATH=src:. uv run --group dev pytest tests/test_phase3_graph_planner_retrieval.py -q
PYTHONPATH=src:. uv run --group dev pytest tests/test_phase1_runtime_seams.py -q
cd frontend && npm run test:health
cd frontend && npm run build:public
```

Also verified in-process:

- `run_pipeline_d(...)` returns `graph_native` on:
  - factura electrónica support question
  - refund / saldo a favor prompt
- refund support-doc selection now preserves practical lexical context and returns:
  - `L-DEV`
  - `T-D`
  - normative devolución support

Last known green from an earlier browser pass, but **not rerun in the latest pass**:

```bash
cd frontend && npm run test:e2e
```

## How To Boot Locally

From `/Users/ava-sensas/Developer/Lia_Graph`:

```bash
npm run dev
```

Useful URLs:

- `http://127.0.0.1:8787/public`
- `http://127.0.0.1:8787/orchestration`

Optional environment checks:

```bash
npm run dev:check
npm run dev:staging:check
```

## Read These Files First

If resuming cold, read these in order:

```bash
sed -n '1,260p' docs/build/buildv1/NEXT.md
sed -n '1,260p' docs/build/buildv1/STATE.md
sed -n '1,260p' docs/guide/orchestration.md
sed -n '1,360p' src/lia_graph/pipeline_d/planner.py
sed -n '1,520p' src/lia_graph/pipeline_d/retriever.py
sed -n '1,360p' src/lia_graph/pipeline_d/orchestrator.py
sed -n '1,260p' frontend/src/features/orchestration/graph/pipelineGraph.ts
sed -n '1,320p' tests/test_phase3_graph_planner_retrieval.py
```

## If You Need To Pick One Front First

Pick in this order:

1. first-response hardening across retrieval precision + practical workflows + published answer quality
2. richer managed GUI surfaces
3. staging parity and broader E2E coverage

## Do Not Regress These

- do not reintroduce visible meta-thinking into the answer
- do not make accountant prompts depend on article-citation phrasing
- do not describe `/orchestration` as anything other than the current runtime
- do not split history/vigencia into a second retrieval architecture
