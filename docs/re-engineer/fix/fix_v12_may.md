## fix_v12_may.md — port Lia Contador's practical-first answer spec to Lia Graph (assembly + polish + práctica retrieval boost)

> **Drafted 2026-05-12 Bogotá** by claude-opus-4-7 after an
> operator-flagged regression on the user-experience axis: the
> chat answers across the SME mini-panel
> (`evals/sme_validation_v1/questions_expert_panel_v1.jsonl`) read
> like "a legal academic guide" instead of practical accounting
> guidance. Operator diagnosed this against the parent product
> **Lia Contador** (https://github.com/avas888/Lia_contadores)
> which had an explicit composer-level spec mandating
> practical-first ordering. Lia Graph diverged silently on three
> independent layers during the v1..v11 retrieval-tuning era.
>
> **Audience.** Zero-context fresh LLM or engineer. Self-contained.
> Skim `fix_v11_may.md §0` for the chunk-class keystone (10A),
> Supabase-routed expert panel (10B), trust-tier prioritization
> (11A), and the v11 DISCARD of the Falkor anchor (11B). Skim
> `CLAUDE.md` "Surface Boundaries" — the `main chat` surface this
> fix targets is parallel to the `Interpretación de Expertos`
> panel, never behind it.
>
> **What this is.** Three independent, independently-shippable
> phases that port the Lia Contador `pipeline_c/composer.py`
> `structure_hint` spec back into Lia Graph's `pipeline_d`
> assembly + polish + retrieval, AND ensure the 1,463 `practica_erp`
> chunks already in cloud Supabase (fix_v10_may Phase 10A backfill)
> actually compete for top-K placement.
>
> **What this is not.** Not a new sidebar panel mirroring
> Interpretación de Expertos (deferred — re-evaluate after Phase 3
> result). Not a corpus re-extraction (the 1,463 chunks are
> correctly tagged). Not a `practica_erp`-only synthesis branch
> (also deferred to Phase 3b if Phase 3 measurement is flat). Not
> a backwards step on the 21-Q expert-panel result (v11A baseline
> 12/21 stays the regression floor; gain target is on the
> orthogonal `main chat` axis).
>
> **Scope guard.** Closing bar at the end of Phase 12C:
> (a) 5/5 manual SME probes show `**Recomendaciones Prácticas**`
> as the first non-`Respuestas directas` heading;
> AND (b) for followup-shape probes, `**Anclaje Legal**` appears
> after `**Precauciones**` (or last if `precautions` empty);
> AND (c) the 21-Q expert-panel mini-panel `main chat` cell
> (acc+ on practical substance, NOT acc+ on the Interpretación
> sidebar) reaches **≥ 13/21** with `Recomendaciones Prácticas`
> bullets being substantively actionable (concrete steps, plazos,
> riesgos) — not legal recitation;
> AND (d) the §1.G 36-Q chat panel still holds at-or-above the
> post-fix_v8f-temp0 baseline (34/36 acc+).

---

## 0. Inheritance from fix_v1..fix_v11 + the v12 starting state

Everything in `fix_v11_may.md §0` carries forward unchanged.
Additional invariants this doc commits to:

- **Phase 10A is production.** `supabase_sink.write_chunks` inherits `knowledge_class` from the parent doc; 2,275 cloud chunks correctly retagged including **1,463 `practica_erp` chunks**. G1/G2/G3 sink-level guardrails prevent drift.
- **Phase 11B Falkor anchor is DISCARDED** (`LIA_PLANNER_INTERPRETATION_ANCHOR=off`). The interpretation panel runs through the Python `article_index` fallback (Phase 10C v0). v12 does NOT re-attempt the interpretation panel — the user complaint is on the **`main chat` surface**, orthogonal to Interpretación.
- **`LIA_INTERPRETATION_SOURCE` defaults stay as v11 set them** (`supabase` for `dev:staging` and `production`, `filesystem` for `npm run dev`). v12 introduces no changes on that axis.
- **Risk-forward flag stance carries forward** (per `project_beta_riskforward_flag_stance.md`): the one new env knob v12 introduces (`LIA_PRACTICA_BOOST_FACTOR=1.5`) flips ON across all three modes; the launcher owns the default; shell override still wins.
- **Polish prompt regression floor:** post-fix_v8 §3a substantive fallback + §3b observability + §3e allowlist + §3f temperature=0.0 + §3g Art. 115 ET anchor for ICA all stay. v12 §Phase-12B adds **one new rule** to the same prompt without unpicking any existing rule.

---

## 1. Diagnosis — three-layer divergence from Lia Contador (verified 2026-05-12 AM)

Three parallel Explore agents combed (a) the parent repo on GitHub, (b) the current Lia Graph `pipeline_d` assembly modules, and (c) the retrieval surfacing for `practica_erp`. The divergence is on three orthogonal layers and they compound.

### 1.A — Parent spec: Lia Contador `pipeline_c/composer.py`

The parent product specified the answer shape at the composer prompt level. **Verbatim from `src/lia_contador/pipeline_c/composer.py` ~L200-250**, the `structure_hint` variable applied to every routing branch (`decision`, `substantive_normative`, `comparative`, `theoretical_normative`):

```
"Ordena la respuesta asi: 1. **Recomendaciones prácticas**
(qué hacer concretamente, pasos, plazos, riesgos),
2. **Normativa relevante** (norma principal, vigencia,
normas complementarias),
luego secciones adicionales si el nivel de detalle lo
requiere."
```

What "Recomendaciones Prácticas" contains per route (verbatim):

| Route | Content directive |
|---|---|
| decision / default | "qué hacer, pasos concretos, plazos, riesgos" |
| substantive_normative | "efecto practico para el contador, qué hacer y qué cuidar" |
| comparative | "perfiles que favorecen cada regimen, criterios clave de decision, pasos para evaluar" |
| theoretical_normative | "qué hacer concretamente, pasos, plazos, riesgos" |

Enforced via `_SECTION_HEADER_TITLES` tuple + `action_opening` deterministic check in `src/lia_contador/pipeline_c/quality_checks.py`. Audience rationale recorded in `docs/done/quality_quickcheck_results_QQ_AB_RUN_2026_04_05.md`: working SMB accountants who need actionable steps first, legal grounding second.

**No `practica_erp` knowledge_class existed in Lia Contador.** The practical-first shape was achieved purely at prompt level — composer told the LLM to lead practically and the LLM synthesized practical content from whatever evidence was retrieved.

### 1.B — Current Lia Graph divergence (post-fix_v11)

| Layer | Lia Contador | Lia Graph (today) | File:line |
|---|---|---|---|
| Q1 lead section label | `**Recomendaciones prácticas**` | `**Ruta sugerida**` | `pipeline_d/answer_first_bubble.py:107` |
| Q2+ lead section label | same | `**Qué Haría Primero**` | `pipeline_d/answer_followup.py:278` |
| Q2+ legal position | bottom of answer | **3rd of 4-7** — `Anclaje Legal` before `Precauciones` and `Soportes` | `pipeline_d/answer_followup.py:281-284` |
| Polish primary_directive | "operativo, sin relleno" + section-order rule | "operativo, sin relleno" — order rule **missing** | `pipeline_d/answer_llm_polish.py:514-544` |
| `practica_erp` chunks in corpus | n/a (instructed-only) | **1,463 chunks** | cloud Supabase (fix_v10_may §4.A) |
| Retrieval treatment of práctica | n/a | `filter_knowledge_class=None` + **no boost parameter exists in hybrid_search** | `pipeline_d/retriever_supabase.py:285`; `supabase/migrations/20260512000000_topic_filter_soft.sql:48-55` (parameter block) |
| Synthesis routing | LLM-instructed | No práctica-specific routing; chunks flow through generic `answer_support.py` extraction | `pipeline_d/answer_support.py:1-200`; `answer_synthesis_sections.py:37-90` |

### 1.C — How the layers compound

1. **Retrieval surfaces few práctica chunks.** With `filter_knowledge_class=None` and no boost, normative chunks dominate top-K by sheer corpus density (~10× more normative than práctica chunks in most subtopics).
2. **`build_recommendations` falls back to article-derived bullets.** `extend_from_support_insights` (called at `answer_synthesis_sections.py:46-53`) returns thin output when support docs are scarce; the function falls through to `extend_from_guidance(primary_articles, ...)` which extracts bullets from **article metadata** (normative voice).
3. **Assembly puts that thin practical content under a non-practical-sounding label** (`Ruta sugerida` / `Qué Haría Primero`) and places `Anclaje Legal` mid-answer (Q2+).
4. **Polish doesn't rescue order.** The `primary_directive` says nothing about section order; `_rules_block`'s `section_structure` rule says `"Mantené la estructura por secciones del borrador"` — i.e. preserve whatever ordering Phase 1-3 produced.

Result: the accountant sees an `Anclaje Legal`-forward, article-language-derived layout where Lia Contador deliberately led with operative steps drawn from práctica-rich evidence.

---

## 2. Target architecture (v12 closing state)

### 2.A — Phase 12A: assembly — rename + reorder sections (port literal `Recomendaciones Prácticas` label)

**Goal.** User sees a section literally titled `**Recomendaciones Prácticas**` at the top of every chat answer (both Q1 and Q2+ shapes), with `Anclaje Legal` pushed to the bottom of Q2+ answers.

**Module edits.**

| File | Edit |
|---|---|
| `pipeline_d/answer_first_bubble.py:107` | Rename `render_prepared_section("Ruta sugerida", route_lines, numbered=True)` → `render_prepared_section("Recomendaciones Prácticas", route_lines, numbered=True)`. No reorder (Q1 already leads with practical content after `direct_answers`; legal stays inlined via `pepper_legal_anchor_into_procedure`). |
| `pipeline_d/answer_followup.py:263-293` (`_compose_expanded_followup_answer`) | (1) Rename `render_bullet_section("Qué Haría Primero", recommendations[:2])` → `render_bullet_section("Recomendaciones Prácticas", recommendations[:2])` on line 278. (2) Move the `Anclaje Legal` branch (currently lines 281-282) to AFTER the `paperwork` / `opportunities` / `context_lines` conditional branches — i.e. legal becomes the LAST always-on section. |
| `pipeline_d/answer_polish_rejected_fallback.py:77-99` | Rename `Ruta sugerida` → `Recomendaciones Prácticas` so the fallback assembler matches the new shape; legal already trails — good. |

**New order for `_compose_expanded_followup_answer`:**

1. `Recomendaciones Prácticas` (was first ✓)
2. `Procedimiento Sugerido` (was second ✓)
3. `Precauciones` (was 4th — moves up to 3rd)
4. `Soportes y Papeles de Trabajo` (conditional, was 5th — unchanged position relative to its trigger)
5. `Oportunidades` (conditional — unchanged)
6. `Cambios y Contexto Legal` (conditional — unchanged)
7. **`Anclaje Legal` — moves from 3rd to LAST** (always-on if `legal_anchor` non-empty)

Q1 path (`answer_first_bubble.py:104-113`) already orders correctly after the rename — no reorder needed there. The fallback when `len(substantive_sections) < 2` at line 127 still emits `**Respuestas directas**` and stays untouched.

**Granular-edit guard** (per `feedback_granular_edits.md`): each of these is a ≤5-line edit to an existing file. No new modules. No large appends.

### 2.B — Phase 12B: polish prompt — lock the order

**Goal.** The LLM polish pass cannot unpick Phase 12A. The `primary_directive` mandates Lia Contador's order explicitly.

**Module edits.**

| File | Edit |
|---|---|
| `pipeline_d/answer_llm_polish.py:514-544` (`primary_directive` string) | Insert a new **point 0** BEFORE existing points 1-4 (the prohibitions stay numbered 1-4, point 0 is the structure rule). See §3.B for the verbatim text. |
| `pipeline_d/answer_llm_polish.py` `_rules_block()` (find the `section_structure` rule) | Replace `"Mantené la estructura por secciones del borrador"` → `"Aplicá el orden obligatorio de la DIRECTIVA PRIMARIA punto 0. Si el borrador difiere, reordená."` |

**Why a "point 0" instead of appending a point 5.** The existing points 1-4 are CONTENT prohibitions (no new norms, no new article numbers, no new years, no new figures). Section order is a STRUCTURE rule, qualitatively different — it goes at the top so the model reads it first and treats the prohibitions as constraints on a structurally-correct output rather than the other way around.

### 2.C — Phase 12C: retrieval — práctica boost so the lead section has práctica substance

**Goal.** `practica_erp` chunks consistently appear in the top-K retrieval set so `build_recommendations` and `extend_from_support_insights` have real práctica content to extract from, instead of falling through to article-derived bullets in normative voice.

**Module edits.**

| File | Edit |
|---|---|
| **NEW** `supabase/migrations/20260513000000_knowledge_class_boost.sql` | Mirror the shape of `20260512000000_topic_filter_soft.sql`. Add `boost_knowledge_class TEXT DEFAULT NULL` parameter + `knowledge_class_boost double precision DEFAULT 1.0`. Multiply the RRF score with `CASE WHEN boost_knowledge_class IS NOT NULL AND COALESCE(f.knowledge_class, s.knowledge_class) = boost_knowledge_class THEN GREATEST(COALESCE(knowledge_class_boost, 1.0), 1.0) ELSE 1.0 END`. Apply to cloud (operator-authorized per `feedback_lia_graph_cloud_writes_authorized.md`) and local. |
| `pipeline_d/retriever_supabase.py:282-304` | After the existing `boost_topic` block, add a parallel block setting `payload["boost_knowledge_class"]="practica_erp"` and `payload["knowledge_class_boost"]=practica_boost` when `practica_boost > 1.0`. Add `_resolve_practica_boost_factor()` helper near `_resolve_topic_boost_factor` reading `LIA_PRACTICA_BOOST_FACTOR` (default `1.5`, clamped to `>= 1.0`). Add both new keys to the existing `try/except` recovery so older deployments without the migration strip them just like `boost_topic` is stripped. |
| `scripts/dev-launcher.mjs` | Add `LIA_PRACTICA_BOOST_FACTOR=1.5` to the per-mode env block alongside other retrieval-tuning flags. Flip ON in all three modes (`dev`, `dev:staging`, `production`). |
| `CLAUDE.md` "Runtime Read Path" paragraph | Add an env-matrix entry dated 2026-05-12 (env v2026-05-12-fix-v12) for `LIA_PRACTICA_BOOST_FACTOR=1.5`. Bump the env-matrix version per the non-negotiable. |
| `docs/orchestration/orchestration.md` | Same env-matrix update (authoritative source) + change-log row. Per the non-negotiable: keep CLAUDE.md, `env_guide.md`, and the orchestration HTML status card aligned in the same task. |
| `docs/guide/env_guide.md` | Mirror env-matrix update. |
| `src/lia_graph/ui_chat_payload.py` | Verify `knowledge_class` is included in per-chunk evidence diagnostics so the boost effect is observable in `response.diagnostics.pipeline_trace.steps[].retriever.hybrid_search.out`. If not whitelisted, add it. |

---

## 3. Migration phases — 12A through 12C

### Phase 12A — Assembly: rename + reorder

**Pre-flight.** Open `pipeline_d/answer_followup.py:263-293` and re-read the section sequence — the Read snapshot in the plan file used the current line numbers but other edits in the v11 era may have shifted them. Confirm `Anclaje Legal` is still rendered at the 3-of-4 position before reordering.

**Code change.** Three single-line renames + one block move (the `Anclaje Legal` if-branch in `answer_followup.py`).

**Verification.**

- **Unit:** No new tests added — visible-shape change. Existing `tests/test_answer_assembly*.py` should still pass; if any tests pin the literal string "Ruta sugerida" or "Qué Haría Primero", update those tests to assert the new label.
- **Integration:** `npm run dev:staging`. Probe 5 SME-panel questions (3 Q1-shape, 2 Q2+-shape). Confirm `retrieval_backend=supabase` on first response (per `feedback_default_run_mode_staging.md`).
- **Numeric criterion:** 5/5 answers display `**Recomendaciones Prácticas**` as the first non-`Respuestas directas` heading. For followup-shape probes, `Anclaje Legal` appears after `Precauciones`.
- **Greenlight:** operator confirms manually.

### Phase 12B — Polish: lock the order

**Pre-flight.** Confirm `primary_directive` is still at `answer_llm_polish.py:514-544` (the v8 §3e rewrite landed there). Confirm `_rules_block` still defines a `section_structure` rule and find its line.

**Code change.** Insert point 0 in `primary_directive` (~8 lines). Update one rule in `_rules_block` (~2 lines).

**Verbatim point 0 text:**

```
0) ORDEN OBLIGATORIO de las secciones — exactamente este, de arriba
   hacia abajo:
   1. **Recomendaciones Prácticas** (qué hacer concretamente, pasos,
      plazos, riesgos)
   2. **Procedimiento Sugerido** (si el borrador lo trae)
   3. **Precauciones** / **Riesgos y condiciones**
   4. **Soportes** (si el borrador lo trae)
   5. **Anclaje Legal** SIEMPRE AL FINAL
   Si el borrador trae las secciones en otro orden, REORDENALAS.
   NO renombres secciones. NO inventes secciones nuevas.
```

**Verification.**

- **Integration:** same 5 SME-panel probes as Phase 12A. For each, read `response.diagnostics.polish_mode` (whitelisted per fix_v8 §3b). For each polished answer (`polish_mode=applied`), confirm visible order matches the directive.
- **Numeric criterion:** 5/5 polished answers preserve order; polish-rejection rate < 20% across the 5 probes.
- **Refine-or-discard.** If `polish_mode=rejected` > 20%, narrow the directive — drop the "REORDENALAS" instruction and just say "preservá el orden del borrador". The fallback at `answer_polish_rejected_fallback.py` (post-12A rename) still produces a correctly-ordered substantive answer, so the rejection-fallback path is safe.

### Phase 12C — Retrieval: práctica boost

**Pre-flight (cloud).** Per `feedback_lia_graph_cloud_writes_authorized.md`, announce the migration intent before executing: "Applying `20260513000000_knowledge_class_boost.sql` to cloud Supabase project LIA_Graph (`utjndyxgfhkfcrjmtdqz`) — adds two parameters to `hybrid_search`, no schema change to any table." Operator standing authorization covers the apply; no per-action confirmation needed.

**Pre-flight (local).** Run `make supabase-reset` then `PYTHONPATH=src:. uv run python scripts/seed_local_passwords.py` (per `CLAUDE.md` Supabase local stack section).

**Code change.** SQL migration (~30 lines mirroring the topic-boost migration). Python helper + caller block (~15 lines in `retriever_supabase.py`). Launcher flag (1 line × 3 modes). Doc updates (env-matrix in 3 places).

**Verification (preflight — engineer-only, ~10 min).** Re-run the same 5 SME-panel probes with `LIA_PRACTICA_BOOST_FACTOR=1.0` (off) vs `=1.5` (on). For each, inspect `response.diagnostics.pipeline_trace.steps[].retriever.hybrid_search.out` and count how many of the top-20 chunks have `knowledge_class=practica_erp`.

**Numeric criterion (preflight):** At `=1.5`, top-20 práctica chunk count ≥ 1.5× the `=1.0` baseline for ≥ 3/5 probes. If yes, the boost is biting and we proceed to the mini-panel. If no, **diagnose-before-intervene** (per `feedback_diagnose_before_intervene.md`): are práctica chunks even retrievable for the queried subtopic? If they don't exist in the relevant `subtopic`, the gap is **corpus coverage**, NOT calibration — record the finding and discard Phase 12C, don't tune the factor.

**Verification (mini-panel — operator-authorized only).** Per `feedback_sme_panel_explicit_request_only.md`: do NOT auto-run. After Phase 12A + 12B + 12C code lands and preflight passes, ask the operator: "Code is ready and preflight bit. Ready to run the 21-Q expert-panel mini-panel on the `main chat` axis?" On approval, run `scripts/eval/run_sme_parallel.py --questions evals/sme_validation_v1/questions_expert_panel_v1.jsonl --workers 4`. Wall: ~5 min.

**Numeric criterion (mini-panel):** the `main chat` cell of the 21-Q mini-panel scores **≥ 13/21 acc+** with `Recomendaciones Prácticas` bullets being substantively practical (concrete steps, plazos, riesgos), not legal recitation. Per `feedback_thresholds_no_lower.md`: record qualitative-pass exceptions per case; do NOT lower the threshold itself. Per `feedback_gates_evaluate_independently.md`: this gate is independent of the Interpretación sidebar — even if the sidebar gets worse, the `main chat` gate is on its own axis.

**Refine-or-discard (gate-6).** If preflight bit but the mini-panel result ≤ baseline, the issue is the **synthesis layer**, not retrieval — escalate to **Phase 12D** (scoped separately): explicit práctica routing in `answer_synthesis_sections.py::build_recommendations`. If preflight did NOT bite AND mini-panel doesn't move, discard Phase 12C and leave Phase 12A + 12B as the v12 closing state (visible shape fixed, substance gap noted as corpus-coverage work for v13).

---

## 4. Six-gate plan per phase (per `docs/aa_next/README.md` policy + `feedback_verify_fixes_end_to_end.md`)

### 4.1 Gates for Phase 12A

| Gate | Spec |
|---|---|
| G1 idea | Rename Lia Graph's lead section to `Recomendaciones Prácticas` (verbatim from Lia Contador) and reorder Q2+ so `Anclaje Legal` sinks to last. |
| G2 plan | This document §2.A + §3 Phase 12A. |
| G3 criterion | 5/5 manual probes show practical-first label + legal-last in Q2+. |
| G4 test plan | Engineer runs `dev:staging`, 5 SME-panel probes spanning 3 Q1 + 2 Q2+ shapes. Visual inspection of rendered answer. |
| G5 greenlight | Operator inspects the 5 answers, signs off. |
| G6 refine-or-discard | If 5/5 doesn't hold, fix the renderer and re-test. No fallback to "keep old labels". |

### 4.2 Gates for Phase 12B

| Gate | Spec |
|---|---|
| G1 idea | Add a structure-order rule (point 0) to the polish `primary_directive` so polish doesn't unpick Phase 12A. |
| G2 plan | §2.B + §3 Phase 12B. |
| G3 criterion | 5/5 polished answers preserve order; polish-rejection rate < 20%. |
| G4 test plan | Engineer re-runs the same 5 probes from 12A, inspects `polish_mode` diagnostic + visual order. |
| G5 greenlight | Operator confirms on the 5 polished outputs. |
| G6 refine-or-discard | If rejection rate spikes, soften "REORDENALAS" → "preservá el orden del borrador". If 5/5 order still fails, discard the point 0 addition; visible shape from 12A alone may already be enough. |

### 4.3 Gates for Phase 12C

| Gate | Spec |
|---|---|
| G1 idea | Boost `practica_erp` chunks in `hybrid_search` RRF score so the assembler's `Recomendaciones Prácticas` section gets real práctica substance, not article-derived bullets. |
| G2 plan | §2.C + §3 Phase 12C. |
| G3 criterion | (a) Preflight: top-20 práctica count ≥ 1.5× baseline on ≥ 3/5 probes. (b) Mini-panel: `main chat` cell ≥ 13/21 acc+ with substantive practical bullets. (c) §1.G 36-Q regression floor: ≥ 34/36 acc+. |
| G4 test plan | Engineer preflight (≤ 1.0 vs 1.5 A/B on 5 probes, inspect `pipeline_trace`). If preflight bites: operator-authorized 21-Q mini-panel + 36-Q §1.G regression sweep. SME judge on substance-vs-recitation per question. |
| G5 greenlight | Operator confirms both panels. Production launcher default flip authorized. |
| G6 refine-or-discard | If preflight bites + panel ≤ baseline → escalate to Phase 12D (synthesis-layer práctica routing). If preflight doesn't bite → corpus-coverage finding; discard 12C; ship 12A+12B alone. |

---

## 5. Schema additions

### 5.1 `hybrid_search` parameters

Migration `supabase/migrations/20260513000000_knowledge_class_boost.sql` adds two parameters to the `hybrid_search` RPC:

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `boost_knowledge_class` | `text` | `NULL` | Knowledge class to boost (e.g. `'practica_erp'`). Soft signal — does NOT filter recall. |
| `knowledge_class_boost` | `double precision` | `1.0` | Multiplier applied to RRF score for chunks matching `boost_knowledge_class`. Clamped to `>= 1.0` per Invariant I5 ("never penalize"). |

No table-level schema changes. No new columns. No new indexes.

### 5.2 No new env knobs beyond the boost factor

The only new env knob v12 introduces is `LIA_PRACTICA_BOOST_FACTOR` (default `1.5`, clamped to `>= 1.0`). Owned by `scripts/dev-launcher.mjs` per the non-negotiable that the launcher owns per-mode flags.

---

## 6. Code surface map (full delta)

| File | LoC change | Type |
|---|---|---|
| `src/lia_graph/pipeline_d/answer_first_bubble.py` | ~1 line (rename) | Existing |
| `src/lia_graph/pipeline_d/answer_followup.py` | ~5 lines (rename + block move) | Existing |
| `src/lia_graph/pipeline_d/answer_polish_rejected_fallback.py` | ~1 line (rename) | Existing |
| `src/lia_graph/pipeline_d/answer_llm_polish.py` | ~10 lines (point 0 + rule update) | Existing |
| `src/lia_graph/pipeline_d/retriever_supabase.py` | ~15 lines (helper + boost block) | Existing |
| `supabase/migrations/20260513000000_knowledge_class_boost.sql` | ~30 lines | **NEW** |
| `scripts/dev-launcher.mjs` | ~3 lines (one per mode) | Existing |
| `CLAUDE.md` | ~2 lines (env-matrix paragraph) | Existing |
| `docs/orchestration/orchestration.md` | ~5 lines (matrix row + change-log row) | Existing |
| `docs/guide/env_guide.md` | ~2 lines (mirror) | Existing |
| `src/lia_graph/ui_chat_payload.py` | 0-2 lines (only if `knowledge_class` not already in evidence whitelist) | Existing |

Total: ~75 lines across 11 files, of which 1 is a new SQL migration. No new Python modules. No new abstractions per `feedback_respect_pipeline_organization.md` (planner/policy/synthesis/assembly stay modular — every edit lands in the narrowest module that owns the behavior).

---

## 7. Risks + mitigations

### 7.1 Polish rejection rate spike after Phase 12B (medium risk)

**Risk.** The point 0 "REORDENALAS" instruction asks the model to do structural rewriting, which may collide with the existing content prohibitions (no new articles, no new norms) and produce rejected outputs more often.

**Mitigation.** Phase 12B's gate G3 explicitly tracks `polish_mode=rejected` rate. If > 20%, soften to "preservá el orden del borrador" (no structural rewriting demanded; the borrador from Phase 12A is already correctly ordered). The substantive-fallback assembler (`answer_polish_rejected_fallback.py`, post-12A rename) keeps the new label even on rejected outputs, so the user-visible shape stays correct either way.

### 7.2 Práctica boost dilutes anchor-doc surfacing (low-medium risk)

**Risk.** Boosting `practica_erp` chunks may demote critical normative anchors (e.g. Art. 115 ET on ICA deductions per fix_v8 §3g) below top-K, regressing the §1.G 36-Q panel.

**Mitigation.** The boost is multiplicative on RRF score, not a filter — normative chunks still surface, just with relatively lower rank when a práctica chunk is comparably scored. Phase 12C gate G3.c requires `≥ 34/36 acc+` on the §1.G regression panel as a hard floor. If that floor breaks, lower `LIA_PRACTICA_BOOST_FACTOR` from `1.5` to `1.25` and re-test before escalating.

### 7.3 Práctica chunks are corpus-thin in some subtopics (medium risk, observable)

**Risk.** Some SME-panel questions touch subtopics where the corpus has ≤ 3 práctica chunks; no boost factor will surface enough practical substance.

**Mitigation.** Preflight A/B in Phase 12C's gate G3.a explicitly measures whether the boost bites per-probe. If it doesn't bite on ≥ 3/5 probes, the diagnosis is corpus coverage, not calibration — record the finding and discard 12C cleanly (per `feedback_diagnose_before_intervene.md`). Corpus authoring is a separate v13 scope; 12A + 12B alone still ship a meaningful visible-shape fix.

### 7.4 Lia Contador's spec is a prompt, Lia Graph's is template-driven (architectural risk, accepted)

**Risk.** Lia Contador achieved practical-first purely by telling the LLM "ordena así". Lia Graph's `pipeline_d` builds the answer template deterministically and the LLM only polishes prose. So the "port" is not 1:1 — the parent's mechanism is at the synthesis-prompt layer, the v12 fix is at the assembly + polish-prompt layer.

**Mitigation accepted.** Phase 12A puts the practical-first shape in the deterministic template (more reliable than prompt instruction). Phase 12B reinforces it in the polish prompt (defense in depth). Phase 12C makes the SUBSTANCE feeding Phase 12A's lead section práctica-rich. This is a stronger architecture than Lia Contador's single-layer prompt approach — but it requires all three layers to ship for the spec to fully realize.

---

## 8. Open questions (decide before code lands)

### 8.1 Should `LIA_PRACTICA_BOOST_FACTOR` default differ per mode?

Operator-decidable. The risk-forward stance argues `1.5` everywhere. A more conservative argument: `1.5` in `dev` + `dev:staging`, `1.25` in `production` until the 36-Q regression panel is run on a `production`-equivalent corpus snapshot.

**Default proposed:** `1.5` across all three (per `project_beta_riskforward_flag_stance.md`). Operator can override per-mode by editing the launcher block.

### 8.2 Should `Anclaje Legal` show at all in Q2+ when it's just a citation rehash?

Subjective UX call. Lia Contador's spec is "Normativa relevante" as section 2 — it always shows. Lia Graph's current `Anclaje Legal` builder emits 1-3 bullets; in some cases all three are redundant citations of articles already named in `Procedimiento Sugerido`.

**Default proposed:** keep `Anclaje Legal` always-on at the bottom (per spec) but tighten `build_legal_anchor_lines` in a follow-up to dedupe against `Procedimiento` references. Out of v12 scope; flagged for v13.

### 8.3 Should we add a `LIA_PRACTICAL_FIRST_MODE=enforce|off` toggle?

Per `project_beta_riskforward_flag_stance.md` — no. v12 ships the new shape ON. Reverting is a code revert, not a flag flip. The boost factor is the only knob.

---

## 9. Order of operations summary

1. **Phase 12A** (lowest risk, biggest visual win). Three single-file edits. Local + `dev:staging` probes. ~30 min wall.
2. **Phase 12B** (medium risk). One file edit (`answer_llm_polish.py`). Re-run the same 5 probes from 12A; check `polish_mode`. ~30 min wall.
3. **Phase 12C preflight only**. SQL migration applied to local + cloud (operator-authorized). Python wire-up. Launcher flag. A/B preflight on 5 probes. ~60 min wall.
4. **Operator decision point.** If preflight bit: ask operator for green light to run the 21-Q mini-panel + 36-Q §1.G regression sweep (~10 min combined).
5. **If panel ≥ 13/21 + §1.G ≥ 34/36:** declare v12 closing state. Commit. Update `fix_v12_may.md §10` with the landing report. Confirm canonical `fixplan_v2.md` (or current canonical re-engineering plan) is updated per `feedback_recommendations_logged_in_canonical_plan.md`.
6. **If panel < 13/21 with preflight biting:** escalate to Phase 12D (synthesis-layer práctica routing). Scope separately in a follow-up section.
7. **If preflight didn't bite:** discard 12C, leave 12A + 12B shipped, record corpus-coverage finding in §11.

---

## 10. What to do tomorrow morning

1. Read this doc top-to-bottom.
2. Open `pipeline_d/answer_followup.py:263-293` and re-verify the line numbers (the v11 era may have shifted them).
3. Make the three Phase 12A edits. Probe locally first, then `dev:staging`.
4. Inspect rendered answers; confirm `**Recomendaciones Prácticas**` lead + `**Anclaje Legal**` last in Q2+.
5. If 5/5 holds → proceed to Phase 12B. If not → fix renderer; do not proceed.
6. Phase 12B → re-probe → inspect `polish_mode`. If rejection rate < 20% → proceed to Phase 12C. If higher → soften the directive per §7.1.
7. Phase 12C → announce cloud migration intent to operator → apply → wire Python → flag → preflight A/B → operator approval for panels → run panels.
8. Update §11 with landing report. Update canonical plan. Done.

---

## 11. Phase 12A/12B/12C landing report (to be filled in after execution)

_To be appended once each phase lands. Format mirrors `fix_v11_may.md §11-§17`:_

- Date/time (Bogotá AM/PM per `feedback_time_format_bogota.md`)
- What changed (files + LoC)
- Numeric result vs. criterion
- Operator/SME ruling
- Next action

### 11.D — Phase 12D attempted then DISCARDED (2026-05-12 AM Bogotá)

**Status.** ↩ regressed-discarded per gate-6 refine-or-discard.

**Hypothesis.** The 7 questions where polish kept rejecting after 12A+12B+12C had `recommendations=()` arriving empty at the assembler, so the polish-rejected fallback path led with `**Anclaje legal**` instead of `**Recomendaciones Prácticas**`. Two structural, generalizable changes were proposed to surface práctica content into the recommendations bucket:

- **Cambio 1.** `answer_support.py::_collect_support_doc_insight_candidates` — extended the `family in {practica, interpretacion}` filter to also accept `knowledge_class in {practica_erp, interpretative_guidance}`. Rationale: `family` is derived from `documents.corpus`, which is NULL for many cloud docs, so the legacy filter silently rejected práctica docs whose corpus column was unset.
- **Cambio 2.** `answer_synthesis_sections.py::build_recommendations` — accept `support_insights` and consume the `procedure` bucket (top 3) before falling through to `extend_from_guidance(primary_articles)`. The downstream `take_new_lines` dedup in `answer_synthesis.py` was supposed to prevent the same lines repeating in `**Procedimiento Sugerido**`.

**Implementation.** Three single-function edits in `answer_support.py` + `answer_synthesis_sections.py` + `answer_synthesis.py`. Existing test `tests/test_phase3_graph_planner_retrieval.py::test_phase3_pipeline_d_anticipo_prompt_does_not_leak_meta_starter_lines` was loosened to accept either the legacy fallback line OR a substantive `**Recomendaciones Prácticas**` section (≥2 bullets).

**Result on 21-Q expert-panel mini-panel (2026-05-12 09:36 Bogotá, run `evals/sme_validation_v1/runs/20260512_0932_phase12d_expert21/`):**

| Metric | 12C baseline | 12D | Δ |
|---|---|---|---|
| Lead = `**Recomendaciones Prácticas**` | 10 / 21 (48 %) | **8 / 21 (38 %)** | **−2** |
| polish_mode = llm (aplicado) | 11 / 21 | 9 / 21 | −2 |
| polish_mode = rejected | 9 / 21 (43 %) | 11 / 21 (52 %) | +2 |
| polish_mode = skipped | 1 / 21 | 1 / 21 | 0 |
| wall total | 207.9 s | 223.6 s | +15.7 s |

**Two specific regressions vs 12C** (both moved from `polish=llm + lead=Recomendaciones Prácticas` → `polish=rejected + lead=anclaje/riesgos`):
- `ep_renta_conciliacion_2516_v1` (12C: lead `Recomendaciones Prácticas`, polish llm → 12D: lead `Riesgos y condiciones`, polish rejected)
- `ep_rst_elegibilidad_sectores_v1` (12C: lead `Recomendaciones Prácticas`, polish llm → 12D: lead `Anclaje legal`, polish rejected)

**Diagnosis.** Cambio 1 (filter expand) admitted additional práctica/interpretacion docs that had been silently filtered out before. Some of those docs contributed bullets to the `procedure` insights bucket that contained absolute year references (e.g. "AG 2024", "2022", "2025") not present in either the query or the article evidence — the polish validator's `invented_periods` check then rejected the polished output, sending the answer through the fallback path. The structural rule itself (use `knowledge_class` as a more reliable signal than `family`) is correct in isolation; the failure mode is the interaction with the polish prompt's strict period-invariance rule. Surfacing more content into the synthesis pool stressed downstream invariants that hold cleanly under a narrower pool.

**What needs to be true for a future Phase 12D re-attempt.** Either: (a) a per-line filter on the support-insights bucket that strips bullets carrying absolute years/dates before they reach the polish prompt, OR (b) loosen the `invented_periods` polish rule (riskier — that rule has a real correctness purpose), OR (c) curate the chunks producing the noisy bullets at ingestion time (cleanest but slow). Out of v12 scope; fresh-plan task.

**Rollback executed (same session).** All three Cambios reverted; the loosened anticipo-prompt test reverted to its original hard-coded fallback-line assertion. Tests: `tests/test_answer_support.py + test_phase3_graph_planner_retrieval.py + test_answer_polish_rejected_fallback.py + test_answer_llm_polish.py` all green post-rollback. v12 closing state = 12A + 12B + 12C.

---

### 11.A — Phase 12A code landed (2026-05-12 PM Bogotá)

**Status.** Code + unit tests landed in working tree on `main`. Operator
5-probe `dev:staging` visual verification PENDING (per Phase 12A G4/G5).

**What changed (files + LoC).**

| File | Change |
|---|---|
| `src/lia_graph/pipeline_d/answer_first_bubble.py` | L107 rename: `"Ruta sugerida"` → `"Recomendaciones Prácticas"` (Q1 path). |
| `src/lia_graph/pipeline_d/answer_followup.py` | L263-293 (`_compose_expanded_followup_answer`): rename `"Qué Haría Primero"` → `"Recomendaciones Prácticas"` AND move the `Anclaje Legal` if-branch from the 3rd position (after `Procedimiento Sugerido`) to LAST (after `paperwork` / `opportunities` / `context_lines` conditionals, before the empty-state fallback). New order matches §2.A spec: Recomendaciones Prácticas → Procedimiento Sugerido → Precauciones → Soportes → Oportunidades → Cambios y Contexto Legal → **Anclaje Legal (last)**. |
| `src/lia_graph/pipeline_d/answer_polish_rejected_fallback.py` | L79 rename: `"Ruta sugerida"` → `"Recomendaciones Prácticas"` (substantive-fallback assembler from fix_v8 §3a). |
| `tests/test_answer_polish_rejected_fallback.py` | L8 docstring + L47 test name (`test_recommendations_render_as_ruta_sugerida` → `..._recomendaciones_practicas`) + L59 assertion: `"Ruta sugerida"` → `"Recomendaciones Prácticas"`. |
| `tests/test_phase3_graph_planner_retrieval.py` | L355 positive assertion (Q1 saldo-a-favor route): rename. L394 ordering positional index (multi-question Q1): rename. L560 strategy_chain negative assertion: rename to confirm strategy path still emits its custom labels (`Cómo La Trabajaría`, etc.) instead of the generic label. L651-653 broad-sectioned Q2+ assertion: replaced `"Ruta sugerida" not in` with **positive** assertion `"Recomendaciones Prácticas" in` + ordering invariant `Procedimiento Sugerido index < Anclaje Legal index` (locks the new Q2+ order Phase 12A introduces). |

Total: 3 src files (~7 LoC delta), 2 test files (~10 LoC delta). No new
modules per `feedback_granular_edits.md`.

**Known remaining usages of the old label (deliberately deferred).**

- `src/lia_graph/pipeline_d/answer_llm_polish.py:76` — `_rules_block`
  `section_structure` rule still names `"Ruta sugerida"` in the example
  list. Phase 12B rewrites this entire rule per §2.B; do NOT touch in 12A.
- `src/lia_graph/pipeline_d/answer_topic_gate.py:8` — module docstring
  example references `"Ruta sugerida"`. Harmless (docstring only, not
  runtime), but should be refreshed alongside 12B's `_rules_block` work
  for consistency.
- `tests/test_answer_topic_gate.py:118,156` and `tests/test_answer_llm_polish.py:64,179,207,302,334,342`
  use `"Ruta sugerida"` as INPUT to the gate/polish under test. These
  are arbitrary string inputs, not assertions on the new label —
  unchanged is correct (preserves the test's contract that the gate
  doesn't care which label the borrador happens to use).
- `tests/test_presentation_invariants.py:58,60` exercises
  `render_bullet_section` with an arbitrary label — unchanged is
  correct (the function's contract is label-agnostic).

**Numeric result vs. criterion (gate G3).**

- **Unit:** `tests/test_answer_polish_rejected_fallback.py` + `tests/test_phase3_graph_planner_retrieval.py` → 53/53 passed (`PYTHONPATH=src:. LIA_BATCHED_RUNNER=1 uv run pytest -q`).
- **Integration (5-probe `dev:staging` visual):** PENDING operator.

**Operator/SME ruling.** PENDING (G4 visual + G5 greenlight).

**Next action.** Operator runs `npm run dev:staging`, hits 5 SME-panel
questions (3 Q1-shape, 2 Q2+-shape) from
`evals/sme_validation_v1/questions_expert_panel_v1.jsonl`, confirms
on each response: (a) `**Recomendaciones Prácticas**` is the first
non-`**Respuestas directas**` heading; (b) on Q2+ shapes,
`**Anclaje Legal**` appears AFTER `**Precauciones**` (or last if
precautions is empty); (c) `response.diagnostics.retrieval_backend ==
"supabase"` (per `feedback_default_run_mode_staging.md`). On
greenlight → proceed to Phase 12B per §3.B. On any failed probe →
diagnose renderer in the narrowest module and re-test before
advancing.
