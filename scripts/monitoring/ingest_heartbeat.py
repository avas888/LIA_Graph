#!/usr/bin/env python3
"""Long-running ingest heartbeat renderer.

Reusable monitor for any Lia_Graph background process that emits
``ingest.delta.*`` events to ``logs/events.jsonl``. Reads events, computes
progress / rate / ETA, polls Supabase + Falkor for live row counts, and
prints a single markdown heartbeat block to stdout.

Designed to be invoked from a Claude Code cron job every ~3 minutes. The
caller decides, based on ``STATE_FINAL`` in the first data line, whether
to stop the loop. This script never blocks and never exits non-zero on
in-progress states.

All user-facing times render as **Bogotá AM/PM** (``America/Bogota``,
UTC-5 fixed, no DST) per repo convention. Machine comparisons (event
timestamp filtering) stay in UTC.

Usage
-----
    set -a; source .env.staging; set +a
    PYTHONPATH=src:. uv run --group dev python scripts/monitoring/ingest_heartbeat.py \
        --delta-id delta_20260423_170209_322c84 \
        --start-utc 2026-04-23T17:02:09 \
        --total 1280 \
        --title "Phase 9.A Reingest (force-full)" \
        --supa-base-docs 6730 \
        --supa-base-chunks 19507 \
        --falk-base-article 8106

Output (stdout) is the full markdown heartbeat block; the FIRST line is a
machine-parseable status line of the form::

    STATE=<running|STOPPED>|PHASE=<...>|RUN_DONE=<True|False>|RUN_FAILED=<True|False>|ERRORS=<int>

so the caller can grep it for transition decisions.

State machine
-------------
``PHASE`` walks the ingest pipeline end-to-end:

- ``startup``                       — process alive, no classified events yet
- ``classifying``                   — subtopic classifier consuming docs
- ``classifier_done_waiting_sink``  — classifier hit TOTAL, sink not started
- ``sink_writing``                  — Supabase sink in progress
- ``post_sink``                     — sink done, Falkor not started
- ``falkor_writing``                — Falkor graph writes in progress
- ``finalizing``                    — Falkor done, run.done not yet emitted
- ``complete``                      — cli.done event seen (success)
- ``failed``                        — run.failed event or ERRORS > 0
- (caller infers ``crashed`` when process is gone + no complete/failed event)

Silence tolerance: ``sink_writing`` and ``falkor_writing`` legitimately
emit no per-item events (single start/done pair each), so freshness > 3min
during those phases is NOT a stall. Only ``classifying`` should tick
continuously.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

BOG = timezone(timedelta(hours=-5))  # America/Bogota, fixed, no DST


def bog_time(dt: datetime) -> str:
    return dt.astimezone(BOG).strftime("%-I:%M:%S %p").lstrip("0")


def bog_time_short(dt: datetime) -> str:
    return dt.astimezone(BOG).strftime("%-I:%M %p").lstrip("0")


@dataclass
class EventStats:
    done: int = 0
    last_ts: str = ""
    sink_started: int = 0
    sink_done: int = 0
    falkor_started: int = 0
    falkor_done: int = 0
    run_done: bool = False
    run_failed: bool = False
    errors: int = 0


def scan_events(events_log: Path, start_utc: str, delta_id: str) -> EventStats:
    """Walk ``events.jsonl`` once, counting the events we care about for
    this delta / starting after this UTC timestamp.

    We scope to ``delta_id`` where the event carries it (run, plan, sink,
    falkor events) and fall back to the time window for per-item
    ``subtopic.ingest.classified`` events (which don't carry delta_id).
    """
    stats = EventStats()
    if not events_log.exists():
        return stats
    with events_log.open() as f:
        for line in f:
            try:
                event = json.loads(line)
            except Exception:
                continue
            ts = event.get("ts_utc", "")
            if not ts or ts < start_utc:
                continue
            event_type = event.get("event_type", "")
            payload = event.get("payload") or {}
            # Per-item classifier events (no delta_id on payload)
            if event_type == "subtopic.ingest.classified":
                stats.last_ts = ts
                stats.done += 1
                continue
            # Delta-scoped lifecycle events
            if payload.get("delta_id") and payload["delta_id"] != delta_id:
                continue
            stats.last_ts = ts
            if event_type == "ingest.delta.sink.start":
                stats.sink_started += 1
            elif event_type == "ingest.delta.sink.done":
                stats.sink_done += 1
            elif event_type == "ingest.delta.falkor.start":
                stats.falkor_started += 1
            elif event_type == "ingest.delta.falkor.done":
                stats.falkor_done += 1
            elif event_type == "ingest.delta.cli.done":
                stats.run_done = True
            elif event_type == "ingest.delta.run.failed":
                stats.run_failed = True
            if (
                "error" in event_type
                or "failed" in event_type
                or "exception" in event_type
            ):
                stats.errors += 1
    return stats


@dataclass
class ProcessInfo:
    pid: str | None
    etime: str
    etime_seconds: int


def inspect_process(process_grep: str) -> ProcessInfo:
    pids = (
        subprocess.run(
            ["pgrep", "-f", process_grep], capture_output=True, text=True
        ).stdout.split()
    )
    if not pids:
        return ProcessInfo(pid=None, etime="n/a", etime_seconds=0)
    pid = pids[0]
    etime = subprocess.run(
        ["ps", "-p", pid, "-o", "etime="], capture_output=True, text=True
    ).stdout.strip()
    etime_seconds = 0
    for piece in etime.split(":"):
        try:
            etime_seconds = etime_seconds * 60 + int(piece)
        except ValueError:
            etime_seconds = 0
            break
    return ProcessInfo(pid=pid, etime=etime, etime_seconds=etime_seconds)


def infer_phase(stats: EventStats, total: int, process_alive: bool) -> str:
    if stats.run_done:
        return "complete"
    if stats.run_failed or stats.errors > 0:
        return "failed"
    if stats.falkor_started and not stats.falkor_done:
        return "falkor_writing"
    if stats.falkor_done and not stats.run_done:
        return "finalizing"
    if stats.sink_started and not stats.sink_done:
        return "sink_writing"
    if stats.sink_done and process_alive:
        return "post_sink"
    if stats.done >= total and stats.sink_started == 0:
        return "classifier_done_waiting_sink"
    if 1 <= stats.done < total:
        return "classifying"
    return "startup"


def supabase_counts(target: str) -> tuple[int, int, int] | None:
    """Return (docs, chunks, embedding_null_count) or None if unavailable.

    Requires .env.staging to be sourced into the environment before the
    caller invokes this script — we import lazily so the script can at
    least render progress without cloud creds.
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
        from lia_graph.supabase_client import create_supabase_client_for_target  # noqa: E402
    except Exception as exc:  # pragma: no cover — environment probe
        print(f"# supabase_counts: import failed: {exc}", file=sys.stderr)
        return None
    try:
        client = create_supabase_client_for_target(target)
        docs = client.table("documents").select("doc_id", count="exact").execute().count
        chunks = (
            client.table("document_chunks")
            .select("chunk_id", count="exact")
            .execute()
            .count
        )
        null_embed = (
            client.table("document_chunks")
            .select("chunk_id", count="exact")
            .is_("embedding", "null")
            .execute()
            .count
        )
    except Exception as exc:  # pragma: no cover
        print(f"# supabase_counts: query failed: {exc}", file=sys.stderr)
        return None
    return int(docs or 0), int(chunks or 0), int(null_embed or 0)


def falkor_counts() -> tuple[int, int, int, int, int] | None:
    """Return (Article, Topic, Subtopic, TEMA, PRACTICA_DE) or None."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
        from lia_graph.graph.client import GraphClient, GraphWriteStatement  # noqa: E402
    except Exception as exc:  # pragma: no cover
        print(f"# falkor_counts: import failed: {exc}", file=sys.stderr)
        return None

    def q(client: "GraphClient", cypher: str) -> int:
        stmt = GraphWriteStatement(description=cypher, query=cypher, parameters={})
        rows = list(client.execute(stmt, strict=True).rows)
        return int(rows[0]["n"]) if rows else 0

    try:
        client = GraphClient.from_env()
        article = q(client, "MATCH (a:ArticleNode) RETURN count(a) AS n")
        topic = q(client, "MATCH (t:TopicNode) RETURN count(t) AS n")
        subtopic = q(client, "MATCH (s:SubTopicNode) RETURN count(s) AS n")
        tema = q(client, "MATCH ()-[e:TEMA]->() RETURN count(e) AS n")
        practica = q(client, "MATCH ()-[e:PRACTICA_DE]->() RETURN count(e) AS n")
    except Exception as exc:  # pragma: no cover
        print(f"# falkor_counts: query failed: {exc}", file=sys.stderr)
        return None
    return article, topic, subtopic, tema, practica


def render(
    *,
    title: str,
    delta_id: str,
    total: int,
    stats: EventStats,
    process: ProcessInfo,
    phase: str,
    supa: tuple[int, int, int] | None,
    falk: tuple[int, int, int, int, int] | None,
    base_supa_docs: int,
    base_supa_chunks: int,
    base_falk_article: int,
    base_falk_topic: int,
    base_falk_tema: int,
    base_falk_practica: int,
) -> str:
    now = datetime.now(timezone.utc)
    last_dt = (
        datetime.fromisoformat(stats.last_ts.replace("Z", "+00:00"))
        if stats.last_ts
        else None
    )
    fresh = int((now - last_dt).total_seconds()) if last_dt else -1

    rate = stats.done * 60 / process.etime_seconds if process.etime_seconds > 0 else 0.0
    eta_min = (total - stats.done) / rate if rate > 0 and stats.done < total else 0.0
    eta_time = bog_time_short(now + timedelta(minutes=eta_min)) if eta_min > 0 else "—"

    pct = stats.done * 100 / total if total > 0 else 0.0
    bar_len = 30
    filled = min(bar_len, int(bar_len * pct / 100))
    bar = "█" * filled + "░" * (bar_len - filled)

    state = "running" if process.pid else "STOPPED"
    # The machine-parseable status line MUST be first.
    status_line = (
        f"STATE={state}|PHASE={phase}"
        f"|RUN_DONE={stats.run_done}|RUN_FAILED={stats.run_failed}"
        f"|ERRORS={stats.errors}|DELTA_ID={delta_id}"
    )

    last_bog = bog_time(last_dt) if last_dt else "n/a"
    now_bog = bog_time(now)

    # Supabase row
    if supa is not None:
        d, c, e = supa
        supa_row = (
            f"| **Supabase** | `{d} (+{d - base_supa_docs})` "
            f"| `{c} (+{c - base_supa_chunks})` | `{e}` "
            f"| — | — | — | — | — |"
        )
    else:
        supa_row = "| **Supabase** | (unavailable) | | | — | — | — | — | — |"

    # Falkor row
    if falk is not None:
        a, t, s, te, p = falk
        falk_row = (
            f"| **Falkor** | — | — | — "
            f"| `{a} (+{a - base_falk_article})` "
            f"| `{t} (+{t - base_falk_topic})` "
            f"| `{s}` "
            f"| `{te} (+{te - base_falk_tema})` "
            f"| `{p} (+{p - base_falk_practica})` |"
        )
    else:
        falk_row = "| **Falkor** | — | — | — | (unavailable) | | | | |"

    # Verdict
    if phase == "complete":
        verdict = "run.done emitted; caller may stop the loop."
    elif phase == "failed":
        verdict = "run.failed or error events emitted; caller should surface the log and stop."
    elif phase == "classifying":
        note = ""
        if fresh > 180:
            note = " ⚠ classifier possibly stalled"
        verdict = f"classifier at {pct:.1f}%, {rate:.1f} docs/min, ETA {eta_time}{note}."
    elif phase == "classifier_done_waiting_sink":
        note = " ⚠ sink not starting" if fresh > 300 else ""
        verdict = f"classifier hit {total}/{total}; sink phase about to fire{note}."
    elif phase == "sink_writing":
        verdict = "sink writing to Supabase; silence between start/done is expected."
    elif phase == "post_sink":
        verdict = "sink done; Falkor phase should start shortly."
    elif phase == "falkor_writing":
        verdict = "Falkor graph writes in progress; silence is expected."
    elif phase == "finalizing":
        verdict = "Falkor done; waiting for run.done."
    else:
        verdict = f"phase={phase}."

    # Progress bar header
    header_line = f"{bar}  {pct:.1f}%   {stats.done} / {total} docs (classifier)"

    meta_table = "\n".join(
        [
            "| | |",
            "|---|---|",
            f"| **State** | `{state}` · {phase} |",
            f"| **PID / etime** | `{process.pid or '—'}`  ·  `{process.etime}` |",
            f"| **Rate** | `{rate:.1f}` docs/min |",
            f"| **ETA** | `{eta_min:.1f} min` → `{eta_time}` |",
            f"| **Freshness** | `{fresh}s`  ·  last `{last_bog}` |",
            f"| **Sink** | `{stats.sink_started}` started · `{stats.sink_done}` flushed |",
            f"| **Falkor** | `{stats.falkor_started}` started · `{stats.falkor_done}` flushed |",
            f"| **Errors** | `{stats.errors}` |",
        ]
    )

    counts_table_header = (
        "| Backend | Docs | Chunks | Null embed | Articles | Topic | Sub | TEMA | PRAC |\n"
        "|---|---|---|---|---|---|---|---|---|"
    )

    return "\n".join(
        [
            status_line,
            "",
            f"## {title} — Heartbeat ({now_bog})",
            "",
            "```",
            header_line,
            "```",
            "",
            meta_table,
            "",
            counts_table_header,
            supa_row,
            falk_row,
            "",
            f"**Verdict** — {verdict}",
        ]
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--delta-id", required=True, help="Target delta_id for lifecycle events.")
    p.add_argument(
        "--start-utc",
        required=True,
        help="UTC ISO timestamp bracketing the start of this run "
        "(events before this are ignored). Example: 2026-04-23T17:02:09.",
    )
    p.add_argument("--total", type=int, required=True, help="Expected classifier total.")
    p.add_argument("--title", default="Ingest", help="Title shown in the heartbeat header.")
    p.add_argument(
        "--events-log",
        default="logs/events.jsonl",
        help="Path to events.jsonl (default: logs/events.jsonl).",
    )
    p.add_argument(
        "--process-grep",
        default="lia_graph.ingest",
        help="pgrep -f pattern for the running process (default: lia_graph.ingest).",
    )
    p.add_argument(
        "--supabase-target",
        default=os.environ.get("PHASE2_SUPABASE_TARGET", "production"),
        help="Supabase target alias (default: production).",
    )
    p.add_argument("--supa-base-docs", type=int, default=0)
    p.add_argument("--supa-base-chunks", type=int, default=0)
    p.add_argument("--falk-base-article", type=int, default=0)
    p.add_argument("--falk-base-topic", type=int, default=0)
    p.add_argument("--falk-base-tema", type=int, default=0)
    p.add_argument("--falk-base-practica", type=int, default=0)
    p.add_argument(
        "--skip-supabase",
        action="store_true",
        help="Skip the Supabase count query (useful for sandboxed envs).",
    )
    p.add_argument(
        "--skip-falkor",
        action="store_true",
        help="Skip the Falkor count query.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    events_log = Path(args.events_log)

    stats = scan_events(events_log, args.start_utc, args.delta_id)
    process = inspect_process(args.process_grep)
    phase = infer_phase(stats, args.total, process.pid is not None)

    supa = None if args.skip_supabase else supabase_counts(args.supabase_target)
    falk = None if args.skip_falkor else falkor_counts()

    out = render(
        title=args.title,
        delta_id=args.delta_id,
        total=args.total,
        stats=stats,
        process=process,
        phase=phase,
        supa=supa,
        falk=falk,
        base_supa_docs=args.supa_base_docs,
        base_supa_chunks=args.supa_base_chunks,
        base_falk_article=args.falk_base_article,
        base_falk_topic=args.falk_base_topic,
        base_falk_tema=args.falk_base_tema,
        base_falk_practica=args.falk_base_practica,
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
