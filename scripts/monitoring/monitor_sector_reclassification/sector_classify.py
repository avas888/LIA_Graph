#!/usr/bin/env python3
"""ingestionfix_v3 Phase 2.5 Task A — LLM-assisted sector classification.

Reads the 510 ``otros_sectoriales`` doc_ids from a probe manifest, groups them
into batches (default 20/batch = ~26 batches for the current corpus), and
classifies each doc's sector / migration-target via Gemini.

## Why batching + checkpointing

Mirrors the durability contract baked into ``launch_batch.sh`` (see
docs/next/ingestionfix_v3.md §5 Phase 3). The classifier isn't a destructive
operation — it's a read-only LLM call — but 510 API calls at ~1-2 seconds
each is 10-20 minutes of wall time, and we don't want a network blip to
force a full restart. So:

1. Each batch writes its result atomically to
   ``artifacts/sector_classification/batches/batch_NNN.json`` (temp + rename).
2. ``artifacts/sector_classification/index.json`` tracks batch status
   (``pending`` / ``in_flight`` / ``done`` / ``failed``).
3. On startup, the script reads the index and skips any batch already
   marked ``done``. Retries only touch the unfinished slice.
4. SIGINT is trapped and flips the current batch to ``interrupted`` before
   exiting, so resume knows exactly where it stopped.

## Visible heartbeat

After every batch the script prints a one-block status to stdout:

- progress bar + count
- ETA (Bogotá AM/PM)
- cumulative sector label histogram so the operator can watch the shape
  of the proposal emerge in real time
- running Gemini cost estimate

## Output

Final aggregation step writes
``artifacts/sector_reclassification_proposal.json`` — a flat list of
``{doc_id, proposed_topic, proposed_topic_kind, confidence, reasoning,
title, current_tema}`` records for operator review (Phase 2.5 Task B).

No Supabase / Falkor writes. This is read-only. All safety rails are
around wall-time + API cost, not data mutation.

## Usage

    set -a; source .env.local; set +a        # for GEMINI_API_KEY
    PYTHONPATH=src:. uv run python \\
      scripts/monitoring/monitor_ingest_topic_batches/sector_classify.py \\
      --manifest artifacts/fingerprint_bust/<latest>_probe_otros_sectoriales.json

    # resume after a crash — just re-run the same command.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import signal
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# Bogotá time (UTC-5, no DST) for all user-facing timestamps per repo convention.
BOG = _dt.timezone(_dt.timedelta(hours=-5))

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_BATCH_SIZE = 20
# Rough cost estimate for gemini-2.5-flash; meant as "are we in the right
# order of magnitude?" not billing-grade.
COST_PER_1K_INPUT_TOKENS_USD = 0.0003
COST_PER_1K_OUTPUT_TOKENS_USD = 0.0025


# ── Existing-topic list (the 39 current top-level taxonomy keys) ─────


def load_existing_topics(taxonomy_path: Path) -> list[str]:
    data = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    return [t["key"] for t in data.get("topics", []) if not t.get("parent_key")]


# ── Doc content loader ──────────────────────────────────────────────


def _doc_id_to_path_candidates(doc_id: str, repo_root: Path) -> list[Path]:
    """Turn a doc_id like ``CORE_ya_Arriba_LEYES_OTROS_SECTORIALES_consolidado_Ley-1712-2014.md``
    back into filesystem path candidates. doc_ids encode the knowledge_base
    path with underscores replacing spaces and slashes; we reverse that.
    """
    name = doc_id
    if name.startswith("CORE_ya_Arriba_"):
        rest = name[len("CORE_ya_Arriba_") :]
    else:
        rest = name
    # First attempt: the top-level folder is "CORE ya Arriba" and subsequent
    # tokens are slash-separated.
    parts = rest.rsplit("_", 1)
    if len(parts) == 2:
        prefix, leaf = parts
        prefix_slashed = prefix.replace("_", "/")
        return [
            repo_root / "knowledge_base" / "CORE ya Arriba" / prefix_slashed / leaf,
            repo_root / "knowledge_base" / "CORE ya Arriba" / (rest.replace("_", "/")),
        ]
    return [repo_root / "knowledge_base" / "CORE ya Arriba" / rest.replace("_", "/")]


def load_doc_content(
    doc_id: str, repo_root: Path, *, max_lines: int = 40
) -> tuple[str, str]:
    """Return (title, first_paragraph) for a doc. Title = first heading line
    (or first non-empty line). Paragraph = first ~40 lines joined.
    """
    candidates = _doc_id_to_path_candidates(doc_id, repo_root)
    content = ""
    for path in candidates:
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
            break
    if not content:
        return "", ""
    lines = content.splitlines()
    title = ""
    for line in lines:
        stripped = line.strip()
        if stripped:
            title = stripped.lstrip("# ").strip()
            break
    head = "\n".join(lines[:max_lines]).strip()
    return title, head


# ── Gemini call ─────────────────────────────────────────────────────


_CLASSIFICATION_PROMPT_TEMPLATE = """Eres un experto contador colombiano clasificando leyes por su tema. Cada ley debe ser asignada a UNA de tres opciones:

