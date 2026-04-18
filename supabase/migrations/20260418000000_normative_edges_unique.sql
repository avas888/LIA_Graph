-- Idempotency key for SupabaseCorpusSink.write_normative_edges upserts.
-- Every row the sink writes carries a generation_id, so duplicate sink runs
-- of the same generation can safely upsert on (source_key, target_key, relation, generation_id).

CREATE UNIQUE INDEX IF NOT EXISTS "normative_edges_idempotency"
    ON "public"."normative_edges" ("source_key", "target_key", "relation", "generation_id");
