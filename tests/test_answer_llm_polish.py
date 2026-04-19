"""Contract tests for the LLM polish step in Pipeline D.

The polish stage takes the template-driven answer plus retrieved evidence
and asks an LLM to rewrite the prose in senior-accountant voice. These
tests lock three invariants that MUST hold in every environment:

1. When no adapter resolves (missing config, missing API keys), the
   template answer is returned unchanged and diagnostics explain *why*.
2. When the LLM returns text that strips every legal anchor, the polish
   is REJECTED — template answer wins.
3. When the LLM returns well-formed text that preserves anchors, the
   polished version is surfaced and `llm_runtime` carries the provider
   identity for observability.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.answer_llm_polish import polish_graph_native_answer
from lia_graph.pipeline_d.contracts import GraphEvidenceBundle, GraphEvidenceItem


def _evidence() -> GraphEvidenceBundle:
    return GraphEvidenceBundle(
        primary_articles=(
            GraphEvidenceItem(
                node_kind="ArticleNode",
                node_key="147",
                title="COMPENSACIÓN DE PÉRDIDAS FISCALES DE SOCIEDADES",
                excerpt="Las sociedades podrán compensar las pérdidas fiscales con rentas líquidas ordinarias.",
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


def _template_answer() -> str:
    return (
        "**Ruta sugerida**\n"
        "1. El régimen base del art. 147 ET es que la sociedad compensa la pérdida "
        "fiscal contra la renta líquida ordinaria (art. 147 ET).\n"
        "2. La firmeza sube a 6 años cuando la declaración compensa pérdidas "
        "(arts. 147 y 714 ET).\n"
        "\n**Riesgos y condiciones**\n"
        "- No mezcles compensación de pérdidas con compensación de saldos a favor "
        "(art. 147 ET).\n"
    )


def _request() -> PipelineCRequest:
    return PipelineCRequest(
        message="¿Cuál es el régimen de compensación de pérdidas fiscales?",
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )


@pytest.fixture(autouse=True)
def _enable_polish(monkeypatch):
    """Polish is opt-in via env; every test in this file exercises the polish
    path explicitly, so enable it. This is also the regression guard that
    the env flag is what gates the behavior."""
    monkeypatch.setenv("LIA_LLM_POLISH_ENABLED", "1")


# --- Contract 1: graceful degradation -----------------------------------


def test_polish_returns_template_unchanged_when_no_adapter_resolves() -> None:
    template = _template_answer()
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(None, {"fallback_skipped": [{"provider_id": "x", "reason": "missing_env:X"}]}),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_evidence(),
        )
    assert answer == template
    assert diag["mode"] == "skipped"
    assert diag["skip_reason"] == "no_adapter_available"
    # Diagnostic should carry enough info for operators to debug
    assert "fallback_skipped" in diag


def test_polish_returns_template_unchanged_when_resolver_raises() -> None:
    template = _template_answer()
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        side_effect=RuntimeError("config missing"),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_evidence(),
        )
    assert answer == template
    assert diag["mode"] == "skipped"
    assert diag["skip_reason"].startswith("resolver_error:")


def test_polish_returns_template_unchanged_when_adapter_raises() -> None:
    class _FailingAdapter:
        def generate(self, prompt: str) -> str:
            raise TimeoutError("network down")

    template = _template_answer()
    resolution = {"selected_provider": "deepseek-chat", "model": "deepseek-chat"}
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_FailingAdapter(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_evidence(),
        )
    assert answer == template
    assert diag["mode"] == "failed"
    assert diag["skip_reason"] == "adapter_error:TimeoutError"
    # Provider identity must still surface — operator needs to know who failed
    assert diag["selected_provider"] == "deepseek-chat"


def test_polish_returns_template_when_llm_returns_empty() -> None:
    class _EmptyAdapter:
        def generate(self, prompt: str) -> str:
            return ""

    template = _template_answer()
    resolution = {"selected_provider": "gemini-flash", "model": "gemini-2.0-flash"}
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_EmptyAdapter(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_evidence(),
        )
    assert answer == template
    assert diag["skip_reason"] == "empty_llm_output"


# --- Contract 2: anchor preservation ------------------------------------


def test_polish_rejects_output_that_strips_all_anchors() -> None:
    class _AnchorStrippingAdapter:
        def generate(self, prompt: str) -> str:
            # LLM completely forgot the inline legal references.
            return (
                "**Ruta sugerida**\n"
                "1. La sociedad compensa la pérdida fiscal con la renta líquida.\n"
                "2. La firmeza es más larga cuando hay pérdidas compensadas.\n"
            )

    template = _template_answer()
    resolution = {"selected_provider": "deepseek-chat", "model": "deepseek-chat"}
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_AnchorStrippingAdapter(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_evidence(),
        )
    # Polish must be rejected — template answer wins.
    assert answer == template
    assert diag["mode"] == "rejected"
    assert diag["skip_reason"] == "anchors_stripped"
    assert diag["selected_provider"] == "deepseek-chat"


def test_polish_accepts_output_that_preserves_anchors() -> None:
    class _GoodAdapter:
        def generate(self, prompt: str) -> str:
            # Rewritten prose, anchors intact.
            return (
                "**Ruta sugerida**\n"
                "1. Sociedad → compensa pérdida fiscal contra renta líquida "
                "ordinaria; no es trámite DIAN (art. 147 ET).\n"
                "2. Con compensación de pérdidas la firmeza sube a 6 años "
                "(arts. 147 y 714 ET).\n"
                "\n**Riesgos y condiciones**\n"
                "- Distinguí compensación de pérdidas de compensación de saldos "
                "a favor (art. 147 ET).\n"
            )

    template = _template_answer()
    resolution = {
        "selected_provider": "deepseek-chat",
        "selected_type": "deepseek",
        "selected_transport": "standard",
        "adapter_class": "DeepSeekChatAdapter",
        "model": "deepseek-chat",
        "strategy": "ordered_fallback",
        "resolution_mode": "deterministic",
        "runtime_config_path": "config/llm_runtime.json",
    }
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_GoodAdapter(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_evidence(),
        )
    assert answer != template, "polished text should replace the template"
    assert "(art. 147 ET)" in answer
    assert "(arts. 147 y 714 ET)" in answer
    assert diag["mode"] == "llm"
    assert diag["selected_provider"] == "deepseek-chat"
    assert diag["model"] == "deepseek-chat"


# --- Contract 3a: env flag gates the whole path -------------------------


def test_polish_skipped_when_env_flag_disabled(monkeypatch) -> None:
    """The flag is the single switch that separates deterministic test runs
    from LLM-polished production runs. Turning it off must completely
    short-circuit polish even if an adapter would otherwise resolve."""
    monkeypatch.setenv("LIA_LLM_POLISH_ENABLED", "0")

    class _ShouldNotBeCalledAdapter:
        def generate(self, prompt: str) -> str:
            raise AssertionError("adapter must not be called when flag=0")

    template = _template_answer()
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_ShouldNotBeCalledAdapter(), {"selected_provider": "x"}),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_evidence(),
        )
    assert answer == template
    assert diag["skip_reason"] == "polish_disabled_by_env"


# --- Contract 3b: polish stays disabled when template is empty -----------


def test_polish_skips_when_template_answer_is_empty() -> None:
    answer, diag = polish_graph_native_answer(
        request=_request(),
        template_answer="   ",
        evidence=_evidence(),
    )
    assert answer == "   "
    assert diag["skip_reason"] == "empty_template"
    assert diag["selected_provider"] is None


# --- Contract 4: prompt contains real evidence --------------------------


def test_polish_prompt_includes_primary_article_excerpts() -> None:
    """Regression guard: the prompt the adapter receives MUST include the
    retrieved article text and the user's question, not just the template.
    If this ever drifts, the LLM would be rewriting prose blind to the
    evidence — the whole point of the step is to ground in retrieval."""
    captured: dict[str, str] = {}

    class _CaptureAdapter:
        def generate(self, prompt: str) -> str:
            captured["prompt"] = prompt
            return _template_answer()  # fine — anchors preserved

    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_CaptureAdapter(), {"selected_provider": "x", "model": "x"}),
    ):
        polish_graph_native_answer(
            request=_request(),
            template_answer=_template_answer(),
            evidence=_evidence(),
        )

    prompt = captured["prompt"]
    assert "compensación de pérdidas fiscales" in prompt.lower()  # user's question
    assert "Art. 147" in prompt  # primary article heading
    assert "COMPENSACIÓN DE PÉRDIDAS FISCALES DE SOCIEDADES" in prompt
    assert "senior" in prompt.lower() or "contador" in prompt.lower()
    assert "(art. X ET)" in prompt or "(art." in prompt  # anchor preservation instruction
