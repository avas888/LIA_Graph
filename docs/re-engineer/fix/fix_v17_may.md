# fix_v17_may.md — Lane B wiring for the 37 new playbooks

> **Author context (zero-agent-context protocol).** This plan is
> self-contained. A fresh LLM agent with no prior conversation history
> can execute it from the file system as-is. Every file path, function
> name, env flag, test name, registry entry, and decision rule is
> specified verbatim. Verify every artifact against `git ls-files`
> before acting. If any cited path or function does not exist, STOP
> and report drift — do not invent.

---

## §0. TL;DR

**Idea.** Take the **37 new playbooks** that fix_v16_may + corpusfix_v1
landed as **Lane A only** (cloud chunks tagged correctly, retrievable
via `hybrid_search`) and add their **Lane B wiring** so the planner
emits a **deterministic anchor** for each topic instead of relying on
hybrid_search ranking.

**Why now.** As of 2026-05-15 the chat engine answers all 7 corpusfix
probe questions, but the new playbooks only surface when retrieval
ranking happens to put them top-K. Lane B closes that loop: detector
fires → planner emits explicit `art:<num>` anchor → retriever fetches
the playbook chunk regardless of FTS/vector ranking → polish surfaces
the correct article in the answer.

**Effort.** ~20 min per topic — playbook already exists, ingestion
override already exists, cloud chunks already exist. The remaining
work is **mechanical wiring** in 4 narrow modules. **37 × 20 min ≈
12 hours** total engineering. Recommend batches of ~3 topics per
session with operator-reviewed probe per topic.

**Risk.** Low. Additive registry rows; rollback is removing the row.
Per-topic precision is operator-validated via the
`answer-engine-probe` skill before merge.

---

## §1. Repository state assumed by this plan

Verify these before changing the runtime:

| Path | Purpose |
|---|---|
| `src/lia_graph/pipeline_d/case_detectors.py` | Pure detector facade. Re-exports detectors from `case_detectors_extensions.py` + `case_detectors_b5.py`. |
| `src/lia_graph/pipeline_d/case_detectors_extensions.py` | b3 + b4 detectors. |
| `src/lia_graph/pipeline_d/case_detectors_b5.py` | b5 detectors (currently last sibling; b6 should be created here when this file reaches ~1000 LOC). |
| `src/lia_graph/pipeline_d/case_bullets/` | Per-topic `CaseSpec` instances. One file per topic. |
| `src/lia_graph/pipeline_d/case_bullets/__init__.py` | `CASE_REGISTRY` tuple. Order determines first-match anchor precedence. |
| `src/lia_graph/pipeline_d/case_bullets/_registry.py` | `CaseSpec` dataclass — see fields used by `planner.py` + polish + fallback. |
| `src/lia_graph/pipeline_d/planner.py` | Reads `CASE_REGISTRY` into `_CASE_ANCHOR_REGISTRY` + `_CASE_SEARCH_QUERIES`. |
| `src/lia_graph/pipeline_d/answer_synthesis_helpers.py` | Re-exports every detector so the synthesis layer iterates them. |
| `src/lia_graph/pipeline_d/answer_synthesis_sections.py` | Owns `build_recommendations` + `_active_case_keywords`. |
| `src/lia_graph/pipeline_d/answer_llm_polish.py` | Polish UVT validator auto-derives cue list from `CASE_REGISTRY.anchor_articles`. |
| `src/lia_graph/pipeline_d/answer_polish_rejected_fallback.py` | A4 substantive fallback — seeds bullets from `CASE_REGISTRY` when polish rejects. |
| `tests/test_planner_case_anchor_registry.py` | Registry membership + anchor emission per topic. Add one test per new topic. |
| `tests/test_case_detectors_purity.py` | Guard: detector module imports stay pure. |
| `.claude/skills/answer-engine-probe/` | Probe skill used at gate 7. |
| `config/article_secondary_topics.json` | Cross-domain anchor map — extend when a topic's anchor lives in a different libro than its router topic. |
| `config/topic_norm_allowlist.json` | Per-topic article allowlist. Extend with the anchor article when the topic key is present in this file. |
| `knowledge_base/.../PLAYBOOKS/playbook_<topic>.md` | Source-of-truth content. Already shipped in fix_v16 + corpusfix_v1. |

### Shipped through fix_v16 + corpusfix_v1 (do NOT re-implement)

- **51 topics** wired in `CASE_REGISTRY` (Lane A + Lane B).
- **45 + 37 = 82 playbook `.md` files** in `knowledge_base/`.
- **82 playbook stems** mapped in `_PLAYBOOK_FILENAME_TO_TOPIC`
  (`src/lia_graph/ingestion_classifier_playbook.py`).
