"""v16 b4 — soporte FE / documento soporte (arts. 771-2, 616-1 ET)."""
from __future__ import annotations

from ..case_detectors import is_soporte_factura_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="soporte_factura",
    detector=is_soporte_factura_case,
    bullets=(
        "**Tipos de soporte fiscal válido (art. 771-2 ET):** **Factura electrónica de venta (FEV)** con validación previa DIAN — soporte principal; **documentos equivalentes** (tiquete POS, boletas, FEV régimen simple); **documento soporte en adquisiciones a no obligados a facturar** (compras a PN no comerciantes, profesionales liberales no obligados); **nota crédito/débito electrónica** para ajustes.",
        "**Requisitos mínimos de la FE (art. 617 ET):** denominación \"Factura de Venta\"; apellidos/razón social del vendedor y adquirente con NIT; número consecutivo autorizado DIAN; fecha; descripción de bienes/servicios; valor total con IVA discriminado; calidad de retenedor IVA; firma + **CUFE** (Código Único de Factura Electrónica).",
        "**Documento soporte en adquisiciones a no obligados (Res. DIAN 000165/2023):** lo expide el **adquirente** (no el vendedor); generado electrónicamente y enviado a DIAN; identifica vendedor, descripción, fecha, valor, IVA; numeración autorizada por DIAN específica.",
        "**Plazo de validación:** el vendedor genera la FEV al momento de la operación. La validación DIAN ocurre dentro de **72 horas hábiles**. **El soporte del costo/gasto es la FEV validada**; una factura no validada (rechazada o pendiente) no es soporte definitivo.",
        "**Causación vs validación:** el costo o gasto se causa contablemente cuando se realiza el hecho económico. **Para efectos fiscales** se exige que la FEV exista y esté validada al momento de presentar la declaración. Práctica conservadora: exigir FEV al recibir el bien/servicio.",
        "**Sanciones (art. 652-1 ET):** sanción por no expedir factura: **cierre del establecimiento (3 a 30 días)** o equivalente económico. Sanción por irregularidades (art. 652 ET): **1 % del valor de la operación, hasta 950 UVT**. Sin soporte válido: rechazo de costos + posible sanción por inexactitud art. 647 ET.",
        "**IVA descontable — requisito adicional:** la FEV debe identificar plenamente al adquirente con NIT y discriminar el IVA causado. Sin esa identificación, no procede el IVA descontable (art. 488 + 771-2 ET). Conservar XML durante **5 años** (art. 632 ET).",
    ),
    keywords=(
        "factura electrónica", "factura electronica",
        "fev",
        "documento soporte",
        "documento equivalente",
        "cufe",
        "771-2", "616-1", "617", "615", "618", "652", "652-1", "657", "632", "488",
        "resolución 000165", "resolucion 000165",
        "resolución 165", "resolucion 165",
        "decreto 358",
        "xml",
        "soporte fiscal",
        "soporte documental",
        "validación dian", "validacion dian",
        "validada",
        "no obligados a facturar",
        "rut",
        "iva descontable",
        "950 uvt",
        "5 años", "cinco años",
    ),
    anchor_articles=("771-2", "616-1"),
    search_queries=(
        "factura electronica soporte costos deducciones art 771-2 et cufe validada dian",
        "documento soporte adquisiciones no obligados resolucion 000165 2023 art 616-1",
    ),
    source_label="soporte_factura_anchor",
)
