"""fixplan_v3 sub-fix 1B-γ — sink for skill-emitted vigencia veredictos.

Reads JSON files from `evals/vigencia_extraction_v1/<norm_id>.json` (the
1B-β output) and writes them to:
  * Supabase: `norms` + `norm_vigencia_history` via `NormHistoryWriter`.
  * Falkor: `(:Norm)` + structured edges via `scripts/sync_vigencia_to_falkor.py`.

Idempotent — re-running with the same `--run-id` skips rows already inserted.

Usage:
  PYTHONPATH=src:. uv run python scripts/ingest_vigencia_veredictos.py \\
      --target staging \\
      --run-id 1Bbeta-batch-2026-05-15 \\
      --extracted-by ingest@v1 \\
      [--input-dir evals/vigencia_extraction_v1] \\
      [--audit-log evals/vigencia_extraction_v1/audit.jsonl] \\
      [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

LOGGER = logging.getLogger("ingest_vigencia_veredictos")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--target", default=os.getenv("LIA_SUPABASE_TARGET", "staging"))
    p.add_argument("--run-id", required=True, help="Idempotency tag for this batch.")
    p.add_argument(
        "--extracted-by",
        default="ingest@v1",
        help="Allowed: cron@v1 | ingest@v1 | manual_sme:<email> | v2_to_v3_upgrade",
    )
    p.add_argument(
        "--input-dir",
        default="evals/vigencia_extraction_v1",
        help="Directory containing per-norm veredicto JSON files.",
    )
    p.add_argument(
        "--audit-log",
        default="evals/vigencia_extraction_v1/audit.jsonl",
        help="Append per-row outcome here.",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    from lia_graph.persistence.norm_history_writer import NormHistoryWriter
    from lia_graph.vigencia import Vigencia

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        LOGGER.error("Input dir not found: %s", input_dir)
        return 2

    if args.dry_run:
        client = _DryRunClient()
    else:
        from lia_graph.supabase_client import create_supabase_client_for_target
        client = create_supabase_client_for_target(args.target)

    writer = NormHistoryWriter(client)

    audit_path = Path(args.audit_log)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    inserted = 0
    skipped = 0
    refused = 0
    errors = 0
    for path in sorted(input_dir.glob("*.json")):
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except Exception as err:
            LOGGER.warning("Cannot parse %s: %s", path, err)
            errors += 1
            continue

        result_block = blob.get("result") or {}
        veredicto_data = result_block.get("veredicto")
        norm_id = blob.get("norm_id") or path.stem
        if not veredicto_data:
            refused += 1
            _append_audit(audit_path, {
                "ts": _now(),
                "run_id": args.run_id,
                "norm_id": norm_id,
                "outcome": "refusal",
                "reason": result_block.get("refusal_reason") or "no_veredicto",
            })
            continue
        try:
            veredicto = Vigencia.from_dict(veredicto_data)
        except Exception as err:
            LOGGER.warning("Bad veredicto for %s: %s", norm_id, err)
            errors += 1
            _append_audit(audit_path, {
                "ts": _now(),
                "run_id": args.run_id,
                "norm_id": norm_id,
                "outcome": "error",
                "reason": str(err),
            })
            continue

        try:
            prepared = writer.prepare_row(
                norm_id=norm_id,
                veredicto=veredicto,
                extracted_by=args.extracted_by,
                run_id=args.run_id,
            )
            res = writer.bulk_insert_run([prepared], run_id=args.run_id)
            inserted += res.history_rows_inserted
            skipped += res.history_rows_skipped
            _append_audit(audit_path, {
                "ts": _now(),
                "run_id": args.run_id,
                "norm_id": norm_id,
                "outcome": "inserted" if res.history_rows_inserted else "skipped",
            })
        except Exception as err:
            LOGGER.error("Write failed for %s: %s", norm_id, err)
            errors += 1
            _append_audit(audit_path, {
                "ts": _now(),
                "run_id": args.run_id,
                "norm_id": norm_id,
                "outcome": "error",
                "reason": str(err),
            })

    LOGGER.info(
        "ingest_vigencia_veredictos: inserted=%d skipped=%d refused=%d errors=%d",
        inserted,
        skipped,
        refused,
        errors,
    )
    return 0 if errors == 0 else 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_audit(path: Path, blob: dict[str, Any]) -> None:
    line = json.dumps(blob, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)


class _DryRunClient:
    """Pretty-printer that satisfies the writer's API surface."""

    def table(self, name: str) -> "_DryRunTable":
        return _DryRunTable(name)


class _DryRunTable:
    def __init__(self, name: str) -> None:
        self.name = name

    def upsert(self, payload: Any, on_conflict: str | None = None) -> "_DryRunOp":
        rows = payload if isinstance(payload, list) else [payload]
        return _DryRunOp(self.name, "upsert", rows)

    def insert(self, payload: Any) -> "_DryRunOp":
        return _DryRunOp(self.name, "insert", [payload])

    def select(self, columns: str) -> "_DryRunQuery":
        return _DryRunQuery(self.name)


class _DryRunQuery:
    def __init__(self, name: str) -> None:
        self.name = name

    def eq(self, *args: Any, **kw: Any) -> "_DryRunQuery":
        return self

    def is_(self, *args: Any, **kw: Any) -> "_DryRunQuery":
        return self

    def execute(self) -> Any:
        from types import SimpleNamespace
        return SimpleNamespace(data=[])


class _DryRunOp:
    def __init__(self, table: str, kind: str, rows: list[Any]) -> None:
        self.table = table
        self.kind = kind
        self.rows = rows

    def execute(self) -> Any:
        from types import SimpleNamespace
        for row in self.rows:
            print(f"[dry-run] {self.kind} {self.table}: {json.dumps(row, ensure_ascii=False, default=str)[:200]}")
        return SimpleNamespace(data=self.rows)


if __name__ == "__main__":
    sys.exit(main())
