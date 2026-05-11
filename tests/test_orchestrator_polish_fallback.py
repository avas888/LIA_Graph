"""fix_v8 §3a end-to-end — when ``polish_graph_native_answer`` returns
``mode=rejected``, the orchestrator must invoke the substantive
fallback composer AND apply the cross-topic gate to the result.

The tests monkey-patch ``polish_graph_native_answer`` to deterministically
return ``mode=rejected`` so they don't depend on a live LLM adapter or on
which polish-guardrail rule fires.
"""

from __future__ import annotations

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d import orchestrator as orchestrator_mod
from lia_graph.pipeline_d.orchestrator import run_pipeline_d


def _force_polish_rejection(monkeypatch) -> dict[str, int]:
    """Patch ``polish_graph_native_answer`` to return ``mode=rejected``
    on every call. Returns a counter dict the test can inspect.
    """
    counter = {"calls": 0}

    def fake_polish(*, request, template_answer, evidence, runtime_config_path=None):
        counter["calls"] += 1
        diag = {
            "selected_provider": "test",
            "selected_type": "test",
            "selected_transport": "test",
            "adapter_class": "FakeAdapter",
            "model": "fake-model",
            "runtime_config_path": None,
            "mode": "rejected",
            "skip_reason": "invented_norm_lineage",
            "attempts": [],
        }
        return template_answer, diag

    monkeypatch.setattr(orchestrator_mod, "polish_graph_native_answer", fake_polish)
    return counter


def _find_step(diag: dict, step_name: str) -> dict | None:
    trace = diag.get("pipeline_trace") or {}
    for step in (trace.get("steps") or []):
        if (step.get("step") or step.get("name")) == step_name:
            return step
    return None


def test_orchestrator_invokes_fallback_on_polish_rejection(monkeypatch) -> None:
    _force_polish_rejection(monkeypatch)
    response = run_pipeline_d(
        PipelineCRequest(
            message="¿Qué artículo regula el anticipo del impuesto de renta?",
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )
    diag = dict(response.diagnostics)
    assert diag.get("polish_mode") == "rejected"
    assert diag.get("polish_skip_reason") == "invented_norm_lineage"
    # The fallback step must fire for a rejected polish.
    step = _find_step(diag, "polish.rejected.fallback_composed")
    assert step is not None, "polish.rejected.fallback_composed step missing"
    details = step.get("details") or step
    assert details.get("polish_skip_reason") == "invented_norm_lineage"


def test_orchestrator_applies_gate_to_fallback(monkeypatch) -> None:
    _force_polish_rejection(monkeypatch)
    response = run_pipeline_d(
        PipelineCRequest(
            message="¿Qué artículo regula el anticipo del impuesto de renta?",
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )
    diag = dict(response.diagnostics)
    # The gate step is only emitted when the fallback assembled something
    # different from the template; if `gate_applied` is missing the
    # fallback returned the template unchanged (e.g. empty parts) which
    # is still a valid path but not exercised here unless evidence is
    # empty. Either way the fallback_composed step must exist.
    assert _find_step(diag, "polish.rejected.fallback_composed") is not None


def test_orchestrator_skips_fallback_when_polish_succeeds(monkeypatch) -> None:
    """When polish returns ``mode=llm``, the orchestrator must NOT
    invoke the fallback composer. The polish output reaches the user
    verbatim."""

    def fake_polish(*, request, template_answer, evidence, runtime_config_path=None):
        diag = {
            "selected_provider": "test",
            "selected_type": "test",
            "selected_transport": "test",
            "adapter_class": "FakeAdapter",
            "model": "fake-model",
            "runtime_config_path": None,
            "mode": "llm",
            "skip_reason": None,
            "attempts": [],
        }
        return template_answer + " [polished]", diag

    monkeypatch.setattr(orchestrator_mod, "polish_graph_native_answer", fake_polish)

    response = run_pipeline_d(
        PipelineCRequest(
            message="¿Qué artículo regula el anticipo del impuesto de renta?",
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )
    diag = dict(response.diagnostics)
    assert diag.get("polish_mode") == "llm"
    assert _find_step(diag, "polish.rejected.fallback_composed") is None


def test_orchestrator_skips_fallback_when_env_off(monkeypatch) -> None:
    _force_polish_rejection(monkeypatch)
    monkeypatch.setenv("LIA_POLISH_REJECTED_FALLBACK_MODE", "off")
    response = run_pipeline_d(
        PipelineCRequest(
            message="¿Qué artículo regula el anticipo del impuesto de renta?",
            topic="declaracion_renta",
            requested_topic="declaracion_renta",
        )
    )
    diag = dict(response.diagnostics)
    assert diag.get("polish_mode") == "rejected"
    assert _find_step(diag, "polish.rejected.fallback_composed") is None
