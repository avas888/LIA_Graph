"""fix_v10_may Phase 10B closing — score the 21-Q expert-panel mini-panel.

For each chat response already captured by `run_sme_parallel.py` in the
`run_dir`, POST `/api/expert-panel` with the chat's `trace_id` +
`citations`, capture the panel surface, and score the §5.4 rubric:

    ≥ 70% of questions must surface at least one expected
    interpretation file in the top-3 panel cards.

The expected files per question live in
`evals/sme_validation_v1/questions_expert_panel_v1.jsonl` under the
`expected_interpretation_files` key.

Writes one `<qid>.panel.json` per question into the run_dir plus a
markdown `panel_report.md` summary (PASS / REFINE / DISCARD).

Usage:
    PYTHONPATH=src:. uv run python scripts/eval/score_expert_panel_mini.py \\
        --run-dir evals/sme_validation_v1/runs/<TS>_phase10b_expert_panel_v1 \\
        [--server http://127.0.0.1:8787]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


sys.path.insert(0, "scripts/eval")
from engine import ChatClient, post_json  # type: ignore  # noqa: E402


_RUBRIC_KEY = "expert_panel_rubric"
_EXPECTED_KEY = "expected_interpretation_files"


def _load_questions(path: Path) -> dict[str, dict]:
    by_qid: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        qid = str(record.get("qid") or "")
        if qid:
            by_qid[qid] = record
    return by_qid


def _extract_normative_refs(chat_response: dict) -> list[str]:
    """Pull article-key refs from the chat's `citations` field."""
    refs: list[str] = []
    seen: set[str] = set()
    for cite in chat_response.get("citations") or []:
        if not isinstance(cite, dict):
            continue
        for key_name in ("article_key", "key", "id"):
            v = str(cite.get(key_name) or "").strip()
            if v and v not in seen:
                seen.add(v)
                refs.append(v)
                break
    return refs


def _extract_panel_card_paths(panel_response: dict) -> list[str]:
    """The expert panel returns docs under `ungrouped` (top-level
    flat) and `groups[*].items` (clustered). Each card carries a
    sanitized `doc_id` (path with `/` and spaces replaced by `_`).
    We collect doc_ids preserving rank order.
    """
    candidates: list[str] = []
    seen: set[str] = set()

    def _maybe_add(value: object) -> None:
        if not isinstance(value, str):
            return
        v = value.strip()
        if v and v not in seen:
            seen.add(v)
            candidates.append(v)

    # Flat fallback bucket — carries every card the panel surfaced,
    # in rerank order. We collect doc_id per card (source/logical are
    # typically identical to doc_id).
    for item in panel_response.get("ungrouped") or []:
        if isinstance(item, dict):
            _maybe_add(item.get("doc_id"))
    # Grouped buckets — when assembled cards form provider clusters
    for group in panel_response.get("groups") or []:
        if not isinstance(group, dict):
            continue
        for item in group.get("items") or []:
            if isinstance(item, dict):
                _maybe_add(item.get("doc_id"))
    return candidates


_NORM_PATH_RE = __import__("re").compile(r"[\s/_\-.]+")


def _norm_path_key(path: str) -> str:
    """Reduce a file path or sanitized doc_id to a single canonical
    string so different separators ({/}, {_}, space, dash) don't
    block matching. Strips the trailing `.md` and casefolds."""
    s = str(path or "").strip().lower()
    if s.endswith(".md"):
        s = s[:-3]
    s = _NORM_PATH_RE.sub("_", s).strip("_")
    return s


def _path_match(expected_files: list[str], panel_paths: list[str]) -> str | None:
    """Return the first expected file whose canonical form is a
    substring (either direction) of any panel doc_id's canonical form.

    Doc_ids returned by the panel are sanitized versions of the
    relative_path (`CORE/ya/Arriba/...` → `CORE_ya_Arriba_...`).
    Normalize both sides before comparing.
    """
    norm_panel = [(p, _norm_path_key(p)) for p in panel_paths]
    for expected in expected_files:
        e_key = _norm_path_key(expected)
        if not e_key:
            continue
        for _orig_panel, p_key in norm_panel:
            if not p_key:
                continue
            if e_key == p_key or e_key in p_key or p_key in e_key:
                return expected
    return None


