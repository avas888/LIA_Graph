"""v17 b2 — PILA (Planilla Integrada de Liquidación de Aportes).

Anchored at ET arts. 108 + 114-1 (Option A per fix_v17_may §3.3). El
régimen sustantivo está en Decreto 1990/2016, Resolución Min. Salud
2388/2016 y Decreto 1273/2018 (independientes mes vencido), citados en
bullets.
"""
from __future__ import annotations

from ..case_detectors import is_pila_aportes_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="pila_aportes",
    detector=is_pila_aportes_case,
    bullets=(
        "**Quién declara PILA:** empleadores con al menos 1 trabajador (tipo **E**); independientes con ingresos ≥ 1 SMMLV (tipo **I**); trabajadores domésticos con sus empleadores; pensionados con ingresos adicionales; cooperativas, agremiaciones y contratistas de servicios personales. PILA Electrónica es obligatoria con **≥ 11 trabajadores** (Decreto 1670/2007).",
        "**Plazos de pago — Decreto 1990 de 2016 (calendario por último dígito NIT):** 00–07 → día 2; 08–14 → día 3; 15–21 → día 4; 22–28 → día 5; 29–35 → día 6; 36–42 → día 7; 43–49 → día 8; 50–56 → día 9; 57–63 → día 10; 64–69 → día 11; 70–75 → día 12; 76–81 → día 13; 82–87 → día 14; 88–93 → día 15; 94–99 → día 16. Días hábiles del mes siguiente al causado.",
        "**Independientes — Decreto 1273/2018 (mes vencido):** plazo por último dígito de cédula con la misma escala. **IBC = 40 % de los ingresos brutos mensualizados** (Ley 1955/2019 art. 244 + Decreto 1601/2022), **mínimo 1 SMMLV**, tope **25 SMMLV**.",
        "**Operadores PILA autorizados (Resolución Min. Salud 2388/2016):** SOI / Aportes en Línea, Mi Planilla, Asopagos, Suaporte, Simple, Arus, y Banco Agrario (PILA Asistida en zonas sin internet). **PILA Asistida (tipo Y)** para empleadores < 11 trabajadores que no pueden hacerla electrónica.",
        "**Tarifas de aportes consolidadas (IBC empleado):** salud empleado **4 %** + empleador **8,5 %** (exonerado 114-1 sobre empleados < 10 SMMLV); pensión empleado **4 %** (+ **1 % solidaridad** si ≥ 4 SMMLV) + empleador **12 %**; ARL **0,522 %–6,960 %** según clase de riesgo; SENA **2 %** + ICBF **3 %** (exonerados 114-1); **Caja de Compensación 4 % — siempre se paga, nunca exonerada**.",
        "**Correcciones — tipo de planilla:** **N (novedades)** para ajustar valores, fechas o conceptos sobre planilla ya pagada; **A (adicionada)** para incluir aportantes omitidos; **Y/X** para ajustes especiales según operador.",
        "**Sanciones por mora y consecuencias fiscales:** **intereses moratorios** a la tasa del impuesto sobre la renta (art. 635 ET supletoriamente); **sanción administrativa UGPP del 5 % por mes o fracción**, hasta el **100 %** del aporte (Ley 1607/2012 art. 179); **pérdida de deducibilidad del costo laboral en renta — art. 108 ET** si los aportes no se pagaron antes de presentar la declaración. **Exoneración SENA / ICBF / salud** sólo aplica con cumplimiento del art. 114-1 ET.",
    ),
    keywords=(
        "pila",
        "planilla integrada",
        "planilla integrada de liquidación", "planilla integrada de liquidacion",
        "decreto 1990 de 2016", "decreto 1990",
        "resolución 2388", "resolucion 2388",
        "decreto 1273 de 2018",
        "decreto 1601 de 2022",
        "ley 1955 de 2019 art 244",
        "operador pila",
        "operadores pila",
        "soi", "aportes en línea", "aportes en linea",
        "mi planilla", "asopagos", "suaporte", "simple", "arus",
        "pila asistida",
        "tipo e", "tipo i",
        "planilla n", "planilla a",
        "último dígito", "ultimo digito", "nit",
        "ibc independiente",
        "ibc mínimo", "ibc minimo",
        "ibc máximo", "ibc maximo",
        "smmlv",
        "25 smmlv",
        "40% ingresos", "40 % ingresos",
        "mes vencido",
        "art. 108", "art 108",
        "art. 114-1", "art 114-1", "114-1",
        "exoneración 114-1", "exoneracion 114-1",
        "caja de compensación", "caja de compensacion",
        "sena", "icbf",
        "salud",
        "pensión", "pension",
        "solidaridad pensional",
        "arl",
        "mora",
        "ley 1607 de 2012",
        "art. 179", "art 179",
        "art. 635", "art 635",
        "intereses moratorios",
    ),
    anchor_articles=("108", "114-1"),
    search_queries=(
        "pila planilla integrada aportes decreto 1990 de 2016 calendario nit",
        "independientes pila decreto 1273 de 2018 ibc 40 por ciento ingresos",
        "exoneracion aportes parafiscales art 114-1 et empleados menos de 10 smmlv",
    ),
    source_label="pila_aportes_anchor",
)
