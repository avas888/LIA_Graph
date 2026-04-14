"""Feature flags for the Gemini Quality Leap v1.2 workstreams.

Every workstream defined in ``docs/quality_ranking/gemini_quality_leap_plan_v1_2.md``
is exposed here as a tri-state flag: ``off`` (default), ``shadow`` or ``on``.

The master kill switch ``LIA_QUALITY_LEAP`` also gates the whole feature family:
when it is ``off`` (default), every workstream is forced to ``off`` regardless of
the per-W flag, so the pipeline is guaranteed to behave identically to ``main``.

All reads happen lazily from ``os.environ`` so tests can monkey-patch the
environment between cases. For structured in-process overrides use
``override_flags``.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from enum import Enum
from typing import Iterator, Mapping


class WorkstreamMode(str, Enum):
    """Tri-state flag value for an individual workstream."""

    OFF = "off"
    SHADOW = "shadow"
    ON = "on"

    @classmethod
    def parse(cls, value: str | None, *, default: "WorkstreamMode" = None) -> "WorkstreamMode":
        fallback = default if default is not None else cls.OFF
        if value is None:
            return fallback
        raw = str(value).strip().lower()
        if not raw:
            return fallback
        if raw in {"0", "false", "no", "n"}:
            return cls.OFF
        if raw in {"1", "true", "yes", "y", "on", "enabled"}:
            return cls.ON
        for mode in cls:
            if mode.value == raw:
                return mode
        return fallback


_MASTER_KILL_ENV = "LIA_QUALITY_LEAP"
_TRACE_ENV = "LIA_QL_TRACE"

# Canonical ids of the workstreams defined in the plan. Keep in lockstep with
# the plan: any new W added must land both here and in the plan doc.
WORKSTREAM_IDS: tuple[str, ...] = (
    "W1",  # answer_spec
    "W2",  # answer_assertiveness
    "W3",  # claim_pack
    "W4",  # dynamic_evidence_budget
    "W5",  # deterministic_helpers
    "W6",  # quality_critic
    "W7",  # normative_edges (graph_edges_v1) — default ON
    "W8",  # planner_graph_walk (graph_edges_v1) — default ON
    "W9",  # reserved
)

# Workstreams that default to ON when master is active.
# All others default to OFF (must be explicitly enabled).
_WORKSTREAM_DEFAULT_ON: frozenset[str] = frozenset({"W1", "W2", "W3", "W5", "W7", "W8"})

_WORKSTREAM_ENV_TEMPLATE = "LIA_QL_{ws}"

# Process-level overrides used by tests and by ``override_flags``.
_OVERRIDES: dict[str, str] = {}


def _env_lookup(name: str) -> str | None:
    if name in _OVERRIDES:
        return _OVERRIDES[name]
    return os.environ.get(name)


def kill_switch_on() -> bool:
    """Return True when the master kill switch is engaged (pipeline frozen to main)."""

    raw = _env_lookup(_MASTER_KILL_ENV)
    return WorkstreamMode.parse(raw, default=WorkstreamMode.ON) is WorkstreamMode.OFF


def master_mode() -> WorkstreamMode:
    """Return the raw mode of the master switch (for reporting / traces)."""

    return WorkstreamMode.parse(_env_lookup(_MASTER_KILL_ENV), default=WorkstreamMode.ON)


def trace_enabled() -> bool:
    """Return True when the quality trace writer should persist artifacts."""

    raw = _env_lookup(_TRACE_ENV)
    return WorkstreamMode.parse(raw, default=WorkstreamMode.OFF) is not WorkstreamMode.OFF


def workstream_mode(workstream_id: str) -> WorkstreamMode:
    """Return the effective ``WorkstreamMode`` for a given ``W{n}`` id."""

    key = str(workstream_id or "").strip().upper()
    if key not in WORKSTREAM_IDS:
        return WorkstreamMode.OFF
    if kill_switch_on():
        return WorkstreamMode.OFF
    raw = _env_lookup(_WORKSTREAM_ENV_TEMPLATE.format(ws=key))
    default = WorkstreamMode.ON if key in _WORKSTREAM_DEFAULT_ON else WorkstreamMode.OFF
    return WorkstreamMode.parse(raw, default=default)


def is_eligible(workstream_id: str) -> WorkstreamMode:
    """Alias of ``workstream_mode``; the name used by the plan."""

    return workstream_mode(workstream_id)


def is_on(workstream_id: str) -> bool:
    return workstream_mode(workstream_id) is WorkstreamMode.ON


def is_shadow(workstream_id: str) -> bool:
    return workstream_mode(workstream_id) is WorkstreamMode.SHADOW


def is_active(workstream_id: str) -> bool:
    """Return True for both ``shadow`` and ``on`` (i.e., any non-off mode)."""

    return workstream_mode(workstream_id) is not WorkstreamMode.OFF


def snapshot() -> dict[str, str]:
    """Return a JSON-serialisable snapshot of all relevant flag values."""

    data: dict[str, str] = {
        _MASTER_KILL_ENV: master_mode().value,
        _TRACE_ENV: WorkstreamMode.parse(_env_lookup(_TRACE_ENV), default=WorkstreamMode.OFF).value,
    }
    for ws in WORKSTREAM_IDS:
        data[_WORKSTREAM_ENV_TEMPLATE.format(ws=ws)] = workstream_mode(ws).value
    return data


def _apply_overrides(values: Mapping[str, str]) -> None:
    _OVERRIDES.update({str(key): str(value) for key, value in values.items()})


def _clear_overrides(keys: Iterator[str]) -> None:
    for key in list(keys):
        _OVERRIDES.pop(str(key), None)


@contextmanager
def override_flags(**overrides: str) -> Iterator[None]:
    """Context manager to temporarily override flag values in-process.

    Keys may be either the raw env var names (``LIA_QUALITY_LEAP``) or the
    workstream id (``W3`` → ``LIA_QL_W3``) plus the master alias
    ``master`` → ``LIA_QUALITY_LEAP`` and ``trace`` → ``LIA_QL_TRACE``.
    """

    resolved: dict[str, str] = {}
    for key, value in overrides.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        upper = normalized_key.upper()
        if upper == "MASTER":
            env_key = _MASTER_KILL_ENV
        elif upper == "TRACE":
            env_key = _TRACE_ENV
        elif upper in WORKSTREAM_IDS:
            env_key = _WORKSTREAM_ENV_TEMPLATE.format(ws=upper)
        else:
            env_key = normalized_key
        resolved[env_key] = str(value)
    previous = {key: _OVERRIDES.get(key) for key in resolved}
    _apply_overrides(resolved)
    try:
        yield
    finally:
        for key, prev in previous.items():
            if prev is None:
                _OVERRIDES.pop(key, None)
            else:
                _OVERRIDES[key] = prev


def reset_overrides() -> None:
    """Clear every in-process override (for test teardown)."""

    _OVERRIDES.clear()


__all__ = [
    "WORKSTREAM_IDS",
    "WorkstreamMode",
    "is_active",
    "is_eligible",
    "is_on",
    "is_shadow",
    "kill_switch_on",
    "master_mode",
    "override_flags",
    "reset_overrides",
    "snapshot",
    "trace_enabled",
    "workstream_mode",
]
