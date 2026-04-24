# Ingestion & Retrieval Tuning v2 — Phased Implementation Plan

> **Status:** awaiting operator approval · **Author:** prepared 2026-04-24 from `ingestion_tunningv1.md` findings · **Branch target:** `feat/ingestion-tunning-v2` (to be created)
>
> **This doc is the execution plan for what v1's investigations concluded should happen.** Do not start coding from this document until the operator explicitly approves. Once approved, an LLM-agent (or human engineer) should be able to read §0, then §1, then execute each phase in order, updating the state log (§12) as they go.
>
> **v1 → v2 relationship.** If you want to know *why* these specific fixes were chosen, read `ingestion_tunningv1.md` §0 (Findings log). This doc (v2) does not re-argue the "why" — it specifies the "what" and "how."

---

## §0 Cold-start briefing (read first if entering cold)

### 0.1 What this document is and isn't

**Is.** An implementation specification. Every phase lists the files to modify, the functions to add, the tests to run, the verification commands, and the success criteria. It is designed to be picked up mid-flight — if something fails in phase 4, a new operator should be able to read the state log (§12), the completed phases, and continue from phase 4 without re-reading the conversation that produced this plan.

**Isn't.** A discussion document. "Should we do this?" was answered in v1. If you are about to propose a different approach, re-read `ingestion_tunningv1.md` §0 Findings-log Synthesis ("After-all-investigations synthesis") and open a new doc. Do not rewrite this one.

### 0.2 How to use the state log

At the bottom of this document (§12) there is a State Log table with one row per phase. Each phase has:
- A status: `pending` / `in-progress` / `blocked` / `done` / `rolled-back`
- A "commit SHA" column that gets filled with the commit hash when the phase lands
- A "notes" column for surprises, blockers, or links to incident writeups

**Rule:** update the state log *before* and *after* each phase. `pending → in-progress` before you start; `in-progress → done` (or `blocked` with a reason) after you finish. If you skip a phase, write `skipped (reason)`. If you roll back, write `rolled-back (reason)` and the revert commit.

This lets a future operator (or a future you) reconstruct where execution was. Do not remove the state log rows; append notes to the "notes" column.

### 0.3 Environment assumptions

- **Repo root:** `/Users/ava-sensas/Developer/Lia_Graph`
- **Main branch:** `main`
- **Work branch:** `feat/ingestion-tunning-v2` (to be created before phase 1)
- **OS:** macOS (darwin); shell: `zsh`
- **Package manager:** `uv` (everything Python runs via `uv run python ...`)
- **PYTHONPATH rule:** always prefix with `PYTHONPATH=src:.` when invoking Python — otherwise `from lia_graph...` imports fail
- **Never run the full pytest suite in one process.** Use `make test-batched` (the conftest guard aborts if >20 test files are collected without `LIA_BATCHED_RUNNER=1`)

### 0.4 Single-line command reference

| Task | Command |
|---|---|
| Run local dev app | `npm run dev` |
| Run staging-against-cloud dev app | `npm run dev:staging` |
| Health-check suite | `npm run test:health` |
| Focused backend smokes | `npm run test:backend` |
| Single Python test | `PYTHONPATH=src:. uv run pytest tests/<file>.py -q` |
| Full Python suite (batched, sanctioned) | `make test-batched` |
| Full corpus rebuild (local artifacts only) | `make phase2-graph-artifacts` |
| Full corpus rebuild + Supabase sink | `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` |
| Gold-set eval | `make eval-c-gold` |
| Start/stop local Supabase | `make supabase-start` / `make supabase-stop` |
| Dev launcher preflight only | `npm run dev:check` |

### 0.5 Auth and credentials

- **Supabase (production):** credentials live in `.env.staging`. Do not print them. The Makefile targets pick them up automatically.
- **FalkorDB (cloud):** credentials live in `.env.staging` under `LIA_FALKORDB_*`. Required for `--strict-falkordb` flag on the Supabase sink target.
- **Local Supabase docker:** started by `make supabase-start`, uses test users from `supabase/migrations/20260417000001_seed_users.sql`. All `@lia.dev` users have password `Test123!` after `make supabase-reset`.
- If any phase hits an auth error: do NOT try to rotate keys or guess credentials. Surface it to the operator.

### 0.6 Source-of-truth pointers

Read these if a decision in this plan conflicts with the codebase. In priority order:

1. `docs/guide/orchestration.md` — authoritative env/flag matrix and hot-path map. If code and this doc disagree, reconcile to orchestration.md.
2. `docs/guide/chat-response-architecture.md` — how the main-chat answer is shaped.
3. `docs/guide/env_guide.md` — run modes, env files, squashed migration baseline, test accounts, corpus refresh playbook.
4. `AGENTS.md` — repo-level operating guide.
5. `CLAUDE.md` — project-specific agent instructions.
6. `docs/next/ingestion_tunningv1.md` — the *why* behind this plan (investigation findings).
7. `docs/next/ingestionfix_v5.md` — the most recent prior ingestion iteration, for context.

### 0.7 Hot-path file inventory (the files this plan touches)

Work in focused modules, not monolithic edits. These are the only files any phase should modify; any phase that needs to touch something outside this list MUST explain why in its notes.

| File | Role | LOC (approx) | Phases that touch it |
|---|---|---|---|
| `src/lia_graph/pipeline_d/orchestrator.py` | Hot-path entry, assembles `response.diagnostics` | 608 | 1, 3 |
| `src/lia_graph/pipeline_d/retriever_falkor.py` | Cloud FalkorDB retriever, emits tema-first diagnostics | ~380 | 1 (read-only) |
| `src/lia_graph/pipeline_d/topic_safety.py` | Topic misalignment detector | 204 | 3 |
| `src/lia_graph/pipeline_d/answer_policy.py` | Prompt policy and allow-list injection point | 342 | 4 |
| `src/lia_graph/pipeline_d/answer_support.py` | Chunk-insight extractor (contamination entry point) | 903 | **do not append — extract if needed** |
| `src/lia_graph/topic_router.py` | Classifier orchestrator | 665 | 5 |
| `src/lia_graph/topic_router_keywords.py` | Keyword + override data | 1790 | 5 |
| `scripts/evaluations/run_ab_comparison.py` | 30Q A/B eval harness | ~330 | 1 |
| `evals/gold_retrieval_v1.jsonl` | 30Q gold file | (30 rows) | 5 |
| `config/topic_taxonomy.json` | Taxonomy source of truth | (76 topics) | 5 (read-only) |

**Rule:** `answer_support.py` is already ≥903 LOC. Per the repo granularization rule (see user memory), do not append to it — extract into a focused sibling module when a new helper is needed.

### 0.8 Test suite layout

- `tests/test_phase3_graph_planner_retrieval.py` — retriever smoke. Fast.
- `tests/test_phase2_graph_scaffolds.py` — graph-build smoke.
- `tests/test_phase1_runtime_seams.py` — env/launcher seams.
- `tests/test_ui_server_http_smokes.py` — HTTP layer smokes.
- `tests/test_background_jobs.py` — job-queue smokes.
- Full retrieval eval: `make eval-c-gold` (threshold 90) / `make eval-c-full`.
- Frontend vitest + Playwright: `npm run test:frontend` / `npm run test:e2e`.

Every phase below names the specific tests it expects to pass. If a phase's tests unexpectedly break an unrelated test, stop the phase and record in the state log.

### 0.9 Git conventions

