-- Ingest-fix v2, Phase 2 — sub_topic_taxonomy reference table +
-- hybrid_search RPC extension (filter_subtopic + subtopic_boost).
--
-- This migration is ADDITIVE beyond the 2026-04-17 baseline:
--   * adds `sub_topic_taxonomy` table (materialized projection of
--     `config/subtopic_taxonomy.json` — file is source of truth per
--     ingestfix-v2 Decision B1).
--   * adds `documents.requires_subtopic_review` bool column.
--   * replaces `hybrid_search` with a version that accepts
--     `filter_subtopic` + `subtopic_boost` and applies a post-RRF score
--     multiplier when a chunk's `subtema` matches the filter.
--
-- Invariant I5 — NULL subtemas are NOT penalized. A missing subtema
-- yields the unboosted rrf_score, not a lower one.

-- ---------------------------------------------------------------------
-- sub_topic_taxonomy — reference table (materialized from JSON file).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "public"."sub_topic_taxonomy" (
    "parent_topic_key" TEXT NOT NULL,
    "sub_topic_key"    TEXT NOT NULL,
    "label"            TEXT NOT NULL,
    "aliases"          TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    "evidence_count"   INTEGER NOT NULL DEFAULT 0,
    "curated_at"       TIMESTAMPTZ,
    "curator"          TEXT,
    "version"          TEXT NOT NULL,
    "updated_at"       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("parent_topic_key", "sub_topic_key")
);

CREATE INDEX IF NOT EXISTS "ix_sub_topic_taxonomy_parent"
    ON "public"."sub_topic_taxonomy" ("parent_topic_key");

CREATE INDEX IF NOT EXISTS "ix_sub_topic_taxonomy_aliases"
    ON "public"."sub_topic_taxonomy" USING GIN ("aliases");

ALTER TABLE "public"."sub_topic_taxonomy" OWNER TO "postgres";

-- ---------------------------------------------------------------------
-- documents.requires_subtopic_review — curator-review flag for docs
-- whose subtopic classification confidence was inconclusive.
-- ---------------------------------------------------------------------
ALTER TABLE "public"."documents"
    ADD COLUMN IF NOT EXISTS "requires_subtopic_review" BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS "ix_documents_requires_subtopic_review"
    ON "public"."documents" ("requires_subtopic_review")
    WHERE "requires_subtopic_review" IS TRUE;

-- ---------------------------------------------------------------------
-- hybrid_search — replace with subtopic-aware version.
-- Postgres requires DROP before changing the parameter list.
-- ---------------------------------------------------------------------
DROP FUNCTION IF EXISTS "public"."hybrid_search"(
    "extensions"."vector",
    "text",
    "text",
    "text",
    integer,
    integer,
    double precision,
    double precision,
    "text",
    "text",
    "text",
    "date"
);

CREATE OR REPLACE FUNCTION "public"."hybrid_search"(
    "query_embedding"            "extensions"."vector",
    "query_text"                 "text",
    "filter_topic"               "text"             DEFAULT NULL::"text",
    "filter_pais"                "text"             DEFAULT NULL::"text",
    "match_count"                integer            DEFAULT 100,
    "rrf_k"                      integer            DEFAULT 60,
    "fts_weight"                 double precision   DEFAULT 1.0,
    "semantic_weight"            double precision   DEFAULT 1.0,
    "filter_knowledge_class"     "text"             DEFAULT NULL::"text",
    "filter_sync_generation"     "text"             DEFAULT NULL::"text",
    "fts_query"                  "text"             DEFAULT NULL::"text",
    "filter_effective_date_max"  "date"             DEFAULT NULL::"date",
    "filter_subtopic"            "text"             DEFAULT NULL::"text",
    "subtopic_boost"             double precision   DEFAULT 1.5
) RETURNS TABLE(
    "doc_id"               "text",
    "chunk_id"             "text",
    "chunk_text"           "text",
    "summary"              "text",
    "concept_tags"         "text"[],
    "chunk_start"          integer,
    "chunk_end"            integer,
    "source_type"          "text",
    "curation_status"      "text",
    "topic"                "text",
    "pais"                 "text",
    "authority"            "text",
    "vigencia"             "text",
    "retrieval_visibility" "text",
    "lane_scores"          "jsonb",
    "relative_path"        "text",
    "tema"                 "text",
    "subtema"              "text",
    "tipo_de_documento"    "text",
    "tipo_de_consulta"     "text",
    "tipo_de_accion"       "text",
    "tipo_de_riesgo"       "text",
    "trust_tier"           "text",
    "source_origin"        "text",
    "nivel_practicidad"    "text",
    "knowledge_class"      "text",
    "chunk_section_type"   "text",
    "fts_rank"             double precision,
    "vector_similarity"    double precision,
    "rrf_score"            double precision
)
    LANGUAGE "plpgsql" STABLE
    AS $$
DECLARE
    effective_tsq tsquery;
    effective_boost double precision;
BEGIN
    IF fts_query IS NOT NULL AND fts_query <> '' THEN
        effective_tsq := to_tsquery('spanish', fts_query);
    ELSE
        effective_tsq := plainto_tsquery('spanish', query_text);
    END IF;

    -- Invariant I5: never penalize. Boost < 1.0 is coerced to 1.0.
    effective_boost := GREATEST(COALESCE(subtopic_boost, 1.0), 1.0);

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
                (
                    fts_weight / (rrf_k + COALESCE(f.rn, match_count + 1))
                    + semantic_weight / (rrf_k + COALESCE(s.rn, match_count + 1))
                )
                *
                CASE
                    WHEN filter_subtopic IS NOT NULL
                         AND COALESCE(f.subtema, s.subtema) = filter_subtopic
                    THEN effective_boost
                    ELSE 1.0
                END
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

ALTER FUNCTION "public"."hybrid_search"(
    "extensions"."vector",
    "text",
    "text",
    "text",
    integer,
    integer,
    double precision,
    double precision,
    "text",
    "text",
    "text",
    "date",
    "text",
    double precision
) OWNER TO "postgres";

GRANT ALL ON FUNCTION "public"."hybrid_search"(
    "extensions"."vector",
    "text",
    "text",
    "text",
    integer,
    integer,
    double precision,
    double precision,
    "text",
    "text",
    "text",
    "date",
    "text",
    double precision
) TO "anon";

GRANT ALL ON FUNCTION "public"."hybrid_search"(
    "extensions"."vector",
    "text",
    "text",
    "text",
    integer,
    integer,
    double precision,
    double precision,
    "text",
    "text",
    "text",
    "date",
    "text",
    double precision
) TO "authenticated";

GRANT ALL ON FUNCTION "public"."hybrid_search"(
    "extensions"."vector",
    "text",
    "text",
    "text",
    integer,
    integer,
    double precision,
    double precision,
    "text",
    "text",
    "text",
    "date",
    "text",
    double precision
) TO "service_role";
