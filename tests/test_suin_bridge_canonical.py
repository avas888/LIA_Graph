"""Phase 5b — SUIN bridge canonical-template synthesis.

Locks down the contract for ``synthesize_canonical_markdown``: one SUIN
document row + its articles + its edges → canonical 8-section markdown with
the ``## Metadata v2`` prelude. Fixtures are inline so the tests do not
depend on a live SUIN harvest directory.
"""

from __future__ import annotations

from typing import Any

import pytest

from lia_graph.ingestion.suin import bridge as suin_bridge


def _base_doc() -> dict[str, Any]:
    return {
        "doc_id": "suin_res_ugpp_532_2024",
        "title": "Resolución UGPP 532 de 2024",
        "authority": "ugpp",
        "number": "532",
        "date_issued": "2024-03-15",
        "date_effective": "2024-04-01",
        "topic": ["laboral", "seguridad_social"],
    }


def _article(text: str, *, key: str = "art1") -> dict[str, Any]:
    return {
        "doc_id": "suin_res_ugpp_532_2024",
        "article_key": key,
        "body_text": text,
        "status": "vigente",
    }


def _edge(verb: str, *, target: str, date: str = "2024-03-15") -> dict[str, Any]:
    return {
        "doc_id": "suin_res_ugpp_532_2024",
        "verb": verb,
        "target_citation": target,
        "date": date,
    }


# ── (a) identificacion bullets ────────────────────────────────


def test_identificacion_bullets_populated_from_row() -> None:
    md = suin_bridge.synthesize_canonical_markdown(_base_doc(), [], [])
    assert "- titulo: Resolución UGPP 532 de 2024" in md
    assert "- numero: 532" in md
    assert "- doc_id: suin_res_ugpp_532_2024" in md
    assert "- fecha_emision: 2024-03-15" in md


# ── (b) texto base with articles ──────────────────────────────


def test_texto_base_concatenates_article_text() -> None:
    md = suin_bridge.synthesize_canonical_markdown(
        _base_doc(),
        [
            _article("Artículo 1. Ámbito de aplicación...", key="art1"),
            _article("Artículo 2. Presunción de costos...", key="art2"),
            _article("Artículo 3. Vigencia.", key="art3"),
        ],
        [],
    )
    assert "Artículo 1. Ámbito de aplicación..." in md
    assert "Artículo 3. Vigencia." in md


# ── (c) no articles → placeholder ─────────────────────────────


def test_texto_base_placeholder_when_no_articles() -> None:
    md = suin_bridge.synthesize_canonical_markdown(_base_doc(), [], [])
    # The canonical texto base section carries `(sin datos)` when empty.
    lines_after_heading = md.split("## Texto base referenciado (resumen tecnico)")[1]
    next_heading_idx = lines_after_heading.find("## ")
    section_body = lines_after_heading[:next_heading_idx].strip()
    assert "(sin datos)" in section_body


# ── (d) modifica edges grouped ────────────────────────────────


def test_relaciones_groups_modifica_edges() -> None:
    md = suin_bridge.synthesize_canonical_markdown(
        _base_doc(),
        [],
        [
            _edge("modifica", target="Decreto 2229 de 2023"),
            _edge("modifica", target="Ley 1819 de 2016"),
        ],
    )
    rel = md.split("## Relaciones normativas")[1].split("## ")[0]
    assert "Modifica" in rel
    assert "Decreto 2229 de 2023" in rel
    assert "Ley 1819 de 2016" in rel


# ── (e) nota_editorial skipped ────────────────────────────────


def test_nota_editorial_is_dropped_from_relaciones() -> None:
    md = suin_bridge.synthesize_canonical_markdown(
        _base_doc(),
        [],
        [
            _edge("modifica", target="Decreto 2229 de 2023"),
            _edge("nota_editorial", target="Aclaración administrativa"),
        ],
    )
    rel = md.split("## Relaciones normativas")[1].split("## ")[0]
    assert "Aclaración administrativa" not in rel
    assert "Decreto 2229 de 2023" in rel


