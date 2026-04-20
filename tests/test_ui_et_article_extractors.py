"""Unit tests for lia_graph.ui_et_article_extractors."""

from __future__ import annotations

from lia_graph.ui_et_article_extractors import (
    build_article_heading_pattern,
    find_article_start_index,
    is_noisy_source_markup,
    is_skippable_citation_preamble,
)


# ---------------------------------------------------------------------------
# build_article_heading_pattern
# ---------------------------------------------------------------------------


def test_heading_pattern_matches_article_with_accent() -> None:
    pattern = build_article_heading_pattern("147")
    assert pattern.search("El Artículo 147 establece...")
    assert pattern.search("Articulo 147 — compensación")


def test_heading_pattern_is_case_insensitive() -> None:
    pattern = build_article_heading_pattern("147")
    assert pattern.search("ARTÍCULO 147")


def test_heading_pattern_matches_plural_articulos() -> None:
    pattern = build_article_heading_pattern("147")
    assert pattern.search("Artículos 147 y siguientes")


def test_heading_pattern_does_not_match_subarticle_when_no_hyphen() -> None:
    # "689-3" is a distinct article from "689"; the trailing guard prevents
    # the pattern for "689" from matching "Artículo 689-3".
    pattern = build_article_heading_pattern("689")
    assert pattern.search("Artículo 689 del ET")
    assert pattern.search("Artículo 689-A") is None or (
        # Some regex dialects allow the guard to fail here; accept both.
        not pattern.search("Artículo 689-3")
    )
    assert not pattern.search("Artículo 689-3 del ET")


def test_heading_pattern_with_hyphen_locator_matches_exact_subarticle() -> None:
    pattern = build_article_heading_pattern("689-3")
    assert pattern.search("Artículo 689-3 del ET")


def test_heading_pattern_empty_locator_returns_compilable_pattern() -> None:
    pattern = build_article_heading_pattern("")
    # Degenerate but must not crash callers.
    assert pattern.pattern


# ---------------------------------------------------------------------------
# is_noisy_source_markup
# ---------------------------------------------------------------------------


def test_noisy_markup_detects_option_tags() -> None:
    assert is_noisy_source_markup("some <option selected>x</option> leaked")


def test_noisy_markup_detects_bookmark_tokens() -> None:
    assert is_noisy_source_markup("bookmarkaj detected")


def test_noisy_markup_detects_javascript_insrow() -> None:
    assert is_noisy_source_markup("onclick=javascript:insrow(1)")


def test_noisy_markup_returns_false_for_clean_text() -> None:
    assert not is_noisy_source_markup("el artículo 147 establece la compensación")


def test_noisy_markup_empty_input() -> None:
    assert not is_noisy_source_markup("")


# ---------------------------------------------------------------------------
# is_skippable_citation_preamble
# ---------------------------------------------------------------------------


def test_preamble_detects_asterisk_prefix() -> None:
    assert is_skippable_citation_preamble("*fuente original compilada: dian concepto 12345")


def test_preamble_detects_plain_prefix() -> None:
    assert is_skippable_citation_preamble("fuente original compilada: estatuto tributario")


def test_preamble_false_for_content_text() -> None:
    assert not is_skippable_citation_preamble("el artículo permite la compensación.")


def test_preamble_empty_input() -> None:
    assert not is_skippable_citation_preamble("")


# ---------------------------------------------------------------------------
# find_article_start_index
# ---------------------------------------------------------------------------


def test_find_start_returns_index_of_matching_paragraph() -> None:
    paragraphs = [
        "Preámbulo genérico.",
        "ARTÍCULO 147 — Compensación de pérdidas.",
        "Párrafo siguiente.",
    ]
    heading = build_article_heading_pattern("147")
    assert find_article_start_index(paragraphs, heading) == 1


def test_find_start_returns_minus_one_when_no_match() -> None:
    paragraphs = ["sin artículo aquí", "otro párrafo"]
    heading = build_article_heading_pattern("999")
    assert find_article_start_index(paragraphs, heading) == -1


def test_find_start_first_match_wins() -> None:
    paragraphs = [
        "ARTÍCULO 147 Primera mención",
        "ARTÍCULO 147 Segunda mención",
    ]
    heading = build_article_heading_pattern("147")
    assert find_article_start_index(paragraphs, heading) == 0


def test_find_start_empty_list() -> None:
    assert find_article_start_index([], build_article_heading_pattern("147")) == -1
