"""CLI-entry smoke tests for ``python -m lia_graph.ingest``.

Regression guard for the bug that motivated ingestfix-v2-maximalist (§1.2 root
cause #4): the module was importable but had no ``__main__`` guard, so
``python -m lia_graph.ingest`` exited 0 with no output, silently no-op'ing
the whole Phase 2 ingest.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"


def _run_module(*args: str, timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "PYTHONPATH": f"{SRC_DIR}:{REPO_ROOT}",
    }
    return subprocess.run(
        [sys.executable, "-m", "lia_graph.ingest", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=str(REPO_ROOT),
    )


def test_help_returns_zero_and_mentions_supabase_target_flag() -> None:
    result = _run_module("--help")
    assert result.returncode == 0, (
        f"expected --help to exit 0, got {result.returncode}; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "usage:" in result.stdout.lower()
    assert "--supabase-target" in result.stdout


def test_nonexistent_corpus_dir_is_not_silent(tmp_path) -> None:
    """Regression: guard against the ``__main__`` guard getting deleted again.

    Pre-fix: exit 0 with empty stdout+stderr (silent no-op).
    Post-fix: runs, detects the missing corpus, exits non-zero with output.

    We point at a non-existent corpus dir so materialize_graph_artifacts
    fails fast (no LLM calls, no real corpus scan).
    """
    result = _run_module(
        "--corpus-dir",
        str(tmp_path / "does-not-exist"),
        "--artifacts-dir",
        str(tmp_path / "artifacts"),
        "--json",
        timeout=15.0,
    )
    has_visible_output = bool(result.stdout.strip() or result.stderr.strip())
    assert has_visible_output, (
        "ingest CLI produced no output at all — the `if __name__ "
        "== \"__main__\"` guard in src/lia_graph/ingest.py has regressed."
    )
    assert result.returncode != 0, (
        f"expected non-zero exit for missing corpus; got {result.returncode}; "
        f"stdout={result.stdout!r}"
    )


# ---------------------------------------------------------------------------
# Phase A6: --skip-llm + --rate-limit-rpm flags
# ---------------------------------------------------------------------------


def test_skip_llm_flag_parses() -> None:
    from lia_graph.ingest import parser

    ns = parser().parse_args(["--skip-llm"])
    assert ns.skip_llm is True


def test_rate_limit_rpm_flag_parses() -> None:
    from lia_graph.ingest import parser

    ns = parser().parse_args(["--rate-limit-rpm", "30"])
    assert ns.rate_limit_rpm == 30


def test_main_passes_skip_llm_through_to_materialize(monkeypatch) -> None:
    """Invoking main(['--skip-llm']) threads skip_llm=True into
    materialize_graph_artifacts, which in turn skips the PASO 4 pass."""
    from lia_graph import ingest as ingest_mod

    captured: dict[str, object] = {}

    def fake_materialize(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "corpus_dir": ".",
            "artifacts_dir": ".",
            "pattern": "*",
            "taxonomy_version": "t",
            "scanned_file_count": 0,
            "decision_counts": {},
            "document_count": 0,
            "document_family_counts": {},
            "knowledge_class_counts": {},
            "source_type_counts": {},
            "extension_counts": {},
            "parse_strategy_counts": {},
            "document_archetype_counts": {},
            "source_tier_counts": {},
            "authority_level_counts": {},
            "review_priority_counts": {},
            "ambiguity_flag_counts": {},
            "topic_key_counts": {},
            "subtopic_key_counts": {},
            "topic_subtopic_coverage": {},
            "reconnaissance_quality_gate": {"status": "ready_for_canonical_blessing"},
            "manual_review_queue_count": 0,
            "manual_review_queue_preview": [],
            "graph_target_families": [],
            "graph_target_document_count": 0,
            "graph_parse_ready_document_count": 0,
            "article_count": 0,
            "raw_edge_count": 0,
            "typed_edge_count": 0,
            "files": {},
            "graph_load_report": {
                "requested_execution": False,
                "executed": False,
                "success_count": 0,
                "failure_count": 0,
                "skipped_count": 0,
                "connection": {},
            },
            "supabase_sink_report": None,
            "suin_merge_report": None,
        }

    monkeypatch.setattr(ingest_mod, "materialize_graph_artifacts", fake_materialize)
    # assert_local_posture may be strict about env; bypass with the flag.
    rc = ingest_mod.main(
        [
            "--skip-llm",
            "--rate-limit-rpm",
            "5",
            "--allow-non-local-env",
            "--json",
        ]
    )
    assert rc == 0
    assert captured["skip_llm"] is True
    assert captured["rate_limit_rpm"] == 5
