"""next_v1 step 07 — `graph.batch_written` emission from ``_execute_live_statement``.

Pins the contract: after a successful live Cypher statement with write-stats,
the graph client emits a ``graph.batch_written`` event carrying the statement
description, the full stats dict, and elapsed_ms. The ``gui_ingestion_v1.md
§13b.4`` stall detection + step-05 progress endpoint's
``_aggregate_phase_signals`` depend on this signal — without it, the
``falkor_writing`` phase is indistinguishable from a silent stall.

Invariants tested:
  1. Stats dicts with write keys trigger emission.
  2. Stats dicts WITHOUT write keys (read queries, probes) do NOT emit.
  3. ``LIA_GRAPH_EMIT_BATCH_EVENTS=0`` mutes emission entirely.
  4. Emission failures never propagate (observability never blocks writes).
"""

from __future__ import annotations

from typing import Any

import pytest

from lia_graph.graph import client as gc


class _CapturedEmit:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, dict(payload)))


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> _CapturedEmit:
    cap = _CapturedEmit()
    # Patch the instrumentation.emit_event lookup so the client's
    # `from ..instrumentation import emit_event` picks up our stub.
    import sys
    import types

    fake = types.ModuleType("lia_graph.instrumentation")
    fake.emit_event = cap  # type: ignore[attr-defined]
    # Preserve DEFAULT_LOG_PATH if other imports need it; tests don't care.
    fake.DEFAULT_LOG_PATH = "logs/events.jsonl"  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "lia_graph.instrumentation", fake)
    return cap


def _make_statement(description: str = "BatchEdge TEMA") -> gc.GraphWriteStatement:
    return gc.GraphWriteStatement(
        description=description,
        query="MERGE (a)-[:TEMA]->(t)",
        parameters={"rows": []},
    )


def test_emits_event_when_stats_include_write_keys(
    captured: _CapturedEmit, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LIA_GRAPH_EMIT_BATCH_EVENTS", raising=False)
    gc._emit_batch_written_event(
        _make_statement("BatchEdge TEMA"),
        stats={"relationships_created": 7, "properties_set": 14},
        elapsed_ms=123.4,
    )
    assert len(captured.events) == 1
    event_type, payload = captured.events[0]
    assert event_type == "graph.batch_written"
    assert payload["description"] == "BatchEdge TEMA"
    assert payload["stats"] == {"relationships_created": 7, "properties_set": 14}
    assert payload["elapsed_ms"] == 123.4


def test_does_not_emit_for_probe_or_read_stats(
    captured: _CapturedEmit, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LIA_GRAPH_EMIT_BATCH_EVENTS", raising=False)
    # Empty stats — read query
    gc._emit_batch_written_event(_make_statement("CountArticles"), stats={}, elapsed_ms=4.2)
    # Stats with only the index-already-present sentinel
    gc._emit_batch_written_event(
        _make_statement("CreateIndex ArticleNode"),
        stats={"indices_already_present": 1},
        elapsed_ms=2.1,
    )
    # Stats with unrelated keys (not in the write-key set)
    gc._emit_batch_written_event(
        _make_statement("ProbeNodeCount"),
        stats={"nodes_deleted": 0},
        elapsed_ms=1.5,
    )
    assert captured.events == []


def test_env_var_zero_mutes_emission(
    captured: _CapturedEmit, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LIA_GRAPH_EMIT_BATCH_EVENTS", "0")
    gc._emit_batch_written_event(
        _make_statement(),
        stats={"nodes_created": 5},
        elapsed_ms=10.0,
    )
    assert captured.events == []
    monkeypatch.setenv("LIA_GRAPH_EMIT_BATCH_EVENTS", "off")
    gc._emit_batch_written_event(
        _make_statement(),
        stats={"nodes_created": 5},
        elapsed_ms=10.0,
    )
    assert captured.events == []


def test_emission_failure_does_not_propagate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Observability never blocks — an emit_event that raises must be swallowed."""
    import sys
    import types

    fake = types.ModuleType("lia_graph.instrumentation")

    def _raising(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("simulated instrumentation failure")

    fake.emit_event = _raising  # type: ignore[attr-defined]
    fake.DEFAULT_LOG_PATH = "logs/events.jsonl"  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "lia_graph.instrumentation", fake)
    monkeypatch.delenv("LIA_GRAPH_EMIT_BATCH_EVENTS", raising=False)

    # Must not raise.
    gc._emit_batch_written_event(
        _make_statement(),
        stats={"relationships_created": 3},
        elapsed_ms=50.0,
    )


def test_batch_write_stat_keys_set_covers_all_write_types() -> None:
    """Regression guard: the key-set lists every stat name FalkorDB reports
    for writes so adding a new kind (e.g. ``labels_added``) doesn't silently
    drop emission."""
    assert "nodes_created" in gc._BATCH_WRITE_STAT_KEYS
    assert "relationships_created" in gc._BATCH_WRITE_STAT_KEYS
    assert "properties_set" in gc._BATCH_WRITE_STAT_KEYS
    assert "labels_added" in gc._BATCH_WRITE_STAT_KEYS
