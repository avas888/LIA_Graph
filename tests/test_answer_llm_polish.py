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
from lia_graph.pipeline_d.answer_llm_polish import (
    _apply_post_hoc_transformers,
    _no_invented_uvt_ranges,
    _uvt_validator_mode,
    polish_graph_native_answer,
)
from lia_graph.pipeline_d.contracts import GraphEvidenceBundle, GraphEvidenceItem


def _expected_unpolished(template: str) -> str:
    """Template after post-hoc transformers — what the polish stage returns
    when the LLM never ran. Numeric bolding fires deterministically."""
    return _apply_post_hoc_transformers(template)


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
    assert answer == _expected_unpolished(template)
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
    assert answer == _expected_unpolished(template)
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
    assert answer == _expected_unpolished(template)
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
    assert answer == _expected_unpolished(template)
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
    assert answer == _expected_unpolished(template)
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
    assert answer == _expected_unpolished(template)
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


# --- Contract 2b: no invented norm lineage / periods ---------------------


def test_polish_rejects_invented_norm_lineage() -> None:
    """Polish must not introduce Ley/Decreto/Sentencia references that
    weren't in the template. Regression guard for the Q6 hallucination
    pattern: the engine said "Ley 1819 de 2016 y Ley 2010 de 2019
    modificaron el (art. 689-3 ET)" — both leyes invented from the
    LLM's memory, neither in the template.
    """

    class _LineageInventingAdapter:
        def generate(self, prompt: str) -> str:
            # Anchors preserved, but introduces Ley 1819 / Ley 2010 which
            # aren't in the template — the validator must reject.
            return (
                "**Ruta sugerida**\n"
                "1. La Ley **1819** de 2016 y la Ley **2010** de 2019 "
                "modificaron el (art. 147 ET), estableciendo el régimen "
                "de compensación de pérdidas fiscales.\n"
                "2. La firmeza sube a 6 años (arts. 147 y 714 ET).\n"
                "\n**Riesgos y condiciones**\n"
                "- No mezcles compensación de pérdidas con saldos a favor "
                "(art. 147 ET).\n"
            )

    template = _template_answer()
    resolution = {"selected_provider": "gemini-flash", "model": "gemini-2.5-flash"}
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_LineageInventingAdapter(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_evidence(),
        )
    assert answer == _expected_unpolished(template)
    assert diag["mode"] == "rejected"
    assert diag["skip_reason"] == "invented_norm_lineage"


def test_polish_accepts_norm_lineage_already_in_template() -> None:
    """The validator must NOT reject polish that just rephrases a ley
    reference the template already carried. Otherwise polish becomes
    useless for any topic that mentions reform history."""

    template = (
        "**Ruta sugerida**\n"
        "1. Antes de Ley 1819 de 2016 la compensación de pérdidas era "
        "8 años; tras Ley 1819 de 2016 son 12 años (art. 147 ET).\n"
    )

    class _RephraseAdapter:
        def generate(self, prompt: str) -> str:
            return (
                "**Ruta sugerida**\n"
                "1. La Ley 1819 de 2016 cambió el plazo de compensación "
                "de 8 a 12 años (art. 147 ET).\n"
            )

    resolution = {"selected_provider": "gemini-flash", "model": "gemini-2.5-flash"}
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_RephraseAdapter(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_evidence(),
        )
    assert diag["mode"] == "llm", f"expected accept, got: {diag}"
    assert "Ley 1819 de 2016" in answer


def test_polish_rejects_invented_periods() -> None:
    """Polish must not introduce 4-digit years that weren't in the
    template. Regression guard for the Q4 hallucination pattern: the
    engine said the beneficio de auditoría applies to "AG 2024, 2025,
    2026" when the real period (per Art. 689-3) is 2022 and 2023.
    The template never carried 2024/2025/2026; the polish step
    confabulated them from training memory.
    """

    template = (
        "**Respuestas directas**\n"
        "*   El beneficio de auditoría aplica a los contribuyentes "
        "del impuesto sobre la renta que incrementen su impuesto neto "
        "(art. 147 ET).\n"
    )

    class _PeriodInventingAdapter:
        def generate(self, prompt: str) -> str:
            return (
                "**Respuestas directas**\n"
                "*   Para los años gravables **2024**, **2025** y **2026**, "
                "el beneficio aplica si el contribuyente incrementa su "
                "impuesto neto (art. 147 ET).\n"
            )

    resolution = {"selected_provider": "gemini-flash", "model": "gemini-2.5-flash"}
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_PeriodInventingAdapter(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_evidence(),
        )
    assert answer == _expected_unpolished(template)
    assert diag["mode"] == "rejected"
    assert diag["skip_reason"] == "invented_periods"


