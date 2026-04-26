# Retrieval runbook — line-level

This doc walks every line of work that happens between the planner emitting a `GraphRetrievalPlan` and the orchestrator receiving a populated `GraphEvidenceBundle`. Two backends are covered:

- `pipeline_d/retriever_supabase.py` — the cloud path used in `dev:staging` and `production` (`LIA_GRAPH_MODE=falkor_live`, `LIA_CORPUS_SOURCE=supabase`).
- `pipeline_d/retriever_falkor.py` — the cloud graph traversal that augments the Supabase chunks with `:ArticleNode` neighborhoods.

The dev artifact path (`retriever.py`) shadows the cloud path's contract but reads from `artifacts/parsed_articles.jsonl` + `artifacts/typed_edges.jsonl` instead. It is intentionally dumber and not detailed here.

## Top-level entry point — `retrieve_graph_evidence`

`pipeline_d/retriever_supabase.py:47-102`. Called from `pipeline_d/orchestrator.py` after the planner emits the plan. Receives `(plan, client=None)`. Returns `(hydrated_plan, evidence_bundle)`.

### Step 1 — Build the FTS query string

`_build_query_text(plan)` at line 108-122. Concatenates entry-point lookup values + topic hints + the raw user message. Output is a space-separated string, ~50 tokens typical. **Never `None`.** Consumed by both Postgres FTS (`plainto_tsquery` fallback path) and the OR-builder (preferred path).

### Step 2 — Hybrid search RPC call

`_hybrid_search(db, plan, query_text)` at line 125-189. Builds a payload and hits Supabase RPC `hybrid_search`. Critical fields:

| Field | Value | Why |
|---|---|---|
| `query_embedding` | `_zero_embedding()` (768 zeros) | Embedding gen happens server-side via `query_text` → no client-side embedding |
| `query_text` | the concatenation from Step 1 | FTS fallback if `fts_query` is empty |
| `filter_topic` | **`None`** (deliberate) | Comment at line 138-141: "topic is a planner-side signal, not a recall predicate. Cross-topic anchors must stay reachable" |
| `filter_pais` | `"colombia"` | Hard-wired |
| `match_count` | `max(primary_limit + connected_limit + support_limit, 24)` | Keeps the candidate pool wide enough |
| `fts_query` | `_build_fts_or_query(query_text)` | OR-joined terms → forces OR semantics over the default AND |
| `filter_subtopic` | `plan.sub_topic_intent` if any | Only set when the planner detected a curated subtopic |
| `subtopic_boost` | `_resolve_subtopic_boost_factor()` (default 1.5, env-overridable) | Multiplier applied in RRF when chunk's `subtema = filter_subtopic` |

**The subtopic-args fallback.** Older Supabase deployments reject the `filter_subtopic` + `subtopic_boost` payload keys. The retriever does a try/except + retry without them at line 168-178. Client-side subtopic boost (`_apply_client_side_subtopic_boost`) handles the legacy DBs.

### Step 3 — Anchor article fetch (bypasses FTS)

`_fetch_anchor_article_rows(db, plan)` at line 310-353. For every entry_point with `kind == "article"` in the plan, does:

```python
db.table("document_chunks")
  .select("chunk_id, doc_id, chunk_text, summary, topic, knowledge_class, concept_tags, relative_path")
  .like("chunk_id", f"%::{key}")
  .limit(8)
  .execute()
```

The `chunk_id` convention from the sink is `doc_id::article_key`, so `LIKE %::<key>` matches every chunk for that article across every doc. **This bypasses FTS entirely** — anchor articles never get out-ranked because the planner already proved they should be primary.

Each anchor row is tagged with `rrf_score = 1.0` and `fts_rank = 1.0` (synthetic, line 350-351). This sentinel value is later read by `_augment_with_topic_supplementary` to detect anchor-band rows.

**Edge case — prose-only anchors don't match.** If the planner extracts an article-key like `"norma-base"` (a slug for prose-only articles), the chunk_id lookup fails because the loader writes prose-only chunks under `whole::source_path` form, not `norma-base`. Per the v5 §6.3 fix, the linker now writes edges with `whole::` keys, but the chunk_id convention in `document_chunks` still uses `article_key`. **The anchor fetch only finds numbered articles reliably.**

### Step 4 — Merge anchors first

`_merge_rows_prefer_anchors(anchor_rows, fts_rows)` at line 432-456. Returns `anchor_rows + [fts_row for fts_row in fts_rows if not in anchor_keys]`. Order matters because downstream consumers walk in order:

- `_classify_article_rows` picks primary articles starting from the front.
- `_collect_support` picks support_documents starting from the front.

So anchor rows always win when they're available.

### Step 5 — (DISABLED) Topic supplementary fetch

