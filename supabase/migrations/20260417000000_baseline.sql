


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


-- Required extensions (pre-squash: 20260309000001_enable_extensions.sql)
CREATE EXTENSION IF NOT EXISTS "vector"   SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS "unaccent" SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS "pg_trgm"  SCHEMA extensions;


CREATE SCHEMA IF NOT EXISTS "public";


ALTER SCHEMA "public" OWNER TO "pg_database_owner";


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE TYPE "public"."contribution_status" AS ENUM (
    'pending',
    'approved',
    'rejected'
);


ALTER TYPE "public"."contribution_status" OWNER TO "postgres";


CREATE TYPE "public"."curation_status" AS ENUM (
    'curated',
    'reviewed',
    'raw',
    'deprecated'
);


ALTER TYPE "public"."curation_status" OWNER TO "postgres";


CREATE TYPE "public"."feedback_tag" AS ENUM (
    'precisa',
    'practica',
    'incompleta',
    'desactualizada',
    'confusa'
);


ALTER TYPE "public"."feedback_tag" OWNER TO "postgres";


CREATE TYPE "public"."job_status" AS ENUM (
    'queued',
    'running',
    'completed',
    'failed',
    'cancelled'
);


ALTER TYPE "public"."job_status" OWNER TO "postgres";


CREATE TYPE "public"."platform_role" AS ENUM (
    'tenant_user',
    'tenant_admin',
    'platform_admin'
);


ALTER TYPE "public"."platform_role" OWNER TO "postgres";


CREATE TYPE "public"."review_vote" AS ENUM (
    'up',
    'down',
    'neutral'
);


ALTER TYPE "public"."review_vote" OWNER TO "postgres";


CREATE TYPE "public"."usage_event_type" AS ENUM (
    'turn_usage',
    'llm_usage',
    'admin_export',
    'background_job'
);


ALTER TYPE "public"."usage_event_type" OWNER TO "postgres";


CREATE TYPE "public"."vigencia_status" AS ENUM (
    'vigente',
    'derogada',
    'proyecto',
    'desconocida',
    'suspendida',
    'parcial'
);


ALTER TYPE "public"."vigencia_status" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."chunks_search_vector_trigger"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.search_vector := to_tsvector('spanish',
        coalesce(array_to_string(NEW.concept_tags, ' '), '') || ' ' ||
        coalesce(NEW.summary, '') || ' ' ||
        coalesce(NEW.chunk_text, '')
    );
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."chunks_search_vector_trigger"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."fts_scored_prefilter"("search_query" "text", "topic_list" "text"[], "country" "text" DEFAULT 'colombia'::"text", "result_limit" integer DEFAULT 4000, "filter_knowledge_class" "text" DEFAULT NULL::"text", "filter_sync_generation" "text" DEFAULT NULL::"text", "fts_query" "text" DEFAULT NULL::"text", "filter_effective_date_max" "date" DEFAULT NULL::"date") RETURNS TABLE("doc_id" "text", "chunk_id" "text", "chunk_text" "text", "summary" "text", "concept_tags" "text"[], "chunk_start" integer, "chunk_end" integer, "source_type" "text", "curation_status" "text", "topic" "text", "pais" "text", "authority" "text", "vigencia" "text", "retrieval_visibility" "text", "lane_scores" "jsonb", "relative_path" "text", "tema" "text", "subtema" "text", "tipo_de_documento" "text", "tipo_de_consulta" "text", "tipo_de_accion" "text", "tipo_de_riesgo" "text", "trust_tier" "text", "source_origin" "text", "nivel_practicidad" "text", "knowledge_class" "text", "chunk_section_type" "text", "fts_rank" real)
    LANGUAGE "plpgsql" STABLE
    AS $$
DECLARE
    fts_count INTEGER;
    pad_limit INTEGER;
    effective_tsq tsquery;
BEGIN
    IF fts_query IS NOT NULL AND fts_query <> '' THEN
        effective_tsq := to_tsquery('spanish', fts_query);
    ELSE
        effective_tsq := plainto_tsquery('spanish', search_query);
    END IF;

    RETURN QUERY
    SELECT
        dc.doc_id,
        dc.chunk_id,
        dc.chunk_text,
        dc.summary,
        dc.concept_tags,
        dc.chunk_start,
        dc.chunk_end,
        dc.source_type,
        dc.curation_status,
        dc.topic,
        dc.pais,
        dc.authority,
        dc.vigencia,
        dc.retrieval_visibility,
        dc.lane_scores,
        dc.relative_path,
        dc.tema,
        dc.subtema,
        dc.tipo_de_documento,
        dc.tipo_de_consulta,
        dc.tipo_de_accion,
        dc.tipo_de_riesgo,
        dc.trust_tier,
        dc.source_origin,
        dc.nivel_practicidad,
        dc.knowledge_class,
        dc.chunk_section_type,
        ts_rank_cd(dc.search_vector, effective_tsq)::REAL AS fts_rank
    FROM document_chunks dc
    WHERE dc.search_vector @@ effective_tsq
      AND (array_length(topic_list, 1) IS NULL OR dc.topic = ANY(topic_list))
      AND dc.pais = country
      AND (
          filter_effective_date_max IS NOT NULL
          OR COALESCE(dc.vigencia, '') NOT IN ('derogada', 'proyecto', 'suspendida')
      )
      AND COALESCE(dc.retrieval_visibility, '') <> 'backstage_only'
      AND (filter_knowledge_class IS NULL OR dc.knowledge_class = filter_knowledge_class)
      AND (filter_sync_generation IS NULL OR dc.sync_generation = filter_sync_generation)
      AND (filter_effective_date_max IS NULL
           OR dc.effective_date IS NULL
           OR dc.effective_date <= filter_effective_date_max)
    ORDER BY ts_rank_cd(dc.search_vector, effective_tsq) DESC
    LIMIT result_limit;

    GET DIAGNOSTICS fts_count = ROW_COUNT;

    IF fts_count < (result_limit / 2) THEN
        pad_limit := result_limit - fts_count;
        RETURN QUERY
        SELECT
            dc.doc_id,
            dc.chunk_id,
            dc.chunk_text,
            dc.summary,
            dc.concept_tags,
            dc.chunk_start,
            dc.chunk_end,
            dc.source_type,
            dc.curation_status,
            dc.topic,
            dc.pais,
            dc.authority,
            dc.vigencia,
            dc.retrieval_visibility,
            dc.lane_scores,
            dc.relative_path,
            dc.tema,
            dc.subtema,
            dc.tipo_de_documento,
            dc.tipo_de_consulta,
            dc.tipo_de_accion,
            dc.tipo_de_riesgo,
            dc.trust_tier,
            dc.source_origin,
            dc.nivel_practicidad,
            dc.knowledge_class,
            dc.chunk_section_type,
            0.0::REAL AS fts_rank
        FROM document_chunks dc
        WHERE (array_length(topic_list, 1) IS NULL OR dc.topic = ANY(topic_list))
          AND dc.pais = country
          AND (
              filter_effective_date_max IS NOT NULL
              OR COALESCE(dc.vigencia, '') NOT IN ('derogada', 'proyecto', 'suspendida')
          )
          AND COALESCE(dc.retrieval_visibility, '') <> 'backstage_only'
          AND (filter_knowledge_class IS NULL OR dc.knowledge_class = filter_knowledge_class)
          AND (filter_sync_generation IS NULL OR dc.sync_generation = filter_sync_generation)
          AND (filter_effective_date_max IS NULL
               OR dc.effective_date IS NULL
               OR dc.effective_date <= filter_effective_date_max)
          AND NOT dc.search_vector @@ effective_tsq
        ORDER BY
            CASE dc.trust_tier
                WHEN 'tier_1' THEN 1
                WHEN 'tier_2' THEN 2
                WHEN 'tier_3' THEN 3
                ELSE 4
            END,
            dc.created_at DESC
        LIMIT pad_limit;
    END IF;
END;
$$;


ALTER FUNCTION "public"."fts_scored_prefilter"("search_query" "text", "topic_list" "text"[], "country" "text", "result_limit" integer, "filter_knowledge_class" "text", "filter_sync_generation" "text", "fts_query" "text", "filter_effective_date_max" "date") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."hybrid_search"("query_embedding" "extensions"."vector", "query_text" "text", "filter_topic" "text" DEFAULT NULL::"text", "filter_pais" "text" DEFAULT NULL::"text", "match_count" integer DEFAULT 100, "rrf_k" integer DEFAULT 60, "fts_weight" double precision DEFAULT 1.0, "semantic_weight" double precision DEFAULT 1.0, "filter_knowledge_class" "text" DEFAULT NULL::"text", "filter_sync_generation" "text" DEFAULT NULL::"text", "fts_query" "text" DEFAULT NULL::"text", "filter_effective_date_max" "date" DEFAULT NULL::"date") RETURNS TABLE("doc_id" "text", "chunk_id" "text", "chunk_text" "text", "summary" "text", "concept_tags" "text"[], "chunk_start" integer, "chunk_end" integer, "source_type" "text", "curation_status" "text", "topic" "text", "pais" "text", "authority" "text", "vigencia" "text", "retrieval_visibility" "text", "lane_scores" "jsonb", "relative_path" "text", "tema" "text", "subtema" "text", "tipo_de_documento" "text", "tipo_de_consulta" "text", "tipo_de_accion" "text", "tipo_de_riesgo" "text", "trust_tier" "text", "source_origin" "text", "nivel_practicidad" "text", "knowledge_class" "text", "chunk_section_type" "text", "fts_rank" double precision, "vector_similarity" double precision, "rrf_score" double precision)
    LANGUAGE "plpgsql" STABLE
    AS $$
DECLARE
    effective_tsq tsquery;
