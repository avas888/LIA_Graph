# Make-or-break — Lia Graph

> **Status:** decision document, opened 2026-04-26 evening after the §1.G SME validation run.
> **Audience:** founder + technical lead. The first section is for the founder; the rest is for whoever owns the engineering call.
> **Authors (panel):** the engineering, product/risk, and brand perspectives are collapsed into one voice; where they disagree it's flagged inline.

---

## Para el jefe — resumen en lenguaje llano

Acabamos de correr una validación independiente. Un contador externo revisó las 36 respuestas que LIA generó para 36 preguntas que él mismo escribió, cubriendo los 12 temas más importantes del producto. **Cero respuestas estaban listas para enviar a un cliente sin revisión humana.** Seis eran directamente peligrosas (le costarían dinero o credibilidad profesional al contador que las cite). Diez fueron honestas y dijeron "no sé" cuando deberían haber sabido. Catorce fueron parcialmente útiles pero con errores de fondo. Solo seis pasaron como "el contador puede usarlas como insumo, pero le toca completar."

**El sistema NO está listo para lanzarse.** Lanzar como está produciría un incidente de cliente la primera semana — cada contador que use LIA va a tropezar con al menos una respuesta peligrosa, y en este oficio una respuesta peligrosa es plata perdida o sanción profesional. Un solo tweet diciendo "LIA me hizo perder $50M" mata la marca y la empresa.

**Pero el producto sí se puede salvar.** Los huesos del sistema funcionan. El corpus tiene la información. El problema NO es que la inteligencia artificial sea mala — el problema es que (a) tenemos contenido viejo mezclado con contenido nuevo sin marcas de cuál está vigente, (b) no inyectamos los valores que cambian cada año (UVT, tarifas, plazos) de forma controlada, (c) hay temas registrados en la configuración que NO tienen ningún documento en el corpus (literalmente fantasmas), y (d) cuando el sistema no encuentra evidencia, en vez de honestamente abstenerse, **inventa una respuesta genérica** que parece autorizada pero no lo es.

**La recomendación de este panel: SALVAR, con un alto en el camino de 8 a 12 semanas para arreglar cinco defectos estructurales específicos. NO lanzar mientras tanto. NO seguir afinando incrementalmente.**

El costo de salvar es real: 2 a 3 ingenieros enfocados durante 8–12 semanas (≈ USD 80–180K en costos directos según tarifa). El costo de NO salvar y lanzar es la pérdida de la marca, lo cual liquida la inversión hecha hasta hoy. El costo de liquidar es perder los 6+ meses ya invertidos pero conservar el capital de marca para una próxima apuesta.

**La pregunta que toca contestar esta semana:** ¿hay 8–12 semanas más de runway? Si la respuesta es sí, salvamos. Si la respuesta es no, liquidamos antes de lanzar para no quemar la marca.

---

## 1. The verdict in one table

The SME's per-question verdict (their own rubric, applied to the 36 verbatim answers in `evals/sme_validation_v1/runs/20260427T003848Z/verbatim.md`):

| | Count | What it means |
|---|---:|---|
| ✅ Ready to send to client | **0** | None |
| 🟨 Useful as input, accountant must complete | 6 | 17% |
| ⚠️ Misleading, contains errors of substance | 14 | 39% |
| ❌ Wrong / dangerous to cite | 6 | 17% |
| 🚫 Honest refusal (system declined) | 10 | 28% |

**Headline reads:**

- **0/36 entregable.** No answer survived expert review unaltered.
- **20/36 (56%) require active correction or are dangerous.** This is not a "polish" problem.
- **10/36 (28%) refusals are mostly honest** but several are refusals on canonical questions whose answers exist in the corpus — meaning the retriever is failing on the easy stuff.
- **The 6 ❌ "wrong" answers are uniformly confident, well-cited, well-formatted, and inverted on the substance.** This is the most dangerous failure mode a RAG can have — confident hallucination wrapped in the visual signature of a correct answer.

