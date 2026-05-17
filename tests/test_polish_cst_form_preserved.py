"""fix_v22_may §9 D6 — labor (CST) anchor form preserved by polish.

v21 closing probe (q01: "¿Qué dice el art. 64 del CST sobre la
terminación sin justa causa?") returned substantive content but
mislabeled labor articles as ``(art. 64 ET)`` — the Estatuto Tributario
(tax code), not the Código Sustantivo del Trabajo (labor code). Root
cause: ``answer_llm_polish.py`` POLISH_RULES enforced ``(art. X ET)`` as
the *only* canonical inline form, so the LLM rewrote CST citations to
match.

v22 widens the prompt rules to accept both ``(art. N ET)`` and
``(art. N CST)`` as parallel forms, with the explicit instruction:
preserve the suffix as it appears in the BORRADOR — never rewrite ET↔CST.
This file locks:

  1. The prompt text contains the new "preserve code suffix" rule.
  2. When the LLM keeps a CST anchor verbatim, polish accepts it
     (no rejection, no skip).
  3. The tax-side regression guard: an ET anchor on a tax question
     stays ET (no accidental CST-ification).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_llm_polish import (
    POLISH_RULES,
    polish_graph_native_answer,
)
from lia_graph.pipeline_d.contracts import GraphEvidenceBundle, GraphEvidenceItem


def _rule_by_id(rule_id: str):
    for rule in POLISH_RULES:
        if rule.id == rule_id:
            return rule
    raise KeyError(rule_id)


def test_anchor_preserve_rule_mentions_cst_explicitly() -> None:
    """The prompt-level rule must name CST as a parallel canonical form
    and forbid ET↔CST rewrites. Pre-v22 the rule said only ``(art. X
    ET)``, which is what the LLM defaulted to even for labor articles."""
    rule = _rule_by_id("anchor_preserve")
    prompt = rule.prompt_text
    assert "CST" in prompt, "anchor_preserve rule must mention CST"
    assert "Estatuto Tributario" in prompt, (
        "anchor_preserve must keep ET as a parallel form"
    )
    assert "Código Sustantivo del Trabajo" in prompt, (
        "anchor_preserve must name the CST long form so the LLM knows what code it is"
    )
    # Locked guardrail phrasing — the load-bearing instruction.
    assert (
        "NUNCA reescribás `(art. N CST)` como `(art. N ET)` ni `(art. N ET)`"
        " como `(art. N CST)`"
    ) in prompt


def test_numeric_format_bold_excludes_cst_examples() -> None:
    """EXCEPCIÓN ESTRICTA must list CST anchors among the preserved
    forms so the bold-number transformer doesn't grab them."""
    rule = _rule_by_id("numeric_format_bold")
    prompt = rule.prompt_text
    assert "(art. 64 CST)" in prompt
    assert "(arts. 186 a 197 CST)" in prompt


def test_anclaje_legal_rule_allows_cst_anchors() -> None:
    """Anclaje Legal section must permit ``Art. N CST — ...`` parallel
    to ``Art. N ET — ...`` — pre-v22 the rule only listed ET."""
    rule = _rule_by_id("anclaje_legal_explanatory_lines")
    prompt = rule.prompt_text
    assert "CST" in prompt
    assert "Código Sustantivo del Trabajo" in prompt
    assert "(art. 64 CST)" in prompt


