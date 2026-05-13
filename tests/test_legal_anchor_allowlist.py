"""fix_v14_may §3 — tests for the legal-anchor topic-allowlist gate.

The gate filters items rendered by `build_legal_anchor_lines` so that
articles whose `art:<num>` form is not in the routed topic's
`allowed_prefixes` (from `config/topic_norm_allowlist.json`) are
dropped before render. Modes: `off | shadow | enforce`. Default
`shadow` at landing — emit diagnostic but do not filter.

Test cases include verbatim panel-rejection examples from the
2026-05-13 panel-judge (e.g. depreciación → Arts. 121-124 exterior,
PT → Art. 240, anticipo → Arts. 100-102 renta vitalicia).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_synthesis_sections import (
    _legal_anchor_gate_mode,
    _legal_anchor_topic_for_request,
    build_legal_anchor_lines,
)
from lia_graph.pipeline_d.contracts import GraphEvidenceItem


def _item(node_key: str, title: str) -> GraphEvidenceItem:
    """Build a minimal GraphEvidenceItem stub matching the contract."""
    return GraphEvidenceItem(
        node_kind="article",
        node_key=node_key,
        title=title,
        excerpt=f"excerpt of {title}",
        source_path=None,
        score=1.0,
        hop_distance=0,
        why="test",
        relation_path=(),
        secondary_topics=(),
    )


def _request(topic: str = "declaracion_renta", message: str = "test") -> PipelineCRequest:
    return PipelineCRequest(message=message, pais="colombia", topic=topic)


# ---------------------------------------------------------------------------
# Gate mode resolution
# ---------------------------------------------------------------------------


def test_gate_mode_default_is_shadow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIA_LEGAL_ANCHOR_GATE_MODE", raising=False)
    assert _legal_anchor_gate_mode() == "shadow"


def test_gate_mode_enforce(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_LEGAL_ANCHOR_GATE_MODE", "enforce")
    assert _legal_anchor_gate_mode() == "enforce"


def test_gate_mode_off(monkeypatch: pytest.MonkeyPatch) -> None:
    for value in ("off", "0", "false", "no", "disabled"):
        monkeypatch.setenv("LIA_LEGAL_ANCHOR_GATE_MODE", value)
        assert _legal_anchor_gate_mode() == "off", f"value {value!r} should map to off"


def test_gate_mode_unknown_value_defaults_shadow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_LEGAL_ANCHOR_GATE_MODE", "potato")
    assert _legal_anchor_gate_mode() == "shadow"


# ---------------------------------------------------------------------------
# Topic resolution from request
# ---------------------------------------------------------------------------


def test_topic_resolved_from_request() -> None:
    req = _request(topic="declaracion_renta")
    assert _legal_anchor_topic_for_request(req) == "declaracion_renta"


def test_topic_none_when_request_has_no_topic() -> None:
    req = _request(topic="")
    assert _legal_anchor_topic_for_request(req) is None


# ---------------------------------------------------------------------------
# Shadow mode — emit diagnostic, do NOT filter
# ---------------------------------------------------------------------------


def test_shadow_mode_keeps_all_items_even_when_off_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIA_LEGAL_ANCHOR_GATE_MODE", "shadow")
    # declaracion_renta allowlist does NOT include 100-102 (renta vitalicia).
    bad_items = (
        _item("100", "DETERMINACIÓN DE LA RENTA BRUTA EN CONTRATOS DE RENTA VITALICIA"),
        _item("101", "LAS SUMAS PAGADAS COMO RENTA VITALICIA SON DEDUCIBLES"),
    )
    req = _request(topic="declaracion_renta", message="anticipo de renta")
    lines = build_legal_anchor_lines(
        request=req,
        primary_articles=bad_items,
        connected_articles=(),
    )
    # Shadow MUST NOT drop — same as v13 behavior.
    assert any("Art. 100" in line for line in lines)
    assert any("Art. 101" in line for line in lines)


# ---------------------------------------------------------------------------
# Off mode — identical to v13 behavior (no gate)
# ---------------------------------------------------------------------------


def test_off_mode_passes_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_LEGAL_ANCHOR_GATE_MODE", "off")
    items = (
        _item("100", "RENTA VITALICIA"),
        _item("999", "ARTÍCULO INVENTADO"),  # not in any allowlist
    )
    req = _request(topic="declaracion_renta")
    lines = build_legal_anchor_lines(
        request=req,
        primary_articles=items,
        connected_articles=(),
    )
    assert len(lines) == 2  # both kept


# ---------------------------------------------------------------------------
# Enforce mode — verbatim panel-rejection cases
# ---------------------------------------------------------------------------


def test_enforce_drops_renta_vitalicia_for_anticipo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Panel case G18 / Práctica Q18: query about anticipo de renta got
    anclaje legal citando Arts. 100, 101, 102 (renta vitalicia + fiducia).
    These articles are intentionally NOT in declaracion_renta allowlist.
    """
    monkeypatch.setenv("LIA_LEGAL_ANCHOR_GATE_MODE", "enforce")
    items = (
        _item("100", "RENTA VITALICIA"),
        _item("101", "RENTA VITALICIA DEDUCIBLES"),
        _item("102", "FIDUCIA MERCANTIL"),
        _item("807", "ANTICIPO DEL IMPUESTO SOBRE LA RENTA"),  # correct anchor
    )
    req = _request(topic="declaracion_renta", message="anticipo de renta")
    lines = build_legal_anchor_lines(
        request=req,
        primary_articles=items,
        connected_articles=(),
    )
    # 100, 101, 102 must be dropped; 807 (allowed) must survive.
    assert not any("Art. 100 " in line for line in lines)
    assert not any("Art. 101 " in line for line in lines)
    assert not any("Art. 102 " in line for line in lines)
    assert any("Art. 807" in line for line in lines)


