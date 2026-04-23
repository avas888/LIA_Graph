"""Tests for tag_report_generator (ingestionfix_v2 §4 Phase 7a)."""

from __future__ import annotations

from typing import Any

import pytest

from lia_graph.tag_report_generator import generate_tag_report


def _doc(markdown: str = "", **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "doc_id": "retencion_en_la_fuente_ret_n03",
        "relative_path": "retencion_en_la_fuente/RET-N03.md",
        "first_heading": "Decreto 572 de 2025 — retenciones",
        "topic": "retencion_en_la_fuente",
        "tema": "retencion_en_la_fuente",
        "subtema": None,
        "subtopic_confidence": 0.42,
        "markdown": markdown,
    }
    base.update(overrides)
    return base


def test_report_includes_title_and_first_500_words():
    long_body = ("palabra " * 750).strip()
    report = generate_tag_report(
        _doc(markdown=long_body),
        report_id="rpt_test1",
    )
    assert "Decreto 572 de 2025 — retenciones" in report.markdown
    assert "## Extracto" in report.markdown
    # 750 words → truncated to 500 + ellipsis
    assert report.first_500_words.endswith("…")
    word_count = len(report.first_500_words.replace("…", "").split())
    assert word_count <= 500


def test_report_lists_top3_classifier_alternatives():
    alternatives = [
        {"topic_key": "iva", "subtopic_key": "iva_declaracion", "confidence": 0.81,
         "rationale": "prominent IVA references"},
        {"topic_key": "retencion_en_la_fuente", "subtopic_key": "retencion_decreto_572",
         "confidence": 0.76},
        {"topic_key": "procedimiento_tributario", "subtopic_key": "recursos",
         "confidence": 0.31},
        {"topic_key": "ignored", "subtopic_key": "ignored", "confidence": 0.01},  # 4th dropped
    ]
    report = generate_tag_report(
        _doc(markdown="texto"),
        report_id="rpt_test2",
        classifier_alternatives=alternatives,
    )
    assert "Alternativas del clasificador" in report.markdown
    # Top-3 shown; 4th filtered
    assert "iva" in report.markdown
    assert "retencion_decreto_572" in report.markdown
    assert "procedimiento_tributario" in report.markdown
    assert "ignored" not in report.markdown


def test_report_lists_neighbors_per_candidate_tag():
    neighbors = {
        "retencion_en_la_fuente": [
            {"first_heading": "RET-N01 — agentes de retención", "score": 0.91},
            {"first_heading": "RET-N02 — bases y tarifas", "score": 0.88},
        ],
        "iva": [
            {"first_heading": "IVA-N01 — régimen general", "score": 0.73},
        ],
    }
    report = generate_tag_report(
        _doc(markdown="texto"),
        report_id="rpt_test3",
        similar_docs_by_tag=neighbors,
    )
    assert "Vecindario semántico" in report.markdown
    assert "RET-N01" in report.markdown
    assert "IVA-N01" in report.markdown
    assert "retencion_en_la_fuente" in report.markdown
    assert "iva" in report.markdown


def test_report_extracts_legal_references():
    md = (
        "El Decreto 572 de 2025 modifica la retención. Ver Ley 2277 de 2022 y "
        "Resolución 00091 de 2025. También Ley 2277 de 2022 (duplicada debe "
        "deduplicarse)."
    )
    report = generate_tag_report(_doc(markdown=md), report_id="rpt_legal")
    refs = report.legal_references
    assert "Decreto 572 de 2025" in refs
    assert "Ley 2277 de 2022" in refs
    assert "Resolución 00091 de 2025" in refs
    # Deduplication check
    assert list(refs).count("Ley 2277 de 2022") == 1


def test_report_without_llm_adapter_returns_deterministic_brief():
    report = generate_tag_report(
        _doc(markdown="cuerpo mínimo"),
        report_id="rpt_no_llm",
        llm_adapter=None,
    )
    assert report.llm_polished is False
    assert report.skip_reason == "no_adapter_available"
    assert "## Documento" in report.markdown


def test_report_llm_polish_preserves_all_sections():
    class _FakeAdapter:
        def generate(self, prompt: str) -> str:
            # Return a valid polished Markdown with all five required H2 sections.
            return (
                "# Brief de revisión de tags\n\n"
                "## Documento\nPolished prose.\n\n"
                "## Extracto\nContenido.\n\n"
                "## Alternativas del clasificador\nN/A.\n\n"
                "## Vecindario semántico\nN/A.\n\n"
                "## Referencias legales detectadas\nN/A.\n"
            )

    report = generate_tag_report(
        _doc(markdown="texto"),
        report_id="rpt_polished",
        llm_adapter=_FakeAdapter(),
    )
    assert report.llm_polished is True
    assert report.skip_reason is None


def test_report_rejects_llm_output_that_strips_required_heading():
    class _BadAdapter:
        def generate(self, prompt: str) -> str:
            # Drops the "Vecindario semántico" heading.
            return (
                "# Brief\n"
                "## Documento\ncontent\n"
                "## Extracto\ncontent\n"
                "## Alternativas del clasificador\ncontent\n"
                "## Referencias legales detectadas\ncontent\n"
            )

    report = generate_tag_report(
        _doc(markdown="texto"),
        report_id="rpt_guard",
        llm_adapter=_BadAdapter(),
    )
    assert report.llm_polished is False
    assert report.skip_reason == "heading_stripped_by_llm"


def test_report_survives_empty_markdown():
    report = generate_tag_report(
        _doc(markdown=""),
        report_id="rpt_empty",
    )
    assert report.first_500_words == ""
    assert report.legal_references == ()
    assert "## Extracto" in report.markdown
