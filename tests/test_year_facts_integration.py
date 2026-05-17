"""v23 P2 — Year-Constants Service (G2) tests."""

from __future__ import annotations

import pytest

from lia_graph.year_facts import (
    build_directive_block,
    clear_cache,
    extract_fiscal_year,
    get_year_facts,
    injection_mode,
)


@pytest.fixture(autouse=True)
def _autoreset(monkeypatch):
    clear_cache()
    monkeypatch.setenv("LIA_YEAR_CONSTANTS_INJECTION", "enforce")
    yield
    clear_cache()


def test_injection_mode_defaults_to_enforce(monkeypatch):
    monkeypatch.delenv("LIA_YEAR_CONSTANTS_INJECTION", raising=False)
    assert injection_mode() == "enforce"


def test_injection_mode_off(monkeypatch):
    monkeypatch.setenv("LIA_YEAR_CONSTANTS_INJECTION", "off")
    assert injection_mode() == "off"


def test_get_year_facts_returns_verified_uvt_2025():
    facts = get_year_facts(2025)
    assert facts is not None
    assert facts.uvt is not None
    assert facts.uvt.value_cop == 49799
    assert facts.uvt.verified is True


def test_get_year_facts_returns_verified_uvt_2026():
    facts = get_year_facts(2026)
    assert facts is not None
    assert facts.uvt is not None
    assert facts.uvt.value_cop == 52374
    assert facts.uvt.verified is True


def test_get_year_facts_missing_year_returns_none():
    assert get_year_facts(1995) is None


def test_extract_fiscal_year_picks_ag_pattern():
    assert extract_fiscal_year("Para AG 2026 retención en la fuente") == 2026


def test_extract_fiscal_year_picks_ano_gravable_pattern():
    assert extract_fiscal_year("año gravable 2024 declaración renta") == 2024


def test_extract_fiscal_year_picks_bare_year():
    assert extract_fiscal_year("UVT 2025 tabla retención") == 2025


def test_extract_fiscal_year_returns_none_when_no_year():
    assert extract_fiscal_year("Quiero entender el ET en general") is None


def test_extract_fiscal_year_never_defaults_to_today(monkeypatch):
    """Per D10 / Q-Open-3 — no silent fallback to date.today().year."""
    assert extract_fiscal_year("¿qué tarifa aplica?") is None


def test_extract_fiscal_year_uses_planner_intent_when_no_text():
    assert extract_fiscal_year(None, planner_intent={"fiscal_year": 2026}) == 2026


def test_extract_fiscal_year_uses_conversation_state_fallback():
    state = {"fiscal_year": 2025}
    assert extract_fiscal_year(None, conversation_state=state) == 2025


def test_build_directive_block_contains_uvt_2026():
    block = build_directive_block(2026)
    assert block is not None
    assert "AÑO GRAVABLE 2026" in block
    assert "52.374" in block


def test_build_directive_block_skips_unverified_smlmv_2026():
    """SMLMV 2026 row is verified=false; directive must not quote it."""
    block = build_directive_block(2026)
    assert block is not None
    # We do not want to leak an unverified figure.
    assert "1.623.500" not in block or "verificable" in block


def test_build_directive_block_returns_none_when_off(monkeypatch):
    monkeypatch.setenv("LIA_YEAR_CONSTANTS_INJECTION", "off")
    assert build_directive_block(2026) is None


def test_allowed_tokens_include_uvt_2026_dotted_form():
    facts = get_year_facts(2026)
    assert facts is not None
    tokens = facts.allowed_tokens()
    assert "52374" in tokens
    assert "52.374" in tokens


def test_directive_lines_only_emit_verified_constants():
    facts = get_year_facts(2026)
    assert facts is not None
    lines = facts.directive_lines()
    assert any("52.374" in line for line in lines)
