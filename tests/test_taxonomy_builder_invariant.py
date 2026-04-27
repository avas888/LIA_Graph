"""Tests for the zero-subtopic-per-parent invariant (Task C6).

Covers:

- ``validate_no_empty_parents`` raises ``EmptyParentTopicError`` when any
  known parent_topic key has zero subtopics, and lists the offenders.
- ``validate_no_empty_parents`` is silent when every known parent has at
  least one entry.
- The ``--allow-empty-parents`` CLI flag on
  ``scripts/ingestion/promote_subtopic_decisions.py`` bypasses the invariant.
- When the invariant fires, an existing ``config/subtopic_taxonomy.json``
  on disk is NOT overwritten and the script exits with code 1.

Tests that hit the topic taxonomy monkey-patch ``iter_ingestion_topic_entries``
to a tiny synthetic list so they don't depend on the live
``config/topic_taxonomy.json``. This keeps the invariant check hermetic and
deterministic regardless of real-world taxonomy drift.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from lia_graph import subtopic_taxonomy_builder
from lia_graph import topic_taxonomy as topic_taxonomy_module
from lia_graph.subtopic_taxonomy_builder import (
    EmptyParentTopicError,
    validate_no_empty_parents,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "promote_subtopic_decisions.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _synthetic_entry(key: str, *, parent_key: str | None = None):
    """Build a minimal ``TopicTaxonomyEntry`` for tests."""
    return topic_taxonomy_module.TopicTaxonomyEntry(
        key=key,
        label=key.replace("_", " ").title(),
        aliases=(),
        ingestion_aliases=(),
        legacy_document_topics=(),
        allowed_path_prefixes=(),
        vocabulary_status="ratified",
        parent_key=parent_key,
    )


@pytest.fixture
def patch_parent_topics(monkeypatch):
    """Replace the canonical parent-topic list with a tiny synthetic set."""

    def _install(parent_keys: list[str]):
        entries = tuple(_synthetic_entry(k) for k in parent_keys)
        monkeypatch.setattr(
            subtopic_taxonomy_builder,
            # We patch the import inside the builder module's `validate` fn,
            # so we patch the source module's accessor directly.
            "iter_ingestion_topic_entries",
            lambda: entries,
            raising=False,
        )
        # Also patch at the topic_taxonomy module since `validate_no_empty_parents`
        # does `from .topic_taxonomy import iter_ingestion_topic_entries` inside
        # the function body.
        monkeypatch.setattr(
            topic_taxonomy_module,
            "iter_ingestion_topic_entries",
            lambda: entries,
        )
        return entries

    return _install


@pytest.fixture
def promote_module():
    """Load the promote CLI as an importable module (re-load each test).

    We re-load per test because the CLI module caches the builder import at
    top of file; a monkeypatch on ``topic_taxonomy`` during one test must
    still be visible when ``validate_no_empty_parents`` is called on the
    next.
    """
    spec = importlib.util.spec_from_file_location(
        "promote_subtopic_decisions_under_test_invariant", _SCRIPT_PATH
    )
    assert spec and spec.loader, "could not load promote_subtopic_decisions.py"
    module = importlib.util.module_from_spec(spec)
    sys.modules["promote_subtopic_decisions_under_test_invariant"] = module
    spec.loader.exec_module(module)
    return module


def _write_decisions(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False))
            fh.write("\n")


def _accept(parent_topic: str, proposal_id: str, final_key: str) -> dict:
    return {
        "ts": "2026-04-21T14:50:00Z",
        "curator": "admin@lia.dev",
        "parent_topic": parent_topic,
        "proposal_id": proposal_id,
        "action": "accept",
        "final_key": final_key,
        "final_label": final_key.replace("_", " ").title(),
        "aliases": [],
        "merged_into": None,
        "reason": None,
        "evidence_count": 1,
    }


# ---------------------------------------------------------------------------
# (1) Invariant raises when any known parent has zero subtopics
# ---------------------------------------------------------------------------


def test_invariant_raises_when_parent_has_zero_subtopics(patch_parent_topics):
    patch_parent_topics(
        ["laboral", "iva", "activos_exterior", "impuestos_saludables"]
    )

    taxonomy_output = {
        "version": "test-v1",
        "subtopics": {
            "laboral": [{"key": "aportes_pila"}],
            "iva": [{"key": "declaracion_iva"}],
            # activos_exterior + impuestos_saludables missing → invariant fires
        },
    }

    with pytest.raises(EmptyParentTopicError) as excinfo:
        validate_no_empty_parents(taxonomy_output)

    message = str(excinfo.value)
    # Offenders are listed (sorted) in the message.
    assert "activos_exterior" in message
    assert "impuestos_saludables" in message
    # Count reflects both empty parents.
    assert "2 parent_topic(s)" in message
    # Non-offenders are NOT in the list.
    # The offenders list follows the literal 'zero subtopics:' label.
    offenders_section = message.split("zero subtopics:", 1)[1]
    assert "laboral" not in offenders_section
    assert "iva" not in offenders_section


def test_invariant_treats_empty_list_as_zero_subtopics(patch_parent_topics):
    """A parent with an explicit empty list should also trigger the invariant."""
    patch_parent_topics(["laboral", "activos_exterior"])

    taxonomy_output = {
        "version": "test-v1",
        "subtopics": {
            "laboral": [{"key": "aportes_pila"}],
            "activos_exterior": [],  # present but empty
        },
    }

    with pytest.raises(EmptyParentTopicError) as excinfo:
        validate_no_empty_parents(taxonomy_output)
    assert "activos_exterior" in str(excinfo.value)


# ---------------------------------------------------------------------------
# (2) Invariant passes when all parents have ≥1 entry
# ---------------------------------------------------------------------------


def test_invariant_passes_when_all_parents_have_at_least_one(patch_parent_topics):
    patch_parent_topics(["laboral", "iva", "activos_exterior"])

    taxonomy_output = {
        "version": "test-v1",
        "subtopics": {
            "laboral": [{"key": "aportes_pila"}],
            "iva": [{"key": "declaracion_iva"}],
            "activos_exterior": [{"key": "cuentas_en_el_exterior"}],
        },
    }

    # Should not raise.
    validate_no_empty_parents(taxonomy_output)


# ---------------------------------------------------------------------------
# (3) CLI --allow-empty-parents flag bypasses the invariant
# ---------------------------------------------------------------------------


def test_override_flag_allows_empty_parents(
    promote_module, patch_parent_topics, tmp_path
):
    """With --allow-empty-parents the CLI writes the file even when the
    invariant would fire."""
    patch_parent_topics(
        ["laboral", "activos_exterior", "impuestos_saludables"]
    )

    decisions_path = tmp_path / "artifacts" / "subtopic_decisions.jsonl"
    output_path = tmp_path / "config" / "subtopic_taxonomy.json"
    # Only seed one parent — the other two will be empty in the generated output.
    _write_decisions(
        decisions_path,
        [_accept("laboral", "laboral::001", "aportes_pila")],
    )

    buf_out = io.StringIO()
    buf_err = io.StringIO()
    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        rc = promote_module.main(
            [
                "--decisions",
                str(decisions_path),
                "--output",
                str(output_path),
                "--version",
                "2026-04-21-v1",
                "--allow-empty-parents",
            ]
        )

    assert rc == 0, f"override should return 0; stderr={buf_err.getvalue()!r}"
    assert output_path.exists(), "override should still write the file"
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert "laboral" in written["subtopics"]
    # The empty parents are NOT inserted as empty lists (build_taxonomy only
    # emits buckets that received at least one entry). That's fine — the
    # override's job is to tolerate their absence.


# ---------------------------------------------------------------------------
# (4) Invariant failure does NOT overwrite the existing JSON on disk
# ---------------------------------------------------------------------------


def test_existing_taxonomy_file_is_not_overwritten_on_validation_failure(
    promote_module, patch_parent_topics, tmp_path
):
    """If validation fails, the existing output file on disk must be untouched
    and the CLI must return exit code 1."""
    patch_parent_topics(
        ["laboral", "activos_exterior", "impuestos_saludables"]
    )

    decisions_path = tmp_path / "artifacts" / "subtopic_decisions.jsonl"
    output_path = tmp_path / "config" / "subtopic_taxonomy.json"

    # Pre-existing published taxonomy with sentinel contents.
    sentinel_payload = {
        "version": "pre-existing",
        "generated_from": "artifacts/subtopic_decisions.jsonl",
        "generated_at": "2026-04-20T00:00:00Z",
        "subtopics": {"iva": [{"key": "sentinel_entry"}]},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(sentinel_payload), encoding="utf-8")
    pre_existing_raw = output_path.read_text(encoding="utf-8")

    # Decisions file would produce a taxonomy that leaves two parents empty.
    _write_decisions(
        decisions_path,
        [_accept("laboral", "laboral::001", "aportes_pila")],
    )

    buf_out = io.StringIO()
    buf_err = io.StringIO()
    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        rc = promote_module.main(
            [
                "--decisions",
                str(decisions_path),
                "--output",
                str(output_path),
                "--version",
                "2026-04-21-v1",
            ]
        )

    # Exit code 1; existing file untouched.
    assert rc == 1
    assert output_path.read_text(encoding="utf-8") == pre_existing_raw, (
        "existing taxonomy file must not be overwritten on invariant failure"
    )

    stderr_text = buf_err.getvalue()
    assert "activos_exterior" in stderr_text
    assert "impuestos_saludables" in stderr_text
    assert "--allow-empty-parents" in stderr_text
