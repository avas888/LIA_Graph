"""Smoke tests for the three sibling modules extracted from
`ui_citation_profile_builders.py` during granularize-v2 round 12:

  * `ui_citation_profile_actions` (action resolvers)
  * `ui_citation_profile_context` (context collectors)
  * `ui_citation_profile_llm` (LLM prompt / facts builder)
  * `ui_citation_profile_sections` (section builders)

The heavy end-to-end behaviour is covered by existing
`test_normativa_surface.py` fixtures — these tests just lock in the
re-export identity contract so the host's back-compat re-imports keep
pointing at the new implementations.
"""

from __future__ import annotations

from lia_graph import ui_citation_profile_builders as host
from lia_graph import (
    ui_citation_profile_actions,
    ui_citation_profile_context,
    ui_citation_profile_llm,
    ui_citation_profile_sections,
)


def test_action_resolvers_reexport_identity() -> None:
    assert host._resolve_companion_action is ui_citation_profile_actions._resolve_companion_action
    assert host._resolve_analysis_action is ui_citation_profile_actions._resolve_analysis_action
    assert host._resolve_source_action is ui_citation_profile_actions._resolve_source_action
    assert host._load_decreto_official_urls is ui_citation_profile_actions._load_decreto_official_urls
    assert host._lookup_decreto_official_url is ui_citation_profile_actions._lookup_decreto_official_url
    assert host._synthesize_ley_official_url is ui_citation_profile_actions._synthesize_ley_official_url


def test_action_constants_reexport_identity() -> None:
    # Values (not identity, since strings may be interned) — but still the
    # host references must resolve through the re-export.
    assert host._CITATION_PROFILE_GUIDE_PROMPT == ui_citation_profile_actions._CITATION_PROFILE_GUIDE_PROMPT
    assert host._CITATION_PROFILE_ORIGINAL_LABEL == ui_citation_profile_actions._CITATION_PROFILE_ORIGINAL_LABEL


def test_context_collectors_reexport_identity() -> None:
    assert host._collect_citation_profile_context is ui_citation_profile_context._collect_citation_profile_context
    assert (
        host._collect_citation_profile_context_by_reference_key
        is ui_citation_profile_context._collect_citation_profile_context_by_reference_key
    )


def test_llm_reexport_identity() -> None:
    assert host._build_citation_profile_prompt is ui_citation_profile_llm._build_citation_profile_prompt
    assert host._llm_citation_profile_payload is ui_citation_profile_llm._llm_citation_profile_payload
    assert host._should_skip_citation_profile_llm is ui_citation_profile_llm._should_skip_citation_profile_llm
    assert host._build_citation_profile_facts is ui_citation_profile_llm._build_citation_profile_facts
    assert host._append_citation_profile_fact is ui_citation_profile_llm._append_citation_profile_fact


def test_sections_reexport_identity() -> None:
    assert host._build_citation_profile_sections is ui_citation_profile_sections._build_citation_profile_sections
    assert (
        host._build_citation_profile_original_text_section
        is ui_citation_profile_sections._build_citation_profile_original_text_section
    )
    assert (
        host._build_citation_profile_expert_section
        is ui_citation_profile_sections._build_citation_profile_expert_section
    )
    assert (
        host._citation_profile_analysis_candidates
        is ui_citation_profile_sections._citation_profile_analysis_candidates
    )
    assert (
        host._extract_locator_excerpt_from_text
        is ui_citation_profile_sections._extract_locator_excerpt_from_text
    )
    assert host._summarize_analysis_excerpt is ui_citation_profile_sections._summarize_analysis_excerpt


def test_action_synthesize_ley_url_for_ley_reference() -> None:
    """End-to-end behaviour: the ley URL synthesizer produces the expected pattern.

    HTTP-only — Senado has no HTTPS listener. See the synthesizer's docstring."""
    url = ui_citation_profile_actions._synthesize_ley_official_url(
        {"citation": {"reference_key": "ley:1819:2016"}}
    )
    assert url == "http://www.secretariasenado.gov.co/senado/basedoc/ley_1819_2016.html"


def test_action_synthesize_ley_url_zero_pads_short_law_numbers() -> None:
    """Senado zero-pads law numbers shorter than 4 digits (ley_0100_1993)."""
    url = ui_citation_profile_actions._synthesize_ley_official_url(
        {"citation": {"reference_key": "ley:100:1993"}}
    )
    assert url == "http://www.secretariasenado.gov.co/senado/basedoc/ley_0100_1993.html"


def test_action_companion_not_applicable_for_non_formulario() -> None:
    result = ui_citation_profile_actions._resolve_companion_action(
        {"document_family": "ley"}
    )
    assert result == {
        "label": "¿Quieres una guía sobre cómo llenarlo?",
        "state": "not_applicable",
        "url": None,
        "helper_text": None,
    }


class _UiStub:
    """Minimal stand-in for the lazy `ui_server` module used by
    `_resolve_source_action`. Only the helpers the resolver actually
    calls are implemented; everything else stays out of the test path."""

    @staticmethod
    def _coerce_http_url(value):  # type: ignore[no-untyped-def]
        s = str(value or "").strip()
        return s if s.startswith(("http://", "https://")) else ""

    @staticmethod
    def _prefer_normograma_mintic_mirror(url):  # type: ignore[no-untyped-def]
        from lia_graph.ui_normograma_urls import _prefer_normograma_mintic_mirror as impl
        return impl(url)

    @staticmethod
    def _prefer_secretariasenado_for_et(url):  # type: ignore[no-untyped-def]
        from lia_graph.ui_normograma_urls import _prefer_secretariasenado_for_et as impl
        return impl(url)

    @staticmethod
    def _citation_targets_et_article(citation):  # type: ignore[no-untyped-def]
        return False

    @staticmethod
    def _citation_et_locator_label(citation):  # type: ignore[no-untyped-def]
        return ""

    @staticmethod
    def _sanitize_url_candidate(value):  # type: ignore[no-untyped-def]
        return str(value or "").strip()


