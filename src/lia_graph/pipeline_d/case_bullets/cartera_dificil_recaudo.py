"""v16 (2026-05-14) — provisión y castigo de cartera (arts. 145 y 146 ET).

Bullet content grounded in:
  * docs/expert_briefs/incoming/playbook_renta_cartera_dificil_recaudo.md
  * knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/playbook_renta_cartera_dificil_recaudo.md
"""
from __future__ import annotations

from ..case_detectors import is_cartera_dificil_recaudo_case
from ._registry import CaseSpec


SPEC = CaseSpec(
    name="cartera_dificil_recaudo",
    detector=is_cartera_dificil_recaudo_case,
    bullets=(
        "El **art. 145 ET** permite deducir la provisión de cartera de difícil cobro; el **art. 146 ET** permite el **castigo** de cartera realmente perdida. Son dos vías distintas — provisión cubre cartera vencida con riesgo, castigo cubre deuda manifiestamente perdida o sin valor.",
        "**Cartera elegible (art. 145 par. 1 ET):** créditos del giro ordinario, no vinculados económicamente con el deudor. Quedan **excluidas:** cartera con socios/accionistas/vinculados; cartera ya castigada; cartera con entidades públicas (reglas especiales).",
        "**Método individual basado en antigüedad** (práctica del gremio bajo DUR 1625/2016): **33%** al primer año vencido, **67%** al segundo, **100%** a partir del tercero. Cada cartera se evalúa con análisis documentado por cuenta. La redacción reglamentaria vigente debe verificarse en el DUR 1625/2016 antes de aplicar tasa puntual.",
        "**Castigo (art. 146 ET):** procedente cuando la deuda esté **manifiestamente perdida** o sin valor. Requisitos acumulativos: (1) descargo contable como pérdida real, (2) causalidad con la actividad productora de renta, (3) gestiones documentadas de cobro (extrajudicial y/o judicial) o evidencia de imposibilidad (quiebra, liquidación, fallecimiento sin patrimonio, prescripción). **No exige siempre demanda judicial.**",
        "**Diferencia NIIF vs fiscal:** el deterioro NIIF (pérdida crediticia esperada — NIIF 9 / sección 11 PYME) suele exceder la provisión fiscal. Lo que exceda el límite fiscal es **diferencia temporaria** (se revierte al castigar) y se gestiona en F2516.",
        "**Soportes para el castigo:** acta del órgano de administración aprobando el castigo, listado detallado (deudor, NIT, valor, antigüedad, gestiones), soportes de cobro (cartas, correos, demandas, acuerdos incumplidos), evidencia de imposibilidad de cobro.",
        "**Recuperación posterior:** si una cartera previamente provisionada o castigada se recupera, opera como **renta líquida por recuperación de deducciones** (art. 195 ET) en el AG de la recuperación.",
    ),
    keywords=(
        "cartera", "carteras",
        "difícil", "dificil", "difícil recaudo", "dificil recaudo",
        "incobrable", "incobrables",
        "vencida",
        "provisión", "provision", "provisionar",
        "castigo", "castigar", "castigada",
        "deuda", "deudas",
        "145", "146", "195",
        "33%", "67%", "100%",
        "dur 1625",
        "antigüedad", "antiguedad",
        "deterioro",
        "niif 9", "niif 11",
        "manifiestamente perdida", "manifiestamente perdidas",
        "acta",
        "gestiones de cobro",
        "demanda", "judicial",
        "quiebra", "liquidación", "liquidacion",
        "prescripción", "prescripcion",
        "deducir", "deducible", "deducción", "deduccion",
        "renglón", "renglon",
        "2516", "f2516",
        "diferencia temporaria",
    ),
    anchor_articles=("145", "146"),
    search_queries=(
        "provision cartera dificil recaudo art 145 castigo deudas perdidas art 146 et",
        "33 67 100 antiguedad provision cartera individual dur 1625 2016",
    ),
    source_label="cartera_dificil_recaudo_anchor",
)
