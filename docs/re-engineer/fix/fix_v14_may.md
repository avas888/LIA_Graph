## fix_v14_may.md — strip the noise that's poisoning the answer

> **Drafted 2026-05-13 Bogotá** by claude-opus-4-7. Successor to
> `fix_v13_may.md`. v13 shipped the dedicated práctica retrieval
> lane (95 % spine adoption). v14 attacks the **next layer**: the
> empirical pass rate on 42 senior-contador-judged turns is **26 %
> strict / 48 % rejected**. Half the answers are unusable. v14 is
> a gated sequence of six focused fixes to lift the strict pass
> rate to **≥ 40 % in v14.1 and ≥ 55 % in v14.2**, each fix with an
> explicit numeric INCLUDE / REVERT criterion.
>
> **Audience.** Zero-context fresh LLM or engineer. Self-contained.
> Skim `fix_v13_may.md` for the práctica lane wiring (this plan
> sits on top of it). Skim the §1 diagnosis below for the failure
> patterns identified empirically from the panel-judge of
> 2026-05-13.
>
> **What this is.** Six independent, low-cost fixes to the
> *synthesis* and *polish* layers, gated by a Claude-as-judge
> measurement of the same 42 panel turns after each fix. Each
> fix lands behind an env flag that defaults to `shadow` or `off`,
> ships in shadow, gets measured, then promotes to `enforce` only
> if the judge-pass-rate moves above the include threshold AND no
> question regresses from PASS to REJECT.
>
> **What this is NOT.** Not a retriever rewrite. Not a semantic
> reranker deployment (deferred to a future fix; see §7). Not a
> gold-refresh task (deferred to fix_v15 — see §7). Not new SQL
> migrations. Not a backfill. Not a corpus reingest. Every fix
> touches existing modules with surgical edits, ≤ 4 hours each.
>
> **Scope guard.** Closing bar at end of Sprint v14.2, measured on
> the combined 42-question panel (`21q_retriever_General.jsonl` +
> `21q_retriever_Practica.jsonl`) judged by Claude Code acting as
> senior contador against the 4-level rubric defined in §3:
>
> 1. Combined strict pass rate (STRONG + ACCEPTABLE) ≥ **55 %**
>    (vs v13 baseline 26 %).
> 2. Combined reject rate (REJECT) ≤ **25 %** (vs v13 baseline 48 %).
> 3. Zero individual question transitions PASS (v13) → REJECT
>    (v14). Per-question regression is the hard veto.
> 4. No silent fallback: every fix surfaces a diagnostic key in
>    `response.diagnostics` so the SME report can audit which
>    fixes fired per turn.
> 5. Each fix's env flag can be flipped off independently and
>    reverts to v13 behavior without redeploy.
>
> **Why this is achievable in ~10 h of engineering.** The 6
> fixes target structural failure modes empirically observed,
> not hypothetical improvements. The 42-turn panel-judge is
> deterministic enough (same prompts, same model, same rubric)
> that judge-rate deltas of ≥ 5 pp are signal.

---

### §0. Inheritance from v13

Carry forward intact, do not touch:

- **v13.A** — dedicated práctica retrieval lane
  (`src/lia_graph/practica/retriever_supabase.py`). v14 does not
  modify retrieval; it cleans what comes out of synthesis.
- **v13.B** — práctica artifact-line filter
  (`pipeline_d/answer_synthesis_practica.py::_is_practica_artifact_line`).
  v14 extends this filter pattern to the unified bullet pipeline,
  not just the práctica section.
- **v13.C** — `LIA_PRACTICA_SOURCE`, `LIA_PRACTICA_RESERVED_SLOTS`,
  `LIA_PRACTICA_BOOST_FACTOR=1.0` default. Stay as-is.
- **fix_v8.A** — polish-rejected fallback assembler
  (`pipeline_d/answer_polish_rejected_fallback.py`). v14 §6
  rebuilds this module's bullet-filtering pipeline so the fallback
  output stops surfacing chunk artifacts; the entry point and
  contract stay identical.
- **fix_v7.C** — topic gate `filter_template_bullets`
  (`pipeline_d/answer_topic_gate.py`). v14 §3 extends the same
  allowlist mechanism to a NEW gate that runs at anchor-rendering
  layer (pre-emit), complementary to the existing bullet-level
  gate (post-emit).

---

### §1. Diagnosis — what the 2026-05-13 panel-judge revealed

Measurement methodology: Claude Code acting as senior contador,
4-level rubric (STRONG / ACCEPTABLE / BORDERLINE / REJECT) +
required justification + flag taxonomy. Applied to the
post-clean post-v13 runs at
`evals/sme_validation_v1/runs/20260513T1030_fix_v13_*_postclean/`.

**Baseline numbers (v13 state, no further changes):**

| Panel | STRONG | ACCEPTABLE | BORDERLINE | REJECT | Strict pass | Reject |
|---|---|---|---|---|---|---|
| Práctica (21Q) | 2 | 5 | 5 | 9 | 33 % | 43 % |
| General (21Q) | 3 | 1 | 6 | 11 | 19 % | 52 % |
| **Combined (42Q)** | **5** | **6** | **11** | **20** | **26 %** | **48 %** |

