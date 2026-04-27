#!/usr/bin/env python3
"""Canonicalizer batch heartbeat — verbose, fully visible.

Renders a single markdown block describing the live state of one
canonicalizer batch run (per `docs/re-engineer/canonicalizer_runv1.md`).
Designed to be invoked from a Claude Code cron job every 3 minutes; the
caller decides, based on ``STATE=...`` in the first data line, whether
to stop the loop.

Reads ``logs/events.jsonl`` filtered by ``--run-id`` (each event from
``scripts/canonicalizer/extract_vigencia.py`` carries ``run_id``). Fields rendered:

  * batch_id / run_id / wall clock + elapsed (Bogotá AM/PM)
  * progress: norms processed / total / percent + ETA
  * state breakdown: V / VM / EC / DE / IE / SP / DT / RV / VL / DI counts
  * volume: successes, refusals, errors, skipped, pending
  * last N norms (most-recent-first table)
  * freshness: last event age (FRESH ≤ 180 s, STALE 180–600 s, FROZEN > 600 s)
  * kill-switch checks (process alive, cli.done, run.failed, errors > 0,
    refusal rate > 25 %)
  * output dir snapshot (file count)

The FIRST line of stdout is machine-parseable::

    STATE=<running|complete|failed|stalled>|PHASE=<startup|extracting|complete|failed>|RUN_DONE=<True|False>|RUN_FAILED=<True|False>|ERRORS=<int>|REFUSALS=<int>|SUCCESS=<int>|PENDING=<int>|FRESH_SEC=<int>

so the heartbeat cron can grep transitions without parsing markdown.

Usage
-----
    PYTHONPATH=src:. uv run python scripts/canonicalizer/heartbeat.py \\
        --batch-id A1 \\
        --run-id canonicalizer-A1-20260428T010000Z \\
        --start-utc 2026-04-28T01:00:00 \\
        --pid 23456                   # optional, used by kill-switch check

If ``--total`` is omitted, it is derived from the batch_id slice resolution
(reads `config/canonicalizer_run_v1/batches.yaml` + the corpus input set).

All Bogotá times are computed via a fixed UTC-5 offset (no DST). Machine
event filtering uses UTC timestamps in ``events.jsonl``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BOG = timezone(timedelta(hours=-5))  # America/Bogota fixed, no DST
FRESH_SEC = 180     # ≤ this → FRESH ✅
STALE_SEC = 600     # > this → FROZEN ⛔ (between is STALE ⚠)
REFUSAL_RATE_LIMIT = 0.25
DEFAULT_TAIL_ROWS = 8

# Vigencia state palette (canonicalizer doc §3 + state_fixplan_v3 §0.5).
STATES_ORDER = ["V", "VM", "EC", "VC", "DT", "DE", "IE", "SP", "RV", "VL", "DI"]
STATE_LABEL = {
    "V": "vigente",
    "VM": "vigente, modificada",
    "EC": "exequible condicional",
    "VC": "vigente con cond.",
    "DT": "derogación tácita",
    "DE": "derogada expresa",
    "IE": "inexequible",
    "SP": "suspendida prov.",
    "RV": "revivida",
    "VL": "vigencia limitada",
    "DI": "derogación implícita",
}


@dataclass
class EventStats:
    started: bool = False
    done: bool = False
    failed: bool = False
    last_ts_iso: str = ""
    successes: int = 0
    refusals: int = 0
    errors: int = 0
    skipped: int = 0
    state_counts: Counter = field(default_factory=Counter)
    refusal_reasons: Counter = field(default_factory=Counter)
    error_messages: list[str] = field(default_factory=list)
    tail: list[dict[str, Any]] = field(default_factory=list)
    cli_done_summary: dict[str, Any] = field(default_factory=dict)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--batch-id", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--start-utc", required=True,
                   help="ISO timestamp the run started (UTC). Used for elapsed/ETA.")
    p.add_argument("--total", type=int, default=None,
                   help="Total norms in the batch slice. If omitted, resolved via the YAML.")
    p.add_argument("--events-log", default="logs/events.jsonl")
    p.add_argument("--output-dir", default=None,
                   help="Per-batch JSON output dir. Defaults to evals/vigencia_extraction_v1/<batch_id>.")
    p.add_argument("--batches-config",
                   default="config/canonicalizer_run_v1/batches.yaml")
    p.add_argument("--corpus-input-set",
                   default="evals/vigencia_extraction_v1/input_set.jsonl")
    p.add_argument("--pid", type=int, default=None,
                   help="Optional pid of the extract process for liveness check.")
    p.add_argument("--tail", type=int, default=DEFAULT_TAIL_ROWS,
                   help="How many recent norm events to render in the tail table.")
    p.add_argument("--quiet-state-line", action="store_true",
                   help="Suppress the leading STATE=... machine line (testing).")
    p.add_argument("--stats-out", default=None,
                   help="Optional path to write the JSON stats snapshot. "
                        "Defaults to evals/canonicalizer_run_v1/<batch_id>/heartbeat_stats.json.")
    p.add_argument("--no-stats-file", action="store_true",
                   help="Skip writing the stats snapshot file.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    start_utc = _parse_utc(args.start_utc)
    now_utc = datetime.now(timezone.utc)
    elapsed = now_utc - start_utc

    batch_meta = _load_batch_meta(Path(args.batches_config), args.batch_id)
    total = args.total or _resolve_total(args, batch_meta)

    events_path = Path(args.events_log)
    stats = _scan_events(events_path, args.run_id, start_utc)

    output_dir = Path(args.output_dir or f"evals/vigencia_extraction_v1/{args.batch_id}")
    files_written = len(list(output_dir.glob("*.json"))) if output_dir.is_dir() else 0

    process_alive = _is_alive(args.pid) if args.pid else None

    fresh_sec = _freshness_seconds(stats.last_ts_iso, now_utc)
    phase = _derive_phase(stats, total)
    state = _derive_state(stats, phase, process_alive, fresh_sec, args.pid is not None)

    processed = stats.successes + stats.refusals + stats.errors
    pending = max(0, total - processed - stats.skipped)
    rate_per_sec = _compute_rate(processed, elapsed)
    eta_str = _format_eta(pending, rate_per_sec, now_utc)
    pct = pct_or_zero(processed, total)

    refusal_rate = (stats.refusals / max(1, processed))

    if not args.quiet_state_line:
        print(
            f"STATE={state}|PHASE={phase}|RUN_DONE={stats.done}|RUN_FAILED={stats.failed}"
            f"|ERRORS={stats.errors}|REFUSALS={stats.refusals}|SUCCESS={stats.successes}"
            f"|PENDING={pending}|FRESH_SEC={fresh_sec}"
        )

    headline_stats = (
        f"{processed}/{total} done · {pct:.1f}% · "
        f"{stats.successes} ✅ · {stats.refusals} 🛑 · {stats.errors} ❌ · "
        f"ETA {eta_str} · {rate_per_sec:.2f} norms/sec"
    )

    out_lines: list[str] = []
    title = (batch_meta or {}).get("title") or args.batch_id
    out_lines.append(f"# Canonicalizer heartbeat — {args.batch_id} · {title}")
    out_lines.append("")
    out_lines.append(f"**Stats:** {headline_stats}")
    out_lines.append("")
    out_lines.append(f"**run_id:** `{args.run_id}`  ")
    out_lines.append(f"**Wall clock:** {_bog_now(now_utc)}  ")
    out_lines.append(
        f"**Started:** {_bog_now(start_utc)}  ·  "
        f"**Elapsed:** {_format_duration(elapsed)}"
    )
    out_lines.append("")

    # Progress block ──
    bar = _ascii_bar(pct, width=40)
    out_lines.append("## Progress")
    out_lines.append("")
    out_lines.append(
        f"`{bar}` {pct:5.1f}%  ({processed} / {total} norms)"
    )
    out_lines.append("")
    out_lines.append(f"- ETA: {eta_str}")
    out_lines.append(f"- Rate: {rate_per_sec:.2f} norms/sec  ({rate_per_sec * 60:.1f} norms/min)")
    out_lines.append(f"- Wall target: {(batch_meta or {}).get('wall_minutes_target', '—')} min")
    out_lines.append("")

    # State breakdown ──
    out_lines.append("## State breakdown (verified veredictos)")
    out_lines.append("")
    out_lines.append("| State | Label | Count | % |")
    out_lines.append("|---|---|---:|---:|")
    total_states = sum(stats.state_counts.values())
    for s in STATES_ORDER:
        c = stats.state_counts.get(s, 0)
        pct_s = (c / total_states * 100) if total_states else 0.0
        out_lines.append(f"| {s} | {STATE_LABEL[s]} | {c} | {pct_s:5.1f}% |")
    other = total_states - sum(stats.state_counts.get(s, 0) for s in STATES_ORDER)
    if other > 0:
        out_lines.append(f"| (other) | unknown | {other} | — |")
    out_lines.append("")

    # Volume ──
    out_lines.append("## Volume")
    out_lines.append("")
    out_lines.append(f"- Successes: **{stats.successes}**")
    out_lines.append(f"- Refusals: **{stats.refusals}** (rate {refusal_rate * 100:.1f}%)")
    out_lines.append(f"- Errors: **{stats.errors}**")
    out_lines.append(f"- Skipped (resume): {stats.skipped}")
    out_lines.append(f"- Pending: **{pending}**")
    out_lines.append(f"- JSONs on disk ({output_dir}): {files_written}")
    out_lines.append("")

    if stats.refusal_reasons:
        out_lines.append("**Top refusal reasons**")
        out_lines.append("")
        for reason, count in stats.refusal_reasons.most_common(5):
            out_lines.append(f"- `{reason}`: {count}")
        out_lines.append("")

    if stats.error_messages:
        out_lines.append("**Recent error messages**")
        out_lines.append("")
        for msg in stats.error_messages[-5:]:
            out_lines.append(f"- `{msg[:120]}`")
        out_lines.append("")

    # Tail ──
    out_lines.append(f"## Last {args.tail} norms")
    out_lines.append("")
    if stats.tail:
        out_lines.append("| Time (Bogotá) | norm_id | outcome | state / reason |")
        out_lines.append("|---|---|---|---|")
        for ev in stats.tail[-args.tail:][::-1]:
            ts_str = _bog_event_ts(ev.get("ts", ""))
            kind = ev.get("kind", "")
            outcome = kind.replace("norm.", "")
            detail = ev.get("state") or ev.get("reason") or ev.get("error") or ""
            detail = str(detail)[:80]
            out_lines.append(
                f"| {ts_str} | `{ev.get('norm_id', '?')}` | {outcome} | {detail} |"
            )
    else:
        out_lines.append("_No per-norm events yet for this run_id._")
    out_lines.append("")

    # Freshness ──
    out_lines.append("## Freshness")
    out_lines.append("")
    fresh_label = _fresh_label(fresh_sec)
    last_event_str = _bog_event_ts(stats.last_ts_iso) if stats.last_ts_iso else "—"
    out_lines.append(f"- Last event: {last_event_str}")
    out_lines.append(f"- Age: {fresh_sec} s ({fresh_label})")
    out_lines.append("")

    # Kill-switches ──
    out_lines.append("## Kill-switches")
    out_lines.append("")
    if args.pid is not None:
        out_lines.append(f"- Process pid {args.pid} alive: {'✅ yes' if process_alive else '❌ no'}")
    else:
        out_lines.append("- Process pid: _not provided_ (cannot check liveness)")
    out_lines.append(f"- cli.done seen: {'✅ yes' if stats.done else 'no'}")
    out_lines.append(f"- run.failed seen: {'❌ yes' if stats.failed else 'no'}")
    out_lines.append(f"- Errors > 0: {'❌ yes' if stats.errors > 0 else 'no'}")
    refusal_flag = "❌ yes" if refusal_rate > REFUSAL_RATE_LIMIT and (stats.successes + stats.refusals + stats.errors) >= 8 else "no"
    out_lines.append(
        f"- Refusal rate > {REFUSAL_RATE_LIMIT * 100:.0f}%: {refusal_flag}"
    )
    out_lines.append("")

    # Stop guidance for the cron loop ──
    out_lines.append("## Stop guidance (for the cron loop)")
    out_lines.append("")
    if state == "complete":
        out_lines.append("- ✅ **STOP loop.** `cli.done` fired.")
        out_lines.append(f"- Summary: {json.dumps(stats.cli_done_summary, ensure_ascii=False)}")
        out_lines.append("- Next: run `scripts/canonicalizer/ingest_vigencia_veredictos.py --target wip --input-dir "
                         f"{output_dir} --run-id {args.run_id} --extracted-by ingest@v1`.")
    elif state == "failed":
        out_lines.append("- ❌ **STOP loop.** Failure detected — surface events and log to operator.")
    elif state == "stalled":
        out_lines.append("- ⚠ **STOP loop.** Process appears dead with no `cli.done`. Do NOT retry blindly; inspect `logs/canonicalizer_<batch>.log` and `logs/events.jsonl`.")
    else:
        out_lines.append("- 🟢 **CONTINUE loop.** Re-run heartbeat in 3 min.")
    out_lines.append("")

    sys.stdout.write("\n".join(out_lines) + "\n")
    sys.stdout.flush()

    # ── Persist a JSON snapshot so downstream tools / dashboards can read
    # the latest stats without parsing markdown.
    if not args.no_stats_file:
        stats_path = Path(
            args.stats_out
            or f"evals/canonicalizer_run_v1/{args.batch_id}/heartbeat_stats.json"
        )
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot = {
            "ts_utc": now_utc.isoformat(),
            "ts_bogota": _bog_now(now_utc),
            "batch_id": args.batch_id,
            "run_id": args.run_id,
            "phase": phase,
            "state": state,
            "headline": headline_stats,
            "total": total,
            "processed": processed,
            "pending": pending,
            "skipped": stats.skipped,
            "successes": stats.successes,
            "refusals": stats.refusals,
            "errors": stats.errors,
            "percent": round(pct, 2),
            "rate_norms_per_sec": round(rate_per_sec, 4),
            "rate_norms_per_min": round(rate_per_sec * 60, 2),
            "eta": eta_str,
            "elapsed": _format_duration(elapsed),
            "elapsed_seconds": int(elapsed.total_seconds()),
            "fresh_seconds": fresh_sec,
            "fresh_label": _fresh_label(fresh_sec),
            "last_event_ts_utc": stats.last_ts_iso,
            "state_counts": dict(stats.state_counts),
            "refusal_reasons_top": dict(stats.refusal_reasons.most_common(5)),
            "errors_recent": stats.error_messages[-5:],
            "files_written": files_written,
            "process_alive": process_alive,
            "cli_done_summary": stats.cli_done_summary,
            "refusal_rate": round(refusal_rate, 4),
        }
        tmp_path = stats_path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(stats_path)  # atomic

    return 0


def pct_or_zero(n: int, d: int) -> float:
    return (n / d * 100) if d else 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scan_events(path: Path, run_id: str, start_utc: datetime) -> EventStats:
    stats = EventStats()
    if not path.is_file():
        return stats
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if str(ev.get("run_id") or "") != run_id:
                continue
            ts = str(ev.get("ts") or "")
            ev_dt = _try_parse_iso(ts)
            if ev_dt is not None and ev_dt < start_utc - timedelta(seconds=5):
                continue
            kind = str(ev.get("kind") or "")
            stats.last_ts_iso = ts or stats.last_ts_iso
            if kind == "run.started":
                stats.started = True
            elif kind == "norm.success":
                stats.successes += 1
                state = str(ev.get("state") or "").upper().strip()
                if state:
                    stats.state_counts[state] += 1
                stats.tail.append(ev)
            elif kind == "norm.refusal":
                stats.refusals += 1
                reason = str(ev.get("reason") or "unspecified")
                stats.refusal_reasons[reason] += 1
                stats.tail.append(ev)
            elif kind == "norm.error":
                stats.errors += 1
                err_msg = str(ev.get("error") or "")
                if err_msg:
                    stats.error_messages.append(err_msg)
                stats.tail.append(ev)
            elif kind == "cli.done":
                stats.done = True
                stats.cli_done_summary = {
                    k: ev.get(k) for k in ("successes", "refusals", "errors", "skipped")
                    if ev.get(k) is not None
                }
            elif kind == "run.failed":
                stats.failed = True
            elif kind == "norm.skipped":
                stats.skipped += 1
    return stats


def _derive_phase(stats: EventStats, total: int) -> str:
    if stats.failed:
        return "failed"
    if stats.done:
        return "complete"
    if stats.successes + stats.refusals + stats.errors == 0:
        return "startup"
    return "extracting"


def _derive_state(
    stats: EventStats,
    phase: str,
    process_alive: bool | None,
    fresh_sec: int,
    pid_provided: bool,
) -> str:
    if phase == "complete":
        return "complete"
    if phase == "failed":
        return "failed"
    if pid_provided and process_alive is False and not stats.done:
        return "stalled"
    if fresh_sec > STALE_SEC and stats.successes + stats.refusals + stats.errors > 0:
        return "stalled"
    return "running"


def _freshness_seconds(last_ts_iso: str, now_utc: datetime) -> int:
    if not last_ts_iso:
        return 10 ** 9  # effectively "never"
    dt = _try_parse_iso(last_ts_iso)
    if dt is None:
        return 10 ** 9
    return max(0, int((now_utc - dt).total_seconds()))


def _fresh_label(sec: int) -> str:
    if sec >= 10 ** 8:
        return "no events yet"
    if sec <= FRESH_SEC:
        return f"FRESH ✅ (≤ {FRESH_SEC}s)"
    if sec <= STALE_SEC:
        return f"STALE ⚠ ({FRESH_SEC}–{STALE_SEC}s)"
    return f"FROZEN ⛔ (> {STALE_SEC}s)"


def _try_parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    # Accept "2026-04-28T01:00:00+00:00", "...Z", or naïve.
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_utc(s: str) -> datetime:
    dt = _try_parse_iso(s)
    if dt is None:
        raise SystemExit(f"--start-utc not parseable: {s!r}")
    return dt


def _bog_now(dt: datetime) -> str:
    return dt.astimezone(BOG).strftime("%Y-%m-%d %I:%M:%S %p Bogotá").replace(" 0", " ")


def _bog_event_ts(s: str) -> str:
    dt = _try_parse_iso(s)
    if dt is None:
        return s or "—"
    return dt.astimezone(BOG).strftime("%I:%M:%S %p").lstrip("0")


def _format_duration(td: timedelta) -> str:
    secs = int(td.total_seconds())
    h, r = divmod(secs, 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    return f"{m}m {s:02d}s"


def _format_eta(pending: int, rate_per_sec: float, now: datetime) -> str:
    if pending <= 0:
        return "—"
    if rate_per_sec <= 0:
        return "computing (no rate yet)"
    remaining_sec = pending / rate_per_sec
    eta = now + timedelta(seconds=remaining_sec)
    eta_str = eta.astimezone(BOG).strftime("%I:%M %p Bogotá").lstrip("0")
    mins = int(remaining_sec // 60)
    return f"{eta_str} (~{mins} min remaining)"


def _compute_rate(processed: int, elapsed: timedelta) -> float:
    sec = elapsed.total_seconds()
    if sec <= 0:
        return 0.0
    return processed / sec


def _ascii_bar(pct: float, width: int = 40) -> str:
    pct = max(0.0, min(100.0, pct))
    filled = int(round(pct / 100 * width))
    return "█" * filled + "░" * (width - filled)


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _load_batch_meta(config_path: Path, batch_id: str) -> dict[str, Any] | None:
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    if not config_path.is_file():
        return None
    try:
        blobs = yaml.safe_load(config_path.read_text(encoding="utf-8")) or []
    except Exception:
        return None
    for b in blobs:
        if str(b.get("batch_id") or "").strip() == batch_id:
            return b
    return None


def _resolve_total(args: argparse.Namespace, batch_meta: dict[str, Any] | None) -> int:
    """Resolve the batch's expected norm count by replaying the same filter
    logic used by ``scripts/canonicalizer/extract_vigencia.py``. Cheap (sub-second) and
    avoids drift between the two tools."""

    if not batch_meta:
        return 0
    nf = batch_meta.get("norm_filter") or {}
    kind = str(nf.get("type") or "").strip()
    if kind == "explicit_list":
        return len(nf.get("norm_ids") or [])
    corpus_path = Path(args.corpus_input_set)
    if not corpus_path.is_file():
        return 0
    norm_ids: list[str] = []
    with corpus_path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                blob = json.loads(raw)
            except json.JSONDecodeError:
                continue
            nid = str(blob.get("norm_id") or "").strip()
            if nid:
                norm_ids.append(nid)
    if kind == "prefix":
        prefix = str(nf.get("prefix") or "")
        return sum(1 for n in norm_ids if n.startswith(prefix))
    if kind == "regex":
        pat = re.compile(str(nf.get("pattern") or ""))
        return sum(1 for n in norm_ids if pat.search(n))
    if kind == "et_article_range":
        lo = str(nf.get("from") or "")
        hi = str(nf.get("to") or "")
        def _key(nid: str) -> tuple[int, int]:
            tail = nid[len("et.art."):] if nid.startswith("et.art.") else nid
            head, _, _ = tail.partition(".")
            major, _, minor = head.partition("-")
            try:
                return (int(major), int(minor or 0))
            except ValueError:
                return (-1, -1)
        lo_k = _key(f"et.art.{lo}")
        hi_k = _key(f"et.art.{hi}")
        return sum(
            1
            for n in norm_ids
            if n.startswith("et.art.") and lo_k <= _key(n) <= hi_k and _key(n) != (-1, -1)
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
