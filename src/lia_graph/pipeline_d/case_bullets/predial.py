"""v15.3 — predial deduction case.

Migrated to the registry package in fix_v16. Content preserved
verbatim from v15.5.
"""
from __future__ import annotations

from ..case_detectors import is_predial_deduction_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="predial_deduction",
    detector=is_predial_deduction_case,
    bullets=(
        "El 100% del impuesto predial efectivamente pagado durante el AG es deducible en la depuración ordinaria de renta conforme al art. 115 inciso 1 ET, siempre que el inmueble tenga relación de causalidad con la actividad económica del contribuyente.",
        "**Requisito clave de causalidad:** el predial es deducible solo cuando el inmueble está afecto a la actividad productora de renta (bodega operativa, oficina, planta, local comercial). El predial de inmuebles personales del socio/contribuyente sin relación con la actividad NO es deducible — es gasto personal.",
        "Registra la deducción en el renglón de 'Otras deducciones' de la depuración ordinaria del formulario 110 (PJ) o 210 (PN obligada a llevar contabilidad).",
        "Soporte obligatorio: recibo del impuesto predial del municipio donde está ubicado el inmueble + comprobante de pago del AG; conserva también la prueba del uso productivo del inmueble (contrato de arrendamiento, certificado de uso, facturas asociadas a la operación en ese inmueble) para defender la causalidad ante una revisión DIAN.",
        "**Prohibición de doble tratamiento (art. 115 ET):** el predial no puede tratarse simultáneamente como costo Y como gasto en la depuración — escoge una sola vía contable.",
    ),
    keywords=(
        "predial", "impuesto predial", "inmueble", "inmuebles",
        "bodega", "oficina", "planta", "local comercial",
        "115",
        "deducir", "deducible", "deducción", "deduccion",
        "depuración", "depuracion",
        "causa", "causación", "causacion", "causalidad",
        "actividad económica", "actividad economica",
        "actividad productora",
        "recibo", "comprobante",
        "renglón", "renglon",
    ),
    anchor_articles=("115",),
    search_queries=(
        "deduccion del impuesto predial inmueble actividad economica art 115",
        "predial efectivamente pagado 100% deducible art 115 inciso 1 et",
    ),
    source_label="predial_deduction_anchor",
)