- Cloud Supabase + Falkor carry all 82 playbook docs with correct
  `tema` and `topic` columns.
- Cross-domain abstention fix landed: `config/article_secondary_topics.json`
  has entries for 28, 240, 555, 555-1, 555-2, 565, 566-1, 568, 631,
  631-1, 631-2, 631-3, 631-4, 631-5, 632, 633, 634, 807, 809, 869,
  869-1, 869-2.

### The 37 Lane B candidates

These topics have **playbook .md on disk + cloud chunks tagged + ingestion
override** but **no `CaseSpec` row in `CASE_REGISTRY`**. Listed in
suggested priority order (highest probe traffic / clearest anchor first):

#### Group A — Labor / Nómina (12 topics)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 1 | `liquidacion_mensual_nomina` | CST + Ley 100 | `laboral` | `knowledge_base/CORE ya Arriba/LABORAL_NOMINA/PLAYBOOKS/playbook_laboral_liquidacion_mensual_nomina.md` |
| 2 | `prestaciones_sociales` | CST 249 + 306 + 186 | `laboral` | `…/playbook_laboral_prestaciones_sociales.md` |
| 3 | `liquidacion_terminacion` | CST 64 | `laboral` | `…/playbook_laboral_liquidacion_terminacion.md` |
| 4 | `pila_aportes` | Decreto 1990/2016 | `parafiscales_seguridad_social` | `…/playbook_laboral_pila_aportes.md` |
| 5 | `ugpp_fiscalizacion` | Ley 1607 art. 178 | `parafiscales_seguridad_social` | `…/playbook_laboral_ugpp_fiscalizacion.md` |
| 6 | `nomina_electronica_dspne` | Res. DIAN 000013/2021 | `laboral` | `…/playbook_laboral_nomina_electronica_dspne.md` |
| 7 | `contrato_prestacion_vs_laboral` | CST 23 | `laboral` | `…/playbook_laboral_contrato_prestacion_vs_laboral.md` |
| 8 | `contrato_aprendizaje_sena` | Ley 789 art. 30-31 | `laboral` | `…/playbook_laboral_contrato_aprendizaje_sena.md` |
| 9 | `embargos_salario` | CST 154-156 | `laboral` | `…/playbook_laboral_embargos_salario.md` |
| 10 | `smmlv_aux_transporte_anual` | Decreto SMMLV anual | `laboral` | `…/playbook_laboral_smmlv_aux_transporte_anual.md` |
| 11 | `subsidios_transporte_alimentacion` | CST 230 + Ley 1393 art. 30 | `laboral` | `…/playbook_laboral_subsidios_transporte_alimentacion.md` |
| 12 | `teletrabajo_trabajo_casa` | Ley 2088/2021 | `laboral` | `…/playbook_laboral_teletrabajo_trabajo_casa.md` |

#### Group B — Renta descuentos (6 topics)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 13 | `discapacidad_200` | Ley 361/1997 art. 31 | `descuentos_tributarios_renta` | `…/RENTA/PLAYBOOKS/playbook_renta_discapacidad_200.md` |
| 14 | `donaciones_descuento` | Art. 257 ET | `descuentos_tributarios_renta` | `…/playbook_renta_donaciones_descuento.md` |
| 15 | `energias_renovables` | Ley 1715/2014 art. 11 | `descuentos_tributarios_renta` | `…/playbook_renta_energias_renovables.md` |
| 16 | `factura_electronica_1` | Ley 2277/2022 art. 7 | `descuentos_tributarios_renta` | `…/playbook_renta_factura_electronica_1.md` |
| 17 | `ica_descuento_50` | Art. 115 par. ET | `descuentos_tributarios_renta` | `…/playbook_renta_ica_descuento_50.md` |
| 18 | `mujeres_violencia_200` | Ley 1257/2008 art. 23 | `descuentos_tributarios_renta` | `…/playbook_renta_mujeres_violencia_200.md` |

#### Group C — Retención fuente (3 topics)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 19 | `retencion_autoretencion` | Decreto 2201/2016 | `retencion_en_la_fuente` | `…/RETENCION_FUENTE/PLAYBOOKS/playbook_retencion_autoretencion.md` |
| 20 | `retencion_bases_minimas` | Decreto 572/2025 | `retencion_en_la_fuente` | `…/playbook_retencion_bases_minimas.md` |
| 21 | `retencion_tablas_ag_2025_2026` | Art. 383 ET + tablas DIAN | `retencion_en_la_fuente` | `…/playbook_retencion_tablas_ag_2025_2026.md` |

