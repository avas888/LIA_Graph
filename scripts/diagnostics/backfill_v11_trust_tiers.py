"""fix_v11_may Phase 11A — cloud Supabase trust_tier + provider_labels backfill.

Two writes per interpretation doc, one pass:

1. Parse the doc's local markdown body for the
   `> **Fuentes secundarias consultadas:** …` line (and a couple of
   variants), split into a list of firm strings, write into
   `documents.provider_labels` (the array column added by
   migration 20260513).

2. Resolve the doc's `trust_tier` from the highest-tier firm
   matched against `config/provider_trust_tiers.json`, then update
   every chunk in `document_chunks` for that doc.

Why this happens here, not in the sink
--------------------------------------
A first dry-run revealed that the cloud `documents.authority`
column carries only two enum values
(`secondary_official_authority` / `expert_interpretive_authority`)
and `documents.provider_labels` is empty everywhere — the
v10C-deferred "provider_labels producer side" never landed. The
branded-firm signal lives in the markdown body, not in metadata.
This backfill IS the missing extraction step. Per memory
`feedback_extract_once_three_stage_promotion`, it fires once and
the result becomes canonical until the next corpus refresh.

The allowlist is a curated artifact that may change without
re-ingesting the corpus. Decoupling provider extraction from the
sink keeps the corpus build cheap. The chat retriever reads
`trust_tier` directly off the chunk row (it lives in
`hybrid_search`'s SELECT columns), so updating the chunk column is
sufficient to flip the live ranking.

Idempotency
-----------
Re-runs are safe — every chunk gets the tier that the current
allowlist resolves to. If the allowlist is unchanged, the WRITE is
a no-op (Postgres still issues the UPDATE, but the value doesn't
move). The script counts rows-with-different-target before each
batch so the operator sees only the actual delta.

Safety
------
- `--dry-run` reports the projected delta without writing.
- Per-batch heartbeat with Bogotá AM/PM timestamps so the operator
  sees progress live.
- Default fail-fast: aborts after 50 errors OR >10% error rate
  per CLAUDE.md "Fail Fast, Fix Fast" canon.

Usage (from repo root):
    set -a; source .env.staging; set +a
    PYTHONPATH=src:. uv run python \\
        scripts/diagnostics/backfill_v11_trust_tiers.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, "src")

from lia_graph.supabase_client import create_supabase_client_for_target


_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALLOWLIST_PATH = _REPO_ROOT / "config" / "provider_trust_tiers.json"
_KNOWLEDGE_BASE = _REPO_ROOT / "knowledge_base"

_VALID_TIERS = ("high", "medium", "low")


# Match `Fuentes secundarias consultadas:`, `Fuentes consultadas:`,
# `Fuente consultada:`, with optional bold markdown (`**...**`) and
# optional blockquote prefix (`> `). Captures everything up to the
# next newline as the firm-list payload.
_FUENTES_LINE_RE = re.compile(
    r"^>?\s*\**\s*Fuente[s]?\s+(?:secundarias?\s+)?consultadas?\s*\**\s*:?\s*\**[:\s]*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)

# Strip parenthetical asides (e.g., "(Diego Guevara, consultorio…)") and
# trailing markdown emphasis. Leaves a clean firm name for matching.
_PARENS_RE = re.compile(r"\([^)]*\)")
_TRAILING_PUNCT_RE = re.compile(r"[\.\;\,]+$")


def _load_allowlist(path: Path) -> tuple[dict[str, list[str]], str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    tiers_block = raw.get("tiers") or {}
    out: dict[str, list[str]] = {tier: [] for tier in _VALID_TIERS}
    for tier in _VALID_TIERS:
        entries = tiers_block.get(tier) or []
        for entry in entries:
            s = str(entry or "").strip()
            if s:
                out[tier].append(s)
    default = str(raw.get("default") or "medium").strip().lower()
    if default not in _VALID_TIERS:
        default = "medium"
    return out, default


def _resolve_tier(
    *,
    authority: str | None,
    provider_labels: list[str] | None,
    allowlist: dict[str, list[str]],
    default: str,
) -> str:
    """Case-insensitive substring match. high → medium → low order."""
    haystack: list[str] = []
    auth = str(authority or "").strip().lower()
    if auth:
        haystack.append(auth)
    for label in provider_labels or []:
        s = str(label or "").strip().lower()
        if s:
            haystack.append(s)
    if not haystack:
        return default
    for tier in _VALID_TIERS:
        for needle in allowlist.get(tier) or []:
            n = needle.strip().lower()
            if not n:
                continue
            for hay in haystack:
                if n in hay:
                    return tier
    return default


def _extract_providers_from_markdown(md_text: str) -> list[str]:
    """Parse the `> **Fuentes secundarias consultadas:** …` line into
    a deduped list of firm names.

    Behavior:
    - First matching line wins (some docs have a per-section variant
      after the canonical one; the lead-in line is the doc-level
      attribution).
    - Splits on commas, strips parenthetical asides, drops empties.
    - Returns ordered, deduped (case-insensitive) names so the order
      reflects the original citation order. The first name typically
      gets the highest weight in downstream UI surfaces.
    """
    if not md_text:
        return []
    m = _FUENTES_LINE_RE.search(md_text)
    if not m:
        return []
    payload = m.group(1).strip()
    payload = _PARENS_RE.sub("", payload)
    payload = _TRAILING_PUNCT_RE.sub("", payload)
    raw_parts = [p.strip(" *") for p in payload.split(",")]
    seen: set[str] = set()
    out: list[str] = []
    for part in raw_parts:
        s = part.strip()
        if not s or s.startswith("**"):
            continue
        # Drop emphasis around the name itself
        s = s.strip("* ").strip()
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def _read_local_markdown(relative_path: str) -> str | None:
    """Resolve `documents.relative_path` to a local file under
    `knowledge_base/`. Returns None when the file isn't present (the
    script tolerates a partial local checkout — those docs just keep
    their existing tier)."""
    rel = (relative_path or "").strip()
    if not rel:
        return None
    p = _KNOWLEDGE_BASE / rel
    try:
        return p.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return None
    except UnicodeDecodeError:
        try:
            return p.read_text(encoding="latin-1")
        except Exception:
            return None


def _fetch_interp_documents(client) -> list[dict[str, object]]:
    """All interpretative_guidance docs with the columns we need.
    Paginated to dodge PostgREST's default 1k row cap."""
    rows: list[dict[str, object]] = []
    page = 0
    page_size = 500
    while True:
        resp = (
            client.table("documents")
            .select("doc_id,authority,provider_labels,relative_path")
            .eq("knowledge_class", "interpretative_guidance")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        )
        batch = list(resp.data or [])
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
    return rows


