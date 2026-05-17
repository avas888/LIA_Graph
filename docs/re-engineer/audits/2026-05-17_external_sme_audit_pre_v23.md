# 2026-05-17 — External Colombian-Accountant Audit (pre-v23)

> **Audit-archival note.** This file archives the 10-question audit that triggered v23 per `docs/re-engineer/fix/fix_v23_may.md`. The verbatim text delivered by the external accountant was not pasted into the v23 execution session — at execution time the operator authorized v23 to proceed using the audit findings already distilled into §1.2 of the v23 fix-doc. This file captures the questions in their canonical form (synthesized from §1.2 topics + audit-scoring weaknesses) for use as the permanent regression suite at `tests/test_audit_regression_q01_q10.py` and as the SME re-run script at P8. **Operator may replace each `Q.text` block below with the verbatim audit text at any time; the question topic + audit weakness + v23 phase mapping are load-bearing and must not be edited without re-baselining the regression suite.**
>
> **Provenance.** Audit delivered 2026-05-17 by external Colombian accountant against production LIA at `https://liagraph-production.up.railway.app`. Overall score `1.85 / 5`. v23 closing gate (P8) re-runs these same 10 questions with same 1–5 rubric.

---

## Rubric (1–5)

- **5 — Excellent.** Substantive, correctly cited, current-year accurate, locale-correct, addresses all parts.
- **4 — Good.** Substantive + mostly correct; minor citation/locale issues.
- **3 — Acceptable.** Useful core but missing parts or partly stale.
- **2 — Poor.** Major gaps (stale constants, wrong code labels, omitted sub-question).
- **1 — Failed.** Refusal / hallucinated entities / mutated user input.

---

## Q1 — Documento soporte facturación electrónica vs deducibilidad

- **Topic:** facturacion_electronica × deducibilidad_renta (multi-domain)
- **Pre-v23 score:** 1/5 (refused on topic mismatch — G1)
- **v23 phase:** P1 (Topic-Gate Decomposition)
- **Q.text:** "¿Cuándo debo expedir documento soporte de adquisición a no obligados a facturar electrónicamente, y qué requisitos debe cumplir para que mi compra sea deducible en renta?"

## Q2 — Retención en la fuente 2026

- **Topic:** retencion_fuente × calendario_obligaciones (AG 2026)
- **Pre-v23 score:** 2/5 (quoted UVT 2026 as COP 49,799 — stale; real = 52,374; cited `Art. notas-y-fuentes` — G2 + G3)
- **v23 phase:** P2 (year-constants) + P3 (source-code awareness)
- **Q.text:** "Para AG 2026, ¿cuál es la base mínima en UVT y la tarifa para retención en la fuente por servicios prestados por personas naturales declarantes y no declarantes?"

## Q3 — IVA periodicidad (regla 92,000 UVT)

- **Topic:** iva_periodicidad × obligaciones_formales (multi-domain)
- **Pre-v23 score:** 1/5 (refused on topic mismatch — G1)
- **v23 phase:** P1
- **Q.text:** "¿Mi cliente con ingresos brutos de 80.000 UVT en 2025 debe declarar IVA bimestral o cuatrimestral para 2026, y dónde está la regla?"

## Q4 — Nómina + auxilio transporte + nómina electrónica

- **Topic:** nomina × auxilio_transporte × nomina_electronica
- **Pre-v23 score:** 3/5 (useful, but cited `Art. 617 ET` for labor obligation that is actually CST/Resolución DIAN; mislabeled CST as ET — G3)
- **v23 phase:** P3 (generalizes v22 CST/ET fix)
- **Q.text:** "Para un trabajador que devenga 2 SMLMV en 2026, ¿debo pagar auxilio de transporte y reportarlo en nómina electrónica? Cite la norma laboral y la resolución de nómina electrónica vigente."

## Q5 — Revisor fiscal SAS topes

