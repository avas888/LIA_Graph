-- Additive corpus ingestion v1 — Phase 1, job surface + lock RPCs.
--
-- Companion to 20260422000000_corpus_additive.sql. Lands:
--   * ingest_delta_jobs table (Decision J2 — the row IS the lock).
--   * idx_ingest_delta_jobs_live_target partial unique index (the lock).
--   * idx_ingest_delta_jobs_heartbeat (supports the janitor reaper).
--   * acquire_ingest_delta_lock(text) RPC — J1 hybrid helper for calls that
--     hold a Postgres transaction for their entire duration.
--   * promote_generation(target_gen text) RPC — Decision F1 skeleton.
--     Returns {"status":"not_implemented"} in Phase 1. Real body lands in
--     Phase 6 alongside the `make phase2-promote-snapshot` target.
--
-- Per §0.11, strictly additive: no drops, no ALTER COLUMN.

-- ---------------------------------------------------------------------------
-- ingest_delta_jobs — the row-level concurrency guard + UI job surface.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS "public"."ingest_delta_jobs" (
    "job_id"             TEXT PRIMARY KEY,
    "lock_target"        TEXT NOT NULL,
    "delta_id"           TEXT,
    "stage"              TEXT NOT NULL,
    "progress_pct"       INTEGER NOT NULL DEFAULT 0,
    "started_at"         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "last_heartbeat_at"  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "completed_at"       TIMESTAMPTZ,
    "created_by"         TEXT,
    "cancel_requested"   BOOLEAN NOT NULL DEFAULT false,
    "error_class"        TEXT,
    "error_message"      TEXT,
    "report_json"        JSONB,
    CONSTRAINT "ingest_delta_jobs_stage_check" CHECK (
        "stage" IN (
            'queued','preview','parsing','supabase','falkor','finalize',
            'completed','failed','cancelled'
        )
    )
);

ALTER TABLE "public"."ingest_delta_jobs" OWNER TO "postgres";

-- The lock: a second non-terminal row for the same lock_target cannot be
-- inserted. Terminal-stage rows are ignored so history accumulates freely.
CREATE UNIQUE INDEX IF NOT EXISTS "idx_ingest_delta_jobs_live_target"
    ON "public"."ingest_delta_jobs" ("lock_target")
    WHERE "stage" NOT IN ('completed','failed','cancelled');

-- Supports the heartbeat-reaper janitor (`make phase2-reap-stalled-jobs`).
CREATE INDEX IF NOT EXISTS "idx_ingest_delta_jobs_heartbeat"
    ON "public"."ingest_delta_jobs" ("last_heartbeat_at")
    WHERE "stage" NOT IN ('completed','failed','cancelled');

CREATE INDEX IF NOT EXISTS "idx_ingest_delta_jobs_started_at"
    ON "public"."ingest_delta_jobs" ("started_at" DESC);

GRANT ALL ON TABLE "public"."ingest_delta_jobs" TO "anon";
GRANT ALL ON TABLE "public"."ingest_delta_jobs" TO "authenticated";
GRANT ALL ON TABLE "public"."ingest_delta_jobs" TO "service_role";

-- ---------------------------------------------------------------------------
-- acquire_ingest_delta_lock — J1 helper (xact-scoped advisory lock).
-- ---------------------------------------------------------------------------
-- Callable only from inside another transaction (i.e. from another RPC body).
-- Returns true on success; false if the lock is currently held by another
-- transaction. The lock is released automatically at transaction end, so
-- this is NOT appropriate for long-running Python workers that span many
-- PostgREST HTTP calls (use the ingest_delta_jobs row as the lock for that
-- case — see §4 Decision J).

CREATE OR REPLACE FUNCTION "public"."acquire_ingest_delta_lock"(lock_target TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN pg_try_advisory_xact_lock(
        hashtext('gen_active_rolling:' || COALESCE(lock_target, ''))
    );
END;
$$;

GRANT EXECUTE ON FUNCTION "public"."acquire_ingest_delta_lock"(TEXT)
    TO "anon", "authenticated", "service_role";

-- ---------------------------------------------------------------------------
-- promote_generation — Decision F1 skeleton.
-- ---------------------------------------------------------------------------
-- Phase 1 ships the skeleton that refuses to act; Phase 6 replaces the body
-- with the real promotion logic (lock acquisition, is_active flip, row-count
-- diagnostics). Shipping the skeleton now means the route + migration surface
-- is final, so Phase 8's admin UI + Phase 6 Makefile target can bind to a
-- stable RPC name.

CREATE OR REPLACE FUNCTION "public"."promote_generation"(target_gen TEXT)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN jsonb_build_object(
        'status', 'not_implemented',
        'target_gen', target_gen,
        'message', 'promote_generation body lands in Phase 6. See docs/next/additive_corpusv1.md §5 Phase 6.'
    );
END;
$$;

GRANT EXECUTE ON FUNCTION "public"."promote_generation"(TEXT)
    TO "anon", "authenticated", "service_role";
