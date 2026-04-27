"""Batched test runner with stall detection + heartbeat.

Discovers all test files (`tests/**/test_*.py`), splits them into N batches,
runs each batch in its own pytest process, and emits a per-batch heartbeat
line to stdout. If a batch's wall time exceeds 6× the median of prior
batches AND > 60s absolute, the runner kills it and re-runs each file in
the batch individually to isolate the culprit.

Sets `LIA_BATCHED_RUNNER=1` so any conftest guards see we are the sanctioned
caller.

Usage (from Makefile):
  PYTHONPATH=src:. uv run python scripts/run_tests_batched.py \\
      --batches 120 [--cov] [--fail-under 90] [--filter <substring>] [--paths tests/integration]

Output:
  Stdout: one batch heartbeat line per batch + a final summary table.
  Exit code: 0 when every batch passes; 1 when any failed; 2 on stall.

Bogotá AM/PM convention: heartbeat timestamps render in `America/Bogota`
12-hour AM/PM per repo memory (`feedback_time_format_bogota.md`).
"""

from __future__ import annotations

import argparse
import math
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEST_PATHS = ("tests",)
BOGOTA_TZ = timezone(timedelta(hours=-5))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--batches", type=int, default=120, help="Number of batches.")
    p.add_argument(
        "--paths",
        nargs="+",
        default=list(DEFAULT_TEST_PATHS),
        help="Pytest paths to scan for test files.",
    )
    p.add_argument(
        "--filter",
        default=None,
        help=(
            "Filter on test file paths. May be a plain substring, a "
            "comma-separated list of substrings, or a regex (any-of-tokens)."
        ),
    )
    p.add_argument(
        "--cov",
        action="store_true",
        help="Run with `--cov=src/lia_graph` (when pytest-cov is installed).",
    )
    p.add_argument(
        "--fail-under",
        type=float,
        default=None,
        help="Fail if total coverage < this percentage (requires --cov).",
    )
    p.add_argument(
        "--max-batch-mult",
        type=float,
        default=6.0,
        help="Stall threshold: kill a batch when wall > this × median of priors.",
    )
    p.add_argument(
        "--stall-floor-seconds",
        type=float,
        default=60.0,
        help="Don't apply stall detection until at least this long.",
    )
    p.add_argument(
        "--include-integration",
        action="store_true",
        help="Include `tests/integration` (requires LIA_INTEGRATION=1).",
    )
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    test_files = _collect_files(args.paths, include_integration=args.include_integration, filter_substring=args.filter)
    if not test_files:
        print("[run_tests_batched] no test files found", file=sys.stderr)
        return 1

    batches = _split(test_files, args.batches)
    print(
        f"[run_tests_batched] {_now_bogota()} — {len(test_files)} files in "
        f"{len(batches)} batches (~{len(test_files)//max(len(batches),1)} per batch)",
        flush=True,
    )

    env = os.environ.copy()
    env["LIA_BATCHED_RUNNER"] = "1"
    env.setdefault("PYTHONPATH", "src:.")

    durations: list[float] = []
    failed_batches: list[tuple[int, list[str]]] = []
    failed_files: list[str] = []
    total_passed = 0
    total_failed = 0
    total_skipped = 0

    cov_args: list[str] = []
    if args.cov:
        cov_args = ["--cov=src/lia_graph", "--cov-append", "--cov-report="]
        # Reset coverage before the run so we don't accumulate prior data
        try:
            (ROOT / ".coverage").unlink(missing_ok=True)
        except Exception:
            pass

    for i, batch in enumerate(batches):
        start = time.monotonic()
        rc, summary = _run_batch(
            batch_index=i,
            batch_files=batch,
            cov_args=cov_args,
            verbose=args.verbose,
            env=env,
            stall_threshold_seconds=_stall_threshold(durations, args.max_batch_mult, args.stall_floor_seconds),
        )
        wall = time.monotonic() - start
        durations.append(wall)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)
        total_passed += passed
        total_failed += failed
        total_skipped += skipped

        # Heartbeat line — Bogotá AM/PM, summary counts, last action
        print(
            f"[run_tests_batched] {_now_bogota()} — batch {i+1:3d}/{len(batches)} "
            f"({len(batch)} files, {wall:5.1f}s) — "
            f"passed={passed} failed={failed} skipped={skipped} rc={rc}",
            flush=True,
        )

        if rc != 0 or failed > 0:
            failed_batches.append((i, batch))
            failed_files.extend(summary.get("failed_files", []))
            if args.verbose:
                # Re-run individually to isolate the culprit file.
                for f in batch:
                    rc_one, sum_one = _run_batch(
                        batch_index=i,
                        batch_files=[f],
                        cov_args=[],  # don't double-count cov
                        verbose=True,
                        env=env,
                        stall_threshold_seconds=None,
                    )
                    if rc_one != 0:
                        failed_files.append(f)

    # Coverage gate
    cov_pct: float | None = None
    if args.cov:
        try:
            cov_proc = subprocess.run(
                ["uv", "run", "coverage", "report"],
                capture_output=True,
                text=True,
                env=env,
                cwd=str(ROOT),
                timeout=120,
            )
            print(cov_proc.stdout, flush=True)
            cov_pct = _parse_total_coverage(cov_proc.stdout)
        except Exception as err:
            print(f"[run_tests_batched] coverage report failed: {err}", flush=True)

    print("", flush=True)
    print(
        f"[run_tests_batched] DONE {_now_bogota()} — "
        f"batches={len(batches)} passed={total_passed} failed={total_failed} skipped={total_skipped} "
        f"failed_batches={len(failed_batches)} coverage={cov_pct or 'n/a'}",
        flush=True,
    )

    if total_failed > 0 or failed_batches:
        if failed_files:
            print("[run_tests_batched] failing files:", flush=True)
            for f in failed_files:
                print(f"  - {f}", flush=True)
        return 1
    if args.cov and args.fail_under is not None and cov_pct is not None and cov_pct < args.fail_under:
        print(
            f"[run_tests_batched] coverage {cov_pct:.2f}% < --fail-under {args.fail_under}",
            flush=True,
        )
        return 3
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_files(paths: list[str], *, include_integration: bool, filter_substring: str | None) -> list[str]:
    out: list[str] = []
    tokens: list[str] = []
    if filter_substring:
        # Comma-separated → any-token match. Single string → substring match.
        if "," in filter_substring:
            tokens = [t.strip() for t in filter_substring.split(",") if t.strip()]
        else:
            tokens = [filter_substring]
    for p in paths:
        candidate = ROOT / p
        if candidate.is_file() and candidate.suffix == ".py":
            rel = str(candidate.relative_to(ROOT))
            if not include_integration and "integration" in rel.split(os.sep):
                continue
            if tokens and not any(t in rel for t in tokens):
                continue
            out.append(rel)
            continue
        base = candidate
        if not base.exists():
            continue
        for f in base.rglob("test_*.py"):
            rel = str(f.relative_to(ROOT))
            if not include_integration and "integration" in rel.split(os.sep):
                continue
            if tokens and not any(t in rel for t in tokens):
                continue
            out.append(rel)
    return sorted(set(out))


