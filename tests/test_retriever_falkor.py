"""Contract tests for the FalkorDB-backed graph retriever.

Uses a `GraphClient` with an injected executor so the tests never touch a
real FalkorDB socket. The executor gets the `GraphWriteStatement` and
returns a `GraphQueryResult` whose `rows` matches what the retriever
expects (same column names its Cypher would return from a live graph).
"""

from __future__ import annotations

from typing import Any

from lia_graph.graph.client import (
    GraphClient,
    GraphClientConfig,
    GraphQueryResult,
    GraphWriteStatement,
)
from lia_graph.graph.schema import default_graph_schema
from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.planner import build_graph_retrieval_plan
from lia_graph.pipeline_d.retriever_falkor import retrieve_graph_evidence


def _client_with_rows(
    *,
    primary_rows: list[dict[str, Any]],
    connected_rows: list[dict[str, Any]],
    reform_rows: list[dict[str, Any]],
) -> GraphClient:
    rows_by_description = {
        "primary_articles": primary_rows,
        "connected_articles": connected_rows,
        "reforms_explicit": reform_rows,
        "reforms_neighborhood": [],
    }

    def executor(statement: GraphWriteStatement, config: GraphClientConfig) -> GraphQueryResult:
        desc = statement.description
        if desc.startswith("primary_articles"):
            rows = rows_by_description["primary_articles"]
        elif desc.startswith("connected_articles"):
            rows = rows_by_description["connected_articles"]
        elif desc.startswith("related_reforms explicit"):
            rows = rows_by_description["reforms_explicit"]
        elif desc.startswith("related_reforms via article neighborhood"):
            rows = rows_by_description["reforms_neighborhood"]
        else:
            rows = []
        return GraphQueryResult(
            description=statement.description,
            query=statement.query,
            parameters=statement.parameters,
            rows=tuple(dict(row) for row in rows),
        )

    return GraphClient(
        config=GraphClientConfig(url="redis://fake:6379", graph_name="LIA_REGULATORY_GRAPH"),
        schema=default_graph_schema(),
        executor=executor,
    )


def test_falkor_retriever_returns_primary_and_connected_articles() -> None:
    request = PipelineCRequest(
        message=(
            "¿Qué exige el ET entre los artículos 771-2, 616-1 y 617 para soportar costos?"
        ),
        topic="facturacion_electronica",
        requested_topic="facturacion_electronica",
    )
    plan = build_graph_retrieval_plan(request)

    client = _client_with_rows(
        primary_rows=[
            {
                "article_key": "771-2",
                "heading": "Soporte de costos",
                "text_current": "Procedencia del costo y deduccion.",
                "source_path": "renta/et_art_771_2.md",
                "status": "vigente",
            },
            {
                "article_key": "616-1",
                "heading": "Factura electrónica",
                "text_current": "Emisión de la factura electrónica.",
                "source_path": "renta/et_art_616_1.md",
                "status": "vigente",
            },
            {
                "article_key": "617",
                "heading": "Requisitos de la factura",
                "text_current": "Requisitos formales de la factura.",
                "source_path": "renta/et_art_617.md",
                "status": "vigente",
            },
        ],
        connected_rows=[
            {
                "article_key": "743",
                "heading": "Idoneidad probatoria",
                "text_current": "Apreciación de la prueba en materia tributaria.",
                "source_path": "renta/et_art_743.md",
                "hop_distance": 1,
                "first_edge_kind": "REFERENCES",
            },
        ],
        reform_rows=[],
    )

    hydrated_plan, evidence = retrieve_graph_evidence(plan, graph_client=client)

    primary_keys = [item.node_key for item in evidence.primary_articles]
    assert "771-2" in primary_keys
    assert "616-1" in primary_keys
    assert "617" in primary_keys
    connected_keys = [item.node_key for item in evidence.connected_articles]
    assert "743" in connected_keys
    assert evidence.diagnostics["graph_backend"] == "falkor_live"
    assert evidence.diagnostics["graph_name"] == "LIA_REGULATORY_GRAPH"
    # Falkor layer does NOT produce support documents — that's the Supabase half.
    assert evidence.support_documents == ()
    assert evidence.citations == ()
    # Plan entries for explicit articles should now be marked resolved.
    resolved_explicit_keys = {
        entry.resolved_key
        for entry in hydrated_plan.entry_points
        if entry.kind == "article" and entry.resolved_key
    }
    assert "771-2" in resolved_explicit_keys


def test_falkor_retriever_surfaces_planner_reforms() -> None:
    request = PipelineCRequest(
        message="¿Qué decía el artículo 115 antes de la Ley 2277 de 2022?",
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )
    plan = build_graph_retrieval_plan(request)

    client = _client_with_rows(
        primary_rows=[
            {
                "article_key": "115",
                "heading": "Deducción de impuestos",
                "text_current": "Texto vigente del 115.",
                "source_path": "renta/et_art_115.md",
                "status": "vigente",
            },
        ],
        connected_rows=[],
        reform_rows=[
            {"reform_key": "LEY-2277-2022", "citation": "Ley 2277 de 2022"},
        ],
    )

    _, evidence = retrieve_graph_evidence(plan, graph_client=client)
    assert evidence.related_reforms
    assert evidence.related_reforms[0].node_key == "LEY-2277-2022"
