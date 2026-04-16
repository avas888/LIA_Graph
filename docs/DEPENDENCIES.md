# LIA_Graph — External Dependencies

> What you (Ava) need to provision before I can build autonomously.

---

## Required Before Phase 1

### 1. Supabase Project
- **What**: A dedicated Supabase project for LIA_Graph
- **Why**: LIA_Graph has its own backend environment and must not share production state with any prior deployment
- **Free tier**: Yes (500 MB DB, 1 GB storage — plenty for dev)
- **What I need from you**:
  - `SUPABASE_URL` (e.g., `https://xxxx.supabase.co`)
  - `SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`
- **Setup**: https://supabase.com/dashboard → New Project
- **Rule**: Do not fall back to any previous Supabase project.

### 2. FalkorDB Cloud
- **What**: Managed graph database instance
- **Why**: Stores the shared regulatory graph (nodes + edges)
- **Free tier**: Yes (1 graph, 1 GB, 100 ops/sec — sufficient for dev/eval)
- **What I need from you**:
  - `FALKORDB_URL` (e.g., `redis://default:xxx@xxx.falkordb.io:6379`)
- **Setup**: https://app.falkordb.cloud → Sign up → Create database
- **Alternative**: FalkorDB can run as a Docker container on Railway ($0-5/mo).
  I can configure this myself if you add a Redis-compatible service to Railway.

### 3. OpenAI API Key
- **What**: OpenAI API key available to the LIA_Graph environment
- **Why**: Embeddings (text-embedding-3-small) + LLM (gpt-4o) for edge classification and composition
- **What I need from you**: The key or confirmation that the existing key should be installed into LIA_Graph's own env
- **Estimated cost for Phase 1**: ~$3-8 (edge classification: ~1.25M tokens)
- **Estimated cost for Phase 2**: ~$5-15 (composer testing with graph context)

### 4. Corpus Files Access
- **What**: The shared accountant corpus source files from Dropbox, with normativa, interpretacion and practica all present in the materialized root
- **Why**: Source material for shared corpus inventory, graph ingestion, and later shared retrieval across normative, interpretative, and practical layers
- **Note**: Older ET-specific references in this repo describe an early bootstrap slice, not the full corpus model used by Build V1.
- **Options** (pick one):
  - **(A) Connect Dropbox** — I pull files directly
  - **(B) Upload to workspace** — You zip the `knowledge_base/` families and share them here
  - **(C) Commit to repo** — You push the corpus files under `knowledge_base/` in LIA_Graph
- **Recommendation**: Option C (shared corpus versioned in repo, always available)

---

## Required Before Phase 3

### 5. Eval Golden Set
- **What**: `evals/pipeline_c_golden.jsonl` baseline dataset
- **Why**: Baseline for Pipeline D comparison
- **Status**: Already present in this repo

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
| Dedicated Supabase project | Create at supabase.com | 2 min |
| FalkorDB Cloud | Sign up at falkordb.cloud | 3 min |
| OpenAI key | Install into LIA_Graph env | 0 min |
| Corpus files | Choose option A, B, or C above | 5-10 min |

**Total setup time: ~10 minutes.** After that, I can run Phases 1-3 with high autonomy.
