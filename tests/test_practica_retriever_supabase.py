"""fix_v13_may Phase 13A — unit tests for the dedicated práctica
Supabase retriever.

Exercises the payload shape (hard `filter_knowledge_class` filter,
optional `boost_topic`), chunk→doc grouping, metadata merge, runtime
shape, and error propagation. Uses a fake SupabaseClient — no HTTP,
no docker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from lia_graph.practica.policy import (
    DEFAULT_RESERVED_SLOTS,
    resolve_reserved_slots,
)
from lia_graph.practica.retriever_supabase import (
    _build_fts_query,
    _group_chunks_by_doc,
    _hybrid_search_payload,
    fetch_practica_candidates,
)
from lia_graph.practica.shared import (
    PracticaChunkRuntime,
    PracticaKnowledgeBundle,
)


# ---------------------------------------------------------------------------
# Fake Supabase client
# ---------------------------------------------------------------------------


@dataclass
class _FakeResp:
    data: Any


class _FakeRPC:
    def __init__(self, client: "_FakeClient", name: str, payload: dict[str, Any]) -> None:
        self._client = client
        self._name = name
        self._payload = payload

    def execute(self) -> _FakeResp:
        self._client.rpc_calls.append((self._name, self._payload))
        if self._client.raise_on_rpc:
            raise self._client.raise_on_rpc
        return _FakeResp(data=list(self._client.canned_chunks))


class _FakeQuery:
    def __init__(self, client: "_FakeClient", table: str) -> None:
        self._client = client
        self._table = table
        self._filters: list[tuple[str, str, Any]] = []
        self._select_cols: str | None = None

    def select(self, cols: str, *, count: str | None = None) -> "_FakeQuery":
        self._select_cols = cols
        return self

    def in_(self, col: str, values: list[Any]) -> "_FakeQuery":
        self._filters.append(("in_", col, list(values)))
        return self

    def execute(self) -> _FakeResp:
        self._client.table_calls.append(
            (self._table, self._select_cols, list(self._filters))
        )
        if self._table == "documents":
            data = []
            for row in self._client.canned_documents:
                ok = True
                for op, col, val in self._filters:
                    if op == "in_" and row.get(col) not in val:
                        ok = False
                        break
                if ok:
                    data.append(row)
            return _FakeResp(data=data)
        return _FakeResp(data=[])


class _FakeTable:
    def __init__(self, client: "_FakeClient", name: str) -> None:
        self._client = client
        self._name = name

    def select(self, cols: str, *, count: str | None = None) -> _FakeQuery:
        return _FakeQuery(self._client, self._name).select(cols, count=count)


@dataclass
class _FakeClient:
    canned_chunks: list[dict[str, Any]] = field(default_factory=list)
    canned_documents: list[dict[str, Any]] = field(default_factory=list)
    rpc_calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    table_calls: list[tuple[str, str | None, list[Any]]] = field(
        default_factory=list
    )
    raise_on_rpc: Exception | None = None

    def rpc(self, name: str, payload: dict[str, Any]) -> _FakeRPC:
        return _FakeRPC(self, name, payload)

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(self, name)


@pytest.fixture(autouse=True)
def _disable_query_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Don't hit Gemini for query embeddings in unit tests."""
    monkeypatch.setenv("LIA_QUERY_EMBEDDINGS_ENABLED", "0")


# ---------------------------------------------------------------------------
# _build_fts_query
# ---------------------------------------------------------------------------


def test_fts_query_strips_stopwords_and_dedupes() -> None:
    q = _build_fts_query("Cómo liquido la retención en la fuente para honorarios")
    assert q is not None
    tokens = [t.strip() for t in q.split("|")]
    assert "la" not in tokens and "en" not in tokens
    assert len(tokens) == len(set(tokens))


def test_fts_query_returns_none_for_pure_stopwords() -> None:
    assert _build_fts_query("") is None
    assert _build_fts_query("la el de y o") is None


def test_fts_query_does_not_prepend_article_refs() -> None:
    """práctica is keyword-driven, not article-anchored — unlike the
    interpretacion lane which prepends `art_xxx_et` tokens."""
    q = _build_fts_query("retención honorarios")
    assert q is not None
    assert "art_115_et" not in q
    assert "honorarios" in q.lower()


