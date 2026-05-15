"""v16 b3 — IVA descontable y prorrateo (arts. 488-491 ET)."""
from __future__ import annotations

from ..case_detectors import is_iva_descontable_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="iva_descontable",
    detector=is_iva_descontable_case,
    bullets=(
        "**Regla general (art. 488 ET):** el IVA descontable corresponde a operaciones que **constituyan costo o gasto** y estén **directamente relacionadas** con operaciones gravadas o exentas del responsable.",
        "**Prorrateo (art. 490 ET) — cuando hay mezcla gravadas + exentas + excluidas:** IVA descontable proporcional = IVA pagado × (Ingresos gravados + Ingresos exentos) / Total de ingresos. Si el resultado es **< 100 %**, parte del IVA pagado pasa a mayor valor del costo (no descontable).",
        "**Ejemplo:** PYME con ventas gravadas **$200M** + exentas **$50M** + excluidas **$50M** (total $300M). IVA pagado en gastos comunes $5.700.000. Proporción = ($200M+$50M)/$300M = **83,33 %**. IVA descontable = $5.700.000 × 83,33 % = **$4.750.000**. IVA NO descontable = $5.700.000 × 16,67 % = **$950.000**.",
        "**Activos fijos (art. 491 ET):** el IVA pagado en activos fijos **NO es descontable** como regla general. Excepción: maquinaria industrial (régimen de descuento en renta del art. 258-1 ET). El IVA no descontable forma parte del **costo depreciable**.",
        "**Oportunidad — art. 496 ET:** el IVA descontable puede tomarse en el **bimestre o cuatrimestre de causación** o en uno de los **tres períodos siguientes**. Pasado ese plazo, **se pierde el derecho**.",
        "**Requisitos sustanciales:** **factura electrónica de venta válida** (con NIT, descripción, IVA discriminado, CUFE); pago por **medios bancarizados** (art. 771-5 ET); compra constituye costo o gasto deducible. Documentos equivalentes (POS, tiquetes) **NO** dan derecho a IVA descontable cuando el comprador es responsable (art. 616-1 ET).",
        "**Notas crédito:** las notas crédito recibidas **reducen** el IVA descontable del período en que se reciben. Si ya se había declarado, se ajusta en el próximo período.",
    ),
    keywords=(
        "iva descontable",
        "descontar el iva", "descontar iva",
        "prorrateo", "prorratear", "proporcionalidad",
        "488", "489", "490", "491", "496", "485", "616-1", "771-5",
        "100%",
        "activo fijo", "activos fijos",
        "258-1",
        "bimestre", "cuatrimestre",
        "factura electrónica", "factura electronica",
        "cufe",
        "tiquete pos", "documento equivalente",
        "notas crédito", "notas credito",
        "exportadores",
        "operaciones gravadas",
        "operaciones exentas",
        "operaciones excluidas",
        "costo o gasto",
        "bancarizado",
    ),
    anchor_articles=("488",),
    search_queries=(
        "iva descontable prorrateo proporcionalidad art 488 490 et operaciones mixtas",
        "iva descontable activos fijos art 491 et oportunidad art 496 et bimestres",
    ),
    source_label="iva_descontable_anchor",
)
