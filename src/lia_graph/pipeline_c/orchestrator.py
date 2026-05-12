from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import PipelineCRequest, PipelineCResponse


def generate_llm_strict(
    prompt: str | object,
    *,
    runtime_config_path: object | None = None,
    trace_id: object | None = None,
    requested_provider: str | None = None,
    **_unused: object,
) -> tuple[str, dict[str, Any]]:
    """Resolve an LLM adapter via the runtime config and invoke it.

    Returns ``(text, diag)`` so callers can do
    ``llm_text, llm_diag = generate_llm_strict(prompt, ...)`` — the
    contract every interpretacion + rerank call site already expects.

    Pre-2026-05-11 this was a compat stub that returned a 4-key dict.
    Every caller did ``llm_text, llm_diag = ...`` against the stub,
    which silently failed with "too many values to unpack (expected 2,
    got 4)" — caught as `expert_rerank.judge.mode == "llm_error"` on
    every panel response from v10B onward. Adopting the same
    ``resolve_llm_adapter`` path the polish (`answer_llm_polish.py`)
    uses unblocks the interpretacion rerank judge + the three other
    LLM call sites in `interpretacion/orchestrator.py`.

    Raises:
        RuntimeError: when no LLM adapter is available OR the adapter
            errors out. Callers wrap this in a ``try/except`` and emit
            a diagnostic; the rerank path falls back to lexical-only
            so a single failure doesn't sink the panel.
    """
    # Lazy import — pipeline_c is a stable seam that some lightweight
    # contexts import without wanting the full LLM stack pulled in.
    from ..llm_runtime import DEFAULT_RUNTIME_CONFIG_PATH, resolve_llm_adapter

    config_path = _coerce_runtime_config_path(runtime_config_path) or DEFAULT_RUNTIME_CONFIG_PATH
    adapter, resolution = resolve_llm_adapter(
        runtime_config_path=config_path,
        requested_provider=requested_provider,
    )
    diag = _diag_from_resolution(resolution)
    if trace_id is not None:
        diag["trace_id"] = str(trace_id)

    if adapter is None:
        diag["mode"] = "no_adapter_available"
        raise RuntimeError(
            "generate_llm_strict: no LLM adapter available "
            f"(fallback_skipped={resolution.get('fallback_skipped', [])!r})"
        )

    prompt_text = str(prompt or "")
    try:
        text = adapter.generate(prompt_text)
    except Exception as exc:  # noqa: BLE001 - re-raised; diag captured by caller's except
        diag["mode"] = "adapter_error"
        diag["error_type"] = type(exc).__name__
        # Re-raise so the caller's except block runs (every caller has one);
        # the caller surfaces `mode: llm_error` in its own diagnostic shape.
        raise

    diag["mode"] = "ok"
    return str(text or "").strip(), diag


def _coerce_runtime_config_path(value: object | None) -> Path | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return value
    s = str(value).strip()
    return Path(s) if s else None


def _diag_from_resolution(resolution: dict[str, Any] | None) -> dict[str, Any]:
    """Surface the keys every caller expects on `llm_diag`:
    ``selected_model``, ``selected_type``, ``selected_provider``,
    ``attempts``, ``token_usage``. `resolve_llm_adapter` returns
    ``model`` (not ``selected_model``) and doesn't currently track
    per-call attempts or token_usage — those become ``None`` / ``{}`` /
    ``[]`` defaults rather than missing keys so caller's
    ``.get(...)`` chains stay deterministic.
    """
    res = dict(resolution or {})
    return {
        "selected_model": res.get("model"),
        "selected_type": res.get("selected_type"),
        "selected_provider": res.get("selected_provider"),
        "selected_transport": res.get("selected_transport"),
        "adapter_class": res.get("adapter_class"),
        "strategy": res.get("strategy"),
        "fallback_skipped": list(res.get("fallback_skipped") or []),
        "attempts": [],
        "token_usage": {},
        "runtime_config_path": res.get("runtime_config_path"),
    }


def run_pipeline_c(
    request: PipelineCRequest,
    *,
    index_file: object | None = None,
    policy_path: object | None = None,
    runtime_config_path: object | None = None,
    stream_sink: object | None = None,
) -> PipelineCResponse:
    answer = (
        "La capa compartida de LIA_Graph fue restaurada parcialmente y el "
        "orquestador heredado de la aplicacion previa todavia no se ha reincorporado "
        "completo en este repo."
    )
    sink = stream_sink
    if sink is not None:
        status = getattr(sink, "status", None)
        on_llm_delta = getattr(sink, "on_llm_delta", None)
        if callable(status):
            status("pipeline_c", "Resolviendo la ruta baseline compatible...")
        if callable(on_llm_delta):
            on_llm_delta(answer)
    return PipelineCResponse(
        trace_id=str(request.trace_id or uuid4().hex),
        run_id=uuid4().hex,
        answer_markdown=answer,
        answer_concise=answer,
        followup_queries=(),
        citations=(),
        confidence_score=0.05,
        confidence_mode="compat_stub",
        answer_mode="compat_stub",
        compose_quality=0.0,
        fallback_reason="pipeline_c_orchestrator_not_restored",
        evidence_snippets=(),
        diagnostics={
            "compatibility_mode": True,
            "index_file": str(index_file) if index_file is not None else None,
            "policy_path": str(policy_path) if policy_path is not None else None,
            "runtime_config_path": (
                str(runtime_config_path) if runtime_config_path is not None else None
            ),
        },
        llm_runtime=None,
        token_usage=None,
        timing=None,
        requested_topic=request.requested_topic,
        effective_topic=request.topic,
        secondary_topics=request.secondary_topics,
        topic_adjusted=request.topic_adjusted,
        topic_notice=request.topic_notice,
        topic_adjustment_reason=request.topic_adjustment_reason,
        coverage_notice="Compatibilidad temporal mientras se restaura la capa compartida.",
        pipeline_variant="pipeline_c",
        pipeline_route="pipeline_c",
    )
