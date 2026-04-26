#!/usr/bin/env python3
"""100qs accountant eval — Claude-as-judge.

Takes a run JSONL produced by `scripts/run_100qs_eval.py` and the rubric
in `evals/100qs_rubric.yaml`, calls the Anthropic API once per question
with the judge prompt, parses the structured JSON verdict, and writes:

    evals/runs/<run-stem>__judged.jsonl   — per-question judge verdicts
    evals/runs/<run-stem>__summary.json   — aggregated scores + gaps

Aggregation produces:
    - macro_pass_percent              (overall, weighted across 7 dims)
    - per-dimension averages          (1–5 → 0–1)
    - per-profile / per-category macro averages
    - weak_questions                  (total < weak_question_threshold)
    - weak_dimensions                 (mean dim score < weak_dimension_threshold)
    - corpus_gap_clusters             (gap count ≥ corpus_gap_min_cluster_size)

Usage
-----
    export ANTHROPIC_API_KEY=sk-ant-...
    PYTHONPATH=src:. uv run python scripts/judge_100qs.py \
        --run-file evals/runs/100qs_dev_local_20260425T193000Z.jsonl

    # smoke (cheap):
    PYTHONPATH=src:. uv run python scripts/judge_100qs.py \
        --run-file evals/runs/100qs_dev_local_xxx.jsonl --limit 3

System prompt is sent with `cache_control: ephemeral` so the rubric stays
warm across the 100 calls (Anthropic prompt cache, 5-min TTL).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import httpx
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUBRIC = REPO_ROOT / "evals" / "100qs_rubric.yaml"

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

DEFAULT_JUDGE_MODEL = "claude-sonnet-4-6"

DIMENSIONS = [
    "exactitud_normativa",
    "aplicabilidad_operativa",
    "completitud",
    "actualizacion",
    "claridad_profesional",
    "prudencia_fiscal",
    "soporte_documental",
]

_BOGOTA = _dt.timezone(_dt.timedelta(hours=-5))


def _bogota_now() -> str:
    return _dt.datetime.now(_BOGOTA).strftime("%Y-%m-%d %-I:%M:%S %p").lstrip("0")


def _utc_iso_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


# ── IO ──────────────────────────────────────────────────────────────────


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"[judge_100qs] {path} invalid JSON line: {exc}")
    return rows


def _atomic_append_json(path: Path, row: dict[str, Any]) -> None:
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass


def _completed_judged_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids: set[str] = set()
    for r in _load_jsonl(path):
        if r.get("ok") and r.get("id"):
            ids.add(str(r["id"]))
    return ids


# ── Rubric → prompts ────────────────────────────────────────────────────


def _format_dimensions_block(rubric: dict[str, Any]) -> str:
    lines: list[str] = ["## Dimensiones de evaluación (puntaje 1–5 cada una)"]
    dims = rubric.get("dimensions") or {}
    for name in DIMENSIONS:
        d = dims.get(name) or {}
        weight = d.get("weight")
        desc = str(d.get("description") or "").strip()
        scale = d.get("scale") or {}
        lines.append("")
        lines.append(f"### {name}  (peso base: {weight})")
        lines.append(desc)
        lines.append("")
        lines.append("Anclas de la escala:")
        for level in (5, 4, 3, 2, 1):
            anchor = scale.get(level) or scale.get(str(level)) or ""
            lines.append(f"  {level}: {anchor}")
    overrides = rubric.get("profile_overrides") or {}
    if overrides:
        lines.append("")
        lines.append("## Ajustes de peso por perfil de pregunta")
        for profile, weights in overrides.items():
            pretty = ", ".join(f"{k}={v}" for k, v in weights.items())
            lines.append(f"- {profile}: {pretty}")
    return "\n".join(lines)


def _build_system_prompt(rubric: dict[str, Any]) -> str:
    base = str(rubric.get("judge_system_prompt") or "").strip()
    dims = _format_dimensions_block(rubric)
    return f"{base}\n\n{dims}"


def _build_user_message(rubric: dict[str, Any], run_row: dict[str, Any]) -> str:
    template = str(rubric.get("judge_user_template") or "").strip()
    citations = run_row.get("citations") or []
    cite_lines = []
    for c in citations[:20]:
        if not isinstance(c, dict):
            continue
        ref = c.get("ref") or c.get("doc_id") or "<sin-ref>"
        snippet = c.get("snippet")
        if snippet:
            cite_lines.append(f"- {ref} :: {snippet}")
        else:
            cite_lines.append(f"- {ref}")
    citations_block = "\n".join(cite_lines) if cite_lines else "(LIA no devolvió citaciones estructuradas)"

    sources = run_row.get("reference_sources") or []
    sources_block = "\n".join(f"- {s}" for s in sources) if sources else "(la referencia no listó fuentes — apóyate en el cuerpo de la respuesta de referencia)"

    answer = (run_row.get("answer_markdown") or run_row.get("answer_concise") or "").strip()
    return template.format(
        question=str(run_row.get("question") or "").strip(),
        lia_answer=answer or "(LIA devolvió respuesta vacía)",
        reference_answer=str(run_row.get("reference_answer") or "").strip(),
        reference_sources=sources_block,
        lia_citations=citations_block,
    )


# ── Anthropic call ──────────────────────────────────────────────────────


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    # Try fenced block first.
    match = _JSON_BLOCK_RE.search(text)
    candidate = match.group(1) if match else text
    # Try direct parse.
    try:
        obj = json.loads(candidate)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    # Last-ditch: locate first { ... } span.
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(candidate[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _call_judge(
    client: httpx.Client,
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    timeout: float,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [{"role": "user", "content": user_message}],
    }
    resp = client.post(
        ANTHROPIC_API_URL,
        headers=headers,
        json=body,
        timeout=timeout,
    )
    if resp.status_code >= 400:
        return None, {
            "error": f"http_{resp.status_code}",
            "body_preview": resp.text[:1000],
        }
    payload = resp.json()
    content = payload.get("content") or []
    text_parts = [
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    raw_text = "\n".join(text_parts).strip()
    parsed = _extract_json(raw_text)
    usage = payload.get("usage") or {}
    meta = {
        "raw_text": raw_text,
        "usage": usage,
        "stop_reason": payload.get("stop_reason"),
    }
    if not parsed:
        meta["error"] = "judge_json_parse_failed"
    return parsed, meta


# ── Aggregation ─────────────────────────────────────────────────────────


def _resolve_weights(rubric: dict[str, Any], profile: str | None) -> dict[str, float]:
    base = {
        name: float((rubric.get("dimensions") or {}).get(name, {}).get("weight") or 0.0)
        for name in DIMENSIONS
    }
    overrides = (rubric.get("profile_overrides") or {}).get(profile or "")
    if isinstance(overrides, dict):
        for name, w in overrides.items():
            if name in base:
                base[name] = float(w)
    # Renormalize so weights sum to 1.0 (defensive — config may not).
    total = sum(base.values())
    if total > 0:
        base = {k: v / total for k, v in base.items()}
    return base


def _question_score_percent(scores: dict[str, Any], weights: dict[str, float]) -> float:
    total = 0.0
    for name in DIMENSIONS:
        entry = scores.get(name)
        if not isinstance(entry, dict):
            continue
        try:
            s = float(entry.get("score"))
        except (TypeError, ValueError):
            continue
        s = max(1.0, min(5.0, s))
        total += (s / 5.0) * weights.get(name, 0.0)
    return round(total * 100.0, 2)


def _summarize(
    judged_rows: list[dict[str, Any]],
    rubric: dict[str, Any],
) -> dict[str, Any]:
    g = rubric.get("global") or {}
    pass_threshold = float(g.get("pass_threshold_percent", 75.0))
    weak_dim_thr = float(g.get("weak_dimension_threshold", 0.4))
    weak_q_thr = float(g.get("weak_question_threshold", 50.0))
    cluster_min = int(g.get("corpus_gap_min_cluster_size", 3))

    successful = [r for r in judged_rows if r.get("ok") and isinstance(r.get("scores"), dict)]
    failed = [r for r in judged_rows if not r.get("ok")]

    per_q_totals: list[tuple[dict[str, Any], float]] = []
    dim_means: dict[str, list[float]] = defaultdict(list)
    by_profile: dict[str, list[float]] = defaultdict(list)
    by_category: dict[str, list[float]] = defaultdict(list)

    for r in successful:
        weights = _resolve_weights(rubric, r.get("evaluation_profile"))
        pct = _question_score_percent(r["scores"], weights)
        per_q_totals.append((r, pct))
        for name in DIMENSIONS:
            entry = r["scores"].get(name)
            if isinstance(entry, dict):
                try:
                    dim_means[name].append(float(entry.get("score")) / 5.0)
                except (TypeError, ValueError):
                    pass
        if r.get("evaluation_profile"):
            by_profile[r["evaluation_profile"]].append(pct)
        if r.get("category"):
            by_category[r["category"]].append(pct)

    macro = (
        round(sum(pct for _, pct in per_q_totals) / len(per_q_totals), 2)
        if per_q_totals
        else 0.0
    )

    weak_questions = [
        {
            "id": r.get("id"),
            "category": r.get("category"),
            "evaluation_profile": r.get("evaluation_profile"),
            "score_percent": pct,
            "overall_assessment": r.get("overall_assessment"),
        }
        for r, pct in per_q_totals
        if pct < weak_q_thr
    ]

    dim_avg = {name: round(sum(v) / len(v), 3) if v else 0.0 for name, v in dim_means.items()}
    weak_dimensions = [name for name, v in dim_avg.items() if v < weak_dim_thr]

    profile_avg = {
        p: round(sum(v) / len(v), 2) if v else 0.0 for p, v in by_profile.items()
    }
    category_avg = {
        c: round(sum(v) / len(v), 2) if v else 0.0 for c, v in by_category.items()
    }

    # Corpus gap clustering: collapse free-text gap strings to lowercase tokens
    # and cluster by exact-string match. This is intentionally crude — a real
    # taxonomy mapping (per rubric.gap_analysis.taxonomy) is a follow-up.
    gap_counter: dict[str, int] = defaultdict(int)
    gap_examples: dict[str, list[str]] = defaultdict(list)
    for r in successful:
        for gap in r.get("corpus_gaps") or []:
            key = str(gap).strip().lower()
            if not key:
                continue
            gap_counter[key] += 1
            if len(gap_examples[key]) < 5:
                gap_examples[key].append(str(r.get("id") or ""))
    gap_clusters = sorted(
        (
            {"gap": key, "count": cnt, "example_ids": gap_examples[key]}
            for key, cnt in gap_counter.items()
            if cnt >= cluster_min
        ),
        key=lambda x: x["count"],
        reverse=True,
    )

    return {
        "macro_pass_percent": macro,
        "pass_threshold_percent": pass_threshold,
        "passes_global_threshold": macro >= pass_threshold,
        "n_judged_ok": len(successful),
        "n_judge_failed": len(failed),
        "per_dimension_mean_0_1": dim_avg,
        "weak_dimensions": weak_dimensions,
        "by_evaluation_profile_percent": profile_avg,
        "by_category_percent": category_avg,
        "weak_questions": sorted(weak_questions, key=lambda x: x["score_percent"]),
        "weak_question_threshold_percent": weak_q_thr,
        "weak_dimension_threshold_0_1": weak_dim_thr,
        "corpus_gap_clusters": gap_clusters,
        "corpus_gap_min_cluster_size": cluster_min,
    }


# ── CLI ─────────────────────────────────────────────────────────────────


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="judge_100qs",
        description=(
            "Run Claude-as-judge over a 100qs run JSONL using `100qs_rubric.yaml`. "
            "Writes per-question verdicts and an aggregated summary."
        ),
    )
    parser.add_argument(
        "--run-file",
        required=True,
        help="Path to a run jsonl produced by run_100qs_eval.py.",
    )
    parser.add_argument(
        "--rubric",
        default=str(DEFAULT_RUBRIC),
        help=f"Path to rubric YAML (default {DEFAULT_RUBRIC.relative_to(REPO_ROOT)}).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_JUDGE_MODEL,
        help=f"Anthropic model (default {DEFAULT_JUDGE_MODEL}).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=2048,
        help="max_tokens for the judge response (default 2048).",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=120.0,
        help="HTTP timeout per call (default 120s).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Judge only the first N rows (smoke convenience).",
    )
    parser.add_argument(
        "--inter-call-pause-seconds",
        type=float,
        default=0.0,
        help="Optional pause between API calls (default 0).",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Skip API calls — just re-aggregate an existing __judged.jsonl.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_argparser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    run_path = Path(args.run_file)
    if not run_path.exists():
        print(f"[judge_100qs] run file not found: {run_path}", file=sys.stderr)
        return 2

    rubric_path = Path(args.rubric)
    if not rubric_path.exists():
        print(f"[judge_100qs] rubric not found: {rubric_path}", file=sys.stderr)
        return 2

    with rubric_path.open("r", encoding="utf-8") as fh:
        rubric = yaml.safe_load(fh) or {}

    judged_path = run_path.with_name(run_path.stem + "__judged.jsonl")
    summary_path = run_path.with_name(run_path.stem + "__summary.json")

    if args.summary_only:
        if not judged_path.exists():
            print(f"[judge_100qs] cannot summarize — {judged_path} not found", file=sys.stderr)
            return 2
        judged_rows = _load_jsonl(judged_path)
        summary = _summarize(judged_rows, rubric)
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"ok": True, "summary": str(summary_path), "summary_inline": summary}, ensure_ascii=False))
        return 0

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("[judge_100qs] ANTHROPIC_API_KEY missing", file=sys.stderr)
        return 3

    run_rows = _load_jsonl(run_path)
    pending = [r for r in run_rows if r.get("ok") and r.get("answer_markdown") or r.get("answer_concise")]
    if args.limit is not None:
        pending = pending[: int(args.limit)]
    already = _completed_judged_ids(judged_path)
    pending = [r for r in pending if str(r.get("id")) not in already]

    system_prompt = _build_system_prompt(rubric)

    started_utc = _utc_iso_now()
    started_bogota = _bogota_now()

    print(
        f"[judge_100qs] start model={args.model} run={run_path.name} "
        f"pending={len(pending)} already_judged={len(already)} "
        f"out={judged_path.name}",
        file=sys.stderr,
    )

    with httpx.Client(timeout=args.timeout_seconds) as client:
        for idx, run_row in enumerate(pending, start=1):
            qid = str(run_row.get("id") or f"_idx{idx}")
            user_message = _build_user_message(rubric, run_row)
            t0 = time.perf_counter()
            try:
                parsed, meta = _call_judge(
                    client,
                    api_key=api_key,
                    model=args.model,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    max_tokens=int(args.max_tokens),
                    timeout=float(args.timeout_seconds),
                )
            except Exception as exc:  # noqa: BLE001
                parsed, meta = None, {"error": f"call_exception={exc!r}"}
            wall_ms = int((time.perf_counter() - t0) * 1000)

            ok = parsed is not None and isinstance(parsed.get("scores"), dict)
            row_out: dict[str, Any] = {
                "id": qid,
                "ok": ok,
                "category": run_row.get("category"),
                "topic": run_row.get("topic"),
                "evaluation_profile": run_row.get("evaluation_profile"),
                "wall_ms": wall_ms,
                "model": args.model,
                "usage": meta.get("usage"),
                "stop_reason": meta.get("stop_reason"),
            }
            if ok:
                row_out["scores"] = parsed["scores"]
                row_out["fuentes_faltantes"] = parsed.get("fuentes_faltantes") or []
                row_out["errores_normativos"] = parsed.get("errores_normativos") or []
                row_out["informacion_omitida"] = parsed.get("informacion_omitida") or []
                row_out["corpus_gaps"] = parsed.get("corpus_gaps") or []
                row_out["overall_assessment"] = parsed.get("overall_assessment")
            else:
                row_out["error"] = meta.get("error") or "unknown_judge_failure"
                row_out["raw_text_preview"] = (meta.get("raw_text") or "")[:600]
            _atomic_append_json(judged_path, row_out)

            marker = "ok" if ok else f"err({row_out.get('error')})"
            print(
                f"[judge_100qs] {idx}/{len(pending)} {qid} {marker} ({wall_ms}ms)",
                file=sys.stderr,
            )
            if args.inter_call_pause_seconds > 0 and idx < len(pending):
                time.sleep(float(args.inter_call_pause_seconds))

    completed_utc = _utc_iso_now()
    completed_bogota = _bogota_now()

    judged_rows = _load_jsonl(judged_path)
    summary = _summarize(judged_rows, rubric)
    summary["run_started_at_utc"] = started_utc
    summary["run_completed_at_utc"] = completed_utc
    summary["run_started_at_bogota"] = started_bogota
    summary["run_completed_at_bogota"] = completed_bogota
    summary["model"] = args.model
    summary["run_file"] = str(run_path)
    summary["judged_file"] = str(judged_path)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ok": True,
                "judged_file": str(judged_path),
                "summary": str(summary_path),
                "macro_pass_percent": summary["macro_pass_percent"],
                "pass_threshold_percent": summary["pass_threshold_percent"],
                "passes_global_threshold": summary["passes_global_threshold"],
                "n_judged_ok": summary["n_judged_ok"],
                "n_judge_failed": summary["n_judge_failed"],
                "weak_dimensions": summary["weak_dimensions"],
                "started_bogota": started_bogota,
                "completed_bogota": completed_bogota,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
