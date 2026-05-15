"""v16 b4 — retención por servicios y honorarios (art. 392 ET)."""
from __future__ import annotations

from ..case_detectors import is_retencion_servicios_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="retencion_servicios",
    detector=is_retencion_servicios_case,
    bullets=(
        "**Tarifas vigentes art. 392 ET — pagos a residentes:** Honorarios **PJ 11 %**, PN declarante **11 %**, PN no declarante **10 %**. PN no declarante con contrato ≥ **3.300 UVT/año**: pasa a **11 %** (asimila a declarante).",
        "**Servicios:** servicios generales **4 %** (PJ y PN declarante) o **6 %** (PN no declarante) con base mínima **4 UVT**. Servicios técnicos / asistencia técnica **6 %** (PJ y PN declarante), **10 %** PN no declarante (Decreto 572/2025).",
        "**Distinción crítica:** **Honorarios** = factor intelectual sin subordinación (abogado, contador, consultor). **Servicios** = factor material o manual (vigilancia, aseo, mantenimiento). **Servicios técnicos** = aplicación de conocimientos tecnológicos sin transferir know-how.",
        "**Cuándo aplicar tarifa de no declarante:** beneficiario PN no obligada a declarar y no acredita lo contrario. Pídase **RUT actualizado**. Por defecto asumir no declarante.",
        "**Regla de los 3.300 UVT (PN honorarios):** si la PN no declarante celebra contratos con un mismo retenedor por **3.300 UVT/año o más**, se asimila a declarante → tarifa **11 %** desde el primer pago.",
        "**Bases mínimas (AG 2025, UVT $47.065):** **4 UVT = $188.000**; **27 UVT = $1.271.000**. AG 2026 (UVT $49.799): **4 UVT = $199.000**; **27 UVT = $1.345.000**.",
        "**IVA NO se incluye** en la base de retención de renta. La base es el valor del servicio antes de IVA. Servicios con AIU (servicios temporales, aseo, vigilancia): tarifa **solo sobre AIU**, no sobre el valor total.",
    ),
    keywords=(
        "retención", "retencion",
        "honorarios", "honorario",
        "servicios", "servicio",
        "comisiones", "comision",
        "392", "401", "408", "383",
        "10%", "11%", "4%", "6%", "1%", "2%", "3,5%",
        "3.300 uvt", "3300 uvt",
        "4 uvt", "27 uvt",
        "declarante", "no declarante",
        "servicios técnicos", "servicios tecnicos",
        "asistencia técnica", "asistencia tecnica",
        "aiu",
        "decreto 572",
        "decreto 1625",
        "exterior",
        "cdi",
        "transporte",
        "aseo", "vigilancia",
        "iva",
        "base mínima", "base minima",
    ),
    anchor_articles=("392",),
    search_queries=(
        "retencion fuente honorarios servicios art 392 et tarifas 10 11 4 6 por ciento",
        "honorarios servicios tecnicos declarante no declarante 3300 uvt decreto 572",
    ),
    source_label="retencion_servicios_anchor",
)
