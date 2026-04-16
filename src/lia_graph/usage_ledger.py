"""Tenant/user/company usage events and lightweight rollups."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .instrumentation import normalize_token_usage

DEFAULT_USAGE_DIR = Path("artifacts/usage")

_log = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _year_month() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year}_{now.month:02d}"


def _use_supabase(base_dir: Path) -> bool:
    from .supabase_client import is_supabase_enabled, matches_default_storage_path

    if not matches_default_storage_path(base_dir, DEFAULT_USAGE_DIR):
        return False
    return is_supabase_enabled()


@dataclass
class UsageEvent:
    event_id: str
    event_type: str
    endpoint: str
    tenant_id: str
    user_id: str = ""
    company_id: str = ""
    session_id: str = ""
    trace_id: str = ""
    run_id: str = ""
    integration_id: str = ""
    provider: str = ""
    model: str = ""
    usage_source: str = "none"
    billable: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = uuid4().hex
        if not self.created_at:
            self.created_at = _utc_now_iso()
        normalized_usage = normalize_token_usage(
            {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.total_tokens,
                "source": self.usage_source,
            }
        )
        self.input_tokens = int(normalized_usage.get("input_tokens") or 0)
        self.output_tokens = int(normalized_usage.get("output_tokens") or 0)
        self.total_tokens = int(normalized_usage.get("total_tokens") or 0)
        self.usage_source = str(normalized_usage.get("source") or "none").strip() or "none"
        self.event_type = str(self.event_type or "").strip() or "usage"
        self.endpoint = str(self.endpoint or "").strip() or "/api/chat"
        self.tenant_id = str(self.tenant_id or "").strip() or "public"
        self.user_id = str(self.user_id or "").strip()
        self.company_id = str(self.company_id or "").strip()
        self.session_id = str(self.session_id or "").strip()
        self.trace_id = str(self.trace_id or "").strip()
        self.run_id = str(self.run_id or "").strip()
        self.integration_id = str(self.integration_id or "").strip()
        self.provider = str(self.provider or "").strip()
        self.model = str(self.model or "").strip()
        self.billable = bool(self.billable)
        self.metadata = dict(self.metadata or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "endpoint": self.endpoint,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "integration_id": self.integration_id,
            "provider": self.provider,
            "model": self.model,
            "usage_source": self.usage_source,
            "billable": self.billable,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UsageEvent":
        return cls(
            event_id=str(payload.get("event_id", "")),
            event_type=str(payload.get("event_type", "")),
            endpoint=str(payload.get("endpoint", "")),
            tenant_id=str(payload.get("tenant_id", "")),
            user_id=str(payload.get("user_id", "")),
            company_id=str(payload.get("company_id", "")),
            session_id=str(payload.get("session_id", "")),
            trace_id=str(payload.get("trace_id", "")),
            run_id=str(payload.get("run_id", "")),
            integration_id=str(payload.get("integration_id", "")),
            provider=str(payload.get("provider", "")),
            model=str(payload.get("model", "")),
            usage_source=str(payload.get("usage_source", "")),
            billable=bool(payload.get("billable", False)),
            input_tokens=int(payload.get("input_tokens", 0) or 0),
            output_tokens=int(payload.get("output_tokens", 0) or 0),
            total_tokens=int(payload.get("total_tokens", 0) or 0),
            metadata=dict(payload.get("metadata") or {}),
            created_at=str(payload.get("created_at", "")),
        )


def _fs_save_event(event: UsageEvent, *, base_dir: Path) -> Path:
    folder = base_dir / _year_month()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{event.event_id}.json"
    path.write_text(json.dumps(event.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _iter_fs_events(*, base_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ym_dir in sorted(base_dir.glob("*"), reverse=True):
        if not ym_dir.is_dir():
            continue
        for path in sorted(ym_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _sb_save_event(event: UsageEvent) -> None:
    from .supabase_client import get_supabase_client

    client = get_supabase_client()
    client.table("usage_events").insert(event.to_dict()).execute()


def _sb_list_events(
    *,
    tenant_id: str | None,
    user_id: str | None,
    company_id: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    from .supabase_client import get_supabase_client

    client = get_supabase_client()
    query = client.table("usage_events").select("*").order("created_at", desc=True).limit(limit)
    if tenant_id:
        query = query.eq("tenant_id", tenant_id)
    if user_id:
        query = query.eq("user_id", user_id)
    if company_id:
        query = query.eq("company_id", company_id)
    result = query.execute()
    return [dict(row) for row in (result.data or [])]


def save_usage_event(event: UsageEvent, *, base_dir: Path = DEFAULT_USAGE_DIR) -> Path:
    if _use_supabase(base_dir):
        _sb_save_event(event)
        return base_dir / "supabase" / f"{event.event_id}.json"
    return _fs_save_event(event, base_dir=base_dir)


def list_usage_events(
    *,
    base_dir: Path = DEFAULT_USAGE_DIR,
    tenant_id: str | None = None,
    user_id: str | None = None,
    company_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    rows = (
        _sb_list_events(tenant_id=tenant_id, user_id=user_id, company_id=company_id, limit=limit)
        if _use_supabase(base_dir)
        else _iter_fs_events(base_dir=base_dir)
    )
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if tenant_id and str(row.get("tenant_id", "")).strip() != tenant_id:
            continue
        if user_id and str(row.get("user_id", "")).strip() != user_id:
            continue
        if company_id and str(row.get("company_id", "")).strip() != company_id:
            continue
        filtered.append(dict(row))
        if len(filtered) >= limit:
            break
    return filtered


def summarize_usage(
    *,
    base_dir: Path = DEFAULT_USAGE_DIR,
    tenant_id: str | None = None,
    user_id: str | None = None,
    company_id: str | None = None,
    group_by: str = "tenant_id",
    limit: int = 500,
) -> dict[str, Any]:
    rows = list_usage_events(
        base_dir=base_dir,
        tenant_id=tenant_id,
        user_id=user_id,
        company_id=company_id,
        limit=limit,
    )
    group_field = str(group_by or "tenant_id").strip() or "tenant_id"
    allowed_group_fields = {
        "tenant_id",
        "user_id",
        "company_id",
        "model",
        "provider",
        "endpoint",
        "event_type",
        "billable",
    }
    if group_field not in allowed_group_fields:
        group_field = "tenant_id"

    grouped: dict[str, dict[str, Any]] = {}
    totals = {
        "events": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "billable_events": 0,
    }
    for row in rows:
        key = str(row.get(group_field, "")).strip() or "(unknown)"
        bucket = grouped.setdefault(
            key,
            {
                "group": key,
                "events": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "billable_events": 0,
            },
        )
        bucket["events"] += 1
        bucket["input_tokens"] += int(row.get("input_tokens", 0) or 0)
        bucket["output_tokens"] += int(row.get("output_tokens", 0) or 0)
        bucket["total_tokens"] += int(row.get("total_tokens", 0) or 0)
        bucket["billable_events"] += 1 if bool(row.get("billable")) else 0

        totals["events"] += 1
        totals["input_tokens"] += int(row.get("input_tokens", 0) or 0)
        totals["output_tokens"] += int(row.get("output_tokens", 0) or 0)
        totals["total_tokens"] += int(row.get("total_tokens", 0) or 0)
        totals["billable_events"] += 1 if bool(row.get("billable")) else 0

    groups = sorted(grouped.values(), key=lambda item: (-int(item["total_tokens"]), str(item["group"])))
    return {
        "filters": {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "company_id": company_id,
            "group_by": group_field,
            "limit": limit,
        },
        "totals": totals,
        "groups": groups,
        "rows": rows[: min(50, len(rows))],
    }