#### Group D — Renta deducciones extras (3 topics)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 22 | `aportes_parafiscales_seguridad_social` | Art. 108 ET | `costos_deducciones_renta` | `…/RENTA/PLAYBOOKS/playbook_renta_aportes_parafiscales_seguridad_social.md` |
| 23 | `pagos_no_constitutivos_salario` | CST 128 + Ley 1393 art. 30 | `costos_deducciones_renta` | `…/playbook_renta_pagos_no_constitutivos_salario.md` |
| 24 | `salario_integral` | CST 132 + Ley 50 art. 18 | `laboral` | `…/playbook_renta_salario_integral.md` |

#### Group E — Renta tarifas (2 topics)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 25 | `ttd_tasa_minima` | Art. 240 par. 6 ET | `tarifas_renta_y_ttd` | `…/playbook_renta_ttd_tasa_minima.md` |
| 26 | `zomac_zese` | Ley 1819 arts. 235-237 + Ley 2238/2022 | `zomac_zese_incentivos_geograficos` | `…/playbook_renta_zomac_zese.md` |

#### Group F — Panel adiciones (4 topics)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 27 | `panel_cierre_fiscal_anual_checklist` | (transversal) | `declaracion_renta` | `…/PANEL_ADICIONES/PLAYBOOKS/playbook_panel_cierre_fiscal_anual_checklist.md` |
| 28 | `panel_ica_territorial` | Ley 14/1983 + Decreto 1333/1986 | `ica` | `…/playbook_panel_ica_territorial.md` |
| 29 | `panel_migracion_rst_ordinario` | Art. 909 ET | `regimen_simple` | `…/playbook_panel_migracion_rst_ordinario.md` |
| 30 | `panel_reteica_municipal` | Acuerdos municipales | `ica` | `…/playbook_panel_reteica_municipal.md` |

#### Group G — NIIF (1 topic)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 31 | `niif_depreciacion_niif_vs_fiscal` | Art. 137 ET + Sección 17 PYMES | `estados_financieros_niif` | `knowledge_base/estados_financieros_niif/PLAYBOOKS/playbook_niif_depreciacion_niif_vs_fiscal.md` |

#### Group H — Tier 2 extras (6 topics)

| # | Slug | Anchor | Topic key | Brief on disk |
|---|---|---|---|---|
| 32 | `tier2_doc_comprobatoria_f1125_f1729` | Art. 260-5 ET + Decreto 1496/2024 | `precios_de_transferencia` | `…/RENTA/PLAYBOOKS/playbook_tier2_doc_comprobatoria_f1125_f1729.md` |
| 33 | `tier2_impuesto_patrimonio` | Arts. 292-296 ET | `impuesto_patrimonio_personas_naturales` | `…/playbook_tier2_impuesto_patrimonio.md` |
| 34 | `tier2_omision_activos_434a` | Art. 434-A ET | `regimen_sancionatorio` | `…/playbook_tier2_omision_activos_434a.md` |
| 35 | `tier2_precios_transferencia_umbrales` | Art. 260-5 ET | `precios_de_transferencia` | `…/playbook_tier2_precios_transferencia_umbrales.md` |
| 36 | `tier2_recursos_dian` | Arts. 720-732 ET | `procedimiento_tributario` | `…/playbook_tier2_recursos_dian.md` |
| 37 | `tier2_renta_presuntiva_historico` | Art. 188 ET | `renta_presuntiva` | `…/playbook_tier2_renta_presuntiva_historico.md` |

**Total: 37 topics**. Spot-check the file paths with
`ls "knowledge_base/CORE ya Arriba"/LABORAL_NOMINA/PLAYBOOKS/`
etc. before starting any batch.

---

## §2. Idea (gate 1)

**One-sentence statement:** for each of the 37 candidate topics, add a
`CaseSpec` row (detector + bullets + keyword whitelist + anchor
articles + search queries) so the planner emits a deterministic anchor
when the case fires, ensuring the playbook content reaches the answer
regardless of hybrid_search ranking.

**Why this matters even though answers already work:**

- Today's behavior: hybrid_search ranks the playbook chunk in top-K,
  polish surfaces it correctly **most of the time**. Failure modes:
  ranking drifts to adjacent chunks (e.g., the broader CST page
  outranks the specific liquidación chunk), polish picks wrong
  article number.
- With Lane B: detector fires → `_CASE_ANCHOR_REGISTRY` walk emits
  `kind="article"` entry point → `retriever._fetch_anchor_article_rows`
  pulls the exact chunk → `_merge_rows_prefer_anchors` puts it in
  primary → polish prompt receives the right article in
  `ARTÍCULOS PERMITIDOS` → answer cites the correct anchor in 100 %
  of probes.

---

## §3. Plan (gate 2 — implementation outline)

### §3.1 Per-topic wiring (the mechanical 20-min loop)

