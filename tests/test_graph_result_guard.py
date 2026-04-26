"""Tests for ``lia_graph.graph.result_guard.check_resultset_cap``."""

from __future__ import annotations

import os
from typing import Any

import pytest

from lia_graph.graph import result_guard


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FALKORDB_RESULTSET_SIZE_CAP", raising=False)


def _capture_emitted(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, dict[str, Any]]]:
    captured: list[tuple[str, dict[str, Any]]] = []

    def fake_emit(event_type: str, payload: dict[str, Any]) -> None:
        captured.append((event_type, payload))

    monkeypatch.setattr(
        "lia_graph.instrumentation.emit_event", fake_emit, raising=True
    )
    return captured


# (a) Below cap → no event.
def test_no_event_below_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_emitted(monkeypatch)
    result_guard.check_resultset_cap(
        description="probe", query="MATCH (n) RETURN n", row_count=9999
    )
    assert captured == []


# (b) At cap (default 10_000) → event with structured payload.
def test_event_at_default_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_emitted(monkeypatch)
    result_guard.check_resultset_cap(
        description="big_probe",
        query="MATCH (n) RETURN n",
        row_count=10_000,
    )
    assert len(captured) == 1
    event_type, payload = captured[0]
    assert event_type == "graph.resultset_cap_reached"
    assert payload["description"] == "big_probe"
    assert payload["row_count"] == 10_000
    assert payload["cap"] == 10_000
    assert "FalkorDB truncated" in payload["implication"]


# (c) Custom cap via env → respected.
def test_custom_cap_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FALKORDB_RESULTSET_SIZE_CAP", "500")
    captured = _capture_emitted(monkeypatch)
    result_guard.check_resultset_cap(
        description="small_cap_probe", query="MATCH (n) RETURN n", row_count=500
    )
    assert len(captured) == 1
    assert captured[0][1]["cap"] == 500


# (d) Long queries get truncated in the event payload.
def test_long_query_preview_truncated(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_emitted(monkeypatch)
    long_query = "MATCH (n) " + ("RETURN n " * 100)
    result_guard.check_resultset_cap(
        description="long", query=long_query, row_count=10_000
    )
    assert len(captured) == 1
    preview = captured[0][1]["query_preview"]
    assert preview.endswith("…")
    assert len(preview) <= 201


# (e) emit_event raising must not propagate.
def test_emit_failure_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(event_type: str, payload: dict[str, Any]) -> None:
        raise RuntimeError("instrumentation broken")

    monkeypatch.setattr(
        "lia_graph.instrumentation.emit_event", boom, raising=True
    )
    # Must not raise.
    result_guard.check_resultset_cap(
        description="x", query="y", row_count=10_000
    )
