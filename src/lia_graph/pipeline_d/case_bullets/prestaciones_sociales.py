"""v17 b1 — prestaciones sociales (cesantías + intereses + prima + vacaciones).

Anchored at ET arts. 108 + 387 (Option A per fix_v17_may §3.3). El régimen
sustantivo está en CST 249-258 + 306-308 + 186-197 y Ley 50/1990 art. 99 ss
(citado en bullets).
"""
from __future__ import annotations

from ..case_detectors import is_prestaciones_sociales_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="prestaciones_sociales",
    detector=is_prestaciones_sociales_case,
    bullets=(
        "**Cesantías (Ley 50/1990 art. 99 ss):** **1 mes de salario por año** trabajado, proporcional por fracción. Base = salario + **auxilio de transporte** (asimilado por jurisprudencia). Fórmula: `(salario base × días trabajados) / 360`. Consignación al fondo elegido por el trabajador **antes del 15 de febrero** del año siguiente.",
        "**Intereses a las cesantías (Decreto 116/1976 + Ley 52/1975):** **12 % anual** sobre el saldo acumulado al 31 dic, proporcional. Fórmula: `(cesantías × días × 12 %) / 360`. Plazo de pago: **hasta el 31 de enero** del año siguiente, **al trabajador directamente** (no al fondo). Si no se pagan en plazo, **se duplica el valor**.",
        "**Prima de servicios (CST art. 306, modif. Ley 1788/2016):** **30 días de salario por año**, proporcional. Se paga en dos contados: **15 días en junio (límite 30 jun)** y **15 días en diciembre (límite 20 dic)**. Base = salario + auxilio de transporte, incluye recargos y comisiones promedio del semestre. Ley 1788/2016 la universalizó a servicio doméstico.",
        "**Vacaciones (CST arts. 186 a 197):** **15 días hábiles** consecutivos por año trabajado. Base = **salario ordinario** del momento del disfrute (**sin recargos, sin horas extras**). Empleador fija fecha avisando con **15 días de antelación** (CST art. 187). Compensación en dinero solo a la terminación o por la mitad durante vigencia (CST art. 189). Fórmula proporcional al retiro: `(salario / 720) × días trabajados`.",
        "**Sanción por mora — Ley 50/1990 art. 99 num. 3 (cesantías):** **un día de salario por cada día de retardo** en la consignación, hasta consignación efectiva. **No procede automáticamente** — debe solicitarla el trabajador por demanda. Para prima y vacaciones la sanción es el **art. 65 CST** (indemnización moratoria al despido).",
        "**Base salarial común (CST art. 99 y doctrina):** si hubo variaciones > 10 % en los últimos 3 meses, promediar los 12 meses anteriores. **Incluye auxilio de transporte** en cesantías y prima. **Excluye pagos no salariales** pactados conforme art. 128 CST. Las vacaciones se calculan solo sobre salario ordinario, sin recargos.",
        "**Deducibilidad fiscal de las prestaciones (art. 108 ET):** son deducibles en renta siempre que se hayan pagado los aportes a seguridad social y parafiscales sobre la base correcta. La retención por salarios sobre devengado total (incluida prima) se calcula bajo **art. 383 + art. 387 ET — depuración del art. 388 ET** (incluye prima como ingreso laboral del mes de pago).",
    ),
    keywords=(
        "cesantías", "cesantias",
        "intereses cesantías", "intereses cesantias",
        "prima", "prima de servicios", "prima legal",
        "vacaciones",
        "ley 50 de 1990", "ley 50/1990",
        "ley 1788 de 2016", "ley 1788/2016",
        "decreto 116 de 1976", "decreto 116/1976",
        "ley 52 de 1975",
        "ley 1071 de 2006",
        "art. 249", "art 249", "art. 250", "art 250",
        "art. 306", "art 306",
        "art. 186", "art 186", "art. 187", "art 187", "art. 189", "art 189",
        "art. 65 cst", "art 65 cst",
        "art. 99 cst", "art 99 cst",
        "art. 108", "art 108",
        "art. 387", "art 387",
        "art. 388", "art 388",
        "auxilio de transporte",
        "consignación", "consignacion",
        "15 de febrero",
        "31 de enero",
        "30 de junio", "20 de diciembre",
        "fondo de cesantías", "fondo de cesantias",
        "porvenir", "protección", "proteccion", "colfondos", "skandia",
        "fondo nacional del ahorro",
        "salario base",
        "doméstico", "domestico",
        "15 días hábiles", "15 dias habiles",
        "12% anual", "12 % anual",
        "doble", "duplicación", "duplicacion",
        "indemnización moratoria", "indemnizacion moratoria",
    ),
    anchor_articles=("108", "387"),
    search_queries=(
        "cesantias ley 50 de 1990 fondo consignacion 15 de febrero auxilio transporte",
        "prima de servicios cst art 306 ley 1788 de 2016 base auxilio transporte",
        "vacaciones cst arts 186 a 197 15 dias habiles salario ordinario",
    ),
    source_label="prestaciones_sociales_anchor",
)