For each of the 37 topics, follow this exact sequence. The pattern
is identical to fix_v16_may §3.3 — read that file's §3.3.1–§3.3.5
**verbatim** before starting; this section assumes that pattern as
given.

**Step-by-step, per topic:**

1. **Read the playbook brief.** Path is in §1's table. Extract:
   - H1 title + one-line summary (for the detector docstring).
   - `## Cómo lo pregunta un contador` phrases (detector markers).
   - `## Norma principal` anchor article number(s).
   - `## Normas relacionadas` for search-query enrichment.
   - `## Respuesta operativa` numbered bullets (case bullets).
2. **Write the detector.** Choose the right sibling file:
   - If `case_detectors_b5.py` is < 800 LOC, append there.
   - Else create `case_detectors_b6.py` and re-export from
     `case_detectors.py` facade. Apply the engineering rules from
     fix_v16_may §3.3.1: word-boundary regex for tokens ≤ 4 chars,
     combined-keyword paths for verb forms, no imports from
     `answer_*` modules, append to `__all__`.
3. **Re-export.** Add the detector name to:
   - `case_detectors.py` facade.
   - `answer_synthesis_helpers.py` import block.
4. **Create `case_bullets/<slug>.py`.** Pattern (copy from an
   existing sibling — `notificaciones_electronicas.py` is the
   cleanest reference):
   - `SPEC = CaseSpec(name=..., detector=<fn>, bullets=tuple(...),
     keywords=tuple(...), anchor_articles=tuple(...),
     search_queries=tuple(...), source_label="<slug>_anchor")`.
   - Bullets **verbatim from the playbook's `## Respuesta operativa`**
     — do NOT paraphrase. Each bullet ≤ 280 chars. Bold UVT
     thresholds + article numbers with `**…**`. Never invent UVT/%
     values outside what the brief provides (the polish UVT validator
     will reject inventions per fix_v15_may §3).
5. **Register in `CASE_REGISTRY`.** Edit
   `case_bullets/__init__.py`:
   - Add the import line at the top.
   - Append the SPEC to the `CASE_REGISTRY` tuple.
   - **Order matters.** Put **specific-anchor topics BEFORE broader
     anchors**. Concrete examples:
     - `salario_integral` BEFORE `liquidacion_mensual_nomina` (the
       latter's markers would otherwise intercept).
     - `panel_reteica_municipal` BEFORE `panel_ica_territorial`
       (reteica is a sub-case of territorial ICA).
     - `tier2_precios_transferencia_umbrales` BEFORE
       `tier2_doc_comprobatoria_f1125_f1729` (umbrales decide if doc
       comprobatoria applies).
6. **Test row.** Add one block to
   `tests/test_planner_case_anchor_registry.py`:
   - `test_<slug>_case_anchors_art_<X>` — asserts planner emits the
     anchor.
   - `test_<slug>_case_adds_search_queries` — asserts the
     search-queries row was registered.
7. **Run focused tests:**
   ```
   PYTHONPATH=src:. uv run pytest \
       tests/test_planner_case_anchor_registry.py \
       tests/test_case_detectors_purity.py -q
   ```
   All green or STOP and diagnose.

### §3.2 Cross-domain anchor cross-check (per topic)

Topics whose anchor article lives in a **different libro** than the
router's natural topic require an entry in
`config/article_secondary_topics.json`. From §1's table, these are
the topics needing pre-add:

| Topic | Anchor | Lives in | Router likely picks | Add secondary_topic |
|---|---|---|---|---|
| `panel_migracion_rst_ordinario` | art. 909 ET | renta (libro 1) | `regimen_simple` | `regimen_simple` |
| `tier2_omision_activos_434a` | art. 434-A ET | sanciones (libro 5) | `regimen_sancionatorio` | already covered |
| `tier2_recursos_dian` | arts. 720-732 ET | libro 5 | `procedimiento_tributario` | already covered |
| `tier2_doc_comprobatoria_f1125_f1729` | art. 260-5 ET | renta (libro 1) | `precios_de_transferencia` | already covered |
| `tier2_renta_presuntiva_historico` | art. 188 ET | renta | `renta_presuntiva` | add `renta_presuntiva` |

Add the missing entries **before** running the staging probe for
that topic. Don't relax the coherence-gate threshold (per
`feedback_thresholds_no_lower`).

### §3.3 Non-ET anchor handling (Option A only, no schema change)

The current `_CASE_ANCHOR_REGISTRY` schema is `(detector,
tuple[article_id, ...], source_label)`. Article IDs are ET-only
strings. For the 12 labor topics + 4 panel + 3 retención + 1 NIIF
whose anchor is CST / Ley / Decreto / Resolución:

**Option A (this plan).** Anchor on the **closest ET tie-in** when
one exists; cite the non-ET norm in the body bullets. Concrete:

