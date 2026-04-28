"""Cascade-level heartbeat for the fixplan_v5 cascade.

Reads:
  * `logs/cascade_v5_campaign.md` — one row per completed batch
  * `evals/canonicalizer_run_v1/<latest active batch>/heartbeat_stats.json`
  * `/tmp/cascade_v5_driver.pid` — driver pid

Prints a Bogotá-timestamped markdown block: which batch is running, how
many batches done, total veredictos so far, the active batch's per-norm
progress + ETA, and whether the driver is alive.

First stdout line is `STATE=...|DRIVER_ALIVE=...|STEP=...|TOTAL=...` so a
cron caller can parse it for stop/continue decisions.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_LOG = ROOT / "logs" / "cascade_v5_campaign.md"
DRIVER_PID_FILE = Path("/tmp/cascade_v5_driver.pid")
RUN_DIR_BASE = ROOT / "evals" / "canonicalizer_run_v1"
LEDGER = ROOT / "evals" / "canonicalizer_run_v1" / "ledger.jsonl"

CASCADE_BATCHES = [
    "J6", "J7", "K4",
    "J1", "J2", "J3", "J4",
    "K3",
    "G1",
    "G6",
    "F2",
    "E5",
    "E6b", "E6c",
    "E1a", "E1b", "E1d",
    "E2a", "E2c",
    "E3b",
    "J8b",
    "D5",
]

BOGOTA = timezone(timedelta(hours=-5))


def _bog_now() -> str:
    return datetime.now(BOGOTA).strftime("%Y-%m-%d %I:%M:%S %p Bogotá")


def _driver_alive() -> tuple[bool, int | None]:
    if not DRIVER_PID_FILE.exists():
        return False, None
    try:
        pid = int(DRIVER_PID_FILE.read_text().strip())
    except Exception:
        return False, None
    try:
        os.kill(pid, 0)
        return True, pid
    except ProcessLookupError:
        return False, pid
    except PermissionError:
        return True, pid


def _completed_batches() -> list[dict]:
    """Parse the campaign log for completed batch rows."""
    if not CAMPAIGN_LOG.exists():
        return []
    rows = []
    for line in CAMPAIGN_LOG.read_text(encoding="utf-8").splitlines():
        # Match: | step | batch | started | wallSec | norms | ver | refs | errs | top |
        m = re.match(
            r"\|\s*(\d+)\s*\|\s*([A-Za-z0-9]+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
            line,
        )
        if not m:
            continue
        step = m.group(1)
        if step == "#":
            continue
        rows.append({
            "step": int(step),
            "batch": m.group(2),
            "started": m.group(3),
            "wall": m.group(4),
            "norms": m.group(5),
            "veredictos": m.group(6),
            "refusals": m.group(7),
            "errors": m.group(8),
            "top_refusal": m.group(9),
        })
    return rows


def _active_batch(completed: list[dict]) -> str | None:
    """Best-effort answer to "what batch is running right now?".

    Priority order:
      1. Inspect `ps` for a live launcher subprocess and parse its --batch
         flag (this is the ground truth — works regardless of which subset
         of CASCADE_BATCHES the driver was configured to run).
      2. Fall back to "next batch in CASCADE_BATCHES not yet in completed".
         Useful when the driver is between batches (no launcher subprocess
         momentarily) or after a clean halt.
    """
    try:
        ps = subprocess.run(
            ["ps", "-eo", "command"],
            capture_output=True, text=True, timeout=5,
        )
        if ps.returncode == 0:
            for line in ps.stdout.splitlines():
                if "launch_batch.sh --batch " in line:
                    parts = line.split("--batch ", 1)[1].split()
                    if parts:
                        return parts[0]
    except Exception:
        pass

    done_batches = {row["batch"] for row in completed}
    for b in CASCADE_BATCHES:
        if b not in done_batches:
            return b
    return None


def _read_active_heartbeat(batch: str) -> dict | None:
    p = RUN_DIR_BASE / batch / "heartbeat_stats.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_active_run_state(batch: str) -> dict | None:
    p = RUN_DIR_BASE / batch / "run_state.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _postgres_norm_count() -> int | None:
    try:
        r = subprocess.run(
            ["docker", "exec", "supabase_db_lia-graph", "psql", "-U", "postgres",
             "-tAc", "SELECT COUNT(DISTINCT norm_id) FROM norm_vigencia_history;"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            return int(r.stdout.strip())
    except Exception:
        pass
    return None


def _campaign_totals(completed: list[dict]) -> dict:
    veredictos = 0
    refusals = 0
    errors = 0
    for row in completed:
        try:
            veredictos += int(row["veredictos"])
        except (ValueError, TypeError):
            pass
        try:
            refusals += int(row["refusals"])
        except (ValueError, TypeError):
            pass
        try:
            errors += int(row["errors"])
        except (ValueError, TypeError):
            pass
    return {"veredictos": veredictos, "refusals": refusals, "errors": errors}


def main() -> int:
    completed = _completed_batches()
    totals = _campaign_totals(completed)
    active = _active_batch(completed)
    alive, pid = _driver_alive()
    pg_count = _postgres_norm_count()

    # Status line for cron parser.
    state = "RUNNING" if alive else ("COMPLETE" if active is None else "STOPPED")
    print(f"STATE={state}|DRIVER_ALIVE={alive}|STEP={len(completed) + (1 if active else 0)}|TOTAL={len(CASCADE_BATCHES)}|ACTIVE={active or '—'}|PG_NORMS={pg_count if pg_count is not None else '?'}")

    # Markdown block.
    print()
    print(f"## Cascade v5 heartbeat — {_bog_now()}")
    print()
    print(f"- **Driver**: {'✅ alive' if alive else '🛑 not running'} · pid {pid or '?'}")
    print(f"- **Progress**: {len(completed)}/{len(CASCADE_BATCHES)} batches complete")
    print(f"- **Cumulative this cascade**: {totals['veredictos']} veredictos · {totals['refusals']} refusals · {totals['errors']} errors")
    if pg_count is not None:
        print(f"- **Postgres `norm_vigencia_history`**: {pg_count} distinct verified norms total (started session at 758)")

    # Active batch details.
    if active and alive:
        hb = _read_active_heartbeat(active)
        rs = _read_active_run_state(active)
        print()
        print(f"### Active batch: **{active}** (step {len(completed) + 1}/{len(CASCADE_BATCHES)})")
        if rs:
            print(f"- run_state.phase: `{rs.get('phase')}` (updated {rs.get('updated_bogota','?')})")
        if hb:
            print(f"- {hb.get('headline','?')}")
            print(f"- elapsed: {hb.get('elapsed','?')} · last event {hb.get('fresh_label','?')}")
            top = (hb.get('refusal_reasons_top') or {})
            if top:
                top_str = ", ".join(f"{k}({v})" for k, v in list(top.items())[:3])
                print(f"- top refusal reasons: {top_str}")
        else:
            print("- no heartbeat snapshot yet (extract just started)")

    # Last 5 batch outcomes table tail.
    if completed:
        print()
        print(f"### Last {min(5, len(completed))} completed batches")
        print()
        print("| step | batch | wall | norms | ver | refs | errs | top_refusal |")
        print("|---:|---|---:|---:|---:|---:|---:|---|")
        for row in completed[-5:]:
            print(f"| {row['step']} | {row['batch']} | {row['wall']} | {row['norms']} | {row['veredictos']} | {row['refusals']} | {row['errors']} | {row['top_refusal']} |")

    if not alive and active is not None:
        print()
        print(f"⚠️  **Driver is not alive but cascade is incomplete.** Investigate `logs/cascade_v5_driver.log` and `logs/cascade_v5_{active}.log`.")

    if active is None:
        print()
        print("✅ **Cascade complete** — all 22 batches accounted for in the campaign log.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
