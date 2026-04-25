"""Trace a query through the lexical planner layers and print a JSON diagnostic.

Backlog item E from `docs/done/next/structuralwork_v1_SEENOW.md`. Replaces the
ad-hoc Python block that was being retyped every time we investigated a
routing miss.

Only touches lexical layers (topic router, subtopic classifier, planner) —
no Supabase, no Falkor, no LLM. Safe to run in any environment without
cloud env vars. Use `--full` to also construct a `GraphRetrievalPlan` via
`build_graph_retrieval_plan` (same in-process, still no I/O).

Usage:
    python scripts/debug_query.py "La DIAN le envió un requerimiento..."
    python scripts/debug_query.py --topic renta "..."        # pin requested_topic
    python scripts/debug_query.py --full "..."               # include GraphRetrievalPlan
    python scripts/debug_query.py --per-sub-question "..."   # trace each ¿…? separately
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _trace_topic(message: str, requested_topic: str | None) -> dict[str, Any]:
    from lia_graph.topic_router import (
        _check_subtopic_overrides,
        _score_topic_keywords,
        resolve_chat_topic,
    )

    routing = resolve_chat_topic(message=message, requested_topic=requested_topic)
    scored = _score_topic_keywords(message)
    override = _check_subtopic_overrides(message)
    return {
        "effective_topic": routing.effective_topic,
        "requested_topic": routing.requested_topic,
        "secondary_topics": list(routing.secondary_topics),
        "mode": routing.mode,
        "confidence": round(float(routing.confidence), 4),
        "reason": routing.reason,
        "subtopic_override_hit": (
            {"topic": override[0], "keywords": list(override[1])} if override else None
        ),
        "keyword_scores": {
            topic: {
                "score": int(data["score"]),
                "strong_hits": list(data.get("strong_hits", ())),
                "weak_hits": list(data.get("weak_hits", ())),
            }
            for topic, data in sorted(
                scored.items(), key=lambda item: -int(item[1]["score"])
            )
        },
    }


def _trace_subtopic(message: str, effective_topic: str | None) -> dict[str, Any]:
    from lia_graph.pipeline_d.planner_query_modes import (
        _detect_sub_topic_intent,
        _get_subtopic_taxonomy,
    )

    if not effective_topic:
        return {"sub_topic_intent": None, "reason": "no_effective_topic"}
    tax = _get_subtopic_taxonomy()
    if tax is None:
        return {"sub_topic_intent": None, "reason": "taxonomy_unavailable"}
    candidates = tax.get_candidates_for(effective_topic)
    intent = _detect_sub_topic_intent(message, effective_topic)
    return {
        "sub_topic_intent": intent,
        "parent_topic": effective_topic,
        "candidate_count": len(candidates),
        "candidate_keys": [entry.key for entry in candidates],
    }


def _trace_sub_questions(message: str) -> list[str]:
    from lia_graph.pipeline_d.planner import _extract_user_sub_questions

    return list(_extract_user_sub_questions(message))


def _trace_plan(message: str, requested_topic: str | None) -> dict[str, Any]:
    from lia_graph.pipeline_c.contracts import PipelineCRequest
    from lia_graph.pipeline_d.planner import build_graph_retrieval_plan

    request = PipelineCRequest(message=message, requested_topic=requested_topic)
    plan = build_graph_retrieval_plan(request)
    return plan.to_dict()


def trace(
    message: str,
    *,
    requested_topic: str | None,
    full: bool,
    per_sub_question: bool,
) -> dict[str, Any]:
    topic_trace = _trace_topic(message, requested_topic)
    subtopic_trace = _trace_subtopic(message, topic_trace["effective_topic"])
    sub_questions = _trace_sub_questions(message)

    result: dict[str, Any] = {
        "query": message,
        "requested_topic": requested_topic,
        "topic": topic_trace,
        "subtopic": subtopic_trace,
        "sub_questions": sub_questions,
    }

    if per_sub_question and sub_questions:
        per_q: list[dict[str, Any]] = []
        for index, sub_q in enumerate(sub_questions, start=1):
            sub_topic_trace = _trace_topic(sub_q, requested_topic)
            sub_subtopic_trace = _trace_subtopic(
                sub_q, sub_topic_trace["effective_topic"]
            )
            per_q.append(
                {
                    "index": index,
                    "text": sub_q,
                    "topic": sub_topic_trace,
                    "subtopic": sub_subtopic_trace,
                }
            )
        result["per_sub_question"] = per_q

    if full:
        try:
            result["plan"] = _trace_plan(message, requested_topic)
        except Exception as exc:  # noqa: BLE001 — surface failure clearly in JSON
            result["plan_error"] = f"{type(exc).__name__}: {exc}"

    return result


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trace a query through the lexical planner layers.",
    )
    parser.add_argument("query", help="The user query string to trace")
    parser.add_argument(
        "--topic",
        dest="requested_topic",
        default=None,
        help="Pin the requested_topic (simulate the UI passing a topic hint)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Also run build_graph_retrieval_plan and include the plan dict",
    )
    parser.add_argument(
        "--per-sub-question",
        action="store_true",
        help="If the query has multiple ¿…? splits, trace each sub-question separately",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indent level (default 2; use 0 for compact)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    trace_result = trace(
        args.query,
        requested_topic=args.requested_topic,
        full=args.full,
        per_sub_question=args.per_sub_question,
    )
    indent = args.indent if args.indent > 0 else None
    print(json.dumps(trace_result, ensure_ascii=False, indent=indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
