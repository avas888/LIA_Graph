"""fix_v6 phase 7a — project the Supabase ``norms`` catalog into FalkorDB.

Reads every row from Supabase ``norms`` (paginated REST), upserts a
``Norm`` node into Falkor with the v3 norm-keyed schema, then upserts the
``IS_SUB_UNIT_OF`` hierarchy edges from ``parent_norm_id``.

Idempotent by design: every write is a ``MERGE`` on ``norm_id`` so re-runs
skip already-projected rows.

ENV-driven so the same script projects local-supabase → local-falkor (run
with ``.env.local``) and cloud-supabase → cloud-falkor (``.env.staging``).

Usage:
  set -a && source .env.staging && set +a
  PYTHONPATH=src:. uv run python scripts/cloud_promotion/project_norms_to_falkor.py \
      --audit-jsonl tracers_and_logs/logs/project_norms_<run_id>.jsonl

Flags:
  --dry-run        — render Cypher + parameter dicts to stdout, do not execute
  --limit N        — preflight: process only the first N rows (post-ordering)
  --audit-jsonl P  — per-row outcome log (default: tracers_and_logs/logs/...)
  --risk-first     — process long-tail norm_types FIRST (default ON)
  --no-risk-first  — disable risk-first ordering (alphabetical sweep)

Fail-fast (per CLAUDE.md "Fail Fast, Fix Fast" canon):
  abort if >50 errors OR >10% rate after 100 ops, between batches.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from lia_graph.graph.client import GraphClient, GraphClientError  # noqa: E402
from lia_graph.graph.schema import EdgeKind, NodeKind  # noqa: E402

NORM_PROPERTY_FIELDS = (
    "norm_id",
    "norm_type",
    "parent_norm_id",
    "display_label",
    "emisor",
    "fecha_emision",
    "canonical_url",
    "is_sub_unit",
    "sub_unit_kind",
)

# Risk-first: smaller / less-exercised norm_types go first. The big
# 5,298-row oficio_dian and 3,426-row decreto_articulo families are
# deliberately last so a structural error trips fail-fast in the first
# minute, not the 25th.
RISK_FIRST_TYPE_ORDER = (
    "sentencia_ce",
    "decreto_legislativo_articulo",
    "decreto_ley_articulo",
    "concepto_dian_numeral",
    "sentencia_cc",
    "cco_articulo",
    "cst_articulo",
    "res_articulo",
    "ley",
    "resolucion",
    "articulo_et",
    "ley_articulo",
    "decreto",
    "concepto_dian",
    "decreto_articulo",
    "oficio_dian",
)

FAIL_FAST_MAX_ERRORS = 50
FAIL_FAST_MIN_ROWS_FOR_RATE = 100
FAIL_FAST_MAX_RATE_PCT = 10


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _supabase_paginate(url: str, key: str, table: str, page_size: int = 1000):
    """Yield every row from a Supabase table via paginated REST GET."""
    base = url.rstrip("/")
    offset = 0
    while True:
        params = {"select": "*", "order": "norm_id.asc"}
        qs = urllib.parse.urlencode(params)
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
            content_range = resp.headers.get("Content-Range", "")
        rows = json.loads(payload) if payload else []
        if not rows:
            return
        for row in rows:
            yield row
        if len(rows) < page_size:
            return
        offset += len(rows)
        # Defensive: stop if total is known and offset exceeds it.
        try:
            total = int(content_range.split("/")[-1])
            if offset >= total:
                return
        except (ValueError, IndexError):
            pass


def _coerce_property(value):
    """Convert Supabase JSON value into a Falkor-storable scalar."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    # Postgres timestamps / dates arrive as strings already; lists / dicts get
    # serialized so they survive the Cypher round-trip without breaking the
    # `_cypher_literal` recursion (which doesn't handle nested dicts on Norm).
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _row_to_node_payload(row: dict) -> dict | None:
    norm_id = (row.get("norm_id") or "").strip()
    if not norm_id:
        return None
    properties: dict = {}
    for field_name in NORM_PROPERTY_FIELDS:
        if field_name == "norm_id":
            continue
        if field_name not in row:
            continue
        coerced = _coerce_property(row.get(field_name))
        if coerced is None:
            continue
        properties[field_name] = coerced
    # Schema requires norm_id, norm_type, display_label.
    if not properties.get("norm_type") or not properties.get("display_label"):
        return None
    properties["norm_id"] = norm_id  # mirror key into props for traversals
    return {"key": norm_id, "properties": properties}


def _row_to_hierarchy_edge(row: dict) -> dict | None:
    norm_id = (row.get("norm_id") or "").strip()
    parent = (row.get("parent_norm_id") or "").strip() if row.get("parent_norm_id") else ""
    if not norm_id or not parent:
        return None
    if norm_id == parent:
        return None
    return {"source_key": norm_id, "target_key": parent, "properties": {}}


