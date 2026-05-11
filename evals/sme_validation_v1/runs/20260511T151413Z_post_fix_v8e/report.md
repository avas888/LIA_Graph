# §1.G SME validation report

**Run dir:** `/Users/ava-sensas/Developer/Lia_Graph/evals/sme_validation_v1/runs/20260511T151413Z_post_fix_v8e`
**Generated:** 2026-05-11 10:18:55 AM Bogotá
**Questions classified:** 36 / 36

## Overall

| Class | Count |
|---|---|
| 🟢 served_strong | 26 |
| 🟡 served_acceptable | 8 |
| 🟠 served_weak | 0 |
| 🔵 served_off_topic | 1 |
| 🔴 refused | 1 |
| 💥 server_error | 0 |
| **total** | **36** |

## Per topic (12 × 3 grid)

| Topic | P1 directa | P2 operativa | P3 borde |
|---|---|---|---|
| beneficio_auditoria | 🟢 served_strong | 🟢 served_strong | 🟢 served_strong |
| firmeza_declaraciones | 🟢 served_strong | 🟢 served_strong | 🟢 served_strong |
| regimen_sancionatorio_extemporaneidad | 🔵 served_off_topic | 🟢 served_strong | 🟢 served_strong |
| descuentos_tributarios_renta | 🟢 served_strong | 🟡 served_acceptable | 🟢 served_strong |
| tarifas_renta_y_ttd | 🟢 served_strong | 🟢 served_strong | 🟢 served_strong |
| dividendos_y_distribucion_utilidades | 🟢 served_strong | 🟢 served_strong | 🟢 served_strong |
| devoluciones_saldos_a_favor | 🟢 served_strong | 🟢 served_strong | 🟢 served_strong |
| perdidas_fiscales_art147 | 🟡 served_acceptable | 🟢 served_strong | 🟢 served_strong |
| precios_de_transferencia | 🔴 refused | 🟢 served_strong | 🟢 served_strong |
| impuesto_patrimonio_personas_naturales | 🟡 served_acceptable | 🟢 served_strong | 🟡 served_acceptable |
| regimen_cambiario | 🟡 served_acceptable | 🟢 served_strong | 🟡 served_acceptable |
| conciliacion_fiscal | 🟢 served_strong | 🟡 served_acceptable | 🟡 served_acceptable |

## Per profile

| Profile | 🟢 served_strong | 🟡 served_acceptable | 🟠 served_weak | 🔵 served_off_topic | 🔴 refused | 💥 server_error |
|---|---|---|---|---|---|---|
| P1 | 7 | 3 | 0 | 1 | 1 | 0 |
| P2 | 10 | 2 | 0 | 0 | 0 | 0 |
| P3 | 9 | 3 | 0 | 0 | 0 | 0 |

## Routing accuracy

- Correct routing: **32/36**
- Wrong routing: **4/36**
- Unknown effective_topic: **0/36**

| qid | expected | actual | class |
|---|---|---|---|
| conciliacion_fiscal_P2 | conciliacion_fiscal | 'patrimonio_fiscal_renta' | 🟡 served_acceptable |
| conciliacion_fiscal_P3 | conciliacion_fiscal | 'patrimonio_fiscal_renta' | 🟡 served_acceptable |
| descuentos_tributarios_renta_P2 | descuentos_tributarios_renta | 'iva' | 🟡 served_acceptable |
| regimen_sancionatorio_extemporaneidad_P1 | regimen_sancionatorio_extemporaneidad | 'declaracion_renta' | 🔵 served_off_topic |

## Cross-checks (binding regardless of overall)

- `impuesto_patrimonio_personas_naturales`: refused 0/3 — ⚠ unexpected mix — investigate
- 11 baseline-SERVED topics with hidden full-refusals: 0 → ✅ none

## Retrieval signal check (fix_v7 §3a/3b/3c invariants)

- Traces inspected: **36** of 36
- ✅ `filter_topic` is None on every served chat (post-7a invariant holds)
- ✅ `embedding_mode == 'ok'` on every served chat (post-7b invariant holds)
- ✅ topic-gate `gate_mode` always in the expected set (post-7c invariant holds)
- 🟠 **Polish rejected on 21 qid(s)** (`polish_mode=rejected`): beneficio_auditoria_P1, beneficio_auditoria_P3, conciliacion_fiscal_P1, conciliacion_fiscal_P2, devoluciones_saldos_a_favor_P1, devoluciones_saldos_a_favor_P2, devoluciones_saldos_a_favor_P3, dividendos_y_distribucion_utilidades_P2, firmeza_declaraciones_P2, impuesto_patrimonio_personas_naturales_P1 … — `polish_skip_reason` distribution: anchors_stripped=3, invented_norm_lineage=4, invented_periods=14. The fix_v8 §3a substantive fallback should keep the answer useful when this fires; if the visible answers regressed, check the `polish.rejected.fallback_composed` trace step.

## Topics flagged for follow-up

### regimen_sancionatorio_extemporaneidad
- **regimen_sancionatorio_extemporaneidad_P1** — 🔵 served_off_topic (mode=`graph_native`, cites=4, len=331, effective_topic=`declaracion_renta`, fallback_reason=`None`)
  - **Q:** ¿Cuánto cobra la DIAN por presentar una declaración de renta tarde si no hay impuesto a cargo?
  - **A (head):** **Respuestas directas** ⏎ - **¿Cuánto cobra la DIAN por presentar una declaración de renta tarde si no hay impuesto a cargo?** ⏎  ⏎ **Anclaje legal** ⏎ - Art. 100 — DETERMINACIÓN DE LA RENTA BRUTA EN CONTRATOS DE RENTA VITALICIA ⏎ - Art. 101 — LAS SUMAS PAGADAS COMO RENTA VITALICIA SON DEDUCIBLES ⏎ - Art. 102 —

### precios_de_transferencia
- **precios_de_transferencia_P1** — 🔴 refused (mode=`topic_safety_abstention`, cites=0, len=260, effective_topic=`precios_de_transferencia`, fallback_reason=`pipeline_d_coherence_primary_off_topic`)
  - **Q:** ¿Cuáles son los umbrales de patrimonio o ingresos a partir de los cuales una empresa colombiana queda obligada al régimen de precios de transferencia?
  - **A (head):** Detecté que los artículos primarios recuperados pertenecen al tema **costos_deducciones_renta**, no al tema clasificado **precios_de_transferencia**. Para evitar una respuesta autoritativa sobre el tema equivocado, confirma manualmente o reformula la consulta.

## Decision

**STATE: PASS** — 34/36 served_acceptable+ ≥ 22 threshold

- PASS = ≥22/36 served_acceptable+
- PARTIAL = 14–21/36 served_acceptable+
- FAIL = ≤13/36 served_acceptable+
