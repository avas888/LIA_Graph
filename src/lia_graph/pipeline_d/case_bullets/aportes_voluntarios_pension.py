"""v16 b5 — aportes voluntarios pensión + AFC (arts. 126-1, 126-4 ET)."""
from __future__ import annotations

from ..case_detectors import is_aportes_voluntarios_pension_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="aportes_voluntarios_pension",
    detector=is_aportes_voluntarios_pension_case,
    bullets=(
        "**INCRNGO con tope conjunto:** aportes voluntarios a pensión (art. 126-1 ET) + consignaciones a cuenta AFC (art. 126-4 ET) + aportes voluntarios obligatorios al SGP son **ingresos no constitutivos de renta ni ganancia ocasional** hasta el **menor entre 30 % del ingreso laboral o tributario del año** y **3.800 UVT anuales**.",
        "**En cifras AG 2025 (UVT $47.065):** **3.800 UVT = $178.847.000** anuales (tope absoluto). 30 % del ingreso laboral del año (tope relativo). El INCRNGO es el **menor de los dos**.",
        "**Tipos de aportes y su tratamiento:** **obligatorios SGP** (4 % empleador + 4 % empleado) → INCRNGO **sin tope numérico** (art. 55 ET). **Voluntarios obligatorios SGP** (RAIS) → dentro del conjunto 30 %/3.800 UVT (incluidos por Ley 2277/2022). **Pensiones voluntarias (FVP)** → dentro del conjunto. **Cuentas AFC / AVC** → dentro del conjunto.",
        "**Conservación del beneficio — pensiones voluntarias:** cumplimiento requisitos de pensión; **permanencia mínima 10 años** desde el aporte (era 5 — Ley 2277/2022); adquisición de vivienda del aportante; pago de cuotas de crédito hipotecario.",
        "**Conservación del beneficio — cuentas AFC:** compra de vivienda del aportante; pago de cuotas de crédito hipotecario; **permanencia 10 años** desde el aporte; **financiación de educación superior** del titular, cónyuge o hijos (incluye crédito ICETEX).",
        "**Retiro por causa distinta antes del plazo:** la entidad financiera **practica retención en la fuente** sobre el monto retirado a la tarifa que correspondió cuando se hizo el aporte (en práctica **35 %** o tarifa al ingreso laboral del año del retiro). Documentar trazabilidad por fecha de aporte (5 años para pre-Ley 2277, 10 años para post).",
        "**Cruce con tope global art. 336 ET:** el tope global de **1.340 UVT** de cédula general aplica a **rentas exentas + deducciones**. **Los aportes voluntarios pensión + AFC son INCRNGO, no rentas exentas** — **NO computan en el tope 1.340 UVT**. Distinción crítica.",
    ),
    keywords=(
        "aportes voluntarios",
        "aporte voluntario",
        "pensión voluntaria", "pension voluntaria",
        "fvp",
        "afc", "avc",
        "ahorro fomento construcción", "ahorro fomento construccion",
        "ahorro voluntario contractual",
        "55", "56", "56-1",
        "126-1", "126-4",
        "336", "383", "388",
        "incr", "incrngo",
        "30%", "30 %",
        "3.800 uvt", "3800 uvt",
        "1.340 uvt", "1340 uvt",
        "10 años permanencia", "10 anos permanencia",
        "5 años", "10 años",
        "ingreso laboral",
        "ingreso tributario",
        "vivienda",
        "icetex",
        "educación superior", "educacion superior",
        "retiro anticipado",
        "ley 2277",
        "rais",
        "sgp",
    ),
    anchor_articles=("126-1",),
    search_queries=(
        "aportes voluntarios pension afc art 126-1 126-4 et incrngo tope 3800 uvt",
        "aportes voluntarios 30 por ciento ingreso 10 años permanencia ley 2277",
    ),
    source_label="aportes_voluntarios_pension_anchor",
)
