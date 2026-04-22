"""Base class for the Lia UI HTTP handler.

Holds the non-dispatch methods of `LiaUIHandler`: request plumbing,
CORS/security headers, auth resolution, rate-limit / public-quota gating,
HTTP response primitives (`_send_bytes`, `_send_json`, SSE), chat-request
lifecycle hooks, the suspended-user cache, and the stdlib `log_message`
override.

The subclass `LiaUIHandler` (in `ui_server_handler_dispatch.py`, lifted in
Phase 3) adds verb dispatchers (`do_GET`/`do_POST`/etc.) and route handlers
on top of this base. MRO is therefore:

    [LiaUIHandler, LiaUIHandlerBase, BaseHTTPRequestHandler, object]

No circular imports: this module only pulls from `ui_server_constants`,
`ui_server_helpers`, and the domain sibling modules that `ui_server.py`
has always imported.
"""

from __future__ import annotations

import hashlib
import json
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse

from .platform_auth import (
    AuthContext,
    PUBLIC_VISITOR_ROLE,
    PlatformAuthError,
    authenticate_access_token,
    load_host_integrations,
    read_bearer_token,
)
from .rate_limiter import check_and_increment_daily_quota
from .runtime_env import is_production_like_env
from .ui_chat_context import build_clarification_scope_key, build_memory_summary
from .ui_chat_persistence import (
    initialize_chat_request_context,
    persist_assistant_turn,
    persist_usage_events,
    persist_user_turn,
)
from .ui_server_constants import (
    HOST_INTEGRATIONS_CONFIG_PATH,
    PUBLIC_CHAT_DAILY_CAP,
    PUBLIC_MODE_ENABLED,
    PUBLIC_TRUST_PROXY,
    PUBLIC_USER_SALT,
    _RATE_LIMITER,
    _SUSPENDED_CACHE,
    _SUSPENDED_CACHE_LOCK,
    _SUSPENDED_CACHE_TTL,
)
from .ui_server_deps import (
    _chat_controller_deps,
    _frontend_compat_controller_deps,
    _public_session_controller_deps,
)
from .ui_server_helpers import _emit_audit_event
from .ui_text_utilities import _json_bytes


