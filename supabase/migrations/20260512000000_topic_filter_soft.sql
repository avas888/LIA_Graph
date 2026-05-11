-- fix_v7_may §3a — Decouple topic boost from filter_topic.
--
-- Background. Migration `20260427000000_topic_boost.sql` introduced
-- `filter_topic_boost` but kept the score-multiplier CASE coupled to
-- `filter_topic`: the boost only fires when `filter_topic IS NOT NULL`.
-- That coupling forced callers wanting a soft topic ranking signal to
-- ALSO pass `filter_topic`, which previously selected the WHERE
-- recall predicate. The result on staging is that cross-topic anchors
-- can drop out of the candidate set whenever the cloud-side
-- `hybrid_search` is on a version that does not have the
-- `OR effective_topic_boost > 1.0` short-circuit applied to the
-- WHERE clause (the 0427 migration adds it, but cloud drift cannot
-- be ruled out, and the orchestration.md §4.1 invariant is
-- unambiguous: topic is a ranking signal, NEVER a WHERE predicate
-- for the chat path).
--
-- Fix. Introduce a NEW parameter `boost_topic` (default NULL) that
-- is the soft-boost target — entirely independent from
-- `filter_topic`. The chat retriever now passes `filter_topic=NULL`
-- always (so no chunks can be hard-filtered out by topic) AND
-- `boost_topic=router_topic` to keep narrow topics ranking above
-- umbrellas. Hard-filter callers (admin / backstage utilities) can
-- still pass `filter_topic=<topic>` and get the recall predicate;
-- they just opt in explicitly.
--
-- Invariant I5 (never penalize): both boosts coerced to >= 1.0.
-- Invariant from docs/orchestration/orchestration.md §4.1: topic is
-- ranking signal, not WHERE filter — enforced here by giving the
-- chat path a parameter that boosts without filtering.

-- Drop ALL prior overloads explicitly per fix_v5 §1.G postmortem
-- (PostgREST chooses the wrong overload when ambiguity exists).
DROP FUNCTION IF EXISTS "public"."hybrid_search"(
    "extensions"."vector", "text", "text", "text", integer,
    integer, double precision, double precision, "text", "text",
    "text", "date", "text", double precision, double precision
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
    "boost_topic"                "text"             DEFAULT NULL::"text"
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
BEGIN
    IF fts_query IS NOT NULL AND fts_query <> '' THEN
        effective_tsq := to_tsquery('spanish', fts_query);
    ELSE
        effective_tsq := plainto_tsquery('spanish', query_text);
    END IF;

    -- Invariant I5: never penalize. Boost < 1.0 is coerced to 1.0.
    effective_subtopic_boost := GREATEST(COALESCE(subtopic_boost, 1.0), 1.0);
    effective_topic_boost    := GREATEST(COALESCE(filter_topic_boost, 1.0), 1.0);

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
          -- fix_v7 §3a: filter_topic is HARD filter only; chat path passes NULL.
          -- boost_topic (below in the score CASE) is the soft signal — no WHERE.
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
                -- fix_v7 §3a — soft topic boost. Decoupled from
                -- filter_topic so cross-topic chunks stay reachable
                -- when filter_topic is NULL but the caller still wants
                -- the routed topic to rank higher.
                CASE
                    WHEN boost_topic IS NOT NULL
                         AND COALESCE(f.topic, s.topic) = boost_topic
                    THEN effective_topic_boost
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
