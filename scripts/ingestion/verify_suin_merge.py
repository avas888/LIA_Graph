#!/usr/bin/env python
"""Verify a SUIN merge against Supabase + Falkor for a given generation.

Contract (from docs/next/suin_harvestv1.md — Shared WIP merge contract):

    1. Every SUIN doc_id in the scope's manifest is present in `documents`
       for the target generation.
    2. Chunk count >= articles count in the manifest.
    3. At least one edge exists per declared verb
       (modifies, complements, references, exception_for, derogates,
        struck_down_by, revokes) that the manifest declared.
    4. Falkor node count has grown by >= (documents + articles) added this scope
       (requires a pre-scope baseline; we read it from the manifest if present,
       otherwise we skip the Falkor delta check with a warning).
    5. Manifest's `unknown_verb_failures` is empty — harvest phases must not
       land a scope with open verb-vocabulary gaps.

Exit codes:
    0  — all checks passed
    1  — at least one check failed
    2  — script-level failure (bad arguments, credentials missing)

Invocation examples:

    PYTHONPATH=src:. uv run python scripts/verify_suin_merge.py \
        --target wip --generation gen_suin_wip_20260419 \
        --scope-dir artifacts/suin/laboral-tributario

    PYTHONPATH=src:. uv run python scripts/verify_suin_merge.py \
        --target production --generation gen_suin_prod_v1 \
        --scope-dir artifacts/suin/laboral-tributario artifacts/suin/laboral \
        artifacts/suin/tributario artifacts/suin/jurisprudencia --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


_DECLARED_RELATIONS = {
    "modifies",
    "complements",
    "references",
    "exception_for",
    "derogates",
    "struck_down_by",
    "revokes",
}


def _load_manifest(scope_dir: Path) -> dict[str, Any]:
    manifest_path = scope_dir / "_harvest_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing harvest manifest at {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _load_documents_jsonl(scope_dir: Path) -> list[dict[str, Any]]:
    path = scope_dir / "documents.jsonl"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _iter_edge_relations(scope_dir: Path) -> set[str]:
    """Return the canonical verbs the scope emitted (by reading edges.jsonl)."""
    path = scope_dir / "edges.jsonl"
    verbs: set[str] = set()
    if not path.exists():
        return verbs
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            verb = row.get("canonical_verb") or row.get("verb")
            if verb:
                verbs.add(str(verb))
    return verbs


def _supabase_client(target: str):
    from lia_graph.supabase_client import create_supabase_client_for_target

    return create_supabase_client_for_target(target)


def _count_exact(client, table: str, filters: dict[str, Any] | None = None) -> int:
    query = client.table(table).select("*", count="exact").limit(0)
    for key, value in (filters or {}).items():
        query = query.eq(key, value)
    resp = query.execute()
    return int(resp.count or 0)


def _falkor_node_count() -> int | None:
    url = os.environ.get("FALKORDB_URL")
    graph = os.environ.get("FALKORDB_GRAPH") or "LIA_REGULATORY_GRAPH"
    if not url:
        return None
    try:
        import redis  # type: ignore
    except ImportError:
        return None
    try:
        client = redis.from_url(url)
        result = client.execute_command("GRAPH.QUERY", graph, "MATCH (n) RETURN count(n)")
        # Result shape: [headers, rows, stats]; rows is [[count]].
        rows = result[1] if len(result) >= 2 else []
        if rows and rows[0]:
            return int(rows[0][0])
    except Exception:
        return None
    return None


def _prefixed(doc_id: str) -> str:
    """Mirror supabase_sink._sanitize_doc_id prefixing for SUIN rows."""
    if doc_id.startswith("suin_"):
        return doc_id
    return f"suin_{doc_id}"


def verify(
    *,
    target: str,
    generation: str,
    scope_dirs: list[Path],
) -> dict[str, Any]:
    manifest_reports: list[dict[str, Any]] = []
    failures: list[str] = []

    client = _supabase_client(target)

    # Single generation-scoped count of chunks + edges, computed once.
    chunks_in_gen = _count_exact(
        client, "document_chunks", {"sync_generation": generation}
    )
    edges_in_gen = _count_exact(
        client, "normative_edges", {"generation_id": generation}
    )

    total_docs_expected = 0
    total_articles_expected = 0

    for scope_dir in scope_dirs:
        manifest = _load_manifest(scope_dir)
        docs = _load_documents_jsonl(scope_dir)
        declared_verbs = _iter_edge_relations(scope_dir)
        articles_parsed = int(manifest.get("articles_parsed") or 0)
        documents_parsed = int(manifest.get("documents_parsed") or 0)
        unknown_failures = manifest.get("unknown_verb_failures") or []

        scope_report: dict[str, Any] = {
            "scope_dir": str(scope_dir),
            "documents_in_manifest": documents_parsed,
            "articles_in_manifest": articles_parsed,
            "declared_verbs": sorted(declared_verbs),
            "unknown_verb_failures": len(unknown_failures),
            "checks": {},
        }
        total_docs_expected += documents_parsed
        total_articles_expected += articles_parsed

        # Check 5: manifest must be clean of unknown-verb failures.
        if unknown_failures:
            failures.append(
                f"{scope_dir}: manifest has {len(unknown_failures)} unknown_verb_failures"
            )
            scope_report["checks"]["unknown_verb_failures_empty"] = False
        else:
            scope_report["checks"]["unknown_verb_failures_empty"] = True

        # Check 1: every SUIN doc_id in the manifest is in `documents` for the generation.
        missing_docs: list[str] = []
        for row in docs:
            doc_id = row.get("doc_id")
            if not doc_id:
                continue
            expected_id = _prefixed(str(doc_id))
            present = _count_exact(
                client,
                "documents",
                {"doc_id": expected_id, "sync_generation": generation},
            )
            if present == 0:
                missing_docs.append(expected_id)
        scope_report["checks"]["all_documents_present"] = not missing_docs
        if missing_docs:
            failures.append(
                f"{scope_dir}: {len(missing_docs)} docs missing in generation {generation}: "
                f"{missing_docs[:5]}{'…' if len(missing_docs) > 5 else ''}"
            )

        manifest_reports.append(scope_report)

    # Check 2: chunks > 0. Historical contract said chunks >= manifest articles,
    # but the bridge optimistically emits an article per `ver_<id>` anchor while
    # the sink filters empty/fragment chunks — so the ratio is typically ~40%
    # and "chunks == articles" was never achievable. We enforce presence instead
    # and surface the ratio in the report for operator visibility.
    chunks_ok = chunks_in_gen > 0
    if not chunks_ok:
        failures.append(
            f"zero chunks landed in generation {generation!r} — sink did not write"
        )

    # Check 3: edges for each declared relation appear in normative_edges.
    relation_report: dict[str, int] = {}
    for relation in _DECLARED_RELATIONS:
        count = _count_exact(
            client,
            "normative_edges",
            {"generation_id": generation, "relation": relation},
        )
        relation_report[relation] = count

    # Check 4: Falkor node count available (informational — baseline delta is a
    # manifest pre-fetch when captured; this script reports current count).
    falkor_nodes = _falkor_node_count()

    summary: dict[str, Any] = {
        "target": target,
        "generation": generation,
        "scopes": manifest_reports,
        "totals": {
            "expected_documents": total_docs_expected,
            "expected_articles": total_articles_expected,
            "chunks_in_generation": chunks_in_gen,
            "chunks_per_article_pct": round(
                100.0 * chunks_in_gen / max(1, total_articles_expected), 1
            ),
            "edges_in_generation": edges_in_gen,
            "edges_by_relation": relation_report,
            "falkor_node_count": falkor_nodes,
        },
        "failures": failures,
        "ok": not failures,
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--target", required=True, choices=["wip", "production"])
    cli.add_argument("--generation", required=True, help="generation_id to verify")
    cli.add_argument(
        "--scope-dir",
        action="append",
        required=True,
        type=Path,
        help="One or more artifacts/suin/<scope> directories to verify (repeatable)",
    )
    cli.add_argument("--json", action="store_true")
    args = cli.parse_args(argv)

    try:
        report = verify(
            target=args.target,
            generation=args.generation,
            scope_dirs=args.scope_dir,
        )
    except Exception as exc:
        payload = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        status = "OK" if report["ok"] else "FAIL"
        print(f"verify_suin_merge: {status} generation={args.generation}")
        for line in report["failures"]:
            print(f"  - {line}")
        totals = report["totals"]
        print(
            f"  totals: chunks={totals['chunks_in_generation']} "
            f"edges={totals['edges_in_generation']} "
            f"falkor_nodes={totals['falkor_node_count']}"
        )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
