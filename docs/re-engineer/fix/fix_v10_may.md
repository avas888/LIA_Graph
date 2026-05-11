## fix_v10_may.md — promote the Interpretación de Expertos corpus to a first-class citizen

> **Drafted 2026-05-11 PM Bogotá** by claude-opus-4-7 after the
> Railway production fix shipped (commit `2d50f93`,
> `.railwayignore` whitelist for `knowledge_base/**/*.md`) restored
> the panel by ensuring the 105 `interpretative_guidance` markdown
> files actually land inside the container at `/app/knowledge_base/`.
> That commit is a band-aid: the panel works only because the
> retriever does a filesystem scan of shipped markdown. The corpus
> is invisible to embeddings, vector search, the rerank stage,
> vigencia, the topic-gate, the coherence-gate, and the FalkorDB
> graph. Every other corpus in the system (`normative_base`,
> `practica_erp`) is a Supabase + FalkorDB first-class citizen.
> Interpretation is the only one still living on the disk image
> like a 1990s static asset.
>
> **Audience.** Zero-context fresh LLM or engineer. This doc is
> self-contained. Skim `fix_v9_may.md §0` if you want the topic-gate
> + planner-anchor archaeology; skim `docs/orchestration/orchestration.md`
> §"Runtime Read Path" for the env-flag matrix that every retrieval
> path now respects. Nothing in this fix changes that matrix — it
> rides it.
>
> **What this is.** A four-phase migration plan (10A → 10D) that
> ends with the Interpretación de Expertos corpus retrieved through
> the same `hybrid_search` RPC the chat already uses, scored by
> RRF over Gemini-embedding-001 vectors + tsvector FTS, reranked
> by the same live reranker, gated by the same topic-gate and
> coherence-gate, and reachable from the graph planner via
> `INTERPRETS` edges from interpretation nodes to the norms they
> analyze. Each phase has a six-gate lifecycle entry per
> `docs/aa_next/README.md` policy.
>
> **What this is not.** Not a UI redesign — the expert-panel UX in
> `frontend/src/features/chat/expertPanelController.ts` is fine.
> Not a content rewrite — the 105 markdown sources stay as the
> authoring surface; the change is downstream of authoring. Not a
> rerank-model change. Not a six-question hack — every behavior in
> this plan must generalize across all 105 docs.
>
> **Scope guard.** Closing bar at the end of phase 10D: (a) the
> SME `§1.G` 36-Q panel result holds at or above its pre-v10
> baseline (current standing-baseline 34/36 acc+ post-fix_v8f); AND
> (b) for a new 20-question Expert-Panel SME mini-panel (see §5.4),
> ≥ 70% of questions surface at least one relevant expert card in
> top 3 with SME accept; AND (c) the empty-panel rate on chats that
> returned ≥ 1 citable normative article is < 5%. All three are
> dual-gated (engineer harness + SME). The expert-panel mini-panel
> is brand new — operator authorizes the SME run before launching
> per `feedback_sme_panel_explicit_request_only`.

---

## 0. Inheritance from fix_v1..fix_v9 + new invariants

Everything in `fix_v9_may.md §0` carries forward unchanged. Additional
invariants this doc commits to:

- **fix_v9 §9a and §9b are assumed live** by the time phase 10A
  starts. If 9a/9b are still mid-ship, phase 10A may proceed in
  parallel because it touches ingestion, not retrieval — but no
  10B/10C/10D launch until 9a/9b's SME panel re-runs are green.
- **The `.railwayignore` whitelist (commit `2d50f93`) is the
  fallback floor**, not the destination. After phase 10D ships, the
  whitelist can stay (cheap, harmless) but the filesystem catalog
  must no longer be the canonical source of truth.
- **No new RPC.** Phase 10B reuses the existing `hybrid_search` RPC
  (post-`20260512000000_topic_filter_soft.sql`) with the
  `filter_knowledge_class` parameter the schema already exposes.
  If the contract proves insufficient (open question §9.2), the
  fallback is an additive RPC, not a fork.
- **No DDL on `document_chunks` unless §9.3 forces it.** The
  baseline migration already provides every column the
  interpretation corpus needs: `embedding (vector)`, `search_vector
  (tsvector)`, `knowledge_class`, `topic`, `subtema`, `trust_tier`,
  `concept_tags`, `tema`, `tipo_de_documento`, plus the vigencia
  trio (`vigencia`, `vigencia_basis`, `vigencia_ruling_id`).
- **Graph integration is phase 10C, behind a feature flag.** It
  ships AFTER 10A + 10B are stable in production. The
  filesystem-only catalog stays available as a fallback path the
  entire time so a graph regression never empties the panel.
- **Provider / authority preservation is non-optional.** The
  current `catalog.py` does provider extraction at READ time off
  the raw markdown (line 55, `extract_expert_providers(preview_text)`).
  Every phase in this plan must preserve provider strings into the
  chunk row so that `_build_runtime_for_doc` in
  `interpretacion/orchestrator.py:87-133` can keep building expert
  cards without re-reading the markdown.

---

## 1. The diagnosis (verified 2026-05-11 PM)

The Railway production deploy at `liagraph-production.up.railway.app`
returned an empty Interpretación de Expertos panel for a Panama /
transfer-pricing query that successfully retrieved 4 normative
articles (Art. 124-2, 260-1, 260-2, 260-5). Forensic walk:

### 1.A — Filesystem-only retrieval

`src/lia_graph/interpretacion/orchestrator.py:136-217`
(`_retrieve_interpretation_docs`) calls
`src/lia_graph/interpretacion/catalog.py:39-82`
(`list_local_interpretation_rows`). The catalog reads
`artifacts/canonical_corpus_manifest.json` from local disk
(`_MANIFEST_PATH`), filters
`knowledge_class == "interpretative_guidance"`, and resolves each
row's `absolute_path` against
`_WORKSPACE_ROOT / "knowledge_base"`. The function never touches
`SupabaseClient`, never invokes a Supabase RPC, never opens a
FalkorDB cursor. It is a pure-disk reader.

When Railway built the new container, `.railwayignore`'s `*.md`
glob stripped the 105 markdown files. The catalog returned an
empty tuple, scoring scored zero rows, and the panel's empty-state
copy `chat.experts.empty` from
`frontend/src/shared/i18n/catalogs.ts` rendered. The chat panel
worked because it routes through `retriever_supabase.py` →
`hybrid_search` RPC → cloud chunks half + cloud Falkor half.

### 1.B — `knowledge_class` lost in transit

`artifacts/canonical_corpus_manifest.json` carries the
`knowledge_class` field on every entry (1,007 `normative_base`,
169 `practica_erp`, 105 `interpretative_guidance`, 5 `unknown`).
But `artifacts/parsed_articles.jsonl` — the chunker output that
`SupabaseCorpusSink.write_chunks` writes against — has an empty
string in `knowledge_class` for every chunk. Verified by reading
the unique value set across the entire JSONL: `{''}`.

Implication: even if `interpretative_guidance` documents reach
Supabase via `documents` table writes (and they probably do, at
the document level, given the manifest is the source-of-truth for
the document loop), the corresponding chunks in `document_chunks`
have NO knowledge_class discriminator. A
`hybrid_search(filter_knowledge_class='interpretative_guidance')`
call against today's Supabase data would return zero rows.

