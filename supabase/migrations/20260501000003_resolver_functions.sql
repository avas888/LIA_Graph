-- fixplan_v3 §0.3.4 step 4 + §0.6 — resolver functions.
--
-- Two resolvers, picked by the planner:
--   * `norm_vigencia_at_date(D)` — instantaneous-tax / procedimiento queries.
--   * `norm_vigencia_for_period(impuesto, year, periodo_label)` — impuestos
--     de período. Honors Art. 338 CP via the row's `applies_to_payload` and
--     `applies_to_kind`.
--
-- Per `docs/learnings/retrieval/hybrid_search-overload-2026-04-27.md`: explicit
-- DROP FUNCTION IF EXISTS before each CREATE OR REPLACE prevents silent
-- overload.

DROP FUNCTION IF EXISTS public.norm_vigencia_at_date(date) CASCADE;
DROP FUNCTION IF EXISTS public.norm_vigencia_for_period(text, integer, text) CASCADE;

CREATE FUNCTION public.norm_vigencia_at_date(as_of_date date)
RETURNS TABLE (
    norm_id                 text,
    state                   text,
    state_from              date,
    state_until             date,
    record_id               uuid,
    change_source           jsonb,
    interpretive_constraint jsonb,
    demotion_factor         numeric
)
LANGUAGE sql
STABLE
AS $$
    SELECT DISTINCT ON (h.norm_id)
        h.norm_id,
        h.state,
        h.state_from,
        h.state_until,
        h.record_id,
        h.change_source,
        h.interpretive_constraint,
        CASE h.state
            WHEN 'V'  THEN 1.0
            WHEN 'VM' THEN 1.0
            WHEN 'DE' THEN 0.0
            WHEN 'DT' THEN 0.3
            WHEN 'SP' THEN 0.0
            WHEN 'IE' THEN 0.0
            WHEN 'EC' THEN 1.0
            WHEN 'VC' THEN 1.0
            WHEN 'VL' THEN 0.0
            WHEN 'DI' THEN 1.0
            WHEN 'RV' THEN 1.0
            ELSE          0.0
        END::numeric AS demotion_factor
    FROM public.norm_vigencia_history h
    WHERE h.state_from <= as_of_date
      AND (h.state_until IS NULL OR h.state_until > as_of_date)
      AND h.superseded_by_record IS NULL
    ORDER BY h.norm_id, h.state_from DESC, h.extracted_at DESC;
$$;

COMMENT ON FUNCTION public.norm_vigencia_at_date(date) IS
    'fixplan_v3 §0.6 resolver 1 — returns the row whose [state_from, state_until) covers as_of_date. One row per norm.';


CREATE FUNCTION public.norm_vigencia_for_period(
    impuesto      text,
    periodo_year  integer,
    periodo_label text DEFAULT NULL
)
RETURNS TABLE (
    norm_id                  text,
    state                    text,
    state_from               date,
    state_until              date,
    record_id                uuid,
    change_source            jsonb,
    interpretive_constraint  jsonb,
    norm_version_aplicable   text,
    demotion_factor          numeric,
    art_338_cp_applied       boolean
)
LANGUAGE sql
STABLE
AS $$
    WITH candidates AS (
        SELECT
            h.norm_id,
            h.state,
            h.state_from,
            h.state_until,
            h.record_id,
            h.change_source,
            h.interpretive_constraint,
            h.applies_to_kind,
            h.applies_to_payload,
            COALESCE(h.applies_to_payload->>'norm_version_aplicable', NULL) AS norm_version_aplicable,
            COALESCE((h.applies_to_payload->>'art_338_cp_shift')::boolean, false) AS art_338_cp_applied
        FROM public.norm_vigencia_history h
        WHERE h.superseded_by_record IS NULL
          AND (
              h.applies_to_kind = 'always'
              OR (
                  h.applies_to_kind = 'per_year'
                  AND COALESCE((h.applies_to_payload->>'year_start')::int, -2147483648) <= periodo_year
                  AND COALESCE((h.applies_to_payload->>'year_end')::int,    2147483647)  >= periodo_year
              )
              OR (
                  h.applies_to_kind = 'per_period'
                  AND (
                      h.applies_to_payload->>'impuesto' IS NULL
                      OR h.applies_to_payload->>'impuesto' = impuesto
                  )
                  AND (
                      h.applies_to_payload->>'period_start' IS NULL
                      OR (h.applies_to_payload->>'period_start')::date <= make_date(periodo_year, 12, 31)
                  )
                  AND (
                      h.applies_to_payload->>'period_end' IS NULL
                      OR (h.applies_to_payload->>'period_end')::date   >= make_date(periodo_year,  1,  1)
                  )
              )
          )
    )
    SELECT DISTINCT ON (norm_id)
        norm_id,
        state,
        state_from,
        state_until,
        record_id,
        change_source,
        interpretive_constraint,
        norm_version_aplicable,
        CASE state
            WHEN 'V'  THEN 1.0
            WHEN 'VM' THEN 1.0
            WHEN 'DE' THEN 0.0
            WHEN 'DT' THEN 0.3
            WHEN 'SP' THEN 0.0
            WHEN 'IE' THEN 0.0
            WHEN 'EC' THEN 1.0
            WHEN 'VC' THEN 1.0
            WHEN 'VL' THEN 0.0
            WHEN 'DI' THEN 1.0
            WHEN 'RV' THEN 1.0
            ELSE          0.0
        END::numeric AS demotion_factor,
        art_338_cp_applied
    FROM candidates
    ORDER BY norm_id, state_from DESC;
$$;

COMMENT ON FUNCTION public.norm_vigencia_for_period(text, integer, text) IS
    'fixplan_v3 §0.6 resolver 2 — period-aware (Art. 338 CP). Filters by applies_to_kind and applies_to_payload.';