The auto-grader (which we ourselves built and tuned) classified the same set as **PARTIAL — 21/36 served_acceptable+**. The auto-grader and the SME diverge by **15 cases**. Every divergence is the auto-grader scoring more leniently than the SME. **Our rubric measures form, not fact.** The SME measures fact. The SME is right.

## 2. Why this happened — the five structural defects

The audit (`docs/learnings/`, `docs/orchestration/`, ~3 hrs of code+corpus reading after the SME report landed) confirms the SME's pattern analysis maps to **five concrete structural defects** in the current system. None of these are addressed by the active backlog (`next_v5.md §1.A–§1.G`); the active backlog tunes other things.

### Defect #1 — No vigencia (temporal-authority) tracking

**What happens.** The corpus contains both `art. 689-1 ET` (derogated 2021) and `art. 689-3 ET` (vigente 2022–2026). The retriever returns either with equal weight. The LLM cites whichever ranks higher lexically. Same pattern: 5-year vs 6-year firmeza, three different versions of the dividend tariff (10% / 15% / 19% / 35% — only the last two are vigente), Ley 1429/2010 (mostly derogated) cited as if current.

**Why it persists.** No mechanism in `pipeline_d/`, `ingestion/`, or `config/` tracks article vigencia. The audit looked specifically: there is no `vigencia_until` field on chunks, no `superseded_by` link in the graph, no demotion in retrieval ranking. The active fix-shape (§1.A multi-topic metadata, §1.B compatible_topics, §1.D topic_boost) all operate on **topical relevance**, not **temporal authority**.

**Impact.** This is the root cause of the most dangerous answers in the SME report. An accountant who cites `art. 689-1 ET` in 2026 looks incompetent. An accountant who applies a 10% dividend tariff when the law has been 19%/35% since 2022 has a malpractice problem.

### Defect #2 — No dynamic parameter injection

**What happens.** UVT, tarifas, plazos, umbrales — values that change every year — live in the corpus as plain text. When the document was indexed, it had UVT 2024 = $47.065. Today is 2026 and UVT is $52.374. LIA still cites the 2024 value because the document still says so.

**Why it persists.** The audit found no parameter-injection mechanism in `src/lia_graph/`. There is a `ui_text_utilities.py:_UVT_REF_RE` pattern that **detects** UVT mentions but doesn't **rewrite** them. There is no canonical "current UVT" registry. When numbers change, every affected document must be re-edited and re-ingested.

**Impact.** Every single answer that cites a UVT amount, a tarifa, a plazo in days/months, or any quota in pesos is at risk of being a year-stale even when the rest of the answer is correct.

### Defect #3 — Hallucinated fallback when retrieval is partial

**What happens.** When the system can't fill a sub-question, it returns the literal string `"Cobertura pendiente para esta sub-pregunta; valida el expediente antes de cerrarla con el cliente."` (confirmed in `src/lia_graph/pipeline_d/answer_policy.py:20-21`). But the LLM polish pass then **synthesizes a "Ruta sugerida" + "Riesgos" wrapper around it that looks authoritative** — and the SME observed that the wrapper consistently veers into facturación electrónica content regardless of the actual question.

**Why it persists.** The `graph_native_partial` mode pipes through the same composer as `graph_native`. The composer doesn't know the difference between "I have evidence and I'm summarizing it" and "I have a placeholder string and I'm dressing it up." There is no anti-hallucination guard at the composition boundary.

**Impact.** A reader sees `**Ruta sugerida** 1. PASO 1 — Identificar si la PYME requiere canalización obligatoria... (arts. paso-a-paso-pr-ctico y posiciones-de-expertos ET).` — a fabricated article reference inside a real-looking template. This is worse than an honest refusal because the reader's eye glides over the substance and trusts the structure.

### Defect #4 — Ghost topics (registered in config, zero corpus)

