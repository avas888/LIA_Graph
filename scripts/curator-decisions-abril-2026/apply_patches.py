#!/usr/bin/env python
"""Merge curator-decisions-abril-2026 patches into config/subtopic_taxonomy.json.

Reads:
  - config/subtopic_taxonomy.json (current v1)
  - scripts/curator-decisions-abril-2026/alias_additions.json (127 alias patches over 15 subtopics)
  - scripts/curator-decisions-abril-2026/new_subtopics.json (20 new subtopic entries)

Writes:
  - config/subtopic_taxonomy.json (bumped to v2026-04-21-v2)

Idempotent: aliases are deduped; an entry already at v2 yields a clean diff.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TAXONOMY_PATH = _REPO_ROOT / "config" / "subtopic_taxonomy.json"
_PATCH_DIR = _REPO_ROOT / "scripts" / "curator-decisions-abril-2026"
_ALIAS_ADDITIONS = _PATCH_DIR / "alias_additions.json"
_NEW_SUBTOPICS = _PATCH_DIR / "new_subtopics.json"

_NEW_VERSION = "2026-04-21-v2"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _split_full_key(full_key: str) -> tuple[str, str]:
    if "." not in full_key:
        raise ValueError(f"full_key missing '.': {full_key!r}")
    parent, sub = full_key.split(".", 1)
    return parent, sub


def _apply_aliases(taxonomy: dict[str, Any], patches_doc: dict[str, Any]) -> tuple[int, int, list[str]]:
    patches = patches_doc.get("patches", [])
    patched = 0
    aliases_added = 0
    skipped: list[str] = []
    for patch in patches:
        parent, sub_key = _split_full_key(patch["subtopic_full_key"])
        to_add = list(patch.get("aliases_to_add", []))
        bucket = taxonomy["subtopics"].get(parent, [])
        matched = False
        for entry in bucket:
            if entry.get("key") != sub_key:
                continue
            matched = True
            existing = list(entry.get("aliases", []))
            before = len(existing)
            seen = set(existing)
            for alias in to_add:
                if alias not in seen:
                    existing.append(alias)
                    seen.add(alias)
            entry["aliases"] = existing
            aliases_added += len(existing) - before
            patched += 1
            break
        if not matched:
            # Curator's patches include some "hypothetical" targets flagged in
            # classify_flagged.py. Warn + skip rather than abort — downstream
            # backfill will simply leave those docs flagged_for_review.
            skipped.append(f"{parent}.{sub_key}")
    return patched, aliases_added, skipped


def _apply_new_subtopics(taxonomy: dict[str, Any], new_doc: dict[str, Any]) -> int:
    entries = new_doc.get("new_subtopics", [])
    added = 0
    for proposed in entries:
        parent = proposed["parent_topic_key"]
        sub_key = proposed["subtopic_key"]
        bucket = taxonomy["subtopics"].setdefault(parent, [])
        if any(e.get("key") == sub_key for e in bucket):
            continue
        bucket.append({
            "key": sub_key,
            "label": proposed["label"],
            "aliases": list(proposed.get("aliases", [])),
            "evidence_count": int(proposed.get("evidence_count_seed", 0)),
            "curated_at": "2026-04-21T16:48:00Z",
            "curator": "curator-decisions-abril-2026",
        })
        added += 1
    return added


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="apply_patches")
    p.add_argument("--dry-run", action="store_true",
                   help="Don't write the new taxonomy; print summary.")
    p.add_argument("--output", default=str(_TAXONOMY_PATH),
                   help="Where to write the merged taxonomy (default overwrites in place).")
    args = p.parse_args(argv)

    taxonomy = _load_json(_TAXONOMY_PATH)
    base_version = taxonomy.get("version")
    patched_taxonomy = copy.deepcopy(taxonomy)

    new_doc = _load_json(_NEW_SUBTOPICS)
    added = _apply_new_subtopics(patched_taxonomy, new_doc)

    alias_doc = _load_json(_ALIAS_ADDITIONS)
    patched, aliases_added, skipped = _apply_aliases(patched_taxonomy, alias_doc)

    patched_taxonomy["version"] = _NEW_VERSION
    patched_taxonomy["generated_from"] = "merge: v1 + curator-decisions-abril-2026"
    patched_taxonomy["generated_at"] = "2026-04-21T21:58:00Z"

    # Count total subtopics before/after
    before_total = sum(len(v) for v in taxonomy["subtopics"].values())
    after_total = sum(len(v) for v in patched_taxonomy["subtopics"].values())

    print(f"base version:      {base_version}")
    print(f"output version:    {_NEW_VERSION}")
    print(f"subtopics before:  {before_total}")
    print(f"subtopics after:   {after_total}  (+{after_total - before_total})")
    print(f"new subtopics:     {added}")
    print(f"aliases patched:   {aliases_added} new aliases across {patched} entries")
    if skipped:
        print(f"skipped aliases:   {len(skipped)} patches referenced missing entries:")
        for key in skipped:
            print(f"                   - {key}")
    print(f"parents before:    {len(taxonomy['subtopics'])}")
    print(f"parents after:     {len(patched_taxonomy['subtopics'])}")

    if args.dry_run:
        print("(dry-run — no file written)")
        return 0

    out_path = Path(args.output)
    out_path.write_text(json.dumps(patched_taxonomy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {out_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
