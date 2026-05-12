"""fix_v11_may Phase 11A — trust_tier coverage probe.

Two read-only checks against cloud Supabase:

1. Post-backfill distribution. Report the count of chunks per
   trust_tier within `knowledge_class = 'interpretative_guidance'`.
   The §2.A target is roughly 3-5 % high, 70-80 % medium, balance
   low — a wildly different distribution means either the allowlist
   drifted or the backfill didn't run.

2. Allowlist coverage. List the unique `documents.authority` values
   among interpretation docs that the current allowlist did NOT
   match. Operator reviews this list monthly to decide whether to
   promote any frequently-cited firms into the high or medium
   tiers, or to demote noisy authors into low.

Usage:
    set -a; source .env.staging; set +a
    PYTHONPATH=src:. uv run python \\
        scripts/diagnostics/probe_v11_trust_tier_coverage.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, "src")

from lia_graph.supabase_client import create_supabase_client_for_target


_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALLOWLIST_PATH = _REPO_ROOT / "config" / "provider_trust_tiers.json"


def _load_allowlist_needles(path: Path) -> list[str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    tiers_block = raw.get("tiers") or {}
    needles: list[str] = []
    for tier in ("high", "medium", "low"):
        for entry in tiers_block.get(tier) or []:
            s = str(entry or "").strip().lower()
            if s:
                needles.append(s)
    return needles


def _matched_by_allowlist(authority: str, needles: list[str]) -> bool:
    a = (authority or "").strip().lower()
    if not a:
        return False
    return any(n in a for n in needles)


def _fetch_interp_chunks_tier_dist(client) -> Counter[str]:
    """Count chunks per trust_tier for interpretation docs.

    Pulls in pages of (doc_id, chunk_id, trust_tier) — the chunk
    table doesn't carry knowledge_class natively before Phase 10A
    but it does today, so we filter directly on it. Tier values are
    normalized lowercase; unknown/missing → 'medium' for the report.
    """
    counts: Counter[str] = Counter()
    page = 0
    page_size = 1000
    while True:
        resp = (
            client.table("document_chunks")
            .select("chunk_id,trust_tier")
            .eq("knowledge_class", "interpretative_guidance")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        )
        batch = list(resp.data or [])
        for row in batch:
            tier = str(row.get("trust_tier") or "medium").strip().lower()
            if tier not in ("high", "medium", "low"):
                tier = "medium"
            counts[tier] += 1
        if len(batch) < page_size:
            break
        page += 1
    return counts


def _fetch_interp_documents(client) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    page = 0
    page_size = 500
    while True:
        resp = (
            client.table("documents")
            .select("doc_id,authority,provider_labels")
            .eq("knowledge_class", "interpretative_guidance")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        )
        batch = list(resp.data or [])
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        default="production",
        choices=("production", "staging", "wip"),
    )
    parser.add_argument(
        "--max-unmatched",
        type=int,
        default=40,
        help="Truncate unmatched-authority list to this many lines.",
    )
    args = parser.parse_args()

    if not os.environ.get("SUPABASE_URL"):
        print(
            "SUPABASE_URL unset — run: set -a; source .env.staging; set +a",
            file=sys.stderr,
        )
        return 2

    stamp = datetime.now(ZoneInfo("America/Bogota")).strftime(
        "%Y-%m-%d %I:%M:%S %p"
    )
    print(f"=== fix_v11_may Phase 11A trust_tier coverage probe — {stamp} Bogotá ===\n")

    needles = _load_allowlist_needles(_ALLOWLIST_PATH)
    print(f"  allowlist entries: {len(needles)}\n")

    client = create_supabase_client_for_target(args.target)

    # 1. Distribution
    print("Step 1/2 — chunk tier distribution (interpretative_guidance)")
    dist = _fetch_interp_chunks_tier_dist(client)
    total = sum(dist.values()) or 1
    for tier in ("high", "medium", "low"):
        n = dist[tier]
        pct = 100.0 * n / total
        print(f"  trust_tier={tier:<7s}  {n:>5d} chunks  ({pct:5.1f}%)")
    print(f"  total: {total} chunks\n")

    target_high_lo, target_high_hi = 1.0, 8.0
    if total:
        high_pct = 100.0 * dist["high"] / total
        if not (target_high_lo <= high_pct <= target_high_hi):
            print(
                f"  ⚠ high-tier share {high_pct:.1f}% outside expected "
                f"{target_high_lo:.0f}-{target_high_hi:.0f}% — review "
                "allowlist or re-run backfill."
            )
        else:
            print(f"  ✓ high-tier share within expected range.")
    print()

    # 2. Unmatched authorities
    print("Step 2/2 — allowlist coverage (unique unmatched documents.authority)")
    docs = _fetch_interp_documents(client)
    unmatched_auth = Counter()
    for doc in docs:
        auth = str(doc.get("authority") or "").strip()
        if not auth:
            continue
        if not _matched_by_allowlist(auth, needles):
            unmatched_auth[auth] += 1

    print(
        f"  unique unmatched authority values: {len(unmatched_auth)} "
        f"(showing top {args.max_unmatched} by doc count)"
    )
    if not unmatched_auth:
        print("  ✓ every authority value resolves through the allowlist.")
    else:
        for auth, n in unmatched_auth.most_common(args.max_unmatched):
            print(f"    {n:>4d} docs  ::  {auth}")

    print()
    print(
        "Probe done. To promote/demote firms, edit "
        "config/provider_trust_tiers.json and re-run the backfill."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
