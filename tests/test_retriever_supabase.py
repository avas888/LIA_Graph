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

    def select(self, _columns: str) -> "_FakeTableQuery":
        return self

    def in_(self, column: str, values: list[Any]) -> "_FakeTableQuery":
        self._filters.append(("in", column, list(values)))
        return self

    def execute(self) -> _FakeResponse:
        for op, column, value in self._filters:
            if op == "in":
                self._rows = [row for row in self._rows if row.get(column) in value]
        return _FakeResponse(data=list(self._rows))


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
    ) -> None:
        self._hybrid_rows = hybrid_rows
        self._documents_rows = documents_rows
        self.last_rpc_payload: dict[str, Any] | None = None

    def rpc(self, name: str, payload: dict[str, Any]) -> _FakeRpc:
        assert name == "hybrid_search"
        self.last_rpc_payload = dict(payload)
        return _FakeRpc(self._hybrid_rows)

    def table(self, name: str) -> _FakeTable:
        assert name == "documents"
        return _FakeTable(self._documents_rows)


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
