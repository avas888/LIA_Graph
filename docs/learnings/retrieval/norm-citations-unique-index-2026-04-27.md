# `norm_citations` UNIQUE-vs-INDEX footgun — caught by live e2e

**Source:** First live integration smoke against local Supabase docker on
2026-04-27 evening, after fixplan_v3 sub-fix 1B-γ migrations landed
(`tests/integration/test_v3_persistence_e2e.py`).

## What broke

The `scripts/ingestion/backfill_norm_citations.py` 1B-δ loop and the new
`tests/integration/test_v3_persistence_e2e.py::test_chunk_vigencia_gate_*`
test both UPSERT into `norm_citations` with
`ON CONFLICT (chunk_id, norm_id, role)`. Against the live DB this raised:

```
psycopg.errors.InvalidColumnReference: there is no unique or exclusion
constraint matching the ON CONFLICT specification
```

## Why it happened

Migration `20260501000002_norm_citations.sql` (as initially shipped)
declared the would-be conflict target as a non-unique index:

```sql
CREATE INDEX IF NOT EXISTS idx_nc_chunk_norm_role_unique
    ON public.norm_citations(chunk_id, norm_id, role);
```

Postgres `ON CONFLICT (...)` requires a **UNIQUE** constraint or **UNIQUE
INDEX**, not just any index — even one whose name claims "_unique". The
H0 unit tests against a fake client never noticed because the fake's
`upsert` was a write-then-merge in Python.

## Why H0 unit tests didn't catch it

The fake Supabase client used in `tests/test_norm_history_writer.py`
implements `.upsert(...)` as a Python list-merge keyed on the
`on_conflict` column name; it never validates against the real
constraint. `test_norms_catalog_migration_shape.py` checks the migration
text but didn't assert on `UNIQUE`.

## Fix

Promoted the index to a UNIQUE INDEX in the same migration:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_nc_chunk_norm_role
    ON public.norm_citations(chunk_id, norm_id, role);
```

Idempotent — `CREATE … IF NOT EXISTS` lets re-applying the migration on a
DB that already has the wrong (non-unique) index pick up the unique one
on next reset.

## Process learning

**H0 fakes aren't enough for any code path that uses ON CONFLICT.** The
real Supabase client / psycopg is the only place the conflict-target
constraint is validated. Add at least one live-DB integration test for
every UPSERT site introduced by a sub-fix; gate on `LIA_INTEGRATION=1`
so CI doesn't need a Postgres.

**Check the migration shape test, not just the runtime test.** Extend
`tests/test_norms_catalog_migration_shape.py` to assert that conflict
targets used by code are actually UNIQUE.

## What to remember

- `CREATE INDEX` with "_unique" in the name is not a unique constraint.
- ON CONFLICT requires a UNIQUE INDEX or UNIQUE/PK constraint — Postgres
  matches by index *kind*, not by name.
- A Python fake of `.upsert(on_conflict=…)` will silently lie about
  whether the real DB accepts the call.
- The first live integration smoke after a migration ships is the only
  thing that catches this class of bug. Run it before any backfill batch.
