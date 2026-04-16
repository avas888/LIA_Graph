"""Replay-protection nonce store for signed host grants."""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_AUTH_NONCES_PATH = Path("artifacts/runtime/auth_nonces.json")
DEFAULT_NONCE_TTL_SECONDS = 900

_LOCK = threading.RLock()
_NONCE_RE = re.compile(r"^[A-Za-z0-9_.:\-]{1,256}$")
_STORE_VERSION = "2026-03-14.1"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().replace(microsecond=0).isoformat()


def _parse_iso(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _sanitize_nonce_id(nonce_id: str) -> str:
    value = str(nonce_id or "").strip()
    if not value:
        raise ValueError("`nonce_id` es requerido.")
    if _NONCE_RE.match(value):
        return value
    normalized = re.sub(r"[^A-Za-z0-9_.:\-]+", "_", value)[:256]
    if not normalized:
        raise ValueError("`nonce_id` invalido.")
    return normalized


def _nonce_key(nonce_id: str, nonce_type: str) -> str:
    return f"{str(nonce_type or 'default').strip() or 'default'}:{_sanitize_nonce_id(nonce_id)}"


def _use_supabase(path: Path) -> bool:
    from .supabase_client import is_supabase_enabled, matches_default_storage_path

    if not matches_default_storage_path(path, DEFAULT_AUTH_NONCES_PATH):
        return False
    return is_supabase_enabled()


def _empty_store() -> dict[str, Any]:
    return {
        "version": _STORE_VERSION,
        "updated_at": None,
        "nonces": {},
    }


def _read_store(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_store()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_store()
    if not isinstance(payload, dict):
        return _empty_store()
    nonces = payload.get("nonces")
    if not isinstance(nonces, dict):
        nonces = {}
    return {
        "version": str(payload.get("version") or _STORE_VERSION),
        "updated_at": payload.get("updated_at"),
        "nonces": nonces,
    }


def _write_store(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _purge_expired_locked(store: dict[str, Any], *, now: datetime) -> int:
    nonces = dict(store.get("nonces") or {})
    removed = 0
    for key, row in list(nonces.items()):
        if not isinstance(row, dict):
            del nonces[key]
            removed += 1
            continue
        expires_at = _parse_iso(row.get("expires_at"))
        if expires_at is not None and expires_at <= now:
            del nonces[key]
            removed += 1
    if removed > 0:
        store["nonces"] = nonces
        store["updated_at"] = now.replace(microsecond=0).isoformat()
    return removed


def _sb_purge_expired() -> int:
    from .supabase_client import get_supabase_client

    client = get_supabase_client()
    result = client.table("auth_nonces").delete().lt("expires_at", _utc_now_iso()).execute()
    return len(result.data or [])


def _sb_consume_nonce(
    nonce_id: str,
    *,
    nonce_type: str,
    expires_at: str,
) -> bool:
    from .supabase_client import get_supabase_client

    client = get_supabase_client()
    key = _nonce_key(nonce_id, nonce_type)
    existing = client.table("auth_nonces").select("nonce_key").eq("nonce_key", key).limit(1).execute()
    if existing.data:
        return False
    client.table("auth_nonces").insert(
        {
            "nonce_key": key,
            "nonce_id": nonce_id,
            "nonce_type": nonce_type,
            "expires_at": expires_at,
            "consumed_at": _utc_now_iso(),
        }
    ).execute()
    return True


def purge_expired_nonces(*, path: Path = DEFAULT_AUTH_NONCES_PATH) -> int:
    if _use_supabase(path):
        return _sb_purge_expired()
    with _LOCK:
        store = _read_store(path)
        removed = _purge_expired_locked(store, now=_utc_now())
        if removed > 0:
            _write_store(path, store)
        return removed


def consume_nonce(
    nonce_id: str,
    *,
    nonce_type: str = "host_grant",
    ttl_seconds: int = DEFAULT_NONCE_TTL_SECONDS,
    expires_at: str | None = None,
    path: Path = DEFAULT_AUTH_NONCES_PATH,
) -> bool:
    safe_nonce_id = _sanitize_nonce_id(nonce_id)
    expiry = _parse_iso(expires_at)
    if expiry is None:
        expiry = _utc_now() + timedelta(seconds=max(60, int(ttl_seconds)))
    expiry_iso = expiry.replace(microsecond=0).isoformat()
    if _use_supabase(path):
        _sb_purge_expired()
        return _sb_consume_nonce(
            safe_nonce_id,
            nonce_type=str(nonce_type or "host_grant").strip() or "host_grant",
            expires_at=expiry_iso,
        )

    with _LOCK:
        now = _utc_now()
        store = _read_store(path)
        _purge_expired_locked(store, now=now)
        nonces = dict(store.get("nonces") or {})
        key = _nonce_key(safe_nonce_id, str(nonce_type or "host_grant").strip() or "host_grant")
        if key in nonces:
            return False
        nonces[key] = {
            "nonce_key": key,
            "nonce_id": safe_nonce_id,
            "nonce_type": str(nonce_type or "host_grant").strip() or "host_grant",
            "expires_at": expiry_iso,
            "consumed_at": now.replace(microsecond=0).isoformat(),
        }
        store["nonces"] = nonces
        store["updated_at"] = now.replace(microsecond=0).isoformat()
        _write_store(path, store)
        return True
