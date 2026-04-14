-- Row-Level Security: tenant isolation for per-tenant tables.
-- service_role bypasses RLS by default in Supabase (both local Docker and cloud).
-- These policies protect against direct PostgREST/anon access and future API gateway paths.

-- ── Helper: extract tenant_id from JWT claims ────────────────────────
-- Works on both local Docker Supabase and Supabase Cloud.
-- current_setting returns NULL (not error) when true is passed as second arg.

CREATE OR REPLACE FUNCTION public.requesting_tenant_id()
RETURNS TEXT
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  raw TEXT;
BEGIN
  raw := current_setting('request.jwt.claims', true);
  IF raw IS NULL OR raw = '' THEN
    RETURN '';
  END IF;
  RETURN COALESCE(raw::json ->> 'tenant_id', '');
EXCEPTION WHEN OTHERS THEN
  RETURN '';
END;
$$;

-- ── conversations ────────────────────────────────────────────────────

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY conversations_tenant_select
  ON conversations FOR SELECT
  USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '');

CREATE POLICY conversations_tenant_insert
  ON conversations FOR INSERT
  WITH CHECK (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '');

CREATE POLICY conversations_tenant_update
  ON conversations FOR UPDATE
  USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '')
  WITH CHECK (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '');

CREATE POLICY conversations_tenant_delete
  ON conversations FOR DELETE
  USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '');

-- ── conversation_turns (inherits via FK, but direct access must be scoped) ──

ALTER TABLE conversation_turns ENABLE ROW LEVEL SECURITY;

CREATE POLICY turns_tenant_select
  ON conversation_turns FOR SELECT
  USING (
    requesting_tenant_id() = ''
    OR conversation_id IN (
      SELECT id FROM conversations WHERE tenant_id = requesting_tenant_id()
    )
  );

CREATE POLICY turns_tenant_insert
  ON conversation_turns FOR INSERT
  WITH CHECK (
    requesting_tenant_id() = ''
    OR conversation_id IN (
      SELECT id FROM conversations WHERE tenant_id = requesting_tenant_id()
    )
  );

CREATE POLICY turns_tenant_update
  ON conversation_turns FOR UPDATE
  USING (
    requesting_tenant_id() = ''
    OR conversation_id IN (
      SELECT id FROM conversations WHERE tenant_id = requesting_tenant_id()
    )
  )
  WITH CHECK (
    requesting_tenant_id() = ''
    OR conversation_id IN (
      SELECT id FROM conversations WHERE tenant_id = requesting_tenant_id()
    )
  );

CREATE POLICY turns_tenant_delete
  ON conversation_turns FOR DELETE
  USING (
    requesting_tenant_id() = ''
    OR conversation_id IN (
      SELECT id FROM conversations WHERE tenant_id = requesting_tenant_id()
    )
  );

-- ── feedback ─────────────────────────────────────────────────────────

ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY feedback_tenant_select
  ON feedback FOR SELECT
  USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '' OR tenant_id = '');

CREATE POLICY feedback_tenant_insert
  ON feedback FOR INSERT
  WITH CHECK (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '' OR tenant_id = '');

CREATE POLICY feedback_tenant_update
  ON feedback FOR UPDATE
  USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '' OR tenant_id = '')
  WITH CHECK (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '' OR tenant_id = '');

CREATE POLICY feedback_tenant_delete
  ON feedback FOR DELETE
  USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '' OR tenant_id = '');

-- ── usage_events ─────────────────────────────────────────────────────

ALTER TABLE usage_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY usage_events_tenant_select
  ON usage_events FOR SELECT
  USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '');

CREATE POLICY usage_events_tenant_insert
  ON usage_events FOR INSERT
  WITH CHECK (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '');

-- ── usage_rollups_daily ──────────────────────────────────────────────

ALTER TABLE usage_rollups_daily ENABLE ROW LEVEL SECURITY;

CREATE POLICY usage_rollups_daily_tenant_select
  ON usage_rollups_daily FOR SELECT
  USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '');

-- ── usage_rollups_monthly ────────────────────────────────────────────

ALTER TABLE usage_rollups_monthly ENABLE ROW LEVEL SECURITY;

CREATE POLICY usage_rollups_monthly_tenant_select
  ON usage_rollups_monthly FOR SELECT
  USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '');

-- ── chat_runs ────────────────────────────────────────────────────────

ALTER TABLE chat_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY chat_runs_tenant_select
  ON chat_runs FOR SELECT
  USING (
    requesting_tenant_id() = ''
    OR tenant_id = requesting_tenant_id()
    OR tenant_id IS NULL
  );

CREATE POLICY chat_runs_tenant_insert
  ON chat_runs FOR INSERT
  WITH CHECK (
    requesting_tenant_id() = ''
    OR tenant_id = requesting_tenant_id()
    OR tenant_id IS NULL
  );

-- ── jobs ─────────────────────────────────────────────────────────────

ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY jobs_tenant_select
  ON jobs FOR SELECT
  USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '' OR tenant_id = '');

CREATE POLICY jobs_tenant_insert
  ON jobs FOR INSERT
  WITH CHECK (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '' OR tenant_id = '');

CREATE POLICY jobs_tenant_update
  ON jobs FOR UPDATE
  USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '' OR tenant_id = '')
  WITH CHECK (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '' OR tenant_id = '');

-- ── contributions ────────────────────────────────────────────────────

ALTER TABLE contributions ENABLE ROW LEVEL SECURITY;

CREATE POLICY contributions_tenant_select
  ON contributions FOR SELECT
  USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '');

CREATE POLICY contributions_tenant_insert
  ON contributions FOR INSERT
  WITH CHECK (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '');

CREATE POLICY contributions_tenant_update
  ON contributions FOR UPDATE
  USING (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '')
  WITH CHECK (tenant_id = requesting_tenant_id() OR requesting_tenant_id() = '');

-- ── Shared/corpus tables: NO RLS (intentionally shared across tenants) ──
-- documents, document_chunks, form_guides, form_hotspots, corpus_generations,
-- query_embedding_cache, expert_summary_overrides, orchestration_settings
