"""v16 (2026-05-14) — atenciones (art. 107-1 ET) case-bullet test."""
from __future__ import annotations

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_synthesis_helpers import is_atenciones_case
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


def test_detector_matches_atenciones_clientes() -> None:
    assert is_atenciones_case(
        "¿cuánto puedo deducir en atenciones a clientes en renta?"
    )


def test_detector_matches_canastas_navidenas() -> None:
    assert is_atenciones_case(
        "¿las canastas navideñas a empleados son deducibles?"
    )


def test_detector_matches_art_107_1() -> None:
    assert is_atenciones_case("tope del 1% atenciones art. 107-1 et")


def test_detector_ignores_gmf_query() -> None:
    assert not is_atenciones_case(
        "¿el gmf 4x1000 es deducible en la depuración?"
    )


def test_detector_ignores_depreciacion_query() -> None:
    assert not is_atenciones_case(
        "vida útil fiscal de una camioneta art. 137"
    )


def test_build_recommendations_emits_atenciones_bullets() -> None:
    out = build_recommendations(
        request=_req(
            "¿cuál es el tope deducible por atenciones a clientes y la fiesta"
            " de fin de año en la renta AG 2025?"
        ),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "art. 107-1" in joined
    assert "1%" in joined or "1 %" in joined
    assert "ingresos fiscales netos" in joined
    assert "publicidad" in joined  # diferencia con publicidad
    assert "iva" in joined  # IVA no descontable
    assert "f2516" in joined or "diferencia permanente" in joined


def test_atenciones_isolates_from_gmf() -> None:
    out = build_recommendations(
        request=_req(
            "¿la fiesta de fin de año para empleados es deducible?"
        ),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "50% del gmf" not in joined
    assert "4×1000" not in joined and "4x1000" not in joined


def test_atenciones_topic_content_reaches_direct_answers() -> None:
    """Layer-A acceptance: substantive bullets reach build_direct_answers'
    output. See depreciación test for the matcher-vs-architecture
    rationale.
    """
    q1 = "¿Cuánto puedo deducir en regalos y atenciones a clientes en renta AG 2025?"
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
    assert "art. 107-1" in flat
    assert "1%" in flat or "1 %" in flat