**What happens.** `tarifas_renta_y_ttd` is registered in `config/topic_taxonomy.json` and `config/article_secondary_topics.json`. The audit grepped `knowledge_base/` for any document tagged with this topic and found **zero matches**. The thin-corpus heartbeat shows `tarifas_renta_y_ttd: SERVED ✅` because the heartbeat probe asks a question that happens to surface ANY chunk mentioning "tarifa." The SME's three properly-scoped questions all refused.

The same audit found `regimen_cambiario` documents only in `knowledge_base/CORE ya Arriba/Documents to branch and improve/to_upload/` — i.e., staging area, not indexed.

**Why it persists.** There is no integrity check between `config/topic_taxonomy.json` (which declares topics exist) and `knowledge_base/` (which contains the actual evidence). The launcher / preflight does not fail when a topic has zero docs.

**Impact.** The product's surface advertises 89 covered topics. The reality is fewer — we don't know how many fewer because we don't measure it. Every ghost topic is a refused-on-arrival client experience.

### Defect #5 — Internal corpus inconsistencies are unmarked

**What happens.** The SME found three different versions of the dividend tariff table (art. 242 num. 1) in three different sections of the corpus. They contradict each other. Nothing marks one as canonical and the others as superseded. The retriever returns whichever ranks; the LLM cites confidently.

**Why it persists.** No editorial discipline in the corpus. Documents were ingested as written, with no "this is the authoritative version" stamp, no "this section is now superseded by section X" cross-link.

**Impact.** Even with a perfect retriever and a perfect LLM, the answer can be wrong because the input itself is internally contradictory.

---

## 3. The two paths

### Path A — Save (recommended)

**Premise.** The bones of the system are real. The retriever, the coherence gates, the multi-mode runtime, the diagnostics surface, the ingest pipeline — all of these are working production-grade engineering. The product's failure is not a failure of intelligence; it is a failure of (i) editorial discipline on the corpus and (ii) a missing layer of vigencia / parameter / anti-hallucination guards. Both are addressable in 8–12 weeks of focused work.

**Outcome on success.** A product that returns ✅ correct + 🟨 useful with caveats on ≥ 24 of 36 SME questions (re-run §1.G as gate), and produces zero ❌ confidently-wrong answers in 100 production-realistic questions (new gate). At that point, soft-launch to a controlled cohort (10–20 friendly accountants) with explicit "beta — review answers before citing" framing, instrument for client incidents, iterate.

**Cost.** 2–3 senior engineers for 8–12 weeks. ~USD 80–180K depending on rates. Plus opportunity cost: 8–12 weeks of no revenue, no growth, founder energy concentrated on rebuild not selling.

**Risks.** (i) The fix takes longer than 12 weeks. (ii) After the fix, residual quality remains below client-grade (e.g. 18/36 instead of 24/36). (iii) Competitive landscape shifts during the rebuild window. (iv) Engineer burn — the team has been pushing hard already.

### Path B — Liquidate

**Premise.** The accumulated technical debt + corpus debt + brand risk is too large to repay before runway runs out. The honest move is to call it now, conserve remaining capital, preserve relationships and reputation, and either (i) start fresh with the lessons learned, or (ii) redirect capital to a different bet.

**Outcome.** No product launch. Founders walk away with brand intact, can credibly say "we built it, we tested it with real accountants, the answer wasn't ready for production responsibility, we did the right thing." That story actually plays well for next-fundraise credibility.

**Cost.** Loss of 6+ months of investment to date. Loss of team momentum. The SME relationship + the captured corpus + the engineering IP all become salvage value rather than going-concern value.

**Risks.** (i) Fixed costs (SME relationship, cloud infra, severance) eat the savings vs. the rebuild path. (ii) Founder optionality narrows — "tried this, killed it" is a mark on the resume even when it's the right call. (iii) The architecture and learnings have real value that gets lost.

### Where the panel disagrees