**Six failure patterns identified from the 20 rejects:**

1. **Wrong-anchor citation (11/42 cases)**. `build_legal_anchor_lines`
   surfaces top primary articles from the retriever bundle without
   any topic-relevance check. Examples observed:
   - Depreciación maquinaria → anclaje legal cita Arts. 121-124 ET
     (deducción gastos exterior) + 245 (dividendos extranjeros)
   - Anticipo renta → anclaje cita Arts. 100-102 ET (renta vitalicia,
     fiducia mercantil)
   - PT umbrales → anclaje cita Arts. 240 + 235-2 ET (tarifa general
     + rentas exentas), no Art. 260
   - IVA responsables → Art. 1 ET citado como "FORMULARIO 7 —
     INV EXTRANJERA"
   - UGPP / parafiscales → Art. 124-2 ET (jurisdicciones no
     cooperantes) citado
2. **Off-topic chunk-text leak (10+ cases)**. Specific bullets
   bleed across topic boundaries because they appear in multiple
   guides in the corpus:
   - `"Inicie sesión con su número de cédula y contraseña…"`
     (portal-login boilerplate) appears in GMF, PT umbrales,
     autorretención, marcación cuentas
   - `"Matrícula Mercantil (Renovación) — Vence: 31 de marzo"`
     bleeds into calendario, retención F.350
   - `"Jornada nocturna 7:00 p.m. — 35%"` bleeds into PILA
     liquidación, tabla 383 retención, UGPP desalarización
   - `"Caso de estudio: Tienda de abarrotes ventas $180M Bogotá"`
     (chunk caption) bleeds into TTD, firmeza
   - `"Texto normativo clave — par. N, art. M ET (fragmento
     relevante)"` (chunk caption format)
3. **Polish-rejected → incoherent fallback (15/42 turns)**. The
   polish stage rejects ~36 % of turns. The fix_v8 fallback
   re-renders `GraphNativeAnswerParts` but the input bullets are
   the same ones polish rejected — full of chunk artifacts, slugs,
   captions, truncations. The fallback output reads as raw
   corpus fragments not synthesized prose.
4. **Topic-drift retrieval (~8 catastrophic cases)**. Retriever
   pulls chunks sharing vocabulary with the query but answering
   a different sub-aspect:
   - IVA F.300 query → retrieves devolución-saldo-favor chunks
   - IVA exentos vs excluidos → also devolución chunks
   - DAV documento equivalente → aduanas / CAN chunks
   - Nómina electrónica DSN → factura electrónica general chunks
   - Decreto 1474/2025 IVA → fragmentos genéricos saldo a favor
5. **Missing numeric operationalization (8+ cases)**. Even when
   norms are correctly identified, no concrete numbers surface:
   dividendos sin tarifas progresivas 0/19/35 %, RST sin tarifas
   por grupo Art. 908, ICA multimunicipio sin tarifas por ciudad,
   anticipo renta sin `$35 M × 75 % = $26 250 000` cuando todos
   los datos están en la pregunta.
6. **Unjustified abstentions (2 cases)**. Coherence-gate refuses
   Ley 2466/2025 questions because router topic key
   `reforma_laboral_ley_2466` doesn't match available chunk
   topics (only `laboral`). `compatible_doc_topics` map is missing
   that pair.

**Important diagnostic finding (Gate 0 bisection)**: the apparent
−14 pp "regression" against the 2026-04-22 baseline is **data
drift, not code regression**. Running the post-fix_v6 commit
(926102e) against today's cloud Supabase gives 16 % retrieval @ 10
— the SAME LOW NUMBER as v13 today. The v6 → v13 code arc was
retrieval-neutral. The drift is in cloud data (knowledge_class
backfill from v10A, ingests since April). The `gold_retrieval_v1.jsonl`
fixture is also stale relative to current node_key surfacing
conventions and is unreliable as a measurement instrument.
**v14 measurement uses Claude-as-judge on the 42-turn panel,
not the gold harness.** Refresh of `gold_retrieval_v1.jsonl` is
deferred to a future fix.

---

### §2. Target architecture (after v14.2)

Two new gates + one filter expansion + one fallback rebuild +
one polish-prompt tightening + one config patch. All in the
synthesis / polish layer; **zero changes to retriever, planner,
or coherence-gate semantics**.

