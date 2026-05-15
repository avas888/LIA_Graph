"""v16 (2026-05-14) — tarifa dividendos PN residentes (art. 242 ET)."""
from __future__ import annotations

from ..case_detectors import is_dividendos_pn_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="dividendos_pn",
    detector=is_dividendos_pn_case,
    bullets=(
        "**Cambio estructural Ley 2277/2022:** se **eliminó la cédula independiente de dividendos** para PN residentes. Los dividendos se integran a la **cédula general** junto con rentas de trabajo, capital y no laborales, y se gravan a las **tarifas marginales del art. 241 ET (0 % a 39 %)**.",
        "**Dividendos de utilidades gravadas en cabeza de la sociedad** (art. 49 ET — la sociedad pagó impuesto): se gravan en cabeza del socio dentro de la cédula general a tarifas del art. 241 ET.",
        "**Dividendos de utilidades no gravadas en cabeza de la sociedad** (INCR o exentas en la sociedad): se gravan primero a la **tarifa general del 35 %** y el resultado neto se integra a la cédula general.",
        "**Régimen de transición — utilidades 2016 y anteriores:** son **ingresos no constitutivos de renta** (INCR) en cabeza del socio. Utilidades 2017-2022 mantienen tarifa preferencial (5 %-10 % bajo Ley 1819/2016).",
        "**Descuento del 19 % (art. 254-1 ET):** las PN residentes toman como descuento **19 % sobre los dividendos que excedan 1.090 UVT** anuales. Para AG 2025 (UVT $47.065): 1.090 UVT = **$51.300.850**. Ejemplo — dividendos de **$80.000.000** → base = $80.000.000 − $51.300.850 = **$28.699.150** → descuento = 19 % × $28.699.150 = **$5.452.838**.",
        "**Retención en la fuente (Decreto 1103/2023):** la sociedad practica retención a tarifas progresivas — **0 % hasta 1.090 UVT**, **15 % sobre el exceso entre 1.090 y 3.270 UVT**, y tarifa creciente sobre 3.270 UVT. Es a título de renta — descontable en la declaración del beneficiario.",
        "**Registro en formulario 210:** los dividendos van en \"Rentas no laborales\" o \"Rentas de capital\" dentro de la cédula general. El descuento del 19 % se diligencia en descuentos tributarios.",
    ),
    keywords=(
        "dividendos", "dividendo", "participaciones",
        "242", "241", "254-1", "245", "49",
        "1.090 uvt", "1090 uvt", "3.270 uvt", "3270 uvt",
        "19%", "19 %",
        "0%", "15%",
        "cédula general", "cedula general",
        "cédula independiente", "cedula independiente",
        "ley 2277", "decreto 1103",
        "retención en la fuente", "retencion en la fuente",
        "tarifa marginal", "tarifas marginales",
        "pn residente", "persona natural residente",
        "renta de capital", "rentas no laborales",
        "formulario 210",
        "descuento", "descontable",
        "incr",
    ),
    anchor_articles=("242",),
    search_queries=(
        "tarifa dividendos personas naturales residentes art 242 et ley 2277",
        "descuento 19 por ciento dividendos 1090 uvt art 254-1 et",
    ),
    source_label="dividendos_pn_anchor",
)