class LiaUIHandlerBase(BaseHTTPRequestHandler):
    server_version = "LIAUI/0.1"

    def _request_origin(self) -> str | None:
        origin = str(self.headers.get("Origin", "")).strip()
        if origin:
            return origin
        referer = str(self.headers.get("Referer", "")).strip()
        if not referer:
            return None
        parsed = urlparse(referer)
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    def _allowed_cors_origin(self) -> str | None:
        origin = self._request_origin()
        if not origin:
            return None
        # Only allow localhost origins in non-production environments
        if not is_production_like_env():
            if origin.startswith("http://127.0.0.1:") or origin.startswith("http://localhost:"):
                return origin
        integrations = load_host_integrations(config_path=HOST_INTEGRATIONS_CONFIG_PATH)
        for integration in integrations.values():
            if integration.allows_origin(origin):
                return origin
        return None

    def _cors_headers(self) -> dict[str, str]:
        headers = {"Vary": "Origin"}
        allowed_origin = self._allowed_cors_origin()
        if allowed_origin:
            headers.update(
                {
                    "Access-Control-Allow-Origin": allowed_origin,
                    "Access-Control-Allow-Headers": "Authorization, Content-Type",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                }
            )
        return headers

    def _embed_security_headers(self) -> dict[str, str]:
        allowed_origins = sorted(
            {
                origin
                for integration in load_host_integrations(config_path=HOST_INTEGRATIONS_CONFIG_PATH).values()
                for origin in integration.allowed_origins
                if str(origin).strip()
            }
        )
        frame_ancestors = " ".join(["'self'", *allowed_origins]).strip() or "'self'"
        return {
            "Content-Security-Policy": f"frame-ancestors {frame_ancestors};",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

    def _send_auth_error(self, exc: PlatformAuthError) -> None:
        self._send_json(
            HTTPStatus(int(exc.http_status)),
            {
                "ok": False,
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                },
            },
            extra_headers={"X-LIA-Error-Code": exc.code},
        )

    def _resolve_auth_context(
        self,
        *,
        required: bool = False,
        allow_public: bool = False,
    ) -> AuthContext | None:
        """Resolve the request's auth context.

        `allow_public` is the single chokepoint that protects every non-chat
        handler from the no-login `/public` visitor. Default `False` means a
        valid `public_visitor` JWT is *rejected with 403* — the caller must
        opt in explicitly. Only `/api/chat` and `/api/chat/stream` (and the
        public route serving) are allowed to set `allow_public=True`.
        """
        authorization_header = self.headers.get("Authorization")
        try:
            token = read_bearer_token(authorization_header)
        except PlatformAuthError:
            if required:
                raise
            return None
        if not token:
            if required:
                raise PlatformAuthError(
                    "Authorization Bearer requerido.",
                    code="auth_required",
                    http_status=401,
                )
            return None

        # Service account API key (lia_eval_ prefix) — bypass JWT flow
        if token.startswith("lia_eval_"):
            try:
                from .service_account_auth import authenticate_service_account
                return authenticate_service_account(token)
            except PlatformAuthError:
                if required:
                    raise
                return None

        try:
            context = authenticate_access_token(token)
        except PlatformAuthError:
            if required:
                raise
            return None
        if context.role == PUBLIC_VISITOR_ROLE:
            # Master kill switch: even a perfectly-signed public token is
            # rejected when public mode is off, so flipping the env flag
            # ages out the entire surface instantly.
            if not PUBLIC_MODE_ENABLED:
                raise PlatformAuthError(
                    "Public mode disabled.",
                    code="public_mode_disabled",
                    http_status=503,
                )
            if not allow_public:
                raise PlatformAuthError(
                    "Acceso público no permitido en esta ruta.",
                    code="auth_public_forbidden",
                    http_status=403,
                )
            # Public visitors live in their own reserved tenant; the suspension
            # cache cannot match them, so skip that check.
            return context
        if self._is_user_suspended(context.tenant_id, context.user_id):
            raise PlatformAuthError(
                "Su cuenta está suspendida.",
                code="auth_user_suspended",
                http_status=403,
            )
        return context

    def _admin_tenant_scope(self, auth_context: AuthContext, requested_tenant_id: str | None = None) -> str | None:
        if auth_context.role not in {"tenant_admin", "platform_admin"}:
            raise PlatformAuthError(
                "Se requiere rol administrativo.",
                code="auth_role_forbidden",
                http_status=403,
            )
        if auth_context.role == "platform_admin":
            tenant_id = str(requested_tenant_id or "").strip()
            return tenant_id or None
        return auth_context.tenant_id

    def _resolve_feedback_rating(self, payload: dict[str, Any]) -> int | None:
        vote = str(payload.get("vote") or payload.get("thumb") or "").strip().lower()
        rating_raw = payload.get("rating")
        if isinstance(rating_raw, (int, float)):
            rating = int(rating_raw)
        elif vote in {"up", "down", "neutral"}:
            rating = {"up": 5, "down": 1, "neutral": 3}[vote]
        else:
            return None
        if 1 <= rating <= 5:
            return rating
        return None

    def _clarification_scope_key(self, request_context: dict[str, Any]) -> str:
        return build_clarification_scope_key(request_context)

    def _build_memory_summary(self, session: Any) -> str:
        return build_memory_summary(session)

    def _handle_chat_frontend_compat_get(self, path: str, parsed: Any) -> bool:
        from .ui_frontend_compat_controllers import handle_chat_frontend_compat_get
        return handle_chat_frontend_compat_get(
            self,
            path,
            parsed,
            deps=_frontend_compat_controller_deps(),
        )

    def _handle_chat_frontend_compat_post(self, path: str) -> bool:
        from .ui_frontend_compat_controllers import handle_chat_frontend_compat_post
        return handle_chat_frontend_compat_post(
            self,
            path,
            deps=_frontend_compat_controller_deps(),
        )

    def _initialize_chat_request_context(
        self,
        *,
        request_context: dict[str, Any],
        auth_context: AuthContext | None,
        channel: str,
    ) -> None:
        initialize_chat_request_context(
            request_context=request_context,
            auth_context=auth_context,
            channel=channel,
            deps=_chat_controller_deps(),
        )

    def _persist_user_turn(self, request_context: dict[str, Any]) -> None:
        persist_user_turn(request_context=request_context, deps=_chat_controller_deps())

    def _persist_assistant_turn(
        self,
        *,
        request_context: dict[str, Any],
        content: str,
        trace_id: str | None,
        layer_contributions: dict[str, int] | None = None,
    ) -> None:
        persist_assistant_turn(
            request_context=request_context,
            content=content,
            trace_id=trace_id,
            layer_contributions=layer_contributions,
            deps=_chat_controller_deps(),
        )

    def _persist_usage_events(
        self,
        *,
        request_context: dict[str, Any],
        response_payload: dict[str, Any],
    ) -> None:
        persist_usage_events(
            request_context=request_context,
            response_payload=response_payload,
            deps=_chat_controller_deps(),
        )

    def _start_api_request_log(self, method: str) -> None:
        self._api_log_response_emitted = False
        self._api_log_started_monotonic = time.monotonic()
        self._api_log_method = method
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            return
        _emit_audit_event(
            "api.http.request",
            {
                "method": method,
                "path": parsed.path,
                "query": parsed.query,
                "client_address": getattr(self, "client_address", None),
            },
        )

    def _log_api_response(self, *, status: int, content_type: str | None) -> None:
        if getattr(self, "_api_log_response_emitted", False):
            return
        raw_path = getattr(self, "path", "")
        if not isinstance(raw_path, str) or not raw_path:
            return
        parsed = urlparse(raw_path)
        if not parsed.path.startswith("/api/"):
            return
        started = getattr(self, "_api_log_started_monotonic", None)
        duration_ms = None
        if isinstance(started, (int, float)):
            duration_ms = round((time.monotonic() - float(started)) * 1000, 2)
        _emit_audit_event(
            "api.http.reply",
            {
                "method": str(getattr(self, "_api_log_method", "") or "UNKNOWN"),
                "path": parsed.path,
                "status": int(status),
                "content_type": content_type,
                "duration_ms": duration_ms,
            },
        )
        self._api_log_response_emitted = True

    @staticmethod
    def _base_security_headers() -> dict[str, str]:
        headers: dict[str, str] = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        if is_production_like_env():
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return headers

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        content_type: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        for key, value in self._base_security_headers().items():
            self.send_header(key, value)
        if str(getattr(self, "path", "") or "").startswith("/api/"):
            for key, value in self._cors_headers().items():
                self.send_header(key, value)
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(str(key), str(value))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self._log_api_response(status=status, content_type=content_type)

    def _send_json(
        self,
        status: int,
        payload: dict[str, Any],
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self._send_bytes(
            status,
            _json_bytes(payload),
            "application/json; charset=utf-8",
            extra_headers=extra_headers,
        )

    def _send_event_stream_headers(self, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("X-Accel-Buffering", "no")
        for key, value in self._cors_headers().items():
            self.send_header(key, value)
        self.end_headers()
        self.close_connection = True
        self._log_api_response(status=status, content_type="text/event-stream; charset=utf-8")

    def _write_sse_event(
        self,
        event_name: str,
        payload: dict[str, Any],
        *,
        event_id: str | int | None = None,
    ) -> None:
        packet_parts: list[str] = []
        if event_id is not None:
            packet_parts.append(f"id: {event_id}")
        packet_parts.append(f"event: {str(event_name or 'message').strip() or 'message'}")
        packet_parts.append(f"data: {json.dumps(payload, ensure_ascii=False)}")
        packet = "\n".join(packet_parts) + "\n\n"
        self.wfile.write(packet.encode("utf-8"))
        self.wfile.flush()

    def _read_json_payload(
        self,
        *,
        empty_body: bytes = b"{}",
        object_error: str | None = None,
        max_size: int = 1_048_576,
    ) -> Any | None:
        length_raw = self.headers.get("Content-Length", "0")
        try:
            length = int(length_raw)
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Content-Length invalido."})
            return None

        if length > max_size:
            self._send_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": f"Payload excede el tamaño maximo ({max_size} bytes)."},
            )
            return None

        raw = self.rfile.read(length) if length > 0 else empty_body
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "JSON invalido."})
            return None

        if object_error is not None and not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": object_error})
            return None
        return payload

    def _check_rate_limit(self, endpoint_key: str, max_requests: int, window_seconds: int) -> bool:
        """Return True if rate limit is exceeded (request should be blocked)."""
        client_ip = self._get_trusted_client_ip()
        key = f"{endpoint_key}:{client_ip}"
        if not _RATE_LIMITER.is_allowed(key, max_requests, window_seconds):
            self._send_json(
                HTTPStatus.TOO_MANY_REQUESTS,
                {"error": "Demasiadas solicitudes. Intente de nuevo en unos segundos."},
                extra_headers={"Retry-After": str(window_seconds)},
            )
            return True
        return False

    def _get_trusted_client_ip(self) -> str:
        """Return the client IP, honoring `X-Forwarded-For` only when trusted.

        Behind Railway / any reverse proxy, `self.client_address` is the proxy
        IP, not the real client. We honor `X-Forwarded-For` (leftmost entry)
        only when `LIA_TRUST_PROXY=1`. We also reject pathologically long XFF
        chains (>10 hops) as untrusted, since they are typical of spoofed
        requests originating outside the trusted ingress.
        """
        if PUBLIC_TRUST_PROXY:
            xff = str(self.headers.get("X-Forwarded-For") or "").strip()
            if xff:
                parts = [item.strip() for item in xff.split(",") if item.strip()]
                if 1 <= len(parts) <= 10:
                    return parts[0]
            real_ip = str(self.headers.get("X-Real-IP") or "").strip()
            if real_ip:
                return real_ip
        return getattr(self, "client_address", ("unknown",))[0]

    def _hash_public_user_id(self, ip: str) -> str:
        """Return the synthetic, deterministic public visitor identifier.

        `pub_<sha256(ip + LIA_PUBLIC_USER_SALT)[:16]>`.

        Raw IPs are never persisted; only this hash is. The salt is a Railway
        secret so the hash space cannot be precomputed by an attacker.
        """
        salt = PUBLIC_USER_SALT or ""
        digest = hashlib.sha256(f"{ip}{salt}".encode("utf-8")).hexdigest()[:16]
        return f"pub_{digest}"

    def _check_public_daily_quota(self, pub_user_id: str) -> bool:
        """Return True if the daily quota is exceeded (request blocked).

        Mirrors the contract of `_check_rate_limit`: True means the response
        has already been sent (429) and the caller should `return`.
        """
        if not is_production_like_env():
            return False
        try:
            from .supabase_client import get_supabase_client
            client = get_supabase_client()
        except Exception:
            client = None
        allowed, _count = check_and_increment_daily_quota(
            ip_hash=pub_user_id,
            cap=PUBLIC_CHAT_DAILY_CAP,
            supabase_client=client,
        )
        if not allowed:
            self._send_json(
                HTTPStatus.TOO_MANY_REQUESTS,
                {
                    "error": {
                        "code": "public_daily_quota_exceeded",
                        "message": "Has alcanzado el límite diario de mensajes en modo público.",
                    }
                },
                extra_headers={"Retry-After": "86400"},
            )
            return True
        return False

    def _is_public_visitor_request(self) -> bool:
        """Probe whether the current request carries a `public_visitor` JWT.

        Returns False (without raising) when no token is present or the token
        is for a normal authenticated user. Used by the `/api/chat` rate-limit
        branch to choose between the public and the authenticated tier.
        """
        try:
            ctx = self._resolve_auth_context(required=False, allow_public=True)
        except PlatformAuthError:
            return False
        return bool(ctx is not None and ctx.role == PUBLIC_VISITOR_ROLE)

    def _handle_public_session_post(self) -> None:
        from .ui_public_session_controllers import handle_public_session_post
        handle_public_session_post(self, deps=_public_session_controller_deps())

    def _serve_public_page(self) -> None:
        from .ui_public_session_controllers import handle_public_page_get
        handle_public_page_get(self, deps=_public_session_controller_deps())

    def _is_user_suspended(self, tenant_id: str, user_id: str) -> bool:
        """Check if user is suspended (cached, best-effort)."""
        if not user_id:
            return False
        cache_key = (tenant_id, user_id)
        now = time.monotonic()
        with _SUSPENDED_CACHE_LOCK:
            cached = _SUSPENDED_CACHE.get(cache_key)
            if cached is not None:
                is_suspended, check_time = cached
                if now - check_time < _SUSPENDED_CACHE_TTL:
                    return is_suspended
        # Best-effort DB check
        try:
            from .supabase_client import get_supabase_client
            client = get_supabase_client()
            if client is None:
                return False
            result = client.table("users").select("status").eq("user_id", user_id).maybe_single().execute()
            is_suspended = bool(result and result.data and result.data.get("status") == "suspended")
            with _SUSPENDED_CACHE_LOCK:
                _SUSPENDED_CACHE[cache_key] = (is_suspended, now)
            return is_suspended
        except Exception:
            return False

    def log_message(self, format: str, *args: object) -> None:
        # Evita ruido en stdout por cada request.
        return
