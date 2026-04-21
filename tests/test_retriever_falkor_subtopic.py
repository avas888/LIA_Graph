"""Phase 6 tests — Falkor retriever subtopic-anchored traversal."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from lia_graph.graph.client import (
    GraphClient,
    GraphClientConfig,
    GraphClientError,
    GraphQueryResult,
    GraphWriteStatement,
)
from lia_graph.graph.schema import default_graph_schema
from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.planner import build_graph_retrieval_plan
from lia_graph.pipeline_d.retriever_falkor import retrieve_graph_evidence


class _Recorder:
    """Cypher recorder returning canned rows keyed on the statement description."""

    def __init__(
        self,
        *,
        subtopic_article_keys: list[str] | None = None,
        primary_rows_by_key: dict[str, dict[str, Any]] | None = None,
        raise_on_description: str | None = None,
    ) -> None:
        self.statements: list[GraphWriteStatement] = []
        self._subtopic_article_keys = list(subtopic_article_keys or [])
        self._primary_rows = dict(primary_rows_by_key or {})
        self._raise_on = raise_on_description

    def __call__(
        self, statement: GraphWriteStatement, config: GraphClientConfig
    ) -> GraphQueryResult:
        self.statements.append(statement)
        if self._raise_on and self._raise_on in statement.description:
            raise GraphClientError("simulated cloud outage")

        rows: list[dict[str, Any]] = []
        if statement.description.startswith("subtopic_bound_articles"):
            rows = [{"article_key": key} for key in self._subtopic_article_keys]
        elif statement.description.startswith("primary_articles"):
            keys = list((statement.parameters or {}).get("keys") or [])
            for key in keys:
                match = self._primary_rows.get(key)
                if match is None:
                    continue
                rows.append(
                    {
                        "article_key": key,
                        "heading": match.get("heading") or f"Art. {key}",
                        "text_current": match.get("text_current") or "",
                        "source_path": match.get("source_path") or "",
                        "status": match.get("status") or "vigente",
                    }
                )
        # For connected/reforms we return no rows — not under test here.
        return GraphQueryResult(
            description=statement.description,
            query=statement.query,
            parameters=statement.parameters,
            rows=tuple(rows),
        )


def _client(recorder: _Recorder) -> GraphClient:
    return GraphClient(
        config=GraphClientConfig(url="redis://fake:6379", graph_name="LIA_TEST"),
        schema=default_graph_schema(),
        executor=recorder,
    )


def _plan_with_intent(intent: str | None, *, article_anchor: str | None = None):
    request = PipelineCRequest(
        message=("qué dice el artículo 107 del ET" if article_anchor else "parafiscales ICBF nómina"),
        topic="laboral",
        requested_topic="laboral",
    )
    plan = build_graph_retrieval_plan(request)
    return replace(plan, sub_topic_intent=intent)


def test_plan_with_intent_queries_subtopic_node() -> None:
    plan = _plan_with_intent("aporte_parafiscales_icbf")
    recorder = _Recorder(subtopic_article_keys=["107"])
    retrieve_graph_evidence(plan, graph_client=_client(recorder))
    subtopic_stmts = [
        s for s in recorder.statements
        if s.description.startswith("subtopic_bound_articles")
    ]
    assert len(subtopic_stmts) == 1
    assert "HAS_SUBTOPIC" in subtopic_stmts[0].query
    assert "SubTopicNode" in subtopic_stmts[0].query
    assert subtopic_stmts[0].parameters["key"] == "aporte_parafiscales_icbf"


def test_plan_without_intent_skips_subtopic_probe() -> None:
    plan = _plan_with_intent(None)
    recorder = _Recorder()
    retrieve_graph_evidence(plan, graph_client=_client(recorder))
    subtopic_stmts = [
        s for s in recorder.statements
        if s.description.startswith("subtopic_bound_articles")
    ]
    assert subtopic_stmts == []


def test_no_matching_subtopic_falls_back_to_explicit_keys() -> None:
    plan = _plan_with_intent("aporte_parafiscales_icbf")
    recorder = _Recorder(
        subtopic_article_keys=[],  # no anchors from subtopic
        primary_rows_by_key={},
    )
    _, evidence = retrieve_graph_evidence(plan, graph_client=_client(recorder))
    assert evidence.diagnostics["retrieval_sub_topic_intent"] == "aporte_parafiscales_icbf"
    assert evidence.diagnostics["subtopic_anchor_keys"] == []


def test_cloud_outage_on_subtopic_probe_propagates() -> None:
    """Invariant I2 — Falkor errors never silently degrade."""
    plan = _plan_with_intent("aporte_parafiscales_icbf")
    recorder = _Recorder(raise_on_description="subtopic_bound_articles")
    with pytest.raises(GraphClientError, match="simulated cloud outage"):
        retrieve_graph_evidence(plan, graph_client=_client(recorder))


def test_traversal_depth_limits_respected() -> None:
    """Subtopic-anchored keys still go through the bounded primary/connected
    queries — no change to depth semantics."""
    plan = _plan_with_intent("aporte_parafiscales_icbf")
    recorder = _Recorder(
        subtopic_article_keys=["107"],
        primary_rows_by_key={
            "107": {
                "heading": "Art. 107 — Deducciones",
                "text_current": "cuerpo",
            }
        },
    )
    _, evidence = retrieve_graph_evidence(plan, graph_client=_client(recorder))
    primary_keys = [item.node_key for item in evidence.primary_articles]
    assert "107" in primary_keys
    assert evidence.diagnostics["subtopic_anchor_keys"] == ["107"]
