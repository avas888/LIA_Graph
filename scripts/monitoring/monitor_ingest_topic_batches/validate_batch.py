#!/usr/bin/env python3
"""ingestionfix_v3 Phase 3.0 — Batch Quality Gate validator.

Runs G1-G10 automated checks against a just-completed batch and persists
the results to ``artifacts/batch_<N>_quality_gate.json``. The operator is
still responsible for M1-M3 (manual smokes) and U1-U4 (ultra-tests) —
this validator handles only the automation-safe slice.

The ten gates:

============  ==================================================================
 G1           Fingerprint-bust applied: documents count per batch topics
              equals the bust manifest's row_count.
 G2           Bust-targeted docs got fresh chunks: DISTINCT doc_id count in
              document_chunks equals row_count.
 G3           Per-topic Falkor TopicNode populated (count == 1 per topic).
 G4           Per-topic Falkor TEMA edges > 0 (at least one per topic).
 G5           No unexpected failure events in logs/events.jsonl for the
              batch's delta_id.
 G6           Sink idempotency: re-running fingerprint_bust in dry-run on
              the batch's topics would mutate 0 rows (all fingerprints
              re-persisted).
 G7           Cross-batch isolation: the next batch's doc-id set does not
              overlap this batch's manifest doc_ids.
 G8           embedding IS NULL = 0 for the batch's chunk set.
 G9           Reingest wall time within the expected 5-25 minute window.
 G10          Zero chunk_text anomalies (NULL or empty) for batch doc_ids.
============  ==================================================================

All G-checks are pure helpers that accept mocked clients so unit tests can
fence them without a live cloud.

See ``docs/next/ingestionfix_v3.md`` §5 Phase 3.0 for the full contract.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


# ── Result shape ─────────────────────────────────────────────────────


@dataclass
class CheckResult:
    """Outcome of a single G-check."""

    gate_id: str
    passed: bool
    detail: str
    actual: Any = None
    expected: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "passed": bool(self.passed),
            "detail": self.detail,
            "actual": self.actual,
            "expected": self.expected,
        }


@dataclass
class GateSummary:
    """Aggregate over all G-checks; the status of the entire automated tier.

    Manual smokes (M1-M3) and ultra-tests (U1-U4) are captured separately —
    the operator fills those in directly in the gate file once they've
    completed the browser / eval work.
    """

    batch: int
    checks: list[CheckResult] = field(default_factory=list)
    generated_at_utc: str = ""

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch": self.batch,
            "generated_at_utc": self.generated_at_utc,
            "status": "passed" if self.all_passed else "failed",
            "auto_checks": [c.to_dict() for c in self.checks],
            "manual_smokes": {
                "M1_retrieval_spot_check": None,
                "M2_main_chat_e2e": None,
                "M3_eval_c_gold_delta": None,
            },
            "ultra_tests": {
                "U1_row_level_audit": None,
                "U2_idempotency_rerun": None,
                "U3_regression_suite": None,
                "U4_chain_stop_resume": None,
            },
            "approved_by": None,
            "approved_at": None,
        }


# ── G-checks (pure helpers) ──────────────────────────────────────────


def _count(resp: Any) -> int:
    """Extract a count from a PostgREST ``select(count='exact')`` response."""
    value = getattr(resp, "count", None)
    if value is None and isinstance(resp, Mapping):
        value = resp.get("count")
    return int(value or 0)


def check_g1_fingerprint_applied(
    client: Any,
    *,
    topics: Sequence[str],
    expected_row_count: int,
) -> CheckResult:
    resp = (
        client.table("documents")
        .select("doc_id", count="exact")
        .in_("tema", list(topics))
        .is_("retired_at", "null")
        .execute()
    )
    actual = _count(resp)
    passed = actual == expected_row_count
    return CheckResult(
        gate_id="G1",
        passed=passed,
        detail=(
            f"documents(tema IN {len(topics)} topics, live) = {actual}; "
            f"manifest row_count = {expected_row_count}"
        ),
        actual=actual,
        expected=expected_row_count,
    )


def check_g2_docs_got_chunks(
    client: Any,
    *,
    doc_ids: Sequence[str],
) -> CheckResult:
    if not doc_ids:
        return CheckResult(
            gate_id="G2",
            passed=True,
            detail="no doc_ids to check (vacuously true)",
            actual=0,
            expected=0,
        )
    resp = (
        client.table("document_chunks")
        .select("doc_id", count="exact")
        .in_("doc_id", list(doc_ids))
        .execute()
    )
    data = list(getattr(resp, "data", None) or [])
    distinct_docs = {str(r.get("doc_id")) for r in data if r.get("doc_id")}
    passed = len(distinct_docs) == len(doc_ids)
    return CheckResult(
        gate_id="G2",
        passed=passed,
        detail=(
            f"document_chunks distinct doc_id count = {len(distinct_docs)}; "
            f"manifest doc_ids = {len(doc_ids)}"
        ),
        actual=len(distinct_docs),
        expected=len(doc_ids),
    )


def check_g3_topic_nodes(
    falkor: Any,
    *,
    topics: Sequence[str],
) -> CheckResult:
    missing: list[str] = []
    for topic in topics:
        count = falkor.topic_node_count(topic)
        if count < 1:
            missing.append(topic)
    passed = not missing
    return CheckResult(
        gate_id="G3",
        passed=passed,
        detail=(
            "all topics have TopicNode"
            if passed
            else f"missing TopicNode for: {missing}"
        ),
        actual={"missing": missing},
        expected={"missing": []},
    )


def check_g4_tema_edges(
    falkor: Any,
    *,
    topics: Sequence[str],
) -> CheckResult:
    zero_edge: list[str] = []
    for topic in topics:
        count = falkor.tema_edge_count(topic)
        if count < 1:
            zero_edge.append(topic)
    passed = not zero_edge
    return CheckResult(
        gate_id="G4",
        passed=passed,
        detail=(
            "all topics have >= 1 TEMA edge"
            if passed
            else f"no TEMA edges into TopicNode for: {zero_edge}"
        ),
        actual={"zero_edge": zero_edge},
        expected={"zero_edge": []},
    )


_FAILURE_PATTERN = re.compile(r"(error|failed|exception)", re.IGNORECASE)


def check_g5_no_failure_events(
    events_log: Path,
    *,
    delta_id: str,
) -> CheckResult:
    if not events_log.exists():
        return CheckResult(
            gate_id="G5",
            passed=False,
            detail=f"events log not found: {events_log}",
            actual={"matches": None},
            expected={"matches": []},
        )
    matches: list[str] = []
    with events_log.open() as f:
        for raw_line in f:
            if delta_id not in raw_line:
                continue
            if _FAILURE_PATTERN.search(raw_line):
                matches.append(raw_line.strip())
    passed = not matches
    return CheckResult(
        gate_id="G5",
        passed=passed,
        detail=(
            f"no failure-shaped events for delta_id={delta_id}"
            if passed
            else f"{len(matches)} failure-shaped events; first: {matches[0][:200]}"
        ),
        actual={"match_count": len(matches)},
        expected={"match_count": 0},
    )


def check_g6_sink_idempotency(
    dry_run_row_count: int,
) -> CheckResult:
    """The caller is expected to re-run ``fingerprint_bust --dry-run`` against
    the same topic set and pass the row count here. Zero means every doc
    got a fresh fingerprint; anything else means at least one sink write
    missed a fingerprint re-stamp and will re-trigger next pass.
    """
    passed = dry_run_row_count == 0
    return CheckResult(
        gate_id="G6",
        passed=passed,
        detail=(
            "dry-run bust reports 0 rows — sink idempotent"
            if passed
            else f"dry-run bust would affect {dry_run_row_count} rows (expected 0)"
        ),
        actual=dry_run_row_count,
        expected=0,
    )


def check_g7_cross_batch_isolation(
    *,
    current_doc_ids: Sequence[str],
    next_batch_doc_ids: Sequence[str],
) -> CheckResult:
    current = set(current_doc_ids)
    overlap = current.intersection(next_batch_doc_ids)
    passed = not overlap
    return CheckResult(
        gate_id="G7",
        passed=passed,
        detail=(
            "no doc_id overlap with next batch"
            if passed
            else f"{len(overlap)} doc_ids overlap between batches: "
                 f"{sorted(overlap)[:5]}"
        ),
        actual={"overlap_count": len(overlap)},
        expected={"overlap_count": 0},
    )


def check_g8_null_embed_zero(
    client: Any,
    *,
    doc_ids: Sequence[str],
) -> CheckResult:
    if not doc_ids:
        return CheckResult(
            gate_id="G8",
            passed=True,
            detail="no doc_ids to check (vacuously true)",
            actual=0,
            expected=0,
        )
    resp = (
        client.table("document_chunks")
        .select("chunk_id", count="exact")
        .in_("doc_id", list(doc_ids))
        .is_("embedding", "null")
        .execute()
    )
    actual = _count(resp)
    passed = actual == 0
    return CheckResult(
        gate_id="G8",
        passed=passed,
        detail=f"document_chunks with NULL embedding for batch doc_ids = {actual}",
        actual=actual,
        expected=0,
    )


def check_g9_walltime_in_range(
    *,
    elapsed_ms: int,
    lower_minutes: int = 5,
    upper_minutes: int = 25,
) -> CheckResult:
    elapsed_min = elapsed_ms / 60_000
    passed = lower_minutes <= elapsed_min <= upper_minutes
    return CheckResult(
        gate_id="G9",
        passed=passed,
        detail=(
            f"delta elapsed = {elapsed_min:.1f} min "
            f"(expected {lower_minutes}-{upper_minutes})"
        ),
        actual=round(elapsed_min, 1),
        expected=f"[{lower_minutes}, {upper_minutes}]",
    )


def check_g10_no_chunk_text_anomalies(
    client: Any,
    *,
    doc_ids: Sequence[str],
) -> CheckResult:
    if not doc_ids:
        return CheckResult(
            gate_id="G10",
            passed=True,
            detail="no doc_ids to check (vacuously true)",
            actual=0,
            expected=0,
        )
    # Fetch only the chunk_text column; scan client-side. Supabase
    # supports `.or_()` for the empty-OR-null test but that API has known
    # quoting quirks; easier + safer to filter here.
    resp = (
        client.table("document_chunks")
        .select("chunk_text")
        .in_("doc_id", list(doc_ids))
        .execute()
    )
    anomalies = 0
    for row in list(getattr(resp, "data", None) or []):
        text = row.get("chunk_text")
        if text is None or (isinstance(text, str) and text.strip() == ""):
            anomalies += 1
    passed = anomalies == 0
    return CheckResult(
        gate_id="G10",
        passed=passed,
        detail=f"chunk_text NULL-or-empty rows for batch doc_ids = {anomalies}",
        actual=anomalies,
        expected=0,
    )


# ── Dependency wrappers (live) ───────────────────────────────────────


class _LiveFalkorProbe:
    """Thin wrapper the G3/G4 checks consume. Kept as a class so unit
    tests can substitute a mock with ``topic_node_count`` /
    ``tema_edge_count`` methods.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def topic_node_count(self, topic_key: str) -> int:
        from lia_graph.graph.client import GraphWriteStatement

        stmt = GraphWriteStatement(
            description="topic_node_count",
            query="MATCH (t:TopicNode {topic_key: $key}) RETURN count(t) AS n",
            parameters={"key": topic_key},
        )
        rows = list(self._client.execute(stmt, strict=True).rows)
        return int(rows[0]["n"]) if rows else 0

    def tema_edge_count(self, topic_key: str) -> int:
        from lia_graph.graph.client import GraphWriteStatement

        stmt = GraphWriteStatement(
            description="tema_edge_count",
            query=(
                "MATCH ()-[e:TEMA]->(t:TopicNode {topic_key: $key}) "
                "RETURN count(e) AS n"
            ),
            parameters={"key": topic_key},
        )
        rows = list(self._client.execute(stmt, strict=True).rows)
        return int(rows[0]["n"]) if rows else 0