def test_source_action_swaps_et_to_secretariasenado(monkeypatch) -> None:
    """An ET fragment URL on DIAN/MinTIC is rewritten to Secretaría del
    Senado's per-section file when the article is in the map. No MinTIC
    reload hint needed — Senado's per-section files are small enough that
    the anchor-scroll race doesn't happen."""
    monkeypatch.setattr(ui_citation_profile_actions, "_ui", lambda: _UiStub)
    result = ui_citation_profile_actions._resolve_source_action(
        {
            "citation": {
                "official_url": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm#107",
            },
            "document_family": "et_dur",
        }
    )
    assert result["url"] == (
        "http://www.secretariasenado.gov.co/senado/basedoc/estatuto_tributario_pr004.html#107"
    )
    assert result["mode"] == "official_link"
    assert result["helper_text"] is None


def test_source_action_swaps_et_landing_article_to_senado(monkeypatch) -> None:
    """Articles 1–21 live on Senado's landing page (no _pr suffix)."""
    monkeypatch.setattr(ui_citation_profile_actions, "_ui", lambda: _UiStub)
    result = ui_citation_profile_actions._resolve_source_action(
        {
            "citation": {
                "official_url": "https://normograma.mintic.gov.co/mintic/compilacion/docs/estatuto_tributario.htm#5",
            },
            "document_family": "et_dur",
        }
    )
    assert result["url"] == (
        "http://www.secretariasenado.gov.co/senado/basedoc/estatuto_tributario.html#5"
    )
    assert result["helper_text"] is None


def test_source_action_falls_back_to_mintic_when_article_not_in_map(monkeypatch) -> None:
    """If the article number isn't in the Senado map, the URL stays on the
    MinTIC mirror (defense-in-depth so unmapped/future bis articles still
    resolve to a working page). No helper text — Senado covers the entire
    current ET, and the fallback is rare enough that surfacing a reload hint
    on every clickable ET citation was deemed more noise than signal."""
    monkeypatch.setattr(ui_citation_profile_actions, "_ui", lambda: _UiStub)
    result = ui_citation_profile_actions._resolve_source_action(
        {
            "citation": {
                "official_url": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm#9999",
            },
            "document_family": "et_dur",
        }
    )
    assert result["url"] == (
        "https://normograma.mintic.gov.co/mintic/compilacion/docs/estatuto_tributario.htm#9999"
    )
    assert result["helper_text"] is None


def test_source_action_no_hint_for_non_et_official_url(monkeypatch) -> None:
    """Senado ley URLs (and any non-ET official link) stay hint-free and
    are not swapped — the Senado ET helper only touches ET compilation URLs."""
    monkeypatch.setattr(ui_citation_profile_actions, "_ui", lambda: _UiStub)
    result = ui_citation_profile_actions._resolve_source_action(
        {
            "citation": {
                "official_url": "https://www.secretariasenado.gov.co/senado/basedoc/ley_1819_2016.html",
            },
            "document_family": "ley",
        }
    )
    assert result["url"] == "https://www.secretariasenado.gov.co/senado/basedoc/ley_1819_2016.html"
    assert result["helper_text"] is None


def test_source_action_no_hint_for_mintic_url_without_fragment(monkeypatch) -> None:
    """A MinTIC URL with no fragment doesn't trigger the anchor race — no hint
    and no Senado swap (the helper needs a fragment to look up the article)."""
    monkeypatch.setattr(ui_citation_profile_actions, "_ui", lambda: _UiStub)
    result = ui_citation_profile_actions._resolve_source_action(
        {
            "citation": {
                "official_url": "https://normograma.mintic.gov.co/mintic/compilacion/docs/estatuto_tributario.htm",
            },
            "document_family": "et_dur",
        }
    )
    assert result["url"] == (
        "https://normograma.mintic.gov.co/mintic/compilacion/docs/estatuto_tributario.htm"
    )
    assert result["helper_text"] is None


def test_prefer_secretariasenado_for_et_bis_article() -> None:
    """Bis articles (e.g., 102-2) resolve to their pr file via the map."""
    from lia_graph.ui_normograma_urls import _prefer_secretariasenado_for_et
    result = _prefer_secretariasenado_for_et(
        "https://normograma.mintic.gov.co/mintic/compilacion/docs/estatuto_tributario.htm#102-2"
    )
    assert result == (
        "http://www.secretariasenado.gov.co/senado/basedoc/estatuto_tributario_pr004.html#102-2"
    )


def test_prefer_secretariasenado_for_et_passes_through_unknown_host() -> None:
    """URLs from other hosts (no Normograma/MinTIC prefix) are returned unchanged."""
    from lia_graph.ui_normograma_urls import _prefer_secretariasenado_for_et
    other = "https://example.com/something.htm#107"
    assert _prefer_secretariasenado_for_et(other) == other
    # Empty / None handling
    assert _prefer_secretariasenado_for_et("") == ""
    assert _prefer_secretariasenado_for_et(None) == ""
