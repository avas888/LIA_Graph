# CLAUDE.md

Quickstart for Claude-family agents working in `Lia_Graph`, a graph-native RAG product shell for Colombian accounting.

## Canonical Guidance

Read these before changing the served runtime. If code and docs disagree, reconcile to `docs/orchestration/orchestration.md` — never the other way around.

1. `AGENTS.md` — canonical repo-level operating guide (layer ownership, surface boundaries, doc discipline)
2. `docs/orchestration/orchestration.md` — end-to-end runtime map + **authoritative** versioned env/flag matrix + change log
3. `docs/guide/chat-response-architecture.md` — companion source of truth for how the `main chat` answer is shaped
4. `docs/guide/env_guide.md` — operational counterpart: run modes, env files, squashed migration baseline, test accounts, corpus refresh
5. `docs/re-engineer/fix/*.md` — per-fix rationale, panel results, rollback notes. The flag table below points to these for context.

## Commands

### Run the app

- `npm run dev` — local app + local Supabase docker + local FalkorDB docker. Fully offline. `LIA_CORPUS_SOURCE=artifacts`, `LIA_GRAPH_MODE=artifacts`.
- `npm run dev:staging` — local app against cloud Supabase + cloud FalkorDB. `LIA_CORPUS_SOURCE=supabase`, `LIA_GRAPH_MODE=falkor_live`.
- `npm run dev:production` — Railway-hosted. Script exits locally; deploy via `railway up`.
- `npm run dev:check` / `npm run dev:staging:check` — preflight only.

`scripts/dev-launcher.mjs` owns per-mode env flags. **Do not hardcode `LIA_CORPUS_SOURCE` / `LIA_GRAPH_MODE` into `.env.local` or `.env.staging`.**

### Tests

- `npm run test:health` / `test:health:fast` — golden health (UI bundle + backend smokes + frontend vitest + e2e; fast skips e2e).
- `npm run test:backend` — curated backend smoke set.
- `npm run test:frontend` / `test:frontend:all` / `test:e2e`.
- `make test-batched` — **only sanctioned way to run the full Python suite.** 120 batches + stall detection. `tests/` conftest aborts if >20 files collected without `LIA_BATCHED_RUNNER=1`.
- Single Python test: `PYTHONPATH=src:. uv run pytest tests/<file>.py -q` (or `-k <pattern>`).
- Evals: `make eval-c-gold` (threshold 90), `make eval-c-full`.
- Preflight only: `make smoke-deps`.

### Build artifacts + Supabase sync

- `make phase2-graph-artifacts` — build artifact bundle from `knowledge_base/` into `artifacts/`.
- `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` — same + `SupabaseCorpusSink`. **Required before `dev:staging` can serve cloud answers.** Idempotent; embeddings stay `NULL` (filled later by `embedding_ops.py`).

### Supabase local stack

- `make supabase-start` / `supabase-stop` / `supabase-reset` / `supabase-status`.
- After `db reset`: `PYTHONPATH=src:. uv run python scripts/seed_local_passwords.py` (every `@lia.dev` user → `Test123!`).
- Local↔cloud parity of canonical-norms catalog (`norms`, `norm_vigencia_history`, `norm_citations`, `sub_topic_taxonomy`):
  1. `scripts/cloud_promotion/sync_norms_cloud_to_local.py` — cloud→local upsert, idempotent on natural keys.
  2. `scripts/cloud_promotion/project_norms_to_falkor.py` — local Supabase rows → local Falkor `:Norm` + `IS_SUB_UNIT_OF`.
  3. `scripts/canonicalizer/sync_vigencia_to_falkor.py --target production` — writes `MODIFIED_BY` / `DEROGATED_BY` / `INEXEQUIBLE_BY` / `CONDITIONALLY_EXEQUIBLE_BY` into local Falkor.
