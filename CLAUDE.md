# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Quickstart for Claude-family agents working in `Lia_Graph`, a graph-native RAG product shell for Colombian accounting.

## Canonical Guidance

Read these before changing the served runtime:

1. `AGENTS.md` — canonical repo-level operating guide (layer ownership, surface boundaries, doc discipline)
2. `docs/orchestration/orchestration.md` — end-to-end runtime map + **authoritative** versioned env/flag matrix + change log
3. `docs/guide/chat-response-architecture.md` — companion source of truth for how the `main chat` answer is shaped
4. `docs/guide/env_guide.md` — operational counterpart: run modes, env files, squashed migration baseline, test accounts, corpus refresh

If code and docs disagree, reconcile to `docs/orchestration/orchestration.md` — never the other way around.

## Commands

### Run the app

- `npm run dev` — local app, local Supabase docker, local FalkorDB docker. Fully offline. `LIA_CORPUS_SOURCE=artifacts`, `LIA_GRAPH_MODE=artifacts`.
- `npm run dev:staging` — local app against cloud Supabase + cloud FalkorDB. `LIA_CORPUS_SOURCE=supabase`, `LIA_GRAPH_MODE=falkor_live`.
- `npm run dev:production` — Railway-hosted. Script exits locally; deploy via `railway up`.
- `npm run dev:check` / `npm run dev:staging:check` — run the preflight only (no server).

The launcher (`scripts/dev-launcher.mjs`) owns the per-mode env flags — **do not hardcode `LIA_CORPUS_SOURCE` / `LIA_GRAPH_MODE` into `.env.local` or `.env.staging`**.

### Tests

- `npm run test:health` — golden health: build public UI bundle + focused backend smokes + frontend health vitest + e2e playwright.
- `npm run test:health:fast` — same minus e2e.
- `npm run test:backend` — the curated backend smoke set (`test_background_jobs.py`, `test_phase1_runtime_seams.py`, `test_phase2_graph_scaffolds.py`, `test_phase3_graph_planner_retrieval.py`, `test_ui_server_http_smokes.py`).
- `npm run test:frontend` / `npm run test:frontend:all` / `npm run test:e2e` — frontend-only vitest / full vitest / playwright.
- `make test-batched` — **the only sanctioned way to run the full Python suite.** Runs pytest in 120 batches with stall detection. There is a `conftest` guard that aborts if >20 test files are collected without `LIA_BATCHED_RUNNER=1`, to prevent OOM.
- Single Python test: `PYTHONPATH=src:. uv run pytest tests/test_retriever_falkor.py -q` (or `-k <pattern>` for a single case).
- Evals: `make eval-c-gold` (threshold 90), `make eval-c-full` (batched + retrieval eval + gold).
- Preflight / dependency probe only: `make smoke-deps`.

### Build artifacts and Supabase sync

- `make phase2-graph-artifacts` — build the artifact bundle from `knowledge_base/` into `artifacts/`.
- `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` — same build + run `SupabaseCorpusSink`. **Required before `dev:staging` can serve answers from cloud.** Idempotent; embeddings stay `NULL` (filled by `embedding_ops.py` on a follow-up pass).

### Supabase local stack

`make supabase-start` / `supabase-stop` / `supabase-reset` / `supabase-status`. After a fresh `db reset`, run `PYTHONPATH=src:. uv run python scripts/seed_local_passwords.py` (every `@lia.dev` user → password `Test123!`).

For full local↔cloud parity of the **canonical-norms catalog** (`norms`, `norm_vigencia_history`, `norm_citations`, `sub_topic_taxonomy`), use `scripts/cloud_promotion/sync_norms_cloud_to_local.py` (mirrors the four tables cloud→local via PostgREST upsert; idempotent on natural keys) followed by `scripts/cloud_promotion/project_norms_to_falkor.py` + `scripts/canonicalizer/sync_vigencia_to_falkor.py --target production` (projects the local Supabase rows into local Falkor as `:Norm` nodes + `IS_SUB_UNIT_OF` / `MODIFIED_BY` / `DEROGATED_BY` / `INEXEQUIBLE_BY` / `CONDITIONALLY_EXEQUIBLE_BY` edges). The `vigencia_to_falkor` sync's reported edge count is `len(statements)`, not actual writes — pass `strict=True` through `GraphClient.execute` or verify per-rel-type with `MATCH ()-[r:KIND]->() RETURN count(r)` after the run. Local docker corpus tables (`documents`, `document_chunks`) stay empty by design — `LIA_CORPUS_SOURCE=artifacts` reads chunks from the filesystem bundle in `artifacts/`. The catalog backbone (Norm nodes + vigencia edges + sub-topic taxonomy) IS expected in local Postgres + Falkor so dev work that traverses the regulatory graph reflects the same topology as staging/prod.

