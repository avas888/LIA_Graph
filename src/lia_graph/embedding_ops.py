"""GUI-driven embedding operations with job lifecycle, heartbeat, and resume.

Mirrors the ``corpus_ops.py`` ``_JobContext`` pattern:
    start → heartbeat loop → batch embed → quality report → finish
    stop  → sets threading.Event → job persists ``cancelled`` with ``last_cursor_id``
    resume → reads ``last_cursor_id`` from cancelled job → continues from cutoff

Sharding (next_v7 P4 — concurrent backfill):
    Pass ``shard_x``/``shard_n`` (or ``--shard X/N`` from the CLI) to run
    one of N disjoint partitions of pending chunks. Partitioning uses a
    stable Python ``hashlib.md5(chunk_id)`` hash — server fetches the full
    batch, the worker keeps only rows where ``md5(chunk_id) % N == X``.
    Wastes (N-1)/N of fetch traffic per shard but unlocks parallel
    embedding-API utilization without a schema migration. Each shard
    runs in its OWN process — they're disjoint by design, so there's no
    write contention. Throughput cap is the embedding API itself.
"""

from __future__ import annotations

import copy
import hashlib
import logging
import math
import os
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .jobs_store import DEFAULT_JOBS_DIR, JobRecord, create_job, list_jobs, load_job, update_job

_log = logging.getLogger(__name__)

EMBEDDING_JOB_TYPE = "embedding_batch"
EMBEDDING_JOBS_DIR = DEFAULT_JOBS_DIR.parent / "embedding_runtime"
HEARTBEAT_INTERVAL_SECONDS = 5.0
LOG_TAIL_MAX_LINES = 160
LOG_TAIL_MAX_CHARS = 16_000

# ── Active job registry (in-process) ────────────────────────────────

_active_jobs: dict[str, "_EmbeddingJobRunner"] = {}
_active_lock = threading.Lock()


def _seconds_since_iso(iso_str: str | None) -> float | None:
    if not iso_str:
        return None
    try:
        parsed = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())
    except (ValueError, TypeError):
        return None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _trimmed_lines(text: str, *, max_lines: int = LOG_TAIL_MAX_LINES, max_chars: int = LOG_TAIL_MAX_CHARS) -> str:
    raw = str(text or "")
    lines = raw.splitlines()
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    trimmed = "\n".join(lines).strip()
    if len(trimmed) > max_chars:
        trimmed = trimmed[-max_chars:]
    return trimmed


# ── Job context (heartbeat + progress persistence) ──────────────────

@dataclass
class _EmbeddingJobCtx:
    job_id: str
    base_dir: Path
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        self._lock = threading.Lock()
        self._stop_heartbeat = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

    def start(self) -> None:
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True, name=f"embed-hb-{self.job_id[:8]}",
        )
        self._heartbeat_thread.start()

    def stop(self) -> None:
        self._stop_heartbeat.set()
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=1.0)

    def _heartbeat_loop(self) -> None:
        while not self._stop_heartbeat.wait(HEARTBEAT_INTERVAL_SECONDS):
            try:
                self.persist(status="running")
            except Exception:  # noqa: BLE001
                _log.warning("Heartbeat persist failed for embedding job %s", self.job_id, exc_info=True)

    def persist(self, *, status: str, error: str | None = None) -> None:
        with self._lock:
            snapshot = copy.deepcopy(self.payload)
            snapshot["heartbeat_at"] = _utc_now_iso()
            self.payload["heartbeat_at"] = snapshot["heartbeat_at"]
            if error is not None:
                self.payload["error"] = error
                snapshot["error"] = error
        update_job(
            self.job_id,
            status=status,
            result_payload=snapshot,
            error=error or "",
            base_dir=self.base_dir,
        )

    def set_fields(self, values: Mapping[str, Any], *, log_text: str | None = None) -> None:
        with self._lock:
            for key, value in values.items():
                self.payload[key] = value
            if log_text:
                current = str(self.payload.get("log_tail") or "").strip()
                merged = f"{current}\n{log_text}".strip() if current else str(log_text).strip()
                self.payload["log_tail"] = _trimmed_lines(merged)
        self.persist(status="running")

    def append_log(self, text: str) -> None:
        if not text:
            return
        with self._lock:
            current = str(self.payload.get("log_tail") or "").strip()
            merged = f"{current}\n{text}".strip() if current else str(text).strip()
            self.payload["log_tail"] = _trimmed_lines(merged)
        self.persist(status="running")

    def add_check(self, check_id: str, label: str, ok: bool, detail: str) -> None:
        entry = {"id": check_id, "label": label, "ok": bool(ok), "detail": str(detail or "").strip()}
        with self._lock:
            checks = [dict(c) for c in list(self.payload.get("checks") or []) if str(c.get("id") or "") != check_id]
            checks.append(entry)
            self.payload["checks"] = checks
        self.persist(status="running")

    def finish(self, *, ok: bool, status: str = "completed", error: str = "") -> None:
        with self._lock:
            self.payload["operation_ok"] = bool(ok)
            self.payload["completed_at"] = _utc_now_iso()
        self.persist(status=status, error=error)


