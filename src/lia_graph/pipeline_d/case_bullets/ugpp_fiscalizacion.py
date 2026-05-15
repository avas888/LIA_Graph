"""v17 b2 — UGPP fiscalización de aportes (Ley 1607/2012 arts. 178-179).

Anchored at ET arts. 108 + 114-1 (Option A per fix_v17_may §3.3). El
régimen sustantivo está en Ley 1607/2012 arts. 178-179 (facultades + sanciones),
Decreto 575/2013 (procedimiento), Ley 1393/2010 art. 30 (tope 40 % no
salarial), citados en bullets.
"""
from __future__ import annotations

from ..case_detectors import is_ugpp_fiscalizacion_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="ugpp_fiscalizacion",
    detector=is_ugpp_fiscalizacion_case,
    bullets=(
        "**Facultades UGPP (Ley 1607/2012 art. 178):** verificar cumplimiento de aportes al SGSS (salud, pensión, ARL) y parafiscales (SENA, ICBF, Cajas); determinar y cobrar aportes omitidos; imponer sanciones; solicitar información; cruzar con DIAN, EPS, AFP, ARL, Cajas y Min. Trabajo. **Prescripción de la acción de cobro: 5 años** desde que el aporte se hizo exigible (Ley 1066/2006 art. 8).",
        "**Procedimiento de fiscalización (Decreto 575/2013):** (1) requerimiento de información — plazo **15 días hábiles** prorrogables; (2) pliego de cargos — **3 meses** para responder o corregir con sanción reducida; (3) resolución sanción / liquidación oficial; (4) recursos: **reposición 2 meses** ante UGPP, apelación ante el superior, **acción de nulidad y restablecimiento del derecho** ante Tribunal Administrativo en **4 meses**.",
        "**Tope crítico — Ley 1393/2010 art. 30:** los pagos no salariales pactados (CST art. 128) no pueden exceder el **40 % del total del ingreso** del trabajador. **El exceso se cotiza igual** sobre IBC. Es el **principal foco de revisión UGPP en PYMEs** — auditar nómina mes a mes.",
        "**Sanciones — Ley 1607/2012 art. 179:** **omisión de afiliados 35 %** de la diferencia; **inexactitud 60 %** de la diferencia; **mora 5 % por mes o fracción** del aporte hasta **100 %** + intereses art. 635 ET; **no suministrar información: 5 SMMLV por falta, hasta 15.000 UVT total**; **reincidencia +20 %** sobre la sanción base.",
        "**Presunción de costos — independientes (Decreto 1601/2022 + Ley 2010/2019):** la UGPP puede presumir **costos del 40 % de los ingresos brutos** para PN con rentas de prestación de servicios, salvo prueba en contrario. Si no se demuestran costos reales > 40 %, paga aportes sobre el 60 % restante × 40 % → **IBC final ≈ 24 % del ingreso bruto**, con piso de 1 SMMLV.",
        "**Doctrina del Consejo de Estado — desalarización procede solo si:** (a) pacto **expreso y por escrito**; (b) concepto **ocasional o por mera liberalidad**; (c) **no** retribuye servicios prestados (no es contraprestación habitual); (d) **no** supera el 40 % del total. Si UGPP demuestra habitualidad y contraprestación, reclasifica como salario y recotiza.",
        "**Estrategia de corrección voluntaria — sanción reducida:** antes del pliego de cargos = **20 %** de la sanción base; dentro de los **3 meses** del requerimiento = **80 %**. Defensa exige: nómina completa, contratos, anexos de no salariales, PILA, declaraciones de renta y exógena, **art. 108 ET** como ancla de deducibilidad del costo laboral en renta + **art. 114-1 ET** para validar exoneración SENA/ICBF/salud por trabajadores < 10 SMMLV.",
    ),
    keywords=(
        "ugpp",
        "fiscalización ugpp", "fiscalizacion ugpp",
        "requerimiento ugpp",
        "sanción ugpp", "sancion ugpp",
        "ley 1607 de 2012",
        "art. 178", "art 178",
        "art. 179", "art 179",
        "decreto 575 de 2013", "decreto 575/2013",
        "decreto 1601 de 2022",
        "ley 1393 de 2010 art 30",
        "art. 30 ley 1393",
        "40% no salarial", "40 % no salarial",
        "40 por ciento no salarial",
        "tope 40",
        "art. 128 cst", "art 128 cst",
        "desalarización", "desalarizacion",
        "pagos no salariales",
        "no constitutivo de salario",
        "presunción de costos", "presuncion de costos",
        "60 %", "60%",
        "35 %", "35%", "60 %",
        "5 %", "5%", "5% por mes",
        "100 %", "100%",
        "5 smmlv", "15.000 uvt", "15000 uvt",
        "reincidencia",
        "reposición", "reposicion",
        "apelación", "apelacion",
        "tribunal administrativo",
        "5 años", "5 anos",
        "ley 1066 de 2006",
        "art. 108", "art 108",
        "art. 114-1", "art 114-1",
        "consejo de estado",
        "sección cuarta", "seccion cuarta",
        "elusión", "elusion",
        "evasión", "evasion",
        "pliego de cargos",
        "corrección voluntaria", "correccion voluntaria",
        "20 %", "20%", "80 %", "80%",
    ),
    anchor_articles=("108", "114-1"),
    search_queries=(
        "ugpp fiscalizacion aportes ley 1607 de 2012 arts 178 179 sanciones",
        "ley 1393 de 2010 art 30 tope 40 por ciento no salarial ibc exceso",
        "desalarizacion consejo de estado seccion cuarta requisitos pacto escrito",
    ),
    source_label="ugpp_fiscalizacion_anchor",
)
