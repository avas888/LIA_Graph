## fix_v13_may.md — dedicated práctica retrieval path (mirror Interpretación, simple v1)

> **Drafted 2026-05-13 Bogotá** by claude-opus-4-7. Successor to
> `fix_v12_may.md`. v12 shipped the *visible* artifact
> (Recomendaciones Prácticas first; soft 1.5× boost on
> `knowledge_class='practica_erp'` inside the unified
> `hybrid_search` call). v13 ships the *structural* one: a
> dedicated `practica/` retrieval package mirroring
> `interpretacion/`, with its own database call, its own slot
> budget, and the same quality gates as everything else.
>
> **Audience.** Zero-context fresh LLM or engineer. Self-contained.
> Skim `fix_v12_may.md` to understand the shipped boost mechanism
> v13 will deprecate (kept wired as emergency rollback only). Skim
> `CLAUDE.md` → "Surface Boundaries" — práctica is NOT a new
> sidebar; it is a new dedicated retrieval lane that feeds the
> existing `main chat` Recomendaciones Prácticas section with
> guaranteed real práctica chunks instead of article-derived
> bullets in normative voice.
>
> **What this is.** The smallest credible architectural change
> that answers the operator's question: "Are práctica chunks
> competing with legal chunks for the same slots?" After v13,
> the answer is "no — they have their own retrieval call and
> reserved slots, evaluated by the same quality bar."
>
> **What this is NOT.** Not a trust-tier weighting pass (deferred
> to a future fix; práctica provider taxonomy doesn't exist yet,
> and the v11A Interpretación experiment showed tier-weighting
> at the retriever layer moved the SME panel 0pt — wrong layer).
> Not an LLM rerank judge for práctica (deferred). Not a top-5
> slot budget (start with top-3 matching the section's natural
> bullet count; raise only if validation shows follow-up bubbles
> still read normative-voiced). Not a filesystem fallback for
> offline dev (deferred — see §7). Not a new UI surface — the
> visible answer shape is unchanged from v12.
>
> **Scope guard.** Closing bar at end of Phase 13C, measured on
> `npm run dev:staging` against the 21-Q expert-panel SME
> mini-panel (`evals/sme_validation_v1/21q_retriever_General.jsonl`)
> and the 36-Q regression sweep:
>
> 1. ≥ 80 % of answers carry `response.diagnostics.practica_backend = "supabase"`
>    AND `practica_reserved_count ≥ 1` (i.e., real práctica chunks
>    reached the section, not the article-derived fallback).
> 2. 21-Q expert-panel score **≥ 12/21** (v11A/v12 floor — never regress).
> 3. 36-Q regression sweep score **≥ 21/36** (v12 floor — never regress).
> 4. 5/5 manual SME probes read Recomendaciones Prácticas as
>    operational guidance ("reúne X, liquida con Y, presenta antes
>    de Z"), not normative-voiced bullets ("según el Art. X...").
> 5. No silent fallback: with `LIA_PRACTICA_SOURCE=supabase`, RPC
>    errors propagate as `practica_backend="error"` + the section
>    falls through to today's v12 behavior (article-derived). They
>    never silently mask as `practica_backend="filesystem"`.

---

### §0. Inheritance from v12

Carry forward intact, do not touch:

- **v12.A** — `**Recomendaciones Prácticas**` is the first non-`Respuestas directas` heading
  (`pipeline_d/answer_first_bubble.py:106–113`).
- **v12.B** — `build_recommendations` call chain
  (`pipeline_d/answer_synthesis_sections.py:37–98`,
  → `extend_from_guidance(lines, "recommendation", primary_articles)` line 89,
  → `extend_from_guidance(lines, "recommendation", connected_articles)` line 90,
  → `fallback_recommendation(...)` lines 91–97). v13 adds a new
  input source at the head of this chain; it does not replace the
  existing extraction.
- **v12.C** — `knowledge_class_boost` + `boost_knowledge_class` RPC
  parameters in `hybrid_search`
  (`supabase/migrations/20260513000001_knowledge_class_boost.sql:59–60, 269–282`).
  v13 keeps the SQL parameters wired. The Python caller defaults
  to `1.0` (off) after v13, but the parameter remains a one-flag
  rollback path.
- **fix_v10_may.A** — `supabase_sink.write_chunks` inherits
  `knowledge_class` from the parent doc; the 1,463 cloud
  `practica_erp` chunks are correctly tagged. No corpus work needed.
- **fix_v10_may.B** — the dispatcher pattern in the orchestrator
  on `LIA_INTERPRETATION_SOURCE`
  (`interpretacion/orchestrator.py:136–254`). v13 replicates this
  shape for `LIA_PRACTICA_SOURCE`.

---

### §1. Diagnosis — what v12 left on the table

v12's 1.5× soft boost is a **tiebreaker, not a guarantee**. Four
gaps it cannot close:

1. **Strong normative still wins.** A dense `normative_base` chunk
   with high RRF base score outranks a `practica_erp` chunk even
   after the 1.5× multiplier. On topics with thick legal coverage
   (renta, retención), práctica chunks never reach
   `primary_articles`.
2. **`build_recommendations` is class-agnostic.**
   (`pipeline_d/answer_synthesis_sections.py:46–98`) The section
   extracts the `"recommendation"` guidance field from any primary
   article — regardless of `knowledge_class`. When práctica chunks
   don't rank into `primary_articles`, the section transparently
   falls back to extracting recommendation text from
   normative-voiced article guidance. This IS the failure mode v12
   was trying to fix.
3. **No diagnostic visibility.** There is no key today that says
   "this turn's Recomendaciones Prácticas was fed by real práctica
   corpus vs the article-derived fallback." An engineer must read
   chunk text manually to know whether v12 is working.
4. **Fixed shared budget.** The unified `hybrid_search` returns a
   fixed `match_count`. Whatever knowledge classes win the
   ranking, divide the budget. A normative-dense topic starves
   práctica to zero.

The structural answer — explicitly deferred in v12's "What this is
not" section — is a dedicated práctica retrieval lane with its own
budget. v13 ships exactly that, in the simplest form.

---

### §2. Target architecture (after v13)

Two parallel retrieval lanes per chat turn:

```
              ┌─────────────────────────────────────────┐
   user Q ──▶ │ pipeline_d/orchestrator.py              │
              │                                         │
              │  ┌─ unified retrieval (existing) ──┐    │
              │  │ pipeline_d/retriever_supabase   │    │
              │  │ → hybrid_search (no kc filter)  │    │
              │  │   normative + interpretative +  │    │
              │  │   práctica into one pool        │    │
              │  │   v12 boost: default 1.0 (off)  │    │
              │  └─────────────────────────────────┘    │
              │                                         │
              │  ┌─ NEW dedicated práctica lane ───┐    │
              │  │ practica/retriever_supabase.py  │    │
              │  │ → hybrid_search                 │    │
              │  │   filter_kc='practica_erp'      │    │
              │  │   filter_topic_boost=1.5        │    │
              │  │   top-K = 3 (env-overridable)   │    │
              │  └─────────────────────────────────┘    │
              │                                         │
              │  Merge: práctica top-3 reserved into    │
              │  build_recommendations input; normative │
              │  continues to feed Anclaje Legal.       │
              │  Same quality gates on both lanes.      │
              └─────────────────────────────────────────┘
```

Behavior contract:

- Práctica lane runs every turn when `LIA_PRACTICA_SOURCE=supabase`
  (default for staging + production).
- Práctica candidates pass through the **same** vigencia demotion,
  topic gate, citation allow-list, and coherence gate as today's
  unified pool. No exemptions.
- The top `LIA_PRACTICA_RESERVED_SLOTS` (default 3) surviving
  chunks are passed to `build_recommendations` as a new
  highest-priority input source, *before* the existing
  `extend_from_guidance(... primary_articles)` extraction.
- If fewer than 3 práctica chunks survive gates, the section
  fills the rest from the existing v12 fallback chain. No
  regression vs v12 in the empty-corpus case.
- RPC errors on the práctica lane DO NOT short-circuit the unified
  lane. `practica_backend="error"` is set; the section falls
  through to v12 behavior.

---

### §3. Phase 13A — scaffold + retriever (no behavior change)

**Goal.** Add the `practica/` package and a unit-tested retriever.
Do not wire it into the orchestrator yet.

**Files to create (mirror `interpretacion/` shape; smaller):**

- `src/lia_graph/practica/__init__.py` — package marker, no exports.
- `src/lia_graph/practica/shared.py` — dataclasses:
  `PracticaChunkRuntime` (doc_id, relative_path, source_label,
  authority, chunk_text, retrieval_score, knowledge_class,
  citation refs); `PracticaKnowledgeBundle` (`chunks_selected:
  tuple[PracticaChunkRuntime, ...]`, `retrieval_diagnostics: dict`).
  Mirror `interpretacion/shared.py` but trimmed — no
  `ExpertPanelSurface`, no `InterpretationCard`.
- `src/lia_graph/practica/policy.py` — constants:
  `DEFAULT_RESERVED_SLOTS = 3`, `DEFAULT_TOPIC_BOOST = 1.5`,
  `MATCH_COUNT_MULTIPLIER = 4`, `MIN_MATCH_COUNT = 24`. Read
  `LIA_PRACTICA_RESERVED_SLOTS` env override.
- `src/lia_graph/practica/retriever_supabase.py` — **the core
  module**. Mirror `interpretacion/retriever_supabase.py:347–514`
  with these specifics:
  - Function `fetch_practica_candidates(*, query_seed, topic,
    pais='colombia', top_k=3, client=None) -> PracticaKnowledgeBundle`.
  - FTS query construction: reuse the tokenizer pattern from
    `interpretacion/retriever_supabase.py:84–116` (extract
    common helper later if duplicated; do not pre-extract).
  - Hybrid search payload: `filter_knowledge_class='practica_erp'`
    (hard filter), `filter_pais=pais`, `boost_topic=topic`,
    `filter_topic_boost=1.5`, `match_count=max(top_k*4, 24)`.
    Do NOT pass `knowledge_class_boost` (this lane already
    filtered to práctica; the boost is for soft tiebreaks in
    mixed pools).
  - Chunk grouping: per `doc_id`, keep highest-scoring chunk.
    Reuse the simpler grouping pattern from
    `interpretacion/retriever_supabase.py:211–269` minus
    trust-tier (skipped per §7 future work) and minus
    `article_refs` lexical boost (not relevant for práctica).
  - Diagnostics emitted: `practica_backend="supabase"`, `mode`,
    `candidate_rows`, `selected_chunks`, `embedding_mode`,
    `fts_query_present`, `topic_boost`.
  - Error contract: RPC exceptions propagate. Caller decides
    fallback. No try/except swallowing.

**Tests to add (mirror `tests/test_interpretacion_retriever_supabase.py`):**

- `tests/test_practica_retriever_supabase.py`
  - `test_payload_knowledge_class_filter` — asserts payload has
    `filter_knowledge_class='practica_erp'` and no
    `knowledge_class_boost`.
  - `test_payload_topic_boost_conditional` — asserts
    `boost_topic` is set only when topic provided.
  - `test_group_picks_highest_chunk_per_doc` — happy path.
  - `test_group_handles_empty_rows` — zero results returns
    empty bundle with diagnostics.
  - `test_fetch_returns_runtime_shape` — DocumentRecord-ish
    shape with required fields.
  - `test_fetch_propagates_rpc_error` — RPC error bubbles out;
    no silent return.
  - `test_top_k_respected` — bundle.chunks_selected length ≤
    `LIA_PRACTICA_RESERVED_SLOTS`.

**Definition of done for 13A:**
`PYTHONPATH=src:. uv run pytest tests/test_practica_retriever_supabase.py -q` passes.
No production code path imports the new package yet. `git diff` shows
only additions under `src/lia_graph/practica/` + the new test file.

---

### §4. Phase 13B — orchestrator dispatch + section wire-up (behavior change)

**Goal.** Wire the práctica lane into the chat hot path so the
Recomendaciones Prácticas section is fed by real `practica_erp`
chunks.

**Edits (narrow, granular — do not collapse modules):**

1. **`src/lia_graph/pipeline_d/orchestrator.py`** — add
   `_retrieve_practica_chunks(*, query, topic, pais, top_k)` as a
   thin dispatcher mirroring `interpretacion._retrieve_interpretation_docs`
   (`interpretacion/orchestrator.py:136–254`):
   - Read `LIA_PRACTICA_SOURCE` (default `"supabase"`).
   - If `"supabase"`: call `practica.retriever_supabase.fetch_practica_candidates(...)`.
   - If `"disabled"`: return empty bundle (`practica_backend="disabled"`).
   - If `"filesystem"`: raise `NotImplementedError` (deferred — §7).
   - On RPC exception: log + return empty bundle with
     `practica_backend="error"` + `practica_error_kind=<class name>`.
     Do NOT silently fall through to `"filesystem"`.
   - Invocation site: in the function that today builds the
     `GraphEvidenceBundle` (around `retriever_supabase.retrieve_graph_evidence`
     call). Run after the unified retrieval; pass the same `topic`
     and `pais`.

2. **`src/lia_graph/pipeline_d/answer_synthesis_sections.py`** —
   modify `build_recommendations(...)` signature and body:
   - Add new first parameter `practica_chunks:
     tuple[PracticaChunkRuntime, ...] = ()`.
   - At line 46 (before the existing `extend_from_support_insights`
     call), insert: extract operational guidance bullets from
     `practica_chunks` via a new helper
     `extend_from_practica_chunks(lines, practica_chunks)` in a new
     sibling file `pipeline_d/answer_synthesis_practica.py`
     (per `feedback_granular_edits.md` — do not bloat the existing
     section file).
   - Keep the rest of the chain unchanged. If
     `extend_from_practica_chunks` fills the section to capacity
     (e.g., 3 lines), the downstream extractors no-op naturally
     via the existing dedup/cap logic at line 98.

3. **`src/lia_graph/pipeline_d/answer_synthesis_practica.py`** —
   new file. Implements `extend_from_practica_chunks(lines: list[str],
   chunks: tuple[PracticaChunkRuntime, ...]) -> None`. Each chunk
   contributes at most one bullet, extracted from its top-ranked
   text via the existing sentence-trim helpers in
   `answer_synthesis_helpers.py`. No new prose synthesis logic —
   pull the existing helpers; do not duplicate.

4. **`src/lia_graph/pipeline_d/answer_synthesis.py`** (the facade) —
   thread `practica_chunks` through `compose_main_chat_answer` into
   `build_recommendations`. The facade signature gains one optional
   parameter; orchestrator passes it; assembly modules
   (`answer_first_bubble.py`, `answer_followup.py`) consume the
   same `GraphNativeAnswerParts.recommendations` tuple they do
   today — no change to assembly. The práctica content reaches
   them through the upstream wire only.

5. **Apply the same quality gates to práctica chunks before they
   reach `build_recommendations`:**
   - **Vigencia demotion** — call
     `pipeline_d/vigencia_demotion._apply_v3_vigencia_demotion`
     on práctica chunks the same way the unified pool does
     (`pipeline_d/retriever_supabase.py:758–834`). Demoted chunks
     drop to factor 0.0 → filtered out before `build_recommendations`.
   - **Topic gate** — feed práctica bullets through
     `pipeline_d/answer_topic_gate.py` the same way unified
     bullets are gated.
   - **Citation allow-list** — práctica chunks that cite norms
     pass the allow-list check at the bullet-render layer (this
     happens naturally if we feed through the existing assembly
     path).

**No changes to:**
- `interpretacion/` — completely independent surface.
- `supabase/migrations/` — the migration from v12 already exposes
  the parameters práctica retrieval needs; práctica's hard
  `filter_knowledge_class` was added in the same migration.
- The v12 `LIA_PRACTICA_BOOST_FACTOR` env flag plumbing — kept
  intact for §5 default flip.

**Definition of done for 13B:**
- `npm run test:health:fast` passes.
- A single dev:staging probe via the `answer-engine-probe` skill on
  a known-good práctica-corpus topic (e.g., a retención query that
  has práctica chunks in the 1,463-row backfill) returns
  `response.diagnostics.practica_backend="supabase"` and
  `practica_reserved_count ≥ 1`.
- The same probe's Recomendaciones Prácticas bullets read
  operational, not normative.

---

### §5. Phase 13C — observability, flag default flip, SME validation

**Goal.** Make the new lane visible to operators + validate end-to-end.

**Edits:**

1. **`src/lia_graph/ui_chat_payload.py`** — whitelist the new
   diagnostic keys (mirror the `interpretation_backend` whitelist
   at `ui_chat_payload.py:76–85`):
   - `practica_backend` ∈ `{"supabase", "disabled", "error"}`
   - `practica_candidate_count` (int)
   - `practica_reserved_count` (int, ≤ `LIA_PRACTICA_RESERVED_SLOTS`)
   - `practica_error_kind` (str, only present when `backend="error"`)

2. **`src/lia_graph/tracers_and_logs/pipeline_trace.py`** — emit
   three new stages from `practica/retriever_supabase.py`:
   - `practica_retrieve.in` — query, topic, top_k.
   - `practica_retrieve.out` — candidate_rows, embedding_mode.
   - `practica_quality_gate` — kept/dropped counts after vigencia +
     topic gate.
   - `practica_merge` — final reserved_count entering
     `build_recommendations`.

3. **`scripts/dev-launcher.mjs`** — env matrix:
   - `LIA_PRACTICA_SOURCE`: `"supabase"` for `dev:staging` +
     `dev:production`; `"disabled"` for `npm run dev` until a
     filesystem fallback ships (§7).
   - `LIA_PRACTICA_RESERVED_SLOTS`: `"3"` across all modes.
   - **Flip `LIA_PRACTICA_BOOST_FACTOR` default from `"1.5"` to
     `"1.0"`** across all modes (off; emergency rollback only —
     set to `"1.5"` in shell env to reinstate the v12 soft boost
     mechanism).

4. **`docs/orchestration/orchestration.md`** — bump env-matrix
   version to v2026-05-13-fix-v13-practica-lane. Add a change-log
   row referencing this plan. Update the mirror tables in
   `docs/guide/env_guide.md`, `CLAUDE.md` "Runtime Read Path", and
   the `/orchestration` status card
   (`frontend/src/features/orchestration/orchestrationApp.ts`).

5. **SME validation gate (operator-triggered, per
   `feedback_sme_panel_explicit_request_only.md`).** After 13A+13B
   merge to main and 13C observability lands, ASK the operator
   before running:
   - 21-Q expert-panel mini-panel:
     `scripts/eval/run_sme_parallel.py --questions evals/sme_validation_v1/21q_retriever_General.jsonl --workers 4`
   - 36-Q regression sweep: same script with the regression file.
   - Cross-reference the diagnostic spine: count answers where
     `practica_backend="supabase"` AND `practica_reserved_count ≥ 1`.
     Pass the §Scope-guard 80 % threshold or refine per gate 6.

**Definition of done for 13C:**
All scope-guard criteria (1)–(5) met. Plan file updated with the
panel numbers in a "Landed" section at the bottom.

---

### §6. Six-gate lifecycle (per `feedback_verify_fixes_end_to_end.md`)

| Gate | State | Evidence |
|---|---|---|
| 1. Idea | ✅ stated | "Práctica chunks compete with legal for the same slots today; give them their own lane." |
| 2. Plan | ✅ this doc | Narrowest modules: new `practica/` package + `_retrieve_practica_chunks` dispatcher + one new sibling synthesis helper. Existing surfaces untouched. |
| 3. Success criterion | ✅ §Scope guard | 5 measurable criteria; floors: 21-Q ≥ 12/21, 36-Q ≥ 21/36; new lever: ≥ 80 % `practica_backend=supabase` + `reserved_count ≥ 1`. |
| 4. Test plan | ✅ §3, §4, §5 | Engineer: unit tests + `test:health:fast`. Operator: dev:staging probe via `answer-engine-probe`. SME: 21-Q + 36-Q panels on explicit request. End-user: 5 manual probes against staging UI. Decision rule: §Scope guard. |
| 5. Greenlight | ⏳ pending | Requires BOTH `test:health:fast` green AND staging probe showing `practica_backend=supabase` AND 5/5 SME manual reads passing. |
| 6. Refine-or-discard | ⏳ pending | If 21-Q regresses below 12/21 → roll back via `LIA_PRACTICA_BOOST_FACTOR=1.5` + `LIA_PRACTICA_SOURCE=disabled` (one-flag rollback). Diagnose pattern (which topics regress) before re-attempting. If qualitative ceiling shows real práctica chunks land but feel low-quality → escalate to §7 trust-tier follow-up. If follow-up bubbles still read normative-voiced → escalate to top-5 budget. |

---

### §7. Out of scope — explicitly deferred to future fixes

Each item below is an independent improvement that can land on top
of v13's structural change. Listed in rough order of expected
value:

- **v14 trust-tier weighting for práctica.** Requires curating a
  práctica-provider taxonomy (DIAN cartillas, Actualícese práctica,
  Gerencie.com, vendor blogs, etc.) → expand
  `config/provider_trust_tiers.json` or add a sibling. Then add
  the `trust_tier_weight` lever to
  `practica/retriever_supabase.py` mirroring Phase 11A
  (`interpretacion/retriever_supabase.py:258–261`). **Defer until
  v13 ships and we know the qualitative ceiling.** v11A
  Interpretación experiment showed tier-weighting alone moved the
  panel 0 pt — wrong layer when section assembler is the
  bottleneck. Re-evaluate once we see where v13 falls short.
- **v14+ LLM rerank judge for práctica.** Mirror
  `interpretacion/rerank/`. Adds a Claude call per turn (latency +
  spend). Only build if v13 + trust tiers leave specific
  semantic-mismatch failures on the SME panel.
- **v14+ raise reserved slots to 5.** Lets the práctica lane feed
  `Procedimiento Sugerido` and `Precauciones` in follow-up bubbles
  (`answer_followup.py:277–290`), not just the first-bubble
  Recomendaciones Prácticas. Cheap flag flip if §Scope guard (4)
  qualitatively flags follow-up bubbles as still normative-voiced.
- **v14+ filesystem fallback (`practica/catalog.py`)** for
  `npm run dev` offline parity. Mirror `interpretacion/catalog.py`.
  Not blocking — `LIA_PRACTICA_SOURCE=disabled` in offline mode
  matches today's behavior (no práctica boost when offline).
- **v14+ retire `LIA_PRACTICA_BOOST_FACTOR` entirely.** Drop the
  `knowledge_class_boost` payload parameter from
  `pipeline_d/retriever_supabase.py` and the SQL parameter from
  `hybrid_search`. Safe only after v13 has run in production
  long enough to retire the rollback path (suggest ≥ 4 weeks).

---

### §8. Verification — how to test end-to-end

**Engineer-side (before each phase merges):**

- `PYTHONPATH=src:. uv run pytest tests/test_practica_retriever_supabase.py -q`
- `npm run test:health:fast` (full health minus e2e)
- A focused dev:staging probe via the `answer-engine-probe` skill
  on a known práctica-bearing topic (e.g., a retención-en-la-fuente
  question with `practica_erp` chunks in the cloud backfill).
  Verify:
  - `response.diagnostics.retrieval_backend == "supabase"`
    (existing).
  - `response.diagnostics.practica_backend == "supabase"` (new).
  - `response.diagnostics.practica_candidate_count > 0` (new).
  - `response.diagnostics.practica_reserved_count >= 1` (new).
  - `tracers_and_logs/logs/pipeline_trace.jsonl` includes the
    `practica_retrieve.*` + `practica_quality_gate` +
    `practica_merge` stages (new).
  - Recomendaciones Prácticas section reads operational, not
    "según el Art. X..." normative.

**Operator-side (after 13C lands; explicit request only per
`feedback_sme_panel_explicit_request_only.md`):**

- 21-Q expert-panel SME mini-panel via
  `scripts/eval/run_sme_parallel.py`.
- 36-Q regression sweep.
- Diagnostic aggregation: count `practica_backend=supabase` and
  `practica_reserved_count ≥ 1` ratios; compare to §Scope-guard
  threshold (1).

**SME-side (after operator panel):**

- 5 manual probes by a domain expert (contador) against the
  staging UI, comparing the same questions pre-v13 / post-v13.
  Verify the Recomendaciones Prácticas section reads as
  operational guidance at the layer an accountant experiences.

**End-user-side:**

- Visual UAT in staging at the answer surface; spot-check across
  topic mix (renta, retención, IVA, nómina, beneficios).

**Rollback recipe (one flag flip, no redeploy):**

```
LIA_PRACTICA_SOURCE=disabled              # turn off new lane
LIA_PRACTICA_BOOST_FACTOR=1.5             # re-enable v12 soft boost
```

This reverts the runtime to v12 behavior. Code stays in repo for
follow-up diagnosis.

---

### §9. Critical files to modify

```
New:
  src/lia_graph/practica/__init__.py
  src/lia_graph/practica/shared.py
  src/lia_graph/practica/policy.py
  src/lia_graph/practica/retriever_supabase.py
  src/lia_graph/pipeline_d/answer_synthesis_practica.py
  tests/test_practica_retriever_supabase.py

Modified (narrow edits only):
  src/lia_graph/pipeline_d/orchestrator.py
    + _retrieve_practica_chunks dispatcher
    + invocation alongside the unified retrieval call
    + diagnostic key emission
  src/lia_graph/pipeline_d/answer_synthesis_sections.py
    ~ build_recommendations gains practica_chunks param
    ~ calls extend_from_practica_chunks at the head of the chain
  src/lia_graph/pipeline_d/answer_synthesis.py
    ~ compose_main_chat_answer threads practica_chunks through
  src/lia_graph/ui_chat_payload.py
    + whitelist practica_backend, practica_candidate_count,
      practica_reserved_count, practica_error_kind
  src/lia_graph/tracers_and_logs/pipeline_trace.py
    + practica_retrieve.{in,out} + practica_quality_gate +
      practica_merge stage names
  scripts/dev-launcher.mjs
    ~ LIA_PRACTICA_SOURCE + LIA_PRACTICA_RESERVED_SLOTS defaults
    ~ flip LIA_PRACTICA_BOOST_FACTOR default 1.5 → 1.0
  docs/orchestration/orchestration.md
    ~ env matrix bump + change log row
  docs/guide/env_guide.md
    ~ mirror env matrix
  CLAUDE.md
    ~ mirror in "Runtime Read Path" section + Fast Decision Rule
  frontend/src/features/orchestration/orchestrationApp.ts
    ~ orchestration map status card
```

Net new code is small. The structural change lives in two new
files (`practica/retriever_supabase.py` + the synthesis sibling)
and one new dispatcher function. Everything else is wiring +
diagnostics + doc-parity.
