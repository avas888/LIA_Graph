"""Topic-alignment harness — third sibling, after eval_retrieval.py and
eval_citations.py.

Why this exists
---------------
The citation-faithfulness harness (2026-04-22) surfaced that ~15% of
non-abstaining gold answers were topically wrong while citing real
articles with authoritative formatting — citation precision was 0.99,
but the answer body discussed a different tax or regime than the
accountant asked about. Retrieval recall and citation faithfulness
both looked acceptable; the failure was at topic granularity.

This harness measures the topic-level signal every other harness misses.
Three metrics, all derived from what the pipeline already emits:

- **body_vs_router_alignment** — for non-abstention answers, fraction
  where the top-scoring topic of the answer body matches the topic
  that the router handed to the planner. Measures pipeline-internal
  consistency: did the writer stay on the topic the router chose?
- **body_vs_expected_alignment** — fraction where the top-scoring topic
  of the answer body matches the gold's ``expected_topic``. Measures
  product correctness: did the accountant get an answer about the
  right thing?
- **safety_abstention_rate** — fraction of queries that trigger
  ``answer_mode == "topic_safety_abstention"`` (router silent-failure
  or borderline-confidence misalignment). Must move in a reasonable
  band — too low means the safety checks are missing wrong-answer
  cases; too high means they're abstaining on valid queries.

Plus a companion observability stat: **misalignment_detection_rate** —
fraction of answers where ``diagnostics.topic_safety.misalignment`` is
True but the answer was still served (hedged, not abstained).

Same methodology-gated regression-vs-baseline CI pattern as the other
two harnesses. Committed to ``evals/alignment_baseline.json``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TOP_K_DEFAULT = 10
BASELINE_PATH_DEFAULT = Path("evals/alignment_baseline.json")
TOLERANCE_PP_DEFAULT = 2.0


# Aspirational red lines. Same rationale as the other harnesses — shown
# in the report, not the CI gate at n=30. Higher is better for alignment
# metrics; for safety_abstention_rate we care about a band, not a floor.
ASPIRATIONAL_RED_LINES: dict[str, Any] = {
    "body_vs_router_alignment": {"floor": 0.85},
    "body_vs_expected_alignment": {"floor": 0.70},
    "safety_abstention_rate": {"floor": 0.03, "ceiling": 0.25},
}


# ---------------------------------------------------------------------------
# Gold loading
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GoldSubQuestion:
    text_es: str
    expected_topic: str | None


@dataclass(frozen=True)
class GoldEntry:
    qid: str
    text_es: str
    expected_topic: str | None
    expected_topic_uncertain: bool
    sub_questions: tuple[GoldSubQuestion, ...]


def load_gold(path: Path) -> list[GoldEntry]:
    if not path.exists():
        raise FileNotFoundError(f"gold file not found: {path}")
    out: list[GoldEntry] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            raw = json.loads(line)
            subs_raw = raw.get("sub_questions") or ()
            sub_questions: tuple[GoldSubQuestion, ...] = ()
            if subs_raw:
                sub_questions = tuple(
                    GoldSubQuestion(
                        text_es=str(sq.get("text_es", "")).strip(),
                        expected_topic=(
                            str(sq["expected_topic"]).strip()
                            if sq.get("expected_topic")
                            else None
                        ),
                    )
                    for sq in subs_raw
                )
            out.append(
                GoldEntry(
                    qid=str(raw["qid"]),
                    text_es=str(raw.get("initial_question_es", "")).strip(),
                    expected_topic=(
                        str(raw["expected_topic"]).strip()
                        if raw.get("expected_topic")
                        else None
                    ),
                    expected_topic_uncertain=bool(raw.get("expected_topic_uncertain", False)),
                    sub_questions=sub_questions,
                )
            )
    return out


# ---------------------------------------------------------------------------
# Per-query probe
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PipelineProbe:
    answer_markdown: str
    answer_mode: str
    confidence_mode: str
    router_topic: str | None
    router_confidence: float
    topic_safety: dict[str, Any]
    retrieval_backend: str | None
    reranker_mode: str | None


def probe(query: str) -> PipelineProbe:
    from lia_graph.pipeline_c.contracts import PipelineCRequest
    from lia_graph.pipeline_d import run_pipeline_d
    from lia_graph.topic_router import resolve_chat_topic

    routing = resolve_chat_topic(message=query, requested_topic=None, pais="colombia")
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
    response = run_pipeline_d(request)
    diag = dict(response.diagnostics or {})
    reranker_diag = diag.get("reranker") or {}
    return PipelineProbe(
        answer_markdown=str(response.answer_markdown or ""),
        answer_mode=str(response.answer_mode or ""),
        confidence_mode=str(response.confidence_mode or ""),
        router_topic=routing.effective_topic,
        router_confidence=float(routing.confidence or 0.0),
        topic_safety=dict(diag.get("topic_safety") or {}),
        retrieval_backend=diag.get("retrieval_backend"),
        reranker_mode=(reranker_diag.get("mode") if isinstance(reranker_diag, dict) else None),
    )


# ---------------------------------------------------------------------------
# Body topic scoring — reuses the topic-router keyword scorer
# ---------------------------------------------------------------------------
def score_body_topics(text: str) -> list[tuple[str, int]]:
    """Return ``[(topic, score), ...]`` sorted by score desc, zeros removed."""
    from lia_graph.topic_router import _score_topic_keywords

    raw = _score_topic_keywords(text)
    scored = [
        (topic, int(data.get("score", 0)))
        for topic, data in raw.items()
    ]
    scored.sort(key=lambda pair: -pair[1])
    return [(topic, score) for topic, score in scored if score > 0]


# ---------------------------------------------------------------------------
# Per-entry scoring
# ---------------------------------------------------------------------------
@dataclass
class EntryScore:
    qid: str
    abstained_by_safety: bool
    answer_mode: str
    confidence_mode: str
    router_topic: str | None
    expected_topic: str | None
    expected_uncertain: bool
    body_top_topic: str | None
    body_top_score: int
    body_vs_router_match: bool | None      # None when abstained or no body
    body_vs_expected_match: bool | None    # None when abstained, no body, or uncertain gold
    misalignment_detected: bool
    # V2-2: per-sub-question routing correctness. For M-type gold entries
    # with a non-empty sub_questions list, fires each sub-question through
    # resolve_chat_topic and compares to the gold's sub-question-level
    # expected_topic. Reports the fraction matched for this entry.
    sub_question_router_matches: list[bool] = field(default_factory=list)
    retrieval_backend: str | None = None
    reranker_mode: str | None = None


def _score_sub_question_routing(entry: GoldEntry) -> list[bool]:
    """For M-type gold entries, fire each sub-question through the router
    and report whether it routes to the gold-annotated expected_topic.
    Skips sub-questions with no expected_topic (or `sub_questions=()`)."""
    from lia_graph.topic_router import resolve_chat_topic

    matches: list[bool] = []
    for sq in entry.sub_questions:
        if not sq.text_es or not sq.expected_topic:
            continue
        routing = resolve_chat_topic(
            message=sq.text_es, requested_topic=None, pais="colombia"
        )
        matches.append((routing.effective_topic or "") == sq.expected_topic)
    return matches


def _score_entry(entry: GoldEntry) -> EntryScore:
    result = probe(entry.text_es)
    abstained = result.answer_mode == "topic_safety_abstention"
    scored_body: list[tuple[str, int]] = []
    if not abstained and result.answer_markdown.strip():
        scored_body = score_body_topics(result.answer_markdown)

    body_top = scored_body[0][0] if scored_body else None
    body_top_score = scored_body[0][1] if scored_body else 0

    if abstained or body_top is None:
        body_vs_router = None
        body_vs_expected = None
    else:
        body_vs_router = (body_top == result.router_topic) if result.router_topic else None
        if entry.expected_topic is None or entry.expected_topic_uncertain:
            body_vs_expected = None
        else:
            body_vs_expected = (body_top == entry.expected_topic)

    misalignment = bool(((result.topic_safety or {}).get("misalignment") or {}).get("misaligned"))
    sub_q_matches = _score_sub_question_routing(entry)

    return EntryScore(
        qid=entry.qid,
        abstained_by_safety=abstained,
        answer_mode=result.answer_mode,
        confidence_mode=result.confidence_mode,
        router_topic=result.router_topic,
        expected_topic=entry.expected_topic,
        expected_uncertain=entry.expected_topic_uncertain,
        body_top_topic=body_top,
        body_top_score=body_top_score,
        body_vs_router_match=body_vs_router,
        body_vs_expected_match=body_vs_expected,
        misalignment_detected=misalignment,
        sub_question_router_matches=sub_q_matches,
        retrieval_backend=result.retrieval_backend,
        reranker_mode=result.reranker_mode,
    )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def _mean_bool(values: Iterable[bool | None]) -> tuple[float | None, int]:
    filtered = [v for v in values if v is not None]
    if not filtered:
        return None, 0
    hits = sum(1 for v in filtered if v)
    return hits / len(filtered), len(filtered)


@dataclass
class Aggregate:
    entry_scores: list[EntryScore]
    body_vs_router_alignment: float | None
    body_vs_router_denominator: int
    body_vs_expected_alignment: float | None
    body_vs_expected_denominator: int
    safety_abstention_rate: float
    safety_abstention_denominator: int
    misalignment_detection_rate: float
    misalignment_detection_denominator: int
    # V2-2: mean across all sub-questions of whether the router routes
    # each one to its gold-expected topic. Denominator is the total
    # count of sub-questions with a non-null expected_topic.
    sub_question_router_accuracy: float | None
    sub_question_router_denominator: int

    def to_flat(self) -> dict[str, float | None]:
        return {
            "body_vs_router_alignment": self.body_vs_router_alignment,
            "body_vs_expected_alignment": self.body_vs_expected_alignment,
            "safety_abstention_rate": self.safety_abstention_rate,
            "misalignment_detection_rate": self.misalignment_detection_rate,
            "sub_question_router_accuracy": self.sub_question_router_accuracy,
        }


def aggregate(entry_scores: list[EntryScore]) -> Aggregate:
    router_acc, router_denom = _mean_bool(e.body_vs_router_match for e in entry_scores)
    expected_acc, expected_denom = _mean_bool(e.body_vs_expected_match for e in entry_scores)
    n_abstained = sum(1 for e in entry_scores if e.abstained_by_safety)
    n_served = len(entry_scores) - n_abstained
    n_misaligned_served = sum(
        1 for e in entry_scores if e.misalignment_detected and not e.abstained_by_safety
    )
    all_sub_matches: list[bool] = []
    for e in entry_scores:
        all_sub_matches.extend(e.sub_question_router_matches)
    sub_q_acc = (
        sum(1 for v in all_sub_matches if v) / len(all_sub_matches)
        if all_sub_matches
        else None
    )

    return Aggregate(
        entry_scores=entry_scores,
        body_vs_router_alignment=router_acc,
        body_vs_router_denominator=router_denom,
        body_vs_expected_alignment=expected_acc,
        body_vs_expected_denominator=expected_denom,
        safety_abstention_rate=(n_abstained / len(entry_scores)) if entry_scores else 0.0,
        safety_abstention_denominator=len(entry_scores),
        misalignment_detection_rate=(n_misaligned_served / n_served) if n_served else 0.0,
        misalignment_detection_denominator=n_served,
        sub_question_router_accuracy=sub_q_acc,
        sub_question_router_denominator=len(all_sub_matches),
    )


# ---------------------------------------------------------------------------
# Baseline I/O (same pattern as eval_retrieval / eval_citations)
# ---------------------------------------------------------------------------
def dump_baseline(
    agg: Aggregate,
    path: Path,
    *,
    gold_path: Path,
    methodology: dict[str, Any],
) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gold_path": str(gold_path),
        "gold_entry_count": len(agg.entry_scores),
        "methodology": methodology,
        "metrics": agg.to_flat(),
        "observability": {
            "safety_abstention_denominator": agg.safety_abstention_denominator,
            "body_vs_router_denominator": agg.body_vs_router_denominator,
            "body_vs_expected_denominator": agg.body_vs_expected_denominator,
            "misalignment_detection_denominator": agg.misalignment_detection_denominator,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_baseline(path: Path) -> tuple[dict[str, float | None], dict[str, Any]] | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    metrics = raw.get("metrics")
    if not isinstance(metrics, dict):
        return None
    methodology = raw.get("methodology") or {}
    if not isinstance(methodology, dict):
        methodology = {}
    out: dict[str, float | None] = {}
    for k, v in metrics.items():
        if v is None:
            out[k] = None
        else:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                out[k] = None
    return out, methodology


def methodology_matches(current: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for key, cur_val in current.items():
        if key not in baseline:
            continue
        if baseline[key] != cur_val:
            mismatches.append(f"{key}: current={cur_val!r}, baseline={baseline[key]!r}")
    return mismatches


# alignment + misalignment_detection: higher is better.
# safety_abstention_rate: regression in EITHER direction if it moves
# outside its band; we treat it as a band, not a monotonic direction.
_HIGHER_BETTER = {
    "body_vs_router_alignment",
    "body_vs_expected_alignment",
    "misalignment_detection_rate",
    "sub_question_router_accuracy",
}
_BAND_METRIC = "safety_abstention_rate"


def compute_regressions(
    current: dict[str, float | None],
    baseline: dict[str, float | None],
    *,
    tolerance_pp: float,
) -> list[str]:
    tol = tolerance_pp / 100.0
    failures: list[str] = []
    for key, base_val in baseline.items():
        if base_val is None:
            continue
        cur_val = current.get(key)
        if cur_val is None:
            failures.append(f"{key}: current=None, baseline={base_val:.3f}")
            continue
        delta = cur_val - base_val
        if key in _HIGHER_BETTER and delta < -tol:
            failures.append(
                f"{key}: {cur_val:.3f} vs baseline {base_val:.3f} (Δ={delta:+.3f}, tolerance -{tol:.3f})"
            )
        elif key == _BAND_METRIC and abs(delta) > tol:
            failures.append(
                f"{key}: {cur_val:.3f} vs baseline {base_val:.3f} (Δ={delta:+.3f}, tolerance ±{tol:.3f}, band metric)"
            )
    return failures


def check_red_lines(agg: Aggregate) -> list[str]:
    failures: list[str] = []
    rule_router = ASPIRATIONAL_RED_LINES["body_vs_router_alignment"]
    rule_expected = ASPIRATIONAL_RED_LINES["body_vs_expected_alignment"]
    rule_abst = ASPIRATIONAL_RED_LINES["safety_abstention_rate"]
    if agg.body_vs_router_alignment is None:
        failures.append("body_vs_router_alignment: no data")
    elif agg.body_vs_router_alignment < rule_router["floor"]:
        failures.append(
            f"body_vs_router_alignment: {agg.body_vs_router_alignment:.3f} < floor {rule_router['floor']:.2f}"
        )
    if agg.body_vs_expected_alignment is None:
        failures.append("body_vs_expected_alignment: no data")
    elif agg.body_vs_expected_alignment < rule_expected["floor"]:
        failures.append(
            f"body_vs_expected_alignment: {agg.body_vs_expected_alignment:.3f} < floor {rule_expected['floor']:.2f}"
        )
    if agg.safety_abstention_rate < rule_abst["floor"]:
        failures.append(
            f"safety_abstention_rate: {agg.safety_abstention_rate:.3f} < band floor {rule_abst['floor']:.2f} — safety checks may be under-firing"
        )
    elif agg.safety_abstention_rate > rule_abst["ceiling"]:
        failures.append(
            f"safety_abstention_rate: {agg.safety_abstention_rate:.3f} > band ceiling {rule_abst['ceiling']:.2f} — safety checks may be over-firing"
        )
    return failures


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _fmt(value: float | None, width: int = 5) -> str:
    if value is None:
        return f"{'n/a':>{width}s}"
    return f"{value:>{width}.3f}"


def render_human(
    agg: Aggregate,
    *,
    gold_path: Path,
    baseline_metrics: dict[str, float | None] | None,
    tolerance_pp: float,
) -> str:
    lines: list[str] = []
    lines.append(f"# Topic-alignment harness — {gold_path} ({len(agg.entry_scores)} entries)")
    lines.append("")
    backends = {e.retrieval_backend for e in agg.entry_scores if e.retrieval_backend}
    rerankers = {e.reranker_mode for e in agg.entry_scores if e.reranker_mode}
    if backends:
        lines.append(f"  retrieval_backend seen: {sorted(backends)}")
    if rerankers:
        lines.append(f"  reranker_mode seen:     {sorted(rerankers)}")
    lines.append("")

    lines.append("## Core metrics")
    lines.append("")
    lines.append(
        f"  body_vs_router_alignment       {_fmt(agg.body_vs_router_alignment)}   n={agg.body_vs_router_denominator}   (writer stayed on router's topic)"
    )
    lines.append(
        f"  body_vs_expected_alignment     {_fmt(agg.body_vs_expected_alignment)}   n={agg.body_vs_expected_denominator}   (writer hit the gold-correct topic)"
    )
    lines.append(
        f"  safety_abstention_rate         {_fmt(agg.safety_abstention_rate)}   n={agg.safety_abstention_denominator}   (router-silent / low-confidence-misaligned)"
    )
    lines.append(
        f"  misalignment_detection_rate    {_fmt(agg.misalignment_detection_rate)}   n={agg.misalignment_detection_denominator}   (served answers flagged as hedged)"
    )
    lines.append(
        f"  sub_question_router_accuracy   {_fmt(agg.sub_question_router_accuracy)}   n={agg.sub_question_router_denominator}   (V2-2: each ¿…? routes to its gold topic)"
    )
    lines.append("")

    lines.append(f"## Regression vs baseline (tolerance ±{tolerance_pp:.1f}pp)")
    if baseline_metrics is None:
        lines.append("  No baseline file — run `--update-baseline` to commit one.")
    else:
        current = agg.to_flat()
        for key in sorted(baseline_metrics.keys()):
            base = baseline_metrics[key]
            cur = current.get(key)
            if cur is None or base is None:
                lines.append(f"  {key:<36s} {_fmt(cur, 6)} vs {_fmt(base, 6)}  Δ=n/a   n/a")
                continue
            delta = cur - base
            tol = tolerance_pp / 100.0
            if key in _HIGHER_BETTER:
                status = "  OK" if delta >= -tol else "  FAIL"
            elif key == _BAND_METRIC:
                status = "  OK" if abs(delta) <= tol else "  FAIL"
            else:
                status = "  OK"
            lines.append(
                f"  {key:<36s} {_fmt(cur, 6)} vs {_fmt(base, 6)}  Δ={delta:+.3f}  {status}"
            )
    lines.append("")

    lines.append("## Aspirational red lines")
    for key, rule in ASPIRATIONAL_RED_LINES.items():
        if key == "body_vs_router_alignment":
            val = agg.body_vs_router_alignment
            lines.append(f"  body_vs_router_alignment       target >= {rule['floor']:.2f}   actual {_fmt(val)}")
        elif key == "body_vs_expected_alignment":
            val = agg.body_vs_expected_alignment
            lines.append(f"  body_vs_expected_alignment     target >= {rule['floor']:.2f}   actual {_fmt(val)}")
        elif key == "safety_abstention_rate":
            val = agg.safety_abstention_rate
            lines.append(
                f"  safety_abstention_rate         band [{rule['floor']:.2f}, {rule['ceiling']:.2f}]   actual {_fmt(val)}"
            )
    lines.append("")

    lines.append("## Per-entry breakdown")
    lines.append(
        f"  {'qid':<6s} {'mode':<24s} {'router':<22s} {'body_top':<22s} {'bodyR':>6s} {'bodyE':>6s} {'mis':>4s}"
    )
    for e in agg.entry_scores:
        bodyR = {True: "   OK", False: " FAIL", None: "   n/a"}[e.body_vs_router_match]
        bodyE = {True: "   OK", False: " FAIL", None: "   n/a"}[e.body_vs_expected_match]
        mis = " MIS" if e.misalignment_detected else "    "
        router_str = (e.router_topic or "—")[:20]
        body_str = (e.body_top_topic or "—")[:20]
        mode_str = e.answer_mode[:22]
        lines.append(
            f"  {e.qid:<6s} {mode_str:<24s} {router_str:<22s} {body_str:<22s} {bodyR:>6s} {bodyE:>6s} {mis:>4s}"
        )
    return "\n".join(lines)


def render_json(
    agg: Aggregate,
    *,
    baseline_metrics: dict[str, float | None] | None,
    tolerance_pp: float,
) -> str:
    current = agg.to_flat()
    regressions: list[str] = []
    if baseline_metrics is not None:
        regressions = compute_regressions(current, baseline_metrics, tolerance_pp=tolerance_pp)
    payload = {
        "metrics": current,
        "baseline_metrics": baseline_metrics,
        "regressions": regressions,
        "tolerance_pp": tolerance_pp,
        "aspirational_red_lines": ASPIRATIONAL_RED_LINES,
        "observability": {
            "safety_abstention_denominator": agg.safety_abstention_denominator,
            "body_vs_router_denominator": agg.body_vs_router_denominator,
            "body_vs_expected_denominator": agg.body_vs_expected_denominator,
            "misalignment_detection_denominator": agg.misalignment_detection_denominator,
        },
        "entries": [
            {
                "qid": e.qid,
                "abstained_by_safety": e.abstained_by_safety,
                "answer_mode": e.answer_mode,
                "confidence_mode": e.confidence_mode,
                "router_topic": e.router_topic,
                "expected_topic": e.expected_topic,
                "expected_uncertain": e.expected_uncertain,
                "body_top_topic": e.body_top_topic,
                "body_top_score": e.body_top_score,
                "body_vs_router_match": e.body_vs_router_match,
                "body_vs_expected_match": e.body_vs_expected_match,
                "misalignment_detected": e.misalignment_detected,
            }
            for e in agg.entry_scores
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Topic-alignment harness (third sibling).")
    parser.add_argument("--gold", type=Path, default=Path("evals/gold_retrieval_v1.jsonl"))
    parser.add_argument("--top-k", type=int, default=TOP_K_DEFAULT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH_DEFAULT)
    parser.add_argument("--fail-on-regression", action="store_true")
    parser.add_argument("--tolerance-pp", type=float, default=TOLERANCE_PP_DEFAULT)
    parser.add_argument("--fail-under-red-lines", action="store_true")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    entries = load_gold(args.gold)
    if not entries:
        print(f"[eval_topic_alignment] gold file is empty: {args.gold}", file=sys.stderr)
        return 2

    scored: list[EntryScore] = []
    for entry in entries:
        scored.append(_score_entry(entry))
    agg = aggregate(scored)

    current_methodology: dict[str, Any] = {
        "top_k": int(args.top_k),
        "reranker_mode": str(os.getenv("LIA_RERANKER_MODE", "off")).strip().lower() or "off",
        "polish_enabled": bool(str(os.getenv("LIA_LLM_POLISH_ENABLED", "")).strip().lower() in {"1", "true", "yes", "on"}),
        "decompose_enabled": str(os.getenv("LIA_QUERY_DECOMPOSE", "off")).strip().lower() == "on",
    }

    loaded = load_baseline(args.baseline)
    baseline_metrics: dict[str, float | None] | None = None
    baseline_methodology: dict[str, Any] = {}
    if loaded is not None:
        baseline_metrics, baseline_methodology = loaded

    if args.update_baseline:
        dump_baseline(agg, args.baseline, gold_path=args.gold, methodology=current_methodology)
        print(f"[eval_topic_alignment] baseline written: {args.baseline}", file=sys.stderr)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            render_json(agg, baseline_metrics=baseline_metrics, tolerance_pp=args.tolerance_pp),
            encoding="utf-8",
        )

    if args.json:
        print(render_json(agg, baseline_metrics=baseline_metrics, tolerance_pp=args.tolerance_pp))
    else:
        print(
            render_human(
                agg,
                gold_path=args.gold,
                baseline_metrics=baseline_metrics,
                tolerance_pp=args.tolerance_pp,
            )
        )

    exit_code = 0
    if args.fail_on_regression:
        if baseline_metrics is None:
            print(
                f"[eval_topic_alignment] --fail-on-regression requested but no baseline at {args.baseline}",
                file=sys.stderr,
            )
            return 3
        method_mismatches = methodology_matches(current_methodology, baseline_methodology)
        if method_mismatches:
            print("", file=sys.stderr)
            print("[eval_topic_alignment] METHODOLOGY MISMATCH vs baseline:", file=sys.stderr)
            for msg in method_mismatches:
                print(f"  - {msg}", file=sys.stderr)
            return 4
        regressions = compute_regressions(
            agg.to_flat(), baseline_metrics, tolerance_pp=args.tolerance_pp
        )
        if regressions:
            print("", file=sys.stderr)
            print(f"[eval_topic_alignment] REGRESSION (tolerance ±{args.tolerance_pp:.1f}pp):", file=sys.stderr)
            for msg in regressions:
                print(f"  - {msg}", file=sys.stderr)
            exit_code = 1

    if args.fail_under_red_lines:
        failures = check_red_lines(agg)
        if failures:
            print("", file=sys.stderr)
            print("[eval_topic_alignment] ASPIRATIONAL RED LINE FAILURES:", file=sys.stderr)
            for msg in failures:
                print(f"  - {msg}", file=sys.stderr)
            exit_code = exit_code or 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
