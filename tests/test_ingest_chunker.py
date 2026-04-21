"""Tests for ``lia_graph.ingestion_chunker`` (Phase 1.6 of ingestfixv1).

Covers:
- canonical 8-section document → 8 chunks tagged per ``_SECTION_TYPE_MAP``,
- the ``## Metadata v2`` block emits as a ``metadata`` chunk,
- ``(sin datos)`` placeholder sections are skipped,
- preamble above the first H2 becomes a ``metadata`` chunk with heading="",
- non-canonical headings fall back to ``metadata``,
- accent-insensitive heading matching (``## Identificación``),
- long sections (>1600 chars) split on double-newline boundaries,
- ``position`` is strictly increasing and 0-based,
- ``section_type_distribution`` counts correctly,
- ``emit_events=True`` fires exactly two trace events.

All fixtures live inline — we never touch the real corpus.
"""

from __future__ import annotations

import pytest

from lia_graph import ingestion_chunker as chunker_mod
from lia_graph.ingestion_chunker import (
    Chunk,
    _SECTION_TYPE_MAP,
    chunk_canonical_markdown,
    section_type_distribution,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _canonical_doc() -> str:
    """A minimally-populated canonical 8-section doc (no Metadata v2).

    Each section body is padded above the 80-char default ``min_chars``
    so every canonical section survives filtering.
    """
    return (
        "## Identificacion\n"
        "- titulo: Ley de prueba tributaria con nombre largo suficiente\n"
        "- autoridad: Congreso de la Republica de Colombia\n"
        "- numero: 99\n"
        "- fecha_emision: 2024-01-01\n"
        "- fecha_vigencia: 2024-01-01\n"
        "- ambito_tema: tributario\n"
        "- doc_id: LEY-99-2024\n"
        "\n"
        "## Texto base referenciado (resumen tecnico)\n"
        "El articulo 1 establece la obligacion tributaria sustancial para personas "
        "juridicas. La norma aplica a todos los contribuyentes del regimen ordinario "
        "y fija la tarifa general del impuesto sobre la renta.\n"
        "\n"
        "## Regla operativa para LIA\n"
        "Al redactar la respuesta: cita el articulo 1, explica el calculo paso a paso y "
        "recuerda verificar la UVT vigente del ejercicio fiscal correspondiente.\n"
        "\n"
        "## Condiciones de aplicacion\n"
        "Aplica a personas juridicas con ingresos brutos anuales superiores a 3500 UVT "
        "y que pertenezcan al regimen ordinario del impuesto sobre la renta.\n"
        "\n"
        "## Riesgos de interpretacion\n"
        "La DIAN suele exigir pruebas contables; evitar interpretaciones expansivas "
        "del articulo y confirmar siempre con doctrina vigente antes de emitir concepto.\n"
        "\n"
        "## Relaciones normativas\n"
        "- modifica: Ley 1819 de 2016 articulo 240\n"
        "- reglamentada_por: Decreto 1625 de 2016 Libro 1 Parte 2\n"
        "- concordante_con: Estatuto Tributario articulo 240\n"
        "\n"
        "## Checklist de vigencia\n"
        "- vigencia: vigente al 2026-03-01 segun consulta en Secretaria Juridica\n"
        "- verificado_en: 2026-03-01 por el equipo de curaduria normativa\n"
        "\n"
        "## Historico de cambios\n"
        "2024-01-01 emision original publicada en el Diario Oficial numero 52500.\n"
        "2025-06-10 modificada parcialmente por la Ley 2200 articulo 12.\n"
    )


def _canonical_doc_with_metadata_v2() -> str:
    return (
        "## Metadata v2\n"
        "- version_canonical_template: 1\n"
        "- coercion_method: native\n"
        "- coercion_confidence: 1.00\n"
        "- source_tier: primary\n"
        "- authority_level: ley\n"
        "- parse_strategy: native\n"
        "- source_type: ley\n"
        "- corpus_family: tributario\n"
        "- vocabulary_labels: \n"
        "- review_priority: normal\n"
        "- country_scope: CO\n"
        "- language: es\n"
        "- generated_at: 2026-04-20\n"
        "- source_relative_path: docs/ley-99.md\n"
        "\n"
        + _canonical_doc()
    )


# ---------------------------------------------------------------------------
# (a) canonical 8 sections → 8 chunks, types match _SECTION_TYPE_MAP
# ---------------------------------------------------------------------------


def test_canonical_doc_produces_eight_chunks_in_order():
    chunks = chunk_canonical_markdown(_canonical_doc())

    # 8 canonical sections all have bodies above min_chars.
    assert len(chunks) == 8

    expected = [
        ("Identificacion", "metadata"),
        ("Texto base referenciado (resumen tecnico)", "vigente"),
        ("Regla operativa para LIA", "operational"),
        ("Condiciones de aplicacion", "operational"),
        ("Riesgos de interpretacion", "operational"),
        ("Relaciones normativas", "metadata"),
        ("Checklist de vigencia", "metadata"),
        ("Historico de cambios", "historical"),
    ]
    actual = [(c.section_heading, c.section_type) for c in chunks]
    assert actual == expected


# ---------------------------------------------------------------------------
# (b) Metadata v2 block emits as metadata
# ---------------------------------------------------------------------------


def test_metadata_v2_block_emits_as_metadata_chunk():
    chunks = chunk_canonical_markdown(_canonical_doc_with_metadata_v2())

    # First chunk should be Metadata v2, typed as metadata.
    assert chunks[0].section_heading == "Metadata v2"
    assert chunks[0].section_type == "metadata"
    # 8 canonical + 1 metadata v2 = 9 chunks total.
    assert len(chunks) == 9


# ---------------------------------------------------------------------------
# (c) "(sin datos)" sections are skipped
# ---------------------------------------------------------------------------


def test_sin_datos_sections_are_skipped():
    doc = (
        "## Identificacion\n"
        "- titulo: X\n- autoridad: Y\n- numero: 1\n- fecha_emision: 2024-01-01\n"
        "- fecha_vigencia: 2024-01-01\n- ambito_tema: Z\n- doc_id: DOC-1\n"
        "\n"
        "## Texto base referenciado (resumen tecnico)\n"
        "(sin datos)\n"
        "\n"
        "## Regla operativa para LIA\n"
        "(sin datos)\n"
        "\n"
        "## Historico de cambios\n"
        "2024-01-01 emision original; hay al menos cien caracteres en esta seccion para "
        "asegurar que supera el piso minimo de caracteres configurado por defecto.\n"
    )
    chunks = chunk_canonical_markdown(doc)
    headings = [c.section_heading for c in chunks]
    assert "Texto base referenciado (resumen tecnico)" not in headings
    assert "Regla operativa para LIA" not in headings
    assert "Identificacion" in headings
    assert "Historico de cambios" in headings


# ---------------------------------------------------------------------------
# (d) preamble above first H2 → metadata chunk with heading=""
# ---------------------------------------------------------------------------


def test_preamble_above_first_h2_emits_as_metadata():
    doc = (
        "Este documento fue generado automaticamente por la tuberia de ingestion "
        "y contiene contenido suficientemente largo para superar el piso minimo "
        "de caracteres por omision.\n"
        "\n"
        + _canonical_doc()
    )
    chunks = chunk_canonical_markdown(doc)
    assert chunks[0].section_heading == ""
    assert chunks[0].section_type == "metadata"
    assert "generado automaticamente" in chunks[0].text


# ---------------------------------------------------------------------------
# (e) non-canonical heading → metadata default
# ---------------------------------------------------------------------------


def test_non_canonical_heading_defaults_to_metadata():
    doc = (
        "## Notas del editor\n"
        "Este contenido no pertenece al template canonico pero debe clasificarse "
        "como metadata por defecto dado que no corresponde a ninguna seccion conocida.\n"
    )
    chunks = chunk_canonical_markdown(doc)
    assert len(chunks) == 1
    assert chunks[0].section_heading == "Notas del editor"
    assert chunks[0].section_type == "metadata"


# ---------------------------------------------------------------------------
# (f) accent-insensitive matching: "## Identificación" → metadata
# ---------------------------------------------------------------------------


def test_accent_insensitive_heading_matches_canonical_map():
    doc = (
        "## Identificación\n"
        "- titulo: Con acentos\n- autoridad: Congreso\n- numero: 1\n"
        "- fecha_emision: 2024-01-01\n- fecha_vigencia: 2024-01-01\n"
        "- ambito_tema: tema\n- doc_id: DOC-1\n"
    )
    chunks = chunk_canonical_markdown(doc)
    assert len(chunks) == 1
    assert chunks[0].section_type == "metadata"
    # Heading echoes the input exactly (accents preserved).
    assert chunks[0].section_heading == "Identificación"


# ---------------------------------------------------------------------------
# (g) long section (>1600 chars) splits on double-newline boundaries
# ---------------------------------------------------------------------------


def test_long_section_splits_on_paragraph_boundaries():
    paragraph = "X" * 500
    body = "\n\n".join([paragraph] * 5)  # 5 paras of 500 chars = ~2500+ chars
    doc = f"## Texto base referenciado (resumen tecnico)\n{body}\n"
    chunks = chunk_canonical_markdown(doc)

    # Must split into more than one piece.
    assert len(chunks) > 1
    # Every piece keeps the same section_type and heading.
    for chunk in chunks:
        assert chunk.section_type == "vigente"
        assert chunk.section_heading == "Texto base referenciado (resumen tecnico)"
    # No piece should substantially exceed the soft cap (1600) — we
    # allow up to 1 paragraph worth of overflow because we never slice
    # inside a paragraph.
    assert all(len(chunk.text) <= 1600 + 500 for chunk in chunks)


# ---------------------------------------------------------------------------
# (h) position is strictly increasing and 0-based
# ---------------------------------------------------------------------------


def test_position_is_monotonic_and_zero_based():
    chunks = chunk_canonical_markdown(_canonical_doc_with_metadata_v2())
    positions = [c.position for c in chunks]
    assert positions[0] == 0
    assert positions == list(range(len(chunks)))


# ---------------------------------------------------------------------------
# (i) section_type_distribution returns correct counts
# ---------------------------------------------------------------------------


def test_section_type_distribution_counts_correctly():
    chunks = chunk_canonical_markdown(_canonical_doc())
    dist = section_type_distribution(chunks)
    assert dist["vigente"] == 1
    assert dist["operational"] == 3
    assert dist["metadata"] == 3  # Identificacion + Relaciones + Checklist
    assert dist["historical"] == 1
    # Distribution sum must equal chunk count.
    assert sum(dist.values()) == len(chunks)


# ---------------------------------------------------------------------------
# (j) emit_events=True fires start + done trace events
# ---------------------------------------------------------------------------


def test_emit_events_true_calls_emit_event_twice(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def _capture(event_type: str, payload: dict) -> None:
        calls.append((event_type, payload))

    monkeypatch.setattr(chunker_mod, "emit_event", _capture)

    chunks = chunk_canonical_markdown(
        _canonical_doc(),
        filename="ley-99.md",
        emit_events=True,
    )

    assert len(calls) == 2
    assert calls[0][0] == "ingest.chunk.start"
    assert calls[0][1]["filename"] == "ley-99.md"
    assert calls[0][1]["char_count"] > 0
    assert calls[1][0] == "ingest.chunk.done"
    assert calls[1][1]["filename"] == "ley-99.md"
    assert calls[1][1]["chunk_count"] == len(chunks)
    assert calls[1][1]["section_type_distribution"] == section_type_distribution(chunks)


# ---------------------------------------------------------------------------
# Extra (defensive): emit_events=False stays silent by default
# ---------------------------------------------------------------------------


def test_emit_events_false_stays_silent(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def _capture(event_type: str, payload: dict) -> None:
        calls.append((event_type, payload))

    monkeypatch.setattr(chunker_mod, "emit_event", _capture)

    chunk_canonical_markdown(_canonical_doc())
    assert calls == []


# ---------------------------------------------------------------------------
# Extra: Chunk is frozen/immutable
# ---------------------------------------------------------------------------


def test_chunk_is_frozen_dataclass():
    chunks = chunk_canonical_markdown(_canonical_doc())
    with pytest.raises(Exception):
        chunks[0].text = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Extra: _SECTION_TYPE_MAP covers all 8 canonical headings
# ---------------------------------------------------------------------------


def test_section_type_map_covers_all_canonical_headings():
    from lia_graph.ingestion_section_coercer import CANONICAL_SECTIONS
    from lia_graph.ingestion_chunker import _normalize_heading  # type: ignore[attr-defined]

    # Every canonical heading resolves to a known type (no "metadata"
    # fallback for anything except Identificacion / Relaciones /
    # Checklist — which IS metadata legitimately).
    for heading in CANONICAL_SECTIONS:
        assert _normalize_heading(heading) in _SECTION_TYPE_MAP


# ---------------------------------------------------------------------------
# Extra: empty / whitespace-only input returns []
# ---------------------------------------------------------------------------


def test_empty_input_returns_empty_list():
    assert chunk_canonical_markdown("") == []
    assert chunk_canonical_markdown("   \n\n  ") == []
