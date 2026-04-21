#!/usr/bin/env python
"""Phase 6 promotion — build ``config/subtopic_taxonomy.json`` from decisions.

Consumes the append-only audit trail at
``artifacts/subtopic_decisions.jsonl`` and writes the curated taxonomy to
``config/subtopic_taxonomy.json``.

Usage:

    python scripts/promote_subtopic_decisions.py --dry-run
    python scripts/promote_subtopic_decisions.py
    python scripts/promote_subtopic_decisions.py \
        --decisions artifacts/subtopic_decisions.jsonl \
        --output config/subtopic_taxonomy.json \
        --version 2026-04-21-v1

Exit codes:
    0   — success
    1   — argparse / I/O error (handled by argparse itself)

Trace events:
    subtopic.promote.start
    subtopic.promote.merge_resolved   (emitted by builder per chain)
    subtopic.promote.done
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

# Keep the script runnable both as ``python scripts/promote_subtopic_decisions.py``
# and as ``PYTHONPATH=src:. python scripts/promote_subtopic_decisions.py``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
for candidate in (_SRC_DIR, _REPO_ROOT):
    candidate_str = str(candidate)
    if candidate.is_dir() and candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from lia_graph.instrumentation import emit_event  # noqa: E402
from lia_graph.subtopic_taxonomy_builder import (  # noqa: E402
    build_taxonomy,
    load_decisions,
)


_DEFAULT_DECISIONS_PATH = "artifacts/subtopic_decisions.jsonl"
_DEFAULT_OUTPUT_PATH = "config/subtopic_taxonomy.json"


def _default_version_slug() -> str:
    """UTC date-based version slug, e.g. ``2026-04-21-v1``."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d-v1")


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="promote_subtopic_decisions",
        description=(
            "Collapse the subtopic decisions JSONL into the curated "
            "config/subtopic_taxonomy.json file."
        ),
    )
    parser.add_argument(
        "--decisions",
        type=str,
        default=_DEFAULT_DECISIONS_PATH,
        help=(
            "Path to the append-only decisions JSONL. "
            f"Default: {_DEFAULT_DECISIONS_PATH}"
        ),
    )
    parser.add_argument(
        "--output",
        type=str,
        default=_DEFAULT_OUTPUT_PATH,
        help=(
            "Where to write the taxonomy JSON. "
            f"Default: {_DEFAULT_OUTPUT_PATH}"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Print a diff summary against the existing output file to "
            "stdout; do NOT write anything to disk."
        ),
    )
    parser.add_argument(
        "--version",
        type=str,
        default=None,
        help=(
            "Version slug recorded in the output. "
            "Default: UTC date like 2026-04-21-v1."
        ),
    )
    return parser


def _count_entries(taxonomy: dict) -> tuple[int, int]:
    """Return (parent_topic_count, subtopic_count)."""
    subtopics = taxonomy.get("subtopics") or {}
    if not isinstance(subtopics, dict):
        return 0, 0
    parent_count = len(subtopics)
    subtopic_count = 0
    for entries in subtopics.values():
        if isinstance(entries, list):
            subtopic_count += len(entries)
    return parent_count, subtopic_count


def _index_keys(taxonomy: dict) -> dict[str, set[str]]:
    """Return {parent_topic: {key, key, ...}} for diffing."""
    out: dict[str, set[str]] = {}
    subtopics = taxonomy.get("subtopics") or {}
    if not isinstance(subtopics, dict):
        return out
    for parent, entries in subtopics.items():
        if not isinstance(entries, list):
            continue
        keys: set[str] = set()
        for entry in entries:
            if isinstance(entry, dict):
                key = entry.get("key")
                if isinstance(key, str) and key:
                    keys.add(key)
        out[str(parent)] = keys
    return out


def _load_existing_output(path: Path) -> dict:
    if not path.is_file():
        return {"version": None, "subtopics": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": None, "subtopics": {}}


def _format_diff(before: dict, after: dict) -> str:
    """Produce a human-readable diff summary for --dry-run."""
    before_index = _index_keys(before)
    after_index = _index_keys(after)
    before_parents, before_subs = _count_entries(before)
    after_parents, after_subs = _count_entries(after)

    lines: list[str] = []
    lines.append("--- existing config/subtopic_taxonomy.json")
    lines.append("+++ proposed config/subtopic_taxonomy.json")
    lines.append(
        f"@@ parents: {before_parents} -> {after_parents}  "
        f"subtopics: {before_subs} -> {after_subs} @@"
    )

    all_parents = sorted(set(before_index) | set(after_index))
    for parent in all_parents:
        before_keys = before_index.get(parent, set())
        after_keys = after_index.get(parent, set())
        added = sorted(after_keys - before_keys)
        removed = sorted(before_keys - after_keys)
        if not added and not removed:
            lines.append(f"  [{parent}] unchanged ({len(after_keys)} entries)")
            continue
        lines.append(
            f"  [{parent}]  before={len(before_keys)}  after={len(after_keys)}"
        )
        for key in added:
            lines.append(f"    + {key}")
        for key in removed:
            lines.append(f"    - {key}")
    return "\n".join(lines) + "\n"


def _serialize(taxonomy: dict) -> str:
    # ``sort_keys=False`` preserves the deliberate ordering build_taxonomy
    # imposes (parent keys alphabetical; entries evidence_count desc / key asc).
    return json.dumps(taxonomy, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_argparser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    decisions_path = Path(args.decisions).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    dry_run = bool(args.dry_run)
    version = args.version or _default_version_slug()

    emit_event(
        "subtopic.promote.start",
        {
            "decisions_path": str(decisions_path),
            "dry_run": dry_run,
        },
    )

    decisions = load_decisions(decisions_path)
    taxonomy = build_taxonomy(decisions, version=version)

    parent_count, subtopic_count = _count_entries(taxonomy)

    if dry_run:
        existing = _load_existing_output(output_path)
        diff_text = _format_diff(existing, taxonomy)
        sys.stdout.write(diff_text)
        sys.stdout.flush()
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(_serialize(taxonomy), encoding="utf-8")
        sys.stdout.write(
            f"promote: wrote {output_path} "
            f"(parents={parent_count}, subtopics={subtopic_count}, "
            f"version={version})\n"
        )
        sys.stdout.flush()

    emit_event(
        "subtopic.promote.done",
        {
            "output_path": str(output_path),
            "parent_topic_count": parent_count,
            "subtopic_count": subtopic_count,
            "taxonomy_version": version,
            "dry_run": dry_run,
        },
    )

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
