-- Platform foundation: auth/embed, tenant-aware conversations, usage ledger, jobs.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'platform_role') THEN
        CREATE TYPE platform_role AS ENUM ('tenant_user', 'tenant_admin', 'platform_admin');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'usage_event_type') THEN
        CREATE TYPE usage_event_type AS ENUM ('turn_usage', 'llm_usage', 'admin_export', 'background_job');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'review_vote') THEN
        CREATE TYPE review_vote AS ENUM ('up', 'down', 'neutral');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_status') THEN
        CREATE TYPE job_status AS ENUM ('queued', 'running', 'completed', 'failed', 'cancelled');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS tenants (
    tenant_id    TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active',
    metadata     JSONB NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    user_id          TEXT PRIMARY KEY,
    external_user_id TEXT NOT NULL DEFAULT '',
    display_name     TEXT NOT NULL DEFAULT '',
    email            TEXT NOT NULL DEFAULT '',
    metadata         JSONB NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tenant_memberships (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    user_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role       platform_role NOT NULL DEFAULT 'tenant_user',
    metadata   JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, user_id)
);

CREATE TABLE IF NOT EXISTS companies (
    company_id    TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    display_name  TEXT NOT NULL,
    pais          TEXT NOT NULL DEFAULT 'colombia',
    status        TEXT NOT NULL DEFAULT 'active',
    metadata      JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_company_access (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    user_id     TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    company_id  TEXT NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    can_admin   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, user_id, company_id)
);

