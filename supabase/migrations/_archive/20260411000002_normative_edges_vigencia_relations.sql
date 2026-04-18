-- vigencia v1.1 Phase 0 — extend normative_edges relation whitelist for vigencia
-- Plan: docs/next/vigencia_v1.1.md §Phase 0
--
-- IMPORTANT: Run this preflight SELECT manually against Supabase WIP BEFORE
-- applying the ADD CONSTRAINT below. If any rows return values not in the
-- new whitelist, decide row-by-row before continuing.
--
--   SELECT DISTINCT relation FROM normative_edges
--    WHERE relation NOT IN (
--      'references','modifies','complements','exception_for',
--      'derogates','supersedes','suspends','struck_down_by','revokes',
--      'cross_domain'
--    );
--
-- 2026-04-11 fix (ingestion_fixv1 Phase 0 promotion): the original whitelist
-- above omitted 'cross_domain', which is a documented, legitimate relation
-- value per src/lia_contador/vigencia_graph_query.py:47 ("cross_domain —
-- topic-level bridge (not a modification)") and cross_domain rows exist in
-- both WIP (from the intake _CROSS_DOMAIN_RELATIONS pipeline) and cloud
-- production. The preflight SELECT found 37 cross_domain rows in cloud. The
-- fix is additive: extend the whitelist, not delete the data.

-- Add CHECK constraint on the (currently unconstrained) relation column.
-- Migration 20260408000001 created `relation text NOT NULL DEFAULT 'references'`
-- with NO check constraint, so this is constraint-introducing, not constraint-replacing.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'normative_edges_relation_check'
  ) THEN
    ALTER TABLE normative_edges
      ADD CONSTRAINT normative_edges_relation_check
      CHECK (relation IN (
        'references','modifies','complements','exception_for',
        'derogates','supersedes','suspends','struck_down_by','revokes',
        'cross_domain'
      ));
  END IF;
END$$;

-- Optional metadata for vigencia edges (effective date of the change, basis text)
ALTER TABLE normative_edges
  ADD COLUMN IF NOT EXISTS effective_date DATE,
  ADD COLUMN IF NOT EXISTS basis_text     TEXT;
