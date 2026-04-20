"""Unit tests for `lia_graph.ui_source_title_resolver`.

The title-resolution pipeline is consumed by four modules
(`ui_source_view_processors`, `ui_citation_profile_builders`,
`ui_normative_processors`, `ui_expert_extractors`). These tests lock in
the behavior that matters for the source-view window and the citation
modal title strip — ordered candidate walks, technical-title detection,
and humanization of filename-derived slugs.
"""

from __future__ import annotations

from lia_graph.ui_source_title_resolver import (
    _humanize_technical_title,
    _infer_source_title_from_url_or_path,
    _is_generic_source_title,
    _looks_like_technical_title,
    _normalize_source_reference_text,
    _resolve_source_display_title,
    _title_from_normative_identity,
)


def test_normalize_source_reference_text_strips_accents_and_whitespace() -> None:
    assert _normalize_source_reference_text("  Decreto 2229 ") == "decreto 2229"
    assert _normalize_source_reference_text("Resolución DIAN") == "resolucion dian"
    assert _normalize_source_reference_text("") == ""
    assert _normalize_source_reference_text(None) == ""  # type: ignore[arg-type]


def test_title_from_normative_identity_parses_three_part_key() -> None:
    assert _title_from_normative_identity({"entity_id": "decreto:2229:2023"}) == "Decreto 2229 de 2023"
    assert _title_from_normative_identity({"entity_id": "ley:1819:2016"}) == "Ley 1819 de 2016"
    assert (
        _title_from_normative_identity({"entity_id": "resolucion_dian:238:2025"})
        == "Resolución DIAN 238 de 2025"
    )
    assert (
        _title_from_normative_identity({"entity_id": "concepto_dian:14396:2025"})
        == "Concepto DIAN 14396 de 2025"
    )


def test_title_from_normative_identity_parses_two_part_key() -> None:
    assert _title_from_normative_identity({"entity_id": "decreto:2229"}) == "Decreto 2229"
    assert _title_from_normative_identity({"entity_id": "circular:8"}) == "Circular 8"


def test_title_from_normative_identity_falls_back_to_reference_keys() -> None:
    row = {"entity_id": "", "reference_identity_keys": ["Ley:1819:2016"]}
    assert _title_from_normative_identity(row) == "Ley 1819 de 2016"


def test_title_from_normative_identity_empty_or_unknown_type() -> None:
    assert _title_from_normative_identity({"entity_id": ""}) == ""
    assert _title_from_normative_identity({"entity_id": "unknown_type:1:2025"}) == ""
    assert _title_from_normative_identity({}) == ""


def test_infer_source_title_detects_formulario_number() -> None:
    # Regex matches `formulario` followed by optional whitespace then digits;
    # underscore separator counts via \s* being zero-width, so this form matches.
    row = {"url": "https://dian.gov.co/formulario 110 renta.pdf"}
    assert _infer_source_title_from_url_or_path(row=row, doc_id="x") == "Formulario 110"


def test_infer_source_title_detects_guide_suffix() -> None:
    # Hint keyword "como-diligenciar" AND a `formulario 220` match in the path.
    row = {"relative_path": "guias/como-diligenciar/formulario 220.md"}
    assert (
        _infer_source_title_from_url_or_path(row=row, doc_id="x")
        == "Guía operativa Formulario 220"
    )


def test_infer_source_title_returns_empty_when_no_form_match() -> None:
    assert _infer_source_title_from_url_or_path(row={"url": "https://x/y.pdf"}, doc_id="x") == ""


def test_looks_like_technical_title_matches_common_slugs() -> None:
    # Each trigger uses word-boundary regexes, so separators must be non-word
    # characters (space, hyphen) to fire. Underscores are word chars and would
    # suppress the match — a quirk worth documenting here.
    assert _looks_like_technical_title("conciliacion fiscal.md") is True  # file extension
    assert _looks_like_technical_title("Ingesta RAG - normativa") is True
    assert _looks_like_technical_title("Carga Usuario documento") is True
    assert _looks_like_technical_title("Bloque 02 Formularios") is True
    assert _looks_like_technical_title("renta part 3 extra") is True  # hyphen-or-space version


