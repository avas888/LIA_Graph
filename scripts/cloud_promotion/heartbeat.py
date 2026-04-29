#!/usr/bin/env python3
"""Heartbeat for next_v7 §3.1 P1 cloud promotion.

Reads `state.json` + `audit.jsonl` written by `run.sh` and prints a
single Bogotá-AM/PM-stamped status block. Designed to be called from a
Monitor loop every 3 minutes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

BOGOTA = timezone(timedelta(hours=-5), name="Bogotá")


def _bogota_now() -> str:
    return datetime.now(BOGOTA).strftime("%Y-%m-%d %I:%M:%S %p %Z")


def _parse_audit(path: Path, run_id: str) -> tuple[Counter, dict[str, Counter]]:
    overall: Counter = Counter()
    per_batch: dict[str, Counter] = {}
    if not path.exists():
        return overall, per_batch
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            row_run = row.get("run_id", "")
            if not row_run.startswith(run_id):
                continue
            batch = row_run[len(run_id) + 1:] if len(row_run) > len(run_id) else "?"
            outcome = row.get("outcome", "?")
            overall[outcome] += 1
            per_batch.setdefault(batch, Counter())[outcome] += 1
    return overall, per_batch


def _proc_alive(pid_file: Path) -> bool:
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
    except Exception:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, help="logs/cloud_promotion_<TS>/")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    state_path = run_dir / "state.json"
    audit_path = run_dir / "audit.jsonl"
    cli_done = run_dir / "cli.done"
    cli_partial = run_dir / "cli.partial"
    cli_failfast = run_dir / "cli.failfast"
    pid_file = run_dir / "driver.pid"

    if not state_path.exists():
        print(f"[{_bogota_now()}] heartbeat: state.json not found at {state_path}", flush=True)
        return 2

    state = json.loads(state_path.read_text())
    run_id = state.get("run_id", "")
    started = state.get("started_at_utc", "?")
    total_batches = state.get("total_batches", 0)
    current_batch = state.get("current_batch") or "(idle)"
    done_batches = state.get("completed_batches", 0)

    overall, per_batch = _parse_audit(audit_path, run_id)
    inserted = overall.get("inserted", 0)
    skipped = overall.get("skipped", 0)
    refused = overall.get("refusal", 0)
    errors = overall.get("error", 0)
    total_rows = inserted + skipped + refused + errors

    if cli_failfast.exists():
        status = "FAIL-FAST aborted"
    elif cli_done.exists():
        status = "FINISHED ok"
    elif cli_partial.exists():
        status = "FINISHED with errors"
    elif _proc_alive(pid_file):
        status = "RUNNING"
    elif total_batches and done_batches >= total_batches:
        status = "FINISHED (no sentinel)"
    else:
        status = "STOPPED (silent death — investigate)"

    started_dt = None
    elapsed_str = "?"
    if started not in (None, "?"):
        try:
            started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
            elapsed = datetime.now(timezone.utc) - started_dt
            mins = int(elapsed.total_seconds() // 60)
            elapsed_str = f"{mins // 60}h{mins % 60:02d}m"
        except Exception:
            pass

    print(f"[{_bogota_now()}] cloud_promotion heartbeat — {status}", flush=True)
    print(f"  run_id={run_id}  elapsed={elapsed_str}  batches={done_batches}/{total_batches}  current={current_batch}", flush=True)
    print(f"  rows: inserted={inserted}  skipped={skipped}  refused={refused}  errors={errors}  total={total_rows}", flush=True)

    if per_batch:
        recent = sorted(per_batch.items())[-3:]
        for name, c in recent:
            print(f"    {name:6s}  ins={c.get('inserted',0):4d}  skp={c.get('skipped',0):4d}  ref={c.get('refusal',0):4d}  err={c.get('error',0):3d}", flush=True)

    if cli_failfast.exists():
        print("CLI_FAILFAST", flush=True)
        return 0
    if cli_done.exists():
        print("CLI_DONE", flush=True)
        return 0
    if cli_partial.exists():
        print("CLI_PARTIAL", flush=True)
        return 0
    if status.startswith("STOPPED"):
        print("CLI_STOPPED", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
