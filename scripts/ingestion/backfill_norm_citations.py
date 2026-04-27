"""fixplan_v3 sub-fix 1B-δ — citations link backfill.

Walks every row in `document_chunks` (cloud staging Supabase) and
`documents.vigencia_basis` (the legacy free-text field), runs the
canonicalizer (`src/lia_graph/canon.py`) over the chunk_text and basis
prose, and populates `norm_citations` with the resolved
`(chunk_id, norm_id, role, anchor_strength)` tuples.

Refusals from the canonicalizer log to a SME-triage queue at
`evals/canonicalizer_refusals_v1/refusals.jsonl`.

Usage:
  PYTHONPATH=src:. uv run python scripts/ingestion/backfill_norm_citations.py \\
      --target staging \\
      --run-id backfill-1Bdelta-2026-05-15 \\
      [--limit 1000] \\
      [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

LOGGER = logging.getLogger("backfill_norm_citations")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--target", default=os.getenv("LIA_SUPABASE_TARGET", "staging"))
    p.add_argument("--run-id", required=True, help="Idempotency tag for this backfill.")
    p.add_argument("--limit", type=int, default=None, help="Process at most N chunks.")
    p.add_argument(
        "--refusal-log",
        default="evals/canonicalizer_refusals_v1/refusals.jsonl",
    )
    p.add_argument(
        "--audit-log",
        default="evals/canonicalizer_refusals_v1/backfill_audit.jsonl",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    from lia_graph.citations import extract_citations
    from lia_graph.persistence.norm_history_writer import build_norm_row

    if args.dry_run:
        from scripts.ingest_vigencia_veredictos import _DryRunClient  # noqa: WPS433
        client = _DryRunClient()
    else:
        from lia_graph.supabase_client import create_supabase_client_for_target
        client = create_supabase_client_for_target(args.target)

    refusal_path = Path(args.refusal_log)
    refusal_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path = Path(args.audit_log)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    chunks = _fetch_chunks(client, limit=args.limit)
    LOGGER.info("Loaded %d chunks for backfill (run_id=%s)", len(chunks), args.run_id)

    # Build doc-anchor map: each chunk_id → the canonical norm_id encoded in
    # its document's relative_path. Used to disambiguate "Ley N" mentions
    # whose year is implicit from the filename. Per fixplan_v3 §0.5.4 the
    # canonicalizer is context-free; this map lets the BACKFILL apply
    # document context without leaking it into canon.py.
    doc_anchor_by_chunk = _build_doc_anchor_map(client, [c.get("chunk_id") or "" for c in chunks])
    LOGGER.info("Doc-anchor map: %d chunks have a host norm_id", sum(1 for v in doc_anchor_by_chunk.values() if v))

    norm_rows: dict[str, dict[str, Any]] = {}
    citation_rows: list[dict[str, Any]] = []
    citation_keys: set[tuple[str, str, str]] = set()
    refused = 0
    chunks_with_citations = 0
    refused_chunks: set[str] = set()

    def _on_refusal(chunk_id: str, refusal) -> None:
        nonlocal refused
        refused += 1
        refused_chunks.add(chunk_id)
        with refusal_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": _now(),
                "run_id": args.run_id,
                "chunk_id": chunk_id,
                "mention": refusal.mention,
                "reason": refusal.reason,
                "context": refusal.context,
            }, ensure_ascii=False) + "\n")

    for chunk in chunks:
        chunk_id = chunk.get("chunk_id") or chunk.get("id")
        chunk_text = chunk.get("chunk_text") or chunk.get("text") or ""
        if not (chunk_id and chunk_text):
            continue
        host_norm_id = doc_anchor_by_chunk.get(chunk_id)

        def _ctx_canonicalize(mention: str, *, context: str | None = None):
            from lia_graph.canon import canonicalize_or_refuse as _can_or_ref
            norm_id, refusal = _can_or_ref(mention, context=context)
            if norm_id is not None:
                return norm_id, None
            # Recovery: if the mention reads like "Ley N" / "Decreto N" and the
            # host document is ley.N.YYYY / decreto.N.YYYY, accept the host's
            # canonical id as the resolution. Per fixplan_v3 §0.9 NEW v3
            # convention: never silently guess — but using the host doc's
            # anchor is structured context, not a guess.
            if host_norm_id and refusal and refusal.reason == "missing_year":
                resolved = _try_doc_anchor_recovery(mention, host_norm_id)
                if resolved is not None:
                    return resolved, None
            return None, refusal

        cites = extract_citations(
            chunk_id,
            chunk_text,
            canonicalize_fn=_ctx_canonicalize,
            on_refusal=_on_refusal,
        )
        if cites:
            chunks_with_citations += 1
        for cite in cites:
            norm_rows.setdefault(cite.norm_id, build_norm_row(cite.norm_id))
            # Dedupe by (chunk_id, norm_id, role) — the same norm cited twice
            # in the same chunk is one citation row, not two. Required by the
            # UNIQUE INDEX on those three columns + by the postgrest UPSERT
            # constraint that a single batch cannot UPDATE the same row twice.
            key = (cite.chunk_id, cite.norm_id, cite.role)
            if key in citation_keys:
                continue
            citation_keys.add(key)
            citation_rows.append({
                "chunk_id": cite.chunk_id,
                "norm_id": cite.norm_id,
                "role": cite.role,
                "anchor_strength": cite.anchor_strength,
                "extracted_via": args.run_id,
            })

    LOGGER.info(
        "Resolved %d unique norms; %d citations; %d refusals across %d chunks",
        len(norm_rows),
        len(citation_rows),
        refused,
        len(chunks),
    )

    # Walk parents for catalog completeness
    from lia_graph.canon import parent_norm_id as canon_parent
    full_norm_rows: dict[str, dict[str, Any]] = {}
    for nid in list(norm_rows.keys()):
        cursor: str | None = nid
        while cursor and cursor not in full_norm_rows:
            full_norm_rows[cursor] = build_norm_row(cursor)
            cursor = canon_parent(cursor)

    if not args.dry_run:
        if full_norm_rows:
            client.table("norms").upsert(list(full_norm_rows.values()), on_conflict="norm_id").execute()
        if citation_rows:
            # batch in 500-row chunks
            BATCH = 500
            for i in range(0, len(citation_rows), BATCH):
                client.table("norm_citations").upsert(
                    citation_rows[i:i + BATCH],
                    on_conflict="chunk_id,norm_id,role",
                ).execute()
    else:
        LOGGER.info("[dry-run] would upsert %d norms + %d citations", len(full_norm_rows), len(citation_rows))

    audit = {
        "ts": _now(),
        "run_id": args.run_id,
        "chunks_seen": len(chunks),
        "chunks_with_citations": chunks_with_citations,
        "norms_upserted": len(full_norm_rows),
        "citation_rows": len(citation_rows),
        "refusals": refused,
        "chunks_with_only_refusals": len(refused_chunks - {c["chunk_id"] for c in citation_rows if c.get("chunk_id")}),
    }
    audit_path.write_text(audit_path.read_text(encoding="utf-8") + json.dumps(audit, ensure_ascii=False) + "\n"
                          if audit_path.exists() else json.dumps(audit, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    LOGGER.info("Audit: %s", json.dumps(audit, ensure_ascii=False))
    return 0


def _fetch_chunks(client: Any, *, limit: int | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    offset = 0
    page_size = 1000
    while True:
        page_end = offset + page_size - 1
        if limit is not None:
            remaining = limit - len(out)
            if remaining <= 0:
                break
            page_end = offset + min(page_size, remaining) - 1
        try:
            resp = (
                client.table("document_chunks")
                .select("chunk_id, chunk_text")
                .range(offset, page_end)
                .execute()
            )
        except Exception as err:  # pragma: no cover
            LOGGER.warning("Fetch chunks failed at offset=%d: %s", offset, err)
            break
        rows = getattr(resp, "data", None) or []
        out.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Doc-anchor recovery (host-document context for ambiguous mentions)
# ---------------------------------------------------------------------------


_LEY_FILENAME_RE = __import__("re").compile(r"Ley-(\d+)-(\d{4})", __import__("re").IGNORECASE)
_DECRETO_FILENAME_RE = __import__("re").compile(r"Decreto-(\d+)-(\d{4})", __import__("re").IGNORECASE)


def _path_to_anchor(relative_path: str) -> str | None:
    """Extract a canonical norm_id from a corpus filename when the path
    encodes one (e.g. `LEYES_..._Ley-1429-2010.md` → `ley.1429.2010`)."""

    if not relative_path:
        return None
    m = _LEY_FILENAME_RE.search(relative_path)
    if m:
        return f"ley.{m.group(1)}.{m.group(2)}"
    m = _DECRETO_FILENAME_RE.search(relative_path)
    if m:
        return f"decreto.{m.group(1)}.{m.group(2)}"
    return None


def _try_doc_anchor_recovery(mention: str, host_norm_id: str) -> str | None:
    """Recover a canonical norm_id when the mention reads like a year-less
    Ley/Decreto and the host document anchors that exact same norm.

    Examples:
      mention="Ley 1429" + host="ley.1429.2010" → "ley.1429.2010"
      mention="Decreto 624" + host="decreto.624.1989" → "decreto.624.1989"
      mention="Ley 222" + host="ley.1429.2010" → None (mismatch)
    """

    import re as _re
    text = (mention or "").strip().lower()
    if not text or not host_norm_id:
        return None

    m = _re.search(r"\bley\s+(\d+)\b", text)
    if m and host_norm_id.startswith("ley."):
        ley_num = m.group(1)
        host_parts = host_norm_id.split(".")
        if len(host_parts) >= 3 and host_parts[1] == ley_num:
            return host_norm_id

    m = _re.search(r"\bdecreto\s+(\d+)\b", text)
    if m and host_norm_id.startswith("decreto."):
        dec_num = m.group(1)
        host_parts = host_norm_id.split(".")
        if len(host_parts) >= 3 and host_parts[1] == dec_num:
            return host_norm_id

    return None


def _build_doc_anchor_map(client: Any, chunk_ids: list[str]) -> dict[str, str]:
    """Map chunk_id → canonical norm_id encoded in the host document's path.

    Looks up `documents.relative_path` via Supabase, applies `_path_to_anchor`.
    Empty string for chunks whose document isn't ley/decreto-shaped.
    """

    if not chunk_ids:
        return {}
    # Pull all documents (cheap — ≤ ~1300 rows) and build a lookup by doc_id.
    out: dict[str, str] = {}
    try:
        # Try to fetch document mapping per chunk; chunk_id encoded as
        # "<doc_id>::<article_key>" in our schema, so the doc_id prefix
        # carries the relative_path.
        resp = client.table("documents").select("doc_id, relative_path").execute()
        rows = getattr(resp, "data", None) or []
    except Exception as err:  # pragma: no cover
        LOGGER.warning("doc_anchor map fetch failed: %s", err)
        return {}
    by_doc: dict[str, str] = {}
    for r in rows:
        doc_id = str(r.get("doc_id") or "")
        rel = str(r.get("relative_path") or "")
        anchor = _path_to_anchor(rel) or _path_to_anchor(doc_id)
        if doc_id and anchor:
            by_doc[doc_id] = anchor
    for chunk_id in chunk_ids:
        if not chunk_id:
            continue
        # chunk_id format: "<doc_id>::<article_key>"
        doc_id = chunk_id.split("::", 1)[0]
        if doc_id in by_doc:
            out[chunk_id] = by_doc[doc_id]
    return out


if __name__ == "__main__":
    sys.exit(main())
