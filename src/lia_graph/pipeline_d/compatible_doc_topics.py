"""Lookup helper for `config/compatible_doc_topics.json` (v5 §1.B).

Single source of truth for the narrow_topic → list[compatible_doc_topics]
mapping that the coherence gate uses to widen the `topic_key_matches`
acceptance set without lowering the 2-doc match threshold.

Mirrors the structure of `ingestion/article_secondary_topics.py` but at
the document-topic layer rather than the article-node layer.

Loaded lazily at first call; cached for the process lifetime; reset by
`reset_lookup_cache_for_tests()`. Degrades to empty dict on missing
config (preserves pre-§1.B coherence-gate behavior).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


_DEFAULT_CONFIG_PATH = Path("config/compatible_doc_topics.json")


def _resolve_config_path() -> Path:
    raw = os.getenv("LIA_COMPATIBLE_DOC_TOPICS_PATH", "").strip()
    return Path(raw) if raw else _DEFAULT_CONFIG_PATH


def _valid_topic_keys() -> frozenset[str]:
    """Lazy-load the canonical taxonomy keys for validation.

    Operator's binding rule (2026-04-26): "todo mapee a nuestra taxonomy
    base principal" — every narrow topic AND every compatible topic in
    the config MUST be a registered topic_taxonomy.json key.
    """
    try:
        from ..topic_taxonomy import iter_topic_taxonomy_entries
    except Exception as exc:  # noqa: BLE001
        print(
            f"[compatible_doc_topics] taxonomy import failed: {exc!r} — "
            "validation skipped.",
            file=sys.stderr,
        )
        return frozenset()
    try:
        return frozenset(e.key for e in iter_topic_taxonomy_entries())
    except Exception as exc:  # noqa: BLE001
        print(
            f"[compatible_doc_topics] taxonomy enumeration failed: "
            f"{exc!r} — validation skipped.",
            file=sys.stderr,
        )
        return frozenset()


def _load_lookup() -> dict[str, frozenset[str]]:
    """Return narrow_topic → frozenset[compatible_doc_topics]."""
    path = _resolve_config_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"[compatible_doc_topics] failed to parse {path}: {exc!r} — "
            "continuing without compatible-topic metadata.",
            file=sys.stderr,
        )
        return {}

    valid_topics = _valid_topic_keys()
    out: dict[str, frozenset[str]] = {}
    topics = data.get("topics") or {}
    if not isinstance(topics, dict):
        print(
            f"[compatible_doc_topics] {path} 'topics' is not an object — "
            "ignoring config.",
            file=sys.stderr,
        )
        return {}

    for narrow, entry in topics.items():
        if not isinstance(narrow, str) or not narrow.strip():
            continue
        narrow_key = narrow.strip()
        if valid_topics and narrow_key not in valid_topics:
            print(
                f"[compatible_doc_topics] narrow topic {narrow_key!r} not "
                "in topic_taxonomy.json — entry dropped.",
                file=sys.stderr,
            )
            continue
        if not isinstance(entry, dict):
            continue
        compatibles = entry.get("compatible_topics") or []
        if not isinstance(compatibles, list):
            continue
        cleaned: list[str] = []
        for t in compatibles:
            if not isinstance(t, str):
                continue
            key = t.strip()
            if not key:
                continue
            if valid_topics and key not in valid_topics:
                print(
                    f"[compatible_doc_topics] compatible_topic {key!r} for "
                    f"narrow {narrow_key!r} not in topic_taxonomy.json — "
                    "dropped.",
                    file=sys.stderr,
                )
                continue
            cleaned.append(key)
        if cleaned:
            out[narrow_key] = frozenset(cleaned)
    return out


_LOOKUP_CACHE: dict[str, frozenset[str]] | None = None


def get_compatible_topics(narrow_topic: str) -> frozenset[str]:
    """Return compatible doc-topics for ``narrow_topic`` (or empty set)."""
    global _LOOKUP_CACHE
    if _LOOKUP_CACHE is None:
        _LOOKUP_CACHE = _load_lookup()
    return _LOOKUP_CACHE.get(str(narrow_topic).strip(), frozenset())


def reset_lookup_cache_for_tests() -> None:
    """Test-only: clear the cached lookup."""
    global _LOOKUP_CACHE
    _LOOKUP_CACHE = None


__all__ = ["get_compatible_topics", "reset_lookup_cache_for_tests"]
