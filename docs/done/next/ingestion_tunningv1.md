# Ingestion & Retrieval Tuning v1 — Investigation Plan

> **Status:** draft · **Author:** paired architectural review · **Date opened:** 2026-04-24
> **Purpose of this doc:** we just ran a 30-question A/B expert evaluation that failed so completely it was uninterpretable. Before we ship code to "fix" it, this document defines the investigation we run *first* to make sure we execute the right things — not the convenient things.
>
> **Who this is for.** A new engineer or LLM coming to the problem cold, a product/business stakeholder (your boss), and future us when we come back to this in six weeks and need to remember why we chose what we chose.
>
> **What this doc is NOT.** An execution plan. No code gets written from this document. Its only output is a sharper diagnosis and a confident choice between three candidate execution paths (A, B, C — see §5).

---

## 0. Findings log (live)

> **This chapter updates as each investigation closes.** Read this first if you're coming to the doc mid-flight — it tells you the current picture of the world, and how that picture has changed our plans for the *next* investigations. The original §1–§11 plan is preserved below for traceability, but some investigations have been rescoped in light of what we've learned. Look for **[REVISED]** tags in §6.

### Operator preferences (ground rules for the study)

> Stated 2026-04-24 by the operator, so study recommendations don't artificially shy away from expensive operations:
>
> - **Full ingestion runs are fine.** If the investigation concludes that the right move is a full corpus re-ingest (`make phase2-graph-artifacts` or the Supabase-sink variant), recommend it — don't downscope to a delta just to be polite.
> - **Full embedding runs are fine.** If an investigation recommends re-embedding the corpus (e.g., because the embedding model changed, or because new chunks need vectors), recommend it.
> - **Full graph rebuilds are fine.** Same principle: Falkor reloads, re-running the SUIN merge, re-stamping topic/subtopic bindings are all on the table.
> - The cost this protects against is *wrong fixes*, not *slow commands*. Cheap partial runs that leave the system in a mixed state (some articles re-parsed, some not; some chunks re-embedded, some stale) are worse than a single clean full rebuild. When in doubt, recommend the clean full rebuild.

### Quick status