def _split(files: list[str], batches: int) -> list[list[str]]:
    if batches <= 0:
        return [files]
    if len(files) <= batches:
        return [[f] for f in files]
    size = math.ceil(len(files) / batches)
    return [files[i : i + size] for i in range(0, len(files), size)]


def _stall_threshold(durations: list[float], multiplier: float, floor_seconds: float) -> float | None:
    if len(durations) < 5:
        return None
    median = statistics.median(durations)
    return max(floor_seconds, median * multiplier)


def _run_batch(
    *,
    batch_index: int,
    batch_files: list[str],
    cov_args: list[str],
    verbose: bool,
    env: dict[str, str],
    stall_threshold_seconds: float | None,
) -> tuple[int, dict[str, object]]:
    cmd = [
        "uv",
        "run",
        "pytest",
        "-r",
        "fEs",
        "--tb=line",
        "-p",
        "no:cacheprovider",
        "-o",
        "addopts=",  # neutralize project-level addopts so -q doesn't suppress the summary
        *cov_args,
        *batch_files,
    ]
    timeout = stall_threshold_seconds if stall_threshold_seconds and stall_threshold_seconds > 0 else None
    try:
        proc = subprocess.run(
            cmd,
            env=env,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 2, {"passed": 0, "failed": len(batch_files), "skipped": 0, "stalled": True, "failed_files": batch_files}
    if verbose:
        print(proc.stdout, flush=True)
        print(proc.stderr, file=sys.stderr, flush=True)
    summary = _parse_pytest_output(proc.stdout)
    if proc.returncode != 0 and summary.get("failed", 0) == 0:
        # parse miss; still mark batch as failed
        summary["failed"] = max(summary.get("failed", 0), 1)
        summary["failed_files"] = batch_files
    return proc.returncode, summary


def _parse_pytest_output(stdout: str) -> dict[str, object]:
    out: dict[str, object] = {"passed": 0, "failed": 0, "skipped": 0, "failed_files": []}
    for line in stdout.splitlines()[::-1]:
        # last summary line: "1 passed, 2 failed, 3 skipped in 1.23s"
        if (" passed" in line or " failed" in line or " skipped" in line or " errors" in line) and " in " in line:
            for token in line.replace(",", "").split():
                if token.isdigit():
                    last_int = int(token)
                    continue
                lower = token.lower()
                if lower in ("passed", "passed,"):
                    out["passed"] = int(out.get("passed", 0)) + last_int
                elif lower in ("failed", "failed,"):
                    out["failed"] = int(out.get("failed", 0)) + last_int
                elif lower in ("skipped", "skipped,"):
                    out["skipped"] = int(out.get("skipped", 0)) + last_int
                elif lower in ("errors", "errors,", "error", "error,"):
                    out["failed"] = int(out.get("failed", 0)) + last_int
            break
    failed_files: list[str] = []
    for line in stdout.splitlines():
        if line.startswith("FAILED ") or line.startswith("ERROR "):
            parts = line.split("::", 1)
            if parts:
                file_part = parts[0].split(" ", 1)
                if len(file_part) >= 2:
                    failed_files.append(file_part[1])
    out["failed_files"] = sorted(set(failed_files))
    return out


def _parse_total_coverage(text: str) -> float | None:
    for line in text.splitlines()[::-1]:
        line = line.strip()
        if line.startswith("TOTAL"):
            for token in line.split():
                if token.endswith("%"):
                    try:
                        return float(token[:-1])
                    except ValueError:
                        return None
    return None


def _now_bogota() -> str:
    now = datetime.now(BOGOTA_TZ)
    return now.strftime("%Y-%m-%d %I:%M:%S %p Bogotá")


if __name__ == "__main__":
    sys.exit(main())
