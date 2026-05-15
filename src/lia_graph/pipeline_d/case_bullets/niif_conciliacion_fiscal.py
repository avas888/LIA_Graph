"""v16 b4 — conciliación fiscal F2516 / F2517 (art. 772-1 ET)."""
from __future__ import annotations

from ..case_detectors import is_niif_conciliacion_fiscal_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="niif_conciliacion_fiscal",
    detector=is_niif_conciliacion_fiscal_case,
    bullets=(
        "**Quién presenta F2516 vs F2517 (art. 772-1 ET):** **F2516** — grandes contribuyentes calificados por DIAN **O** contribuyentes con ingresos brutos fiscales **≥ 45.000 UVT** (AG 2025 UVT $47.065 → **$2.117.925.000**). **F2517** — demás PJ y PN obligadas a llevar contabilidad. Versión simplificada.",
        "**No obligados:** PN no obligadas a llevar contabilidad; contribuyentes del **RST** (aplica solo a régimen ordinario); entidades del RTE sin actividad comercial.",
        "**Naturaleza:** la conciliación fiscal es **anexo** de la declaración de renta (formulario 110), **no** la sustituye. Mismo plazo, mismo contribuyente. Se carga en MUISCA en formato **XML** según especificaciones técnicas vigentes.",
        "**Estructura del F2516:** Sección **ERI** (Estado de Resultados Integral) reproduce el ERI contable NIIF línea a línea; **ESF** (Estado de Situación Financiera) — activos, pasivos, patrimonio; **Conciliación Patrimonio Contable vs Fiscal**; **Conciliación Renta** — partidas conciliatorias NIIF → renta líquida fiscal; **Impuesto Diferido** — activo y pasivo conciliados con notas EE.FF.",
        "**Diferencias temporarias (DT) vs permanentes (DP):** **Temporarias** — se revierten en períodos futuros y generan impuesto diferido (ej. depreciación acelerada art. 137 vs NIIF, provisión cartera art. 145, pérdidas fiscales). **Permanentes** — no se revierten ni generan impuesto diferido (ej. **50 % del GMF no deducible** art. 115, gastos sin RUT, sanciones e intereses moratorios).",
        "**Ejemplo DT — maquinaria $100.000.000:** depreciación NIIF lineal 10 años = $10.000.000/año. Depreciación fiscal acelerada 20 % = **$20.000.000**. DT año 1 = $10.000.000 → **pasivo por impuesto diferido = $10M × 35 % = $3.500.000**. **Ejemplo DP — GMF $2.000.000 pagado:** 50 % deducible ($1.000.000), 50 % no deducible ($1.000.000) → diferencia permanente, sin impuesto diferido.",
        "**Renglones críticos antes de presentar:** total ingresos NIIF (ERI) = balance contable; renta líquida fiscal del 2516 = renglón \"Renta líquida del ejercicio\" del 110; impuesto neto del 2516 = impuesto neto del 110; patrimonio fiscal del 2516 = patrimonio fiscal del 110. **Cualquier desfase dispara revisión DIAN.** Plazo de conservación: **5 años** (art. 632 ET).",
    ),
    keywords=(
        "conciliación fiscal", "conciliacion fiscal",
        "f2516", "f2517",
        "formato 2516", "formato 2517",
        "2516", "2517",
        "772-1",
        "45.000 uvt", "45000 uvt",
        "diferencia temporaria", "diferencia permanente",
        "diferencias temporarias", "diferencias permanentes",
        "dt", "dp",
        "impuesto diferido",
        "activo por impuesto diferido", "pasivo por impuesto diferido",
        "niif", "nic 12",
        "eri", "estado de resultados integral",
        "esf", "estado de situación financiera",
        "decreto 1998", "decreto 1625",
        "resolución 000071", "resolucion 000071",
        "ley 1314",
        "art. 632", "art 632",
        "art. 647", "art 647",
        "art. 651", "art 651",
        "art. 28", "art. 105", "art. 137", "art. 145",
        "xml",
        "muisca",
        "patrimonio contable",
        "patrimonio fiscal",
    ),
    anchor_articles=("772-1",),
    search_queries=(
        "conciliacion fiscal f2516 f2517 art 772-1 et 45000 uvt grandes contribuyentes",
        "diferencias temporarias permanentes impuesto diferido niif vs et conciliacion fiscal",
    ),
    source_label="niif_conciliacion_fiscal_anchor",
)
