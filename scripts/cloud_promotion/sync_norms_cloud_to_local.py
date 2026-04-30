"""fix_v6 phase 7a-sync — copy norms-related Supabase tables cloud → local.

After the 2026-04-29 canonicalizer bulk-write populated cloud Supabase
to 17,169 norms / 9,322 norm_vigencia_history / 106 sub_topic_taxonomy /
52,246 norm_citations, the local Supabase docker is behind. This script
brings local up to cloud parity for the canonical-norms-and-vigencia
tables so that re-projecting local Supabase → local Falkor closes the
last leg of the four-corner parity.

Reads from CLOUD Supabase (REST + service-role), writes to LOCAL via
PostgREST UPSERT. Idempotent on the natural keys declared by each
table's schema (every table has a primary key Supabase honors via
``Prefer: resolution=merge-duplicates``).

ENV expected:
  CLOUD_SUPABASE_URL                — e.g. https://utjndyxgfhkfcrjmtdqz.supabase.co
  CLOUD_SUPABASE_SERVICE_ROLE_KEY   — service-role key for cloud project
  LOCAL_SUPABASE_URL                — e.g. http://127.0.0.1:54321
  LOCAL_SUPABASE_SERVICE_ROLE_KEY   — local docker service-role key

Convenience: if any of the above are missing, the script reads them from
the standard ``SUPABASE_URL`` / ``SUPABASE_SERVICE_ROLE_KEY`` pair using
the heuristic that ``127.0.0.1`` / ``localhost`` is the local target. So
sourcing ``.env.local`` for local creds and passing cloud creds via
CLOUD_* explicitly works out of the box.

Tables synced (in dependency order):
  sub_topic_taxonomy       (small; FK target for chunks)
  norms                    (canonical legal-norms registry)
  norm_vigencia_history    (append-only vigencia state per norm)
  norm_citations           (chunk → norm anchor mapping)

Usage:
  set -a && source .env.local && set +a
  CLOUD_SUPABASE_URL=https://utjndyxgfhkfcrjmtdqz.supabase.co \
  CLOUD_SUPABASE_SERVICE_ROLE_KEY=$STAGING_KEY \
  PYTHONPATH=src:. uv run python scripts/cloud_promotion/sync_norms_cloud_to_local.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Tables synced in this order. PK columns are listed for the
# `on_conflict` clause that PostgREST honors when `resolution=merge-duplicates`.
SYNC_TABLES: tuple[tuple[str, str, str, int], ...] = (
    # (table_name, on_conflict_columns, resolution, page_size)
    # ``resolution`` is the PostgREST Prefer header value:
    #   merge-duplicates  → INSERT … ON CONFLICT DO UPDATE (mutable tables)
    #   ignore-duplicates → INSERT … ON CONFLICT DO NOTHING (append-only)
    # norm_vigencia_history grants service_role only INSERT/SELECT (no
    # UPDATE) — append-only by design — so merge-duplicates 403s.
    # norm_citations has uq_nc_chunk_norm_role beyond the PK; row-set
    # parity is the goal, not field-level updates.
    ("sub_topic_taxonomy", "parent_topic_key,sub_topic_key", "merge-duplicates", 500),
    ("norms", "norm_id", "merge-duplicates", 1000),
    ("norm_vigencia_history", "record_id", "ignore-duplicates", 1000),
    ("norm_citations", "chunk_id,norm_id,role", "ignore-duplicates", 1000),
)

WRITE_BATCH = 500


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_creds() -> tuple[tuple[str, str], tuple[str, str]]:
    """Return ((cloud_url, cloud_key), (local_url, local_key))."""
    cloud_url = os.environ.get("CLOUD_SUPABASE_URL", "").strip()
    cloud_key = os.environ.get("CLOUD_SUPABASE_SERVICE_ROLE_KEY", "").strip()
    local_url = os.environ.get("LOCAL_SUPABASE_URL", "").strip()
    local_key = os.environ.get("LOCAL_SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not cloud_url or not cloud_key or not local_url or not local_key:
        # Fallback heuristic: source SUPABASE_URL/KEY and infer local-vs-cloud
        # from the hostname. Pair the missing side with the configured pair.
        sb_url = os.environ.get("SUPABASE_URL", "").strip()
        sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        is_local = "127.0.0.1" in sb_url or "localhost" in sb_url
        if is_local:
            local_url = local_url or sb_url
            local_key = local_key or sb_key
        else:
            cloud_url = cloud_url or sb_url
            cloud_key = cloud_key or sb_key

    missing = [n for n, v in [
        ("CLOUD_SUPABASE_URL", cloud_url),
        ("CLOUD_SUPABASE_SERVICE_ROLE_KEY", cloud_key),
        ("LOCAL_SUPABASE_URL", local_url),
        ("LOCAL_SUPABASE_SERVICE_ROLE_KEY", local_key),
    ] if not v]
    if missing:
        raise SystemExit(f"missing required env: {missing}")

    return (cloud_url, cloud_key), (local_url, local_key)


def _supabase_paginate(
    url: str,
    key: str,
    table: str,
    *,
    page_size: int,
    order_col: str,
):
    """Yield every row from a Supabase table via paginated REST GET."""
    base = url.rstrip("/")
    offset = 0
    while True:
        qs = urllib.parse.urlencode({"select": "*", "order": f"{order_col}.asc"})
        req = urllib.request.Request(
            f"{base}/rest/v1/{table}?{qs}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Range-Unit": "items",
                "Range": f"{offset}-{offset + page_size - 1}",
                "Prefer": "count=exact",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = resp.read()
        rows = json.loads(payload) if payload else []
        if not rows:
            return
        for row in rows:
            yield row
        if len(rows) < page_size:
            return
        offset += len(rows)


def _supabase_count(url: str, key: str, table: str) -> int:
    base = url.rstrip("/")
    req = urllib.request.Request(
        f"{base}/rest/v1/{table}?select=*",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Prefer": "count=exact",
            "Range": "0-0",
        },
        method="HEAD",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        cr = resp.headers.get("Content-Range", "")
    try:
        return int(cr.split("/")[-1])
    except (ValueError, IndexError):
        return -1


def _supabase_upsert(
    url: str,
    key: str,
    table: str,
    rows: list[dict],
    *,
    on_conflict: str,
    resolution: str = "merge-duplicates",
) -> tuple[int, str | None]:
    """POST batch of rows with the given conflict resolution. Returns (status, err)."""
    if not rows:
        return 200, None
    base = url.rstrip("/")
    qs = urllib.parse.urlencode({"on_conflict": on_conflict})
    body = json.dumps(rows, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/rest/v1/{table}?{qs}",
        data=body,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": f"resolution={resolution},return=minimal",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, None
    except urllib.error.HTTPError as exc:
        try:
            err = exc.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            err = str(exc)
        return exc.code, err
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def _sync_table(
    cloud: tuple[str, str],
    local: tuple[str, str],
    table: str,
    on_conflict: str,
    resolution: str,
    page_size: int,
    audit_path: Path,
) -> dict:
    cloud_url, cloud_key = cloud
    local_url, local_key = local

    cloud_count = _supabase_count(cloud_url, cloud_key, table)
    local_count_before = _supabase_count(local_url, local_key, table)
    print(
        f"[{_utcnow_iso()}] {table}: cloud={cloud_count} local_before={local_count_before}"
    )

    rows_synced = 0
    errors = 0
    t0 = time.perf_counter()
    buffer: list[dict] = []
    for row in _supabase_paginate(
        cloud_url, cloud_key, table, page_size=page_size, order_col=on_conflict
    ):
        buffer.append(row)
        if len(buffer) >= WRITE_BATCH:
            status, err = _supabase_upsert(
                local_url, local_key, table, buffer,
                on_conflict=on_conflict, resolution=resolution,
            )
            outcome = "ok" if status in (200, 201, 204) else "error"
            if outcome != "ok":
                errors += 1
                with audit_path.open("a", encoding="utf-8") as fp:
                    fp.write(
                        json.dumps(
                            {
                                "ts_utc": _utcnow_iso(),
                                "table": table,
                                "phase": "upsert",
                                "outcome": outcome,
                                "status": status,
                                "error": (err or "")[:500],
                                "batch_size": len(buffer),
                            }
                        )
                        + "\n"
                    )
                if errors > 5:
                    print(
                        f"[{_utcnow_iso()}] {table}: ABORT after {errors} batch errors",
                        file=sys.stderr,
                    )
                    return {
                        "table": table,
                        "rows_synced": rows_synced,
                        "errors": errors,
                        "elapsed_seconds": round(time.perf_counter() - t0, 2),
                    }
            rows_synced += len(buffer)
            buffer = []
            if rows_synced % 5000 == 0:
                print(
                    f"[{_utcnow_iso()}] {table}: {rows_synced}/{cloud_count} "
                    f"errors={errors} elapsed={time.perf_counter()-t0:.1f}s"
                )
    if buffer:
        status, err = _supabase_upsert(
            local_url, local_key, table, buffer,
            on_conflict=on_conflict, resolution=resolution,
        )
        outcome = "ok" if status in (200, 201, 204) else "error"
        if outcome != "ok":
            errors += 1
            with audit_path.open("a", encoding="utf-8") as fp:
                fp.write(
                    json.dumps(
                        {
                            "ts_utc": _utcnow_iso(),
                            "table": table,
                            "phase": "upsert_final",
                            "outcome": outcome,
                            "status": status,
                            "error": (err or "")[:500],
                            "batch_size": len(buffer),
                        }
                    )
                    + "\n"
                )
        rows_synced += len(buffer)
    elapsed = time.perf_counter() - t0

    local_count_after = _supabase_count(local_url, local_key, table)
    print(
        f"[{_utcnow_iso()}] {table}: synced={rows_synced} "
        f"local_after={local_count_after} errors={errors} elapsed={elapsed:.1f}s"
    )
    return {
        "table": table,
        "cloud": cloud_count,
        "local_before": local_count_before,
        "local_after": local_count_after,
        "rows_synced": rows_synced,
        "errors": errors,
        "elapsed_seconds": round(elapsed, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tables",
        nargs="+",
        default=None,
        help="subset of tables to sync (default: all)",
    )
    parser.add_argument("--audit-jsonl", type=Path, default=None)
    args = parser.parse_args()

    cloud, local = _get_creds()
    print(f"[{_utcnow_iso()}] cloud={cloud[0]}")
    print(f"[{_utcnow_iso()}] local={local[0]}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    audit_path = args.audit_jsonl or (
        REPO_ROOT / "tracers_and_logs" / "logs" / f"sync_norms_{run_id}.jsonl"
    )
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    selected = args.tables
    summaries = []
    for table_name, on_conflict, resolution, page_size in SYNC_TABLES:
        if selected is not None and table_name not in selected:
            continue
        summary = _sync_table(
            cloud, local, table_name, on_conflict, resolution, page_size, audit_path
        )
        summaries.append(summary)
        with audit_path.open("a", encoding="utf-8") as fp:
            fp.write(
                json.dumps({"ts_utc": _utcnow_iso(), "phase": "table_summary", **summary})
                + "\n"
            )

    print(f"[{_utcnow_iso()}] DONE")
    for s in summaries:
        print(
            f"  {s['table']}: {s.get('local_before','?')} → {s.get('local_after','?')} "
            f"(cloud={s.get('cloud','?')}, errors={s['errors']})"
        )
    print(f"[{_utcnow_iso()}] audit: {audit_path}")
    total_errors = sum(s["errors"] for s in summaries)
    return 0 if total_errors == 0 else 4


if __name__ == "__main__":
    sys.exit(main())
