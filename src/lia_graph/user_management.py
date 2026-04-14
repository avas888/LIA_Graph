"""User and tenant management store (Supabase-backed)."""

from __future__ import annotations

import secrets
from collections.abc import Iterable
from datetime import datetime, timezone, timedelta
from typing import Any

from .password_auth import hash_password, verify_password

_INVITE_TTL_HOURS = 72


def _get_client() -> Any:
    from .supabase_client import get_supabase_client
    client = get_supabase_client()
    if client is None:
        raise RuntimeError("Supabase client not available.")
    return client


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def _single_row(rows: Iterable[dict[str, Any]] | None, *, missing_message: str) -> dict[str, Any]:
    data = list(rows or [])
    if not data:
        raise ValueError(missing_message)
    if len(data) > 1:
        raise ValueError(
            "Hay múltiples cuentas con el mismo correo. Corrija la data antes de continuar."
        )
    return data[0]


def _load_user_by_email(client: Any, email: str, *, allow_missing: bool = False) -> dict[str, Any] | None:
    result = (
        client.table("users")
        .select("user_id, email, display_name, status, password_hash, password_reset_required")
        .eq("email", email)
        .limit(2)
        .execute()
    )
    rows = list(result.data or [])
    if not rows and allow_missing:
        return None
    return _single_row(rows, missing_message="Usuario no encontrado.")


def _list_memberships(client: Any, user_id: str) -> list[dict[str, Any]]:
    result = (
        client.table("tenant_memberships")
        .select("tenant_id, role, tenants(display_name)")
        .eq("user_id", user_id)
        .execute()
    )
    memberships: list[dict[str, Any]] = []
    for row in result.data or []:
        tenant_row = row.get("tenants") or {}
        if isinstance(tenant_row, list):
            tenant_row = tenant_row[0] if tenant_row else {}
        memberships.append(
            {
                "tenant_id": str(row.get("tenant_id", "") or "").strip(),
                "role": str(row.get("role", "tenant_user") or "tenant_user").strip(),
                "display_name": str(tenant_row.get("display_name", "") or "").strip(),
            }
        )
    return memberships


def _revoke_pending_invites(client: Any, tenant_id: str, email: str) -> None:
    client.table("invite_tokens").update({"status": "revoked"}).eq("tenant_id", tenant_id).eq(
        "email", email
    ).eq("status", "pending").execute()


# ---------------------------------------------------------------------------
# User listing
# ---------------------------------------------------------------------------

def list_tenant_users(tenant_id: str, *, status: str | None = None) -> list[dict[str, Any]]:
    """List all users in a tenant with their roles and status."""
    client = _get_client()
    query = (
        client.table("tenant_memberships")
        .select("user_id, role, users(user_id, email, display_name, status, created_at)")
        .eq("tenant_id", tenant_id)
    )
    result = query.execute()
    rows: list[dict[str, Any]] = []
    for m in result.data or []:
        user_data = m.get("users") or {}
        user_status = user_data.get("status", "active")
        if status and user_status != status:
            continue
        rows.append({
            "user_id": m.get("user_id", ""),
            "email": user_data.get("email", ""),
            "display_name": user_data.get("display_name", ""),
            "role": m.get("role", "tenant_user"),
            "status": user_status,
            "created_at": user_data.get("created_at", ""),
        })
    return rows


# ---------------------------------------------------------------------------
# Invite flow
# ---------------------------------------------------------------------------

