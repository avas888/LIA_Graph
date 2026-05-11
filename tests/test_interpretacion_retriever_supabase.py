"""fix_v10_may Phase 10B — unit tests for the Supabase-backed
Interpretación de Expertos retriever.

Exercises the full call shape (fts_query construction, RPC payload,
chunk→doc grouping, provider_labels merge, DocumentRecord shape,
diagnostics) using a fake SupabaseClient. No HTTP, no docker.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import pytest

from lia_graph.interpretacion.retriever_supabase import (
    _build_fts_query,
    _group_chunks_by_doc,
    _hybrid_search_payload,
    fetch_interpretation_candidates,
)


# ---------------------------------------------------------------------------
# Fake Supabase client. Records every RPC + table call; lets the test
# inject canned `hybrid_search` chunks and `documents.provider_labels`
# rows.
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

    def eq(self, col: str, val: Any) -> "_FakeQuery":
        self._filters.append(("eq", col, val))
        return self

    def in_(self, col: str, values: list[Any]) -> "_FakeQuery":
        self._filters.append(("in_", col, list(values)))
        return self

    def limit(self, n: int) -> "_FakeQuery":
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
                    if op == "eq" and row.get(col) != val:
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

    def rpc(self, name: str, payload: dict[str, Any]) -> _FakeRPC:
        return _FakeRPC(self, name, payload)

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(self, name)


@pytest.fixture(autouse=True)
def _disable_query_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Don't hit Gemini for query embeddings in unit tests; the
    retriever already tolerates a None vector and the RPC still
    returns FTS-ranked rows."""
    monkeypatch.setenv("LIA_QUERY_EMBEDDINGS_ENABLED", "0")


# ---------------------------------------------------------------------------
# _build_fts_query
# ---------------------------------------------------------------------------


def test_fts_query_dedupes_and_strips_stopwords() -> None:
    q = _build_fts_query(
        "Cuál es la deducción del ICA en renta de la sociedad", ()
    )
    assert q is not None
    tokens = [t.strip() for t in q.split("|")]
    assert "deducción" in tokens or "deduccion" in [t.lower() for t in tokens]
    assert "la" not in tokens and "en" not in tokens  # stopwords
    assert "el" not in tokens
    # No duplicates
    assert len(tokens) == len(set(tokens))


def test_fts_query_article_refs_appear_first() -> None:
    q = _build_fts_query(
        "deducción ICA renta", ("art_115_et", "art_124_2_et")
    )
    assert q is not None
    tokens = [t.strip() for t in q.split("|")]
    assert tokens[0] == "art_115_et"
    assert tokens[1] == "art_124_2_et"


def test_fts_query_empty_when_no_usable_tokens() -> None:
    assert _build_fts_query("", ()) is None
    assert _build_fts_query("a b c d e", ()) is None  # all <2 chars or stopwords
    assert _build_fts_query("la el de y o", ()) is None  # pure stopwords


# ---------------------------------------------------------------------------
# _hybrid_search_payload
# ---------------------------------------------------------------------------


def test_payload_pins_filter_knowledge_class_to_interpretation() -> None:
    payload = _hybrid_search_payload(
        query_embedding=None,
        fts_query="ica | art_115_et",
        topic="declaracion_renta",
        pais="colombia",
        match_count=32,
    )
    assert payload["filter_knowledge_class"] == "interpretative_guidance"
    # filter_topic is None (topic is a ranking signal, not a WHERE filter)
    assert payload["filter_topic"] is None
    # Topic boost present when topic was resolved; lever (a) bumped 1.5 → 2.5
    # so interpretation-class topic-matched docs win against topic-adjacent
    # alternatives without being a hard filter.
    assert payload["boost_topic"] == "declaracion_renta"
    assert payload["filter_topic_boost"] == 2.5


def test_payload_omits_topic_boost_when_topic_unresolved() -> None:
    payload = _hybrid_search_payload(
        query_embedding=None,
        fts_query="anything",
        topic=None,
        pais="colombia",
        match_count=32,
    )
    assert "boost_topic" not in payload
    assert "filter_topic_boost" not in payload


# ---------------------------------------------------------------------------
# _group_chunks_by_doc
# ---------------------------------------------------------------------------


def test_group_picks_highest_scoring_chunk_per_doc() -> None:
    rows = [
        {"doc_id": "doc_a", "rrf_score": 0.2, "chunk_id": "a1"},
        {"doc_id": "doc_a", "rrf_score": 0.8, "chunk_id": "a2"},
        {"doc_id": "doc_b", "rrf_score": 0.5, "chunk_id": "b1"},
        {"doc_id": "doc_b", "fts_rank": 0.3, "chunk_id": "b2"},
    ]
    grouped = _group_chunks_by_doc(rows, top_k=10)
    assert len(grouped) == 2
    assert grouped[0][0] == "doc_a"
    assert grouped[0][1]["chunk_id"] == "a2"  # higher rrf
    assert grouped[1][0] == "doc_b"
    assert grouped[1][1]["chunk_id"] == "b1"  # higher rrf


