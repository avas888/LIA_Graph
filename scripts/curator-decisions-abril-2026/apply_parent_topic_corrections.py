#!/usr/bin/env python
"""Apply parent_topic_corrections.sql to a Supabase target via supabase-py.

The SQL file uses column name ``parent_topic_key`` (semantic). The
Supabase ``documents`` table calls this column ``topic``. This script
parses the SQL, remaps the column, and executes each UPDATE via the
REST API (one-at-a-time for safety; idempotent).

Usage:
    python scripts/curator-decisions-abril-2026/apply_parent_topic_corrections.py --target wip [--dry-run]
"""
from __future__ import annotations

import argparse
import re
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


_UPDATE_RE = re.compile(
    r"UPDATE documents SET parent_topic_key = '([^']+)' WHERE relative_path = '([^']+)';"
)


def main(argv: list[str] | None = None) -> int:
    load_dotenv_if_present()
    p = argparse.ArgumentParser()
    p.add_argument("--target", choices=["wip", "production"], default="wip")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--allow-non-local-env",
        action="store_true",
        help="Required when --target production.",
    )
    args = p.parse_args(argv)

    if args.target == "production" and not args.allow_non_local_env:
        sys.stderr.write(
            "parent_topic_corrections: cloud target requires --allow-non-local-env\n"
        )
        return 4

    if args.target == "wip":
        from lia_graph.env_posture import EnvPostureError, assert_local_posture

        try:
            assert_local_posture(require_supabase=True, require_falkor=False)
        except EnvPostureError as exc:
            sys.stderr.write(f"parent_topic_corrections: {exc}\n")
            return 4

    sql_path = _REPO_ROOT / "scripts" / "curator-decisions-abril-2026" / "parent_topic_corrections.sql"
    text = sql_path.read_text(encoding="utf-8")
    corrections: list[tuple[str, str]] = _UPDATE_RE.findall(text)
    print(f"found {len(corrections)} UPDATE statements")

    if not corrections:
        return 0

    from lia_graph.supabase_client import create_supabase_client_for_target

    client = create_supabase_client_for_target(args.target)

    emit_event(
        "parent_topic_corrections.start",
        {"target": args.target, "count": len(corrections), "dry_run": args.dry_run},
    )

    updated = 0
    missing = 0
    for new_topic, rel_path in corrections:
        # Preview current state
        pre = (
            client.table("documents")
            .select("doc_id, topic")
            .eq("relative_path", rel_path)
            .execute()
        )
        rows = list(getattr(pre, "data", None) or [])
        if not rows:
            missing += 1
            emit_event(
                "parent_topic_corrections.skip_missing",
                {"relative_path": rel_path, "reason": "no_document_row"},
            )
            continue
        for row in rows:
            if row.get("topic") == new_topic:
                continue  # already correct
            if not args.dry_run:
                client.table("documents").update({"topic": new_topic}).eq(
                    "doc_id", row["doc_id"]
                ).execute()
            updated += 1
            emit_event(
                "parent_topic_corrections.applied",
                {
                    "doc_id": row["doc_id"],
                    "relative_path": rel_path,
                    "old_topic": row.get("topic"),
                    "new_topic": new_topic,
                    "dry_run": args.dry_run,
                },
            )

    print(
        f"updated={updated}  missing={missing}  dry_run={args.dry_run}  target={args.target}"
    )
    emit_event(
        "parent_topic_corrections.done",
        {"target": args.target, "updated": updated, "missing": missing, "dry_run": args.dry_run},
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
