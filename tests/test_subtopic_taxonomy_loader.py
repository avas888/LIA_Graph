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


def _write_fixture(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "taxonomy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_loader_parses_deprecated_aliases_when_present(tmp_path: Path) -> None:
    """Curator renames (memo §5.4–5.5) populate ``deprecated_aliases``."""
    fixture = {
        "version": "fixture-deprecated-1",
        "generated_from": "test",
        "generated_at": "2026-04-21T00:00:00Z",
        "subtopics": {
            "tributario": [
                {
                    "key": "emergencia_tributaria_decretos_transitorios",
                    "label": "Emergencia tributaria — decretos transitorios",
                    "aliases": ["decretos_transitorios"],
                    "deprecated_aliases": [
                        "exenciones_tributarias_covid_19",
                        "old_key_x",
                    ],
                    "evidence_count": 3,
                    "curated_at": "2026-04-21T00:00:00Z",
                    "curator": "test",
                },
                {
                    "key": "plain_entry",
                    "label": "Plain Entry",
                    "aliases": [],
                    "evidence_count": 1,
                    "curated_at": "2026-04-21T00:00:00Z",
                    "curator": "test",
                },
            ]
        },
    }
    taxonomy = load_taxonomy(_write_fixture(tmp_path, fixture))
    renamed = taxonomy.lookup_by_key[
        ("tributario", "emergencia_tributaria_decretos_transitorios")
    ]
    assert renamed.deprecated_aliases == (
        "exenciones_tributarias_covid_19",
        "old_key_x",
    )


def test_loader_defaults_deprecated_aliases_to_empty_tuple_when_absent(
    tmp_path: Path,
) -> None:
    """Pre-rename entries without the field still load cleanly."""
    fixture = {
        "version": "fixture-deprecated-2",
        "generated_from": "test",
        "generated_at": "2026-04-21T00:00:00Z",
        "subtopics": {
            "laboral": [
                {
                    "key": "nomina_electronica",
                    "label": "Nómina electrónica",
                    "aliases": ["nom_elec"],
                    "evidence_count": 1,
                    "curated_at": "2026-04-21T00:00:00Z",
                    "curator": "test",
                }
            ]
        },
    }
    taxonomy = load_taxonomy(_write_fixture(tmp_path, fixture))
    entry = taxonomy.lookup_by_key[("laboral", "nomina_electronica")]
    assert entry.deprecated_aliases == ()


def test_resolve_key_prefers_current_key_over_deprecated(tmp_path: Path) -> None:
    """When a key appears as both current and deprecated, current wins."""
    fixture = {
        "version": "fixture-deprecated-3",
        "generated_from": "test",
        "generated_at": "2026-04-21T00:00:00Z",
        "subtopics": {
            "tributario": [
                {
                    "key": "shared_name",
                    "label": "Shared Name — canonical",
                    "aliases": [],
                    "evidence_count": 2,
                    "curated_at": "2026-04-21T00:00:00Z",
                    "curator": "test",
                },
                {
                    "key": "new_owner",
                    "label": "New Owner",
                    "aliases": [],
                    "deprecated_aliases": ["shared_name"],
                    "evidence_count": 2,
                    "curated_at": "2026-04-21T00:00:00Z",
                    "curator": "test",
                },
            ]
        },
    }
    taxonomy = load_taxonomy(_write_fixture(tmp_path, fixture))
    resolved = taxonomy.resolve_key("tributario", "shared_name")
    assert resolved is not None
    assert resolved.key == "shared_name"
    assert resolved.label == "Shared Name — canonical"


def test_resolve_key_falls_back_to_deprecated_when_current_missing(
    tmp_path: Path,
) -> None:
    """Legacy keys route to the renamed entry via deprecated_aliases."""
    fixture = {
        "version": "fixture-deprecated-4",
        "generated_from": "test",
        "generated_at": "2026-04-21T00:00:00Z",
        "subtopics": {
            "tributario": [
                {
                    "key": "impuesto_patrimonio_personas_naturales_permanente",
                    "label": "Impuesto al patrimonio — personas naturales (permanente)",
                    "aliases": [],
                    "deprecated_aliases": [
                        "impuesto_al_patrimonio_excepcional_2011"
                    ],
                    "evidence_count": 4,
                    "curated_at": "2026-04-21T00:00:00Z",
                    "curator": "test",
                }
            ]
        },
    }
    taxonomy = load_taxonomy(_write_fixture(tmp_path, fixture))
    assert (
        taxonomy.resolve_key(
            "tributario", "impuesto_al_patrimonio_excepcional_2011"
        )
        is not None
    )
    resolved = taxonomy.resolve_key(
        "tributario", "impuesto_al_patrimonio_excepcional_2011"
    )
    assert resolved is not None
    assert resolved.key == "impuesto_patrimonio_personas_naturales_permanente"
    # Unknown key in the same parent returns None.
    assert taxonomy.resolve_key("tributario", "totally_unknown_key") is None
    # Legacy key under a non-matching parent does NOT cross-resolve.
    assert (
        taxonomy.resolve_key(
            "laboral", "impuesto_al_patrimonio_excepcional_2011"
        )
        is None
    )


def test_all_surface_forms_includes_deprecated_aliases() -> None:
    """Planner intent detection must still match queries phrased with old keys."""
    entry = SubtopicEntry(
        parent_topic="tributario",
        key="emergencia_tributaria_decretos_transitorios",
        label="Emergencia tributaria — decretos transitorios",
        aliases=("decretos_transitorios",),
        evidence_count=1,
        curated_at="2026-04-21T00:00:00Z",
        curator="test",
        deprecated_aliases=("exenciones_tributarias_covid_19",),
    )
    forms = set(entry.all_surface_forms())
    assert "emergencia_tributaria_decretos_transitorios" in forms
    assert "Emergencia tributaria — decretos transitorios" in forms
    assert "decretos_transitorios" in forms
    assert "exenciones_tributarias_covid_19" in forms