def invite_user(
    tenant_id: str,
    email: str,
    role: str = "tenant_user",
    invited_by: str = "",
) -> dict[str, Any]:
    """Create an invite token and optionally a user record."""
    client = _get_client()
    tenant_id = str(tenant_id or "").strip()
    email = _normalize_email(email)

    if not tenant_id:
        raise ValueError("Se requiere tenant_id.")

    if role not in ("tenant_user", "tenant_admin"):
        raise ValueError(f"Rol invalido: {role}")

    existing = _load_user_by_email(client, email, allow_missing=True)
    if existing is not None:
        user_id = str(existing["user_id"])
    else:
        user_id = f"usr_{secrets.token_hex(8)}"
        client.table("users").insert({
            "user_id": user_id,
            "email": email,
            "display_name": "",
            "status": "invited",
            "password_hash": "",
            "password_reset_required": True,
        }).execute()

    _revoke_pending_invites(client, tenant_id, email)

    # Create invite token
    token_id = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=_INVITE_TTL_HOURS)

    client.table("invite_tokens").insert({
        "token_id": token_id,
        "tenant_id": tenant_id,
        "email": email,
        "role": role,
        "invited_by": invited_by,
        "status": "pending",
        "expires_at": expires_at.isoformat(),
    }).execute()

    membership = (
        client.table("tenant_memberships")
        .select("role")
        .eq("tenant_id", tenant_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    effective_role = (
        str((membership.data or {}).get("role", "") or "").strip()
        if membership and membership.data
        else role
    )

    return {
        "token_id": token_id,
        "email": email,
        "role": effective_role,
        "expires_at": expires_at.isoformat(),
        "user_id": user_id,
    }


def accept_invite(token_id: str, display_name: str = "", *, password: str) -> dict[str, Any]:
    """Accept an invitation — activate user, create membership, return context."""
    client = _get_client()
    password_hash = hash_password(password)

    # Fetch and validate token
    result = (
        client.table("invite_tokens")
        .select("*")
        .eq("token_id", token_id)
        .eq("status", "pending")
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        raise ValueError("Invitacion no encontrada o ya fue utilizada.")

    token = result.data
    expires_at = datetime.fromisoformat(token["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        # Mark expired
        client.table("invite_tokens").update({"status": "expired"}).eq("token_id", token_id).execute()
        raise ValueError("La invitacion ha expirado.")

    tenant_id = token["tenant_id"]
    email = token["email"]
    role = token["role"]

    # Find or create user
    user_row = _load_user_by_email(client, email, allow_missing=True)
    if user_row is not None:
        user_id = user_row["user_id"]
    else:
        user_id = f"usr_{secrets.token_hex(8)}"
        client.table("users").insert({
            "user_id": user_id,
            "email": email,
            "display_name": display_name or email.split("@")[0],
            "status": "active",
            "password_hash": password_hash,
            "password_reset_required": False,
            "password_updated_at": _utcnow_iso(),
        }).execute()

    # Update user
    update_data: dict[str, Any] = {
        "status": "active",
        "password_hash": password_hash,
        "password_reset_required": False,
        "password_updated_at": _utcnow_iso(),
    }
    if display_name:
        update_data["display_name"] = display_name
    client.table("users").update(update_data).eq("user_id", user_id).execute()

    # Create membership (upsert to handle re-invite)
    client.table("tenant_memberships").upsert(
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "role": role,
        },
        on_conflict="tenant_id,user_id",
    ).execute()

    # Mark token accepted
    client.table("invite_tokens").update({
        "status": "accepted",
        "accepted_at": _utcnow_iso(),
        "accepted_by": user_id,
    }).eq("token_id", token_id).execute()

    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "email": email,
        "role": role,
        "display_name": display_name or email.split("@")[0],
    }


def authenticate_user(
    email: str,
    password: str,
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Authenticate a user via email + password and resolve tenant membership."""
    client = _get_client()
    normalized_email = _normalize_email(email)
    requested_tenant = str(tenant_id or "").strip()

    if not normalized_email:
        raise ValueError("Correo invalido.")

    user_row = _load_user_by_email(client, normalized_email, allow_missing=True)
    if user_row is None:
        raise ValueError("Credenciales inválidas.")

    status = str(user_row.get("status", "active") or "active").strip()
    if status == "suspended":
        raise ValueError("Su cuenta está suspendida.")
    if status == "invited":
        raise ValueError("Debe aceptar su invitación antes de iniciar sesión.")
    if bool(user_row.get("password_reset_required")):
        raise ValueError("Debe usar un enlace de invitación reciente para definir su contraseña.")

    if not verify_password(password, str(user_row.get("password_hash", "") or "")):
        raise ValueError("Credenciales inválidas.")

    memberships = _list_memberships(client, str(user_row.get("user_id", "") or ""))
    if requested_tenant:
        memberships = [row for row in memberships if row["tenant_id"] == requested_tenant]
    if not memberships:
        raise ValueError("No tiene acceso al tenant solicitado.")
    if len(memberships) > 1:
        return {
            "requires_tenant_selection": True,
            "tenants": memberships,
            "user_id": str(user_row.get("user_id", "") or ""),
            "email": normalized_email,
            "display_name": str(user_row.get("display_name", "") or ""),
        }

    membership = memberships[0]
    return {
        "requires_tenant_selection": False,
        "tenant_id": membership["tenant_id"],
        "user_id": str(user_row.get("user_id", "") or ""),
        "role": membership["role"],
        "email": normalized_email,
        "display_name": str(user_row.get("display_name", "") or ""),
        "tenants": memberships,
    }


def list_invites(tenant_id: str, *, status: str | None = "pending") -> list[dict[str, Any]]:
    """List invite tokens for a tenant."""
    client = _get_client()
    query = client.table("invite_tokens").select("*").eq("tenant_id", tenant_id)
    if status:
        query = query.eq("status", status)
    result = query.order("created_at", desc=True).execute()
    return result.data or []


def revoke_invite(token_id: str) -> bool:
    """Revoke a pending invite."""
    client = _get_client()
    result = (
        client.table("invite_tokens")
        .update({"status": "revoked"})
        .eq("token_id", token_id)
        .eq("status", "pending")
        .execute()
    )
    return bool(result.data)


# ---------------------------------------------------------------------------
# User lifecycle
# ---------------------------------------------------------------------------

def suspend_user(tenant_id: str, user_id: str) -> dict[str, Any]:
    """Suspend a user within a tenant."""
    client = _get_client()
    # Verify membership exists
    membership = (
        client.table("tenant_memberships")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not membership or not membership.data:
        raise ValueError("El usuario no pertenece a este tenant.")

    client.table("users").update({"status": "suspended"}).eq("user_id", user_id).execute()
    return {"user_id": user_id, "status": "suspended"}


def reactivate_user(tenant_id: str, user_id: str) -> dict[str, Any]:
    """Reactivate a suspended user."""
    client = _get_client()
    membership = (
        client.table("tenant_memberships")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not membership or not membership.data:
        raise ValueError("El usuario no pertenece a este tenant.")

    client.table("users").update({"status": "active"}).eq("user_id", user_id).execute()
    return {"user_id": user_id, "status": "active"}


def delete_user_from_tenant(tenant_id: str, user_id: str) -> dict[str, Any]:
    """Remove a user from a tenant (delete membership)."""
    client = _get_client()
    client.table("tenant_memberships").delete().eq("tenant_id", tenant_id).eq("user_id", user_id).execute()
    # Also revoke any pending invites for this user's email
    user_result = client.table("users").select("email").eq("user_id", user_id).maybe_single().execute()
    if user_result and user_result.data and user_result.data.get("email"):
        client.table("invite_tokens").update({"status": "revoked"}).eq("tenant_id", tenant_id).eq("email", user_result.data["email"]).eq("status", "pending").execute()
    return {"user_id": user_id, "deleted": True}


# ---------------------------------------------------------------------------
# Tenant management
# ---------------------------------------------------------------------------

def list_tenants(*, include_members: bool = False) -> list[dict[str, Any]]:
    """List all tenants.  When *include_members* is True, each tenant dict
    gets a ``members`` list with ``{user_id, email, display_name}`` for
    every active membership."""
    client = _get_client()
    result = client.table("tenants").select("*").order("created_at", desc=True).execute()
    tenants = result.data or []
    if not include_members or not tenants:
        return tenants

    # Bulk-fetch all memberships with user data in one query.
    mem_result = (
        client.table("tenant_memberships")
        .select("tenant_id, user_id, users(email, display_name)")
        .execute()
    )
    # Group by tenant_id.
    members_by_tenant: dict[str, list[dict[str, str]]] = {}
    for m in mem_result.data or []:
        tid = m.get("tenant_id", "")
        user_data = m.get("users") or {}
        members_by_tenant.setdefault(tid, []).append({
            "user_id": m.get("user_id", ""),
            "email": user_data.get("email", ""),
            "display_name": user_data.get("display_name", ""),
        })
    for t in tenants:
        t["members"] = members_by_tenant.get(t.get("tenant_id", ""), [])
    return tenants


def create_tenant(display_name: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a new tenant."""
    client = _get_client()
    tenant_id = f"tenant_{secrets.token_hex(6)}"
    data: dict[str, Any] = {
        "tenant_id": tenant_id,
        "display_name": display_name,
        "status": "active",
    }
    if metadata:
        data["metadata"] = metadata
    client.table("tenants").insert(data).execute()
    return {"tenant_id": tenant_id, "display_name": display_name, "status": "active"}
