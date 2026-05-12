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
        trust_tier_weight=0.0,  # isolate lever (b) under test
    )
    score = grouped[0][2]
    # 2 hits × 0.25 boost → 0.40 * 1.5 = 0.60
    assert 0.59 < score < 0.61


# ---------------------------------------------------------------------------
# fix_v11_may §2.A — trust-tier prioritization
# ---------------------------------------------------------------------------


def test_group_high_tier_outranks_medium_tied_baseline() -> None:
    """When two docs tie on base RRF, the high-tier one rises above
    the medium-tier one. ×1.6 vs ×1.3 spread at the default
    trust_tier_weight=0.30."""
    rows = [
        {"doc_id": "doc_medium", "rrf_score": 0.50, "trust_tier": "medium"},
        {"doc_id": "doc_high", "rrf_score": 0.50, "trust_tier": "high"},
    ]
    grouped = _group_chunks_by_doc(rows, top_k=10)
    assert grouped[0][0] == "doc_high"
    assert grouped[1][0] == "doc_medium"
    # 0.50 * 1.6 = 0.80
    assert 0.79 < grouped[0][2] < 0.81
    # 0.50 * 1.3 = 0.65
    assert 0.64 < grouped[1][2] < 0.66


def test_group_high_tier_can_overtake_higher_base_medium() -> None:
    """A high-tier doc with mid base (0.40 * 1.6 = 0.64) beats a
    medium-tier doc with higher base (0.45 * 1.3 = 0.585). This is
    exactly the cluster-A fix the v11A lever targets — when the
    article-anchor index returns 16 docs of similar base score, the
    branded firm rises to top."""
    rows = [
        {"doc_id": "doc_medium_higher_base", "rrf_score": 0.45, "trust_tier": "medium"},
        {"doc_id": "doc_high_lower_base", "rrf_score": 0.40, "trust_tier": "high"},
    ]
    grouped = _group_chunks_by_doc(rows, top_k=10)
    assert grouped[0][0] == "doc_high_lower_base"
    assert grouped[1][0] == "doc_medium_higher_base"


def test_group_low_tier_does_not_promote_below_zero() -> None:
    """A `trust_tier=low` doc should still get its base score (no
    bonus, no penalty). Recall must be preserved when the index lacks
    coverage for a question — a low-tier doc that's the ONLY hit
    should still surface, not be dropped."""
    rows = [
        {"doc_id": "doc_low", "rrf_score": 0.50, "trust_tier": "low"},
    ]
    grouped = _group_chunks_by_doc(rows, top_k=10)
    assert len(grouped) == 1
    assert grouped[0][0] == "doc_low"
    # 0.50 * (1.0 + 0.30 * 0.0) = 0.50 — unchanged from base
    assert 0.49 < grouped[0][2] < 0.51


def test_group_trust_tier_weight_zero_disables_lever_cleanly() -> None:
    """Setting trust_tier_weight=0.0 reverts to pre-11A behavior
    (pure RRF + lexical boost). Used by diagnostic A/B comparisons
    and by tests of other levers in isolation."""
    rows = [
        {"doc_id": "doc_high", "rrf_score": 0.50, "trust_tier": "high"},
        {"doc_id": "doc_low", "rrf_score": 0.60, "trust_tier": "low"},
    ]
    grouped = _group_chunks_by_doc(rows, top_k=10, trust_tier_weight=0.0)
    # Without the lever the higher-base doc wins regardless of tier
    assert grouped[0][0] == "doc_low"
    assert grouped[1][0] == "doc_high"


def test_group_unknown_trust_tier_defaults_to_medium() -> None:
    """Chunks where `trust_tier` is missing, empty, or an unrecognized
    value get the medium multiplier (×1.3 at default weight) so they
    behave like the pre-11A norm. Prevents an upgrade-free corpus from
    silently demoting all docs to baseline."""
    rows = [
        {"doc_id": "doc_a", "rrf_score": 0.50},  # no trust_tier key
        {"doc_id": "doc_b", "rrf_score": 0.50, "trust_tier": ""},
        {"doc_id": "doc_c", "rrf_score": 0.50, "trust_tier": "unrecognized"},
        {"doc_id": "doc_medium_explicit", "rrf_score": 0.50, "trust_tier": "medium"},
    ]
    grouped = _group_chunks_by_doc(rows, top_k=10)
    # All four docs are tied at 0.50 * 1.3 = 0.65
    scores = [round(s, 4) for _id, _row, s in grouped]
    assert all(abs(s - 0.65) < 0.01 for s in scores)


