-- Expert-summary overrides: durable crux curation for expert panel.

CREATE TABLE IF NOT EXISTS expert_summary_overrides (
    override_key   TEXT PRIMARY KEY,
    logical_doc_id TEXT NOT NULL,
    provider_name  TEXT NOT NULL,
    source_hash    TEXT NOT NULL,
    summary_text   TEXT NOT NULL,
    summary_origin TEXT NOT NULL DEFAULT 'llm',
    summary_quality TEXT NOT NULL DEFAULT 'high',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_expert_summary_overrides_lookup
    ON expert_summary_overrides (logical_doc_id, provider_name, source_hash);

DROP TRIGGER IF EXISTS trg_expert_summary_overrides_updated ON expert_summary_overrides;
CREATE TRIGGER trg_expert_summary_overrides_updated
    BEFORE UPDATE ON expert_summary_overrides
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
