#!/usr/bin/env python3
"""ingestionfix_v3 Phase 2.5 Task E — apply the approved sector reclassification.

Reads ``artifacts/sector_classification/sector_reclassification_proposal.approved.json``,
validates its checksum + filename suffix, then writes ``documents.tema`` +
``doc_fingerprint=NULL`` for every migrate/new_sector decision. Docs whose
final bucket stays ``otros_sectoriales`` are skipped entirely (tema unchanged,
fingerprint left in place).

Safety rails (same shape as ``fingerprint_bust.py``):

* Input file MUST end in ``.approved.json`` AND its ``decisions_sha256``
  field MUST match the SHA-256 of ``{plan_version, decisions}`` computed with
  ``json.dumps(sort_keys=True, ensure_ascii=False)``. Fails fast otherwise.
* ``--dry-run`` is the default; prints a decision summary and writes the
  pre-execute manifest but issues zero UPDATE calls.
* ``--confirm`` is required for non-dry-run execution, regardless of size.
* Per-batch-group UPDATE: groups all docs moving to the same ``new_tema``
  into a single PostgREST ``.in_("doc_id", [...])`` call, chunked at 200
  keys (PostgREST URL-length cliff).
* Manifest is written BEFORE any UPDATE runs so a mid-flight crash still
  leaves an auditable record of which rows were targeted.

Usage::

    # Dry-run (safe; mandatory first pass)
    PYTHONPATH=src:. uv run python \\
      scripts/monitoring/monitor_sector_reclassification/apply_sector_reclassification.py \\
      --approved artifacts/sector_classification/sector_reclassification_proposal.approved.json \\
      --dry-run

    # Production write (requires --confirm)
    set -a; source .env.staging; set +a
    PYTHONPATH=src:. uv run python \\
      scripts/monitoring/monitor_sector_reclassification/apply_sector_reclassification.py \\
      --approved artifacts/sector_classification/sector_reclassification_proposal.approved.json \\
      --confirm

See ``docs/next/ingestionfix_v3.md`` §5 Phase 2.5 (Task E) for the canonical story.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

# Chosen to match PostgREST URL/body cliffs (same rationale as fingerprint_bust).
UPDATE_BATCH_SIZE = 200

APPROVED_SUFFIX = ".approved.json"


# ── Data shapes ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class Decision:
    doc_id: str
    current_tema: str
    new_tema: str
    action: str  # migrate_existing | new_sector | stay_orphan
    reason_tag: str


@dataclass(frozen=True)
class MigrationPlan:
    approved_path: Path
    plan_version: str
    decisions_sha256: str
    decisions: tuple[Decision, ...]
    approved_by: str
    approved_at_bogota: str

    @property
    def write_decisions(self) -> tuple[Decision, ...]:
        """Decisions that actually mutate rows (skip stay_orphan)."""
        return tuple(d for d in self.decisions if d.action != "stay_orphan")

    @property
    def action_counts(self) -> dict[str, int]:
        c: Counter[str] = Counter(d.action for d in self.decisions)
        return dict(c)

    @property
    def new_tema_counts(self) -> dict[str, int]:
        c: Counter[str] = Counter(d.new_tema for d in self.write_decisions)
        return dict(c)


# ── Approved-file loader (checksum + suffix gate) ────────────────────


class UnsafeApplyError(RuntimeError):
    """Raised when the caller's input or flag combination is unsafe."""


