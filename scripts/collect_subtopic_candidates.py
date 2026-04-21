#!/usr/bin/env python
"""Phase 2 — corpus-wide sub-topic label collection pass.

Walks ``knowledge_base/**/*.md``, invokes
``lia_graph.ingestion_classifier.classify_ingestion_document`` with
``always_emit_label=True`` so the LLM populates ``generated_label`` on
every doc (not only on the low-confidence path), and writes one row per
doc to ``artifacts/subtopic_candidates/collection_<UTC>.jsonl``.

See ``docs/next/subtopic_generationv1.md`` §5 Phase 2 and
``docs/next/subtopic_generationv1-contracts.md`` for the authoritative
field schema. Exit codes: 0 success, 2 if commit mode saw any per-doc
classification failure. Trace events use the ``subtopic.collect.*``
namespace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

# Keep runnable both as ``python scripts/collect_subtopic_candidates.py``
# and as ``PYTHONPATH=src:. python scripts/collect_subtopic_candidates.py``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
for candidate in (_SRC_DIR, _REPO_ROOT):
    candidate_str = str(candidate)
    if candidate.is_dir() and candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from lia_graph.corpus_walk import (  # noqa: E402
    iter_corpus_files,
    parent_topic_from_relative,
    relative_path,
)
from lia_graph.ingestion_classifier import (  # noqa: E402
    AutogenerarResult,
    classify_ingestion_document,
)
from lia_graph.instrumentation import emit_event  # noqa: E402
from lia_graph.topic_guardrails import get_supported_topics  # noqa: E402

# Cached at module load: the canonical topic-key set we check the filesystem
# segment against. Classifier-derived fallback kicks in when the segment
# doesn't match one of these (e.g. `CORE ya Arriba` staging dir).
_SUPPORTED_TOPICS = frozenset(get_supported_topics())


def _utc_ts_slug() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _derive_doc_id(relative: str, content_hash: str) -> str:
    """Stable id per (relative_path, content_hash) pair; ``sha256:<hex[:32]>``."""
    key = f"{relative}:{content_hash}".encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()[:32]
    return f"sha256:{digest}"


def _load_resume_doc_ids(resume_from: Path | None) -> set[str]:
    """Return the set of ``doc_id`` present in an existing collection JSONL."""
    if resume_from is None or not resume_from.is_file():
        return set()
    seen: set[str] = set()
    with resume_from.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            doc_id = row.get("doc_id")
            if isinstance(doc_id, str) and doc_id:
                seen.add(doc_id)
    return seen


def _build_row_dict(
    *,
    batch_id: str,
    rel_path: str,
    parent_topic: str | None,
    filename: str,
    content_hash: str,
    doc_id: str,
    result: AutogenerarResult,
) -> dict[str, Any]:
    """Materialize a single collection row as the contract-defined dict."""
    llm_used = result.generated_label is not None or result.rationale is not None
    return {
        "collection_batch_id": batch_id,
        "collected_at": _utc_now_iso(),
        "corpus_relative_path": rel_path,
        "doc_id": doc_id,
        "filename": filename,
        "content_hash": content_hash,
        "parent_topic": parent_topic,
        "autogenerar_label": result.generated_label,
        "autogenerar_rationale": result.rationale,
        "detected_topic": result.detected_topic,
        "detected_type": result.detected_type,
        "topic_confidence": float(result.topic_confidence),
        "combined_confidence": float(result.combined_confidence),
        "classification_source": result.classification_source,
        "is_raw": bool(result.is_raw),
        "llm_used": bool(llm_used),
        "error": None,
    }


def _append_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_latest_pointer(
    artifacts_dir: Path,
    *,
    batch_id: str,
    collection_path: Path,
    collected_at: str,
    docs_processed: int,
    docs_failed: int,
    total_llm_calls: int,
) -> Path:
    pointer = artifacts_dir / "subtopic_candidates" / "_latest.json"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "collection_batch_id": batch_id,
        "collection_path": str(collection_path),
        "collected_at": collected_at,
        "docs_processed": docs_processed,
        "docs_failed": docs_failed,
        "total_llm_calls": total_llm_calls,
    }
    pointer.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return pointer


def _compute_rate_sleep_seconds(rate_limit_rpm: float) -> float:
    """Convert an rpm target into seconds-per-request; 0 disables throttling."""
    if rate_limit_rpm <= 0:
        return 0.0
    return 60.0 / float(rate_limit_rpm)


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collect_subtopic_candidates",
        description=(
            "Corpus-wide pass that records autogenerar_label for every doc "
            "into artifacts/subtopic_candidates/collection_<UTC>.jsonl."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", dest="dry_run", action="store_true", help="Default mode; no files written.")
    mode.add_argument("--commit", dest="commit", action="store_true", help="Write the collection JSONL + _latest.json pointer.")
    parser.add_argument("--limit", type=int, default=None, help="Stop after processing N docs.")
    parser.add_argument("--only-topic", type=str, default=None, help="Restrict the walk to knowledge_base/<SLUG>/...")
    parser.add_argument("--knowledge-base", type=str, default="knowledge_base", help="Path to the corpus root.")
    parser.add_argument("--batch-id", type=str, default=None, help="Override the generated batch id.")
    parser.add_argument("--resume-from", type=str, default=None, help="Existing collection JSONL; skip doc_ids already present.")
    parser.add_argument("--rate-limit-rpm", type=float, default=60.0, help="Target LLM requests per minute (default 60).")
    parser.add_argument("--artifacts-dir", type=str, default="artifacts", help="Directory for the JSONL + pointer.")
    parser.add_argument("--skip-llm", action="store_true", help="Force skip_llm=True on the classifier.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_argparser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    commit_mode = bool(args.commit and not args.dry_run)
    dry_run = not commit_mode

    knowledge_base = Path(args.knowledge_base).expanduser().resolve()
    artifacts_dir = Path(args.artifacts_dir).expanduser().resolve()
    resume_from = (
        Path(args.resume_from).expanduser().resolve()
        if args.resume_from
        else None
    )

    batch_id = args.batch_id or f"collection_{_utc_ts_slug()}"
    collection_path = (
        artifacts_dir / "subtopic_candidates" / f"{batch_id}.jsonl"
    ).resolve()

    all_paths = list(iter_corpus_files(knowledge_base, only_topic=args.only_topic))
    already_seen = _load_resume_doc_ids(resume_from)
    rate_sleep = _compute_rate_sleep_seconds(float(args.rate_limit_rpm))

    emit_event(
        "subtopic.collect.start",
        {
            "batch_id": batch_id,
            "corpus_root": str(knowledge_base),
            "dry_run": dry_run,
            "limit": args.limit,
            "only_topic": args.only_topic,
            "skip_llm": bool(args.skip_llm),
        },
    )

    started_at = time.time()
    docs_processed = 0
    docs_failed = 0
    total_llm_calls = 0
    # Counts docs that were actually classified (either success or failure)
    # this run — drives --limit and the "first call skips sleep" rule.
    processed_count_for_limit = 0

    for idx, path in enumerate(all_paths, start=1):
        if (
            args.limit is not None
            and args.limit >= 0
            and processed_count_for_limit >= args.limit
        ):
            break

        rel_path = relative_path(path, knowledge_base)
        parent_topic = parent_topic_from_relative(rel_path)
        filename = path.name

        try:
            raw_bytes = path.read_bytes()
        except OSError as exc:
            docs_failed += 1
            emit_event(
                "subtopic.collect.doc.failed",
                {
                    "batch_id": batch_id,
                    "doc_id": None,
                    "corpus_relative_path": rel_path,
                    "error": repr(exc),
                    "phase": "read",
                },
            )
            sys.stdout.write(
                f"[{idx}/{len(all_paths)}] {rel_path} -> READ ERROR "
                f"{type(exc).__name__}: {exc}\n"
            )
            sys.stdout.flush()
            continue

        content_hash = f"sha256:{hashlib.sha256(raw_bytes).hexdigest()}"
        doc_id = _derive_doc_id(rel_path, content_hash)

        # Resume: skip anything already in the checkpoint without counting
        # it against --limit.
        if doc_id in already_seen:
            continue

        # Rate-limit between calls (not before the first).
        if processed_count_for_limit > 0 and rate_sleep > 0:
            time.sleep(rate_sleep)

        body_text = raw_bytes.decode("utf-8", errors="replace")
        t0 = time.time()
        try:
            result = classify_ingestion_document(
                filename=filename,
                body_text=body_text,
                always_emit_label=True,
                skip_llm=bool(args.skip_llm),
            )
        except Exception as exc:  # noqa: BLE001 — keep walking on per-doc errors
            docs_failed += 1
            emit_event(
                "subtopic.collect.doc.failed",
                {
                    "batch_id": batch_id,
                    "doc_id": doc_id,
                    "corpus_relative_path": rel_path,
                    "error": repr(exc),
                    "phase": "classify",
                },
            )
            sys.stdout.write(
                f"[{idx}/{len(all_paths)}] {rel_path} -> CLASSIFY ERROR "
                f"{type(exc).__name__}: {exc}\n"
            )
            sys.stdout.flush()
            processed_count_for_limit += 1
            continue
        llm_latency_ms = int((time.time() - t0) * 1000)

        # Parent-topic resolution order:
        #   1. Filesystem segment IF it matches a canonical topic key (so
        #      a well-organized `knowledge_base/<topic>/...` tree wins).
        #   2. Classifier's `detected_topic` (canonical key from N1/N2).
        #   3. Filesystem segment as-is (for trees staged under non-topic
        #      container dirs, e.g. `knowledge_base/CORE ya Arriba/...`,
        #      the segment itself is preserved so diagnostics aren't
        #      silently blanked; mining will still see the real topic
        #      via the classifier path in step 2 when it fires).
        if parent_topic and parent_topic in _SUPPORTED_TOPICS:
            effective_parent_topic = parent_topic
        else:
            effective_parent_topic = result.detected_topic or parent_topic

        row = _build_row_dict(
            batch_id=batch_id,
            rel_path=rel_path,
            parent_topic=effective_parent_topic,
            filename=filename,
            content_hash=content_hash,
            doc_id=doc_id,
            result=result,
        )
        if row["llm_used"]:
            total_llm_calls += 1
        if commit_mode:
            _append_row(collection_path, row)

        docs_processed += 1
        processed_count_for_limit += 1

        emit_event(
            "subtopic.collect.doc.processed",
            {
                "batch_id": batch_id,
                "doc_id": doc_id,
                "parent_topic": effective_parent_topic,
                "generated_label": row["autogenerar_label"],
                "rationale_len": len(row["autogenerar_rationale"] or ""),
                "llm_latency_ms": llm_latency_ms,
            },
        )

        sys.stdout.write(
            f"[{idx}/{len(all_paths)}] {rel_path} -> "
            f"label={row['autogenerar_label']!r} parent={effective_parent_topic}\n"
        )
        sys.stdout.flush()

    collected_at = _utc_now_iso()
    pointer_path: Path | None = None
    if commit_mode:
        pointer_path = _write_latest_pointer(
            artifacts_dir,
            batch_id=batch_id,
            collection_path=collection_path,
            collected_at=collected_at,
            docs_processed=docs_processed,
            docs_failed=docs_failed,
            total_llm_calls=total_llm_calls,
        )

    elapsed_s = round(time.time() - started_at, 3)

    emit_event(
        "subtopic.collect.done",
        {
            "batch_id": batch_id,
            "docs_processed": docs_processed,
            "docs_failed": docs_failed,
            "total_llm_calls": total_llm_calls,
            "elapsed_s": elapsed_s,
            "output_path": str(collection_path) if commit_mode else None,
            "dry_run": dry_run,
        },
    )

    sys.stdout.write(
        f"\nsubtopic.collect: batch={batch_id} "
        f"docs_processed={docs_processed} docs_failed={docs_failed} "
        f"llm_calls={total_llm_calls} elapsed_s={elapsed_s} "
        f"mode={'commit' if commit_mode else 'dry_run'}\n"
    )
    if commit_mode:
        sys.stdout.write(f"output: {collection_path}\n")
        if pointer_path is not None:
            sys.stdout.write(f"latest: {pointer_path}\n")
    sys.stdout.flush()

    if commit_mode and docs_failed > 0:
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
