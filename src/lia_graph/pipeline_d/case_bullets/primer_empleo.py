"""v15.4 — primer empleo (art. 108-5 ET) case.

Migrated to the registry package in fix_v16. Content preserved
verbatim from v15.5.
"""
from __future__ import annotations

from ..case_detectors import is_primer_empleo_deduction_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="primer_empleo_deduction",
    detector=is_primer_empleo_deduction_case,
    bullets=(
        "El art. 108-5 ET permite deducir el **120% del salario** pagado a un empleado entre **18 y 28 años** que esté en su **primer empleo formal**. El 100% es la deducción ordinaria del salario; el 20% adicional es el beneficio fiscal.",
        "**Requisitos acumulativos (los cinco deben cumplirse):** (1) edad del empleado entre 18 y 28 años, (2) primer empleo formal acreditado, (3) contrato de trabajo (no de servicios ni prestación de servicios), (4) **certificación expedida por el Ministerio del Trabajo** que acredite que es el primer empleo formal, (5) el beneficio aplica solo durante los **primeros tres (3) años** del contrato.",
        "**Error más común (riesgo MEDIO en revisión DIAN):** tomar el 120% sin la certificación del Ministerio del Trabajo. Sin esa certificación, la DIAN rechaza el 20% adicional y deja solo el 100% ordinario. La certificación es un trámite barato — su omisión es la falla operativa que destruye el beneficio.",
        "**Cómo registrarlo en la depuración:** el 100% del salario va al renglón ordinario de gastos de nómina; el 20% adicional se incluye como **deducción especial** (renglón de deducciones especiales del formulario 110/210) — no lo dupliques con el salario base.",
        "**Tip operativo:** al onboarding de cualquier empleado entre 18 y 28 años, incluye la gestión de la certificación MinTrabajo en la lista de tareas del primer mes. Esperar al cierre fiscal para tramitarla suele significar perder el beneficio del AG.",
    ),
    keywords=(
        "primer empleo",
        "108-5",
        "120%", "20% adicional",
        "joven", "jóvenes", "jovenes",
        "menores de 28", "18 y 28", "18 a 28",
        "salario", "salarios", "nómina", "nomina",
        "ministerio del trabajo", "mintrabajo",
        "certificación", "certificacion",
        "contrato de trabajo",
        "deducir", "deducible", "deducción", "deduccion",
        "deducción especial", "deduccion especial",
        "depuración", "depuracion",
        "renglón", "renglon",
        "onboarding",
        "primeros tres años", "primeros 3 años", "primeros 3 anos",
    ),
    anchor_articles=("108-5",),
    search_queries=(
        "deduccion 120% primer empleo jovenes 18 28 años art 108-5",
        "certificacion ministerio del trabajo primer empleo art 108-5",
    ),
    source_label="primer_empleo_deduction_anchor",
)
