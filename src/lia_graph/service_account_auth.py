"""Service account CRUD and API-key authentication for eval robots."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .platform_auth import AuthContext, PlatformAuthError

SERVICE_ACCOUNTS_PATH = Path(os.getenv("LIA_SERVICE_ACCOUNTS_PATH", "artifacts/service_accounts"))
_API_KEY_PREFIX = "lia_eval_"
_KEY_HEX_LENGTH = 32  # 32 bytes = 64 hex chars


@dataclass
class ServiceAccount:
    service_account_id: str
    tenant_id: str
    display_name: str
    role: str = "eval_robot"
    status: str = "active"
    secret_hash: str = ""
    secret_hint: str = ""
    scopes: list[str] | None = None
    rate_limit_profile: str = "eval_robot"
    metadata: dict[str, Any] | None = None
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    last_used_at: str | None = None
    expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if d["scopes"] is None:
            d["scopes"] = ["eval:read", "eval:write", "chat:ask"]
        if d["metadata"] is None:
            d["metadata"] = {}
        return d

    def to_public_dict(self) -> dict[str, Any]:
        d = self.to_dict()
        d.pop("secret_hash", None)
        return d


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_secret(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _build_hint(raw_key: str) -> str:
    bare = raw_key.removeprefix(_API_KEY_PREFIX)
    if len(bare) < 12:
        return f"{_API_KEY_PREFIX}{bare[:4]}****"
    return f"{_API_KEY_PREFIX}{bare[:8]}****{bare[-4:]}"


def _ensure_dir() -> Path:
    SERVICE_ACCOUNTS_PATH.mkdir(parents=True, exist_ok=True)
    return SERVICE_ACCOUNTS_PATH


def _account_file(service_account_id: str) -> Path:
    return _ensure_dir() / f"{service_account_id}.json"


def _load_account(service_account_id: str) -> ServiceAccount | None:
    path = _account_file(service_account_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return ServiceAccount(**{k: v for k, v in data.items() if k in ServiceAccount.__dataclass_fields__})


def _save_account(account: ServiceAccount) -> None:
    path = _account_file(account.service_account_id)
    path.write_text(json.dumps(account.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


# ── Public API ──


def create_service_account(
    *,
    tenant_id: str,
    display_name: str,
    created_by: str = "",
    role: str = "eval_robot",
    scopes: list[str] | None = None,
    expires_at: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not str(tenant_id or "").strip():
        raise PlatformAuthError("tenant_id requerido.", code="EVAL_VALIDATION_ERROR", http_status=400)
    if not str(display_name or "").strip():
        raise PlatformAuthError("display_name requerido.", code="EVAL_VALIDATION_ERROR", http_status=400)

    account_id = f"svc_eval_{secrets.token_hex(8)}"
    raw_key = f"{_API_KEY_PREFIX}{secrets.token_hex(_KEY_HEX_LENGTH)}"
    now = _now_iso()

    account = ServiceAccount(
        service_account_id=account_id,
        tenant_id=str(tenant_id).strip(),
        display_name=str(display_name).strip(),
        role=role,
        status="active",
        secret_hash=_hash_secret(raw_key),
        secret_hint=_build_hint(raw_key),
        scopes=scopes or ["eval:read", "eval:write", "chat:ask"],
        rate_limit_profile="eval_robot",
        metadata=metadata or {},
        created_by=str(created_by or "").strip(),
        created_at=now,
        updated_at=now,
        last_used_at=None,
        expires_at=expires_at,
    )
    _save_account(account)

    result = account.to_public_dict()
    result["api_key"] = raw_key  # Only returned once at creation time
    return result


def authenticate_service_account(api_key: str) -> AuthContext:
    raw = str(api_key or "").strip()
    if not raw.startswith(_API_KEY_PREFIX):
        raise PlatformAuthError("API key invalida.", code="auth_invalid", http_status=401)

    key_hash = _hash_secret(raw)

    for path in _ensure_dir().glob("svc_eval_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        stored_hash = str(data.get("secret_hash", ""))
        if not stored_hash:
            continue
        if not hmac.compare_digest(key_hash, stored_hash):
            continue

        # Match found
        if data.get("status") != "active":
            raise PlatformAuthError(
                "Cuenta de servicio revocada.",
                code="auth_account_revoked",
                http_status=403,
            )
        expires_at_str = data.get("expires_at")
        if expires_at_str:
            try:
                exp_dt = datetime.fromisoformat(expires_at_str)
                if exp_dt < datetime.now(timezone.utc):
                    raise PlatformAuthError(
                        "Cuenta de servicio expirada.",
                        code="auth_account_expired",
                        http_status=403,
                    )
            except (ValueError, TypeError):
                pass

        # Update last_used_at
        data["last_used_at"] = _now_iso()
        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

        return AuthContext(
            tenant_id=str(data.get("tenant_id", "")).strip(),
            user_id=str(data.get("service_account_id", "")).strip(),
            role=str(data.get("role", "eval_robot")).strip(),
            allowed_company_ids=(),
            active_company_id="",
            integration_id="eval_robot",
            claims_source="service_account_api_key",
            is_robot=True,
        )

    raise PlatformAuthError("API key invalida.", code="auth_invalid", http_status=401)


def revoke_service_account(service_account_id: str) -> dict[str, Any]:
    account = _load_account(service_account_id)
    if account is None:
        raise PlatformAuthError(
            "Cuenta de servicio no encontrada.",
            code="EVAL_ACCOUNT_NOT_FOUND",
            http_status=404,
        )
    account.status = "revoked"
    account.updated_at = _now_iso()
    _save_account(account)
    return account.to_public_dict()


def rotate_service_account_key(service_account_id: str) -> dict[str, Any]:
    account = _load_account(service_account_id)
    if account is None:
        raise PlatformAuthError(
            "Cuenta de servicio no encontrada.",
            code="EVAL_ACCOUNT_NOT_FOUND",
            http_status=404,
        )
    if account.status != "active":
        raise PlatformAuthError(
            "Solo se pueden rotar claves de cuentas activas.",
            code="EVAL_ACCOUNT_NOT_ACTIVE",
            http_status=400,
        )
    raw_key = f"{_API_KEY_PREFIX}{secrets.token_hex(_KEY_HEX_LENGTH)}"
    account.secret_hash = _hash_secret(raw_key)
    account.secret_hint = _build_hint(raw_key)
    account.updated_at = _now_iso()
    _save_account(account)

    result = account.to_public_dict()
    result["api_key"] = raw_key  # Only returned once
    return result


def list_service_accounts(*, tenant_id: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in sorted(_ensure_dir().glob("svc_eval_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(data.get("tenant_id", "")).strip() != str(tenant_id).strip():
            continue
        data.pop("secret_hash", None)
        results.append(data)
    return results