- **The engineer says SAVE.** The defects are concrete and bounded. None of them require novel research; all five are well-understood patterns with proven solutions in industry. 8–12 weeks is a realistic estimate from someone who has read the codebase end-to-end.
- **The product/risk perspective says SAVE WITH HARD CHECKPOINTS.** Don't commit to the full rebuild blindly — set a 4-week midpoint gate. If the vigencia + injection layer isn't producing measurable gains by week 4, the project is in trouble, and we should stop rather than continue throwing money at it.
- **The brand/risk perspective says LIQUIDATE IF RUNWAY IS THIN.** Launching a product that gives accountants confidently-wrong tax advice is a bigger brand wound than walking away. If the rebuild can't be funded with breathing room, kill it now while we can still control the narrative.

**Combined recommendation.** SAVE, but with an explicit week-4 kill switch tied to a measurable midpoint result. If the midpoint metric isn't hit, the brand/risk perspective wins and we liquidate cleanly.

## 4. The save plan — 12 weeks, 5 workstreams

If SAVE is chosen, this is the work. The order matters: workstreams 1 and 2 must finish before 3 and 4 are even worth attempting; 5 runs in parallel throughout.

### Workstream 1 — Vigencia layer (weeks 1–4, 1 senior engineer)

**Deliverable.** Every chunk and every article in the corpus carries a `vigencia_status` (one of `vigente`, `derogado`, `suspendido`, `transicion`) and an optional `superseded_by` reference. The retriever's RRF formula multiplies by `0` for `derogado` and by `0.3` for `suspendido` / `transicion` unless the planner explicitly requested historical context.

**Subtasks:**
- A vigencia ontology: define the 4 states + the rules for transition (e.g. "an article cited by a Decreto Reglamentario from 2025 stays vigente even if its enabling Ley is from 2010").
- A reviewer interface (CLI, not GUI — the operator uses it once during the migration) that walks every article and asks the SME to assign vigencia_status.
- A migration that adds `vigencia_status` + `superseded_by` columns to Supabase `documents` and `document_chunks`, and `vigencia_status` property to `:ArticleNode` in Falkor.
- Update `pipeline_d/retriever_supabase._hybrid_search` to pass a `vigencia_filter` parameter and update the SQL function to apply the multiplier.
- Tests: 6 SME-curated golden questions whose correct answer hinges on derogated-vs-vigente disambiguation.

**Midpoint gate (week 4).** Re-run the §1.G SME questions on `beneficio_auditoria`, `firmeza_declaraciones`, `dividendos_y_distribucion_utilidades` (the 3 topics where SME found the most vigencia errors). Goal: zero `art. 689-1` citations, zero "6 años" for firmeza, zero pre-Ley-2277 dividend tariffs. **This is the kill-switch metric: if any of those three persist after week 4, the project is in trouble.**

### Workstream 2 — Parameter injection (weeks 1–3, 0.5 engineer)

**Deliverable.** A `lia_graph.parameters` module that exposes current-year canonical values for UVT, tarifa general renta, tarifa dividendos por tramo, plazo de firmeza por escenario, plazos de presentación, etc. The composer's polish pass rewrites any value in the answer that the parameter table can disambiguate.

**Subtasks:**
- A `config/canonical_parameters_2026.yaml` (and `_2025.yaml`, `_2024.yaml`) with every parameter that changes annually.
- A `parameters.py` module that resolves "the value this answer should cite, given the year context."
- A composer-side rewrite pass that detects `$XX UVT`, `$X.XXX.XXX`, `XX%` patterns and verifies them against the canonical table, flagging mismatches.
- Tests: 8 questions whose correct answer requires a 2026 parameter the corpus only has at 2024 value.

### Workstream 3 — Anti-hallucination guard (weeks 4–6, 1 engineer)

**Deliverable.** When `graph_native_partial` mode produces a sub-question with `Cobertura pendiente`, the composer is forbidden from generating "Ruta sugerida" / "Riesgos" / fabricated article references for that sub-question. Instead, the response surfaces an explicit "couldn't answer this part — recommend escalation."

