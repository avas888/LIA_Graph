#!/usr/bin/env python3
"""evaluacion_ingestionfixtask_v1 — A/B launcher for TEMA-first vs prior retrieval.

Reads ``evals/gold_retrieval_v1.jsonl`` (one JSON per line, canonical 30
questions), iterates, and for EACH question runs :func:`run_pipeline_d`
twice:

1. With ``LIA_TEMA_FIRST_RETRIEVAL=off``  (prior mode — v4-era behavior).
2. With ``LIA_TEMA_FIRST_RETRIEVAL=on``   (new mode   — v5 TEMA-first).

After each pair it appends ONE JSON row to
``<output_dir>/ab_comparison_<ts>.jsonl`` and flushes. A crash mid-run
leaves a partial JSONL the renderer (``render_ab_markdown.py``) can still
process. A ``--resume <path>`` flag skips qids already present in the
target file, so operators can recover by re-launching.

Explicitly NOT in scope:
  * Automated answer grading. Output goes to a human expert panel.
  * Changes to any production code. This harness calls ``run_pipeline_d``
    read-only — no writes to Supabase or Falkor.
  * Parallel execution. Env-flag toggling is process-global, so we run
    sequentially. Typical wall time: 20–30 min for 30 × 2 queries.

See docs/quality_tests/evaluacion_ingestionfixtask_v1.md §5 Phase 1 for
the binding contract this file implements.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import signal
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


# ── Time helpers (Bogotá AM/PM for user surfaces, UTC ISO for machine) ────

_BOGOTA = _dt.timezone(_dt.timedelta(hours=-5))


def _bogota_now() -> str:
    return _dt.datetime.now(_BOGOTA).strftime("%Y-%m-%d %-I:%M:%S %p").lstrip("0")


def _utc_iso_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


# ── Gold loader ───────────────────────────────────────────────────────────


def _load_gold(path: Path) -> list[dict[str, Any]]:
    """Read the gold JSONL and return one dict per line.

    Lines that don't parse as JSON abort the run — malformed gold is a
    data bug, not a transient error; surface it loudly.
    """
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise SystemExit(
                    f"[run_ab_comparison] gold file {path} line {lineno} invalid JSON: {exc}"
                )
    return rows


# ── Result row shape ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class ModeResult:
    """One mode's result for a single question. Serialized to JSON inside
    the per-question row; fields deliberately narrow to keep panel-doc
    rendering straightforward."""

    mode: str  # "prior" or "new"
    env_flag_value: str  # what LIA_TEMA_FIRST_RETRIEVAL was set to
    answer_markdown: str
    retrieval_backend: str | None
    graph_backend: str | None
    primary_article_count: int
    connected_article_count: int
    related_reform_count: int
    seed_article_keys: list[str]
    tema_first_mode: str | None  # surfaced only when v5 retriever fires
    tema_first_topic_key: str | None
    tema_first_anchor_count: int | None
    planner_query_mode: str | None
    effective_topic: str | None
    trace_id: str | None
    wall_ms: int


# ── Pipeline invocation ───────────────────────────────────────────────────


def _invoke_pipeline(query: str) -> tuple[Any, dict[str, Any], float]:
    """Fire one query end-to-end through the production-equivalent path.

    Mirrors the contract used by ``scripts/eval_retrieval.py:310-340``.
    Returns ``(response, diagnostics_dict, wall_seconds)``.
    """
    from lia_graph.pipeline_c.contracts import PipelineCRequest
    from lia_graph.pipeline_d import run_pipeline_d
    from lia_graph.topic_router import resolve_chat_topic

    routing = resolve_chat_topic(
        message=query, requested_topic=None, pais="colombia"
    )
    request = PipelineCRequest(
        message=query,
        pais="colombia",
        topic=routing.effective_topic,
        requested_topic=routing.requested_topic,
        secondary_topics=routing.secondary_topics,
        topic_adjusted=routing.topic_adjusted,
        topic_notice=routing.topic_notice,
        topic_adjustment_reason=routing.reason,
        topic_router_confidence=routing.confidence,
    )
    t0 = time.perf_counter()
    response = run_pipeline_d(request)
    wall_s = time.perf_counter() - t0
    diag = dict(getattr(response, "diagnostics", None) or {})
    # Attach effective_topic from routing for the panel doc.
    diag.setdefault("effective_topic", routing.effective_topic)
    return response, diag, wall_s


def _capture_mode_result(
    *,
    mode: str,
    env_value: str,
    query: str,
) -> ModeResult:
    """Set the env flag, invoke the pipeline, pluck the narrow diagnostics
    we surface in the panel doc.

    Keeps the error surface narrow: any exception is re-raised so the
    per-question handler can emit a failure row without caller logic.
    """
    os.environ["LIA_TEMA_FIRST_RETRIEVAL"] = env_value
    response, diag, wall_s = _invoke_pipeline(query)
    return ModeResult(
        mode=mode,
        env_flag_value=env_value,
        answer_markdown=str(getattr(response, "answer_markdown", "") or ""),
        retrieval_backend=diag.get("retrieval_backend"),
        graph_backend=diag.get("graph_backend"),
        primary_article_count=int(diag.get("primary_article_count") or 0),
        connected_article_count=int(diag.get("connected_article_count") or 0),
        related_reform_count=int(diag.get("related_reform_count") or 0),
        seed_article_keys=list(diag.get("seed_article_keys") or [])[:20],
        tema_first_mode=diag.get("tema_first_mode"),
        tema_first_topic_key=diag.get("tema_first_topic_key"),
        tema_first_anchor_count=diag.get("tema_first_anchor_count"),
        planner_query_mode=diag.get("planner_query_mode"),
        effective_topic=diag.get("effective_topic"),
        trace_id=str(getattr(response, "trace_id", "") or "") or None,
        wall_ms=int(wall_s * 1000),
    )


# ── Atomic-append output ──────────────────────────────────────────────────


def _append_row(path: Path, row: dict[str, Any]) -> None:
    """Append one JSON row + newline, flush + fsync so a kill -9 can't
    truncate the written line. Tested by ``test_run_ab_comparison.py``.
    """
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            # Non-POSIX filesystem; flush is best-effort.
            pass


def _load_completed_qids(path: Path) -> set[str]:
    """Read an existing output JSONL and return the set of qids already
    present. Malformed lines are skipped (not fatal — corrupted partial
    writes shouldn't block resume)."""
    qids: set[str] = set()
    if not path.exists():
        return qids
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            qid = row.get("qid")
            if isinstance(qid, str):
                qids.add(qid)
    return qids


# ── Manifest ──────────────────────────────────────────────────────────────


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


def _write_manifest(
    path: Path,
    *,
    manifest_tag: str,
    gold_path: Path,
    target: str,
    started_utc: str,
    completed_utc: str,
    started_bogota: str,
    completed_bogota: str,
    questions_attempted: int,
    questions_succeeded: int,
    questions_failed: list[dict[str, Any]],
    falkor_baseline: dict[str, Any] | None,
    pre_env_state: dict[str, str | None],
) -> None:
    body = {
        "manifest_tag": manifest_tag,
        "gold_path": str(gold_path),
        "target": target,
        "run_started_at_utc": started_utc,
        "run_completed_at_utc": completed_utc,
        "run_started_at_bogota": started_bogota,
        "run_completed_at_bogota": completed_bogota,
        "questions_attempted": questions_attempted,
        "questions_succeeded": questions_succeeded,
        "questions_failed": questions_failed,
        "falkor_baseline": falkor_baseline,
        "git_commit_sha": _git_sha(),
        "env_flag_matrix": {
            "modes_run": ["off", "on"],
            "pre_run_env_value_LIA_TEMA_FIRST_RETRIEVAL": pre_env_state.get(
                "LIA_TEMA_FIRST_RETRIEVAL"
            ),
        },
    }
    path.write_text(
        json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _load_falkor_baseline(path: Path | None) -> dict[str, Any] | None:
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


# ── Per-question orchestrator ─────────────────────────────────────────────


def _render_query(gold_row: dict[str, Any]) -> str:
    """Pick the query text to send. Single-point questions use
    ``initial_question_es`` verbatim. Multi-point (``type=M``) also sends
    the compound prompt — the pipeline's query_decomposer handles
    sub-questions internally, so we don't pre-split here.
    """
    return str(gold_row.get("initial_question_es") or "").strip()


def _process_one(
    *,
    gold_row: dict[str, Any],
    output_jsonl: Path,
) -> dict[str, Any]:
    """Run both modes for one question, append one row, return summary."""
    qid = str(gold_row.get("qid") or "")
    query = _render_query(gold_row)
    if not qid or not query:
        failure = {
            "qid": qid or "<missing>",
            "error": "gold row missing qid or initial_question_es",
            "mode_failed": "both",
        }
        _append_row(output_jsonl, failure)
        return {"qid": qid, "ok": False, "error": "missing_fields"}

    row: dict[str, Any] = {
        "qid": qid,
        "type": gold_row.get("type"),
        "query_shape": gold_row.get("query_shape"),
        "macro_area": gold_row.get("macro_area"),
        "query": query,
        "expected_topic": gold_row.get("expected_topic"),
        "expected_subtopic": gold_row.get("expected_subtopic"),
        "expected_article_keys": list(gold_row.get("expected_article_keys") or []),
        "sub_questions": gold_row.get("sub_questions"),
        "followup_question_es": gold_row.get("followup_question_es"),
    }

    # Prior mode.
    try:
        prior = _capture_mode_result(mode="prior", env_value="off", query=query)
        row["prior"] = prior.__dict__
    except Exception as exc:  # noqa: BLE001
        row["prior_error"] = {
            "error": repr(exc),
            "traceback": traceback.format_exc(limit=12),
        }

    # New mode.
    try:
        new = _capture_mode_result(mode="new", env_value="on", query=query)
        row["new"] = new.__dict__
    except Exception as exc:  # noqa: BLE001
        row["new_error"] = {
            "error": repr(exc),
            "traceback": traceback.format_exc(limit=12),
        }

    _append_row(output_jsonl, row)
    ok = "prior" in row and "new" in row
    return {"qid": qid, "ok": ok}


# ── CLI ───────────────────────────────────────────────────────────────────


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_ab_comparison",
        description=(
            "A/B run the 30-question gold set with "
            "LIA_TEMA_FIRST_RETRIEVAL=off vs =on. Appends results to a "
            "per-run JSONL; renderer produces the panel markdown."
        ),
    )
    parser.add_argument(
        "--gold",
        required=True,
        help="Path to gold JSONL (e.g. evals/gold_retrieval_v1.jsonl).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory that will hold ab_comparison_<ts>.jsonl + manifest.",
    )
    parser.add_argument(
        "--manifest-tag",
        default="v5_tema_first_vs_prior",
        help="Free-text tag embedded in output filenames.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N questions (dry-run convenience).",
    )
    parser.add_argument(
        "--resume",
        default=None,
        help="Path to an existing output JSONL; skip qids already present.",
    )
    parser.add_argument(
        "--target",
        default="production",
        choices=["production", "wip"],
        help="Supabase target (default production).",
    )
    parser.add_argument(
        "--falkor-baseline",
        default="artifacts/eval/falkor_baseline_v5.json",
        help="Optional baseline snapshot file for the manifest.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_argparser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    gold_path = Path(args.gold)
    if not gold_path.exists():
        print(f"[run_ab_comparison] gold not found: {gold_path}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_tag = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in args.manifest_tag
    )[:64]

    if args.resume:
        output_jsonl = Path(args.resume)
        completed = _load_completed_qids(output_jsonl)
        print(
            f"[run_ab_comparison] resuming from {output_jsonl} — "
            f"{len(completed)} qids already done.",
            file=sys.stderr,
        )
    else:
        output_jsonl = output_dir / f"ab_comparison_{ts}_{safe_tag}.jsonl"
        completed = set()
    manifest_path = output_jsonl.with_suffix("")
    manifest_path = Path(str(manifest_path) + "_manifest.json")

    gold_rows = _load_gold(gold_path)
    if args.limit is not None:
        gold_rows = gold_rows[: int(args.limit)]

    # Record pre-run env state so the manifest is honest about what was set.
    pre_env = {
        "LIA_TEMA_FIRST_RETRIEVAL": os.environ.get("LIA_TEMA_FIRST_RETRIEVAL"),
    }

    # SIGINT: finish current pair, then exit cleanly.
    stop_flag = {"stop": False}

    def _on_sigint(signum: int, frame: Any) -> None:
        stop_flag["stop"] = True
        print(
            "[run_ab_comparison] SIGINT received — finishing current pair "
            "then exiting.",
            file=sys.stderr,
        )

    signal.signal(signal.SIGINT, _on_sigint)

    started_utc = _utc_iso_now()
    started_bogota = _bogota_now()
    attempted = 0
    failed: list[dict[str, Any]] = []

    for row in gold_rows:
        qid = str(row.get("qid") or "")
        if qid in completed:
            continue
        if stop_flag["stop"]:
            break
        attempted += 1
        outcome = _process_one(gold_row=row, output_jsonl=output_jsonl)
        if not outcome.get("ok"):
            failed.append(outcome)
        print(
            f"[run_ab_comparison] qid={qid} ok={outcome.get('ok')}",
            file=sys.stderr,
        )

    completed_utc = _utc_iso_now()
    completed_bogota = _bogota_now()

    # Restore pre-run env state.
    original = pre_env.get("LIA_TEMA_FIRST_RETRIEVAL")
    if original is None:
        os.environ.pop("LIA_TEMA_FIRST_RETRIEVAL", None)
    else:
        os.environ["LIA_TEMA_FIRST_RETRIEVAL"] = original

    _write_manifest(
        manifest_path,
        manifest_tag=safe_tag,
        gold_path=gold_path,
        target=args.target,
        started_utc=started_utc,
        completed_utc=completed_utc,
        started_bogota=started_bogota,
        completed_bogota=completed_bogota,
        questions_attempted=attempted,
        questions_succeeded=attempted - len(failed),
        questions_failed=failed,
        falkor_baseline=_load_falkor_baseline(
            Path(args.falkor_baseline) if args.falkor_baseline else None
        ),
        pre_env_state=pre_env,
    )

    print(
        json.dumps(
            {
                "ok": True,
                "output_jsonl": str(output_jsonl),
                "manifest": str(manifest_path),
                "questions_attempted": attempted,
                "questions_failed": len(failed),
                "started_bogota": started_bogota,
                "completed_bogota": completed_bogota,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
