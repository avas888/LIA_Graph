"""Tests for the Phase-4 edge typing (ingestionfix_v2 §4 Phase 4).

Covers:
  * ``RawEdgeCandidate.source_family`` plumbing through ``extract_edge_candidates``
  * ``ClassifiedEdge.edge_type`` + ``weight`` derivation in
    ``classify_edge_candidates`` / ``_resolve_edge_type_and_weight``
  * Back-compat: callers that don't pass ``family_by_source_path`` still get
    sensibly-typed edges (MODIFICA / DEROGA when relation_hint is strong, else
    MENCIONA).
"""

from __future__ import annotations

from lia_graph.graph.schema import EdgeKind
from lia_graph.ingestion.classifier import (
    EDGE_TYPE_CITA,
    EDGE_TYPE_DEROGA,
    EDGE_TYPE_INTERPRETA_A,
    EDGE_TYPE_MENCIONA,
    EDGE_TYPE_MODIFICA,
    EDGE_TYPE_PRACTICA_DE,
    classify_edge_candidates,
)
from lia_graph.ingestion.linker import extract_edge_candidates
from lia_graph.ingestion.parser import ParsedArticle


def _article(
    *,
    article_key: str,
    source_path: str,
    body: str,
    heading: str = "Test",
) -> ParsedArticle:
    full_text = f"# Art. {article_key} - {heading}\n{body}"
    return ParsedArticle(
        article_key=article_key,
        article_number=article_key,
        heading=heading,
        body=body,
        full_text=full_text,
        status="vigente",
        source_path=source_path,
    )


def _classify(articles, *, family_by_source_path=None):
    raw = extract_edge_candidates(
        articles, family_by_source_path=family_by_source_path
    )
    return classify_edge_candidates(raw)


# ---------------------------------------------------------------------------
# Phase-4 typing rules
# ---------------------------------------------------------------------------


def test_normativa_source_produces_modifica_edge():
    articles = [
        _article(
            article_key="100",
            source_path="/abs/normativa/ley.md",
            body="Modificase el Articulo 37 del Estatuto Tributario para agregar...",
        ),
    ]
    edges = _classify(
        articles, family_by_source_path={"/abs/normativa/ley.md": "normativa"}
    )
    modifica = [e for e in edges if e.edge_type == EDGE_TYPE_MODIFICA]
    assert modifica, "normativa source with 'modificase' must produce MODIFICA"
    assert all(e.weight == 1.0 for e in modifica)


def test_normativa_source_produces_deroga_edge():
    articles = [
        _article(
            article_key="200",
            source_path="/abs/normativa/deroga.md",
            body="Derogase el Articulo 42 del Estatuto.",
        ),
    ]
    edges = _classify(
        articles, family_by_source_path={"/abs/normativa/deroga.md": "normativa"}
    )
    deroga = [e for e in edges if e.edge_type == EDGE_TYPE_DEROGA]
    assert deroga, "normativa source with 'derogase' must produce DEROGA"
    assert all(e.weight == 1.0 for e in deroga)


def test_normativa_source_plain_citation_produces_cita():
    articles = [
        _article(
            article_key="300",
            source_path="/abs/normativa/cita.md",
            body="Ver Articulo 147 del Estatuto Tributario para referencia.",
        ),
    ]
    edges = _classify(
        articles, family_by_source_path={"/abs/normativa/cita.md": "normativa"}
    )
    cita = [e for e in edges if e.edge_type == EDGE_TYPE_CITA]
    assert cita, "normativa source without modify/derogate keywords → CITA"
    assert all(e.weight == 1.0 for e in cita)


def test_practica_source_produces_practica_de_edge():
    articles = [
        _article(
            article_key="pr-1",
            source_path="/abs/practica/guia.md",
            body="Ver Articulo 651 ET para los requisitos de sancion.",
        ),
    ]
    edges = _classify(
        articles, family_by_source_path={"/abs/practica/guia.md": "practica"}
    )
    practica = [e for e in edges if e.edge_type == EDGE_TYPE_PRACTICA_DE]
    assert practica, "practica source → PRACTICA_DE"
    assert all(e.weight == 0.6 for e in practica)


def test_interpretacion_source_produces_interpreta_a_edge():
    for family in ("interpretacion", "expertos"):
        articles = [
            _article(
                article_key=f"int-{family}",
                source_path=f"/abs/{family}/memo.md",
                body="Analisis del Articulo 368 ET en contexto del decreto 572.",
            ),
        ]
        edges = _classify(
            articles, family_by_source_path={f"/abs/{family}/memo.md": family}
        )
        interp = [e for e in edges if e.edge_type == EDGE_TYPE_INTERPRETA_A]
        assert interp, f"{family} source → INTERPRETA_A"
        assert all(e.weight == 0.6 for e in interp)


def test_casual_mention_gets_menciona_type():
    """No family map passed AND no authority hint in context → MENCIONA."""
    articles = [
        _article(
            article_key="c-1",
            source_path="/abs/unknown/note.md",
            body="La Ley 1429 de 2010 es un referente comun aqui.",
        ),
    ]
    # Deliberately no family_by_source_path.
    edges = _classify(articles)
    menciona = [e for e in edges if e.edge_type == EDGE_TYPE_MENCIONA]
    assert menciona, "no family + no authority hint → MENCIONA"
    assert all(e.weight == 0.2 for e in menciona)


# ---------------------------------------------------------------------------
# Back-compat
# ---------------------------------------------------------------------------


def test_legacy_callers_without_family_still_type_authoritative_hints():
    """Callers that haven't been updated to pass family_by_source_path
    should still get an MODIFICA/DEROGA when the relation_hint is strong,
    not lose authority signal entirely."""
    articles = [
        _article(
            article_key="400",
            source_path="/abs/whatever.md",
            body="Modificase el Articulo 55 para agregar...",
        ),
    ]
    edges = _classify(articles)  # no family map
    assert any(e.edge_type == EDGE_TYPE_MODIFICA for e in edges)


def test_classified_edge_to_dict_includes_new_fields():
    articles = [
        _article(
            article_key="500",
            source_path="/abs/normativa/x.md",
            body="Derogase el Articulo 10.",
        ),
    ]
    edges = _classify(
        articles, family_by_source_path={"/abs/normativa/x.md": "normativa"}
    )
    dumped = [e.to_dict() for e in edges]
    assert any("edge_type" in d and "weight" in d for d in dumped)


def test_extract_edge_candidates_stamps_source_family_on_raw_candidates():
    articles = [
        _article(
            article_key="600",
            source_path="/abs/practica/guia.md",
            body="Ver Articulo 42 ET.",
        ),
    ]
    raw = extract_edge_candidates(
        articles, family_by_source_path={"/abs/practica/guia.md": "practica"}
    )
    assert raw
    assert all(c.source_family == "practica" for c in raw)


def test_classifier_preserves_edge_kind_while_adding_edge_type():
    """EdgeKind (English enum) must NOT be replaced by edge_type (Spanish tag)."""
    articles = [
        _article(
            article_key="700",
            source_path="/abs/normativa/y.md",
            body="Modificase el Articulo 5 del ET.",
        ),
    ]
    edges = _classify(
        articles, family_by_source_path={"/abs/normativa/y.md": "normativa"}
    )
    for e in edges:
        assert isinstance(e.record.kind, EdgeKind), "EdgeKind stays intact"
        # record.properties must carry edge_type + weight for loader consumption
        assert "edge_type" in e.record.properties
        assert "weight" in e.record.properties
