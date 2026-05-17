"""v23 P5 — numeric-input preservation + contradiction detection tests."""

from __future__ import annotations

import pytest

from lia_graph.pipeline_d.answer_llm_polish import (
    _no_inconsistent_year_constants,
    _preserves_user_numerics,
)


@pytest.fixture(autouse=True)
def _enforce(monkeypatch):
    monkeypatch.setenv("LIA_POLISH_INPUT_PRESERVATION", "enforce")


# ---------------------------------------------------------------------------
# _preserves_user_numerics
# ---------------------------------------------------------------------------


def test_preserves_amount_survives_dotted_form():
    q = "Compré un laptop por $3.000.000 más IVA."
    polished = "Para un activo de $3.000.000, deprecie..."
    assert _preserves_user_numerics("", polished, None, q) is True


def test_preserves_amount_survives_compact_form():
    q = "Compré un laptop por $3.000.000 más IVA."
    polished = "El costo de 3000000 pesos se deprecia en cinco años."
    assert _preserves_user_numerics("", polished, None, q) is True


def test_rejects_mutated_amount():
    q = "Compré un laptop por $3.000.000 más IVA."
    polished = "Para un activo de $2.000.000, deprecie..."
    assert _preserves_user_numerics("", polished, None, q) is False


def test_off_mode_passes_anything(monkeypatch):
    monkeypatch.setenv("LIA_POLISH_INPUT_PRESERVATION", "off")
    q = "Compré un laptop por $3.000.000."
    polished = "Para $99.999..."
    assert _preserves_user_numerics("", polished, None, q) is True


def test_shadow_mode_logs_but_passes(monkeypatch):
    monkeypatch.setenv("LIA_POLISH_INPUT_PRESERVATION", "shadow")
    q = "Compré un laptop por $3.000.000."
    polished = "Para $2.000.000..."
    assert _preserves_user_numerics("", polished, None, q) is True


def test_noop_when_no_amount_in_question():
    q = "¿Cómo deprecio un activo fijo?"
    polished = "Aplique el método lineal según vida útil."
    assert _preserves_user_numerics("", polished, None, q) is True


def test_spelled_amount_matches_digit_form():
    q = "Tengo un cliente con tres millones de pesos en cartera."
    polished = "Para $3.000.000 en cartera, evalúe deterioro."
    assert _preserves_user_numerics("", polished, None, q) is True


# ---------------------------------------------------------------------------
# _no_inconsistent_year_constants
# ---------------------------------------------------------------------------


def test_passes_single_uvt_value():
    polished = "El monto en UVT 2026 = $52.374."
    assert _no_inconsistent_year_constants("", polished) is True


def test_rejects_two_uvt_values_no_year_signal():
    polished = "UVT $47.065 ... y también UVT $49.799 en otra parte."
    assert _no_inconsistent_year_constants("", polished) is False


def test_allows_explicit_multi_year_comparison():
    polished = (
        "Comparación AG 2024 vs AG 2025: UVT AG 2024 = $47.065; "
        "UVT AG 2025 = $49.799."
    )
    assert _no_inconsistent_year_constants("", polished) is True


def test_off_mode_passes(monkeypatch):
    monkeypatch.setenv("LIA_POLISH_INPUT_PRESERVATION", "off")
    polished = "UVT $47.065 ... UVT $49.799."
    assert _no_inconsistent_year_constants("", polished) is True


def test_no_uvt_mention_passes():
    polished = "Aplique el método lineal de depreciación."
    assert _no_inconsistent_year_constants("", polished) is True
