#!/usr/bin/env python
"""Maintenance-only backfill of ``documents.subtema`` via PASO 4.

After ingestfix-v2-maximalist (``docs/next/ingestfixv2.md``, Phase A4+A5)
the normal single-pass ingest runs PASO 4 inline and populates subtema +
emits Falkor SubTopic structure in one shot. This script is kept around
as a **maintenance utility** for two cases:

1. Re-classify docs that were flagged ``requires_subtopic_review=True``
   during the live ingest pass (LLM returned a low-confidence verdict).
2. Re-classify every doc after a curated-taxonomy version bump.

Default filter: ``WHERE requires_subtopic_review = true OR subtema IS NULL``.
Pass ``--only-requires-review`` to narrow to (1). Pass ``--refresh-existing``
to include rows that already have a subtema.

Beyond the Supabase write, the script now also emits ``SubTopicNode`` +
``HAS_SUBTOPIC`` edges to FalkorDB (MERGE, idempotent) for every doc it
updates, matching what the single-pass ingest emits.

Usage::

    python scripts/backfill_subtopic.py --dry-run --limit 5
    python scripts/backfill_subtopic.py --commit --only-requires-review
    python scripts/backfill_subtopic.py --commit --refresh-existing

Exit codes:
    0   success
    1   classifier / sync error
    2   argparse error (handled by argparse itself)
    4   env posture guard failed (see --allow-non-local-env)

Trace events:
    subtopic.backfill.start
    subtopic.backfill.doc.processed
    subtopic.backfill.doc.failed
    subtopic.backfill.done
    subtopic.graph.binding_built  (per Falkor emission)
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
for _candidate in (_SRC_DIR, _REPO_ROOT):
    _candidate_str = str(_candidate)
    if _candidate.is_dir() and _candidate_str not in sys.path:
        sys.path.insert(0, _candidate_str)

from lia_graph.env_loader import load_dotenv_if_present  # noqa: E402
from lia_graph.instrumentation import emit_event  # noqa: E402


@dataclass
class BackfillOptions:
    dry_run: bool
    limit: int | None
    only_topic: str | None
    rate_limit_rpm: int
    generation_id: str | None
    resume_from: str | None
    refresh_existing: bool
    only_requires_review: bool = False
    emit_falkor: bool = True


@dataclass
class BackfillResult:
    docs_processed: int
    docs_updated: int
    docs_failed: int
    elapsed_s: float


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backfill_subtopic",
        description=(
            "Re-classify documents in the active corpus generation to "
            "populate documents.subtema via the classifier PASO 4 verdict."
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan the backfill (read-only). Emits counts and exits.",
    )
    group.add_argument(
        "--commit",
        action="store_true",
        help="Execute the backfill — writes to documents/document_chunks.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after processing N documents (default: no limit).",
    )
    parser.add_argument(
        "--only-topic",
        type=str,
        default=None,
        help="Restrict backfill to docs whose topic matches SLUG.",
    )
    parser.add_argument(
        "--rate-limit-rpm",
        type=int,
        default=60,
        help="Upper bound on classifier calls per minute (default: 60).",
    )
    parser.add_argument(
        "--generation-id",
        type=str,
        default=None,
        help="Target generation_id (default: active generation).",
    )
    parser.add_argument(
        "--resume-from",
        type=str,
        default=None,
        help="Skip documents whose doc_id is lexicographically <= this value.",
    )
    parser.add_argument(
        "--refresh-existing",
        action="store_true",
        help="Re-classify rows that already have a subtema (default: skip them).",
    )
    parser.add_argument(
        "--only-requires-review",
        action="store_true",
        help=(
            "Narrow the filter to docs flagged requires_subtopic_review=true "
            "during the live ingest pass. Default is "
            "`requires_subtopic_review=true OR subtema IS NULL`."
        ),
    )
    parser.add_argument(
        "--no-falkor-emit",
        dest="emit_falkor",
        action="store_false",
        help=(
            "Skip emitting SubTopicNode + HAS_SUBTOPIC edges to FalkorDB. "
            "Default is to emit (matching single-pass ingest behavior)."
        ),
    )
    parser.set_defaults(emit_falkor=True)
    parser.add_argument(
        "--allow-non-local-env",
        action="store_true",
        help=(
            "Skip the local-env posture guard. Required when intentionally "
            "running against cloud Supabase."
        ),
    )
    return parser


def _resolve_active_generation_id(client: Any) -> str | None:
    try:
        resp = (
            client.table("corpus_generations")
            .select("generation_id")
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
    except Exception:  # noqa: BLE001
        return None
    rows = list(getattr(resp, "data", None) or [])
    if not rows:
        return None
    return str(rows[0].get("generation_id") or "") or None


def _fetch_documents(
    client: Any,
    *,
    generation_id: str,
    only_topic: str | None,
    refresh_existing: bool,
    limit: int | None,
    resume_from: str | None,
    only_requires_review: bool = False,
) -> list[dict[str, Any]]:
    query = client.table("documents").select(
        "doc_id, topic, tema, subtema, relative_path, content_hash, requires_subtopic_review"
    ).eq("sync_generation", generation_id)
    if only_topic:
        query = query.eq("topic", only_topic)
    if only_requires_review:
        # Narrow: only docs flagged for review
        query = query.eq("requires_subtopic_review", True)
    elif not refresh_existing:
        # Maintenance default: docs flagged for review OR missing subtema
        query = query.or_(
            "requires_subtopic_review.eq.true,subtema.is.null"
        )
    if resume_from:
        query = query.gt("doc_id", resume_from)
    query = query.order("doc_id")
    if limit is not None:
        query = query.limit(int(limit))
    resp = query.execute()
    return list(getattr(resp, "data", None) or [])


def _load_markdown(client: Any, doc_id: str) -> str:
    """Best-effort markdown lookup: chunks.chunk_text for the first chunk.

    The backfill re-classification only needs the first ~2 KB of body,
    which matches the classifier's own ``_BODY_PREVIEW_CHARS`` clip.
    """
    try:
        resp = (
            client.table("document_chunks")
            .select("chunk_text")
            .eq("doc_id", doc_id)
            .order("chunk_id")
            .limit(1)
            .execute()
        )
    except Exception:  # noqa: BLE001
        return ""
    rows = list(getattr(resp, "data", None) or [])
    if not rows:
        return ""
    return str(rows[0].get("chunk_text") or "")


def _apply_rate_limit(rpm: int, last_tick: float | None) -> float:
    if rpm <= 0:
        return time.monotonic()
    min_gap = 60.0 / max(rpm, 1)
    now = time.monotonic()
    if last_tick is None:
        return now
    delta = now - last_tick
    if delta < min_gap:
        time.sleep(min_gap - delta)
        return time.monotonic()
    return now


def _update_subtopic(
    client: Any,
    *,
    doc_id: str,
    subtopic_key: str | None,
    requires_review: bool,
) -> None:
    payload: dict[str, Any] = {
        "subtema": subtopic_key,
        "requires_subtopic_review": requires_review,
    }
    client.table("documents").update(payload).eq("doc_id", doc_id).execute()
    client.table("document_chunks").update({"subtema": subtopic_key}).eq(
        "doc_id", doc_id
    ).execute()


def _emit_falkor_subtopic(
    *,
    graph_client: Any,
    article_key: str,
    sub_topic_key: str,
    parent_topic: str,
    label: str,
) -> None:
    """MERGE a SubTopicNode + HAS_SUBTOPIC edge. Idempotent."""
    from lia_graph.graph.client import GraphWriteStatement

    node_stmt = GraphWriteStatement(
        description="backfill.subtopic_node.merge",
        query=(
            "MERGE (s:SubTopicNode { sub_topic_key: $sub_topic_key }) "
            "SET s.parent_topic = $parent_topic, s.label = $label "
            "RETURN s.sub_topic_key AS sub_topic_key"
        ),
        parameters={
            "sub_topic_key": sub_topic_key,
            "parent_topic": parent_topic,
            "label": label,
        },
    )
    edge_stmt = GraphWriteStatement(
        description="backfill.subtopic_edge.merge",
        query=(
            # ArticleNode stores its identity under `article_id` per
            # default_graph_schema() — NOT `article_key` (the Python
            # attribute on ParsedArticle). See
            # tests/test_graph_node_key_contract.py for the contract.
            "MATCH (a:ArticleNode { article_id: $article_key }) "
            "MATCH (s:SubTopicNode { sub_topic_key: $sub_topic_key }) "
            "MERGE (a)-[r:HAS_SUBTOPIC]->(s) "
            "RETURN type(r) AS kind"
        ),
        parameters={
            "article_key": article_key,
            "sub_topic_key": sub_topic_key,
        },
    )
    graph_client.execute(node_stmt, strict=True)
    graph_client.execute(edge_stmt, strict=True)
    emit_event(
        "subtopic.graph.binding_built",
        {
            "article_key": article_key,
            "sub_topic_key": sub_topic_key,
            "parent_topic": parent_topic,
        },
    )


def run(
    options: BackfillOptions,
    *,
    client: Any | None = None,
    classifier: Callable[..., Any] | None = None,
    graph_client: Any | None = None,
) -> BackfillResult:
    """Execute a backfill pass.

    ``client`` / ``classifier`` / ``graph_client`` are injection points for
    unit tests. Production callers should leave them None to pick up the
    cloud Supabase + real classifier + env-configured FalkorDB client.
    """
    start = time.monotonic()
    if client is None:
        from lia_graph.supabase_client import get_supabase_client

        client = get_supabase_client()
        if client is None:
            raise RuntimeError(
                "backfill_subtopic: Supabase client unavailable — "
                "run with LIA_STORAGE_BACKEND=supabase."
            )

    if classifier is None:
        from lia_graph.ingestion_classifier import classify_ingestion_document

        classifier = classify_ingestion_document

    # Falkor client is optional — if emit_falkor is off, skip entirely.
    _graph_client = graph_client
    if options.emit_falkor and _graph_client is None and not options.dry_run:
        try:
            from lia_graph.graph import GraphClient

            _graph_client = GraphClient.from_env()
        except Exception as exc:  # noqa: BLE001
            emit_event(
                "subtopic.backfill.falkor_unavailable",
                {"error": str(exc)[:200]},
            )
            _graph_client = None

    generation_id = options.generation_id or _resolve_active_generation_id(client)
    if not generation_id:
        raise RuntimeError(
            "backfill_subtopic: could not resolve active generation_id; "
            "pass --generation-id explicitly."
        )

    emit_event(
        "subtopic.backfill.start",
        {
            "generation_id": generation_id,
            "dry_run": options.dry_run,
            "limit": options.limit,
            "only_topic": options.only_topic,
            "refresh_existing": options.refresh_existing,
            "only_requires_review": options.only_requires_review,
            "emit_falkor": options.emit_falkor,
        },
    )

    docs = _fetch_documents(
        client,
        generation_id=generation_id,
        only_topic=options.only_topic,
        refresh_existing=options.refresh_existing,
        limit=options.limit,
        resume_from=options.resume_from,
        only_requires_review=options.only_requires_review,
    )
    # Taxonomy is needed once per run for topic→label resolution.
    taxonomy = None
    if options.emit_falkor and _graph_client is not None:
        from lia_graph.subtopic_taxonomy_loader import load_taxonomy

        taxonomy = load_taxonomy()

    updated = 0
    failed = 0
    last_tick: float | None = None
    for doc in docs:
        doc_id = str(doc.get("doc_id") or "").strip()
        if not doc_id:
            continue
        try:
            last_tick = _apply_rate_limit(options.rate_limit_rpm, last_tick)
            body = _load_markdown(client, doc_id)
            filename = str(doc.get("relative_path") or doc_id)
            result = classifier(filename=filename, body_text=body)
            subtopic_key = getattr(result, "subtopic_key", None)
            requires_review = bool(
                getattr(result, "requires_subtopic_review", False)
            )
            was_null_before = not doc.get("subtema")
            if not options.dry_run:
                _update_subtopic(
                    client,
                    doc_id=doc_id,
                    subtopic_key=subtopic_key,
                    requires_review=requires_review,
                )
                # Emit Falkor SubTopicNode + HAS_SUBTOPIC when the key
                # resolves in the curated taxonomy.
                if (
                    subtopic_key
                    and not requires_review
                    and _graph_client is not None
                    and taxonomy is not None
                ):
                    parent_topic = getattr(result, "detected_topic", None) or doc.get(
                        "topic"
                    )
                    entry = getattr(taxonomy, "lookup_by_key", {}).get(
                        (parent_topic, subtopic_key)
                    )
                    if entry is not None and parent_topic:
                        try:
                            _emit_falkor_subtopic(
                                graph_client=_graph_client,
                                article_key=doc_id,
                                sub_topic_key=subtopic_key,
                                parent_topic=parent_topic,
                                label=getattr(entry, "label", subtopic_key),
                            )
                        except Exception as exc:  # noqa: BLE001
                            emit_event(
                                "subtopic.backfill.falkor_emit_failed",
                                {"doc_id": doc_id, "error": str(exc)[:200]},
                            )
            updated += 1 if subtopic_key or requires_review else 0
            emit_event(
                "subtopic.backfill.doc.processed",
                {
                    "doc_id": doc_id,
                    "topic": doc.get("topic"),
                    "subtopic_key": subtopic_key,
                    "subtopic_confidence": round(
                        float(getattr(result, "subtopic_confidence", 0.0) or 0.0),
                        4,
                    ),
                    "was_null_before": was_null_before,
                    "dry_run": options.dry_run,
                },
            )
        except Exception as exc:  # noqa: BLE001 — backfill tolerates per-doc failures
            failed += 1
            emit_event(
                "subtopic.backfill.doc.failed",
                {"doc_id": doc_id, "error": str(exc)[:200]},
            )
    elapsed = time.monotonic() - start
    emit_event(
        "subtopic.backfill.done",
        {
            "generation_id": generation_id,
            "docs_processed": len(docs),
            "docs_updated": updated,
            "docs_failed": failed,
            "elapsed_s": round(elapsed, 2),
            "dry_run": options.dry_run,
        },
    )
    return BackfillResult(
        docs_processed=len(docs),
        docs_updated=updated,
        docs_failed=failed,
        elapsed_s=elapsed,
    )


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv_if_present()
    parser = _build_argparser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not args.allow_non_local_env:
        from lia_graph.env_posture import EnvPostureError, assert_local_posture

        try:
            assert_local_posture(require_supabase=True, require_falkor=False)
        except EnvPostureError as exc:
            sys.stderr.write(f"backfill_subtopic: {exc}\n")
            return 4
    options = BackfillOptions(
        dry_run=bool(args.dry_run),
        limit=args.limit,
        only_topic=args.only_topic,
        rate_limit_rpm=int(args.rate_limit_rpm),
        generation_id=args.generation_id,
        resume_from=args.resume_from,
        refresh_existing=bool(args.refresh_existing),
        only_requires_review=bool(args.only_requires_review),
        emit_falkor=bool(args.emit_falkor),
    )
    try:
        result = run(options)
    except RuntimeError as exc:
        sys.stderr.write(f"backfill_subtopic: {exc}\n")
        return 1
    sys.stdout.write(
        f"backfill_subtopic: processed={result.docs_processed} "
        f"updated={result.docs_updated} failed={result.docs_failed} "
        f"elapsed={result.elapsed_s:.1f}s "
        f"(dry_run={options.dry_run})\n"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
