#!/usr/bin/env python
"""Post-hoc repair: read Supabase subtema state and emit Falkor bindings.

Reads from Supabase ``documents`` (joined to article rows in FalkorDB via
the SUIN-compatible ``doc_id`` = article_key mapping) and for every doc
where ``(topic, subtema)`` resolves in the curated taxonomy, MERGEs a
``SubTopicNode`` + a ``HAS_SUBTOPIC`` edge per article.

This is a one-shot Falkor-only repair. It does NOT mutate Supabase. Runs
in ~30-60 seconds against the local WIP stack. Safe to re-run (idempotent
MERGE).

Usage:
    python scripts/repair_falkor_subtopic.py --target wip
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
for _candidate in (_SRC_DIR, _REPO_ROOT):
    _s = str(_candidate)
    if _candidate.is_dir() and _s not in sys.path:
        sys.path.insert(0, _s)

from lia_graph.env_loader import load_dotenv_if_present  # noqa: E402
from lia_graph.instrumentation import emit_event  # noqa: E402


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="repair_falkor_subtopic")
    p.add_argument("--target", choices=["wip", "production"], default="wip")
    p.add_argument(
        "--generation-id",
        default=None,
        help="Target generation. Defaults to active generation.",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--allow-non-local-env",
        action="store_true",
        help="Bypass the local-env posture guard.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    load_dotenv_if_present()
    args = _build_argparser().parse_args(argv)

    if not args.allow_non_local_env:
        from lia_graph.env_posture import EnvPostureError, assert_local_posture

        try:
            assert_local_posture(require_supabase=True, require_falkor=True)
        except EnvPostureError as exc:
            sys.stderr.write(f"repair_falkor_subtopic: {exc}\n")
            return 4

    from lia_graph.graph import GraphClient
    from lia_graph.graph.client import GraphWriteStatement
    from lia_graph.subtopic_taxonomy_loader import load_taxonomy
    from lia_graph.supabase_client import create_supabase_client_for_target

    client = create_supabase_client_for_target(args.target)
    graph = GraphClient.from_env()
    taxonomy = load_taxonomy()

    gen_id = args.generation_id
    if not gen_id:
        resp = (
            client.table("corpus_generations")
            .select("generation_id")
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        rows = list(getattr(resp, "data", None) or [])
        if not rows:
            sys.stderr.write("repair_falkor_subtopic: no active generation\n")
            return 1
        gen_id = rows[0]["generation_id"]

    # Fetch docs with subtema + topic in this generation
    resp = (
        client.table("documents")
        .select("doc_id, topic, subtema, relative_path")
        .eq("sync_generation", gen_id)
        .not_.is_("subtema", None)
        .execute()
    )
    docs = list(getattr(resp, "data", None) or [])
    print(f"docs to consider: {len(docs)}")

    # Fetch articles keyed by source_path from Falkor.
    article_stmt = GraphWriteStatement(
        description="repair.list_articles",
        query=(
            "MATCH (a:ArticleNode) "
            "RETURN a.article_id AS article_id, a.source_path AS source_path"
        ),
        parameters={},
    )
    ar = graph.execute(article_stmt, strict=True)
    articles_by_path: dict[str, list[str]] = {}
    for row in ar.rows:
        sp = str(row.get("source_path") or "")
        ak = str(row.get("article_id") or "")
        if sp and ak:
            articles_by_path.setdefault(sp, []).append(ak)
    total_articles = sum(len(v) for v in articles_by_path.values())
    print(f"articles keyed by source_path: {total_articles}")

    nodes_emitted = set()
    edges_emitted = 0
    skipped_no_tax = 0
    skipped_no_articles = 0

    for doc in docs:
        topic = doc.get("topic")
        sub = doc.get("subtema")
        rel = doc.get("relative_path")
        if not (topic and sub and rel):
            continue
        entry = taxonomy.lookup_by_key.get((topic, sub))
        if entry is None:
            skipped_no_tax += 1
            continue
        # Resolve articles — try a few source_path candidate forms
        candidates = [rel, f"knowledge_base/{rel}"]
        arts: list[str] = []
        for cand in candidates:
            if cand in articles_by_path:
                arts = articles_by_path[cand]
                break
        if not arts:
            skipped_no_articles += 1
            continue

        if not args.dry_run:
            # Node merge (once per sub_topic_key)
            if sub not in nodes_emitted:
                graph.execute(
                    GraphWriteStatement(
                        description="repair.subtopic_node.merge",
                        query=(
                            "MERGE (s:SubTopicNode { sub_topic_key: $k }) "
                            "SET s.parent_topic = $pt, s.label = $lbl"
                        ),
                        parameters={
                            "k": sub,
                            "pt": topic,
                            "lbl": getattr(entry, "label", sub),
                        },
                    ),
                    strict=True,
                )
                nodes_emitted.add(sub)
            # Edge merges for every article of this doc
            # (ArticleNode key_field is `article_id` per default_graph_schema)
            for ak in arts:
                graph.execute(
                    GraphWriteStatement(
                        description="repair.has_subtopic.merge",
                        query=(
                            "MATCH (a:ArticleNode { article_id: $ak }) "
                            "MATCH (s:SubTopicNode { sub_topic_key: $k }) "
                            "MERGE (a)-[:HAS_SUBTOPIC]->(s)"
                        ),
                        parameters={"ak": ak, "k": sub},
                    ),
                    strict=True,
                )
                edges_emitted += 1

    emit_event(
        "subtopic.repair.done",
        {
            "generation_id": gen_id,
            "docs_considered": len(docs),
            "nodes_emitted": len(nodes_emitted),
            "edges_emitted": edges_emitted,
            "skipped_no_tax": skipped_no_tax,
            "skipped_no_articles": skipped_no_articles,
            "dry_run": args.dry_run,
        },
    )
    print(
        f"docs={len(docs)} nodes={len(nodes_emitted)} edges={edges_emitted} "
        f"skip_no_tax={skipped_no_tax} skip_no_articles={skipped_no_articles} "
        f"dry_run={args.dry_run}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
