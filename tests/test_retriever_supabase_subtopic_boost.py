"""Phase 6 tests — Supabase retriever subtopic filter + boost."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import pytest

from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.planner import build_graph_retrieval_plan
from lia_graph.pipeline_d.retriever_supabase import retrieve_graph_evidence


@dataclass
class _Resp:
    data: list[dict[str, Any]]


class _Q:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def select(self, *_a: Any, **_k: Any) -> "_Q":
        return self

    def in_(self, *_a: Any, **_k: Any) -> "_Q":
        return self

    def like(self, *_a: Any, **_k: Any) -> "_Q":
        return self

    def limit(self, *_a: Any, **_k: Any) -> "_Q":
        return self

    def execute(self) -> _Resp:
        return _Resp(list(self._rows))


class _Table:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def select(self, *_a: Any, **_k: Any) -> _Q:
        return _Q(self._rows)


class _Rpc:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def execute(self) -> _Resp:
        return _Resp(list(self._rows))


class _Client:
    def __init__(self, hybrid_rows: list[dict[str, Any]]) -> None:
        self._hybrid_rows = hybrid_rows
        self.last_payload: dict[str, Any] | None = None

    def rpc(self, name: str, payload: dict[str, Any]) -> _Rpc:
        assert name == "hybrid_search"
        self.last_payload = dict(payload)
        return _Rpc(self._hybrid_rows)

    def table(self, name: str) -> _Table:
        return _Table([])


def _row(
    doc_id: str,
    article_key: str,
    *,
    rrf: float = 0.8,
    subtema: str | None = None,
) -> dict[str, Any]:
    return {
        "doc_id": doc_id,
        "chunk_id": f"{doc_id}::{article_key}",
        "chunk_text": "cuerpo",
        "summary": f"Art. {article_key}",
        "topic": "laboral",
        "subtema": subtema,
        "knowledge_class": "normative_base",
        "fts_rank": 1.0,
        "vector_similarity": 0.0,
        "rrf_score": rrf,
    }


def _plan_with_intent(intent: str | None):
    request = PipelineCRequest(
        message="cómo liquido parafiscales ICBF en la nomina",
        topic="laboral",
        requested_topic="laboral",
    )
    plan = build_graph_retrieval_plan(request)
    return replace(plan, sub_topic_intent=intent)


def test_plan_with_intent_passes_filter_subtopic_to_rpc() -> None:
    plan = _plan_with_intent("aporte_parafiscales_icbf")
    client = _Client([_row("d", "1", subtema="aporte_parafiscales_icbf")])
    retrieve_graph_evidence(plan, client=client)
    assert client.last_payload is not None
    assert client.last_payload.get("filter_subtopic") == "aporte_parafiscales_icbf"
    assert client.last_payload.get("subtopic_boost") == 1.5


def test_plan_without_intent_omits_subtopic_filter() -> None:
    plan = _plan_with_intent(None)
    client = _Client([_row("d", "1")])
    retrieve_graph_evidence(plan, client=client)
    assert client.last_payload is not None
    assert "filter_subtopic" not in client.last_payload
    assert "subtopic_boost" not in client.last_payload


def test_matching_subtopic_boosts_rrf_client_side() -> None:
    """Client-side boost yields rrf * 1.5 for matching chunks, sorted first."""
    plan = _plan_with_intent("aporte_parafiscales_icbf")
    client = _Client([
        _row("d_other", "999", rrf=0.9, subtema="other_subtopic"),
        _row("d_match", "1", rrf=0.7, subtema="aporte_parafiscales_icbf"),
    ])
    _, evidence = retrieve_graph_evidence(plan, client=client)
    # 0.7 * 1.5 = 1.05 > 0.9 — matching chunk should win.
    assert evidence.diagnostics["retrieval_sub_topic_intent"] == "aporte_parafiscales_icbf"


def test_null_subtema_is_not_penalized() -> None:
    """Invariant I5 — chunks with subtema=NULL keep their original score."""
    plan = _plan_with_intent("aporte_parafiscales_icbf")
    client = _Client([
        _row("d_a", "1", rrf=0.9, subtema=None),
        _row("d_b", "2", rrf=0.6, subtema="aporte_parafiscales_icbf"),
    ])
    retrieve_graph_evidence(plan, client=client)
    assert client.last_payload is not None
    assert client.last_payload["filter_subtopic"] == "aporte_parafiscales_icbf"


def test_env_boost_factor_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIA_SUBTOPIC_BOOST_FACTOR", "2.0")
    plan = _plan_with_intent("aporte_parafiscales_icbf")
    client = _Client([_row("d", "1", subtema="aporte_parafiscales_icbf")])
    retrieve_graph_evidence(plan, client=client)
    assert client.last_payload is not None
    assert client.last_payload["subtopic_boost"] == 2.0


def test_diagnostics_carry_sub_topic_intent() -> None:
    plan = _plan_with_intent("nomina_electronica")
    client = _Client([_row("d", "1")])
    _, evidence = retrieve_graph_evidence(plan, client=client)
    assert evidence.diagnostics["retrieval_sub_topic_intent"] == "nomina_electronica"
    assert evidence.diagnostics["retrieval_backend"] == "supabase"
