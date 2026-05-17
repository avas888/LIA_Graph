"""v23 P4-T1 — cloud Supabase pollution scan (read-only, diagnose-only).

Scans `public.document_chunks` for named-entity / acta-template / formulario
leak patterns + the audit's verbatim pollution strings. Emits a markdown
report at `tracers_and_logs/corpus_audit/<UTC>_pollution_report.md` listing
each finding (chunk_id, document_id, topic_tag, snippet, recommended action).

**Read-only.** v23 does NOT retire any chunk; that is v24's scope per D-S3.
Operator pre-authorizes Lia Graph cloud READS per
`feedback_lia_graph_cloud_writes_authorized`.

Long-running canon (per CLAUDE.md "Long-running Python processes"):
  - Launch detached via `scripts/launch_phase9a*.sh` shape, or directly
    `nohup uv run python scripts/corpus_audit/pollution_scan.py >log 2>&1 &`
  - Heartbeat emitted to `tracers_and_logs/corpus_audit/heartbeat.jsonl`
    every 30 seconds.
  - `cli.done` marker in audit log → terminal.

Usage:
  PYTHONPATH=src:. uv run python scripts/corpus_audit/pollution_scan.py \\
      --batch-size 1000 --limit 50000

The runtime safety net (LIA_CHUNK_QUALITY_ENTITY_FILTER, default `shadow`)
demotes matching chunks at request time so production behavior is
unchanged until operator promotes the flag.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


# v23 entity-leak patterns (must mirror chunk_quality_heuristics.py).
_AUDIT_VERBATIM_LEAK_RE = re.compile(
    r"\b(?:DISTRIBUIDORA\s+EL\s+SOL|ALEJANDRO\s+VASQUEZ)\b",
    re.IGNORECASE,
)
_CORPORATE_SUFFIX_RE = re.compile(
    r"\b(?:SAS|S\.A\.S\.|LTDA|L\.T\.D\.A\.|S\.A\.)\b",
)
_NAMED_ENTITY_LEAK_RE = re.compile(
    r"\b[A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,}){2,}\b"
)
_ACTA_TEMPLATE_LEAK_RE = re.compile(
    r"\bACTA\s+No\.?\s*\d+\b|\bEn\s+Bogot[aá],?\s+a\s+los?\s+\d",
    re.IGNORECASE,
)
_FORMULARIO_LEAK_RE = re.compile(
    r"\bFormulario\s+\d{2,4}\s*[-—]",
    re.IGNORECASE,
)


def _classify(text: str) -> tuple[str, str] | None:
    """Return (severity, reason) or None for clean chunks."""
    if _AUDIT_VERBATIM_LEAK_RE.search(text):
        return ("retire", "audit_verbatim_pollution_string")
    has_corporate = bool(_CORPORATE_SUFFIX_RE.search(text))
    has_proper = bool(_NAMED_ENTITY_LEAK_RE.search(text))
    has_acta = bool(_ACTA_TEMPLATE_LEAK_RE.search(text))
    has_form = bool(_FORMULARIO_LEAK_RE.search(text))
    if has_acta and (has_corporate or has_proper):
        return ("retire", "acta_template_with_entity")
    if has_form and (has_corporate or has_proper):
        return ("retire", "formulario_template_with_entity")
    if has_corporate and has_proper and len(text) < 800:
        return ("re-chunk", "entity_dominant_short_chunk")
    return None


def _heartbeat_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent.parent
        / "tracers_and_logs"
        / "corpus_audit"
        / "heartbeat.jsonl"
    )


def _emit_heartbeat(payload: dict[str, Any]) -> None:
    path = _heartbeat_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**payload, "ts_utc": datetime.now(timezone.utc).isoformat()}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


def _supabase_client():
    """Lazy-create the Supabase client using project envvars."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) "
            "required for cloud pollution scan."
        )
    try:
        from supabase import create_client  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "supabase-py not installed; run `uv pip install supabase`."
        ) from e
    return create_client(url, key)


def _iter_chunks(client, *, batch_size: int, limit: int | None) -> Iterable[dict[str, Any]]:
    offset = 0
    seen = 0
    while True:
        if limit is not None and seen >= limit:
            return
        end = offset + batch_size - 1
        resp = (
            client.table("document_chunks")
            .select("id, document_id, content, topic_tag")
            .range(offset, end)
            .execute()
        )
        rows = list(resp.data or [])
        if not rows:
            return
        for row in rows:
            if limit is not None and seen >= limit:
                return
            yield row
            seen += 1
        offset += batch_size


def _report_path() -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (
        Path(__file__).resolve().parent.parent.parent
        / "tracers_and_logs"
        / "corpus_audit"
        / f"{ts}_pollution_report.md"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="v23 P4 cloud pollution scan")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Skip Supabase; emit empty report")
    args = parser.parse_args(argv)

    started = time.time()
    _emit_heartbeat({"event": "scan.start", "batch_size": args.batch_size, "limit": args.limit})

    findings: list[dict[str, Any]] = []
    if args.dry_run:
        _emit_heartbeat({"event": "scan.dry_run"})
    else:
        try:
            client = _supabase_client()
        except RuntimeError as e:
            _emit_heartbeat({"event": "scan.failed", "error": str(e)})
            print(f"FAIL: {e}", file=sys.stderr)
            return 2
        last_hb = time.time()
        seen = 0
        for row in _iter_chunks(client, batch_size=args.batch_size, limit=args.limit):
            seen += 1
            text = str(row.get("content") or "")
            classified = _classify(text)
            if classified is not None:
                severity, reason = classified
                findings.append({
                    "chunk_id": str(row.get("id") or ""),
                    "document_id": str(row.get("document_id") or ""),
                    "topic_tag": str(row.get("topic_tag") or ""),
                    "snippet": text[:200].replace("\n", " "),
                    "reason": reason,
                    "severity": severity,
                })
            if time.time() - last_hb >= 30:
                _emit_heartbeat({
                    "event": "scan.progress",
                    "seen": seen,
                    "findings": len(findings),
                    "elapsed_s": round(time.time() - started, 1),
                })
                last_hb = time.time()

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# v23 P4 — cloud corpus pollution scan",
        f"- Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"- Findings: {len(findings)}",
        f"- Mode: {'dry-run' if args.dry_run else 'live cloud read-only'}",
        "",
        "| Chunk id | Document id | Topic tag | Reason | Severity | Snippet |",
        "|---|---|---|---|---|---|",
    ]
    for f in findings:
        snippet = (f["snippet"] or "").replace("|", "\\|")
        lines.append(
            f"| `{f['chunk_id']}` | `{f['document_id']}` | "
            f"`{f['topic_tag']}` | `{f['reason']}` | `{f['severity']}` | {snippet} |"
        )
    report.write_text("\n".join(lines), encoding="utf-8")

    _emit_heartbeat({
        "event": "cli.done",
        "report": str(report),
        "findings": len(findings),
        "elapsed_s": round(time.time() - started, 1),
    })
    print(f"OK report={report} findings={len(findings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