# ---------------------------------------------------------------------------
# _hybrid_search_payload
# ---------------------------------------------------------------------------


def test_payload_knowledge_class_filter_is_hard() -> None:
    payload = _hybrid_search_payload(
        query_embedding=None,
        fts_query="retencion | honorarios",
        topic="retencion",
        pais="colombia",
        match_count=24,
    )
    assert payload["filter_knowledge_class"] == "practica_erp"
    # filter_topic is None (topic is ranking signal, not WHERE filter)
    assert payload["filter_topic"] is None


def test_payload_omits_knowledge_class_boost() -> None:
    """The unified retriever uses `knowledge_class_boost`; the
    dedicated lane already hard-filters, so the boost parameter must
    NOT be set (would be a no-op and would confuse trace readers)."""
    payload = _hybrid_search_payload(
        query_embedding=None,
        fts_query="x",
        topic=None,
        pais="colombia",
        match_count=24,
    )
    assert "boost_knowledge_class" not in payload
    assert "knowledge_class_boost" not in payload


def test_payload_topic_boost_conditional() -> None:
    with_topic = _hybrid_search_payload(
        query_embedding=None,
        fts_query="x",
        topic="retencion",
        pais="colombia",
        match_count=24,
    )
    assert with_topic["boost_topic"] == "retencion"
    assert with_topic["filter_topic_boost"] == 1.5

    without_topic = _hybrid_search_payload(
        query_embedding=None,
        fts_query="x",
        topic=None,
        pais="colombia",
        match_count=24,
    )
    assert "boost_topic" not in without_topic
    assert "filter_topic_boost" not in without_topic


def test_payload_topic_boost_skipped_when_floor() -> None:
    """topic_boost=1.0 means the boost is OFF; must NOT show in payload."""
    payload = _hybrid_search_payload(
        query_embedding=None,
        fts_query="x",
        topic="retencion",
        pais="colombia",
        match_count=24,
        topic_boost=1.0,
    )
    assert "boost_topic" not in payload
    assert "filter_topic_boost" not in payload


# ---------------------------------------------------------------------------
# _group_chunks_by_doc
# ---------------------------------------------------------------------------


def test_group_picks_highest_chunk_per_doc() -> None:
    rows = [
        {"doc_id": "doc_a", "rrf_score": 0.2, "chunk_id": "a1"},
        {"doc_id": "doc_a", "rrf_score": 0.8, "chunk_id": "a2"},
        {"doc_id": "doc_b", "rrf_score": 0.5, "chunk_id": "b1"},
    ]
    grouped = _group_chunks_by_doc(rows, top_k=10)
    assert len(grouped) == 2
    assert grouped[0][0] == "doc_a"
    assert grouped[0][1]["chunk_id"] == "a2"
    assert grouped[1][0] == "doc_b"


def test_group_truncates_to_top_k() -> None:
    rows = [{"doc_id": f"d{i}", "rrf_score": float(i)} for i in range(10)]
    grouped = _group_chunks_by_doc(rows, top_k=3)
    assert len(grouped) == 3
    assert [doc_id for doc_id, _r, _s in grouped] == ["d9", "d8", "d7"]


def test_group_handles_empty_rows() -> None:
    assert _group_chunks_by_doc([], top_k=3) == []


def test_group_falls_back_to_fts_rank_when_rrf_absent() -> None:
    rows = [
        {"doc_id": "doc_a", "fts_rank": 0.4},
        {"doc_id": "doc_b", "fts_rank": 0.9},
    ]
    grouped = _group_chunks_by_doc(rows, top_k=2)
    assert grouped[0][0] == "doc_b"


# ---------------------------------------------------------------------------
# fetch_practica_candidates
# ---------------------------------------------------------------------------


