"""Sub-fix 1B-β — produce the deduplicated norm_id set for the corpus.

Walks `artifacts/parsed_articles.jsonl` (or the live `document_chunks` table)
and runs the canonicalizer over every chunk's prose. Outputs a deduplicated
list of (article + sub-unit) `norm_id`s ready for the extractor batch.

Usage:
  PYTHONPATH=src:. uv run python scripts/canonicalizer/build_extraction_input_set.py \\
      --output evals/vigencia_extraction_v1/input_set.jsonl \\
      [--source artifacts]      # default: read from artifacts JSONL
      [--limit 1000]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

LOGGER = logging.getLogger("build_extraction_input_set")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--output",
        default="evals/vigencia_extraction_v1/input_set.jsonl",
    )
    p.add_argument(
        "--source",
        choices=["artifacts", "supabase"],
        default="artifacts",
    )
    p.add_argument("--target", default="staging", help="Supabase target when --source=supabase")
    p.add_argument(
        "--artifacts-path",
        default="artifacts/parsed_articles.jsonl",
    )
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    from lia_graph.canon import canonicalize_or_refuse, find_mentions

    if args.source == "artifacts":
        chunks = list(_iter_artifacts(Path(args.artifacts_path), args.limit))
    else:
        chunks = list(_iter_supabase(args.target, args.limit))

    LOGGER.info("Walking %d chunks", len(chunks))

    seen: dict[str, dict[str, Any]] = {}
    refusals: Counter = Counter()
    for chunk_id, chunk_text in chunks:
        for mention in find_mentions(chunk_text):
            norm_id, refusal = canonicalize_or_refuse(mention.text)
            if norm_id is None:
                if refusal is not None:
                    refusals[refusal.reason] += 1
                continue
            row = seen.get(norm_id)
            if row is None:
                seen[norm_id] = {
                    "norm_id": norm_id,
                    "first_seen_in_chunk": chunk_id,
                    "occurrences": 1,
                }
            else:
                row["occurrences"] += 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for row in sorted(seen.values(), key=lambda r: r["norm_id"]):
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    LOGGER.info(
        "Wrote %d unique norm_ids to %s; %d refusals (top: %s)",
        len(seen),
        out_path,
        sum(refusals.values()),
        refusals.most_common(3),
    )
    return 0


def _iter_artifacts(path: Path, limit: int | None) -> Iterable[tuple[str, str]]:
    if not path.is_file():
        LOGGER.warning("Artifacts file not found: %s", path)
        return
    count = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                blob = json.loads(line)
            except json.JSONDecodeError:
                continue
            chunk_id = str(
                blob.get("article_id")
                or blob.get("chunk_id")
                or blob.get("article_key")
                or count
            )
            text = str(
                blob.get("text")
                or blob.get("chunk_text")
                or blob.get("body")
                or ""
            )
            if text:
                yield chunk_id, text
                count += 1
                if limit is not None and count >= limit:
                    break


def _iter_supabase(target: str, limit: int | None) -> Iterable[tuple[str, str]]:
    from lia_graph.supabase_client import create_supabase_client_for_target
    sb = create_supabase_client_for_target(target)
    offset = 0
    page = 1000
    fetched = 0
    while True:
        try:
            resp = (
                sb.table("document_chunks")
                .select("chunk_id, chunk_text")
                .range(offset, offset + page - 1)
                .execute()
            )
        except Exception as err:  # pragma: no cover
            LOGGER.warning("Supabase fetch failed: %s", err)
            return
        rows = getattr(resp, "data", None) or []
        for r in rows:
            yield str(r.get("chunk_id") or ""), str(r.get("chunk_text") or "")
            fetched += 1
            if limit is not None and fetched >= limit:
                return
        if len(rows) < page:
            return
        offset += page


if __name__ == "__main__":
    sys.exit(main())
