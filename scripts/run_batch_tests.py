"""Run a canonicalizer batch's test_questions against the served chat — pre & post.

For each batch_id from `config/canonicalizer_run_v1/batches.yaml`:

  * `--mode pre`  posts each question to the chat backend BEFORE the batch
                  ingests, captures verbatim answer + citations + diagnostics.
  * `--mode post` posts the SAME questions AFTER the batch ingests.
  * `--mode score` compares pre vs post against the must_cite / must_not_cite /
                   must_not_say / expected_chip_state rules and emits one PASS /
                   FAIL line per question + an aggregate batch verdict.

Outputs land at:
  evals/canonicalizer_run_v1/<batch_id>/<mode>_<run_id>.json
  evals/canonicalizer_run_v1/ledger.jsonl  (append-only batch verdicts)

Usage (per the protocol in docs/re-engineer/canonicalizer_runv1.md §0):

  # Step 1 — baseline
  PYTHONPATH=src:. uv run python scripts/run_batch_tests.py \\
      --batch-id A2 --mode pre --base-url http://127.0.0.1:8787 \\
      --run-id baseline-A2-$(date +%Y%m%dT%H%M%SZ)

  # Step 2 — extract + ingest the batch (separate scripts)

  # Step 3 — verify
  PYTHONPATH=src:. uv run python scripts/run_batch_tests.py \\
      --batch-id A2 --mode post --base-url http://127.0.0.1:8787 \\
      --run-id verify-A2-$(date +%Y%m%dT%H%M%SZ)

  # Step 4 — score the delta
  PYTHONPATH=src:. uv run python scripts/run_batch_tests.py \\
      --batch-id A2 --mode score
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

LOGGER = logging.getLogger("run_batch_tests")
ROOT = Path(__file__).resolve().parent.parent
BOGOTA_TZ = timezone(timedelta(hours=-5))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--batch-id", required=True)
    p.add_argument("--mode", choices=("pre", "post", "score"), required=True)
    p.add_argument("--run-id", default=None,
                   help="Used in pre/post output filenames. Auto-generated if omitted.")
    p.add_argument("--batches-config",
                   default="config/canonicalizer_run_v1/batches.yaml")
    p.add_argument("--output-dir",
                   default="evals/canonicalizer_run_v1")
    p.add_argument("--ledger",
                   default="evals/canonicalizer_run_v1/ledger.jsonl")
    p.add_argument("--base-url",
                   default="http://127.0.0.1:8787",
                   help="Chat backend (lia-ui server). Use 8787 for direct, 5173 for vite-proxied.")
    p.add_argument("--auth", action="store_true",
                   help="Send /api/public/session to mint a Bearer token (needed when hitting the Vite proxy).")
    p.add_argument("--topic", default=None,
                   help="Optional topic hint to include in the chat payload.")
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    batch = _load_batch(Path(args.batches_config), args.batch_id)
    if batch is None:
        LOGGER.error("Batch %s not found in %s", args.batch_id, args.batches_config)
        return 2

    questions = batch.get("test_questions") or []
    if args.mode in ("pre", "post"):
        if not questions:
            LOGGER.warning("Batch %s has no test_questions — nothing to run.", args.batch_id)
            return 0
        return _run_questions(args, batch, questions)
    elif args.mode == "score":
        return _score_batch(args, batch, questions)
    return 1


# ---------------------------------------------------------------------------
# pre/post — run questions against the chat backend
# ---------------------------------------------------------------------------


def _run_questions(args: argparse.Namespace, batch: dict[str, Any], questions: list[dict[str, Any]]) -> int:
    sys.path.insert(0, str(ROOT / "scripts" / "eval"))
    try:
        from engine import ChatClient  # type: ignore
    except ImportError as err:
        LOGGER.error("Cannot import scripts/eval/engine.ChatClient: %s", err)
        return 3

    run_id = args.run_id or f"{args.mode}-{args.batch_id}-{_compact_now()}"
    out_dir = Path(args.output_dir) / args.batch_id
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{args.mode}_{run_id}.json"

    client = ChatClient(base_url=args.base_url, auth=args.auth, timeout=args.timeout)

    captured: list[dict[str, Any]] = []
    for idx, qspec in enumerate(questions, start=1):
        question = str(qspec.get("q") or "").strip()
        if not question:
            continue
        LOGGER.info("[%s/%d] Q: %s", idx, len(questions), question[:80])
        t0 = time.monotonic()
        try:
            status, payload = client.chat(question, topic=args.topic)
            wall_ms = int((time.monotonic() - t0) * 1000)
        except Exception as err:
            LOGGER.warning("Chat call failed: %s", err)
            captured.append({
                "index": idx,
                "question": question,
                "expected": qspec,
                "http_status": None,
                "error": str(err),
                "wall_ms": int((time.monotonic() - t0) * 1000),
            })
            continue
        captured.append({
            "index": idx,
            "question": question,
            "expected": qspec,
            "http_status": status,
            "answer_markdown": payload.get("answer_markdown") or payload.get("answer_concise") or "",
            "answer_concise": payload.get("answer_concise") or "",
            "citations": payload.get("citations") or [],
            "diagnostics": payload.get("diagnostics") or {},
            "wall_ms": wall_ms,
        })

    blob = {
        "ts_bogota": _now_bogota(),
        "batch_id": args.batch_id,
        "mode": args.mode,
        "run_id": run_id,
        "base_url": args.base_url,
        "questions": captured,
    }
    output_path.write_text(json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("Wrote %s (%d questions captured)", output_path, len(captured))
    return 0


# ---------------------------------------------------------------------------
# score — diff pre vs post and emit verdict
# ---------------------------------------------------------------------------


@dataclass
class _QuestionVerdict:
    index: int
    question: str
    pre_pass: bool | None
    post_pass: bool
    delta: str
    failures: list[str] = field(default_factory=list)


def _score_batch(args: argparse.Namespace, batch: dict[str, Any], questions: list[dict[str, Any]]) -> int:
    out_dir = Path(args.output_dir) / args.batch_id
    if not out_dir.exists():
        LOGGER.error("No pre/post outputs at %s — run --mode pre and --mode post first.", out_dir)
        return 4

    pre_files = sorted(out_dir.glob("pre_*.json"))
    post_files = sorted(out_dir.glob("post_*.json"))
    if not post_files:
        LOGGER.error("No post_*.json in %s — run --mode post first.", out_dir)
        return 4

    pre_blob = _load_json(pre_files[-1]) if pre_files else None
    post_blob = _load_json(post_files[-1])
    if post_blob is None:
        LOGGER.error("Could not read post output.")
        return 4

    pre_by_q = {q["index"]: q for q in (pre_blob.get("questions") if pre_blob else [])}
    post_by_q = {q["index"]: q for q in post_blob.get("questions", [])}

    verdicts: list[_QuestionVerdict] = []
    for q in questions:
        idx = questions.index(q) + 1
        pre = pre_by_q.get(idx)
        post = post_by_q.get(idx)
        if post is None:
            verdicts.append(_QuestionVerdict(
                index=idx,
                question=q["q"],
                pre_pass=_score_question(pre, q) if pre else None,
                post_pass=False,
                delta="MISSING_POST",
                failures=["post run missing this question"],
            ))
            continue
        pre_pass = _score_question(pre, q) if pre else None
        post_pass, post_failures = _score_question_detailed(post, q)
        delta = _delta_label(pre_pass, post_pass)
        verdicts.append(_QuestionVerdict(
            index=idx,
            question=q["q"],
            pre_pass=pre_pass,
            post_pass=post_pass,
            delta=delta,
            failures=post_failures,
        ))

    passed = sum(1 for v in verdicts if v.post_pass)
    failed = len(verdicts) - passed
    moved_to_pass = sum(1 for v in verdicts if v.pre_pass is False and v.post_pass is True)
    regressions = sum(1 for v in verdicts if v.pre_pass is True and v.post_pass is False)

    print()
    print(f"=== Batch {args.batch_id} score @ {_now_bogota()} ===")
    for v in verdicts:
        print(f"  Q{v.index} [{v.delta}] {'PASS' if v.post_pass else 'FAIL'}: {v.question[:90]}")
        for f in v.failures:
            print(f"      ↳ {f}")
    print()
    print(f"  Total: passed={passed} failed={failed} moved_to_pass={moved_to_pass} regressions={regressions}")
    print()

    # Append to ledger
    ledger_row = {
        "ts_bogota": _now_bogota(),
        "batch_id": args.batch_id,
        "phase": batch.get("phase"),
        "title": batch.get("title"),
        "questions_total": len(verdicts),
        "questions_passed": passed,
        "questions_failed": failed,
        "moved_to_pass": moved_to_pass,
        "regressions": regressions,
        "verdict": "PASS" if (failed == 0 and regressions == 0) else "FAIL",
        "per_question": [
            {
                "index": v.index,
                "question": v.question,
                "pre_pass": v.pre_pass,
                "post_pass": v.post_pass,
                "delta": v.delta,
                "failures": v.failures,
            }
            for v in verdicts
        ],
    }
    ledger_path = Path(args.ledger)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ledger_row, ensure_ascii=False) + "\n")
    LOGGER.info("Ledger row appended to %s", ledger_path)

    # Exit code: 0 PASS, 1 FAIL.
    return 0 if ledger_row["verdict"] == "PASS" else 1


def _score_question(question_payload: dict[str, Any] | None, expected: dict[str, Any]) -> bool | None:
    if question_payload is None:
        return None
    return _score_question_detailed(question_payload, expected)[0]


def _score_question_detailed(payload: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return (passed, list_of_failure_reasons)."""

    failures: list[str] = []
    if payload.get("error"):
        failures.append(f"chat call errored: {payload['error']}")
        return False, failures

    answer = (payload.get("answer_markdown") or "").lower()
    citations = payload.get("citations") or []
    cited_norm_ids = _extract_norm_ids_from_citations(citations)

    must_cite = expected.get("must_cite") or []
    for needed in must_cite:
        if not _norm_in_set(needed, cited_norm_ids, answer):
            failures.append(f"must_cite missing: {needed}")

    must_not_cite = expected.get("must_not_cite") or []
    for forbidden in must_not_cite:
        if _norm_in_set(forbidden, cited_norm_ids, answer):
            failures.append(f"must_not_cite present: {forbidden}")

    must_not_say = expected.get("must_not_say") or []
    for phrase in must_not_say:
        if str(phrase).lower() in answer:
            failures.append(f"must_not_say present: {phrase!r}")

    expected_chips = expected.get("expected_chip_state") or {}
    for norm_id, expected_state in expected_chips.items():
        actual_state = _find_chip_state(citations, norm_id)
        if actual_state is None:
            failures.append(f"expected chip state {expected_state} on {norm_id}, but no vigencia_v3 annotation found")
        elif str(actual_state).upper() != str(expected_state).upper():
            failures.append(
                f"chip state mismatch on {norm_id}: expected {expected_state}, got {actual_state}"
            )

    return (len(failures) == 0), failures


