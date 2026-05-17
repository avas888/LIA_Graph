"""v23 P1 — Topic-Gate Decomposition (G1) unit tests."""

from __future__ import annotations

import pytest

from lia_graph.pipeline_d.answer_topic_decomposition import (
    decomposition_mode,
    detect_topic_groups,
    diagnostics_payload,
    effective_router_topic,
    framing_line,
    should_decompose,
)
from lia_graph.pipeline_d.contracts import GraphEvidenceBundle, GraphEvidenceItem


def _ev(node_key: str, *, secondaries: tuple[str, ...] = ()) -> GraphEvidenceItem:
    return GraphEvidenceItem(
        node_kind="article",
        node_key=node_key,
        title=f"Art. {node_key}",
        excerpt=f"Texto del artículo {node_key}.",
        source_path=None,
        score=0.9,
        hop_distance=0,
        secondary_topics=secondaries,
    )


def _bundle(primary: tuple[GraphEvidenceItem, ...]) -> GraphEvidenceBundle:
    return GraphEvidenceBundle(
        primary_articles=primary,
        connected_articles=(),
        related_reforms=(),
        support_documents=(),
        citations=(),
        diagnostics={},
    )


@pytest.fixture(autouse=True)
def _enforce_mode(monkeypatch):
    monkeypatch.setenv("LIA_TOPIC_DECOMPOSITION_MODE", "enforce")


def test_mode_defaults_to_enforce(monkeypatch):
    monkeypatch.delenv("LIA_TOPIC_DECOMPOSITION_MODE", raising=False)
    assert decomposition_mode() == "enforce"


def test_mode_off_disables_decomposition(monkeypatch):
    monkeypatch.setenv("LIA_TOPIC_DECOMPOSITION_MODE", "off")
    bundle = _bundle((
        _ev("art:617", secondaries=("facturacion_electronica",)),
        _ev("art:107", secondaries=("deducibilidad_renta",)),
    ))
    coherence = {"misaligned": True, "reason": "primary_off_topic", "dominant_topic": "deducibilidad_renta"}
    assert should_decompose(coherence, bundle, "facturacion_electronica") is False


def test_should_decompose_fires_on_primary_off_topic():
    bundle = _bundle((
        _ev("art:617", secondaries=("facturacion_electronica",)),
        _ev("art:107", secondaries=("deducibilidad_renta",)),
    ))
    coherence = {
        "misaligned": True,
        "reason": "primary_off_topic",
        "dominant_topic": "deducibilidad_renta",
    }
    assert should_decompose(coherence, bundle, "facturacion_electronica") is True


def test_should_decompose_fires_on_chunks_off_topic():
    bundle = _bundle((
        _ev("art:600", secondaries=("iva_periodicidad",)),
        _ev("art:601", secondaries=("obligaciones_formales",)),
    ))
    coherence = {
        "misaligned": True,
        "reason": "chunks_off_topic",
        "dominant_topic": "obligaciones_formales",
    }
    assert should_decompose(coherence, bundle, "iva_periodicidad") is True


def test_should_decompose_skips_aligned_coherence():
    bundle = _bundle((_ev("art:107"),))
    coherence = {"misaligned": False, "reason": "primary_on_topic"}
    assert should_decompose(coherence, bundle, "deducibilidad_renta") is False


def test_effective_router_topic_falls_back_to_coherence_router():
    coherence = {"router_topic": "iva", "misaligned": True}
    assert effective_router_topic(coherence, "") == "iva"
    assert effective_router_topic(coherence, "regimen_simple") == "regimen_simple"


def test_should_decompose_fires_on_fanout_with_empty_request_topic():
    """v23 P1 — fan-out queries leave request.topic empty; bypass must
    still fire using the coherence dict's router_topic."""
    bundle = _bundle((
        _ev("art:600", secondaries=("iva_periodicidad",)),
        _ev("art:107", secondaries=("deducibilidad_renta",)),
    ))
    coherence = {
        "misaligned": True,
        "reason": "primary_off_topic",
        "router_topic": "iva",
        "dominant_topic": "costos_deducciones_renta",
    }
    assert should_decompose(coherence, bundle, "") is True


def test_should_decompose_fires_with_single_primary():
    """v23 P1 threshold lowered to >=1 primary so audit-shape refusals
    flip to substantive answers even when only one article anchored."""
    bundle = _bundle((_ev("art:107", secondaries=("deducibilidad_renta",)),))
    coherence = {"misaligned": True, "reason": "primary_off_topic"}
    assert should_decompose(coherence, bundle, "facturacion_electronica") is True


def test_should_decompose_skips_unrelated_reason():
    bundle = _bundle((
        _ev("art:617", secondaries=("facturacion_electronica",)),
        _ev("art:107", secondaries=("deducibilidad_renta",)),
    ))
    coherence = {"misaligned": True, "reason": "zero_evidence_for_router_topic"}
    assert should_decompose(coherence, bundle, "facturacion_electronica") is False


def test_detect_topic_groups_uses_router_membership():
    bundle = _bundle((
        _ev("art:617", secondaries=("facturacion_electronica", "deducibilidad_renta")),
        _ev("art:107", secondaries=("deducibilidad_renta",)),
        _ev("art:771", secondaries=("deducibilidad_renta",)),
    ))
    groups = detect_topic_groups(bundle, "deducibilidad_renta")
    assert dict(groups)["deducibilidad_renta"] == 3


def test_detect_topic_groups_falls_back_when_router_not_in_secondaries():
    bundle = _bundle((
        _ev("art:617", secondaries=("facturacion_electronica",)),
        _ev("art:107", secondaries=("deducibilidad_renta",)),
    ))
    groups = detect_topic_groups(bundle, "regimen_simple")
    assert any(t == "facturacion_electronica" for t, _ in groups)
    assert any(t == "deducibilidad_renta" for t, _ in groups)


def test_framing_line_lists_multiple_topics():
    bundle = _bundle((
        _ev("art:617", secondaries=("facturacion_electronica",)),
        _ev("art:107", secondaries=("deducibilidad_renta",)),
    ))
    coherence = {"reason": "primary_off_topic", "dominant_topic": "deducibilidad_renta"}
    text = framing_line(coherence, bundle, "facturacion_electronica")
    assert "varios ámbitos" in text
    assert "facturación electrónica" in text or "deducibilidad" in text
    assert text.endswith("\n\n")


def test_diagnostics_payload_when_applied():
    bundle = _bundle((
        _ev("art:617", secondaries=("facturacion_electronica",)),
        _ev("art:107", secondaries=("deducibilidad_renta",)),
    ))
    coherence = {"reason": "primary_off_topic", "dominant_topic": "deducibilidad_renta"}
    diag = diagnostics_payload(coherence, bundle, "facturacion_electronica", applied=True)
    assert diag["topic_decomposition_applied"] is True
    assert diag["topic_decomposition_mode"] == "enforce"
    assert diag["topic_decomposition_section_count"] >= 1
    assert all(
        "topic" in g and "primary_article_count" in g
        for g in diag["topic_decomposition_groups"]
    )