## Repository Layout

- `src/lia_graph/` — Python backend. Entrypoints via `pyproject.toml`: `lia-ui` (`ui_server.py`), `lia-graph-artifacts` (`ingest.py`), `lia-deps-check` (`dependency_smoke.py`).
  - `pipeline_d/` — the served runtime; see "Hot Path" below.
  - `pipeline_c/` — legacy pipeline, still wired for contracts and shared plumbing. `pipeline_router.py` routes between them.
  - `normativa/` and `interpretacion/` — **surface-specific** orchestration/synthesis/assembly. These are parallel to `pipeline_d`'s `main chat` facades, not hidden behind them.
  - `ingestion/` — build-time corpus ingestion (includes `supabase_sink.py`).
  - top-level modules — auth (`password_auth.py`, `platform_auth.py`, `service_account_auth.py`), `ui_*_controllers.py` (HTTP handlers fanning out from `ui_server.py`), storage (`supabase_client.py`, `*_store.py`), domain helpers.
- `frontend/` — Vite + TypeScript UI. Built with `npm run frontend:build` (which is `npm --prefix frontend run build:public`). Tested with vitest + Playwright.
- `scripts/dev-launcher.mjs` — the run-mode entrypoint. Owns env selection, preflight, and the `LIA_*` flag matrix.
- `supabase/migrations/` — squashed baseline (`20260417000000_baseline.sql` + `20260417000001_seed_users.sql`) plus post-baseline files (e.g. `20260418000000_normative_edges_unique.sql`). Pre-squash files are in `_archive/` for reference — **do not replay them**.
- `artifacts/` — filesystem corpus bundle served in dev mode (`canonical_corpus_manifest.json`, `parsed_articles.jsonl`, `typed_edges.jsonl`, etc.).
- `tests/` — pytest suite. Run via `make test-batched` for the full run; single files directly with `uv run pytest`.
- `evals/` — retrieval/gold benchmarks.
- `docs/` — `guide/` (canonical runtime docs), `architecture/FORK-BOUNDARY.md`, `build/buildv1/` (ingestion/graph-build docs), `state/` (task state ledgers), `deprecated/old-RAG/` (historical, not active steering).

## Runtime Read Path (Env v2026-05-13-fix-v14-1-anchor-gate-and-cq-heuristics)

| Mode | `LIA_CORPUS_SOURCE` | `LIA_GRAPH_MODE` | Where chunks come from | Where graph traversal runs |
|---|---|---|---|---|
| `npm run dev` | `artifacts` | `artifacts` | filesystem artifacts | local docker FalkorDB (parity only) |
| `npm run dev:staging` | `supabase` | `falkor_live` | cloud Supabase (`hybrid_search` RPC) | cloud FalkorDB (`LIA_REGULATORY_GRAPH`) |
| `npm run dev:production` | inherits Railway env | inherits Railway env | mirrors staging | mirrors staging |

Every `PipelineCResponse.diagnostics` carries `retrieval_backend` and `graph_backend` — use them to confirm which adapters served a turn. If staging ever returns `retrieval_backend=artifacts`, the launcher flags drifted.

### Active runtime flags (launcher defaults across all three modes; shell override still wins)

**Long-standing flags:**

- `LIA_LLM_POLISH_ENABLED=1` — polish on.
- `LIA_RERANKER_MODE=live` — flipped from `shadow` on 2026-04-22 (internal-beta risk-forward). Adapter falls back to hybrid when `LIA_RERANKER_ENDPOINT` is unset.
- `LIA_QUERY_DECOMPOSE=on` — multi-`¿…?` fan-out.
- `LIA_SUBTOPIC_BOOST_FACTOR=1.5`.

**Promoted to enforce 2026-04-25 ("no off flags" directive):**

- **`LIA_TEMA_FIRST_RETRIEVAL=on`** — re-flipped after taxonomy v2 + K2 path-veto cleared SME 30Q gate (`docs/aa_next/gate_9_threshold_decision.md`, `next_done.md`).
- **`LIA_EVIDENCE_COHERENCE_GATE=enforce`** — coherence gate refuses on cross-topic contamination.
- **`LIA_POLICY_CITATION_ALLOWLIST=enforce`** — per-topic citation allow-list.
- **`LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE=enforce`** — next_v3 §7 path-veto + 6 mutex rules.

