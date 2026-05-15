"""v16 (2026-05-14) — tarifa general PJ 35 % (art. 240 ET)."""
from __future__ import annotations

from ..case_detectors import is_tarifa_general_pj_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="tarifa_general_pj",
    detector=is_tarifa_general_pj_case,
    bullets=(
        "**Tarifa general AG 2025: 35 %** sobre la renta líquida gravable para personas jurídicas (sociedades nacionales, establecimientos permanentes, entidades del exterior). Vigente desde AG 2022 por Ley 2155 de 2021 art. 7.",
        "**Sobretasa sector financiero (art. 240 par. 7 ET — Ley 2277/2022):** las entidades financieras (bancos, corporaciones financieras, aseguradoras, fiduciarias, reaseguradoras, bolsas, comisionistas) tienen sobretasa de **+5 puntos** porcentuales si la renta líquida ≥ **120.000 UVT**. Tarifa total: **40 %**.",
        "**Sobretasa sector extractivo carbón/petróleo (art. 240 par. 3-4 ET):** sobretasa **variable** según percentil del precio internacional promedio del año — **5, 10 o 15 puntos** según percentil 65 / 75 / 80-100.",
        "**Sobretasa generación hidroeléctrica (art. 240 par. 2 ET):** **+3 puntos** porcentuales (tarifa total **38 %**) sobre la renta líquida superior a **30.000 UVT**.",
        "**Tarifa cooperativas (art. 19-4 ET):** **20 %** sobre los beneficios netos que no se destinen a educación formal en los términos del art. 142 Ley 1819/2016.",
        "**Tarifa ECE:** las rentas pasivas de Entidad Controlada del Exterior se gravan a la tarifa general del **35 %** en cabeza del residente colombiano controlador (arts. 882-893 ET).",
        "**Base de aplicación:** renta líquida gravable = renta líquida ordinaria − rentas exentas − descuentos por base (no descuentos tributarios). La tarifa se aplica al resultado. **TTD del 15 % (art. 240 par. 6 ET)** opera como piso mínimo de tributación cuando aplica.",
    ),
    keywords=(
        "tarifa", "tarifas",
        "35%", "35 %", "40%", "40 %", "38%", "38 %",
        "240", "240-1", "241", "242", "19-4", "235-2",
        "ttd",
        "renta líquida", "renta liquida",
        "persona jurídica", "persona juridica", "pj",
        "sas", "sociedad",
        "sobretasa", "sobretasas",
        "financiero", "extractivo", "petróleo", "petroleo",
        "carbón", "carbon", "hidroeléctrica", "hidroelectrica",
        "cooperativa", "cooperativas",
        "ece",
        "120.000 uvt", "30.000 uvt",
        "ley 2155", "ley 2277",
    ),
    anchor_articles=("240",),
    search_queries=(
        "tarifa general personas juridicas 35 por ciento art 240 et ley 2155",
        "sobretasa financiero extractivo hidroelectrica art 240 par 2 3 4 7 et",
    ),
    source_label="tarifa_general_pj_anchor",
)
