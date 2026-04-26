# Re-evaluation (2026-04-22, after three harnesses landed)

**This section is a re-read of the original backlog under the light of what the three harnesses revealed.** The original doc (preserved below from "Top Ranked" onward) was written before we had any measurement. We now have three. The conclusions below should be treated as the operative understanding; the long-form catalog that follows is preserved for context on items that haven't been re-evaluated yet.

## The single most-important finding

The citation-faithfulness harness accidentally surfaced a failure mode that reranks the entire backlog: **~15% of non-abstaining answers on the gold set were topically wrong while citing real articles with authoritative formatting.** Citation precision was 0.99 — the hallucination was NOT at the cite level. It was at the topic level: the system routed a patrimony-tax question to something adjacent, assembled an answer about IVA periodicity, and cited real patrimony articles at the end. An accountant reading it cannot distinguish "cites real law, correctly addresses my question" from "cites real law, answers a different question."

This is the biggest risk in the product today. It was invisible before the harnesses existed.

## What the three harnesses now tell us

With the safety checks landed (2026-04-22), the joint baseline on the 30-entry gold is:

| Metric | Value | Interpretation |
|---|---|---|
| retrieval@10 (with_connected, loose) | **0.275** | Retriever-only recall. Where the original structural doc's items A–H aim. |
| nDCG@10 (with_connected, loose) | 0.238 | Rank-aware retrieval quality. |
| MRR | 0.290 | Mostly tracks retrieval@10 at n=30. |
| router_accuracy | **0.429** (n=28) | Resolver-only measure. Below target; structural backlog item C was already designed to help. |
| citation_precision (loose) | **0.991** (n=22) | Cite-level faithfulness. Essentially ceiling — the writer does not fabricate. |
| primary_anchor_recall (loose) | **0.855** (n=22) | Synthesis didn't drop evidence. IMPROVED from 0.754 after the safety checks filtered the worst-aligned queries. |
| abstention_rate (citation harness) | 0.267 | Now carries both pre-existing `Cobertura pendiente` and the new `topic_safety_abstention` paths. |
| body_vs_router_alignment | **0.727** (n=22) | In-pipeline consistency. 27% of served answers' body drifts from the router's chosen topic. |
| body_vs_expected_alignment | **0.500** (n=20) | Product correctness. Half of served answers discuss the topic the accountant's gold annotation expected. |
| safety_abstention_rate | 0.233 (n=30) | Within the 0.03–0.25 design band. The router-silent + borderline-misalignment checks are firing on 5 of 30 queries. |
| misalignment_detection_rate | 0.261 (n=23) | 6 of 23 served answers have the misalignment flag — hedged, not abstained. |

## How the original backlog ordering holds up

