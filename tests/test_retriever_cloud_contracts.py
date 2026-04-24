"""Contract tests for the cloud retrieval path — the invariants that MUST
hold in every environment for the served `answer_mode=graph_native` path.

These tests were added after a silent schema-drift incident where the Falkor
retriever queried ArticleNodes by a property (`article_key`) that no live
node actually carried. Every article lookup returned zero; the system fell
back to template answers for weeks. The old tests passed because they only
exercised the *output transformation* path (mock executor returning already-
shaped rows) — they never validated the *query shape* the retriever emits or
the *health contract* the orchestrator exposes when retrieval is empty.

The tests below encode the minimum contract:

1. Falkor Cypher MATCH predicates use property names the graph schema declares
   on `ArticleNode` — not arbitrary aliases.
2. Every empty-primary path produces an `empty_reason` in diagnostics so
   operators never see mystery silence.
3. A real-schema happy path with `article_number` works end-to-end.
4. The schema-drift detector fires with a specific reason code when the graph
   exposes the legacy `article_key` instead of the canonical `article_number`.
5. The orchestrator surfaces `retrieval_health` in its response diagnostics.
6. Supabase's unseeded-corpus case produces `empty_reason=corpus_not_seeded`
   so operators know the action is "run the sink", not "tune ranking".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lia_graph.graph.client import (
    GraphClient,
    GraphClientConfig,
    GraphQueryResult,
    GraphWriteStatement,
)
from lia_graph.graph.schema import NodeKind, default_graph_schema
from lia_graph.pipeline_c.contracts import PipelineCRequest
from lia_graph.pipeline_d.orchestrator import _build_retrieval_health, _compose_partial_coverage_notice
from lia_graph.pipeline_d.contracts import GraphEvidenceBundle
from lia_graph.pipeline_d.planner import build_graph_retrieval_plan
from lia_graph.pipeline_d.retriever_falkor import retrieve_graph_evidence as falkor_retrieve
from lia_graph.pipeline_d.retriever_supabase import retrieve_graph_evidence as supabase_retrieve


# --- helpers ----------------------------------------------------------------


class _CypherRecorder:
    """Captures every `GraphWriteStatement` passed through the executor so
    tests can assert on the actual Cypher the retriever emits."""

    def __init__(self, node_rows_by_property: dict[str, list[dict[str, Any]]]) -> None:
        self._node_rows_by_property = node_rows_by_property
        self.statements: list[GraphWriteStatement] = []

    def __call__(
        self, statement: GraphWriteStatement, config: GraphClientConfig
    ) -> GraphQueryResult:
        self.statements.append(statement)
        query = statement.query
        params = statement.parameters or {}
        rows: list[dict[str, Any]] = []

        # Diagnostic probe: total ArticleNode count
        if "RETURN count(n) AS total" in query and "ArticleNode" in query:
            total = sum(
                len(rows_for_prop)
                for rows_for_prop in self._node_rows_by_property.values()
            )
            rows = [{"total": total}]
        # Diagnostic probe: matches by article_number
        elif "MATCH (n:ArticleNode {article_number: key})" in query and "count(n) AS matches" in query:
            keys = set(params.get("keys") or [])
            matched = sum(
                1
                for row in self._node_rows_by_property.get("article_number", [])
                if row.get("article_number") in keys
            )
            rows = [{"matches": matched}]
        # Diagnostic probe: matches by legacy article_key
        elif "MATCH (n:ArticleNode {article_key: key})" in query and "count(n) AS matches" in query:
            keys = set(params.get("keys") or [])
            matched = sum(
                1
                for row in self._node_rows_by_property.get("article_key", [])
                if row.get("article_key") in keys
            )
            rows = [{"matches": matched}]
        # Primary fetch by article_number — the canonical happy path
        elif statement.description.startswith("primary_articles"):
            keys = list(params.get("keys") or [])
            matches = [
                row
                for row in self._node_rows_by_property.get("article_number", [])
                if row.get("article_number") in keys
            ]
            rows = [
                {
                    "article_key": m["article_number"],
                    "heading": m.get("heading") or f"Art. {m['article_number']}",
                    "text_current": m.get("text_current") or "",
                    "source_path": m.get("source_path") or "",
                    "status": m.get("status") or "vigente",
                }
                for m in matches
            ]
        # Connected / reforms: let the existing tests exercise those paths.
        return GraphQueryResult(
            description=statement.description,
            query=statement.query,
            parameters=statement.parameters,
            rows=tuple(rows),
        )


def _client(recorder: _CypherRecorder) -> GraphClient:
    return GraphClient(
        config=GraphClientConfig(
            url="redis://fake:6379", graph_name="LIA_REGULATORY_GRAPH"
        ),
        schema=default_graph_schema(),
        executor=recorder,
    )


def _plan_with_anchor_147() -> Any:
    # A loss-compensation question triggers the planner's `article=147` anchor
    # (source=`loss_compensation_anchor`) — this is the exact user flow that
    # hit the schema-drift bug.
    request = PipelineCRequest(
        message=(
            "Mi cliente acumuló pérdidas fiscales en años anteriores y ahora tiene "
            "renta líquida positiva. ¿Cuál es el régimen de compensación?"
        ),
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )
    plan = build_graph_retrieval_plan(request)
    anchor_keys = {
        entry.lookup_value
        for entry in plan.entry_points
        if entry.kind == "article"
    }
    assert "147" in anchor_keys, (
        "planner contract: a loss-compensation question MUST anchor on Art. 147"
    )
    return plan


# --- Contract 1: Cypher MATCH predicates agree with the graph schema --------


def test_falkor_primary_match_uses_schema_declared_property() -> None:
    """The property the retriever matches on MUST exist on ArticleNode per
    `graph/schema.py`. Using any other name creates a silent no-op against a
    live graph — which is exactly the bug this test is the guard for."""
    schema = default_graph_schema()
    article_node_type = schema.node_types[NodeKind.ARTICLE]
    allowed_properties = (
        set(article_node_type.required_fields)
        | set(getattr(article_node_type, "optional_fields", ()) or ())
        | {article_node_type.key_field}
    )

    plan = _plan_with_anchor_147()
    recorder = _CypherRecorder({"article_number": []})  # empty graph triggers probes
    falkor_retrieve(plan, graph_client=_client(recorder))

    primary_stmt = next(
        s for s in recorder.statements if s.description.startswith("primary_articles")
    )
    # Extract the property used inside `{property: key}` in MATCH clauses.
    # Accept any of the schema's declared properties. Reject anything else —
    # in particular `article_key`, which is a Python-internal alias that never
    # existed on the graph.
    import re

    property_matches = re.findall(
        r"MATCH \(\w+:ArticleNode \{(\w+):", primary_stmt.query
    )
    assert property_matches, "primary_articles MATCH must bind a node property"
    for prop in property_matches:
        assert prop in allowed_properties, (
            f"primary_articles Cypher binds `{prop}` which is not declared in "
            f"ArticleNode schema (allowed: {sorted(allowed_properties)}). "
            "This is the schema-drift smell that cost us weeks — fix the "
            "retriever or the schema before this lands."
        )


def test_falkor_connected_match_uses_schema_declared_property() -> None:
    schema = default_graph_schema()
    article_node_type = schema.node_types[NodeKind.ARTICLE]
    allowed_properties = (
        set(article_node_type.required_fields)
        | set(getattr(article_node_type, "optional_fields", ()) or ())
        | {article_node_type.key_field}
    )

    plan = _plan_with_anchor_147()
    recorder = _CypherRecorder({"article_number": []})
    falkor_retrieve(plan, graph_client=_client(recorder))

    connected_stmt = next(
        (s for s in recorder.statements if s.description.startswith("connected_articles")),
        None,
    )
    if connected_stmt is None:  # no-anchor plans skip this query — acceptable
        return
    import re

    property_matches = re.findall(
        r":ArticleNode \{(\w+):", connected_stmt.query
    )
    for prop in property_matches:
        assert prop in allowed_properties, (
            f"connected_articles binds `{prop}`, not declared in ArticleNode schema"
        )


# --- Contract 2: Every empty primary path emits a reason --------------------


def test_falkor_empty_reason_set_when_graph_is_empty() -> None:
    plan = _plan_with_anchor_147()
    recorder = _CypherRecorder({"article_number": []})
    _, evidence = falkor_retrieve(plan, graph_client=_client(recorder))
    assert evidence.primary_articles == ()
    assert evidence.diagnostics.get("empty_reason") == "graph_not_seeded"
    assert evidence.diagnostics.get("article_node_total") == 0


def test_falkor_empty_reason_fires_schema_drift_when_legacy_property_used() -> None:
    """If a future ingestion writes `article_key` (as the old buggy graph did),
    retrieval must *loudly* report drift — not silently return empty."""
    plan = _plan_with_anchor_147()
    # Graph has 1 node under the LEGACY property. Canonical lookup returns 0.
    recorder = _CypherRecorder(
        {"article_key": [{"article_key": "147"}], "article_number": []}
    )
    _, evidence = falkor_retrieve(plan, graph_client=_client(recorder))
    assert evidence.primary_articles == ()
    reason = evidence.diagnostics.get("empty_reason")
    assert reason == (
        "schema_drift:retriever_expects_article_number_but_data_uses_article_key"
    ), f"expected explicit schema_drift reason, got {reason!r}"
    # And the counters that let operators verify the claim
    assert evidence.diagnostics.get("article_node_matches_by_article_number") == 0
    assert evidence.diagnostics.get("article_node_matches_by_article_key") == 1


def test_falkor_empty_reason_when_plan_has_no_article_anchors() -> None:
    # A plan with no explicit article entries should classify distinctly.
    request = PipelineCRequest(
        message="consulta sin anclajes claros",
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )
    plan = build_graph_retrieval_plan(request)
    assert not any(e.kind == "article" for e in plan.entry_points), (
        "sanity: this message should not anchor on any explicit article"
    )
    recorder = _CypherRecorder({"article_number": [{"article_number": "99999"}]})
    _, evidence = falkor_retrieve(plan, graph_client=_client(recorder))
    assert evidence.primary_articles == ()
    assert (
        evidence.diagnostics.get("empty_reason")
        == "no_explicit_article_keys_in_plan"
    )


# --- Contract 3: Real-schema happy path end-to-end --------------------------


def test_falkor_primary_resolves_when_graph_has_article_number_147() -> None:
    """Regression guard for the exact bug: planner anchors on '147', the cloud
    graph has `(:ArticleNode {article_number: '147'})`, retriever must return
    it as a primary article. Before the fix, this failed for 1300 nodes."""
    plan = _plan_with_anchor_147()
    recorder = _CypherRecorder(
        {
            "article_number": [
                {
                    "article_number": "147",
                    "heading": "COMPENSACIÓN DE PÉRDIDAS FISCALES DE SOCIEDADES.",
                    "text_current": "Las sociedades podrán compensar...",
                    "source_path": "renta/et_art_147.md",
                    "status": "vigente",
                }
            ]
        }
    )
    _, evidence = falkor_retrieve(plan, graph_client=_client(recorder))
    assert [item.node_key for item in evidence.primary_articles] == ["147"]
    assert evidence.diagnostics["empty_reason"] == "ok"


# --- Contract 4: Supabase empty-corpus path classifies distinctly -----------


@dataclass
class _FakeCountResponse:
    data: list[dict[str, Any]]
    count: int | None


class _FakeSupaQuery:
    def __init__(self, rows: list[dict[str, Any]], count: int | None) -> None:
        self._rows = rows
        self._count = count

    def select(self, _cols: str, count: str | None = None) -> "_FakeSupaQuery":
        return self

    def limit(self, _n: int) -> "_FakeSupaQuery":
        return self

    def in_(self, _col: str, _vals: list[Any]) -> "_FakeSupaQuery":
        return self

    def execute(self) -> _FakeCountResponse:
        return _FakeCountResponse(data=list(self._rows), count=self._count)


class _FakeSupaTable:
    def __init__(self, rows: list[dict[str, Any]], count: int | None) -> None:
        self._rows = rows
        self._count = count

    def select(self, cols: str, count: str | None = None) -> _FakeSupaQuery:
        return _FakeSupaQuery(self._rows, self._count)


class _FakeSupaRpc:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def execute(self) -> _FakeCountResponse:
        return _FakeCountResponse(data=list(self._rows), count=None)


class _FakeSupaClient:
    def __init__(self, *, chunks_total: int) -> None:
        self._chunks_total = chunks_total

    def rpc(self, _name: str, _payload: dict[str, Any]) -> _FakeSupaRpc:
        return _FakeSupaRpc([])  # always empty to force diagnostic probe

    def table(self, name: str) -> _FakeSupaTable:
        if name == "document_chunks":
            return _FakeSupaTable([], self._chunks_total)
        return _FakeSupaTable([], None)


def test_supabase_empty_reason_is_corpus_not_seeded_when_chunks_total_zero() -> None:
    request = PipelineCRequest(
        message="compensacion perdidas fiscales",
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )
    plan = build_graph_retrieval_plan(request)
    client = _FakeSupaClient(chunks_total=0)
    _, evidence = supabase_retrieve(plan, client=client)
    assert evidence.diagnostics.get("empty_reason") == "corpus_not_seeded"
    assert evidence.diagnostics.get("document_chunks_total") == 0


def test_supabase_empty_reason_is_no_hits_when_corpus_has_chunks() -> None:
    request = PipelineCRequest(
        message="compensacion perdidas fiscales",
        topic="declaracion_renta",
        requested_topic="declaracion_renta",
    )
    plan = build_graph_retrieval_plan(request)
    client = _FakeSupaClient(chunks_total=120_000)
    _, evidence = supabase_retrieve(plan, client=client)
    assert evidence.diagnostics.get("empty_reason") == "no_lexical_or_vector_hits"
    assert evidence.diagnostics.get("document_chunks_total") == 120_000


# --- Contract 5: Orchestrator exposes retrieval_health ----------------------


def test_build_retrieval_health_carries_empty_reason_and_hint() -> None:
    evidence = GraphEvidenceBundle(
        primary_articles=(),
        connected_articles=(),
        related_reforms=(),
        support_documents=(),
        citations=(),
        diagnostics={
            "empty_reason": "graph_not_seeded",
            "article_node_total": 0,
            "graph_name": "LIA_REGULATORY_GRAPH",
        },
    )
    health = _build_retrieval_health(
        evidence=evidence,
        backend_diagnostics={
            "retrieval_backend": "supabase",
            "graph_backend": "falkor_live",
        },
    )
    assert health["empty_reason"] == "graph_not_seeded"
    assert "grafo normativo" in health["empty_reason_hint"]
    assert health["retrieval_backend"] == "supabase"
    assert health["graph_backend"] == "falkor_live"
    assert health["primary_article_count"] == 0


def test_build_retrieval_health_omits_hint_when_reason_is_ok() -> None:
    evidence = GraphEvidenceBundle(
        primary_articles=(),
        connected_articles=(),
        related_reforms=(),
        support_documents=(),
        citations=(),
        diagnostics={"empty_reason": "ok"},
    )
    health = _build_retrieval_health(
        evidence=evidence,
        backend_diagnostics={"retrieval_backend": "artifacts", "graph_backend": "artifacts"},
    )
    assert health["empty_reason"] == "ok"
    assert "empty_reason_hint" not in health


def test_build_retrieval_health_surfaces_per_half_reasons() -> None:
    # Merged-backends case: Falkor saved the answer but Supabase was unseeded.
    # Operators must still see the corpus_not_seeded signal so ingestion is
    # prioritized, not masked by the graph-half success.
    evidence = GraphEvidenceBundle(
        primary_articles=(),
        connected_articles=(),
        related_reforms=(),
        support_documents=(),
        citations=(),
        diagnostics={
            "empty_reason": "ok",
            "chunks_empty_reason": "corpus_not_seeded",
            "graph_empty_reason": "ok",
        },
    )
    health = _build_retrieval_health(
        evidence=evidence,
        backend_diagnostics={"retrieval_backend": "supabase", "graph_backend": "falkor_live"},
    )
    assert health["chunks_empty_reason"] == "corpus_not_seeded"
    assert health["graph_empty_reason"] == "ok"


def test_partial_coverage_notice_names_the_cause() -> None:
    # Operators and end-users should see the concrete reason, not a generic
    # "couldn't find anchors" line that forces them into the logs.
    health = {
        "empty_reason": "schema_drift:retriever_expects_article_number_but_data_uses_article_key",
        "empty_reason_hint": (
            "los nodos del grafo exponen 'article_key' pero el retriever "
            "consulta 'article_number' — desalineacion de esquema"
        ),
    }
    notice = _compose_partial_coverage_notice(health)
    assert "desalineacion de esquema" in notice
    assert "schema_drift" in notice


def test_partial_coverage_notice_falls_back_cleanly_when_reason_missing() -> None:
    notice = _compose_partial_coverage_notice({})
    assert "articulos ancla suficientes" in notice
    assert "Causa:" not in notice


# --- Contract 6: UI payload preserves retrieval_health for public users -----


def test_public_response_preserves_retrieval_health_when_present() -> None:
    """Production observability guarantee: end-users don't see debug
    diagnostics, but operators reading a failed turn's stored payload MUST be
    able to identify the cause (schema drift, unseeded corpus, planner miss)
    without re-running with debug flags."""
    from lia_graph.ui_chat_payload import filter_diagnostics_for_public_response

    result = filter_diagnostics_for_public_response(
        {
            "planner": {"sensitive": "hidden"},  # this must stay hidden
            "evidence_bundle": {"large": "hidden"},
            "retrieval_health": {
                "empty_reason": "schema_drift:retriever_expects_article_number_but_data_uses_article_key",
                "retrieval_backend": "supabase",
                "graph_backend": "falkor_live",
                "article_node_total": 1300,
            },
        }
    )
    assert result is not None
    assert "planner" not in result
    assert "evidence_bundle" not in result
    assert result["retrieval_health"]["empty_reason"].startswith("schema_drift")
    assert result["retrieval_health"]["article_node_total"] == 1300


def test_public_response_returns_none_when_no_retrieval_health() -> None:
    from lia_graph.ui_chat_payload import filter_diagnostics_for_public_response

    # Non-partial turn — nothing to surface publicly
    assert filter_diagnostics_for_public_response(
        {"planner": {"x": 1}, "evidence_bundle": {}}
    ) is None
    # Missing or malformed input
    assert filter_diagnostics_for_public_response(None) is None
    assert filter_diagnostics_for_public_response({}) is None
    assert filter_diagnostics_for_public_response({"retrieval_health": {}}) is None


def test_public_response_does_not_leak_orchestrator_internals() -> None:
    from lia_graph.ui_chat_payload import filter_diagnostics_for_public_response

    result = filter_diagnostics_for_public_response(
        {
            "planner": {"entry_points": [{"lookup_value": "147"}]},
            "evidence_bundle": {"primary_articles": [{"excerpt": "..."}]},
            "index_file": "/absolute/path/to/artifacts",
            "policy_path": "/absolute/path/to/policy",
            "retrieval_health": {
                "empty_reason": "ok",
                "primary_article_count": 3,
            },
        }
    )
    assert result is not None
    assert set(result.keys()) == {"retrieval_health"}
    # Defensive: the nested dict must be a copy — mutating it should not
    # reach the orchestrator's diagnostics upstream.
    result["retrieval_health"]["mutated"] = True
    fresh = filter_diagnostics_for_public_response(
        {
            "retrieval_health": {
                "empty_reason": "ok",
                "primary_article_count": 3,
            }
        }
    )
    assert "mutated" not in fresh["retrieval_health"]
