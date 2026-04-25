#!/usr/bin/env python3
"""Invalidate ``documents.doc_fingerprint`` for a targeted topic (or topic set).

The additive-delta ingestion path skips a document whenever its on-disk
content + classifier output hash still matches ``documents.doc_fingerprint``
in Supabase. That fingerprint checkpoint saves wall time on repeat runs but
has an ugly failure mode: when an earlier ingestion phase went wrong AFTER
the sink stamped the fingerprint, the next additive run sees the doc as
"unchanged" and silently skips it. The only pre-v3 escape was
``--force-full-classify``, which re-runs the classifier on all 1,280 corpus
docs (~40 minutes of wall time) and was what made today's 4×40-min reingest
pain so expensive.

This tool is the cheaper escape: null out ``doc_fingerprint`` for the
small subset of docs belonging to a given topic (or explicit ``--force-multi``
set of topics), so the next additive run reclassifies + re-sinks only that
subset. Pair it with ``scripts/launch_phase9a.sh`` for a full per-topic pass.

Safety rules (strict on purpose — this is a production Supabase write):

* ``--dry-run`` (default when ``--confirm`` is absent) performs only the
  SELECT and writes a manifest under ``artifacts/fingerprint_bust/``. Zero
  mutations. Use this first, always.
* ``--confirm`` is required before any UPDATE runs. Without it, the tool
  refuses to mutate, regardless of row count.
* ``--force-multi`` is required whenever more than one topic is supplied
  via ``--topics a,b,c``. Single-topic runs never need it.
* Row count > 200 without ``--confirm`` refuses explicitly (the safety
  threshold test fences this path; smaller counts refuse via the same
  rule with a different message so both code paths stay covered).

Manifest written BEFORE the UPDATE executes, so even if the UPDATE crashes
mid-batch the operator has an audit trail of exactly which rows were
targeted. Manifest path is printed on stdout.

Usage::

    # Dry run (always safe; no mutations)
    python scripts/fingerprint_bust.py --topic laboral --dry-run

    # Real run (requires --confirm)
    python scripts/fingerprint_bust.py --topic laboral --confirm

    # Multi-topic (requires --force-multi AND --confirm)
    python scripts/fingerprint_bust.py \
        --topics cambiario,activos_exterior,beneficio_auditoria \
        --confirm --force-multi

See ``docs/done/next/ingestionfix_v3.md`` §5 Phase 2 for the canonical story.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

# The default safety threshold for "how many rows can be mutated without
# looking scary". Chosen to match the PostgREST .in_() URL-length cliff that
# bit us in 9.A (~200 keys). Keep them aligned on purpose: if a topic has
# more than 200 live docs, the operator should think twice.
DEFAULT_SAFETY_THRESHOLD = 200

# Batch sizes for the two PostgREST pinch points (URL length on SELECT
# filter, body size on UPDATE payload). Matches v2's `_LOAD_BATCH_SIZE=200`
# + `_UPSERT_BATCH_SIZE=500` convention in `dangling_store.py`.
SELECT_BATCH_SIZE = 200
UPDATE_BATCH_SIZE = 200


# ── Data shapes ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class BustPlan:
    """The resolved set of rows the tool would (or will) mutate.

    Built in Phase 1 (SELECT) and consumed in Phase 2 (UPDATE). Keeping
    this as a distinct shape lets the unit tests exercise each phase
    independently.
    """

    topics: tuple[str, ...]
    doc_ids: tuple[str, ...]
    target: str  # "production" | "wip" — Supabase target

    @property
    def row_count(self) -> int:
        return len(self.doc_ids)


# ── Phase 1: resolve which docs to touch ─────────────────────────────


def resolve_affected_docs(
    client: Any,
    *,
    topics: Sequence[str],
    target: str,
) -> BustPlan:
    """SELECT doc_ids of live documents whose ``tema`` ∈ ``topics``.

    "Live" = ``retired_at IS NULL``. We deliberately skip retired docs:
    their fingerprints are irrelevant (additive path won't touch them)
    and mutating them would be a pointless production write.

    Batches the ``.in_()`` filter at ``SELECT_BATCH_SIZE`` keys; redundant
    for typical single-topic runs (1 topic = 1 filter value) but kept for
    symmetry with the multi-topic path.
    """
    topic_list = [t for t in (topics or []) if t]
    if not topic_list:
        raise ValueError("fingerprint_bust: at least one topic is required.")

    all_doc_ids: list[str] = []
    seen: set[str] = set()

    # Chunk the topic list for .in_() even though 200 topics is unrealistic;
    # keeps the code honest about the PostgREST URL-length limit.
    for chunk_start in range(0, len(topic_list), SELECT_BATCH_SIZE):
        chunk = topic_list[chunk_start : chunk_start + SELECT_BATCH_SIZE]
        query = (
            client.table("documents")
            .select("doc_id")
            .in_("tema", chunk)
            .is_("retired_at", "null")
        )
        resp = query.execute()
        for raw in list(getattr(resp, "data", None) or []):
            doc_id = str(raw.get("doc_id") or "").strip()
            if not doc_id or doc_id in seen:
                continue
            seen.add(doc_id)
            all_doc_ids.append(doc_id)

    return BustPlan(
        topics=tuple(topic_list),
        doc_ids=tuple(all_doc_ids),
        target=target,
    )


# ── Phase 2: null out the fingerprints ───────────────────────────────


def null_fingerprints(client: Any, *, doc_ids: Sequence[str]) -> int:
    """UPDATE ``documents`` SET ``doc_fingerprint=NULL`` for the given ids.

    Returns the total affected row count (accumulated across batches).
    Idempotent: running this twice in a row is a no-op on the second
    pass because the rows already carry ``doc_fingerprint IS NULL``. The
    caller is responsible for verifying that pre-condition when asserting
    sink-idempotency (Quality Gate G6).
    """
    ids = [d for d in (doc_ids or []) if d]
    if not ids:
        return 0

    total = 0
    for chunk_start in range(0, len(ids), UPDATE_BATCH_SIZE):
        chunk = ids[chunk_start : chunk_start + UPDATE_BATCH_SIZE]
        query = (
            client.table("documents")
            .update({"doc_fingerprint": None})
            .in_("doc_id", chunk)
        )
        resp = query.execute()
        data = list(getattr(resp, "data", None) or [])
        total += len(data) if data else len(chunk)
    return total


# ── Manifest ─────────────────────────────────────────────────────────


def write_manifest(
    manifest_dir: Path,
    *,
    plan: BustPlan,
    dry_run: bool,
    confirm: bool,
    force_multi: bool,
    tag: str,
    now: _dt.datetime | None = None,
) -> Path:
    """Persist the bust plan to ``artifacts/fingerprint_bust/<ts>_<tag>.json``.

    Called BEFORE the UPDATE runs. If the UPDATE crashes, the manifest
    survives for post-mortem; operators can re-run the tool safely because
    the underlying UPDATE is idempotent.
    """
    manifest_dir.mkdir(parents=True, exist_ok=True)
    ts = (now or _dt.datetime.now(_dt.timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    safe_tag = "".join(c if c.isalnum() or c in "-_" else "_" for c in tag)[:48]
    path = manifest_dir / f"{ts}_{safe_tag}.json"
    payload = {
        "run_id": f"{ts}_{safe_tag}",
        "generated_at_utc": ts,
        "target": plan.target,
        "topics": list(plan.topics),
        "row_count": plan.row_count,
        "doc_ids": list(plan.doc_ids),
        "dry_run": bool(dry_run),
        "flags": {
            "confirm": bool(confirm),
            "force_multi": bool(force_multi),
        },
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


# ── Safety rules ─────────────────────────────────────────────────────


class UnsafeBustError(RuntimeError):
    """Raised when the caller's flag combination would permit an unsafe run."""


def enforce_flag_rules(
    topics: Sequence[str],
    *,
    confirm: bool,
    force_multi: bool,
    dry_run: bool,
) -> None:
    """Validate the flag combination BEFORE any I/O.

    Separate from the row-count check (``enforce_row_count_rule``) so
    tests can exercise each path independently.
    """
    topic_list = [t for t in (topics or []) if t]
    if not topic_list:
        raise UnsafeBustError("fingerprint_bust: supply --topic or --topics.")
    if len(topic_list) > 1 and not force_multi:
        raise UnsafeBustError(
            "fingerprint_bust: --topics with more than one topic requires "
            "--force-multi (belt-and-suspenders; single-topic runs are the "
            "default safe path)."
        )
    if not dry_run and not confirm:
        raise UnsafeBustError(
            "fingerprint_bust: non-dry-run execution requires --confirm. "
            "Re-run with --dry-run first to preview the row count."
        )


def enforce_row_count_rule(
    plan: BustPlan,
    *,
    confirm: bool,
    dry_run: bool,
    threshold: int = DEFAULT_SAFETY_THRESHOLD,
) -> None:
    """Refuse huge mutations absent explicit confirmation.

    Run AFTER the SELECT resolves ``plan.row_count``. The threshold is a
    soft guardrail: operators with ``--confirm`` can still mutate >200
    rows, but the unconfirmed path refuses with an explicit message so
    the failure mode is audible, not silent.
    """
    if dry_run:
        return
    if plan.row_count > threshold and not confirm:
        raise UnsafeBustError(
            f"fingerprint_bust: would mutate {plan.row_count} rows (> "
            f"{threshold} threshold) without --confirm. Refusing. Re-run "
            f"with --confirm if this is intentional."
        )


# ── Orchestrator ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class BustOutcome:
    plan: BustPlan
    manifest_path: Path
    rows_updated: int
    dry_run: bool


def run_bust(
    client: Any,
    *,
    topics: Sequence[str],
    target: str,
    dry_run: bool,
    confirm: bool,
    force_multi: bool,
    manifest_dir: Path,
    tag: str,
    now: _dt.datetime | None = None,
) -> BustOutcome:
    """Top-level entrypoint used by both the CLI and the unit tests."""
    enforce_flag_rules(
        topics, confirm=confirm, force_multi=force_multi, dry_run=dry_run
    )
    plan = resolve_affected_docs(client, topics=topics, target=target)
    enforce_row_count_rule(plan, confirm=confirm, dry_run=dry_run)

    # Write manifest BEFORE the UPDATE. If the UPDATE crashes mid-flight,
    # the operator still has an audit trail of the intended rows.
    manifest_path = write_manifest(
        manifest_dir,
        plan=plan,
        dry_run=dry_run,
        confirm=confirm,
        force_multi=force_multi,
        tag=tag,
        now=now,
    )

    if dry_run:
        return BustOutcome(
            plan=plan,
            manifest_path=manifest_path,
            rows_updated=0,
            dry_run=True,
        )

    rows_updated = null_fingerprints(client, doc_ids=plan.doc_ids)
    return BustOutcome(
        plan=plan,
        manifest_path=manifest_path,
        rows_updated=rows_updated,
        dry_run=False,
    )


# ── CLI surface ──────────────────────────────────────────────────────


def _parse_topics(args: argparse.Namespace) -> list[str]:
    if args.topic and args.topics:
        raise UnsafeBustError(
            "fingerprint_bust: pass either --topic OR --topics, not both."
        )
    if args.topic:
        return [args.topic.strip()]
    if args.topics:
        return [t.strip() for t in args.topics.split(",") if t.strip()]
    return []


def _build_tag(topics: Sequence[str]) -> str:
    if len(topics) == 1:
        return topics[0]
    return f"batch_{len(topics)}topics"


def _default_manifest_dir() -> Path:
    # Walk up until we find the repo root (has artifacts/ and scripts/
    # siblings). Resilient to future file moves under scripts/.
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "artifacts").is_dir() and (parent / "scripts").is_dir():
            return parent / "artifacts" / "fingerprint_bust"
    # Fallback: three-levels-up matches the layout at the time of writing
    # (scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py).
    return here.parents[3] / "artifacts" / "fingerprint_bust"


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fingerprint_bust",
        description=(
            "Invalidate documents.doc_fingerprint for a targeted topic so the "
            "next additive ingestion run reclassifies + re-sinks that subset."
        ),
    )
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument(
        "--topic",
        help="Single topic key (e.g. 'laboral'). Use --topics for multi.",
    )
    selector.add_argument(
        "--topics",
        help="Comma-separated topic keys. Requires --force-multi.",
    )
    parser.add_argument(
        "--target",
        default="production",
        choices=["production", "wip"],
        help="Supabase target (default: production).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="SELECT only; write manifest; do NOT issue UPDATE.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required for non-dry-run execution.",
    )
    parser.add_argument(
        "--force-multi",
        action="store_true",
        help="Required when --topics contains more than one key.",
    )
    parser.add_argument(
        "--manifest-dir",
        default=None,
        help="Override output directory (defaults to artifacts/fingerprint_bust/).",
    )
    parser.add_argument(
        "--tag",
        default=None,
        help="Override the manifest filename tag (default: derived from topics).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_argparser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        topics = _parse_topics(args)
        tag = args.tag or _build_tag(topics)
        manifest_dir = (
            Path(args.manifest_dir) if args.manifest_dir else _default_manifest_dir()
        )

        # Lazy import so unit tests don't need a real supabase client.
        from lia_graph.supabase_client import create_supabase_client_for_target

        client = create_supabase_client_for_target(args.target)
        outcome = run_bust(
            client,
            topics=topics,
            target=args.target,
            dry_run=args.dry_run,
            confirm=args.confirm,
            force_multi=args.force_multi,
            manifest_dir=manifest_dir,
            tag=tag,
        )
    except UnsafeBustError as exc:
        print(f"[fingerprint_bust] REFUSED: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - CLI safety net
        print(f"[fingerprint_bust] ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "dry_run": outcome.dry_run,
                "target": outcome.plan.target,
                "topics": list(outcome.plan.topics),
                "row_count": outcome.plan.row_count,
                "rows_updated": outcome.rows_updated,
                "manifest_path": str(outcome.manifest_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