- **Branch:** `feat/ingestion-tunning-v2` off of `main`, created in phase 0.
- **One commit per phase.** Message format: `feat(ingestionfix-v6-phase-N): <short summary>`.
- **Co-author trailer on every commit:** `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
- **Never force-push.** Never push to `main`. Never bypass hooks with `--no-verify` or `--no-gpg-sign`.
- **PR is opened only after all phases of this plan are complete** — this is explicitly not per-phase PRs. Each phase is a commit on the same branch.
- If a phase requires a rollback, use `git revert <sha>` and write the revert SHA in the state log. Do NOT amend or rewrite history.

### 0.10 Glossary (terms used in this plan)

- **Tema-first retrieval:** the v5 mechanism that seeds retrieval from articles connected to a routed topic via `TopicNode<-[:TEMA]-(ArticleNode)` edges. Gated by `LIA_TEMA_FIRST_RETRIEVAL` env flag (off / shadow / on).
- **Evidence-topic coherence gate:** a new refusal mechanism this plan introduces. Fires when primary retrieval returns zero articles AND support_documents don't topic-match the plan's topic, OR when retrieved articles' dominant topic disagrees with plan.topic. Distinct from a classifier-confidence gate (which v1 investigation proved ineffective).
- **Diagnostic surface:** the fields on `response.diagnostics`. Pre-v2 these are partially nested (e.g., `primary_article_count` is at `diagnostics["evidence_bundle"]["diagnostics"]`, not top-level). Phase 1 fixes this.
- **The artifact:** `artifacts/parsed_articles.jsonl`. Built by `make phase2-graph-artifacts`. Stale since 2026-04-21 until phase 2 runs.
- **Contamination:** an answer that includes content from chunks not semantically related to the user's query (eg Q16's biofuel paragraph in a labor answer).
- **Gold file:** `evals/gold_retrieval_v1.jsonl`. 30 questions with `expected_topic` + `expected_article_keys` used by the A/B harness and retrieval evals.

### 0.11 When to invoke sub-agents

This plan is designed for single-operator execution. Sub-agents are NOT required. However, they are permitted for specific narrow tasks:
- **Explore agent** (`subagent_type=Explore`) — permitted for phase verification when you want an independent read on whether a change landed correctly.
- **Code-reviewer / ultrareview** — only invoked by the operator (not by agents) since they are billed.

Do NOT delegate decisions to sub-agents. Decisions belong to the operator.

### 0.12 Stop conditions

Stop the current phase and surface to the operator if any of these fire:
- A test failure that isn't covered by the phase's expected failure list.
- An auth error on Supabase or FalkorDB.
- A corpus rebuild (`make phase2-graph-artifacts`) that takes >30 minutes, or fails partway through.
- Any operation that would publish to a shared system (push, PR comment, studio notebook, etc.) — those require explicit operator approval per turn, even if authorized once.
- A diff that grows the hot-path files by >200 LOC total across the phase. That signals scope creep; extract to a sibling module instead.

### 0.13 Safety and destructive-operation rules

- **No `rm -rf` under any circumstance.** If a directory seems wrong, rename it with a `.broken` suffix and surface.
- **No force-pushes, no `git reset --hard`.** Use `git revert` for rollbacks.
- **No skipping hooks.**
- **No modifications to `main` branch.**
- Before any Supabase sink run (`phase2-graph-artifacts-supabase`), confirm `PHASE2_SUPABASE_TARGET` is as intended. The production target writes to the cloud.
- Before any Falkor-touching command, verify you are against the expected database via `LIA_FALKORDB_URL` env — the production URL writes to the cloud graph.

---

## §1 Phase overview (the at-a-glance plan)

Seven phases, roughly a week of focused work. The order is chosen so each phase's output is measurable before the next phase starts — meaning if phase 3 regresses phase 2's metrics, we catch it immediately.

| # | Phase | Goal | Risk | Surface touched | Gate before next |
|---|---|---|---|---|---|
| 0 | Prep | Branch created, state log initialized | none | git only | branch exists |
| 1 | Diagnostic lift | A/B harness + orchestrator surface the right fields. All future measurements become trustworthy. | low (additive) | `orchestrator.py` (+~30 LOC), `run_ab_comparison.py` (+~15 LOC) | existing eval jsonl re-reads produce non-zero `primary_article_count` for previously-run Q12; one new pytest passes |
| 2 | Full corpus rebuild | Rebuild `parsed_articles.jsonl` + push to Supabase + load into Falkor. Adds ~3,609 EXPERTOS/PRACTICA articles. | **medium (cloud write)** | artifact files, Supabase, FalkorDB | new artifact has >5,000 articles; Supabase `documents` row count increases; Falkor ArticleNode count increases |
| 3 | Evidence-topic coherence gate | Extend `topic_safety.detect_topic_misalignment` to fire on zero-primary + off-topic-chunks. New refusal_reason surfaced. | medium (flag-gated) | `topic_safety.py` (+~60 LOC), `orchestrator.py` (refusal hookup +~20 LOC) | flag-off behavior unchanged; flag-on sample query returns refusal with specific `refusal_reason` |
| 4 | Citation allow-list in answer policy | Port Contadores defensive per-topic citation allow-list. Start with 4 topics: laboral, SAGRILAFT, facturación_electronica, régimen_simple. | low (prompt-level, flag-gated) | `answer_policy.py` (+~50 LOC); new config `config/citation_allow_list.json` | Q11 / Q27 / Q16 contamination cases verify no citation outside allow-list |
| 5 | Gold file + taxonomy alignment | Align `evals/gold_retrieval_v1.jsonl` `expected_topic` keys to real taxonomy. Add subtopic keywords for declaracion_renta procedural branches. | low (config+data only) | `evals/gold_retrieval_v1.jsonl`, `topic_router_keywords.py`, optionally `config/topic_taxonomy.json` | on-disk 30Q replay: zero expected_topic != taxonomy-key mismatches |
| 6 | 30Q A/B re-run (validation) | Run the same 30Q A/B with rebuilt corpus + fixed harness. Compare against prior v5 panel result. | low (eval only) | produces `artifacts/eval/ab_comparison_<timestamp>_v6_rebuild.jsonl` | diagnostics now show real counts; contamination on Q11/Q16/Q22/Q27 decreases or refuses; panel doc regenerated |
| 7 | *Optional* subtopic keyword fills | For any topics still missing keywords after phase 5 (e.g., `firmeza_declaraciones`, `sanciones_extemporaneidad`, `devoluciones_saldos_a_favor`), add keyword entries. | low | `topic_router_keywords.py` | re-run 30Q shows improvement on Q20/Q21/Q22 |

**Hard gate:** if phase 6 shows the contamination rate hasn't fallen, STOP, do not proceed to phase 7. Surface to operator for decision.

---

## §1.5 Cumulative success criteria (plan-wide)

This is the one-page "did we win" scorecard. Every number here aggregates across the phase-level criteria. If at plan-end any of these metrics is below its hard-gate value, the v6 work is not done — either re-run missed phases, or hand off to a v7 plan.

### Corpus (after phase 2)

| Metric | v5 baseline | v6 target | Hard gate |
|---|---|---|---|
| Ingested articles in `parsed_articles.jsonl` | 2,118 | ≥ 5,700 | ≥ 5,000 |
| EXPERTOS-family articles | 0 | ≥ 1,200 | ≥ 800 |
| PRACTICA-family articles | 0 | ≥ 2,000 | ≥ 1,500 |
| Falkor `ArticleNode` count | 9,160 | ≥ 12,500 | ≥ 11,500 |
| Falkor `TEMA` edges | 2,361 | ≥ 2,700 | ≥ 2,500 |
| Gold-set eval score (`make eval-c-gold`) | ~90 | ≥ 90 | ≥ 87 |

### Classifier (after phases 5 + 7)

| Metric | v5 baseline | v6 target | Hard gate |
|---|---|---|---|
| Taxonomy topics with no keyword coverage | 9 | ≤ 3 | ≤ 5 |
| Green-coverage topics | 18 | ≥ 24 | ≥ 21 |
| Gold-file `expected_topic` vs taxonomy mismatches | 4 | 0 | 0 |
| Classifier startup warning lines | 9 | ≤ 3 | ≤ 5 |

### Diagnostic surface (after phase 1, visible after phase 6 rerun)

| Metric | v5 baseline | v6 target | Hard gate |
|---|---|---|---|
| 30Q rows with `primary_article_count != None` | 0 / 30 | ≥ 25 / 30 | ≥ 20 / 30 |
| 30Q rows with `tema_first_mode == "on"` (NEW) | 0 / 30 | 30 / 30 | 28 / 30 |
| Mean `primary_article_count` (NEW) | 0.0 | ≥ 3.0 | ≥ 2.0 |

### Answer quality (after phase 6)

| Metric | v5 baseline | v6 target | Hard gate |
|---|---|---|---|
| Contamination cases (Q11, Q16, Q22, Q27) satisfactorily handled | 0 / 4 | 4 / 4 | 4 / 4 (non-negotiable) |
| Forbidden substrings in contaminated questions | 5+ occurrences | 0 | 0 (non-negotiable) |
| Previously-good bail cases (Q4, Q7, Q9) preserved | 3 / 3 | 3 / 3 | 3 / 3 (non-negotiable) |
| Questions with substantial answer (`len(answer) > 400`) | ~6 / 30 | ≥ 18 / 30 | ≥ 14 / 30 |
| Questions with ≥ 1 article citation in answer | ~12 / 30 | ≥ 22 / 30 | ≥ 18 / 30 |

### Code health (across all phases)

| Metric | v6 target | Hard gate |
|---|---|---|
| New files created | 5 (1 config, 2 sibling modules, 2 test files) | ≤ 7 |
| Files modified | 6 (orchestrator, topic_safety, answer_policy, run_ab_comparison, gold file, topic_router_keywords) | ≤ 10 |
| Total LOC added | ≤ 700 | ≤ 1,000 |
| Total LOC deleted | ≤ 80 | ≤ 150 |
| `npm run test:health:fast` | green | green |
| `make test-batched` | pass count ≥ pre-v6 | no net regression |
| Public-surface breakage | 0 | 0 (non-negotiable) |

### Flag state at end of plan (what we flip, what we leave)

| Flag | Value at end-of-v6 | Notes |
|---|---|---|
| `LIA_TEMA_FIRST_RETRIEVAL` | `on` (default) | Was `shadow` by launcher default. Operator confirms before phase 6. |
| `LIA_EVIDENCE_COHERENCE_GATE` | `shadow` (default) | Introduced in phase 3. Flipping to `enforce` is an explicit post-v6 decision. |
| `LIA_POLICY_CITATION_ALLOWLIST` | `off` (default) → `enforce` (staging only) → decision before production | Introduced in phase 4. Phase 6 runs it in `enforce` to validate, but launcher default stays `off` until observed refusal rate is acceptable. |

### What "DONE" looks like in one sentence

The v6 plan is done when the 30Q rerun (phase 6) produces a panel markdown where all 4 contamination cases are either refused or cleanly answered, the diagnostic surface is populated across all 30 rows, the corpus is ≥ 2.5× its v5 size, and no non-negotiable hard gate has fired.

---

## §2 Phase 0 — Preparation

### 2.1 Goal
Branch created, state log initialized, working directory is clean, I understand the plan. No code changes yet.

### 2.2 Steps
1. Verify working tree is clean: `git status` (no uncommitted changes).
2. Verify you are on `main` with `git rev-parse --abbrev-ref HEAD` — if not, switch.
3. Create the branch: `git switch -c feat/ingestion-tunning-v2`.
4. Verify this doc at `docs/next/ingestion_tunningv2.md` renders correctly in your editor.
5. Read §0 of this doc and `ingestion_tunningv1.md` §0 Findings log end-to-end.
6. In §12 State Log of this doc, change Phase 0 status from `pending` to `done` and fill in the date. Commit the state-log update with: `chore(ingestionfix-v6-phase-0): initialize state log and branch`.

### 2.3 Deliverable
- Branch `feat/ingestion-tunning-v2` exists locally.
- State log phase 0 row is `done`.
- One commit on the branch, only modifying this file's state log.

### 2.4 Success criteria (measurable)
- `git rev-parse --abbrev-ref HEAD` returns exactly `feat/ingestion-tunning-v2`.
- `git rev-list --count main..HEAD` returns exactly `1` (one commit ahead of main).
- `git diff main -- docs/next/ingestion_tunningv2.md` shows exactly the §12 state-log row for phase 0 changed from `pending` to `done`.
- `git log -1 --pretty=%s` matches `chore(ingestionfix-v6-phase-0): initialize state log and branch`.
- No other files in the working tree are modified.

### 2.5 Gate to next phase
All 5 bullets above hold. Move to phase 1.

---

## §3 Phase 1 — Diagnostic lift

### 3.1 Goal
Surface `primary_article_count`, `connected_article_count`, `seed_article_keys`, `tema_first_mode`, `tema_first_topic_key`, `tema_first_anchor_count`, `planner_query_mode`, `retrieval_sub_topic_intent`, and `subtopic_anchor_keys` at the **top level** of `response.diagnostics`. Fix the A/B harness to read from that top level. Result: every future measurement becomes trustworthy.

### 3.2 Why this phase first
Without phase 1, every subsequent phase's "did it work" signal is unreadable. The v1 investigation proved that the eval's "zero primary articles everywhere" conclusion was a harness-side artifact. We cannot fix what we can't measure.

### 3.3 Files to modify

**`src/lia_graph/pipeline_d/orchestrator.py`** — `diagnostics={...}` dict at approximately lines 483–499.

Before (current):
```python
diagnostics={
    "compatibility_mode": False,
    "pipeline_family": "pipeline_d_phase3",
    ...
    "planner": plan.to_dict(),
    "evidence_bundle": evidence.to_dict(),
    "retrieval_backend": backend_diagnostics.get("retrieval_backend"),
    "graph_backend": backend_diagnostics.get("graph_backend"),
    "retrieval_health": retrieval_health,
    "reranker": reranker_diagnostics,
    "topic_safety": topic_safety_diag,
    "decomposer": decomposer_diag,
},
```

After (add the following top-level keys, read from `evidence.diagnostics`):
```python
# v6 phase 1: lift retrieval diagnostics to top-level so downstream
# harnesses don't have to drill into evidence_bundle.diagnostics.
_ev_diag = evidence.diagnostics or {}
diagnostics={
    "compatibility_mode": False,
    "pipeline_family": "pipeline_d_phase3",
    ...
    "planner": plan.to_dict(),
    "evidence_bundle": evidence.to_dict(),
    "retrieval_backend": backend_diagnostics.get("retrieval_backend"),
    "graph_backend": backend_diagnostics.get("graph_backend"),
    "retrieval_health": retrieval_health,
    # v6 phase 1 — lifted-to-top fields:
    "primary_article_count": _ev_diag.get("primary_article_count"),
    "connected_article_count": _ev_diag.get("connected_article_count"),
    "related_reform_count": _ev_diag.get("related_reform_count"),
    "seed_article_keys": _ev_diag.get("seed_article_keys"),
    "planner_query_mode": _ev_diag.get("planner_query_mode"),
    "tema_first_mode": _ev_diag.get("tema_first_mode"),
    "tema_first_topic_key": _ev_diag.get("tema_first_topic_key"),
    "tema_first_anchor_count": _ev_diag.get("tema_first_anchor_count"),
    "retrieval_sub_topic_intent": _ev_diag.get("retrieval_sub_topic_intent"),
    "subtopic_anchor_keys": _ev_diag.get("subtopic_anchor_keys"),
    "reranker": reranker_diagnostics,
    "topic_safety": topic_safety_diag,
    "decomposer": decomposer_diag,
},
```

**`scripts/evaluations/run_ab_comparison.py`** — confirm the harness at approximately lines 162–174 reads from top level. It already does via `diag.get("...")`. After phase 1, those reads will succeed.

Optional hardening: add a preflight assertion that `response.diagnostics["primary_article_count"]` is not None when `retrieval_backend` is `supabase` or `falkor_live`. This catches any regression silently dropping the lifted field.

### 3.4 Files to create

**`tests/test_orchestrator_diagnostic_surface.py`** — new test file (~80 LOC).

Must verify:
1. `run_pipeline_d` against a canned query returns a response whose `diagnostics` dict has all nine lifted keys at top level.
2. The lifted values match those nested at `diagnostics["evidence_bundle"]["diagnostics"]`.
3. When `evidence.diagnostics` is empty, the lifted keys are present with value `None` (so `diag.get("...")` returns None uniformly, not `KeyError`).

Fixture: the existing artifact-mode corpus is fine; `LIA_GRAPH_MODE=artifacts` + `LIA_CORPUS_SOURCE=artifacts` is the default and works offline.

### 3.5 Verification commands
```bash
# 1. New test passes
PYTHONPATH=src:. uv run pytest tests/test_orchestrator_diagnostic_surface.py -q

