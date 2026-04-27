# next_v5 — forward plan opened 2026-04-26

> **Opened 2026-04-26** as the live forward-facing surface after `next_v4.md` accumulated the gate-9 qualitative-pass debt + the 2026-04-25/26 ship cycle (conversational-memory staircase L1+L2, comparative-regime mode, 100-Q gauge, parity-probe diagnostic).
>
> v4 stays in this folder as the **record of what was done in that cycle**. Active work — anything still 💡 idea, 🛠 awaiting verification, or with an open success-criterion measurement — lives here. v5 also carries one new investigation surfaced 2026-04-26: retrieval-depth envelope calibration (§7).
>
> **Policy (carries from v3/v4).** Six-gate lifecycle per `docs/aa_next/README.md`: 💡 idea → 🛠 code landed → 🧪 verified locally → ✅ verified in target env → ↩ regressed-discarded. **Every step's gate-3 success criterion must be measured, not asserted.** Unit-tests-green ≠ improvement.

---

## §1 Coherence-gate calibration diagnostic — ✅ Phase 1+2 complete 2026-04-26

**Status:** ✅ **diagnostic complete in target environment 2026-04-26.** Phase 1 (thin-corpus inventory) + Phase 2 (cross-topic dependency) both ran against staging cloud. Decision: **HYBRID — multi-topic ArticleNode metadata + chunk-precedence on retrieval.**

### Findings (binding, with numbers)

- **89 registered topics**; **12 are thin-corpus** (chunks ≥ 10, native_articles < 5) → **13,5% structural risk surface**.
- **12/12 thin-corpus topics show 100% cross-topic dependency** — every single one has its primary article references owned by OTHER topics.
- **16 distinct cross-topic owners**, but **top 5 carry 74% of mentions** (Pareto). The strict-threshold verdict says "distributed"; the empirical shape is concentrated enough for a bounded curation effort.
- **FIRMEZA anomaly**: `firmeza_declaraciones` is healthy by Phase-1 metrics (12 native articles post-FIR-N02 ingest) yet the chat still refuses. Root cause traced to **chunk-level cross-topic mix** (legacy chunks from `09_Libro1_T1_Caps8a11.md` tagged `declaracion_renta` compete with new FIR-N02 chunks tagged `firmeza_declaraciones` in hybrid_search). Article-level metadata alone is insufficient.

Full numbers + samples + per-topic article tables: [`docs/learnings/ingestion/coherence-gate-thin-corpus-diagnostic-2026-04-26.md`](../learnings/ingestion/coherence-gate-thin-corpus-diagnostic-2026-04-26.md).

### Recommended fix path — opens §1.A and §1.B

**§1.A — Multi-topic ArticleNode metadata (🛠 code landed 2026-04-26)**

Status: structural plumbing shipped + 82 tests green. Awaiting (a) re-ingest to write `secondary_topics` props on existing :ArticleNodes, (b) operator-authorized expansion of the seed config from the 1 entry (Art. 689-3) to the SME-validated mapping in `taxonomy_v2_sme_response.md §1.4`.

Code surface:
- `config/article_secondary_topics.json` — curation config (seed: 1 entry).
- `src/lia_graph/ingestion/article_secondary_topics.py` — lookup module with taxonomy validation + degrade-to-empty on errors.
- `src/lia_graph/graph/schema.py` — `secondary_topics` declared on `:ArticleNode.optional_fields`.
- `src/lia_graph/ingestion/loader.py` — writes `secondary_topics` prop at MERGE time.
- `src/lia_graph/pipeline_d/contracts.py::GraphEvidenceItem` — carries the field through retrieval.
- `src/lia_graph/pipeline_d/retriever_falkor.py` — pulls the prop in primary_articles query.
- `src/lia_graph/pipeline_d/topic_safety.py::detect_topic_misalignment` — short-circuits BEFORE lexical scoring when `router_topic ∈ primary.secondary_topics`.

What's pending (gate 4b):
1. Re-ingest the prose-only FIRMEZA trilogy + at least one numbered-article doc that touches Art. 689-3 (e.g., NORMATIVA_FIR-N02 already in cloud) so the new `secondary_topics` prop lands on the ArticleNode.
2. Re-ask the firmeza+beneficio chat question. Pre-§1.A: refused with `pipeline_d_coherence_primary_off_topic`. Post-§1.A: should pass `secondary_topic_match` and serve the answer.
3. Operator authorizes seed-config expansion from 1 entry to the ~30-50 SME-validated mappings.

Lessons captured: `docs/learnings/ingestion/coherence-gate-thin-corpus-diagnostic-2026-04-26.md` "v5 §1.A implementation — lessons" section (L1-L6). Sibling pattern cross-referenced from `docs/learnings/ingestion/path-veto-rule-based-classifier-correction.md`.

**§1.B — Chunk-precedence on hybrid_search (FIRMEZA case, ~2-3 days)**
- When a new doc covers articles already chunked under another topic, decide which chunk set takes retrieval precedence. Three options scoped in the learnings doc.
- Implementation choice depends on Phase-1.B investigation (~1 day): how often does this dilution actually fire vs the article-mapping case?

### What this rules OUT (binding)

- **Pure curation without metadata changes** — would be unbounded across the ET's umbrella topics.
- **Lowering the coherence-gate threshold** — `feedback_thresholds_no_lower`.
- **Disabling cross-topic refusal entirely** — re-introduces Q1-class contamination guard.

### Original (now-superseded) plan

The original v4 §1 plan focused on the 11 `coherence_misaligned=True` questions from gate-9. That fixture is still useful for §1.B verification but no longer drives §1's decision — Phase 1+2 measurements gave a more definitive answer at the structural level. The 11-Q fixture survives as a regression check after §1.A + §1.B ship.

### Effort summary

- §1.A: 3-5 days (schema + loader + SME curation + verification).
- §1.B: 2-3 days (investigation + implementation + verification).
- Total: ~5-8 days serialized; some parallelism possible if SME curation runs alongside the §1.B investigation.

---

## §2 v3 §10 carries (still-pending track)

These do not block re-flip but ship in this cycle when there's bandwidth. Removed entries that completed in v4. **Still pending:**

- **§10.1 TokenBudget primitive** — wire `TokenBudget` + `TPMRateLimitError` into `ingest_classifier_pool`. Lets `LIA_INGEST_CLASSIFIER_WORKERS` go back to 8 against production. ~4-6 hr code + cloud verify.
- **§10.2 Persistent verdict cache** — SQLite-keyed cache for classifier verdicts. Drops idempotent rebuilds from ~7 min → < 60 s. ~2 days.
- **§10.3 Gold v2 expansion** — ≥ 10-15 additional SME-commissioned questions. ~1-2 weeks SME.
- **§10.4 Subtopic taxonomy refresh** — v2.1 SME pass on subtopics under `impuesto_timbre`, `rut_y_responsabilidades_tributarias`. ~0.5 day SME + 0.5 day code.
- **§10.5 Corpus expansion** — fill the 11 `corpus_coverage: pending` top-level topics from canonical sources. ~2-4 weeks SME + content team. **§1 above may surface specific topics that need expansion regardless of their pending/active flag.**

---

## §3 Conversational-memory staircase — Level 2 verification + Level 3 reopen conditions (carried from v4 §3+§4)

**Status:** 🛠 code landed 2026-04-25 (Level 1 + Level 2 shipped). 🧪 verified locally via 13 unit tests. **Awaiting target-env harness measurement** — that's why this is in v5.

### What's already done (v4 record)
- **Level 1 (FE topic propagation):** `frontend/src/features/chat/requestController.ts:230-243` — forwards `payload.topic = lastTurnEffectiveTopic` when prior assistant turn anchored a topic. Shipped.
- **Level 2 (`ConversationState` extension + classifier prior):** `conversation_state.py` (4 new fields), `topic_router.py` (prior-topic tiebreaker, `_classify_topic_with_llm` accepts `conversation_state`), `ui_chat_payload.py` (early `load_session` peek). Shipped.
- **Harness:** `scripts/evaluations/run_multiturn_dialogue_harness.py` + `evals/multiturn_dialogue_v1.jsonl` (10 ambiguous-verb dialogues) — built but not yet run.

### What's pending in v5

#### Gate 4-5 verification (binding)
Run the multi-turn harness against staging cloud (`LIA_CORPUS_SOURCE=supabase`, `LIA_GRAPH_MODE=falkor_live`, `LIA_EVIDENCE_COHERENCE_GATE=enforce`). Decision rule unchanged from v4 §4 Level 2: refusal rate via `primary_off_topic` ≤ 5% AND contamination rate ≤ baseline AND SME (Alejandro) no-regression verdict on 5-8 spot-cases.

- **Engineer:** posts harness output + diagnostics summary.
- **Operator:** triggers run with staging credentials.
- **SME:** ~30 min spot-review of 5-8 multi-turn dialogues.

