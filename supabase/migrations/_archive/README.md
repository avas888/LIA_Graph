# Archived Migrations (pre-squash)

These 45 migrations were consolidated into `supabase/migrations/20260417000000_baseline.sql` (schema) and `20260417000001_seed_users.sql` (seed data) on 2026-04-17.

They are retained here for historical reference only. Do not copy them back into `supabase/migrations/`; the CLI would apply them twice against a fresh DB.

To reconstruct any of the original files, use `git log --all --diff-filter=D -- supabase/migrations/`.