# 2. Existing orchestrator tests still pass
PYTHONPATH=src:. uv run pytest tests/test_phase3_graph_planner_retrieval.py -q

# 3. The health suite is green
npm run test:health:fast

# 4. Manual smoke: re-parse the prior eval output using the lifted fields
PYTHONPATH=src:. uv run python -c "
import json
with open('artifacts/eval/ab_comparison_20260424T122224Z_v5_tema_first_vs_prior_live.jsonl') as f:
    rows = [json.loads(l) for l in f]
print('This row read from lifted diagnostics (after phase 1 re-run):')
print('  expected primary_article_count to be non-None after phase 2 re-run')
"
```

### 3.6 Success criteria (measurable)

**Code-shape metrics:**
- New test file `tests/test_orchestrator_diagnostic_surface.py` exists with exactly 3 test functions, all passing (`pytest --collect-only -q` shows 3 items; `pytest -q` shows `3 passed`).
- `git diff --stat main...HEAD -- src/lia_graph/pipeline_d/orchestrator.py scripts/evaluations/run_ab_comparison.py tests/test_orchestrator_diagnostic_surface.py` shows: ≤ 60 lines added, ≤ 5 lines deleted, exactly 3 files touched.
- `npm run test:health:fast` exits 0.
- `make test-batched` pass count ≥ pre-phase pass count (no net regression). Record the two counts in the state log.

**Diagnostic-surface behavior (run against current-corpus Q3 "¿Qué artículo regula el anticipo del impuesto de renta?"):**
- `response.diagnostics["primary_article_count"]` is an `int` (not `None`). Current local baseline: 3.
- `response.diagnostics["connected_article_count"]` is an `int` (not `None`).
- `response.diagnostics["seed_article_keys"]` is a `list` (may be empty but never `None`).
- `response.diagnostics["tema_first_mode"]` is one of `{"off", "shadow", "on"}` (never `None`).
- `response.diagnostics["planner_query_mode"]` is a non-empty string.
- Re-parsing `artifacts/eval/ab_comparison_20260424T122224Z_v5_tema_first_vs_prior_live.jsonl` with the phase-1 harness re-reads: at least one row has a non-None `primary_article_count` recovered from `evidence_bundle.diagnostics`. (Not all rows will, because the jsonl was recorded pre-phase-1; this proves the upward-reading path works.)

**Baseline-before (record in state log):**
- Current `response.diagnostics["primary_article_count"]` read via `diag.get(...)` → `None`.
- Current `response.diagnostics["tema_first_mode"]` read via `diag.get(...)` → `None`.

### 3.7 Rollback procedure
`git revert <phase-1-sha>`. No data to clean up (pure code change). Record revert SHA in state log.

### 3.8 Commit message
`feat(ingestionfix-v6-phase-1): lift retrieval diagnostics to top-level response.diagnostics`

---

## §4 Phase 2 — Full corpus rebuild

### 4.1 Goal
Rebuild the local `artifacts/parsed_articles.jsonl`, push the fresh corpus to Supabase (production target), and load the Falkor graph. After this phase: the served corpus contains ~5,700 articles (up from 2,118), including all EXPERTOS and PRACTICA content curated on disk.

### 4.2 Why this phase now
Phase 1 gave us the eyes. Phase 2 gives us the data to look at. Every subsequent phase's measurements depend on running against a fresh, representative corpus.

### 4.3 Pre-rebuild checklist (MUST complete before running any Make target)

1. Confirm disk space: the artifact files can reach ~500 MB; Supabase sink + Falkor load streams ~1 GB over the wire.
2. Confirm `.env.staging` contains `LIA_FALKORDB_*` and `SUPABASE_*` — the make target will fail early without them, which is the right safety behavior.
3. Verify the corpus root hasn't shifted: `ls "knowledge_base/CORE ya Arriba/" | wc -l` should return ~30.
4. Snapshot the current artifact for rollback: `cp artifacts/parsed_articles.jsonl artifacts/parsed_articles.jsonl.v5_backup`.
5. Record baseline counts in state log:
   - Current `parsed_articles.jsonl` line count: `wc -l artifacts/parsed_articles.jsonl`
   - Current Falkor ArticleNode count (from `falkor_baseline_v5.json` or a fresh query): 9,160 as of 2026-04-24.
   - Current Supabase documents row count (if accessible): query via `psql` or the Supabase dashboard.

### 4.4 Rebuild sequence

Step 1 — Local artifact rebuild (no cloud writes):
```bash
make phase2-graph-artifacts
```
Expected wall time: 3–8 minutes. Watch for `graph_target_document_count` in the JSON summary; it should be >1200.

Step 2 — Inspect the new artifact before any cloud write:
```bash
wc -l artifacts/parsed_articles.jsonl
# Expected: ~5700+ (was 2118)

PYTHONPATH=src:. uv run python -c "
import json
from collections import Counter
with open('artifacts/parsed_articles.jsonl') as f:
    rows = [json.loads(l) for l in f]