def _score_question(
    *,
    qid: str,
    question: dict,
    chat_response: dict,
    panel_response: dict,
    top_k_for_rubric: int = 3,
) -> dict:
    """Compute the §5.4 rubric for one question."""
    expected = list(question.get(_EXPECTED_KEY) or [])
    rubric = str(question.get(_RUBRIC_KEY) or "at_least_one_top3")
    panel_paths_all = _extract_panel_card_paths(panel_response)
    panel_paths_top = panel_paths_all[:top_k_for_rubric]
    match = _path_match(expected, panel_paths_top)
    return {
        "qid": qid,
        "topic_key": question.get("topic_key"),
        "rubric": rubric,
        "expected_count": len(expected),
        "panel_cards_top3": panel_paths_top,
        "panel_cards_all": panel_paths_all[:10],
        "matched_file": match,
        "outcome": "accept" if match else "wrong",
        "interpretation_backend": (
            (panel_response.get("diagnostics") or {}).get(
                "interpretation_backend"
            )
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", required=True)
    p.add_argument("--server", default="http://127.0.0.1:8787")
    p.add_argument(
        "--questions",
        default="evals/sme_validation_v1/questions_expert_panel_v1.jsonl",
    )
    p.add_argument("--timeout-seconds", type=int, default=90)
    args = p.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"run-dir does not exist: {run_dir}", file=sys.stderr)
        return 2

    questions = _load_questions(Path(args.questions))
    if not questions:
        print("no questions loaded", file=sys.stderr)
        return 2

    # Shared session, single mint (same hardening as run_sme_parallel)
    client = ChatClient(base_url=args.server, auth=True, timeout=args.timeout_seconds)
    client.ensure_session()
    headers = dict(client._auth_headers or {})

    bogota = ZoneInfo("America/Bogota")
    stamp = datetime.now(bogota).strftime("%Y-%m-%d %I:%M:%S %p")
    print(f"=== Expert-Panel mini-panel scorer — {stamp} Bogotá ===\n")

    results: list[dict] = []
    for qid, question in sorted(questions.items()):
        chat_file = run_dir / f"{qid}.json"
        if not chat_file.is_file():
            print(f"  ⚠ {qid}: chat response missing — skipping")
            continue
        chat_record = json.loads(chat_file.read_text(encoding="utf-8"))
        chat_response = chat_record.get("response") or {}
        trace_id = str(chat_response.get("trace_id") or "").strip()
        if not trace_id:
            print(f"  ⚠ {qid}: chat response has no trace_id — skipping")
            continue
        message = str(chat_record.get("message") or "").strip()
        topic_key = question.get("topic_key")
        normative_refs = _extract_normative_refs(chat_response)
        panel_payload = {
            "trace_id": trace_id,
            "message": message,
            "assistant_answer": chat_response.get("answer_markdown") or "",
            "normative_article_refs": normative_refs,
            "topic": topic_key,
            "pais": "colombia",
            "top_k": 8,
        }
        status, panel_response = post_json(
            f"{args.server}/api/expert-panel",
            panel_payload,
            headers=headers,
            timeout=args.timeout_seconds,
        )
        # Persist the raw panel response for debugging
        panel_file = run_dir / f"{qid}.panel.json"
        panel_file.write_text(
            json.dumps(
                {
                    "qid": qid,
                    "http_status": status,
                    "request_payload": panel_payload,
                    "response": panel_response,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        if status != 200:
            print(
                f"  ✗ {qid}: panel HTTP {status} "
                f"({(panel_response or {}).get('error')!r})"
            )
            results.append(
                {
                    "qid": qid,
                    "topic_key": topic_key,
                    "outcome": "server_error",
                    "http_status": status,
                    "error": (panel_response or {}).get("error"),
                }
            )
            continue
        score = _score_question(
            qid=qid,
            question=question,
            chat_response=chat_response,
            panel_response=panel_response,
        )
        results.append(score)
        symbol = "✓" if score["outcome"] == "accept" else "✗"
        print(
            f"  {symbol} {qid}  topic={topic_key}  "
            f"matched={score['matched_file'] or '—'}"
        )

    # Aggregate
    total = len(results)
    accepts = sum(1 for r in results if r.get("outcome") == "accept")
    wrongs = sum(1 for r in results if r.get("outcome") == "wrong")
    errors = sum(1 for r in results if r.get("outcome") == "server_error")
    pct = (accepts / total * 100.0) if total else 0.0
    if pct >= 70:
        decision = "PASS"
    elif pct >= 50:
        decision = "REFINE"
    else:
        decision = "DISCARD"

    print()
    print(f"=== Aggregate ===")
    print(f"  total scored:    {total}")
    print(f"  accept:          {accepts}")
    print(f"  wrong:           {wrongs}")
    print(f"  server_error:    {errors}")
    print(f"  accept rate:     {pct:.1f}%")
    print(f"  decision (§5.4): {decision}")

    # Write report
    report_path = run_dir / "panel_report.md"
    lines = [
        "# Expert-Panel mini-panel report",
        "",
        f"**Run timestamp:** {stamp} Bogotá",
        f"**Server:** `{args.server}`",
        f"**Run dir:** `{run_dir}`",
        f"**Questions file:** `{args.questions}`",
        "",
        "## Aggregate",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total scored | {total} |",
        f"| Accept (top-3 had expected file) | {accepts} |",
        f"| Wrong | {wrongs} |",
        f"| Server error | {errors} |",
        f"| Accept rate | **{pct:.1f}%** |",
        f"| Decision (§5.4: ≥70% pass, 50–69% refine, <50% discard) | **{decision}** |",
        "",
        "## Per question",
        "",
        f"| qid | topic | outcome | matched expected file |",
        f"|---|---|---|---|",
    ]
    for r in results:
        match = r.get("matched_file") or "—"
        lines.append(
            f"| `{r.get('qid')}` | {r.get('topic_key')} | "
            f"{r.get('outcome')} | `{match}` |"
        )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n  report: {report_path}")
    return 0 if decision != "DISCARD" else 4


if __name__ == "__main__":
    raise SystemExit(main())
