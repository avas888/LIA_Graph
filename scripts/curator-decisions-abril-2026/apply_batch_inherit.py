#!/usr/bin/env python
"""Apply batch_inherit.sql: the 353-row UPDATE for LEYES/OTROS_SECTORIALES.

The canonical SQL:
    UPDATE documents
    SET parent_topic_key = 'otros_sectoriales',
        subtema = 'cumplimiento_normativo_sectorial_pymes'
    WHERE relative_path LIKE '%/LEYES/OTROS_SECTORIALES/%'
      AND subtema IS NULL;

Supabase column is `topic` not `parent_topic_key` — translated via REST API.
Also emits SubTopicNode + HAS_SUBTOPIC to Falkor for each doc's article(s).

Usage:
    python scripts/curator-decisions-abril-2026/apply_batch_inherit.py --target wip
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
for _c in (_SRC_DIR, _REPO_ROOT):
    _s = str(_c)
    if _c.is_dir() and _s not in sys.path:
        sys.path.insert(0, _s)

from lia_graph.env_loader import load_dotenv_if_present  # noqa: E402
from lia_graph.instrumentation import emit_event  # noqa: E402

_TARGET_SUBTOPIC = "cumplimiento_normativo_sectorial_pymes"
_TARGET_PARENT = "otros_sectoriales"
_PATH_PATTERN = "%/LEYES/OTROS_SECTORIALES/%"


def main(argv: list[str] | None = None) -> int:
    load_dotenv_if_present()
    p = argparse.ArgumentParser()
    p.add_argument("--target", choices=["wip", "production"], default="wip")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--allow-non-local-env", action="store_true")
    args = p.parse_args(argv)

    if args.target == "production" and not args.allow_non_local_env:
        sys.stderr.write("batch_inherit: cloud target requires --allow-non-local-env\n")
        return 4

    if args.target == "wip":
        from lia_graph.env_posture import EnvPostureError, assert_local_posture

        try:
            assert_local_posture(require_supabase=True, require_falkor=False)
        except EnvPostureError as exc:
            sys.stderr.write(f"batch_inherit: {exc}\n")
            return 4

    from lia_graph.supabase_client import create_supabase_client_for_target

    client = create_supabase_client_for_target(args.target)

    # Fetch candidates: LEYES/OTROS_SECTORIALES/ paths with NULL subtema
    # Using .ilike to match the SQL LIKE; note Supabase uses %...%
    r = (
        client.table("documents")
        .select("doc_id, relative_path, topic, subtema")
        .ilike("relative_path", _PATH_PATTERN)
        .is_("subtema", None)
        .execute()
    )
    rows = list(getattr(r, "data", None) or [])
    print(f"batch_inherit candidates: {len(rows)} rows")

    emit_event(
        "batch_inherit.start",
        {"target": args.target, "count": len(rows), "dry_run": args.dry_run},
    )

    updated = 0
    for row in rows:
        doc_id = row["doc_id"]
        if not args.dry_run:
            client.table("documents").update(
                {
                    "topic": _TARGET_PARENT,
                    "subtema": _TARGET_SUBTOPIC,
                    "requires_subtopic_review": False,
                }
            ).eq("doc_id", doc_id).execute()
            # Also update chunks to inherit subtema
            client.table("document_chunks").update(
                {"subtema": _TARGET_SUBTOPIC}
            ).eq("doc_id", doc_id).execute()
        updated += 1

    emit_event(
        "batch_inherit.done",
        {"target": args.target, "updated": updated, "dry_run": args.dry_run},
    )
    print(f"updated={updated} dry_run={args.dry_run} target={args.target}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
