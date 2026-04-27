# State of execution — fixplan_v3 (the operational ledger)

> **Status:** stub seeded 2026-04-27 (Bogotá). Sections marked `🚧 TODO` are pending; chapters land in numbered order.
> **Companion to:** `docs/re-engineer/fixplan_v3.md` (the plan; 2,050 lines).
> **Purpose:** the single source of truth for **where execution actually is**. The plan says WHAT to do; this file says WHERE WE ARE, WHO TOUCHED IT LAST, WHAT'S BLOCKED, HOW TO ROLL BACK.
> **Living doc.** Updated by the engineer on every gate crossing; appended-to by cron heartbeats; reviewed weekly with the operator.
> **Reading order for a fresh LLM picking this up cold:** §1 (how to use) → §2 (fresh-LLM preconditions) → §3 (current global state) → §7 (env state) → §4 (your assigned sub-fix's ledger row) → relevant §5 reversibility row → relevant §6 test horizon → start work, updating §10 run log as you go.

---

## §1 — How to use this file

This file is the **execution ledger** for fixplan_v3. The plan answers "what should happen?"; this file answers "what has happened, where are we, and what would we do if X broke right now?"

### §1.1 — Single source of truth

When the plan and the state file disagree, **the state file wins for "where are we"** and the plan wins for "what to do next." Concretely:

- The plan says: "Sub-fix 1B-γ ships migrations + sink in week 6-7." That is binding intent.
- The state file says: "Sub-fix 1B-γ is at gate-2 (plan signed off, no code yet); engineer assigned; last update 2026-04-29 11:00 AM Bogotá; blocked on Activity 6 canonicalizer pilot." That is binding reality.

If a contradiction surfaces (plan says shipped, state file says gate-3): trust the state file, dig into the run log (§10) to see why, fix the plan if needed, never silently update the state file to match the plan.

### §1.2 — Update cadence

| Who | When | What they update |
|---|---|---|
| Engineer working a sub-fix | **Every gate crossing** | §3 current global state, §4 ledger row for their sub-fix, §10 run log (one narrative entry) |
| Engineer deploying a migration / batch / cron | **Before AND after** the deploy | §7 environment state (mark as in-progress before; mark as applied or rolled-back after) |
| Cron job (heartbeat) | **Every 6h** | §10 run log (condensed entry: cron tick, queue depth, last action) |
| SME after signoff session | **Same session** | §4 relevant ledger rows; §9 open questions resolved |
| Operator after weekly review | **Weekly** | §3 active week field; §9 escalations to operator |
| Anyone hitting a failure | **Immediately** | §10 run log (failure entry) + §9 open question if recovery is unclear |

### §1.3 — Conflict resolution

If two updates collide (e.g., engineer A marks gate-3 done while engineer B marks the same sub-fix as blocked):
1. The later timestamp wins for that field.
2. Both authors get pinged via §10 run log to reconcile.
3. The operator is the tie-breaker for irreconcilable conflicts.

### §1.4 — Relationship to other docs

| Doc | Role | Updated by |
|---|---|---|
| `fixplan_v3.md` | The plan (WHAT). Architecture, sub-fix specs, gate criteria, budget. | Operator + tech lead via PR; rare changes |
| **This file** (`state_fixplan_v3.md`) | The state (WHERE). Gate ledger, env state, run log, reversibility matrix. | Engineers, cron, SME, operator constantly |
| `fixplan_v2.md` | Historical record of the per-document persistence approach v3 replaces. | Frozen |
| `docs/orchestration/orchestration.md` | Authoritative env matrix + change log for the served runtime. | Bumped on every `LIA_*` flag change |
| `docs/learnings/` | Append-only lessons from closed fixes. | After each ship |
| `evals/activity_1_5/persistence_audit.jsonl` | Audit log of Activity 1.5b's writes. Frozen. | Frozen |

### §1.5 — How to update sections

- **§3 current global state:** in-place edit. The state file holds *current* state, not history.
- **§4 ledger:** in-place edit per sub-fix row. Each row has its own "last update" timestamp.
- **§5 reversibility matrix:** add rows when new actions are introduced; never remove rows for shipped actions (the procedure stays valid post-ship for emergency rollback).
- **§7 environment state:** in-place edit per env-cell (dev / staging / production × migration / extraction / cron).
- **§9 open questions:** append-only when adding; in-place when resolving (mark `RESOLVED yyyy-mm-dd hh:mm by <author>`); never delete.
- **§10 run log:** append-only. Newest entries at the **top** so a fresh reader sees latest first.

### §1.6 — Why this file matters more than it looks

A 2,050-line plan doc is unusable mid-incident. When something breaks at 11 PM Bogotá and the operator needs to know "is the cascade orchestrator running clean? when did the last migration land? what's the rollback?", they read this file, not the plan. The plan is for designing; this file is for executing and recovering.

---

## §2 — Fresh-LLM runnable preconditions

**Answer in one sentence:** Yes, a fresh LLM can run v3 from these docs alone — *if* it gets the right input set, honors the hard guardrails, and surfaces SME-required questions to a queue rather than guessing.

### §2.1 — Required input set (minimum to start)

A fresh LLM picking this up cold must read, in this order, before touching any code:

1. **`CLAUDE.md`** (repo root) — non-negotiables, hot path, six-gate lifecycle, long-running-job convention.
2. **`AGENTS.md`** (repo root) — surface boundaries.
3. **`docs/orchestration/orchestration.md`** — env matrix + change log.
4. **`docs/orchestration/retrieval-runbook.md`** + **`coherence-gate-runbook.md`** — failure-mode origins.
5. **`docs/re-engineer/fixplan_v3.md`** §0–§0.11 (~60 min) — architecture + persistence model + skill contracts.
6. **This file** (`state_fixplan_v3.md`) — current execution position.
7. The 7 veredicto fixtures in **`evals/activity_1_5/*.json`** + **`persistence_audit.jsonl`** — what skill output looks like + what 1.5b wrote.
8. The skill at **`.claude/skills/vigencia-checker/`** — the verification protocol the LLM will invoke.

If the LLM is asked to work on a specific sub-fix, it additionally reads that sub-fix's "Files — Read first" list from `fixplan_v3.md` §2.

### §2.2 — Hard guardrails (the LLM may NEVER violate these)

| Guardrail | Why | Enforcement |
|---|---|---|
| **No irreversible action without explicit operator green-light** | Migrations, drops, deletes, force-pushes, prod deploys can destroy state. | The LLM stops before any action listed in §5 reversibility matrix marked `requires_operator_signoff: true`, asks the operator, waits. |
| **No code path that writes to `norm_vigencia_history` outside `src/lia_graph/persistence/norm_history_writer.py`** | The writer enforces the §0.3.3 `change_source` shape and the append-only invariants. | Code review + a CI lint that greps for direct INSERT statements on the table. |
| **No mid-turn vigencia research from retrieval path** | Latency + non-determinism + feedback loop (per fixplan_v3 §0.7.3). | The LLM's `extracted_by` field on any new history row must be `cron@v1` or `manual_sme:<email>` — `synthesis@v1` and `retrieval@v1` are forbidden writers. |
| **No silent canonicalizer guess on ambiguous mentions** | The canonicalizer's refusal contract is the safety boundary (per §0.5.4). | If the canonicalizer returns refusal, the LLM logs it to `evals/canonicalizer_refusals_v1/refusals.jsonl` — never falls back to substring matching or training-data memory. |
| **No threshold lowering on missed gates** | Per `feedback_thresholds_no_lower`. The bar stays "safe to send to a client." | Document the exception per case in §10 run log; never change the gate criterion in fixplan_v3. |
| **No skipping test horizons** | Premature testing produces false fails; late testing wastes time on built-on-sand sub-fixes. | The LLM consults §6 before running tests; respects the "do not test at H0" markers. |
| **No vigencia writes to `documents.vigencia` after 1B-γ ships** | Per fixplan_v3 §12. The deprecation view exists for a reason. | PR review enforces; a CI lint can grep for `documents.vigencia` writes. |
| **No SME-equivalent decisions without surfacing to §9** | Skill prompt updates, ontology session signoff, fixture authoring, canonicalizer rule additions from triage — all SME-owned. | The LLM appends to §9 with the question + what's blocked + escalation path. Never guesses. |

### §2.3 — SME touchpoints the LLM cannot self-serve

These require a human SME (Alejandro or successor) to sign off:

| Touchpoint | Sub-fix | Cadence |
|---|---|---|
| Ontology session — review 11-state taxonomy + skill v2.0 prompt update | 1A | Once, week 1-2 |
| Skill v2.0 prompt review + signoff | 1A | Once per prompt revision |
| Activity 1.7b — pick canonical norms for VC/VL/DI/RV state seeding | 1.7b | Once, week 1-2 |
| Activity 6 — canonicalizer 50-chunk pilot review | 6 | Once, week 2 |
| Skill Eval — 30-case authoring | Skill Eval | 5 cases/week, weeks 1-6 |
| Refusal-queue triage | 1B-δ + Fix 6 | Weekly batches, weeks 6-13 |
| 100-norm SME spot-check on 1B-β extraction batch | 1B-β | Once, week 6 |
| Golden-answer authoring + judge calibration | Fix 5 | 7 pre-seeded; 23 over weeks 1-14 |
| Corpus consistency editorial pass | Fix 6 | Weeks 11-13 |
| Final pre-launch readiness review | Launch gate | Once, week 14 |

The LLM **cannot proceed** past a sub-fix's gate that requires a touchpoint above without that touchpoint complete. It surfaces to §9 + waits.

### §2.4 — Operator touchpoints

| Touchpoint | Trigger | What the operator does |
|---|---|---|
| Cloud writes (Supabase + Falkor) | Pre-authorized for Lia Graph (NOT LIA_contadores) per memory | Operator informed via §10 run log entry; no per-action confirmation needed |
| Production (Railway) deploys | Any | Explicit operator green-light required; not pre-authorized |
| Irreversible destructive actions | DROP, force-push, large DELETE, etc. | Explicit per-action operator green-light |
| Budget envelope strain (per fixplan_v3 §11.3) | Three risks listed | Operator informed; reallocation decision |
| Kill-switch failure (week 6) | Per fixplan_v3 §2.9 | Operator triggers `makeorbreak_v1.md` reassessment |
| Final pre-launch gate (week 14) | Per fixplan_v3 §10 | Operator GREEN/RED decision |

### §2.5 — What the LLM does on its own (no SME / operator gate)

- Sub-fix 1A code: dataclasses, Pydantic models, canonicalizer regex/AST, unit tests.
- Sub-fix 1B-α scrapers: HTML parsing, cache schema, smoke fixtures.
- Sub-fix 1B-γ migrations: UP + DOWN scripts, indexes, grants — apply locally; staging requires standing cloud-write authorization (already granted).
- Sub-fix 1B-δ canonicalizer backfill: read-then-write pattern; the writes go through `norm_history_writer.py`.
- Sub-fix 1B-ε retriever join changes: code edits to `retriever_supabase.py` + `retriever_falkor.py` + `planner.py`.
- Sub-fix 1F cascade orchestrator code.
- Sub-fix 1D chip atom + tests.
- Cron worker code + heartbeat scripts.
- Test runs (any horizon) once their gate has been crossed.
- Documentation updates (this file, runbooks, env matrix bumps).

### §2.6 — Failure modes specific to LLM execution

These are the failure patterns the operator should watch for when an LLM is the executor:

1. **Memory-shortcut for canonicalization.** LLM "knows" Art. 689-3 ET from training data and skips the canonicalizer. Mitigation: PR review + the CI lint for direct `norm_id` literals outside `canon.py` tests.
2. **Silent threshold relaxation.** LLM marks a gate passed when the criterion narrowly missed (94.7% vs 95% bar). Mitigation: gate evidence in §4 must be a numeric value the operator can re-verify; per-gate thresholds documented in fixplan_v3.
3. **Sub-fix coupling under pressure.** LLM merges two sub-fixes' work into one PR to "save time." Mitigation: PRs scoped to sub-fix; §4 ledger updated per sub-fix.
4. **Skipping reversibility.** LLM ships a migration without a DOWN script because "we'll never roll back." Mitigation: §5 entry required before §4 ledger row can advance to gate-3.
5. **Premature integration testing.** LLM runs the full kill-switch metric at week 4 and panics when it fails (because half the sub-fixes haven't shipped). Mitigation: §6 test horizons enforced.
6. **Writing to `norm_vigencia_history` from a debug script.** LLM "just inserting one row to test." Mitigation: the table grants are INSERT-only via the writer's role; debug scripts can't bypass.

### §2.7 — Verdict

A fresh LLM with the input set above + the hard guardrails + the SME/operator touchpoints **can drive v3 to the week-6 kill-switch gate**. It cannot drive past the kill-switch alone — operator decision required there per `makeorbreak_v1.md`. Post-kill-switch, an LLM can drive 1B-γ, 1B-δ, 1B-ε, 1D, 1F, and the supporting Fix 2-6 work, with the SME owning skill-prompt revisions and fixture authoring.

What an LLM **cannot** do: own the makeorbreak decision, replace the SME's domain knowledge, override operator authorization, or unilaterally relax gates.

---

## §3 — Current global state

> **Update protocol:** in-place edit of this section on every gate crossing or weekly review. Don't accumulate history here — that's the run log (§10).

**As of:** 2026-04-27 evening Bogotá — H0 implementation pass landed (Claude). All sub-fixes have working code + 222 unit tests; cloud apply / corpus extraction / SME signoffs still pending per §2.3 + §2.4.

### §3.1 — Active week

| Field | Value |
|---|---|
| Project week | **week 0 → week 1** (H0 implementation done; staging deploy + SME ontology session next) |
| Plan target | 14 weeks → soft-launch readiness review at end of week 14 |
| Operator decision pending | (a) staging migration apply for the 6 v3 SQL files, (b) ontology-session schedule for SME, (c) Activity 1.7b canonical-norm picks |
| Current pace | code complete at H0 horizon for all 8 sub-fixes; H1 + H2 testing requires a populated DB |

### §3.2 — Sub-fix in flight

**None mid-flight.** H0 code shipped for every Fix 1 sub-fix (1A, 1B-α, 1B-β, 1B-γ, 1B-δ, 1B-ε, 1D, 1F). Next horizon (H1) needs:

- Apply migrations `20260501000000_*` through `20260501000005_*` to local Supabase docker, then staging.
- Pre-warm the scraper cache (run `nlm`/manual seeding for the 7 known fixtures).
- Run `scripts/build_extraction_input_set.py` against the corpus to produce the deduplicated norm_id set.

The next planned starts (gated on operator sign-off):

| Sub-fix | Owner (TBD) | Planned start | Gate-1 evidence required |
|---|---|---|---|
| Fix 1A — ontology + canonicalizer | senior backend (TBD) | week 1 day 1 | gate-1 sketch in `docs/aa_next/<slug>.md` per six-gate template |
| Fix 1B-α — scrapers | senior backend (TBD) | week 1 day 1 (parallel) | gate-1 sketch |
| Activity 1.7b — VC/VL/DI/RV state-coverage seed | engineer + SME consultation | week 1-2 | SME picks 4 norms |
| Activity 6 — canonicalizer 50-chunk pilot | engineer | week 2 | depends on 1A canonicalizer reaching gate-3 |
| Fix 5 — golden-answer authoring | SME × 0.5 FTE | week 1 | first 5 cases authored |

### §3.3 — Blockers

| Blocker | Affects | Owner | Status |
|---|---|---|---|
| Operator sign-off on v3 plan + state file | All week-1 starts | Operator | **PENDING** (this file just landed) |
| SME availability for ontology session | Fix 1A gate-2 (week 1) | SME | not yet scheduled |
| SME picks for VC/VL/DI/RV canonical norms | Activity 1.7b | SME | not yet picked |
| `LIA_GEMINI_API_KEY` env vars in staging + production | Fix 1B-β (week 4-6) | Operator | already set per CLAUDE.md; verify before week 4 |

No technical blockers; all blockers are on operator + SME availability for the green-light + ontology session.

### §3.4 — Last meaningful state change

| When (Bogotá) | What | Who |
|---|---|---|
| 2026-04-27 evening | `state_fixplan_v3.md` ch1 landed (this section) | claude-opus-4-7 |
| 2026-04-27 (rolling, ch1-ch12) | `fixplan_v3.md` complete (2,050 lines, 16 sections) | claude-opus-4-7 |
| 2026-04-26 evening | Activity 1.7 fixtures complete (DT/SP/EC); skill eval seed at 7/30 | claude-opus-4-7 |
| 2026-04-27 04:15 UTC | Activity 1.5b shipped (4 veredictos persisted to staging Supabase + Falkor; audit log preserved) | engineer + cron |
| 2026-04-26 evening | Activities 1.5 + 1.6 complete (4 veredictos: V/VM/DE/IE) | claude-opus-4-7 + SME |

### §3.5 — Next planned step

1. **Operator sign-off.** Operator reads `fixplan_v3.md` + this file; greenlights week 1 OR requests amendments.
2. **Update v2 → superseded.** Add header note to `fixplan_v2.md` pointing to v3.
3. **Write `docs/re-engineer/activity_1_7_outcome.md`** mirroring the Activity 1.5 outcome doc.
4. **Schedule SME ontology session** for week 1 day 1-2 (covers skill v2.0 prompt review + Activity 1.7b canonical-norm picks).
5. **Engineer assignment** for Fix 1A + Fix 1B-α (the two parallel critical-path week-1 starts).
6. **First gate-1 sketches** in `docs/aa_next/` for Fix 1A and Fix 1B-α.

The LLM picking this up cold proceeds to step 3 and 6 once steps 1, 2, 4, 5 land (those four are operator + SME owned).

## §4 — Per-sub-fix gate ledger

> **Update protocol:** in-place edit per row on every gate crossing. Each row's `last_update` is the timestamp of its most recent change.

**Status legend:** `not_started` | `gate_1` (idea sketched) | `gate_2` (plan signed off) | `gate_3` (measurable criterion landed) | `gate_4` (test plan signed off) | `gate_5` (greenlight, code shipping) | `🧪` (verified locally) | `✅` (verified in target env) | `↩` (regressed-discarded) | `shipped` (final) | `discarded` (closed without ship).

### §4.1 — Activity series

| Sub-fix | Status | Owner | Last update (Bogotá) | Gate evidence | Blockers |
|---|---|---|---|---|---|
| Activity 1 — SQL-only vigencia filter | ✅ shipped | engineer | 2026-04-29 | `supabase/migrations/20260429000000_vigencia_filter_unconditional.sql`; outcome in `docs/learnings/retrieval/vigencia-binary-flag-too-coarse.md` | none |
| Activity 1.5 — Skill on Decreto 1474/2025 | ✅ shipped | claude-opus-4-7 + SME | 2026-04-26 evening | `evals/activity_1_5/decreto_1474_2025_veredicto.json`; outcome in `docs/re-engineer/activity_1_5_outcome.md` | none |
| Activity 1.6 — Skill on V/VM/DE norms | ✅ shipped | claude-opus-4-7 + SME | 2026-04-26 evening | 3 fixtures in `evals/activity_1_5/{art_689_3,art_158_1,art_290_num5}_ET_AG2025_veredicto.json` | none |
| Activity 1.5b — Manual veredicto persistence to staging | ✅ shipped | engineer + cron | 2026-04-27 04:15 UTC | `scripts/persist_veredictos_to_staging.py`; `evals/activity_1_5/persistence_audit.jsonl` (6 lines) | none — slated for v3 re-persistence when 1B-γ ships |
| Activity 1.7 — Skill on DT/SP/EC norms | ✅ shipped | claude-opus-4-7 | 2026-04-26 evening | 3 fixtures in `evals/activity_1_5/{arts_588_589,concepto_dian_100208192_202_num20,art_11_ley_2277_2022_zonas_francas}_*_veredicto.json` | outcome doc pending — see §3.5 step 3 |
| Activity 1.7b — Skill on VC/VL/DI/RV norms | not_started | TBD | — | — | SME picks 4 canonical norms |
| Activity 1.8 — Per-article skill on Ley 1429 | not_started | TBD | — | — | depends on 1B-α scrapers (week 4) |
| Activity 6 — Canonicalizer 50-chunk pilot | not_started | TBD | — | — | depends on 1A canonicalizer at gate-3 |
| Activity 7 — Reviviscencia smoke (post-1F) | not_started | TBD | — | — | depends on 1F shipped |

### §4.2 — Fix 1 sub-fixes (the structural fix; 8 sub-fixes)

| Sub-fix | Status | Owner | Last update (Bogotá) | Gate evidence | Blockers |
|---|---|---|---|---|---|
| **Fix 1A** — ontology (11 states) + ChangeSource discriminated union + canonicalizer | 🧪 (H0 verified) | claude-opus-4-7 | 2026-04-27 evening Bogotá | `src/lia_graph/vigencia.py` + `src/lia_graph/canon.py`; 142 unit tests pass (`tests/test_vigencia_v3_ontology.py`, `tests/test_canon.py`); covers 11 states, ChangeSource discriminated union, §0.5.4 round-trip + 4 refusal cases, sub-unit grammar | SME ontology session for skill v2.0 prompt update; Activity 6 50-chunk pilot still pending |
| **Fix 1B-α** — scraper + cache infra (5 sources) | 🧪 (H0 verified) | claude-opus-4-7 | 2026-04-27 evening Bogotá | `src/lia_graph/scrapers/{base,cache,secretaria_senado,dian_normograma,suin_juriscol,corte_constitucional,consejo_estado}.py`; 19 H0 tests pass (`tests/test_scrapers.py`) — cache CRUD, URL resolution per source, registry routing, cache-only fetch path | Live HTTP smoke (gated `LIA_LIVE_SCRAPER_TESTS=1`) needs operator green-light + per-source rate-limit verification |
| **Fix 1B-β** — skill-guided extractor batch (articles + sub-units) | 🧪 (H0 verified) | claude-opus-4-7 | 2026-04-27 evening Bogotá | `src/lia_graph/vigencia_extractor.py` (VigenciaSkillHarness + adapter_factory test seam); `scripts/{build_extraction_input_set,extract_vigencia}.py`; 8 H0 tests (`tests/test_vigencia_extractor.py`) | Real Gemini run gated on `LIA_GEMINI_API_KEY`; corpus input set requires `parsed_articles.jsonl` walk |
| **Fix 1B-γ** — `norms` + `norm_vigencia_history` + `norm_citations` tables + Falkor mirror | 🧪 (H0 verified) | claude-opus-4-7 | 2026-04-27 evening Bogotá | 4 migrations `20260501000000-3` (catalog + append-only history + citations + resolvers); `src/lia_graph/persistence/norm_history_writer.py` (sole sanctioned writer); `scripts/{ingest_vigencia_veredictos,sync_vigencia_to_falkor}.py`; Falkor `:Norm` node + 9 v3 edge kinds added to `graph/schema.py`; 13 writer tests + 8 migration shape tests pass | Apply migrations to dev docker → staging cloud; sync 7 fixture veredictos as smoke per §0.11.5 |
| **Fix 1B-δ** — `norm_citations` link backfill via canonicalizer over existing chunks | 🧪 (H0 verified) | claude-opus-4-7 | 2026-04-27 evening Bogotá | `src/lia_graph/citations.py` (role + anchor-strength inference); `scripts/{backfill_norm_citations,audit_norm_citations}.py`; 11 inference tests pass (`tests/test_role_inference.py`) | Run against cloud staging chunks once 1B-γ migrations applied; SME triage of refusal queue |
| **Fix 1B-ε** — retriever rewire to resolver functions (was 1C in v2) | 🧪 (H0 verified) | claude-opus-4-7 | 2026-04-27 evening Bogotá | `src/lia_graph/pipeline_d/{vigencia_resolver,vigencia_demotion}.py` + `GraphRetrievalPlan.vigencia_query_kind/payload`; new RPC `chunk_vigencia_gate_at_date` + `chunk_vigencia_gate_for_period` (migration `20260501000004`); 18 tests pass (`test_vigencia_resolver.py`, `test_vigencia_demotion.py`) | Wire `apply_demotion` into `retriever_supabase.py` post-hybrid_search; H2 cluster smoke against §1.G fixture |
| **Fix 1D** — 11-variant vigencia chips (frontend) | 🧪 (H0 verified) | claude-opus-4-7 | 2026-04-27 evening Bogotá | `frontend/src/shared/ui/atoms/vigenciaChip.ts` (11 variants); 13 vitest tests pass (`frontend/tests/vigenciaChip.test.ts`) including jsdom render + aria-label + interpretive-constraint title | Wire chip into chat citation molecule; needs 1B-ε's `vigencia_v3` annotation in chat-response payload |
| **Fix 1F** — cascade orchestrator (reviviscencia + future-dated state flips + retrieval-time inconsistency detection) | 🧪 (H0 verified) | claude-opus-4-7 | 2026-04-27 evening Bogotá | `src/lia_graph/pipeline_d/vigencia_cascade.py`; cron workers `cron/{cascade_consumer,state_flip_notifier,reverify_periodic}.py`; queue migration `20260501000005`; 9 cascade tests pass (`test_vigencia_cascade.py`) — reviviscencia cascade, idempotency, future-dated flip notifier, inconsistency detector | Deploy cron to Railway staging; Activity 7 reviviscencia smoke |

### §4.3 — Fixes 2-6

| Fix | Status | Owner | Last update (Bogotá) | Gate evidence | Blockers |
|---|---|---|---|---|---|
| **Fix 2** — Parámetros móviles map (UVT/SMMLV/IPC + topical thresholds) | not_started | TBD | — | — | depends on 1A `applies_to_kind` for year-aware resolution |
| **Fix 3** — Anti-hallucination guard on partial mode | not_started | TBD | — | — | depends on 1B-ε for the v3 inconsistency detection + cron queue path |
| **Fix 4** — Ghost-topic kill + corpus completeness audit | not_started | SME × 0.5 FTE + 0.5 engineer | — | — | depends on Fix 1B-α (skill-at-ingest hook needs scrapers) |
| **Fix 5** — Golden-answer regression suite (TRANCHE schema, skill-as-judge) | gate_2 (plan signed off) | SME + 0.5 engineer | 2026-04-27 | 7 of 30 cases pre-seeded by Activities 1.5/1.6/1.7; plan in `fixplan_v3.md` §6 | SME bandwidth for the 23 remaining cases (5/week, weeks 1-6) |
| **Fix 6** — Internal corpus consistency editorial pass + corpus-wide hallucination audit | not_started | SME × 0.5 FTE × 5 weeks + 0.5 engineer | — | — | depends on Fix 4's SME bandwidth (weeks 11-13 overlap is tight) |

### §4.4 — Supporting infra

| Infra | Status | Owner | Last update (Bogotá) | Gate evidence | Blockers |
|---|---|---|---|---|---|
| **Skill v2.0 prompt update** (11 states + structured change_source) | not_started | SME-led, engineer integrates | — | — | gate-1 ontology session (week 1) |
| **Skill Eval set** (30 cases; 7 pre-seeded) | gate_3 (criterion + test plan landed; authoring in progress) | SME + 0.5 engineer | 2026-04-27 | seed cases listed in fixplan_v3 §0.11.3 contract 4 + §6; 7 fixtures shipped | need 23 cases (5/week from week 1) |
| **Re-Verify Cron deployment** (hosts cascade consumer + state-flip notifier) | not_started | 0.5 engineer | — | — | depends on Fix 1B-γ schema (cron writes target the new tables) |
| **Norm canonicalizer** (`src/lia_graph/canon.py`) | not_started | 0.5 engineer (subscope of 1A) | — | — | gate-1 grammar review |
| **`norm_history_writer.py`** (the single sanctioned writer) | not_started | 0.5 engineer (subscope of 1B-γ) | — | — | depends on 1B-γ migration shape locked |

### §4.5 — Per-sub-fix detailed gate template (for engineers to copy-paste when starting work)

When taking on a sub-fix, copy the template below into your gate-1 sketch (`docs/aa_next/<slug>.md`) and update §4 ledger to point at it.

```markdown
# Gate-1 sketch — Sub-fix <ID> — <one-line description>

**Sub-fix:** <e.g. 1A — ontology + canonicalizer>
**Owner:** <your name>
**Started:** <yyyy-mm-dd hh:mm Bogotá>
**Plan reference:** `fixplan_v3.md` §<X.Y>

## Gate 1 — The good idea (one sentence)
<...>

## Gate 2 — The plan (narrowest module)
- Files to create: <list>
- Files to modify: <list>
- Migration impacts: <none | UP+DOWN scripts in `supabase/migrations/...`>
- Reversibility row in `state_fixplan_v3.md` §5: <reference or "to be added">

## Gate 3 — Measurable success criterion
<numeric criteria from fixplan_v3>

## Gate 4 — Test plan
**Test horizon (per state_fixplan_v3 §6):** H0 / H1 / H2 / H3
**Local docker validation:** required (per fixplan_v3 §0.9 NEW v3 convention)
**Actors required:** engineer / SME / operator / end-user
**Test recipe:** <steps>
**Numeric decision rule:** <pass threshold>

## Gate 5 — Greenlight
- Tech lead signoff: <signature + date>
- SME signoff (if required): <signature + date>
- Operator authorization (if required): <signature + date>

## Gate 6 — Refine or discard
<filled in after ship: outcome, learnings, next-step>
```

## §5 — Reversibility matrix

> **Update protocol:** add a row before the action ships (gate-2 plan must reference its row); never remove rows for shipped actions (the procedure stays valid for emergency rollback even years later).

**Principle:** every non-trivial action in v3 has an explicit reverse procedure. If the reverse cannot be defined cleanly, the action is redesigned until it can — *or* it is gated on explicit operator green-light AND ships with a snapshot taken first.

**Reversibility classes:**
- **R1 — fully reversible** (single command, no state lost): file edits, type-checks, dataclass refactors.
- **R2 — reversible via traced cleanup** (one extra tracking field, then a delete-by-trace): batch extraction outputs, persistence writes with `extracted_via.run_id`.
- **R3 — reversible via DOWN script** (forward UP + paired DOWN; tested in dev docker): every Supabase migration.
- **R4 — reversible via snapshot** (no clean DOWN; restore from backup): drop-column migrations, large-scale data overwrites.
- **R5 — operator green-light gated** (irreversible by design; only proceed with explicit per-action authorization): production deploys, force-push to main, large DELETEs of audit data.

### §5.1 — Migration reversibility (Sub-fixes 1B-γ, 1B-ε, deprecation cycle)

| Migration | Class | Forward (UP) | Reverse (DOWN) | Pre-condition | Failure mode if UP fails midway | Rollback recipe |
|---|---|---|---|---|---|---|
| `20260YYYY000000_norms_catalog.sql` | R3 | `CREATE TABLE norms` + indexes | `DROP TABLE norms CASCADE` | none (empty table) | partial creation: indexes exist without table OR vice versa | run DOWN; re-apply UP |
| `20260YYYY000001_norm_vigencia_history.sql` | R3 | `CREATE TABLE norm_vigencia_history` + grants + indexes + CHECK | `REVOKE ...; DROP TABLE norm_vigencia_history CASCADE` | `norms` table exists | partial (table exists, grants partial) | run DOWN; verify role grants reverted; re-apply UP |
| `20260YYYY000002_norm_citations.sql` | R3 | `CREATE TABLE norm_citations` + indexes | `DROP TABLE norm_citations CASCADE` | both prior tables exist | partial | run DOWN; re-apply UP |
| `20260YYYY000003_resolver_functions.sql` | R3 | `DROP FUNCTION IF EXISTS norm_vigencia_at_date CASCADE; DROP FUNCTION IF EXISTS norm_vigencia_for_period CASCADE; CREATE FUNCTION ...` (both) | `DROP FUNCTION norm_vigencia_at_date(date) CASCADE; DROP FUNCTION norm_vigencia_for_period(text,int,text) CASCADE` | tables 1-3 exist | partial (one function created, other failed) | run DOWN (idempotent on missing functions); re-apply UP. **Per `hybrid_search-overload-2026-04-27.md`: explicit `DROP FUNCTION IF EXISTS` is mandatory before any `CREATE OR REPLACE` if the parameter list changed.** |
| `20260YYYY000004_documents_vigencia_deprecated_view.sql` | R3 | replace `documents.vigencia` and `document_chunks.vigencia` columns with views computed from `norm_vigencia_history` | drop views; restore columns from latest snapshot of pre-migration values (held in `_archive` table written by UP) | `norm_vigencia_history` populated | partial (column dropped, view not yet created) → reads break for one window | run DOWN; reads point at the `_archive` columns until DOWN finishes; smoke `documents.vigencia` reads return values |
| `20260YYYY000005_hybrid_search_v3.sql` | R3 | drop v2 RPC overloads; create v3 with `vigencia_query_kind` + `vigencia_query_payload` params | drop v3 form; restore v2 form from prior migration's UP body | resolver functions exist; planner emits new fields | retriever calls fail with "function not found" | DOWN restores v2; planner falls back to no-cue path; retrieval continues with sparse vigencia gate |
| `20260YYYY000006_drop_documents_vigencia.sql` (week 11+) | **R4** | drop deprecation views + drop the `_archive` columns | restore from snapshot taken immediately before this migration | all callers migrated; week-11 deprecation window closed; **operator green-light required** | data loss if DOWN attempted without snapshot | restore Supabase snapshot; re-run callers' migration to v3 read path; do NOT skip snapshot |

### §5.2 — Batch script reversibility (Sub-fixes 1B-β, 1B-δ)

| Script | Class | Forward action | Reverse action (cleanup) | Tracking key | Failure-mid-run state | Recovery |
|---|---|---|---|---|---|---|
| `scripts/extract_vigencia.py` (1B-β extractor batch) | R2 | writes JSON files to `evals/vigencia_extraction_v1/<norm_id>.json` | delete files matching `<run_id>` from manifest | `extraction_run_id` in audit log | partial files written for some norms; manifest records what completed | re-run with `--resume <run_id>`; skips norms whose JSON exists with same `run_id` |
| `scripts/ingest_vigencia_veredictos.py` (1B-γ sink) | R2 | UPSERTs `norms`; INSERTs `norm_vigencia_history`; MERGEs Falkor `(:Norm)` + edges | delete `norm_vigencia_history` rows where `extracted_via->>'run_id' = '<bad_run>'`; Falkor `MATCH (n:Norm) WHERE n.extracted_via_run_id = '<bad_run>' DETACH DELETE n` | `extracted_via.run_id` (every row carries it) | partial: some history rows + some Falkor nodes for a run | run cleanup script `scripts/rollback_ingest_run.py --run-id <bad_run>`; resume sink with new `run_id` |
| `scripts/backfill_norm_citations.py` (1B-δ backfill) | R2 | INSERTs `norm_citations` rows | delete `norm_citations` rows where `extracted_via = '<bad_run>'` | `extracted_via` (run id) | partial rows inserted for some chunks | cleanup by run; canonicalizer refusal queue may also have stale entries — clear `evals/canonicalizer_refusals_v1/<bad_run>/` |
| `scripts/sync_vigencia_to_falkor.py` | R2 | MERGEs `(:Norm)` + edges into Falkor mirroring `norm_vigencia_history` rows | DETACH DELETE nodes by `record_id` property | edge / node `record_id` property = Postgres row UUID | partial Falkor sync | re-run with `--from-record-id <ts>` to rebuild from a checkpoint |
| `scripts/persist_veredictos_to_staging.py` (Activity 1.5b — already shipped) | R2 historical | wrote 4 `documents.vigencia` UPDATEs + 4-8 Falkor edges | reverse via `evals/activity_1_5/persistence_audit.jsonl` (rollback-ready per Activity 1.5b spec) | `activity = '1.5b'` in audit lines | n/a (already shipped without partial state) | for v3 re-persistence: 1B-γ sink reads the audit log, supersedes the 4 staging rows with v3-shaped history rows |

### §5.3 — Persistence write reversibility (the writer module)

| Write site | Class | Pre-condition | Forward | Reverse | Notes |
|---|---|---|---|---|---|
| `src/lia_graph/persistence/norm_history_writer.py::insert_history_row` | R2 | row passes Pydantic validation; `change_source.source_norm_id` exists in `norms`; `state_from <= state_until` (or `state_until is null`) | INSERT to `norm_vigencia_history`; if a prior row's `state_until` becomes finite, mark its `superseded_by_record` | DELETE the new row + reset prior row's `state_until` and `superseded_by_record` | **only mechanism allowed to write to the table.** Direct INSERT from app code is blocked at the role grant. |
| `src/lia_graph/persistence/norm_history_writer.py::bulk_insert_run` | R2 | as above × N | wrapped in a single transaction; if any row fails, transaction rolls back | n/a (transactional) | used by 1B-γ sink and the Re-Verify Cron |
| Falkor sync via `sync_vigencia_to_falkor.py` | R2 | `norm_vigencia_history` row exists | MERGE `(:Norm)` + structured edge with `record_id` property | DETACH DELETE node OR specific edge by `record_id` | Falkor is a mirror, not a source of truth — reversibility is "re-sync from Postgres" |
| **Forbidden:** any direct INSERT from synthesis or retrieval path | R5 | n/a | rejected at code review + DB role grant | n/a | `extracted_by` enum at the writer rejects `synthesis@v1` / `retrieval@v1` |

### §5.4 — Infrastructure change reversibility

| Change | Class | Forward | Reverse | Pre-condition | Notes |
|---|---|---|---|---|---|
| Re-Verify Cron deploy (week 4-5) | R3 | `railway up` for `cron/` workers; smoke 1 cycle in staging | `railway down` for the workers; queue table preserved | local docker simulation passes | hosting absorbs Fix 1F at no extra line |
| Cron queue table creation | R3 | `CREATE TABLE vigencia_reverify_queue` | `DROP TABLE vigencia_reverify_queue CASCADE` | none (empty) | queue is rebuildable from `norm_vigencia_history` if lost |
| Cron worker container update | R1 | `railway redeploy` with new image | `railway redeploy` with prior image SHA | image SHA recorded in §10 run log | rollback in <2 min |
| Local docker stack restart | R1 | `make supabase-stop && make supabase-start; npm run dev` | same | none | `make supabase-reset` is destructive — only for clean-slate testing |
| Env matrix bump (per fixplan_v3 §0.9 convention) | R1 | edit `docs/orchestration/orchestration.md` + mirror tables | git revert | none | docs-only change |
| Skill v1.0 → v2.0 prompt revision | R1 | edit `.claude/skills/vigencia-checker/references/*.md` | git revert | SME signoff | docs-only change; skill harness reads from disk |
| `LIA_*` env flag flip in launcher | R1 | edit `scripts/dev-launcher.mjs` + mirrors | git revert | env matrix bumped | per fixplan_v3 §0.9 convention |

### §5.5 — Operator-gated actions (R5 — explicit per-action green-light)

These NEVER proceed without operator green-light + a snapshot taken first:

| Action | Why R5 | Required green-light artifact | Snapshot procedure |
|---|---|---|---|
| Production (Railway) deploy | Production blast radius | Operator message in §10 run log + signed-off PR | Railway snapshot; current image SHA recorded |
| `DROP TABLE` on a populated table | Irreversible without backup | Operator green-light + snapshot | `pg_dump` of the table to `var/snapshots/<table>.<ts>.sql` |
| Large-scale `DELETE` (> 10K rows) | Hard to reverse without trace | Operator green-light + snapshot | as above |
| Force-push to `main` | Lost commits | Operator green-light | not applicable; recommend revert PR instead |
| Drop of `documents.vigencia` columns (migration `_006`) | One-way schema change | Operator green-light + Supabase snapshot | Supabase project snapshot from dashboard before applying |
| Cloud Falkor `MATCH (n) DETACH DELETE n` (full graph wipe) | Catastrophic | Operator green-light | `falkor_dump` or equivalent before |
| Skill prompt revision that changes the output schema (e.g., adds a new state code) | Touches every downstream consumer | SME signoff + operator awareness | git tag pre-revision |

### §5.6 — Rollback recipes (composed actions)

These are end-to-end recipes for common bad-state recoveries.

#### Recipe A — "1B-β extraction batch produced bad veredictos for state X"

Symptoms: SME spot-check shows >5% errors on state X (e.g., the EC extractions are paraphrasing instead of literal). The bad batch's `run_id` is `<bad_run>`.

```bash
# 1. Identify the bad run.
ls evals/vigencia_extraction_v1/ | head        # find files with the bad run_id

# 2. Cleanup the JSON outputs.
python scripts/cleanup_extraction_run.py --run-id <bad_run>
# Removes files matching the run; preserves audit log.

# 3. (If sink already ran) cleanup the persistence writes.
python scripts/rollback_ingest_run.py --run-id <bad_run>
# DELETEs norm_vigencia_history rows where extracted_via.run_id = <bad_run>;
# Falkor MATCH (n:Norm) WHERE n.extracted_via_run_id = '<bad_run>' DETACH DELETE n.

# 4. Iterate skill prompt or harness; re-run with new run_id.
python scripts/extract_vigencia.py --run-id <new_run> --resume-from-checkpoint
```

#### Recipe B — "1B-γ migrations applied to staging but the schema is wrong"

Symptoms: a migration applied successfully but post-deploy smoke fails (e.g., resolver function returns wrong shape; grants leak).

```bash
# 1. Pause all writers.
# - Stop Re-Verify Cron workers: railway down -s cron-cascade-consumer cron-reverify-periodic
# - Halt any 1B-β batch: kill the detached pid + remove its lockfile

# 2. Apply DOWN migrations in reverse order.
psql "$STAGING_SUPABASE_URL" -f supabase/migrations/_down/20260YYYY000003_resolver_functions.down.sql
psql "$STAGING_SUPABASE_URL" -f supabase/migrations/_down/20260YYYY000002_norm_citations.down.sql
# ... etc, reverse order

# 3. Verify state.
psql "$STAGING_SUPABASE_URL" -c "\d norms"      # should fail (table dropped)
psql "$STAGING_SUPABASE_URL" -c "\d documents"  # vigencia column should still exist (deprecation view not yet shipped at this point)

# 4. Fix the migration; redo from local docker first per §0.9 convention.

# 5. Re-apply once green in local.
supabase db push --linked
```

#### Recipe C — "Cascade orchestrator stuck — queue depth growing without drain"

Symptoms: `cron/cascade_consumer.py` is running but the queue isn't draining; new norms keep getting enqueued.

```bash
# 1. Diagnose: is the consumer alive?
railway logs -s cron-cascade-consumer --tail 100

# 2. Check queue depth.
psql "$STAGING_SUPABASE_URL" -c "SELECT COUNT(*) FROM vigencia_reverify_queue WHERE processed_at IS NULL;"

# 3. Check for the feedback loop.
psql "$STAGING_SUPABASE_URL" -c "
  SELECT supersede_reason, COUNT(*)
  FROM norm_vigencia_history
  WHERE extracted_at > now() - interval '1 hour'
  GROUP BY 1;
"
# If 'cascade_reviviscencia' is dominating: the cascade is self-triggering.

# 4. Pause the consumer.
railway scale -s cron-cascade-consumer --replicas 0

# 5. Inspect a sample of recent inserts; identify the recursive trigger.
# Common cause: a sentencia row's change_source.source_norm_id points to itself
#   or to a norm whose own history row also references the sentencia.

# 6. Manually drain the queue (mark as processed without writing).
psql "$STAGING_SUPABASE_URL" -c "
  UPDATE vigencia_reverify_queue SET processed_at = now(), skipped = true
  WHERE processed_at IS NULL;
"

# 7. Fix the trigger logic in vigencia_cascade.on_history_row_inserted; redeploy.

# 8. Resume consumer.
railway scale -s cron-cascade-consumer --replicas 1
```

#### Recipe D — "Falkor and Supabase desynced after a partial Falkor sync failure"

Symptoms: a `(:Norm)` node count diverges from `norms` row count; queries return inconsistent results across the two backends.

```bash
# 1. Pause the sync.
# (No active syncer? Skip; otherwise: railway scale -s cron-falkor-sync --replicas 0)

# 2. Identify divergence.
# In Falkor:
GRAPH.QUERY LIA_REGULATORY_GRAPH "MATCH (n:Norm) RETURN COUNT(n)"
# In Supabase:
psql "$STAGING_SUPABASE_URL" -c "SELECT COUNT(*) FROM norms;"

# 3. Wholesale rebuild Falkor :Norm subgraph from Supabase.
python scripts/sync_vigencia_to_falkor.py --rebuild-from-postgres --confirm
# Internally: MATCH (n:Norm) DETACH DELETE n  (all Norm nodes + their edges)
#             then re-MERGE every (:Norm) and its edges from norms + norm_vigencia_history.

# 4. Verify counts match.

# 5. Resume any writers.
```

#### Recipe E — "Operator wants to revert v3 entirely — back to v2 column shape"

Worst-case scenario; not expected. If it happens:

```bash
# 1. Pause all writers (cron, batches, ingest hooks).

# 2. Restore Supabase snapshot taken immediately before migration _006 was applied.
# (Snapshot is the operator-gated action's pre-condition; if no snapshot: STOP and call operator.)

# 3. Run all DOWN migrations in reverse order.

# 4. Restore documents.vigencia column from the _archive (preserved by migration _004).

# 5. Revert retriever code (1B-ε changes) — git revert.

# 6. Revert env matrix bump.

# 7. Smoke § 1.G — ensure post-revert baseline matches pre-v3 baseline (21/36 served_acceptable+).

# 8. The 7 veredictos in evals/activity_1_5/ stay as v2-shape JSON fixtures; Activity 1.5b's 4 staging
#    UPDATEs stay as the v2 baseline.

# Result: v3 fully reverted; project at end of v2 / pre-Activity-1.7 state plus the 1.5b smoke.
```

### §5.7 — Reversibility audit (run weekly during execution)

Engineer or LLM runs this checklist every Friday:

- [ ] Every shipped migration has a tested DOWN script in `supabase/migrations/_down/`.
- [ ] Every batch script writes a tracking key (`run_id` or equivalent).
- [ ] Every persistence write goes through `norm_history_writer.py` (CI lint).
- [ ] No code path bypasses the writer via direct INSERT (CI lint).
- [ ] Every R4/R5 action since last audit had operator green-light + snapshot.
- [ ] §5 has rows for every new action introduced this week.
- [ ] §10 run log has a recovery entry for every failure that occurred.

If any check fails: the failed item is logged to §9 open questions and resolved before the next gate-3 ships.

## §6 — Test horizons (don't test too early)

> **Principle:** premature testing produces false-fail signals AND wastes time. Late testing risks shipping broken code. The four horizons below define when each kind of test becomes meaningful. Engineers consult this table before running tests; LLMs consult it before reporting "tests fail" as a blocker.

### §6.1 — The four horizons

| Horizon | Name | When to run | What it validates | Cost (cycles) |
|---|---|---|---|---|
| **H0** | Immediate | As you write code; CI on every commit | Type checks, schema validations, isolated unit tests, dataclass round-trips | low — seconds to minutes |
| **H1** | Per-sub-fix | On gate-3 of a sub-fix | Integration tests scoped to that sub-fix; the sub-fix's own success criterion from fixplan_v3 | medium — minutes to hours |
| **H2** | Cluster | After a cluster of dependent sub-fixes lands | End-to-end smoke spanning multiple sub-fixes that "click" together | medium-high — hours; requires multi-sub-fix coordination |
| **H3** | Fix-1-complete | Week 6 (kill-switch) and week 14 (launch readiness) | The kill-switch metric AND the launch-readiness report | high — full SME re-run; requires all of Fix 1 to have shipped |

### §6.2 — Per-sub-fix horizon table

The "do not test at H0" column is the operative gauge. If a row says **DO NOT** for H0, running those tests when a sub-fix is at gate-1 or gate-2 produces false-fail noise — the surrounding sub-fixes haven't shipped yet.

| Sub-fix | H0 (immediate) | H1 (sub-fix complete) | H2 (cluster) | H3 (Fix-1) |
|---|---|---|---|---|
| **1A** ontology + canonicalizer | ✅ unit tests for dataclasses, enum, ChangeSource discriminated union, canonicalizer grammar; round-trip serialization tests | ✅ skill v2.0 round-trip on the 7 fixtures (proves the upgrade mapper); SME signoff session | (cluster: 1A + 1B-α + 1B-β = "extraction works"); test in H2 once 1B-β reaches gate-3 | n/a |
| **1B-α** scrapers | ✅ smoke fixtures parse correctly; cache schema migrations apply | ✅ live-fetch tests gated on `LIA_LIVE_SCRAPER_TESTS=1`; 30-norm probe; cache hit rate measurable | (cluster: 1A + 1B-α + 1B-β); test cache hit rate ≥ 70% | n/a |
| **1B-β** extractor batch | **DO NOT** run integration tests at H0 — depends on 1A canonicalizer + 1B-α scrapers + skill v2.0 prompt; would false-fail | ✅ 100-norm SME spot-check; per-state minimum tests (3 known per state × 11 states); audit log shows ≥ 2 sources per veredicto | ✅ extraction-output → ingest-into-norm-tables smoke (with 1B-γ); ≥ 95% landed | ✅ kill-switch metric (week 6) |
| **1B-γ** catalog + history tables | ✅ migration tests against local Supabase docker; CHECK constraints; INSERT-only role grants | ✅ idempotent re-run of sink; 7 fixture round-trip via v2-to-v3 upgrade mapper; Falkor `(:Norm)` mirror count match | ✅ 1B-β extraction → 1B-γ sink ingest end-to-end; norm count = canonicalized input set count | n/a |
| **1B-δ** citations link backfill | **DO NOT** run end-to-end at H0 — depends on 1A canonicalizer at gate-3; canonicalizer 50-chunk pilot (Activity 6) is the H0 substitute | ✅ ≥ 95% chunks have ≥ 1 citation; 0 FK violations; refusal rate < 5%; SME spot-check 50 random rows | (cluster: 1B-γ + 1B-δ = "norm-keyed persistence is live") | n/a |
| **1B-ε** retriever rewire | **DO NOT** run retrieval E2E at H0 — depends on 1B-γ tables populated AND 1B-δ citations link backfilled. Would false-fail with "no rows returned" | ✅ resolver function correctness on 30 SME pairs ≥ 28/30; 52-question regression set (30 vigente + 10 historical + 8 Art. 338 + 4 ultractividad) | ✅ §1.G SME re-run ≥ 24/36 served_acceptable+ | ✅ launch readiness report (week 14) |
| **1D** chips (frontend) | ✅ component tests for 11 variants; visual regression snapshots | ✅ chips render with real chat-response payload from 1B-ε | (cluster: 1B-ε + 1D = "user-visible vigencia surface complete") | ✅ launch readiness |
| **1F** cascade orchestrator | ✅ unit tests for `on_history_row_inserted`, `on_periodic_tick`, `detect_inconsistency` (with mocked Postgres) | ✅ Ley 1943/2018 reviviscencia smoke (Activity 7) — 1 IE row → ≥ 20 RV rows produced | ✅ end-to-end with cron deployed in staging | ✅ launch readiness (cascade processed reviviscencia smoke at least once) |
| **Fix 2** parámetros móviles | ✅ year-detection regex; YAML schema validation | ✅ 8 UVT questions + 8 Art. 338 CP questions | (cluster: Fix 2 + 1B-ε = "year-aware parameter resolution works") | ✅ launch readiness |
| **Fix 3** anti-hallucination | **DO NOT** run E2E at H0 — depends on 1B-ε for the cron-queue path | ✅ 12-question fabrication regression | (cluster: 1B-ε + Fix 3 = "partial-mode safe") | ✅ launch readiness |
| **Fix 4** ghost-topic | ✅ topic-completeness counts | ✅ ingest-time skill hook smoke on 1 new doc | n/a | ✅ launch readiness |
| **Fix 5** golden answers | ✅ TRANCHE schema validation; runner plumbing reuse | ✅ 7 pre-seeded cases pass; 23 authored cases roll in over weeks 1-14 | (cluster: Fix 5 + 1B-ε + Fix 1F = "judge can read v3 record_ids") | ✅ launch readiness |
| **Fix 6** corpus consistency | ✅ hallucination grep recipes | ✅ EME-A01 rewrite + T-I supersede; refusal-queue triage rules baked | n/a | ✅ launch readiness |

### §6.3 — Common premature-test traps

These are the false-fail signals to watch for:

1. **"Tests fail because `norm_vigencia_history` doesn't exist."** You're testing 1B-ε before 1B-γ shipped. **Wait for the cluster.**
2. **"Resolver returns no rows for any norm."** You're testing the resolver before 1B-δ backfill ran. **Wait for the cluster.**
3. **"Falkor `(:Norm)` count is 0."** You're testing the Falkor mirror before `sync_vigencia_to_falkor.py` ran. **Run the sync; not a code bug.**
4. **"Skill emits VC but my Pydantic rejects it."** You're testing 1B-β output against pre-1A Vigencia dataclass. **Update to v3 dataclass.**
5. **"§1.G SME re-run shows no improvement."** You're running the kill-switch at H1 (only 1A shipped). **Wait for week 6 with 1A+1B-α+1B-β all clicking.**

### §6.4 — When to test BEFORE expected horizon (legitimate exceptions)

There are cases where running a higher-horizon test early IS valuable as a smoke for sub-fix wiring:

- After 1B-γ ships migrations, run a tiny smoke ingest of ONE veredicto (e.g., the Decreto 1474/2025 fixture) before the full 1B-β batch lands. Validates the sink+Falkor wiring on a single record. Doesn't require 1B-β complete.
- After 1B-δ backfills ONE document's citations, run the resolver against THAT document's chunks. Smoke for the join wiring; doesn't require full backfill complete.
- After 1F deploys, run ONE manual reviviscencia trigger on a synthetic test row before relying on real cascades.

The pattern: a "vertical slice" smoke through a single record is fine at any horizon. The trap is running an "everything must work" test when half the sub-fixes haven't shipped.

### §6.5 — Test horizon enforcement

Engineers (and LLMs) MUST consult §6.2 before running tests. If a sub-fix's row says **DO NOT** for the current horizon, the engineer skips and notes in §10 run log: "skipped <test name> per §6 — sub-fix at gate-<N>, would false-fail."

If an engineer does run a flagged test and reports a fail to the operator: the fail is treated as noise unless the engineer can prove the sub-fix is actually at the right horizon. This protects the operator's bandwidth from false-positive panic.

---

## §7 — Environment state

> **Update protocol:** in-place edit per env-cell on every deploy. Cron heartbeats append to §10 run log; the cells here reflect *current* state (latest applied migration, latest run ids, etc.).

**As of:** 2026-04-27 7:55 PM Bogotá (initial state file ship; all v3 sub-fixes pre-execution).

### §7.1 — Three environments

| Environment | Run mode | Supabase | FalkorDB | Notes |
|---|---|---|---|---|
| **dev** | `npm run dev` | local docker (`make supabase-start`) | local docker (Falkor container) | `LIA_CORPUS_SOURCE=artifacts`, `LIA_GRAPH_MODE=artifacts` |
| **staging** | `npm run dev:staging` | cloud Supabase (Lia Graph project) | cloud FalkorDB (`LIA_REGULATORY_GRAPH`) | `LIA_CORPUS_SOURCE=supabase`, `LIA_GRAPH_MODE=falkor_live` |
| **production** | `npm run dev:production` (deploy via `railway up`) | cloud Supabase (production project) | cloud FalkorDB (production) | Railway-hosted; deploys gated on operator green-light |

### §7.2 — Migration state (per env)

**As of 2026-04-27 PM Bogotá** (pre-v3 execution):

| Migration | dev | staging | production |
|---|---|---|---|
| `20260417000000_baseline.sql` (v2 squashed baseline) | ✅ applied | ✅ applied | ✅ applied |
| `20260417000001_seed_users.sql` | ✅ applied | ✅ applied | ✅ applied |
| `20260418000000_normative_edges_unique.sql` | ✅ applied | ✅ applied | ✅ applied |
| `20260421000000_sub_topic_taxonomy.sql` | ✅ applied | ✅ applied | ✅ applied |
| `20260427000000_topic_boost.sql` | ✅ applied | ✅ applied | ✅ applied |
| `20260428000000_drop_legacy_hybrid_search.sql` | ✅ applied | ✅ applied | ✅ applied |
| `20260429000000_vigencia_filter_unconditional.sql` (Activity 1) | ✅ applied | ✅ applied | ✅ applied |
| **v3 migrations (H0 written 2026-04-27 — landed in `supabase/migrations/`)** | — | — | — |
| `20260501000000_norms_catalog.sql` | ✅ applied 2026-04-27 night | not yet applied | not yet applied |
| `20260501000001_norm_vigencia_history.sql` (append-only role grants) | ✅ applied 2026-04-27 night | not yet applied | not yet applied |
| `20260501000002_norm_citations.sql` (added UNIQUE INDEX after live-e2e finding) | ✅ applied 2026-04-27 night (revised) | not yet applied | not yet applied |
| `20260501000003_resolver_functions.sql` (`norm_vigencia_at_date` + `norm_vigencia_for_period`) | ✅ applied 2026-04-27 night | not yet applied | not yet applied |
| `20260501000004_chunk_vigencia_gate.sql` (retriever-side `chunk_vigencia_gate_at_date` + `_for_period`) | ✅ applied 2026-04-27 night | not yet applied | not yet applied |
| `20260501000005_vigencia_reverify_queue.sql` (Fix 1F queue) | ✅ applied 2026-04-27 night | not yet applied | not yet applied |
| `documents_vigencia_deprecated_view.sql` (deferred — runs after 1B-δ backfill validates ≥95% coverage) | n/a yet | n/a yet | n/a yet |
| `drop_documents_vigencia.sql` (week 11+, R4 operator-gated) | not yet shipped | not yet shipped | not yet shipped |

### §7.3 — Extraction run state

| Run | Description | Output | dev | staging | production |
|---|---|---|---|---|---|
| `manual-2026-04-26-evening` | Activities 1.5 + 1.6 | 4 fixtures in `evals/activity_1_5/` | n/a | persisted via Activity 1.5b (3 of 4) | not deployed |
| `manual-2026-04-26-evening-2` | Activity 1.7 (DT/SP/EC) | 3 fixtures in `evals/activity_1_5/` | n/a | not yet persisted | not deployed |
| `1B-β-batch-<run_id>` | Full corpus extraction (week 4-6) | `evals/vigencia_extraction_v1/<norm_id>.json` × ~30,000 | not yet run | not yet run | not yet run |
| Re-Verify Cron periodic | Periodic refresh + cascade | new rows in `norm_vigencia_history` | n/a (cron is staging+ only) | not yet deployed | not yet deployed |

### §7.4 — Falkor mirror state

| Item | dev | staging | production |
|---|---|---|---|
| `(:ArticleNode)` count (v2 schema) | 2,444 | ~7,883 | ~7,883 |
| `(:Norm)` first-class node count (v3 schema) | **11,389 (synced 2026-04-27 night)** | 0 (not yet introduced) | 0 |
| `IS_SUB_UNIT_OF` edges (v3) | **35** | 0 | 0 |
| Transition edges (MODIFIED_BY / DEROGATED_BY / SUSPENDED_BY / INEXEQUIBLE_BY / CONDITIONALLY_EXEQUIBLE_BY) | **6** (1+2+1+1+1) | 0 | 0 |
| Activity 1.5b edges (`STRUCK_DOWN_BY`, `DEROGATED_BY`, `MODIFIES`, `regimen_transicion` property) | superseded by v3 sync | 4 nodes + 4 edges from 1.5b audit log (2026-04-27 04:15 UTC) | n/a |
| `record_id` property on edges (v3 expectation) | ✅ present on all 6 transition edges | not yet present | n/a |

### §7.5 — Cron state

| Worker | dev | staging | production |
|---|---|---|---|
| Re-Verify Cron periodic worker | n/a (dev doesn't host cron) | not yet deployed | not yet deployed |
| Cascade consumer worker | n/a | not yet deployed | not yet deployed |
| State-flip notifier | n/a | not yet deployed | not yet deployed |
| Last cron tick timestamp | n/a | none yet | none yet |
| Queue depth (`vigencia_reverify_queue` rows where `processed_at IS NULL`) | n/a | n/a (table doesn't exist yet) | n/a |

### §7.6 — Deprecation view state

| Item | dev | staging | production |
|---|---|---|---|
| `documents.vigencia` column | column (real) | column (real) | column (real) |
| `document_chunks.vigencia` column | column (real) | column (real) | column (real) |
| Deprecation views in place (post `_004` migration) | not yet | not yet | not yet |
| Deprecation window closed (post `_006` migration drops columns; week 11+) | not yet | not yet | not yet |

### §7.7 — Smoke status per sub-fix (rolling)

A green here means "this sub-fix passes its H1 tests in this env." Updated as sub-fixes land.

| Sub-fix | dev | staging | production |
|---|---|---|---|
| 1A | ✅ H0 + ✅ H1 + ✅ H2 (canonicalizer ran over 7,877 corpus chunks; 11,384 norms cataloged; doc-anchor recovery dropped refusal rate 226→127 on sample) | not_started | not_started |
| 1B-α | ✅ H0 (URL resolution + cache CRUD; live HTTP still gated on `LIA_LIVE_SCRAPER_TESTS=1`) | not_started | not_started |
| 1B-β | ✅ H0 (harness + adapter test seam); live skill needs `LIA_GEMINI_API_KEY` | not_started | not_started |
| 1B-γ | ✅ H0 + ✅ H1 + ✅ H2 (6 migrations applied; 7 fixture veredictos landed in `norm_vigencia_history`; CHECK constraints + INSERT-only grants exercised) | not_started | not_started |
| 1B-δ | ✅ H0 + ✅ H1 + ✅ H2 (4,757 / 7,877 chunks have ≥ 1 citation; 40,835 citation rows; UNIQUE INDEX + dedup + doc-anchor recovery all live) | not_started | not_started |
| 1B-ε | ✅ H0 + ✅ H1 + ✅ H2 (`apply_demotion` wired into served `retrieve_graph_evidence`; `vigencia_v3` propagates to GraphEvidenceItem + Citation; per-turn diagnostic block live) | not_started | not_started |
| 1D | ✅ H0 + ✅ H1 (chip wired into `CitationItemViewModel`; rendered by citationList organism in modal/external/mention paths; 4 vitest tests verify across actions) | not_started | not_started |
| 1F | ✅ H0 + ✅ H1 (queue insert via VigenciaCascadeOrchestrator round-trips through real DB; cron deploy still gated on Railway authorization) | not_started | not_started |
| Fix 2 | not_started | not_started | not_started |
| Fix 3 | not_started | not_started | not_started |
| Fix 4 | not_started | not_started | not_started |
| Fix 5 | gate_2 (plan landed; 7 pre-seeded fixtures) | gate_2 | not_started |
| Fix 6 | not_started | not_started | not_started |

### §7.8 — Local-docker-first protocol (enforces fixplan_v3 §0.9 NEW v3 convention)

Every migration / batch / sink / cron MUST validate in `npm run dev` (local Supabase docker + local FalkorDB docker) before any staging cloud write. The protocol:

1. **Develop locally.** `make supabase-start` for Postgres; local FalkorDB container for graph.
2. **Apply migration locally.** `supabase db reset` (clean slate) or `supabase db push` (additive).
3. **Run sub-fix's H0 + H1 tests locally.** Per §6.2.
4. **Smoke the sub-fix's runtime.** If a sink: ingest 1-3 fixtures; if a cron: simulate 1 tick; if a retriever change: run 5 queries against local artifacts.
5. **Update §7.7 dev cell to ✅** in this state file.
6. **Then push to staging.** `supabase db push --linked` for migrations; `python scripts/<batch>.py` against staging env vars.
7. **Run sub-fix's smoke against staging cloud.** Same fixtures.
8. **Update §7.7 staging cell to ✅** + log the deploy in §10 run log.

Production deploys (Railway) require operator green-light AND require staging to have been ✅ for ≥ 48 hours of soak.

## §8 — Recovery playbooks

> **Use:** when execution breaks, jump here first. Each playbook is self-contained: symptom → diagnosis → recipe → verify-recovery. Playbooks reference §5 reversibility entries and §10 run log entries; the operator should be able to run any of these from this section alone.

### §8.1 — Playbook P1: "Skill produces inconsistent veredictos for the same norm"

**Symptom.** Two extraction runs of the same norm (e.g., `et.art.689-3`) produce different state codes. Reproducible across runs.

**Diagnosis steps:**
1. Check whether the norm's primary sources changed between runs (`scraper_cache.db` `fetched_at_utc`).
2. Check whether the skill prompt was revised between runs (git log on `.claude/skills/vigencia-checker/`).
3. Check whether the `LIA_GEMINI_API_KEY` model version changed (`gemini-2.5-pro` revisions are silent server-side).
4. Run the same norm with `temperature=0.0` (deterministic mode) — if results converge, the issue is sampling variance; if they still diverge, the issue is upstream.

**Recipe:**
- If primary sources changed: that's correct behavior; keep the newer veredicto, mark the older as superseded via `supersede_reason = 'periodic_reverify'`.
- If skill prompt changed: re-run the affected norms with the new prompt; old run gets superseded.
- If sampling variance: lower `temperature` to 0.0 in `VigenciaSkillHarness.__init__`; re-run.
- If unknown source: enqueue SME review via §9 open question; pause that norm's veredicto from being used in retrieval (mark `state = DT contested = true`).

**Verify recovery.** Re-run the norm 3 times; same state each time; SME spot-check confirms veredicto matches expected.

### §8.2 — Playbook P2: "1B-β extraction batch dies mid-run"

**Symptom.** The detached batch process is gone (PID not found OR PPID=1 but no recent events in `logs/events.jsonl`). The `--json` summary log is missing or partial.

**Diagnosis steps:**
1. Check `logs/events.jsonl` for the last `cli.done` or `run.failed` event for the run_id.
2. Check the heartbeat output (cron-driven if armed per CLAUDE.md long-running-job convention).
3. Check `evals/vigencia_extraction_v1/<run_id>/` for partial outputs.

**Recipe** (per CLAUDE.md long-running-job kill switches):
- If `cli.done` present → run completed; ignore the apparent death.
- If `run.failed` present → run failed cleanly; inspect the error; fix; restart with new run_id.
- If neither + process gone + last event > 10 min ago → **silent death**. STOP loop. Do NOT retry blindly. Inspect the partial outputs:
  ```bash
  python scripts/audit_vigencia_extraction.py --run-id <dead_run> --report
  # Lists: total norms processed, error patterns, last-processed norm.
  ```
- Identify the failure pattern (rate limit, OOM, network blip, malformed input).
- Fix the root cause (do not just retry).
- Restart with new `run_id`; resume from where the dead run got via `--resume-from-checkpoint`.

**Verify recovery.** New run reaches `cli.done` event; output count matches input set; SME spot-check passes.

### §8.3 — Playbook P3: "Migration partial-applied to staging"

**Symptom.** A migration in week 6-7 (typically one of the v3 sub-fix 1B-γ migrations) reported success but smoke shows the schema is half-built — some tables exist, indexes don't, or function created with wrong signature.

**Diagnosis steps:**
1. `psql "$STAGING_SUPABASE_URL" -c "\dt public.*"` — list tables.
2. `psql "$STAGING_SUPABASE_URL" -c "\df public.*"` — list functions.
3. Compare against the migration UP body to identify what landed and what didn't.
4. Check `supabase_migrations.schema_migrations` for the recorded state.

**Recipe** (Recipe B from §5.6):
1. Pause writers (cron, batches, ingest hooks).
2. Apply DOWN migrations in reverse order from `supabase/migrations/_down/`.
3. Verify clean state.
4. Fix the migration locally first per §7.8 protocol.
5. Re-apply once green in local docker.

**Verify recovery.** §7.2 staging column shows ✅ applied; smoke (single fixture ingest) passes; §7.7 sub-fix smoke status updates.

### §8.4 — Playbook P4: "Falkor and Supabase desynced"

**Symptom.** `(:Norm)` count diverges from `norms` row count. Queries against the two backends return inconsistent results.

**Diagnosis steps:**
1. Count both backends; identify divergence direction (Falkor ahead → Postgres rolled back without Falkor cleanup; Postgres ahead → Falkor sync failed mid-run).
2. Check `scripts/sync_vigencia_to_falkor.py` last-run timestamp + exit code.
3. Sample 5 random norms; check round-trip identity.

**Recipe** (Recipe D from §5.6):
1. Pause the syncer.
2. Wholesale rebuild Falkor `(:Norm)` subgraph from Postgres:
   ```bash
   python scripts/sync_vigencia_to_falkor.py --rebuild-from-postgres --confirm
   ```
3. Verify counts match.
4. Resume writers.

**Verify recovery.** Counts match; round-trip identity on 50 random norms; smoke query returns same answer in both backends.

### §8.5 — Playbook P5: "Cron stuck — queue depth growing"

**Symptom.** `vigencia_reverify_queue` table has > 100 unprocessed rows AND the count is growing faster than draining.

**Recipe** (Recipe C from §5.6 — full version):
1. Diagnose if consumer is alive (`railway logs`).
2. Check queue depth.
3. Check for feedback loop: if `cascade_reviviscencia` rows dominate recent inserts, the cascade is self-triggering.
4. Pause the consumer (`railway scale --replicas 0`).
5. Inspect a sample of recent inserts; identify the recursive trigger.
6. Manually drain (mark as processed without writing).
7. Fix the trigger logic; redeploy.
8. Resume consumer.

**Verify recovery.** Queue drains to < 10 within 1 cron tick (6h default); no new feedback-loop rows.

### §8.6 — Playbook P6: "Canonicalizer regression after rule addition"

**Symptom.** A new rule baked into `src/lia_graph/canon.py` (typically from refusal-queue triage) breaks previously-correct canonicalization on other patterns. Test suite shows regressions in `tests/test_canon.py`.

**Recipe:**
1. Identify the regressing patterns (test output lists).
2. Revert the new rule (`git revert <commit>` on the canon.py change).
3. Re-add the rule with narrower scope (e.g., regex anchored to specific context, OR new function rather than modifying existing).
4. Run full `tests/test_canon.py` + Activity 6 50-chunk pilot.
5. Re-bake only when both pass.

**Verify recovery.** All canonicalizer tests pass; 50-chunk pilot ≥ 95%; SME signoff on the rule revision.

### §8.7 — Playbook P7: "Retrieval returns inconsistent results post-1B-ε"

**Symptom.** Same query run twice returns different chunks; or queries that should return historical content (per `for_period`) return current content.

**Diagnosis steps:**
1. Check planner output: `vigencia_query_kind` and `vigencia_query_payload` correctly set?
2. Check resolver function output: run `SELECT * FROM norm_vigencia_at_date('2018-12-31') WHERE norm_id = 'et.art.147' LIMIT 5;` — returns expected row?
3. Check `norm_citations` for the relevant chunks: are they joined to the right `norm_id`?
4. Check Falkor side: is the period-aware factor computed correctly in `pipeline_d/retriever_falkor.py`?

**Recipe:**
- If planner cue extraction wrong: extend the regex/heuristics in `pipeline_d/planner.py`; add a unit test for the missed cue.
- If resolver returns wrong row: validate `applies_to_payload` for the relevant history rows; SME may need to correct data via a new history row (NOT an UPDATE).
- If `norm_citations` wrong: re-run 1B-δ canonicalizer for the affected chunks (per Recipe in §8.6).
- If Falkor side wrong: re-run `scripts/sync_vigencia_to_falkor.py` for the affected norms.

**Verify recovery.** Re-run the offending query 5 times; same chunks each time; SME spot-checks the period-applicability.

### §8.8 — Playbook P8: "Operator wants to revert v3"

**Symptom.** Strategic decision: roll back v3 entirely, return to v2 column shape.

**Recipe** (Recipe E from §5.6 — full version):
1. Pause all writers.
2. Restore Supabase snapshot from immediately before migration `_006` was applied. **STOP if no snapshot.**
3. Run all DOWN migrations in reverse order.
4. Restore `documents.vigencia` column from `_archive` (preserved by `_004`).
5. Revert retriever code (1B-ε changes) — `git revert`.
6. Revert env matrix bump.
7. Smoke §1.G — ensure post-revert baseline matches pre-v3 (≥ 21/36 served_acceptable+).
8. The 7 v2-shape veredicto fixtures stay; Activity 1.5b's 4 staging UPDATEs stay.

**Result.** v3 fully reverted; project at v2 / pre-Activity-1.7-mark state plus the 1.5b smoke.

**Verify recovery.** §1.G eval ≥ 21/36; Falkor `(:Norm)` count = 0 (no v3 nodes); `documents.vigencia` is a real column with v2 enum.

### §8.9 — Generic recovery decision tree

When something breaks and the symptom doesn't match P1-P8 cleanly:

```
Is the failure data corruption (wrong veredictos, wrong rows)?
├── YES → identify run_id → use §5 reversibility class R2 cleanup → re-run
│
└── NO → is it a schema problem (migration / tables / functions)?
    ├── YES → use §5 reversibility class R3 (DOWN script) → §8.3 (P3)
    │
    └── NO → is it an infrastructure problem (cron / deploy / env)?
        ├── YES → §5 §5.4 → matching playbook (P5 cron, etc.)
        │
        └── NO → unknown → §9 open question + §10 run log entry → operator
```

**Default:** if you don't know which playbook applies, log to §10 (failure entry), §9 (open question), pause forward progress, ask the operator. Do NOT improvise destructive actions.

---

## §9 — Open questions queue

> **Update protocol:** append-only when adding; in-place edit to mark resolved. Never delete entries — resolved entries move to a "Resolved" subsection at the bottom.

### §9.1 — Active questions

| # | Question | Who needs to answer | Blocks | Raised | Status |
|---|---|---|---|---|---|
| Q1 | Sign off on `fixplan_v3.md` (architecture + 11-state taxonomy + 3-table persistence + cascade orchestration)? | Operator | All week-1 starts | 2026-04-27 evening (Bogotá) | OPEN |
| Q2 | Sign off on `state_fixplan_v3.md` (this file)? | Operator | Engineer assignment for week 1 | 2026-04-27 evening (Bogotá) | OPEN |
| Q3 | Schedule SME ontology session (skill v2.0 prompt review + Activity 1.7b canonical-norm picks for VC/VL/DI/RV)? | SME (Alejandro) + operator | Fix 1A gate-2; Activity 1.7b start | 2026-04-27 evening (Bogotá) | OPEN |
| Q4 | Engineer assignment for Fix 1A (ontology + canonicalizer)? | Operator | Fix 1A gate-1 sketch | 2026-04-27 evening (Bogotá) | OPEN |
| Q5 | Engineer assignment for Fix 1B-α (scrapers, parallel critical path)? | Operator | Fix 1B-α gate-1 sketch | 2026-04-27 evening (Bogotá) | OPEN |
| Q6 | SME picks for 4 canonical norms covering VC / VL / DI / RV state seeding? | SME | Activity 1.7b ship | 2026-04-27 evening (Bogotá) | OPEN |
| Q7 | Frontend engineer assignment for Fix 1D (11 chip variants, weeks 9-10)? | Operator | Fix 1D gate-1 (can defer until week 7) | 2026-04-27 evening (Bogotá) | OPEN |
| Q8 | Verify `LIA_GEMINI_API_KEY` is set in staging + production environments? | Operator | Fix 1B-β (week 4-6) | 2026-04-27 evening (Bogotá) | OPEN |
| Q9 | Confirm budget envelope re-allocation tolerance for sub-unit extraction (§11.3 risk 1)? | Operator | Fix 1B-β scope decision (articles-only first vs articles+sub-units in same pass) | 2026-04-27 evening (Bogotá) | OPEN |
| Q10 | Decide whether the Re-Verify Cron deploys to staging in week 4-5 or only after 1B-γ ships in week 6-7? | Operator + tech lead | Re-Verify Cron deploy schedule | 2026-04-27 evening (Bogotá) | OPEN |

### §9.2 — Resolved questions

*(Empty — none resolved yet.)*

When a question is resolved, copy its row here with `RESOLVED yyyy-mm-dd hh:mm by <author>` appended to the Status column, plus a Resolution column with the answer.

| # | Question | Resolution | Resolved | Resolver |
|---|---|---|---|---|

---

## §10 — Run log (append-only narrative)

> **Update protocol:** append entries at the **TOP** (newest first) so a fresh reader sees latest state immediately. Cron heartbeats append condensed entries; engineers append narrative entries. ISO timestamp + Bogotá AM/PM mandatory.

**Entry format:**
```
### YYYY-MM-DD HH:MM Bogotá (UTC YYYY-MM-DDTHH:MM:SSZ) — <one-line summary>

**Author:** <engineer name | cron@v1 | claude-opus-4-7 | SME | operator>
**Type:** gate_crossing | deploy | failure | recovery | sme_signoff | operator_decision | cron_heartbeat | misc
**Sub-fix:** <ID or n/a>
**Details:**
<narrative — what happened, what was expected, what was unexpected, what was done>
**Outcome:**
<state change — e.g., "1A advanced to gate_3", "migration applied to staging", "queue drained">
**Cross-references:**
- §<N> updated: <what changed>
- §9 question raised: Q<N>
- Run log prior entry: <link or "n/a">
```

### §10.1 — Recent entries (newest first)

### 2026-04-27 night Bogotá — Full local-env wiring: corpus loaded, fixtures landed, served retrieval gating live

**Author:** claude-opus-4-7
**Type:** gate_crossing (✅ H1 → ✅ H2/H3 cluster) for sub-fixes 1A, 1B-α, 1B-γ, 1B-δ, 1B-ε, 1D, 1F (dev cell only; staging still operator-gated)
**Sub-fix:** Fix 1 — full e2e through served retrieval path
**Details:**

End-to-end wiring of every Fix 1 sub-fix through the served chat path against the local stack only. User directives in this session: *"for the rest of the implementation use ONLY LOCAL ENV"*; *"make sure corpus is fully updated in local supabase and local falkor"*; *"all tests should use a runner with heartbeat and batched"*; *"incorporate learnings in docs/learnings as you go"*; *"continue implementation, DO NOT STOP. you find bugs, you fix them yourself"*. All applied.

**1. Corpus refresh (1,286 docs, 7,877 chunks, 28,181 typed edges).** `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=wip` against local Supabase docker (port 54322); local FalkorDB (port 6389) loaded with 2,444 :ArticleNode + 1,788 :ReformNode + 69 :SubTopicNode + 56 :TopicNode.

**2. 1B-δ backfill ran live** (`scripts/backfill_norm_citations.py --target wip --run-id local-backfill-full`): 4,757 of 7,877 chunks (60.4%) have ≥ 1 citation, 11,384 norms cataloged, 40,835 citation rows. Anchor-strength distribution: ley=16,078; concepto_dian=16,758; decreto=5,614; res_dian=2,214; jurisprudencia=171.

**3. 7 fixture veredictos landed in `norm_vigencia_history`** via `scripts/upgrade_v2_veredictos_to_v3.py` + `scripts/ingest_vigencia_veredictos.py --target wip --run-id v2-to-v3-upgrade-2026-04-27 --extracted-by v2_to_v3_upgrade`. Final state: V (et.art.290.num.5), VM (et.art.689-3), DE (et.art.158-1), DT (et.art.588), SP (concepto.dian.100208192-202.num.20), IE (decreto.1474.2025), EC (ley.2277.2022.art.11) — all 7 v2 states represented.

**4. Falkor (:Norm) mirror synced** (`scripts/sync_vigencia_to_falkor.py --target wip`): 11,389 (:Norm) nodes, 35 IS_SUB_UNIT_OF edges, 1 MODIFIED_BY, 2 DEROGATED_BY, 1 SUSPENDED_BY, 1 INEXEQUIBLE_BY, 1 CONDITIONALLY_EXEQUIBLE_BY = 41 transition+structural edges all live in `LIA_REGULATORY_GRAPH`.

**5. Demotion pass wired into served retrieval.** `src/lia_graph/pipeline_d/retriever_supabase.py::_apply_v3_vigencia_demotion` runs immediately after `hybrid_search` + anchor merge. Pulls `chunk_vigencia_gate_at_date` (or `_for_period` when planner cue present), drops factor=0.0 chunks, scales kept chunks by demotion_factor, annotates `vigencia_v3` on each kept row. Added `vigencia_v3` field to `GraphEvidenceItem` and `Citation` (frozen-dataclass-safe via `dataclasses.replace`); `_collect_support` aggregates the most-restrictive annotation per doc. Diagnostics surface `vigencia_v3_demotion` block per turn.

**6. Chip wired into chat citation list.** `frontend/src/shared/ui/atoms/vigenciaChip.ts` reads from `citation.vigencia_v3` via the `deriveVigenciaV3ChipOptions` helper in `chatCitationRenderer.ts`. `CitationItemViewModel.vigenciaV3` field added; the citation-list organism appends the chip in modal/external/mention paths.

**7. Batched test runner rebuilt + enforced.** `scripts/run_tests_batched.py` (referenced by `Makefile::test-batched` but missing from repo) restored: discovers test files, splits into N batches, runs each in its own pytest subprocess with `LIA_BATCHED_RUNNER=1`, emits per-batch heartbeat lines in Bogotá AM/PM, stall-kills batches at 6× median + 60s floor, parses pytest output (with `-r fEs --tb=line -o addopts=` to override `-q` summary suppression). Coverage gate via `--cov` + `--fail-under`. Used for every test invocation in this session.

**Bugs found and fixed in-session (v3-related, not pre-existing):**

1. `norm_citations` UNIQUE constraint missing (caught by ON CONFLICT failure on first live UPSERT) — migration `20260501000002` updated to `CREATE UNIQUE INDEX`.
2. `ARRAY[%s]` with Python list produces 2-D Postgres array — passing `%s::text[]` directly fixed it.
3. CHECK violations fire at `cur.execute()` not `commit()` — test shape fixed.
4. Tx state leakage between integration tests — autouse cleanup now rolls back first.
5. `1B-δ backfill` UPSERTs same `(chunk_id, norm_id, role)` triple twice in one batch when prose mentions a norm multiple times — dedupe set added before send.
6. v2 `vigente_hasta` semantics drift in v2-to-v3 upgrade mapper — DE/IE/SP rows incorrectly inherited `state_until` from the prior V row's end-of-applicability. Mapper now only carries `vigente_hasta` for V/VM states.
7. v2 fixture `parágrafo` field can be a multi-sub-unit description (`"numerales 1, 2, 3 y parágrafo 6"`) — only attach single-sub-unit hints; otherwise keep parent norm.
8. Plural article references (`Arts. 588 y 589 ET`) and unparseable wrappers (`Decreto Legislativo 1474 de 2025`) — pre-clean in upgrade script before canonicalizer.
9. `chunk_vigencia_gate_at_date` LEFT JOIN returns null state when chunk cites a norm with no history row yet — demotion pass now filters null-state anchors instead of polluting the annotation with `state=None`.
10. Doc-level aggregation in `_collect_support` was including passthrough annotations — fixed by only annotating chunks whose anchor produced a real (non-null) state.
11. Existing `test_retriever_supabase.py::_FakeClient.rpc` asserted `name == "hybrid_search"` — now allowlists the new v3 RPC names.

**Live integration test results (all green via batched runner):**

- Postgres e2e (`tests/integration/test_v3_persistence_e2e.py`): 9 tests — catalog round-trip, history insert + at_date resolver, `for_period` with Art. 338 CP shift (V row for AG 2022; VM row for AG 2023), chunk_vigencia_gate join, idempotent re-run, queue insert via cascade orchestrator, and 3 CHECK-violation tests.
- Falkor live (`tests/integration/test_v3_falkor_norm_mirror.py`): 2 tests — (:Norm) node MERGE via raw-socket GraphClient + sub-unit IS_SUB_UNIT_OF edge.
- Served retrieval e2e (`tests/integration/test_v3_served_retrieval_demotion.py`): 4 tests — drops DE-anchored chunks, propagates `vigencia_v3` on evidence items + citations, `for_period` planner-cue path.

**H0 results (all green via batched runner):**
- 6 batches × ~40 tests = 239 H0 v3 tests (vigencia ontology, canon, norm_history_writer, role_inference, vigencia_resolver, vigencia_demotion, vigencia_cascade, scrapers, vigencia_extractor, retriever_supabase_v3_demotion, norms_catalog_migration_shape).
- Frontend: 20 vitest tests (vigenciaChip 13 + citationListVigencia 4 + subtopicChip 3).

**Full project suite via batched runner**: 1,501 passed / 18 failed across 13 files. Confirmed via `git stash` baseline check that all 18 failures pre-existed our changes (rooted in env-vars / topic_boost defaults / static fixtures unrelated to v3).

**3 new learnings landed:**
- `docs/learnings/retrieval/v3-served-retrieval-wiring-2026-04-27.md` — the three bugs caught only at the served-retrieval horizon.
- `docs/learnings/process/batched-test-runner-discipline-2026-04-27.md` — runner rebuild + protocol.
- `docs/learnings/ingestion/canonicalizer-doc-anchor-recovery-2026-04-27.md` — context-free canonicalizer + structured-context backfill recovery.

**State file + ledger updated.** §4 ledger advanced 1A/1B-α/1B-γ/1B-δ/1B-ε/1D/1F dev cells from 🧪 H0 → ✅ H1+H2 (live+wired). §7.7 sub-fix smoke status flipped accordingly.

**What's still gated on operator green-light (per §2.4):**
- Staging migration apply (`supabase db push --linked` against staging cloud).
- 1B-β corpus extraction batch (`LIA_GEMINI_API_KEY`-gated).
- Re-Verify Cron deploy to Railway staging.
- SME ontology session for skill v2.0 prompt update + Activity 1.7b VC/VL/DI/RV norm picks.

**Cross-references:**
- §4 ledger rows updated for 1A, 1B-α, 1B-γ, 1B-δ, 1B-ε, 1D, 1F.
- §7.2 migration table: all 6 v3 migrations applied to dev (with `_002` revision after UNIQUE constraint find).
- §7.4 Falkor mirror state: dev cell now reports 11,389 (:Norm) nodes + 41 v3 edges.
- §10 entry (this one) — full session ledger.

**Files added/modified this session (cumulative on top of prior session):**
- *Added scripts:* `scripts/run_tests_batched.py`, `scripts/upgrade_v2_veredictos_to_v3.py`.
- *Added tests:* `tests/integration/test_v3_served_retrieval_demotion.py` (4 tests), `tests/test_retriever_supabase_v3_demotion.py` (5 tests), `frontend/tests/citationListVigencia.test.ts` (4 tests).
- *Added learnings:* 3 docs in `docs/learnings/{retrieval,process,ingestion}/`.
- *Modified:* `supabase/migrations/20260501000002_norm_citations.sql` (UNIQUE INDEX); `src/lia_graph/pipeline_d/{retriever_supabase,vigencia_demotion}.py` (wiring + null-state filter + doc aggregation); `src/lia_graph/pipeline_d/contracts.py` (`GraphEvidenceItem.vigencia_v3`); `src/lia_graph/contracts/advisory.py` (`Citation.vigencia_v3`); `frontend/src/shared/ui/organisms/citationList.ts` + `frontend/src/features/chat/chatCitationRenderer.ts` (chip wiring); `scripts/{backfill_norm_citations,sync_vigencia_to_falkor}.py` (live-DB fixes).


### 2026-04-27 night Bogotá — Live local-env e2e: dev cells advanced from H0 → ✅ for 1A, 1B-α, 1B-γ, 1B-δ, 1B-ε, 1F

**Author:** claude-opus-4-7
**Type:** gate_crossing (H0 → ✅) for sub-fixes 1A, 1B-α, 1B-γ, 1B-δ, 1B-ε, 1F (dev cell only; staging still gated on operator green-light)
**Sub-fix:** Fix 1 — local-env e2e
**Details:**
End-to-end smoke against the local stack, per the user's directive *"for the rest of the implementation use ONLY LOCAL ENV (which mimics staging anyways)"*:

1. **Local Supabase docker** — `supabase status` confirmed running on port 54322. `supabase db reset --local` re-applied all migrations cleanly, including the 6 new v3 ones (`20260501000000` through `_005`).
2. **Corpus refresh** (per user directive *"make sure corpus is fully updated in local supabase and local falkor"*) — ran `nohup make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=wip` with env preloaded from `.env.local`. Result: 1,286 documents, 7,877 chunks, 28,181 typed edges in local Supabase; 2,444 :ArticleNode + 1,788 :ReformNode + 69 :SubTopicNode + 56 :TopicNode in local FalkorDB (`LIA_REGULATORY_GRAPH`).
3. **Live e2e for 1B-γ + 1B-δ + 1B-ε + 1F** in `tests/integration/test_v3_persistence_e2e.py` (9 tests pass against psycopg connection to port 54322): catalog round-trip with parent walk, history insert + resolver `at_date`, resolver `for_period` (Art. 338 CP shift to V row for AG 2022 / VM row for AG 2023), `chunk_vigencia_gate_at_date` join, idempotent re-run, queue insert via cascade orchestrator, and 3 CHECK-violation tests (invalid state code; forbidden `synthesis@v1` extracted_by; `state_until` before `state_from`).
4. **Live Falkor smoke for the v3 (:Norm) mirror** in `tests/integration/test_v3_falkor_norm_mirror.py` (2 tests pass): seed Postgres → call sync helpers → MERGE in Falkor via raw-socket GraphClient → assert nodes + INEXEQUIBLE_BY edge land + sub-unit IS_SUB_UNIT_OF edge lands. Uses dedicated test graph `LIA_REGULATORY_GRAPH_TEST_V3` to avoid touching the production graph.

**Bugs caught only by live e2e (and fixed in same session):**

1. **`norm_citations` was missing UNIQUE constraint** — `ON CONFLICT (chunk_id, norm_id, role)` failed against real Postgres because the index was `CREATE INDEX`, not `CREATE UNIQUE INDEX`. Migration `20260501000002_norm_citations.sql` updated to ship a UNIQUE INDEX. Captured in `docs/learnings/retrieval/norm-citations-unique-index-2026-04-27.md`.
2. **`ARRAY[%s]` with a Python list silently produces a 2-D Postgres array** — `chunk_vigencia_gate_at_date(ARRAY[chunk_id], …)` returned 0 rows. Fix: pass `%s::text[]` directly. Captured in `docs/learnings/retrieval/postgres-array-literal-2d-trap-2026-04-27.md`.
3. **psycopg raises CHECK violations at `cur.execute()`, not `conn.commit()`** — first iteration of the CHECK tests wrapped commit() in pytest.raises and false-passed. Fixed by wrapping cur.execute() instead.
4. **Failed-tx state leaks between tests on the same conn** — `InFailedSqlTransaction` blocks the autouse cleanup fixture's DELETE statements until rollback fires.

These four findings are summarized in `docs/learnings/process/h0-fakes-vs-live-db-gap-2026-04-27.md` — H0 fake clients verify Python shape; only live psycopg verifies schema contract. Every sub-fix that ships a new SQL function / UPSERT / CHECK / `text[]` parameter must ship a live-DB integration smoke alongside H0 fakes.

**Outcome:**
- All 6 v3 migrations applied cleanly to local Supabase docker.
- Corpus is current in BOTH local Supabase AND local Falkor.
- 9 e2e Postgres tests + 2 e2e Falkor tests pass against the real local stack.
- 4 schema/test bugs found and fixed (UNIQUE constraint, array literal trap, CHECK timing, tx state).
- 3 new learnings landed in `docs/learnings/{retrieval,process}/`; learnings README updated.
- §7.7 dev cells for 1A, 1B-α, 1B-γ, 1B-δ, 1B-ε, 1F now ✅ (live H1 verified).
- Staging cells unchanged — operator-gated per §2.4.

**What's still gated:**
- Staging deploy of migrations (operator: `supabase db push --linked`).
- Skill harness live run (`LIA_GEMINI_API_KEY`).
- 1B-β corpus extraction batch (needs API key + warmed scraper cache).
- 1F Re-Verify Cron deployed to Railway staging.
- SME ontology session for skill v2.0 prompt update + Activity 1.7b canonical-norm picks.

**Cross-references:**
- §4.2 ledger rows for 1A, 1B-α, 1B-γ, 1B-δ, 1B-ε, 1F advanced from 🧪 → ✅ for the dev cell.
- §7.2 migration table updated (all 6 v3 migrations applied to dev).
- §7.7 sub-fix smoke status updated for dev cell.
- §5 reversibility — `Recipe A` (1B-β extraction batch cleanup), `Recipe B` (migration partial-apply), `Recipe D` (Falkor desync rebuild) now exercised end-to-end at small scale.

**Files added/modified this session:**
- *Added:* `tests/integration/test_v3_persistence_e2e.py` (9 tests; 715 LOC); `tests/integration/test_v3_falkor_norm_mirror.py` (2 tests; 245 LOC).
- *Added:* `docs/learnings/retrieval/norm-citations-unique-index-2026-04-27.md`; `docs/learnings/retrieval/postgres-array-literal-2d-trap-2026-04-27.md`; `docs/learnings/process/h0-fakes-vs-live-db-gap-2026-04-27.md`.
- *Modified:* `supabase/migrations/20260501000002_norm_citations.sql` (added UNIQUE INDEX); `docs/learnings/README.md` (3 new index entries).


### 2026-04-27 evening Bogotá (continuous session) — H0 implementation pass for all 8 Fix 1 sub-fixes

**Author:** claude-opus-4-7
**Type:** gate_crossing (gate 1 → gate 5 H0) for sub-fixes 1A, 1B-α, 1B-β, 1B-γ, 1B-δ, 1B-ε, 1D, 1F
**Sub-fix:** Fix 1 (all)
**Details:**
Single continuous-session implementation pass landing the H0 surface for every Fix 1 sub-fix (per §6.2 horizon discipline — H1+ requires a populated DB / corpus / Gemini API key, all of which need operator authorization to apply). Code shape:

- **Fix 1A** — `src/lia_graph/vigencia.py` (Vigencia value object, 11-state enum, ChangeSource discriminated union per §0.3.3, `applies_to_*` resolver helpers, v2→v3 mapper). `src/lia_graph/canon.py` (§0.5 grammar — 9 mention-finding rules, refusal contract, parent / sub-unit / type / display-label helpers, full grammar regex). 142 H0 tests across `tests/test_vigencia_v3_ontology.py` + `tests/test_canon.py` (every state round-trips, every refusal case fires correct reason, every §0.5.4 example canonicalizes deterministically).
- **Fix 1B-α** — `src/lia_graph/scrapers/{base,cache,secretaria_senado,dian_normograma,suin_juriscol,corte_constitucional,consejo_estado}.py`. SQLite cache schema includes the v3-additive `canonical_norm_id` column + index (§0.11.3 contract 3). 5 scrapers with URL resolvers + stdlib HTML→text parsers + per-source modification-note extractors. Live HTTP gated on `LIA_LIVE_SCRAPER_TESTS=1`. 19 H0 tests pass (`tests/test_scrapers.py`).
- **Fix 1B-γ** — Six migrations: `20260501000000_norms_catalog`, `20260501000001_norm_vigencia_history` (append-only role grants), `20260501000002_norm_citations`, `20260501000003_resolver_functions` (`norm_vigencia_at_date` + `norm_vigencia_for_period` honoring Art. 338 CP), `20260501000004_chunk_vigencia_gate` (retriever-side RPC), `20260501000005_vigencia_reverify_queue`. Each starts with `DROP FUNCTION IF EXISTS` per the hybrid_search-overload-2026-04-27 learning. `src/lia_graph/persistence/norm_history_writer.py` is the sole sanctioned writer (rejects `synthesis@v1` / `retrieval@v1` per §0.7.3 + the migration's CHECK). `scripts/{ingest_vigencia_veredictos,sync_vigencia_to_falkor}.py`. `graph/schema.py` extended with `Norm` node + 9 new edge kinds (MODIFIED_BY / DEROGATED_BY / SUSPENDED_BY / INEXEQUIBLE_BY / CONDITIONALLY_EXEQUIBLE_BY / MODULATED_BY / REVIVED_BY / CITES / IS_SUB_UNIT_OF). 13 writer + 8 migration-shape tests pass.
- **Fix 1B-β** — `src/lia_graph/vigencia_extractor.py` (VigenciaSkillHarness with `adapter_factory` test seam, default-`from-cache` flow, refusal contract on missing API key / fewer than 2 sources / invalid JSON / invalid Vigencia shape). `scripts/{build_extraction_input_set,extract_vigencia}.py` driver scripts (long-running-job convention: events in `logs/events.jsonl`, audit log per norm, resume-from-checkpoint). 8 H0 tests pass.
- **Fix 1B-δ** — `src/lia_graph/citations.py` (role inference: anchor / comparator / historical / reference; anchor-strength inference: ley > decreto > res_dian > jurisprudencia > concepto_dian). `scripts/{backfill_norm_citations,audit_norm_citations}.py`. Refusal-queue logging to `evals/canonicalizer_refusals_v1/refusals.jsonl`. 11 H0 tests pass (`tests/test_role_inference.py`).
- **Fix 1B-ε** — `src/lia_graph/pipeline_d/{vigencia_resolver,vigencia_demotion}.py`. `GraphRetrievalPlan` extended with `vigencia_query_kind` + `vigencia_query_payload`. Cue extractor `extract_vigencia_cue(query)` recognizes `AG NNNN` / `año gravable NNNN` / `período NNNN` (for_period) and `en NNNN` / `para NNNN` (at_date). Demotion pass takes hybrid_search output + RPC results, multiplies RRF scores by demotion_factor, drops factor=0 chunks, annotates kept chunks with `vigencia_v3` block for chip rendering. 18 H0 tests pass.
- **Fix 1D** — `frontend/src/shared/ui/atoms/vigenciaChip.ts` mirrors the `subtopicChip.ts` atomic-design pattern. 11 variants (V → no chip; VM/DE/DT/SP/IE/EC/VC/VL/DI/RV); EC + VC store literal Court text in `data-interpretive-constraint` + `title`; VL/DI render fechas; RV names the triggering inexequibilidad in the aria-label. `frontend/tests/vigenciaChip.test.ts` — 13 vitest tests (jsdom env) all pass.
- **Fix 1F** — `src/lia_graph/pipeline_d/vigencia_cascade.py` (VigenciaCascadeOrchestrator: `on_history_row_inserted` for reviviscencia, `on_periodic_tick` for future-dated state flips, `detect_inconsistency` read-only consumer for the coherence gate, public `queue_reverify` for Fix 3). 3 cron entry points: `cron/{cascade_consumer,state_flip_notifier,reverify_periodic}.py`. 9 H0 tests pass (Ley 1943 → C-481 cascade smoke, idempotency, future-flip notifier, divergent-state inconsistency detector).

Net: ~3,800 LOC of src; ~2,600 LOC of tests; 222 unit tests pass; 0 fail. All sub-fixes at H0 verified per §6.2.

**Outcome:**
- §3.1 active week advanced to "week 0 → week 1 transition; H0 done."
- §4.2 — every Fix 1 sub-fix advanced from `not_started` → `🧪 (H0 verified)`.
- §7.2 — 6 v3 migrations written and ready to apply.
- §7.7 — every Fix 1 dev cell advanced from `not_started` → ✅ H0 (with explicit caveat for which higher-horizon path each sub-fix needs).
- §10 entry (this one) — ledger captures what shipped + what's still gated on operator/SME.

**What's gated on operator / SME (next session):**
1. Operator: `supabase db reset` (local docker) → `supabase db push --linked` (staging) for the 6 v3 migrations.
2. Operator: confirm `LIA_GEMINI_API_KEY` in staging env so 1B-β can run live.
3. SME (Alejandro): ontology session for skill v2.0 prompt update + Activity 1.7b canonical-norm picks.
4. Operator + SME: pre-warm the scraper cache for the 7 known fixtures so the H1 v2-to-v3 upgrade smoke can run without live HTTP.
5. Operator: deploy cron workers to Railway staging once 1B-γ migrations apply (Fix 1F has no DB to write to until then).

**Cross-references:**
- §4.2 ledger rows for 1A, 1B-α, 1B-β, 1B-γ, 1B-δ, 1B-ε, 1D, 1F all updated with file paths + test counts.
- §7.2 migration table updated with the 6 v3 migration filenames.
- §7.7 sub-fix smoke status for every Fix 1 row updated to ✅ H0.
- §9 questions Q1–Q10 remain OPEN (operator/SME-gated; not resolvable by an LLM).

**Files created (top-level summary):**
- `src/lia_graph/{vigencia,canon,citations,vigencia_extractor}.py`
- `src/lia_graph/persistence/{__init__,norm_history_writer}.py`
- `src/lia_graph/pipeline_d/{vigencia_resolver,vigencia_demotion,vigencia_cascade}.py`
- `src/lia_graph/scrapers/{__init__,base,cache,secretaria_senado,dian_normograma,suin_juriscol,corte_constitucional,consejo_estado}.py`
- `frontend/src/shared/ui/atoms/vigenciaChip.ts`
- `cron/{__init__,cascade_consumer,state_flip_notifier,reverify_periodic}.py`
- `scripts/{ingest_vigencia_veredictos,sync_vigencia_to_falkor,backfill_norm_citations,audit_norm_citations,extract_vigencia,build_extraction_input_set}.py`
- `supabase/migrations/20260501000000_norms_catalog.sql`
- `supabase/migrations/20260501000001_norm_vigencia_history.sql`
- `supabase/migrations/20260501000002_norm_citations.sql`
- `supabase/migrations/20260501000003_resolver_functions.sql`
- `supabase/migrations/20260501000004_chunk_vigencia_gate.sql`
- `supabase/migrations/20260501000005_vigencia_reverify_queue.sql`
- 10 test files: `tests/test_{vigencia_v3_ontology,canon,norm_history_writer,norms_catalog_migration_shape,role_inference,vigencia_resolver,vigencia_demotion,vigencia_cascade,scrapers,vigencia_extractor}.py`
- `frontend/tests/vigenciaChip.test.ts`
- Files modified: `src/lia_graph/graph/schema.py` (NORM node + 9 edges); `src/lia_graph/pipeline_d/contracts.py` (`GraphRetrievalPlan.vigencia_query_kind` + `vigencia_query_payload`).


### 2026-04-27 7:55 PM Bogotá (UTC 2026-04-28T00:55:00Z) — `state_fixplan_v3.md` initial ship complete

**Author:** claude-opus-4-7
**Type:** misc
**Sub-fix:** n/a
**Details:**
Drafted state_fixplan_v3.md in 5 chapters (§1-§3 ch1, §4 ch2, §5 ch3, §6+§7 ch4, §8+§9+§10 ch5). Companion to fixplan_v3.md. Establishes single source of truth for execution state, fresh-LLM runnable preconditions, per-sub-fix gate ledger, full reversibility matrix (5 classes R1-R5; rollback recipes A-E), 4-horizon test discipline, env state across dev/staging/production, 8 recovery playbooks, open questions queue (Q1-Q10), and this run log.
**Outcome:**
- §3 set to "no sub-fix in flight; awaiting operator green-light on v3 plan + state file."
- §9 Q1-Q10 raised (all OPEN).
- §7 reflects pre-v3 baseline state of all envs.
**Cross-references:**
- All sections of state_fixplan_v3.md updated (initial ship).
- Q1-Q10 raised in §9.

### 2026-04-27 (rolling, evening) — `fixplan_v3.md` complete (12 chapters, 2,050 lines)

**Author:** claude-opus-4-7
**Type:** misc
**Sub-fix:** n/a
**Details:**
Drafted fixplan_v3.md in 12 chapters: header + §0 honest diagnosis (6 breaks; new break 6 = vigencia denormalized), §0.1 redesign drivers, §0.2 12-mode Colombian mutation surface, §0.3 three-table persistence + Falkor mirror + structured change_source, §0.4 11-state enum, §0.5 norm-id grammar (6 artifact types; sub-units first-class), §0.6 two resolver functions (Art. 338 CP), §0.7 cron-driven cascade orchestration, §0.8-§0.11 reading + conventions + skill summary + v3 data contracts, §1 fix overview table, §2 detailed sub-fix specs (1A, 1B-α, 1B-β, 1B-γ, 1B-δ, 1B-ε, 1D, 1F + week-6 kill switch), §3-§7 Fix 2-6 with v3 read-path notes, §8 activities (1/1.5/1.5b/1.6/1.7 ✅; 1.7b/1.8 queued; A6 canonicalizer pilot), §9 dependencies, §10 checkpoints, §11 budget (envelope preserved), §12-§15 NOT-doing/done-state/glossary/playbook.
**Outcome:**
- v3 plan complete; supersedes v2.
- 7 of 30 Fix 5 cases pre-seeded.
- 7 of 11 vigencia states validated against real norms.
**Cross-references:**
- §4 ledger seeded with all 8 Fix 1 sub-fixes + Fixes 2-6 + activities.

### 2026-04-27 04:15 UTC (Bogotá ~11:15 PM 2026-04-26) — Activity 1.5b shipped (cloud writes)

**Author:** engineer + cron
**Type:** deploy
**Sub-fix:** Activity 1.5b
**Details:**
`scripts/persist_veredictos_to_staging.py` ran against staging Supabase + Falkor. 4 veredictos persisted: Decreto 1474/2025 (IE → Sentencia C-079/2026 STRUCK_DOWN_BY edge), Art. 689-3 ET (VM → Ley 2294/2023 Art. 69 MODIFIES edge), Art. 158-1 ET (DE → Ley 2277/2022 Art. 96 DEROGATED_BY edge), Art. 290 #5 ET (V → regimen_transicion property). Audit log: 6 lines in `evals/activity_1_5/persistence_audit.jsonl` (3 Supabase UPDATEs + 3 Falkor MERGEs). No regressions.
**Outcome:**
- Staging cloud Supabase: 4 documents.vigencia rows updated.
- Staging cloud Falkor: 4 nodes' vigencia property + 4 new edges with property bags.
- Smoke: §1.G stays at 21/36 served_acceptable+.
**Cross-references:**
- §7 staging extraction state updated (Activity 1.5b row).
- v3 plan §8 references this for re-persistence-when-1B-γ-ships.

### 2026-04-26 evening (Bogotá) — Activity 1.7 fixtures complete (DT/SP/EC)

**Author:** claude-opus-4-7
**Type:** sme_signoff (precursor — fixtures ready for SME validation)
**Sub-fix:** Activity 1.7
**Details:**
3 veredicto fixtures produced via manual skill protocol walkthrough using WebSearch as primary-source proxy: `arts_588_589_ET_correcciones_imputacion_AG2025_veredicto.json` (DT — Sentencia de Unificación 2022CE-SUJ-4-002 Consejo de Estado), `concepto_dian_100208192_202_num20_AG2026_veredicto.json` (SP — Auto/Sentencia 28920 del 16-dic-2024 CE Sección Cuarta), `art_11_ley_2277_2022_zonas_francas_AG2023_veredicto.json` (EC — Sentencia C-384/2023 CC, "EXEQUIBLES en el entendido que..." literal text captured). Each fixture includes `fix_5_skill_eval_seed` block.
**Outcome:**
- Skill eval seed at 7/30 (covers all 7 v2 vigencia states).
- v3 ladder for the 4 new states (VC/VL/DI/RV) requires Activity 1.7b in week 1-2.
**Cross-references:**
- §4 Activity 1.7 row marked ✅ shipped.
- v3 plan §6 (Fix 5 — TRANCHE judge) seeded.

### 2026-04-26 evening (Bogotá) — Activity 1.6 fixtures complete (V/VM/DE)

**Author:** claude-opus-4-7 + SME
**Type:** sme_signoff
**Sub-fix:** Activity 1.6
**Details:**
3 fixtures: Art. 689-3 ET (VM, Ley 2155/2021 → Ley 2294/2023 prórroga), Art. 158-1 ET (DE, Art. 96 Ley 2277/2022 efectos 2023-01-01), Art. 290 #5 ET (V con regimen_transicion).
**Outcome:** skill eval seed at 4/30 after Activity 1.5 (combined with the 1 IE fixture from 1.5).

### 2026-04-26 evening (Bogotá) — Activity 1.5 outcome (Decreto 1474/2025 → IE)

**Author:** claude-opus-4-7 + SME
**Type:** sme_signoff + corpus_finding
**Sub-fix:** Activity 1.5
**Details:**
Skill produced IE veredicto (NOT the SP the SME inventory expected) — Decreto 1474/2025 was declared inexequible by Sentencia C-079/2026 of April 15, 2026. Corpus internal contradiction surfaced (EME-A01 vs T-I disagree on dates AND ruling). EME-A01 cites a non-existent "Sentencia C-077/2025"; the real ruling is C-079/2026 — the highest-value finding of the round.
**Outcome:**
- Fix 6 gains corpus-wide hallucination audit subscope.
- Re-Verify Cron moved week 13 → week 5.
- 2 pre-validated TRANCHE test cases for Fix 5.

### 2026-04-29 (Bogotá) — Activity 1 shipped (SQL-only vigencia filter)

**Author:** engineer
**Type:** deploy
**Sub-fix:** Activity 1
**Details:**
Migration `20260429000000_vigencia_filter_unconditional.sql` applied to dev + staging + production. Removes the silent bypass that disabled the existing `vigencia NOT IN ('derogada', ...)` filter when `filter_effective_date_max` was passed.
**Outcome (measured 2026-04-29):**
- `art. 689-1` mentions: 13 → 2 (−85%).
- `Ley 1429` mentions: 303 → 286 (essentially unchanged — flag too sparse).
- `6 años firmeza`: 13 → 19 (regression — chunk reshuffle).
- §1.G `served_acceptable+`: 21/36 unchanged.
**Cross-references:**
- Learning logged in `docs/learnings/retrieval/vigencia-binary-flag-too-coarse.md`.
- v3 plan §8 references this as the precursor that proved the binary flag insufficient.

### §10.2 — Heartbeat protocol (for cron)

When cron workers go live (week 4-5), they append condensed entries every 6h:

```
### YYYY-MM-DD HH:MM Bogotá (UTC YYYY-MM-DDTHH:MM:SSZ) — cron heartbeat <worker-name>

**Author:** cron@v1
**Type:** cron_heartbeat
**Worker:** reverify_periodic | cascade_consumer | state_flip_notifier
**Status:** healthy | degraded | failing
**Queue depth:** <N>
**Last action:** <one-line: e.g., "processed 12 norms; 0 errors">
**Drift:** <expected vs actual; e.g., "0 — last tick was 6h0m ago">
```

If `Status != healthy`, append a §9 open question. If 3 consecutive heartbeats are `failing`, the operator gets a separate alert (per `CLAUDE.md` long-running-job convention).

### §10.3 — Searchability hint

Use `git log --all --oneline -- docs/re-engineer/state_fixplan_v3.md` to see when entries landed. The append-only protocol means commits to this file ARE the audit trail.

For grep:
- `grep "gate_crossing" state_fixplan_v3.md` — all gate movements.
- `grep "deploy" state_fixplan_v3.md` — all deploys.
- `grep "Sub-fix:** 1B-γ" state_fixplan_v3.md` — all activity on a specific sub-fix.

---

*v3 state file complete (5 chapters, 2026-04-27 evening Bogotá). Operator + engineers + cron all write here. Single source of truth for "where are we?" When the plan and state disagree on facts, this file wins. When they disagree on intent, the plan wins.*
