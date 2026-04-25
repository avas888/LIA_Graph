# Structural Work — v3 (PENDING)

**Status:** Proposal. v2 (`docs/next/structuralwork_v2.md`) shipped V2-1 (router keyword coverage, 9 empty topics populated) and V2-2 (query decomposition, `LIA_QUERY_DECOMPOSE=on` flipped in staging on 2026-04-22). V3 is what to do next; it lives as `_v3pending.md` until the user approves the items and sequencing, at which point it moves to `_v3SEENOW.md`.

**Framing question:** what adds the most value to the answer an accountant actually reads — and keeps the answer correct while doing it?

---

## Baseline imprinted (2026-04-22, post-V2 shipped state, `LIA_QUERY_DECOMPOSE=on`)

All three harnesses re-frozen on 2026-04-22 under the production-shipped v2 pipeline (reranker=shadow, decompose=on, polish default). Any V3 work is gated against these numbers at ±2pp regression tolerance.

| Metric | Value | What it tells us |
|---|---|---|
| `retrieval@10` (with_connected, loose) | **0.336** | Retriever ceiling is low — 66% of gold-anchor articles are never surfaced. |
| `nDCG@10` (with_connected, loose) | 0.270 | Rank-aware retrieval — the few right articles we find aren't at the top. |
| `MRR` (with_connected, loose) | 0.326 | First relevant hit lands at rank ~3 on average. |
| `router_accuracy` | **0.607** (n=28) | Resolver hits gold topic 60% of the time. |
| `citation_precision` (loose) | **0.990** (n=27) | Essentially no hallucination. This is the floor we will not sacrifice. |
| `primary_anchor_recall` (loose) | 0.826 (n=27) | Writer cites 83% of hop-0 planner anchors. |
| `abstention_rate` (citations) | 0.100 | 10% of queries produce no inline cites (3 of 30). |
| `body_vs_router_alignment` | **0.593** (n=27) | Writer drifts off the router's topic on 41% of served answers. |
| `body_vs_expected_alignment` | **0.560** (n=25) | Product correctness — only 56% of answers discuss the topic the accountant asked about. |
| `safety_abstention_rate` | 0.067 (n=30) | Safety checks fire on 2 of 30 queries. Within band (0.03–0.25). |
| `misalignment_detection_rate` | 0.357 (n=28) | 36% of served answers are hedged, not abstained. |
| `sub_question_router_accuracy` | **0.452** (n=42) | V2-2 metric — each `¿…?` routes to its gold topic 45% of the time individually. |

**Three numbers most load-bearing for the accountant's experienced value:**
1. `retrieval@10 = 0.336` — if the right article isn't retrieved, no downstream work can cite it correctly. This is the ceiling on breadth.
2. `body_vs_expected_alignment = 0.560` — even when retrieval works, the writer discusses the right topic in barely half of answers. This is the ceiling on relevance.
3. `sub_question_router_accuracy = 0.452` — each sub-question independently routes correctly less than half the time. This is the ceiling on multi-part-question depth.

**One number not to touch:** `citation_precision = 0.990`. Every V3 item must keep this ≥ 0.985. If a change would move it below, the harness regression gate fails the PR.

---

## The three V3 items

### V3-1. Cross-encoder reranker live mode (`LIA_RERANKER_MODE=live`)

**Current state.** Structural v1 shipped the shadow-mode scaffold: `src/lia_graph/pipeline_d/reranker.py` implements `off | shadow | live` with an HTTP contract against `LIA_RERANKER_ENDPOINT`. Shadow logs the delta between hybrid top-10 and reranker-proposed top-10 in `response.diagnostics.reranker` but serves hybrid order unchanged. Live mode reorders `primary_articles` by the sidecar's score.

The senior RAG review flagged a cross-encoder reranker over hybrid top-50 as the single biggest precision lever available for Spanish legal text — because BM25 and dense retrieval return lots of surface-similar-but-legally-wrong chunks (different articles citing the same phrase, derogated versions, sibling subtopics). A cross-encoder sees the query and chunk jointly and is the only component that can distinguish them.

