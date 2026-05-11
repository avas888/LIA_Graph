"""fix_v10_may §9.1 probe — does cloud Supabase already hold the
interpretation chunks, just mistagged?

Read-only. Counts document_chunks broken down by knowledge_class,
plus the cross-count of how many chunks descend from documents
flagged as `interpretative_guidance` (or sitting under an
EXPERTOS/ path).

Decides whether Phase 10A's data fix is a 30-sec UPDATE backfill
(chunks exist, just mislabeled) or a ~30-min full re-ingest
(chunks never landed).

Run from repo root:
    set -a; source .env.staging; set +a
    PYTHONPATH=src:. uv run python scripts/diagnostics/probe_v10_knowledge_class.py

Throwaway. See docs/re-engineer/fix/fix_v10_may_diagnosis.md.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, "src")

from lia_graph.supabase_client import (
    create_supabase_client_for_target,
)


def _count(client, table: str, **filters) -> int:
    query = client.table(table).select("*", count="exact").limit(0)
    for column, value in filters.items():
        query = query.eq(column, value)
    return int(query.execute().count or 0)


def _count_chunks_for_doc_ids(client, doc_ids: list[str]) -> int:
    """Count chunks whose doc_id is in the given list (batched to
    keep URL length manageable)."""
    if not doc_ids:
        return 0
    total = 0
    chunk_batch = 50
    for start in range(0, len(doc_ids), chunk_batch):
        batch = doc_ids[start : start + chunk_batch]
        resp = (
            client.table("document_chunks")
            .select("chunk_id", count="exact")
            .in_("doc_id", batch)
            .limit(0)
            .execute()
        )
        total += int(resp.count or 0)
    return total


def _interp_doc_ids(client) -> tuple[list[str], list[str]]:
    """Return (doc_ids tagged interpretative_guidance,
    doc_ids matching EXPERTOS/ path)."""
    tagged_resp = (
        client.table("documents")
        .select("doc_id")
        .eq("knowledge_class", "interpretative_guidance")
        .execute()
    )
    tagged = [
        str(row.get("doc_id"))
        for row in (tagged_resp.data or [])
        if row.get("doc_id")
    ]

    # PostgREST `like` filter — % wildcard
    path_resp = (
        client.table("documents")
        .select("doc_id")
        .like("relative_path", "%EXPERTOS%")
        .execute()
    )
    by_path = [
        str(row.get("doc_id"))
        for row in (path_resp.data or [])
        if row.get("doc_id")
    ]
    return tagged, by_path


def _practica_doc_ids(client) -> list[str]:
    """Return doc_ids tagged practica_erp at the documents level."""
    resp = (
        client.table("documents")
        .select("doc_id")
        .eq("knowledge_class", "practica_erp")
        .execute()
    )
    return [
        str(row.get("doc_id"))
        for row in (resp.data or [])
        if row.get("doc_id")
    ]


def main() -> int:
    if not os.environ.get("SUPABASE_URL"):
        print(
            "SUPABASE_URL unset — run: set -a; source .env.staging; set +a",
            file=sys.stderr,
        )
        return 2

    client = create_supabase_client_for_target("production")

    bogota_now = datetime.now(ZoneInfo("America/Bogota"))
    stamp = bogota_now.strftime("%Y-%m-%d %I:%M:%S %p")
    print(f"=== fix_v10_may §9.1 probe — {stamp} Bogotá ===\n")

    print("--- document_chunks counts (by knowledge_class) ---")
    total_chunks = _count(client, "document_chunks")
    tagged_interp = _count(
        client, "document_chunks", knowledge_class="interpretative_guidance"
    )
    tagged_practica = _count(
        client, "document_chunks", knowledge_class="practica_erp"
    )
    tagged_norm = _count(
        client, "document_chunks", knowledge_class="normative_base"
    )
    tagged_unknown = _count(
        client, "document_chunks", knowledge_class="unknown"
    )
    print(f"  total_chunks:           {total_chunks:>8}")
    print(f"  tagged_interp:          {tagged_interp:>8}")
    print(f"  tagged_practica:        {tagged_practica:>8}")
    print(f"  tagged_norm:            {tagged_norm:>8}")
    print(f"  tagged_unknown:         {tagged_unknown:>8}")

    other = total_chunks - tagged_interp - tagged_practica - tagged_norm - tagged_unknown
    if other:
        print(f"  (other / NULL):         {other:>8}")

    print("\n--- documents counts (by knowledge_class) ---")
    for kc in (
        "normative_base",
        "practica_erp",
        "interpretative_guidance",
        "unknown",
    ):
        n = _count(client, "documents", knowledge_class=kc)
        print(f"  {kc:<28} {n:>6}")

    print("\n--- interp_chunks_by_parent (the keystone signal) ---")
    tagged_doc_ids, path_doc_ids = _interp_doc_ids(client)
    union = sorted(set(tagged_doc_ids) | set(path_doc_ids))
    print(f"  docs tagged interpretative_guidance:  {len(tagged_doc_ids):>5}")
    print(f"  docs matching path %EXPERTOS%:        {len(path_doc_ids):>5}")
    print(f"  union (deduped):                      {len(union):>5}")

    interp_chunks = _count_chunks_for_doc_ids(client, union)
    print(f"  chunks descending from those docs:    {interp_chunks:>5}")

    print("\n--- practica_erp_chunks_by_parent (sibling check) ---")
    practica_doc_ids = _practica_doc_ids(client)
    print(f"  docs tagged practica_erp:             {len(practica_doc_ids):>5}")
    practica_chunks = _count_chunks_for_doc_ids(client, practica_doc_ids)
    print(f"  chunks descending from those docs:    {practica_chunks:>5}")

    print("\n--- decision ---")
    if tagged_interp == 0 and interp_chunks >= 500:
        verdict = (
            "PATH A — UPDATE backfill (chunks already in Supabase, "
            "just mistagged). ~30 sec."
        )
    elif tagged_interp == 0 and interp_chunks < 500:
        verdict = (
            "PATH B — full re-ingest (chunks never landed). ~30 min."
        )
    elif tagged_interp >= 1000:
        verdict = (
            "ALREADY FIXED — tagged_interp is healthy. Skip Phase 10A "
            "data fix; jump to Phase 10B work."
        )
    else:
        verdict = (
            f"PARTIAL / DRIFT — tagged_interp={tagged_interp}, "
            f"interp_chunks_by_parent={interp_chunks}. Investigate "
            "before proceeding."
        )
    print(f"  {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
