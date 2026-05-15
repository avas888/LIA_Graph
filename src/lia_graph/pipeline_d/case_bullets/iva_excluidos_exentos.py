"""v16 b3 — bienes excluidos vs exentos del IVA (arts. 424, 476, 477 ET)."""
from __future__ import annotations

from ..case_detectors import is_iva_excluidos_exentos_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="iva_excluidos_exentos",
    detector=is_iva_excluidos_exentos_case,
    bullets=(
        "**Diferencia operativa clave:** **exentos** = tarifa **0 %**, el responsable factura sin IVA, descuenta el IVA pagado en costos y **solicita devolución** del saldo a favor. **Excluidos** = están **fuera del ámbito** del impuesto, el vendedor **NO es responsable**, NO factura IVA y el IVA en compras **se vuelve mayor valor del costo** (no descontable).",
        "**Bienes excluidos típicos (art. 424 ET):** hortalizas y legumbres frescas; frutas frescas (banano, manzana, naranja); café y té sin tostar; cereales en grano; pan tradicional; sal; medicamentos esenciales del INVIMA; productos farmacéuticos y dispositivos médicos del POS; petróleo crudo destinado a refinación; gas natural; libros y revistas (art. 478 ET).",
        "**Servicios excluidos típicos (art. 476 ET):** servicios médicos, odontológicos, hospitalarios y de laboratorio; educación prestada por **establecimientos reconocidos por el Estado**; transporte público terrestre, fluvial y marítimo; servicios públicos domiciliarios; intereses y comisiones bancarias clasificadas; servicios funerarios; arrendamiento de inmuebles para vivienda.",
        "**Bienes exentos típicos (art. 477 ET):** carnes (bovina, porcina, ovina, caprina, aves, conejo) frescas/refrigeradas/congeladas; pescado fresco; leche y productos lácteos básicos; huevos; queso fresco sin madurar; fórmulas lácteas infantiles; **bienes corporales exportados**.",
        "**Régimen del contribuyente:** vende solo excluidos → **NO es responsable de IVA**, no factura IVA, no declara, el IVA en compras es costo. Vende exentos (tarifa 0 %) → **SÍ es responsable**, factura con IVA 0 %, declara bimestralmente, descuenta IVA en compras y solicita devolución. Mezcla → aplica **prorrateo art. 490 ET**.",
        "**Tratamiento contable:** bien exento → IVA descontable en cuenta 2408; bien excluido → IVA en compras al **costo o gasto** (cuenta de costo, no a 2408). Diferencia clave.",
        "**Interpretación restrictiva:** las exenciones y exclusiones tienen interpretación restrictiva. Si el bien no está expresamente listado, **se considera gravado**. La DIAN no acepta exclusiones por analogía o similitud.",
    ),
    keywords=(
        "iva",
        "excluido", "excluidos",
        "exento", "exentos",
        "excluidos vs exentos",
        "0%", "0 %", "tarifa cero",
        "424", "476", "477", "478", "481", "488",
        "carne", "leche", "huevos", "pescado",
        "frutas", "hortalizas",
        "medicamentos",
        "transporte público", "transporte publico",
        "educación", "educacion",
        "servicios médicos", "servicios medicos",
        "responsable",
        "no responsable",
        "factura sin iva",
        "exportación", "exportacion", "exportados",
        "costo o gasto",
        "2408",
        "iva descontable",
        "devolución", "devolucion",
        "saldo a favor",
        "prorrateo",
        "490",
    ),
    anchor_articles=("424", "477"),
    search_queries=(
        "excluidos vs exentos iva art 424 477 et diferencia operativa",
        "bienes exentos iva tarifa cero art 477 et derecho devolucion saldo a favor",
    ),
    source_label="iva_excluidos_exentos_anchor",
)
