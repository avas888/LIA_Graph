#!/usr/bin/env python3
"""Pure renderer: Phase-1 JSONL + manifest → side-by-side panel markdown.

Zero network. Deterministic for a given input. Output structure defined
in docs/quality_tests/evaluacion_ingestionfixtask_v1.md §5 Phase 2.

Each question block contains:
  * header (qid, macro_area, query_shape, type)
  * query + (if multi) sub_questions
  * **[PRIOR MODE]** answer + diagnostics
  * **[NEW MODE]**   answer + diagnostics
  * verdict placeholder YAML

Row-level error handling: when a row carries ``prior_error`` or
``new_error``, that mode block renders an ``**[ERROR]**`` banner with a
short traceback excerpt in place of the answer, so the panel can see
the failure without crashing the renderer.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


# ── Helpers ──────────────────────────────────────────────────────────────


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                # Skip corrupt line but log to stderr; don't abort rendering
                # — partial files are the norm after mid-run crashes.
                print(
                    f"[render_ab_markdown] {path} line {lineno}: skipping malformed JSON",
                    file=sys.stderr,
                )
    return out


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _fmt_diagnostics(mode_data: dict[str, Any]) -> str:
    """Render the <details><summary>Diagnostics</summary> block for one mode."""
    lines: list[str] = ["<details><summary>Diagnostics</summary>", ""]
    for key in (
        "retrieval_backend",
        "graph_backend",
        "primary_article_count",
        "connected_article_count",
        "related_reform_count",
        "tema_first_mode",
        "tema_first_topic_key",
        "tema_first_anchor_count",
        "planner_query_mode",
        "effective_topic",
        "coherence_mode",
        "coherence_misaligned",
        "coherence_reason",
        "wall_ms",
        "trace_id",
    ):
        lines.append(f"- {key}: {mode_data.get(key)}")
    seed_keys = mode_data.get("seed_article_keys") or []
    preview = seed_keys[:10]
    suffix = f" … (+{len(seed_keys) - 10} more)" if len(seed_keys) > 10 else ""
    lines.append(f"- seed_article_keys: {preview}{suffix}")
    lines.append("")
    lines.append("</details>")
    return "\n".join(lines)


def _render_error_block(err: dict[str, Any]) -> str:
    excerpt = str(err.get("traceback") or err.get("error") or "").strip()
    if len(excerpt) > 1500:
        excerpt = excerpt[:1500] + "\n…(truncated)…"
    return (
        "**[ERROR]** — this mode failed to produce an answer.\n\n"
        "```\n"
        f"{excerpt}\n"
        "```"
    )


def _render_question(row: dict[str, Any]) -> str:
    qid = row.get("qid", "??")
    macro = row.get("macro_area", "—")
    shape = row.get("query_shape", "—")
    type_ = row.get("type", "—")
    query = row.get("query", "")
    expected_topic = row.get("expected_topic") or "—"
    expected_sub = row.get("expected_subtopic") or "—"
    sub_questions = row.get("sub_questions") or []

    parts: list[str] = []
    parts.append(f"## {qid} — {macro} — {shape} — {type_}")
    parts.append("")
    parts.append(f"**Query.** {query}")
    parts.append("")
    if sub_questions:
        parts.append("**Sub-questions:**")
        for i, sq in enumerate(sub_questions, start=1):
            txt = (sq or {}).get("text_es") or ""
            parts.append(f"  {i}. {txt}")
        parts.append("")
    parts.append(
        f"**Expected topic:** `{expected_topic}`  "
        f"**Expected subtopic:** `{expected_sub}`"
    )
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("### **[PRIOR MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=off`")
    parts.append("")
    if "prior_error" in row:
        parts.append(_render_error_block(row["prior_error"]))
    else:
        prior = row.get("prior") or {}
        parts.append(str(prior.get("answer_markdown") or "").rstrip())
        parts.append("")
        parts.append(_fmt_diagnostics(prior))
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("### **[NEW MODE]** — `LIA_TEMA_FIRST_RETRIEVAL=on`")
    parts.append("")
    if "new_error" in row:
        parts.append(_render_error_block(row["new_error"]))
    else:
        new = row.get("new") or {}
        parts.append(str(new.get("answer_markdown") or "").rstrip())
        parts.append("")
        parts.append(_fmt_diagnostics(new))
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("**Panel verdict block**")
    parts.append("")
    parts.append("```yaml")
    parts.append("verdict:          # new_better | prior_better | tie | both_wrong | need_clarification")
    parts.append("notes:            # free text, one paragraph max")
    parts.append("```")
    parts.append("")
    return "\n".join(parts)


def _render_preamble(manifest: dict[str, Any]) -> str:
    tag = manifest.get("manifest_tag", "")
    started_bogota = manifest.get("run_started_at_bogota", "—")
    completed_bogota = manifest.get("run_completed_at_bogota", "—")
    started_utc = manifest.get("run_started_at_utc", "—")
    completed_utc = manifest.get("run_completed_at_utc", "—")
    sha = manifest.get("git_commit_sha", "—")
    baseline = manifest.get("falkor_baseline") or {}
    tn = baseline.get("TopicNode", "—")
    te = baseline.get("TEMA_edges", "—")
    an = baseline.get("ArticleNode", "—")
    stn = baseline.get("SubTopicNode", "—")

    lines = [
        "# A/B Evaluation: TEMA-first retrieval vs prior mode",
        "",
        f"**Run tag.** `{tag}`  ",
        f"**Started.**   {started_bogota} (Bogotá)  ·  {started_utc} (UTC)  ",
        f"**Completed.** {completed_bogota} (Bogotá)  ·  {completed_utc} (UTC)  ",
        f"**Git commit.** `{sha}`",
        "",
        (
            "**Falkor baseline (pre-run).** "
            f"TopicNode {tn}, TEMA edges {te}, ArticleNode {an}, SubTopicNode {stn}."
        ),
        "",
        "## Panel instructions (read first)",
        "",
        "Every question below has TWO answer blocks, clearly labeled ",
        "**[PRIOR MODE]** (legacy v4-era retrieval, baseline) and "
        "**[NEW MODE]** (v5 TEMA-first retrieval).",
        "",
        "For each question, read both blocks and fill the `verdict:` field with ONE of:",
        "",
        "- `new_better` — the NEW-mode answer is materially better for the reader",
        "- `prior_better` — the PRIOR-mode answer is materially better",
        "- `tie` — answers are equivalent in usefulness",
        "- `both_wrong` — neither answers the question correctly",
        "- `need_clarification` — the question is ambiguous / outside scope; no verdict",
        "",
        "Add one short paragraph in `notes:` if you want to explain.",
        "Do NOT edit the answer text or diagnostics blocks — the operator",
        "uses those verbatim when aggregating.",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def _render_aggregate_block() -> str:
    return "\n".join(
        [
            "## Aggregate (filled by operator after panel review)",
            "",
            "```yaml",
            "totals:",
            "  new_better:",
            "  prior_better:",
            "  tie:",
            "  both_wrong:",
            "  need_clarification:",
            "decision:           # flip_to_on | hold | rollback",
            "decision_reason:    # one-paragraph justification citing specific qids",
            "signed_off_by:",
            "signed_off_at_bogota:",
            "```",
            "",
        ]
    )


# ── Top-level render ─────────────────────────────────────────────────────


def render_md(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> str:
    parts: list[str] = [_render_preamble(manifest)]
    for row in rows:
        parts.append(_render_question(row))
    parts.append(_render_aggregate_block())
    return "\n".join(parts)


# ── CLI ──────────────────────────────────────────────────────────────────


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="render_ab_markdown",
        description="Render the A/B JSONL + manifest into a panel-reviewable markdown file.",
    )
    parser.add_argument("--jsonl", required=True, help="Path to ab_comparison_*.jsonl.")
    parser.add_argument("--manifest", required=True, help="Path to the companion _manifest.json.")
    parser.add_argument("--output", required=True, help="Output .md path.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_argparser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    rows = _load_jsonl(Path(args.jsonl))
    manifest = _load_manifest(Path(args.manifest))
    md = render_md(rows, manifest)
    Path(args.output).write_text(md + "\n", encoding="utf-8")
    print(f"[render_ab_markdown] wrote {args.output} ({len(rows)} questions)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
