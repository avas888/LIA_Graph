#!/usr/bin/env python3
"""Aggregate a §1.G SME validation run into a markdown report + verbatim doc.

Reads a run dir produced by `run_sme_validation.py` (containing per-Q JSON
files + classified.jsonl) and emits two artifacts in the same dir:

  1. report.md   — overall counts, per-topic 12×3 grid, per-profile,
                   routing accuracy, topics flagged for follow-up,
                   PASS/PARTIAL/FAIL decision.
  2. verbatim.md — every one of the responses reproduced word-for-word,
                   grouped by topic → profile, with the question, full
                   answer_markdown, citations, mode, effective_topic,
                   fallback_reason, latency, and assigned class.

Stdlib only. Bogotá AM/PM rendering for the human-facing timestamp on the
report header (machine fields stay UTC ISO).

Usage:
    PYTHONPATH=src:. uv run python scripts/eval/sme_validation_report.py <run_dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

_BOGOTA = timezone(timedelta(hours=-5), name="America/Bogota")

CLASS_ORDER = (
    "served_strong",
    "served_acceptable",
    "served_weak",
    "served_off_topic",
    "refused",
    "server_error",
)

CLASS_GLYPH = {
    "served_strong": "🟢 served_strong",
    "served_acceptable": "🟡 served_acceptable",
    "served_weak": "🟠 served_weak",
    "served_off_topic": "🔵 served_off_topic",
    "refused": "🔴 refused",
    "server_error": "💥 server_error",
}

PROFILE_ORDER = ("P1_directa", "P2_operativa", "P3_borde")
PROFILE_HEADER = {"P1_directa": "P1", "P2_operativa": "P2", "P3_borde": "P3"}


# Topic order: thin-corpus baseline order from
# `scripts/monitoring/thin_corpus_baseline.json`, with the SME's 12 topics.
TOPIC_ORDER = (
    "beneficio_auditoria",
    "firmeza_declaraciones",
    "regimen_sancionatorio_extemporaneidad",
    "descuentos_tributarios_renta",
    "tarifas_renta_y_ttd",
    "dividendos_y_distribucion_utilidades",
    "devoluciones_saldos_a_favor",
    "perdidas_fiscales_art147",
    "precios_de_transferencia",
    "impuesto_patrimonio_personas_naturales",
    "regimen_cambiario",
    "conciliacion_fiscal",
)


def _bogota_now() -> str:
    return datetime.now(_BOGOTA).strftime("%Y-%m-%d %I:%M:%S %p Bogotá")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _load_response(run_dir: Path, qid: str) -> dict[str, Any]:
    path = run_dir / f"{qid}.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Report (gauge)
# ---------------------------------------------------------------------------


def _decision(counts: dict[str, int]) -> tuple[str, str]:
    server_err = counts.get("server_error", 0)
    served = counts.get("served_strong", 0) + counts.get("served_acceptable", 0)
    total_executed = sum(counts.values()) - server_err

    # Infrastructure failures contaminate the gauge — re-run is required.
    if server_err > 0:
        return (
            "INCONCLUSIVE",
            f"{server_err}/36 server_error rows — re-run those qids before "
            f"interpreting the verdict. Of the {total_executed} executed: "
            f"{served} served_acceptable+.",
        )

    if served >= 22:
        return ("PASS", f"{served}/36 served_acceptable+ ≥ 22 threshold")
    if served >= 14:
        return ("PARTIAL", f"{served}/36 served_acceptable+ in [14, 21] band")
    return ("FAIL", f"{served}/36 served_acceptable+ ≤ 13 — reopen")


def _build_overall(rows: list[dict[str, Any]]) -> tuple[dict[str, int], str]:
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r["class"]] += 1
    lines = ["| Class | Count |", "|---|---|"]
    for c in CLASS_ORDER:
        lines.append(f"| {CLASS_GLYPH[c]} | {counts.get(c, 0)} |")
    lines.append(f"| **total** | **{sum(counts.values())}** |")
    return dict(counts), "\n".join(lines)


def _build_per_topic(rows: list[dict[str, Any]]) -> str:
    by_topic: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for r in rows:
        by_topic[r["topic_key_expected"]][r["profile"]] = r
    lines = ["| Topic | P1 directa | P2 operativa | P3 borde |", "|---|---|---|---|"]
    for topic in TOPIC_ORDER:
        cells = [topic]
        for profile in PROFILE_ORDER:
            row = by_topic.get(topic, {}).get(profile)
            cells.append(CLASS_GLYPH[row["class"]] if row else "—")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _build_per_profile(rows: list[dict[str, Any]]) -> str:
    by_profile: dict[str, dict[str, int]] = {p: defaultdict(int) for p in PROFILE_ORDER}
    for r in rows:
        by_profile[r["profile"]][r["class"]] += 1
    header = ["Profile"] + [CLASS_GLYPH[c] for c in CLASS_ORDER]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for p in PROFILE_ORDER:
        cells = [PROFILE_HEADER[p]]
        for c in CLASS_ORDER:
            cells.append(str(by_profile[p].get(c, 0)))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _build_routing(rows: list[dict[str, Any]]) -> str:
    correct = 0
    wrong: list[dict[str, Any]] = []
    unknown = 0
    for r in rows:
        actual = r.get("effective_topic")
        if actual is None:
            unknown += 1
            continue
        if actual == r["topic_key_expected"]:
            correct += 1
        else:
            wrong.append(r)
    lines = [
        f"- Correct routing: **{correct}/36**",
        f"- Wrong routing: **{len(wrong)}/36**",
        f"- Unknown effective_topic: **{unknown}/36**",
    ]
    if wrong:
        lines.append("")
        lines.append("| qid | expected | actual | class |")
        lines.append("|---|---|---|---|")
        for r in sorted(wrong, key=lambda x: x["qid"]):
            lines.append(
                f"| {r['qid']} | {r['topic_key_expected']} | "
                f"{r.get('effective_topic')!r} | {CLASS_GLYPH[r['class']]} |"
            )
    return "\n".join(lines)


def _build_followups(rows: list[dict[str, Any]], run_dir: Path) -> str:
    flagged_classes = {"served_weak", "served_off_topic", "refused", "server_error"}
    by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r["class"] in flagged_classes:
            by_topic[r["topic_key_expected"]].append(r)
    if not by_topic:
        return "_No topics flagged for follow-up._"
    parts: list[str] = []
    for topic in TOPIC_ORDER:
        flagged = by_topic.get(topic, [])
        if not flagged:
            continue
        parts.append(f"### {topic}")
        for r in sorted(flagged, key=lambda x: x["profile"]):
            response = _load_response(run_dir, r["qid"])
            message = response.get("message", "")
            answer = (
                response.get("response", {}).get("answer_markdown")
                or response.get("response", {}).get("answer")
                or ""
            )
            head = answer[:300].replace("\n", " ⏎ ")
            parts.append(
                f"- **{r['qid']}** — {CLASS_GLYPH[r['class']]} "
                f"(mode=`{r.get('answer_mode')}`, cites={r.get('citations_count')}, "
                f"len={r.get('answer_len')}, "
                f"effective_topic=`{r.get('effective_topic')}`, "
                f"fallback_reason=`{r.get('fallback_reason')}`)"
            )
            parts.append(f"  - **Q:** {message}")
            parts.append(f"  - **A (head):** {head if head else '_empty answer_'}")
        parts.append("")
    return "\n".join(parts).rstrip()


def _build_retrieval_signal_check(rows: list[dict[str, Any]], run_dir: Path) -> str:
    """fix_v7 §3a/3b/3c + fix_v8 §3b — scan every response trace and
    verify the new runtime invariants held during the run. Failures here
    mean the infrastructure regressed between the code change and the
    eval, so the run is INCONCLUSIVE rather than a PASS/FAIL of model
    quality.

    Invariants:
      • `retriever.hybrid_search.in.filter_topic` is None (post-7a)
      • `retriever.hybrid_search.in.embedding_mode` == 'ok' (post-7b)
      • `synthesis.topic_gate.applied.gate_mode` in {'applied',
        'noop_no_topic_entry', 'disabled_by_env', 'noop_empty_template'}
        (post-7c — any other value means the gate failed to load)
      • `diagnostics.polish_mode == 'rejected'` count (post-8b — the
        fix_v8 §3a substantive fallback should keep the answer useful
        when this fires; visibility here lets the operator track the
        rejection rate per run)

    Reports counts; does NOT mutate the verdict — the operator reads
    this section and decides whether to treat the gauge as inconclusive.
    """

    expected_gate_modes = {
        "applied",
        "noop_no_topic_entry",
        "noop_empty_template",
        "disabled_by_env",
    }

    total_traces = 0
    filter_topic_violations: list[str] = []
    embedding_non_ok: dict[str, int] = defaultdict(int)
    gate_non_expected: dict[str, int] = defaultdict(int)
    missing_trace: list[str] = []
    polish_rejected: list[str] = []
    polish_rejected_reasons: dict[str, int] = defaultdict(int)

    for r in rows:
        qid = r.get("qid", "(unknown)")
        response_record = _load_response(run_dir, qid)
        response = response_record.get("response", {}) or {}
        diagnostics = response.get("diagnostics") or {}
        if isinstance(diagnostics, dict) and diagnostics.get("polish_mode") == "rejected":
            polish_rejected.append(qid)
            reason = str(diagnostics.get("polish_skip_reason") or "unknown")
            polish_rejected_reasons[reason] += 1
        trace = diagnostics.get("pipeline_trace") if isinstance(diagnostics, dict) else None
        steps = (trace or {}).get("steps") or []
        if not steps:
            missing_trace.append(qid)
            continue
        total_traces += 1

        gate_modes_seen: set[str] = set()
        for step in steps:
            name = step.get("step") or step.get("name") or ""
            details = step.get("details") or step
            if name == "retriever.hybrid_search.in":
                if details.get("filter_topic") is not None:
                    filter_topic_violations.append(qid)
                em = details.get("embedding_mode")
                if em and em != "ok":
                    embedding_non_ok[em] += 1
            if name == "synthesis.topic_gate.applied":
                mode = details.get("gate_mode") or ""
                gate_modes_seen.add(mode)
                if mode and mode not in expected_gate_modes:
                    gate_non_expected[mode] += 1
        # A run with NO topic-gate trace step at all is fine (the gate
        # is wired post-template emission and a turn may bail before
        # then), so we do not report missing gate-steps here.

    lines = [
        f"- Traces inspected: **{total_traces}** of {len(rows)}",
    ]
    if missing_trace:
        lines.append(
            f"- ⚠ Missing `pipeline_trace` on {len(missing_trace)} response(s): "
            f"{', '.join(missing_trace[:10])}{' …' if len(missing_trace) > 10 else ''}"
        )
    if filter_topic_violations:
        lines.append(
            f"- 🔴 **fix_v7 §3a regression:** `filter_topic` non-None on "
            f"{len(filter_topic_violations)} qid(s): "
            f"{', '.join(filter_topic_violations[:10])}"
            f"{' …' if len(filter_topic_violations) > 10 else ''} — "
            f"chat path must pass `filter_topic=None` always"
        )
    else:
        lines.append("- ✅ `filter_topic` is None on every served chat (post-7a invariant holds)")
    if embedding_non_ok:
        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(embedding_non_ok.items()))
        lines.append(
            f"- 🔴 **fix_v7 §3b regression:** `embedding_mode != 'ok'` "
            f"distribution: {breakdown} — verify GEMINI_API_KEY + "
            f"LIA_QUERY_EMBEDDINGS_ENABLED on the serving env"
        )
    else:
        lines.append("- ✅ `embedding_mode == 'ok'` on every served chat (post-7b invariant holds)")
    if gate_non_expected:
        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(gate_non_expected.items()))
        lines.append(
            f"- 🔴 **fix_v7 §3c regression:** unexpected `gate_mode` "
            f"distribution: {breakdown} — `config/topic_norm_allowlist.json` "
            f"may have failed to load"
        )
    else:
        lines.append("- ✅ topic-gate `gate_mode` always in the expected set (post-7c invariant holds)")
    if polish_rejected:
        breakdown = ", ".join(
            f"{k}={v}" for k, v in sorted(polish_rejected_reasons.items())
        )
        sample = ", ".join(polish_rejected[:10])
        lines.append(
            f"- 🟠 **Polish rejected on {len(polish_rejected)} qid(s)** "
            f"(`polish_mode=rejected`): {sample}"
            f"{' …' if len(polish_rejected) > 10 else ''} — "
            f"`polish_skip_reason` distribution: {breakdown}. The fix_v8 §3a "
            f"substantive fallback should keep the answer useful when this "
            f"fires; if the visible answers regressed, check the "
            f"`polish.rejected.fallback_composed` trace step."
        )
    else:
        lines.append(
            "- ✅ No polish rejections this run (`polish_mode=rejected` count = 0)"
        )
    return "\n".join(lines)


def _build_cross_checks(rows: list[dict[str, Any]]) -> str:
    by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_topic[r["topic_key_expected"]].append(r)

    impatpn = by_topic.get("impuesto_patrimonio_personas_naturales", [])
    impatpn_refused = sum(1 for r in impatpn if r["class"] == "refused")
    impatpn_msg = (
        f"- `impuesto_patrimonio_personas_naturales`: refused {impatpn_refused}/3 — "
        f"{'✅ consistent refusal (expected)' if impatpn_refused == 3 else '⚠ unexpected mix — investigate'}"
    )

    served_baseline_topics = [
        t for t in TOPIC_ORDER if t != "impuesto_patrimonio_personas_naturales"
    ]
    hidden_refusals: list[str] = []
    for t in served_baseline_topics:
        rs = by_topic.get(t, [])
        if rs and all(r["class"] == "refused" for r in rs):
            hidden_refusals.append(t)
    hidden_msg = (
        f"- 11 baseline-SERVED topics with hidden full-refusals: {len(hidden_refusals)} → "
        f"{'✅ none' if not hidden_refusals else '⚠ ' + ', '.join(hidden_refusals)}"
    )
    return impatpn_msg + "\n" + hidden_msg


def write_report(run_dir: Path) -> Path:
    classified_path = run_dir / "classified.jsonl"
    rows = _read_jsonl(classified_path)
    counts, overall = _build_overall(rows)
    decision, decision_detail = _decision(counts)

    body = f"""# §1.G SME validation report

