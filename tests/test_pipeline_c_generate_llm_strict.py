"""Regression test for `pipeline_c.orchestrator.generate_llm_strict`.

2026-05-11 fix_v11_may §14.A: the pre-fix shim returned a 4-key dict
(`content`, `reasoning_content`, `finish_reason`, `usage`). Every
caller did ``llm_text, llm_diag = generate_llm_strict(...)``, which
silently failed with ``too many values to unpack (expected 2, got 4)``
— caught as ``expert_rerank.judge.mode = 'llm_error'`` on every panel
response across v10B + v11A + v11B runs. The system was on lexical-only
rerank fallback the whole time without anyone realizing.

The contract is now ``(text, diag)`` — these tests pin that down so
the regression cannot recur. They exercise the function with a stubbed
adapter (no LLM API call, no network).
"""

from __future__ import annotations

from typing import Any

import pytest

from lia_graph.pipeline_c.orchestrator import (
    _diag_from_resolution,
    generate_llm_strict,
)


class _FakeAdapter:
    """Stand-in for an LLMAdapter; records prompts + returns canned text."""

    def __init__(self, *, response: str = "stub response", raises: Exception | None = None) -> None:
        self._response = response
        self._raises = raises
        self.calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        if self._raises is not None:
            raise self._raises
        return self._response


@pytest.fixture
def patch_adapter(monkeypatch: pytest.MonkeyPatch):
    """Monkeypatch `resolve_llm_adapter` to return a fake adapter +
    canned resolution. Returns the adapter so each test can assert
    against `adapter.calls` and tweak responses."""

    def _make(*, adapter: _FakeAdapter, resolution: dict | None = None) -> _FakeAdapter:
        canned_resolution = dict(resolution or {
            "selected_provider": "gemini-flash",
            "selected_type": "gemini",
            "selected_transport": "openai_compat",
            "model": "gemini-2.5-flash",
            "adapter_class": "GeminiChatAdapter",
            "strategy": "ordered_fallback",
            "fallback_skipped": [],
            "runtime_config_path": "config/llm_runtime.json",
        })

        def fake_resolve(*, runtime_config_path=None, requested_provider=None):
            return adapter, canned_resolution

        # Patch at the import site inside pipeline_c.orchestrator's local
        # import (`from ..llm_runtime import ... resolve_llm_adapter`).
        monkeypatch.setattr(
            "lia_graph.llm_runtime.resolve_llm_adapter", fake_resolve
        )
        return adapter

    return _make


# ---------------------------------------------------------------------------
# The contract — `text, diag = generate_llm_strict(...)` MUST work.
# ---------------------------------------------------------------------------


def test_returns_tuple_unpacks_into_text_and_diag(patch_adapter) -> None:
    """The previously-broken pattern. Every caller in the repo does this;
    if this test fails, the rerank judge crashes on every panel call."""
    patch_adapter(adapter=_FakeAdapter(response="hello world"))
    # The literal failing unpack — this would have raised
    # `too many values to unpack (expected 2, got 4)` against the
    # pre-fix dict-returning stub.
    llm_text, llm_diag = generate_llm_strict("any prompt", runtime_config_path=None, trace_id="trace_xyz")
    assert llm_text == "hello world"
    assert isinstance(llm_diag, dict)


def test_diag_carries_keys_every_caller_reads(patch_adapter) -> None:
    """Verifies the keys interpretacion/orchestrator.py + rerank/llm_judge.py
    read off `llm_diag` — `selected_model`, `selected_type`,
    `selected_provider`, `attempts`, `token_usage`. Missing-key drift
    would silently degrade panel diagnostics; this test catches it."""
    patch_adapter(adapter=_FakeAdapter())
    _, diag = generate_llm_strict("prompt", runtime_config_path=None, trace_id=None)
    for required_key in (
        "selected_model",
        "selected_type",
        "selected_provider",
        "attempts",
        "token_usage",
    ):
        assert required_key in diag, f"missing diag key: {required_key}"
    # `attempts` is a list (callers do `list(llm_diag.get('attempts') or [])`)
    assert isinstance(diag["attempts"], list)
    # `token_usage` is a dict
    assert isinstance(diag["token_usage"], dict)


def test_trace_id_is_recorded_when_provided(patch_adapter) -> None:
    patch_adapter(adapter=_FakeAdapter())
    _, diag = generate_llm_strict(
        "prompt",
        runtime_config_path=None,
        trace_id="ep_test:expert-rerank",
    )
    assert diag.get("trace_id") == "ep_test:expert-rerank"


