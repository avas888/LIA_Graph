"""Parallel wrapper around the §1.G SME-panel chat-server runner.

The stock `run_sme_validation.py` posts each of the 36 questions
sequentially with `pacing-seconds` between calls. Each cloud chat
round-trip is ~60-90 s — wall-time ~40-50 min for a full pass.

The lia-ui server handles concurrent requests fine and the LLM
(DeepSeek) is well below its 240 RPM cap at 4-8 concurrent flows.
This wrapper fans out via a ThreadPoolExecutor for ~4-6× speedup.

Resumable: questions whose per-Q response JSON already exists in the
run-dir are skipped (same contract as the stock runner).

Auth-rate-limit invariants (fix_v10_may session-mint 429 incident):
  * ONE ChatClient instance is shared across all workers; the session
    token is minted exactly once in the main thread BEFORE any
    worker starts. Earlier versions created a fresh ChatClient per
    thread, which slammed `/api/public/session` with one token-mint
    per question and tripped the server's 429 rate limit on most of
    a 36-Q run.
  * A `_RateLimit429Feeler` watches every response; the second 429
    (configurable via `--max-429`) cancels all remaining work and
    exits non-zero. "Fail fast, fix fast" — first 429 is a signal,
    second 429 says STOP and have a human evaluate before retry.
    Already-completed per-Q files are preserved so the resumable
    re-run only retries what's missing.

Usage:
  PYTHONPATH=src:. uv run python scripts/eval/run_sme_parallel.py \\
      --run-dir evals/sme_validation_v1/runs/<TS>_<tag> \\
      --workers 4 \\
      [--server http://127.0.0.1:8787] [--timeout-seconds 180] \\
      [--max-429 2]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
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
    p.add_argument(
        "--max-429",
        type=int,
        default=2,
        help=(
            "Stop the run after this many cumulative HTTP 429 responses "
            "across all workers (default 2). First 429 is a warning; "
            "second 429 aborts the run for human evaluation. "
            "Set to 0 to disable the feeler (not recommended)."
        ),
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


class _RateLimit429Feeler:
    """Thread-safe HTTP-429 detector + abort signal.

    Increments a count on each 429 hit; once `threshold` is reached,
    sets a cancel event that workers check before each chat call. New
    work short-circuits to a sentinel result that the writer refuses
    to persist, keeping the run-dir clean of empty/partial responses.

    Per "Fail fast, fix fast" — the first 429 is a signal, the second
    is a stop-and-evaluate trigger. Don't sleep-retry through repeated
    429s; surface them to the operator so they can adjust workers /
    rate-limit config / server capacity before the next attempt.
    """

    def __init__(self, *, threshold: int, logger: logging.Logger) -> None:
        self._lock = threading.Lock()
        self._count = 0
        self._threshold = max(0, int(threshold))
        self._cancel = threading.Event()
        self._logger = logger
        self._sample_qids: list[str] = []

    def record(self, qid: str, status: int) -> None:
        """Call after every chat response."""
        if status != 429:
            return
        with self._lock:
            self._count += 1
            if len(self._sample_qids) < 10:
                self._sample_qids.append(qid)
            count = self._count
        if self._threshold > 0 and count == 1:
            self._logger.warning(
                "29 feeler: first 429 received (qid=%s). "
                "%d more before abort.",
                qid,
                self._threshold - 1,
            )
        if self._threshold > 0 and count >= self._threshold:
            if not self._cancel.is_set():
                self._cancel.set()
                self._logger.error(
                    "429 feeler tripped — %d cumulative 429s (threshold=%d). "
                    "Aborting remaining work; sample qids=%s",
                    count,
                    self._threshold,
                    self._sample_qids,
                )

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    @property
    def count(self) -> int:
        return self._count

    @property
    def sample_qids(self) -> list[str]:
        return list(self._sample_qids)


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

    # fix_v10_may session-mint 429 incident — ONE shared ChatClient,
    # session minted once in the main thread BEFORE workers fan out.
    # `requests`/urllib usage in ChatClient.chat() is thread-safe; the
    # `_auth_headers` dict is read-only after ensure_session().
    shared_client = ChatClient(
        base_url=args.server, auth=args.auth, timeout=args.timeout_seconds
    )
    if args.auth:
        try:
            shared_client.ensure_session()
        except Exception as exc:
            LOGGER.error("auth-session mint failed before fan-out: %s", exc)
            return 3

    todo: list[dict] = []
    for r in rows:
        out = run_dir / f"{r['qid']}.json"
        if out.exists() and out.stat().st_size > 0:
            continue
        todo.append(r)
    LOGGER.info("todo=%d  done=%d/%d  workers=%d  server=%s  max_429=%d",
                len(todo), len(rows) - len(todo), len(rows), args.workers, args.server, args.max_429)
    if not todo:
        LOGGER.info("nothing to do — run dir already complete")
        return 0

    summary_path = run_dir / "summary.jsonl"
    feeler = _RateLimit429Feeler(threshold=args.max_429, logger=LOGGER)

    def _one(record: dict) -> tuple[str, str, int, float]:
        qid = record["qid"]
        msg = record["message"]
        # Short-circuit any work scheduled AFTER the feeler tripped — keeps
        # the run-dir free of phantom records when the operator aborts.
        if feeler.cancelled:
            return qid, "cancelled", -2, 0.0
        t0 = time.monotonic()
        try:
            status, payload = shared_client.chat(msg)
        except Exception as exc:
            payload = {"_transport_error": repr(exc)}
            status = -1
        latency_ms = int((time.monotonic() - t0) * 1000)
        feeler.record(qid, status)
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
        # Persist EVERY response (even 429/transport errors) so the operator
        # can diagnose them. The classifier already treats status<0 and
        # status>=400 as `server_error` (non-quality), so leaving them on
        # disk is informative, not poisoning. Cancelled-after-trip results
        # (status=-2) are NOT persisted so the resumable runner picks them
        # up cleanly on the next attempt.
        if status != -2:
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
    if feeler.cancelled:
        LOGGER.error(
            "RUN ABORTED by 429 feeler — %d cumulative 429s. "
            "Inspect server-side rate-limit config and re-run; the resumable "
            "wrapper will only retry the missing per-Q files. "
            "Sample qids: %s",
            feeler.count,
            feeler.sample_qids,
        )
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
