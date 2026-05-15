"""v16 b3 — sanción por inexactitud (art. 647 ET)."""
from __future__ import annotations

from ..case_detectors import is_sancion_inexactitud_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="sancion_inexactitud",
    detector=is_sancion_inexactitud_case,
    bullets=(
        "**Sanción por inexactitud (art. 647 ET):** **100 %** regla general — diferencia entre saldo a pagar/saldo a favor declarado y el determinado por la DIAN. **160 %** — abuso tributario (art. 869 ET). **200 %** — omisión de activos o inclusión de pasivos inexistentes (art. 648 ET).",
        "**Hechos sancionables:** omisión de ingresos o impuestos; inclusión de costos, deducciones, descuentos, exenciones, pasivos, impuestos descontables, retenciones o anticipos **inexistentes** o **improcedentes**; uso de datos o factores **falsos, equivocados o desfigurados**; compras o gastos con proveedores ficticios o insolventes.",
        "**Base de cálculo:** la diferencia entre lo declarado y lo determinado oficialmente. **NO** se calcula sobre el patrimonio ni sobre los ingresos brutos.",
        "**Reducción art. 709 ET — al responder requerimiento especial:** si acepta total o parcialmente y paga (impuesto + sanción reducida + intereses), la sanción se reduce a **una cuarta parte** (es decir, **25 %** de la original).",
        "**Reducción art. 713 ET — al aceptar la liquidación oficial:** si acepta dentro del término para interponer recurso de reconsideración, la sanción se reduce a **la mitad** (**50 %**) de la liquidada.",
        "**Reducción art. 640 ET — adicional sobre la ya reducida:** **50 %** si en los 2 años anteriores no se cometió la misma conducta; **75 %** si nunca se ha cometido.",
        "**Defensa por diferencia razonable de criterio (art. 647 par. ET):** si la inexactitud se debe a una **diferencia razonable de criterio** sobre interpretación del derecho, **con hechos completos y verdaderos**, no procede la sanción. Principal defensa práctica.",
    ),
    keywords=(
        "sanción", "sancion",
        "inexactitud",
        "647", "648", "709", "713", "640", "869", "671", "651",
        "100%", "160%", "200%", "25%", "50%", "75%",
        "omisión", "omision",
        "ingresos", "activos", "pasivos",
        "costos", "deducciones",
        "diferencia de criterio",
        "razonable",
        "abuso tributario",
        "requerimiento especial",
        "liquidación oficial", "liquidacion oficial",
        "saldo a pagar", "saldo a favor",
        "proveedores ficticios",
        "intereses moratorios",
    ),
    anchor_articles=("647",),
    search_queries=(
        "sancion por inexactitud declaracion renta 100 200 por ciento art 647 et",
        "reduccion sancion inexactitud art 709 713 640 et requerimiento especial",
    ),
    source_label="sancion_inexactitud_anchor",
)
