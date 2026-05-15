"""v16 b4 — compensación de pérdidas fiscales (art. 147 ET)."""
from __future__ import annotations

from ..case_detectors import is_compensacion_perdidas_fiscales_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="compensacion_perdidas",
    detector=is_compensacion_perdidas_fiscales_case,
    bullets=(
        "**Quién compensa:** únicamente **sociedades** (PJ contribuyentes del régimen ordinario). Las personas naturales **no** compensan pérdidas fiscales con esta regla (tienen reglas cedulares específicas).",
        "**Plazo (Ley 1819/2016):** las pérdidas generadas a partir del **AG 2017** se compensan con la renta líquida ordinaria de los **12 períodos gravables siguientes**. Pasados los 12 años, la pérdida no compensada se pierde.",
        "**Régimen de transición — pérdidas hasta AG 2016 (art. 290 num. 5 ET):** conservan el régimen anterior (Ley 1607/2012) — compensación sin límite de tiempo. PERO obliga recalcular la pérdida acumulada al 31/12/2016 por fórmula de transición (proporción tarifa nueva 35 % vs histórica).",
        "**Reajuste fiscal:** la Ley 1819/2016 **eliminó el reajuste fiscal** sobre pérdidas generadas a partir del AG 2017. Las de AG 2016 y anteriores conservan reajuste histórico hasta 31/12/2016, pero no se siguen reajustando.",
        "**Aplicación:** en el AG con renta líquida positiva, la sociedad toma el monto acumulado disponible y lo resta en el renglón \"compensaciones\" del formulario 110. La compensación **no puede generar pérdida nueva** — se compensa hasta agotar la renta líquida del AG.",
        "**Firmeza especial — 5 años:** cuando la declaración compense o determine pérdidas, la firmeza es de **5 años** (art. 117 Ley 2010 de 2019 que modificó el art. 147 inciso final ET). Aplica al AG de generación y al AG de compensación.",
        "**Operaciones societarias (art. 156 ET):** fusión — la absorbente compensa pérdidas de la absorbida **proporcionalmente al patrimonio aportado**, con actividades similares. Escisión — proporcional al patrimonio que conserva. **No** se puede \"comprar\" pérdidas vía control. Solo se compensan contra **renta líquida ordinaria**, no contra ganancia ocasional.",
    ),
    keywords=(
        "compensación", "compensacion",
        "compensar", "compensa",
        "pérdida", "perdida",
        "pérdidas fiscales", "perdidas fiscales",
        "147", "290", "714", "156", "26", "178",
        "12 años", "12 periodos", "doce años", "doce periodos",
        "5 años", "cinco años",
        "ag 2017", "ag 2016",
        "ley 1819", "ley 2010", "ley 1607",
        "art. 117 ley 2010", "art 117 ley 2010",
        "reajuste fiscal",
        "renta líquida", "renta liquida",
        "fusión", "fusion", "escisión", "escision",
        "absorbente", "absorbida",
        "impuesto diferido",
        "f2516",
        "firmeza especial",
        "ganancia ocasional",
        "rst", "régimen simple", "regimen simple",
    ),
    anchor_articles=("147",),
    search_queries=(
        "compensacion de perdidas fiscales sociedades art 147 et 12 años",
        "firmeza especial 5 años compensacion perdidas art 147 ley 2010 art 117",
    ),
    source_label="compensacion_perdidas_anchor",
)
