"""Append an EXTRACT_ONLY ledger row when --skip-post (and implied --skip-score) ran.

Used by `launch_batch.sh` to keep `evals/canonicalizer_run_v1/ledger.jsonl`
contiguous across autonomous runs that intentionally skip the post-verify
chat-replay step. Closes fixplan_v5 §3 #5.

Schema is a strict subset of the full score row in `run_batch_tests.py`:
the test/delta fields are nulled out, and `verdict = "EXTRACT_ONLY"` so
downstream roll-up code can distinguish from PASS/FAIL.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "canonicalizer"))

from run_batch_tests import (  # noqa: E402
    _load_batch,
    _load_extraction_stats,
    _now_bogota,
    _started_bogota_from_elapsed,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--batch-id", required=True)
    p.add_argument("--extraction-run-id", required=True)
    p.add_argument("--extraction-stats", required=True,
                   help="Path to heartbeat_stats.json snapshot.")
    p.add_argument("--batches-config",
                   default="config/canonicalizer_run_v1/batches.yaml")
    p.add_argument("--ledger",
                   default="evals/canonicalizer_run_v1/ledger.jsonl")
    p.add_argument("--attested-by", default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    batch = _load_batch(Path(args.batches_config), args.batch_id)
    if batch is None:
        print(f"[append_extract_only_row] batch {args.batch_id} not in {args.batches_config}",
              file=sys.stderr)
        return 2

    stats = _load_extraction_stats(args.extraction_stats)
    questions = batch.get("test_questions") or []

    row = {
        "batch_id": args.batch_id,
        "phase": batch.get("phase"),
        "title": batch.get("title"),
        "extraction_run_id": args.extraction_run_id or stats.get("run_id"),

        "started_bogota": stats.get("started_bogota") or _started_bogota_from_elapsed(stats),
        "ended_bogota": _now_bogota(),
        "wall_seconds": stats.get("elapsed_seconds"),

        "norms_targeted": stats.get("total"),
        "veredictos": stats.get("successes"),
        "refusals": stats.get("refusals"),
        "errors": stats.get("errors"),
        "states_observed": stats.get("state_counts") or {},
        "refusal_reasons_top": stats.get("refusal_reasons_top") or {},

        "pre_test_results": None,
        "post_test_results": None,
        "delta": None,
        "questions_total": len(questions),
        "questions_passed": None,
        "questions_failed": None,
        "questions_deferred": None,
        "moved_to_pass": None,
        "regressions": None,

        "verdict": "EXTRACT_ONLY",
        "next_batch_unblocked": None,
        "engineer_attest": args.attested_by,
        "sme_spot_check": None,
        "skip_reason": "skip_post_implied_skip_score",

        "per_question": [],
        "ts_bogota": _now_bogota(),
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }

    ledger_path = Path(args.ledger)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[append_extract_only_row] EXTRACT_ONLY row appended to {ledger_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
