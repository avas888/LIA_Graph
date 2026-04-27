"""Tests for the v3 vigencia gate wired into retriever_supabase."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from lia_graph.pipeline_d.contracts import (
    EvidenceBundleShape,
    GraphRetrievalPlan,
    TraversalBudget,
)
from lia_graph.pipeline_d.retriever_supabase import _apply_v3_vigencia_demotion


def _bare_plan(**overrides) -> GraphRetrievalPlan:
    return GraphRetrievalPlan(
        query_mode="hybrid",
        entry_points=(),
        traversal_budget=TraversalBudget(max_hops=2, max_nodes=20, max_edges=40, max_paths=10, max_support_documents=5),
        evidence_bundle_shape=EvidenceBundleShape(primary_article_limit=10, connected_article_limit=5, related_reform_limit=5, support_document_limit=5),
        **overrides,
    )


class _FakeRpcResp:
    def __init__(self, data) -> None:
        self.data = data


class _FakeDB:
    """Mimics db.rpc(name, payload).execute() returning gate rows."""

    def __init__(self, rows: list[dict[str, Any]], expected_name: str = "chunk_vigencia_gate_at_date") -> None:
        self._rows = rows
        self._expected_name = expected_name
        self.calls: list[tuple[str, dict]] = []

    def rpc(self, name: str, payload: dict):
        self.calls.append((name, payload))
        return self  # chainable

    def execute(self):
        return _FakeRpcResp(self._rows)


def test_demotion_drops_de_anchor_chunk():
    chunks = [
        {"chunk_id": "c1", "rrf_score": 0.9, "chunk_text": "..."},  # anchored on derogated
        {"chunk_id": "c2", "rrf_score": 0.8, "chunk_text": "..."},  # vigente
        {"chunk_id": "c3", "rrf_score": 0.5, "chunk_text": "..."},  # no citations → passthrough
    ]
    rpc_rows = [
        {"chunk_id": "c1", "norm_id": "et.art.158-1", "role": "anchor",
         "anchor_strength": "ley", "state": "DE", "demotion_factor": 0.0,
         "interpretive_constraint": None, "record_id": "r-de"},
        {"chunk_id": "c2", "norm_id": "et.art.689-3", "role": "anchor",
         "anchor_strength": "ley", "state": "VM", "demotion_factor": 1.0,
         "interpretive_constraint": None, "record_id": "r-vm"},
    ]
    db = _FakeDB(rpc_rows)
    plan = _bare_plan()
    new_rows, diag = _apply_v3_vigencia_demotion(db, plan, chunks)
    by_id = {c["chunk_id"]: c for c in new_rows}
    assert "c1" not in by_id  # dropped
    assert by_id["c2"]["rrf_score"] == 0.8
    assert by_id["c2"]["vigencia_v3"]["anchor_state"] == "VM"
    assert by_id["c3"]["rrf_score"] == 0.5  # passthrough
    assert diag["status"] == "ok"
    assert diag["chunks_dropped"] == 1


def test_demotion_demotes_dt_anchor_chunk():
    chunks = [{"chunk_id": "c1", "rrf_score": 1.0, "chunk_text": "..."}]
    rpc_rows = [
        {"chunk_id": "c1", "norm_id": "et.art.588", "role": "anchor",
         "anchor_strength": "ley", "state": "DT", "demotion_factor": 0.3,
         "interpretive_constraint": None, "record_id": "r-dt"},
    ]
    db = _FakeDB(rpc_rows)
    plan = _bare_plan()
    new_rows, diag = _apply_v3_vigencia_demotion(db, plan, chunks)
    assert pytest.approx(new_rows[0]["rrf_score"]) == 0.3
    assert new_rows[0]["vigencia_v3"]["anchor_state"] == "DT"
    assert diag["chunks_demoted"] == 1


def test_demotion_uses_for_period_when_planner_cue_present():
    chunks = [{"chunk_id": "c1", "rrf_score": 0.9}]
    rpc_rows = [
        {"chunk_id": "c1", "norm_id": "et.art.240", "role": "anchor",
         "anchor_strength": "ley", "state": "V", "demotion_factor": 1.0,
         "interpretive_constraint": None, "record_id": "r-v",
         "art_338_cp_applied": True, "norm_version_aplicable": "redacción anterior a Ley 2277/2022"},
    ]
    db = _FakeDB(rpc_rows, expected_name="chunk_vigencia_gate_for_period")
    plan = _bare_plan(
        vigencia_query_kind="for_period",
        vigencia_query_payload={"impuesto": "renta", "periodo_year": 2022},
    )
    new_rows, diag = _apply_v3_vigencia_demotion(db, plan, chunks)
    assert diag["rpc_kind"] == "for_period"
    assert db.calls[0][0] == "chunk_vigencia_gate_for_period"
    assert db.calls[0][1]["impuesto"] == "renta"
    assert db.calls[0][1]["periodo_year"] == 2022
    assert new_rows[0]["vigencia_v3"]["art_338_cp_applied"] is True


def test_demotion_no_chunks_noop():
    db = _FakeDB([])
    plan = _bare_plan()
    new_rows, diag = _apply_v3_vigencia_demotion(db, plan, [])
    assert new_rows == []
    assert diag["status"] == "no_chunks"


def test_demotion_rpc_unavailable_passes_through():
    """If the RPC raises (env without v3 schema), retrieval keeps every chunk."""

    class _Broken:
        def rpc(self, name, payload):
            raise RuntimeError("function does not exist")

    chunks = [{"chunk_id": "c1", "rrf_score": 0.9}]
    plan = _bare_plan()
    new_rows, diag = _apply_v3_vigencia_demotion(_Broken(), plan, chunks)
    # Pass should not fail; it returns empty rpc rows → 1.0 factor for every
    # chunk → all kept.
    assert len(new_rows) == 1
    assert diag["status"] == "ok"
    assert diag["chunks_kept"] == 1
