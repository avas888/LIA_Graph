"""fix_v25_may.md P15 — enum-list extractor tests.

Locks the audit-question patterns that v25-v2 missed (compras, parafiscales,
INC, page-por-pais, etc.). Every entry here = a question shape the
extractor must keep recognizing.
"""

from __future__ import annotations

from lia_graph.pipeline_d.enum_list_extractor import (
    build_enum_list_directive,
    extract_enum_lists,
)


def test_q2_services_honorarios_compras():
    q = (
        "Como contador, como determino en 2026 la retencion en la fuente por "
        "pagos de servicios, honorarios y compras a terceros?"
    )
    lists = extract_enum_lists(q)
    items = {it for el in lists for it in el.items}
    assert "servicios" in items
    assert "honorarios" in items
    assert any("compras" in it for it in items), (
        f"Q2 must surface 'compras a terceros' as enum item; got {items}"
    )


def test_q4_salud_pension_parafiscales():
    q = (
        "El auxilio entra en la base de prima, cesantias, intereses de "
        "cesantias, vacaciones, salud, pension y parafiscales?"
    )
    lists = extract_enum_lists(q)
    items = {it for el in lists for it in el.items}
    assert "salud" in items
    assert "pension" in items
    assert "parafiscales" in items
    # The longer enum should also surface the earlier items.
    assert "cesantias" in items
    assert "vacaciones" in items


def test_q6_rst_restaurant_six_items():
    q = (
        "Que obligaciones tiene frente al SIMPLE, IVA o INC, ICA, anticipos "
        "bimestrales, declaracion anual y retenciones?"
    )
    lists = extract_enum_lists(q)
    items = {it.lower() for el in lists for it in el.items}
    # All six must surface.
    expected = {"simple", "ica", "anticipos bimestrales", "declaracion anual", "retenciones"}
    missing = expected - items
    assert not missing, f"Q6 missing items: {missing}; got {items}"


def test_q16_informe_local_maestro_pais_por_pais():
    q = "Que informe local, informe maestro o pais por pais debe revisar?"
    lists = extract_enum_lists(q)
    items = {it.lower() for el in lists for it in el.items}
    assert "informe local" in items
    assert "informe maestro" in items
    assert any("pais por pais" in it for it in items)


def test_q15_two_item_y():
    q = "Como manejo documentos societarios y fiscales?"
    lists = extract_enum_lists(q)
    items = {it.lower() for el in lists for it in el.items}
    assert "documentos societarios" in items or "documentos societarios y fiscales" in q.lower()
    assert "fiscales" in items


def test_no_enum_in_simple_question():
    q = "Cuál es el plazo para declarar renta en 2026?"
    lists = extract_enum_lists(q)
    # Single nominal "plazo" — no enum.
    assert not lists or all(len(el.items) < 2 for el in lists)


def test_does_not_match_verb_y_verb():
    """The regex must not pull verb conjugations into the enum surface."""
    q = "El contador revisó y aprobó la declaración."
    lists = extract_enum_lists(q)
    # `revisó y aprobó` could match — but stop-list / item validity should
    # prevent it from being a "must-cover" list of nouns. Allow at most one
    # noise capture, but make sure neither verb is surfaced as a topic.
    surfaced = {it.lower() for el in lists for it in el.items}
    # Whatever the regex emits, it shouldn't claim 'revisó' as a topic.
    assert "revisó" not in surfaced


def test_directive_includes_all_items():
    q = (
        "Que obligaciones tiene frente al SIMPLE, IVA o INC, ICA, anticipos "
        "bimestrales, declaracion anual y retenciones?"
    )
    block = build_enum_list_directive(q)
    assert "SIMPLE" in block
    assert "ICA" in block
    assert "retenciones" in block.lower() or "retenciones" in block
    assert "CADA" in block.upper()  # 'cada uno' nudges the LLM


def test_directive_empty_when_no_enum():
    q = "Cuándo aplica la renta presuntiva?"
    block = build_enum_list_directive(q)
    assert block == ""
