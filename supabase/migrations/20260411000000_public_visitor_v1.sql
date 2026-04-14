-- Public Visitor v1 — persistent state for the no-login `/public` chat surface.
--
-- Two tables:
--   1. public_usage_quota   — per-IP-hash daily message counter (cost ceiling)
--   2. public_captcha_passes — per-IP-hash registry of "captcha already solved"
--
-- Both are keyed by `pub_user_id` = `pub_<sha256(ip + LIA_PUBLIC_USER_SALT)[:16]>`
-- — raw IPs never live in the DB. Salt is a Railway secret.
--
-- RLS pattern matches `20260322000001_rls_tenant_isolation.sql`:
-- service-role bypasses RLS by default; PostgREST/anon get blocked.
-- Public visitors run with `tenant_id='public_anon'` claim → policies refuse them
-- so a stolen public JWT cannot read or write these tables directly.

-- ── public_usage_quota ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.public_usage_quota (
  ip_hash TEXT NOT NULL,
  day DATE NOT NULL,
  count INTEGER NOT NULL DEFAULT 0,
  first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ip_hash, day)
);

CREATE INDEX IF NOT EXISTS public_usage_quota_day_idx
  ON public.public_usage_quota (day);

ALTER TABLE public.public_usage_quota ENABLE ROW LEVEL SECURITY;

-- Service-role-only: any non-empty `requesting_tenant_id()` (i.e. real JWT) is rejected.
-- Service role bypasses RLS entirely so the backend can still UPSERT rows.
CREATE POLICY public_usage_quota_service_only_select
  ON public.public_usage_quota FOR SELECT
  USING (requesting_tenant_id() = '');

CREATE POLICY public_usage_quota_service_only_insert
  ON public.public_usage_quota FOR INSERT
  WITH CHECK (requesting_tenant_id() = '');

CREATE POLICY public_usage_quota_service_only_update
  ON public.public_usage_quota FOR UPDATE
  USING (requesting_tenant_id() = '')
  WITH CHECK (requesting_tenant_id() = '');

CREATE POLICY public_usage_quota_service_only_delete
  ON public.public_usage_quota FOR DELETE
  USING (requesting_tenant_id() = '');

-- ── public_captcha_passes ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.public_captcha_passes (
  ip_hash TEXT PRIMARY KEY,
  passed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.public_captcha_passes ENABLE ROW LEVEL SECURITY;

CREATE POLICY public_captcha_passes_service_only_select
  ON public.public_captcha_passes FOR SELECT
  USING (requesting_tenant_id() = '');

CREATE POLICY public_captcha_passes_service_only_insert
  ON public.public_captcha_passes FOR INSERT
  WITH CHECK (requesting_tenant_id() = '');

CREATE POLICY public_captcha_passes_service_only_update
  ON public.public_captcha_passes FOR UPDATE
  USING (requesting_tenant_id() = '')
  WITH CHECK (requesting_tenant_id() = '');

CREATE POLICY public_captcha_passes_service_only_delete
  ON public.public_captcha_passes FOR DELETE
  USING (requesting_tenant_id() = '');