#### Conditions to reopen Level 3 (binding)
Free-text rolling summary stays deferred unless **all three** trigger:
1. Level 2 ships AND multi-turn harness shows refusal > 15% on 5+ turn dialogues.
2. SME identifies ≥ 3 distinct cases where structured state demonstrably could not have captured what was needed.
3. Operator opens a v5 §X with a six-gate plan that includes an **anti-drift measurement harness BEFORE any code is written**.

Estimated effort if reopened: ~2-3 weeks (summarization subsystem + anti-drift harness + staging iteration).

---

## §4 Comparative-regime planner mode — SME validation + pair-config expansion (carried from v4 §5)

**Status:** 🧪 verified locally 2026-04-25 — implementation landed (`pipeline_d/answer_comparative_regime.py`, `config/comparative_regime_pairs.json`, planner detection at `planner.py:279-310`, orchestrator fan-out suppression, polish-prompt rule). One regime pair config'd: `perdidas_fiscales_2017` (Art. 147 ↔ Art. 290 #5).

### What's pending in v5

1. **SME end-to-end validation of the binding case** — run the original 3-turn dialogue against staging post-deploy. Alejandro reads the third turn, marks pass/fail on whether a senior contador would consider the table format + verdict + 3+ ET citations operative. **This is the gate-5 greenlight.**
2. **Pair-config expansion** — add at least 2 more entries (e.g., depreciación 137-140 ↔ Art. 290 #1-2; tarifa renta 240 ↔ Ley 2277/2022 transitions) to validate generality of the table renderer.
3. **Cue-detector tuning** — if SME flags false positives or missed comparative cases during validation, narrow/widen `_looks_like_comparative_regime_case` cues.

Effort: 0.5d SME + iteration; ~0.5d for additional pair configs (config-only change).

---

## §5 100-Q quality gauge — first baseline + judge spot-check (carried from v4 §6)

**Status:** 🛠 code landed 2026-04-26 (`scripts/run_100qs_eval.py` + `scripts/judge_100qs.py`). 🧪 partially verified — offline checks pass, runner smoke 3/3 OK against `localhost:8787` dev mode. **Live judge run blocked on `ANTHROPIC_API_KEY`.**

### What's pending in v5

#### §5.1 First baseline (the actual measurement)
Once `ANTHROPIC_API_KEY` is available:
1. **Dev artifact baseline.** `npm run dev` → `run_100qs_eval.py --tag dev_baseline` (~15-20 min) → `judge_100qs.py --run-file …` (~$2-4 USD; ~15-20 min). Commit `__summary.json` to `evals/runs/`.
2. **Staging cloud baseline.** Same against `npm run dev:staging`. Commit summary.
3. **Spot-validate the judge.** Operator/SME picks 5-10 lowest-scoring questions from each summary and reads them independently against Lia's actual answer. ≥ 80% agreement → judge is trustworthy. < 80% → refine `judge_system_prompt` first (gate 6).

#### §5.2 `summary_diff.py` (only if §5.1 produces actionable spread)
Build only when dev/staging differ by > 3pp macro or ≥ 1 dimension diverges by > 0.05.

### What this is NOT (binding, carried from v4)
Not a head-to-head Claude-with-web baseline. Not a per-topic statistical claim. Not a substitute for `make eval-c-gold`. Not a release gate (`pass_threshold_percent: 75.0` is aspirational; record exception per case, never relax — `feedback_thresholds_no_lower`).

Effort: 1 day operator (the two runs + spot-checks + commit).

---

## §1.C Open difficulties from §1.A + §1.B deployment (catalogued 2026-04-26 evening)

> **Reason for cataloging in detail.** §1.A + §1.B shipped end-to-end on 2026-04-26 and unblocked **8 of 12 thin-corpus topics** in the chat. The 4 remaining topics refuse for distinct structural reasons that aren't obvious from the code. This section captures every failure mode + every attempted fix + every hypothesis for the next attempt, so we don't forget the dead ends and re-walk them.
>
> **Status:** 💡 idea — open, blocked on understanding the retrieval pipeline at runbook-level depth (in progress as `docs/orchestration/` 2026-04-26).

### The 4 stuck topics — by failure mode

#### Topic 1 — `precios_de_transferencia` → `pipeline_d_coherence_primary_off_topic`

**What's failing.** The router routes correctly to `precios_de_transferencia`. The planner pulls primary articles from Falkor. The lexical-scoring inside `detect_topic_misalignment` scores those articles' titles+excerpts against topic keywords, and the lexical winner is **NOT** `precios_de_transferencia`.

**Why §1.A's short-circuit didn't fire.** §1.A short-circuits when `router_topic ∈ primary_article.secondary_topics`. Currently `Art. 260-5` has `secondary_topics=["firmeza_declaraciones"]` — does NOT include `precios_de_transferencia` because the SME-validated mapping was a) Art. 260-5's canonical owner is precios; b) it ALSO serves firmeza. The reverse direction (some other article whose canonical owner is firmeza or declaracion_renta but which is the canonical for precios queries) hasn't been curated.

**Attempted fix.** None yet specifically for this. §1.A seed didn't add a precios entry beyond Art. 260-5.

**Hypothesis for next attempt.** Curate canonical precios articles with `secondary_topics=["precios_de_transferencia"]` — Art. 260, 260-1, 260-2, 260-3, 260-7, 260-9 etc. Per `pt_normativa_precios_transferencia.md` (728 lines covering 260-1 through 260-11), all 11 should probably have precios as a secondary if their primary owner doc is something else (e.g., declaracion_renta umbrella). Empirical check: query Falkor for `MATCH (a:ArticleNode) WHERE a.article_id STARTS WITH '260' RETURN a.article_id, a.source_path, a.secondary_topics` to see which need curation.

**Risk of fix.** Low — adding `precios_de_transferencia` as secondary to articles that genuinely cover precios topics is curation, not relaxation.

#### Topic 2 — `regimen_cambiario` → `pipeline_d_coherence_chunks_off_topic`

**What's failing.** Hybrid_search returns 5 support_documents. Diagnostic shows `topic_key_matches: 1`, `dominant_topic: retencion_fuente_general`, `top_lexical_score: 8`. The narrow topic has 6 docs in Supabase but hybrid_search ranks them below 4 retencion-tagged chunks for this query.

**Why §1.B didn't fire.** §1.B's `compatible_doc_topics` config initially had `regimen_cambiario → ["cambiario"]`, but `cambiario` is NOT a registered topic in `topic_taxonomy.json` — only `regimen_cambiario` is. The Supabase docs that show up as the hybrid_search winners are tagged with `retencion_fuente_general`, an umbrella retention topic that's NOT a SME-validated adjacency for cambiario operations.

