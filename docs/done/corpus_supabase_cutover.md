# Corpus → Supabase Sink + Staging Runtime Cutover

## Goal

After this work ships, running `npm run dev:staging` must:

- serve `main chat` answers whose evidence was retrieved from **cloud Supabase** (`documents`, `document_chunks` + the `hybrid_search` RPC), not from filesystem `artifacts/*.jsonl`.
- resolve graph traversal against **cloud FalkorDB** (`LIA_REGULATORY_GRAPH`), not from in-memory edge snapshots loaded off disk.
- emit a diagnostics field in every response confirming which backend served the turn.

Running `npm run dev` must continue to work fully offline against local artifacts + local docker Falkor — this scope is strictly additive, gated by an env flag.

## Two phases

| Phase | What it does | Read path cutover? |
|---|---|---|
| **A — Ingestion sink** | Extend `materialize_graph_artifacts()` so each ingestion run writes the same rows it already writes to artifacts+Falkor into Supabase `documents` / `document_chunks` / `corpus_generations` / `normative_edges`. | No — populates rows only. |
| **B — Retrieval cutover** | Add a Supabase-backed retriever + Falkor-backed graph traversal behind a `LIA_CORPUS_SOURCE` flag. Set the flag in staging env so staging uses them; dev keeps artifact mode. | Yes, in staging only. |

Phase A is a prerequisite for Phase B — B has nothing to read until A runs at least once.

---

## Phase A — Ingestion sink

### Files to create

1. **`src/lia_graph/ingestion/supabase_sink.py`** (new, ~250–350 LOC).
   - Public surface:
     ```python
     class SupabaseCorpusSink:
         def __init__(self, target: str = "production"): ...
         def write_generation(self, generation: CorpusGeneration) -> None: ...
         def write_documents(self, rows: Iterable[dict]) -> None: ...
         def write_chunks(self, rows: Iterable[dict]) -> None: ...
         def write_normative_edges(self, rows: Iterable[dict]) -> None: ...
         def finalize(self, *, activate: bool) -> None: ...
     ```
   - Constructor calls `supabase_client.create_supabase_client_for_target(target)` (`src/lia_graph/supabase_client.py:120`). `target` defaults to `"production"`; the `"wip"` alias is available for dry-runs against a shadow project.
   - All writes use `table(...).upsert(..., on_conflict=<pk>)` for idempotency. Batch to 500 rows per request.
   - Columns and constraints are pinned to the squashed baseline at `supabase/migrations/20260417000000_baseline.sql`:
     - `documents` PK `doc_id`; NOT-NULLs without defaults: `doc_id`, `relative_path`, `source_type`, `topic`, `authority`, `pais`, `curation_status`. Use `content_hash` as the idempotency key on subsequent runs.
     - `document_chunks` PK `id (uuid)`, unique `chunk_id`; NOT-NULLs: `id`, `doc_id`, `chunk_text`, `created_at`. FK `doc_id → documents(doc_id) ON DELETE CASCADE`. Leave `embedding` NULL — embeddings are generated later by `src/lia_graph/embedding_ops.py:332` and that step already upserts `document_chunks`.
     - `corpus_generations` PK `generation_id`; partial unique index `idx_corpus_generations_single_active` (baseline line 1790) requires that only one row has `is_active=true`. On `finalize(activate=True)`, run a two-step: `UPDATE corpus_generations SET is_active=false WHERE is_active=true; UPDATE corpus_generations SET is_active=true WHERE generation_id = <new>;` inside a single RPC so the partial unique is never violated.
     - `normative_edges` PK `id` (identity); CHECK constraint `relation IN (...)` (baseline line ~1129). Map the ingestion's `ClassifiedEdge.kind` (`MODIFIES`, `REFERENCES`, `SUPERSEDES`, `EXCEPTION_TO`, ...) to the lowercased values the DB allows. Do not pass `kind` values the CHECK does not accept — add an assertion in `_map_relation()` and fail loud.
   - Idempotency keys:
     - `documents` on `doc_id` (already PK).
     - `document_chunks` on `chunk_sha256` (preferred) or `chunk_id` (unique index). Prefer `chunk_sha256` since it survives chunker changes.
     - `normative_edges` on `(source_key, target_key, relation, generation_id)` — enforce via a new partial unique index (see migration below).
   - Every row must carry the `generation_id` from the current ingestion run, so a sink re-run never cross-contaminates prior generations.

2. **`supabase/migrations/20260418000000_normative_edges_unique.sql`** (new, ~15 LOC).
   - Add `CREATE UNIQUE INDEX IF NOT EXISTS normative_edges_idempotency ON normative_edges (source_key, target_key, relation, generation_id);`
   - Required so the sink's upsert has a conflict target; today there is no unique constraint there and repeated runs would duplicate rows.
   - After writing, run locally: `supabase db reset` (verifies baseline + new migration replay cleanly), then `supabase db push` to apply to cloud (requires `supabase link` with DB password per the existing workflow in `docs/next/env_fixv1.md`).

