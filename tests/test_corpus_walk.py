"""Unit tests for ``lia_graph.corpus_walk`` (Phase 2 shared walker).

Exercises the filter + ordering + parent-topic-derivation rules that
both ``scripts/regrandfather_corpus.py`` and
``scripts/collect_subtopic_candidates.py`` rely on:

  (a) hidden dirs (``.git`` etc.) are pruned
  (b) sentinel filenames (``readme.md`` / ``state.md`` / ``claude.md``)
      are pruned case-insensitively
  (c) the ``__MACOSX`` subtree is pruned entirely
  (d) ``knowledge_base`` override: only_topic scopes the walk
  (e) ordering is deterministic (same input → same output order)
  (f) ``parent_topic_from_relative`` returns the first segment
"""

from __future__ import annotations

from pathlib import Path

from lia_graph.corpus_walk import (
    SKIP_DIR_NAMES,
    SKIP_FILENAMES,
    iter_corpus_files,
    parent_topic_from_relative,
    relative_path,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _touch(path: Path, content: str = "body\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_kb(root: Path, files: list[str]) -> Path:
    kb = root / "knowledge_base"
    for rel in files:
        _touch(kb / rel)
    return kb


# ---------------------------------------------------------------------------
# (a) hidden dirs are pruned
# ---------------------------------------------------------------------------


def test_hidden_dirs_are_pruned(tmp_path):
    kb = _make_kb(
        tmp_path,
        [
            "laboral/doc.md",
            ".git/HEAD.md",
            ".hidden/nested.md",
            "tributario/.cache/x.md",
        ],
    )

    names = {p.name for p in iter_corpus_files(kb)}
    assert names == {"doc.md"}


# ---------------------------------------------------------------------------
# (b) sentinel filenames (case-insensitive) are pruned
# ---------------------------------------------------------------------------


def test_sentinel_filenames_are_pruned_case_insensitive(tmp_path):
    kb = _make_kb(
        tmp_path,
        [
            "laboral/README.md",
            "laboral/State.md",
            "laboral/CLAUDE.md",
            "laboral/real_doc.md",
            "iva/readme.md",
            "iva/guide.md",
        ],
    )

    names = {p.name for p in iter_corpus_files(kb)}
    assert names == {"real_doc.md", "guide.md"}

    # Sanity: SKIP_FILENAMES is lowercase.
    assert all(name == name.lower() for name in SKIP_FILENAMES)


# ---------------------------------------------------------------------------
# (c) __MACOSX subtree is pruned entirely
# ---------------------------------------------------------------------------


def test_macosx_subtree_is_pruned(tmp_path):
    kb = _make_kb(
        tmp_path,
        [
            "laboral/doc.md",
            "laboral/__MACOSX/ignored.md",
            "__MACOSX/top_ignored.md",
            "iva/__macosx/also_ignored.md",
        ],
    )

    paths = sorted(str(p) for p in iter_corpus_files(kb))
    # Exactly one survivor — everything under __MACOSX pruned
    # regardless of case or depth.
    assert len(paths) == 1
    assert paths[0].endswith("laboral/doc.md")

    assert "__macosx" in SKIP_DIR_NAMES


# ---------------------------------------------------------------------------
# (d) knowledge_base override + only_topic
# ---------------------------------------------------------------------------


def test_only_topic_restricts_walk(tmp_path):
    kb = _make_kb(
        tmp_path,
        [
            "laboral/a.md",
            "laboral/sub/b.md",
            "iva/c.md",
            "tributario/d.md",
        ],
    )

    scoped = {p.name for p in iter_corpus_files(kb, only_topic="laboral")}
    assert scoped == {"a.md", "b.md"}

    # Unknown topic → empty yield, no crash.
    missing = list(iter_corpus_files(kb, only_topic="does_not_exist"))
    assert missing == []

    # Missing knowledge_base root → empty yield, no crash.
    assert list(iter_corpus_files(tmp_path / "nope")) == []


# ---------------------------------------------------------------------------
# (e) deterministic ordering
# ---------------------------------------------------------------------------


def test_ordering_is_deterministic(tmp_path):
    kb = _make_kb(
        tmp_path,
        [
            "laboral/z.md",
            "laboral/a.md",
            "laboral/m.md",
            "iva/b.md",
            "iva/y.md",
            "tributario/c.md",
        ],
    )

    first = [relative_path(p, kb) for p in iter_corpus_files(kb)]
    second = [relative_path(p, kb) for p in iter_corpus_files(kb)]
    assert first == second
    # Within each topic, alphabetical ordering is preserved.
    laboral_order = [name for name in first if name.startswith("laboral/")]
    assert laboral_order == sorted(laboral_order)


# ---------------------------------------------------------------------------
# (f) parent_topic_from_relative
# ---------------------------------------------------------------------------


def test_parent_topic_from_relative_returns_first_segment():
    assert parent_topic_from_relative("laboral/NOM-liquidacion.md") == "laboral"
    assert parent_topic_from_relative("iva/subdir/file.md") == "iva"
    assert parent_topic_from_relative("tributario/a/b/c.md") == "tributario"
    # Top-level file (no parent dir) → None.
    assert parent_topic_from_relative("top_level.md") is None
    # Empty string → None.
    assert parent_topic_from_relative("") is None
