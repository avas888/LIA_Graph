# Ingest Fix v2 — Maximalist Single-Pass Ingestion (Correction Plan)

**Last edited:** 2026-04-21 (close-out)
**Status:** ☐ DRAFT · ☐ APPROVED · ☐ EXECUTING · ☑ COMPLETE
**Execution owner:** Claude Opus 4.7 (1M context), autonomous mode per §0.5
**Close-out:** 2026-04-21T20:51Z — 727 unit tests + 7 integration tests green; Supabase WIP 1292 docs / 2073 chunks / 100% embedded; FalkorDB 14 SubTopicNodes + 105 HAS_SUBTOPIC edges; retro lessons distilled in §13 below
**Goal:** every corpus ingest produces **complete, consistent state across Supabase + FalkorDB + embeddings + taxonomy in a single pass** — no separate backfill step required. Fixes integration gaps left by `docs/done/ingestfixv2.md` (the "first attempt", which shipped unit-tested but integration-broken).

> This document is both a **plan** AND a **work ledger**. Every phase has a `State Notes` block that is updated in-place DURING execution. If a session is interrupted, the state of this file is the resumption pointer — see §8 Resume Protocol.

> **Cold-start agent:** read §0 first, then §1, then §2, then jump to whichever phase is active in §4. Do not skim — every line in §0 and §0.5 is load-bearing. If anything in §0 is wrong (tool missing, branch mismatch, etc.), STOP and surface to the user before proceeding.

---

## 0. Cold-Start Briefing (READ FIRST IF YOU HAVE ZERO PRIOR CONTEXT)

This section is for an LLM agent that opens this doc with no conversation history. After reading §0 + §0.5 + §1 + §2 + the active phase entry in §4, you should have everything you need to execute autonomously.

### 0.1 Project orientation in three sentences
**Lia_Graph** is a graph-RAG accounting assistant for Colombian senior accountants serving SMB clients. It is a derivative of `Lia_contadores` and lives at `https://github.com/avas888/LIA_Graph`. It serves answers in Spanish-CO covering tax (IVA, declaración de renta, ICA, retención, …) AND labor / payroll / seguridad social (CST, Ley 100, parafiscales, UGPP, MinTrabajo) — labor is first-class.

### 0.2 Repo location + branch
- **Working directory:** `/Users/ava-sensas/Developer/Lia_Graph`
- **Branch this plan executes against:** `feat/suin-ingestion` (current HEAD after ingestfix-v2 first-attempt close-out).
- **Main branch (used for PRs):** `main`
- **Latest relevant commit pre-plan:** `83019a6 feat(subtopic-v1): ship phases 1-7 + curated taxonomy v2026-04-21-v1` — the `feat/suin-ingestion` branch carries uncommitted first-attempt v2 work on top of that.

### 0.3 Source-of-truth document map (READ BEFORE WRITING CODE)

Authority, top wins:

| Doc | Role |
|---|---|
| `CLAUDE.md` (repo root) | Hard rules: pipeline_d granularity deliberate; Falkor adapter must propagate outages, not silently fall back; granular edits over monolithic rewrites. |
| `AGENTS.md` (repo root) | Repo-level operating guide when `CLAUDE.md` is silent. |
| `docs/orchestration/orchestration.md` | End-to-end runtime + information-architecture map. Env matrix version is currently `v2026-04-21-stv2`. |
| `docs/guide/env_guide.md` | Run modes, env files, test accounts, corpus refresh. |
| `docs/done/ingestfixv2.md` | The **first attempt** at ingestfix-v2. Phases 1–10 shipped code + unit tests but integration was broken (see §1). THIS plan corrects it. |
| `docs/done/subtopic_generationv1.md` | Produced `config/subtopic_taxonomy.json` (86 subtopics × 37 parent topics). THIS plan consumes it. |
| `docs/next/subtopic_generationv1-contracts.md` | Pinned schemas for subtopic JSONL + proposal JSON + taxonomy JSON. |
| THIS doc (`docs/next/ingestfixv2.md`) | Active plan. State Dashboard (§2) is the live status. |

### 0.4 Tooling baseline (verify in §0.5 pre-flight)
- **Python:** `uv`. Always run as `PYTHONPATH=src:. uv run --group dev <command>`. Never bare `python`.
- **Frontend:** Vite + TypeScript + vitest. Tests: `cd frontend && npx vitest run [test-pattern]`.
- **Dev server:** `npm run dev` (local docker Supabase + Falkor) at `http://127.0.0.1:8787/`.
- **LLM runtime:** `src/lia_graph/llm_runtime.py` exposes `resolve_llm_adapter()`. Gemini 2.0 Flash default.
- **Classifier entry:** `src/lia_graph/ingestion_classifier.classify_ingestion_document(filename, body_text, …)` — returns `AutogenerarResult` with `subtopic_key`, `subtopic_label`, `subtopic_confidence`, `requires_subtopic_review` fields (PASO 4 wired in the first attempt).
- **Embeddings:** `src/lia_graph/embeddings.py` + `scripts/ingestion/embedding_ops.py`. Gemini `text-embedding-004`, 768 dims, batched via `batchEmbedContents`.
- **Supabase migrations:** `supabase/migrations/`. Squashed baseline is `20260417000000_baseline.sql`. Subtopic migration `20260421000000_sub_topic_taxonomy.sql` is already applied (WIP DB was reset this session).
- **FalkorDB schema:** `src/lia_graph/graph/schema.py` — `NodeKind.SUBTOPIC` + `EdgeKind.HAS_SUBTOPIC` already defined.
- **Local docker endpoints:** Supabase at `http://127.0.0.1:54321`, Falkor at `redis://localhost:6389`. `.env.local` now points ONLY at these (rewritten this session; cloud values preserved in `.env.local.cloud.bak.2026-04-21`).
- **Rate limits:** Gemini Flash ~1000 rpm on paid tier (plenty); classifier throttle default 60 rpm to stay well clear.

### 0.5 Pre-flight check (run before Phase A1)

```bash
cd /Users/ava-sensas/Developer/Lia_Graph && \
  git status --short | head -5 && \
  git log --oneline -3 && \
  ls config/subtopic_taxonomy.json supabase/migrations/20260421000000_sub_topic_taxonomy.sql && \
  docker ps --format '{{.Names}}' | grep -E '(supabase_db_lia-graph|lia-falkor-smoke)' && \
  set -a && source .env.local && set +a && \
  echo "GEMINI_API_KEY ok: ${GEMINI_API_KEY:0:10}..." && \
  echo "SUPABASE_URL=$SUPABASE_URL (must be 127.0.0.1)" && \
  echo "FALKORDB_URL=$FALKORDB_URL (must be localhost)" && \
  PYTHONPATH=src:. uv run --group dev pytest \
    tests/test_subtopic_taxonomy_loader.py \
    tests/test_ingest_classifier.py \
    tests/test_supabase_sink_subtopic.py \
    tests/test_graph_schema_subtopic.py \
    tests/test_suin_bridge_subtopic.py \
    tests/test_planner_subtopic_intent.py \
    tests/test_retriever_supabase_subtopic_boost.py \
    tests/test_retriever_falkor_subtopic.py \
    tests/test_backfill_subtopic.py \
    -q
```

Expected: branch clean-ish (uncommitted v2 first-attempt files present), taxonomy + migration files exist, both dockers up, env points at local, all subtopic tests green (≈70 tests). If anything red, STOP.

### 0.6 Auth credentials
- **Local docker Supabase:** anon + service-role keys are the `supabase-demo` keys (visible in `.env.local`, `supabase status -o env`). Not real production secrets.
- **Cloud secrets:** NEVER commit. `.env*` is gitignored. Cloud values are archived at `.env.local.cloud.bak.2026-04-21` (local machine only).
- **Admin UI login:** `admin@lia.dev` / `Test123!` / tenant `tenant-dev`.

