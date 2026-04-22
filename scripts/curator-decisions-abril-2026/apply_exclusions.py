#!/usr/bin/env python
"""Apply exclusions.txt: move files out of knowledge_base/ + delete from Supabase.

Reads:
  scripts/curator-decisions-abril-2026/exclusions.txt
    # Lines starting with '#' are comments/section headers
    # Other non-empty lines are corpus-root-relative paths to exclude

Actions:
  1. Move each file out of knowledge_base/ into knowledge_base_archive/ (preserving
     relative path). The audit gate will now also exclude them via C5's
     EXCLUDED_FILENAMES / EXCLUDED_PATH_PREFIXES filters, so this step is a
     hygiene pass — future ingests won't see them even if they move back.
  2. DELETE the matching rows from documents + document_chunks in the target
     Supabase (cascades through normative_edges via FK).

Usage:
    python scripts/curator-decisions-abril-2026/apply_exclusions.py --target wip
    python scripts/curator-decisions-abril-2026/apply_exclusions.py --target wip --dry-run
    python scripts/curator-decisions-abril-2026/apply_exclusions.py --target wip --no-move  # DB-only
"""
from __future__ import annotations

import argparse
import shutil
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

_EXCLUSIONS_PATH = _REPO_ROOT / "scripts" / "curator-decisions-abril-2026" / "exclusions.txt"
_CORPUS_ROOT = _REPO_ROOT / "knowledge_base"
_ARCHIVE_ROOT = _REPO_ROOT / "knowledge_base_archive"


def _parse_exclusions() -> list[str]:
    lines = _EXCLUSIONS_PATH.read_text(encoding="utf-8").splitlines()
    paths: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        paths.append(stripped)
    return paths


def main(argv: list[str] | None = None) -> int:
    load_dotenv_if_present()
    p = argparse.ArgumentParser()
    p.add_argument("--target", choices=["wip", "production"], default="wip")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--no-move", action="store_true",
        help="Skip filesystem moves (DB-only); useful when cloud target and local FS already archived.",
    )
    p.add_argument(
        "--allow-non-local-env", action="store_true",
        help="Required for --target production.",
    )
    args = p.parse_args(argv)

    if args.target == "production" and not args.allow_non_local_env:
        sys.stderr.write("apply_exclusions: cloud target requires --allow-non-local-env\n")
        return 4

    if args.target == "wip":
        from lia_graph.env_posture import EnvPostureError, assert_local_posture

        try:
            assert_local_posture(require_supabase=True, require_falkor=False)
        except EnvPostureError as exc:
            sys.stderr.write(f"apply_exclusions: {exc}\n")
            return 4

    paths = _parse_exclusions()
    print(f"exclusions: {len(paths)} paths")

    from lia_graph.supabase_client import create_supabase_client_for_target
    client = create_supabase_client_for_target(args.target)

    emit_event(
        "exclusions.apply.start",
        {"target": args.target, "count": len(paths), "dry_run": args.dry_run},
    )

    moved = 0
    missing_fs = 0
    db_deleted = 0
    db_missing = 0
    for rel in paths:
        src = _CORPUS_ROOT / rel
        dst = _ARCHIVE_ROOT / rel
        # Step 1: filesystem move
        if args.no_move:
            pass
        elif src.exists():
            if not args.dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
            moved += 1
        else:
            missing_fs += 1

        # Step 2: DB delete
        # First check whether the row exists in this target so we can emit
        # accurate counts in dry-run.
        pre = (
            client.table("documents")
            .select("doc_id")
            .eq("relative_path", rel)
            .execute()
        )
        rows = list(getattr(pre, "data", None) or [])
        if not rows:
            db_missing += 1
            continue
        for row in rows:
            doc_id = row["doc_id"]
            if not args.dry_run:
                # Chunks first (no cascade guaranteed in all envs)
                client.table("document_chunks").delete().eq("doc_id", doc_id).execute()
                client.table("documents").delete().eq("doc_id", doc_id).execute()
            db_deleted += 1
            emit_event(
                "exclusions.apply.doc",
                {"relative_path": rel, "doc_id": doc_id, "target": args.target, "dry_run": args.dry_run},
            )

    print(
        f"fs_moved={moved}  fs_missing={missing_fs}  db_deleted={db_deleted}  db_missing={db_missing}"
    )
    emit_event(
        "exclusions.apply.done",
        {"target": args.target, "moved": moved, "db_deleted": db_deleted, "dry_run": args.dry_run},
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