print(f'Total articles: {len(rows)}')
fam = Counter()
for r in rows:
    sp = r.get('source_path', '').upper()
    if 'EXPERTO' in sp: fam['EXPERTOS'] += 1
    elif 'PRACTICA' in sp or 'LOGGRO' in sp: fam['PRACTICA'] += 1
    elif 'NORMATIVA' in sp: fam['NORMATIVA'] += 1
    else: fam['OTHER'] += 1
print(f'By family: {dict(fam)}')
"
```
**Gate:** if EXPERTOS count < 1000 or PRACTICA count < 1500, stop. Do NOT push to cloud. Surface to operator.

Step 3 — Supabase + Falkor load:
```bash
make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production
```
Expected wall time: 10–25 minutes. This is a long-running operation.

**If this step is expected to take >2 minutes of real execution time**, follow the long-running-python-process pattern in `CLAUDE.md`: launch detached with `nohup … > log 2>&1 &`, arm a heartbeat via `scripts/monitoring/ingest_heartbeat.py`. See that script's README for the cron template.

Step 4 — Post-load verification:
```bash
# Expected Falkor counts (approximate):
# ArticleNode ≥ 13000 (was 9160; new ~4000 articles from EXPERTOS+PRACTICA)
# TopicNode unchanged (41)
# TEMA edges may grow slightly (new articles → new TEMA edges via classifier)

# Check graph_load_report for write counts:
cat artifacts/graph_load_report.json | python3 -m json.tool | head -40
```

### 4.5 Files modified by this phase
None by hand. These are regenerated by the Make targets:
- `artifacts/parsed_articles.jsonl` (rewritten)
- `artifacts/typed_edges.jsonl` (rewritten)
- `artifacts/raw_edges.jsonl` (rewritten)
- `artifacts/canonical_corpus_manifest.json` (rewritten)
- `artifacts/corpus_audit_report.json` (rewritten)
- `artifacts/corpus_inventory.json` (rewritten)
- `artifacts/graph_load_report.json` (rewritten)
- `artifacts/graph_validation_report.json` (rewritten)
- `artifacts/subtopic_decisions.jsonl` (rewritten)
- Supabase `documents`, `chunks`, `subtopic_bindings` tables (added/updated rows — the sink is idempotent per document fingerprint)
- Falkor `ArticleNode`, `TopicNode`, `SubTopicNode`, `TEMA`, `HAS_SUBTOPIC` nodes and edges (added/updated)

### 4.6 Verification commands
```bash
# 1. Local artifact is fresh
stat -f "%Sm %N" artifacts/parsed_articles.jsonl
# Expected: today's date

# 2. Counts hit targets
wc -l artifacts/parsed_articles.jsonl
# Expected: ~5700+

# 3. Health suite is still green
npm run test:health:fast

# 4. Eval:
make eval-c-gold
# Expected: threshold ≥ 90. Surface diff from prior eval runs.

# 5. A diagnostic smoke: hit dev app and inspect one response's diagnostics
# (only after phase 1 lands)
```

### 4.7 Success criteria (measurable)

**Artifact-file counts (local, `wc -l` or Python counter):**
- `artifacts/parsed_articles.jsonl` line count ≥ **5,700** (pre-rebuild: 2,118 → +170% minimum).
- Count of rows whose `source_path` contains `EXPERTOS` ≥ **1,200** (pre: 0 → Δ +1,200).
- Count of rows whose `source_path` contains `PRACTICA` or `LOGGRO` ≥ **2,000** (pre: 0 → Δ +2,000).
- Count of rows whose `source_path` contains `NORMATIVA` ≥ **1,800** (pre: ~1,865 — must not regress).
- `artifacts/typed_edges.jsonl` line count ≥ 22,000 (pre: 20,368 → +~8% from new articles' reform references).
- `artifacts/graph_load_report.json`: `articles_written` ≥ **3,500** AND `nodes_upserted` ≥ 3,500.

**Falkor cloud graph counts (query after load; compare to `falkor_baseline_v5.json`):**
- `ArticleNode` count ≥ **12,500** (pre-rebuild: 9,160 → Δ ≥ +3,340).
- `TopicNode` count = **41** (unchanged; assertion, not ≥).
- `SubTopicNode` count ≥ **87** (no regression; expected modest growth).
- `TEMA` edges count ≥ **2,700** (pre: 2,361; new articles → new TEMA edges per the v2-aware classifier).
- `HAS_SUBTOPIC` edges count ≥ **450** (pre: 432).
- Zero `ArticleNode` rows with `topic_key IS NULL` and `family='normativa'`.

**Supabase cloud counts (query via `psql` or dashboard; compare to pre-rebuild snapshot):**
- `documents` row count increased by ≥ **3,400** vs pre-rebuild.
- `chunks` row count increased (exact target depends on chunking; expect ≥ 15,000 new chunk rows).
- Zero rows in `manual_review_queue` with `severity='critical'` post-rebuild.

**Eval parity:**
- `make eval-c-gold` returns a score ≥ **90** AND within **3 points** of pre-rebuild baseline (record both in state log).
- `npm run test:health:fast` exits 0.
- `make test-batched` pass count ≥ pre-rebuild pass count (no net regression).

**Gate — halt and surface if any of these hold:**
- Parsed-articles EXPERTOS count < 1,000 (→ stop; do NOT push to cloud; ingestion broken).
- Parsed-articles NORMATIVA count regresses below 1,500 (→ stop; something wrongly filtered out).
- `graph_load_report.json` shows `failures > 0` (→ stop; surface error).
- Eval score drops by > 5 points vs pre-rebuild (→ stop; re-ingestion introduced a quality regression).

### 4.8 Rollback procedure
The artifact rebuild is safe to reverse locally: `mv artifacts/parsed_articles.jsonl.v5_backup artifacts/parsed_articles.jsonl`. Other artifacts can be rebuilt from the older state but typically don't need rollback.

**Cloud rollback is more invasive.** The Supabase sink is additive (upsert semantics). To roll back cloud writes you would need to either (a) drop the new `documents.doc_id` rows by manifest diff, or (b) promote a previously frozen `gen_<UTC>` snapshot via `promote_generation` RPC. Do NOT improvise a rollback; if you must roll back cloud writes, open a new task and surface to operator.

### 4.9 Commit message
`feat(ingestionfix-v6-phase-2): full corpus rebuild (+3600 EXPERTOS/PRACTICA articles)`

(No code changes — this commit only updates the state log. The artifact files are regenerable and not committed.)

---

## §5 Phase 3 — Evidence-topic coherence gate

### 5.1 Goal
Add a refusal mechanism that fires when retrieval fails on topic grounds — either zero primary articles AND off-topic chunks, or primary articles whose dominant topic disagrees with `plan.topic`. Flag-gated behind `LIA_EVIDENCE_COHERENCE_GATE={off|shadow|enforce}` with default `shadow`. When the gate fires in `enforce` mode, the orchestrator emits a courteous refusal with a specific `refusal_reason` instead of composing an answer from incoherent evidence.

### 5.2 Why this mechanism (not a confidence gate)
v1 investigation I6 proved that a classifier-confidence gate catches only 2 of 5 contamination cases — the others have confidence 1.00 but still retrieve off-topic content. The mechanism that catches the biofuel-in-labor case must key on evidence composition, not classifier state.

### 5.3 Files to modify

**`src/lia_graph/pipeline_d/topic_safety.py`** — extend `detect_topic_misalignment` at approximately lines 102–152. Currently it short-circuits when `primary_articles` is empty (line 113–119). New behavior:

```python
# v6 phase 3: extend detection to cover zero-primary + off-topic support cases.
def detect_topic_misalignment(request, evidence):
    router_topic = normalize_topic_key(request.topic)
    if not router_topic:
        return {"misaligned": False, "reason": "no_router_topic", ...}

    # Case A (pre-existing): primary_articles exist; score their dominant topic.
    if evidence.primary_articles:
        # ... existing logic unchanged ...
        return {"misaligned": ..., "source": "primary", ...}

    # Case B (new in v6): primary_articles empty. Score the support_documents
    # instead. If their dominant topic disagrees with router_topic OR if
    # fewer than K (K=2) support docs match router_topic by family/topic
    # metadata, return misaligned=True with source="support_documents_empty".
    if evidence.support_documents:
        text = _support_doc_topic_scoring_text(evidence.support_documents)
        scores = _score_topic_keywords(text)
        if scores:
            top_topic, top_data = max(scores.items(), key=lambda kv: kv[1]["score"])
            if top_topic != router_topic and top_data["score"] >= 3:
                return {"misaligned": True, "source": "support_documents",
                        "router_topic": router_topic, "dominant_topic": top_topic,
                        "reason": "chunks_off_topic"}

    # Case C (new): neither primary nor topic-matched support. Full refusal.
    return {"misaligned": True, "source": "no_evidence",
            "router_topic": router_topic, "reason": "zero_evidence_for_router_topic"}
```

**`src/lia_graph/pipeline_d/orchestrator.py`** — after `_retrieve_evidence` returns, check the gate and short-circuit to a refusal composer if it fires in `enforce` mode. In `shadow` mode, emit the diagnostic but continue composing (so we can measure what would have happened). Approximate placement: after line 142 where evidence is merged.

```python
# v6 phase 3: evidence-topic coherence gate
coherence_mode = os.getenv("LIA_EVIDENCE_COHERENCE_GATE", "shadow").strip().lower()
if coherence_mode not in ("off", "shadow", "enforce"):
    coherence_mode = "shadow"
misalignment = detect_topic_misalignment(request, evidence)
if misalignment["misaligned"] and coherence_mode == "enforce":
    return _compose_refusal_response(
        request=request,
        refusal_reason=misalignment["reason"],
        misalignment_diagnostic=misalignment,
    )