def _labor_evidence() -> GraphEvidenceBundle:
    return GraphEvidenceBundle(
        primary_articles=(
            GraphEvidenceItem(
                node_kind="ArticleNode",
                node_key="64",
                title="TERMINACIÓN UNILATERAL DEL CONTRATO DE TRABAJO SIN JUSTA CAUSA",
                excerpt=(
                    "En caso de terminación unilateral sin justa causa el "
                    "empleador deberá pagar una indemnización al trabajador."
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


def _labor_template_cst() -> str:
    return (
        "**Respuestas directas**\n"
        "- **¿Qué dice el artículo 64 del CST sobre la terminación sin "
        "justa causa?**\n"
        "  - La indemnización se regula en el (art. 64 CST).\n"
        "\n"
        "**Anclaje legal**\n"
        "- Art. 64 CST — terminación unilateral sin justa causa.\n"
    )


def _labor_request() -> PipelineCRequest:
    return PipelineCRequest(
        message="¿Qué dice el artículo 64 del CST sobre la terminación sin justa causa?",
        topic="laboral",
        requested_topic="laboral",
    )


@pytest.fixture(autouse=True)
def _enable_polish(monkeypatch):
    monkeypatch.setenv("LIA_LLM_POLISH_ENABLED", "1")


def test_polish_accepts_cst_anchor_preserved_by_llm() -> None:
    """When the LLM returns a CST anchor verbatim from the BORRADOR,
    polish must NOT reject it. The validator regex is already
    code-agnostic; the prompt widening is what stops the LLM from
    rewriting to ET in the first place."""

    class _CstPreservingAdapter:
        def generate(self, prompt: str) -> str:
            return (
                "**Respuestas directas**\n"
                "- **¿Qué dice el artículo 64 del CST sobre la terminación "
                "sin justa causa?**\n"
                "  - La indemnización por despido sin justa causa se regula "
                "en el (art. 64 CST) y aplica al contrato de trabajo.\n"
                "\n"
                "**Anclaje legal**\n"
                "- Art. 64 CST — terminación unilateral sin justa causa.\n"
            )

    resolution = {"selected_provider": "gemini-flash", "model": "gemini-2.5-flash"}
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_CstPreservingAdapter(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_labor_request(),
            template_answer=_labor_template_cst(),
            evidence=_labor_evidence(),
        )
    assert diag["mode"] == "llm", f"polish must accept CST anchor, got diag={diag}"
    assert diag["skip_reason"] is None
    assert "(art. 64 CST)" in answer, "CST suffix must survive polish"
    assert "(art. 64 ET)" not in answer, "polish must not mislabel CST as ET"


def _tax_evidence() -> GraphEvidenceBundle:
    return GraphEvidenceBundle(
        primary_articles=(
            GraphEvidenceItem(
                node_kind="ArticleNode",
                node_key="147",
                title="COMPENSACIÓN DE PÉRDIDAS FISCALES",
                excerpt=(
                    "Las sociedades podrán compensar las pérdidas fiscales "
                    "con las rentas líquidas ordinarias que obtuvieren "
                    "dentro de los doce (12) períodos gravables siguientes."
                ),
                source_path="renta/et_art_147.md",
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


def _tax_template() -> str:
    return (
        "**Respuestas directas**\n"
        "- **¿Cuál es el régimen de compensación de pérdidas fiscales?**\n"
        "  - Las pérdidas se compensan en los términos del (art. 147 ET).\n"
        "\n"
        "**Anclaje legal**\n"
        "- Art. 147 ET — compensación de pérdidas fiscales.\n"
    )


def _tax_request() -> PipelineCRequest:
    return PipelineCRequest(
        message="¿Cuál es el régimen de compensación de pérdidas fiscales del artículo 147 ET?",
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )


def test_polish_keeps_et_anchor_on_tax_question_regression_guard() -> None:
    """Tax-side regression guard: the v22 prompt widening must NOT cause
    ET anchors on tax questions to mutate into CST. Same evidence + same
    BORRADOR → ET stays ET."""

    class _EtPreservingAdapter:
        def generate(self, prompt: str) -> str:
            return (
                "**Respuestas directas**\n"
                "- **¿Cuál es el régimen de compensación de pérdidas fiscales?**\n"
                "  - Las pérdidas fiscales se compensan dentro de los **12** "
                "períodos gravables siguientes, según el (art. 147 ET).\n"
                "\n"
                "**Anclaje legal**\n"
                "- Art. 147 ET — compensación de pérdidas fiscales.\n"
            )

    resolution = {"selected_provider": "gemini-flash", "model": "gemini-2.5-flash"}
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_EtPreservingAdapter(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_tax_request(),
            template_answer=_tax_template(),
            evidence=_tax_evidence(),
        )
    assert diag["mode"] == "llm"
    assert diag["skip_reason"] is None
    assert "(art. 147 ET)" in answer, "ET suffix must survive polish (regression guard)"
    assert "(art. 147 CST)" not in answer, "tax question must NOT get CST suffix"
