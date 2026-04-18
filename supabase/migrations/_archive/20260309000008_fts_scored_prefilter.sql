-- Phase 6: FTS-scored pre-filter RPC + metadata columns on document_chunks
-- Replaces the paginated full-corpus fetch (5 pages × 5000 rows ≈ 9s)
-- with a single FTS-scored SQL round-trip (~200ms for 4000 results).

-- Step 1: Add denormalized metadata columns to document_chunks.
-- These come from the documents table and are written by the chunk migration
-- script. Having them on chunks avoids a JOIN in the hot retrieval path.
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS relative_path TEXT;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS tema TEXT;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS subtema TEXT;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS tipo_de_documento TEXT;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS tipo_de_consulta TEXT;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS tipo_de_accion TEXT;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS tipo_de_riesgo TEXT;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS trust_tier TEXT;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS source_origin TEXT;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS nivel_practicidad TEXT;

-- Step 2: FTS-scored pre-filter function.
-- Uses OR-based FTS (plainto_tsquery with ' | ' for broad recall).
-- Hard-filters: topic, pais, vigencia, retrieval_visibility (pushed to WHERE).
-- Quality-filters: excludes backstage_only (matches JSONL _metadata_filtered_candidates).
-- FTS padding: if FTS returns < result_limit/2, pads with metadata-sorted rows.
CREATE OR REPLACE FUNCTION fts_scored_prefilter(
    search_query TEXT,
    topic_list TEXT[],
    country TEXT DEFAULT 'colombia',
    result_limit INTEGER DEFAULT 4000
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
    fts_rank REAL
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    fts_count INTEGER;
    pad_limit INTEGER;
BEGIN
    -- Main FTS-scored query: OR-based for broad recall
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
        ts_rank_cd(dc.search_vector, plainto_tsquery('spanish', search_query))::REAL AS fts_rank
    FROM document_chunks dc
    WHERE dc.search_vector @@ plainto_tsquery('spanish', search_query)
      AND (array_length(topic_list, 1) IS NULL OR dc.topic = ANY(topic_list))
      AND dc.pais = country
      AND COALESCE(dc.vigencia, '') NOT IN ('derogada', 'proyecto')
      AND COALESCE(dc.retrieval_visibility, '') <> 'backstage_only'
    ORDER BY ts_rank_cd(dc.search_vector, plainto_tsquery('spanish', search_query)) DESC
    LIMIT result_limit;

    -- Check how many FTS results we got
    GET DIAGNOSTICS fts_count = ROW_COUNT;

    -- If FTS returned fewer than half the limit, pad with metadata-sorted rows
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
            0.0::REAL AS fts_rank
        FROM document_chunks dc
        WHERE (array_length(topic_list, 1) IS NULL OR dc.topic = ANY(topic_list))
          AND dc.pais = country
          AND COALESCE(dc.vigencia, '') NOT IN ('derogada', 'proyecto')
          AND COALESCE(dc.retrieval_visibility, '') <> 'backstage_only'
          -- Exclude rows already returned by FTS
          AND NOT dc.search_vector @@ plainto_tsquery('spanish', search_query)
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

-- Grant access to all Supabase roles
GRANT EXECUTE ON FUNCTION fts_scored_prefilter TO authenticated;
GRANT EXECUTE ON FUNCTION fts_scored_prefilter TO anon;
GRANT EXECUTE ON FUNCTION fts_scored_prefilter TO service_role;