**fix_v7 (2026-05-11):**

- **`LIA_QUERY_EMBEDDINGS_ENABLED=1`** (§3b) — `gemini-embedding-001` replaces the legacy zero-vector so the vector half of RRF is live. Rollback: `=0`.
- **`LIA_TOPIC_GATE_MODE=enforce`** (§3c) — synthesis-time cross-topic content gate. Rollback: `=off`.

**fix_v8 (2026-05-11):**

- **`LIA_POLISH_REJECTED_FALLBACK_MODE=enforce`** (§3a) — when polish returns `mode=rejected`, the orchestrator assembles a substantive answer from `GraphNativeAnswerParts` via `pipeline_d/answer_polish_rejected_fallback.py` instead of returning the bare question-echo template. Rollback: `=off`.

**fix_v10_may Phase 10B (2026-05-11):**

- **`LIA_INTERPRETATION_SOURCE=supabase`** for `dev:staging` + `dev:production`, **`filesystem`** for `npm run dev` — Interpretación de Expertos panel routes through `hybrid_search(filter_knowledge_class='interpretative_guidance')` via `interpretacion/retriever_supabase.py`. Filesystem path stays as safety floor for offline dev; errors propagate per the no-silent-fallback non-negotiable. Diagnostic `interpretation_backend ∈ {supabase, filesystem}` is whitelisted in `ui_chat_payload.py`.

**fix_v13_may (2026-05-13) — dedicated práctica retrieval lane:**

- **`LIA_PRACTICA_SOURCE=supabase`** for `dev:staging` + `dev:production`, **`disabled`** for `npm run dev` (§5) — dedicated `practica_erp` retrieval lane in `src/lia_graph/practica/retriever_supabase.py` runs in parallel to the unified `hybrid_search` call. Reserves the top-K `practica_erp` chunks for `build_recommendations` so the **Recomendaciones Prácticas** section is fed by real operational-guidance chunks before the v12 article-derived fallback. Errors propagate as `practica_backend="error"`, never silent filesystem fallback. `filesystem` value reserved for a future offline fallback (§7 deferred) and currently raises `NotImplementedError`.
- **`LIA_PRACTICA_RESERVED_SLOTS=3`** (§5) — top-K práctica chunks reserved for the section. Matches `build_recommendations`'s `tuple(lines[:3])` cap. Floors at 0 (disable), caps at 8.
- **`LIA_PRACTICA_BOOST_FACTOR=1.0`** (§5) — default flipped from `1.5` in v12; the v13 dedicated práctica lane supersedes the soft-boost mechanism. SQL parameter + Python plumbing stay wired as a one-flag rollback path: setting to `1.5` reinstates v12 behavior on top of v13 disabled.

**fix_v14_may §3 + §4 (2026-05-13) — sprint v14.1 anchor gate + chunk-quality heuristics:**

- **`LIA_LEGAL_ANCHOR_GATE_MODE=enforce`** (§3) — flipped from `shadow` after sprint v14.1 panel-judge (operator-amended decision rule: net improvement + zero new hallucinations). Topic-allowlist filter applied to `build_legal_anchor_lines` output; drops items whose `art:<num>` form is not in the primary topic's `allowed_prefixes` from `config/topic_norm_allowlist.json`. v14.1 measurement: 41/42 turns gate fired, 41 items dropped, 0 new hallucinations in 3 regressed turns. Rollback: `=shadow` (runs but does not alter output) or `=off`.
- **`LIA_CHUNK_QUALITY_HEURISTIC_MODE=enforce`** (§4) — flipped from `shadow`. Unified heuristics in `pipeline_d/chunk_quality_heuristics.py` demote chunk rows carrying corpus-build artifacts (portal-login boilerplate, cross-topic operational leaks, captions, section-heading numerals). Floored at 0.1 per Invariant I5. Rollback: `=shadow` or `=off`.

**Ingest-pipeline knobs (next_v3 phases 2a/2b/2c):**

- `LIA_INGEST_CLASSIFIER_WORKERS=4` (held at 4 until `TokenBudget` primitive ships per next_v4 §10.1).
- `LIA_INGEST_CLASSIFIER_RPM=300`.
- `LIA_SUPABASE_SINK_WORKERS=4`.
- `FALKORDB_QUERY_TIMEOUT_SECONDS=30`.
- `FALKORDB_BATCH_NODES=500`.
- `FALKORDB_BATCH_EDGES=1000`.

