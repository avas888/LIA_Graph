"""v19 Fase 3 cloud prep — rename `:ArticleNode.article_id` to match `norm_id`.

Why this exists
---------------
Fase 2 (applied 2026-05-15 to cloud staging) stamped `norm_id` as a NEW
property on 1,300 nodes. Their `article_id` PK stayed at the original bare
form (`"64"`, `"420"`, etc.) for backwards compat during the migration.

Fase 3 (loader.graph_article_key, shipped 2026-05-15 PM) makes future
MERGEs use `norm_id` as the key (`"et.art.420"`). Without this rekey,
future ingests would create NEW dotted-keyed nodes alongside the old
bare-keyed nodes — same article, two ArticleNodes.

This script closes that gap: for every node where `norm_id` is set, copy
`norm_id` into `article_id`. After this runs, the next additive ingest
MERGEs onto the same node identity instead of creating a duplicate.

Safety
------
- Idempotent: re-running produces same state (already-renamed rows are
  no-ops because article_id == norm_id).
- Reversible: the inverse Cypher (`SET a.article_id = a.article_number`)
  restores the pre-rename state, since `article_number` was never touched.
- Edges follow: Falkor edges are keyed by node identity (internal node
  id), NOT by the `article_id` property. Rename does not affect edges.
- Default mode is --dry-run; --apply required to write.

Usage
-----
  PYTHONPATH=src:. uv run python scripts/falkor_rekey_article_id_to_norm_id.py [options]

  --target {local|staging|production}    Falkor target (default: local)
  --dry-run                              Default. Counts what would change.
  --apply                                Actually performs the rename.
  --batch-size N                         UNWIND batch (default 500).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

LOGGER = logging.getLogger("falkor_rekey_article_id_to_norm_id")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--target", default="local", choices=["local", "staging", "production"])
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True)
    mode.add_argument("--apply", action="store_true")
    p.add_argument("--batch-size", type=int, default=500)
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.apply:
        args.dry_run = False
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    try:
        from lia_graph.env_loader import load_dotenv_if_present
        from lia_graph.graph.client import GraphClient, GraphWriteStatement
    except Exception as err:
        LOGGER.error("Imports failed: %s", err)
        return 3

    if args.target in ("staging", "production"):
        os.environ.setdefault("LIA_ENV", args.target)
    load_dotenv_if_present()

    LOGGER.info("Mode: %s | Target: %s | LIA_ENV=%s",
                "APPLY" if args.apply else "DRY-RUN",
                args.target,
                os.getenv("LIA_ENV", "(unset)"))

    c = GraphClient.from_env()
    if not c.config.is_configured:
        LOGGER.error("FALKORDB_URL not configured for target=%s", args.target)
        return 3
    LOGGER.info("Connected to graph %s at %s",
                c.config.graph_name, c.config.redacted_url)

    def q(label: str, query: str):
        return c.execute(
            GraphWriteStatement(description=label, query=query, parameters={}),
            strict=True,
        )

    # ---- Pre-flight counts ----
    pre_total = q("count-total",
                  "MATCH (a:ArticleNode) RETURN count(a) AS c").rows or []
    pre_with = q("count-with-norm-id",
                 "MATCH (a:ArticleNode) WHERE a.norm_id IS NOT NULL AND a.norm_id <> '' RETURN count(a) AS c").rows or []
    pre_already = q("count-already-matching",
                    "MATCH (a:ArticleNode) WHERE a.norm_id IS NOT NULL AND a.norm_id <> '' AND a.article_id = a.norm_id RETURN count(a) AS c").rows or []
    pre_pending = q("count-pending",
                    "MATCH (a:ArticleNode) WHERE a.norm_id IS NOT NULL AND a.norm_id <> '' AND a.article_id <> a.norm_id RETURN count(a) AS c").rows or []

    def _val(rows):
        if not rows:
            return 0
        r = rows[0]
        return int(r.get('c', 0) if isinstance(r, dict) else r[0])

    total = _val(pre_total)
    with_id = _val(pre_with)
    already = _val(pre_already)
    pending = _val(pre_pending)

    LOGGER.info("Pre-flight counts:")
    LOGGER.info("  total :ArticleNode             %d", total)
    LOGGER.info("  with non-empty norm_id          %d", with_id)
    LOGGER.info("  already article_id == norm_id   %d (idempotent — would be no-ops)", already)
    LOGGER.info("  pending rename                  %d", pending)

    if pending == 0:
        LOGGER.info("Nothing to do — %d nodes already have article_id == norm_id.", already)
        return 0

    if args.dry_run:
        LOGGER.info("DRY-RUN — would rename %d nodes' article_id to match norm_id.", pending)
        LOGGER.info("To apply: re-run with --apply.")
        return 0

    # ---- Apply ----
    # Cypher: for every node with a non-empty norm_id whose article_id
    # doesn't already match, set article_id = norm_id. One statement,
    # Falkor handles it as a single update pass.
    LOGGER.info("APPLY — running rename for %d nodes...", pending)
    rename_q = (
        "MATCH (a:ArticleNode) "
        "WHERE a.norm_id IS NOT NULL AND a.norm_id <> '' "
        "AND a.article_id <> a.norm_id "
        "SET a.article_id = a.norm_id"
    )
    r = q("rekey", rename_q)
    LOGGER.info("Rename stats: %s", r.stats)

    # ---- Verify ----
    post_already = q("post-count-matching",
                     "MATCH (a:ArticleNode) WHERE a.norm_id IS NOT NULL AND a.norm_id <> '' AND a.article_id = a.norm_id RETURN count(a) AS c").rows or []
    post_pending = q("post-count-pending",
                     "MATCH (a:ArticleNode) WHERE a.norm_id IS NOT NULL AND a.norm_id <> '' AND a.article_id <> a.norm_id RETURN count(a) AS c").rows or []
    LOGGER.info("Post-apply: already=%d  pending=%d",
                _val(post_already), _val(post_pending))
    if _val(post_pending) > 0:
        LOGGER.error("Verification FAILED: %d nodes still have article_id != norm_id",
                     _val(post_pending))
        return 4
    LOGGER.info("APPLY complete. Cloud Falkor ready for F3-3 additive ingest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
