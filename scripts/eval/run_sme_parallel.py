"""Parallel wrapper around the §1.G SME-panel chat-server runner.

The stock `run_sme_validation.py` posts each of the 36 questions
sequentially with `pacing-seconds` between calls. Each cloud chat
round-trip is ~60-90 s — wall-time ~40-50 min for a full pass.

The lia-ui server handles concurrent requests fine and the LLM
(DeepSeek) is well below its 240 RPM cap at 4-8 concurrent flows.
This wrapper fans out via a ThreadPoolExecutor for ~4-6× speedup.

Resumable: questions whose per-Q response JSON already exists in the
run-dir are skipped (same contract as the stock runner).

Usage:
  PYTHONPATH=src:. uv run python scripts/eval/run_sme_parallel.py \\
      --run-dir evals/sme_validation_v1/runs/<TS>_<tag> \\
      --workers 4 \\
      [--server http://127.0.0.1:8787] [--timeout-seconds 180]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

LOGGER = logging.getLogger("run_sme_parallel")

QUESTIONS_JSONL = Path("evals/sme_validation_v1/questions_2026-04-26.jsonl")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run-dir", required=True, help="Run dir to populate with per-Q JSON files.")
    p.add_argument("--server", default="http://127.0.0.1:8787")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--timeout-seconds", type=int, default=180)
    p.add_argument("--questions", default=str(QUESTIONS_JSONL))
    p.add_argument("--auth", action="store_true", help="Mint /api/public/session token first")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    qfile = Path(args.questions)
    if not qfile.is_file():
        LOGGER.error("questions file missing: %s", qfile)
        return 2

    rows: list[dict] = []
    for line in qfile.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    LOGGER.info("loaded %d questions from %s", len(rows), qfile)

    # Reuse the stock runner's HTTP plumbing + summarizer to keep behavior identical.
    from scripts.eval.engine import ChatClient, append_jsonl, utc_iso
    from scripts.eval.run_sme_validation import _summarize_record

    # ChatClient is a dataclass; instantiate per-thread to avoid sharing
    # the auth token state between concurrent requests (it's safe to
    # re-mint via ensure_session() on each instance).
    def _make_client() -> ChatClient:
        return ChatClient(base_url=args.server, auth=args.auth, timeout=args.timeout_seconds)

    todo: list[dict] = []
    for r in rows:
        out = run_dir / f"{r['qid']}.json"
        if out.exists() and out.stat().st_size > 0:
            continue
        todo.append(r)
    LOGGER.info("todo=%d  done=%d/%d  workers=%d  server=%s",
                len(todo), len(rows) - len(todo), len(rows), args.workers, args.server)
    if not todo:
        LOGGER.info("nothing to do — run dir already complete")
        return 0

    summary_path = run_dir / "summary.jsonl"

    def _one(record: dict) -> tuple[str, str, int, float]:
        qid = record["qid"]
        msg = record["message"]
        client = _make_client()
        t0 = time.monotonic()
        try:
            status, payload = client.chat(msg)
        except Exception as exc:
            payload = {"_transport_error": repr(exc)}
            status = -1
        latency_ms = int((time.monotonic() - t0) * 1000)
        rec = {
            "qid": qid,
            "topic_key_expected": record.get("topic_key"),
            "profile": record.get("profile"),
            "message": msg,
            "http_status": status,
            "latency_ms": latency_ms,
            "captured_utc": utc_iso(),
            "response": payload,
        }
        (run_dir / f"{qid}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        try:
            summary = _summarize_record(rec)
            append_jsonl(summary_path, summary)
            return qid, summary.get("answer_mode") or "?", status, latency_ms / 1000
        except Exception as err:
            LOGGER.warning("qid=%s summarize failed: %s", qid, err)
            return qid, "summarize_error", status, latency_ms / 1000

    completed = 0
    started = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_one, r) for r in todo]
        for fut in as_completed(futs):
            qid, mode, status, elapsed = fut.result()
            completed += 1
            LOGGER.info("[%d/%d] qid=%s status=%d mode=%s elapsed=%.1fs",
                        completed, len(todo), qid, status, mode, elapsed)
    total_elapsed = time.time() - started
    LOGGER.info("DONE %d new responses in %.1fs (%.1fs/Q wall, %d workers)",
                len(todo), total_elapsed, total_elapsed / max(len(todo), 1), args.workers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
