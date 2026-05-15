"""v16 b5 — dividendos no gravados (art. 49 ET)."""
from __future__ import annotations

from ..case_detectors import is_dividendos_no_gravados_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="dividendos_no_gravados",
    detector=is_dividendos_no_gravados_case,
    bullets=(
        "**Fórmula art. 49 ET — Utilidad Máxima No Gravada (UMNG):** renta líquida gravable × tarifa nominal − impuesto a cargo neto de descuentos + INCRNGO ya distribuidos + descuentos por impuestos pagados en el exterior. Esa suma es la **UMNG**, monto máximo distribuible como dividendo **no gravado** en cabeza del socio.",
        "**Compare UMNG con utilidad contable después de impuestos (UCDI):** **UCDI ≤ UMNG** → toda la utilidad distribuible como **no gravada**. **UCDI > UMNG** → el exceso (UCDI − UMNG) se distribuye como **gravado** y tributa adicionalmente en cabeza del receptor.",
        "**Tributación PN residente post Ley 2277/2022 (AG 2023+):** **Dividendos no gravados** → cédula general con tarifa marginal **art. 241 ET** (0 % a 39 %); sociedad retiene **15 %** sobre exceso de **1.090 UVT** (art. 242 ET + Decreto 1103/2023); descuento **art. 254-1 ET = 19 % del dividendo** (hasta impuesto generado por cédula). **Dividendos gravados** → primero retención **35 %** (tarifa nominal PJ), remanente sigue regla anterior.",
        "**Otros receptores:** **PN no residente** → **20 %** sobre no gravados; sobre gravados primero 35 % y luego 20 % al remanente (art. 245 ET). **Sociedad nacional receptora** → **10 %** retención a título de renta (art. 242-1 ET); se acredita cuando distribuye a sus socios PN.",
        "**Certificación al socio:** la sociedad emite certificado discriminando porción **no gravada** y **gravada**, retención practicada, año al que corresponde la utilidad. **Soporte obligatorio** para la declaración del receptor. Emitir antes del **31 de marzo** del año siguiente.",
        "**Retenciones en Formulario 350:** **concepto 36** dividendos PN residente no gravados; **37** gravados; **38** no residentes; **39** sociedades nacionales receptoras.",
        "**Tip de planeación:** el descuento art. 254-1 ET compensa parcialmente el impuesto en cédula general. **Tributación efectiva total típica PYME socio único PN residente: ~38-42 %** sobre la utilidad original (vs ~35 % pre-Ley 2277). Modele antes de definir política de dividendos.",
    ),
    keywords=(
        "dividendos", "dividendo",
        "participaciones",
        "no gravado", "no gravados",
        "gravado", "gravados",
        "49", "48",
        "242", "242-1", "245",
        "254-1",
        "umng",
        "utilidad máxima", "utilidad maxima",
        "ucdi",
        "renta líquida gravable", "renta liquida gravable",
        "fórmula", "formula",
        "tarifa marginal",
        "1.090 uvt", "1090 uvt",
        "19%", "19 %",
        "15%", "15 %",
        "20%", "20 %",
        "10%", "10 %",
        "35%", "35 %",
        "decreto 1103",
        "ley 2277",
        "certificado de dividendos",
        "incr", "incrngo",
        "cédula general", "cedula general",
        "concepto 36", "concepto 37", "concepto 38", "concepto 39",
        "formulario 350",
        "31 de marzo", "31 marzo",
    ),
    anchor_articles=("49",),
    search_queries=(
        "dividendos no gravados art 49 et formula umng utilidad maxima",
        "tarifa dividendos pn residente ley 2277 cedula general 19 descuento 254-1 et",
    ),
    source_label="dividendos_no_gravados_anchor",
)
