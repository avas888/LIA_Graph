"""v15.3 (2026-05-14) — ICA + predial deduction cases in
`build_recommendations`.

Same pattern as the GMF case (v15.1). Each detector fires on common
synonyms of its topic and emits 5 substantive bullets that carry the
porcentaje + norma + registro tokens needed by Q2-style sub-questions.

ICA bullet content grounded in:
* `knowledge_base/.../05_Libro1_T1_Cap4_Renta_Liquida.md` (Art. 115 ET literal)
* `knowledge_base/.../ICA_INDUSTRIA_COMERCIO/NORMATIVA/ICA-N01-marco-legal-ley-14-1983-territorialidad.md`
* `knowledge_base/.../ICA_INDUSTRIA_COMERCIO/EXPERTOS/ICA-E01-interpretaciones-ICA-RST-conflictos-territoriales.md`

Predial bullet content grounded in:
* `knowledge_base/.../05_Libro1_T1_Cap4_Renta_Liquida.md` (Art. 115 inciso 1)
"""

from __future__ import annotations

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_synthesis_helpers import (
    is_ica_deduction_case,
    is_predial_deduction_case,
)
from lia_graph.pipeline_d.answer_synthesis_sections import build_recommendations


def _req(message: str, topic: str = "costos_deducciones_renta") -> PipelineCRequest:
    return PipelineCRequest(
        message=message,
        topic=topic,
        requested_topic=topic,
    )


# ---------------------------------------------------------------------------
# is_ica_deduction_case
# ---------------------------------------------------------------------------


def test_ica_detector_matches_bare_token() -> None:
    assert is_ica_deduction_case("¿el ica pagado es deducible en renta?")


def test_ica_detector_matches_full_name() -> None:
    assert is_ica_deduction_case(
        "deducción del impuesto de industria y comercio en bogotá"
    )


def test_ica_detector_matches_avisos_y_tableros() -> None:
    assert is_ica_deduction_case(
        "tratamiento de avisos y tableros como deducción en renta"
    )


def test_ica_detector_ignores_indica_substring() -> None:
    # Without word-boundary check, "ica" would substring-match "indica"
    # / "indicador" / "publicado" — false positives that mis-route
    # unrelated queries to the ICA case bullets.
    assert not is_ica_deduction_case("la dian indica que el procedimiento es")
    assert not is_ica_deduction_case("publicación reciente sobre dividendos")
    assert not is_ica_deduction_case("indicador de evasión tributaria")


def test_ica_detector_ignores_predial_query() -> None:
    assert not is_ica_deduction_case(
        "el predial pagado por la sociedad es deducible"
    )


# ---------------------------------------------------------------------------
# is_predial_deduction_case
# ---------------------------------------------------------------------------


def test_predial_detector_matches_token() -> None:
    assert is_predial_deduction_case("¿el predial pagado es deducible?")


def test_predial_detector_matches_impuesto_predial() -> None:
    assert is_predial_deduction_case(
        "deducción del impuesto predial sobre la bodega del negocio"
    )


def test_predial_detector_ignores_ica_query() -> None:
    assert not is_predial_deduction_case("¿el ica pagado es deducible?")


# ---------------------------------------------------------------------------
# ICA case bullets
# ---------------------------------------------------------------------------


def test_ica_case_emits_100pct_and_descuento_alternative() -> None:
    out = build_recommendations(
        request=_req(
            "¿el ICA pagado por una PYME es deducible en renta? ¿qué"
            " porcentaje y en qué norma?"
        ),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "100%" in joined
    assert "art. 115 inciso 1 et" in joined
    # The alternative (50% descuento tributario under art. 115-1 ET) is
    # operationally critical — most PYMEs benefit more from it.
    assert "115-1" in joined
    assert "descuento tributario" in joined
    # Tarifa marginal comparison logic surfaces.
    assert "tarifa marginal" in joined or "35%" in joined


def test_ica_case_q2_tokens_present() -> None:
    """The five ICA bullets must collectively carry porcentaje +
    deducible + depuración + registra so the lexical Q→bullet matcher
    routes them into a Q2 about porcentaje + norma + registro."""
    out = build_recommendations(
        request=_req("¿qué porcentaje del ICA es deducible y cómo se registra?"),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "deducible" in joined or "deduccion" in joined or "deducción" in joined
    assert "depuración" in joined or "depuracion" in joined
    assert "registra" in joined
    assert "renglón" in joined or "renglon" in joined


# ---------------------------------------------------------------------------
# Predial case bullets
# ---------------------------------------------------------------------------


def test_predial_case_emits_causalidad_requirement() -> None:
    out = build_recommendations(
        request=_req(
            "¿el predial pagado por la bodega del negocio es deducible en renta?"
        ),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "100%" in joined
    assert "art. 115 inciso 1 et" in joined
    # The causalidad requirement is what separates a deductible
    # business-predial from a non-deductible personal-predial.
    assert "causalidad" in joined or "causación" in joined or "causacion" in joined
    # Must call out the personal-predial exclusion explicitly.
    assert "personal" in joined or "personales" in joined


def test_predial_case_q2_tokens_present() -> None:
    out = build_recommendations(
        request=_req(
            "¿qué porcentaje del predial es deducible, en qué norma se"
            " fundamenta, y cómo se registra?"
        ),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    assert "deducible" in joined or "deduccion" in joined or "deducción" in joined
    assert "registra" in joined
    assert "art. 115" in joined


# ---------------------------------------------------------------------------
# Case isolation — ICA bullets don't leak into a predial query and vice versa.
# ---------------------------------------------------------------------------


def test_predial_query_does_not_emit_ica_descuento_alternative() -> None:
    out = build_recommendations(
        request=_req("¿el predial pagado por la oficina es deducible?"),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    # The "50% descuento tributario via art. 115-1 ET" only applies
    # to ICA, never to predial.
    assert "art. 115-1 et" not in joined
    assert "descuento tributario" not in joined


def test_ica_query_does_not_emit_predial_personal_exclusion() -> None:
    out = build_recommendations(
        request=_req("¿el ICA pagado es deducible en renta?"),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    joined = "\n".join(out).lower()
    # The "predial de inmueble personal no es deducible" carve-out
    # only applies to predial, not to ICA.
    assert "inmueble" not in joined and "inmuebles personales" not in joined


# ---------------------------------------------------------------------------
# End-to-end: Q2 stops being Cobertura pendiente for both new cases.
# ---------------------------------------------------------------------------


def test_ica_q2_no_longer_cobertura_pendiente() -> None:
    from lia_graph.pipeline_d.answer_policy import DIRECT_ANSWER_COVERAGE_PENDING
    from lia_graph.pipeline_d.answer_synthesis_sections import build_direct_answers

    q1 = "¿El ICA pagado por una PYME es deducible en la declaración de renta?"
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
    q2_assignment = direct[1]
    assert q2_assignment[0] == q2
    assert q2_assignment[1] != (DIRECT_ANSWER_COVERAGE_PENDING,)


def test_predial_q2_no_longer_cobertura_pendiente() -> None:
    from lia_graph.pipeline_d.answer_policy import DIRECT_ANSWER_COVERAGE_PENDING
    from lia_graph.pipeline_d.answer_synthesis_sections import build_direct_answers

    q1 = "¿El predial pagado por la bodega del negocio es deducible en renta?"
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
    q2_assignment = direct[1]
    assert q2_assignment[0] == q2
    assert q2_assignment[1] != (DIRECT_ANSWER_COVERAGE_PENDING,)
