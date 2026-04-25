"""Pinned thresholds for `scripts/diagnostics/audit_rebuild.py`.

The audit is the runtime guardrail that prevents a degraded full-rebuild
from being declared "done" silently — the failure mode that surfaced in
next_v2.md §J on 2026-04-24 (55% requires_subtopic_review under 8 workers,
silent through the pool's failed= boundary). These tests pin every
threshold + edge case so a future PR can't loosen the guardrail without a
visible test edit.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


# Load the script as a module without requiring a package install — script
# lives in scripts/diagnostics/, not in the lia_graph package.
_AUDIT_PATH = (
    Path(__file__).resolve().parent.parent
    / "scripts" / "diagnostics" / "audit_rebuild.py"
)
_spec = importlib.util.spec_from_file_location("audit_rebuild", _AUDIT_PATH)
audit_rebuild = importlib.util.module_from_spec(_spec)
sys.modules["audit_rebuild"] = audit_rebuild
_spec.loader.exec_module(audit_rebuild)


# Fixture builders ---------------------------------------------------------

def _events_jsonl(rows: list[dict]) -> str:
    return "\n".join(json.dumps(r) for r in rows) + "\n"


def _classified_event(ts: str, requires_review: bool) -> dict:
    return {
        "ts_utc": ts,
        "event_type": "subtopic.ingest.classified",
        "payload": {"requires_subtopic_review": requires_review},
    }


def _clean_log() -> str:
    """Top-level --json summary block + exit marker, no tracebacks, no 429s."""
    return (
        "{\n"
        '  "ok": true,\n'
        '  "corpus_dir": "knowledge_base"\n'
        "}\n"
        "PHASE2_FULL_REBUILD_EXIT=0\n"
    )


# Tests --------------------------------------------------------------------

def test_clean_run_passes(tmp_path: Path) -> None:
    log = tmp_path / "rebuild.log"
    log.write_text(_clean_log())
    events = tmp_path / "events.jsonl"
    events.write_text(_events_jsonl([
        _classified_event("2026-04-25T00:00:01", False),
        _classified_event("2026-04-25T00:00:02", False),
        _classified_event("2026-04-25T00:00:03", False),
    ]))

    findings = audit_rebuild.audit(
        log_path=log, events_log=events, start_utc="2026-04-25T00:00:00",
    )
    assert findings.is_clean()
    assert findings.degradation_pct == 0.0
    assert findings.tracebacks == 0
    assert findings.http_429s == 0
    assert findings.exit_marker_seen is True
    assert findings.exit_code == 0


def test_today_55pct_degradation_fails(tmp_path: Path) -> None:
    """Reproduces today's §J rebuild — 55% requires_subtopic_review must fail."""
    log = tmp_path / "rebuild.log"
    log.write_text(
        _clean_log()  # the run technically completed; only the audit catches it
        + "Gemini HTTP 429: RESOURCE_EXHAUSTED quota exceeded\n" * 144
        + "Traceback (most recent call last):\n  File ...\nRuntimeError: x\n" * 96
    )
    rows: list[dict] = []
    # 55% degraded mirrors the 702/1275 measurement on the audit run.
    for i in range(1275):
        rows.append(_classified_event(
            f"2026-04-24T23:29:{i % 60:02d}.{i:06d}",
            requires_review=(i < 702),
        ))
    events = tmp_path / "events.jsonl"
    events.write_text(_events_jsonl(rows))

    findings = audit_rebuild.audit(
        log_path=log, events_log=events, start_utc="2026-04-24T23:29:00",
    )
    assert not findings.is_clean()
    assert findings.degradation_pct > audit_rebuild.DEGRADATION_THRESHOLD_PCT
    assert findings.tracebacks > audit_rebuild.MAX_TRACEBACKS
    assert findings.http_429s > audit_rebuild.MAX_HTTP_429
    # Exactly the three operationally-actionable failure messages must appear.
    failure_text = " ".join(findings.failures)
    assert "degradation rate" in failure_text
    assert "tracebacks" in failure_text
    assert "HTTP 429" in failure_text or "RESOURCE_EXHAUSTED" in failure_text
    assert "--classifier-workers 4" in failure_text  # operator guidance carried through


