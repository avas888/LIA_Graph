-- End-to-end chat run telemetry and resume state.

CREATE TABLE IF NOT EXISTS chat_runs (
    chat_run_id                TEXT PRIMARY KEY,
    trace_id                   TEXT NOT NULL DEFAULT '',
    session_id                 TEXT NOT NULL DEFAULT '',
    client_turn_id             TEXT NOT NULL DEFAULT '',
    request_fingerprint        TEXT NOT NULL,
    endpoint                   TEXT NOT NULL DEFAULT '/api/chat',
    tenant_id                  TEXT,
    user_id                    TEXT,
    company_id                 TEXT,
    status                     TEXT NOT NULL DEFAULT 'running',
    pipeline_run_id            TEXT,
    request_payload            JSONB NOT NULL DEFAULT '{}',
    response_payload           JSONB NOT NULL DEFAULT '{}',
    error_payload              JSONB NOT NULL DEFAULT '{}',
    request_received_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    pipeline_started_at        TIMESTAMPTZ,
    first_model_delta_at       TIMESTAMPTZ,
    first_visible_answer_at    TIMESTAMPTZ,
    pipeline_completed_at      TIMESTAMPTZ,
    final_payload_ready_at     TIMESTAMPTZ,
    response_sent_at           TIMESTAMPTZ,
    async_persistence_done_at  TIMESTAMPTZ,
    completed_at               TIMESTAMPTZ,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_run_events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_run_id   TEXT NOT NULL REFERENCES chat_runs(chat_run_id) ON DELETE CASCADE,
    event_index   INTEGER NOT NULL,
    event_payload JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (chat_run_id, event_index)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_runs_request_fingerprint
    ON chat_runs (request_fingerprint);

CREATE INDEX IF NOT EXISTS idx_chat_runs_created
    ON chat_runs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_runs_trace
    ON chat_runs (trace_id);

CREATE INDEX IF NOT EXISTS idx_chat_runs_session
    ON chat_runs (session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_run_events_run
    ON chat_run_events (chat_run_id, event_index);

DROP TRIGGER IF EXISTS trg_chat_runs_updated ON chat_runs;
CREATE TRIGGER trg_chat_runs_updated
    BEFORE UPDATE ON chat_runs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE pipeline_c_runs
    ADD COLUMN IF NOT EXISTS chat_run_id TEXT REFERENCES chat_runs(chat_run_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_pipeline_c_runs_chat_run
    ON pipeline_c_runs (chat_run_id);
