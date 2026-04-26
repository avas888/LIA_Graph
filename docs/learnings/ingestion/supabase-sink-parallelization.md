# Parallelizing the Supabase sink

**Source:** `docs/done/next/ingestion_tunningv2.md` §16 Appendix D §9 (follow-up); v6 phase 2b execution 2026-04-24; commit TBD.

> **TL;DR.** The Supabase sink is four batched-upsert loops that are trivially parallelizable because every row has a unique primary key. We reused the **same** `classify_documents_parallel` primitive from `ingest_classifier_pool.py` rather than forking it. Default 4 workers (conservative for Postgres connection pools). Expected speedup on ~7,883 docs: 10–15 min → 2–3 min.

## The incident that motivated this

On 2026-04-24 during v6 phase 2, the cloud sink (`make phase2-graph-artifacts-supabase`) stalled silently for ~25 min before I killed it. Post-mortem traced the stall to `load_existing_tema` at `src/lia_graph/ingestion/supabase_sink.py:123` — a pre-sink call that issues ~53 sequential `SELECT doc_id, tema FROM documents WHERE doc_id IN (<150-key chunk>)` queries, merging results into a dict. No per-batch events, no progress indicator, no timeout — just a tight `for start in range(...)` loop holding the whole pipeline.

The `load_existing_tema` stall was particularly toxic because:

1. **It blocks BEFORE any sink writes.** So the operator can't tell whether anything has landed in cloud yet — nothing has.
2. **It blocks AFTER the classifier + binding pass.** So 6-7 min of real work is done but invisible to the stuck operator.
3. **Its network signature looks "healthy"**: ESTABLISHED socket to Supabase PostgREST, RSS holding steady. Only the events.jsonl freshness check catches the stall.

When I retried with the dependency health probe (`scripts/monitoring/dep_health.py`), Supabase responded in **1.2 s**. So the stall was transient but complete — the sink was waiting on a response that arrived (probably) after my kill.

**Fix: parallelize the 53 batches across 4 workers**. Even if one batch still takes 1-2 min from a transient slowdown, the other 52 continue; the dict merge still completes.

## Why the sink is safe to parallelize

Every heavy sink stage writes on a **unique primary (or composite) key**. Splitting rows across workers guarantees no two workers target the same key — no contention, no deadlock, no lost updates.

| Stage | Key | Parallel? |
|---|---|---|
| `load_existing_tema` | read-only `SELECT IN ...` | YES |
| `write_documents` | `upsert(batch, on_conflict="doc_id")` | YES (unique `doc_id` per row) |
| `write_chunks` | `upsert(batch, on_conflict="chunk_id")` | YES (unique `chunk_id` per row) |
| `write_normative_edges` | `upsert(batch, on_conflict="source_key,target_key,relation,generation_id")` | YES (unique composite) |
| `write_generation` / `finalize` | single-row ops | **NO** (not worth parallelizing anyway) |

If any future sink stage writes with a non-unique key, it must stay sequential. The rule is simple: **row-level partitioning is safe iff no two partitions can target the same key.**

## Reusing, not forking, the primitive

The `classify_documents_parallel` function in `ingest_classifier_pool.py` (phase 2a) already had the exact shape we needed:

```python
def classify_documents_parallel(
    documents: tuple,                       # → batches
    *,
    classify_fn: Callable[[int, Any], Any], # → _upsert_doc(idx, batch) -> rowcount
    worker_count: int,
    rate_limit_rpm: int,
    ...
) -> list[Any]:
```

- Pre-allocated indexed output → deterministic sum of batch counts
- `TokenBucket` with `rpm<=0 = unlimited` → we pass 0 because Supabase fronts its own rate-limiting
- Per-future exception isolation → one bad batch raises, siblings' results remain
- Decorrelated-jitter retry → transient 5xx / PostgREST timeouts recover

We added a thin wrapper `_run_batches_parallel` that:
- Calls `classify_documents_parallel` under the hood
- Unwraps the `_ClassifierError` sentinel and re-raises as `RuntimeError("supabase_sink batch #N failed after retries: ...")` — keeps the pool primitive agnostic while giving sink callers a sink-flavored exception
- Returns `list[int]` so callers can `sum(per_batch)` for the total rowcount

**Net diff:** ~80 new LOC in `supabase_sink.py`, four sequential loops replaced in place, zero changes to `ingest_classifier_pool.py`.

## Default worker count — why 4, not 8

Postgres connection pools are the binding constraint, not Gemini RPM:

