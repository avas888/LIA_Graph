"""v23 P7 — Anclaje Legal topic-aware constraint tests."""

from __future__ import annotations

import pytest

from lia_graph.pipeline_d.answer_anclaje_topic_gate import (
    diagnostics_payload,
    filter_anclaje_articles,
    gate_mode,
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


def test_articles_with_no_secondary_topics_are_kept():
    articles = [
        _ev("64", secondaries=("terminacion_contrato",)),
        _ev("999", secondaries=()),
    ]
    kept, dropped = filter_anclaje_articles(articles, "terminacion_contrato")
    kept_keys = {i.node_key for i in kept}
    assert kept_keys == {"64", "999"}
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
