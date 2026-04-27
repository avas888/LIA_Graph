# `ARRAY[%s]` with a Python list silently produces a 2D Postgres array

**Source:** Live e2e for `chunk_vigencia_gate_at_date(text[], date)` on
2026-04-27, sub-fix 1B-ε.

## What broke

The new RPC takes `text[]` for chunk_ids:

```sql
CREATE FUNCTION chunk_vigencia_gate_at_date(chunk_ids text[], as_of_date date)
```

The first integration test invoked it as:

```python
cur.execute(
    "SELECT ... FROM chunk_vigencia_gate_at_date(ARRAY[%s], %s)",
    ([chunk_id], "2026-04-27"),
)
```

The function returned 0 rows even though the citation + history rows
existed and the standalone `norm_vigencia_at_date` resolver returned the
expected DE row.

## Why it happened

psycopg substitutes a Python `list` as a Postgres array literal. So
`ARRAY[%s]` with `%s = [chunk_id]` expands to:

```sql
ARRAY[ARRAY['itest-chunk-...']]
```

That's a `text[][]` (2-D), not a `text[]` (1-D). The function's `chunk_id
= ANY(chunk_ids)` predicate then fails to match anything because
`ANY(text[][])` is comparing rows against rows-of-rows.

## Fix

Pass the list directly without the `ARRAY[]` constructor:

```python
cur.execute(
    "SELECT ... FROM chunk_vigencia_gate_at_date(%s::text[], %s::date)",
    ([chunk_id], "2026-04-27"),
)
```

psycopg formats a Python list of strings as `'{...}'::text[]` already —
explicit `ARRAY[...]` wrapping is redundant and dangerous when the
parameter is itself a list.

## What to remember

- For Postgres array parameters, pass a Python list as `%s::<type>[]`,
  never as `ARRAY[%s]`.
- A test that returns 0 rows from a `WHERE id = ANY(:ids)` query against
  a known-populated table is the smoking gun — silent type mismatch, not
  a missing row.
- This bug only surfaces with live psycopg execution; the H0 fake client
  never sees the SQL.

## Bigger principle

Every new RPC added by a sub-fix needs a "call it from real psycopg"
smoke alongside the H0 unit test. The H0 fake validates the Python-side
shape; the integration smoke validates the type-coercion contract with
real Postgres.
