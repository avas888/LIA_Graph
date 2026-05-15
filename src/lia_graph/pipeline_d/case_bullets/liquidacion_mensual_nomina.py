"""v17 b1 — liquidación mensual de nómina (CST + Ley 100/1993 + art. 114-1 ET).

Anchored at ET arts. 108 + 387 (per fix_v17_may §3.3 Option A — closest
ET tie-in). The non-ET norms (CST 127/128/132/159/168/179, Ley 100/1993,
Ley 1393/2010 art. 30) are cited in the body bullets.
"""
from __future__ import annotations

from ..case_detectors import is_liquidacion_mensual_nomina_case
from ..presentation import with_sub_bullets
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="liquidacion_mensual_nomina",
    detector=is_liquidacion_mensual_nomina_case,
    bullets=(
        "**Devengado mensual (CST):** salario básico + auxilio de transporte (cuando salario **≤ 2 SMMLV**, art. 7 Ley 1/1963) + recargos y horas extras. **Auxilio de transporte no es salario** pero **sí integra base de prestaciones**.",
        with_sub_bullets(
            "**Recargos y horas extras (CST arts. 159, 168, 179):**",
            (
                "trabajo nocturno (21:00–06:00) **+ 35 %**",
                "hora extra diurna **+ 25 %**",
                "hora extra nocturna **+ 75 %**",
                "dominical/festivo ocasional **+ 75 %**",
                "hora extra diurna en dominical **+ 100 %**",
                "hora extra nocturna en dominical **+ 150 %**",
            ),
        ),
        with_sub_bullets(
            "**Aportes empleado (descuentos en nómina sobre IBC):**",
            (
                "salud **4 %**",
                "pensión **4 %**",
                "solidaridad pensional **+ 1 %** si gana ≥ 4 SMMLV",
                "subcuenta de subsistencia **+ 0,2 % a 1 %** escalonado si gana 16–25 SMMLV",
            ),
        ),
        with_sub_bullets(
            "**Aportes empleador sobre IBC:**",
            (
                "salud **8,5 %** (exonerado para sociedades sobre empleados < 10 SMMLV — **art. 114-1 ET**)",
                "pensión **12 %**",
                "ARL **0,522 %–6,960 %** según clase de riesgo",
                "SENA **2 %** (exonerado 114-1)",
                "ICBF **3 %** (exonerado 114-1)",
                "Caja de Compensación **4 %** — **siempre se paga, nunca exonerada**",
            ),
        ),
        "**IBC mínimo = 1 SMMLV; IBC máximo = 25 SMMLV.** Cotizar al SMMLV cuando el salario real es mayor es una de las observaciones UGPP más frecuentes — el IBC es el salario real, mínimo el SMMLV.",
        "**Pagos no salariales (CST art. 128) + tope 40 % (Ley 1393/2010 art. 30):** auxilios de alimentación, conectividad, herramientas, bonificaciones ocasionales pueden pactarse como no salariales. **Si exceden el 40 % del total del ingreso, el exceso se cotiza igual** sobre IBC. Es el foco crítico de revisión UGPP.",
        "**Deducibilidad fiscal del costo laboral (art. 108 ET):** los salarios y prestaciones solo son deducibles en renta si se pagaron los aportes a seguridad social y parafiscales sobre la base correcta. La retención por salarios se calcula bajo **art. 383 ET + procedimientos 1 (mensual) o 2 (factor semestral) — art. 387 ET para deducciones del trabajador**.",
    ),
    keywords=(
        "nómina", "nomina",
        "liquidación", "liquidacion",
        "smmlv",
        "auxilio de transporte",
        "ibc",
        "recargo", "recargos",
        "nocturno", "diurno",
        "dominical", "festivo",
        "hora extra", "horas extras",
        "aporte", "aportes",
        "salud", "pensión", "pension",
        "solidaridad pensional",
        "arl",
        "clase de riesgo",
        "sena", "icbf",
        "caja de compensación", "caja de compensacion",
        "parafiscales",
        "art. 114-1", "art 114-1", "114-1",
        "art. 108", "art 108",
        "art. 387", "art 387",
        "art. 383", "art 383",
        "exoneración", "exoneracion",
        "no salarial",
        "ley 1393", "ley 1393 de 2010", "40%", "40 %",
        "ley 100", "ley 100 de 1993",
        "cst",
        "art. 127", "art 127",
        "art. 128", "art 128",
        "art. 159", "art 159",
        "art. 168", "art 168",
        "art. 179", "art 179",
        "decreto 1072",
        "25 smmlv",
        "10 smmlv",
        "2 smmlv",
    ),
    anchor_articles=("108", "387"),
    search_queries=(
        "liquidacion mensual nomina cst aportes seguridad social ibc art 108 et",
        "exoneracion parafiscales art 114-1 et caja compensacion siempre paga",
        "ley 1393 de 2010 art 30 tope 40 por ciento no salarial ibc",
    ),
    source_label="liquidacion_mensual_nomina_anchor",
)
