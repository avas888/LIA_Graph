-- fix_v10_may §9.3 — promote interpretation provider attribution from a
-- read-time markdown grep (interpretacion/catalog.py:55) to a
-- first-class column on documents.
--
-- Phase 10A retagged 2,275 chunks correctly by knowledge_class but kept
-- provider attribution (Crowe, EY, KPMG, …) read-time-derived from the
-- raw .md file. Phase 10B's Supabase retriever needs providers on the
-- row payload so the panel's "expert card" surface can build without
-- re-opening every markdown file on every chat turn.
--
-- Why a proper column instead of stuffing into concept_tags:
--   * concept_tags is intentionally a free-form tagging surface; mixing
--     provider names into it would corrupt the existing GIN index's
--     semantic shape and conflict with future tag-based filters.
--   * Provider attribution has a clean cardinality (one document → 0..N
--     providers) and tight semantics (author/publisher), unlike tags.
--   * Querying "all Crowe interpretations of Art. 124-2 ET" should be a
--     direct GIN-indexed lookup, not a substring scan over tags.
--
-- Backwards-compatible: column defaults to an empty array so existing
-- writers continue to function. Producers (manifest builder + sink) get
-- wired up in subsequent commits to populate the column.

ALTER TABLE "public"."documents"
    ADD COLUMN IF NOT EXISTS "provider_labels" "text"[]
    DEFAULT '{}'::"text"[]
    NOT NULL;

COMMENT ON COLUMN "public"."documents"."provider_labels" IS
    'Expert/author providers (e.g. {"Crowe","EY","KPMG"}). One row → 0..N. '
    'Empty for normative_base docs; populated for interpretative_guidance '
    'and select practica_erp docs. See fix_v10_may §3.D + §9.3.';

CREATE INDEX IF NOT EXISTS "idx_documents_provider_labels"
    ON "public"."documents" USING "gin" ("provider_labels");
