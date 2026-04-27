"""Sub-fix 1B-δ — audit the `norm_citations` table after backfill.

Reports: total chunks, % with ≥ 1 citation, % refused, anchor-strength
distribution. Per fixplan_v3 §2.5 success criteria.

Usage:
  PYTHONPATH=src:. uv run python scripts/ingestion/audit_norm_citations.py \\
      --target staging \\
      [--refusal-log evals/canonicalizer_refusals_v1/refusals.jsonl] \\
      [--output evals/canonicalizer_refusals_v1/audit_report.json]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("audit_norm_citations")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--target", default=os.getenv("LIA_SUPABASE_TARGET", "staging"))
    p.add_argument("--refusal-log", default="evals/canonicalizer_refusals_v1/refusals.jsonl")
    p.add_argument("--output", default="evals/canonicalizer_refusals_v1/audit_report.json")
    p.add_argument("--print-table", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    from lia_graph.supabase_client import create_supabase_client_for_target
    sb = create_supabase_client_for_target(args.target)

    chunk_count = _count(sb, "document_chunks")
    citation_count = _count(sb, "norm_citations")
    norm_count = _count(sb, "norms")

    chunks_with_citations = _count_distinct(sb, "norm_citations", "chunk_id")
    coverage_pct = (chunks_with_citations / chunk_count * 100) if chunk_count else 0.0

    strengths = _count_by(sb, "norm_citations", "anchor_strength")
    roles = _count_by(sb, "norm_citations", "role")

    refusals = _count_refusals(Path(args.refusal_log))

    report = {
        "ts": _now_iso(),
        "target": args.target,
        "chunks_total": chunk_count,
        "chunks_with_citations": chunks_with_citations,
        "coverage_pct": round(coverage_pct, 2),
        "norms_total": norm_count,
        "citations_total": citation_count,
        "anchor_strength_distribution": strengths,
        "role_distribution": roles,
        "refusal_count": refusals["total"],
        "refusal_top_reasons": refusals["top_reasons"],
        "fixplan_v3_target_coverage_pct": 95.0,
        "passes_coverage_target": coverage_pct >= 95.0,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.print_table:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        LOGGER.info(
            "coverage=%.1f%%, citations=%d, refusals=%d, target=%.0f%%",
            coverage_pct,
            citation_count,
            refusals["total"],
            95.0,
        )
    return 0 if report["passes_coverage_target"] else 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count(sb: Any, table: str) -> int:
    try:
        resp = sb.table(table).select("*", count="exact").limit(1).execute()
    except Exception as err:  # pragma: no cover
        LOGGER.warning("Count failed for %s: %s", table, err)
        return 0
    return int(getattr(resp, "count", 0) or 0)


def _count_distinct(sb: Any, table: str, column: str) -> int:
    """Page through all rows and count distinct values of `column`."""

    seen: set[Any] = set()
    offset = 0
    page_size = 5000
    while True:
        try:
            resp = sb.table(table).select(column).range(offset, offset + page_size - 1).execute()
        except Exception as err:  # pragma: no cover
            LOGGER.warning("Distinct fetch failed: %s", err)
            break
        rows = getattr(resp, "data", None) or []
        for r in rows:
            seen.add(r.get(column))
        if len(rows) < page_size:
            break
        offset += page_size
    return len(seen)


def _count_by(sb: Any, table: str, column: str) -> dict[str, int]:
    out: Counter = Counter()
    offset = 0
    page_size = 5000
    while True:
        try:
            resp = sb.table(table).select(column).range(offset, offset + page_size - 1).execute()
        except Exception as err:  # pragma: no cover
            LOGGER.warning("Count-by fetch failed: %s", err)
            break
        rows = getattr(resp, "data", None) or []
        for r in rows:
            out[str(r.get(column))] += 1
        if len(rows) < page_size:
            break
        offset += page_size
    return dict(out)


def _count_refusals(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"total": 0, "top_reasons": []}
    reasons: Counter = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            blob = json.loads(line)
        except Exception:
            continue
        reasons[str(blob.get("reason") or "unknown")] += 1
    return {
        "total": sum(reasons.values()),
        "top_reasons": reasons.most_common(10),
    }


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    sys.exit(main())
