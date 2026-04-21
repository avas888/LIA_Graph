"""Taxonomy loader — Phase 1 of ingestfix-v2.

Read-only facade over ``config/subtopic_taxonomy.json`` (produced by
``subtopic_generationv1``). Every downstream seam (classifier PASO 4,
planner intent detection, backfill) imports from this module.

Public API:

- :func:`load_taxonomy(path=None) -> SubtopicTaxonomy` — reads the JSON file
  (default path = ``config/subtopic_taxonomy.json`` at repo root).
- :class:`SubtopicTaxonomy` — frozen dataclass carrying the parsed data +
  pre-built lookup indices.
- :func:`validate_taxonomy(data: dict) -> list[str]` — structural checks.
- :func:`normalize_alias(value: str) -> str` — shared slug normalizer.

Invariant I1 (alias breadth) is honored: callers resolve via ``aliases``
in addition to ``key`` and ``label``. The loader never narrows the alias
list it returns.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

__all__ = [
    "SubtopicEntry",
    "SubtopicTaxonomy",
    "load_taxonomy",
    "validate_taxonomy",
    "normalize_alias",
    "DEFAULT_TAXONOMY_PATH",
]


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_TAXONOMY_PATH = _REPO_ROOT / "config" / "subtopic_taxonomy.json"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def normalize_alias(value: str) -> str:
    """Lowercase + strip accents + collapse non-alphanumerics to ``_``.

    Used to make alias / key / label comparisons robust to accents and
    spacing differences between curator input and query text.
    """
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = stripped.lower()
    squashed = _SLUG_RE.sub("_", lowered).strip("_")
    return squashed


@dataclass(frozen=True)
class SubtopicEntry:
    """One subtopic row from ``config/subtopic_taxonomy.json``."""

    parent_topic: str
    key: str
    label: str
    aliases: tuple[str, ...]
    evidence_count: int
    curated_at: str
    curator: str

    def all_surface_forms(self) -> tuple[str, ...]:
        """Return ``key + label + aliases`` as a de-duplicated tuple.

        Honors Invariant I1 — the breadth of the alias list is preserved.
        """
        forms: list[str] = [self.key, self.label, *self.aliases]
        seen: set[str] = set()
        out: list[str] = []
        for form in forms:
            if not form:
                continue
            if form in seen:
                continue
            seen.add(form)
            out.append(form)
        return tuple(out)


@dataclass(frozen=True)
class SubtopicTaxonomy:
    """Parsed taxonomy with lookup indices.

    ``subtopics_by_parent`` is the primary map; ``lookup_by_key`` and
    ``lookup_by_alias`` are pre-built for fast O(1) resolution by planner /
    classifier.
    """

    version: str
    generated_from: str
    generated_at: str
    subtopics_by_parent: Mapping[str, tuple[SubtopicEntry, ...]]
    lookup_by_key: Mapping[tuple[str, str], SubtopicEntry] = field(
        default_factory=dict
    )
    lookup_by_alias: Mapping[str, SubtopicEntry] = field(default_factory=dict)

    def parents(self) -> tuple[str, ...]:
        """Return sorted tuple of parent-topic keys with subtopics."""
        return tuple(sorted(self.subtopics_by_parent))

    def total_entries(self) -> int:
        return sum(len(v) for v in self.subtopics_by_parent.values())

    def get_candidates_for(self, parent_topic: str) -> tuple[SubtopicEntry, ...]:
        """Return subtopic candidates for a parent topic (empty if none)."""
        return self.subtopics_by_parent.get(parent_topic, ())

    def resolve_alias(self, alias: str) -> SubtopicEntry | None:
        """Resolve an alias / key / label to a :class:`SubtopicEntry`.

        Matching is normalized via :func:`normalize_alias`. When a surface
        form collides across parents, the first insertion wins — callers
        that need parent-aware resolution should use
        :meth:`resolve_within_parent` instead.
        """
        if not alias:
            return None
        normalized = normalize_alias(alias)
        return self.lookup_by_alias.get(normalized)

    def resolve_within_parent(
        self, alias: str, parent_topic: str
    ) -> SubtopicEntry | None:
        """Resolve an alias restricted to a specific parent topic."""
        normalized = normalize_alias(alias)
        if not normalized:
            return None
        for entry in self.subtopics_by_parent.get(parent_topic, ()):
            for form in entry.all_surface_forms():
                if normalize_alias(form) == normalized:
                    return entry
        return None


def validate_taxonomy(data: Any) -> list[str]:
    """Structural validation of a parsed taxonomy dict.

    Returns a list of human-readable error messages; empty list == valid.
    Does NOT mutate ``data``. Warnings (e.g. alias collisions across
    parents) are intentionally NOT errors — see the docstring for the
    breadth policy rationale.
    """
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["taxonomy must be a JSON object"]

    for required in ("version", "subtopics"):
        if required not in data:
            errors.append(f"missing required field '{required}'")

    subtopics = data.get("subtopics")
    if subtopics is None:
        return errors
    if not isinstance(subtopics, dict):
        errors.append("'subtopics' must be a JSON object keyed by parent_topic")
        return errors

    for parent_topic, entries in subtopics.items():
        if not isinstance(parent_topic, str) or not parent_topic:
            errors.append(f"invalid parent_topic key: {parent_topic!r}")
            continue
        if not isinstance(entries, list):
            errors.append(
                f"subtopics[{parent_topic}] must be a list, got {type(entries).__name__}"
            )
            continue
        seen_keys: set[str] = set()
        for idx, entry in enumerate(entries):
            prefix = f"subtopics[{parent_topic}][{idx}]"
            if not isinstance(entry, dict):
                errors.append(f"{prefix} must be an object")
                continue
            for field_name in ("key", "label"):
                if not entry.get(field_name):
                    errors.append(f"{prefix} missing required field '{field_name}'")
            key = entry.get("key")
            if isinstance(key, str) and key:
                if key in seen_keys:
                    errors.append(
                        f"{prefix} duplicate key '{key}' within parent '{parent_topic}'"
                    )
                seen_keys.add(key)
            aliases = entry.get("aliases", [])
            if aliases is not None and not isinstance(aliases, list):
                errors.append(f"{prefix} 'aliases' must be a list if present")
    return errors


def _build_lookup_indices(
    subtopics_by_parent: Mapping[str, tuple[SubtopicEntry, ...]],
) -> tuple[
    dict[tuple[str, str], SubtopicEntry],
    dict[str, SubtopicEntry],
]:
    by_key: dict[tuple[str, str], SubtopicEntry] = {}
    by_alias: dict[str, SubtopicEntry] = {}
    for parent, entries in subtopics_by_parent.items():
        for entry in entries:
            by_key[(parent, entry.key)] = entry
            for form in entry.all_surface_forms():
                normalized = normalize_alias(form)
                if not normalized:
                    continue
                # First insertion wins — breadth policy preserves all aliases
                # on the entry itself; the lookup just breaks ties.
                by_alias.setdefault(normalized, entry)
    return by_key, by_alias


def load_taxonomy(path: Path | None = None) -> SubtopicTaxonomy:
    """Read the taxonomy JSON and return an immutable :class:`SubtopicTaxonomy`.

    Raises :class:`ValueError` with line number context when the JSON is
    malformed, and :class:`ValueError` with the accumulated validation
    errors when the structure is wrong.
    """
    target = Path(path) if path is not None else DEFAULT_TAXONOMY_PATH
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"subtopic taxonomy not found at {target}; run promote_subtopic_decisions "
            "to generate it"
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"subtopic taxonomy at {target} is not valid JSON "
            f"(line {exc.lineno}, col {exc.colno}): {exc.msg}"
        ) from exc

    errors = validate_taxonomy(data)
    if errors:
        joined = "; ".join(errors[:10])
        more = f" (+{len(errors) - 10} more)" if len(errors) > 10 else ""
        raise ValueError(f"subtopic taxonomy invalid: {joined}{more}")

    subtopics_by_parent: dict[str, tuple[SubtopicEntry, ...]] = {}
    for parent_topic, entries in data.get("subtopics", {}).items():
        parsed: list[SubtopicEntry] = []
        for entry in entries:
            aliases_raw = entry.get("aliases") or ()
            parsed.append(
                SubtopicEntry(
                    parent_topic=parent_topic,
                    key=entry["key"],
                    label=entry["label"],
                    aliases=tuple(aliases_raw),
                    evidence_count=int(entry.get("evidence_count", 0) or 0),
                    curated_at=str(entry.get("curated_at", "") or ""),
                    curator=str(entry.get("curator", "") or ""),
                )
            )
        subtopics_by_parent[parent_topic] = tuple(parsed)

    by_key, by_alias = _build_lookup_indices(subtopics_by_parent)
    return SubtopicTaxonomy(
        version=str(data["version"]),
        generated_from=str(data.get("generated_from", "") or ""),
        generated_at=str(data.get("generated_at", "") or ""),
        subtopics_by_parent=subtopics_by_parent,
        lookup_by_key=by_key,
        lookup_by_alias=by_alias,
    )