def _write_provider_labels(
    client, doc_id: str, providers: list[str], *, dry_run: bool
) -> bool:
    """Write the deduped provider list to documents.provider_labels.
    Returns True iff a real write happened (idempotent guard: if the
    current value already matches, we skip the round-trip)."""
    if dry_run:
        return False
    # Cheap guard: read current value, only write if different.
    cur = (
        client.table("documents")
        .select("provider_labels")
        .eq("doc_id", doc_id)
        .limit(1)
        .execute()
    )
    cur_labels = []
    if cur.data:
        cur_labels = list(cur.data[0].get("provider_labels") or [])
    if [str(x).strip() for x in cur_labels] == providers:
        return False
    (
        client.table("documents")
        .update({"provider_labels": providers})
        .eq("doc_id", doc_id)
        .execute()
    )
    return True


def _count_chunks_needing_update(
    client, doc_id: str, target_tier: str
) -> int:
    """Count chunks for this doc whose trust_tier is either NULL or
    a value different from `target_tier`. The delta an UPDATE would
    actually flip.

    PostgREST 3-valued logic gotcha: a bare `.neq("trust_tier", X)`
    excludes NULL rows because `NULL <> X` is NULL (not TRUE), so
    the count under-reports any column that isn't yet populated.
    Pre-Phase-11A the trust_tier column for interpretation chunks is
    almost entirely NULL — we OR the IS-NULL predicate explicitly.
    """
    resp = (
        client.table("document_chunks")
        .select("chunk_id", count="exact")
        .eq("doc_id", doc_id)
        .or_(f"trust_tier.is.null,trust_tier.neq.{target_tier}")
        .limit(0)
        .execute()
    )
    return int(resp.count or 0)


