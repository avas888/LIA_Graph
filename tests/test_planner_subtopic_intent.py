"""Phase 6 planner tests — lexical subtopic intent detection."""

from __future__ import annotations

import pytest

from lia_graph.pipeline_d import planner_query_modes as pqm
from lia_graph.subtopic_taxonomy_loader import SubtopicEntry, SubtopicTaxonomy


def _tax() -> SubtopicTaxonomy:
    entries_laboral = (
        SubtopicEntry(
            parent_topic="laboral",
            key="aporte_parafiscales_icbf",
            label="Aporte Parafiscales ICBF",
            aliases=("aporte_icbf", "parafiscales_icbf"),
            evidence_count=9,
            curated_at="2026-04-21T00:00:00Z",
            curator="test",
        ),
        SubtopicEntry(
            parent_topic="laboral",
            key="nomina_electronica",
            label="Nómina electrónica",
            aliases=("pago_nomina_electronica",),
            evidence_count=4,
            curated_at="2026-04-21T00:00:00Z",
            curator="test",
        ),
    )
    entries_iva = (
        SubtopicEntry(
            parent_topic="iva",
            key="factura_titulo_valor",
            label="Factura título valor",
            aliases=("factura_como_titulo_valor",),
            evidence_count=5,
            curated_at="2026-04-21T00:00:00Z",
            curator="test",
        ),
    )
    entries_retencion = (
        SubtopicEntry(
            parent_topic="retencion",
            key="aporte_parafiscales_icbf",  # collision — different parent
            label="Versión retención ICBF",
            aliases=("icbf",),
            evidence_count=2,
            curated_at="2026-04-21T00:00:00Z",
            curator="test",
        ),
    )
    by_parent = {
        "laboral": entries_laboral,
        "iva": entries_iva,
        "retencion": entries_retencion,
        "empty_topic": (),
    }
    by_key: dict = {}
    by_alias: dict = {}
    for parent, entries in by_parent.items():
        for entry in entries:
            by_key[(parent, entry.key)] = entry
            for form in entry.all_surface_forms():
                by_alias.setdefault(pqm._normalize_alias(form), entry)
    return SubtopicTaxonomy(
        version="test",
        generated_from="test",
        generated_at="2026-04-21T00:00:00Z",
        subtopics_by_parent=by_parent,
        lookup_by_key=by_key,
        lookup_by_alias=by_alias,
    )


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    pqm._SUBTOPIC_INTENT_CACHE.clear()


def test_parafiscales_query_resolves_laboral_intent() -> None:
    tax = _tax()
    result = pqm._detect_sub_topic_intent(
        "cómo liquido parafiscales ICBF en nómina",
        "laboral",
        taxonomy=tax,
    )
    assert result == "aporte_parafiscales_icbf"


def test_alias_only_hit_resolves_via_breadth() -> None:
    """Invariant I1 — aliases, not just key/label, match."""
    tax = _tax()
    result = pqm._detect_sub_topic_intent(
        "pago de nomina electronica",
        "laboral",
        taxonomy=tax,
    )
    assert result == "nomina_electronica"


def test_generic_query_yields_no_intent() -> None:
    tax = _tax()
    result = pqm._detect_sub_topic_intent(
        "cuéntame sobre impuestos en general",
        "laboral",
        taxonomy=tax,
    )
    assert result is None


def test_alias_from_different_parent_is_not_matched() -> None:
    """A query under topic=iva must not resolve to a laboral-only subtopic."""
    tax = _tax()
    result = pqm._detect_sub_topic_intent(
        "pago de nomina electronica",
        "iva",  # nomina_electronica is under laboral
        taxonomy=tax,
    )
    assert result is None


def test_longest_alias_wins_tie() -> None:
    tax = _tax()
    # "aporte_parafiscales_icbf" (22 chars) beats "icbf" (4 chars).
    result = pqm._detect_sub_topic_intent(
        "aporte parafiscales icbf obligatorio",
        "laboral",
        taxonomy=tax,
    )
    assert result == "aporte_parafiscales_icbf"


def test_parent_with_no_subtopics_returns_none() -> None:
    tax = _tax()
    result = pqm._detect_sub_topic_intent(
        "cualquier texto",
        "empty_topic",
        taxonomy=tax,
    )
    assert result is None


def test_empty_query_returns_none() -> None:
    tax = _tax()
    assert pqm._detect_sub_topic_intent("", "laboral", taxonomy=tax) is None


def test_none_topic_returns_none() -> None:
    tax = _tax()
    assert pqm._detect_sub_topic_intent("parafiscales", None, taxonomy=tax) is None
