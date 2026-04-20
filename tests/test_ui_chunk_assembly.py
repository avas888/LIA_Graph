"""Unit tests for `lia_graph.ui_chunk_assembly`.

Locks in the chunk-to-markdown reassembly contract the citation-profile
modal depends on when the serving host can't see the original knowledge-base
file (which is every mode that isn't local `npm run dev` reading artifacts):

  * the `[authority | topic | path]` decoration on the first line is stripped
  * the chunker's bare-heading-prefix pattern (`Texto normativo vigente`
    inlined before every paragraph) is re-emitted as `## Heading` markdown
  * chunk-overlap duplicates (same paragraph appearing as the last segment
    of chunk N and the first segment of chunk N+1) are dropped
  * body lines that merely *start with* a heading label don't falsely trip
    the heading detector
"""

from __future__ import annotations

from lia_graph.ui_chunk_assembly import (
    _match_heading_label,
    _reconstruct_chunk_markdown,
    _strip_chunk_context_prefix,
)


def test_strip_context_prefix_removes_decoration_line() -> None:
    stored = "[DIAN | Renta | normograma/et_art_290.md]\nEl Artículo 290 regula el régimen de transición."
    assert _strip_chunk_context_prefix(stored) == "El Artículo 290 regula el régimen de transición."


def test_strip_context_prefix_passthrough_when_no_decoration() -> None:
    stored = "Primera línea normal.\nSegunda línea."
    assert _strip_chunk_context_prefix(stored) == stored


def test_strip_context_prefix_handles_empty_and_whitespace() -> None:
    assert _strip_chunk_context_prefix("") == ""
    assert _strip_chunk_context_prefix(None) == ""


def test_strip_context_prefix_only_drops_first_line() -> None:
    stored = "[a | b | c]\n[also | looks | like]\nbody"
    # Only the first decoration-matching line is removed.
    assert _strip_chunk_context_prefix(stored) == "[also | looks | like]\nbody"


def test_match_heading_label_exact_and_prefix() -> None:
    labels = ("texto normativo vigente", "histórico de cambios", "notas")
    assert _match_heading_label("texto normativo vigente", labels) == "texto normativo vigente"
    assert _match_heading_label("notas adicionales", labels) == "notas"
    assert _match_heading_label("notas(resumen)", labels) == "notas"


def test_match_heading_label_rejects_body_paragraphs() -> None:
    labels = ("texto normativo vigente",)
    # Sentence terminator → not a heading.
    assert _match_heading_label("texto normativo vigente.", labels) is None
    # Too long → definitely a body paragraph.
    assert _match_heading_label("texto normativo vigente con detalles adicionales " + "x" * 200, labels) is None


def test_match_heading_label_empty_input() -> None:
    assert _match_heading_label("", ("x",)) is None


def test_reconstruct_chunk_markdown_emits_headings_and_dedup(monkeypatch) -> None:
    # Fixture: the chunker inlines the section label before every paragraph.
    # Reassembly must produce `## Heading` and collapse repeated labels,
    # plus drop the chunk-overlap duplicate paragraph at the boundary.
    monkeypatch.setattr(
        "lia_graph.ingestion_chunker._SECTION_TYPE_MAP",
        (
            ("Texto normativo vigente", "texto_vigente"),
            ("Histórico de cambios", "historico"),
        ),
    )

    chunk_a = (
        "Texto normativo vigente\n"
        "Párrafo uno sobre el régimen.\n"
        "Texto normativo vigente\n"
        "Párrafo dos sobre la Ley 1819."
    )
    # Chunk B starts with the overlap duplicate of Chunk A's last paragraph,
    # then introduces a brand-new section.
    chunk_b = (
        "Texto normativo vigente\n"
        "Párrafo dos sobre la Ley 1819.\n"
        "Histórico de cambios\n"
        "En 2016 se adicionó el capítulo."
    )

    result = _reconstruct_chunk_markdown([chunk_a, chunk_b])
    assert "## Texto normativo vigente" in result
    assert "## Histórico de cambios" in result
    # Repeated inline heading collapsed — only one `##` per section.
    assert result.count("## Texto normativo vigente") == 1
    assert result.count("## Histórico de cambios") == 1
    # Paragraph dedup across chunk boundary.
    assert result.count("Párrafo dos sobre la Ley 1819") == 1
    # Ordering preserved.
    assert result.index("Párrafo uno") < result.index("Párrafo dos")
    assert result.index("Párrafo dos") < result.index("## Histórico")


def test_reconstruct_chunk_markdown_passthrough_when_no_heading_map(monkeypatch) -> None:
    monkeypatch.setattr("lia_graph.ingestion_chunker._SECTION_TYPE_MAP", tuple())
    bodies = ["Línea uno.", "Línea dos."]
    result = _reconstruct_chunk_markdown(bodies)
    assert "Línea uno." in result
    assert "Línea dos." in result
    assert "##" not in result


def test_reconstruct_chunk_markdown_handles_empty_input(monkeypatch) -> None:
    monkeypatch.setattr(
        "lia_graph.ingestion_chunker._SECTION_TYPE_MAP",
        (("Texto normativo vigente", "texto_vigente"),),
    )
    assert _reconstruct_chunk_markdown([]) == ""
    assert _reconstruct_chunk_markdown(["", "   "]) == ""


def test_reconstruct_markdown_paragraph_after_heading_is_not_dropped(monkeypatch) -> None:
    # Regression guard: a paragraph under section B that happens to match
    # an earlier paragraph under section A must NOT be dropped by the
    # dedup state — the heading boundary must reset it.
    monkeypatch.setattr(
        "lia_graph.ingestion_chunker._SECTION_TYPE_MAP",
        (
            ("Texto normativo vigente", "texto_vigente"),
            ("Histórico de cambios", "historico"),
        ),
    )
    body = (
        "Texto normativo vigente\n"
        "Comentario compartido.\n"
        "Histórico de cambios\n"
        "Comentario compartido."
    )
    result = _reconstruct_chunk_markdown([body])
    # Appears once under each heading.
    assert result.count("Comentario compartido.") == 2
