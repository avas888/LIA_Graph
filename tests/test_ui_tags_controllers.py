"""Tests for the /api/tags/review admin endpoints (ingestionfix_v2 §4 Phase 7a).

The controllers only talk to Supabase through the supabase-py table API
and to the LLM via an adapter interface. Both are stubbed here so the
tests stay contract-level.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from http import HTTPStatus
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlparse

import pytest

from lia_graph.ui_tags_controllers import handle_tags_get, handle_tags_post


# --- fake supabase-py client -----------------------------------------------


@dataclass
class _Row(dict):
    """Concrete row used by the fake client; behaves like a dict."""


class _FakeExecute:
    def __init__(self, data: list[dict[str, Any]] | None = None) -> None:
        self.data = data or []


class _FakeQuery:
    def __init__(self, parent: "_FakeClient", table: str, op: str, payload: Any = None,
                 on_conflict: str | None = None) -> None:
        self._parent = parent
        self._table = table
        self._op = op
        self._payload = payload
        self._on_conflict = on_conflict
        self._filters: list[tuple[str, str, Any]] = []
        self._limit: int | None = None
        self._order: tuple[str, bool] | None = None

    def select(self, cols: str) -> "_FakeQuery":
        return self

    def eq(self, column: str, value: Any) -> "_FakeQuery":
        self._filters.append(("eq", column, value))
        return self

    def neq(self, column: str, value: Any) -> "_FakeQuery":
        self._filters.append(("neq", column, value))
        return self

    def is_(self, column: str, value: str) -> "_FakeQuery":
        self._filters.append(("is", column, value))
        return self

    def in_(self, column: str, values: list[Any]) -> "_FakeQuery":
        self._filters.append(("in", column, tuple(values)))
        return self

    def order(self, column: str, desc: bool = False) -> "_FakeQuery":
        self._order = (column, desc)
        return self

    def limit(self, n: int) -> "_FakeQuery":
        self._limit = n
        return self

    def execute(self) -> _FakeExecute:
        self._parent.calls.append(
            {
                "table": self._table,
                "op": self._op,
                "payload": self._payload,
                "on_conflict": self._on_conflict,
                "filters": list(self._filters),
                "limit": self._limit,
                "order": self._order,
            }
        )
        # Serve a canned response from the parent's fixture map.
        if self._op == "select":
            rows = list(self._parent.select_fixture.get(self._table, []))
            for ftype, col, val in self._filters:
                if ftype == "eq":
                    rows = [r for r in rows if r.get(col) == val]
                elif ftype == "neq":
                    rows = [r for r in rows if r.get(col) != val]
                elif ftype == "is" and val == "null":
                    rows = [r for r in rows if r.get(col) is None]
            if self._limit is not None:
                rows = rows[: self._limit]
            return _FakeExecute(data=rows)
        return _FakeExecute(data=[])


class _FakeTable:
    def __init__(self, client: "_FakeClient", name: str) -> None:
        self._client = client
        self._name = name

    def select(self, cols: str) -> _FakeQuery:
        return _FakeQuery(self._client, self._name, "select")

    def upsert(self, payload: Any, on_conflict: str | None = None) -> _FakeQuery:
        rows = payload if isinstance(payload, list) else [payload]
        return _FakeQuery(
            self._client, self._name, "upsert", payload=rows, on_conflict=on_conflict
        )

    def update(self, payload: Any) -> _FakeQuery:
        return _FakeQuery(self._client, self._name, "update", payload=payload)


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.select_fixture: dict[str, list[dict[str, Any]]] = {}

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(self, name)


# --- fake HTTP handler -----------------------------------------------------


class _FakeAuthContext:
    def __init__(self, role: str = "tenant_admin", email: str = "ava@lia.dev") -> None:
        self.role = role
        self.email = email
        self.user_id = email


class _FakeHandler:
    def __init__(self, *, body: dict[str, Any] | None = None,
                 role: str = "tenant_admin") -> None:
        encoded = json.dumps(body).encode("utf-8") if body is not None else b""
        self.rfile = io.BytesIO(encoded)
        self.headers = {"Content-Length": str(len(encoded))}
        self.wfile = io.BytesIO()
        self.status: int | None = None
        self.response_headers: dict[str, str] = {}
        self.auth_error: Any = None
        self._role = role

    # Interface used by the controllers ---------------------------------

    def _resolve_auth_context(self, *, required: bool = True) -> _FakeAuthContext:
        return _FakeAuthContext(role=self._role)

    def _send_auth_error(self, exc: Any) -> None:
        self.auth_error = exc
        self.status = getattr(exc, "http_status", 403)

    def _cors_headers(self) -> dict[str, str]:
        return {"Access-Control-Allow-Origin": "*"}

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, key: str, value: str) -> None:
        self.response_headers[key] = str(value)

    def end_headers(self) -> None:
        pass

    # Test helpers ------------------------------------------------------

    def response_body(self) -> dict[str, Any]:
        return json.loads(self.wfile.getvalue().decode("utf-8"))


# --- tests -----------------------------------------------------------------


def _make_deps(client: _FakeClient, **extra: Any) -> dict[str, Any]:
    deps = {"supabase_client": client, "supabase_target": "test"}
    deps.update(extra)
    return deps


def test_list_review_queue_filters_by_confidence():
    client = _FakeClient()
    client.select_fixture["document_tag_reviews"] = [
        {
            "review_id": "r1", "doc_id": "doc1", "trigger_reason": "low_confidence",
            "snapshot_topic": "iva", "snapshot_subtopic": None,
            "snapshot_confidence": 0.35, "decided_at": None, "created_at": "2026-04-23T10:00:00Z",
        },
        {
            "review_id": "r2", "doc_id": "doc2", "trigger_reason": "low_confidence",
            "snapshot_topic": "iva", "snapshot_subtopic": "iva_declaracion",
            "snapshot_confidence": 0.85, "decided_at": None, "created_at": "2026-04-23T10:01:00Z",
        },
    ]
    handler = _FakeHandler()
    parsed = urlparse("/api/tags/review?min_confidence=0.5")
    assert handle_tags_get(
        handler, parsed.path, parsed, deps=_make_deps(client),
    ) is True
    assert handler.status == HTTPStatus.OK
    body = handler.response_body()
    # Only the low-confidence row survives (<=0.5).
    assert body["count"] == 1
    assert body["reviews"][0]["review_id"] == "r1"


def test_list_review_queue_forbidden_for_non_admin():
    client = _FakeClient()
    handler = _FakeHandler(role="user")
    parsed = urlparse("/api/tags/review")
    handled = handle_tags_get(
        handler, parsed.path, parsed, deps=_make_deps(client),
    )
    assert handled is True
    assert handler.auth_error is not None


def test_get_doc_detail_includes_neighbors():
    client = _FakeClient()
    client.select_fixture["documents"] = [
        {"doc_id": "doc1", "relative_path": "iva/x.md", "topic": "iva",
         "first_heading": "X", "subtema": None},
        {"doc_id": "doc2", "relative_path": "iva/y.md", "topic": "iva",
         "first_heading": "Y"},
        {"doc_id": "doc3", "relative_path": "iva/z.md", "topic": "iva",
         "first_heading": "Z"},
    ]
    client.select_fixture["document_tag_reviews"] = [
        {"review_id": "r1", "doc_id": "doc1", "snapshot_topic": "iva",
         "snapshot_subtopic": None, "snapshot_confidence": 0.3,
         "decided_at": None, "created_at": "2026-04-23T10:00:00Z"},
    ]
    handler = _FakeHandler()
    parsed = urlparse("/api/tags/review/doc1")
    assert handle_tags_get(
        handler, parsed.path, parsed, deps=_make_deps(client),
    ) is True
    assert handler.status == HTTPStatus.OK
    body = handler.response_body()
    assert body["doc"]["doc_id"] == "doc1"
    assert body["review"]["review_id"] == "r1"
    # Neighbors should contain other docs with topic=iva, excluding doc1.
    assert "iva" in body["neighbors_by_tag"]
    neighbor_ids = {n["doc_id"] for n in body["neighbors_by_tag"]["iva"]}
    assert "doc1" not in neighbor_ids
    assert neighbor_ids <= {"doc2", "doc3"}


def test_post_report_updates_review_row_and_returns_markdown():
    client = _FakeClient()
    client.select_fixture["documents"] = [
        {"doc_id": "doc1", "relative_path": "iva/x.md", "topic": "iva",
         "first_heading": "Título de prueba", "subtema": None},
    ]
    client.select_fixture["document_tag_reviews"] = [
        {"review_id": "r1", "doc_id": "doc1", "snapshot_topic": "iva",
         "snapshot_subtopic": None, "snapshot_confidence": 0.3,
         "decided_at": None, "created_at": "2026-04-23T10:00:00Z"},
    ]
    client.select_fixture["document_chunks"] = [
        {"chunk_text": "Contenido mínimo para el brief."},
    ]
    handler = _FakeHandler(body={})
    assert handle_tags_post(
        handler, "/api/tags/review/doc1/report", deps=_make_deps(client),
    ) is True
    assert handler.status == HTTPStatus.OK
    body = handler.response_body()
    assert body["report_id"].startswith("rpt_")
    assert "## Documento" in body["markdown"]
    # Review row should have been updated with report fields.
    updates = [c for c in client.calls if c["table"] == "document_tag_reviews" and c["op"] == "update"]
    assert updates, "expected document_tag_reviews update call"
    update_payload = updates[0]["payload"]
    assert update_payload["report_id"] == body["report_id"]
    assert update_payload["report_markdown"] == body["markdown"]


def test_post_decision_approve_updates_documents_row_and_review():
    client = _FakeClient()
    client.select_fixture["document_tag_reviews"] = [
        {"review_id": "r1", "doc_id": "doc1", "snapshot_topic": "iva",
         "snapshot_subtopic": None, "snapshot_confidence": 0.3,
         "decided_at": None, "created_at": "2026-04-23T10:00:00Z"},
    ]
    handler = _FakeHandler(body={"action": "approve", "reason": "tag ok"})
    assert handle_tags_post(
        handler, "/api/tags/review/doc1/decision", deps=_make_deps(client),
    ) is True
    assert handler.status == HTTPStatus.OK

    # Review row marked decided.
    review_updates = [
        c for c in client.calls
        if c["table"] == "document_tag_reviews" and c["op"] == "update"
    ]
    assert review_updates
    assert review_updates[0]["payload"]["decision_action"] == "approve"
    assert review_updates[0]["payload"]["decided_by"] == "ava@lia.dev"

    # Documents row cleared requires_subtopic_review flag.
    doc_updates = [
        c for c in client.calls if c["table"] == "documents" and c["op"] == "update"
    ]
    assert doc_updates
    assert doc_updates[0]["payload"]["requires_subtopic_review"] is False


def test_post_decision_override_applies_new_topic_and_subtopic():
    client = _FakeClient()
    client.select_fixture["document_tag_reviews"] = [
        {"review_id": "r1", "doc_id": "doc1", "snapshot_topic": "iva",
         "snapshot_subtopic": None, "snapshot_confidence": 0.3,
         "decided_at": None, "created_at": "2026-04-23T10:00:00Z"},
    ]
    handler = _FakeHandler(body={
        "action": "override",
        "new_topic": "retencion_en_la_fuente",
        "new_subtopic": "retencion_decreto_572",
        "reason": "reclassification",
    })
    assert handle_tags_post(
        handler, "/api/tags/review/doc1/decision", deps=_make_deps(client),
    ) is True
    doc_updates = [
        c for c in client.calls if c["table"] == "documents" and c["op"] == "update"
    ]
    assert doc_updates
    payload = doc_updates[0]["payload"]
    assert payload["topic"] == "retencion_en_la_fuente"
    assert payload["tema"] == "retencion_en_la_fuente"
    assert payload["subtema"] == "retencion_decreto_572"


def test_post_decision_rejects_unknown_action():
    client = _FakeClient()
    client.select_fixture["document_tag_reviews"] = []
    handler = _FakeHandler(body={"action": "nonexistent"})
    assert handle_tags_post(
        handler, "/api/tags/review/doc1/decision", deps=_make_deps(client),
    ) is True
    assert handler.status == HTTPStatus.BAD_REQUEST


def test_post_report_404_when_no_open_review():
    client = _FakeClient()
    client.select_fixture["documents"] = [
        {"doc_id": "doc1", "relative_path": "iva/x.md", "topic": "iva",
         "first_heading": "T"},
    ]
    client.select_fixture["document_tag_reviews"] = []
    handler = _FakeHandler(body={})
    assert handle_tags_post(
        handler, "/api/tags/review/doc1/report", deps=_make_deps(client),
    ) is True
    assert handler.status == HTTPStatus.NOT_FOUND


def test_get_report_returns_persisted_markdown():
    client = _FakeClient()
    client.select_fixture["document_tag_reviews"] = [
        {
            "review_id": "r1", "doc_id": "doc1",
            "report_id": "rpt_abc", "report_markdown": "## Documento\ncontenido",
            "report_generated_at": "2026-04-23T11:00:00Z",
        },
    ]
    handler = _FakeHandler()
    parsed = urlparse("/api/tags/review/doc1/report/rpt_abc")
    assert handle_tags_get(
        handler, parsed.path, parsed, deps=_make_deps(client),
    ) is True
    assert handler.status == HTTPStatus.OK
    body = handler.response_body()
    assert body["report_id"] == "rpt_abc"
    assert "## Documento" in body["report_markdown"]