3. **`tests/test_ingestion_supabase_sink.py`** (new, ~200 LOC).
   - Fixture: a local Supabase (reached via `.env.dev.local`, not cloud) with the baseline applied.
   - Cases, in order:
     - `test_writes_generation_then_rows` — one run inserts all four tables; counts match the input fixtures.
     - `test_rerun_is_idempotent` — second invocation with identical input produces zero row deltas and a new `corpus_generations` row flagged `is_active=true`, older row flagged `false`.
     - `test_relation_check_constraint_enforced` — passing a `ClassifiedEdge.kind` not in the CHECK list raises `AssertionError` before hitting the network (fail loud, not silent skip).
     - `test_activate_is_atomic` — two concurrent `finalize(activate=True)` calls don't leave two active generations. Test with a threading stub or a sequential assertion that the `UPDATE … WHERE is_active=true` runs first.

### Files to modify

4. **`src/lia_graph/ingest.py`** (`materialize_graph_artifacts`, lines 383–540).
   - Add CLI flags (arg parser at lines 603–634):
     - `--supabase-sink` (bool, default from env `LIA_INGEST_SUPABASE=1`).
     - `--supabase-target` (`production|wip`, default `production`).
     - `--generation-id` (string; default `f"gen_{utcnow().strftime('%Y%m%d%H%M%S')}"`).
   - In the main flow, after the existing `_write_jsonl` calls at lines 505–509:
     ```python
     if args.supabase_sink:
         sink = SupabaseCorpusSink(target=args.supabase_target)
         sink.write_generation(...)          # from the audit + plan counts
         sink.write_documents(doc_rows)      # derived from ParsedArticle + audit
         sink.write_chunks(chunk_rows)       # produced alongside parsed_articles
         sink.write_normative_edges(typed_edges)
         sink.finalize(activate=True)
     ```
   - The existing Falkor write at `src/lia_graph/ingestion/loader.py:125` (`client.execute_many(plan.statements, strict=strict)`) stays as-is; Supabase is purely additive.

5. **`Makefile`** (`phase2-graph-artifacts`, line 42–43).
   - Add a second target `phase2-graph-artifacts-supabase` that invokes the same command with `--supabase-sink --supabase-target production` so staging ops can trigger a full ingest without remembering flags.

6. **`docs/guide/env_guide.md`** — add a short "Corpus refresh" section pointing at the new Makefile target and explaining: local dev never needs to run the sink; staging needs to run it once (or after corpus changes) against cloud Supabase before the runtime cutover will have data to serve.

### Acceptance (Phase A)

- `make phase2-graph-artifacts-supabase` run against cloud writes non-zero counts into `documents`, `document_chunks`, `corpus_generations`, `normative_edges`.
- A second run produces zero row duplicates (verified by `SELECT count(*)` pre/post) and a single `is_active=true` generation.
- `tests/test_ingestion_supabase_sink.py` all green against a fresh `supabase db reset` local DB.

---

## Phase B — Staging runtime cutover

### Files to create

7. **`src/lia_graph/pipeline_d/retriever_supabase.py`** (new, ~250 LOC).
   - Mirrors the public signature of `src/lia_graph/pipeline_d/retriever.py` so `orchestrator.py` can swap adapters with one line.
   - `retrieve_graph_evidence(plan: GraphRetrievalPlan) -> EvidenceBundle` implementation:
     - Uses `supabase_client.get_supabase_client()` (already guards `LIA_STORAGE_BACKEND=supabase`).
     - Entry-point resolution: `client.table("documents").select(...).in_("doc_id", plan.entry_point_candidates)`.
     - Chunk expansion: if the plan asks for text, call the existing `hybrid_search` RPC (defined in baseline at line ~264) via `client.rpc("hybrid_search", {...})` with the plan's query + filters; else direct `table("document_chunks").select(...)`.
     - Temporal filters and vigencia checks: pass `plan.as_of_date` through to RPC params (`effective_date`) so the existing `20260411000003_fts_rpc_effective_date_param.sql` behavior applies — that migration is folded into the baseline.
   - Must return the exact same `EvidenceBundle` shape as `retriever.py` — do not change downstream synthesis.

8. **`src/lia_graph/pipeline_d/retriever_falkor.py`** (new, ~300 LOC).
   - Same public signature as `retriever.py`. Uses `src/lia_graph/graph/client.py` `GraphClient.execute()` with `GraphWriteStatement` to issue Cypher.
   - Port the bounded BFS from `retriever.py` into Cypher with the same neighbor sort (temporal → edge-kind priority → direction). Use parameterized Cypher and a per-request statement budget.
   - Graph name comes from `FALKORDB_GRAPH` (default `LIA_REGULATORY_GRAPH`); URL from `FALKORDB_URL`. Both are already set correctly per env file.
   - Fallback: on any Falkor error, propagate — do **not** silently fall back to artifacts. The operator must see Falkor outages.

