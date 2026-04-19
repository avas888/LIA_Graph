# SUIN-Juriscol Ingestion Plan

## Implementation stage tracker (resumable)

Every stage mutates this table when it starts (`in progress`) and completes (`done`). If an agent restarts mid-flight, this table is the source of truth for where to resume. Last-updated timestamps are UTC.

| # | Stage | Status | Artifacts that prove it | Updated |
|---|---|---|---|---|
| 0 | Commit pending + branch (`feat/suin-ingestion`) | done | commit `266a8b9` on main, branch `feat/suin-ingestion` created | 2026-04-19T17:17Z |
| 1 | Stage tracker added to this doc | in progress | this table | 2026-04-19T17:20Z |
| 2 | Survey integration surfaces (parser.py, classifier.py, ingest.py, sink, Makefile, env targets) | done | notes captured in conversation; `wip` target verified as local docker Supabase in `.env.staging` | 2026-04-19T17:25Z |
| 3 | Phase A — `suin/{fetcher,parser,harvest}.py` + tests + Makefile targets + `.gitignore` cache | done | `src/lia_graph/ingestion/suin/{__init__,fetcher,parser,harvest}.py`; `tests/test_suin_{parser,fetcher}.py` 17/17 green; Makefile targets `phase2-suin-harvest-{et,tax-laws,jurisprudence,full}`; `cache/suin/` in `.gitignore` | 2026-04-19T17:45Z |
| 4 | Phase B — EdgeKind extension, sink map, `suin/bridge.py`, `--include-suin` on `ingest.py`, Makefile `--execute-load` fix | done | schema.py adds ANULA/DECLARES_EXEQUIBLE/DEROGATES/REGLAMENTA/STRUCK_DOWN_BY/SUSPENDS; supabase_sink `_RELATION_MAP` extended + Gap #1 resolved; `ingestion/suin/bridge.py` + `ingest.py` `_merge_suin_scope` two-pass wiring; Makefile now passes `--execute-load --allow-unblessed-load --strict-falkordb` + plumbs INGEST_SUIN; 85 ingestion tests + 17 Phase A tests green | 2026-04-19T18:05Z |
| 5 | Test against local docker Supabase (target = `wip`) + local docker Falkor | pending | `documents`/`document_chunks`/`normative_edges` rows for a SUIN generation_id visible in `http://127.0.0.1:54323`; Falkor node count increased | — |
| 6 | Promote to cloud Supabase + cloud FalkorDB | pending (requires user confirmation before firing — cloud write is irreversible) | `generation_id` visible in cloud Supabase studio; cloud Falkor `MATCH (n) RETURN count(n)` > 2,568 | — |

### Resume protocol

If you pick this up mid-stream: read this table top-down, find the first row that is not `done`, confirm the "Artifacts that prove it" column against the repo, and continue from there. Do **not** skip forward — each stage's artifacts are preconditions for the next.

---

## What we are trying to achieve (in plain language)

Today LIA reads tax norms (Estatuto Tributario, reform laws, decretos, resoluciones) as static text. An article is either "in" the corpus or not. What the app **cannot do** is answer the senior-accountant question that always comes next: *"is this article still alive? who changed it? which sentencia says it means X?"* We feel this as thin answers when a user asks about a modified article, vague vigencia claims, and no traceable link back to the law that introduced the change.

SUIN-Juriscol is the Ministerio de Justicia's official legal portal. For every tax article it already holds a hand-maintained list of **which law modified it, which decreto reglamenta it, which Corte Constitucional sentencia declared it exequible or inexequible, and which articles were added or derogated in each reform** — and it exposes that list as clean, labeled HTML that a scraper can read without NLP.

If we ingest this, LIA stops being "a corpus of norms" and becomes "a corpus of norms with a living change history."

### What success looks like for the app

- Every article node in the graph carries typed, dated edges to the other norms that affected it.
- Vigencia is a queryable property, not a regex over article text.
- Constitutional jurisprudence (sentencias of the Corte Constitucional and Consejo de Estado) is a first-class node type, linked to the exact article it interprets, strikes down, or upholds.
- Retrieval can prefer, deprioritize, or surface articles based on their current vigencia — so derogated content stops leaking into answers by accident.

### What success looks like for the user

