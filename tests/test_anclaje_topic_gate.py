"""v23 P7 — Anclaje Legal topic-aware constraint tests."""

from __future__ import annotations

import pytest

from lia_graph.pipeline_d.answer_anclaje_topic_gate import (
    diagnostics_payload,
    filter_anclaje_articles,
    gate_mode,
)
from lia_graph.pipeline_d.answer_llm_polish import (
    filter_polished_anclaje_section,
)
from lia_graph.pipeline_d.contracts import GraphEvidenceItem


def _ev(node_key: str, *, secondaries: tuple[str, ...] = ()) -> GraphEvidenceItem:
    return GraphEvidenceItem(
        node_kind="article",
        node_key=node_key,
        title=f"Art. {node_key}",
        excerpt="",
        source_path=None,
        score=0.9,
        hop_distance=0,
        secondary_topics=secondaries,
    )


@pytest.fixture(autouse=True)
def _enforce(monkeypatch):
    monkeypatch.setenv("LIA_ANCLAJE_TOPIC_GATE", "enforce")


def test_gate_mode_defaults_enforce(monkeypatch):
    monkeypatch.delenv("LIA_ANCLAJE_TOPIC_GATE", raising=False)
    assert gate_mode() == "enforce"


def test_off_mode_preserves_all_articles(monkeypatch):
    monkeypatch.setenv("LIA_ANCLAJE_TOPIC_GATE", "off")
    articles = [
        _ev("64", secondaries=("terminacion_contrato",)),
        _ev("102", secondaries=("fiducia",)),
    ]
    kept, dropped = filter_anclaje_articles(articles, "terminacion_contrato")
    assert len(kept) == 2
    assert dropped == ()


def test_cst_64_question_drops_off_topic_et_articles():
    """Mirror of v22 P3 q01 finding."""
    articles = [
        _ev("64", secondaries=("terminacion_contrato",)),
        _ev("102", secondaries=("fiducia",)),
        _ev("102-2", secondaries=("transporte_terrestre",)),
        _ev("103", secondaries=("definicion_rentas",)),
    ]
    kept, dropped = filter_anclaje_articles(articles, "terminacion_contrato")
    kept_keys = {i.node_key for i in kept}
    dropped_keys = {i.node_key for i in dropped}
    assert "64" in kept_keys
    assert {"102", "102-2", "103"}.issubset(dropped_keys)


def test_articles_with_no_secondary_topics_fall_back_to_source_code_family():
    """v23 P7 method-level: empty secondary_topics → use source-code family.

    Labor effective topic + ET-titled article (graph gap on secondaries) →
    drop from Anclaje. Labor topic + CST-titled article → keep. This
    closes the v22 P3 q01 finding where Art. 102 / 102-2 / 103 ET had
    empty secondaries and passed the gate.
    """

    def _ev_with_title(node_key: str, title: str) -> GraphEvidenceItem:
        from lia_graph.pipeline_d.contracts import GraphEvidenceItem
        return GraphEvidenceItem(
            node_kind="article",
            node_key=node_key,
            title=title,
            excerpt="",
            source_path=None,
            score=0.9,
            hop_distance=0,
            secondary_topics=(),
        )

    articles = [
        _ev_with_title("64", "Art. 64 CST"),
        _ev_with_title("102", "Art. 102 ET"),
        _ev_with_title("102-2", "Art. 102-2 ET"),
        _ev_with_title("103", "Art. 103 ET"),
    ]
    kept, dropped = filter_anclaje_articles(articles, "terminacion_contrato")
    kept_keys = {i.node_key for i in kept}
    dropped_keys = {i.node_key for i in dropped}
    assert "64" in kept_keys
    assert {"102", "102-2", "103"}.issubset(dropped_keys)


def test_post_polish_filter_drops_off_topic_et_in_cst_answer():
    """v22 P3 q01 finding reproduced in markdown form: Anclaje had four
    bullets, three of them off-topic ET. Post-polish filter must drop them.
    """
    polished = (
        "**Recomendaciones Prácticas**\n"
        "1. Pague la indemnización del (art. 64 CST) en contratos a término indefinido.\n"
        "2. Aplique las reglas del (art. 65 CST) sobre salarios pendientes.\n"
        "\n"
        "**Anclaje Legal**\n"
        "* (Art. 64 CST) — Regula la terminación unilateral.\n"
        "* (Art. 102 ET) — Establece reglas de fiducia mercantil.\n"
        "* (Art. 102-2 ET) — Transporte terrestre.\n"
        "* (Art. 103 ET) — Rentas exclusivas de trabajo.\n"
    )
    out = filter_polished_anclaje_section(polished)
    assert "Art. 64 CST" in out
    assert "Art. 102 ET" not in out
    assert "Art. 102-2 ET" not in out
    assert "Art. 103 ET" not in out


def test_post_polish_filter_noop_when_no_anclaje():
    polished = "**Recomendaciones Prácticas**\n1. Algo.\n"
    assert filter_polished_anclaje_section(polished) == polished


def test_post_polish_filter_keeps_legitimate_et_in_tax_answer():
    polished = (
        "**Recomendaciones Prácticas**\n"
        "1. Aplique el (art. 240 ET) para tarifa de renta.\n"
        "2. Revise el (art. 241 ET) sobre tabla.\n"
        "\n"
        "**Anclaje Legal**\n"
        "* (Art. 240 ET) — Tarifa renta personas jurídicas.\n"
        "* (Art. 241 ET) — Tabla renta personas naturales.\n"
    )
    out = filter_polished_anclaje_section(polished)
    assert "Art. 240 ET" in out
    assert "Art. 241 ET" in out


def test_unknown_family_preserves_everything():
    """When the effective topic isn't in labor/tax families, fall back to
    'keep' so the gate doesn't over-block on niche topics."""

    def _ev_no_topics(node_key: str) -> GraphEvidenceItem:
        from lia_graph.pipeline_d.contracts import GraphEvidenceItem
        return GraphEvidenceItem(
            node_kind="article",
            node_key=node_key,
            title=f"Art. {node_key}",
            excerpt="",
            source_path=None,
            score=0.9,
            hop_distance=0,
            secondary_topics=(),
        )

    articles = [_ev_no_topics("100"), _ev_no_topics("200")]
    kept, dropped = filter_anclaje_articles(articles, "tema_nuevo_no_mapeado")
    assert len(kept) == 2
    assert dropped == ()


def test_empty_effective_topic_skips_gate():
    articles = [_ev("64", secondaries=("foo",))]
    kept, dropped = filter_anclaje_articles(articles, "")
    assert len(kept) == 1
    assert dropped == ()


def test_diagnostics_payload_shape():
    kept = (_ev("64", secondaries=("terminacion_contrato",)),)
    dropped = (_ev("102", secondaries=("fiducia",)),)
    payload = diagnostics_payload(
        kept=kept, dropped=dropped, effective_topic="terminacion_contrato"
    )
    assert payload["anclaje_topic_gate_mode"] == "enforce"
    assert payload["anclaje_topic_gate_applied"] is True
    assert payload["anclaje_articles_kept"] == ["64"]
    assert payload["anclaje_articles_dropped"] == ["102"]
    assert payload["anclaje_articles_dropped_count"] == 1