OPCIÓN 1 — MIGRAR A TOPIC EXISTENTE: La ley claramente pertenece a uno de estos topics ya presentes en la taxonomía:
{existing_topics}

OPCIÓN 2 — NUEVO SECTOR: La ley trata un sector no cubierto por los topics existentes (ej: salud, educación, agropecuario, servicios_publicos, cultura, vivienda, turismo, etc). Proponle un nombre en snake_case prefijado con `sector_` (ej: `sector_salud`, `sector_educacion`).

OPCIÓN 3 — HUÉRFANO: No encaja claramente en ningún topic ni se puede agrupar con otras leyes similares.

Para cada ley abajo, devuelve SOLO un JSON array con este formato exacto (sin prosa adicional, sin markdown, sin ```json):

[
  {{"doc_id": "...", "proposed_topic": "nombre_del_topic", "kind": "migrate|new_sector|orphan", "confidence": "high|medium|low", "reasoning": "breve, en español, máx 20 palabras"}}
]

Leyes a clasificar:

{doc_blocks}
"""


@dataclass
class ClassificationResult:
    doc_id: str
    proposed_topic: str
    kind: str  # migrate | new_sector | orphan | error
    confidence: str  # high | medium | low | n/a
    reasoning: str
    title: str = ""

    @classmethod
    def error(cls, doc_id: str, title: str, reason: str) -> "ClassificationResult":
        return cls(
            doc_id=doc_id,
            proposed_topic="otros_sectoriales",
            kind="error",
            confidence="n/a",
            reasoning=reason[:200],
            title=title,
        )


def _extract_json_array(raw: str) -> list[dict[str, Any]]:
    """Parse a JSON array from LLM output even if it's wrapped in prose/fences."""
    stripped = raw.strip()
    # Peel fenced blocks
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    # Find first [ and last ] to tolerate leading prose
    lb = stripped.find("[")
    rb = stripped.rfind("]")
    if lb == -1 or rb == -1 or rb <= lb:
        raise ValueError("no JSON array found in response")
    payload = stripped[lb : rb + 1]
    return json.loads(payload)


def classify_batch(
    adapter: Any,
    *,
    docs: list[tuple[str, str, str]],  # (doc_id, title, head)
    existing_topics: list[str],
) -> list[ClassificationResult]:
    """Send one batch to Gemini; map response back to per-doc results.

    Robust to: missing doc_ids in response, extra entries, malformed JSON.
    Any doc not present in the response comes back as ``kind=error``.
    """
    topic_lines = "\n".join(f"  - {t}" for t in existing_topics)
    doc_blocks = "\n\n".join(
        f"### doc_id: {did}\n**Título:** {title}\n**Contenido:**\n{head[:1200]}"
        for did, title, head in docs
    )
    prompt = _CLASSIFICATION_PROMPT_TEMPLATE.format(
        existing_topics=topic_lines, doc_blocks=doc_blocks
    )

    raw = adapter.generate(prompt)
    by_id: dict[str, dict[str, Any]] = {}
    try:
        parsed = _extract_json_array(raw)
        for entry in parsed:
            did = str(entry.get("doc_id") or "").strip()
            if did:
                by_id[did] = entry
    except Exception as exc:
        # Mark every doc in batch as error; caller will retry or flag for review.
        return [
            ClassificationResult.error(did, title, f"parse_failed: {exc}")
            for did, title, _ in docs
        ]

    results: list[ClassificationResult] = []
    for did, title, _head in docs:
        entry = by_id.get(did)
        if entry is None:
            results.append(
                ClassificationResult.error(did, title, "llm_omitted_doc")
            )
            continue
        results.append(
            ClassificationResult(
                doc_id=did,
                proposed_topic=str(entry.get("proposed_topic") or "otros_sectoriales"),
                kind=str(entry.get("kind") or "orphan"),
                confidence=str(entry.get("confidence") or "low"),
                reasoning=str(entry.get("reasoning") or "")[:240],
                title=title,
            )
        )
    return results


# ── Checkpointing ────────────────────────────────────────────────────


@dataclass
class BatchState:
    batch_num: int
    doc_ids: list[str]
    status: str = "pending"  # pending | in_flight | done | failed | interrupted
    started_at_utc: str | None = None
    completed_at_utc: str | None = None
    result_path: str | None = None
    error: str | None = None
    input_hash: str = ""


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def load_index(index_path: Path) -> dict[str, Any]:
    if index_path.exists():
        try:
            return json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"batches": {}, "created_at_utc": None}


def save_index(index_path: Path, index: dict[str, Any]) -> None:
    index["updated_at_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    _atomic_write_json(index_path, index)


def _hash_ids(ids: Iterable[str]) -> str:
    h = hashlib.sha256()
    for did in sorted(ids):
        h.update(did.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()[:16]


# ── Heartbeat ────────────────────────────────────────────────────────


def _bog_time(dt: _dt.datetime) -> str:
    return dt.astimezone(BOG).strftime("%-I:%M:%S %p").lstrip("0")


def render_heartbeat(
    *,
    batch_num: int,
    total_batches: int,
    per_batch_seconds: list[float],
    sector_histogram: dict[str, int],
    migration_histogram: dict[str, int],
    errors: int,
    total_docs_done: int,
    total_docs: int,
    cost_usd: float,
    just_finished_batch: bool = True,
) -> str:
    now = _dt.datetime.now(_dt.timezone.utc)
    avg = sum(per_batch_seconds) / len(per_batch_seconds) if per_batch_seconds else 0.0
    remaining_batches = max(total_batches - batch_num, 0)
    eta_sec = avg * remaining_batches if avg > 0 else 0
    eta_wall = (
        _bog_time(now + _dt.timedelta(seconds=eta_sec)) if eta_sec > 0 else "—"
    )

    pct = (total_docs_done / total_docs * 100) if total_docs > 0 else 0
    bar_len = 30
    filled = min(bar_len, int(bar_len * pct / 100))
    bar = "█" * filled + "░" * (bar_len - filled)

    def _hist(h: dict[str, int], topn: int) -> str:
        items = sorted(h.items(), key=lambda kv: -kv[1])[:topn]
        return ", ".join(f"{k}={v}" for k, v in items) or "(none yet)"

    verb = "finished" if just_finished_batch else "starting"
    lines = [
        "",
        "────────────────────────────────────────────────────────────────",
        f"[sector_classify] batch {batch_num}/{total_batches} {verb} · {_bog_time(now)} Bogotá",
        f"  {bar}  {pct:.1f}%   {total_docs_done}/{total_docs} docs",
        f"  avg/batch: {avg:.1f}s   ETA: {eta_sec/60:.1f} min → {eta_wall}",
        f"  running cost estimate: ${cost_usd:.3f} USD",
        f"  errors so far: {errors}",
        f"  top proposed new sectors:   {_hist(sector_histogram, 8)}",
        f"  top migrate-to targets:     {_hist(migration_histogram, 6)}",
        "────────────────────────────────────────────────────────────────",
    ]
    return "\n".join(lines)


# ── Main orchestrator ───────────────────────────────────────────────


@dataclass
class RunStats:
    batches_total: int
    batches_done: int = 0
    docs_total: int = 0
    docs_done: int = 0
    errors: int = 0
    sector_histogram: dict[str, int] = field(default_factory=dict)
    migration_histogram: dict[str, int] = field(default_factory=dict)
    per_batch_seconds: list[float] = field(default_factory=list)
    cost_usd: float = 0.0


def _load_manifest_doc_ids(manifest_path: Path) -> list[str]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    ids = list(data.get("doc_ids") or [])
    # De-dup while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for d in ids:
        if d and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def _build_batches(
    doc_ids: list[str], batch_size: int
) -> list[BatchState]:
    batches: list[BatchState] = []
    for i in range(0, len(doc_ids), batch_size):
        chunk = doc_ids[i : i + batch_size]
        batches.append(
            BatchState(
                batch_num=(i // batch_size) + 1,
                doc_ids=chunk,
                input_hash=_hash_ids(chunk),
            )
        )
    return batches


def _ingest_results_into_stats(
    results: list[ClassificationResult], stats: RunStats
) -> None:
    for r in results:
        stats.docs_done += 1
        if r.kind == "error":
            stats.errors += 1
            continue
        if r.kind == "new_sector":
            stats.sector_histogram[r.proposed_topic] = (
                stats.sector_histogram.get(r.proposed_topic, 0) + 1
            )
        elif r.kind == "migrate":
            stats.migration_histogram[r.proposed_topic] = (
                stats.migration_histogram.get(r.proposed_topic, 0) + 1
            )


def _estimate_cost(prompt_chars: int, output_chars: int) -> float:
    # crude: 1 token ~= 4 chars
    in_tok = prompt_chars / 4
    out_tok = output_chars / 4
    return (
        in_tok / 1000 * COST_PER_1K_INPUT_TOKENS_USD
        + out_tok / 1000 * COST_PER_1K_OUTPUT_TOKENS_USD
    )


def run(
    *,
    manifest_path: Path,
    output_dir: Path,
    taxonomy_path: Path,
    repo_root: Path,
    batch_size: int,
    model: str,
    api_key: str,
    dry_run: bool = False,
    max_batches: int | None = None,
) -> int:
    from lia_graph.gemini_runtime import (
        GeminiChatAdapter,
        DEFAULT_GEMINI_OPENAI_BASE_URL,
    )

    existing_topics = load_existing_topics(taxonomy_path)
    doc_ids = _load_manifest_doc_ids(manifest_path)
    batches = _build_batches(doc_ids, batch_size)

    batch_dir = output_dir / "batches"
    batch_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.json"
    index = load_index(index_path)
    index.setdefault("created_at_utc", _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    index["manifest_path"] = str(manifest_path)
    index["batch_size"] = batch_size
    index["total_docs"] = len(doc_ids)
    index["total_batches"] = len(batches)
    index["model"] = model
    index.setdefault("batches", {})

    stats = RunStats(batches_total=len(batches), docs_total=len(doc_ids))

    # Replay stats from any already-done batches so the heartbeat is accurate
    # across resumes.
    for bs in batches:
        key = f"{bs.batch_num:03d}"
        rec = index["batches"].get(key) or {}
        if rec.get("status") == "done" and rec.get("result_path"):
            stats.batches_done += 1
            try:
                done_results = json.loads(
                    Path(rec["result_path"]).read_text(encoding="utf-8")
                )["results"]
                parsed = [
                    ClassificationResult(
                        doc_id=r["doc_id"],
                        proposed_topic=r["proposed_topic"],
                        kind=r["kind"],
                        confidence=r["confidence"],
                        reasoning=r["reasoning"],
                        title=r.get("title", ""),
                    )
                    for r in done_results
                ]
                _ingest_results_into_stats(parsed, stats)
                stats.per_batch_seconds.append(float(rec.get("elapsed_seconds") or 0))
            except Exception:
                pass

    if stats.batches_done > 0:
        print(
            f"[sector_classify] resumed — {stats.batches_done}/{stats.batches_total} "
            f"batches already done; skipping those."
        )

    adapter = None
    if not dry_run:
        adapter = GeminiChatAdapter(
            model=model,
            api_key=api_key,
            base_url=DEFAULT_GEMINI_OPENAI_BASE_URL,
            timeout_seconds=90.0,
            temperature=0.1,
        )

    # SIGINT handler — mark the currently in-flight batch as interrupted
    # so a resume run knows it needs to retry.
    current_batch_key: list[str] = [""]

    def _on_sigint(signum: int, frame: Any) -> None:
        key = current_batch_key[0]
        if key:
            rec = index["batches"].get(key) or {}
            if rec.get("status") == "in_flight":
                rec["status"] = "interrupted"
                rec["interrupted_at_utc"] = _dt.datetime.now(
                    _dt.timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
                index["batches"][key] = rec
                save_index(index_path, index)
        print(
            f"\n[sector_classify] interrupted — resume later; {stats.batches_done}/{stats.batches_total} batches done",
            file=sys.stderr,
        )
        sys.exit(130)

    signal.signal(signal.SIGINT, _on_sigint)
    signal.signal(signal.SIGTERM, _on_sigint)

    new_batches_this_run = 0
    for bs in batches:
        key = f"{bs.batch_num:03d}"
        rec = index["batches"].get(key) or {}
        if rec.get("status") == "done" and rec.get("input_hash") == bs.input_hash:
            continue
        # --max-batches is a per-invocation cap; resumed batches don't count.
        if max_batches is not None and new_batches_this_run >= max_batches:
            print(f"[sector_classify] --max-batches {max_batches} reached; stopping.")
            break
        new_batches_this_run += 1

        # Mark in_flight BEFORE any I/O (durability invariant #1).
        rec = {
            "batch_num": bs.batch_num,
            "status": "in_flight",
            "input_hash": bs.input_hash,
            "started_at_utc": _dt.datetime.now(_dt.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "doc_count": len(bs.doc_ids),
        }
        index["batches"][key] = rec
        save_index(index_path, index)
        current_batch_key[0] = key

        # Load content for this batch's docs.
        content: list[tuple[str, str, str]] = []
        for did in bs.doc_ids:
            title, head = load_doc_content(did, repo_root)
            content.append((did, title, head))

        t_start = time.time()
        if dry_run:
            # Fabricate deterministic results so tests / rehearsals don't cost money.
            results = [
                ClassificationResult(
                    doc_id=did,
                    proposed_topic="sector_dryrun",
                    kind="new_sector",
                    confidence="low",
                    reasoning="dry-run stub",
                    title=title,
                )
                for did, title, _ in content
            ]
        else:
            try:
                assert adapter is not None
                results = classify_batch(
                    adapter, docs=content, existing_topics=existing_topics
                )
            except Exception as exc:
                rec["status"] = "failed"
                rec["error"] = str(exc)[:400]
                rec["failed_at_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
                index["batches"][key] = rec
                save_index(index_path, index)
                print(
                    f"[sector_classify] batch {bs.batch_num} FAILED: {exc}",
                    file=sys.stderr,
                )
                # Continue to next batch — the operator can re-run to retry this one.
                continue

        elapsed = time.time() - t_start

        # Write batch result file (atomic).
        result_path = batch_dir / f"batch_{key}.json"
        payload = {
            "batch_num": bs.batch_num,
            "input_hash": bs.input_hash,
            "doc_ids": bs.doc_ids,
            "elapsed_seconds": round(elapsed, 2),
            "model": model,
            "results": [
                {
                    "doc_id": r.doc_id,
                    "proposed_topic": r.proposed_topic,
                    "kind": r.kind,
                    "confidence": r.confidence,
                    "reasoning": r.reasoning,
                    "title": r.title,
                }
                for r in results
            ],
        }
        _atomic_write_json(result_path, payload)

        # Mark done.
        rec["status"] = "done"
        rec["completed_at_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        rec["elapsed_seconds"] = round(elapsed, 2)
        rec["result_path"] = str(result_path)
        index["batches"][key] = rec
        save_index(index_path, index)
        current_batch_key[0] = ""

        # Update stats + heartbeat.
        stats.batches_done += 1
        stats.per_batch_seconds.append(elapsed)
        _ingest_results_into_stats(results, stats)
        prompt_chars = sum(len(c[2]) for c in content) + 2000
        output_chars = sum(len(r.reasoning) + 40 for r in results)
        stats.cost_usd += _estimate_cost(prompt_chars, output_chars)
        print(
            render_heartbeat(
                batch_num=stats.batches_done,
                total_batches=stats.batches_total,
                per_batch_seconds=stats.per_batch_seconds,
                sector_histogram=stats.sector_histogram,
                migration_histogram=stats.migration_histogram,
                errors=stats.errors,
                total_docs_done=stats.docs_done,
                total_docs=stats.docs_total,
                cost_usd=stats.cost_usd,
            ),
            flush=True,
        )

    # Final aggregation.
    aggregate_path = output_dir / "sector_reclassification_proposal.json"
    aggregate_results: list[dict[str, Any]] = []
    for bs in batches:
        key = f"{bs.batch_num:03d}"
        rec = index["batches"].get(key) or {}
        if rec.get("status") != "done":
            continue
        rp = Path(rec.get("result_path") or "")
        if not rp.exists():
            continue
        batch_payload = json.loads(rp.read_text(encoding="utf-8"))
        aggregate_results.extend(batch_payload.get("results") or [])

    summary = {
        "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "source_manifest": str(manifest_path),
        "model": model,
        "total_docs": len(doc_ids),
        "total_classified": len(aggregate_results),
        "total_errors": sum(
            1 for r in aggregate_results if r.get("kind") == "error"
        ),
        "new_sector_label_counts": _histogram(
            [
                r["proposed_topic"]
                for r in aggregate_results
                if r.get("kind") == "new_sector"
            ]
        ),
        "migrate_target_counts": _histogram(
            [
                r["proposed_topic"]
                for r in aggregate_results
                if r.get("kind") == "migrate"
            ]
        ),
        "kind_counts": _histogram([r["kind"] for r in aggregate_results]),
        "estimated_cost_usd": round(stats.cost_usd, 3),
        "results": aggregate_results,
    }
    _atomic_write_json(aggregate_path, summary)

    print(
        f"\n[sector_classify] complete. Aggregate proposal at {aggregate_path}",
        flush=True,
    )
    return 0 if stats.errors == 0 else 1


def _histogram(values: list[str]) -> dict[str, int]:
    h: dict[str, int] = {}
    for v in values:
        h[v] = h.get(v, 0) + 1
    return dict(sorted(h.items(), key=lambda kv: -kv[1]))


# ── CLI ──────────────────────────────────────────────────────────────


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sector_classify",
        description=(
            "LLM-assisted sector classification of otros_sectoriales docs. "
            "Resumable across restarts; per-batch checkpoint; visible heartbeat."
        ),
    )
    p.add_argument(
        "--manifest",
        required=True,
        help="Path to a fingerprint_bust probe manifest "
             "(typically artifacts/fingerprint_bust/<ts>_probe_otros_sectoriales.json).",
    )
    p.add_argument(
        "--output-dir",
        default="artifacts/sector_classification",
        help="Directory for per-batch checkpoints + final proposal.",
    )
    p.add_argument(
        "--taxonomy",
        default="config/topic_taxonomy.json",
        help="Existing taxonomy (for the 'migrate' option topic list).",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Docs per Gemini call (default {DEFAULT_BATCH_SIZE}).",
    )
    p.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini model (default {DEFAULT_MODEL}).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip Gemini calls; fabricate stub results (for wiring tests).",
    )
    p.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Process at most N batches this run (useful for staged rollout).",
    )
    return p


def main(argv: Iterable[str] | None = None) -> int:
    args = build_argparser().parse_args(list(argv) if argv is not None else None)
    repo_root = Path(__file__).resolve().parents[3]
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not args.dry_run and not api_key:
        print(
            "[sector_classify] ERROR: GEMINI_API_KEY not set. "
            "Source .env.local before invoking.",
            file=sys.stderr,
        )
        return 2
    return run(
        manifest_path=Path(args.manifest),
        output_dir=Path(args.output_dir),
        taxonomy_path=Path(args.taxonomy),
        repo_root=repo_root,
        batch_size=args.batch_size,
        model=args.model,
        api_key=api_key,
        dry_run=args.dry_run,
        max_batches=args.max_batches,
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