- When the user asks about an article, LIA can say "**vigente**, modificado por la Ley 1819 de 2016 art. 135" with a citation the user can click.
- When the user asks about a derogated or struck-down article, LIA proactively flags it — not three paragraphs in, at the top.
- When the user asks a practical question, the answer includes the sentencia that settles the interpretation, not just the raw text.
- Version history of the Estatuto Tributario becomes browsable: "what did this article look like before reform X?"

This is the difference between a competent assistant and one a senior accountant can trust with a client call.

---

## Scope boundary

Strictly additive. No changes to:

- How local `npm run dev` serves answers (still artifacts).
- How `answer_policy.py` / `answer_assembly.py` render.
- DIAN conceptos (those stay sourced from `normograma.dian.gov.co` — out of scope here).

This plan brings SUIN into the existing ingestion path so it lands in `normative_edges` + `documents` + `document_chunks` like the current corpus does, and it extends the edge vocabulary so the new relationship types survive into the Supabase schema.

## Pre-implementation health check (2026-04-19)

A practical health check was run before handoff, including a **live query against cloud Supabase and cloud FalkorDB**. Findings that shape this plan:

### Live cloud state (queried 2026-04-19)

| Component | State |
|---|---|
| Cloud Supabase linked (`supabase/.temp/project-ref`) | ✅ `utjndyxgfhkfcrjmtdqz` |
| `documents` rows | ✅ 1,292 |
| `document_chunks` rows | ✅ 2,064 (active generation `gen_20260418035334`) |
| `normative_edges` rows | ✅ 19,903 |
| `corpus_generations.is_active=true` count | ✅ exactly 1 (partial unique index holding) |
| Cloud FalkorDB reachable + populated | ✅ 2,568 nodes (above the 500-node preflight floor) |
| `retriever_supabase.py` + `retriever_falkor.py` + orchestrator dispatch | ✅ wired at `src/lia_graph/pipeline_d/orchestrator.py:43-79`, with lazy imports and `retrieval_backend`/`graph_backend` diagnostics |
| Staging env flags (`scripts/dev-launcher.mjs:274`) | ✅ sets `LIA_CORPUS_SOURCE=supabase`, `LIA_GRAPH_MODE=falkor_live` |
| `documents.source_type` CHECK constraint | ✅ none — `"suin_norma"` is accepted as a free-text value |

### Verified assumptions

- **Pipeline is green.** `tests/test_phase2_graph_scaffolds.py` (19/19) and `tests/test_ingestion_supabase_sink.py` (6/6) pass. A real end-to-end ingest of a 3-file corpus slice produced `parsed_articles.jsonl` + `raw_edges.jsonl` + `typed_edges.jsonl` + a full audit bundle with graph validation `ok: true`.
- **CHECK constraint already covers every DB relation this plan maps to.** Verified at `supabase/migrations/20260417000000_baseline.sql:1129` — `normative_edges_relation_check` permits `references | modifies | complements | exception_for | derogates | supersedes | suspends | struck_down_by | revokes | cross_domain`. **No relation-expansion migration is needed** (an earlier draft included one — removed).
- **`hybrid_search` has an independent FTS path** (baseline line 310: `WHERE dc.search_vector @@ effective_tsq`). It returns rows based on Postgres full-text search regardless of whether `embedding` is NULL. This means SUIN chunks become retrievable the instant they land — the vector RRF half simply contributes zero until embeddings are generated.
- **`hybrid_search` implicitly filters `vigencia IN ('derogada', 'proyecto', 'suspendida')`** when `filter_effective_date_max IS NULL` (baseline line 317). SUIN-sourced chunks flagged `derogada` will be correctly excluded from default vigente-only retrieval without extra code — Phase C just needs to pass `filter_effective_date_max` when the user asks a historical question.

### Gaps found

- **Gap #1 — `_RELATION_DROP` silently discards graph-only edge kinds.** `src/lia_graph/ingestion/supabase_sink.py:59` drops `REQUIRES`, `COMPUTATION_DEPENDS_ON`, `DEFINES`, `PART_OF` rather than persist them. The live health-check run produced 1 `COMPUTATION_DEPENDS_ON` edge that was thrown away. SUIN doesn't emit those kinds, so this is not a blocker — but since we're already extending `_RELATION_MAP` in Phase B, this is the cheapest moment to decide (map `REQUIRES` + `COMPUTATION_DEPENDS_ON` to `references`, keep `DEFINES`/`PART_OF` dropped with an inline comment).

