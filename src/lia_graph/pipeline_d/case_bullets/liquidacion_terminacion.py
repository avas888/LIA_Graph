"""v17 b1 — liquidación por terminación del contrato (CST arts. 64 + 65).

Anchored at ET arts. 108 + 387 (Option A per fix_v17_may §3.3). El régimen
sustantivo de la indemnización y la moratoria está en CST 62-65 (citado en
bullets); la retención sobre indemnización en art. 401-3 ET; renta exenta
parcial en art. 206 num. 5 ET.
"""
from __future__ import annotations

from ..case_detectors import is_liquidacion_terminacion_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="liquidacion_terminacion",
    detector=is_liquidacion_terminacion_case,
    bullets=(
        "**Conceptos de la liquidación final (siempre, con o sin justa causa):** salarios pendientes + **cesantías acumuladas** (saldo en fondo + lo causado en el último año no consignado, **al trabajador directamente**) + intereses cesantías proporcionales + prima proporcional + vacaciones disfrutadas pendientes o compensadas + bonificaciones y comisiones pendientes + indemnización art. 64 si aplica.",
        "**Indemnización por despido sin justa causa (CST art. 64) — contrato indefinido — salario < 10 SMMLV:** **30 días de salario** por el primer año + **20 días** por cada año adicional o proporcional. Salario ≥ 10 SMMLV: **20 días** primer año + **15 días** por cada año adicional.",
        "**Indemnización contrato a término fijo:** valor de los **salarios faltantes** hasta el vencimiento pactado. Contrato por obra o labor: valor de los salarios del tiempo faltante para terminar, **mínimo 15 días**.",
        "**Justa causa (CST art. 62):** debe **probarse** + procedimiento disciplinario previo (descargos) + aviso escrito motivado. **Si hay justa causa probada NO procede la indemnización del art. 64**; igual deben pagarse salarios, prestaciones y vacaciones causadas.",
        "**Indemnización moratoria — CST art. 65:** durante los **primeros 24 meses** después del retiro = **1 día de salario por cada día de mora**. A partir del **mes 25** = intereses moratorios a tasa máxima legal (DTF + sobretasa). Procede solo si el empleador no demuestra buena fe (Sentencia C-892/2009 — modulación). No es automática — el trabajador debe demandar.",
        "**Plazo de pago de la liquidación:** **inmediato**, al momento de la terminación o en los días estrictamente necesarios para liquidar. Jurisprudencia ha aceptado **24 a 72 horas** como razonable; más allá, riesgo de sanción moratoria del art. 65 CST.",
        "**Tratamiento fiscal de la indemnización (ET):** **art. 206 num. 5 ET** — renta exenta solo para trabajadores con ingresos mensuales **< 350 UVT**; por encima la indemnización es **gravada**. **Art. 401-3 ET — retención en la fuente:** si el salario mensual (sin contar la indemnización) supera **204 UVT**, se retiene **20 %** sobre el valor de la indemnización. La deducibilidad del empleador exige aportes y depuración bajo art. 108 + 387 ET.",
    ),
    keywords=(
        "liquidación final", "liquidacion final",
        "indemnización", "indemnizacion",
        "despido",
        "justa causa",
        "sin justa causa",
        "renuncia voluntaria",
        "terminación contrato", "terminacion contrato",
        "art. 64 cst", "art 64 cst", "art. 64", "art 64",
        "art. 65 cst", "art 65 cst", "art. 65", "art 65",
        "art. 62 cst", "art 62 cst",
        "art. 401-3", "art 401-3", "401-3",
        "art. 206 num 5", "art 206 num 5",
        "350 uvt", "204 uvt",
        "moratoria",
        "indemnización moratoria", "indemnizacion moratoria",
        "buena fe",
        "c-892", "sentencia c-892",
        "c-1507",
        "30 días", "30 dias",
        "20 días", "20 dias",
        "15 días", "15 dias",
        "10 smmlv",
        "24 meses", "mes 25",
        "dtf",
        "art. 108", "art 108",
        "art. 387", "art 387",
        "20%",
        "contrato a término fijo", "contrato a termino fijo",
        "obra o labor",
        "descargos",
    ),
    anchor_articles=("108", "387"),
    search_queries=(
        "indemnizacion despido sin justa causa cst art 64 escala 30 20 dias",
        "indemnizacion moratoria art 65 cst 24 meses buena fe",
        "retencion indemnizacion laboral art 401-3 et 204 uvt 20 por ciento",
    ),
    source_label="liquidacion_terminacion_anchor",
)