### Runtime-shape additions (no env flag)

**2026-04-25 (next_v4 §3 + §4 + §5):**

- Conversational-memory staircase Levels 1+2: `ConversationState.prior_topic` / `prior_subtopic` / `topic_trajectory` / `prior_secondary_topics`; classifier soft-tiebreaker on `prior_topic`.
- `comparative_regime_chain` query mode: `config/comparative_regime_pairs.json` + `pipeline_d/answer_comparative_regime.py`.

**2026-05-11 (fix_v7 §3a + §3c, SQL/wire-up):**

- Migration `supabase/migrations/20260512000000_topic_filter_soft.sql` adds `boost_topic` to `hybrid_search` so the topic boost is decoupled from `filter_topic` (chat path passes `filter_topic=None` always).
- `pipeline_d/answer_topic_gate.py` + `config/topic_norm_allowlist.json` filter off-topic-norm bullets out of the template before polish runs.

**2026-05-11 fix_v8 — five surgical fixes:**

- (§3a) Substantive polish-rejected fallback (`pipeline_d/answer_polish_rejected_fallback.py`) — when polish rejects, orchestrator assembles a real answer from `GraphNativeAnswerParts`. Gate re-applied to fallback output.
- (§3b) Polish observability — `polish.applied` trace step + `response.diagnostics.polish_mode` / `polish_skip_reason` (whitelisted in `ui_chat_payload.py`).
- (§3e) Polish prompt rewrite — explicit DIRECTIVA PRIMARIA + `ARTÍCULOS PERMITIDOS` / `REFORMAS Y NORMAS PERMITIDAS` allowlists in `_build_polish_prompt`.
- (§3f) `gemini-flash` temperature `0.1 → 0.0` in `config/llm_runtime.json` (chat-polish path only; canonicalizer DeepSeek stays at 0.1).
- (§3g) `planner.py` anchors Art. 115 ET explicitly for ICA-deduction queries.

**2026-05-11 fix_v10_may:**

- (10A) `supabase_sink.write_chunks` inherits `knowledge_class` from parent doc captured during `write_documents` instead of hardcoding `"normative_base"`. Cloud backfill applied to LIA_Graph: 2,275 chunks retagged (812 interpretative_guidance + 1,463 practica_erp). G2 sink-level parity invariant tracks `chunks_default_class_count`. SME §1.G 36-Q post-backfill panel byte-identical to baseline (34/36 acc+, 26 strong, 0 per-question deltas).
- (10B) Interpretación de Expertos panel routes through `hybrid_search` via new `interpretacion/retriever_supabase.py`; `orchestrator._retrieve_interpretation_docs` is a thin dispatcher on `LIA_INTERPRETATION_SOURCE`.
- (§9.3) New `documents.provider_labels (text[])` column + GIN index via migration `20260513000000_documents_provider_labels.sql`. Sink reads `document["provider_labels"]`, strips/dedupes, writes the cleaned list.

**2026-05-11 fix_v11_may Phase 11A:**

- Trust-tier prioritization in `interpretacion/retriever_supabase.py::_group_chunks_by_doc` — `trust_tier_weight=0.30`. Score = `base * (1 + ref_boost·hits) * (1 + tier_weight·tier_bonus)` with `tier_bonus ∈ {high:2.0, medium:1.0, low:0.0}`.
- New `config/provider_trust_tiers.json` (52 entries). Backfill `scripts/diagnostics/backfill_v11_trust_tiers.py` also writes `documents.provider_labels` from local markdown `> Fuentes secundarias consultadas:`.
- Cloud backfill: 65 chunks/8 docs → high tier; 747 chunks/97 docs → medium.
- Mini-panel net effect: 0pt (12/21 = 57.1%, identical to v10 baseline). Diagnosis: lever operates at chunk-grouping but downstream `synthesize_expert_panel` rerank+filter dominates final surface. Code stays shipped — Phase 11B will consume `trust_tier` via `INTERPRETS ORDER BY trust_tier DESC LIMIT 8`.
- SME runner hardened (single shared ChatClient + `_RateLimit429Feeler`) against the `/api/public/session` 429 burst.

**2026-05-11 fix_v11_may Phase 11B (DISCARDED per gate-6):**