def _norm_in_set(needed: str, cited_norm_ids: set[str], answer_text: str) -> bool:
    if needed in cited_norm_ids:
        return True
    # Soft fallback — the answer text mentions the norm in a recognizable form
    needed_lower = needed.lower()
    if needed_lower in answer_text:
        return True
    # Try a free-text variant: et.art.689-3 → "art. 689-3"
    if needed.startswith("et.art."):
        article = needed.split(".", 2)[2]
        # Match "Art. 689-3" or "Articulo 689-3"
        article_pattern = re.compile(rf"art(?:[íi]culo|\.)?\s*{re.escape(article)}", re.IGNORECASE)
        if article_pattern.search(answer_text):
            return True
    return False


def _extract_norm_ids_from_citations(citations: Iterable[Any]) -> set[str]:
    out: set[str] = set()
    for c in citations:
        if not isinstance(c, dict):
            continue
        # Direct norm_id field if v3 is plumbed through
        nid = c.get("norm_id")
        if isinstance(nid, str) and nid:
            out.add(nid)
        v3 = c.get("vigencia_v3")
        if isinstance(v3, dict):
            anchor = v3.get("anchor_norm_id")
            if isinstance(anchor, str) and anchor:
                out.add(anchor)
        # Fallback: parse from legal_reference / source_label / reference_key
        for field in ("legal_reference", "source_label", "reference_key"):
            text = str(c.get(field) or "").strip()
            if text:
                out.update(_norm_ids_from_freetext(text))
    return out


