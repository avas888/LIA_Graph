#!/usr/bin/env python
"""Backfill ``documents.doc_fingerprint`` from persisted classifier columns.

Phase 1 of ``docs/next/additive_corpusv1.md``. Idempotent, pure SQL against
Supabase via PostgREST — no markdown re-read, no classifier re-run.

**Decision K1 (reviewer-ratified 2026-04-22).** The fingerprint formula used
at ingest time (see ``src/lia_graph/ingestion/fingerprint.py``) consumes the
classifier output in its rich in-memory shape, which includes a ``source_tier``
field that is **not** persisted to the ``documents`` table. Rather than
widening the schema (K2) or re-running the classifier over the whole corpus
(K3), we drop ``source_tier`` from the fingerprint field set and reconstruct
``document_archetype`` / ``authority_level`` from the persisted
``tipo_de_documento`` / ``authority`` columns. The ingest path's
``compute_doc_fingerprint`` uses the same shape (see fingerprint.py's
``CLASSIFIER_FINGERPRINT_FIELDS``), which is what lets a full rebuild after
this backfill NOT mark every row ``modified`` spuriously. Test
``test_fingerprint.py`` case (f) asserts this equivalence.

Usage::

    # Preview counts without writing:
    PYTHONPATH=src:. uv run --group dev python scripts/backfill_doc_fingerprint.py \\
        --target production --dry-run

    # Commit fingerprints for the active generation:
    PYTHONPATH=src:. uv run --group dev python scripts/backfill_doc_fingerprint.py \\
        --target production --commit

Exit codes:
    0   success
    1   runtime error
    2   argparse error (handled by argparse)

Trace events:
    ingest.backfill.start
    ingest.backfill.batch.written
    ingest.backfill.done
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
for _candidate in (_SRC_DIR, _REPO_ROOT):
    _candidate_str = str(_candidate)
    if _candidate.is_dir() and _candidate_str not in sys.path:
        sys.path.insert(0, _candidate_str)

from lia_graph.env_loader import load_dotenv_if_present  # noqa: E402
from lia_graph.instrumentation import emit_event  # noqa: E402
from lia_graph.ingestion.fingerprint import (  # noqa: E402
    compute_doc_fingerprint,
    classifier_output_from_document_row,
)


DEFAULT_BATCH_SIZE = 200


@dataclass
class BackfillOptions:
    target: str
    dry_run: bool
    batch_size: int
    limit: int | None
    generation_id: str | None


@dataclass
class BackfillResult:
    target: str
    rows_scanned: int
    rows_written: int
    elapsed_ms: int


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backfill_doc_fingerprint",
        description=(
            "Compute documents.doc_fingerprint for every row where it is NULL. "
            "Uses the persisted classifier-shape columns only (no markdown read)."
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan the backfill (read-only). Prints the count and exits.",
    )
    group.add_argument(
        "--commit",
        action="store_true",
        help="Execute the backfill (writes documents.doc_fingerprint).",
    )
    parser.add_argument(
        "--target",
        type=str,
        default="production",
        help="Supabase target name passed to create_supabase_client_for_target().",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Rows per upsert batch (default: {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after processing N rows (default: no limit).",
    )
    parser.add_argument(
        "--generation-id",
        type=str,
        default=None,
        help="Restrict backfill to a specific sync_generation (default: all).",
    )
    return parser


def _parse_options(argv: list[str] | None = None) -> BackfillOptions:
    parser = _build_argparser()
    args = parser.parse_args(argv)
    return BackfillOptions(
        target=str(args.target or "production"),
        dry_run=bool(args.dry_run and not args.commit),
        batch_size=max(1, int(args.batch_size or DEFAULT_BATCH_SIZE)),
        limit=int(args.limit) if args.limit is not None else None,
        generation_id=args.generation_id,
    )


# Field projection — mirrors the persisted surface, not the in-memory classifier
# object. Aligns with Decision K1.
_PROJECTION = (
    "doc_id, sync_generation, content_hash, topic, tema, subtema, authority, "
    "tipo_de_documento, source_type, knowledge_class, requires_subtopic_review, "
    "doc_fingerprint"
)


def _iter_rows_to_backfill(
    client: Any,
    *,
    generation_id: str | None,
    batch_size: int,
    limit: int | None,
    dry_run: bool = False,
) -> Iterable[list[dict[str, Any]]]:
    """Yield batches of documents rows needing a fingerprint.

    Always queries ``range(0, batch_size - 1)`` because each batch gets
    WRITTEN (populates ``doc_fingerprint``) before the next iteration —
    so the ``doc_fingerprint IS NULL`` filter naturally "advances" the
    result window without needing a manual offset. Incrementing offset
    would skip rows on the next SELECT (classic read-while-write bug).
    Dry-run mode sets ``write_batch=noop`` externally, so we guard the
    iteration with a max-iterations safety net to avoid an infinite loop.
    """
    fetched_total = 0
    max_iterations = 10_000  # safety net; 10k batches × 200 rows = 2M docs
    iterations = 0
    while iterations < max_iterations:
        iterations += 1
        query = client.table("documents").select(_PROJECTION).is_("doc_fingerprint", "null")
        if generation_id:
            query = query.eq("sync_generation", generation_id)
        remaining = None if limit is None else max(0, limit - fetched_total)
        if remaining == 0:
            return
        take = batch_size if remaining is None else min(batch_size, remaining)
        resp = query.order("doc_id").range(0, take - 1).execute()
        rows = list(getattr(resp, "data", None) or [])
        if not rows:
            return
        yield rows
        fetched_total += len(rows)
        if len(rows) < take:
            return
        if dry_run:
            # Dry-run doesn't persist fingerprints, so the NULL filter
            # keeps returning the same rows — stop after one batch to
            # report the count without looping.
            return


def _compute_batch_fingerprints(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return upsert payloads for every row with a usable content_hash."""
    payloads: list[dict[str, Any]] = []
    for row in rows:
        doc_id = str(row.get("doc_id") or "").strip()
        content_hash = str(row.get("content_hash") or "").strip()
        if not doc_id or not content_hash:
            # Skip: fingerprint needs a content_hash; rows missing one are
            # upstream bugs that a backfill can't paper over.
            continue
        classifier_output = classifier_output_from_document_row(row)
        fingerprint = compute_doc_fingerprint(
            content_hash=content_hash,
            classifier_output=classifier_output,
        )
        payloads.append({"doc_id": doc_id, "doc_fingerprint": fingerprint})
    return payloads


