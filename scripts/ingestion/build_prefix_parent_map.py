#!/usr/bin/env python
"""Build / audit the filename-prefix -> parent_topic_key lookup table.

Walks ``knowledge_base/`` (or any ``--corpus-root``), extracts the
``^[A-Za-z]{1,5}-`` prefix from each markdown file, and counts how often
each prefix occurs. Compares that evidence against
``config/prefix_parent_topic_map.json`` and prints divergence:

- prefixes in the JSON that no longer have corpus evidence ("orphans")
- prefixes with >= ``--min-count`` corpus occurrences that are NOT in the
  JSON ("uncovered")

Rationale documented in
``scripts/curator-decisions-abril-2026/strategy-memo.md`` §2.2 — the JSON
itself is the contract; this script is a bootstrapping + drift-detection
helper, not the authoritative source.

Usage::

    python scripts/ingestion/build_prefix_parent_map.py --dry-run
    python scripts/ingestion/build_prefix_parent_map.py --dry-run --min-count 3
    python scripts/ingestion/build_prefix_parent_map.py --write --output path.json

Exit codes:
    0   success
    2   argparse error (handled by argparse itself)
    3   no markdown files under --corpus-root
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
for _candidate in (_SRC_DIR, _REPO_ROOT):
    _candidate_str = str(_candidate)
    if _candidate.is_dir() and _candidate_str not in sys.path:
        sys.path.insert(0, _candidate_str)

from lia_graph.env_loader import load_dotenv_if_present  # noqa: E402

_DEFAULT_CORPUS_ROOT = _REPO_ROOT / "knowledge_base"
_DEFAULT_OUTPUT = _REPO_ROOT / "config" / "prefix_parent_topic_map.json"
_PREFIX_RE = re.compile(r"^([A-Za-z]{1,5})-")

# Common prefixes that are NOT topic-routing prefixes (they precede law
# numbers, section numbers, generic markers, etc.). Excluded from the
# "uncovered" report so it does not drown out real signal.
_NOISE_PREFIXES = frozenset(
    {
        "ley",  # Ley-XXXX
        "l",    # L-XX-* LOGGRO markers
        "n",    # N-XX-* NORMATIVA markers
        "t",    # T-XX-* TOPIC markers (Corpus de Contabilidad)
        "a",    # rare single-letter artifacts
        "d",    # rare single-letter artifacts
    }
)


def _extract_prefix(filename: str) -> str | None:
    match = _PREFIX_RE.match(filename)
    if not match:
        return None
    return match.group(1).lower() + "-"


def _scan_prefixes(corpus_root: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for path in corpus_root.rglob("*.md"):
        prefix = _extract_prefix(path.name)
        if prefix is None:
            continue
        counts[prefix] += 1
    return counts


def _load_existing(json_path: Path) -> dict[str, Any]:
    if not json_path.exists():
        return {"version": "bootstrap", "mappings": {}}
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"version": "bootstrap", "mappings": {}}
    payload.setdefault("mappings", {})
    return payload


def _normalize_mapping_keys(mappings: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in mappings.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        normalized[key.strip().lower()] = value.strip().lower()
    return normalized


def _format_table(rows: list[tuple[str, Any]]) -> str:
    if not rows:
        return "(none)"
    width = max(len(str(left)) for left, _ in rows)
    return "\n".join(f"  {str(left):<{width}}  {right}" for left, right in rows)


def _emit_report(
    *,
    counts: Counter[str],
    existing_mappings: dict[str, str],
    min_count: int,
) -> dict[str, list[tuple[str, Any]]]:
    covered: list[tuple[str, Any]] = []
    orphans: list[tuple[str, Any]] = []
    uncovered: list[tuple[str, Any]] = []

    for prefix, parent_topic in sorted(existing_mappings.items()):
        occurrences = counts.get(prefix, 0)
        if occurrences > 0:
            covered.append((prefix, f"{parent_topic}  (evidence: {occurrences})"))
        else:
            orphans.append((prefix, f"{parent_topic}  (no corpus evidence)"))

    for prefix, occurrences in counts.most_common():
        if prefix in existing_mappings:
            continue
        bare = prefix.rstrip("-")
        if bare in _NOISE_PREFIXES:
            continue
        if occurrences < min_count:
            continue
        uncovered.append((prefix, f"count={occurrences}"))

    return {
        "covered": covered,
        "orphans": orphans,
        "uncovered": uncovered,
    }


def _build_proposal(
    *,
    existing_payload: dict[str, Any],
    counts: Counter[str],
) -> dict[str, Any]:
    """Return a JSON-ready dict echoing the existing payload plus a
    ``_observed_prefix_counts`` block for auditability. Does NOT auto-add
    uncovered prefixes — curator still owns the mapping decision.
    """
    proposal = dict(existing_payload)
    proposal.setdefault("version", "bootstrap")
    proposal.setdefault("mappings", {})
    proposal["_observed_prefix_counts"] = dict(sorted(counts.items()))
    return proposal


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan the corpus for filename prefixes and audit them "
        "against config/prefix_parent_topic_map.json."
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=_DEFAULT_CORPUS_ROOT,
        help=f"Directory to walk recursively (default: {_DEFAULT_CORPUS_ROOT}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help=f"JSON file to compare against / write to (default: {_DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=3,
        help="Minimum corpus count for a prefix to appear in the "
        "'uncovered' report (default: 3).",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the audit report without writing anything (default).",
    )
    group.add_argument(
        "--write",
        action="store_true",
        help="Write an audit-augmented JSON back to --output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv_if_present()
    args = _parse_args(argv)

    corpus_root: Path = args.corpus_root
    if not corpus_root.exists() or not corpus_root.is_dir():
        print(f"[error] corpus root not found: {corpus_root}", file=sys.stderr)
        return 3

    counts = _scan_prefixes(corpus_root)
    if not counts:
        print(f"[error] no markdown files under {corpus_root}", file=sys.stderr)
        return 3

    existing_payload = _load_existing(args.output)
    existing_mappings = _normalize_mapping_keys(existing_payload.get("mappings", {}))

    report = _emit_report(
        counts=counts,
        existing_mappings=existing_mappings,
        min_count=args.min_count,
    )

    print(f"corpus_root: {corpus_root}")
    print(f"json:        {args.output}")
    print(f"unique prefixes scanned: {len(counts)}")
    print(f"mappings in json:        {len(existing_mappings)}")
    print()
    print("[covered]  (prefix in json AND in corpus)")
    print(_format_table(report["covered"]))
    print()
    print("[orphans]  (prefix in json but 0 corpus hits — stale?)")
    print(_format_table(report["orphans"]))
    print()
    print(f"[uncovered] (prefix in corpus with count >= {args.min_count} but NOT in json)")
    print(_format_table(report["uncovered"]))

    if args.write:
        proposal = _build_proposal(
            existing_payload=existing_payload,
            counts=counts,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(proposal, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print()
        print(f"[write] wrote audit-augmented JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
