-- Backfill user_id (and tenant_id where possible) on conversations that were
-- created while the streaming endpoint (/api/chat/stream) was missing the
-- Authorization header.  Those conversations stored user_id = '' and
-- tenant_id = 'public'.
--
-- Correlation sources (best → weakest):
--   1. feedback        — always has correct user_id (auth required)
--   2. chat_runs       — correct when endpoint = '/api/chat' (non-streaming)
--   3. single-member   — if tenant has exactly one member, assign that user
--
-- Safe to re-run: every UPDATE is guarded by user_id = '' on the target row.

BEGIN;

-- ── Step 1: backfill from feedback (most reliable) ──────────────────────
-- feedback.session_id links to conversations.session_id; feedback always
-- carries the authenticated user_id and tenant_id.

UPDATE conversations c
SET
  user_id    = fb.user_id,
  tenant_id  = CASE
                 WHEN c.tenant_id IN ('public', '') THEN fb.tenant_id
                 ELSE c.tenant_id
               END,
  accountant_id = CASE
                    WHEN c.accountant_id IN ('ui_user', '') THEN fb.user_id
                    ELSE c.accountant_id
                  END
FROM (
  SELECT DISTINCT ON (session_id)
         session_id, user_id, tenant_id
  FROM   feedback
  WHERE  session_id IS NOT NULL AND session_id != ''
    AND  user_id    IS NOT NULL AND user_id    != ''
  ORDER  BY session_id, created_at DESC
) fb
WHERE c.session_id = fb.session_id
  AND (c.user_id IS NULL OR c.user_id = '');


-- ── Step 2: backfill from chat_runs (non-streaming turns had auth) ──────

UPDATE conversations c
SET
  user_id    = cr.user_id,
  tenant_id  = CASE
                 WHEN c.tenant_id IN ('public', '') AND cr.tenant_id IS NOT NULL AND cr.tenant_id != ''
                 THEN cr.tenant_id
                 ELSE c.tenant_id
               END,
  accountant_id = CASE
                    WHEN c.accountant_id IN ('ui_user', '') THEN cr.user_id
                    ELSE c.accountant_id
                  END
FROM (
  SELECT DISTINCT ON (session_id)
         session_id, user_id, tenant_id
  FROM   chat_runs
  WHERE  session_id IS NOT NULL AND session_id != ''
    AND  user_id    IS NOT NULL AND user_id    != ''
  ORDER  BY session_id, created_at DESC
) cr
WHERE c.session_id = cr.session_id
  AND (c.user_id IS NULL OR c.user_id = '');


-- ── Step 3: single-member tenant inference ──────────────────────────────
-- If a conversation already has a real tenant_id (not 'public') and that
-- tenant has exactly one user, we can safely assign that user.

UPDATE conversations c
SET
  user_id       = solo.user_id,
  accountant_id = CASE
                    WHEN c.accountant_id IN ('ui_user', '') THEN solo.user_id
                    ELSE c.accountant_id
                  END
FROM (
  SELECT tenant_id, MIN(user_id) AS user_id
  FROM   tenant_memberships
  GROUP  BY tenant_id
  HAVING COUNT(*) = 1
) solo
WHERE c.tenant_id = solo.tenant_id
  AND c.tenant_id NOT IN ('public', '')
  AND (c.user_id IS NULL OR c.user_id = '');


-- ── Step 4: propagate to chat_runs ──────────────────────────────────────
-- Now that conversations have better user_id, propagate back to chat_runs
-- that are still missing it.

UPDATE chat_runs cr
SET
  user_id   = c.user_id,
  tenant_id = CASE
                WHEN cr.tenant_id IS NULL OR cr.tenant_id = '' THEN c.tenant_id
                ELSE cr.tenant_id
              END
FROM conversations c
WHERE cr.session_id = c.session_id
  AND c.user_id  != ''
  AND (cr.user_id IS NULL OR cr.user_id = '');


-- ── Step 5: propagate to usage_events ───────────────────────────────────

UPDATE usage_events ue
SET
  user_id   = c.user_id,
  tenant_id = CASE
                WHEN ue.tenant_id IN ('public', '') AND c.tenant_id NOT IN ('public', '')
                THEN c.tenant_id
                ELSE ue.tenant_id
              END
FROM conversations c
WHERE ue.session_id = c.session_id
  AND c.user_id  != ''
  AND (ue.user_id IS NULL OR ue.user_id = '');

COMMIT;