def test_group_combines_trust_tier_with_lexical_ref_boost_multiplicatively() -> None:
    """When BOTH levers fire (article_refs supplied AND chunk has
    trust_tier=high), the score is `base * (1 + ref_boost·hits) *
    (1 + tier_weight·tier_bonus)`. Multiplicative — not additive —
    so the two levers reinforce each other."""
    rows = [
        {
            "doc_id": "doc_high_with_refs",
            "rrf_score": 0.40,
            "trust_tier": "high",
            "chunk_text": "Art. 115 ET y artículo 124-2 ET.",
        },
    ]
    grouped = _group_chunks_by_doc(
        rows,
        top_k=10,
        article_refs=("art_115_et", "art_124_2_et"),
    )
    score = grouped[0][2]
    # 0.40 * (1 + 0.25*2) * (1 + 0.30*2.0) = 0.40 * 1.5 * 1.6 = 0.96
    assert 0.95 < score < 0.97


def test_fetch_surfaces_trust_tier_mix_and_weight_in_diagnostics() -> None:
    """End-to-end — the bundle's `retrieval_diagnostics` carries
    `trust_tier_weight` and `selected_trust_tier_mix` so the operator
    can confirm what the lever is doing on each panel call without
    re-running the corpus."""
    client = _FakeClient(
        canned_chunks=[
            {
                "doc_id": "doc_high",
                "rrf_score": 0.95,
                "chunk_text": "...",
                "summary": "high-tier card",
                "concept_tags": [],
                "relative_path": "x/high.md",
                "topic": "iva",
                "authority": "Crowe Colombia",
                "source_type": "markdown",
                "trust_tier": "high",
                "pais": "colombia",
                "knowledge_class": "interpretative_guidance",
            },
            {
                "doc_id": "doc_medium",
                "rrf_score": 0.80,
                "chunk_text": "...",
                "summary": "medium-tier card",
                "concept_tags": [],
                "relative_path": "x/medium.md",
                "topic": "iva",
                "authority": "Actualicese",
                "source_type": "markdown",
                "trust_tier": "medium",
                "pais": "colombia",
                "knowledge_class": "interpretative_guidance",
            },
        ],
        canned_documents=[
            {"doc_id": "doc_high", "provider_labels": ["Crowe"], "authority": "Crowe Colombia"},
            {"doc_id": "doc_medium", "provider_labels": ["Actualicese"], "authority": "Actualicese"},
        ],
    )
    bundle = fetch_interpretation_candidates(
        query_seed="iva",
        topic="iva",
        client=client,
    )
    diag = bundle.retrieval_diagnostics
    assert diag["trust_tier_weight"] == 0.30
    assert diag["selected_trust_tier_mix"] == {"high": 1, "medium": 1, "low": 0}


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


# ---------------------------------------------------------------------------
# fix_v11_may Phase 11B — planner_anchor_doc_ids (Falkor-resolved anchor)
# ---------------------------------------------------------------------------


def _make_canned_chunks(
    rows: list[tuple[str, float]],
) -> list[dict[str, Any]]:
    """Helper: build a minimal canned_chunks list from (doc_id, rrf_score)
    tuples so each test can declare its candidate set in one line."""
    return [
        {
            "doc_id": doc_id,
            "rrf_score": score,
            "chunk_text": "...",
            "summary": f"summary for {doc_id}",
            "concept_tags": [],
            "relative_path": f"x/{doc_id}.md",
            "topic": "declaracion_renta",
            "subtema": "",
            "authority": "",
            "source_type": "markdown",
            "trust_tier": "medium",
            "pais": "colombia",
            "knowledge_class": "interpretative_guidance",
        }
        for doc_id, score in rows
    ]


def test_planner_anchor_doc_ids_take_precedence_over_python_index() -> None:
    """When `planner_anchor_doc_ids` is non-empty, those doc_ids get the
    ×4 boost — not the doc_ids the Python article_index would have
    returned. Verified by passing a doc_id the article_index could NOT
    know about (a synthetic one) and confirming the boost applied."""
    client = _FakeClient(
        canned_chunks=_make_canned_chunks(
            [
                ("synthetic_planner_anchor_doc", 0.20),  # low base
                ("higher_base_unboosted_doc", 0.60),
            ]
        ),
        canned_documents=[
            {"doc_id": "synthetic_planner_anchor_doc", "provider_labels": [], "authority": ""},
            {"doc_id": "higher_base_unboosted_doc", "provider_labels": [], "authority": ""},
        ],
    )
    bundle = fetch_interpretation_candidates(
        query_seed="some question with no article refs in the text",
        article_refs=(),  # no article refs → article_index returns empty
        client=client,
        planner_anchor_doc_ids=("synthetic_planner_anchor_doc",),
    )
    # 0.20 * 4.0 = 0.80, beats unboosted 0.60
    docs = bundle.docs_selected
    assert docs[0].doc_id == "synthetic_planner_anchor_doc"
    diag = bundle.retrieval_diagnostics
    assert diag["interpretation_anchor_source"] == "planner_falkor"
    assert diag["interpretation_anchor_boosted_chunks"] == 1
    assert diag["interpretation_anchor_eligible_docs"] == 1


