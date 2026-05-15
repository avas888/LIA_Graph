"""v15.4 (2026-05-14) — intereses + leasing + primer empleo cases in
`build_recommendations`.

Same pattern as the GMF / ICA / predial cases. Each detector fires on
common synonyms of its topic and emits 5 substantive bullets that carry
the porcentaje + norma + registro tokens needed by Q2-style
sub-questions.

Content groundings:

* **Intereses + subcapitalización**:
  `knowledge_base/.../RENTA/LOGGRO/seccion-09-costos-y-deducciones.md`
  §9.10 (arts. 117 + 118-1 ET); `T-A-tasa-minima-tributacion-TTD-fuentes-secundarias.md`
  (exceso subcap como DPARL).
* **Leasing (art. 127-1 ET)**:
  `seccion-24-planeacion-tributaria-pymes-estrategias-legitimas.md`
  (tabla comparativa compra/financiero/operativo);
  `estados_financieros_niif/seccion-10-PATCH-leasing-financiero-art127-1.md`;
  `seccion-15-descuentos-tributarios.md` (IVA art. 258-1 inciso 3).
* **Primer empleo (art. 108-5 ET)**:
  `T-B-costos-deducciones-fuentes-secundarias.md` (requisitos y error
  más común); `T-F-planeacion-tributaria-legitima-fuentes-secundarias.md`
  (riesgo medio sin certificación MinTrabajo).
"""

from __future__ import annotations

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_synthesis_helpers import (
    is_intereses_deduction_case,
    is_leasing_deduction_case,
    is_primer_empleo_deduction_case,
)
from lia_graph.pipeline_d.answer_synthesis_sections import build_recommendations


def _req(message: str, topic: str = "costos_deducciones_renta") -> PipelineCRequest:
    return PipelineCRequest(
        message=message,
        topic=topic,
        requested_topic=topic,
    )


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------


def test_intereses_detector_matches_subcapitalizacion() -> None:
    assert is_intereses_deduction_case(
        "¿cómo se aplica la regla de subcapitalización del art. 118-1?"
    )


def test_intereses_detector_matches_deduccion_de_intereses() -> None:
    assert is_intereses_deduction_case(
        "deducción de intereses pagados por la PYME en el AG 2025"
    )


def test_intereses_detector_ignores_predial_query() -> None:
    assert not is_intereses_deduction_case(
        "el predial pagado por la oficina es deducible"
    )


def test_leasing_detector_matches_token() -> None:
    assert is_leasing_deduction_case(
        "¿cómo se trata fiscalmente el leasing financiero en renta?"
    )


def test_leasing_detector_matches_article() -> None:
    assert is_leasing_deduction_case(
        "tratamiento del art. 127-1 ET en el cierre fiscal"
    )


def test_leasing_detector_ignores_intereses_query() -> None:
    assert not is_leasing_deduction_case(
        "¿son deducibles los intereses pagados al banco?"
    )


def test_primer_empleo_detector_matches_phrase() -> None:
    assert is_primer_empleo_deduction_case(
        "¿procede la deducción del 120% por primer empleo?"
    )


def test_primer_empleo_detector_matches_article() -> None:
    assert is_primer_empleo_deduction_case(
        "requisitos del art. 108-5 ET para PYMEs"
    )


def test_primer_empleo_detector_ignores_unrelated_salary_query() -> None:
    assert not is_primer_empleo_deduction_case(
        "¿es deducible el salario de un empleado de 35 años?"
    )


# ---------------------------------------------------------------------------
# Intereses case bullets
# ---------------------------------------------------------------------------