`_augment_with_topic_supplementary(db, plan, query_text, chunk_rows)` — defined at ~line 358-430 but **NOT invoked** (line 64 has the call site commented out as of 2026-04-26 evening).

History: added 2026-04-26 evening as a §1.B fix attempt. Empirically regressed `impuesto_patrimonio_pn` and `conciliacion_fiscal` from `chunks_off_topic` to `pipeline_d_no_graph_primary_articles` because supplementary chunks crowded out anchor classification. Reverted, helper kept for reference. Re-enabling needs a smarter `_collect_support` (2-pass that decouples support_doc choice from chunk_rows order). See `docs/aa_next/next_v5.md §1.C` for the full incident catalog.

### Step 6 — Load parent docs

`_load_documents_for_rows(db, chunk_rows)` queries `documents` table for every distinct `doc_id` in chunk_rows. Returns `dict[doc_id → row]`. Used downstream to attach `topic`, `relative_path`, `first_heading`, `knowledge_class`, etc. to chunks for support_document construction.

### Step 7 — Classify article rows

`_classify_article_rows(plan, chunk_rows, documents_by_doc_id)` (around line 470+). Walks chunk_rows and decides which become **primary articles**, **connected articles**, or are skipped. Decision rules:

- Anchor rows (rrf_score==1.0 sentinel) get classified first regardless of position.
- For non-anchor rows: a chunk_id matching one of the planner's `article` entry_points becomes primary; chunks reached via `connected_article` entry points become connected.
- Limits enforced by `plan.evidence_bundle_shape`: typically `primary_article_limit ≤ 5`, `connected_article_limit ≤ 5`.

**This is where `pipeline_d_no_graph_primary_articles` originates.** If the classifier returns an empty primary tuple, the orchestrator (`orchestrator.py:547-549`) sets `answer_mode = "graph_native_partial"` and `fallback_reason = "pipeline_d_no_graph_primary_articles"` BEFORE the coherence gate even runs.

### Step 8 — Reform collection

`_collect_reforms(plan, chunk_rows)` builds the `related_reforms` tuple from chunks tagged with reform-citation patterns. Capped at `related_reform_limit` (typically 4).

### Step 9 — Support document selection

`_collect_support(plan, documents_by_doc_id, chunk_rows)` at line 540-579. **This is where the coherence-gate's `chunks_off_topic` problem ultimately bites.** Algorithm:

```python
ordered_doc_ids = []
seen = set()
for row in chunk_rows:
    doc_id = row['doc_id']
    if not doc_id or doc_id in seen: continue
    if doc_id not in documents_by_doc_id: continue
    seen.add(doc_id)
    ordered_doc_ids.append(doc_id)
    if len(ordered_doc_ids) >= limit: break  # support_document_limit, typically 5
```

Walks chunk_rows IN ORDER. Picks the first `limit` unique doc_ids. **No topic-aware reservation.** A doc tagged with the router topic that happens to land in chunk_rows position 6 will not be in support_documents if positions 1-5 are different docs.

For each picked doc_id, builds a `GraphSupportDocument` (line 561-577). Critical field:

```python
topic_key = str(row.get("topic") or "") or None  # ← from documents.topic, NOT from chunk.topic
```

The `topic_key` on `GraphSupportDocument` is the parent **document's** topic, not the chunk's topic. Empirically (verified 2026-04-26) chunks always inherit their doc's topic, so the distinction doesn't matter in practice — but if a future ingest variant tags chunks per-section, the gate would still see only doc.topic.

### Step 10 — Plan hydration