# ── Job runner ──────────────────────────────────────────────────────

def _chunk_shard_index(chunk_id: str, n: int) -> int:
    """Stable client-side hash → shard index in ``[0, n)``.

    Uses MD5(chunk_id) first 4 bytes → big-endian uint → mod N. MD5 is
    overkill cryptographically but it's universally available in Python
    stdlib, deterministic across processes (Python's built-in ``hash()``
    is randomized via PYTHONHASHSEED), and uniform.
    """

    digest = hashlib.md5(str(chunk_id).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % max(int(n), 1)


class _EmbeddingJobRunner:
    def __init__(
        self, job_id: str, *, target: str, force: bool,
        resume_cursor_id: str | None = None,
        resume_embedded: int = 0, resume_failed: int = 0, resume_batches: int = 0,
        shard_x: int | None = None, shard_n: int | None = None,
    ) -> None:
        self.job_id = job_id
        self.target = target
        self.force = force
        self.resume_cursor_id = resume_cursor_id
        self.resume_embedded = resume_embedded
        self.resume_failed = resume_failed
        self.resume_batches = resume_batches
        # Sharding (next_v7 P4). Both must be set together; X in [0, N).
        if (shard_x is None) != (shard_n is None):
            raise ValueError("shard_x and shard_n must be set together")
        if shard_n is not None:
            if shard_n < 1:
                raise ValueError(f"shard_n must be >= 1, got {shard_n}")
            if shard_x is None or not (0 <= shard_x < shard_n):
                raise ValueError(f"shard_x must satisfy 0 <= X < {shard_n}, got {shard_x}")
        self.shard_x = shard_x
        self.shard_n = shard_n
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, daemon=True, name=f"embed-job-{self.job_id[:8]}",
        )
        self._thread.start()

    def request_stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        base_dir = EMBEDDING_JOBS_DIR
        ctx = _EmbeddingJobCtx(
            job_id=self.job_id,
            base_dir=base_dir,
            payload={
                "target": self.target,
                "force": self.force,
                "started_at": _utc_now_iso(),
                "stage": "embedding",
                "stage_status": "running",
                "log_tail": "",
                "checks": [],
                "progress": {},
                "quality_report": None,
            },
        )
        ctx.start()
        try:
            self._run_embedding(ctx)
        except Exception as exc:
            _log.exception("Embedding job %s failed", self.job_id)
            import traceback
            tb = traceback.format_exc()
            ctx.append_log(f"[FATAL] Thread crashed: {type(exc).__name__}: {exc}")
            ctx.append_log(f"[FATAL] Traceback:\n{tb[-500:]}")
            ctx.finish(ok=False, status="failed", error=str(exc))
        finally:
            ctx.stop()
            with _active_lock:
                _active_jobs.pop(self.job_id, None)

    def _run_embedding(self, ctx: _EmbeddingJobCtx) -> None:
        from .embeddings import _load_config, compute_embeddings_batch, is_available
        from .supabase_client import create_supabase_client_for_target, get_supabase_client

        if not is_available():
            raise RuntimeError("GEMINI_API_KEY not set — cannot generate embeddings")

        cfg = _load_config()
        batch_size = cfg.get("batch_size", 100)
        client = create_supabase_client_for_target(self.target) if self.target else get_supabase_client()

        # Count chunks
        total_q = client.table("document_chunks").select("id", count="exact").limit(0).execute()
        total_count = total_q.count or 0

        if self.force:
            pending_count_global = total_count
        else:
            pending_q = client.table("document_chunks").select("id", count="exact").is_("embedding", "null").limit(0).execute()
            pending_count_global = pending_q.count or 0

        # Sharded mode estimates this shard's slice as 1/N of pending. The
        # actual count varies slightly because md5 mod N is uniform but not
        # exactly even on small populations. Used for ETA / progress only;
        # the loop terminates when the global pending hits zero (i.e. all
        # shards have done their work).
        if self.shard_n is not None:
            pending_count = max(1, pending_count_global // self.shard_n)
        else:
            pending_count = pending_count_global

        _chunk_chars = int(os.environ.get("LIA_EMBED_CHUNK_CHARS", "512"))
        _combined_cap = int(os.environ.get("LIA_EMBED_COMBINED_CAP", "768"))

        ctx.append_log(f"[init] Thread {threading.current_thread().name} alive")
        ctx.append_log(f"[init] Target: {self.target}, force={self.force}, batch_size={batch_size}")
        if self.shard_n is not None:
            ctx.append_log(
                f"[init] Shard: {self.shard_x}/{self.shard_n} — "
                f"global pending {pending_count_global}, this shard ~{pending_count}"
            )
        else:
            ctx.append_log(f"[init] Total chunks: {total_count}, pending: {pending_count}")
        if self.resume_cursor_id:
            ctx.append_log(f"[init] Resuming from cursor: {self.resume_cursor_id}")
        ctx.append_log(f"[init] Gemini model: {cfg.get('model', '?')}, embed_chars={_chunk_chars}, cap={_combined_cap}")

        if pending_count == 0:
            ctx.append_log("All chunks already embedded.")
            ctx.add_check("coverage", "Embedding coverage", True, f"{total_count}/{total_count} chunks embedded (100%)")
            ctx.finish(ok=True)
            return

        # Embedding loop — carry over counters from previous run if resuming
        embedded = self.resume_embedded
        failed = self.resume_failed
        upsert_failures = 0
        current_batch = self.resume_batches
        total_batches = (pending_count + batch_size - 1) // batch_size
        t_start = time.monotonic()
        cursor_id = self.resume_cursor_id

        if embedded > 0:
            ctx.append_log(f"[init] Carrying over from previous run: {embedded} embedded, {failed} failed, batch {current_batch}")

        while True:
            if self._stop_event.is_set():
                ctx.append_log(f"Stop requested after {embedded} chunks. Cursor saved for resume.")
                ctx.set_fields({"progress": self._build_progress(
                    total_count, pending_count, embedded, failed, upsert_failures, current_batch,
                    total_batches, batch_size, t_start, cursor_id,
                )})
                ctx.finish(ok=False, status="cancelled")
                return

            # In sharded mode we OVER-FETCH to keep ~batch_size rows after
            # the client-side filter. md5 mod N is uniform, so fetching
            # batch_size * N rows yields ~batch_size that match the shard.
            fetch_size = batch_size * (self.shard_n or 1)

            q = client.table("document_chunks").select("id, doc_id, chunk_id, chunk_text, summary")
            if not self.force:
                q = q.is_("embedding", "null")
            # Sharded mode MUST advance cursor even when force=False —
            # otherwise rows hashing to other shards stay NULL forever and
            # this shard refetches the same window indefinitely.
            if (self.shard_n is not None or self.force) and cursor_id is not None:
                q = q.gt("id", cursor_id)
            q = q.order("id").limit(fetch_size)
            result = q.execute()
            rows = result.data or []
            if not rows:
                break
            cursor_id = rows[-1]["id"]
            current_batch += 1

            # Client-side shard filter — keep only rows whose chunk_id
            # hashes into this shard. Other shards (running in their own
            # processes) cover the remaining (N-1)/N of fetched rows.
            if self.shard_n is not None:
                rows = [
                    r for r in rows
                    if _chunk_shard_index(str(r.get("chunk_id") or r["id"]), self.shard_n) == self.shard_x
                ]
                if not rows:
                    # Whole fetch landed in other shards — advance cursor
                    # (already set above) and try the next window.
                    continue

            # Build embedding texts
            texts = []
            for r in rows:
                summary = str(r.get("summary") or "").strip()
                chunk_text = str(r.get("chunk_text") or "").strip()
                if summary and chunk_text:
                    combined = f"{summary}\n{chunk_text[:_chunk_chars]}"
                elif summary:
                    combined = summary
                else:
                    combined = chunk_text
                texts.append(combined[:_combined_cap])

            t_batch = time.monotonic()
            embeddings = compute_embeddings_batch(texts)
            api_ms = round((time.monotonic() - t_batch) * 1000)

            batch_ok = sum(1 for e in embeddings if e is not None)
            batch_fail = len(embeddings) - batch_ok

            # Retry once if entire batch failed (likely rate limit)
            if batch_ok == 0 and len(embeddings) > 0:
                ctx.append_log(f"[batch {current_batch}] API returned 0/{len(embeddings)} embeddings ({api_ms}ms) — retrying in 5s...")
                time.sleep(5.0)
                t_batch = time.monotonic()
                embeddings = compute_embeddings_batch(texts)
                api_ms = round((time.monotonic() - t_batch) * 1000)
                batch_ok = sum(1 for e in embeddings if e is not None)
                batch_fail = len(embeddings) - batch_ok
                if batch_ok == 0:
                    ctx.append_log(f"[batch {current_batch}] Retry also failed ({api_ms}ms) — Gemini API may be rate-limiting or down")
                else:
                    ctx.append_log(f"[batch {current_batch}] Retry succeeded: {batch_ok}/{len(embeddings)} ({api_ms}ms)")

            # Brief pause between batches to avoid Gemini rate limits
            time.sleep(0.5)

            # Batch upsert
            batch_updates: list[dict[str, Any]] = []
            batch_failed_ids: list[str] = []
            for row, emb in zip(rows, embeddings):
                if emb is None:
                    failed += 1
                    batch_failed_ids.append(str(row.get("chunk_id", row["id"])))
                    continue
                batch_updates.append({
                    "id": row["id"],
                    "doc_id": row["doc_id"],
                    "chunk_id": row["chunk_id"],
                    "chunk_text": row["chunk_text"],
                    "embedding": emb,
                })

            if batch_updates:
                try:
                    t_upsert = time.monotonic()
                    client.table("document_chunks").upsert(batch_updates, on_conflict="id").execute()
                    upsert_ms = round((time.monotonic() - t_upsert) * 1000)
                    embedded += len(batch_updates)
                except Exception as exc:
                    _log.exception("Upsert failed for batch %d", current_batch)
                    upsert_failures += len(batch_updates)
                    ctx.append_log(f"[batch {current_batch}] UPSERT FAILED: {str(exc)[:100]}")
                    upsert_ms = 0
            else:
                upsert_ms = 0

            # Update progress
            progress = self._build_progress(
                total_count, pending_count, embedded, failed, upsert_failures,
                current_batch, total_batches, batch_size, t_start, cursor_id,
            )

            # Log every batch with timing details
            log_line = f"[batch {current_batch}/{total_batches}] {batch_ok} ok, {batch_fail} fail | api={api_ms}ms upsert={upsert_ms}ms | total: {embedded}/{pending_count} ({progress['pct_complete']:.1f}%)"
            if batch_fail > 0:
                log_line += f" | failed: {batch_failed_ids[:2]}"

            # Thread health check
            thread_alive = threading.current_thread().is_alive()
            heartbeat_ok = not ctx._stop_heartbeat.is_set()
            if not thread_alive or not heartbeat_ok:
                log_line += f" | THREAD: alive={thread_alive} heartbeat={heartbeat_ok}"

            ctx.set_fields({"progress": progress}, log_text=log_line)

        # Completed — run quality validation
        elapsed = time.monotonic() - t_start
        rate = embedded / elapsed if elapsed > 0 else 0
        ctx.append_log(f"[done] Embedding complete: {embedded}/{pending_count} chunks in {elapsed:.1f}s ({rate:.1f} chunks/s)")
        ctx.append_log(f"[done] Failed: {failed}, Upsert failures: {upsert_failures}")
        ctx.append_log(f"[done] Thread {threading.current_thread().name} still alive: {threading.current_thread().is_alive()}")
        ctx.append_log(f"[done] Running quality validation...")

        quality_report = _validate_embedding_distribution(client)
        ctx.set_fields({
            "quality_report": quality_report,
            "progress": self._build_progress(
                total_count, pending_count, embedded, failed, upsert_failures,
                current_batch, total_batches, batch_size, t_start, cursor_id,
            ),
        })

        ctx.add_check("coverage", "Embedding coverage", failed < pending_count * 0.02,
                       f"{embedded}/{pending_count} embedded, {failed} failed ({failed/max(pending_count,1)*100:.2f}%)")
        ctx.add_check("distribution", "Embedding distribution",
                       not quality_report.get("collapsed_warning") and not quality_report.get("noise_warning"),
                       f"mean_cosine={quality_report.get('mean_cosine_similarity', 0):.4f}")

        all_ok = failed < pending_count * 0.02 and not quality_report.get("collapsed_warning")
        ctx.finish(ok=all_ok)

    def _build_progress(
        self,
        total: int, pending: int, embedded: int, failed: int, upsert_failures: int,
        current_batch: int, total_batches: int, batch_size: int,
        t_start: float, cursor_id: str | None,
    ) -> dict[str, Any]:
        elapsed = time.monotonic() - t_start
        rate = embedded / elapsed if elapsed > 0 else 0.0
        remaining = pending - embedded - failed
        eta = remaining / rate if rate > 0 else None
        out = {
            "total": total,
            "pending": pending,
            "embedded": embedded,
            "failed": failed,
            "upsert_failures": upsert_failures,
            "current_batch": current_batch,
            "total_batches": total_batches,
            "batch_size": batch_size,
            "elapsed_seconds": round(elapsed, 1),
            "rate_chunks_per_sec": round(rate, 1),
            "eta_seconds": round(eta, 1) if eta is not None else None,
            "pct_complete": round(embedded / max(pending, 1) * 100, 1),
            "last_cursor_id": cursor_id,
        }
        if self.shard_n is not None:
            out["shard_x"] = self.shard_x
            out["shard_n"] = self.shard_n
        return out


# ── Distribution validation ─────────────────────────────────────────

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _parse_emb(val: object) -> list[float] | None:
    if val is None:
        return None
    if isinstance(val, list):
        return [float(x) for x in val]
    if isinstance(val, str):
        import json
        try:
            return [float(x) for x in json.loads(val)]
        except (ValueError, json.JSONDecodeError):
            return None
    return None


def _validate_embedding_distribution(client: Any, sample_size: int = 50) -> dict[str, Any]:
    result = client.table("document_chunks").select("id, embedding").not_.is_("embedding", "null").limit(sample_size * 2).execute()
    rows = result.data or []
    if len(rows) < 10:
        return {"sample_pairs": 0, "collapsed_warning": False, "noise_warning": False, "too_few_samples": True}

    sample = random.sample(rows, min(sample_size, len(rows)))
    similarities: list[float] = []
    for i in range(len(sample)):
        for j in range(i + 1, min(i + 5, len(sample))):
            emb_a = _parse_emb(sample[i].get("embedding"))
            emb_b = _parse_emb(sample[j].get("embedding"))
            if not emb_a or not emb_b:
                continue
            similarities.append(_cosine_similarity(emb_a, emb_b))

    if not similarities:
        return {"sample_pairs": 0, "collapsed_warning": False, "noise_warning": False}

    mean_sim = sum(similarities) / len(similarities)
    return {
        "mean_cosine_similarity": round(mean_sim, 4),
        "min_cosine_similarity": round(min(similarities), 4),
        "max_cosine_similarity": round(max(similarities), 4),
        "sample_pairs": len(similarities),
        "collapsed_warning": mean_sim > 0.95,
        "noise_warning": mean_sim < 0.10,
    }


# ── Public API ──────────────────────────────────────────────────────

def _launch_embedding_subprocess(record: JobRecord, *, base_dir: Path) -> None:
    """Launch embedding job as detached subprocess that survives server reload."""
    import shutil
    import subprocess

    workspace_root = Path(__file__).resolve().parents[2]
    script = workspace_root / "scripts" / "run_embedding_job.py"
    uv_path = shutil.which("uv")
    if uv_path:
        cmd = [uv_path, "run", "python", str(script), record.job_id, str(base_dir)]
    else:
        cmd = ["python3", str(script), record.job_id, str(base_dir)]

    env = dict(os.environ)
    env["PYTHONPATH"] = f"src:{workspace_root}"

    _log.info("Launching embedding job %s as subprocess", record.job_id[:8])
    subprocess.Popen(
        cmd,
        cwd=str(workspace_root),
        env=env,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _find_active_job() -> _EmbeddingJobRunner | None:
    with _active_lock:
        for runner in _active_jobs.values():
            if runner._thread and runner._thread.is_alive():
                return runner
    return None


def start_embedding_job(*, target: str = "wip", force: bool = False) -> JobRecord:
    active = _find_active_job()
    if active is not None:
        raise RuntimeError(f"Embedding job already running: {active.job_id}")

    base_dir = EMBEDDING_JOBS_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    record = create_job(
        job_type=EMBEDDING_JOB_TYPE,
        request_payload={"target": target, "force": force},
        base_dir=base_dir,
    )

    _launch_embedding_subprocess(record, base_dir=base_dir)
    return record


def stop_embedding_job(job_id: str) -> dict[str, Any]:
    with _active_lock:
        runner = _active_jobs.get(job_id)
    if runner is None:
        # Job might have finished already — mark as cancelled via disk if still running
        record = load_job(job_id, base_dir=EMBEDDING_JOBS_DIR)
        if record and record.status == "running":
            update_job(job_id, status="cancelled", error="Stop requested", base_dir=EMBEDDING_JOBS_DIR)
            return {"ok": True, "status": "cancelled"}
        return {"ok": False, "error": "Job not found or not running"}
    runner.request_stop()
    # Don't block the HTTP response — the job will stop at next batch boundary
    return {"ok": True, "status": "cancelling"}


def resume_embedding_job(job_id: str) -> JobRecord:
    record = load_job(job_id, base_dir=EMBEDDING_JOBS_DIR)
    if record is None:
        raise RuntimeError(f"Job {job_id} not found")
    if record.status not in ("cancelled", "failed"):
        raise RuntimeError(f"Job {job_id} status is {record.status}, cannot resume")

    prev_progress = record.result_payload.get("progress") or {}
    cursor_id = prev_progress.get("last_cursor_id")
    prev_embedded = int(prev_progress.get("embedded") or 0)
    prev_failed = int(prev_progress.get("failed") or 0)
    prev_batches = int(prev_progress.get("current_batch") or 0)
    target = record.request_payload.get("target", "wip")
    force = record.request_payload.get("force", False)

    active = _find_active_job()
    if active is not None:
        raise RuntimeError(f"Embedding job already running: {active.job_id}")

    base_dir = EMBEDDING_JOBS_DIR
    new_record = create_job(
        job_type=EMBEDDING_JOB_TYPE,
        request_payload={
            "target": target, "force": force, "resumed_from": job_id,
            "resume_cursor_id": cursor_id,
            "resume_embedded": prev_embedded, "resume_failed": prev_failed, "resume_batches": prev_batches,
        },
        base_dir=base_dir,
    )

    _launch_embedding_subprocess(new_record, base_dir=base_dir)
    return new_record


def build_embedding_status(*, target: str = "wip") -> dict[str, Any]:
    """Build the full embedding status payload for the GUI."""
    # Supabase counts
    try:
        from .supabase_client import create_supabase_client_for_target, get_supabase_client
        client = create_supabase_client_for_target(target) if target else get_supabase_client()
        total_q = client.table("document_chunks").select("id", count="exact").limit(0).execute()
        total = total_q.count or 0
        null_q = client.table("document_chunks").select("id", count="exact").is_("embedding", "null").limit(0).execute()
        null_count = null_q.count or 0
    except Exception:
        _log.warning("Cannot query Supabase for embedding status", exc_info=True)
        total = 0
        null_count = 0

    embedded = total - null_count

    # Find current/last jobs
    base_dir = EMBEDDING_JOBS_DIR
    current_op = None
    last_op = None

    try:
        jobs = list_jobs(base_dir=base_dir)
        jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    except Exception:
        jobs = []

    for j in jobs:
        payload = dict(j.get("result_payload") or {})
        status = str(j.get("status", "")).strip()
        op = {
            "job_id": j.get("job_id", ""),
            "status": status,
            "started_at": payload.get("started_at", j.get("created_at", "")),
            "updated_at": j.get("updated_at", ""),
            "heartbeat_at": payload.get("heartbeat_at", ""),
            "target": payload.get("target", j.get("request_payload", {}).get("target", "wip")),
            "force": payload.get("force", j.get("request_payload", {}).get("force", False)),
            "progress": payload.get("progress", {}),
            "quality_report": payload.get("quality_report"),
            "checks": payload.get("checks", []),
            "log_tail": payload.get("log_tail", ""),
            "error": payload.get("error") or j.get("error", ""),
        }
        if status in ("running", "queued"):
            # Detect stalled jobs: heartbeat >60s old and no in-process runner
            heartbeat_age = _seconds_since_iso(op["heartbeat_at"])
            runner_alive = _find_active_job() is not None
            if heartbeat_age is not None and heartbeat_age > 60 and not runner_alive:
                op["status"] = "stalled"
                # Also persist the stall so it's visible on next read
                update_job(op["job_id"], status="failed", error="Job stalled (thread died)", base_dir=base_dir)
                if last_op is None:
                    last_op = op
            else:
                current_op = op
        elif last_op is None and status in ("completed", "failed", "cancelled", "stalled"):
            last_op = op

    # Gemini API health probe
    api_health = _probe_gemini_api()

    return {
        "target": target,
        "total_chunks": total,
        "embedded_chunks": embedded,
        "null_embedding_chunks": null_count,
        "coverage_pct": round(embedded / max(total, 1) * 100, 1),
        "current_operation": current_op,
        "last_operation": last_op,
        "api_health": api_health,
    }


def _probe_gemini_api() -> dict[str, Any]:
    """Quick probe: generate a single embedding to verify API key + connectivity."""
    try:
        from .embeddings import is_available
        if not is_available():
            return {"ok": False, "detail": "GEMINI_API_KEY not set"}

        from .embeddings import compute_embedding
        t0 = time.monotonic()
        result = compute_embedding("test de conectividad")
        latency_ms = round((time.monotonic() - t0) * 1000)
        if result is None:
            return {"ok": False, "detail": "API returned null", "latency_ms": latency_ms}
        return {"ok": True, "detail": f"{len(result)}d, {latency_ms}ms", "latency_ms": latency_ms}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:120]}
