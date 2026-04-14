# LIA_Graph — External Dependencies

> What you (Ava) need to provision before I can build autonomously.

---

## Required Before Phase 1

### 1. Supabase Project (2nd instance)
- **What**: A separate Supabase project for LIA_Graph dev
- **Why**: Isolation from production Lia_contadores data
- **Free tier**: Yes (500 MB DB, 1 GB storage — plenty for dev)
- **What I need from you**:
  - `SUPABASE_URL` (e.g., `https://xxxx.supabase.co`)
  - `SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`
- **Setup**: https://supabase.com/dashboard → New Project
- **Alternative**: If you prefer, I can reuse the existing Supabase project
  and create new tables with a `graph_` prefix. Less isolation but zero setup.

### 2. FalkorDB Cloud
- **What**: Managed graph database instance
- **Why**: Stores the ET knowledge graph (nodes + edges)
- **Free tier**: Yes (1 graph, 1 GB, 100 ops/sec — sufficient for dev/eval)
- **What I need from you**:
  - `FALKORDB_URL` (e.g., `redis://default:xxx@xxx.falkordb.io:6379`)
- **Setup**: https://app.falkordb.cloud → Sign up → Create database
- **Alternative**: FalkorDB can run as a Docker container on Railway ($0-5/mo).
  I can configure this myself if you add a Redis-compatible service to Railway.

### 3. OpenAI API Key
- **What**: Same key used by Lia_contadores
- **Why**: Embeddings (text-embedding-3-small) + LLM (gpt-4o) for edge classification and composition
- **What I need from you**: Confirm I should use the same `OPENAI_API_KEY`
- **Estimated cost for Phase 1**: ~$3-8 (edge classification: ~1.25M tokens)
- **Estimated cost for Phase 2**: ~$5-15 (composer testing with graph context)

### 4. Corpus Files Access
- **What**: The 24 ET Markdown files + supporting files from Dropbox
- **Why**: Source material for graph ingestion
- **Options** (pick one):
  - **(A) Connect Dropbox** — I pull files directly
  - **(B) Upload to workspace** — You zip the `Normativa/` folder and share it here
  - **(C) Commit to repo** — You push the corpus files to `corpus/et/` in LIA_Graph
- **Recommendation**: Option C (corpus versioned in repo, always available)

---

## Required Before Phase 3

### 5. Eval Golden Set
- **What**: `evals/pipeline_c_golden.jsonl` from Lia_contadores
- **Why**: Baseline for Pipeline D comparison
- **Status**: Already in the Lia_contadores repo; will copy during Phase 0

---

## Required Before Phase 4

### 6. Railway Project
- **What**: Railway deployment for LIA_Graph
- **Why**: Production hosting
- **What I need from you**: Railway project link or `RAILWAY_TOKEN`
- **Can defer**: Not needed until Phase 4

---

## Summary: What to Provision Now

| Item | Action | Time |
|------|--------|------|
| Supabase 2nd project | Create at supabase.com | 2 min |
| FalkorDB Cloud | Sign up at falkordb.cloud | 3 min |
| OpenAI key | Confirm reuse | 0 min |
| Corpus files | Choose option A, B, or C above | 5-10 min |

**Total setup time: ~10 minutes.** After that, I can run Phases 1-3 with high autonomy.
