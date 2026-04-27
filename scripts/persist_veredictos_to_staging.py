#!/usr/bin/env python3
"""Activity 1.5b — Manual veredicto persistence to staging Supabase + Falkor.

Reads the 4 veredicto JSON fixtures produced by Activities 1.5 + 1.6, finds
the corresponding chunks (Supabase) + ArticleNodes (Falkor) in staging cloud,
and persists the structured Vigencia data:

    Supabase:  UPDATE document_chunks SET vigencia=..., vigencia_basis=...
               WHERE chunk_id LIKE '%::<article_key>'
    Falkor:    MERGE structured edges (MODIFIES / DEROGATES / STRUCK_DOWN_BY)
               between ArticleNodes and ReformNodes per skill schema.

Default mode is DRY-RUN — print every proposed write without applying.
Pass --apply to execute writes against staging.

Per Activity 1.5's discrimination, this script does NOT touch:
- Document-level `documents.vigencia` (interpretation docs are not the norm)
- Local Supabase docker (would need separate `supabase db reset` + re-run)
- Production / Railway environment

Usage:
    # Dry run (default):
    PYTHONPATH=src:. uv run python scripts/persist_veredictos_to_staging.py

    # Actually apply writes to staging:
    PYTHONPATH=src:. uv run python scripts/persist_veredictos_to_staging.py --apply

Output:
    evals/activity_1_5/persistence_audit.jsonl  — every write with before/after
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VEREDICTOS_DIR = ROOT / "evals" / "activity_1_5"
AUDIT_LOG = VEREDICTOS_DIR / "persistence_audit.jsonl"

# ---------------------------------------------------------------------------
# Veredicto → persistence-target mapping
# ---------------------------------------------------------------------------
# Each entry maps a veredicto file to:
#   - chunk_pattern: SQL LIKE pattern for document_chunks.chunk_id
#                    (None = no chunk-level update; document-level only)
#   - falkor_op:    Cypher MERGE describing the structured edge to emit
#                   (None = no edge needed; e.g. for state V)
#   - vigencia_for_chunks: target value for document_chunks.vigencia
#                          (per existing Supabase enum: vigente|derogada|...)

PERSISTENCE_PLAN: list[dict[str, Any]] = [
    {
        "veredicto_file": "decreto_1474_2025_veredicto.json",
        "norm_label": "Decreto 1474/2025",
        # Decreto 1474 is NOT the ET — its chunks live in interpretation docs.
        # Per Activity 1.5: don't wholesale-flag interpretations. Only Falkor
        # edge here.
        "chunk_pattern": None,
        "vigencia_for_chunks": None,
        "falkor_op": {
            "description": "Decreto 1474/2025 STRUCK_DOWN_BY Sentencia C-079/2026",
            "cypher": """
                MERGE (decreto:ReformNode {norm_id: 'D-1474-2025'})
                  ON CREATE SET decreto.label = 'Decreto Legislativo 1474 de 2025',
                                decreto.tipo = 'decreto_legislativo_emergencia',
                                decreto.fecha_promulgacion = '2025-12-29'
                MERGE (sentencia:ReformNode {norm_id: 'C-079-2026'})
                  ON CREATE SET sentencia.label = 'Sentencia C-079 de 2026',
                                sentencia.tipo = 'sentencia_corte_constitucional',
                                sentencia.fecha = '2026-04-15'
                MERGE (decreto)-[r:STRUCK_DOWN_BY]->(sentencia)
                  ON CREATE SET r.fecha = '2026-04-15',
                                r.alcance = 'total',
                                r.efectos = 'inmediatos+retroactivos',
                                r.dian_devolucion_ordenada = true,
                                r.activity = 'activity_1_5b',
                                r.recorded_at = '2026-04-26'
                RETURN decreto.norm_id AS source, sentencia.norm_id AS target
            """,
        },
    },
    {
        "veredicto_file": "art_689_3_ET_AG2025_veredicto.json",
        "norm_label": "Art. 689-3 ET",
        "chunk_pattern": "%::689-3",
        "vigencia_for_chunks": "vigente",  # VM → vigente (text is current)
        "falkor_op": {
            "description": "Art. 689-3 ET MODIFIES (modificado por) Ley 2294/2023 Art. 69",
            "cypher": """
                MERGE (art:ArticleNode {article_id: '689-3'})
                  ON CREATE SET art.label = 'Art. 689-3 ET — Beneficio de auditoría'
                MERGE (ley:ReformNode {norm_id: 'Ley-2294-2023'})
                  ON CREATE SET ley.label = 'Ley 2294 de 2023 (PND 2022-2026)',
                                ley.tipo = 'ley',
                                ley.fecha_promulgacion = '2023-05-19'
                MERGE (ley)-[r:MODIFIES]->(art)
                  ON CREATE SET r.articulo_modificador = 'Art. 69',
                                r.fecha = '2023-05-19',
                                r.scope = 'prórroga del beneficio para AG 2024-2026',
                                r.activity = 'activity_1_5b',
                                r.recorded_at = '2026-04-26'
                RETURN ley.norm_id AS source, art.article_id AS target
            """,
        },
    },
    {
        "veredicto_file": "art_158_1_ET_AG2025_veredicto.json",
        "norm_label": "Art. 158-1 ET",
        "chunk_pattern": "%::158-1",
        "vigencia_for_chunks": "derogada",  # DE → derogada
        "falkor_op": {
            "description": "Art. 158-1 ET DEROGATED_BY Ley 2277/2022 Art. 96",
            "cypher": """
                MERGE (art:ArticleNode {article_id: '158-1'})
                  ON CREATE SET art.label = 'Art. 158-1 ET — Deducción CTeI (derogado)'
                MERGE (ley:ReformNode {norm_id: 'Ley-2277-2022'})
                  ON CREATE SET ley.label = 'Ley 2277 de 2022 (Reforma tributaria)',
                                ley.tipo = 'ley',
                                ley.fecha_promulgacion = '2022-12-13'
                MERGE (ley)-[r:DEROGATES]->(art)
                  ON CREATE SET r.articulo_derogador = 'Art. 96',
                                r.fecha = '2022-12-13',
                                r.fecha_efectos = '2023-01-01',
                                r.alcance = 'total',
                                r.activity = 'activity_1_5b',
                                r.recorded_at = '2026-04-26'
                RETURN ley.norm_id AS source, art.article_id AS target
            """,
        },
    },
    {
        "veredicto_file": "art_290_num5_ET_AG2025_veredicto.json",
        "norm_label": "Art. 290 #5 ET",
        # State V — no chunk vigencia change needed; just structured property.
        "chunk_pattern": None,
        "vigencia_for_chunks": None,
        "falkor_op": {
            "description": "Art. 290 ET regimen_transicion property (no edge — V state)",
            # No edge: state is V. Just annotate the article with the regimen
            # transicion fact + creating-law reference.
            "cypher": """
                MERGE (art:ArticleNode {article_id: '290'})
                  ON CREATE SET art.label = 'Art. 290 ET — Régimen de transición'
                SET art.regimen_transicion_origen = 'Ley 1819/2016 Art. 123',
                    art.regimen_transicion_alcance = 'pérdidas pre-2017 (numeral 5)',
                    art.constitucionalidad_confirmada_por = 'Sentencia C-087/2019',
                    art.activity_1_5b_recorded_at = '2026-04-26'
                RETURN art.article_id AS source, NULL AS target
            """,
        },
    },
]


# ---------------------------------------------------------------------------
# Load veredictos
# ---------------------------------------------------------------------------


def load_veredictos() -> list[dict[str, Any]]:
    out = []
    for entry in PERSISTENCE_PLAN:
        path = VEREDICTOS_DIR / entry["veredicto_file"]
        if not path.exists():
            print(f"[skip] missing veredicto: {path}", file=sys.stderr)
            continue
        with path.open() as fh:
            veredicto = json.load(fh)
        out.append({**entry, "veredicto": veredicto, "veredicto_path": str(path)})
    return out


# ---------------------------------------------------------------------------
# Supabase ops
# ---------------------------------------------------------------------------


def _get_supabase_client():
    """Use the project's existing strict-mode Supabase client."""
    sys.path.insert(0, str(ROOT / "src"))
    from lia_graph.supabase_client import get_supabase_client
    return get_supabase_client()


