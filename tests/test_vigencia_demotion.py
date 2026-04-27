"""Tests for the v3 retriever-side vigencia demotion pass — sub-fix 1B-ε."""

from __future__ import annotations

from datetime import date

import pytest

from lia_graph.pipeline_d.contracts import (
    EvidenceBundleShape,
    GraphRetrievalPlan,
    TraversalBudget,
)
from lia_graph.pipeline_d.vigencia_demotion import (
    DemotionResult,
    apply_demotion,
    run_demotion_pass,
)


def _plan(**overrides) -> GraphRetrievalPlan:
    return GraphRetrievalPlan(
        query_mode="hybrid",
        entry_points=(),
        traversal_budget=TraversalBudget(
            max_hops=2,
            max_nodes=20,
            max_edges=40,
            max_paths=10,
            max_support_documents=5,
        ),
        evidence_bundle_shape=EvidenceBundleShape(
            primary_article_limit=10,
            connected_article_limit=5,
            related_reform_limit=5,
            support_document_limit=5,
        ),
        **overrides,
    )


def _gate_rows_at_date():
    """Mimics the chunk_vigencia_gate_at_date RPC return shape."""

    return [
        # chunk-1 anchored on a derogated ET article → must be dropped
        {
            "chunk_id": "chunk-1",
            "norm_id": "et.art.158-1",
            "role": "anchor",
            "anchor_strength": "ley",
            "state": "DE",
            "state_from": date(2023, 1, 1),
            "state_until": None,
            "record_id": "rec-de",
            "interpretive_constraint": None,
            "demotion_factor": 0.0,
        },
        # chunk-2 anchored on a vigente article → kept full score
        {
            "chunk_id": "chunk-2",
            "norm_id": "et.art.689-3",
            "role": "anchor",
            "anchor_strength": "ley",
            "state": "VM",
            "state_from": date(2023, 1, 1),
            "state_until": None,
            "record_id": "rec-vm",
            "interpretive_constraint": None,
            "demotion_factor": 1.0,
        },
        # chunk-3 anchored on derogada-tácita → demoted to 0.3
        {
            "chunk_id": "chunk-3",
            "norm_id": "et.art.588",
            "role": "anchor",
            "anchor_strength": "ley",
            "state": "DT",
            "state_from": date(2022, 1, 1),
            "state_until": None,
            "record_id": "rec-dt",
            "interpretive_constraint": None,
            "demotion_factor": 0.3,
        },
        # chunk-4 has only a reference role — should not affect score
        {
            "chunk_id": "chunk-4",
            "norm_id": "ley.2277.2022",
            "role": "reference",
            "anchor_strength": "ley",
            "state": "V",
            "state_from": date(2022, 12, 13),
            "state_until": None,
            "record_id": "rec-v",
            "interpretive_constraint": None,
            "demotion_factor": 1.0,
        },
    ]


# ---------------------------------------------------------------------------
# run_demotion_pass
# ---------------------------------------------------------------------------


def test_pass_drops_chunk_with_de_anchor():
    chunk_ids = ["chunk-1", "chunk-2", "chunk-3", "chunk-4", "chunk-5"]
    rows = _gate_rows_at_date()

    def at_date(cids, as_of):
        # The RPC respects the chunk_id filter
        return [r for r in rows if r["chunk_id"] in cids]

    plan = _plan()
    result = run_demotion_pass(
        plan=plan,
        chunk_ids=chunk_ids,
        rpc_at_date_fn=at_date,
        today=date(2026, 4, 27),
    )
    assert result.rpc_kind == "at_date"
    assert result.chunks_seen == 5
    factors = {r.chunk_id: r.score_factor for r in result.per_chunk}
    assert factors["chunk-1"] == 0.0
    assert factors["chunk-2"] == 1.0
    assert factors["chunk-3"] == 0.3
    # chunk-4: only reference role; the demotion pass treats no-anchor as 1.0
    assert factors["chunk-4"] == 1.0
    # chunk-5: no rows returned at all → passthrough 1.0
    assert factors["chunk-5"] == 1.0
    assert result.chunks_dropped == 1
    assert result.chunks_demoted == 1


def test_apply_demotion_drops_zeros_and_scales_kept():
    rows = _gate_rows_at_date()

    def at_date(cids, as_of):
        return [r for r in rows if r["chunk_id"] in cids]

    chunks = [
        {"chunk_id": "chunk-1", "rrf_score": 0.95, "chunk_text": "..."},
        {"chunk_id": "chunk-2", "rrf_score": 0.80, "chunk_text": "..."},
        {"chunk_id": "chunk-3", "rrf_score": 0.70, "chunk_text": "..."},
    ]

    plan = _plan()
    pass_result = run_demotion_pass(
        plan=plan,
        chunk_ids=[c["chunk_id"] for c in chunks],
        rpc_at_date_fn=at_date,
        today=date(2026, 4, 27),
    )
    out = apply_demotion(chunks, pass_result)
    by_id = {c["chunk_id"]: c for c in out}
    assert "chunk-1" not in by_id  # dropped
    assert pytest.approx(by_id["chunk-2"]["rrf_score"]) == 0.80
    assert pytest.approx(by_id["chunk-3"]["rrf_score"]) == 0.70 * 0.3
    # vigencia_v3 annotation present
    assert by_id["chunk-2"]["vigencia_v3"]["anchor_state"] == "VM"
    assert by_id["chunk-3"]["vigencia_v3"]["anchor_state"] == "DT"


def test_pass_handles_for_period():
    chunk_ids = ["chunk-A"]
    rows = [
        {
            "chunk_id": "chunk-A",
            "norm_id": "et.art.240",
            "role": "anchor",
            "anchor_strength": "ley",
            "state": "V",
            "state_from": date(2017, 1, 1),
            "state_until": date(2022, 12, 31),
            "record_id": "rec-pre-2277",
            "interpretive_constraint": None,
            "norm_version_aplicable": "redacción anterior a Ley 2277/2022",
            "demotion_factor": 1.0,
            "art_338_cp_applied": True,
        }
    ]

    def for_period(cids, impuesto, year, label):
        assert impuesto == "renta"
        assert year == 2022
        return rows

    plan = _plan(
        vigencia_query_kind="for_period",
        vigencia_query_payload={"impuesto": "renta", "periodo_year": 2022},
    )
    result = run_demotion_pass(
        plan=plan,
        chunk_ids=chunk_ids,
        rpc_for_period_fn=for_period,
    )
    assert result.rpc_kind == "for_period"
    assert result.per_chunk[0].art_338_cp_applied is True
    assert result.per_chunk[0].score_factor == 1.0


def test_pass_passthrough_when_rpc_unavailable():
    plan = _plan()
    result = run_demotion_pass(
        plan=plan,
        chunk_ids=["a", "b", "c"],
        rpc_at_date_fn=None,
        rpc_for_period_fn=None,
    )
    assert result.chunks_kept == 3
    assert result.chunks_dropped == 0
    for r in result.per_chunk:
        assert r.score_factor == 1.0


def test_pass_empty_chunk_ids_noop():
    plan = _plan()
    result = run_demotion_pass(plan=plan, chunk_ids=[])
    assert result.rpc_kind == "noop"
    assert result.chunks_seen == 0
