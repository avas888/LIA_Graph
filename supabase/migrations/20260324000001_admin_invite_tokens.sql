-- CloudHost v1: user status column + invite tokens table + RLS

-- Add status column to users table (active, suspended, invited)
ALTER TABLE users ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';
CREATE INDEX IF NOT EXISTS idx_users_status ON users (status);

-- Invite tokens table for invite-link login flow
CREATE TABLE IF NOT EXISTS invite_tokens (
    token_id    TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    email       TEXT NOT NULL DEFAULT '',
    role        platform_role NOT NULL DEFAULT 'tenant_user',
    invited_by  TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'pending',
    expires_at  TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    accepted_by TEXT,
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_invite_tokens_tenant ON invite_tokens (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_invite_tokens_email ON invite_tokens (email, status);

-- RLS on tenant_memberships
ALTER TABLE tenant_memberships ENABLE ROW LEVEL SECURITY;
CREATE POLICY memberships_tenant_isolation ON tenant_memberships
  FOR ALL USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '');

-- RLS on invite_tokens
ALTER TABLE invite_tokens ENABLE ROW LEVEL SECURITY;
CREATE POLICY invites_tenant_isolation ON invite_tokens
  FOR ALL USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '');
