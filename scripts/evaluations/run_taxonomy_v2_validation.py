"""Run the SME's 30-question taxonomy v2 validation suite.

next_v3.md §6 — the 30 questions in ``evals/gold_taxonomy_v2_validation.jsonl``
are the v2 approval gate. For each question, we run:

1. ``detect_topic_from_text`` — the lexical router alone (fast, no LLM).
2. ``resolve_chat_topic`` — full routing (router + LLM if configured).

Decision rule (next_v3 §6 step 5b): ≥ 27/30 expected_topic matches for the
combined path. Single question with ``ambiguous_acceptable`` is scored as a
hit if any of its acceptable topics matches.

Usage::

    PYTHONPATH=src:. uv run python scripts/evaluations/run_taxonomy_v2_validation.py \\
        --gold evals/gold_taxonomy_v2_validation.jsonl \\
        --threshold 27
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Row:
    qid: int
    query: str
    expected: str
    acceptable: tuple[str, ...]
    notes: str | None


def _load_gold(path: Path) -> list[Row]:
    rows: list[Row] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            data: dict[str, Any] = json.loads(line)
            expected = str(data["expected_topic"]).strip().lower()
            acceptable_raw = data.get("ambiguous_acceptable") or [expected]
            acceptable = tuple(str(a).strip().lower() for a in acceptable_raw)
            rows.append(
                Row(
                    qid=int(data["qid"]),
                    query=str(data["query"]),
                    expected=expected,
                    acceptable=acceptable,
                    notes=(str(data["sme_notes"]) if data.get("sme_notes") else None),
                )
            )
    return rows


def _router_topic(query: str) -> str | None:
    """Lexical-router-only signal (no LLM)."""
    from lia_graph.topic_router import detect_topic_from_text

    det = detect_topic_from_text(query)
    return det.topic if det is not None else None


def _chat_topic(query: str, *, runtime_config_path: Path | None = None) -> str | None:
    """Full resolver signal — mirrors what the chat pipeline sees.

    When ``runtime_config_path`` is provided, ``resolve_chat_topic``
    activates the LLM fallback. SME §3.2 threshold (≥27/30) is against
    this path, so the ``--use-llm`` harness flag is the real gate.
    """
    from lia_graph.topic_router import resolve_chat_topic

    result = resolve_chat_topic(
        message=query,
        requested_topic=None,
        runtime_config_path=runtime_config_path,
    )
    return result.effective_topic if result is not None else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Taxonomy v2 validation harness")
    parser.add_argument(
        "--gold",
        default="evals/gold_taxonomy_v2_validation.jsonl",
        help="JSONL validation set",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=27,
        help="Minimum passes (default 27/30 per next_v3 §6)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print per-question result"
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help=(
            "Activate resolve_chat_topic's LLM fallback. Required to hit the "
            "27/30 threshold — router-alone baseline tops out below that."
        ),
    )
    parser.add_argument(
        "--runtime-config",
        default="config/llm_runtime.json",
        help="LLM runtime config path (only used with --use-llm)",
    )
    args = parser.parse_args()

    runtime_config: Path | None = None
    if args.use_llm:
        runtime_config = Path(args.runtime_config)
        if not runtime_config.exists():
            print(
                f"[taxonomy-v2-eval] --use-llm set but runtime config missing: {runtime_config}",
                file=sys.stderr,
            )
            sys.exit(2)

    gold_path = Path(args.gold)
    if not gold_path.exists():
        print(f"[taxonomy-v2-eval] missing gold file: {gold_path}", file=sys.stderr)
        sys.exit(2)

    rows = _load_gold(gold_path)
    router_hits = 0
    chat_hits = 0
    per_q: list[dict[str, Any]] = []

    for row in rows:
        router_pred = _router_topic(row.query)
        chat_pred = _chat_topic(row.query, runtime_config_path=runtime_config)
        router_ok = router_pred in row.acceptable if router_pred else False
        chat_ok = chat_pred in row.acceptable if chat_pred else False
        router_hits += int(router_ok)
        chat_hits += int(chat_ok)
        per_q.append(
            {
                "qid": row.qid,
                "expected": row.expected,
                "router": router_pred,
                "router_ok": router_ok,
                "chat": chat_pred,
                "chat_ok": chat_ok,
                "notes": row.notes,
            }
        )
        if args.verbose:
            status_r = "OK" if router_ok else "XX"
            status_c = "OK" if chat_ok else "XX"
            print(
                f"[{status_r} router / {status_c} chat] q{row.qid:02d} exp={row.expected:42s} "
                f"router={str(router_pred):40s} chat={str(chat_pred)}"
            )

    total = len(rows)
    print()
    print(f"Router-only accuracy: {router_hits}/{total}")
    print(f"Chat-resolver accuracy: {chat_hits}/{total}")
    print(f"Threshold: {args.threshold}/{total}")

    passed = chat_hits >= args.threshold
    if not passed:
        print("FAIL: chat-resolver accuracy below threshold.")
        # Brief failure list
        fails = [q for q in per_q if not q["chat_ok"]]
        for f in fails:
            print(
                f"  - q{f['qid']:02d}: expected {f['expected']}, got chat={f['chat']} "
                f"(router={f['router']})"
            )
        sys.exit(1)

    print("PASS")


if __name__ == "__main__":
    main()
