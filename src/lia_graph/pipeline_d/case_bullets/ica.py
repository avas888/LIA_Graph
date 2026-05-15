"""v15.3 — ICA / industria y comercio deduction case.

Migrated to the registry package in fix_v16. Content preserved
verbatim from v15.5.
"""
from __future__ import annotations

from ..case_detectors import is_ica_deduction_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="ica_deduction",
    detector=is_ica_deduction_case,
    bullets=(
        "El 100% del ICA (industria y comercio, junto con su complementario de avisos y tableros) efectivamente pagado durante el AG es deducible en la depuración ordinaria de renta conforme al art. 115 inciso 1 ET, siempre que tenga relación de causalidad con la actividad económica del contribuyente.",
        "**Alternativa más beneficiosa para la mayoría de PYMEs:** el art. 115-1 ET permite tomar el 50% del ICA pagado como **descuento tributario** (no como deducción). Para un contribuyente con tarifa marginal del 35%, el descuento del 50% siempre supera el beneficio de la deducción del 100% (50% > 100% × 35% = 35%). Solo es preferible la deducción si la tarifa efectiva supera el 50%.",
        "Registra la deducción del 100% en el renglón de 'Otras deducciones' de la depuración ordinaria; si tomas la vía del descuento tributario (art. 115-1 ET), el valor va en el renglón de descuentos tributarios — nunca en ambos lados de la declaración.",
        "Soporte obligatorio: declaración del ICA del municipio (anual o bimestral según jurisdicción) + comprobante de pago + paz y salvo cuando el municipio lo exija. Verifica si el ICA pagado corresponde al AG declarado y no a períodos anteriores.",
        "**Tip de planeación:** modela ambas vías (100% deducción vs. 50% descuento tributario) para el cliente antes de cerrar la declaración; la decisión cambia con la tarifa marginal y con la existencia de saldo a favor en renta.",
    ),
    keywords=(
        "ica", "industria y comercio", "avisos y tableros",
        "impuesto de industria",
        "115", "115-1",
        "deducir", "deducible", "deducción", "deduccion",
        "descuento tributario",
        "depuración", "depuracion",
        "causa", "causación", "causacion", "causalidad",
        "tarifa marginal",
        "municipio", "municipal",
        "paz y salvo",
        "renglón", "renglon",
        "complementario",
    ),
    anchor_articles=("115", "115-1"),
    search_queries=(
        "deduccion del ica impuesto industria comercio descuento tributario en renta art 115",
        "ica pagado deducible renta descuento tributario art 115 ica",
    ),
    source_label="ica_deduction_anchor",
)
