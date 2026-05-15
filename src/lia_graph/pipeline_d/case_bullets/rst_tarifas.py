"""v16 (2026-05-14) — tarifas Régimen Simple (art. 908 ET)."""
from __future__ import annotations

from ..case_detectors import is_rst_tarifas_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="rst_tarifas",
    detector=is_rst_tarifas_case,
    bullets=(
        "El **Régimen Simple de Tributación (RST)** sustituye renta, INC, ICA y avisos y tableros por una **tarifa única progresiva sobre los ingresos brutos**, segmentada en **cuatro grupos** (art. 908 ET modif. Ley 2277/2022). **Tope para acceder:** ingresos brutos anuales **< 100.000 UVT** = AG 2025 **$4.706.500.000**.",
        "**Grupo 1 — Tiendas, mini-mercados, peluquerías:** tarifas bimestrales por ingresos en UVT — **1,2 %** (0-1.000), **2,8 %** (1.001-2.500), **4,4 %** (2.501-5.000), **5,6 %** (5.001-6.000).",
        "**Grupo 2 — Comercio mayor y detal, técnicos/mecánicos, construcción, talleres, hoteles, restaurantes y bares, transporte, industria manufacturera:** **1,6 %**, **2,0 %**, **3,5 %**, **4,5 %** por los mismos rangos.",
        "**Grupo 3 — Servicios profesionales y de consultoría con predominio intelectual:** **7,3 %** (0-1.000 UVT), **8,3 %** en los rangos superiores. Sub-tope: si ingresos anuales ≥ 12.000 UVT (AG 2025: $564.780.000) aplica la tarifa más alta.",
        "**Grupo 4 — Expendio de comidas y bebidas (restaurantes, panaderías, comida rápida):** **3,1 %**, **3,4 %**, **4,0 %**, **4,5 %** por los rangos UVT.",
        "**Qué sustituye y qué NO:** la tarifa unificada cubre **renta**, **INC**, **ICA** y **avisos y tableros**. **NO sustituye IVA** (se declara aparte por responsables) ni **retención en la fuente como agente retenedor** (aparte). Aportes a seguridad social y parafiscales se pagan independiente. **Anticipos bimestrales (art. 910 ET):** Formulario 2593 cada bimestre, Formulario 260 anual.",
        "**Descuentos en el RST (art. 912 ET):** aportes obligatorios de pensión que el empleador realice (**50 % como descuento**); retenciones que terceros le hayan practicado al RST; **0,5 % del impuesto** del bimestre si los pagos son por medios electrónicos.",
    ),
    keywords=(
        "rst", "régimen simple", "regimen simple",
        "simple", "simples",
        "908", "905", "906", "910", "912", "903",
        "tarifa", "tarifas",
        "grupo 1", "grupo 2", "grupo 3", "grupo 4",
        "1,2%", "2,8%", "4,4%", "5,6%",
        "1,6%", "2,0%", "3,5%", "4,5%",
        "7,3%", "8,3%",
        "3,1%", "3,4%", "4,0%",
        "100.000 uvt", "12.000 uvt",
        "uvt",
        "bimestre", "bimestral", "bimestrales",
        "formulario 2593", "formulario 260",
        "ica",
        "inc",
        "avisos y tableros",
        "ley 2277", "decreto 0875",
        "anticipo", "anticipos",
        "tienda", "tiendas", "peluquería", "peluqueria",
        "restaurante", "restaurantes",
        "servicios profesionales", "consultoría", "consultoria",
        "ingresos brutos",
    ),
    anchor_articles=("908",),
    search_queries=(
        "tarifas regimen simple tributacion rst art 908 et ley 2277",
        "grupos rst 1 2 3 4 tarifas bimestrales uvt 100000 anuales",
    ),
    source_label="rst_tarifas_anchor",
)
