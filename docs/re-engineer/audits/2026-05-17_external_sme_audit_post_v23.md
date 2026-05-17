# 2026-05-17 external SME audit — post-v23 dual-packet

> Verbatim audit delivered by external Colombian-accountant SME on 2026-05-17 PM Bogotá.
> Production endpoint tested: `https://liagraph-production.up.railway.app`.
> v25 closing-gate evidence per fix_v25_may.md D-S2. Do not edit content; append-only.

## Packet 1 — rerun of original v23 baseline (Q1–Q10)

- Original baseline (pre-v23): **1.85 / 5** average.
- Rerun (post-v23): **2.15 / 5** average. Net **+0.30**.
- Best advances: Q1 (1→2.5), Q2 (2→3), Q6 (1→2), Q7 (2→2.5).
- Unresolved: Q5 revisor fiscal still polluted; Q8 RUB regressed (refusal → hallucination); Q3 IVA periodicidad still skips ET 600; Q10 still mutates COP 3,000,000 → 2,000,000.

| # | Topic | Original | Rerun | Movement | Failure shape |
|---|---|---:|---:|---|---|
| 1 | Documento soporte | 1.0 | 2.5 | + | Misses Res. DIAN 000167/2021; cites ET 240-1 wrongly |
| 2 | Retenciones | 2.0 | 3.0 | + | UVT 2026 correct; under-answers compras; thin legal base |
| 3 | Periodicidad IVA | 1.0 | 1.5 | + (weak) | No ET 600; emits "Cobertura pendiente para esta sub-pregunta" |
| 4 | Nómina | 3.0 | 3.0 | = | Citation hygiene noisy; ET 617 leaks into payroll |
| 5 | Revisor fiscal | 1.0 | 1.0 | = | Acta "DISTRIBUIDORA EL SOL SAS / ALEJANDRO VASQUEZ ARANGO" still surfaces; cites ET 1/49/660 instead of CCo 203 + Ley 43/1990 art. 13 |
| 6 | Régimen Simple | 1.0 | 2.0 | + | Adds irrelevant INC vehicle arts. 512-3/4/5; assumes CIIU 4711 |
| 7 | Información exógena | 2.0 | 2.5 | + (weak) | Pseudo-citations `art. 6-10` / `art. introducci-n…`; names Res. 000233/2025 |
| 8 | RUB | 1.0 | 1.0 | safety regression | Hallucinated "Carlos Moreno Pérez"; mixes INCRNGO / donations |
| 9 | Cartera (deterioro) | 3.5 | 3.0 | − | Core ET 145/146 good; Concepto DIAN 191/2025 (depreciación) polluted |
| 10 | Activo fijo computador | 2.0 | 2.0 | = | COP 3,000,000 → 2,000,000 mutation persists; stale 2025 UVT threshold |

## Packet 2 — new critical accountant topics (Q11–Q20)

- Average: **2.35 / 5**.
- Best: Q12 IVA prorrateo (3.5).
- Worst: Q11 ICA Bogotá territorialidad (1.0); Q14 cloud abroad (1.0).

| # | Topic | Score | Failure shape |
|---|---|---:|---|
| 11 | ICA + reteICA Bogotá territorialidad | 1.0 | Drifts to RST + TTD + ET 240/115; no Bogotá SHD (Acuerdo 65/2002, Decreto 352/2002); no territoriality rule |
| 12 | IVA proporcional / prorrateo | 3.5 | Right formula (ET 490); polluted with IVA-responsibility + retención-services-abroad |
| 13 | Contratistas + seguridad social (40 % IBC) | 3.0 | Practical; 4 UVT = `$199.000` (real 4 UVT 2026 = `$209.496`); no UGPP grounding |
| 14 | Software cloud sin domicilio en Colombia | 1.0 | Treats foreign supplier as domestic; misses ET 408 / 437-2 / 420 par.3 / 124-1; no DTT review |
| 15 | Dividendos (residente + extranjero) | 2.0 | Recognizes art. 49 ET; misses art. 245 ET (no-residente); inserts INCRNGO donations rule |
| 16 | Precios de transferencia | 2.5 | Injects Panama 1,930M counterfactual over user's 6,000M / 18,000M facts |
| 17 | Pérdidas fiscales | 3.0 | Solid ET 147/714; noise from TTD; injects "InnovaLab" example |
| 18 | Notas crédito / débito FE | 2.5 | Misses Resolución DIAN 000165/2023; weak buyer-events workflow |
| 19 | Leasing NIIF Pymes + fiscal | 2.5 | **Critical framework error**: applies NIIF 16 (IFRS Plenas) to NIIF Pymes question; should use Sección 20 |
| 20 | RTE / ESAL anual | 2.5 | **Critical date error**: claims "enero a junio 30" annual update; real DIAN deadline is March 31 |