def supabase_count_matching_chunks(client, chunk_pattern: str) -> int:
    resp = (
        client.table("document_chunks")
        .select("chunk_id", count="exact")
        .like("chunk_id", chunk_pattern)
        .limit(1)
        .execute()
    )
    return getattr(resp, "count", None) or 0


def supabase_apply_chunk_vigencia(
    client, chunk_pattern: str, new_vigencia: str, basis: str
) -> dict[str, Any]:
    """UPDATE document_chunks SET vigencia=..., vigencia_basis=... WHERE chunk_id LIKE pattern."""
    resp = (
        client.table("document_chunks")
        .update({
            "vigencia": new_vigencia,
            "vigencia_basis": basis,
        })
        .like("chunk_id", chunk_pattern)
        .execute()
    )
    return {
        "rows_affected": len(getattr(resp, "data", []) or []),
        "vigencia_set_to": new_vigencia,
        "basis_set_to": basis,
    }


# ---------------------------------------------------------------------------
# Falkor ops
# ---------------------------------------------------------------------------


def _get_falkor_client():
    """Construct the project's GraphClient pointing at staging Falkor.

    Uses live execution via _execute_live_statement under the hood
    (no in-memory executor) — the GraphClient.execute() method handles that
    when self._executor is None and config.is_configured returns True.
    """
    sys.path.insert(0, str(ROOT / "src"))
    from lia_graph.graph.client import GraphClient
    return GraphClient.from_env(environ=os.environ)


