-- fixplan_v3 §0.3.1 Table 2 + §0.3.4 step 2.
--
-- Append-only state-transition history. Corrections never UPDATE; they
-- INSERT a new row that supersedes via `superseded_by_record`. UPDATE/DELETE
-- are blocked at the role grant level — only superuser migrations may DROP
-- the table.
--
-- `state_from` is the LEGAL effective date (NOT extracted_at). For
-- retroactive inexequibilidades, this can be earlier than extracted_at.
--
-- Reversibility: R3 — `REVOKE … ; DROP TABLE norm_vigencia_history CASCADE`.

CREATE TABLE IF NOT EXISTS public.norm_vigencia_history (
    record_id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    norm_id                text NOT NULL REFERENCES public.norms(norm_id) ON DELETE CASCADE,
    state                  text NOT NULL,
    state_from             date NOT NULL,
    state_until            date,
    applies_to_kind        text NOT NULL,
    applies_to_payload     jsonb NOT NULL DEFAULT '{}'::jsonb,
    change_source          jsonb NOT NULL,
    veredicto              jsonb NOT NULL,
    fuentes_primarias      jsonb NOT NULL DEFAULT '[]'::jsonb,
    interpretive_constraint jsonb,
    extracted_via          jsonb NOT NULL,
    extracted_at           timestamptz NOT NULL DEFAULT now(),
    extracted_by           text NOT NULL,
    superseded_by_record   uuid REFERENCES public.norm_vigencia_history(record_id) ON DELETE SET NULL,
    supersede_reason       text,

    CONSTRAINT nvh_state_valid CHECK (
        state IN ('V', 'VM', 'DE', 'DT', 'SP', 'IE', 'EC', 'VC', 'VL', 'DI', 'RV')
    ),
    CONSTRAINT nvh_applies_to_kind_valid CHECK (
        applies_to_kind IN ('always', 'per_year', 'per_period')
    ),
    CONSTRAINT nvh_state_until_after_from CHECK (
        state_until IS NULL OR state_until >= state_from
    ),
    CONSTRAINT nvh_change_source_has_type CHECK (
        change_source ? 'type'
    ),
    -- For non-V states, change_source.source_norm_id is mandatory.
    CONSTRAINT nvh_change_source_has_source_norm_for_non_v CHECK (
        state = 'V' OR (change_source ? 'source_norm_id' AND change_source->>'source_norm_id' <> '')
    ),
    CONSTRAINT nvh_extracted_by_valid CHECK (
        extracted_by = 'cron@v1'
        OR extracted_by = 'ingest@v1'
        OR extracted_by LIKE 'manual_sme:%'
        OR extracted_by = 'v2_to_v3_upgrade'
    ),
    CONSTRAINT nvh_supersede_reason_valid CHECK (
        supersede_reason IS NULL OR supersede_reason IN (
            'periodic_reverify',
            'reform_trigger',
            'cascade_reviviscencia',
            'sme_correction',
            'contradiction_detected',
            'partial_coverage_followup'
        )
    )
);

-- Append-only enforcement.
-- The "writers" role (production app) gets INSERT + SELECT only.
-- Migrations run as superuser; the application can never UPDATE or DELETE.
-- service_role is used by Supabase clients for trusted server-side writes.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        REVOKE UPDATE, DELETE ON public.norm_vigencia_history FROM service_role;
        GRANT  INSERT, SELECT ON public.norm_vigencia_history TO   service_role;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE UPDATE, DELETE ON public.norm_vigencia_history FROM authenticated;
        GRANT SELECT ON public.norm_vigencia_history TO authenticated;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON public.norm_vigencia_history FROM anon;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_nvh_norm_state_from
    ON public.norm_vigencia_history(norm_id, state_from DESC);
CREATE INDEX IF NOT EXISTS idx_nvh_supersede
    ON public.norm_vigencia_history(superseded_by_record)
    WHERE superseded_by_record IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_nvh_change_source_id
    ON public.norm_vigencia_history((change_source->>'source_norm_id'))
    WHERE change_source ? 'source_norm_id';
CREATE INDEX IF NOT EXISTS idx_nvh_extracted_via_run_id
    ON public.norm_vigencia_history((extracted_via->>'run_id'))
    WHERE extracted_via ? 'run_id';

COMMENT ON TABLE public.norm_vigencia_history IS
    'fixplan_v3 §0.3.1 Table 2 — append-only vigencia history per norm. UPDATE/DELETE forbidden at role grant level.';