This is the keystone bug. It's a one-field propagation hole between
two artifact stages, not a schema gap.

### 1.C — No embeddings on interpretation chunks

Because §1.B holds, the embedding-backfill pass in
`src/lia_graph/embedding_ops.py` cannot target interpretation
chunks selectively. It may have embedded them already as part of
its global sweep (verifiable; see §9.1 open question), but the
retriever has no way to ask for them.

### 1.D — No graph integration

`src/lia_graph/graph/schema.py:12-102` declares six node labels
(`ArticleNode`, `ReformNode`, `ConceptNode`, `ParameterNode`,
`SubTopicNode`, `TopicNode`). None of them represent expert
interpretations or their providers. The 16-edge relation
vocabulary (`REFERENCES`, `MODIFIES`, `COMPLEMENTS`,
`EXCEPTION_TO`, `DEROGATES`, `SUPERSEDES`, `SUSPENDS`,
`STRUCK_DOWN_BY`, `REVOKES`, `DEFINES`, `PART_OF`, `REQUIRES`,
`COMPUTATION_DEPENDS_ON`, `DECLARES_EXEQUIBLE`, `REGLAMENTA`,
`ANULA`, `CROSS_DOMAIN`) has no `INTERPRETS` edge.

Consequence: a planner Cypher query like *"give me all expert
interpretations of Art. 124-2 ET"* is structurally inexpressible.
The chat's planner can anchor on `MATCH (a:ArticleNode {key:
'art_124_2_et'})` and follow `MODIFIES` / `REFERENCES` edges, but
there's nothing to follow into interpretation space.

### 1.E — No vigencia, rerank, topic-gate, coherence-gate

The interpretation retrieval is scored by
`catalog.py:166-181`:
`raw_score = 2.5*ref_hits + token_hits + phrase_bonus +
topic_bonus + provider_bonus`. After scoring, results pass into
`rerank_runtimes()` (`interpretacion/rerank/`) — that IS the
adapter that calls the reranker, so reranking does happen, but
only over the lexical-only candidate set. The first-pass shortlist
is a bag-of-words match. There's no:

- vector similarity contribution to first-pass scoring
- vigencia v3 demotion / drop on the interpretation row itself
  (an interpretation of a derogated article is just as visible as
  one of a live article)
- topic-gate filter ON THE CARDS (the cross-topic content gate in
  `pipeline_d/answer_topic_gate.py` runs on the chat answer, not
  on the panel)
- coherence-gate validation on the cards as evidence

### 1.F — Deploy-coupled update cycle

Today, updating an interpretation (say, adding a Crowe analysis on
the Reforma Tributaria 2025) requires: edit markdown → commit →
push → Railway redeploy. For normative content, the same change
requires: edit markdown → `make phase2-graph-artifacts-supabase` →
done (next chat request sees it). The asymmetry penalizes
interpretation curation specifically — the corpus that benefits
most from rapid iteration (because legal commentary evolves fast)
has the slowest update path.

### 1.G — Scoring is pure lexical, RAM-bound

The 105 rows are scanned linearly on every request. With more
interpretations (the corpus is intentionally growing), this is
O(N) per chat turn. `@lru_cache(maxsize=1)` on
`list_local_interpretation_rows` saves the disk hit but not the
scoring loop. At 1,000 interpretations the scan + scoring will
add ≥ 50 ms of CPU per chat turn; at 5,000 it's a real latency
contributor.

### 1.H — Two separate paths for the same data

`run_expert_panel_request` (`orchestrator.py:220-329`) and
`run_citation_interpretations_request` (`orchestrator.py:332-433`)
both call `_retrieve_interpretation_docs` but with different
seed-construction logic. The cards rendered in the right-panel
chat surface vs. the cards rendered in the citation-detail modal
are siblings, not the same query. Today both share the lexical
catalog; in the target, both share `hybrid_search`.

---

## 2. What "first-class citizen" means — the contract

Before the workstreams, fix what we're aiming at. A corpus is a
first-class citizen when ALL of these hold:

1. **Storage parity.** Lives in `documents` + `document_chunks`
   tables, indexed exactly like `normative_base` chunks. Same
   `embedding` column, same `search_vector`, same `knowledge_class`
   discriminator, same vigencia trio.
2. **Retrieval parity.** Reachable through the standard
   `hybrid_search` RPC. No bespoke scoring loop in Python. RRF over
   FTS + cosine similarity. Same rerank stage. Same coherence and
   topic-gate logic.
3. **Graph parity.** Has its own node label in FalkorDB with
   typed edges to the normative entities it relates to. Planner
   anchors can traverse interpretation space the same way they
   traverse norm space.
4. **Vigencia parity.** Interpretations of derogated norms are
   demoted or dropped automatically. An interpretation of Art. 147
   ET (modified by Ley 1819/2016) ranks lower than an
   interpretation of Art. 115 ET (live, ICA deduction).
5. **Update parity.** A new interpretation flows into production
   through `make phase2-graph-artifacts-supabase` + an additive
   ingest, never through a Railway redeploy.
6. **Observability parity.** The pipeline trace
   (`tracers_and_logs/pipeline_trace.py`) records interpretation
   retrieval stages (anchor, hybrid_search, rerank, gate) exactly
   like it records normative retrieval today. The chat response's
   `diagnostics.retrieval_backend` extends to a sibling field
   `diagnostics.interpretation_backend` so we can see
   `supabase` / `filesystem` per turn.

Anything less is second-class. Today, interpretation fails on (1)
through (6).

---

## 3. Target architecture

### 3.A — Data model: zero schema migration needed

Per the schema audit, `document_chunks` already has every column
this needs:

| Column | What it holds for interpretations |
|---|---|
| `chunk_id` | stable hash of (`doc_id`, section heading or chunk index) |
| `doc_id` | the existing synthetic id (`local_interp_<hash>`) or a stable rename |
| `embedding` | Gemini-embedding-001 vector(768) — same dimension as norm chunks |
| `search_vector` | Spanish-tokenized tsvector over the chunk text |
| `knowledge_class` | the literal `'interpretative_guidance'` — already in the schema's allowed set since the baseline migration |
| `topic` | from `manifest.topic_key` |
| `subtema` | from `manifest.subtopic_key` (often null for interpretations) |
| `concept_tags` | inherited from the parent doc's normative_refs + interpretation's own theme tags |
| `tema` / `tipo_de_documento` | `'interpretation'` / `'expert_commentary'` |
| `trust_tier` | `'medium'` default (matches `catalog.py:60` setdefault) — could be uplifted per provider via §9.5 |
| `vigencia` | `'vigente'` by default; downgraded when the underlying norm's vigencia degrades (see §3.E) |
| `vigencia_basis` | the underlying norm + ruling that drives the demotion |
| `vigencia_ruling_id` | propagated from the linked norm |
| `chunk_section_type` | use the existing `'general'` value initially; could be refined later to mark e.g. `'normative_overlay'` for sections that interpret a specific article vs `'historical'` for archaeology sections |

The one column that may need a non-schema decision is
`authority` (on `documents`) — today it defaults to the first
provider label or `"Fuente profesional"`. We can keep that. We do
NOT need a new column for provider list; the existing
`provider_labels` field on the document row in the manifest can
become `documents.provider_labels` if we widen the documents table
later, but for v10 we can survive by storing providers in
`concept_tags` and reconstructing them at synthesis time, OR by
adding a `provider_labels (text[])` column to `documents` in a
small DDL (open question §9.3).

### 3.B — Retrieval contract: one `hybrid_search`, two callers

The new file `src/lia_graph/interpretacion/retriever_supabase.py`
exposes a single function:

```python
def fetch_interpretation_candidates(
    *,
    query_seed: str,
    article_refs: tuple[str, ...],
    topic: str | None,
    pais: str,
    top_k: int,
) -> InterpretationKnowledgeBundle:
    """Same return shape as _retrieve_interpretation_docs returns today."""