BEGIN
    IF fts_query IS NOT NULL AND fts_query <> '' THEN
        effective_tsq := to_tsquery('spanish', fts_query);
    ELSE
        effective_tsq := plainto_tsquery('spanish', query_text);
    END IF;

    RETURN QUERY
    WITH fts AS (
        SELECT
            dc.id AS chunk_pk,
            dc.doc_id,
            dc.chunk_id,
            dc.chunk_text,
            dc.summary,
            dc.concept_tags,
            dc.chunk_start,
            dc.chunk_end,
            dc.source_type,
            dc.curation_status,
            dc.topic,
            dc.pais,
            dc.authority,
            dc.vigencia,
            dc.retrieval_visibility,
            dc.lane_scores,
            dc.relative_path,
            dc.tema,
            dc.subtema,
            dc.tipo_de_documento,
            dc.tipo_de_consulta,
            dc.tipo_de_accion,
            dc.tipo_de_riesgo,
            dc.trust_tier,
            dc.source_origin,
            dc.nivel_practicidad,
            dc.knowledge_class,
            dc.chunk_section_type,
            ts_rank_cd(dc.search_vector, effective_tsq) AS rank,
            ROW_NUMBER() OVER (ORDER BY ts_rank_cd(dc.search_vector, effective_tsq) DESC) AS rn
        FROM document_chunks dc
        WHERE dc.search_vector @@ effective_tsq
          AND (filter_topic IS NULL OR dc.topic IN (filter_topic, filter_topic || '_parametros'))
          AND (filter_pais IS NULL OR dc.pais = filter_pais)
          AND (filter_knowledge_class IS NULL OR dc.knowledge_class = filter_knowledge_class)
          AND (filter_sync_generation IS NULL OR dc.sync_generation = filter_sync_generation)
          AND (
              filter_effective_date_max IS NOT NULL
              OR COALESCE(dc.vigencia, '') NOT IN ('derogada', 'proyecto', 'suspendida')
          )
          AND COALESCE(dc.retrieval_visibility, '') <> 'backstage_only'
          AND (filter_effective_date_max IS NULL
               OR dc.effective_date IS NULL
               OR dc.effective_date <= filter_effective_date_max)
        ORDER BY rank DESC
        LIMIT match_count
    ),
    semantic AS (
        SELECT
            dc.id AS chunk_pk,
            dc.doc_id,
            dc.chunk_id,
            dc.chunk_text,
            dc.summary,
            dc.concept_tags,
            dc.chunk_start,
            dc.chunk_end,
            dc.source_type,
            dc.curation_status,
            dc.topic,
            dc.pais,
            dc.authority,
            dc.vigencia,
            dc.retrieval_visibility,
            dc.lane_scores,
            dc.relative_path,
            dc.tema,
            dc.subtema,
            dc.tipo_de_documento,
            dc.tipo_de_consulta,
            dc.tipo_de_accion,
            dc.tipo_de_riesgo,
            dc.trust_tier,
            dc.source_origin,
            dc.nivel_practicidad,
            dc.knowledge_class,
            dc.chunk_section_type,
            1.0 - (dc.embedding <=> query_embedding) AS similarity,
            ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding) AS rn
        FROM document_chunks dc
        WHERE dc.embedding IS NOT NULL
          AND (filter_topic IS NULL OR dc.topic IN (filter_topic, filter_topic || '_parametros'))
          AND (filter_pais IS NULL OR dc.pais = filter_pais)
          AND (filter_knowledge_class IS NULL OR dc.knowledge_class = filter_knowledge_class)
          AND (filter_sync_generation IS NULL OR dc.sync_generation = filter_sync_generation)
          AND (
              filter_effective_date_max IS NOT NULL
              OR COALESCE(dc.vigencia, '') NOT IN ('derogada', 'proyecto', 'suspendida')
          )
          AND COALESCE(dc.retrieval_visibility, '') <> 'backstage_only'
          AND (filter_effective_date_max IS NULL
               OR dc.effective_date IS NULL
               OR dc.effective_date <= filter_effective_date_max)
        ORDER BY dc.embedding <=> query_embedding
        LIMIT match_count
    ),
    combined AS (
        SELECT
            COALESCE(f.chunk_pk, s.chunk_pk) AS chunk_pk,
            COALESCE(f.doc_id, s.doc_id) AS doc_id,
            COALESCE(f.chunk_id, s.chunk_id) AS chunk_id,
            COALESCE(f.chunk_text, s.chunk_text) AS chunk_text,
            COALESCE(f.summary, s.summary) AS summary,
            COALESCE(f.concept_tags, s.concept_tags) AS concept_tags,
            COALESCE(f.chunk_start, s.chunk_start) AS chunk_start,
            COALESCE(f.chunk_end, s.chunk_end) AS chunk_end,
            COALESCE(f.source_type, s.source_type) AS source_type,
            COALESCE(f.curation_status, s.curation_status) AS curation_status,
            COALESCE(f.topic, s.topic) AS topic,
            COALESCE(f.pais, s.pais) AS pais,
            COALESCE(f.authority, s.authority) AS authority,
            COALESCE(f.vigencia, s.vigencia) AS vigencia,
            COALESCE(f.retrieval_visibility, s.retrieval_visibility) AS retrieval_visibility,
            COALESCE(f.lane_scores, s.lane_scores) AS lane_scores,
            COALESCE(f.relative_path, s.relative_path) AS relative_path,
            COALESCE(f.tema, s.tema) AS tema,
            COALESCE(f.subtema, s.subtema) AS subtema,
            COALESCE(f.tipo_de_documento, s.tipo_de_documento) AS tipo_de_documento,
            COALESCE(f.tipo_de_consulta, s.tipo_de_consulta) AS tipo_de_consulta,
            COALESCE(f.tipo_de_accion, s.tipo_de_accion) AS tipo_de_accion,
            COALESCE(f.tipo_de_riesgo, s.tipo_de_riesgo) AS tipo_de_riesgo,
            COALESCE(f.trust_tier, s.trust_tier) AS trust_tier,
            COALESCE(f.source_origin, s.source_origin) AS source_origin,
            COALESCE(f.nivel_practicidad, s.nivel_practicidad) AS nivel_practicidad,
            COALESCE(f.knowledge_class, s.knowledge_class) AS knowledge_class,
            COALESCE(f.chunk_section_type, s.chunk_section_type) AS chunk_section_type,
            COALESCE(f.rank, 0.0) AS fts_rank,
            COALESCE(s.similarity, 0.0) AS vector_similarity,
            (
                fts_weight / (rrf_k + COALESCE(f.rn, match_count + 1))
                + semantic_weight / (rrf_k + COALESCE(s.rn, match_count + 1))
            ) AS rrf_score
        FROM fts f
        FULL OUTER JOIN semantic s ON f.chunk_pk = s.chunk_pk
    )
    SELECT
        c.doc_id,
        c.chunk_id,
        c.chunk_text,
        c.summary,
        c.concept_tags,
        c.chunk_start,
        c.chunk_end,
        c.source_type,
        c.curation_status,
        c.topic,
        c.pais,
        c.authority,
        c.vigencia,
        c.retrieval_visibility,
        c.lane_scores,
        c.relative_path,
        c.tema,
        c.subtema,
        c.tipo_de_documento,
        c.tipo_de_consulta,
        c.tipo_de_accion,
        c.tipo_de_riesgo,
        c.trust_tier,
        c.source_origin,
        c.nivel_practicidad,
        c.knowledge_class,
        c.chunk_section_type,
        c.fts_rank::float,
        c.vector_similarity::float,
        c.rrf_score::float
    FROM combined c
    ORDER BY c.rrf_score DESC
    LIMIT match_count;
END;
$$;


ALTER FUNCTION "public"."hybrid_search"("query_embedding" "extensions"."vector", "query_text" "text", "filter_topic" "text", "filter_pais" "text", "match_count" integer, "rrf_k" integer, "fts_weight" double precision, "semantic_weight" double precision, "filter_knowledge_class" "text", "filter_sync_generation" "text", "fts_query" "text", "filter_effective_date_max" "date") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."requesting_tenant_id"() RETURNS "text"
    LANGUAGE "plpgsql" STABLE
    AS $$
DECLARE
  raw TEXT;
BEGIN
  raw := current_setting('request.jwt.claims', true);
  IF raw IS NULL OR raw = '' THEN
    RETURN '';
  END IF;
  RETURN COALESCE(raw::json ->> 'tenant_id', '');
EXCEPTION WHEN OTHERS THEN
  RETURN '';
END;
$$;