## Cross-cutting generic weaknesses surfaced (v25 mandate)

| ID | Pattern | Audit Qs |
|---|---|---|
| G8 | Specific Resoluciones named in the question are not retrieved (000167/2021, 000165/2023, 000164/2021, 000233/2025) | Q1, Q7, Q8, Q18 |
| G9 | Cross-border / payments-to-abroad context defaults to domestic ET 392 | Q14 (and partly Q15 extranjero) |
| G10 | Municipal / district tax (ICA Bogotá SHD) defaults to national TTD / RST | Q11 |
| G11 | Framework awareness (NIIF Pymes vs IFRS 16) is missing | Q19 |
| G12 | Sub-question coverage gaps surface as `"Cobertura pendiente"` non-answers | Q3, Q12, Q16 |
| G13 | Compliance deadlines (RTE annual update March 31, exógena calendar, 4 UVT 2026) wrong or missing | Q7, Q13, Q20 |
| G14 | Fallback path remutates user numerics after polish-reject | Q10 |
| G15 | Retrieval pollution persists (named persons, acta templates, Concepto DIAN 191/2025 depreciación, INC vehicle arts.) | Q5, Q6, Q8, Q9, Q15 |
| G16 | Counterfactual injection — answer introduces named persons, companies, or monetary facts NOT in the question or evidence | Q5, Q8, Q16, Q17 |

## Recommended next regression tests (v25 closes against these)

- Audit packet 1 verbatim re-run (Q1–Q10) — must lift above v23's 2.15/5.
- Audit packet 2 verbatim (Q11–Q20) — must lift above 2.35/5 baseline.
- D-S2 closing bar (carried from v23): avg ≥ 4.0/5 + zero 1s on the combined 20-question superset.

## References (verbatim from SME)

- DIAN UVT 2026 / Resolución 000238 de 2025: https://www.dian.gov.co/Prensa/Paginas/NG-Comunicado-de-Prensa-128-2025.aspx
- DIAN calendar 2026: https://www.dian.gov.co/Paginas/CalendarioTributario.aspx
- Estatuto Tributario: https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm
- Resolución DIAN 000167 de 2021 (documento soporte): https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_0167_2021.htm
- Resolución DIAN 000013 de 2021 (nómina electrónica): https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_0013_2021.htm
- Resolución DIAN 000164 de 2021 (RUB): https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_0164_2021.htm
- Resolución DIAN 000165 de 2023 (FE notas crédito/débito + eventos): https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_0165_2023.htm
- DIAN RTE: https://www.dian.gov.co/impuestos/sociedades/Regimen-Tributario-Especial-RTE/
- DIAN exógena AG 2025: https://www.dian.gov.co/impuestos/sociedades/ExogenaTributaria/CalendarioExogena/Paginas/vigencia-2025.aspx
- UGPP independiente: https://www.ugpp.gov.co/seguridad-social-trabajadores-independientes/
- Bogotá SHD Acuerdo 65/2002: https://compilacionjuridica.shd.gov.co/compilacion/docs/a_conbog_0065_2002.htm
- Bogotá SHD Decreto 352/2002: https://compilacionjuridica.shd.gov.co/compilacion/docs/d_alcabog_0352_2002.htm