def test_group_truncates_to_top_k() -> None:
    rows = [
        {"doc_id": f"doc_{i}", "rrf_score": float(i)} for i in range(10)
    ]
    grouped = _group_chunks_by_doc(rows, top_k=3)
    assert len(grouped) == 3
    assert [doc_id for doc_id, _row, _s in grouped] == ["doc_9", "doc_8", "doc_7"]


def test_group_drops_chunks_without_doc_id() -> None:
    rows = [
        {"doc_id": "", "rrf_score": 0.9},
        {"doc_id": None, "rrf_score": 0.8},
        {"doc_id": "doc_x", "rrf_score": 0.5},
    ]
    grouped = _group_chunks_by_doc(rows, top_k=10)
    assert len(grouped) == 1
    assert grouped[0][0] == "doc_x"


# fix_v10_may §5.2 gate-6 lever (b) — lexical article-ref reranking
def test_group_boosts_chunks_with_article_ref_text_hits() -> None:
    """When `article_refs` is supplied, chunks whose text contains those
    refs get a multiplicative boost. Restores the lexical-precision
    intent of the legacy catalog's `2.5 * ref_hits` scoring."""
    rows = [
        {
            "doc_id": "off_topic",
            "rrf_score": 0.50,
            "chunk_text": "Texto genérico sobre ZOMAC sin artículos clave.",
        },
        {
            "doc_id": "on_topic_costos_deducciones",
            "rrf_score": 0.40,  # lower base
            "chunk_text": (
                "El art. 115 ET regula la deducción de impuestos pagados. "
                "Ver también artículo 124-2 ET sobre jurisdicciones."
            ),
        },
    ]
    grouped = _group_chunks_by_doc(
        rows,
        top_k=10,
        article_refs=("art_115_et", "art_124_2_et"),
    )
    # Without boost: off_topic (0.50) wins. With 2 ref hits × 0.25 boost,
    # on_topic_costos_deducciones gets 0.40 * 1.5 = 0.60 → wins.
    assert grouped[0][0] == "on_topic_costos_deducciones"
    assert grouped[1][0] == "off_topic"


def test_group_no_boost_when_article_refs_empty() -> None:
    """When article_refs=(), behavior matches the pre-lever-(b)
    baseline (pure RRF ordering)."""
    rows = [
        {"doc_id": "a", "rrf_score": 0.50, "chunk_text": "art. 115 ET"},
        {"doc_id": "b", "rrf_score": 0.60, "chunk_text": "no refs"},
    ]
    grouped = _group_chunks_by_doc(rows, top_k=10, article_refs=())
    assert grouped[0][0] == "b"  # 0.60 > 0.50 — boost didn't fire
    assert grouped[1][0] == "a"


def test_group_lexical_boost_handles_punctuation_variants() -> None:
    """Article ref tokenization tolerates `art.`, `artículo`, `art_`,
    `articulo`, with dash/dot/underscore in sub-numbers."""
    rows = [
        {
            "doc_id": "doc_a",
            "rrf_score": 0.40,
            "chunk_text": "Artículo 124-2 ET y art. 115 son relevantes.",
        },
    ]
    grouped = _group_chunks_by_doc(
        rows,
        top_k=10,
        article_refs=("art_115_et", "art_124_2_et"),
    )
    score = grouped[0][2]
    # 2 hits × 0.25 boost → 0.40 * 1.5 = 0.60
    assert 0.59 < score < 0.61


# ---------------------------------------------------------------------------
# End-to-end with fake client
# ---------------------------------------------------------------------------


