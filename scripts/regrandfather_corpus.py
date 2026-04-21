#!/usr/bin/env python
"""Phase 5c regrandfather pass — re-chunk existing corpus under canonical template.

Per ``docs/next/ingestfixv1.md`` Phase 5c: walks ``knowledge_base/**/*.md``,
runs the Phase 1.5 section coercer + Phase 1.6 chunker against each doc,
and (in ``--commit`` mode) rewrites the file under the canonical
8-section template. ``--dry-run`` reports coverage without touching the
filesystem.

Usage:

    python scripts/regrandfather_corpus.py --dry-run
    python scripts/regrandfather_corpus.py --commit --limit 10
    python scripts/regrandfather_corpus.py --dry-run --only-topic laboral --skip-llm

Exit codes:
    0   — success (all docs processed without exceptions)
    1   — argparse error (handled by argparse itself)
    2   — one or more docs raised an exception in ``--commit`` mode

Trace events:
    ingest.regrandfather.start
    ingest.regrandfather.doc.processed   (commit only)
    ingest.regrandfather.done
    ingest.regrandfather.failed          (per-doc exceptions)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

# Keep the script runnable both as ``python scripts/regrandfather_corpus.py``
# and as ``PYTHONPATH=src:. python scripts/regrandfather_corpus.py``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
for candidate in (_SRC_DIR, _REPO_ROOT):
    candidate_str = str(candidate)
    if candidate.is_dir() and candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from lia_graph.corpus_walk import (  # noqa: E402
    SKIP_DIR_NAMES as _SKIP_DIR_NAMES,
    SKIP_FILENAMES as _SKIP_FILENAMES,
    iter_corpus_files as _shared_iter_corpus_files,
    relative_path as _shared_relative_path,
)
from lia_graph.ingestion_chunker import (  # noqa: E402
    chunk_canonical_markdown,
    section_type_distribution,
)
from lia_graph.ingestion_section_coercer import (  # noqa: E402
    coerce_to_canonical_template,
)
from lia_graph.instrumentation import emit_event  # noqa: E402


@dataclass
class _DocReport:
    path: str
    coercion_method: str
    sections_matched_count: int
    chunk_count: int
    section_type_distribution: dict[str, int]
    confidence: float
    llm_used: bool
    mutated: bool = False


@dataclass
class _Aggregate:
    docs_processed: int = 0
    error_count: int = 0
    per_method: Counter = field(default_factory=Counter)
    per_section_type: Counter = field(default_factory=Counter)
    errors: list[dict[str, str]] = field(default_factory=list)
    reports: list[_DocReport] = field(default_factory=list)


def _utc_ts_slug() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _iter_corpus_files(
    knowledge_base: Path,
    *,
    only_topic: str | None,
) -> Iterable[Path]:
    """Walk ``knowledge_base`` yielding markdown files to process.

    Thin wrapper around :func:`lia_graph.corpus_walk.iter_corpus_files`
    so the regrandfather pass and the subtopic-collection pass stay in
    lock-step on filter rules (hidden dirs, ``__MACOSX``, sentinel
    filenames, ``.md`` gate).
    """
    yield from _shared_iter_corpus_files(knowledge_base, only_topic=only_topic)


def _relative_path(path: Path, root: Path) -> str:
    return _shared_relative_path(path, root)


def _process_one(
    path: Path,
    *,
    skip_llm: bool,
    coerce_fn,
    chunk_fn,
) -> tuple[_DocReport, str]:
    """Read, coerce, and chunk a single doc. Returns (report, coerced_markdown)."""
    original = path.read_text(encoding="utf-8")
    coerce_result = coerce_fn(
        original,
        skip_llm=skip_llm,
        filename=path.name,
    )
    chunks = chunk_fn(coerce_result.coerced_markdown, filename=path.name)
    distribution = section_type_distribution(chunks)
    report = _DocReport(
        path=str(path),
        coercion_method=coerce_result.coercion_method,
        sections_matched_count=coerce_result.sections_matched_count,
        chunk_count=len(chunks),
        section_type_distribution=distribution,
        confidence=float(coerce_result.confidence),
        llm_used=bool(coerce_result.llm_used),
    )
    return report, coerce_result.coerced_markdown


def _log_progress(
    index: int,
    total: int,
    rel_path: str,
    report: _DocReport,
    *,
    stream=sys.stdout,
) -> None:
    stream.write(
        f"[{index}/{total}] {rel_path} -> {report.coercion_method} "
        f"({report.sections_matched_count}/8, {report.chunk_count} chunks)\n"
    )
    stream.flush()


def _resolve_report_path(
    explicit: str | None,
    *,
    mode: str,
    artifacts_dir: Path,
) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    ts = _utc_ts_slug()
    return (artifacts_dir / f"regrandfather_{mode}_{ts}.json").resolve()


def _write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="regrandfather_corpus",
        description="One-time regrandfather pass: re-chunk corpus under the canonical 8-section template.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Do not mutate files; emit a coverage report only. Default mode.",
    )
    mode.add_argument(
        "--commit",
        dest="commit",
        action="store_true",
        help="Overwrite each markdown file with the coerced canonical output.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after processing N docs (useful for testing).",
    )
    parser.add_argument(
        "--only-topic",
        type=str,
        default=None,
        help="Restrict the walk to knowledge_base/<SLUG>/...",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Force heuristic-only coercion (no LLM calls).",
    )
    parser.add_argument(
        "--knowledge-base",
        type=str,
        default="knowledge_base",
        help="Path to the corpus root (default: ./knowledge_base).",
    )
    parser.add_argument(
        "--report-path",
        type=str,
        default=None,
        help="Where to write the JSON aggregate report. "
        "Default: artifacts/regrandfather_<mode>_<ts>.json",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=str,
        default="artifacts",
        help="Directory for the default report path (default: ./artifacts).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_argparser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    commit_mode = bool(args.commit and not args.dry_run)
    mode_label = "commit" if commit_mode else "dry_run"

    knowledge_base = Path(args.knowledge_base).expanduser().resolve()
    artifacts_dir = Path(args.artifacts_dir).expanduser().resolve()
    report_path = _resolve_report_path(
        args.report_path, mode=mode_label, artifacts_dir=artifacts_dir
    )

    # Discover files first so we know the total and can honour --limit.
    all_paths = list(
        _iter_corpus_files(knowledge_base, only_topic=args.only_topic)
    )
    if args.limit is not None and args.limit >= 0:
        paths = all_paths[: args.limit]
    else:
        paths = all_paths
    total = len(paths)

    started_at = time.time()
    emit_event(
        "ingest.regrandfather.start",
        {
            "mode": mode_label,
            "knowledge_base": str(knowledge_base),
            "total_candidates": total,
            "limit": args.limit,
            "only_topic": args.only_topic,
            "skip_llm": bool(args.skip_llm),
        },
    )

    aggregate = _Aggregate()

    for idx, path in enumerate(paths, start=1):
        rel_path = _relative_path(path, _REPO_ROOT)
        try:
            report, coerced_markdown = _process_one(
                path,
                skip_llm=bool(args.skip_llm),
                coerce_fn=coerce_to_canonical_template,
                chunk_fn=chunk_canonical_markdown,
            )
        except Exception as exc:  # noqa: BLE001 — we want to keep going
            aggregate.error_count += 1
            aggregate.errors.append({"path": str(path), "error": repr(exc)})
            emit_event(
                "ingest.regrandfather.failed",
                {
                    "filename": path.name,
                    "path": str(path),
                    "error": repr(exc),
                    "mode": mode_label,
                },
            )
            sys.stdout.write(
                f"[{idx}/{total}] {rel_path} -> ERROR {type(exc).__name__}: {exc}\n"
            )
            sys.stdout.flush()
            continue

        if commit_mode:
            # Only rewrite on a real change — avoids noise in git and keeps
            # already-canonical files pristine (bytes unchanged).
            try:
                original_bytes = path.read_bytes()
            except OSError:
                original_bytes = b""
            new_bytes = coerced_markdown.encode("utf-8")
            if new_bytes != original_bytes:
                path.write_bytes(new_bytes)
                report.mutated = True
            emit_event(
                "ingest.regrandfather.doc.processed",
                {
                    "filename": path.name,
                    "path": str(path),
                    "coercion_method": report.coercion_method,
                    "sections_matched_count": report.sections_matched_count,
                    "chunk_count": report.chunk_count,
                    "mutated": report.mutated,
                    "confidence": report.confidence,
                },
            )

        aggregate.docs_processed += 1
        aggregate.per_method[report.coercion_method] += 1
        for section_type, count in report.section_type_distribution.items():
            aggregate.per_section_type[section_type] += int(count)
        aggregate.reports.append(report)

        _log_progress(idx, total, rel_path, report)

    duration_s = round(time.time() - started_at, 3)

    summary = {
        "mode": mode_label,
        "knowledge_base": str(knowledge_base),
        "only_topic": args.only_topic,
        "skip_llm": bool(args.skip_llm),
        "limit": args.limit,
        "total_candidates": total,
        "docs_processed": aggregate.docs_processed,
        "error_count": aggregate.error_count,
        "duration_seconds": duration_s,
        "per_coercion_method": dict(aggregate.per_method),
        "per_section_type": dict(aggregate.per_section_type),
        "errors": aggregate.errors,
        "report_path": str(report_path),
        "docs": [
            {
                "path": r.path,
                "coercion_method": r.coercion_method,
                "sections_matched_count": r.sections_matched_count,
                "chunk_count": r.chunk_count,
                "section_type_distribution": r.section_type_distribution,
                "confidence": r.confidence,
                "llm_used": r.llm_used,
                "mutated": r.mutated,
            }
            for r in aggregate.reports
        ],
    }

    _write_report(report_path, summary)

    emit_event(
        "ingest.regrandfather.done",
        {
            "mode": mode_label,
            "docs_processed": aggregate.docs_processed,
            "error_count": aggregate.error_count,
            "per_coercion_method": dict(aggregate.per_method),
            "per_section_type": dict(aggregate.per_section_type),
            "duration_seconds": duration_s,
            "report_path": str(report_path),
        },
    )

    # Terse stdout summary.
    sys.stdout.write(
        f"\nregrandfather: mode={mode_label} docs={aggregate.docs_processed} "
        f"errors={aggregate.error_count} "
        f"methods={dict(aggregate.per_method)} "
        f"section_types={dict(aggregate.per_section_type)}\n"
        f"report: {report_path}\n"
    )
    sys.stdout.flush()

    if commit_mode and aggregate.error_count > 0:
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