- `LIA_INGEST_INTERPRETATION_NODES=enforce` (loader idempotent, kept).
- **`LIA_PLANNER_INTERPRETATION_ANCHOR=off`** — default flipped `on → off`. Three refinement attempts (§15 judge fix, §16 Option A soft veto, §17 hybrid count threshold) all landed at or below the 12/21 baseline. Cloud Falkor InterpretationNode subgraph (105 nodes + 586 INTERPRETS + 105 COVERS_TOPIC) stays in place; modules `graph/interpretation_loader.py` + `interpretacion/anchor_resolver.py` stay in repo behind the off flag.
- **Kept (independent correctness fix):** §15 `pipeline_c.orchestrator.generate_llm_strict` tuple-contract fix — pre-fix returned a 4-key dict; every caller did `text, diag = ...` unpacking; silently crashed `expert_rerank.judge` + 3 other LLM call sites for months. Verified 21/21 `judge.mode = 'llm'` post-fix. 12 regression tests at `tests/test_pipeline_c_generate_llm_strict.py`. Full record at `docs/re-engineer/fix/fix_v11_may.md §17`.

### Diagnostic surface

Nine retrieval-diagnostic keys lifted to top-level `response.diagnostics` (next_v3 phase 1).

## LLM provider split — chat vs canonicalizer (2026-04-29)

`config/llm_runtime.json` lists provider preference for the whole repo. **Chat and canonicalizer have different needs and the wrong default broke chat:**

* **Chat path** (topic resolver in `topic_router._classify_topic_with_llm`, polish in `answer_llm_polish`) needs a fast, structured-JSON-faithful model. Topic-classifier prompt requires a strict `{"primary_topic":...,"confidence":...}` JSON object back, with an 8-second timeout per call.
* **Canonicalizer path** (vigencia extraction, classifier, etc.) needs a long-context, schema-following model and runs at high RPM as a batch job. DeepSeek-v4-flash and v4-pro fit this well (cheap, 1M context, on a 75% discount window through 2026-05-05).

**The default `provider_order` in `config/llm_runtime.json` puts `gemini-flash` first** so chat works correctly. The canonicalizer keeps DeepSeek by overriding via the existing `LIA_VIGENCIA_PROVIDER=deepseek-v4-flash` env knob (set explicitly by every canonicalizer launch script). 

The reason for this split: DeepSeek-v4-pro is a *reasoning model* that returns `reasoning_content` (chain-of-thought) but often empty `message.content` for short structured-output prompts. The adapter at `llm_runtime.py:198` raises `RuntimeError("DeepSeek response missing message content.")`; the topic resolver swallowed the exception and silently fell through to the keyword fallback, mis-routing every multi-domain SME query to the parent topic `declaracion_renta`. This caused the §1.G 36-Q SME panel to drop from 21/36 to 8/36 acc+ on 2026-04-29. After flipping providers back, the panel returned to 22/36 acc+ with zero ok→zero regressions. Full diagnosis: `docs/re-engineer/fix/fix_v1_diagnosis.md`. Ongoing work to push 22 → 24/36: `docs/re-engineer/fix/fix_v1.md` (sub-query LLM-skipped path).

**If you flip provider order again, re-run the §1.G panel** (`scripts/eval/run_sme_parallel.py --workers 4`, ~5 min wall) before merging.

## Retrieval-stage deep trace (2026-04-29)

`tracers_and_logs/pipeline_trace.py` is a context-local collector that writes one JSONL line per retrieval stage to `tracers_and_logs/logs/pipeline_trace.jsonl` AND attaches the snapshot to `response.diagnostics["pipeline_trace"]` for every served chat. PII-safe by design (no chunk text, no answer text, only stage names + counts + truncated decision details). Whitelisted in `ui_chat_payload.filter_diagnostics_for_public_response` so eval traces survive the public-response strip.

Stage coverage: topic resolution (every silent return-None branch), planner, retriever (hybrid_search input/output, anchor merge, vigencia v3 demotion kept/dropped/demoted), reranker, coherence gate, citation allow-list, LLM polish (provider/adapter/elapsed). Read with `jq` against `tracers_and_logs/logs/pipeline_trace.jsonl` or directly in the eval JSON's `response.diagnostics.pipeline_trace.steps[*]`.

## Hot Path (main chat)

