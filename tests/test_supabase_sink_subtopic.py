"""Phase 4 tests — supabase_sink subtopic wire-up."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from lia_graph.ingestion.parser import ParsedArticle
from lia_graph.ingestion.supabase_sink import SupabaseCorpusSink


# Reuse the recording-client shape from test_ingestion_supabase_sink.
@dataclass
class _TableCall:
    table: str
    op: str
    payload: Any
    on_conflict: str | None = None


class _FakeExecute:
    def __init__(self) -> None:
        self.data: list[dict[str, Any]] = []


class _FakeQuery:
    def __init__(
        self,
        parent: "_FakeTable",
        op: str,
        payload: Any,
        on_conflict: str | None = None,
    ) -> None:
        self._parent = parent
        self._op = op
        self._payload = payload
        self._on_conflict = on_conflict

    def eq(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def neq(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def execute(self) -> _FakeExecute:
        self._parent.calls.append(
            _TableCall(
                table=self._parent.name,
                op=self._op,
                payload=self._payload,
                on_conflict=self._on_conflict,
            )
        )
        return _FakeExecute()


class _FakeTable:
    def __init__(self, name: str, calls: list[_TableCall]) -> None:
        self.name = name
        self.calls = calls

    def upsert(
        self, rows: Any, on_conflict: str | None = None
    ) -> _FakeQuery:
        payload = list(rows) if isinstance(rows, list) else [rows]
        return _FakeQuery(self, "upsert", payload, on_conflict=on_conflict)

    def update(self, payload: Any) -> _FakeQuery:
        return _FakeQuery(self, "update", payload)


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[_TableCall] = []

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(name, self.calls)


def _article(source_path: str, key: str = "1") -> ParsedArticle:
    return ParsedArticle(
        article_key=key,
        article_number=key,
        heading=f"Art {key}",
        body="cuerpo",
        full_text=f"# Art {key}\ncuerpo",
        status="vigente",
        source_path=source_path,
        paragraph_markers=(),
        reform_references=(),
        annotations=(),
    )


def _doc(
    rel: str,
    source: str,
    *,
    subtopic_key: str | None = None,
    requires_subtopic_review: bool = False,
    topic_key: str = "laboral",
) -> dict[str, Any]:
    return {
        "relative_path": rel,
        "source_path": source,
        "title_hint": rel,
        "markdown": "# doc\n",
        "family": "normativa",
        "knowledge_class": "normative_base",
        "source_type": "article_collection",
        "authority_level": "mintrabajo",
        "topic_key": topic_key,
        "subtopic_key": subtopic_key,
        "requires_subtopic_review": requires_subtopic_review,
        "document_archetype": "article_collection",
        "pais": "colombia",
    }


def _documents_rows(client: _FakeClient) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for call in client.calls:
        if call.table == "documents" and call.op == "upsert":
            rows.extend(call.payload)
    return rows


def _chunk_rows(client: _FakeClient) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for call in client.calls:
        if call.table == "document_chunks" and call.op == "upsert":
            rows.extend(call.payload)
    return rows


def test_write_documents_propagates_subtopic_key_to_subtema() -> None:
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_sub_1", client=client
    )
    sink.write_generation(documents=1, chunks=0)
    sink.write_documents([
        _doc(
            "laboral/nom.md",
            "/abs/laboral/nom.md",
            subtopic_key="parafiscales_icbf",
        ),
    ])
    [row] = _documents_rows(client)
    assert row["subtema"] == "parafiscales_icbf"


def test_write_documents_null_subtopic_leaves_subtema_null() -> None:
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_sub_2", client=client
    )
    sink.write_generation(documents=1, chunks=0)
    sink.write_documents([_doc("x.md", "/abs/x.md", subtopic_key=None)])
    [row] = _documents_rows(client)
    assert row["subtema"] is None


def test_write_chunks_inherits_parent_subtema() -> None:
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_sub_3", client=client
    )
    sink.write_generation(documents=1, chunks=2)
    doc_ids, _ = sink.write_documents([
        _doc(
            "laboral/n.md",
            "/abs/laboral/n.md",
            subtopic_key="parafiscales_icbf",
        ),
    ])
    sink.write_chunks(
        [
            _article("/abs/laboral/n.md", key="1"),
            _article("/abs/laboral/n.md", key="2"),
        ],
        doc_id_by_source_path=doc_ids,
    )
    chunks = _chunk_rows(client)
    assert len(chunks) == 2
    assert all(c["subtema"] == "parafiscales_icbf" for c in chunks)
    assert all(c["tema"] == "laboral" for c in chunks)


def test_write_chunks_null_when_doc_has_no_subtema() -> None:
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_sub_4", client=client
    )
    sink.write_generation(documents=1, chunks=1)
    doc_ids, _ = sink.write_documents([
        _doc("x.md", "/abs/x.md", subtopic_key=None),
    ])
    sink.write_chunks(
        [_article("/abs/x.md", key="1")],
        doc_id_by_source_path=doc_ids,
    )
    [chunk] = _chunk_rows(client)
    assert chunk["subtema"] is None


def test_write_documents_persists_requires_subtopic_review_flag() -> None:
    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_sub_5", client=client
    )
    sink.write_generation(documents=2, chunks=0)
    sink.write_documents([
        _doc(
            "x.md",
            "/abs/x.md",
            subtopic_key="parafiscales_icbf",
            requires_subtopic_review=False,
        ),
        _doc(
            "y.md",
            "/abs/y.md",
            subtopic_key=None,
            requires_subtopic_review=True,
        ),
    ])
    rows = _documents_rows(client)
    by_rel = {r["relative_path"]: r for r in rows}
    assert by_rel["x.md"]["requires_subtopic_review"] is False
    assert by_rel["y.md"]["requires_subtopic_review"] is True


def test_finalize_emits_subtopic_sunk_event(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[tuple[str, dict[str, Any]]] = []
    from lia_graph.ingestion import supabase_sink as sink_mod
    from lia_graph import instrumentation

    def _capture(event_type: str, payload: dict[str, Any], **kwargs: Any) -> None:
        captured.append((event_type, payload))

    monkeypatch.setattr(instrumentation, "emit_event", _capture)

    client = _FakeClient()
    sink = SupabaseCorpusSink(
        target="wip", generation_id="gen_sub_6", client=client
    )
    sink.write_generation(documents=2, chunks=0)
    sink.write_documents([
        _doc(
            "a.md",
            "/abs/a.md",
            subtopic_key="parafiscales_icbf",
            requires_subtopic_review=False,
        ),
        _doc(
            "b.md",
            "/abs/b.md",
            subtopic_key=None,
            requires_subtopic_review=True,
        ),
    ])
    sink.finalize(activate=False)
    names = [name for name, _ in captured]
    assert "subtopic.ingest.sunk" in names
    payload = dict(captured[names.index("subtopic.ingest.sunk")][1])
    assert payload["docs_with_subtopic"] == 1
    assert payload["docs_requiring_subtopic_review"] == 1
    assert payload["generation_id"] == "gen_sub_6"
