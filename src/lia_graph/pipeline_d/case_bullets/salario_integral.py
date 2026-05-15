"""v17 b3 — salario integral (art. 132 CST + art. 18 Ley 50/1990).

Anchored at ET arts. 108 + 387 (Option A per fix_v17_may §3.3 — deducción
de salarios + depuración para retención). El régimen sustantivo está en
CST art. 132 + Ley 50/1990 art. 18 + art. 49 Ley 789/2002 (base 70 % para
aportes), citados en bullets.

Order-sensitive: este SPEC debe registrarse en CASE_REGISTRY **antes** de
liquidacion_mensual_nomina (que también dispara con marcadores genéricos
de \"nómina\"). Su detector tiene veto explícito para preguntas de \"salario
integral\".
"""
from __future__ import annotations

from ..case_detectors import is_salario_integral_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="salario_integral",
    detector=is_salario_integral_case,
    bullets=(
        "**Piso mínimo (CST art. 132 + Ley 50/1990 art. 18):** salario ordinario mensual **≥ 10 SMMLV** + factor prestacional **mínimo 30 %** sobre ese salario ordinario. **Para 2026 (SMMLV $1.423.500 referencia, verificar Decreto MinTrabajo):** salario ordinario mínimo = **$14.235.000**; factor 30 % = **$4.270.500**; salario integral mínimo ≈ **$18.505.500 mensuales (13 SMMLV)**.",
        "**Qué cubre el factor prestacional 30 %:** cesantías y sus intereses + prima de servicios + recargos por trabajo nocturno, dominical y festivo + horas extras + auxilios pactados por convención. **NO cubre vacaciones** (art. 87 CST) — se otorgan y pagan **adicionalmente** sobre el salario ordinario.",
        "**Forma del pacto — POR ESCRITO:** debe constar en el contrato de trabajo, indicando expresamente que se trata de salario integral y **discriminando el salario ordinario y el factor prestacional**. **Sin pacto escrito no opera el salario integral** aunque la cuantía sea suficiente. Un factor prestacional < 30 % **invalida el régimen**.",
        "**IBC para aportes — regla del 70 % (art. 49 Ley 789/2002):** salud, pensión, parafiscales (SENA, ICBF, Cajas) y riesgos laborales (ARL) se calculan sobre el **70 % del salario integral mensual**. Es la única excepción al principio \"IBC = salario devengado\". Ejemplo: salario integral $18.500.000 → IBC mensual = **$12.950.000**. Tope máximo del IBC: **25 SMMLV**.",
        "**Exoneración del art. 114-1 ET — NO APLICA al salario integral:** por definición, un trabajador con salario integral devenga ≥ 10 SMMLV de salario ordinario; por tanto **no procede la exoneración de SENA / ICBF / salud** (que solo aplica para empleados con salario < 10 SMMLV). Se paga **la totalidad de los aportes** sobre el 70 % del IBC.",
        "**Tratamiento contable y fiscal de cesantías:** al pactar salario integral, **no hay provisión de cesantías** porque el factor prestacional ya las pagó anticipadamente. **No se consigna al fondo de cesantías**. El gasto se reconoce en el mes en que se paga el salario integral. Vacaciones se otorgan, disfrutan y pagan **adicionalmente** sobre el salario ordinario (70 % del integral).",
        "**Deducibilidad y retención (ET):** el salario integral es deducible en renta bajo **art. 108 ET** siempre que se hayan pagado los aportes sobre el 70 % y el contrato escrito esté formalizado. **Retención en la fuente — art. 383 ET + art. 387 ET (depuración):** se calcula sobre el ingreso laboral total (incluido el factor prestacional pagado). El **25 % de renta exenta** del art. 206 num. 10 ET aplica con tope **790 UVT/año** (Ley 2277/2022). Tope global 40 % / 1.340 UVT.",
    ),
    keywords=(
        "salario integral",
        "factor prestacional",
        "13 smmlv",
        "10 smmlv",
        "art. 132 cst", "art 132 cst", "132 cst",
        "art. 18 ley 50", "art 18 ley 50",
        "ley 50 de 1990 art 18",
        "art. 49 ley 789", "art 49 ley 789",
        "ley 789 de 2002",
        "ibc 70 %", "ibc 70%", "ibc del 70",
        "70 % del salario",
        "30 %", "30%", "30 por ciento",
        "factor 30",
        "vacaciones",
        "art. 87 cst", "art 87 cst",
        "cesantías", "cesantias",
        "prima",
        "exoneración 114-1", "exoneracion 114-1",
        "art. 114-1", "art 114-1", "114-1",
        "art. 108", "art 108",
        "art. 387", "art 387",
        "art. 383", "art 383",
        "art. 206 num 10", "art 206 num 10",
        "art. 206", "art 206",
        "ley 2277", "ley 2277 de 2022",
        "790 uvt",
        "1.340 uvt", "1340 uvt",
        "40 %", "40%",
        "25 %", "25%", "25 % renta exenta",
        "25 smmlv",
        "ley 797 de 2003",
        "salario ordinario",
        "pacto escrito",
        "contrato de trabajo",
        "smmlv 2026", "$1.423.500",
    ),
    anchor_articles=("108", "387"),
    search_queries=(
        "salario integral cst art 132 ley 50 de 1990 art 18 piso 10 smmlv",
        "ibc 70 por ciento salario integral art 49 ley 789 de 2002 aportes",
        "art 114-1 et exoneracion no aplica salario integral mas de 10 smmlv",
    ),
    source_label="salario_integral_anchor",
)