def test_enforce_drops_240_235_2_for_pt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Panel case G12 PT umbrales: anclaje incluyó Arts. 240 + 235-2
    (irrelevantes a precios de transferencia). PT allowlist solo 260-* + 124-2.
    """
    monkeypatch.setenv("LIA_LEGAL_ANCHOR_GATE_MODE", "enforce")
    items = (
        _item("240", "TARIFA GENERAL PARA PERSONAS JURÍDICAS"),
        _item("235-2", "RENTAS EXENTAS A PARTIR DEL AÑO GRAVABLE 2019"),
        _item("260-5", "DOCUMENTACIÓN COMPROBATORIA"),  # correct anchor
        _item("260-7", "JURISDICCIONES NO COOPERANTES"),  # correct anchor
    )
    req = _request(topic="precios_de_transferencia")
    lines = build_legal_anchor_lines(
        request=req,
        primary_articles=items,
        connected_articles=(),
    )
    assert not any("Art. 240 " in line for line in lines)
    assert not any("Art. 235-2" in line for line in lines)
    assert any("Art. 260-5" in line for line in lines)
    assert any("Art. 260-7" in line for line in lines)


def test_enforce_drops_124_2_for_parafiscales(monkeypatch: pytest.MonkeyPatch) -> None:
    """Panel case G7 parafiscales: anclaje incluyó Art. 124-2 (pagos a
    jurisdicciones no cooperantes) — totalmente irrelevante a
    parafiscales. Allowlist parafiscales_seguridad_social excluye 124-2.
    """
    monkeypatch.setenv("LIA_LEGAL_ANCHOR_GATE_MODE", "enforce")
    items = (
        _item("124-2", "PAGOS A JURISDICCIONES NO COOPERANTES"),
        _item("108", "APORTES PARAFISCALES SON REQUISITO PARA LA DEDUCCIÓN"),
    )
    req = _request(topic="parafiscales_seguridad_social")
    lines = build_legal_anchor_lines(
        request=req,
        primary_articles=items,
        connected_articles=(),
    )
    assert not any("Art. 124-2" in line for line in lines)
    assert any("Art. 108" in line for line in lines)


def test_enforce_drops_121_124_when_depreciacion_query_topic_is_costos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Panel case Práctica Q3 depreciación: anclaje incluyó Arts. 121-124
    (gastos exterior) + 245 (dividendos extranjeros). Even though the
    router routed to `costos_deducciones_renta` and 121-124 IS in that
    allowlist (legitimately, for services exterior), Art. 245 is NOT.
    """
    monkeypatch.setenv("LIA_LEGAL_ANCHOR_GATE_MODE", "enforce")
    items = (
        _item("121", "DEDUCCIÓN DE GASTOS EN EL EXTERIOR"),
        _item("122", "LIMITACIÓN A LAS DEDUCCIONES"),
        _item("137", "FACULTAD PARA FIJAR VIDA ÚTIL"),  # depreciación canonical
        _item("245", "TARIFA ESPECIAL PARA DIVIDENDOS EXTRANJEROS"),  # off-topic
    )
    req = _request(topic="costos_deducciones_renta")
    lines = build_legal_anchor_lines(
        request=req,
        primary_articles=items,
        connected_articles=(),
    )
    # 121, 122, 137 should all pass (costos allowlist includes them).
    assert any("Art. 137" in line for line in lines)
    # 245 (dividendos extranjeros) is NOT in costos_deducciones_renta allowlist.
    assert not any("Art. 245" in line for line in lines)


