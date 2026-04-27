-- fixplan_v3 sub-fix 1F — re-verify queue (cascade orchestrator host).
--
-- Single-writer (the cron) drains; producers are:
--   * `VigenciaCascadeOrchestrator.on_history_row_inserted` (post-INSERT hook)
--   * `VigenciaCascadeOrchestrator.on_periodic_tick`        (6h sweep)
--   * `VigenciaCascadeOrchestrator.queue_reverify`          (Fix 3 hook)
--
-- Reversibility: R3 — DROP TABLE (rebuildable from norm_vigencia_history).

CREATE TABLE IF NOT EXISTS public.vigencia_reverify_queue (
    queue_id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    norm_id               text NOT NULL,
    supersede_reason      text NOT NULL,
    triggering_norm_id    text,
    triggering_record_id  uuid REFERENCES public.norm_vigencia_history(record_id) ON DELETE SET NULL,
    enqueued_at           timestamptz NOT NULL DEFAULT now(),
    processed_at          timestamptz,
    skipped               boolean NOT NULL DEFAULT false,
    skip_reason           text,

    CONSTRAINT vrq_supersede_reason_valid CHECK (
        supersede_reason IN (
            'periodic_reverify',
            'reform_trigger',
            'cascade_reviviscencia',
            'sme_correction',
            'contradiction_detected',
            'partial_coverage_followup'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_vrq_pending
    ON public.vigencia_reverify_queue(enqueued_at)
    WHERE processed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_vrq_norm_id
    ON public.vigencia_reverify_queue(norm_id);

COMMENT ON TABLE public.vigencia_reverify_queue IS
    'fixplan_v3 §1F — cascade re-verify queue. Single-writer (cron); rebuildable.';
