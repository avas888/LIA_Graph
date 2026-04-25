# LIA_Graph — External Dependencies

> What has to be provisioned for the repo to run autonomously, with current status notes.

---

## Production-critical

### 1. Supabase (local + cloud)
- **What**: a dedicated Supabase project for LIA_Graph (cloud `utjndyxgfhkfcrjmtdqz`) plus a local Supabase CLI stack for `npm run dev`.
- **Why**: auth, tenant history, runtime state, corpus rows (`documents` / `document_chunks` / `corpus_generations` / `normative_edges` / `sub_topic_taxonomy`). Storage backend is `supabase` in every mode; the old filesystem backend was removed in the April 2026 env cut.
- **What is needed**:
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`
- **Status**: provisioned. Both `dev` and `dev:staging` preflights green. Migration baseline squashed into `20260417000000_baseline.sql` + `20260417000001_seed_users.sql` + `20260418000000_normative_edges_unique.sql`.

### 2. FalkorDB (local + cloud)
- **What**: managed cloud FalkorDB instance (`LIA_REGULATORY_GRAPH`) + local docker container for parity runs.
- **Why**: cloud FalkorDB IS the live per-request traversal engine in `dev:staging` and production — `retriever_falkor.py` issues a bounded Cypher BFS per chat turn. In `dev`, local Falkor is used for environment parity only.
- **What is needed**:
  - `FALKORDB_URL`
  - optional `LIA_FALKOR_MIN_NODES` (default `500`) — blocks staging/prod boot when cloud graph is empty
- **Status**: provisioned. Graph validation green (`artifacts/graph_validation_report.json`: 2633 nodes / 20495 edges / ok=true).

### 3. Gemini API Key
- **What**: Google AI Studio / Gemini API key.
- **Why**:
  - Embeddings (text-embedding-004) for `document_chunks.embedding`.
  - LLM (Gemini Flash) for the PASO 4 subtopic classifier in `ingest_subtopic_pass.py`.
  - Optional LLM polish of the final chat answer (`answer_llm_polish.py`, gated by `LIA_LLM_POLISH_ENABLED`).
- **What is needed**: `GEMINI_API_KEY` in `.env.local` (gitignored). Intentionally NOT in `.env.dev.local` or `.env.staging` so it never gets committed.
- **Status**: provisioned.
- **Rough LLM cost envelope**: full-corpus re-ingest with PASO 4 classification ≈ $5–15; chat-time polish cost is per-request (template answer is the safety net if the key is missing).

### 4. Corpus Files Access
- **What**: Colombian accountant corpus under `CORE ya Arriba`, `to upload`, and `to_upload_graph/` in the Dropbox source root.
- **Why**: source material for the audit-first ingestion, the canonical corpus manifest, the graph, and Supabase chunk rows.
- **How it's wired**: `scripts/sync_corpus_snapshot.sh` copies the three roots into the gitignored `knowledge_base/` directory before `make phase2-graph-artifacts-supabase`.
- **Status**: mounted from the host Dropbox. `to_upload_graph/` was added in `v2026-04-20-ui15` to back the admin drag-to-ingest UI.

### 5. Eval Golden Set
- **What**: `evals/pipeline_c_golden.jsonl` baseline dataset.
- **Status**: in the repo.

### 6. Railway Project
- **What**: Railway deployment for production (`npm run dev:production` explicitly exits with a Railway notice).
- **Status**: scaffold only; Railway wiring is the one externally-provisioned dependency that is still a follow-up (see `docs/done/next/env_fixv1.md` §Follow-up item 2). Staging runs against the cloud infra locally via `npm run dev:staging`.

---

## Summary

| Item | Status |
|------|--------|
| Supabase (local + cloud) | Provisioned |
| FalkorDB (local + cloud) | Provisioned |
| Gemini API key | Provisioned |
| Corpus files | Mounted from Dropbox |
| Eval golden set | In repo |
| Railway production | Scaffolded, not yet wired |

The Gemini key is the only secret that has to live per-developer in `.env.local`. Every other value is either in a checked-in mode-specific env file (`.env.dev.local` / `.env.staging`) or set deterministically by `scripts/dev-launcher.mjs` per run mode.
