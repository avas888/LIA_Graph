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

**§1.A — Multi-topic ArticleNode metadata (structural, ~3-5 days)**
- Add `secondary_topics: text[]` to `:ArticleNode` schema in Falkor + the loader's MERGE writes.
- SME-curated mapping of ~30-50 high-traffic articles to their secondary topics (Art. 689-3 + `[firmeza_declaraciones, beneficio_auditoria]`, Art. 49 + `[ingresos_fiscales_renta, dividendos_y_distribucion_utilidades]`, etc.).
- Coherence-gate code: accept primary if `query_topic ∈ {primary.topic} ∪ primary.secondary_topics`.

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
