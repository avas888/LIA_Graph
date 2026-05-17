"""fix_v21_may §3.2 P2-T1 — polish over-rejection regression on labor.

The v20 closing probe (q01: "¿Qué dice el art. 64 del CST sobre la
terminación sin justa causa?") landed in the cloud-staged
``20260517T013419Z_v20_labor_collision`` run with
``polish_skip_reason=invented_norm_lineage`` despite the polish output
legitimately citing ``Ley 50 de 1990`` and ``Ley 2466 de 2025`` — both
present in the evidence ``related_reforms`` block the polish prompt
rendered, and both surfaced as citations in the response.

Root cause: ``_no_invented_norm_lineage`` only compares
``(template, polished)``. It never inspects the evidence excerpts the
LLM was explicitly invited to draw from, so anything the synthesis
template happened to omit gets flagged as "invented" — even when the
reference is right there in the prompt's EXCERPTS / REFORMAS block.

This file locks the behavior that the validator must accept a
Ley/Decreto/Resolución/Sentencia reference that is present anywhere in
the evidence bundle (titles + excerpts across primary_articles,
connected_articles, related_reforms, support_documents), and continue
to reject references that are absent from BOTH the template and the
evidence.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_llm_polish import (
    _apply_post_hoc_transformers,
    polish_graph_native_answer,
)
from lia_graph.pipeline_d.contracts import GraphEvidenceBundle, GraphEvidenceItem


def _labor_evidence_with_reforms() -> GraphEvidenceBundle:
    """Mirror the v20 q01 evidence shape: CST 64 anchor + Ley 50/1990 +
    Ley 2466/2025 carried in ``related_reforms``."""
    return GraphEvidenceBundle(
        primary_articles=(
            GraphEvidenceItem(
                node_kind="ArticleNode",
                node_key="64",
                title="TERMINACIÓN UNILATERAL DEL CONTRATO DE TRABAJO SIN JUSTA CAUSA",
                excerpt=(
                    "En todo contrato de trabajo va envuelta la condición "
                    "resolutoria por incumplimiento; en caso de terminación "
                    "unilateral sin justa causa el empleador deberá pagar "
                    "una indemnización al trabajador."
                ),
                source_path="laboral/cst_art_64.md",
                score=1.0,
                hop_distance=0,
                why=None,
                relation_path=(),
            ),
        ),
        connected_articles=(),
        related_reforms=(
            GraphEvidenceItem(
                node_kind="LeyNode",
                node_key="ley:50:1990",
                title="Ley 50 de 1990 — Reforma laboral (CST, cesantías)",
                excerpt="Reformó el régimen sustantivo del trabajo.",
                source_path="leyes/ley_50_1990.md",
                score=0.9,
                hop_distance=1,
                why=None,
                relation_path=(),
            ),
            GraphEvidenceItem(
                node_kind="LeyNode",
                node_key="ley:2466:2025",
                title="Ley 2466 de 2025 — Reforma Laboral Integral: Compilación Normativa",
                excerpt="Actualiza la indemnización por despido sin justa causa.",
                source_path="leyes/ley_2466_2025.md",
                score=0.9,
                hop_distance=1,
                why=None,
                relation_path=(),
            ),
        ),
        support_documents=(),
        citations=(),
        diagnostics={},
    )


def _labor_template() -> str:
    """Thin first-bubble template — mirrors v20 q01's 124-char shape:
    question echo + minimal anclaje, NO Ley reference."""
    return (
        "**Respuestas directas**\n"
        "- **¿Qué dice el artículo 64 del CST sobre la terminación sin "
        "justa causa del contrato de trabajo?**\n"
        "\n"
        "**Anclaje legal**\n"
        "- Art. 64 CST — terminación unilateral sin justa causa.\n"
    )


def _request() -> PipelineCRequest:
    return PipelineCRequest(
        message=(
            "¿Qué dice el artículo 64 del CST sobre la terminación sin "
            "justa causa del contrato de trabajo?"
        ),
        topic="laboral",
        requested_topic="laboral",
    )


@pytest.fixture(autouse=True)
def _enable_polish(monkeypatch):
    monkeypatch.setenv("LIA_LLM_POLISH_ENABLED", "1")


def test_polish_accepts_ley_present_in_evidence_related_reforms() -> None:
    """v20-q01 regression: polish must NOT reject when the cited Ley is
    in ``evidence.related_reforms`` (the prompt's REFORMAS block).

    Pre-fix: validator compares only ``(template, polished)`` and flags
    every Ley/Decreto/Sentencia ref absent from the template as
    "invented." For a labor question with a thin template (mostly the
    question echo + the CST anchor) the polish step legitimately reaches
    into the evidence for the reform lineage — and gets killed for it.

    Post-fix: refs found in any evidence field (related_reforms titles
    are the load-bearing case) count as "grounded" — only references
    present nowhere in template OR evidence trigger rejection.
    """

    class _LaborPolishAdapter:
        def generate(self, prompt: str) -> str:
            return (
                "**Respuestas directas**\n"
                "- **¿Qué dice el artículo 64 del CST sobre la terminación "
                "sin justa causa del contrato de trabajo?**\n"
                "  - El art. 64 CST consagra la indemnización por terminación "
                "unilateral sin justa causa, modificado por **Ley 50 de 1990** "
                "y actualizado por **Ley 2466 de 2025**.\n"
                "\n"
                "**Anclaje legal**\n"
                "- Art. 64 CST — terminación unilateral sin justa causa.\n"
            )

    template = _labor_template()
    resolution = {"selected_provider": "gemini-flash", "model": "gemini-2.5-flash"}
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_LaborPolishAdapter(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_labor_evidence_with_reforms(),
        )
    assert diag["mode"] == "llm", (
        f"polish must accept Ley refs present in evidence.related_reforms, "
        f"got diag={diag}"
    )
    assert diag["skip_reason"] is None
    assert "Ley 50 de 1990" in answer
    assert "Ley 2466 de 2025" in answer


def test_polish_still_rejects_ley_absent_from_template_and_evidence() -> None:
    """The widening must not blunt the existing guard: a Ley reference
    that is in NEITHER the template NOR any evidence field must still
    fire ``invented_norm_lineage``. Otherwise we'd regress the q06 fix
    the validator was built for."""

    class _LeyHallucinatingAdapter:
        def generate(self, prompt: str) -> str:
            return (
                "**Respuestas directas**\n"
                "- **¿Qué dice el artículo 64 del CST sobre la terminación "
                "sin justa causa del contrato de trabajo?**\n"
                "  - El régimen fue ampliado por **Ley 1819 de 2016**, "
                "no citada en la evidencia.\n"
                "\n"
                "**Anclaje legal**\n"
                "- Art. 64 CST — terminación unilateral sin justa causa.\n"
            )

    template = _labor_template()
    resolution = {"selected_provider": "gemini-flash", "model": "gemini-2.5-flash"}
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_LeyHallucinatingAdapter(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_labor_evidence_with_reforms(),
        )
    assert diag["mode"] == "rejected", (
        f"polish must still reject a Ley ref absent from template AND "
        f"evidence, got diag={diag}"
    )
    assert diag["skip_reason"] == "invented_norm_lineage"
    assert answer == _apply_post_hoc_transformers(template)


def test_polish_accepts_ley_present_in_primary_article_excerpt() -> None:
    """A Ley reference quoted inside an article excerpt (primary or
    connected) counts as grounded — the LLM saw it in the EXCERPTS block."""

    evidence = GraphEvidenceBundle(
        primary_articles=(
            GraphEvidenceItem(
                node_kind="ArticleNode",
                node_key="64",
                title="TERMINACIÓN UNILATERAL DEL CONTRATO DE TRABAJO SIN JUSTA CAUSA",
                excerpt=(
                    "Modificado por el art. 28 de la Ley 789 de 2002. "
                    "En todo contrato de trabajo va envuelta la condición "
                    "resolutoria por incumplimiento."
                ),
                source_path="laboral/cst_art_64.md",
                score=1.0,
                hop_distance=0,
                why=None,
                relation_path=(),
            ),
        ),
        connected_articles=(),
        related_reforms=(),
        support_documents=(),
        citations=(),
        diagnostics={},
    )

    class _PolishCitesArticleLineage:
        def generate(self, prompt: str) -> str:
            return (
                "**Respuestas directas**\n"
                "- **¿Qué dice el art. 64 del CST?**\n"
                "  - El art. 64 CST fue modificado por **Ley 789 de 2002** "
                "para ajustar la fórmula de indemnización.\n"
                "\n"
                "**Anclaje legal**\n"
                "- Art. 64 CST.\n"
            )

    template = _labor_template()
    resolution = {"selected_provider": "gemini-flash", "model": "gemini-2.5-flash"}
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_PolishCitesArticleLineage(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=evidence,
        )
    assert diag["mode"] == "llm", (
        f"polish must accept Ley refs present in article excerpts, "
        f"got diag={diag}"
    )
    assert "Ley 789 de 2002" in answer
