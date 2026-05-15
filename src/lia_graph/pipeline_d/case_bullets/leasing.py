"""v15.4 — leasing (art. 127-1 ET) case.

Migrated to the registry package in fix_v16. Content preserved
verbatim from v15.5.
"""
from __future__ import annotations

from ..case_detectors import is_leasing_deduction_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="leasing_deduction",
    detector=is_leasing_deduction_case,
    bullets=(
        "El art. 127-1 ET distingue **dos tratamientos fiscales del leasing**, y la calificación determina cómo se deduce: **leasing financiero** (con opción irrevocable de compra) vs **leasing operativo** (arrendamiento puro sin opción de compra o con opción no irrevocable).",
        "**Leasing financiero:** el arrendatario activa fiscalmente el bien en su patrimonio y deduce (a) la depreciación fiscal del activo bajo art. 137 ET y (b) la porción de intereses del canon. La porción de capital del canon NO es deducible — amortiza la deuda, no el gasto.",
        "**Leasing operativo:** el arrendatario NO activa el bien y deduce el **canon completo** como gasto bajo art. 107 ET (causalidad + necesidad + proporcionalidad). El bien no aparece en el patrimonio fiscal del arrendatario.",
        "**Divergencia NIIF 16 vs fiscal:** desde 2019, NIIF 16 obliga a registrar todo arrendamiento >12 meses como activo por derecho de uso + pasivo (similar al leasing financiero contable), pero el art. 127-1 ET sigue distinguiendo financiero vs operativo para efectos fiscales. Esta diferencia se concilia en el formulario 2516/2517 — no la ignores.",
        "**IVA en leasing financiero (art. 258-1 inciso 3 ET + art. 1.2.1.27.5 DUR 1625/2016):** el descuento por IVA en activos fijos reales productivos procede en cabeza del **arrendatario**, no del arrendador. El arrendador financiero debe certificar al arrendatario el valor del IVA pagado.",
        "**Cómo debe registrarse en la depuración de renta:** la norma que fundamenta el tratamiento es el art. 127-1 ET. En leasing operativo, el porcentaje deducible es del 100% del canon, registrado como gasto en el renglón ordinario del formulario 110 (PJ) o 210 (PN obligada a llevar contabilidad). En leasing financiero, no se deduce el canon completo: registra la depreciación fiscal del activo y los intereses del canon, mientras la porción de capital amortiza la deuda y no es deducible.",
    ),
    keywords=(
        "leasing", "arrendamiento", "arrendatario", "arrendador",
        "127-1", "137", "107", "258-1",
        "opción", "opcion", "opción de compra", "opcion de compra",
        "irrevocable",
        "financiero", "operativo",
        "canon",
        "depreciación", "depreciacion",
        "patrimonio fiscal",
        "niif 16", "nic 16",
        "conciliación fiscal", "conciliacion fiscal",
        "2516", "2517",
        "iva",
        "activo fijo", "activos fijos",
        "deducir", "deducible", "deducción", "deduccion",
        "renglón", "renglon",
        "causa", "causación", "causacion", "causalidad",
    ),
    anchor_articles=("127-1",),
    search_queries=(
        "tratamiento fiscal del leasing financiero opcion irrevocable de compra art 127-1",
        "leasing operativo canon arrendamiento gasto deducible art 107 art 127-1",
    ),
    source_label="leasing_deduction_anchor",
)
