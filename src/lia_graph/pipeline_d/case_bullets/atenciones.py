"""v16 (2026-05-14) — atenciones a clientes/proveedores/empleados (art. 107-1 ET).

Bullet content grounded in:
  * docs/expert_briefs/incoming/playbook_renta_atenciones_clientes_empleados.md
  * knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/playbook_renta_atenciones_clientes_empleados.md
"""
from __future__ import annotations

from ..case_detectors import is_atenciones_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="atenciones",
    detector=is_atenciones_case,
    bullets=(
        "El art. 107-1 ET limita la deducción de **atenciones a clientes, proveedores y empleados** (regalos, cortesías, fiestas, reuniones y festejos) al **1% de los ingresos fiscales netos efectivamente realizados** del año gravable. Lo que excede no es deducible y genera diferencia permanente en F2516.",
        "**Base del 1%:** ingresos fiscales netos = ingresos brutos fiscales − devoluciones, rebajas y descuentos. No se calcula sobre ingresos contables NIIF si difieren de los fiscales. Ejemplo: PYME con ingresos fiscales netos de $2.000M tiene tope de atenciones deducibles de **$20M**.",
        "**Qué cae en el tope:** cenas y almuerzos con clientes, eventos corporativos, canastas navideñas, regalos institucionales, fiesta de fin de año, aguinaldos. **Qué NO entra (va por otra cuenta):** publicidad y propaganda a mercado abierto (deducción ordinaria art. 107 ET sin tope), capacitaciones a empleados con causalidad, pagos laborales constitutivos de salario.",
        "**Requisitos de procedencia (art. 107 + 107-1 ET):** causalidad con la actividad productora de renta, necesidad y proporcionalidad, factura electrónica (art. 771-2 ET), pago bancarizado (art. 771-5 ET) y retención en la fuente cuando aplique.",
        "**IVA descontable:** el IVA pagado en atenciones **no es descontable** porque el gasto subyacente no está destinado a operaciones gravadas con derecho a descuento bajo art. 488 ET.",
        "**Tratamiento en F2516:** registra el 100% del gasto contable. El exceso sobre el 1% se ajusta como **diferencia permanente** — no genera impuesto diferido.",
        "**Soporte obligatorio:** factura electrónica con identificación del beneficiario o evento, listado de asistentes cuando sea grupal, acta o memo interno justificando la atención, pago bancarizado.",
    ),
    keywords=(
        "atención", "atencion", "atenciones",
        "107-1",
        "regalos", "regalo",
        "fiesta", "fiestas", "festejo", "festejos",
        "canastas", "canasta navideña", "canasta navidena",
        "aguinaldo", "aguinaldos",
        "cortesía", "cortesia", "cortesías", "cortesias",
        "evento corporativo", "eventos corporativos",
        "cliente", "clientes", "proveedor", "proveedores", "empleado", "empleados",
        "1%", "1 %", "tope", "límite", "limite",
        "ingresos fiscales", "ingresos netos",
        "publicidad", "propaganda",
        "deducir", "deducible", "deducción", "deduccion",
        "depuración", "depuracion",
        "renglón", "renglon",
        "iva descontable",
        "f2516", "2516",
        "diferencia permanente",
        "causa", "causalidad",
    ),
    anchor_articles=("107-1",),
    search_queries=(
        "deduccion por atenciones clientes proveedores empleados 1% art 107-1 et",
        "art 107-1 et regalos fiestas cortesias tope ingresos fiscales netos",
    ),
    source_label="atenciones_anchor",
)
