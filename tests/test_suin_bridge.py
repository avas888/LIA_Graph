"""SUIN bridge round-trip tests.

The bridge converts SUIN harvest JSONL (`documents.jsonl` / `articles.jsonl` /
`edges.jsonl`) into the `ParsedArticle` / `ClassifiedEdge` / document-dict rows
the existing pipeline already persists. These tests pin:

- every canonical verb (except `nota_editorial`) produces an `EdgeKind`.
- `nota_editorial` emits no edge (document-level annotation only).
- vigencia flows: a `derogada` SUIN doc lands as `status="derogado"` on every
  article it contains, which the sink turns into `vigencia="derogada"` +
  `chunk_section_type="historical"`.
- `basis_text` on the edge payload carries the original SUIN anchor text so a
  consumer can cite it verbatim.
- Two-pass merge: stub articles are created for SUIN edge targets that are
  not present in either the base corpus or the SUIN articles file.
"""

from __future__ import annotations

import json
from pathlib import Path

from lia_graph.graph.schema import EdgeKind
from lia_graph.ingestion.suin.bridge import (
    SuinScope,
    build_classified_edges,
    build_document_rows,
    build_parsed_articles,
    build_stub_articles,
    build_stub_document_rows,
)


def _write_scope(tmp: Path) -> SuinScope:
    docs = [
        {
            "doc_id": "624_1989",
            "ruta": "Decretos/624_1989",
            "title": "Estatuto Tributario",
            "emitter": "Presidencia",
            "diario_oficial": "DO 38756",
            "fecha_publicacion": "1989-03-30",
            "rama": "Tributaria",
            "materia": "Renta",
            "vigencia": "vigente",
        },
        {
            "doc_id": "SENT-C-123-2021",
            "ruta": "SentenciasCorteConstitucional/C-123-2021",
            "title": "Sentencia C-123 de 2021",
            "emitter": "Corte Constitucional",
            "diario_oficial": "",
            "fecha_publicacion": "2021-05-12",
            "rama": "Constitucional",
            "materia": "Tributaria",
            "vigencia": "vigente",
        },
        {
            "doc_id": "DEROGADO_ART",
            "ruta": "Leyes/Ley999_2019",
            "title": "Ley derogada",
            "emitter": "Congreso",
            "diario_oficial": "",
            "fecha_publicacion": "2019-01-01",
            "rama": "Tributaria",
            "materia": "Renta",
            "vigencia": "derogada",
        },
    ]
    articles = [
        {
            "doc_id": "624_1989",
            "article_number": "135",
            "article_fragment_id": "10001",
            "heading": "Artículo 135. Del impuesto.",
            "body_text": "Texto del artículo 135.",
        },
        {
            "doc_id": "624_1989",
            "article_number": "631",
            "article_fragment_id": "20002",
            "heading": "Artículo 631.",
            "body_text": "Deber de informar.",
        },
        {
            "doc_id": "SENT-C-123-2021",
            "article_number": "1",
            "article_fragment_id": "30003",
            "heading": "Sentencia C-123 de 2021",
            "body_text": "Declarase exequible el artículo 631 ET.",
        },
        {
            "doc_id": "DEROGADO_ART",
            "article_number": "5",
            "article_fragment_id": "40004",
            "heading": "Artículo 5º. Derogado.",
            "body_text": "Artículo derogado.",
        },
    ]
    edges = [
        # 135 modified by LEY 1607 art 139 (target doc we did NOT harvest — stubbed)
        {
            "source_doc_id": "624_1989",
            "source_article_key": "135",
            "verb": "modifica",
            "raw_verb": "Modificado",
            "target_doc_id": "1607001",
            "target_article_key": "139",
            "target_fragment_id": "50",
            "target_citation": "Artículo 139 LEY 1607 de 2012",
            "scope": None,
            "container_kind": "NotasDestino",
        },
        # 631 struck down by sentencia — both ends harvested
        {
            "source_doc_id": "624_1989",
            "source_article_key": "631",
            "verb": "declara_inexequible",
            "raw_verb": "Declarado inexequible",
            "target_doc_id": "SENT-C-123-2021",
            "target_article_key": "1",
            "target_fragment_id": "30003",
            "target_citation": "Sentencia C-123 de 2021",
            "scope": "inciso 1",
            "container_kind": "NotasDestinoJurisp",
        },
        # Reciprocal on sentencia side
        {
            "source_doc_id": "SENT-C-123-2021",
            "source_article_key": "1",
            "verb": "declara_inexequible",
            "raw_verb": "Inexequible",
            "target_doc_id": "624_1989",
            "target_article_key": "631",
            "target_fragment_id": "20002",
            "target_citation": "Artículo 631 ET",
            "scope": None,
            "container_kind": "NotasOrigen",
        },
        # Editorial annotation — must produce NO edge
        {
            "source_doc_id": "624_1989",
            "source_article_key": "135",
            "verb": "nota_editorial",
            "raw_verb": "Nota editorial",
            "target_doc_id": "",
            "target_article_key": "",
            "target_fragment_id": None,
            "target_citation": "Editor's note",
            "scope": None,
            "container_kind": "NotasDestino",
        },
    ]
    (tmp / "documents.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in docs) + "\n",
        encoding="utf-8",
    )
    (tmp / "articles.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in articles) + "\n",
        encoding="utf-8",
    )
    (tmp / "edges.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in edges) + "\n",
        encoding="utf-8",
    )
    (tmp / "_harvest_manifest.json").write_text(
        json.dumps({"verb_counts": {"modifica": 1, "declara_inexequible": 2}}),
        encoding="utf-8",
    )
    return SuinScope.load(tmp)