- **Gap #2 — unresolved edges are dropped, not stubbed.** The test ingest logged *"Skipped 11 unresolved ArticleNode edges whose targets are not materialized in the current corpus snapshot."* SUIN will hit the same case en masse: ET article → law we haven't ingested yet. In a single-pass ingest we'd lose most of the value SUIN brings. Phase B step #13 below mandates a two-pass merge that materializes stub target nodes for SUIN-discovered refs before the unresolved-drop step runs.

- **Gap #3 (silent trap) — `make phase2-graph-artifacts-supabase` does NOT execute the Falkor load.** The target at `Makefile:48` passes `--supabase-sink` but omits `--execute-load`. `materialize_graph_artifacts` only writes to Falkor when `execute_load=True` (see `src/lia_graph/ingest.py:474,499-504`). As a result, running the current Makefile target against cloud populates Supabase but leaves Falkor untouched — staging's graph-traversal half would never see the new edges. The existing 2,568 nodes in cloud Falkor were loaded by a manual `--execute-load` invocation at some earlier point, not by the Makefile target. **Phase B step #5 below fixes this.** Without the fix, Phase B produces Supabase-only SUIN absorption and the promised graph coverage never materializes.

- **Gap #4 (myth-busting) — embeddings are NOT a gate for SUIN visibility.** Live cloud state shows 0 of 2,064 chunks have embeddings. Staging already serves answers against that state via the FTS half of `hybrid_search`. SUIN chunks follow the same pattern: FTS-retrievable at landing time, improved by running `embedding_ops.py` later. An earlier draft of this plan treated embeddings as a precondition — they are a **quality improvement**, not a blocker. Running `embedding_ops.py` against cloud backfills both the existing corpus and the new SUIN chunks; it is worth doing, but it does not gate Phase B success.

- **Invocation convention.** The codebase runs ingestion under `uv run python` with `PYTHONPATH=src:.` (see `Makefile:43`). Every CLI and Makefile target this plan introduces must follow that pattern — no bare `python3 -m ...`.

---

## Three phases

| Phase | What it does | External IO? |
|---|---|---|
| **A — Scrape + parse** | Walk SUIN sitemaps, fetch HTML, extract typed cross-references with BeautifulSoup into a normalized intermediate (JSONL). | Yes (read-only). |
| **B — Integrate with existing pipeline** | Merge the intermediate into `parser.py` / `classifier.py` outputs so the Supabase sink + Falkor loader pick it up for free. Expand `EdgeKind` + the DB CHECK vocabulary where the SUIN verbs don't cleanly map. | No new. |
| **C — Retrieval + surfacing** | Teach the retriever to carry vigencia + modification chains into the evidence bundle; teach `answer_support.py` to surface them. | No new. |

A and B must ship together for Supabase to have new data to serve. C is valuable on its own but can be sequenced after.

---

## Phase A — Scrape + parse

### Files to create

1. **`src/lia_graph/ingestion/suin/__init__.py`** — package marker; exports the two public entry points below.

2. **`src/lia_graph/ingestion/suin/fetcher.py`** (~200 LOC).
   - `class SuinFetcher`: wraps `httpx.Client` with:
     - User-Agent identifying LIA + a contact email.
     - Default 1 req/s rate limit (configurable via `LIA_SUIN_RPS`), exponential backoff on 5xx, 2xx+304 caching keyed on `(url, last_modified)`.
     - Local cache at `cache/suin/<sha1(url)>.html` (outside `artifacts/` — not part of the corpus snapshot). Include `cache/suin/_manifest.jsonl` with `{url, sha1, fetched_at, etag}`.
     - `iter_sitemap(sitemap_url) -> Iterable[str]`: XML parser with recursive sitemap-index support.
   - `SITEMAPS`: ordered list of the reachable sitemap URLs (confirmed alive: `sitemapleyes.xml`, `sitemapconsejoestado.xml`, `sitemapcircular.xml`, `sitemapinstruccion.xml`, `sitemapacuerdo.xml`). Each entry records whether it's `REQUIRED` (fail the run if missing) or `OPTIONAL` (warn + continue).
   - Respects `robots.txt` on boot — fetch once and enforce its allow list; fail closed if robots disallows a path we planned to crawl.