def test_polish_accepts_periods_already_in_template() -> None:
    """A polish that just rephrases existing year mentions must pass."""

    template = (
        "**Respuestas directas**\n"
        "*   Para 2022 y 2023, el beneficio de auditoría redujo la firmeza "
        "(art. 147 ET).\n"
    )

    class _RephraseYearsAdapter:
        def generate(self, prompt: str) -> str:
            return (
                "**Respuestas directas**\n"
                "*   En los años gravables **2022** y **2023** la firmeza "
                "se redujo bajo el beneficio (art. 147 ET).\n"
            )

    resolution = {"selected_provider": "gemini-flash", "model": "gemini-2.5-flash"}
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_RephraseYearsAdapter(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_evidence(),
        )
    assert diag["mode"] == "llm", f"expected accept, got: {diag}"
    assert "2022" in answer and "2023" in answer


# --- Contract 4: prompt contains real evidence --------------------------


# ---------------------------------------------------------------------------
# fix_v14_may §5 + §16 + §17 (A3) — DIRECTIVA NUMÉRICA, REVERTED default OFF
#
# A3 was REVERTED 2026-05-13 per fix_v14_may §17 after a 42-turn judge
# panel found it introduces invented UVT/% values (one HARD hallucination
# on pr_rst_anticipo_bimestral). Default `LIA_POLISH_NUMERIC_DIRECTIVE=off`.
# Tests below force `=on` to exercise the helper for future A/B work
# behind the kill switch. The default-off path is covered by
# `test_a3_numeric_directive_off_by_default`.
# ---------------------------------------------------------------------------


@pytest.fixture
def numeric_directive_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_POLISH_NUMERIC_DIRECTIVE", "on")


def _capture_prompt(request: PipelineCRequest) -> str:
    captured: dict[str, str] = {}

    class _CaptureAdapter:
        def generate(self, prompt: str) -> str:
            captured["prompt"] = prompt
            return _template_answer()

    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_CaptureAdapter(), {"selected_provider": "x", "model": "x"}),
    ):
        polish_graph_native_answer(
            request=request,
            template_answer=_template_answer(),
            evidence=_evidence(),
        )
    return captured["prompt"]


def test_a3_numeric_directive_off_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """fix_v14_may §17 REVERT — when `LIA_POLISH_NUMERIC_DIRECTIVE` is
    unset, the directive must NOT be injected even on a question with
    a clear numeric cue. This is the shipped default after the
    2026-05-13 judge found A3 introduced an invented UVT tarifa."""
    monkeypatch.delenv("LIA_POLISH_NUMERIC_DIRECTIVE", raising=False)
    req = PipelineCRequest(
        message="Mi cliente PYME recibió $35 millones de dividendos; Art. 242 ET.",
        topic="dividendos_y_distribucion_utilidades",
        requested_topic="dividendos_y_distribucion_utilidades",
    )
    prompt = _capture_prompt(req)
    assert "DIRECTIVA NUMÉRICA" not in prompt


def test_a3_numeric_directive_fires_on_money_figure(numeric_directive_on: None) -> None:
    req = PipelineCRequest(
        message="Mi cliente PYME recibió $35 millones de dividendos en 2024; ¿cuánto retiene?",
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )
    prompt = _capture_prompt(req)
    assert "DIRECTIVA NUMÉRICA" in prompt
    assert "cifras del cliente" in prompt
    # Guard: directive must instruct against inventing numbers from outside
    # the EXCERPTS — A5 telemetry showed `invented_periods` was the
    # dominant rejection mode and this is the explicit mitigation.
    assert "no inventes" in prompt.lower()


def test_a3_numeric_directive_fires_on_tarifa_progressive_article(
    numeric_directive_on: None,
) -> None:
    req = PipelineCRequest(
        message="¿Cómo aplico el Art. 242 ET para dividendos a un socio persona natural?",
        topic="dividendos_y_distribucion_utilidades",
        requested_topic="dividendos_y_distribucion_utilidades",
    )
    prompt = _capture_prompt(req)
    assert "DIRECTIVA NUMÉRICA" in prompt
    assert "tarifa progresiva" in prompt
    assert "rangos UVT" in prompt


def test_a3_numeric_directive_fires_on_nit_by_digit(
    numeric_directive_on: None,
) -> None:
    req = PipelineCRequest(
        message="¿Cuándo vence renta para un NIT terminado en 5 en el AG 2024?",
        topic="calendario_obligaciones",
        requested_topic="calendario_obligaciones",
    )
    prompt = _capture_prompt(req)
    assert "DIRECTIVA NUMÉRICA" in prompt
    assert "calendario DIAN por dígito de NIT" in prompt
    # Critical safety clause: when the calendar isn't in evidence, the
    # directive must instruct abstention, not invention.
    assert "consulta el calendario DIAN vigente" in prompt


