"""Signed host-grant exchange and platform access tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from .auth_nonce_store import DEFAULT_AUTH_NONCES_PATH, consume_nonce

DEFAULT_HOST_INTEGRATIONS_CONFIG = Path("config/host_integrations.json")
# Temporary testing exception: keep access tokens alive for 24 hours during alpha QA.
DEFAULT_ACCESS_TTL_SECONDS = 86400
DEFAULT_HOST_GRANT_AUDIENCE = "lia-embed"
DEFAULT_ACCESS_AUDIENCE = "lia-api"
# `public_visitor` is the no-login `/public` chat role. It is sandboxed to
# `tenant_id == PUBLIC_TENANT_ID` and rejected at every non-chat handler via
# `_resolve_auth_context(allow_public=False)`.
ALLOWED_PLATFORM_ROLES = frozenset(
    {"tenant_user", "tenant_admin", "platform_admin", "eval_robot", "public_visitor"}
)
PUBLIC_TENANT_ID = "public_anon"
PUBLIC_VISITOR_ROLE = "public_visitor"
DEFAULT_PUBLIC_TOKEN_TTL_SECONDS = 3600


class PlatformAuthError(RuntimeError):
    def __init__(self, message: str, *, code: str = "auth_invalid", http_status: int = 401) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


@dataclass(frozen=True)
class HostIntegration:
    integration_id: str
    label: str
    allowed_origins: tuple[str, ...]
    status: str = "active"
    secret_env: str = ""
    tenant_id: str = ""
    shared_secret: str = ""
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "HostIntegration":
        allowed_raw = payload.get("allowed_origins", [])
        allowed = tuple(str(item).strip() for item in allowed_raw if str(item).strip())
        return cls(
            integration_id=str(payload.get("integration_id", "")).strip(),
            label=str(payload.get("label", "")).strip() or str(payload.get("integration_id", "")).strip(),
            allowed_origins=allowed,
            status=str(payload.get("status", "active")).strip() or "active",
            secret_env=str(payload.get("secret_env", "")).strip(),
            tenant_id=str(payload.get("tenant_id", "")).strip(),
            shared_secret=str(payload.get("shared_secret", "")).strip(),
            metadata=dict(payload.get("metadata") or {}) if isinstance(payload.get("metadata"), dict) else None,
        )

    def allows_origin(self, origin: str | None) -> bool:
        origin_value = str(origin or "").strip()
        if not origin_value:
            return True
        return origin_value in set(self.allowed_origins)

    def resolve_secret(self) -> str:
        if self.secret_env:
            env_secret = str(os.getenv(self.secret_env, "")).strip()
            if env_secret:
                return env_secret
        return self.shared_secret


@dataclass(frozen=True)
class AuthContext:
    tenant_id: str
    user_id: str
    role: str
    allowed_company_ids: tuple[str, ...]
    active_company_id: str
    integration_id: str = ""
    host_session_id: str = ""
    external_user_id: str = ""
    token_id: str = ""
    issued_at: int = 0
    expires_at: int = 0
    claims_source: str = "lia_access_token"
    is_robot: bool = False

    @classmethod
    def from_claims(cls, claims: dict[str, Any], *, claims_source: str) -> "AuthContext":
        allowed_raw = claims.get("allowed_company_ids", [])
        if isinstance(allowed_raw, str):
            allowed = tuple(item.strip() for item in allowed_raw.split(",") if item.strip())
        else:
            allowed = tuple(str(item).strip() for item in allowed_raw if str(item).strip())
        role = str(claims.get("role", "tenant_user")).strip() or "tenant_user"
        if role not in ALLOWED_PLATFORM_ROLES:
            role = "tenant_user"
        tenant_id_value = str(claims.get("tenant_id", "")).strip()
        if role == PUBLIC_VISITOR_ROLE:
            # public_visitor is sandboxed: it MUST have tenant_id == public_anon
            # and MUST NOT carry any company scopes. A token that violates this
            # is either tampered or buggy — refuse it.
            if tenant_id_value != PUBLIC_TENANT_ID:
                raise PlatformAuthError(
                    "Token público con tenant inválido.",
                    code="auth_public_token_invalid",
                    http_status=401,
                )
            if allowed:
                raise PlatformAuthError(
                    "Token público no puede portar `allowed_company_ids`.",
                    code="auth_public_token_invalid",
                    http_status=401,
                )
        return cls(
            tenant_id=tenant_id_value,
            user_id=str(claims.get("user_id") or claims.get("sub") or "").strip(),
            role=role,
            allowed_company_ids=allowed,
            active_company_id=str(claims.get("active_company_id", "")).strip(),
            integration_id=str(claims.get("integration_id") or claims.get("iss") or "").strip(),
            host_session_id=str(claims.get("host_session_id", "")).strip(),
            external_user_id=str(claims.get("external_user_id", "")).strip(),
            token_id=str(claims.get("jti", "")).strip(),
            issued_at=int(claims.get("iat") or 0),
            expires_at=int(claims.get("exp") or 0),
            claims_source=claims_source,
            is_robot=role == "eval_robot" or bool(claims.get("is_robot")),
        )

    def to_claims(self, *, audience: str, ttl_seconds: int) -> dict[str, Any]:
        now = int(time.time())
        exp = max(now + 60, now + int(ttl_seconds))
        claims: dict[str, Any] = {
            "sub": self.user_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "role": self.role,
            "allowed_company_ids": list(self.allowed_company_ids),
            "active_company_id": self.active_company_id,
            "integration_id": self.integration_id,
            "host_session_id": self.host_session_id or None,
            "external_user_id": self.external_user_id or None,
            "iss": "lia-platform",
            "aud": audience,
            "iat": now,
            "exp": exp,
            "jti": self.token_id or uuid4().hex,
        }
        if self.is_robot:
            claims["is_robot"] = True
        return claims

    def to_public_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "role": self.role,
            "allowed_company_ids": list(self.allowed_company_ids),
            "active_company_id": self.active_company_id,
            "integration_id": self.integration_id,
            "host_session_id": self.host_session_id or None,
            "external_user_id": self.external_user_id or None,
            "claims_source": self.claims_source,
            "issued_at": self.issued_at or None,
            "expires_at": self.expires_at or None,
            "token_id": self.token_id or None,
        }
        if self.is_robot:
            result["is_robot"] = True
        return result

    def with_active_company(self, company_id: str) -> "AuthContext":
        next_company = str(company_id or "").strip()
        if next_company and next_company not in set(self.allowed_company_ids):
            raise PlatformAuthError(
                "La compañia activa no pertenece a `allowed_company_ids`.",
                code="auth_company_not_allowed",
                http_status=403,
            )
        return AuthContext(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            role=self.role,
            allowed_company_ids=self.allowed_company_ids,
            active_company_id=next_company,
            integration_id=self.integration_id,
            host_session_id=self.host_session_id,
            external_user_id=self.external_user_id,
            token_id="",
            issued_at=0,
            expires_at=0,
            claims_source=self.claims_source,
            is_robot=self.is_robot,
        )


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    text = str(data or "").strip()
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + padding).encode("ascii"))


def _json_compact(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sign(header_segment: str, payload_segment: str, secret: str) -> str:
    digest = hmac.new(
        str(secret or "").encode("utf-8"),
        f"{header_segment}.{payload_segment}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _b64url_encode(digest)


def encode_signed_token(payload: dict[str, Any], *, secret: str) -> str:
    if not str(secret or "").strip():
        raise PlatformAuthError(
            "No existe secreto de firma configurado.",
            code="auth_secret_missing",
            http_status=500,
        )
    header_segment = _b64url_encode(_json_compact({"alg": "HS256", "typ": "JWT"}))
    payload_segment = _b64url_encode(_json_compact(payload))
    signature = _sign(header_segment, payload_segment, secret)
    return f"{header_segment}.{payload_segment}.{signature}"


def decode_unverified_token(token: str) -> dict[str, Any]:
    raw = str(token or "").strip()
    parts = raw.split(".")
    if len(parts) != 3:
        raise PlatformAuthError("Token invalido.", code="auth_token_invalid", http_status=401)
    try:
        payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PlatformAuthError("Token invalido.", code="auth_token_invalid", http_status=401) from exc
    if not isinstance(payload, dict):
        raise PlatformAuthError("Token invalido.", code="auth_token_invalid", http_status=401)
    return payload


def decode_signed_token(
    token: str,
    *,
    secret: str,
    expected_audience: str | None = None,
) -> dict[str, Any]:
    raw = str(token or "").strip()
    parts = raw.split(".")
    if len(parts) != 3:
        raise PlatformAuthError("Token invalido.", code="auth_token_invalid", http_status=401)
    header_segment, payload_segment, provided_signature = parts
    expected_signature = _sign(header_segment, payload_segment, secret)
    if not hmac.compare_digest(provided_signature, expected_signature):
        raise PlatformAuthError("Firma invalida.", code="auth_signature_invalid", http_status=401)
    payload = decode_unverified_token(raw)
    now = int(time.time())
    exp = int(payload.get("exp") or 0)
    if exp and exp < now:
        raise PlatformAuthError("Token expirado.", code="auth_token_expired", http_status=401)
    if expected_audience is not None:
        audience = str(payload.get("aud", "")).strip()
        if audience != expected_audience:
            raise PlatformAuthError("Audiencia invalida.", code="auth_audience_invalid", http_status=401)
    return payload


def load_host_integrations(
    *,
    config_path: Path = DEFAULT_HOST_INTEGRATIONS_CONFIG,
) -> dict[str, HostIntegration]:
    if not config_path.exists():
        return {}
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = payload if isinstance(payload, list) else payload.get("integrations", [])
    if not isinstance(rows, list):
        return {}
    integrations: dict[str, HostIntegration] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        integration = HostIntegration.from_dict(row)
        if not integration.integration_id:
            continue
        integrations[integration.integration_id] = integration
    return integrations


def resolve_platform_signing_secret() -> str:
    secret = str(os.getenv("LIA_PLATFORM_SIGNING_SECRET", "")).strip()
    if secret:
        return secret

    from .runtime_env import is_production_like_env

    if not is_production_like_env():
        # Local/dev fallback so public-mode and host-auth flows can run without
        # requiring secrets in every personal checkout.
        return "lia-dev-signing-secret"

    raise PlatformAuthError(
        "Configurar `LIA_PLATFORM_SIGNING_SECRET`.",
        code="auth_secret_missing",
        http_status=500,
    )


def exchange_host_grant(
    grant: str,
    *,
    origin: str | None = None,
    config_path: Path = DEFAULT_HOST_INTEGRATIONS_CONFIG,
    nonce_path: Path = DEFAULT_AUTH_NONCES_PATH,
    access_ttl_seconds: int = DEFAULT_ACCESS_TTL_SECONDS,
) -> dict[str, Any]:
    unverified = decode_unverified_token(grant)
    integration_id = str(unverified.get("integration_id") or unverified.get("iss") or "").strip()
    integrations = load_host_integrations(config_path=config_path)
    integration = integrations.get(integration_id)
    if integration is None or integration.status != "active":
        raise PlatformAuthError(
            "Integracion host no reconocida.",
            code="auth_integration_unknown",
            http_status=401,
        )
    if not integration.allows_origin(origin):
        raise PlatformAuthError(
            "Origin no permitido para la integracion.",
            code="auth_origin_invalid",
            http_status=403,
        )
    secret = integration.resolve_secret()
    if not secret:
        raise PlatformAuthError(
            "La integracion no tiene secreto configurado.",
            code="auth_integration_secret_missing",
            http_status=500,
        )
    claims = decode_signed_token(
        grant,
        secret=secret,
        expected_audience=DEFAULT_HOST_GRANT_AUDIENCE,
    )
    grant_origin = str(claims.get("origin", "")).strip()
    if grant_origin and origin and grant_origin != origin:
        raise PlatformAuthError(
            "Origin no coincide con el grant firmado.",
            code="auth_origin_mismatch",
            http_status=403,
        )
    if integration.tenant_id and str(claims.get("tenant_id", "")).strip() != integration.tenant_id:
        raise PlatformAuthError(
            "Tenant del grant no coincide con la integracion.",
            code="auth_tenant_mismatch",
            http_status=403,
        )
    token_id = str(claims.get("jti", "")).strip()
    if token_id:
        if not consume_nonce(
            token_id,
            nonce_type="host_grant",
            expires_at=str(claims.get("exp") or ""),
            path=nonce_path,
        ):
            raise PlatformAuthError(
                "Grant ya utilizado.",
                code="auth_replay_detected",
                http_status=409,
            )
    context = AuthContext.from_claims(
        {
            **claims,
            "integration_id": integration.integration_id,
        },
        claims_source="host_gateway_grant",
    )
    access_context = AuthContext(
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        role=context.role,
        allowed_company_ids=context.allowed_company_ids,
        active_company_id=context.active_company_id,
        integration_id=integration.integration_id,
        host_session_id=context.host_session_id,
        external_user_id=context.external_user_id,
        token_id="",
        issued_at=0,
        expires_at=0,
        claims_source="lia_access_token",
    )
    access_token = issue_access_token(access_context, ttl_seconds=access_ttl_seconds)
    resolved = authenticate_access_token(access_token)
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_at": resolved.expires_at,
        "me": resolved.to_public_dict(),
        "integration": {
            "integration_id": integration.integration_id,
            "label": integration.label,
            "allowed_origins": list(integration.allowed_origins),
        },
    }


def issue_access_token(context: AuthContext, *, ttl_seconds: int = DEFAULT_ACCESS_TTL_SECONDS) -> str:
    secret = resolve_platform_signing_secret()
    claims = context.to_claims(audience=DEFAULT_ACCESS_AUDIENCE, ttl_seconds=ttl_seconds)
    return encode_signed_token(claims, secret=secret)


def issue_public_visitor_token(
    *,
    pub_user_id: str,
    ttl_seconds: int = DEFAULT_PUBLIC_TOKEN_TTL_SECONDS,
) -> tuple[str, int]:
    """Mint a short-lived JWT for a no-login `/public` visitor.

    `pub_user_id` is the synthetic, deterministic `pub_<sha256(ip+salt)[:16]>`
    identifier — never a raw IP. The token is sandboxed:
      * `tenant_id` is hardcoded to `PUBLIC_TENANT_ID`
      * `role` is hardcoded to `PUBLIC_VISITOR_ROLE`
      * `allowed_company_ids` is empty — `from_claims` rejects any token that
        re-introduces a value here.

    Returns `(token, expires_at_epoch_seconds)`.
    """
    user_id = str(pub_user_id or "").strip()
    if not user_id:
        raise PlatformAuthError(
            "pub_user_id requerido para emitir token público.",
            code="auth_public_user_missing",
            http_status=500,
        )
    context = AuthContext(
        tenant_id=PUBLIC_TENANT_ID,
        user_id=user_id,
        role=PUBLIC_VISITOR_ROLE,
        allowed_company_ids=tuple(),
        active_company_id="",
        integration_id="lia_public",
        host_session_id="",
        external_user_id="",
        token_id="",
        issued_at=0,
        expires_at=0,
        claims_source="lia_access_token",
    )
    token = issue_access_token(context, ttl_seconds=ttl_seconds)
    resolved = authenticate_access_token(token)
    return token, int(resolved.expires_at or 0)


def authenticate_access_token(token: str) -> AuthContext:
    secret = resolve_platform_signing_secret()
    claims = decode_signed_token(
        token,
        secret=secret,
        expected_audience=DEFAULT_ACCESS_AUDIENCE,
    )
    return AuthContext.from_claims(claims, claims_source="lia_access_token")


def switch_active_company(context: AuthContext, company_id: str) -> dict[str, Any]:
    next_context = context.with_active_company(company_id)
    access_token = issue_access_token(next_context)
    resolved = authenticate_access_token(access_token)
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_at": resolved.expires_at,
        "me": resolved.to_public_dict(),
    }


def read_bearer_token(authorization_header: str | None) -> str | None:
    value = str(authorization_header or "").strip()
    if not value:
        return None
    parts = value.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise PlatformAuthError(
            "Authorization debe usar esquema Bearer.",
            code="auth_header_invalid",
            http_status=401,
        )
    token = str(parts[1]).strip()
    if not token:
        raise PlatformAuthError(
            "Authorization Bearer vacio.",
            code="auth_header_invalid",
            http_status=401,
        )
    return token