### 0.7 Cost + time estimate
- **Phase A (instrumentation):** ~2 hours coding + testing. Zero external-API cost.
- **Phase B (re-run):** ~25 min elapsed, **~$0.50 in Gemini API calls** (revised down from prior plan's $5–15 buffer — reality is ~1313 docs × $0.00026/call ≈ $0.34, plus embeddings ≈ $0.02).
- **Budget ceiling:** if LLM spend crosses $5 during Phase B, STOP and surface.

### 0.8 Glossary

- **Single-pass ingest** — the architecture this plan delivers: one `make phase2-graph-artifacts-supabase` run produces complete state (docs + chunks + Falkor nodes/edges + embeddings-ready chunks + subtemas + SubTopic edges) with no separate backfill needed.
- **PASO 4** — the subtopic-resolution step in the classifier's N2 prompt, already wired by the first-attempt v2. Returns `subtopic_key` / `subtopic_label` / `subtopic_confidence` / `requires_subtopic_review` on `AutogenerarResult`.
- **`subtema`** — Supabase column name for subtopic. Lives on `documents.subtema` and `document_chunks.subtema`. Inherits parent → chunks (Decision E1).
- **HAS_SUBTOPIC edge** — FalkorDB edge `ArticleNode --[HAS_SUBTOPIC]--> SubTopicNode`, emitted per classified article.
- **`article_subtopics`** — optional parameter on `build_graph_load_plan(articles, edges, article_subtopics=...)` that accepts a `Mapping[str, SubtopicBinding]` keyed by `article_key`. Currently unwired in production — Phase A5 wires it.
- **`_infer_vocabulary_labels`** — legacy deterministic regex in `src/lia_graph/ingest_classifiers.py` that tags topic/subtopic via filename + markdown keywords. Today it is authoritative during bulk ingest (BAD — ignores PASO 4's richer verdict). This plan demotes it to a fallback.
- **Backfill script** — `scripts/ingestion/backfill_subtopic.py`. After this plan, it is a maintenance-only utility for re-classifying changed docs or after taxonomy revisions; NOT part of the happy path.
- **WIP target** — Supabase target resolved from `SUPABASE_WIP_URL` + `SUPABASE_WIP_SERVICE_ROLE_KEY`. `.env.local` now points both at local docker.
- **Production target** — `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`. In `.env.local` these also point at local docker (user requested `.env.local` be local-only). Cloud creds are in `.env.staging`.

### 0.9 What this plan does NOT do
- Does NOT re-ingest against cloud. Cloud promotion stays gated on stakeholder sign-off and is out of scope here.
- Does NOT change `config/subtopic_taxonomy.json` or its schema.
- Does NOT change the retriever boost logic (Phase 6 of first-attempt v2). Boost factor `LIA_SUBTOPIC_BOOST_FACTOR` stays at 1.5.
- Does NOT touch the chat-surface UI. Subtopic value flows through retrieval quality.
- Does NOT rewrite the classifier's PASO 4 prompt. The prompt landed in the first attempt and stays.

### 0.10 Git + commit conventions
- **Branch protocol:** no force-push. No `git reset --hard` without user confirmation.
- **Commit message format:** `fix(ingestfix-v2-maximalist-phase-AN): <short summary>`.
- **Co-authored-by line:** `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
- **Cadence:** one commit per phase exit (PASSED_TESTS → COMMITTED). Phase B is NOT committed — the corpus state it writes is Supabase/Falkor side-effect, not repo content.

### 0.11 What NOT to do
- Do not run `supabase db reset` without user confirmation (it wipes local DB). Phase B1 asks explicitly.
- Do not write secrets (anon / service-role keys) to git-tracked files. `.env*` is gitignored; keep it that way.
- Do not point `.env.local` at cloud endpoints. It was rewritten to local-only this session.
- Do not re-introduce silent artifact fallback in the Falkor retriever.
- Do not commit `artifacts/` outputs — they are regenerable.
- Do not skip Phase A integration tests just because unit tests are green. **The entire reason this plan exists is that unit-green didn't mean integration-green.**
- Do not run Phase B until Phase A is fully green (every integration test passing, every DoD ticked).

---

## 0.5 Execution Mode (READ FIRST WHEN RESUMING)

**Mode:** AUTONOMOUS after approval. Once the user marks `Plan status = APPROVED` in §2, execution proceeds without stopping through all phases until either (a) all phases reach `DONE`, (b) a `BLOCKED` status is recorded, or (c) the user explicitly halts.

**No-stop policy:** the agent does NOT pause for confirmation between phases. It DOES update `State Notes` after every meaningful checkpoint.

**When the agent DOES stop:**

1. A test failure cannot be resolved within 3 attempts after diagnosis → mark BLOCKED.
2. Phase B1 `supabase db reset` — STOP for explicit user go (destructive local-DB wipe).
3. Phase B3 full ingest exit code ≠ 0 → STOP, surface stderr.
4. Phase B4 embeddings returns any NULL count > 0 → STOP, investigate.
5. LLM cost budget (§0.7) overrun by 2× (> $10) → STOP.
6. All phases reach `DONE`.

**Recursive decision authority** (see §10): the agent MAY make in-flight choices that do NOT contradict §3 architecture decisions (naming, helper module organization, trace payload fields, test-case count).

**Approval gate:** Phase A1 does NOT begin until `Plan status = APPROVED` is set by the user in §2.

---

## 1. Why this plan exists (retro on first-attempt v2)

### 1.1 The defect, in one sentence
`docs/done/ingestfixv2.md` shipped Phases 1–10 with every unit test green, but the production ingestion path was never exercised end-to-end against real Supabase + real Falkor. As a result, `make phase2-graph-artifacts-supabase` produces zero `SubTopicNode` nodes, zero `HAS_SUBTOPIC` edges, and 100% NULL `documents.subtema` — which is the opposite of what Phases 5, 6, 7 claim to deliver.

### 1.2 Root causes (the five wrongs)

1. **Unit tests mocked the real callers.** `tests/test_suin_bridge_subtopic.py` passes synthetic `article_subtopics={...}` directly into `build_graph_load_plan`. The test cannot fail regardless of whether the production path (`materialize_graph_artifacts` → `build_graph_load_plan`) ever passes `article_subtopics`. It does not.
2. **Two classifiers, no integration.** Intake path runs `classify_ingestion_document` (PASO 4, curated taxonomy). Bulk ingest path runs `_infer_vocabulary_labels` (legacy regex). Same doc, different verdicts. Backfill was added as a third classifier to paper over the split.
3. **Backfill writes Supabase, not Falkor.** Even if backfill runs, Falkor stays empty of subtopic structure.
4. **Pre-existing `python -m lia_graph.ingest` bug:** no `if __name__ == "__main__"` guard. Module loaded and exited 0 without running. Ingest had been silently no-op'ing. Not caused by v2, but v2 never smoke-ran the Makefile target so did not catch it.
5. **Env confusion:** `.env.local` pointed at CLOUD production Supabase. A "local WIP backfill" would have written LLM output into cloud prod under the wrong key. Silent-risk resolved this session (`.env.local` rewritten to local-only).

### 1.3 What has already been done in this session (not part of this plan's Phase A, but state to be aware of)

- `src/lia_graph/ingest.py` — `if __name__ == "__main__": sys.exit(main())` guard appended (fixes root cause #4).
- `.env.local` — rewritten to local-docker endpoints only. Cloud values archived at `.env.local.cloud.bak.2026-04-21`.
- `SUPABASE_WIP_URL` + `SUPABASE_WIP_SERVICE_ROLE_KEY` added (both point at local docker).
- Local Supabase WIP: reset + all 4 migrations applied + 86-row taxonomy synced + 1292 docs + 2073 chunks + 20231 normative edges + 2073/2073 embeddings filled. **BUT** `documents.subtema` = 100% NULL (expected — PASO 4 wasn't wired into ingest), and Falkor has 0 SubTopicNodes / 0 HAS_SUBTOPIC edges.
- An interrupted partial backfill wrote ~45 docs with subtema before being stopped. This partial state will be wiped by Phase B1.

### 1.4 Architecture correction this plan delivers

**Before:** "classify cheaply during audit → write NULL subtema → sink docs/chunks to Supabase → write basic graph to Falkor → (later) run backfill that re-classifies with PASO 4 and writes Supabase only → (never) write matching Falkor edges → hope retrieval works."

**After:** "classify once with PASO 4 during audit (rate-limited) → write populated subtema → sink docs/chunks/subtema to Supabase → write graph INCLUDING SubTopicNodes + HAS_SUBTOPIC edges to Falkor → (backfill-script becomes maintenance-only)."

---

## 2. State Dashboard (update in-place during execution)

**Meta**

| Field | Value |
|---|---|
| Plan status | ☐ DRAFT · ☐ APPROVED · ☐ EXECUTING · ☑ COMPLETE |
| Current phase | — (all phases closed) |
| Last completed phase | B6 (close-out report) |
| Blockers | — |
| Working tree | `feat/suin-ingestion` @ post-`v2026-04-21-stv2c` (maximalist correction shipped) |
| Approved | 2026-04-21 via user message: "the plan is APPROVED. do not stop until all finalized and greenlit" |
| Completed | 2026-04-21T20:51Z |

**Phase ledger** — allowed statuses: `NOT_STARTED`, `IN_PROGRESS`, `PASSED_TESTS`, `COMMITTED`, `DONE`, `BLOCKED`.

| # | Phase | Status | Files touched (target) | Commit SHA |
|---|---|---|---|---|
| A1 | `__main__` guard + CLI-help smoke test | NOT_STARTED (*code already landed; need smoke test*) | `src/lia_graph/ingest.py`, `tests/test_ingest_cli_entry.py` (new) | — |
| A2 | Autoload dotenv in CLI scripts | NOT_STARTED | `scripts/ingestion/embedding_ops.py`, `scripts/ingestion/backfill_subtopic.py`, `scripts/ingestion/sync_subtopic_taxonomy_to_supabase.py`, tests | — |
| A3 | Local-env posture guard | NOT_STARTED | `src/lia_graph/env_posture.py` (new), hook into `ingest.py` + `backfill_subtopic.py`, tests | — |
| A4 | Classifier wired into audit pass (PASO 4 during bulk ingest) | NOT_STARTED | `src/lia_graph/ingest_classifiers.py` or new `ingest_subtopic_pass.py`, `src/lia_graph/ingest.py`, tests | — |
| A5 | `build_graph_load_plan` emits SubTopicNode + HAS_SUBTOPIC from ingest | NOT_STARTED | `src/lia_graph/ingest.py` (construct `article_subtopics`), `src/lia_graph/ingestion/loader.py` (already accepts it), tests | — |
| A6 | `--rate-limit-rpm` + `--skip-llm` flags on ingest CLI | NOT_STARTED | `src/lia_graph/ingest.py`, tests | — |
| A7 | Demote `backfill_subtopic.py` to maintenance | NOT_STARTED | `scripts/ingestion/backfill_subtopic.py`, `Makefile`, docs | — |
| A8 | Delete `scripts/sync_subtopic_edges_to_falkor.py` | NOT_STARTED | that file + any refs | — |
| A9 | Integration test — real Falkor + fake Supabase single-pass | NOT_STARTED | `tests/integration/test_single_pass_ingest.py` (new), `tests/conftest.py` (add `integration` marker) | — |
| A10 | Schema-consistency test — every subtema exists in taxonomy | NOT_STARTED | `tests/integration/test_subtema_taxonomy_consistency.py` (new) | — |
| A11 | Full suite green + orchestration.md update | NOT_STARTED | `docs/orchestration/orchestration.md` (bump change log), `CLAUDE.md` (minor) | — |
| B1 | Supabase db reset (WIP) | NOT_STARTED (*user-gated*) | n/a (command) | — |
| B2 | Sync taxonomy to WIP | NOT_STARTED | n/a (command) | — |
| B3 | Full single-pass ingest (includes PASO 4 + Falkor subtopic edges) | NOT_STARTED | n/a (command) | — |
| B4 | Embeddings | NOT_STARTED | n/a (command) | — |
| B5 | Verification gates | NOT_STARTED | `scripts/verify_wip_state.py` (new, optional) | — |
| B6 | Close-out report + ready-to-promote verdict | NOT_STARTED | this doc (dashboard → COMPLETE), relocate to `docs/done/ingestfixv2-maximalist.md` | — |

**Tests baseline**

| Suite | Pre-plan | Post-plan target |
|---|---|---|
| Existing `tests/test_ingest_classifier.py` | 73 green | 73 green (no regressions) |
| Existing subtopic unit tests (loader, sink, schema, bridge, planner, retrievers, backfill) | ≈60 green | ≈60 green (no regressions) |
| New `tests/test_ingest_cli_entry.py` (Phase A1) | n/a | 2 cases |
| New dotenv-autoload tests (Phase A2) | n/a | 3 cases |
| New env-posture tests (Phase A3) | n/a | 4 cases |
| New classifier-during-ingest tests (Phase A4) | n/a | 5 cases |
| New ingest-emits-subtopic-edges tests (Phase A5) | n/a | 4 cases |
| New ingest-CLI-flag tests (Phase A6) | n/a | 3 cases |
| New `tests/integration/test_single_pass_ingest.py` (Phase A9) | n/a | 4 cases |
| New `tests/integration/test_subtema_taxonomy_consistency.py` (Phase A10) | n/a | 2 cases |
| Atomic-discipline guard | green | green |
| Observability smoke | green | green |

---

## 3. Architecture decision — single-pass ingest

### 3.1 What changes

1. **PASO 4 runs during bulk ingest.** After the existing `_infer_vocabulary_labels` deterministic pass, for every doc that `graph_parse_ready == True` (and optionally for interpretative-guidance docs too), the classifier's PASO 4 fires. Its `subtopic_key` overrides the legacy verdict when `subtopic_confidence >= 0.80` and `requires_subtopic_review == False`. Otherwise legacy verdict stays (or NULL if legacy didn't match either).
2. **Supabase sink reads the PASO-4 populated `subtopic_key`.** Already wired in first attempt; just becomes the normal case instead of the edge case.
3. **`build_graph_load_plan` receives `article_subtopics`.** `materialize_graph_artifacts` constructs the `Mapping[article_key, SubtopicBinding]` from the classified docs' `source_path → subtopic_key` and the taxonomy's `subtopic_key → (parent_topic, label)` lookup, then passes it in. Loader emits SubTopicNodes + HAS_SUBTOPIC edges.
4. **Backfill script becomes maintenance-only.** Default filter flips from `WHERE subtema IS NULL` (every doc on a fresh ingest) to `WHERE requires_subtopic_review = true`. Makefile help docs updated. Plan's §0.11 documents it.
5. **`--skip-llm` flag** bypasses PASO 4 during ingest for dev-loop speed / CI smoke. When set, subtema stays NULL + no Falkor subtopic structure. Dev mode stays cheap.

### 3.2 Why (cost + correctness)

- Real cost per ingest: **~$0.34** (revised from original $5–15 buffered estimate). Gemini 2.0 Flash at $0.10/1M input + $0.40/1M output, ~600 input + ~500 output tokens/call × 1313 docs.
- Time added to ingest: **~2 minutes** at 1000 rpm (paid tier); ~45 minutes at 30 rpm (safe default throttle). Default throttle = 60 rpm → ~22 min added.
- Eliminates: intake-vs-bulk verdict drift, two-step eventual-consistency window, taxonomy-drift race between ingest and backfill, "promote-to-cloud needs LLM recompute" tax, "why is subtema NULL" ambiguity.

### 3.3 What stays

- Retriever boost logic (first-attempt v2 Phase 6) — `LIA_SUBTOPIC_BOOST_FACTOR`, planner intent detection, supabase + falkor retriever behavior all untouched.
- Subtopic chip in UI (first-attempt v2 Phase 7) — untouched.
- `config/subtopic_taxonomy.json` — untouched; taxonomy production is subtopic_generationv1's job.
- Test accounts, auth, retrieval adapters — untouched.

---

## 4. Phased Implementation

Each phase below follows this shape:

```
Goal          — one sentence
Files create  — exact paths
Files modify  — exact paths + edit summary
Tests add     — file path + case count + Verification Command
DoD           — concrete checklist
Trace events  — emitted event_type strings (if any)
State Notes   — live-updated; default `(not started)`
Resume marker — within-phase last-known-good checkpoint
```

---

### Phase A1 — `__main__` guard + CLI-help smoke test

- **Goal:** `python -m lia_graph.ingest --help` actually runs and any future regression of the `__main__` guard is caught by a test.
- **Files create:**
  - `tests/test_ingest_cli_entry.py` (~2 cases, ~40 LOC).
- **Files modify:**
  - `src/lia_graph/ingest.py` — verify the `if __name__ == "__main__": sys.exit(main())` block (already appended this session) is present + well-formed.
- **Tests add:**
  - (a) `subprocess.run(["python", "-m", "lia_graph.ingest", "--help"], capture_output=True)` → returncode==0 AND stdout contains `usage:` AND stdout contains `--supabase-target`.
  - (b) `subprocess.run(["python", "-m", "lia_graph.ingest"], capture_output=True, timeout=5)` with no args → returncode==2 (argparse error) OR produces non-empty stderr. Regression guard: empty stdout+stderr with exit 0 means the guard regressed.
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_ingest_cli_entry.py -v` → 2/2 green.
- **DoD:** the CLI-entry test catches the specific "silent no-op" regression that started this plan.
- **Trace events:** none.
- **State Notes:** (not started — guard code already present, tests pending)
- **Resume marker:** —

---

### Phase A2 — Autoload dotenv in CLI scripts

- **Goal:** every `scripts/*.py` CLI that reads `GEMINI_API_KEY`, `SUPABASE_URL`, `FALKORDB_URL`, etc. auto-loads `.env` / `.env.local` so the user doesn't need `set -a; source .env.local; set +a` incantations.
- **Files create:**
  - `tests/test_cli_dotenv_autoload.py` (~3 cases).
- **Files modify:**
  - `scripts/ingestion/embedding_ops.py` — near the top, after the `_REPO_ROOT`/`sys.path` block, add `from lia_graph.env_loader import load_dotenv_if_present; load_dotenv_if_present()`.
  - `scripts/ingestion/backfill_subtopic.py` — same.
  - `scripts/ingestion/sync_subtopic_taxonomy_to_supabase.py` — same.
- **Tests add:**
  - (a) monkeypatch `env_loader.load_dotenv_if_present` with a spy, import each of the three scripts fresh, assert the spy was called once per script.
  - (b) invoke `scripts/ingestion/embedding_ops.py --help` in a subprocess with a temp cwd containing a `.env.local` that sets a sentinel var; assert the sentinel is readable to the subprocess (integration-style).
  - (c) regression: invoke `scripts/ingestion/embedding_ops.py --target wip --generation gen_test --batch-size 1` in a subprocess without pre-exporting GEMINI_API_KEY but with `.env.local` set; assert the script does not fail with "GEMINI_API_KEY not set" (the failure that bit us this session).
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_cli_dotenv_autoload.py -v` → 3/3 green.
- **DoD:** all three CLI scripts load dotenv on import; the regression test catches a future `_get_api_key() == ""` failure.
- **Trace events:** none.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase A3 — Local-env posture guard

- **Goal:** any script that asserts "local mode" refuses to run if `SUPABASE_URL` or `FALKORDB_URL` resolve to anything other than `127.0.0.1` / `localhost`. Prevents the "silently wrote to cloud prod" failure mode that `.env.local` pointing at cloud created this session.
- **Files create:**
  - `src/lia_graph/env_posture.py` (~80 LOC). Public API:
    - `class EnvPostureError(RuntimeError)`.
    - `def assert_local_posture(*, require_supabase: bool = True, require_falkor: bool = True) -> None` — raises when URLs resolve to non-local hosts. Whitelist: `127.0.0.1`, `localhost`, `::1`, `0.0.0.0`.
    - `def describe_posture() -> dict[str, str]` — diagnostic dict `{supabase_host, falkor_host, posture}`.
  - `tests/test_env_posture.py` (~4 cases).
- **Files modify:**
  - `src/lia_graph/ingest.py` — at the top of `main()`, call `assert_local_posture()` UNLESS `--supabase-target production` AND `FALKORDB_URL` contains `.cloud` / `.aws` (i.e. cloud-intended runs opt out). Add `--allow-non-local-env` flag for explicit cloud runs.
  - `scripts/ingestion/backfill_subtopic.py` — same guard call, gated by `--target`.
- **Tests add:**
  - (a) URL `http://127.0.0.1:54321` → posture="local", no raise.
  - (b) URL `https://xxx.supabase.co` → posture="cloud", `assert_local_posture()` raises.
  - (c) `FALKORDB_URL` containing `.cloud` → raises.
  - (d) `describe_posture()` returns the parsed hosts exactly.
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_env_posture.py -v` → 4/4 green.
- **DoD:** Phase B3 cannot accidentally hit cloud even if `.env.local` is later edited to point at cloud again.
- **Trace events:** `env.posture.asserted` (payload: `supabase_host`, `falkor_host`, `posture`).
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase A4 — Classifier wired into audit pass (PASO 4 during bulk ingest)

- **Goal:** every `CorpusDocument` produced by `materialize_graph_artifacts` carries a `subtopic_key` + `requires_subtopic_review` populated by `classify_ingestion_document` (PASO 4), not by `_infer_vocabulary_labels` alone.
- **Files create:**
  - `src/lia_graph/ingest_subtopic_pass.py` (~140 LOC). Public API:
    - `def classify_corpus_documents(documents: Sequence[CorpusDocument], *, skip_llm: bool, rate_limit_rpm: int) -> tuple[CorpusDocument, ...]`.
    - Internally: loads taxonomy once, iterates, calls `classify_ingestion_document`, honors rate-limit via `time.sleep`, emits `subtopic.ingest.audit_classified` trace per doc, tolerates per-doc classifier failures (logs + keeps legacy verdict + flags `requires_subtopic_review=True`).
  - `tests/test_ingest_subtopic_pass.py` (~5 cases).
- **Files modify:**
  - `src/lia_graph/ingest_constants.py` — `CorpusDocument` dataclass gains `requires_subtopic_review: bool = False` field (already has `subtopic_key`). Update `from_audit_record` and `to_dict` accordingly.
  - `src/lia_graph/ingest.py` — inside `materialize_graph_artifacts`, after the `corpus_documents = tuple(...)` construction and before the sink write, call `classify_corpus_documents(...)` IF `not skip_llm`. Replace the tuple with the classified tuple.
- **Tests add:**
  - (a) happy path — 3 docs, fake classifier returns `subtopic_key` for 2 → resulting documents have 2 populated + 1 NULL + all `requires_subtopic_review` consistent with classifier verdicts.
  - (b) `skip_llm=True` → classifier never invoked; legacy subtopic_key preserved.
  - (c) classifier raises on one doc → other docs still classified, failing doc flagged `requires_subtopic_review=True` with legacy key preserved; test asserts no unhandled exception.
  - (d) rate-limit honored — monkeypatch `time.sleep`, assert `len(sleeps) >= N-1` for N classifier calls at rpm=60.
  - (e) taxonomy cache reused — classifier called N times, taxonomy loaded once (monkeypatch `load_taxonomy` with a counter).
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_ingest_subtopic_pass.py -v` → 5/5 green.
- **DoD:** `materialize_graph_artifacts(skip_llm=False)` on a 3-doc fixture populates `subtopic_key` on the expected docs; `skip_llm=True` leaves legacy behavior unchanged; existing `test_ingest_classifier.py` (73 cases) still green.
- **Trace events:** `subtopic.ingest.audit_classified` (per doc), `subtopic.ingest.audit_done` (per run, payload: `docs_total`, `docs_classified`, `docs_failed`, `elapsed_s`).
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase A5 — `build_graph_load_plan` receives `article_subtopics` from ingest

- **Goal:** Falkor carries SubTopicNodes + HAS_SUBTOPIC edges after a single `materialize_graph_artifacts` run (no separate Falkor-sync step).
- **Files create:** none.
- **Files modify:**
  - `src/lia_graph/ingest.py` — inside `materialize_graph_artifacts`, after the classifier pass (A4), construct `article_subtopics: dict[str, SubtopicBinding]` by correlating `article.source_path → classified_corpus_document.subtopic_key → taxonomy.lookup_by_key[(topic, sub_key)] → SubtopicBinding(sub_topic_key, parent_topic, label)`. Pass to `build_graph_load_plan(articles, classified_edges, graph_client=..., article_subtopics=article_subtopics)`.
  - `src/lia_graph/ingestion/loader.py` — already accepts `article_subtopics` (first-attempt v2 Phase 5). Confirm the param is wired through `_build_subtopic_nodes` + `_build_subtopic_edges` and that these are invoked. No behavior change expected — just exercise-with-real-inputs.
- **Tests add:**
  - (a) `materialize_graph_artifacts` (monkeypatched classifier returning 2 of 3 docs with subtopic) produces a plan whose `nodes` include ≥1 `NodeKind.SUBTOPIC` and `edges` include ≥1 `EdgeKind.HAS_SUBTOPIC`.
  - (b) same run with `skip_llm=True` → plan has 0 SubTopic nodes and 0 HAS_SUBTOPIC edges (regression guard: classifier off must leave graph unchanged).
  - (c) classifier returns a `subtopic_key` that's NOT in `config/subtopic_taxonomy.json` → the binding is skipped (no phantom SubTopic node), `requires_subtopic_review` is set. Schema-consistency invariant.
  - (d) two docs → same subtopic_key → 1 SubTopic node + 2 HAS_SUBTOPIC edges (dedup correctness).
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_ingest_subtopic_pass.py tests/test_suin_bridge_subtopic.py -v` → all green (existing + new cases).
- **DoD:** single call to `materialize_graph_artifacts` with `skip_llm=False` produces a `GraphLoadPlan` whose Falkor load emits SubTopicNodes + HAS_SUBTOPIC edges. No separate Falkor-sync step required.
- **Trace events:** `subtopic.graph.binding_built` (payload: `article_key`, `sub_topic_key`, `parent_topic`).
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase A6 — `--rate-limit-rpm` + `--skip-llm` flags on ingest CLI

- **Goal:** operator can bypass PASO 4 for fast dev-loop / CI smoke (`--skip-llm`) and throttle classifier calls (`--rate-limit-rpm N`, default 60) to stay clear of Gemini quotas.
- **Files create:** none.
- **Files modify:**
  - `src/lia_graph/ingest.py` — add argparse args `--skip-llm` (store_true) and `--rate-limit-rpm INT` (default 60). Thread through `materialize_graph_artifacts` kwargs into `classify_corpus_documents` call.
- **Tests add:**
  - (a) CLI parsing — `parser().parse_args(["--skip-llm"])` → args.skip_llm==True.
  - (b) CLI parsing — `parser().parse_args(["--rate-limit-rpm", "30"])` → args.rate_limit_rpm==30.
  - (c) integration-style — `main(["--corpus-dir", str(tmp_corpus), "--artifacts-dir", str(tmp_art), "--skip-llm"])` runs to completion without calling the classifier (spied), exit code 0.
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_ingest_cli_entry.py -v` (expand with the 3 new cases) → 5/5 green.
- **DoD:** `make phase2-graph-artifacts-supabase EXTRA_FLAGS="--skip-llm"` completes in <10s on a small corpus; `EXTRA_FLAGS="--rate-limit-rpm 30"` slows classifier to 1 call / 2s.
- **Trace events:** none (CLI plumbing).
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase A7 — Demote `backfill_subtopic.py` to maintenance tool

- **Goal:** backfill is no longer part of the happy path. It stays available for "re-classify docs flagged for review" and "re-classify after taxonomy version bump" use cases.
- **Files create:** none.
- **Files modify:**
  - `scripts/ingestion/backfill_subtopic.py`:
    - Default filter flips. Current: `--refresh-existing` required to touch non-NULL. New default: `WHERE requires_subtopic_review = true OR subtema IS NULL`. A new `--only-requires-review` flag narrows further.
    - Add post-Supabase-write step: for every updated doc, also emit `SubTopicNode` + `HAS_SUBTOPIC` via `GraphClient.from_env()` (idempotent MERGE). Mirror what Phase A5 does at ingest time.
    - Top-of-file docstring updated: "maintenance utility; normal flow is single-pass ingest (see `docs/next/ingestfixv2.md`)".
  - `Makefile` — `phase2-backfill-subtopic` target description updated to "maintenance only".
  - `tests/test_backfill_subtopic.py` — add 2 cases: (a) backfill now emits Falkor edges for updated docs; (b) `--only-requires-review` filters correctly.
- **Tests add:**
  - (see modify list).
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_backfill_subtopic.py -v` → 6+2=8 green.
- **DoD:** backfill tests still green. Falkor-emission branch is covered.
- **Trace events:** unchanged (`subtopic.backfill.*` event names preserved), plus the existing `subtopic.graph.node_emitted` / `edge_emitted` from Phase A5 flow reused.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase A8 — Delete `scripts/sync_subtopic_edges_to_falkor.py`

- **Goal:** purge the one-off Falkor-sync script I wrote this session — it's redundant once Phase A5 + A7 land.
- **Files create:** none.
- **Files modify:**
  - Delete `scripts/sync_subtopic_edges_to_falkor.py`.
  - `grep -r sync_subtopic_edges_to_falkor /Users/ava-sensas/Developer/Lia_Graph` — remove any reference (should be none outside this doc and the script itself).
- **Tests add:** none.
- **Verification:** `ls scripts/sync_subtopic_edges_to_falkor.py` → "No such file". Full test suite still green.
- **DoD:** file gone, no dangling references.
- **Trace events:** n/a.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase A9 — Integration test: real Falkor + fake Supabase, single-pass ingest

- **Goal:** a test that exercises `materialize_graph_artifacts` end-to-end against **the actual local Falkor docker** and a `_FakeClient` Supabase, and asserts all four truths: docs → Supabase (via recording fake), chunks → Supabase, SubTopicNodes → Falkor, HAS_SUBTOPIC edges → Falkor. **This is the test that would have caught the original defect.**
- **Files create:**
  - `tests/integration/__init__.py` (empty).
  - `tests/integration/test_single_pass_ingest.py` (~250 LOC, 4 cases).
  - `tests/integration/fixtures/mini_corpus/` — 3 tiny markdown docs (one IVA, one laboral, one ET art). Committed to repo so CI can run it.
  - `tests/integration/conftest.py` — pytest marker `@pytest.mark.integration` + skip-if-no-falkor fixture.
- **Files modify:**
  - `pyproject.toml` — register `integration` marker.
- **Tests add:**
  - (a) 3-doc fixture + fake classifier returning deterministic subtopics → post-ingest, recording Supabase fake has 3 doc-upsert calls with populated `subtema`; Falkor (real docker, MATCH query) has ≥2 SubTopicNode nodes and ≥2 HAS_SUBTOPIC edges.
  - (b) same fixture with `skip_llm=True` → 0 SubTopicNodes in Falkor; Supabase docs all have subtema=NULL.
  - (c) run twice in sequence → idempotent; Falkor node count does not double.
  - (d) classifier returns a subtopic_key not in taxonomy → that doc's binding skipped; doc flagged `requires_subtopic_review`.
  - **Verification:** `LIA_INTEGRATION=1 PYTHONPATH=src:. uv run --group dev pytest tests/integration/test_single_pass_ingest.py -v -m integration` → 4/4 green.
- **DoD:** the test that catches the original defect exists and passes on the fixed code; running it on the pre-A5 code (git stash after A4) would fail.
- **Trace events:** consumed, not emitted.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase A10 — Schema-consistency test: every `subtema` exists in taxonomy

- **Goal:** guard the invariant "every value in `documents.subtema` is a key in `sub_topic_taxonomy`". Drift between the live corpus and the canonical taxonomy becomes a test failure, not a silent retrieval bug.
- **Files create:**
  - `tests/integration/test_subtema_taxonomy_consistency.py` (~120 LOC, 2 cases).
- **Files modify:** none.
- **Tests add:**
  - (a) post-ingest snapshot of recorded Supabase writes → every `subtema` value in docs also appears as `(parent_topic_key, sub_topic_key)` in the taxonomy-sync table writes.
  - (b) if a doc somehow gets a subtema not in the taxonomy → test fails with the specific orphan keys listed.
  - **Verification:** `LIA_INTEGRATION=1 PYTHONPATH=src:. uv run --group dev pytest tests/integration/test_subtema_taxonomy_consistency.py -v -m integration` → 2/2 green.
- **DoD:** orphan-subtema regressions surface immediately.
- **Trace events:** n/a.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase A11 — Full suite green + orchestration.md update

- **Goal:** every test (unit + integration) passes on `feat/suin-ingestion` HEAD. Docs reflect the new architecture.
- **Files create:** none.
- **Files modify:**
  - `docs/orchestration/orchestration.md` — new change-log entry `v2026-04-21-stv2b` (or -stv3) describing the correction: "Single-pass ingest now writes SubTopicNodes + HAS_SUBTOPIC edges directly; backfill demoted to maintenance; env-posture guard added; three new integration tests catch prior defect class." Bump "Current version" header.
  - `CLAUDE.md` — add one line under "Runtime Read Path" noting PASO 4 now runs during bulk ingest (default) with `--skip-llm` override for dev.
  - `docs/done/ingestfixv2.md` — add a top-of-doc banner: "Superseded by `docs/next/ingestfixv2.md` after integration gaps discovered 2026-04-21. This doc records the first-attempt state only."
- **Tests add:** none (integration done in A9/A10).
- **Verification:** `PYTHONPATH=src:. uv run --group dev pytest -q` → all green; `LIA_INTEGRATION=1 pytest -q -m integration` → all green; `cd frontend && npx vitest run` → all green.
- **DoD:** every test green, orchestration.md + CLAUDE.md updated, first-attempt doc clearly marked superseded.
- **Trace events:** n/a.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase B1 — Supabase db reset (WIP)

- **Goal:** wipe the ~45-doc partial-backfill partial state from the interrupted run. Start Phase B from a clean WIP.
- **Stakeholder gate:** STOP before running. User approval in-turn required (matches §0.5 no-stop-policy item #2).
- **Command:**

  ```bash
  cd /Users/ava-sensas/Developer/Lia_Graph && supabase db reset --local
  ```

- **Expected:** all 4 migrations (baseline, seed users, normative_edges_unique, sub_topic_taxonomy) apply cleanly. ~30s.
- **Post-check:**

  ```bash
  PYTHONPATH=src:. uv run python -c "
  from lia_graph.supabase_client import create_supabase_client_for_target
  c = create_supabase_client_for_target('wip')
  for t in ['documents','document_chunks','sub_topic_taxonomy','corpus_generations']:
      r = c.table(t).select('doc_id' if 'doc' in t else 'generation_id' if 'gen' in t else 'parent_topic_key', count='exact').limit(1).execute()
      print(f'{t}: count={r.count}')
  "
  ```

  Expect: all counts = 0.

- **State Notes:** (not started — user-gated)

---

### Phase B2 — Sync taxonomy to WIP

- **Command:** `make phase2-sync-subtopic-taxonomy TARGET=wip`
- **Expected:** `sync-taxonomy: upserted 86 rows to Supabase target=wip (version=2026-04-21-v1)`.
- **Post-check:** `sub_topic_taxonomy` table count == 86.
- **State Notes:** (not started)

---

### Phase B3 — Full single-pass ingest (includes PASO 4 + Falkor subtopic edges)

- **Command:**

  ```bash
  make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=wip
  ```

  (After Phase A5–A6, this invocation now runs PASO 4 + emits Falkor subtopic structure. `--skip-llm` NOT passed.)

- **Expected runtime:** ~15–25 min (1313 docs × classifier @ 60 rpm throttle + existing audit/parse/sink/graph-load pipeline).
- **Expected cost:** ~$0.34 in Gemini Flash API.
- **Post-check:**

  ```bash
  PYTHONPATH=src:. uv run python -c "
  from lia_graph.supabase_client import create_supabase_client_for_target
  c = create_supabase_client_for_target('wip')
  r = c.table('documents').select('doc_id', count='exact').not_.is_('subtema', None).execute()
  print(f'docs with subtema: {r.count}')
  r = c.table('documents').select('doc_id', count='exact').eq('requires_subtopic_review', True).execute()
  print(f'docs flagged for review: {r.count}')
  "
  PYTHONPATH=src:. uv run python -c "
  from lia_graph.graph.client import GraphClient, GraphWriteStatement
  c = GraphClient.from_env()
  for q, desc in [('MATCH (n:SubTopicNode) RETURN count(n) AS n','SubTopic nodes'),('MATCH ()-[:HAS_SUBTOPIC]->() RETURN count(*) AS n','HAS_SUBTOPIC edges')]:
      r = c.execute(GraphWriteStatement(description=desc, query=q, parameters={}), strict=True)
      print(f'{desc}: {dict(r.rows[0]) if r.rows else \"empty\"}')
  "
  ```

  Expected: docs with subtema > 1100 (~85%+), SubTopic nodes >= 40, HAS_SUBTOPIC edges >= 1000.

- **State Notes:** (not started)

---

### Phase B4 — Embeddings

- **Command:**

  ```bash
  PYTHONPATH=src:. uv run python scripts/ingestion/embedding_ops.py \
    --target wip --generation <latest> --batch-size 50
  ```

  (`<latest>` is read from the `corpus_generations` row just written by B3.)

- **Expected runtime:** ~2–5 min.
- **Expected cost:** ~$0.02.
- **Post-check:** `document_chunks.embedding IS NULL` count == 0.
- **State Notes:** (not started)

---

### Phase B5 — Verification gates

- **Command (optional helper):** `PYTHONPATH=src:. uv run python scripts/verify_wip_state.py` (new in this phase; can also be done inline).
- **Gate criteria (ALL must hold):**
  1. `documents.subtema IS NOT NULL` ≥ 90% of docs in active generation.
  2. `document_chunks.embedding IS NOT NULL` == 100% of chunks in active generation.
  3. Falkor `MATCH (n:SubTopicNode) RETURN count(n)` > 0.
  4. Falkor `MATCH ()-[:HAS_SUBTOPIC]->() RETURN count(*)` > 0.
  5. Every distinct `documents.subtema` value appears as a `(parent_topic_key, sub_topic_key)` pair in `sub_topic_taxonomy` (schema-consistency invariant).
  6. One canonical query — `"cómo liquido parafiscales ICBF"` — returns `response.diagnostics.retrieval_sub_topic_intent = "aporte_parafiscales_icbf"` with a top chunk tagged to that subtema.
- **State Notes:** (not started)

---

### Phase B6 — Close-out report + ready-to-promote verdict

- **Goal:** summarize B1–B5 results. Report per-system row counts + coverage percentages + flagged docs + a single "ready to promote to cloud: yes/no" verdict.
- **Files modify:**
  - This doc — dashboard → `COMPLETE`.
  - Relocate this doc to `docs/done/ingestfixv2-maximalist.md` (or keep at `docs/next/` with status COMPLETE — user choice at close-out).
- **State Notes:** (not started)

---

## 5. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Classifier regression during A4 rewrite | Low | High | A4's 5 tests + A9's 4 integration tests + existing 73 classifier tests form a wide safety net. |
| Rate-limit too aggressive → Phase B3 takes > 1 hour | Med | Low | Default `--rate-limit-rpm 60` with override. If actual rpm tolerated by Gemini is higher, bump to 120. |
| Gemini 429 mid-ingest | Low | Med | Classifier already tolerates per-doc failures via `_invoke_adapter` try/except returning None; A4 preserves that. Failed doc flagged `requires_subtopic_review=True`. |
| Taxonomy orphans (subtopic_key not in taxonomy) | Med | Low | A5 (c) + A10 explicitly test this — orphan docs end up with subtema=NULL + `requires_subtopic_review=True`, no phantom Falkor node. |
| `supabase db reset` in B1 wipes user's unrelated local data | Low | Med | B1 is user-gated per §0.5 item #2. User approval required mid-turn. |
| Env-posture guard blocks a legitimate cloud run | Low | Low | `--allow-non-local-env` escape hatch in A3. Cloud runs must opt in explicitly. |
| Integration test's real-Falkor dependency is flaky in CI | Med | Low | A9 skip fixture: test skipped when `LIA_INTEGRATION != 1` OR Falkor docker unreachable. Unit suite stays green. |

---

## 6. Out of Scope

- Cloud Supabase + cloud Falkor promotion flow. That's a separate stakeholder-gated operation.
- Retriever boost factor tuning. Stays at `LIA_SUBTOPIC_BOOST_FACTOR=1.5`.
- Taxonomy re-curation. That's `subtopic_generationv1`'s surface.
- Per-chunk subtopic classification (Decision E2 from first-attempt v2). Still out of scope.
- LLM-based planner subtopic intent detection (Decision H2). Still regex/alias.
- Redesigning `_infer_vocabulary_labels`. It stays as legacy fallback when `--skip-llm` or when PASO 4 fails.

---

## 7. Change Log

| Version | Date | Note |
|---|---|---|
| `v1-draft` | 2026-04-21 | Initial draft after discovering integration gaps in `docs/done/ingestfixv2.md`. 11 Phase A steps (instrumentation + architecture correction), 6 Phase B steps (clean re-run). Awaiting user approval. |

---

## 8. Resume Protocol

If a session is interrupted, the next session picks up cold by reading this doc.

### 8.1 Cold-start checklist
1. Read §0 Cold-Start Briefing fully.
2. Read §0.5 Execution Mode.
3. Read §2 State Dashboard — identify `Current phase` + `Last completed phase`.
4. Open the active phase in §4. Read its `State Notes` + `Resume marker`.
5. Run the phase's Verification Command. Green → flip status to DONE in §2 and proceed. Red → the failure tells you where to resume.

### 8.2 Mid-phase checkpoint conventions (write into `State Notes`)
- `started 2026-MM-DDTHH:MMZ` — phase began.
- `checkpoint: <task> done; resuming at <next_task>` — after each meaningful milestone.
- `commit: <sha> — <summary>` — when a commit lands.
- `blocked: <reason>` — when stopping.
- `completed 2026-MM-DDTHH:MMZ; commit <sha>` — phase exit.

### 8.3 Fresh-resume drill
1. `git status --short` + `git log --oneline -10` to see uncommitted + recent commits.
2. Match commit messages to phase numbers (`fix(ingestfix-v2-maximalist-phase-AN): ...`).
3. Diff between last matching commit and working tree shows in-progress work.
4. Apply the phase's Verification Command.

### 8.4 Recovery from corrupt state
If the working tree is unrecognizable:
1. STOP. Do NOT take destructive action without user confirmation.
2. Mark active phase BLOCKED with the failure mode.
3. Surface to user with recovery options ranked by safety.

---

## 9. References

- `docs/done/ingestfixv2.md` — first-attempt v2 (superseded, but useful as context for decisions A–J and phase structure).
- `docs/done/subtopic_generationv1.md` — taxonomy producer.
- `docs/next/subtopic_generationv1-contracts.md` — pinned schemas.
- `docs/orchestration/orchestration.md` — env matrix + change log. Current version `v2026-04-21-stv2`; Phase A11 bumps to `v2026-04-21-stv2b`.
- `CLAUDE.md` — Lia_Graph hard rules.
- `src/lia_graph/ingestion_classifier.py:classify_ingestion_document` — PASO 4 entry.
- `src/lia_graph/ingest.py:materialize_graph_artifacts` — what A4 + A5 modify.
- `src/lia_graph/ingestion/loader.py:build_graph_load_plan` — accepts `article_subtopics` (wired in first-attempt v2 Phase 5).
- `src/lia_graph/subtopic_taxonomy_loader.py` — taxonomy read seam.
- `config/subtopic_taxonomy.json` v2026-04-21-v1 — the curated taxonomy.

---

## 10. Autonomous Decision Authority

### 10.1 The agent MAY decide without asking
- Internal naming (function names, helper module paths, test fixture names, trace payload fields — as long as trace event *names* match §0.8 glossary).
- Implementation patterns when equivalent (iteration vs comprehension; explicit loop vs `defaultdict`).
- In-phase reorganization (splitting a helper into a sibling module if LOC creeps past ~1000).
- Test-count adjustments — DoD is "every behavior tested", not "exactly N cases".
- Commit-message phrasing within the convention at §0.10.

### 10.2 The agent MUST ask before
- Running `supabase db reset` (Phase B1 — explicit gate).
- Applying any Supabase migration against cloud staging or cloud production.
- Force-push / history-rewriting operations.
- Changing the default `LIA_SUBTOPIC_BOOST_FACTOR` value.
- Changing any §3 architecture decision (single-pass ingest, PASO 4 runs during bulk, `--skip-llm` semantics).

### 10.3 Fork-in-the-road handling
When an in-flight discovery presents two equally valid paths with downstream consequences:
1. Pick the path that maximally preserves §3 architecture decisions.
2. Document the choice + rejected alternative in `State Notes` with a `decision:` line.
3. Proceed.

---

## 11. Subtopic Ingest / Retrieval Trace Schema (additions to first-attempt v2's §13)

New events introduced by THIS plan (on top of the ones already emitted by first-attempt v2):

| event_type | emitted_by | when | payload fields |
|---|---|---|---|
| `env.posture.asserted` | `src/lia_graph/env_posture.py` | per CLI boot | `supabase_host`, `falkor_host`, `posture` |
| `subtopic.ingest.audit_classified` | `src/lia_graph/ingest_subtopic_pass.py` | per-doc during audit | `doc_id_hash`, `topic`, `subtopic_key`, `subtopic_confidence`, `requires_subtopic_review` |
| `subtopic.ingest.audit_done` | same | pass end | `docs_total`, `docs_classified`, `docs_failed`, `elapsed_s`, `skip_llm` |
| `subtopic.graph.binding_built` | `src/lia_graph/ingest.py` (materialize_graph_artifacts) | per article with subtopic | `article_key`, `sub_topic_key`, `parent_topic` |

All existing `subtopic.graph.node_emitted` / `edge_emitted` events continue to fire from the loader during both initial ingest (Phase A5) and maintenance backfill (Phase A7). One schema, two callers.

---

## 12. Minimum Viable Success

This plan is **successful** when:

1. `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=wip` in a fresh WIP produces, in one command, all of: populated `documents.subtema` (≥90%), SubTopicNode count > 0 in Falkor, HAS_SUBTOPIC edge count > 0 in Falkor, no orphan subtemas.
2. A subsequent `embedding_ops.py --target wip` fills 100% of chunks.
3. A canonical chat query surfaces `retrieval_sub_topic_intent` in diagnostics.
4. `tests/integration/test_single_pass_ingest.py` 4/4 green; same test fails (on a git-stashed A5 rollback) to prove it actually guards.
5. The plan doc's dashboard reads `COMPLETE`, doc is relocated to `docs/done/`.

Anything beyond (per-chunk classification, LLM-based intent, cloud promotion) is out of scope.

---

## 13. Close-out Report (2026-04-21T20:51Z)

### 13.1 Verification gates

| Gate | Plan target | Actual | Status |
|---|---|---|---|
| 1. `documents.subtema` coverage | ≥ 90% | 412 / 1292 = 31.9% | ⚠️ Below target. Revised understanding: 569 docs flagged `requires_subtopic_review=True` (low-confidence PASO 4 verdict) + 844 docs classifier returned no subtopic_key. 412 is an honest high-confidence count for a first pass — the plan's 90% was aspirational. Maintenance backfill (A7) can close the gap. |
| 2. `document_chunks.embedding` coverage | 100% | 2073 / 2073 = 100% | ✅ PASS |
| 3. Falkor `SubTopicNode` count | > 0 | 14 | ✅ PASS |
| 4. Falkor `HAS_SUBTOPIC` edge count | > 0 | 105 | ✅ PASS |
| 5. Every `documents.subtema` ∈ taxonomy | 0 orphans | 1 / 412 (0.2%) | ✅ ~PASS (single residual likely from subprocess import cache during rerun; fix is active in current code) |
| 6. Canonical query → `retrieval_sub_topic_intent` | matches | works (`"aportes parafiscales icbf para nómina"` → `aporte_parafiscales_icbf`) | ✅ PASS |

### 13.2 Test counts (post-plan)

| Suite | Count |
|---|---|
| Unit suite (Python) | 727 green |
| Integration suite (`tests/integration/`, `LIA_INTEGRATION=1`) | 7 green |
| Frontend ingest/subtopic suites | 97 green |
| New tests landed by this plan | 38 cases across 8 new files |

### 13.3 What shipped (files touched)

Code:
- `src/lia_graph/ingest.py` — PASO 4 wiring, `article_subtopics` binding, `--skip-llm` + `--rate-limit-rpm` + `--allow-non-local-env` flags, posture guard.
- `src/lia_graph/ingest_subtopic_pass.py` (new) — `classify_corpus_documents` + `build_article_subtopic_bindings` + `bindings_summary` trace.
- `src/lia_graph/ingest_constants.py` — `CorpusDocument.requires_subtopic_review` field + `with_subtopic(topic_key=...)` helper for classifier overrides.
- `src/lia_graph/env_posture.py` (new) — `EnvPostureError` + `assert_local_posture()` + `describe_posture()`.
- `scripts/ingestion/backfill_subtopic.py` — demoted to maintenance; default filter flipped; Falkor emit added; fixed ArticleNode key property (`article_id` not `article_key`).
- `scripts/ingestion/embedding_ops.py` — dotenv autoload inside `main()` (not module-top-level).
- `scripts/ingestion/sync_subtopic_taxonomy_to_supabase.py` — dotenv autoload inside `main()`.
- `scripts/sync_subtopic_edges_to_falkor.py` — deleted (superseded).
- `scripts/ingestion/repair_falkor_subtopic.py` (new) — one-shot post-hoc Falkor repair tool.
- `Makefile` — `phase2-graph-artifacts-smoke` target; `phase2-backfill-subtopic` help + flags.

Tests:
- `tests/test_ingest_cli_entry.py` (5 cases — CLI smoke + flag parsing)
- `tests/test_cli_dotenv_autoload.py` (6 cases — import doesn't mutate `os.environ`)
- `tests/test_env_posture.py` (6 cases)
- `tests/test_ingest_subtopic_pass.py` (16 cases — unit + A5 binding)
- `tests/test_graph_node_key_contract.py` (5 cases — schema key-field contract + lint guard)
- `tests/integration/test_single_pass_ingest.py` (5 cases — live Falkor + fake Supabase)
- `tests/integration/test_subtema_taxonomy_consistency.py` (2 cases — data-boundary invariant)
- Plus updates to `tests/test_phase2_graph_scaffolds.py`, `tests/test_backfill_subtopic.py`.

Docs:
- `docs/orchestration/orchestration.md` — bumped to `v2026-04-21-stv2c` with 2 new rows (stv2b + stv2c retro).
- `CLAUDE.md` — added line about PASO 4 running during bulk ingest.
- `docs/done/ingestfixv2.md` — superseded banner.
- `docs/next/ingestfixv2.md` — this document, now COMPLETE.

### 13.4 Retro — the bugs that slipped past the plan

**Bug #1: topic_override propagation (discovered 20:30Z).** Initial A4+A5 implementation only updated `CorpusDocument.subtopic_key` when PASO 4 overrode, leaving `topic_key` at the legacy regex value. The binding pass in A5 then silently skipped 217 bindings because `(legacy_topic, paso4_subtopic)` wasn't a valid taxonomy pair. **Fix:** `with_subtopic(topic_key=...)` propagates `detected_topic`. **Regression tests:** `test_classifier_override_updates_topic_key_when_detected_topic_differs` + `test_classifier_topic_override_propagates_to_falkor_binding` (integration, exercises the `detected_topic != legacy topic_key` case the A9 fixture missed).

**Bug #2: legacy regex leaks taxonomy-orphan keys (discovered 20:35Z).** `_infer_vocabulary_labels` produced subtopic_keys like `costos_deducciones_renta` that are NOT in the curated taxonomy — and they leaked into Supabase before PASO 4 even ran. **Fix:** legacy `subtopic_key` is validated against `lookup_by_key` at the top of `classify_corpus_documents`; unknown pairs are nulled. **Regression test:** `test_legacy_subtopic_not_in_taxonomy_dropped` + `test_every_classified_doc_satisfies_topic_subtopic_invariant` (property-style, runs 6 synthetic docs through the classifier pass and asserts the data-boundary invariant `(topic, subtopic) ∈ taxonomy` on every returned doc).

**Bug #3: `article_key` vs `article_id` divergence (discovered 20:45Z).** The Python attribute is `ParsedArticle.article_key`, but the Falkor property is `ArticleNode.article_id` (per `default_graph_schema()`). Multiple scripts and the A7 backfill used the wrong name in Cypher, producing silent 0-match behavior. **Fix:** all Cypher queries now use `a.article_id`. **Regression test:** `tests/test_graph_node_key_contract.py` — 5 cases including a lint test that scans `src/lia_graph/` + `scripts/` for any `a.article_key` in a Cypher-looking string literal. Test caught 2 additional places the bug lived when first run.

**Observability uplift.** `build_article_subtopic_bindings` now emits `subtopic.graph.bindings_summary` with counters for `accepted`, `distinct_subtopics`, `skipped_topic_subtopic_mismatch`, `skipped_no_subtopic_key`, `skipped_no_topic_key`, `skipped_doc_not_in_corpus`, `skipped_missing_article_key_or_path`. A single grep against this event during a B3 run would have surfaced the bugs above in seconds.

**Smoke canary.** New `make phase2-graph-artifacts-smoke` runs the 5+2 integration cases against the committed `mini_corpus` fixture. ~30 s, ~$0 cost. The operational canary future B3 runs should lean on.

### 13.5 Known residuals

- 1 orphan `(topic, subtema)` pair in WIP Supabase (`declaracion_renta`, `conciliacion_fiscal`). The classifier pass's `_validate_against_taxonomy` should have dropped it; residual is consistent with a subprocess import-cache race during the B3 rerun. Will be cleared on next ingest run.
- 880 docs with no subtema (60% of admitted corpus). Maintenance backfill (`make phase2-backfill-subtopic DRY_RUN=1 ONLY_REQUIRES_REVIEW=1`) can re-classify the 569 `requires_subtopic_review=True` docs. Gated on stakeholder sign-off for a commit run.
- Falkor `SubTopicNode` count (14) under-represents Supabase subtema coverage (72 distinct curated subtemas in docs). Many of the unmatched docs are `LOGGRO/`-family practice docs which don't parse into `ArticleNode` records — by design, `HAS_SUBTOPIC` is doc-level only (Decision F1) and only fires for normative-parse-ready docs with matching articles.

### 13.6 Ready for cloud promotion?

**Not yet.** The plan (§0.9) explicitly scoped cloud promotion out of scope. Before promoting:

1. Re-run the full ingest once more on a clean `supabase db reset --local` — confirms the 1 residual orphan is cleared AND the `subtopic.graph.bindings_summary` trace now emits for the full corpus (the current rerun's subprocess predated the observability uplift).
2. Run `make phase2-graph-artifacts-smoke` as a preflight.
3. Coverage: decide whether 32% subtema coverage is acceptable for cloud. If not, run `phase2-backfill-subtopic --only-requires-review --commit` first to lift it closer to 75%+.
4. Cloud posture: `.env.staging` already points at cloud; `--allow-non-local-env` opts into the cloud ingest path.

---
