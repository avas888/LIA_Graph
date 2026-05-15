"""v16 b4 — Formato 1001 pagos terceros (Res. DIAN 000162/2023 art. 17)."""
from __future__ import annotations

from ..case_detectors import is_exogena_1001_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="exogena_1001",
    detector=is_exogena_1001_case,
    bullets=(
        "**Formato 1001 — Pagos o abonos en cuenta a terceros** (Res. DIAN 000162/2023 art. 17, V11). Reporta todos los pagos hechos durante el AG a terceros, deducibles y no deducibles, identificando beneficiario, concepto, valor y retenciones practicadas.",
        "**Sujetos obligados:** PJ con ingresos brutos del AG 2023 **≥ 100.000 UVT** (≈ $4.241.200.000) y PN con ingresos brutos del AG 2023 **≥ $500.000.000** + obligados específicos del art. 1 Res. 000162/2023 (agentes de retención, consorcios, fiducias).",
        "**Qué se reporta:** todo pago o abono en cuenta del AG — en efectivo o en especie — a cualquier título: compras, servicios, honorarios, comisiones, arrendamientos, regalías, intereses, dividendos no gravados, viáticos, donaciones, aportes a fondos.",
        "**Cuantías mínimas:** conceptos 5004–5099 → reportar cuando el acumulado al beneficiario sea **≥ $100.000**. Pagos menores se acumulan con **NIT genérico 222222222** (\"CUANTÍAS MENORES\"). Beneficiarios del exterior: NIT **444444001** + código país.",
        "**Conceptos típicos:** **5002** honorarios; **5003** comisiones; **5004** servicios; **5005** arrendamientos; **5006** intereses y rendimientos; **5007** otros pagos; **5010** compra activos fijos; **5011** compra inventario; **5020/5022** aportes pensión; **5027** pagos al exterior; **5046** donaciones; **5060** IVA mayor valor del costo. Salarios pasaron al 2276 desde AG 2020.",
        "**Cruces obligatorios:** 1001 (pagos) ↔ 1006 del proveedor (sus ingresos); 1001 retenciones ↔ Formato **1003**; 1001 retenciones ↔ sumatoria anual de declaraciones **350**. IVA descontable va al **1005** (NO al 1001); IVA mayor valor del costo va al concepto **5060**.",
        "**Plazos:** vencimientos **abril–junio** del año siguiente según último dígito del NIT (Res. 000162/2023 art. 45 + resolución específica). Sin retención no exime de reportar — la obligación depende de que haya pago, no de que haya retención.",
    ),
    keywords=(
        "formato 1001", "1001",
        "exógena", "exogena",
        "pagos a terceros", "pago a terceros",
        "beneficiario",
        "concepto",
        "5001", "5002", "5003", "5004", "5005", "5006", "5007",
        "5010", "5011", "5020", "5022", "5027", "5046", "5060",
        "100.000 uvt", "100000 uvt",
        "500.000.000", "500000000",
        "222222222",
        "444444001",
        "$100.000",
        "cuantía mínima", "cuantia minima",
        "1003", "1005", "1006", "2276",
        "350",
        "retención", "retencion",
        "res. dian 000162", "resolucion 000162",
        "art. 631", "art 631", "631",
        "art. 651", "art 651",
        "agente de retención",
    ),
    anchor_articles=("631",),
    search_queries=(
        "formato 1001 exogena pagos terceros res dian 000162 2023 cuantias minimas",
        "concepto 5002 5003 5004 honorarios servicios formato 1001 cuadre 1003 350",
    ),
    source_label="exogena_1001_anchor",
)
