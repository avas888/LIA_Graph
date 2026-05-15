"""v16 (2026-05-14) — depreciación fiscal (art. 137 ET).

Bullet content grounded in:
  * docs/expert_briefs/incoming/playbook_renta_depreciacion_fiscal.md
  * knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/playbook_renta_depreciacion_fiscal.md
"""
from __future__ import annotations

from ..case_detectors import is_depreciacion_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="depreciacion",
    detector=is_depreciacion_case,
    bullets=(
        "El art. 137 ET fija **tasas máximas anuales de depreciación fiscal** por categoría de activo. La tasa contable NIIF puede ser menor; la fiscal funciona como techo. Algunas tasas clave: construcciones y edificaciones **2,22%** (45 años); maquinaria, equipo de transporte terrestre, muebles y enseres, equipo médico **10%** (10 años); equipo de computación, redes y equipo de comunicación **20%** (5 años).",
        "**Base de cálculo (art. 131 ET):** costo fiscal del activo (precio de adquisición + costos directos atribuibles para ponerlo en condiciones de uso). Si el activo es inmueble, **excluye el terreno** — el terreno no se deprecia (art. 135 ET). Separa contable y fiscalmente terreno (no depreciable) y construcción (depreciable a 2,22% anual).",
        "**Techo NIIF vs fiscal:** si la depreciación contable NIIF es menor que la tasa fiscal del art. 137, prevalece la NIIF — la deducción fiscal no puede exceder la depreciación realmente registrada en contabilidad (art. 131 ET). Si la fiscal es menor que la NIIF, el exceso contable no es deducible.",
        "**Método (art. 134 ET):** línea recta es el default; reducción de saldos y otros métodos técnicamente aceptados son válidos siempre que sean consistentes año tras año. Cambio de método requiere justificación técnica documentada.",
        "**Conciliación F2516:** registra la diferencia entre depreciación contable y fiscal como diferencia temporaria (genera impuesto diferido). Mantén papel de trabajo por activo con costo fiscal, tasa aplicada, depreciación del AG y acumulada.",
        "**Activos menores a 50 UVT** ($2.353.250 con UVT 2025 = $47.065): la práctica aceptada por DIAN es llevarlos al gasto en el año de adquisición. Revisa política contable y consistencia.",
        "**Soporte documental obligatorio:** factura de adquisición, contrato, registro contable, ficha técnica del activo, cálculo de depreciación anual. Sin soporte la depreciación es objetable en revisión DIAN.",
    ),
    keywords=(
        "depreciación", "depreciacion", "depreciar", "deprecio", "deprecia",
        "137", "131", "134", "135", "138", "290",
        "tasa", "tasas",
        "vida útil", "vida util",
        "línea recta", "linea recta", "reducción de saldos", "reduccion de saldos",
        "construcción", "construccion", "edificación", "edificacion",
        "maquinaria", "equipo", "equipos",
        "computación", "computacion", "computador", "computadores",
        "vehículo", "vehiculo", "camioneta",
        "activo", "activos", "activo fijo", "activos fijos",
        "costo fiscal",
        "terreno",
        "niif", "nic 16",
        "2516", "2517", "conciliación fiscal", "conciliacion fiscal",
        "diferencia temporaria",
        "deducir", "deducible", "deducción", "deduccion",
        "renglón", "renglon",
    ),
    anchor_articles=("137",),
    search_queries=(
        "depreciacion fiscal tasa maxima art 137 et vida util activos",
        "depreciacion contable niif vs fiscal techo art 131 art 134 et",
    ),
    source_label="depreciacion_anchor",
)
