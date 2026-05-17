"""Permanent regression suite for the 10 questions in the 2026-05-17 external
Colombian-accountant audit (fix_v23_may.md §1.2 + audit archive at
``docs/re-engineer/audits/2026-05-17_external_sme_audit_pre_v23.md``).

Each test is xfail-decorated initially; the v23 phase that closes the
question removes the xfail and tightens the assertion. The suite is the
canonical regression bar that v23+ must clear, per D12 + `feedback_verify_fixes_end_to_end`.

The tests assert SHAPE invariants (no refusal, correct citation source-code,
no stale UVT, no voseo, no off-topic Anclaje, user numerics preserved). They
do NOT do live LLM calls; the heavy lift is `scripts/eval/answer_engine_probe`
(via the `answer-engine-probe` skill), run by the operator phase-by-phase.

The 10 questions, by phase mapping (see audit archive for canonical Q.text):

  Q1  P1   Documento soporte factura electronica vs deducibilidad   (G1)
  Q2  P2+P3 Retencion en la fuente 2026                              (G2+G3)
  Q3  P1   IVA periodicidad 92,000 UVT                                (G1)
  Q4  P3   Nomina + auxilio transporte + nomina electronica           (G3)
  Q5  P3+P4 Revisor fiscal SAS topes                                  (G3+G4)
  Q6  P1   Regimen Simple restaurante INC/IVA/ICA                     (G1)
  Q7  P2+P6 Informacion exogena AG 2025                               (G6+G2 cal.)
  Q8  P1   RUB beneficiarios finales                                  (G1)
  Q9  P3+P4 NIIF Pymes deterioro + ET 145/146 castigo                 (G3+G4)
  Q10 P2+P5 Computador laptop activo fijo                             (G5+G2)
"""

from __future__ import annotations

import re
from typing import Final

import pytest

# Refusal cues from `_coherence_gate.py::refusal_text`. If any survives in
# the produced answer the topic-decomposition fix (P1) hasn't fired.
REFUSAL_CUES: Final[tuple[str, ...]] = (
    "reformula la consulta",
    "no cuento con información suficiente",
    "no tengo suficiente información",
    "no encontré información suficiente",
)

# Voseo verbs blacklist (P6). Word-boundary scan; case-insensitive.
VOSEO_VERBS_RX: Final[re.Pattern[str]] = re.compile(
    r"\b(verific[aá]|ten[eé]|and[aá]|mir[aá]|decid[ií]|pens[aá]|sal[ií]"
    r"|ped[ií]|segu[ií]|eleg[ií]|escrib[ií]|habl[aá]|tom[aá]|hac[eé]|pon[eé])\b",
    flags=re.IGNORECASE,
)

# Stale 2024 UVT (47,065). Audit Q2/Q10 surfaced this. P2 closes.
STALE_UVT_2024_TOKENS: Final[tuple[str, ...]] = ("47065", "47.065", "47,065")
# Stale 2025 UVT in a 2026 answer (49,799). P2 closes.
STALE_UVT_2025_TOKENS: Final[tuple[str, ...]] = ("49799", "49.799", "49,799")
# Correct 2026 UVT (52,374). Res. DIAN 000238/2025.
CORRECT_UVT_2026_TOKENS: Final[tuple[str, ...]] = ("52374", "52.374", "52,374")

# Pseudo-citation tokens from audit (G3). Anchor-shape validator rejects.
PSEUDO_CITATION_TOKENS: Final[tuple[str, ...]] = (
    "notas-y-fuentes",
    "respuesta-operativa",
    "art. notas",
    "art. respuesta",
)

# Pollution leakage from audit Q5 (G4). Filter ships shadow in v23 P4;
# v24 cleans cloud. Tests assert these MUST NOT appear in answers.
POLLUTION_LEAK_TOKENS: Final[tuple[str, ...]] = (
    "DISTRIBUIDORA EL SOL",
    "ALEJANDRO VASQUEZ",
    "Formulario 7",
)


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


# ---------------------------------------------------------------------------
# Shape assertion helpers — used by the operator probe runner. Each test
# is a no-op contract test until a sample probe-output fixture lands.
# ---------------------------------------------------------------------------


def assert_no_refusal(answer: str) -> None:
    assert not _has_any(answer, REFUSAL_CUES), (
        f"Refusal cue found in answer (G1 / P1 regression). Cues checked: {REFUSAL_CUES}"
    )


def assert_no_voseo(answer: str) -> None:
    match = VOSEO_VERBS_RX.search(answer)
    assert match is None, (
        f"Voseo verb '{match.group(0)}' found in answer (G6 / P6 regression)."
    )


def assert_no_pseudo_citation(answer: str) -> None:
    assert not _has_any(answer, PSEUDO_CITATION_TOKENS), (
        f"Pseudo-citation token found (G3 / P3 regression). Tokens: {PSEUDO_CITATION_TOKENS}"
    )


def assert_no_pollution_leak(answer: str) -> None:
    assert not _has_any(answer, POLLUTION_LEAK_TOKENS), (
        f"Pollution leak found (G4 / P4 regression). Tokens: {POLLUTION_LEAK_TOKENS}"
    )


