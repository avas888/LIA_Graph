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
    """End-to-end behaviour: the ley URL synthesizer produces the expected pattern."""
    url = ui_citation_profile_actions._synthesize_ley_official_url(
        {"citation": {"reference_key": "ley:1819:2016"}}
    )
    assert url == "https://www.secretariasenado.gov.co/senado/basedoc/ley_1819_2016.html"


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
