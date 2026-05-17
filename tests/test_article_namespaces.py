"""v23 P3 — article→source-code resolver tests."""

from __future__ import annotations

import pytest

from lia_graph.pipeline_d.article_namespaces import (
    ResolvedAnchor,
    awareness_mode,
    is_real_article_number,
    render_anchor_phrase,
    resolve_source_code,
)


@pytest.fixture(autouse=True)
def _enforce(monkeypatch):
    monkeypatch.setenv("LIA_CITATION_SOURCE_CODE_AWARENESS", "enforce")


def test_awareness_mode_defaults_to_enforce(monkeypatch):
    monkeypatch.delenv("LIA_CITATION_SOURCE_CODE_AWARENESS", raising=False)
    assert awareness_mode() == "enforce"


def test_is_real_article_number_accepts_numeric():
    assert is_real_article_number("64") is True
    assert is_real_article_number("401-3") is True
    assert is_real_article_number("102-2") is True


def test_is_real_article_number_rejects_pseudo_citations():
    assert is_real_article_number("notas-y-fuentes") is False
    assert is_real_article_number("respuesta-operativa") is False
    assert is_real_article_number("paso-a-paso") is False


def test_resolve_source_code_node_key_cst_prefix_wins():
    assert resolve_source_code("64", node_key="cst.art.64") == "CST"


def test_resolve_source_code_node_key_et_prefix_wins():
    assert resolve_source_code("147", node_key="et.art.147") == "ET"


def test_resolve_source_code_labor_topic_anchors_cst():
    assert resolve_source_code("64", topic_hint="terminacion_contrato") == "CST"
    assert resolve_source_code("57", topic_hint="nomina") == "CST"


def test_resolve_source_code_revisor_fiscal_203_anchors_cco():
    assert (
        resolve_source_code("203", topic_hint="revisor_fiscal") == "CCO"
    )


def test_resolve_source_code_ley_43_1990_art_13():
    assert (
        resolve_source_code("13", topic_hint="revisor_fiscal")
        == "LEY_43_1990"
    )


def test_resolve_source_code_falls_back_to_et_legacy_default():
    assert resolve_source_code("147", topic_hint="deducibilidad_renta") == "ET"


def test_resolve_source_code_returns_none_when_legacy_default_disabled():
    # Tax topic that doesn't match labor/revisor-fiscal AND no prefix or CCo
    # article table hit AND legacy_default=None → no fallback emitted.
    assert (
        resolve_source_code("147", topic_hint="deducibilidad_renta", legacy_default=None)
        is None
    )


def test_resolve_source_code_off_mode_passthrough(monkeypatch):
    monkeypatch.setenv("LIA_CITATION_SOURCE_CODE_AWARENESS", "off")
    assert resolve_source_code("64", topic_hint="terminacion_contrato") == "ET"


def test_render_anchor_phrase_single_cst():
    anchors = [ResolvedAnchor(article="64", source_code="CST")]
    assert render_anchor_phrase(anchors) == "art. 64 CST"


def test_render_anchor_phrase_single_cco():
    anchors = [ResolvedAnchor(article="203", source_code="CCO")]
    assert render_anchor_phrase(anchors) == "art. 203 C.Co."


def test_render_anchor_phrase_single_ley_43_1990():
    anchors = [ResolvedAnchor(article="13", source_code="LEY_43_1990")]
    assert render_anchor_phrase(anchors) == "art. 13 Ley 43/1990"


def test_render_anchor_phrase_two_same_code_groups():
    anchors = [
        ResolvedAnchor(article="64", source_code="CST"),
        ResolvedAnchor(article="65", source_code="CST"),
    ]
    assert render_anchor_phrase(anchors) == "arts. 64 y 65 CST"


def test_render_anchor_phrase_mixed_codes_separate_clauses():
    anchors = [
        ResolvedAnchor(article="64", source_code="CST"),
        ResolvedAnchor(article="401-3", source_code="ET"),
    ]
    out = render_anchor_phrase(anchors)
    assert "art. 64 CST" in out
    assert "art. 401-3 ET" in out
    assert "; " in out


def test_render_anchor_phrase_drops_pseudo_citations():
    anchors = [
        ResolvedAnchor(article="notas-y-fuentes", source_code="ET"),
        ResolvedAnchor(article="64", source_code="CST"),
    ]
    assert render_anchor_phrase(anchors) == "art. 64 CST"


def test_render_anchor_phrase_drops_all_pseudo_returns_empty():
    anchors = [
        ResolvedAnchor(article="notas-y-fuentes", source_code="ET"),
        ResolvedAnchor(article="respuesta-operativa", source_code="ET"),
    ]
    assert render_anchor_phrase(anchors) == ""