**Subtasks:**
- Refactor `pipeline_d/answer_policy.py` so partial-mode placeholders propagate as a typed signal, not just text.
- Update `pipeline_d/answer_synthesis_*` so partial sub-questions render an honest "no answer available" stub, NOT a confident-looking template.
- Update the LLM polish prompt so the polish stage cannot resurrect content for partial sub-questions.
- Regression test: 12 questions known to trigger partial mode; verify zero fabricated article references in the polished output.

### Workstream 4 — Corpus completeness audit + ghost-topic kill (weeks 5–8, SME + 0.5 engineer)

**Deliverable.** Every topic registered in `config/topic_taxonomy.json` has a minimum of N documents in `knowledge_base/` (recommended N = 5 for thin-corpus topics). Topics that don't meet the floor are either populated (preferred) or de-registered with an explicit "this topic is not in scope for v1" status.

**Subtasks:**
- Audit script: for each of the 89 topics, count documents tagged with that topic in `knowledge_base/`, output a table.
- SME triage: for each topic with < 5 docs, decide (a) populate (with a documented work item to add docs) or (b) de-register.
- Populate `tarifas_renta_y_ttd` (and any other ghost topic) with at least the canonical Ley/Decreto/concepto for the major rules — minimum 5 docs, ideally 10.
- Move all `to_upload/` content for `regimen_cambiario` into the indexed corpus, validate retrieval, re-run SME questions on this topic.
- Add a launcher preflight that fails when any registered topic has zero docs.

### Workstream 5 — Golden-answer regression suite (weeks 1–12, ongoing, 0.25 engineer + SME)

**Deliverable.** A growing suite of 50+ canonical questions, each with an SME-verified correct answer, that runs on every PR. PRs that regress any golden answer cannot merge.

**Subtasks:**
- SME drafts 50 golden questions, paced 5/week starting week 1, expert-verified and committed under `evals/golden_answers_v1/`.
- Each golden question has: (a) the question, (b) the canonical correct answer in markdown, (c) the citation list it must include, (d) the topic_key, (e) a list of "must-not-say" patterns (e.g. "for `firmeza_declaraciones_basic`, must not contain '6 años'").
- A judge (LLM-based, prompted to be strict) compares each LIA answer against the canonical answer + must-not-say list; emits PASS / SOFT_FAIL / HARD_FAIL.
- CI gate: any HARD_FAIL on the golden suite blocks merge.
- This is the long-term quality net. Without it, every fix risks regressing something else.

### What we deliberately are NOT doing

These were considered and rejected:

- **No more incremental gates** (`§1.H`, `§1.I`, etc.). The §1.A–§1.G chain demonstrated that incremental retrieval tuning hits diminishing returns once the corpus + vigencia layer is broken. We stop adding gates until the foundation is fixed.
- **No threshold relaxation.** Per `feedback_thresholds_no_lower.md` — the bar stays at "the answer must be safe to send to a client." If we don't meet it, we don't ship; we don't lower it.
- **No "soft launch with disclaimer".** The disclaimer doesn't transfer the risk — accountants who use the tool will read past the disclaimer. The first incident becomes a brand wound regardless of what the disclaimer said.
- **No corpus expansion until vigencia layer is in.** Adding more documents to a corpus that doesn't track vigencia just multiplies the contamination surface.
- **No retrieval rewrite.** The retriever architecture is sound. The fix is in the metadata it operates on, not in the algorithm itself.
- **No LLM model upgrade as a first-line fix.** The errors are not "the model is too dumb" errors — they are "the model is fed contradictory or stale evidence" errors. Better evidence trumps a better model in this failure mode.

## 5. Decision criteria — when to call it

This panel recommends three explicit checkpoints:

**Week 4 — Vigencia layer midpoint.** Re-run SME questions on the 3 most-affected topics (`beneficio_auditoria`, `firmeza_declaraciones`, `dividendos_y_distribucion_utilidades`). Required result: zero stale-article citations, zero stale-tarifa citations. **If we miss this, we are not on track to fix the system; recommend honoring the brand/risk perspective and liquidating before further sunk cost.**

