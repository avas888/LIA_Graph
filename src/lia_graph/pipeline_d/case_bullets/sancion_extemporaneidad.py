"""v16 b3 — sanción por extemporaneidad (art. 641 ET)."""
from __future__ import annotations

from ..case_detectors import is_sancion_extemporaneidad_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="sancion_extemporaneidad",
    detector=is_sancion_extemporaneidad_case,
    bullets=(
        "**Sin emplazamiento previo (art. 641 ET):** **5 %** del impuesto a cargo por cada **mes o fracción** de mes calendario de retraso, **tope 100 %** del impuesto. **Con emplazamiento previo (art. 642 ET):** **10 %** por mes o fracción, **tope 200 %**.",
        "**Base cuando no hay impuesto a cargo:** **1 %** sobre el patrimonio bruto del AG por cada mes o fracción, tope **5 % del patrimonio bruto** o **2.500 UVT** ($117.662.500 con UVT 2025), la menor. Sin patrimonio, base = ingresos brutos, mismo % y tope.",
        "**Conteo del retraso:** por **mes o fracción de mes calendario** desde el día siguiente al vencimiento hasta la fecha de presentación. **Un día de retraso = un mes completo** de sanción.",
        "**Sanción mínima (art. 639 ET):** **10 UVT** ($470.650 con UVT 2025; $497.990 con UVT 2026). Si el cálculo da menos, se liquida la mínima.",
        "**Intereses moratorios (art. 634 ET):** son **independientes** de la sanción. Se liquidan sobre el impuesto a cargo no pagado, desde el vencimiento hasta el pago efectivo, a la tasa del art. 635 ET (tasa de usura − 2 puntos).",
        "**Ejemplo:** impuesto a cargo $10.000.000, presentación con 3 meses de retraso voluntario → sanción = $10.000.000 × 5 % × 3 = **$1.500.000**. Más intereses moratorios sobre el impuesto.",
        "**Aplicabilidad:** aplica a **todas** las declaraciones administradas por la DIAN — renta, IVA, retención en la fuente, autorretención, GMF. La sanción por no enviar exógena tiene régimen propio (art. 651 ET).",
    ),
    keywords=(
        "sanción", "sancion",
        "extemporaneidad", "extemporanea", "extemporánea",
        "presentar tarde", "presentación tardía", "presentacion tardia",
        "5%", "10%", "1%",
        "100%", "200%",
        "tope",
        "641", "642", "639", "640", "634", "635",
        "10 uvt", "2.500 uvt", "2500 uvt",
        "impuesto a cargo",
        "patrimonio bruto",
        "ingresos brutos",
        "intereses moratorios",
        "mes", "meses", "fracción", "fraccion",
        "renta", "iva", "retención", "retencion",
        "exógena", "exogena", "651",
    ),
    anchor_articles=("641",),
    search_queries=(
        "sancion por extemporaneidad declaracion renta 5 por ciento art 641 et",
        "sancion presentar tarde declaracion impuesto a cargo mes fraccion art 641",
    ),
    source_label="sancion_extemporaneidad_anchor",
)
