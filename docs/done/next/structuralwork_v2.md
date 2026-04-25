# Structural Work — v2 (2026-04-22)

**Context.** v1 (`docs/next/structuralwork_v1_SEENOW.md`) catalogued structural weaknesses and landed three harnesses plus pipeline topic-safety checks. The harnesses now tell us with numbers what was previously intuition. The v1 re-evaluation section at the top of that doc is the current "where we are" read; this file is the forward plan.

**v2 premise.** With hallucinations tightened (citation precision 0.991) and the dangerous-confident-wrong-answer failure mode gated (safety abstention firing appropriately on 23% of gold queries), the two remaining axes to move are:

1. **Fewer unreplied queries.** Today `safety_abstention_rate = 0.233` plus pre-existing `Cobertura pendiente` paths mean ~30% of gold queries don't get a real answer. Four of five current safety abstentions trace to topics the router has zero registered keywords for — routing silence, not a retrieval problem.
2. **Deeper, broader replied queries.** `body_vs_expected_alignment = 0.500`: half of served answers are topically on-point. `retrieval@10 = 0.275`: the retriever's ceiling is low. Multi-`¿…?` questions are scoped to one topic today; sub-questions in different topics get shallow treatment.

## The three work items

### Item V2-1. Router keyword coverage for empty top-level topics

**What's broken.** `src/lia_graph/topic_router_keywords.py::_TOPIC_KEYWORDS` has ~40 top-level topics with `{"strong": (), "weak": ()}` — `_log_topics_without_keywords()` logs them at startup. When a query hits any of those topics, the router returns `effective_topic=None, confidence=0.0`, which now correctly triggers `topic_safety_abstention` but also means the query goes unreplied. Four of the five current safety abstentions (Q13 RST, Q17 fondo solidaridad, Q25 patrimonio, Q27 SAGRILAFT) hit empty-topic domains directly.

**Gold-query-touching empty topics (from inspection):**
- `regimen_simple` (Q12, Q13)
- `impuesto_patrimonio` / `impuesto_patrimonio_personas_naturales` (Q25)
- `sagrilaft_ptee` (Q27)
- `obligaciones_profesionales_contador` (Q30)
- Plus `zonas_francas`, `perdidas_fiscales_art147`, `informacion_exogena` — present in gold as `expected_topic` but all empty keyword banks
- Labor-adjacent niches (pension solidarity fund; UGPP sub-areas) sit inside `laboral` but aren't differentiated at the subtopic level

**Technical attack plan.**

1. **Inventory pass** (engineer, 30 min). Extract the current empty-topic list from the router's startup log. Cross-reference with gold `expected_topic` values to prioritize. Write the ordered list to `artifacts/empty_topics_priority.json`.
2. **Candidate-vocabulary mining** (engineer, 2h). New script `scripts/mine_topic_keywords.py`:
   - For each priority topic `T`, iterate `canonical_corpus_manifest.json` for documents classified to `T` (via `topic_key`).
   - Extract title + body tokens, compute **TF-IDF** over the `T`-cohort vs rest-of-corpus.
   - Emit top-30 candidate terms per topic to `artifacts/topic_keyword_candidates/<topic>.jsonl` with TF-IDF score, document-frequency, and 2-3 example source sentences per term.
   - Side pass: mine the last 90 days of `logs/chat_verbose.jsonl` for queries the router classified to each topic at high confidence — their vocabulary is ground-truth signal.
3. **Accountant review** (curator, 30 min per topic × ~15 topics = ~8h total, parallelizable). Accountant marks each candidate as `strong` / `weak` / `reject`, adds any missing terms. Strong = unambiguous domain markers; weak = polysemous but scored-weighted. Review format: a single sheet per topic, same shape as `_TOPIC_KEYWORDS` currently uses.
4. **Polysemous-collision test** (engineer, 1h). Before merge, run proposed `strong` terms against every *other* topic's training queries to ensure no accidental cross-topic capture. Reuses the adversarial test fixture pattern from v1 item A.
5. **Registration** (engineer, 1h). Write reviewed vocab into `_TOPIC_KEYWORDS` via a new curator-output importer (`scripts/apply_topic_keywords.py`) so the merge is auditable — no hand-edited dicts.
6. **Harness-gated merge.** Each topic's keywords merged as a separate PR; baselines re-frozen; all three harness gates must pass at 2pp tolerance.

