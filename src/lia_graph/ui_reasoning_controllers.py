"""Reasoning event poll + SSE stream surfaces.

HTTP surface handled here (both GET):

* ``/api/reasoning/events``   — polling interface, returns events page + cursor
* ``/api/reasoning/stream``   — Server-Sent Events long-poll stream with
                                heartbeat; blocks until the client disconnects

The SSE path writes directly to ``handler.wfile`` and must set the streaming
headers manually (``text/event-stream``, ``no-cache``, ``X-Accel-Buffering: no``).
If you add another streaming endpoint in this file, follow the same header
pattern and wrap the write loop in the same ``BrokenPipeError/OSError`` guard.

See ``docs/done/next/granularization_v1.md`` §Controller Surface Catalog.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs


def handle_reasoning_get(
    handler: Any,
    path: str,
    parsed: Any,
    *,
    deps: dict[str, Any],
) -> bool:
    """Dispatch GET on ``/api/reasoning/events`` and ``/api/reasoning/stream``.

    ``deps`` keys: ``list_reasoning_events``, ``wait_reasoning_events``.
    """
    if path == "/api/reasoning/events":
        query = parse_qs(parsed.query)
        trace_id = str((query.get("trace_id") or [""])[0]).strip() or None
        cursor_raw = str((query.get("cursor") or ["0"])[0]).strip() or "0"
        limit_raw = str((query.get("limit") or ["200"])[0]).strip() or "200"
        try:
            cursor = int(cursor_raw)
            limit = int(limit_raw)
        except ValueError:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "`cursor` y `limit` deben ser enteros."},
            )
            return True
        if cursor < 0:
            handler._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "`cursor` debe ser >= 0."}
            )
            return True
        events, next_cursor, latest_seq = deps["list_reasoning_events"](
            trace_id=trace_id,
            cursor=cursor,
            limit=limit,
        )
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "trace_id": trace_id,
                "cursor": cursor,
                "next_cursor": next_cursor,
                "latest_seq": latest_seq,
                "events": events,
            },
        )
        return True

    if path != "/api/reasoning/stream":
        return False

    query = parse_qs(parsed.query)
    trace_id = str((query.get("trace_id") or [""])[0]).strip() or None
    cursor_raw = str((query.get("cursor") or ["0"])[0]).strip() or "0"
    try:
        cursor = int(cursor_raw)
    except ValueError:
        handler._send_json(
            HTTPStatus.BAD_REQUEST, {"error": "`cursor` debe ser entero."}
        )
        return True
    if cursor < 0:
        handler._send_json(
            HTTPStatus.BAD_REQUEST, {"error": "`cursor` debe ser >= 0."}
        )
        return True

    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.send_header("X-Accel-Buffering", "no")
    handler.end_headers()
    handler._log_api_response(
        status=HTTPStatus.OK, content_type="text/event-stream; charset=utf-8"
    )

    try:
        while True:
            events, next_cursor, latest_seq = deps["wait_reasoning_events"](
                trace_id=trace_id,
                cursor=cursor,
                timeout_seconds=12.0,
                limit=200,
            )
            if events:
                for event in events:
                    body = json.dumps(event, ensure_ascii=False)
                    packet = (
                        f"id: {event.get('seq', '')}\n"
                        "event: reasoning\n"
                        f"data: {body}\n\n"
                    )
                    handler.wfile.write(packet.encode("utf-8"))
                cursor = next_cursor
            else:
                heartbeat_payload = json.dumps(
                    {
                        "trace_id": trace_id,
                        "cursor": cursor,
                        "latest_seq": latest_seq,
                    },
                    ensure_ascii=False,
                )
                heartbeat = f"event: heartbeat\ndata: {heartbeat_payload}\n\n"
                handler.wfile.write(heartbeat.encode("utf-8"))
            handler.wfile.flush()
    except (BrokenPipeError, ConnectionResetError, OSError):
        return True
    return True