| Topic | Anchor used in registry | Non-ET norm cited in bullets |
|---|---|---|
| `salario_integral` | `108` (deducción salarios) + `387` (retención) | CST 132 + Ley 50/1990 art. 18 |
| `pila_aportes` | `108` (parafiscales requisito) + `114-1` | Decreto 1990/2016 |
| `ugpp_fiscalizacion` | `108` + `114-1` | Ley 1607 art. 178 |
| `nomina_electronica_dspne` | `617` (FE general) | Res. DIAN 000013/2021 |
| `liquidacion_mensual_nomina` | `108` + `387` | CST + Ley 100 |
| `prestaciones_sociales` | `108` + `387` | CST 249-306 |
| `liquidacion_terminacion` | `108` + `387` | CST 64 |
| `contrato_prestacion_vs_laboral` | `383` (retención salarios) | CST 23 |
| `contrato_aprendizaje_sena` | `108` (deducción) | Ley 789 art. 30-31 |
| `embargos_salario` | `108` | CST 154-156 |
| `smmlv_aux_transporte_anual` | `108` + `387` | Decreto SMMLV anual |
| `subsidios_transporte_alimentacion` | `108` + `387` | CST 230 + Ley 1393 art. 30 |
| `teletrabajo_trabajo_casa` | `108` | Ley 2088/2021 |
| `panel_cierre_fiscal_anual_checklist` | `26` + `588` + `714` | (transversal — keep generic) |
| `panel_ica_territorial` | `115` + `115-1` | Ley 14/1983 + Decreto 1333/1986 |
| `panel_migracion_rst_ordinario` | `909` | (anchor is ET) |
| `panel_reteica_municipal` | `115` + `115-1` | Acuerdos municipales |
| `niif_depreciacion_niif_vs_fiscal` | `137` (depreciación fiscal) | Sección 17 PYMES + NIC 16 |
| `discapacidad_200` | `255` (descuento) | Ley 361/1997 art. 31 |
| `energias_renovables` | `255` | Ley 1715/2014 art. 11 + Decreto 829/2020 |
| `factura_electronica_1` | `255` | Ley 2277/2022 art. 7 |
| `mujeres_violencia_200` | `255` | Ley 1257/2008 art. 23 |
| `retencion_autoretencion` | `365` (causación) | Decreto 2201/2016 |
| `retencion_bases_minimas` | `383` (tabla) + `392` | Decreto 572/2025 |
| `retencion_tablas_ag_2025_2026` | `383` + `387` | (anchor is ET) |

**Option B (schema change to support `kind="ley"` / `kind="decreto"`)
is OUT OF SCOPE for v17.** Document the deferral in the change-log
row and let v18+ revisit when more non-ET topics ship.

---

## §4. Success criterion (gate 3 — measurable minimum)

A topic is SHIPPED when ALL of the following hold:

1. The `CaseSpec` row exists in `case_bullets/<slug>.py` and is
   imported in `case_bullets/__init__.py::CASE_REGISTRY`.
2. The detector function exists in
   `case_detectors_b5.py` (or `_b6.py` if created) and is re-exported
   in both `case_detectors.py` and `answer_synthesis_helpers.py`.
3. `tests/test_planner_case_anchor_registry.py` carries two new
   tests for the topic; full suite green.
4. `tests/test_case_detectors_purity.py` still green (no
   `answer_*` import leaks in detector modules).
5. The full related sweep passes:
   ```
   PYTHONPATH=src:. uv run pytest \
       tests/test_planner_case_anchor_registry.py \
       tests/test_case_detectors_purity.py \
       tests/test_classifier_playbook_override.py \
       tests/test_classifier_path_veto.py \
       tests/test_answer_polish_rejected_fallback.py \
       tests/test_answer_synthesis_practica.py -q
   ```
6. Probe via `answer-engine-probe` skill against dev:staging returns
   `pass` or `warn` (never `fail`) for one representative question
   per topic.
7. The answer cites the registered anchor article in the rendered
   answer (visible inline anchor + Anclaje Legal section).

**Batch-level criterion:** ≥ 90 % of attempted topics in a batch
reach SHIPPED on first probe. Below 90 %, pause the batch and
diagnose the playbook template / engineer intake (per fix_v16_may §4
and `feedback_diagnose_before_intervene`).

---

## §5. Test plan (gate 4 — how to test, who runs what)

