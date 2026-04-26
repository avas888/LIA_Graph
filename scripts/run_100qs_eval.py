#!/usr/bin/env python3
"""100qs accountant eval — runner.

Iterates `evals/100qs_accountant.jsonl` against a running `ui_server`
(`/api/chat`), captures answer + citations + diagnostics per question,
and appends to `evals/runs/100qs_<tag>_<ts>.jsonl`. Resumable: re-running
on an existing output file skips IDs already present.

Usage
-----
    # 1. start a server
    npm run dev          # local artifact mode (LIA_GRAPH_MODE=artifacts)
    npm run dev:staging  # cloud mode (LIA_GRAPH_MODE=falkor_live)

    # 2. run the harness
    PYTHONPATH=src:. uv run python scripts/run_100qs_eval.py \
        --base-url http://localhost:5173 \
        --tag dev_local

    # 3. (optional) limit / resume
    PYTHONPATH=src:. uv run python scripts/run_100qs_eval.py \
        --base-url http://localhost:5173 \
        --tag dev_local \
        --limit 5
        # re-run with same --tag to resume; already-captured IDs are skipped

Output
------
    evals/runs/100qs_<tag>_<ts>.jsonl             — one row per question
    evals/runs/100qs_<tag>_<ts>_manifest.json     — run metadata
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = REPO_ROOT / "evals" / "100qs_accountant.jsonl"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evals" / "runs"

_BOGOTA = _dt.timezone(_dt.timedelta(hours=-5))


def _bogota_now() -> str:
    return _dt.datetime.now(_BOGOTA).strftime("%Y-%m-%d %-I:%M:%S %p").lstrip("0")


def _utc_iso_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


# ── HTTP ────────────────────────────────────────────────────────────────


def _post_json(
    url: str,
    body: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = Request(url, data=data, headers=req_headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"_raw_body": raw}
            return int(resp.status), payload if isinstance(payload, dict) else {"_raw_body": raw}
    except HTTPError as exc:
        try:
            body_text = exc.read().decode("utf-8")
        except Exception:  # noqa: BLE001
            body_text = ""
        try:
            payload = json.loads(body_text) if body_text else {}
        except json.JSONDecodeError:
            payload = {"_raw_body": body_text}
        return int(exc.code), payload if isinstance(payload, dict) else {"_raw_body": body_text}


def _create_public_session(base_url: str) -> str:
    status, payload = _post_json(f"{base_url}/api/public/session", {})
    if status != 200 or not payload.get("ok"):
        raise SystemExit(
            f"[run_100qs_eval] /api/public/session failed: status={status} payload={payload}"
        )
    token = str(payload.get("token") or "").strip()
    if not token:
        raise SystemExit("[run_100qs_eval] session token missing in response")
    return token


# ── Fixture / output IO ─────────────────────────────────────────────────


def _load_fixture(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"[run_100qs_eval] {path} line {lineno} invalid JSON: {exc}")
            if not isinstance(row, dict) or not row.get("id") or not row.get("question"):
                raise SystemExit(f"[run_100qs_eval] {path} line {lineno} missing id/question")
            rows.append(row)
    return rows


def _completed_ids(output_jsonl: Path) -> set[str]:
    if not output_jsonl.exists():
        return set()
    ids: set[str] = set()
    with output_jsonl.open("r", encoding="utf-8") as fh:
        for raw in fh:
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            qid = str(row.get("id") or "").strip()
            if qid and row.get("ok"):
                ids.add(qid)
    return ids


def _atomic_append_json(path: Path, row: dict[str, Any]) -> None:
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass


def _git_sha() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=REPO_ROOT,
        )
        return out.decode("ascii").strip()
    except Exception:  # noqa: BLE001
        return None


# ── Per-question capture ────────────────────────────────────────────────


def _ask_one(
    *,
    base_url: str,
    auth_headers: dict[str, str],
    question_row: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    qid = str(question_row["id"])
    question = str(question_row["question"]).strip()
    body: dict[str, Any] = {
        "message": question,
        "pais": "colombia",
    }
    t0 = time.perf_counter()
    try:
        status, payload = _post_json(
            f"{base_url}/api/chat",
            body,
            headers=auth_headers,
            timeout=timeout,
        )
    except (URLError, OSError) as exc:
        return {
            "id": qid,
            "ok": False,
            "error": f"transport_error={exc!r}",
            "wall_ms": int((time.perf_counter() - t0) * 1000),
        }
    wall_ms = int((time.perf_counter() - t0) * 1000)

    if status != 200:
        err_msg = ""
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict):
                err_msg = str(err.get("code") or err.get("message") or "")
        return {
            "id": qid,
            "ok": False,
            "error": f"http_status={status} {err_msg}".strip(),
            "wall_ms": wall_ms,
            "http_status": status,
        }

    diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
    citations = payload.get("citations") if isinstance(payload.get("citations"), list) else []
    citations_norm = [
        {
            "ref": c.get("ref") or c.get("reference") or c.get("title"),
            "doc_id": c.get("doc_id") or c.get("source_doc_id"),
            "snippet": (str(c.get("snippet") or c.get("excerpt") or "")[:400] or None),
        }
        for c in citations
        if isinstance(c, dict)
    ]

    return {
        "id": qid,
        "ok": True,
        "category": question_row.get("category"),
        "topic": question_row.get("topic"),
        "evaluation_profile": question_row.get("evaluation_profile"),
        "question": question,
        "reference_answer": question_row.get("reference_answer"),
        "reference_sources": question_row.get("reference_sources") or [],
        "answer_markdown": str(payload.get("answer_markdown") or ""),
        "answer_concise": str(payload.get("answer_concise") or ""),
        "citations": citations_norm,
        "diagnostics": {
            "retrieval_backend": diagnostics.get("retrieval_backend"),
            "graph_backend": diagnostics.get("graph_backend"),
            "primary_article_count": diagnostics.get("primary_article_count"),
            "seed_article_keys": list(diagnostics.get("seed_article_keys") or [])[:20],
            "topic_safety": diagnostics.get("topic_safety"),
            "pipeline_variant": payload.get("pipeline_variant"),
            "effective_topic": payload.get("effective_topic"),
            "topic_router_mode": (diagnostics.get("topic_safety") or {}).get("router_mode")
            if isinstance(diagnostics.get("topic_safety"), dict)
            else None,
        },
        "trace_id": payload.get("trace_id"),
        "chat_run_id": payload.get("chat_run_id"),
        "session_id": payload.get("session_id"),
        "wall_ms": wall_ms,
    }


# ── CLI ─────────────────────────────────────────────────────────────────


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_100qs_eval",
        description=(
            "Run the 100-question accountant eval against a live ui_server "
            "/api/chat endpoint. Captures answers + citations + diagnostics."
        ),
    )
    parser.add_argument(
        "--fixture",
        default=str(DEFAULT_FIXTURE),
        help=f"Path to questions JSONL (default: {DEFAULT_FIXTURE.relative_to(REPO_ROOT)}).",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:5173",
        help="ui_server base URL (default http://localhost:5173).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output dir for run jsonl + manifest (default {DEFAULT_OUTPUT_DIR.relative_to(REPO_ROOT)}).",
    )
    parser.add_argument(
        "--tag",
        required=True,
        help="Run tag, e.g. `dev_local`, `staging_falkor`. Embedded in output filenames.",
    )
    parser.add_argument(
        "--resume-file",
        default=None,
        help=(
            "Path to an existing run JSONL to resume into. If set, IDs already "
            "present (with ok=true) are skipped and new rows append to this file."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N questions (smoke convenience).",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=120.0,
        help="HTTP timeout per /api/chat call (default 120s).",
    )
    parser.add_argument(
        "--inter-question-pause-seconds",
        type=float,
        default=0.0,
        help="Optional pause between questions (default 0).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_argparser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    fixture_path = Path(args.fixture)
    if not fixture_path.exists():
        print(f"[run_100qs_eval] fixture not found: {fixture_path}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_tag = "".join(c if c.isalnum() or c in "-_" else "_" for c in args.tag)[:64]

    if args.resume_file:
        output_jsonl = Path(args.resume_file)
        # Manifest sits next to it (replace .jsonl with _manifest.json).
        if output_jsonl.suffix == ".jsonl":
            manifest_path = output_jsonl.with_name(output_jsonl.stem + "_manifest.json")
        else:
            manifest_path = output_jsonl.with_name(output_jsonl.name + "_manifest.json")
    else:
        ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_jsonl = output_dir / f"100qs_{safe_tag}_{ts}.jsonl"
        manifest_path = output_dir / f"100qs_{safe_tag}_{ts}_manifest.json"

    rows = _load_fixture(fixture_path)
    if args.limit is not None:
        rows = rows[: int(args.limit)]
    already_done = _completed_ids(output_jsonl)
    pending = [r for r in rows if str(r["id"]) not in already_done]
    skipped = len(rows) - len(pending)

    base_url = args.base_url.rstrip("/")
    started_utc = _utc_iso_now()
    started_bogota = _bogota_now()

    if not pending:
        print(
            f"[run_100qs_eval] nothing to do — all {len(rows)} IDs already in {output_jsonl}",
            file=sys.stderr,
        )
    else:
        try:
            token = _create_public_session(base_url)
        except SystemExit as exc:
            print(str(exc), file=sys.stderr)
            return 3
        auth_headers = {"Authorization": f"Bearer {token}"}

        print(
            f"[run_100qs_eval] start tag={safe_tag} base_url={base_url} "
            f"pending={len(pending)} skipped={skipped} "
            f"output={output_jsonl}",
            file=sys.stderr,
        )

        for idx, q in enumerate(pending, start=1):
            qid = str(q["id"])
            try:
                row = _ask_one(
                    base_url=base_url,
                    auth_headers=auth_headers,
                    question_row=q,
                    timeout=float(args.timeout_seconds),
                )
            except Exception as exc:  # noqa: BLE001 — never crash the run loop
                row = {"id": qid, "ok": False, "error": f"runner_exception={exc!r}"}
            _atomic_append_json(output_jsonl, row)
            marker = "ok" if row.get("ok") else f"err({row.get('error')})"
            backend = ""
            if row.get("ok"):
                d = row.get("diagnostics") or {}
                backend = f" backend={d.get('retrieval_backend')}/{d.get('graph_backend')}"
            print(
                f"[run_100qs_eval] {idx}/{len(pending)} {qid} {marker}{backend} "
                f"({row.get('wall_ms', 0)}ms)",
                file=sys.stderr,
            )
            if args.inter_question_pause_seconds > 0 and idx < len(pending):
                time.sleep(float(args.inter_question_pause_seconds))

    completed_utc = _utc_iso_now()
    completed_bogota = _bogota_now()

    # Compute lightweight summary from the file (ok/total + backend distribution).
    ok_count = 0
    total = 0
    backends: dict[str, int] = {}
    if output_jsonl.exists():
        with output_jsonl.open("r", encoding="utf-8") as fh:
            for raw in fh:
                stripped = raw.strip()
                if not stripped:
                    continue
                try:
                    r = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                total += 1
                if r.get("ok"):
                    ok_count += 1
                    d = r.get("diagnostics") or {}
                    key = f"{d.get('retrieval_backend')}/{d.get('graph_backend')}"
                    backends[key] = backends.get(key, 0) + 1

    manifest = {
        "tag": safe_tag,
        "fixture_path": str(fixture_path),
        "base_url": base_url,
        "output_jsonl": str(output_jsonl),
        "run_started_at_utc": started_utc,
        "run_completed_at_utc": completed_utc,
        "run_started_at_bogota": started_bogota,
        "run_completed_at_bogota": completed_bogota,
        "git_commit_sha": _git_sha(),
        "fixture_total": len(rows),
        "skipped_already_done": skipped,
        "captured_total": total,
        "captured_ok": ok_count,
        "captured_failed": total - ok_count,
        "backend_distribution": backends,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ok": True,
                "output_jsonl": str(output_jsonl),
                "manifest": str(manifest_path),
                "captured_ok": ok_count,
                "captured_total": total,
                "started_bogota": started_bogota,
                "completed_bogota": completed_bogota,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
