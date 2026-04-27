#!/usr/bin/env python3
"""Run the §1.G SME-authored validation set against the live chat server.

Pipeline:
  1. Parse `evals/sme_validation_v1/questions_2026-04-26.txt` (TEMA blocks)
     into `evals/sme_validation_v1/questions_2026-04-26.jsonl` (36 records).
  2. POST each record to the chat endpoint, capture the full response.
  3. Classify each response into one of:
       served_strong | served_acceptable | served_weak | served_off_topic | refused
  4. Write per-Q response JSON, a summary JSONL, and a classified JSONL.

Resumable: if a per-Q response file already exists in the run dir, that qid
is skipped (the classifier picks the existing file up on the next pass).

HTTP / IO / timestamp plumbing lives in `scripts/eval/engine.py`. The
parser (Phase A) and classifier (Phase C) live here because they're the
only SME-specific pieces.

Usage:
    PYTHONPATH=src:. uv run python scripts/eval/run_sme_validation.py
    # optional flags:
    #   --server http://127.0.0.1:8787  (default — lia-ui port, no auth)
    #   --auth                          (mint a /api/public/session token first)
    #   --pais colombia                 (default)
    #   --parse-only                    (rebuild the JSONL and exit)
    #   --classify-only <run_dir>       (re-classify an existing run dir)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable
from urllib.error import URLError

# Sibling import — invocation puts scripts/eval/ on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import (  # noqa: E402
    ChatClient,
    append_jsonl,
    bogota_now_human,
    git_sha,
    iter_jsonl,
    utc_iso,
    utc_iso_compact,
    write_jsonl,
    write_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "evals" / "sme_validation_v1"
RUNS_DIR = EVAL_DIR / "runs"
QUESTIONS_TXT = EVAL_DIR / "questions_2026-04-26.txt"
QUESTIONS_JSONL = EVAL_DIR / "questions_2026-04-26.jsonl"
TAXONOMY_PATH = ROOT / "config" / "topic_taxonomy.json"

PROFILE_LABELS = {
    "P1": "P1_directa",
    "P2": "P2_operativa",
    "P3": "P3_borde",
}


# ---------------------------------------------------------------------------
# Phase A — parser (SME-specific input shape)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Question:
    qid: str
    topic_key: str
    profile: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_taxonomy_keys() -> set[str]:
    with TAXONOMY_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    keys: set[str] = set()
    for t in data.get("topics", []):
        k = t.get("key") or t.get("topic_key") or t.get("name")
        if k:
            keys.add(k)
    return keys


_PROFILE_LINE = re.compile(r"^(P[123])\s*\(([^)]+)\)\s*:\s*(.+)$")


def parse_questions(text: str, *, valid_topics: set[str]) -> list[Question]:
    """Split a TEMA-formatted paste into Question records.

    Robust to:
      - Blank lines between blocks
      - Stray whitespace around colons
      - Missing P-lines (raises ValueError naming the topic)
      - Unknown topic_keys (raises ValueError listing the offending key)
    """
    out: list[Question] = []
    blocks = [b for b in re.split(r"(?m)^TEMA:\s*", text.strip()) if b.strip()]
    for block in blocks:
        lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        topic_key = lines[0].strip()
        if topic_key not in valid_topics:
            raise ValueError(
                f"Unknown topic_key {topic_key!r} — not in topic_taxonomy.json"
            )
        seen: dict[str, str] = {}
        for ln in lines[1:]:
            m = _PROFILE_LINE.match(ln)
            if not m:
                continue
            seen[m.group(1)] = m.group(3).strip()
        for tag in ("P1", "P2", "P3"):
            if tag not in seen:
                raise ValueError(f"Topic {topic_key!r} missing line for {tag}")
            out.append(
                Question(
                    qid=f"{topic_key}_{tag}",
                    topic_key=topic_key,
                    profile=PROFILE_LABELS[tag],
                    message=seen[tag],
                )
            )
    return out


def load_jsonl_questions(path: Path) -> list[Question]:
    return [Question(**row) for row in iter_jsonl(path)]


# ---------------------------------------------------------------------------
# Phase B — runner
# ---------------------------------------------------------------------------


def run_questions(
    questions: list[Question],
    client: ChatClient,
    run_dir: Path,
    *,
    pacing_seconds: float = 1.0,
) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "summary.jsonl"

    for q in questions:
        response_path = run_dir / f"{q.qid}.json"
        if response_path.exists():
            print(f"  [skip] {q.qid} (already in run dir)")
            continue

        print(f"  [run]  {q.qid} ...", flush=True)
        t0 = time.monotonic()
        try:
            status, payload = client.chat(q.message)
        except (URLError, OSError) as exc:
            payload = {"_transport_error": repr(exc)}
            status = -1
        latency_ms = int((time.monotonic() - t0) * 1000)

        record = {
            "qid": q.qid,
            "topic_key_expected": q.topic_key,
            "profile": q.profile,
            "message": q.message,
            "http_status": status,
            "latency_ms": latency_ms,
            "captured_utc": utc_iso(),
            "response": payload,
        }
        response_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        summary = _summarize_record(record)
        append_jsonl(summary_path, summary)
        print(
            f"         mode={summary['answer_mode']!r} "
            f"topic={summary['effective_topic']!r} "
            f"cites={summary['citations_count']} "
            f"len={summary['answer_len']} "
            f"latency={latency_ms}ms"
        )
        time.sleep(pacing_seconds)

    return summary_path


# ---------------------------------------------------------------------------
# Phase C — classifier
# ---------------------------------------------------------------------------


def _summarize_record(record: dict[str, Any]) -> dict[str, Any]:
    resp = record.get("response", {}) or {}
    diag = resp.get("diagnostics", {}) or {}
    answer_md = resp.get("answer_markdown") or resp.get("answer") or ""
    citations = resp.get("citations") or []
    cite_labels = [
        c.get("label") for c in citations
        if isinstance(c, dict) and c.get("label")
    ]
    return {
        "qid": record["qid"],
        "topic_key_expected": record["topic_key_expected"],
        "profile": record["profile"],
        "answer_mode": resp.get("answer_mode"),
        "fallback_reason": (
            resp.get("fallback_reason") or diag.get("fallback_reason")
        ),
        "effective_topic": (
            resp.get("effective_topic")
            or diag.get("effective_topic")
            or diag.get("router_topic")
        ),
        "citations_count": len(citations),
        "citation_labels": cite_labels,
        "answer_len": len(answer_md),
        "compose_quality": (
            resp.get("compose_quality") or diag.get("compose_quality")
        ),
        "latency_ms": record["latency_ms"],
        "http_status": record["http_status"],
    }


def classify(summary: dict[str, Any]) -> str:
    mode = summary.get("answer_mode") or ""
    expected = summary["topic_key_expected"]
    actual = summary.get("effective_topic")
    cites = summary.get("citations_count") or 0
    n = summary.get("answer_len") or 0
    status = summary.get("http_status")

    # Server-side failure (HTTP non-200, transport error, missing payload).
    # Bucket separately so the gauge denominator isn't contaminated by
    # infrastructure issues — those need to be re-run, not interpreted as
    # quality outcomes.
    if status is None or status < 0 or status >= 400:
        return "server_error"

    if mode == "topic_safety_abstention":
        return "refused"

    if mode in ("graph_native", "graph_native_partial"):
        # Hard topic-routing check first — even a long answer is "off topic"
        # if the router latched on the wrong topic.
        if actual and actual != expected:
            return "served_off_topic"
        if cites >= 3 and n >= 1500 and actual == expected and mode == "graph_native":
            return "served_strong"
        if cites >= 1 and n >= 600:
            return "served_acceptable"
        return "served_weak"

    return "served_weak"


def classify_run(run_dir: Path) -> Path:
    out_path = run_dir / "classified.jsonl"
    rows: list[dict[str, Any]] = []
    for response_path in sorted(run_dir.glob("*.json")):
        if response_path.name in ("manifest.json",):
            continue
        with response_path.open("r", encoding="utf-8") as fh:
            record = json.load(fh)
        if "qid" not in record:
            continue
        summary = _summarize_record(record)
        summary["class"] = classify(summary)
        rows.append(summary)
    write_jsonl(out_path, rows)
    return out_path


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------


def _print_state(classified_path: Path) -> None:
    counts: dict[str, int] = {}
    for row in iter_jsonl(classified_path):
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    served = counts.get("served_strong", 0) + counts.get("served_acceptable", 0)
    weak = counts.get("served_weak", 0) + counts.get("served_off_topic", 0)
    refused = counts.get("refused", 0)
    server_err = counts.get("server_error", 0)
    print(
        f"\nSTATE: served_acceptable+={served}/36 weak={weak} refused={refused} "
        f"server_error={server_err}"
    )
    print("       breakdown:", json.dumps(counts, ensure_ascii=False))


def _write_run_manifest(run_dir: Path, args: argparse.Namespace, n_questions: int) -> None:
    manifest = {
        "run_kind": "sme_validation_v1",
        "run_dir": str(run_dir),
        "started_utc": utc_iso(),
        "started_bogota": bogota_now_human(),
        "server": args.server,
        "auth": args.auth,
        "pais": args.pais,
        "questions_fixture": str(QUESTIONS_JSONL),
        "questions_count": n_questions,
        "git_commit_sha": git_sha(ROOT),
    }
    write_manifest(run_dir / "manifest.json", manifest)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--server", default="http://127.0.0.1:8787")
    p.add_argument("--auth", action="store_true",
                   help="Mint /api/public/session token (needed against Vite proxy on :5173)")
    p.add_argument("--pais", default="colombia")
    p.add_argument("--parse-only", action="store_true")
    p.add_argument(
        "--classify-only", type=Path,
        help="Re-classify an existing run dir without posting any new requests",
    )
    p.add_argument(
        "--run-dir", type=Path, default=None,
        help="Override the auto-generated run dir (default: runs/<utc_iso>)",
    )
    p.add_argument("--pacing-seconds", type=float, default=1.0)
    p.add_argument("--timeout-seconds", type=float, default=90.0)
    args = p.parse_args(argv)

    if args.classify_only:
        out_path = classify_run(args.classify_only)
        _print_state(out_path)
        return 0

    valid_topics = _load_taxonomy_keys()
    if not QUESTIONS_TXT.exists():
        print(f"FATAL: missing {QUESTIONS_TXT}", file=sys.stderr)
        return 2
    text = QUESTIONS_TXT.read_text(encoding="utf-8")
    questions = parse_questions(text, valid_topics=valid_topics)
    if len(questions) != 36:
        print(
            f"WARNING: parsed {len(questions)} questions (expected 36)",
            file=sys.stderr,
        )
    n = write_jsonl(QUESTIONS_JSONL, [q.to_dict() for q in questions])
    print(f"Parsed {n} questions → {QUESTIONS_JSONL}")

    if args.parse_only:
        return 0

    run_dir = args.run_dir or (RUNS_DIR / utc_iso_compact())
    _write_run_manifest(run_dir, args, len(questions))
    print(f"Run dir: {run_dir}")
    print(f"Server:  {args.server}  (auth={args.auth})")

    client = ChatClient(
        base_url=args.server,
        auth=args.auth,
        timeout=args.timeout_seconds,
        pais=args.pais,
    )
    try:
        client.ensure_session()
    except RuntimeError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 3

    run_questions(questions, client, run_dir, pacing_seconds=args.pacing_seconds)
    classified_path = classify_run(run_dir)
    _print_state(classified_path)
    print(f"\nNext: scripts/eval/sme_validation_report.py {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
