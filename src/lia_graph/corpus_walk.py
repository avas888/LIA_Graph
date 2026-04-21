"""Shared corpus-walk utility for build-time scripts.

Centralizes the filter + ordering rules for enumerating corpus markdown
files under ``knowledge_base/``. Extracted so both
``scripts/regrandfather_corpus.py`` and
``scripts/collect_subtopic_candidates.py`` stay in lock-step on:

- hidden-directory pruning (anything starting with ``.`` — ``.git``,
  ``.ds_store``, etc.)
- ``__MACOSX`` subtree pruning (case-insensitive)
- sentinel-filename pruning (``readme.md``/``state.md``/``claude.md``;
  case-insensitive)
- ``.md`` extension gate (case-insensitive)
- deterministic ordering — per-directory ``sorted()`` so the same corpus
  always yields the same sequence of paths regardless of filesystem
  enumeration order

Public surface:

- ``iter_corpus_files(knowledge_base, *, only_topic)`` — generator of
  absolute ``Path`` objects in stable order.
- ``relative_path(path, root)`` — string relativization that falls back to
  ``str(path)`` when the path is not under ``root``.
- ``parent_topic_from_relative(relative_path)`` — the top-level directory
  segment of a ``knowledge_base``-relative path, or ``None`` when the
  path has no parent directory (top-level file).
- ``SKIP_FILENAMES`` / ``SKIP_DIR_NAMES`` — the canonical ignore sets
  (case-insensitive comparisons expected).

No trace events, no LLM, no filesystem mutation — this module is a pure
iterator + helper.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


SKIP_FILENAMES: frozenset[str] = frozenset(
    {"readme.md", "state.md", "claude.md"}
)
"""Sentinel filenames that are never treated as corpus documents.

Comparisons are case-insensitive — the walker lowercases each filename
before checking membership.
"""

SKIP_DIR_NAMES: frozenset[str] = frozenset({"__macosx"})
"""Directory names to prune entirely from the walk.

Stored lowercase; comparisons are case-insensitive. Hidden directories
(``.*``) are pruned separately by prefix check.
"""


def iter_corpus_files(
    knowledge_base: Path,
    *,
    only_topic: str | None = None,
) -> Iterable[Path]:
    """Yield markdown files under ``knowledge_base`` in stable order.

    Skips hidden directories, ``__MACOSX`` subtrees, and any sentinel
    filename declared in ``SKIP_FILENAMES``. Only ``.md`` files are
    emitted. When ``only_topic`` is provided, the walk is restricted to
    ``knowledge_base/<only_topic>/...``.

    Yields paths as ``Path`` objects rooted on the caller-supplied
    ``knowledge_base`` (absolute if the caller passed an absolute path).
    Order is deterministic: each directory's filenames are sorted before
    yield, and ``os.walk`` visits subdirectories in sorted order too.
    """
    if not knowledge_base.is_dir():
        return

    root = knowledge_base
    if only_topic:
        scoped = knowledge_base / only_topic
        if not scoped.is_dir():
            return
        root = scoped

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune hidden + ignored dirs in place so os.walk never descends.
        # Sort what remains so traversal order is deterministic.
        dirnames[:] = sorted(
            name
            for name in dirnames
            if not name.startswith(".")
            and name.lower() not in SKIP_DIR_NAMES
        )
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            if name.lower() in SKIP_FILENAMES:
                continue
            if not name.lower().endswith(".md"):
                continue
            yield Path(dirpath) / name


def relative_path(path: Path, root: Path) -> str:
    """Return ``path`` relative to ``root`` as a POSIX-style string.

    Falls back to ``str(path)`` when ``path`` is not a descendant of
    ``root`` (mirrors the pre-extraction behaviour in regrandfather).
    """
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def parent_topic_from_relative(relative_path: str) -> str | None:
    """Return the first path segment of ``relative_path`` or ``None``.

    ``relative_path`` is expected to be the output of ``relative_path``
    above — e.g. ``laboral/NOM-liquidacion.md``. The first directory
    segment is the Lia-canonical parent topic. Top-level files (no
    directory) return ``None`` so callers can fall back to the
    classifier's ``detected_topic``.
    """
    if not relative_path:
        return None
    # Use pathlib so both POSIX and Windows separators normalize.
    parts = Path(relative_path).parts
    if len(parts) <= 1:
        return None
    first = parts[0]
    if not first or first in (".", ".."):
        return None
    return first


__all__ = [
    "SKIP_FILENAMES",
    "SKIP_DIR_NAMES",
    "iter_corpus_files",
    "relative_path",
    "parent_topic_from_relative",
]
