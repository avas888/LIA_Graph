-- Migration: feedback satisfaction rating system
-- Adds question_text, answer_text, updated_at to feedback table.
-- Deduplicates existing rows and adds unique constraint on (trace_id, tenant_id)
-- for upsert behavior (re-rating updates instead of inserting duplicates).

-- Step 1: Add new columns
ALTER TABLE feedback
    ADD COLUMN IF NOT EXISTS question_text TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS answer_text   TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS updated_at    TIMESTAMPTZ NOT NULL DEFAULT now();

-- Step 2: Deduplicate existing rows — keep most recent per (trace_id, tenant_id)
DELETE FROM feedback a
USING feedback b
WHERE a.trace_id = b.trace_id
  AND a.tenant_id = b.tenant_id
  AND a.id <> b.id
  AND a.created_at < b.created_at;

-- Step 3: Unique constraint for upsert on (trace_id, tenant_id)
CREATE UNIQUE INDEX IF NOT EXISTS idx_feedback_trace_tenant_unique
    ON feedback (trace_id, tenant_id);

-- Step 4: Index for admin ratings listing (filter by rating, sort by date)
CREATE INDEX IF NOT EXISTS idx_feedback_rating_created
    ON feedback (rating, created_at DESC);

-- Step 5: Index for user filtering in admin view
CREATE INDEX IF NOT EXISTS idx_feedback_user_created
    ON feedback (user_id, created_at DESC);