def test_fetch_returns_supabase_diagnostics_and_documentrecords() -> None:
    client = _FakeClient(
        canned_chunks=[
            {
                "doc_id": "EXPERTOS_crowe_art_124_2",
                "chunk_id": "c1",
                "rrf_score": 0.95,
                "fts_rank": 0.7,
                "chunk_text": "Análisis de Crowe sobre Art. 124-2 ET …",
                "summary": "Art. 124-2 — pagos al exterior",
                "concept_tags": ["art_124_2_et", "panama"],
                "relative_path": "CORE/EXPERTOS/crowe/art_124_2.md",
                "topic": "declaracion_renta",
                "subtema": "",
                "authority": "",
                "source_type": "markdown",
                "trust_tier": "high",
                "pais": "colombia",
                "knowledge_class": "interpretative_guidance",
            },
            {
                "doc_id": "EXPERTOS_ey_art_124_2",
                "chunk_id": "c2",
                "rrf_score": 0.80,
                "chunk_text": "EY interpreta jurisdicciones no cooperantes …",
                "summary": "EY — paraísos fiscales",
                "concept_tags": ["art_124_2_et"],
                "relative_path": "CORE/EXPERTOS/ey/art_124_2.md",
                "topic": "declaracion_renta",
                "subtema": "",
                "authority": "EY",
                "source_type": "markdown",
                "trust_tier": "high",
                "pais": "colombia",
                "knowledge_class": "interpretative_guidance",
            },
        ],
        canned_documents=[
            {
                "doc_id": "EXPERTOS_crowe_art_124_2",
                "provider_labels": ["Crowe Colombia"],
                "authority": "Crowe Colombia",
            },
            {
                "doc_id": "EXPERTOS_ey_art_124_2",
                "provider_labels": ["EY", "Ernst & Young"],
                "authority": "EY",
            },
        ],
    )

    bundle = fetch_interpretation_candidates(
        query_seed="Pagos a Panamá deducibilidad Art. 124-2 ET",
        # Intentionally NO article_refs here so the end-to-end fixture
        # tests pure-RRF ordering against the canned hybrid_search rows.
        # Lever (b) lexical-boost behavior is covered by the dedicated
        # `test_group_boosts_chunks_with_article_ref_text_hits` test.
        article_refs=(),
        topic="declaracion_renta",
        pais="colombia",
        top_k=8,
        client=client,
    )

    # Diagnostics shape — interpretation_backend is the new key the
    # ui_chat_payload whitelist will surface to the frontend.
    diag = bundle.retrieval_diagnostics
    assert diag["interpretation_backend"] == "supabase"
    assert diag["mode"] == "supabase_hybrid_search"
    assert diag["candidate_rows"] == 2
    assert diag["selected_docs"] == 2
    assert diag["topic_boost"] == "declaracion_renta"
    assert diag["fts_query_present"] is True

    # RPC payload was correct
    assert len(client.rpc_calls) == 1
    name, payload = client.rpc_calls[0]
    assert name == "hybrid_search"
    assert payload["filter_knowledge_class"] == "interpretative_guidance"
    assert payload["filter_topic"] is None
    assert payload["boost_topic"] == "declaracion_renta"

    # Provider lookup was batched in a single in_(...) call
    docs_table_calls = [c for c in client.table_calls if c[0] == "documents"]
    assert len(docs_table_calls) == 1

    # DocumentRecord shape — providers + score + class
    docs = bundle.docs_selected
    assert len(docs) == 2
    crowe = next(d for d in docs if "crowe" in d.relative_path.lower())
    ey = next(d for d in docs if "ey" in d.relative_path.lower())
    # DocumentRecord normalizes list → tuple at construction time
    assert tuple(crowe.provider_labels) == ("Crowe Colombia",)
    assert tuple(ey.provider_labels) == ("EY", "Ernst & Young")
    assert crowe.knowledge_class == "interpretative_guidance"
    assert ey.knowledge_class == "interpretative_guidance"
    # The Crowe row had higher rrf_score → normalized retrieval_score = 1.0
    assert crowe.retrieval_score == 1.0
    # EY had 0.80 / 0.95 = ~0.8421
    assert 0.83 < ey.retrieval_score < 0.85


def test_fetch_returns_empty_bundle_when_no_chunks() -> None:
    client = _FakeClient(canned_chunks=[], canned_documents=[])
    bundle = fetch_interpretation_candidates(
        query_seed="zzz_no_match_query",
        article_refs=(),
        topic=None,
        pais="colombia",
        top_k=8,
        client=client,
    )
    assert bundle.docs_selected == ()
    assert bundle.retrieval_diagnostics["interpretation_backend"] == "supabase"
    assert bundle.retrieval_diagnostics["selected_docs"] == 0
    assert bundle.retrieval_diagnostics["candidate_rows"] == 0


def test_fetch_propagates_rpc_error() -> None:
    """Per CLAUDE.md — Supabase adapter must propagate errors, not
    fall back silently."""

    class _FailingClient(_FakeClient):
        def rpc(self, name: str, payload: dict[str, Any]) -> Any:
            class _Boom:
                def execute(self) -> None:
                    raise RuntimeError("upstream RPC unavailable")
            return _Boom()

    client = _FailingClient()
    # _call_hybrid_search retries once with stripped payload; both
    # attempts raise; the exception propagates out of fetch_*.
    with pytest.raises(RuntimeError):
        fetch_interpretation_candidates(
            query_seed="anything",
            article_refs=(),
            topic="declaracion_renta",
            pais="colombia",
            top_k=4,
            client=client,
        )


def test_fetch_supplies_default_authority_from_provider_when_missing() -> None:
    """When the chunk row's `authority` is empty, the retriever falls
    back to the first provider label so the card has a non-empty
    attribution string."""
    client = _FakeClient(
        canned_chunks=[
            {
                "doc_id": "doc_x",
                "rrf_score": 0.9,
                "chunk_text": "...",
                "summary": "Some heading",
                "concept_tags": [],
                "relative_path": "x.md",
                "topic": "iva",
                "authority": "",  # explicitly empty
                "source_type": "markdown",
                "trust_tier": "medium",
                "pais": "colombia",
                "knowledge_class": "interpretative_guidance",
            },
        ],
        canned_documents=[
            {"doc_id": "doc_x", "provider_labels": ["KPMG"], "authority": ""},
        ],
    )
    bundle = fetch_interpretation_candidates(
        query_seed="iva",
        topic="iva",
        client=client,
    )
    [doc] = bundle.docs_selected
    assert doc.authority == "KPMG"
