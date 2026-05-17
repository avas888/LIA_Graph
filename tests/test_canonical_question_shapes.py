"""fix_v22_may §9c P2-T-Orphan — canonical question shape matcher.

Revived from the orphan ``fix_v7-truncated-tail-and-canonical-shapes``
branch (HEAD ``4b953ca``, 2026-04-30). Locks:

  1. The seed shape ``plazos_renta_personas_juridicas`` matches a plain
     "fechas límite para presentar renta por NIT" question when the
     classifier already routed to ``declaracion_renta``.
  2. A topic mismatch suppresses the match (the canonical match is a
     *confidence boost* on the classifier, not an override).
  3. Empty input returns None (defensive).
"""

from __future__ import annotations

from lia_graph.canonical_question_shapes import (
    load_canonical_shapes,
    match_canonical_shape,
)


def test_seed_shape_loads_from_json_config() -> None:
    shapes = load_canonical_shapes()
    assert len(shapes) >= 1
    ids = {s.id for s in shapes}
    assert "plazos_renta_personas_juridicas" in ids


def test_match_plazos_renta_question_routed_to_declaracion_renta() -> None:
    msg = "¿Cuáles son las fechas límite para presentar renta por NIT?"
    shape = match_canonical_shape(msg, classified_topic="declaracion_renta")
    assert shape is not None
    assert shape.id == "plazos_renta_personas_juridicas"
    assert shape.evidence_shape_override.get("query_mode") == "tabular_reference"


def test_topic_mismatch_suppresses_match() -> None:
    msg = "¿Cuáles son las fechas límite para presentar renta por NIT?"
    shape = match_canonical_shape(msg, classified_topic="laboral")
    assert shape is None


def test_empty_input_returns_none() -> None:
    assert match_canonical_shape("") is None
    assert match_canonical_shape("   ") is None