3. **`src/lia_graph/ingestion/suin/parser.py`** (~300 LOC).
   - `class SuinDocument`: `doc_id`, `ruta` (e.g. `Decretos/1132325`), `title`, `emitter`, `diario_oficial`, `fecha_publicacion`, `rama`, `materia`, `vigencia`, `articles: list[SuinArticle]`.
   - `class SuinArticle`: `article_number`, `article_fragment_id` (the `ver_<id>` anchor), `heading`, `body_html`, `outbound_edges: list[SuinEdge]`.
   - `class SuinEdge`: `verb` (raw Spanish token from the `<span>`), `scope` (optional parenthetical, e.g. `"inciso 1 parágrafo 3"`), `target_ruta`, `target_fragment_id`, `target_citation` (the anchor text, e.g. `"Artículo 139 LEY 1607 de 2012"`), `container_kind` (`"NotasDestino"` = legislative, `"NotasDestinoJurisp"` = jurisprudence, `"NotasOrigen"` = reciprocal on sentencia side, `"leg_ant"` = prior-text archive).
   - `parse_document(html: str, doc_id: str) -> SuinDocument`:
     - BeautifulSoup (`lxml` backend, streamed for large docs — ET is ~16 MB).
     - Split into articles by `<a name="ver_<id>">` anchors and their sibling `<div class="articulo_normal">`.
     - For each article, collect all `li.referencia` descendants; route by container-id prefix; extract `<span>` verb, parenthetical scope (regex `\s*\(([^)]+)\)\s*`), and the `<a>` target.
     - Normalize `target_ruta` from `href="/viewDocument.asp?id=<n>#ver_<m>"` → `(id=n, fragment=m)`.
   - `VERB_NORMALIZER`: dict that lowercases + strips accents + collapses whitespace + maps the known 74-token long tail onto a closed vocabulary of 11 canonical verbs:
     - `modifica` (covers: modificado, modificado parcialmente, sustituido, modificado y adicionado, subrogado)
     - `adiciona` (covers: adicionado, adicionado parcialmente)
     - `deroga` (covers: derogado, derogado parcialmente)
     - `reglamenta` (covers: reglamentado, reglamentado parcialmente)
     - `suspende`
     - `anula` (nulidad / anulado)
     - `declara_exequible`
     - `declara_inexequible`
     - `inhibida` (inhibida para emitir pronunciamiento)
     - `estarse_a_lo_resuelto`
     - `nota_editorial`
   - An unrecognized verb raises `UnknownVerb` with the raw token — we fail loud, not silently drop. Extending the vocabulary is a code edit, not a silent fallback.

4. **`src/lia_graph/ingestion/suin/harvest.py`** (~150 LOC).
   - CLI, invoked as `PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest --scope <scope> --out <dir>` (matches the existing `Makefile:43` convention — do not use bare `python3`).
   - Scopes (pick one):
     - `et` — Decreto 624/1989 only (single URL, ~6k edges, ~15 min including cache).
     - `tax-laws` — the ET plus the tax reform laws reachable from its outbound links (Ley 1819/2016, 2155/2021, 2277/2022, and their reglamentary decretos). Depth-1 walk from ET article edges, filtered to `Leyes` + `Decretos` rutas.
     - `jurisprudence` — walk `sitemapconsejoestado.xml` filtered to docs that cite any ET article fragment in their `NotasOrigen*` blocks. This produces the sentencia→article reciprocal edges.
     - `full` — all three.
   - Writes:
     - `artifacts/suin/<scope>/documents.jsonl` — one row per `SuinDocument` sans articles.
     - `artifacts/suin/<scope>/articles.jsonl` — one row per `SuinArticle` sans edges.
     - `artifacts/suin/<scope>/edges.jsonl` — one row per `SuinEdge`, each keyed by `(source_doc_id, source_article_key, target_doc_id, target_article_key, canonical_verb, scope, container_kind)`.
     - `artifacts/suin/<scope>/_harvest_manifest.json` — run summary: URLs crawled, cache hit rate, per-verb edge counts, unknown-verb failures (should be zero).

### Files to modify

5. **`Makefile`** — add `phase2-suin-harvest-et`, `phase2-suin-harvest-tax-laws`, `phase2-suin-harvest-jurisprudence`, `phase2-suin-harvest-full` targets calling the CLI with the matching `--scope`.

