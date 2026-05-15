"""v16 b3 (2026-05-14) — limit-style question matcher in build_direct_answers.

Pins the fix that lifts q07-style ("¿Cuál es el tope de ingresos para ser no
responsable de IVA?") from "Cobertura pendiente" to a substantive bullet
assignment when the bullets carry numeric ranges (e.g., "ingresos brutos del
año anterior < 3.500 UVT = $164.727.500") but no literal token overlap with
the question (no word "tope" in the bullet).

Before this fix, the lexical-overlap matcher returned `(DIRECT_ANSWER_COVERAGE_PENDING,)`
for these questions even though the answer was in `recommendations`.
"""
from __future__ import annotations

from lia_graph.pipeline_d.answer_policy import DIRECT_ANSWER_COVERAGE_PENDING
from lia_graph.pipeline_d.answer_synthesis_sections import (
    _bullet_has_numeric_range,
    _is_limit_style_question,
    build_direct_answers,
)


# ---------------------------------------------------------------------------
# _is_limit_style_question
# ---------------------------------------------------------------------------


def test_limit_question_tope_ingresos() -> None:
    assert _is_limit_style_question(
        "cual es el tope de ingresos para ser no responsable de iva"
    )


def test_limit_question_que_porcentaje() -> None:
    assert _is_limit_style_question("que porcentaje del gmf es deducible")


def test_limit_question_cuanto_puedo() -> None:
    assert _is_limit_style_question("cuanto puedo deducir en atenciones a clientes")


def test_limit_question_umbral() -> None:
    assert _is_limit_style_question("umbral de bancarizacion art 771-5")


def test_limit_question_hasta_cuanto() -> None:
    assert _is_limit_style_question("hasta cuanto puedo descontar")


def test_non_limit_question_when_aplica() -> None:
    # "cuándo aplica" is a temporal/applicability question, not a limit
    assert not _is_limit_style_question("cuando aplica el beneficio de auditoria")


def test_non_limit_question_como_calculo() -> None:
    # "cómo calculo" is a procedural question, not a limit
    assert not _is_limit_style_question(
        "como calculo la depreciacion fiscal de una camioneta"
    )


# ---------------------------------------------------------------------------
# _bullet_has_numeric_range
# ---------------------------------------------------------------------------


def test_bullet_with_uvt_threshold() -> None:
    assert _bullet_has_numeric_range(
        "Ingresos brutos del año anterior < 3.500 UVT = $164.727.500"
    )


def test_bullet_with_percentage_only() -> None:
    assert _bullet_has_numeric_range("El 50% del GMF efectivamente pagado es deducible")


def test_bullet_with_money() -> None:
    assert _bullet_has_numeric_range(
        "Si la PYME pagó $20.000.000, deduce $10.000.000"
    )


def test_bullet_with_range_entre_y() -> None:
    assert _bullet_has_numeric_range(
        "Retención progresiva: entre 1.090 y 3.270 UVT, tarifa 15%"
    )


def test_bullet_with_smmlv() -> None:
    assert _bullet_has_numeric_range(
        "Trabajadores con salario inferior a 10 SMMLV"
    )


def test_bullet_with_tope_de_phrase() -> None:
    assert _bullet_has_numeric_range("Tope de atenciones: 1% de ingresos fiscales netos")


def test_plain_prose_no_numeric_range() -> None:
    assert not _bullet_has_numeric_range(
        "Conserva el papel de trabajo del cálculo durante el plazo de firmeza."
    )


def test_only_year_is_not_a_range() -> None:
    # A bare year like 2025 shouldn't trip the detector — we want amounts /
    # thresholds / percentages, not plain calendar references.
    assert not _bullet_has_numeric_range(
        "El régimen aplica para el año gravable AG"
    )


# ---------------------------------------------------------------------------
# build_direct_answers — end-to-end behavior change
# ---------------------------------------------------------------------------


