"""Locks in v19 Fase 3-2 fix to the gap-analysis exclusion filter.

Before 2026-05-15 the content classifier at
`ingest_classifiers._classify_ingestion_decision` excluded any document
containing the bare token `"gap"`. That false-positived the v19 CST
consolidado delivery, whose §6 "Notas de cobertura" required by the
expert brief contains the line `"Sin gaps. Toda la cobertura proviene
de Secretaría del Senado."` — innocuous coverage report, not gap
analysis.

The filter now requires multi-word phrases ("audit gap", "gap analysis",
"analisis gap"). Filename-stem matches on `*analisis_gap*` /
`*gap_analysis*` continue to catch obvious gap-analysis files.
"""

from __future__ import annotations

from pathlib import Path

from lia_graph.ingest_classifiers import _classify_ingestion_decision


def _classify(*, name: str, body: str, relative_path: str | None = None):
    rel = relative_path or name
    return _classify_ingestion_decision(
        path=Path(rel),
        relative_path=rel,
        markdown=body,
        extension=".md",
        text_extractable=True,
        corpus_root=Path("."),
    )


def test_cst_consolidado_with_sin_gaps_is_not_excluded():
    """Regression: the CST consolidado delivery 2026-05-15 contains
    `"Sin gaps."` in its coverage report. Must NOT classify as
    gap-analysis working material."""
    body = (
        "# Código Sustantivo del Trabajo — texto consolidado\n"
        "Fuente: Secretaría del Senado\n"
        "Total de artículos: 504\n"
        "\n"
        "### ARTÍCULO 64. TERMINACION UNILATERAL.\n"
        "URL: http://www.secretariasenado.gov.co/.../pr001.html\n"
        "Texto del artículo 64.\n"
        "\n"
        "## Notas de cobertura\n"
        "Sin gaps. Toda la cobertura proviene de Secretaría del Senado.\n"
    )
    decision, reason, _, archetype = _classify(
        name="Codigo_Sustantivo_Trabajo.md",
        body=body,
        relative_path="knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md",
    )
    assert archetype != "gap_analysis", (
        f"CST consolidado was excluded as gap_analysis. reason={reason!r}"
    )


def test_legitimate_gap_analysis_doc_still_excluded_by_filename():
    """Positive control: filename-based gap-analysis exclusion stays intact."""
    decision, _, _, archetype = _classify(
        name="gap_analysis_renta_2026.md",
        body="Comparativa de cobertura del corpus vs leyes vigentes.",
    )
    assert archetype == "gap_analysis"
    assert decision == "exclude_internal"


def test_legitimate_gap_analysis_phrase_still_excluded():
    """Positive control: multi-word `gap analysis` in content still triggers."""
    _, _, _, archetype = _classify(
        name="some_doc.md",
        body=(
            "## Resumen\n"
            "This document presents a gap analysis of the current "
            "normative coverage versus the latest reform.\n"
        ),
    )
    assert archetype == "gap_analysis"


def test_legitimate_audit_gap_phrase_still_excluded():
    """Positive control: `audit gap` phrase still triggers."""
    _, _, _, archetype = _classify(
        name="audit_report.md",
        body="The audit gap we identified covers articles 60 through 75.",
    )
    assert archetype == "gap_analysis"


def test_legitimate_analisis_gap_phrase_still_excluded():
    """Positive control: Spanish `análisis gap` (normalized to `analisis gap`)."""
    _, _, _, archetype = _classify(
        name="reporte.md",
        body="Hicimos el analisis gap sobre la cobertura del corpus laboral.",
    )
    assert archetype == "gap_analysis"


def test_doc_with_bare_gap_word_in_other_context_not_excluded():
    """A canonical statute that uses 'gap' as a Spanish/English regular word
    (e.g. mentioning 'closing the gap') should not be flagged. Pre-fix
    behavior would have excluded it."""
    body = (
        "# Ley sobre infraestructura\n"
        "Artículo 1. Objetivo: cerrar el gap entre regiones rurales y urbanas.\n"
    )
    _, _, _, archetype = _classify(name="Ley-123-2024.md", body=body)
    assert archetype != "gap_analysis"
