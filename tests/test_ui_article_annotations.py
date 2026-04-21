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
    group_editor_notes,
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
        "Legislación Anterior",
    )


# `Jurisprudencia Concordante` is the exact header used in the ET corpus
# (~483 occurrences, including Art. 147). The old regex only accepted bare
# `Jurisprudencia`, so these blocks leaked into Concordancias as a single
# run-on paragraph. This fixture mirrors the real source shape.
ARTICLE_147_LIKE_FIXTURE = """\
Body of Art. 147.

**Concordancias:**
> * [Ley 1739 de 2014](https://example.com/ley1739.htm)
> * [Decreto 1032 de 1999; Art. 1](https://example.com/d1032.htm)

**Jurisprudencia Concordante:**
> * [- Consejo de Estado, Sección Cuarta, Expediente 18912 de 2019](https://example.com/ce18912.htm)
> * [- Consejo de Estado, Sección Cuarta, Expediente 23419 de 2020](https://example.com/ce23419.htm)

**Doctrina Concordante:**
> * [Oficio DIAN 2197 de 2023](https://example.com/oficio2197.htm)
"""


def test_jurisprudencia_concordante_gets_its_own_tab() -> None:
    _, annotations = split_article_annotations(ARTICLE_147_LIKE_FIXTURE)
    labels = [a["label"] for a in annotations]
    assert labels == ["Concordancias", "Jurisprudencia", "Doctrina Concordante"]


def test_jurisprudencia_entries_are_individual_bullets() -> None:
    _, annotations = split_article_annotations(ARTICLE_147_LIKE_FIXTURE)
    jur = next(a for a in annotations if a["label"] == "Jurisprudencia")
    assert [i["href"] for i in jur["items"]] == [
        "https://example.com/ce18912.htm",
        "https://example.com/ce23419.htm",
    ]
    # Leading "- " typographic prefix from corpus anchor text is stripped.
    assert jur["items"][0]["text"].startswith("Consejo de Estado")
    assert not any(i["text"].startswith("-") for i in jur["items"])


def test_concordancias_no_longer_absorbs_jurisprudencia() -> None:
    _, annotations = split_article_annotations(ARTICLE_147_LIKE_FIXTURE)
    conc = next(a for a in annotations if a["label"] == "Concordancias")
    assert len(conc["items"]) == 2
    assert all("Consejo de Estado" not in i["text"] for i in conc["items"])


def test_jurisprudencia_variants_merge_into_one_tab() -> None:
    text = """\
**Jurisprudencia Concordante:**
> * [Corte A](https://example.com/a.htm)

**Jurisprudencia Vigencia:**
> * [Corte B](https://example.com/b.htm)

**Jurisprudencia Unificación:**
> * [Corte C](https://example.com/c.htm)
"""
    _, annotations = split_article_annotations(text)
    labels = [a["label"] for a in annotations]
    assert labels == ["Jurisprudencia"]
    hrefs = [i["href"] for i in annotations[0]["items"]]
    assert hrefs == [
        "https://example.com/a.htm",
        "https://example.com/b.htm",
        "https://example.com/c.htm",
    ]


def test_doctrina_variants_collapse_into_canonical_tab() -> None:
    text = """\
**Doctrina Concordante (DIAN):**
> * [Oficio DIAN 111 de 2020](https://example.com/o111.htm)

**Doctrina DIAN:**
> * [Oficio DIAN 222 de 2021](https://example.com/o222.htm)
"""
    _, annotations = split_article_annotations(text)
    assert [a["label"] for a in annotations] == ["Doctrina Concordante"]
    assert len(annotations[0]["items"]) == 2


def test_typo_jurisprucdencia_is_still_recognized() -> None:
    text = """\
**Jurisprucdencia Concordante:**
> * [Corte typo](https://example.com/t.htm)
"""
    _, annotations = split_article_annotations(text)
    assert [a["label"] for a in annotations] == ["Jurisprudencia"]


def test_legislacion_anterior_is_its_own_tab() -> None:
    # Real ET articles place `**Legislación Anterior:**` right after Doctrina
    # Concordante. Before the fix this block leaked into the Doctrina tab as a
    # single paragraph-length `<a>` because the splitter didn't recognize the
    # label. The parser should now emit it as a separate tab.
    text = """\
**Doctrina Concordante:**
> * [Concepto DIAN 08219 de 1997](https://example.com/c08219.htm)

**Legislación Anterior:**
> * Texto modificado por la Ley 1111 de 2016:
> * [<Inciso modificado por el artículo 5 de la Ley 1111 de 2006> Las sociedades podrán compensar las pérdidas fiscales reajustadas fiscalmente.](https://example.com/ley1111.htm)
> * Texto modificado por la Ley 788 de 2002:
> * <INCISO 1> Las sociedades podrán compensar las pérdidas fiscales ajustadas por inflación.
"""
    _, annotations = split_article_annotations(text)
    labels = [a["label"] for a in annotations]
    assert labels == ["Doctrina Concordante", "Legislación Anterior"]
    doctrina = next(a for a in annotations if a["label"] == "Doctrina Concordante")
    assert len(doctrina["items"]) == 1
    assert "Las sociedades" not in doctrina["items"][0]["text"]
    legacy = next(a for a in annotations if a["label"] == "Legislación Anterior")
    # Four bullets in → four items out; paragraph-long anchors are preserved
    # verbatim so the frontend can choose how to render them.
    assert len(legacy["items"]) == 4
    assert legacy["items"][1]["href"] == "https://example.com/ley1111.htm"
    assert "pérdidas fiscales reajustadas" in legacy["items"][1]["text"]


