"""v16 (2026-05-14) — donaciones a ESAL/RTE (arts. 125 y 257 ET).

Bullet content grounded in:
  * docs/expert_briefs/incoming/playbook_renta_donaciones_deducibles.md
  * knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/playbook_renta_donaciones_deducibles.md
"""
from __future__ import annotations

from ..case_detectors import is_donaciones_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="donaciones",
    detector=is_donaciones_case,
    bullets=(
        "**Regla general post Ley 1819/2016:** las donaciones dejaron de ser deducción y pasaron a ser **descuento tributario del 25% del valor donado** (art. 257 ET). El art. 125 ET conserva tratamiento de deducción solo para casos puntuales (red de bibliotecas públicas y Biblioteca Nacional). Confirma siempre que el contribuyente esté usando el vehículo correcto.",
        "**Tratamiento general — descuento art. 257 ET:** descuento del **25%** del valor donado contra el impuesto sobre la renta a cargo. Sujeto al **límite del art. 258 ET** (la suma de descuentos del año no puede exceder el 25% del impuesto neto de renta). **No es deducción** — el 100% de la donación no rebaja la renta líquida; solo el 25% rebaja el impuesto.",
        "**Entidades elegibles (art. 125-1 + 257 ET):** ESAL pertenecientes al **Régimen Tributario Especial (RTE)** (art. 19 ET) calificadas o readmitidas por DIAN, o entidades no contribuyentes señaladas en arts. 22 y 23 ET. Donación a entidad no calificada en RTE = **sin beneficio fiscal** (art. 125-5 ET).",
        "**Requisitos formales (art. 125-3 ET):** certificado emitido por el revisor fiscal o contador de la entidad receptora (identificación del donante, fecha, valor, destinación, manifestación de reconocimiento efectivo) + soporte del pago bancarizado + acreditación de calificación RTE de la receptora al momento de la donación.",
        "**Modalidades válidas (art. 125-2 ET):** dinero en efectivo con pago bancarizado obligatorio; bienes muebles o inmuebles a costo fiscal del bien al momento de donar; títulos valores a precio de mercado o costo fiscal según aplique.",
        "**Tratamiento contable + fiscal:** registra la donación como gasto contable del 100%. **Renta líquida:** el 100% se ajusta como **no deducible** en F2516 (diferencia permanente). **Impuesto:** descuenta el **25%** del valor donado en el renglón 'descuentos tributarios' del formulario 110/210, sujeto al límite del art. 258 ET.",
        "**Error crítico (riesgo ALTO):** doble beneficio — deducir el 100% + descontar el 25%. **Solo aplica el descuento**; el gasto contable es no deducible. Otro error frecuente: descontar el 100% en vez del 25%.",
    ),
    keywords=(
        "donación", "donacion", "donaciones", "donar", "donado", "donante",
        "125", "125-1", "125-2", "125-3", "125-4", "125-5",
        "257", "258", "256",
        "descuento tributario", "descuentos tributarios",
        "25%", "25 %",
        "esal",
        "régimen tributario especial", "regimen tributario especial", "rte",
        "ánimo de lucro", "animo de lucro",
        "sin ánimo", "sin animo",
        "fundación", "fundacion", "fundaciones",
        "iglesia", "iglesias",
        "biblioteca", "biblioteca nacional", "bibliotecas",
        "deducir", "deducible", "deducción", "deduccion",
        "depuración", "depuracion",
        "renglón", "renglon",
        "certificado",
        "revisor fiscal",
        "bancarizado", "bancarización", "bancarizacion",
        "f2516", "2516",
        "diferencia permanente",
    ),
    anchor_articles=("257", "125"),
    search_queries=(
        "donaciones descuento tributario 25% art 257 et esal rte",
        "donaciones art 125 125-1 125-2 125-3 deducciones deducibles requisitos",
    ),
    source_label="donaciones_anchor",
)
