"""Tests for ``scripts/validate_batch.py`` (ingestionfix_v3 Phase 3.0).

Exercises each G-check against mocked Supabase/Falkor clients + a local
events.jsonl fixture. The live-wiring helpers (``_LiveFalkorProbe``, the
``main`` CLI) are covered by the rehearsal in Phase 2's run recipe, not
here — unit tests fence the logic that protects the autonomous chain
from advancing on bad data.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "monitoring"
    / "monitor_ingest_topic_batches"
    / "validate_batch.py"
)
_spec = importlib.util.spec_from_file_location("validate_batch", _SCRIPT)
assert _spec is not None and _spec.loader is not None
validate_batch = importlib.util.module_from_spec(_spec)
sys.modules["validate_batch"] = validate_batch
_spec.loader.exec_module(validate_batch)  # type: ignore[union-attr]


# ── Supabase fakes (tight: each G-check calls a narrow chain) ────────


@dataclass
class _Execute:
    data: list[dict[str, Any]]
    count: int | None = None


class _Query:
    def __init__(
        self,
        parent: "_Table",
        op: str,
        *,
        count_mode: bool = False,
    ) -> None:
        self._parent = parent
        self._op = op
        self._filters: list[tuple[str, str, Any]] = []
        self._count_mode = count_mode

    def select(self, columns: str, *, count: str | None = None) -> "_Query":
        self._count_mode = count == "exact"
        return self

    def in_(self, column: str, values: list[Any]) -> "_Query":
        self._filters.append(("in_", column, list(values)))
        return self

    def is_(self, column: str, value: Any) -> "_Query":
        self._filters.append(("is_", column, value))
        return self

    def _matches(self, row: dict[str, Any]) -> bool:
        for op, column, value in self._filters:
            if op == "in_":
                if row.get(column) not in value:
                    return False
            elif op == "is_":
                cell = row.get(column)
                if str(value).lower() == "null":
                    if cell is not None:
                        return False
                else:
                    if cell != value:
                        return False
        return True

    def execute(self) -> _Execute:
        rows = self._parent.rows
        matched = [dict(r) for r in rows if self._matches(r)]
        return _Execute(
            data=matched,
            count=len(matched) if self._count_mode else None,
        )


class _Table:
    def __init__(self, name: str, rows: list[dict[str, Any]]) -> None:
        self.name = name
        self.rows = rows

    def select(self, columns: str, *, count: str | None = None) -> _Query:
        q = _Query(self, "select")
        return q.select(columns, count=count)


class _FakeClient:
    def __init__(self, seed: dict[str, list[dict[str, Any]]]) -> None:
        self._rows: dict[str, list[dict[str, Any]]] = {
            k: [dict(r) for r in v] for k, v in seed.items()
        }

    def table(self, name: str) -> _Table:
        if name not in self._rows:
            self._rows[name] = []
        return _Table(name, self._rows[name])


class _FakeFalkor:
    def __init__(
        self,
        *,
        topic_nodes: dict[str, int],
        tema_edges: dict[str, int],
    ) -> None:
        self._topic_nodes = dict(topic_nodes)
        self._tema_edges = dict(tema_edges)

    def topic_node_count(self, topic_key: str) -> int:
        return self._topic_nodes.get(topic_key, 0)

    def tema_edge_count(self, topic_key: str) -> int:
        return self._tema_edges.get(topic_key, 0)


# ── Individual G-checks ──────────────────────────────────────────────


def test_g1_fingerprint_applied_passes_when_counts_match() -> None:
    client = _FakeClient(
        seed={
            "documents": [
                {"doc_id": "d1", "tema": "laboral", "retired_at": None},
                {"doc_id": "d2", "tema": "laboral", "retired_at": None},
                {"doc_id": "d_ret", "tema": "laboral", "retired_at": "2026-04-01"},
                {"doc_id": "d3", "tema": "iva", "retired_at": None},  # different topic
            ]
        }
    )
    result = validate_batch.check_g1_fingerprint_applied(
        client, topics=["laboral"], expected_row_count=2
    )
    assert result.passed
    assert result.actual == 2
    assert result.gate_id == "G1"


def test_g1_fingerprint_applied_mock_fails_on_mismatch() -> None:
    client = _FakeClient(
        seed={
            "documents": [
                {"doc_id": "d1", "tema": "laboral", "retired_at": None},
            ]
        }
    )
    result = validate_batch.check_g1_fingerprint_applied(
        client, topics=["laboral"], expected_row_count=5
    )
    assert not result.passed
    assert "1" in result.detail and "5" in result.detail


def test_g2_docs_got_chunks_passes_when_every_doc_has_chunks() -> None:
    client = _FakeClient(
        seed={
            "document_chunks": [
                {"chunk_id": "c1", "doc_id": "d1"},
                {"chunk_id": "c2", "doc_id": "d1"},  # multiple chunks per doc OK
                {"chunk_id": "c3", "doc_id": "d2"},
            ]
        }
    )
    result = validate_batch.check_g2_docs_got_chunks(
        client, doc_ids=["d1", "d2"]
    )
    assert result.passed


def test_g2_docs_got_chunks_fails_when_doc_has_no_chunks() -> None:
    client = _FakeClient(
        seed={
            "document_chunks": [
                {"chunk_id": "c1", "doc_id": "d1"},
                # d2 missing — shouldn't happen if sink wrote cleanly
            ]
        }
    )
    result = validate_batch.check_g2_docs_got_chunks(
        client, doc_ids=["d1", "d2"]
    )
    assert not result.passed
    assert result.actual == 1
    assert result.expected == 2


def test_g3_per_topic_falkor_missing() -> None:
    falkor = _FakeFalkor(
        topic_nodes={"laboral": 1, "iva": 0},  # iva not populated
        tema_edges={},
    )
    result = validate_batch.check_g3_topic_nodes(
        falkor, topics=["laboral", "iva"]
    )
    assert not result.passed
    assert "iva" in result.detail


def test_g3_per_topic_falkor_all_populated() -> None:
    falkor = _FakeFalkor(
        topic_nodes={"laboral": 1, "iva": 1},
        tema_edges={},
    )
    result = validate_batch.check_g3_topic_nodes(
        falkor, topics=["laboral", "iva"]
    )
    assert result.passed


def test_g4_tema_edges_fails_when_any_topic_has_zero() -> None:
    falkor = _FakeFalkor(
        topic_nodes={},
        tema_edges={"laboral": 4, "iva": 0},
    )
    result = validate_batch.check_g4_tema_edges(
        falkor, topics=["laboral", "iva"]
    )
    assert not result.passed
    assert "iva" in result.detail


def test_g5_no_failure_events_passes_when_log_clean(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps({"delta_id": "delta_xyz", "event_type": "ingest.delta.run.start"})
        + "\n"
        + json.dumps({"delta_id": "delta_xyz", "event_type": "ingest.delta.cli.done"})
        + "\n",
        encoding="utf-8",
    )
    result = validate_batch.check_g5_no_failure_events(
        events, delta_id="delta_xyz"
    )
    assert result.passed


def test_g5_no_failure_events_fails_on_exception_event(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps({"delta_id": "delta_xyz", "event_type": "ingest.delta.run.start"})
        + "\n"
        + json.dumps(
            {
                "delta_id": "delta_xyz",
                "event_type": "ingest.delta.sink.exception",
                "error": "InvalidURL",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = validate_batch.check_g5_no_failure_events(
        events, delta_id="delta_xyz"
    )
    assert not result.passed
    assert result.actual["match_count"] == 1


def test_g5_ignores_other_deltas(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps(
            {
                "delta_id": "some_other_delta",
                "event_type": "failed_other_run",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = validate_batch.check_g5_no_failure_events(
        events, delta_id="delta_xyz"
    )
    assert result.passed


def test_g6_idempotency_dryrun_nonzero_fails() -> None:
    assert validate_batch.check_g6_sink_idempotency(0).passed
    assert not validate_batch.check_g6_sink_idempotency(3).passed


def test_g7_cross_batch_overlap_detected() -> None:
    result = validate_batch.check_g7_cross_batch_isolation(
        current_doc_ids=["d1", "d2", "d3"],
        next_batch_doc_ids=["d3", "d4"],  # d3 overlaps
    )
    assert not result.passed
    assert result.actual["overlap_count"] == 1


def test_g7_cross_batch_isolation_clean() -> None:
    result = validate_batch.check_g7_cross_batch_isolation(
        current_doc_ids=["d1", "d2"],
        next_batch_doc_ids=["d3", "d4"],
    )
    assert result.passed


def test_g8_null_embed_zero_passes() -> None:
    client = _FakeClient(seed={"document_chunks": []})
    # vacuous pass (no doc_ids).
    assert validate_batch.check_g8_null_embed_zero(client, doc_ids=[]).passed


def test_g8_null_embed_fails_when_any_null() -> None:
    client = _FakeClient(
        seed={
            "document_chunks": [
                {"chunk_id": "c1", "doc_id": "d1", "embedding": [0.1, 0.2]},
                {"chunk_id": "c2", "doc_id": "d1", "embedding": None},
                {"chunk_id": "c3", "doc_id": "d2", "embedding": [0.3, 0.4]},
            ]
        }
    )
    result = validate_batch.check_g8_null_embed_zero(
        client, doc_ids=["d1", "d2"]
    )
    assert not result.passed
    assert result.actual == 1


def test_g9_walltime_in_range() -> None:
    assert validate_batch.check_g9_walltime_in_range(
        elapsed_ms=15 * 60_000
    ).passed
    assert not validate_batch.check_g9_walltime_in_range(
        elapsed_ms=2 * 60_000  # too fast — signals something skipped
    ).passed
    assert not validate_batch.check_g9_walltime_in_range(
        elapsed_ms=40 * 60_000  # too slow — signals stall
    ).passed


def test_g10_chunk_text_anomaly_detection() -> None:
    client = _FakeClient(
        seed={
            "document_chunks": [
                {"chunk_id": "c1", "doc_id": "d1", "chunk_text": "hola"},
                {"chunk_id": "c2", "doc_id": "d1", "chunk_text": ""},  # empty
                {"chunk_id": "c3", "doc_id": "d2", "chunk_text": None},  # null
            ]
        }
    )
    result = validate_batch.check_g10_no_chunk_text_anomalies(
        client, doc_ids=["d1", "d2"]
    )
    assert not result.passed
    assert result.actual == 2


# ── End-to-end summary ──────────────────────────────────────────────


def test_gate_file_written_on_completion(tmp_path: Path) -> None:
    supa = _FakeClient(
        seed={
            "documents": [
                {"doc_id": "d1", "tema": "laboral", "retired_at": None},
                {"doc_id": "d2", "tema": "laboral", "retired_at": None},
            ],
            "document_chunks": [
                {
                    "chunk_id": "c1",
                    "doc_id": "d1",
                    "chunk_text": "x",
                    "embedding": [0.1],
                },
                {
                    "chunk_id": "c2",
                    "doc_id": "d2",
                    "chunk_text": "y",
                    "embedding": [0.2],
                },
            ],
        }
    )
    falkor = _FakeFalkor(
        topic_nodes={"laboral": 1},
        tema_edges={"laboral": 3},
    )
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps({"delta_id": "delta_ok", "event_type": "ingest.delta.cli.done"})
        + "\n",
        encoding="utf-8",
    )

    inputs = validate_batch.ValidationInputs(
        batch=1,
        topics=["laboral"],
        doc_ids=["d1", "d2"],
        manifest_row_count=2,
        delta_id="delta_ok",
        delta_elapsed_ms=10 * 60_000,
        dry_run_row_count_after=0,
        next_batch_doc_ids=["d3", "d4"],
        events_log=events,
        supa_client=supa,
        falkor_probe=falkor,
    )
    summary = validate_batch.run_all_checks(inputs)
    assert summary.all_passed
    gate_path = tmp_path / "gate.json"
    validate_batch.write_gate_file(summary, gate_path)
    payload = json.loads(gate_path.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert payload["batch"] == 1
    assert len(payload["auto_checks"]) == 10
    assert set(payload["manual_smokes"].keys()) == {
        "M1_retrieval_spot_check",
        "M2_main_chat_e2e",
        "M3_eval_c_gold_delta",
    }
    assert set(payload["ultra_tests"].keys()) == {
        "U1_row_level_audit",
        "U2_idempotency_rerun",
        "U3_regression_suite",
        "U4_chain_stop_resume",
    }


def test_summary_flips_to_failed_on_any_gate_failure(tmp_path: Path) -> None:
    supa = _FakeClient(
        seed={
            "documents": [
                {"doc_id": "d1", "tema": "laboral", "retired_at": None},
            ],
            "document_chunks": [
                {"chunk_id": "c1", "doc_id": "d1", "chunk_text": "x", "embedding": [0.1]},
            ],
        }
    )
    falkor = _FakeFalkor(
        topic_nodes={"laboral": 0},  # G3 will fail
        tema_edges={"laboral": 1},
    )
    events = tmp_path / "events.jsonl"
    events.write_text("", encoding="utf-8")

    inputs = validate_batch.ValidationInputs(
        batch=1,
        topics=["laboral"],
        doc_ids=["d1"],
        manifest_row_count=1,
        delta_id="delta_x",
        delta_elapsed_ms=10 * 60_000,
        dry_run_row_count_after=0,
        next_batch_doc_ids=[],
        events_log=events,
        supa_client=supa,
        falkor_probe=falkor,
    )
    summary = validate_batch.run_all_checks(inputs)
    assert not summary.all_passed
    assert summary.to_dict()["status"] == "failed"
    failed_gates = [c["gate_id"] for c in summary.to_dict()["auto_checks"] if not c["passed"]]
    assert "G3" in failed_gates
