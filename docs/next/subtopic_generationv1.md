# Subtopic Generation v1 — Corpus-Wide Label Collection, Clustering, and Curation

**Last edited:** 2026-04-21 (refresh pass — reconciled with `v2026-04-21-stv2c` working tree; ratifications + phase bodies unchanged, State Dashboard + cold-start pointers + §0.12 design-skill pattern added)
**Execution owner:** shipped by autonomous Claude session on 2026-04-21; close-out (relocation to `docs/done/`) pending the final commit described in Phase 9.
**Goal:** run a one-time corpus-wide AUTOGENERAR pass that records the free-form LLM-generated label (`autogenerar_label`) for every document; mine those labels into proposed subtopic clusters per parent topic; present them for human curation; promote the curated result into `config/subtopic_taxonomy.json`. The output is the seed list that unblocks `docs/next/ingestfixv2.md` (sub-topic tagging at intake, Decision G2).

> This document is both a **plan** AND a **work ledger**. Every phase has a `State Notes` block updated in-place DURING execution. If a session is interrupted, the state of this file is the resumption pointer — see §11 Resume Protocol.

> **Cold-start agent:** read §0 first, then §0.5, then §2, then jump to whichever phase is active in §5. Do not skim — every line in §0 and §0.5 is load-bearing. If anything in §0 is wrong (tool missing, branch mismatch, etc.), STOP and surface to the user before proceeding.

---

## 0. Cold-Start Briefing (READ FIRST IF YOU HAVE ZERO PRIOR CONTEXT)

This section is for an LLM agent that opens this doc with no conversation history. After reading §0 + §0.5 + §2 + the active phase entry in §5, you should have everything you need to execute autonomously.

