"""v16 (2026-05-14) — donaciones (arts. 125 / 257 ET) test."""
from __future__ import annotations

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_synthesis_helpers import is_donaciones_case
from lia_graph.pipeline_d.answer_synthesis_sections import (
    build_direct_answers,
    build_recommendations,
)


def _req(message: str) -> PipelineCRequest:
    return PipelineCRequest(
        message=message,
        topic="descuentos_tributarios_renta",
        requested_topic="descuentos_tributarios_renta",
    )


def test_detector_matches_donacion_fundacion() -> None:
    assert is_donaciones_case(
        "¿las donaciones a fundaciones son deducibles?"
    )


def test_detector_matches_esal_rte() -> None:
    assert is_donaciones_case(
        "donación a una esal en el régimen tributario especial"
    )


def test_detector_matches_art_257() -> None:
    assert is_donaciones_case("descuento por donaciones art. 257 et")


def test_detector_ignores_gmf_query() -> None:
    assert not is_donaciones_case("¿el gmf 4x1000 es deducible?")


def test_build_recommendations_emits_donaciones_bullets() -> None:
    out = build_recommendations(
        request=_req(
            "¿la donación a una fundación calificada en el RTE da derecho a"
            " deducción o a descuento tributario en renta AG 2025?"
        ),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "art. 257" in joined
    assert "25%" in joined or "25 %" in joined
    assert "rte" in joined or "régimen tributario especial" in joined
    assert "art. 125" in joined or "art. 125-3" in joined
    assert "certificado" in joined  # requisitos formales
    assert "art. 258" in joined  # límite global


def test_donaciones_isolates_from_other_cases() -> None:
    out = build_recommendations(
        request=_req(
            "¿la donación a una iglesia da descuento tributario en renta?"
        ),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "50% del gmf" not in joined
    assert "4×1000" not in joined and "4x1000" not in joined
    assert "predial" not in joined


def test_donaciones_q2_no_longer_cobertura_pendiente() -> None:
    from lia_graph.pipeline_d.answer_policy import DIRECT_ANSWER_COVERAGE_PENDING

    q1 = "¿La donación a una fundación calificada en RTE genera deducción o descuento en renta AG 2025?"
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
    assert direct[1][1] != (DIRECT_ANSWER_COVERAGE_PENDING,)
