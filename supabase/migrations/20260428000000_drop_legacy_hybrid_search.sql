-- Drop the 14-arg `hybrid_search` overload left behind by the v5 §1.D
-- topic_boost migration (`20260427000000_topic_boost.sql`).
--
-- Background:
--   * `20260421000000_sub_topic_taxonomy.sql` created `hybrid_search` with
--     14 args (adds `filter_subtopic` + `subtopic_boost`).
--   * `20260427000000_topic_boost.sql` ran `CREATE OR REPLACE FUNCTION`
--     with 15 args (adds `filter_topic_boost`). Postgres identifies
--     functions by argument signature, so this created a NEW function
--     instead of replacing the old one.
--   * Both overloads now exist in cloud. PostgREST raises HTTP 500 with
--     "Could not choose the best candidate function between..." when a
--     caller's payload matches both signatures via DEFAULTs — which is
--     exactly what `pipeline_d/retriever_supabase._hybrid_search` does
--     when `filter_topic_boost` is omitted (no router_topic / boost == 1.0).
--
-- Surfaced by §1.G SME validation run 2026-04-26 evening: 15 of 36 SME
-- questions returned HTTP 500 with this exact ambiguity error. Heartbeat
-- probes happened to always include `filter_topic_boost` so they passed.
--
-- Fix: drop the 14-arg variant. The 15-arg variant is fully backward-
-- compatible (`filter_topic_boost DEFAULT 1.0` is a no-op when omitted),
-- so existing callers continue to work.
--
-- IDEMPOTENT — safe to replay.

DROP FUNCTION IF EXISTS "public"."hybrid_search"(
    "extensions"."vector",   -- query_embedding
    "text",                  -- query_text
    "text",                  -- filter_topic
    "text",                  -- filter_pais
    integer,                 -- match_count
    integer,                 -- rrf_k
    double precision,        -- fts_weight
    double precision,        -- semantic_weight
    "text",                  -- filter_knowledge_class
    "text",                  -- filter_sync_generation
    "text",                  -- fts_query
    "date",                  -- filter_effective_date_max
    "text",                  -- filter_subtopic
    double precision         -- subtopic_boost
);