1. `src/lia_graph/ui_server.py`
2. `src/lia_graph/pipeline_router.py`
3. `src/lia_graph/topic_router.py`
4. `src/lia_graph/pipeline_d/orchestrator.py` — reads `LIA_CORPUS_SOURCE` + `LIA_GRAPH_MODE`, dispatches
5. `src/lia_graph/pipeline_d/planner.py`
6. Retriever (one of):
   - `pipeline_d/retriever.py` — artifact BFS (dev default)
   - `pipeline_d/retriever_supabase.py` — Supabase `hybrid_search` (staging chunks half)
   - `pipeline_d/retriever_falkor.py` — cloud FalkorDB Cypher BFS (staging graph half). Errors **propagate** — never silently falls back to artifacts.
7. `pipeline_d/answer_support.py` — practical enrichment extraction
8. `pipeline_d/answer_synthesis.py` — **stable facade** for synthesis
9. `pipeline_d/answer_assembly.py` — **stable facade** for assembly

Facade implementation modules (edit the narrow one that owns the behavior):
`answer_synthesis_sections.py`, `answer_synthesis_helpers.py`, `answer_first_bubble.py`, `answer_followup.py`, `answer_inline_anchors.py`, `answer_historical_recap.py`, `answer_comparative_regime.py` (next_v4 §5 — `comparative_regime_chain` table renderer), `answer_topic_gate.py` (fix_v7 §3c — cross-topic content gate run inside `compose_main_chat_answer`), `answer_shared.py`, `answer_policy.py`.

## Fast Decision Rule

- wrong norms or wrong workflow → planner or retriever
- right evidence but weak practical substance → `answer_support.py`
- `**Recomendaciones Prácticas**` section reads as normative-voiced bullets instead of operational guidance → check `response.diagnostics.practica_backend` + `practica_reserved_count`. If `practica_backend="supabase"` AND `practica_reserved_count >= 1` → tune the bullet-extraction helper at `pipeline_d/answer_synthesis_practica.py::_candidate_lines_from_chunk`. If `practica_reserved_count == 0` with `practica_backend="supabase"` → corpus or topic-routing issue (the lane fetched but everything dropped at vigencia / grouping); read `practica.retriever.*` trace stages. If `practica_backend="error"` → RPC outage, surface in `practica_error_kind`; rollback path is `LIA_PRACTICA_SOURCE=disabled` (+ optional `LIA_PRACTICA_BOOST_FACTOR=1.5` to reinstate v12 soft-boost)
- wrong tone, shape, or visible organization → `answer_policy.py` or the `main chat` assembly/synthesis modules
- answer cites off-topic norms (e.g. pérdidas-fiscales bullets in a beneficio-auditoría answer) → `config/topic_norm_allowlist.json` (allowed prefixes per topic) or `pipeline_d/answer_topic_gate.py` (gate logic). Toggle with `LIA_TOPIC_GATE_MODE=off`
- polish was rejected (`diagnostics.polish_mode=rejected`) and the answer is essentially empty (~120 chars) → `pipeline_d/answer_polish_rejected_fallback.py` (substantive-fallback assembler) or `pipeline_d/answer_synthesis_sections.py` (the underlying part builders feeding the assembler). Toggle with `LIA_POLISH_REJECTED_FALLBACK_MODE=off`
- vector half of RRF looks dead / `embedding_mode != "ok"` on trace → `retriever_supabase._query_embedding` + `lia_graph.embeddings.get_query_embedding`. Rollback with `LIA_QUERY_EMBEDDINGS_ENABLED=0`
- cross-topic anchor missing on staging despite being in the corpus → check `retriever.hybrid_search.in.filter_topic` is `None` and `boost_topic` carries the routed topic. Otherwise `retriever_supabase.py` lines 258–304 or `supabase/migrations/20260512000000_topic_filter_soft.sql`
- expert panel surfaces wrong / off-topic interpretation cards → as of fix_v11_may §17 DISCARD, the expert panel runs through the Python `article_index` fallback (Phase 10C v0). Bottleneck is the assembly-layer off_topic-pattern veto at `synthesis_helpers.select_interpretation_candidates`; pattern-axis tuning was exhausted in v11 (judge fix + Option A soft veto + hybrid threshold; all ≤ baseline). Future fix needs a semantic relevance signal at the filter layer (embedding cosine, learned ranker) — fresh-plan task. The Falkor anchor path stays in repo behind `LIA_PLANNER_INTERPRETATION_ANCHOR=on` for diagnostic A/B work
- runtime wiring change → `orchestrator.py` (and only then)
- dev ≠ staging → check `response.diagnostics.retrieval_backend` / `graph_backend`, then `scripts/dev-launcher.mjs` + the env matrix in `docs/orchestration/orchestration.md`
- `Normativa` / `Interpretación` UX work → their own packages (`src/lia_graph/normativa/`, `src/lia_graph/interpretacion/`). **Never** route their requirements into `main chat` assembly.

