SET LOCAL search_path = public, extensions;

-- Phase 5: Hybrid search RPC function (FTS + vector via RRF)
-- Requires: pgvector extension, document_chunks.embedding column (migration 000006)

CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(768),
    query_text text,
    filter_topic text DEFAULT NULL,
    filter_pais text DEFAULT NULL,
    match_count int DEFAULT 100,
    rrf_k int DEFAULT 60,
    fts_weight float DEFAULT 1.0,
    semantic_weight float DEFAULT 1.0
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
    fts_rank float,
    vector_similarity float,
    rrf_score float
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
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
            ts_rank_cd(dc.search_vector, plainto_tsquery('spanish', query_text)) AS rank,
            ROW_NUMBER() OVER (ORDER BY ts_rank_cd(dc.search_vector, plainto_tsquery('spanish', query_text)) DESC) AS rn
        FROM document_chunks dc
        WHERE dc.search_vector @@ plainto_tsquery('spanish', query_text)
          AND (filter_topic IS NULL OR dc.topic IN (filter_topic, filter_topic || '_parametros'))
          AND (filter_pais IS NULL OR dc.pais = filter_pais)
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
            1.0 - (dc.embedding <=> query_embedding) AS similarity,
            ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding) AS rn
        FROM document_chunks dc
        WHERE dc.embedding IS NOT NULL
          AND (filter_topic IS NULL OR dc.topic IN (filter_topic, filter_topic || '_parametros'))
          AND (filter_pais IS NULL OR dc.pais = filter_pais)
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
        c.fts_rank::float,
        c.vector_similarity::float,
        c.rrf_score::float
    FROM combined c
    ORDER BY c.rrf_score DESC
    LIMIT match_count;
END;
$$;

-- Grant access to all Supabase roles
GRANT EXECUTE ON FUNCTION hybrid_search TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search TO anon;
GRANT EXECUTE ON FUNCTION hybrid_search TO service_role;
