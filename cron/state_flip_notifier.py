"""Cron worker: 30-day-window state-flip notifier (sub-fix 1F §0.7.2).

Periodic sweep over `norm_vigencia_history` looking for rows whose
`state_until` falls in the next 30 days OR whose future-dated `state_from`
falls in the next 30 days. For each: enqueues a re-verify on dependent
norms (via VigenciaCascadeOrchestrator.on_periodic_tick) AND emits an
operator alert through the heartbeat shape.

Usage (deployed via Railway):
  PYTHONPATH=src:. uv run python -m cron.state_flip_notifier \\
      --target staging \\
      --window-days 30
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("state_flip_notifier")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--target", default=os.getenv("LIA_SUPABASE_TARGET", "staging"))
    p.add_argument("--window-days", type=int, default=30)
    p.add_argument(
        "--alert-log",
        default="logs/state_flip_alerts.jsonl",
        help="Append heartbeat-shaped alerts here.",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    from lia_graph.pipeline_d.vigencia_cascade import VigenciaCascadeOrchestrator
    from lia_graph.supabase_client import create_supabase_client_for_target

    client = create_supabase_client_for_target(args.target)
    orchestrator = VigenciaCascadeOrchestrator(client)

    result = orchestrator.on_periodic_tick(flip_window_days=args.window_days)
    LOGGER.info(
        "Periodic tick: rows_inspected=%d queued=%d flips_notified=%d",
        result.rows_inspected,
        result.queued,
        result.flips_notified,
    )

    alert_path = Path(args.alert_log)
    alert_path.parent.mkdir(parents=True, exist_ok=True)
    with alert_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "worker": "state_flip_notifier",
            "rows_inspected": result.rows_inspected,
            "queued": result.queued,
            "flips_in_window": [e.to_dict() for e in result.queue_entries],
        }, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