# else: continue normal flow; diagnostic will be surfaced regardless.
```

Add a new `_compose_refusal_response` helper (or reuse the existing abstention_text_for_misalignment at `topic_safety.py:184`). The helper builds a `PipelineCResponse` whose `answer_markdown` is the courteous refusal text, with `diagnostics["refusal_reason"]` and `diagnostics["refusal_source"]` set.

### 5.4 Files to create

**`src/lia_graph/pipeline_d/_coherence_gate.py`** (NEW, sibling module, ~100 LOC) — owns the `LIA_EVIDENCE_COHERENCE_GATE` env parsing, the support-docs topic-scoring helper `_support_doc_topic_scoring_text`, and the refusal response composer. Keeps `topic_safety.py` and `orchestrator.py` from growing beyond their current LOC.

**`tests/test_coherence_gate.py`** (NEW, ~120 LOC). Tests:
1. Gate `off`: behavior identical to pre-phase-3 (regression test).
2. Gate `shadow`: diagnostic is emitted but answer is composed (no refusal).
3. Gate `enforce`, primary empty + chunks off-topic: refusal emitted, `refusal_reason == "chunks_off_topic"`.
4. Gate `enforce`, primary empty + chunks absent: refusal emitted, `refusal_reason == "zero_evidence_for_router_topic"`.
5. Gate `enforce`, primary present and on-topic: no refusal.
6. Gate `enforce`, primary present but off-topic: refusal emitted, `refusal_reason == "primary_off_topic"`.

### 5.5 Verification commands
```bash
# 1. New tests pass
PYTHONPATH=src:. uv run pytest tests/test_coherence_gate.py -q

# 2. Existing topic_safety tests still pass
PYTHONPATH=src:. uv run pytest tests/ -k topic_safety -q

# 3. Shadow mode: run two canned queries and confirm the diagnostic surface
# shows misalignment for Q16-like queries
LIA_EVIDENCE_COHERENCE_GATE=shadow PYTHONPATH=src:. uv run python scripts/evaluations/run_ab_comparison.py \
  --gold evals/gold_retrieval_v1.jsonl --output /tmp/coherence_shadow.jsonl --sample Q16

# 4. Enforce mode: confirm refusal path on Q16
LIA_EVIDENCE_COHERENCE_GATE=enforce PYTHONPATH=src:. uv run python scripts/evaluations/run_ab_comparison.py \
  --gold evals/gold_retrieval_v1.jsonl --output /tmp/coherence_enforce.jsonl --sample Q16
# Expected: Q16 answer_markdown contains "no pude ubicar evidencia..." style refusal.
```

*Note:* the `--sample` CLI flag may not exist on the current harness. If not, add a minimal `--sample Q16` filter during phase 3 or copy Q16 into a throwaway gold file.

### 5.6 Success criteria (measurable)

**Code-shape metrics:**
- `tests/test_coherence_gate.py` exists with exactly **6 test functions**, all passing.
- New sibling module `src/lia_graph/pipeline_d/_coherence_gate.py` ≤ **120 LOC**.
- Modifications to `src/lia_graph/pipeline_d/topic_safety.py`: ≤ **60 lines added**, ≤ 10 deleted.
- Modifications to `src/lia_graph/pipeline_d/orchestrator.py`: ≤ **25 lines added**, ≤ 5 deleted.
- Total phase-3 diff: ≤ **200 lines across ≤ 4 files**.
- `make test-batched` pass count ≥ pre-phase pass count.

**Gate-off (flag unset or `off`) — regression protection:**
- Q3 ("¿Qué artículo regula el anticipo del impuesto de renta?"): response identical to pre-phase-3 (byte-exact `answer_markdown` match).
- Q16: response identical to pre-phase-3.

**Gate-shadow (`LIA_EVIDENCE_COHERENCE_GATE=shadow`) — observation without action:**
- Q16: `diagnostics["topic_safety"]["misaligned"] == True`.
- Q16: `diagnostics["topic_safety"]["reason"]` ∈ `{"chunks_off_topic", "zero_evidence_for_router_topic", "primary_off_topic"}`.
- Q16: `diagnostics["topic_safety"]["source"]` ∈ `{"primary", "support_documents", "no_evidence"}`.
- Q16: `len(response.answer_markdown) > 0` (answer still composed — shadow does not refuse).
- Q3: `diagnostics["topic_safety"]["misaligned"] == False` (healthy case stays healthy).

**Gate-enforce (`LIA_EVIDENCE_COHERENCE_GATE=enforce`) — refusal where indicated:**
- Q16: `"biocombustible"` substring is NOT in `response.answer_markdown` (contamination blocked).
- Q16: `response.diagnostics["refusal_reason"]` is a non-empty string.
- Q16: `response.answer_markdown` contains at least one of the refusal phrases: `"no pude"`, `"no puedo"`, `"reformules"`, `"evidencia insuficiente"`.
- Q3: `diagnostics["refusal_reason"]` is `None` (healthy case is not over-refused).
- Q3: answer composed normally (length ≥ 200 characters, contains article citation).

**Whole-30Q shadow-mode telemetry (run full gold set in shadow; count refusal *would-haves*):**
- Number of 30Q questions where `misaligned=True` is ≥ **4** (covers at least Q11, Q16, Q22, Q27 — the 4 contamination cases).
- Number of 30Q questions where `misaligned=True` is ≤ **12** (false-positive ceiling; refusing >40% of traffic means miscalibration).

### 5.7 Rollback procedure
`git revert <phase-3-sha>`. Flag default is `shadow` (no user-visible behavior change), so rollback risk is bounded even without revert — just set `LIA_EVIDENCE_COHERENCE_GATE=off` in launcher.

### 5.8 Commit message
`feat(ingestionfix-v6-phase-3): evidence-topic coherence gate with shadow/enforce modes`

---

## §6 Phase 4 — Citation allow-list in answer policy

### 6.1 Goal
Port the Contadores defensive mechanism from `prompts/answer_policy_es.md`: for a fixed set of topics, the answer composer MAY only cite articles from an allow-list; any other cited article must be silently dropped (treated as retrieval leakage). Seed with 4 topics:
- `laboral` → {ET: 383, 384, 385, 387, 387-1, 388, 108, 114-1; CST: any}
- `sagrilaft_ptee` → {Circular Básica Jurídica SuperSoc; Res. Ministerio de Justicia on UIAF; no ET articles at all}
- `facturacion_electronica` → {ET: 616-1; Res. DIAN 165/2023; Res. DIAN 12761/2011; no ET articles outside 616-1 without specific product justification}
- `regimen_simple` → {ET: 903–916; no ET retención-fuente articles; no ET régimen-ordinario articles outside 905}

Flag-gated behind `LIA_POLICY_CITATION_ALLOWLIST={off|enforce}` with default `off` during rollout.

### 6.2 Files to modify

**`src/lia_graph/pipeline_d/answer_policy.py`** — add a `filter_citations_by_allowlist` function at the appropriate integration point (where citations are assembled). Approximate +~50 LOC. Do NOT append more than 100 LOC; if that ceiling is hit, extract.

### 6.3 Files to create

**`config/citation_allow_list.json`** (NEW). Schema:
```json
{
  "version": "v2026-04-26-v1",
  "topics": {
    "laboral": {
      "allowed_et_articles": ["383","384","385","387","387-1","388","108","114-1"],
      "allowed_article_families": ["CST","CODIGO_SUSTANTIVO_TRABAJO"],
      "notes": "Defensive allow-list. ET articles outside this set should be dropped as retrieval leakage."
    },
    "sagrilaft_ptee": {
      "allowed_et_articles": [],
      "allowed_article_families": ["CIRCULAR_BASICA_JURIDICA","RESOLUCION_UIAF"],
      "notes": "SAGRILAFT has no relevant ET anchors; any ET citation is leakage."
    },
    "facturacion_electronica": {
      "allowed_et_articles": ["616-1"],
      "allowed_article_families": ["RESOLUCION_DIAN"],
      "notes": "ET articles outside 616-1 (e.g., 516, 514) are timbre/retención leakage."
    },
    "regimen_simple": {
      "allowed_et_articles": ["903","904","905","906","907","908","909","910","911","912","913","914","915","916"],
      "allowed_article_families": ["DECRETO_1625_2016"],
      "notes": "Outside RST article block → leakage from retención-fuente or renta-ordinaria."
    }
  }
}
```

**`src/lia_graph/pipeline_d/_citation_allowlist.py`** (NEW sibling module, ~80 LOC). Owns config load, citation-match logic, and the drop-with-diagnostic emission. Exposes one function: `filter_citations_by_allowlist(citations, topic, mode) -> (filtered_citations, dropped_citations_diag)`.

**`tests/test_citation_allowlist.py`** (NEW, ~100 LOC). Tests:
1. Config loads cleanly.
2. Topic `laboral` + citation to ET 148 → dropped.
3. Topic `laboral` + citation to ET 383 → kept.
4. Topic `sagrilaft_ptee` + citation to ET 148 → dropped.
5. Topic `sagrilaft_ptee` + citation to Circular Básica Jurídica → kept.
6. Topic `facturacion_electronica` + citation to ET 516 → dropped (the Q11 case).
7. Topic `regimen_simple` + citation to ET 392 → dropped.
8. Mode `off` → all citations kept regardless.

### 6.4 Verification commands
```bash
# 1. Test file passes
PYTHONPATH=src:. uv run pytest tests/test_citation_allowlist.py -q

# 2. Existing answer_policy tests still green
PYTHONPATH=src:. uv run pytest tests/ -k answer_policy -q

# 3. Manual Q11 trace
LIA_POLICY_CITATION_ALLOWLIST=enforce PYTHONPATH=src:. uv run python scripts/evaluations/run_ab_comparison.py \
  --gold evals/gold_retrieval_v1.jsonl --output /tmp/allowlist_q11.jsonl --sample Q11