6. **`.gitignore`** — add `cache/suin/` (it's an HTTP cache, not an artifact).

### Tests

7. **`tests/test_suin_parser.py`** (~250 LOC). Fixtures: minimal handcrafted HTML snippets covering every canonical verb + each container kind + the reciprocal `NotasOrigen` idiom + the `leg_ant` archive. Plus one fixture sourced from a real SUIN doc for regression (saved under `tests/fixtures/suin/`).
   - `test_parses_single_article_with_destino`
   - `test_parses_jurisp_container_maps_to_canonical_verb`
   - `test_parses_reciprocal_origen_on_sentencia`
   - `test_unknown_verb_raises_loud`
   - `test_scope_parenthetical_extracted`
   - `test_et_fragment_large` — parses a 15 MB synthetic doc in <30s on CI and emits ≥5,000 edges; streaming works.

8. **`tests/test_suin_fetcher.py`** (~120 LOC). Uses `httpx.MockTransport` — no real network.
   - `test_respects_robots_disallow`
   - `test_rate_limit_enforced`
   - `test_cache_hit_avoids_refetch`
   - `test_5xx_backoff_then_succeed`

### Acceptance (Phase A)

- `make phase2-suin-harvest-et` completes in <20 min from a cold cache, <2 min from a warm cache.
- Produces a `edges.jsonl` with ≥6,000 rows, all with known canonical verbs, ≥99% with a non-null `target_article_key` (the `ver_<id>` fragment).
- Zero `UnknownVerb` failures on the ET scope. Any failure is a parser bug, not a data problem — fix the parser, not the data.
- All `tests/test_suin_*.py` green.

---

## Phase B — Integrate with existing pipeline

This is where SUIN stops being a side directory and starts producing rows the existing loader + Supabase sink already know how to write.

### The mapping problem

`EdgeKind` today (`src/lia_graph/graph/schema.py:19`) has: `REFERENCES, MODIFIES, SUPERSEDES, EXCEPTION_TO, REQUIRES, COMPUTATION_DEPENDS_ON, DEFINES, PART_OF`.

The Supabase CHECK constraint on `normative_edges.relation` allows: `references | modifies | complements | exception_for | derogates | supersedes | suspends | struck_down_by | revokes | cross_domain`.

SUIN canonical verbs: `modifica | adiciona | deroga | reglamenta | suspende | anula | declara_exequible | declara_inexequible | inhibida | estarse_a_lo_resuelto | nota_editorial`.

Proposed mapping — SUIN verb → `EdgeKind` → DB relation:

| SUIN verb | EdgeKind | DB relation | Notes |
|---|---|---|---|
| `modifica` | `MODIFIES` | `modifies` | already wired |
| `adiciona` | `MODIFIES` | `modifies` | semantic match; carry `scope` as property |
| `deroga` | **new: `DEROGATES`** | `derogates` | DB already allows this; `EdgeKind` doesn't — add it |
| `reglamenta` | **new: `REGLAMENTA`** | `complements` | DB `complements` is the nearest; add edge kind for graph typing |
| `suspende` | **new: `SUSPENDS`** | `suspends` | DB allows; add `EdgeKind` |
| `anula` | **new: `ANULA`** | `revokes` | DB allows; add `EdgeKind` |
| `declara_exequible` | **new: `DECLARES_EXEQUIBLE`** | `references` | affirms constitutionality; no structural change, but the *edge to the sentencia* is still meaningful |
| `declara_inexequible` | **new: `STRUCK_DOWN_BY`** | `struck_down_by` | DB allows; this is the one we most need |
| `inhibida` | `REFERENCES` | `references` | sentencia touched the article but did not rule |
| `estarse_a_lo_resuelto` | `REFERENCES` | `references` | procedural reference |
| `nota_editorial` | — | — | skip; carry as metadata on the article, not as an edge |

Five new `EdgeKind` members. The existing `_RELATION_MAP` in `supabase_sink.py:52` expands to cover them.

### Files to create

9. **`src/lia_graph/ingestion/suin/bridge.py`** (~200 LOC).
   - `build_parsed_articles(documents: Iterable[SuinDocument]) -> list[ParsedArticle]`: converts SUIN articles into the same `ParsedArticle` shape the existing parser produces, so chunk writing and embedding work unchanged. `source_path` is synthesized as `suin://<ruta>` so it survives `_sanitize_doc_id`.
   - `build_classified_edges(documents: Iterable[SuinDocument]) -> list[ClassifiedEdge]`: converts `SuinEdge` into `ClassifiedEdge` with `confidence=1.0` (DOM-sourced, not NLP-inferred) and `rule="suin_dom_extraction"`. Uses the mapping table above.
   - `build_document_rows(documents: Iterable[SuinDocument]) -> list[dict]`: produces the dicts `SupabaseCorpusSink.write_documents` expects, with `source_type="suin_norma"`, `authority` derived from `emitter`, `topic` from `rama`+`materia`, `knowledge_class="normative_base"` for Decretos/Leyes, `"jurisprudence"` for sentencias.
   - Note: an article's `status` is set from the SUIN `vigencia` attribute directly (`"vigente" | "derogada" | "suspendida"`), not regex-sniffed from prose. This is stricter than the existing parser.

### Files to modify

10. **`src/lia_graph/graph/schema.py`** — add the five new `EdgeKind` members + their `GraphEdgeType` entries in `default_graph_schema()`. Keep them alphabetized inside the existing block.

11. **`src/lia_graph/ingestion/classifier.py`** — extend `_classify_candidate` to recognize the new hints so edges from *other* sources (future DIAN normograma ingestion, etc.) can also produce them. This is a forward-compat change; SUIN itself bypasses the classifier via the bridge.

12. **`src/lia_graph/ingestion/supabase_sink.py`** — extend `_RELATION_MAP` and `_ALLOWED_RELATIONS` per the table above. Remove any new kind from `_RELATION_DROP`. The assertion on unknown kinds stays. **While here, address pre-existing gap #1**: decide what to do with `REQUIRES`, `COMPUTATION_DEPENDS_ON`, `DEFINES`, `PART_OF` (currently silently dropped). Recommended resolution: map `REQUIRES` and `COMPUTATION_DEPENDS_ON` to `references`, keep `DEFINES` and `PART_OF` dropped but add an inline comment explaining they are graph-topology concepts without a Postgres analogue. Do not defer this decision — we touch `_RELATION_DROP` in this PR regardless.

13. **`src/lia_graph/ingest.py`** (the `materialize_graph_artifacts` CLI).
    - New flag `--include-suin <scope>` that loads `artifacts/suin/<scope>/*.jsonl` via `suin.bridge.*` and merges the results into the existing `parsed_articles` + `classified_edges` buffers *before* the Supabase sink runs.
    - **Two-pass merge — required** (addresses pre-existing gap #2). Pass 1: materialize stub `documents`/`ParsedArticle` rows for every SUIN edge target that is not already present in the corpus (source_type=`suin_stub`, `curation_status="stub"`, body empty — just enough for FK integrity). Pass 2: the existing "skip unresolved edge" step now sees resolved targets for everything SUIN discovered. Emit a diagnostic: `{"suin_merge": {"replaced": N, "added": M, "stubs_created": K, "unresolved_after_stub": U}}` — `U` should be 0 on a clean SUIN scope.
    - Ordering matters: SUIN-sourced articles for a doc that the existing parser also produces should **replace** the existing rows (SUIN carries richer vigencia + the cross-references). Keyed on `doc_id`.

14. **`Makefile`** — **close Gap #3 by wiring `--execute-load` into the sink target.** The current `phase2-graph-artifacts-supabase` target (line 48) runs the Supabase sink but skips the Falkor write. Replace its recipe with:
    ```make
    phase2-graph-artifacts-supabase:
    	PYTHONPATH=src:. uv run python -m lia_graph.ingest \
    		--corpus-dir $(PHASE2_CORPUS_DIR) \
    		--artifacts-dir $(PHASE2_ARTIFACTS_DIR) \
    		--supabase-sink --supabase-target $(PHASE2_SUPABASE_TARGET) \
    		--execute-load --allow-unblessed-load --strict-falkordb \
    		--json
    ```
    `--execute-load` makes `materialize_graph_artifacts` call `load_graph_plan(..., execute=True)` at `src/lia_graph/ingest.py:499`, which drives the existing Falkor writer. `--allow-unblessed-load` bypasses the reconnaissance gate (we're running against production — the gate's "canonical blessing" only matters for local artifacts). `--strict-falkordb` ensures we fail loud if FalkorDB is unreachable instead of silently skipping (production must never serve against a stale graph). Without this change, Phase B ingests to Supabase only and cloud Falkor stays frozen at 2,568 nodes — defeating half the plan.

    **Aside — struck migration:** an earlier draft included `supabase/migrations/20260420000000_normative_edges_relation_expand.sql`. It is **not needed**: the baseline CHECK at `supabase/migrations/20260417000000_baseline.sql:1129` already permits every DB relation this plan maps to. Verified during the health check. Skip entirely.

### Tests

15. **`tests/test_suin_bridge.py`** (~150 LOC). Round-trip fixtures from Phase A into `ParsedArticle` / `ClassifiedEdge` and assert:
    - Every canonical verb maps to a non-null `(EdgeKind, DB relation)` pair.
    - `nota_editorial` produces zero edges (article annotation only).
    - Vigencia flows through: a SUIN article flagged `derogada` becomes a `ParsedArticle(status="derogado")`, which downstream writes `document_chunks.vigencia="derogada"` + `chunk_section_type="historical"`.
    - `basis_text` on `normative_edges` carries the original SUIN anchor text (e.g. `"Artículo 139 LEY 1607 de 2012"`), so a consumer can cite it verbatim.

16. **`tests/test_ingestion_supabase_sink.py`** — add case `test_writes_suin_relations`: given a `ClassifiedEdge` with each new `EdgeKind`, the sink writes a row with the correct DB relation. Confirm `struck_down_by` and `derogates` both land.

### Acceptance (Phase B)

- `make phase2-graph-artifacts-supabase INGEST_SUIN=et` produces, **in both Supabase and Falkor**:
  - Supabase: a non-empty `normative_edges` delta vs. the last generation, with rows in at least: `modifies`, `derogates`, `struck_down_by`, `complements`.
  - Supabase: `documents` rows of `source_type="suin_norma"` for the ET plus every law the ET edges point at (depth-1).
  - Supabase: chunks with accurate `vigencia` — a known-derogated article shows `derogada` without regex heuristics.
  - **Falkor**: `GRAPH.QUERY LIA_REGULATORY_GRAPH "MATCH (n) RETURN count(n)"` climbs measurably above the pre-run baseline (captured before the run). If it doesn't, `--execute-load` didn't fire — check the command.
  - **Falkor**: the same SUIN edge types appear on a spot-check: `GRAPH.QUERY LIA_REGULATORY_GRAPH "MATCH ()-[r:MODIFIES|DEROGATES|STRUCK_DOWN_BY]->() RETURN type(r), count(*) LIMIT 10"`.
- Existing `tests/test_ingestion_*.py` stay green.
- `npm run dev` (artifacts mode) is unaffected — SUIN data lands in Supabase + Falkor only when `--include-suin` is passed.
- **First moment SUIN appears in staging answers**: immediately after this target completes successfully — no embedding run required, because `hybrid_search`'s FTS half returns SUIN chunks without embeddings (health-check Gap #4). An optional follow-up `embedding_ops.py` run lifts retrieval quality for both SUIN and the existing 2,064 un-embedded chunks.

---

## Phase C — Retrieval + surfacing

This is where the new edges become visible to the user. Sequencing after A+B so we can ship data first, UX second.

### Files to modify

17. **`src/lia_graph/pipeline_d/retriever.py`** and **`retriever_supabase.py`** — when assembling the `EvidenceBundle` for an article, attach:
    - `modification_chain`: ordered list of `modifies` / `adiciona` / `deroga` edges whose source is the article, sorted by the target doc's `fecha_publicacion`. Most recent first.
    - `jurisprudence`: list of `struck_down_by` / `declara_exequible` / `references` (from sentencias) edges into the article.
    - `vigencia`: pulled directly from `document_chunks.vigencia` (already populated by the bridge).
    - Both retrievers must return the same shape — keep the contract parity that Phase B of `corpus_supabase_cutover.md` established.

18. **`src/lia_graph/pipeline_d/answer_support.py`** — when `vigencia != "vigente"` or the `modification_chain` is non-empty, include a short "Estado del artículo" note in the supporting evidence that synthesis can consume. The note is data, not prose — synthesis decides whether and how to render it.

19. **`src/lia_graph/pipeline_d/answer_policy.py`** — extend the policy so:
    - A derogated article triggers a top-of-answer flag (not buried mid-paragraph).
    - When a sentencia exists for the article, cite it by name in the rationale block.

Do NOT change `answer_assembly.py`. Per the product memory, the multi-question block shape is already settled — this is a content signal, not a layout change.

### Tests

20. Extend `tests/test_phase3_graph_planner_retrieval.py` with two cases:
    - `test_retriever_attaches_modification_chain` — a query hitting ET art. 631 returns a bundle with ≥1 entry in `modification_chain`.
    - `test_retriever_flags_struck_down_article` — a query hitting any ET article with a `struck_down_by` edge returns `vigencia != "vigente"` and a non-empty `jurisprudence` list.

21. Add a prompt-level regression in `tests/fixtures/chat_regressions/` for a question about a known-derogated article. The expected synthesis must mention derogation prominently.

### Acceptance (Phase C)

- On a curated 10-question regression suite covering modified + derogated + constitutionally-affected articles:
  - 100% of answers about derogated articles flag the status in the first paragraph.
  - 100% of answers about articles with Corte Constitucional rulings cite the sentencia.
  - No answer text references an article as "vigente" when SUIN says otherwise.

---

## Out of scope

- DIAN conceptos ingestion. SUIN does not carry them; `normograma.dian.gov.co` is a separate source and a separate plan.
- Backfilling sentencia *text* into `document_chunks`. We need the edges first; whether sentencia body text belongs in the retrieval corpus is a follow-up product call.
- Decretos Únicos Reglamentarios consolidation. Worth a dedicated pass — each DUR is a consolidated compendium and deserves its own scope.
- Full-text mirroring. We are not becoming SUIN's CDN — we keep the `ruta`/`fragment` reference and let the user click through for the original.

---

## Handoff checklist

Before implementing:

- Read `AGENTS.md`, `docs/guide/orchestration.md`, `docs/guide/env_guide.md`, and `docs/next/corpus_supabase_cutover.md`. SUIN ingestion sits on top of the latter; the cutover's Phase A + B are already live per the 2026-04-19 health check (cloud Supabase populated, cloud Falkor populated, retriever cutover wired).
- Skim the "Pre-implementation health check" section above. Four gaps were identified:
  - Gap #1 (`_RELATION_DROP`) → resolved in Phase B step #12.
  - Gap #2 (unresolved edge drop) → resolved in Phase B step #13 via the two-pass merge.
  - Gap #3 (Makefile target skips Falkor) → resolved in Phase B step #14 via `--execute-load --allow-unblessed-load --strict-falkordb`. **Do not skip this — it's the silent trap.**
  - Gap #4 (embeddings mis-cast as a gate) → no action required; `embedding_ops.py` is a follow-up quality lift, not a prerequisite.
- Before the first SUIN ingest, capture a Falkor baseline: `GRAPH.QUERY LIA_REGULATORY_GRAPH "MATCH (n) RETURN count(n)"` — the Phase B acceptance check asserts an increase from this number. The baseline at handoff is **2,568 nodes**.
- Confirm `cache/suin/` is added to `.gitignore` before the first harvest run — the cache will be sizeable and must not end up in commits or in `artifacts/`.
- Stage Phase A + B as one PR. Phase C can ship in a follow-up once stakeholders see the new edges in Supabase and Falkor.
- Invoke the new CLI under `uv run python` with `PYTHONPATH=src:.`, matching `Makefile:43`. Never use bare `python3`.
- Optional quality lift after Phase B merges to main: run `embedding_ops.py` against cloud Supabase to backfill the 2,064 existing chunks plus whatever new chunks SUIN added. This improves the vector half of `hybrid_search`; it does not change whether SUIN data is retrievable.

## Risks and how we address them

- **SUIN outage during a harvest** — the fetcher is resumable (cache-keyed by URL). A full harvest is retry-safe. We never require a successful crawl to mid-run to serve traffic; the bridge is idempotent through `generation_id`.
- **Silent SUIN HTML drift** — the parser fails loud on unknown verbs and emits a manifest with per-verb counts. A sharp count drop between generations is a regression signal worth alerting on; consider adding a `make phase2-suin-verify` target that diffs the latest manifest against the prior.
- **Editorial lag at SUIN** — SUIN's consolidated ET can trail a recent reform by weeks. We should prefer SUIN for historical truth and treat the raw reform text (already in the corpus) as the primary source for the newest articles. The retriever merge in step 17 already handles this: the most recent `modifies` edge wins.
- **Relationship ambiguity** — some verbs (`inhibida`, `estarse_a_lo_resuelto`) map to `references` only because we lack better buckets. Acceptable for now; revisit if users surface questions where the distinction matters.
