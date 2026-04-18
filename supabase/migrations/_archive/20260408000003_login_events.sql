-- Login audit trail: records every login attempt (success + failure).
-- Also adds last_login_at to users for quick "last seen" queries.

CREATE TABLE IF NOT EXISTS login_events (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        TEXT,
    email          TEXT NOT NULL,
    tenant_id      TEXT,
    status         TEXT NOT NULL DEFAULT 'success',
    failure_reason TEXT,
    ip_address     TEXT NOT NULL DEFAULT '',
    user_agent     TEXT NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_login_events_created ON login_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_login_events_user    ON login_events (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_login_events_tenant  ON login_events (tenant_id, created_at DESC);

ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;