# Expected: Q11 answer_markdown does NOT contain ET 516 or ET 514 citations.
```

### 6.5 Success criteria (measurable)

**Code-shape metrics:**
- `tests/test_citation_allowlist.py` exists with exactly **8 test functions**, all passing.
- New config file `config/citation_allow_list.json` parses as valid JSON, has exactly **4 topic entries** (`laboral`, `sagrilaft_ptee`, `facturacion_electronica`, `regimen_simple`).
- New sibling module `src/lia_graph/pipeline_d/_citation_allowlist.py` ≤ **100 LOC**.
- Modifications to `src/lia_graph/pipeline_d/answer_policy.py`: ≤ **50 lines added**, ≤ 5 deleted.
- Total phase-4 diff: ≤ **220 lines across ≤ 4 files**.

**Flag-off (default) — regression protection:**
- Q11: `response.answer_markdown` byte-exact match to pre-phase-4.
- Q14 (clean laboral case): byte-exact match to pre-phase-4.
- `diagnostics["dropped_by_allowlist"]` is `[]` across all 30 gold questions.

**Flag-enforce per-question expected drops (run each with `LIA_POLICY_CITATION_ALLOWLIST=enforce`):**

| qid | Expected citation drops (articles that should appear in `diagnostics["dropped_by_allowlist"]`) | Must NOT appear in `answer_markdown` |
|---|---|---|
| Q11 (nota crédito FE) | `{"article": "516"}`, `{"article": "514"}` | strings `"516"`, `"514"` in any citation context |
| Q16 (medio tiempo) | citations to `Ley-939-2004.md` articles (biofuel), any ET article not in `{383, 384, 385, 387, 387-1, 388, 108, 114-1, 114_1}` | string `"biocombustible"` |
| Q22 (saldo a favor) | any retención-fuente article (e.g., `{"article": "104"}` cesantías) — saldo-a-favor is not in allowlist scope but should be left intact | — |
| Q27 (SAGRILAFT) | `{"article": "148"}`, `{"article": "588"}`, any ET article | any bare `"art. NNN"` pattern citing ET |
| Q14 (parafiscales — control, clean case) | `[]` (empty) | — |
| Q8 (retención salarios — control) | `[]` (expects ET 383, 206, 336 all in scope) | — |

**Flag-enforce aggregate:**
- Number of 30Q questions with `diagnostics["dropped_by_allowlist"]` non-empty: ≥ **4** (at least the 4 contamination cases).
- Number of 30Q questions with `diagnostics["dropped_by_allowlist"]` non-empty: ≤ **10** (over-drop ceiling — dropping >33% of traffic's citations means allowlist is too narrow).
- Across all 30 questions, `answer_markdown` contains zero `"biocombustible"`, zero `"art. 148"` / `"Art. 148"` in a non-SAGRILAFT topic, zero `"art. 516"` / `"Art. 516"` in a non-timbre topic.

**Observability — each drop is logged:**
- For every entry in `diagnostics["dropped_by_allowlist"]`, it must have shape `{"article": "<num>", "topic": "<topic_key>", "reason": "<str>"}`.

### 6.6 Rollback procedure
`git revert <phase-4-sha>`. Flag default is `off`, so rollback risk is bounded.

### 6.7 Commit message
`feat(ingestionfix-v6-phase-4): defensive per-topic citation allow-list (laboral, sagrilaft, FE, RST)`

---

## §7 Phase 5 — Gold file and taxonomy alignment

### 7.1 Goal
Close the naming-mismatch gap v1 found between `evals/gold_retrieval_v1.jsonl` `expected_topic` strings and the real taxonomy keys. Add subtopic keyword coverage for the declaracion_renta procedural branches that the classifier currently lumps into the parent.

### 7.2 Files to modify

**`evals/gold_retrieval_v1.jsonl`** — update the 4 known naming mismatches (from v1 I5 findings):
- Q19: `obligaciones_mercantiles` → `comercial_societario`
- Q25: `impuesto_patrimonio` → `impuesto_patrimonio_personas_naturales`
- Q26: `dividendos` → `dividendos_utilidades`
- Q29: `perdidas_fiscales` → `perdidas_fiscales_art147`

Additionally, audit and correct any other expected_topic values that don't match `config/topic_taxonomy.json` keys. Script to detect (run before editing):
```bash
PYTHONPATH=src:. uv run python -c "
import json
with open('config/topic_taxonomy.json') as f:
    tax_keys = {t['key'] for t in json.load(f)['topics']}