## Surface Boundaries

`main chat`, `Normativa`, and future `Interpretación` are **distinct surfaces** with parallel orchestration/synthesis/assembly modules. Shared graph/evidence utilities may stay shared; visible assembly must stay surface-specific. `answer_synthesis.py` / `answer_assembly.py` are not the backend for the Normativa modal.

## Non-Negotiables

- Keep docs, code, and the `/orchestration` HTML map (`frontend/src/app/orchestration/shell.ts`, `frontend/src/features/orchestration/orchestrationApp.ts`) aligned.
- Prefer focused module edits over monolithic rewrites. Make changes in the narrowest module that owns the behavior.
- If architecture changes, update `docs/orchestration/orchestration.md` (including the versioned env matrix) **in the same task** as the code change.
- If a `LIA_*` env or launcher flag changes, bump the env matrix version in the orchestration guide, add a change-log row, and update the mirror tables in `docs/guide/env_guide.md`, this file, and the `/orchestration` status card.
- The Falkor adapter must keep propagating cloud outages — **no silent artifact fallback** on staging.
- **Cloud retirements are CLI-explicit only.** Once a doc lives in cloud Supabase + Falkor, removing it requires `lia-graph-artifacts --additive --allow-retirements` from a CLI typed by an operator. The GUI additive flow (`/api/ingest/additive/preview` + `/apply`) and any non-explicit CLI invocation MUST pass `allow_retirements=False` (the default). Adding to the corpus is the friendly path; deletion is the deliberate one. Out-of-sync local `knowledge_base/`, partial Dropbox sync, machine swaps and similar local-disk drift must NEVER silently retire production docs. The disk-vs-baseline `removed` bucket surfaces as a yellow diagnostic in the preview, not as a delete action. Enforced at `src/lia_graph/ingestion/delta_runtime.py::materialize_delta` (parameter `allow_retirements`, defaults to False; strips `delta.removed` to `()` before sink + Falkor when False).
- `PipelineCResponse.diagnostics` must always carry `retrieval_backend` and `graph_backend`.
- Never run the full pytest suite in one process — use `make test-batched`. The `tests/` conftest guard aborts without `LIA_BATCHED_RUNNER=1`.
- Do not inherit old-RAG assumptions (indexing, tagging, vocab design, reranking, chunk orchestration, cache strategy). Old-RAG docs under `docs/deprecated/` are archaeology, not active steering.
- **Idea vs. verified improvement — mandatory six-gate lifecycle for every `docs/aa_next/**` step.** RAG is complex science; "improvements" misbehave and regress all the time. Unit tests green ≠ improvement. Every pipeline change must pass all six gates in the plan doc **before any code is written**: (1) describe the good idea in one sentence; (2) plan the implementation in the narrowest module; (3) define a measurable minimum success criterion with numbers; (4) define HOW to test the criterion — including development needed, conceptualization, running environment, actors/interventions required (engineer / operator / SME / end user), and the numeric decision rule; (5) greenlight requires BOTH technical tests AND end-user validation against real data at the layer an accountant experiences; (6) refine-or-discard — if validation fails, either iterate or explicitly discard (kept in record, never silently rolled back). Status lifecycle: 💡 idea → 🛠 code landed → 🧪 verified locally → ✅ verified in target environment → ↩ regressed-discarded. When target-env verification is infeasible locally, mark 🧪 and name the specific run still needed. Full policy in `docs/aa_next/README.md`.

## Fail Fast, Fix Fast — operations canon

For any operation against real systems that touches ≥100 records (cloud promotions, batch ingests, evals, embedding backfills, scraper cascades, migrations): instrument fail-fast thresholds **before** launching, treat the first abort as **diagnosis material** (not a blocker), fix the root cause, then re-run until **stable**. Do not let cascades crawl through thousands of rows accumulating errors.

Operating rules:

