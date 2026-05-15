"""v16 b3 — hecho generador del IVA (arts. 420 y 421 ET)."""
from __future__ import annotations

from ..case_detectors import is_iva_hecho_generador_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="iva_hecho_generador",
    detector=is_iva_hecho_generador_case,
    bullets=(
        "**Hechos generadores del IVA (art. 420 ET):** **(a)** venta de bienes corporales muebles e inmuebles no excluidos; **(b)** cesión de derechos sobre **activos intangibles** asociados con propiedad industrial; **(c)** **prestación de servicios** en territorio nacional o desde el exterior cuando el usuario directo es residente fiscal en Colombia; **(d)** **importación** de bienes corporales muebles no excluidos; **(e)** **juegos de suerte y azar** (salvo loterías).",
        "**Momento de causación (art. 429 ET):** **Ventas:** fecha de emisión de la factura; si no hay obligación de facturar, fecha de entrega. **Servicios:** fecha de emisión de factura, terminación del servicio, o pago/abono en cuenta — **lo que ocurra primero**. **Importaciones:** nacionalización del bien (declaración de importación). **Retiros de inventario (art. 421 ET):** fecha del retiro.",
        "**Territorialidad (art. 420 par. 3 ET):** servicios prestados desde el exterior se entienden en Colombia cuando el **usuario directo** tiene residencia fiscal, domicilio o establecimiento permanente en Colombia. Aplica a servicios digitales prestados por no residentes (régimen art. 437-2 num. 8 ET).",
        "**Operaciones asimiladas a venta (art. 421 ET):** retiro de bienes para uso propio o destino no gravado; incorporación de bienes corporales a inmuebles o servicios no gravados; transferencias entre vinculados.",
        "**Bienes y servicios no gravados:** **excluidos** (arts. 424, 476 ET) — NO generan IVA, el vendedor NO es responsable, el IVA en compras es mayor valor del costo. **Exentos** (arts. 477, 478, 481 ET) — tarifa **0 %**, el vendedor SÍ es responsable, descuenta IVA en compras y solicita devolución del saldo a favor.",
        "**Venta de activos fijos:** la venta **ocasional** de activos fijos **NO genera IVA** (doctrina DIAN reiterada). Excepción: aerodinos y automotores por contribuyentes habituales (concesionarios) → sí grava.",
        "**Donaciones y operaciones gratuitas:** las entregas gratuitas pueden generar IVA cuando se asimilan a retiro de inventario (art. 421 ET) o cuando hay autoconsumo.",
    ),
    keywords=(
        "iva",
        "hecho generador",
        "hechos generadores",
        "420", "421", "424", "426", "429", "437", "476", "477", "478", "481",
        "causación", "causacion",
        "venta",
        "servicios",
        "importación", "importacion",
        "juegos de suerte y azar",
        "territorialidad",
        "retiro de inventario",
        "activo fijo", "activos fijos",
        "responsable",
        "excluido", "excluidos", "exento", "exentos",
        "0%", "0 %",
        "factura",
        "nacionalización", "nacionalizacion",
        "autoconsumo",
        "donación", "donacion",
    ),
    anchor_articles=("420",),
    search_queries=(
        "hechos generadores del iva art 420 et venta servicios importacion juegos",
        "causacion iva art 429 et fecha factura entrega pago abono cuenta",
    ),
    source_label="iva_hecho_generador_anchor",
)