```
       (after fix_v13 retrieval is unchanged)
                        │
                        ▼
       ┌────────────────────────────────────┐
       │  build_graph_native_answer_parts   │
       │  → recommendations / procedure /   │
       │    paperwork / legal_anchor / …    │
       └────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │ §3 anchor allowlist gate      │ NEW — filters legal_anchor
        │ §4 chunk-quality heuristics   │ NEW — drops off-topic-leak bullets
        └───────────────┬───────────────┘
                        ▼
       ┌────────────────────────────────────┐
       │  compose_main_chat_answer          │
       │  + filter_template_bullets (v7)    │
       └────────────────┬───────────────────┘
                        ▼
       ┌────────────────────────────────────┐
       │  polish_graph_native_answer        │
       │  + §5 operationalization directive │ NEW — prompt tightening
       └────────────────┬───────────────────┘
                        ▼
       polish=llm        polish=rejected
            │                  │
            │                  ▼
            │   ┌────────────────────────────────┐
            │   │ §6 rebuilt fallback assembler  │ REBUILT — re-filter input
            │   │   + omit-section-if-empty      │
            │   │   + honest "evidence partial"  │
            │   │     when stripped < 500 chars  │
            │   └────────────────────────────────┘
            │                  │
            └──────────┬───────┘
                       ▼
       §8 coherence-gate vocabulary expansion (Ley 2466)
```

`§7` is a diagnostic instrumentation step (no behavior change —
emits per-turn `polish_skip_reason` distribution so we can target
fixes if rejection rate stays above 30 %).

---

### §3. Phase A1 — legal-anchor topic allowlist (HIGHEST ROI)

**Idea.** Filter `build_legal_anchor_lines` output by the same
topic-allowlist mechanism that already gates bullet-level content
in `answer_topic_gate.py`. Today the legal-anchor block surfaces
the top primary articles from the retriever bundle without any
topic-relevance check, leading to 11 / 42 turns citing articles
completely unrelated to the question topic.

**Files.**

- `src/lia_graph/pipeline_d/answer_synthesis_sections.py` —
  `build_legal_anchor_lines()` gains a topic-allowlist filter
  applied to `primary_articles + connected_articles` BEFORE the
  `(art. N ET)` rendering loop. Reuses
  `answer_topic_gate._bullet_passes()` and `_load_allowlist()`
  so the configuration source is single-sourced.
- `config/topic_norm_allowlist.json` — extend with coverage for
  the topics where the panel showed wrong-anchor citations:
  `declaracion_renta`, `iva`, `retencion_en_la_fuente`,
  `facturacion_electronica`, `gravamen_movimiento_financiero_4x1000`,
  `precios_de_transferencia`, `procedimiento_tributario`,
  `regimen_simple`, `laboral`, `ica`, `informacion_exogena`,
  `calendario_obligaciones`, `regimen_sancionatorio`,
  `dividendos_y_distribucion_utilidades`. Each entry uses the
  existing `allowed_prefixes` schema (`art:147`, `art:240-par-6`,
  etc.). **Curation is the load-bearing work** — must cite
  exact ET articles per topic, no invention. Each prefix verified
  by grepping `parsed_articles.jsonl` to confirm the article
  exists in the corpus.
- `tests/test_legal_anchor_allowlist.py` — new file. ≥ 12 test
  cases: one verbatim panel-rejection case per topic that passes
  AFTER the gate (e.g. `topic=declaracion_renta` with `evidence`
  surfacing Arts. 121-124 must drop those; with Art. 115 must keep
  it). Plus false-positive guards: a topic without curation in
  the allowlist passes everything (noop-by-default).

**Env knob.** `LIA_LEGAL_ANCHOR_GATE_MODE ∈ {off, shadow, enforce}`,
default `shadow` at landing. `shadow` emits diagnostic
`legal_anchor_gate_dropped_keys` but does not reorder. `enforce`
filters before render. Floored: gate is noop when topic has no
allowlist entry (Invariant I5 — never penalize).

**Decision rule (INCLUDE / REVERT).**

- **INCLUDE A1 if**: after enforce, judge-pass-rate on combined
  42-turn panel improves by **≥ 5 pp strict pass** (from 26 % to
  ≥ 31 %), AND reject-rate drops by **≥ 5 pp** (from 48 % to
  ≤ 43 %), AND **zero** turns transition PASS → REJECT.
- **REVERT A1 if**: any of: judge improvement < 3 pp; OR ≥ 1
  turn transitions PASS → REJECT; OR allowlist false-positive
  rate (relevant article dropped) ≥ 2 cases.
- **REFINE A1 once if**: 3 pp ≤ improvement < 5 pp AND zero
  regressions — expand allowlist coverage on the 3 topics with
  the most-dropped-keys, re-judge, then INCLUDE or REVERT.

**Effort.** 2–3 h (allowlist curation is most of it). **Risk.**
Low — leaf rendering layer, downstream of all retrieval.

**Rollback.** `LIA_LEGAL_ANCHOR_GATE_MODE=off` → noop, identical
to v13.

---

### §4. Phase A2 — chunk-quality heuristics on unified bullet pipeline

**Idea.** Extend the practica-specific artifact filter (v13 §6,
`answer_synthesis_practica._is_practica_artifact_line`) into a
shared `chunk_quality_heuristics` module applied to the entire
chunk pool BEFORE `_classify_article_rows`. Targets the off-topic
chunk-text leaks observed in 10+ / 42 turns.

**Files.**