**Why this is V3-1 (not V2's top item).** We deferred the sidecar because shadow mode was enough to measure whether reranking would help before spending the infra budget. V2 didn't need it — V2-1 and V2-2 were routing-layer fixes. V3-1 is the first item that specifically targets `retrieval@10` and `nDCG@10`, which are now the load-bearing ceiling metrics.

**Technical attack plan.**

1. **Stand up the sidecar.** `bge-reranker-v2-m3` behind FastAPI, either on a modest GPU or on Railway CPU with latency headroom (~200–400ms per call at top-50 × ~500-char chunks is feasible on CPU). Expose `POST /rerank` matching the contract the adapter already expects: `{query, candidates:[{id, text}]}` → `{scores}`.
2. **Deploy behind `LIA_RERANKER_ENDPOINT`** in staging first, production second.
3. **Shadow-measure for 48h.** With the sidecar healthy, `diagnostics.reranker.delta_jaccard` and `delta_swap_count` accumulate per query. The harness regression gate's `reranker_mode` methodology field already catches the shadow-vs-live transition.
4. **Extend the retrieval harness** with a shadow-mode comparator: `retrieval@10_if_reranked` — what retrieval@10 *would have been* if we'd served the reranked order. Computed from the already-logged rerank scores, no additional calls. This lets us preview the live-mode lift before flipping.
5. **Flip to live.** `LIA_RERANKER_MODE=live` in staging's dev-launcher config. Re-freeze the three baselines under the new methodology (gate expects this — methodology-mismatch guard fires until re-frozen).
6. **Production flip** after staging shows a ≥5pp lift on `retrieval@10` with `citation_precision` unchanged.

**Success criteria.**

| Metric | Baseline | Target after V3-1 |
|---|---|---|
| `retrieval@10` (with_connected, loose) | 0.336 | **≥ 0.45** |
| `nDCG@10` (with_connected, loose) | 0.270 | ≥ 0.40 |
| `MRR` (with_connected, loose) | 0.326 | ≥ 0.50 |
| `citation_precision` (loose) | 0.990 | ≥ 0.985 (floor, non-negotiable) |
| `primary_anchor_recall` (loose) | 0.826 | ≥ 0.82 (floor) |
| p95 pipeline latency | baseline — measure pre-flip | ≤ baseline + 500ms |

**Risks + mitigations.**
- *Sidecar latency spikes.* → Pre-flight health check; fallback to hybrid order with `reranker_fallback=true` in diagnostics. Already implemented; needs staging validation.
- *Sidecar cost.* → Cheap on Railway CPU for the first weeks; revisit GPU when sustained load justifies it.
- *Rerank degrades precision on specific legal-domain queries.* → Already catchable: `citation_precision` on the harness must stay ≥ 0.985. Regression gate protects.

**Effort.** Engineering: 1 day for sidecar standup + harness comparator + deployment. Ops: 1 day for staging validation + production flip.

---

### V3-2. Synthesis topic-discipline

**Current state.** `body_vs_router_alignment = 0.593` means 41% of served answers — even when the router picks the correct topic — are written with language that scores highest on a different topic's keyword bank. Q20 (sanción by extemporaneidad, router picked regimen_sancionatorio correctly) has a body dominated by `declaracion_renta` vocabulary. Q3 (correction + audit-benefit, router picked declaracion_renta) has a body dominated by `procedimiento_tributario` vocabulary.

**Root cause.** The answer template scaffolding (`Ruta sugerida`, `Riesgos y condiciones`, `Soportes clave`) is generic — it doesn't know the router's chosen topic. When the retrieved evidence has cross-topic hits (primary articles from the target topic plus connected articles from adjacent topics), the template weaves them into the body without a topic-discipline pass. Connected articles often contribute the dominant vocabulary because there are more of them.

The citation harness confirms this isn't a hallucination: precision is 0.990, so the cited articles are grounded. It's a *framing* problem: the answer body discusses adjacent content extensively while citing the target articles — an accountant reading it sees authoritative citations under a body that wandered.

**Technical attack plan.**

1. **New check in `pipeline_d/topic_safety.py`**: `detect_body_topic_drift(answer_markdown, router_topic)`. Runs AFTER synthesis but BEFORE the response is returned. Scores the answer body's topic-keyword distribution against the router's chosen topic. If the router's topic isn't the top scorer, flag `body_drift_detected=true` with the top competitor topic.
2. **Hedged response path.** If drift is detected, wrap the answer with a one-line header: `**Nota de clasificación:** la consulta se clasificó como {router_topic}, pero el desarrollo de la respuesta toca también {dominant_body_topic}; revisa que ambos ángulos se ajusten a tu caso.` The accountant sees both topics named explicitly and can self-filter.
3. **Template-level mitigation** (harder, second pass). In `answer_assembly.py`, when the router topic is known, inject a topic-specific header template that biases the writer toward on-topic vocabulary: `**Tratamiento específico de {router_topic}**` at the top of the "Ruta sugerida" section. Measure whether this reduces drift.
4. **New harness metric** `body_drift_detected_rate` in the alignment harness — fraction of served answers where the drift check fires. This is the quantity V3-2 moves.

**Success criteria.**

| Metric | Baseline | Target after V3-2 |
|---|---|---|
| `body_vs_router_alignment` | 0.593 | **≥ 0.80** |
| `body_vs_expected_alignment` | 0.560 | ≥ 0.65 (indirect lift via router-alignment improvement) |
| `body_drift_detected_rate` (new) | TBD at first measurement | report, not gated at v0 |
| `citation_precision` (loose) | 0.990 | ≥ 0.985 (floor) |
| `primary_anchor_recall` (loose) | 0.826 | ≥ 0.82 (floor) |
| `abstention_rate` | 0.100 | ≤ 0.12 (we don't want the hedge header to spiral into abstentions) |

**Risks + mitigations.**
- *Hedge header is noisy and accountants ignore it.* → Measure click-through in the UI layer once we have product analytics. Out of scope for v0.
- *Template-per-topic becomes hard to maintain.* → Don't template per topic exhaustively — only the top 10 topics cover ~80% of traffic (fat head). Everything else gets the generic template + the hedge header.
- *Template rewrite regresses citations.* → Regression gate on `citation_precision` is the safety net.

**Effort.** Engineering: 1 day for the drift detector + hedge header + new harness metric. 1 more day if we ship the per-topic template variants (recommended after step 1–2 are measured).

---

### V3-3. Corpus curation rollout for the three highest-traffic empty-practica topics

**Current state.** v2 commissioned the DIAN-procedure slate (five documents: PRO-N01, PRO-E01, PRO-L02/L03/L04) via `docs/next/commission_dian_procedure_slate.md`. Specialist is engaged; deliverables land over the next 20 business days.

The gold set reveals **three more empty-practica domains that cost us answer quality**:

1. **RST operations** (Q12, Q13): `regimen_simple` now routes correctly thanks to V2-1, but the corpus has ET articles 903–915 and no practical guide. Accountants asking about bimonthly anticipos, Form 2593, annual Form 260, or exit rules get articles cited but no step-by-step.
2. **UGPP audit defense**: payroll audit response, contribution reconciliation, pleiting before UGPP. Heavy real-world cost (UGPP sanctions regularly hit millions). Covered in laboral vocabulary but no practica.
3. **Devoluciones de saldos a favor** (Q22, partly Q3): the procedural mechanics of requesting a refund — application, supporting documentation, DIAN response windows, escalation if denied. Art. 815, 854, 855 are in the corpus; no practica wraps them.

**Technical attack plan.**

1. **Commission the three additional slates** using the existing `commission_dian_procedure_slate.md` template, one specialist per domain (they don't overlap):
   - **Slate B (RST operations)** — 4 documents: RST-N01 normativa marco, RST-E01 doctrinal, RST-L02 anticipos bimestrales step-by-step, RST-L03 exit and re-entry.
   - **Slate C (UGPP audit defense)** — 4 documents: UGPP-N01 marco, UGPP-E01 doctrinal, UGPP-L02 respuesta a requerimiento, UGPP-L03 defensa en liquidación.
   - **Slate D (Devoluciones)** — 3 documents: DEV-N01 marco, DEV-E01 doctrinal, DEV-L02 solicitud paso-a-paso.
2. **Parallelize.** Slates B/C/D run in parallel with slate A (DIAN procedure) — different specialists, no content overlap. Total specialist-bandwidth: 3 domain experts × 2 weeks each.
3. **Ingestion pathway unchanged.** Same canonical 8-section template, same single-pass ingest, same three-gate sign-off (specialist → accountant → automated citation validation). No engineering needed beyond what v1/v2 already shipped.
4. **New harness metrics** to quantify the depth/breadth gain, deferred from v2:
   - `answer_body_length_median_chars` — answer length; higher = more substantive coverage.
   - `answer_distinct_forms_cited` — count of formulario numbers (regex `(?i)formulari[oas]\s+(\d{2,4})`) in the answer. Proxy for "did the answer name the specific operational artifact."
   - Both metrics added to `eval_retrieval.py` with `_HIGHER_BETTER` regression gates at 2pp tolerance.

**Success criteria.**

| Metric | Baseline | Target after V3-3 (all four slates, ~6 weeks) |
|---|---|---|
| `retrieval@10` (with_connected, loose) | 0.336 | ≥ 0.50 (post-reranker; V3-1 contributes the other half) |
| `body_vs_expected_alignment` | 0.560 | **≥ 0.75** |
| `abstention_rate` on covered topics | variable | ≤ 0.05 |
| `answer_body_length_median_chars` (new) | ~700 | **≥ 1200** |
| `answer_distinct_forms_cited` (new) | ~0.3 | **≥ 1.5** |
| `citation_precision` (loose) | 0.990 | ≥ 0.985 (floor) |

**Acceptance test per slate.** Pick three accountant-submitted production queries (not in gold) for the covered topic; run through the pipeline post-ingest; each must produce a ≥ 1500-char answer citing at least one specific form/deadline/UVT, with accountant sign-off on substantive correctness.

**Risks + mitigations.**
- *Specialist bandwidth.* → Parallelize by domain; cap any single specialist at one slate at a time.
- *Content drift between slates.* → Shared review checklist; accountant reviewer signs off across all four slates for consistency.
- *Factual errors in drafted content.* → Citation-faithfulness harness gate catches drafts that cite articles not in the graph. Accountant review is the human gate.

**Effort.** Engineering: ~1 day (two new harness metrics + acceptance-test harness). Curator/specialist: 6 weeks for all three additional slates; DIAN slate (v2) continues in parallel.

---

## Joint success criteria (V3-1 + V3-2 + V3-3)

The canonical v3 target: what the three items together should deliver against the current imprinted baseline.

| Metric | Imprinted (2026-04-22) | V3 target (all 3 shipped) |
|---|---|---|
| `retrieval@10` | 0.336 | **≥ 0.55** |
| `nDCG@10` | 0.270 | ≥ 0.45 |
| `MRR` | 0.326 | ≥ 0.50 |
| `router_accuracy` | 0.607 | ≥ 0.75 (no direct V3 action; drifts upward as gold grows and aliases improve) |
| `citation_precision` (loose) | 0.990 | **≥ 0.985** (floor — the number we refuse to trade) |
| `primary_anchor_recall` (loose) | 0.826 | ≥ 0.85 |
| `body_vs_router_alignment` | 0.593 | **≥ 0.80** |
| `body_vs_expected_alignment` | 0.560 | **≥ 0.75** |
| `sub_question_router_accuracy` | 0.452 | ≥ 0.65 (reranker indirectly helps; most lift comes from corpus breadth) |
| `abstention_rate` | 0.100 | ≤ 0.08 |
| `answer_body_length_median_chars` (new) | ~700 | ≥ 1200 |
| `answer_distinct_forms_cited` (new) | ~0.3 | ≥ 1.5 |

**What winning looks like in one sentence:** the accountant reads a longer, more specific answer that cites the right law, discusses the right topic, names the right form and deadline, and is right — with the regression-gated harnesses demonstrating each of those moved while hallucination stayed at floor.

---

## Explicit non-scope for V3

- **Replacing the lexical topic router.** Still correct for hot-path latency + determinism. If router_accuracy stalls below 0.70 after V3-1 ships, revisit.
- **Growing the gold set past 50 entries.** That's a curator track; growing the gold helps the aspirational red lines become meaningful but doesn't require engineering. Runs in parallel, not blocking.
- **LLM-judged answer quality.** Deferred indefinitely — deterministic harness signal is more trustworthy.
- **Full-fanout retrieval-harness baseline** (sub-questions). Still deferred; not load-bearing for V3 metrics.

## Sequencing

```
Week 1 (V3 week 1)
  V3-1 engineering: sidecar image, deployment scripts, shadow-mode comparator metric
  V3-2 engineering: body-drift detector + hedge header (default on)
  V3-3 commissioning: slates B + C + D briefs drafted and sent

Week 2
  V3-1 staging: deploy sidecar, let shadow metrics accumulate for 48h, compute expected live-mode lift
  V3-2 staging: hedge header visible in staging; accountant team reviews first 20 hedged answers
  V3-3 specialists begin drafting

Week 3
  V3-1 live: flip to live in staging after shadow confirms ≥ 5pp lift; measure 48h; flip production
  V3-2 template variants: top-10 topic-aware templates land
  V3-3 slate A (DIAN) first documents land via ingest pipeline

Weeks 4–6
  V3-3 rolling ingestion as slate deliverables complete
  Gold growth 30→50 runs in parallel (accountant, separate track)
  Re-freeze baselines at the end of week 6; bump aspirational targets

Week 7
  V3 retrospective: which item delivered the biggest value-per-effort for the accountant?
  Write v4pending.md based on what the answers still miss after V3 lands.
```

## Change log

| Version | Date | Notes |
|---|---|---|
| v3 (this doc, pending) | 2026-04-22 | Proposed V3 items: cross-encoder reranker live mode (V3-1), synthesis topic discipline (V3-2), corpus curation rollout to three additional empty-practica domains (V3-3). Post-V2 baseline imprinted. Gated on user approval before moving to `_v3SEENOW.md` and beginning execution. |