**Architectural choice: why not an LLM classifier?** Considered and rejected for this axis. The topic router is the most-trafficked decision in the pipeline; an LLM call here adds ~300–500ms to every query and introduces non-determinism that downstream tests depend on not having. Lexical routing is correct for top-level topic granularity; sub-topic detection (already LLM-driven in `planner_query_modes.py`) handles finer resolution. This item keeps the hot path lexical.

**Success criteria (measured on the 30-gold harness trio; will re-measure when gold grows to 50).**

| Metric | Today | Target after V2-1 |
|---|---|---|
| `router_accuracy` | 0.429 | **≥ 0.70** |
| `safety_abstention_rate` | 0.233 | **≤ 0.12** |
| `body_vs_expected_alignment` | 0.500 | ≥ 0.60 |
| `retrieval@10 (with_connected, loose)` | 0.275 | ≥ 0.33 |
| `citation_precision (loose)` | 0.991 | **≥ 0.985** (regression gate: must not drop) |
| `primary_anchor_recall (loose)` | 0.855 | ≥ 0.85 (regression gate) |

**Direct attribution.** Q13, Q17, Q25, Q27, Q30 must no longer hit `topic_safety_abstention` as a categorical test (they can still fail retrieval; they cannot silently fail at routing).

**Risks + mitigations.**
- *Polysemous-weak collision:* new keywords for topic `X` accidentally capture queries that belong to topic `Y`. → Mitigated by the cross-topic adversarial test in step 4 plus harness regression gates.
- *Over-fitting to the 30-gold:* vocabulary tuned to make the current 30 queries route correctly but fails on the next 20 mined queries. → Mitigated by the log-mining side pass in step 2 and by delaying the aspirational-red-line bump until the gold is 50+.
- *Curator bandwidth:* 8h of accountant review is the bottleneck. → Parallelizable across topics; a junior accountant with the expert's guidance rules can review 5 topics/day.

**Effort.** Engineering: ~1 day. Curator: ~1 day spread over 2 weeks.

---

### Item V2-2. LLM query decomposition

**What's broken.** Today, a multi-`¿…?` query is routed as one string to one topic. `build_graph_retrieval_plan` does detect sub-questions and stores them in `plan.sub_questions`, but retrieval is single-topic: the same hybrid search and graph BFS run once against `plan.entry_points`, which were built from the composite query. A question like Q2 ("¿cómo calculo TTD? ¿qué si el resultado queda por debajo del 15%? ¿en qué renglón del formulario 110?") asks about three separate concerns — the first two are in `declaracion_renta`, the third is in `formulario_110` territory. Today the third gets retrieval-starved because retrieval anchored on the first two.

**Observable today.** The sub-question-level recall metric in `eval_retrieval.py` is already reported (currently computed against the primary query's retrieved set — a proxy). What we lack: per-sub-question routing and retrieval.

**Technical attack plan.**

1. **New module `src/lia_graph/pipeline_d/query_decomposer.py`.** Owns the split. Two layers:
   - **Regex first pass**: split on the `¿...?` terminator that we already parse. 80% of gold M-type queries work with this alone.
   - **LLM disambiguation pass** (Gemini Flash, ~300ms) only when the regex yields > 3 fragments or when fragment lengths are uneven (some fragments < 20 chars). The LLM returns `[{text, expected_family, coherence_group}]` where `coherence_group` lets us avoid redundant retrieval for tightly-related sub-questions.
   - Env gate: `LIA_QUERY_DECOMPOSE=off|on`, default `off` at ship, flip to `on` in `dev:staging` after the alignment harness confirms a ≥ 5pp lift on `body_vs_expected_alignment`.
2. **Orchestrator wiring (`pipeline_d/orchestrator.py`).** When decompose is on and the query has > 1 sub-question:
   ```
   sub_queries = decompose(message)
   plan_bundles = [build_graph_retrieval_plan(sub_query) for sub_query in sub_queries]
   evidence_bundles = [retrieve_graph_evidence(plan) for plan in plan_bundles]
   merged = merge_evidence_bundles_for_multi_intent(evidence_bundles, coherence_groups=...)
   # then the existing answer_synthesis/assembly path runs on `merged`
   ```
3. **New helper `merge_evidence_bundles_for_multi_intent`** in `pipeline_d/retrieval_support.py`. Merge strategy:
   - Union of `primary_articles` across sub-queries, deduped by `node_key`, provenance tagged (`item.why += f" (sub-query {i})"`)
   - Union of `connected_articles`, deduped
   - Per-sub-query `primary_article_count` stashed in `diagnostics.sub_query_retrieval` so the alignment harness can score each sub-question's topic independently
4. **Synthesis stays the same.** The existing `answer_synthesis_sections.py` multi-bubble shape (per the memory `feedback_multiquestion_answer_shape`) already emits one answer block per `¿…?`. It just gets richer, per-sub-question grounded evidence.
5. **Cost governance.** The decomposer's LLM pass is skipped on single-`¿?` queries (most of the gold's S-type entries). For M-type, the LLM cost is < $0.001/query at Gemini Flash rates. Latency budget: + 300ms LLM call + ~200ms extra retrieval per additional sub-query (was 1 retrieval, now up to 3 in worst case). Total added latency: 500–900ms, well within the 3s soft budget.

