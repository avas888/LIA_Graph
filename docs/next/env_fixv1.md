# Environment Fix v1 — Execution Plan

## Goal

Make three run modes behave the way the repo says they should:

| Command | App | Supabase | FalkorDB | Expected |
|---|---|---|---|---|
| `npm run dev` | local | local docker (`127.0.0.1:54321`) | local docker (`127.0.0.1:6389`) | greenlit |
| `npm run dev:staging` | local | cloud (`utjndyxgfhkfcrjmtdqz`) | cloud Falkor | greenlit |
| `npm run dev:production` | Railway (TBD) | cloud | cloud | scaffold only, exits non-zero locally |

Login with `admin@lia.dev / Test123!` must succeed on every greenlit mode.

## Baseline (before fix)

- `npm run dev`: forces `LIA_STORAGE_BACKEND=filesystem`, preflight skips Supabase, login impossible.
- `npm run dev:staging`: working, cloud passwords reset in this session.
- `npm run dev:production`: does not exist.
- Local Supabase stack (`supabase_*_lia-contador`) healthy on `54321`/`54322`, 7 migrations behind.
- Local users already seeded (`admin@lia.dev`, `usuario1@lia.dev` … `usuario10@lia.dev`) but passwords unknown.

## Execution Steps

1. Create `.env.staging` with cloud credentials explicit.
2. Create `.env.dev.local` with local Supabase URL + demo keys.
3. Modify `scripts/dev-launcher.mjs`:
   - Load `.env.dev.local` when `mode=local`, `.env.staging` when `mode=staging`.
   - Drop the `LIA_STORAGE_BACKEND=filesystem` branch. Use `supabase` for both dev and staging.
   - Force local Supabase env defaults in local mode so the mode still boots if the file is missing.
   - Run the Supabase preflight in local mode alongside FalkorDB.
   - Add a `production` branch that prints a "use Railway" message and exits non-zero.
4. Add `dev:production` script to `package.json`.
5. Apply the 7 pending migrations to local Postgres via `supabase migration up`.
6. Write `scripts/seed_local_passwords.py` that hashes `Test123!` and patches every `@lia.dev` user row. Run it against the local Supabase REST API.
7. Test each mode:
   - `npm run dev` boots, preflight green for Supabase + FalkorDB + Gemini, login `admin@lia.dev / Test123!` returns 200.
   - `npm run dev:staging` boots unchanged, login still works.
   - `npm run dev:production` exits non-zero with the Railway message.
8. Update documentation: `docs/guide/env_guide.md`, `AGENTS.md`, `CLAUDE.md`, and cross-references in `docs/guide/orchestration.md`.

## Design Choices

- **Separate `.env.*` files per mode.** Today staging piggy-backs on `.env.local`, which is fragile. Dedicated files kill the "edited local, broke staging" class of bug.
- **Local Supabase demo keys hardcoded in launcher.** Supabase CLI ships the same demo JWTs for every local stack (fixed `exp=1983812996`, issuer `supabase-demo`). Safe to commit; the launcher falls back to them if `.env.dev.local` is absent, so fresh clones just work.
- **`migration up`, not `db reset`.** Local DB has 10 days of dev state. We only apply the 7 missing migrations, preserving existing data.
- **Production stays disabled.** Railway deployment is out of scope. The script exists only to stop accidental production runs.

## Risk + Blast Radius

- Local: destructive operations limited to INSERT/UPDATE on seeded `@lia.dev` users and additive migrations. No `db reset`.
- Cloud Supabase (staging): no writes from this plan. Seeded passwords from the prior session remain.
- Cloud Falkor: read-only.
- Files changed: `scripts/dev-launcher.mjs`, `package.json`, new `.env.staging`, new `.env.dev.local`, new `scripts/seed_local_passwords.py`, documentation updates.

## Execution Results

Completed 2026-04-17.

### Verified

| Mode | Preflight | Login `admin@lia.dev / Test123!` |
|---|---|---|
| `npm run dev` | `[OK] falkordb` + `[OK] supabase (local)` + `[OK] gemini` | HTTP 200, `role=platform_admin`, `tenant=tenant-dev` |
| `npm run dev:staging` | `[OK] falkordb` + `[OK] supabase (cloud)` + `[OK] gemini` | HTTP 200, `role=platform_admin`, `tenant=tenant-dev` |
| `npm run dev:production` | n/a — script prints Railway notice and exits 2 | n/a |

### Files changed

- `scripts/dev-launcher.mjs` — dropped filesystem backend, added `ensureLocalSupabaseStack`, loads `.env.dev.local` in local mode, added `production` branch.
- `package.json` — added `dev:production`.
- `.env.dev.local` — new. Local Supabase URL + demo keys + local Falkor.
- `.env.staging` — new. Cloud Supabase + cloud Falkor + Gemini.
- `scripts/seed_local_passwords.py` — new. Reseeds all `@lia.dev` users to `Test123!` against whichever Supabase the env points at.
- `supabase/migrations/20260417000000_baseline.sql` — new. pg_dump of local `public` schema at head, plus required extensions prepended.
- `supabase/migrations/20260417000001_seed_users.sql` — new. Consolidated from the three pre-squash seed migrations.
- `supabase/migrations/_archive/` — new. 45 pre-squash migration files preserved here.
- `docs/guide/env_guide.md` — updated with the new boundary and seeding workflow.

### Migration squash summary

- Before: 45 migration files spanning 2026-03-09 to 2026-04-11, already applied locally.
- After: 2 files (baseline + seed_users). `supabase db reset` from a clean DB successfully replays them and the app boots against the result.
- Cloud Supabase (`utjndyxgfhkfcrjmtdqz`) was NOT re-migrated. Its live schema predates this squash and already satisfies app expectations; DDL changes against cloud require the database password (not available in this session) plus a separate `supabase db push` pass. Follow-up captured below.

### Follow-up

1. ~~Sync the squashed baseline to cloud Supabase.~~ **Done 2026-04-17.** After `supabase link` with the cloud DB password, `supabase db diff --linked` confirmed zero schema drift between the local baseline and the cloud `public` schema. Ran `supabase migration repair --status reverted` for the 45 cloud-only migration IDs from the 2026-04-14 batch, then `--status applied 20260417000000 20260417000001`. `supabase migration list` now shows only the two baseline IDs on both sides with no drift.
2. Wire Railway for the `production` run: create the project, set env vars (cloud Supabase + cloud Falkor + cloud Gemini), and verify `railway up` deploys a clean image.
3. ~~Consider moving `GEMINI_API_KEY` out of `.env.dev.local` and `.env.staging` into per-developer `.env.local` so neither committed file carries a live key.~~ **Done 2026-04-17.** Key now lives only in the gitignored `.env.local`; both committed files have a comment in place of the value and both preflights still pass.

