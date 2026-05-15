"""v16 b4 — Formato 1007 ingresos (Res. DIAN 000162/2023 art. 23)."""
from __future__ import annotations

from ..case_detectors import is_exogena_1007_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="exogena_1007",
    detector=is_exogena_1007_case,
    bullets=(
        "**Formato 1007 — Ingresos recibidos** (Res. DIAN 000162/2023 art. 23, V9). Reporta ingresos recibidos durante el AG por todo concepto (operacionales y no operacionales), identificando comprador/usuario, concepto y valor.",
        "**Sujetos obligados:** PJ y PN con ingresos brutos del AG anterior > umbral (regla general AG 2025: PJ ≥ **100.000 UVT**, PN ≥ **$500.000.000**); agentes de retención; consorcios; fiducias.",
        "**Qué se reporta por ingreso:** NIT/cédula del comprador/usuario; apellidos/razón social; **concepto (4xxx)**; **valor del ingreso bruto recibido** durante el AG; **devoluciones, rebajas y descuentos** asociados (columna separada); **ingreso no gravado** asociado.",
        "**Conceptos típicos:** **4001** ventas; **4002** servicios; **4003** honorarios; **4004** comisiones; **4005** intereses y rendimientos; **4006** arrendamientos; **4007** dividendos y participaciones; **4008** enajenación activos fijos; **4009** indemnizaciones; **4010** otros no operacionales; **4012** INCRNGO.",
        "**Cuantías mínimas:** acumulado anual con un mismo comprador **≥ $500.000** (verificar resolución vigente). Por debajo, acumular en NIT **222222222**. Ingresos del exterior: NIT genérico **444444001** + código país.",
        "**Devoluciones, rebajas y descuentos:** se reportan en **columna separada** por cada NIT en el mismo concepto, **NO se restan** del valor bruto. El total devoluciones del 1007 cuadra con devoluciones de la declaración de renta y del 300 IVA.",
        "**Cruces obligatorios:** 1007 total = ingresos brutos formulario 110/210; 1007 por NIT del cliente ↔ 1001 del cliente; 1007 ingresos gravados con IVA ↔ ingresos del 300 + 1006. **Anticipos de clientes:** no son ingreso fiscal hasta su realización (art. 28 ET); se reportan cuando se causa el ingreso.",
    ),
    keywords=(
        "formato 1007", "1007",
        "exógena", "exogena",
        "ingresos recibidos", "ingresos brutos",
        "concepto",
        "4001", "4002", "4003", "4004", "4005", "4006", "4007", "4008", "4009", "4010", "4012",
        "comprador", "usuario", "cliente",
        "100.000 uvt",
        "500.000.000",
        "222222222",
        "444444001",
        "$500.000",
        "devoluciones",
        "rebajas",
        "descuentos",
        "1001", "300", "1006",
        "formulario 110", "formulario 210",
        "anticipo", "anticipos",
        "incr", "incrngo",
        "art. 26", "art 26", "art. 27", "art 27", "art. 28", "art 28",
        "art. 631", "art 631",
    ),
    anchor_articles=("631",),
    search_queries=(
        "formato 1007 exogena ingresos res dian 000162 2023 cuantias minimas",
        "cuadre 1007 con formulario 110 210 ingresos brutos devoluciones rebajas",
    ),
    source_label="exogena_1007_anchor",
)