def falkor_run_cypher(client, description: str, cypher: str) -> dict[str, Any]:
    """Execute a raw Cypher MERGE via GraphClient.execute()."""
    from lia_graph.graph.client import GraphWriteStatement
    statement = GraphWriteStatement(
        description=description,
        query=cypher.strip(),
        parameters={},
    )
    result = client.execute(statement, strict=False)
    if result.skipped:
        return {
            "success": False,
            "error": f"skipped — {dict(result.diagnostics)}",
        }
    if not result.ok:
        return {
            "success": False,
            "error": result.error or "unknown",
        }
    return {
        "success": True,
        "rows": len(result.rows or ()),
        "stats": dict(result.stats),
    }


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


def audit_log(entry: dict[str, Any]) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    with AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run(*, apply: bool, supabase_only: bool, falkor_only: bool) -> int:
    plan = load_veredictos()
    if not plan:
        print("FATAL: no veredictos loaded; exiting", file=sys.stderr)
        return 2

    print(f"=== Activity 1.5b — Persist veredictos to staging ===")
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")
    print(f"Targets: {'Supabase only' if supabase_only else 'Falkor only' if falkor_only else 'Supabase + Falkor'}")
    print(f"Veredictos to persist: {len(plan)}")
    print()

    sb_client = None
    if not falkor_only:
        try:
            sb_client = _get_supabase_client()
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: cannot connect to Supabase ({exc!s}); skipping Supabase ops", file=sys.stderr)
            sb_client = None

    falkor_client = None
    if not supabase_only:
        try:
            falkor_client = _get_falkor_client()
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: cannot connect to Falkor ({exc!s}); skipping Falkor ops", file=sys.stderr)
            falkor_client = None

    summary = {"supabase_writes": 0, "falkor_writes": 0, "errors": 0}

    for item in plan:
        norm = item["norm_label"]
        print(f"--- {norm} ---")

        # Supabase chunk-level vigencia
        if sb_client and item.get("chunk_pattern"):
            pattern = item["chunk_pattern"]
            target = item["vigencia_for_chunks"]
            basis = item["veredicto"]["veredicto"].get("state", "unknown") + "_activity_1_5b"
            try:
                count = supabase_count_matching_chunks(sb_client, pattern)
            except Exception as exc:  # noqa: BLE001
                print(f"  [supabase] count error: {exc!s}", file=sys.stderr)
                count = -1
            print(f"  [supabase] chunks matching {pattern!r}: {count}")
            print(f"  [supabase] proposed: SET vigencia={target!r}, vigencia_basis={basis!r}")
            if apply and count > 0 and target:
                result = supabase_apply_chunk_vigencia(sb_client, pattern, target, basis)
                print(f"  [supabase] APPLIED: {result}")
                audit_log({
                    "activity": "1.5b",
                    "target": "supabase",
                    "norm": norm,
                    "chunk_pattern": pattern,
                    "result": result,
                })
                summary["supabase_writes"] += result.get("rows_affected", 0)
            elif apply and count == 0:
                print(f"  [supabase] no matching chunks — skipping")
            elif not apply:
                print(f"  [supabase] DRY-RUN — would update {count} chunks")
        elif item.get("chunk_pattern") is None:
            print(f"  [supabase] no chunk-level update (per Activity 1.5 discrimination)")

        # Falkor structured edge
        if falkor_client and item.get("falkor_op"):
            fop = item["falkor_op"]
            print(f"  [falkor] proposed: {fop['description']}")
            if apply:
                result = falkor_run_cypher(falkor_client, fop["description"], fop["cypher"])
                if result["success"]:
                    print(f"  [falkor] APPLIED: rows={result['rows']} stats={result['stats']}")
                    summary["falkor_writes"] += 1
                else:
                    print(f"  [falkor] ERROR: {result['error']}")
                    summary["errors"] += 1
                audit_log({
                    "activity": "1.5b",
                    "target": "falkor",
                    "norm": norm,
                    "operation": fop["description"],
                    "result": result,
                })
            else:
                print(f"  [falkor] DRY-RUN — would execute MERGE")
                # Show first few lines of the cypher
                cypher_preview = "\n    ".join(
                    line.strip() for line in fop["cypher"].strip().splitlines()[:5]
                )
                print(f"    {cypher_preview}")
                print(f"    ...")
        print()

    print(f"=== Summary ===")
    print(json.dumps(summary, indent=2))
    if not apply:
        print()
        print("This was a DRY-RUN. Re-run with --apply to actually write to staging.")
        print(f"Audit log: {AUDIT_LOG}")
    return 0 if summary["errors"] == 0 else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true",
                   help="Actually write to staging (default: dry-run)")
    p.add_argument("--supabase-only", action="store_true")
    p.add_argument("--falkor-only", action="store_true")
    args = p.parse_args(argv)
    return run(
        apply=args.apply,
        supabase_only=args.supabase_only,
        falkor_only=args.falkor_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