- **Gotcha**: `vigencia_to_falkor` reports `len(statements)`, not real writes. Verify with `MATCH ()-[r:KIND]->() RETURN count(r)` per rel-type, or pass `strict=True` through `GraphClient.execute`.
- **Why local catalog parity matters**: local corpus tables (`documents`, `document_chunks`) stay empty by design — artifacts mode reads from the filesystem bundle. The Norm + vigencia + sub-topic backbone IS expected locally so graph traversals reflect staging/prod topology.

## Repository Layout

- `src/lia_graph/` — Python backend. Entrypoints in `pyproject.toml`: `lia-ui`, `lia-graph-artifacts`, `lia-deps-check`.
  - `pipeline_d/` — served runtime (see Hot Path).
  - `pipeline_c/` — legacy, still wired for contracts. `pipeline_router.py` routes between them.
  - `normativa/`, `interpretacion/`, `practica/` — **surface-specific** orchestration/synthesis. Parallel to `pipeline_d`'s `main chat` facades, not nested.
  - `ingestion/` — build-time corpus ingestion (`supabase_sink.py`).
  - top-level — auth (`password_auth.py`, `platform_auth.py`, `service_account_auth.py`), `ui_*_controllers.py`, storage (`supabase_client.py`, `*_store.py`).
- `frontend/` — Vite + TypeScript. `npm run frontend:build`. Vitest + Playwright.
- `scripts/dev-launcher.mjs` — run-mode entrypoint, owns env + `LIA_*` flag matrix.
- `supabase/migrations/` — squashed baseline (`20260417000000_baseline.sql` + `_seed_users.sql`) + post-baseline. Pre-squash in `_archive/` — **do not replay.**
- `artifacts/` — filesystem corpus bundle for dev mode.
- `tests/` — pytest; full run via `make test-batched` only.
- `evals/`, `docs/` (guide/, architecture/, build/, state/, deprecated/old-RAG/).

## Runtime Read Path (Env v2026-05-15-fix-v18-b2)

| Mode | `LIA_CORPUS_SOURCE` | `LIA_GRAPH_MODE` | Chunks from | Graph traversal |
|---|---|---|---|---|
| `npm run dev` | `artifacts` | `artifacts` | filesystem | local docker Falkor (parity only) |
| `npm run dev:staging` | `supabase` | `falkor_live` | cloud Supabase `hybrid_search` | cloud Falkor (`LIA_REGULATORY_GRAPH`) |
| `npm run dev:production` | inherits Railway | inherits Railway | mirrors staging | mirrors staging |

Every `PipelineCResponse.diagnostics` carries `retrieval_backend` + `graph_backend`. If staging ever returns `retrieval_backend=artifacts`, the launcher flags drifted.

### Active runtime flags

Launcher defaults across all three modes; shell override still wins. **Per-fix rationale, panel results, and rollback details live in `docs/re-engineer/fix/<file>.md`** — this table is the operational index.