ALTER FUNCTION "public"."requesting_tenant_id"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_updated_at_column"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."auth_nonces" (
    "nonce_key" "text" NOT NULL,
    "nonce_id" "text" NOT NULL,
    "nonce_type" "text" DEFAULT 'host_grant'::"text" NOT NULL,
    "expires_at" timestamp with time zone NOT NULL,
    "consumed_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."auth_nonces" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."chat_run_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "chat_run_id" "text" NOT NULL,
    "event_index" integer NOT NULL,
    "event_payload" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."chat_run_events" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."chat_runs" (
    "chat_run_id" "text" NOT NULL,
    "trace_id" "text" DEFAULT ''::"text" NOT NULL,
    "session_id" "text" DEFAULT ''::"text" NOT NULL,
    "client_turn_id" "text" DEFAULT ''::"text" NOT NULL,
    "request_fingerprint" "text" NOT NULL,
    "endpoint" "text" DEFAULT '/api/chat'::"text" NOT NULL,
    "tenant_id" "text",
    "user_id" "text",
    "company_id" "text",
    "status" "text" DEFAULT 'running'::"text" NOT NULL,
    "pipeline_run_id" "text",
    "request_payload" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "response_payload" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "error_payload" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "request_received_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "pipeline_started_at" timestamp with time zone,
    "first_model_delta_at" timestamp with time zone,
    "first_visible_answer_at" timestamp with time zone,
    "pipeline_completed_at" timestamp with time zone,
    "final_payload_ready_at" timestamp with time zone,
    "response_sent_at" timestamp with time zone,
    "async_persistence_done_at" timestamp with time zone,
    "completed_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."chat_runs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."chat_session_metrics" (
    "session_id" "text" NOT NULL,
    "turn_count" integer DEFAULT 0 NOT NULL,
    "token_usage_total" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "llm_token_usage_total" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "last_trace_id" "text",
    "last_run_id" "text",
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."chat_session_metrics" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."citation_gap_registry" (
    "reference_key" "text" NOT NULL,
    "reference_text" "text" DEFAULT ''::"text" NOT NULL,
    "reference_type" "text" DEFAULT ''::"text" NOT NULL,
    "seen_count_total" integer DEFAULT 0 NOT NULL,
    "seen_count_user" integer DEFAULT 0 NOT NULL,
    "seen_count_assistant" integer DEFAULT 0 NOT NULL,
    "first_seen_at" timestamp with time zone,
    "last_seen_at" timestamp with time zone,
    "last_trace_id" "text",
    "last_session_id" "text",
    "last_topic" "text",
    "last_pais" "text",
    "samples" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."citation_gap_registry" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."clarification_sessions" (
    "session_id" "text" NOT NULL,
    "state" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "expires_at" timestamp with time zone DEFAULT ("now"() + '02:00:00'::interval) NOT NULL
);


ALTER TABLE "public"."clarification_sessions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."companies" (
    "company_id" "text" NOT NULL,
    "tenant_id" "text" NOT NULL,
    "display_name" "text" NOT NULL,
    "pais" "text" DEFAULT 'colombia'::"text" NOT NULL,
    "status" "text" DEFAULT 'active'::"text" NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."companies" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."contributions" (
    "contribution_id" "text" NOT NULL,
    "topic" "text" NOT NULL,
    "content_markdown" "text" NOT NULL,
    "authority_claim" "text" NOT NULL,
    "submitter_id" "text" NOT NULL,
    "tenant_id" "text" NOT NULL,
    "status" "public"."contribution_status" DEFAULT 'pending'::"public"."contribution_status" NOT NULL,
    "review_comment" "text" DEFAULT ''::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "reviewed_at" timestamp with time zone
);


ALTER TABLE "public"."contributions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."conversation_turns" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "conversation_id" "uuid" NOT NULL,
    "role" "text" NOT NULL,
    "content" "text" NOT NULL,
    "layer_contributions" "jsonb",
    "trace_id" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "turn_metadata" "jsonb"
);


ALTER TABLE "public"."conversation_turns" OWNER TO "postgres";


COMMENT ON COLUMN "public"."conversation_turns"."turn_metadata" IS 'Per-turn enrichment: citations, normative support context, topic routing, confidence. Nullable for pre-existing turns.';



CREATE TABLE IF NOT EXISTS "public"."conversations" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "session_id" "text" NOT NULL,
    "tenant_id" "text" NOT NULL,
    "accountant_id" "text" NOT NULL,
    "topic" "text",
    "pais" "text" DEFAULT 'colombia'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "user_id" "text" DEFAULT ''::"text" NOT NULL,
    "company_id" "text" DEFAULT ''::"text" NOT NULL,
    "integration_id" "text" DEFAULT ''::"text" NOT NULL,
    "host_session_id" "text" DEFAULT ''::"text" NOT NULL,
    "channel" "text" DEFAULT 'chat'::"text" NOT NULL,
    "status" "text" DEFAULT 'active'::"text" NOT NULL,
    "memory_summary" "text" DEFAULT ''::"text" NOT NULL
);


ALTER TABLE "public"."conversations" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."conversation_summaries" AS
 SELECT "c"."id",
    "c"."session_id",
    "c"."tenant_id",
    "c"."accountant_id",
    "c"."topic",
    "c"."pais",
    "c"."user_id",
    "c"."company_id",
    "c"."integration_id",
    "c"."host_session_id",
    "c"."channel",
    "c"."status",
    "c"."memory_summary",
    "c"."created_at",
    "c"."updated_at",
    COALESCE("agg"."turn_count", 0) AS "turn_count",
    COALESCE("agg"."first_question", ''::"text") AS "first_question"
   FROM ("public"."conversations" "c"
     LEFT JOIN LATERAL ( SELECT ("count"(*))::integer AS "turn_count",
            ( SELECT SUBSTRING("ct2"."content" FROM 1 FOR 120) AS "substring"
                   FROM "public"."conversation_turns" "ct2"
                  WHERE (("ct2"."conversation_id" = "c"."id") AND ("ct2"."role" = 'user'::"text") AND ("ct2"."content" <> ''::"text"))
                  ORDER BY "ct2"."created_at"
                 LIMIT 1) AS "first_question"
           FROM "public"."conversation_turns" "ct"
          WHERE ("ct"."conversation_id" = "c"."id")) "agg" ON (true));


ALTER VIEW "public"."conversation_summaries" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."corpus_generations" (
    "generation_id" "text" NOT NULL,
    "generated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "activated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "documents" integer DEFAULT 0 NOT NULL,
    "chunks" integer DEFAULT 0 NOT NULL,
    "countries" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "files" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "knowledge_class_counts" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "index_dir" "text" DEFAULT ''::"text" NOT NULL,
    "is_active" boolean DEFAULT false NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."corpus_generations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."doc_utility_scores" (
    "doc_id" "text" NOT NULL,
    "use_count" integer DEFAULT 0 NOT NULL,
    "rating_sum" integer DEFAULT 0 NOT NULL,
    "rating_count" integer DEFAULT 0 NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."doc_utility_scores" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."document_chunks" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "doc_id" "text" NOT NULL,
    "chunk_id" "text",
    "chunk_text" "text" NOT NULL,
    "summary" "text",
    "concept_tags" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "chunk_start" integer,
    "chunk_end" integer,
    "chunk_sha256" "text",
    "source_type" "text",
    "curation_status" "text",
    "topic" "text",
    "pais" "text" DEFAULT 'colombia'::"text",
    "authority" "text",
    "vigencia" "text",
    "retrieval_visibility" "text",
    "lane_scores" "jsonb",
    "search_vector" "tsvector",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "embedding" "extensions"."vector"(768),
    "relative_path" "text",
    "tema" "text",
    "subtema" "text",
    "tipo_de_documento" "text",
    "tipo_de_consulta" "text",
    "tipo_de_accion" "text",
    "tipo_de_riesgo" "text",
    "trust_tier" "text",
    "source_origin" "text",
    "nivel_practicidad" "text",
    "knowledge_class" "text",
    "sync_generation" "text",
    "publish_date" "date",
    "effective_date" "date",
    "chunk_section_type" "text",
    "vigencia_basis" "text",
    "vigencia_ruling_id" "text"
);


ALTER TABLE "public"."document_chunks" OWNER TO "postgres";


COMMENT ON COLUMN "public"."document_chunks"."chunk_section_type" IS 'Section type derived from markdown ## headings during ingestion: vigente, historical, operational, metadata, general';



CREATE TABLE IF NOT EXISTS "public"."documents" (
    "doc_id" "text" NOT NULL,
    "relative_path" "text" NOT NULL,
    "source_type" "text" DEFAULT 'unknown'::"text" NOT NULL,
    "topic" "text" DEFAULT 'unknown'::"text" NOT NULL,
    "authority" "text" DEFAULT 'unknown'::"text" NOT NULL,
    "pais" "text" DEFAULT 'colombia'::"text" NOT NULL,
    "locale" "text" DEFAULT 'es-CO'::"text",
    "knowledge_class" "text",
    "jurisdiccion" "text",
    "tema" "text",
    "subtema" "text",
    "tipo_de_accion" "text",
    "tipo_de_riesgo" "text",
    "tipo_de_documento" "text",
    "nivel_practicidad" "text",
    "vigencia" "public"."vigencia_status" DEFAULT 'desconocida'::"public"."vigencia_status",
    "autoridad" "text",
    "publish_date" "text",
    "effective_date" "text",
    "status" "text",
    "review_cadence" "text",
    "superseded_by" "text",
    "curation_status" "public"."curation_status",
    "entity_id" "text",
    "entity_type" "text",
    "relation_type" "text",
    "reference_identity_keys" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "mentioned_reference_keys" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "concept_tags" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "normative_refs" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "topic_domains" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "admissible_surfaces" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "supports_fields" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "storage_partition" "text",
    "url" "text",
    "notes" "text",
    "cross_topic" boolean DEFAULT false NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "sync_generation" "text",
    "applicability_kind" "text",
    "ag_from_year" integer,
    "ag_to_year" integer,
    "filing_from_year" integer,
    "filing_to_year" integer,
    "corpus" "text",
    "content_hash" "text",
    "filename_normalized" "text",
    "first_heading" "text",
    "vigencia_basis" "text",
    "vigencia_marked_at" timestamp with time zone,
    "vigencia_marked_by" "text",
    "vigencia_ruling_id" "text"
);


ALTER TABLE "public"."documents" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."eval_diagnoses" (
    "eval_diagnosis_id" "text" NOT NULL,
    "eval_run_id" "text" NOT NULL,
    "eval_turn_id" "text",
    "diagnoser" "text" DEFAULT ''::"text" NOT NULL,
    "category" "text" DEFAULT ''::"text" NOT NULL,
    "severity" "text" DEFAULT 'medium'::"text" NOT NULL,
    "title" "text" DEFAULT ''::"text" NOT NULL,
    "description" "text" DEFAULT ''::"text" NOT NULL,
    "affected_stages" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "recommendation" "text" DEFAULT ''::"text" NOT NULL,
    "evidence" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."eval_diagnoses" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."eval_rankings" (
    "eval_ranking_id" "text" NOT NULL,
    "eval_run_id" "text" NOT NULL,
    "question_id" "text" DEFAULT ''::"text" NOT NULL,
    "ranker" "text" DEFAULT ''::"text" NOT NULL,
    "candidates" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "criteria" "text" DEFAULT ''::"text" NOT NULL,
    "rationale" "text" DEFAULT ''::"text" NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."eval_rankings" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."eval_reviews" (
    "eval_review_id" "text" NOT NULL,
    "eval_turn_id" "text" NOT NULL,
    "eval_run_id" "text" NOT NULL,
    "reviewer" "text" DEFAULT ''::"text" NOT NULL,
    "scores" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "overall_score" double precision,
    "verdict" "text" DEFAULT ''::"text" NOT NULL,
    "flags" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "comment" "text" DEFAULT ''::"text" NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."eval_reviews" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."eval_runs" (
    "eval_run_id" "text" NOT NULL,
    "tenant_id" "text" NOT NULL,
    "label" "text" NOT NULL,
    "description" "text" DEFAULT ''::"text" NOT NULL,
    "dataset_id" "text" DEFAULT ''::"text" NOT NULL,
    "status" "text" DEFAULT 'created'::"text" NOT NULL,
    "config" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "tags" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "stats" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_by" "text" DEFAULT ''::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "completed_at" timestamp with time zone
);


ALTER TABLE "public"."eval_runs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."eval_turns" (
    "eval_turn_id" "text" NOT NULL,
    "eval_run_id" "text" NOT NULL,
    "question_id" "text" DEFAULT ''::"text" NOT NULL,
    "message" "text" NOT NULL,
    "topic" "text" DEFAULT ''::"text" NOT NULL,
    "pais" "text" DEFAULT 'colombia'::"text" NOT NULL,
    "config" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "pipeline_run_id" "text",
    "response" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "retrieval_trace" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "retrieval_trace_summary" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "error" "text" DEFAULT ''::"text" NOT NULL,
    "latency_ms" double precision,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "completed_at" timestamp with time zone
);


ALTER TABLE "public"."eval_turns" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."expert_summary_overrides" (
    "override_key" "text" NOT NULL,
    "logical_doc_id" "text" NOT NULL,
    "provider_name" "text" NOT NULL,
    "source_hash" "text" NOT NULL,
    "summary_text" "text" NOT NULL,
    "summary_origin" "text" DEFAULT 'llm'::"text" NOT NULL,
    "summary_quality" "text" DEFAULT 'high'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."expert_summary_overrides" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."feedback" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "trace_id" "text" NOT NULL,
    "session_id" "text",
    "rating" integer NOT NULL,
    "tags" "public"."feedback_tag"[] DEFAULT '{}'::"public"."feedback_tag"[] NOT NULL,
    "comment" "text" DEFAULT ''::"text" NOT NULL,
    "docs_used" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "layer_contributions" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "pain_detected" "text" DEFAULT ''::"text" NOT NULL,
    "task_detected" "text" DEFAULT ''::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "tenant_id" "text" DEFAULT ''::"text" NOT NULL,
    "user_id" "text" DEFAULT ''::"text" NOT NULL,
    "company_id" "text" DEFAULT ''::"text" NOT NULL,
    "integration_id" "text" DEFAULT ''::"text" NOT NULL,
    "vote" "public"."review_vote" DEFAULT 'neutral'::"public"."review_vote" NOT NULL,
    "review_status" "text" DEFAULT 'submitted'::"text" NOT NULL,
    "source" "text" DEFAULT 'api'::"text" NOT NULL,
    "created_by" "text" DEFAULT ''::"text" NOT NULL,
    "question_text" "text" DEFAULT ''::"text" NOT NULL,
    "answer_text" "text" DEFAULT ''::"text" NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "feedback_rating_check" CHECK ((("rating" >= 1) AND ("rating" <= 5)))
);


ALTER TABLE "public"."feedback" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."form_guides" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "reference_key" "text" NOT NULL,
    "form_version" "text",
    "profile_id" "text",
    "title" "text",
    "description" "text",
    "guide_data" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."form_guides" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."form_hotspots" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "guide_id" "uuid" NOT NULL,
    "casilla" "text" NOT NULL,
    "field_name" "text",
    "bbox_x" real,
    "bbox_y" real,
    "bbox_w" real,
    "bbox_h" real,
    "page_number" integer,
    "tooltip" "text",
    "help_text" "text",
    "validation_rule" "text",
    "data_type" "text",
    "required" boolean DEFAULT false NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."form_hotspots" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."host_integrations" (
    "integration_id" "text" NOT NULL,
    "tenant_id" "text",
    "label" "text" NOT NULL,
    "allowed_origins" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "secret_env" "text" DEFAULT ''::"text" NOT NULL,
    "status" "text" DEFAULT 'active'::"text" NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."host_integrations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."integration_secrets" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "integration_id" "text" NOT NULL,
    "key_version" "text" DEFAULT 'v1'::"text" NOT NULL,
    "secret_hint" "text" DEFAULT ''::"text" NOT NULL,
    "active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "rotated_at" timestamp with time zone
);


ALTER TABLE "public"."integration_secrets" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."invite_tokens" (
    "token_id" "text" NOT NULL,
    "tenant_id" "text" NOT NULL,
    "email" "text" DEFAULT ''::"text" NOT NULL,
    "role" "public"."platform_role" DEFAULT 'tenant_user'::"public"."platform_role" NOT NULL,
    "invited_by" "text" DEFAULT ''::"text" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "expires_at" timestamp with time zone NOT NULL,
    "accepted_at" timestamp with time zone,
    "accepted_by" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."invite_tokens" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."job_runs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "job_id" "text" NOT NULL,
    "status" "public"."job_status" DEFAULT 'queued'::"public"."job_status" NOT NULL,
    "payload" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "error" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."job_runs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."jobs" (
    "job_id" "text" NOT NULL,
    "job_type" "text" NOT NULL,
    "status" "public"."job_status" DEFAULT 'queued'::"public"."job_status" NOT NULL,
    "tenant_id" "text" DEFAULT ''::"text" NOT NULL,
    "user_id" "text" DEFAULT ''::"text" NOT NULL,
    "company_id" "text" DEFAULT ''::"text" NOT NULL,
    "request_payload" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "result_payload" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "error" "text" DEFAULT ''::"text" NOT NULL,
    "attempts" integer DEFAULT 0 NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "completed_at" timestamp with time zone
);


ALTER TABLE "public"."jobs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."login_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "text",
    "email" "text" NOT NULL,
    "tenant_id" "text",
    "status" "text" DEFAULT 'success'::"text" NOT NULL,
    "failure_reason" "text",
    "ip_address" "text" DEFAULT ''::"text" NOT NULL,
    "user_agent" "text" DEFAULT ''::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."login_events" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."normative_edges" (
    "id" bigint NOT NULL,
    "source_key" "text" NOT NULL,
    "target_key" "text" NOT NULL,
    "relation" "text" DEFAULT 'references'::"text" NOT NULL,
    "source_chunk_id" bigint,
    "confidence" double precision DEFAULT 1.0 NOT NULL,
    "generation_id" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "effective_date" "date",
    "basis_text" "text",
    CONSTRAINT "normative_edges_relation_check" CHECK (("relation" = ANY (ARRAY['references'::"text", 'modifies'::"text", 'complements'::"text", 'exception_for'::"text", 'derogates'::"text", 'supersedes'::"text", 'suspends'::"text", 'struck_down_by'::"text", 'revokes'::"text", 'cross_domain'::"text"])))
);


ALTER TABLE "public"."normative_edges" OWNER TO "postgres";


ALTER TABLE "public"."normative_edges" ALTER COLUMN "id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "public"."normative_edges_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "public"."orchestration_settings" (
    "scope" "text" NOT NULL,
    "document" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "schema_version" "text" DEFAULT ''::"text" NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_by" "text" DEFAULT ''::"text" NOT NULL
);


ALTER TABLE "public"."orchestration_settings" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."pipeline_c_run_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "run_id" "text" NOT NULL,
    "event_index" integer NOT NULL,
    "event_payload" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."pipeline_c_run_events" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."pipeline_c_runs" (
    "run_id" "text" NOT NULL,
    "trace_id" "text" DEFAULT ''::"text" NOT NULL,
    "status" "text" DEFAULT 'running'::"text" NOT NULL,
    "started_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "ended_at" timestamp with time zone,
    "request_snapshot" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "summary" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "chat_run_id" "text"
);


ALTER TABLE "public"."pipeline_c_runs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."public_captcha_passes" (
    "ip_hash" "text" NOT NULL,
    "passed_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "last_seen" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."public_captcha_passes" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."public_usage_quota" (
    "ip_hash" "text" NOT NULL,
    "day" "date" NOT NULL,
    "count" integer DEFAULT 0 NOT NULL,
    "first_seen" timestamp with time zone DEFAULT "now"() NOT NULL,
    "last_seen" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."public_usage_quota" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."query_embedding_cache" (
    "cache_key" "text" NOT NULL,
    "normalized_text" "text" DEFAULT ''::"text" NOT NULL,
    "embedding" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."query_embedding_cache" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."retrieval_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "trace_id" "text" NOT NULL,
    "query_text" "text" NOT NULL,
    "cascade_mode" "text" NOT NULL,
    "top_k" integer NOT NULL,
    "results" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "latency_ms" integer NOT NULL,
    "retriever" "text" DEFAULT 'supabase'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."retrieval_events" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."reviews" AS
 SELECT ("id")::"text" AS "review_id",
    "trace_id",
    "session_id",
    "tenant_id",
    "user_id",
    "company_id",
    "integration_id",
    "vote",
    "rating",
    "review_status" AS "status",
    "comment",
    "tags",
    "docs_used",
    "layer_contributions",
    "pain_detected",
    "task_detected",
    "source",
    "created_by",
    "created_at"
   FROM "public"."feedback";


ALTER VIEW "public"."reviews" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."service_accounts" (
    "service_account_id" "text" NOT NULL,
    "tenant_id" "text" NOT NULL,
    "display_name" "text" NOT NULL,
    "role" "text" DEFAULT 'eval_robot'::"text" NOT NULL,
    "status" "text" DEFAULT 'active'::"text" NOT NULL,
    "secret_hash" "text" DEFAULT ''::"text" NOT NULL,
    "secret_hint" "text" DEFAULT ''::"text" NOT NULL,
    "scopes" "text"[] DEFAULT '{eval:read,eval:write,chat:ask}'::"text"[] NOT NULL,
    "rate_limit_profile" "text" DEFAULT 'eval_robot'::"text" NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_by" "text" DEFAULT ''::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "last_used_at" timestamp with time zone,
    "expires_at" timestamp with time zone
);


ALTER TABLE "public"."service_accounts" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."tenant_memberships" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "tenant_id" "text" NOT NULL,
    "user_id" "text" NOT NULL,
    "role" "public"."platform_role" DEFAULT 'tenant_user'::"public"."platform_role" NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."tenant_memberships" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."tenants" (
    "tenant_id" "text" NOT NULL,
    "display_name" "text" NOT NULL,
    "status" "text" DEFAULT 'active'::"text" NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."tenants" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."terms_acceptance_state" (
    "state_key" "text" NOT NULL,
    "accepted_version" "text" DEFAULT ''::"text" NOT NULL,
    "accepted_enforcement_revision" integer DEFAULT 0 NOT NULL,
    "accepted_at_utc" timestamp with time zone,
    "accepted_by" "text" DEFAULT ''::"text" NOT NULL,
    "operator" "text" DEFAULT ''::"text" NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."terms_acceptance_state" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."usage_events" (
    "event_id" "text" NOT NULL,
    "event_type" "public"."usage_event_type" NOT NULL,
    "endpoint" "text" NOT NULL,
    "tenant_id" "text" NOT NULL,
    "user_id" "text" DEFAULT ''::"text" NOT NULL,
    "company_id" "text" DEFAULT ''::"text" NOT NULL,
    "session_id" "text" DEFAULT ''::"text" NOT NULL,
    "trace_id" "text" DEFAULT ''::"text" NOT NULL,
    "run_id" "text" DEFAULT ''::"text" NOT NULL,
    "integration_id" "text" DEFAULT ''::"text" NOT NULL,
    "provider" "text" DEFAULT ''::"text" NOT NULL,
    "model" "text" DEFAULT ''::"text" NOT NULL,
    "usage_source" "text" DEFAULT 'none'::"text" NOT NULL,
    "billable" boolean DEFAULT false NOT NULL,
    "input_tokens" integer DEFAULT 0 NOT NULL,
    "output_tokens" integer DEFAULT 0 NOT NULL,
    "total_tokens" integer DEFAULT 0 NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."usage_events" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."usage_rollups_daily" (
    "rollup_key" "text" NOT NULL,
    "rollup_date" "date" NOT NULL,
    "tenant_id" "text" NOT NULL,
    "user_id" "text" DEFAULT ''::"text" NOT NULL,
    "company_id" "text" DEFAULT ''::"text" NOT NULL,
    "endpoint" "text" DEFAULT ''::"text" NOT NULL,
    "provider" "text" DEFAULT ''::"text" NOT NULL,
    "model" "text" DEFAULT ''::"text" NOT NULL,
    "total_events" integer DEFAULT 0 NOT NULL,
    "billable_events" integer DEFAULT 0 NOT NULL,
    "input_tokens" bigint DEFAULT 0 NOT NULL,
    "output_tokens" bigint DEFAULT 0 NOT NULL,
    "total_tokens" bigint DEFAULT 0 NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."usage_rollups_daily" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."usage_rollups_monthly" (
    "rollup_key" "text" NOT NULL,
    "rollup_month" "date" NOT NULL,
    "tenant_id" "text" NOT NULL,
    "user_id" "text" DEFAULT ''::"text" NOT NULL,
    "company_id" "text" DEFAULT ''::"text" NOT NULL,
    "endpoint" "text" DEFAULT ''::"text" NOT NULL,
    "provider" "text" DEFAULT ''::"text" NOT NULL,
    "model" "text" DEFAULT ''::"text" NOT NULL,
    "total_events" integer DEFAULT 0 NOT NULL,
    "billable_events" integer DEFAULT 0 NOT NULL,
    "input_tokens" bigint DEFAULT 0 NOT NULL,
    "output_tokens" bigint DEFAULT 0 NOT NULL,
    "total_tokens" bigint DEFAULT 0 NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."usage_rollups_monthly" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user_company_access" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "tenant_id" "text" NOT NULL,
    "user_id" "text" NOT NULL,
    "company_id" "text" NOT NULL,
    "can_admin" boolean DEFAULT false NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."user_company_access" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."users" (
    "user_id" "text" NOT NULL,
    "external_user_id" "text" DEFAULT ''::"text" NOT NULL,
    "display_name" "text" DEFAULT ''::"text" NOT NULL,
    "email" "text" DEFAULT ''::"text" NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "status" "text" DEFAULT 'active'::"text" NOT NULL,
    "password_hash" "text" DEFAULT ''::"text" NOT NULL,
    "password_reset_required" boolean DEFAULT true NOT NULL,
    "password_updated_at" timestamp with time zone,
    "last_login_at" timestamp with time zone
);


ALTER TABLE "public"."users" OWNER TO "postgres";


ALTER TABLE ONLY "public"."auth_nonces"
    ADD CONSTRAINT "auth_nonces_pkey" PRIMARY KEY ("nonce_key");



ALTER TABLE ONLY "public"."chat_run_events"
    ADD CONSTRAINT "chat_run_events_chat_run_id_event_index_key" UNIQUE ("chat_run_id", "event_index");



ALTER TABLE ONLY "public"."chat_run_events"
    ADD CONSTRAINT "chat_run_events_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."chat_runs"
    ADD CONSTRAINT "chat_runs_pkey" PRIMARY KEY ("chat_run_id");



ALTER TABLE ONLY "public"."chat_session_metrics"
    ADD CONSTRAINT "chat_session_metrics_pkey" PRIMARY KEY ("session_id");



ALTER TABLE ONLY "public"."citation_gap_registry"
    ADD CONSTRAINT "citation_gap_registry_pkey" PRIMARY KEY ("reference_key");



ALTER TABLE ONLY "public"."clarification_sessions"
    ADD CONSTRAINT "clarification_sessions_pkey" PRIMARY KEY ("session_id");



ALTER TABLE ONLY "public"."companies"
    ADD CONSTRAINT "companies_pkey" PRIMARY KEY ("company_id");



ALTER TABLE ONLY "public"."contributions"
    ADD CONSTRAINT "contributions_pkey" PRIMARY KEY ("contribution_id");



ALTER TABLE ONLY "public"."conversation_turns"
    ADD CONSTRAINT "conversation_turns_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."conversations"
    ADD CONSTRAINT "conversations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."conversations"
    ADD CONSTRAINT "conversations_session_id_key" UNIQUE ("session_id");



ALTER TABLE ONLY "public"."corpus_generations"
    ADD CONSTRAINT "corpus_generations_pkey" PRIMARY KEY ("generation_id");



ALTER TABLE ONLY "public"."doc_utility_scores"
    ADD CONSTRAINT "doc_utility_scores_pkey" PRIMARY KEY ("doc_id");



ALTER TABLE ONLY "public"."document_chunks"
    ADD CONSTRAINT "document_chunks_chunk_id_key" UNIQUE ("chunk_id");



ALTER TABLE ONLY "public"."document_chunks"
    ADD CONSTRAINT "document_chunks_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_pkey" PRIMARY KEY ("doc_id");



ALTER TABLE ONLY "public"."eval_diagnoses"
    ADD CONSTRAINT "eval_diagnoses_pkey" PRIMARY KEY ("eval_diagnosis_id");



ALTER TABLE ONLY "public"."eval_rankings"
    ADD CONSTRAINT "eval_rankings_pkey" PRIMARY KEY ("eval_ranking_id");



ALTER TABLE ONLY "public"."eval_reviews"
    ADD CONSTRAINT "eval_reviews_pkey" PRIMARY KEY ("eval_review_id");



ALTER TABLE ONLY "public"."eval_runs"
    ADD CONSTRAINT "eval_runs_pkey" PRIMARY KEY ("eval_run_id");



ALTER TABLE ONLY "public"."eval_turns"
    ADD CONSTRAINT "eval_turns_pkey" PRIMARY KEY ("eval_turn_id");



ALTER TABLE ONLY "public"."expert_summary_overrides"
    ADD CONSTRAINT "expert_summary_overrides_pkey" PRIMARY KEY ("override_key");



ALTER TABLE ONLY "public"."feedback"
    ADD CONSTRAINT "feedback_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."form_guides"
    ADD CONSTRAINT "form_guides_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."form_guides"
    ADD CONSTRAINT "form_guides_reference_key_form_version_profile_id_key" UNIQUE ("reference_key", "form_version", "profile_id");



ALTER TABLE ONLY "public"."form_hotspots"
    ADD CONSTRAINT "form_hotspots_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."host_integrations"
    ADD CONSTRAINT "host_integrations_pkey" PRIMARY KEY ("integration_id");



ALTER TABLE ONLY "public"."integration_secrets"
    ADD CONSTRAINT "integration_secrets_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."invite_tokens"
    ADD CONSTRAINT "invite_tokens_pkey" PRIMARY KEY ("token_id");



ALTER TABLE ONLY "public"."job_runs"
    ADD CONSTRAINT "job_runs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."jobs"
    ADD CONSTRAINT "jobs_pkey" PRIMARY KEY ("job_id");



ALTER TABLE ONLY "public"."login_events"
    ADD CONSTRAINT "login_events_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."normative_edges"
    ADD CONSTRAINT "normative_edges_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."orchestration_settings"
    ADD CONSTRAINT "orchestration_settings_pkey" PRIMARY KEY ("scope");



ALTER TABLE ONLY "public"."pipeline_c_run_events"
    ADD CONSTRAINT "pipeline_c_run_events_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."pipeline_c_run_events"
    ADD CONSTRAINT "pipeline_c_run_events_run_id_event_index_key" UNIQUE ("run_id", "event_index");



ALTER TABLE ONLY "public"."pipeline_c_runs"
    ADD CONSTRAINT "pipeline_c_runs_pkey" PRIMARY KEY ("run_id");



ALTER TABLE ONLY "public"."public_captcha_passes"
    ADD CONSTRAINT "public_captcha_passes_pkey" PRIMARY KEY ("ip_hash");



ALTER TABLE ONLY "public"."public_usage_quota"
    ADD CONSTRAINT "public_usage_quota_pkey" PRIMARY KEY ("ip_hash", "day");



ALTER TABLE ONLY "public"."query_embedding_cache"
    ADD CONSTRAINT "query_embedding_cache_pkey" PRIMARY KEY ("cache_key");



ALTER TABLE ONLY "public"."retrieval_events"
    ADD CONSTRAINT "retrieval_events_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."service_accounts"
    ADD CONSTRAINT "service_accounts_pkey" PRIMARY KEY ("service_account_id");



ALTER TABLE ONLY "public"."tenant_memberships"
    ADD CONSTRAINT "tenant_memberships_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."tenant_memberships"
    ADD CONSTRAINT "tenant_memberships_tenant_id_user_id_key" UNIQUE ("tenant_id", "user_id");



ALTER TABLE ONLY "public"."tenants"
    ADD CONSTRAINT "tenants_pkey" PRIMARY KEY ("tenant_id");



ALTER TABLE ONLY "public"."terms_acceptance_state"
    ADD CONSTRAINT "terms_acceptance_state_pkey" PRIMARY KEY ("state_key");



ALTER TABLE ONLY "public"."usage_events"
    ADD CONSTRAINT "usage_events_pkey" PRIMARY KEY ("event_id");



ALTER TABLE ONLY "public"."usage_rollups_daily"
    ADD CONSTRAINT "usage_rollups_daily_pkey" PRIMARY KEY ("rollup_key");



ALTER TABLE ONLY "public"."usage_rollups_monthly"
    ADD CONSTRAINT "usage_rollups_monthly_pkey" PRIMARY KEY ("rollup_key");



ALTER TABLE ONLY "public"."user_company_access"
    ADD CONSTRAINT "user_company_access_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."user_company_access"
    ADD CONSTRAINT "user_company_access_tenant_id_user_id_company_id_key" UNIQUE ("tenant_id", "user_id", "company_id");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_pkey" PRIMARY KEY ("user_id");



CREATE INDEX "idx_auth_nonces_expiry" ON "public"."auth_nonces" USING "btree" ("expires_at");



CREATE INDEX "idx_chat_run_events_run" ON "public"."chat_run_events" USING "btree" ("chat_run_id", "event_index");



CREATE INDEX "idx_chat_runs_created" ON "public"."chat_runs" USING "btree" ("created_at" DESC);



CREATE UNIQUE INDEX "idx_chat_runs_request_fingerprint" ON "public"."chat_runs" USING "btree" ("request_fingerprint");



CREATE INDEX "idx_chat_runs_session" ON "public"."chat_runs" USING "btree" ("session_id", "created_at" DESC);



CREATE INDEX "idx_chat_runs_trace" ON "public"."chat_runs" USING "btree" ("trace_id");



CREATE INDEX "idx_chat_session_metrics_updated" ON "public"."chat_session_metrics" USING "btree" ("updated_at" DESC);



CREATE INDEX "idx_chunks_concept_tags" ON "public"."document_chunks" USING "gin" ("concept_tags");



CREATE INDEX "idx_chunks_doc_id" ON "public"."document_chunks" USING "btree" ("doc_id");



CREATE INDEX "idx_chunks_embedding" ON "public"."document_chunks" USING "hnsw" ("embedding" "extensions"."vector_cosine_ops") WITH ("m"='16', "ef_construction"='64');



CREATE INDEX "idx_chunks_knowledge_class" ON "public"."document_chunks" USING "btree" ("knowledge_class");



CREATE INDEX "idx_chunks_search_vector" ON "public"."document_chunks" USING "gin" ("search_vector");



CREATE INDEX "idx_chunks_sha256" ON "public"."document_chunks" USING "btree" ("chunk_sha256");



CREATE INDEX "idx_chunks_sync_generation" ON "public"."document_chunks" USING "btree" ("sync_generation");



CREATE INDEX "idx_chunks_topic_pais" ON "public"."document_chunks" USING "btree" ("topic", "pais", "curation_status", "retrieval_visibility");



CREATE INDEX "idx_citation_gap_registry_last_seen" ON "public"."citation_gap_registry" USING "btree" ("last_seen_at" DESC, "seen_count_total" DESC);



CREATE INDEX "idx_clarification_expires" ON "public"."clarification_sessions" USING "btree" ("expires_at");



CREATE INDEX "idx_clarification_session" ON "public"."clarification_sessions" USING "btree" ("session_id");



CREATE INDEX "idx_companies_tenant" ON "public"."companies" USING "btree" ("tenant_id");



CREATE INDEX "idx_contributions_status" ON "public"."contributions" USING "btree" ("status");



CREATE INDEX "idx_contributions_tenant" ON "public"."contributions" USING "btree" ("tenant_id");



CREATE INDEX "idx_conversations_session" ON "public"."conversations" USING "btree" ("session_id");



CREATE INDEX "idx_conversations_tenant" ON "public"."conversations" USING "btree" ("tenant_id");



CREATE INDEX "idx_conversations_tenant_user_company" ON "public"."conversations" USING "btree" ("tenant_id", "user_id", "company_id");



CREATE INDEX "idx_corpus_generations_activated_at" ON "public"."corpus_generations" USING "btree" ("activated_at" DESC);



CREATE UNIQUE INDEX "idx_corpus_generations_single_active" ON "public"."corpus_generations" USING "btree" ("is_active") WHERE ("is_active" = true);



CREATE INDEX "idx_doc_utility_scores_updated" ON "public"."doc_utility_scores" USING "btree" ("updated_at" DESC);



CREATE INDEX "idx_documents_ag_from_year" ON "public"."documents" USING "btree" ("ag_from_year");



CREATE INDEX "idx_documents_ag_to_year" ON "public"."documents" USING "btree" ("ag_to_year");



CREATE INDEX "idx_documents_authority" ON "public"."documents" USING "btree" ("authority");



CREATE INDEX "idx_documents_concept_tags" ON "public"."documents" USING "gin" ("concept_tags");



CREATE INDEX "idx_documents_content_hash" ON "public"."documents" USING "btree" ("content_hash") WHERE ("content_hash" IS NOT NULL);



CREATE INDEX "idx_documents_curation" ON "public"."documents" USING "btree" ("curation_status");



CREATE INDEX "idx_documents_filename_normalized" ON "public"."documents" USING "btree" ("corpus", "filename_normalized") WHERE ("filename_normalized" IS NOT NULL);



CREATE INDEX "idx_documents_first_heading" ON "public"."documents" USING "btree" ("corpus", "first_heading") WHERE ("first_heading" IS NOT NULL);



CREATE INDEX "idx_documents_pais" ON "public"."documents" USING "btree" ("pais");



CREATE INDEX "idx_documents_sync_generation" ON "public"."documents" USING "btree" ("sync_generation");



CREATE INDEX "idx_documents_topic" ON "public"."documents" USING "btree" ("topic");



CREATE INDEX "idx_documents_vigencia" ON "public"."documents" USING "btree" ("vigencia");



CREATE INDEX "idx_documents_vigencia_ruling" ON "public"."documents" USING "btree" ("vigencia_ruling_id") WHERE ("vigencia_ruling_id" IS NOT NULL);



CREATE INDEX "idx_eval_diagnoses_category" ON "public"."eval_diagnoses" USING "btree" ("category");



CREATE INDEX "idx_eval_diagnoses_run" ON "public"."eval_diagnoses" USING "btree" ("eval_run_id");



CREATE INDEX "idx_eval_diagnoses_turn" ON "public"."eval_diagnoses" USING "btree" ("eval_turn_id");



CREATE INDEX "idx_eval_rankings_run" ON "public"."eval_rankings" USING "btree" ("eval_run_id");



CREATE INDEX "idx_eval_reviews_run" ON "public"."eval_reviews" USING "btree" ("eval_run_id");



CREATE INDEX "idx_eval_reviews_turn" ON "public"."eval_reviews" USING "btree" ("eval_turn_id");



CREATE INDEX "idx_eval_runs_label" ON "public"."eval_runs" USING "btree" ("label");



CREATE INDEX "idx_eval_runs_status" ON "public"."eval_runs" USING "btree" ("status");



CREATE INDEX "idx_eval_runs_tenant" ON "public"."eval_runs" USING "btree" ("tenant_id");



CREATE INDEX "idx_eval_turns_question" ON "public"."eval_turns" USING "btree" ("question_id");



CREATE INDEX "idx_eval_turns_run" ON "public"."eval_turns" USING "btree" ("eval_run_id");



CREATE INDEX "idx_expert_summary_overrides_lookup" ON "public"."expert_summary_overrides" USING "btree" ("logical_doc_id", "provider_name", "source_hash");



CREATE INDEX "idx_feedback_rating_created" ON "public"."feedback" USING "btree" ("rating", "created_at" DESC);



CREATE INDEX "idx_feedback_session" ON "public"."feedback" USING "btree" ("session_id");



CREATE INDEX "idx_feedback_tenant_user_company" ON "public"."feedback" USING "btree" ("tenant_id", "user_id", "company_id");



CREATE INDEX "idx_feedback_trace" ON "public"."feedback" USING "btree" ("trace_id");



CREATE UNIQUE INDEX "idx_feedback_trace_tenant_unique" ON "public"."feedback" USING "btree" ("trace_id", "tenant_id");



CREATE INDEX "idx_feedback_user_created" ON "public"."feedback" USING "btree" ("user_id", "created_at" DESC);



CREATE INDEX "idx_feedback_vote_status" ON "public"."feedback" USING "btree" ("vote", "review_status");



CREATE INDEX "idx_form_guides_ref_key" ON "public"."form_guides" USING "btree" ("reference_key");



CREATE INDEX "idx_form_hotspots_casilla" ON "public"."form_hotspots" USING "btree" ("casilla");



CREATE INDEX "idx_form_hotspots_guide" ON "public"."form_hotspots" USING "btree" ("guide_id");



CREATE INDEX "idx_host_integrations_tenant" ON "public"."host_integrations" USING "btree" ("tenant_id");



CREATE INDEX "idx_invite_tokens_email" ON "public"."invite_tokens" USING "btree" ("email", "status");



CREATE INDEX "idx_invite_tokens_tenant" ON "public"."invite_tokens" USING "btree" ("tenant_id", "status");



CREATE INDEX "idx_job_runs_job" ON "public"."job_runs" USING "btree" ("job_id", "created_at" DESC);



CREATE INDEX "idx_jobs_tenant_status" ON "public"."jobs" USING "btree" ("tenant_id", "status", "created_at" DESC);



CREATE INDEX "idx_login_events_created" ON "public"."login_events" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_login_events_tenant" ON "public"."login_events" USING "btree" ("tenant_id", "created_at" DESC);



CREATE INDEX "idx_login_events_user" ON "public"."login_events" USING "btree" ("user_id", "created_at" DESC);



CREATE INDEX "idx_normative_edges_generation" ON "public"."normative_edges" USING "btree" ("generation_id");



CREATE INDEX "idx_normative_edges_source" ON "public"."normative_edges" USING "btree" ("source_key");



CREATE INDEX "idx_normative_edges_target" ON "public"."normative_edges" USING "btree" ("target_key");



CREATE INDEX "idx_pipeline_c_run_events_run" ON "public"."pipeline_c_run_events" USING "btree" ("run_id", "event_index");



CREATE INDEX "idx_pipeline_c_runs_chat_run" ON "public"."pipeline_c_runs" USING "btree" ("chat_run_id");



CREATE INDEX "idx_pipeline_c_runs_started" ON "public"."pipeline_c_runs" USING "btree" ("started_at" DESC);



CREATE INDEX "idx_pipeline_c_runs_trace" ON "public"."pipeline_c_runs" USING "btree" ("trace_id");



CREATE INDEX "idx_query_embedding_cache_updated" ON "public"."query_embedding_cache" USING "btree" ("updated_at" DESC);



CREATE INDEX "idx_retrieval_events_created" ON "public"."retrieval_events" USING "btree" ("created_at");



CREATE INDEX "idx_retrieval_events_trace" ON "public"."retrieval_events" USING "btree" ("trace_id");



CREATE INDEX "idx_service_accounts_status" ON "public"."service_accounts" USING "btree" ("status");



CREATE INDEX "idx_service_accounts_tenant" ON "public"."service_accounts" USING "btree" ("tenant_id");



CREATE INDEX "idx_tenant_memberships_tenant" ON "public"."tenant_memberships" USING "btree" ("tenant_id");



CREATE INDEX "idx_tenant_memberships_user" ON "public"."tenant_memberships" USING "btree" ("user_id");



CREATE INDEX "idx_turns_conversation" ON "public"."conversation_turns" USING "btree" ("conversation_id");



CREATE INDEX "idx_turns_trace" ON "public"."conversation_turns" USING "btree" ("trace_id");



CREATE INDEX "idx_usage_events_company" ON "public"."usage_events" USING "btree" ("company_id", "created_at" DESC);



CREATE INDEX "idx_usage_events_tenant" ON "public"."usage_events" USING "btree" ("tenant_id", "created_at" DESC);



CREATE INDEX "idx_usage_events_trace" ON "public"."usage_events" USING "btree" ("trace_id");



CREATE INDEX "idx_usage_events_user" ON "public"."usage_events" USING "btree" ("user_id", "created_at" DESC);



CREATE INDEX "idx_user_company_access_lookup" ON "public"."user_company_access" USING "btree" ("tenant_id", "user_id", "company_id");



CREATE UNIQUE INDEX "idx_users_email_normalized_unique" ON "public"."users" USING "btree" ("lower"("email")) WHERE ("btrim"("email") <> ''::"text");



CREATE INDEX "idx_users_status" ON "public"."users" USING "btree" ("status");



CREATE INDEX "public_usage_quota_day_idx" ON "public"."public_usage_quota" USING "btree" ("day");



CREATE OR REPLACE TRIGGER "trg_chat_runs_updated" BEFORE UPDATE ON "public"."chat_runs" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_chat_session_metrics_updated" BEFORE UPDATE ON "public"."chat_session_metrics" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_chunks_search_vector" BEFORE INSERT OR UPDATE ON "public"."document_chunks" FOR EACH ROW EXECUTE FUNCTION "public"."chunks_search_vector_trigger"();



CREATE OR REPLACE TRIGGER "trg_citation_gap_registry_updated" BEFORE UPDATE ON "public"."citation_gap_registry" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_clarification_updated" BEFORE UPDATE ON "public"."clarification_sessions" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_companies_updated" BEFORE UPDATE ON "public"."companies" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_conversations_updated" BEFORE UPDATE ON "public"."conversations" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_corpus_generations_updated" BEFORE UPDATE ON "public"."corpus_generations" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_doc_utility_scores_updated" BEFORE UPDATE ON "public"."doc_utility_scores" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_documents_updated" BEFORE UPDATE ON "public"."documents" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_expert_summary_overrides_updated" BEFORE UPDATE ON "public"."expert_summary_overrides" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_form_guides_updated" BEFORE UPDATE ON "public"."form_guides" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_host_integrations_updated" BEFORE UPDATE ON "public"."host_integrations" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_jobs_updated" BEFORE UPDATE ON "public"."jobs" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_orchestration_settings_updated" BEFORE UPDATE ON "public"."orchestration_settings" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_query_embedding_cache_updated" BEFORE UPDATE ON "public"."query_embedding_cache" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_tenant_memberships_updated" BEFORE UPDATE ON "public"."tenant_memberships" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_tenants_updated" BEFORE UPDATE ON "public"."tenants" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_terms_acceptance_state_updated" BEFORE UPDATE ON "public"."terms_acceptance_state" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_usage_rollups_daily_updated" BEFORE UPDATE ON "public"."usage_rollups_daily" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_usage_rollups_monthly_updated" BEFORE UPDATE ON "public"."usage_rollups_monthly" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "trg_users_updated" BEFORE UPDATE ON "public"."users" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



ALTER TABLE ONLY "public"."chat_run_events"
    ADD CONSTRAINT "chat_run_events_chat_run_id_fkey" FOREIGN KEY ("chat_run_id") REFERENCES "public"."chat_runs"("chat_run_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."companies"
    ADD CONSTRAINT "companies_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("tenant_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."conversation_turns"
    ADD CONSTRAINT "conversation_turns_conversation_id_fkey" FOREIGN KEY ("conversation_id") REFERENCES "public"."conversations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."document_chunks"
    ADD CONSTRAINT "document_chunks_doc_id_fkey" FOREIGN KEY ("doc_id") REFERENCES "public"."documents"("doc_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."eval_diagnoses"
    ADD CONSTRAINT "eval_diagnoses_eval_run_id_fkey" FOREIGN KEY ("eval_run_id") REFERENCES "public"."eval_runs"("eval_run_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."eval_diagnoses"
    ADD CONSTRAINT "eval_diagnoses_eval_turn_id_fkey" FOREIGN KEY ("eval_turn_id") REFERENCES "public"."eval_turns"("eval_turn_id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."eval_rankings"
    ADD CONSTRAINT "eval_rankings_eval_run_id_fkey" FOREIGN KEY ("eval_run_id") REFERENCES "public"."eval_runs"("eval_run_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."eval_reviews"
    ADD CONSTRAINT "eval_reviews_eval_run_id_fkey" FOREIGN KEY ("eval_run_id") REFERENCES "public"."eval_runs"("eval_run_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."eval_reviews"
    ADD CONSTRAINT "eval_reviews_eval_turn_id_fkey" FOREIGN KEY ("eval_turn_id") REFERENCES "public"."eval_turns"("eval_turn_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."eval_turns"
    ADD CONSTRAINT "eval_turns_eval_run_id_fkey" FOREIGN KEY ("eval_run_id") REFERENCES "public"."eval_runs"("eval_run_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."form_hotspots"
    ADD CONSTRAINT "form_hotspots_guide_id_fkey" FOREIGN KEY ("guide_id") REFERENCES "public"."form_guides"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."host_integrations"
    ADD CONSTRAINT "host_integrations_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("tenant_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."integration_secrets"
    ADD CONSTRAINT "integration_secrets_integration_id_fkey" FOREIGN KEY ("integration_id") REFERENCES "public"."host_integrations"("integration_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."invite_tokens"
    ADD CONSTRAINT "invite_tokens_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("tenant_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."job_runs"
    ADD CONSTRAINT "job_runs_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "public"."jobs"("job_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."pipeline_c_run_events"
    ADD CONSTRAINT "pipeline_c_run_events_run_id_fkey" FOREIGN KEY ("run_id") REFERENCES "public"."pipeline_c_runs"("run_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."pipeline_c_runs"
    ADD CONSTRAINT "pipeline_c_runs_chat_run_id_fkey" FOREIGN KEY ("chat_run_id") REFERENCES "public"."chat_runs"("chat_run_id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."tenant_memberships"
    ADD CONSTRAINT "tenant_memberships_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("tenant_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."tenant_memberships"
    ADD CONSTRAINT "tenant_memberships_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("user_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_company_access"
    ADD CONSTRAINT "user_company_access_company_id_fkey" FOREIGN KEY ("company_id") REFERENCES "public"."companies"("company_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_company_access"
    ADD CONSTRAINT "user_company_access_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("tenant_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_company_access"
    ADD CONSTRAINT "user_company_access_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("user_id") ON DELETE CASCADE;



ALTER TABLE "public"."chat_runs" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "chat_runs_tenant_insert" ON "public"."chat_runs" FOR INSERT WITH CHECK ((("public"."requesting_tenant_id"() = ''::"text") OR ("tenant_id" = "public"."requesting_tenant_id"()) OR ("tenant_id" IS NULL)));



CREATE POLICY "chat_runs_tenant_select" ON "public"."chat_runs" FOR SELECT USING ((("public"."requesting_tenant_id"() = ''::"text") OR ("tenant_id" = "public"."requesting_tenant_id"()) OR ("tenant_id" IS NULL)));



ALTER TABLE "public"."contributions" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "contributions_tenant_insert" ON "public"."contributions" FOR INSERT WITH CHECK ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text")));



CREATE POLICY "contributions_tenant_select" ON "public"."contributions" FOR SELECT USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text")));



CREATE POLICY "contributions_tenant_update" ON "public"."contributions" FOR UPDATE USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text"))) WITH CHECK ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text")));



ALTER TABLE "public"."conversation_turns" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."conversations" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "conversations_tenant_delete" ON "public"."conversations" FOR DELETE USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text")));



CREATE POLICY "conversations_tenant_insert" ON "public"."conversations" FOR INSERT WITH CHECK ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text")));



CREATE POLICY "conversations_tenant_select" ON "public"."conversations" FOR SELECT USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text")));



CREATE POLICY "conversations_tenant_update" ON "public"."conversations" FOR UPDATE USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text"))) WITH CHECK ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text")));



ALTER TABLE "public"."eval_diagnoses" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."eval_rankings" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."eval_reviews" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."eval_runs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."eval_turns" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."feedback" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "feedback_tenant_delete" ON "public"."feedback" FOR DELETE USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text") OR ("tenant_id" = ''::"text")));



CREATE POLICY "feedback_tenant_insert" ON "public"."feedback" FOR INSERT WITH CHECK ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text") OR ("tenant_id" = ''::"text")));



CREATE POLICY "feedback_tenant_select" ON "public"."feedback" FOR SELECT USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text") OR ("tenant_id" = ''::"text")));



CREATE POLICY "feedback_tenant_update" ON "public"."feedback" FOR UPDATE USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text") OR ("tenant_id" = ''::"text"))) WITH CHECK ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text") OR ("tenant_id" = ''::"text")));



ALTER TABLE "public"."invite_tokens" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "invites_tenant_isolation" ON "public"."invite_tokens" USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text")));



ALTER TABLE "public"."jobs" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "jobs_tenant_insert" ON "public"."jobs" FOR INSERT WITH CHECK ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text") OR ("tenant_id" = ''::"text")));



CREATE POLICY "jobs_tenant_select" ON "public"."jobs" FOR SELECT USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text") OR ("tenant_id" = ''::"text")));



CREATE POLICY "jobs_tenant_update" ON "public"."jobs" FOR UPDATE USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text") OR ("tenant_id" = ''::"text"))) WITH CHECK ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text") OR ("tenant_id" = ''::"text")));



CREATE POLICY "memberships_tenant_isolation" ON "public"."tenant_memberships" USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text")));



ALTER TABLE "public"."normative_edges" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "normative_edges_read_all" ON "public"."normative_edges" FOR SELECT USING (true);



CREATE POLICY "normative_edges_service_write" ON "public"."normative_edges" USING (("auth"."role"() = 'service_role'::"text"));



ALTER TABLE "public"."public_captcha_passes" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "public_captcha_passes_service_only_delete" ON "public"."public_captcha_passes" FOR DELETE USING (("public"."requesting_tenant_id"() = ''::"text"));



CREATE POLICY "public_captcha_passes_service_only_insert" ON "public"."public_captcha_passes" FOR INSERT WITH CHECK (("public"."requesting_tenant_id"() = ''::"text"));



CREATE POLICY "public_captcha_passes_service_only_select" ON "public"."public_captcha_passes" FOR SELECT USING (("public"."requesting_tenant_id"() = ''::"text"));



CREATE POLICY "public_captcha_passes_service_only_update" ON "public"."public_captcha_passes" FOR UPDATE USING (("public"."requesting_tenant_id"() = ''::"text")) WITH CHECK (("public"."requesting_tenant_id"() = ''::"text"));



ALTER TABLE "public"."public_usage_quota" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "public_usage_quota_service_only_delete" ON "public"."public_usage_quota" FOR DELETE USING (("public"."requesting_tenant_id"() = ''::"text"));



CREATE POLICY "public_usage_quota_service_only_insert" ON "public"."public_usage_quota" FOR INSERT WITH CHECK (("public"."requesting_tenant_id"() = ''::"text"));



CREATE POLICY "public_usage_quota_service_only_select" ON "public"."public_usage_quota" FOR SELECT USING (("public"."requesting_tenant_id"() = ''::"text"));



CREATE POLICY "public_usage_quota_service_only_update" ON "public"."public_usage_quota" FOR UPDATE USING (("public"."requesting_tenant_id"() = ''::"text")) WITH CHECK (("public"."requesting_tenant_id"() = ''::"text"));



ALTER TABLE "public"."service_accounts" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."tenant_memberships" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "turns_tenant_delete" ON "public"."conversation_turns" FOR DELETE USING ((("public"."requesting_tenant_id"() = ''::"text") OR ("conversation_id" IN ( SELECT "conversations"."id"
   FROM "public"."conversations"
  WHERE ("conversations"."tenant_id" = "public"."requesting_tenant_id"())))));



CREATE POLICY "turns_tenant_insert" ON "public"."conversation_turns" FOR INSERT WITH CHECK ((("public"."requesting_tenant_id"() = ''::"text") OR ("conversation_id" IN ( SELECT "conversations"."id"
   FROM "public"."conversations"
  WHERE ("conversations"."tenant_id" = "public"."requesting_tenant_id"())))));



CREATE POLICY "turns_tenant_select" ON "public"."conversation_turns" FOR SELECT USING ((("public"."requesting_tenant_id"() = ''::"text") OR ("conversation_id" IN ( SELECT "conversations"."id"
   FROM "public"."conversations"
  WHERE ("conversations"."tenant_id" = "public"."requesting_tenant_id"())))));



CREATE POLICY "turns_tenant_update" ON "public"."conversation_turns" FOR UPDATE USING ((("public"."requesting_tenant_id"() = ''::"text") OR ("conversation_id" IN ( SELECT "conversations"."id"
   FROM "public"."conversations"
  WHERE ("conversations"."tenant_id" = "public"."requesting_tenant_id"()))))) WITH CHECK ((("public"."requesting_tenant_id"() = ''::"text") OR ("conversation_id" IN ( SELECT "conversations"."id"
   FROM "public"."conversations"
  WHERE ("conversations"."tenant_id" = "public"."requesting_tenant_id"())))));



ALTER TABLE "public"."usage_events" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "usage_events_tenant_insert" ON "public"."usage_events" FOR INSERT WITH CHECK ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text")));



CREATE POLICY "usage_events_tenant_select" ON "public"."usage_events" FOR SELECT USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text")));



ALTER TABLE "public"."usage_rollups_daily" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "usage_rollups_daily_tenant_select" ON "public"."usage_rollups_daily" FOR SELECT USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text")));



ALTER TABLE "public"."usage_rollups_monthly" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "usage_rollups_monthly_tenant_select" ON "public"."usage_rollups_monthly" FOR SELECT USING ((("tenant_id" = "public"."requesting_tenant_id"()) OR ("public"."requesting_tenant_id"() = ''::"text")));



GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



GRANT ALL ON FUNCTION "public"."chunks_search_vector_trigger"() TO "anon";
GRANT ALL ON FUNCTION "public"."chunks_search_vector_trigger"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."chunks_search_vector_trigger"() TO "service_role";



GRANT ALL ON FUNCTION "public"."fts_scored_prefilter"("search_query" "text", "topic_list" "text"[], "country" "text", "result_limit" integer, "filter_knowledge_class" "text", "filter_sync_generation" "text", "fts_query" "text", "filter_effective_date_max" "date") TO "anon";
GRANT ALL ON FUNCTION "public"."fts_scored_prefilter"("search_query" "text", "topic_list" "text"[], "country" "text", "result_limit" integer, "filter_knowledge_class" "text", "filter_sync_generation" "text", "fts_query" "text", "filter_effective_date_max" "date") TO "authenticated";
GRANT ALL ON FUNCTION "public"."fts_scored_prefilter"("search_query" "text", "topic_list" "text"[], "country" "text", "result_limit" integer, "filter_knowledge_class" "text", "filter_sync_generation" "text", "fts_query" "text", "filter_effective_date_max" "date") TO "service_role";



GRANT ALL ON FUNCTION "public"."hybrid_search"("query_embedding" "extensions"."vector", "query_text" "text", "filter_topic" "text", "filter_pais" "text", "match_count" integer, "rrf_k" integer, "fts_weight" double precision, "semantic_weight" double precision, "filter_knowledge_class" "text", "filter_sync_generation" "text", "fts_query" "text", "filter_effective_date_max" "date") TO "anon";
GRANT ALL ON FUNCTION "public"."hybrid_search"("query_embedding" "extensions"."vector", "query_text" "text", "filter_topic" "text", "filter_pais" "text", "match_count" integer, "rrf_k" integer, "fts_weight" double precision, "semantic_weight" double precision, "filter_knowledge_class" "text", "filter_sync_generation" "text", "fts_query" "text", "filter_effective_date_max" "date") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hybrid_search"("query_embedding" "extensions"."vector", "query_text" "text", "filter_topic" "text", "filter_pais" "text", "match_count" integer, "rrf_k" integer, "fts_weight" double precision, "semantic_weight" double precision, "filter_knowledge_class" "text", "filter_sync_generation" "text", "fts_query" "text", "filter_effective_date_max" "date") TO "service_role";



GRANT ALL ON FUNCTION "public"."requesting_tenant_id"() TO "anon";
GRANT ALL ON FUNCTION "public"."requesting_tenant_id"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."requesting_tenant_id"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "service_role";



GRANT ALL ON TABLE "public"."auth_nonces" TO "anon";
GRANT ALL ON TABLE "public"."auth_nonces" TO "authenticated";
GRANT ALL ON TABLE "public"."auth_nonces" TO "service_role";



GRANT ALL ON TABLE "public"."chat_run_events" TO "anon";
GRANT ALL ON TABLE "public"."chat_run_events" TO "authenticated";
GRANT ALL ON TABLE "public"."chat_run_events" TO "service_role";



GRANT ALL ON TABLE "public"."chat_runs" TO "anon";
GRANT ALL ON TABLE "public"."chat_runs" TO "authenticated";
GRANT ALL ON TABLE "public"."chat_runs" TO "service_role";



GRANT ALL ON TABLE "public"."chat_session_metrics" TO "anon";
GRANT ALL ON TABLE "public"."chat_session_metrics" TO "authenticated";
GRANT ALL ON TABLE "public"."chat_session_metrics" TO "service_role";



GRANT ALL ON TABLE "public"."citation_gap_registry" TO "anon";
GRANT ALL ON TABLE "public"."citation_gap_registry" TO "authenticated";
GRANT ALL ON TABLE "public"."citation_gap_registry" TO "service_role";



GRANT ALL ON TABLE "public"."clarification_sessions" TO "anon";
GRANT ALL ON TABLE "public"."clarification_sessions" TO "authenticated";
GRANT ALL ON TABLE "public"."clarification_sessions" TO "service_role";



GRANT ALL ON TABLE "public"."companies" TO "anon";
GRANT ALL ON TABLE "public"."companies" TO "authenticated";
GRANT ALL ON TABLE "public"."companies" TO "service_role";



GRANT ALL ON TABLE "public"."contributions" TO "anon";
GRANT ALL ON TABLE "public"."contributions" TO "authenticated";
GRANT ALL ON TABLE "public"."contributions" TO "service_role";



GRANT ALL ON TABLE "public"."conversation_turns" TO "anon";
GRANT ALL ON TABLE "public"."conversation_turns" TO "authenticated";
GRANT ALL ON TABLE "public"."conversation_turns" TO "service_role";



GRANT ALL ON TABLE "public"."conversations" TO "anon";
GRANT ALL ON TABLE "public"."conversations" TO "authenticated";
GRANT ALL ON TABLE "public"."conversations" TO "service_role";



GRANT ALL ON TABLE "public"."conversation_summaries" TO "anon";
GRANT ALL ON TABLE "public"."conversation_summaries" TO "authenticated";
GRANT ALL ON TABLE "public"."conversation_summaries" TO "service_role";



GRANT ALL ON TABLE "public"."corpus_generations" TO "anon";
GRANT ALL ON TABLE "public"."corpus_generations" TO "authenticated";
GRANT ALL ON TABLE "public"."corpus_generations" TO "service_role";



GRANT ALL ON TABLE "public"."doc_utility_scores" TO "anon";
GRANT ALL ON TABLE "public"."doc_utility_scores" TO "authenticated";
GRANT ALL ON TABLE "public"."doc_utility_scores" TO "service_role";



GRANT ALL ON TABLE "public"."document_chunks" TO "anon";
GRANT ALL ON TABLE "public"."document_chunks" TO "authenticated";
GRANT ALL ON TABLE "public"."document_chunks" TO "service_role";



GRANT ALL ON TABLE "public"."documents" TO "anon";
GRANT ALL ON TABLE "public"."documents" TO "authenticated";
GRANT ALL ON TABLE "public"."documents" TO "service_role";



GRANT ALL ON TABLE "public"."eval_diagnoses" TO "anon";
GRANT ALL ON TABLE "public"."eval_diagnoses" TO "authenticated";
GRANT ALL ON TABLE "public"."eval_diagnoses" TO "service_role";



GRANT ALL ON TABLE "public"."eval_rankings" TO "anon";
GRANT ALL ON TABLE "public"."eval_rankings" TO "authenticated";
GRANT ALL ON TABLE "public"."eval_rankings" TO "service_role";



GRANT ALL ON TABLE "public"."eval_reviews" TO "anon";
GRANT ALL ON TABLE "public"."eval_reviews" TO "authenticated";
GRANT ALL ON TABLE "public"."eval_reviews" TO "service_role";



GRANT ALL ON TABLE "public"."eval_runs" TO "anon";
GRANT ALL ON TABLE "public"."eval_runs" TO "authenticated";
GRANT ALL ON TABLE "public"."eval_runs" TO "service_role";



GRANT ALL ON TABLE "public"."eval_turns" TO "anon";
GRANT ALL ON TABLE "public"."eval_turns" TO "authenticated";
GRANT ALL ON TABLE "public"."eval_turns" TO "service_role";



GRANT ALL ON TABLE "public"."expert_summary_overrides" TO "anon";
GRANT ALL ON TABLE "public"."expert_summary_overrides" TO "authenticated";
GRANT ALL ON TABLE "public"."expert_summary_overrides" TO "service_role";



GRANT ALL ON TABLE "public"."feedback" TO "anon";
GRANT ALL ON TABLE "public"."feedback" TO "authenticated";
GRANT ALL ON TABLE "public"."feedback" TO "service_role";



GRANT ALL ON TABLE "public"."form_guides" TO "anon";
GRANT ALL ON TABLE "public"."form_guides" TO "authenticated";
GRANT ALL ON TABLE "public"."form_guides" TO "service_role";



GRANT ALL ON TABLE "public"."form_hotspots" TO "anon";
GRANT ALL ON TABLE "public"."form_hotspots" TO "authenticated";
GRANT ALL ON TABLE "public"."form_hotspots" TO "service_role";



GRANT ALL ON TABLE "public"."host_integrations" TO "anon";
GRANT ALL ON TABLE "public"."host_integrations" TO "authenticated";
GRANT ALL ON TABLE "public"."host_integrations" TO "service_role";



GRANT ALL ON TABLE "public"."integration_secrets" TO "anon";
GRANT ALL ON TABLE "public"."integration_secrets" TO "authenticated";
GRANT ALL ON TABLE "public"."integration_secrets" TO "service_role";



GRANT ALL ON TABLE "public"."invite_tokens" TO "anon";
GRANT ALL ON TABLE "public"."invite_tokens" TO "authenticated";
GRANT ALL ON TABLE "public"."invite_tokens" TO "service_role";



GRANT ALL ON TABLE "public"."job_runs" TO "anon";
GRANT ALL ON TABLE "public"."job_runs" TO "authenticated";
GRANT ALL ON TABLE "public"."job_runs" TO "service_role";



GRANT ALL ON TABLE "public"."jobs" TO "anon";
GRANT ALL ON TABLE "public"."jobs" TO "authenticated";
GRANT ALL ON TABLE "public"."jobs" TO "service_role";



GRANT ALL ON TABLE "public"."login_events" TO "anon";
GRANT ALL ON TABLE "public"."login_events" TO "authenticated";
GRANT ALL ON TABLE "public"."login_events" TO "service_role";



GRANT ALL ON TABLE "public"."normative_edges" TO "anon";
GRANT ALL ON TABLE "public"."normative_edges" TO "authenticated";
GRANT ALL ON TABLE "public"."normative_edges" TO "service_role";



GRANT ALL ON SEQUENCE "public"."normative_edges_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."normative_edges_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."normative_edges_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."orchestration_settings" TO "anon";
GRANT ALL ON TABLE "public"."orchestration_settings" TO "authenticated";
GRANT ALL ON TABLE "public"."orchestration_settings" TO "service_role";



GRANT ALL ON TABLE "public"."pipeline_c_run_events" TO "anon";
GRANT ALL ON TABLE "public"."pipeline_c_run_events" TO "authenticated";
GRANT ALL ON TABLE "public"."pipeline_c_run_events" TO "service_role";



GRANT ALL ON TABLE "public"."pipeline_c_runs" TO "anon";
GRANT ALL ON TABLE "public"."pipeline_c_runs" TO "authenticated";
GRANT ALL ON TABLE "public"."pipeline_c_runs" TO "service_role";



GRANT ALL ON TABLE "public"."public_captcha_passes" TO "anon";
GRANT ALL ON TABLE "public"."public_captcha_passes" TO "authenticated";
GRANT ALL ON TABLE "public"."public_captcha_passes" TO "service_role";



GRANT ALL ON TABLE "public"."public_usage_quota" TO "anon";
GRANT ALL ON TABLE "public"."public_usage_quota" TO "authenticated";
GRANT ALL ON TABLE "public"."public_usage_quota" TO "service_role";



GRANT ALL ON TABLE "public"."query_embedding_cache" TO "anon";
GRANT ALL ON TABLE "public"."query_embedding_cache" TO "authenticated";
GRANT ALL ON TABLE "public"."query_embedding_cache" TO "service_role";



GRANT ALL ON TABLE "public"."retrieval_events" TO "anon";
GRANT ALL ON TABLE "public"."retrieval_events" TO "authenticated";
GRANT ALL ON TABLE "public"."retrieval_events" TO "service_role";



GRANT ALL ON TABLE "public"."reviews" TO "anon";
GRANT ALL ON TABLE "public"."reviews" TO "authenticated";
GRANT ALL ON TABLE "public"."reviews" TO "service_role";



GRANT ALL ON TABLE "public"."service_accounts" TO "anon";
GRANT ALL ON TABLE "public"."service_accounts" TO "authenticated";
GRANT ALL ON TABLE "public"."service_accounts" TO "service_role";



GRANT ALL ON TABLE "public"."tenant_memberships" TO "anon";
GRANT ALL ON TABLE "public"."tenant_memberships" TO "authenticated";
GRANT ALL ON TABLE "public"."tenant_memberships" TO "service_role";



GRANT ALL ON TABLE "public"."tenants" TO "anon";
GRANT ALL ON TABLE "public"."tenants" TO "authenticated";
GRANT ALL ON TABLE "public"."tenants" TO "service_role";



GRANT ALL ON TABLE "public"."terms_acceptance_state" TO "anon";
GRANT ALL ON TABLE "public"."terms_acceptance_state" TO "authenticated";
GRANT ALL ON TABLE "public"."terms_acceptance_state" TO "service_role";



GRANT ALL ON TABLE "public"."usage_events" TO "anon";
GRANT ALL ON TABLE "public"."usage_events" TO "authenticated";
GRANT ALL ON TABLE "public"."usage_events" TO "service_role";



GRANT ALL ON TABLE "public"."usage_rollups_daily" TO "anon";
GRANT ALL ON TABLE "public"."usage_rollups_daily" TO "authenticated";
GRANT ALL ON TABLE "public"."usage_rollups_daily" TO "service_role";



GRANT ALL ON TABLE "public"."usage_rollups_monthly" TO "anon";
GRANT ALL ON TABLE "public"."usage_rollups_monthly" TO "authenticated";
GRANT ALL ON TABLE "public"."usage_rollups_monthly" TO "service_role";



GRANT ALL ON TABLE "public"."user_company_access" TO "anon";
GRANT ALL ON TABLE "public"."user_company_access" TO "authenticated";
GRANT ALL ON TABLE "public"."user_company_access" TO "service_role";



GRANT ALL ON TABLE "public"."users" TO "anon";
GRANT ALL ON TABLE "public"."users" TO "authenticated";
GRANT ALL ON TABLE "public"."users" TO "service_role";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";







