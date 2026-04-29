#!/usr/bin/env python3
"""Heartbeat for next_v7 post-P1 streams (P5 / P4 / P6).

Reads the dir written by `launch_post_p1.sh` (path stored in
`logs/post_p1_latest_dir`) and prints a single Bogotá-AM/PM-stamped
status block. Designed to be called from a Monitor loop every 3 min.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BOGOTA = timezone(timedelta(hours=-5), name="Bogotá")


def _bogota_now() -> str:
    return datetime.now(BOGOTA).strftime("%Y-%m-%d %I:%M:%S %p %Z")


def _proc_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return int(path.read_text().strip())
    except Exception:
        return None


def _tail(path: Path, n: int = 200) -> str:
    if not path.exists():
        return ""
    try:
        with path.open("rb") as fh:
            try:
                fh.seek(-65536, os.SEEK_END)
            except OSError:
                fh.seek(0)
            data = fh.read().decode("utf-8", errors="replace")
        lines = data.splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return ""


def _scan_p4_progress(log: str) -> dict[str, int | str]:
    out: dict[str, int | str] = {}
    # _EmbeddingJobRunner emits patterns like:
    #   [init] Target: production, force=False, batch_size=100
    #   [progress] batch=12/45 cursor_id=… elapsed=…
    #   pending_count=N
    for line in log.splitlines()[::-1]:
        if "pending_count" in line:
            m = re.search(r"pending_count=(\d+)", line)
            if m and "pending" not in out:
                out["pending"] = int(m.group(1))
        if "batch=" in line and "/" in line:
            m = re.search(r"batch=(\d+)/(\d+)", line)
            if m and "batch_now" not in out:
                out["batch_now"] = int(m.group(1))
                out["batch_total"] = int(m.group(2))
        if "filled=" in line:
            m = re.search(r"filled=(\d+)", line)
            if m and "filled" not in out:
                out["filled"] = int(m.group(1))
        if all(k in out for k in ("pending", "batch_now", "filled")):
            break
    return out


def _scan_p6_progress(events_log: Path, cascade_log: Path) -> dict[str, int | str]:
    out: dict[str, int | str] = {}
    # Prefer logs/events.jsonl tail for cascade event types. Actual kinds
    # emitted by extract_vigencia.py: norm.success / norm.refusal /
    # norm.error (NOT the *-ed forms an earlier draft of this script
    # grepped). Cap to the recent tail so a long events.jsonl doesn't
    # over-count old work.
    if events_log.exists():
        text = _tail(events_log, n=600)
        succeses = sum(1 for line in text.splitlines() if '"kind": "norm.success"' in line or '"kind":"norm.success"' in line)
        refusals = sum(1 for line in text.splitlines() if '"kind": "norm.refusal"' in line or '"kind":"norm.refusal"' in line)
        errors = sum(1 for line in text.splitlines() if '"kind": "norm.error"' in line or '"kind":"norm.error"' in line)
        out["events_tail_succ"] = succeses
        out["events_tail_ref"] = refusals
        out["events_tail_err"] = errors
    cascade_text = _tail(cascade_log, n=200)
    # current batch from "── batch X/Y: Z ──" lines or similar.
    for line in cascade_text.splitlines()[::-1]:
        m = re.search(r"batch (\d+)/(\d+): (\w+)", line)
        if m:
            out["batch_now"] = int(m.group(1))
            out["batch_total"] = int(m.group(2))
            out["batch_label"] = m.group(3)
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--post-dir", default=None,
                    help="logs/post_p1_<TS>/. Default reads logs/post_p1_latest_dir.")
    args = ap.parse_args()

    if args.post_dir:
        post_dir = Path(args.post_dir)
    else:
        latest = Path("logs/post_p1_latest_dir")
        if not latest.exists():
            print(f"[{_bogota_now()}] post-p1 heartbeat: logs/post_p1_latest_dir missing. Has launch_post_p1.sh fired?", flush=True)
            return 2
        post_dir = Path(latest.read_text().strip())

    if not post_dir.is_dir():
        print(f"[{_bogota_now()}] post-p1 heartbeat: {post_dir} not found.", flush=True)
        return 2

    launch_log = post_dir / "launch.log"
    p5_log = post_dir / "p5_falkor_sync.log"
    p4_log = post_dir / "p4_embedding_backfill.log"
    p6_log = post_dir / "p6_cascade_v6_2.log"
    p4_pid_file = post_dir / "p4.pid"
    p6_pid_file = post_dir / "p6.pid"
    events_log = Path("logs/events.jsonl")

    p4_pid = _read_pid(p4_pid_file)
    p6_pid = _read_pid(p6_pid_file)

    p4_alive = _proc_alive(p4_pid)
    p6_alive = _proc_alive(p6_pid)

    launch_text = _tail(launch_log, n=80)
    p5_done = "P5 ok" in launch_text or "P5 — sync" not in launch_text and p5_log.exists()
    p5_failed = "P5 failed" in launch_text

    if p5_failed:
        p5_status = "FAILED"
    elif p5_done:
        p5_status = "ok"
    elif "P5 — sync" in launch_text:
        p5_status = "running"
    else:
        p5_status = "pending"

    print(f"[{_bogota_now()}] post-p1 heartbeat — dir={post_dir.name}", flush=True)
    print(f"  P5 Falkor sync : {p5_status}", flush=True)

    # P4
    if p4_pid is None:
        print(f"  P4 backfill    : not yet launched", flush=True)
    else:
        p4_state = "RUNNING" if p4_alive else ("FINISHED (PID gone)" if p4_log.exists() else "STOPPED")
        prog = _scan_p4_progress(_tail(p4_log, n=300))
        prog_str = ""
        if "pending" in prog:
            prog_str = f"pending={prog['pending']}"
        if "batch_now" in prog:
            prog_str += f"  batch={prog['batch_now']}/{prog.get('batch_total','?')}"
        if "filled" in prog:
            prog_str += f"  filled={prog['filled']}"
        print(f"  P4 backfill    : {p4_state}  PID={p4_pid}  {prog_str}", flush=True)

    # P6
    if p6_pid is None:
        print(f"  P6 refusal rerun: not yet launched", flush=True)
    else:
        p6_state = "RUNNING" if p6_alive else ("FINISHED (PID gone)" if p6_log.exists() else "STOPPED")
        prog = _scan_p6_progress(events_log, p6_log)
        prog_str = ""
        if "batch_now" in prog:
            prog_str = f"batch={prog['batch_now']}/{prog.get('batch_total','?')} ({prog.get('batch_label','?')})"
        if "events_tail_succ" in prog:
            prog_str += f"  recent: succ={prog['events_tail_succ']} ref={prog['events_tail_ref']} err={prog['events_tail_err']}"
        print(f"  P6 refusal rerun: {p6_state}  PID={p6_pid}  {prog_str}", flush=True)

    # Stop conditions
    if p5_status == "FAILED":
        print("POST_P1_FAILED_AT_P5", flush=True)
        return 1
    # Both detached jobs finished?
    p4_finished = (p4_pid is not None) and (not p4_alive)
    p6_finished = (p6_pid is not None) and (not p6_alive)
    if p4_finished and p6_finished:
        print("POST_P1_BOTH_FINISHED", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
