"""next_v3.md §7 step 4 — unit test on the taxonomy-aware classifier prompt.

Mocks no LLM. Asserts the *shape* of the redesigned prompt:
  - Full v2 taxonomy enumerated as a numbered candidate list;
  - The 6 SME mutex rules named and numbered (1..6);
  - Path-veto clause present (RENTA/NORMATIVA/ hint);
  - Default-to-parent rule present;
  - Identical JSON output schema to v1 (so downstream parsers don't break).

The tests toggle ``LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE`` and verify the
right template fires.
"""

from __future__ import annotations

import pytest

from lia_graph.ingestion_classifier import (
    _AUTOGENERAR_PROMPT_TEMPLATE,
    _build_mutex_block,
    _build_n2_prompt,
    _build_numbered_taxonomy_block,
    _build_taxonomy_aware_prompt,
    classifier_taxonomy_mode,
)
from lia_graph.subtopic_taxonomy_loader import load_taxonomy as load_subtopic_taxonomy


EXPECTED_MUTEX_RULE_NAMES = (
    "iva vs procedimiento tributario",
    "iva vs familia renta",
    "comercial societario fusion",
    "facturacion electronica vs impuesto timbre",
    "rub vs rut",
    "laboral family",
)


def test_classifier_taxonomy_mode_defaults_to_off(monkeypatch) -> None:
    monkeypatch.delenv("LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE", raising=False)
    assert classifier_taxonomy_mode() == "off"


@pytest.mark.parametrize("mode", ["off", "shadow", "enforce", "bogus"])
def test_classifier_taxonomy_mode_normalizes(monkeypatch, mode: str) -> None:
    monkeypatch.setenv("LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE", mode)
    expected = mode if mode in ("off", "shadow", "enforce") else "off"
    assert classifier_taxonomy_mode() == expected


def test_numbered_taxonomy_block_enumerates_all_active_topics() -> None:
    """Every active v2 topic must appear in the numbered list; deprecated omitted."""
    block = _build_numbered_taxonomy_block()
    # Active topics
    for key in (
        "impuesto_timbre",
        "rut_y_responsabilidades_tributarias",
        "parafiscales_seguridad_social",
        "niif_pymes",
        "regimen_cambiario",
        "regimen_tributario_especial_esal",
        "dividendos_y_distribucion_utilidades",
        "declaracion_renta",
        "iva",
        "procedimiento_tributario",
    ):
        assert f" {key} " in block, f"missing active topic {key} in numbered list"
    # Deprecated topic (estados_financieros_niif) should NOT appear as a candidate.
    assert " estados_financieros_niif " not in block
    # Enumeration is numbered — first line starts with "1."
    first_line = block.split("\n", 1)[0]
    assert first_line.startswith("1."), f"expected numbered list, got: {first_line!r}"


def test_numbered_taxonomy_block_includes_subtopic_parent_notes() -> None:
    block = _build_numbered_taxonomy_block()
    # firmeza_declaraciones was moved to procedimiento_tributario (SME §1.4).
    assert "firmeza_declaraciones" in block
    assert "(subtema de procedimiento_tributario)" in block
    # renta_presuntiva is a NEW subtopic under declaracion_renta.
    assert "renta_presuntiva" in block
    assert "(subtema de declaracion_renta)" in block


def test_mutex_block_contains_six_numbered_rules() -> None:
    block = _build_mutex_block()
    for i in range(1, 7):
        assert f"REGLA {i}" in block, f"missing REGLA {i} heading"
    for name in EXPECTED_MUTEX_RULE_NAMES:
        assert name in block.lower(), f"missing mutex rule {name!r}"


def test_taxonomy_aware_prompt_contains_all_sme_fixtures() -> None:
    taxonomy = load_subtopic_taxonomy()
    prompt = _build_taxonomy_aware_prompt(
        filename="RENTA/NORMATIVA/Normativa/06_Libro1_T1_Cap5_Deducciones.md",
        body_preview="Artículo 148 del Estatuto Tributario — pérdidas fiscales.",
        subtopic_taxonomy=taxonomy,
    )
    # Full taxonomy enumerated (spot-check 3 SME-promised topics).
    assert " impuesto_timbre " in prompt
    assert " niif_pymes " in prompt
    assert " parafiscales_seguridad_social " in prompt
    # 6 mutex rules present & numbered.
    for i in range(1, 7):
        assert f"REGLA {i}" in prompt
    # Path-veto clause (SME §7 / next_v3 §7 plan).
    assert "PATH VETO" in prompt
    assert "RENTA/NORMATIVA/" in prompt
    assert "Libro 3 ET" in prompt or "Libro 3 et" in prompt.lower()
    # Default-to-parent rule (SME §4.2).
    assert "PADRE" in prompt or "padre" in prompt
    # Identical JSON schema to v1 — every field the parser expects must
    # appear in the response-shape example.
    for field in (
        "generated_label",
        "rationale",
        "resolved_to_existing",
        "synonym_confidence",
        "is_new_topic",
        "suggested_key",
        "detected_type",
        "subtopic_resolved_to_existing",
        "subtopic_synonym_confidence",
        "subtopic_is_new",
        "subtopic_suggested_key",
        "subtopic_label",
    ):
        assert field in prompt, f"prompt missing response field: {field}"


def test_build_n2_prompt_selects_v1_when_flag_off(monkeypatch) -> None:
    monkeypatch.setenv("LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE", "off")
    prompt = _build_n2_prompt("Ley_2277.md", "Texto de ejemplo.")
    # v1 template's hallmark phrase is "PASO 1" + "genera UNA etiqueta"
    assert "PASO 1" in prompt
    # v2 template's hallmark — PATH VETO — must NOT appear.
    assert "PATH VETO" not in prompt
    assert "REGLA 1" not in prompt


def test_build_n2_prompt_selects_v2_when_flag_enforce(monkeypatch) -> None:
    monkeypatch.setenv("LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE", "enforce")
    prompt = _build_n2_prompt("Ley_2277.md", "Texto de ejemplo.")
    assert "PATH VETO" in prompt
    assert "REGLA 1" in prompt
    assert "REGLA 6" in prompt


def test_build_n2_prompt_selects_v2_when_flag_shadow(monkeypatch) -> None:
    monkeypatch.setenv("LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE", "shadow")
    prompt = _build_n2_prompt("Ley_2277.md", "Texto de ejemplo.")
    assert "PATH VETO" in prompt
    assert "REGLA 1" in prompt


def test_v2_prompt_preserves_v1_output_schema_keys() -> None:
    """Downstream parser contract — JSON field set matches v1 exactly."""
    v1_fields = {
        "generated_label",
        "rationale",
        "resolved_to_existing",
        "synonym_confidence",
        "is_new_topic",
        "suggested_key",
        "detected_type",
        "subtopic_resolved_to_existing",
        "subtopic_synonym_confidence",
        "subtopic_is_new",
        "subtopic_suggested_key",
        "subtopic_label",
    }
    v1_template = _AUTOGENERAR_PROMPT_TEMPLATE
    taxonomy = load_subtopic_taxonomy()
    v2_prompt = _build_taxonomy_aware_prompt(
        filename="x.md", body_preview="y", subtopic_taxonomy=taxonomy
    )
    for f in v1_fields:
        assert f in v1_template
        assert f in v2_prompt, f"v2 prompt missing v1-contract field: {f}"