def test_planner_anchor_empty_falls_back_to_python_article_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When `planner_anchor_doc_ids` is None / empty AND `article_refs`
    is non-empty, the retriever consults the Python article_index path.
    Verified by stubbing `doc_ids_for_article_refs` to return a known
    set and checking the anchor_source diagnostic reports
    `python_article_index`."""

    def fake_doc_ids(refs):
        return frozenset({"python_indexed_doc"})

    import lia_graph.interpretacion.article_index as ai
    monkeypatch.setattr(ai, "doc_ids_for_article_refs", fake_doc_ids)

    client = _FakeClient(
        canned_chunks=_make_canned_chunks(
            [
                ("python_indexed_doc", 0.20),
                ("other_doc", 0.50),
            ]
        ),
        canned_documents=[
            {"doc_id": "python_indexed_doc", "provider_labels": [], "authority": ""},
            {"doc_id": "other_doc", "provider_labels": [], "authority": ""},
        ],
    )
    bundle = fetch_interpretation_candidates(
        query_seed="art 115 et",
        article_refs=("et_art_115",),
        client=client,
        planner_anchor_doc_ids=(),  # explicit empty
    )
    docs = bundle.docs_selected
    assert docs[0].doc_id == "python_indexed_doc"
    diag = bundle.retrieval_diagnostics
    assert diag["interpretation_anchor_source"] == "python_article_index"


def test_planner_anchor_none_with_no_article_refs_records_anchor_source_none() -> None:
    """When neither anchor source has docs, the diagnostic explicitly
    reports `anchor_source=none` so the operator can tell the boost
    didn't fire."""
    client = _FakeClient(
        canned_chunks=_make_canned_chunks([("doc_a", 0.5), ("doc_b", 0.3)]),
        canned_documents=[
            {"doc_id": "doc_a", "provider_labels": [], "authority": ""},
            {"doc_id": "doc_b", "provider_labels": [], "authority": ""},
        ],
    )
    bundle = fetch_interpretation_candidates(
        query_seed="anything",
        article_refs=(),
        client=client,
        planner_anchor_doc_ids=None,
    )
    diag = bundle.retrieval_diagnostics
    assert diag["interpretation_anchor_source"] == "none"
    assert diag["interpretation_anchor_eligible_docs"] == 0
    assert diag["interpretation_anchor_boosted_chunks"] == 0


def test_planner_anchor_diagnostic_is_surfaced_on_bundle() -> None:
    """The `planner_anchor_diagnostic` passed in by the dispatcher is
    forwarded onto the bundle's `retrieval_diagnostics` under
    `interpretation_anchor_planner` so the operator can confirm which
    Falkor branch supplied (or didn't supply) the anchor."""
    client = _FakeClient(
        canned_chunks=_make_canned_chunks([("doc_a", 0.5)]),
        canned_documents=[{"doc_id": "doc_a", "provider_labels": [], "authority": ""}],
    )
    bundle = fetch_interpretation_candidates(
        query_seed="anything",
        article_refs=("115",),
        client=client,
        planner_anchor_doc_ids=(),
        planner_anchor_diagnostic={
            "anchor_source": "falkor_empty",
            "reason": "no_interprets_edges",
            "matched_articles": 0,
        },
    )
    diag = bundle.retrieval_diagnostics
    assert "interpretation_anchor_planner" in diag
    assert diag["interpretation_anchor_planner"]["anchor_source"] == "falkor_empty"
    assert diag["interpretation_anchor_planner"]["reason"] == "no_interprets_edges"


def test_planner_anchor_strips_empty_doc_ids() -> None:
    """Empty / whitespace-only entries in `planner_anchor_doc_ids` get
    stripped — no Cypher row matches the empty doc_id by accident."""
    client = _FakeClient(
        canned_chunks=_make_canned_chunks([("real_doc", 0.30)]),
        canned_documents=[{"doc_id": "real_doc", "provider_labels": [], "authority": ""}],
    )
    bundle = fetch_interpretation_candidates(
        query_seed="anything",
        client=client,
        planner_anchor_doc_ids=("", "  ", "real_doc"),
    )
    diag = bundle.retrieval_diagnostics
    assert diag["interpretation_anchor_eligible_docs"] == 1
    assert diag["interpretation_anchor_boosted_chunks"] == 1