def _norm_ids_from_freetext(text: str) -> set[str]:
    """Best-effort canonicalization of citation labels into norm_ids."""

    try:
        from lia_graph.canon import canonicalize  # type: ignore
    except Exception:
        return set()
    out: set[str] = set()
    for token in re.split(r"[,;]\s*", text):
        candidate = canonicalize(token)
        if candidate:
            out.add(candidate)
    return out


def _find_chip_state(citations: Iterable[Any], norm_id: str) -> str | None:
    for c in citations:
        if not isinstance(c, dict):
            continue
        v3 = c.get("vigencia_v3")
        if not isinstance(v3, dict):
            continue
        anchor = str(v3.get("anchor_norm_id") or "")
        if anchor == norm_id:
            state = v3.get("anchor_state")
            return str(state) if state is not None else None
    return None


def _delta_label(pre: bool | None, post: bool) -> str:
    if pre is None:
        return "NO_BASELINE"
    if pre and post:
        return "STILL_PASS"
    if not pre and post:
        return "MOVED_TO_PASS"
    if pre and not post:
        return "REGRESSED"
    return "STILL_FAIL"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_batch(config_path: Path, batch_id: str) -> dict[str, Any] | None:
    try:
        import yaml  # type: ignore
    except ImportError:
        LOGGER.error("PyYAML required: uv pip install pyyaml")
        return None
    if not config_path.is_file():
        LOGGER.error("Config not found: %s", config_path)
        return None
    blobs = yaml.safe_load(config_path.read_text(encoding="utf-8")) or []
    for b in blobs:
        if str(b.get("batch_id") or "").strip() == batch_id:
            return b
    return None


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        LOGGER.warning("Cannot read %s: %s", path, err)
        return None


def _now_bogota() -> str:
    return datetime.now(BOGOTA_TZ).strftime("%Y-%m-%d %I:%M:%S %p Bogotá")


def _compact_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


if __name__ == "__main__":
    sys.exit(main())
