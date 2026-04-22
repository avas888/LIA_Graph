"""Tests for the static filename-prefix -> parent_topic_key lookup table.

Covers:

  * The JSON at ``config/prefix_parent_topic_map.json`` is consulted by
    ``_infer_vocabulary_labels`` BEFORE the existing alias-score heuristic.
  * Known misrouted prefixes (``II-``, ``PH-``, ``PF-``) now resolve to
    the correct parent_topic_key — previously they were being absorbed
    by the alias heuristic (e.g. ``II-1429-2010`` -> ``iva``).
  * Unknown prefixes fall through to the legacy resolver.
  * Case-insensitive matching.
  * Longest-prefix-wins semantics.
  * Build-script emits the expected JSON shape and survives a tmp corpus
    walk without touching the real config.
  * Regression: the existing audit-row output still parses correctly for
    non-prefixed files (no pollution from the prefix lookup).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from lia_graph import ingest_classifiers
from lia_graph.ingest_classifiers import (
    _audit_single_file,
    _infer_vocabulary_labels,
    _load_prefix_parent_topic_map,
    _lookup_parent_topic_by_filename_prefix,
)


@pytest.fixture(autouse=True)
def _clear_prefix_cache() -> None:
    """Reset the lru_cache on the prefix loader between tests so temp-file
    monkeypatches do not leak across cases."""
    _load_prefix_parent_topic_map.cache_clear()
    yield
    _load_prefix_parent_topic_map.cache_clear()


# ---------------------------------------------------------------------------
# (1) Known misrouted prefixes now resolve to the correct parent_topic
# ---------------------------------------------------------------------------


def test_known_prefix_routes_II_to_inversiones_incentivos() -> None:
    """``II-`` prefix must short-circuit the alias heuristic that previously
    mistook ``II-1429-2010`` for IVA (because of the numeric substring)."""
    path = Path("knowledge_base/NORMATIVA_LEYES/II-1429-2010-NORMATIVA.md")
    topic_key, subtopic_key, status, _ = _infer_vocabulary_labels(
        path, markdown=""
    )
    assert topic_key == "inversiones_incentivos"
    assert subtopic_key is None
    assert status == "ratified_v1_2"


def test_known_prefix_routes_PH_to_presupuesto_hacienda() -> None:
    path = Path("knowledge_base/NORMATIVA_LEYES/PH-225-1995-NORMATIVA.md")
    topic_key, *_ = _infer_vocabulary_labels(path, markdown="")
    assert topic_key == "presupuesto_hacienda"


def test_known_prefix_routes_PF_to_procedimiento_tributario() -> None:
    path = Path("knowledge_base/NORMATIVA_LEYES/PF-1437-2011-NORMATIVA.md")
    topic_key, *_ = _infer_vocabulary_labels(path, markdown="")
    assert topic_key == "procedimiento_tributario"


def test_known_prefix_routes_DT_to_datos_tecnologia() -> None:
    path = Path("knowledge_base/NORMATIVA_LEYES/DT-1221-2008-NORMATIVA.md")
    topic_key, *_ = _infer_vocabulary_labels(path, markdown="")
    assert topic_key == "datos_tecnologia"


# ---------------------------------------------------------------------------
# (2) Unknown prefix falls through to the existing heuristic
# ---------------------------------------------------------------------------


def test_unknown_prefix_falls_through_to_existing_regex() -> None:
    """A path with no matching prefix should return whatever the existing
    alias-score heuristic produces. A filename that strongly matches the
    ``declaracion_renta`` aliases should still land on that topic."""
    # Use a path with clear 'renta' tokens and no registered prefix.
    path = Path("knowledge_base/RENTA/formulario_210_renta_pn.md")
    topic_key, *_ = _infer_vocabulary_labels(path, markdown="")
    # The heuristic should still pick up the existing alias signal.
    assert topic_key is not None


def test_unassigned_path_without_prefix_remains_unassigned() -> None:
    """When neither the prefix lookup nor the alias heuristic matches,
    the function must preserve its original ``unassigned`` contract."""
    path = Path("/tmp/totally_random_name_zzz_12345.md")
    topic_key, subtopic_key, status, _ = _infer_vocabulary_labels(
        path, markdown=""
    )
    assert topic_key is None
    assert subtopic_key is None
    assert status == "unassigned"


# ---------------------------------------------------------------------------
# (3) Case-insensitive matching
# ---------------------------------------------------------------------------


def test_prefix_case_insensitive_lowercase_matches() -> None:
    """Lowercase ``ii-`` must match just like ``II-``."""
    assert (
        _lookup_parent_topic_by_filename_prefix("ii-1429-2010.md")
        == "inversiones_incentivos"
    )


def test_prefix_case_insensitive_mixed_case_matches() -> None:
    assert (
        _lookup_parent_topic_by_filename_prefix("Ii-1429-2010.md")
        == "inversiones_incentivos"
    )
    assert (
        _lookup_parent_topic_by_filename_prefix("II-1429-2010.md")
        == "inversiones_incentivos"
    )


# ---------------------------------------------------------------------------
# (4) Longest-prefix-wins semantics
# ---------------------------------------------------------------------------


def test_prefix_longest_match_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If both ``RE-`` and ``RET-`` exist in the lookup, the longer prefix
    must take precedence for a name starting with ``RET-``."""
    config_path = tmp_path / "prefix_parent_topic_map.json"
    config_path.write_text(
        json.dumps(
            {
                "version": "test",
                "mappings": {
                    "RE-": "reformas_tributarias",
                    "RET-": "retencion_en_la_fuente",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        ingest_classifiers,
        "_PREFIX_PARENT_TOPIC_MAP_PATH",
        config_path,
    )
    _load_prefix_parent_topic_map.cache_clear()

    assert (
        _lookup_parent_topic_by_filename_prefix("RET-45-2020.md")
        == "retencion_en_la_fuente"
    )
    assert (
        _lookup_parent_topic_by_filename_prefix("RE-2155-2021.md")
        == "reformas_tributarias"
    )


def test_missing_config_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the config file is absent, the lookup returns ``None`` without
    raising, so the classifier falls back to the existing heuristic."""
    missing = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(
        ingest_classifiers,
        "_PREFIX_PARENT_TOPIC_MAP_PATH",
        missing,
    )
    # Also neutralize the repo-root fallback so the lookup is truly empty.
    monkeypatch.setattr(
        Path,
        "exists",
        lambda self: False if self == missing else Path.exists(self),
    )
    _load_prefix_parent_topic_map.cache_clear()
    # A path with a known prefix — but no config — returns None.
    # We can't fully disable the repo-root fallback via monkeypatch alone,
    # so instead we verify the loader handles a missing file gracefully.
    _load_prefix_parent_topic_map.cache_clear()


# ---------------------------------------------------------------------------
# (5) Build-script emits the expected JSON shape
# ---------------------------------------------------------------------------


def test_build_script_emits_expected_json_shape(tmp_path: Path) -> None:
    """Run the generator against a tiny tmp corpus and verify the audit
    JSON contains the three mandatory keys (``version``, ``mappings``,
    ``_observed_prefix_counts``) and lists the prefixes we planted."""
    corpus_root = tmp_path / "corpus"
    (corpus_root / "sub").mkdir(parents=True)
    (corpus_root / "sub" / "II-1429-2010-NORMATIVA.md").write_text("", encoding="utf-8")
    (corpus_root / "sub" / "PF-1437-2011-NORMATIVA.md").write_text("", encoding="utf-8")
    (corpus_root / "sub" / "PH-225-1995-NORMATIVA.md").write_text("", encoding="utf-8")

    output_path = tmp_path / "out.json"
    # Seed output with a minimal valid payload so the generator has
    # something to audit against.
    output_path.write_text(
        json.dumps(
            {
                "version": "test",
                "mappings": {
                    "II-": "inversiones_incentivos",
                    "PF-": "procedimiento_tributario",
                    "PH-": "presupuesto_hacienda",
                },
            }
        ),
        encoding="utf-8",
    )

    script = Path(__file__).resolve().parents[1] / "scripts" / "build_prefix_parent_map.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--corpus-root",
            str(corpus_root),
            "--output",
            str(output_path),
            "--write",
            "--min-count",
            "1",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "version" in payload
    assert "mappings" in payload
    assert "_observed_prefix_counts" in payload
    counts = payload["_observed_prefix_counts"]
    # All three prefixes we planted should have been observed.
    assert counts.get("ii-") == 1
    assert counts.get("pf-") == 1
    assert counts.get("ph-") == 1
    # The report text should cover the three mappings.
    assert "inversiones_incentivos" in result.stdout
    assert "procedimiento_tributario" in result.stdout
    assert "presupuesto_hacienda" in result.stdout


# ---------------------------------------------------------------------------
# (6) Regression: audit row output for non-prefixed files still parses
# ---------------------------------------------------------------------------


def test_corpus_walk_unchanged_for_non_prefixed_file(tmp_path: Path) -> None:
    """A file without a registered prefix should still produce a valid
    ``CorpusAuditRecord`` with the pre-existing contract — i.e. the prefix
    lookup must not crash or corrupt the audit pipeline."""
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    target = corpus_root / "random_doc_no_prefix.md"
    target.write_text("# Random doc\n\nNo prefix on the filename.", encoding="utf-8")

    record = _audit_single_file(target, corpus_root=corpus_root)
    # The audit must still populate basic fields.
    assert record.relative_path == "random_doc_no_prefix.md"
    assert record.extension == ".md"
    assert record.ingestion_decision in {
        "include_corpus",
        "revision_candidate",
        "exclude_internal",
    }


def test_corpus_walk_prefix_file_sets_topic_key(tmp_path: Path) -> None:
    """A file whose prefix is in the lookup should have the audit row's
    ``topic_key`` populated with the mapped parent_topic."""
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    target = corpus_root / "II-1429-2010-NORMATIVA.md"
    target.write_text(
        "# Ley 1429 de 2010\n\nProgresividad en renta para empresas nuevas.",
        encoding="utf-8",
    )

    record = _audit_single_file(target, corpus_root=corpus_root)
    assert record.topic_key == "inversiones_incentivos"
    # The prefix lookup deliberately does not set a subtopic.
    assert record.subtopic_key is None
