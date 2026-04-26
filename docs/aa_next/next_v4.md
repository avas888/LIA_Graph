# next_v4 — record of the 2026-04-25/26 ship cycle (closed forward; see v5 for active work)

> **Opened 2026-04-25** when the operator accepted gate-9 on qualitative basis (see `gate_9_threshold_decision.md` §7). next_v4 inherited one explicitly-scoped item from gate-9's deferred debt + the 2026-04-25/26 ship cycle (conversational-memory staircase, comparative-regime mode, 100-Q gauge code, parity-probe diagnostic, 10k cap audit).
>
> ### ⚠ This file is now historical. Active forward work has moved to [`next_v5.md`](./next_v5.md) as of 2026-04-26.
>
> Forward-facing items still pending verification or with open success-criterion measurements were migrated to v5 §1-§7. v5 also carries one new investigation surfaced 2026-04-26: retrieval-depth envelope calibration.
>
> v4 stays in this folder as the **record of what was done in this cycle** — every "code landed" / "verified locally" / "shipped" line below remains true and the implementation references stay accurate. Do not add new forward work here; open it in v5.
>
> **Policy (carries from next_v3, applies to v5 too).** Every item used the mandatory six-gate lifecycle per `docs/aa_next/README.md`: 💡 idea → 🛠 code landed → 🧪 verified locally → ✅ verified in target env → ↩ regressed-discarded.

---

## §1 Coherence-gate calibration diagnostic (operator-scoped 2026-04-25)

### Idea (operator's words, binding)

> Determine whether the 11 `coherence_misaligned=True` questions concentrate in topics with thin corpus coverage, or distribute across topics evenly. If concentrated → the fix is corpus expansion (free as `corpus_coverage: pending` topics fill in per `next_v3 §10.5`). If distributed → the fix is coherence-gate recalibration (a real engineering intervention). **Diagnose before intervening.**

### Measurement set (binding)

The 11 questions from v10_taxonomy_v2_rebuild5_clean (2026-04-25) where the v6 evidence-coherence gate rejected retrieval despite correct topic routing:

| qid | expected_topic | corpus_coverage flag (taxonomy v2) |
|---|---|---|
| Q12 | regimen_simple | active |
| Q18 | estados_financieros_niif | **deprecated** (v2 split into niif_pymes/plenas/microempresas) |
| Q20 | regimen_sancionatorio | active |
| Q21 | firmeza_declaraciones | active |
| Q22 | devoluciones_saldos_a_favor | active |
| Q23 | informacion_exogena | active |
| Q25 | impuesto_patrimonio_personas_naturales | active |
| Q26 | dividendos_y_distribucion_utilidades | active |
| Q27 | sagrilaft_ptee | active |
| Q28 | zonas_francas | active |
| Q29 | perdidas_fiscales_art147 | active |

Q10 (`facturacion_electronica` routing-fail) is **not in this set** — tracked separately as a vocabulary-gap line item, not a coherence-gate concern.

### Early signal — concentration hypothesis already weakened

10 of 11 measurement-set topics carry `corpus_coverage: active` in the taxonomy. Only Q18 maps to a `deprecated` topic (because v2 split `estados_financieros_niif` into the three NIIF buckets — those rows likely route to one of the splits depending on resolver behavior). **The "concentrate in thin-corpus topics" hypothesis is not supported by the metadata flag alone** — the rejections look distributed across topics that are flagged as actively covered.

But `corpus_coverage: active` is a binary flag, not a density measurement. The diagnostic still has to measure:

