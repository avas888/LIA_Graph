"""Cron worker: periodic norm freshness checks (the v2-planned scope).

Walks `norms` rows whose latest `norm_vigencia_history.extracted_at` is
older than the freshness window and enqueues them for re-verification.

Usage (deployed via Railway):
  PYTHONPATH=src:. uv run python -m cron.reverify_periodic \\
      --target staging \\
      --max-age-days 90
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

LOGGER = logging.getLogger("reverify_periodic")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--target", default=os.getenv("LIA_SUPABASE_TARGET", "staging"))
    p.add_argument("--max-age-days", type=int, default=90,
                   help="Re-verify norms whose last extraction is older than this.")
    p.add_argument("--max-rows", type=int, default=200,
                   help="Cap the queue depth per tick.")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    from lia_graph.pipeline_d.vigencia_cascade import (
        CascadeQueueEntry,
        VigenciaCascadeOrchestrator,
    )
    from lia_graph.supabase_client import create_supabase_client_for_target

    client = create_supabase_client_for_target(args.target)
    orchestrator = VigenciaCascadeOrchestrator(client)

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.max_age_days)
    LOGGER.info("Looking for norms whose latest extraction predates %s", cutoff.isoformat())

    stale = _find_stale_norms(client, cutoff=cutoff, limit=args.max_rows)
    LOGGER.info("Stale norms: %d", len(stale))

    for norm_id in stale:
        orchestrator.queue_reverify(norm_id, reason="periodic_reverify")
    return 0


def _find_stale_norms(client: Any, *, cutoff: datetime, limit: int) -> list[str]:
    try:
        resp = (
            client.table("norm_vigencia_history")
            .select("norm_id, extracted_at")
            .order("extracted_at", desc=True)
            .limit(10000)
            .execute()
        )
    except Exception as err:  # pragma: no cover
        LOGGER.warning("Stale-norm fetch failed: %s", err)
        return []
    rows = list(getattr(resp, "data", None) or [])
    latest: dict[str, str] = {}
    for r in rows:
        norm_id = str(r.get("norm_id") or "")
        ts = str(r.get("extracted_at") or "")
        if not norm_id or not ts:
            continue
        if norm_id not in latest:
            latest[norm_id] = ts
    out: list[str] = []
    cutoff_iso = cutoff.isoformat()
    for norm_id, ts in latest.items():
        if ts < cutoff_iso:
            out.append(norm_id)
        if len(out) >= limit:
            break
    return out


if __name__ == "__main__":
    sys.exit(main())
