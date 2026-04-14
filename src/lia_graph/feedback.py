"""User feedback collection and storage.

Supabase is the production backend for Pipeline C.
Filesystem remains only for explicit test/dev path overrides.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_FEEDBACK_DIR = Path("artifacts/feedback")
ALLOWED_TAGS = frozenset({"precisa", "practica", "incompleta", "desactualizada", "confusa"})

_log = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _year_month() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year}_{now.month:02d}"


def _use_supabase(base_dir: Path) -> bool:
    from lia_contador.supabase_client import is_supabase_enabled, matches_default_storage_path

    if not matches_default_storage_path(base_dir, DEFAULT_FEEDBACK_DIR):
        return False
    return is_supabase_enabled()


@dataclass
class FeedbackRecord:
    trace_id: str
    session_id: str | None
    rating: int  # 1-5
    tenant_id: str = ""
    user_id: str = ""
    company_id: str = ""
    integration_id: str = ""
    tags: list[str] = field(default_factory=list)
    comment: str = ""
    vote: str = ""
    status: str = "submitted"
    source: str = "api"
    created_by: str = ""
    timestamp: str = ""
    docs_used: list[str] = field(default_factory=list)
    layer_contributions: dict[str, int] = field(default_factory=dict)
    pain_detected: str = ""
    task_detected: str = ""
    question_text: str = ""
    answer_text: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _utc_now_iso()
        self.rating = max(1, min(5, int(self.rating)))
        self.tags = [t for t in self.tags if t in ALLOWED_TAGS]
        normalized_vote = str(self.vote or "").strip().lower()
        if normalized_vote not in {"up", "down", "neutral"}:
            if self.rating >= 4:
                normalized_vote = "up"
            elif self.rating <= 2:
                normalized_vote = "down"
            else:
                normalized_vote = "neutral"
        self.vote = normalized_vote
        self.status = str(self.status or "submitted").strip() or "submitted"
        self.source = str(self.source or "api").strip() or "api"
        self.created_by = str(self.created_by or "").strip()
        self.tenant_id = str(self.tenant_id or "").strip()
        self.user_id = str(self.user_id or "").strip()
        self.company_id = str(self.company_id or "").strip()
        self.integration_id = str(self.integration_id or "").strip()
        self.question_text = str(self.question_text or "").strip()[:2000]
        self.answer_text = str(self.answer_text or "").strip()[:5000]

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "rating": self.rating,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "integration_id": self.integration_id,
            "tags": self.tags,
            "comment": self.comment,
            "vote": self.vote,
            "status": self.status,
            "source": self.source,
            "created_by": self.created_by,
            "timestamp": self.timestamp,
            "docs_used": self.docs_used,
            "layer_contributions": self.layer_contributions,
            "pain_detected": self.pain_detected,
            "task_detected": self.task_detected,
            "question_text": self.question_text,
            "answer_text": self.answer_text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeedbackRecord:
        return cls(
            trace_id=str(data.get("trace_id", "")),
            session_id=data.get("session_id"),
            rating=int(data.get("rating", 3)),
            tenant_id=str(data.get("tenant_id", "")),
            user_id=str(data.get("user_id", "")),
            company_id=str(data.get("company_id", "")),
            integration_id=str(data.get("integration_id", "")),
            tags=list(data.get("tags", [])),
            comment=str(data.get("comment", "")),
            vote=str(data.get("vote", "")),
            status=str(data.get("status", "submitted")),
            source=str(data.get("source", "api")),
            created_by=str(data.get("created_by", "")),
            timestamp=str(data.get("timestamp", "")),
            docs_used=list(data.get("docs_used", [])),
            layer_contributions=dict(data.get("layer_contributions", {})),
            pain_detected=str(data.get("pain_detected", "")),
            task_detected=str(data.get("task_detected", "")),
            question_text=str(data.get("question_text", "")),
            answer_text=str(data.get("answer_text", "")),
        )


# ---------------------------------------------------------------------------
# Filesystem implementation
# ---------------------------------------------------------------------------

def _fs_save_feedback(record: FeedbackRecord, *, base_dir: Path) -> Path:
    ym = _year_month()
    folder = base_dir / ym
    folder.mkdir(parents=True, exist_ok=True)
    safe_trace = record.trace_id.replace("/", "_").replace("..", "_")[:64]
    path = folder / f"{safe_trace}.json"
    path.write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _fs_load_feedback(trace_id: str, *, base_dir: Path) -> FeedbackRecord | None:
    safe_trace = trace_id.replace("/", "_").replace("..", "_")[:64]
    for ym_dir in sorted(base_dir.glob("*"), reverse=True):
        if not ym_dir.is_dir():
            continue
        path = ym_dir / f"{safe_trace}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return FeedbackRecord.from_dict(data)
            except (OSError, json.JSONDecodeError):
                continue
    return None


def _fs_list_feedback(*, base_dir: Path, limit: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for ym_dir in sorted(base_dir.glob("*"), reverse=True):
        if not ym_dir.is_dir():
            continue
        for path in sorted(ym_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                records.append(data)
            except (OSError, json.JSONDecodeError):
                continue
            if len(records) >= limit:
                return records
    return records


# ---------------------------------------------------------------------------
# Supabase implementation
# ---------------------------------------------------------------------------

def _sb_save_feedback(record: FeedbackRecord) -> None:
    from lia_contador.supabase_client import get_supabase_client
    client = get_supabase_client()
    client.table("feedback").upsert({
        "trace_id": record.trace_id,
        "session_id": record.session_id,
        "rating": record.rating,
        "tenant_id": record.tenant_id or "",
        "user_id": record.user_id or "",
        "company_id": record.company_id or "",
        "integration_id": record.integration_id or "",
        "tags": record.tags,
        "comment": record.comment,
        "vote": record.vote,
        "review_status": record.status,
        "source": record.source,
        "created_by": record.created_by or "",
        "docs_used": record.docs_used,
        "layer_contributions": record.layer_contributions,
        "pain_detected": record.pain_detected,
        "task_detected": record.task_detected,
        "question_text": record.question_text,
        "answer_text": record.answer_text,
        "updated_at": _utc_now_iso(),
    }, on_conflict="trace_id,tenant_id").execute()


def _sb_load_feedback(trace_id: str) -> FeedbackRecord | None:
    from lia_contador.supabase_client import get_supabase_client
    client = get_supabase_client()
    res = client.table("feedback").select("*").eq("trace_id", trace_id).limit(1).execute()
    if not res.data:
        return None
    row = res.data[0]
    return FeedbackRecord(
        trace_id=row["trace_id"],
        session_id=row.get("session_id"),
        rating=row["rating"],
        tenant_id=row.get("tenant_id", ""),
        user_id=row.get("user_id", ""),
        company_id=row.get("company_id", ""),
        integration_id=row.get("integration_id", ""),
        tags=list(row.get("tags", [])),
        comment=row.get("comment", ""),
        vote=row.get("vote", ""),
        status=row.get("review_status", "submitted"),
        source=row.get("source", "api"),
        created_by=row.get("created_by", ""),
        timestamp=str(row.get("created_at", "")),
        docs_used=list(row.get("docs_used", [])),
        layer_contributions=dict(row.get("layer_contributions", {})),
        pain_detected=row.get("pain_detected", ""),
        task_detected=row.get("task_detected", ""),
        question_text=row.get("question_text", ""),
        answer_text=row.get("answer_text", ""),
    )


def _sb_list_feedback(
    *,
    limit: int,
    tenant_id: str | None = None,
    user_id: str | None = None,
    company_id: str | None = None,
) -> list[dict[str, Any]]:
    from lia_contador.supabase_client import get_supabase_client
    client = get_supabase_client()
    query = client.table("feedback").select("*")
    if tenant_id:
        query = query.eq("tenant_id", tenant_id)
    if user_id:
        query = query.eq("user_id", user_id)
    if company_id:
        query = query.eq("company_id", company_id)
    res = query.order("created_at", desc=True).limit(limit).execute()
    records: list[dict[str, Any]] = []
    for row in res.data or []:
        records.append(_row_to_dict(row))
    return records


def _row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "trace_id": row["trace_id"],
        "session_id": row.get("session_id"),
        "rating": row["rating"],
        "tenant_id": row.get("tenant_id", ""),
        "user_id": row.get("user_id", ""),
        "company_id": row.get("company_id", ""),
        "integration_id": row.get("integration_id", ""),
        "tags": list(row.get("tags", [])),
        "comment": row.get("comment", ""),
        "vote": row.get("vote", ""),
        "status": row.get("review_status", "submitted"),
        "source": row.get("source", "api"),
        "created_by": row.get("created_by", ""),
        "timestamp": str(row.get("created_at", "")),
        "docs_used": list(row.get("docs_used", [])),
        "layer_contributions": dict(row.get("layer_contributions", {})),
        "pain_detected": row.get("pain_detected", ""),
        "task_detected": row.get("task_detected", ""),
        "question_text": row.get("question_text", ""),
        "answer_text": row.get("answer_text", ""),
    }


def _sb_update_feedback_comment(trace_id: str, comment: str, *, tenant_id: str) -> bool:
    from lia_contador.supabase_client import get_supabase_client
    client = get_supabase_client()
    query = client.table("feedback").update({
        "comment": comment[:500],
        "updated_at": _utc_now_iso(),
    }).eq("trace_id", trace_id)
    if tenant_id:
        query = query.eq("tenant_id", tenant_id)
    res = query.execute()
    return bool(res.data)


def _sb_list_feedback_for_admin(
    *,
    tenant_id: str | None = None,
    user_id: str | None = None,
    rating_min: int | None = None,
    rating_max: int | None = None,
    limit: int = 50,
    offset: int = 0,
    since: str | None = None,
) -> list[dict[str, Any]]:
    from lia_contador.supabase_client import get_supabase_client
    client = get_supabase_client()
    query = client.table("feedback").select("*")
    if tenant_id:
        query = query.eq("tenant_id", tenant_id)
    if user_id:
        query = query.eq("user_id", user_id)
    if rating_min is not None:
        query = query.gte("rating", rating_min)
    if rating_max is not None:
        query = query.lte("rating", rating_max)
    if since:
        query = query.gte("created_at", since)
    query = query.order("created_at", desc=True)
    if offset > 0 or limit != 50:
        query = query.range(offset, offset + limit - 1)
    else:
        query = query.limit(limit)
    res = query.execute()
    return [_row_to_dict(row) for row in (res.data or [])]


# ---------------------------------------------------------------------------
# Public API — dispatch based on backend
# ---------------------------------------------------------------------------

def save_feedback(
    record: FeedbackRecord,
    *,
    base_dir: Path = DEFAULT_FEEDBACK_DIR,
) -> Path:
    if _use_supabase(base_dir):
        _sb_save_feedback(record)
        return base_dir / "supabase" / f"{record.trace_id}.json"
    return _fs_save_feedback(record, base_dir=base_dir)


def load_feedback(
    trace_id: str,
    *,
    base_dir: Path = DEFAULT_FEEDBACK_DIR,
) -> FeedbackRecord | None:
    if _use_supabase(base_dir):
        return _sb_load_feedback(trace_id)
    return _fs_load_feedback(trace_id, base_dir=base_dir)


def list_feedback(
    *,
    base_dir: Path = DEFAULT_FEEDBACK_DIR,
    limit: int = 50,
    tenant_id: str | None = None,
    user_id: str | None = None,
    company_id: str | None = None,
) -> list[dict[str, Any]]:
    if _use_supabase(base_dir):
        return _sb_list_feedback(limit=limit, tenant_id=tenant_id, user_id=user_id, company_id=company_id)
    rows = _fs_list_feedback(base_dir=base_dir, limit=max(limit * 4, limit))
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if tenant_id and str(row.get("tenant_id", "")).strip() != tenant_id:
            continue
        if user_id and str(row.get("user_id", "")).strip() != user_id:
            continue
        if company_id and str(row.get("company_id", "")).strip() != company_id:
            continue
        filtered.append(row)
        if len(filtered) >= limit:
            break
    return filtered


def update_feedback_comment(
    trace_id: str,
    comment: str,
    *,
    tenant_id: str = "",
    base_dir: Path = DEFAULT_FEEDBACK_DIR,
) -> bool:
    if _use_supabase(base_dir):
        return _sb_update_feedback_comment(trace_id, comment, tenant_id=tenant_id)
    record = _fs_load_feedback(trace_id, base_dir=base_dir)
    if record is None:
        return False
    record.comment = str(comment or "").strip()[:500]
    _fs_save_feedback(record, base_dir=base_dir)
    return True


def list_feedback_for_admin(
    *,
    base_dir: Path = DEFAULT_FEEDBACK_DIR,
    tenant_id: str | None = None,
    user_id: str | None = None,
    rating_min: int | None = None,
    rating_max: int | None = None,
    limit: int = 50,
    offset: int = 0,
    since: str | None = None,
) -> list[dict[str, Any]]:
    if _use_supabase(base_dir):
        return _sb_list_feedback_for_admin(
            tenant_id=tenant_id,
            user_id=user_id,
            rating_min=rating_min,
            rating_max=rating_max,
            limit=limit,
            offset=offset,
            since=since,
        )
    rows = _fs_list_feedback(base_dir=base_dir, limit=max((offset + limit) * 2, 200))
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if tenant_id and str(row.get("tenant_id", "")).strip() != tenant_id:
            continue
        if user_id and str(row.get("user_id", "")).strip() != user_id:
            continue
        r = int(row.get("rating", 0))
        if rating_min is not None and r < rating_min:
            continue
        if rating_max is not None and r > rating_max:
            continue
        filtered.append(row)
    return filtered[offset : offset + limit]
