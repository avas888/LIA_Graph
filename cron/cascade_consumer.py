"""Cron worker: consumes the vigencia re-verify queue.

Reads `vigencia_reverify_queue` rows where `processed_at IS NULL`, invokes
the vigencia-checker skill on each `norm_id`, INSERTs the resulting v3
`Vigencia` row to `norm_vigencia_history`, and marks the queue row as
processed. Idempotent — re-running on a partially-drained queue is safe.

Usage (deployed via Railway):
  PYTHONPATH=src:. uv run python -m cron.cascade_consumer \\
      --target staging \\
      --max-rows 50 \\
      [--once]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

LOGGER = logging.getLogger("cascade_consumer")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--target", default=os.getenv("LIA_SUPABASE_TARGET", "staging"))
    p.add_argument("--max-rows", type=int, default=50, help="Max queue rows per tick.")
    p.add_argument("--once", action="store_true", help="Run one tick and exit (default).")
    p.add_argument("--loop-seconds", type=int, default=21600,
                   help="When --loop, sleep N seconds between ticks (default: 6h).")
    p.add_argument("--loop", action="store_true", help="Run forever, sleeping between ticks.")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if args.once and args.loop:
        LOGGER.error("--once and --loop are mutually exclusive")
        return 2

    if args.loop:
        while True:
            tick(args)
            LOGGER.info("Sleeping %ds before next cron tick", args.loop_seconds)
            time.sleep(args.loop_seconds)
    else:
        tick(args)
    return 0


def tick(args: argparse.Namespace) -> None:
    from lia_graph.persistence.norm_history_writer import NormHistoryWriter
    from lia_graph.supabase_client import create_supabase_client_for_target
    from lia_graph.vigencia import Vigencia
    # Lazy-import the harness so test environments without the API key can
    # still load this module.
    try:
        from lia_graph.vigencia_extractor import VigenciaSkillHarness
    except Exception as err:  # pragma: no cover
        LOGGER.error("Cannot import VigenciaSkillHarness: %s", err)
        VigenciaSkillHarness = None  # type: ignore[assignment]

    client = create_supabase_client_for_target(args.target)
    writer = NormHistoryWriter(client)

    rows = _fetch_pending(client, limit=args.max_rows)
    LOGGER.info("Picked %d queue rows", len(rows))

    processed = 0
    errors = 0
    for row in rows:
        norm_id = row.get("norm_id")
        try:
            if VigenciaSkillHarness is None:
                LOGGER.warning("Skill harness unavailable; marking %s as deferred", norm_id)
                _mark_processed(client, row["queue_id"], skipped=True, reason="skill_harness_unavailable")
                continue
            harness = VigenciaSkillHarness.default()
            result = harness.verify_norm(norm_id=norm_id)
            if result.veredicto is None:
                LOGGER.info("Skill refused %s: %s", norm_id, result.refusal_reason)
                _mark_processed(client, row["queue_id"], skipped=True, reason=str(result.refusal_reason or ""))
                continue
            prepared = writer.prepare_row(
                norm_id=norm_id,
                veredicto=result.veredicto,
                extracted_by="cron@v1",
                run_id=f"cascade-tick-{_now_compact()}",
                supersede_reason=row.get("supersede_reason") or "periodic_reverify",
            )
            writer.bulk_insert_run([prepared], run_id=prepared.extracted_via.get("run_id") or "cascade")
            _mark_processed(client, row["queue_id"], skipped=False)
            processed += 1
        except Exception as err:  # pragma: no cover
            LOGGER.exception("Failed to process %s: %s", norm_id, err)
            errors += 1
    LOGGER.info("Cron tick complete: processed=%d errors=%d", processed, errors)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fetch_pending(client: Any, *, limit: int) -> list[dict[str, Any]]:
    try:
        resp = (
            client.table("vigencia_reverify_queue")
            .select("*")
            .is_("processed_at", "null")
            .limit(limit)
            .execute()
        )
    except Exception as err:  # pragma: no cover
        LOGGER.warning("Queue fetch failed: %s", err)
        return []
    return list(getattr(resp, "data", None) or [])


def _mark_processed(client: Any, queue_id: str, *, skipped: bool, reason: str = "") -> None:
    try:
        client.table("vigencia_reverify_queue").update(
            {
                "processed_at": _now_iso(),
                "skipped": skipped,
                "skip_reason": reason,
            }
        ).eq("queue_id", queue_id).execute()
    except Exception as err:  # pragma: no cover
        LOGGER.warning("Mark-processed failed for %s: %s", queue_id, err)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


if __name__ == "__main__":
    sys.exit(main())
