"""v16 b3 — retención en la fuente por salarios (art. 383 ET).

v23 P2-T5 — replaced the hardcoded stale `AG 2025 $47.065` (47,065 is the
2024 UVT, NOT the 2025 UVT) with a year_facts lookup. The audit Q2 surfaced
this as a stale-year-constant bug; v23 P2 closes G2.
"""
from __future__ import annotations

from ...year_facts import get_year_facts
from ..case_detectors import is_retencion_salarios_case
from ._registry import CaseSpec


def _uvt_2025_label() -> str:
    facts = get_year_facts(2025)
    if facts and facts.uvt and facts.uvt.verified and facts.uvt.value_cop:
        formatted = f"{facts.uvt.value_cop:,}".replace(",", ".")
        return f"AG 2025 ${formatted}"
    return "AG 2025"


SPEC = CaseSpec(
    name="retencion_salarios",
    detector=is_retencion_salarios_case,
    bullets=(
        f"**Tabla art. 383 ET (UVT del año del pago — {_uvt_2025_label()}):** Rangos UVT y tarifa marginal — **0–95: 0 %**; **95–150: 19 %**; **150–360: 28 %**; **360–640: 33 %**; **640–945: 35 %**; **945–2.300: 37 %**; **>2.300: 39 %**. Aplica acumulado escalonado por tramos.",
        "**Procedimiento 1 — art. 385 ET (mensual):** depure mes a mes la base, conviértala a UVT del año del pago y aplique la tabla del art. 383 ET. Ideal cuando el ingreso es estable.",
        "**Procedimiento 2 — art. 386 ET (semestral con factor):** calcule un **factor (% fijo)** en junio y diciembre, aplicable los seis meses siguientes. Útil cuando hay prima, bonificaciones o pagos extraordinarios — distribuye carga uniformemente.",
        "**Depuración base art. 388 ET (orden):** (1) total pagos laborales del mes; (2) menos ingresos no constitutivos: aportes obligatorios salud (4 %) y pensión (4 %); (3) menos deducciones art. 387 ET — intereses vivienda hasta **100 UVT/mes**, medicina prepagada hasta **16 UVT/mes**, dependientes **72 UVT/año** (10 % renta hasta **32 UVT/mes**); (4) menos rentas exentas — aportes voluntarios pensiones/AFC (límite combinado 30 % ingreso, hasta **3.800 UVT/año**) + **25 % renta exenta laboral** del art. 206 num. 10 (tope **790 UVT/año**).",
        "**Tope global (art. 336 / 388 ET):** las rentas exentas + deducciones no pueden exceder **40 % de los ingresos** menos no-constitutivos, ni **1.340 UVT/año** (Ley 2277/2022).",
        "**Indemnizaciones laborales (art. 401-3 ET):** si el salario mensual del trabajador (sin contar la indemnización) excede **204 UVT**, se retiene **20 %** sobre el valor de la indemnización. Por debajo, no hay retención.",
        "**Ley 2277/2022 — clave:** redujo el tope de rentas exentas laborales al 25 % limitado a **790 UVT/año** (antes 2.880 UVT) y mantuvo el límite global **40 % / 1.340 UVT**.",
    ),
    keywords=(
        "retención", "retencion",
        "salarios", "salario",
        "nómina", "nomina",
        "383", "385", "386", "387", "388", "206", "401-3", "336", "126-1", "126-4",
        "procedimiento 1", "procedimiento 2",
        "uvt", "49799", "49.799",
        "0%", "19%", "28%", "33%", "35%", "37%", "39%",
        "20%",
        "95", "150", "360", "640", "945", "2.300", "2300", "204",
        "25%",
        "40%",
        "790 uvt", "1.340 uvt", "1340 uvt", "3.800 uvt", "100 uvt", "16 uvt", "32 uvt", "72 uvt",
        "depuración", "depuracion",
        "dependientes",
        "intereses vivienda",
        "medicina prepagada",
        "aportes voluntarios",
        "afc",
        "ley 2277",
        "indemnización", "indemnizacion",
        "factor",
        "renta exenta laboral",
    ),
    anchor_articles=("383",),
    search_queries=(
        "retencion fuente salarios art 383 et tabla uvt procedimiento 1 2",
        "depuracion base art 388 et 25 por ciento renta exenta laboral 790 uvt 40 por ciento",
    ),
    source_label="retencion_salarios_anchor",
)