def test_enforce_drops_art_1_for_iva_question(monkeypatch: pytest.MonkeyPatch) -> None:
    """Panel case G6 IVA responsables: anclaje incluyó 'Art. 1 ET —
    FORMULARIO 7 — INVERSIÓN EXTRANJERA DIRECTA' (mal-citado). IVA
    allowlist no incluye Art. 1.
    """
    monkeypatch.setenv("LIA_LEGAL_ANCHOR_GATE_MODE", "enforce")
    items = (
        _item("1", "FORMULARIO 7 — INVERSIÓN EXTRANJERA DIRECTA"),
        _item("437", "RESPONSABLES DEL IVA"),
        _item("420", "HECHOS SOBRE LOS QUE RECAE EL IMPUESTO"),
    )
    req = _request(topic="iva")
    lines = build_legal_anchor_lines(
        request=req,
        primary_articles=items,
        connected_articles=(),
    )
    assert not any("Art. 1 —" in line for line in lines)
    assert any("Art. 437" in line for line in lines)
    assert any("Art. 420" in line for line in lines)


# ---------------------------------------------------------------------------
# Safe-by-default — topic without allowlist entry is noop
# ---------------------------------------------------------------------------


def test_enforce_noop_for_topic_without_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    """A topic that has no entry in topic_norm_allowlist.json passes
    everything (safe-by-default; Invariant I5)."""
    monkeypatch.setenv("LIA_LEGAL_ANCHOR_GATE_MODE", "enforce")
    items = (
        _item("100", "RENTA VITALICIA"),
        _item("999", "ARTÍCULO INVENTADO"),
    )
    req = _request(topic="sector_juegos_azar")  # real topic, no allowlist
    lines = build_legal_anchor_lines(
        request=req,
        primary_articles=items,
        connected_articles=(),
    )
    assert len(lines) == 2  # all kept


def test_enforce_noop_when_request_has_no_topic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_LEGAL_ANCHOR_GATE_MODE", "enforce")
    items = (_item("100", "RENTA VITALICIA"),)
    req = _request(topic="")
    lines = build_legal_anchor_lines(
        request=req,
        primary_articles=items,
        connected_articles=(),
    )
    assert len(lines) == 1


# ---------------------------------------------------------------------------
# Connected articles flow through the same gate
# ---------------------------------------------------------------------------


def test_enforce_filters_connected_articles_too(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_LEGAL_ANCHOR_GATE_MODE", "enforce")
    primary = (_item("260-5", "DOCUMENTACIÓN COMPROBATORIA"),)
    connected = (
        _item("240", "TARIFA GENERAL"),
        _item("260-7", "JURISDICCIONES NO COOPERANTES"),
    )
    req = _request(
        topic="precios_de_transferencia",
        # Use a question that will trip `should_surface_connected_anchor`'s
        # keyword overlap check positively.
        message="documentación comprobatoria tarifa jurisdicción no cooperante",
    )
    lines = build_legal_anchor_lines(
        request=req,
        primary_articles=primary,
        connected_articles=connected,
    )
    # 240 should be dropped; 260-5 + 260-7 should pass (if connected
    # gate lets them through).
    assert not any("Art. 240 " in line for line in lines)
    assert any("Art. 260-5" in line for line in lines)
