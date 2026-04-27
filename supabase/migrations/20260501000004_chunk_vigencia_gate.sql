-- fixplan_v3 sub-fix 1B-ε — the v3 retriever-side vigencia gate.
--
-- For each candidate chunk_id returned by hybrid_search, this RPC returns
-- the anchor's vigencia state at the requested date OR period, plus the
-- demotion factor the retriever multiplies into the chunk's RRF score.
--
-- This is layered on top of (not in place of) the existing hybrid_search.
-- The retriever calls hybrid_search first, then this RPC with the chunk_ids;
-- chunks whose anchor returns demotion_factor = 0 are filtered out, and the
-- rest get their score multiplied.
--
-- Rationale: keeping `hybrid_search` untouched preserves the v2 binary
-- filter while we ramp up `norm_citations` coverage. Once 1B-δ backfill
-- hits ≥ 95% chunks-with-citations (the §2.5 success criterion), we flip
-- the retriever to use this RPC as the primary gate and turn off the
-- legacy `vigencia` column filter via a follow-up migration.
--
-- Reversibility: R3 — DROP FUNCTION (idempotent on re-deploy).

DROP FUNCTION IF EXISTS public.chunk_vigencia_gate_at_date(text[], date) CASCADE;
DROP FUNCTION IF EXISTS public.chunk_vigencia_gate_for_period(text[], text, integer, text) CASCADE;


CREATE FUNCTION public.chunk_vigencia_gate_at_date(
    chunk_ids   text[],
    as_of_date  date
)
RETURNS TABLE (
    chunk_id            text,
    norm_id             text,
    role                text,
    anchor_strength     text,
    state               text,
    state_from          date,
    state_until         date,
    record_id           uuid,
    interpretive_constraint jsonb,
    demotion_factor     numeric
)
LANGUAGE sql
STABLE
AS $$
    WITH cites AS (
        SELECT nc.chunk_id, nc.norm_id, nc.role, nc.anchor_strength
        FROM public.norm_citations nc
        WHERE nc.chunk_id = ANY(chunk_ids)
    )
    SELECT
        c.chunk_id,
        c.norm_id,
        c.role,
        c.anchor_strength,
        v.state,
        v.state_from,
        v.state_until,
        v.record_id,
        v.interpretive_constraint,
        v.demotion_factor
    FROM cites c
    LEFT JOIN public.norm_vigencia_at_date(as_of_date) v
        ON v.norm_id = c.norm_id;
$$;

COMMENT ON FUNCTION public.chunk_vigencia_gate_at_date(text[], date) IS
    'fixplan_v3 §1B-ε — return per-chunk vigencia state at as_of_date for retriever-side demotion.';


CREATE FUNCTION public.chunk_vigencia_gate_for_period(
    chunk_ids     text[],
    impuesto      text,
    periodo_year  integer,
    periodo_label text DEFAULT NULL
)
RETURNS TABLE (
    chunk_id                  text,
    norm_id                   text,
    role                      text,
    anchor_strength           text,
    state                     text,
    state_from                date,
    state_until               date,
    record_id                 uuid,
    interpretive_constraint   jsonb,
    norm_version_aplicable    text,
    demotion_factor           numeric,
    art_338_cp_applied        boolean
)
LANGUAGE sql
STABLE
AS $$
    WITH cites AS (
        SELECT nc.chunk_id, nc.norm_id, nc.role, nc.anchor_strength
        FROM public.norm_citations nc
        WHERE nc.chunk_id = ANY(chunk_ids)
    )
    SELECT
        c.chunk_id,
        c.norm_id,
        c.role,
        c.anchor_strength,
        v.state,
        v.state_from,
        v.state_until,
        v.record_id,
        v.interpretive_constraint,
        v.norm_version_aplicable,
        v.demotion_factor,
        v.art_338_cp_applied
    FROM cites c
    LEFT JOIN public.norm_vigencia_for_period(impuesto, periodo_year, periodo_label) v
        ON v.norm_id = c.norm_id;
$$;

COMMENT ON FUNCTION public.chunk_vigencia_gate_for_period(text[], text, integer, text) IS
    'fixplan_v3 §1B-ε — period-aware retriever gate (Art. 338 CP).';
