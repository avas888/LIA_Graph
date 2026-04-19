"""Public visitor session endpoints extracted from ``ui_server.LiaUIHandler``.

Two surfaces, tightly coupled around the captcha + JWT-minting flow:

* ``POST /api/public/session`` → ``handle_public_session_post``
* ``GET /public`` (and ``/public.html``) → ``handle_public_page_get``

Both are **env-gated** by ``LIA_PUBLIC_MODE_ENABLED`` and by whether the
deployment requires Cloudflare Turnstile (``PUBLIC_CAPTCHA_ENABLED``). Every
env-driven flag and every stateful collaborator is injected via ``deps`` so
tests that ``monkeypatch.setattr(ui_server, "PUBLIC_MODE_ENABLED", True)``
continue to take effect — no direct ``from .ui_server import …``.
"""

from __future__ import annotations

import html
import json
from http import HTTPStatus
from typing import Any


def handle_public_session_post(
    handler: Any,
    *,
    deps: dict[str, Any],
) -> None:
    """`POST /api/public/session` — mint a short-lived public_visitor JWT.

    First-time visitors must include `turnstile_token` in the body. Once
    Cloudflare confirms the token, the IP-hash is recorded in
    `public_captcha_passes` and subsequent visits skip the captcha.
    """
    if not deps["public_mode_enabled"]:
        handler._send_json(
            HTTPStatus.SERVICE_UNAVAILABLE,
            {"error": {"code": "public_mode_disabled", "message": "Public mode disabled."}},
        )
        return

    issue_token = deps["issue_public_visitor_token"]
    ttl_seconds = deps["public_token_ttl_seconds"]

    client_ip = handler._get_trusted_client_ip()
    pub_user_id = handler._hash_public_user_id(client_ip)

    if not deps["public_captcha_enabled"]:
        token, expires_at = issue_token(
            pub_user_id=pub_user_id,
            ttl_seconds=ttl_seconds,
        )
        handler._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "token": token,
                "expires_at": expires_at,
                "captcha_required": False,
            },
        )
        return

    public_captcha_pass_exists = deps["public_captcha_pass_exists"]
    public_captcha_pass_record = deps["public_captcha_pass_record"]
    verify_turnstile = deps["verify_turnstile"]
    turnstile_site_key = deps["public_turnstile_site_key"]

    body_raw = b""
    try:
        content_length = int(handler.headers.get("Content-Length") or 0)
    except (TypeError, ValueError):
        content_length = 0
    if content_length > 0:
        try:
            body_raw = handler.rfile.read(content_length) or b""
        except Exception:
            body_raw = b""
    try:
        body = json.loads(body_raw.decode("utf-8")) if body_raw else {}
    except (ValueError, json.JSONDecodeError):
        body = {}
    if not isinstance(body, dict):
        body = {}

    already_passed = public_captcha_pass_exists(pub_user_id)
    if not already_passed:
        turnstile_token = str(body.get("turnstile_token") or "").strip()
        if not turnstile_token:
            handler._send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "error": {
                        "code": "captcha_required",
                        "message": "Captcha requerido para el primer acceso público.",
                    },
                    "site_key": turnstile_site_key,
                },
            )
            return
        if not verify_turnstile(turnstile_token, client_ip):
            handler._send_json(
                HTTPStatus.FORBIDDEN,
                {
                    "error": {
                        "code": "captcha_invalid",
                        "message": "Captcha inválido. Recargue la página.",
                    }
                },
            )
            return
        public_captcha_pass_record(pub_user_id)

    token, expires_at = issue_token(
        pub_user_id=pub_user_id,
        ttl_seconds=ttl_seconds,
    )
    handler._send_json(
        HTTPStatus.OK,
        {
            "ok": True,
            "token": token,
            "expires_at": expires_at,
            "captcha_required": False,
        },
    )


def handle_public_page_get(
    handler: Any,
    *,
    deps: dict[str, Any],
) -> None:
    """`GET /public` — serve the chat-only HTML shell with token injection.

    Two paths:
      * IP already in `public_captcha_passes` → mint token, inject as
        `lia-public-token` meta, set `lia-public-captcha-required=false`.
      * Otherwise → leave the token meta empty, set
        `lia-public-captcha-required=true`, inject the Turnstile site key.

    The frontend's `/src/app/public/main.ts` reads these meta tags on
    boot. All injected values are `html.escape`d as defense in depth even
    though the JWT alphabet is `[A-Za-z0-9_\\-.]` and the site key is
    `[A-Za-z0-9_\\-]`.
    """
    if not deps["public_mode_enabled"]:
        handler._send_json(
            HTTPStatus.SERVICE_UNAVAILABLE,
            {"error": {"code": "public_mode_disabled", "message": "Public mode disabled."}},
        )
        return

    ui_dir = deps["ui_dir"]
    public_html_path = ui_dir / "public.html"
    if not public_html_path.exists():
        handler._send_json(
            HTTPStatus.NOT_FOUND,
            {"error": {"code": "public_shell_missing", "message": "Public shell not built."}},
        )
        return

    issue_token = deps["issue_public_visitor_token"]
    ttl_seconds = deps["public_token_ttl_seconds"]
    turnstile_site_key = deps["public_turnstile_site_key"]

    client_ip = handler._get_trusted_client_ip()
    pub_user_id = handler._hash_public_user_id(client_ip)

    token_value = ""
    expires_value = ""
    captcha_required = "true"
    if not deps["public_captcha_enabled"]:
        token, expires_at = issue_token(
            pub_user_id=pub_user_id,
            ttl_seconds=ttl_seconds,
        )
        token_value = token
        expires_value = str(int(expires_at or 0))
        captcha_required = "false"
    else:
        public_captcha_pass_exists = deps["public_captcha_pass_exists"]
        if public_captcha_pass_exists(pub_user_id):
            token, expires_at = issue_token(
                pub_user_id=pub_user_id,
                ttl_seconds=ttl_seconds,
            )
            token_value = token
            expires_value = str(int(expires_at or 0))
            captcha_required = "false"

    try:
        html_text = public_html_path.read_text(encoding="utf-8")
    except OSError:
        handler._send_json(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"error": {"code": "public_shell_unreadable", "message": "Cannot read public shell."}},
        )
        return

    replacements = {
        "__LIA_PUBLIC_TOKEN__": html.escape(token_value),
        "__LIA_PUBLIC_EXPIRES_AT__": html.escape(expires_value),
        "__LIA_PUBLIC_CAPTCHA_REQUIRED__": html.escape(captcha_required),
        "__LIA_PUBLIC_TURNSTILE_SITE_KEY__": html.escape(turnstile_site_key),
    }
    for placeholder, value in replacements.items():
        html_text = html_text.replace(placeholder, value)

    handler._send_bytes(
        HTTPStatus.OK,
        html_text.encode("utf-8"),
        "text/html; charset=utf-8",
        extra_headers={"Cache-Control": "no-store"},
    )
