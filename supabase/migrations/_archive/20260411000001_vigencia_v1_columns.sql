-- vigencia v1.1 Phase 0 — additive audit-trail columns for validity tracking
-- Plan: docs/next/vigencia_v1.1.md §Phase 0
-- This migration is schema-only. No runtime code reads these columns yet.

-- Extend documents with audit-trail columns for vigencia state changes
ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS vigencia_basis     TEXT,
  ADD COLUMN IF NOT EXISTS vigencia_marked_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS vigencia_marked_by TEXT,
  ADD COLUMN IF NOT EXISTS vigencia_ruling_id TEXT;

-- Mirror onto chunks so retrieval can read without JOIN
ALTER TABLE document_chunks
  ADD COLUMN IF NOT EXISTS vigencia_basis     TEXT,
  ADD COLUMN IF NOT EXISTS vigencia_ruling_id TEXT;

-- New status values: 'suspendida' (suspended pending CC review),
-- 'parcial' (partially modified). 'desconocida' stays the default.
ALTER TYPE vigencia_status ADD VALUE IF NOT EXISTS 'suspendida';
ALTER TYPE vigencia_status ADD VALUE IF NOT EXISTS 'parcial';

-- Index for fast filtering by ruling
CREATE INDEX IF NOT EXISTS idx_documents_vigencia_ruling
  ON documents (vigencia_ruling_id) WHERE vigencia_ruling_id IS NOT NULL;
