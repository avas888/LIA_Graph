"""Unit tests for `lia_graph.ui_source_view_noise_filter`.

The noise filter is the single biggest reason the source-view modal shows
useful content from DIAN's normograma pages (which are otherwise dense
with nav chrome, accessibility icons, and `<option>` dropdowns). These
tests lock in the "drop or keep" rules so future additions to the hint
lists don't silently broaden the drop filter.
"""

from __future__ import annotations

from lia_graph.ui_source_view_noise_filter import (
    _SOURCE_VIEW_USEFUL_HINT_RE,
    _is_source_view_noise_text,
    _trim_source_view_content_markers,
)


def test_trim_content_markers_strips_prefix() -> None:
    raw = "Menu bar · navegación · Contenido principal: El artículo 290 del ET…"
    out = _trim_source_view_content_markers(raw)
    assert out == "El artículo 290 del ET…"


def test_trim_content_markers_passthrough_when_no_marker() -> None:
    raw = "Sin marcador, solo texto."
    assert _trim_source_view_content_markers(raw) == raw


def test_trim_content_markers_handles_empty() -> None:
    assert _trim_source_view_content_markers("") == ""
    assert _trim_source_view_content_markers("   ") == ""


def test_is_noise_flags_social_icons() -> None:
    # Each individual hint (like "icono twitter") is in the HTML noise list.
    assert _is_source_view_noise_text("icono twitter icono facebook") is True
    # "icono instagram" is also explicitly listed in _SOURCE_VIEW_HTML_NOISE_HINTS.
    assert _is_source_view_noise_text("icono instagram") is True
    # A bare "icono " without any listed hint but ≥2 occurrences still trips the count guard.
    assert _is_source_view_noise_text("icono xxx icono yyy") is True
    # Single unknown "icono" does not flag.
    assert _is_source_view_noise_text("icono xxx about something normal") is False


def test_is_noise_flags_scaffold_text() -> None:
    assert _is_source_view_noise_text("resumen tecnico inicial para seed documental") is True
    assert _is_source_view_noise_text("claim en construcción") is True


def test_is_noise_flags_portal_dian() -> None:
    # "portal dian" is in the HTML noise list — always flagged.
    assert _is_source_view_noise_text("Portal DIAN - Navegación") is True
    # Even with useful keywords alongside, the hint set wins first.
    assert _is_source_view_noise_text("Portal DIAN - formulario 110 declaración de renta") is True


def test_is_noise_empty_is_noise() -> None:
    assert _is_source_view_noise_text("") is True
    assert _is_source_view_noise_text("   \n  ") is True


def test_is_noise_rejects_normal_tax_prose() -> None:
    assert _is_source_view_noise_text("El artículo 290 regula el régimen de transición.") is False
    assert _is_source_view_noise_text("Formulario 220 para personas jurídicas no residentes.") is False


def test_useful_hint_re_matches_tax_terms() -> None:
    assert _SOURCE_VIEW_USEFUL_HINT_RE.search("presenta el formulario 110") is not None
    assert _SOURCE_VIEW_USEFUL_HINT_RE.search("declaración de renta") is not None
    assert _SOURCE_VIEW_USEFUL_HINT_RE.search("resolución 238 de 2025") is not None
    assert _SOURCE_VIEW_USEFUL_HINT_RE.search("random unrelated text") is None