| Resource | Classifier (phase 2a) | Sink (phase 2b) |
|---|---|---|
| **Rate limit** | Flash: 1,000 RPM | PostgREST: ~100 req/s (free), higher paid |
| **Connection pool** | N/A (HTTP 1.1 per-call) | Supabase default: 15 direct, 100 pooled |
| **Request cost** | ~500 ms (LLM round-trip) | ~200 ms (upsert round-trip) |
| **Safe worker count** | 8 (70% ceiling) | 4 (conservative on conn pool) |

4 workers × 200 ms = 20 requests/sec — well under free-tier PostgREST, and leaves pool headroom for other app traffic hitting the DB.

Override via `--supabase-workers N` / `LIA_SUPABASE_SINK_WORKERS`. We'd go to 8 on paid prod if chunk-upload throughput becomes the bottleneck.

## What we did NOT parallelize (and why)

- **`write_generation` and `finalize`** — single-row operations. Parallelism isn't applicable.
- **The Falkor graph load** — Cypher `MERGE` can contend on the same node key across workers. Graph loads usually have to chunk by disjoint subgraph or serialize per-label. Leaving this for a later phase; no evidence yet that the Falkor load is a bottleneck.
- **`_load_tema` inside the sink instance** (line 314) — the module-level function (which the Falkor path calls before the sink exists) is already parallelized; the instance wrapper delegates to it.

## Tests

`tests/test_supabase_sink_parallel.py` (9 tests):

1. Default worker count = 4.
2. Env override (`LIA_SUPABASE_SINK_WORKERS`) takes effect.
3. Explicit kwarg beats env.
4. `_run_batches_parallel` preserves input order (slower-when-earlier work).
5. Empty-input is a no-op.
6. Persistent failure raises `RuntimeError("supabase_sink batch #N ...")`.
7. `load_existing_tema` parallel path merges all batches correctly.
8. `load_existing_tema` degrades to `{}` on any transport error (pre-2b contract preserved).
9. `load_existing_tema` empty input is a no-op.

Uses a thread-safe `_FakeClient` that records every `.upsert(...)` and `.select(...)` call. No network, no real Supabase.

## Rollout notes

- **Idempotent by design** — every stage uses `upsert(batch, on_conflict=...)`. Re-running after a partial failure is safe.
- **Flag-gated via default** — `--supabase-workers 4` is the default, but `--supabase-workers 1` forces the old sequential path. Regression-safe.
- **`load_existing_tema` preserves its "degrade to {}" contract** — if any batch raises after retries, the whole function returns an empty dict. Callers that relied on "empty dict means unknown, trust classifier" still work.
- **No schema changes.** Pure runtime change.

## Anti-patterns to watch for

- **Parallelizing stages with non-unique keys.** If a new stage writes on a composite key that can collide across workers (e.g., a staging table without a unique constraint), parallel upserts will cause lost updates. Check the `on_conflict=` clause.
- **Running 8+ workers on free tier.** Saturates the 15-connection pool, starves app traffic. Stick with 4 unless you know the tier.
- **Silencing batch failures.** The wrapper raises `RuntimeError("supabase_sink batch #N ...")` specifically so callers notice. Don't catch-and-ignore unless you're in `load_existing_tema`-style best-effort paths.
- **Changing a write-time key-form without updating cleanup paths.** Parallelism safety doesn't help if `WHERE source_key = …` queries on retire / modify still match the old form. The write-path and delete-path must mirror each other in lockstep. See [`edge-key-form-discipline.md`](edge-key-form-discipline.md) for the triage checklist — surfaced by the v5 §6.3 prose-only-edges fix where the linker started writing `whole::` keys but `_handle_apply` cleanup paths kept matching the legacy slug, leaving stale rows on every modify of a prose-only doc.

## Follow-ups

- **Per-stage worker budget** — chunks are 5× the volume of documents. A future refinement could let chunks run at 8 workers while documents stay at 4. Not urgent; phase 2b's uniform 4 is already 2-3× speedup.
- **Connection pool visibility** — `SELECT * FROM pg_stat_activity` to audit real connection usage during a large sink. Add a probe to `dep_health.py` if we ever need it.
- **Falkor parallelization** — separate investigation. Cypher MERGE contention rules out naïve parallelism; staged by relation-label or subgraph partitioning.

## See also

- `src/lia_graph/ingestion/supabase_sink.py:109` — `_run_batches_parallel`.
- [`parallelism-and-rate-limits.md`](parallelism-and-rate-limits.md) — the phase 2a classifier-pool design this reuses.
- [`../process/heartbeat-monitoring.md`](../process/heartbeat-monitoring.md) — how to detect a `load_existing_tema`-class silent stall.
- [`../process/cloud-sink-execution-notes.md`](../process/cloud-sink-execution-notes.md) — the env-posture prerequisites.