def test_strips_whitespace_from_response(patch_adapter) -> None:
    patch_adapter(adapter=_FakeAdapter(response="   bordered text   "))
    text, _ = generate_llm_strict("prompt", runtime_config_path=None, trace_id=None)
    assert text == "bordered text"


def test_handles_empty_response_as_empty_string(patch_adapter) -> None:
    patch_adapter(adapter=_FakeAdapter(response=""))
    text, diag = generate_llm_strict("prompt", runtime_config_path=None, trace_id=None)
    assert text == ""
    # `mode='ok'` even on empty response — the upstream caller is
    # the one that decides whether empty is failure (e.g. polish
    # treats it as `skip_reason=empty_llm_output`).
    assert diag.get("mode") == "ok"


def test_raises_when_no_adapter_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """When `resolve_llm_adapter` returns `(None, resolution)` (no
    provider configured / all skipped), the function raises RuntimeError.
    Every caller wraps this in `try/except Exception` and surfaces it
    as their own diagnostic mode (`llm_error`, `adapter_error`, etc.)."""
    def fake_resolve(*, runtime_config_path=None, requested_provider=None):
        return None, {"fallback_skipped": [{"provider_id": "x", "reason": "disabled"}]}

    monkeypatch.setattr("lia_graph.llm_runtime.resolve_llm_adapter", fake_resolve)
    with pytest.raises(RuntimeError, match="no LLM adapter available"):
        generate_llm_strict("any prompt", runtime_config_path=None, trace_id=None)


def test_re_raises_adapter_errors(patch_adapter) -> None:
    """When the adapter's `generate(...)` raises, the exception
    propagates so the caller's `except` block runs. The fake adapter
    error type is preserved (not swallowed into a generic RuntimeError)."""
    class _CustomError(Exception):
        pass

    patch_adapter(adapter=_FakeAdapter(raises=_CustomError("upstream timeout")))
    with pytest.raises(_CustomError, match="upstream timeout"):
        generate_llm_strict("prompt", runtime_config_path=None, trace_id=None)


def test_accepts_prompt_as_positional_argument(patch_adapter) -> None:
    """All call sites pass `prompt` as the first positional arg."""
    adapter = patch_adapter(adapter=_FakeAdapter(response="ok"))
    generate_llm_strict("first positional", runtime_config_path=None, trace_id=None)
    assert adapter.calls == ["first positional"]


def test_passes_requested_provider_through_to_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    """`requested_provider` kwarg routes to `resolve_llm_adapter`'s
    same kwarg — used by callers that want to pin a specific provider
    (e.g. `LIA_VIGENCIA_PROVIDER` canonicalizer overrides)."""
    captured: dict[str, Any] = {}

    def fake_resolve(*, runtime_config_path=None, requested_provider=None):
        captured["requested_provider"] = requested_provider
        captured["runtime_config_path"] = runtime_config_path
        return _FakeAdapter(response="ok"), {
            "model": "x",
            "selected_provider": requested_provider or "default",
            "selected_type": "stub",
        }

    monkeypatch.setattr("lia_graph.llm_runtime.resolve_llm_adapter", fake_resolve)
    generate_llm_strict(
        "prompt",
        runtime_config_path=None,
        trace_id=None,
        requested_provider="deepseek-v4-flash",
    )
    assert captured["requested_provider"] == "deepseek-v4-flash"


# ---------------------------------------------------------------------------
# _diag_from_resolution helper — locks the key renaming + default values.
# ---------------------------------------------------------------------------


def test_diag_renames_model_to_selected_model() -> None:
    """`resolve_llm_adapter` returns `model`; callers read `selected_model`."""
    diag = _diag_from_resolution({"model": "gemini-2.5-flash"})
    assert diag["selected_model"] == "gemini-2.5-flash"


def test_diag_defaults_attempts_to_empty_list_and_token_usage_to_empty_dict() -> None:
    """`resolve_llm_adapter` doesn't currently track per-call attempts /
    token_usage. The shim defaults them so caller's
    `list(llm_diag.get('attempts') or [])` chains stay deterministic."""
    diag = _diag_from_resolution({})
    assert diag["attempts"] == []
    assert diag["token_usage"] == {}


def test_diag_from_none_resolution_returns_full_key_set() -> None:
    """Defense against a future refactor where resolve_llm_adapter
    returns None. The keys callers read should still be present."""
    diag = _diag_from_resolution(None)
    for k in ("selected_model", "selected_type", "selected_provider", "attempts", "token_usage"):
        assert k in diag
