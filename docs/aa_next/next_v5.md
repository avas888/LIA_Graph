# next_v5 — forward plan opened 2026-04-26

> **Opened 2026-04-26** as the live forward-facing surface after `next_v4.md` accumulated the gate-9 qualitative-pass debt + the 2026-04-25/26 ship cycle (conversational-memory staircase L1+L2, comparative-regime mode, 100-Q gauge, parity-probe diagnostic).
>
> v4 stays in this folder as the **record of what was done in that cycle**. Active work — anything still 💡 idea, 🛠 awaiting verification, or with an open success-criterion measurement — lives here. v5 also carries one new investigation surfaced 2026-04-26: retrieval-depth envelope calibration (§7).
>
> **Policy (carries from v3/v4).** Six-gate lifecycle per `docs/aa_next/README.md`: 💡 idea → 🛠 code landed → 🧪 verified locally → ✅ verified in target env → ↩ regressed-discarded. **Every step's gate-3 success criterion must be measured, not asserted.** Unit-tests-green ≠ improvement.

---

## §1 Coherence-gate calibration diagnostic (carried from v4 §1)

**Status:** 💡 idea — opened 2026-04-25, not yet started. Awaits next_v3 close.

**One-sentence idea.** Measure whether the 11 `coherence_misaligned=True` questions concentrate in topics with thin corpus coverage (corpus problem) or distribute across topics evenly (calibration problem) — diagnose before intervening (`feedback_diagnose_before_intervene`).

**Full plan + measurement set + early signal:** see [v4 §1](./next_v4.md#1-coherence-gate-calibration-diagnostic-operator-scoped-2026-04-25). The 11-Q fixture and the `corpus_coverage` taxonomy flags are unchanged.

**Why it's still here.** Diagnostic instrumentation (chunk-level coherence scores) hasn't been written. SME-binding chunk-pair inspection hasn't run. Decision rule unchanged: concentrated → corpus expansion (free, per §10.5); distributed → coherence-gate recalibration (real engineering).

**Effort:** ~1-2 days engineering + ~3-5 hours SME + ~half day aggregation.

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

#### §6.2 (carries v4 §6.5.D) — Sub-bucket the 33% endpoint-missing
Sub-bucketing pass on `scripts/diag_falkor_edge_undercount.py`: split bucket (a) (9.934 edges) into (a1) prose-only key mismatch / (a2) genuinely orphaned / (a3) reform-side missing. Decision: if (a1) ≥ 70% → fix the classifier to emit `_graph_article_key()`; recovery upside ≤ 9.934 edges. Full plan: [v4 §6.5.D](./next_v4.md#item-65d--investigate-the-33-endpoint-missing-bucket-opened-2026-04-26).

**Effort:** ~30 LoC sub-bucketing + diagnostic re-run (~1 hour). Decision-branch follow-up: ~1-2 days if (a1) dominates.

#### §6.3 (carries v4 §6.5.B watchlist) — Silent-drop bucket re-measurement
Bucket (b) = 54 (`references → CITA`, < 0,2%) recorded as qualitative-pass per case. **Re-run the diagnostic after the next staging delta** (§6.2 sub-bucketing already requires this anyway). Decision: if (b) grows > 100 → escalate to a §6.4 writer-investigation; if stays ≤ 100 → close §6.3 as expected variance.

#### §6.4 (carries v4 §6.5.E) — Operator-staging silence verification
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
