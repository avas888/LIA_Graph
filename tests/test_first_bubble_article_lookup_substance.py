"""fix_v21_may §3.2 P2-T5 — article-lookup mode should surface case bullets.

After P2-T1 + P2-T2 landed (polish guards consult evidence; détector widens
to article-lookup form), v21's q01 probe surfaced a new symptom: the answer
is now off-topic-free but reads as a thin description ("Art. 64 CST regula
las condiciones y consecuencias") with no day-count formula or SMMLV
threshold — because ``compose_first_bubble_answer``'s fix_v4-phase-5
bail-out fires whenever ``substantive_sections < 2`` (counting RAW
sections, not their total content). For an article-lookup with a rich
single-section Recomendaciones Prácticas (case-bullet SPEC populated:
1900+ chars of substantive guidance) and empty Riesgos/Soportes, the
bail-out wrongly discards the rich section and returns the bare question
echo.

Root cause: the fix_v4 trigger condition (``len(substantive_sections) <
2``) was designed for queries where synthesis was genuinely thin (e.g.
regimen_sancionatorio_extemporaneidad_P2 had ~239 chars of total
assembled content). Now that the détector widen makes the labor case
fire on article-lookup form, synthesis IS substantive — but it lands in
a single section, which the bail-out interprets as "too thin".

This file locks: when at least one route/risk/support section reaches a
real-content threshold, the bail-out must NOT fire — synthesis output
is kept and handed to polish. The genuinely-thin regression guard
(empty sections) still fires the bail-out unchanged.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_first_bubble import compose_first_bubble_answer
from lia_graph.pipeline_d.answer_synthesis_sections import build_recommendations
from lia_graph.pipeline_d.answer_shared import (
    filter_published_lines,
    normalize_text,
    should_surface_change_context,
    take_new_lines,
)
from lia_graph.pipeline_d.contracts import GraphEvidenceItem


def _labor_q01_primary() -> tuple[GraphEvidenceItem, ...]:
    return (
        GraphEvidenceItem(
            node_kind="ArticleNode",
            node_key="64",
            title="TERMINACION UNILATERAL DEL CONTRATO DE TRABAJO SIN JUSTA CAUSA",
            excerpt="",
            source_path="",
            score=1.0,
            hop_distance=0,
            why=None,
            relation_path=(),
        ),
        GraphEvidenceItem(
            node_kind="ArticleNode",
            node_key="62",
            title="Terminación por justa causa",
            excerpt="",
            source_path="",
            score=0.9,
            hop_distance=0,
            why=None,
            relation_path=(),
        ),
        GraphEvidenceItem(
            node_kind="ArticleNode",
            node_key="65",
            title="Indemnización moratoria",
            excerpt="",
            source_path="",
            score=0.9,
            hop_distance=0,
            why=None,
            relation_path=(),
        ),
    )


def _labor_q01_recommendations() -> tuple[str, ...]:
    """Reproduce what build_recommendations returns for q01 — the
    liquidación-terminación case SPEC's 7 bullets, after the standard
    filter_published_lines + take_new_lines pipeline that
    build_graph_native_answer_parts applies."""
    msg = (
        "¿Qué dice el artículo 64 del CST sobre la terminación sin "
        "justa causa del contrato de trabajo?"
    )
    req = PipelineCRequest(message=msg, topic="laboral", requested_topic="laboral")
    allow_change = should_surface_change_context(
        normalized_message=normalize_text(msg),
        temporal_context={},
        planner_query_mode="article_lookup",
        requested_period_label="",
    )
    raw = build_recommendations(
        request=req,
        temporal_context={},
        primary_articles=_labor_q01_primary(),
        connected_articles=(),
        practica_chunks=(),
    )
    filtered = filter_published_lines(raw, allow_change_lines=allow_change)
    seen: set[str] = set()
    return take_new_lines(filtered, seen)


def test_article_lookup_with_rich_single_section_does_not_bail_out() -> None:
    """v21-q01 regression: when Recomendaciones Prácticas carries
    substantive case-bullet content (~1900 chars) but Riesgos / Soportes
    are empty, the assembled answer must KEEP the Recomendaciones section
    — not replace it with the bare question-echo bail-out."""

    msg = (
        "¿Qué dice el artículo 64 del CST sobre la terminación sin "
        "justa causa del contrato de trabajo?"
    )
    req = PipelineCRequest(message=msg, topic="laboral", requested_topic="laboral")

    recommendations = _labor_q01_recommendations()
    assert len(recommendations) >= 5, (
        "precondition: build_recommendations must populate 5+ case bullets "
        "for the labor q01 article-lookup form (P2-T2 détector widen)"
    )

    answer = compose_first_bubble_answer(
        request=req,
        answer_mode="graph_native",
        planner_query_mode="article_lookup",
        temporal_context={},
        primary_articles=_labor_q01_primary(),
        connected_articles=(),
        reforms=(),
        support_documents=(),
        article_insights={},
        support_insights={},
        recommendations=recommendations,
        procedure=(),
        paperwork=(),
        precautions=(),
        direct_answers=(),
    )

    assert "Recomendaciones Prácticas" in answer, (
        f"answer must keep Recomendaciones Prácticas section, got "
        f"{len(answer)} chars:\n{answer[:400]}"
    )
    assert "30 días" in answer or "20 días" in answer, (
        f"answer must surface the indemnización formula tokens, got: "
        f"{answer[:600]}"
    )
    assert len(answer) > 500, (
        f"answer must be substantive (>500 chars), got {len(answer)} chars "
        f"— bail-out fired and discarded the rich Recomendaciones section"
    )


def test_thin_synthesis_still_triggers_question_reformulation_bailout() -> None:
    """Regression guard for fix_v4 phase 5: when synthesis is genuinely
    thin (empty Recomendaciones + Riesgos + Soportes), the bail-out
    must still fire so polish can expand from the question-reformulation
    shape. SME panel +1/36 (35→36) was driven by this fallback."""

    msg = "¿Cuál es el régimen sancionatorio aplicable?"
    req = PipelineCRequest(
        message=msg, topic="declaracion_renta", requested_topic="declaracion_renta"
    )

    answer = compose_first_bubble_answer(
        request=req,
        answer_mode="graph_native",
        planner_query_mode="article_lookup",
        temporal_context={},
        primary_articles=_labor_q01_primary(),  # 3 primary articles
        connected_articles=(),
        reforms=(),
        support_documents=(),
        article_insights={},
        support_insights={},
        recommendations=(),  # empty
        procedure=(),  # empty
        paperwork=(),
        precautions=(),
        direct_answers=(),
    )

    assert answer.startswith("**Respuestas directas**"), (
        f"thin-synthesis case must bail out to question-reformulation "
        f"shape (fix_v4 phase 5); got: {answer[:200]}"
    )
    assert "¿Cuál es el régimen sancionatorio aplicable?" in answer
    assert "Recomendaciones Prácticas" not in answer
