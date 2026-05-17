"""v23 P6 — Colombian-Spanish style validator tests."""

from __future__ import annotations

import pytest

from lia_graph.pipeline_d.answer_llm_polish import _no_voseo


@pytest.fixture(autouse=True)
def _enforce(monkeypatch):
    monkeypatch.setenv("LIA_POLISH_LOCALE_STYLE_COLOMBIAN", "enforce")


def test_passes_usted_imperatives():
    polished = "Verifique que el RUT esté actualizado. Tenga presente el plazo."
    assert _no_voseo("", polished) is True


def test_rejects_voseo_verb_verifica():
    polished = "Verificá que el RUT esté actualizado."
    assert _no_voseo("", polished) is False


def test_rejects_voseo_verb_tene():
    polished = "Tené presente que el plazo es de cinco días."
    assert _no_voseo("", polished) is False


def test_rejects_explicit_voseo_pronoun():
    polished = "vos podés revisar el RUT después."
    assert _no_voseo("", polished) is False


def test_off_mode_passes_voseo(monkeypatch):
    monkeypatch.setenv("LIA_POLISH_LOCALE_STYLE_COLOMBIAN", "off")
    polished = "Verificá y andá al portal DIAN."
    assert _no_voseo("", polished) is True


def test_shadow_mode_logs_but_passes(monkeypatch):
    monkeypatch.setenv("LIA_POLISH_LOCALE_STYLE_COLOMBIAN", "shadow")
    polished = "Verificá y andá al portal DIAN."
    assert _no_voseo("", polished) is True


def test_does_not_overfire_on_unrelated_accent():
    polished = "Recuérdele al cliente que el plazo vence."
    # "Recuérdele" is not a voseo form; should pass.
    assert _no_voseo("", polished) is True


def test_passes_legitimate_imperative_revise():
    polished = "Revise el formulario antes de enviarlo."
    assert _no_voseo("", polished) is True
