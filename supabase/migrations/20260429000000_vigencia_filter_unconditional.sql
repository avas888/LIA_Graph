-- Activity 1 — Surgical "Fix 1D-zero": stop bypassing the vigencia filter.
--
-- Background
-- ----------
-- The hybrid_search function (latest version: 20260427000000_topic_boost.sql,
-- the §1.D `filter_topic_boost` variant) excludes chunks where
-- `vigencia IN ('derogada', 'proyecto', 'suspendida')` — but ONLY when
-- `filter_effective_date_max IS NULL`. When the planner passes a temporal
-- cutoff (which `pipeline_d/retriever_supabase.py:171` does whenever
-- `plan.temporal_context.cutoff_date` is set, i.e. the common case), the
-- vigencia exclusion is silently SKIPPED.
--
-- The original intent of the bypass: support "what was vigente on date X?"
-- historical-context queries by returning then-vigente-but-now-derogated
-- articles. In practice that pathway is unused (the planner doesn't
-- explicitly request historical context; cutoff_date is set from a generic
-- temporal_context that's almost always today's date or None). What it
-- ACTUALLY does today is silently disable the derogada filter for nearly
-- every retrieval.
--
-- The §1.G SME validation surfaced this: 4+ answers cited art. 689-1 ET
-- (derogated 2021), Ley-1429-2010 appears as a citation in nearly every
-- refusal, and the binary `vigencia` flag (set by the parser regex) is
-- being silently bypassed in production.
--
-- Surgical fix
-- ------------
-- Drop the bypass. The vigencia exclusion now applies unconditionally —
-- regardless of `filter_effective_date_max`. Historical-context queries
-- via planner-driven `vigencia_at_date` signal will be added in Fix 1D
-- (next_v6 §… — not in this migration).
--
-- Why this is safe
-- ----------------
-- * The arg list is UNCHANGED — `CREATE OR REPLACE FUNCTION` replaces in
--   place, no new overload created (per the
--   `hybrid_search-overload-2026-04-27` learning).
-- * The temporal date filter (`dc.effective_date <= filter_effective_date_max`)
--   STAYS — historical-cutoff for vigente articles still works.
-- * The §1.D `filter_topic_boost` semantics are PRESERVED.
-- * Reversible: re-applying `20260427000000_topic_boost.sql` restores the
--   bypass.
--
-- Measurable impact (gate-3 numeric criteria)
-- -------------------------------------------
-- After applying + re-running §1.G:
--   * `art. 689-1` citations:  4+ → ≤ 1   (binding pass)
--   * `Ley 1429/2010` citations:  12+ → ≤ 5   (binding pass; some uses are
--      legitimate intro/historical references, hence not 0)
--   * `served_acceptable+` count: ≥ 21/36 (current baseline; must not drop)
--   * Zero answers move from 🟨/🟢 to 🚫 (must not make things worse)
--
-- Followup
-- --------
-- * Fix 1A (vigencia ontology) + Fix 1B (LLM extraction over 7,883 articles)
--   replace the binary `vigencia` flag with the structured Vigencia value
--   object. After Fix 1B, the per-document/per-article granularity becomes
--   sound and the surgical filter here remains valid.
-- * Fix 1D adds `vigencia_at_date` planner signal for historical-context
--   queries — re-introduces the bypass in a controlled, planner-driven way.

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
    "filter_topic_boost"         double precision   DEFAULT 1.0
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
          -- v5 §1.D: filter_topic is now a BOOST signal (see CTE
          -- `combined`), not a hard filter. Recall predicate stays as it
          -- was — narrow topic + parametros sub-bucket — but only when
          -- filter_topic_boost == 1.0 (caller wants strict filtering).
          -- When filter_topic_boost > 1.0, the caller wants a soft boost
          -- without losing other topics from recall, so we drop the WHERE
          -- clause.
          AND (
              filter_topic IS NULL
              OR effective_topic_boost > 1.0  -- soft boost mode: no WHERE filter
              OR dc.topic IN (filter_topic, filter_topic || '_parametros')
          )
          AND (filter_pais IS NULL OR dc.pais = filter_pais)
          AND (filter_knowledge_class IS NULL OR dc.knowledge_class = filter_knowledge_class)
          AND (filter_sync_generation IS NULL OR dc.sync_generation = filter_sync_generation)
          -- ACTIVITY 1 (2026-04-29) — vigencia filter applies UNCONDITIONALLY.
          -- The previous `filter_effective_date_max IS NOT NULL OR ...` bypass
          -- has been removed; historical-context queries will be supported via
          -- a planner-driven `vigencia_at_date` signal in Fix 1D.
          AND COALESCE(dc.vigencia, '') NOT IN ('derogada', 'proyecto', 'suspendida')
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
              OR effective_topic_boost > 1.0
              OR dc.topic IN (filter_topic, filter_topic || '_parametros')
          )
          AND (filter_pais IS NULL OR dc.pais = filter_pais)
          AND (filter_knowledge_class IS NULL OR dc.knowledge_class = filter_knowledge_class)
          AND (filter_sync_generation IS NULL OR dc.sync_generation = filter_sync_generation)
          -- ACTIVITY 1 (2026-04-29) — vigencia filter applies UNCONDITIONALLY.
          -- See FTS branch above for rationale.
          AND COALESCE(dc.vigencia, '') NOT IN ('derogada', 'proyecto', 'suspendida')
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
                -- v5 §1.D — topic boost composes multiplicatively with subtopic boost.
                CASE
                    WHEN filter_topic IS NOT NULL
                         AND COALESCE(f.topic, s.topic) = filter_topic
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
