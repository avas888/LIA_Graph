-- Phase 1: Session persistence tables
-- Source dataclasses: ConversationSession, ConversationTurn, FeedbackRecord,
--                     Contribution, clarification_session_store

-- ENUMs -----------------------------------------------------------------

CREATE TYPE feedback_tag AS ENUM (
    'precisa',
    'practica',
    'incompleta',
    'desactualizada',
    'confusa'
);

CREATE TYPE contribution_status AS ENUM (
    'pending',
    'approved',
    'rejected'
);

-- Tables ----------------------------------------------------------------

-- conversations (source: ConversationSession)
CREATE TABLE conversations (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   TEXT        NOT NULL UNIQUE,
    tenant_id    TEXT        NOT NULL,
    accountant_id TEXT       NOT NULL,
    topic        TEXT,
    pais         TEXT        NOT NULL DEFAULT 'colombia',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- conversation_turns (source: ConversationTurn)
CREATE TABLE conversation_turns (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     UUID        NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role                TEXT        NOT NULL,
    content             TEXT        NOT NULL,
    layer_contributions JSONB,
    trace_id            TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- clarification_sessions (source: clarification_session_store.py)
CREATE TABLE clarification_sessions (
    session_id   TEXT PRIMARY KEY,
    state        JSONB       NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '2 hours')
);

-- feedback (source: FeedbackRecord)
CREATE TABLE feedback (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id            TEXT        NOT NULL,
    session_id          TEXT,
    rating              INTEGER     NOT NULL CHECK (rating BETWEEN 1 AND 5),
    tags                feedback_tag[] NOT NULL DEFAULT '{}',
    comment             TEXT        NOT NULL DEFAULT '',
    docs_used           TEXT[]      NOT NULL DEFAULT '{}',
    layer_contributions JSONB       NOT NULL DEFAULT '{}',
    pain_detected       TEXT        NOT NULL DEFAULT '',
    task_detected       TEXT        NOT NULL DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- contributions (source: Contribution)
CREATE TABLE contributions (
    contribution_id TEXT PRIMARY KEY,
    topic           TEXT                NOT NULL,
    content_markdown TEXT               NOT NULL,
    authority_claim TEXT                NOT NULL,
    submitter_id    TEXT                NOT NULL,
    tenant_id       TEXT                NOT NULL,
    status          contribution_status NOT NULL DEFAULT 'pending',
    review_comment  TEXT                NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ         NOT NULL DEFAULT now(),
    reviewed_at     TIMESTAMPTZ
);

-- Indexes ---------------------------------------------------------------

CREATE INDEX idx_conversations_tenant     ON conversations (tenant_id);
CREATE INDEX idx_conversations_session    ON conversations (session_id);
CREATE INDEX idx_turns_conversation       ON conversation_turns (conversation_id);
CREATE INDEX idx_turns_trace              ON conversation_turns (trace_id);
CREATE INDEX idx_clarification_expires    ON clarification_sessions (expires_at);
CREATE INDEX idx_clarification_session    ON clarification_sessions (session_id);
CREATE INDEX idx_feedback_trace           ON feedback (trace_id);
CREATE INDEX idx_feedback_session         ON feedback (session_id);
CREATE INDEX idx_contributions_status     ON contributions (status);
CREATE INDEX idx_contributions_tenant     ON contributions (tenant_id);

-- Auto-update updated_at trigger ----------------------------------------

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_conversations_updated
    BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_clarification_updated
    BEFORE UPDATE ON clarification_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
