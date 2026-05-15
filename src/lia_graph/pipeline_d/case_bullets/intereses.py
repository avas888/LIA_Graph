"""v15.4 — intereses + subcapitalización case (arts. 117, 118-1 ET).

Migrated to the registry package in fix_v16. Content preserved
verbatim from v15.5.
"""
from __future__ import annotations

from ..case_detectors import is_intereses_deduction_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="intereses_deduction",
    detector=is_intereses_deduction_case,
    bullets=(
        "Los intereses pagados por préstamos destinados a financiar la actividad productora de renta son deducibles bajo el art. 117 ET, siempre que cumplan los requisitos generales del art. 107 ET (causalidad, necesidad, proporcionalidad).",
        "**Límite de subcapitalización (art. 118-1 ET):** no son deducibles los intereses generados por deudas que, en promedio durante el AG, excedan **dos (2) veces el patrimonio líquido del contribuyente a 31 de diciembre del AG inmediatamente anterior**. El exceso queda como gasto contable no deducible.",
        "**Excepción al límite (art. 118-1 par. 1 ET):** la regla de subcapitalización NO aplica a contribuyentes sometidos a inspección y vigilancia de la Superintendencia Financiera ni a entidades del sector cooperativo.",
        "Cómo aplicar el límite: calcula la **deuda promedio del AG** (saldos diarios o mensuales) y compárala contra **2 × patrimonio líquido del año anterior**; si la deuda promedio supera el doble del patrimonio, la porción del interés correspondiente al exceso es no deducible. Registra esa porción como DPARL (diferencia permanente que no genera impuesto diferido) en el formulario 2516/2517.",
        "Soporte mínimo: contratos de crédito + tabla de amortización + certificación bancaria del interés efectivamente pagado en el AG; conserva también el cálculo del patrimonio líquido del año anterior y el promedio de la deuda durante el AG para defender la deducción ante una revisión DIAN.",
    ),
    keywords=(
        "intereses", "interés", "interes",
        "subcapitalización", "subcapitalizacion",
        "117", "118-1",
        "deuda", "deudas",
        "patrimonio líquido", "patrimonio liquido",
        "promedio",
        "préstamo", "prestamo", "préstamos", "prestamos",
        "crédito", "credito",
        "amortización", "amortizacion",
        "deducir", "deducible", "deducción", "deduccion",
        "depuración", "depuracion",
        "causa", "causación", "causacion", "causalidad",
        "renglón", "renglon",
        "dparl",
        "exceso", "límite", "limite",
    ),
    anchor_articles=("117", "118-1"),
    search_queries=(
        "deduccion de intereses prestamo bancario art 117",
        "subcapitalizacion deuda promedio dos veces patrimonio liquido art 118-1",
    ),
    source_label="intereses_deduction_anchor",
)