| Stage | Actor | Environment | What runs | Pass condition |
|---|---|---|---|---|
| 1. Read brief | Engineer | shell | `cat <brief_path>` | Has all 6 named sections from fix_v16_may §3.1 |
| 2. Wire detector + bullets + spec + registry | Engineer | local editor | Per §3.1 of this plan | All 7 sub-steps complete |
| 3. Cross-domain check | Engineer | grep | Confirm anchor article is in `config/article_secondary_topics.json` OR primary_topic matches router | Either present or not needed |
| 4. Unit tests | Engineer | local | Sweep from §4 step 5 | All green |
| 5. Restart server | Engineer + operator | dev:staging | `kill $(pgrep -f lia_graph.ui_server) && npm run dev:staging` | Health endpoint 200 |
| 6. Staging probe | Engineer + operator | dev:staging via `answer-engine-probe` | One probe per topic | `pass` or `warn`; cited anchor matches `anchor_articles` |
| 7. Operator review | Operator | browser | Read rendered answer | Would forward to paying SMB-contador as-is? |

**Decision rule per topic.** Stages 1–7 all clean → topic SHIPPED.
Any `fail` at stage 6 → blocking; diagnose layer per §6 below.

**Decision rule per batch (~3 topics).** If ≥ 1 of 3 topics fails at
stage 6, pause the batch, run a retrospective, do NOT relax the
per-topic decision rule (per `feedback_thresholds_no_lower`).

---

## §6. Greenlight (gate 5 — end-user validation)

Per `feedback_verify_fixes_end_to_end`, unit tests alone are not
sufficient.

- **Per topic:** operator opens dev:staging in a browser, types a
  representative question for the topic, reads the rendered answer.
- **Sign-off question:** would the operator forward this answer to a
  paying SMB-contador customer **as-is**? If yes → greenlight. If
  no → record the specific drag (citation, tone, missing detail) and
  route back per §7.

Greenlight is what separates "tests are green" from "contador-ready."
Do not skip.

---

## §7. Refine-or-discard (gate 6 — what to do if a topic regresses)

Per `feedback_diagnose_before_intervene`:

1. **Pinpoint the layer.**
   - Bullet missing → Lane B bullet extraction (re-read brief, verify
     verbatim transfer).
   - Anchor wrong → `_CASE_ANCHOR_REGISTRY` row anchor list edit.
   - Detector fires on wrong query → tighten markers / add veto guard
     for adjacent topic.
   - Coherence-gate abstains despite correct retrieval → add
     `article_secondary_topics.json` entry for the anchor.
   - Polish strips bullet → A4 fallback should catch it; if not,
     bullet > 280 chars or contains invented UVT.
2. **Refine vs discard.**
   - Refine: keep the row, fix the narrow issue, re-probe.
   - Discard: explicit `↩ regressed-discarded` status in the
     ship-state table at the bottom of this file; remove the row
     from `CASE_REGISTRY`; keep the case_bullets/<slug>.py file in
     the repo with a comment explaining the discard reason.
3. **Record the regression** in
   `docs/aa_next/playbook_regressions.md` (create if absent) with:
   topic, layer, fix applied or "discarded with reason."

A topic moves 🛠 → 🧪 → ✅ via §4 + §6; demotes to ↩ if §7 cannot
recover it in one iteration. Never silently roll back.

---

## §8. Rollback

**Per-topic rollback.**
1. Delete the import + registry row in
   `case_bullets/__init__.py`.
2. Delete `case_bullets/<slug>.py`.
3. Remove the detector from `case_detectors_b5.py` (or `_b6.py`).
4. Remove the re-exports in `case_detectors.py` +
   `answer_synthesis_helpers.py`.
5. Remove the test rows from
   `tests/test_planner_case_anchor_registry.py`.

No corpus or cloud rollback needed — chunks stay tagged correctly.
The answer just falls back to retrieval-only ranking for that topic.

**Full v17 rollback** (unlikely): `git revert` of the v17 commits.

---

## §9. Suggested batching schedule

