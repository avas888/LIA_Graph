"""Tests for the LLM-throttle env var resolution.

Verifies LLM_DEEPSEEK_RPM is the preferred cap source on DeepSeek
runs and that legacy aliases still work.
"""

from __future__ import annotations

import os

import pytest

from lia_graph.gemini_throttle import _resolve_rpm, _is_disabled


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in (
        "LLM_DEEPSEEK_RPM",
        "LIA_LLM_GLOBAL_RPM",
        "LIA_GEMINI_GLOBAL_RPM",
        "LLM_GLOBAL_DISABLED",
        "LIA_GEMINI_GLOBAL_DISABLED",
    ):
        monkeypatch.delenv(k, raising=False)


def test_default_rpm_when_no_env(monkeypatch):
    assert _resolve_rpm(80) == 80


def test_deepseek_rpm_takes_priority(monkeypatch):
    monkeypatch.setenv("LLM_DEEPSEEK_RPM", "240")
    monkeypatch.setenv("LIA_GEMINI_GLOBAL_RPM", "60")
    assert _resolve_rpm(80) == 240


def test_llm_global_rpm_falls_back_when_no_deepseek(monkeypatch):
    monkeypatch.setenv("LIA_LLM_GLOBAL_RPM", "120")
    monkeypatch.setenv("LIA_GEMINI_GLOBAL_RPM", "60")
    assert _resolve_rpm(80) == 120


def test_legacy_gemini_rpm_works_alone(monkeypatch):
    monkeypatch.setenv("LIA_GEMINI_GLOBAL_RPM", "150")
    assert _resolve_rpm(80) == 150


def test_disabled_via_modern_env(monkeypatch):
    monkeypatch.setenv("LLM_GLOBAL_DISABLED", "1")
    assert _is_disabled() is True


def test_disabled_via_legacy_env(monkeypatch):
    monkeypatch.setenv("LIA_GEMINI_GLOBAL_DISABLED", "1")
    assert _is_disabled() is True


def test_not_disabled_by_default(monkeypatch):
    assert _is_disabled() is False