def test_every_canonical_verb_maps_to_edge_kind(tmp_path: Path) -> None:
    scope = _write_scope(tmp_path)
    edges = build_classified_edges(scope)
    kinds = {e.record.kind for e in edges}
    # `nota_editorial` is absent — document annotation, not an edge.
    assert EdgeKind.MODIFIES in kinds
    assert EdgeKind.STRUCK_DOWN_BY in kinds
    # All edges have confidence 1.0 (DOM-derived, not classifier heuristic).
    assert all(e.confidence == 1.0 for e in edges)
    # Editorial verb never produces an edge.
    assert not any(
        e.record.properties.get("suin_verb") == "nota_editorial" for e in edges
    )


def test_nota_editorial_emits_zero_edges(tmp_path: Path) -> None:
    scope = _write_scope(tmp_path)
    edges = build_classified_edges(scope)
    editorial_sources = [
        e
        for e in edges
        if e.record.source_key == "135"
        and e.record.properties.get("suin_verb") == "nota_editorial"
    ]
    assert editorial_sources == []


def test_vigencia_flows_through_to_parsed_article_status(tmp_path: Path) -> None:
    scope = _write_scope(tmp_path)
    articles = build_parsed_articles(scope)
    by_key = {(a.article_key, a.source_path): a for a in articles}
    # Article from `vigente` doc (ET) -> status "vigente"
    et_135 = [a for k, a in by_key.items() if k[0] == "135"][0]
    assert et_135.status == "vigente"
    # Article from `derogada` doc -> status "derogado"
    derogado = [a for k, a in by_key.items() if k[0] == "5"][0]
    assert derogado.status == "derogado"


def test_basis_text_carried_verbatim(tmp_path: Path) -> None:
    scope = _write_scope(tmp_path)
    edges = build_classified_edges(scope)
    citations = {
        str(e.record.properties.get("raw_reference") or "") for e in edges
    }
    assert "Artículo 139 LEY 1607 de 2012" in citations
    assert "Sentencia C-123 de 2021" in citations


def test_two_pass_merge_creates_stub_for_unresolved_target(tmp_path: Path) -> None:
    scope = _write_scope(tmp_path)
    articles = build_parsed_articles(scope)
    resolved = {a.article_key for a in articles}
    # LEY 1607 art 139 is referenced but never harvested.
    assert "139" not in resolved
    stubs, unresolved_doc_ids = build_stub_articles(
        scope, resolved_article_keys=resolved
    )
    stub_keys = {s.article_key for s in stubs}
    assert "139" in stub_keys, (stub_keys, resolved)
    assert any(s.status == "stub" for s in stubs)
    # The unresolved doc_id list includes the LEY 1607 doc we never harvested.
    assert "1607001" in unresolved_doc_ids


def test_stub_document_rows_match_sink_shape(tmp_path: Path) -> None:
    _write_scope(tmp_path)
    rows = build_stub_document_rows(["1607001", ""])
    # Empty strings are dropped; valid doc_ids produce one row each.
    assert len(rows) == 1
    row = rows[0]
    for required in (
        "source_path",
        "relative_path",
        "markdown",
        "source_type",
        "family",
        "knowledge_class",
    ):
        assert required in row
    assert row["source_type"] == "suin_stub"
    assert row["source_path"].startswith("suin://")


def test_document_rows_carry_source_type_and_authority(tmp_path: Path) -> None:
    scope = _write_scope(tmp_path)
    rows = build_document_rows(scope)
    by_path = {r["relative_path"]: r for r in rows}
    et_row = by_path["suin/624_1989"]
    assert et_row["source_type"] == "suin_norma"
    assert et_row["knowledge_class"] == "normative_base"
    # authority_from_emitter("Presidencia") -> "presidencia"
    assert et_row["authority_level"] == "presidencia"
    sent_row = by_path["suin/SENT-C-123-2021"]
    assert sent_row["authority_level"] == "corte_constitucional"
    assert sent_row["knowledge_class"] == "jurisprudence"
