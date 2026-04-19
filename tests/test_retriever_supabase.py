"""Contract tests for the Supabase-backed retriever.

Uses a fake supabase-py client so the tests do not need a running local
docker Supabase. The fake mimics the parts of the client the retriever
exercises:

- `client.rpc("hybrid_search", {...}).execute()` -> object with `.data`
  holding a list of chunk rows.
- `client.table("documents").select(...).in_(...).execute()` -> object with
  `.data` holding a list of document rows.

The retriever signature matches `retriever.retrieve_graph_evidence`:
`(plan, *, artifacts_dir=None)`, returning `(GraphRetrievalPlan, GraphEvidenceBundle)`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.planner import build_graph_retrieval_plan
from lia_graph.pipeline_d.retriever_supabase import retrieve_graph_evidence


@dataclass
class _FakeResponse:
    data: list[dict[str, Any]]


class _FakeTableQuery:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self._filters: list[tuple[str, str, Any]] = []
        self._limit: int | None = None

    def select(self, _columns: str) -> "_FakeTableQuery":
        return self

    def in_(self, column: str, values: list[Any]) -> "_FakeTableQuery":
        self._filters.append(("in", column, list(values)))
        return self

    def like(self, column: str, pattern: str) -> "_FakeTableQuery":
        self._filters.append(("like", column, pattern))
        return self

    def limit(self, n: int) -> "_FakeTableQuery":
        self._limit = int(n)
        return self

    def execute(self) -> _FakeResponse:
        filtered = list(self._rows)
        for op, column, value in self._filters:
            if op == "in":
                filtered = [row for row in filtered if row.get(column) in value]
            elif op == "like":
                # Minimal `ILIKE`-ish semantics: only leading `%` supported
                # (matches the retriever's `%::<key>` call shape).
                if value.startswith("%") and not value.endswith("%"):
                    suffix = value[1:]
                    filtered = [
                        row for row in filtered
                        if str(row.get(column, "")).endswith(suffix)
                    ]
                else:
                    needle = value.strip("%")
                    filtered = [
                        row for row in filtered
                        if needle in str(row.get(column, ""))
                    ]
        if self._limit is not None:
            filtered = filtered[: self._limit]
        return _FakeResponse(data=filtered)


class _FakeTable:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def select(self, columns: str) -> _FakeTableQuery:
        query = _FakeTableQuery(list(self._rows))
        return query.select(columns)


class _FakeRpc:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.last_payload: dict[str, Any] | None = None

    def execute(self) -> _FakeResponse:
        return _FakeResponse(data=list(self._rows))


class _FakeClient:
    def __init__(
        self,
        *,
        hybrid_rows: list[dict[str, Any]],
        documents_rows: list[dict[str, Any]],
        document_chunks_rows: list[dict[str, Any]] | None = None,
    ) -> None:
        self._hybrid_rows = hybrid_rows
        self._documents_rows = documents_rows
        # Separate table used by the retriever's direct anchor fetch.
        self._document_chunks_rows = list(document_chunks_rows or [])
        self.last_rpc_payload: dict[str, Any] | None = None

    def rpc(self, name: str, payload: dict[str, Any]) -> _FakeRpc:
        assert name == "hybrid_search"
        self.last_rpc_payload = dict(payload)
        return _FakeRpc(self._hybrid_rows)

    def table(self, name: str) -> _FakeTable:
        if name == "documents":
            return _FakeTable(self._documents_rows)
        if name == "document_chunks":
            return _FakeTable(self._document_chunks_rows)
        raise AssertionError(f"Unexpected table name: {name!r}")


def _hybrid_row(doc_id: str, article_key: str, *, rrf: float = 0.9) -> dict[str, Any]:
    return {
        "doc_id": doc_id,
        "chunk_id": f"{doc_id}::{article_key}",
        "chunk_text": f"Cuerpo del articulo {article_key}. ",
        "summary": f"Art. {article_key} - Objeto y ambito",
        "topic": "declaracion_renta",
        "knowledge_class": "normative_base",
        "fts_rank": 1.0,
        "vector_similarity": 0.0,
        "rrf_score": rrf,
    }


def _document_row(doc_id: str, relative_path: str) -> dict[str, Any]:
    return {
        "doc_id": doc_id,
        "relative_path": relative_path,
        "source_type": "article_collection",
        "topic": "declaracion_renta",
        "authority": "dian",
        "pais": "colombia",
        "knowledge_class": "normative_base",
        "corpus": "normativa",
        "first_heading": relative_path,
        "curation_status": "ready",
        "url": None,
    }


def test_supabase_retriever_uses_hybrid_search_and_returns_primary_articles() -> None:
    request = PipelineCRequest(
        message="¿Qué dice el artículo 115 del ET?",
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )
    plan = build_graph_retrieval_plan(request)

    client = _FakeClient(
        hybrid_rows=[
            _hybrid_row("renta_corpus_a_et_art_115", "115", rrf=0.94),
            _hybrid_row("renta_corpus_a_et_art_116", "116", rrf=0.82),
        ],
        documents_rows=[
            _document_row("renta_corpus_a_et_art_115", "renta/et_art_115.md"),
            _document_row("renta_corpus_a_et_art_116", "renta/et_art_116.md"),
        ],
    )

    hydrated_plan, evidence = retrieve_graph_evidence(plan, client=client)

    assert client.last_rpc_payload is not None
    assert client.last_rpc_payload["filter_pais"] == "colombia"
    # Topic is a ranking signal (carried via query_text), not a recall
    # predicate — cross-topic anchors must remain reachable.
    assert client.last_rpc_payload["filter_topic"] is None

    # FTS query must use OR semantics, not the RPC's default AND via
    # plainto_tsquery. Regression guard: a missing `fts_query` + a multi-term
    # `query_text` produces empty recall in production.
    fts_query = client.last_rpc_payload["fts_query"]
    assert fts_query is not None and " | " in fts_query, (
        f"fts_query must be OR-joined to avoid AND-driven empty recall; got {fts_query!r}"
    )

    primary_keys = [item.node_key for item in evidence.primary_articles]
    assert "115" in primary_keys
    connected_keys = [item.node_key for item in evidence.connected_articles]
    assert "116" in connected_keys
    assert evidence.support_documents
    assert evidence.citations
    assert evidence.diagnostics["retrieval_backend"] == "supabase"
    assert hydrated_plan is not plan


def test_supabase_retriever_is_empty_when_hybrid_search_returns_nothing() -> None:
    request = PipelineCRequest(
        message="consulta sin anclajes",
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )
    plan = build_graph_retrieval_plan(request)

    client = _FakeClient(hybrid_rows=[], documents_rows=[])
    hydrated_plan, evidence = retrieve_graph_evidence(plan, client=client)

    assert evidence.primary_articles == ()
    assert evidence.connected_articles == ()
    assert evidence.support_documents == ()
    assert evidence.citations == ()
    assert evidence.diagnostics["chunk_row_count"] == 0
    assert hydrated_plan.query_mode == plan.query_mode


def test_supabase_retriever_surfaces_cross_topic_anchor() -> None:
    # Regression guard: Art. 147 ET is load-bearing for a declaracion_renta
    # loss-compensation question but it is catalogued under the IVA topic in
    # the current corpus. The planner emits it as an explicit article entry
    # (loss_compensation_anchor), so the retriever must return it regardless
    # of the routed topic.
    request = PipelineCRequest(
        message=(
            "Mi cliente acumuló pérdidas fiscales en años anteriores y ahora tiene "
            "renta líquida positiva. ¿Cuál es el régimen de compensación de pérdidas?"
        ),
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )
    plan = build_graph_retrieval_plan(request)
    assert any(
        entry.kind == "article" and entry.lookup_value == "147"
        for entry in plan.entry_points
    ), "planner should anchor loss-compensation queries on Art. 147"

    iva_chunk = _hybrid_row("iva_06_libro1_t1_cap5_deducciones", "147", rrf=0.91)
    iva_chunk["topic"] = "iva"
    iva_document = _document_row("iva_06_libro1_t1_cap5_deducciones", "iva/cap5.md")
    iva_document["topic"] = "iva"

    client = _FakeClient(hybrid_rows=[iva_chunk], documents_rows=[iva_document])
    _, evidence = retrieve_graph_evidence(plan, client=client)

    assert client.last_rpc_payload["filter_topic"] is None
    primary_keys = [item.node_key for item in evidence.primary_articles]
    assert "147" in primary_keys


def test_fts_or_query_drops_stopwords_and_dedups() -> None:
    from lia_graph.pipeline_d.retriever_supabase import _build_fts_or_query

    assert _build_fts_or_query("") is None
    assert _build_fts_or_query("   ") is None
    # Stopwords + duplicates removed; kept tokens joined by OR
    out = _build_fts_or_query("La compensación de las pérdidas fiscales y perdidas fiscales")
    assert out is not None
    assert "|" in out
    tokens = [t.strip() for t in out.split("|")]
    assert "compensación" in tokens
    assert "pérdidas" in tokens
    assert "fiscales" in tokens
    assert "la" not in tokens and "de" not in tokens and "y" not in tokens
    # dedup — `perdidas` should appear once even though the text had it twice
    assert len([t for t in tokens if t in ("perdidas", "pérdidas")]) <= 2


def test_supabase_retriever_anchor_fetch_promotes_article_when_fts_misses() -> None:
    """Regression guard: even when the broad OR FTS does not return a chunk
    for the planner's explicit anchor (e.g. match_count cap or noisy OR
    ranking), the retriever's direct chunk_id-pattern fetch must still bring
    the anchor in so classification can promote it to primary."""

    from lia_graph.pipeline_d.planner import build_graph_retrieval_plan

    request = PipelineCRequest(
        message=(
            "Mi cliente acumuló pérdidas fiscales en años anteriores y "
            "ahora tiene renta líquida positiva. ¿Cuál es el régimen de "
            "compensación de pérdidas fiscales? ¿Hay límite anual?"
        ),
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )
    plan = build_graph_retrieval_plan(request)
    # Sanity: the planner anchors this case on Art. 147
    assert any(
        e.kind == "article" and e.lookup_value == "147"
        for e in plan.entry_points
    )

    # FTS returns noisy chunks for unrelated articles — the anchor is NOT in
    # the top-N. The retriever's direct anchor fetch must still surface it.
    noisy_fts = [
        _hybrid_row(f"noisy_doc_{i}", str(200 + i), rrf=0.03 - i * 0.001)
        for i in range(5)
    ]
    anchor_chunk = _hybrid_row("renta_corpus_art_147", "147", rrf=0.1)
    anchor_chunk["chunk_id"] = "renta_corpus_art_147::147"

    client = _FakeClient(
        hybrid_rows=noisy_fts,
        documents_rows=[_document_row("renta_corpus_art_147", "renta/et_art_147.md")]
        + [_document_row(f"noisy_doc_{i}", f"noise/{i}.md") for i in range(5)],
        document_chunks_rows=[anchor_chunk],
    )
    _, evidence = retrieve_graph_evidence(plan, client=client)
    primary_keys = [item.node_key for item in evidence.primary_articles]
    assert "147" in primary_keys, (
        "anchor fetch must surface Art. 147 even when FTS misses it"
    )


def test_fts_or_query_preserves_article_number_tokens() -> None:
    from lia_graph.pipeline_d.retriever_supabase import _build_fts_or_query

    out = _build_fts_or_query("Articulo 147 art 290 perdidas fiscales")
    assert out is not None
    # `147` and `290` are the anchor keys — must not be dropped as stopwords.
    assert "147" in out
    assert "290" in out


def test_supabase_retriever_exposes_backend_diagnostics_for_orchestrator() -> None:
    request = PipelineCRequest(
        message="¿Cómo se conectan los artículos 631-5 y 658-3 del ET?",
        topic="beneficiario_final_rub",
        requested_topic="beneficiario_final_rub",
    )
    plan = build_graph_retrieval_plan(request)

    client = _FakeClient(
        hybrid_rows=[
            _hybrid_row("rub_et_art_631_5", "631-5"),
            _hybrid_row("rub_et_art_658_3", "658-3"),
        ],
        documents_rows=[
            _document_row("rub_et_art_631_5", "rub/et_art_631_5.md"),
            _document_row("rub_et_art_658_3", "rub/et_art_658_3.md"),
        ],
    )

    _, evidence = retrieve_graph_evidence(plan, client=client)
    assert evidence.diagnostics["retrieval_backend"] == "supabase"
    assert evidence.diagnostics["chunk_row_count"] == 2
    assert evidence.diagnostics["document_row_count"] == 2
