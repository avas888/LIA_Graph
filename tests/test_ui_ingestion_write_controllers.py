"""Smoke tests for `lia_graph.ui_ingestion_write_controllers`.

The handler is 849 LOC of route dispatch against a live `ingestion_runtime`
— full per-route coverage lives closer to the ingestion runtime itself.
What this test file proves is:

  * the dispatcher returns False for non-matching URLs (keeps the
    write-controller chain composable)
  * lightweight input-validation paths that don't need the real runtime
    still produce the expected 400 responses (sanity for JSON parsing
    + field requirements)
  * the thin re-export on `ui_write_controllers` still points at the same
    function object (granularize-v2 migration guard)
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from lia_graph.ui_ingestion_write_controllers import (
    _find_doc,
    _topic_label,
    _type_label,
    handle_ingestion_post,
)


class _FakeHandler:
    """Minimal handler double that records `_send_json` calls."""

    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self._payload = payload
        self.sent: list[tuple[int, dict[str, Any]]] = []

    def _read_json_payload(self, **_kwargs: Any) -> dict[str, Any] | None:
        return self._payload

    def _send_json(
        self,
        status: int,
        body: dict[str, Any],
        **_kwargs: Any,
    ) -> None:
        self.sent.append((int(status), body))


class _StubIngestionRuntime:
    """Stub that records calls and returns deterministic values."""

    def __init__(self) -> None:
        self.registered: list[dict[str, Any]] = []

    def register_corpus(self, **kwargs: Any) -> dict[str, Any]:
        self.registered.append(kwargs)
        return {"key": "test-corpus", **kwargs}


def _deps_with_runtime(runtime: Any) -> dict[str, Any]:
    import re

    return {
        "ingestion_runtime": runtime,
        "ingestion_files_route_re": re.compile(r"^/api/ingestion/sessions/([^/]+)/files$"),
        "ingestion_process_route_re": re.compile(r"^/api/ingestion/sessions/([^/]+)/process$"),
        "ingestion_retry_route_re": re.compile(r"^/api/ingestion/sessions/([^/]+)/retry$"),
        "ingestion_validate_batch_route_re": re.compile(
            r"^/api/ingestion/sessions/([^/]+)/validate-batch$"
        ),
        "ingestion_delete_failed_route_re": re.compile(
            r"^/api/ingestion/sessions/([^/]+)/delete-failed$"
        ),
        "ingestion_stop_route_re": re.compile(r"^/api/ingestion/sessions/([^/]+)/stop$"),
        "ingestion_clear_batch_route_re": re.compile(
            r"^/api/ingestion/sessions/([^/]+)/clear-batch$"
        ),
    }


def test_returns_false_for_non_ingestion_path() -> None:
    handler = _FakeHandler()
    deps = _deps_with_runtime(_StubIngestionRuntime())
    assert handle_ingestion_post(handler, "/api/something-else", deps=deps) is False
    assert handler.sent == []


def test_corpora_post_rejects_missing_label() -> None:
    handler = _FakeHandler(payload={"label": ""})
    deps = _deps_with_runtime(_StubIngestionRuntime())
    assert handle_ingestion_post(handler, "/api/corpora", deps=deps) is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.BAD_REQUEST
    assert "label" in body["error"]


def test_corpora_post_happy_path_calls_runtime() -> None:
    runtime = _StubIngestionRuntime()
    handler = _FakeHandler(
        payload={
            "label": "Test",
            "slug": "test",
            "keywords_strong": ["alpha", "  beta  ", ""],
            "keywords_weak": "gamma",
        }
    )
    deps = _deps_with_runtime(runtime)
    assert handle_ingestion_post(handler, "/api/corpora", deps=deps) is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.CREATED
    assert body["ok"] is True
    # keywords normalized (whitespace trimmed, empties dropped)
    assert runtime.registered[0]["keywords_strong"] == ["alpha", "beta"]
    # scalar keyword coerced to list
    assert runtime.registered[0]["keywords_weak"] == ["gamma"]


def test_sessions_post_rejects_missing_corpus() -> None:
    handler = _FakeHandler(payload={"corpus": ""})
    deps = _deps_with_runtime(_StubIngestionRuntime())
    assert handle_ingestion_post(handler, "/api/ingestion/sessions", deps=deps) is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.BAD_REQUEST
    assert "corpus" in body["error"]


def test_preflight_post_rejects_empty_files() -> None:
    handler = _FakeHandler(payload={"files": []})
    deps = _deps_with_runtime(_StubIngestionRuntime())
    assert handle_ingestion_post(handler, "/api/ingestion/preflight", deps=deps) is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.BAD_REQUEST
    assert "files" in body["error"]


def test_type_and_topic_labels_fallback_to_key() -> None:
    assert _type_label("normative_base") == "Normativa"
    assert _type_label("unknown_key") == "unknown_key"
    assert _type_label(None) == "?"
    assert _topic_label("iva") == "IVA"
    assert _topic_label("laboral") == "Laboral"
    assert _topic_label(None) == "?"


def test_find_doc_matches_doc_id() -> None:
    docs = [{"doc_id": "a"}, {"doc_id": "b"}, {"doc_id": "c"}]
    assert _find_doc(docs, "b") == {"doc_id": "b"}
    assert _find_doc(docs, "missing") is None
    assert _find_doc([], "a") is None


def test_write_controllers_reexport_is_same_function() -> None:
    # granularize-v2 guard: the thin re-export on ui_write_controllers must
    # stay bound to the real implementation here, because ui_server.py
    # eagerly imports `handle_ingestion_post` from ui_write_controllers.
    from lia_graph.ui_write_controllers import handle_ingestion_post as via_reexp
    assert via_reexp is handle_ingestion_post