```

Internally it:

1. Computes the query embedding via
   `lia_graph.embeddings.get_query_embedding` (the same path the
   chat retrieval uses; cached).
2. Builds an FTS query that *injects the article refs as required
   tokens* — this preserves the current scoring's `2.5*ref_hits`
   weighting in a way the SQL side understands. Example: a seed
   "deducibilidad de pagos al exterior" with article_refs
   `("art_124_2_et",)` becomes a tsquery like
   `'deducibilidad' & 'pagos' & 'exterior' & 'art_124_2_et'` (the
   ampersand asks Postgres for all-match boost; the absence of a
   ref produces zero false negatives because the FTS half is
   joined by RRF, not by intersection).
3. Calls `hybrid_search` with `filter_knowledge_class =
   'interpretative_guidance'`, `boost_topic = topic`,
   `filter_pais = pais`, and the computed `query_embedding` +
   `fts_query`.
4. Maps the returned rows into the same `DocumentRecord` shape
   `catalog.py` produces today, so
   `orchestrator._build_runtime_for_doc` doesn't need to change.
5. Returns `retrieval_diagnostics` matching the existing shape
   (`mode`, `candidate_rows`, `selected_docs`) PLUS a new
   `interpretation_backend` field documenting whether this came
   from `supabase` or the `filesystem` fallback.

`_retrieve_interpretation_docs` becomes a 12-line dispatcher: if
`LIA_INTERPRETATION_SOURCE == 'supabase'` and the SupabaseClient
is wired, call the new function; else fall back to the
filesystem catalog. The fallback never disappears in v10 — it's
the safety floor.

### 3.C — Graph integration: `Interpretation` + `INTERPRETS`

In FalkorDB we add:

- **Node label** `InterpretationNode` with properties:
  `doc_id` (key), `source_label`, `authority`, `trust_tier`,
  `topic`, `pais`, `provider_labels` (list), `relative_path`
  (for debug only).
- **Edge labels** (additive to the existing 16):
  - `INTERPRETS` — from `InterpretationNode` to `ArticleNode`. One
    edge per article the interpretation references. Cardinality
    is many-to-many.
  - `AUTHORED_BY` — from `InterpretationNode` to a new
    `ExpertProviderNode` (keyed by `provider_name`). Optional in
    v10; can defer to a v10.1 polish pass.
  - `COVERS_TOPIC` — from `InterpretationNode` to `TopicNode`.

The planner then anchors interpretations the same way it anchors
articles. When a chat turn cites `Art. 124-2 ET`, the planner can
issue:

```cypher
MATCH (a:ArticleNode {key: 'art_124_2_et'})<-[:INTERPRETS]-(i:InterpretationNode)
RETURN i.doc_id, i.authority, i.trust_tier
ORDER BY i.trust_tier DESC LIMIT 8
```

and hand the doc_ids back to the retriever as a graph-anchored
candidate seed. This is the SAME pattern the planner uses today
for normative anchors (see `pipeline_d/planner.py` and the ICA
Art. 115 anchor added in fix_v8 §3g).

### 3.D — Provider / authority preservation

The current `catalog.py:55` extracts providers via
`extract_expert_providers(preview_text)` AT READ TIME. The
expensive part is `_first_heading` + `extract_article_refs` +
`extract_expert_providers` over the full markdown — fine for 105
docs but architecturally wrong: it means provider attribution
depends on whether the .md file is on disk, not on whether the
chunk exists.

In the target, provider extraction happens ONCE at ingest, and
the result lives in:

- `documents.authority` — primary provider label (already there)
- `documents.provider_labels` — full list (new column, see §9.3),
  OR encoded into `concept_tags` for v10 zero-DDL ship
- `InterpretationNode.provider_labels` in Falkor (new property)
- `ExpertProviderNode` in Falkor with one node per distinct
  provider (optional, v10.1)

`orchestrator._build_runtime_for_doc` reads providers from the
row payload (line 98-122), not from the raw text, after v10
ships. It already half-does this — it accepts a `row` and falls
back to re-extracting from `corpus_text`. The v10 change makes
the row-based path authoritative; the text-based fallback becomes
unreachable when SupabaseCorpusSink populates providers correctly.

### 3.E — Vigencia coupling: derived, not authored

An interpretation never has its own vigencia — it inherits from
the norms it interprets. The rule: if ALL articles an
interpretation references are demoted (vigencia ≠ 'vigente'), the
interpretation chunk's `vigencia` is demoted to `'historical'`. If
ANY referenced article is fully live, the interpretation stays
`'vigente'`.

Implementation: this is a derived column populated at ingest by
joining the interpretation's `article_refs` against the
`norm_vigencia_history` table (the canonical source-of-truth per
the memory `feedback_vigencia_norm_keyed`). The vigencia v3 demote
logic in `retriever_supabase.py` then DROPS or DEMOTES historical
interpretation chunks exactly like it does normative chunks.

This is one of the most valuable side effects of phase 10A — it
means an old Crowe interpretation of Art. 147 ET (now significantly
modified by Ley 1819/2016) will NOT confuse the panel on a current
question about pérdidas fiscales. Today the catalog has no concept
of this.

### 3.F — Synthesis layer: keep `expert_summary_overrides`

The baseline migration includes
`expert_summary_overrides` (`override_key`, `logical_doc_id`,
`provider_name`, `source_hash`, `summary_text`, `summary_origin`,
`summary_quality`). This is the right home for human-curated
card summaries that override the auto-generated ones. v10 does
NOT touch this table — it remains the polish layer that wraps the
retrieved chunks. The synthesis path
(`interpretacion/synthesis.py::synthesize_expert_panel`) keeps
joining against it.

---

## 4. Migration phases — 10A through 10D

### Phase 10A — Carry `knowledge_class` through the chunk pipeline

**The keystone change.** Without 10A, nothing else works.

**Status: ✅ CLOSED 2026-05-11 PM Bogotá.** Phase 10A complete on
every dimension: code shipped, cloud backfill ran (2,275 chunks
retagged across 274 docs), G2 sink-parity guardrails landed, SME
§1.G 36-Q regression panel rerun **byte-identical to the
post_fix_v8f_temp0 baseline** — 26 strong / 8 acceptable / 1 weak /
1 refused = **34/36 acc+** with zero per-question class deltas. Run:
`evals/sme_validation_v1/runs/20260511T182942Z_post_fix_v10a_kc_backfill/`.

**Phase 10B status: 🧪 code shipped, mini-panel ran (42.9 % baseline).**
**Phase 10C v0 status: 🧪 code shipped, mini-panel re-ran (57.1 %, REFINE).**
2026-05-11 PM Bogotá: 21-Q expert-panel mini-panel scored **12/21
accept = 57.1 %** in top-3 against staging cloud Supabase with the
Phase 10C anchor-boost path live (vs 9/21 = 42.9 % on Phase 10B
alone). §5.4 decision rule lands this in REFINE (50–69 %), not
DISCARD. Path from 43 % → 57 % closed by: (1) Python-side
article→doc index built from full-markdown reading
(`interpretacion/article_index.py`); (2) sanitizer matches cloud
`supabase_sink._sanitize_doc_id` byte-for-byte (preserves dashes +
dots — earlier mismatch regressed the panel to 9.5 %); (3) anchor
applied as a ×4 multiplicative boost on `rrf_score`, NOT a hard
filter (hard-filter regressed to 28.6 % because the index can't
know every article a doc covers). Graph schema additions
(`InterpretationNode` + `INTERPRETS` + `COVERS_TOPIC`) landed in
`graph/schema.py` for v10.1 Falkor-loader scope; v0 uses the
in-process Python index for the same functional benefit. Diagnostic
`interpretation_anchor_eligible_docs` + `interpretation_anchor_boosted_chunks`
extends `response.diagnostics.retrieval_diagnostics`. Wins added vs
Phase 10B baseline (+5): fe_nuevos_documentos_dav,
iva_exentos_vs_excluidos, proc_devoluciones_riesgo_auditoria,
pt_paraisos_panama, renta_patrimonio_niif. Remaining 9 misses
cluster on questions where the planner extracts a weak article ref
or where the index entry has too many competing docs (Art. 240 has
16 docs in the index). 10B+10C does NOT yet ship to production —
57 % is well above the discard floor but below the 70 % ship bar.
Path to ≥ 70 %: §5.2 gate-6 lever (c) trust-tier prioritization,
OR (the architecturally clean answer) v10.1 Falkor loader with
chunk-level concept_tags + Cypher planner anchor. Run:
`evals/sme_validation_v1/runs/20260511T195358Z_phase10b_expert_panel_v1/`.

#### 4.A.0 — What §9.1 actually showed (the diagnosis pivoted the plan)

The §9.1 cloud probe (run 2026-05-11 01:18 PM Bogotá via
`scripts/diagnostics/probe_v10_knowledge_class.py`) found:

| Cloud Supabase count | Value |
|---|---|
| `document_chunks.total` | 19,546 |
| `document_chunks` tagged `interpretative_guidance` | **0** |
| `document_chunks` tagged `practica_erp` | **0** |
| `document_chunks` tagged `normative_base` | 19,546 |
| `documents` tagged `interpretative_guidance` | 105 ✓ |
| `documents` tagged `practica_erp` | 169 ✓ |
| Chunks parented by `interpretative_guidance` docs | **1,414** |
| Chunks parented by `practica_erp` docs | **1,463** |
| **Total mistagged chunks (initial estimate)** | **2,877** (14.7% of corpus) |
| **Actually retagged by backfill** | **2,275** (812 + 1,463) |
| Gap (parent path matches EXPERTOS but doc tagged normative_base) | 602 — v10.1 audit |

The 602-chunk gap is **not** a backfill failure: those chunks descend
from documents whose `documents.knowledge_class` is `normative_base`
(even though their `relative_path` contains `EXPERTOS/`). Path A
correctly keys off the document's class and refused to retag them.
Reconciling whether those 211 documents (= 316 path-matches − 105
correctly-tagged) should be reclassified at the documents level is
an explicit v10.1 task; doing so unsupervised could mis-promote
internal templates or non-commentary files into the expert panel.

This means: the chunks ARE in cloud Supabase (with embeddings, FTS,
the lot). They're just labeled `normative_base` instead of their
correct class because of the now-fixed sink bug. **Path A — UPDATE
backfill** is the right route, not a full re-ingest.

Bonus finding (not blocking, follow-up for v10.1): 316 docs sit
under an `EXPERTOS/` path but only 105 are tagged
`interpretative_guidance` at the document level. The 211-doc gap is
likely path-vs-taxonomy drift on internal templates / non-commentary
files; auditable as a v10.1 task and does NOT affect Path A (the
UPDATE keys off `documents.knowledge_class`, which is correct).

#### 4.A.1 — The code change (shipped)

Three surgical edits in `src/lia_graph/ingestion/supabase_sink.py`
(verified via `tests/test_supabase_sink_knowledge_class.py`):

1. `__init__` adds `self._knowledge_class_by_doc_id: dict[str, str] = {}`
2. `write_documents` populates it next to `_topic_by_doc_id` /
   `_subtema_by_doc_id`, sourcing from `document["knowledge_class"]`
   exactly as the documents-row write already does at the old line 516.
3. `write_chunks` looks up
   `self._knowledge_class_by_doc_id.get(doc_id, "normative_base")`
   instead of hardcoding `"normative_base"`. The default fallback
   stays as defense-in-depth for chunks whose parent doc didn't flow
   through `write_documents` (never happens in normal pipelines).

This was the **narrow-module** fix the §1.B diagnosis pointed to —
no JSONL writer change needed because the sink reads document
metadata directly from the manifest-derived document dicts, not from
`parsed_articles.jsonl`. The original §4 bullet about
`parsed_articles.jsonl` was slightly off; reconciled here.

Provider preservation (§3.D) is **deferred to v10.1** — out of scope
for the keystone. Phase 10B can use the existing read-time provider
extraction at the catalog while building the Supabase retriever; the
move to ingest-time extraction lands with v10.1 once §9.3
(`documents.provider_labels` column) is decided.

#### 4.A.2 — The cloud UPDATE backfill (Path A)

Idempotent two-step UPDATE keyed on parent-document
`knowledge_class`. Touches exactly 2,877 chunks across 274 documents
(105 + 169). Safe to re-run: the `.eq("knowledge_class",
"normative_base")` predicate makes already-fixed rows a no-op.

Recipe (executed via PostgREST, batched by doc_id list to keep URL
length manageable — see
`scripts/diagnostics/backfill_v10_knowledge_class.py`):

```python
# Pass 1: interpretative_guidance chunks
doc_ids = client.table("documents")
  .select("doc_id").eq("knowledge_class", "interpretative_guidance").execute()
