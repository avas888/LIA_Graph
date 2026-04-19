"""Tests for scripts/embedding_ops.py (thin CLI over lia_graph.embedding_ops).

Mocks the runner + status function so the CLI contract can be exercised
without talking to Supabase or Gemini.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "embedding_ops.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("embedding_ops_cli", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_exits_zero_when_null_count_drops_to_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        module,
        "_run",
        lambda target, batch_size, force: {
            "job_id": "job-1",
            "status": {
                "total_chunks": 1000,
                "null_embedding_chunks": 0,
                "coverage_pct": 100.0,
            },
            "finished_at": "2026-04-19T00:00:00Z",
        },
    )

    rc = module.main(
        ["--target", "wip", "--generation", "gen_test", "--json"]
    )
    assert rc == 0

    manifests = list((tmp_path / "artifacts" / "suin").glob("_embedding_wip_*.json"))
    assert len(manifests) == 1
    payload = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["null_embedding_chunks"] == 0


def test_cli_exits_one_when_nulls_remain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        module,
        "_run",
        lambda target, batch_size, force: {
            "job_id": "job-2",
            "status": {
                "total_chunks": 1000,
                "null_embedding_chunks": 50,
                "coverage_pct": 95.0,
            },
            "finished_at": "2026-04-19T00:00:00Z",
        },
    )

    rc = module.main(
        ["--target", "wip", "--generation", "gen_test"]
    )
    assert rc == 1


def test_cli_exits_two_on_runner_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)

    def _boom(*_a, **_kw):
        raise RuntimeError("runner blew up")

    monkeypatch.setattr(module, "_run", _boom)
    rc = module.main(["--target", "wip", "--generation", "gen_test"])
    assert rc == 2