def _risk_first_sort_key(row: dict) -> tuple:
    nt = row.get("norm_type") or ""
    try:
        order = RISK_FIRST_TYPE_ORDER.index(nt)
    except ValueError:
        order = -1  # unknown long-tail families go to the very front
    return (order, row.get("norm_id") or "")


def _write_audit_line(audit_path: Path, payload: dict) -> None:
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _check_fail_fast(error_count: int, total: int) -> str | None:
    if error_count > FAIL_FAST_MAX_ERRORS:
        return f"max_errors: {error_count} > {FAIL_FAST_MAX_ERRORS}"
    if total >= FAIL_FAST_MIN_ROWS_FOR_RATE:
        rate = (error_count * 100) // max(total, 1)
        if rate >= FAIL_FAST_MAX_RATE_PCT:
            return f"error_rate: {rate}% >= {FAIL_FAST_MAX_RATE_PCT}% ({error_count}/{total})"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="render but do not execute")
    parser.add_argument("--limit", type=int, default=None, help="process only the first N rows")
    parser.add_argument(
        "--audit-jsonl",
        type=Path,
        default=None,
        help="per-batch audit log path (default tracers_and_logs/logs/...)",
    )
    parser.add_argument(
        "--risk-first",
        dest="risk_first",
        action="store_true",
        default=True,
        help="process long-tail norm_types FIRST (default)",
    )
    parser.add_argument(
        "--no-risk-first",
        dest="risk_first",
        action="store_false",
        help="disable risk-first ordering",
    )
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    falkor_url = os.environ.get("FALKORDB_URL", "").strip()
    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set", file=sys.stderr)
        return 2
    if not falkor_url and not args.dry_run:
        print("ERROR: FALKORDB_URL not set (required unless --dry-run)", file=sys.stderr)
        return 2

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    audit_path = args.audit_jsonl or (
        REPO_ROOT / "tracers_and_logs" / "logs" / f"project_norms_{run_id}.jsonl"
    )

    is_local = "127.0.0.1" in supabase_url or "localhost" in supabase_url
    target_label = "LOCAL" if is_local else "CLOUD"

    print(f"[{_utcnow_iso()}] run_id={run_id} target={target_label}")
    print(f"[{_utcnow_iso()}] supabase_url={supabase_url}")
    print(f"[{_utcnow_iso()}] audit_jsonl={audit_path}")
    print(f"[{_utcnow_iso()}] reading Supabase norms (paginated)...")

    rows = list(_supabase_paginate(supabase_url, supabase_key, "norms", page_size=1000))
    print(f"[{_utcnow_iso()}] fetched {len(rows)} rows from Supabase norms")

    if args.risk_first:
        rows.sort(key=_risk_first_sort_key)
        type_order_seen = []
        for r in rows[:50]:
            nt = r.get("norm_type") or ""
            if nt not in type_order_seen:
                type_order_seen.append(nt)
        print(f"[{_utcnow_iso()}] risk-first ordering — first types: {type_order_seen[:6]}")

    if args.limit is not None:
        rows = rows[: args.limit]
        print(f"[{_utcnow_iso()}] --limit {args.limit} → processing {len(rows)} rows")

    node_payloads: list[dict] = []
    edge_payloads: list[dict] = []
    skipped_no_required = 0
    for row in rows:
        node = _row_to_node_payload(row)
        if node is None:
            skipped_no_required += 1
            continue
        node_payloads.append(node)
        edge = _row_to_hierarchy_edge(row)
        if edge is not None:
            edge_payloads.append(edge)

    print(
        f"[{_utcnow_iso()}] staged: nodes={len(node_payloads)} edges={len(edge_payloads)} "
        f"skipped_missing_required={skipped_no_required}"
    )

    client = GraphClient.from_env()
    batch_nodes = client.config.batch_size_nodes
    batch_edges = client.config.batch_size_edges
    print(
        f"[{_utcnow_iso()}] graph_name={client.config.graph_name} "
        f"falkor_url={client.config.redacted_url} "
        f"batch_nodes={batch_nodes} batch_edges={batch_edges}"
    )

    error_count = 0
    total_processed = 0
    nodes_created_total = 0
    nodes_set_total = 0
    edges_created_total = 0
    t0 = time.perf_counter()

    # Phase 0: create index on Norm.norm_id (idempotent via _is_benign_index_error).
    if not args.dry_run:
        try:
            idx_stmt = client.stage_index(NodeKind.NORM)
            client.execute(idx_stmt, strict=False)
        except GraphClientError as exc:
            print(f"[{_utcnow_iso()}] WARN index creation: {exc}", file=sys.stderr)

    # Phase 1: nodes.
    print(f"[{_utcnow_iso()}] phase 1/2: upsert {len(node_payloads)} Norm nodes")
    for batch_idx in range(0, len(node_payloads), batch_nodes):
        batch = node_payloads[batch_idx : batch_idx + batch_nodes]
        stmt = client.stage_node_batch(NodeKind.NORM, batch)
        if args.dry_run:
            print(f"--- DRY-RUN node batch {batch_idx}–{batch_idx+len(batch)-1} ---")
            print(stmt.query.strip())
            print(f"  rows={len(batch)} sample_keys={[b['key'] for b in batch[:3]]}")
            total_processed += len(batch)
            continue
        result = client.execute(stmt, strict=False)
        ok = bool(result.ok and not result.error)
        nc = int(result.stats.get("nodes_created", 0) or 0)
        ps = int(result.stats.get("properties_set", 0) or 0)
        nodes_created_total += nc
        nodes_set_total += ps
        outcome = "ok" if ok else "error"
        if not ok:
            error_count += 1
        total_processed += len(batch)
        _write_audit_line(
            audit_path,
            {
                "ts_utc": _utcnow_iso(),
                "phase": "node_upsert",
                "batch_idx": batch_idx,
                "batch_size": len(batch),
                "outcome": outcome,
                "error": result.error,
                "stats": dict(result.stats),
            },
        )
        if (batch_idx // batch_nodes) % 5 == 0 or batch_idx + len(batch) >= len(node_payloads):
            elapsed = time.perf_counter() - t0
            print(
                f"[{_utcnow_iso()}]   nodes {batch_idx+len(batch)}/{len(node_payloads)} "
                f"errors={error_count} created={nodes_created_total} set={nodes_set_total} "
                f"elapsed={elapsed:.1f}s"
            )
        trip = _check_fail_fast(error_count, total_processed)
        if trip is not None:
            print(f"[{_utcnow_iso()}] FAIL-FAST tripped: {trip}", file=sys.stderr)
            _write_audit_line(
                audit_path,
                {"ts_utc": _utcnow_iso(), "phase": "fail_fast", "reason": trip},
            )
            return 3

    # Phase 2: hierarchy edges (IS_SUB_UNIT_OF).
    print(f"[{_utcnow_iso()}] phase 2/2: upsert {len(edge_payloads)} IS_SUB_UNIT_OF edges")
    for batch_idx in range(0, len(edge_payloads), batch_edges):
        batch = edge_payloads[batch_idx : batch_idx + batch_edges]
        stmt = client.stage_edge_batch(
            edge_kind=EdgeKind.IS_SUB_UNIT_OF,
            source_kind=NodeKind.NORM,
            target_kind=NodeKind.NORM,
            rows=batch,
        )
        if args.dry_run:
            print(f"--- DRY-RUN edge batch {batch_idx}–{batch_idx+len(batch)-1} ---")
            print(stmt.query.strip())
            print(
                f"  rows={len(batch)} "
                f"sample={[(b['source_key'], b['target_key']) for b in batch[:3]]}"
            )
            total_processed += len(batch)
            continue
        result = client.execute(stmt, strict=False)
        ok = bool(result.ok and not result.error)
        rc = int(result.stats.get("relationships_created", 0) or 0)
        edges_created_total += rc
        outcome = "ok" if ok else "error"
        if not ok:
            error_count += 1
        total_processed += len(batch)
        _write_audit_line(
            audit_path,
            {
                "ts_utc": _utcnow_iso(),
                "phase": "edge_upsert",
                "batch_idx": batch_idx,
                "batch_size": len(batch),
                "outcome": outcome,
                "error": result.error,
                "stats": dict(result.stats),
            },
        )
        if (batch_idx // batch_edges) % 5 == 0 or batch_idx + len(batch) >= len(edge_payloads):
            elapsed = time.perf_counter() - t0
            print(
                f"[{_utcnow_iso()}]   edges {batch_idx+len(batch)}/{len(edge_payloads)} "
                f"errors={error_count} created={edges_created_total} elapsed={elapsed:.1f}s"
            )
        trip = _check_fail_fast(error_count, total_processed)
        if trip is not None:
            print(f"[{_utcnow_iso()}] FAIL-FAST tripped: {trip}", file=sys.stderr)
            _write_audit_line(
                audit_path,
                {"ts_utc": _utcnow_iso(), "phase": "fail_fast", "reason": trip},
            )
            return 3

    elapsed = time.perf_counter() - t0
    summary = {
        "ts_utc": _utcnow_iso(),
        "run_id": run_id,
        "target": target_label,
        "rows_fetched": len(rows),
        "node_payloads": len(node_payloads),
        "edge_payloads": len(edge_payloads),
        "skipped_missing_required": skipped_no_required,
        "nodes_created": nodes_created_total,
        "properties_set": nodes_set_total,
        "edges_created": edges_created_total,
        "errors": error_count,
        "elapsed_seconds": round(elapsed, 2),
        "phase": "summary",
    }
    _write_audit_line(audit_path, summary)
    print(
        f"[{_utcnow_iso()}] DONE — nodes_created={nodes_created_total} "
        f"edges_created={edges_created_total} errors={error_count} "
        f"elapsed={elapsed:.1f}s"
    )
    print(f"[{_utcnow_iso()}] audit: {audit_path}")
    return 0 if error_count == 0 else 4


if __name__ == "__main__":
    sys.exit(main())
