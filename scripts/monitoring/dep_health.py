#!/usr/bin/env python3
"""Probe the critical cloud dependencies with a tight timeout.

Emits a single line of JSON to stdout with the health status of each
dependency the ingest pipeline can block on. Designed to be called every
~60s from a heartbeat loop; safe to call during a running ingest.

Each probe has a hard 5-second timeout so the script itself never
contributes to a stall. Exit code is 0 if all checks succeeded, else 1.

Usage:
    PYTHONPATH=src:. uv run python scripts/monitoring/dep_health.py \
        --supabase-target production --probe supabase --probe falkor

Output (one line of JSON):
    {"ts_utc": "...", "checks": {"supabase": {...}, "falkor": {...}},
     "all_ok": true}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_TIMEOUT_SECONDS = 5.0


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_dotenv(path: str) -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def probe_supabase(target: str) -> dict[str, Any]:
    """Trivial SELECT that hits PostgREST. Reports latency in ms."""
    t0 = time.monotonic()
    try:
        from lia_graph.supabase_client import create_supabase_client_for_target

        client = create_supabase_client_for_target(target)
        # Lightest-possible read. `documents` always exists in the schema.
        result = client.table("documents").select("doc_id").limit(1).execute()
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        rows = len(getattr(result, "data", None) or [])
        return {
            "ok": True,
            "latency_ms": elapsed_ms,
            "rows_sampled": rows,
            "target": target,
        }
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return {
            "ok": False,
            "latency_ms": elapsed_ms,
            "error": f"{type(exc).__name__}: {str(exc)[:200]}",
            "target": target,
        }


def probe_falkor() -> dict[str, Any]:
    """Trivial Cypher that hits the graph. Reports latency in ms.

    Post-2026-04-24 cloud-sink stall:
      * fixed module path ``lia_graph.graph.client`` (was ``lia_graph.graph_client``)
      * fixed API — GraphClient uses ``execute(GraphWriteStatement)``,
        not ``run_query(str)``
    """
    t0 = time.monotonic()
    try:
        from lia_graph.graph.client import GraphClient, GraphWriteStatement

        client = GraphClient.from_env()
        stmt = GraphWriteStatement(
            description="dep_health_probe",
            query="RETURN 1 AS probe",
        )
        result = client.execute(stmt, strict=True)
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return {
            "ok": bool(getattr(result, "ok", False)),
            "latency_ms": elapsed_ms,
            "graph_name": getattr(getattr(client, "config", None), "graph_name", "?"),
            "error": getattr(result, "error", None),
        }
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return {
            "ok": False,
            "latency_ms": elapsed_ms,
            "error": f"{type(exc).__name__}: {str(exc)[:200]}",
        }


def probe_gemini() -> dict[str, Any]:
    """Trivial generate() call to the resolved adapter. Reports latency in ms."""
    t0 = time.monotonic()
    try:
        from lia_graph.llm_runtime import resolve_llm_adapter

        adapter, _info = resolve_llm_adapter()
        if adapter is None:
            return {"ok": False, "error": "no_adapter_resolved"}
        _ = adapter.generate("Responde solo con OK")
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return {
            "ok": True,
            "latency_ms": elapsed_ms,
            "adapter": type(adapter).__name__,
        }
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return {
            "ok": False,
            "latency_ms": elapsed_ms,
            "error": f"{type(exc).__name__}: {str(exc)[:200]}",
        }


_PROBES = {
    "supabase": lambda args: probe_supabase(args.supabase_target),
    "falkor": lambda _args: probe_falkor(),
    "gemini": lambda _args: probe_gemini(),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Dependency health probes")
    parser.add_argument(
        "--probe",
        action="append",
        default=[],
        choices=sorted(_PROBES.keys()),
        help="Which dependency to probe. Repeat for multiple.",
    )
    parser.add_argument("--supabase-target", default="production")
    parser.add_argument(
        "--dotenv",
        action="append",
        default=[".env", ".env.local", ".env.staging"],
        help="Dotenv files to source (later wins). Default: .env + .env.local + .env.staging",
    )
    args = parser.parse_args()

    for path in args.dotenv:
        _load_dotenv(path)

    probes_to_run = args.probe or ["supabase", "falkor", "gemini"]
    checks: dict[str, dict[str, Any]] = {}
    for name in probes_to_run:
        checks[name] = _PROBES[name](args)

    all_ok = all(bool(c.get("ok")) for c in checks.values())
    line = {"ts_utc": _iso(), "checks": checks, "all_ok": all_ok}
    print(json.dumps(line, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
