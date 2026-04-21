"""Phase 1 tests — subtopic taxonomy loader."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from lia_graph.subtopic_taxonomy_loader import (
    DEFAULT_TAXONOMY_PATH,
    SubtopicEntry,
    SubtopicTaxonomy,
    load_taxonomy,
    normalize_alias,
    validate_taxonomy,
)


def test_loads_real_taxonomy_with_expected_shape() -> None:
    taxonomy = load_taxonomy()
    assert taxonomy.version.startswith("2026-04-21")
    assert taxonomy.total_entries() >= 86
    assert len(taxonomy.parents()) >= 37
    assert isinstance(taxonomy, SubtopicTaxonomy)


def test_get_candidates_for_laboral_returns_entries() -> None:
    taxonomy = load_taxonomy()
    entries = taxonomy.get_candidates_for("laboral")
    assert len(entries) >= 1
    assert all(isinstance(e, SubtopicEntry) for e in entries)
    assert all(e.parent_topic == "laboral" for e in entries)


def test_resolve_alias_uses_full_breadth() -> None:
    """Invariant I1 — aliases resolve, not just keys/labels."""
    taxonomy = load_taxonomy()
    found_by_alias = False
    for parent, entries in taxonomy.subtopics_by_parent.items():
        for entry in entries:
            if entry.aliases:
                resolved = taxonomy.resolve_alias(entry.aliases[0])
                assert resolved is not None
                assert resolved.key == entry.key
                found_by_alias = True
                break
        if found_by_alias:
            break
    assert found_by_alias, "fixture should have at least one aliased entry"


def test_malformed_json_raises_with_location(tmp_path: Path) -> None:
    bad = tmp_path / "taxonomy.json"
    bad.write_text("{ not json", encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        load_taxonomy(bad)
    assert "line" in str(excinfo.value).lower()


def test_missing_version_is_validation_error() -> None:
    errors = validate_taxonomy({"subtopics": {}})
    assert any("version" in err for err in errors)


def test_duplicate_keys_within_parent_are_errors() -> None:
    data = {
        "version": "test",
        "subtopics": {
            "topic_a": [
                {"key": "dup", "label": "First", "aliases": []},
                {"key": "dup", "label": "Second", "aliases": []},
            ]
        },
    }
    errors = validate_taxonomy(data)
    assert any("duplicate key" in err for err in errors)


def test_alias_collision_across_parents_is_not_an_error(tmp_path: Path) -> None:
    """Breadth policy: same alias under two parents is ALLOWED.

    The ``resolve_alias`` lookup picks the first insertion; parent-aware
    callers use :meth:`resolve_within_parent` instead.
    """
    fixture = {
        "version": "fixture-1",
        "generated_from": "test",
        "generated_at": "2026-04-21T00:00:00Z",
        "subtopics": {
            "topic_a": [
                {
                    "key": "alpha",
                    "label": "Alpha A",
                    "aliases": ["shared_alias"],
                    "evidence_count": 1,
                    "curated_at": "2026-04-21T00:00:00Z",
                    "curator": "test",
                }
            ],
            "topic_b": [
                {
                    "key": "beta",
                    "label": "Beta B",
                    "aliases": ["shared_alias"],
                    "evidence_count": 1,
                    "curated_at": "2026-04-21T00:00:00Z",
                    "curator": "test",
                }
            ],
        },
    }
    assert validate_taxonomy(fixture) == []
    path = tmp_path / "taxonomy.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    taxonomy = load_taxonomy(path)
    assert taxonomy.resolve_alias("shared_alias") is not None
    under_b = taxonomy.resolve_within_parent("shared_alias", "topic_b")
    assert under_b is not None and under_b.key == "beta"


def test_taxonomy_dataclass_is_frozen() -> None:
    taxonomy = load_taxonomy()
    with pytest.raises(FrozenInstanceError):
        taxonomy.version = "mutated"  # type: ignore[misc]
    entry = next(iter(taxonomy.subtopics_by_parent.values()))[0]
    with pytest.raises(FrozenInstanceError):
        entry.key = "mutated"  # type: ignore[misc]


def test_normalize_alias_handles_accents_and_spacing() -> None:
    assert normalize_alias("Nómina Electrónica") == "nomina_electronica"
    assert normalize_alias("") == ""
    assert normalize_alias("  Aporte  ICBF!! ") == "aporte_icbf"


def test_default_taxonomy_path_points_to_config() -> None:
    assert DEFAULT_TAXONOMY_PATH.name == "subtopic_taxonomy.json"
    assert DEFAULT_TAXONOMY_PATH.parent.name == "config"
