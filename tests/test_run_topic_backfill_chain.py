"""Tests for ``scripts/run_topic_backfill_chain.sh`` (gate enforcement).

The chain supervisor is a bash script, so these tests shell out to it.
They assert only the Phase-2 piece we've shipped so far: gate-file
enforcement. The full batch loop (STOP_BACKFILL poll, state-file atomic
writes, done_batches_log progression) ships in Phase 3 proper and gets
its own tests then.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "monitoring"
    / "monitor_ingest_topic_batches"
    / "run_topic_backfill_chain.sh"
)


def _run(
    tmp_path: Path,
    *args: str,
    plan_file: Path | None = None,
    gate_file: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke the chain script in an isolated working directory.

    We can't run it straight out of the repo for these tests because it
    hard-codes ``artifacts/...`` paths. Instead we:

    1. Copy the script into ``tmp_path/scripts/``.
    2. Mirror the two env-configurable paths via ``PLAN_FILE`` /
       ``GATE_FILE``, which the script already honors.
    3. Ensure an ``artifacts/`` directory exists (defaults point there).
    """
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    target = scripts_dir / SCRIPT.name
    shutil.copy2(SCRIPT, target)
    target.chmod(0o755)
    (tmp_path / "artifacts").mkdir(exist_ok=True)

    env = os.environ.copy()
    if plan_file is not None:
        env["PLAN_FILE"] = str(plan_file)
    else:
        # Seed a trivial plan so "plan missing" (exit 3) is not the thing
        # under test; the tests care about the gate.
        pf = tmp_path / "plan.json"
        pf.write_text('{"batches": []}', encoding="utf-8")
        env["PLAN_FILE"] = str(pf)
    if gate_file is not None:
        env["GATE_FILE"] = str(gate_file)

    return subprocess.run(
        ["bash", str(target), *args],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
        timeout=15,
    )


def test_chain_exits_3_when_plan_missing(tmp_path: Path) -> None:
    missing_plan = tmp_path / "definitely_not_here.json"
    result = _run(tmp_path, plan_file=missing_plan)
    assert result.returncode == 3, result.stderr
    assert "plan" in result.stderr.lower()


def test_chain_exits_2_when_gate_file_missing(tmp_path: Path) -> None:
    gate_file = tmp_path / "artifacts" / "batch_1_quality_gate.json"  # does not exist
    result = _run(tmp_path, gate_file=gate_file)
    assert result.returncode == 2, result.stdout + result.stderr
    combined = result.stdout + result.stderr
    assert "REFUSED" in combined
    assert "gate file not found" in combined


def test_chain_exits_2_when_gate_status_is_failed(tmp_path: Path) -> None:
    gate_file = tmp_path / "artifacts" / "batch_1_quality_gate.json"
    gate_file.parent.mkdir(parents=True, exist_ok=True)
    gate_file.write_text(
        json.dumps({"batch": 1, "status": "failed"}), encoding="utf-8"
    )
    result = _run(tmp_path, gate_file=gate_file)
    assert result.returncode == 2, result.stdout + result.stderr
    combined = result.stdout + result.stderr
    assert "REFUSED" in combined
    assert "failed" in combined  # reports actual status


def test_chain_exits_2_when_gate_status_absent_field(tmp_path: Path) -> None:
    gate_file = tmp_path / "artifacts" / "batch_1_quality_gate.json"
    gate_file.parent.mkdir(parents=True, exist_ok=True)
    gate_file.write_text(json.dumps({"batch": 1}), encoding="utf-8")
    result = _run(tmp_path, gate_file=gate_file)
    assert result.returncode == 2, result.stdout + result.stderr


def test_chain_proceeds_when_gate_status_passed(tmp_path: Path) -> None:
    gate_file = tmp_path / "artifacts" / "batch_1_quality_gate.json"
    gate_file.parent.mkdir(parents=True, exist_ok=True)
    gate_file.write_text(
        json.dumps({"batch": 1, "status": "passed"}), encoding="utf-8"
    )
    result = _run(tmp_path, gate_file=gate_file)
    # Phase-2 skeleton exits 0 with a "Phase 3 loop not yet wired" note.
    assert result.returncode == 0, result.stdout + result.stderr
    assert "gate passed" in (result.stdout + result.stderr).lower()


def test_chain_gate_only_bypasses_gate_check(tmp_path: Path) -> None:
    # --gate-only is precisely the mode that produces the gate file, so
    # it must NOT require the gate file to already exist.
    gate_file = tmp_path / "artifacts" / "batch_1_quality_gate.json"
    result = _run(tmp_path, "--gate-only", gate_file=gate_file)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "--gate-only" in result.stderr or "gate-only" in result.stderr


def test_chain_rejects_unknown_flag(tmp_path: Path) -> None:
    result = _run(tmp_path, "--bogus-flag")
    assert result.returncode == 1
    assert "unknown flag" in result.stderr.lower()
