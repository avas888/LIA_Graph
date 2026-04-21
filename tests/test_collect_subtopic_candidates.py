"""Tests for ``scripts/collect_subtopic_candidates.py`` (Phase 2).

Stages a synthetic ``knowledge_base`` under ``tmp_path``, monkeypatches
the script module's ``classify_ingestion_document`` import to return a
minimal ``AutogenerarResult`` stub, and exercises the CLI in-process via
``main(argv)`` — no network, no real LLM.

Covers:
  (a) empty corpus → 0 rows emitted + ``subtopic.collect.done`` fired
  (b) 3-doc fixture → 3 rows with ``autogenerar_label`` + ``_latest.json``
  (c) ``--dry-run`` writes no files but still emits events
  (d) ``--limit 1`` stops after first doc
  (e) ``--only-topic laboral`` restricts the walk
  (f) ``--resume-from`` checkpoint skips already-present doc_ids
  (g) rate-limit honoured (``time.sleep`` called ≥ n-1 times)
  (h) LLM failure on one doc → ``.doc.failed`` fires; walk continues; rc=2
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "collect_subtopic_candidates.py"


# ---------------------------------------------------------------------------
# Module loader — cached so monkeypatching lands once per test.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def collect_module():
    spec = importlib.util.spec_from_file_location(
        "collect_subtopic_candidates_under_test", _SCRIPT_PATH
    )
    assert spec and spec.loader, "could not load collect_subtopic_candidates.py"
    module = importlib.util.module_from_spec(spec)
    sys.modules["collect_subtopic_candidates_under_test"] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_autogenerar_result(collect_module, *, label: str = "etiqueta de prueba"):
    """Build a minimal ``AutogenerarResult`` stub that mimics a happy N2 hit."""
    AutogenerarResult = collect_module.AutogenerarResult
    return AutogenerarResult(
        generated_label=label,
        rationale="fragmento coincide con el tema",
        resolved_to_existing="laboral",
        synonym_confidence=0.9,
        is_new_topic=False,
        suggested_key=None,
        detected_type="normative_base",
        detected_topic="laboral",
        topic_confidence=0.95,
        type_confidence=0.95,
        combined_confidence=0.95,
        classification_source="keywords",
        is_raw=False,
        requires_review=False,
    )


def _install_classifier_mock(
    collect_module,
    monkeypatch: pytest.MonkeyPatch,
    *,
    calls: list[dict[str, Any]],
    result_for=None,
    raise_for: set[str] | None = None,
):
    """Patch the script-bound ``classify_ingestion_document`` symbol."""
    raise_for = raise_for or set()

    def _fake(**kwargs):
        calls.append(kwargs)
        fn = kwargs.get("filename", "")
        if fn in raise_for:
            raise RuntimeError(f"boom on {fn}")
        if result_for is not None:
            return result_for(fn)
        return _fake_autogenerar_result(collect_module)

    monkeypatch.setattr(
        collect_module, "classify_ingestion_document", _fake, raising=True
    )


def _install_event_capture(
    collect_module, monkeypatch: pytest.MonkeyPatch
) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []

    def _capture(event_type: str, payload: dict[str, Any], *_a, **_kw) -> None:
        events.append((event_type, dict(payload)))

    monkeypatch.setattr(collect_module, "emit_event", _capture, raising=True)
    return events


def _seed_corpus(root: Path, files: dict[str, str]) -> Path:
    kb = root / "knowledge_base"
    kb.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        target = kb / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return kb


def _base_argv(
    tmp_path: Path,
    *,
    commit: bool = False,
    extra: list[str] | None = None,
) -> list[str]:
    argv = [
        "--knowledge-base",
        str(tmp_path / "knowledge_base"),
        "--artifacts-dir",
        str(tmp_path / "artifacts"),
        "--rate-limit-rpm",
        "0",  # disable throttling by default to keep unit tests instant
    ]
    argv.append("--commit" if commit else "--dry-run")
    if extra:
        argv.extend(extra)
    return argv


def _read_collection_rows(artifacts_dir: Path) -> tuple[Path, list[dict[str, Any]]]:
    root = artifacts_dir / "subtopic_candidates"
    jsonls = sorted(p for p in root.glob("collection_*.jsonl") if p.is_file())
    assert jsonls, f"expected at least one collection_*.jsonl in {root}"
    latest = jsonls[-1]
    rows = [
        json.loads(line)
        for line in latest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return latest, rows


# ---------------------------------------------------------------------------
# (a) Empty corpus
# ---------------------------------------------------------------------------


def test_empty_corpus_emits_done_with_zero_docs(
    tmp_path: Path, collect_module, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "knowledge_base").mkdir()
    calls: list[dict[str, Any]] = []
    _install_classifier_mock(collect_module, monkeypatch, calls=calls)
    events = _install_event_capture(collect_module, monkeypatch)

    rc = collect_module.main(_base_argv(tmp_path, commit=True))

    assert rc == 0
    assert calls == []
    types = [etype for etype, _ in events]
    assert types[0] == "subtopic.collect.start"
    assert types[-1] == "subtopic.collect.done"
    done_payload = events[-1][1]
    assert done_payload["docs_processed"] == 0
    assert done_payload["docs_failed"] == 0


# ---------------------------------------------------------------------------
# (b) 3-doc fixture produces 3 rows + _latest.json
# ---------------------------------------------------------------------------


def test_three_doc_fixture_emits_rows_and_latest_pointer(
    tmp_path: Path, collect_module, monkeypatch: pytest.MonkeyPatch
):
    _seed_corpus(
        tmp_path,
        {
            "laboral/a.md": "cuerpo a",
            "laboral/b.md": "cuerpo b",
            "iva/c.md": "cuerpo c",
        },
    )
    calls: list[dict[str, Any]] = []
    _install_classifier_mock(collect_module, monkeypatch, calls=calls)
    _install_event_capture(collect_module, monkeypatch)

    rc = collect_module.main(_base_argv(tmp_path, commit=True))
    assert rc == 0

    latest_path, rows = _read_collection_rows(tmp_path / "artifacts")
    assert len(rows) == 3
    assert all(row["autogenerar_label"] == "etiqueta de prueba" for row in rows)
    # Parent topic derived from the first path segment.
    parents = sorted({row["parent_topic"] for row in rows})
    assert parents == ["iva", "laboral"]
    # doc_id + content_hash populated with the expected shape.
    assert all(row["doc_id"].startswith("sha256:") for row in rows)
    assert all(row["content_hash"].startswith("sha256:") for row in rows)

    pointer = tmp_path / "artifacts" / "subtopic_candidates" / "_latest.json"
    assert pointer.is_file()
    pointer_payload = json.loads(pointer.read_text(encoding="utf-8"))
    assert pointer_payload["docs_processed"] == 3
    assert pointer_payload["docs_failed"] == 0
    assert pointer_payload["collection_path"] == str(latest_path)


# ---------------------------------------------------------------------------
# (c) --dry-run writes no files but still emits events
# ---------------------------------------------------------------------------


def test_dry_run_writes_no_files_but_still_emits_events(
    tmp_path: Path, collect_module, monkeypatch: pytest.MonkeyPatch
):
    _seed_corpus(
        tmp_path,
        {"laboral/a.md": "cuerpo a", "iva/b.md": "cuerpo b"},
    )
    calls: list[dict[str, Any]] = []
    _install_classifier_mock(collect_module, monkeypatch, calls=calls)
    events = _install_event_capture(collect_module, monkeypatch)

    rc = collect_module.main(_base_argv(tmp_path, commit=False))
    assert rc == 0

    artifacts_root = tmp_path / "artifacts" / "subtopic_candidates"
    # No JSONL, no pointer.
    assert not any(p.suffix == ".jsonl" for p in artifacts_root.glob("*")) or not artifacts_root.exists()
    assert not (artifacts_root / "_latest.json").exists()

    types = [etype for etype, _ in events]
    assert "subtopic.collect.start" in types
    assert types.count("subtopic.collect.doc.processed") == 2
    assert types[-1] == "subtopic.collect.done"
    done_payload = events[-1][1]
    assert done_payload["dry_run"] is True
    assert done_payload["output_path"] is None


# ---------------------------------------------------------------------------
# (d) --limit 1 stops after first doc
# ---------------------------------------------------------------------------


def test_limit_stops_after_first_doc(
    tmp_path: Path, collect_module, monkeypatch: pytest.MonkeyPatch
):
    _seed_corpus(
        tmp_path,
        {
            "laboral/a.md": "cuerpo a",
            "laboral/b.md": "cuerpo b",
            "iva/c.md": "cuerpo c",
        },
    )
    calls: list[dict[str, Any]] = []
    _install_classifier_mock(collect_module, monkeypatch, calls=calls)
    _install_event_capture(collect_module, monkeypatch)

    rc = collect_module.main(_base_argv(tmp_path, commit=True, extra=["--limit", "1"]))
    assert rc == 0
    assert len(calls) == 1

    _, rows = _read_collection_rows(tmp_path / "artifacts")
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# (e) --only-topic laboral restricts the walk
# ---------------------------------------------------------------------------


def test_only_topic_restricts_walk(
    tmp_path: Path, collect_module, monkeypatch: pytest.MonkeyPatch
):
    _seed_corpus(
        tmp_path,
        {
            "laboral/a.md": "cuerpo a",
            "laboral/sub/b.md": "cuerpo b",
            "iva/c.md": "cuerpo c",
            "tributario/d.md": "cuerpo d",
        },
    )
    calls: list[dict[str, Any]] = []
    _install_classifier_mock(collect_module, monkeypatch, calls=calls)
    _install_event_capture(collect_module, monkeypatch)

    rc = collect_module.main(
        _base_argv(tmp_path, commit=True, extra=["--only-topic", "laboral"])
    )
    assert rc == 0
    assert len(calls) == 2

    _, rows = _read_collection_rows(tmp_path / "artifacts")
    assert {row["parent_topic"] for row in rows} == {"laboral"}
    filenames = sorted(row["filename"] for row in rows)
    assert filenames == ["a.md", "b.md"]


# ---------------------------------------------------------------------------
# (f) --resume-from checkpoint skips already-present doc_ids
# ---------------------------------------------------------------------------


def test_resume_from_checkpoint_skips_seen_doc_ids(
    tmp_path: Path, collect_module, monkeypatch: pytest.MonkeyPatch
):
    _seed_corpus(
        tmp_path,
        {
            "laboral/a.md": "cuerpo a",
            "laboral/b.md": "cuerpo b",
            "iva/c.md": "cuerpo c",
        },
    )

    # Compute the doc_id for laboral/a.md using the script's own helpers so
    # the checkpoint row is byte-identical to what a real run would emit.
    import hashlib

    rel = "laboral/a.md"
    raw = (tmp_path / "knowledge_base" / rel).read_bytes()
    content_hash = f"sha256:{hashlib.sha256(raw).hexdigest()}"
    doc_id = collect_module._derive_doc_id(rel, content_hash)

    checkpoint = tmp_path / "existing_collection.jsonl"
    checkpoint.write_text(
        json.dumps({"doc_id": doc_id}) + "\n", encoding="utf-8"
    )

    calls: list[dict[str, Any]] = []
    _install_classifier_mock(collect_module, monkeypatch, calls=calls)
    _install_event_capture(collect_module, monkeypatch)

    rc = collect_module.main(
        _base_argv(
            tmp_path,
            commit=True,
            extra=["--resume-from", str(checkpoint)],
        )
    )
    assert rc == 0

    # laboral/a.md was in the checkpoint → only 2 classifier calls.
    assert len(calls) == 2
    _, rows = _read_collection_rows(tmp_path / "artifacts")
    assert len(rows) == 2
    assert all(row["doc_id"] != doc_id for row in rows)


# ---------------------------------------------------------------------------
# (g) Rate limit honoured (time.sleep called between classifier calls)
# ---------------------------------------------------------------------------


def test_rate_limit_honoured(
    tmp_path: Path, collect_module, monkeypatch: pytest.MonkeyPatch
):
    _seed_corpus(
        tmp_path,
        {
            "laboral/a.md": "cuerpo a",
            "laboral/b.md": "cuerpo b",
            "iva/c.md": "cuerpo c",
        },
    )
    calls: list[dict[str, Any]] = []
    _install_classifier_mock(collect_module, monkeypatch, calls=calls)
    _install_event_capture(collect_module, monkeypatch)

    sleep_calls: list[float] = []

    def _record_sleep(seconds: float) -> None:
        sleep_calls.append(float(seconds))

    monkeypatch.setattr(collect_module.time, "sleep", _record_sleep)

    argv = [
        "--knowledge-base",
        str(tmp_path / "knowledge_base"),
        "--artifacts-dir",
        str(tmp_path / "artifacts"),
        "--commit",
        "--rate-limit-rpm",
        "60",  # 1.0s per call
    ]
    rc = collect_module.main(argv)
    assert rc == 0

    # For 3 classifier calls at 60 rpm, expect ≥ 2 sleeps (n-1 between calls).
    assert len(sleep_calls) >= 2
    # Each sleep at rpm=60 is ~1.0s.
    assert all(abs(s - 1.0) < 1e-6 for s in sleep_calls)


# ---------------------------------------------------------------------------
# (h) LLM failure on one doc — .doc.failed fires, walk continues, rc=2
# ---------------------------------------------------------------------------


def test_llm_failure_on_one_doc_continues_and_exits_two(
    tmp_path: Path, collect_module, monkeypatch: pytest.MonkeyPatch
):
    _seed_corpus(
        tmp_path,
        {
            "laboral/a.md": "cuerpo a",
            "laboral/b.md": "cuerpo b",  # this one raises
            "iva/c.md": "cuerpo c",
        },
    )
    calls: list[dict[str, Any]] = []
    _install_classifier_mock(
        collect_module, monkeypatch, calls=calls, raise_for={"b.md"}
    )
    events = _install_event_capture(collect_module, monkeypatch)

    rc = collect_module.main(_base_argv(tmp_path, commit=True))
    assert rc == 2

    # The walk did not abort on b.md.
    assert len(calls) == 3

    types = [etype for etype, _ in events]
    assert "subtopic.collect.doc.failed" in types
    failed_event = next(p for t, p in events if t == "subtopic.collect.doc.failed")
    assert failed_event["phase"] == "classify"
    assert "RuntimeError" in failed_event["error"]
    # Two successful rows still written.
    _, rows = _read_collection_rows(tmp_path / "artifacts")
    assert len(rows) == 2
    done_payload = next(p for t, p in events if t == "subtopic.collect.done")
    assert done_payload["docs_processed"] == 2
    assert done_payload["docs_failed"] == 1


# ---------------------------------------------------------------------------
# (i) parent_topic falls back to classifier when filesystem dir isn't a
# canonical topic key (regression for real-corpus layouts like
# `knowledge_base/CORE ya Arriba/<TOPIC>/<SUBTYPE>/...`)
# ---------------------------------------------------------------------------


def test_parent_topic_prefers_classifier_when_filesystem_is_staging_dir(
    tmp_path: Path,
    collect_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the first path segment isn't a canonical topic key (e.g.
    `"CORE ya Arriba"`), the classifier's `detected_topic` wins — so
    mining buckets by real topic, not by staging dir."""
    kb = tmp_path / "knowledge_base" / "CORE ya Arriba" / "RST_REGIMEN_SIMPLE"
    kb.mkdir(parents=True)
    (kb / "doc_a.md").write_text("# RST\n\ntexto", encoding="utf-8")

    monkeypatch.setattr(
        collect_module,
        "classify_ingestion_document",
        lambda *, filename, body_text, always_emit_label=False, skip_llm=False: _fake_autogenerar_result(
            collect_module,
            label="etiqueta rst",
        ),
    )
    # Swap in a fixture classifier that returns a canonical topic key.
    real_fixture = _fake_autogenerar_result(collect_module, label="etiqueta rst")

    def _classifier(*, filename, body_text, always_emit_label=False, skip_llm=False):
        # Return an AutogenerarResult with detected_topic="rst_regimen_simple"
        # (a canonical key).
        from dataclasses import replace
        return replace(real_fixture, detected_topic="rst_regimen_simple")

    monkeypatch.setattr(collect_module, "classify_ingestion_document", _classifier)

    collect_module.main(
        [
            "--commit",
            "--knowledge-base",
            str(tmp_path / "knowledge_base"),
            "--artifacts-dir",
            str(tmp_path / "artifacts"),
            "--skip-llm",
            "--rate-limit-rpm",
            "6000",
        ]
    )

    _, rows = _read_collection_rows(tmp_path / "artifacts")
    assert rows, "at least one row emitted"
    # parent_topic from the classifier, not the filesystem staging dir.
    assert rows[0]["parent_topic"] == "rst_regimen_simple"
    # The original filesystem segment is preserved in corpus_relative_path
    # so traceability isn't lost.
    assert rows[0]["corpus_relative_path"].startswith("CORE ya Arriba/")


