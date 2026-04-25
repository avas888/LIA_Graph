"""next_v3.md §5 — CI gate: gold file topics must exist in the v2 taxonomy.

Closes I6 per ``docs/learnings/retrieval/citation-allowlist-and-gold-alignment.md``
(Part 2): every ``expected_topic`` in the gold file must be either a current
taxonomy key or a ``legacy_document_topic`` on some current entry (so renames
don't silently orphan gold rows).

A future PR that renames a topic without updating ``legacy_document_topics``
(or the gold file) will fail this test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lia_graph.topic_taxonomy import iter_topic_taxonomy_entries


REPO = Path(__file__).resolve().parents[1]
GOLD_PATH = REPO / "evals" / "gold_retrieval_v1.jsonl"
VALIDATION_PATH = REPO / "evals" / "gold_taxonomy_v2_validation.jsonl"


def _taxonomy_keyspace() -> set[str]:
    keys: set[str] = set()
    for entry in iter_topic_taxonomy_entries():
        keys.add(entry.key)
        for legacy in entry.legacy_document_topics:
            if legacy:
                keys.add(legacy)
    return keys


def _iter_gold_topics(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        qid = row.get("qid")
        top = row.get("expected_topic")
        if top:
            yield qid, "expected_topic", top
        for sq in (row.get("sub_questions") or []):
            st = sq.get("expected_topic")
            if st:
                yield qid, "sub_questions.expected_topic", st
        # Acceptable-alternatives for ambiguous questions (v2 validation)
        for alt in (row.get("ambiguous_acceptable") or []):
            yield qid, "ambiguous_acceptable", alt


def test_gold_retrieval_topics_align_with_taxonomy() -> None:
    keyspace = _taxonomy_keyspace()
    offenders: list[tuple[str, str, str]] = []
    for qid, field, topic in _iter_gold_topics(GOLD_PATH):
        if topic not in keyspace:
            offenders.append((qid, field, topic))
    if offenders:
        lines = [f"{qid} · {field} = {topic!r}" for qid, field, topic in offenders]
        raise AssertionError(
            "gold_retrieval_v1.jsonl has topics that are neither current taxonomy keys "
            "nor legacy_document_topics on v2 entries:\n  "
            + "\n  ".join(lines)
        )


def test_validation_gold_topics_align_with_taxonomy() -> None:
    """The SME-authored 30Q validation set must also align."""
    keyspace = _taxonomy_keyspace()
    offenders: list[tuple[str, str, str]] = []
    for qid, field, topic in _iter_gold_topics(VALIDATION_PATH):
        if topic not in keyspace:
            offenders.append((qid, field, topic))
    if offenders:
        lines = [f"q{qid} · {field} = {topic!r}" for qid, field, topic in offenders]
        raise AssertionError(
            "gold_taxonomy_v2_validation.jsonl has topics that are not in the taxonomy:\n  "
            + "\n  ".join(lines)
        )
