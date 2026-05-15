"""v16 b5 — Impuesto Nacional al Consumo (art. 512-1 ET)."""
from __future__ import annotations

from ..case_detectors import is_inc_consumo_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="inc_consumo",
    detector=is_inc_consumo_case,
    bullets=(
        "**Hechos generadores y tarifas (art. 512-1 ET):** **telefonía/datos/internet 4 %** (sobre valor > 4 UVT mensuales por línea, art. 512-2); **restaurantes, cafeterías, panaderías, bares 8 %** (arts. 512-9 a 512-13); **vehículos ≤ USD 30.000 → 8 %**, **> USD 30.000 → 16 %** (art. 512-15); **yates / aeronaves privadas → 16 %**; **bolsas plásticas** tarifa por unidad indexada en UVT (art. 512-4).",
        "**Restaurantes vs franquicias:** restaurante sin franquicia → **INC 8 %**. **Franquicias internacionales** (McDonald's, KFC, Subway) → **IVA 19 %**, no INC (Ley 2010/2019). El catering empresarial corporativo paga IVA 19 % (servicio empresarial), no INC.",
        "**Vehículos — alcance art. 512-15:** aplica a autos, camperos, pick-ups, motocicletas > 200 cc, yates, aeronaves, lanchas, planeadores. **NO aplica** a vehículos comerciales (carga, transporte público), taxis. **Vehículos usados destinados a uso particular: excluidos.** Importación: causación al momento de nacionalización.",
        "**Régimen Simple (RST):** los responsables del INC restaurante que se inscriban en **RST quedan exonerados del INC** — la tarifa unificada del RST lo integra (art. 907 ET).",
        "**Tratamiento contable — para el responsable** (vendedor/prestador): cuenta **2408** (impuestos por pagar — INC); causación en facturación. **Para el comprador:** el INC **NO es descontable** como IVA — es **mayor valor del costo o gasto** (art. 512-1 par. 3 ET). Ejemplo: almuerzo $100.000 + INC $8.000 = gasto deducible $108.000 (sujeto a causalidad).",
        "**Obligaciones del responsable:** inscripción RUT con responsabilidad INC; facturación electrónica obligatoria discriminando INC; **declaración bimestral en Formulario 310**. **No hay retención en la fuente del INC**.",
        "**No responsables INC restaurantes (art. 512-13 ET — Ley 2277/2022):** ingresos brutos del año anterior **< 3.500 UVT** (≈ $164.727.500 UVT 2025); no franquicia; un solo establecimiento; sin actividades complementarias gravadas con IVA.",
    ),
    keywords=(
        "inc",
        "impuesto al consumo",
        "impuesto nacional al consumo",
        "512-1", "512-2", "512-4", "512-9", "512-10", "512-11", "512-12", "512-13", "512-14", "512-15",
        "4%", "4 %",
        "8%", "8 %",
        "16%", "16 %",
        "restaurante", "restaurantes",
        "bar", "bares",
        "telefonía", "telefonia",
        "datos", "internet",
        "vehículo", "vehiculo", "vehículos", "vehiculos",
        "yate", "yates", "aeronave", "aeronaves",
        "bolsas plásticas", "bolsas plasticas",
        "franquicia", "franquicias",
        "rst", "régimen simple", "regimen simple",
        "907",
        "descontable",
        "mayor valor del costo",
        "formulario 310",
        "ley 1607", "ley 2010", "ley 2277",
        "ley 2010/2019",
        "3.500 uvt",
    ),
    anchor_articles=("512-1",),
    search_queries=(
        "impuesto nacional al consumo inc art 512-1 et tarifas restaurantes vehiculos",
        "inc 8 por ciento restaurantes franquicia iva 19 ley 2010 art 512-13",
    ),
    source_label="inc_consumo_anchor",
)
