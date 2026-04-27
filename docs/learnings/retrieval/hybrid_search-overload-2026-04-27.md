# `hybrid_search` overload ambiguity — silent migration footgun

**Source:** §1.G SME validation run 2026-04-26 evening (`evals/sme_validation_v1/runs/20260427T003848Z/`); fix migration `supabase/migrations/20260428000000_drop_legacy_hybrid_search.sql`.

## What broke

15 of the 36 SME-authored validation questions returned **HTTP 500** with a Postgres-side error:

```
Could not choose the best candidate function between:
  public.hybrid_search(query_embedding => extensions.vector, ..., subtopic_boost => double precision)
  public.hybrid_search(query_embedding => extensions.vector, ..., subtopic_boost => double precision, filter_topic_boost => double precision)
```

PostgREST received a payload that matched **two** function signatures (one 14-arg, one 15-arg) and refused to pick.

## Why it happened

The §1.D migration `supabase/migrations/20260427000000_topic_boost.sql` shipped a new `hybrid_search` variant with one extra parameter (`filter_topic_boost double precision DEFAULT 1.0`). It used `CREATE OR REPLACE FUNCTION`.

**`CREATE OR REPLACE FUNCTION` only replaces a function with the *same argument signature*.** Postgres identifies functions by `(name, arg_types)`. Adding a parameter creates a brand-new function — the old 14-arg one is left in place. After the migration ran, both lived in cloud Supabase.

When `pipeline_d/retriever_supabase._hybrid_search` builds its payload, it adds `filter_topic_boost` only when `router_topic` is set AND `topic_boost > 1.0`. Otherwise the payload's keyset matches **both** overloads via DEFAULTs → ambiguity → 500.

## Why it wasn't caught earlier

- **The §1.D plan said "drop + recreate"** (next_v5.md §1.D Gate 2 line 244: *"Drop + recreate `hybrid_search` adding `filter_topic_boost`"*) — but the actual migration only did `CREATE OR REPLACE`. The drop step was lost between plan and SQL.
- **Heartbeat probes pass.** The 12-topic heartbeat questions are short and route cleanly, so `router_topic` is always set and `filter_topic_boost > 1.0` is always passed → only the 15-arg variant matches → no ambiguity. The bug is invisible to baseline regression watchers.
- **Unit tests pass.** Local Supabase replays migrations in chronological order; if the 14-arg variant is created and then `CREATE OR REPLACE`d into a 14-arg shape later, no overload exists. Only **cloud** had the problem because it had been mutated by the §1.D push without a fresh reset.
- **Failure mode is intermittent.** Of the 36 SME questions, the 15 that failed all had richer phrasing (P2 operativa + P3 borde profiles); the P1 directa questions sailed through. That made it look like a content-quality issue at first glance.

## The fix

`supabase/migrations/20260428000000_drop_legacy_hybrid_search.sql`:

```sql
DROP FUNCTION IF EXISTS "public"."hybrid_search"(
    "extensions"."vector", "text", "text", "text", integer, integer,
    double precision, double precision, "text", "text", "text", "date",
    "text", double precision
);
```

Idempotent. The 15-arg variant is fully backward-compatible (`filter_topic_boost DEFAULT 1.0` is a no-op when omitted), so existing callers keep working.

## The general lesson

**When a migration changes a function's parameter list, the migration MUST drop the old signature explicitly before the `CREATE`.** `CREATE OR REPLACE` is not enough. The earlier `20260421000000_sub_topic_taxonomy.sql` got this right (see lines 55–68 — explicit `DROP FUNCTION IF EXISTS` with the old signature). The §1.D migration omitted it.

**Pattern to copy** when adding/removing a `hybrid_search` parameter (or any RPC that PostgREST routes by signature):

```sql
-- 1. Drop every prior overload that PostgREST might still match.
DROP FUNCTION IF EXISTS "public"."<name>"( <old-arg-types> );

-- 2. Then create the new one.
CREATE OR REPLACE FUNCTION "public"."<name>"( <new-arg-list> ) RETURNS TABLE(...) ...;
```

**Detection.** Any time a `hybrid_search` migration adds or removes a parameter, before pushing to cloud:

```bash
psql "$STAGING_DB_URL" -c "
  SELECT proname, pg_get_function_identity_arguments(oid)
  FROM pg_proc WHERE proname = 'hybrid_search';
"
```

Should return exactly one row. More than one = overload ambiguity is one cold path away.

## Where this surfaced in the §1.G data

`evals/sme_validation_v1/runs/20260427T003848Z/report.md` initially read **STATE: FAIL** because the classifier bucketed the 15 server-error responses into `served_weak`. After re-classifying (with a new `server_error` bucket added to `scripts/eval/run_sme_validation.py:classify`), the verdict moved to **STATE: INCONCLUSIVE — re-run those 15 qids before interpreting**. Once `20260428000000_drop_legacy_hybrid_search.sql` was applied to staging, the runner resumed only those 15 (the other 21 stayed cached on disk) and produced a clean classified.jsonl + verbatim.md.

Of the 21 questions that **did** execute end-to-end on the contaminated run, 7 were `served_acceptable+` — useful signal that survived the infrastructure failure (e.g., `tarifas_renta_y_ttd` refused all 3 even with the DB working — a real curation gap, not infra), but the verdict couldn't be trusted until the 15 were re-run.

## Ripple

Add a **shape-change detector** to `make supabase-status` or the launcher preflight: if any `public.<rpc>` has more than one row in `pg_proc`, fail loudly. That makes future overload bugs impossible to ship past the preflight.
