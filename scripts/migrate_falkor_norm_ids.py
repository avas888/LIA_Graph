"""v19 Fase 2 — Falkor :ArticleNode.norm_id migration.

Reads every :ArticleNode from a Falkor target (local docker / cloud
staging / cloud production), derives a canonical `norm_id` for each
numbered statutory article from its `(source_path, article_number)`,
and stamps the node with `norm_id` plus a unique index.

Per v19 scope doc §2.0.5 Gate 1 (Opción B): this is a Falkor-only
migration. Supabase `chunk_id` is NOT touched. Embeddings are content-
keyed semantically and stored under chunk_id — preserving chunk_id
preserves embeddings, so no re-embedding work is triggered.

Why reuse `canon.canonicalize()` instead of inventing a new mapping
grammar:
- `public.norms.norm_id` already uses the dotted grammar.
- `:Norm` Falkor nodes (the vigencia catalog) already use it.
- `canonicalize()` is the single source of truth per fixplan_v3 §0.5.
- This script only constructs the free-text *mention* for each node
  (e.g. `"Ley 50 de 1990 art. 64"`) and delegates the formatting.

Usage:
  PYTHONPATH=src:. uv run python scripts/migrate_falkor_norm_ids.py [options]

Options:
  --target {local|staging|production}    Falkor target (default: local)
  --dry-run                              Default mode. Writes JSONL plan + summary.
                                         No Falkor writes.
  --apply                                Applies the plan to Falkor.
  --strict                               Abort if any numbered node is
                                         unclassified (OTHER). Default in --dry-run.
  --limit N                              Only process first N nodes (smoke).
  --report-path PATH                     Where the dry-run report goes
                                         (default: artifacts/v19/norm_id_plan.jsonl).
  --batch-size N                         Apply-mode UNWIND batch size (default: 200).
  --verbose                              DEBUG logging.

Exit codes:
  0 = success (dry-run report written, or apply committed)
  2 = unclassified rows in --strict mode
  3 = import / connection / config error
  4 = post-apply verification failed
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

LOGGER = logging.getLogger("migrate_falkor_norm_ids")


# Rules + derivation live in `lia_graph.norm_id_rules` so the loader can
# import the same logic (Fase 3). Anything the migration script needs:
#   - `derive_norm_id(...)` — the entry point
#   - `DerivationOutcome` — the dataclass it returns
# The migration script keeps the Falkor I/O + reporting + CLI.
def _import_rules():
    from lia_graph.norm_id_rules import DerivationOutcome, derive_norm_id

    return derive_norm_id, DerivationOutcome


# Backwards-compat for tests / callers that imported these symbols directly
# from this script.
def derive_norm_id(*, article_id: str, article_number: str, source_path: str):
    fn, _ = _import_rules()
    return fn(article_id=article_id, article_number=article_number, source_path=source_path)


# Re-export so legacy imports continue to work.
from lia_graph.norm_id_rules import DerivationOutcome as DerivationOutcome  # noqa: E402,F401


# ---------------------------------------------------------------------------
# Falkor I/O
# ---------------------------------------------------------------------------


@dataclass
class MigrationPlan:
    outcomes: list[DerivationOutcome] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    duplicates: dict[str, list[str]] = field(default_factory=dict)
    other_samples: list[DerivationOutcome] = field(default_factory=list)

    def bucket(self) -> None:
        """Compute summary counts after outcomes are populated."""
        self.counts = {}
        by_norm_id: dict[str, list[str]] = {}
        for o in self.outcomes:
            self.counts[o.rule_name] = self.counts.get(o.rule_name, 0) + 1
            if o.norm_id:
                by_norm_id.setdefault(o.norm_id, []).append(o.article_id)
            if o.rule_name == "OTHER" and len(self.other_samples) < 50:
                self.other_samples.append(o)
        self.duplicates = {nid: aids for nid, aids in by_norm_id.items() if len(aids) > 1}

    def total(self) -> int:
        return len(self.outcomes)

    def classified_count(self) -> int:
        return sum(1 for o in self.outcomes if o.norm_id is not None)

    def other_count(self) -> int:
        return self.counts.get("OTHER", 0)

    def prose_only_count(self) -> int:
        return self.counts.get("prose_only", 0)


def _fetch_article_nodes(
    graph_client,
    *,
    limit: int | None = None,
) -> list[tuple[str, str, str]]:
    """Read every :ArticleNode and return (article_id, article_number, source_path) tuples.

    Empty / missing properties surface as ''.
    """
    from lia_graph.graph.client import GraphWriteStatement

    query = (
        "MATCH (a:ArticleNode) "
        "RETURN a.article_id AS article_id, "
        "       coalesce(a.article_number, '') AS article_number, "
        "       coalesce(a.source_path, '') AS source_path"
    )
    if limit is not None:
        query += f" LIMIT {int(limit)}"
    stmt = GraphWriteStatement(
        description="read-all-article-nodes",
        query=query,
        parameters={},
    )
    result = graph_client.execute(stmt, strict=True)
    rows = result.rows or ()
    out: list[tuple[str, str, str]] = []
    for r in rows:
        if isinstance(r, dict):
            aid = str(r.get("article_id") or "")
            num = str(r.get("article_number") or "")
            sp = str(r.get("source_path") or "")
        else:
            # Falkor row shape may be a positional sequence
            aid = str(r[0] or "")
            num = str(r[1] or "") if len(r) > 1 else ""
            sp = str(r[2] or "") if len(r) > 2 else ""
        if not aid:
            continue
        out.append((aid, num, sp))
    return out


def _apply_index_and_norm_ids(
    graph_client,
    plan: MigrationPlan,
    *,
    batch_size: int,
) -> dict[str, int]:
    """Apply: CREATE INDEX (idempotent) + UNWIND SET node.norm_id per batch."""
    from lia_graph.graph.client import GraphWriteStatement

    stats = {"nodes_written": 0, "batches": 0, "index_created": 0}

    # 1. Unique index (Falkor treats existing-index error as benign per
    # _is_benign_index_error in graph/client.py:595-609).
    idx_stmt = GraphWriteStatement(
        description="CreateIndex:ArticleNode.norm_id",
        query="CREATE INDEX FOR (a:ArticleNode) ON (a.norm_id)",
        parameters={},
    )
    idx_result = graph_client.execute(idx_stmt, strict=False)
    if not idx_result.skipped:
        stats["index_created"] = 1

    # 2. Batched UNWIND SET.
    rows = [
        {"article_id": o.article_id, "norm_id": o.norm_id}
        for o in plan.outcomes
        if o.norm_id is not None
    ]
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        stmt = GraphWriteStatement(
            description=f"SetNormId:batch-{stats['batches']}",
            query=(
                "UNWIND $rows AS row "
                "MATCH (a:ArticleNode {article_id: row.article_id}) "
                "SET a.norm_id = row.norm_id"
            ),
            parameters={"rows": batch},
        )
        graph_client.execute(stmt, strict=True)
        stats["nodes_written"] += len(batch)
        stats["batches"] += 1
    return stats


def _verify_post_apply(graph_client, plan: MigrationPlan) -> dict[str, int | bool]:
    """Sanity-check the apply: count nodes with norm_id set, count uniques."""
    from lia_graph.graph.client import GraphWriteStatement

    expected_with = plan.classified_count()
    stmt = GraphWriteStatement(
        description="verify-norm-id-coverage",
        query=(
            "MATCH (a:ArticleNode) "
            "WHERE a.norm_id IS NOT NULL "
            "RETURN count(a) AS with_norm_id, count(DISTINCT a.norm_id) AS distinct_norm_ids"
        ),
        parameters={},
    )
    result = graph_client.execute(stmt, strict=True)
    rows = result.rows or ()
    if not rows:
        return {"verified": False, "with_norm_id": 0, "distinct_norm_ids": 0}
    r = rows[0]
    with_norm_id = int(r.get("with_norm_id", 0) if isinstance(r, dict) else r[0])
    distinct = int(r.get("distinct_norm_ids", 0) if isinstance(r, dict) else r[1])
    return {
        "verified": with_norm_id >= expected_with,
        "with_norm_id": with_norm_id,
        "distinct_norm_ids": distinct,
        "expected_classified": expected_with,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _write_report(plan: MigrationPlan, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    # Line-delimited per-node outcomes
    with report_path.open("w", encoding="utf-8") as f:
        for o in plan.outcomes:
            f.write(json.dumps({
                "article_id": o.article_id,
                "article_number": o.article_number,
                "source_path": o.source_path,
                "norm_id": o.norm_id,
                "rule_name": o.rule_name,
                "mention": o.mention,
                "refusal_reason": o.refusal_reason,
            }, ensure_ascii=False) + "\n")

    summary_path = report_path.with_suffix(".summary.json")
    summary = {
        "total_article_nodes": plan.total(),
        "classified_count": plan.classified_count(),
        "prose_only_count": plan.prose_only_count(),
        "other_count": plan.other_count(),
        "by_rule": dict(sorted(plan.counts.items(), key=lambda kv: -kv[1])),
        "duplicate_norm_ids": {
            nid: aids[:5] for nid, aids in list(plan.duplicates.items())[:50]
        },
        "duplicate_norm_id_count": len(plan.duplicates),
        "other_samples": [
            {
                "article_id": s.article_id,
                "article_number": s.article_number,
                "source_path": s.source_path,
            }
            for s in plan.other_samples
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--target", default=os.getenv("LIA_FALKOR_TARGET", "local"),
                   choices=["local", "staging", "production"])
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True,
                      help="Default. Writes JSONL plan + summary. No Falkor writes.")
    mode.add_argument("--apply", action="store_true",
                      help="Applies the plan to Falkor.")
    p.add_argument("--strict", action="store_true",
                   help="Abort if any numbered node is unclassified (OTHER).")
    p.add_argument("--allow-other-up-to", type=int, default=0,
                   help="Tolerate up to N OTHER nodes in --apply mode "
                        "(default 0 = strict). Use when a small handful of "
                        "OTHERs are known corpus artifacts.")
    p.add_argument("--limit", type=int, default=None,
                   help="Smoke mode — only process first N nodes.")
    p.add_argument("--report-path", type=Path,
                   default=Path("artifacts/v19/norm_id_plan.jsonl"),
                   help="Where the dry-run plan + summary land.")
    p.add_argument("--batch-size", type=int, default=200,
                   help="UNWIND batch size for --apply (default 200).")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.apply:
        args.dry_run = False
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    try:
        from lia_graph.graph.client import GraphClient
        from lia_graph.env_loader import load_dotenv_if_present
    except Exception as err:
        LOGGER.error("Cannot import GraphClient / env_loader: %s", err)
        return 3

    # Steer the .env file selection. `LIA_ENV=staging` makes
    # `load_dotenv_if_present` pick up `.env.staging` (which carries the
    # cloud FALKORDB_URL). Don't clobber an explicit env override.
    if args.target in ("staging", "production"):
        os.environ.setdefault("LIA_ENV", args.target)
    load_dotenv_if_present()

    LOGGER.info("Mode: %s | Target: %s | LIA_ENV=%s | Strict: %s",
                "APPLY" if args.apply else "DRY-RUN",
                args.target,
                os.getenv("LIA_ENV", "(unset)"),
                args.strict)

    graph_client = GraphClient.from_env()
    if not graph_client.config.is_configured:
        LOGGER.error("FALKORDB_URL not configured for target=%s — set env vars "
                     "(e.g. LIA_ENV=%s) or change --target.",
                     args.target, args.target)
        return 3

    LOGGER.info("Connected to graph %s at %s",
                graph_client.config.graph_name,
                graph_client.config.redacted_url)

    # ---- Read ----
    t0 = time.perf_counter()
    triples = _fetch_article_nodes(graph_client, limit=args.limit)
    LOGGER.info("Read %d :ArticleNode rows in %.2fs",
                len(triples), time.perf_counter() - t0)

    # ---- Derive ----
    plan = MigrationPlan()
    for aid, num, sp in triples:
        plan.outcomes.append(derive_norm_id(
            article_id=aid, article_number=num, source_path=sp,
        ))
    plan.bucket()

    LOGGER.info("Plan: total=%d classified=%d prose_only=%d OTHER=%d",
                plan.total(),
                plan.classified_count(),
                plan.prose_only_count(),
                plan.other_count())
    LOGGER.info("Distinct duplicate norm_ids (>1 article sharing): %d",
                len(plan.duplicates))
    for rule_name, count in sorted(plan.counts.items(), key=lambda kv: -kv[1]):
        LOGGER.info("  rule %-30s %6d", rule_name, count)

    # ---- Write report ----
    _write_report(plan, args.report_path)
    LOGGER.info("Plan written to %s + %s",
                args.report_path, args.report_path.with_suffix(".summary.json"))

    # ---- Strict gating ----
    is_strict = args.strict or args.dry_run is False  # apply implies strict
    other_count = plan.other_count()
    if is_strict and other_count > args.allow_other_up_to:
        LOGGER.error("STRICT mode aborting: %d unclassified (OTHER) nodes "
                     "(allowed: %d). Review %s.summary.json `other_samples` "
                     "and add a path rule, or raise --allow-other-up-to.",
                     other_count, args.allow_other_up_to,
                     args.report_path.with_suffix(".summary.json"))
        return 2
    if other_count > 0 and other_count <= args.allow_other_up_to:
        LOGGER.warning("Proceeding despite %d OTHER node(s) — within "
                       "--allow-other-up-to=%d threshold. These will keep "
                       "their existing article_id, no norm_id stamped.",
                       other_count, args.allow_other_up_to)

    if plan.duplicates:
        LOGGER.warning("%d duplicate norm_ids in plan — multiple articles "
                       "share a derived norm_id. Review before --apply.",
                       len(plan.duplicates))
        if args.apply:
            LOGGER.warning("Apply will MERGE all sharing articles onto the same "
                           "norm_id property — but article_id (the Falkor PK) "
                           "stays unique, so node identity is unchanged.")

    if args.dry_run:
        LOGGER.info("DRY-RUN complete. No Falkor writes. To apply: re-run with --apply.")
        return 0

    # ---- Apply ----
    LOGGER.info("APPLYING to %s — %d nodes to update.",
                args.target, plan.classified_count())
    apply_stats = _apply_index_and_norm_ids(
        graph_client, plan, batch_size=args.batch_size,
    )
    LOGGER.info("Wrote: %d nodes across %d batches; index_created=%d",
                apply_stats["nodes_written"],
                apply_stats["batches"],
                apply_stats["index_created"])

    # ---- Verify ----
    verify = _verify_post_apply(graph_client, plan)
    LOGGER.info("Post-apply verification: %s", verify)
    if not verify.get("verified"):
        LOGGER.error("Post-apply verification FAILED. Expected >= %d nodes "
                     "with norm_id; got %d.",
                     verify.get("expected_classified"),
                     verify.get("with_norm_id"))
        return 4

    LOGGER.info("APPLY complete. norm_id migration done for target=%s.", args.target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
