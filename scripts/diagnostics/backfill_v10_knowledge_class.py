"""fix_v10_may Phase 10A Path A — cloud Supabase UPDATE backfill.

Retags the 2,877 document_chunks rows whose parent doc is
interpretative_guidance (1,414) or practica_erp (1,463) but were
mistagged as normative_base by the pre-10A sink bug.

Idempotent: the `.eq("knowledge_class", "normative_base")` predicate
makes already-fixed rows no-ops on re-run.

Safety: writes only touch chunks whose `doc_id` belongs to a
correctly-tagged parent document. The classes are looked up from
`documents.knowledge_class` (correct today), not from the path or
manifest.

Run from repo root (after the probe confirms Path A):
    set -a; source .env.staging; set +a
    PYTHONPATH=src:. uv run python scripts/diagnostics/backfill_v10_knowledge_class.py [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, "src")

from lia_graph.supabase_client import create_supabase_client_for_target


def _doc_ids_for_class(client, knowledge_class: str) -> list[str]:
    resp = (
        client.table("documents")
        .select("doc_id")
        .eq("knowledge_class", knowledge_class)
        .execute()
    )
    return [
        str(row.get("doc_id"))
        for row in (resp.data or [])
        if row.get("doc_id")
    ]


def _count_mistagged_chunks(client, doc_ids: list[str]) -> int:
    """How many chunks of this doc-set currently say normative_base."""
    if not doc_ids:
        return 0
    total = 0
    for start in range(0, len(doc_ids), 50):
        batch = doc_ids[start : start + 50]
        resp = (
            client.table("document_chunks")
            .select("chunk_id", count="exact")
            .in_("doc_id", batch)
            .eq("knowledge_class", "normative_base")
            .limit(0)
            .execute()
        )
        total += int(resp.count or 0)
    return total


def _retag_chunks(
    client, doc_ids: list[str], target_class: str, *, dry_run: bool
) -> int:
    if not doc_ids:
        return 0
    if dry_run:
        return _count_mistagged_chunks(client, doc_ids)
    touched = 0
    for start in range(0, len(doc_ids), 50):
        batch = doc_ids[start : start + 50]
        # Count BEFORE the update so we can report the actual touched rows
        # (PostgREST's update response payload doesn't include count by
        # default, and we don't want to widen surface for this one shot).
        pre = (
            client.table("document_chunks")
            .select("chunk_id", count="exact")
            .in_("doc_id", batch)
            .eq("knowledge_class", "normative_base")
            .limit(0)
            .execute()
        )
        pre_n = int(pre.count or 0)
        (
            client.table("document_chunks")
            .update({"knowledge_class": target_class})
            .in_("doc_id", batch)
            .eq("knowledge_class", "normative_base")
            .execute()
        )
        touched += pre_n
    return touched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count what WOULD be updated; do not write.",
    )
    args = parser.parse_args()

    if not os.environ.get("SUPABASE_URL"):
        print(
            "SUPABASE_URL unset — run: set -a; source .env.staging; set +a",
            file=sys.stderr,
        )
        return 2

    client = create_supabase_client_for_target("production")

    bogota = ZoneInfo("America/Bogota")
    stamp = datetime.now(bogota).strftime("%Y-%m-%d %I:%M:%S %p")
    mode = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"=== fix_v10_may Path A backfill — {stamp} Bogotá [{mode}] ===\n")

    print("Step 1/2 — interpretative_guidance retag")
    interp_doc_ids = _doc_ids_for_class(client, "interpretative_guidance")
    print(f"  parent docs: {len(interp_doc_ids)}")
    interp_touched = _retag_chunks(
        client,
        interp_doc_ids,
        "interpretative_guidance",
        dry_run=args.dry_run,
    )
    label = "would retag" if args.dry_run else "retagged"
    print(f"  chunks {label}: {interp_touched}")

    print("\nStep 2/2 — practica_erp retag")
    practica_doc_ids = _doc_ids_for_class(client, "practica_erp")
    print(f"  parent docs: {len(practica_doc_ids)}")
    practica_touched = _retag_chunks(
        client,
        practica_doc_ids,
        "practica_erp",
        dry_run=args.dry_run,
    )
    print(f"  chunks {label}: {practica_touched}")

    total = interp_touched + practica_touched
    print(f"\nTotal chunks {label}: {total}")
    if args.dry_run:
        print(
            "\nDry-run only — no writes performed. Re-run without "
            "--dry-run to apply."
        )
    else:
        print(
            "\n✅ Backfill complete. Re-run the probe to verify:"
            "\n   PYTHONPATH=src:. uv run python "
            "scripts/diagnostics/probe_v10_knowledge_class.py"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
