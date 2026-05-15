"""v15.1 — GMF (4×1000) deduction case.

Bullets grounded in:
  * knowledge_base/CORE ya Arriba/RENTA/LOGGRO/seccion-09-costos-y-deducciones.md §9.9
  * knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/playbook_renta_*.md (sibling)

Migrated to the registry package in fix_v16. Bullet text and whitelist
preserved verbatim from v15.5 (no semantic change).
"""
from __future__ import annotations

from ..case_detectors import is_gmf_deduction_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="gmf_deduction",
    detector=is_gmf_deduction_case,
    bullets=(
        "El 50% del GMF (4×1000) efectivamente pagado durante el AG es deducible en la depuración ordinaria de renta conforme al art. 115 ET, sin requerir relación de causalidad con la actividad productora de renta — es una excepción notable al art. 107 ET.",
        "Calcula la deducción como 50% × (total del GMF certificado por cada entidad financiera donde el contribuyente tuvo cuentas durante el AG); si pagó $20M de 4×1000, deduce $10M.",
        "Registra el 50% deducible en el renglón de 'Otras deducciones' de la depuración ordinaria del formulario 110 (PJ) o 210 (PN obligada a llevar contabilidad); el otro 50% queda como gasto contable no deducible que no afecta la renta líquida.",
        "Soporte obligatorio: certificado anual emitido por cada entidad financiera con el GMF efectivamente retenido durante el AG — sin este certificado bancario, la deducción es objetable en una revisión DIAN.",
        "**Tip de planeación:** si el contribuyente tiene una cuenta marcada como exenta de GMF (art. 879 ET — una cuenta por persona natural o jurídica), evalúa canalizar el mayor volumen transaccional por ella; la exención completa puede valer más que la deducción del 50% del GMF pagado.",
    ),
    keywords=(
        "gmf", "4x1000", "4×1000", "4 x 1000", "cuatro por mil",
        "gravamen a los movimientos", "movimientos financieros",
        "115", "879", "870", "871", "872", "881",
        "deducir", "deducible", "deducción", "deduccion",
        "depuración", "depuracion",
        "causa", "causación", "causacion",
        "certificado bancario", "certificado anual",
        "entidad financiera",
        "renglón", "renglon",
        "débito", "debito", "crédito", "credito",
        "exenta", "exención", "exencion",
    ),
    anchor_articles=("115",),
    search_queries=(
        "deduccion del gmf 4x1000 gravamen movimientos financieros art 115",
        "gmf efectivamente pagado 50% deducible art 115 inciso 2 et",
    ),
    source_label="gmf_deduction_anchor",
)
