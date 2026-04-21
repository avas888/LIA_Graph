"""Phase 8 tests — backfill_subtopic.py."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BACKFILL = _load_script(
    "backfill_subtopic",
    _SCRIPTS_DIR / "backfill_subtopic.py",
)


@dataclass
class _Resp:
    data: list[dict[str, Any]]
    count: int | None = None


class _Q:
    def __init__(
        self,
        rows: list[dict[str, Any]],
        *,
        updates: list[tuple[str, dict[str, Any], list[tuple[str, Any]]]] | None = None,
    ) -> None:
        self._rows = rows
        self._updates = updates
        self._payload: dict[str, Any] | None = None
        self._filters: list[tuple[str, Any]] = []
        self._limit: int | None = None

    def select(self, *_a: Any, **_k: Any) -> "_Q":
        return self

    def update(self, payload: dict[str, Any]) -> "_Q":
        self._payload = dict(payload)
        return self

    def eq(self, column: str, value: Any) -> "_Q":
        self._filters.append((column, value))
        return self

    def is_(self, column: str, value: Any) -> "_Q":
        self._filters.append((f"{column}:is", value))
        return self

    def or_(self, expression: str) -> "_Q":
        # Supabase-py style: "col.op.val,col.op.val"
        self._filters.append(("__or__", expression))
        return self

    def not_(self) -> "_Q":
        return self

    def gt(self, column: str, value: Any) -> "_Q":
        self._filters.append((f"{column}:gt", value))
        return self

    def order(self, *_a: Any, **_k: Any) -> "_Q":
        return self

    def limit(self, n: int) -> "_Q":
        self._limit = int(n)
        return self

    def execute(self) -> _Resp:
        if self._payload is not None and self._updates is not None:
            self._updates.append(
                (
                    "update",
                    self._payload,
                    list(self._filters),
                )
            )
        rows = list(self._rows)
        for column, value in self._filters:
            if column == "__or__":
                # Parse "col.op.val,col.op.val" — treat as OR predicate list
                clauses = [c.strip() for c in str(value).split(",") if c.strip()]
                predicates = []
                for clause in clauses:
                    parts = clause.split(".", 2)
                    if len(parts) != 3:
                        continue
                    col, op, raw = parts
                    if op == "eq":
                        def _pred(r, col=col, raw=raw):
                            target = r.get(col)
                            return str(target).lower() == str(raw).lower()
                    elif op == "is":
                        def _pred(r, col=col, raw=raw):
                            target = r.get(col)
                            if raw == "null":
                                return target is None
                            return target is True if raw == "true" else target is False
                    else:
                        continue
                    predicates.append(_pred)
                if predicates:
                    rows = [r for r in rows if any(p(r) for p in predicates)]
            elif column.endswith(":is"):
                target = column[:-3]
                rows = [r for r in rows if r.get(target) is value]
            elif column.endswith(":gt"):
                target = column[:-3]
                rows = [
                    r for r in rows
                    if r.get(target) is not None and r.get(target) > value
                ]
            else:
                rows = [r for r in rows if r.get(column) == value]
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Resp(data=rows, count=len(rows))


class _Client:
    def __init__(
        self,
        *,
        generations: list[dict[str, Any]],
        documents: list[dict[str, Any]],
        chunks: list[dict[str, Any]],
    ) -> None:
        self._generations = generations
        self._documents = documents
        self._chunks = chunks
        self.updates: list[tuple[str, dict[str, Any], list[tuple[str, Any]]]] = []

    def table(self, name: str) -> _Q:
        if name == "corpus_generations":
            return _Q(self._generations)
        if name == "documents":
            return _Q(self._documents, updates=self.updates)
        if name == "document_chunks":
            return _Q(self._chunks, updates=self.updates)
        raise AssertionError(f"unexpected table: {name}")


@dataclass
class _ClassResult:
    subtopic_key: str | None
    subtopic_label: str | None = None
    subtopic_confidence: float = 0.0
    requires_subtopic_review: bool = False


def _fake_classifier_factory(
    *, canned: dict[str, _ClassResult]
) -> Any:
    def _fn(*, filename: str, body_text: str) -> _ClassResult:
        return canned.get(filename, _ClassResult(subtopic_key=None))
    return _fn


def _opts(**overrides: Any) -> Any:
    defaults = dict(
        dry_run=True,
        limit=None,
        only_topic=None,
        rate_limit_rpm=0,
        generation_id="gen_x",
        resume_from=None,
        refresh_existing=False,
    )
    defaults.update(overrides)
    return BACKFILL.BackfillOptions(**defaults)


def test_backfill_dry_run_updates_no_rows() -> None:
    client = _Client(
        generations=[{"generation_id": "gen_x", "is_active": True}],
        documents=[
            {"doc_id": "d1", "topic": "laboral", "relative_path": "d1.md", "subtema": None, "sync_generation": "gen_x"},
            {"doc_id": "d2", "topic": "laboral", "relative_path": "d2.md", "subtema": None, "sync_generation": "gen_x"},
            {"doc_id": "d3", "topic": "laboral", "relative_path": "d3.md", "subtema": None, "sync_generation": "gen_x"},
        ],
        chunks=[
            {"doc_id": "d1", "chunk_id": "d1::1", "chunk_text": "cuerpo d1"},
            {"doc_id": "d2", "chunk_id": "d2::1", "chunk_text": "cuerpo d2"},
            {"doc_id": "d3", "chunk_id": "d3::1", "chunk_text": "cuerpo d3"},
        ],
    )
    classifier = _fake_classifier_factory(canned={
        "d1.md": _ClassResult(subtopic_key="parafiscales_icbf", subtopic_confidence=0.9),
        "d2.md": _ClassResult(subtopic_key="nomina_electronica", subtopic_confidence=0.88),
        "d3.md": _ClassResult(subtopic_key=None, requires_subtopic_review=True),
    })
    result = BACKFILL.run(_opts(dry_run=True), client=client, classifier=classifier)
    assert result.docs_processed == 3
    # Dry run: no update executions recorded.
    assert client.updates == []


def test_backfill_commit_writes_subtopic_key_and_chunks() -> None:
    client = _Client(
        generations=[{"generation_id": "gen_x", "is_active": True}],
        documents=[
            {"doc_id": "d1", "topic": "laboral", "relative_path": "d1.md", "subtema": None, "sync_generation": "gen_x"},
        ],
        chunks=[{"doc_id": "d1", "chunk_id": "d1::1", "chunk_text": "cuerpo"}],
    )
    classifier = _fake_classifier_factory(canned={
        "d1.md": _ClassResult(subtopic_key="parafiscales_icbf", subtopic_confidence=0.95),
    })
    BACKFILL.run(_opts(dry_run=False), client=client, classifier=classifier)
    payloads = [upd[1] for upd in client.updates]
    assert {"subtema": "parafiscales_icbf", "requires_subtopic_review": False} in payloads
    assert {"subtema": "parafiscales_icbf"} in payloads


def test_backfill_resume_from_skips_earlier_doc_ids() -> None:
    client = _Client(
        generations=[{"generation_id": "gen_x", "is_active": True}],
        documents=[
            {"doc_id": "d1", "topic": "laboral", "relative_path": "d1.md", "subtema": None, "sync_generation": "gen_x"},
            {"doc_id": "d2", "topic": "laboral", "relative_path": "d2.md", "subtema": None, "sync_generation": "gen_x"},
            {"doc_id": "d3", "topic": "laboral", "relative_path": "d3.md", "subtema": None, "sync_generation": "gen_x"},
        ],
        chunks=[],
    )
    classifier = _fake_classifier_factory(canned={})
    result = BACKFILL.run(
        _opts(resume_from="d1"), client=client, classifier=classifier
    )
    # d1 was filtered out by the gt filter.
    assert result.docs_processed == 2


def test_backfill_tolerates_per_doc_failure() -> None:
    client = _Client(
        generations=[{"generation_id": "gen_x", "is_active": True}],
        documents=[
            {"doc_id": "ok", "topic": "laboral", "relative_path": "ok.md", "subtema": None, "sync_generation": "gen_x"},
            {"doc_id": "bad", "topic": "laboral", "relative_path": "bad.md", "subtema": None, "sync_generation": "gen_x"},
        ],
        chunks=[],
    )

    def _classifier(*, filename: str, body_text: str) -> _ClassResult:
        if filename == "bad.md":
            raise RuntimeError("simulated classifier error")
        return _ClassResult(subtopic_key="nomina_electronica", subtopic_confidence=0.95)

    result = BACKFILL.run(_opts(dry_run=True), client=client, classifier=_classifier)
    assert result.docs_processed == 2
    assert result.docs_failed == 1


def test_backfill_rate_limit_is_honored(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(BACKFILL.time, "sleep", lambda s: sleeps.append(s))
    ticks = iter([0.0, 0.0, 10.0, 10.0])

    def _fake_monotonic() -> float:
        return next(ticks, 20.0)

    monkeypatch.setattr(BACKFILL.time, "monotonic", _fake_monotonic)

    # 60 rpm == 1 call per second. Second call arrives immediately → sleep(1.0).
    tick = None
    tick = BACKFILL._apply_rate_limit(60, tick)
    tick = BACKFILL._apply_rate_limit(60, tick)
    assert any(s >= 0.9 for s in sleeps), (
        f"expected a ~1.0s sleep for rpm=60; saw {sleeps!r}"
    )


def test_backfill_only_requires_review_narrows_filter() -> None:
    """Phase A7: ``--only-requires-review`` narrows the filter to docs
    flagged requires_subtopic_review=True during the live ingest pass."""
    client = _Client(
        generations=[{"generation_id": "gen_x", "is_active": True}],
        documents=[
            {
                "doc_id": "flagged",
                "topic": "laboral",
                "relative_path": "flagged.md",
                "subtema": "legacy",
                "requires_subtopic_review": True,
                "sync_generation": "gen_x",
            },
            {
                "doc_id": "clean",
                "topic": "laboral",
                "relative_path": "clean.md",
                "subtema": "already_classified",
                "requires_subtopic_review": False,
                "sync_generation": "gen_x",
            },
            {
                "doc_id": "null_subtema",
                "topic": "laboral",
                "relative_path": "null.md",
                "subtema": None,
                "requires_subtopic_review": False,
                "sync_generation": "gen_x",
            },
        ],
        chunks=[],
    )
    classifier = _fake_classifier_factory(canned={})
    result = BACKFILL.run(
        _opts(only_requires_review=True, refresh_existing=True),
        client=client,
        classifier=classifier,
    )
    # Only the flagged row should be processed
    assert result.docs_processed == 1


def test_backfill_emits_falkor_subtopic_node_and_edge_on_commit() -> None:
    """Phase A7: after the Supabase update, backfill merges SubTopicNode +
    HAS_SUBTOPIC into FalkorDB for each doc whose classifier verdict
    resolves in the curated taxonomy."""
    client = _Client(
        generations=[{"generation_id": "gen_x", "is_active": True}],
        documents=[
            {
                "doc_id": "d1",
                "topic": "laboral",
                "relative_path": "d1.md",
                "subtema": None,
                "requires_subtopic_review": False,
                "sync_generation": "gen_x",
            }
        ],
        chunks=[{"doc_id": "d1", "chunk_id": "d1::1", "chunk_text": "body"}],
    )
    classifier = _fake_classifier_factory(
        canned={
            "d1.md": _ClassResult(
                subtopic_key="aporte_parafiscales_icbf",
                subtopic_confidence=0.95,
            )
        }
    )
    # Inject a classifier result that also carries detected_topic.
    canned_with_topic = dict(
        d1=dict(
            subtopic_key="aporte_parafiscales_icbf",
            subtopic_label="Aporte Parafiscales ICBF",
            subtopic_confidence=0.95,
            requires_subtopic_review=False,
        )
    )

    @dataclass
    class _Verdict:
        subtopic_key: str | None
        subtopic_label: str | None
        subtopic_confidence: float
        requires_subtopic_review: bool
        detected_topic: str | None = "laboral"

    def _cls(*, filename: str, body_text: str) -> _Verdict:
        return _Verdict(**canned_with_topic["d1"])

    captured_statements: list[tuple[str, dict[str, Any]]] = []

    class _FakeResult:
        ok = True
        rows = ()
        diagnostics = {}

    class _FakeGraphClient:
        def execute(self, statement, strict=False):
            captured_statements.append(
                (statement.description, dict(statement.parameters))
            )
            return _FakeResult()

    BACKFILL.run(
        _opts(dry_run=False, emit_falkor=True, refresh_existing=True),
        client=client,
        classifier=_cls,
        graph_client=_FakeGraphClient(),
    )
    descriptions = [d for d, _ in captured_statements]
    assert "backfill.subtopic_node.merge" in descriptions
    assert "backfill.subtopic_edge.merge" in descriptions
    # Verify the node merge carried the curated sub_topic_key
    node_params = [p for d, p in captured_statements if d == "backfill.subtopic_node.merge"][0]
    assert node_params["sub_topic_key"] == "aporte_parafiscales_icbf"
    assert node_params["parent_topic"] == "laboral"


def test_backfill_emits_done_event(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        BACKFILL, "emit_event", lambda name, payload, **_k: captured.append((name, payload))
    )
    client = _Client(
        generations=[{"generation_id": "gen_x", "is_active": True}],
        documents=[
            {"doc_id": "d1", "topic": "laboral", "relative_path": "d1.md", "subtema": None, "sync_generation": "gen_x"},
        ],
        chunks=[],
    )
    classifier = _fake_classifier_factory(
        canned={"d1.md": _ClassResult(subtopic_key="nomina_electronica", subtopic_confidence=0.95)}
    )
    BACKFILL.run(_opts(dry_run=True), client=client, classifier=classifier)
    names = [name for name, _ in captured]
    assert "subtopic.backfill.start" in names
    assert "subtopic.backfill.doc.processed" in names
    assert "subtopic.backfill.done" in names
