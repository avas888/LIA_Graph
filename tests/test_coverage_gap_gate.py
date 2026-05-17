"""fix_v25_may.md §3.5 — Phase 5 / G12 tests."""

from __future__ import annotations

from lia_graph.pipeline_d.answer_polish_validators_v25 import no_coverage_gap_phrase


def test_rejects_canonical_cobertura_pendiente_stub():
    polished = (
        "Para la periodicidad IVA aplica el artículo 600 ET.\n"
        "Cobertura pendiente para esta sub-pregunta; valida el expediente "
        "antes de cerrarla con el cliente."
    )
    assert not no_coverage_gap_phrase("", polished, None, None)


def test_rejects_no_encuentro_evidencia_para_stub():
    polished = "No encuentro evidencia para esta sub-pregunta."
    assert not no_coverage_gap_phrase("", polished, None, None)


def test_allows_clean_answer():
    polished = "Para AG 2025 con ingresos > 92,000 UVT, IVA es bimestral (art. 600 ET)."
    assert no_coverage_gap_phrase("", polished, None, None)


def test_allows_legitimate_gap_mention_without_stub_phrase():
    polished = "Recomendamos al contador validar la cifra exacta con la DIAN."
    assert no_coverage_gap_phrase("", polished, None, None)
