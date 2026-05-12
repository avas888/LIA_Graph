-- fix_v12_may §2.C — knowledge_class boost in hybrid_search.
--
-- Background. fix_v10_may Phase 10A retagged 1,463 cloud chunks to
-- `knowledge_class='practica_erp'` (operational guidance: pasos,
-- plazos, errores típicos, soportes). They coexist with ~10x more
-- `normative_base` chunks per subtopic, so the latter dominate top-K
-- in raw RRF ranking. The chat assembler's `build_recommendations`
-- + `extend_from_support_insights` falls through to article-derived
-- bullets when práctica chunks are scarce, which makes the
-- `**Recomendaciones Prácticas**` lead section (Phase 12A rename)
-- read like normative recitation instead of operative steps.
--
-- Fix. Add a soft, multiplicative boost for chunks whose
-- `knowledge_class` matches a caller-specified target. Mirrors the
-- shape of `boost_topic` / `filter_topic_boost` (fix_v7 §3a +
-- migration `20260512000000_topic_filter_soft.sql`): boost is a
-- ranking signal, NEVER a WHERE predicate — every chunk stays
-- reachable, práctica chunks just rank relatively higher when the
-- caller opts in. The default factor `LIA_PRACTICA_BOOST_FACTOR=1.5`
-- is comparable to the topic-boost and subtopic-boost factors.
--
-- Invariant I5 (never penalize): boost coerced to >= 1.0. Setting
-- `knowledge_class_boost=1.0` is the explicit OFF position.
--
-- Backwards compatibility. The chat retriever
-- (`pipeline_d/retriever_supabase.py`) strips both `boost_knowledge_class`
-- and `knowledge_class_boost` from the RPC payload on the
-- "first_attempt_error" recovery path, alongside `boost_topic` /
-- `filter_topic_boost`. Older deployments without this migration
-- continue to serve unboosted retrieval — degraded ranking, never
-- broken recall.

-- Drop ALL prior overloads explicitly per fix_v5 §1.G postmortem
-- (PostgREST chooses the wrong overload when ambiguity exists).
DROP FUNCTION IF EXISTS "public"."hybrid_search"(
    "extensions"."vector", "text", "text", "text", integer,
    integer, double precision, double precision, "text", "text",
    "text", "date", "text", double precision, double precision,
    "text"
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
    "subtopic_boost"             double precision   DEFAULT 1.5,
    "filter_topic_boost"         double precision   DEFAULT 1.0,
    "boost_topic"                "text"             DEFAULT NULL::"text",
    "boost_knowledge_class"      "text"             DEFAULT NULL::"text",
    "knowledge_class_boost"      double precision   DEFAULT 1.0
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
    effective_subtopic_boost double precision;
    effective_topic_boost double precision;
    effective_knowledge_class_boost double precision;
BEGIN
    IF fts_query IS NOT NULL AND fts_query <> '' THEN
        effective_tsq := to_tsquery('spanish', fts_query);
    ELSE
        effective_tsq := plainto_tsquery('spanish', query_text);
    END IF;

    -- Invariant I5: never penalize. Boost < 1.0 is coerced to 1.0.
    effective_subtopic_boost        := GREATEST(COALESCE(subtopic_boost, 1.0), 1.0);
    effective_topic_boost           := GREATEST(COALESCE(filter_topic_boost, 1.0), 1.0);
    effective_knowledge_class_boost := GREATEST(COALESCE(knowledge_class_boost, 1.0), 1.0);

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
          AND (
              filter_topic IS NULL
              OR dc.topic IN (filter_topic, filter_topic || '_parametros')
          )
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
            (1 - (dc.embedding <=> query_embedding)) AS similarity,
            ROW_NUMBER() OVER (ORDER BY (1 - (dc.embedding <=> query_embedding)) DESC) AS rn
        FROM document_chunks dc
        WHERE dc.embedding IS NOT NULL
          AND (
              filter_topic IS NULL
              OR dc.topic IN (filter_topic, filter_topic || '_parametros')
          )
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
        ORDER BY similarity DESC
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
                    THEN effective_subtopic_boost
                    ELSE 1.0
                END
                *
                CASE
                    WHEN boost_topic IS NOT NULL
                         AND COALESCE(f.topic, s.topic) = boost_topic
                    THEN effective_topic_boost
                    ELSE 1.0
                END
                *
                -- fix_v12 §2.C — soft knowledge_class boost. Decoupled
                -- from filter_knowledge_class (which is the hard
                -- recall filter). Lets the chat path raise the
                -- relative rank of `practica_erp` chunks so
                -- `**Recomendaciones Prácticas**` has práctica
                -- substance instead of article-derived bullets in
                -- normative voice, without excluding normative
                -- chunks from recall.
                CASE
                    WHEN boost_knowledge_class IS NOT NULL
                         AND COALESCE(f.knowledge_class, s.knowledge_class) = boost_knowledge_class
                    THEN effective_knowledge_class_boost
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
