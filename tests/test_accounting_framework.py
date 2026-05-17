"""fix_v25_may.md §3.4 — Phase 4 / G11 tests."""

from __future__ import annotations

from lia_graph.pipeline_d.accounting_framework import (
    detect_framework_hint,
    framework_directive,
)
from lia_graph.pipeline_d.answer_polish_validators_v25 import framework_coherence


def test_detects_niif_pymes():
    hint = detect_framework_hint(
        "Una pyme colombiana toma en arriendo una máquina por 36 meses; bajo NIIF "
        "para Pymes, cómo se contabiliza?"
    )
    assert hint.framework == "niif_pymes"


def test_detects_niif_plenas():
    hint = detect_framework_hint(
        "Bajo NIIF Plenas / IFRS 16 cómo contabilizo un arrendamiento"
    )
    assert hint.framework == "niif_plenas"


def test_detects_decreto_2649():
    hint = detect_framework_hint("Aplica el Decreto 2649 para esta entidad")
    assert hint.framework == "decreto_2649_2706"


def test_no_framework_for_generic_question():
    hint = detect_framework_hint("Cómo liquido la prima de servicios")
    assert hint.framework == "none"


def test_directive_for_pymes_warns_against_niif16():
    block = framework_directive(detect_framework_hint("bajo NIIF para Pymes"))
    assert "NIIF 16" in block
    assert "Sección 20" in block


def test_directive_empty_when_framework_none():
    assert framework_directive(detect_framework_hint("liquidación nómina")) == ""


def test_validator_rejects_niif16_in_pymes_question():
    question = "Bajo NIIF para Pymes cómo contabilizo un leasing"
    bad = "Bajo NIIF 16 reconocemos un derecho de uso..."
    assert not framework_coherence("", bad, evidence=None, question=question)


def test_validator_allows_niif16_in_plenas_question():
    question = "Bajo NIIF Plenas cómo contabilizo el leasing"
    polished = "Bajo NIIF 16 reconocemos un derecho de uso..."
    assert framework_coherence("", polished, evidence=None, question=question)


def test_validator_allows_seccion_20_answer_for_pymes():
    question = "Bajo NIIF para Pymes el arrendamiento"
    polished = "Bajo la Sección 20 clasificamos como financiero u operativo."
    assert framework_coherence("", polished, evidence=None, question=question)