- **Topic:** revisor_fiscal × sas × obligaciones_formales
- **Pre-v23 score:** 1/5 (response contained literal `DISTRIBUIDORA EL SOL SAS` / `ALEJANDRO VASQUEZ ARANGO` / `Formulario 7`; cited `Art. ET 1/49/660/10` instead of `CCo art. 203` / `Ley 43/1990 art. 13 par. 2` — G3 + G4 pollution)
- **v23 phase:** P3 + P4
- **Q.text:** "¿Cuáles son los topes vigentes que obligan a una SAS a tener revisor fiscal, y cuál es el fundamento normativo (Código de Comercio y Ley 43 de 1990)?"

## Q6 — Régimen Simple restaurante + INC/IVA + ICA

- **Topic:** regimen_simple × restaurantes × inc × ica (multi-domain)
- **Pre-v23 score:** 1/5 (refused on topic mismatch — G1)
- **v23 phase:** P1
- **Q.text:** "Tengo un cliente restaurante en Régimen Simple. ¿Debe cobrar INC del 8% o IVA del 19%? ¿Cómo interactúa con ICA municipal y con la declaración anual del SIMPLE?"

## Q7 — Información exógena AG 2025

- **Topic:** informacion_exogena × calendario_obligaciones (AG 2025)
- **Pre-v23 score:** 2/5 (useful, but voseo "Verifica" / "Tene"; stale calendar — G6 + G2 calendar)
- **v23 phase:** P2 + P6
- **Q.text:** "¿Qué información exógena de AG 2025 debo reportar como contador de una persona jurídica del régimen ordinario, y en qué fechas?"

## Q8 — RUB beneficiarios finales (cadena de propiedad)

- **Topic:** rub × beneficiario_final × regimen_cambiario (multi-domain risk of mis-routing)
- **Pre-v23 score:** 1/5 (refused — régimen cambiario vs beneficiario final — G1)
- **v23 phase:** P1
- **Q.text:** "Mi cliente es una SAS cuyo socio mayoritario es una sociedad panameña. ¿Cómo reporto la cadena de propiedad en el RUB y qué plazo tengo?"

## Q9 — NIIF Pymes deterioro + ET 145/146 castigo

- **Topic:** niif_pymes × deterioro_cartera × castigo_cartera
- **Pre-v23 score:** 3.5/5 (best answer; polluted with irrelevant Concepto DIAN 191/2025 depreciación + pseudo-citations `ET 1` / `ET 28` — G3 + G4)
- **v23 phase:** P3 + P4
- **Q.text:** "Bajo NIIF para Pymes, ¿cuándo debo registrar deterioro de cartera y cuándo aplica el castigo fiscal del ET arts. 145 y 146 para deducibilidad en renta?"

## Q10 — Computador laptop activo fijo + depreciación + IVA descontable

- **Topic:** activos_fijos × depreciacion × iva_descontable
- **Pre-v23 score:** 2/5 (mutated user input COP 3,000,000 → 2,000,000; mixed 2025 + 2026 UVT in same answer; failed to address IVA fixed-asset treatment — G5 numeric mutation + G2 mixed years)
- **v23 phase:** P2 + P5
- **Q.text:** "Compré un computador laptop por $3.000.000 más IVA del 19% para mi empresa SAS en marzo 2026. ¿Lo deprecio y en qué vida útil, y puedo tomar IVA descontable?"

---

## v22-handoff probe (G7 — added 2026-05-17 ~12:50 PM post-v22 close)

- **Topic:** terminacion_contrato × cst (single-topic — testing Anclaje gate, not refusal)
- **Pre-v23 finding:** v22 closing probe (`tracers_and_logs/logs/probe_runs/20260517T174327Z_v22_t2_postfix/q01.json`) Anclaje Legal expanded from 1 → 4 lines with 3 off-topic ET articles (Art. 102 / 102-2 / 103 ET)
- **v23 phase:** P7
- **Q.text:** "¿Qué dice el artículo 64 del CST sobre la terminación sin justa causa del contrato de trabajo?"

---

## Closing-gate target (D-S2)

- Same 10 questions (verbatim) re-run by the same external accountant on production.
- Pass = **avg score ≥ 4.0 / 5 AND zero scores of 1**.
- One question at 3 is acceptable; any 1 reopens the failing phase per `feedback_thresholds_no_lower`.
- SME verdict archived at `docs/re-engineer/audits/<UTC>_v23_closing_sme_verdict.md`.
