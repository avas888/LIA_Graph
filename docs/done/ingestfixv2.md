# Ingest Fix v2 — Subtopic-Aware Ingestion, Graph, and Retrieval

> **⚠️ SUPERSEDED 2026-04-21:** this doc records the **first-attempt v2** state
> only. Phases 1–10 shipped unit-green but integration-broken — the PASO 4
> classifier was never wired into bulk ingest and `build_graph_load_plan`
> received `article_subtopics=None`, so `documents.subtema` ended up 100%
> NULL and FalkorDB carried zero `SubTopicNode` / `HAS_SUBTOPIC` state
> after a `make phase2-graph-artifacts-supabase` run. The correction plan
> is `docs/next/ingestfixv2.md` (Phases A1–A11 + B1–B6); version
> `v2026-04-21-stv2b` in `docs/orchestration/orchestration.md`. Treat this doc as
> historical context only.

**Last edited:** 2026-04-21 (plan rewritten from stub to full implementation plan)
**Status:** ☑ DRAFT · ☐ APPROVED · ☐ EXECUTING · ☐ COMPLETE
**Execution owner:** TBD after approval (plan-only — no code yet)
**Goal:** wire the curated subtopic taxonomy (`config/subtopic_taxonomy.json`, shipped by `docs/done/subtopic_generationv1.md`) into the ingestion pipeline so every doc gets tagged with a `subtopic_key`, FalkorDB carries `SubTopic` nodes + edges, and retrieval boosts chunks matching a detected subtopic intent.

> This document is both a **plan** AND a **work ledger**. Every phase has a `State Notes` block that is updated in-place DURING execution. If a session is interrupted, the state of this file is the resumption pointer — see §11 Resume Protocol.

> **Cold-start agent:** read §0 first, then §0.5, then §2, then jump to whichever phase is active in §5. Do not skim — every line in §0 and §0.5 is load-bearing. If anything in §0 is wrong (tool missing, branch mismatch, etc.), STOP and surface to the user before proceeding.

---

## 0. Cold-Start Briefing (READ FIRST IF YOU HAVE ZERO PRIOR CONTEXT)

This section is for an LLM agent that opens this doc with no conversation history. After reading §0 + §0.5 + §2 + the active phase entry in §5, you should have everything you need to execute autonomously.