**Run dir:** `{run_dir}`
**Generated:** {_bogota_now()}
**Questions classified:** {len(rows)} / 36

## Overall

{overall}

## Per topic (12 × 3 grid)

{_build_per_topic(rows)}

## Per profile

{_build_per_profile(rows)}

## Routing accuracy

{_build_routing(rows)}

## Cross-checks (binding regardless of overall)

{_build_cross_checks(rows)}

## Retrieval signal check (fix_v7 §3a/3b/3c invariants)

{_build_retrieval_signal_check(rows, run_dir)}

## Topics flagged for follow-up

{_build_followups(rows, run_dir)}

## Decision

**STATE: {decision}** — {decision_detail}

- PASS = ≥22/36 served_acceptable+
- PARTIAL = 14–21/36 served_acceptable+
- FAIL = ≤13/36 served_acceptable+
"""
    out = run_dir / "report.md"
    out.write_text(body, encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Verbatim doc — operator's extra deliverable
# ---------------------------------------------------------------------------


def _format_citation(idx: int, c: dict[str, Any]) -> str:
    label = c.get("label") or c.get("title") or c.get("anchor") or "(no label)"
    extras: list[str] = []
    for k in ("doc_id", "article_id", "subtopic", "score", "anchor"):
        v = c.get(k)
        if v not in (None, ""):
            extras.append(f"{k}={v!r}")
    suffix = f" — {'; '.join(extras)}" if extras else ""
    return f"  {idx}. {label}{suffix}"


def write_verbatim(run_dir: Path) -> Path:
    classified_path = run_dir / "classified.jsonl"
    rows = _read_jsonl(classified_path)
    by_qid = {r["qid"]: r for r in rows}

    lines: list[str] = [
        "# §1.G SME validation — verbatim responses",
        "",
        f"**Run dir:** `{run_dir}`",
        f"**Generated:** {_bogota_now()}",
        f"**Responses included:** {len(rows)} / 36",
        "",
        "Every response below is reproduced word-for-word as the chat server",
        "returned it. No truncation, no editing.",
        "",
        "---",
        "",
    ]

    for topic in TOPIC_ORDER:
        topic_qids = [
            f"{topic}_P1",
            f"{topic}_P2",
            f"{topic}_P3",
        ]
        if not any(q in by_qid for q in topic_qids):
            continue
        lines.append(f"## {topic}")
        lines.append("")
        for qid in topic_qids:
            row = by_qid.get(qid)
            response_record = _load_response(run_dir, qid)
            if not row and not response_record:
                lines.append(f"### {qid}")
                lines.append("")
                lines.append("_No response captured._")
                lines.append("")
                continue

            response = response_record.get("response", {}) or {}
            message = response_record.get("message", "")
            answer = response.get("answer_markdown") or response.get("answer") or ""
            citations = response.get("citations") or []
            mode = response.get("answer_mode")
            fallback = response.get("fallback_reason") or (
                response.get("diagnostics", {}).get("fallback_reason")
                if isinstance(response.get("diagnostics"), dict) else None
            )
            effective_topic = (
                response.get("effective_topic")
                or (response.get("diagnostics", {}).get("effective_topic")
                    if isinstance(response.get("diagnostics"), dict) else None)
            )
            latency_ms = response_record.get("latency_ms")
            cls = (row or {}).get("class", "(unclassified)")

            lines.append(f"### {qid}")
            lines.append("")
            lines.append(f"- **Class:** {CLASS_GLYPH.get(cls, cls)}")
            lines.append(f"- **answer_mode:** `{mode}`")
            lines.append(f"- **effective_topic:** `{effective_topic}` "
                         f"(expected `{topic}`)")
            lines.append(f"- **fallback_reason:** `{fallback}`")
            lines.append(f"- **citations:** {len(citations)}")
            lines.append(f"- **answer length:** {len(answer)} chars")
            lines.append(f"- **latency:** {latency_ms} ms")
            lines.append("")
            lines.append("**Question:**")
            lines.append("")
            lines.append("> " + message.replace("\n", "\n> "))
            lines.append("")
            lines.append("**Answer (verbatim):**")
            lines.append("")
            if answer:
                lines.append(answer)
            else:
                lines.append("_(no answer_markdown returned)_")
            lines.append("")
            if citations:
                lines.append("**Citations (verbatim):**")
                lines.append("")
                for i, c in enumerate(citations, start=1):
                    if isinstance(c, dict):
                        lines.append(_format_citation(i, c))
                    else:
                        lines.append(f"  {i}. {c!r}")
                lines.append("")
            lines.append("---")
            lines.append("")

    out = run_dir / "verbatim.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_dir", type=Path)
    args = p.parse_args(argv)

    run_dir: Path = args.run_dir
    if not run_dir.exists():
        print(f"FATAL: run dir does not exist: {run_dir}", file=sys.stderr)
        return 2
    classified = run_dir / "classified.jsonl"
    if not classified.exists():
        print(
            f"FATAL: classified.jsonl missing in {run_dir} — run the runner first",
            file=sys.stderr,
        )
        return 2

    report_path = write_report(run_dir)
    verbatim_path = write_verbatim(run_dir)

    rows = _read_jsonl(classified)
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r["class"]] += 1
    decision, _ = _decision(counts)
    served = counts.get("served_strong", 0) + counts.get("served_acceptable", 0)

    print(f"STATE: decision={decision} served_acceptable+={served}/36")
    print(f"  report:   {report_path}")
    print(f"  verbatim: {verbatim_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
