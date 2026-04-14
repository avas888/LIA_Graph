"""Filesystem cache for query embeddings."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_CACHE_DIR = Path("artifacts/query_embedding_cache")


def normalize_query_text(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def build_embedding_config_digest(
    *,
    provider: str,
    model: str,
    dimensions: int | str | None,
    config_digest: str,
) -> str:
    payload = json.dumps(
        {
            "provider": str(provider or "").strip().lower(),
            "model": str(model or "").strip(),
            "dimensions": int(dimensions or 0),
            "config_digest": str(config_digest or "").strip(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_path(*, query_text: str, config_digest: str) -> Path:
    digest = hashlib.sha256(f"{normalize_query_text(query_text)}::{config_digest}".encode("utf-8")).hexdigest()
    return _CACHE_DIR / f"{digest}.json"


def load_query_embedding(*, query_text: str, config_digest: str) -> list[float] | None:
    path = _cache_path(query_text=query_text, config_digest=config_digest)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    values = payload.get("embedding")
    if not isinstance(values, list):
        return None
    try:
        return [float(item) for item in values]
    except (TypeError, ValueError):
        return None


def save_query_embedding(*, query_text: str, config_digest: str, embedding: list[float]) -> Path:
    path = _cache_path(query_text=query_text, config_digest=config_digest)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "query_text": normalize_query_text(query_text),
        "config_digest": config_digest,
        "embedding": [float(item) for item in embedding],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