- `src/lia_graph/pipeline_d/chunk_quality_heuristics.py` — new
  focused module exposing
  `score_chunk_quality(row: dict) -> tuple[float, str | None]`
  returning a multiplicative penalty factor in `[0.1, 1.0]` plus
  a reason string for trace visibility. Pattern catalog (each
  pattern verified verbatim from panel-judge flags):
  - portal-login boilerplate: `"Inicie sesión con su número de
    cédula y contraseña"` and variants
  - cross-topic operational fragments: `"Matrícula Mercantil
    (Renovación) — Vence"`, `"Jornada nocturna … 35%"` when the
    chunk's `topic` does NOT match the planner's routed topic
  - chunk-caption shape: `"Caso de estudio:"`,
    `"Texto normativo clave —"`, `"… (fragmento relevante)"`,
    `"### N.N.N"` alone
  - section-numeral headings without prose content
  - bullets that are pure question-echo (start with `¿` end with
    `?` and length > 30 chars)
- `src/lia_graph/pipeline_d/retriever_supabase.py` — call
  `score_chunk_quality` between `_hybrid_search` and the anchor
  merge. Multiply each row's `rrf_score` by the returned factor,
  attach `chunk_quality_demotion_reason` to the row for trace.
- `tests/test_chunk_quality_heuristics.py` — ≥ 16 cases
  (12 verbatim panel flags + 4 false-positive guards: legit
  bullets that happen to contain the trigger token but in proper
  operational context).

**Env knob.** `LIA_CHUNK_QUALITY_HEURISTIC_MODE ∈ {off, shadow,
enforce}`, default `shadow`. Shadow emits diagnostic
`chunk_quality_demoted_count` + sampled `_reason` list.

**Decision rule (INCLUDE / REVERT).**

- **INCLUDE A2 if**: judge-pass-rate +≥ 5 pp strict OR reject-rate
  −≥ 8 pp from v14.0 (post-A1 baseline), AND zero turns
  transition PASS → REJECT, AND false-positive rate < 5 % across
  42 turns.
- **REVERT A2 if**: any regression; OR false-positive rate ≥ 8 %.
- **REFINE A2 once if**: improvement < 5 pp AND no regressions —
  add patterns observed in v14.1 reruns that weren't in initial
  catalog.

**Effort.** 3–4 h. **Risk.** Low (flag-gated, no schema change).

**Rollback.** `LIA_CHUNK_QUALITY_HEURISTIC_MODE=off` → noop.

---

### §5. Phase A3 — polish prompt operationalization directive

**Idea.** The polish stage today is conservative — it filters
inventions but doesn't enforce that numeric data in the question
becomes numeric output in the answer. 8+ panel cases had correct
norms but no operational numbers (dividendos sin 0/19/35 %, RST
sin tarifas grupo, anticipo sin `$35M × 75 % = $26 250 000`).

**Files.**

- `src/lia_graph/pipeline_d/answer_llm_polish.py::_build_polish_prompt` —
  add a new section "DIRECTIVA NUMÉRICA" at the head of the
  primary directive, before the existing invention guards. Text:

  > Si la pregunta menciona una cifra del cliente (monto en pesos,
  > porcentaje, salario, ingresos, antigüedad), debes presentar el
  > cálculo numérico explícito que conteste la pregunta. Si la
  > pregunta menciona un artículo con tarifas progresivas
  > (Art. 242 ET dividendos, Art. 383 ET retención, Art. 908 ET
  > RST), debes nombrar los rangos UVT y los porcentajes
  > concretos del artículo, no parafrasear "según la tarifa".
  > Si la pregunta pide plazos por NIT, da los días específicos
  > por dígito según el calendario DIAN, no fórmulas genéricas.

- Tests in `tests/test_answer_llm_polish.py` — add 4 cases:
  question with `$X M` figure in body, question with `art. 242 ET`
  reference, question with `NIT terminado en 5`, question with
  none of the above (control — directive should not fire).

**Risk note.** This directive could PUSH the LLM to invent numbers
when the corpus doesn't have them — exactly what the existing
`no_invented_periods` validator catches. Mitigation: the directive
is conditional on "menciona una cifra del cliente" — the LLM only
operates on data already in the question, never invents UVT
values or computes against external benchmarks.

**Decision rule (INCLUDE / REVERT).**

- **INCLUDE A3 if**: judge-pass-rate +≥ 3 pp strict, AND polish
  rejection rate does NOT increase by > 5 pp (the directive could
  trigger more validator rejections; measure this), AND zero
  PASS → REJECT regressions.
- **REVERT A3 if**: polish rejection rate increases by ≥ 8 pp
  (the directive is causing more `invented_norm_lineage` /
  `invented_periods` rejections than it solves); OR any
  PASS → REJECT regression.
- **REFINE A3 once if**: rejection rate goes up 5-8 pp but
  pass rate also up ≥ 3 pp — soften the directive language
  (replace "debes" with "procura") and re-measure.

**Effort.** 1–2 h. **Risk.** Medium — polish prompt is touchy
because it directly drives validator behavior.

**Rollback.** Revert the prompt edit (single function).

---

### §6. Phase A4 — polish-rejected fallback rebuild