def test_silent_death_no_exit_marker_fails(tmp_path: Path) -> None:
    """Process exited without writing the marker — the canonical silent-death case."""
    log = tmp_path / "rebuild.log"
    # No `PHASE2_FULL_REBUILD_EXIT=` line.
    log.write_text("some normal output\n")
    events = tmp_path / "events.jsonl"
    events.write_text(_events_jsonl([
        _classified_event("2026-04-25T00:00:01", False),
    ]))

    findings = audit_rebuild.audit(
        log_path=log, events_log=events, start_utc="2026-04-25T00:00:00",
    )
    assert not findings.is_clean()
    assert findings.exit_marker_seen is False
    assert any("missing terminal-state marker" in f for f in findings.failures)


def test_non_zero_exit_code_fails(tmp_path: Path) -> None:
    log = tmp_path / "rebuild.log"
    log.write_text(_clean_log().replace("PHASE2_FULL_REBUILD_EXIT=0", "PHASE2_FULL_REBUILD_EXIT=2"))
    events = tmp_path / "events.jsonl"
    events.write_text(_events_jsonl([_classified_event("2026-04-25T00:00:01", False)]))

    findings = audit_rebuild.audit(
        log_path=log, events_log=events, start_utc="2026-04-25T00:00:00",
    )
    assert not findings.is_clean()
    assert any("non-zero code 2" in f for f in findings.failures)


def test_events_before_start_utc_are_ignored(tmp_path: Path) -> None:
    log = tmp_path / "rebuild.log"
    log.write_text(_clean_log())
    events = tmp_path / "events.jsonl"
    events.write_text(_events_jsonl([
        # Stale event from yesterday's run — must NOT count toward today's audit.
        _classified_event("2026-04-23T10:00:00", True),
        _classified_event("2026-04-23T10:00:01", True),
        # Today's run, all clean.
        _classified_event("2026-04-25T00:00:01", False),
        _classified_event("2026-04-25T00:00:02", False),
    ]))

    findings = audit_rebuild.audit(
        log_path=log, events_log=events, start_utc="2026-04-25T00:00:00",
    )
    assert findings.classified_total == 2  # not 4
    assert findings.requires_review_count == 0  # the stale degraded events are ignored
    assert findings.is_clean()


def test_threshold_boundary_5_percent_passes(tmp_path: Path) -> None:
    """Exactly 5% degradation is the threshold — values UP TO and including
    the threshold must NOT fail (strict-greater is the rule)."""
    log = tmp_path / "rebuild.log"
    log.write_text(_clean_log())
    events = tmp_path / "events.jsonl"
    rows: list[dict] = []
    for i in range(100):
        rows.append(_classified_event(
            f"2026-04-25T00:00:{i % 60:02d}.{i:06d}",
            requires_review=(i < 5),  # exactly 5/100 = 5.0%
        ))
    events.write_text(_events_jsonl(rows))

    findings = audit_rebuild.audit(
        log_path=log, events_log=events, start_utc="2026-04-25T00:00:00",
    )
    assert findings.degradation_pct == 5.0
    assert findings.is_clean(), (
        f"5% should be at the boundary, not over it; got failures: {findings.failures}"
    )


def test_high_review_rate_without_tpm_signals_passes(tmp_path: Path) -> None:
    """Honest classifier uncertainty case: 30% requires_review but 0 tracebacks
    and 0 HTTP 429s. Means the N2 cascade ran cleanly and the LLM just couldn't
    pick a confident subtopic for ambiguous docs — that's data, not failure.

    Reproduces today's workers=4 rebuild profile (next_v2.md §J.2 outcome
    block). Without this carve-out, the audit would false-positive on every
    rebuild whose corpus has a meaningful tail of subtopic-ambiguous docs."""
    log = tmp_path / "rebuild.log"
    log.write_text(_clean_log())  # no tracebacks, no 429s
    events = tmp_path / "events.jsonl"
    rows: list[dict] = []
    for i in range(100):
        rows.append(_classified_event(
            f"2026-04-25T00:00:{i % 60:02d}.{i:06d}",
            requires_review=(i < 30),  # 30/100 — well above the 5% threshold
        ))
    events.write_text(_events_jsonl(rows))

    findings = audit_rebuild.audit(
        log_path=log, events_log=events, start_utc="2026-04-25T00:00:00",
    )
    assert findings.degradation_pct == 30.0
    assert findings.tracebacks == 0
    assert findings.http_429s == 0
    assert findings.is_clean(), (
        f"high review rate without TPM signals should pass; got failures: {findings.failures}"
    )


