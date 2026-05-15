"""v16 (2026-05-14) — exoneración de parafiscales (art. 114-1 ET)."""
from __future__ import annotations

from ..case_detectors import is_exoneracion_parafiscales_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="exoneracion_parafiscales",
    detector=is_exoneracion_parafiscales_case,
    bullets=(
        "El art. 114-1 ET exonera **SENA (2 %), ICBF (3 %) y salud empleador (8,5 %)** — total **13,5 % del IBC** — sobre los trabajadores que devenguen **menos de 10 SMMLV**. **No exonera** Cajas de Compensación (4 %), pensión (16 %), ARL, ni salud trabajador (4 %).",
        "**Beneficiarios:** sociedades y PJ asimiladas contribuyentes del régimen ordinario; **PN empleadoras con dos (2) o más empleados** (art. 114-1 inciso 1); consorcios, uniones temporales y patrimonios autónomos; **contribuyentes del RST** (art. 905 ET).",
        "**Excluidos:** ESAL del RTE (art. 19 ET); PJ no contribuyentes; PN empleadoras con menos de 2 empleados; mineros pequeños bajo régimen especial.",
        "**Regla de los 10 SMMLV:** la exoneración aplica **por trabajador y por mes** sobre empleados con salario inferior a 10 SMMLV. Si un mes iguala o supera el umbral, **ese mes no opera** y se aporta el 13,5 % completo. Cálculo individual, no por nómina promediada. AG 2025: 10 SMMLV ≈ **$13.000.000**; AG 2026: **$14.235.000**.",
        "**Salario integral:** por definición ≥ 10 SMMLV de salario ordinario; el trabajador con salario integral **NO se beneficia** de la exoneración. Sobre el IBC del 70 % se aportan todos los conceptos (SENA, ICBF, salud, Cajas, pensión, ARL).",
        "**Socios y representantes legales:** si tienen vínculo laboral y devengan < 10 SMMLV, aplica. Honorarios o dividendos sin vínculo laboral = no hay parafiscales que exonerar.",
        "**Tratamiento contable y fiscal:** no se causa el gasto exonerado. El ahorro no es ingreso ni renta adicional — es ausencia de obligación. El requisito del art. 108 ET para deducir el salario se cumple automáticamente.",
    ),
    keywords=(
        "exoneración", "exoneracion", "exonerar", "exonerado",
        "parafiscales", "aportes",
        "114-1", "108",
        "sena", "icbf", "salud empleador",
        "cajas de compensación", "cajas de compensacion",
        "pensión", "pension", "arl",
        "smmlv", "10 smmlv",
        "ibc",
        "salario", "salarios", "nómina", "nomina",
        "régimen ordinario", "regimen ordinario", "rst",
        "esal", "rte",
        "13,5%", "13.5%", "2%", "3%", "8,5%", "8.5%",
        "deducir", "deducible",
    ),
    anchor_articles=("114-1",),
    search_queries=(
        "exoneracion de aportes parafiscales sena icbf salud art 114-1 et",
        "exoneracion 13,5 ibc 10 smmlv trabajadores art 114-1 et",
    ),
    source_label="exoneracion_parafiscales_anchor",
)