# ── Top-level runner ─────────────────────────────────────────────────


@dataclass
class ValidationInputs:
    """All the data the validator needs to run G1-G10 once a batch lands.

    Populated by the CLI from the plan + bust manifest + run log + optional
    next-batch manifest. Tests construct this directly with mocked clients.
    """

    batch: int
    topics: Sequence[str]
    doc_ids: Sequence[str]
    manifest_row_count: int
    delta_id: str
    delta_elapsed_ms: int
    dry_run_row_count_after: int
    next_batch_doc_ids: Sequence[str]
    events_log: Path
    supa_client: Any
    falkor_probe: Any


def run_all_checks(inputs: ValidationInputs) -> GateSummary:
    """Execute every G1-G10 check and collect results into a GateSummary."""
    summary = GateSummary(
        batch=inputs.batch,
        generated_at_utc=_dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    )
    summary.checks.extend(
        [
            check_g1_fingerprint_applied(
                inputs.supa_client,
                topics=inputs.topics,
                expected_row_count=inputs.manifest_row_count,
            ),
            check_g2_docs_got_chunks(
                inputs.supa_client, doc_ids=inputs.doc_ids
            ),
            check_g3_topic_nodes(inputs.falkor_probe, topics=inputs.topics),
            check_g4_tema_edges(inputs.falkor_probe, topics=inputs.topics),
            check_g5_no_failure_events(
                inputs.events_log, delta_id=inputs.delta_id
            ),
            check_g6_sink_idempotency(inputs.dry_run_row_count_after),
            check_g7_cross_batch_isolation(
                current_doc_ids=inputs.doc_ids,
                next_batch_doc_ids=inputs.next_batch_doc_ids,
            ),
            check_g8_null_embed_zero(
                inputs.supa_client, doc_ids=inputs.doc_ids
            ),
            check_g9_walltime_in_range(elapsed_ms=inputs.delta_elapsed_ms),
            check_g10_no_chunk_text_anomalies(
                inputs.supa_client, doc_ids=inputs.doc_ids
            ),
        ]
    )
    return summary