def test_fetch_returns_runtime_shape() -> None:
    client = _FakeClient(
        canned_chunks=[
            {
                "doc_id": "doc_a",
                "rrf_score": 0.9,
                "chunk_text": "Liquida la retención antes del día 15.",
                "relative_path": "knowledge_base/practica/x.md",
                "summary": "Guía retención",
                "concept_tags": ["art_383_et"],
            }
        ],
        canned_documents=[
            {
                "doc_id": "doc_a",
                "authority": "Actualícese",
                "provider_labels": ["Actualícese"],
                "source_label": "Guía retención honorarios",
            }
        ],
    )
    bundle = fetch_practica_candidates(
        query_seed="cómo liquido la retención",
        topic="retencion",
        pais="colombia",
        top_k=3,
        client=client,
    )
    assert isinstance(bundle, PracticaKnowledgeBundle)
    assert len(bundle.chunks_selected) == 1
    runtime = bundle.chunks_selected[0]
    assert isinstance(runtime, PracticaChunkRuntime)
    assert runtime.doc_id == "doc_a"
    assert runtime.authority == "Actualícese"
    # source_label is derived from chunk_row['summary'] since the cloud
    # `documents` table doesn't carry a `source_label` column (fix_v13_may
    # APIError fix). The documents row's `source_label` field in canned
    # data is intentionally ignored at the SELECT layer.
    assert runtime.source_label == "Guía retención"
    assert runtime.knowledge_class == "practica_erp"
    assert "retención" in runtime.chunk_text
    assert 0.0 < runtime.retrieval_score <= 1.0
    assert "art_383_et" in runtime.normative_refs


def test_fetch_emits_diagnostics_with_supabase_backend() -> None:
    client = _FakeClient(canned_chunks=[])
    bundle = fetch_practica_candidates(
        query_seed="retencion",
        topic="retencion",
        pais="colombia",
        top_k=3,
        client=client,
    )
    diag = bundle.retrieval_diagnostics
    assert diag["practica_backend"] == "supabase"
    assert diag["mode"] == "supabase_hybrid_search"
    assert diag["candidate_rows"] == 0
    assert diag["selected_chunks"] == 0
    assert diag["topic_boost"] == "retencion"


def test_fetch_propagates_rpc_error() -> None:
    """No silent fallback — RPC exceptions must bubble out for the
    orchestrator dispatcher to handle."""
    client = _FakeClient(raise_on_rpc=RuntimeError("supabase exploded"))
    with pytest.raises(RuntimeError, match="supabase exploded"):
        fetch_practica_candidates(
            query_seed="x", topic=None, pais="colombia", top_k=3, client=client
        )


def test_fetch_top_k_respected() -> None:
    client = _FakeClient(
        canned_chunks=[
            {"doc_id": f"doc_{i}", "rrf_score": float(i), "chunk_text": f"text{i}"}
            for i in range(10)
        ],
        canned_documents=[
            {"doc_id": f"doc_{i}", "authority": "X"} for i in range(10)
        ],
    )
    bundle = fetch_practica_candidates(
        query_seed="x", topic=None, pais="colombia", top_k=3, client=client
    )
    assert len(bundle.chunks_selected) == 3
    # Highest-score doc first
    assert bundle.chunks_selected[0].doc_id == "doc_9"


def test_fetch_payload_uses_hard_kc_filter() -> None:
    client = _FakeClient(canned_chunks=[])
    fetch_practica_candidates(
        query_seed="cómo liquido retención",
        topic="retencion",
        pais="colombia",
        top_k=3,
        client=client,
    )
    assert len(client.rpc_calls) == 1
    name, payload = client.rpc_calls[0]
    assert name == "hybrid_search"
    assert payload["filter_knowledge_class"] == "practica_erp"
    assert payload["filter_topic"] is None
    assert payload["boost_topic"] == "retencion"
    assert "knowledge_class_boost" not in payload


# ---------------------------------------------------------------------------
# policy.resolve_reserved_slots
# ---------------------------------------------------------------------------


def test_reserved_slots_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIA_PRACTICA_RESERVED_SLOTS", raising=False)
    assert resolve_reserved_slots() == DEFAULT_RESERVED_SLOTS


def test_reserved_slots_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_PRACTICA_RESERVED_SLOTS", "5")
    assert resolve_reserved_slots() == 5


def test_reserved_slots_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_PRACTICA_RESERVED_SLOTS", "-2")
    assert resolve_reserved_slots() == 0
    monkeypatch.setenv("LIA_PRACTICA_RESERVED_SLOTS", "100")
    assert resolve_reserved_slots() == 8


def test_reserved_slots_garbage_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_PRACTICA_RESERVED_SLOTS", "not-a-number")
    assert resolve_reserved_slots() == DEFAULT_RESERVED_SLOTS