def test_high_review_rate_with_tpm_signals_fails(tmp_path: Path) -> None:
    """TPM-induced degradation case: 30% requires_review AND 429s present.
    The pairing is what differentiates real silent degradation from honest
    uncertainty. Reproduces today's workers=8 rebuild profile."""
    log = tmp_path / "rebuild.log"
    log.write_text(
        _clean_log()
        + "Gemini HTTP 429: RESOURCE_EXHAUSTED quota exceeded\n" * 10
    )
    events = tmp_path / "events.jsonl"
    rows: list[dict] = []
    for i in range(100):
        rows.append(_classified_event(
            f"2026-04-25T00:00:{i % 60:02d}.{i:06d}",
            requires_review=(i < 30),
        ))
    events.write_text(_events_jsonl(rows))

    findings = audit_rebuild.audit(
        log_path=log, events_log=events, start_utc="2026-04-25T00:00:00",
    )
    assert findings.degradation_pct == 30.0
    assert findings.http_429s > 0
    assert not findings.is_clean()
    failure_text = " ".join(findings.failures)
    assert "degradation rate" in failure_text
    assert "TPM-pressure signals present" in failure_text


def test_only_tpm_signals_with_low_review_rate_still_fails(tmp_path: Path) -> None:
    """One 429 with 1% review rate is still a hard fail — 429s are hard fails
    on their own (they signal TPM pressure even if it didn't show in review-rate
    yet). The degradation-rate gate is additional, not a substitute."""
    log = tmp_path / "rebuild.log"
    log.write_text(
        _clean_log()
        + "RESOURCE_EXHAUSTED: rate limited\n"
    )
    events = tmp_path / "events.jsonl"
    rows: list[dict] = []
    for i in range(100):
        rows.append(_classified_event(
            f"2026-04-25T00:00:{i % 60:02d}.{i:06d}",
            requires_review=(i < 1),  # 1/100 — below 5% threshold
        ))
    events.write_text(_events_jsonl(rows))

    findings = audit_rebuild.audit(
        log_path=log, events_log=events, start_utc="2026-04-25T00:00:00",
    )
    assert findings.http_429s > 0
    assert findings.degradation_pct == 1.0
    assert not findings.is_clean()  # 429s alone trip the audit
    assert any("HTTP 429" in f or "RESOURCE_EXHAUSTED" in f for f in findings.failures)


def test_main_returns_exit_code_2_on_degradation(tmp_path: Path, capsys) -> None:
    log = tmp_path / "rebuild.log"
    log.write_text("nothing\n")  # no exit marker → silent death
    events = tmp_path / "events.jsonl"
    events.write_text("")

    rc = audit_rebuild.main([
        "--log", str(log),
        "--events-log", str(events),
        "--start-utc", "2026-04-25T00:00:00",
    ])
    assert rc == 2
    captured = capsys.readouterr()
    assert "VERDICT: degraded" in captured.out


def test_main_returns_exit_code_0_on_clean(tmp_path: Path, capsys) -> None:
    log = tmp_path / "rebuild.log"
    log.write_text(_clean_log())
    events = tmp_path / "events.jsonl"
    events.write_text(_events_jsonl([_classified_event("2026-04-25T00:00:01", False)]))

    rc = audit_rebuild.main([
        "--log", str(log),
        "--events-log", str(events),
        "--start-utc", "2026-04-25T00:00:00",
    ])
    assert rc == 0
    assert "VERDICT: clean" in capsys.readouterr().out


def test_invalid_start_utc_raises_argparse_error(tmp_path: Path) -> None:
    log = tmp_path / "rebuild.log"
    log.write_text("")
    with pytest.raises(SystemExit):
        audit_rebuild.main([
            "--log", str(log),
            "--events-log", str(tmp_path / "events.jsonl"),
            "--start-utc", "not-an-iso-timestamp",
        ])


def test_json_output_round_trips(tmp_path: Path, capsys) -> None:
    log = tmp_path / "rebuild.log"
    log.write_text(_clean_log())
    events = tmp_path / "events.jsonl"
    events.write_text(_events_jsonl([_classified_event("2026-04-25T00:00:01", False)]))

    audit_rebuild.main([
        "--log", str(log),
        "--events-log", str(events),
        "--start-utc", "2026-04-25T00:00:00",
        "--json",
    ])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["verdict"] == "clean"
    assert parsed["classified_total"] == 1
    assert parsed["failures"] == []
