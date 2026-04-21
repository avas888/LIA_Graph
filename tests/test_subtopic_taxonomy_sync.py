"""Phase 2 tests — sync_subtopic_taxonomy_to_supabase."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
for candidate in (_REPO_ROOT / "src", _REPO_ROOT, _SCRIPTS_DIR):
    candidate_str = str(candidate)
    if candidate.is_dir() and candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SYNC_SCRIPT = _load_script(
    "sync_subtopic_taxonomy_to_supabase",
    _SCRIPTS_DIR / "sync_subtopic_taxonomy_to_supabase.py",
)


FIXTURE = {
    "version": "test-1",
    "generated_from": "test",
    "generated_at": "2026-04-21T00:00:00Z",
    "subtopics": {
        "laboral": [
            {
                "key": "parafiscales_icbf",
                "label": "Parafiscales ICBF",
                "aliases": ["aporte_parafiscales_icbf"],
                "evidence_count": 9,
                "curated_at": "2026-04-21T00:00:00Z",
                "curator": "auto_accept_v1",
            }
        ],
        "iva": [
            {
                "key": "nomina_electronica",
                "label": "Nómina electrónica",
                "aliases": ["pago_nomina_electronica"],
                "evidence_count": 4,
                "curated_at": "2026-04-21T00:00:00Z",
                "curator": "auto_accept_v1",
            }
        ],
    },
}


def _write_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "taxonomy.json"
    path.write_text(json.dumps(FIXTURE), encoding="utf-8")
    return path


class _RecordingUpserter:
    """Captures upsert calls in place of a real Supabase client."""

    def __init__(self) -> None:
        self.calls: list[list[dict[str, Any]]] = []

    def __call__(self, client: Any, rows: list[dict[str, Any]]) -> int:
        self.calls.append(rows)
        return len(rows)


def test_dry_run_prints_count_without_writing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write_fixture(tmp_path)
    exit_code = SYNC_SCRIPT.main(
        ["--taxonomy", str(path), "--target", "wip", "--dry-run"]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "would upsert 2 rows" in out


def test_sync_upserts_all_rows(tmp_path: Path) -> None:
    from lia_graph.subtopic_taxonomy_loader import load_taxonomy

    path = _write_fixture(tmp_path)
    taxonomy = load_taxonomy(path)
    upserter = _RecordingUpserter()
    sent = SYNC_SCRIPT.sync(
        taxonomy,
        target="wip",
        dry_run=False,
        client_factory=lambda target: object(),
        upserter=upserter,
    )
    assert sent == 2
    assert len(upserter.calls) == 1
    rows = upserter.calls[0]
    keys = {(r["parent_topic_key"], r["sub_topic_key"]) for r in rows}
    assert ("laboral", "parafiscales_icbf") in keys
    assert ("iva", "nomina_electronica") in keys
    for row in rows:
        assert row["version"] == "test-1"
        assert isinstance(row["aliases"], list)


def test_sync_is_idempotent(tmp_path: Path) -> None:
    from lia_graph.subtopic_taxonomy_loader import load_taxonomy

    path = _write_fixture(tmp_path)
    taxonomy = load_taxonomy(path)
    upserter = _RecordingUpserter()
    factory = lambda target: object()
    first = SYNC_SCRIPT.sync(
        taxonomy, target="wip", dry_run=False,
        client_factory=factory, upserter=upserter,
    )
    second = SYNC_SCRIPT.sync(
        taxonomy, target="wip", dry_run=False,
        client_factory=factory, upserter=upserter,
    )
    assert first == second == 2
    # Same rows each time.
    assert upserter.calls[0] == upserter.calls[1]


def test_version_bump_re_upserts_aliases(tmp_path: Path) -> None:
    from lia_graph.subtopic_taxonomy_loader import load_taxonomy

    path = _write_fixture(tmp_path)
    v1 = load_taxonomy(path)
    bumped = dict(FIXTURE)
    bumped["version"] = "test-2"
    bumped["subtopics"] = dict(FIXTURE["subtopics"])
    # Same topics — but new alias added.
    bumped["subtopics"]["laboral"] = [
        {
            **FIXTURE["subtopics"]["laboral"][0],
            "aliases": ["aporte_parafiscales_icbf", "parafiscales_bienestar"],
        }
    ]
    path.write_text(json.dumps(bumped), encoding="utf-8")
    v2 = load_taxonomy(path)

    upserter = _RecordingUpserter()
    factory = lambda target: object()
    SYNC_SCRIPT.sync(v1, target="wip", dry_run=False,
                     client_factory=factory, upserter=upserter)
    SYNC_SCRIPT.sync(v2, target="wip", dry_run=False,
                     client_factory=factory, upserter=upserter)
    laboral_row = next(
        row for row in upserter.calls[1]
        if row["parent_topic_key"] == "laboral"
    )
    assert "parafiscales_bienestar" in laboral_row["aliases"]
    assert laboral_row["version"] == "test-2"


def test_malformed_taxonomy_returns_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"not": "taxonomy"}', encoding="utf-8")
    exit_code = SYNC_SCRIPT.main(
        ["--taxonomy", str(path), "--target", "wip", "--dry-run"]
    )
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "failed to load taxonomy" in err
