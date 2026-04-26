"""Lookup helper for `config/article_secondary_topics.json` (v5 §1.A).

Single source of truth for the article_id → list[secondary_topics] mapping
that the loader writes onto :ArticleNode props in Falkor.

Loaded at module import; the file is small (a few hundred entries max) and
the lookup is per-article during ingest. If the file is missing or invalid,
the lookup degrades to "no secondary topics" (returns empty tuple) — the
loader keeps writing canonical-topic-only ArticleNodes, which is the
pre-§1.A behavior. No silent failure modes.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


_DEFAULT_CONFIG_PATH = Path("config/article_secondary_topics.json")


def _resolve_config_path() -> Path:
    raw = os.getenv("LIA_ARTICLE_SECONDARY_TOPICS_PATH", "").strip()
    return Path(raw) if raw else _DEFAULT_CONFIG_PATH


def _valid_topic_keys() -> frozenset[str]:
    """Lazy-load the canonical taxonomy keys from `topic_taxonomy.json`.

    Operator's binding rule (2026-04-26): "todo mapee a nuestra taxonomy
    base principal" — every primary/secondary topic referenced in
    `article_secondary_topics.json` MUST be a registered taxonomy key.
    Unknown topics get dropped with a stderr warning so the typo is
    visible but ingestion doesn't crash on it.
    """
    try:
        from ..topic_taxonomy import iter_topic_taxonomy_entries
    except Exception as exc:  # noqa: BLE001 — degrade if taxonomy lookup unavailable
        print(
            f"[article_secondary_topics] taxonomy import failed: {exc!r} — "
            "validation skipped.",
            file=sys.stderr,
        )
        return frozenset()
    try:
        return frozenset(e.key for e in iter_topic_taxonomy_entries())
    except Exception as exc:  # noqa: BLE001
        print(
            f"[article_secondary_topics] taxonomy enumeration failed: {exc!r} — "
            "validation skipped.",
            file=sys.stderr,
        )
        return frozenset()


def _load_lookup() -> dict[str, tuple[str, ...]]:
    """Read the JSON config and return article_id → tuple[secondary_topics].

    Tuple is always non-empty for entries we materialize — empty entries are
    skipped so callers never have to distinguish "no entry" from "entry
    with empty list" (both behave identically: no secondary topic).

    On any error (missing file, malformed JSON, non-list secondary_topics),
    we log to stderr and return an empty dict. The loader then writes
    canonical-topic-only nodes — same as pre-§1.A.

    Topic-key validation against the canonical taxonomy: any
    `secondary_topic` not registered in `topic_taxonomy.json` is dropped
    with a stderr warning. Operator directive 2026-04-26.
    """
    path = _resolve_config_path()
    if not path.exists():
        # Quietly OK — pre-§1.A behavior, no nag.
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"[article_secondary_topics] failed to parse {path}: {exc!r} — "
            "continuing without secondary-topic metadata.",
            file=sys.stderr,
        )
        return {}

    valid_topics = _valid_topic_keys()

    out: dict[str, tuple[str, ...]] = {}
    entries = data.get("articles") or []
    if not isinstance(entries, list):
        print(
            f"[article_secondary_topics] {path} 'articles' is not a list — "
            "ignoring config.",
            file=sys.stderr,
        )
        return {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        aid = str(entry.get("article_id") or "").strip()
        secondary = entry.get("secondary_topics") or []
        primary = str(entry.get("primary_topic") or "").strip()
        if not aid or not isinstance(secondary, list):
            continue
        # Validate primary_topic against the taxonomy (warn-only — primary
        # is informational here; the canonical owner is computed elsewhere
        # from the doc's topic). Skip the warning if the taxonomy lookup
        # itself failed (valid_topics is empty in that case).
        if valid_topics and primary and primary not in valid_topics:
            print(
                f"[article_secondary_topics] entry article_id={aid!r}: "
                f"primary_topic={primary!r} is not in topic_taxonomy.json — "
                "fix the typo or add the topic.",
                file=sys.stderr,
            )
        cleaned: list[str] = []
        for t in secondary:
            if not isinstance(t, str):
                continue
            key = t.strip()
            if not key:
                continue
            if valid_topics and key not in valid_topics:
                print(
                    f"[article_secondary_topics] entry article_id={aid!r}: "
                    f"secondary_topic={key!r} is not in topic_taxonomy.json — "
                    "dropped.",
                    file=sys.stderr,
                )
                continue
            cleaned.append(key)
        if cleaned:
            out[aid] = tuple(cleaned)
    return out


# Cached on first access; reset by `reset_lookup_cache_for_tests()`.
_LOOKUP_CACHE: dict[str, tuple[str, ...]] | None = None


def get_secondary_topics(article_id: str) -> tuple[str, ...]:
    """Return the (possibly empty) tuple of secondary topics for an article.

    Pure function modulo the lazy import of the JSON config. Safe to call
    in hot paths.
    """
    global _LOOKUP_CACHE
    if _LOOKUP_CACHE is None:
        _LOOKUP_CACHE = _load_lookup()
    return _LOOKUP_CACHE.get(str(article_id).strip(), ())


def reset_lookup_cache_for_tests() -> None:
    """Test-only: force the next `get_secondary_topics` call to re-read.

    Used by tests that monkey-patch the env to point at a fixture file.
    """
    global _LOOKUP_CACHE
    _LOOKUP_CACHE = None


__all__ = [
    "get_secondary_topics",
    "reset_lookup_cache_for_tests",
]