CREATE TABLE IF NOT EXISTS host_integrations (
    integration_id   TEXT PRIMARY KEY,
    tenant_id        TEXT REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    label            TEXT NOT NULL,
    allowed_origins  TEXT[] NOT NULL DEFAULT '{}',
    secret_env       TEXT NOT NULL DEFAULT '',
    status           TEXT NOT NULL DEFAULT 'active',
    metadata         JSONB NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS integration_secrets (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    integration_id TEXT NOT NULL REFERENCES host_integrations(integration_id) ON DELETE CASCADE,
    key_version    TEXT NOT NULL DEFAULT 'v1',
    secret_hint    TEXT NOT NULL DEFAULT '',
    active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    rotated_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS auth_nonces (
    nonce_key    TEXT PRIMARY KEY,
    nonce_id     TEXT NOT NULL,
    nonce_type   TEXT NOT NULL DEFAULT 'host_grant',
    expires_at   TIMESTAMPTZ NOT NULL,
    consumed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS company_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS integration_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS host_session_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS channel TEXT NOT NULL DEFAULT 'chat',
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS memory_summary TEXT NOT NULL DEFAULT '';

ALTER TABLE feedback
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS company_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS integration_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS vote review_vote NOT NULL DEFAULT 'neutral',
    ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'submitted',
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'api',
    ADD COLUMN IF NOT EXISTS created_by TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS usage_events (
    event_id        TEXT PRIMARY KEY,
    event_type      usage_event_type NOT NULL,
    endpoint        TEXT NOT NULL,
    tenant_id       TEXT NOT NULL,
    user_id         TEXT NOT NULL DEFAULT '',
    company_id      TEXT NOT NULL DEFAULT '',
    session_id      TEXT NOT NULL DEFAULT '',
    trace_id        TEXT NOT NULL DEFAULT '',
    run_id          TEXT NOT NULL DEFAULT '',
    integration_id  TEXT NOT NULL DEFAULT '',
    provider        TEXT NOT NULL DEFAULT '',
    model           TEXT NOT NULL DEFAULT '',
    usage_source    TEXT NOT NULL DEFAULT 'none',
    billable        BOOLEAN NOT NULL DEFAULT FALSE,
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    total_tokens    INTEGER NOT NULL DEFAULT 0,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS usage_rollups_daily (
    rollup_key      TEXT PRIMARY KEY,
    rollup_date     DATE NOT NULL,
    tenant_id       TEXT NOT NULL,
    user_id         TEXT NOT NULL DEFAULT '',
    company_id      TEXT NOT NULL DEFAULT '',
    endpoint        TEXT NOT NULL DEFAULT '',
    provider        TEXT NOT NULL DEFAULT '',
    model           TEXT NOT NULL DEFAULT '',
    total_events    INTEGER NOT NULL DEFAULT 0,
    billable_events INTEGER NOT NULL DEFAULT 0,
    input_tokens    BIGINT NOT NULL DEFAULT 0,
    output_tokens   BIGINT NOT NULL DEFAULT 0,
    total_tokens    BIGINT NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS usage_rollups_monthly (
    rollup_key      TEXT PRIMARY KEY,
    rollup_month    DATE NOT NULL,
    tenant_id       TEXT NOT NULL,
    user_id         TEXT NOT NULL DEFAULT '',
    company_id      TEXT NOT NULL DEFAULT '',
    endpoint        TEXT NOT NULL DEFAULT '',
    provider        TEXT NOT NULL DEFAULT '',
    model           TEXT NOT NULL DEFAULT '',
    total_events    INTEGER NOT NULL DEFAULT 0,
    billable_events INTEGER NOT NULL DEFAULT 0,
    input_tokens    BIGINT NOT NULL DEFAULT 0,
    output_tokens   BIGINT NOT NULL DEFAULT 0,
    total_tokens    BIGINT NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id           TEXT PRIMARY KEY,
    job_type         TEXT NOT NULL,
    status           job_status NOT NULL DEFAULT 'queued',
    tenant_id        TEXT NOT NULL DEFAULT '',
    user_id          TEXT NOT NULL DEFAULT '',
    company_id       TEXT NOT NULL DEFAULT '',
    request_payload  JSONB NOT NULL DEFAULT '{}',
    result_payload   JSONB NOT NULL DEFAULT '{}',
    error            TEXT NOT NULL DEFAULT '',
    attempts         INTEGER NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS job_runs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id       TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    status       job_status NOT NULL DEFAULT 'queued',
    payload      JSONB NOT NULL DEFAULT '{}',
    error        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE VIEW reviews AS
SELECT
    id::text AS review_id,
    trace_id,
    session_id,
    tenant_id,
    user_id,
    company_id,
    integration_id,
    vote,
    rating,
    review_status AS status,
    comment,
    tags,
    docs_used,
    layer_contributions,
    pain_detected,
    task_detected,
    source,
    created_by,
    created_at
FROM feedback;

CREATE INDEX IF NOT EXISTS idx_tenant_memberships_tenant ON tenant_memberships (tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_memberships_user ON tenant_memberships (user_id);
CREATE INDEX IF NOT EXISTS idx_companies_tenant ON companies (tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_company_access_lookup ON user_company_access (tenant_id, user_id, company_id);
CREATE INDEX IF NOT EXISTS idx_host_integrations_tenant ON host_integrations (tenant_id);
CREATE INDEX IF NOT EXISTS idx_auth_nonces_expiry ON auth_nonces (expires_at);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_user_company ON conversations (tenant_id, user_id, company_id);
CREATE INDEX IF NOT EXISTS idx_feedback_tenant_user_company ON feedback (tenant_id, user_id, company_id);
CREATE INDEX IF NOT EXISTS idx_feedback_vote_status ON feedback (vote, review_status);
CREATE INDEX IF NOT EXISTS idx_usage_events_tenant ON usage_events (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_events_user ON usage_events (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_events_company ON usage_events (company_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_events_trace ON usage_events (trace_id);
CREATE INDEX IF NOT EXISTS idx_jobs_tenant_status ON jobs (tenant_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_job_runs_job ON job_runs (job_id, created_at DESC);

DROP TRIGGER IF EXISTS trg_tenants_updated ON tenants;
CREATE TRIGGER trg_tenants_updated
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_users_updated ON users;
CREATE TRIGGER trg_users_updated
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_tenant_memberships_updated ON tenant_memberships;
CREATE TRIGGER trg_tenant_memberships_updated
    BEFORE UPDATE ON tenant_memberships
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_companies_updated ON companies;
CREATE TRIGGER trg_companies_updated
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_host_integrations_updated ON host_integrations;
CREATE TRIGGER trg_host_integrations_updated
    BEFORE UPDATE ON host_integrations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_usage_rollups_daily_updated ON usage_rollups_daily;
CREATE TRIGGER trg_usage_rollups_daily_updated
    BEFORE UPDATE ON usage_rollups_daily
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_usage_rollups_monthly_updated ON usage_rollups_monthly;
CREATE TRIGGER trg_usage_rollups_monthly_updated
    BEFORE UPDATE ON usage_rollups_monthly
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_jobs_updated ON jobs;
CREATE TRIGGER trg_jobs_updated
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
