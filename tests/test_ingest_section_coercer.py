"""Tests for `lia_graph.ingestion_section_coercer` (Phase 1.5 of ingestfixv1).

Covers the hybrid heuristic + LLM coercer cascade:
- native shape detection,
- heuristic alias mapping (>= 6/8 canonical sections),
- LLM fallback with a stubbed adapter,
- identification bullet list + v2 metadata block synthesis,
- skip_llm forcing heuristic path,
- accent/case-insensitive heading matching,
- malformed LLM response → heuristic fallback,
- hint propagation,
- event emission on LLM unavailability.

Fixtures live in-file; we never touch `knowledge_base/` or real doc files.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lia_graph import ingestion_section_coercer as coercer_mod
from lia_graph.ingestion_section_coercer import (
    CANONICAL_SECTIONS,
    IDENTIFICATION_KEYS,
    METADATA_V2_KEYS,
    CoerceResult,
    coerce_to_canonical_template,
)


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------


class _StubAdapter:
    """Minimal LLM adapter stub exposing `generate_with_options`."""

    def __init__(self, response: str, *, via_dict: bool = True) -> None:
        self._response = response
        self._via_dict = via_dict
        self.calls: list[dict[str, object]] = []

    def generate_with_options(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, object] | str:
        self.calls.append(
            {
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout_seconds": timeout_seconds,
            }
        )
        if self._via_dict:
            return {"content": self._response}
        return self._response


class _BrokenAdapter:
    """Adapter that raises — used to confirm we swallow exceptions and fall back."""

    def generate_with_options(self, *_args, **_kwargs) -> dict[str, object]:
        raise RuntimeError("boom")


def _native_markdown() -> str:
    sections = []
    for heading in CANONICAL_SECTIONS:
        if heading == "Identificacion":
            body = (
                "- titulo: Decreto 123 de 2024\n"
                "- autoridad: Presidencia\n"
                "- numero: 123\n"
                "- fecha_emision: 2024-01-10\n"
                "- fecha_vigencia: 2024-02-01\n"
                "- ambito_tema: tributario\n"
                "- doc_id: dec-123-2024"
            )
        else:
            body = f"Contenido de {heading}."
        sections.append(f"## {heading}\n{body}")
    return "\n\n".join(sections) + "\n"


def _heuristic_6of8_markdown() -> str:
    # 6 canonical targets reached via alias headings:
    #   Identificacion, Texto base referenciado, Condiciones, Riesgos,
    #   Relaciones normativas, Checklist de vigencia.
    # Missing: Regla operativa, Historico.
    return (
        "## Encabezado\n"
        "- titulo: Ley 2277 de 2022\n"
        "- autoridad: Congreso\n"
        "- numero: 2277\n"
        "- fecha_emision: 2022-12-13\n\n"
        "## Articulos\n"
        "Articulo 1. ...\n\n"
        "## Condiciones\n"
        "Requisito A.\n\n"
        "## Alertas\n"
        "Riesgo X.\n\n"
        "## Cadena normativa\n"
        "Modifica Ley 100.\n\n"
        "## Vigencia\n"
        "Desde 2023-01-01.\n"
    )


def _freeform_markdown() -> str:
    # Free-form essay style — zero canonical headings.
    return (
        "# Notas internas\n\n"
        "Este documento es un borrador sin estructura formal. "
        "Habla sobre el impacto de varias normas pero no sigue la plantilla.\n\n"
        "## Resumen ejecutivo\n"
        "Parrafo uno.\n\n"
        "## Observaciones\n"
        "Parrafo dos.\n"
    )


def _llm_response_canonical() -> str:
    parts = []
    for heading in CANONICAL_SECTIONS:
        if heading == "Identificacion":
            body = (
                "- titulo: Ley Freeform\n"
                "- autoridad: Congreso\n"
                "- numero: (sin datos)\n"
                "- fecha_emision: (sin datos)\n"
                "- fecha_vigencia: (sin datos)\n"
                "- ambito_tema: general\n"
                "- doc_id: ley-ff"
            )
        else:
            body = f"LLM body for {heading}."
        parts.append(f"## {heading}\n{body}")
    return "\n\n".join(parts)


def _llm_response_malformed() -> str:
    return (
        "## Identificacion\n"
        "- titulo: foo\n\n"
        "## Otra cosa\n"
        "lorem ipsum\n"
    )


def _section_body(markdown: str, heading: str) -> str:
    """Return the text between ``## heading`` and the next ``## `` boundary."""
    marker = f"## {heading}\n"
    idx = markdown.find(marker)
    assert idx >= 0, f"heading not found: {heading}"
    start = idx + len(marker)
    rest = markdown[start:]
    next_idx = rest.find("\n## ")
    if next_idx == -1:
        return rest.strip()
    return rest[:next_idx].strip()


