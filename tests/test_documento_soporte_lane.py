"""fix_v25_may.md P12 — documento-soporte lane tests."""

from __future__ import annotations

from lia_graph.pipeline_d.documento_soporte_lane import (
    canonical_anchors_for,
    detect_documento_soporte_context,
    documento_soporte_directive,
)


def test_detects_doc_soporte_no_obligado():
    hint = detect_documento_soporte_context(
        "Una SAS compra servicios a una persona natural no obligada a expedir factura. "
        "Qué documento soporte debe generar para que el costo sea deducible?"
    )
    assert hint.detected
    assert len(hint.cues) == 2


def test_does_not_fire_on_generic_fe_question():
    hint = detect_documento_soporte_context(
        "Cómo funciona la factura electrónica de venta en Colombia"
    )
    assert not hint.detected


def test_does_not_fire_on_doc_soporte_alone():
    # If the question mentions doc soporte but no no-obligado context,
    # the lane should NOT fire (could be DSE or another scenario).
    hint = detect_documento_soporte_context(
        "Necesito un documento soporte para mi declaración de renta"
    )
    assert not hint.detected


def test_canonical_anchors_include_771_2_and_167_2021():
    hint = detect_documento_soporte_context(
        "documento soporte para adquisiciones a sujetos no obligados a facturar"
    )
    anchors = canonical_anchors_for(hint)
    keys = [k for k, _ in anchors]
    assert "et.art.771-2" in keys
    assert "res_dian.0167.2021" in keys


def test_directive_warns_against_zona_franca_drift():
    hint = detect_documento_soporte_context(
        "soporte en adquisiciones a no obligados a expedir factura"
    )
    block = documento_soporte_directive(hint)
    assert "zona franca" in block.lower()
    assert "Art. 771-2" in block or "art. 771-2" in block.lower()
    assert "000167" in block
    assert "CUDS" in block


def test_directive_empty_when_not_detected():
    hint = detect_documento_soporte_context("Cómo liquido la prima de servicios")
    assert documento_soporte_directive(hint) == ""