def test_limit_question_picks_up_numeric_range_bullet_when_no_token_overlap() -> None:
    """The whole point of the fix: a question asking 'tope de ingresos' with
    NO literal word 'tope' in the bullet still gets the numeric bullet
    assigned, rather than falling to Cobertura pendiente.
    """
    q1 = "¿Cómo aplico el procedimiento 1 para retener salarios?"
    q2 = "¿Cuál es el tope de ingresos para ser no responsable de IVA en AG 2025?"
    bullets = (
        # Bullet 1: literal match for Q1 (procedimiento + retener)
        "Procedimientos 1 y 2 — el contador elige entre cálculo mensual y semestral.",
        # Bullet 2: numeric-range answer for Q2 but no literal "tope" token
        "Requisitos acumulativos para PN no responsable: ingresos brutos del año anterior < 3.500 UVT = $164.727.500 y un único establecimiento.",
    )
    result = build_direct_answers(
        sub_questions=(q1, q2),
        recommendations=bullets,
        procedure=(), paperwork=(), precautions=(), context_lines=(), opportunities=(),
    )
    assert len(result) == 2
    q1_assignment = result[0][1]
    q2_assignment = result[1][1]
    # Q2 must NOT be Cobertura pendiente — it must pick up the numeric bullet
    assert q2_assignment != (DIRECT_ANSWER_COVERAGE_PENDING,)
    assert any("3.500 UVT" in b or "164.727.500" in b for b in q2_assignment)


def test_literal_match_still_wins_over_structural_match() -> None:
    """When a bullet has literal token overlap with a non-limit question
    AND another sub-question is limit-style with a numeric bullet, the
    literal hit goes to its question — not stolen by the limit question.
    """
    q1 = "¿Cuál es el tope de UVT para el grupo 2 del RST?"  # limit-style
    q2 = "¿Cuál es la firmeza ordinaria de la declaración de renta?"
    bullets = (
        # Numeric range present (so Q1 *could* take it structurally), BUT
        # the bullet shares "firmeza" with Q2 — literal match must win.
        "La firmeza ordinaria de la declaración de renta es de 3 años (art. 714 ET).",
    )
    result = build_direct_answers(
        sub_questions=(q1, q2),
        recommendations=bullets,
        procedure=(), paperwork=(), precautions=(), context_lines=(), opportunities=(),
    )
    q1_assignment = result[0][1]
    q2_assignment = result[1][1]
    # Q2 wins via literal match; Q1 (limit) does NOT steal the bullet.
    assert q2_assignment != (DIRECT_ANSWER_COVERAGE_PENDING,)
    assert any("firmeza" in b.lower() for b in q2_assignment)
    assert q1_assignment == (DIRECT_ANSWER_COVERAGE_PENDING,)


def test_non_limit_question_no_structural_match_when_no_overlap() -> None:
    """A non-limit question with zero token overlap still falls to Cobertura
    pendiente — the structural bonus only kicks in for limit-shaped questions.
    Prevents the bonus from swallowing unrelated bullets into procedural
    questions.
    """
    q1 = "¿Cómo aplica la firmeza ordinaria de las declaraciones?"
    q2 = "¿Qué documentación conservo?"
    bullets = (
        "Tarifa marginal del 19% sobre el exceso de 95 UVT en la base.",  # numeric, unrelated
    )
    result = build_direct_answers(
        sub_questions=(q1, q2),
        recommendations=bullets,
        procedure=(), paperwork=(), precautions=(), context_lines=(), opportunities=(),
    )
    # Neither question gets the unrelated numeric bullet — both pending.
    assert result[0][1] == (DIRECT_ANSWER_COVERAGE_PENDING,)
    assert result[1][1] == (DIRECT_ANSWER_COVERAGE_PENDING,)


def test_single_subquestion_still_short_circuits() -> None:
    """The < 2 sub_questions guard is preserved — single-Q calls return ()."""
    result = build_direct_answers(
        sub_questions=("¿Cuál es el tope de ingresos para no responsable de IVA?",),
        recommendations=("Ingresos brutos < 3.500 UVT.",),
        procedure=(), paperwork=(), precautions=(), context_lines=(), opportunities=(),
    )
    assert result == ()