**Attempted fix.** Added `cambiario` to compatible_topics → dropped at validation (taxonomy didn't have it). Without a valid compatible topic, §1.B is no-op for this query.

**Hypothesis for next attempt.** Three branches:
1. Add a `cambiario` topic to `topic_taxonomy.json` (umbrella for currency/exchange controls) and curate `regimen_cambiario.compatible_topics = ["cambiario"]`. Requires SME approval of the new umbrella topic.
2. Add a hybrid_search topic-aware boost (server-side SQL change) so chunks with `chunk.topic = router_topic` are scored higher in RRF. This is the Lia-wide fix, not just for cambiario.
3. Reserve slots in `_collect_support` for router-topic docs (2-pass selection): pick first N high-rank docs, then fill remaining slots with router-topic docs if they exist anywhere in chunk_rows.

Branch 2 is the most general; branches 1 + 3 are targeted.

**Risk of each.** Branch 1: low (just data). Branch 2: medium (SQL migration to staging + production Supabase). Branch 3: low-medium (Python only, but needs care to not regress primary_articles classification).

#### Topic 3 — `impuesto_patrimonio_personas_naturales` → `pipeline_d_coherence_chunks_off_topic`

**What's failing.** Same shape as cambiario. 4 docs exist, hybrid_search pulls 1, gate refuses. Phase-2 measured the cross-topic owner is `patrimonio_fiscal_renta` (33 mentions, 94% of cross-topic refs).

**Why §1.B didn't fire fully.** `compatible_doc_topics` includes `patrimonio_fiscal_renta` — that part works. But the dominant lexical winner from the support_documents text is also `retencion_fuente_general` (same pattern as cambiario, the retention dump dominates lexical scoring on titles).

**Attempted fix.** §1.B added `patrimonio_fiscal_renta` + `declaracion_renta` to compatible_topics. Doesn't help because the support_documents pulled aren't tagged with EITHER — they're retention.

**Hypothesis for next attempt.** Same as cambiario branches 2 or 3. The compatible_topics list can't widen indefinitely without becoming contamination. The architectural fix is at the ranking layer.

#### Topic 4 — `conciliacion_fiscal` → `pipeline_d_coherence_chunks_off_topic`

**What's failing.** Conciliacion has only 2 .md docs total (the third is a PDF that the .md-only ingest pattern excluded). Even if both made it into support_documents, that's the bare-minimum threshold. Hybrid_search currently pulls 1; the other 1 doesn't make it.

**Why §1.B didn't fire fully.** §1.B added `procedimiento_tributario`, `declaracion_renta`, `costos_deducciones_renta` to compatible_topics. These topics have lots of docs but the hybrid_search query for "formato 2516 conciliar diferencias contables fiscales" doesn't pull them either — it pulls retention-tagged chunks.

**Attempted fix.** Same compatible_topics widening, didn't help.

**Hypothesis for next attempt.** Same structural fix as cambiario/patrimonio. Plus: investigate why the second conciliacion .md doc isn't ranked into support_documents — it might score poorly on FTS for this specific query phrasing.

### The supplementary-fetch attempt (failed)

Tried in `retriever_supabase.py` — added `_augment_with_topic_supplementary` that, when fewer than 2 router-topic docs were present in chunk_rows, did a second hybrid_search call with `filter_topic=router_topic` and prepended the results.

**What broke.** Empirically REGRESSED `impuesto_patrimonio_pn` and `conciliacion_fiscal` from `chunks_off_topic` to `pipeline_d_no_graph_primary_articles`. Root cause: prepending supplementary chunks pushed the anchor-row chunks (which provide primary_articles via `_classify_article_rows`) further down in chunk_rows, and the classifier's primary-article extraction stopped finding them within its scan window.

Mitigation tried: reorder so supplementary goes AFTER anchor_prefix but before fts_rows. Same regression. The classifier seems to prefer earlier rows for primary_articles regardless of anchor tagging.

**Status.** Helper `_augment_with_topic_supplementary` is kept in the file (docstring explains why) but **not invoked**. Re-enabling requires fixing `_collect_support` to do 2-pass selection that decouples support_doc choice from chunk_rows order.

### Architectural gap surfaced

Lia's hybrid_search has a `subtopic_boost` (RRF formula multiplier when `chunk.subtema = filter_subtopic`) but NO `topic_boost`. So the ONLY signals shaping retrieval ranking are FTS (term match in chunk_text/search_vector) + vector (semantic similarity to the query embedding) + RRF combination. Topic is purely informational on the result set, not used to rank. This is the deliberate design (per `retriever_supabase.py:138-141` comment: "topic is a planner-side signal, not a recall predicate"). But the consequence is exactly what we measured: when the retention dump's chunks score higher lexically/semantically than narrow-topic chunks, the narrow topic's docs get crowded out.

**The general fix candidate.** Add `topic_boost` parameter to `hybrid_search` SQL, default 1.0. Multiply RRF by `topic_boost` when `chunk.topic = filter_topic`. Plumb from the planner. Per `feedback_thresholds_no_lower`: this widens recall for the router topic without lowering any threshold.

This is a **structural Lia change**, not just a §1.B patch. Would also help any future thin-corpus topic without per-topic curation. Estimated effort: SQL migration (1 day) + Python wiring (0.5 day) + verification (0.5 day) = ~2 days.

### What this section is NOT

- A claim that §1.A or §1.B failed. Both shipped correctly + 8/12 unblocked is real progress.
- A request to lower thresholds. The 2-doc threshold + lexical scoring rules stay intact.
- A request to add `retencion_fuente_general` to compatible_doc_topics. That would be Q1-class contamination relaxation.

### Next-step priority (suggested)

1. Read `docs/orchestration/` deep runbooks (in progress) to understand the retrieval flow at line-level. Will likely surface additional fix candidates.
2. After reading: pick one fix and execute. Most-promising at this hour: hybrid_search topic_boost (general structural).
3. For topic 1 (precios), the curation fix is independent and can ship in parallel.

---

## §1.D Topic-aware boost in hybrid_search (opened 2026-04-26 evening)

> **Status:** 💡 idea — opened 2026-04-26 after the docs/orchestration/ runbooks made the architectural gap visible. This is the candidate gap-#1 fix surfaced in `retrieval-runbook.md`.

### Gate 1 — Idea (one sentence)

Add a `filter_topic_boost` parameter to the `hybrid_search` SQL RPC (default 1.0, no-op when unset) so chunks tagged with `chunk.topic = filter_topic` get their RRF score multiplied by the boost factor — analogous to the existing `filter_subtopic` + `subtopic_boost` mechanism — letting narrow-topic chunks rank above umbrella-topic chunks for the 3 thin-corpus topics still refusing with `chunks_off_topic` in §1.C without lowering any threshold.

### Gate 2 — Plan (narrowest scope)

1. **New Supabase migration** at `supabase/migrations/20260427000000_topic_boost.sql`:
   - Drop + recreate `hybrid_search` adding `filter_topic_boost double precision DEFAULT 1.0` parameter.
   - Modify the RRF formula in CTE `combined`: when `filter_topic IS NOT NULL AND chunk.topic = filter_topic`, multiply RRF by `topic_boost`.
   - Preserve the existing `filter_subtopic` + `subtopic_boost` boost (compose multiplicatively).
   - Invariant I5 carry-over: never penalize. Boost < 1.0 coerced to 1.0.

2. **Python wiring** at `src/lia_graph/pipeline_d/retriever_supabase.py::_hybrid_search`:
   - Read `LIA_TOPIC_BOOST_FACTOR` env (default 1.5, mirroring subtopic_boost default).
   - Determine `router_topic = next(iter(plan.topic_hints), None)`.
   - When `router_topic` is set, pass `filter_topic=router_topic` AND `filter_topic_boost=topic_boost_factor` in the RPC payload. Keep the older comment at line 138-141 accurate: filter_topic is a BOOST signal here, not a recall predicate. The SQL function only filters when `filter_topic` is paired with `filter_topic_strict=true` (NEW param too, default false). When strict=false, filter_topic is treated as a boost target, not a WHERE clause.
   - Try/except retry without the new params for older Supabase deployments (mirrors the existing subtopic-fallback pattern at line 168-178).

3. **Migration safety**:
   - Use `CREATE OR REPLACE FUNCTION` (Supabase migrations are idempotent on functions).
   - Add a smoke test that hits the new function shape from Python (probe an old query against the new RPC, verify it returns chunks).

4. **Tests**:
   - Update existing `test_hybrid_search_*.py` (if any) to verify the new RRF formula on a fixture.
   - Add `test_topic_boost.py` with 3 cases: (a) topic_boost=1.0 → identical to pre-§1.D ranking; (b) topic_boost=1.5 → narrow-topic chunk ranks above umbrella when both have similar FTS rank; (c) `filter_topic` is None → no boost applied (back-compat).

### Gate 3 — Minimum success criterion (measurable)

After the migration is applied to staging cloud Supabase + the Python wiring lands + a server restart picks up the new env default:

- **3 of the 4 currently-failing topics flip from `chunks_off_topic` (or `primary_off_topic`) to SERVED** in the chat probe (`bash /tmp/probe_topics.sh`):
  - `regimen_cambiario` → SERVED
  - `impuesto_patrimonio_personas_naturales` → SERVED
  - `conciliacion_fiscal` → SERVED
  - (`precios_de_transferencia` is not addressed by this fix — it's `primary_off_topic` and needs §1.A curation expansion. Out of scope here.)

- **No regression on the 8 currently-SERVED topics.** All 8 remain SERVED with same or higher citation counts.

- **No regression on the 30-Q gold set** (when next operator runs `make eval-c-gold`). This is a soft signal; the chat probe is the binding gate.

### Gate 4 — Test plan

- **Development needed.**
  - SQL migration file (~100 LoC).
  - Python wiring (~30 LoC + 1 fallback try/except branch).
  - Unit tests for the boost behavior (~150 LoC across 3 cases).
  - Smoke probe against staging Supabase post-migration (~30 LoC, read-only).
- **Conceptualization.** "Narrow-topic chunks should outrank umbrella-topic chunks when topically relevant" is the structural goal. The boost factor is a tuning knob; 1.5 is the inherited default from subtopic_boost (which has been stable since 2026-04-21). Per the precedent of `subtopic_boost`, this won't introduce contamination because the boost only fires when `chunk.topic = filter_topic` exactly — same chunks the gate already accepts as on-topic.
- **Running environment.**
  - Unit tests via `make test-batched`.
  - Migration applied to staging cloud Supabase (via `make supabase-start` locally first to validate, then via `supabase db push` against staging — operator-explicit per the cloud-write contract).
  - End-to-end verification via `bash /tmp/probe_topics.sh` against `dev:staging` server.
- **Actors + interventions required.**
  - Engineer (Claude): migration file + Python + unit tests + smoke probe against local Supabase.
  - Operator: explicit `supabase db push` to staging cloud (cloud-write — per `feedback_diagnose_before_intervene` and the operator's general no-cloud-writes-without-authorization rule).
  - Server restart: automated via my `Bash(pkill / npm run dev:*)` permission rule.
  - SME: not needed for this gate; gate 4b is binary (chat probes).
- **Decision rule.**
  - **Pass:** 3/4 currently-failing topics flip to SERVED + 0/8 SERVED topics regress.
  - **Partial pass (1 or 2 of the 3 flip):** investigate which topic still refuses and why; may need topic-specific tuning of `LIA_TOPIC_BOOST_FACTOR` per topic (env override). Iterate.
  - **No flips OR regressions appear:** revert the migration (idempotent — re-deploy the pre-§1.D function definition) and reopen with a different hypothesis.

### Gate 5 — Greenlight

Both signals required:
1. Unit tests green (the SQL boost + Python wiring + back-compat fallback).
2. End-user chat probe shows the 3-of-4 flip target met against staging cloud.

### Gate 6 — Refine-or-discard

- **If the boost is too aggressive (regresses adjacent topics):** lower `LIA_TOPIC_BOOST_FACTOR` from 1.5 to 1.2 or 1.1. The factor is env-overridable, so no code change to iterate.
- **If the boost is too weak (no flips):** raise to 2.0 or 2.5. Bounded by Invariant I5 (never penalize, always >=1.0).
- **If specific topics need different boost factors:** add a per-topic override config (`config/topic_boost_factors.json`) — only do this if a single global factor can't satisfy 3-of-4 simultaneously.
- **Discard path:** if neither single-factor nor per-topic overrides give a consistent 3/4 flip, revert the migration. The boost mechanism is principled (mirrors subtopic) but if it doesn't produce empirical movement, it's not the right fix and we explore §1.B's gap #2 (2-pass `_collect_support`) instead.

### Effort

Total: ~1 working day end-to-end.
- 0.25d SQL migration draft + local-Supabase smoke.
- 0.25d Python wiring + unit tests.
- 0.25d operator-driven staging migration apply + server restart.
- 0.25d chat probe re-run + post-mortem.

### Dependencies — strict

- **§1.A and §1.B must remain shipped.** §1.D layers on top; doesn't replace.
- **Operator action required for staging migration.** The Python wiring can ship to main but is no-op until the migration applies.
- **No SME involvement needed.** This is structural, not curation.

### What this is NOT

- **Not a relaxation of any threshold.** The 2-doc topic_key match minimum stays at 2. The lexical scoring rules unchanged. Boost only affects chunk rank ordering before the gate.
- **Not a new compatibility map.** §1.B's `compatible_doc_topics.json` is unchanged.
- **Not a switch from "topic as informational" to "topic as filter".** Per the existing comment at `retriever_supabase.py:138-141`, topic stays a planner-side signal. Boost ≠ filter — chunks of all topics still come back; narrow-topic chunks just rank higher among them.

### Status

💡 **idea** — opened 2026-04-26 from `docs/orchestration/retrieval-runbook.md` gap #1. Plan above is binding; code not yet written. Next step: implement gate 4a (migration + wiring + tests).

---

## ⚡ Execution priority order (2026-04-26 evening)

The next-task ordering operator-fixed 2026-04-26 evening:

1. **`§1.G` — SME validation run** (36 questions, ready). HUMAN EVIDENCE FIRST. Tells us whether the 11/12 are actually USEFUL or just `not refused`.
2. **`§1.F` — Investigate impuesto_patrimonio_personas_naturales regression**. Last remaining 1/12 refusal. Diagnostic-first. Only after §1.G clarifies whether the 11/12 are quality-pass.
3. **(After both)** revisit anything §1.G surfaced as "served but weak quality" — likely curation work, possibly content gaps requiring SME-authored material.

The order is binding because the SME has already authored the 36 questions — they're the rate-limited resource. Process them first while §1.F is purely engineering work that can wait.

---

## §1.G SME-authored validation run (opened 2026-04-26 evening, OPERATOR PRIORITY 1)

> **For an LLM with zero context taking this task on later:** read [`thin_corpus_validation_sme_brief.md`](thin_corpus_validation_sme_brief.md) first — that's the brief the SME used to author the questions. Then read this section in full.

### Status: 💡 idea — opened 2026-04-26 evening. Waiting on operator to paste the 36 SME-authored questions.

### Gate 1 — Idea (one sentence)

Run the 36 SME-authored questions (3 per topic × 12 topics, each labeled `P1 directa` / `P2 operativa` / `P3 borde`) against the live staging chat at `http://127.0.0.1:8787/api/chat`, classify each response by served/refused + citation count + quality class, and produce a per-topic + per-profile aggregate report so the operator + SME can see which topics genuinely answer well, which respond but weakly, and which still refuse.

### Gate 2 — Plan (narrowest scope)

#### Phase A — Ingest the questions

The operator pastes the 36 questions as plain text in this format (mirroring the brief's spec):

```
TEMA: <topic_key>
P1 (directa): <pregunta>
P2 (operativa): <pregunta>
P3 (borde): <pregunta>

TEMA: <next topic_key>
...
```

Save the operator's paste to `evals/sme_validation_v1/questions_2026-04-26.txt`. Build a tiny parser that splits on `TEMA:` blocks + extracts the `P1/P2/P3` lines into a normalized JSONL at `evals/sme_validation_v1/questions_2026-04-26.jsonl`:

```json
{"qid": "regimen_cambiario_P1", "topic_key": "regimen_cambiario", "profile": "P1_directa", "message": "..."}
```

12 topics × 3 profiles = 36 records. Topic keys MUST match `topic_taxonomy.json` registered keys exactly (validate via `tests/test_article_secondary_topics.py` style assertion). The 12 valid keys are listed in `thin_corpus_validation_sme_brief.md`.

#### Phase B — Build the runner

Create `scripts/eval/run_sme_validation.py`. It must:

1. Load `evals/sme_validation_v1/questions_2026-04-26.jsonl`.
2. Iterate over each record. For each:
   - POST `http://127.0.0.1:8787/api/chat` with body `{"message": <message>, "pais": "colombia"}`. Timeout 90s per request.
   - Capture: `answer_mode`, `fallback_reason`, `effective_topic`, `citations[].label`, `len(answer_markdown)`, `compose_quality`, latency_ms.
   - Store the full response in `evals/sme_validation_v1/runs/<utc_iso>__<qid>.json`.
   - Append a one-line summary to `evals/sme_validation_v1/runs/<utc_iso>__summary.jsonl`.
3. Pacing: 1 second sleep between requests so the server doesn't thrash. Total wall ≈ 36 × 15s ≈ 9 minutes.
4. Resume on Ctrl-C: skip qids whose response file already exists in the run dir.
5. Emit a single STATE line at the end: `STATE: served=X/36 partial=Y refused=Z`.

Use stdlib only (`urllib.request` + `json`). No new pip deps.

#### Phase C — Classify each response

For each qid, classify into one of:

| Class | Criteria |
|---|---|
| **`served_strong`** | `answer_mode == "graph_native"` AND `citations >= 3` AND `len(answer_markdown) >= 1500` AND `effective_topic == expected topic_key` |
| **`served_acceptable`** | `answer_mode in ("graph_native", "graph_native_partial")` AND `citations >= 1` AND `len(answer_markdown) >= 600` |
| **`served_weak`** | `answer_mode in ("graph_native", "graph_native_partial")` AND `len(answer_markdown) < 600` (mode is served but answer is too thin) |
| **`served_off_topic`** | served BUT `effective_topic != expected topic_key` (the router picked a different topic than the SME labeled) |
| **`refused`** | `answer_mode == "topic_safety_abstention"` |

The `expected topic_key` for each qid comes from the parser (Phase A). Save classifications to `evals/sme_validation_v1/runs/<utc_iso>__classified.jsonl`.

#### Phase D — Aggregate report

Build `scripts/eval/sme_validation_report.py` that reads the latest classified.jsonl + writes a markdown report at `evals/sme_validation_v1/runs/<utc_iso>__report.md` with these sections:

1. **Overall** — counts by class across all 36 (`served_strong`, `served_acceptable`, etc.).
2. **Per topic** — 12 rows, each with the 3 profiles × class. Format:
   ```
   | topic | P1 | P2 | P3 |
   |---|---|---|---|
   | beneficio_auditoria | served_strong | served_strong | served_acceptable |
   ```
3. **Per profile** — group by `P1/P2/P3`, count by class. Tells us if directa is hardest, operativa, or borde.
4. **Routing accuracy** — for each qid, did `effective_topic` match the SME's expected topic? Topic-routing is upstream of all the §1.A-E work; this surfaces if the router is the bottleneck rather than the gate.
5. **Topics flagged for follow-up** — any topic with ≥ 1 of its 3 questions in `served_weak` or `served_off_topic` or `refused`. List the qids + the specific question text + the response head (first 300 chars).
6. **Decision summary at the bottom** — apply Gate 3 numeric rule (below) and print PASS / PARTIAL / FAIL.

Also emit `STATE:` first line for cron-friendly polling: `STATE: pass=N partial=M fail=K`.

#### Phase E — Operator + SME review

After the report lands, the operator and/or SME inspects the "topics flagged for follow-up" section. Decisions per topic:
- **All 3 served_strong** → topic is production-ready.
- **Mix of strong + acceptable** → topic is OK; consider curation tuning if SME notes weak phrasing.
- **Any served_weak** → answer is thin; flag for content expansion (corpus deficit) OR for `answer_synthesis` tuning.
- **Any served_off_topic** → router is wrong; flag for `path-veto-rule-based-classifier-correction.md` extension OR `topic_taxonomy.json` keyword_anchors expansion.
- **Any refused** → either the §1.E/§1.F still has scope, OR a deeper structural fix is needed.

### Gate 3 — Minimum success criterion (numeric)

After the run + report:

- **PASS** = at least 22/36 questions are `served_strong` OR `served_acceptable` (≈ 60% threshold; 22 covers ~7 fully-passing topics × 3 + a couple partials).
- **PARTIAL** = 14/36 to 21/36 served_acceptable+. The 11/12 metric still holds at the topic level but quality is uneven.
- **FAIL** = ≤ 13/36 served_acceptable+. The §1.A-E work is not delivering useful answers; reopen with quality-focused investigation before declaring victory.

**Cross-checks** (binding regardless of overall):
- The single still-refusing topic (`impuesto_patrimonio_personas_naturales`) should refuse all 3 of its questions — confirms §1.F is needed AND that the refusal is consistent (not flaky).
- The 11 currently-SERVED topics in the heartbeat baseline should NOT see all 3 questions refused — that would mean the heartbeat baseline question was unrepresentative and we have hidden refusals.

### Gate 4 — Test plan

- **Development needed.** ~150 LoC across `run_sme_validation.py` (parser + runner + classifier) and `sme_validation_report.py` (aggregator). Plus a directory `evals/sme_validation_v1/` with the question fixture. No new tests required — the script is its own test (output is the artifact); but a smoke unit test for the parser (handles empty TEMA blocks, missing P-lines, etc.) is good practice (~30 LoC).
- **Conceptualization.** "Served + cites + length" is a cheap proxy for quality. The SME's eyes on the flagged topics are the actual quality measurement; the script just funnels their attention to the topics that need it.
- **Running environment.** Local Python (stdlib + the existing repo). The chat server must be running at `http://127.0.0.1:8787` with §1.A + §1.B + §1.D + §1.E all live (heartbeat baseline shows 11/12 with `precios_de_transferencia: ✅` after §1.E ship). If the heartbeat shows < 11/12 at the start of the run, abort + investigate before running the SME questions.
- **Actors + interventions.**
  - **Operator** pastes the 36 questions in the format above and runs the runner (≈ 9 minutes).
  - **Engineer (Claude)** wrote the runner + report scripts; reviews the report; flags any pattern the SME should review.
  - **SME (optional)** reviews the "topics flagged for follow-up" section + sample answers from `served_weak` / `served_off_topic` / `refused`.
- **Decision rule.** Apply Gate 3 numeric thresholds + cross-checks. Print PASS/PARTIAL/FAIL in the report.

### Gate 5 — Greenlight

PASS or PARTIAL → §1.G is closed; proceed to §1.F.

FAIL → reopen with the report data. Likely causes: §1.A/§1.E curation gaps surfaced (more articles need secondary_topics), router_topic mis-classification dominates (path-veto extension needed), or `answer_synthesis` shortcuts a topic.

### Gate 6 — Refine-or-discard

If the report shows that 1-2 specific topics fail consistently, drill into those:
- Re-read the topic's docs (`docs/learnings/ingestion/coherence-gate-thin-corpus-diagnostic-2026-04-26.md` has the corpus inventory).
- Pick the highest-leverage fix (curation, `compatible_doc_topics.json`, etc.).
- Re-run only the 3 affected qids (the runner supports resume).
- Iterate until the 3 hit at least `served_acceptable`.

If 5+ topics fail consistently, that's a structural issue beyond what §1.A-E is designed to fix. Pause the SME validation track and reopen with a different hypothesis (likely: corpus quality, not retrieval architecture).

### Dependencies — strict

- The operator pastes 36 questions in the format spec'd in Phase A.
- Server is running + heartbeat shows 11/12 SERVED at run start.
- All §1.A + §1.D + §1.E work is shipped + verified (it is, as of 2026-04-26 evening).
- No SME action required at runtime; SME reads the report after.

### Effort

- Phase A (parser): ~30 min
- Phase B (runner): ~45 min
- Phase C (classifier): ~30 min
- Phase D (aggregator + report): ~45 min
- Phase E (operator/SME review): operator-driven, async
- Total engineering: ~2.5 hrs of code + ~10 min runtime + SME review time

### What this is NOT

- **Not** a substitute for the existing 100-Q gauge in §5 — that's a different scope (100 Qs across 28 categories, broader). §1.G is targeted at the 12 thin-corpus topics specifically.
- **Not** a regression check on the 30-Q gold set — that's `make eval-c-gold`, runs against staging cloud already.
- **Not** a release gate. We're not blocking anything on this; it's diagnostic + quality-assurance for the 12-topic flip we just did.

---

## §1.E Precios de transferencia — curación expandida de §1.A (opened 2026-04-26 evening)

> **Status:** 💡 idea — opened after §1.D verification surfaced this as the only remaining `primary_off_topic` refusal among the 12 thin-corpus topics. §1.D doesn't address it; §1.A does, but the seed config (36 entries) didn't cover the precios family.

### Gate 1 — Idea (one sentence)

Add the canonical Art. 260-N family (260-1 through 260-11) to `config/article_secondary_topics.json` with `secondary_topics=["precios_de_transferencia"]` so when a user asks about a precios topic and the planner pulls one of those articles as a primary, the §1.A short-circuit fires and the gate accepts the article as on-topic.

### Gate 2 — Plan (narrowest scope)

1. **Identify which articles to add.** SME-validated source: `pt_normativa_precios_transferencia.md` (728 lines covering Art. 260-1 through 260-11) + `taxonomy_v2_sme_response.md` line 766 (allowed_et_articles for precios). Concrete list:
   - Art. 260-1 (operaciones entre vinculados — definición y alcance)
   - Art. 260-2 (principio de plena competencia)
   - Art. 260-3 (cinco métodos para aplicar plena competencia)
   - Art. 260-4 (criterios de comparabilidad)
   - Art. 260-5 (already in config with secondary `firmeza_declaraciones` — extend to also include `precios_de_transferencia`)
   - Art. 260-6 (criterios de vinculación)
   - Art. 260-7 (vinculación con jurisdicciones de baja o nula imposición)
   - Art. 260-8 (registro de operaciones de cambio)
   - Art. 260-9 (declaración informativa)
   - Art. 260-10 (acuerdos anticipados de precios)
   - Art. 260-11 (sanciones por incumplimiento de obligaciones de precios de transferencia)

2. **Edit the JSON config.** ~11 entries. Each cites its SME source + rationale.

3. **Verify via `tests/test_article_secondary_topics.py::test_default_seed_topics_all_in_canonical_taxonomy`.** All new topic refs must be `precios_de_transferencia` (already a registered taxonomy key — confirmed earlier).

4. **Sync to Falkor via the existing one-shot script.** `scripts/ingestion/sync_article_secondary_topics_to_falkor.py` is idempotent — re-runs the full config and updates only the changed/new entries.

### Gate 3 — Minimum success criterion

After config update + sync to Falkor + (no server restart needed — config is read at request time):

- The `precios_de_transferencia` probe in `bash /tmp/probe_topics.sh` flips from `pipeline_d_coherence_primary_off_topic` to **SERVED** (mode `graph_native` or `graph_native_partial`).
- No regression on the other 11 topics in the heartbeat (`scripts/monitoring/thin_corpus_heartbeat.py` exits with status 0).
- The current 10/12 baseline becomes 11/12.

### Gate 4 — Test plan

- **Development needed.** Edit JSON + run sync script. ~30 min total. No code change.
- **Conceptualization.** Adding precios_de_transferencia as a secondary topic on canonical 260-N articles tells the gate: "even if these articles' canonical owner doc is `declaracion_renta` (or whatever umbrella), they ALSO serve precios queries." Same mechanism §1.A used to unblock 7 topics.
- **Running environment.** Local edit + sync to staging cloud Falkor (read-only of taxonomy.json + write of `secondary_topics` props on existing nodes). No SQL migration. No server restart.
- **Actors.** Engineer (Claude) edits + syncs. Operator confirms by running the heartbeat.
- **Decision rule.** Pass = `precios_de_transferencia` flips to SERVED + heartbeat shows 11/12 + 0 regressions. Fail = something else regressed; revert.

### Gate 5 — Greenlight

Both: (a) `tests/test_article_secondary_topics.py` green (8 cases including taxonomy validation); (b) chat probe of precios_de_transferencia returns a `graph_native*` response with citations.

### Gate 6 — Refine-or-discard

If the probe still refuses post-curation: investigate which specific Art. 260-N the planner is pulling as primary. The curation only helps if THAT article is in the secondary_topics map. If a different article (not in 260-1..260-11) is the primary, expand the curation list further.

If the response IS served but the QUALITY is poor (SME spot-check): the corpus may be thin on the actual answer content; that's a §1.E.B follow-up (add content, not just curation metadata).

### Effort

~30 min of curation + ~5 min running the sync script + ~2 min running the heartbeat. ~40 min total.

### Dependencies — strict

- **§1.A must remain shipped** (it is — 8/12 baseline still SERVED via §1.A + §1.D combo).
- **No SME involvement needed for the structural curation.** The article→topic mapping is unambiguous from the SME-validated `taxonomy_v2_sme_response.md` line 766.

---

## §1.F Impuesto patrimonio PN — investigar regresión causada por §1.D (opened 2026-04-26 evening, OPERATOR PRIORITY 2)

> **Execution order:** AFTER `§1.G` (SME validation). The SME-authored questions may surface that the impuesto_patrimonio failure is broader than the single probe suggests, OR may reveal it's contained — that signal informs how aggressive §1.F's fix needs to be.
>
> **For an LLM with zero context taking this task on later:** read `docs/orchestration/coherence-gate-runbook.md` (the `coherence_zero_evidence_for_router_topic` decision-tree branch) and `docs/orchestration/retrieval-runbook.md` (gap #4: vector path inert with zero embeddings, and the §1.D boost SQL formula in detail) before starting. Also read `next_v5.md §1.D` for what the boost migration changed.

> **Status:** 💡 idea — opened after §1.D shipped and `impuesto_patrimonio_personas_naturales` REGRESSED from `chunks_off_topic` (its §1.B-era state) to `coherence_zero_evidence_for_router_topic`. §1.D's boost factor 1.5 caused the SQL function to return zero evidence for this specific topic.

### Gate 1 — Idea (one sentence)

Investigate why §1.D's topic boost causes the `hybrid_search` SQL to return zero rows for `impuesto_patrimonio_personas_naturales` queries (instead of the expected behavior of "narrow-topic chunks rank higher among returned rows"), then fix without breaking the 2-of-3 §1.D successes.

### Gate 2 — Plan (narrowest scope)

This is a **diagnostic** first, not an intervention. Per `feedback_diagnose_before_intervene`:

1. **Direct SQL probe** (read-only, no migration):
   - Run the `hybrid_search` RPC manually for the impuesto_patrimonio probe message with `filter_topic_boost=1.5` AND `filter_topic="impuesto_patrimonio_personas_naturales"`.
   - Run the same RPC with `filter_topic_boost=1.0` (effectively pre-§1.D).
   - Diff the row counts + ranking. Where does the difference originate? FTS CTE? Semantic CTE? Combined?

2. **Hypothesis space:**
   - **H1 (FTS cutoff):** with the topic boost active, the FTS CTE's `LIMIT match_count` cuts off after the boosted narrow-topic chunks but the FTS rank itself isn't actually higher for them — so they fail the `search_vector @@ effective_tsq` predicate at the top, and the boost can't help because they're not in the candidate pool.
   - **H2 (zero-embedding interaction):** with `query_embedding = _zero_embedding()`, the semantic CTE returns chunks ranked essentially randomly. The boost in `combined` re-ranks but if the FTS CTE has zero impuesto_patrimonio chunks, the only chunks for that topic come from semantic — and there might not be enough.
   - **H3 (SQL bug):** the CASE WHEN chunk.topic = filter_topic check has a typo or misses something subtle. Re-read the migration carefully.

3. **Decision after diagnosis:**
   - If H1: lower the boost factor for this topic only (per-topic config), OR pre-seed the CTE with the topic-specific chunks before the FTS filter applies.
   - If H2: hand the planner a real embedding (via Gemini embed call) so the semantic CTE actually contributes ranking. This is a bigger lift but unlocks more than just this topic.
   - If H3: fix the SQL.

### Gate 3 — Minimum success criterion

After the fix lands:

- The `impuesto_patrimonio_personas_naturales` probe flips back to SERVED (mode `graph_native*`).
- The other 9 currently-served topics (firmeza, regimen_sancionatorio, descuentos, tarifas, dividendos, devoluciones, perdidas, regimen_cambiario, conciliacion) stay SERVED — no regression.
- `beneficio_auditoria` stays SERVED.
- Net: 11/12 (assuming §1.E not yet shipped) or 12/12 (if §1.E ships first).

### Gate 4 — Test plan

- **Development needed.** Diagnostic SQL probe script (~20 LoC). Possibly per-topic boost factor config OR embedding wiring depending on H1/H2/H3 verdict.
- **Conceptualization.** A boost should NEVER reduce evidence — that's Invariant I5 violation in spirit (even if not letter; the boost is ≥1.0 by construction). If the boost causes evidence reduction, the SQL is interacting with the cutoff incorrectly.
- **Running environment.** Diagnostic probe runs locally against staging Supabase (read-only). Any fix that requires a SQL migration → operator-explicit `supabase db push`. Python-only fix → server restart.
- **Actors.** Engineer (Claude) runs diagnostic + writes fix + tests. Operator applies migration if needed. SME not involved.
- **Decision rule.** Pass = impuesto_patrimonio probe flips to SERVED + heartbeat shows 0 regressions. Fail = revert the §1.D boost factor for this topic only via per-topic env override OR revert §1.D entirely.

### Gate 5 — Greenlight

Both: (a) diagnostic identifies the root cause (H1, H2, or H3) with measured numbers; (b) chosen fix delivers SERVED for impuesto_patrimonio + 0 regressions in heartbeat.

### Gate 6 — Refine-or-discard

If neither H1, H2, nor H3 fix the issue: per-topic boost factor override (`config/topic_boost_overrides.json`). Set boost to 1.0 (off) for impuesto_patrimonio specifically. The other 11 topics keep the global 1.5. This is a fallback, not a clean fix — record explicitly as such.

If even per-topic override doesn't help: revert §1.D entirely. Net cost: regimen_cambiario + conciliacion_fiscal flip back to refused. We accept 8/12 + figure out a different structural fix (§1.B's gap #2: `_collect_support` 2-pass selection).

### Effort

~1-2 hours diagnostic + ~1-3 hours fix + ~30 min verification = ~3-5 hours total.

### Dependencies — strict

- **§1.D must remain in production** (revert is the ultimate fallback, not the preferred path).
- **No SME involvement.** This is structural debugging.

---

## §6 Falkor parity + corpus-grow safety (carried from v4 §6.5)

**Status mix:** §6.5.A 💡 idea; §6.5.B 🧪 verified locally with qualitative-pass on bucket (b)=54; §6.5.D 💡 idea; §6.5.E 🧪 verified locally (5/5 guard tests, audit complete). Full record + bucket numbers + samples in `docs/learnings/ingestion/falkor-edge-undercount-and-resultset-cap-2026-04-26.md`.

### What's pending in v5

#### §6.1 (carries v4 §6.5.A) — Propagate `sync_generation` to Falkor nodes
Schema + loader + backfill + flag `LIA_FALKOR_NODE_GENERATION_TAG`. Closes the parity-probe asymmetry so the GUI tarjeta can reach "Alineada ✓" on real alignment, not on label-name luck. Full plan + gates: [v4 §6.5.A](./next_v4.md#item-65a--propagate-sync_generation-to-falkor-nodes).

**Recommended order:** §6.2 (sub-bucketing) FIRST per `feedback_diagnose_before_intervene`; §6.1 only if §6.2 shows the gen-tag is needed for the right reason.

#### §6.2 — Sub-bucket the 33% endpoint-missing (read-only diagnostic, opened 2026-04-26)

**Status:** ✅ **verified in target environment 2026-04-26** — diagnostic ran against staging cloud. Result: **(a1) = 99,1% (9.848/9.934)**, (a2) = 0,9%, (a3) = 0%. Math-check passes. **Decision branch fired: open §6.3** with recovery upside ≤ 9.848 edges. Full numbers + samples + pattern observation in `docs/learnings/ingestion/falkor-edge-undercount-and-resultset-cap-2026-04-26.md`.

> **Pattern note (operator-relevant).** All sampled (a1) edges share the same source document: an interpretation/expert-comment file (`T-REF-LABORAL-reforma-laboral-interpretaciones-expertos.md`). The loss concentrates heavily in **prose-only interpretation/expert files**, which lack `article_number` and so MERGE into Falkor under the `whole::{source_path}` form. Numbered-article docs are unaffected.

##### Gate 1 — Idea (one sentence)

Take the 9.934 edges in bucket (a) "endpoint not materialized in Falkor" and split them into three sub-buckets — **(a1)** prose-only key mismatch (source `article_key` is the legacy slug form like `'10-fuentes-y-referencias'` while Falkor has the article under `whole::{source_path}`), **(a2)** genuinely filtered (article was rejected by `loader.py`'s schema gate, edge correctly dropped), **(a3)** reform-side missing (source_key looks like `DECRETO-XXX-…` but no `:ReformNode` exists) — so the next intervention targets the actually-dominant cause instead of guessing.

##### Gate 2 — Plan (narrowest scope, no production code touched)

All work in `scripts/diag_falkor_edge_undercount.py`. Read-only. ~40-50 LoC additions, no new dependencies.

1. **Pull a Supabase chunks lookup table.** Paginated `SELECT article_key, article_number, source_path, is_prose_only FROM document_chunks WHERE sync_generation = $active_gen` → in-memory dict keyed by `article_key`. Gives the classifier's view of "is this article prose-only and where does it live on disk".
2. **Pull Falkor's `whole::*` keys.** `MATCH (a:ArticleNode) WHERE a.article_id STARTS WITH 'whole::' RETURN a.article_id` — paginated using the existing helper from §6.5.E learnings. Gives the set of prose-only articles that DID land in Falkor (under the alternate key form).
3. **Pull a reform-id pattern set.** Single regex applied to bucket-(a) source_keys: `^(DECRETO|LEY|RESOLUCION|CIRCULAR|SENTENCIA|CONCEPTO)-\d+(-\w+)?$`. If matched and the key isn't in the Falkor `:ReformNode` keyset (already pulled in §6.5.B), → (a3).
4. **Bucket (a) edges into (a1)/(a2)/(a3) using the three lookup sets.** Classification rule for each missing-endpoint edge's source_key:
   - matches reform-id regex AND not in `:ReformNode` keyset → **(a3)**
   - in chunks lookup AND `is_prose_only=true` AND `whole::{chunks[key].source_path}` IS in Falkor → **(a1)**
   - in chunks lookup AND not prose-only OR Falkor doesn't have the `whole::` form → **(a2)**
   - not in chunks lookup at all → **(a2)** (article never made it to Supabase chunks either)
5. **Print sub-bucket counts + 5+ samples per bucket.**
6. **Compute recovery upside per bucket.** (a1) upside = count(a1). (a3) upside = N/A unless a separate §6.X opens for ReformNode hydration. (a2) upside = 0 (loader is doing what it should).
7. **Append sub-bucket section to** `docs/learnings/ingestion/falkor-edge-undercount-and-resultset-cap-2026-04-26.md` with the numbers and decision branch.

##### Gate 3 — Minimum success criterion (measurable, numeric)

After the diagnostic re-runs against staging cloud:
- (a1) + (a2) + (a3) sums to 9.934 (math check; misclassifications must not silently drop edges).
- Each sub-bucket has ≥ 5 distinct sample edges printed.
- Decision branch named in the learnings doc:
  - **(a1) ≥ 70% of bucket (a)** → open §6.3 to fix the classifier; recovery upside ≤ 9.934 edges in Falkor.
  - **(a3) ≥ 50% of bucket (a)** → open §6.X for ReformNode hydration (separate from §6.3).
  - **(a2) ≥ 50% AND (a1) < 30%** → close as "expected loss confirmed", document and stop.
  - **No single bucket > 50%** → close as "diffuse cause"; the 9.934 number is heterogeneous and a single fix won't dent it materially. Document the null-result and don't pursue.

##### Gate 4 — Test plan

- **Development needed.** ~40-50 LoC in the diagnostic script (chunks-pull helper, reform-regex, three-way classifier, sample collector, recovery-upside math, learnings-doc append). The existing pagination helpers from §6.5.E are reused.
- **Conceptualization.** "Sub-bucket dominance ≥ 70% means a single intervention recovers most of the loss" — that's the threshold that makes a follow-up worth scoping. < 70% means the cause is heterogeneous and we're better off stopping.
- **Running environment.** Local execution (`uv run` against staging cloud read endpoints). Read-only — no Supabase or Falkor writes. ~1 hour wall time including the script run + learnings doc write-up.
- **Actors.** Engineer runs and writes up. **No SME or operator action needed for this gate.**
- **Decision rule.** Numeric, per Gate 3 thresholds. AND-conjoined with the math-check (sub-buckets sum to 9.934).

##### Gate 5 — Greenlight

Both signals: (a) math-check passes (sub-buckets sum to bucket (a) total) AND (b) decision branch is unambiguously identified per the Gate 3 threshold rules. If the result is "diffuse cause" or "(a2) dominates", that's a legitimate close per gate-6 — not a failure.

##### Gate 6 — Refine-or-discard

- If the chunks lookup + Falkor `whole::` enumeration reveals data inconsistencies that block clean classification (e.g., the chunks table doesn't track `is_prose_only` for some rows), narrow the diagnostic to just the rows where the metadata is clean and report partial. Don't overstate.
- If the script can't reach a clean bucketing (heterogeneous samples, no clear pattern), discard the bucketing approach and reopen with a different hypothesis (perhaps inspecting the loader's per-edge skip log directly instead of comparing endpoint sets).
- A "diffuse cause" outcome is itself a successful gate-6 close — it tells us not to invest engineering in a fix that won't help.

##### Effort

~1 hour engineering + ~5-10 minutes wall time for the diagnostic to actually run. Decision-branch follow-up scoped only after this gate clears.

---

#### §6.3 — Fix: classifier emits `_graph_article_key()` for prose-only edges

**Status:** ✅ **verified in target environment 2026-04-26** — code shipped + tests green + applied against staging cloud via the `BRECHAS-SEMANA4-ABRIL-2026/FIRMEZA_DECLARACIONES` trilogy (3 docs). Gate-3 numeric criteria all passed.

**Empirical verification numbers** (pre vs post the FIRMEZA trilogy ingest):

| Metric | Pre | Post | Δ | Verdict |
|---|---:|---:|---:|---|
| Falkor edges total | 24.874 | 24.973 | +99 | new edges landed |
| "Present in Falkor" | 19.815 | 19.894 | **+79** | new whole:: source_keys MATCHed |
| **(a1) prose-only key mismatch** | 9.848 | **9.848** | **0** | ✅ **gate-3 binding pass** — no new slug-form rows |
| (a2) genuinely orphaned | 86 | 87 | +1 | acceptable noise |
| Falkor `:ArticleNode` `whole::*` | 1.141 | 1.143 | +2 | 2 prose-only docs landed |
| Edges from SEMANA4 sources | 0 | **38** | +38 | direct proof: whole:: source edges MATCHed |

The 9.848 legacy rows in `normative_edges` (slug-form source_key, written before the fix) stay until either (a) their source documents are individually re-classified or (b) a forced full reclassify runs. They're functionally invisible to runtime retrieval; cleanup is optional and out of §6.3 scope.

**Side-finding (not §6.3-related):** bucket (b) silent-drop grew 54 → 75 (+21). The new edges all originate from NORMATIVA_FIR-N02's numbered articles (Art. 147, 705, 689-3, …) referencing other articles whose target `article_id` doesn't exist in Falkor due to the known F8 article_id-collision issue (per `docs/learnings/ingestion/falkor-bulk-load.md`). Below the 100-edge watchlist threshold, not blocking §6.3. Worth a §6.6 if the pattern repeats on the next 4 trilogies.

Full empirical numbers + samples + the unexpected NORMATIVA-doc-materialization-as-numbered-articles outcome live in `docs/learnings/ingestion/falkor-edge-undercount-and-resultset-cap-2026-04-26.md` — "v5 §6.3 fix — outcome" section.

##### Gate 1 — Idea (one sentence)

When the classifier writes `normative_edges` rows for edges whose source or target is a prose-only article, emit the `_graph_article_key()` form (`whole::{source_path}`) directly into `source_key` / `target_key` — instead of the legacy `article_key` slug — so the loader's downstream MATCH against Falkor finds the endpoint instead of filtering the edge out.

##### Gate 2 — Plan (narrowest scope)

1. **Locate the classifier site that writes `normative_edges` source/target keys.** Likely in `src/lia_graph/ingestion/classifier.py` or `linker.py`. Read-trace required before code changes.
2. **Single change.** When the article is prose-only (`article_number` empty), substitute `_graph_article_key()` (already exists at `loader.py:43-65`) for the raw `article_key` when constructing the edge row.
3. **New ingest contract test.** Build a fixture: one prose-only article + one numbered article + one edge between them. Assert the classifier writes the edge with `source_key='whole::…'` (or whatever the prose side is), and assert the loader MATCH succeeds.
4. **Re-run §6.2 sub-bucketing as the verification harness.** The same diagnostic script is the gate-3 measurement tool.

##### Gate 3 — Minimum success criterion

After the fix ships and the next staging delta runs:
- §6.2 sub-bucketing re-run shows **bucket (a1) drops by ≥ 70%** (i.e., the fix recovered most of the prose-key-mismatch loss).
- Bucket (a2) does NOT increase (we didn't accidentally orphan more articles).
- Bucket (b) silent-drop count stays ≤ 100 (we didn't introduce a new silent-drop pattern).
- Total Falkor edges count increases by approximately the bucket-(a1) drop.

##### Gate 4 — Test plan

- **Development needed.** Read-trace + ~10-30 LoC change in the classifier + 1 new ingest contract test.
- **Conceptualization.** "Bucket (a1) drops by ≥ 70%" is the fix actually working at the layer where the loss happens. Bucket (a2) staying flat confirms we didn't trade one loss for another.
- **Running environment.** Unit + ingest contract tests via `make test-batched`. End-to-end verification needs a staging hydration of at least one prose-only document with measurable edges, ideally the next operator-driven additive delta.
- **Actors.** Engineer ships code + tests. Operator triggers the staging delta. No SME involvement (this is plumbing, not content).
- **Decision rule.** All three Gate-3 numeric checks pass = ship. Any single failure = revert + reopen with a different hypothesis.

##### Gate 5 — Greenlight

Both: (a) unit + ingest tests green, (b) post-staging-delta §6.2 re-run shows the (a1) drop AND no (a2)/(b) regressions.

##### Gate 6 — Refine-or-discard

If the staging re-run shows the (a1) drop happened but (a2) or (b) increased, **investigate which articles got newly-orphaned** before discarding. The rollback is simple (revert the classifier change), but we should understand why before reverting in case the (a2) increase is itself a different fixable bug.

If the (a1) drop doesn't materialize at all, the hypothesis was wrong — discard the change and reopen §6.2 with a different sub-bucketing rule.

##### Effort (only counted if §6.2 says go)

~1-2 days end-to-end on the optimistic path: ~0.5d for read-trace + locate the classifier site + understand the data flow, ~0.5d for the code change + unit + contract tests, ~0.5d operator-triggered staging delta + §6.2 re-run for verification.

##### Dependencies — strict

- **§6.2 must clear gate-3 with bucket (a1) ≥ 70%.** This is the only path that opens §6.3.
- §6.1 (sync_generation propagation) is **independent** — neither blocks the other.

#### §6.4 (carries v4 §6.5.B watchlist) — Silent-drop bucket re-measurement
Bucket (b) = 54 (`references → CITA`, < 0,2%) recorded as qualitative-pass per case. **Re-run the diagnostic after the next staging delta** (§6.2 sub-bucketing already requires this anyway). Decision: if (b) grows > 100 → escalate to a §6.6 writer-investigation; if stays ≤ 100 → close §6.4 as expected variance.

#### §6.5 (carries v4 §6.5.E) — Operator-staging silence verification
Guard at `src/lia_graph/graph/result_guard.py` is shipped + 5/5 tests green. ✅ **target-env verification:** any operator-driven staging session running with the guard in place that emits **no** `graph.resultset_cap_reached` events is a positive signal. Mark ✅ once the §3 multi-turn harness or the §5 100-Q gauge runs through the guard.

---

## §7 Retrieval-depth envelope calibration (operator-surfaced 2026-04-26)

### Why

Operator question (2026-04-26): "¿por qué los límites en `pipeline_d/planner.py` son 3-5 y no 8 o 10? ¿En qué ayuda eso a tener una mejor respuesta?"

The honest answer: the per-mode envelopes (`primary_article_limit`, `connected_article_limit`, `related_reform_limit`) range 3-5 / 3-5 / 2-4 across query modes; they're **tuned by intuition**, not by a documented A/B against the 100-Q gauge or any other measurable. The choice trades off four forces (context-window pressure, precision-vs-recall U-curve, latency, cost) against one (recall on multi-faceta questions). With `LIA_RERANKER_MODE=live` already feeding a wider candidate pool to the reranker, the *current* bottleneck may not be "show more articles to the LLM" — it may be "make sure the reranker's top-5 is the right top-5". This question can only be answered with the gauge.

### Idea (one sentence — gate 1)

Run a controlled A/B/C calibration through the 100-Q gauge (per §5) that varies only the per-mode `primary_article_limit` + `connected_article_limit` envelope (5/5 baseline → 7/7 moderado → 10/10 amplio), holds everything else constant, and decides whether to re-tune the envelope based on the resulting macro-pass / latency / cost surface.

### Plan (gate 2 — narrowest scope)

1. **Knob.** Add `LIA_RETRIEVAL_DEPTH_OVERRIDE` env that, when set to `5_5`, `7_7`, or `10_10`, overrides `BundleShape.primary_article_limit` and `BundleShape.connected_article_limit` for every mode. `related_reform_limit` follows proportionally (×0.8, rounded). Off by default — overrides only fire when the env is set, so production behavior is unchanged.
2. **Implementation site.** Single helper in `pipeline_d/planner.py` that wraps the existing `BundleShape` factory; reads the env once at module import. No changes to query templates (they already accept `LIMIT $limit` parametrically).
3. **A/B/C harness.** Re-use `scripts/judge_100qs.py` with three runs tagged `depth_5_5`, `depth_7_7`, `depth_10_10`. Each run captures: macro-pass-%, per-dimension means, judged-cost in USD, mean per-Q latency-ms.

### Success criterion (gate 3 — measurable, no vibes)

Define **before** running, per `feedback_thresholds_no_lower` and `feedback_gates_evaluate_independently`:

- **Pass to flip envelope:** moderado (7/7) macro-pass ≥ baseline (5/5) macro-pass + **2.0 percentage points** AND mean latency increase ≤ **800 ms/Q** AND judged-cost increase ≤ **+50%**. All three thresholds are AND-conjoined; partial wins are not flips.
- **Pass to flip to amplio (10/10):** same rule applied to amplio vs moderado, with the moderado run as the new baseline. Sequential gates — never compare amplio directly to 5/5 to claim a flip.
- **Tie or worse → keep 5/5.** If 7/7 doesn't clear by ≥ 2.0pp, the envelope stays. The corpus-quality lever lives elsewhere (reranker, retrieval recall, planner mode-detection) — confirmed by null-result.

### Test plan (gate 4)

- **Development needed.** ~30 LoC for the env-driven envelope override + 2 unit tests asserting (a) absent env → unchanged behavior, (b) `5_5`/`7_7`/`10_10` envs → expected `BundleShape` outputs.
- **Conceptualization.** Macro-pass % is the user-visible signal ("answer quality moves with depth"). Per-dimension means tell us *how* it moves (does extra depth help `completitud` while hurting `claridad_profesional`? then the gain is real but partial). Latency + cost guard against silent operational regression.
- **Running environment.** Three serial runs of `run_100qs_eval.py` + `judge_100qs.py` against staging cloud (`npm run dev:staging`). Approx ~$6-12 USD total + ~45-60 min wall time per run.
- **Actors + interventions.** Engineer ships the env-driven knob + unit tests. **Operator** runs the three A/B/C cycles (production credentials + ANTHROPIC_API_KEY). **SME spot-check on the moderado-vs-baseline weakest 10 deltas** if the macro number flips — confirms the gauge isn't being fooled by judge-bias toward verbosity.
- **Decision rule.** Already specified in gate 3, AND-conjoined.

### Greenlight (gate 5)

Both signals: (a) gate-3 thresholds clear AND (b) SME spot-check confirms no answer-quality regression on the 10 weakest moderado-vs-baseline deltas. Either fails → keep the 5/5 envelope.

### Refine-or-discard (gate 6)

If 7/7 clears the macro+cost gates but SME finds the answers got *more* generic (the "more articles → distractor" failure mode), narrow the trigger: keep 7/7 only on `comparative_regime_chain` mode (where multi-faceta is structural) and revert other modes to 5/5. Discard entirely if SME flags regression on ≥ 3 of 10 spot-cases.

### Effort

~1 day engineering (knob + tests) + ~1 operator afternoon for the three runs + ~1 hour SME spot-check (only if a flip is on the table).

### Dependencies — strict

- §5 §5.1 must ship first. Without a baseline 100-Q run, depth A/B is unmeasurable.
- `ANTHROPIC_API_KEY` available to the operator.
- §3 (multi-turn harness verification) **independent** — no blocker.

### Status

💡 **idea** — opened 2026-04-26 from operator design question. Code not written. **Strict precondition: §5.1 baseline must land first.**

---

## §8 What's NOT here (deliberately)

- **Free-text LLM rolling summary as an immediate deliverable** — explicitly deferred per §3 Level 3 with binding reopen conditions. Don't reopen without all three triggers.
- **Lowering the coherence-gate threshold** — `feedback_thresholds_no_lower` + the gate is doing its job per `next_v3 §13.10.x`. Diagnostic in §1 targets upstream causes.
- **Per-topic statistical claims from the 100-Q gauge** — sample size doesn't support it. Gauge is for global movement, not topic deltas.
- **GUI corpus-retire flow** — `CLAUDE.md` non-negotiable: cloud retirements are CLI-explicit only. Never propose a GUI delete button.
- **Anything touching the Falkor adapter's "errors propagate" invariant** — the staging adapter must keep failing loudly on cloud outages. No silent fallback to artifacts.

---

## Cross-references

- v4 (record of 2026-04-25/26 ship cycle): [`next_v4.md`](./next_v4.md)
- Six-gate policy: [`README.md`](./README.md)
- Falkor parity diagnostic + cap audit: [`docs/learnings/ingestion/falkor-edge-undercount-and-resultset-cap-2026-04-26.md`](../learnings/ingestion/falkor-edge-undercount-and-resultset-cap-2026-04-26.md)
- 100-Q gauge fixtures + rubric: [`evals/100qs_accountant.jsonl`](../../evals/100qs_accountant.jsonl), [`evals/100qs_rubric.yaml`](../../evals/100qs_rubric.yaml)
- Comparative-regime config: [`config/comparative_regime_pairs.json`](../../config/comparative_regime_pairs.json)

---

*Opened 2026-04-26 after the v4 ship cycle wound down (conversational-memory L1+L2 shipped; comparative-regime mode shipped; 100-Q gauge code landed; parity-probe diagnostic + 10k cap audit closed). v5 carries the still-pending verifications, the deferred-but-still-relevant items, and §7 (retrieval-depth envelope calibration) — a new operator-surfaced design question that can only be answered empirically through the gauge once §5.1 produces a baseline.*