| Flag | Default | Purpose | Rollback | Origin |
|---|---|---|---|---|
| `LIA_LLM_POLISH_ENABLED` | `1` | Polish on | `=0` | long-standing |
| `LIA_RERANKER_MODE` | `live` | Reranker on; falls back to hybrid if `LIA_RERANKER_ENDPOINT` unset | `=shadow` | 2026-04-22 |
| `LIA_QUERY_DECOMPOSE` | `on` | Multi-`¿…?` fan-out | `=off` | long-standing |
| `LIA_SUBTOPIC_BOOST_FACTOR` | `1.5` | Subtopic re-weight | numeric | long-standing |
| `LIA_TEMA_FIRST_RETRIEVAL` | `on` | Topic-first retrieval pass | `=off` | 2026-04-25 |
| `LIA_EVIDENCE_COHERENCE_GATE` | `enforce` | Refuse on cross-topic contamination | `=shadow`/`off` | 2026-04-25 |
| `LIA_POLICY_CITATION_ALLOWLIST` | `enforce` | Per-topic citation allow-list | `=off` | 2026-04-25 |
| `LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE` | `enforce` | next_v3 §7 path-veto + 6 mutex rules | `=off` | 2026-04-25 |
| `LIA_QUERY_EMBEDDINGS_ENABLED` | `1` | `gemini-embedding-001` powers vector half of RRF | `=0` | fix_v7 |
| `LIA_TOPIC_GATE_MODE` | `enforce` | Synthesis-time cross-topic content gate | `=off` | fix_v7 §3c |
| `LIA_POLISH_REJECTED_FALLBACK_MODE` | `enforce` | On polish rejection, assemble substantive answer from `GraphNativeAnswerParts` | `=off` | fix_v8 §3a |
| `LIA_INTERPRETATION_SOURCE` | `supabase` (staging/prod), `filesystem` (dev) | Interpretación panel routes through `hybrid_search` | flip value | fix_v10 §10B |
| `LIA_PRACTICA_SOURCE` | `supabase` (staging/prod), `disabled` (dev) | Dedicated `practica_erp` lane feeding **Recomendaciones Prácticas** | `=disabled` | fix_v13 §5 |
| `LIA_PRACTICA_RESERVED_SLOTS` | `3` | Top-K práctica chunks reserved for the section (floor 0, cap 8) | numeric | fix_v13 §5 |
| `LIA_PRACTICA_BOOST_FACTOR` | `1.0` | Reinstates v12 soft-boost if set to `1.5` | numeric | fix_v13 §5 |
| `LIA_LEGAL_ANCHOR_GATE_MODE` | `enforce` | Topic-allowlist filter on `build_legal_anchor_lines` | `=shadow`/`off` | fix_v14.1 §3 |
| `LIA_CHUNK_QUALITY_HEURISTIC_MODE` | `enforce` | Demotes corpus-build artifacts (boilerplate, leaks, captions, TOC, pre-Ley markers, orphan calcs, isolated software codes) | `=shadow`/`off` | fix_v14.1 §4 + fix_v18 b1 |
| `LIA_POLISH_REJECTED_FALLBACK_FILTER` | `clean` | Filters fallback bullets through quality + allowlist; abstains if evidence < 300 chars | `=legacy` | fix_v14.2 §6 |
| `LIA_POLISH_NUMERIC_DIRECTIVE` | `off` | DIRECTIVA NUMÉRICA prompt-engineering pass — REVERTED; kept as kill switch | `=on` (NOT SAFE without UVT validator) | fix_v14.2 §17 |
| `LIA_POLISH_UVT_VALIDATOR` | `enforce` | Structural `_no_invented_uvt_ranges` validator on polished tarifa output (cue-gated to Art. 240/241/242/383/908 ET) | `=shadow`/`off` | fix_v15 §3 |
| `LIA_PRACTICA_NOISE_FILTER` | `enforce` | Drops `pre_ley_lead` / `software_code_tail` / `orphan_numeric_calc` bullets in práctica section | `=shadow`/`off`/`legacy` | fix_v18 b1 §1.1; promoted fix_v21 §3.3 P3-T4 |
| `LIA_CONFLICT_RESOLVER_MODE` | `enforce` | Detects + resolves bullets with same predicate / different numeric value via A1 article-match + A2 LLM fallback | `=shadow`/`off`/`legacy` | fix_v18 b2 §1.5; promoted fix_v21 §3.3 P3-T4 |
| `LIA_TOPIC_DECOMPOSITION_MODE` | `enforce` | Bypass coherence-gate refusal on multi-domain Qs (router topic ≠ retrieved articles' dominant topic) — prepends framing line, lets synthesis+polish produce sectioned-ish answer | `=shadow`/`off` | fix_v23 §3.1 |
| `LIA_YEAR_CONSTANTS_INJECTION` | `enforce` | Injects verified UVT/SMLMV/auxilio canonical values for the detected fiscal year into the polish prompt + seeds the `_no_invented_uvt_ranges` validator | `=shadow`/`off` | fix_v23 §3.2 |
| `LIA_CITATION_SOURCE_CODE_AWARENESS` | `enforce` | Resolves cited articles to real source code (ET/CST/C.Co./Ley 43-1990/Res. DIAN/Decreto) + rejects pseudo-citations (`art. notas-y-fuentes`) at the renderer | `=off` | fix_v23 §3.3 |
| `LIA_CHUNK_QUALITY_ENTITY_FILTER` | `shadow` | Demotes chunks matching named-entity / acta-template / formulario / verbatim-audit-string leak patterns. Stays `shadow` in v23 per D-S3; v24 retires source data + promotes to enforce | `=enforce`/`off` | fix_v23 §3.4 |
| `LIA_POLISH_INPUT_PRESERVATION` | `enforce` | Two polish validators: user-stated numerics survive (catches Q10 `$3M→$2M` mutation); ≥2 distinct UVTs without explicit AG-year comparison rejected | `=shadow`/`off` | fix_v23 §3.5 |
| `LIA_POLISH_LOCALE_STYLE_COLOMBIAN` | `enforce` | Voseo-verb + `\bvos\b` pronoun regex rejection on polished output; closed verb set | `=shadow`/`off` | fix_v23 §3.6 |
| `LIA_ANCLAJE_TOPIC_GATE` | `enforce` | Anclaje Legal section filters primary+connected articles against `config/compatible_doc_topics.json` allowlist (body bullets untouched) — closes v22 P3 q01 finding | `=shadow`/`off` | fix_v23 §3.7 |
| `LIA_PLANNER_INTERPRETATION_ANCHOR` | `off` | Falkor InterpretationNode anchor path (DISCARDED per fix_v11 gate-6; kept for diagnostic A/B) | `=on` | fix_v11 §17 |
| `LIA_INGEST_INTERPRETATION_NODES` | `enforce` | Idempotent loader for InterpretationNode subgraph | `=off` | fix_v11 |

**Ingest-pipeline knobs:** `LIA_INGEST_CLASSIFIER_WORKERS=4` (held until `TokenBudget` ships per next_v4 §10.1), `LIA_INGEST_CLASSIFIER_RPM=300`, `LIA_SUPABASE_SINK_WORKERS=4`, `FALKORDB_QUERY_TIMEOUT_SECONDS=30`, `FALKORDB_BATCH_NODES=500`, `FALKORDB_BATCH_EDGES=1000`.

### Runtime-shape additions (no env flag)

Code/SQL changes that altered runtime behavior without a new flag. Full context in the linked fix docs.

- Conversational-memory staircase L1+L2 — `ConversationState.prior_topic/prior_subtopic/topic_trajectory/prior_secondary_topics`; classifier soft-tiebreaker on `prior_topic`. (next_v4 §3–§5)
- `comparative_regime_chain` query mode — `config/comparative_regime_pairs.json` + `pipeline_d/answer_comparative_regime.py`. (next_v4 §5)
- `hybrid_search` decoupled `filter_topic` ↔ `boost_topic` via migration `20260512000000_topic_filter_soft.sql`; chat path always passes `filter_topic=None`. (fix_v7)
- `pipeline_d/answer_topic_gate.py` + `config/topic_norm_allowlist.json` filter off-topic-norm bullets before polish. (fix_v7 §3c)
- Polish observability — `polish.applied` trace step + `diagnostics.polish_mode` / `polish_skip_reason` whitelisted. (fix_v8 §3b)
- Polish prompt rewrite — DIRECTIVA PRIMARIA + ARTÍCULOS/REFORMAS PERMITIDAS allowlists; `gemini-flash` temperature `0.1 → 0.0` (chat-polish only). (fix_v8 §3e–§3f)
- `supabase_sink.write_chunks` inherits `knowledge_class` from parent doc. Cloud backfill: 2,275 chunks retagged. New `documents.provider_labels (text[])` + GIN index. (fix_v10 §10A, §9.3)
- Trust-tier prioritization in `interpretacion/retriever_supabase.py::_group_chunks_by_doc` — `trust_tier_weight=0.30` (high/medium/low). (fix_v11 Phase 11A)
- `pipeline_c.orchestrator.generate_llm_strict` tuple-contract fix — was returning dict; every caller unpacked as tuple; 12 regression tests at `tests/test_pipeline_c_generate_llm_strict.py`. (fix_v11 §15)
- `pipeline_d/case_detectors.py::is_donaciones_case` — `"esal" in msg` → `re.search(r"\besal\b", ...)`; fixes UGPP `desalarización` collision. (fix_v18 b1 §1.4)
- `pipeline_d/answer_conflict_resolver.py` (~360 LOC) wired into `orchestrator.run_pipeline_d` between `synthesis.template_built` and `polish_graph_native_answer`; A1 reuses `primary_articles`, A2 reuses polish LLM adapter — zero new infra. (fix_v18 b2 §1.5)

### Diagnostic surface

Nine retrieval-diagnostic keys lifted to top-level `response.diagnostics` (next_v3 phase 1). Retrieval-stage deep trace via `tracers_and_logs/pipeline_trace.py` — context-local collector, one JSONL line per stage to `tracers_and_logs/logs/pipeline_trace.jsonl`, also attached to `response.diagnostics["pipeline_trace"]`. PII-safe (stage names + counts + truncated decisions). Whitelisted in `ui_chat_payload.filter_diagnostics_for_public_response`. Stage coverage: topic resolution (every silent-None branch), planner, retriever (hybrid_search I/O, anchor merge, vigencia v3 kept/dropped/demoted), reranker, coherence gate, citation allow-list, polish (provider/adapter/elapsed).

## LLM provider split — chat vs canonicalizer

`config/llm_runtime.json` defaults `provider_order` to **`gemini-flash` first** so chat works. Canonicalizer overrides via `LIA_VIGENCIA_PROVIDER=deepseek-v4-flash` (set explicitly in every canonicalizer launch script).

- **Chat path** (`topic_router._classify_topic_with_llm`, `answer_llm_polish`) needs fast structured-JSON; 8s timeout per call.
- **Canonicalizer** needs long-context schema-following at high RPM; DeepSeek v4-flash/pro fits.
- **Why this matters**: DeepSeek-v4-pro is a reasoning model — returns `reasoning_content` but often empty `message.content` for short structured prompts. Adapter at `llm_runtime.py:198` raises; topic resolver previously swallowed it and fell through to keyword fallback, mis-routing every multi-domain query to `declaracion_renta`. SME panel dropped 21/36 → 8/36 acc+ on 2026-04-29. Full diagnosis: `docs/re-engineer/fix/fix_v1_diagnosis.md`.
- **If you flip provider order again, re-run the §1.G panel** before merging.

## Hot Path (main chat)

1. `ui_server.py` → 2. `pipeline_router.py` → 3. `topic_router.py` → 4. `pipeline_d/orchestrator.py` (reads `LIA_CORPUS_SOURCE` + `LIA_GRAPH_MODE`, dispatches) → 5. `pipeline_d/planner.py`
6. Retriever — one of:
   - `pipeline_d/retriever.py` — artifact BFS (dev default)
   - `pipeline_d/retriever_supabase.py` — Supabase `hybrid_search` (staging chunks)
   - `pipeline_d/retriever_falkor.py` — cloud Falkor Cypher BFS (staging graph). **Errors propagate — never silently falls back to artifacts.**
7. `answer_support.py` → 8. `answer_synthesis.py` (stable facade) → 9. `answer_assembly.py` (stable facade)

Facade implementations (edit the narrow one that owns the behavior): `answer_synthesis_sections.py`, `answer_synthesis_helpers.py`, `answer_synthesis_practica.py`, `answer_first_bubble.py`, `answer_followup.py`, `answer_inline_anchors.py`, `answer_historical_recap.py`, `answer_comparative_regime.py`, `answer_topic_gate.py`, `answer_conflict_resolver.py`, `answer_polish_rejected_fallback.py`, `answer_shared.py`, `answer_policy.py`.

## Fast Decision Rule

- wrong norms / workflow → planner or retriever
- right evidence, weak practical substance → `answer_support.py`
- `**Recomendaciones Prácticas**` reads as normative bullets → check `diagnostics.practica_backend` + `practica_reserved_count`. `supabase` + `>=1` reserved → tune `answer_synthesis_practica.py::_candidate_lines_from_chunk`. `supabase` + `0` reserved → corpus/routing (read `practica.retriever.*` trace). `error` → RPC outage; rollback `LIA_PRACTICA_SOURCE=disabled`
- wrong tone/shape → `answer_policy.py` or assembly/synthesis modules
- answer cites off-topic norms → `config/topic_norm_allowlist.json` or `answer_topic_gate.py`. Toggle `LIA_TOPIC_GATE_MODE=off`
- polish rejected + empty answer (~120 chars) → `answer_polish_rejected_fallback.py` or `answer_synthesis_sections.py`. Toggle `LIA_POLISH_REJECTED_FALLBACK_MODE=off`
- vector RRF dead / `embedding_mode != "ok"` → `retriever_supabase._query_embedding` + `lia_graph.embeddings.get_query_embedding`. Rollback `LIA_QUERY_EMBEDDINGS_ENABLED=0`
- cross-topic anchor missing on staging → check `retriever.hybrid_search.in.filter_topic` is `None` + `boost_topic` carries the routed topic. Else `retriever_supabase.py:258-304` or the topic_filter_soft migration
- bullets with same predicate but contradictory numeric values (pre-Ley + current rule both surface) → `LIA_CONFLICT_RESOLVER_MODE` (default `shadow`); inspect `synthesis.conflict_resolver.applied` trace step
- tarifa-shaped UVT/% appears polished but not in evidence → `_no_invented_uvt_ranges` in `answer_llm_polish.py`; toggle `LIA_POLISH_UVT_VALIDATOR=shadow`
- expert panel surfaces off-topic interpretation cards → Python `article_index` fallback (Phase 10C v0); pattern-axis tuning exhausted in v11. Future fix needs a semantic relevance signal at the filter layer. Falkor anchor path stays behind `LIA_PLANNER_INTERPRETATION_ANCHOR=on` for diagnostic A/B
- runtime wiring change → `orchestrator.py` (and only then)
- dev ≠ staging → check `diagnostics.retrieval_backend` / `graph_backend`, then `scripts/dev-launcher.mjs` + env matrix
- `Normativa` / `Interpretación` UX work → their own packages. **Never** route into `main chat` assembly.

## Surface Boundaries

`main chat`, `Normativa`, and `Interpretación` are **distinct surfaces** with parallel orchestration/synthesis/assembly modules. Shared graph/evidence utilities may stay shared; visible assembly stays surface-specific. `answer_synthesis.py` / `answer_assembly.py` are not the backend for the Normativa modal.

## Non-Negotiables

- **No text walls in docs.** Every doc / change-log / banner / fix-plan entry is bullets, lists, or tables — never multi-sentence prose. 1-line headline → `-`-bulleted sub-points (≤ 2 short sentences each). Tables for what/why/rollback; code blocks for rollback recipes. Applies to every `.md` in the repo.
- Keep docs, code, and the `/orchestration` HTML map (`frontend/src/app/orchestration/shell.ts`, `frontend/src/features/orchestration/orchestrationApp.ts`) aligned.
- Prefer focused module edits over monolithic rewrites — change the narrowest module that owns the behavior.
- Architecture change → update `docs/orchestration/orchestration.md` (versioned env matrix) **in the same task** as the code change.
- `LIA_*` env or launcher flag change → bump env matrix version, add change-log row, update mirror tables in `docs/guide/env_guide.md`, this file, and the `/orchestration` status card.
- Falkor adapter must keep propagating cloud outages — **no silent artifact fallback** on staging.
- **Cloud retirements are CLI-explicit only.**
  - Removing a doc from cloud Supabase + Falkor REQUIRES `lia-graph-artifacts --additive --allow-retirements` typed by an operator.
  - GUI additive flow + any non-explicit CLI invocation MUST pass `allow_retirements=False` (the default).
  - Out-of-sync `knowledge_base/`, partial Dropbox sync, machine swaps must NEVER silently retire prod docs.
  - Enforced at `src/lia_graph/ingestion/delta_runtime.py::materialize_delta`.
- `PipelineCResponse.diagnostics` must always carry `retrieval_backend` and `graph_backend`.
- Never run the full pytest suite in one process — use `make test-batched`.
- Do not inherit old-RAG assumptions (indexing, tagging, vocab, reranking, chunk orchestration, cache). `docs/deprecated/` is archaeology.
- **Worktree + commit hygiene (fix_v22_may §9b).** Drift-prevention rules — every session, every commit, every fix doc.
  - **Worktree session ends with one of three outcomes — no fourth option.**
    - **Land** — commit, fast-forward main, push, `git worktree remove`, `git branch -D <branch>`. State ledger updated to ✅.
    - **Snapshot + discard** — `git format-patch` (or `git diff > <name>.patch`) into `tracers_and_logs/snapshots/<UTC>_<slug>.patch`, commit the patch on main, then `worktree remove -f`.
    - **Park with explicit ETA** — append a row to `docs/re-engineer/active_worktrees.md` naming worktree + branch + slug + operator-authorized return date + expiry behavior. No undated parks. Past-ETA parks are removed without further confirmation.
  - **Lock semantics are advisory.** Locked worktrees owned by dead PIDs are stale; `ps -p <pid>` the lock owner, force-remove if dead. Live PID lock is honored.
  - **A worktree branch only exists while the worktree exists.** `git worktree remove` and `git branch -D <its-branch>` run on the same command line. Orphan branches with no worktree are forbidden.
  - **Every code change lands as 1 commit + 1 push within the operator session that wrote it.** Sessions ending mid-implementation snapshot the diff as a `.patch`. No bare `git commit` without a paired `git push`; exceptions documented in the run log.
  - **Fast-forward-only main.** Rebase the worktree branch onto main first, then ff-merge into main. No merge commits on main.
  - **Commit message includes the fix doc id.** Every commit on a `fix_vNN_may` worktree starts subject with `fix(vNN ...)` / `ship(vNN ...)` / `docs(vNN ...)`.
  - **Fix-doc is closed only when §⏯ "Last completed step" reads "vNN closed ✅" AND every §2 phase row is `✅` or `↩`.** No partial closures. On closure, tag the closing commit `fix_vNN_closed`.
  - **Stale-fix-doc audit runs at every v(NN+1) opening.** P1 includes `git worktree list` + `docs/re-engineer/active_worktrees.md` review; surface anything past ETA or older than 14 days.
- **Six-gate lifecycle for every `docs/aa_next/**` step.** Unit tests green ≠ improvement. Every pipeline change passes all six gates BEFORE any code is written:
  1. **Idea** — one sentence.
  2. **Plan** — narrowest module.
  3. **Success criterion** — measurable minimum with numbers.
  4. **Test plan** — HOW: development needed, environment, actors (engineer/operator/SME/end user), numeric decision rule.
  5. **Greenlight** — BOTH technical tests AND end-user validation against real data at the accountant-experience layer.
  6. **Refine-or-discard** — iterate, or explicitly discard (kept in record, never silently rolled back).
  - Status lifecycle: 💡 idea → 🛠 code landed → 🧪 verified locally → ✅ verified in target env → ↩ regressed-discarded. Full policy in `docs/aa_next/README.md`.

## Fail Fast, Fix Fast — operations canon

For any operation against real systems touching ≥100 records (cloud promotions, batch ingests, evals, embedding backfills, scraper cascades, migrations): instrument fail-fast thresholds **before** launching, treat the first abort as **diagnosis material**, fix the root cause, re-run until **stable**.

1. **Instrument before launching.** Every ≥100-op detached job needs an absolute error count + error-rate gate (default `>50 errors OR >10% rate after 100 ops → abort`). Check between sub-batches. Surface threshold + current rate in the heartbeat.
2. **First abort = diagnosis, not retry.** Do NOT raise the threshold, add `--continue-on-error`, or relaunch. Read audit log, group by root cause, fix the producer, dry-validate on full input, then re-launch.
3. **"Stable" = past the prior failure point with errors at or below dry-run prediction.** One clean heartbeat is not stable; one clean cycle past the bad spot is.
4. **Idempotency is mandatory** — UPSERT on natural keys, idempotency-key checks, sentinel files, deterministic run-ids.
5. **Audit logs, not stdout.** Heartbeat reads structured JSONL outcome rows. Categorize errors; the error-pattern bucket IS the diagnosis.
6. **Diagnose at the audit layer, not the symptom.** "DB constraint violated" → read failing rows, find shared shape, fix the writer/canon/extractor — not the constraint, not the threshold.
7. **Preflight before volume.** Independent sub-runs → ingest ONE record per sub-run through the full real-writer + real-DB path BEFORE the main loop. Same run-id as main loop so idempotency-key matches. Abort on any preflight error. Cost: ~1 min per ~40 batches; saves ~25 min per fail-fast trip.
8. **Risk-first ordering.** Heterogeneous risk → process novelty / historical-failure batches FIRST. High-risk = anything touching a code path / data shape / DB constraint not yet exercised in this env. Failure at minute 25 of a 30-minute run is unrecoverable.

Reference impl: `scripts/cloud_promotion/{run.sh,heartbeat.py}` (`RISK_FIRST=1` / `PREFLIGHT=1`). Full canonicalizer learning: `docs/learnings/canonicalizer/preflight-and-risk-first-batching-2026-04-29.md`. Process companion: `docs/learnings/process/risk-first-cascade-design.md`.

## Long-running Python processes — always detached + heartbeat

Any background Python process expected to take >2 min (reingests, embedding backfills, subtopic-miner, evals, long Gemini sweeps): operator should never have to ask for progress.

1. **Launch detached** — `scripts/launch_phase9a*.sh` shape: `nohup` + `disown` + direct `>log 2>&1` redirects (NO `| tee` pipe; tee breaks on SIGHUP and has crashed a run). Reparenting to init (`PPID=1`) is the success signal.
2. **Arm a 3-min heartbeat** via `CronCreate` → `scripts/monitoring/ingest_heartbeat.py` with `--delta-id`, `--start-utc`, `--total`, and pre-run baselines. Template + transitions + kill-switches in `scripts/monitoring/README.md`.
3. **Anchor progress to `logs/events.jsonl`**, not the `--json` summary (which buffers until termination).
4. **Render in Bogotá AM/PM** per the time-format memory; use the heartbeat's markdown table shape.
5. **Phase-aware silence** — `sink_writing` + `falkor_writing` legitimately emit no per-item events. Only `classifying` ticks continuously; only there does `FRESH > 180s` signal a stall.
6. **Kill-switches** — process gone + no `cli.done` → STOP, surface events/log, do NOT retry. `run.failed` / `ERRORS > 0` → STOP. `cli.done` → STOP, declare complete.

Do not add new `--json`/tee/background variants when launching long Python jobs; copy the launcher + heartbeat shape.

---

If in doubt, follow `AGENTS.md` and treat it as the repo-level operating guide.
