"""Tests for ``scripts/backfill_doc_fingerprint.py`` (Phase 1).

All cases run against an in-memory fake Supabase client; no network.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from lia_graph.ingestion.fingerprint import (
    classifier_output_from_document_row,
    compute_doc_fingerprint,
)


def _load_backfill_module() -> Any:
    """Import ``scripts/backfill_doc_fingerprint.py`` as a module."""
    spec_path = Path(__file__).resolve().parent.parent / "scripts" / "backfill_doc_fingerprint.py"
    spec = importlib.util.spec_from_file_location("backfill_doc_fingerprint", spec_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


backfill = _load_backfill_module()


# ---------------------------------------------------------------------------
# Fake Supabase client — mirrors the test pattern in
# tests/test_ingestion_supabase_sink.py.
# ---------------------------------------------------------------------------


@dataclass
class _Call:
    table: str
    op: str
    payload: Any
    on_conflict: str | None = None
    filters: list[tuple[str, str, Any]] | None = None


class _Execute:
    def __init__(self, data: list[dict[str, Any]] | None = None) -> None:
        self.data = data if data is not None else []


class _Query:
    def __init__(self, parent: "_Table", op: str, payload: Any = None, on_conflict: str | None = None) -> None:
        self._parent = parent
        self._op = op
        self._payload = payload
        self._on_conflict = on_conflict
        self._filters: list[tuple[str, str, Any]] = []
        self._order_col: str | None = None
        self._range: tuple[int, int] | None = None
        self._columns: str | None = None

    def select(self, columns: str) -> "_Query":
        self._columns = columns
        return self

    def eq(self, column: str, value: Any) -> "_Query":
        self._filters.append(("eq", column, value))
        return self

    def is_(self, column: str, value: Any) -> "_Query":
        self._filters.append(("is_", column, value))
        return self

    def order(self, column: str) -> "_Query":
        self._order_col = column
        return self

    def range(self, start: int, end: int) -> "_Query":
        self._range = (start, end)
        return self

    def execute(self) -> _Execute:
        self._parent.calls.append(
            _Call(
                table=self._parent.name,
                op=self._op,
                payload=self._payload,
                on_conflict=self._on_conflict,
                filters=list(self._filters),
            )
        )
        if self._op == "select":
            rows = self._parent.fetch_rows(self._filters, self._range)
            return _Execute(rows)
        if self._op == "upsert":
            self._parent.apply_upsert(self._payload, self._on_conflict)
            return _Execute([])
        if self._op == "update":
            self._parent.apply_update(self._payload, self._filters)
            return _Execute([])
        return _Execute([])


class _Table:
    def __init__(self, name: str, store: "_FakeStore") -> None:
        self.name = name
        self._store = store
        self.calls: list[_Call] = []

    def fetch_rows(
        self,
        filters: list[tuple[str, str, Any]],
        range_: tuple[int, int] | None,
    ) -> list[dict[str, Any]]:
        rows = list(self._store.rows.get(self.name, []))
        for op, column, value in filters:
            if op == "eq":
                rows = [r for r in rows if r.get(column) == value]
            elif op == "is_":
                if value == "null":
                    rows = [r for r in rows if r.get(column) is None]
                else:
                    rows = [r for r in rows if r.get(column) == value]
        rows.sort(key=lambda r: str(r.get("doc_id", "")))
        if range_ is not None:
            start, end = range_
            rows = rows[start : end + 1]
        return rows

    def apply_upsert(self, payload: Any, on_conflict: str | None) -> None:
        key = on_conflict or "doc_id"
        existing = self._store.rows.setdefault(self.name, [])
        for row in payload:
            match = next((r for r in existing if r.get(key) == row.get(key)), None)
            if match is None:
                existing.append(dict(row))
            else:
                match.update(row)

    def apply_update(self, payload: Any, filters: list[tuple[str, str, Any]]) -> None:
        existing = self._store.rows.setdefault(self.name, [])
        for row in existing:
            matches = True
            for op, column, value in filters:
                if op == "eq" and row.get(column) != value:
                    matches = False
                    break
                if op == "is_" and value == "null" and row.get(column) is not None:
                    matches = False
                    break
            if matches:
                row.update(payload)

    def select(self, columns: str) -> _Query:
        q = _Query(self, "select")
        q.select(columns)
        return q

    def upsert(self, rows: Any, on_conflict: str | None = None) -> _Query:
        payload = list(rows) if isinstance(rows, list) else [rows]
        return _Query(self, "upsert", payload, on_conflict=on_conflict)

    def update(self, payload: dict[str, Any]) -> _Query:
        return _Query(self, "update", dict(payload))


class _FakeStore:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict[str, Any]]] = {}


class _FakeClient:
    def __init__(self, seed: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self._store = _FakeStore()
        if seed:
            for name, rows in seed.items():
                self._store.rows[name] = [dict(r) for r in rows]
        self._tables: dict[str, _Table] = {}

    def table(self, name: str) -> _Table:
        if name not in self._tables:
            self._tables[name] = _Table(name, self._store)
        return self._tables[name]

    @property
    def documents(self) -> list[dict[str, Any]]:
        return self._store.rows.get("documents", [])


def _seed_doc(**overrides: Any) -> dict[str, Any]:
    row = {
        "doc_id": "doc_001",
        "sync_generation": "gen_2026",
        "content_hash": "hash_001",
        "topic": "iva",
        "tema": "iva",
        "subtema": "iva.regimen_responsable",
        "authority": "nacional",
        "tipo_de_documento": "ley",
        "source_type": "article_collection",
        "knowledge_class": "normative_base",
        "requires_subtopic_review": False,
        "doc_fingerprint": None,
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# (a) migration SQL parses clean — verified by the migration up step in
# Phase 1's Verification command. Represented here by a schema-contract
# sanity check: the backfill module imports + exposes its public surface.
def test_backfill_module_public_surface() -> None:
    for attr in ("run_backfill", "BackfillOptions", "BackfillResult", "main"):
        assert hasattr(backfill, attr), f"backfill module missing {attr}"


# (b) backfill against empty DB → no-op.
def test_backfill_noop_on_empty_db() -> None:
    client = _FakeClient(seed={"documents": []})
    options = backfill.BackfillOptions(
        target="test", dry_run=False, batch_size=10, limit=None, generation_id=None
    )
    result = backfill.run_backfill(options, client=client)
    assert result.rows_scanned == 0
    assert result.rows_written == 0


# (c) backfill against 3-doc seed → 3 fingerprints computed, deterministic.
def test_backfill_computes_three_fingerprints_deterministic() -> None:
    seed = [
        _seed_doc(doc_id="doc_001", content_hash="h1"),
        _seed_doc(doc_id="doc_002", content_hash="h2", subtema="iva.otros"),
        _seed_doc(doc_id="doc_003", content_hash="h3", authority="territorial"),
    ]
    client = _FakeClient(seed={"documents": [dict(r) for r in seed]})
    options = backfill.BackfillOptions(
        target="test", dry_run=False, batch_size=10, limit=None, generation_id=None
    )
    result = backfill.run_backfill(options, client=client)
    assert result.rows_scanned == 3
    assert result.rows_written == 3
    # Assert every row got the exact fingerprint the library computes.
    for row in client.documents:
        expected = compute_doc_fingerprint(
            content_hash=row["content_hash"],
            classifier_output=classifier_output_from_document_row(row),
        )
        assert row["doc_fingerprint"] == expected


# (d) backfill is idempotent (re-running changes nothing).
def test_backfill_is_idempotent() -> None:
    seed = [_seed_doc(doc_id="doc_001", content_hash="h1")]
    client = _FakeClient(seed={"documents": [dict(r) for r in seed]})
    options = backfill.BackfillOptions(
        target="test", dry_run=False, batch_size=10, limit=None, generation_id=None
    )
    backfill.run_backfill(options, client=client)
    # Second run: rows now have fingerprints, so the filter
    # "doc_fingerprint IS NULL" returns zero rows.
    result = backfill.run_backfill(options, client=client)
    assert result.rows_scanned == 0
    assert result.rows_written == 0


# (e) backfill --dry-run prints count without writing.
def test_backfill_dry_run_writes_nothing() -> None:
    seed = [
        _seed_doc(doc_id="doc_001", content_hash="h1"),
        _seed_doc(doc_id="doc_002", content_hash="h2"),
    ]
    client = _FakeClient(seed={"documents": [dict(r) for r in seed]})
    options = backfill.BackfillOptions(
        target="test", dry_run=True, batch_size=10, limit=None, generation_id=None
    )
    result = backfill.run_backfill(options, client=client)
    assert result.rows_scanned == 2
    assert result.rows_written == 0
    for row in client.documents:
        assert row["doc_fingerprint"] is None


# (f) fingerprint matches the sha256(content_hash || "|" || canonical_classifier_json)
#     contract per §0.8 using the Decision K1 backfill field mapping.
def test_backfill_fingerprint_matches_contract() -> None:
    seed = [_seed_doc(doc_id="doc_001", content_hash="h1")]
    client = _FakeClient(seed={"documents": [dict(r) for r in seed]})
    options = backfill.BackfillOptions(
        target="test", dry_run=False, batch_size=10, limit=None, generation_id=None
    )
    backfill.run_backfill(options, client=client)
    row = client.documents[0]
    expected = compute_doc_fingerprint(
        content_hash="h1",
        classifier_output=classifier_output_from_document_row(row),
    )
    assert row["doc_fingerprint"] == expected
    # Also assert the fingerprint starts with a 64-char hex string (sha256).
    assert len(row["doc_fingerprint"]) == 64
    assert all(c in "0123456789abcdef" for c in row["doc_fingerprint"])


# (g) reviewer-added: backfill-mapping fingerprint is byte-equal to the
# ingest-path fingerprint for a representative doc. Already covered in
# test_fingerprint.py, but we re-check through the script entry point to
# guard the backfill-script-level contract.
def test_backfill_path_matches_ingest_path_fingerprint() -> None:
    from lia_graph.ingestion.fingerprint import classifier_output_from_corpus_document

    live = {
        "topic_key": "iva",
        "subtopic_key": "iva.regimen_responsable",
        "requires_subtopic_review": False,
        "authority_level": "nacional",
        "document_archetype": "ley",
        "knowledge_class": "normative_base",
        "source_type": "article_collection",
        "source_tier": "official_compilation",  # dropped by K1
    }
    persisted = _seed_doc(content_hash="hconsistent")
    client = _FakeClient(seed={"documents": [dict(persisted)]})
    options = backfill.BackfillOptions(
        target="test", dry_run=False, batch_size=10, limit=None, generation_id=None
    )
    backfill.run_backfill(options, client=client)
    backfill_fp = client.documents[0]["doc_fingerprint"]
    ingest_fp = compute_doc_fingerprint(
        content_hash="hconsistent",
        classifier_output=classifier_output_from_corpus_document(live),
    )
    assert backfill_fp == ingest_fp


# Additional coverage — filter by generation_id.
def test_backfill_respects_generation_id_filter() -> None:
    seed = [
        _seed_doc(doc_id="doc_a", content_hash="hA", sync_generation="gen_old"),
        _seed_doc(doc_id="doc_b", content_hash="hB", sync_generation="gen_new"),
    ]
    client = _FakeClient(seed={"documents": [dict(r) for r in seed]})
    options = backfill.BackfillOptions(
        target="test",
        dry_run=False,
        batch_size=10,
        limit=None,
        generation_id="gen_new",
    )
    result = backfill.run_backfill(options, client=client)
    assert result.rows_scanned == 1
    assert result.rows_written == 1
    rows_by_id = {r["doc_id"]: r for r in client.documents}
    assert rows_by_id["doc_b"]["doc_fingerprint"] is not None
    assert rows_by_id["doc_a"]["doc_fingerprint"] is None