def _canonical_checksum_payload(body: dict[str, Any]) -> bytes:
    return json.dumps(
        {"plan_version": body["plan_version"], "decisions": body["decisions"]},
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")


def load_approved_plan(path: Path) -> MigrationPlan:
    """Parse + validate the approved proposal file.

    Refuses anything that doesn't end in ``.approved.json`` (per Task E's
    gate contract) AND anything whose embedded ``decisions_sha256`` doesn't
    match a recomputed SHA-256 over the canonical ``{plan_version, decisions}``
    payload.
    """
    p = Path(path)
    if not p.name.endswith(APPROVED_SUFFIX):
        raise UnsafeApplyError(
            f"apply_sector_reclassification: input must end in "
            f"'{APPROVED_SUFFIX}' (got {p.name!r}). Raw proposal files are "
            f"not accepted — approve them first."
        )
    if not p.exists():
        raise UnsafeApplyError(
            f"apply_sector_reclassification: approved file not found at {p}."
        )
    body = json.loads(p.read_text(encoding="utf-8"))
    for field_name in ("plan_version", "decisions", "decisions_sha256"):
        if field_name not in body:
            raise UnsafeApplyError(
                f"apply_sector_reclassification: approved file missing "
                f"required field {field_name!r}."
            )
    expected = hashlib.sha256(_canonical_checksum_payload(body)).hexdigest()
    if expected != body["decisions_sha256"]:
        raise UnsafeApplyError(
            "apply_sector_reclassification: checksum mismatch — the approved "
            "file has been modified after signing. Re-generate the approved "
            "proposal rather than hand-editing it."
        )
    decisions = tuple(
        Decision(
            doc_id=str(d["doc_id"]),
            current_tema=str(d.get("current_tema") or "otros_sectoriales"),
            new_tema=str(d["new_tema"]),
            action=str(d["action"]),
            reason_tag=str(d.get("reason_tag") or ""),
        )
        for d in body["decisions"]
    )
    return MigrationPlan(
        approved_path=p,
        plan_version=str(body["plan_version"]),
        decisions_sha256=str(body["decisions_sha256"]),
        decisions=decisions,
        approved_by=str(body.get("approved_by") or ""),
        approved_at_bogota=str(body.get("approved_at_bogota") or ""),
    )


# ── Pre-execute manifest ─────────────────────────────────────────────


def write_manifest(
    manifest_dir: Path,
    *,
    plan: MigrationPlan,
    dry_run: bool,
    confirm: bool,
    now: _dt.datetime | None = None,
) -> Path:
    """Persist the intended write plan BEFORE any UPDATE runs."""
    manifest_dir.mkdir(parents=True, exist_ok=True)
    ts = (now or _dt.datetime.now(_dt.timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    path = manifest_dir / f"{ts}_apply.json"
    payload = {
        "run_id": f"{ts}_apply",
        "generated_at_utc": ts,
        "approved_source": str(plan.approved_path),
        "approved_by": plan.approved_by,
        "approved_at_bogota": plan.approved_at_bogota,
        "plan_version": plan.plan_version,
        "decisions_sha256": plan.decisions_sha256,
        "dry_run": bool(dry_run),
        "flags": {"confirm": bool(confirm)},
        "action_counts": plan.action_counts,
        "new_tema_counts": plan.new_tema_counts,
        "write_row_count": len(plan.write_decisions),
        "write_decisions": [
            {
                "doc_id": d.doc_id,
                "new_tema": d.new_tema,
                "action": d.action,
                "reason_tag": d.reason_tag,
            }
            for d in plan.write_decisions
        ],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


# ── Safety rules ─────────────────────────────────────────────────────


def enforce_flag_rules(*, dry_run: bool, confirm: bool) -> None:
    if not dry_run and not confirm:
        raise UnsafeApplyError(
            "apply_sector_reclassification: non-dry-run execution requires "
            "--confirm. Re-run with --dry-run first to preview counts."
        )


# ── Writer ───────────────────────────────────────────────────────────


def _group_by_new_tema(
    decisions: Sequence[Decision],
) -> dict[str, list[str]]:
    """Collect doc_ids by their destination ``new_tema``.

    Skips stay_orphan decisions (caller should have filtered them, but
    being defensive here costs nothing and keeps this function callable
    in isolation from the tests).
    """
    groups: dict[str, list[str]] = defaultdict(list)
    for d in decisions:
        if d.action == "stay_orphan":
            continue
        groups[d.new_tema].append(d.doc_id)
    return dict(groups)


def apply_migration(
    client: Any,
    *,
    decisions: Sequence[Decision],
    batch_size: int = UPDATE_BATCH_SIZE,
) -> int:
    """Execute the UPDATE calls; returns total rows written.

    One UPDATE per (new_tema, chunk_of_doc_ids). ``doc_fingerprint`` is
    set to NULL so the next additive ingestion run reclassifies + re-sinks
    the affected docs.
    """
    groups = _group_by_new_tema(decisions)
    total = 0
    for new_tema, doc_ids in groups.items():
        for start in range(0, len(doc_ids), batch_size):
            chunk = doc_ids[start : start + batch_size]
            query = (
                client.table("documents")
                .update({"tema": new_tema, "doc_fingerprint": None})
                .in_("doc_id", chunk)
            )
            resp = query.execute()
            data = list(getattr(resp, "data", None) or [])
            total += len(data) if data else len(chunk)
    return total


# ── Orchestrator ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class ApplyOutcome:
    plan: MigrationPlan
    manifest_path: Path
    rows_written: int
    dry_run: bool


def run_apply(
    client: Any,
    *,
    approved_path: Path,
    manifest_dir: Path,
    dry_run: bool,
    confirm: bool,
    now: _dt.datetime | None = None,
) -> ApplyOutcome:
    enforce_flag_rules(dry_run=dry_run, confirm=confirm)
    plan = load_approved_plan(approved_path)

    # Manifest first — survives mid-UPDATE crashes.
    manifest_path = write_manifest(
        manifest_dir,
        plan=plan,
        dry_run=dry_run,
        confirm=confirm,
        now=now,
    )

    if dry_run:
        return ApplyOutcome(
            plan=plan,
            manifest_path=manifest_path,
            rows_written=0,
            dry_run=True,
        )

    rows_written = apply_migration(client, decisions=plan.write_decisions)
    return ApplyOutcome(
        plan=plan,
        manifest_path=manifest_path,
        rows_written=rows_written,
        dry_run=False,
    )


# ── CLI surface ──────────────────────────────────────────────────────


def _default_manifest_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "artifacts").is_dir() and (parent / "scripts").is_dir():
            return parent / "artifacts" / "sector_reclassification"
    return here.parents[3] / "artifacts" / "sector_reclassification"


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apply_sector_reclassification",
        description=(
            "Apply the approved otros_sectoriales reclassification to "
            "production Supabase: UPDATE documents SET tema=<new_tema>, "
            "doc_fingerprint=NULL for every migrate/new_sector decision."
        ),
    )
    parser.add_argument(
        "--approved",
        required=True,
        help="Path to *.approved.json proposal file (checksum-verified).",
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
        help="Load + validate approved file; write manifest; do NOT UPDATE.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required for non-dry-run execution.",
    )
    parser.add_argument(
        "--manifest-dir",
        default=None,
        help=(
            "Override output directory for the pre-execute manifest "
            "(default: artifacts/sector_reclassification/)."
        ),
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_argparser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        manifest_dir = (
            Path(args.manifest_dir)
            if args.manifest_dir
            else _default_manifest_dir()
        )
        approved_path = Path(args.approved)

        if args.dry_run:
            client: Any = _NullClient()  # never consulted in dry-run
        else:
            from lia_graph.supabase_client import (
                create_supabase_client_for_target,
            )

            client = create_supabase_client_for_target(args.target)

        outcome = run_apply(
            client,
            approved_path=approved_path,
            manifest_dir=manifest_dir,
            dry_run=args.dry_run,
            confirm=args.confirm,
        )
    except UnsafeApplyError as exc:
        print(f"[apply_sector_reclassification] REFUSED: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - CLI safety net
        print(f"[apply_sector_reclassification] ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "dry_run": outcome.dry_run,
                "approved_source": str(outcome.plan.approved_path),
                "plan_version": outcome.plan.plan_version,
                "action_counts": outcome.plan.action_counts,
                "write_row_count": len(outcome.plan.write_decisions),
                "rows_written": outcome.rows_written,
                "manifest_path": str(outcome.manifest_path),
                "distinct_new_temas": len(outcome.plan.new_tema_counts),
            },
            ensure_ascii=False,
        )
    )
    return 0


class _NullClient:
    """Stand-in used only for --dry-run so we don't create a real Supabase
    client when no mutation is intended."""

    def table(self, name: str) -> Any:  # pragma: no cover - never reached
        raise RuntimeError(
            "apply_sector_reclassification: _NullClient consulted in dry-run; "
            "this is a bug — dry-run paths must not touch the client."
        )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