**Week 8 — Ghost-topic + anti-hallucination midpoint.** Re-run SME questions on all 12 topics. Required result: ≥ 18/36 answers in 🟨 or better per SME rubric (50% threshold), and zero fabricated article references on any sub-question. **If we miss this, the rebuild's scope was wrong; revisit the plan, do not extend timeline blindly.**

**Week 12 — Final gate.** ≥ 24/36 answers in 🟨 or better, zero ❌ in the verbatim. Plus the golden-answer suite (50 questions) at ≥ 90% PASS, zero HARD_FAIL. **If we hit this, we earn a soft-launch to 10–20 friendly accountants with instrumented feedback.** If we don't, we have the data to make an informed liquidate-vs-extend call rather than a panic call.

## 6. What to do this week

If the founder agrees with SAVE:

1. Commit publicly to the team that we are NOT shipping in the next 12 weeks. This stops side-conversations about partial launches.
2. Formally pause the §1.A–§1.G fix-track. The work done is not lost; it lives in `next_v5.md` and the closed gates remain shipped. We just stop adding to the chain.
3. Open `docs/re-engineer/workstreams/` and turn the five workstreams above into individual tracker docs with named owners and weekly checkpoints.
4. Schedule the SME for two sessions: vigencia ontology design (workstream 1, week 1) and golden-answer authoring kickoff (workstream 5, week 1). The SME is the rate-limited resource; book them now.
5. Re-frame the `aa_next/` planning cadence around the five workstreams instead of the §1.x gates.

If the founder leans LIQUIDATE:

1. Decide before any further engineering spend. Every week of continued work that ends in liquidation is wasted runway.
2. Plan the wind-down: comms to SME + early accountants, IP archival, brand statement (frame as "responsible decision after independent expert validation," not "we failed").
3. Salvage value: the SME report, the codebase, the captured 7,883-article corpus, and the architectural learnings from this cycle have real worth — package them for either a future bet or a sale.

If the founder is undecided:

- **Do NOT default to "ship and see."** That is the worst option. It commits to the action with the highest brand-damage tail risk while pretending to defer the decision.
- A 1-week sprint to firmer up the vigencia + injection workstream estimates is reasonable. After that the call is binary.

---

## Appendix — pointer table

| Source | Where | What it adds |
|---|---|---|
| SME verbatim review | (provided in conversation 2026-04-26 evening) | The 36-question expert verdict |
| Auto-grader output | `evals/sme_validation_v1/runs/20260427T003848Z/report.md` | The PARTIAL=21/36 verdict that diverges from SME |
| Verbatim chat answers | `evals/sme_validation_v1/runs/20260427T003848Z/verbatim.md` | The 36 word-for-word responses |
| Architecture map | `docs/orchestration/orchestration.md` | Current runtime + env matrix + change log |
| Retrieval line-by-line | `docs/orchestration/retrieval-runbook.md` | What the retriever does today; gap #1 closed by §1.D |
| Refusal decision tree | `docs/orchestration/coherence-gate-runbook.md` | Where each `fallback_reason` originates and fix candidates |
| Past lessons | `docs/learnings/{retrieval,ingestion,process}/*.md` | 24 closed fixes + open gaps; nothing in here addresses the 5 defects |
| Active fix track (now paused) | `docs/aa_next/next_v5.md` | The §1.A–§1.G chain; relevant for context but not the path forward |
| Hybrid_search overload | `docs/learnings/retrieval/hybrid_search-overload-2026-04-27.md` | The infrastructure bug we cleared today, an example of the kind of defect-of-defects the §1.G run surfaced |

---

*v1, drafted in one session 2026-04-26 evening after the §1.G SME validation. Open for amendment by anyone on the team — but amend by adding a new section, not by softening the verdict.*