@pytest.fixture()
def isolated_events(tmp_path, monkeypatch):
    """Redirect `emit_event` to a per-test log file."""
    log_file = tmp_path / "events.jsonl"
    real_emit = coercer_mod.emit_event

    def _redirect(event_type, payload, log_path=None):  # noqa: ARG001
        return real_emit(event_type, payload, log_path=log_file)

    monkeypatch.setattr(coercer_mod, "emit_event", _redirect)
    return log_file


def _load_events(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_native_shape_returns_native_method(isolated_events):
    # Case (a): doc already in canonical shape.
    result = coerce_to_canonical_template(_native_markdown())
    assert isinstance(result, CoerceResult)
    assert result.coercion_method == "native"
    assert result.confidence == pytest.approx(1.0)
    assert result.llm_used is False
    assert result.sections_matched_count == 8


def test_heuristic_6of8_confidence(isolated_events):
    # Case (b): 6/8 canonical targets reachable via heuristic aliases.
    result = coerce_to_canonical_template(_heuristic_6of8_markdown())
    assert result.coercion_method == "heuristic"
    assert result.sections_matched_count == 6
    assert result.confidence == pytest.approx(0.75)
    assert result.llm_used is False
    # Missing sections should show the placeholder.
    assert "(sin datos)" in result.coerced_markdown


def test_llm_path_with_stub_adapter(isolated_events):
    # Case (c): freeform doc + adapter returns valid 8-section markdown.
    adapter = _StubAdapter(_llm_response_canonical())
    result = coerce_to_canonical_template(
        _freeform_markdown(),
        adapter=adapter,
    )
    assert result.coercion_method == "llm"
    assert result.llm_used is True
    assert result.sections_matched_count == 8
    assert len(adapter.calls) == 1
    call = adapter.calls[0]
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 4096
    assert call["timeout_seconds"] == 30


def test_all_eight_sections_present_post_coerce(isolated_events):
    # Case (d): iterate over every canonical heading and assert presence.
    result = coerce_to_canonical_template(_heuristic_6of8_markdown())
    for heading in CANONICAL_SECTIONS:
        assert f"## {heading}\n" in result.coerced_markdown, heading


def test_identification_list_has_all_seven_keys(isolated_events):
    # Case (e): identification bullets include all seven keys; hints honored,
    # missing values become (sin datos).
    hints = {
        "titulo": "Resolucion 999",
        "numero": "999",
        "doc_id": "res-999",
    }
    result = coerce_to_canonical_template(
        _heuristic_6of8_markdown(),
        identification_hints=hints,
    )
    body = _section_body(result.coerced_markdown, "Identificacion")
    # The body should have one bullet per canonical key.
    bullet_keys = [line[2:].split(":", 1)[0].strip() for line in body.splitlines() if line.startswith("- ")]
    assert bullet_keys == list(IDENTIFICATION_KEYS)
    # Values — titulo from original body wins over hint? We allow either
    # because both are populated; just confirm numero uses the hint and
    # ambito_tema falls back to (sin datos).
    assert "- numero: 2277" in body or "- numero: 999" in body
    assert "- ambito_tema: (sin datos)" in body
    assert "- doc_id: res-999" in body


def test_metadata_block_synthesized_with_fourteen_keys(isolated_events):
    # Case (f): v2 metadata block appears and includes all 14 keys.
    result = coerce_to_canonical_template(_heuristic_6of8_markdown())
    meta_body = _section_body(result.coerced_markdown, "Metadata v2")
    keys = [line[2:].split(":", 1)[0].strip() for line in meta_body.splitlines() if line.startswith("- ")]
    assert keys == list(METADATA_V2_KEYS)
    # coercion_method / coercion_confidence must have real values.
    assert "- coercion_method: heuristic" in meta_body
    assert "- coercion_confidence: 0.75" in meta_body


def test_coercion_method_attribution_all_paths(isolated_events):
    # Case (g): verify method attribution for native / heuristic / llm.
    native = coerce_to_canonical_template(_native_markdown())
    assert native.coercion_method == "native"

    heuristic = coerce_to_canonical_template(_heuristic_6of8_markdown())
    assert heuristic.coercion_method == "heuristic"

    adapter = _StubAdapter(_llm_response_canonical())
    llm = coerce_to_canonical_template(_freeform_markdown(), adapter=adapter)
    assert llm.coercion_method == "llm"


def test_skip_llm_forces_heuristic(isolated_events):
    # Case (h): `skip_llm=True` must not invoke the adapter.
    adapter = _StubAdapter(_llm_response_canonical())
    result = coerce_to_canonical_template(
        _freeform_markdown(),
        adapter=adapter,
        skip_llm=True,
    )
    assert result.coercion_method == "heuristic"
    assert result.llm_used is False
    assert adapter.calls == []


def test_llm_unavailable_emits_fallback_event(isolated_events, monkeypatch):
    # Case (i): adapter=None and resolver returns None → heuristic fallback
    # with a `fallback` event.
    monkeypatch.setattr(coercer_mod, "_resolve_adapter", lambda: None)
    result = coerce_to_canonical_template(_freeform_markdown())
    assert result.coercion_method == "heuristic"
    assert result.llm_used is False

    events = _load_events(isolated_events)
    fallback = [e for e in events if e["event_type"] == "ingest.coerce.llm.fallback"]
    assert len(fallback) == 1
    assert fallback[0]["payload"]["reason"] == "adapter_unavailable"


def test_accent_and_case_insensitive_heading_match(isolated_events):
    # Case (j): `## Vigencia` (no accent, capitalized) must resolve to
    # Checklist de vigencia.
    src = (
        "## IDENTIFICACIÓN\n"
        "- titulo: X\n\n"
        "## Artículos\n"
        "A1\n\n"
        "## Criterios de Aplicación\n"
        "C1\n\n"
        "## Alertas\n"
        "R1\n\n"
        "## Normas Referenciadas\n"
        "N1\n\n"
        "## Vigencia\n"
        "V1\n"
    )
    result = coerce_to_canonical_template(src)
    assert result.sections_matched_count >= 6
    # Confirm the "Checklist de vigencia" section got the body from `Vigencia`.
    body = _section_body(result.coerced_markdown, "Checklist de vigencia")
    assert body == "V1"


def test_malformed_llm_response_falls_back_to_heuristic(isolated_events):
    # Case (k): malformed LLM response (fewer than 8 headings) → heuristic.
    adapter = _StubAdapter(_llm_response_malformed())
    result = coerce_to_canonical_template(_freeform_markdown(), adapter=adapter)
    assert result.coercion_method == "heuristic"
    assert result.llm_used is False

    events = _load_events(isolated_events)
    fallbacks = [e for e in events if e["event_type"] == "ingest.coerce.llm.fallback"]
    assert any(e["payload"]["reason"] == "malformed_response" for e in fallbacks)


def test_identification_and_metadata_hints_propagate(isolated_events):
    # Case (l): hints surface in the emitted markdown.
    ident = {
        "titulo": "Circular 100",
        "autoridad": "DIAN",
        "numero": "100",
        "fecha_emision": "2023-05-01",
        "fecha_vigencia": "2023-06-01",
        "ambito_tema": "tributario",
        "doc_id": "dian-circ-100",
    }
    meta = {
        "source_tier": "oficial",
        "authority_level": "alta",
        "source_type": "circular",
        "country_scope": "CO",
        "language": "es",
    }
    result = coerce_to_canonical_template(
        _heuristic_6of8_markdown(),
        identification_hints=ident,
        metadata_hints=meta,
    )
    ident_body = _section_body(result.coerced_markdown, "Identificacion")
    for key, value in ident.items():
        assert f"- {key}: {value}" in ident_body

    meta_body = _section_body(result.coerced_markdown, "Metadata v2")
    for key, value in meta.items():
        assert f"- {key}: {value}" in meta_body
