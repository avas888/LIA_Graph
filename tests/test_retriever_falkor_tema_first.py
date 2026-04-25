"""Tests for v5 Phase 3 — TEMA-first retrieval path.

Locks the contract: when ``LIA_TEMA_FIRST_RETRIEVAL`` is ``on`` or
``shadow``, the retriever expands its candidate article-key set with
articles that have TEMA edges to the routed topic. Shadow mode emits the
comparison event but keeps the legacy result; live mode merges the new
anchors into the effective key set.

See docs/next/ingestionfix_v5.md §5 Phase 3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from lia_graph.pipeline_d import retriever_falkor


@dataclass
class _FakeRows:
    rows: list[dict[str, Any]]


class _FakeClient:
    """Minimal GraphClient stand-in. Returns pre-seeded rows per query
    description. Any `_execute` call not covered returns empty rows."""

    def __init__(self, rows_by_description: dict[str, list[dict[str, Any]]]) -> None:
        self.calls: list[str] = []
        self._rows_by_description = rows_by_description

    @property
    def config(self) -> Any:
        class _Cfg:
            is_configured = True
            graph_name = "TEST_GRAPH"
        return _Cfg()

    def execute(self, statement: Any, *, strict: bool = False) -> _FakeRows:
        desc = statement.description
        self.calls.append(desc)
        # Simple prefix-match against seeded rows.
        for key, rows in self._rows_by_description.items():
            if key in desc:
                return _FakeRows(rows=rows)
        return _FakeRows(rows=[])


def _make_plan(topic_hints: tuple[str, ...] = ("iva",)) -> Any:
    """Build the smallest plan shape the retriever needs."""
    from lia_graph.pipeline_d.contracts import (
        EvidenceBundleShape,
        GraphRetrievalPlan,
        GraphTemporalContext,
        TraversalBudget,
    )

    return GraphRetrievalPlan(
        query_mode="standard",
        entry_points=(),
        traversal_budget=TraversalBudget(
            max_hops=2,
            max_nodes=50,
            max_edges=100,
            max_paths=20,
            max_support_documents=0,
        ),
        evidence_bundle_shape=EvidenceBundleShape(
            primary_article_limit=10,
            connected_article_limit=0,
            related_reform_limit=0,
            snippet_char_limit=400,
            support_document_limit=0,
        ),
        temporal_context=GraphTemporalContext(),
        topic_hints=topic_hints,
        sub_topic_intent=None,
    )


# ── _retrieve_tema_bound_article_keys ────────────────────────────────


def test_retrieve_tema_bound_returns_empty_for_empty_topic():
    client = _FakeClient({})
    assert retriever_falkor._retrieve_tema_bound_article_keys(
        client=client, topic_key="", limit=10
    ) == ()


def test_retrieve_tema_bound_returns_empty_for_zero_limit():
    client = _FakeClient({})
    assert retriever_falkor._retrieve_tema_bound_article_keys(
        client=client, topic_key="iva", limit=0
    ) == ()


def test_retrieve_tema_bound_returns_deduped_keys_in_order():
    client = _FakeClient(
        {
            "tema_bound_articles topic=iva": [
                {"article_key": "420"},
                {"article_key": "483"},
                {"article_key": "420"},  # duplicate
                {"article_key": ""},      # ignored
                {"article_key": None},    # ignored
                {"article_key": "850"},
            ]
        }
    )
    keys = retriever_falkor._retrieve_tema_bound_article_keys(
        client=client, topic_key="iva", limit=10
    )
    assert keys == ("420", "483", "850")


# ── _tema_first_mode + env parsing ───────────────────────────────────


def test_tema_first_mode_defaults_off(monkeypatch):
    monkeypatch.delenv("LIA_TEMA_FIRST_RETRIEVAL", raising=False)
    assert retriever_falkor._tema_first_mode() == "off"


def test_tema_first_mode_accepts_known_values(monkeypatch):
    for v in ("off", "shadow", "on"):
        monkeypatch.setenv("LIA_TEMA_FIRST_RETRIEVAL", v)
        assert retriever_falkor._tema_first_mode() == v


def test_tema_first_mode_rejects_unknown(monkeypatch):
    monkeypatch.setenv("LIA_TEMA_FIRST_RETRIEVAL", "maybe")
    assert retriever_falkor._tema_first_mode() == "off"


def test_tema_first_mode_case_insensitive(monkeypatch):
    monkeypatch.setenv("LIA_TEMA_FIRST_RETRIEVAL", "SHADOW")
    assert retriever_falkor._tema_first_mode() == "shadow"


# ── Integration: retrieve_graph_evidence ─────────────────────────────


def test_retrieve_graph_evidence_off_mode_does_not_fire_tema_query(monkeypatch):
    """With flag off, no TEMA-first query is issued."""
    monkeypatch.delenv("LIA_TEMA_FIRST_RETRIEVAL", raising=False)
    client = _FakeClient({})
    plan = _make_plan(topic_hints=("iva",))
    _hydrated, evidence = retriever_falkor.retrieve_graph_evidence(
        plan, graph_client=client
    )
    assert evidence.diagnostics["tema_first_mode"] == "off"
    assert evidence.diagnostics["tema_first_anchor_count"] == 0
    assert not any("tema_bound_articles" in call for call in client.calls)


def test_retrieve_graph_evidence_shadow_mode_fires_query_but_does_not_merge(monkeypatch):
    """Shadow mode runs the query + emits an event but keeps the legacy
    effective key set (which is empty here → no primary articles returned)."""
    monkeypatch.setenv("LIA_TEMA_FIRST_RETRIEVAL", "shadow")
    client = _FakeClient(
        {
            "tema_bound_articles topic=laboral": [
                {"article_key": "22"},
                {"article_key": "65"},
            ],
        }
    )
    plan = _make_plan(topic_hints=("laboral",))
    _hydrated, evidence = retriever_falkor.retrieve_graph_evidence(
        plan, graph_client=client
    )
    assert evidence.diagnostics["tema_first_mode"] == "shadow"
    assert evidence.diagnostics["tema_first_anchor_count"] == 2
    # Shadow does NOT merge — primary_articles stays empty (no explicit anchors).
    assert evidence.diagnostics["primary_article_count"] == 0


def test_retrieve_graph_evidence_on_mode_merges_tema_anchors(monkeypatch):
    """Live mode merges TEMA-bound keys into the effective set + primary
    articles include them."""
    monkeypatch.setenv("LIA_TEMA_FIRST_RETRIEVAL", "on")
    client = _FakeClient(
        {
            "tema_bound_articles topic=laboral": [
                {"article_key": "22"},
                {"article_key": "65"},
            ],
            "primary_articles": [
                {
                    "article_key": "22",
                    "heading": "Art. 22",
                    "text_current": "Contrato laboral",
                    "source_path": "CORE/labor/22.md",
                    "status": "vigente",
                },
                {
                    "article_key": "65",
                    "heading": "Art. 65",
                    "text_current": "Salarios",
                    "source_path": "CORE/labor/65.md",
                    "status": "vigente",
                },
            ],
        }
    )
    plan = _make_plan(topic_hints=("laboral",))
    _hydrated, evidence = retriever_falkor.retrieve_graph_evidence(
        plan, graph_client=client
    )
    assert evidence.diagnostics["tema_first_mode"] == "on"
    assert evidence.diagnostics["tema_first_anchor_count"] == 2
    assert evidence.diagnostics["primary_article_count"] == 2


def test_retrieve_graph_evidence_no_topic_hint_no_tema_query(monkeypatch):
    """No topic_hint → TEMA-first skipped even in live mode."""
    monkeypatch.setenv("LIA_TEMA_FIRST_RETRIEVAL", "on")
    client = _FakeClient({})
    plan = _make_plan(topic_hints=())
    _hydrated, evidence = retriever_falkor.retrieve_graph_evidence(
        plan, graph_client=client
    )
    assert evidence.diagnostics["tema_first_mode"] == "on"
    assert evidence.diagnostics["tema_first_topic_key"] is None
    assert evidence.diagnostics["tema_first_anchor_count"] == 0
    assert not any("tema_bound_articles" in call for call in client.calls)


# ── seed_article_keys contract (next_v1 step 01) ─────────────────────


def test_seed_article_keys_includes_tema_first_anchors_in_live_mode(monkeypatch):
    """next_v1 step 01 invariant: seed_article_keys reflects the actual BFS
    seed set (effective_article_keys), not just planner-explicit entry
    points. When the planner anchored nothing explicit but TEMA-first
    expanded the key set + primary articles came back, seed_article_keys
    must be non-empty. Regression guard for the phase-6 0/30 panel gap."""
    monkeypatch.setenv("LIA_TEMA_FIRST_RETRIEVAL", "on")
    client = _FakeClient(
        {
            "tema_bound_articles topic=laboral": [
                {"article_key": "22"},
                {"article_key": "65"},
            ],
            "primary_articles": [
                {
                    "article_key": "22",
                    "heading": "Art. 22",
                    "text_current": "Contrato laboral",
                    "source_path": "CORE/labor/22.md",
                    "status": "vigente",
                },
                {
                    "article_key": "65",
                    "heading": "Art. 65",
                    "text_current": "Salarios",
                    "source_path": "CORE/labor/65.md",
                    "status": "vigente",
                },
            ],
        }
    )
    plan = _make_plan(topic_hints=("laboral",))
    _hydrated, evidence = retriever_falkor.retrieve_graph_evidence(
        plan, graph_client=client
    )
    seed_keys = evidence.diagnostics["seed_article_keys"]
    assert evidence.diagnostics["primary_article_count"] >= 1
    # The stronger invariant: any row with primary_article_count >= 1 has
    # a non-empty seed_article_keys list.
    assert seed_keys, "seed_article_keys must be non-empty when primary_article_count >= 1"
    # And it must reflect the effective BFS seeds, including TEMA-first anchors.
    assert set(seed_keys) >= {"22", "65"}


def test_seed_article_keys_empty_when_shadow_mode_does_not_merge(monkeypatch):
    """Shadow mode observes but does not expand effective_article_keys, so
    seed_article_keys stays at whatever the planner explicitly anchored.
    With an empty entry_points plan, that's the empty list."""
    monkeypatch.setenv("LIA_TEMA_FIRST_RETRIEVAL", "shadow")
    client = _FakeClient(
        {
            "tema_bound_articles topic=laboral": [
                {"article_key": "22"},
            ],
        }
    )
    plan = _make_plan(topic_hints=("laboral",))
    _hydrated, evidence = retriever_falkor.retrieve_graph_evidence(
        plan, graph_client=client
    )
    assert evidence.diagnostics["tema_first_mode"] == "shadow"
    # Shadow mode does not merge → seed set stays at planner-explicit (empty here).
    assert evidence.diagnostics["seed_article_keys"] == []