### 0.1 Project orientation in three sentences
**Lia_Graph** is a graph-RAG accounting assistant for Colombian senior accountants serving SMB clients. It is a derivative of `Lia_contadores` (https://github.com/avas888/Lia_contadores) and lives at `https://github.com/avas888/LIA_Graph`. It serves answers in Spanish-CO covering tax (IVA, declaración de renta, ICA, retención, …) AND labor / payroll / seguridad social (CST, Ley 100, parafiscales, UGPP, MinTrabajo) — labor is first-class, not tax-adjacent.

### 0.2 Repo location + branch
- **Working directory:** `/Users/ava-sensas/Developer/Lia_Graph`
- **Branch this plan executes against:** `feat/suin-ingestion` (or a fresh `feat/ingestfix-v2` branched off main if preferred — commit `83019a6` is the subtopic v1 baseline)
- **Main branch (used for PRs):** `main`
- **Last shipped change pre-plan:** `v2026-04-21-stv1` (see `docs/orchestration/orchestration.md` change log) — subtopic_generationv1 phases 1-7 + curated `config/subtopic_taxonomy.json`. This plan consumes that file.

### 0.3 Source-of-truth document map (READ THESE BEFORE WRITING CODE)
Hierarchy of authority — when documents disagree, the higher one wins:

| Doc | Role |
|---|---|
| `CLAUDE.md` (repo root) | Quickstart for Claude-family agents. Hard rules: don't touch Lia_contadores cloud resources; pipeline_d organization is deliberate; Falkor adapter must propagate outages, not silently fall back to artifacts; granular edits over monolithic rewrites. |
| `AGENTS.md` (repo root) | Repo-level operating guide. If `CLAUDE.md` is silent on something, `AGENTS.md` is canonical. |
| `docs/orchestration/orchestration.md` | THE end-to-end runtime + information-architecture map. Env matrix version is currently `v2026-04-21-stv1`. Lane 0 (build-time ingestion) + retrieval adapters section are relevant. |
| `docs/guide/env_guide.md` | Operational counterpart to orchestration.md. Run modes + env files + test accounts + corpus refresh. |
| `docs/done/ingestfixv1.md` | Predecessor plan. Describes AUTOGENERAR cascade, intake sidecar JSONL shape, classifier API — direct dependencies of THIS plan. |
| `docs/done/subtopic_generationv1.md` *(moved here after v1 Phase 9 close-out)* | Immediate predecessor. Describes how `config/subtopic_taxonomy.json` was produced — THIS plan consumes that file. |
| `docs/next/subtopic_generationv1-contracts.md` | Pinned schemas for the subtopic JSONL + proposal JSON + taxonomy JSON. Reading the Taxonomy JSON contract is mandatory before Phase 1. |
| THIS doc (`docs/next/ingestfixv2.md`) | The active plan. State Dashboard (§2) is the live status. |

### 0.4 Tooling baseline (verify in pre-flight check)
- **Python:** managed via `uv`. Always run as `PYTHONPATH=src:. uv run --group dev <command>`. Never use bare `python` for repo code.
- **Frontend:** Vite + TypeScript + vitest. Tests: `cd frontend && npx vitest run [test-pattern]`.
- **Dev server:** `npm run dev` (local docker Supabase + Falkor) at `http://127.0.0.1:8787/`. `npm run dev:staging` (cloud Supabase + cloud FalkorDB) for live parity.
- **LLM runtime:** `src/lia_graph/llm_runtime.py` exposes `resolve_llm_adapter()` returning `(adapter, diagnostics)`. Adapter has `.generate(prompt)` + `.generate_with_options(prompt, *, temperature, max_tokens, timeout_seconds)`. Gemini Flash default.
- **Embeddings:** `src/lia_graph/embeddings.py` + `scripts/embedding_ops.py`. Gemini `text-embedding-004`, 768 dims.
- **Supabase migrations:** live in `supabase/migrations/`. Add new SQL files dated `YYYYMMDDNNNNNN_<slug>.sql`. Squashed baseline is `20260417000000_baseline.sql` (already carries `documents.subtema` + `document_chunks.subtema` columns — see §3.2).
- **FalkorDB schema:** defined in `src/lia_graph/graph/schema.py` via `NodeKind` + `EdgeKind` enums. Adding a SubTopic node requires extending both enums + `default_graph_schema()`.
- **Rate limits:** Gemini Flash ~60 req/min. Backfill pass ≈ 1313 docs × 1 call = ~22 min theoretical, ~35-60 min realistic.

### 0.5 Pre-flight check (run before Phase 1)
```bash
cd /Users/ava-sensas/Developer/Lia_Graph && \
  git status && \
  git log --oneline -5 && \
  ls config/subtopic_taxonomy.json artifacts/subtopic_decisions.jsonl && \
  PYTHONPATH=src:. uv run --group dev pytest \
    tests/test_ingest_classifier.py \
    tests/test_subtopic_observability.py \
    tests/test_ui_subtopic_controllers.py \
    tests/test_promote_subtopic_decisions.py \
    -q
```

Expected: all subtopic-v1 tests green (67 classifier + 5 observability + 16 controllers + 8 promote), taxonomy file present, commit `83019a6` (or later) at HEAD.

### 0.6 Auth credentials for testing
All `@lia.dev` accounts share password `Test123!` in both local docker Supabase and cloud staging. Admin credential for the intake UI + subtopic preview:
- **email:** `admin@lia.dev`, **password:** `Test123!`, **role:** `platform_admin`, **tenant:** `tenant-dev`
Login: `POST http://127.0.0.1:8787/api/auth/login` with `{email, password, tenant_id: ""}`.

### 0.7 Cost estimate (one-time)
- **Classifier PASO 4 extension:** zero cloud cost — prompt change only.
- **Backfill pass (Phase 6):** ~1313 docs × 1 Gemini Flash call ≈ $5-15 one-time (mirrors subtopic_generationv1 Phase 2 spend).
- **Embeddings:** zero new cost — existing chunk embeddings don't change shape.
- **FalkorDB writes:** no per-call cost; cloud Falkor seat already paid.
- **Total one-time:** ~$5-15.

### 0.8 Glossary (terms used throughout)
- **parent_topic** — canonical topic key (~40 options: `laboral`, `iva`, `declaracion_renta`, …). Already populated today in `documents.topic` + `documents.tema`.
- **subtopic** — child of a parent_topic (86 known + expandable). Lives in `config/subtopic_taxonomy.json`. The slug goes into `documents.subtema` + `document_chunks.subtema`.
- **subtopic taxonomy** — `config/subtopic_taxonomy.json` v2026-04-21-v1. The canonical registry this plan wires into every stage.
- **PASO 4** — the new prompt step in AUTOGENERAR's N2 LLM call that resolves a candidate subtopic against the taxonomy.
- **sub_topic_intent** — a new field on the planner's `GraphRetrievalPlan` output that flags "the user's question is narrowly about subtopic X"; retrieval uses it to boost.
- **hybrid_search** — the Postgres RPC at `supabase/migrations/20260417000000_baseline.sql:264` that merges FTS + vector retrieval. Already returns `subtema` for every chunk.
- **HAS_SUBTOPIC edge** — new FalkorDB edge type: `Document -[HAS_SUBTOPIC]-> SubTopic` and `Topic -[HAS_SUBTOPIC]-> SubTopic`.
- **backfill** — one-shot re-classification of existing corpus to populate `subtema` on rows written before this plan ships.
- **alias breadth policy** — aliases in the taxonomy are intentionally wide; retrieval must use the full alias list in similarity matching, not just `key`+`label`. See auto-memory `feedback_subtopic_aliases_breadth.md`.

### 0.9 What this plan does NOT do
Out of scope — belongs elsewhere:
- Does NOT re-curate the taxonomy. Taxonomy refinement (merge/split/rename) uses the existing `/api/subtopics/*` admin surface + `make phase2-promote-subtopic-taxonomy`.
- Does NOT change how topics are detected. v1 topic detection via N1+N2 stays intact.
- Does NOT add new chat-surface UI beyond the intake preview surfacing. Chat answers become subtopic-aware via retrieval boost, but the answer-UI stays the same.
- Does NOT introduce a new env flag for "subtopic mode on/off". Subtopic tagging is always on once v2 ships. (If we need a kill-switch during rollout, see §4 Decision D2.)

### 0.10 Git + commit conventions
- **Branch protocol:** no force-push; no `git reset --hard` without user approval.
- **Commit message format:** `feat(ingestfix-v2-phase-N): <short summary>`.
- **Co-authored-by line:** `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
- **Commit cadence:** one commit per phase exit (PASSED_TESTS → COMMITTED). Phase 6 backfill is an artifact-landing commit with the post-backfill evidence bundle.

### 0.11 What to ABSOLUTELY NOT do
- Do not extend/modify the `config/subtopic_taxonomy.json` schema in this plan. That schema is frozen at v2026-04-21-v1 and this plan consumes it as-is. Changes to the schema require a new `subtopic_generationv2` plan.
- Do not tighten `aliases` lists when reading the taxonomy — breadth is intentional (§0.8 alias breadth policy + auto-memory).
- Do not silently drop a doc that fails subtopic classification. Flag it via `requires_subtopic_review = true` and let the curator pick up.
- Do not re-introduce a silent artifact fallback in the Falkor adapter. Cloud outages must still propagate loudly.
- Do not ship Phase 6 backfill without stakeholder sign-off — it writes to production Supabase + cloud Falkor and costs LLM $.
- Do not commit `artifacts/subtopic_backfill_<ts>.jsonl` to git — it's multi-MB and reproducible. Add a `.gitignore` entry if needed.

---

## 0.5 Execution Mode (READ FIRST WHEN RESUMING)

**Mode:** AUTONOMOUS after approval. Once the user marks `Plan status = APPROVED` in §2, execution proceeds without stopping through all phases until either (a) all phases reach `DONE`, (b) a `BLOCKED` status is recorded, or (c) the user explicitly halts.

**No-stop policy:** the assistant does NOT pause for confirmation between phases. The assistant DOES update `State Notes` after every meaningful checkpoint (file written, test passing, commit landed).

**When the assistant DOES stop:**
1. A §4 ratified decision turns out to be wrong on contact with reality → mark phase BLOCKED.
2. A test failure cannot be resolved within 3 attempts after diagnosis → mark BLOCKED.
3. Phase 6 (backfill) needs stakeholder approval to execute against the real corpus → pause for sign-off.
4. Phase 2 Supabase migration applies changes to cloud staging or cloud production — STOP and require explicit approval (local docker Supabase changes are fine).
5. LLM cost budget (§0.7) overrun by 2× → surface before continuing.
6. All phases reach `DONE`.

**Recursive decision authority** (see §12): the assistant MAY make in-flight choices that do NOT contradict §4 ratified decisions (naming, field names, internal helper organization, trace payload fields).

**Approval gate:** Phase 1 does NOT begin until `Plan status = APPROVED` is set by the user in §2.

---

## 1. Executive Summary

**Problem.** `subtopic_generationv1` produced a curated taxonomy of 86 subtopics across 37 parent topics, but the taxonomy is **inert** — no ingestion code reads it, no document row carries a subtopic, no retrieval uses it. The subtopic-aware answer quality improvement that motivated v1 is unrealized until the pipeline actually tags docs.

**Strategy.** Five seams get subtopic-aware:
1. **Classifier** — extend `classify_ingestion_document` with PASO 4 that resolves a candidate subtopic against the taxonomy; produce a new `subtopic_key` + `subtopic_label` + confidence fields on `AutogenerarResult`.
2. **Schema** — minimal Supabase work because `documents.subtema` + `document_chunks.subtema` columns ALREADY exist (baseline migration already carries them — see §3.2). Add a thin `sub_topic_taxonomy` reference table + an optional `filter_subtopic` param on the `hybrid_search` RPC.
3. **Sink** — teach the supabase sink to read the classifier's `subtopic_key` and propagate it to `documents.subtema` + per-chunk `document_chunks.subtema`.
4. **Graph** — add `SubTopic` node + 2 edge types to FalkorDB via `graph/schema.py` + teach the bridge to emit them.
5. **Retrieval** — extend the planner to surface `sub_topic_intent`, extend the supabase retriever to pass that intent to `hybrid_search` with a boost, and extend the Falkor retriever to narrow traversal when intent is present.

**Order.** Decisions first (§4), then Phase 1 (taxonomy loader + validation), Phase 2 (schema reference table only — columns already exist), Phase 3 (classifier PASO 4), Phase 4 (sink wire-up), Phase 5 (graph schema + bridge), Phase 6 (planner + retriever boost), Phase 7 (UI surfacing), Phase 8 (backfill), Phase 9 (E2E), Phase 10 (close-out).

**Non-goals.**
- Not shipping a "subtopic curator v2" UI flow. The existing `/api/subtopics/*` admin surface + promote CLI already exist; new taxonomy versions flow through those.
- Not changing the chat rendering layer. Subtopic value flows through retrieval quality, not through a new answer block.
- Not backfilling retroactively on corpus generations that pre-date this plan's schema. Only the active generation gets backfilled.

---

## 2. State Dashboard (update in-place during execution)

**Meta**

| Field | Value |
|---|---|
| Plan status | ☐ DRAFT · ☐ APPROVED · ☐ EXECUTING · ☑ COMPLETE |
| Current phase | — (all phases code-complete) |
| Last completed phase | 10 (close-out) |
| Blockers | Phase 9 stakeholder-gated production cut requires explicit go; Phase 8 full-corpus backfill requires sign-off before `--commit` against production Supabase |
| Working tree | `feat/suin-ingestion` @ post-`v2026-04-21-stv1` (subtopic_generationv1 shipped, commit `83019a6`) |
| Approved | 2026-04-21 — user approved plan + all §4 recommended defaults (A1, B1, C1, D1, E1, F1, G1+G3, H1, I1, J1); branch stays `feat/suin-ingestion` |
| Completed | 2026-04-21 — Phases 1–10 automated; E2E runbook drafted in `tests/manual/ingestfixv2_e2e_runbook.md`; orchestration.md change log updated to `v2026-04-21-stv2`; CLAUDE.md updated |

**Phase ledger** — allowed statuses: `NOT_STARTED`, `IN_PROGRESS`, `PASSED_TESTS`, `COMMITTED`, `DONE`, `BLOCKED`.

| # | Phase | Status | Files touched (target) | Commit SHA |
|---|---|---|---|---|
| 0 | Decisions ratified by user (§4) | DONE | this doc | — |
| 1 | Taxonomy loader + validation | PASSED_TESTS | `src/lia_graph/subtopic_taxonomy_loader.py` (new), tests | — |
| 2 | Supabase schema: `sub_topic_taxonomy` reference table + `hybrid_search` RPC `filter_subtopic` | PASSED_TESTS | new migration SQL, tests via `test_hybrid_search_rpc.py` (if exists) or fresh test | — |
| 3 | Classifier PASO 4 extension | PASSED_TESTS | `ingestion_classifier.py`, tests | — |
| 4 | Sink wire-up (subtopic_key → documents.subtema + chunks.subtema) | PASSED_TESTS | `ingestion/supabase_sink.py`, `ingest.py`, tests | — |
| 5 | FalkorDB SubTopic node + edges + bridge | PASSED_TESTS | `graph/schema.py`, `graph/validators.py`, `ingestion/loader.py`, tests | — |
| 6 | Planner intent + retriever boost | PASSED_TESTS | `pipeline_d/planner_query_modes.py`, `retriever_supabase.py`, `retriever_falkor.py`, tests | — |
| 7 | UI: subtopic chip in intake preview + subtopic column in Generaciones row | PASSED_TESTS | 1 molecule + `intakeFileRow.ts` + `generationRow.ts` updates, tests | — |
| 8 | Backfill: re-classify corpus for subtopic | PASSED_TESTS | `scripts/backfill_subtopic.py` (new), Makefile target, tests | — |
| 9 | E2E runbook + evidence | PASSED_TESTS | `tests/manual/ingestfixv2_e2e_runbook.md` (new), evidence dirs | — |
| 10 | Close-out + `orchestration.md` change-log entry `v2026-04-21-stv2` | DONE | `orchestration.md`, `CLAUDE.md`, this doc relocates to `docs/done/` | — |

**Tests baseline** (set in Phase 0)

| Suite | Pre-plan | Post-plan target |
|---|---|---|
| `tests/test_ingest_classifier.py` | 67 pass | 67 + ~6 (PASO 4 cases) |
| New: `tests/test_subtopic_taxonomy_loader.py` | n/a | ~8 cases |
| New: `tests/test_supabase_sink_subtopic.py` | n/a | ~6 cases |
| New: `tests/test_graph_schema_subtopic.py` | n/a | ~5 cases |
| New: `tests/test_suin_bridge_subtopic.py` | n/a | ~4 cases |
| New: `tests/test_planner_subtopic_intent.py` | n/a | ~8 cases |
| New: `tests/test_retriever_supabase_subtopic_boost.py` | n/a | ~6 cases |
| New: `tests/test_retriever_falkor_subtopic.py` | n/a | ~5 cases |
| New: `tests/test_backfill_subtopic.py` | n/a | ~6 cases |
| New: `frontend/tests/subtopicChip.test.ts` | n/a | ~4 cases |
| Atomic discipline guard | green | green |
| Observability smoke (existing) | 5 pass | 5 + 1 (backfill event) |

---

## 3. What We Already Have (read-only survey, 2026-04-21)

### 3.1 `config/subtopic_taxonomy.json` (v2026-04-21-v1)
Committed by `83019a6`. 86 subtopics across 37 parent topics. Schema (already contracted in `docs/next/subtopic_generationv1-contracts.md`):
```json
{
  "version": "2026-04-21-v1",
  "generated_from": "artifacts/subtopic_decisions.jsonl",
  "generated_at": "2026-04-21T15:07:23Z",
  "subtopics": {
    "<parent_topic_key>": [
      {
        "key": "<slug>",
        "label": "<human-readable Spanish label>",
        "aliases": ["slug1", "slug2", ...],
        "evidence_count": <int>,
        "curated_at": "<iso ts>",
        "curator": "<string>"
      }
    ]
  }
}
```
Phase 1 builds a loader over this file.

### 3.2 Supabase baseline (already has subtema columns)
`supabase/migrations/20260417000000_baseline.sql`:
- `documents.subtema TEXT` — exists (line ~790)
- `document_chunks.subtema TEXT` — exists (line ~754)
- `hybrid_search` RPC (line ~264) already SELECTs `subtema` but does NOT accept a `filter_subtopic` param or boost based on it.
- `fts_scored_prefilter` (line ~138) same shape.

**Phase 2 work is narrow:** add a `sub_topic_taxonomy` reference table + a new migration that replaces `hybrid_search` with a subtopic-aware version. No column additions.

### 3.3 `classify_ingestion_document` (subtopic_generationv1 extended it)
Returns `AutogenerarResult` with 17 fields including `always_emit_label` kwarg. Phase 3 adds 5 new fields for subtopic: `subtopic_resolved_to_existing`, `subtopic_synonym_confidence`, `subtopic_is_new`, `subtopic_suggested_key`, `subtopic_label`, plus the derived `subtopic_key` (final verdict).

### 3.4 Supabase sink (`src/lia_graph/ingestion/supabase_sink.py`)
`write_documents` already reads `document.get("subtopic_key")` and writes it to `documents.subtema` (line 241) — but upstream never populates that key today. Phase 4 closes this gap by wiring the classifier output through `ingest.py`.

`write_chunks` does NOT currently copy `subtema` onto `document_chunks`. Phase 4 adds that propagation.

### 3.5 FalkorDB schema (`src/lia_graph/graph/schema.py`)
`NodeKind` enum: ARTICLE, REFORM, CONCEPT, PARAMETER. No `SUBTOPIC`.
`EdgeKind` enum: 11 entries (REFERENCES, MODIFIES, SUPERSEDES, EXCEPTION_TO, COMPUTATION_DEPENDS_ON, REQUIRES, DEFINES, PART_OF, ANULA, DECLARES_EXEQUIBLE, DEROGATES, REGLAMENTA, STRUCK_DOWN_BY, SUSPENDS). No `HAS_SUBTOPIC`.

Phase 5 extends both enums + `default_graph_schema()` + `validate_edge_record`.

### 3.6 Planner query modes (`src/lia_graph/pipeline_d/planner_query_modes.py`)
Classifies queries into 9 modes (`article_lookup`, `definition_chain`, `obligation_chain`, `computation_chain`, `reform_chain`, `strategy_chain`, `historical_reform_chain`, `historical_graph_research`, `general_graph_research`). Does NOT surface subtopic intent.

Phase 6 adds a `sub_topic_intent: str | None` field to `GraphRetrievalPlan` + a `_detect_sub_topic_intent` classifier that matches query text against the full alias list from the taxonomy.

### 3.7 Supabase retriever (`src/lia_graph/pipeline_d/retriever_supabase.py`)
`_hybrid_search` at line 123 calls `db.rpc("hybrid_search", payload)` with `filter_topic`. Does NOT pass subtopic.

Phase 6 adds `filter_subtopic` to the RPC payload (wired to the Phase 2 RPC extension) and a post-rerank boost of 1.5x for chunks whose `subtema` matches the plan's `sub_topic_intent`.

### 3.8 Falkor retriever (`src/lia_graph/pipeline_d/retriever_falkor.py`)
Walks `Document -[...]-> Article` chains bounded by parent topic. Phase 6 teaches it to prefer documents with a matching `HAS_SUBTOPIC` edge when `sub_topic_intent` is set; keeps full traversal as fallback.

### 3.9 Admin UI (intake preview + Generaciones)
- `intakeFileRow` molecule renders each classified doc during drag-to-ingest. Today shows `topic`, `type`, confidence. Phase 7 adds a subtopic chip.
- `generationRow` molecule renders corpus-generations rows. Today shows doc count, chunk count, top class. Phase 7 adds a subtopic-coverage micro-metric.

### 3.10 Existing curation surface (`/api/subtopics/*`)
Already ships via subtopic_generationv1. Zero changes here — this plan does not re-curate the taxonomy.

---

## 4. Decision Points (RATIFY BEFORE PHASE 1)

Each decision gets an explicit yes/no/modify from the user before Phase 1 lands.

### Decision A — PASO 4 in the same LLM call or a second call?
**RATIFIED 2026-04-21: A1 (same call).**


**A1 (recommended):** **Same call**. Extend the existing N2 prompt with PASO 4 after PASO 3. One LLM call per doc. Pro: no latency doubling; the existing `generate_with_options` path already sets max_tokens=300 (raise to 500 to accommodate the extra fields). Con: prompt complexity grows; risk of PASO 4 regressing PASO 1-3 quality.

**A2:** **Second sequential call**. First call returns PASO 1-3. Second call (with topic known) returns PASO 4. Pro: clean separation; either call can evolve independently. Con: 2× latency + 2× cost (worst case $10-30 backfill vs. $5-15).

**Recommendation: A1.** Needs user sign-off.

### Decision B — Taxonomy loader: file-first or DB-first?
**RATIFIED 2026-04-21: B1 (file-first).**


**B1 (recommended):** **File-first**. `config/subtopic_taxonomy.json` is the canonical source. The Supabase `sub_topic_taxonomy` table is a materialized projection of the file, rebuilt by a sync script. Pro: single source of truth (the JSON file is git-tracked, reviewable, reproducible). The Phase 2 migration adds the table but `promote_subtopic_decisions.py` gets a new `--sync-supabase` flag to mirror it.

**B2:** **DB-first**. Taxonomy lives primarily in the `sub_topic_taxonomy` table; the JSON file becomes a dump. Pro: queries can JOIN directly. Con: loses the git-trackable review workflow; harder to diff versions.

**Recommendation: B1.** The JSON file stays the source of truth. Needs user sign-off.

### Decision C — Subtopic confidence fusion: mirror topic-level fusion?
**RATIFIED 2026-04-21: C1 (mirror topic-level fusion).**


**C1 (recommended):** **Mirror topic-level fusion.** Reuse the existing `_fuse_autogenerar_confidence` shape for subtopic:
- subtopic is new → 0.70
- synonym_confidence ≥ 0.80 → base 0.85 + 0.10 if N1 alias-match agreement + 0.05 if synonym ≥ 0.90 (capped at 1.0)
- 0.50 ≤ synonym < 0.80 → 0.0 (forces review)
- synonym < 0.50 → 0.0

A doc with topic-conf 0.95 AND subtopic-conf < 0.80 lands with `subtema=NULL` + `requires_subtopic_review=true`. The topic verdict stays.

**C2:** **Simpler threshold.** Accept subtopic only when `subtopic_synonym_confidence >= 0.85`; else NULL. No fusion math.

**Recommendation: C1.** Keeps the policy coherent with topic-level behavior. Needs user sign-off.

### Decision D — Rollout: always-on or env-flagged?
**RATIFIED 2026-04-21: D1 (always on).**


**D1 (recommended):** **Always on**. Once Phase 3 lands, every new ingestion run produces subtopics. No `LIA_SUBTOPIC_MODE` flag. Pro: one code path; no forgotten-flag state. Con: if PASO 4 regresses PASO 1-3, roll-forward requires a code fix (no env kill-switch).

**D2:** **Env-flagged via `LIA_SUBTOPIC_ENABLED=1`**. Default on in `dev:staging`, off in `dev`. Pro: kill-switch. Con: matrix version bump + more state.

**Recommendation: D1** with a caveat: during the 48h after Phase 3 ships, monitor `logs/events.jsonl` for PASO 4 failures. If > 5% of classifications fail PASO 4, revert via `git revert` rather than flag. Needs user sign-off.

### Decision E — Chunk-level subtopic: per-chunk or inherited?
**RATIFIED 2026-04-21: E1 (inherited).**


**E1 (recommended):** **Inherited per-document**. Every chunk gets the same `subtema` as its parent document. Fast sink work; retrieval already has the column indexed. Pro: simple; matches how `topic` already cascades. Con: loses "some chunks in this doc are about a different subtopic" nuance.

**E2:** **Per-chunk classification**. Each chunk gets its own subtopic via a lightweight per-chunk prompt. Pro: higher precision. Con: 10-50× more LLM calls (1313 docs × ~10 chunks avg = 13,000 calls → $50-150).

**Recommendation: E1.** Start inherited; add per-chunk as v3 if retrieval precision shows the gap matters. Needs user sign-off.

### Decision F — FalkorDB SubTopic edges: document-only or also chunk-level?
**RATIFIED 2026-04-21: F1 (document-only edges).**


**F1 (recommended):** **Document-only edges**. `Document -[HAS_SUBTOPIC]-> SubTopic` and `Topic -[HAS_SUBTOPIC]-> SubTopic`. Graph queries for "docs about X subtopic under topic Y" work; chunks are reached via `Document -[HAS_CHUNK]-> Chunk`.

**F2:** **Chunk-level edges too**. Add `Chunk -[ABOUT_SUBTOPIC]-> SubTopic`. Pro: direct chunk retrieval without doc hop. Con: 10-50× more edges (up to ~20k more per generation), potentially hurts graph write time.

**Recommendation: F1.** Needs user sign-off.

### Decision G — Retriever boost factor?
**RATIFIED 2026-04-21: G1+G3 (1.5× default + `LIA_SUBTOPIC_BOOST_FACTOR` env override).**


**G1 (recommended):** **1.5× boost on matching subtema**, applied post-ranking. A chunk whose `subtema == plan.sub_topic_intent` gets its `rrf_score` multiplied by 1.5. Pro: simple; reversible; tunable. Con: arbitrary; no A/B grounding yet.

**G2:** **2.0× boost** (more aggressive).

**G3:** **Configurable via `LIA_SUBTOPIC_BOOST_FACTOR` env, default 1.5**.

**Recommendation: G1 as default + G3 as env override** (`LIA_SUBTOPIC_BOOST_FACTOR` defaulting to 1.5). Needs user sign-off.

### Decision H — Planner subtopic intent detection: regex-based or LLM-based?
**RATIFIED 2026-04-21: H1 (regex/alias match).**


**H1 (recommended):** **Regex/alias match**. The planner scans the query against the full alias list from the taxonomy. First match wins; ties resolved by longest alias + parent-topic agreement with the planner's topic verdict. Pro: zero LLM cost; deterministic; testable. Con: misses paraphrased queries.

**H2:** **LLM-based**. An LLM call per query maps query → subtopic_key. Pro: higher recall. Con: +1 LLM call per chat turn (hundreds of $ per month at scale).

**Recommendation: H1.** Start with lexical; v3 can add LLM when the regex recall gap is measurable. Needs user sign-off.

### Decision I — Backfill scope?
**RATIFIED 2026-04-21: I1 (full corpus, active generation only).**


**I1 (recommended):** **Full corpus, active generation only**. Re-classify every doc in the CURRENT `is_active=true` `corpus_generations` row. Past generations stay NULL-subtopic (they're frozen history).

**I2:** **All generations**. Pro: retrieval from any frozen generation is subtopic-aware. Con: 3-5× the LLM spend.

**Recommendation: I1.** Needs user sign-off.

### Decision J — Scope boundary: where does this plan stop?
**RATIFIED 2026-04-21: J1 (stop at ≥95% coverage, no per-chunk / LLM intent / A-B harness).**


**J1 (recommended):** This plan STOPS after `documents.subtema` is populated on ≥95% of active-generation docs AND retrieval's boost logic is green on the E2E runbook. Taxonomy refinement (Phase 4+ of subtopic_generationv1's follow-on UI curation) is a separate future plan.

**J2:** This plan also ships per-chunk re-classification (Decision E2) + LLM-based intent (Decision H2) + retriever A/B harness.

**Recommendation: J1.** Needs user sign-off.

---

## 5. Phased Implementation

> Each phase has a Definition of Done + a Verification Command run before marking `PASSED_TESTS`. Tests are required at every phase.

### 5.0 Cross-cutting Invariants

**Invariant I1 — Alias breadth preserved.** Any code path that reads the taxonomy uses `key + label + aliases[]` together. Never narrow to `key + label`. (Honors auto-memory `feedback_subtopic_aliases_breadth.md`.)

**Invariant I2 — Falkor outages propagate.** Any new Falkor-dependent code path must raise on connection failure, never silently degrade to artifacts. (Honors `CLAUDE.md` hard rule.)

**Invariant I3 — Trace every link.** Every new code path emits `emit_event`. Event namespace: `subtopic.ingest.*` (classifier + sink), `subtopic.graph.*` (bridge), `subtopic.retrieval.*` (planner + retriever), `subtopic.backfill.*`.

**Invariant I4 — Subtopic never overrides topic.** If the classifier's topic verdict is `iva` but PASO 4 says `subtopic=nomina_electronica`, the subtopic is dropped (NULL + `requires_subtopic_review=true`). Logic in `ingestion_classifier.py`.

**Invariant I5 — Null-safety everywhere.** Every SELECT + Cypher traversal handles `subtema IS NULL`. The boost logic does not penalize null-subtopic chunks.

### Phase template (each phase below follows this shape)

```
Goal           — one sentence
Files create   — exact paths
Files modify   — exact paths + brief edit summary
Tests add      — file path + case count + Verification Command
DoD            — checklist of "done" concretely
Trace events   — emitted event_type strings
State Notes    — live-updated; default `(not started)`
Resume marker  — within-phase last-known-good checkpoint
```

---

### Phase 0 — Decisions ratified
- **Goal:** all 10 §4 decisions marked with explicit user choice.
- **Verification:** plan-doc diff shows `RATIFIED 2026-MM-DD: <choice>` against each decision A–J.
- **State Notes:** (not started — awaiting user approval)
- **Resume marker:** —

---

### Phase 1 — Taxonomy loader + validation
- **Goal:** one module everyone else imports; returns the taxonomy in memory-efficient shape with alias-index for fast lookups.
- **Files create:**
  - `src/lia_graph/subtopic_taxonomy_loader.py` (~180 LOC). Public API:
    - `load_taxonomy(path: Path | None = None) -> SubtopicTaxonomy` — reads `config/subtopic_taxonomy.json` (or `path` override). Returns a frozen dataclass with `version`, `subtopics_by_parent`, `lookup_by_key`, `lookup_by_alias`.
    - `SubtopicTaxonomy.get_candidates_for(parent_topic: str) -> list[SubtopicEntry]` — returns the candidates to feed into PASO 4.
    - `SubtopicTaxonomy.resolve_alias(alias: str) -> SubtopicEntry | None` — used by planner.
    - `validate_taxonomy(data: dict) -> list[ValidationError]` — structural checks for load + CI.
  - `tests/test_subtopic_taxonomy_loader.py` (~8 cases).
- **Files modify:** none.
- **Tests add:**
  - (a) load real `config/subtopic_taxonomy.json` → ≥86 entries, ≥37 parents.
  - (b) `get_candidates_for("laboral")` returns ≥1 entry.
  - (c) `resolve_alias("acoso_laboral_y_sus_interpretaciones")` resolves to the right parent (validates alias breadth — Invariant I1).
  - (d) malformed JSON → raises with line number.
  - (e) missing `version` field → `validate_taxonomy` returns an error.
  - (f) duplicate keys within a parent → `validate_taxonomy` returns an error.
  - (g) alias collision across different parents → `validate_taxonomy` emits warning (not error) + resolution prefers first occurrence.
  - (h) freeze test — returned dataclass is immutable (`dataclass(frozen=True)`).
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_subtopic_taxonomy_loader.py -v` → 8/8 green.
- **DoD:** taxonomy-file identity tests green; other phases can `from lia_graph.subtopic_taxonomy_loader import load_taxonomy`.
- **Trace events:** none (pure module).
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 2 — Supabase: `sub_topic_taxonomy` table + RPC extension
- **Goal:** materialize the taxonomy in Supabase for cloud-live environments; extend `hybrid_search` to accept `filter_subtopic`.
- **Files create:**
  - `supabase/migrations/YYYYMMDDNNNNNN_sub_topic_taxonomy.sql` (~120 LOC):
    - `CREATE TABLE sub_topic_taxonomy(parent_topic_key TEXT, sub_topic_key TEXT, label TEXT, aliases TEXT[], evidence_count INT, curated_at TIMESTAMPTZ, curator TEXT, version TEXT, PRIMARY KEY (parent_topic_key, sub_topic_key))`.
    - `CREATE INDEX ix_sub_topic_taxonomy_parent ON sub_topic_taxonomy (parent_topic_key)`.
    - `CREATE INDEX ix_sub_topic_taxonomy_aliases ON sub_topic_taxonomy USING GIN (aliases)`.
    - `CREATE OR REPLACE FUNCTION hybrid_search(...)` — same signature as today PLUS a new `filter_subtopic TEXT DEFAULT NULL` param. Body adds a boost: `rrf_score * (1.5 ^ (1 if subtema = filter_subtopic else 0))`.
  - `scripts/sync_subtopic_taxonomy_to_supabase.py` (~140 LOC) — reads `config/subtopic_taxonomy.json`, upserts rows to `sub_topic_taxonomy`. CLI flags `--target {wip|production}`, `--dry-run`.
  - `tests/test_subtopic_taxonomy_sync.py` (~5 cases).
- **Files modify:**
  - `scripts/promote_subtopic_decisions.py` — add `--sync-supabase {wip|production}` flag that invokes the sync script after writing the JSON.
- **Tests add:**
  - (a) `sync_subtopic_taxonomy_to_supabase.py --dry-run` against a stub taxonomy → echoes 86 rows without writing.
  - (b) `sync_subtopic_taxonomy_to_supabase.py --target wip` (mocked Supabase client) → upserts 86 rows.
  - (c) idempotency — running twice produces identical rows.
  - (d) updating the version string re-upserts aliases.
  - (e) malformed taxonomy → non-zero exit.
  - **Verification:** `pytest tests/test_subtopic_taxonomy_sync.py -v` → 5/5 green.
- **DoD:** migration applies cleanly on local docker Supabase (`supabase db reset` + new migration lands). Remote cloud Supabase apply is Phase 9 E2E territory — do NOT apply in this phase.
- **Trace events:** `subtopic.ingest.taxonomy_synced` on successful sync.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 3 — Classifier PASO 4 extension
- **Goal:** extend `classify_ingestion_document` N2 prompt with PASO 4 that resolves subtopic against taxonomy.
- **Files create:** none.
- **Files modify:**
  - `src/lia_graph/ingestion_classifier.py`:
    - Extend `_AUTOGENERAR_PROMPT_TEMPLATE` with PASO 4 block (subtopic resolution).
    - Add `_N2Result.subtopic_resolved_to_existing`, `subtopic_synonym_confidence`, `subtopic_is_new`, `subtopic_suggested_key`, `subtopic_label`.
    - Add `_fuse_subtopic_confidence(n1, n2)` mirroring `_fuse_autogenerar_confidence`.
    - Extend `AutogenerarResult` with `subtopic_key`, `subtopic_label`, `subtopic_confidence`, `requires_subtopic_review`.
    - In `classify_ingestion_document`, after PASO 3, call the taxonomy loader to get candidates for the resolved topic; pass into PASO 4.
    - Honor Invariant I4: if subtopic is resolved against a parent ≠ the final `detected_topic`, drop subtopic (NULL + require_review=true).
  - `tests/test_ingest_classifier.py` — add 6 PASO 4 cases.
- **Tests add:** 6 cases covering:
  - (a) PASO 4 resolves against an existing subtopic → `subtopic_key` set, `requires_subtopic_review=false`.
  - (b) PASO 4 declares new subtopic → `subtopic_is_new=true`, `subtopic_key=_slugify(subtopic_label)`.
  - (c) PASO 4 low confidence (0.50-0.79) → `subtopic_key=NULL`, `requires_subtopic_review=true`.
  - (d) PASO 4 resolves to a subtopic under a DIFFERENT parent than topic verdict → drop + review (Invariant I4).
  - (e) `skip_llm=True` → PASO 4 not called, subtopic fields default NULL.
  - (f) Malformed PASO 4 JSON → subtopic NULL, topic verdict unaffected.
  - **Verification:** `pytest tests/test_ingest_classifier.py -v` → 73/73 green (67 existing + 6 new).
- **DoD:** prompt template includes PASO 4; all N2-firing tests produce the new fields.
- **Trace events:** `subtopic.ingest.classified` on every classification (payload: `doc_id_hash`, `topic`, `subtopic_key`, `subtopic_confidence`, `requires_review`).
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 4 — Sink wire-up
- **Goal:** classifier's `subtopic_key` flows into `documents.subtema` + propagates to `document_chunks.subtema`.
- **Files create:** none.
- **Files modify:**
  - `src/lia_graph/ingest.py` (or wherever the classifier result populates the document dict before sinking) — add `document["subtopic_key"] = result.subtopic_key` after classification.
  - `src/lia_graph/ingestion/supabase_sink.py`:
    - `write_documents` already reads `document.get("subtopic_key")` → `subtema`. Verify + add `requires_subtopic_review` → new column or JSON sidecar in `documents.concept_tags`. (See Decision: confirm where review flag persists — most natural: add `documents.requires_subtopic_review BOOL` via Phase 2 migration.)
    - `write_chunks` — inherit `subtema` from `doc_id_by_source_path` map's parent document (Decision E1). Touch the ParsedArticle → chunk row mapping.
  - `src/lia_graph/ui_ingest_run_controllers.py` — intake sidecar JSONL row shape gains `subtopic_key` + `subtopic_confidence` + `requires_subtopic_review` fields.
  - `tests/test_supabase_sink_subtopic.py` (new, ~6 cases).
- **Tests add:**
  - (a) `write_documents` with `subtopic_key="nomina_electronica"` → row.subtema == "nomina_electronica".
  - (b) `write_documents` with `subtopic_key=None` → row.subtema is NULL.
  - (c) `write_chunks` — all chunks for doc_id X inherit the doc's subtema.
  - (d) chunks from docs with NULL subtema → chunk.subtema NULL too.
  - (e) `requires_subtopic_review=true` persists (either column or tags).
  - (f) sidecar JSONL after intake includes all three new fields.
  - **Verification:** `pytest tests/test_supabase_sink_subtopic.py tests/test_ingest_intake_controller.py -v` → green.
- **DoD:** `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=wip --limit 5` on local Supabase produces 5 docs where `documents.subtema IS NOT NULL` for at least the laboral/iva ones (assuming Phase 3 classifier produces those). Spot-check via `SELECT doc_id, topic, subtema FROM documents WHERE sync_generation=<generation_id> LIMIT 20`.
- **Trace events:** `subtopic.ingest.sunk` at end of sink write (payload: `generation_id`, `docs_with_subtopic`, `docs_requiring_review`).
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 5 — FalkorDB schema + bridge
- **Goal:** graph carries `SubTopic` node + `HAS_SUBTOPIC` edges.
- **Files create:**
  - `tests/test_graph_schema_subtopic.py` (~5 cases).
  - `tests/test_suin_bridge_subtopic.py` (~4 cases).
- **Files modify:**
  - `src/lia_graph/graph/schema.py`:
    - Add `NodeKind.SUBTOPIC = "SubTopicNode"`.
    - Add `EdgeKind.HAS_SUBTOPIC = "HAS_SUBTOPIC"`.
    - Extend `default_graph_schema()` with the new node + edge definitions. Source kinds for HAS_SUBTOPIC: `(NodeKind.ARTICLE, NodeKind.REFORM, NodeKind.CONCEPT)` (i.e. any doc-origin node) + Topic-as-concept. Target kinds: `(NodeKind.SUBTOPIC,)`.
    - `validate_edge_record` — HAS_SUBTOPIC validates source in valid set.
  - `src/lia_graph/graph/validators.py` — extend validation rules if needed.
  - `src/lia_graph/ingestion/suin/bridge.py` (or wherever Falkor node/edge emission happens): for every document written, emit a `SubTopic` node (if not yet present) + a `HAS_SUBTOPIC` edge from the doc's Article/Concept node to the SubTopic node. Idempotent via MERGE-style Cypher.
- **Tests add:**
  - Schema (5 cases):
    - (a) `NodeKind.SUBTOPIC` exists.
    - (b) `EdgeKind.HAS_SUBTOPIC` exists.
    - (c) `default_graph_schema()` includes both.
    - (d) `validate_edge_record` accepts Article → SubTopic.
    - (e) `validate_edge_record` rejects SubTopic → Article.
  - Bridge (4 cases):
    - (a) document with subtopic_key → emits SubTopic node + HAS_SUBTOPIC edge.
    - (b) document without subtopic_key → no emission.
    - (c) 5 docs sharing same subtopic → 1 node + 5 edges.
    - (d) bridge run twice → no duplicate nodes/edges (idempotent).
  - **Verification:** `pytest tests/test_graph_schema_subtopic.py tests/test_suin_bridge_subtopic.py -v` → 9/9 green.
- **DoD:** local docker FalkorDB shows SubTopic nodes after an ingestion run: `MATCH (s:SubTopicNode) RETURN count(s)` > 0.
- **Trace events:** `subtopic.graph.node_emitted`, `subtopic.graph.edge_emitted`, `subtopic.graph.done`.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 6 — Planner intent + retriever boost
- **Goal:** detect subtopic intent in user queries; pass to both retrievers; boost matching chunks.
- **Files create:**
  - `tests/test_planner_subtopic_intent.py` (~8 cases).
  - `tests/test_retriever_supabase_subtopic_boost.py` (~6 cases).
  - `tests/test_retriever_falkor_subtopic.py` (~5 cases).
- **Files modify:**
  - `src/lia_graph/pipeline_d/planner_query_modes.py` — add `_detect_sub_topic_intent(query_text: str, detected_topic: str) -> str | None`. Implementation (Decision H1 — regex/alias match):
    - Load taxonomy once (module-level cache).
    - Normalize query (lowercase, strip accents).
    - For each subtopic under `detected_topic`, check if `key`, `label` (slugified), or any `aliases[]` appears as substring or word in the query.
    - Return the first match (ties broken by longest-alias-first, then key-ascending).
  - `src/lia_graph/pipeline_d/planner.py` — extend `GraphRetrievalPlan` with `sub_topic_intent: str | None = None`. Populate via `_detect_sub_topic_intent`.
  - `src/lia_graph/pipeline_d/retriever_supabase.py` — `_hybrid_search` payload adds `"filter_subtopic": plan.sub_topic_intent`. Post-rerank, apply `LIA_SUBTOPIC_BOOST_FACTOR` (default 1.5) to matching chunks (Decision G1+G3).
  - `src/lia_graph/pipeline_d/retriever_falkor.py` — when `plan.sub_topic_intent` is set, preferentially walk `Document -[HAS_SUBTOPIC]-> SubTopic{key: intent}` paths; fallback to full topic traversal when no matches.
  - Diagnostics: extend `PipelineCResponse.diagnostics` with `retrieval_sub_topic_intent` so the orchestration guide's per-turn diagnostics table still captures it.
- **Tests add:**
  - Planner (8 cases):
    - (a) query `"cómo liquido parafiscales ICBF"` + topic=laboral → intent=`aporte_parafiscales_icbf`.
    - (b) query `"pago de nómina electrónica"` + topic=laboral → intent=`nomina_electronica` (via alias match).
    - (c) query mentioning alias only (no key/label) → resolves via alias breadth (Invariant I1).
    - (d) query with no subtopic keywords → intent=None.
    - (e) query with alias belonging to DIFFERENT parent → not matched when topic verdict narrows.
    - (f) longest-alias tie-breaker.
    - (g) parent with 0 subtopics → intent=None.
    - (h) empty query → intent=None.
  - Retriever supabase (6 cases):
    - (a) plan with intent → RPC payload includes `filter_subtopic`.
    - (b) plan without intent → `filter_subtopic=NULL`.
    - (c) chunk with matching subtema → `rrf_score * 1.5`.
    - (d) chunk with NULL subtema + intent set → score unchanged (Invariant I5).
    - (e) `LIA_SUBTOPIC_BOOST_FACTOR=2.0` env → boost uses 2.0.
    - (f) diagnostics carry `retrieval_sub_topic_intent`.
  - Retriever falkor (5 cases):
    - (a) plan with intent → Cypher filters on SubTopic{key: intent}.
    - (b) plan without intent → full traversal unchanged.
    - (c) no matching SubTopic in graph → fallback to full traversal.
    - (d) cloud outage propagates (Invariant I2).
    - (e) traversal depth limits still honored.
  - **Verification:** `pytest tests/test_planner_subtopic_intent.py tests/test_retriever_supabase_subtopic_boost.py tests/test_retriever_falkor_subtopic.py -v` → 19/19 green.
- **DoD:** a chat turn with `"cómo liquido parafiscales ICBF"` produces `response.diagnostics.retrieval_sub_topic_intent == "aporte_parafiscales_icbf"` and the top chunk is one tagged with that subtema.
- **Trace events:** `subtopic.retrieval.intent_detected`, `subtopic.retrieval.boost_applied`, `subtopic.retrieval.fallback_to_topic`.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 7 — UI surfacing
- **Goal:** admin UI shows subtopic per doc during intake + subtopic coverage per corpus generation.
- **Files create:**
  - `frontend/src/shared/ui/atoms/subtopicChip.ts` (~60 LOC) — thin wrapper over existing `chip.ts` atom but with subtopic-specific tone mapping.
  - `frontend/tests/subtopicChip.test.ts` (~4 cases).
- **Files modify:**
  - `frontend/src/shared/ui/molecules/intakeFileRow.ts` — render `subtopicChip` under the existing topic chip when `subtopic_key` present; `(needs review)` badge when `requires_subtopic_review=true`.
  - `frontend/src/shared/ui/molecules/generationRow.ts` — new micro-metric: `% with subtopic`.
  - `frontend/src/features/ingest/ingestController.ts` — surface `subtopic_key` + `subtopic_confidence` + `requires_subtopic_review` in the intake response view-model.
  - Backend: `src/lia_graph/ui_ingest_run_controllers.py` — `GET /api/ingest/generations/{id}` response gains `subtopic_coverage` aggregate.
  - `frontend/tests/ingestPhase5Organisms.test.ts` — update existing cases to assert the subtopic chip renders.
- **Tests add:**
  - (a) `subtopicChip` renders key + label.
  - (b) `(needs review)` badge appears when flagged.
  - (c) `intakeFileRow` without subtopic → no chip.
  - (d) atomic-discipline guard stays green.
  - **Verification:** `cd frontend && npx vitest run tests/subtopicChip.test.ts tests/atomicDiscipline.test.ts tests/ingestPhase5Organisms.test.ts` → all green.
- **DoD:** live drag-to-ingest in `npm run dev` shows a subtopic chip on the preview row for a laboral doc.
- **Trace events:** none (frontend; backend already emits via Phase 4).
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 8 — Backfill
- **Goal:** re-classify every doc in the active `corpus_generations` row so historical docs get `subtema` populated.
- **Files create:**
  - `scripts/backfill_subtopic.py` (~260 LOC). CLI flags: `--dry-run | --commit`, `--limit N`, `--only-topic SLUG`, `--rate-limit-rpm 60`, `--generation-id ID` (defaults to active), `--resume-from CHECKPOINT`. Walks documents by generation_id, loads markdown from storage, reruns classifier (topic + subtopic), updates `documents.subtema` + `document_chunks.subtema` + emits FalkorDB HAS_SUBTOPIC edges.
  - `tests/test_backfill_subtopic.py` (~6 cases).
- **Files modify:**
  - `Makefile` — add `phase2-backfill-subtopic` target (mirrors `phase2-regrandfather-corpus` style).
- **Tests add:**
  - (a) 3-doc fixture → 3 rows updated with subtema.
  - (b) dry-run → no DB writes.
  - (c) resume-from → already-subtopic'd docs skipped (`WHERE subtema IS NULL` filter).
  - (d) per-doc failure → logged + continues.
  - (e) rate-limit honored.
  - (f) trace events fire.
  - **Verification:** `pytest tests/test_backfill_subtopic.py -v` → 6/6 green.
- **DoD:** `make phase2-backfill-subtopic DRY_RUN=1 LIMIT=10` shows 10 candidates. Full backfill is a STAKEHOLDER-APPROVED step (stop per §0.5 item 3) — runbook in Phase 9 covers the real execution.
- **Trace events:** `subtopic.backfill.start`, `subtopic.backfill.doc.processed`, `subtopic.backfill.doc.failed`, `subtopic.backfill.done`.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 9 — E2E runbook + evidence
- **Goal:** stakeholder-facing runbook that drives the full flow end-to-end against real infrastructure.
- **Files create:**
  - `tests/manual/ingestfixv2_e2e_runbook.md` — step-by-step: pre-flight, classifier smoke probe (3 docs), sync taxonomy to Supabase (wip → verify → production), run backfill on wip, verify retrieval boost via 5 canned chat queries, cut to production, commit.
  - `tests/manual/ingestfixv2_evidence/<run-ts>/` — evidence bundle template.
- **Files modify:** none.
- **Tests add:** the runbook IS the test; each run produces an evidence bundle.
- **DoD:** (1) classifier probe green on 3 docs; (2) `sub_topic_taxonomy` table synced to wip Supabase; (3) backfill completes with `docs_with_subtopic >= 90%` coverage; (4) retrieval boost confirmed via at least 3 chat queries (examples: "parafiscales ICBF", "factura como título valor", "presunción de costos independientes UGPP"); (5) `logs/events.jsonl` carries a complete subtopic.* trace; (6) stakeholder signs off; (7) production cut.
- **Trace events:** consumed.
- **State Notes:** (not started)
- **Resume marker:** —

---

### Phase 10 — Close-out
- **Goal:** orchestration change log + relocate this doc.
- **Files modify:**
  - `docs/orchestration/orchestration.md` — new change-log entry `v2026-MM-DD-stv2` documenting the pipeline extension + the new RPC param + the SubTopic FalkorDB nodes/edges + any env var (`LIA_SUBTOPIC_BOOST_FACTOR`).
  - `CLAUDE.md` — minor addition: the subtopic intent propagation in diagnostics.
  - THIS doc — dashboard to COMPLETE; move to `docs/done/ingestfixv2.md`.
- **DoD:** orchestration.md entry landed; plan relocated; CLAUDE.md updated.
- **State Notes:** (not started)
- **Resume marker:** —

---

## 6. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| PASO 4 regresses PASO 1-3 quality | Med | High | Phase 3 tests assert PASO 1-3 outputs unchanged on a golden set of 20 docs. Rollback via `git revert` per Decision D1 caveat. |
| Classifier emits subtopic key not in taxonomy | Med | Med | `subtopic_is_new=true` path already handles; no runtime write to DB unless synonym_confidence ≥ 0.80. |
| Backfill updates fail partway → mixed-state corpus | Med | Med | Append-only JSONL checkpoint + `--resume-from`; query `WHERE subtema IS NULL AND sync_generation = <active>` to resume. |
| Retriever boost surfaces wrong chunks when intent detection is wrong | Med | Med | Boost factor configurable (`LIA_SUBTOPIC_BOOST_FACTOR`); easy rollback to 1.0. |
| FalkorDB writes fail silently | Low | High | Invariant I2 + existing Falkor error propagation. |
| Taxonomy version drift between JSON file and Supabase table | Med | Low | Sync script idempotent; promotion pipeline invokes sync. E2E runbook verifies versions match. |
| LLM rate limits during backfill | High | Med | `--rate-limit-rpm` flag; resume-from ensures cheap retry. |
| Subtopic chip clutters intake preview on high-density views | Low | Low | Atomic-discipline guard + tokens-only CSS; can hide via CSS media query if feedback demands. |

---

## 7. Out of Scope

- LLM-based subtopic intent detection in planner (Decision H2) — a future plan.
- Per-chunk subtopic classification (Decision E2) — future plan.
- Taxonomy schema v2 (new fields on taxonomy entries) — future plan.
- Retriever A/B harness with automated quality scoring.
- Multi-curator subtopic-registry promotion workflow.
- Retroactive backfill on frozen historical `corpus_generations`.

---

## 8. Open Questions for User (Phase 0 sign-off)

1. **Decision A (PASO 4 call):** A1 (same call) or A2 (second sequential call)?
2. **Decision B (taxonomy source):** B1 (file-first, DB is projection) or B2 (DB-first)?
3. **Decision C (confidence fusion):** C1 (mirror topic fusion) or C2 (simple threshold)?
4. **Decision D (rollout):** D1 (always on) or D2 (env-flagged)?
5. **Decision E (chunk-level):** E1 (inherited) or E2 (per-chunk)?
6. **Decision F (graph edges):** F1 (document-only) or F2 (also chunk-level)?
7. **Decision G (boost factor):** G1 (1.5× default) or G2 (2.0×) or G3 (env override)?
8. **Decision H (intent detection):** H1 (regex/alias) or H2 (LLM)?
9. **Decision I (backfill scope):** I1 (active generation) or I2 (all generations)?
10. **Decision J (plan scope):** J1 (stop at ≥95% coverage) or J2 (go further)?
11. **Corpus scope for Phase 8 backfill:** full 1313-doc active generation, or restrict pilot to `--only-topic laboral` first?
12. **Branching:** stay on `feat/suin-ingestion` or cut a fresh `feat/ingestfix-v2` off main?

---

## 9. Change Log
| Version | Date | Note |
|---|---|---|
| `v1-stub` | 2026-04-20 | Initial stub authored alongside ingestfixv1 Decision G2. |
| `v2-plan` | 2026-04-21 | Full plan rewrite: 11 phases, cold-start briefing, state dashboard, 10 ratifiable decisions. Consumes `config/subtopic_taxonomy.json` v2026-04-21-v1. |

---

## 10. References

- `docs/done/ingestfixv1.md` — AUTOGENERAR cascade + classifier API shipped.
- `docs/next/subtopic_generationv1.md` (will move to `docs/done/` post v1 close-out) — taxonomy producer.
- `docs/next/subtopic_generationv1-contracts.md` — canonical schemas.
- `docs/orchestration/orchestration.md` Lane 0 + retrieval adapters section.
- `CLAUDE.md` — Lia_Graph hard rules (no silent Falkor fallback, pipeline_d granularity).
- `src/lia_graph/ingestion_classifier.py:AutogenerarResult` — the shape Phase 3 extends.
- `src/lia_graph/ingestion/supabase_sink.py:write_documents` — already reads `subtopic_key`, Phase 4 wires the producer.
- `src/lia_graph/graph/schema.py:default_graph_schema` — Phase 5 extends.
- `src/lia_graph/pipeline_d/planner_query_modes.py` — Phase 6 extends.
- `src/lia_graph/pipeline_d/retriever_supabase.py:_hybrid_search` — Phase 6 extends.
- `supabase/migrations/20260417000000_baseline.sql` — the baseline with existing `subtema` columns.
- `config/subtopic_taxonomy.json` — the taxonomy this plan consumes.
- Auto-memory `feedback_subtopic_aliases_breadth.md` — alias breadth policy.

---

## 11. Resume Protocol

If a session is interrupted, the next session picks up cold by reading this doc. **Do NOT restart any phase from scratch.**

### 11.1 Cold-start checklist
1. Read §0.5 Execution Mode. Confirm autonomous rules still in force.
2. Read §2 State Dashboard. Identify `Current phase` + `Last completed phase`.
3. Open the active phase in §5. Read its `State Notes` top to bottom.
4. Read the `Resume marker` if present.
5. Run the phase's Verification Command. Green → flip status in §2. Red → the failure tells you where to resume.
6. If `State Notes` say `blocked: <reason>`, address the blocker first.

### 11.2 Mid-phase checkpoint conventions
- `started 2026-MM-DDTHH:MMZ` — phase began.
- `checkpoint: <task> done; resuming at <next_task>` — after each meaningful milestone.
- `commit: <sha> — <summary>` — when a commit lands.
- `blocked: <reason>` — when stopping.
- `completed 2026-MM-DDTHH:MMZ; commit <sha>` — phase exit.

### 11.3 Fresh-resume drill
1. `git status` to see uncommitted files.
2. `git log --oneline -20` to see what the previous session committed (expect `feat(ingestfix-v2-phase-N): ...`).
3. Match commit messages to phase numbers.
4. Diff between last commit and `git status` shows in-progress work.
5. Apply the phase's Verification Command — green → DONE; red → finish the work the diff suggests.

### 11.4 Recovery from corrupt state
If the working tree is unrecognizable:
1. Stop. Do NOT take destructive action without user confirmation.
2. Mark active phase BLOCKED with the failure mode.
3. Surface to the user with recovery options ranked by safety.

---

## 12. Autonomous Decision Authority

### 12.1 The assistant MAY decide without asking
- Internal naming (function names, helper module names, JSON/SQL column names within documented contracts, CSS class names, test fixture names). Document the choice in `State Notes`.
- Implementation patterns when equivalent (iteration vs comprehension; explicit loop vs `defaultdict`).
- In-phase reorganization (splitting a helper into a sibling module if LOC creeps past ~1000).
- Test count adjustments (the DoD is "every behavior tested", not "exactly N cases").
- Trace event payload field additions. Document in §13.
- Minor migration naming / comments.

### 12.2 The assistant MUST ask before
- Contradicting any §4 ratified decision.
- Applying a Supabase migration against cloud staging or cloud production (local docker fine).
- Kicking off the full-corpus backfill (Phase 8 production run).
- Force-pushing or history-rewriting operations.
- Committing a taxonomy bump (that's the job of `subtopic_generationv1`'s UI, not this plan).
- Changing the `LIA_SUBTOPIC_BOOST_FACTOR` default from 1.5 without re-ratifying Decision G.

### 12.3 Fork-in-the-road handling
When an in-flight discovery presents two equally valid paths with downstream consequences:
1. Pick the path that maximally preserves §4 ratified decisions.
2. Document the choice + rejected alternative in `State Notes` with a `decision:` line.
3. Revert is one-line: undo the file changes from that checkpoint forward.

---

## 13. Subtopic Ingest / Retrieval Trace Schema (filled in Phase 7 audit or earlier)

Until Phase 7 audits actual emissions, the table below is the TARGET schema. Phase 10 close-out verifies reality matches.

| event_type | emitted_by | when | payload fields |
|---|---|---|---|
| `subtopic.ingest.taxonomy_synced` | `scripts/sync_subtopic_taxonomy_to_supabase` | after successful upsert | `target`, `version`, `row_count` |
| `subtopic.ingest.classified` | `src/lia_graph/ingestion_classifier` | per-doc classify | `doc_id_hash`, `topic`, `subtopic_key`, `subtopic_confidence`, `requires_subtopic_review` |
| `subtopic.ingest.sunk` | `src/lia_graph/ingestion/supabase_sink` | end of sink write | `generation_id`, `docs_with_subtopic`, `docs_requiring_review` |
| `subtopic.graph.node_emitted` | `ingestion/suin/bridge` | per-SubTopic-node MERGE | `subtopic_key`, `parent_topic`, `was_new` |
| `subtopic.graph.edge_emitted` | same | per-HAS_SUBTOPIC edge | `source_kind`, `source_key`, `subtopic_key` |
| `subtopic.graph.done` | same | bridge run end | `nodes_emitted`, `edges_emitted`, `elapsed_s` |
| `subtopic.retrieval.intent_detected` | `pipeline_d/planner_query_modes` | per-query planner | `query_hash`, `topic`, `sub_topic_intent`, `match_via` (key/label/alias) |
| `subtopic.retrieval.boost_applied` | `pipeline_d/retriever_supabase` | per-chunk post-rank | `chunk_id`, `sub_topic_intent`, `boost_factor`, `original_rrf`, `boosted_rrf` |
| `subtopic.retrieval.fallback_to_topic` | `pipeline_d/retriever_falkor` | when SubTopic traversal empty | `sub_topic_intent`, `parent_topic`, `fallback_node_count` |
| `subtopic.backfill.start` | `scripts/backfill_subtopic` | pass start | `generation_id`, `dry_run`, `limit`, `only_topic` |
| `subtopic.backfill.doc.processed` | same | per-doc success | `doc_id`, `topic`, `subtopic_key`, `subtopic_confidence`, `was_null_before` |
| `subtopic.backfill.doc.failed` | same | per-doc error | `doc_id`, `error`, `phase` |
| `subtopic.backfill.done` | same | pass end | `docs_processed`, `docs_failed`, `elapsed_s`, `output_report` |

---

## 14. Minimum Viable Success

This plan is **successful** when:

1. `classify_ingestion_document` returns a `subtopic_key` for ≥90% of docs in the active corpus generation (measurable via `SELECT COUNT(*) FILTER (WHERE subtema IS NOT NULL) / COUNT(*) FROM documents WHERE sync_generation=<active>`).
2. FalkorDB contains `SubTopic` nodes and `HAS_SUBTOPIC` edges linking documents to them (measurable via `MATCH (s:SubTopicNode) RETURN count(s)` > 0 AND `MATCH ()-[e:HAS_SUBTOPIC]->() RETURN count(e)` > 0).
3. A chat query like `"cómo liquido parafiscales ICBF"` produces `response.diagnostics.retrieval_sub_topic_intent = "aporte_parafiscales_icbf"` AND the top chunk is one tagged with that subtema.
4. `docs/orchestration/orchestration.md` has a `v2026-MM-DD-stv2` change-log entry.
5. Phase 9 E2E runbook completed with evidence bundle; stakeholder signed off.
6. The plan doc is relocated to `docs/done/ingestfixv2.md` with the final dashboard showing COMPLETE.

Anything beyond that (LLM-based intent, per-chunk subtopics, chat-facing UI for subtopic filters) is explicitly the next plan's problem.

---

*End of plan. Phase 1 does not begin until the user marks `Plan status = APPROVED` in §2 and ratifies each decision A–J in §4.*
