"""Tests for the Phase 1.7 canonical-template validator.

All fixtures are inline per the plan doc; no external files.
"""

from __future__ import annotations

import pytest

from lia_graph import ingestion_validator
from lia_graph.ingestion_validator import (
    CANONICAL_SECTIONS,
    REQUIRED_IDENTIFICATION_KEYS,
    REQUIRED_METADATA_V2_KEYS,
    validate_canonical_template,
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


_FULL_IDENTIFICATION_VALUES = {
    "titulo": "Estatuto Tributario",
    "autoridad": "Congreso de la Republica",
    "numero": "624-1989",
    "fecha_emision": "1989-03-30",
    "fecha_vigencia": "1989-03-30",
    "ambito_tema": "tributario",
    "doc_id": "et-624-1989",
}


_FULL_METADATA_VALUES = {
    "version_canonical_template": "2026-04-18",
    "coercion_method": "heuristic_v2",
    "coercion_confidence": "0.92",
    "source_tier": "ley",
    "authority_level": "alta",
    "parse_strategy": "markdown_v1",
    "source_type": "ley",
    "corpus_family": "tributario",
    "vocabulary_labels": "renta,iva",
    "review_priority": "normal",
    "country_scope": "CO",
    "language": "es",
    "generated_at": "2026-04-18T12:00:00Z",
    "source_relative_path": "knowledge_base/tributario/et.md",
}


def _metadata_block(overrides: dict[str, str] | None = None,
                    omit: set[str] | None = None) -> str:
    values = dict(_FULL_METADATA_VALUES)
    if overrides:
        values.update(overrides)
    if omit:
        for key in omit:
            values.pop(key, None)
    bullets = [f"- {k}: {v}" for k, v in values.items()]
    return "## Metadata v2\n" + "\n".join(bullets) + "\n"


def _identification_block(overrides: dict[str, str] | None = None,
                          omit: set[str] | None = None,
                          heading: str = "## Identificacion") -> str:
    values = dict(_FULL_IDENTIFICATION_VALUES)
    if overrides:
        values.update(overrides)
    if omit:
        for key in omit:
            values.pop(key, None)
    bullets = [f"- {k}: {v}" for k, v in values.items()]
    return f"{heading}\n" + "\n".join(bullets) + "\n"


def _canonical_body(skip_section: str | None = None) -> str:
    """Build canonical sections 2..8 (Identificacion is injected separately)."""
    parts: list[str] = []
    for section in CANONICAL_SECTIONS[1:]:
        if section == skip_section:
            continue
        parts.append(f"## {section}\nContenido de {section.lower()}.\n")
    return "\n".join(parts)


def _build_doc(
    *,
    include_metadata: bool = True,
    metadata_overrides: dict[str, str] | None = None,
    metadata_omit: set[str] | None = None,
    identification_overrides: dict[str, str] | None = None,
    identification_omit: set[str] | None = None,
    identification_heading: str = "## Identificacion",
    skip_section: str | None = None,
    swap_last_two: bool = False,
) -> str:
    chunks: list[str] = []
    if include_metadata:
        chunks.append(_metadata_block(metadata_overrides, metadata_omit))
    chunks.append(
        _identification_block(
            identification_overrides,
            identification_omit,
            heading=identification_heading,
        )
    )
    if swap_last_two:
        # Emit sections 2..6 in order, then Historico before Checklist.
        for section in CANONICAL_SECTIONS[1:6]:
            chunks.append(f"## {section}\nContenido de {section.lower()}.\n")
        chunks.append("## Historico de cambios\nContenido.\n")
        chunks.append("## Checklist de vigencia\nContenido.\n")
    else:
        chunks.append(_canonical_body(skip_section=skip_section))
    return "\n".join(chunks)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_a_fully_canonical_doc_is_ok() -> None:
    markdown = _build_doc()
    result = validate_canonical_template(markdown)
    assert result.ok is True
    assert result.missing_sections == ()
    assert result.sections_out_of_order == ()
    assert result.missing_keys == ()
    assert result.missing_metadata == ()
    assert result.sections_found == CANONICAL_SECTIONS
    assert result.strict is True


def test_b_missing_riesgos_section() -> None:
    markdown = _build_doc(skip_section="Riesgos de interpretacion")
    result = validate_canonical_template(markdown)
    assert result.ok is False
    assert result.missing_sections == ("Riesgos de interpretacion",)
    assert result.missing_keys == ()
    assert result.missing_metadata == ()


def test_c_sections_out_of_order() -> None:
    markdown = _build_doc(swap_last_two=True)
    result = validate_canonical_template(markdown)
    assert result.ok is False
    # All 8 sections are still present.
    assert result.missing_sections == ()
    # Checklist appears AFTER Historico -> Checklist is the out-of-order one.
    assert "Checklist de vigencia" in result.sections_out_of_order


def test_d_identification_missing_doc_id() -> None:
    markdown = _build_doc(identification_omit={"doc_id"})
    result = validate_canonical_template(markdown)
    assert result.ok is False
    assert result.missing_keys == ("doc_id",)
    assert result.missing_sections == ()


def test_e_identification_value_is_sin_datos_counts_as_missing() -> None:
    markdown = _build_doc(identification_overrides={"autoridad": "(sin datos)"})
    result = validate_canonical_template(markdown)
    assert result.ok is False
    assert "autoridad" in result.missing_keys


def test_f_metadata_v2_missing_generated_at_strict_vs_non_strict() -> None:
    markdown = _build_doc(metadata_omit={"generated_at"})
    strict = validate_canonical_template(markdown, strict=True)
    assert strict.ok is False
    assert strict.missing_metadata == ("generated_at",)

    non_strict = validate_canonical_template(markdown, strict=False)
    assert non_strict.ok is True
    assert non_strict.missing_metadata == ()
    assert non_strict.strict is False


def test_g_metadata_v2_sin_datos_is_accepted_in_both_modes() -> None:
    overrides = {key: "(sin datos)" for key in REQUIRED_METADATA_V2_KEYS}
    markdown = _build_doc(metadata_overrides=overrides)
    strict = validate_canonical_template(markdown, strict=True)
    assert strict.ok is True
    assert strict.missing_metadata == ()

    non_strict = validate_canonical_template(markdown, strict=False)
    assert non_strict.ok is True
    assert non_strict.missing_metadata == ()


def test_h_accent_insensitive_heading_match() -> None:
    markdown = _build_doc(identification_heading="## Identificación")
    result = validate_canonical_template(markdown)
    assert result.ok is True
    assert "Identificacion" in result.sections_found
    assert result.missing_keys == ()


def test_i_emit_events_records_ok_event(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[tuple[str, dict]] = []

    def _fake_emit(event_type: str, payload: dict, *args, **kwargs) -> None:
        captured.append((event_type, payload))

    monkeypatch.setattr(ingestion_validator.instrumentation, "emit_event", _fake_emit)

    markdown = _build_doc()
    result = validate_canonical_template(
        markdown, emit_events=True, filename="et.md"
    )
    assert result.ok is True
    assert len(captured) == 1
    event_type, payload = captured[0]
    assert event_type == "ingest.validate.ok"
    assert payload["doc_id"] == "et-624-1989"
    assert payload["sections_matched_count"] == len(CANONICAL_SECTIONS)


def test_j_emit_events_records_failed_event_with_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, dict]] = []

    def _fake_emit(event_type: str, payload: dict, *args, **kwargs) -> None:
        captured.append((event_type, payload))

    monkeypatch.setattr(ingestion_validator.instrumentation, "emit_event", _fake_emit)

    markdown = _build_doc(
        skip_section="Riesgos de interpretacion",
        identification_omit={"doc_id"},
    )
    result = validate_canonical_template(
        markdown, emit_events=True, filename="broken.md"
    )
    assert result.ok is False
    assert len(captured) == 1
    event_type, payload = captured[0]
    assert event_type == "ingest.validate.failed"
    assert payload["filename"] == "broken.md"
    # doc_id bullet was removed -> event payload falls back to filename label.
    assert payload["doc_id"] is None
    assert payload["label"] == "broken.md"
    assert "Riesgos de interpretacion" in payload["missing_sections"]
    assert "doc_id" in payload["missing_keys"]


def test_k_emit_events_disabled_by_default_does_not_call_instrumentation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict]] = []

    def _fake_emit(event_type: str, payload: dict, *args, **kwargs) -> None:
        calls.append((event_type, payload))

    monkeypatch.setattr(ingestion_validator.instrumentation, "emit_event", _fake_emit)

    validate_canonical_template(_build_doc())
    assert calls == []


def test_required_identification_keys_match_contract() -> None:
    # Safety net: if this tuple ever changes, tests above must be revisited.
    assert REQUIRED_IDENTIFICATION_KEYS == (
        "titulo",
        "autoridad",
        "numero",
        "fecha_emision",
        "fecha_vigencia",
        "ambito_tema",
        "doc_id",
    )
    assert len(REQUIRED_METADATA_V2_KEYS) == 14
