from __future__ import annotations

from lia_graph.citation_resolution import (
    collect_reference_mentions,
    extract_reference_identities_from_citation_payload,
    extract_reference_identities_from_text,
    extract_reference_keys_from_text,
    reference_detail_resolution_text,
    reference_detail_title,
)


def test_collect_reference_mentions_dedupes_by_identity_but_keeps_locators() -> None:
    collection = collect_reference_mentions("arts. 147 y 290 ET. arts. 147 y 290 ET.")

    assert collection.detected_count == 2
    assert collection.unique_count == 2
    assert [item.reference_identity for item in collection.mentions] == [
        "et::articles::147::::artículos 147",
        "et::articles::290::::artículos 290",
    ]


def test_extract_reference_identity_and_keys_from_text_use_shared_collector() -> None:
    identities = extract_reference_identities_from_text("12 ET y ET 290")
    keys = extract_reference_keys_from_text("12 ET y ET 290")

    assert identities == {
        "et::articles::12::::artículos 12",
        "et::articles::290::::artículos 290",
    }
    assert keys == {"et"}


def test_extract_reference_identities_from_citation_payload_includes_explicit_and_embedded_mentions() -> None:
    identities = extract_reference_identities_from_citation_payload(
        {
            "reference_key": "et",
            "locator_start": "147",
            "locator_kind": "articles",
            "locator_text": "Artículos 147",
            "source_label": "arts. 147 y 290 ET",
        }
    )

    assert identities == {
        "et::articles::147::::artículos 147",
        "et::articles::290::::artículos 290",
    }


def test_reference_detail_helpers_build_stable_titles() -> None:
    detail = {
        "reference_key": "et",
        "reference_identity": "et::articles::147::::artículos 147",
        "reference_text": "Estatuto Tributario",
        "locator_text": "Artículos 147",
    }

    assert reference_detail_title(detail) == "Estatuto Tributario, Artículos 147"
    assert reference_detail_resolution_text(detail) == "Estatuto Tributario, Artículos 147"
