# H0 fakes pass while live DB fails — the integration gap

**Source:** First live e2e of fixplan_v3 v3 sub-fixes against local
Supabase docker on 2026-04-27. 9 H0-fake-passing tests; 4 of the 9 caught
real bugs only when run against a live psycopg connection.

## The gap

For each v3 sub-fix the H0 unit-test suite uses an in-memory fake
Supabase client (`FakeSupabase` in `tests/test_norm_history_writer.py`,
`_Client` in `tests/test_vigencia_cascade.py`). These fakes:

- Implement `.table().upsert(...)` as a list-merge keyed on the
  `on_conflict` column name — they don't validate that a UNIQUE
  constraint actually exists.
- Implement `.select().eq().execute()` as Python filtering — they don't
  exercise Postgres-side types or operators.
- Don't run CHECK constraints, so a row that would be rejected by the
  migration's `CHECK` lands silently.
- Don't exercise PL/pgSQL functions or `text[]` parameters.

This means H0 verification is "the Python shape compiles." It is NOT
"the schema works."

## Bugs caught only by the live integration smoke

1. **Missing UNIQUE constraint on `norm_citations`** —
   `ON CONFLICT (chunk_id, norm_id, role)` requires a UNIQUE INDEX, but
   the migration shipped a plain INDEX. (`norm-citations-unique-index-2026-04-27.md`)

2. **`ARRAY[%s]` formatting trap** — passing a Python list to a Postgres
   `text[]` parameter wrapped in `ARRAY[%s]` produces a 2-D array. The
   function silently returned 0 rows. (`postgres-array-literal-2d-trap-2026-04-27.md`)

3. **CHECK-violation timing** — psycopg raises `CheckViolation` at
   `cur.execute()`, not at `conn.commit()`. Tests that wrap `commit()` in
   `pytest.raises` silently miss real CHECK enforcement (false-PASS).

4. **Failed-tx state leakage between tests** — once a CHECK violation
   aborts a transaction, the same `conn` returns
   `InFailedSqlTransaction` on every subsequent statement until rollback.
   Autouse cleanup fixtures must `conn.rollback()` before they can DELETE.

## Process correction

Every sub-fix that introduces:

- A new SQL function, OR
- A new UPSERT site (ON CONFLICT), OR
- A new migration with CHECK constraints, OR
- Any code that builds a Postgres array literal from a Python list,

…must ship at least one **live-DB integration test** alongside its H0
fake-client tests. Live tests live in `tests/integration/`, gate on
`LIA_INTEGRATION=1`, and connect via psycopg directly to the local
Supabase docker (port 54322 by default).

The integration tests are not "extra." They are the only place the
sub-fix's claims about Postgres semantics are verified. H0 fakes
guarantee the Python shape; H1 integration tests guarantee the schema
contract.

## Cost vs. benefit

The 9-test live e2e for the v3 stack runs in <1 second against a warm
local Supabase. The marginal cost of writing it (one file, ~700 lines
of test code) is trivial compared to the cost of shipping a migration
with the four bugs above to staging or production.

## What to remember

- "H0 unit tests pass" means "the Python module compiles and its fakes
  agree with each other."
- "Live integration smoke passes" means "the schema actually works."
- These are different gates. Don't conflate them in the state-fixplan
  ledger.