def test_looks_like_technical_title_rejects_clean_titles() -> None:
    assert _looks_like_technical_title("Estatuto Tributario Artículo 290") is False
    assert _looks_like_technical_title("Ley 1819 de 2016") is False
    assert _looks_like_technical_title("") is False


def test_humanize_strips_hash_prefix_and_part_suffix() -> None:
    # Real-world inputs are filename stems after separator normalization.
    # The humanizer strips `.md`, then hex hashes and `part N` suffixes run on
    # the already-hyphenated form; underscore-only inputs don't trip the
    # word-boundary regexes until separators get normalized.
    result = _humanize_technical_title("n01 renta e45ce62d part 02.md")
    assert "e45ce62d" not in result.lower()
    assert "part" not in result.lower()
    assert ".md" not in result
    # Technical "n01" prefix stripped by _TECHNICAL_PREFIX_TOKEN_RE.
    assert result.lower().startswith("renta")


def test_humanize_applies_spanish_title_case() -> None:
    # "de", "del", "y" stay lowercase; first word capitalized.
    result = _humanize_technical_title("conciliacion fiscal de personas juridicas")
    assert result == "Conciliacion Fiscal de Personas Juridicas"


def test_humanize_handles_empty_input() -> None:
    assert _humanize_technical_title("") == ""
    assert _humanize_technical_title(None) == ""  # type: ignore[arg-type]


def test_is_generic_source_title_uses_shared_generic_set(monkeypatch) -> None:
    # The generic set lives on ui_server; mocking via the lazy accessor.
    import lia_graph.ui_source_title_resolver as mod

    fake = {"dian", "suin", "fuente", "documento"}

    class _StubUi:
        _GENERIC_SOURCE_TITLES = fake

    monkeypatch.setattr(mod, "_ui", lambda: _StubUi())
    assert _is_generic_source_title("DIAN") is True
    assert _is_generic_source_title("Fuente") is True
    assert _is_generic_source_title("Ley 1819 de 2016") is False
    # Authority echo detection
    assert _is_generic_source_title("Dian", authority="DIAN") is True
    # Empty input → treated as generic (caller must fall back)
    assert _is_generic_source_title("") is True


def test_resolve_source_display_title_walks_candidates_in_order(monkeypatch) -> None:
    import lia_graph.ui_source_title_resolver as mod

    class _StubUi:
        _GENERIC_SOURCE_TITLES = {"dian", "documento", "fuente"}

        @staticmethod
        def _clean_markdown_inline(text: str) -> str:
            return text.strip()

    monkeypatch.setattr(mod, "_ui", lambda: _StubUi())

    # source_label present → used first.
    row_a = {"source_label": "Ley 1819 de 2016", "title": "otro"}
    assert _resolve_source_display_title(row=row_a, doc_id="x") == "Ley 1819 de 2016"

    # source_label absent, title present.
    row_b = {"title": "Decreto 1625 de 2016"}
    assert _resolve_source_display_title(row=row_b, doc_id="x") == "Decreto 1625 de 2016"

    # All candidates empty → falls through to authority.
    row_c = {"authority": "DIAN"}
    assert _resolve_source_display_title(row=row_c, doc_id="") == "DIAN"

    # Nothing at all → "Fuente" default.
    assert _resolve_source_display_title(row={}, doc_id="") == "Fuente"


def test_reexport_from_host_module_has_same_identity() -> None:
    # Granularize-v2 guard: moving this cluster must not leave stale
    # definitions behind in ui_source_view_processors.
    from lia_graph.ui_source_view_processors import (
        _pick_source_display_title as host_pick,
        _normalize_source_reference_text as host_norm,
    )
    assert host_pick is _resolve_source_display_title.__globals__["_pick_source_display_title"]
    # host_norm should be bound to the same object we exported here
    assert host_norm is _normalize_source_reference_text
