"""Tests for the ``ingest_delta_jobs`` partial-unique-index concurrency guard.

These exercise the DB-level lock behavior (Decision J2). They require a local
Supabase docker stack with the Phase 1 migrations applied. When the stack is
not available, the tests skip (they do not silently pass).

Run explicitly with::

    PYTHONPATH=src:. uv run --group dev pytest tests/test_ingest_delta_jobs_lock.py -v
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import pytest


def _require_local_supabase() -> Any:
    """Return a service-role Supabase client pointed at local docker, or skip.

    Resolves env via the project's standard env loader (``.env.local``), so
    the normal dev workflow (`make supabase-start`, run tests) just works
    without extra env plumbing. Guards against running against cloud by
    requiring the URL to be a localhost.
    """
    supabase_mod = pytest.importorskip("supabase")
    try:
        from lia_graph.env_loader import load_dotenv_if_present

        load_dotenv_if_present()
    except Exception:
        pass
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        pytest.skip(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing — skipping DB-level "
            "lock tests (run `make supabase-start` and source .env.local)."
        )
    # Safety: never run these tests against cloud by accident.
    if "127.0.0.1" not in url and "localhost" not in url:
        pytest.skip(
            f"refusing to run DB-level tests against non-local URL: {url}"
        )
    try:
        client = supabase_mod.create_client(url, key)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"could not create supabase client: {exc}")
    try:
        client.table("ingest_delta_jobs").select("job_id").limit(1).execute()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"ingest_delta_jobs not reachable (migrations applied?): {exc}")
    return client


@pytest.fixture
def client() -> Any:
    return _require_local_supabase()


@pytest.fixture
def lock_target() -> str:
    # Unique per test run so parallel test processes don't collide on the
    # partial unique index.
    return f"test_{uuid.uuid4().hex[:12]}"


def _cleanup(client: Any, lock_target: str) -> None:
    try:
        client.table("ingest_delta_jobs").delete().eq("lock_target", lock_target).execute()
    except Exception:  # noqa: BLE001
        pass


def _insert_job(
    client: Any,
    *,
    lock_target: str,
    stage: str = "queued",
    job_id: str | None = None,
) -> str:
    jid = job_id or f"job_{uuid.uuid4().hex[:12]}"
    client.table("ingest_delta_jobs").insert(
        {
            "job_id": jid,
            "lock_target": lock_target,
            "stage": stage,
            "progress_pct": 0,
        }
    ).execute()
    return jid


# (1) First insert for a lock_target succeeds.
def test_first_live_insert_succeeds(client: Any, lock_target: str) -> None:
    try:
        job_id = _insert_job(client, lock_target=lock_target, stage="queued")
        assert job_id
    finally:
        _cleanup(client, lock_target)


# (2) Second live insert for the same lock_target raises (partial-unique-index).
def test_second_live_insert_is_rejected(client: Any, lock_target: str) -> None:
    try:
        _insert_job(client, lock_target=lock_target, stage="queued")
        with pytest.raises(Exception) as exc_info:
            _insert_job(client, lock_target=lock_target, stage="queued")
        # The error should mention the unique index by name.
        assert "idx_ingest_delta_jobs_live_target" in str(exc_info.value) \
            or "unique" in str(exc_info.value).lower()
    finally:
        _cleanup(client, lock_target)


# (3) Transitioning the first row to a terminal stage frees the slot.
def test_terminal_row_frees_slot(client: Any, lock_target: str) -> None:
    try:
        first = _insert_job(client, lock_target=lock_target, stage="queued")
        client.table("ingest_delta_jobs").update({"stage": "completed"}).eq(
            "job_id", first
        ).execute()
        # Now a second insert for the same lock_target should succeed.
        second = _insert_job(client, lock_target=lock_target, stage="queued")
        assert second != first
    finally:
        _cleanup(client, lock_target)


# (4) The heartbeat-reaper query pattern (documented for Phase 7) returns stalled
# rows. We insert a live row with an old heartbeat and assert the same filter
# the reaper will use (stage non-terminal AND last_heartbeat_at < cutoff) finds it.
def test_heartbeat_reaper_predicate_finds_stalled_row(
    client: Any, lock_target: str
) -> None:
    try:
        job_id = _insert_job(client, lock_target=lock_target, stage="parsing")
        # Backdate the heartbeat by 10 minutes (well past the 5-minute window).
        client.table("ingest_delta_jobs").update(
            {"last_heartbeat_at": "2026-01-01T00:00:00+00:00"}
        ).eq("job_id", job_id).execute()
        # Reaper predicate: non-terminal stage AND old heartbeat.
        resp = (
            client.table("ingest_delta_jobs")
            .select("job_id, stage, last_heartbeat_at")
            .eq("lock_target", lock_target)
            .neq("stage", "completed")
            .neq("stage", "failed")
            .neq("stage", "cancelled")
            .lt("last_heartbeat_at", "2026-04-01T00:00:00+00:00")
            .execute()
        )
        found = list(getattr(resp, "data", None) or [])
        assert len(found) == 1
        assert found[0]["job_id"] == job_id
    finally:
        _cleanup(client, lock_target)
