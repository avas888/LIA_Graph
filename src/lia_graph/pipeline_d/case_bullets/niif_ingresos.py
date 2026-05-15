"""v16 b5 — reconocimiento ingresos NIIF 15 vs art. 28 ET."""
from __future__ import annotations

from ..case_detectors import is_niif_ingresos_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="niif_ingresos",
    detector=is_niif_ingresos_case,
    bullets=(
        "**Regla general — coincide:** para la mayoría de ingresos PYME (venta de bienes muebles, prestación de servicios, comisiones), **NIIF 15 / Sección 23 NIIF PYMES y el ET coinciden** — el ingreso se reconoce cuando se transfiere el control / se cumple la obligación de desempeño (art. 28 ET regla general).",
        "**Modelo de 5 pasos NIIF 15:** (1) identificar el **contrato** con el cliente; (2) identificar las **obligaciones de desempeño** distintas; (3) determinar el **precio de la transacción**; (4) asignar el precio a cada obligación; (5) reconocer el ingreso cuando se satisface la obligación (en un momento del tiempo o a lo largo del tiempo).",
        "**Los seis numerales del par. 1 del art. 28 ET — NIIF reconoce antes pero fiscal espera:** **(1) Dividendos** → gravan al decretarse exigibles. **(2) Venta de inmuebles** → solo al otorgarse la **escritura pública**. **(3) Mediciones a valor razonable** → ajustes positivos NO son ingreso fiscal hasta enajenación. **(4) Método de participación patrimonial** → solo al decretarse los dividendos. **(5) Reversiones de provisiones** asociadas a pasivos no deducibles → no son ingreso fiscal. **(6) Pasivos por ingresos diferidos** de programas de fidelización → solo al realizarse el ingreso.",
        "**Caso 1 — dividendos no decretados:** subsidiaria reporta utilidad atribuible **$50.000.000** a la matriz al cierre. NIIF: ingreso $50M. Fiscal: NO ingreso hasta el decreto. Ajuste F2516: **−$50M** en conciliación de ingresos.",
        "**Caso 2 — venta inmueble dic 2025, escritura ene 2026:** $500M promesa firmada. NIIF puede reconocer parcial o total. Fiscalmente, el ingreso de **$500M se grava en 2026**, no en 2025. Ajuste F2516 2025: **−$500M** y reversión en 2026.",
        "**Caso 3 — propiedad de inversión a VR:** sube **$30M** al cierre 2025. NIIF: ingreso. Fiscal: **NO es ingreso** hasta la venta. Ajuste F2516: **−$30M**. **Caso 4 — reversión provisión no deducida:** provisión garantías $10M en 2024 (no deducible art. 105 ET). En 2025 vence y se revierte. NIIF: ingreso $10M. Fiscal: NO es ingreso porque no se dedujo originalmente. Ajuste F2516: **−$10M**.",
        "**Conciliación en F2516:** **Sección ERI** → ingresos totales NIIF. **Sección Conciliación Renta** → menos ingresos no realizados fiscalmente (los seis numerales). **Sección Impuesto Diferido** → registrar **pasivo diferido** por ingreso reconocido NIIF no gravado aún (monto × 35 %). **Anti-patrón:** NO tratar los seis numerales como diferencias permanentes — son **temporarias** y se revierten al evento de realización fiscal.",
    ),
    keywords=(
        "niif 15",
        "ifrs 15",
        "sección 23", "seccion 23",
        "reconocimiento de ingresos",
        "realización del ingreso", "realizacion del ingreso",
        "art. 28", "art 28",
        "art. 21-1", "art 21-1",
        "art. 27", "art 27",
        "numerales 1 a 6",
        "numeral 1 al 6",
        "art. 28 par", "art 28 par",
        "5 pasos",
        "modelo de 5 pasos",
        "transferencia de control",
        "obligaciones de desempeño", "obligaciones de desempeno",
        "método de avance", "metodo de avance",
        "diferencia temporaria",
        "valor razonable",
        "venta de inmuebles",
        "escritura pública", "escritura publica",
        "dividendos no decretados",
        "método de participación", "metodo de participacion",
        "participación patrimonial", "participacion patrimonial",
        "reversiones de provisiones",
        "ingresos diferidos",
        "fidelización", "fidelizacion",
        "componente financiero",
        "ley 1819 art 28",
        "ley 1314",
        "f2516",
    ),
    anchor_articles=("28",),
    search_queries=(
        "realizacion ingreso art 28 et numerales 1 a 6 niif 15 conciliacion fiscal",
        "ingresos niif vs fiscal dividendos inmuebles valor razonable participacion patrimonial",
    ),
    source_label="niif_ingresos_anchor",
)
