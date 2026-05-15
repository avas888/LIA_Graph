"""v16 b5 — impuesto diferido (NIC 12 / Sección 29 NIIF PYMES)."""
from __future__ import annotations

from ..case_detectors import is_impuesto_diferido_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="impuesto_diferido",
    detector=is_impuesto_diferido_case,
    bullets=(
        "**Método obligatorio — pasivo basado en balance (NIC 12 / Sección 29 NIIF PYMES):** compare la **base contable NIIF** de cada activo y pasivo con su **base fiscal**, y reconozca el efecto fiscal futuro a la **tasa aplicable** cuando se revierta la diferencia. **No** se acepta el método basado en estado de resultados (antiguo Colgaap).",
        "**Diferencia temporaria imponible (DTI) → pasivo por impuesto diferido.** Surge cuando **base contable > base fiscal** en activos. La empresa pagará **más** impuesto en el futuro. Ejemplos: depreciación fiscal acelerada > depreciación NIIF; mediciones a valor razonable PPyE; revaluación de propiedades; ingresos por dividendos no realizados.",
        "**Diferencia temporaria deducible (DTD) → activo por impuesto diferido.** Surge cuando **base contable < base fiscal** en activos. La empresa pagará **menos** impuesto en el futuro. Ejemplos: provisión cartera no deducida (art. 145 ET); **pérdidas fiscales por compensar** (art. 147 ET — 12 años); deterioros NIIF no aceptados fiscalmente; estimación de garantías y litigios.",
        "**Tasa aplicable — la del momento de reversión** considerando normas vigentes o promulgadas a la fecha del balance. PJ ordinaria colombiana: **35 %** (art. 240 ET). Zona franca: **20 %**. Si una reforma aprobada modifica la tarifa hacia adelante → **ajustar el cálculo** del diferido.",
        "**Reconocimiento del activo diferido — prueba de probabilidad:** solo si es **probable** (> 50 %) que la empresa genere **renta gravable suficiente** en los períodos en que se revertirá la diferencia. Documentar: proyecciones financieras 3-5 años; historial de utilidades fiscales; análisis de pérdidas por compensar (12 años art. 147 ET). Sin probabilidad → **no reconocer** y revelarlo en notas.",
        "**Presentación en EE.FF.:** impuesto diferido (activo o pasivo) en ESF como **no corriente**, separado del impuesto corriente. ERI: gasto por impuesto = corriente + diferido. **Compensación de activos y pasivos diferidos:** solo si misma autoridad fiscal (DIAN) y derecho legalmente exigible — para PJ colombianas, presentación neta estándar.",
        "**Pérdidas fiscales por compensar (art. 147 ET):** generan **activo diferido = pérdida fiscal × 35 %**, recuperable hasta **12 años** desde la generación, sin reajuste. Requiere prueba de probabilidad reforzada — historial de pérdidas continuadas debilita el reconocimiento. **Revelación en notas (NIC 12.79-88):** componentes del gasto por impuesto, **conciliación numérica entre gasto teórico (utilidad × tarifa) y gasto efectivo**, diferencias temporarias acumuladas, pérdidas no reconocidas con vencimiento, cambios de tarifa.",
    ),
    keywords=(
        "impuesto diferido",
        "activo por impuesto diferido",
        "pasivo por impuesto diferido",
        "activo diferido",
        "pasivo diferido",
        "nic 12",
        "ias 12",
        "sección 29 niif", "seccion 29 niif",
        "ifrs",
        "diferencia temporaria",
        "diferencia temporaria imponible",
        "diferencia temporaria deducible",
        "dti", "dtd",
        "método del pasivo", "metodo del pasivo",
        "pasivo basado en balance",
        "base contable",
        "base fiscal",
        "35%", "35 %",
        "20%", "20 %",
        "240",
        "137", "145", "147",
        "12 años",
        "probabilidad",
        "renta gravable",
        "valor razonable",
        "revaluación", "revaluacion",
        "no corriente",
        "ley 1314",
        "decreto 2420",
        "ctcp",
        "f2516",
        "conciliación tarifa efectiva", "conciliacion tarifa efectiva",
        "ley 2277",
    ),
    anchor_articles=("240",),
    search_queries=(
        "impuesto diferido nic 12 seccion 29 niif pymes metodo pasivo balance",
        "diferencias temporarias imponibles deducibles activo pasivo diferido 35 por ciento",
    ),
    source_label="impuesto_diferido_anchor",
)