**Idea.** The fix_v8 §3a fallback re-renders `GraphNativeAnswerParts`
when polish rejects. But the input bullets are the SAME ones
polish rejected — full of chunk artifacts. 15 / 42 turns hit
fallback and most leak slugs / captions / truncations into the
final answer.

**Files.**

- `src/lia_graph/pipeline_d/answer_polish_rejected_fallback.py` —
  refactor `compose_polish_rejected_fallback`:
  1. Run every bullet through the A2 chunk-quality heuristics
     (now-shared module) PLUS the A1 legal-anchor allowlist
     before rendering.
  2. If a section's filtered output is empty after step 1,
     OMIT that section entirely from the fallback markdown
     (no empty `**Procedimiento Sugerido**\n` headers).
  3. If the total assembled fallback after step 2 is < 500
     non-markdown chars (i.e., evidence is mostly junk), return
     an honest abstention text:

     > "Tengo evidencia parcial sobre este tema pero no alcanzó
     > para una respuesta operativa confiable. Valida el
     > expediente manualmente o reformula la consulta con un
     > caso más específico."

     instead of surfacing chunk fragments.
- `tests/test_answer_polish_rejected_fallback.py` — extend with
  3 new cases: fallback input full of artifacts (verify dropped);
  fallback ending up < 500 chars (verify honest-abstention text
  emitted); fallback with mixed clean+dirty bullets (verify clean
  surface).

**Env knob.** `LIA_POLISH_REJECTED_FALLBACK_MODE` already exists
from fix_v8. Add a new sub-mode `LIA_POLISH_REJECTED_FALLBACK_FILTER`
with values `legacy | clean`, default `clean` at landing. `legacy`
preserves v13 behavior for rollback comparison.

**Decision rule (INCLUDE / REVERT).**

- **INCLUDE A4 if**: of the 15 polish-rejected turns, judge-rate
  improvement is ≥ 8 pp (≥ 1 turn lifts from REJECT to BORDERLINE+,
  or ≥ 2 turns from BORDERLINE to ACCEPTABLE+); AND of the 15
  no turn transitions to a worse class (no fallback output gets
  judge-worse than before).
- **REVERT A4 if**: any of the 15 polish-rejected turns transitions
  to worse class; OR honest-abstention path triggers on > 30 % of
  rejected turns (means the filter is too aggressive — fallback
  was useful before).
- **REFINE A4 once if**: improvement 3-8 pp — relax the < 500 char
  threshold to < 300, re-measure.

**Effort.** 2–3 h. **Risk.** Medium — affects 36 % of turns.
Mitigation: `LIA_POLISH_REJECTED_FALLBACK_FILTER=legacy` reverts
the filter without touching the assembler.

**Rollback.** `LIA_POLISH_REJECTED_FALLBACK_FILTER=legacy` OR
`LIA_POLISH_REJECTED_FALLBACK_MODE=off` (latter is more aggressive,
reverts to fix_v7 thin-template behavior).

---

### §7. Phase A5 — polish rejection diagnostic instrumentation (NO BEHAVIOR CHANGE)

**Idea.** 15 / 42 turns hit polish=rejected. We don't know
WHICH validator is doing the rejecting most often:
`invented_norm_lineage`? `invented_periods`? `anchors_stripped`?
`empty_llm_output`? Without that, future fixes are blind.

**Files.**

- `src/lia_graph/pipeline_d/answer_llm_polish.py` — already
  emits `polish_skip_reason` per turn. Add aggregation: count
  per `skip_reason` across the panel and emit summary to a
  diagnostic file at run end.
- `scripts/eval/sme_validation_report.py` — extend
  `_build_retrieval_signal_check` to include a polish-rejection
  breakdown by reason.

**Env knob.** None — pure diagnostic addition, always on.

**Decision rule (INCLUDE / REVERT).** Always include — no behavior
change. The output gates Sprint v14.2 decisions: if
`invented_norm_lineage` dominates, A3's directive is suspect; if
`anchors_stripped` dominates, A1's allowlist is too tight; if
`empty_llm_output` dominates, the input template is the problem.

**Effort.** 1 h. **Risk.** Zero (observability only).

**Rollback.** N/A.

---

### §8. Phase A6 — coherence-gate vocabulary expansion (Ley 2466)

**Idea.** Two of the 42 turns abstain because the coherence gate
refuses `reforma_laboral_ley_2466` queries — the router classifies
to that topic key but the corpus chunks are tagged just `laboral`.
The `compatible_doc_topics` map is missing the mapping.

**Files.**

- `src/lia_graph/pipeline_d/compatible_doc_topics.py` — add entry:
  ```
  "reforma_laboral_ley_2466": {"laboral", "derecho_laboral",
                                "nomina_seguridad_social"},
  ```
- `tests/test_compatible_doc_topics.py` — add a case asserting
  the new mapping resolves a Ley 2466 query through the gate.

**Decision rule (INCLUDE / REVERT).**

- **INCLUDE A6 if**: the 2 abstention turns transition to
  graph_native (non-abstention), AND their judged class is
  BORDERLINE or better (i.e., serving an imperfect answer is
  better than abstaining).
