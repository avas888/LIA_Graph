"""fixplan_v3 §0.3.2 + sub-fix 1B-γ — Falkor mirror of the v3 vigencia tables.

Reads `norms` + `norm_vigencia_history` from Supabase and MERGEs `(:Norm)`
nodes + the structured edges (DEROGATED_BY / MODIFIED_BY / SUSPENDED_BY /
INEXEQUIBLE_BY / CONDITIONALLY_EXEQUIBLE_BY / MODULATED_BY / REVIVED_BY /
IS_SUB_UNIT_OF) into the regulatory graph.

Usage:
  PYTHONPATH=src:. uv run python scripts/canonicalizer/sync_vigencia_to_falkor.py [options]

Options:
  --target {production|staging|local}    Supabase target (default: staging)
  --rebuild-from-postgres                 Wipe (:Norm) subgraph first
  --confirm                              Required when --rebuild-from-postgres
  --from-record-id <ts>                  Replay history starting at a checkpoint
  --dry-run                              Print Cypher only, do not execute
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any, Iterable, Mapping

LOGGER = logging.getLogger("sync_vigencia_to_falkor")


_STATE_TO_EDGE = {
    "VM": "MODIFIED_BY",
    "DE": "DEROGATED_BY",
    "DT": "DEROGATED_BY",
    "SP": "SUSPENDED_BY",
    "IE": "INEXEQUIBLE_BY",
    "EC": "CONDITIONALLY_EXEQUIBLE_BY",
    "VC": "MODULATED_BY",
    "RV": "REVIVED_BY",
    # V / VL / DI don't emit a direct edge — only the (:Norm) node update.
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--target", default=os.getenv("LIA_FALKOR_TARGET", "staging"))
    p.add_argument("--rebuild-from-postgres", action="store_true",
                   help="DETACH DELETE every (:Norm) node before re-MERGE.")
    p.add_argument("--confirm", action="store_true", help="Required for --rebuild-from-postgres.")
    p.add_argument("--from-record-id", default=None, help="Resume from a record_id checkpoint.")
    p.add_argument("--dry-run", action="store_true", help="Print Cypher only.")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if args.rebuild_from_postgres and not args.confirm:
        LOGGER.error(
            "--rebuild-from-postgres requires --confirm (drops every (:Norm) node)."
        )
        return 2

    try:
        from lia_graph.supabase_client import create_supabase_client_for_target  # noqa: WPS433
    except Exception as err:  # pragma: no cover — env-dependent
        LOGGER.error("Cannot import Supabase client: %s", err)
        return 3

    try:
        from lia_graph.graph.client import GraphClient, GraphWriteStatement  # type: ignore
    except Exception as err:  # pragma: no cover
        LOGGER.error("Cannot import GraphClient: %s", err)
        return 4

    graph_client: Any = None
    if not args.dry_run:
        graph_client = GraphClient.from_env()
        if not graph_client.config.is_configured:
            LOGGER.error("FALKORDB_URL not configured — set env or use --dry-run")
            return 5

    sb = create_supabase_client_for_target(args.target)

    norms = _fetch(sb, "norms")
    history = _fetch(sb, "norm_vigencia_history", filter_record_id_gte=args.from_record_id)

    norm_cypher = _build_norm_merges(norms)
    edge_cypher = _build_edge_merges(history)

    if args.rebuild_from_postgres:
        wipe = "MATCH (n:Norm) DETACH DELETE n"
        if args.dry_run:
            print(wipe + ";")
        else:
            graph_client.execute(GraphWriteStatement(description="wipe-norm-subgraph", query=wipe))

    for i, stmt in enumerate(norm_cypher):
        if args.dry_run:
            print(stmt + ";")
        else:
            graph_client.execute(GraphWriteStatement(description=f"merge-norm-{i}", query=stmt))
    for i, stmt in enumerate(edge_cypher):
        if args.dry_run:
            print(stmt + ";")
        else:
            graph_client.execute(GraphWriteStatement(description=f"merge-edge-{i}", query=stmt))

    LOGGER.info(
        "Sync complete: %d norm nodes, %d edges (rebuild=%s, dry_run=%s)",
        len(norm_cypher),
        len(edge_cypher),
        args.rebuild_from_postgres,
        args.dry_run,
    )
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fetch(sb: Any, table_name: str, *, filter_record_id_gte: str | None = None) -> list[dict[str, Any]]:
    """Read all rows from a Supabase table. Paginates the standard 1000-row limit."""

    out: list[dict[str, Any]] = []
    offset = 0
    page_size = 1000
    while True:
        q = sb.table(table_name).select("*").range(offset, offset + page_size - 1)
        if filter_record_id_gte and table_name == "norm_vigencia_history":
            q = q.gte("record_id", filter_record_id_gte)
        try:
            resp = q.execute()
        except Exception as err:  # pragma: no cover
            LOGGER.warning("Fetch failed for %s offset=%d: %s", table_name, offset, err)
            break
        data = getattr(resp, "data", None) or []
        out.extend(data)
        if len(data) < page_size:
            break
        offset += page_size
    return out


def _build_norm_merges(norms: Iterable[Mapping[str, Any]]) -> list[str]:
    out: list[str] = []
    for n in norms:
        norm_id = n.get("norm_id")
        if not norm_id:
            continue
        props = {
            "norm_id": norm_id,
            "norm_type": n.get("norm_type"),
            "display_label": n.get("display_label"),
            "parent_norm_id": n.get("parent_norm_id"),
            "is_sub_unit": bool(n.get("is_sub_unit")),
            "sub_unit_kind": n.get("sub_unit_kind"),
            "emisor": n.get("emisor"),
            "fecha_emision": str(n.get("fecha_emision") or ""),
            "canonical_url": n.get("canonical_url"),
        }
        out.append(_merge_node_cypher(norm_id, props))
        # IS_SUB_UNIT_OF edge for sub-units
        if n.get("is_sub_unit") and n.get("parent_norm_id"):
            out.append(
                f"MATCH (a:Norm {{norm_id:'{_q(norm_id)}'}}), "
                f"(b:Norm {{norm_id:'{_q(n['parent_norm_id'])}'}}) "
                "MERGE (a)-[:IS_SUB_UNIT_OF]->(b)"
            )
    return out


def _build_edge_merges(history: Iterable[Mapping[str, Any]]) -> list[str]:
    out: list[str] = []
    for h in history:
        state = h.get("state")
        edge_kind = _STATE_TO_EDGE.get(state)
        if not edge_kind:
            continue
        cs = h.get("change_source") or {}
        if not isinstance(cs, dict):
            continue
        source_norm_id = cs.get("source_norm_id")
        norm_id = h.get("norm_id")
        if not (source_norm_id and norm_id):
            continue
        record_id = h.get("record_id") or ""
        props = {
            "record_id": str(record_id),
            "state_from": str(h.get("state_from") or ""),
            "state_until": str(h.get("state_until") or ""),
            "effect_type": cs.get("effect_type"),
        }
        out.append(
            f"MATCH (a:Norm {{norm_id:'{_q(norm_id)}'}}), "
            f"(b:Norm {{norm_id:'{_q(source_norm_id)}'}}) "
            f"MERGE (a)-[r:{edge_kind} {{record_id:'{_q(str(record_id))}'}}]->(b) "
            f"SET {_set_clause(props)}"
        )
    return out


def _merge_node_cypher(norm_id: str, props: Mapping[str, Any]) -> str:
    return (
        f"MERGE (n:Norm {{norm_id:'{_q(norm_id)}'}}) "
        f"SET {_set_clause(props, prefix='n')}"
    )


def _set_clause(props: Mapping[str, Any], *, prefix: str = "r") -> str:
    parts: list[str] = []
    for key, value in props.items():
        if value is None:
            continue
        if isinstance(value, bool):
            parts.append(f"{prefix}.{key}={'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            parts.append(f"{prefix}.{key}={value}")
        else:
            parts.append(f"{prefix}.{key}='{_q(str(value))}'")
    if not parts:
        parts.append(f"{prefix}.last_synced=timestamp()")
    return ", ".join(parts)


def _q(text: str) -> str:
    """Naive single-quote escape for inline Cypher literals."""

    return str(text).replace("\\", "\\\\").replace("'", "\\'")


if __name__ == "__main__":
    sys.exit(main())
