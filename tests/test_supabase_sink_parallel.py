"""Phase 2b (v6) — parallel Supabase sink.

Pins the determinism + failure-isolation + worker-count semantics of the
four parallelized sink operations. No real Supabase client: the test
uses a fake ``_FakeClient`` that records every upsert/select the sink
makes, so we can assert on call ordering and totals.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from lia_graph.ingestion.supabase_sink import (
    _resolve_sink_workers,
    _run_batches_parallel,
    load_existing_tema,
)


# ── Fake Supabase client ────────────────────────────────────────────


class _FakeExecuteResult:
    def __init__(self, data: list[dict] | None = None) -> None:
        self.data = data or []


class _FakeTable:
    def __init__(self, name: str, parent: "_FakeClient") -> None:
        self._name = name
        self._parent = parent
        self._op: str | None = None
        self._payload: Any = None
        self._select_cols: str | None = None
        self._filter: tuple[str, Any] | None = None
        self._on_conflict: str | None = None

    def upsert(self, batch: list[dict], on_conflict: str | None = None) -> "_FakeTable":
        self._op = "upsert"
        self._payload = list(batch)
        self._on_conflict = on_conflict
        return self

    def select(self, cols: str) -> "_FakeTable":
        self._op = "select"
        self._select_cols = cols
        return self

    def in_(self, col: str, values: list) -> "_FakeTable":
        self._filter = (col, list(values))
        return self

    def limit(self, n: int) -> "_FakeTable":
        return self

    def execute(self) -> _FakeExecuteResult:
        with self._parent._lock:
            self._parent.calls.append(
                {
                    "table": self._name,
                    "op": self._op,
                    "rows": len(self._payload) if self._payload else 0,
                    "filter_values": (self._filter[1] if self._filter else None),
                    "on_conflict": self._on_conflict,
                }
            )
            if self._op == "select" and self._filter:
                data = self._parent._selects_by_filter.get(tuple(self._filter[1]), [])
                return _FakeExecuteResult(data=list(data))
        return _FakeExecuteResult()


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self._lock = threading.Lock()
        self._selects_by_filter: dict[tuple, list[dict]] = {}

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(name, self)

    def seed_select(self, ids: list[str], rows: list[dict]) -> None:
        self._selects_by_filter[tuple(ids)] = rows


# ── 1. Worker-count resolution ─────────────────────────────────────


def test_default_worker_count_is_4(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIA_SUPABASE_SINK_WORKERS", raising=False)
    assert _resolve_sink_workers(None) == 4


def test_env_override_takes_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_SUPABASE_SINK_WORKERS", "12")
    assert _resolve_sink_workers(None) == 12


def test_explicit_kwarg_beats_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_SUPABASE_SINK_WORKERS", "12")
    assert _resolve_sink_workers(3) == 3


# ── 2. _run_batches_parallel determinism + counts ──────────────────


def test_run_batches_parallel_preserves_order_and_sums() -> None:
    calls: list[int] = []
    calls_lock = threading.Lock()

    def _exec(idx: int, batch: list[int]) -> int:
        # Slower-when-earlier so non-determinism would show up as wrong order
        time.sleep(0.01 * (10 - idx))
        with calls_lock:
            calls.append(idx)
        return len(batch) * 2

    batches = [[1, 2], [3, 4, 5], [6], [7, 8, 9, 10]]
    per_batch = _run_batches_parallel(
        batches, execute_fn=_exec, worker_count=4, rate_limit_rpm=0
    )
    # Order preserved regardless of completion
    assert per_batch == [4, 6, 2, 8]
    assert sum(per_batch) == 20
    # All batches seen exactly once
    assert sorted(calls) == [0, 1, 2, 3]


def test_run_batches_parallel_empty_input() -> None:
    assert _run_batches_parallel([], execute_fn=lambda i, b: 0, worker_count=4) == []


def test_run_batches_parallel_raises_on_persistent_failure() -> None:
    def _exec(idx: int, batch: list[int]) -> int:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="supabase_sink batch"):
        _run_batches_parallel(
            [[1], [2]], execute_fn=_exec, worker_count=2, rate_limit_rpm=0
        )


# ── 3. load_existing_tema parallel path ────────────────────────────


def test_load_existing_tema_parallel_merges_all_batches() -> None:
    client = _FakeClient()
    # 300 ids → 2 batches of 150. Pre-seed both batches' return data.
    ids = [f"doc_{i}" for i in range(300)]
    batch_a = ids[:150]
    batch_b = ids[150:]
    client.seed_select(batch_a, [{"doc_id": d, "tema": f"tema_a_{d}"} for d in batch_a[:50]])
    client.seed_select(batch_b, [{"doc_id": d, "tema": f"tema_b_{d}"} for d in batch_b[:30]])

    result = load_existing_tema(client, ids, worker_count=4)

    assert len(result) == 80  # 50 from batch_a + 30 from batch_b
    assert result["doc_0"] == "tema_a_doc_0"
    assert result["doc_150"] == "tema_b_doc_150"
    # Two select calls observed
    selects = [c for c in client.calls if c["op"] == "select"]
    assert len(selects) == 2


def test_load_existing_tema_degrades_to_empty_dict_on_error() -> None:
    class _BrokenClient:
        def table(self, _name: str) -> Any:
            raise RuntimeError("network down")

    result = load_existing_tema(_BrokenClient(), ["doc_1"], worker_count=2)
    assert result == {}


def test_load_existing_tema_empty_input_is_no_op() -> None:
    client = _FakeClient()
    assert load_existing_tema(client, [], worker_count=4) == {}
    assert client.calls == []