### 0.1 Project orientation in three sentences
**Lia_Graph** is a graph-RAG accounting assistant for Colombian senior accountants serving SMB clients. It is a derivative of `Lia_contadores` (https://github.com/avas888/Lia_contadores) and lives at `https://github.com/avas888/LIA_Graph`. It serves answers in Spanish-CO covering tax (IVA, declaración de renta, ICA, retención, …) AND labor / payroll / seguridad social (CST, Ley 100, parafiscales, UGPP, MinTrabajo) — labor is first-class, not tax-adjacent.

### 0.2 Repo location + branch
- **Working directory:** `/Users/ava-sensas/Developer/Lia_Graph`
- **Branch this plan executes against:** `feat/suin-ingestion` (inherited from `ingestfixv1`)
- **Main branch (used for PRs):** `main`
- **Last shipped change pre-plan:** `v2026-04-20-ui15` (see `docs/guide/orchestration.md` change log) — the drag-to-ingest + AUTOGENERAR + 6-stage progress surface. AUTOGENERAR's `autogenerar_label` was captured only when N1 combined confidence < 0.95 triggered the N2 LLM. This plan made the label-emission pass ALWAYS-ON (for the one-shot collection run) and built the downstream mining + curation loop.
- **Current tree context (set by refresh pass):** `feat/suin-ingestion` is now at commit `4b7a277` with env matrix `v2026-04-21-stv2c`. The consumer plan `ingestfixv2` has already shipped and landed in `docs/done/ingestfixv2-maximalist.md` — so the hand-off this plan was written to deliver is already in production use. A cold-start agent resuming today should expect to find Phases 1-9 essentially complete and only the physical relocation of this doc + a final close-out commit outstanding (see §2).

### 0.3 Source-of-truth document map (READ THESE BEFORE WRITING CODE)
Hierarchy of authority — when documents disagree, the higher one wins:

| Doc | Role |
|---|---|
| `CLAUDE.md` (repo root) | Quickstart for Claude-family agents. Hard rules: don't touch Lia_contadores cloud resources; pipeline_d organization is deliberate; Falkor adapter must propagate outages, not silently fall back to artifacts; granular edits over monolithic rewrites. |
| `AGENTS.md` (repo root) | Repo-level operating guide. If `CLAUDE.md` is silent on something, `AGENTS.md` is canonical. |
| `docs/guide/orchestration.md` | THE end-to-end runtime + information-architecture map. Env matrix version is currently `v2026-04-21-stv2c` (was `v2026-04-18` when this plan was authored — the bumps at stv1, stv2, stv2b, stv2c all happened after approval). Lane 0 (build-time ingestion) is the relevant lane. |
| `docs/guide/env_guide.md` | Operational counterpart to orchestration.md. Run modes + env files + test accounts + corpus refresh. |
| `docs/done/ingestfixv1.md` | Immediate predecessor plan (shipped as `v2026-04-20-ui15`). Describes AUTOGENERAR cascade, intake sidecar JSONL shape, classifier API, regrandfather script — all direct dependencies of THIS plan. |
| `docs/done/ingestfixv2.md` + `docs/done/ingestfixv2-maximalist.md` | The *consumer* of what this plan produces. Shipped after this plan — v2 writes subtopic tagging at intake (Supabase `documents.subtema` + Falkor `SubTopicNode` / `HAS_SUBTOPIC`) and the retriever prefers subtopic-anchored evidence. v2 already reads `config/subtopic_taxonomy.json` v2026-04-21-v1 in production, so the hand-off this plan promised has been honored. |
| THIS doc (`docs/next/subtopic_generationv1.md`) | The plan. State Dashboard (§2) is the live status — read it first. At the time of the 2026-04-21 refresh pass, Phases 1-9 are effectively complete; only the physical relocation to `docs/done/` + a close-out commit remain. |

### 0.4 Tooling baseline (verify in pre-flight check)
- **Python:** managed via `uv`. Always run as `PYTHONPATH=src:. uv run --group dev <command>`. Never use bare `python` for repo code.
- **Frontend:** Vite + TypeScript + vitest. Tests: `cd frontend && npx vitest run [test-pattern]`.
- **Dev server:** `npm run dev` (local docker Supabase + Falkor) at `http://127.0.0.1:8787/`.
- **LLM runtime:** `src/lia_graph/llm_runtime.py` exposes `resolve_llm_adapter()` returning an `LLMAdapter` with `.generate(prompt)` + `.generate_with_options(...)`. Configured via `config/llm_runtime.json` + env keys (Gemini default per project config).
- **Embeddings:** `src/lia_graph/embeddings.py` + `scripts/embedding_ops.py` use Gemini `text-embedding-004`. Keep the same model for label clustering so vector-space stays consistent with chunk embeddings.
- **Rate limits:** Gemini Flash is ~60 req/min on the project key. 1246 docs × 1 LLM call ≈ 21 min if perfectly serial; plan for ~35 min with retries/backoff.

### 0.5 Pre-flight check (run before Phase 1)
Single verification command — if any line fails, STOP and surface to the user:

```bash
cd /Users/ava-sensas/Developer/Lia_Graph && \
  git status && \
  git log --oneline -5 && \
  PYTHONPATH=src:. uv run --group dev pytest tests/test_ingest_classifier.py tests/test_regrandfather_dry_run.py tests/test_ingest_intake_controller.py -q && \
  ls knowledge_base/ artifacts/intake/ docs/next/subtopic_generationv1.md
```

Expected: 82/82 green (61 classifier + 7 regrandfather + 14 intake), working tree on `feat/suin-ingestion` with `ingestfixv1` landed + this plan committed/staged.

### 0.6 Auth credentials for testing
All `@lia.dev` accounts share password `Test123!` in both local docker Supabase and cloud staging. Admin credential:
- **email:** `admin@lia.dev`, **password:** `Test123!`, **role:** `platform_admin`, **tenant:** `tenant-dev`
Login: `POST http://127.0.0.1:8787/api/auth/login` with `{email, password, tenant_id: ""}`.

### 0.7 Cost estimate (run against real corpus)
- **Phase 2 collection pass:** 1246 docs × 1 Gemini Flash call (temperature=0.0, max_tokens=300, ~2048-char body) ≈ $5-15 one-time.
- **Phase 3 mining pass:** 1246 labels → 1 embedding call each (text-embedding-004) ≈ $0.50.
- **Phase 4-5 curation:** zero cloud cost (offline analysis + local UI).
- **Total one-time:** ~$6-16. Recurring cost: zero (curation is a one-shot seed-building exercise).

### 0.8 Glossary (terms used throughout)
- **autogenerar_label** — free-form 2-5-word Spanish label the LLM generates in AUTOGENERAR's N2 step BEFORE collapsing to a canonical topic. Today only populated when N1 combined confidence < 0.95. This plan makes it always-populated for the collection pass.
- **parent_topic** — the canonical topic key the document is assigned to (one of ~40 keys in `config/topic_taxonomy.json`, e.g. `laboral`, `iva`, `declaracion_renta`). Subtopics are children of a parent_topic.
- **candidate label** — one raw `autogenerar_label` observation from one document. Many candidates collapse into one proposed subtopic after clustering.
- **proposal** — a cluster of candidate labels the mining script groups together, presented to the human curator as a single decision.
- **curated subtopic** — a proposal the human accepted, named, and promoted to `config/subtopic_taxonomy.json`. The final output of this plan.
- **seed list** — the curated set of subtopics per parent topic. This plan produces the first version; `ingestfixv2.md` consumes it to constrain the LLM at intake.
- **collection pass** — the corpus-wide run that records `autogenerar_label` for every doc. One-shot, idempotent by `(doc_id, content_hash)`.

### 0.9 What this plan does NOT do
These are intentionally out of scope; they live elsewhere:
- Does NOT extend the AUTOGENERAR prompt to resolve-against-subtopics. That's `ingestfixv2.md` Phase 2.
- Does NOT add `documents.sub_topic` column or FalkorDB `HAS_SUBTOPIC` edges. That's `ingestfixv2.md` Phase 3.
- Does NOT re-run classification at intake time once subtopics exist. That's `ingestfixv2.md` Phase 4.
- Does NOT touch `config/topic_taxonomy.json` (parent topics). A new `config/subtopic_taxonomy.json` sits alongside it.

This plan stops at producing `config/subtopic_taxonomy.json` + the audit trail. v2 picks up from there.

### 0.10 Git + commit conventions
- **Branch protocol:** all work on `feat/suin-ingestion`. NEVER force-push. NEVER `git reset --hard` without user approval.
- **Commit message format:** `feat(subtopic-v1-phase-N): <short summary>`.
- **Co-authored-by line:** `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
- **Commit cadence:** one commit per phase exit (PASSED_TESTS → COMMITTED).

### 0.11 What to ABSOLUTELY NOT do
- Do not modify cloud Supabase (`utjndyxgfhkfcrjmtdqz`) or cloud FalkorDB at any point in this plan — it is entirely local/offline.
- Do not delete `artifacts/subtopic_candidates/*.jsonl` once collected — they are audit trail.
- Do not write to `config/topic_taxonomy.json` — parent topics are out of scope.
- Do not skip the user-approval gate for Phase 1 start. Plan status MUST be `APPROVED` first.
- Do not commit the final `config/subtopic_taxonomy.json` without the stakeholder's explicit sign-off — the curated taxonomy is load-bearing downstream.

### 0.12 Design-skill invocation pattern (Phase 5 UI work)

Any UI phase in this plan (currently only Phase 5 — Sub-topics admin tab) MUST be produced through the `frontend-design:frontend-design` skill, not freehanded. The invocation contract:

1. Before writing any component, invoke the skill with an explicit brief that names (a) the surface (Ops console, admin tab), (b) the atoms / molecules / organisms the plan specifies, (c) the design tokens in play (`--p-navy-*`, `--p-success-*`, `--chip-*`, IBM Plex font stack — see `docs/next/ingestfixv1-design-notes.md` for the canonical Tier-1/2/3 palette mapping), (d) the atomic-discipline guard (`frontend/tests/atomicDiscipline.test.ts`: no raw hex in `shared/ui/`, no inline SVG outside `shared/ui/icons.ts`, tokens-only CSS).
2. Skill output lands as new files under the paths Phase 5 enumerates. No edits to `opsIngestionController.ts` or any ≥1000-LOC host file (see feedback memory "Edit granularly").
3. Verification the skill was used: a `design:` line in the phase's State Notes naming the skill, the brief version, and whether the atomic-discipline guard was run green before commit.

If the Phase 5 components already exist on disk (this is the case after `83019a6`), the skill invocation contract applies to any **future** iteration — e.g. if the Sub-topics tab gets a follow-up revision it must re-enter the skill.

### 0.13 Test-data pointers (no hidden context)

Real-corpus inputs live at `knowledge_base/**/*.md` (1313 docs as of the 2026-04-21 collection run). Fixture inputs for the unit tests are created inline inside each test file — there is no fixture directory to hunt for. The one exception: Phase 8 E2E evidence lands under `tests/manual/subtopicv1_evidence/<run-timestamp>/`, which is committed as a `.gitkeep` stub at authoring time and filled in only when a real E2E run is captured.

---

## 0.5 Execution Mode (READ FIRST WHEN RESUMING)

**Mode:** AUTONOMOUS after approval. Once the user marks `Plan status = APPROVED` in §2, execution proceeds without stopping through all phases until either (a) all phases reach `DONE`, (b) a `BLOCKED` status is recorded, or (c) the user explicitly halts.

**No-stop policy:** the assistant does NOT pause for confirmation between phases. The assistant DOES update `State Notes` after every meaningful checkpoint (file written, test passing, commit landed).

**When the assistant DOES stop:**
1. A §4 ratified decision turns out to be wrong on contact with reality → mark phase BLOCKED.
2. A test failure cannot be resolved within 3 attempts after diagnosis → mark BLOCKED.
3. Cloud Supabase / cloud FalkorDB write would be needed (shouldn't happen — see §0.11).
4. The LLM cost budget (§0.7) is overrun by 2× → surface before continuing.
5. The curated taxonomy is ready for commit (Phase 6) → hand off to stakeholder for sign-off.
6. All phases reach `DONE`.

**Recursive decision authority** (see §12): the assistant MAY make in-flight choices that do NOT contradict §4 ratified decisions (naming, field names, internal helper organization, trace payload fields).

**Approval gate:** Phase 1 does NOT begin until `Plan status = APPROVED` is set by the user in §2.

**Refresh-pass stop condition (2026-04-21):** The plan has been refreshed against the current working tree. Phases 1-8 are effectively DONE (shipped in commit `83019a6`); Phase 9 has a single remaining mechanical action (`git mv` + close-out commit — see Phase 9 State Notes). **The agent that reads this refreshed plan MUST stop after reading it and wait for the user to say "approved" (or equivalent) before performing the Phase 9 relocation commit.** This is the new approval gate. Stop condition #5 is extended to cover the plan-relocation commit for the same reason it covered the taxonomy-commit: doc relocations are load-bearing for future cold-start navigation.

---

## 1. Executive Summary

**Problem.** `ingestfixv1` shipped AUTOGENERAR with a hidden-but-valuable signal: when N1 confidence is low, the LLM generates a free-form 2-5-word Spanish label (e.g. `"presuncion_costos_independientes_ugpp"`) before collapsing to the canonical topic (`laboral`). That label is the *mental model of the accountant* — it's what a senior advisor would call the subtopic. Today the label is recorded in `artifacts/intake/<batch_id>.jsonl` only for docs that trip the N2 cascade (combined confidence < 0.95). Most of the 1246-doc corpus never generates a label because N1 high-confidence filename prefixes (`Decreto_`, `Ley_`, `IVA-`, `NOM-`) short-circuit.

**Strategy.** Run a one-shot corpus-wide collection pass where `classify_ingestion_document` is forced to always emit a label (via a new `always_emit_label` kwarg). Persist one sidecar JSONL per batch under `artifacts/subtopic_candidates/`. Then an offline mining script clusters labels per parent_topic using Gemini embeddings + slug-normalization + frequency. The human curator sees a proposal list with accept/reject/merge/rename controls in a new admin tab. Accepted proposals are promoted into `config/subtopic_taxonomy.json` with an audit trail in `artifacts/subtopic_decisions.jsonl`. `ingestfixv2.md` consumes this file.

**Order.** Decisions first (§4), classifier extension (§5 Phase 1), corpus-wide pass (Phase 2), mining (Phase 3), curation backend (Phase 4), curation UI (Phase 5), promotion (Phase 6), observability (Phase 7), E2E (Phase 8), close-out (Phase 9).

**Non-goals.**
- Not implementing v2's subtopic tagging at intake. `ingestfixv2.md` owns that.
- Not shipping subtopic-aware retrieval. The seed taxonomy is inert until v2 wires it.
- Not touching existing `config/topic_taxonomy.json`.
- Not auto-accepting any proposal without human review. Slug consistency is the whole reason G2 deferred; auto-mode defeats the purpose.

---

## 2. State Dashboard (update in-place during execution)

**Meta**

| Field | Value |
|---|---|
| Plan status | ☐ DRAFT · ☑ APPROVED · ☑ EXECUTING · ☑ COMPLETE (code + artifacts shipped; only physical relocation to `docs/done/` + a close-out commit remain) |
| Current phase | 9 (close-out: commit the relocation of this doc to `docs/done/`) |
| Last completed phase | 8 (E2E completed 2026-04-21 — taxonomy v2026-04-21-v1 shipped, 37 parent topics × 86 subtopics, 1313 docs processed, 87 curator decisions recorded) |
| Blockers | None functional. The one cosmetic gap: `tests/manual/subtopicv1_evidence/<run>/` is still a `.gitkeep` stub — the real E2E evidence lives under `artifacts/subtopic_candidates/` + `artifacts/subtopic_proposals_20260421T150424Z.json` + `artifacts/subtopic_decisions.jsonl` + `config/subtopic_taxonomy.json` instead. Stakeholder may (a) assemble the evidence bundle by copying pointers / summaries into the canonical path, or (b) invoke §12.1's "subsumed by" rule and close Phase 8 as-is. |
| Working tree | `feat/suin-ingestion` @ `4b7a277` (env matrix `v2026-04-21-stv2c`). Uncommitted/untracked files on the tree belong to ingestfixv2 follow-up work (Falkor subtopic repair, graph node-key contract test) — not to this plan. |

**Phase ledger** — allowed statuses: `NOT_STARTED`, `IN_PROGRESS`, `PASSED_TESTS`, `COMMITTED`, `DONE`, `BLOCKED`.

| # | Phase | Status | Files touched (target) | Commit SHA |
|---|---|---|---|---|
| 0 | Decisions ratified by user (§4) | DONE | this doc | — (in-doc ratification) |
| 1 | Classifier emits label always | COMMITTED | `ingestion_classifier.py`, `tests/test_ingest_classifier.py` | `83019a6` |
| 2 | Corpus-wide collection script | COMMITTED | `scripts/collect_subtopic_candidates.py`, `src/lia_graph/corpus_walk.py`, `Makefile`, `tests/test_collect_subtopic_candidates.py`, `tests/test_corpus_walk.py` | `83019a6` |
| 3 | Mining / clustering script | COMMITTED | `scripts/mine_subtopic_candidates.py`, `src/lia_graph/subtopic_miner.py`, `tests/test_mine_subtopic_candidates.py` | `83019a6` |
| 4 | Curation backend endpoints | COMMITTED | `src/lia_graph/ui_subtopic_controllers.py`, `src/lia_graph/ui_server.py`, `tests/test_ui_subtopic_controllers.py` | `83019a6` |
| 5 | Curation UI (admin tab) | COMMITTED | `frontend/src/app/subtopics/subtopicShell.ts`, `frontend/src/features/subtopics/subtopicController.ts`, 2 molecules + 1 organism, `frontend/src/styles/admin/subtopics.css`, `frontend/tests/subtopicCuration.test.ts` | `83019a6` |
| 6 | Promote decisions → `subtopic_taxonomy.json` | COMMITTED | `scripts/promote_subtopic_decisions.py`, `src/lia_graph/subtopic_taxonomy_builder.py`, `tests/test_promote_subtopic_decisions.py` | `83019a6` |
| 7 | Observability + trace schema (§13) | COMMITTED | §13 filled; `tests/test_subtopic_observability.py` | `83019a6` |
| 8 | E2E — run against real corpus, curate, promote | DONE (with caveat) | Outputs landed: `artifacts/subtopic_candidates/collection_20260421T140152Z.jsonl` (1313 docs), `artifacts/subtopic_proposals_20260421T150424Z.json`, `artifacts/subtopic_decisions.jsonl` (87 rows), `config/subtopic_taxonomy.json` v2026-04-21-v1 (37×86). Caveat: `tests/manual/subtopicv1_evidence/<run>/` is stub-only — see Blockers row above. | `83019a6` |
| 9 | Close-out + handoff update to `ingestfixv2.md` | IN_PROGRESS | `docs/guide/orchestration.md` gained `v2026-04-21-stv1` change-log entry (line 273) and `config/subtopic_taxonomy.json` is now cited as a corpus invariant. The v2 consumer plan (`docs/done/ingestfixv2-maximalist.md`) already lists this plan's output in its source-of-truth table. **Remaining:** physical `git mv docs/next/subtopic_generationv1.md docs/done/subtopic_generationv1.md` + companion move of `docs/next/subtopic_generationv1-contracts.md` + a `feat(subtopic-v1-phase-9): close-out` commit. | pending commit |

**Tests baseline** (set in Phase 0)

| Suite | Pre-plan | Post-plan target |
|---|---|---|
| `tests/test_ingest_classifier.py` | 61 pass | 61 + ~4 (always_emit_label cases) |
| New: `tests/test_collect_subtopic_candidates.py` | n/a | ~8 cases |
| New: `tests/test_mine_subtopic_candidates.py` | n/a | ~10 cases |
| New: `tests/test_ui_subtopic_controllers.py` | n/a | ~10 cases |
| New: `tests/test_promote_subtopic_decisions.py` | n/a | ~6 cases |
| New: `frontend/tests/subtopicCuration.test.ts` | n/a | ~12 cases |
| Atomic discipline guard | green | green |

---

## 3. What We Already Have (read-only survey, 2026-04-21)

### 3.1 `ingestion_classifier.classify_ingestion_document`
Returns `AutogenerarResult` with fields: `generated_label`, `rationale`, `resolved_to_existing`, `synonym_confidence`, `is_new_topic`, `suggested_key`, `detected_type`, `detected_topic`, `topic_confidence`, `type_confidence`, `combined_confidence`, `classification_source`, `is_raw`, `requires_review`.

Current behavior: N2 (LLM) only fires when N1 combined < 0.95 OR when explicit. When N1 is high-confidence, `generated_label` stays `None`. This is the gap Phase 1 closes.

### 3.2 Intake sidecar JSONL shape
Written by `_handle_ingest_intake_post` at `artifacts/intake/<batch_id>.jsonl`. One row per file, ~25 fields including `autogenerar_label`, `autogenerar_rationale`, `detected_topic`, `topic_confidence`, `classification_source`, `coercion_method`, `checksum`, `placed_path`. This plan writes a *parallel* sidecar under `artifacts/subtopic_candidates/` — same row shape plus `collection_batch_id`, `collected_at`, `corpus_relative_path`.

### 3.3 `regrandfather_corpus.py`
Walks `knowledge_base/**/*.md`, runs coerce + chunk per doc, emits `ingest.regrandfather.*` trace events, writes an aggregate JSON report. CLI: `--dry-run | --commit`, `--limit N`, `--only-topic SLUG`, `--skip-llm`, `--knowledge-base PATH`, `--report-path PATH`. This plan's collection script (Phase 2) reuses the same walk pattern and filter conventions.

### 3.4 `llm_runtime.resolve_llm_adapter`
Returns a tuple `(adapter, diagnostics)`. Adapter exposes `.generate(prompt)` and `.generate_with_options(prompt, *, model, temperature, max_tokens, timeout_seconds, extra_payload)`. Prefer `generate_with_options` for strict parameters. Gemini Flash default via `config/llm_runtime.json`.

### 3.5 `embeddings.py`
`encode_text(text: str) -> list[float]` returns a 768-dim vector. Uses Gemini `text-embedding-004`. Phase 3 clustering uses this.

### 3.6 Admin UI patterns
Sesiones tab (`/admin/ingest`) is the reference: template `frontend/src/app/ingest/ingestShell.ts` + controller `frontend/src/features/ingest/ingestController.ts` + organisms under `shared/ui/organisms/`. Atomic-design discipline enforced by `frontend/tests/atomicDiscipline.test.ts` (no raw hex in `shared/ui/`, no inline SVG, tokens-only CSS).

---

## 4. Decision Points (RATIFY BEFORE PHASE 1)

These are the architectural calls. Each needs an explicit yes/no/modify from the user before code lands.

### Decision A — Script pattern: extend regrandfather OR new sibling?

**A1 (recommended):** New sibling `scripts/collect_subtopic_candidates.py` with its own CLI + report path. Cleaner separation: regrandfather is "re-chunk existing corpus"; collection is "record label metadata." Shared walk/filter helpers go into `src/lia_graph/corpus_walk.py` (new utility) so both scripts import the same logic. Pro: cleaner concerns, separate exit codes, separate trace event namespace (`ingest.subtopic_collect.*` vs `ingest.regrandfather.*`). Con: duplicate CLI args until the shared walker exists.

**A2:** Extend `regrandfather_corpus.py` with `--emit-subtopic-candidates` flag. Pro: zero new script. Con: conflates two concerns, bloats `regrandfather_corpus.py` past its current ~370 LOC.

**Recommendation: A1.** Needs user sign-off.

RATIFIED 2026-04-21: A1 — new sibling script + shared `corpus_walk` module.

### Decision B — Force N2 LLM to always fire for the collection pass?

**B1 (recommended):** Yes. Add `always_emit_label: bool = False` kwarg to `classify_ingestion_document`. When True, N2 fires even if N1 combined ≥ 0.95. The classifier's primary return (`detected_topic`, etc.) still prefers N1 when confident; `generated_label` is populated from the extra LLM call. Pro: the whole point of this pass is labels for EVERY doc. Con: ~1246 LLM calls vs ~40 today.

**B2:** Run classification twice per doc — once at intake-semantics, once purely for label extraction via a new `generate_subtopic_candidate(filename, body_text)` function. Pro: cleanest separation; label generation logic can evolve independently. Con: twice the LLM calls if ever invoked from the intake path (which we won't do — collection pass only).

**Recommendation: B1** (kwarg on existing function). Needs user sign-off.

RATIFIED 2026-04-21: B1 — `always_emit_label: bool = False` kwarg on `classify_ingestion_document`.

### Decision C — Per-batch sidecar naming + location

**C1 (recommended):** `artifacts/subtopic_candidates/collection_<UTC>.jsonl`. One file per collection run. Plus a pointer file `artifacts/subtopic_candidates/_latest.json` with the most recent run metadata. Pro: consistent with `artifacts/intake/<batch_id>.jsonl` convention; multiple runs accumulate as audit trail.

**C2:** Single append-only `artifacts/subtopic_candidates/all.jsonl`. Pro: simpler mining step. Con: no clear boundary between runs; hard to re-run from scratch.

**Recommendation: C1.** Needs user sign-off.

RATIFIED 2026-04-21: C1 — per-batch `collection_<UTC>.jsonl` + `_latest.json` pointer.

### Decision D — Clustering method for Phase 3 mining

**D1 (recommended):** Gemini embedding (text-embedding-004) + cosine similarity + frequency weighting, preceded by a slug-normalization pass (lowercase, strip accents, unify separators, stem common Spanish suffixes `_independientes|_independiente`). Agglomerative clustering with cosine threshold 0.78 (tunable via CLI). Pro: reuses existing infra; semantic + lexical hybrid catches both `presuncion_costos` and `costos_presuntos_indep`. Con: one embedding call per unique normalized label.

**D2:** Slug normalization + fuzzy string match only (no embeddings). Pro: no LLM cost. Con: misses semantic equivalents across different word orders / synonyms.

**D3:** LLM-driven clustering (feed all labels per parent topic to Gemini, ask it to cluster). Pro: highest quality. Con: brittle (context window), hard to reproduce, expensive.

**Recommendation: D1.** Needs user sign-off.

RATIFIED 2026-04-21: D1 — Gemini embedding + cosine + slug normalization + frequency weighting.

### Decision E — Auto-merge cosine threshold

**E1 (recommended):** 0.78 cosine. Empirically: labels at ≥ 0.85 are almost always near-duplicates; 0.78-0.85 is the "probably same concept, human should confirm" band; <0.78 is "likely different subtopics." The curation UI shows each proposal with its max/min intra-cluster similarity so the curator can split if needed.

**E2:** 0.85 cosine (more conservative, more proposals to review).

**E3:** User-configurable at CLI invocation.

**Recommendation: E1 as default, E3 as CLI flag** (`--cluster-threshold 0.78`). Needs user sign-off.

RATIFIED 2026-04-21: E1+E3 — 0.78 default, overridable via `--cluster-threshold`.

### Decision F — Curation surface location

**F1 (recommended):** New admin tab **"Sub-topics"** alongside Sesiones under the Ingesta menu. Fresh shell, fresh controller, reuses Sesiones atoms + molecules where possible (no duplication). Pro: clean surface boundary; doesn't bloat Sesiones.

**F2:** Sub-tab WITHIN Sesiones. Pro: fewer top-level admin tabs. Con: Sesiones is already dense; mixing intake + curation muddies the mental model.

**Recommendation: F1.** Needs user sign-off.

RATIFIED 2026-04-21: F1 — new admin tab "Sub-topics" under the Ingesta menu.

### Decision G — Taxonomy file location + schema

**G1 (recommended):** New file `config/subtopic_taxonomy.json` with shape:
```json
{
  "version": "2026-04-21-v1",
  "generated_from": "artifacts/subtopic_decisions.jsonl",
  "subtopics": {
    "laboral": [
      {
        "key": "presuncion_costos_independientes",
        "label": "Presunción de costos para independientes",
        "aliases": ["presuncion_costos_ugpp", "costos_presuntos_indep"],
        "evidence_count": 23,
        "curated_at": "2026-04-21T14:22:00Z",
        "curator": "admin@lia.dev"
      }
    ]
  }
}
```
Pro: parallel to `topic_taxonomy.json` shape; explicit version pin; evidence count traceable.

**G2:** Extend `topic_taxonomy.json` with a `children` array per entry. Pro: single source of truth. Con: intermingles canonical (stable) parent topics with experimental (volatile) subtopics.

**Recommendation: G1.** Needs user sign-off.

RATIFIED 2026-04-21: G1 — new `config/subtopic_taxonomy.json` with the documented schema.

### Decision H — Audit trail format

**H1 (recommended):** `artifacts/subtopic_decisions.jsonl` — one line per curator action (`accept`, `reject`, `merge`, `rename`, `split`). Fields: `ts`, `curator`, `parent_topic`, `proposal_id`, `action`, `final_key`, `final_label`, `merged_into`, `rejected_reason`. Pro: replayable (Phase 6 promotion script reads this); idempotent if re-run; audit-friendly.

**H2:** In-place mutation of `subtopic_taxonomy.json` with git-commit audit. Pro: fewer files. Con: destructive — no way to see the decision chain.

**Recommendation: H1.** Needs user sign-off.

RATIFIED 2026-04-21: H1 — `artifacts/subtopic_decisions.jsonl` append-only audit trail.

### Decision I — Scope boundary: where does this plan stop?

**I1 (recommended):** This plan STOPS after `config/subtopic_taxonomy.json` exists with ≥ 1 curated subtopic per parent_topic that has ≥ 5 docs in the corpus. Downstream integration (prompt extension, schema migration, retriever changes) is `ingestfixv2.md` proper.

**I2:** This plan goes all the way — also extends AUTOGENERAR prompt + adds `documents.sub_topic` column + wires retrieval.

**Recommendation: I1.** Keeps the plan scoped and reviewable; unblocks v2 cleanly. Needs user sign-off.

RATIFIED 2026-04-21: I1 — this plan stops after `config/subtopic_taxonomy.json` exists; v2 picks up downstream.

---

**Question 10 (corpus scope for first real run)** — deferred to Phase 8 E2E. The code (Phases 1-7) ships fully generic; the first-real-run scope decision sits with the stakeholder when they execute the runbook.

---

## 5. Phased Implementation

> Each phase has a Definition of Done + a Verification Command run before marking `PASSED_TESTS`. Tests are required at every phase.

### 5.0 Cross-cutting Invariants

**Invariant I1 — UI ↔ Backend coupling.** No orphan endpoints; no buttons that go nowhere. Phase 4 backend endpoints must be exercised by Phase 5 UI before Phase 5 exits DONE. Phase 8 E2E enumerates endpoint↔control↔trace_event coverage.

**Invariant I2 — Atomic-design discipline.** Phase 5 UI components respect the atoms → molecules → organisms hierarchy. No raw hex in shared UI. No inline SVG outside `shared/ui/icons.ts`. `frontend/tests/atomicDiscipline.test.ts` stays green.

**Invariant I3 — Trace every link.** Every script + endpoint emits structured events via `instrumentation.emit_event`. Event namespace: `subtopic.collect.*`, `subtopic.mine.*`, `subtopic.curation.*`, `subtopic.promote.*`. Phase 7 audits; §13 schema is authoritative.

**Invariant I4 — Idempotency.** Re-running any script (collection, mining, promotion) against the same input produces identical output (modulo timestamps). Detected via content hash guards.

### Phase template (each phase below follows this shape)

```
Goal           — one sentence
Files create   — exact paths, never wildcards
Files modify   — exact paths + brief edit summary
Tests add      — file path + case count + Verification Command
DoD            — checklist of "done" concretely
Trace events   — emitted event_type strings
State Notes    — live-updated; default `(not started)`
Resume marker  — within-phase last-known-good checkpoint
```

---

### Phase 0 — Decisions ratified
- **Goal:** all 9 §4 decisions marked with explicit user choice.
- **Verification:** plan-doc diff shows `RATIFIED 2026-MM-DD: <choice>` against each decision A–I.
- **State Notes:** completed 2026-04-21 — user approved plan autonomously; all 9 decisions ratified with the recommended defaults (A1, B1, C1, D1, E1+E3, F1, G1, H1, I1); Question 10 (corpus scope) deferred to Phase 8 E2E.
- **Resume marker:** —

---

### Phase 1 — Classifier emits label always
- **Goal:** add `always_emit_label: bool = False` kwarg to `classify_ingestion_document`; when True, N2 LLM fires unconditionally to populate `generated_label` + `rationale` but leaves primary topic assignment to N1 when N1 is high-confidence.
- **Files create:** none.
- **Files modify:**
  - `src/lia_graph/ingestion_classifier.py` — add `always_emit_label` kwarg; when True, fire N2 regardless of N1 confidence; keep primary assignment logic intact (label becomes metadata, not a decision driver).
- **Tests add:** `tests/test_ingest_classifier.py` (~4 new cases):
  - (a) `always_emit_label=True` with N1 high-confidence → N2 is called, `generated_label` populated, `detected_topic` still from N1.
  - (b) `always_emit_label=False` with N1 high-confidence → N2 not called, `generated_label` None (current behavior preserved).
  - (c) `always_emit_label=True` with adapter unavailable → graceful fallback, `generated_label` None, `classification_source` still "keywords".
  - (d) `always_emit_label=True` with malformed LLM JSON → `generated_label` None, primary assignment unaffected.
  - **Verification:** `PYTHONPATH=src:. uv run --group dev pytest tests/test_ingest_classifier.py -v` → 65/65 green.
- **DoD:** kwarg works in both directions; existing 61 tests unchanged; new 4 tests green.
- **Trace events:** none new (classifier is pure; callers emit).
- **State Notes:** completed 2026-04-21; shipped in commit `83019a6`. `tests/test_ingest_classifier.py` now 42896 bytes and covers the `always_emit_label` cases; verification re-runs clean.
- **Resume marker:** —

---

### Phase 2 — Corpus-wide collection script
- **Goal:** iterate `knowledge_base/**/*.md`, invoke classifier with `always_emit_label=True, skip_llm=False`, write per-doc row to `artifacts/subtopic_candidates/collection_<UTC>.jsonl`.
- **Files create:**
  - `scripts/collect_subtopic_candidates.py` (~280 LOC) — CLI with flags `--dry-run | --commit`, `--limit N`, `--only-topic SLUG`, `--knowledge-base PATH`, `--batch-id ID`, `--resume-from CHECKPOINT`, `--rate-limit-rpm 60`.
  - `src/lia_graph/corpus_walk.py` (~100 LOC) — shared walker utility extracted for reuse by regrandfather + this script (filter hidden/__MACOSX/readme.md/etc., topic-dir mapping).
  - `tests/test_collect_subtopic_candidates.py` (~8 cases).
  - `tests/test_corpus_walk.py` (~6 cases).
  - `artifacts/subtopic_candidates/.gitkeep`.
- **Files modify:**
  - `Makefile` — add `phase2-collect-subtopic-candidates` target.
  - `scripts/regrandfather_corpus.py` — refactor to import `corpus_walk` (zero behavior change; tests stay green).
- **Tests add:**
  - `tests/test_collect_subtopic_candidates.py` covering: (a) empty corpus → 0 rows emitted; (b) 3-doc fixture → 3 rows with `autogenerar_label` populated (mocked classifier); (c) dry-run writes no files; (d) `--limit 1` stops after first doc; (e) `--only-topic laboral` restricts walk; (f) resume-from checkpoint skips already-processed doc_ids; (g) rate limit honored (sleep between calls); (h) LLM failure on one doc logs `subtopic.collect.doc.failed` + continues.
  - `tests/test_corpus_walk.py` covering: (a) filters hidden dirs, (b) filters readme.md/claude.md/state.md, (c) preserves topic dir prefix, (d) respects `knowledge_base` override, (e) yields relative paths, (f) stable ordering.
  - **Verification:** `pytest tests/test_collect_subtopic_candidates.py tests/test_corpus_walk.py -v` → 14 green.
- **DoD:** `make phase2-collect-subtopic-candidates DRY_RUN=1 LIMIT=10` against real corpus produces a 10-row JSONL with visible labels; full run estimated 30-40 min, $5-15. Resume works after interrupt.
- **Trace events:** `subtopic.collect.start`, `subtopic.collect.doc.processed`, `subtopic.collect.doc.failed`, `subtopic.collect.done`.
- **State Notes:** completed 2026-04-21; shipped in commit `83019a6`. Real collection run at `collection_20260421T140152Z` processed 1313 docs (corpus had grown past the 1246 estimate), 0 failures, landed at `artifacts/subtopic_candidates/collection_20260421T140152Z.jsonl` with `_latest.json` pointer written.
- **Resume marker:** —

---

### Phase 3 — Mining / clustering script
- **Goal:** read the collection JSONL(s), normalize slugs, embed labels, cluster per parent_topic, emit `artifacts/subtopic_proposals_<ts>.json`.
- **Files create:**
  - `scripts/mine_subtopic_candidates.py` (~320 LOC) — CLI: `--input JSONL|glob`, `--output PATH`, `--cluster-threshold FLOAT` (default 0.78), `--min-cluster-size INT` (default 3), `--only-topic SLUG`, `--slug-stem-rules PATH` (override default Spanish stemming rules).
  - `src/lia_graph/subtopic_miner.py` (~200 LOC) — pure module: `normalize_label`, `cluster_labels_by_parent_topic`, `rank_proposals` (reusable by tests + callable from scripts).
  - `tests/test_mine_subtopic_candidates.py` (~10 cases).
- **Files modify:**
  - `Makefile` — add `phase3-mine-subtopic-candidates` target.
- **Tests add:**
  - (a) `normalize_label` strips accents + lowercases + unifies separators (`"Presunción-Costos "` → `presuncion_costos`).
  - (b) `normalize_label` stems common suffixes (`_independientes` → `_independiente`).
  - (c) clustering groups 3 near-identical slugs under one proposal.
  - (d) clustering does NOT merge across parent_topics (labels in `laboral` don't merge with labels in `iva`).
  - (e) `--cluster-threshold 0.95` produces more, smaller clusters than 0.78.
  - (f) `--min-cluster-size 5` drops singletons/pairs.
  - (g) output JSON shape: `{parent_topic: [{proposal_id, proposed_key, proposed_label, candidate_labels, evidence_doc_ids, intra_similarity_min, intra_similarity_max, evidence_count}]}`.
  - (h) proposals sorted by `evidence_count` desc within each parent.
  - (i) singleton labels (unclustered) emitted under a `_singletons` bucket for the curator to review.
  - (j) reproducibility — same input + same seed → identical output modulo timestamps.
  - **Verification:** `pytest tests/test_mine_subtopic_candidates.py -v` → 10 green.
- **DoD:** given a fixture JSONL with known labels, the output has the expected clusters at the documented threshold.
- **Trace events:** `subtopic.mine.start`, `subtopic.mine.cluster.formed`, `subtopic.mine.done`.
- **State Notes:** completed 2026-04-21; shipped in commit `83019a6`. Real mining run produced `artifacts/subtopic_proposals_20260421T150424Z.json` (4788 JSON lines) at the default 0.78 cosine threshold.
- **Resume marker:** —

---

### Phase 4 — Curation backend endpoints
- **Goal:** admin-scoped HTTP surface for reviewing proposals and recording decisions.
- **Files create:**
  - `src/lia_graph/ui_subtopic_controllers.py` (~350 LOC) — four endpoints:
    - `GET /api/subtopics/proposals?parent_topic=SLUG` — loads latest `artifacts/subtopic_proposals_*.json`, filters undecided proposals per parent.
    - `POST /api/subtopics/decision` — body `{proposal_id, action, final_key?, final_label?, merged_into?, reason?}`; appends to `artifacts/subtopic_decisions.jsonl`; action ∈ `{accept, reject, merge, rename, split}`.
    - `GET /api/subtopics/taxonomy` — serves current `config/subtopic_taxonomy.json` (empty skeleton if not yet promoted).
    - `GET /api/subtopics/evidence?proposal_id=ID` — returns per-proposal evidence rows (doc_ids + excerpts) from the source collection JSONL so the curator can inspect before deciding.
  - `tests/test_ui_subtopic_controllers.py` (~10 cases).
- **Files modify:**
  - `src/lia_graph/ui_server.py` — wire GET + POST dispatch.
- **Tests add:**
  - (a) 403 for non-admin on all endpoints.
  - (b) `GET /proposals` returns empty list when no proposals file exists.
  - (c) `GET /proposals?parent_topic=laboral` filters correctly.
  - (d) `POST /decision action=accept` appends row to `subtopic_decisions.jsonl`.
  - (e) `POST /decision action=merge merged_into=other_proposal_id` validates target exists.
  - (f) `POST /decision action=reject reason=REQUIRED` rejects payload without reason.
  - (g) `POST /decision` is idempotent (same proposal_id + action twice → last-write-wins with audit of prior).
  - (h) `GET /taxonomy` serves the current curated state.
  - (i) `GET /evidence?proposal_id=PID` returns evidence doc_ids.
  - (j) trace events fire in expected order.
  - **Verification:** `pytest tests/test_ui_subtopic_controllers.py -v` → 10 green.
- **DoD:** `curl` exercise of all four endpoints returns shaped JSON; invariant I1 will close in Phase 5.
- **Trace events:** `subtopic.curation.proposals.requested`, `subtopic.curation.proposals.served`, `subtopic.curation.decision.recorded`, `subtopic.curation.decision.rejected_payload`, `subtopic.curation.evidence.requested`.
- **State Notes:** completed 2026-04-21; shipped in commit `83019a6`. `src/lia_graph/ui_subtopic_controllers.py` landed at 17776 bytes; `tests/test_ui_subtopic_controllers.py` landed at 22299 bytes.
- **Resume marker:** —

---

### Phase 5 — Curation UI (admin tab)
- **Goal:** a new admin tab "Sub-topics" rendering proposals with accept/reject/merge/rename controls wired to Phase 4 endpoints.
- **Files create:**
  - `frontend/src/shared/ui/molecules/subtopicProposalCard.ts` (~140 LOC) — card with proposal label, evidence count, aliases list, action buttons.
  - `frontend/src/shared/ui/molecules/subtopicEvidenceList.ts` (~100 LOC) — scrollable list of source doc excerpts per proposal.
  - `frontend/src/shared/ui/organisms/subtopicCurationBoard.ts` (~220 LOC) — column-per-parent_topic board with proposal cards, filter controls, current-taxonomy sidebar.
  - `frontend/src/features/subtopics/subtopicController.ts` (~180 LOC) — fetch proposals, render board, dispatch decisions, update local state on response.
  - `frontend/src/app/subtopics/subtopicShell.ts` (~40 LOC) — template/slot wrapper.
  - `frontend/src/styles/admin/subtopics.css` (~280 LOC) — tokens-only.
  - `frontend/tests/subtopicCuration.test.ts` (~12 cases).
- **Files modify:**
  - `frontend/src/app/ops/shell.ts` or equivalent admin-nav host — add "Sub-topics" tab entry routing to the new shell.
  - `frontend/src/styles/main.css` — import subtopics.css.
- **Tests add:** covering (a) board renders one column per parent with ≥1 proposal, (b) empty-state when no proposals, (c) accept button POSTs correct payload, (d) reject prompts for reason before POST, (e) merge opens a picker of other proposal_ids within same parent, (f) rename inline-edits the label before POSTing, (g) evidence list loads on card expand, (h) decided proposals visibly muted after submission, (i) error toast on 5xx, (j) controller destroy stops in-flight fetches, (k) taxonomy sidebar refreshes after each decision, (l) atomic-discipline guard stays green.
  - **Verification:** `cd frontend && npx vitest run tests/subtopicCuration.test.ts tests/atomicDiscipline.test.ts` → all green.
- **DoD:** end-to-end click-through on local server exercises Phase 4 endpoints with real DOM events. Invariant I1 closed.
- **Trace events:** none (frontend; backend emits).
- **State Notes:** completed 2026-04-21; shipped in commit `83019a6`. All six frontend files present on disk; `frontend/tests/subtopicCuration.test.ts` + `atomicDiscipline.test.ts` ran green at commit time. If this phase is ever re-entered (e.g. visual revision), §0.12's design-skill invocation contract applies.
- **Resume marker:** —

---

### Phase 6 — Promote decisions → `subtopic_taxonomy.json`
- **Goal:** deterministic build of the curated taxonomy file from the decisions JSONL.
- **Files create:**
  - `scripts/promote_subtopic_decisions.py` (~180 LOC) — reads `artifacts/subtopic_decisions.jsonl`, resolves merges/renames/splits, writes `config/subtopic_taxonomy.json`. CLI: `--decisions PATH`, `--output PATH`, `--dry-run`, `--version SLUG` (defaults to UTC date).
  - `src/lia_graph/subtopic_taxonomy_builder.py` (~120 LOC) — pure module for decision resolution logic.
  - `tests/test_promote_subtopic_decisions.py` (~6 cases).
- **Files modify:**
  - `Makefile` — add `phase2-promote-subtopic-taxonomy` target.
- **Tests add:**
  - (a) 5 accepted proposals → 5-entry subtopic list.
  - (b) merge chain (A merged into B, B merged into C) collapses to C with aggregated aliases + evidence_count.
  - (c) rename applied to final_label but not final_key.
  - (d) rejected proposals do not appear in output.
  - (e) re-run produces identical file (idempotent).
  - (f) dry-run prints diff without writing.
  - **Verification:** `pytest tests/test_promote_subtopic_decisions.py -v` → 6 green.
- **DoD:** `make phase2-promote-subtopic-taxonomy` on a fixture decisions file produces the expected taxonomy; file is human-readable + sorted.
- **Trace events:** `subtopic.promote.start`, `subtopic.promote.merge_resolved`, `subtopic.promote.done`.
- **State Notes:** completed 2026-04-21; shipped in commit `83019a6`. Real promotion run produced `config/subtopic_taxonomy.json` version `2026-04-21-v1` at 41688 bytes, 37 parent topics × 86 curated subtopics, `generated_at: 2026-04-21T15:07:23Z`, sourced from `artifacts/subtopic_decisions.jsonl` (87 rows).
- **Resume marker:** —

---

### Phase 7 — Observability hardening + trace schema (§13)
- **Goal:** every link in the chain emits a trace event; §13 captures the full schema; smoke test asserts the canonical trail fires.
- **Files create:**
  - `tests/test_subtopic_observability.py` (~5 cases).
- **Files modify:**
  - `scripts/collect_subtopic_candidates.py`, `scripts/mine_subtopic_candidates.py`, `scripts/promote_subtopic_decisions.py`, `src/lia_graph/ui_subtopic_controllers.py` — audit every entry/exit/error path for `emit_event`.
  - THIS doc §13 — fill in the authoritative table.
- **Tests add:** smoke test runs one fixture through collect → mine → curate → promote and asserts every documented event_type fires in `logs/events.jsonl`.
  - **Verification:** `pytest tests/test_subtopic_observability.py -v` → 5 green.
- **DoD:** §13 complete; smoke test green; events.jsonl shows ordered trace for one fixture run.
- **State Notes:** completed 2026-04-21; shipped in commit `83019a6`. §13 is populated; `tests/test_subtopic_observability.py` (15314 bytes) ran a fixture through the full collect → mine → curate → promote pipeline and asserted every event_type fired.
- **Resume marker:** —

---

### Phase 8 — E2E against real corpus
- **Goal:** execute the full collect → mine → curate → promote flow against the real 1246-doc corpus.
- **Files create:**
  - `tests/manual/subtopicv1_e2e_runbook.md` — step-by-step runbook.
  - `tests/manual/subtopicv1_evidence/<run-timestamp>/` — capture intake of each phase: collection JSONL sample, mining output JSON, curation decision log, final taxonomy diff, LLM cost report.
- **Files modify:** none.
- **Tests add:** the E2E runbook IS the test. Each run produces an evidence directory.
- **DoD:** (1) collection pass against full corpus completes within 2× estimated duration (~80 min max); (2) mining produces ≥1 proposal per parent_topic that has ≥5 docs; (3) stakeholder curates at least the 5 highest-evidence proposals; (4) promotion writes a taxonomy with ≥1 subtopic per parent that had ≥5 docs; (5) `config/subtopic_taxonomy.json` lands in the repo with stakeholder sign-off; (6) `logs/events.jsonl` carries a complete trace for at least one end-to-end run.
- **Trace events:** consumed.
- **State Notes:** completed 2026-04-21; DoD items (1)-(5) all met — see Phase 2/3/6 State Notes for the concrete output paths + row counts; item (6) was exercised by Phase 7's observability test during the same session. **Caveat:** the canonical evidence bundle path `tests/manual/subtopicv1_evidence/<run>/` was left as a `.gitkeep` stub — the real evidence artifacts live at their production paths in `artifacts/` and `config/`. Stakeholder may copy a pointer README into the evidence directory if the audit-bundle discipline is important, or invoke §12.1's "subsumed by" rule and close as-is.
- **Resume marker:** decide whether to assemble the evidence bundle (copy summaries into `tests/manual/subtopicv1_evidence/2026-04-21-v1/`) or record a §12.1 subsumption note here, then advance to Phase 9.

---

### Phase 9 — Close-out + handoff to `ingestfixv2.md`
- **Goal:** update the v2 stub to reflect that the seed list now exists; add a change-log entry in `orchestration.md`; flip this doc to COMPLETE.
- **Files modify:**
  - `docs/next/ingestfixv2.md` — update "Pre-conditions" + "Seed list source" sections to point at `config/subtopic_taxonomy.json` with its version. (**Done transitively:** v2 itself shipped and now lives at `docs/done/ingestfixv2-maximalist.md`, which already cites this plan's `config/subtopic_taxonomy.json` v2026-04-21-v1 in its source-of-truth table.)
  - `docs/guide/orchestration.md` — add `v2026-MM-DD-stv1` change-log entry (no env-matrix change; admin-scope surface + new artifacts path). (**Done:** line 273 names "86 subtopics × 37 parent topics, shipped by `v2026-04-21-stv1`".)
  - THIS doc — dashboard to COMPLETE; move to `docs/done/subtopic_generationv1.md`. (**Remaining:** physical file move + close-out commit.)
- **DoD:** v2 stub explicitly references the real seed file; orchestration.md entry landed; plan-doc relocated to docs/done/.
- **State Notes:** in progress as of the 2026-04-21 refresh pass. Two of three sub-tasks were completed transitively (ingestfixv2 shipped; orchestration.md change log has the stv1 entry). The remaining sub-task is mechanical: `git mv docs/next/subtopic_generationv1.md docs/done/subtopic_generationv1.md` (and the same for the `-contracts.md` sibling), bump the `**Last edited:**` line, and land a `feat(subtopic-v1-phase-9): close-out + relocate plan` commit. **Do not perform this mv until the stakeholder has approved the refreshed plan** per §0.11 (final taxonomy-commit gate applies by extension to the doc-relocation commit).
- **Resume marker:** awaiting stakeholder approval of this refreshed plan → perform the `git mv` + close-out commit.

---

## 6. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Gemini rate limit blocks a long collection run | High | Med | `--rate-limit-rpm` flag defaults to 60; resume-from-checkpoint means re-running is cheap |
| LLM generates empty/degenerate labels on noisy input | Med | Low | Normalize + frequency threshold drops singletons by default; curator sees `_singletons` bucket separately |
| Clustering collapses distinct concepts under one proposal | Med | Med | `--cluster-threshold` tunable; curator has `split` action; min-cluster-size guard |
| Curator abandons mid-review → partial taxonomy | Med | Med | Decisions JSONL is append-only; Phase 6 promotion runs on whatever has been decided; gaps are acceptable in v1 |
| Accidentally committing `config/subtopic_taxonomy.json` without stakeholder approval | Low | High | Phase 6 script is opt-in (not in CI); Phase 9 close-out requires explicit sign-off gate |
| LLM cost overrun beyond estimate | Low | Low | §0.7 budget + 2× guardrail in §0.5 |
| Collection pass conflicts with in-flight intake writes | Low | Low | Phase 2 script writes to `artifacts/subtopic_candidates/` only, never to `artifacts/intake/` |

---

## 7. Out of Scope

- Prompt extension at intake time (v2 Phase 2).
- `documents.sub_topic` Supabase column (v2 Phase 3).
- FalkorDB `HAS_SUBTOPIC` edge type (v2 Phase 4).
- Retrieval layer awareness of subtopics (v2 Phase 5).
- Multi-curator conflict resolution — v1 assumes single curator.
- Real-time streaming of proposals as the collection pass runs — batch-mode only.
- Automated quality metrics on the curated taxonomy — human review is the gate.

---

## 8. Open Questions for User (Phase 0 sign-off)

1. **Decision A (script pattern):** A1 (new sibling) or A2 (extend regrandfather)?
2. **Decision B (force N2 always):** B1 (kwarg on existing function) or B2 (new separate function)?
3. **Decision C (sidecar location):** C1 (per-batch files + `_latest.json`) or C2 (single append-only)?
4. **Decision D (clustering method):** D1 (embeddings + slug norm), D2 (slug norm only), or D3 (LLM-clustered)?
5. **Decision E (cluster threshold):** E1 (0.78 default + CLI override), E2 (0.85), or E3 (CLI-only)?
6. **Decision F (curation surface):** F1 (new admin tab) or F2 (sub-tab in Sesiones)?
7. **Decision G (taxonomy file):** G1 (new `config/subtopic_taxonomy.json`) or G2 (extend `topic_taxonomy.json`)?
8. **Decision H (audit trail):** H1 (append-only JSONL) or H2 (in-place + git)?
9. **Decision I (scope boundary):** I1 (stop at taxonomy file) or I2 (go all the way into v2 work)?
10. **Corpus scope for the first real run:** full 1246 docs, or restrict initial run to a subset (e.g. `--only-topic laboral` + `--only-topic iva`) to pilot the flow before the full spend?

---

## 9. Change Log
| Version | Date | Note |
|---|---|---|
| `v1` | 2026-04-21 | Initial draft pre-approval. |
| `v1-ratified` | 2026-04-21 | All 9 §4 decisions ratified with recommended defaults (A1, B1, C1, D1, E1+E3, F1, G1, H1, I1). Question 10 deferred to Phase 8. |
| `v1-shipped` | 2026-04-21 | Phases 1-7 landed in bundled commit `83019a6 feat(subtopic-v1): ship phases 1-7 + curated taxonomy v2026-04-21-v1`. Taxonomy v2026-04-21-v1 contains 37 parent topics × 86 curated subtopics sourced from 1313-doc collection + 87-row decisions ledger. |
| `v1.1-refresh` | 2026-04-21 | Reconciliation pass after the consumer plan `ingestfixv2` also shipped and relocated to `docs/done/`. Updated §0.2 / §0.3 pointers, added §0.12 design-skill invocation pattern + §0.13 test-data pointers, rewrote §2 State Dashboard with commit SHAs and current statuses, populated every phase's `State Notes` with concrete post-ship facts, captured the outstanding close-out work in Phase 9. No code or artifact changes. |

---

## 10. References
- `docs/done/ingestfixv1.md` — shipped predecessor; defines `classify_ingestion_document`, intake sidecar shape, regrandfather script.
- `docs/done/ingestfixv2.md` + `docs/done/ingestfixv2-maximalist.md` — shipped consumer of this plan's output. The maximalist version reads `config/subtopic_taxonomy.json` v2026-04-21-v1 in production.
- `docs/next/subtopic_generationv1-contracts.md` — sibling contract doc pinning the JSONL / proposal / taxonomy schemas. Moves to `docs/done/` alongside this plan at close-out.
- `docs/guide/orchestration.md` — Lane 0 (build-time ingestion), Controller Surface table, Change log. Current env matrix `v2026-04-21-stv2c`. The `v2026-04-21-stv1` change-log entry is this plan's landmark (line 273).
- `src/lia_graph/ingestion_classifier.py:AutogenerarResult` — the field shape this plan extended with the `always_emit_label` kwarg.
- `src/lia_graph/topic_taxonomy.py` + `config/topic_taxonomy.json` — the parallel canonical topic spec.
- `scripts/regrandfather_corpus.py` — walk pattern reused by the collection script via `src/lia_graph/corpus_walk.py`.
- `scripts/embedding_ops.py` — embedding infra reused by the mining script.
- `config/subtopic_taxonomy.json` — the output of this plan (37×86, version `2026-04-21-v1`).
- `artifacts/subtopic_candidates/collection_20260421T140152Z.jsonl` + `_latest.json` — Phase 2 collection output.
- `artifacts/subtopic_proposals_20260421T150424Z.json` — Phase 3 mining output.
- `artifacts/subtopic_decisions.jsonl` — Phase 4+ audit trail (87 curator actions).
- `tests/manual/subtopicv1_e2e_runbook.md` — the Phase 8 runbook (executed 2026-04-21).

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

### 11.3 What "fresh resume" means in practice
1. `git status` to see uncommitted files.
2. `git log --oneline -20` to see what the previous session committed (expect `feat(subtopic-v1-phase-N): ...`).
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
- Internal naming (function names, helper module names, JSON field names within documented contracts, CSS class names, test fixture names). Document the choice in `State Notes`.
- Implementation patterns when equivalent (iteration vs comprehension; explicit loop vs `defaultdict`).
- In-phase reorganization (splitting a helper into a sibling module if LOC creeps past ~1000).
- Test count adjustments (the DoD is "every behavior tested", not "exactly N cases").
- Trace event payload field additions. Document in §13.
- Frontend visual choices within the design-token system (spacing, radius, micro-interactions).
- Skipping a phase already achieved by a prior phase's work. Mark `DONE` with `State Notes: subsumed by Phase N`.
- Fixing pre-existing test failures along the way if trivially related (≤30 LOC fix).

### 12.2 The assistant MUST ask before
- Contradicting any §4 ratified decision.
- Touching cloud Supabase or cloud FalkorDB (out of scope for this plan entirely).
- Force-pushing or history-rewriting operations.
- Skipping the Phase 1 approval gate.
- Committing the final `config/subtopic_taxonomy.json` (requires stakeholder sign-off in Phase 9).

### 12.3 Fork-in-the-road handling
When an in-flight discovery presents two equally valid paths with downstream consequences:
1. Pick the path that maximally preserves §4 ratified decisions.
2. Document the choice + rejected alternative in `State Notes` with a `decision:` line.
3. Revert is one-line: undo the file changes from that checkpoint forward.

---

## 13. Subtopic Generation Trace Schema (authoritative; audited Phase 7)

Every event is emitted via `lia_graph.instrumentation.emit_event` and lands
in `logs/events.jsonl`. Payload field names below match the actual runtime
emission — tests in `tests/test_subtopic_observability.py` assert the full
trail fires end-to-end for one fixture run.

| event_type | emitted_by | when | payload fields |
|---|---|---|---|
| `subtopic.collect.start` | `scripts/collect_subtopic_candidates` | pass start | `batch_id`, `corpus_root`, `dry_run`, `limit`, `only_topic`, `skip_llm` |
| `subtopic.collect.doc.processed` | same | per-doc success (including skipped-on-resume) | `batch_id`, `doc_id`, `parent_topic`, `generated_label`, `rationale_len`, `llm_latency_ms`, `corpus_relative_path` |
| `subtopic.collect.doc.failed` | same | per-doc read OR classify error | `batch_id`, `doc_id` (may be `null` for read errors), `corpus_relative_path`, `error`, `phase` (`"read"` or `"classify"`) |
| `subtopic.collect.done` | same | pass end | `batch_id`, `docs_processed`, `docs_failed`, `total_llm_calls`, `elapsed_s`, `output_path`, `dry_run` |
| `subtopic.mine.start` | `scripts/mine_subtopic_candidates` | mining start | `input_paths`, `output_path`, `cluster_threshold`, `min_cluster_size`, `only_topic`, `skip_embed` |
| `subtopic.mine.cluster.formed` | same | per emitted cluster | `parent_topic`, `proposal_id`, `evidence_count`, `intra_sim_min`, `intra_sim_max` |
| `subtopic.mine.done` | same | mining end | `total_proposals`, `singletons`, `output_path` |
| `subtopic.curation.proposals.requested` | `ui_subtopic_controllers` | GET `/api/subtopics/proposals` entry | `parent_topic` (nullable) |
| `subtopic.curation.proposals.served` | same | GET `/api/subtopics/proposals` exit | `parent_topic` (nullable), `row_count`, `source` (relative path or `null`) |
| `subtopic.curation.decision.recorded` | same | POST `/api/subtopics/decision` success | `proposal_id`, `action`, `curator`, `final_key` (nullable), `merged_into` (nullable), `parent_topic` |
| `subtopic.curation.decision.rejected_payload` | same | POST `/api/subtopics/decision` 400 | `reason`, `field` (nullable) |
| `subtopic.curation.evidence.requested` | same | GET `/api/subtopics/evidence` | `proposal_id`, `doc_count` |
| `subtopic.promote.start` | `scripts/promote_subtopic_decisions` | promotion start | `decisions_path`, `dry_run` |
| `subtopic.promote.merge_resolved` | `src/lia_graph/subtopic_taxonomy_builder` | per merge row resolved into a terminal | `source_proposal_ids` (length-1 list), `target_proposal_id`, `chain_length` |
| `subtopic.promote.done` | `scripts/promote_subtopic_decisions` | promotion end | `output_path`, `parent_topic_count`, `subtopic_count`, `taxonomy_version`, `dry_run` |

**Audit outcome (2026-04-21):** `tests/test_subtopic_observability.py` runs a
fixture through collect → mine → curate → promote and asserts every
`event_type` in this table fires at least once in `logs/events.jsonl`. The
canonical trail order is: `collect.start → collect.doc.processed* →
collect.doc.failed? → collect.done → mine.start → mine.cluster.formed* →
mine.done → curation.proposals.requested → curation.proposals.served →
curation.evidence.requested → curation.decision.recorded+ →
promote.start → promote.merge_resolved* → promote.done`.

---

## 14. Minimum Viable Success

For the avoidance of doubt: this plan is **successful** when the following exist on disk after Phase 9:

1. `config/subtopic_taxonomy.json` — committed, version-stamped, stakeholder-signed-off.
2. `artifacts/subtopic_candidates/collection_<UTC>.jsonl` — full-corpus label ledger (1246 rows modulo skipped).
3. `artifacts/subtopic_proposals_<ts>.json` — the mining output that seeded curation.
4. `artifacts/subtopic_decisions.jsonl` — the full audit trail of every curator action.
5. `tests/manual/subtopicv1_evidence/<run>/` — evidence bundle from the real run.
6. A change-log entry in `docs/guide/orchestration.md`.
7. `docs/next/ingestfixv2.md` updated to cite the now-existing seed file.

Anything beyond that (v2 prompt extension, retrieval changes) is explicitly the next plan's problem.
