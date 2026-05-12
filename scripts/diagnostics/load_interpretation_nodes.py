"""fix_v11_may Phase 11B — operator-targeted CLI for the InterpretationNode loader.

Runs `graph/interpretation_loader.build_interpretation_load_plan` against a
target Falkor (local docker or cloud staging/production) and executes the
batched UNWIND MERGE statements. Idempotent on `doc_id` for nodes and on
edge endpoints — safe to re-run.

Usage:

    # Local docker Falkor (parity probe — `npm run dev` env)
    PYTHONPATH=src:. uv run python scripts/diagnostics/load_interpretation_nodes.py \\
        --target local

    # Cloud staging Falkor (needs FALKORDB_URL pointing at cloud)
    PYTHONPATH=src:. uv run python scripts/diagnostics/load_interpretation_nodes.py \\
        --target staging --eligible-from-cloud

    # Plan only — no execution. Useful for diffing eligible sets.
    PYTHONPATH=src:. uv run python scripts/diagnostics/load_interpretation_nodes.py \\
        --target staging --dry-run

What this script DOES NOT do:
    * Re-audit, re-parse, or re-build `canonical_corpus_manifest.json`. The
      loader reads the existing manifest from `artifacts/`. If you need a
      fresh manifest, run `make phase2-graph-artifacts` first.
    * Re-load `ArticleNode` / `ReformNode` / `TopicNode` into Falkor. The
      loader assumes those already exist (they're populated by the regular
      `materialize_graph_artifacts` ingest run). INTERPRETS edges are
      filtered to only those whose target `ArticleNode.article_number`
      actually exists in cloud Falkor (when `--eligible-from-cloud` is
      passed) so the script doesn't emit no-op edges.
    * Write to Supabase. This is pure-Falkor.

Per `feedback_lia_graph_cloud_writes_authorized`, this script is
operator-authorized and writes to cloud Falkor on `--target=staging` or
`--target=production`. Announce before running. Per CLAUDE.md "Fail Fast,
Fix Fast", run with `--target=local` first when validating new loader code.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Make `src/` importable when invoked directly (mirrors the
# `PYTHONPATH=src:. uv run` invocation pattern used by `make smoke-deps`
# etc.).
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from lia_graph.graph.client import GraphClient, GraphWriteStatement  # noqa: E402
from lia_graph.graph.interpretation_loader import (  # noqa: E402
    build_interpretation_load_plan,
    build_interpretation_load_plan_from_supabase,
    execute_interpretation_load_plan,
    interpretation_loader_enabled,
)


_LOCAL_FALKOR_URL = "redis://127.0.0.1:6389"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Phase 11B interpretation loader against Falkor.",
    )
    parser.add_argument(
        "--target",
        choices=("local", "staging", "production"),
        required=True,
        help=(
            "Falkor target. `local` uses the docker Falkor at "
            f"{_LOCAL_FALKOR_URL}; `staging` / `production` require "
            "FALKORDB_URL already set in the environment (sourced from "
            ".env.staging or Railway env)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the plan + print diagnostics but skip execution.",
    )
    parser.add_argument(
        "--eligible-from-cloud",
        action="store_true",
        help=(
            "Query Falkor for the actual `ArticleNode.article_number` set "
            "and use it as the eligible-article filter. Without this, the "
            "loader emits INTERPRETS edges for every article number it "
            "extracts from the markdown; MATCH semantics mean missing "
            "endpoints silently no-op in Cypher, but counts would be "
            "inflated in the diagnostic."
        ),
    )
    parser.add_argument(
        "--source",
        choices=("auto", "supabase", "manifest"),
        default="auto",
        help=(
            "Where to read the interpretation doc list + article-ref source "
            "text. `supabase` reads `documents` (filter "
            "`knowledge_class='interpretative_guidance'`) + `document_chunks` "
            "from cloud Supabase — the source of truth for what the panel "
            "retriever returns at request time. `manifest` reads "
            "`artifacts/canonical_corpus_manifest.json` + local "
            "`knowledge_base/` markdown. `auto` (default) picks "
            "`supabase` for staging/production targets and `manifest` for "
            "local — matches the preflight-locally-then-cloud workflow."
        ),
    )
    parser.add_argument(
        "--manifest-path",
        default=str(_REPO_ROOT / "artifacts" / "canonical_corpus_manifest.json"),
        help="Path to canonical_corpus_manifest.json (used when --source=manifest).",
    )
    parser.add_argument(
        "--knowledge-base-root",
        default=str(_REPO_ROOT / "knowledge_base"),
        help="Path to knowledge_base/ (used when --source=manifest).",
    )
    return parser.parse_args()


def _resolve_source(args: argparse.Namespace) -> str:
    if args.source != "auto":
        return args.source
    return "manifest" if args.target == "local" else "supabase"


def _ensure_target_env(target: str) -> None:
    """Sanity-check the env before we connect. `local` sets the URL inline;
    `staging` + `production` require it to be already set."""
    if target == "local":
        os.environ.setdefault("FALKORDB_URL", _LOCAL_FALKOR_URL)
        return
    if not os.environ.get("FALKORDB_URL"):
        print(
            f"[abort] --target={target} requires FALKORDB_URL to be set. "
            f"Source .env.staging (or the Railway env) before re-running."
        )
        sys.exit(2)


def _probe_eligible_article_numbers(client: GraphClient) -> set[str]:
    """Read every `ArticleNode.article_number` currently in the target
    graph. Used as the eligibility filter so the loader only emits
    INTERPRETS edges whose target exists in cloud Falkor."""
    stmt = GraphWriteStatement(
        description="ProbeEligibleArticleNumbers",
        query=(
            "MATCH (a:ArticleNode)\n"
            "WHERE a.article_number IS NOT NULL AND a.article_number <> ''\n"
            "RETURN DISTINCT a.article_number AS article_number\n"
        ),
        parameters={},
    )
    result = client.execute(stmt, strict=True)
    return {
        str(row.get("article_number") or "").strip()
        for row in result.rows
        if str(row.get("article_number") or "").strip()
    }


def _probe_eligible_topic_keys(client: GraphClient) -> set[str]:
    stmt = GraphWriteStatement(
        description="ProbeEligibleTopicKeys",
        query=(
            "MATCH (t:TopicNode)\n"
            "WHERE t.topic_key IS NOT NULL AND t.topic_key <> ''\n"
            "RETURN DISTINCT t.topic_key AS topic_key\n"
        ),
        parameters={},
    )
    result = client.execute(stmt, strict=True)
    return {
        str(row.get("topic_key") or "").strip().lower()
        for row in result.rows
        if str(row.get("topic_key") or "").strip()
    }


def _probe_post_load_state(client: GraphClient) -> dict[str, int]:
    """Confirm the loader actually wrote nodes + edges. Counts:
    (i) InterpretationNode, (ii) ArticleNode reached by an INTERPRETS,
    (iii) total INTERPRETS instances, (iv) total COVERS_TOPIC instances."""
    counts: dict[str, int] = {}
    for label, query in (
        (
            "interpretation_nodes",
            "MATCH (i:InterpretationNode) RETURN count(i) AS n",
        ),
        (
            "articles_with_inbound_interprets",
            "MATCH (a:ArticleNode)<-[:INTERPRETS]-(:InterpretationNode) "
            "RETURN count(DISTINCT a) AS n",
        ),
        (
            "interprets_edge_count",
            "MATCH (:InterpretationNode)-[r:INTERPRETS]->(:ArticleNode) "
            "RETURN count(r) AS n",
        ),
        (
            "covers_topic_edge_count",
            "MATCH (:InterpretationNode)-[r:COVERS_TOPIC]->(:TopicNode) "
            "RETURN count(r) AS n",
        ),
    ):
        stmt = GraphWriteStatement(
            description=f"Probe_{label}",
            query=query + "\n",
            parameters={},
        )
        try:
            result = client.execute(stmt, strict=True)
            rows = list(result.rows or ())
            counts[label] = int(rows[0].get("n", 0)) if rows else 0
        except Exception as exc:  # noqa: BLE001
            counts[label] = -1
            print(f"  probe[{label}] FAILED: {exc}")
    return counts


def main() -> int:
    args = _parse_args()
    target = args.target

    if not interpretation_loader_enabled():
        print(
            "[abort] LIA_INGEST_INTERPRETATION_NODES is OFF in the current env. "
            "Set to `enforce` (or unset to use the default) before re-running."
        )
        return 2

    _ensure_target_env(target)
    source = _resolve_source(args)
    manifest_path = Path(args.manifest_path)
    knowledge_base_root = Path(args.knowledge_base_root)
    if source == "manifest":
        if not manifest_path.exists():
            print(
                f"[abort] manifest not found at {manifest_path}. "
                f"Run `make phase2-graph-artifacts` to build it."
            )
            return 2
        if not knowledge_base_root.exists():
            print(f"[abort] knowledge_base not found at {knowledge_base_root}")
            return 2

    client = GraphClient.from_env()
    print(f"[info] target={target}")
    print(f"[info] source={source}")
    print(f"[info] FALKORDB_URL={client.config.redacted_url}")
    print(f"[info] graph_name={client.config.graph_name}")
    if source == "manifest":
        print(f"[info] manifest={manifest_path}")
        print(f"[info] knowledge_base={knowledge_base_root}")
    else:
        print(f"[info] supabase_url={(os.environ.get('SUPABASE_URL') or '').strip()}")

    eligible_article_ids: set[str] | None = None
    eligible_topic_keys: set[str] | None = None
    if args.eligible_from_cloud:
        print("[probe] reading eligible ArticleNode.article_number set ...")
        eligible_article_ids = _probe_eligible_article_numbers(client)
        print(f"  → {len(eligible_article_ids)} distinct article_numbers")
        print("[probe] reading eligible TopicNode.topic_key set ...")
        eligible_topic_keys = _probe_eligible_topic_keys(client)
        print(f"  → {len(eligible_topic_keys)} distinct topic_keys")

    print(f"[plan] building interpretation load plan (source={source}) ...")
    if source == "manifest":
        plan = build_interpretation_load_plan(
            manifest_path=manifest_path,
            knowledge_base_root=knowledge_base_root,
            graph_client=client,
            eligible_article_ids=eligible_article_ids,
            eligible_topic_keys=eligible_topic_keys,
        )
    else:
        # Lazy-import the supabase client so a `--source=manifest` run
        # doesn't pull in supabase-py + dotenv at all.
        from lia_graph.supabase_client import get_supabase_client
        supabase_client = get_supabase_client()
        plan = build_interpretation_load_plan_from_supabase(
            supabase_client=supabase_client,
            graph_client=client,
            eligible_article_ids=eligible_article_ids,
            eligible_topic_keys=eligible_topic_keys,
        )
    plan_summary = plan.to_dict()
    print("[plan] " + json.dumps(plan_summary, indent=2, ensure_ascii=False))

    if args.dry_run:
        print("[done] --dry-run; skipping execution.")
        return 0

    print(f"[exec] executing {len(plan.statements)} batched statement(s) ...")
    t0 = time.perf_counter()
    results = execute_interpretation_load_plan(
        plan, graph_client=client, strict=True
    )
    elapsed = time.perf_counter() - t0
    print(f"[exec] done in {elapsed:.2f}s")

    success = sum(1 for r in results if r.ok and not r.skipped)
    failed = sum(1 for r in results if not r.ok)
    skipped = sum(1 for r in results if r.skipped)
    print(
        f"[exec] success={success} failure={failed} skipped={skipped} "
        f"total={len(results)}"
    )
    for r in results:
        if r.ok and not r.skipped:
            print(f"  ✓ {r.description}: stats={dict(r.stats or {})}")
        elif r.skipped:
            print(f"  - {r.description} SKIPPED diag={dict(r.diagnostics or {})}")
        else:
            print(f"  ✗ {r.description}: error={r.error}")

    print("[probe] post-load graph state:")
    counts = _probe_post_load_state(client)
    for label, n in counts.items():
        print(f"  {label} = {n}")

    print("[done]")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