The senior RAG reorder (top of this doc, #1 → #2 → #3) got the engineering-vs-curator axis right: measurement first, then reranker, then decomposition. **But the load-bearing product problem is now downstream of all of those**: it's topic-level hallucination in synthesis, not retrieval recall. Specifically:

- **A (polysemous weak keywords), C (empty topics)**: help router_accuracy, which is 0.429. Still real, still worth doing, but they only move one dial of three now.
- **B (taxonomy alias + coverage)**: same — helps retrieval@10 (0.275). Real, but not the dangerous number.
- **F, G (planner anchors, diagnostic probes)**: don't move any of the three dials in a measurable way on the 30-entry gold. Defer.
- **H (three-family corpus curation)**: addresses `abstention_rate` for queries where the corpus genuinely has nothing to say. Load-bearing for DIAN-procedure specifically, unchanged.
- **D (multi-intent classifier)**: replaced by the #3a query decomposer in the senior reorder — still unblocked, not yet started.

**The item that was missing from the original doc entirely: topic-safety.** Both router silent-failure and router↔retrieval misalignment are now gated at orchestrator entry (`src/lia_graph/pipeline_d/topic_safety.py`). The safety-abstention path eliminates Q13/Q25/Q27-class failures (confident-looking answers about the wrong tax) by refusing to synthesize when the routing signal is insufficient. This is a NEW backlog item not in the A–H catalog; it became obvious only after the alignment harness existed.

## Revised order (as of 2026-04-22)

1. **Topic-safety tuning** (in-flight). The thresholds (`ROUTER_SILENT_CONFIDENCE_THRESHOLD = 0.15`, `MISALIGNMENT_PROMOTE_TO_ABSTENTION_BELOW = 0.50`) are v0 guesses. Re-calibrate as gold grows and more data arrives. Monitor `safety_abstention_rate`'s band (0.03–0.25).
2. **Router accuracy** — items C (empty topics) + A (polysemous weak keywords). Direct move on the 0.429 number. Still curator-assisted.
3. **Taxonomy coverage** — item B. Moves retrieval@10 on queries where the retrieval-side vocabulary is thin.
4. **Query decomposition** — #3a from the senior reorder. Multi-`¿…?` is still under-measured; decomposition makes each sub-question its own routable unit.
5. **H (three-family curation)**: parallel, curator-bottlenecked.
6. **Open question**: does item #4 (decomposition) reduce or grow `safety_abstention_rate`? Hypothesis: reduces it, because decomposed sub-questions are more likely to route confidently. Measure when shipping.

## What NOT to do (lessons learned from the inspection)

- **Don't add a "safety-net citation trailer" at the bottom of answers.** The first-round recommendation was this; the forensic read of the 4 worst-recall cases showed that forcing citations of orphaned primaries would pollute answers with irrelevant cites. The current 0.991 precision is precisely *because* the writer refuses to cite articles that don't match. A trailer breaks that invariant.
- **Don't loosen the per-sentence relevance cutoff.** Same reason.
- **Don't treat `primary_anchor_recall < 1.0` as a bug.** Some primaries are legitimately tangential to the specific query; citing them would be false precision.
- **Don't chase body_vs_expected_alignment past 0.70 without improving retrieval and routing first.** The writer can only be "on topic" if the retrieved articles are on topic; improving the writer alone hits a ceiling at whatever the router+retriever provide.

---

# Top Ranked (Senior RAG Friend-Review, 2026-04-22)

**Review.** The author's order (`E → F → G → C → A → B ∥ H → D`) was re-read by a senior RAG practitioner (10+ years IR, hybrid retrieval, graph-augmented RAG, regulated-domain curation). Her top-line verdict: the data-before-architecture instinct is right, H's three-family framing is right, and deferring D is right — but the doc has **three large blind spots that outrank most of A–H**: no evaluation harness, no reranker, and D-as-classifier instead of D-as-query-understanding. Her reordering follows. See full review at the tail of this file or reconstruct from conversation; the three items below are the opening slate regardless of what the author's ordering said.

## Landed state (2026-04-22, revised after expert verdict)

Day 1–2 of the week-1 slate shipped, then was revised end-to-end after the senior-RAG verdict captured in `docs/next/package_expert.md`. Current state:

- **#1 eval harness** — `scripts/eval_retrieval.py` reads `evals/gold_retrieval_v1.jsonl` (30 entries), fires each through `resolve_chat_topic` → `run_pipeline_d` (and each sub-question of M-type entries individually), scores against curator-annotated `expected_article_keys` + router topic labels. Reports every retrieval metric across a **2×2 matrix**: `(primary_only | with_connected) × (strict | loose normalizer)`. The expert's critique was that collapsing those two axes hid what the number meant — the loose−strict delta shows the cost of the "parent-container counts as a hit" UX looseness, and the with_connected−primary_only delta shows how much graph expansion rescues the planner's direct anchors. No fuzzy matching, no LLM judging — both strict and loose are explicit-rule canonicalizations.
- **CI gate: regression-vs-baseline, not absolute floors.** `make eval-retrieval` diffs against a committed `evals/baseline.json` and fails when any reported metric regressed by more than `--tolerance-pp` (default 2pp). Rationale: at n≈25 scoring entries the 95% CI on r@10 is ±~18pp, so an absolute `>= 0.70` floor would both false-fail clean PRs and false-pass real regressions. Absolute red lines (`retrieval@10 ≥ 0.70`, `router_accuracy ≥ 0.85`, `sub_question_recall@10 ≥ 0.60` — all against `with_connected_loose`) stay in the report as aspirational targets, opt-in via `ASPIRATIONAL=1`. Switch to absolute gating once the gold hits ~80 entries.
- **Rename: `topic_accuracy` → `router_accuracy`.** `run_pipeline_d` only echoes `request.topic`; the real decision is made upstream by `topic_router.resolve_chat_topic`. The metric measures the resolver. Name reflects that so no one draws a pipeline conclusion from a resolver number.
- **`subtopic_accuracy` dropped from reporting.** Gold `expected_subtopic` slugs were annotated without cross-indexing against `config/subtopic_taxonomy.json`; the 0.000 score was a vocabulary mismatch, not a retrieval signal. Returns once the accountant re-indexes (≈30 min per 30 entries). Deliberately not LLM-mapped — the whole point of the eval is to not depend on that.
- **#2 reranker shadow scaffold** — `src/lia_graph/pipeline_d/reranker.py` adds `LIA_RERANKER_MODE=off|shadow|live` with a `{id, text}` → `{scores}` sidecar contract against `LIA_RERANKER_ENDPOINT`. Wired into `orchestrator.py` right after retrieval; shadow mode logs delta diagnostics into `response.diagnostics.reranker` without changing served order. Sidecar errors fall back to hybrid cleanly. `scripts/dev-launcher.mjs` defaults the flag to `shadow` across all three modes.
- **Baseline committed** — `evals/baseline.json` is the reference snapshot for the regression gate. It carries a `methodology` block (`skip_sub_questions`, `top_k`, `reranker_mode`) that the harness refuses to gate across — a methodology mismatch between CI and baseline returns exit 4 with a clear error, forcing an explicit `--update-baseline` rather than a silent apples-to-oranges compare. The first baseline is frozen at `skip_sub_questions=true, top_k=10, reranker_mode=shadow` (default `make eval-retrieval` methodology); full sub-question fanout is a future baseline. Re-committed whenever a judged retrieval or reranker improvement is accepted; never lowered to make a red number green.

**Baseline snapshot** (`evals/baseline.json`, `skip_sub_questions=true`, `reranker=shadow`, artifacts backend):

| Variant | r@10 | nDCG@10 | MRR | sub_q_recall@10 |
|---|---|---|---|---|
| `primary_only_strict` | 0.244 | 0.214 | 0.290 | 0.244 |
| `primary_only_loose`  | 0.299 | 0.268 | 0.355 | 0.299 |
| `with_connected_strict` | 0.253 | 0.219 | 0.290 | 0.253 |
| `with_connected_loose` | **0.307** | 0.274 | 0.355 | 0.307 |

Router accuracy: **0.429 (n=28)**. Two entries (Q19, Q28) correctly excluded via `expected_topic_uncertain`. Diagnostic reads: loose−strict ≈ +5.4pp (the cost of treating "in the parent article/law" as a hit); with_connected−primary_only ≈ +0.9pp (graph expansion is barely rescuing anything — the planner either anchors at hop 0 or misses entirely). MRR is identical for `*_loose` across scopes, confirming that graph expansion never contributes a first hit — the rank-1 article is always in `primary_only` when it's there at all.

Curator tracks from the week-1 slate remain human-bottlenecked and have *not* been auto-generated:

- **Day 2–3 gold spot-check** (accountant, ~4h): walk the 30 gold entries, fix any wrong `expected_article_keys`, rule on the two `expected_topic_uncertain: true` cases (Q19 obligaciones_mercantiles, Q28 ZOMAC), and re-index every `expected_subtopic` against `config/subtopic_taxonomy.json`.
- **Day 5 DIAN-procedure commissioning** (domain specialist, 2–3 weeks): PRO-N01 + PRO-E01 first; PRO-L02 / L03 / L04 follow.
- **Day 5 gold growth 30 → 50** (accountant, ~2h): mine 20 queries from `logs/chat_verbose.jsonl` (10 `Cobertura pendiente`, 10 multi-`¿…?`), annotate in the same JSONL schema. Re-commit the baseline against the expanded gold; ratchet from regression-vs-baseline to absolute red lines once n ≥ 80.
- **Citation-faithfulness harness** — **landed 2026-04-22.** Sibling script `scripts/eval_citations.py` + `make eval-faithfulness` target + committed `evals/faithfulness_baseline.json`. Measures two numbers: (1) **citation precision** — fraction of inline `(art. X ET)` anchors in the answer that appear in the retrieved evidence bundle; (2) **primary-anchor recall** — fraction of hop-0 planner anchors that survived into the answer's inline anchors. Plus an **abstention-rate** observability stat (fraction of answers with zero inline anchors). Same methodology-gated regression-vs-baseline CI pattern as `eval-retrieval`. Gold-free — no new curator annotations needed. **Baseline numbers: precision = 0.993, recall = 0.754, abstention = 0.100 (n=30).** All three aspirational red lines (≥0.95 / ≥0.70 / ≤0.25) pass at baseline. v1 scopes inline ET anchors only; body-text regulatory cites (`(Res. X/Y)`, `Ley X de Y`, `Decreto X de Y`) are counted as an observability stat but not scored — v2 axis.

## #1 — Build an eval harness, before touching anything else (MISSING from A–H)

**What.** A gold set of 80–120 query→expected-artifact-keys pairs in JSONL, covering the query shapes already in logs (multi-`¿…?`, cross-topic, DIAN procedure, nómina, facturación electrónica, corrección, devolución, UGPP). For each: the 3–10 `article_key`s any acceptable answer must cite, and the topic/subtopic labels a correct router would emit. Wired to a harness that emits **retrieval@10, nDCG@10, MRR, topic-routing accuracy, subtopic-routing accuracy, and sub-question-level recall** (split the query, score each `¿…?` independently — this is the metric that actually reflects product quality). v0 red lines: retrieval@10 ≥ 0.70, topic-acc ≥ 0.85, sub-question recall ≥ 0.60; ratchet up.

**Why #1.** Every item in A–H is a *hypothesis* about what improves retrieval. Without this harness you have no way to falsify any of them. The author's ordering is based on intuition; half of those items may be neutral or negative on real traffic (alias explosion famously tanks precision on short queries). For a regulated-domain product you cannot ship faith-based engineering.

**Monday move.** One engineer + one accountant, half a day each: pull 40 real queries from logs, the accountant annotates expected `article_key`s and topic labels in a sheet, export to `evals/gold_retrieval_v1.jsonl`. By Friday, a `make eval-retrieval` target that runs the gold through `pipeline_router` and prints the five metrics. Gate every subsequent PR on it. The starting point for this gold set is the 30-question evaluation doc at `docs/quality_tests/EVALUACION-CORPUS-30-PREGUNTAS-RESPUESTAS.md` — reshape it into the harness format described there and grow from 30 to 80–120 over the first two weeks.

## #2 — Add a cross-encoder reranker over `hybrid_search` top-50 (MISSING from A–H)

**What.** After `hybrid_search` returns top-50 chunks, rerank with a multilingual cross-encoder (`BAAI/bge-reranker-v2-m3` self-hosted, or Cohere `rerank-multilingual-v3.0` via API), take top-10 into the synthesis context. One new function in the retriever path, one env var for model/endpoint, ~200–400ms added latency.

**Why #2.** In legal/tax Spanish, BM25 and dense both return lots of *surface-similar-but-legally-wrong* chunks — different articles citing the same phrase, derogated versions, sibling subtopics. A cross-encoder sees the query and chunk jointly and is the single biggest precision lever available for the money. It also partially masks taxonomy gaps (B2) and weak aliasing (B1), because good chunks bubble up by semantic match even when the subtopic router guessed wrong. It outranks F and G (graph-anchor polishing, diagnostic probes) because it helps **every** query, not just the 5–10 workflows with hardcoded anchors.

**Monday move.** Spin up `bge-reranker-v2-m3` behind a small FastAPI sidecar (one modest GPU, or Railway CPU with latency headroom), add `LIA_RERANKER_MODE=off|shadow|live`; run in `shadow` first, logging reranker-top-10 vs hybrid-top-10 differences for a week; flip to `live` once #1 confirms a ≥5pt nDCG@10 lift.

## #3 — LLM query decomposition + H curation for DIAN procedure (combined, replaces most of D)

**What.** Two things fused because they solve the DIAN-audit failure mode end-to-end. **(a)** An upstream LLM query decomposer: cheap call that splits `"¿términos? ¿pruebas? ¿ruta procesal?"` into N atomic sub-queries before routing. Each gets its own topic resolution and retrieval fan-out; results merge at answer assembly. This obsoletes most of D (D1 and D2) at a fraction of the engineering cost because multi-intent becomes a solved *preprocessing* problem instead of a contract rewrite of planner + both retrievers. **(b)** Execute H's DIAN-procedure curation slate — the five documents (N01 marco, E01 doctrinal digest, L02/L03/L04 práctica) — with accountant sign-off (the only non-negotiable: LLM-drafted EXPERTOS/PRÁCTICA without expert review is *worse* than `Cobertura pendiente`).

**Why #3 and not higher.** #1 and #2 land in two weeks of pure engineering. This is curator-bottlenecked. But it is the *only* item that fixes Q3-type failures where the document simply does not exist. Ranking above A/C/F/G because: alias and keyword work improves retrieval of documents *that exist*; this creates the documents that don't. DIAN procedure first (the canonical failing case), prove the three-family loop with measurable eval lift from #1, then scale to UGPP / PILA / precios de transferencia / corrección voluntaria / devolución saldos / RUB actualizaciones.

**Monday move.** Engineer: build the decomposer as a new `query_decomposer.py` module upstream of `topic_router.py`, behind `LIA_QUERY_DECOMPOSE=off|on`, with the eval harness from #1 measuring sub-question recall with and without. Curator track in parallel: commission N01 + E01 for DIAN procedure with the named specialist this week; L02–L04 follow over 2–3 weeks. Ship N01/E01 first — they unblock synthesis before the práctica guides land.

## What this reordering deprioritizes vs the original author order

- **E / F / G** — Small effort, low ceiling. Do opportunistically, not as the opening slate.
- **A (polysemous weak keywords)** — matters, but a reranker (#2) masks most of it.
- **C (40+ empty topics)** — LLM-draft from corpus samples in an afternoon + human review, don't staff as a project.
- **D (multi-intent classifier + multi-topic scope)** — kill outright; replaced by upstream decomposition in #3.

**Net new order:** **#1 eval harness → #2 reranker → (#3a query decomposition ∥ #3b DIAN-procedure curation)**, with A/B/C/F/G falling out as smaller opportunistic work measured against the harness. The author's A–H remain the correct *catalog of structural weaknesses*; the ordering above is what improves RAG overall, fastest, with evidence.

---

# Structural Work — v1 (SEE NOW)

**Context.** Written after investigating two recurring failure modes surfaced by two multi-question accountant queries:

1. A DIAN audit-procedure query (`"requerimiento ordinario... ¿términos? ¿pruebas? ¿ruta procesal?"`) where Q1 got `Cobertura pendiente` because the top-level router mis-routed to `laboral` (via bare-polysemous `liquidación` weak keyword), and because the entire 106-entry subtopic taxonomy had zero alias coverage for the procedural-audit vocabulary.
2. A documento-soporte-de-pago query (`"¿requisitos DSE? ¿resoluciones DIAN y info mínima?"`) where Q1 got a full answer but Q2 got `Cobertura pendiente` because Q2's vocabulary (`resoluciones DIAN regulan expedición electrónica información mínima`) scored 0 against every topic's keywords, hit 0 aliases across the taxonomy, and described a facet the taxonomy has no subtopic entry for at all — compounded by the query being cross-topic (Q1 costos_deducciones, Q2 facturacion_electronica), which the single-topic planner doesn't fan out.

The narrow fixes for investigation (1) landed — `src/lia_graph/topic_router_keywords.py` got `procedimiento_tributario` audit-procedure vocabulary + had polysemous bare `liquidación` entries removed from `laboral.weak`; `config/subtopic_taxonomy.json` got audit-procedure aliases on `simplificacion_tramites_administrativos_y_tributarios`. Investigation (2) got no narrow fix — its root causes are all in this document.

This file catalogs the **general** weaknesses those single-point fixes only papered over. Each item is a data or design pattern that will keep biting new queries until it's addressed at the pattern level. Items are split into **easier fixes** (Part 1 — S-to-M effort, mostly data/tooling, low architectural risk) and **complex fixes** (Part 2 — L effort or crosses module contracts / taxonomy curation scope).

**Scope note.** This is a structural backlog, not a refactor plan with batches. Each item is independently actionable. Effort estimates are coarse (S = under a day, M = a day to a week, L = multi-week).

**Non-goals.** Not re-opening the `main chat` → `Normativa` / `Interpretación` split. Not changing the retriever contract (hybrid_search RPC stays, Falkor Cypher stays). Not touching answer-synthesis / assembly — those are downstream of everything here.

---

# Part 1 — Easier fixes

These are additive, low-risk, and unblock or amplify the harder work in Part 2. Do them first.

## E. No standalone CLI for tracing a query through the pipeline

### Symptom

Every time we debug routing, we reconstruct the trace by ad-hoc Python against `resolve_chat_topic` + `_detect_sub_topic_intent`:

```python
from lia_graph.topic_router import resolve_chat_topic, _score_topic_keywords
from lia_graph.pipeline_d.planner_query_modes import _detect_sub_topic_intent
query = "..."
routing = resolve_chat_topic(message=query, requested_topic=None)
print(routing.effective_topic, routing.confidence, routing.reason)
print(_score_topic_keywords(query))
print(_detect_sub_topic_intent(query, routing.effective_topic))
```

There's no committed tool for this. Every investigation reinvents it. The test suite at `tests/test_phase3_graph_planner_retrieval.py` comes closest but requires writing a test to probe one query.

### Why it's general

Tooling absence compounds. Every time any of items A-D comes back (during adversarial testing, during a regression, during future curation work), the investigator has to recompose the same 10 lines. The shape of the investigation is: *given a query string, emit the full planner/retriever diagnostic trace as JSON*. That's a 30-line script.

### Where to intervene

New file: `scripts/debug_query.py`. Existing `scripts/` convention (sibling to `scripts/backfill_subtopic.py`, `scripts/mine_subtopic_candidates.py`, etc.) is standalone Python scripts with argparse. Target shape:

```python
# scripts/debug_query.py
"""Run a query through the live planner + subtopic classifier and print
a diagnostic JSON trace. Does not hit Supabase or Falkor — lexical layers
only, so it runs in dev without env config.

Usage:
  python scripts/debug_query.py "La DIAN le envió un requerimiento..."
  python scripts/debug_query.py --topic renta "..."     # pin requested_topic
  python scripts/debug_query.py --full "..."            # include full plan.to_dict()
  python scripts/debug_query.py --per-sub-question "..." # run each ¿…? separately
"""
```

Wire (in order):
1. `lia_graph.topic_router.resolve_chat_topic(message=q, requested_topic=...)` → top-level topic + score breakdown via `_score_topic_keywords`
2. `lia_graph.topic_router._check_subtopic_overrides(q)` → which override pattern fired, if any
3. `lia_graph.pipeline_d.planner_query_modes._detect_sub_topic_intent(q, topic)` → subtopic intent + match form
4. `lia_graph.pipeline_d.planner.build_graph_retrieval_plan(request)` → full plan, including entry points and sub-questions (optional, behind `--full`)
5. `lia_graph.pipeline_d.planner._extract_user_sub_questions(q)` → the `¿…?` splits — when `--per-sub-question` is set, repeat steps 1-3 for each split

Output is a single JSON object. No retrieval, no LLM — so it's safe to run unconditionally.

**Add a Makefile target.** The repo has a Makefile with existing targets like `make phase2-graph-artifacts-supabase`. Add:
```makefile
debug-query:
	@test -n "$(Q)" || (echo "Usage: make debug-query Q='your query here'"; exit 1)
	.venv/bin/python scripts/debug_query.py "$(Q)"
```
So investigation becomes `make debug-query Q="..."`.

### Test gates

- `tests/test_debug_query_cli.py` — one test: run the script on a known query via `subprocess`, parse the JSON, assert the expected topic + subtopic. Prevents the script from silently bit-rotting.

### Effort / risk

**S**. One file, one afternoon. Risk is effectively zero. The only thing to watch is not accidentally importing a module that requires env config (Supabase client, LLM adapter) — the lexical layers don't, and the script must not grow to include retrieval without a `--live` flag that errors clearly when env is missing.

---

## C. 40+ top-level topics with zero registered keywords

### Symptom

Running a keyword-registration census:

```python
from lia_graph.topic_guardrails import get_supported_topics
from lia_graph.topic_router_keywords import _TOPIC_KEYWORDS
empty = [t for t in get_supported_topics()
         if not (_TOPIC_KEYWORDS.get(t, {}).get("strong") or
                 _TOPIC_KEYWORDS.get(t, {}).get("weak"))]
# len(empty) == 40+
```

Of ~50 supported top-level topics, only ~8 have manually curated keyword entries (`laboral`, `declaracion_renta`, `iva`, `ica`, `facturacion_electronica`, `estados_financieros_niif`, `calendario_obligaciones`, `procedimiento_tributario`). The other 40+ either have to be populated dynamically via `_bootstrap_custom_corpora()` in `topic_router.py:71-179` (which reads `config/corpora_custom.json`) or they simply never route.

The second investigation exposed a narrower variant of this: `facturacion_electronica` IS populated with 24 strong + 28 weak keywords, but they all describe *what facturación is* (DSE, CUFE, RADIAN, factura de venta). They don't describe *which regulatory instruments govern it* (resoluciones DIAN, información mínima, expedición). Q2 `"¿Qué resoluciones DIAN regulan su expedición electrónica y qué información mínima debe contener?"` scored 0 on `facturacion_electronica` and fell through to `None`. So "zero keywords" isn't the only failure mode — "incomplete keyword facets" is a subtler one that hits populated topics too.

### Why it's general

Every query about an unregistered topic is silently vulnerable. Some examples of topics with zero hardcoded keywords:

- `anticipos_retenciones_a_favor` — queries about anticipos de renta, retenciones a favor
- `beneficiario_final_rub` — RUB / beneficiario final
- `comercial_societario` — sociedades, reforma estatutaria, liquidación de sociedades (!)
- `contratacion_estatal` — SECOP, contratos estatales
- `economia_digital_criptoactivos` — criptoactivos, economía digital
- `ganancia_ocasional` — ganancia ocasional (one of the four renta sub-impuestos)
- `informacion_exogena` — exógena (despite being a core accountant workflow!)
- `precios_de_transferencia` — operaciones entre vinculados
- `regimen_simple` — Régimen Simple
- `retencion_en_la_fuente` — retención en la fuente (despite being a daily workflow)
- `sagrilaft_ptee` — SAGRILAFT, PTEE
- `zonas_francas` — zonas francas

A query like *"¿Cómo reporto la exógena 2025?"* has no `informacion_exogena` strong/weak entries to score against; it will either fall through to `None` or be hijacked by whatever weak term happens to match on an adjacent topic.

### Where to intervene

1. **Decide the intended sourcing per unregistered topic.** The bootstrap at `topic_router.py:71-179` is the escape hatch: a custom corpus declared in `config/corpora_custom.json` with a `keywords: {strong: […], weak: […]}` block auto-registers at import time via `register_topic_keywords` (`topic_router.py:56-68`). So there are two legitimate states for a topic to be in:
   - (a) **Static registration in `_TOPIC_KEYWORDS`** — for topics that are load-bearing enough to belong in code.
   - (b) **Dynamic registration via `corpora_custom.json`** — for topics owned by a specific corpus configuration.

   Everything currently sitting at 0/0 is in neither state. The first task is a diagnostic: for each unregistered topic, classify it as (a)-candidate, (b)-candidate, or "not actually a top-level concern (should be a subtopic under another parent)".

2. **Add a boot-time invariant check.** In `topic_router.py`, after `_bootstrap_custom_corpora()` runs (currently line 182), emit a warning log for every entry in `get_supported_topics()` with zero keywords. Right now a 0/0 topic is silently broken; the invariant would surface it the first time the process starts. One-line addition:

   ```python
   for topic in get_supported_topics():
       kw = _TOPIC_KEYWORDS.get(topic, {})
       if not (kw.get("strong") or kw.get("weak")):
           logger.warning("topic_router: topic %r has no registered keywords", topic)
   ```

3. **Populate the (a) bucket.** For topics that must route without depending on a custom-corpus config (common SMB-accountant workflows: `retencion_en_la_fuente`, `informacion_exogena`, `ganancia_ocasional`, `regimen_simple`), add entries directly in `_TOPIC_KEYWORDS`. These are daily-traffic topics; losing them to a config-file oversight is a production hazard.

4. **Audit the *incomplete* side too.** The populated topics (`facturacion_electronica`, `laboral`, `declaracion_renta`, `iva`, etc.) each need a facet review: for the question *"does this topic's keyword set cover every face of the domain an accountant asks about?"*. Concrete procedure: sample 20 real queries per topic from `logs/chat_verbose.jsonl`, run them through `_score_topic_keywords`, flag any that score 0 despite being unambiguously on-topic. Each flag is a facet gap to fill.

5. **Subtopic vs. top-level disambiguation.** Some of the 40+ may actually be misplaced — they're subtopics masquerading as top-level topics. `gravamen_movimiento_financiero_4x1000` is an interesting case: it's registered as a top-level topic with 0 keywords, but `_SUBTOPIC_OVERRIDE_PATTERNS` (topic_router_keywords.py:577-588) already owns the routing for GMF queries via regex. Check whether the top-level registration is still load-bearing or whether it's dead weight since the override supersedes it.

### Test gates

- `tests/test_topic_router_keywords.py` — add a parameterized test that asserts every topic in `get_supported_topics()` has at least one keyword after `_bootstrap_custom_corpora()` runs. Fails loudly if a new topic gets registered without keywords.
- Smoke tests for each newly populated (a)-bucket topic: 3-5 representative queries per topic, asserting correct routing.

### Effort / risk

**M**. Classification is quick (1 hour). Populating the (a) bucket is a few hours per topic for ~10 topics. The facet-completeness audit (step 4) is the slower part — needs real query logs and per-topic judgment, but it's per-topic-parallel and a junior contributor can drive it once the procedure is written. Risk is low — adding keywords can only *add* routing precision, not subtract it (barring accidental cross-topic pollution, caught by A's adversarial tests).

---

## A. Polysemous bare weak keywords (the "liquidación" anti-pattern)

### Symptom

Query `"¿Cuál es la ruta procesal si escala a requerimiento especial y luego a liquidación oficial?"` routed to `laboral` with confidence 0.3 because `_TOPIC_KEYWORDS["laboral"]["weak"]` contained bare `liquidar` / `liquidacion` / `liquidación` — each of which also means *contract liquidation*, *company dissolution*, *tax self-assessment*, and *DIAN audit liquidation*. The first weak hit, on any topic, wins the keyword scorer when no stronger signal is present. A single polysemous bare term is enough to hijack a whole subdomain of queries.

### Why it's general

The same anti-pattern lives, right now, for these bare entries still in `_TOPIC_KEYWORDS["laboral"]["weak"]` (src/lia_graph/topic_router_keywords.py:96-150):

| Bare term | Other senses it still matches |
|---|---|
| `prima` | prima en colocación de acciones (societario), prima de seguros (financial) |
| `aportes` / `aportaciones` | aportes de capital (societario), aportes a fondos de inversión |
| `cotización` | precio cotizado (comercial / bolsa) |
| `planilla` | planilla de cálculo genérica |
| `bonificación` | bonificación comercial, bonificación fiscal |
| `dotación` | dotación de activos fijos (contabilidad) |
| `salud` | sector salud, impuestos saludables, salud financiera |
| `pensión` | pensión alimenticia (civil), pensión hotelera |

Every item on this list is labor-**dominant**, not labor-**exclusive**. For each one there is a foreseeable query where the labor interpretation is wrong and routing will mis-fire exactly like `liquidación` did. The risk is also not confined to `laboral.weak` — any topic's weak list that contains a bare polysemous term inherits the same problem.

### Where to intervene

Two files, one design rule:

1. **`src/lia_graph/topic_router_keywords.py` — audit every topic's `weak` tuple.**
   The function that consumes these is `_score_topic_keywords(message)` at `src/lia_graph/topic_router.py:284-298`. Scoring is `strong_hits × 3 + weak_hits × 1`, gated by `_keyword_in_text(kw, text)` which uses `\bkeyword\b` word boundaries with no proximity context. The weak bucket exists precisely because these are low-confidence signals — the design assumption is that each weak term is topic-characteristic enough that *any* occurrence nudges toward the topic. That assumption fails for polysemous bare terms.

2. **Where polysemous terms should move.** Two valid relocations:
   - **Up to `strong` as compound phrases.** Bare `prima` → `prima de servicios`, `prima de antigüedad`. Bare `aportes` → `aportes parafiscales`, `aportes seguridad social`. The scorer's `\b…\b` boundary is already compound-safe (it matches `prima de servicios` as a single unit).
   - **Down into `_SUBTOPIC_OVERRIDE_PATTERNS`.** Same file, lines 571-667. Each entry is `(compiled_regex, topic_key, search_keywords_tuple)` and runs **before** keyword scoring via `_check_subtopic_overrides` in `topic_router.py:390-396`. The laboral override at `topic_router_keywords.py:656-666` already demonstrates the pattern: `\bliquid\w*\b[^.?!]{0,30}\b(?:emplead[oa]|trabajador[ae]|…)` — proximity window forces the bare term to fire only with labor context. Polysemous terms that need context can become override entries with a similar proximity regex.

3. **The design rule to codify.** Add this to the module docstring at the top of `topic_router_keywords.py` (currently lines 1-22):

   > Weak-bucket entries must be topic-**characteristic** on their own. A bare term that is topic-**dominant** but also appears in other domains (e.g. `liquidación` — labor-dominant, but also means DIAN audit, company dissolution, tax self-assessment) does not belong in `weak`. Promote it to `strong` as a compound phrase (`liquidación de nómina`) or to `_SUBTOPIC_OVERRIDE_PATTERNS` as a proximity regex (`liquidar` within 30 chars of `empleado/trabajador`).

### Test gates

- `tests/test_topic_router_keywords.py` — add parameterized cases for every polysemous term with an *adversarial* example that should NOT route to the current topic (e.g. `prima en colocación de acciones` must not route to laboral; `cotización en bolsa` must not route to laboral; `sociedad en liquidación` must not route to laboral).
- `tests/test_topic_router_llm.py` exists for the LLM fallback path — the rule-based path gets most of the traffic and deserves equivalent adversarial coverage.

### Effort / risk

**M**. The audit is mechanical once the rule is named. Risk is recall loss on queries that used to squeak through on a bare weak hit — mitigated by adding compound strong entries and/or override regexes to cover the real labor phrasings. Run the existing labor test suite (`pytest -k laboral`) after each removal.

---

## F. Planner procedural-workflow anchor gap

### Symptom

Query `"La DIAN le envió un requerimiento ordinario... ¿términos? ¿pruebas? ¿ruta procesal si escala a requerimiento especial y luego a liquidación oficial?"` routes correctly (after investigation (1)'s narrow fixes landed in `topic_router_keywords.py` and `subtopic_taxonomy.json`) but the Falkor retriever still returns a `Cobertura pendiente` banner with `empty_reason=no_explicit_article_keys_in_plan`. The banner is technically accurate: `retriever_falkor._explicit_article_keys(plan)` filters `plan.entry_points` by `kind == "article"` (src/lia_graph/pipeline_d/retriever_falkor.py:269-276), and the planner only emits `kind="article"` entries when one of three paths fires:

- the user typed an explicit `art. X` reference (caught by `_extract_article_refs` at planner.py:486-501),
- `_looks_like_loss_compensation_case` fires → injects art. 147 (planner.py:326-336),
- `_looks_like_tax_planning_case` fires → injects arts. 869 / 869-1 / 869-2 (planner.py:337-348).

For the procedimiento-DIAN workflow (requerimiento ordinario → respuesta → requerimiento especial → liquidación oficial → recurso de reconsideración), none of these three paths fires. `_looks_like_correction_firmness_case` DOES return True (score ≥ 4 on "requerimiento especial" + "liquidacion oficial") but it only feeds `_build_article_search_queries` (planner.py:583-592), which emits `kind="article_search"` entries — lexical hints, not article anchors, and Falkor's `_explicit_article_keys` ignores them.

### Why it's general

Every procedural-workflow subdomain inherits this gap, not just DIAN audits. The planner's anchor path has exactly two domain-specific anchors hardcoded (loss compensation, tax planning); every other workflow that *should* have a deterministic article seed set has to rely on the user typing the article reference themselves or on the subtopic-bound-articles fallback (`_retrieve_subtopic_bound_article_keys` at retriever_falkor.py:237-266) — which in turn only fires when `_detect_sub_topic_intent` wins, and depends on the taxonomy having the right subtopic keys bound to the right articles (see B2).

Workflows with no planner anchor despite being first-class accountant concerns and having a well-known deterministic article set:

| Workflow | Deterministic article anchor set | Detector status |
|---|---|---|
| DIAN audit procedure (requerimiento ordinario/especial, emplazamiento, liquidación oficial, recurso de reconsideración) | arts. 685, 703, 704, 707, 710, 711, 712, 714, 720, 730, 742, 744 ET | detector exists (`_looks_like_correction_firmness_case`) but currently mixes two distinct workflows; no anchor |
| Corrección voluntaria de declaraciones | arts. 588, 589 ET | detector exists (same mixed one); no anchor |
| Devolución de saldos a favor (trámite) | arts. 850, 855, 857, 860 ET | detector exists (`_looks_like_refund_balance_case`); no anchor |
| PILA / aportes a seguridad social | arts. Ley 100 / Ley 1607 relevantes | no detector, no anchor |
| UGPP fiscalización | arts. Ley 1607 / Ley 1819 relevantes | no detector, no anchor |

Each row is a deterministic article set. "Detector fires → anchor injected" is already the pattern for tax planning and loss compensation; extending it is additive.

### Where to intervene

`src/lia_graph/pipeline_d/planner.py:326-348`. Add sibling blocks to the two existing anchors. Concrete shape:

```python
if not article_refs and not reform_refs and _looks_like_dian_audit_case(normalized_message):
    for article_key in ("685", "703", "704", "707", "710", "711", "712", "714", "720", "730", "742", "744"):
        entry_points.append(
            PlannerEntryPoint(
                kind="article",
                lookup_value=article_key,
                source="dian_audit_anchor",
                confidence=0.88,
                label=f"Art. {article_key} ET",
                resolved_key=article_key,
            )
        )
```

**Required disambiguation before injecting.** `_looks_like_correction_firmness_case` (planner_query_modes.py:359-378) currently fuses two workflows whose anchor sets differ:

- *voluntary correction of one's own return* → arts. 588/589 ET,
- *responding to DIAN audit actions* → arts. 703/710+/742/744 ET.

Its marker tuple `_CORRECTION_FIRMNESS_MARKERS` (lines 249-257) mixes both: `"corregir"`, `"correccion"` belong to voluntary correction; `"requerimiento especial"`, `"liquidacion oficial"` belong to DIAN audits. Fork the detector before wiring an anchor, otherwise every voluntary-correction query gets seeded with arts. 703/710 (wrong anchors) and vice versa. Two new detectors:

- `_looks_like_voluntary_correction_case` — triggers on `"corregir mi declaracion"`, `"correccion para disminuir"`, `"aumentar saldo a favor"`, absent `"requerimiento"` / `"dian"` / `"liquidacion oficial"` context. Anchor: arts. 588, 589.
- `_looks_like_dian_audit_case` — triggers on `"requerimiento"` / `"emplazamiento"` / `"liquidacion oficial"` / `"ruta procesal"` / `"contestar a la dian"` / `"me llego un requerimiento"`. Anchor: arts. 685, 703, 704, 707, 710, 711, 712, 714, 720, 730, 742, 744.

Apply the same pattern to `_looks_like_refund_balance_case`: add an anchor block that injects arts. 850, 855, 857, 860 ET.

**Where NOT to intervene.** Do not widen `_OBLIGATION_MODE_MARKERS` (planner_query_modes.py:132-147) to carry the anchor — that tuple drives `query_mode` selection (traversal budget + evidence shape), not anchor injection. Conflating them couples two orthogonal concerns.

### Test gates

- `tests/test_planner_anchor_injection.py` (new): parameterized fixture of `{query: expected_article_keys_subset}`. One case per workflow — DIAN audit, voluntary correction, refund, tax planning (existing), loss compensation (existing). Asserts `plan.entry_points` includes `kind="article"` entries with the expected `lookup_value` set. Also add negative cases: a voluntary-correction query must NOT anchor arts. 703/710.
- End-to-end in `tests/test_phase3_graph_planner_retrieval.py`: extend with a DIAN-audit query and assert `response.diagnostics.retrieval_health.empty_reason != "no_explicit_article_keys_in_plan"` once the staging graph has those ArticleNodes seeded.

### Effort / risk

**S**. One file for the anchors, one file for the detector split, a handful of tests. Risk is false-positive anchoring — mitigated by the negative adversarial tests above and by the fact that anchor injection only fires when `not article_refs and not reform_refs` (the user gave nothing explicit). Recall-safe by construction: anchors only fill the vacuum.

---

## G. Retriever diagnostic probe fidelity

### Symptom

`_diagnose_empty_primary` (src/lia_graph/pipeline_d/retriever_falkor.py:156-236) receives only `explicit_article_keys` (line 137), not `effective_article_keys`. When `explicit_article_keys` is empty, it short-circuits at line 168-170 with `empty_reason="no_explicit_article_keys_in_plan"` and never inspects whether `subtopic_article_keys` resolved anything.

Two distinct failure modes collapse into one banner:

1. *Planner-no-anchor*: no explicit article refs AND no subtopic intent fired AND no workflow anchor (F) exists → truly empty. Banner `"no_explicit_article_keys_in_plan"` is accurate.
2. *Subtopic-resolved-but-fetch-empty*: subtopic intent fired, `_retrieve_subtopic_bound_article_keys` returned N keys, `effective_article_keys` was non-empty, but `_retrieve_primary_articles` still came back empty (SubTopicNode → ArticleNode edges not seeded in this graph instance, or articles filtered out by the traversal budget). Banner still says `"no_explicit_article_keys_in_plan"` — misleading; triage has to open logs to disambiguate.

### Why it's general

`empty_reason` is the primary triage signal in `PipelineCResponse.diagnostics.retrieval_health` (surfaced by `_compose_partial_coverage_notice` at orchestrator.py:391-401) and it's the first field anyone looks at when the partial-coverage banner appears. A probe that can't distinguish "planner contributed zero anchors" from "subtopic path contributed anchors but primary fetch yielded zero" turns every triage session into a log-dive. Every future F/B2 investigation will hit this.

### Where to intervene

`src/lia_graph/pipeline_d/retriever_falkor.py:133-139` — the call site of `_diagnose_empty_primary`.

1. Pass both key tuples:
   ```python
   if not primary_articles:
       diagnostics.update(
           _diagnose_empty_primary(
               client=client,
               explicit_article_keys=explicit_article_keys,
               subtopic_article_keys=subtopic_article_keys,
           )
       )
   ```

2. Widen `_diagnose_empty_primary` (line 156) and replace lines 168-170 with:
   ```python
   if not explicit_article_keys and not subtopic_article_keys:
       probe["empty_reason"] = "no_anchors_resolved_anywhere"
       return probe
   if not explicit_article_keys and subtopic_article_keys:
       probe["empty_reason_precondition"] = "subtopic_anchors_only"
       probe["subtopic_key_count"] = len(subtopic_article_keys)
       # Continue into the graph-probe path with subtopic keys as the effective
       # anchor set — we DO want article_node_total + canonical/legacy match
       # probes to run so we can tell graph_not_seeded from schema_drift from
       # primary_fetch_zero_despite_canonical_matches in this case too.
       article_keys = subtopic_article_keys
   else:
       article_keys = explicit_article_keys
   ```

3. Update `_EMPTY_REASON_HINTS` in `orchestrator.py:313-338` to include `no_anchors_resolved_anywhere` with an operator-facing hint ("ni el planner ancló artículos explícitos ni el subtopic-intent resolvió anclas — workflow sin anchor registrado o consulta fuera de taxonomy").

4. Rename the old `no_explicit_article_keys_in_plan` to `no_anchors_resolved_anywhere` OR keep the old string as a deprecated alias for one release cycle. The latter is less disruptive — existing tests that assert the old reason string keep passing.

### Test gates

- `tests/test_retriever_cloud_contracts.py` already has cases for `no_explicit_article_keys_in_plan`. Add two new cases:
  - `subtopic_resolved_but_primary_fetch_empty`: mock `_retrieve_subtopic_bound_article_keys` to return 2 keys, mock `_retrieve_primary_articles` to return 0 items, assert the new distinguishing diagnostic fires (e.g. `empty_reason_precondition == "subtopic_anchors_only"` AND downstream `empty_reason` reflects the canonical/legacy probe outcome, not a false `no_explicit_article_keys_in_plan`).
  - `no_anchors_resolved_anywhere`: neither path resolves anything, assert the renamed reason fires.

### Effort / risk

**S**. One function signature change, one branch split, one hint table update, two tests. Risk is downstream string-matching on the old reason — grep confirms the only references are `tests/test_retriever_cloud_contracts.py` and the `_EMPTY_REASON_HINTS` table itself, both updated in this change.

---

# Part 2 — Complex fixes

These cross taxonomy curation scope or module contracts. Don't start them before Part 1 lands — the tooling (E) makes this work tractable, and the data fixes (A + C) close enough silent-misses that the returns on B and D become measurable.

## B. Taxonomy alias + coverage gap (label-speak vs query-speak)

### Symptom

`_detect_sub_topic_intent` (src/lia_graph/pipeline_d/planner_query_modes.py:58-111) scanned the entire 106-entry taxonomy for the DIAN-audit query and returned **zero** alias hits. Not one. Not because the subtopic wasn't there — `procedimiento_tributario.simplificacion_tramites_administrativos_y_tributarios` existed and semantically covered the query — but because its aliases were `guia_practica_procedimiento_tributario_dian`, `fiscalizacion_y_recursos_tributarios`, `codigo_de_procedimiento_administrativo`. Those are slugified **document titles**, not words an accountant would ever type into a chat.

The second investigation revealed a harder variant: for the query *"¿Qué resoluciones DIAN regulan su expedición electrónica y qué información mínima debe contener?"* there is no matching entry anywhere in the taxonomy. It isn't that the aliases are wrong — it's that no subtopic exists for "which regulatory instruments govern this + minimum-info requirements". This is a **taxonomy coverage** gap, not just an alias-style gap.

### Why it's general — two compounding sub-gaps

This isn't a single-subtopic curation oversight. Two distinct, compounding patterns:

**Sub-gap B1 — alias style (label-speak vs query-speak).** Spot-check the taxonomy:

- `devoluciones_y_compensaciones_de_saldos_a_favor.aliases` = `["compensacion_y_devoluciones_de_saldos_a_favor", "gestion_de_reteiva_y_saldos_a_favor", …]` — label reorderings of the key itself.
- `asistencia_administrativa_mutua_fiscal_internacional.aliases` = `["asistencia_administrativa_mutua_en_materia_fiscal"]` — one alias, same formal phrasing.
- `registro_unico_de_beneficiarios_finales.aliases` = `["marco_normativo_registro_unico_de_beneficiarios_finales"]` — prefix variant.

The curation pattern across the whole file is: take the document's formal title, slugify it, add two or three prefix variants. That produces aliases that match *corpus documents* but not *user queries*. Accountants don't type `guia_practica_procedimiento_tributario_dian`; they type `me llegó un requerimiento`, `tengo que contestar un pliego de cargos`, `me hicieron una liquidación oficial`.

**Sub-gap B2 — taxonomy coverage (from-corpus-forward vs from-queries-backward).** Even after B1 is fixed, facets without any subtopic entry remain unreachable. The Q2 in investigation (2) is the canonical example — `facturacion_electronica` has 4 subtopics (`factura_como_titulo_valor`, `reforma_tributaria_2003`, `cronograma_documentos_electronicos_dian`, `impuesto_de_timbre_y_papel_sellado`), none of which covers "which DIAN resolutions regulate DSE expedition and what minimum info they require". The taxonomy was built from the existing corpus forward — subtopics exist where documents exist — so any facet the corpus doesn't cover is also absent from the taxonomy. Queries asking about those facets hit 0 aliases no matter how rich the alias lists get.

### Where to intervene

1. **Sub-gap B1 fix — `config/subtopic_taxonomy.json`, every subtopic's `aliases` array.**
   The loader is `src/lia_graph/subtopic_taxonomy_loader.py`; `SubtopicEntry.all_surface_forms()` at lines 74-97 is what the classifier scans. Adding entries to `aliases` is the canonical extension point — the loader de-duplicates against `key` and `label`, so adding accountant-vernacular forms is safe and additive.

2. **A curator pass with this concrete question per subtopic:** *"What phrases would a working Colombian SMB accountant type to land on this subtopic?"* Examples of the vocabulary gap:

   | Subtopic key | Label-speak (current) | Query-speak (missing) |
   |---|---|---|
   | `simplificacion_tramites_administrativos_y_tributarios` | `guia_practica_procedimiento_tributario_dian` | `requerimiento`, `pliego_de_cargos`, `auto_de_archivo` (NOW ADDED by the narrow fix) |
   | `actualizacion_normativa_informacion_exogena` | `guia_practica_informacion_exogena` | `formato_1001`, `reportar_exogena`, `medios_magneticos` |
   | `agente_retenedor_bases_y_tarifas_de_retencion_en_la_fuente` | `tablas_y_calculo_de_retencion_en_la_fuente_2026` | `certificado_de_retencion`, `practicar_retencion`, `tarifa_minima_retencion` |
   | `implementacion_retencion_en_la_fuente_pyme` | `regulacion_de_retencion_en_la_fuente` | `exonerado_de_retencion`, `autorretenedor`, `base_minima_retencion` |

3. **Honor Invariant I1 (alias breadth).** The memory at `feedback_subtopic_aliases_breadth.md` is the explicit permission for this pass: *"wide alias lists in config/subtopic_taxonomy.json are intentional semantic-expansion fuel for retrieval; don't auto-tighten them."* Adding query-speak is the canonical breadth-expansion move — this pass is unblocked by policy.

4. **Sub-gap B2 fix — curator workflow addition.** The existing curation procedure (see `docs/next/subtopic_generationv1.md`) starts from the corpus. Add a reverse pass that starts from real queries. Concrete shape:

   - Sample N=100-200 queries from `logs/chat_verbose.jsonl` across the last quarter.
   - For each query, run it through `scripts/debug_query.py` (from item E) and flag any that produce `sub_topic_intent=None` despite having clear domain intent.
   - Group the flagged queries by domain/facet. Each cluster where no existing subtopic semantically covers the facet is a **new-subtopic candidate** — not an alias addition.
   - Feed those candidates into the existing curator-decisions workflow (`scripts/promote_subtopic_decisions.py`).

5. **Where *not* to edit.** Do not touch `label`. Labels are the human-readable display string used by the admin UI at `ui/assets/subtopicShell-*.js` (the admin review path). Mutating labels will churn the UI and break curator recognition.

### Test gates

- Extend `tests/test_planner_subtopic_intent.py` with a query-speak fixture: a dict of `{user_query_string: expected_subtopic_key}` grown from the 106-entry taxonomy. The fixture doubles as a curator-facing spec of what *should* route where.
- For B2: a separate fixture of known-uncovered queries with `expected_subtopic_key: None` — flipping any of these to a non-None value means a new subtopic has landed, and the test should force-update rather than silently pass.
- `tests/test_phase3_graph_planner_retrieval.py` has end-to-end smoke tests that call `run_pipeline_d(request)` — extend with a subtopic-diagnostic assertion for a curated set of queries.

### Effort / risk

**L**. Sub-gap B1 is per-subtopic curator judgment; 106 entries × ~10 aliases to add per entry ≈ ~1000 aliases. Cannot be automated safely — an LLM pass would re-introduce the label-speak bias unless prompted carefully. Sub-gap B2 requires real query logs and adds net-new taxonomy entries, which also adds corpus curation work (each new subtopic needs documents tagged to it to be useful). Best shape is a curator UI workflow that walks each subtopic, shows its current aliases + 3-5 candidate accountant phrases mined from real chat logs, and accepts/rejects — and surfaces uncovered-facet queries in a separate "propose new subtopic" queue. The win is recall across every future query — this is the single highest-leverage item in this backlog.

---

## D. Single-intent classifier + single-topic retrieval scope

### Symptom

`_detect_sub_topic_intent` (src/lia_graph/pipeline_d/planner_query_modes.py:58-111) returns `str | None` — one winning subtopic or nothing. The winner is chosen by greedy longest-alias-match, tiebroken lexicographically on the key (line 95: `matches.sort(key=lambda item: (-item[0], item[1]))`).

This is a latent cap for multi-facet queries. The original triggering query had three sub-questions that landed across different subtopic facets — `plazos` (procedural deadlines), `pruebas` (derecho probatorio), `ruta procesal` (sequence of DIAN actos administrativos). Even after the narrow fix made `simplificacion_tramites_administrativos_y_tributarios` win, the Supabase boost (`filter_subtopic` at `retriever_supabase.py:165-167`) and the Falkor anchor probe (`_retrieve_subtopic_bound_article_keys` at `retriever_falkor.py:66-70`) both steer retrieval toward **one** subtopic. Sub-questions that would benefit from evidence under a sibling subtopic (e.g. `regimen_sancionatorio` for Q2's pruebas admisibles) get starved.

The second investigation exposed a harder variant: Q1 belongs to `costos_deducciones_renta`, Q2 to `facturacion_electronica`. `resolve_chat_topic(whole_query)` picks one `effective_topic` (`costos_deducciones_renta`, via the subtopic override regex) and retrieval is scoped to it. Q2's evidence lives in a *different top-level topic's corpus*, which is never traversed. Multi-intent at subtopic level doesn't fix cross-topic sub-questions — the scope is wrong one level higher.

### Why it's general — two distinct sub-caps

Multi-question queries aren't rare — they're the standard shape of an accountant prompt. Every `¿…? ¿…? ¿…?` turn will face these caps as soon as the sub-questions span more than one subtopic (sub-cap D1) or more than one top-level topic (sub-cap D2). The memory at `feedback_multiquestion_answer_shape.md` explicitly commits to "one visible block per `¿…?` with unrestricted multi-bullets inside" — meaning the product promise is that each sub-question gets its own evidence-backed answer. The single-intent + single-topic stack breaks that promise structurally, not accidentally.

**Sub-cap D1 — single-intent subtopic classifier.** Within one top-level topic, the classifier emits one `sub_topic_intent`. Multi-facet sub-questions get starved.

**Sub-cap D2 — single-topic retrieval scope.** Across top-level topics, the planner emits one `effective_topic` that the retriever scopes to. Cross-topic sub-questions never see the other topic's corpus. `TopicRoutingResult` (src/lia_graph/topic_router.py:205-229) already has a `secondary_topics: tuple[str, ...]` field — it's populated by `_normalize_secondary_topics` (lines 242-262) and survives through to `to_dict`, but it's currently only used as a fallback hint for downstream display; it does not feed retrieval fan-out.

### Where to intervene

This is the biggest design change in this backlog — it touches the planner contract, both retrievers, the diagnostics schema, topic routing, and tests. Trace in two phases (D1 first, D2 second):

**Phase D1 — multi-intent subtopic classifier (within one topic).**

1. **Contract change — `src/lia_graph/pipeline_d/contracts.py:107`**
   ```python
   sub_topic_intent: str | None = None
   # becomes
   sub_topic_intents: tuple[str, ...] = ()
   ```
   And at `contracts.py:119`, the `to_dict` emits a list.

2. **Classifier change — `src/lia_graph/pipeline_d/planner_query_modes.py:58-111`**
   Return type becomes `tuple[str, ...]`. The greedy single-winner block (lines 83-111) becomes: for each sub-question emitted by `_extract_user_sub_questions` (already called in planner.py:423), run the same alias scan; union the top-1 result per sub-question. Final return is the de-duplicated tuple. Fall back to the single-winner behavior when there's only one sub-question.

3. **Call site — `src/lia_graph/pipeline_d/planner.py:425-442`**
   Pass `sub_questions` (already available at line 423) into `_detect_intent`. Update the `GraphRetrievalPlan` construction at line 442.

4. **Falkor retriever — `src/lia_graph/pipeline_d/retriever_falkor.py:63-131`**
   Replace single-key probe at lines 66-70 with a loop that unions `_retrieve_subtopic_bound_article_keys` across all intents. Preserve `primary_article_limit` by dividing the budget evenly across intents (floor 1). Rename diagnostic field at line 130 from `retrieval_sub_topic_intent` to `retrieval_sub_topic_intents` (list).

5. **Supabase retriever — `src/lia_graph/pipeline_d/retriever_supabase.py:88, 148-187`**
   The RPC accepts a single `filter_subtopic` today. Either (a) extend the RPC server-side to accept `filter_subtopics` (list) + `subtopic_boosts` (list-parallel floats), or (b) run the RPC N times and union results client-side. (b) is the cheaper landing — no DB migration, retries still work. `_apply_client_side_subtopic_boost` at lines 206-249 already handles post-sort boosting; extend it to check `subtema in sub_topic_intents` instead of scalar equality.

6. **Diagnostics propagation.** `response.diagnostics["retrieval_sub_topic_intent"]` is the contract the `chat-response-architecture.md` guide documents (line 64). Bump to plural everywhere, update `docs/orchestration/orchestration.md` at the env-matrix version row (currently `v2026-04-21-stv2d` — bump to `-stv3`), and document the field rename in the change log section.

**Phase D2 — multi-topic retrieval scope (across topics).**

7. **Per-sub-question top-level topic classification — `src/lia_graph/pipeline_d/planner.py` (new seam).**
   Today the planner calls `resolve_chat_topic` once, on the whole message. Add a per-sub-question pass: for each `¿…?` split, run `resolve_chat_topic` again and collect distinct `effective_topic` values. Union them with the whole-query result. This catches the case where Q2 alone would have resolved to `facturacion_electronica` even though the whole query resolved to `costos_deducciones_renta`.

8. **Wire `secondary_topics` into retrieval scope.**
   `GraphRetrievalPlan.topic_hints` (contracts.py:102) already exists and flows to both retrievers. Instead of inventing a new field, extend the planner to merge per-sub-question topics into `topic_hints`. Then in `retriever_supabase.py:_build_query_text` (line 106-120), the topic hints are already included in the RPC query text — but more importantly, the classifier/anchor pipeline needs a *retrieval* hook, not just a query-text one. Add a `secondary_topic_probe` in `retriever_falkor.py` that runs a narrower anchor probe for each secondary topic, same shape as the subtopic anchor probe already does.

9. **Supabase scope.** `hybrid_search` RPC currently takes `filter_topic: None` (retriever_supabase.py:149) — the comment at lines 136-141 documents that topic is deliberately *not* a WHERE predicate. Don't change that. Instead: extend the caller to pass the full topic set (primary + secondaries) as additional `query_text` tokens, so FTS ranking surfaces chunks from secondary topics without excluding the primary.

10. **Diagnostics addition.** Add `retrieval_effective_topics: list[str]` alongside `retrieval_sub_topic_intents`, carrying primary + all secondaries. Observable failure mode: the list is length-1 → single-topic retrieval happened → expected for simple queries, flagged for investigation for multi-question ones.

### Test gates

- **D1:** split `tests/test_planner_subtopic_intent.py` into (a) single-sub-question behavior (existing cases keep passing, `intents` is 1-tuple), (b) multi-sub-question behavior (new cases: a tri-facet query should emit three subtopic keys in `intents`).
- **D2:** new test `tests/test_planner_cross_topic_routing.py` — fixture of queries where Q1 and Q2 belong to different top-level topics, assert `retrieval_effective_topics` has length ≥ 2.
- End-to-end in `tests/test_phase3_graph_planner_retrieval.py`: assert that Q2 of a multi-facet cross-topic query gets evidence from its own topic+subtopic, not from the dominant Q1 pool.

### Effort / risk

**L-to-XL**. D1 alone is M-to-L (contract + two retrievers + diagnostics rename + tests). D2 is the bigger change: per-sub-question topic classification is a new planner seam, secondary-topic retrieval fan-out touches both retrievers, and the Supabase RPC query-text path has subtle interactions with `_build_fts_or_query` (retriever_supabase.py:178-199) that need careful rework. Do A, B, and C first: they fix the *data* so multi-intent + multi-topic have something to be intelligent over. Multi-intent on top of thin alias sets just fans out the same misses across more queries.

---

## H. Corpus content curation — the Normativa / Expertos / Práctica three-family model

### Symptom

Every item in this backlog so far treats the failure mode as a *data-routing, retrieval, or classifier* problem: the planner didn't anchor (F), the taxonomy missed a facet (B2), the topic didn't route (C). Beneath those is a harder failure that no code change can fix: **the corpus does not contain the document the answer needs, in any form.** Audit of the DIAN-procedure subdomain (2026-04-22) surfaced this concretely — the Estatuto Tributario Libro V articles are essentially all ingested as `ArticleNode` (41/44 article groups, 93%), but the operational documents that turn those articles into *something an accountant can execute* (how to draft a response to a requerimiento, what evidence attaches to which article, how the case escalates from DIAN to Consejo de Estado if needed) are almost entirely absent. A `grep` of `knowledge_base/` for `PROCEDIMIENTO` / `procedimiento-tributario` / `fiscalizacion-dian` finds **one** document covering DIAN procedure: `PRO-L01-guia-practica-recurso-sancion-no-presentar-exogena.md` — a narrow guide for a single exógena sanction. Nothing on the main workflows.

The answer shape this produces: correct citations with no executable path. Q1 of the DIAN-audit query got arts. 703 ET (term) and 742 ET (admissible evidence) — accurate. Q3 ("ruta procesal si escala a requerimiento especial y luego a liquidación oficial") got `Cobertura pendiente` because no document walks that sequence end-to-end. The synthesis layer cannot fabricate content that was never ingested.

### Why it's general — the three-family corpus model

The `knowledge_base/` layout encodes a three-family mental model, and the assignment happens **at corpus-creation time** (during ingest), not at retrieval time. A document's family is a load-bearing field set by the ingestion pipeline and persisted in `canonical_corpus_manifest.json`. Before diagnosing gaps, it is important to read that classification precisely because the naming across the stack is inconsistent: the *folder* a document lives in, the *family* the manifest records, the *source_tier* the ingestion pipeline assigns, and the *product surface* the UI exposes all use related-but-not-identical names. The mismatch is historical, not intentional — but curators and future Claude instances working on corpus additions must know which name is authoritative where.

**The four naming axes, per family:**

| Axis (and where it lives) | Family 1 | Family 2 | Family 3 |
|---|---|---|---|
| `family` (authoritative field in `canonical_corpus_manifest.json`) | `normativa` | `interpretacion` | `practica` |
| `knowledge_class` (paired in manifest) | `normative_base` | `interpretative_guidance` | `practica_erp` |
| `source_tier` (paired in manifest — a parallel ingestion-origin axis) | `normativo` | `expertos` | `loggro` |
| Folder under `knowledge_base/<area>/<TOPIC>/` | `NORMATIVA/` | `EXPERTOS/` | `LOGGRO/` (legacy) or `PRACTICA/` (newer) |
| File prefix convention | `N01-` | `E01-` | `L01-`, `L02-`, ... |
| Product-surface name | `Normativa` (CLAUDE.md + UI) | `Interpretación` in code (`src/lia_graph/interpretacion/`, per CLAUDE.md) / `Expertos` in the chat sidebar panel | not exposed as a dedicated surface — feeds `main chat` |

**Authoritative field is `family`.** Retrieval weighting, graph tagging, and the `Normativa` / Expertos / (future) `Interpretación` surface splits all read off `family`. The folder name `EXPERTOS/` is curator-ergonomic — humans write `EXPERTOS` in a path, but the ingest pipeline transcodes that into `family: "interpretacion"`. Source_tier (`expertos`) is a parallel axis used for authority weighting, not family assignment. When writing this document we keep the human-readable family labels (Normativa / Expertos / Práctica) because accountants and curators speak that dialect, but every code reference and manifest field must use the `family` values.

**There is a fourth cohort — `family: "unknown"` — which is NOT a fourth family, it is pending-review triage.** The manifest carries 5 entries (all formulario PDFs under `knowledge_base/form_guides/`) with `family: "unknown"`, `knowledge_class: "unknown"`, `source_tier: "unknown"`, `ambiguity_flags: ["family_unknown", "knowledge_class_unknown", "source_type_unknown"]`, `review_priority: "critical"`, `needs_manual_review: true`, `canonical_blessing_status: "blocked"`. These are documents admitted to the corpus but not yet classified by a curator; the ingest pipeline refuses to bless them canonical until a human assigns a family. Treat the `unknown` cohort as a curation backlog, not a design choice.

---

**Family 1 — NORMATIVA** (manifest: `family: "normativa"`, `knowledge_class: "normative_base"`, `source_tier: "normativo"` or `"official_compilation"` or `"suin_harvest"` depending on ingestion origin, `authority_level: "primary_official_authority"`; folder `NORMATIVA/`, prefix `N01-`).

The *what does the law say* layer. Marco-legal compilations: articles of the ET by Libro, Decretos Únicos Reglamentarios (esp. Decreto 1625/2016 para materia tributaria, Decreto 1072/2015 para laboral), Resoluciones DIAN vigentes, leyes y reformas (esp. Ley 2277/2022), CPACA (Ley 1437/2011), CGP (Ley 1564/2012). This is the *citable evidence* that synthesis renders as `(art. 703 ET)`. Current corpus state: **strong for substantive tax** (`RENTA/NORMATIVA/regulacion-FE-compilada.md`, `GMF_4X1000/NORMATIVA/GMF-N01-marco-legal-GMF-cuentas-exentas-art-879-ET.md`, `REFORMA_LABORAL_LEY_2466/NORMATIVA/REF-N01-*`), **thin for procedural/contentious law** (CPACA a 26 artículos fragmentados, CGP a 10, ningún marco compilado de procedimiento tributario). Note that many NORMATIVA entries do not come from hand-curated `N01-` files at all — the SUIN-harvest ingestion path writes `family: "normativa"` with `source_tier: "suin_harvest"` for every ET / law / decree article auto-parsed from official sources (`src/lia_graph/ingestion/suin/bridge.py`). Both the curated compilations and the auto-harvested primary articles share the `normativa` family at retrieval time.

**Family 2 — EXPERTOS / INTERPRETACIÓN** (manifest: `family: "interpretacion"`, `knowledge_class: "interpretative_guidance"`, `source_tier: "expertos"`, `authority_level: "secondary_official_authority"`; folder `EXPERTOS/`, prefix `E01-`, surface name `Expertos` in chat sidebar or `Interpretación` in CLAUDE.md / `src/lia_graph/interpretacion/`).

The *how specialists read the law* layer. Interpretations-for-practitioners: how a tax advisor resolves ambiguity in the normativa, which DIAN Conceptos are binding vs. superseded, consolidated Consejo de Estado Sección Cuarta jurisprudence lines, open doctrinal debates curated for practitioners. Distinct from NORMATIVA because it carries *judgment* — which reading wins when the law is silent, which Concepto DIAN to cite, which tesis jurisprudencial está consolidada. Current corpus state: **present for complex substantive topics** (`CAM_DECLARACION_CAMBIO/EXPERTOS/CAM-E01-*`, `SOC_OBLIGACIONES_ANUALES/EXPERTOS/SOC-E04-*`, `BEN_BENEFICIARIOS_FINALES/EXPERTOS/BEN-E01-*`, `REFORMA_LABORAL_LEY_2466/EXPERTOS/REF-E01-*`), **absent for procedural workflows** despite 891 raw DIAN conceptos and 617 raw Consejo de Estado decisions sitting in the base corpus as uncurated `normativa`-family articles (the raw primary sources are family=normativa; the digest-style curation would land as family=interpretacion). Those primary sources are individually retrievable but no digest tells the accountant which line is consolidated and which is superseded. The gap is not raw material — it is curated interpretation.

**Family 3 — PRÁCTICA** (manifest: `family: "practica"`, `knowledge_class: "practica_erp"`, `source_tier: "loggro"`, authority tier operational; folder `LOGGRO/` historically or `PRACTICA/` in newer curation, prefix `L01-` / `L02-` / ... for multiple practical docs per subdomain).

The *how I actually do this on Monday morning* layer. Guías operativas: step-by-step procedures, checklists, worked examples, templates in code blocks, decision trees, MUISCA / PILA / prevalidador screen walkthroughs. Distinct from EXPERTOS because it's action-oriented — not "what does the law mean" but "what do I type, where do I click, what do I attach, in what order". Current corpus state: **present for high-traffic operational workflows** (`FACTURACION_ELECTRONICA_OPERATIVA/LOGGRO/FE-L01-guia-practica-facturacion-electronica-operativa-2026.md`, `INFORMACION_EXOGENA_2026/LOGGRO/EXO-L01-guia-practica-exogena-AG2025-formatos-prevalidador-plazos.md`, `GMF_4X1000/LOGGRO/GMF-L01-guia-practica-GMF-cuentas-exentas-flujo-caja-PYME.md`, `TRABAJO_TIEMPO_PARCIAL/LOGGRO/TPR-L02-*`), **absent for procedural/defensive workflows** (one PRO-L01 on a niche exógena sanction; nothing else). The `LOGGRO/` → `PRACTICA/` folder rename is in-progress; both point to the same `family: "practica"` at ingest — do not assume a document under `LOGGRO/` is a different family from one under `PRACTICA/`.

**The ratio pattern.** A subdomain is *operationally answerable* by Lia when at least one document exists per family for it. Subdomains missing one family are only partially answerable:

- missing NORMATIVA → synthesis has no article anchors, falls back to LLM priors (risk of unfaithful citations);
- missing EXPERTOS → synthesis can cite but cannot adjudicate between conflicting primary sources or flag when a Concepto DIAN está superado;
- missing PRÁCTICA → synthesis can explain the law but cannot tell the accountant what to DO.

The DIAN-procedure subdomain is the most asymmetric case in the corpus today: ~100% NORMATIVA (via raw ET articles) but 0% EXPERTOS digests and ~0% PRÁCTICA guides. This is why the narrow fixes of investigation (1) plus F plus G cannot fully close the DIAN-audit banner — the *articles* are there, the *routing to them* is being fixed, but the *executable guidance that wraps them* was never written.

### The gap in concrete terms — DIAN procedure as the canonical case

Using DIAN procedure as the template for diagnosing a three-family gap:

**What exists today.**
- `NORMATIVA` (procedimiento-specific): none compiled; implicit via parsed ET Libro V articles + fragmentary CPACA/CGP ingestion.
- `EXPERTOS` (procedimiento-specific): zero digests despite heavy raw-source coverage (891 DIAN conceptos, 617 Consejo de Estado decisions uncurated).
- `PRÁCTICA`: one narrow document (PRO-L01 on sanción exógena) out of the full procedural domain.

**Proposed curation slate — five documents, three families.**

| # | Family | Proposed document | Purpose | Anchor articles supported |
|---|---|---|---|---|
| 1 | NORMATIVA | `PRO-N01-marco-legal-procedimiento-tributario-ET-Libro-V.md` | Compiled marco legal: ET Libro V structured by fase procesal, CPACA artículos pertinentes a impugnación de actos administrativos tributarios (138 nulidad y restablecimiento, 137 simple nulidad, 161 medidas cautelares, 243-253 recurso extraordinario de revisión), CGP medios de prueba (164-278) incorporated by reference from art. 742 ET, Decreto 1625/2016 reglamentación procedimental. | 685, 703-714, 720-730, 742-752 ET; CPACA 137, 138, 161, 243-253; CGP 164-278 |
| 2 | EXPERTOS | `PRO-E01-interpretaciones-procedimiento-tributario-dian-consejo-estado.md` | Curated digest: qué líneas de Consejo de Estado Sección Cuarta están consolidadas (caducidad 4 meses, tesis sobre ineptitud de la demanda, carga probatoria en materia tributaria, presunción de veracidad del art. 746 ET); qué Conceptos DIAN sobre procedimiento vigentes vs derogados; debates abiertos sobre prueba indiciaria; criterios sobre indebida notificación y nulidad de actos. | Same ET articles + DIAN Conceptos curated + Sección Cuarta sentencias curated |
| 3 | PRÁCTICA | `PRO-L02-guia-practica-respuesta-requerimiento-ordinario.md` | Step-by-step: recibí un requerimiento ordinario → cómo leo el objeto del requerimiento → preparación del paquete probatorio por tipo de diferencia (diferencias en exógena/retenciones, inconsistencias en costos, rechazos de IVA descontable, diferencias en pasivos) → estructura del escrito de respuesta → radicación → qué esperar después. Include templates en code blocks. | 684, 685, 742, 744, 746 ET |
| 4 | PRÁCTICA | `PRO-L03-guia-practica-respuesta-requerimiento-especial-y-liquidacion-oficial.md` | La ruta escalada: recibí un requerimiento especial → término ampliado del art. 707 → preparación de la respuesta → expedición de liquidación oficial de revisión del art. 712 → elementos del acto administrativo → cuándo es anulable y por qué. | 703-714 ET |
| 5 | PRÁCTICA | `PRO-L04-guia-practica-via-gubernativa-y-contenciosa-recurso-demanda.md` | La ruta defensiva completa: recurso de reconsideración ante la DIAN (art. 720) → agotamiento de vía gubernativa → demanda de nulidad y restablecimiento ante Consejo de Estado (art. 138 CPACA, caducidad de 4 meses desde notificación) → medidas cautelares → recursos extraordinarios de revisión. This is the single most-missing piece: zero corpus content today on the transition from administrativa to contenciosa. | 720-730 ET; CPACA 137, 138, 161, 243-253 |

**The general pattern, beyond DIAN procedure.** For each top-level topic in `get_supported_topics()`, run a three-family census against `canonical_corpus_manifest.json`. Subdomains likely to surface as three-family asymmetric based on memory cues (`project_lia_scope_labor.md`, `project_lia_payroll_advisor_role.md`):

- **UGPP fiscalización** — likely 0 NORMATIVA, 0 EXPERTOS, 0 PRÁCTICA despite being an existential risk for PYMEs.
- **PILA y aportes a seguridad social (operación mensual)** — substantive law present, PRÁCTICA thin despite being daily.
- **Precios de transferencia (declaración, estudio, documentación)** — EXPERTOS likely thin; PRÁCTICA for SMB sub-threshold cases likely absent.
- **Corrección voluntaria de declaraciones** — substantive NORMATIVA via arts. 588-589 ET present; EXPERTOS digest absent; PRÁCTICA absent.
- **Devolución de saldos a favor (trámite completo)** — NORMATIVA via arts. 850-862 ET; EXPERTOS fragmentary; PRÁCTICA absent.
- **Beneficiario Final RUB actualizaciones y sanciones** — has EXPERTOS and PRÁCTICA foundational, but procedural/sanctions mechanics thin.

Every one of these deserves the same five-document treatment as DIAN procedure, tailored per subdomain.

### Where to intervene

1. **Build the three-family census tool.** New `scripts/corpus_family_census.py` — parallel to E's `scripts/debug_query.py`. Reads `artifacts/canonical_corpus_manifest.json`, emits a `topic × {normativa, expertos, practica}` count matrix as JSON + Markdown table. Flag any `(topic, family)` cell at zero. Also emit a `topic × subtopic × family` variant for finer-grained auditing once B2 lands. Ship with a Makefile target `make corpus-family-census`.

2. **Write the curator reference guide once.** New `docs/guide/corpus_curation_families.md` — the writing counterpart of E's investigator tool. Documents for each family:
   - Role and authority tier.
   - Document shape: structure, length, citation density, voice (expository / interpretive / imperative).
   - Prefix conventions (`N01-`, `E01-`, `L01-/L02-` for multi-práctica per subdomain).
   - Subtopic tagging expectations (NORMATIVA tags by article range; EXPERTOS tags by interpretive controversy; PRÁCTICA tags by workflow name — these map cleanly onto B2's first-class subtopic keys).
   - A template skeleton per family with required sections.
   - An anti-pattern catalog: LLM-drafted PRÁCTICA without expert review, EXPERTOS that just paraphrases NORMATIVA instead of adjudicating, NORMATIVA that is just concatenated article text without structure.

3. **Open a curation bucket per three-family-asymmetric subdomain.** Start with DIAN procedure as the canonical case: create `knowledge_base/to upload/PROCEDIMIENTO_TRIBUTARIO/{NORMATIVA,EXPERTOS,PRACTICA}/` with the five slot filenames above pre-committed as empty placeholders. Doing this makes the backlog visible to curators without requiring the engineering team to track per-document. Repeat the pattern for UGPP, PILA, precios de transferencia, corrección voluntaria, devolución saldos, RUB actualizaciones.

4. **Coordinate landing with B2.** A curated PRÁCTICA document on "respuesta a requerimiento ordinario" is dramatically more retrievable if `requerimiento_ordinario` is a first-class subtopic with HAS_SUBTOPIC edges to the relevant ArticleNodes, versus being buried as an alias of `simplificacion_tramites_administrativos_y_tributarios`. H benefits from B2 landing but does not strictly depend on it — curators can write drafts against the current taxonomy and re-tag when B2 promotes keys. Sequence: start curator drafts in parallel with B2; merge both changes together in a single re-ingestion pass.

5. **Wire through the existing ingest/graph pipelines.** Once documents land, `make phase2-graph-artifacts` + `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` ingests them with no code changes required. Verify each document's manifest row has correct `family`, `source_tier`, `topic_primary`, `subtopic_assignments`.

6. **Do not over-fragment up front.** Write one document per family per subdomain first. Split only after real queries reveal the chunking boundary — Supabase retrieval operates at chunk level, Falkor at article level, and the right granularity is "one answer's worth of context per chunk," which is clearer after-the-fact than in advance.

### Documentos por arreglar — cohort `family: "unknown"`

Separate from the "add more curated documents" problem (everything above) is the "fix the documents that are already admitted but stuck" problem. Today the manifest carries exactly **5 entries** in this state. All five share the same signals:

```json
"family": "unknown",
"knowledge_class": "unknown",
"source_type": "unknown",
"source_tier": "unknown",
"authority_level": "authority_unknown",
"ambiguity_flags": ["family_unknown", "knowledge_class_unknown", "source_type_unknown"],
"review_priority": "critical",
"needs_manual_review": true,
"canonical_blessing_status": "blocked",
"graph_target": false,
"graph_parse_ready": false,
"canonical_ready": false
```

`canonical_blessing_status: "blocked"` is the consequence — these documents are admitted to the corpus inventory but held out of retrieval until a curator classifies them. Every other document in the manifest is `canonical_blessing_status: "ready"`.

**The five documents.** All formularios PDF under `knowledge_base/form_guides/`:

| # | Path | What it is | Extra flags |
|---|---|---|---|
| 1 | `form_guides/formulario_110/pj_ordinario/assets/formulario_110_2025_oficial.pdf` | Formulario 110 — Declaración de renta y complementarios PJ ordinario | — |
| 2 | `form_guides/formulario_115/pes_general/assets/formulario_115_2025_oficial.pdf` | Formulario 115 — Declaración informativa de precios de transferencia / pagos al exterior | also `vocabulary_unassigned` |
| 3 | `form_guides/formulario_210/pn_residente/assets/formulario_210_2025_oficial.pdf` | Formulario 210 — Declaración de renta PN residente | — |
| 4 | `form_guides/formulario_2517/pn_residente/assets/formato_2517_v6_guia_prevalidador.pdf` | Formato 2517 v6 — Guía de prevalidador | — |
| 5 | `form_guides/formulario_260/rst_general/assets/formulario_260_2025_oficial.pdf` | Formulario 260 — Declaración Régimen Simple de Tributación | — |

**Why they're stuck.** Every one has `text_extractable: false` and `parse_strategy: "binary_inventory_only"`. The ingest pipeline admitted the PDF as an inventory entry but could not read its content, so there was no text for the auto-classifier to read, so `family` / `knowledge_class` / `source_type` could not be assigned. The pipeline is doing the honest thing — refusing to guess — and blocking canonical blessing until a human decides.

**Why this matters.** These are not fringe documents. Formularios 110 / 210 / 260 are the three anchor declaration forms (renta PJ ordinario, renta PN residente, Régimen Simple). 115 covers precios de transferencia. 2517 is the prevalidador guide. Every SMB accountant will eventually ask Lia a question where evidence from one of these forms would strengthen the answer, and today those forms are held out of retrieval entirely.

**Three fix paths, per document.**

1. **Text-extract-then-reclassify.** Run OCR or a PDF text-extraction pass (formularios DIAN are born-digital PDFs with selectable text in most years — OCR quality should be high). Once text lands, the auto-classifier can assign `family: "normativa"` (if the form is reproduced verbatim as a reference doc) or `family: "practica"` (if it is wrapped in a how-to-fill-it guide). Feasible for formularios 110 / 210 / 260 / 2517. This path is engineer-work (extraction tooling) plus light curator-work (sanity-check the auto-assignment).

2. **Replace-with-guide.** The forms themselves are mostly blank templates. What an accountant needs is the *instructions* for filling them. The `form_guides/` subtree already contains partial `structured_guide.json` and `interactive_map.json` artifacts for formularios 110 / 260 / 2517 (visible in `knowledge_base/form_guides/formulario_110/pj_ordinario/`, `knowledge_base/form_guides/formulario_260/rst_general/`, etc.). Decision: if the structured guides fully cover what a chat query would need, the raw form PDF is dead weight — remove the manifest entry and let the `structured_guide.json` carry the load. Curator-work.

3. **Manual curator classification.** If neither (1) nor (2) fits, a human assigns `family` + `knowledge_class` + `source_type` + `subtopic_key` directly in a classifier-override config. Cheapest per document but does not scale and creates divergence between folder conventions and assignments. Last resort.

**Recommended decision per document.** Run (1) on 110 / 210 / 260 / 2517 — the ingest can handle born-digital tax forms. For 115 (precios de transferencia, also flagged `vocabulary_unassigned` beyond the family issue), decide between (1) + a new `precios_de_transferencia` subtopic vocabulary (intersects with SEENOW item C — this top-level topic is among the 40+ unregistered — and B2 — no subtopic coverage) or (2) if a PT-specific practical guide already exists in the curation backlog. For any of the five, (3) is the fallback only if both (1) and (2) fail.

**Ongoing hygiene, not one-shot cleanup.** The `family: "unknown"` cohort is not a five-item backlog that closes and stays closed. Any future document admitted to the corpus that the auto-classifier cannot read — unreadable PDFs, malformed markdown, non-UTF-8 encodings, files placed outside the `N01-/E01-/L01-` folder convention — will surface with the same flag set. The ongoing job is to keep the cohort at ≈0 by triaging new additions as they appear.

**Extend the census tool to surface this backlog.** `scripts/corpus_family_census.py` (proposed in "Where to intervene" above) should emit a second section alongside the `topic × family` matrix: a `por_arreglar` list containing every manifest entry with any of `family == "unknown"`, `canonical_blessing_status == "blocked"`, `needs_manual_review == true`, or non-empty `ambiguity_flags`. Operators then get both the curation gaps (need new documents) and the hygiene gaps (need stuck documents unstuck) in one report.

**Relationship to SEENOW items.** This sub-section intersects with:
- **C** (40+ unregistered topics): formulario 115's `vocabulary_unassigned` flag is an instance of an unregistered topic (precios de transferencia) blocking a specific document.
- **B2** (taxonomy coverage): if a freed formulario needs a subtopic assignment that does not exist yet, B2 has to land first (or in parallel) to give it somewhere to map.
- **H proper**: the five stuck formularios are orthogonal to the five proposed DIAN-procedure documents — one backlog is *undelivered new content*, the other is *admitted-but-broken content*. Both need to be closed for the corpus to be operationally complete; neither substitutes for the other.

### Acceptance / verification

A curated document counts as *landed and operational* when all four conditions hold:

1. It exists in `knowledge_base/<area>/<TOPIC>/{NORMATIVA|EXPERTOS|PRACTICA}/` following the N01/E01/L0x prefix convention.
2. `make phase2-graph-artifacts` ingests it without errors and the manifest entry carries the correct `family`, `source_tier`, `topic_primary`, and `subtopic_assignments`.
3. A diagnostic query via `scripts/debug_query.py` (item E) that targets the covered workflow returns the document as a retrieved chunk with nonzero rank score.
4. An end-to-end query through `run_pipeline_d` returns an answer whose `evidence_snippets` include text from the document, and whose `retrieval_health.primary_article_count > 0`.

(4) is the real acceptance criterion — ingestion without retrieval is vanity coverage. Add one smoke test per landed document in `tests/test_phase3_graph_planner_retrieval.py` asserting (4).

### Effort / risk

**L — mostly curator-time, not engineer-time.** The engineering pieces are small: the census script (S), the curation guide (S), ingest pipelines are already wired. The curator work is the bulk: five documents for DIAN procedure alone is ~2-3 weeks of a specialist's time for quality output, and DIAN procedure is one of ~10-15 identified asymmetric subdomains.

The risk profile is inverse to code changes: no regressions possible (ingestion is additive, never removes or mutates existing content), but the quality of answers is bounded entirely by the quality of the curator. **An LLM-drafted PRÁCTICA or EXPERTOS document without expert review is worse than no document**, because the synthesis layer will cite it authoritatively while being wrong — unlike `Cobertura pendiente`, which is at least honest about the gap. Workflow gate: every new NORMATIVA / EXPERTOS / PRÁCTICA document requires sign-off from a domain specialist before `make phase2-graph-artifacts-supabase` lands it in staging.

The economics still make H the highest-ROI item in this backlog: unlike A-G which improve *retrieval fidelity over existing content*, H improves *the content itself*, and every retrieval, routing, and synthesis step downstream benefits proportionally from richer source material. The single-corpus-improvement-multiplies-everything property is why H belongs alongside B in Part 2 rather than at a separate tier.

---

# Recommended order

The order below assumes you care about *recall impact per unit of effort*, not chronological convenience.

**Part 1 — do first unconditionally.**

1. **E (tooling)** — S effort, S risk. Unlocks faster iteration on everything else.
2. **F (planner procedural anchors)** — S effort. Directly closes the `no_explicit_article_keys_in_plan` banner for the DIAN-audit subdomain and every adjacent workflow with a deterministic article set. Independent of routing work; fires only when the detector is already known-good. Requires the detector split described in F's "Where to intervene" before wiring — otherwise voluntary-correction queries get DIAN-audit anchors.
3. **G (diagnostic probe fidelity)** — S effort. Disambiguates the partial-coverage banner so future triage (including F's test surface and B2's) can tell "planner didn't anchor" from "subtopic anchored but primary fetch came back empty". Do alongside F — the two compose: F closes the planner-anchor gap for the workflows it covers, G makes the residual gaps (subtopic-only paths, graph-seeding mismatches) legible instead of silent.
4. **C (empty / incomplete topic keywords)** — M effort. Independent of A; the boot-time invariant log (step 2 of C) is a one-liner that surfaces future regressions automatically. The facet-completeness audit (step 4) depends on E being available.
5. **A (weak-list polysemy audit)** — M effort. Mostly mechanical once the rule is named and adversarial tests exist. Fixes a whole class of silent mis-routings.

**Part 2 — do after Part 1 has landed.**

6. **B (alias style + coverage)** — L effort. Highest single *recall* win against the existing corpus. Sub-gap B1 (alias style) is faster and can start in parallel with B2 (coverage gap requires query-log mining and new subtopics). Cannot be skipped even if D is done — D multiplies misses when the alias data is thin.
7. **H (corpus content curation — Normativa/Expertos/Práctica)** — L effort, curator-dominated. Highest single *answer-quality* win because it improves the source material every downstream layer reads. Runs in parallel with B — B2 and H share the same subdomain-curation cadence and benefit from being landed together in one re-ingestion pass. Start DIAN procedure as the canonical case (five documents across three families), then extend to UGPP, PILA, precios de transferencia, corrección voluntaria, devolución saldos, RUB actualizaciones.
8. **D (multi-intent classifier + multi-topic scope)** — L-to-XL effort. **Do last.** Phase D1 (multi-intent within a topic) first, Phase D2 (multi-topic fan-out across topics) second. Both phases amplify the data gains from A/B/C/F/G/H; neither rescues a query whose evidence was never curated (B/H) or never anchored (F) in the first place. Doing D on a thin corpus just fans out the same misses across more queries.

---

## Change log

| Version | Date | Notes |
|---|---|---|
| v1 | 2026-04-21 | Initial catalog. Written after the `requerimiento ordinario` / `liquidación` investigation that landed narrow fixes in `topic_router_keywords.py` and `subtopic_taxonomy.json`. |
| v2 | 2026-04-21 | Restructured into Part 1 (easier fixes — E, C, A) and Part 2 (complex fixes — B, D). Folded in two sub-points from the `documento soporte de pago` investigation: B gained sub-gap B2 (taxonomy coverage — facets with no subtopic entry at all); D gained sub-cap D2 (single-topic retrieval scope — cross-topic multi-question queries never see secondary topics' corpora). C picked up the "incomplete-facet" variant from Q2 scoring 0 on `facturacion_electronica`. |
| v3 | 2026-04-22 | Added F (planner procedural-workflow anchor gap) and G (retriever diagnostic probe fidelity) to Part 1 after tracing a DIAN-audit query on 2026-04-22 that still surfaced `empty_reason=no_explicit_article_keys_in_plan` despite investigation (1)'s narrow fixes having landed. Root cause: those narrow fixes addressed *routing* (`topic_router_keywords.py` + `subtopic_taxonomy.json` aliases) but not *planner article anchoring* — the two detectors that inject explicit article keys today (`_looks_like_tax_planning_case`, `_looks_like_loss_compensation_case`) cover a narrow slice of the workflows that have deterministic article sets. F adds the missing anchor path; G is the companion probe-fidelity fix so future triage can distinguish planner-no-anchor from subtopic-anchored-but-fetch-empty. Recommended order updated accordingly (E → F → G → C → A → B → D). |
| v4 | 2026-04-22 | Added H (corpus content curation — the Normativa / Expertos / Práctica three-family model) to Part 2 after a corpus-coverage audit on 2026-04-22 revealed that the DIAN-procedure subdomain has ~100% NORMATIVA coverage via raw ET articles but zero curated EXPERTOS digests and essentially zero PRÁCTICA guides — the most three-family-asymmetric subdomain in the corpus. H names the general pattern (every subdomain's operational answerability depends on having at least one document per family), proposes the DIAN-procedure curation slate as the canonical case (five documents across NORMATIVA / EXPERTOS / PRÁCTICA), and extends the diagnosis to UGPP, PILA, precios de transferencia, corrección voluntaria, devolución saldos, and RUB actualizaciones. Introduces `scripts/corpus_family_census.py` as the standing three-family diagnostic and `docs/guide/corpus_curation_families.md` as the curator-facing writing guide. Recommended order updated to E → F → G → C → A → B ∥ H → D; B and H run in parallel because they share subdomain-curation cadence. |
| v4.1 | 2026-04-22 | Corrected H's family-naming after re-reading `canonical_corpus_manifest.json` and `src/lia_graph/ingestion/suin/bridge.py`: the authoritative `family` for the Expertos bucket is `interpretacion`, not `expertos` (which is the `source_tier` value). Added the four-axis naming table (`family` / `knowledge_class` / `source_tier` / folder / prefix / surface) and clarified that `family: "unknown"` is pending-review triage (5 formulario PDF entries with `ambiguity_flags: ["family_unknown", ...]` and `canonical_blessing_status: "blocked"`), not a fourth family. Curators and future Claude instances now have the precise field names and values the ingest pipeline writes. |
| v4.2 | 2026-04-22 | Added H's "Documentos por arreglar — cohort `family: \"unknown\"`" sub-section listing the 5 formulario PDFs currently blocked from canonical blessing (formularios 110 / 115 / 210 / 2517 / 260), why they are blocked (`text_extractable: false` + `parse_strategy: binary_inventory_only`), and the three fix paths per document (text-extract-then-reclassify, replace-with-guide, manual-curator-classification). Added the operational guideline that the `family: unknown` cohort is ongoing hygiene — the census tool (proposed in H's "Where to intervene") must emit a `por_arreglar` section alongside the `topic × family` matrix so operators see both curation gaps (undelivered content) and hygiene gaps (admitted-but-broken content) in one report. Flagged the intersection with C (formulario 115's `vocabulary_unassigned` flag is a precios-de-transferencia-topic-unregistered instance) and B2 (stuck formularios may need subtopic assignments that don't yet exist). |
| v5 | 2026-04-22 | **Day 1–2 landed.** `#1 eval harness` + `make eval-retrieval` + `#2 reranker shadow scaffold` shipped per the senior RAG reorder. New files: `scripts/eval_retrieval.py`, `src/lia_graph/pipeline_d/reranker.py`. Orchestrator wired to call `rerank_evidence_bundle` after retrieval; response `diagnostics.reranker` now carries the shadow-vs-hybrid delta. Launcher defaults `LIA_RERANKER_MODE=shadow` across all three modes; env matrix bumped to `v2026-04-22-evalharness1` with the new flag row. Baseline numbers from the 30-entry gold are recorded in the "Landed state" section at the top of this doc — all three gated metrics fail red lines today; that is by design. Curator tracks (gold spot-check, DIAN-procedure commissioning, 30→50 growth) remain human-bottlenecked and have not been auto-generated. |
| v5.3 | 2026-04-22 | **Topic-safety checks + alignment harness landed. Re-evaluation of the whole backlog added at the top of this doc.** The citation-faithfulness harness surfaced a failure mode bigger than citation-level hallucination: ~15% of non-abstaining answers were topically wrong (patrimony question, IVA answer) while citing real articles. Two orchestrator-level safeguards now fire at pipeline entry: (1) **router silent-failure abstention** — when `topic_router` returns no topic at confidence ≤ 0.15, short-circuit to an honest "couldn't classify" response instead of letting general-graph-research assemble a confident wrong answer. Catches Q13, Q25, Q27 on the gold. (2) **router↔retrieval misalignment detection** — score primary articles' titles+excerpts against topic-router keywords, flag when the router's chosen topic mismatches the articles' dominant topic. Promotes to abstention when router confidence < 0.50, otherwise serves the answer with `confidence_mode=topic_misalignment_hedged` and a diagnostics flag. Catches Q1-class confident-wrong routing. (3) **New third harness** `scripts/eval_topic_alignment.py` + `evals/alignment_baseline.json` + `make eval-alignment` — scores three metrics: `body_vs_router_alignment` (in-pipeline consistency), `body_vs_expected_alignment` (product correctness), `safety_abstention_rate` (band metric, 0.03–0.25). Same methodology-gated regression pattern. (4) All three baselines re-frozen at the post-safety pipeline shape. Retrieval baseline metrics dropped ~3pp because abstained queries now score 0 (the product improvement trades a few points of raw recall for fewer wrong-but-confident answers — worth it). Citation-faithfulness recall *improved* from 0.754 to 0.855 on the remaining non-abstaining queries. (5) Re-evaluation section at the top of this doc recomputes how the original A–H backlog ranks under these new measurements; topic-safety is now item #1, not on the original A–H list at all. No LIA_* env change. | `src/lia_graph/pipeline_d/topic_safety.py` (new), `src/lia_graph/pipeline_d/orchestrator.py` (two new safety hooks + abstention composer), `scripts/eval_topic_alignment.py` (new), `evals/alignment_baseline.json` (new), `evals/baseline.json` (re-frozen), `evals/faithfulness_baseline.json` (re-frozen), `Makefile` (new `eval-alignment` target), `docs/next/structuralwork_v1_SEENOW.md` (re-evaluation section + this row), `docs/orchestration/orchestration.md` (change-log companion row) |
| v5.2 | 2026-04-22 | **Citation-faithfulness harness landed.** Sibling to `eval_retrieval.py`, measures whether the served answer is grounded in the retrieved evidence. Two metrics: `citation_precision` (anti-hallucination — cites must be in the evidence bundle) and `primary_anchor_recall` (anti-orphan-evidence — hop-0 seeds should surface in the answer's inline anchors), plus `abstention_rate` observability. Gold-free (no new curator annotations). Same regression-vs-baseline CI pattern, same methodology-mismatch guard. Baseline snapshot: **precision = 0.993, recall = 0.754, abstention = 0.100** — all three aspirational red lines pass at baseline (0.95 / 0.70 / 0.25). v1 scopes inline `(art. X ET)` anchors only; body-text regulatory cites counted as observability but not scored. Next v2 axes flagged: body-text regulatory cite parsing, polish-mode faithfulness (does the LLM preserve anchors through rewrite). New files: `scripts/eval_citations.py`, `evals/faithfulness_baseline.json`, `make eval-faithfulness`. No LIA_* env change. | `scripts/eval_citations.py` (new), `evals/faithfulness_baseline.json` (new), `Makefile`, `docs/next/structuralwork_v1_SEENOW.md`, `docs/orchestration/orchestration.md` |
| v5.1 | 2026-04-22 | **Harness revised per senior-RAG verdict** captured in `docs/next/package_expert.md`. Five changes, no LIA_* env change (so no env matrix bump): (1) every retrieval metric now reported across a **2×2 matrix** — `(primary_only \| with_connected) × (strict \| loose normalizer)` — so the planner-anchor vs graph-expansion split and the "parent container counts as a hit" looseness are both visible. (2) CI gate demoted from absolute red lines (statistical theater at n=30, ±~18pp CI on r@10) to **regression-vs-baseline** at 2pp tolerance against committed `evals/baseline.json`. Absolute red lines stay as aspirational `ASPIRATIONAL=1` opt-in. (3) `topic_accuracy` renamed to `router_accuracy` — it measures `resolve_chat_topic`, not the pipeline (which echoes `request.topic`). (4) `subtopic_accuracy` dropped from reported metrics until accountant re-indexes gold `expected_subtopic` slugs against `config/subtopic_taxonomy.json`; the 0.000 score was a vocabulary mismatch, not a retrieval signal. Deliberately not auto-mapped with an LLM. (5) Baseline file `evals/baseline.json` committed as the reference snapshot. New Makefile levers: `FAIL_ON_REGRESSION` (default 1), `ASPIRATIONAL`, `UPDATE_BASELINE`, `TOLERANCE_PP` (default 2). Next milestone (flagged by the same expert as load-bearing): build a sibling **citation-faithfulness** harness — retrieval@10 is necessary but not sufficient in regulated domain. | `scripts/eval_retrieval.py` (rewrite), `evals/baseline.json` (new), `Makefile` (`eval-retrieval` target rewritten), `docs/next/package_expert.md` (new — expert ask package), `docs/next/structuralwork_v1_SEENOW.md` (landed-state rewrite + v5.1 row), `docs/orchestration/orchestration.md` (change-log companion row) |
