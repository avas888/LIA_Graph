"""Unit tests for `lia_graph.ui_chat_clarification`.

The clarification flow is the gate that stops the `/api/chat` request
from reaching the pipeline when a guided clarification session is
active. Tests here lock in the directive dispatch
(`pass_through` / `limit_reached` / `ask` / `run_pipeline`) and the
early-return contract the controller depends on.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from lia_graph.ui_chat_clarification import apply_api_chat_clarification


class _FakeHandler:
    def __init__(self) -> None:
        self.sent: list[tuple[int, dict[str, Any]]] = []

    def _send_json(self, status: int | HTTPStatus, body: dict[str, Any], **_kw: Any) -> None:
        self.sent.append((int(status), body))


class _FakeChatRunCoordinator:
    def __init__(self) -> None:
        self.failed: list[tuple[str, dict[str, Any]]] = []
        self.marked_sent: list[str] = []

    def fail(self, run_id: str, payload: dict[str, Any], *, base_dir: Any) -> None:
        del base_dir
        self.failed.append((run_id, payload))

    def mark_response_sent(self, run_id: str, *, base_dir: Any) -> None:
        del base_dir
        self.marked_sent.append(run_id)


def _base_request_context() -> dict[str, Any]:
    return {
        "trace_id": "trace-1",
        "chat_run_id": "run-1",
        "session_id": "sess-1",
        "clarification_session_id": "sess-1",
        "message": "¿Cuál tarifa aplica?",
        "response_route": "decision",
        "normalized_pais": "colombia",
        "primary_scope_mode": "current",
        "pipeline_response_route": "decision",
    }


def _deps_base(
    *,
    clarification_state: Any,
    directive: dict[str, Any],
    intercept: bool = True,
) -> dict[str, Any]:
    return {
        "get_clarification_session_state": lambda **_kw: clarification_state,
        "clarification_sessions_path": "/tmp/clarif",
        "should_intercept_clarification_state": lambda state, **_kw: intercept,
        "advance_clarification_state": lambda state, **_kw: ({**state}, directive),
        "llm_dynamic_clarification_decider": lambda **_kw: {"next_question": "fallback"},
        "clear_clarification_session_state": lambda **_kw: None,
        "build_public_api_error": lambda **kw: {"code": kw["code"], "msg": kw["message"]},
        "build_clarification_interaction_payload": lambda **kw: {"interaction": kw.get("question", "")},
        "build_clarification_error_payload": lambda **kw: {
            "public_error": kw["public_error"],
            "user_message": kw["user_message"],
            "interaction": kw["interaction"],
            "session_id": kw["session_id"],
        },
        "build_user_message_for_question": lambda **kw: kw["question"],
        "upsert_clarification_session_state": lambda session_id, state, **_kw: {**state, "upserted": True},
        "resolve_guided_clarification_requirements": lambda **_kw: [],
        "persist_assistant_turn_path": "/tmp/persist",
        "chat_run_coordinator": _FakeChatRunCoordinator(),
        "chat_runs_path": "/tmp/runs",
        "persist_user_turn_path": "/tmp/user",
    }


def test_returns_false_when_no_clarification_state() -> None:
    handler = _FakeHandler()
    ctx = _base_request_context()
    deps = _deps_base(clarification_state=None, directive={})
    # persistence functions shouldn't run when we fall through — provide no-ops.
    deps["persist_user_turn"] = lambda **_kw: None
    deps["persist_assistant_turn"] = lambda **_kw: None

    handled = apply_api_chat_clarification(
        handler, request_context=ctx, t_api_chat=0.0, deps=deps,
    )
    assert handled is False
    assert handler.sent == []


def test_returns_false_when_not_decision_route() -> None:
    handler = _FakeHandler()
    ctx = _base_request_context()
    ctx["response_route"] = "analysis"
    deps = _deps_base(clarification_state={"route": "decision"}, directive={})

    handled = apply_api_chat_clarification(
        handler, request_context=ctx, t_api_chat=0.0, deps=deps,
    )
    assert handled is False
    assert ctx["pipeline_response_route"] == "analysis"


def test_pass_through_directive_falls_through_without_sending() -> None:
    handler = _FakeHandler()
    ctx = _base_request_context()
    deps = _deps_base(
        clarification_state={"route": "decision", "turn_count": 0},
        directive={"type": "pass_through"},
    )

    handled = apply_api_chat_clarification(
        handler, request_context=ctx, t_api_chat=0.0, deps=deps,
    )
    assert handled is False
    assert handler.sent == []
    # state should be updated to the advanced state
    assert ctx["clarification_state"] == {"route": "decision", "turn_count": 0}


def test_run_pipeline_directive_updates_context_and_falls_through() -> None:
    handler = _FakeHandler()
    ctx = _base_request_context()
    deps = _deps_base(
        clarification_state={"route": "decision", "turn_count": 1},
        directive={
            "type": "run_pipeline",
            "message": "mensaje reformulado",
            "route": "decision",
        },
    )

    handled = apply_api_chat_clarification(
        handler, request_context=ctx, t_api_chat=0.0, deps=deps,
    )
    assert handled is False
    assert ctx["pipeline_message"] == "mensaje reformulado"
    assert ctx["pipeline_response_route"] == "decision"
    assert ctx["clear_clarification_on_success"] is True


def test_limit_reached_sends_422_and_marks_run() -> None:
    handler = _FakeHandler()
    ctx = _base_request_context()
    coord = _FakeChatRunCoordinator()
    deps = _deps_base(
        clarification_state={"route": "decision", "turn_count": 5},
        directive={"type": "limit_reached", "question": "ultima pregunta"},
    )
    deps["chat_run_coordinator"] = coord

    import lia_graph.ui_chat_persistence as pers

    calls = {"user": 0, "assistant": 0}
    orig_user = pers.persist_user_turn
    orig_assist = pers.persist_assistant_turn

    def fake_user_turn(**_kw: Any) -> None:
        calls["user"] += 1

    def fake_assist_turn(**_kw: Any) -> None:
        calls["assistant"] += 1

    pers.persist_user_turn = fake_user_turn  # type: ignore[assignment]
    pers.persist_assistant_turn = fake_assist_turn  # type: ignore[assignment]
    try:
        # clarification module imported these at module load time, so also patch it
        import lia_graph.ui_chat_clarification as clar
        clar.persist_user_turn = fake_user_turn  # type: ignore[assignment]
        clar.persist_assistant_turn = fake_assist_turn  # type: ignore[assignment]
        try:
            handled = apply_api_chat_clarification(
                handler, request_context=ctx, t_api_chat=0.0, deps=deps,
            )
        finally:
            clar.persist_user_turn = orig_user  # type: ignore[assignment]
            clar.persist_assistant_turn = orig_assist  # type: ignore[assignment]
    finally:
        pers.persist_user_turn = orig_user  # type: ignore[assignment]
        pers.persist_assistant_turn = orig_assist  # type: ignore[assignment]

    assert handled is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.UNPROCESSABLE_ENTITY
    assert body["session_id"] == "sess-1"
    assert body["chat_run_id"] == "run-1"
    assert coord.failed == [("run-1", body)]
    assert coord.marked_sent == ["run-1"]
    assert calls == {"user": 1, "assistant": 1}


def test_ask_directive_sends_422_and_upserts_state() -> None:
    handler = _FakeHandler()
    ctx = _base_request_context()
    coord = _FakeChatRunCoordinator()
    deps = _deps_base(
        clarification_state={"route": "decision", "turn_count": 0, "active_error_code": "PC_COMPARATIVE_DATA_MISSING"},
        directive={"type": "ask", "question": "¿Cuál es el ingreso?"},
    )
    deps["chat_run_coordinator"] = coord

    import lia_graph.ui_chat_clarification as clar

    orig_user = clar.persist_user_turn
    orig_assist = clar.persist_assistant_turn
    clar.persist_user_turn = lambda **_kw: None  # type: ignore[assignment]
    clar.persist_assistant_turn = lambda **_kw: None  # type: ignore[assignment]
    try:
        handled = apply_api_chat_clarification(
            handler, request_context=ctx, t_api_chat=0.0, deps=deps,
        )
    finally:
        clar.persist_user_turn = orig_user  # type: ignore[assignment]
        clar.persist_assistant_turn = orig_assist  # type: ignore[assignment]

    assert handled is True
    status, body = handler.sent[0]
    assert status == HTTPStatus.UNPROCESSABLE_ENTITY
    assert body["user_message"] == "¿Cuál es el ingreso?"
    assert coord.failed[0][0] == "run-1"
    assert coord.marked_sent == ["run-1"]


def test_reexport_from_host_is_same_object() -> None:
    from lia_graph.ui_chat_clarification import (
        apply_api_chat_clarification as clar_gate,
        _build_semantic_clarification_payload as clar_semantic,
    )
    from lia_graph.ui_chat_payload import (
        apply_api_chat_clarification as host_gate,
        _build_semantic_clarification_payload as host_semantic,
    )
    assert host_gate is clar_gate
    assert host_semantic is clar_semantic