for batch in chunks_of_50(doc_ids):
    client.table("document_chunks")
      .update({"knowledge_class": "interpretative_guidance"})
      .in_("doc_id", batch)
      .eq("knowledge_class", "normative_base")
      .execute()

# Pass 2: practica_erp chunks — identical shape, swap the class string
```

Equivalent direct SQL (for context only — we execute via PostgREST):

```sql
UPDATE document_chunks AS c
   SET knowledge_class = d.knowledge_class
  FROM documents AS d
 WHERE c.doc_id = d.doc_id
   AND d.knowledge_class IN ('interpretative_guidance', 'practica_erp')
   AND c.knowledge_class = 'normative_base';
```

#### 4.A.3 — Verification gates (post-backfill)

- Re-run `scripts/diagnostics/probe_v10_knowledge_class.py`. Pass iff:
  - `tagged_interp` ≥ 1,400 (was 0)
  - `tagged_practica` ≥ 1,450 (was 0)
  - `tagged_norm` = 19,546 − (tagged_interp + tagged_practica), no
    collateral loss
- Embedding backfill: `embedding_ops.py` is `knowledge_class`-blind,
  so retagging doesn't invalidate existing vectors. No re-embedding
  needed.
- Operator-authorized §1.G 36-Q SME panel re-run gates Phase 10B
  (target: ≥ baseline 34/36 acc+ post-fix_v8f).

#### 4.A.4 — Test guardrails so this class of bug can't ship again

Three layers, smallest-blast-radius first:

**G1 — strong unit-test floor (shipped).** Five tests in
`tests/test_supabase_sink_knowledge_class.py` assert chunk-class
inheritance from parent doc for every defined `knowledge_class`
value, including a mixed-corpus regression test and a
defense-in-depth fallback case. Pytest discovers it automatically;
runs in `make test-batched`.

**G2 — sink-level parity invariant (shipped).** The sink now tracks
per-write `(doc_id, knowledge_class)` pairs and asserts at
`finalize()` that every chunk's class matches its parent's. Mismatch
emits `"ingest.sink.chunk_class_mismatch"` to the instrumentation
event stream (visible in `tracers_and_logs/logs/events.jsonl` and to
any heartbeat watching the ingest). Also tracks
`_chunks_default_class_count` — number of chunks that fell back to
the `"normative_base"` default because their parent wasn't
registered via `write_documents`. In a healthy ingest this is `0`.
A positive count emits
`"ingest.sink.chunk_class_default_used"` with a sample of doc_ids.

**G3 — runnable cloud parity probe (shipped as
`scripts/diagnostics/probe_v10_knowledge_class.py`).** Operator can
re-run this any time post-ingest to confirm cloud Supabase still
holds the invariant: every document's `knowledge_class` is reflected
in its chunks' `knowledge_class`. Same script that diagnosed the
original bug; reusable as a CI gate when we wire cloud-credentialed
smokes (out of scope today).

**Future-content protection.** When a fresh
`make phase2-graph-artifacts-supabase` runs against staging or
production, all three guardrails fire in order:

1. G2 fails the ingest's finalize step if any chunk's class drifted
   from its parent's
2. G3 (operator-run post-ingest) confirms cloud DB matches expectation
3. G1 prevents the regression from ever landing in code in the first
   place via the parametrized unit-test floor

### Phase 10B — Build the Supabase-backed interpretation retriever

**Modules touched:**

- NEW: `src/lia_graph/interpretacion/retriever_supabase.py`
  (implements `fetch_interpretation_candidates` per §3.B).
- `src/lia_graph/interpretacion/orchestrator.py:136-217`
  (`_retrieve_interpretation_docs`) — turn into a dispatcher:
  read `LIA_INTERPRETATION_SOURCE`; on `'supabase'` call the new
  retriever; on anything else call `list_local_interpretation_rows`
  as today.
- `src/lia_graph/ui_chat_payload.py` —
  `filter_diagnostics_for_public_response` adds
  `interpretation_backend` to the whitelist so the panel response
  carries it just like `retrieval_backend` does for chat.
- `scripts/dev-launcher.mjs` — add `LIA_INTERPRETATION_SOURCE`
  to the env matrix: `filesystem` (dev), `supabase`
  (dev:staging), `supabase` (production). Bump env matrix
  version + add change-log row in
  `docs/orchestration/orchestration.md`.

**Verification:**

- Unit test on the new retriever using a fixture
  SupabaseClient that returns canned rows from
  `hybrid_search`.
- Integration: `dev:staging` with
  `LIA_INTERPRETATION_SOURCE=supabase`, hit the existing 10-Q
  probe — every served chat must produce a non-empty panel
  when any normative article is cited (target ≥ 95%).
- Diagnostic check: every response's
  `diagnostics.interpretation_backend` reads `'supabase'`.
- Performance: panel-render latency must not regress by more
  than 200 ms p95 vs filesystem baseline (the Supabase round-trip
  cost is on the order of one extra `hybrid_search` call).

### Phase 10C — Graph nodes + planner anchor

**Modules touched:**

- `src/lia_graph/graph/schema.py:12-102` — add `InterpretationNode`
  and `ExpertProviderNode` to the label set; add `INTERPRETS`,
  `AUTHORED_BY`, `COVERS_TOPIC` to the edge enum.
- NEW: `src/lia_graph/graph/interpretation_loader.py` — emits the
  Cypher MERGE statements for interpretation nodes + edges as
  part of the `materialize_graph_artifacts` execution.
  Idempotent on `(doc_id)` for nodes and on `(source_doc_id,
  target_article_key, relation)` for edges. Follows the same
  staging pattern `GraphClient.stage_node()` /
  `.stage_edge()` already uses (graph/client.py:195+).
- `src/lia_graph/pipeline_d/planner.py` — when the planner detects
  the chat will cite articles, ALSO emit an "interpretation
  anchor" seed = the set of `InterpretationNode.doc_id` values
  reachable via `INTERPRETS` from those articles. Pass that seed
  to the retriever as a `requested_refs` augmentation so the
  Supabase call's RRF boosts them.
- `src/lia_graph/interpretacion/retriever_supabase.py` —
  accepts the planner-supplied seed and uses it to weight the
  candidate scoring.

**Verification:**

- A Cypher probe against cloud Falkor:
  `MATCH (i:InterpretationNode)-[:INTERPRETS]->(a:ArticleNode)
   RETURN count(i), count(distinct a)` — expect counts matching
  the manifest's interpretation count and the union of their
  referenced articles.
- The 10-Q probe re-run: for every question that cites an article,
  inspect `diagnostics.pipeline_trace` for a graph anchor step
  named `interpretation_anchor`. At least 7 of 10 questions
  should add at least one card via the anchor path.
- Mini-panel (§5.4) re-run: same 20 questions, target ≥ 75%
  SME-relevance (5pt uplift over phase 10B).

### Phase 10D — Retire the filesystem catalog (carefully)

**Modules touched:**

- `src/lia_graph/interpretacion/catalog.py` — keep the file. Mark
  the public functions as deprecated in docstrings; add a runtime
  warning if `LIA_INTERPRETATION_SOURCE` is not `'supabase'` in
  production-mode.
- `scripts/dev-launcher.mjs` — flip `dev`'s
  `LIA_INTERPRETATION_SOURCE` default to `'supabase'` after two
  weeks of stable production. Local docker still gets its
  interpretations from cloud Supabase (parity with how
  `dev:staging` works today for chunks).
- `.railwayignore` — keep the `!knowledge_base/**/*.md`
  whitelist for now. It's cheap insurance; remove only after
  Phase 10D's SME panel hits the closing bar.

**Verification:**

- Production telemetry: 100% of served chats should report
  `interpretation_backend = 'supabase'` over a 7-day window with
  zero `'filesystem'` fallbacks (the fallback is still wired but
  should never fire in steady state).
- The closing bar (§scope guard) must hold: SME §1.G ≥ baseline,
  mini-panel ≥ 70% acc+, empty-panel rate < 5%.

---

## 5. Six-gate plan per phase (per `docs/aa_next/README.md` policy)

### 5.1 Gates for Phase 10A

1. **Idea (one sentence).** Propagate the `knowledge_class` field
   from the canonical manifest through the chunk JSONL and into
   `document_chunks` so the existing `hybrid_search` RPC can
   filter the interpretation corpus.
2. **Plan (narrow module).** Touch
   `src/lia_graph/ingestion/ingest.py` (JSONL writer) and
   `src/lia_graph/ingestion/supabase_sink.py:644` (chunk write).
   No DDL. No retriever change.
3. **Minimum success criterion.** After ingest, `SELECT
   knowledge_class, count(*) FROM document_chunks GROUP BY 1`
   on staging Supabase returns ≥ 1,000 rows for
   `'interpretative_guidance'` (≈ 105 docs × ~10 chunks/doc
   conservative lower bound from the 1,285 `EXPERTOS`-hit count).
4. **Test plan.**
   - Development: build artifacts locally, grep JSONL for
     non-empty `knowledge_class`.
   - Operator: triggers `make
     phase2-graph-artifacts-supabase
     PHASE2_SUPABASE_TARGET=staging` per
     `feedback_lia_graph_cloud_writes_authorized`.
   - Engineer: probes staging Supabase with the SQL above.
   - SME: NOT required for 10A — the gate is purely structural.
   - Decision rule: pass iff ≥ 1,000 interpretation chunks land
     AND embedding backfill subsequently produces non-null
     embeddings on ≥ 95% of them.
5. **Greenlight.** Engineer SQL probe + embedding-backfill
   completion report. Auto-greenlight; no SME needed.
6. **Refine-or-discard.** If embedding-backfill stalls or
   chunk count is below 1,000, root-cause before unblocking 10B
   (likely the JSONL writer dropped fields silently). NO threshold
   relaxation per `feedback_thresholds_no_lower`.

### 5.2 Gates for Phase 10B

1. **Idea.** Route the Interpretación de Expertos panel through
   `hybrid_search` instead of the filesystem catalog, gated by an
   env flag.
2. **Plan.** New `retriever_supabase.py` in
   `src/lia_graph/interpretacion/`; flag dispatcher in
   `orchestrator._retrieve_interpretation_docs`; env-matrix
   addition + doc updates.
3. **Minimum success criterion.** On the existing 10-Q chat
   probe in `tracers_and_logs/logs/probe_runs/`, with
   `LIA_INTERPRETATION_SOURCE=supabase`, ≥ 9 of 10 questions
   produce a non-empty Interpretación panel; AND none of the 10
   drop a normative-side article that previously survived
   (verified by diffing the chat answers' citations against
   the post-fix_v8f baseline).
4. **Test plan.**
   - Development: unit test on the retriever with a stub
     SupabaseClient; vitest on no frontend change (UI unchanged).
   - Operator: runs `dev:staging` with the flag flipped,
     replays the 10-Q probe.
   - Engineer: diffs probe outputs against baseline.
   - SME: runs the new 20-question mini-panel (§5.4); rates each
     card top-3 as `accept` / `meh` / `wrong`.
   - Decision rule: pass iff probe non-empty rate ≥ 90% AND
     mini-panel accept rate ≥ 70% in top-3 AND zero new SME
     `wrong` rulings vs prior pure-filesystem rerank.
5. **Greenlight.** Dual gate. SME run is the only one that
   blocks ship-to-production.
6. **Refine-or-discard.** If mini-panel falls below 70%, three
   levers in priority order: (a) raise the
   `subtopic_boost`/`boost_topic` multipliers for the
   interpretation `knowledge_class` only (orthogonal to
   normative scoring); (b) injection rule for article-ref
   tokens in the FTS query weight; (c) trust-tier prioritization
   (boost provider-tagged rows). If after all three the panel
   still underperforms vs filesystem, fall back to filesystem
   for that subset (split-rollout per topic), and discard the
   phase as currently scoped — return to design.

### 5.3 Gates for Phase 10C

1. **Idea.** Expose interpretations as graph nodes so the planner
   can anchor interpretation retrieval on the exact articles the
   chat is about to cite.
2. **Plan.** Add `InterpretationNode` + `INTERPRETS` /
   `COVERS_TOPIC` to schema; emit nodes + edges from the
   materialize step; planner emits interpretation anchors.
3. **Minimum success criterion.** Mini-panel SME accept rate
   improves by ≥ 5 percentage points over 10B's number (e.g. if
   10B hits 72%, 10C must hit ≥ 77%); AND zero `wrong` rulings
   from anchor-seeded cards that didn't exist in 10B's results.
4. **Test plan.**
   - Development: Cypher probes on staging Falkor count nodes +
     edges; integration test verifies anchor seeds flow.
   - Operator: full re-ingest with graph build, then mini-panel.
   - Engineer: pipeline-trace inspection per question.
   - SME: re-runs mini-panel.
   - Decision rule: +5pt or ship; below that, discard the anchor
     path as net-zero value, document the negative result in
     `docs/aa_next/next_done.md`.
5. **Greenlight.** Dual gate. Don't ship if anchor produces
   `wrong` cards even if accept rate is up — false positives
   are worse than false negatives in expert content.
6. **Refine-or-discard.** Two attempted refinements before
   discard: (a) limit anchor seeds to articles whose
   `trust_tier` is `high` to avoid amplifying weak edges;
   (b) intersect anchor seeds with the question's resolved
   topic (don't anchor on `Art. 124-2` for a labor-law
   question even if the chat happens to cite it).

### 5.4 The new 20-question Expert-Panel SME mini-panel

**Why a new panel.** The existing §1.G 36-Q SME panel measures
chat quality. The expert panel is a different surface; it needs
its own measurement instrument. Reusing §1.G is wrong because:
(a) some §1.G questions don't expect expert content (e.g. simple
plazo questions); (b) success on §1.G says nothing about whether
the right Crowe brief surfaced.

**Composition.** 20 questions across topic distribution:

- 5 RENTA (deducciones, ICA-deduction, costos)
- 4 IVA / facturación electrónica
- 3 retención en la fuente
- 3 normativa laboral / parafiscales (UGPP, CST)
- 2 GMF (4×1000) — interpretations are dense here
- 2 precios de transferencia / paraísos fiscales
- 1 RST (régimen simple)

Each question must have at least one known relevant interpretation
in the corpus — verified by the engineer before the run by
spot-checking the markdown. (Per
`feedback_no_hallucinated_examples` — never invent panel questions.)

**Run mechanics.** Reuse `scripts/eval/run_sme_parallel.py` with
a new question file
`evals/sme_validation_v1/questions_expert_panel_v1.json`. The
runner already supports parallel SME judging; the only addition
is a new rubric column for "panel top-3 had a relevant card"
(yes/meh/no).

**Decision rule.** ≥ 70% accept = pass. 50–69% = refine.
< 50% = discard the phase as scoped, return to design.

**Gating.** Operator authorizes the run per
`feedback_sme_panel_explicit_request_only`. Wall-clock ~10 min
per run at 4 workers.

### 5.5 Gates for Phase 10D

Closing the loop. Verification is operational, not feature-driven.

1. **Idea.** Make Supabase the canonical source of truth for
   interpretations; demote filesystem to "fallback floor".
2. **Plan.** Flip `dev` mode's default; add a startup warning if
   production resolves to filesystem; keep `.railwayignore`
   whitelist as belt-and-suspenders.
3. **Minimum success criterion.** Over a 7-day production window,
   0 fallback firings AND no panel-empty rate degradation.
4. **Test plan.** Production telemetry on
   `interpretation_backend` value distribution + panel
   non-empty rate. Operator inspects the dashboard daily.
5. **Greenlight.** 7 clean days.
6. **Refine-or-discard.** A single fallback firing is a diagnostic
   signal, not a failure (per "Fail Fast, Fix Fast" canon in
   CLAUDE.md) — root-cause it before declaring 10D shipped.

---

## 6. Schema additions

**Zero new tables needed.** All work flows through the existing
`documents` + `document_chunks` schema.

**Zero RPC additions needed.** `hybrid_search` already exposes
`filter_knowledge_class`.

**One optional DDL (see §9.3 open question):** add
`provider_labels (text[])` to `documents` if the v10 team
decides to upgrade provider attribution from "encoded in
concept_tags" to "first-class column". Recommendation: defer to
v10.1 unless §9.3 resolves in favor of column-first.

**Graph schema additions (phase 10C only):**

- New node labels: `InterpretationNode`, optionally `ExpertProviderNode`
- New edge relations: `INTERPRETS`, `COVERS_TOPIC`, optionally
  `AUTHORED_BY`

These are FalkorDB-only — the Postgres `normative_edges` table
already restricts to its `relation` enum
(`{references, modifies, complements, exception_for, derogates,
supersedes, suspends, struck_down_by, revokes, cross_domain}`)
and the new edges don't fit any of those, which is fine because
they're not normative-to-normative edges; they don't need to
sync to Postgres.

---

## 7. Code surface map (full delta)

```
src/lia_graph/
├── ingestion/
│   ├── ingest.py                              MODIFIED (10A)
│   │   └── carries knowledge_class + provider_labels
│   │       from manifest into parsed_articles.jsonl
│   └── supabase_sink.py                       MODIFIED (10A)
│       └── chunk write path uses chunk's own knowledge_class
│           (not a hardcoded "normative_base" default)
├── interpretacion/
│   ├── catalog.py                             DEPRECATED (10B+)
│   │   └── kept as filesystem fallback
│   ├── orchestrator.py                        MODIFIED (10B, 10C)
│   │   ├── _retrieve_interpretation_docs becomes dispatcher
│   │   └── _build_runtime_for_doc trusts row.provider_labels
│   └── retriever_supabase.py                  NEW (10B)
│       └── fetch_interpretation_candidates(...)
├── graph/
│   ├── schema.py                              MODIFIED (10C)
│   │   └── adds InterpretationNode + INTERPRETS edge
│   └── interpretation_loader.py               NEW (10C)
│       └── emits Cypher MERGE for nodes + edges
├── pipeline_d/
│   └── planner.py                             MODIFIED (10C)
│       └── emits interpretation_anchor when citing articles
├── ui_chat_payload.py                         MODIFIED (10B)
│   └── whitelists interpretation_backend in public response
└── (no other backend changes)

