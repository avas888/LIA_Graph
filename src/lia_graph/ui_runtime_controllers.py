"""Runtime-config + terms-of-use read + orchestration settings write surfaces.

HTTP surface handled here:

* ``GET /api/llm/status``      — LLM adapter resolution status
* ``GET /api/terms/status``    — accepted-terms status for the current user
* ``GET /api/terms``           — full terms markdown + status
* ``GET /terms-of-use``        — raw terms markdown (for browser view)
* ``PUT /api/orchestration/settings`` — admin write of orchestration config

Dispatch note: Lia_Graph also wires ``GET /api/llm/status`` into the
frontend-compat surface (see ``ui_frontend_compat_controllers``) which
currently runs earlier in ``do_GET`` and returns a simpler stub shape. The
richer impl below is kept for contract parity with Lia_contadores and in
case the dispatcher is re-ordered to expose the real adapter resolution.

See ``docs/next/granularization_v1.md`` §Controller Surface Catalog.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any
from urllib.parse import urlparse


def handle_runtime_terms_get(
    handler: Any,
    path: str,
    *,
    deps: dict[str, Any],
) -> bool:
    """Dispatch GET on ``/api/llm/status``, ``/api/terms*``, ``/terms-of-use``.

    ``deps`` keys: ``resolve_llm_adapter``, ``LLMRuntimeConfigInvalidError``,
    ``emit_event``, ``get_terms_status``, ``read_terms_text``,
    ``llm_runtime_config_path``, ``terms_policy_path``, ``terms_state_path``.
    """
    if path == "/api/llm/status":
        try:
            _, runtime = deps["resolve_llm_adapter"](
                runtime_config_path=deps["llm_runtime_config_path"],
                requested_provider=None,
            )
        except deps["LLMRuntimeConfigInvalidError"] as exc:
            deps["emit_event"](
                "llm_runtime_config_invalid",
                {
                    "path": str(deps["llm_runtime_config_path"]),
                    "error": str(exc),
                },
            )
            handler._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "llm_runtime_config_invalid", "details": str(exc)},
            )
            return True
        handler._send_json(HTTPStatus.OK, {"ok": True, "llm_runtime": runtime})
        return True

    if path == "/api/terms/status":
        status = deps["get_terms_status"](
            policy_path=deps["terms_policy_path"],
            state_path=deps["terms_state_path"],
        )
        handler._send_json(HTTPStatus.OK, status)
        return True

    if path == "/api/terms":
        status = deps["get_terms_status"](
            policy_path=deps["terms_policy_path"],
            state_path=deps["terms_state_path"],
        )
        handler._send_json(
            HTTPStatus.OK,
            {
                "terms_markdown": deps["read_terms_text"](
                    policy_path=deps["terms_policy_path"]
                ),
                "status": status,
            },
        )
        return True

    if path == "/terms-of-use":
        text = deps["read_terms_text"](policy_path=deps["terms_policy_path"])
        if not text:
            handler._send_json(
                HTTPStatus.NOT_FOUND, {"error": "Terminos no disponibles."}
            )
            return True
        handler._send_bytes(
            HTTPStatus.OK, text.encode("utf-8"), "text/markdown; charset=utf-8"
        )
        return True

    return False


def handle_orchestration_settings_put(
    handler: Any,
    *,
    deps: dict[str, Any],
) -> None:
    """Handle PUT ``/api/orchestration/settings``.

    ``deps`` keys: ``update_orchestration_settings``, ``orchestration_settings_path``.
    """
    parsed = urlparse(handler.path)
    path = (parsed.path or "/").rstrip("/") or "/"
    if path != "/api/orchestration/settings":
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint no encontrado."})
        return

    payload = handler._read_json_payload(object_error="El body debe ser un objeto JSON.")
    if payload is None:
        return

    try:
        settings = deps["update_orchestration_settings"](
            payload, path=deps["orchestration_settings_path"]
        )
    except ValueError as exc:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        return

    handler._send_json(HTTPStatus.OK, {"ok": True, "settings": settings})