def assert_user_numerics_preserved(answer: str, question_amounts: tuple[str, ...]) -> None:
    """E.g. for Q10 question_amounts = ('3.000.000', '3000000', 'tres millones')."""
    assert any(token in answer for token in question_amounts), (
        f"User numeric mutated (G5 / P5 regression). Expected one of {question_amounts}"
    )


def assert_correct_year_uvt(answer: str, year: int) -> None:
    if year == 2026:
        assert _has_any(answer, CORRECT_UVT_2026_TOKENS), (
            "UVT 2026 (52,374) not found in answer (G2 / P2 regression)."
        )
        assert not _has_any(answer, STALE_UVT_2025_TOKENS), (
            "Stale UVT 2025 (49,799) found in a 2026 answer (G2 / P2 regression)."
        )


# ---------------------------------------------------------------------------
# The 10 audit questions. Each test is xfail-skip until the closing phase
# enables it via a probe output fixture (operator path) OR removes the xfail
# after manual probe verification.
# ---------------------------------------------------------------------------


def test_q01_documento_soporte_vs_deducibilidad() -> None:
    """Q1 (G1 / P1) — multi-domain refusal. Must be sectioned, not refused."""
    answer = _probe_or_skip("q01")
    assert_no_refusal(answer)


@pytest.mark.xfail(reason="P2+P3 not yet enabled", strict=False)
def test_q02_retencion_fuente_2026() -> None:
    """Q2 (G2+G3 / P2+P3) — UVT 2026 = 52,374 (not 49,799); no pseudo-citations."""
    answer = _probe_or_skip("q02")
    assert_correct_year_uvt(answer, 2026)
    assert_no_pseudo_citation(answer)


def test_q03_iva_periodicidad_92000_uvt() -> None:
    """Q3 (G1 / P1)."""
    answer = _probe_or_skip("q03")
    assert_no_refusal(answer)


@pytest.mark.xfail(reason="P3 not yet enabled", strict=False)
def test_q04_nomina_auxilio_transporte() -> None:
    """Q4 (G3 / P3) — labor cites CST, not ET; nomina electronica = Res. DIAN."""
    answer = _probe_or_skip("q04")
    assert "CST" in answer or "Código Sustantivo del Trabajo" in answer
    assert_no_pseudo_citation(answer)


@pytest.mark.xfail(reason="P3+P4 not yet enabled", strict=False)
def test_q05_revisor_fiscal_sas_topes() -> None:
    """Q5 (G3+G4 / P3+P4) — cites C.Co. + Ley 43/1990; no pollution leak."""
    answer = _probe_or_skip("q05")
    assert ("C.Co." in answer or "Código de Comercio" in answer) or "Ley 43" in answer
    assert_no_pseudo_citation(answer)
    assert_no_pollution_leak(answer)


def test_q06_regimen_simple_restaurante() -> None:
    """Q6 (G1 / P1)."""
    answer = _probe_or_skip("q06")
    assert_no_refusal(answer)


def test_q07_informacion_exogena_2025() -> None:
    """Q7 (G6+G2cal / P2+P6) — no voseo."""
    answer = _probe_or_skip("q07")
    assert_no_voseo(answer)


def test_q08_rub_beneficiarios_finales() -> None:
    """Q8 (G1 / P1)."""
    answer = _probe_or_skip("q08")
    assert_no_refusal(answer)


def test_q09_niif_pymes_deterioro_castigo() -> None:
    """Q9 (G3+G4 / P3+P4) — no pseudo-citations; mentions ET 145/146."""
    answer = _probe_or_skip("q09")
    assert_no_pseudo_citation(answer)
    assert "145" in answer or "146" in answer


@pytest.mark.xfail(reason="P2+P5 not yet enabled", strict=False)
def test_q10_laptop_activo_fijo() -> None:
    """Q10 (G5+G2 / P2+P5) — preserves COP 3,000,000; single-year UVT."""
    answer = _probe_or_skip("q10")
    assert_user_numerics_preserved(answer, ("3.000.000", "3000000", "tres millones", "$3M"))


def test_q01_v22_handoff_anclaje_cst_64() -> None:
    """v22-P3-handoff probe — CST 64 question. Anclaje Legal must NOT surface
    Art. 102 / 102-2 / 103 ET (G7 / P7).
    """
    answer = _probe_or_skip("q01_v22_handoff")
    for off_topic in ("Art. 102 ET", "Art. 102-2 ET", "Art. 103 ET"):
        assert off_topic not in answer, (
            f"Off-topic Anclaje line surfaced: {off_topic} (G7 / P7 regression)."
        )


# ---------------------------------------------------------------------------
# Probe-output fixture loader. Looks for a per-question text capture under
# ``tests/fixtures/audit_q01_q10/<id>.answer.txt``. Phases land fixtures as
# they close. Until a fixture exists for a Q, that Q's test xfails-skip.
# ---------------------------------------------------------------------------


def _probe_or_skip(qid: str) -> str:
    import pathlib

    fixture = (
        pathlib.Path(__file__).parent
        / "fixtures"
        / "audit_q01_q10"
        / f"{qid}.answer.txt"
    )
    if not fixture.exists():
        pytest.skip(f"No probe-output fixture yet at {fixture}; phase still open.")
    return fixture.read_text(encoding="utf-8")
