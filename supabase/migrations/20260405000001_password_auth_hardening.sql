-- Alpha security hardening: password auth for web login and normalized emails.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS password_hash TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS password_reset_required BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS password_updated_at TIMESTAMPTZ;

UPDATE users
SET email = lower(btrim(email))
WHERE email IS NOT NULL;

UPDATE users
SET password_reset_required = TRUE,
    password_updated_at = NULL
WHERE COALESCE(password_hash, '') = '';

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_normalized_unique
ON users ((lower(email)))
WHERE btrim(email) <> '';
