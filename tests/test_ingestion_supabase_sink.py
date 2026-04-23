"""Supabase corpus sink contract tests.

The sink only talks to Supabase over the supabase-py REST table API. These
tests inject a fake client that records every upsert/update call so we can
assert the contract without requiring a running local Supabase.

If you want to run these against a real local docker Supabase, point the
environment at it and replace `_FakeClient()` with
`create_supabase_client_for_target("production")` — the assertions are
contract-level, not row-level.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from lia_graph.graph.schema import EdgeKind, GraphEdgeRecord, NodeKind
from lia_graph.ingestion.classifier import ClassifiedEdge
from lia_graph.ingestion.parser import ParsedArticle
from lia_graph.ingestion.supabase_sink import (
    SupabaseCorpusSink,
    _RELATION_MAP,
    _derive_source_type,
)


# --- fake supabase-py client ------------------------------------------------


@dataclass
class _TableCall:
    table: str
    op: str
    payload: Any
    on_conflict: str | None = None
    filters: list[tuple[str, str, Any]] | None = None


class _FakeExecute:
    def __init__(self) -> None:
        self.data: list[dict[str, Any]] = []


class _FakeQuery:
    def __init__(self, parent: "_FakeTable", op: str, payload: Any, on_conflict: str | None = None) -> None:
        self._parent = parent
        self._op = op
        self._payload = payload
        self._on_conflict = on_conflict
        self._filters: list[tuple[str, str, Any]] = []

    def eq(self, column: str, value: Any) -> "_FakeQuery":
        self._filters.append(("eq", column, value))
        return self

    def neq(self, column: str, value: Any) -> "_FakeQuery":
        self._filters.append(("neq", column, value))
        return self

    def execute(self) -> _FakeExecute:
        self._parent.calls.append(
            _TableCall(
                table=self._parent.name,
                op=self._op,
                payload=self._payload,
                on_conflict=self._on_conflict,
                filters=list(self._filters),
            )
        )
        return _FakeExecute()


class _FakeTable:
    def __init__(self, name: str, calls: list[_TableCall]) -> None:
        self.name = name
        self.calls = calls

    def upsert(self, rows: Any, on_conflict: str | None = None) -> _FakeQuery:
        payload = list(rows) if isinstance(rows, list) else [rows]
        return _FakeQuery(self, "upsert", payload, on_conflict=on_conflict)

    def update(self, payload: Any) -> _FakeQuery:
        return _FakeQuery(self, "update", payload)


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[_TableCall] = []

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(name, self.calls)


# --- fixtures ---------------------------------------------------------------


def _article(key: str, heading: str, source_path: str, status: str = "vigente") -> ParsedArticle:
    return ParsedArticle(
        article_key=key,
        article_number=key,
        heading=heading,
        body=f"Body of article {key}",
        full_text=f"# Art. {key} - {heading}\nBody of article {key}",
        status=status,
        source_path=source_path,
        paragraph_markers=(),
        reform_references=("Ley 2277 de 2022",),
        annotations=(),
    )


def _doc(relative_path: str, source_path: str, family: str = "normativa") -> dict[str, Any]:
    return {
        "relative_path": relative_path,
        "source_path": source_path,
        "title_hint": relative_path,
        "markdown": f"# {relative_path}\nLorem ipsum.",
        "family": family,
        "knowledge_class": "normative_base",
        "source_type": "article_collection",
        "source_tier": "official_compilation",
        "authority_level": "dian",
        "topic_key": "declaracion_renta",
        "subtopic_key": None,
        "document_archetype": "article_collection",
        "pais": "colombia",
    }


def _edge(source: str, target: str, kind: EdgeKind, raw: str = "Ley 2277 de 2022") -> ClassifiedEdge:
    return ClassifiedEdge(
        record=GraphEdgeRecord(
            kind=kind,
            source_kind=NodeKind.ARTICLE,
            source_key=source,
            target_kind=NodeKind.ARTICLE if kind is EdgeKind.REFERENCES else NodeKind.REFORM,
            target_key=target,
            properties={"raw_reference": raw},
        ),
        confidence=0.9,
        rule="test_rule",
    )


# --- tests ------------------------------------------------------------------


def test_writes_generation_then_rows() -> None:
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="production",
        generation_id="gen_test_0001",
        client=client,
    )
    docs = [
        _doc("a/doc_one.md", "/abs/knowledge_base/a/doc_one.md"),
        _doc("a/doc_two.md", "/abs/knowledge_base/a/doc_two.md"),
    ]
    articles = [
        _article("1", "Objeto", "/abs/knowledge_base/a/doc_one.md"),
        _article("2", "Ambito", "/abs/knowledge_base/a/doc_two.md"),
    ]
    edges = [
        _edge("1", "2", EdgeKind.REFERENCES),
        _edge("1", "LEY-2277-2022", EdgeKind.MODIFIES),
        _edge("2", "LEY-2277-2022", EdgeKind.SUPERSEDES),
    ]

    sink.write_generation(documents=len(docs), chunks=len(articles), files=[d["relative_path"] for d in docs])
    doc_ids, written_docs = sink.write_documents(docs)
    written_chunks = sink.write_chunks(articles, doc_id_by_source_path=doc_ids)
    written_edges = sink.write_normative_edges(edges)
    result = sink.finalize(activate=True)

    assert written_docs == 2
    assert written_chunks == 2
    assert written_edges == 3
    assert result.generation_id == "gen_test_0001"
    assert result.activated is True
    assert len(doc_ids) == 2

    tables_touched = {call.table for call in client.calls if call.op == "upsert"}
    assert {"corpus_generations", "documents", "document_chunks", "normative_edges"} <= tables_touched

    # Activation flow must deactivate prior actives then activate this row.
    update_calls = [call for call in client.calls if call.op == "update"]
    assert len(update_calls) == 2
    deactivate, activate = update_calls
    assert deactivate.table == "corpus_generations"
    assert deactivate.payload.get("is_active") is False
    assert ("neq", "generation_id", "gen_test_0001") in (deactivate.filters or [])
    assert ("eq", "is_active", True) in (deactivate.filters or [])
    assert activate.table == "corpus_generations"
    assert activate.payload.get("is_active") is True
    assert ("eq", "generation_id", "gen_test_0001") in (activate.filters or [])


def test_rerun_is_idempotent_same_chunk_ids() -> None:
    docs = [_doc("a/doc_one.md", "/abs/a/doc_one.md")]
    articles = [_article("1", "Objeto", "/abs/a/doc_one.md")]

    chunk_ids_run_one: list[str] = []
    chunk_ids_run_two: list[str] = []

    for batch, capture in ((1, chunk_ids_run_one), (2, chunk_ids_run_two)):
        client = _FakeClient()
        sink = SupabaseCorpusSink(
            target="production",
            generation_id=f"gen_rerun_{batch}",
            client=client,
        )
        sink.write_generation(documents=len(docs), chunks=len(articles))
        doc_ids, _ = sink.write_documents(docs)
        sink.write_chunks(articles, doc_id_by_source_path=doc_ids)
        sink.finalize(activate=False)
        chunk_upserts = [call for call in client.calls if call.table == "document_chunks" and call.op == "upsert"]
        assert chunk_upserts and chunk_upserts[0].on_conflict == "chunk_id"
        for row in chunk_upserts[0].payload:
            capture.append(row["chunk_id"])

    # Same input -> same chunk_ids across runs (idempotency key stable).
    assert chunk_ids_run_one == chunk_ids_run_two


def test_relation_check_constraint_enforced_rejects_unknown_kind() -> None:
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="production",
        generation_id="gen_relation_check",
        client=client,
    )

    # Fabricate a ClassifiedEdge whose kind is not known to the sink.
    # We cannot construct an unknown EdgeKind directly (it is a closed Enum),
    # so we monkey-patch an allowed one into a not-mapped-and-not-dropped state
    # by clearing the map to force the assertion.
    original_map = dict(_RELATION_MAP)
    _RELATION_MAP.clear()
    try:
        with pytest.raises(AssertionError):
            sink.write_normative_edges([_edge("1", "2", EdgeKind.REFERENCES)])
    finally:
        _RELATION_MAP.clear()
        _RELATION_MAP.update(original_map)

    # Must NOT have reached Supabase.
    assert not [call for call in client.calls if call.table == "normative_edges"]


def test_edges_skip_graph_only_relations_without_assertion() -> None:
    """Gap #1 resolution: REQUIRES + COMPUTATION_DEPENDS_ON now map to
    `references`. DEFINES and PART_OF remain graph-only and are dropped.

    With source/target identical across every edge in the fixture, the
    references-mapped rows deduplicate to one, so the sink writes one row.
    """
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="production",
        generation_id="gen_skip_relations",
        client=client,
    )
    sink.write_generation(documents=1, chunks=1)
    edges = [
        _edge("1", "2", EdgeKind.REQUIRES),
        _edge("1", "2", EdgeKind.COMPUTATION_DEPENDS_ON),
        _edge("1", "2", EdgeKind.DEFINES),
        _edge("1", "2", EdgeKind.PART_OF),
        _edge("1", "2", EdgeKind.REFERENCES),
    ]
    written = sink.write_normative_edges(edges)

    assert written == 1  # three references-mapped edges dedupe; DEFINES+PART_OF drop
    result = sink.finalize(activate=False)
    assert result.edges_skipped_relation == 2  # DEFINES + PART_OF


def test_activate_uses_two_step_flow_so_partial_unique_holds() -> None:
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="production",
        generation_id="gen_activate",
        client=client,
    )
    sink.write_generation(documents=0, chunks=0)
    sink.finalize(activate=True)

    updates = [call for call in client.calls if call.op == "update"]
    assert len(updates) == 2, "finalize(activate=True) must run exactly two updates"
    deactivate, activate = updates
    # Deactivate must run first.
    assert client.calls.index(deactivate) < client.calls.index(activate)
    assert deactivate.payload.get("is_active") is False
    assert activate.payload.get("is_active") is True


def test_activate_requires_generation_row() -> None:
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="production",
        generation_id="gen_no_row",
        client=client,
    )
    with pytest.raises(RuntimeError):
        sink.finalize(activate=True)


def test_chunk_source_type_numeric_article_key() -> None:
    assert _derive_source_type("512-1", "512-1") == "article"
    assert _derive_source_type("147", "147") == "article"


def test_chunk_source_type_slug_section_key() -> None:
    assert _derive_source_type("identificacion", "") == "section"
    assert _derive_source_type("regla-operativa-para-lia", "") == "section"
    assert _derive_source_type("historico-de-cambios-1", "") == "section"


def test_chunk_source_type_whole_doc_key() -> None:
    assert _derive_source_type("doc", "") == "document"


def test_chunk_source_type_emitted_for_mixed_article_shapes() -> None:
    """End-to-end: a parsed-article mix should produce mixed source_type
    values in the sink upsert payload, not a hardcoded "article"."""
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="production",
        generation_id="gen_source_type_mix",
        client=client,
    )
    docs = [
        _doc("a/statutory.md", "/abs/a/statutory.md"),
        _doc("b/practica.md", "/abs/b/practica.md", family="practica"),
        _doc("c/leftover.md", "/abs/c/leftover.md", family="practica"),
    ]
    articles = [
        _article("512-1", "Hecho generador", "/abs/a/statutory.md"),
        ParsedArticle(
            article_key="identificacion",
            article_number="",
            heading="Identificacion",
            body="Body",
            full_text="## Identificacion\nBody",
            status="vigente",
            source_path="/abs/b/practica.md",
        ),
        ParsedArticle(
            article_key="doc",
            article_number="",
            heading="Documento completo",
            body="Body",
            full_text="Body",
            status="vigente",
            source_path="/abs/c/leftover.md",
        ),
    ]
    sink.write_generation(documents=len(docs), chunks=len(articles))
    doc_ids, _ = sink.write_documents(docs)
    sink.write_chunks(articles, doc_id_by_source_path=doc_ids)

    chunk_upserts = [
        call for call in client.calls if call.table == "document_chunks" and call.op == "upsert"
    ]
    assert chunk_upserts, "expected at least one document_chunks upsert"
    source_types = {row["source_type"] for call in chunk_upserts for row in call.payload}
    assert source_types == {"article", "section", "document"}


def test_writes_suin_relations() -> None:
    """Every SUIN-derived EdgeKind must map onto an allowed DB relation.

    Confirms Phase B mapping table: DEROGATES → derogates, REGLAMENTA →
    complements, SUSPENDS → suspends, ANULA → revokes,
    DECLARES_EXEQUIBLE → references, STRUCK_DOWN_BY → struck_down_by.
    """
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="production",
        generation_id="gen_suin_relations",
        client=client,
    )
    sink.write_generation(documents=0, chunks=0)
    edges = [
        _edge("135", "1607_139", EdgeKind.DEROGATES),
        _edge("135", "DECRETO-99-2019", EdgeKind.REGLAMENTA),
        _edge("135", "DECRETO-5-2020", EdgeKind.SUSPENDS),
        _edge("135", "SENTENCIA-C-1-2021", EdgeKind.ANULA),
        _edge("135", "SENTENCIA-C-2-2022", EdgeKind.DECLARES_EXEQUIBLE),
        _edge("135", "SENTENCIA-C-3-2022", EdgeKind.STRUCK_DOWN_BY),
    ]
    written = sink.write_normative_edges(edges)
    assert written == 6

    upserts = [
        call
        for call in client.calls
        if call.table == "normative_edges" and call.op == "upsert"
    ]
    relations = {row["relation"] for call in upserts for row in call.payload}
    assert relations == {
        "derogates",
        "complements",
        "suspends",
        "revokes",
        "references",
        "struck_down_by",
    }