def write_gate_file(summary: GateSummary, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


# ── CLI ──────────────────────────────────────────────────────────────


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="validate_batch",
        description="Run G1-G10 automated checks for a completed batch.",
    )
    p.add_argument("--batch", type=int, required=True, help="Batch number (1..8).")
    p.add_argument(
        "--gate",
        action="store_true",
        help="Write artifacts/batch_<N>_quality_gate.json on completion.",
    )
    p.add_argument(
        "--plan",
        default="artifacts/fingerprint_bust/plan.json",
        help="Path to the batch plan JSON.",
    )
    p.add_argument(
        "--manifest",
        required=True,
        help="Path to the fingerprint-bust manifest for this batch.",
    )
    p.add_argument(
        "--delta-id",
        required=True,
        help="delta_id of the batch's reingest run.",
    )
    p.add_argument(
        "--delta-elapsed-ms",
        type=int,
        required=True,
        help="Elapsed milliseconds of the reingest run (for G9).",
    )
    p.add_argument(
        "--dry-run-row-count-after",
        type=int,
        default=0,
        help="Row count reported by fingerprint_bust --dry-run AFTER the batch completed (G6).",
    )
    p.add_argument(
        "--next-batch-manifest",
        default=None,
        help="Optional path to the next batch's bust manifest (for G7).",
    )
    p.add_argument(
        "--events-log",
        default="logs/events.jsonl",
        help="Events log path (for G5).",
    )
    p.add_argument(
        "--output",
        default=None,
        help="Override the gate file path (defaults to artifacts/batch_<N>_quality_gate.json).",
    )
    p.add_argument(
        "--target",
        default="production",
        choices=["production", "wip"],
        help="Supabase target.",
    )
    return p


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Iterable[str] | None = None) -> int:  # pragma: no cover
    args = build_argparser().parse_args(list(argv) if argv is not None else None)

    manifest = _load_manifest(Path(args.manifest))
    topics = list(manifest.get("topics") or [])
    doc_ids = list(manifest.get("doc_ids") or [])
    row_count = int(manifest.get("row_count") or 0)

    next_doc_ids: list[str] = []
    if args.next_batch_manifest:
        next_doc_ids = list(
            _load_manifest(Path(args.next_batch_manifest)).get("doc_ids") or []
        )

    from lia_graph.supabase_client import create_supabase_client_for_target
    from lia_graph.graph.client import GraphClient

    inputs = ValidationInputs(
        batch=args.batch,
        topics=topics,
        doc_ids=doc_ids,
        manifest_row_count=row_count,
        delta_id=args.delta_id,
        delta_elapsed_ms=args.delta_elapsed_ms,
        dry_run_row_count_after=args.dry_run_row_count_after,
        next_batch_doc_ids=next_doc_ids,
        events_log=Path(args.events_log),
        supa_client=create_supabase_client_for_target(args.target),
        falkor_probe=_LiveFalkorProbe(GraphClient.from_env()),
    )
    summary = run_all_checks(inputs)

    gate_path = (
        Path(args.output)
        if args.output
        else Path(f"artifacts/batch_{args.batch}_quality_gate.json")
    )

    if args.gate:
        write_gate_file(summary, gate_path)

    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    return 0 if summary.all_passed else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
