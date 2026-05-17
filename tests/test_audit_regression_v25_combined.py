"""v25 combined-superset regression suite — 20 questions.

The 2026-05-17 external Colombian-accountant SME ran a dual packet:
  - Packet 1 (Q1–Q10): rerun of the v23 baseline (audit archive
    ``docs/re-engineer/audits/2026-05-17_external_sme_audit_pre_v23.md``).
  - Packet 2 (Q11–Q20): new critical topics
    (``docs/re-engineer/audits/2026-05-17_external_sme_audit_post_v23.md``).

This module asserts SHAPE invariants per phase mapping in fix_v25_may.md §1.2.
Tests do not run live LLM calls — heavy lift is `answer-engine-probe`.

The 20 questions, by phase mapping:

  Q1   P1 norm-keyed Res. DIAN 000167/2021
  Q2   v23 P2 carryover (UVT 2026)
  Q3   P5 coverage-gap (IVA periodicidad ET 600)
  Q4   v23 P3 carryover (CST source-code)
  Q5   P8 entity-filter promote (revisor fiscal pollution)
  Q6   v23 P1 carryover (RST refusal) + P8 INC vehicle leak
  Q7   P1 norm-keyed Res. DIAN 000233/2025 + P6 deadline
  Q8   P1 norm-keyed Res. DIAN 000164/2021 + P9 counterfactual
  Q9   P8 entity-filter (Concepto DIAN 191/2025 depreciacion leak)
  Q10  P7 fallback numeric echo
  Q11  P3 municipal-tax routing (ICA Bogota territorialidad)
  Q12  P5 coverage-gap (IVA prorrateo noise)
  Q13  P6 multi-UVT helper (4 UVT 2026 = $209,496)
  Q14  P2 cross-border lane (servicios desde el exterior)
  Q15  P2 cross-border (dividendos extranjero) + P8 INCRNGO leak
  Q16  P9 counterfactual (Panama 1,930M injection)
  Q17  P9 counterfactual (InnovaLab injection)
  Q18  P1 norm-keyed Res. DIAN 000165/2023
  Q19  P4 framework awareness (NIIF Pymes vs NIIF 16)
  Q20  P6 deadline registry (RTE March 31)
"""

from __future__ import annotations

import re
from typing import Final

import pytest


# Phase mapping per fix_v25_may.md §1.2.
PHASE_MAP: Final[dict[str, tuple[str, ...]]] = {
    "Q1": ("P1",),
    "Q2": ("v23-P2",),
    "Q3": ("P5",),
    "Q4": ("v23-P3",),
    "Q5": ("P8",),
    "Q6": ("v23-P1", "P8"),
    "Q7": ("P1", "P6"),
    "Q8": ("P1", "P9"),
    "Q9": ("P8",),
    "Q10": ("P7",),
    "Q11": ("P3",),
    "Q12": ("P5",),
    "Q13": ("P6",),
    "Q14": ("P2",),
    "Q15": ("P2", "P8"),
    "Q16": ("P9",),
    "Q17": ("P9",),
    "Q18": ("P1",),
    "Q19": ("P4",),
    "Q20": ("P6",),
}


COVERAGE_GAP_STUBS: Final[tuple[str, ...]] = (
    "cobertura pendiente",
    "valida el expediente",
    "no encuentro evidencia",
)


COUNTERFACTUAL_TOKENS_BANNED: Final[tuple[str, ...]] = (
    "Carlos Moreno",  # Q8 RUB invented person
    "InnovaLab",  # Q17 invented company
    "DISTRIBUIDORA EL SOL",  # corpus pollution
    "ALEJANDRO VASQUEZ",  # corpus pollution
)


NIIF_16_TOKENS: Final[tuple[str, ...]] = ("NIIF 16", "IFRS 16", "right-of-use", "derecho de uso")
NIIF_PYMES_TOKENS: Final[tuple[str, ...]] = ("Sección 20", "Seccion 20", "NIIF para las Pymes")


# Probe-fixture cache directory (populated by P10-T2 internal close).
PROBE_FIXTURE_DIR = "tests/fixtures/audit_v25_q01_q20"


def _read_probe_fixture(qid: str) -> str | None:
    """Return probe answer text for ``qid`` or None when not yet captured.

    The fixture file lives at ``{PROBE_FIXTURE_DIR}/{qid}.answer.txt`` and is
    written by P10-T2 (internal close probe sweep). Until that runs, every
    test stays xfail.
    """
    from pathlib import Path

    path = Path(__file__).resolve().parent / "fixtures" / "audit_v25_q01_q20" / f"{qid}.answer.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _assert_no_coverage_gap(answer: str) -> None:
    haystack = answer.lower()
    for stub in COVERAGE_GAP_STUBS:
        assert stub not in haystack, f"coverage-gap stub leaked: {stub!r}"


def _assert_no_counterfactual_tokens(answer: str) -> None:
    for token in COUNTERFACTUAL_TOKENS_BANNED:
        assert token not in answer, f"counterfactual token leaked: {token!r}"


@pytest.mark.xfail(reason="P10-T2 probe fixture not yet captured", strict=False)
@pytest.mark.parametrize(
    "qid",
    sorted(PHASE_MAP.keys(), key=lambda q: int(q[1:])),
)
def test_audit_question_passes_phase_invariants(qid: str) -> None:
    answer = _read_probe_fixture(qid)
    if answer is None:
        pytest.xfail(f"probe fixture for {qid} not yet captured")

    _assert_no_coverage_gap(answer)
    _assert_no_counterfactual_tokens(answer)

    if qid == "Q19":
        haystack = answer
        if "NIIF para las Pymes" in haystack or "NIIF Pymes" in haystack:
            for tok in NIIF_16_TOKENS:
                assert tok not in haystack, (
                    f"Q19 framework-coherence breach: {tok!r} surfaced in a NIIF-Pymes answer"
                )

    if qid == "Q20":
        assert any(s in answer for s in ("31 de marzo", "March 31", "marzo 31")), (
            "Q20 RTE deadline not present in answer (P6 deadline registry must inject)"
        )

    if qid == "Q14":
        assert any(
            tok in answer for tok in ("art. 437-2", "art. 420", "art. 408", "Art. 437-2", "Art. 408")
        ), "Q14 cross-border canonical articles missing (P2 lane must surface)"

    if qid == "Q11":
        assert any(
            tok in answer for tok in ("Acuerdo 65/2002", "Decreto 352/2002", "Decreto Distrital 352")
        ), "Q11 municipal pointer missing (P3 routing must surface)"
