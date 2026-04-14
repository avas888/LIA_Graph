"""Gemini API-based embeddings for semantic retrieval signal.

Uses gemini-embedding-001 (768 dims) via native Gemini API.
Falls back gracefully when GEMINI_API_KEY is not set.
No external SDK required — uses urllib.request (same as GeminiChatAdapter).

Config: config/embedding.json
"""

from __future__ import annotations

import functools
import json
import logging
import math
import os
import urllib.request
from pathlib import Path
from typing import Any

from .query_embedding_cache import (
    build_embedding_config_digest,
    load_query_embedding,
    normalize_query_text,
    save_query_embedding,
)

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path("config/embedding.json")
_config_cache: dict[str, Any] | None = None


def _load_config() -> dict[str, Any]:
    """Load embedding config, caching after first read."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    if _CONFIG_PATH.exists():
        _config_cache = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    else:
        _config_cache = {
            "model": "gemini-embedding-001",
            "dimensions": 768,
            "provider": "gemini",
            "api_key_env_var": "GEMINI_API_KEY",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "batch_size": 100,
            "cache_query_embeddings": True,
            "cache_maxsize": 256,
        }
    return _config_cache


def _get_api_key() -> str:
    """Get the API key from environment. Returns empty string if not set."""
    cfg = _load_config()
    return os.environ.get(cfg.get("api_key_env_var", "GEMINI_API_KEY"), "")


def _query_embedding_cache_identity() -> dict[str, Any]:
    cfg = _load_config()
    provider = str(cfg.get("provider") or "gemini").strip().lower()
    model = str(cfg.get("model") or "gemini-embedding-001").strip()
    dimensions = cfg.get("dimensions", 768)
    config_digest = build_embedding_config_digest(
        provider=provider,
        model=model,
        dimensions=dimensions,
        config_digest=json.dumps(
            {
                "base_url": cfg.get("base_url"),
                "batch_size": cfg.get("batch_size"),
                "api_key_env_var": cfg.get("api_key_env_var"),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    return {
        "provider": provider,
        "model": model,
        "dimensions": dimensions,
        "config_digest": config_digest,
    }


_warned_missing_key = False


def is_available() -> bool:
    """True if the embedding API key env var is set (non-empty)."""
    global _warned_missing_key
    key = _get_api_key()
    if not key and not _warned_missing_key:
        _warned_missing_key = True
        cfg = _load_config()
        env_var = cfg.get("api_key_env_var", "GEMINI_API_KEY")
        logger.warning(
            "⚠️  CAUTION: %s not found in environment. "
            "Hybrid semantic search DISABLED — falling back to FTS-only retrieval. "
            "Set %s in .env or environment to enable embeddings.",
            env_var, env_var,
        )
    return bool(key)


def _embed_single(text: str) -> list[float] | None:
    """Call Gemini embedContent for a single text."""
    api_key = _get_api_key()
    if not api_key:
        return None
    cfg = _load_config()
    model = cfg.get("model", "gemini-embedding-001")
    base_url = cfg.get("base_url", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    dims = cfg.get("dimensions", 768)

    payload: dict[str, Any] = {
        "model": f"models/{model}",
        "content": {"parts": [{"text": text}]},
    }
    if dims:
        payload["outputDimensionality"] = dims

    req = urllib.request.Request(
        url=f"{base_url}/models/{model}:embedContent?key={api_key}",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body.get("embedding", {}).get("values")
    except Exception:
        logger.warning("Gemini embedContent failed", exc_info=True)
        return None


def _embed_batch(texts: list[str]) -> list[list[float] | None]:
    """Call Gemini batchEmbedContents for multiple texts."""
    api_key = _get_api_key()
    if not api_key:
        return [None] * len(texts)
    cfg = _load_config()
    model = cfg.get("model", "gemini-embedding-001")
    base_url = cfg.get("base_url", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    dims = cfg.get("dimensions", 768)

    requests_list = []
    for text in texts:
        entry: dict[str, Any] = {
            "model": f"models/{model}",
            "content": {"parts": [{"text": text}]},
        }
        if dims:
            entry["outputDimensionality"] = dims
        requests_list.append(entry)

    payload = {"requests": requests_list}

    req = urllib.request.Request(
        url=f"{base_url}/models/{model}:batchEmbedContents?key={api_key}",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        embeddings = body.get("embeddings", [])
        return [e.get("values") for e in embeddings]
    except Exception:
        logger.warning("Gemini batchEmbedContents failed", exc_info=True)
        return [None] * len(texts)


def compute_embedding(text: str) -> list[float] | None:
    """Compute embedding for a single text via Gemini API."""
    return _embed_single(text)


def compute_embeddings_batch(texts: list[str]) -> list[list[float] | None]:
    """Compute embeddings for a batch of texts via Gemini API.

    Splits into sub-batches per config batch_size.
    """
    if not _get_api_key():
        return [None] * len(texts)
    cfg = _load_config()
    batch_size = cfg.get("batch_size", 100)

    results: list[list[float] | None] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch_result = _embed_batch(batch)
        results.extend(batch_result)
    return results


def get_query_embedding(text: str, *, allow_remote: bool = True) -> tuple[float, ...] | None:
    """LRU-cached query embedding backed by a durable store."""
    normalized = normalize_query_text(text)
    if not normalized:
        return None
    cache_identity = _query_embedding_cache_identity()
    return _cached_query_embedding(
        normalized,
        allow_remote,
        str(cache_identity.get("provider") or ""),
        str(cache_identity.get("model") or ""),
        cache_identity.get("dimensions"),
        str(cache_identity.get("config_digest") or ""),
    )


@functools.lru_cache(maxsize=512)
def _cached_query_embedding(
    text: str,
    allow_remote: bool,
    provider: str,
    model: str,
    dimensions: int | str | None,
    config_digest: str,
) -> tuple[float, ...] | None:
    cached = load_query_embedding(
        text,
        provider=provider,
        model=model,
        dimensions=dimensions,
        config_digest=config_digest,
    )
    if cached is not None:
        return cached
    if not allow_remote:
        return None
    vec = compute_embedding(text)
    if vec is None:
        return None
    save_query_embedding(
        text,
        vec,
        provider=provider,
        model=model,
        dimensions=dimensions,
        config_digest=config_digest,
    )
    return tuple(vec)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors (works for any dimension)."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# --- Deprecated stubs (kept for backward compatibility) ---


def enrich_chunk_records_with_embeddings(
    chunk_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deprecated: local model enrichment. Returns records unchanged."""
    return chunk_records


def load_embedding_index(path: Path) -> dict[str, list[float]]:
    """Deprecated: JSONL embedding index loader."""
    index: dict[str, list[float]] = {}
    if not path.exists():
        return index
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        doc_id = record.get("doc_id", "")
        vec = record.get("embedding_vector")
        if doc_id and isinstance(vec, list):
            index[doc_id] = vec
    return index