def test_intereses_case_emits_subcap_limit_and_exception() -> None:
    out = build_recommendations(
        request=_req(
            "¿son deducibles los intereses pagados por la PYME y cómo aplica"
            " la subcapitalización?"
        ),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    # The 2× patrimonio líquido limit.
    assert "2" in joined  # "dos (2) veces"
    assert "patrimonio líquido" in joined or "patrimonio liquido" in joined
    # Art. 117 (deducción general) + Art. 118-1 (subcap).
    assert "117" in joined
    assert "118-1" in joined
    # Exception for Superfinanciera / cooperativas.
    assert "superintendencia financiera" in joined or "superfinanciera" in joined
    assert "cooperativ" in joined
    # DPARL classification for the exceso.
    assert "dparl" in joined


def test_intereses_case_q2_tokens_present() -> None:
    out = build_recommendations(
        request=_req(
            "¿qué porcentaje de intereses es deducible y cómo se registra en"
            " la depuración?"
        ),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "deducible" in joined or "deducción" in joined or "deduccion" in joined
    assert "art. 118-1" in joined or "art. 117" in joined
    assert "registra" in joined or "registr" in joined


# ---------------------------------------------------------------------------
# Leasing case bullets
# ---------------------------------------------------------------------------


def test_leasing_case_emits_financiero_vs_operativo() -> None:
    out = build_recommendations(
        request=_req(
            "¿cómo se deduce el leasing en renta? ¿qué diferencia hay entre"
            " financiero y operativo?"
        ),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "127-1" in joined
    assert "financiero" in joined
    assert "operativo" in joined
    # Financiero → activa el bien + depreciación + intereses.
    assert "depreciación" in joined or "depreciacion" in joined
    # Operativo → canon como gasto bajo art. 107.
    assert "canon" in joined
    assert "107" in joined


def test_leasing_case_calls_out_niif16_divergence() -> None:
    out = build_recommendations(
        request=_req("tratamiento fiscal del leasing y NIIF 16 en la conciliación"),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "niif 16" in joined
    # F2516/F2517 conciliación reference.
    assert "2516" in joined or "2517" in joined


def test_leasing_case_surfaces_iva_descuento_arrendatario() -> None:
    out = build_recommendations(
        request=_req("leasing financiero y descuento de IVA en activo fijo"),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "258-1" in joined
    assert "arrendatario" in joined


# ---------------------------------------------------------------------------
# Primer empleo case bullets
# ---------------------------------------------------------------------------


def test_primer_empleo_emits_120pct_and_requisitos() -> None:
    out = build_recommendations(
        request=_req("¿procede la deducción del 120% por primer empleo del art. 108-5?"),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "120%" in joined
    assert "108-5" in joined
    # Age window.
    assert "18" in joined and "28" in joined
    # MinTrabajo certificación requirement.
    assert "ministerio del trabajo" in joined
    assert "certificación" in joined or "certificacion" in joined
    # Trabajo contract (not prestación de servicios).
    assert "contrato de trabajo" in joined
    # 3-year window.
    assert "tres" in joined or "3 años" in joined or "3 anos" in joined


def test_primer_empleo_warns_about_missing_certification() -> None:
    """The most common audit failure for art. 108-5 is taking the 120%
    without the MinTrabajo certification. The bullets must surface
    this risk explicitly."""
    out = build_recommendations(
        request=_req("requisitos formales para la deducción del 120% primer empleo"),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "sin" in joined and "certificación" in joined
    # "DIAN rechaza el 20% adicional" or equivalent risk-framing.
    assert "rechaz" in joined or "riesgo" in joined or "error" in joined


# ---------------------------------------------------------------------------
# Case isolation — each case stays in its lane.
# ---------------------------------------------------------------------------


def test_intereses_query_does_not_emit_leasing_or_primer_empleo() -> None:
    out = build_recommendations(
        request=_req("¿son deducibles los intereses del préstamo bancario?"),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "leasing" not in joined
    assert "108-5" not in joined
    assert "primer empleo" not in joined


def test_leasing_query_does_not_emit_intereses_or_primer_empleo() -> None:
    out = build_recommendations(
        request=_req("¿cómo se deduce el leasing financiero?"),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    # 118-1 (subcap) shouldn't fire on a pure leasing query.
    assert "118-1" not in joined
    assert "subcapitalización" not in joined and "subcapitalizacion" not in joined
    assert "108-5" not in joined


def test_primer_empleo_query_does_not_emit_intereses_or_leasing() -> None:
    out = build_recommendations(
        request=_req("¿procede el 120% del art. 108-5 por primer empleo?"),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "leasing" not in joined
    assert "subcapitalización" not in joined and "subcapitalizacion" not in joined


# ---------------------------------------------------------------------------
# End-to-end: Q2 stops being Cobertura pendiente for all three cases.
# ---------------------------------------------------------------------------


def _q2_assignment(q1: str, q2: str):
    from lia_graph.pipeline_d.answer_synthesis_sections import build_direct_answers

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
    return direct[1]


def test_intereses_q2_no_longer_cobertura_pendiente() -> None:
    from lia_graph.pipeline_d.answer_policy import DIRECT_ANSWER_COVERAGE_PENDING

    q1 = "¿Son deducibles los intereses del crédito bancario AG 2025?"
    q2 = (
        "¿Qué porcentaje es deducible, en qué norma se fundamenta, y cómo"
        " debe registrarse en la depuración de renta?"
    )
    assignment = _q2_assignment(q1, q2)
    assert assignment[1] != (DIRECT_ANSWER_COVERAGE_PENDING,)


def test_leasing_q2_no_longer_cobertura_pendiente() -> None:
    from lia_graph.pipeline_d.answer_policy import DIRECT_ANSWER_COVERAGE_PENDING

    q1 = "¿Cómo se deduce el leasing financiero del vehículo de la PYME?"
    q2 = (
        "¿Qué porcentaje es deducible, en qué norma se fundamenta, y cómo"
        " debe registrarse en la depuración?"
    )
    assignment = _q2_assignment(q1, q2)
    assert assignment[1] != (DIRECT_ANSWER_COVERAGE_PENDING,)


def test_primer_empleo_q2_no_longer_cobertura_pendiente() -> None:
    from lia_graph.pipeline_d.answer_policy import DIRECT_ANSWER_COVERAGE_PENDING

    q1 = "¿Procede la deducción del 120% por primer empleo para un joven de 25 años?"
    q2 = (
        "¿Qué porcentaje es deducible, en qué norma se fundamenta, y cómo"
        " debe registrarse en la depuración?"
    )
    assignment = _q2_assignment(q1, q2)
    assert assignment[1] != (DIRECT_ANSWER_COVERAGE_PENDING,)
