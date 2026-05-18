"""fix_v25_may.md P13 — práctica topic-filter tests."""

from __future__ import annotations

from lia_graph.pipeline_d.answer_synthesis_practica import (
    filter_practica_chunks_by_topic,
)
from lia_graph.pipeline_d.off_topic_content_strip import strip_off_topic_bullets
from lia_graph.practica.shared import PracticaChunkRuntime


def _chunk(topic_key: str | None) -> PracticaChunkRuntime:
    return PracticaChunkRuntime(
        doc_id=f"d_{topic_key or 'none'}",
        relative_path="p",
        source_label="s",
        authority="a",
        chunk_text="t",
        retrieval_score=0.5,
        topic_key=topic_key,
    )


def test_filter_drops_off_topic_chunks():
    chunks = (
        _chunk("costos_deducciones_renta"),
        _chunk("tarifas_renta_y_ttd"),  # zona franca
        _chunk("zonas_francas"),
    )
    kept, diag = filter_practica_chunks_by_topic(
        chunks, frozenset({"costos_deducciones_renta"})
    )
    assert len(kept) == 1
    assert kept[0].topic_key == "costos_deducciones_renta"
    assert diag["chunks_dropped"] == 2


def test_filter_keeps_chunks_with_no_topic_key():
    chunks = (_chunk(None), _chunk(""), _chunk("costos_deducciones_renta"))
    kept, diag = filter_practica_chunks_by_topic(
        chunks, frozenset({"costos_deducciones_renta"})
    )
    assert len(kept) == 3
    assert diag["chunks_dropped"] == 0


def test_filter_noop_when_allowed_topics_empty():
    chunks = (_chunk("tarifas_renta_y_ttd"),)
    kept, _ = filter_practica_chunks_by_topic(chunks, None)
    assert kept == chunks
    kept2, _ = filter_practica_chunks_by_topic(chunks, frozenset())
    assert kept2 == chunks


def test_strip_drops_zona_franca_bullets_in_non_zona_franca_question():
    text = (
        "**Recomendaciones Prácticas**\n"
        "- Verifique RUT del proveedor.\n"
        "- Tras la Ley 2277/2022 art. 11, los usuarios industriales (UIB/UIS) "
        "de zona franca aplican doble tarifa.\n"
        "- Plan de internacionalización con MinCIT.\n"
    )
    cleaned, drops = strip_off_topic_bullets(text, "documento soporte deducible")
    assert "zona franca" not in cleaned
    assert "MinCIT" not in cleaned
    assert "Verifique RUT" in cleaned
    assert any(d["family"] == "zona_franca" for d in drops)


def test_strip_keeps_zona_franca_bullets_when_question_mentions_it():
    text = "- Zona franca con UIB/UIS aplica doble tarifa.\n"
    cleaned, drops = strip_off_topic_bullets(
        text, "Cómo declara una sociedad en zona franca su renta?"
    )
    assert "Zona franca" in cleaned
    assert drops == []