def test_parent_topic_prefers_filesystem_when_segment_is_canonical_topic(
    tmp_path: Path,
    collect_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the filesystem segment IS a canonical topic key (e.g. `laboral`),
    it wins over a divergent classifier verdict — a well-organized corpus
    tree is authoritative."""
    kb = tmp_path / "knowledge_base" / "laboral"
    kb.mkdir(parents=True)
    (kb / "doc_a.md").write_text("# Laboral\n\ntexto", encoding="utf-8")

    real_fixture = _fake_autogenerar_result(collect_module)

    def _classifier(*, filename, body_text, always_emit_label=False, skip_llm=False):
        from dataclasses import replace
        # Classifier thinks it's iva, but the dir says laboral — dir wins.
        return replace(real_fixture, detected_topic="iva")

    monkeypatch.setattr(collect_module, "classify_ingestion_document", _classifier)

    collect_module.main(
        [
            "--commit",
            "--knowledge-base",
            str(tmp_path / "knowledge_base"),
            "--artifacts-dir",
            str(tmp_path / "artifacts"),
            "--skip-llm",
            "--rate-limit-rpm",
            "6000",
        ]
    )

    _, rows = _read_collection_rows(tmp_path / "artifacts")
    assert rows[0]["parent_topic"] == "laboral"
