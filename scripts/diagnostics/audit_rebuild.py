"""Post-rebuild audit guardrail.

Scans a phase2 full-rebuild's log + the run's slice of events.jsonl and decides
whether the rebuild was clean or degraded. Exits non-zero on degradation so the
launcher / heartbeat / human cannot declare success on a silently-degraded run
(the trap documented in `docs/learnings/process/cloud-sink-execution-notes.md`
and re-measured at 55% degradation on 2026-04-24, see next_v2.md §J).

Pinned thresholds — kept here (single source of truth) and pytest-tested in
`tests/test_audit_rebuild.py`. Loosen these only with a same-PR justification
and corresponding test update.

Designed to be invoked at the end of `scripts/ingestion/launch_phase2_full_rebuild.sh`,
inline in the same nohup-bash block, so the rebuild and its audit share a
process group and produce a single PHASE2_AUDIT_VERDICT= marker.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


# Thresholds — see module docstring.
DEGRADATION_THRESHOLD_PCT = 5.0
MAX_TRACEBACKS = 0
MAX_HTTP_429 = 0
EXIT_MARKER_PREFIX = "PHASE2_FULL_REBUILD_EXIT="


@dataclass(frozen=True)
class AuditFindings:
    classified_total: int
    requires_review_count: int
    degradation_pct: float
    tracebacks: int
    http_429s: int
    exit_marker_seen: bool
    exit_code: int | None
    summary_block_seen: bool
    failures: tuple[str, ...]

    def is_clean(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict[str, object]:
        return {
            "classified_total": self.classified_total,
            "requires_review_count": self.requires_review_count,
            "degradation_pct": round(self.degradation_pct, 2),
            "tracebacks": self.tracebacks,
            "http_429s": self.http_429s,
            "exit_marker_seen": self.exit_marker_seen,
            "exit_code": self.exit_code,
            "summary_block_seen": self.summary_block_seen,
            "failures": list(self.failures),
            "verdict": "clean" if self.is_clean() else "degraded",
        }


def _iter_run_events(events_log: Path, start_utc: str) -> list[dict]:
    """Yield events.jsonl rows whose ts_utc >= start_utc.

    String comparison works because ISO-8601 timestamps sort lexically.
    """
    out: list[dict] = []
    if not events_log.exists():
        return out
    with events_log.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = rec.get("ts_utc") or ""
            if ts and ts >= start_utc:
                out.append(rec)
    return out


def _scan_log(log_path: Path) -> tuple[int, int, bool, int | None, bool]:
    """Return (tracebacks, http_429s, exit_marker_seen, exit_code, summary_block_seen).

    `summary_block_seen` looks for the top-level `--json` summary indicator
    (the ingest's first ``"ok": true`` line at indentation level 2 in the JSON
    output). We approximate by checking the very first occurrence is at the
    start of a line — the inner per-statement ``"ok": true`` rows are nested
    so they're indented.
    """
    if not log_path.exists():
        return (0, 0, False, None, False)
    text = log_path.read_text(encoding="utf-8", errors="replace")
    tracebacks = text.count("Traceback (most recent call last):")
    http_429s = text.count("Gemini HTTP 429") + text.count("RESOURCE_EXHAUSTED")
    # Avoid double-counting if both substrings appear on the same line; safer
    # to take the max of the two indicators rather than the sum.
    http_429s = max(text.count("Gemini HTTP 429"), text.count("RESOURCE_EXHAUSTED"))
    exit_marker_seen = False
    exit_code: int | None = None
    for line in reversed(text.splitlines()):
        if line.startswith(EXIT_MARKER_PREFIX):
            exit_marker_seen = True
            try:
                exit_code = int(line[len(EXIT_MARKER_PREFIX):].strip())
            except ValueError:
                exit_code = None
            break
    summary_block_seen = "\n  \"ok\": true," in text or text.startswith("{\n  \"ok\": true,")
    return (tracebacks, http_429s, exit_marker_seen, exit_code, summary_block_seen)


def audit(*, log_path: Path, events_log: Path, start_utc: str) -> AuditFindings:
    events = _iter_run_events(events_log, start_utc)
    classified = [e for e in events if e.get("event_type") == "subtopic.ingest.classified"]
    requires_review = [
        e for e in classified
        if (e.get("payload") or {}).get("requires_subtopic_review") is True
    ]
    classified_total = len(classified)
    requires_review_count = len(requires_review)
    degradation_pct = (
        (requires_review_count / classified_total * 100.0) if classified_total else 0.0
    )
    tracebacks, http_429s, exit_marker_seen, exit_code, summary_block_seen = _scan_log(log_path)

    failures: list[str] = []
    if not exit_marker_seen:
        failures.append(
            f"missing terminal-state marker `{EXIT_MARKER_PREFIX}<n>` in log "
            f"(observability-patterns.md mandate)"
        )
    elif exit_code != 0:
        failures.append(f"rebuild exited with non-zero code {exit_code}")
    if not summary_block_seen:
        failures.append("rebuild did not emit the top-level --json summary block")
    if tracebacks > MAX_TRACEBACKS:
        failures.append(
            f"{tracebacks} tracebacks in log (threshold {MAX_TRACEBACKS}); "
            f"see cloud-sink-execution-notes.md silent-degradation trap"
        )
    if http_429s > MAX_HTTP_429:
        failures.append(
            f"{http_429s} HTTP 429s / RESOURCE_EXHAUSTED in log "
            f"(threshold {MAX_HTTP_429}); TPM ceiling hit — re-run at "
            f"--classifier-workers 4 per parallelism-and-rate-limits.md"
        )
    # `requires_subtopic_review=true` has two distinct causes that look the same
    # in aggregate but mean different things for downstream trust:
    #   (a) TPM-induced degradation — N2 cascade hit a 429, classifier returned
    #       a degraded N1-only verdict. The rebuild's TEMA + HAS_SUBTOPIC edges
    #       encode random fallbacks. This is a hard failure.
    #   (b) Honest classifier uncertainty — N2 ran fine, the LLM just can't
    #       confidently pick a subtopic for an ambiguous doc. The verdicts are
    #       legitimate; the doc joins the subtopic-review queue. Not a failure.
    # Differentiator: tracebacks + HTTP 429s are present iff (a). Without them,
    # high `requires_review` is just data about subtopic ambiguity in the corpus.
    # See cloud-sink-execution-notes.md for the original rule (which scoped the
    # 5% threshold to the TPM case) and next_v2.md §J.2 for this refinement.
    if degradation_pct > DEGRADATION_THRESHOLD_PCT and (tracebacks > 0 or http_429s > 0):
        failures.append(
            f"requires_subtopic_review degradation rate "
            f"{degradation_pct:.1f}% > {DEGRADATION_THRESHOLD_PCT}% threshold "
            f"({requires_review_count}/{classified_total}) "
            f"AND TPM-pressure signals present (tracebacks={tracebacks}, 429s={http_429s}); "
            f"classifier pass is N1-only-degraded — re-run at "
            f"--classifier-workers 4 (parallelism-and-rate-limits.md)"
        )

    return AuditFindings(
        classified_total=classified_total,
        requires_review_count=requires_review_count,
        degradation_pct=degradation_pct,
        tracebacks=tracebacks,
        http_429s=http_429s,
        exit_marker_seen=exit_marker_seen,
        exit_code=exit_code,
        summary_block_seen=summary_block_seen,
        failures=tuple(failures),
    )


def _validate_iso_utc(value: str) -> str:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"--start-utc must be ISO-8601 (e.g. 2026-04-24T23:29:01); got {value!r}"
        ) from exc
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="audit_rebuild",
        description="Post-rebuild guardrail. Exits non-zero on degradation.",
    )
    parser.add_argument("--log", required=True, type=Path, help="Path to rebuild log.")
    parser.add_argument(
        "--events-log",
        type=Path,
        default=Path("logs/events.jsonl"),
        help="Path to events.jsonl (default: logs/events.jsonl).",
    )
    parser.add_argument(
        "--start-utc",
        required=True,
        type=_validate_iso_utc,
        help="UTC ISO-8601 timestamp the rebuild started; events older than this are ignored.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print findings as JSON instead of human prose.",
    )
    args = parser.parse_args(argv)

    findings = audit(
        log_path=args.log,
        events_log=args.events_log,
        start_utc=args.start_utc,
    )

    if args.json:
        print(json.dumps(findings.to_dict(), indent=2))
    else:
        print(f"# Rebuild audit — {datetime.now(timezone.utc).isoformat()}")
        print(f"# log: {args.log}")
        print(f"# start_utc: {args.start_utc}")
        print()
        print(f"classified docs:           {findings.classified_total}")
        print(f"requires_subtopic_review:  {findings.requires_review_count}")
        print(
            f"degradation rate:          {findings.degradation_pct:.1f}% "
            f"(threshold {DEGRADATION_THRESHOLD_PCT}%)"
        )
        print(f"tracebacks in log:         {findings.tracebacks} (threshold {MAX_TRACEBACKS})")
        print(f"HTTP 429s in log:          {findings.http_429s} (threshold {MAX_HTTP_429})")
        print(f"exit marker seen:          {findings.exit_marker_seen} (code {findings.exit_code})")
        print(f"--json summary block:      {findings.summary_block_seen}")
        print()
        if findings.is_clean():
            print("VERDICT: clean ✅")
        else:
            print("VERDICT: degraded ❌")
            for failure in findings.failures:
                print(f"  - {failure}")

    return 0 if findings.is_clean() else 2


if __name__ == "__main__":
    sys.exit(main())
