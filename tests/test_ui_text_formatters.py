"""Unit tests for lia_graph.ui_text_formatters — pure text helpers."""

from __future__ import annotations

import pytest

from lia_graph.ui_text_formatters import (
    SPANISH_SMALL_WORDS,
    clean_practica_label,
    label_dedup_key,
    spanish_title_case_label,
)


# ---------------------------------------------------------------------------
# SPANISH_SMALL_WORDS
# ---------------------------------------------------------------------------


def test_small_words_contains_spanish_connectors() -> None:
    for word in ["de", "del", "en", "la", "los", "y", "o", "para"]:
        assert word in SPANISH_SMALL_WORDS


# ---------------------------------------------------------------------------
# spanish_title_case_label
# ---------------------------------------------------------------------------


def test_title_case_capitalizes_each_content_word() -> None:
    assert spanish_title_case_label("firmeza de las declaraciones tributarias") == (
        "Firmeza de las Declaraciones Tributarias"
    )


def test_title_case_keeps_small_words_lowercase_mid_sentence() -> None:
    assert spanish_title_case_label("compensación de pérdidas y descuentos") == (
        "Compensación de Pérdidas y Descuentos"
    )


def test_title_case_capitalizes_first_word_even_if_connector() -> None:
    # A connector at position 0 looks broken when left lowercase.
    assert spanish_title_case_label("de pérdidas fiscales") == "De Pérdidas Fiscales"


def test_title_case_handles_empty_input() -> None:
    assert spanish_title_case_label("") == ""
    assert spanish_title_case_label("   ") == "   "


def test_title_case_handles_none() -> None:
    # Some callers pass None; the formatter should coerce to "".
    assert spanish_title_case_label(None) == ""  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# label_dedup_key
# ---------------------------------------------------------------------------


def test_dedup_key_strips_entity_type_variants() -> None:
    base = label_dedup_key("Ley 1943 — Personas Jurídicas")
    other = label_dedup_key("Ley 1943 — Personas Naturales")
    assert base == other


def test_dedup_key_strips_year() -> None:
    assert label_dedup_key("Ley 1943 de 2018") == label_dedup_key("Ley 1943 de 2022")


def test_dedup_key_strips_entity_abbreviations() -> None:
    base = label_dedup_key("Ley 100 — GC")
    assert base == label_dedup_key("Ley 100 — PJ")
    assert base == label_dedup_key("Ley 100 — PES")


def test_dedup_key_normalizes_whitespace() -> None:
    assert label_dedup_key("  algo   con   espacios ") == "algo con espacios"


def test_dedup_key_empty_input() -> None:
    assert label_dedup_key("") == ""


# ---------------------------------------------------------------------------
# clean_practica_label
# ---------------------------------------------------------------------------


def test_clean_practica_strips_code_prefix() -> None:
    assert clean_practica_label("abc def — Guía cierre contable") == "Guía cierre contable"


def test_clean_practica_strips_unknown_prefix() -> None:
    assert clean_practica_label("Unknown: Guía cierre contable") == "Guía cierre contable"


def test_clean_practica_strips_numeric_prefix() -> None:
    assert clean_practica_label("12 — Guía cierre contable") == "Guía cierre contable"


def test_clean_practica_strips_file_extension() -> None:
    assert clean_practica_label("guia_cierre_contable.md") == "guia cierre contable"
    assert clean_practica_label("informe.html") == "informe"


def test_clean_practica_replaces_underscores_with_spaces() -> None:
    assert clean_practica_label("guia_cierre_contable") == "guia cierre contable"


def test_clean_practica_falls_back_to_raw_when_empty_after_clean() -> None:
    # Exotic input that would become empty — the original stays.
    assert clean_practica_label("---") == "---"


@pytest.mark.parametrize("raw", ["", "   "])
def test_clean_practica_empty_input_returns_raw(raw: str) -> None:
    assert clean_practica_label(raw) == raw