with open('evals/gold_retrieval_v1.jsonl') as f:
    for line in f:
        r = json.loads(line)
        et = r.get('expected_topic')
        if et and et not in tax_keys:
            print(f\"  {r['qid']:<5} expected_topic={et!r} is NOT in taxonomy\")
"
```

**`src/lia_graph/topic_router_keywords.py`** — add keyword buckets for the declaracion_renta procedural children currently uncovered. From v1 I2 findings, these topics have no keyword entries but cause routing failures (Q20, Q21, Q22):

- `firmeza_declaraciones` — strong: `("firmeza de la declaración", "declaración en firme", "art. 714", "firmeza tributaria")`; weak: `("firmeza", "término de firmeza", "años")`.
- `regimen_sancionatorio_extemporaneidad` — strong: `("sanción por extemporaneidad", "declaración extemporánea", "art. 641")`; weak: `("extemporánea", "sanción", "reducción de sanción")`.
- `devoluciones_saldos_a_favor` — strong: `("saldo a favor", "devolución saldo a favor", "compensación saldo", "art. 850")`; weak: `("devolución", "saldo", "solicitud de devolución")`.

If any of these keys are not in `config/topic_taxonomy.json`, add them as subtopics (child of `declaracion_renta` or `procedimiento_tributario` as appropriate). Coordinate with the subtopic_taxonomy.json as well.

**`config/topic_taxonomy.json`** — if new topics added above, append entries matching the existing schema (key, label, parent_key, aliases, ingestion_aliases, etc.). Bump the `version` string.

### 7.3 Files to create
None required by this phase.

### 7.4 Verification commands
```bash
# 1. Topic-alignment detector (run post-edit to confirm zero mismatches)
PYTHONPATH=src:. uv run python -c "
import json
with open('config/topic_taxonomy.json') as f:
    tax_keys = {t['key'] for t in json.load(f)['topics']}
fails = []
with open('evals/gold_retrieval_v1.jsonl') as f:
    for line in f:
        r = json.loads(line)
        et = r.get('expected_topic')
        if et and et not in tax_keys:
            fails.append((r['qid'], et))
print(f'Mismatches remaining: {len(fails)}')
for qid, et in fails: print(f'  {qid}: {et}')
"
# Expected: Mismatches remaining: 0

# 2. Classifier test on Q20/Q21/Q22 after keyword additions
PYTHONPATH=src:. uv run python -c "
from lia_graph.topic_router import detect_topic_from_text
for label, q in [
    ('Q20', 'Un cliente PJ se atrasó 3 meses en presentación de renta. ¿Cuál es la sanción por extemporaneidad?'),
    ('Q21', '¿Cuándo queda en firme una declaración de renta del AG 2022?'),
    ('Q22', 'Un cliente tiene saldo a favor de 85M en renta. ¿Cómo solicito la devolución?'),
]:
    d = detect_topic_from_text(q)
    print(f'{label}: {d.topic}  conf={d.confidence:.2f}')
"
# Expected: Q20 → regimen_sancionatorio_extemporaneidad (or parent), Q21 → firmeza_declaraciones, Q22 → devoluciones_saldos_a_favor

# 3. Full test suite
npm run test:health:fast
```

### 7.5 Success criteria (measurable)

**Gold-file alignment:**
- The topic-alignment detector script (§7.4 #1) reports **0 mismatches** between `evals/gold_retrieval_v1.jsonl` `expected_topic` values and `config/topic_taxonomy.json` keys.
- `git diff --stat evals/gold_retrieval_v1.jsonl` shows **exactly 4 rows modified** (Q19, Q25, Q26, Q29 — unless additional mismatches surface in the detector, in which case record each extra row in the state log).
- No rows added or deleted in the gold file.

**Classifier behavior on the 3 procedural queries:**
- Q20 ("Un cliente PJ se atrasó 3 meses en presentación de renta..."): `detect_topic_from_text` returns topic `regimen_sancionatorio_extemporaneidad` (or whichever subtopic key was chosen) with `confidence ≥ 0.50`. Pre-phase-5 baseline: `declaracion_renta` conf 1.00.
- Q21 ("¿Cuándo queda en firme una declaración de renta del AG 2022?"): returns `firmeza_declaraciones` with `confidence ≥ 0.50`. Pre: `declaracion_renta` conf 1.00.
- Q22 ("Un cliente tiene saldo a favor de 85M en renta..."): returns `devoluciones_saldos_a_favor` with `confidence ≥ 0.50`. Pre: `declaracion_renta` conf 1.00.
- No regression on the 16 questions that routed correctly pre-phase-5 (topic unchanged, confidence within ±0.10).

**Taxonomy bookkeeping (if new subtopics added):**
- `config/topic_taxonomy.json` top-level `version` string bumped.
- If new topics added: count grows from **76 → ≥ 79** (3 new subtopics); `parent_key` field present on each new entry pointing to `declaracion_renta` or `procedimiento_tributario`.
- `config/subtopic_taxonomy.json` kept in sync with any additions.
- Keyword-warning lines emitted at `from lia_graph.topic_router import …` startup drop from **9 to ≤ 6** (the 3 newly-covered topics stop warning).

**Eval & test:**
- `make eval-c-gold` score ≥ **90** AND within 2 points of pre-phase-5 baseline.
- `npm run test:health:fast` exits 0.
- `make test-batched` pass count ≥ pre-phase pass count.

**Phase diff size:**
- Total phase-5 diff: ≤ **150 lines added, ≤ 30 deleted** across ≤ 4 files (`gold_retrieval_v1.jsonl`, `topic_router_keywords.py`, `topic_taxonomy.json`, optionally `subtopic_taxonomy.json`).

### 7.6 Rollback procedure
`git revert <phase-5-sha>`. Pure data changes, safe to revert.

### 7.7 Commit message
`feat(ingestionfix-v6-phase-5): gold-file taxonomy alignment + declaracion_renta subtopic keywords`

---

## §8 Phase 6 — 30Q A/B re-run (validation)

### 8.1 Goal
Run the same 30Q A/B eval with the rebuilt corpus, fixed harness, coherence gate in `shadow` mode, and citation allow-list in `enforce` mode. Produce a new panel doc. Compare outcomes against the v5 panel.

### 8.2 Files to modify
None. This phase only runs evals.

### 8.3 Files to create
**`artifacts/eval/ab_comparison_<timestamp>_v6_rebuild.jsonl`** (generated by harness).
**`artifacts/eval/ab_comparison_<timestamp>_v6_rebuild.md`** (generated by the md-renderer).
**`artifacts/eval/ab_comparison_<timestamp>_v6_rebuild_manifest.json`** (generated).

### 8.4 Verification commands
```bash
# 1. Run the A/B with all phase 1–5 changes active
LIA_EVIDENCE_COHERENCE_GATE=shadow \
LIA_POLICY_CITATION_ALLOWLIST=enforce \
LIA_TEMA_FIRST_RETRIEVAL=on \
LIA_GRAPH_MODE=falkor_live \
LIA_CORPUS_SOURCE=supabase \
PYTHONPATH=src:. uv run python scripts/evaluations/run_ab_comparison.py \
  --gold evals/gold_retrieval_v1.jsonl \
  --output artifacts/eval/ab_comparison_$(date +%Y%m%dT%H%M%SZ)_v6_rebuild.jsonl \
  --tag v6_rebuild

# 2. Regenerate the panel doc
PYTHONPATH=src:. uv run python scripts/evaluations/render_ab_markdown.py \
  --input artifacts/eval/ab_comparison_*_v6_rebuild.jsonl \
  --output artifacts/eval/ab_comparison_*_v6_rebuild.md

# 3. Quick quantitative compare vs v5 run
PYTHONPATH=src:. uv run python -c "
import json
def stats(path):
    with open(path) as f:
        rs = [json.loads(l) for l in f]
    pac = [r['new']['primary_article_count'] for r in rs if r['new'].get('primary_article_count') is not None]
    tfm_on = sum(1 for r in rs if r['new'].get('tema_first_mode') in ('on','shadow'))
    return len(rs), sum(pac)/max(len(pac),1), tfm_on
for p in ['v5_tema_first_vs_prior_live', 'v6_rebuild']:
    path = f'artifacts/eval/ab_comparison_...' # find the right one
    n, avg, tfm = stats(path)
    print(f'{p}: n={n}, avg_primary={avg:.2f}, tema_first_live={tfm}')
"
```

### 8.5 Success criteria (measurable)

This is the validation gate for the whole v6 stack. Every criterion below compares against the v5 baseline stored in `artifacts/eval/ab_comparison_20260424T122224Z_v5_tema_first_vs_prior_live.jsonl`.

**Diagnostic-surface metrics (proves phase 1 works against cloud):**

| Metric | v5 baseline | v6 target | Hard gate |
|---|---|---|---|
| `primary_article_count != None` in NEW mode | 0 / 30 | ≥ **25** / 30 | ≥ 20 / 30 |
| `primary_article_count >= 1` in NEW mode | 0 / 30 | ≥ **20** / 30 | ≥ 15 / 30 |
| Mean `primary_article_count` in NEW mode | 0.0 | ≥ **3.0** | ≥ 2.0 |
| `tema_first_mode == "on"` in NEW mode | 0 / 30 | **30** / 30 (all) | 28 / 30 |
| `tema_first_anchor_count >= 1` in NEW mode | 0 / 30 | ≥ **20** / 30 (proves TEMA is contributing) | ≥ 10 / 30 |
| `tema_first_topic_key != None` in NEW mode | 0 / 30 | **30** / 30 (all) | 28 / 30 |
| `seed_article_keys` is non-empty list in NEW mode | 0 / 30 | ≥ **20** / 30 | ≥ 10 / 30 |

**Contamination-case behavior (the 4 cases that contaminated in v5 — Q11, Q16, Q22, Q27):**

Each of these 4 questions must satisfy **at least one** of:
- (a) `diagnostics["refusal_reason"]` is non-empty (honest refusal via coherence gate), OR
- (b) `diagnostics["dropped_by_allowlist"]` is non-empty AND `answer_markdown` contains zero out-of-scope citations (allow-list caught the leak), OR
- (c) `primary_article_count >= 2` AND `diagnostics["topic_safety"]["misaligned"] == False` (genuine retrieval recovered, no refusal needed).

**Gate:** all 4 / 4 must satisfy at least one of (a)/(b)/(c). If any case still emits the contaminated v5 answer text, phase 6 fails.

Forbidden substrings (each must not appear in the `answer_markdown` of its matching question):
- Q16: `"biocombustible"`, `"motores diesel"`, `"Ley 939 de 2004"`.
- Q11: `"art. 516"`, `"art. 514"`, `"impuesto de timbre"`, `"Art. 516"`, `"Art. 514"`.
- Q22: `"cesantías"` outside a labor-context sentence (use semantic spot-check).
- Q27: `"Art. 148"`, `"art. 148"`, `"corrección de la declaración"`.

**Previously-good-behavior preservation (Q4, Q7, Q9 — the 3 cases NEW correctly bailed on in v5):**
- All 3 must preserve a protective response: either refusal (new coherence gate), or the pre-existing misalignment hedge ("Detecté un desajuste..." text), or a now-correct-retrieval answer with primary_article_count ≥ 1.
- None of the 3 may degrade into silent boilerplate or contaminated content.

**Aggregate quality metrics:**
- `make eval-c-gold` score ≥ **90** AND within 3 points of the post-phase-2 baseline.
- Count of "would refuse" (coherence gate in shadow mode fires `misaligned=True`) across all 30 questions: between **4 and 12** inclusive.
- Count of questions with `len(answer_markdown) > 400` (a proxy for "substantial answer"): ≥ **18 / 30** (v5 baseline: most answers were ~250-char boilerplate).
- Panel-simulating check: count of questions where `answer_markdown` contains at least one citation pattern (`"Art. N"` or `"artículo N"`): ≥ **22 / 30**.

**Regression screen:**
- No question that was `tie` or `new_better` in v5 may regress to `prior_better` equivalent (manually spot-check; if ambiguous, route to human panel).
- No question may introduce a new type of contamination (cross-topic chunk leak) that wasn't in v5.

### 8.6 Gate to phase 7
- If success criteria all met AND contamination cases resolved or refused → phase 7 is optional. Proceed only if there are still misrouted questions.
- If success criteria NOT met → STOP. Do not proceed to phase 7. Surface to operator.

### 8.7 Rollback procedure
Not applicable — no code changes in phase 6.

### 8.8 Commit message
`chore(ingestionfix-v6-phase-6): 30Q A/B re-run with v6 stack (rebuilt corpus + lifted diagnostics + gates)`

(Commit only updates the state log and attaches a copy of the new eval manifest.)

---

## §9 Phase 7 (optional) — Residual subtopic keyword fills

### 9.1 Goal
Only run if phase 6 reveals remaining misroutes beyond Q20/Q21/Q22. Fill in keyword coverage for any remaining red-coverage topics (from v1 I2: activos_exterior, contratacion_estatal, estatuto_tributario, impuesto_nacional_consumo, impuestos_saludables, leyes_derogadas, reforma_pensional, sector_puertos, sector_transporte).

### 9.2 Files to modify
- `src/lia_graph/topic_router_keywords.py` — add strong/weak keyword buckets for each remaining red topic.

### 9.3 Verification commands
```bash
# After editing, re-run the classifier coverage script from v1 I2:
PYTHONPATH=src:. uv run python -c "
from lia_graph.topic_router_keywords import _TOPIC_KEYWORDS
red = []
for t, buckets in _TOPIC_KEYWORDS.items():
    s = len(buckets.get('strong', ()))
    w = len(buckets.get('weak', ()))
    if not (s+w >= 15 and s >= 5) and not (s+w >= 6 and s >= 2):
        red.append((t, s, w))
print(f'Red topics remaining: {len(red)}')
for t,s,w in red: print(f'  {t}: {s}/{w}')
"
```

### 9.4 Success criteria (measurable)

**Keyword coverage metrics:**
- Red-coverage topic count (strong+weak < 6, or strong < 2): ≤ **3** (v1 baseline: 9). Aim is ≤ 3, stop-gate is ≤ 5.
- Yellow-coverage topics (strong+weak 6-14, strong ≥ 2): ≤ 35 (mild relaxation of 38 baseline is acceptable if topics migrate up to green).
- Green-coverage topics (strong+weak ≥ 15 AND strong ≥ 5): ≥ **24** (v1 baseline: 18; at least +6 promotions).
- Every topic emitted by the classifier across the 30Q gold has strong+weak ≥ **6**.

**Startup-warning metrics:**
- `python -c "from lia_graph.topic_router import *"` emits ≤ **3** `topic 'X' has no registered keywords` warning lines (v1 baseline: 9).
- The 9 previously-uncovered subtopic children of `declaracion_renta` (ganancia_ocasional, tarifas_tasa_minima_renta, rentas_exentas, anticipos_retenciones_a_favor, ingresos_fiscales_renta, beneficio_auditoria, conciliacion_fiscal, renta_liquida_gravable, descuentos_tributarios_renta): at least **6 of 9** now have keyword entries.

**Classifier-on-30Q metrics:**
- Re-running direct-classifier on the 30Q set (post-phase-5 + phase-7): number of cases where `detect_topic_from_text` returns a subtopic (child key with `parent_key` set) rather than its parent: ≥ **5** (v1 pre-phase baseline: 0 — procedural queries always lumped into parent).
- No regression: questions that routed correctly pre-phase-7 still route to the same topic with confidence within ±0.10.

**Phase diff size:**
- Total phase-7 diff: ≤ **200 lines added, ≤ 20 deleted** across `topic_router_keywords.py` and possibly `topic_taxonomy.json`.

### 9.5 Commit message
`feat(ingestionfix-v6-phase-7): residual keyword coverage for red-ranked topics`

---

## §10 Post-phase handoff

When all phases (0 through 6, plus optional 7) are marked `done` in the state log:

1. Regenerate `docs/next/ingestion_tunningv1.md` findings log so the Open Questions list is resolved.
2. Open PR: title `feat(ingestionfix-v6): lifted diagnostics + corpus rebuild + coherence gate + citation allow-list`. Body references this doc, v1, and the phase-6 panel doc.
3. Request ultrareview via `/ultrareview` — **operator only; do not self-invoke**.
4. After merge: update `docs/guide/orchestration.md` env matrix with the new flags (`LIA_EVIDENCE_COHERENCE_GATE`, `LIA_POLICY_CITATION_ALLOWLIST`). Bump matrix version.
5. Archive this doc: `git mv docs/next/ingestion_tunningv2.md docs/done/ingestion_tunningv2.md`.

---

## §11 Risks and mitigations (plan-level)

| Risk | Likelihood | Mitigation |
|---|---|---|
| Phase 2 rebuild fails partway through Supabase sink | medium | Pre-rebuild snapshot + resumable delta support in `phase2-corpus-additive` target. If stuck: surface to operator, do not improvise cloud cleanup. |
| Phase 3 coherence gate over-refuses in `enforce` mode | medium | Ship in `shadow` mode first; measure refusal rate on a production-log sample; flip to `enforce` only after observed rate is acceptable (<20%). |
| Phase 4 allow-list drops legitimate citations | low-medium | Defensive: allow-list mode defaults to `off`; phase 6 spot-checks; allow-list itself is config-driven so additions don't need code changes. |
| Phase 5 taxonomy edit collides with subtopic_taxonomy.json | low | Always edit both files together; bump version strings in both; run `npm run test:health:fast` after. |
| Phase 6 eval shows NEW regression vs v5 | low but serious | STOP at phase 6 gate, do not proceed to 7. Surface. Likely diagnosis: one of phases 3–5 changed behavior the panel didn't expect. |
| Scope creep into classifier redesign or Path B rebuild | medium | This plan explicitly defers those. Any phase that proposes touching files outside the §0.7 inventory must halt and surface. |

---

## §12 State log (update as you go)

> This is the "state-aware" mechanism. Update the row for each phase as you enter it (`pending → in-progress`), and again when you finish (`in-progress → done`). If blocked, use `blocked (reason)` and add a line to the notes column. If rolled back, use `rolled-back` and record the revert SHA in the commit column.
>
> **Do not reformat or remove rows.** Append notes; never overwrite history.

| Phase | Status | Started (UTC) | Completed (UTC) | Commit SHA | Notes |
|---|---|---|---|---|---|
| 0 — Prep | done | 2026-04-24 | 2026-04-24 | `93698ed` | Branch `feat/ingestion-tunning-v2` created; v1/v2 docs added. Base deviated from plan: rebased onto `feat/evaluacion-ingestionfixtask-v1-ab-harness@f8a154f` (not `main`) because that unmerged branch holds `scripts/evaluations/run_ab_comparison.py` which phase 1 depends on. Rebase SHA: `93698ed`. |
| 1 — Diagnostic lift | done | 2026-04-24 | 2026-04-24 | pending | 9 lifted keys surfaced at top of `response.diagnostics`. Count-style (primary/connected/related) fall back to `len(evidence.*)`; `planner_query_mode` falls back to `plan.query_mode`; TEMA-first keys pass through (None in artifact mode, populated in falkor_live). New test file has 3 passing functions. Baseline on Q3 artifacts: primary_article_count=1, connected=2, related=0, tema_first_mode=None. Pre-existing failures on `test_phase3_graph_planner_retrieval.py::test_phase3_pipeline_d_followup_*` reproduced with my change stashed — NOT caused by phase 1, independently broken on the AB harness base (classifier routes a follow-up prompt to router-silent refusal). Surfacing for later triage; not blocking phase 2. |
| 2 — Full corpus rebuild | pending | | | | Pre-check: snapshot artifact, confirm credentials. |
| 3 — Evidence-topic coherence gate | pending | | | | Ship in `shadow` default. Do not flip to `enforce` default in this phase. |
| 4 — Citation allow-list | pending | | | | Seed with 4 topics. Expand later if needed. |
| 5 — Gold + taxonomy alignment | pending | | | | Confirm subtopic_taxonomy.json stays in sync. |
| 6 — 30Q A/B re-run (validation) | pending | | | | HARD GATE: if contamination hasn't dropped, stop and surface. |
| 7 — Residual keyword fills (optional) | pending | | | | Only if phase 6 surfaces remaining misroutes. |
| Post — PR + docs sync | pending | | | | Operator-invoked `/ultrareview`. |

### Phase-level free-form notes

Use this section to log anything that doesn't fit the state log table: surprises, rethinks, incident links, decisions made under uncertainty, questions for the operator. Keep entries dated.

- *(none yet)*

---

## §13 Appendix A — Known pitfalls from v1 investigations

Carry these forward into execution. Each is a real thing that happened during v1's investigations.

1. **Short-phrasing classifier tests lie.** v1 I2 initially reported Q12 routes to `regimen_simple` because I tested with a paraphrased short query. The real Q12 (from `evals/gold_retrieval_v1.jsonl`) is a long business-case paragraph that doesn't contain "RST" or "régimen simple" at all — it routes to `sector_medio_ambiente` at confidence 0.083. Always use the gold file's exact query strings when testing classifier behavior.

2. **`tema_first_mode: None` is ambiguous.** Pre-phase-1 it meant "the harness didn't find the field at top-level" — NOT "the feature didn't run." Post-phase-1 it unambiguously means "the feature is `off`" because the value is surfaced directly. Don't debug a "None" reading without first confirming whether the harness is pre- or post-phase-1.

3. **Stale artifact masks many symptoms.** Every v1 finding reflects a corpus of 2,118 articles. Phase 2 adds ~3,600 more. Expect numbers to shift in every subsequent investigation post-rebuild. Re-baseline before acting on pre-rebuild numbers.

4. **The classifier warns on stdout at import time.** Every `uv run python` invocation that imports `lia_graph.topic_router` emits nine `topic_router: topic 'X' has no registered keywords` warnings. They are annoying but not errors. If a test captures stderr/stdout, filter those warnings.

5. **FalkorDB ArticleNode count is higher than `parsed_articles.jsonl` line count.** The cloud graph accumulates via delta runs; the local artifact is a full-rebuild snapshot. Post-phase-2 they should converge. Do not use "Falkor count == artifact count" as a correctness check.

6. **`answer_support.py` is already 903 LOC.** Any temptation to add a helper to it triggers the repo's "extract to sibling, do not append" rule (see user memory about granular edits). Create a new focused module instead.

7. **`make test-batched` is the only sanctioned way to run the full Python suite.** Regular `uv run pytest` against `tests/` will trip the conftest >20-file guard and abort. If a phase needs the full suite, use `make test-batched`.

---

## §14 Appendix B — File inventory of artifacts produced by phase 2

For an operator who needs to know what "full rebuild" generates, here's the complete list of files `make phase2-graph-artifacts` writes into `artifacts/`:

- `parsed_articles.jsonl` — one JSON object per parsed article
- `raw_edges.jsonl` — edge candidates before classification
- `typed_edges.jsonl` — classified, normalized edges (MODIFICA, DEROGA, CITA, PRACTICA_DE, INTERPRETA_A, etc.)
- `subtopic_decisions.jsonl` — per-document subtopic binding decisions
- `canonical_corpus_manifest.json` — authoritative document registry
- `corpus_audit_report.json` — per-file audit (ingestion_decision, family, graph_target, graph_parse_ready)
- `corpus_inventory.json` — flat inventory for dashboards
- `corpus_reconnaissance_report.json` — topic/subtopic/family rollups
- `graph_load_report.json` — Falkor load counts (only with `--execute-load`)
- `graph_validation_report.json` — post-load validation
- Per-batch: `batch_N_quality_gate.json`, `launch_batch_state_N.json`

None of these are committed to git. All are regenerable.

---

## §15 Appendix C — Quick map: finding a file from a v1 claim

If a phase references "the file where X is" and you can't remember, use this map:

| v1 claim | File |
|---|---|
| "the harness reads diagnostics from the wrong nesting" | `scripts/evaluations/run_ab_comparison.py:162-174` |
| "top-level diagnostics is built here" | `src/lia_graph/pipeline_d/orchestrator.py:483-499` |
| "tema_first_mode is emitted here" | `src/lia_graph/pipeline_d/retriever_falkor.py:176` |
| "the misalignment detector lives here" | `src/lia_graph/pipeline_d/topic_safety.py:102-152` |
| "the abstention text is here" | `src/lia_graph/pipeline_d/topic_safety.py:184` |
| "the keyword table is here" | `src/lia_graph/topic_router_keywords.py` (_TOPIC_KEYWORDS dict, ~line 50) |
| "the ingestion decision logic is here" | `src/lia_graph/ingest_classifiers.py:186-348` |
| "family aliases live here" | `src/lia_graph/ingest_constants.py:92-124` |
| "GRAPH_TARGET_FAMILIES is defined here" | `src/lia_graph/ingest_constants.py:25` |
| "the full rebuild Make target" | `Makefile:125-126` |
| "the Supabase-sink rebuild target" | `Makefile:141-142` |

---

*End of `ingestion_tunningv2.md`. Next document in this sequence, after execution completes: `ingestion_tunningv3.md` if a third iteration is needed, otherwise archive to `docs/done/`.*