`with_resolved_entry_points(plan, resolved_entries)` at line 79. Returns a copy of the plan with the entry_points decorated with `resolved_key` (the actual chunk's article_key when found). Consumed downstream by the orchestrator for citation rendering.

### Step 11 — Diagnostics + return

Builds the `diagnostics` dict (line 80-93) including `retrieval_backend`, `chunk_row_count`, `document_row_count`, `planner_query_mode`, `temporal_context`, `retrieval_sub_topic_intent`. Empty chunk_rows trigger `_diagnose_empty_chunks(db)` to populate `empty_reason` with the specific cause.

Returns `(hydrated_plan, GraphEvidenceBundle(primary_articles, connected_articles, related_reforms, support_documents, citations, diagnostics))`.

## The hybrid_search SQL — RRF formula in detail

Defined at `supabase/migrations/20260421000000_sub_topic_taxonomy.sql:70-318` (current version). Three CTEs:

### CTE `fts` (lines 133-181)

Filters `document_chunks` by:

- `dc.search_vector @@ effective_tsq` — the FTS predicate.
- `(filter_topic IS NULL OR dc.topic IN (filter_topic, filter_topic || '_parametros'))` — topic filter; **NULL means no filter, all topics admitted**.
- `dc.pais = filter_pais` (if set).
- `dc.knowledge_class = filter_knowledge_class` (if set).
- `dc.sync_generation = filter_sync_generation` (if set).
- Vigencia exclusion: not in `('derogada', 'proyecto', 'suspendida')` unless an effective-date filter is also set.
- `retrieval_visibility != 'backstage_only'`.
- Effective-date constraint: `effective_date IS NULL OR effective_date <= filter_effective_date_max`.

Ranks by `ts_rank_cd(dc.search_vector, effective_tsq) DESC`, then `LIMIT match_count`. The `ROW_NUMBER()` window function tags each row with its rank position (`rn`), used in RRF.

### CTE `semantic` (lines 182-228)

Same shape as `fts` but ranks by vector similarity:

```sql
1 - (dc.embedding <=> query_embedding) AS similarity
```

The `<=>` operator is pgvector's cosine distance; `1 - distance` gives similarity in [0, 1]. Ranks by similarity DESC, gets `LIMIT match_count`, tagged with `rn`.

**Important.** When the embedding is `_zero_embedding()` (the client always passes zeros), the vector similarity for every chunk is essentially `1 - cos(zero_vec, embedding) ≈ 1 - 0 = 1.0`. So the semantic CTE returns chunks ranked by ID order (or whatever default). It contributes minimally to ranking — FTS is doing the actual work.

### CTE `combined` (lines 231-278)

Full outer join on `chunk_pk`, then computes RRF score:

```sql
rrf_score = (
    (
        fts_weight / (rrf_k + COALESCE(f.rn, match_count + 1))
        + semantic_weight / (rrf_k + COALESCE(s.rn, match_count + 1))
    )
    *
    CASE
        WHEN filter_subtopic IS NOT NULL
             AND COALESCE(f.subtema, s.subtema) = filter_subtopic
        THEN effective_boost  -- typically 1.5
        ELSE 1.0
    END
)
```

- `rrf_k = 60` (default) — Reciprocal Rank Fusion smoothing constant. Larger k → flatter ranking distribution.
- `fts_weight = 1.0`, `semantic_weight = 1.0` (default).
- A chunk found in both CTEs gets contributions from both. A chunk found in only one CTE has `1 / (60 + match_count + 1)` from the other (effectively zero).
- Subtopic boost is the **only** topic-related boost. Topic itself is NOT a boost factor.

### Final SELECT

Lines 279-316. Returns chunks ordered by `rrf_score DESC LIMIT match_count`. Each row carries the chunk's full set of metadata fields including `topic`, `subtema`, `chunk_section_type`, etc.

## Graph traversal — `retriever_falkor.py`

The Supabase retriever returns chunks. The Falkor retriever ALSO runs (in `falkor_live` mode) and returns articles + connected articles via Cypher BFS. The orchestrator merges both. See `pipeline_d/retriever_falkor.py` for the Cypher queries; key audited in `docs/learnings/ingestion/falkor-edge-undercount-and-resultset-cap-2026-04-26.md` (Falkor 10k row cap, defensive guard).

## Known structural gaps (open as of 2026-04-26)

1. **No topic boost in hybrid_search.** Subtopic has a multiplier; topic doesn't. This is the root of the 4 thin-corpus topic refusals catalogued in `next_v5.md §1.C`. Fix candidate: SQL migration adds `topic_boost` parameter analogous to `subtopic_boost`.

2. **`_collect_support` selects strictly by chunk_rows order.** No reservation for router-topic docs. A narrow-topic doc that ranks 6th-of-20 won't make the support_document bundle. Fix candidate: 2-pass selection — first pass picks first N by rank, second pass fills remaining slots with router-topic docs found anywhere downstream.

3. **`_fetch_anchor_article_rows` only matches numbered articles.** The `chunk_id LIKE %::<key>` pattern doesn't catch prose-only anchors (e.g. `whole::path/to.md`). Fix candidate: extend the LIKE pattern to handle the `whole::` form when the planner detects a prose-only anchor.

4. **Vector path is essentially inert with zero embeddings.** Client passes `_zero_embedding()`, so the semantic CTE doesn't differentiate chunks. FTS is doing all the ranking work. Fix candidate: real embedding generation client-side (cost: extra Gemini call per query).

5. **The 2-doc `_SUPPORT_DOC_TOPIC_KEY_MATCH_MIN` threshold is brittle for thin-corpus topics with ≤ 3 docs.** Even when content is perfect, hybrid_search rarely brings 2+ narrow-topic docs to the top-5 support set. Fix candidate: 1-pass topic-aware filtering before support_doc selection (related to gap #2).

Each gap above corresponds to a specific failing topic in `next_v5.md §1.C`. Don't fix one without considering the others — they interact.