| Investigation | Status | One-line result |
|---|---|---|
| I1 — Práctica / Expertos tagging audit | ✅ Closed 2026-04-24 | **The concern is moot in the current state — Práctica/Expertos content is effectively not ingested at all.** See I1 findings below. |
| I1b — Ingestion-pipeline skip audit | ✅ Closed 2026-04-24 | **No pipeline bug. The artifact is stale.** A fresh `make phase2-graph-artifacts` run would add ~3,609 articles (1,391 EXPERTOS + 2,218 PRACTICA) — a **2.7× corpus expansion**. See I1b findings below. |
| I2 — Classifier keyword coverage scan | ✅ Closed 2026-04-24 | **Classifier isn't the bug it looked like.** Taxonomy contract holds, eval's Q12 misroute does NOT reproduce on direct test (Q12 routes correctly to `regimen_simple`). Only Q27 SAGRILAFT is a true classifier miss. The gap between eval-reported topics and direct-classifier output is now a new open question for I5. |
| I3 — Fixed-env 30Q re-run | ⏳ Pending · **rescoped by I5 — now harness-fix, not env-fix** | I5 showed the env was correct but the harness reads diagnostics from the wrong level. Rescope I3 to: fix harness to read `retrieval_health.primary_article_count` and `evidence_bundle.diagnostics.tema_first_mode`, then re-run. |
| I4 — Corpus completeness | ✅ Closed 2026-04-24 | **87.7% of the gold's expected article references are already in the corpus** (50 of 57). Missing 7 are mostly late-2024/2025 reforms (LEY_2466_2025, LEY_1819_2016, CONCEPTO_DIAN_006483_2024, DECRETO_2616_2013, DECRETO_957_2019, DECRETO_1650, LEY_2277_2022). Per-topic diff confirms 7 topic dirs have 0 ingested despite on-disk content — all would be fixed by the rebuild from I1b. |
| I5 — Contamination trace | ✅ Closed 2026-04-24 | **Two root causes, one unexpected.** Biofuel paragraph sourced from `knowledge_base/CORE ya Arriba/LEYES/OTROS_SECTORIALES/consolidado/Ley-939-2004.md` (Ley 939/2004 Art.1). AND — much bigger — **the A/B harness reads `primary_article_count`/`tema_first_mode` from the wrong nesting level of `response.diagnostics`. Those fields live in `evidence_bundle.diagnostics` or `retrieval_health`, not at top level. The "0 primary articles everywhere" narrative is measurement error, not a retrieval failure.** |
| I6 — Refusal-rate simulation | ✅ Closed 2026-04-24 | **A classifier-confidence gate does NOT solve the contamination problem.** 4 of the 5 contamination cases had confidence 1.00; the 5th had 0.67. Only 2 of 9 panel-flagged bad cases are low-confidence. The refusal gate must trigger on *evidence-topic coherence* (retrieval returned zero or off-topic chunks), not on classifier confidence. At threshold 0.2, refusal rate is 13% and catches only 2 bad cases — honest but narrow. |
| I7 — Contadores principle port audit | ✅ Closed 2026-04-24 | **Priority shuffle.** Still high value: hard topic-scope filter (biofuel trace confirms), citation allow-list in prompts, ClaimPack for number-drift, fabrication-marker eval rubric. **Lower value than I thought** before investigating: filename-prefix ingest classifier (we already have `ingestion_classifier.py` assigning `family`/`topic_key` at ingest — the mechanism exists, it's just unused at retrieval time), intent-specific confidence gate (I6 showed contamination mostly happens at high confidence). **New priority that emerged from investigations**: an *evidence-topic coherence gate* (not a classifier-confidence gate) — when retrieved primary articles' topic majority disagrees with plan.topic, refuse. Biofuel case + I6 prove this is the mechanism that would catch what's actually happening. |

### Headline findings so far

**Update 2026-04-24 after I5 (this is the most important update in the doc so far).** The A/B evaluation report's headline claim — "all 60 result blocks returned 0 primary articles, TEMA-first never fired, the experiment was invalid because of a configuration mistake" — turns out to be partly a measurement artifact, not an observed reality. Walking through the evidence:

1. The eval's run manifest confirms `graph_backend: falkor_live` was correctly set, `retrieval_backend: supabase` was correctly set, and `LIA_TEMA_FIRST_RETRIEVAL` was explicitly set to `"on"` / `"off"` per mode. The environment was right.
2. The eval's per-row output shows `primary_article_count: 0` and `tema_first_mode: None` across all 60 blocks. At first reading this suggests retrieval failed completely.
3. Direct inspection of `response.diagnostics` construction in `src/lia_graph/pipeline_d/orchestrator.py:483–499` shows that the top-level `diagnostics` dict does NOT contain `primary_article_count`, `tema_first_mode`, `tema_first_topic_key`, `tema_first_anchor_count`, or `seed_article_keys`. Those fields live *nested* inside `diagnostics["evidence_bundle"]["diagnostics"]`, or equivalently in `diagnostics["retrieval_health"]` (which IS at top level but with a different key).
4. The A/B harness (`scripts/evaluations/run_ab_comparison.py:162–174`) reads every one of those fields from the top level via `diag.get("...")`. Every read returns `None`, and the harness falls back to `0` for the counts.
5. Confirmed by running `run_pipeline_d` locally against the real Q12 query: top-level `diagnostics["primary_article_count"]` is `None`, top-level `diagnostics["retrieval_health"]["primary_article_count"]` is `3`. The real number is visible; the harness just reads the wrong key.

Translation: **we can't trust the 30Q A/B's quantitative diagnostics.** Retrieval may have returned useful articles the whole time, or it may have returned zero the whole time, or it may have returned mixed results — we literally cannot tell from the recorded data. The *qualitative* observations are still real (Q16's biofuel contamination is verbatim in the answer_markdown; the senior-contador panel's verdicts are credible on answer quality) but the *diagnostic* narrative that shaped the "invalid A/B" conclusion is a harness bug.

This reshapes I3 from "fix the environment and re-run" (nothing to fix — env was correct) into "fix the harness's diagnostic reads and re-run." Much smaller change.

Biofuel contamination itself was traced: the chunk came from `knowledge_base/CORE ya Arriba/LEYES/OTROS_SECTORIALES/consolidado/Ley-939-2004.md` (Ley 939/2004, Art. 1 "Definición de biocombustibles"). It's a *normativa* article with `family=normativa` — so even a strict topic-gate keyed on document family wouldn't have blocked it. The gate would have to be keyed on topic (`sector_energia_mineria` or `otros_sectoriales`) not matching `laboral`.

Additionally, I5 revealed a classifier-confidence story that redefines what an "eval misroute" is:
- **16 of 30 questions classify correctly** (direct test matches expected topic).
- **4 of the remaining are low-confidence cases the system should have refused instead of guessing** (Q9, Q10, Q12, Q24 — all confidence ≤ 0.25). These are where a minimum-confidence refusal gate would have converted "wrong answer" into "honest refusal."
- **4 are naming mismatches** between the eval's `expected_topic` string and the actual taxonomy key (Q19 `obligaciones_mercantiles` vs taxonomy `comercial_societario`; Q25 `impuesto_patrimonio` vs `impuesto_patrimonio_personas_naturales`; Q26 `dividendos` vs `dividendos_utilidades`; Q29 `perdidas_fiscales` vs `perdidas_fiscales_art147`). The classifier is right; the gold file uses inconsistent keys.
- **3 are under-specific routing** (Q20 sanciones, Q21 firmeza, Q22 devoluciones — all lumped into `declaracion_renta` because there's no subtopic granularity in the keyword tables for procedural tax topics).
- **1 is a genuine misroute** (Q1 expected `declaracion_renta`, routes to `facturacion_electronica` at confidence 1.00 because "facturación electrónica" keywords dominate — a case where prompt-engineering or subtopic detection is needed).

In other words: the classifier is much less broken than the eval's narrative suggested. The real interventions indicated by I5 are: **(a) minimum-confidence refusal gate** (fixes 4 cases), **(b) align gold-file topic keys to the taxonomy** (fixes 4 cases), **(c) subtopic keywords for declaracion_renta procedural branches** (fixes 3 cases). Only 1 case requires classifier-logic changes.

**Update 2026-04-24 after I2.** The classifier is in better shape than the eval led us to believe. The taxonomy has 76 topics (65 parents + 11 subtopics), every parent has a keyword dictionary, no keyword key maps to an invalid topic, and the contract "classifier cannot emit a key absent from the taxonomy" holds. 18 topics are green-coverage, 38 yellow, 9 red (mostly minor sectoral topics). More importantly, **when I ran the eval's own questions through `detect_topic_from_text` directly, Q12 ("RST para SAS de consultoría") routes correctly to `regimen_simple` with 15 points and confidence 1.00 — not to `sector_medio_ambiente` as the eval report claimed.** Q16 fires its subtopic override for `trabajador tiempo parcial`. Only Q27 (SAGRILAFT) is a true classifier problem — it ties 3-3 between `laboral` and `sagrilaft_ptee`, with `laboral` winning by dict order. Nine subtopic children of `declaracion_renta` (ganancia_ocasional, rentas_exentas, beneficio_auditoria, conciliacion_fiscal, etc.) have no keyword coverage at all — the classifier itself emits a warning at startup listing them. The discrepancy between my direct-classifier results and the eval's reported `effective_topic` values is now itself a new signal: some layer *downstream* of the classifier appears to be reassigning topics. Nailing that down is now the job of I5.

**Update 2026-04-24 after I1b.** I1's "the content isn't ingested" finding turned out to be a stale-artifact problem, not a pipeline bug. The ingestion pipeline *correctly* admits EXPERTOS and PRACTICA content (`graph_target=True`, `graph_parse_ready=True`, `parse_strategy=markdown_graph_parse`, `knowledge_class=interpretative_guidance|practica_erp`). A direct test of `parse_article_documents` on the EXPERTOS scope alone produces **1,391 articles**; on the PRACTICA/LOGGRO scope, **2,218 articles**. Neither set appears in `artifacts/parsed_articles.jsonl` (built 2026-04-21). Running `make phase2-graph-artifacts` against the current `knowledge_base/` would 2.7× the served corpus (from 2,118 articles to ~5,700+). **The single highest-leverage action this project can take is running that command.** Everything downstream — retrieval tuning, classifier fixes, refusal gates — will give different answers against a corpus that's nearly three times its current size.

**The most important thing we've learned is not in the plan.** We opened I1 to answer your boss's concern ("will a strict topic gate over-filter Práctica and Expertos content?"). The concern, as framed, is answered. But the answer revealed a much bigger problem that changes what this project should be about.

1. **Práctica and Expertos content does exist — as curated folders on disk, covering nearly every major topic** (SAGRILAFT, labor, RST, firmeza, IVA, NIIF, …). Roughly **99 directories and ~398 markdown files** are organized on disk under `knowledge_base/CORE ya Arriba/*/EXPERTOS/` and related subfolders.
2. **None of that content made it into the ingested corpus.** `artifacts/parsed_articles.jsonl` has **zero** paths containing "PRACTICA", "EXPERTO", or "INTERPRETACION". Of 2,118 ingested articles, 1,865 are under `NORMATIVA/` path segments. The remaining paths are still normative in character, just with different directory naming.
3. **The corpus is overwhelmingly tax-code-heavy.** Of the 16 top-level topic folders under `CORE ya Arriba/`, **RENTA alone contains 1,297 of the 2,118 ingested articles** (65%) and `LEYES` contains another 416 (21%). Labor, RST, SAGRILAFT, and FIRMEZA topics — the ones the 30Q eval failed hardest on — together contain **fewer than 100** ingested articles.
4. **Interpretative and doctrinal content IS present, but embedded inside normative articles' markdown bodies** (sections like "**Doctrina Concordante:**", "**Jurisprudencia:**", "**Concepto DIAN 833 de 2024:**"). That is the contamination surface we observed in the eval: a SAGRILAFT question lexically matches the word "SARLAFT" appearing inside a footnote of article 631-5 (a tax-code article), and the chunker returns that article as evidence.
5. **Document family and topic are encoded in the `source_path` string, not in first-class metadata.** No `topic_key`, `document_family`, or `cross_topic` flags exist on parsed articles today. A Lia-Contadores-style `path_prefix` filter would require parsing the path, which is a convention some articles follow and others don't.

### After-all-investigations synthesis (2026-04-24)

All seven investigations closed in a single session. Major revisions to the original narrative:

**The 30Q A/B eval's headline conclusion was partly wrong.** It reported that the A/B was invalid because of a configuration mistake and that retrieval returned zero articles 60/60. The real state of the system is more nuanced:

1. The environment was configured correctly — `graph_backend: falkor_live` and `retrieval_backend: supabase` were both set as intended.
2. The "zero primary articles everywhere" claim is a **harness-diagnostic bug**, not an observed reality. The A/B harness reads `primary_article_count` and `tema_first_mode` from the top level of `response.diagnostics`, but those fields live nested inside `evidence_bundle.diagnostics` and `retrieval_health`. We literally do not know what the real counts were in the eval run.
3. The classifier is much less broken than the eval suggested. Of 30 cases, 16 route correctly, 4 are low-confidence (should refuse), 4 are gold-file naming mismatches, 3 are under-specific (procedural topics lumped into `declaracion_renta`), and only 1 is a true misroute.
4. The corpus is much less incomplete than the eval suggested. 87.7% of the gold's expected article references are already present. The 7 missing are late-2024/2025 reforms and decrees.
5. The contamination IS real and IS a serious problem — biofuel text from `Ley-939-2004.md` appeared in a labor answer. But the mechanism isn't "classifier is confused"; it's "retrieval fell back to chunk-level lexical scoring with no topic filter, and the chunk happened to match on weak tokens."

**What actually needs to happen**, in priority order:

1. **Rebuild the artifact** (`make phase2-graph-artifacts`). Adds ~3,609 articles (1,391 EXPERTOS + 2,218 PRACTICA) the pipeline has always been ready to ingest. This alone is a 2.7× corpus expansion and will change the picture for every other metric. The operator has already confirmed this is OK.
2. **Fix the A/B harness diagnostic reads** so `primary_article_count`, `tema_first_mode`, and `tema_first_topic_key` are read from the correct nesting (or lift them to top-level `response.diagnostics`, which is cheaper). Without this, no future eval can be trusted quantitatively.
3. **Add an evidence-topic coherence gate** (not a classifier-confidence gate). When retrieval returns primary articles whose dominant topic differs from `plan.topic`, or returns zero primary articles and the support_documents don't topic-match the plan, refuse with a specific `refusal_reason`. This is the Contadores `topic_guardrails` principle, adapted to the graph world.
4. **Extend the existing `topic_safety.detect_topic_misalignment`** (which exists in `pipeline_d/topic_safety.py` and did correctly hedge on Q4/Q7/Q9 in the eval) to also fire when `primary_articles` is empty — scoring support_documents instead. Today it short-circuits on zero primary.
5. **Port the defensive citation allow-list** from Contadores's `prompts/answer_policy_es.md` into Lia_Graph's `pipeline_d/answer_policy.py`. A per-topic ET-article allow-list (labor → {383, 384, 385, 387, 387-1, 388, 108, 114-1}) would have blocked the Q11 `art.516/514` and Q27 `art.148` contamination observed by the panel.
6. **Align the gold file's `expected_topic` keys to the real taxonomy.** Q19 expects `obligaciones_mercantiles`, taxonomy has `comercial_societario`. Four cases of this in the 30Q set.
7. **Add subtopic keyword coverage** for the procedural branches of `declaracion_renta` — `firmeza_declaraciones`, `sanciones_extemporaneidad`, `devoluciones_saldos_a_favor`. Currently these are lumped into the parent.
8. **Re-run the 30Q** with the rebuilt corpus and the fixed harness. The result is what we originally wanted from the April 24 run.

**Items we can safely defer or deprioritize:**
- A classifier redesign (graph-query mode, etc.). The keyword-table classifier does its job at the known-good cases and its known failures have simpler fixes. Revisit only if the fixes above don't move the needle.
- Full Path B rebuild. The investigations found that most of what looked like "architectural rot" is actually missing glue (diagnostic surfacing, evidence-coherence gate, citation allow-list). A ~one-week focused tightening pass addresses everything we observed.
- The `cross_topic=true` edge flag concern for Práctica/Expertos. Empirically moot until the rebuild happens; then the first test is whether the topic gate lets legitimate cross-cutting Práctica through. Revisit after the rebuild.

**Items that still matter but haven't been touched by these investigations:**
- Ingesting late-2024/2025 reforms (Ley 2466/2025, Res. DIAN 165/2023, Ley 2277/2022 articles — some of which ARE in the corpus but not with the exact keys the gold expects).
- Supabase's freshness. We verified the *artifact* is stale; we didn't verify the cloud Supabase chunks table. If Supabase is also stale, the staging run is reading from a truncated corpus too.

### How this reshapes the plan

- **The boss's concern is answered: No, a strict topic gate cannot over-filter Práctica/Expertos today**, because those families aren't in the corpus. The concern becomes valid only *after* we fix ingestion to include them — at which point the gate design must account for their cross-topic nature. We should carry the concern forward as a design constraint, not a blocker for any current work.
- **The most important problem is no longer retrieval tuning — it's ingestion completeness.** Investigation I4 (corpus completeness) is promoted from "verify the normative anchors are present" to a P0 investigation that must also measure how much *curated but uningested* content exists, and why.
- **A new investigation I1b is opened**: understand why the ingestion pipeline is skipping content the user has clearly organized on disk. Is it a deliberate scope decision (Expertos rendered differently, not as article-like chunks), a missing glob pattern, or a pipeline bug? We cannot fix ingestion without knowing.
- **Investigation I6 (refusal-rate simulation) inherits a caveat.** If we simulate refusal rates today, they will be high *by construction* because operational/interpretive content doesn't exist in the corpus. Any refusal-rate number we produce needs to be interpreted "given current corpus state" and re-run after I1b/I4 close.
- **Path choice implication.** Path A (tighten) and Path B (rebuild) were both framed as retrieval-layer interventions. If the headline problem is actually ingestion breadth, then *neither path as currently scoped fixes the observed eval failures* — both would deliver a correctly-filtering retriever on top of a corpus that doesn't contain the answers. Path selection should wait until I1b + I4 report.

### Evidence for the above

- `artifacts/parsed_articles.jsonl` — 2,118 articles total; `grep -c NORMATIVA = 1865`; `grep -c PRACTICA = 0`; `grep -c EXPERTO = 0`; `grep -c INTERPRETACION = 0`.
- Disk inventory: `find knowledge_base -type d | grep -iE "(PRACTICA|EXPERTO|INTERPRETACION)"` returns 99 dirs; the .md count under those dirs is 398.
- Top-level topic distribution under `CORE ya Arriba/`: RENTA 1297, LEYES 416, Corpus de Contabilidad 104, and a long tail under 50 each.
- Sample article (art. 631-5 beneficiario final) contains embedded sections for Doctrina Concordante, Jurisprudencia, and Concepto DIAN 833 de 2024 inside its `full_text` — showing how interpretative content enters the corpus today.

---

## 1. The one-paragraph story

Lia Graph is a retrieval-augmented question-answering system for Colombian accountants. It was branched from an earlier product, Lia Contadores, with a bet that swapping a flat vector index for a knowledge graph would reduce hallucinations. Last week, an independent expert panel graded 30 questions across the new system's two retrieval modes and returned a devastating verdict: **the experiment was invalid because of a configuration mistake, and worse, it surfaced a more fundamental quality problem — when the system can't find good evidence, it invents it from unrelated fragments**. A question about part-time labor returned a paragraph about biofuels. A question about anti-money-laundering returned a tax-declaration-correction article. This document defines what we investigate before we commit to a fix, so that whatever we ship next is grounded in evidence, not instinct.

---

## 2. Context: how we got here

### 2.1 Ancestor product — Lia Contadores

A conventional RAG stack. Not great at being right, but **genuinely good at being quiet when it wasn't sure**. It achieved that quietness via five stacked filter surfaces (see §7 for full inventory). The most important ones:

- A **hard topic-scope filter**: a chunk about labor code couldn't be admitted into an IVA answer, regardless of vector similarity. Topic was an identity check, not a score.
- A **defensive citation allow-list** in the answer prompt: "when topic=laboral, the only ET articles you may cite are 383, 384, 385, 387, 387-1, 388, 108, 114-1 — everything else is retrieval leakage, ignore it."
- A **low-confidence refusal branch**: when evidence was weak, the system returned a polite "I can't answer this confidently, can you reformulate?" instead of guessing.

These were ugly, code-level, domain-specific safeguards. They worked. The bet in building Lia Graph was that a knowledge graph with explicit topic-to-article edges would make these safeguards unnecessary — topology would encode discipline that Lia Contadores achieved with tape.

### 2.2 Successor product — Lia Graph

A graph-native RAG. FalkorDB for traversal, Supabase for chunks. Ingests the Colombian tax/labor corpus into a graph with `ArticleNode`, `TopicNode` (41 of them), `SubTopicNode`, and typed edges including `TEMA` (2,361 of them — the topic-to-article adjacency the original bet was about). A modular pipeline (`planner` → `retriever` → `topic_safety` → `answer_policy` → `answer_synthesis` → `answer_assembly`) lives under `src/lia_graph/pipeline_d/`.

The ingestion & retrieval subsystem has been iterated five times already — `docs/next/ingestionfix_v1.md` through `v5.md` — each pass addressing a different corpus or retrieval issue. **v5 introduced "TEMA-first retrieval" behind the flag `LIA_TEMA_FIRST_RETRIEVAL`** with the hypothesis that seeding retrieval from topic-bound articles would suppress contamination.

### 2.3 The failed 30-question A/B evaluation

Run `v5_tema_first_vs_prior_live` put 30 accounting questions through both modes and asked a senior-contador panel to grade each one. Outcome:

| Verdict | Count | What it means |
|---|---|---|
| New better (TEMA-first wins) | 4 | All 4 were cases where NEW correctly detected a topic mismatch and **refused to answer**. |
| Prior better (legacy wins) | 5 | All 5 were cases where NEW **contaminated** the answer with unrelated content and PRIOR stayed silent with boilerplate. |
| Tie | 17 | Both modes returned the same empty/boilerplate response. |
| Both wrong | 4 | Topic classification failed upstream in both modes. |

The panel's headline judgment: **this was not an A/B between TEMA-first and legacy — it was an A/B between two broken retrieval paths** that happened to differ only in how they phrased their disclaimers. Evidence: every one of the 60 result blocks (30 × 2) reported `primary_article_count: 0`, `tema_first_mode: None`, and an empty `seed_article_keys` list. The new code path never actually executed.

### 2.4 What we've already diagnosed

A paired architectural review (one "reconstructor" perspective, one "incremental" perspective) ran after the eval. Points of convergence:

1. **The single wire that invalidated the A/B.** The eval shell didn't export `LIA_GRAPH_MODE=falkor_live`, so the orchestrator silently defaulted to `artifacts` mode and `retriever_falkor.py` never ran. The TEMA-first path is gated by that environment variable. A one-line oversight, but it poisoned all 60 data points.
2. **A much deeper issue is not about TEMA-first at all.** When retrieval returns zero primary articles, the synthesizer falls through to a lexical-overlap chunk search in `answer_support.py` that has no topic filter. This is the contamination vector. A chunk from an unrelated article can surface simply because it shares a token with the query.
3. **The classifier can emit topic keys that don't exist.** Question 12 ("RST para SAS de consultoría") was routed to `sector_medio_ambiente`, which is not even a valid topic in `config/subtopic_taxonomy.json` (the closest real topic is `otros_sectoriales`). This is a contract bug: the classifier output space is larger than the taxonomy.
4. **A functioning safeguard exists but was silent when it mattered.** `pipeline_d/topic_safety.py` contains a `detect_topic_misalignment` function that compares the router-predicted topic against the dominant topic in retrieved articles. When they disagree, it emits a courteous refusal. It was the *only* good behavior observed in NEW mode (questions 4, 7, 9). But it short-circuits when `primary_articles` is empty — exactly the case we hit 30 out of 30 times.

### 2.5 What we have *not* yet diagnosed

The investigation in §6 closes these gaps. The short list:

- We don't know how Práctica and Expertos documents are tagged today. We don't know whether a strict topic gate would starve them (your boss's concern — see §4).
- We don't know whether the classifier's keyword coverage is sparse across all 39 topics or only a few. The eval exposed 3–5 misroutes; we don't know if the other 34 are healthy or just untested.
- We haven't re-run the 30Q with the environment correctly set. We don't know what TEMA-first *actually does* when it runs. The eval tells us nothing about this.
- We don't know how many production queries would convert to honest refusals under a strict minimum-evidence gate. If it's 40%, we have a usability problem. If it's 8%, we have a clean win.

These gaps are the reason this document exists. Shipping any of the three candidate paths below without closing them is a second round of confidently-acting-on-shaky-evidence.

---

## 3. What we know with confidence (claims backed by code or the eval report)

| # | Claim | Evidence |
|---|---|---|
| 1 | The graph data is healthy. TopicNode and TEMA edges exist and are populated. | Graph header in the eval: 41 TopicNodes, 2361 TEMA edges. |
| 2 | The TEMA-first code path is implemented and gated correctly in `retriever_falkor.py`. | `src/lia_graph/pipeline_d/retriever_falkor.py:99–139`, commit `258666e`. |
| 3 | The TEMA-first code path was **not executed** during the eval. | All 60 result blocks: `tema_first_mode: None`. |
| 4 | The eval ran in `artifacts` mode, not `falkor_live` mode. | All 60 result blocks: `primary_article_count: 0`; `LIA_GRAPH_MODE` unset in harness. |
| 5 | When primary retrieval returns zero, the synthesizer still emits an answer built from lexical-overlap-scored chunks with no topic filter. | `src/lia_graph/pipeline_d/answer_support.py` — `extract_support_doc_insights` scores candidates against query tokens, no topic gate. |
| 6 | A topic-misalignment detector exists and works, but it short-circuits when `primary_articles` is empty. | `src/lia_graph/pipeline_d/topic_safety.py:113–119`. |
| 7 | The classifier can emit topic keys absent from the taxonomy. | Eval Q12 effective_topic = `sector_medio_ambiente`; `config/subtopic_taxonomy.json` has no such key. |
| 8 | Lia Contadores's anti-hallucination stack (five filter surfaces) is fully absent from Lia Graph. | Side-by-side study of `github.com/avas888/Lia_contadores` vs. `src/lia_graph/`. |

## 4. What we're guessing about (claims we need evidence for before acting)

| # | Open question | Why it matters | How it changes the plan |
|---|---|---|---|
| A | Do Práctica and Expertos documents have a reliable topic tag today? | If tagging is sparse, a strict topic gate silently starves the most operationally useful content. This is the risk your boss named. | If tagging is bad, we must schedule a tagging pass *before* any strict gate ships. |
| B | How many of the 39 taxonomy topics have thin classifier keyword coverage? | The eval exposed 3–5 misroutes. We don't know if that's the tip of an iceberg or the full list. | If coverage is thin across many topics, Path A's keyword-hardening patch grows from one day to one week. |
| C | When TEMA-first actually runs (with env fixed), does it outperform legacy on the same 30 questions? | The whole v5 bet hinges on this and we have zero data on it. | If TEMA-first wins clearly, Path B (rebuild) becomes more attractive. If it's a wash, Path A is sufficient. |
| D | Under a strict "minimum evidence → refuse" gate, what fraction of real user queries would flip to refusals? | A high refusal rate is a usability regression even if accuracy improves. | If the rate is >25%, we need to soften the gate or invest in retrieval improvements first. |
| E | Is the lexical-overlap fallback ever the *right* behavior, or is it pure damage? | If it occasionally saves a legitimately-graph-missing query, deleting it costs us those wins. | Affects whether we gate-then-delete (Path A) or delete-now (Path B). |
| F | Does Supabase's `hybrid_search` RPC accept or respect a topic filter argument today? | Determines how cheaply we can implement the topic gate at the query level vs. post-filtering in Python. | Cheap = ship Path A in days. Expensive = requires migration, tips toward Path B or C. |
| G | What is the graph-level completeness for the domains where the eval showed zero evidence (SAGRILAFT, ZOMAC, Ley 2466, Res. DIAN 165/2023)? | Some of those questions might have failed simply because the corpus doesn't contain those documents yet. | If coverage is absent, it's an ingestion problem, not a retrieval one — neither A nor B fixes it. |

---

## 5. The three candidate execution paths (summarized so the investigation has a target)

| Path | One-sentence description | Rough effort |
|---|---|---|
| **A. Tighten** | Ship seven flag-gated patches that add a topic gate, a refusal branch, keyword-hardening, surfaced diagnostics, a citation allow-list in prompts, and a fast 10–12 question regression harness. Zero deletions. | ~1 week |
| **B. Rebuild** | Redesign the retrieval contract: `ArticleNode.topic_key` becomes a required graph property, BFS may not cross topic boundaries without a `cross_topic=true` edge flag, the classifier queries the graph rather than a keyword table, and the lexical fallback is deleted. | 2–3 weeks |
| **C. Hybrid** | Execute Path A plus one piece of Path B — stamp `ArticleNode.topic_key` at ingest so the topic gate has deterministic ground truth to filter against. Defer the classifier rewrite and the cross-topic edge flag. | ~1.5 weeks |

The investigations in §6 are designed so that their outputs tell us which path is justified. We should not choose before those investigations return.

---

## 6. Investigations to run

Each investigation has: **the question, why it matters, method, time budget, deliverable, decision impact**. All are read-only; none ship code.

### Investigation I1 — Tagging audit of Práctica and Expertos documents

> **Status: ✅ Closed 2026-04-24.** Headline result in §0 Findings. Short version: the question we set out to answer was moot — Práctica/Expertos content isn't in the ingested corpus at all, so no gate can over-filter it. The real finding is an ingestion gap, not a tagging problem. That finding opens I1b below and rescopes I4/I6.

- **Question it answers.** Do Práctica (operational guidance) and Expertos (interpretive opinion) documents currently carry reliable topic metadata? How many of them legitimately span 2+ topics?
- **Why it matters.** Your boss's concern. A strict topic gate (Path B, or even Path A's softer version) silently filters out chunks whose topic tag is wrong, missing, or overly narrow. Práctica and Expertos are the most cross-cutting content by nature — a single UGPP circular can legitimately touch labor, simple regime, withholding, and tax procedure all at once. If their tagging is poor today, we have to fix tagging before any gate.
- **Method.** Sample 100 chunks from Supabase `chunks` table where `document_family ∈ {practica, interpretacion}`. For each: inspect `topic_key`, any subtopic metadata, any cross-topic flag. Manually classify a 20-chunk subsample and compare against the stored tag.
- **Time budget.** Half a day.
- **Deliverable.** A short report: tagging coverage % (chunks with non-null topic), tagging accuracy on the manual subsample, and a cross-topic frequency estimate ("X% of Práctica legitimately spans ≥2 topics").
- **Decision impact.** If tagging coverage < 80% or accuracy < 85%, no strict gate ships until tagging is fixed — shifting Path A's schedule by ~1 week and making Path B conditional on a tagging pass.

### Investigation I1b — Ingestion-pipeline skip audit  🆕 *opened by I1*

- **Question it answers.** Why is curated content under `knowledge_base/CORE ya Arriba/*/EXPERTOS/` (and the sibling `PRACTICA` / `Interpretacion_Expertos` folders under `Documents to branch and improve/`) missing from `artifacts/parsed_articles.jsonl`? Is it a deliberate scope decision (e.g., Expertos are intentionally routed to a different pipeline), a missing glob in the ingestion entry point, or a silent skip triggered by file-shape assumptions?
- **Why it matters.** The I1 audit found ~398 markdown files across ~99 EXPERTOS/PRACTICA directories on disk that are invisible to the retriever. This is the largest single gap separating the eval's "cobertura parcial" verdicts from a system that could actually help a working accountant. Any retrieval-layer fix ships on top of a corpus that's missing the operational content its users need. We cannot pick an execution path without knowing whether fixing ingestion is a one-line change or a pipeline redesign.
- **Method.** (a) Read the ingestion entry point — `src/lia_graph/ingestion/` (including `ingest.py` CLI) — to understand how it walks the filesystem and what it admits. (b) Locate the glob / extension / filename filter that decides what gets parsed. (c) Test the hypothesis by manually running the ingestion loader against one EXPERTOS file (e.g., `CORE ya Arriba/SAGRILAFT_PTEE/EXPERTOS/*.md`) and observing what happens — accepted, rejected, or silently skipped. (d) If it's rejected, categorize why (filename pattern, markdown structure, missing frontmatter, intentional skip rule).
- **Time budget.** Half a day to one day.
- **Deliverable.** A short root-cause writeup with one of four verdicts: *deliberate-scope*, *missing-glob*, *structural-rejection* (docs don't match the parser's expected article shape), or *bug*. If deliberate-scope, document where Expertos content *is* supposed to surface — chunks via Supabase only? an unimplemented pipeline? If not deliberate, a patch sketch for the glob/parser.
- **Decision impact.** This is now the gate for everything else. If ingestion is trivially fixable (missing glob), we should fix it *before* I3–I7 so subsequent investigations reflect the real corpus. If ingestion needs a structural redesign, that scope absorbs much of what we called Path B/C and reprioritizes the whole project.

### Investigation I2 — Classifier keyword coverage scan

> **Status: ✅ Closed 2026-04-24.** Headline result in §0 Findings. Short version: the classifier is in better shape than the eval led us to believe. Taxonomy contract holds, Q12's reported misroute does not reproduce on direct test, and only 9 topics are red-coverage (mostly minor). The interesting finding is the *gap* between the eval-reported `effective_topic` and what the classifier returns on the same question — that gap is now the job of I5.


- **Question it answers.** Across all 39 taxonomy topics, how many have well-populated keyword lists versus sparse or empty ones?
- **Why it matters.** The eval exposed 3–5 misroutes, but we only tested 30 questions. A classifier with thin keyword coverage for 20 topics will silently mis-route production queries in ways our current eval set doesn't expose.
- **Method.** Load `src/lia_graph/topic_router_keywords.py`. For each of the 39 topics in the taxonomy, count strong and weak keyword entries. Also check whether the closed-set contract holds: does every topic the classifier can emit exist in the taxonomy?
- **Time budget.** 2 hours.
- **Deliverable.** A table with one row per topic: keyword count, alias count, a rough "coverage health" rating (green/yellow/red). Plus the list of invalid keys the classifier can currently emit.
- **Decision impact.** If >10 topics are red, Path A's P3 (keyword hardening) grows from 1 day to 3–4 days. If the closed-set contract is broken for many topics, we have a structural bug that argues for Path B or C.

### Investigation I3 — Re-run the 30Q A/B with the environment fixed

- **Question it answers.** When TEMA-first actually executes, does it do what v5 intended? Does the underlying hypothesis of v5 (topic-anchored retrieval beats lexical-anchored retrieval) hold?
- **Why it matters.** This is the experiment we thought we ran last week. We still don't have its result. Our choice between A, B, and C depends partly on how good the graph-native retrieval already is; right now we're guessing.
- **Method.** Export `LIA_GRAPH_MODE=falkor_live`, `LIA_CORPUS_SOURCE=supabase`, `LIA_TEMA_FIRST_RETRIEVAL=on`. Re-run `scripts/evaluations/run_ab_comparison.py` on the same 30 questions. Add a preflight assertion that refuses to start unless `retrieval_backend/graph_backend` match the expected mode — a safeguard so this can't happen again.
- **Time budget.** Half a day (the run itself is ~15 minutes; the analysis is the bulk).
- **Deliverable.** A corrected A/B report with diagnostic signatures. No new expert panel yet — just the machine diagnostics: primary_article_count distributions, TEMA anchor counts, classifier confidences, mismatch detections. Compare side-by-side with last week's invalid run.
- **Decision impact.** Strong TEMA-first performance → Path B/C are more attractive. Weak or mixed → Path A is sufficient. Also tells us whether the bright spots in NEW mode (Q4/Q7/Q9 mismatch bails) were artifacts of artifact-mode or real.

### Investigation I4 — Graph-completeness spot check for known-failed domains  **[REVISED by I1]**

- **Question it answers.** (a) For the 30 eval questions, do the expected normative anchors *exist* in the graph? (b) **[new]** For each topic folder that appeared in the eval, how does *ingested* article count compare to *on-disk* markdown count across its NORMATIVA, EXPERTOS, and PRACTICA sub-folders? In other words: how much of the content the user has already curated is the retriever actually seeing?
- **Why it matters.** Some failures may not be retrieval failures at all — they may be ingestion gaps. For example: Q10 needs Res. DIAN 165/2023, Q15 needs Ley 2466, Q25 needs Ley 2277/2022 art. 35. If those documents aren't in the corpus, no retrieval tuning rescues them. **[new]** I1 already established that EXPERTOS/PRACTICA coverage is effectively zero in the ingested corpus; I4 now also needs to quantify *per-topic* what fraction of on-disk content is invisible to the retriever, so we can target the ingestion fix.
- **Method.** For each of the 30 questions, extract the normative references the expert panel said should have been cited. Run a Cypher query against FalkorDB checking whether each `ArticleNode` exists. Also check the Supabase `chunks` table. **[new]** In parallel, for each top-level topic dir under `knowledge_base/CORE ya Arriba/`, diff the on-disk .md file count against the ingested article count (join via `source_path` substring).
- **Time budget.** 1 day (unchanged).
- **Deliverable.** (a) A 30-row table: question → expected references → graph status. (b) **[new]** A per-topic coverage-gap table: topic → on-disk .md count → ingested-article count → coverage ratio.
- **Decision impact.** If >25% of failures are ingestion gaps, we have a corpus problem that no retrieval path fixes alone. **[new]** Combined with I1b, this investigation sets the scope of the ingestion fix: which topics are worst-starved, and what the ingestion fix needs to cover to move the needle on the eval.

### Investigation I5 — Contamination trace on the five PRIOR-better questions

> **Status: ✅ Closed 2026-04-24.** Headline result in §0 Findings. Short version: two findings, one specific and one architectural. Specific: the Q16 biofuel paragraph came from `Ley-939-2004.md` Art. 1. Architectural: **the A/B harness reads `primary_article_count` and `tema_first_mode` from the wrong nesting level of `response.diagnostics`; the `0 everywhere` narrative is measurement error, not actual retrieval failure.** This finding rescopes I3 (no env fix needed, just a harness diagnostic fix) and redefines what an "eval misroute" is (most cases are low-confidence, naming-mismatch, or under-specific routing — not classifier bugs).


- **Question it answers.** How exactly did biofuels end up in a part-time-labor answer? What's the chain of code decisions from query to contaminated output?
- **Why it matters.** We hypothesize the path is: classifier routes correctly → primary retrieval returns zero → `answer_support.extract_support_doc_insights` falls back to lexical chunk scoring → an unrelated chunk scores high on a shared token. We should *confirm* this before ripping out or gating the fallback. If the real path is different, our fix would miss.
- **Method.** For each of questions 11, 16, 22, 27, and one of the both_wrong cases: re-run with full diagnostic logging enabled. Trace the chunk ID of each contaminating paragraph back through retrieval to its source document and metadata. Record which code path admitted it and which ranker scored it highest.
- **Time budget.** 1 day.
- **Deliverable.** A trace report with five chain-of-custody diagrams, one per contamination case. Pinpoints the exact code location where a filter should have fired and didn't.
- **Decision impact.** Confirms or refutes our current hypothesis. If confirmed, Path A's P1 patch (topic gate on support documents) targets the right line. If refuted, the patch needs to move.

### Investigation I6 — Refusal-rate simulation against production log  **[CAVEAT from I1]**

> **Caveat.** I1 found that Práctica/Expertos content isn't ingested today. Any refusal-rate number produced from today's corpus will therefore be high *by construction* — the system can't answer operational questions because the operational content isn't there. This investigation should still run, because its *shape* (where refusals concentrate) is informative even when its *level* isn't. But the absolute number needs to be re-measured after I1b/I4 ship any ingestion fix.

- **Question it answers.** If we ship the "minimum evidence → refuse" gate, what fraction of real user queries become refusals?
- **Why it matters.** Refusal is strictly safer than hallucination, but refusal at scale is its own product problem. If 35% of production queries get a "please reformulate," we have a usability regression even though we fixed the hallucination issue. Your boss will notice this before the users do.
- **Method.** Sample 500 queries from recent production logs (or from the existing eval corpora, if prod logs aren't available). Replay each through the retriever only. For each, compute what a proposed minimum-evidence gate would do: proceed or refuse. Report the distribution.
- **Time budget.** 1 day.
- **Deliverable.** A histogram: refusal rate at several evidence thresholds (e.g., require ≥1 primary article; ≥3; ≥1 primary OR ≥5 topic-matched chunks). Calibration data for tuning the gate.
- **Decision impact.** Sets the refusal threshold. Also flags queries where a strict gate would refuse but the legacy system answers fine — those become a candidate subset for "does the legacy answer look good, and if so, why?"

### Investigation I7 — Lia Contadores principle audit

- **Question it answers.** Of Lia Contadores's five anti-hallucination mechanisms, which port cleanly to a graph-native world and which need rethinking?
- **Why it matters.** We already know we want the *principles* (topic is identity, evidence is closed, silence is legal). We haven't been explicit about which specific mechanisms translate to graph idioms and which become incoherent in a graph world. For example: Contadores's filename-prefix classifier has no graph equivalent — but a TopicNode full-text-index query does. Contadores's `path_prefix` filter has no graph equivalent — but an edge-traversal constraint does. Without this mapping, Path B risks porting the wrong pieces.
- **Method.** Take each of Contadores's five mechanisms from the prior architect study. For each, specify: (a) what the equivalent graph idiom is, (b) what code changes that implies, (c) whether any ingestion changes are required, (d) what it costs if we skip it.
- **Time budget.** Half a day (builds on existing architect reports).
- **Deliverable.** A five-row mapping table. Feeds directly into whichever execution plan we choose.
- **Decision impact.** Refines the specifics of Path B and C. Doesn't change which path we pick — just what that path contains.

---

## 7. Risks if we skip this investigation phase

| Risk | What it looks like |
|---|---|
| We ship Path A, topic gate starves Práctica, answers become less useful even though they stop hallucinating. | Users complain about "the system used to tell me how to file with UGPP, now it just refuses." |
| We ship Path B, discover mid-rebuild that corpus has ingestion gaps no rebuild could have fixed, lose 2 weeks. | The new system refuses at the same rate as the old one and for the same questions, because the documents aren't there at all. |
| We ship the classifier keyword hardening, discover 20 *other* topics have thin coverage, spend the next three weeks on whack-a-mole. | Weekly bug reports: "it routed my IVA question to income tax," scope creep on a supposedly one-week project. |
| We ship a strict minimum-evidence gate, refusal rate climbs to 35%, product management pushes back, we flip the flag off, we're back where we started. | Reactive flag-flipping, no net progress. |
| We re-run the A/B with the environment fixed, discover TEMA-first underperforms legacy on a real comparison, and only then realize the whole v5 design was aimed at the wrong problem. | A hard conversation much later than it should have been. |

All of these risks are cheap to eliminate in the investigation phase (days) and expensive to recover from in the execution phase (weeks).

---

## 8. Decision gates — how investigation outcomes route to execution paths

| Investigation | If outcome is… | …then lean toward |
|---|---|---|
| I1 (tagging audit) | Coverage ≥ 80%, accuracy ≥ 85% | Any path is viable. |
| I1 (tagging audit) | Below either threshold | **Fix tagging before any strict gate.** Slot an `ingestionfix_v6_tagging` task ahead of A/B/C. |
| I2 (classifier coverage) | ≤ 5 red topics | Path A as planned. |
| I2 (classifier coverage) | > 10 red topics | Path C — take the structural classifier redesign with us. |
| I3 (fixed A/B re-run) | TEMA-first clearly beats legacy | Path B or C — the graph bet is paying off, invest more. |
| I3 (fixed A/B re-run) | No measurable difference | Path A — TEMA-first doesn't earn its complexity yet, patch what we have. |
| I4 (corpus completeness) | < 10% ingestion gaps | Retrieval-path focus is correct. |
| I4 (corpus completeness) | > 25% ingestion gaps | **Corpus completion is the priority**, above any retrieval work. |
| I5 (contamination trace) | Matches our hypothesis | Path A's P1 patch location is correct. |
| I5 (contamination trace) | Different root cause | Re-scope the P1 patch to the actual code location. |
| I6 (refusal simulation) | < 15% refusal rate at chosen threshold | Ship the refusal branch. |
| I6 (refusal simulation) | > 25% refusal rate | Soften the gate, and treat high refusal rate as a retrieval-quality signal, not a gate problem. |
| I7 (principle audit) | 3+ mechanisms port cleanly | Path B is credible. |
| I7 (principle audit) | ≤ 2 mechanisms port cleanly | Path A or C — we have less Contadores wisdom to translate than we thought. |

---

## 9. Success criteria for this investigation phase

We exit the investigation phase when **all seven investigations have closed their open questions AND we can answer these four questions with evidence, not intuition**:

1. *Is the corpus complete enough that retrieval-tuning is the right intervention?* (I4)
2. *Does TEMA-first retrieval deliver on its hypothesis when actually run?* (I3)
3. *Is the current topic metadata on chunks trustworthy enough to be a filter key?* (I1)
4. *How far off is the classifier, and is a keyword patch or a redesign the right move?* (I2, I7)

If any of those four can't be answered confidently, the investigation isn't done.

---

## 10. Timeline and ownership (indicative)

Investigations are independent and can parallelize. A single engineer full-time could complete the set in roughly one calendar week. Paired with another engineer, half of that.

| Day | Activity |
|---|---|
| 1 | I1 + I2 in parallel. Morning audit + afternoon scan. |
| 2 | I3 (fixed A/B re-run) + I7 (principle audit, can overlap). |
| 3 | I4 (corpus completeness), I5 (contamination trace) in parallel. |
| 4 | I6 (refusal-rate simulation). |
| 5 | Synthesis. Write up `ingestion_tunningv2.md` as the execution plan, with the path chosen and justified. |

End of week: execution begins with evidence, not instinct.

---

## 11. What gets shipped as code from this document

**Nothing.** That is deliberate. The output of this document is another document: `docs/next/ingestion_tunningv2.md`, which will be the execution plan — chosen path, scoped patches, flags, rollout sequence — justified by the findings of the investigations above.

---

## Appendix A — Primary references and evidence

### In this repo
- `docs/next/ingestionfix_v5.md` — most recent prior design, introduced TEMA-first.
- `docs/orchestration/orchestration.md` — authoritative env/flag matrix and hot-path description.
- `src/lia_graph/pipeline_d/retriever_falkor.py:99–139` — TEMA-first implementation.
- `src/lia_graph/pipeline_d/topic_safety.py:102–152` — the misalignment detector that worked.
- `src/lia_graph/pipeline_d/answer_support.py:284–417` — the contamination vector.
- `src/lia_graph/topic_router.py` + `topic_router_keywords.py` — the classifier layer.
- `config/subtopic_taxonomy.json` — the authoritative topic set.
- `scripts/evaluations/run_ab_comparison.py` — the A/B harness that needs the env-strict preflight.
- `evals/` — existing gold/retrieval benchmarks; candidate sources for I4 and I6.

### Outside this repo (read-only)
- `github.com/avas888/Lia_contadores` — ancestor repo. Specifically: `src/lia_contador/topic_guardrails.py` (topic-scope filter), `src/lia_contador/ingestion_classifier.py` (filename-prefix classifier), `src/lia_contador/low_confidence.py` (refusal gate), `src/lia_contador/pipeline_c/evidence_claim_pack.py` (number-drift detection), `prompts/answer_policy_es.md` (defensive citation allow-list), `prompts/quality_critic_es.md` (draft-stage critic).

### Deliverables of this investigation
- `docs/next/ingestion_tunningv1_findings.md` (new, to be written at end of week) — consolidated findings from I1–I7.
- `docs/next/ingestion_tunningv2.md` (new, to be written at end of week) — the execution plan.

---

## Appendix B — Glossary for the non-technical reader

- **RAG (Retrieval-Augmented Generation).** A system that retrieves relevant documents from a corpus and feeds them to a language model so the model's answer is grounded in those documents rather than its training data. Lia Graph is a RAG system.
- **Knowledge graph.** A database where facts are stored as nodes and relationships (edges) between them. Here, each normative article is a node, each topic is a node, and "this article is about this topic" is an edge.
- **Topic.** The subject area of a question or document — for example, IVA (VAT), labor, withholding, compliance (SAGRILAFT). The taxonomy has 39 of them.
- **Chunk.** A paragraph-sized piece of a document, the atomic unit of retrieval.
- **Classifier.** The component that decides which topic a user's question belongs to.
- **Hallucination.** When a language model generates content that isn't grounded in the retrieved evidence.
- **Contamination.** A specific hallucination pattern where retrieval surfaces an unrelated chunk (biofuels) and the model dutifully uses it in answering an unrelated question (part-time labor).
- **Refusal.** The system returning "I can't answer this confidently" instead of guessing. In this domain, refusal is usually the correct safety behavior when evidence is weak.
- **Flag / gate.** A configuration switch that turns a feature on or off at runtime, so we can ship changes safely and reverse them without redeploying.
- **TEMA edge.** In this graph specifically, an edge from a topic node to an article node indicating the article is primarily about that topic. 2,361 of these exist today.

---

*End of `ingestion_tunningv1.md`. Next document in this sequence: `ingestion_tunningv1_findings.md` (investigation outputs), then `ingestion_tunningv2.md` (execution plan).*
