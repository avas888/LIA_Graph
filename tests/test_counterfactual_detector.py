"""fix_v25_may.md §3.9 — Phase 9 / G16 tests."""

from __future__ import annotations

from lia_graph.pipeline_d.answer_polish_validators_v25 import (
    no_counterfactual_entities,
)
from lia_graph.pipeline_d.counterfactual_detector import (
    detect_counterfactual_entities,
)


def test_flags_invented_person_name():
    findings = detect_counterfactual_entities(
        question="quién es beneficiario final de la SAS",
        evidence_text="",
        polished="Carlos Moreno Pérez es el beneficiario final del 50%.",
    )
    kinds = {f.kind for f in findings}
    assert "person_name" in kinds


def test_allows_institutional_names_like_dian():
    findings = detect_counterfactual_entities(
        question="qué reporta a la DIAN",
        evidence_text="",
        polished="La DIAN exige reportar a través del MUISCA.",
    )
    surfaces = [f.surface for f in findings]
    assert "DIAN" not in surfaces


def test_flags_invented_company_name():
    findings = detect_counterfactual_entities(
        question="cómo aplica la depreciación",
        evidence_text="",
        polished="DISTRIBUIDORA EL SOL SAS aplicó deprecación lineal de 10 años.",
    )
    kinds = {f.kind for f in findings}
    assert "company_name" in kinds


def test_does_not_flag_company_present_in_question():
    findings = detect_counterfactual_entities(
        question="DISTRIBUIDORA EL SOL SAS tuvo ingresos en 2025",
        evidence_text="",
        polished="DISTRIBUIDORA EL SOL SAS debe presentar exógena.",
    )
    surfaces = [f.surface for f in findings]
    assert "DISTRIBUIDORA EL SOL SAS" not in surfaces


def test_flags_large_monetary_fact_absent_from_inputs():
    findings = detect_counterfactual_entities(
        question="patrimonio bruto 18,000 millones operaciones 6,000 millones",
        evidence_text="",
        polished=(
            "El umbral aplicable corresponde a $1.930 millones en Panamá."
        ),
    )
    kinds = {f.kind for f in findings}
    assert "monetary_fact" in kinds


def test_validator_returns_true_for_clean_polished():
    question = "tope ingreso obligados RTE 160,000 UVT"
    polished = "Para RTE el umbral es 160,000 UVT; aplica art. 364-5 ET."
    assert no_counterfactual_entities("", polished, None, question)


def test_validator_returns_false_when_entity_invented():
    question = "RUB beneficiario final"
    polished = "Carlos Moreno Pérez aparece como beneficiario al 30%."
    assert not no_counterfactual_entities("", polished, None, question)