scripts/
└── dev-launcher.mjs                           MODIFIED (10B, 10D)
    └── adds LIA_INTERPRETATION_SOURCE to env matrix

docs/
└── orchestration/orchestration.md             MODIFIED (10B, 10C, 10D)
    └── env matrix version bumps + change-log rows

frontend/                                       NO CHANGE
evals/
└── sme_validation_v1/
    └── questions_expert_panel_v1.json         NEW (5.4)
```

---

## 8. Risks + mitigations

### 8.1 Chunking strategy mismatch

**Risk.** Today's chunker emits article-shaped chunks. Expert
markdowns aren't articles — they're long-form prose with H1/H2
headings. If the chunker treats a 4,000-word interpretation as
one chunk, the embedding is too dilute to retrieve precisely.
If it splits too aggressively, providers and norms get fragmented
across chunks.

**Mitigation.** Phase 10A audits the existing chunk distribution
(`SELECT doc_id, count(*) FROM document_chunks WHERE
knowledge_class='interpretative_guidance' GROUP BY doc_id`)
before declaring success. If a typical doc produces fewer than 4
chunks, we add a section-aware chunker (H2-split) in
`ingestion/`. This is gate 3 in §5.1 — if the chunk count is below
1,000 (lower bound is 4 × 105 docs = 420 — but the field count
from `parsed_articles.jsonl` showed 1,285 EXPERTOS-hit lines, so
the chunker is already segmenting them).

### 8.2 Vector embedding regression vs lexical scoring

**Risk.** The current lexical scoring weights ref_hits 2.5×. A
pure-vector first pass might surface semantically similar but
article-irrelevant interpretations (e.g. a "deducciones generales"
brief instead of an "Art. 124-2 jurisdicciones no cooperantes"
brief).

**Mitigation.** §3.B injects article refs into the FTS query as
required tokens. Combined with rerank, this preserves the
lexical-precision intent of the current scoring while gaining
semantic recall. The mini-panel (§5.4) is the empirical check —
if pure-Supabase scoring lands below 70% accept, gate-4 has
three pre-defined levers before discarding.

### 8.3 The filesystem fallback gets exercised in production

**Risk.** A transient Supabase outage causes the panel to silently
flip to filesystem fallback, masking the cloud issue.

**Mitigation.** Per CLAUDE.md's "Falkor adapter must keep
propagating cloud outages — no silent artifact fallback on
staging" principle, the Supabase interpretation retriever PROPAGATES
errors. The fallback only fires when
`LIA_INTERPRETATION_SOURCE != 'supabase'`, which is a config
state, not a runtime fallback. Production telemetry surfaces the
flag value per chat so a misconfiguration shows up immediately.

### 8.4 Provider attribution data loss

**Risk.** Today `extract_expert_providers(preview_text)` runs on
the full markdown. If we move to ingest-time extraction and the
ingest pipeline drops providers for a malformed file, that
attribution is lost permanently from the chunk metadata.

**Mitigation.** Phase 10A adds a regression check: count distinct
providers across all interpretation rows before and after ingest;
abort if the post-ingest count drops by more than 2%. The
`expert_summary_overrides` table also serves as a curated
override layer that survives even if extraction drifts.

### 8.5 Cardinality blowup in graph edges

**Risk.** A long Crowe brief might reference 30 articles, yielding
30 `INTERPRETS` edges per node. Across 105 docs that's potentially
3,000+ edges — small in absolute terms, but the planner queries
need to be bounded so they don't pull back hundreds of
interpretations for a chat that cites Art. 631 ET (a frequently
referenced article).

**Mitigation.** Planner caps interpretation anchors at 8 per
article (§3.C example query uses `LIMIT 8`); rerank handles
final ordering. Per `feedback_subtopic_aliases_breadth`, we
intentionally don't over-tighten on the retrieval side — width
at retrieval, precision at rerank.

### 8.6 Re-ingest cost

**Risk.** Phase 10A requires a full re-ingest of the entire
manifest to fix `knowledge_class`. That's ~1,300 documents
re-processed.

**Mitigation.** The re-ingest is idempotent (UPSERT on `chunk_id`)
per "Fail Fast, Fix Fast" canon point 4. Run it with the existing
`make phase2-graph-artifacts-supabase` pipeline which already
has heartbeat + risk-first batching after next_v7 P1. Cost in
wall clock: ~30 min based on the cloud_promotion reference
implementation.

---

## 9. Open questions + decisions needed before code lands

### 9.1 Are interpretation chunks ALREADY in cloud Supabase?

**✅ RESOLVED 2026-05-11 01:18 PM Bogotá — Path A (UPDATE backfill).**
See §4.A.0 for the numeric result and §4.A.2 for the executed fix.
Original framing of this open question preserved below for the
archaeological record.

---

The manifest's interpretation entries have `graph_target: true`
and `graph_parse_ready: true`. The chunker has produced
`EXPERTOS`-path entries in `parsed_articles.jsonl`. If the most
recent `make phase2-graph-artifacts-supabase` run wrote them
through, they MAY already be in `document_chunks` with embeddings
— just without `knowledge_class` populated.

**Action before phase 10A.** Engineer queries cloud Supabase:

```sql
SELECT
  count(*) AS total_chunks,
  count(*) FILTER (WHERE knowledge_class = 'interpretative_guidance') AS tagged_interp,
  count(*) FILTER (WHERE doc_id LIKE 'local_interp_%' OR doc_id IN (
    SELECT doc_id FROM documents
    WHERE relative_path LIKE '%EXPERTOS%'
  )) AS untagged_interp_by_path