| Batch | Topics | Effort | Recommended order rationale |
|---|---|---|---|
| v17 b1 | `liquidacion_mensual_nomina`, `prestaciones_sociales`, `liquidacion_terminacion` | ~1 h | Highest-traffic nómina core. Same anchor cluster (108 + 387). |
| v17 b2 | `pila_aportes`, `ugpp_fiscalizacion`, `nomina_electronica_dspne` | ~1 h | Compliance + nómina electrónica — also tightly clustered. |
| v17 b3 | `contrato_prestacion_vs_laboral`, `contrato_aprendizaje_sena`, `salario_integral` | ~1 h | Common contador questions; salario_integral order-sensitive vs nómina. |
| v17 b4 | `embargos_salario`, `smmlv_aux_transporte_anual`, `subsidios_transporte_alimentacion`, `teletrabajo_trabajo_casa` | ~1.5 h | Closes the labor block. |
| v17 b5 | `discapacidad_200`, `donaciones_descuento`, `energias_renovables` | ~1 h | Renta descuentos batch 1. |
| v17 b6 | `factura_electronica_1`, `ica_descuento_50`, `mujeres_violencia_200` | ~1 h | Renta descuentos batch 2. |
| v17 b7 | `retencion_autoretencion`, `retencion_bases_minimas`, `retencion_tablas_ag_2025_2026` | ~1 h | Retención block. |
| v17 b8 | `aportes_parafiscales_seguridad_social`, `pagos_no_constitutivos_salario` | ~45 min | Renta deducciones extras. |
| v17 b9 | `ttd_tasa_minima`, `zomac_zese`, `niif_depreciacion_niif_vs_fiscal` | ~1 h | Tarifas + NIIF. |
| v17 b10 | `panel_cierre_fiscal_anual_checklist`, `panel_ica_territorial`, `panel_migracion_rst_ordinario`, `panel_reteica_municipal` | ~1.5 h | Panel adiciones — heavy on cross-topic guards. |
| v17 b11 | `tier2_doc_comprobatoria_f1125_f1729`, `tier2_impuesto_patrimonio`, `tier2_omision_activos_434a` | ~1 h | Tier 2 batch 1. |
| v17 b12 | `tier2_precios_transferencia_umbrales`, `tier2_recursos_dian`, `tier2_renta_presuntiva_historico` | ~1 h | Tier 2 batch 2. |

**Total: ~12 hours engineering** across 12 batches. Operator review
adds ~15 min per topic.

Per `feedback_canonicalizer_autonomous_progression`, an autonomous
operator session may proceed b1 → b12 without per-batch check-ins as
long as the §4 + §6 criteria fire green. Stop only when a batch hits
the §5 "≥ 1 fail per batch" pause condition.

---

## §10. Known residuals (NOT in v17 scope)

1. **Non-ET-anchor schema change.** Many labor / panel / Ley
   anchors are still mapped to the closest ET tie-in (§3.3 Option A).
   A future fix should extend `_CASE_ANCHOR_REGISTRY` to support
   `kind="ley"` / `kind="decreto"` / `kind="sentencia"` and migrate
   these topics. Out of scope here.
2. **Polish UVT validator cue extension.** New anchors flow into
   `_no_invented_uvt_ranges` via `CASE_REGISTRY.anchor_articles`
   automatically (fix_v15_may §3). No flag change.
3. **A4 substantive fallback bullet quality.** When polish rejects,
   A4 builds the answer from `CaseSpec.bullets`. Verify each new
   topic's bullets render cleanly in the fallback shape (no broken
   tables, no orphaned `**bold**` sections). Track residuals in
   `docs/aa_next/playbook_regressions.md`.
4. **Latency 23-32 s** is consistent across all probes. Within the
   system's normal range; tracked separately if/when SLA matters.

---

## §11. Change log entry (to be appended after merge)

Append to `docs/orchestration/orchestration.md` under `### Change Log`
the following row (verbatim, with the merge date filled in):

```
- v2026-MM-DD-fix-v17-lane-b-wiring-for-37-playbooks
  - Adds 37 CaseSpec rows to case_bullets/CASE_REGISTRY (one per
    Lane-A-only playbook that fix_v16_may + corpusfix_v1 shipped).
  - No env flag changes; no schema changes.
  - Rollback: per-topic via row + sibling-file removal.
```

Mirror the row in `docs/guide/env_guide.md` `## Runtime Retrieval
Flags` ("no flag delta, content-only batch"). `CLAUDE.md` Hot Path
section unchanged.

---

## §12. Ship-state table (update as batches land)

Mark each topic 🛠 / 🧪 / ✅ / ↩ as it progresses. A fresh executing
agent should update this section IN THE SAME COMMIT as the code
change.

