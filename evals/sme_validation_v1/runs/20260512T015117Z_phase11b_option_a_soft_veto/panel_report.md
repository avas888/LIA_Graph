# Expert-Panel mini-panel report

**Run timestamp:** 2026-05-11 08:54:47 PM Bogotá
**Server:** `http://127.0.0.1:8787`
**Run dir:** `evals/sme_validation_v1/runs/20260512T015117Z_phase11b_option_a_soft_veto`
**Questions file:** `evals/sme_validation_v1/questions_expert_panel_v1.jsonl`

## Aggregate

| Metric | Value |
|---|---|
| Total scored | 21 |
| Accept (top-3 had expected file) | 10 |
| Wrong | 11 |
| Server error | 0 |
| Accept rate | **47.6%** |
| Decision (§5.4: ≥70% pass, 50–69% refine, <50% discard) | **DISCARD** |

## Per question

| qid | topic | outcome | matched expected file |
|---|---|---|---|
| `ep_fe_cufe_contingencia_v1` | facturacion_electronica | accept | `CORE ya Arriba/FACTURACION_ELECTRONICA_OPERATIVA/EXPERTOS/FE-E01-interpretaciones-CUFE-contingencia-notas-credito.md` |
| `ep_fe_nuevos_documentos_dav_v1` | facturacion_electronica | accept | `CORE ya Arriba/to update/FE-ROADMAP-NUEVOS-DOCS-2026/FASE-1-CONTENIDO/EXPERTOS/T14-nuevos-documentos-electronicos-DAV-REI-retenciones-interpretaciones.md` |
| `ep_gmf_exencion_350uvt_v1` | gravamen_movimiento_financiero_4x1000 | wrong | `—` |
| `ep_iva_exentos_vs_excluidos_v1` | iva | wrong | `—` |
| `ep_iva_proporcionalidad_d1474_v1` | iva | accept | `CORE ya Arriba/IVA_COMPLETO/EXPERTOS/IVA-E02-interpretaciones-proporcionalidad-decreto-1474.md` |
| `ep_iva_regimen_responsables_v1` | iva | accept | `CORE ya Arriba/IVA_COMPLETO/EXPERTOS/IVA-E01-interpretaciones-regimen-responsables-topes.md` |
| `ep_laboral_parafiscales_especiales_v1` | laboral | wrong | `—` |
| `ep_laboral_reforma_2466_v1` | laboral | accept | `CORE ya Arriba/NUEVOS-DATOS-BRECHAS-MARZO-2026/03-REFORMA-LABORAL-LEY-2466/INTERPRETACION/T-REF-LABORAL-reforma-laboral-interpretaciones-expertos.md` |
| `ep_laboral_ugpp_desalarizacion_v1` | laboral | accept | `CORE ya Arriba/NOMINA_SEGURIDAD_SOCIAL/EXPERTOS/NOM-E01-interpretaciones-costos-laborales-UGPP-fiscalizacion.md` |
| `ep_proc_devoluciones_riesgo_auditoria_v1` | procedimiento_tributario | wrong | `—` |
| `ep_pt_paraisos_panama_v1` | precios_de_transferencia | accept | `CORE ya Arriba/Documents to branch and improve/Precios_Transferencia/Interpretacion_Expertos/pt_expertos_precios_transferencia.md` |
| `ep_pt_umbrales_pyme_v1` | precios_de_transferencia | wrong | `—` |
| `ep_renta_beneficio_auditoria_v1` | declaracion_renta | wrong | `—` |
| `ep_renta_conciliacion_2516_v1` | declaracion_renta | wrong | `—` |
| `ep_renta_deduccion_ica_v1` | declaracion_renta | wrong | `—` |
| `ep_renta_dividendos_242_v1` | declaracion_renta | accept | `CORE ya Arriba/DIVIDENDOS_UTILIDADES/EXPERTOS/DIV-E01-interpretaciones-dividendos-optimizacion-fiscal-PYME.md` |
| `ep_renta_patrimonio_niif_v1` | declaracion_renta | accept | `CORE ya Arriba/RENTA/EXPERTOS/T-J-patrimonio-fiscal-niif-vs-fiscal-conciliacion-2516.md` |
| `ep_renta_ttd_paragrafo6_v1` | declaracion_renta | wrong | `—` |
| `ep_retencion_autorretencion_especial_v1` | retencion_en_la_fuente | wrong | `—` |
| `ep_retencion_decreto_572_v1` | retencion_en_la_fuente | wrong | `—` |
| `ep_rst_elegibilidad_sectores_v1` | regimen_simple | accept | `CORE ya Arriba/RST_REGIMEN_SIMPLE/EXPERTOS/RST-E02-interpretaciones-tarifas-elegibilidad-sectores-RST.md` |