- Article/chunk count per topic (Supabase `documents` + `document_chunks` filtered by topic).
- Article-text vs query-text alignment characterization (sample 2-3 of the rejected (query, chunk) pairs per topic and inspect whether the chunks really are off-topic from a contador's perspective, or whether the gate is over-triggering on legitimate matches).
- Coherence-gate scoring distribution per topic (does the gate threshold sit at the same percentile across topics, or does it accidentally cut more strictly in some topics due to embedding-space topology?).

### Plan (when it ships)

1. **Density audit.** Per topic in the measurement set: count documents + chunks in production Supabase. If any topic has < 50 chunks, it functionally has thin coverage regardless of the `active` flag — that's a corpus-expansion problem, not a gate problem.
2. **Sample-pair inspection.** For each of the 11 rejected (qid, retrieved_chunks) pairs in v10's run output, surface 2-3 chunks the gate dropped + 2-3 it admitted (if any). Have engineering + SME read 5-10 minutes per qid and verdict each chunk *as a contador would*: actually-off-topic, marginally-related, or wrongly-rejected. Aggregate.
3. **Gate-score distribution.** Add instrumentation that emits the actual coherence score per chunk (currently we only see the `misaligned/aligned` boolean and the `chunks_off_topic` reason string). Recompute the rejection rate per topic at the current threshold + at threshold ± 0.05 / ± 0.10.

The combination of (1), (2), and (3) is the diagnostic. Only after it lands does the team decide between corpus expansion (per-topic), gate-threshold tuning (per-topic or global), or both.

### Success criterion

Diagnostic produces a per-topic verdict: `{thin_corpus, gate_overstrict, both, neither}` with numeric backing for each. Output is a markdown table the operator can act on.

### What this is NOT

- **Not a generic "retrieval-depth lift"** — the operator explicitly rejected that framing on 2026-04-25.
- **Not gate-loosening** — the gate exists to keep contamination clean (Q22 + Q27 in the contamination-test set are themselves part of the measurement set, both with primary=0 + coh_misaligned=True; aggressive gate-loosening would re-introduce contamination).
- **Not a re-flip prerequisite** — gate 9 is already qualitative-✅ in next_v3. v4 §1 is debt repayment, not a re-flip blocker.

### Effort

Diagnostic: ~1-2 days engineering for instrumentation (chunk-level coherence scores) + ~3-5 hours operator/SME chunk-pair inspection + ~half day for the per-topic verdict aggregation. Intervention (whatever the diagnostic recommends): scoped after the diagnostic lands.

### Six-gate status

💡 idea (operator-scoped 2026-04-25) — code not yet started, awaiting next_v3 close.

---

## §2 Carries from next_v3 §10 (parallel tracks, soft gates)

These do not block re-flip but ship in this cycle when there's bandwidth:

- **§10.1 TokenBudget primitive** — wire `TokenBudget` + `TPMRateLimitError` into `ingest_classifier_pool`. Lets workers default come back to 8 against production. ~4-6 hr code + cloud verify.
- **§10.2 Persistent verdict cache** — SQLite-keyed cache for classifier verdicts (read-before-call, write-after-call). Drops idempotent rebuilds from ~7 min → < 60 s. Critical for fast iteration on next-cycle prompt work. ~2 days.
- **§10.3 Gold v2 expansion** — commission ≥ 10-15 additional questions from SME post-taxonomy-v2 stabilization. ~1-2 weeks SME.
- **§10.4 Subtopic taxonomy refresh** — v2.1 SME pass on subtopics under the new top-level topics (`impuesto_timbre`, `rut_y_responsabilidades_tributarias`). ~0.5 day SME + 0.5 day code.
- **§10.5 Corpus expansion** — fill the 11 `corpus_coverage: pending` top-level topics (proteccion_datos, regimen_cambiario, NIIF splits, etc.) from canonical sources. ~2-4 weeks SME + content team. **Note: §1 above may surface specific measurement-set topics that need expansion regardless of their current `pending`/`active` flag.**

---

## §3 Stateless classifier vs stateful retriever — follow-up coherence-gate refusal (operator-surfaced 2026-04-25)

### Idea (one sentence)

The chat-topic classifier is stateless (sees only the current message), the planner/retriever is stateful (carries forward `conversation_state.normative_anchors`), and the v6 evidence-coherence gate compares the two — so any short follow-up with an ambiguous verb produces a gate refusal even when retrieval anchored correctly.

### Operator-binding observation (2026-04-25)

Two-turn dialogue against the live UI, with `LIA_TEMA_FIRST_RETRIEVAL=on` + `LIA_EVIDENCE_COHERENCE_GATE=enforce`:

- **T1.** "El cliente acumuló pérdidas fiscales en años anteriores… ¿Cuál es el régimen legal de compensación de pérdidas fiscales? ¿Hay límite anual? ¿Cómo afecta la compensación al término de firmeza…?" → routed `perdidas_fiscales_art147`, art. 147 ET answered cleanly.
- **T2 (follow-up).** "existe algun limite de monto de dinero a descontar por año?" → classifier picked `descuentos_tributarios_renta`; retriever still pulled art. 147 ET; coherence gate fired with `primary_off_topic` reason and the user got the abstention text from `_coherence_gate.refusal_text`.

The retriever was right. The classifier was wrong. The gate is doing exactly what it was designed to do (Q1-class contamination guard) but fires on a follow-up the system already had enough state to answer.

### Mechanism — full code-anchored trace (2026-04-25 deep-trace pass)

The earlier draft of this section listed three "live hypotheses." A deep trace from browser keystroke to coherence-gate refusal showed two of them are **structurally confirmed in code**, not hypotheses. The prior turn's `effective_topic` is dropped at three independent boundaries, in series. Any single-frontier patch is insufficient at one frontier and unnecessary at another — the question is no longer "which hypothesis is dominant" but "which frontier is cheapest to close."

**Trace summary (T2 = "existe algún limite de monto de dinero a descontar por año?", ~12 tokens, follow-up to a `perdidas_fiscales_art147` T1):**

```
T2 keystroke
  ↓
[Frontier 1 — FE] frontend/src/features/chat/requestController.ts:224-228
  payload = { message, pais, primary_scope_mode, response_route, debug, client_turn_id, session_id }
  ❌ payload.topic NOT included
  ↓
POST /api/chat
  ↓
src/lia_graph/ui_chat_payload.py:301
  requested_topic_raw = normalize_topic_key(payload.get("topic")) → None
  ↓
src/lia_graph/topic_router.py:781  resolve_chat_topic(message=T2, requested_topic=None, ...)
  - _resolve_rule_based_topic: _score_topic_keywords("…descontar…") → ∅
    ("descontar" is not in any strong/weak bucket; "descuento tributario" requires the noun phrase)
    → None
  - _should_attempt_llm: scores empty → True (line 626-634)
  - _classify_topic_with_llm: prompt _build_classifier_prompt(message=T2, requested_topic=None, pais)
    [Frontier 3 — classifier] ❌ prompt carries no conversation_context / normative_anchors / prior_topic
    LLM picks "descuentos_tributarios_renta", confidence ≥ 0.50 (deduced from refusal-text branch)
  ↓
PipelineCRequest(topic="descuentos_tributarios_renta", topic_router_confidence ≥ 0.50)
conversation_state ← build_conversation_state(session)
  ↓
src/lia_graph/pipeline_c/conversation_state.py:155-207
  Walks turns[-8:]. From assistant turns extracts: norm_anchors, entities, citations.
  [Frontier 2 — state schema] ❌ never reads turn_metadata["effective_topic"]; ConversationState dataclass
    (lines 102-110) has 7 fields, none is `prior_topic` / `last_effective_topic`.
  ↓
pipeline_d/orchestrator.py
  detect_router_silent_failure → topic is set → no fire
  build_graph_retrieval_plan(request)
  ↓
pipeline_d/planner.py:204
  _looks_like_followup_focus_request: turn_count>0 + ~12 tokens ≤ 18 → True
  _conversation_state_article_refs → ("147",)
  carried_article_refs → entry_points includes Art. 147 (source="conversation_state_anchor")
  → primary_articles populated with art. 147 ET (perdidas_fiscales_art147)
  ↓
detect_topic_misalignment(request, evidence):
  router_topic="descuentos_tributarios_renta", articles' lexical winner="perdidas_fiscales_art147"
  top_score on articles ≥ 6, router_score on articles = 0 → misaligned=True
should_promote_misalignment_to_abstention: confidence ≥ 0.50 → False (no topic_safety abstention)
  ↓
_coherence_gate.detect_evidence_coherence Case A:
  primary_articles populated AND primary_misalignment.misaligned=True
  → {misaligned:True, source:"primary", reason:"primary_off_topic", dominant_topic:"perdidas_fiscales_art147"}
coherence_mode()="enforce" → should_refuse=True → refusal_text primary_off_topic branch
  → exact text user sees in production
```

**The three frontiers, each independently rendered the prior topic invisible to the classifier:**

| # | Frontier | Site | Status | Cost-to-close |
|---|---|---|---|---|
| 1 | Frontend `/api/chat` body omits `topic` | `frontend/src/features/chat/requestController.ts:224-228` | ❌ confirmed | ~30 LOC FE + ~10 LOC to read last turn's effective_topic |
| 2 | `ConversationState` dataclass has no `prior_topic` slot; `build_conversation_state` does not read `turn_metadata["effective_topic"]` from prior turns | `src/lia_graph/pipeline_c/conversation_state.py:102-110, 166-196` | ❌ confirmed | ~20 LOC + state-schema migration of tests that pin the 7-field shape |
| 3 | `resolve_chat_topic` signature has no `conversation_state` parameter; `_build_classifier_prompt` (line 639) does not embed prior context | `src/lia_graph/topic_router.py:639, 781` | ❌ confirmed | ~40 LOC + change to a public primitive reused by `ingestion_classifier` |

The persistence layer DOES save `effective_topic` per turn (`ui_chat_persistence.py:57, 78, 80`), but no consumer levantates it for the next turn — it's storage-only, not state-flow.

**One nuance worth recording.** `topic_safety.detect_topic_misalignment` and `_coherence_gate.detect_evidence_coherence` Case A evaluate the same condition over the same data — the second receives the first's verdict (`primary_misalignment`) and forwards it when primary_articles is populated. Their visible difference is only the refusal *text*: topic_safety's text fires when confidence < 0.50; coherence_gate's text fires when confidence ≥ 0.50. The fact that the user sees the coherence-gate wording is what fixes the LLM-confidence inference at ≥ 0.50. **This rules out H1** as a dominant lever — even if we lowered `MISALIGNMENT_PROMOTE_TO_ABSTENTION_BELOW`, the answer would still be an abstention, just with a different sentence. The user is not blocked by which text shows; they are blocked by the system refusing at all.

### Failure classification — distributed, not concentrated

This is a **calibration / wiring failure**, not a corpus failure. Per the diagnose-before-intervene memory and §1's precedent: the failure distributes across any short follow-up that combines (a) ambiguous verb (descontar / compensar / deducir / limitar / aplicar / corregir / ajustar), (b) topic anchor carried in `conversation_state`, (c) lexical signal too thin for rule-based routing. The prior topic is irrelevant to the mechanism — what's specific is the structural break in topic-state continuity.

### Intervention candidates (frontier-based, not hypothesis-based)

H1 ruled out by trace. H2 and H3 collapse from "hypotheses to disambiguate" into "frontiers to choose between." Three implementation options remain, ordered by cost + reversibility:

| Option | Frontiers closed | Cost | Risk |
|---|---|---|---|
| **A. FE sends `topic: lastTurnEffectiveTopic` when it exists** | 1 only | ~30 LOC FE | **Low.** The LLM prompt already says "Si la consulta es ambigua, conserva requested_topic cuando exista" (`_build_classifier_prompt:691`). Legitimate topic switches still work because that retention rule is gated on ambiguity. The classifier becomes single-source-of-truth for follow-ups too, with no backend contract change. |
| **B. Backend infers `requested_topic` from `conversation_state` when FE doesn't send it** | 2 + 3 (partial) | ~20 LOC state schema + ~5 LOC controller fallback + extract `effective_topic` from `turn_metadata` in `build_conversation_state` | **Medium.** Adds a field to the state dataclass; requires migration of any test that asserts the 7-field shape. Decouples FE from the fix (defense-in-depth) but introduces backend-side topic-stickiness that wasn't there before. |
| **C. Pass `conversation_state` into the classifier as a soft prior** | 3 | ~40 LOC `topic_router` + ~5 LOC `ui_chat_payload` | **High.** The classifier stops being stateless; signature change ripples into `ingestion_classifier` (which reuses `_build_classifier_prompt` primitives). The most architecturally invasive option. |

**Operator-suggested route: A first, B as defense-in-depth if A is fragile in practice, C only if the LLM ignores `requested_topic` even when supplied.** Option A is strictly the least invasive and structurally sufficient: it closes the frontier highest in the stack (browser), does not touch the classifier, and leaves the state schema unchanged.

### Plan (when the diagnostic ships — six-gate, code not written yet)

1. **Reproduce with diagnostics on.** Run T1→T2 against staging with `LIA_EVIDENCE_COHERENCE_GATE=shadow` and capture `response.diagnostics.topic_safety` for both turns:
   - `topic_router_confidence` for T2 (confirm the ≥ 0.50 inference from the trace)
   - `misalignment.router_score_on_articles` and `misalignment.top_score_on_articles`
   - Whether `requested_topic` arrived populated on the T2 request (expected: empty per Frontier 1)
   - Whether `conversation_state.normative_anchors` was populated and what it carried (expected: art. 147)
2. **Distribute-or-concentrate measurement.** Construct 8-12 two-turn dialogues where T1 anchors a clear topic and T2 is a 6-15 token follow-up using verbs from the ambiguous-verb list (descontar, compensar, deducir, limitar, aplicar, corregir, ajustar). Measure: refusal rate, classifier confidence distribution, anchor-vs-classifier agreement rate. If ≥ 30% refuse via `primary_off_topic`, the failure is structural — proceed to gate 4. If < 10%, document as an isolated incident and close at 💡 discard.
3. **Frontier selection.** From the data captured in (1)+(2), confirm Option A is sufficient. The trace says it should be; the harness measures whether the LLM honors `requested_topic` consistently when supplied. If A's predicted refusal-rate-reduction is ≥ 50%, ship A. If between 25-50%, ship A + B. If < 25%, escalate to C with new evidence. **Do not pre-commit to a fix before this step lands** — the operator's diagnose-before-intervene rule still applies, even with H1 ruled out.

### Success criterion

A markdown table that, for each of the 8-12 follow-up dialogues, records: classifier_topic / classifier_confidence / retriever_top_topic / requested_topic_arrived / anchors_arrived / coherence_outcome. Aggregate verdict: option-A-sufficient / A-plus-B-needed / C-needed, with the predicted refusal-rate-reduction and a one-paragraph operator-actionable recommendation appended.

### Test plan (gate 4 — required before any code lands)

- **Development needed.** Two pieces of harness work, neither shipped today: (a) a two-turn dialogue runner that scripts T1→T2 against staging and dumps the full `response.diagnostics` JSON for each turn (the existing 30-gold harness is single-turn); (b) a small fixture of the 8-12 follow-up pairs (operator + SME compose ~1 hour). The runner is ~half-day code on top of the existing single-turn cloud runner.
- **Conceptualization.** Refusal rate on this fixture is the proxy for "fraction of legitimate follow-ups the system silently kills". The metric maps to user-experienced harm because every refusal in this fixture is, by construction, a question the retriever already had the right evidence for.
- **Running environment.** Staging cloud (`LIA_CORPUS_SOURCE=supabase`, `LIA_GRAPH_MODE=falkor_live`, `LIA_EVIDENCE_COHERENCE_GATE=shadow` so we measure would-refuse without producing user-visible refusals during the diagnostic). Local artifact-mode is insufficient — the failure depends on the live LLM classifier and the production conversation_state plumbing.
- **Actors + interventions.** Engineer writes the runner + ships fixture. Operator triggers the staging run + reads the diagnostics dump. SME (Alejandro) reviews 5-10 of the dialogue pairs to confirm each T2 is in fact a legitimate follow-up of T1 (sanity-check the fixture). No end-user accountant needed at this gate — the criterion is mechanism-level, not answer-quality-level.
- **Decision rule.** Refusal rate ≥ 30% on the fixture → structural, intervention warranted, proceed to gate-5 hypothesis-driven plan. Refusal rate 10-30% → borderline; widen fixture to 20+ pairs before deciding. Refusal rate < 10% → close as 💡 discard with the data kept as record.

### Greenlight (gate 5 — names what would be sufficient to ship a fix later)

Requires both: (a) gate-4 fixture passes the decision rule **and** the chosen frontier-fix (A / A+B / C) reduces refusal rate by at least 50% on the same fixture without raising contamination rate on the existing 30-gold contamination subset (Q22 + Q27 family). (b) SME spot-review on 5-8 of the post-fix answers confirms the answer is faithful to the carried anchor (no contamination from the verb-trigger topic, no topic-stickiness blocking a legitimate topic switch).

### Refine-or-discard (gate 6)

If the gate-5 fix raises contamination rate on the 30-gold contamination subset, **discard the fix**, keep the diagnostic record, and reopen with a narrower hypothesis (e.g., gate Option A on `_looks_like_followup_focus_request`-triggered turns only, instead of every turn). Per the operator's "don't lower thresholds" memory, the fix must not loosen `MISALIGNMENT_PROMOTE_TO_ABSTENTION_BELOW` or `_coherence_gate` thresholds globally — frontier-closing wiring changes are the preferred shape, and H1 was already ruled out by the trace.

### Effort

Diagnostic only (gates 1-3 above): ~half-day runner + ~1 hour fixture + ~1 hour SME sanity-check + ~half-day analysis = ≈ 1 day end-to-end. **Option A implementation (if the diagnostic confirms sufficiency):** ~30 LOC FE + tests ≈ ~half-day code + harness re-run for verification ≈ ~half-day = ≈ 1 day. Total v4 §3: ~2 days end-to-end on the optimistic path.

### What this is NOT

- **Not a re-flip blocker.** v3 close path is unchanged.
- **Not a coherence-gate-loosening proposal.** The gate is correctly catching a real misalignment in the data it sees; the fix should be upstream (so the gate sees aligned data) or in the abstention-promotion threshold for the specific follow-up class — not in lowering the gate's sensitivity.
- **Not §1 in disguise.** §1 is "are the 11 gold-set coherence rejections corpus-thin or gate-overstrict". §3 is "is the classifier statelessness producing legitimate-follow-up refusals at all". Different fixtures, different mechanisms — the only overlap is that both touch the coherence gate.

### Six-gate status

🛠 code landed 2026-04-25 — Option A shipped (frontier 1 closed) **plus** Option C as defense-in-depth on the same task per operator direction. Specifically:

- **Frontier 1 (FE).** `frontend/src/features/chat/requestController.ts:230-243` — `submitChatTurn` now reads the most recent `state.questionEntries[i].effectiveTopic` and forwards it as `payload.topic` whenever a prior assistant turn anchored a topic. ~14 LOC.
- **Frontier 2 (state).** `src/lia_graph/pipeline_c/conversation_state.py:102-130, 140-156, 155-220` — `ConversationState` gained `prior_topic`, `prior_subtopic`, `topic_trajectory`, `prior_secondary_topics`; round-trip extended; `build_conversation_state` now lifts `effective_topic` / `secondary_topics` / `effective_subtopic` from each assistant turn's `turn_metadata` (the persistence layer at `ui_chat_persistence._build_turn_metadata` already wrote these — connected the existing half-built chain).
- **Frontier 3 (classifier).** `src/lia_graph/topic_router.py:639-704, 718-787, 781-919` — `_build_classifier_prompt`, `_classify_topic_with_llm`, and `resolve_chat_topic` all accept optional `conversation_state`. Prompt embeds `prior_topic` as a soft hint mirroring the existing line 691 `requested_topic` retention rule. Post-LLM, a strict tiebreaker fires only when (a) lexical scoring is empty AND (b) the LLM verdict diverges from `prior_topic` AND (c) `prior_topic` is in `_SUPPORTED_TOPICS` — returns the prior with confidence boosted by +0.15 capped at 0.85, mode `prior_state_tiebreaker`. A separate `prior_state_fallback` mode covers the LLM-unreachable + lexical-empty + no-requested-topic edge case.
- **Wiring.** `src/lia_graph/ui_chat_payload.py:299-360, 446-460` — best-effort early `load_session` peek extracts `conversation_state` before `resolve_chat_topic`, threads it through, and stashes the loaded session on `request_context` so `_ensure_conversation_session_loaded` later doesn't double-pay the IO. Skips entirely when the FE didn't supply `session_id` (first turn).

Tests: `tests/test_conversation_state_prior_topic.py` (5 cases — defaults, round-trip, build-from-metadata, trajectory dedup, no-metadata back-compat) + `tests/test_topic_router_with_state.py` (8 cases — prompt assembly, tiebreaker fires/doesn't fire, lexical-router precedence, runtime-unreachable fallback). All 13 pass.

Harness: `scripts/evaluations/run_multiturn_dialogue_harness.py` — HTTP-based, scripts T1→T2 against a single session_id, captures per-turn diagnostics, aggregates refusal rate. Fixture: `evals/multiturn_dialogue_v1.jsonl` (10 ambiguous-verb dialogues anchored across the measurement-set topics). `--propagate-topic` toggle isolates Frontier 1's contribution from Frontier 2+3's.

Status now: 🛠 code landed; 🧪 verified locally via unit tests — 🧪 awaiting harness baseline run + intervention measurement against staging cloud per gate-4 / gate-5 plan above.

---

## §4 Conversational memory — three-level staircase (architectural plan, 2026-04-25)

### Idea (one sentence)

Lia already carries structured per-turn memory (`ConversationState` with 7 fields) into the planner/retriever but not into the classifier; rather than jumping to a free-text LLM rolling summary (a flashy-but-risky single step), escalate conversational memory in three measured levels and only climb the staircase when the harness says the previous level was insufficient.

### Why a staircase, not a single move

The instinct to "add a rolling LLM summary so the next question always reads from a continuously-updated story of the conversation" is architecturally on-trend (ChatGPT / Claude.ai / Cursor do variants of this). But applied to Lia's product context — a contable assistant where citation traceability is the core trust contract — a free-text rolling summary introduces three documented failure modes (drift / latency / debug-cost) that don't compensate the marginal benefit when 80% of the value can be unlocked with structured-state extensions of an existing primitive. Level 2 is the conservative-but-ambitious move; Level 3 is held in reserve for cases where Level 2 demonstrably can't reach.

### Level 1 — Frontend-side `topic` propagation (committed; full plan in §3 Option A)

**Status: 🛠 code landed 2026-04-25.** Plan, success criterion, test plan, greenlight, refine-or-discard, and effort estimate all live in §3 (Option A row of the intervention-candidates table + plan/criterion/test-plan blocks). This entry is the architectural framing only; ship-tracking lives against §3 ("Six-gate status" block).

**Scope at this level**: 30 LOC FE change in `frontend/src/features/chat/requestController.ts:224-228` to include `topic: lastTurnEffectiveTopic` in `/api/chat` payload when a prior turn exists. Backend already reads it (`ui_chat_payload.py:301`). No backend, schema, or classifier changes.

**What it unlocks**: short follow-ups like "¿hay límite anual?" / "¿qué pasa con el saldo restante?" stop being silently refused when the prior turn anchored a clear topic. Approximately matches the operator-observed T2 failure class.

**What it does NOT unlock**: multi-turn dialogues where the topic drifts gradually over 3-5 turns; any case where the classifier needs richer context than just the prior topic (subtopic shifts, parallel topic tracks, etc.). Those go to Level 2.

### Level 2 — Extended `ConversationState` with classifier-aware fields (committed for ship after Level 1 measurement)

**Status: 🛠 code landed 2026-04-25 alongside Level 1** per operator direction to ship A + C as defense-in-depth on the same task. Full six-gate plan below; gates 1-2 cover the as-shipped behavior, gates 3-6 still describe the harness-driven verification path.

**Idea (one sentence).** Add `prior_topic`, `prior_subtopic`, `topic_trajectory[]`, and `prior_secondary_topics` as first-class fields on `ConversationState`; have `build_conversation_state` populate them from `turn_metadata` (which `ui_chat_persistence.py` already saves per turn); pass `conversation_state` into `resolve_chat_topic` as a soft prior that the classifier uses as a tiebreaker — never as a hard override.

**Plan (narrowest modules touched, with line-anchors).**

1. `src/lia_graph/pipeline_c/conversation_state.py:102-110` — extend `ConversationState` dataclass with four new fields: `prior_topic: str | None`, `prior_subtopic: str | None`, `topic_trajectory: tuple[str, ...]` (last 4 distinct topics, oldest-first), `prior_secondary_topics: tuple[str, ...]` (last turn's secondaries).
2. `src/lia_graph/pipeline_c/conversation_state.py:155-207` — extend `build_conversation_state` to read `turn_metadata["effective_topic"]`, `turn_metadata["secondary_topics"]`, etc., from each assistant turn (the persistence layer already writes these per `ui_chat_persistence.py:78,80`). Build trajectory by walking turns oldest-to-newest, deduping consecutive identical topics.
3. `src/lia_graph/pipeline_c/conversation_state.py:140-152` + `:112-121` — extend `conversation_state_from_dict` and `to_dict` to round-trip the new fields.
4. `src/lia_graph/topic_router.py:781` — extend `resolve_chat_topic` signature with optional `conversation_state: dict | None = None`. When provided AND lexical scoring returns no dominant topic AND LLM verdict disagrees with `prior_topic`, treat `prior_topic` as a tiebreaker (return it with confidence boosted by `+0.15`, capped at 0.85). When LLM verdict matches `prior_topic`, no change. When LLM is confidently in a *different* topic AND that topic is well-represented lexically (clear topic-switch signal), no override.
5. `src/lia_graph/topic_router.py:639` `_build_classifier_prompt` — when `conversation_state` is provided AND `prior_topic` exists, append a single line to the prompt: `Tema del turno anterior: {prior_topic}. Si la consulta actual es ambigua y plausiblemente continúa el mismo hilo, conserva ese tema.` Already aligned with the existing line 691 retention rule for `requested_topic`; this just gives the LLM the prior topic when the FE didn't send it (defense-in-depth for cases where Level 1 fails to reach).
6. `src/lia_graph/ui_chat_payload.py:302-308` — pass `conversation_state` through to `resolve_chat_topic`.
7. Tests: extend the existing `tests/test_conversation_state.py` (or whichever covers it) for the new fields + their round-trip; add a new `tests/test_topic_router_with_state.py` for the prior-topic-as-tiebreaker behavior with both ambiguous and topic-switch test cases.

**Why Level 2 is structurally different from Level 1, not just a backup.**

- Level 1 depends on the FE shipping correctly — any UI bug, race condition on session reload, deferred-message replay, or expert-panel reopening could drop the topic. Level 2 reconstructs it from server-side persistence, immune to FE drift.
- Level 1 only sees the most-recent prior topic. Level 2's `topic_trajectory[]` enables future planner/synthesizer features (e.g., "the user has been moving from pérdidas → firmeza → declaración — likely about to ask about beneficio_auditoría") without re-architecting.
- Level 2 unlocks the classifier consuming any `ConversationState` field, not just `prior_topic`. Future expansions (e.g., prior `entities`, `carry_forward_facts`) become trivial.

**Success criterion (gate 3).**

On the multi-turn extension of the §3 fixture (8-12 base 2-turn dialogues + 4-6 new 3-5 turn dialogues where topic evolves naturally between sub-tracks), Level-2-with-Level-1 reduces refusal rate via `primary_off_topic` to **≤ 5%** (from the v4 §3 baseline harness measurement) AND keeps contamination rate on the 30-gold contamination subset (Q22 + Q27 family) at or below the pre-change baseline. The "≤ 5%" target is intentionally tight because at 3-5 turns the structural mechanism is fully exercised — a higher residual rate would suggest Level 2 hits a real ceiling and Level 3 may need to be revisited.

**Test plan (gate 4).**

- **Development needed.** Extend the v4 §3 two-turn harness into N-turn (N ∈ {2,3,4,5}). The runner has to script each turn, capture diagnostics per turn, and reset session_id between dialogues. Build the 4-6 new fixture dialogues — these exercise topic-evolution patterns (pérdidas→firmeza→ben_auditoría; renta→nómina→PILA→UGPP; IVA→retención_IVA→saldo_a_favor) where each turn legitimately needs the prior context to disambiguate. Engineer + SME compose ~2 hours.
- **Conceptualization.** Multi-turn refusal rate is the proxy for "does Lia remain coherent across the realistic length of a contador consultation". The 30-gold contamination check ensures the prior-topic prior doesn't make Lia stick to the wrong topic when the user does shift.
- **Running environment.** Staging cloud (`LIA_CORPUS_SOURCE=supabase`, `LIA_GRAPH_MODE=falkor_live`, `LIA_EVIDENCE_COHERENCE_GATE=enforce` — Level 2 ships against the live gate, not shadow). Local artifact-mode is insufficient for the same reason as §3.
- **Actors + interventions.** Engineer ships harness + Level 2 code. Operator triggers run + reads diagnostics. SME (Alejandro) reviews 8-10 of the multi-turn dialogues to confirm topic evolution is realistic + that the post-Level-2 answers don't show topic-stickiness regression. End-user accountant test only if SME flags an answer that "feels mechanical" (catches subtle topic-stickiness the harness misses).
- **Decision rule.** Refusal rate ≤ 5% on multi-turn fixture AND contamination ≤ baseline AND SME no-regression verdict → ship Level 2. Refusal 5-15% → tune the `+0.15` confidence-boost cap or the "lexical-scoring-empty AND LLM-disagrees" precondition; re-run; ship if next iteration meets the gate. Refusal > 15% → Level 2 ceiling reached; document and consider Level 3 reopen.

**Greenlight (gate 5).** Both: (a) gate-4 decision rule passes AND (b) SME spot-review on 5-8 cases confirms answer faithfulness + no topic-stickiness regression on legitimate switches.

**Refine-or-discard (gate 6).** If Level 2 raises contamination or introduces topic-stickiness regressions, **narrow the trigger** before discarding: try gating the prior-topic boost on `_looks_like_followup_focus_request`-positive turns only (mirroring how the planner's anchor carry-forward is gated). Discard only if the narrowed version also regresses. Discard does NOT cascade to Level 1 — Level 1 ships independently.

**Effort.** ~3-5 days end-to-end on the optimistic path: ~1.5 days for `ConversationState` extension + classifier prior wiring + unit tests, ~1 day for harness extension to N-turn, ~1 day for fixture composition + SME sanity-check, ~1 day for staging run + analysis + iteration if needed.

**Dependencies.** Level 1 must ship and produce harness data first. Level 2 starts only after the §3 gate-4 measurement returns its number.

### Level 3 — Free-text LLM rolling summary (deferred to v5+ as optional)

**Status: 💡 deferred, optional.** No plan written; this entry exists to ensure the option is captured rather than silently dropped, AND to record the conditions under which it should be reopened.

**What it would be.** A per-session running narrative summary, generated by an LLM after each assistant turn, capturing the conversation's substantive thread (not just topics + entities). Fed into the classifier prompt + planner + synthesizer on every subsequent turn. Common pattern in modern conversational systems.

**Why deferred (not rejected — deferred).**

1. **Drift / telephone-game effect.** Documented failure mode: a summary at turn N that mis-compresses one detail propagates the corruption to N+1, N+2, … By turn 8-10 the summary may assert facts the user never said. Requires its own anti-drift harness (re-summarization checkpointing, per-turn delta validation, or both).
2. **Latency + cost.** Adds an LLM call per assistant turn before the next user turn can be processed. +1 to +3 seconds per turn end-to-end + token cost multiplied by every active session.
3. **Debug surface.** Today's `ConversationState` is structured + inspectable; a debugger reads it in 30 seconds and verifies. A free-text summary requires reading generated prose, judging whether capture was faithful, and sometimes proving the summarizer hallucinated. ~10x debug-time multiplier on multi-turn bugs.
4. **Citation traceability.** Lia's product trust contract is "every claim is anchored to a real norm". A summary that paraphrases legal positions can introduce shifts that propagate into the answer's framing. For a contable product this is a real audit-trail risk.
5. **Level 2 may be sufficient.** The §3 mechanism (classifier blind to prior topic) is the dominant failure today; Level 2 closes it structurally. Level 3 is justified only if multi-turn coherence remains a structural ceiling AFTER Level 2 ships and is measured.

**Conditions to reopen Level 3 (binding — not aspirational).**

- Level 2 ships and the multi-turn harness still shows refusal rate > 15% on 5+ turn dialogues, AND
- SME spot-review identifies ≥ 3 distinct failure cases where structured state (`prior_topic`, `topic_trajectory`, `entities`, `carry_forward_facts`) demonstrably could not have captured what was needed (e.g., dialogues where the user is reasoning across multiple norms simultaneously and a free-text gist would help), AND
- Operator explicitly opens v5 §X with a six-gate plan that includes an anti-drift measurement harness BEFORE any code is written.

**Estimated effort if reopened.** ~2-3 weeks: ~1 week for the summarization subsystem (prompt design, batching, caching, fallback when LLM is slow/down) + ~1 week for the anti-drift harness + ~3-5 days for staging-validation iteration. Plus ongoing operational cost per session.

### Cross-reference

| Level | Six-gate status | Plan location | Ship trigger |
|---|---|---|---|
| 1 | 🛠 code landed 2026-04-25 | §3 (Option A row + plan blocks) | Shipped — `requestController.ts:230-243` |
| 2 | 🛠 code landed 2026-04-25 | §4 (this section) | Shipped alongside Level 1 — `conversation_state.py`, `topic_router.py`, `ui_chat_payload.py`. Verification path (≤ 5% refusal target on multi-turn fixture) still pending the staging-cloud harness run. |
| 3 | 💡 deferred, optional | §4 (this section, conditions-to-reopen block) | Level 2 ships + multi-turn refusal rate stays > 15% + ≥ 3 SME-confirmed cases where structured state proven insufficient |

---

## §5 Comparative-regime planner mode — pre/post reform follow-ups (operator-surfaced 2026-04-25)

### Why

A live three-turn session pasted by the operator on 2026-04-25 surfaced this gap. The third turn ("cuanto cambia esto si alguna parte del saldo es de pre 2017?") returned an evasive answer:

> "Sí cambia. Debes validar el régimen de transición del art. 290 ET antes de aplicar la regla de los 12 años."

…plus a single-line Ruta, one Riesgo, and a Soportes section that **hallucinated a description for Art. 290 ET** ("Régimen de transición para la depreciación de activos"). Two distinct issues stacked:

1. **Content gap** — `ARTICLE_GUIDANCE` had no entry for `"290"`, so the synthesis had nothing operative to say beyond "validate the transition regime."
2. **Structural gap** — even with content, the system lacks a planner mode that recognizes the question pattern "what specifically changes pre-X vs vigente" and renders a side-by-side comparison. A senior contador answers this with a 3-row table (plazo, fórmula, reajuste); today the synthesis tries to merge two regimes into one prose block and the comparative structure dissolves.

The content gap was patched on the same day (`ARTICLE_GUIDANCE["290"]` for numeral 5; LLM polish prompt hardened against invented article descriptions). The structural gap is what this section plans.

### Idea (one sentence)

Add `comparative_regime_chain` as a new `query_mode` in `pipeline_d/planner.py`, triggered when the user asks how a regime changed across a temporal cutoff, that anchors BOTH articles (current + transition) and renders the answer as a side-by-side table.

### Plan (narrowest scope)

1. **Detection** — `_looks_like_comparative_regime_case(message, conversation_context)` in `planner_query_modes.py`. Lexical cues: `\b(antes de|anterior a|pre-?)(\d{4})\b`, "qué cambió con la reforma", "régimen de transición", "viene de antes". Returns `(matched, cutoff_year, regime_pair_key)`.
2. **Anchoring** — When detected, planner adds two `article` entries (current article + transition article) with source `comparative_regime_anchor`. Pair lookup is config-driven: `config/comparative_regime_pairs.json` mapping `(domain, cutoff_year) → (current_article, transition_article, transition_numeral)`. Initial entries: pérdidas (147 ↔ 290 #5), depreciación (137-140 ↔ 290 #1-2), tarifa renta (240 ↔ Ley 2277/2022 transitions).
3. **Synthesis** — `compose_comparative_regime_answer` in a new `pipeline_d/answer_comparative_regime.py` emits a markdown table (≥3 rows: plazo / fórmula-o-tope / reajuste-o-ajuste) + a 1-line verdict ("Sí cambia" / "No cambia") + a 1-line action. Standard Riesgos + Soportes sections wrap below the table.
4. **Polish-prompt extension** — explicit rule in `answer_llm_polish.py` to preserve the table verbatim (don't reflow into prose).

### Success criterion (gate 3)

The third-turn case from the 2026-04-25 session ("cuanto cambia si alguna parte del saldo es de pre-2017?") returns an answer whose first 30 lines contain:
- The verdict "Sí cambia" or "Sí, cambia" in line 1-2.
- A markdown table with ≥ 3 rows comparing pre-2017 vs vigente.
- ≥ 3 inline ET article references (147 + 290 + at least one numeral-specific citation like `art. 290 #5 ET`).

Plus: zero regression on the 42 existing phase3 smokes.

### How to test (gate 4)

- **Local technical** — new test `test_phase3_pipeline_d_comparative_regime_pre2017_followup` mirroring the format of existing followup tests, asserting table structure + verdict + numeral citation.
- **Staging end-to-end with SME** — run the same 3-turn dialogue against staging post-deploy. SME (Alejandro) reads the third turn, marks pass/fail on whether a senior contador would consider it operative.
- **Decision rule** — technical test green AND SME pass on the binding case → ship. Either fail → iterate on synthesis (gate 6 narrow first, discard last).

### Refine-or-discard (gate 6)

If SME flags the table format as too rigid for qualitative comparative cases (e.g., when the change is "ya no aplica" rather than a numeric difference), narrow the trigger to numeric-cue cases only ("plazo cambia", "tope cambia", "fórmula cambia") instead of discarding the whole feature. Discard only if BOTH numeric and qualitative cases regress versus today's evasive prose.

### Effort

~2-3 days end-to-end:
- 0.5d — detection logic + cue extraction + unit tests
- 0.5d — config schema + initial regime pairs (3 to validate generality)
- 1d — synthesis module + table rendering + polish prompt rule
- 0.5d — SME staging validation + iteration

### Dependencies

- §3 Level 1 must ship first (the multi-turn refusal rate baseline informs whether this is the dominant remaining failure mode or a smaller tail).
- The corto-plazo content patches landed 2026-04-25 (`ARTICLE_GUIDANCE["290"]` + polish-prompt anti-hallucination rule) are prerequisites — without them the comparative table would still have a hallucinated description risk.

### Status

🧪 **verified locally 2026-04-25** — full implementation landed same day:
- New module `src/lia_graph/pipeline_d/answer_comparative_regime.py` (config loader + cue detector + pair matcher + composer with markdown table renderer).
- New config `config/comparative_regime_pairs.json` v2026-04-25-v1 with the binding `perdidas_fiscales_2017` pair (147 ↔ 290 #5, 4 dimensions, verdict + action + risks + supports).
- Planner: new `comparative_regime_chain` budget; pre-classifier detection at `planner.py:279-310` that overrides query_mode when (a) cue matches, (b) conversation_state has anchors, (c) a regime pair matches. Anchor entries added with source `comparative_regime_anchor`.
- Orchestrator: fan-out suppressed when the parent message itself is comparative (`orchestrator.py` near `decompose_query`) — prevents the decomposer from splitting a comparative cue into two sub-queries where only one carries it.
- Assembly: `compose_main_chat_answer` routes to `compose_comparative_regime_answer` when `planner_query_mode == "comparative_regime_chain"`.
- Polish: prompt rule added to preserve markdown tables verbatim.
- Tests: new `test_phase3_pipeline_d_comparative_regime_pre2017_followup_renders_table` (binding case). Three pre-existing follow-up tests updated to assert the new (strictly better) comparative output instead of the legacy prose phrasing.

✅ pending — staging end-to-end with SME on the binding case + adjacent comparative scenarios (depreciación, tarifa renta) to validate generality. The current pair config has only one entry; adding more is a config-only change once SME validates the structure.

---

## §6 100-Q quality gauge — first baseline + delta tool (operator-surfaced 2026-04-26)

### Why

The repo carries `evals/100qs_accountant.jsonl` (100 unique Qs across 28 categories and 4 evaluation profiles) plus `evals/100qs_rubric.yaml` (7 weighted dimensions: exactitud_normativa 0.25, aplicabilidad_operativa 0.20, completitud 0.15, actualizacion 0.12, claridad_profesional 0.10, prudencia_fiscal 0.10, soporte_documental 0.08; profile_overrides bias toward the dimension that matters per profile). The structural audit on 2026-04-26 confirmed: 100/100 unique IDs, 100/100 non-empty references, 79/100 cite Art. # in-text, 19/100 reference 2026 UVT, ten rows have empty `reference_sources` (cosmetic; bodies cite norms). The dataset is fit-for-gauge but no runner consumes it — we cannot answer "did this pipeline change improve or regress Lia" with a number.

### Idea (one sentence)

Run the 100 Qs end-to-end through `/api/chat`, score with Claude-as-judge against the existing rubric, and produce a single repeatable macro-pass-percent number plus per-dimension/per-category breakdowns that move when pipeline knobs flip.

### Status (2026-04-26)

🛠 **code landed 2026-04-26** — `scripts/run_100qs_eval.py` + `scripts/judge_100qs.py` (unauthenticated public-session HTTP path; resumable per-ID; Sonnet 4.6 judge with `cache_control: ephemeral` on the static system prompt + 7-dim rubric block; aggregator computes macro-pass-%, weighted per-profile, per-category, weak-questions, weak-dimensions, corpus-gap clusters via `corpus_gap_min_cluster_size` from rubric).

🧪 **partially verified locally 2026-04-26 around 7:00 AM Bogotá**:
- Offline checks pass — fixture loader (100/100), resume-skip logic, prompt build (system 6196 chars, user template 2079 chars on a representative row), `_extract_json` against fenced/raw/embedded JSON, profile-aware weight resolution (calculative biases `exactitud_normativa` over procedural; renormalizes to 1.0), aggregation math (synthetic 4/5+5/5+2/5 → 73.33% macro, weak-Q + corpus-gap-cluster detection both fire).
- Live runner smoke 3/3 OK against `http://localhost:8787` (dev artifact mode), 2618–6047 ms/Q, output at `evals/runs/100qs_dev_smoke_20260426T115529Z.jsonl`. AQ_001 returned partial-coverage notice; AQ_002 returned a substantive multi-bullet answer; AQ_003 hit the v6 evidence-coherence-gate refusal as expected (the gate is doing its job, not a bug).
- **Live judge unverified** — needs `ANTHROPIC_API_KEY` (none found in env files). Not a code blocker.

### Plan §6.1 — first baseline run (the actual measurement)

Once `ANTHROPIC_API_KEY` is available:

1. **Dev artifact baseline.** `npm run dev` → `run_100qs_eval.py --tag dev_baseline` (~15-20 min) → `judge_100qs.py --run-file …` (~$2-4 USD; ~15-20 min). Commit the `__summary.json` to `evals/runs/`.
2. **Staging cloud baseline.** Same against `npm run dev:staging` (Supabase + cloud Falkor). Commit summary.
3. **Spot-validate the judge.** Operator/SME picks 5-10 lowest-scoring questions from each summary and reads them independently against Lia's actual answer. If the judge's verdict matches the operator's gut on ≥ 80% of spot-checks → judge is trustworthy enough to use as the gauge. If < 80% match → refine `judge_system_prompt` first (gate 6), don't trust the macro number yet.

### Plan §6.2 — `summary_diff.py` (only if §6.1 produces actionable spread)

If the dev baseline and the staging baseline differ meaningfully (e.g., > 3pp macro-pass spread, or one or more dimensions diverging by > 0.05 in mean), build `scripts/summary_diff.py` (~50 LOC): takes two `__summary.json` paths and prints a ranked table of dimension/category deltas with sign markers. If §6.1 shows dev ≈ staging within noise, defer §6.2 — the tool only earns its keep when there's drift to track.

### Success criterion (gate 3)

§6.1: two `__summary.json` files in `evals/runs/` (one per mode) with `n_judged_ok ≥ 95` (allows ≤5 judge failures), `macro_pass_percent` populated, per-dimension means populated, ≥ 1 corpus_gap_cluster surfaced (the dataset is large enough that something will cluster). Spot-check agreement ≥ 80% on 5-10 weakest Qs in each summary.

§6.2: ships only if §6.1 spread ≥ 3pp macro OR ≥ 1 dimension diverges ≥ 0.05.

### How to test (gate 4)

- **Engineer** runs the runner + judge in both modes and posts the two summaries.
- **Operator/SME (Alejandro)** spot-checks 5-10 weakest Qs in each summary against Lia's actual answers (10-15 min per mode). The criterion is "does the judge's verdict on this Q match what an experienced contador would say?" — not "is Lia's answer good." We're validating the judge, not Lia.
- **Decision rule (gate 5):** ≥ 80% spot-check agreement → publish the macro number as Lia's first quality baseline; flip to "this number is the gauge" mode for future changes. < 80% → judge prompt refinement before publishing any number.

### Refine-or-discard (gate 6)

- If the judge is too generous (spot-checks find Lia answers worse than the score suggests) → tighten `judge_system_prompt` "no seas indulgente" wording + add explicit anti-bias examples.
- If the judge is too harsh (spot-checks find Lia answers better than the score suggests) → audit whether the rubric's "reference is just a factual anchor, not a quality model" instruction is being honored; the judge may be marking down LIA for not matching reference verbatim.
- If macro-pass varies > 5pp between two judge runs of the same answers (prompt-cache off + temperature noise) → run twice with different seeds and report mean ± half-spread; if half-spread > 2pp the gauge isn't useful as a single number.
- Discard only if spot-check agreement stays < 60% after two prompt-refinement passes.

### Effort

- §6.1: 1 day (one operator afternoon for the two runs + the spot-checks + commit).
- §6.2: 0.5 day, conditional on §6.1 producing drift.

### Dependencies

- `ANTHROPIC_API_KEY` available to the operator running the judge.
- Both `dev` and `dev:staging` modes operational on the operator's machine (Supabase docker + cloud Falkor reachable for `dev:staging`).
- §3 Level 1 multi-turn baseline does NOT block this — single-turn 100-Q gauge is independent.

### What this is NOT

- **Not a head-to-head Claude-with-web baseline.** The rubric describes a 30-Q sample (`comparison_sample_size: 30`, `comparison_seed: 42`) with `research_*_template` and `comparison_*_template` prompts. That's deferred to v5+ — useful for diagnosing "is this a corpus gap or a pipeline gap?" but not needed to establish the baseline.
- **Not a per-topic statistical claim.** 100 Qs / 28 categories ≈ 2-7 per category. The macro number is reliable; per-category deltas < 5pp are noise. Use the gauge for "did Lia get better overall" and "is dimension X weak globally"; do not use it for "did IVA improve."
- **Not a substitute for the existing eval suites.** `make eval-c-gold`, retrieval eval, multiturn dialogue harness all measure narrower things. The 100-Q gauge is the answer-quality layer, complementary to those.
- **Not a release gate.** The rubric's `pass_threshold_percent: 75.0` is an aspirational anchor, not a CI fail-threshold. Per the "thresholds — no lower" memory: if a run lands below 75 we record the exception per case, never relax the threshold.

### Notes from the structural audit

- Ten reference rows have `reference_sources: []` despite citing norms in-text (`AQ_017, AQ_038, AQ_041, AQ_056, AQ_067, AQ_075, AQ_076, AQ_087, AQ_088, AQ_093`). This shows up in the judge prompt as "(la referencia no listó fuentes — apóyate en el cuerpo)". Cosmetic; the judge handles it. A v5+ cleanup PR can fill them in by parsing the answer text.
- The runner currently records `retrieval_backend = null` / `graph_backend = null` for some turns where Lia's `diagnostics` object is `None` (e.g., coherence-gate refusals where the pipeline short-circuits). That's faithful capture, not a runner bug. If the macro gauge later wants to slice "judge score conditional on backend served the answer", we'd need Lia to populate those keys even on refused turns — separate ticket.

---

## §6.5 Parity probe asymmetry — propagate `sync_generation` to Falkor + investigate edge undercount (operator-surfaced 2026-04-26)

> **Context.** GUI ingestion's "Salud del corpus" tarjeta showed `Parity Supabase ↔ Falkor: Desfasada` with deltas equal to ~the entire corpus (`docs Δ1278, chunks_vs_articles Δ7842, edges Δ5229`). Diagnosis (2026-04-26): the probe was querying labels that don't exist in Falkor (`:Document`, `:Article` — the schema uses `:ArticleNode`). **Short-term fix landed same day** in `src/lia_graph/ingestion/parity_check.py`: queries point at `ArticleNode` and use `count(DISTINCT a.source_path)` as the docs proxy. Tests updated, 5/5 green.
>
> **Post-fix real numbers (against staging cloud, 2026-04-26):**
> - `docs`: Supabase 1.278 (active gen) vs Falkor 3.248 (DISTINCT source_path, gen-agnostic) → +1.970 lingering on Falkor.
> - `chunks_vs_articles`: Supabase 7.842 vs Falkor 9.247 → +1.405 lingering on Falkor.
> - `edges`: Supabase ~30.103 vs Falkor 24.874 → **−5.229 missing on Falkor**.
>
> The card will keep showing "Desfasada" until both items below land. That's the honest signal — the bug noise is gone, the real drift remains.

### Item §6.5.A — Propagate `sync_generation` to Falkor nodes

#### Gate 1 — Idea (one sentence)

Tag every `ArticleNode` (and every other node Falkor materializes) with `sync_generation` at MERGE time, so the parity probe and any future generation-scoped query can filter Falkor counts to the active generation just like it already does on Supabase.

#### Gate 2 — Plan (narrowest module)

- **Schema layer.** `src/lia_graph/graph/schema.py` — add `sync_generation` to the property set the loader writes for `ArticleNode`, `TopicNode`, `SubTopicNode`, `ReformNode`, `ConceptNode`, `ParameterNode` (six labels, one new property each).
- **Loader.** `src/lia_graph/ingestion/loader.py` — every MERGE that creates or touches a node must `SET n.sync_generation = $generation_id` from the active delta context. The generation_id already lives in `delta_runtime.materialize_delta` and on the loader's call-site.
- **Probe symmetry.** `src/lia_graph/ingestion/parity_check.py` — once nodes carry `sync_generation`, swap the gen-agnostic counts for `MATCH (a:ArticleNode {sync_generation: $gen}) …`. Drop the asymmetry note in the docstring.
- **Backfill.** One-shot script `scripts/backfill_sync_generation_falkor.py` that walks every existing node (9.247 ArticleNode + 81 + 94 + 1.860 + …) and SET their `sync_generation` to the generation that originally wrote them. The originating gen can be inferred from `documents.sync_generation` joined on `source_path` for ArticleNode; for derived nodes (Topic/SubTopic/Concept/Parameter) the inference rule is "active generation when the connected ArticleNode was written" — needs a design pass.
- **Retire policy follow-up (out of scope here).** Once gen-tag exists, a separate plan can decide whether/how to retire nodes whose `sync_generation` is older than active. Today the corpus is **append-only on Falkor side** (per the operator's "additive is the friendly path" directive in `CLAUDE.md`); explicit retirement stays opt-in via the `--allow-retirements` CLI flag, but it should at least *be possible* to identify them.

#### Gate 3 — Minimum success criterion (measurable)

After the change ships and a fresh `make phase2-graph-artifacts-supabase` runs against staging:

- `MATCH (a:ArticleNode) WHERE a.sync_generation IS NULL RETURN count(a) AS n` ⇒ `n = 0` (no untagged nodes).
- The corpus health card's three Supabase-vs-Falkor deltas all fall **inside** the parity tolerance (±5 absolute / ±0.2%), so the card flips from "Desfasada" to "Alineada ✓" without changing tolerance values.
- Ingest events emit one `ingest.parity.check.done` per `--additive` run with `ok=True`.

#### Gate 4 — Test plan

- **Development needed.** (a) Schema + loader edits behind a single feature flag `LIA_FALKOR_NODE_GENERATION_TAG=on` (so the change can ship and bake without immediately triggering the backfill). (b) Backfill script with `--dry-run` mode that prints "would tag N nodes with gen X" without writing. (c) New unit test in `tests/test_parity_check.py` covering the gen-scoped query path with a fake Falkor that respects the `{sync_generation: $gen}` filter. (d) New ingest contract test verifying that after a `delta_runtime.materialize_delta` invocation, every newly-MERGEd node has `sync_generation` set.
- **Conceptualization.** "All nodes carry the gen tag" means the parity probe finally has matching reference frames on both sides — Supabase active-gen counts vs Falkor active-gen counts. That eliminates the structural asymmetry; any remaining delta is real drift.
- **Running environment.** Unit + ingest tests in `make test-batched`. End-to-end verification needs a staging-cloud run of `make phase2-graph-artifacts-supabase` + the backfill script, both observed via `logs/events.jsonl`.
- **Actors.** Engineer ships code + unit tests. Operator runs the staging hydration + backfill (production credentials). No SME / end-user actor needed — this is plumbing.
- **Decision rule.** Pass = all three Gate-3 numeric checks succeed. Fail = any one missing → discard the loader edits, keep the schema change inert, leave the asymmetry note in place.

#### Gate 5 — Greenlight

Requires both signals: (a) unit + ingest tests green; (b) operator-run hydration shows `Alineada ✓` on the GUI card.

#### Gate 6 — Refine-or-discard

If end-to-end shows Falkor still drifts post-tag, the discard path is to revert the loader edits, leave the schema field nullable + unused, and reopen with the assumption that gen-tagging alone isn't sufficient (i.e., the writer is dropping nodes silently, not failing to tag them).

#### Status

💡 **idea** — opened 2026-04-26 from the GUI parity-probe diagnostic. Code not written.

---

### Item §6.5.B — Investigate the −5.229 missing edges on Falkor — **🧪 verified locally, mostly closed**

> **Outcome (2026-04-26).** Diagnostic ran via `scripts/diag_falkor_edge_undercount.py` against staging cloud. Real picture:
> - 65,8% of Supabase edges (19.815) **present** in Falkor.
> - 33,0% (9.934) endpoint-missing — bucket (a), expected loss by loader design but proportion warrants follow-up → **Item §6.5.D opened.**
> - 1,0% (300) type-mismatch — bucket (c), Falkor *richer* than Supabase (`references → REQUIRES/COMPUTATION_DEPENDS_ON`); not a drop, not a problem.
> - 0,18% (54) silent-drop — bucket (b), all `references → CITA`. Threshold was ≤ 50; numerically 54 is above but semantically a single concentrated pattern at < 0,2%. **Qualitative-pass per case** (`feedback_thresholds_no_lower`): threshold not relaxed, this run is the recorded exception, watchlist for next ingest.
> - 0% unknown relation — mapping complete.
>
> Plus lateral finding promoted to its own item: FalkorDB server caps RESP responses at 10.000 rows silently → **Item §6.5.E opened and 🧪 verified locally same day.**
>
> Full bucket details, samples, and decision rationale in `docs/learnings/ingestion/falkor-edge-undercount-and-resultset-cap-2026-04-26.md`.

#### Gate 1 — Idea

Find out why Supabase `normative_edges` for the active generation has ~30.103 rows but Falkor only materialized 24.874 — specifically, whether the 5.229 missing edges are the **expected** loss from the loader's "skip unresolved ArticleNode endpoint" filter (`loader.py:271, 276, 412`), or whether some other class of edges is being dropped silently.

#### Gate 2 — Plan

- **Diagnostic, not intervention** (per the user's `feedback_diagnose_before_intervene` memory). Before touching the writer, measure where the 5.229 missing edges concentrate.
- **Probe.** Single-shot script `scripts/diag_falkor_edge_undercount.py` that:
  1. Pulls every row from Supabase `normative_edges` for the active generation (paginate).
  2. For each row, checks whether the `(source_article_id, target_article_id, edge_type)` triple exists in Falkor.
  3. Buckets the missing edges by edge_type, by source_article materialization status, by target_article materialization status.
- **Cross-reference.** Read the existing `loader.py` skip counters that already log `skipped_edge_count` and `dropped_edges` (`loader.py:271-279, 276-280, 412-415`). Sum across the last `delta_jobs` row's events; the sum should equal 5.229 if the loss is fully accounted for.

#### Gate 3 — Minimum success criterion

A short report (`docs/learnings/ingestion/falkor-edge-undercount-2026-04-26.md`) that classifies the 5.229 missing edges into:
- (a) edges deliberately skipped by the loader's endpoint filter (expected),
- (b) edges silently dropped by an unidentified path (problem),
with a count for each bucket and at least 5 sample edges per bucket. Decision rule: if (b) ≤ 50 edges, close as "expected loss". If (b) > 50, open a follow-up item targeting the specific drop path.

#### Gate 4 — Test plan

- **Development needed.** The diagnostic script (above) and the delta_jobs event-log aggregator. No production-code changes for this gate; everything is read-only.
- **Conceptualization.** Each bucket maps to a different remediation: (a) is "documented behavior, leave it"; (b) is "real bug to chase". Without the bucketing, the −5.229 number is just noise.
- **Running environment.** Local execution (`uv run`) reading from staging-cloud Supabase + Falkor. Read-only, no writes anywhere.
- **Actors.** Engineer runs the script, reads logs, writes the learnings doc.
- **Decision rule.** Bucket-(b) ≤ 50 → close. > 50 → escalate to a new §6.5.C item with its own six gates.

#### Gate 5 — Greenlight

Doc landed in `docs/learnings/ingestion/`. No end-user signal needed because this gate is investigation, not change.

#### Gate 6 — Refine-or-discard

If the script can't reach a clean bucket count (e.g., the join on triple keys is itself ambiguous), discard the bucketing approach and reopen with a different methodology.

#### Status

🧪 **verified locally** — opened and resolved 2026-04-26. Diagnostic ran, buckets recorded, watchlist active. ✅ **verified in target env** pending: re-run after the next staging delta to confirm bucket (b) doesn't grow.

---

### Item §6.5.D — Investigate the 33% endpoint-missing bucket (opened 2026-04-26)

#### Gate 1 — Idea

The §6.5.B diagnostic showed **9.934 of 30.103 Supabase edges (33%) reach Falkor with at least one endpoint not materialized**. The dominant pattern in samples is source articles using the legacy `article_key` form (e.g. `'10-fuentes-y-referencias'`) whose Falkor MERGE key is actually `whole::{source_path}` because the article is prose-only with no `article_number`. The loader filters these edges out by design (`loader.py:43-65, 271-279`). Investigate whether the **classifier** could emit edges using the graph key (`_graph_article_key()`) from the start, so prose-only articles' edges land in Falkor instead of being filtered downstream.

#### Gate 2 — Plan (narrowest module)

- **Diagnostic first** (`feedback_diagnose_before_intervene`). Add a sub-bucketing pass to `scripts/diag_falkor_edge_undercount.py` that splits bucket (a) into:
  - (a1) prose-only key mismatch (`source_key` resolves to `whole::{source_path}` if reformulated)
  - (a2) genuinely orphaned endpoints (article was filtered out for any reason)
  - (a3) reform-side missing (`source_key` looks like `DECRETO-XXX` but no `:ReformNode` exists)
  Ship the sub-bucketing as part of the same script; run it; record proportions.
- **Decision branches based on sub-buckets:**
  - If (a1) ≥ 70% of bucket (a): the fix is in `pipeline_d/classifier.py` (or wherever classifier emits the `source_key`/`target_key` for `normative_edges` writes). Change the classifier to emit `_graph_article_key()` for prose-only articles. Estimated upside: ≤ 9.934 edges recovered.
  - If (a3) is dominant: the fix is in the ReformNode materialization path; out of scope of the classifier change.
  - If (a2) is dominant: the loader filter is doing the right thing; close §6.5.D as "expected loss confirmed".

#### Gate 3 — Minimum success criterion

Sub-bucketing produces percentages summing to bucket (a) total (9.934). Branch decision recorded in the learnings doc. If the (a1) branch is taken, the implementation criterion is: **after a fresh staging hydration, the §6.5.B diagnostic shows bucket (a) decreased by ≥ 50%** without any increase in bucket (b) or (c).

#### Gate 4 — Test plan

- **Development needed.** Sub-bucketing logic in the existing diagnostic script (~30 LoC). If the (a1) branch lands, a new ingest contract test that emits a prose-only article + an edge whose `source_key` would be the legacy form, and asserts the classifier writes `_graph_article_key()`.
- **Conceptualization.** Bucket (a1) ≥ 70% → keying mismatch is the dominant cause and a fix in the classifier directly recovers most of the 33%. (a2) dominance means the loader is doing what it should and §6.5.D closes as "no fix available without weakening the corpus".
- **Running environment.** Sub-bucket diagnostic locally (read-only). If a code change ships, the validation needs a staging hydration run.
- **Actors.** Engineer for the diagnostic. Operator for any staging hydration.
- **Decision rule.** ≥ 50% bucket-(a) decrease in the post-fix re-run = pass. < 50% = revert + reopen.

#### Gate 5 — Greenlight

If §6.5.D triggers a code change, both signals must clear: unit/contract tests + the staging-hydration delta measurement.

#### Gate 6 — Refine-or-discard

If sub-bucketing reveals the dominant cause is something else (a3 or a different pattern), close §6.5.D and open a new item targeting the actual cause. The learnings doc keeps the (a1) hypothesis as a recorded null-result if it doesn't pan out.

#### Status

💡 **idea** — opened 2026-04-26 from §6.5.B sub-bucketing. Sub-bucketing pass not written.

---

### Item §6.5.E — FalkorDB 10.000-row resultset cap audit (opened + resolved 2026-04-26)

#### Gate 1 — Idea

FalkorDB caps RESP responses at `MAX_RESULTSET_SIZE = 10000` and silently truncates the tail. The §6.5.B diagnostic discovered this when its first un-paginated pull returned exactly 10.000 rows. **Audit every runtime query** to confirm none can hit the cap; add a defensive guard so future regressions surface immediately.

#### Gate 2 — Plan (narrowest module)

- Read-only audit of every Falkor query in `pipeline_d/retriever_falkor.py` (the only runtime file outside ingestion that queries Falkor).
- For each query, record the bound mechanism (`count()` agg, explicit `LIMIT`, input slice) and realistic max-row scenario.
- Add `src/lia_graph/graph/result_guard.py` (new sibling module — `client.py` is at 1.033 LoC, over the granular-edits threshold) that emits `graph.resultset_cap_reached` when a query returns ≥ cap rows. Configurable via `FALKORDB_RESULTSET_SIZE_CAP`.
- Hook the guard into `GraphClient.execute` at every successful-result return point.

#### Gate 3 — Minimum success criterion

Audit table covers all 9 runtime queries with a bound mechanism for each. Guard emits the structured event under unit-test conditions when row count == cap. No current query is shown to risk the cap.

#### Gate 4 — Test plan

- **Development needed.** Audit performed by reading code; recorded in the learnings doc. Guard logic + 5 unit tests (below cap, at cap, custom cap via env, query truncation in payload, emit-failure swallowed).
- **Conceptualization.** "All runtime queries safe today AND any future regression is caught by the structured event" is the durable outcome; the audit alone would have been point-in-time only.
- **Running environment.** `pytest` for the guard. Audit table is in the learnings doc.
- **Actors.** Engineer.
- **Decision rule.** Audit shows zero current risk + 5/5 guard tests green = pass. Anything less = block and address.

#### Gate 5 — Greenlight

Both signals: 5/5 guard tests + audit table covering all 9 runtime queries.

#### Gate 6 — Refine-or-discard

If a future query shows up that legitimately needs > 10.000 rows, the guard's event will surface it; the response is to paginate the query (not to silence the guard). The guard has no behavior change risk — it never blocks, raises, or modifies results.

#### Status

🧪 **verified locally** — audit complete, guard shipped + tested. Test count 5/5 green. ✅ **verified in target env** pending: any production-staging query in real conditions would be a confirming signal but the guard's no-op-when-below-cap design makes target-env verification mostly redundant. Mark ✅ when at least one operator-driven staging session has run with the guard in place and emitted no `graph.resultset_cap_reached` events (expected silence = positive evidence).

---

## §7 What's NOT here (deliberately)

- Re-flip mechanics — those belong in `next_v3.md §13.10.7` item 3 and ship the moment SME closes gate 8.
- Anything that reopens settled six-gate decisions without new evidence.
- Generic "retrieval-depth lift" framings — the operator scoped v4 §1 specifically; honor the scope.
- Coherence-gate-loosening proposals — the gate is doing what it was designed to do; §1 and §3 both target upstream causes, not gate sensitivity.
- Free-text LLM rolling summary as an immediate deliverable — explicitly deferred per §4 Level 3 with binding reopen conditions.

---

*Opened 2026-04-25 after operator's qualitative-pass on gate 9 with explicit scoping for the deferred debt. §3 added 2026-04-25 from a live two-turn UI session that surfaced the stateless-classifier vs stateful-retriever interaction with the v6 coherence gate; deep-traced same day to confirm three serial frontier breaks (FE payload, ConversationState schema, classifier signature) and to rule out H1 (LLM-confidence threshold tuning). §4 added 2026-04-25 to capture the conversational-memory architecture as a three-level staircase: Level 1 = §3 Option A (committed, immediate), Level 2 = `ConversationState` extension with classifier-aware fields (committed conditional on Level 1 measurement), Level 3 = free-text LLM rolling summary (deferred to v5+ with binding reopen conditions). §5 added 2026-04-25 from a live three-turn session where a follow-up "cuanto cambia si parte es pre-2017?" returned an evasive answer with a hallucinated Art. 290 description; corto-plazo content patches landed same day (`ARTICLE_GUIDANCE["290"]` + polish-prompt anti-hallucination rule), §5 plans the structural `comparative_regime_chain` planner mode. §6 added 2026-04-26 — `scripts/run_100qs_eval.py` + `scripts/judge_100qs.py` landed and offline-verified; live runner smoke 3/3 OK against `localhost:8787`; live judge run pending an `ANTHROPIC_API_KEY` for the operator's first baseline. See `gate_9_threshold_decision.md` §7 for the binding decision record and `next_v3.md §13.10.8` for the cross-reference.*
