"""v16 b4 — Formato 1005 IVA descontable (Res. DIAN 000162/2023 art. 21)."""
from __future__ import annotations

from ..case_detectors import is_exogena_1005_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="exogena_1005",
    detector=is_exogena_1005_case,
    bullets=(
        "**Formato 1005 — IVA descontable** (Res. DIAN 000162/2023 art. 21, V7). Reporta cada operación que generó IVA descontable durante el AG, identificando proveedor, base gravable, IVA descontable y tipo de operación.",
        "**Sujetos obligados:** responsables del IVA con ingresos brutos del AG anterior por encima del umbral de Res. 000162/2023 (regla general: PJ ≥ **100.000 UVT** y PN ≥ **$500.000.000**).",
        "**Qué se reporta por operación:** NIT/cédula del proveedor; apellidos/razón social; **base gravable** del IVA descontable; **valor del IVA descontable**; **tarifa aplicada** (5 %, 19 %); concepto (bienes, servicios, importaciones, devoluciones, retenciones).",
        "**Periodicidad:** **anual** (consolidado de los 6 bimestres o 3 cuatrimestres del AG), permitiendo identificar el período fiscal de cada operación según el anexo técnico vigente.",
        "**Cruce obligatorio con declaración 300:** suma del IVA descontable del 1005 = suma del renglón \"Total IVA descontable\" de todas las declaraciones 300 del AG. Diferencias **> 1 UVT** activan validación de inconsistencia y carta DIAN.",
        "**IVA en importaciones:** sí se reporta — NIT del proveedor del exterior **444444001** + código país; valor declarado en la importación + IVA pagado en aduana. **Notas crédito** de compras se reportan con valor **negativo** en el período en que se reciben.",
        "**IVA descontable proporcional (art. 490 ET):** cuando hay operaciones gravadas + exentas + excluidas, aplicar prorrateo en la 300 y reportar en 1005 únicamente la porción descontable efectivamente tomada. Operaciones exentas/excluidas del proveedor → NO van en 1005.",
    ),
    keywords=(
        "formato 1005", "1005",
        "exógena", "exogena",
        "iva descontable",
        "488", "489", "490", "491", "496",
        "300", "1006",
        "100.000 uvt",
        "5%", "19%",
        "5 %", "19 %",
        "tarifa",
        "proveedor",
        "base gravable",
        "importación", "importacion",
        "444444001",
        "notas crédito", "notas credito",
        "prorrateo", "proporcionalidad",
        "operaciones gravadas",
        "operaciones exentas",
        "operaciones excluidas",
        "1 uvt",
        "validación", "validacion",
        "art. 631", "art 631",
        "art. 651", "art 651",
    ),
    anchor_articles=("488",),
    search_queries=(
        "formato 1005 exogena iva descontable res dian 000162 2023",
        "cuadre 1005 con 300 iva descontable proveedores prorrateo art 490 et",
    ),
    source_label="exogena_1005_anchor",
)
