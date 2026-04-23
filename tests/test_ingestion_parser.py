"""Unit tests for the two-tier parser fallback introduced by ingestionfix_v2.

These lock in the behavior that enables práctica / interpretación docs
(which lack `## Artículo N` statutory headers) to produce retrievable chunks.
See `docs/next/ingestionfix_v2.md` §4 Phase 1.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lia_graph.ingestion.parser import WHOLE_DOC_ARTICLE_KEY, parse_articles


REPO_ROOT = Path(__file__).resolve().parents[1]

CLASSIC_NORMATIVA = (
    REPO_ROOT
    / "knowledge_base"
    / "CORE ya Arriba"
    / "Corpus de Contabilidad"
    / "NORMATIVA"
    / "N-INC-impuesto-nacional-consumo.md"
)
V2_TEMPLATE_NORMATIVA = (
    REPO_ROOT
    / "knowledge_base"
    / "retencion_en_la_fuente"
    / "RET-N03-decreto-572-2025-agentes-bases-tarifas.md"
)
V2_INTERPRETACION = (
    REPO_ROOT
    / "knowledge_base"
    / "retencion_en_la_fuente"
    / "RET-E02-decreto-572-vs-art368-interpretaciones.md"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_classic_normativa_unchanged():
    md = _read(CLASSIC_NORMATIVA)
    arts = parse_articles(md, source_path=str(CLASSIC_NORMATIVA))
    assert len(arts) == 16
    assert all(a.article_number for a in arts)
    assert all(a.article_key == a.article_number for a in arts)
    assert arts[0].article_number == "512-1"
    numbers = {a.article_number for a in arts}
    assert "512-1" in numbers and "512-16" in numbers


def test_v2_template_section_chunks():
    md = _read(V2_TEMPLATE_NORMATIVA)
    arts = parse_articles(md, source_path=str(V2_TEMPLATE_NORMATIVA))
    assert len(arts) == 2
    assert all(a.article_number == "" for a in arts)
    keys = {a.article_key for a in arts}
    assert keys == {"identificacion", "checklist-de-vigencia"}
    for a in arts:
        assert a.body.strip(), "section body must be non-empty after fallback filtering"
        assert a.heading, "section heading must be preserved"


def test_v2_placeholder_only_produces_identificacion_chunk():
    md = _read(V2_INTERPRETACION)
    arts = parse_articles(md, source_path=str(V2_INTERPRETACION))
    assert len(arts) == 1
    assert arts[0].article_key == "identificacion"
    assert arts[0].heading.lower().startswith("identificacion")


def test_empty_markdown_returns_empty():
    assert parse_articles("") == ()
    assert parse_articles("   \n\n   ") == ()


def test_duplicate_section_headings_get_index_suffix():
    md = (
        "## Identificacion\n"
        "Primera copia con contenido real.\n"
        "\n"
        "## Identificacion\n"
        "Segunda copia, también con texto.\n"
    )
    arts = parse_articles(md, source_path="synthetic.md")
    assert len(arts) == 2
    keys = [a.article_key for a in arts]
    assert keys == ["identificacion", "identificacion-1"]


def test_metadata_v2_section_is_skipped():
    md = (
        "## Metadata v2\n"
        "- version: 2\n"
        "- generated_at: 2026-04-23\n"
        "\n"
        "## Identificacion\n"
        "Contenido real de la seccion.\n"
    )
    arts = parse_articles(md, source_path="synthetic.md")
    keys = [a.article_key for a in arts]
    assert keys == ["identificacion"]
    for a in arts:
        assert "metadata" not in a.heading.lower()


def test_article_key_uniqueness_under_fallback():
    """chunk_id = <doc_id>::<article_key> must never collide within a single doc."""
    md = (
        "## Identificacion\nPrimer bloque con datos.\n"
        "\n## Regla operativa\nTexto operativo.\n"
        "\n## Identificacion\nDuplicado con texto.\n"
        "\n## Regla operativa\nSegundo duplicado con texto.\n"
        "\n## Identificacion\nTercero con mas texto.\n"
    )
    arts = parse_articles(md, source_path="synthetic.md")
    keys = [a.article_key for a in arts]
    assert len(keys) == len(set(keys)), f"duplicate article_keys: {keys}"
    assert keys == [
        "identificacion",
        "regla-operativa",
        "identificacion-1",
        "regla-operativa-1",
        "identificacion-2",
    ]


def test_whole_document_fallback_when_no_h2_headers():
    md = "Un parrafo suelto sin encabezados.\nOtra linea."
    arts = parse_articles(md, source_path="synthetic.md")
    assert len(arts) == 1
    assert arts[0].article_key == WHOLE_DOC_ARTICLE_KEY


def test_empty_sections_do_not_produce_chunks():
    md = (
        "## Identificacion\n"
        "(sin datos)\n"
        "\n## Regla operativa\n"
        "Contenido real.\n"
    )
    arts = parse_articles(md, source_path="synthetic.md")
    keys = [a.article_key for a in arts]
    assert keys == ["regla-operativa"], (
        "(sin datos) placeholder section must be skipped; only 'regla-operativa' should remain"
    )


@pytest.mark.parametrize(
    "path",
    [CLASSIC_NORMATIVA, V2_TEMPLATE_NORMATIVA, V2_INTERPRETACION],
)
def test_reference_docs_always_produce_at_least_one_chunk(path: Path):
    """Regression guard: any canonical corpus doc must yield >=1 retrievable chunk."""
    arts = parse_articles(_read(path), source_path=str(path))
    assert len(arts) >= 1, f"no chunks produced for {path.name}"
