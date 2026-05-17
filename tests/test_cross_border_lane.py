"""fix_v25_may.md §3.2 — Phase 2 / G9 tests."""

from __future__ import annotations

from lia_graph.pipeline_d.cross_border_lane import (
    canonical_articles_for,
    cross_border_directive,
    detect_cross_border_context,
)


def test_detects_cloud_software_abroad():
    hint = detect_cross_border_context(
        "Una SAS colombiana paga una suscripción anual de software en la nube a un "
        "proveedor sin domicilio en Colombia."
    )
    assert hint.detected
    assert hint.kind == "cloud_software"


def test_detects_services_from_abroad():
    hint = detect_cross_border_context(
        "Pagamos servicios prestados desde el exterior por un proveedor en España."
    )
    assert hint.detected
    assert hint.kind == "services_from_abroad"


def test_detects_nonresident_dividend():
    hint = detect_cross_border_context(
        "La SAS va a decretar dividendos a un socio no residente con cédula extranjera."
    )
    assert hint.detected
    assert hint.kind == "nonresident_dividend"


def test_detects_royalty():
    hint = detect_cross_border_context("Pagamos regalías por una licencia de software a EE.UU.")
    assert hint.detected
    assert hint.kind == "royalty"


def test_domestic_question_is_not_detected():
    hint = detect_cross_border_context(
        "Cómo determino la retención en la fuente por honorarios a una persona natural colombiana."
    )
    assert not hint.detected


def test_canonical_articles_for_cloud_software():
    hint = detect_cross_border_context(
        "suscripción de software en la nube a proveedor sin domicilio en Colombia"
    )
    arts = canonical_articles_for(hint)
    keys = [k for k, _ in arts]
    assert "et.art.437-2" in keys
    assert "et.art.420.par.3" in keys
    assert "et.art.408" in keys


def test_directive_empty_when_not_detected():
    hint = detect_cross_border_context("Cómo liquido la prima de servicios")
    assert cross_border_directive(hint) == ""


def test_directive_lists_cdi_review():
    hint = detect_cross_border_context(
        "Servicios desde el exterior con un proveedor sin domicilio"
    )
    block = cross_border_directive(hint)
    assert "CDI" in block or "Convenio" in block
    assert "art. 437-2" in block.lower()
