"""fix_v25_may.md §3.3 — Phase 3 / G10 tests."""

from __future__ import annotations

from lia_graph.pipeline_d.municipal_tax_routing import (
    detect_municipal_context,
    municipal_directive,
    municipal_pointer_block,
)


def test_detects_bogota_ica_territoriality():
    hint = detect_municipal_context(
        "Una SAS de Bogotá presta servicios de consultoría a un cliente ubicado en "
        "Medellín, pero el trabajo se ejecuta desde Bogotá. ¿Cómo determino si el "
        "ingreso está gravado con ICA en Bogotá y si aplica reteICA?"
    )
    assert hint.detected
    assert hint.city == "Bogotá"
    assert hint.has_reteica


def test_detects_medellin_ica():
    hint = detect_municipal_context(
        "Cómo se aplica el ICA en Medellín para una empresa que factura desde allí"
    )
    assert hint.detected
    assert hint.city == "Medellín"


def test_does_not_detect_when_no_ica_or_reteica_mentioned():
    hint = detect_municipal_context(
        "La sucursal está en Bogotá y declara renta en formulario 110."
    )
    assert not hint.detected


def test_pointer_block_lists_bogota_norms():
    hint = detect_municipal_context("ICA en Bogotá territorialidad reteICA")
    block = municipal_pointer_block(hint)
    assert "Acuerdo Distrital 65 de 2002" in block
    assert "Decreto Distrital 352 de 2002" in block


def test_directive_warns_against_national_articles():
    hint = detect_municipal_context("reteICA en Bogotá")
    block = municipal_directive(hint)
    assert "Estatuto Tributario" in block
    assert "municipal" in block.lower()


def test_pointer_empty_when_not_detected():
    hint = detect_municipal_context("retención fuente honorarios")
    assert municipal_pointer_block(hint) == ""
    assert municipal_directive(hint) == ""
