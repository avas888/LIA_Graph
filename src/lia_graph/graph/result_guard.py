"""Defensive guard for FalkorDB result-set cap (next_v4 §6.5.E).

FalkorDB's server caps RESP response rows at ``MAX_RESULTSET_SIZE`` (default
10,000). When a query returns ≥ the cap, the server truncates the tail
**silently** — no error, no flag in the response. The audit on 2026-04-26
confirmed every current runtime query is bounded well below 10,000, but a
future change could regress that without anyone noticing.

This module emits a structured warning event whenever a query returns at
least ``cap`` rows, so a regression is immediately visible in the event log
instead of as mystery-incomplete answers downstream.

Cap value:
    * Default 10,000 (FalkorDB documented default, empirically verified
      against staging on 2026-04-26).
    * Override via ``FALKORDB_RESULTSET_SIZE_CAP`` env if the cluster has
      been reconfigured.

The guard is fire-and-forget: it never raises, never modifies the result,
and never blocks the call path (Invariant I2 — the Falkor adapter's job
is to propagate cloud outages, not to add new failure modes).
"""

from __future__ import annotations

import os
from typing import Any

_DEFAULT_CAP = 10000


def _resolve_cap() -> int:
    raw = os.getenv("FALKORDB_RESULTSET_SIZE_CAP", "")
    try:
        value = int(raw) if raw else _DEFAULT_CAP
    except ValueError:
        value = _DEFAULT_CAP
    return max(1, value)


def check_resultset_cap(
    *,
    description: str,
    query: str,
    row_count: int,
) -> None:
    """Emit ``graph.resultset_cap_reached`` if ``row_count`` is at the cap.

    Called from ``GraphClient.execute`` after each successful query. No-op
    when row count is below the cap. The event payload is structured so
    operators can grep ``logs/events.jsonl`` for the regression.
    """
    cap = _resolve_cap()
    if row_count < cap:
        return
    try:
        from ..instrumentation import emit_event

        emit_event(
            "graph.resultset_cap_reached",
            {
                "description": description,
                "query_preview": (query[:200] + "…") if len(query) > 200 else query,
                "row_count": int(row_count),
                "cap": int(cap),
                "implication": (
                    "FalkorDB truncated this response at the server cap. "
                    "Result is silently incomplete; add LIMIT/pagination."
                ),
            },
        )
    except Exception:  # noqa: BLE001
        # Observability failures must never break the read path.
        pass


__all__ = ["check_resultset_cap"]
