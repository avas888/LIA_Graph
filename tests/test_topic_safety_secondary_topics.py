"""v5 §1.A — topic_safety.detect_topic_misalignment respects ArticleNode.secondary_topics.

The structural fix for the FIRMEZA-class refusal pattern: if a primary article's
`secondary_topics` includes the router topic, treat as on-topic regardless of
lexical scoring. Pre-§1.A, the detector only used lexical scoring on the
article text — articles whose text scored heavily on adjacent topics (e.g.,
Art. 689-3 scoring high on `firmeza_declaraciones` lexically) refused queries
routed to the SME-validated other topic (`beneficio_auditoria`).
"""

from __future__ import annotations

import pytest

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.contracts import (
    GraphEvidenceBundle,
    GraphEvidenceItem,
)
from lia_graph.pipeline_d.topic_safety import detect_topic_misalignment


def _request(topic: str) -> PipelineCRequest:
    return PipelineCRequest(
        message="¿se puede tomar el beneficio de auditoría con pérdidas fiscales pendientes?",
        topic=topic,
        requested_topic=topic,
    )


def _article(
    *,
    node_key: str,
    title: str,
    excerpt: str,
    secondary_topics: tuple[str, ...] = (),
) -> GraphEvidenceItem:
    return GraphEvidenceItem(
        node_kind="ArticleNode",
        node_key=node_key,
        title=title,
        excerpt=excerpt,
        source_path=None,
        score=1.0,
        hop_distance=0,
        secondary_topics=secondary_topics,
    )


def _bundle(*items: GraphEvidenceItem) -> GraphEvidenceBundle:
    return GraphEvidenceBundle(
        primary_articles=tuple(items),
        connected_articles=(),
        related_reforms=(),
        support_documents=(),
        citations=(),
        diagnostics={},
    )


# ────────────────────────────────────────────────────────────────────────────
# (a) The binding §1.A case — Art. 689-3 declares secondary_topic
# beneficio_auditoria. Router routed to beneficio_auditoria. Lexical scoring
# of the article text would say firmeza_declaraciones (the canonical owner
# topic). Pre-§1.A this would be misaligned. Post-§1.A: NOT misaligned.
# ────────────────────────────────────────────────────────────────────────────


def test_secondary_topic_match_overrides_lexical_misalignment() -> None:
    article = _article(
        node_key="689-3",
        title="BENEFICIO DE AUDITORÍA.",
        excerpt=(
            "Para los periodos gravables 2024 a 2026 la liquidación privada de los "
            "contribuyentes del impuesto sobre la renta y complementarios quedará en "
            "firme si dentro de los seis (6) o doce (12) meses... firmeza... declaracion..."
        ),
        secondary_topics=("beneficio_auditoria",),
    )
    result = detect_topic_misalignment(
        _request("beneficio_auditoria"), _bundle(article)
    )
    assert result["misaligned"] is False
    assert result["reason"] == "secondary_topic_match"
    assert "689-3" in result["secondary_topic_matches"]
    assert result["articles_top_topic"] == "beneficio_auditoria"


# ────────────────────────────────────────────────────────────────────────────
# (b) Articles without secondary_topics fall through to lexical scoring
# (pre-§1.A behavior preserved). This guards against accidentally over-broadening
# the gate when no curation has been applied.
# ────────────────────────────────────────────────────────────────────────────


def test_no_secondary_topics_falls_through_to_lexical_path() -> None:
    article = _article(
        node_key="103",
        title="EXENCIÓN DE IVA.",
        excerpt="iva ventas iva impuesto sobre las ventas iva tarifa iva exencion iva",
        secondary_topics=(),
    )
    # Router says laboral, articles all say iva → misaligned (lexical).
    result = detect_topic_misalignment(_request("laboral"), _bundle(article))
    # The default reason path isn't 'secondary_topic_match' — confirms the
    # short-circuit didn't fire on the empty secondary_topics tuple.
    assert result["reason"] != "secondary_topic_match"


# ────────────────────────────────────────────────────────────────────────────
# (c) Multi-article bundle — even one article with the matching secondary
# topic flips the verdict. The other articles' lexical content doesn't matter.
# ────────────────────────────────────────────────────────────────────────────


def test_one_matching_secondary_among_many_flips_verdict() -> None:
    a1 = _article(
        node_key="240",
        title="TARIFA GENERAL DE RENTA.",
        excerpt="tarifa renta personas juridicas 35% renta tarifa renta",
        secondary_topics=(),  # no curation
    )
    a2 = _article(
        node_key="689-3",
        title="BENEFICIO DE AUDITORÍA.",
        excerpt="firmeza declaracion contribuyente beneficio",
        secondary_topics=("beneficio_auditoria",),
    )
    a3 = _article(
        node_key="714",
        title="FIRMEZA GENERAL.",
        excerpt="firmeza declaracion 3 anos",
        secondary_topics=(),
    )
    result = detect_topic_misalignment(
        _request("beneficio_auditoria"), _bundle(a1, a2, a3)
    )
    assert result["misaligned"] is False
    assert result["reason"] == "secondary_topic_match"
    assert result["secondary_topic_matches"] == ["689-3"]


# ────────────────────────────────────────────────────────────────────────────
# (d) Router topic NOT in any secondary_topics — short-circuit doesn't fire.
# Lexical path runs. This is the contamination guard preserved.
# ────────────────────────────────────────────────────────────────────────────


def test_router_topic_not_in_any_secondary_falls_through() -> None:
    a = _article(
        node_key="689-3",
        title="BENEFICIO DE AUDITORÍA.",
        excerpt="iva iva iva iva iva",
        secondary_topics=("firmeza_declaraciones",),  # different secondary
    )
    # Router says laboral; secondary says firmeza_declaraciones; lexical says iva
    # → no short-circuit; lexical path can flag misaligned.
    result = detect_topic_misalignment(_request("laboral"), _bundle(a))
    assert result["reason"] != "secondary_topic_match"


# ────────────────────────────────────────────────────────────────────────────
# (e) No primary articles — pre-existing path unchanged.
# ────────────────────────────────────────────────────────────────────────────


def test_no_primary_articles_returns_no_primary_articles_reason() -> None:
    result = detect_topic_misalignment(
        _request("beneficio_auditoria"), _bundle()
    )
    assert result["misaligned"] is False
    assert result["reason"] == "no_primary_articles"


# ────────────────────────────────────────────────────────────────────────────
# (f) Empty router topic — pre-existing path unchanged.
# ────────────────────────────────────────────────────────────────────────────


def test_no_router_topic_short_circuits_first() -> None:
    a = _article(
        node_key="689-3",
        title="BENEFICIO DE AUDITORÍA.",
        excerpt="...",
        secondary_topics=("beneficio_auditoria",),
    )
    result = detect_topic_misalignment(_request(""), _bundle(a))
    assert result["misaligned"] is False
    assert result["reason"] == "no_router_topic"
