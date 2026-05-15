"""v16 (2026-05-14) — cartera de difícil recaudo (arts. 145, 146 ET) test."""
from __future__ import annotations

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_synthesis_helpers import (
    is_cartera_dificil_recaudo_case,
)
from lia_graph.pipeline_d.answer_synthesis_sections import (
    build_direct_answers,
    build_recommendations,
)


def _req(message: str) -> PipelineCRequest:
    return PipelineCRequest(
        message=message,
        topic="costos_deducciones_renta",
        requested_topic="costos_deducciones_renta",
    )


def test_detector_matches_provision_cartera() -> None:
    assert is_cartera_dificil_recaudo_case(
        "¿qué porcentaje de cartera puedo provisionar este año?"
    )


def test_detector_matches_cartera_vencida() -> None:
    assert is_cartera_dificil_recaudo_case(
        "cartera vencida más de un año cuánto provisiono fiscalmente"
    )


def test_detector_matches_castigo_cartera() -> None:
    assert is_cartera_dificil_recaudo_case(
        "¿cuándo puedo castigar una cartera incobrable?"
    )


def test_detector_matches_arts_145_146() -> None:
    assert is_cartera_dificil_recaudo_case(
        "deducción de deudas de difícil cobro art. 145 et"
    )


def test_detector_ignores_unrelated_query() -> None:
    assert not is_cartera_dificil_recaudo_case(
        "¿el gmf 4x1000 es deducible?"
    )


def test_build_recommendations_emits_cartera_bullets() -> None:
    out = build_recommendations(
        request=_req(
            "¿qué porcentaje puedo provisionar de la cartera vencida más de un"
            " año y cuándo puedo castigar una cuenta incobrable en renta AG"
            " 2025?"
        ),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "art. 145" in joined
    assert "art. 146" in joined
    assert "33%" in joined or "100%" in joined
    assert "castigo" in joined or "castigar" in joined
    assert "soportes" in joined or "acta" in joined
    assert "art. 195" in joined  # recuperación


def test_cartera_isolates_from_other_cases() -> None:
    out = build_recommendations(
        request=_req(
            "¿cuándo castigo una cartera de difícil cobro?"
        ),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "50% del gmf" not in joined
    assert "4×1000" not in joined and "4x1000" not in joined


def test_cartera_topic_content_reaches_direct_answers() -> None:
    """Layer-A acceptance: substantive bullets reach build_direct_answers'
    output. See depreciación test for the matcher-vs-architecture
    rationale.
    """
    q1 = "¿Qué porcentaje puedo provisionar de la cartera de difícil cobro en renta AG 2025?"
    q2 = (
        "¿Qué porcentaje es deducible, en qué norma se fundamenta, y cómo"
        " debe registrarse en la depuración?"
    )
    recs = build_recommendations(
        request=_req(f"{q1} {q2}"),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    direct = build_direct_answers(
        sub_questions=(q1, q2),
        recommendations=recs,
        procedure=(),
        paperwork=(),
        precautions=(),
        context_lines=(),
        opportunities=(),
    )
    flat = "\n".join(line for _, lines in direct for line in lines).lower()
    assert "art. 145" in flat or "art. 146" in flat
    assert "castigo" in flat or "castigar" in flat or "provis" in flat
