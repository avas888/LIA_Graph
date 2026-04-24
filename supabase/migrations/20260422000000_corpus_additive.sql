-- Additive corpus ingestion v1 — Phase 1 schema additions.
--
-- This migration is STRICTLY ADDITIVE per docs/next/additive_corpusv1.md §0.11
-- ("Do not drop or ALTER COLUMN existing documents / document_chunks /
-- normative_edges columns"). Every change below is ADD COLUMN, CREATE INDEX,
-- CREATE TABLE, or an INSERT … ON CONFLICT DO NOTHING seed row.
--
-- Together with 20260422000001_ingest_delta_jobs.sql this migration lands the
-- storage contracts required by Phases 2-8 of the additive plan:
--   * documents.doc_fingerprint + documents.last_delta_id + documents.retired_at
--   * normative_edges.last_seen_delta_id
--   * normative_edge_candidates_dangling (Decision D1, persistent dangling store)
--   * normative_edges_rolling_idempotency partial unique index, alongside
--     (not replacing) the pre-existing (source_key,target_key,relation,
--     generation_id) idempotency index.
--   * Reserved `gen_active_rolling` row in corpus_generations, seeded inactive.

-- ---------------------------------------------------------------------------
-- documents: additive columns for change detection + retirement.
-- ---------------------------------------------------------------------------

ALTER TABLE "public"."documents"
    ADD COLUMN IF NOT EXISTS "doc_fingerprint" TEXT,
    ADD COLUMN IF NOT EXISTS "last_delta_id" TEXT,
    ADD COLUMN IF NOT EXISTS "retired_at" TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS "idx_documents_doc_fingerprint"
    ON "public"."documents" ("doc_fingerprint")
    WHERE "doc_fingerprint" IS NOT NULL;

-- Partial index on the hot "not retired" path: every retriever + diagnostic
-- predicate we care about filters on retired_at IS NULL, so this keeps the
-- working set tight once retirements start landing.
CREATE INDEX IF NOT EXISTS "idx_documents_retired_at"
    ON "public"."documents" ("retired_at")
    WHERE "retired_at" IS NULL;

CREATE INDEX IF NOT EXISTS "idx_documents_last_delta"
    ON "public"."documents" ("last_delta_id")
    WHERE "last_delta_id" IS NOT NULL;

-- ---------------------------------------------------------------------------
-- normative_edges: per-edge delta attribution.
-- ---------------------------------------------------------------------------

ALTER TABLE "public"."normative_edges"
    ADD COLUMN IF NOT EXISTS "last_seen_delta_id" TEXT;

CREATE INDEX IF NOT EXISTS "idx_normative_edges_last_seen_delta"
    ON "public"."normative_edges" ("last_seen_delta_id")
    WHERE "last_seen_delta_id" IS NOT NULL;

-- Rolling-idempotency partial unique index. Coexists with the pre-existing
-- `normative_edges_idempotency` unique index on (source_key, target_key,
-- relation, generation_id) from 20260418000000_normative_edges_unique.sql.
-- Snapshot rebuilds keep using the compound-generation index; additive deltas
-- that write into gen_active_rolling get a tighter 3-column uniqueness guard.
CREATE UNIQUE INDEX IF NOT EXISTS "normative_edges_rolling_idempotency"
    ON "public"."normative_edges" ("source_key", "target_key", "relation")
    WHERE "generation_id" = 'gen_active_rolling';

-- ---------------------------------------------------------------------------
-- normative_edge_candidates_dangling (Decision D1).
-- ---------------------------------------------------------------------------
-- Candidates survive across deltas so that edges from old (unchanged) source
-- docs whose target ARTICLE keys arrive in a later delta get promoted into
-- `normative_edges` instead of being silently dropped by the current loader
-- behavior documented in §3.5.

CREATE TABLE IF NOT EXISTS "public"."normative_edge_candidates_dangling" (
    "source_key"           TEXT NOT NULL,
    "target_key"           TEXT NOT NULL,
    "relation"             TEXT NOT NULL,
    "source_doc_id"        TEXT,
    "first_seen_delta_id"  TEXT,
    "last_seen_delta_id"   TEXT,
    "raw_reference"        TEXT,
    "created_at"           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updated_at"           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("source_key", "target_key", "relation")
);

ALTER TABLE "public"."normative_edge_candidates_dangling"
    OWNER TO "postgres";

CREATE INDEX IF NOT EXISTS "idx_dangling_target_key"
    ON "public"."normative_edge_candidates_dangling" ("target_key");

CREATE INDEX IF NOT EXISTS "idx_dangling_last_seen_delta"
    ON "public"."normative_edge_candidates_dangling" ("last_seen_delta_id")
    WHERE "last_seen_delta_id" IS NOT NULL;

-- Keep updated_at in sync.
DROP TRIGGER IF EXISTS "trg_dangling_updated"
    ON "public"."normative_edge_candidates_dangling";
CREATE TRIGGER "trg_dangling_updated"
    BEFORE UPDATE ON "public"."normative_edge_candidates_dangling"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."update_updated_at_column"();

GRANT ALL ON TABLE "public"."normative_edge_candidates_dangling" TO "anon";
GRANT ALL ON TABLE "public"."normative_edge_candidates_dangling" TO "authenticated";
GRANT ALL ON TABLE "public"."normative_edge_candidates_dangling" TO "service_role";

-- ---------------------------------------------------------------------------
-- Reserved rolling-generation row (Decision A1).
-- ---------------------------------------------------------------------------
-- Seeded inactive. Additive deltas flip it active via the same path
-- `_activate_generation` uses today; snapshot promotion (Decision F1) flips
-- `is_active` between this row and a `gen_<UTC>` snapshot row without
-- rewriting the data.

INSERT INTO "public"."corpus_generations" (
    "generation_id",
    "is_active",
    "documents",
    "chunks",
    "countries",
    "files",
    "knowledge_class_counts",
    "index_dir",
    "created_at",
    "updated_at",
    "generated_at",
    "activated_at"
) VALUES (
    'gen_active_rolling',
    false,
    0,
    0,
    ARRAY['colombia']::text[],
    ARRAY[]::text[],
    '{}'::jsonb,
    '',
    NOW(),
    NOW(),
    NOW(),
    NOW()
)
ON CONFLICT ("generation_id") DO NOTHING;
