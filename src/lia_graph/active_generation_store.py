"""Active corpus generation persistence.

Supabase is the authoritative backend for active corpus/runtime state.
Filesystem storage remains only for non-product local tests/dev flows.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ACTIVE_GENERATION_PATH = Path("artifacts/runtime/active_index_generation.json")
_DEFAULT_KNOWLEDGE_CLASS_COUNTS = {
    "normative_base": 0,
    "interpretative_guidance": 0,
    "practica_erp": 0,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _use_supabase(path: Path) -> bool:
    from lia_contador.supabase_client import is_supabase_enabled, matches_default_storage_path

    if not matches_default_storage_path(path, DEFAULT_ACTIVE_GENERATION_PATH):
        return False
    return is_supabase_enabled()


@dataclass
class ActiveGenerationRecord:
    generation_id: str
    generated_at: str = ""
    activated_at: str = ""
    documents: int = 0
    chunks: int = 0
    countries: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    knowledge_class_counts: dict[str, int] = field(default_factory=dict)
    index_dir: str = ""
    is_active: bool = True

    def __post_init__(self) -> None:
        now = _utc_now_iso()
        if not self.generated_at:
            self.generated_at = now
        if not self.activated_at and self.is_active:
            self.activated_at = now
        self.generation_id = str(self.generation_id or "").strip()
        self.documents = max(0, int(self.documents or 0))
        self.chunks = max(0, int(self.chunks or 0))
        self.countries = [str(item).strip() for item in list(self.countries or []) if str(item).strip()]
        self.files = [str(item).strip() for item in list(self.files or []) if str(item).strip()]
        self.knowledge_class_counts = {
            key: max(0, int((self.knowledge_class_counts or {}).get(key) or 0))
            for key in _DEFAULT_KNOWLEDGE_CLASS_COUNTS
        }
        self.index_dir = str(self.index_dir or "").strip()
        self.is_active = bool(self.is_active)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_id": self.generation_id,
            "generated_at": self.generated_at,
            "activated_at": self.activated_at,
            "documents": self.documents,
            "chunks": self.chunks,
            "countries": list(self.countries),
            "files": list(self.files),
            "knowledge_class_counts": dict(self.knowledge_class_counts),
            "index_dir": self.index_dir,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActiveGenerationRecord":
        return cls(
            generation_id=str(data.get("generation_id", "")),
            generated_at=str(data.get("generated_at", "")),
            activated_at=str(data.get("activated_at", "")),
            documents=int(data.get("documents", 0) or 0),
            chunks=int(data.get("chunks", 0) or 0),
            countries=list(data.get("countries", [])),
            files=list(data.get("files", [])),
            knowledge_class_counts=dict(data.get("knowledge_class_counts") or {}),
            index_dir=str(data.get("index_dir", "")),
            is_active=bool(data.get("is_active", True)),
        )


def _fs_load_active_generation(path: Path) -> ActiveGenerationRecord | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return ActiveGenerationRecord.from_dict(payload)


def _fs_save_active_generation(record: ActiveGenerationRecord, *, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def _sb_load_active_generation(*, supabase_target: str = "production") -> ActiveGenerationRecord | None:
    from lia_contador.supabase_client import create_supabase_client_for_target

    client = create_supabase_client_for_target(supabase_target)
    result = (
        client.table("corpus_generations")
        .select("*")
        .eq("is_active", True)
        .order("activated_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return ActiveGenerationRecord.from_dict(dict(result.data[0]))


def _sb_save_active_generation(
    record: ActiveGenerationRecord,
    *,
    supabase_target: str = "production",
) -> None:
    from lia_contador.supabase_client import create_supabase_client_for_target

    client = create_supabase_client_for_target(supabase_target)
    activated_at = str(record.activated_at or "").strip()
    if not activated_at:
        activated_at = _utc_now_iso() if record.is_active else record.generated_at or _utc_now_iso()
    if record.is_active:
        client.table("corpus_generations").update({"is_active": False}).eq("is_active", True).neq(
            "generation_id", record.generation_id
        ).execute()
    client.table("corpus_generations").upsert(
        {
            "generation_id": record.generation_id,
            "generated_at": record.generated_at,
            "activated_at": activated_at,
            "documents": record.documents,
            "chunks": record.chunks,
            "countries": list(record.countries),
            "files": list(record.files),
            "knowledge_class_counts": dict(record.knowledge_class_counts),
            "index_dir": record.index_dir or "",
            "is_active": record.is_active,
        },
        on_conflict="generation_id",
    ).execute()


def load_active_generation(
    *,
    path: Path = DEFAULT_ACTIVE_GENERATION_PATH,
    supabase_target: str = "production",
) -> ActiveGenerationRecord | None:
    if _use_supabase(path):
        return _sb_load_active_generation(supabase_target=supabase_target)
    return _fs_load_active_generation(path)


def save_active_generation(
    record: ActiveGenerationRecord,
    *,
    path: Path = DEFAULT_ACTIVE_GENERATION_PATH,
    supabase_target: str = "production",
) -> Path:
    if _use_supabase(path):
        _sb_save_active_generation(record, supabase_target=supabase_target)
        return path.parent / "supabase" / f"{record.generation_id}.json"
    return _fs_save_active_generation(record, path=path)


__all__ = [
    "DEFAULT_ACTIVE_GENERATION_PATH",
    "ActiveGenerationRecord",
    "load_active_generation",
    "save_active_generation",
]
