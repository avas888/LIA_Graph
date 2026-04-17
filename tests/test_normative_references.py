from __future__ import annotations

from lia_graph.normative_references import (
    extract_normative_reference_mentions,
    extract_normative_references,
)


def test_extract_normative_references_collapses_to_one_row_per_reference_key() -> None:
    references = extract_normative_references("arts. 147 y 290 ET")
    mentions = extract_normative_reference_mentions("arts. 147 y 290 ET")

    assert len(references) == 1
    assert references[0]["reference_key"] == "et"
    assert references[0]["locator_start"] == "147"
    assert [item["locator_start"] for item in mentions] == ["147", "290"]


def test_extract_normative_reference_mentions_accepts_et_as_article_signifier() -> None:
    mentions = extract_normative_reference_mentions("12 ET y ET 290")

    assert [item["locator_start"] for item in mentions] == ["12", "290"]


def test_extract_normative_reference_mentions_rejects_quantities_and_year_ranges() -> None:
    assert extract_normative_reference_mentions("12 años") == []
    assert extract_normative_reference_mentions("años 2017-2018 y 2019-2020") == []
    assert extract_normative_reference_mentions("art. 12 años") == []


def test_extract_normative_reference_mentions_keeps_prior_articles_when_sentence_ends_with_quantity() -> None:
    mentions = extract_normative_reference_mentions("arts. 147, 290 y 12 años")

    assert [item["locator_start"] for item in mentions] == ["147", "290"]


def test_extract_normative_reference_mentions_handles_dotted_article_lists() -> None:
    mentions = extract_normative_reference_mentions("arts. 771-2, 616-1 y 617 ET")

    assert [item["locator_start"] for item in mentions] == ["771-2", "616-1", "617"]


def test_extract_normative_references_parses_dur_and_generic_documents() -> None:
    references = extract_normative_references(
        "art. 1.2.1.5.1 del DUR 1625 de 2016, Ley 1819 de 2016 y Formato 2517."
    )

    assert references[0]["reference_key"] == "dur:1625:2016"
    assert references[0]["locator_start"] == "1.2.1.5.1"
    assert references[1]["reference_key"] == "ley:1819:2016"
    assert references[2]["reference_key"] == "formulario:2517"