def test_a3_numeric_directive_does_NOT_fire_on_general_question(
    numeric_directive_on: None,
) -> None:
    """Control case: even with the kill switch ON, a question without
    any numeric cue must NOT carry the DIRECTIVA NUMÉRICA block.
    Unconditional inclusion risked amplifying `invented_periods` per
    the A5 telemetry; cue-gating is the explicit mitigation that
    survives the §17 revert as the helper's internal gate."""
    req = _request()  # "¿Cuál es el régimen de compensación de pérdidas fiscales?"
    prompt = _capture_prompt(req)
    assert "DIRECTIVA NUMÉRICA" not in prompt


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


# ---------------------------------------------------------------------------
# fix_v15_may §5.1 — UVT validator unit tests
#
# Cover the structural validator that closes the fix_v14_may §17 gap.
# Function-level cases call `_no_invented_uvt_ranges` directly (no polish
# pipeline). The shadow-mode end-to-end case exercises the full
# `polish_graph_native_answer` path with a monkeypatched adapter.
# ---------------------------------------------------------------------------


def _evidence_with_excerpt_substring(substring: str) -> GraphEvidenceBundle:
    """Build a single-primary-article evidence bundle whose excerpt
    contains ``substring`` verbatim. Used to assert that polished values
    present in real excerpts pass the validator."""
    excerpt = (
        "Tarifa aplicable: "
        f"{substring}"
        " sobre los ingresos brutos del bimestre."
    )
    return GraphEvidenceBundle(
        primary_articles=(
            GraphEvidenceItem(
                node_kind="ArticleNode",
                node_key="908",
                title="TARIFA RST",
                excerpt=excerpt,
                source_path="renta/et_art_908.md",
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


@pytest.fixture
def _uvt_validator_enforce(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_POLISH_UVT_VALIDATOR", "enforce")


def test_uvt_validator_noop_outside_tarifa_context(
    _uvt_validator_enforce: None,
) -> None:
    """No Art. 240/241/242/383/908 or 'tarifa' reference → validator is
    a noop even if the polished text contains percentages."""
    template = "**Recomendaciones**\n- Verifica el gasto."
    polished = "**Recomendaciones**\n- Verifica el gasto. Margen: 5%."
    assert _no_invented_uvt_ranges(template, polished, None) is True


def test_uvt_validator_rejects_invented_tarifa_pct(
    _uvt_validator_enforce: None,
) -> None:
    """Reproduces pr_rst_anticipo_bimestral_v1: polished asserts a Grupo
    1 tarifa of 3.5 % that is not in the template or excerpts."""
    template = "**Recomendaciones**\n- Aplica la tarifa del Art. 908 ET."
    polished = (
        "**Recomendaciones**\n- Aplica la tarifa del 3,5% según Art. 908 ET."
    )
    evidence = _evidence()  # no 3.5% in any excerpt
    assert _no_invented_uvt_ranges(template, polished, evidence) is False


def test_uvt_validator_accepts_pct_present_in_template(
    _uvt_validator_enforce: None,
) -> None:
    template = "**Recomendaciones**\n- Tarifa Art. 908 ET: 1,2%."
    polished = (
        "**Recomendaciones**\n- Aplica la tarifa del **1,2%** del Art. 908 ET."
    )
    assert _no_invented_uvt_ranges(template, polished, None) is True


def test_uvt_validator_accepts_pct_present_in_evidence_excerpt(
    _uvt_validator_enforce: None,
) -> None:
    """The excerpt the polish prompt rendered counts as ground truth.
    Bold markers must be stripped before comparing."""
    template = "**Recomendaciones**\n- Aplica la tarifa Art. 908 ET."
    polished = "**Recomendaciones**\n- Aplica **2,8%** del Art. 908 ET."
    evidence = _evidence_with_excerpt_substring("2,8%")
    assert _no_invented_uvt_ranges(template, polished, evidence) is True


def test_uvt_validator_decimal_separator_normalization(
    _uvt_validator_enforce: None,
) -> None:
    """3,5% in template must match 3.5% in polished and vice versa."""
    template = "**Recomendaciones**\n- Tarifa Art. 242 ET de 3,5%."
    polished = "**Recomendaciones**\n- Aplica el 3.5% según Art. 242 ET."
    assert _no_invented_uvt_ranges(template, polished, None) is True


def test_uvt_validator_uvt_value_invented(
    _uvt_validator_enforce: None,
) -> None:
    template = "**Recomendaciones**\n- Tabla Art. 383 ET."
    polished = (
        "**Recomendaciones**\n- Rango 95 UVT a tarifa 19% (Art. 383 ET)."
    )
    evidence = _evidence()  # excerpts do NOT include "95 UVT"
    assert _no_invented_uvt_ranges(template, polished, evidence) is False


def test_uvt_validator_uvt_value_present_in_excerpt(
    _uvt_validator_enforce: None,
) -> None:
    template = "**Recomendaciones**\n- Tabla Art. 383 ET."
    polished = "**Recomendaciones**\n- Rango 95 UVT (Art. 383 ET)."
    evidence = _evidence_with_excerpt_substring("95 UVT")
    assert _no_invented_uvt_ranges(template, polished, evidence) is True


def test_uvt_validator_accepts_value_present_in_question(
    _uvt_validator_enforce: None,
) -> None:
    """fix_v15_may §3.4 + post-shadow-panel REFINE: a polished value
    that echoes the user's question is grounded in user input, not
    invented from LLM memory. Regression guard for the
    `ep_gmf_exencion_350uvt_v1` false positive observed in the first
    shadow run on 2026-05-13 (question: "...excede los 350 UVT
    mensuales... deducción del 50% del Art. 115 ET")."""
    template = "**Recomendaciones**\n- Aplica la exención del Art. 872 ET."
    polished = (
        "**Recomendaciones**\n"
        "- La exención de GMF cubre hasta 350 UVT mensuales por cuenta (Art. 872 ET).\n"
        "- Deducción del 50% del GMF pagado (Art. 115 ET)."
    )
    question = (
        "Mi cliente excede los 350 UVT mensuales en retiros marcados como exentos. "
        "¿Cómo aplicar la deducción del 50% del Art. 115 ET?"
    )
    assert (
        _no_invented_uvt_ranges(template, polished, None, question) is True
    )


def test_uvt_validator_mode_default_shadow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LIA_POLISH_UVT_VALIDATOR", raising=False)
    assert _uvt_validator_mode() == "shadow"


def test_uvt_validator_mode_enforce(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_POLISH_UVT_VALIDATOR", "enforce")
    assert _uvt_validator_mode() == "enforce"


def test_uvt_validator_mode_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_POLISH_UVT_VALIDATOR", "off")
    assert _uvt_validator_mode() == "off"


def test_uvt_validator_shadow_mode_does_not_fail_polish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In shadow mode the validator records the invented set but the
    full polish pipeline still returns mode=llm (not rejected). Anchor:
    the §5.4 promotion gate keeps shadow until panel telemetry confirms
    zero false positives — production polish must not flip until then."""
    monkeypatch.setenv("LIA_POLISH_UVT_VALIDATOR", "shadow")

    template = "**Recomendaciones**\n- Aplica la tarifa del Art. 908 ET (art. 908 ET)."
    invented_pct = "3,5%"

    class _UVTInventingAdapter:
        def generate(self, prompt: str) -> str:
            return (
                "**Recomendaciones**\n"
                f"- Aplica la tarifa del {invented_pct} según Art. 908 ET (art. 908 ET).\n"
            )

    resolution = {"selected_provider": "gemini-flash", "model": "gemini-2.5-flash"}
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_UVTInventingAdapter(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_evidence(),  # no 3.5% anywhere
        )
    # Shadow mode: polish still ships the LLM output, validator did NOT reject.
    assert diag["mode"] == "llm", f"expected accept under shadow, got: {diag}"
    assert "3,5" in answer or "3.5" in answer


def test_uvt_validator_enforce_mode_rejects_invented_tarifa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: in enforce mode the same invented-3,5%-on-Art.-908
    polish must be rejected and the template returned with
    ``skip_reason="invented_uvt_ranges"``. This is the v15 INCLUDE
    target for `pr_rst_anticipo_bimestral_v1`."""
    monkeypatch.setenv("LIA_POLISH_UVT_VALIDATOR", "enforce")

    template = "**Recomendaciones**\n- Aplica la tarifa del Art. 908 ET (art. 908 ET)."

    class _UVTInventingAdapter:
        def generate(self, prompt: str) -> str:
            return (
                "**Recomendaciones**\n"
                "- Aplica la tarifa del 3,5% según Art. 908 ET (art. 908 ET).\n"
            )

    resolution = {"selected_provider": "gemini-flash", "model": "gemini-2.5-flash"}
    with patch(
        "lia_graph.pipeline_d.answer_llm_polish.resolve_llm_adapter",
        return_value=(_UVTInventingAdapter(), resolution),
    ):
        answer, diag = polish_graph_native_answer(
            request=_request(),
            template_answer=template,
            evidence=_evidence(),
        )
    assert diag["mode"] == "rejected"
    assert diag["skip_reason"] == "invented_uvt_ranges"
    assert answer == _expected_unpolished(template)

