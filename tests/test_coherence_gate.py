"""Phase 3 (v6) — evidence-topic coherence gate.

Six cases pinned against the plan's success criteria:
1. gate off → detector still runs (observation is cheap); ``should_refuse`` is False.
2. gate shadow → detector emits diagnostic; ``should_refuse`` is False.
3. gate enforce + primary empty + chunks off-topic → refusal (``chunks_off_topic``).
4. gate enforce + primary empty + chunks absent → refusal (``zero_evidence_for_router_topic``).
5. gate enforce + primary present on-topic → no refusal.
6. gate enforce + primary off-topic → refusal (``primary_off_topic``).
"""

from __future__ import annotations

import pytest

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d._coherence_gate import (
    coherence_mode,
    detect_evidence_coherence,
    refusal_text,
    should_refuse,
)
from lia_graph.pipeline_d.contracts import (
    Citation,
    GraphEvidenceBundle,
    GraphEvidenceItem,
    GraphSupportDocument,
)


def _request(topic: str = "laboral") -> PipelineCRequest:
    return PipelineCRequest(
        message="¿cómo se liquidan las cesantías de un trabajador medio tiempo?",
        topic=topic,
        requested_topic=topic,
    )


def _primary_item(title: str, excerpt: str) -> GraphEvidenceItem:
    return GraphEvidenceItem(
        node_kind="article",
        node_key=title.split()[0],
        title=title,
        excerpt=excerpt,
        source_path=None,
        score=1.0,
        hop_distance=0,
    )


def _support(topic_key: str | None, hint: str = "Documento de apoyo") -> GraphSupportDocument:
    return GraphSupportDocument(
        relative_path="fake/doc.md",
        source_path="fake/doc.md",
        title_hint=hint,
        family="normativa",
        knowledge_class=None,
        topic_key=topic_key,
        subtopic_key=None,
        canonical_blessing_status=None,
        graph_target=False,
        reason="test",
    )


def _bundle(
    *,
    primary: tuple[GraphEvidenceItem, ...] = (),
    support: tuple[GraphSupportDocument, ...] = (),
) -> GraphEvidenceBundle:
    return GraphEvidenceBundle(
        primary_articles=primary,
        connected_articles=(),
        related_reforms=(),
        support_documents=support,
        citations=(),
        diagnostics={},
    )


# ── 1. gate off ──────────────────────────────────────────────────────────


def test_gate_off_never_refuses_even_on_flagged_coherence(monkeypatch) -> None:
    monkeypatch.setenv("LIA_EVIDENCE_COHERENCE_GATE", "off")
    assert coherence_mode() == "off"
    coherence = detect_evidence_coherence(
        _request(), _bundle(support=(_support("impuesto_renta"),)), {}
    )
    assert coherence["misaligned"] is True
    assert should_refuse(coherence) is False


# ── 2. gate shadow ──────────────────────────────────────────────────────


def test_gate_shadow_emits_diagnostic_without_refusing(monkeypatch) -> None:
    monkeypatch.setenv("LIA_EVIDENCE_COHERENCE_GATE", "shadow")
    assert coherence_mode() == "shadow"
    coherence = detect_evidence_coherence(
        _request(), _bundle(support=(_support("impuesto_renta"),)), {}
    )
    assert coherence["misaligned"] is True
    assert coherence["reason"] in {"chunks_off_topic", "zero_evidence_for_router_topic"}
    assert should_refuse(coherence) is False


# ── 3. enforce + primary empty + chunks off-topic → chunks_off_topic ────


def test_gate_enforce_chunks_off_topic_refuses(monkeypatch) -> None:
    monkeypatch.setenv("LIA_EVIDENCE_COHERENCE_GATE", "enforce")
    # Request topic is 'laboral' but the support-doc title scores strongly
    # for a different topic (retencion_en_la_fuente) — lexical mismatch is
    # the exact Q16-class contamination the gate must refuse on.
    off_topic = _support(
        None,
        hint="retención en la fuente impuesto renta declaración régimen ordinario",
    )
    coherence = detect_evidence_coherence(_request(), _bundle(support=(off_topic,)), {})
    assert coherence["misaligned"] is True
    assert coherence["source"] == "support_documents"
    assert coherence["reason"] == "chunks_off_topic"
    assert coherence["dominant_topic"] != "laboral"
    assert should_refuse(coherence) is True
    msg = refusal_text(coherence)
    assert "laboral" in msg
    assert "no pude" in msg.lower() or "evidencia" in msg.lower()


# ── 4. enforce + primary empty + no support → zero_evidence ─────────────


def test_gate_enforce_zero_evidence_refuses(monkeypatch) -> None:
    monkeypatch.setenv("LIA_EVIDENCE_COHERENCE_GATE", "enforce")
    coherence = detect_evidence_coherence(_request(), _bundle(), {})
    assert coherence["misaligned"] is True
    assert coherence["source"] == "no_evidence"
    assert coherence["reason"] == "zero_evidence_for_router_topic"
    assert should_refuse(coherence) is True


# ── 5. enforce + primary present + on-topic → no refusal ────────────────


def test_gate_enforce_primary_on_topic_does_not_refuse(monkeypatch) -> None:
    monkeypatch.setenv("LIA_EVIDENCE_COHERENCE_GATE", "enforce")
    primary = (
        _primary_item(
            "383 retención en la fuente salarios",
            "Aplicable a pagos laborales regulares; ver también la UVT vigente.",
        ),
    )
    misalignment = {"misaligned": False, "articles_top_topic": "laboral"}
    coherence = detect_evidence_coherence(_request(), _bundle(primary=primary), misalignment)
    assert coherence["misaligned"] is False
    assert coherence["source"] == "primary"
    assert should_refuse(coherence) is False


# ── 6. enforce + primary off-topic → primary_off_topic ──────────────────


def test_gate_enforce_primary_off_topic_refuses(monkeypatch) -> None:
    monkeypatch.setenv("LIA_EVIDENCE_COHERENCE_GATE", "enforce")
    primary = (
        _primary_item(
            "Ley 939 de 2004 biocombustibles",
            "Incentivos para biocombustibles de origen vegetal y motores diesel.",
        ),
    )
    misalignment = {"misaligned": True, "articles_top_topic": "otros_sectoriales"}
    coherence = detect_evidence_coherence(_request(), _bundle(primary=primary), misalignment)
    assert coherence["misaligned"] is True
    assert coherence["source"] == "primary"
    assert coherence["reason"] == "primary_off_topic"
    assert coherence["dominant_topic"] == "otros_sectoriales"
    assert should_refuse(coherence) is True
    assert "otros_sectoriales" in refusal_text(coherence)


# ── Regression: support_documents with topic_key matches → on topic ─────


def test_support_topic_key_matches_treated_as_on_topic(monkeypatch) -> None:
    monkeypatch.setenv("LIA_EVIDENCE_COHERENCE_GATE", "enforce")
    support = (_support("laboral"), _support("laboral"))
    coherence = detect_evidence_coherence(_request(), _bundle(support=support), {})
    assert coherence["misaligned"] is False
    assert coherence["source"] == "support_documents"
    assert coherence["reason"] == "support_docs_on_topic"
    assert should_refuse(coherence) is False
