from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


DEFAULT_TOPIC_TAXONOMY_PATH = Path("config/topic_taxonomy.json")


@dataclass(frozen=True)
class TopicTaxonomyEntry:
    key: str
    label: str
    aliases: tuple[str, ...]
    ingestion_aliases: tuple[str, ...]
    legacy_document_topics: tuple[str, ...]
    allowed_path_prefixes: tuple[str, ...]
    vocabulary_status: str
    parent_key: str | None = None

    def all_aliases(self) -> tuple[str, ...]:
        ordered: list[str] = []
        for raw_value in (self.key, *self.aliases):
            value = str(raw_value).strip().lower()
            if value and value not in ordered:
                ordered.append(value)
        return tuple(ordered)

    def all_ingestion_aliases(self) -> tuple[str, ...]:
        ordered: list[str] = []
        for raw_value in (self.key, *self.aliases, *self.ingestion_aliases):
            value = str(raw_value).strip().lower()
            if value and value not in ordered:
                ordered.append(value)
        return tuple(ordered)


@dataclass(frozen=True)
class TopicTaxonomy:
    version: str
    entries: tuple[TopicTaxonomyEntry, ...]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_taxonomy_path() -> Path:
    raw_override = str(os.getenv("LIA_TOPIC_TAXONOMY_PATH", "") or "").strip()
    if raw_override:
        return Path(raw_override)
    candidate = DEFAULT_TOPIC_TAXONOMY_PATH
    if candidate.exists():
        return candidate
    return _repo_root() / DEFAULT_TOPIC_TAXONOMY_PATH


def _normalize_alias(value: str) -> str:
    return str(value or "").strip().lower()


@lru_cache(maxsize=1)
def load_topic_taxonomy() -> TopicTaxonomy:
    path = _resolve_taxonomy_path()
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_topics = payload.get("topics")
    if not isinstance(raw_topics, list) or not raw_topics:
        raise RuntimeError(f"Topic taxonomy is empty or invalid: {path}")

    entries: list[TopicTaxonomyEntry] = []
    keys_seen: set[str] = set()
    aliases_seen: dict[str, str] = {}
    for raw_entry in raw_topics:
        if not isinstance(raw_entry, dict):
            continue
        key = _normalize_alias(raw_entry.get("key"))
        if not key:
            continue
        if key in keys_seen:
            raise RuntimeError(f"Duplicate topic taxonomy key: {key}")
        entry = TopicTaxonomyEntry(
            key=key,
            label=str(raw_entry.get("label") or key),
            aliases=tuple(_normalize_alias(item) for item in list(raw_entry.get("aliases") or []) if _normalize_alias(item)),
            ingestion_aliases=tuple(
                _normalize_alias(item)
                for item in list(raw_entry.get("ingestion_aliases") or [])
                if _normalize_alias(item)
            ),
            legacy_document_topics=tuple(
                _normalize_alias(item)
                for item in list(raw_entry.get("legacy_document_topics") or [])
                if _normalize_alias(item)
            ),
            allowed_path_prefixes=tuple(
                str(item).strip().lower()
                for item in list(raw_entry.get("allowed_path_prefixes") or [])
                if str(item).strip()
            ),
            vocabulary_status=str(raw_entry.get("vocabulary_status") or "unassigned"),
            parent_key=_normalize_alias(raw_entry.get("parent_key")) or None,
        )
        keys_seen.add(entry.key)
        for alias in entry.all_aliases():
            owner = aliases_seen.get(alias)
            if owner is not None and owner != entry.key:
                raise RuntimeError(
                    f"Duplicate topic taxonomy alias {alias!r} for {entry.key!r} and {owner!r}"
                )
            aliases_seen[alias] = entry.key
        entries.append(entry)

    return TopicTaxonomy(
        version=str(payload.get("version") or "unversioned"),
        entries=tuple(entries),
    )


@lru_cache(maxsize=1)
def _entries_by_key() -> dict[str, TopicTaxonomyEntry]:
    taxonomy = load_topic_taxonomy()
    return {entry.key: entry for entry in taxonomy.entries}


@lru_cache(maxsize=1)
def _alias_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for entry in load_topic_taxonomy().entries:
        for alias in entry.all_aliases():
            mapping[alias] = entry.key
    return mapping


@lru_cache(maxsize=1)
def _children_by_parent() -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for entry in load_topic_taxonomy().entries:
        if not entry.parent_key:
            continue
        grouped.setdefault(entry.parent_key, []).append(entry.key)
    return {
        parent_key: tuple(sorted(children))
        for parent_key, children in grouped.items()
    }


def topic_taxonomy_version() -> str:
    return load_topic_taxonomy().version


def iter_topic_taxonomy_entries() -> tuple[TopicTaxonomyEntry, ...]:
    return load_topic_taxonomy().entries


def normalize_topic_key(topic: str | None) -> str | None:
    candidate = _normalize_alias(topic)
    if not candidate:
        return None
    return _alias_map().get(candidate)


def get_topic_taxonomy_entry(topic: str | None) -> TopicTaxonomyEntry | None:
    normalized = normalize_topic_key(topic)
    if normalized is None:
        return None
    return _entries_by_key().get(normalized)


def get_parent_topic_key(topic: str | None) -> str | None:
    entry = get_topic_taxonomy_entry(topic)
    if entry is None:
        return None
    return entry.parent_key


def get_child_topic_keys(topic: str | None) -> tuple[str, ...]:
    normalized = normalize_topic_key(topic)
    if normalized is None:
        return ()
    return _children_by_parent().get(normalized, ())


def iter_ingestion_topic_entries() -> tuple[TopicTaxonomyEntry, ...]:
    def sort_key(entry: TopicTaxonomyEntry) -> tuple[int, int, int, str]:
        alias_lengths = [len(alias.split("_")) for alias in entry.all_ingestion_aliases()]
        max_tokens = max(alias_lengths) if alias_lengths else 0
        max_length = max((len(alias) for alias in entry.all_ingestion_aliases()), default=0)
        is_parent = 1 if entry.parent_key is None else 0
        return (-max_tokens, -max_length, is_parent, entry.key)

    return tuple(sorted(load_topic_taxonomy().entries, key=sort_key))
