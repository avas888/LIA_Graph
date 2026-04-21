"""Login audit trail — records every authentication attempt."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

_log = logging.getLogger(__name__)

_MAX_USER_AGENT_LEN = 512
_MAX_IP_LEN = 45  # IPv6 max length


def _get_client() -> Any:
    from .supabase_client import get_supabase_client
    client = get_supabase_client()
    if client is None:
        raise RuntimeError("Supabase client not available.")
    return client


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_login_event(
    *,
    email: str,
    status: str,
    user_id: str | None = None,
    tenant_id: str | None = None,
    ip_address: str = "",
    user_agent: str = "",
    failure_reason: str | None = None,
) -> None:
    """Record a login attempt. Fire-and-forget — errors are logged, never raised."""
    try:
        client = _get_client()
        safe_ip = str(ip_address or "").strip()[:_MAX_IP_LEN]
        safe_ua = str(user_agent or "").strip()[:_MAX_USER_AGENT_LEN]
        safe_email = str(email or "").strip().lower()

        client.table("login_events").insert({
            "email": safe_email,
            "status": status,
            "user_id": user_id or None,
            "tenant_id": tenant_id or None,
            "ip_address": safe_ip,
            "user_agent": safe_ua,
            "failure_reason": failure_reason if status == "failure" else None,
        }).execute()

        if status == "success" and user_id:
            client.table("users").update({
                "last_login_at": _utcnow_iso(),
            }).eq("user_id", user_id).execute()

    except Exception:
        _log.warning("login_audit: failed to record login event", exc_info=True)


def query_recent_logins(
    *,
    tenant_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return recent login events, optionally scoped to a tenant."""
    client = _get_client()
    query = (
        client.table("login_events")
        .select("email, user_id, tenant_id, status, failure_reason, ip_address, created_at")
        .order("created_at", desc=True)
        .limit(min(max(1, limit), 500))
    )
    if tenant_id:
        query = query.eq("tenant_id", tenant_id)
    result = query.execute()
    return list(result.data or [])


def query_user_activity_stats(
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Build per-user activity stats combining login_events + chat_runs."""
    client = _get_client()

    login_query = (
        client.table("login_events")
        .select("user_id, email, status, created_at")
        .eq("status", "success")
        .order("created_at", desc=True)
        .limit(2000)
    )
    if tenant_id:
        login_query = login_query.eq("tenant_id", tenant_id)
    login_rows = list((login_query.execute()).data or [])

    runs_query = (
        client.table("chat_runs")
        .select("user_id, created_at")
        .order("created_at", desc=True)
        .limit(5000)
    )
    if tenant_id:
        runs_query = runs_query.eq("tenant_id", tenant_id)
    runs_rows = list((runs_query.execute()).data or [])

    users_query = client.table("users").select("user_id, email, display_name, last_login_at")
    if tenant_id:
        member_query = (
            client.table("tenant_memberships")
            .select("user_id")
            .eq("tenant_id", tenant_id)
        )
        member_rows = list((member_query.execute()).data or [])
        member_ids = [r["user_id"] for r in member_rows if r.get("user_id")]
        if member_ids:
            users_query = users_query.in_("user_id", member_ids)
        else:
            users_query = users_query.eq("user_id", "__none__")
    users_rows = list((users_query.execute()).data or [])
    users_map: dict[str, dict[str, str]] = {}
    for u in users_rows:
        uid = str(u.get("user_id", "") or "").strip()
        if uid:
            users_map[uid] = {
                "email": str(u.get("email", "") or ""),
                "display_name": str(u.get("display_name", "") or ""),
                "last_login_at": str(u.get("last_login_at", "") or ""),
            }

    login_counts: dict[str, int] = {}
    for row in login_rows:
        uid = str(row.get("user_id", "") or "").strip()
        if uid:
            login_counts[uid] = login_counts.get(uid, 0) + 1

    interaction_counts: dict[str, int] = {}
    last_interaction: dict[str, str] = {}
    for row in runs_rows:
        uid = str(row.get("user_id", "") or "").strip()
        if uid:
            interaction_counts[uid] = interaction_counts.get(uid, 0) + 1
            if uid not in last_interaction:
                last_interaction[uid] = str(row.get("created_at", "") or "")

    all_user_ids = set(login_counts) | set(interaction_counts) | set(users_map)
    user_stats: list[dict[str, Any]] = []
    for uid in sorted(all_user_ids):
        info = users_map.get(uid, {})
        user_stats.append({
            "user_id": uid,
            "email": info.get("email", ""),
            "display_name": info.get("display_name", ""),
            "login_count": login_counts.get(uid, 0),
            "last_login_at": info.get("last_login_at", ""),
            "interaction_count": interaction_counts.get(uid, 0),
            "last_interaction_at": last_interaction.get(uid, ""),
        })
    user_stats.sort(key=lambda s: s["interaction_count"], reverse=True)

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    seven_days_ago = (now - timedelta(days=7)).isoformat()

    logins_today = sum(
        1 for r in login_rows
        if str(r.get("created_at", "") or "") >= today_start
    )
    active_users_7d = len({
        str(r.get("user_id", "") or "").strip()
        for r in login_rows
        if str(r.get("created_at", "") or "") >= seven_days_ago
        and str(r.get("user_id", "") or "").strip()
    })
    interactions_7d = sum(
        1 for r in runs_rows
        if str(r.get("created_at", "") or "") >= seven_days_ago
    )

    return {
        "recent_logins": [],
        "user_stats": user_stats,
        "summary": {
            "logins_today": logins_today,
            "active_users_7d": active_users_7d,
            "total_interactions_7d": interactions_7d,
        },
    }
