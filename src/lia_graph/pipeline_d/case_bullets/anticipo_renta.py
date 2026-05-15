"""v16 b4 — anticipo del impuesto de renta (arts. 807, 809 ET)."""
from __future__ import annotations

from ..case_detectors import is_anticipo_renta_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="anticipo_renta",
    detector=is_anticipo_renta_case,
    bullets=(
        "**Porcentaje del anticipo según historial:** **Primera declaración → 25 %** del impuesto neto del AG. **Segunda → 50 %** del promedio de los dos últimos años (o 50 % del AG, el menor). **Tercera en adelante → 75 %** sobre la base que elija el contribuyente (art. 807 ET).",
        "**Dos opciones de base para 75 %:** **Opción A** — 75 % del impuesto neto del AG declarado. **Opción B** — 75 % del **promedio** del impuesto neto del AG declarado y del AG anterior. El contribuyente elige la **menor**. Documentar la elección en papel de trabajo.",
        "**Reste las retenciones del AG.** Anticipo final = (porcentaje × base) − retenciones a favor del AG. Si negativo, el anticipo es **cero**.",
        "**Imputación al año siguiente:** el anticipo se imputa como pago al impuesto de renta del AG siguiente, en el renglón \"Anticipo del año anterior\" del formulario 110.",
        "**Reducción del anticipo (art. 809 ET):** procede solicitud cuando se prevé impuesto inferior. Plazo: **antes del 31 de julio** del año siguiente al que se liquida. Causales: reducción de ingresos ≥ **25 %**, terminación de actividad. DIAN responde en **2 meses**; **silencio administrativo positivo**.",
        "**Casos sin anticipo (art. 808 ET):** contribuyentes que dejan de existir; PN no obligadas a llevar contabilidad con impuesto cero; **contribuyentes del RST** (liquidan anticipos bimestrales — art. 911 ET — y NO anticipo anual ordinario).",
        "**Tip:** cuando el AG es atípicamente alto (ingreso extraordinario, venta de activos), comparar las dos opciones de base. El **promedio** suele ser más favorable porque suaviza el pico. Registrar como cuenta por cobrar 1355 al cierre.",
    ),
    keywords=(
        "anticipo",
        "807", "808", "809", "810", "911",
        "25%", "50%", "75%",
        "impuesto neto",
        "renta",
        "reducción", "reduccion",
        "31 de julio", "31 julio",
        "silencio administrativo",
        "retenciones",
        "promedio",
        "primera declaración", "primera declaracion",
        "segunda declaración", "segunda declaracion",
        "rst",
        "1355",
        "formulario 110", "formulario 210",
    ),
    anchor_articles=("807",),
    search_queries=(
        "anticipo del impuesto de renta art 807 et 25 50 75 por ciento",
        "reduccion anticipo art 809 et 31 de julio silencio administrativo positivo",
    ),
    source_label="anticipo_renta_anchor",
)
