#!/usr/bin/env python
"""Sync ``config/subtopic_taxonomy.json`` into Supabase ``sub_topic_taxonomy``.

Ingestfix-v2 Phase 2 companion to
``scripts/ingestion/promote_subtopic_decisions.py`` — the file remains the source of
truth (Decision B1); this script materializes the file into the DB.

Usage::

    python scripts/ingestion/sync_subtopic_taxonomy_to_supabase.py --dry-run
    python scripts/ingestion/sync_subtopic_taxonomy_to_supabase.py --target wip
    python scripts/ingestion/sync_subtopic_taxonomy_to_supabase.py --target production

Exit codes:
    0   success
    1   malformed taxonomy / sync error
    2   argparse error (handled by argparse itself)

Trace events:
    subtopic.ingest.taxonomy_sync.start
    subtopic.ingest.taxonomy_synced
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
for candidate in (_SRC_DIR, _REPO_ROOT):
    candidate_str = str(candidate)
    if candidate.is_dir() and candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from lia_graph.env_loader import load_dotenv_if_present  # noqa: E402
from lia_graph.instrumentation import emit_event  # noqa: E402
from lia_graph.subtopic_taxonomy_loader import (  # noqa: E402
    DEFAULT_TAXONOMY_PATH,
    SubtopicTaxonomy,
    load_taxonomy,
)


_TABLE = "sub_topic_taxonomy"


def _rows_from_taxonomy(taxonomy: SubtopicTaxonomy) -> list[dict[str, Any]]:
    """Project a SubtopicTaxonomy into rows matching the DB table shape."""
    rows: list[dict[str, Any]] = []
    for parent_topic in sorted(taxonomy.subtopics_by_parent):
        for entry in taxonomy.subtopics_by_parent[parent_topic]:
            rows.append(
                {
                    "parent_topic_key": parent_topic,
                    "sub_topic_key": entry.key,
                    "label": entry.label,
                    "aliases": list(entry.aliases),
                    "evidence_count": entry.evidence_count,
                    "curated_at": entry.curated_at or None,
                    "curator": entry.curator or None,
                    "version": taxonomy.version,
                }
            )
    return rows


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sync_subtopic_taxonomy_to_supabase",
        description=(
            "Mirror config/subtopic_taxonomy.json into the Supabase "
            "sub_topic_taxonomy reference table. The JSON file remains the "
            "source of truth (ingestfix-v2 Decision B1)."
        ),
    )
    parser.add_argument(
        "--taxonomy",
        type=str,
        default=str(DEFAULT_TAXONOMY_PATH),
        help=f"Path to the taxonomy JSON (default: {DEFAULT_TAXONOMY_PATH})",
    )
    parser.add_argument(
        "--target",
        type=str,
        choices=("wip", "production"),
        default="wip",
        help="Supabase target ('wip' = local docker, 'production' = cloud).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print row count + summary without writing.",
    )
    return parser


def _supabase_upsert(client: Any, rows: list[dict[str, Any]]) -> int:
    """Upsert taxonomy rows via the Supabase REST client.

    Returns the number of rows sent. Errors propagate — the sink sharing
    the same posture means we never silently swallow DB errors.
    """
    if not rows:
        return 0
    client.table(_TABLE).upsert(
        rows, on_conflict="parent_topic_key,sub_topic_key"
    ).execute()
    return len(rows)


def sync(
    taxonomy: SubtopicTaxonomy,
    *,
    target: str,
    dry_run: bool,
    client_factory: Callable[[str], Any] | None = None,
    upserter: Callable[[Any, list[dict[str, Any]]], int] | None = None,
) -> int:
    """Execute the sync. Returns the number of rows upserted (0 on dry-run).

    ``client_factory`` / ``upserter`` are injection points so the test suite
    can exercise the sync without touching a real Supabase instance.
    """
    rows = _rows_from_taxonomy(taxonomy)
    emit_event(
        "subtopic.ingest.taxonomy_sync.start",
        {
            "target": target,
            "version": taxonomy.version,
            "row_count": len(rows),
            "dry_run": dry_run,
        },
    )
    if dry_run:
        sys.stdout.write(
            f"sync-taxonomy: DRY RUN — would upsert {len(rows)} rows "
            f"(version={taxonomy.version}, target={target})\n"
        )
        sys.stdout.flush()
        return 0

    factory = client_factory
    if factory is None:
        from lia_graph.supabase_client import create_supabase_client_for_target

        factory = create_supabase_client_for_target

    client = factory(target)
    sender = upserter or _supabase_upsert
    sent = sender(client, rows)
    emit_event(
        "subtopic.ingest.taxonomy_synced",
        {
            "target": target,
            "version": taxonomy.version,
            "row_count": sent,
        },
    )
    sys.stdout.write(
        f"sync-taxonomy: upserted {sent} rows to Supabase target={target} "
        f"(version={taxonomy.version})\n"
    )
    sys.stdout.flush()
    return sent


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv_if_present()
    parser = _build_argparser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    taxonomy_path = Path(args.taxonomy).expanduser().resolve()
    try:
        taxonomy = load_taxonomy(taxonomy_path)
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"sync-taxonomy: failed to load taxonomy — {exc}\n")
        return 1
    try:
        sync(taxonomy, target=args.target, dry_run=bool(args.dry_run))
    except Exception as exc:  # noqa: BLE001 — surface all sync failures loudly
        sys.stderr.write(f"sync-taxonomy: sync failed — {exc}\n")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