def _write_batch(client: Any, payloads: list[dict[str, Any]]) -> int:
    if not payloads:
        return 0
    # PATCH (UPDATE) per row instead of upsert — Supabase PostgREST's
    # upsert path tries an INSERT first and hits NOT NULL constraints on
    # columns we didn't include in the payload (relative_path, etc.).
    # One UPDATE per row is fine: the backfill is a one-time operation
    # over ~1.3k rows, still completes in seconds.
    written = 0
    for payload in payloads:
        doc_id = payload.get("doc_id")
        if not doc_id:
            continue
        update_body = {k: v for k, v in payload.items() if k != "doc_id"}
        client.table("documents").update(update_body).eq("doc_id", doc_id).execute()
        written += 1
    return written


def run_backfill(
    options: BackfillOptions,
    *,
    client: Any | None = None,
) -> BackfillResult:
    if client is None:
        from lia_graph.supabase_client import create_supabase_client_for_target

        client = create_supabase_client_for_target(options.target)

    emit_event(
        "ingest.backfill.start",
        {
            "target": options.target,
            "dry_run": options.dry_run,
            "generation_id": options.generation_id,
            "batch_size": options.batch_size,
            "limit": options.limit,
        },
    )
    t0 = time.monotonic()
    rows_scanned = 0
    rows_written = 0
    batch_index = 0
    for batch in _iter_rows_to_backfill(
        client,
        generation_id=options.generation_id,
        batch_size=options.batch_size,
        limit=options.limit,
        dry_run=options.dry_run,
    ):
        rows_scanned += len(batch)
        payloads = _compute_batch_fingerprints(batch)
        if options.dry_run:
            continue
        written = _write_batch(client, payloads)
        rows_written += written
        batch_index += 1
        emit_event(
            "ingest.backfill.batch.written",
            {
                "target": options.target,
                "batch_index": batch_index,
                "rows_written": written,
                "elapsed_ms": int((time.monotonic() - t0) * 1000),
            },
        )

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    emit_event(
        "ingest.backfill.done",
        {
            "target": options.target,
            "total_rows_scanned": rows_scanned,
            "total_rows_written": rows_written,
            "total_elapsed_ms": elapsed_ms,
            "dry_run": options.dry_run,
        },
    )
    return BackfillResult(
        target=options.target,
        rows_scanned=rows_scanned,
        rows_written=rows_written,
        elapsed_ms=elapsed_ms,
    )


def main(argv: list[str] | None = None) -> int:
    try:
        load_dotenv_if_present()
    except Exception:  # noqa: BLE001
        # env loading is best-effort — tests inject clients directly.
        pass
    options = _parse_options(argv)
    try:
        result = run_backfill(options)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"backfill failed: {exc}\n")
        return 1
    mode = "dry-run" if options.dry_run else "commit"
    sys.stdout.write(
        f"[{mode}] target={result.target} scanned={result.rows_scanned} "
        f"written={result.rows_written} elapsed_ms={result.elapsed_ms}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
