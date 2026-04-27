"""Tests for scripts/ingestion/verify_suin_merge.py.

Loads the script as a module via importlib, mocks a Supabase client, and
asserts the verification contract returns the right pass/fail branches.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_suin_merge.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("verify_suin_merge", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_scope(scope_dir: Path, *, manifest: dict[str, Any], docs: list[dict]) -> None:
    scope_dir.mkdir(parents=True, exist_ok=True)
    (scope_dir / "_harvest_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    with (scope_dir / "documents.jsonl").open("w", encoding="utf-8") as handle:
        for row in docs:
            handle.write(json.dumps(row) + "\n")
    (scope_dir / "edges.jsonl").write_text(
        json.dumps({"canonical_verb": "modifies"}) + "\n"
        + json.dumps({"canonical_verb": "derogates"}) + "\n",
        encoding="utf-8",
    )


class _FakeQuery:
    def __init__(self, count: int) -> None:
        self._count = count

    def select(self, *_a, **_kw):
        return self

    def eq(self, *_a, **_kw):
        return self

    def limit(self, *_a, **_kw):
        return self

    def execute(self):
        return MagicMock(count=self._count, data=[])


class _FakeClient:
    def __init__(self, *, doc_count: int, chunks: int, edges_by_relation: dict[str, int]) -> None:
        self._doc_count = doc_count
        self._chunks = chunks
        self._edges_by_relation = edges_by_relation

    def table(self, name: str):
        if name == "documents":
            return _FakeQuery(self._doc_count)
        if name == "document_chunks":
            return _FakeQuery(self._chunks)
        if name == "normative_edges":
            return _EdgeQuery(self._edges_by_relation)
        raise AssertionError(f"unexpected table {name}")


class _EdgeQuery:
    def __init__(self, counts: dict[str, int]) -> None:
        self._counts = counts
        self._relation: str | None = None

    def select(self, *_a, **_kw):
        return self

    def eq(self, field: str, value: str):
        if field == "relation":
            self._relation = value
        return self

    def limit(self, *_a, **_kw):
        return self

    def execute(self):
        if self._relation is None:
            return MagicMock(count=sum(self._counts.values()), data=[])
        return MagicMock(count=self._counts.get(self._relation, 0), data=[])


def test_verify_passes_on_complete_merge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    scope_dir = tmp_path / "laboral-tributario"
    _write_scope(
        scope_dir,
        manifest={
            "documents_parsed": 1,
            "articles_parsed": 2,
            "unknown_verb_failures": [],
        },
        docs=[{"doc_id": "1234"}],
    )
    client = _FakeClient(
        doc_count=1,
        chunks=2,
        edges_by_relation={rel: 1 for rel in module._DECLARED_RELATIONS},
    )
    monkeypatch.setattr(module, "_supabase_client", lambda _target: client)
    monkeypatch.setattr(module, "_falkor_node_count", lambda: 2700)

    report = module.verify(
        target="wip", generation="gen_test", scope_dirs=[scope_dir]
    )
    assert report["ok"] is True, report
    assert report["failures"] == []


def test_verify_fails_when_docs_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    scope_dir = tmp_path / "laboral"
    _write_scope(
        scope_dir,
        manifest={
            "documents_parsed": 1,
            "articles_parsed": 1,
            "unknown_verb_failures": [],
        },
        docs=[{"doc_id": "missing"}],
    )
    client = _FakeClient(doc_count=0, chunks=1, edges_by_relation={})
    monkeypatch.setattr(module, "_supabase_client", lambda _target: client)
    monkeypatch.setattr(module, "_falkor_node_count", lambda: None)

    report = module.verify(
        target="wip", generation="gen_test", scope_dirs=[scope_dir]
    )
    assert report["ok"] is False
    assert any("missing" in f.lower() for f in report["failures"])


def test_verify_fails_on_unknown_verb_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    scope_dir = tmp_path / "tributario"
    _write_scope(
        scope_dir,
        manifest={
            "documents_parsed": 1,
            "articles_parsed": 1,
            "unknown_verb_failures": [{"url": "x", "raw_verb": "modificadisimo"}],
        },
        docs=[{"doc_id": "4242"}],
    )
    client = _FakeClient(
        doc_count=1,
        chunks=5,
        edges_by_relation={rel: 1 for rel in module._DECLARED_RELATIONS},
    )
    monkeypatch.setattr(module, "_supabase_client", lambda _target: client)
    monkeypatch.setattr(module, "_falkor_node_count", lambda: None)

    report = module.verify(
        target="wip", generation="gen_test", scope_dirs=[scope_dir]
    )
    assert report["ok"] is False
    assert any("unknown_verb" in f for f in report["failures"])


def test_verify_fails_when_zero_chunks_landed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    scope_dir = tmp_path / "jurisprudencia"
    _write_scope(
        scope_dir,
        manifest={
            "documents_parsed": 1,
            "articles_parsed": 50,
            "unknown_verb_failures": [],
        },
        docs=[{"doc_id": "9001"}],
    )
    # zero chunks landed — sink never ran or failed mid-run
    client = _FakeClient(
        doc_count=1,
        chunks=0,
        edges_by_relation={rel: 1 for rel in module._DECLARED_RELATIONS},
    )
    monkeypatch.setattr(module, "_supabase_client", lambda _target: client)
    monkeypatch.setattr(module, "_falkor_node_count", lambda: None)

    report = module.verify(
        target="wip", generation="gen_test", scope_dirs=[scope_dir]
    )
    assert report["ok"] is False
    assert any("zero chunks" in f for f in report["failures"])