1. **Instrument before launching.** Every detached job that does ≥100 ops needs a fail-fast gate: an absolute error count AND an error-rate gate (default `>50 errors OR >10% rate after 100 ops → abort`). Check **between sub-batches**, not after the whole job. Surface the threshold + current error rate in the heartbeat so the operator sees how close it is.
2. **First abort = diagnosis signal, not retry signal.** When fail-fast trips, do NOT raise the threshold, NOT add `--continue-on-error`, NOT relaunch the same code. Read the audit log, group errors by root cause (failure-pattern Counter), fix the underlying issue (data shape, code bug, missing migration, drifted contract), dry-validate the fix on the full input set, then re-launch.
3. **"Stable" means past the prior failure point with the new error count at or below the dry-run prediction.** One clean heartbeat is not stable. One clean cycle past the bad spot is.
4. **Idempotency is mandatory.** Every long-running write op must be re-runnable with no harm to already-completed work (UPSERT on natural keys, idempotency-key checks, sentinel files, deterministic run-ids). Without it, "fail fast" becomes "lose work fast."
5. **Audit logs, not just stdout.** The heartbeat must read structured per-row audit (JSONL outcome rows), not just count log lines. Categorize errors; don't lump them. The error-pattern bucket IS the diagnosis.
6. **Diagnose at the audit layer, not the symptom.** A row exception saying "DB constraint violated" means: read the failing rows, find the data shape they share, fix the producer (writer / canon / extractor) — not the constraint, not the threshold.
7. **Preflight before volume.** When a cascade has independent sub-runs (batches/files/generations), ingest **one record per sub-run** through the full path (writer + DB constraints + downstream sinks) BEFORE the main loop. Use the real writer + real DB (not a dry-run client) — DB-level bugs (CHECK, FK, RLS) only surface when the row hits cloud Postgres. Use the SAME run-id as the main loop so its idempotency-key matches and the volume loop skips already-ingested probe rows. Abort the cascade on any preflight error. Cost: ~1 minute for ~40 batches; saves ~25 minutes per fail-fast trip.
8. **Risk-first ordering.** When sub-runs have heterogeneous risk profiles, process novelty / historical-failure batches FIRST. High-risk = anything touching a code path / data shape / DB constraint that hasn't been exercised in this environment before (new prefixes, new sources, batches the previous attempt got stuck on). A failure in the first 5 minutes is recoverable; a failure at minute 25 of a 30-minute run is not. The default alphabetical / chronological / size-ordered sweep is almost always wrong — order by risk, not by the dimension that happens to make sub-runs easy to enumerate.

This is paired with the six-gate lifecycle: gates 4 (test plan) and 6 (refine-or-discard) cover this loop for pipeline changes. For ops work (ingests, promotions, evals, backfills, cascades), this section IS the lifecycle. The reference implementation is `scripts/cloud_promotion/{run.sh,heartbeat.py}` (next_v7 P1) — see `RISK_FIRST=1` / `PREFLIGHT=1` env-flags. Full canonicalizer-specific learning: `docs/learnings/canonicalizer/preflight-and-risk-first-batching-2026-04-29.md`. Process companion: `docs/learnings/process/risk-first-cascade-design.md`.

## Long-running Python processes — always detached + heartbeat, never ad-hoc

For **any** background Python process expected to take more than ~2 minutes (reingests, embedding backfills, subtopic-miner batches, evals, long Gemini sweeps): the operator should never have to ask for progress monitoring. Default to this pattern, applied automatically:

1. **Launch detached.** Use the `scripts/launch_phase9a*.sh` shape — `nohup` + `disown` + direct `>log 2>&1` redirects (NO `| tee` pipe; tee breaks on SIGHUP and has already crashed one run this way). The process must survive CLI close, Claude exit, and shell disconnect. Reparenting to init (`PPID=1`) is the success signal.
2. **Arm a 3-minute heartbeat** via `CronCreate` that invokes `scripts/monitoring/ingest_heartbeat.py` with the run's `--delta-id`, `--start-utc`, `--total`, and pre-run baselines. See `scripts/monitoring/README.md` for the full cron prompt template, transition logic, and kill-switches.
3. **Anchor progress to `logs/events.jsonl`**, not the `--json` summary log (which buffers until termination and is useless mid-run).
4. **Render in Bogotá AM/PM** per the time-format memory, using the markdown table shape the heartbeat script already emits.
5. **Respect phase-aware silence**: the heartbeat knows `sink_writing` and `falkor_writing` legitimately emit no per-item events. Only `classifying` should tick continuously; only there does `FRESH > 180s` signal a stall.
6. **Kill-switches** (the caller must enforce): process gone + no `cli.done` → silent death → STOP loop and surface events/log, do NOT retry. `run.failed` / `ERRORS > 0` → STOP and surface. `cli.done` → STOP and declare complete.

Do not add a new `--json`/tee/background variant when launching a long Python job; copy the launcher + heartbeat shape instead.

If there is any doubt, follow `AGENTS.md` and treat it as the repo-level operating guide.
