"""v16 b3 — responsables y no responsables de IVA (art. 437 ET)."""
from __future__ import annotations

from ..case_detectors import is_iva_responsables_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="iva_responsables",
    detector=is_iva_responsables_case,
    bullets=(
        "Desde la **Ley 1943 de 2018** existen dos categorías: **Responsables de IVA** (antes \"régimen común\") y **No responsables de IVA** (antes \"régimen simplificado\"). La categoría \"no responsable\" es **exclusiva de personas naturales** — toda PJ que venda bienes/servicios gravados es responsable.",
        "**Requisitos acumulativos para PN ser NO responsable (art. 437 par. 3 ET, AG 2025 UVT $47.065):** ingresos brutos del año anterior por actividad gravada **< 3.500 UVT = $164.727.500**; ingresos del año en curso **< 3.500 UVT**; **un único establecimiento** de comercio; **no franquicias** ni explotación de intangibles; **no ser usuario aduanero**; contratos individuales **< 3.500 UVT**; consignaciones bancarias **< 3.500 UVT**.",
        "**Incumplir cualquier requisito = responsable.** Los requisitos son **acumulativos**; basta superar uno para perder la condición de no responsable.",
        "**Tránsito a responsable (art. 508-2 ET):** al superar un tope, el contribuyente debe **inscribirse como responsable** desde el **bimestre siguiente** al hecho y empezar a facturar con IVA, presentar declaraciones bimestrales/cuatrimestrales y cumplir todas las obligaciones.",
        "**Obligaciones del no responsable (art. 506 ET):** inscribirse en el RUT marcando \"No responsable de IVA\" (código 49); conservar documentos por **5 años** (art. 632 ET); **NO cobrar IVA**, **NO presentar declaración de IVA**, **NO descontar IVA** en compras.",
        "**Reclasificación de oficio (art. 508-1 ET):** la DIAN puede reclasificar al contribuyente al detectar incumplimiento, con efectos **retroactivos** al bimestre del hecho.",
        "**Agentes de retención de IVA (art. 437-2 ET):** entidades estatales, grandes contribuyentes, personas designadas por la DIAN, responsables que adquieran de no domiciliados, usuarios de servicios desde el exterior. **Tarifa general de retención: 15 % del IVA facturado** (art. 437-1 ET). Servicios desde el exterior: **100 %**.",
    ),
    keywords=(
        "iva",
        "responsable", "responsables",
        "no responsable", "no responsables",
        "437", "437-1", "437-2", "506", "508-1", "508-2", "632",
        "régimen común", "regimen comun",
        "régimen simplificado", "regimen simplificado",
        "3.500 uvt", "3500 uvt",
        "agente de retención", "agente de retencion",
        "retención de iva", "retencion de iva",
        "15%", "100%",
        "establecimiento",
        "franquicia",
        "usuario aduanero",
        "consignaciones",
        "ley 1943",
        "ley 2010",
        "rut",
        "bimestral", "cuatrimestral",
        "código 49", "codigo 49",
    ),
    anchor_articles=("437",),
    search_queries=(
        "responsables no responsables iva art 437 par 3 et 3500 uvt",
        "agentes de retencion iva art 437-2 et grandes contribuyentes 15 por ciento",
    ),
    source_label="iva_responsables_anchor",
)
