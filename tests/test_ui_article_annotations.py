"""Unit tests for `lia_graph.ui_article_annotations`.

Locks in the contract that matters for the normative article modal: the
parser must preserve markdown hrefs as a structured `items` list so the
frontend can render Doctrina/Concordancias/Notas de Vigencia bullets as
clickable anchors instead of plain text.
"""

from __future__ import annotations

from lia_graph.ui_article_annotations import (
    ANNOTATION_LABELS,
    clean_annotation_body,
    parse_annotation_items,
    split_article_annotations,
)


ARTICLE_290_FIXTURE = """\
ARTÍCULO 290. RÉGIMEN DE TRANSICIÓN. Texto del articulo.

**Notas de Vigencia:**
> * [- Capítulo adicionado por el artículo 123 de la Ley 1819 de 2016](https://normograma.dian.gov.co/dian/compilacion/docs/ley_1819_2016.htm#123)

**Concordancias:**
> * [Decreto 2235 de 2017](https://normograma.dian.gov.co/dian/compilacion/docs/decreto_2235_2017.htm#inicio)
> * [Decreto Único Reglamentario 1625 de 2016; Art. 1.2.1.25.15](https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm#1.2.1.25.15)

**Doctrina Concordante:**
> * [Oficio DIAN 635 de 2019](https://normograma.dian.gov.co/dian/compilacion/docs/oficio_dian_0635_2019.htm#INICIO)
> * [Concepto DIAN 14396 de 2025](https://normograma.dian.gov.co/dian/compilacion/docs/oficio_dian_14396_2025.htm#0)
"""


def test_split_returns_labels_in_canonical_order() -> None:
    _, annotations = split_article_annotations(ARTICLE_290_FIXTURE)
    labels = [a["label"] for a in annotations]
    assert labels == ["Notas de Vigencia", "Concordancias", "Doctrina Concordante"]


def test_body_excludes_annotation_blocks() -> None:
    body, _ = split_article_annotations(ARTICLE_290_FIXTURE)
    assert body.startswith("ARTÍCULO 290.")
    assert "**Notas de Vigencia" not in body
    assert "Oficio DIAN" not in body


def test_items_preserve_markdown_hrefs() -> None:
    _, annotations = split_article_annotations(ARTICLE_290_FIXTURE)
    by_label = {a["label"]: a for a in annotations}

    doctrina = by_label["Doctrina Concordante"]["items"]
    assert doctrina == [
        {
            "text": "Oficio DIAN 635 de 2019",
            "href": "https://normograma.dian.gov.co/dian/compilacion/docs/oficio_dian_0635_2019.htm#INICIO",
        },
        {
            "text": "Concepto DIAN 14396 de 2025",
            "href": "https://normograma.dian.gov.co/dian/compilacion/docs/oficio_dian_14396_2025.htm#0",
        },
    ]

    concordancias = by_label["Concordancias"]["items"]
    assert [i["href"] for i in concordancias] == [
        "https://normograma.dian.gov.co/dian/compilacion/docs/decreto_2235_2017.htm#inicio",
        "https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm#1.2.1.25.15",
    ]
    assert concordancias[1]["text"] == "Decreto Único Reglamentario 1625 de 2016; Art. 1.2.1.25.15"


def test_items_fallback_to_plain_text_when_no_href() -> None:
    text = """\
**Concordancias:**
> * Corte Constitucional — Sentencia C-087-19 de 27 de febrero de 2019
> * [Decreto 2235 de 2017](https://normograma.dian.gov.co/x.htm)
"""
    _, annotations = split_article_annotations(text)
    items = annotations[0]["items"]
    assert items[0] == {
        "text": "Corte Constitucional — Sentencia C-087-19 de 27 de febrero de 2019",
        "href": "",
    }
    assert items[1]["href"] == "https://normograma.dian.gov.co/x.htm"


def test_items_reject_unsafe_hrefs() -> None:
    text = """\
**Concordancias:**
> * [Scary](javascript:alert)
> * [Also scary](data:text/html,xss)
> * [Good](https://example.com/page)
"""
    _, annotations = split_article_annotations(text)
    items = annotations[0]["items"]
    assert items[0]["href"] == ""
    assert "Scary" in items[0]["text"]
    assert items[1]["href"] == ""
    assert items[2]["href"] == "https://example.com/page"


def test_body_string_strips_markdown_for_back_compat() -> None:
    segment = """\
> * [Oficio DIAN 635 de 2019](https://example.com/a)
> * **Bold** and `code`
"""
    cleaned = clean_annotation_body(segment)
    assert "](" not in cleaned  # markdown link flattened
    assert "**" not in cleaned  # bold stripped
    assert "`" not in cleaned  # backticks stripped
    assert "Oficio DIAN 635 de 2019" in cleaned


def test_parse_items_handles_bare_paragraph() -> None:
    items = parse_annotation_items(
        "This is a single paragraph that mentions [Ley 1819 de 2016](https://example.com/ley) inline."
    )
    assert len(items) == 1
    assert items[0]["href"] == "https://example.com/ley"
    # anchor text embedded in paragraph → paragraph kept, href attached
    assert "mentions Ley 1819 de 2016 inline" in items[0]["text"]


def test_no_matches_returns_raw_body_unchanged() -> None:
    raw = "No annotation labels here."
    body, anns = split_article_annotations(raw)
    assert body == raw
    assert anns == []


def test_annotation_labels_are_stable() -> None:
    assert ANNOTATION_LABELS == (
        "Notas de Vigencia",
        "Concordancias",
        "Jurisprudencia",
        "Doctrina Concordante",
    )
