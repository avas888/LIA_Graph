-- vigencia v1.1 Phase 4 — add optional effective_date_max filter to retrieval RPCs
-- Plan: docs/next/vigencia_v1.1.md §Phase 4
--
-- This migration ports the Python-side `max_effective_date` filter (already
-- applied in `retrieval_filters._metadata_filtered_candidates`) down into the
-- SQL hot path. Before this migration the SQL RPCs did NOT filter by
-- `effective_date`, so documents with a future effective_date could still be
-- returned and only dropped by the Python post-filter. Callers that ran the
-- pipeline with a caller-supplied `consulta_date` had no SQL-side enforcement.
--
-- Both RPCs gain a new optional parameter:
--   filter_effective_date_max DATE DEFAULT NULL
--
-- When NULL (the default), the behavior is identical to the pre-Phase-4 RPC —
-- no new WHERE clauses are active. This is load-bearing: existing callers that
-- do not thread the new kwarg keep working without any DB-side change.
--
-- When non-NULL, the RPC only returns chunks whose `effective_date` is NULL
-- (unknown — keep them) OR `<= filter_effective_date_max`. This replicates
-- the Python-side filter exactly.
--
-- The `document_chunks.effective_date DATE` column was added by
-- `20260319190000_chunks_publish_effective_date.sql`.

SET LOCAL search_path = public, extensions;
SET search_path TO public, extensions;

-- ============================================================
-- fts_scored_prefilter: add filter_effective_date_max parameter
-- ============================================================
-- Baseline: 20260327000001_chunk_section_type.sql (last definition).
-- Parameter signature change requires DROP + CREATE.
DROP FUNCTION IF EXISTS fts_scored_prefilter(text, text[], text, int, text, text, text);

CREATE OR REPLACE FUNCTION fts_scored_prefilter(
    search_query              TEXT,
    topic_list                TEXT[],
    country                   TEXT    DEFAULT 'colombia',
    result_limit              INTEGER DEFAULT 4000,
    filter_knowledge_class    TEXT    DEFAULT NULL,
    filter_sync_generation    TEXT    DEFAULT NULL,
    fts_query                 TEXT    DEFAULT NULL,
    filter_effective_date_max DATE    DEFAULT NULL
)
RETURNS TABLE (
    doc_id TEXT,
    chunk_id TEXT,
    chunk_text TEXT,
    summary TEXT,
    concept_tags TEXT[],
    chunk_start INT,
    chunk_end INT,
    source_type TEXT,
    curation_status TEXT,
    topic TEXT,
    pais TEXT,
    authority TEXT,
    vigencia TEXT,
    retrieval_visibility TEXT,
    lane_scores JSONB,
    relative_path TEXT,
    tema TEXT,
    subtema TEXT,
    tipo_de_documento TEXT,
    tipo_de_consulta TEXT,
    tipo_de_accion TEXT,
    tipo_de_riesgo TEXT,
    trust_tier TEXT,
    source_origin TEXT,
    nivel_practicidad TEXT,
    knowledge_class TEXT,
    chunk_section_type TEXT,
    fts_rank REAL
)
LANGUAGE plpgsql
STABLE
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
      AND COALESCE(dc.vigencia, '') NOT IN ('derogada', 'proyecto')
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
          AND COALESCE(dc.vigencia, '') NOT IN ('derogada', 'proyecto')
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

GRANT EXECUTE ON FUNCTION fts_scored_prefilter TO authenticated;
GRANT EXECUTE ON FUNCTION fts_scored_prefilter TO anon;
GRANT EXECUTE ON FUNCTION fts_scored_prefilter TO service_role;

-- ============================================================
-- hybrid_search: add filter_effective_date_max parameter
-- ============================================================
-- Baseline: 20260327000001_chunk_section_type.sql (last definition).
-- Parameter signature change requires DROP + CREATE.
DROP FUNCTION IF EXISTS hybrid_search(vector(768), text, text, text, int, int, float, float, text, text, text);

CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding           vector(768),
    query_text                text,
    filter_topic              text  DEFAULT NULL,
    filter_pais               text  DEFAULT NULL,
    match_count               int   DEFAULT 100,
    rrf_k                     int   DEFAULT 60,
    fts_weight                float DEFAULT 1.0,
    semantic_weight           float DEFAULT 1.0,
    filter_knowledge_class    text  DEFAULT NULL,
    filter_sync_generation    text  DEFAULT NULL,
    fts_query                 text  DEFAULT NULL,
    filter_effective_date_max date  DEFAULT NULL
)
RETURNS TABLE (
    doc_id text,
    chunk_id text,
    chunk_text text,
    summary text,
    concept_tags text[],
    chunk_start int,
    chunk_end int,
    source_type text,
    curation_status text,
    topic text,
    pais text,
    authority text,
    vigencia text,
    retrieval_visibility text,
    lane_scores jsonb,
    relative_path text,
    tema text,
    subtema text,
    tipo_de_documento text,
    tipo_de_consulta text,
    tipo_de_accion text,
    tipo_de_riesgo text,
    trust_tier text,
    source_origin text,
    nivel_practicidad text,
    knowledge_class text,
    chunk_section_type text,
    fts_rank float,
    vector_similarity float,
    rrf_score float
)
LANGUAGE plpgsql
STABLE
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
          AND COALESCE(dc.vigencia, '') NOT IN ('derogada', 'proyecto')
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
          AND COALESCE(dc.vigencia, '') NOT IN ('derogada', 'proyecto')
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

GRANT EXECUTE ON FUNCTION hybrid_search TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search TO anon;
GRANT EXECUTE ON FUNCTION hybrid_search TO service_role;
