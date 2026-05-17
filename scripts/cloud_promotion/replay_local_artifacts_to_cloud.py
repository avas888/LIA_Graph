"""Replay verified local v20 P1 artifacts to Supabase + Falkor (local or cloud).

v20 P2 entrypoint. Reads the FROZEN iter2 bundle at
`artifacts/v20/local_rehearsal_iter2/` and writes to the chosen targets
without re-running parse / classify / corpus audit.

Idempotent: MERGE on natural keys for Falkor, UPSERT on natural keys for
Supabase. Safe to re-run.

Designed for fix_v20_may.md §3.2 (revised). Stages:

1. **Load.** Stream parsed_articles.jsonl + typed_edges.jsonl + manifest
   into in-memory ParsedArticle / ClassifiedEdge / doc-dict collections.
2. **Sha verify.** If `SHA256SUMS.txt` is present in the bundle, recompute
   and abort on mismatch (drift detection).
3. **Falkor.** Build the same `GraphLoadPlan` the loader builds at ingest
   time; execute against the chosen Falkor target. Emits the same
   `ingest.norm_id.binding_summary` + `ingest.tema.binding_summary`
   diagnostic events.
4. **Supabase.** Drive `SupabaseCorpusSink.write_documents` +
   `write_chunks` + `write_normative_edges`; finalize with optional
   activation.
5. **Report.** Print summary + write `replay_report.json` to artifacts_dir.

CLI flags — see `--help`. Defaults match v20 P2 step 2 (local replay,
non-activating); flip `--target-falkor staging --target-supabase production
--activate` for the cloud step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from lia_graph.graph.client import GraphClient  # noqa: E402
from lia_graph.graph.schema import EdgeKind, GraphEdgeRecord, NodeKind  # noqa: E402
from lia_graph.ingest_subtopic_pass import build_article_subtopic_bindings  # noqa: E402
from lia_graph.ingestion.classifier import ClassifiedEdge  # noqa: E402
from lia_graph.ingestion.loader import (  # noqa: E402
    _graph_article_key,
    _is_article_node_eligible,
    build_graph_load_plan,
    load_graph_plan,
)
from lia_graph.ingestion.parser import ParsedArticle  # noqa: E402
from lia_graph.ingestion.supabase_sink import SupabaseCorpusSink  # noqa: E402
from lia_graph.instrumentation import emit_event  # noqa: E402


DEFAULT_ARTIFACTS_DIR = REPO_ROOT / "artifacts/v20/local_rehearsal_iter2"


# ---------------------------------------------------------------------------
# Load helpers
# ---------------------------------------------------------------------------


def _verify_sha256sums(artifacts_dir: Path) -> None:
    """If SHA256SUMS.txt exists, recompute + abort on mismatch."""
    sums_path = artifacts_dir / "SHA256SUMS.txt"
    if not sums_path.exists():
        print("  [warn] SHA256SUMS.txt not found — proceeding without integrity check.")
        return
    expected: dict[str, str] = {}
    for line in sums_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        sha, rel = parts
        expected[rel.strip()] = sha.strip()
    bad: list[str] = []
    for rel, want in expected.items():
        path = REPO_ROOT / rel
        if not path.exists():
            bad.append(f"{rel}: missing")
            continue
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        got = h.hexdigest()
        if got != want:
            bad.append(f"{rel}: sha {got[:12]}… ≠ expected {want[:12]}…")
    if bad:
        raise RuntimeError(
            "SHA256SUMS verification FAILED — artifact bundle has drifted:\n  - "
            + "\n  - ".join(bad)
        )
    print(f"  [ok] sha256 verified for {len(expected)} files.")


def load_articles(path: Path) -> list[ParsedArticle]:
    out: list[ParsedArticle] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            out.append(
                ParsedArticle(
                    article_key=str(d.get("article_key") or ""),
                    article_number=str(d.get("article_number") or ""),
                    heading=str(d.get("heading") or ""),
                    body=str(d.get("body") or ""),
                    full_text=str(d.get("full_text") or ""),
                    status=str(d.get("status") or "vigente"),
                    source_path=d.get("source_path"),
                    paragraph_markers=tuple(d.get("paragraph_markers") or ()),
                    reform_references=tuple(d.get("reform_references") or ()),
                    annotations=tuple(d.get("annotations") or ()),
                )
            )
    return out


def load_edges(path: Path) -> list[ClassifiedEdge]:
    out: list[ClassifiedEdge] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            record = GraphEdgeRecord(
                kind=EdgeKind(d["kind"]),
                source_kind=NodeKind(d["source_kind"]),
                source_key=str(d.get("source_key") or ""),
                target_kind=NodeKind(d["target_kind"]),
                target_key=str(d.get("target_key") or ""),
                properties=dict(d.get("properties") or {}),
            )
            out.append(
                ClassifiedEdge(
                    record=record,
                    confidence=float(d.get("confidence") or 0.0),
                    rule=str(d.get("rule") or ""),
                    edge_type=d.get("edge_type"),
                    weight=float(d.get("weight") or 1.0),
                )
            )
    return out


def load_corpus_documents(manifest_path: Path, *, repo_root: Path) -> list[dict[str, Any]]:
    """Return list of doc dicts ready for SupabaseCorpusSink.write_documents.

    Reads markdown from disk for each ingestion_decision=include_corpus doc.
    Missing files are tolerated (markdown="") — the sink computes a content
    hash either way.
    """
    manifest = json.loads(manifest_path.read_text())
    docs = manifest.get("documents", [])
    out: list[dict[str, Any]] = []
    missing_md = 0
    binary_assets = 0
    for d in docs:
        if d.get("ingestion_decision") != "include_corpus":
            continue
        md = ""
        # source_path is repo-rooted (e.g. "knowledge_base/CORE.../foo.md");
        # relative_path is corpus-rooted ("CORE.../foo.md"). Prefer the
        # repo-rooted source_path so we don't have to know the corpus root.
        sp = d.get("source_path")
        if sp:
            disk_path = repo_root / sp
            if disk_path.exists():
                # PDFs / binary assets are admitted to the corpus but have
                # no readable text; treat as empty body (sink computes
                # content_hash on empty string).
                ext = disk_path.suffix.lower()
                if ext in {".md", ".txt", ".html", ".htm"}:
                    try:
                        md = disk_path.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        md = ""
                        missing_md += 1
                else:
                    binary_assets += 1
            else:
                missing_md += 1
        out.append({**d, "markdown": md})
    if missing_md:
        print(f"  [warn] {missing_md} text corpus files had no readable markdown on disk.")
    if binary_assets:
        print(f"  [info] {binary_assets} binary-asset docs (pdf/etc) — markdown=''")
    return out


# ---------------------------------------------------------------------------
# Falkor track
# ---------------------------------------------------------------------------


def _emit_norm_id_summary_pre_load(articles: list[ParsedArticle]) -> dict[str, int]:
    """Re-emit the same binding_summary event the loader emits during build_article_nodes.

    Keeps heartbeat + observability parity with the full ingest path.
    """
    from lia_graph import norm_id_rules as R

    by_rule: dict[str, int] = {}
    eligible = 0
    stamped = 0
    for a in articles:
        out = R.derive_norm_id(
            article_id=a.article_key,
            article_number=a.article_number,
            source_path=a.source_path or "",
        )
        by_rule[out.rule_name] = by_rule.get(out.rule_name, 0) + 1
        if out.rule_name == "prose_only":
            continue
        eligible += 1
        if out.norm_id:
            stamped += 1
    emit_event(
        "ingest.norm_id.binding_summary",
        {
            "phase": "replay.derive_norm_id_preview",
            "eligible_count": eligible + by_rule.get("prose_only", 0),
            "stamped_count": stamped,
            "by_rule": by_rule,
        },
    )
    return by_rule


def build_article_topics_and_subtopics(
    *,
    articles: list[ParsedArticle],
    docs: list[dict[str, Any]],
) -> tuple[dict[str, str], dict[str, Any]]:
    topic_by_source_path: dict[str, str] = {}
    for d in docs:
        sp = d.get("source_path")
        tk = d.get("topic_key")
        if sp and tk:
            topic_by_source_path[str(sp)] = str(tk)
    article_topics: dict[str, str] = {}
    for a in articles:
        sp = str(a.source_path or "")
        if sp in topic_by_source_path:
            article_topics[_graph_article_key(a)] = topic_by_source_path[sp]

    # build_article_subtopic_bindings expects CorpusDocument-shaped objects;
    # we duck-type with SimpleNamespace exposing source_path, topic_key,
    # subtopic_key (those are the only attributes accessed in the function).
    duck_docs = [
        SimpleNamespace(
            source_path=d.get("source_path"),
            topic_key=d.get("topic_key"),
            subtopic_key=d.get("subtopic_key"),
        )
        for d in docs
    ]
    article_subtopics = build_article_subtopic_bindings(
        classified_documents=duck_docs,
        articles=articles,
    )
    return article_topics, article_subtopics


def run_falkor_track(
    *,
    articles: list[ParsedArticle],
    edges: list[ClassifiedEdge],
    article_topics: dict[str, str],
    article_subtopics: dict[str, Any],
    falkor_client: GraphClient,
    execute: bool,
    strict: bool,
) -> dict[str, Any]:
    plan = build_graph_load_plan(
        articles,
        edges,
        graph_client=falkor_client,
        article_topics=article_topics,
        article_subtopics=article_subtopics,
    )
    print(
        f"  [plan] nodes={len(plan.nodes)} edges={len(plan.edges)} "
        f"statements={len(plan.statements)} warnings={len(plan.warnings)}"
    )
    for w in plan.warnings:
        print(f"    warn: {w}")

    if not execute:
        print("  [dry-run] not executing Falkor load.")
        return {"executed": False, "node_count": len(plan.nodes), "edge_count": len(plan.edges)}

    model = load_graph_plan(
        plan,
        graph_client=falkor_client,
        execute=True,
        strict=strict,
    )
    d = model.to_dict()
    print(
        f"  [exec] statements={d['statement_count']} ok={d['success_count']} "
        f"failed={d['failure_count']} skipped={d['skipped_count']}"
    )
    return d


# ---------------------------------------------------------------------------
# Supabase track
# ---------------------------------------------------------------------------


def run_supabase_track(
    *,
    articles: list[ParsedArticle],
    edges: list[ClassifiedEdge],
    docs: list[dict[str, Any]],
    target: str,
    generation_id: str,
    activate: bool,
    worker_count: int,
    execute: bool,
) -> dict[str, Any] | None:
    if not execute:
        print("  [dry-run] not writing Supabase.")
        return None
    sink = SupabaseCorpusSink(
        target=target,
        generation_id=generation_id,
        worker_count=worker_count,
    )

    # knowledge_class counts (matches materialize_graph_artifacts behavior)
    kc_counts: dict[str, int] = {}
    for d in docs:
        kc = str(d.get("knowledge_class") or "unknown")
        kc_counts[kc] = kc_counts.get(kc, 0) + 1

    sink.write_generation(
        documents=len(docs),
        chunks=len(articles),
        countries=("colombia",),
        files=[str(d.get("relative_path") or "") for d in docs if d.get("relative_path")],
        knowledge_class_counts=kc_counts,
        index_dir="artifacts/v20/local_rehearsal_iter2",
    )
    doc_id_by_source_path, documents_written = sink.write_documents(docs)
    print(f"  [supabase] documents={documents_written} doc_id_map_size={len(doc_id_by_source_path)}")
    chunks_written = sink.write_chunks(articles, doc_id_by_source_path=doc_id_by_source_path)
    print(f"  [supabase] chunks={chunks_written}")
    edges_written = sink.write_normative_edges(edges)
    print(f"  [supabase] normative_edges={edges_written}")
    result = sink.finalize(activate=activate)
    print(f"  [supabase] finalize: activate={activate} -> {result.to_dict()}")
    return result.to_dict() | {
        "documents_written": int(documents_written),
        "chunks_written": int(chunks_written),
        "edges_written": int(edges_written),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Replay verified local v20 P1 artifacts to Supabase + Falkor "
            "(local or cloud). v20 P2 entrypoint."
        )
    )
    p.add_argument(
        "--artifacts-dir",
        type=Path,
        default=DEFAULT_ARTIFACTS_DIR,
        help=f"Frozen iter2 bundle directory (default: {DEFAULT_ARTIFACTS_DIR})",
    )
    p.add_argument(
        "--target-falkor",
        choices=("local", "cloud", "skip"),
        default="local",
        help="Falkor target: local docker (default), cloud staging, or skip.",
    )
    p.add_argument(
        "--target-supabase",
        choices=("production", "wip", "skip"),
        default="skip",
        help=(
            "Supabase target (passes through to SupabaseCorpusSink). Default skip "
            "— flip to `wip` for a non-production cloud target, `production` for the real cloud."
        ),
    )
    p.add_argument(
        "--generation-id",
        default="gen_active_rolling",
        help="Supabase generation_id tag.",
    )
    p.add_argument(
        "--activate",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="If true, finalize() activates the generation.",
    )
    p.add_argument(
        "--strict",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Strict Falkor mode (default true).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Load + verify + emit summaries; no Falkor writes, no Supabase writes.",
    )
    p.add_argument(
        "--doc-filter",
        default=None,
        help="Preflight: restrict to a single relative_path (one-doc end-to-end).",
    )
    p.add_argument(
        "--supabase-workers",
        type=int,
        default=4,
        help="Parallel batch workers for Supabase upserts.",
    )
    p.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write a JSON summary to this path (default: <artifacts-dir>/replay_report.json).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    bundle = args.artifacts_dir.resolve()
    if not bundle.exists():
        print(f"[fatal] artifacts dir not found: {bundle}", file=sys.stderr)
        return 1
    print(f"[v20-replay] bundle = {bundle}")
    print(f"[v20-replay] falkor target = {args.target_falkor}, "
          f"supabase target = {args.target_supabase}, dry-run = {args.dry_run}, "
          f"doc-filter = {args.doc_filter}")

    print("[v20-replay] phase 1 — verify sha256")
    _verify_sha256sums(bundle)

    print("[v20-replay] phase 2 — load articles + edges + corpus docs")
    articles = load_articles(bundle / "parsed_articles.jsonl")
    edges = load_edges(bundle / "typed_edges.jsonl")
    docs = load_corpus_documents(bundle / "canonical_corpus_manifest.json", repo_root=REPO_ROOT)
    print(f"  loaded: articles={len(articles)} edges={len(edges)} docs={len(docs)}")

    if args.doc_filter:
        before = (len(articles), len(edges), len(docs))
        rel = args.doc_filter.strip()
        # Resolve relative_path → source_path for filtering
        src_paths = {
            d["source_path"] for d in docs
            if str(d.get("relative_path") or "") == rel or str(d.get("source_path") or "").endswith(rel)
        }
        if not src_paths:
            print(f"[fatal] --doc-filter '{rel}' matched no documents in manifest.", file=sys.stderr)
            return 2
        articles = [a for a in articles if str(a.source_path or "") in src_paths]
        edges = [e for e in edges if e.record.source_kind != NodeKind.ARTICLE or True]  # keep all edges; filter conservatively
        docs = [d for d in docs if d["source_path"] in src_paths]
        print(f"  doc-filter applied: articles {before[0]} -> {len(articles)}, "
              f"edges {before[1]} -> {len(edges)} (kept), docs {before[2]} -> {len(docs)}")

    print("[v20-replay] phase 3 — derive_norm_id preview")
    by_rule = _emit_norm_id_summary_pre_load(articles)
    print(f"  by_rule top 6: {dict(sorted(by_rule.items(), key=lambda x: -x[1])[:6])}")

    print("[v20-replay] phase 4 — build article_topics + article_subtopics")
    article_topics, article_subtopics = build_article_topics_and_subtopics(
        articles=articles, docs=docs
    )
    print(f"  article_topics={len(article_topics)} article_subtopics={len(article_subtopics)}")

    print("[v20-replay] phase 5 — Falkor track")
    falkor_report: dict[str, Any] | None = None
    if args.target_falkor == "skip":
        print("  [skip] Falkor track disabled.")
    else:
        if args.target_falkor == "local":
            os.environ.setdefault("FALKORDB_URL", "redis://127.0.0.1:6389")
        elif args.target_falkor == "cloud":
            os.environ.setdefault("LIA_ENV", "staging")
        falkor_client = GraphClient.from_env()
        falkor_report = run_falkor_track(
            articles=articles,
            edges=edges,
            article_topics=article_topics,
            article_subtopics=article_subtopics,
            falkor_client=falkor_client,
            execute=not args.dry_run,
            strict=bool(args.strict),
        )

    print("[v20-replay] phase 6 — Supabase track")
    supabase_report: dict[str, Any] | None = None
    if args.target_supabase == "skip":
        print("  [skip] Supabase track disabled.")
    else:
        supabase_report = run_supabase_track(
            articles=articles,
            edges=edges,
            docs=docs,
            target=args.target_supabase,
            generation_id=str(args.generation_id),
            activate=bool(args.activate),
            worker_count=int(args.supabase_workers),
            execute=not args.dry_run,
        )

    summary = {
        "bundle": str(bundle),
        "doc_filter": args.doc_filter,
        "dry_run": bool(args.dry_run),
        "target_falkor": args.target_falkor,
        "target_supabase": args.target_supabase,
        "counts": {
            "articles": len(articles),
            "edges": len(edges),
            "docs": len(docs),
            "article_topics": len(article_topics),
            "article_subtopics": len(article_subtopics),
        },
        "norm_id_by_rule": by_rule,
        "falkor": falkor_report,
        "supabase": supabase_report,
    }
    report_path = args.report or (bundle.parent / f"replay_report_{int(time.time())}.json")
    try:
        report_path.write_text(json.dumps(summary, indent=2, default=str))
        print(f"[v20-replay] summary written -> {report_path}")
    except Exception as e:  # noqa: BLE001
        print(f"[v20-replay] WARNING — could not write report: {e}")

    print("[v20-replay] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
