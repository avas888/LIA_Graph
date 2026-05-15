"""v16 b4 — Formato 1003 retenciones (Res. DIAN 000162/2023 art. 19)."""
from __future__ import annotations

from ..case_detectors import is_exogena_1003_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="exogena_1003",
    detector=is_exogena_1003_case,
    bullets=(
        "**Formato 1003 — Retenciones en la fuente practicadas** (Res. DIAN 000162/2023 art. 19, V7). Reporta cada retención practicada por el agente retenedor durante el AG, por sujeto retenido, concepto y valor.",
        "**Sujetos obligados:** agentes de retención que cumplan el umbral general de exógena (PJ ≥ **100.000 UVT** del AG anterior; PN ≥ **$500.000.000**) + obligados específicos del art. 1 Res. 000162/2023 (consorcios, fiducias, sociedades fiduciarias).",
        "**Qué se reporta por registro:** NIT/cédula del sujeto retenido; apellidos/razón social; **concepto de retención (1xxx)**; **base sometida a retención**; **valor de la retención practicada**.",
        "**Conceptos típicos:** **1301** retención salarios; **1302** honorarios; **1303** comisiones; **1304** servicios; **1305** arrendamientos; **1306** rendimientos financieros; **1307** compras; **1308** dividendos; **1309** pagos al exterior; **1310** enajenación activos fijos; **1312** autorretención por venta; **1320** retención de IVA; **1331** autorretención especial de renta (Decreto 0261/2023).",
        "**Sin cuantía mínima:** todas las retenciones practicadas durante el AG se reportan, sin tope mínimo. El umbral por cuantía aplica al 1001 (pago), NO al 1003 (retención).",
        "**Autorretención:** se reporta con el NIT del **propio reportante** como sujeto retenido (concepto 1312 venta + 1331 especial renta), reflejando que el agente actuó como retenido y retenedor simultáneamente.",
        "**Cruces obligatorios:** total 1003 por concepto = sumatoria anual del renglón equivalente del Formulario **350** de los 12 meses; 1003 por sujeto retenido ↔ retención asociada al 1001 del mismo NIT; 1003 ↔ **certificados de retención** emitidos (art. 381 ET).",
    ),
    keywords=(
        "formato 1003", "1003",
        "exógena", "exogena",
        "retenciones practicadas", "retención practicada", "retencion practicada",
        "agente de retención", "agente de retencion",
        "concepto",
        "1301", "1302", "1303", "1304", "1305", "1306", "1307", "1308", "1309", "1310", "1312", "1320", "1331",
        "365", "381", "437-1", "437-2", "408",
        "autorretención", "autorretencion",
        "decreto 0261", "decreto 261",
        "decreto 572",
        "350",
        "certificado de retención", "certificado de retencion",
        "formato 220",
        "444444001",
        "exterior",
        "cdi",
        "art. 651", "art 651",
    ),
    anchor_articles=("365",),
    search_queries=(
        "formato 1003 exogena retenciones practicadas res dian 000162 2023",
        "concepto 1301 1302 1331 autorretencion especial decreto 0261 cuadre 350",
    ),
    source_label="exogena_1003_anchor",
)
