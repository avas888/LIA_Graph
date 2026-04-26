#!/usr/bin/env python3
"""next_v4 §3 / §4 — multi-turn dialogue harness.

Scripts T1→T2 (and T3+) against a single `session_id` over the running
`/api/chat` HTTP endpoint, captures `response.diagnostics` per turn, and
aggregates the refusal-rate-via-coherence-gate metric the v4 plan calls for.

The existing `run_ab_comparison.py` is single-turn and in-process — both
properties make it useless for measuring the stateless-classifier vs
stateful-retriever interaction this harness exists to characterize. The
mechanism only fires when persistence + conversation_state actually thread
across turns, which is server-side behavior.

Usage
-----
    # 1. start a server (any of the three modes)
    npm run dev          # local artifact mode
    npm run dev:staging  # cloud mode (closer to gate-4 conditions)

    # 2. run the harness against it
    PYTHONPATH=src:. uv run python scripts/evaluations/run_multiturn_dialogue_harness.py \\
        --fixture evals/multiturn_dialogue_v1.jsonl \\
        --base-url http://localhost:5173 \\
        --output-dir artifacts/eval

Output: one JSONL row per dialogue (each row contains a list of per-turn
diagnostics) + a `_summary.json` with aggregate refusal rate, plus a
`_manifest.json` mirroring run_ab_comparison's manifest contract.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# ── Time helpers (Bogotá AM/PM for user surfaces, UTC ISO for machines) ──

_BOGOTA = _dt.timezone(_dt.timedelta(hours=-5))


def _bogota_now() -> str:
    return _dt.datetime.now(_BOGOTA).strftime("%Y-%m-%d %-I:%M:%S %p").lstrip("0")


def _utc_iso_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


# ── Fixture loader ───────────────────────────────────────────────────────


def _load_fixture(path: Path) -> list[dict[str, Any]]:
    """Each row: {did, anchor_topic, ambiguous_verb, turns: [str, ...]}."""
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise SystemExit(
                    f"[run_multiturn_dialogue_harness] {path} line {lineno} invalid JSON: {exc}"
                )
            if not isinstance(row, dict):
                raise SystemExit(f"[run_multiturn_dialogue_harness] {path} line {lineno} not an object")
            turns = row.get("turns")
            if not isinstance(turns, list) or len(turns) < 2:
                raise SystemExit(
                    f"[run_multiturn_dialogue_harness] {path} line {lineno} 'turns' must be a list of length >= 2"
                )
            rows.append(row)
    return rows


# ── HTTP helpers ─────────────────────────────────────────────────────────


def _post_json(
    url: str,
    body: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 90.0,
) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = Request(url, data=data, headers=req_headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"_raw_body": raw}
            return int(resp.status), payload if isinstance(payload, dict) else {"_raw_body": raw}
    except HTTPError as exc:
        try:
            body_text = exc.read().decode("utf-8")
        except Exception:  # noqa: BLE001
            body_text = ""
        try:
            payload = json.loads(body_text) if body_text else {}
        except json.JSONDecodeError:
            payload = {"_raw_body": body_text}
        return int(exc.code), payload if isinstance(payload, dict) else {"_raw_body": body_text}


def _create_public_session(base_url: str) -> str:
    status, payload = _post_json(f"{base_url}/api/public/session", {})
    if status != 200 or not payload.get("ok"):
        raise SystemExit(
            f"[run_multiturn_dialogue_harness] /api/public/session failed: status={status} payload={payload}"
        )
    token = str(payload.get("token") or "").strip()
    if not token:
        raise SystemExit("[run_multiturn_dialogue_harness] session token missing in response")
    return token


# ── Per-turn capture ─────────────────────────────────────────────────────


@dataclass
class TurnResult:
    turn_num: int  # 1-indexed
    message: str
    sent_topic: str | None  # what `topic` field carried in the request, if any
    http_status: int
    session_id: str | None
    chat_run_id: str | None
    trace_id: str | None
    answer_markdown: str
    requested_topic: str | None
    effective_topic: str | None
    secondary_topics: list[str]
    topic_router_mode: str | None
    topic_router_confidence: float | None
    coherence_mode: str | None
    coherence_misaligned: bool | None
    coherence_reason: str | None
    coherence_dominant_topic: str | None
    refused: bool
    retrieval_backend: str | None
    graph_backend: str | None
    primary_article_count: int
    seed_article_keys: list[str]
    wall_ms: int


def _extract_turn_diagnostics(
    *,
    turn_num: int,
    message: str,
    sent_topic: str | None,
    http_status: int,
    payload: dict[str, Any],
    wall_ms: int,
) -> TurnResult:
    diag = payload.get("diagnostics") or {}
    if not isinstance(diag, dict):
        diag = {}
    topic_safety = diag.get("topic_safety") or {}
    if not isinstance(topic_safety, dict):
        topic_safety = {}
    coherence = topic_safety.get("coherence") if isinstance(topic_safety, dict) else None
    if not isinstance(coherence, dict):
        coherence = {}

    refused_flag = bool(coherence.get("misaligned")) and (
        str(coherence.get("mode") or "").strip().lower() == "enforce"
    )

    return TurnResult(
        turn_num=turn_num,
        message=message,
        sent_topic=sent_topic,
        http_status=http_status,
        session_id=str(payload.get("session_id") or "").strip() or None,
        chat_run_id=str(payload.get("chat_run_id") or "").strip() or None,
        trace_id=str(payload.get("trace_id") or "").strip() or None,
        answer_markdown=str(payload.get("answer_markdown") or "")[:4000],
        requested_topic=payload.get("requested_topic"),
        effective_topic=payload.get("effective_topic"),
        secondary_topics=list(payload.get("secondary_topics") or []),
        topic_router_mode=topic_safety.get("router_mode"),
        topic_router_confidence=(
            float(topic_safety.get("router_confidence"))
            if isinstance(topic_safety.get("router_confidence"), (int, float))
            else None
        ),
        coherence_mode=coherence.get("mode"),
        coherence_misaligned=coherence.get("misaligned"),
        coherence_reason=coherence.get("reason"),
        coherence_dominant_topic=coherence.get("dominant_topic"),
        refused=refused_flag,
        retrieval_backend=diag.get("retrieval_backend"),
        graph_backend=diag.get("graph_backend"),
        primary_article_count=int(diag.get("primary_article_count") or 0),
        seed_article_keys=list(diag.get("seed_article_keys") or [])[:20],
        wall_ms=wall_ms,
    )


# ── Per-dialogue runner ──────────────────────────────────────────────────


@dataclass
class DialogueOutcome:
    did: str
    anchor_topic: str
    ambiguous_verb: str
    ok: bool
    turns: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


def _run_dialogue(
    *,
    base_url: str,
    fixture_row: dict[str, Any],
    propagate_topic: bool,
    inter_turn_pause_seconds: float,
) -> DialogueOutcome:
    did = str(fixture_row.get("did") or "").strip() or "<missing>"
    anchor = str(fixture_row.get("anchor_topic") or "").strip()
    verb = str(fixture_row.get("ambiguous_verb") or "").strip()
    turns = list(fixture_row.get("turns") or [])

    outcome = DialogueOutcome(
        did=did,
        anchor_topic=anchor,
        ambiguous_verb=verb,
        ok=False,
    )

    try:
        token = _create_public_session(base_url)
    except SystemExit as exc:
        outcome.error = str(exc)
        return outcome

    auth_headers = {"Authorization": f"Bearer {token}"}
    session_id: str | None = None
    last_effective_topic: str | None = None

    for idx, turn_text in enumerate(turns, start=1):
        body: dict[str, Any] = {
            "message": str(turn_text or "").strip(),
            "pais": "colombia",
        }
        if session_id:
            body["session_id"] = session_id
        sent_topic: str | None = None
        if propagate_topic and idx > 1 and last_effective_topic:
            body["topic"] = last_effective_topic
            sent_topic = last_effective_topic

        t0 = time.perf_counter()
        try:
            status, payload = _post_json(
                f"{base_url}/api/chat",
                body,
                headers=auth_headers,
                timeout=120.0,
            )
        except (URLError, OSError) as exc:
            outcome.error = f"turn={idx} transport_error={exc!r}"
            return outcome
        wall_ms = int((time.perf_counter() - t0) * 1000)

        result = _extract_turn_diagnostics(
            turn_num=idx,
            message=body["message"],
            sent_topic=sent_topic,
            http_status=status,
            payload=payload,
            wall_ms=wall_ms,
        )
        outcome.turns.append(result.__dict__)

        if status != 200:
            outcome.error = f"turn={idx} http_status={status}"
            return outcome

        if result.session_id:
            session_id = result.session_id
        if result.effective_topic:
            last_effective_topic = result.effective_topic

        if inter_turn_pause_seconds > 0 and idx < len(turns):
            time.sleep(inter_turn_pause_seconds)

    outcome.ok = True
    return outcome


# ── Aggregation ──────────────────────────────────────────────────────────


def _summarize(outcomes: list[DialogueOutcome]) -> dict[str, Any]:
    total_dialogues = len(outcomes)
    successful = [o for o in outcomes if o.ok]
    total_followup_turns = 0
    refused_followup_turns = 0
    refusal_by_anchor: dict[str, dict[str, int]] = {}
    refusal_reasons: dict[str, int] = {}

    for outcome in successful:
        for turn_data in outcome.turns:
            if turn_data.get("turn_num", 0) <= 1:
                continue
            total_followup_turns += 1
            anchor_bucket = refusal_by_anchor.setdefault(
                outcome.anchor_topic or "<unknown>", {"total": 0, "refused": 0}
            )
            anchor_bucket["total"] += 1
            if turn_data.get("refused"):
                refused_followup_turns += 1
                anchor_bucket["refused"] += 1
                reason_key = str(turn_data.get("coherence_reason") or "<no_reason>")
                refusal_reasons[reason_key] = refusal_reasons.get(reason_key, 0) + 1

    refusal_rate = (
        refused_followup_turns / total_followup_turns if total_followup_turns else 0.0
    )

    return {
        "total_dialogues": total_dialogues,
        "successful_dialogues": len(successful),
        "failed_dialogues": total_dialogues - len(successful),
        "total_followup_turns": total_followup_turns,
        "refused_followup_turns": refused_followup_turns,
        "refusal_rate": round(refusal_rate, 4),
        "refusal_by_anchor": refusal_by_anchor,
        "refusal_reasons": refusal_reasons,
    }


# ── Manifest ─────────────────────────────────────────────────────────────


def _git_sha() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=Path(__file__).resolve().parents[2],
        )
        return out.decode("ascii").strip()
    except Exception:  # noqa: BLE001
        return None


def _atomic_append_json(path: Path, row: dict[str, Any]) -> None:
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass


# ── CLI ──────────────────────────────────────────────────────────────────


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_multiturn_dialogue_harness",
        description=(
            "Multi-turn dialogue harness for next_v4 §3 / §4. Hits a running "
            "ui_server's /api/chat endpoint with a fixed session_id across "
            "T1→T2 (or longer) and aggregates coherence-gate refusal rate."
        ),
    )
    parser.add_argument("--fixture", required=True, help="Path to multiturn fixture JSONL.")
    parser.add_argument("--base-url", required=True, help="ui_server base URL, e.g. http://localhost:5173")
    parser.add_argument("--output-dir", required=True, help="Directory for output JSONL + summary.")
    parser.add_argument(
        "--manifest-tag",
        default="multiturn_v4_baseline",
        help="Free-text tag embedded in output filenames.",
    )
    parser.add_argument(
        "--propagate-topic",
        action="store_true",
        help=(
            "If set, send `topic: <last assistant turn's effective_topic>` in T2+ requests "
            "(simulates Nivel 1 / §3 Option A behavior). Default off — establishes the baseline."
        ),
    )
    parser.add_argument(
        "--inter-turn-pause-seconds",
        type=float,
        default=0.0,
        help="Optional pause between turns within a dialogue (default 0).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N dialogues (smoke convenience).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_argparser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    fixture_path = Path(args.fixture)
    if not fixture_path.exists():
        print(f"[run_multiturn_dialogue_harness] fixture not found: {fixture_path}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_tag = "".join(c if c.isalnum() or c in "-_" else "_" for c in args.manifest_tag)[:64]
    output_jsonl = output_dir / f"multiturn_dialogue_{ts}_{safe_tag}.jsonl"
    summary_path = output_dir / f"multiturn_dialogue_{ts}_{safe_tag}_summary.json"
    manifest_path = output_dir / f"multiturn_dialogue_{ts}_{safe_tag}_manifest.json"

    fixture_rows = _load_fixture(fixture_path)
    if args.limit is not None:
        fixture_rows = fixture_rows[: int(args.limit)]

    base_url = args.base_url.rstrip("/")
    started_utc = _utc_iso_now()
    started_bogota = _bogota_now()

    outcomes: list[DialogueOutcome] = []
    for row in fixture_rows:
        outcome = _run_dialogue(
            base_url=base_url,
            fixture_row=row,
            propagate_topic=bool(args.propagate_topic),
            inter_turn_pause_seconds=float(args.inter_turn_pause_seconds or 0),
        )
        outcomes.append(outcome)
        _atomic_append_json(
            output_jsonl,
            {
                "did": outcome.did,
                "anchor_topic": outcome.anchor_topic,
                "ambiguous_verb": outcome.ambiguous_verb,
                "ok": outcome.ok,
                "error": outcome.error,
                "turns": outcome.turns,
            },
        )
        marker = "ok" if outcome.ok else f"err({outcome.error})"
        print(f"[run_multiturn_dialogue_harness] did={outcome.did} {marker}", file=sys.stderr)

    completed_utc = _utc_iso_now()
    completed_bogota = _bogota_now()
    summary = _summarize(outcomes)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "manifest_tag": safe_tag,
        "fixture_path": str(fixture_path),
        "base_url": base_url,
        "propagate_topic": bool(args.propagate_topic),
        "run_started_at_utc": started_utc,
        "run_completed_at_utc": completed_utc,
        "run_started_at_bogota": started_bogota,
        "run_completed_at_bogota": completed_bogota,
        "git_commit_sha": _git_sha(),
        "summary_path": str(summary_path),
        "output_jsonl": str(output_jsonl),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ok": True,
                "output_jsonl": str(output_jsonl),
                "summary": str(summary_path),
                "manifest": str(manifest_path),
                "summary_inline": summary,
                "started_bogota": started_bogota,
                "completed_bogota": completed_bogota,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