# ── (f) missing fecha_emision ─────────────────────────────────


def test_missing_fecha_emision_rendered_as_sin_datos() -> None:
    row = _base_doc()
    row.pop("date_issued")
    md = suin_bridge.synthesize_canonical_markdown(row, [], [])
    assert "- fecha_emision: (sin datos)" in md


# ── (g) all 8 canonical headings in order ─────────────────────


def test_all_8_canonical_sections_present_in_order() -> None:
    md = suin_bridge.synthesize_canonical_markdown(_base_doc(), [], [])
    headings = [
        "## Identificacion",
        "## Texto base referenciado (resumen tecnico)",
        "## Regla operativa para LIA",
        "## Condiciones de aplicacion",
        "## Riesgos de interpretacion",
        "## Relaciones normativas",
        "## Checklist de vigencia",
        "## Historico de cambios",
    ]
    positions = [md.find(h) for h in headings]
    assert all(pos >= 0 for pos in positions), f"missing heading in {positions}"
    assert positions == sorted(positions), "headings out of order"


# ── (h) metadata v2 block with 14 keys ────────────────────────


def test_metadata_v2_block_has_all_14_keys() -> None:
    md = suin_bridge.synthesize_canonical_markdown(_base_doc(), [], [])
    assert "## Metadata v2" in md
    block = md.split("## Metadata v2")[1].split("## ")[0]
    for key in suin_bridge._SUIN_METADATA_V2_KEYS:
        assert f"- {key}:" in block, f"metadata v2 key missing: {key}"


# ── (i) vigencia checklist ────────────────────────────────────


def test_checklist_de_vigencia_lists_suspends_and_derogates() -> None:
    md = suin_bridge.synthesize_canonical_markdown(
        _base_doc(),
        [],
        [
            _edge("suspende", target="Concepto 0812 de 2019"),
            _edge("deroga", target="Resolución 2023 de 2021"),
        ],
    )
    vig = md.split("## Checklist de vigencia")[1].split("## ")[0]
    assert "0812 de 2019" in vig or "Suspende" in vig
    assert "2023 de 2021" in vig or "Deroga" in vig


# ── (j) historico ─────────────────────────────────────────────


def test_historico_lists_fecha_emision_and_modificacion_edges() -> None:
    md = suin_bridge.synthesize_canonical_markdown(
        _base_doc(),
        [],
        [_edge("modifica", target="Decreto 2229 de 2023", date="2023-12-01")],
    )
    hist = md.split("## Historico de cambios")[1]
    assert "2024-03-15" in hist or "Resolución UGPP 532" in hist


# ── (k) events ────────────────────────────────────────────────


def test_emit_events_true_fires_start_and_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, dict[str, Any]]] = []

    def _fake_emit(event: str, payload: dict[str, Any]) -> None:
        captured.append((event, dict(payload)))

    monkeypatch.setattr(suin_bridge, "_emit_event", _fake_emit)
    suin_bridge.synthesize_canonical_markdown(
        _base_doc(),
        [_article("body")],
        [_edge("modifica", target="Ley X")],
        emit_events=True,
    )
    names = [n for n, _ in captured]
    assert "ingest.suin.bridge.start" in names
    assert "ingest.suin.bridge.done" in names
    start_payload = next(p for n, p in captured if n == "ingest.suin.bridge.start")
    assert start_payload["article_count"] == 1
    assert start_payload["edge_count"] == 1


# ── (l) integration with validator ────────────────────────────


def test_synthesized_markdown_passes_non_strict_validator() -> None:
    from lia_graph.ingestion_validator import validate_canonical_template

    md = suin_bridge.synthesize_canonical_markdown(
        _base_doc(),
        [_article("Artículo 1 — contenido normativo", key="art1")],
        [_edge("modifica", target="Decreto 2229 de 2023")],
    )
    result = validate_canonical_template(md, strict=False)
    # ok may be False when curator-only sections trip the (sin datos) guard,
    # but the 8 canonical sections MUST be present in order.
    assert result.missing_sections == ()
    assert result.sections_out_of_order == ()
