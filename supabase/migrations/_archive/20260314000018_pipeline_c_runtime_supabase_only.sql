-- Strict Supabase runtime state for Pipeline C.
-- Removes chunk-level SHA uniqueness that blocks valid duplicate text across docs
-- and migrates mutable runtime stores off local filesystem authority.

ALTER TABLE document_chunks
    DROP CONSTRAINT IF EXISTS document_chunks_chunk_sha256_key;

CREATE TABLE IF NOT EXISTS terms_acceptance_state (
    state_key                      TEXT PRIMARY KEY,
    accepted_version               TEXT NOT NULL DEFAULT '',
    accepted_enforcement_revision  INTEGER NOT NULL DEFAULT 0,
    accepted_at_utc                TIMESTAMPTZ,
    accepted_by                    TEXT NOT NULL DEFAULT '',
    operator                       TEXT NOT NULL DEFAULT '',
    updated_at                     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orchestration_settings (
    scope          TEXT PRIMARY KEY,
    document       JSONB NOT NULL DEFAULT '{}',
    schema_version TEXT NOT NULL DEFAULT '',
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS chat_session_metrics (
    session_id             TEXT PRIMARY KEY,
    turn_count             INTEGER NOT NULL DEFAULT 0,
    token_usage_total      JSONB NOT NULL DEFAULT '{}',
    llm_token_usage_total  JSONB NOT NULL DEFAULT '{}',
    last_trace_id          TEXT,
    last_run_id            TEXT,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS citation_gap_registry (
    reference_key         TEXT PRIMARY KEY,
    reference_text        TEXT NOT NULL DEFAULT '',
    reference_type        TEXT NOT NULL DEFAULT '',
    seen_count_total      INTEGER NOT NULL DEFAULT 0,
    seen_count_user       INTEGER NOT NULL DEFAULT 0,
    seen_count_assistant  INTEGER NOT NULL DEFAULT 0,
    first_seen_at         TIMESTAMPTZ,
    last_seen_at          TIMESTAMPTZ,
    last_trace_id         TEXT,
    last_session_id       TEXT,
    last_topic            TEXT,
    last_pais             TEXT,
    samples               JSONB NOT NULL DEFAULT '[]',
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS doc_utility_scores (
    doc_id         TEXT PRIMARY KEY,
    use_count      INTEGER NOT NULL DEFAULT 0,
    rating_sum     INTEGER NOT NULL DEFAULT 0,
    rating_count   INTEGER NOT NULL DEFAULT 0,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pipeline_c_runs (
    run_id             TEXT PRIMARY KEY,
    trace_id           TEXT NOT NULL DEFAULT '',
    status             TEXT NOT NULL DEFAULT 'running',
    started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at           TIMESTAMPTZ,
    request_snapshot   JSONB NOT NULL DEFAULT '{}',
    summary            JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS pipeline_c_run_events (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id        TEXT NOT NULL REFERENCES pipeline_c_runs(run_id) ON DELETE CASCADE,
    event_index   INTEGER NOT NULL,
    event_payload JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, event_index)
);

CREATE INDEX IF NOT EXISTS idx_chat_session_metrics_updated
    ON chat_session_metrics (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_citation_gap_registry_last_seen
    ON citation_gap_registry (last_seen_at DESC, seen_count_total DESC);

CREATE INDEX IF NOT EXISTS idx_doc_utility_scores_updated
    ON doc_utility_scores (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_c_runs_started
    ON pipeline_c_runs (started_at DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_c_runs_trace
    ON pipeline_c_runs (trace_id);

CREATE INDEX IF NOT EXISTS idx_pipeline_c_run_events_run
    ON pipeline_c_run_events (run_id, event_index);

DROP TRIGGER IF EXISTS trg_terms_acceptance_state_updated ON terms_acceptance_state;
CREATE TRIGGER trg_terms_acceptance_state_updated
    BEFORE UPDATE ON terms_acceptance_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_orchestration_settings_updated ON orchestration_settings;
CREATE TRIGGER trg_orchestration_settings_updated
    BEFORE UPDATE ON orchestration_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_chat_session_metrics_updated ON chat_session_metrics;
CREATE TRIGGER trg_chat_session_metrics_updated
    BEFORE UPDATE ON chat_session_metrics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_citation_gap_registry_updated ON citation_gap_registry;
CREATE TRIGGER trg_citation_gap_registry_updated
    BEFORE UPDATE ON citation_gap_registry
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_doc_utility_scores_updated ON doc_utility_scores;
CREATE TRIGGER trg_doc_utility_scores_updated
    BEFORE UPDATE ON doc_utility_scores
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
