"""fix_v8 §3b regression guards on the polish trace surface.

Locks two invariants that the post-fix_v7 verification needed but didn't
have:

1. The `polish.applied` trace step always carries `mode` + `skip_reason`
   keys (even when polish was skipped or never reached an adapter).
2. `response.diagnostics.polish_mode` + `polish_skip_reason` are present
   on every served chat so downstream consumers (the SME report's
   `_build_retrieval_signal_check`, the probe-skill's digest) can read
   the polish outcome without walking the trace.

These tests run the real orchestrator in artifact mode against a topic
that produces enough evidence for synthesis to reach polish. They do not
require a live LLM adapter — the polish step degrades to
`mode=skipped`/`no_adapter_available` in test env, and the contract here
is about the *trace surface*, not the polish outcome itself.
"""

from __future__ import annotations

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.orchestrator import run_pipeline_d


_VALID_POLISH_MODES = {"llm", "skipped", "rejected", "failed", "unknown"}


def _run_q3() -> dict:
    request = PipelineCRequest(
        message="¿Qué artículo regula el anticipo del impuesto de renta?",
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )
    response = run_pipeline_d(request)
    return dict(response.diagnostics)


def _polish_applied_step(diag: dict) -> dict | None:
    trace = diag.get("pipeline_trace") or {}
    for step in (trace.get("steps") or []):
        name = step.get("step") or step.get("name") or ""
        if name == "polish.applied":
            return step
    return None


def test_polish_applied_step_has_mode_key() -> None:
    diag = _run_q3()
    step = _polish_applied_step(diag)
    assert step is not None, "polish.applied step missing from trace"
    details = step.get("details") or step
    assert "mode" in details, "polish.applied step missing `mode` key"


def test_polish_applied_step_has_skip_reason_key() -> None:
    diag = _run_q3()
    step = _polish_applied_step(diag)
    assert step is not None
    details = step.get("details") or step
    assert "skip_reason" in details, "polish.applied step missing `skip_reason` key"


def test_response_diagnostics_carry_polish_mode() -> None:
    diag = _run_q3()
    assert "polish_mode" in diag, "polish_mode missing from response.diagnostics"
    assert "polish_skip_reason" in diag, "polish_skip_reason missing from response.diagnostics"


def test_polish_mode_enumeration_is_complete() -> None:
    diag = _run_q3()
    mode = diag.get("polish_mode")
    assert mode in _VALID_POLISH_MODES, (
        f"polish_mode={mode!r} not in expected enumeration {_VALID_POLISH_MODES}"
    )


def test_polish_applied_step_mode_matches_diagnostics() -> None:
    """The trace step's `mode` and the lifted `diagnostics.polish_mode`
    must agree — they're populated from the same `llm_runtime_diag.mode`
    field and any drift between them is an instrumentation bug."""
    diag = _run_q3()
    step = _polish_applied_step(diag)
    assert step is not None
    details = step.get("details") or step
    assert details.get("mode") == diag.get("polish_mode")
    assert details.get("skip_reason") == diag.get("polish_skip_reason")
