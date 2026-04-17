from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormativaSectionBlueprint:
    id: str
    title: str
    field_name: str


NORMATIVA_QUERY_SUFFIX = "explicacion normativa, vigencia y aterrizaje contable"
NORMATIVA_PRIMARY_ANCHOR_LIMIT = 3
NORMATIVA_CONNECTED_ANCHOR_LIMIT = 2
NORMATIVA_RELATION_LIMIT = 4
NORMATIVA_SUPPORT_LIMIT = 4

NORMATIVA_SCOPE_SECTION = NormativaSectionBlueprint(
    id="normativa_scope",
    title="Qué mirar en esta norma",
    field_name="applicability_summary",
)
NORMATIVA_PRACTICAL_SECTION = NormativaSectionBlueprint(
    id="normativa_practical",
    title="Qué revisar para aterrizarla",
    field_name="professional_impact",
)
NORMATIVA_RELATIONS_SECTION = NormativaSectionBlueprint(
    id="normativa_relations",
    title="Relaciones útiles detectadas",
    field_name="relations_summary",
)
NORMATIVA_SECTION_BLUEPRINTS = (
    NORMATIVA_SCOPE_SECTION,
    NORMATIVA_PRACTICAL_SECTION,
    NORMATIVA_RELATIONS_SECTION,
)

NORMATIVA_DEFAULT_SECTION_ID = "normativa_default"
NORMATIVA_DEFAULT_SECTION_TITLE = "Lectura inicial"

