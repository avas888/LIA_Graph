"""Lightweight persisted jobs for async/admin workflows."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

DEFAULT_JOBS_DIR = Path("artifacts/jobs/runtime")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class JobRecord:
    job_id: str
    job_type: str
    status: str = "queued"
    tenant_id: str = ""
    user_id: str = ""
    company_id: str = ""
    request_payload: dict[str, Any] = field(default_factory=dict)
    result_payload: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    attempts: int = 0
    created_at: str = ""
    updated_at: str = ""
    completed_at: str = ""

    def __post_init__(self) -> None:
        if not self.job_id:
            self.job_id = uuid4().hex
        now = _utc_now_iso()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = self.created_at
        self.job_type = str(self.job_type or "").strip() or "generic"
        self.status = str(self.status or "").strip() or "queued"
        self.request_payload = dict(self.request_payload or {})
        self.result_payload = dict(self.result_payload or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "request_payload": dict(self.request_payload),
            "result_payload": dict(self.result_payload),
            "error": self.error,
            "attempts": self.attempts,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at or None,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobRecord":
        return cls(**dict(payload))


def _job_path(base_dir: Path, job_id: str) -> Path:
    safe = str(job_id or "").replace("/", "_").replace("..", "_")[:128]
    return base_dir / f"{safe}.json"


def create_job(
    *,
    job_type: str,
    tenant_id: str = "",
    user_id: str = "",
    company_id: str = "",
    request_payload: dict[str, Any] | None = None,
    base_dir: Path = DEFAULT_JOBS_DIR,
) -> JobRecord:
    job = JobRecord(
        job_id="",
        job_type=job_type,
        tenant_id=tenant_id,
        user_id=user_id,
        company_id=company_id,
        request_payload=dict(request_payload or {}),
    )
    base_dir.mkdir(parents=True, exist_ok=True)
    _job_path(base_dir, job.job_id).write_text(json.dumps(job.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return job


def load_job(job_id: str, *, base_dir: Path = DEFAULT_JOBS_DIR) -> JobRecord | None:
    path = _job_path(base_dir, job_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return JobRecord.from_dict(payload)


def update_job(
    job_id: str,
    *,
    status: str,
    result_payload: dict[str, Any] | None = None,
    error: str = "",
    attempts: int | None = None,
    base_dir: Path = DEFAULT_JOBS_DIR,
) -> JobRecord | None:
    existing = load_job(job_id, base_dir=base_dir)
    if existing is None:
        return None
    existing.status = str(status or "").strip() or existing.status
    existing.updated_at = _utc_now_iso()
    existing.result_payload = dict(result_payload or existing.result_payload)
    existing.error = str(error or "").strip()
    if attempts is not None:
        existing.attempts = max(0, int(attempts))
    if existing.status in {"completed", "failed", "cancelled"}:
        existing.completed_at = existing.updated_at
    _job_path(base_dir, job_id).write_text(json.dumps(existing.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return existing


def list_jobs(
    *,
    tenant_id: str | None = None,
    limit: int = 100,
    base_dir: Path = DEFAULT_JOBS_DIR,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(base_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if tenant_id and str(payload.get("tenant_id") or "").strip() != tenant_id:
            continue
        rows.append(payload)
        if len(rows) >= max(1, int(limit)):
            break
    return rows

