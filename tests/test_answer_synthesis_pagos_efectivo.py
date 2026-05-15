"""v16 (2026-05-14) — bancarización / pagos en efectivo (art. 771-5 ET) test."""
from __future__ import annotations

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_synthesis_helpers import is_pagos_efectivo_case
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


def test_detector_matches_bancarizacion() -> None:
    assert is_pagos_efectivo_case(
        "bancarización art. 771-5 porcentaje vigente AG 2025"
    )


def test_detector_matches_pagos_efectivo() -> None:
    assert is_pagos_efectivo_case(
        "¿cuánto puedo pagar en efectivo y que sea deducible?"
    )


def test_detector_matches_efectivo_with_deducible_cue() -> None:
    assert is_pagos_efectivo_case(
        "¿la nómina en efectivo es deducible?"
    )


def test_detector_matches_art_771_5() -> None:
    assert is_pagos_efectivo_case(
        "tope individual art. 771-5 et 100 uvt por transacción"
    )


def test_detector_ignores_gmf_query() -> None:
    assert not is_pagos_efectivo_case(
        "¿el gmf 4x1000 es deducible en la depuración?"
    )


def test_detector_ignores_isolated_efectivo_token() -> None:
    # The bare word "efectivo" without a deducible cue should NOT
    # fire — it's commonly an adverb in unrelated contexts.
    assert not is_pagos_efectivo_case(
        "¿la sociedad realiza efectivo control sobre el proveedor?"
    )


def test_build_recommendations_emits_bancarizacion_bullets() -> None:
    out = build_recommendations(
        request=_req(
            "¿cuánto puedo pagar en efectivo y deducir en renta AG 2025 bajo el"
            " art. 771-5 ET, y cuál es el tope individual por transacción?"
        ),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "art. 771-5" in joined
    assert "35%" in joined or "35 %" in joined
    assert "40%" in joined or "40 %" in joined
    assert "100 uvt" in joined
    assert "ley 2277" in joined  # gradualidad
    assert "f2516" in joined or "2516" in joined
    assert "diferencia permanente" in joined


def test_pagos_efectivo_isolates_from_gmf_and_ica() -> None:
    out = build_recommendations(
        request=_req(
            "¿cuál es el tope de pagos en efectivo deducibles?"
        ),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "50% del gmf" not in joined
    assert "4×1000" not in joined and "4x1000" not in joined


def test_pagos_efectivo_q2_no_longer_cobertura_pendiente() -> None:
    from lia_graph.pipeline_d.answer_policy import DIRECT_ANSWER_COVERAGE_PENDING

    q1 = (
        "¿Cuánto puedo pagar en efectivo y que sea deducible en renta AG 2025"
        " bajo el art. 771-5?"
    )
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