def _update_chunks_for_doc(
    client, doc_id: str, target_tier: str, *, dry_run: bool
) -> int:
    """Update all chunks for this doc to `target_tier`. Returns the
    count of rows actually changed (rows whose prior value was NULL
    or a different non-target tier)."""
    delta = _count_chunks_needing_update(client, doc_id, target_tier)
    if dry_run or delta == 0:
        return delta
    (
        client.table("document_chunks")
        .update({"trust_tier": target_tier})
        .eq("doc_id", doc_id)
        .or_(f"trust_tier.is.null,trust_tier.neq.{target_tier}")
        .execute()
    )
    return delta


def _now_bogota_stamp() -> str:
    return datetime.now(ZoneInfo("America/Bogota")).strftime(
        "%Y-%m-%d %I:%M:%S %p"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count delta but don't write.",
    )
    parser.add_argument(
        "--target",
        default="production",
        choices=("production", "staging", "wip"),
        help="Supabase target (resolves to LIA_Graph cloud).",
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=50,
        help="Abort after this many per-doc errors. Default 50.",
    )
    parser.add_argument(
        "--error-rate-after",
        type=int,
        default=100,
        help="Once this many docs processed, abort if error_rate > 10%%.",
    )
    args = parser.parse_args()

    if not os.environ.get("SUPABASE_URL"):
        print(
            "SUPABASE_URL unset — run: set -a; source .env.staging; set +a",
            file=sys.stderr,
        )
        return 2

    print(
        f"=== fix_v11_may Phase 11A trust_tier backfill — "
        f"{_now_bogota_stamp()} Bogotá [{'DRY-RUN' if args.dry_run else 'LIVE'}] ==="
    )
    print(f"  allowlist: {_ALLOWLIST_PATH.relative_to(_REPO_ROOT)}")
    allowlist, default_tier = _load_allowlist(_ALLOWLIST_PATH)
    for tier in _VALID_TIERS:
        print(f"  tier={tier:<7s} entries={len(allowlist[tier])}")
    print(f"  default (unmatched): {default_tier}\n")

    client = create_supabase_client_for_target(args.target)
    docs = _fetch_interp_documents(client)
    print(f"  interpretative_guidance docs in {args.target}: {len(docs)}")

    if not docs:
        print("  nothing to do.")
        return 0

    tier_counts: Counter[str] = Counter()
    chunks_touched_by_tier: Counter[str] = Counter()
    docs_touched_by_tier: Counter[str] = Counter()
    docs_with_providers_extracted = 0
    docs_with_provider_label_writes = 0
    docs_missing_local_md = 0
    error_count = 0
    error_patterns: Counter[str] = Counter()

    for idx, doc in enumerate(docs, start=1):
        doc_id = str(doc.get("doc_id") or "")
        if not doc_id:
            continue
        relative_path = str(doc.get("relative_path") or "")
        cloud_provider_labels = doc.get("provider_labels")
        if not isinstance(cloud_provider_labels, list):
            cloud_provider_labels = []

        # Step A — extract providers from local markdown
        md_text = _read_local_markdown(relative_path)
        if md_text is None:
            docs_missing_local_md += 1
            extracted_providers: list[str] = []
        else:
            extracted_providers = _extract_providers_from_markdown(md_text)
            if extracted_providers:
                docs_with_providers_extracted += 1

        # Effective providers = union(extracted, already-in-cloud); the
        # extraction is canonical-source-of-truth but we never strip a
        # firm a previous run wrote that the parser missed this time.
        merged_providers: list[str] = []
        seen_lower: set[str] = set()
        for src in (extracted_providers, cloud_provider_labels):
            for p in src:
                s = str(p or "").strip()
                if not s:
                    continue
                key = s.lower()
                if key in seen_lower:
                    continue
                seen_lower.add(key)
                merged_providers.append(s)

        # Step B — resolve tier from the merged provider list
        target_tier = _resolve_tier(
            authority=doc.get("authority"),  # type: ignore[arg-type]
            provider_labels=merged_providers,
            allowlist=allowlist,
            default=default_tier,
        )
        tier_counts[target_tier] += 1

        # Step C — write provider_labels (only if changed) + chunk tier
        try:
            wrote_labels = _write_provider_labels(
                client, doc_id, merged_providers, dry_run=args.dry_run
            )
            if wrote_labels:
                docs_with_provider_label_writes += 1
            changed = _update_chunks_for_doc(
                client, doc_id, target_tier, dry_run=args.dry_run
            )
        except Exception as exc:
            error_count += 1
            error_patterns[type(exc).__name__] += 1
            print(f"  ✗ {doc_id} → {target_tier} :: {type(exc).__name__}: {exc}")
            if error_count >= args.max_errors:
                print(
                    f"\n  ABORT: error_count {error_count} ≥ max_errors "
                    f"{args.max_errors}."
                )
                print(f"  error patterns: {dict(error_patterns)}")
                return 3
            continue
        chunks_touched_by_tier[target_tier] += changed
        if changed > 0:
            docs_touched_by_tier[target_tier] += 1

        if idx % 25 == 0 or idx == len(docs):
            error_rate = (error_count / idx) if idx else 0.0
            print(
                f"  [{_now_bogota_stamp()}] {idx}/{len(docs)} docs  "
                f"errors={error_count} ({error_rate:.1%})  "
                f"providers_extracted={docs_with_providers_extracted}  "
                f"chunks_changed={sum(chunks_touched_by_tier.values())}"
            )
            if (
                idx >= args.error_rate_after
                and error_count > 0
                and error_rate > 0.10
            ):
                print(
                    f"\n  ABORT: error_rate {error_rate:.1%} > 10% after "
                    f"{idx} docs."
                )
                print(f"  error patterns: {dict(error_patterns)}")
                return 3

    total_chunks_changed = sum(chunks_touched_by_tier.values())
    label = "would change" if args.dry_run else "changed"

    print()
    print("=== Provider extraction summary ===")
    print(f"  docs missing local markdown:        {docs_missing_local_md}")
    print(f"  docs with providers extracted:      {docs_with_providers_extracted}")
    print(
        f"  docs with provider_labels written:  "
        f"{docs_with_provider_label_writes}"
    )

    print()
    print("=== Tier resolution summary ===")
    for tier in _VALID_TIERS:
        print(
            f"  tier={tier:<7s} docs={tier_counts[tier]:>5d}  "
            f"docs_with_chunks_{label.split()[-1]}={docs_touched_by_tier[tier]:>5d}  "
            f"chunks_{label.split()[-1]}={chunks_touched_by_tier[tier]:>5d}"
        )
    print(f"\n  Total chunks {label}: {total_chunks_changed}")
    if args.dry_run:
        print(
            "\n  Dry-run only — no writes performed. Re-run without "
            "--dry-run to apply."
        )
    else:
        print(
            "\n  ✅ Backfill complete. Verify with:"
            "\n    PYTHONPATH=src:. uv run python "
            "scripts/diagnostics/probe_v11_trust_tier_coverage.py"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