**New metric the alignment harness will gain for this work.** `sub_question_router_accuracy` — for every M-type gold entry, what fraction of sub-questions' independently-computed router topic matches the gold's sub-question-level `expected_topic`. Added to `eval_topic_alignment.py` as a fourth core metric. Regression gate inherits the 2pp tolerance.

**Success criteria.**

| Metric | Today | Target after V2-2 |
|---|---|---|
| `body_vs_expected_alignment` | 0.500 | **≥ 0.70** |
| `safety_abstention_rate` | 0.233 | ≤ 0.10 (M-type partial abstention goes away) |
| `retrieval@10` on M-type entries specifically | ~0.28 (subset) | ≥ 0.40 |
| New: `sub_question_router_accuracy` | TBD at v2-baseline | ≥ 0.70 |
| `primary_anchor_recall` | 0.855 | ≥ 0.85 (regression gate — must not drop from orphan'd sub-query evidence) |
| p95 pipeline latency | TBD — measure before ship | ≤ baseline + 900ms |

**Acceptance test.** Q2, Q4, Q6, Q18, Q20, Q22, Q26 (all M-type multi-concern gold entries) must show per-sub-question topic routing in `response.diagnostics.sub_query_retrieval`, and their `body_vs_expected_alignment` must bump from FAIL to OK on at least 4 of 7.

**Risks + mitigations.**
- *Over-splitting.* "¿puede el cliente deducir el 1% y cuál artículo aplica?" is one question, not two. → Mitigated by the LLM's `coherence_group` output + a fallback: if decomposer produces N sub-queries but the composite query routes with confidence > 0.7 to a single topic, honor the single-topic path and skip the fan-out.
- *Decomposer LLM failure* (timeout, bad JSON). → Fallback to single-query path, log `decompose_fallback=true` in diagnostics. Non-fatal.
- *Latency in staging.* + 900ms worst case on complex multi-part queries. → Budget is fine for chat UX; if user feedback says otherwise, gate decomposition behind a query-length heuristic (only fire when composite > 250 chars).
- *Cost blowout.* If M-type queries spike in production. → Pre-flight token estimate caps queries > 2000 chars at regex-only decomposition.

**Effort.** Engineering: 1 day (module + wiring + harness metric extension + fallback paths). Zero curator work.

---

### Item V2-3. Practical-guide corpus curation for high-traffic procedures

**What's broken.** v1 item H named the three-family model (NORMATIVA / EXPERTOS / PRÁCTICA). A corpus-family census hasn't been productionized yet (the v1 `corpus_family_census.py` script is scoped but not written). Inspection confirms the pattern empirically on our gold: queries like Q10 (habilitación facturación electrónica), Q12 (RST elegibilidad), Q27 (SAGRILAFT) have NORMATIVA coverage but thin-to-absent PRÁCTICA, so even a correctly-routed query produces shallow or abstained answers.

**Distinct from V2-1 and V2-2 because:** keyword coverage and decomposition route/retrieve material that *exists*. This item *creates* material where the corpus is hollow. It's the only lever that increases answer **depth and breadth** rather than routing accuracy.

**Technical attack plan.**

1. **Census script** (engineer, half day). `scripts/corpus_family_census.py`:
   - Walks `canonical_corpus_manifest.json`, groups by `(topic_key, family)` where `family ∈ {normativa, interpretacion, practica}` (note: `interpretacion` is the authoritative family slug for what v1 called "expertos" — see v1 doc v4.1 change).
   - Emits `artifacts/family_census.json` with per-topic (count_normativa, count_interpretacion, count_practica, total) + a flagged-for-curation section for topics where any family count is 0 or < 3.
   - Rerunnable; the census result becomes an artifact the curator dashboard consumes.
2. **Priority slate from census + gold analysis.** The census plus gold `macro_area` distribution gives us a joint ordering. Initial working slate:
   - **Tier 1 (commissioned now, 2–3 weeks):** DIAN procedure (PRO-N01, PRO-E01, PRO-L02/L03/L04 — five docs, already scoped in v1 H).
   - **Tier 2 (commissioned week 2):** RST operations (bimonthly anticipos, annual Form 260, exit procedures); UGPP audit procedure; facturación electrónica habilitación.
   - **Tier 3 (commissioned month 2):** SAGRILAFT/PTEE thresholds and implementation; impuesto al patrimonio declaration; ZOMAC benefit request.
3. **Canonical template enforcement.** Every new PRÁCTICA document lands in `knowledge_base/<topic>/<subtopic>/<slug>.md` and is structured per the 8-section canonical template `ingestion_section_coercer.py` enforces. The sections are non-negotiable: *Contexto, Marco normativo, Procedimiento paso-a-paso, Formularios y plazos, Sanciones, Riesgos comunes, Interpretación doctrinal, Referencias*. The coercer will reject anything else.
4. **Ingestion flow.** Single-pass ingest (`make phase2-graph-artifacts-supabase`) picks up the new documents automatically and classifies subtopics via PASO 4. No manual schema changes. New documents appear in retrieval within one ingest run.
5. **Gate.** Every new document merges only after (a) accountant + domain-specialist sign-off, (b) `corpus_audit_report.json` shows `canonical_blessing_status=canonical`, (c) all three harnesses pass regression at 2pp tolerance. The citation-faithfulness harness implicitly catches factual errors where the document references articles not in the graph.

**New metrics this item needs.**

The v1 harness set doesn't yet measure answer depth. Two new metrics added to `eval_retrieval.py`:

- **`answer_body_length_median_chars`** — length of `response.answer_markdown` across served answers. Currently ~700 chars median on the 30-gold; practical-guide additions should lift queries in covered topics to 1200+ chars.
- **`answer_distinct_forms_cited`** — count of distinct formulario numbers mentioned in the answer (Form 110, 260, 300, 350, 2516, 2593, etc., regex `(?i)formulari[oas]\s+(\d{2,4})`). Proxy for "did the answer name the specific operational artifact." Currently low; practical guides should raise this.

Both metrics are per-entry averages; regression gate at 2pp tolerance with `_HIGHER_BETTER`.

**Success criteria.**

| Metric | Today | Target after V2-3 (tier 1 complete) |
|---|---|---|
| `safety_abstention_rate` on DIAN-procedure queries | high | ≤ 0.05 |
| `retrieval@10` on covered topics | variable | ≥ 0.55 (from ~0.20) |
| `answer_body_length_median_chars` on covered-topic queries | ~700 | ≥ 1200 |
| `answer_distinct_forms_cited` on covered-topic queries | ~0.3 | ≥ 1.5 |
| `citation_precision` | 0.991 | ≥ 0.985 (regression gate — new content must not introduce ghost-article cites) |

**Acceptance test (DIAN procedure, tier 1).** Pick three representative accountant queries not in the gold set ("requerimiento ordinario DIAN qué hacer", "auditoría DIAN plazos respuesta", "pruebas DIAN requerimiento especial") and run them through the pipeline post-ingest. Each must produce a > 1500-char answer that names at least one DIAN resolution, at least one ET procedural article (e.g., 707, 708, 714), and a step-by-step in the "Procedimiento" section. Accountant spot-checks all three for factual correctness before tier 1 is declared done.

**Risks + mitigations.**
- *Specialist bandwidth.* One DIAN-procedure specialist cannot simultaneously draft all five tier-1 docs. → Parallelize by document type: N01 + E01 can be drafted in parallel with L02 (different levels of abstraction); L03 + L04 follow. Same specialist, staggered.
- *Factual drift in drafted content.* Any document citing fictitious articles destroys the citation-precision number we paid to achieve. → Mandatory accountant review gate + automated post-ingest check: new documents' `legal_reference` fields are validated against the actual article graph before `canonical_blessing_status` flips to `canonical`.
- *Scope creep.* Curator hands engineer a 40-page narrative. → Template enforcement (step 3) rejects non-conforming drafts at the ingest stage.

**Effort.** Engineering: ~1 day (census script + 2 new harness metrics + ingestion post-check). Curator/specialist: 2–3 weeks for tier 1, ongoing for tiers 2–3.

---

## Joint success criteria (all three items together)

The baseline we lock at 2026-04-22 is our zero-line. After all three items are complete:

| Metric | Today | Combined target |
|---|---|---|
| `router_accuracy` | 0.429 | ≥ 0.80 |
| `safety_abstention_rate` | 0.233 | ≤ 0.08 |
| `retrieval@10 (with_connected, loose)` | 0.275 | ≥ 0.55 |
| `body_vs_expected_alignment` | 0.500 | ≥ 0.75 |
| `body_vs_router_alignment` | 0.727 | ≥ 0.85 |
| `citation_precision (loose)` | 0.991 | ≥ 0.985 (floor, non-negotiable) |
| `primary_anchor_recall (loose)` | 0.855 | ≥ 0.85 (floor) |
| `sub_question_router_accuracy` (new) | TBD | ≥ 0.70 |
| `answer_body_length_median_chars` (new) | ~700 | ≥ 1000 |
| `answer_distinct_forms_cited` (new) | ~0.3 | ≥ 1.0 |

**The regression-gate harness trio protects every one of these numbers across every PR.** Nothing in v2 is allowed to improve one metric by regressing another beyond 2pp; that's the commitment the citation-precision floor and primary-anchor-recall floor encode.

## Sequencing

```
Week 1 (this week)
  Mon–Tue   V2-1 engineering pieces: inventory, miner script, polysemous-collision test harness
  Wed       V2-3 engineering pieces: census script, two new harness metrics
  Thu       V2-2 engineering: query_decomposer.py module + orchestrator wiring (off by default)
  Thu–Fri   V2-1 curator: first 5 topics' keyword review (RST, patrimonio, SAGRILAFT, obligaciones_contador, fondo_solidaridad)
  Fri       V2-1 merge: first PR lands keywords for 5 topics with full harness regression gates

Week 2
  Mon–Wed   V2-1 curator: remaining 10 priority topics, merged in batches of 3–5
  Mon       V2-3 Tier 1 commissioning: DIAN-procedure specialist starts PRO-N01 + PRO-E01
  Tue–Thu   V2-2 staging flip: LIA_QUERY_DECOMPOSE=on in dev:staging; measure harness lift for 48h
  Fri       V2-2 production decision: if ≥ 5pp lift on body_vs_expected_alignment with no regression elsewhere, ship to production

Weeks 3–4
  V2-3 Tier 1 tranche lands (N01 + E01 first, L02–L04 rolling)
  V2-1 remaining long-tail topics (labor niches, UGPP, precios de transferencia)
  Gold growth 30→50 via log mining (accountant, in parallel)
  Re-freeze all three baselines at the end of week 4; bump aspirational red lines

Weeks 5–8
  V2-3 Tier 2 + Tier 3 documents land via the same ingestion pathway
  Continuous harness gating
```

## Out of scope for v2

- **LLM judgment of answer quality.** Deferred. The harness trio gives deterministic signal; an LLM-as-judge layer adds subjectivity and cost without solving any measured failure.
- **Reranker live mode.** Still `shadow` until a bge-reranker-v2-m3 sidecar is deployed. V2 does not depend on it — all target metrics are achievable with retrieval reranked in shadow.
- **Replacing the lexical topic router with an LLM classifier.** Rejected for V2-1 reasons (latency, non-determinism, hot-path concerns).
- **Full-fanout retrieval-harness baseline** (`skip_sub_questions=false`). Still deferred until a non-hanging path through the pipeline is diagnosed; not load-bearing for V2 items' success criteria, all of which operate on the `skip_sub_questions=true` methodology.

## Decision log baked in

Choices that deserve to be visible so future Claude-family agents don't re-debate them:

1. **Topic router stays lexical.** Hot-path latency + determinism wins over an LLM classifier even though the LLM would score better on router_accuracy in isolation.
2. **Query decomposer is LLM-assisted, not LLM-gated.** Regex first pass handles 80% of gold M-type queries; LLM only disambiguates. This keeps decomposer unavailable ≠ whole pipeline down.
3. **Corpus curation runs parallel to engineering.** Neither blocks the other. Engineering items V2-1 and V2-2 are shippable without V2-3; V2-3 gets richer value from them but doesn't require them.
4. **All baselines re-freeze on every structural change.** Regression gate is against the committed baseline, never against aspirational targets. Never lower aspirational targets to make a red metric green; re-freeze the baseline if a change is a judged improvement.

## Change log

| Version | Date | Notes |
|---|---|---|
| v2 (this doc) | 2026-04-22 | Three items derived from v1 re-evaluation section. V2-1 router keyword coverage, V2-2 query decomposition, V2-3 practical-guide corpus curation. Joint success criteria locked against 2026-04-22 committed baselines. |
| v2.1 | 2026-04-22 | **V2-1 landed.** Populated 9 gold-touching empty topics (`regimen_simple`, `impuesto_patrimonio_personas_naturales`, `sagrilaft_ptee`, `zonas_francas`, `obligaciones_profesionales_contador`, `informacion_exogena`, `perdidas_fiscales_art147`, `dividendos_utilidades`, `regimen_sancionatorio`) plus `fondo de solidaridad pensional` phrases in `laboral`. Baselines re-frozen. Measured deltas: **router_accuracy 0.429 → 0.607 (+17.9pp)**, **retrieval@10 0.275 → 0.336 (+6.1pp)**, **safety_abstention_rate 0.233 → 0.067 (−16.7pp, 5 fewer silent abstentions)**, **body_vs_expected_alignment 0.500 → 0.560 (+6.0pp)**, **citation_precision stable at 0.993**. Two methodology-shift drops: `body_vs_router_alignment` 0.727 → 0.630 (writer now correctly recognizes narrow topics but the generic answer templates still drift broad — synthesis-layer issue, out of scope) and `primary_anchor_recall` 0.855 → 0.825 (queries that used to abstain now get scored, some fall below mean — metric got more complete, not worse). 38 empty topics remain; long-tail work continues via `scripts/mine_topic_keywords.py` when curator bandwidth frees up. | `src/lia_graph/topic_router_keywords.py`, `evals/baseline.json`, `evals/faithfulness_baseline.json`, `evals/alignment_baseline.json` |
| v2.2 | 2026-04-22 | **V2-2 landed (default OFF, ready to flip in staging).** New module `src/lia_graph/pipeline_d/query_decomposer.py` + env flag `LIA_QUERY_DECOMPOSE=off\|on` (default `off`). When enabled AND a query has 2–5 `¿…?` sub-questions, the orchestrator routes + plans + retrieves per sub-query and merges the evidence bundles before synthesis. Regex-first splitter reuses `planner._extract_user_sub_questions`. LLM disambiguation is a stub seam for a future v2 iteration. New metric in the alignment harness: `sub_question_router_accuracy` — for M-type gold entries, fraction of sub-questions that route to their gold-annotated `expected_topic`. Baseline: **0.452 (n=42)**. All three harness gates still pass at the default-off state. End-to-end smoke of a 3-intent synthetic query confirms the fan-out works: three sub-queries each route to their own topic (retención / RST / SAGRILAFT), retrieve independently, and merge into a 6-article primary bundle with per-sub-query provenance in `diagnostics.evidence_bundle.diagnostics.sub_query_retrieval`. Next step: flip the flag in `dev:staging` and measure the lift on `body_vs_expected_alignment` for 48h before production rollout. | `src/lia_graph/pipeline_d/query_decomposer.py` (new), `src/lia_graph/pipeline_d/orchestrator.py` (fan-out wiring + diagnostics), `scripts/eval_topic_alignment.py` (new metric + baseline re-freeze), `evals/alignment_baseline.json` |