### Files to modify

9. **`src/lia_graph/pipeline_d/orchestrator.py`** (the call site for `retrieve_graph_evidence`, roughly line 74 — the research agent documented this).
   - Read two env flags once at module import:
     - `LIA_CORPUS_SOURCE` ∈ `{"artifacts", "supabase"}`, default `"artifacts"`.
     - `LIA_GRAPH_MODE` ∈ `{"artifacts", "falkor_live"}`, default `"artifacts"`.
   - Pick the adapter per-request based on those flags. Keep both adapters loadable so a future request-level override (header) stays cheap.
   - Emit diagnostics on the `PipelineCResponse`: `diagnostics.retrieval_backend = LIA_CORPUS_SOURCE` and `diagnostics.graph_backend = LIA_GRAPH_MODE`.

10. **`scripts/dev-launcher.mjs`** — inside `buildRuntimeEnv`:
    - `mode === "local"`: leave both flags unset (they default to `"artifacts"` / `"artifacts"`).
    - `mode === "staging"`: set `env.LIA_CORPUS_SOURCE = "supabase"` and `env.LIA_GRAPH_MODE = "falkor_live"`.
    - `mode === "production"`: exit unchanged (Railway will carry its own envs).
    - Also update the preflight `runDependencySmoke` call list so staging verifies both Supabase and Falkor are healthy before the server binds.

11. **`src/lia_graph/dependency_smoke.py`** — extend `_check_falkordb()` (research agent pointed at lines ~273–354) to also run `MATCH (n) RETURN count(n) AS n` and compare against a configurable floor (`LIA_FALKOR_MIN_NODES`, default 500). Fail preflight if the staging Falkor is empty so we never boot staging against an un-ingested graph.

12. **`tests/test_phase3_graph_planner_retrieval.py`** and a new `tests/test_retriever_supabase.py`:
    - Parametrize the existing suite over both adapters so the contract stays identical.
    - The Supabase test uses the local docker Supabase seeded from the baseline + Phase A sink fixture rows.
    - The Falkor test uses the local docker Falkor (`lia-graph-falkor-dev`) with a seeded tiny graph.

13. **`docs/guide/orchestration.md`** — flip the paragraph at line ~1006 that currently says Falkor "is not yet the live per-request traversal engine." Replace with the new runtime split (artifacts in dev, supabase+falkor in staging) and reference the `LIA_CORPUS_SOURCE` / `LIA_GRAPH_MODE` flags. Per `AGENTS.md`, also update the `/orchestration` HTML map in `frontend/src/app/orchestration/shell.ts` and `frontend/src/features/orchestration/orchestrationApp.ts` in the same change.

### Acceptance (Phase B)

Concrete, must all pass:

1. `npm run dev` preflight shows `retrieval_backend=artifacts`, `graph_backend=artifacts`; login + a probe chat turn return an answer whose diagnostics confirm both.
2. `npm run dev:staging` preflight shows `retrieval_backend=supabase`, `graph_backend=falkor_live`; login + the same probe chat turn return an answer whose diagnostics confirm both and whose text matches the artifact-mode answer on a small regression suite of 5 curated questions.
3. Temporarily renaming `artifacts/parsed_articles.jsonl` → `.bak` and rerunning `dev:staging` still serves answers (proves the hot path is Supabase, not the filesystem). Rename back after.
4. Temporarily blocking outbound Falkor traffic (set `FALKORDB_URL` to an invalid host for one run) causes `dev:staging` to fail preflight with a clear error, not silently fall back to artifacts.
5. `npm run dev` unaffected by (3) and (4) — it never touched cloud infra.

---

## Out of scope

- Production mode (`npm run dev:production`) remains a Railway concern; the `LIA_CORPUS_SOURCE` / `LIA_GRAPH_MODE` flags will carry over automatically when the Railway env vars are set to the staging values.
- Embedding generation stays where it is (`src/lia_graph/embedding_ops.py`). The sink leaves `document_chunks.embedding` NULL and relies on the existing embedding worker to populate it.
- Migrating ingestion off the filesystem entirely. Artifacts stay as local dev's source of truth, and as a recovery backup.

## Handoff checklist

Before handing to the implementing agent:

- Read this doc top to bottom.
- Read `docs/guide/orchestration.md` and `docs/guide/env_guide.md` for the runtime and env context.
- Confirm the cloud DB is already linked (`supabase/.temp/project-ref` exists). If not, run `supabase link --project-ref utjndyxgfhkfcrjmtdqz --password '<pw>'` first. The current DB password was rotated after the prior session — ask the owner.
- Phase A must go first and be green in tests before touching Phase B.
