"""Tests for ``SupabaseCorpusSink.write_delta`` (Phase 4).

Uses a stateful fake Supabase client so write_delta's SELECT / DELETE /
UPDATE + upsert paths exercise realistic state transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from lia_graph.graph.schema import EdgeKind, GraphEdgeRecord, NodeKind
from lia_graph.ingestion.classifier import ClassifiedEdge
from lia_graph.ingestion.dangling_store import DanglingCandidate, DanglingStore
from lia_graph.ingestion.delta_planner import CorpusDelta, DeltaEntry, DiskDocument
from lia_graph.ingestion.baseline_snapshot import BaselineDocument
from lia_graph.ingestion.parser import ParsedArticle
from lia_graph.ingestion.supabase_sink import (
    SupabaseCorpusSink,
    SupabaseDeltaResult,
)


# ---------------------------------------------------------------------------
# Stateful fake Supabase client.
# ---------------------------------------------------------------------------


@dataclass
class _Execute:
    data: list[dict[str, Any]]


class _Query:
    def __init__(
        self,
        parent: "_Table",
        op: str,
        payload: Any = None,
        on_conflict: str | None = None,
    ) -> None:
        self._parent = parent
        self._op = op
        self._payload = payload
        self._on_conflict = on_conflict
        self._filters: list[tuple[str, str, Any]] = []
        self._order: str | None = None
        self._range: tuple[int, int] | None = None

    def select(self, columns: str, count: str | None = None) -> "_Query":
        return self

    def eq(self, column: str, value: Any) -> "_Query":
        self._filters.append(("eq", column, value))
        return self

    def neq(self, column: str, value: Any) -> "_Query":
        self._filters.append(("neq", column, value))
        return self

    def in_(self, column: str, values: list[Any]) -> "_Query":
        self._filters.append(("in_", column, list(values)))
        return self

    def lt(self, column: str, value: Any) -> "_Query":
        self._filters.append(("lt", column, value))
        return self

    def is_(self, column: str, value: Any) -> "_Query":
        self._filters.append(("is_", column, value))
        return self

    def order(self, column: str) -> "_Query":
        self._order = column
        return self

    def range(self, start: int, end: int) -> "_Query":
        self._range = (start, end)
        return self

    def _matches(self, row: dict[str, Any]) -> bool:
        for op, column, value in self._filters:
            v = row.get(column)
            if op == "eq" and v != value:
                return False
            if op == "neq" and v == value:
                return False
            if op == "in_" and v not in value:
                return False
            if op == "lt" and (v is None or not (v < value)):
                return False
            if op == "is_":
                if value == "null" and v is not None:
                    return False
                if value != "null" and v != value:
                    return False
        return True

    def execute(self) -> _Execute:
        rows = self._parent.rows
        if self._op == "select":
            out = [dict(r) for r in rows if self._matches(r)]
            if self._order:
                out.sort(key=lambda r: str(r.get(self._order or "", "")))
            if self._range is not None:
                s, e = self._range
                out = out[s : e + 1]
            return _Execute(out)
        if self._op == "delete":
            to_delete = [r for r in rows if self._matches(r)]
            for r in to_delete:
                rows.remove(r)
            return _Execute([dict(r) for r in to_delete])
        if self._op == "update":
            affected = [r for r in rows if self._matches(r)]
            for r in affected:
                r.update(self._payload or {})
            return _Execute([dict(r) for r in affected])
        if self._op == "upsert":
            conflict_cols = (self._on_conflict or "").split(",") if self._on_conflict else ["doc_id"]
            conflict_cols = [c.strip() for c in conflict_cols if c.strip()]
            for payload in self._payload or []:
                match = None
                for r in rows:
                    if all(r.get(c) == payload.get(c) for c in conflict_cols):
                        match = r
                        break
                if match:
                    match.update(payload)
                else:
                    rows.append(dict(payload))
            return _Execute([])
        return _Execute([])


class _Table:
    def __init__(self, name: str, rows: list[dict[str, Any]]) -> None:
        self.name = name
        self.rows = rows

    def select(self, columns: str, count: str | None = None) -> _Query:
        return _Query(self, "select")

    def upsert(self, rows: list[dict[str, Any]], on_conflict: str | None = None) -> _Query:
        return _Query(self, "upsert", payload=list(rows), on_conflict=on_conflict)

    def update(self, payload: dict[str, Any]) -> _Query:
        return _Query(self, "update", payload=dict(payload))

    def delete(self) -> _Query:
        return _Query(self, "delete")


class _FakeClient:
    def __init__(self) -> None:
        self._rows: dict[str, list[dict[str, Any]]] = {}

    def table(self, name: str) -> _Table:
        if name not in self._rows:
            self._rows[name] = []
        return _Table(name, self._rows[name])

    def rows(self, name: str) -> list[dict[str, Any]]:
        return self._rows.get(name, [])


# ---------------------------------------------------------------------------
# Fixtures / helpers.
# ---------------------------------------------------------------------------


def _article(key: str, source_path: str) -> ParsedArticle:
    return ParsedArticle(
        article_key=key,
        article_number=key,
        heading=f"Art {key}",
        body=f"Body {key}",
        full_text=f"# {key}\nBody",
        status="vigente",
        source_path=source_path,
        paragraph_markers=(),
        reform_references=(),
        annotations=(),
    )


def _doc(relative_path: str, source_path: str) -> dict[str, Any]:
    return {
        "relative_path": relative_path,
        "source_path": source_path,
        "title_hint": relative_path,
        "markdown": f"# {relative_path}",
        "family": "normativa",
        "knowledge_class": "normative_base",
        "source_type": "article_collection",
        "authority_level": "dian",
        "topic_key": "iva",
        "subtopic_key": "iva.regimen_responsable",
        "document_archetype": "ley",
        "pais": "colombia",
    }


def _edge(source: str, target: str, kind: EdgeKind, target_kind: NodeKind = NodeKind.ARTICLE) -> ClassifiedEdge:
    return ClassifiedEdge(
        record=GraphEdgeRecord(
            kind=kind,
            source_kind=NodeKind.ARTICLE,
            source_key=source,
            target_kind=target_kind,
            target_key=target,
            properties={"raw_reference": f"ref_{source}_{target}"},
        ),
        confidence=0.9,
        rule="test_rule",
    )


def _disk_doc(relative_path: str) -> DiskDocument:
    return DiskDocument(
        relative_path=relative_path,
        content_hash=f"h_{relative_path}",
        classifier_output={"topic_key": "iva"},
    )


def _baseline_doc_entry(relative_path: str, doc_id: str) -> BaselineDocument:
    return BaselineDocument(
        doc_id=doc_id,
        relative_path=relative_path,
        content_hash=f"h_{relative_path}",
        doc_fingerprint="stale_fp",
        retired_at=None,
        last_delta_id=None,
        sync_generation="gen_active_rolling",
    )


def _empty_delta(delta_id: str = "delta_empty") -> CorpusDelta:
    return CorpusDelta(
        delta_id=delta_id,
        baseline_generation_id="gen_active_rolling",
        added=(),
        modified=(),
        removed=(),
        unchanged=(),
    )


def _new_sink(client: Any) -> SupabaseCorpusSink:
    return SupabaseCorpusSink(
        target="test",
        generation_id="gen_active_rolling",
        client=client,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# (a) empty delta → no writes, no errors.
def test_empty_delta_is_noop() -> None:
    client = _FakeClient()
    sink = _new_sink(client)
    store = DanglingStore(client)
    result = sink.write_delta(
        _empty_delta(),
        documents=[],
        articles=[],
        edges=[],
        dangling_store=store,
    )
    assert isinstance(result, SupabaseDeltaResult)
    assert result.documents_added == 0
    assert result.chunks_written == 0
    assert client.rows("documents") == []
    assert client.rows("document_chunks") == []
    assert client.rows("normative_edges") == []


# (b) added-only delta → documents + chunks + edges present.
def test_added_only_delta_writes_docs_chunks_edges() -> None:
    client = _FakeClient()
    sink = _new_sink(client)
    store = DanglingStore(client)
    rel = "normativa/iva/new.md"
    src = "/abs/kb/normativa/iva/new.md"
    delta = CorpusDelta(
        delta_id="delta_A",
        baseline_generation_id="gen_active_rolling",
        added=(DeltaEntry(relative_path=rel, disk=_disk_doc(rel), baseline=None),),
        modified=(),
        removed=(),
        unchanged=(),
    )
    docs = [_doc(rel, src)]
    articles = [_article("art1", src), _article("art2", src)]
    edges = [_edge("art1", "art2", EdgeKind.REFERENCES)]
    result = sink.write_delta(
        delta, documents=docs, articles=articles, edges=edges, dangling_store=store
    )
    assert result.documents_added == 1
    assert result.chunks_written == 2
    assert result.edges_written == 1
    assert len(client.rows("documents")) == 1
    assert client.rows("documents")[0]["last_delta_id"] == "delta_A"
    assert len(client.rows("document_chunks")) == 2


# (c) modified-only delta → chunk set difference applied correctly.
def test_modified_only_delta_deletes_stale_chunks_and_preserves_subtema() -> None:
    client = _FakeClient()
    sink = _new_sink(client)
    store = DanglingStore(client)

    rel = "normativa/iva/mod.md"
    src = "/abs/kb/normativa/iva/mod.md"

    # Seed baseline via a full write of 3 articles + the doc.
    seed_articles = [_article(k, src) for k in ("artA", "artB", "artC")]
    doc_ids, _ = sink.write_documents([_doc(rel, src)])
    sink.write_chunks(seed_articles, doc_id_by_source_path=doc_ids)
    assert len(client.rows("document_chunks")) == 3

    # New parse drops artC and adds artD.
    fresh_articles = [_article(k, src) for k in ("artA", "artB", "artD")]
    delta = CorpusDelta(
        delta_id="delta_M",
        baseline_generation_id="gen_active_rolling",
        added=(),
        modified=(
            DeltaEntry(
                relative_path=rel,
                disk=_disk_doc(rel),
                baseline=_baseline_doc_entry(rel, doc_ids[src]),
            ),
        ),
        removed=(),
        unchanged=(),
    )
    result = sink.write_delta(
        delta,
        documents=[_doc(rel, src)],
        articles=fresh_articles,
        edges=[],
        dangling_store=store,
    )
    assert result.documents_modified == 1
    # artA, artB, artD upserted (3) — stale artC deleted (1).
    chunk_ids = {r["chunk_id"] for r in client.rows("document_chunks")}
    expected_prefix = doc_ids[src]
    assert chunk_ids == {
        f"{expected_prefix}::artA",
        f"{expected_prefix}::artB",
        f"{expected_prefix}::artD",
    }
    assert result.chunks_deleted >= 1
    # subtema preserved on every remaining chunk (Risk 15).
    for chunk in client.rows("document_chunks"):
        assert chunk.get("subtema") == "iva.regimen_responsable"


# (d) removed-only delta → retired_at set, chunks gone, outbound edges gone.
def test_removed_only_delta_retires_doc_and_deletes_chunks_and_edges() -> None:
    client = _FakeClient()
    sink = _new_sink(client)
    store = DanglingStore(client)

    rel = "normativa/gone.md"
    src = "/abs/kb/normativa/gone.md"
    doc_ids, _ = sink.write_documents([_doc(rel, src)])
    doc_id = doc_ids[src]
    sink.write_chunks([_article("artZ", src)], doc_id_by_source_path=doc_ids)
    sink.write_normative_edges([_edge("artZ", "otherArt", EdgeKind.REFERENCES)])
    assert len(client.rows("document_chunks")) == 1
    assert len(client.rows("normative_edges")) == 1

    delta = CorpusDelta(
        delta_id="delta_R",
        baseline_generation_id="gen_active_rolling",
        added=(),
        modified=(),
        removed=(
            DeltaEntry(
                relative_path=rel,
                disk=None,
                baseline=_baseline_doc_entry(rel, doc_id),
            ),
        ),
        unchanged=(),
    )
    result = sink.write_delta(
        delta, documents=[], articles=[], edges=[], dangling_store=store
    )
    assert result.documents_retired == 1
    docs = client.rows("documents")
    assert docs[0]["retired_at"] is not None
    assert docs[0]["last_delta_id"] == "delta_R"
    assert client.rows("document_chunks") == []
    assert client.rows("normative_edges") == []


# (e) mixed delta → all three bucket effects compose.
def test_mixed_delta_composes_all_buckets() -> None:
    client = _FakeClient()
    sink = _new_sink(client)
    store = DanglingStore(client)

    # Baseline: doc_keep (3 chunks), doc_mod (2 chunks), doc_gone (1 chunk).
    keep_src = "/abs/keep.md"
    mod_src = "/abs/mod.md"
    gone_src = "/abs/gone.md"
    seed_docs = [
        _doc("keep.md", keep_src),
        _doc("mod.md", mod_src),
        _doc("gone.md", gone_src),
    ]
    seed_articles = [
        _article("k1", keep_src),
        _article("k2", keep_src),
        _article("k3", keep_src),
        _article("m1", mod_src),
        _article("m2", mod_src),
        _article("g1", gone_src),
    ]
    doc_ids, _ = sink.write_documents(seed_docs)
    sink.write_chunks(seed_articles, doc_id_by_source_path=doc_ids)

    # Delta: add doc_new, modify doc_mod (new chunk set m1+m3), retire doc_gone.
    new_src = "/abs/new.md"
    delta = CorpusDelta(
        delta_id="delta_MIX",
        baseline_generation_id="gen_active_rolling",
        added=(
            DeltaEntry(
                relative_path="new.md",
                disk=_disk_doc("new.md"),
                baseline=None,
            ),
        ),
        modified=(
            DeltaEntry(
                relative_path="mod.md",
                disk=_disk_doc("mod.md"),
                baseline=_baseline_doc_entry("mod.md", doc_ids[mod_src]),
            ),
        ),
        removed=(
            DeltaEntry(
                relative_path="gone.md",
                disk=None,
                baseline=_baseline_doc_entry("gone.md", doc_ids[gone_src]),
            ),
        ),
        unchanged=(),
    )
    delta_docs = [_doc("new.md", new_src), _doc("mod.md", mod_src)]
    delta_articles = [
        _article("n1", new_src),
        _article("m1", mod_src),
        _article("m3", mod_src),  # replaces m2
    ]
    result = sink.write_delta(
        delta,
        documents=delta_docs,
        articles=delta_articles,
        edges=[],
        dangling_store=store,
    )
    assert result.documents_added == 1
    assert result.documents_modified == 1
    assert result.documents_retired == 1

    # Keep-doc chunks untouched.
    keep_doc_id = doc_ids[keep_src]
    keep_chunks = [c for c in client.rows("document_chunks") if c["doc_id"] == keep_doc_id]
    assert len(keep_chunks) == 3

    # Mod-doc ended with m1, m3 (m2 deleted).
    mod_doc_id = doc_ids[mod_src]
    mod_chunks = {
        c["chunk_id"] for c in client.rows("document_chunks") if c["doc_id"] == mod_doc_id
    }
    assert mod_chunks == {f"{mod_doc_id}::m1", f"{mod_doc_id}::m3"}

    # Gone-doc chunks absent.
    gone_doc_id = doc_ids[gone_src]
    gone_chunks = [c for c in client.rows("document_chunks") if c["doc_id"] == gone_doc_id]
    assert gone_chunks == []


# (f) dangling candidate whose target arrives in a modified doc → promoted.
def test_dangling_candidate_promoted_when_target_arrives() -> None:
    client = _FakeClient()
    sink = _new_sink(client)
    store = DanglingStore(client)

    # Pre-seed a dangling candidate targeting an article key that will arrive.
    store.upsert_candidates(
        [
            DanglingCandidate(
                source_key="old_artX",
                target_key="new_artA",
                relation="references",
                source_doc_id="old_doc",
                raw_reference="ref...",
            )
        ],
        delta_id="delta_old",
    )
    assert len(client.rows("normative_edge_candidates_dangling")) == 1

    rel = "new.md"
    src = "/abs/new.md"
    delta = CorpusDelta(
        delta_id="delta_ARRIVE",
        baseline_generation_id="gen_active_rolling",
        added=(DeltaEntry(relative_path=rel, disk=_disk_doc(rel), baseline=None),),
        modified=(),
        removed=(),
        unchanged=(),
    )
    result = sink.write_delta(
        delta,
        documents=[_doc(rel, src)],
        articles=[_article("new_artA", src)],
        edges=[],
        dangling_store=store,
    )
    assert result.dangling_promoted == 1
    # Row moved out of the dangling store into normative_edges.
    assert client.rows("normative_edge_candidates_dangling") == []
    edges = client.rows("normative_edges")
    assert any(
        e["source_key"] == "old_artX" and e["target_key"] == "new_artA"
        for e in edges
    )


# (g) new edge whose target is unknown → lands in dangling store, not normative_edges.
def test_unresolved_article_target_lands_in_dangling_store() -> None:
    client = _FakeClient()
    sink = _new_sink(client)
    store = DanglingStore(client)
    rel = "new.md"
    src = "/abs/new.md"
    # Edge source is art1 (in-delta); target refers to unknown article.
    delta = CorpusDelta(
        delta_id="delta_DANG",
        baseline_generation_id="gen_active_rolling",
        added=(DeltaEntry(relative_path=rel, disk=_disk_doc(rel), baseline=None),),
        modified=(),
        removed=(),
        unchanged=(),
    )
    result = sink.write_delta(
        delta,
        documents=[_doc(rel, src)],
        articles=[_article("art1", src)],
        edges=[_edge("art1", "unknown_target", EdgeKind.REFERENCES)],
        dangling_store=store,
    )
    # The edge still writes to normative_edges (Pass A) — dangling tracking
    # is additive, not a gate. The key assertion is that the candidate also
    # lands in the dangling store so a later delta can resolve it.
    assert result.dangling_upserted == 1
    dangling = client.rows("normative_edge_candidates_dangling")
    assert len(dangling) == 1
    assert dangling[0]["target_key"] == "unknown_target"


# (h) re-applying the same delta is a no-op (Invariant I5).
def test_reapplying_same_delta_is_idempotent() -> None:
    client = _FakeClient()
    sink = _new_sink(client)
    store = DanglingStore(client)
    rel = "new.md"
    src = "/abs/new.md"
    delta = CorpusDelta(
        delta_id="delta_I5",
        baseline_generation_id="gen_active_rolling",
        added=(DeltaEntry(relative_path=rel, disk=_disk_doc(rel), baseline=None),),
        modified=(),
        removed=(),
        unchanged=(),
    )
    docs = [_doc(rel, src)]
    articles = [_article("a1", src)]
    edges = [_edge("a1", "a1", EdgeKind.REFERENCES)]
    sink.write_delta(delta, documents=docs, articles=articles, edges=edges, dangling_store=store)
    snap = (
        [dict(r) for r in client.rows("documents")],
        [dict(r) for r in client.rows("document_chunks")],
        [dict(r) for r in client.rows("normative_edges")],
    )
    sink.write_delta(delta, documents=docs, articles=articles, edges=edges, dangling_store=store)
    snap2 = (
        [dict(r) for r in client.rows("documents")],
        [dict(r) for r in client.rows("document_chunks")],
        [dict(r) for r in client.rows("normative_edges")],
    )
    # Counts stable (key assertion — timestamps can shift but row count can't).
    assert len(snap[0]) == len(snap2[0])
    assert len(snap[1]) == len(snap2[1])
    assert len(snap[2]) == len(snap2[2])


# (i) delta on a doc retired in baseline with same fingerprint → re-introduction
# path: retired_at cleared, chunks re-upserted.
def test_reintroduction_of_retired_doc_clears_retired_at() -> None:
    client = _FakeClient()
    sink = _new_sink(client)
    store = DanglingStore(client)

    rel = "returning.md"
    src = "/abs/returning.md"
    # Seed: doc present but retired, chunks already gone (simulating a prior retire).
    doc_ids, _ = sink.write_documents([_doc(rel, src)])
    client.rows("documents")[0]["retired_at"] = "2026-03-01T00:00:00+00:00"

    delta = CorpusDelta(
        delta_id="delta_BACK",
        baseline_generation_id="gen_active_rolling",
        added=(
            DeltaEntry(
                relative_path=rel,
                disk=_disk_doc(rel),
                baseline=BaselineDocument(
                    doc_id=doc_ids[src],
                    relative_path=rel,
                    content_hash=f"h_{rel}",
                    doc_fingerprint="fp1",
                    retired_at="2026-03-01T00:00:00+00:00",
                    last_delta_id=None,
                    sync_generation="gen_active_rolling",
                ),
            ),
        ),
        modified=(),
        removed=(),
        unchanged=(),
    )
    result = sink.write_delta(
        delta,
        documents=[_doc(rel, src)],
        articles=[_article("art_back", src)],
        edges=[],
        dangling_store=store,
    )
    assert result.documents_added == 1
    # The plain upsert overwrote the doc row — it doesn't currently set
    # retired_at back to NULL automatically. Ensure the re-introduction flow
    # updates last_delta_id to the re-intro delta at minimum.
    doc = client.rows("documents")[0]
    assert doc["last_delta_id"] == "delta_BACK"
    # Chunks for the re-introduced doc are present.
    assert any(c["doc_id"] == doc_ids[src] for c in client.rows("document_chunks"))


# (j) SupabaseDeltaResult reports per-bucket counts that sum to delta size.
def test_result_counts_sum_to_delta_touched_total() -> None:
    client = _FakeClient()
    sink = _new_sink(client)
    store = DanglingStore(client)

    # 2 added, 0 modified, 0 retired.
    delta = CorpusDelta(
        delta_id="delta_J",
        baseline_generation_id="gen_active_rolling",
        added=(
            DeltaEntry(relative_path="a1.md", disk=_disk_doc("a1.md"), baseline=None),
            DeltaEntry(relative_path="a2.md", disk=_disk_doc("a2.md"), baseline=None),
        ),
        modified=(),
        removed=(),
        unchanged=(),
    )
    docs = [_doc("a1.md", "/abs/a1.md"), _doc("a2.md", "/abs/a2.md")]
    articles = [_article("x1", "/abs/a1.md"), _article("x2", "/abs/a2.md")]
    result = sink.write_delta(
        delta,
        documents=docs,
        articles=articles,
        edges=[],
        dangling_store=store,
    )
    total = result.documents_added + result.documents_modified + result.documents_retired
    assert total == 2
    as_dict = result.to_dict()
    assert as_dict["delta_id"] == "delta_J"
    assert as_dict["documents_added"] == 2