| Batch | Topic | Status | Probe verdict | Notes |
|---|---|---|---|---|
| v17 b1 | `liquidacion_mensual_nomina` | 🛠 | — | |
| v17 b1 | `prestaciones_sociales` | 🛠 | — | |
| v17 b1 | `liquidacion_terminacion` | 🛠 | — | |
| v17 b2 | `pila_aportes` | 🛠 | — | |
| v17 b2 | `ugpp_fiscalizacion` | 🛠 | — | |
| v17 b2 | `nomina_electronica_dspne` | 🛠 | — | |
| v17 b3 | `contrato_prestacion_vs_laboral` | 🛠 | — | |
| v17 b3 | `contrato_aprendizaje_sena` | 🛠 | — | |
| v17 b3 | `salario_integral` | 🛠 | — | order BEFORE nómina core |
| v17 b4 | `embargos_salario` | 🛠 | — | |
| v17 b4 | `smmlv_aux_transporte_anual` | 🛠 | — | |
| v17 b4 | `subsidios_transporte_alimentacion` | 🛠 | — | |
| v17 b4 | `teletrabajo_trabajo_casa` | 🛠 | — | |
| v17 b5 | `discapacidad_200` | 🛠 | — | non-ET anchor (Ley 361) |
| v17 b5 | `donaciones_descuento` | 🛠 | — | |
| v17 b5 | `energias_renovables` | 🛠 | — | non-ET anchor (Ley 1715) |
| v17 b6 | `factura_electronica_1` | 🛠 | — | non-ET anchor (Ley 2277) |
| v17 b6 | `ica_descuento_50` | 🛠 | — | order vs ICA deduction case |
| v17 b6 | `mujeres_violencia_200` | 🛠 | — | non-ET anchor (Ley 1257) |
| v17 b7 | `retencion_autoretencion` | 🛠 | — | non-ET anchor (Decreto 2201) |
| v17 b7 | `retencion_bases_minimas` | 🛠 | — | non-ET anchor (Decreto 572/2025) |
| v17 b7 | `retencion_tablas_ag_2025_2026` | 🛠 | — | |
| v17 b8 | `aportes_parafiscales_seguridad_social` | 🛠 | — | |
| v17 b8 | `pagos_no_constitutivos_salario` | 🛠 | — | |
| v17 b9 | `ttd_tasa_minima` | 🛠 | — | order vs tarifa_general_pj |
| v17 b9 | `zomac_zese` | 🛠 | — | dedicated topic key |
| v17 b9 | `niif_depreciacion_niif_vs_fiscal` | 🛠 | — | order vs depreciacion case |
| v17 b10 | `panel_cierre_fiscal_anual_checklist` | 🛠 | — | transversal — careful with veto guards |
| v17 b10 | `panel_ica_territorial` | 🛠 | — | |
| v17 b10 | `panel_migracion_rst_ordinario` | 🛠 | — | |
| v17 b10 | `panel_reteica_municipal` | 🛠 | — | order BEFORE ica_territorial |
| v17 b11 | `tier2_doc_comprobatoria_f1125_f1729` | 🛠 | — | order AFTER umbrales |
| v17 b11 | `tier2_impuesto_patrimonio` | 🛠 | — | |
| v17 b11 | `tier2_omision_activos_434a` | 🛠 | — | |
| v17 b12 | `tier2_precios_transferencia_umbrales` | 🛠 | — | order BEFORE doc_comprobatoria |
| v17 b12 | `tier2_recursos_dian` | 🛠 | — | |
| v17 b12 | `tier2_renta_presuntiva_historico` | 🛠 | — | secondary_topic add needed |

Status legend:
- 🛠 — code landed, not yet probed.
- 🧪 — verified locally (unit tests green).
- ✅ — verified in dev:staging via `answer-engine-probe` + operator review.
- ↩ — regressed and discarded with reason (recorded in
  `docs/aa_next/playbook_regressions.md`).

---

## §13. Author notes for the executing agent

- **Idempotency.** Adding a topic is idempotent: re-running the
  intake on the same playbook produces the same code edits. The
  registry is a tuple with a stable order — appending the same
  SPEC twice would just shadow the second; remove duplicates if
  you see them.
- **Granularity.** Per `feedback_granular_edits`, do NOT append to
  any module already ≥ 1000 LOC.
  `case_detectors_b5.py` is the current last sibling; check its
  size before adding the 38th detector and create
  `case_detectors_b6.py` if it crosses 800 LOC. Same rule for
  `answer_synthesis_sections.py` if it ever grows past 1500 LOC.
- **Verification non-negotiable.** Per `feedback_no_hallucinated_examples`,
  every numeric value, article reference, plazo, monto, or registro
  detail you wire into bullets MUST be verifiable against the
  expert's playbook URLs. If the expert wrote it but the URL no
  longer resolves, STOP and flag it before landing.
- **No new env flags.** v17 is registry-content only. If you find
  yourself adding `LIA_*` flags, you are extending scope — stop and
  surface the question.
- **No money in status reports.** Per `feedback_no_money_quoting`,
  report effort in time + scope, not currency.
- **Plain language in operator updates.** Per
  `feedback_plain_language_communication`, end-of-batch reports to
  the operator are plain language by default; engineering depth only
  when asked.
- **Default run mode is dev:staging.** Per
  `feedback_default_run_mode_staging`. Verify via
  `retrieval_backend=supabase` on first response of each probe run.
- **SME panel runs only on explicit request.** Per
  `feedback_sme_panel_explicit_request_only`. Do NOT auto-run
  `scripts/eval/run_sme_parallel.py` after a batch lands — finish
  the code + tests + per-topic probes, then ASK before launching the
  panel.

---

*End of fix_v17_may.md.*