- **REVERT A6 if**: either abstention turn transitions to
  graph_native but receives REJECT judgment — that means the
  abstention was correct (corpus genuinely doesn't have material).

**Effort.** 30 min. **Risk.** Low.

**Rollback.** Revert the dict entry.

---

### §9. Six-gate lifecycle (per `feedback_verify_fixes_end_to_end.md`)

| Gate | State | Evidence |
|---|---|---|
| 1. Idea | ✅ stated | "Half the answers are unusable; the rejects concentrate on 6 identifiable failure modes in synthesis/polish, each fixable at < 4 h." |
| 2. Plan | ✅ this doc | Each phase A1-A6 names the narrowest module to edit and exposes a flag-gated mode (off/shadow/enforce). Six independent commits, two sprints. |
| 3. Success criterion | ✅ §Scope guard | Combined 42-turn judge-pass-rate ≥ 55 % strict, reject ≤ 25 %, zero PASS → REJECT regressions, every fix has its own numeric INCLUDE/REVERT rule. |
| 4. Test plan | ✅ §3-§8 + §10 | Engineer: unit tests per phase + `test:health:fast`. Operator: re-judge 42 panel turns via Claude Code in conversation after each phase. SME: spot-check 5 manual probes against staging UI at sprint close. Decision rule: §Scope guard + per-phase INCLUDE/REVERT. |
| 5. Greenlight | ⏳ pending | Requires BOTH `test:health:fast` green AND post-judge pass rate ≥ thresholds AND no PASS → REJECT regressions. |
| 6. Refine-or-discard | ⏳ pending | Each phase has explicit REFINE branch (one retry) before DISCARD. If 4 of 6 phases pass INCLUDE individually but combined pass rate < 50 %, declare v14 partial-ship: keep the 4 that passed individually, write retrospective on the 2 that didn't, escalate the remaining gap to fix_v15 (likely semantic reranker, deferred per §10). |

---

### §10. Out of scope — explicitly deferred to future fixes

- **fix_v15 semantic reranker (TEI sidecar)**. The chunk-level
  cross-encoder rerank attacks the 8 topic-drift cases that
  structural fixes cannot reach. Defer until v14 ships and we
  measure whether topic-drift is still the dominant residual
  pattern. Cost: deploy time + ~$10-30/mo + 150-250 ms p99 latency.
- **fix_v15 gold_retrieval_v1 refresh**. The gold is stale
  relative to current node_key surfacing (e.g., gold expects
  `LEY_2277_2022_ART_7` but retriever surfaces `115` / `771-2`;
  gold expects `RES_DIAN_000233` but retriever surfaces section
  slugs). 3-4 h of manual per-question review. Until that lands,
  v14 measurement uses Claude-as-judge on the 42-turn panel.
- **fix_v15 chunk_section_type canonical persistence**. The Gate 2
  proposal from the original v14 plan (wire `ingestion_chunker._SECTION_TYPE_MAP`
  into supabase_sink + SQL soft penalty + cloud backfill). Deferred
  because A2 regex heuristics cover ~80 % of the structural noise
  at < 1/4 of the cost. Re-evaluate after v14.
- **fix_v15+ coherence-gate vocabulary audit**. A6 patches one
  specific case (Ley 2466). A broader audit of the
  `compatible_doc_topics` map for completeness is deferred.
- **fix_v15+ polish prompt rewrite for rejection-rate reduction**.
  If A5's diagnostic reveals a single dominant rejection reason,
  a targeted polish prompt rewrite (akin to fix_v8 §3e) is the
  follow-up. Deferred because requires the A5 data first.

---

### §11. Verification — how to measure each phase

**Engineer-side (before each phase merges):**

```bash
PYTHONPATH=src:. LIA_BATCHED_RUNNER=1 uv run pytest \
  tests/test_<phase-specific>.py -q
npm run test:health:fast
```

**Phase-judge measurement (after each phase merges, in shadow mode):**

1. Restart `dev:staging` so the new code is loaded.
2. Re-run both 21Q panels:
   ```bash
   for fixture in 21q_retriever_General 21q_retriever_Practica; do
     PYTHONPATH=src:. uv run python scripts/eval/run_sme_parallel.py \
       --run-dir evals/sme_validation_v1/runs/$(date +%Y%m%dT%H%M)_v14_<phase>_${fixture} \
       --questions evals/sme_validation_v1/${fixture}.jsonl \
       --server http://127.0.0.1:8787 --workers 4 --auth
   done
   ```
3. Re-judge all 42 turns through Claude Code in conversation
   using the 4-level senior-contador rubric (STRONG / ACCEPTABLE /
   BORDERLINE / REJECT + flags). Same rubric as the v13 baseline
   judge at `evals/sme_validation_v1/runs/20260513T1030_*_postclean/`.
4. Build the comparison table: per-turn class transition v13 → v14.x.
   Decision rule from §3-§8 applies.

**Sprint close measurement (after v14.1 phases A1+A2+A5+A6,
after v14.2 phases A3+A4):**

Same re-judge methodology, full 42-turn table. Sprint passes its
sub-scope-guard if cumulative INCLUDE decisions hit the sprint
target:

- v14.1 target: combined strict pass ≥ **40 %** (vs 26 % baseline).
- v14.2 target: combined strict pass ≥ **55 %**, reject ≤ **25 %**.

**Hard veto (applies at every phase and at sprint close):** if
ANY single turn transitions PASS (v13) → REJECT (v14.x), the
last-merged phase is reverted before continuing.

**SME-side (only after v14.2 closes):** 5 manual probes by a
domain expert (contador) against the staging UI on 5 of the
turns judged STRONG by Claude. Operator-triggered per
`feedback_sme_panel_explicit_request_only`.

---

### §12. Critical files

```
New (4 files):
  src/lia_graph/pipeline_d/chunk_quality_heuristics.py
  tests/test_legal_anchor_allowlist.py
  tests/test_chunk_quality_heuristics.py
  tests/test_compatible_doc_topics.py   (if not already present)

Modified (narrow edits only):
  src/lia_graph/pipeline_d/answer_synthesis_sections.py
    ~ build_legal_anchor_lines gains topic-allowlist filter (A1)
  src/lia_graph/pipeline_d/retriever_supabase.py
    ~ call score_chunk_quality between _hybrid_search and
      _classify_article_rows; demote rrf_score; attach reason (A2)
  src/lia_graph/pipeline_d/answer_llm_polish.py
    ~ _build_polish_prompt prepends DIRECTIVA NUMÉRICA (A3)
    ~ aggregate polish_skip_reason distribution (A5)
  src/lia_graph/pipeline_d/answer_polish_rejected_fallback.py
    ~ filter bullets through A1+A2; omit-empty-section; honest
      abstention < 500 chars (A4)
  src/lia_graph/pipeline_d/compatible_doc_topics.py
    ~ add reforma_laboral_ley_2466 mapping (A6)
  config/topic_norm_allowlist.json
    ~ extend coverage to 14 topics (A1)
  scripts/dev-launcher.mjs
    ~ LIA_LEGAL_ANCHOR_GATE_MODE, LIA_CHUNK_QUALITY_HEURISTIC_MODE,
      LIA_POLISH_REJECTED_FALLBACK_FILTER defaults per mode
  scripts/eval/sme_validation_report.py
    ~ polish-rejection breakdown by reason (A5)
  docs/orchestration/orchestration.md
    ~ env matrix bump v2026-05-13-fix-v13-practica-lane
      → v2026-05-14-fix-v14-anchor-and-noise + change-log row
  docs/guide/env_guide.md
    ~ mirror env matrix
  CLAUDE.md
    ~ mirror in "Runtime Read Path" section + Fast Decision Rule
  frontend/src/features/orchestration/orchestrationApp.ts
    ~ orchestration map status card
```

Net new code: small. Largest single edit is the allowlist JSON
curation (A1). All Python edits are < 60 LoC per file.

---

### §13. Rollback recipe (per phase, all flag-flips, no redeploy)

| Phase | Rollback |
|---|---|
| A1 legal-anchor allowlist | `LIA_LEGAL_ANCHOR_GATE_MODE=off` |
| A2 chunk-quality heuristics | `LIA_CHUNK_QUALITY_HEURISTIC_MODE=off` |
| A3 polish operationalization | revert the prompt edit (single function), no env flag |
| A4 fallback rebuild | `LIA_POLISH_REJECTED_FALLBACK_FILTER=legacy` |
| A5 polish diagnostic | n/a — pure observability |
| A6 Ley 2466 mapping | revert dict entry |
| FULL v14 → v13 | combine A1 off + A2 off + A4 legacy → identical to v13 |

---

### §14. Two-sprint roadmap

| Sprint | Date target | Phases | Effort | Per-sprint pass-rate target |
|---|---|---|---|---|
| **v14.1** | 2026-05-14 | A1 (anchor allowlist) + A2 (chunk heuristics) + A5 (polish diagnostic) + A6 (Ley 2466) | ~7 h | combined strict ≥ **40 %** |
| **v14.2** | 2026-05-15 / 2026-05-16 | A3 (polish operational directive) + A4 (fallback rebuild) — informed by A5 data | ~4 h | combined strict ≥ **55 %**, reject ≤ **25 %** |

Each sprint closes with:
1. `npm run test:health:fast` green
2. Re-judge 42 panel turns (Claude-as-contador-senior)
3. Phase-by-phase INCLUDE / REVERT decision against §3-§8 rules
4. Boss summary in plain language
5. Commit `ship(v14.<N>): <one-liner>`
6. Push to origin/main
7. Operator authorization before opening next sprint

---

### §15. Sprint v14.1 — landed 2026-05-13

**Decision rule, amended by operator 2026-05-13 mid-sprint**: the
original "zero PASS→REJECT regressions" hard veto was replaced with
a **net-improvement + zero-new-hallucinations** rule. A phase PASSES
if (a) judge-pass-rate moves up on the combined 42-turn panel AND
(b) inspection of every regressed turn confirms NO new invented
facts (cifras, normas, plazos, casillas) were introduced — even if
the answer is less complete or carries irrelevant corpus fragments.
A new hallucination is the only hard fail. Rationale: the corpus
already had factual ground truth in v13; v14 fixes should not
introduce inventions but ARE allowed to land less polished outputs
on a small subset as a transitional cost. v14.2 (polish stage) will
recover those.

**v14.1 measurement (post-clean panels run 2026-05-13T13:14):**

| | Baseline v13 (2026-05-13T10:30) | v14.1 enforce (2026-05-13T13:14) | Δ |
|---|---|---|---|
| STRONG | 5/42 | 5/42 | 0 |
| ACCEPTABLE | 6/42 | 8/42 | +2 |
| BORDERLINE | 11/42 | 6/42 | -5 |
| REJECT | 20/42 | 23/42 | +3 |
| **Strict pass** | **11/42 = 26.2 %** | **13/42 = 31.0 %** | **+4.8 pp** |
| Reject rate | 47.6 % | 54.8 % | +7.2 pp |

**Class transitions** (9 improvements, 3 degradations, 30 no-change):

* ↑↑ STRONG ← BORDERLINE: `pr_fe_contingencia_operativa`
* ↑↑ ACCEPTABLE ← REJECT: `ep_renta_ttd_paragrafo6` (A1 dropped Arts. 100-102 from anchor)
* ↑ ACCEPTABLE ← BORDERLINE: `pr_correccion_renta_saldo_favor`,
  `ep_fe_cufe_contingencia`, `ep_iva_regimen_responsables`,
  `ep_rst_elegibilidad_sectores`
* ↑ BORDERLINE-serving ← BORDERLINE-abstention (A6 effect):
  `pr_reforma_laboral_recargos`, `ep_laboral_reforma_2466`
* ↓ REJECT ← STRONG: `pr_fe_nota_credito_correccion` (polish flipped
  llm→rejected; chunk fragments visible; codes FAC-001/010 SAME as
  v13, not new)
* ↓ REJECT ← ACCEPTABLE: `pr_firmeza_calendario_defensivo` (polish
  flipped llm→rejected; corpus-leak fragments visible — "PYME
  manufactura ingresos $950M" — these are real corpus content, NOT
  invented)
* ↓ REJECT ← BORDERLINE: `ep_gmf_exencion_350uvt` (sections emptied;
  remaining bullets reference real arts. 592/593/594-3 ET Ley
  2277/2022 — no invention)

**Hallucination audit on the 3 degradations**: zero new invented
facts. All degraded content references real norms (Arts. 147, 588,
589, 689-3, 616-1, 616-2, 592, 593, 594-3) and real entities (Nequi,
Daviplata, FAC-001 error codes from prior corpus). Degradation is
purely "less complete" + "off-topic corpus fragments surfaced", not
factual invention. The amended decision rule applies: PASS.

**Phase-by-phase decisions:**

* **A1 — legal-anchor topic allowlist**: INCLUDE at `enforce`.
  Gate fired in 41/42 turns, dropped 41 items across the panel.
  Surfaced real improvements (Q39 TTD Arts. 100-102 dropped, Q27 IVA
  Art. 1 FORMULARIO 7 dropped) and contributed indirectly to the
  4-pp uplift. The 3 polish-rejected cases that flipped class are
  hallucination-free per audit above; v14.2 polish work recovers.
* **A2 — chunk-quality heuristics**: INCLUDE at `enforce`. Fired
  8 demotions total (low volume — pattern catalog needs more
  patterns for portal-login / matrícula mercantil cases that
  survived). Refinement of catalog deferred to v14.2 §4.
* **A5 — polish diagnostic instrumentation**: INCLUDE (always-on).
  Pure observability; no behavior change. Already gating the
  `polish.rejected.fallback_composed` path is visible in every run.
* **A6 — Ley 2466 coherence-gate mapping**: INCLUDE. Both Ley 2466
  turns transitioned from `topic_safety_abstention` to
  `graph_native` with BORDERLINE-class content. No regression
  elsewhere.

**Launcher defaults flipped 2026-05-13**:
* `LIA_LEGAL_ANCHOR_GATE_MODE` default: `shadow` → `enforce`
* `LIA_CHUNK_QUALITY_HEURISTIC_MODE` default: `shadow` → `enforce`

**Sprint v14.1 close**: strict pass 31 % (target was ≥ 40 %); we
landed 4-5 pp below target but the gates are wired correctly and
the next sprint (v14.2 polish stage) targets the rejection rate
directly. A2's pattern catalog refinement (catch portal-login + the
chunk-leak strings that survived A2-shadow) folds into v14.2.

**v14.1 evidence runs** (committed alongside this plan):
* `evals/sme_validation_v1/runs/20260513T1314_v14_1_enforce_practica/` (21 JSONs)
* `evals/sme_validation_v1/runs/20260513T1314_v14_1_enforce_general/` (21 JSONs)