def test_mixed_block_with_orphan_bold_header_keeps_bullets() -> None:
    # Art 147 leaks `**Notas del Editor:**` into the Legislación Anterior
    # segment. The old parser collapsed this mixed block into one paragraph;
    # the new parser drops the orphan header and emits bullets individually.
    text = """\
> * Legacy bullet A.
> * Legacy bullet B.

**Notas del Editor:**
> * [En criterio del editor first note.](https://example.com/note1.htm)
> * (Continuation fragment.)
> * [En criterio del editor second note.](https://example.com/note2.htm)
"""
    items = parse_annotation_items(text)
    texts = [i["text"] for i in items]
    assert "Legacy bullet A." in texts
    assert "En criterio del editor first note." in texts
    assert "En criterio del editor second note." in texts
    assert "(Continuation fragment.)" in texts
    # Orphan bold header is not emitted as a prose item.
    assert not any("Notas del Editor" in t for t in texts)


def test_group_editor_notes_folds_continuations_into_sub_items() -> None:
    flat = [
        {"text": "En criterio del editor note one.", "href": "https://example.com/n1.htm"},
        {"text": "(Continuation one-a.)", "href": ""},
        {"text": "Quoted norm 1-B.", "href": "https://example.com/n1b.htm"},
        {"text": "En criterio del editor note two.", "href": "https://example.com/n2.htm"},
        {"text": "(Continuation two-a.)", "href": ""},
    ]
    grouped = group_editor_notes(flat)
    assert len(grouped) == 2
    first, second = grouped
    assert first["text"].startswith("En criterio del editor note one")
    assert first["href"] == "https://example.com/n1.htm"
    assert [s["text"] for s in first["sub_items"]] == [
        "(Continuation one-a.)",
        "Quoted norm 1-B.",
    ]
    assert first["sub_items"][1]["href"] == "https://example.com/n1b.htm"
    assert second["text"].startswith("En criterio del editor note two")
    assert [s["text"] for s in second["sub_items"]] == ["(Continuation two-a.)"]


def test_group_editor_notes_is_noop_without_sentinel() -> None:
    flat = [
        {"text": "Ley 1819 de 2016; Art. 88", "href": "https://example.com/l1.htm"},
        {"text": "Decreto 1625 de 2016", "href": "https://example.com/d1.htm"},
    ]
    assert group_editor_notes(flat) == flat


def test_items_before_first_sentinel_pass_through() -> None:
    flat = [
        {"text": "Texto modificado por la Ley X:", "href": ""},
        {"text": "Historical passage.", "href": "https://example.com/h.htm"},
        {"text": "En criterio del editor commentary.", "href": "https://example.com/c.htm"},
        {"text": "(Continuation.)", "href": ""},
    ]
    grouped = group_editor_notes(flat)
    assert len(grouped) == 3
    assert grouped[0]["text"] == "Texto modificado por la Ley X:"
    assert "sub_items" not in grouped[0]
    assert grouped[2]["text"].startswith("En criterio del editor")
    assert grouped[2]["sub_items"] == [{"text": "(Continuation.)", "href": ""}]


def test_split_article_groups_editor_notes_inside_legislacion_anterior() -> None:
    # End-to-end: source has `**Legislación Anterior:**` followed by an
    # orphan `**Notas del Editor:**` block. The resulting tab should have
    # the editor notes grouped with sub_items, while the pure historical
    # bullets stay flat at the top level.
    text = """\
**Legislación Anterior:**
> * Texto original del Estatuto Tributario.
> * [<Old text passage>](https://example.com/old.htm)

**Notas del Editor:**
> * [En criterio del editor para la interpretación A.](https://example.com/a.htm)
> * (Por favor remitirse a la norma original.)
> * ['Artículo 319-4](https://example.com/art319.htm)
> * [En criterio del editor para la interpretación B.](https://example.com/b.htm)
> * (Continuation B.)
"""
    _, annotations = split_article_annotations(text)
    leg = next(a for a in annotations if a["label"] == "Legislación Anterior")
    items = leg["items"]
    # Two flat historical items + two grouped editor notes = 4 top-level items.
    assert len(items) == 4
    assert items[0]["text"].startswith("Texto original")
    assert "sub_items" not in items[0]
    note_a = items[2]
    assert note_a["text"].startswith("En criterio del editor para la interpretación A")
    assert note_a["href"] == "https://example.com/a.htm"
    assert [s["text"] for s in note_a["sub_items"]] == [
        "(Por favor remitirse a la norma original.)",
        "'Artículo 319-4",
    ]
    note_b = items[3]
    assert note_b["text"].startswith("En criterio del editor para la interpretación B")
    assert note_b["sub_items"][0]["text"] == "(Continuation B.)"


def test_unknown_bold_headers_stay_in_body() -> None:
    text = """\
Body text with **Nota importante:** inline emphasis.

**Random Label:**
> * item

**Concordancias:**
> * [Ley X](https://example.com/x.htm)
"""
    body, annotations = split_article_annotations(text)
    # Unknown bold headers are ignored — only recognized ones slice the body.
    assert [a["label"] for a in annotations] == ["Concordancias"]
    assert "Random Label" in body
    assert "Nota importante" in body
