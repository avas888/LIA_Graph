"""v16 b3 — sanción por corrección (art. 644 ET)."""
from __future__ import annotations

from ..case_detectors import is_sancion_correccion_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="sancion_correccion",
    detector=is_sancion_correccion_case,
    bullets=(
        "**Sanción art. 644 ET:** **10 %** del mayor valor a pagar (o menor saldo a favor) si la corrección es **antes del emplazamiento para corregir** (art. 685 ET); **20 %** si es **después del emplazamiento** y antes de notificación del requerimiento especial.",
        "**Distinga el tipo de corrección:** **aumenta impuesto** o disminuye saldo a favor → **art. 588 ET** (presentación directa vía MUISCA). **Genera sanción del 644.** **Disminuye impuesto** o aumenta saldo a favor → **art. 589 ET** (solicitud ante DIAN dentro de **1 año** desde vencimiento). **NO genera sanción.**",
        "**Plazo para corregir bajo art. 588 ET:** mientras la declaración no esté en firme — **3 años** ordinaria o **5 años** con pérdidas desde el vencimiento. La corrección **reinicia el plazo de firmeza** desde la fecha de la corrección.",
        "**Liquidación:** mayor valor a pagar = impuesto corregido − impuesto inicial. Sanción = **10 %** × mayor valor (o **20 %** si aplica). Sanción mínima art. 639 ET: **10 UVT** ($470.650 con UVT 2025).",
        "**Intereses moratorios:** se liquidan **además** de la sanción, sobre el mayor valor del impuesto, desde el vencimiento original hasta el pago efectivo (art. 634 ET).",
        "**Reducción art. 640 ET:** **50 %** si en los 2 años anteriores no se cometió la misma conducta y se paga antes del pliego; **75 %** si nunca se ha cometido. Para autoliquidación voluntaria, la DIAN ha aceptado el 50 % al pagar simultáneamente.",
        "**Corrección sin afectar valores fiscales (errores de digitación, RUT):** **no genera sanción** del art. 644 ET, pero puede generar sanción por inconsistencia (art. 650-3 ET).",
    ),
    keywords=(
        "sanción", "sancion",
        "corrección", "correccion", "corregir",
        "644", "588", "589", "685", "640", "639", "650-3", "634",
        "10%", "20%", "50%", "75%",
        "mayor valor a pagar",
        "menor saldo a favor",
        "emplazamiento para corregir",
        "requerimiento especial",
        "10 uvt",
        "firmeza",
        "3 años", "5 años",
        "intereses moratorios",
        "muisca",
        "voluntaria",
    ),
    anchor_articles=("644",),
    search_queries=(
        "sancion por correccion declaracion renta 10 20 por ciento art 644 et",
        "art 588 art 589 et corregir declaracion sancion emplazamiento corregir",
    ),
    source_label="sancion_correccion_anchor",
)