FROM document_chunks;
```

If `tagged_interp` is 0 but `untagged_interp_by_path` is in the
thousands, phase 10A is a backfill (UPDATE on existing rows) not
a fresh ingest — faster and cheaper. The path-shape predicate
makes the UPDATE deterministic.

### 9.2 Is `hybrid_search`'s `filter_knowledge_class` parameter
expressive enough?

The current RPC accepts a single value. If we ever want a
multi-class query ("interpretations OR practice notes for this
question"), we need either a comma-list parameter or an
additive RPC.

**Decision for v10.** Single-value is sufficient — the expert
panel is interpretation-only by definition. Multi-class is a
v11 concern.

### 9.3 Add `documents.provider_labels (text[])` column?

**✅ RESOLVED 2026-05-11 PM Bogotá — yes, column.** Migration
`supabase/migrations/20260513000000_documents_provider_labels.sql`
applied to LIA_Graph cloud Supabase via `supabase db push`. Column
present + queryable + defaults to `[]` for every existing row (no
backfill UPDATE needed; the manifest builder populates new ingests).
Sink wire-up landed in the same commit
(`supabase_sink.write_documents` reads `document["provider_labels"]`,
cleans whitespace/empties, writes to the new column). 4 new unit
tests cover default empty / populated / whitespace stripping /
non-list robustness. Producer side (manifest builder emitting the
field per interpretation doc) lands inside Phase 10B proper.

Original framing preserved below.

---

**Pro.** Clean attribution; query-friendly; the chunk row can
inherit. Aligns with how `topic_domains`, `normative_refs`,
`reference_identity_keys` are already stored as text arrays.

**Con.** DDL requires a baseline migration update or a post-
baseline `20260513*` migration. Re-ingest covers populating it
but every existing chunk row needs to be touched.

**Recommendation.** Add the DDL in phase 10A as a small
post-baseline migration (`20260513000000_documents_provider_labels.sql`).
Cost is one migration file + one backfill UPDATE. Avoids the
"encoded in concept_tags" anti-pattern.

### 9.4 Should `ExpertProviderNode` ship in v10 or v10.1?

The added value of provider nodes is the "show me all Crowe
interpretations for this topic" cross-cut. That's a real product
feature but it's NOT what the empty panel was blocking. Provider
nodes are a separate planner anchor pattern that deserves its
own design pass.

**Recommendation.** Ship phase 10C with `INTERPRETS` +
`COVERS_TOPIC` only. Defer `AUTHORED_BY` + `ExpertProviderNode`
to v10.1 after the SME panel proves the basic graph integration
adds value.

### 9.5 Trust-tier policy per provider

Today every interpretation gets `trust_tier='medium'` via
`catalog.py:60` setdefault. In a first-class corpus we want
provider-aware tiers: Crowe / EY / KPMG / DIAN-circular-by-known-officer
might warrant `high`; anonymous blog posts cited as
interpretation should be `low`.

**Decision for v10.** Keep `medium` as default; allow override
via a curated `config/provider_trust_tiers.json` that the
ingest step reads. Out-of-scope for v10 minimum viable; in-scope
for v10.1.

### 9.6 What if §1.G regresses while 10A is shipping?

Phase 10A changes the chunk-write code path. A regression that
mangles `normative_base` chunks would harm chat quality.

**Mitigation.** The §1.G re-run is mandatory after phase 10A's
re-ingest, BEFORE phase 10B starts. Phase 10A is reversible
(re-ingest with the pre-10A binary recovers state). Per
`feedback_sme_panel_explicit_request_only`, the operator
authorizes the §1.G run.

---

## 10. Order of operations summary

1. Verify §9.1 against cloud Supabase — establishes whether 10A
   is a backfill or a fresh ingest.
2. Decide §9.3 (add `provider_labels` column or not). Recommended:
   yes, in phase 10A.
3. Ship phase 10A (`ingest.py` + `supabase_sink.py` chunk write
   path + optional DDL). Re-ingest to staging. Verify chunk count.
   Run embedding backfill. Run §1.G to confirm no chat regression.
4. Ship phase 10B (`retriever_supabase.py` + dispatcher + env
   matrix). Run 10-Q probe + Expert-Panel mini-panel on staging.
   Gate on §5.2 decision rule.
5. Promote 10B to production. Monitor `interpretation_backend`
   telemetry for 48h. If clean, proceed; if not, root-cause.
6. Ship phase 10C (graph nodes + planner anchor). Run mini-panel
   for the +5pt criterion. Gate on §5.3 decision rule.
7. Ship phase 10D. Flip dev default. 7-day production telemetry.
8. After 10D is shipped + stable for 7 days, archive the
   filesystem catalog reference in `docs/aa_next/next_done.md`
   per the six-gate refine-or-discard requirement.

**Earliest realistic end-to-end calendar.** Phase 10A: 2 engineer
days + 1 day re-ingest wait. Phase 10B: 3 engineer days +
1 SME mini-panel run + 2 days production soak. Phase 10C: 3
engineer days + 1 SME mini-panel run. Phase 10D: 7 days
telemetry observation. Total ≈ 3 weeks engineer time + 10 days
operational soak, parallelizable to ≈ 2.5 weeks calendar with
operator + SME availability.

---

## 11. What to do tomorrow morning

If you want this to start moving without re-reading the whole
document:

1. **Engineer**: run the §9.1 query against cloud Supabase. The
   answer tells you whether 10A is a 30-min backfill or a 4-hour
   re-ingest. Drop the result into a new
   `docs/re-engineer/fix/fix_v10_may_diagnosis.md` companion (same
   pattern as `fix_v1_diagnosis.md`).
2. **Operator**: decide §9.3. The recommendation is "yes, add the
   column" — it's the right architectural call and the cost is
   one migration file.
3. **Engineer + Operator**: schedule the §5.4 mini-panel question
   curation. The 20 questions need to come from real practice;
   spending 90 minutes on this BEFORE writing phase 10B code saves
   you from gate-4 surprises later.

Phase 10A is the smallest, safest, most reversible step. It also
unlocks every other phase. Start there.
