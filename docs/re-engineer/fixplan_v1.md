# Fix plan v1 — Lia Graph re-engineering

> ⚠️ **SUPERSEDED 2026-04-26 evening by [`fixplan_v2.md`](fixplan_v2.md)** after expert vigencia-checker skill delivery + Activity 1 measurement.
>
> v1 is preserved as the historical record of the pre-skill-integration plan. Read v2 for the current authoritative execution plan. The v1 → v2 delta is documented in detail in `skill_integration_v1.md`.
>
> **Headline differences:** v2 adopts the skill's 7-state vigencia taxonomy (was 6) + the 2D (formal × period) model; re-scopes Fix 1B into 3 sub-fixes (1B-α scrapers / 1B-β skill-guided extractor / 1B-γ materialize); replaces the Fix 5 judge schema with the skill's audit-LIA TRANCHE format; bumps the budget from $500K to $525K (skill-driven scraper infra absorbs $52K of the $60K v1 reserve, leaves $25K residual approved 2026-04-26 evening).

---

> **Funded:** USD 500K, 2026-04-26 evening. Decision per `makeorbreak_v1.md`: **SAVE**.
> **Timeline target:** 14 weeks to soft-launch readiness (4 weeks slack on the 12-week makeorbreak target).
> **Team shape recommended:** 1 tech lead + 2 senior backend engineers + 0.5 SME bandwidth + 0.25 ops/data.
> **Companion docs:** `docs/re-engineer/makeorbreak_v1.md` (the why), `docs/re-engineer/exec_summary_v1.md` (one-page founder view).
> **Reader assumption:** **none.** This document is written so a fresh engineer or fresh LLM with zero project context can start at §0 and execute. If you've worked in this repo before, skim §0–§0.6 and jump to §1.

---

## §0.5 — Required reading before you write any code (45 min, in this order)

1. **`CLAUDE.md`** (repo root, ~6 KB) — non-negotiables, run modes, hot path, decision rules. **Pay attention to the six-gate lifecycle policy in the Non-Negotiables section** — every fix below MUST pass all six gates before code is judged "an improvement," not just "code that compiles."
2. **`AGENTS.md`** (repo root) — layer ownership and surface boundaries (`main chat` vs `Normativa` vs `Interpretación` are distinct surfaces).
3. **`docs/orchestration/orchestration.md`** (~30 KB) — full architecture. The versioned env matrix at the bottom is authoritative; bumping its version is mandatory whenever a launcher flag, an `LIA_*` env, or a `query_mode` changes.
4. **`docs/orchestration/retrieval-runbook.md`** — line-level walkthrough of `pipeline_d/retriever_supabase.py` + `retriever_falkor.py`. Fix 1D rewrites parts of these; you must understand the current path first.
5. **`docs/orchestration/coherence-gate-runbook.md`** — every refusal mode (`fallback_reason`) mapped to its origin file:line. Fix 1D + Fix 3 both interact with this layer.
6. **`docs/learnings/README.md`** + scan the file list under `docs/learnings/{retrieval,ingestion,process}/` — 24 closed-fix lessons. Read fully any whose title sounds adjacent to your fix.
7. **`docs/re-engineer/makeorbreak_v1.md`** §0 ("Honest answer to 'what happened with vigencia in the graph?'") — the diagnosis Fix 1 is built around.
8. **This document, §0–§0.6 then your assigned Fix.**

If you read nothing else: read `CLAUDE.md` and the two runbooks. Everything else is reference.

---

## §0.6 — Project conventions every fix must follow

These are not preferences; they are mandatory:

| Convention | Where it lives | What it means for your fix |
|---|---|---|
| **Six-gate lifecycle** | `docs/aa_next/README.md` + `CLAUDE.md` Non-Negotiables | Every pipeline change passes idea → plan → measurable success criterion → test plan (with named actors + run env) → greenlight (technical + end-user) → refine-or-discard. **Unit tests green ≠ improvement.** All Success criteria + How to test sections in this doc are gate-3 + gate-4 specs; you must produce gate-5 evidence before declaring done. |
| **Tests are run via `make test-batched`** | `Makefile` + `tests/conftest.py` guard | Never run the full pytest suite directly — the conftest aborts unless `LIA_BATCHED_RUNNER=1` is set, to prevent OOM. Single tests are fine: `PYTHONPATH=src:. uv run pytest tests/test_X.py -q`. |
| **Migrations apply via `supabase db push --linked`** | per the v5 §1.D + §1.G workflows | Cloud writes against Lia Graph Supabase + Falkor are pre-authorized (see operator memory). Announce the action in one line, then execute. **Do NOT touch LIA_contadores resources.** |
| **`CREATE OR REPLACE FUNCTION` requires explicit `DROP FUNCTION IF EXISTS` first when changing parameter list** | `docs/learnings/retrieval/hybrid_search-overload-2026-04-27.md` | Every Fix 1D / Fix 2 / Fix 6 SQL function migration MUST drop the prior signature before recreating, or PostgREST will hit overload-ambiguity 500s. Verified on 2026-04-27 — do NOT relearn this. |
| **Env matrix bump on any launcher / `LIA_*` / `query_mode` change** | `docs/orchestration/orchestration.md` "Runtime Env Matrix (Versioned)" | Bump version in the same PR; add a change-log row; mirror the table in `docs/guide/env_guide.md` + `CLAUDE.md` + the `/orchestration` HTML map (`frontend/src/features/orchestration/orchestrationApp.ts`). |
| **Time format: Bogotá AM/PM for user surfaces; UTC ISO for machine logs** | `feedback_time_format_bogota.md` (operator memory) | All status reports, heartbeat outputs, dashboards in Bogotá `YYYY-MM-DD HH:MM:SS AM/PM`. Machine logs (`logs/events.jsonl`) stay UTC. Helpers exist in `scripts/eval/engine.py:bogota_now_human()`. |
| **Reuse `scripts/eval/engine.py` for any new chat-based eval** | (extracted 2026-04-27 §1.G) | `ChatClient`, `post_json`, `append_jsonl`, `completed_ids`, `git_sha`, `write_manifest`, `bogota_now_human`, `utc_iso` all live there. Fix 5 (golden judge), Fix 1D regression suite, Fix 4 SME re-run all consume this. **Do not write a third copy.** |
| **Atomic-design first for any UI** | `feedback_atomic_design_first.md` (operator memory) | Read `frontend/src/shared/ui/atoms+molecules` BEFORE writing UI. Fix 1E vigencia chips must mirror the existing `subtopicChip.ts` pattern; extract a molecule when a sub-pattern repeats 2+ times. |
| **Plain-language reports to operator** | `feedback_plain_language_communication.md` (operator memory) | Status reports, dashboards, exec summaries default to short, jargon-free. Engineering depth only when explicitly asked. |
| **No threshold lowering on missed gates** | `feedback_thresholds_no_lower.md` (operator memory) | If a Success criterion below isn't met, document the exception per case; do NOT relax the threshold itself. |
| **Long-running Python jobs: detached + heartbeat** | `CLAUDE.md` last section | Any job > 2 min must launch with `nohup + disown + > log 2>&1` (NO tee, NO `--json`-only output) and arm a 3-min heartbeat via `CronCreate` against `scripts/monitoring/ingest_heartbeat.py`. Fix 1B (7,883-article re-extraction) hits this. |
| **`pyproject.toml` entry points** | repo root | `lia-ui` (`ui_server.py`), `lia-graph-artifacts` (`ingest.py`), `lia-deps-check` (`dependency_smoke.py`). Run via `uv run <entry-point>`. |
| **Run modes** | `scripts/dev-launcher.mjs` | `npm run dev` (local, artifacts), `npm run dev:staging` (cloud Supabase + cloud Falkor), `npm run dev:production` (Railway). Never hardcode `LIA_CORPUS_SOURCE` / `LIA_GRAPH_MODE` in `.env.local` — the launcher owns them. Fix validation runs against `dev:staging` (matches §1.G run conditions). |

---

## §0. What happened with vigencia in the graph — honest diagnosis

The founder asked: *"We HAVE an ET corpus and a normograma and a Mintic normograma that talk about vigencia, and provide a whole HISTORY of a law, when created, when changed, etc — and that was supposed to be what the Graph would help with??? what happened???"*

Code-level audit done 2026-04-26 evening. Here is the truth.

### The architecture was designed correctly

The plumbing exists and it's the right plumbing:

- **Graph schema** (`src/lia_graph/graph/schema.py:166-190` + `EdgeKind` enum lines 23-44): `:ArticleNode` declares a `status` field. `EdgeKind` includes `SUPERSEDES`, `DEROGATES`, `MODIFIES`, `SUSPENDS`, `STRUCK_DOWN_BY`, `ANULA`. The ontology to express "Article X was derogated by Ley Y on date Z" is defined.
- **Supabase schema** (`supabase/migrations/20260417000000_baseline.sql:795`): `documents` table has `vigencia` (enum: `vigente / derogada / proyecto / desconocida / suspendida / parcial`), `vigencia_basis`, `vigencia_ruling_id` columns. The columns to store the structured data are reserved.
- **Composer features** (`pipeline_d/answer_historical_recap.py`, `pipeline_d/answer_comparative_regime.py`, `config/comparative_regime_pairs.json`): the user-facing surfaces for "tell me what changed" exist.

### The architecture was not connected

Three breaks turn that beautiful plumbing into water that never flows:

**Break 1 — The classifier never extracted vigencia.** `src/lia_graph/ingestion_classifier.py:279-298` (`AutogenerarResult` dataclass) emits topic, subtopic, doc-type, intent — but **zero vigencia fields**. The whole 7,883-article ingestion pipeline runs and the only "vigencia" derived is a binary regex flag in `ingestion/parser.py:234`: `status = "derogado" if DEROGATED_RE.search(full_text) else "vigente"`. Literally: if the word "derogado" appears anywhere in the article text, mark it derogado; else mark it vigente.

**Break 2 — The sink never populated the columns.** `src/lia_graph/ingestion/supabase_sink.py:639,646` writes `"vigencia": "vigente"|"derogada"` (the binary flag from break 1) but **never writes** `vigencia_basis` or `vigencia_ruling_id`. Those columns were created in the baseline migration and have stayed `NULL` for every row in production. The schema has the slot; nothing fills it.

**Break 3 — The retriever's vigencia filter is disabled in the common case.** `supabase/migrations/20260417000000_baseline.sql:188` shows that `hybrid_search` excludes `vigencia IN ('derogada', 'proyecto', 'suspendida')` **only when `filter_effective_date_max IS NULL`**. When the planner passes a temporal cutoff (which it does for most realistic queries), the vigencia filter is **skipped**. So even the impoverished binary flag we DO have is bypassed in the queries where it matters.

### Why historical recap + comparative regime didn't save us

`pipeline_d/answer_historical_recap.py` extracts year ranges and law citations from already-retrieved articles via regex (`_NORMATIVE_CHANGE_RE.findall(...)`) and formats them as narrative ("Reforma ancla: Ley 1819/2016"). It is a **display-layer flourish**, not a retrieval gate. If retrieval surfaced a derogated article, the recap dutifully narrates its history while the LLM cites the derogated rule as if vigente.

`pipeline_d/answer_comparative_regime.py` matches hardcoded pairs from `config/comparative_regime_pairs.json` (currently 1 entry: `perdidas_fiscales_2017`). Same pattern: post-retrieval assembly, no influence on what got retrieved.

### Why the corpus's own vigencia info didn't help

The source documents (ET, normograma, Mintic normograma) **do** contain vigencia info — but as **prose**: "Derogado por Ley 1819/2016 Art. 5", "Vigente desde 2016", "Modificado por Decreto 1234/2020". The ingest path's parser (`ingestion/parser.py:22-24`) only does keyword matching for the words "derogado", "modificado". It never extracts the **referent** (which Ley, which Decreto, which date). The structured information is lying in plain sight in every article and the ingester walks past it.

### One-sentence summary

**The engineers built the right house and never plumbed it.** The schema reserves rooms for vigencia metadata; the ingestion pipeline never delivers the metadata to the rooms; the retriever consequently has nothing to query against; and the only fallback filter that exists is silently disabled in the most common query shape. The historical features the user can SEE (recap, comparative regime) operate on text after retrieval — they cannot prevent retrieval from surfacing a derogated article in the first place.

This is good news. **Nothing in this diagnosis says the architecture is wrong.** Every fix below builds on the existing schema. None of it requires a re-architecture.

---

## §1. Fix overview

| Fix | Title | Weeks | Engineers | $K | Status gate |
|---|---|---|---|---|---|
| **Fix 1** | Vigencia as structural variable (schema → extractor → sink → retriever → UI) | 1–8 | 2.0 | 200 | week-4 midpoint kill switch |
| **Fix 2** | Parámetros móviles map + runtime injection (UVT, SMMLV, IPC, valores absolutos) | 2–6 | 1.0 | 80 | week-6 verified |
| **Fix 3** | Anti-hallucination guard on partial mode | 5–8 | 1.0 | 50 | week-8 zero fabricated refs |
| **Fix 4** | Ghost-topic kill + corpus completeness audit | 6–11 | 0.5 + SME | 70 | week-11 every topic ≥ 5 docs |
| **Fix 5** | Golden-answer regression suite (50+ canonical Qs, CI gate) | 1–14 | 0.5 + SME | 60 | week-14 ≥ 90% PASS |
| **Fix 6** | Internal corpus consistency editorial pass | 9–13 | 0.5 + SME | 40 | week-13 zero contradictions on probed sections |
| | **Reserve / contingency** | — | — | 50 | unallocated for emergent work |
| | **Total** | 14 wks | 5 FTE-weeks/wk avg | **500** | |

Fixes 1, 2, 3 are the **structural core** — without them the product is unsafe regardless of corpus quality. Fixes 4, 5, 6 are the **quality lock** — they prevent regression and close known content gaps. They run in parallel where possible.

---

## §2. Fix 1 — Vigencia as structural variable

This is the big one. It maps directly to the founder's insight: vigencia must be **structural**, not annotational.

### 2.1 Sub-fix 1A — Define the vigencia ontology

**What.** Replace the binary `status` field with a structured `Vigencia` value object. Slots:

| Field | Type | Example |
|---|---|---|
| `status` | enum | `vigente` / `derogado` / `suspendido` / `transicion` / `proyecto` / `desconocida` |
| `vigente_desde` | date \| null | `2016-12-29` |
| `vigente_hasta` | date \| null | `2021-09-13` (null = sin fecha de retiro) |
| `derogado_por` | citation \| null | `{ley: "Ley 1819", articulo: "Art. 5", fecha: "2016-12-29"}` |
| `modificado_por` | list[citation] | `[{ley: "Ley 2155", articulo: "Art. 51", fecha: "2021-09-14"}, ...]` |
| `suspension_actual` | citation \| null | `{sentencia: "CE 28920/2025", fecha_suspension: "2025-07-03", scope: "numeral 20"}` |
| `regimen_transicion` | citation \| null | `{ley_origen: "Ley 1819/2016", articulo_transicion: "Art. 290 #5"}` |
| `vigencia_audit` | object | `{extraction_method: "llm-gemini-2-flash-v2026-05", confidence: 0.92, reviewed_by: null}` |

**Success criteria.**
- The dataclass exists, lives in `src/lia_graph/vigencia.py`, has unit tests covering 12 canonical Colombian patterns (Decreto Reglamentario without retiro date, Ley derogada por Ley posterior, sentencia suspensiva del Consejo de Estado, régimen de transición Ley 1819 art. 290, etc.).
- The ontology doc exists at `docs/re-engineer/vigencia_ontology.md`, SME-signed.

**How to test.**
- 12 unit tests (the canonical patterns).
- SME walkthrough: present the ontology + 5 worked examples; SME signs off in writing.

**Effort.** 1 senior engineer × 1 week + SME × 0.3 week. Week 1.

**Files.**
- *Read first:* `src/lia_graph/graph/schema.py` (lines 23-44 EdgeKind enum, 166-190 ArticleNode), `src/lia_graph/ingestion/parser.py:22-50,151,196,234` (current binary `status` regex), `supabase/migrations/20260417000000_baseline.sql:264-450,795` (existing `vigencia` enum + reserved columns), `src/lia_graph/ingestion_classifier.py:279-298` (current `AutogenerarResult` shape — extend it).
- *Create:* `src/lia_graph/vigencia.py` (the dataclass + enum), `tests/test_vigencia_ontology.py` (12 canonical patterns), `docs/re-engineer/vigencia_ontology.md` (SME-signed reference).
- *Modify:* none yet — Sub-fix 1A is the contract; modifications start in 1B onwards.

### 2.2 Sub-fix 1B — Extract vigencia from existing corpus (LLM extraction pass)

**What.** Re-run the existing 7,883 articles through a vigencia-extraction pass. This is the missing classifier output. Use Gemini 2 Flash with a structured-output prompt that emits the `Vigencia` shape from §2.1. Skip articles where the vigencia extraction confidence is below 0.7 (route those to SME review queue).

**Cost.** 7,883 articles × ~3K tokens avg × Gemini Flash pricing ≈ USD 60–120 of LLM spend. One-time cost, fits inside the Fix 1 budget envelope.

**Success criteria.**
- ≥ 95% of articles produce a non-null `Vigencia` record.
- ≥ 80% of articles have `extraction_confidence >= 0.7`.
- 100% of `derogado` extractions cite the deroganting norm (no naked "derogado" without `derogado_por`).
- A 100-article spot-check by the SME shows ≥ 95 correct extractions.

**How to test.**
- After extraction completes: `scripts/audit_vigencia_extraction.py` reports the % at each confidence bucket.
- SME spot-check: 10 articles per topic × 12 topics = 120 articles, SME marks correct/incorrect.
- Gate: if SME spot-check < 95% correct, the prompt is wrong; iterate before populating the DB.

**Effort.** 1 senior engineer × 2 weeks. Weeks 2–3.

**Files.**
- *Read first:* `src/lia_graph/ingestion_classifier.py` (full — understand how Gemini is called today, prompt structure, structured-output discipline; mirror the same pattern), `scripts/launch_phase9a.sh` + `scripts/monitoring/ingest_heartbeat.py` + `scripts/monitoring/README.md` (the long-running-job launcher pattern — Fix 1B hits this), `artifacts/parsed_articles.jsonl` (the corpus you'll iterate over).
- *Create:* `src/lia_graph/ingestion/vigencia_extractor.py` (the LLM extraction module, mirrors `ingestion_classifier.py` shape), `scripts/extract_vigencia.py` (the one-off batch script, launched detached per the long-running-job convention), `evals/vigencia_extraction_v1/` (the SME spot-check fixture + audit outputs), `scripts/audit_vigencia_extraction.py` (the confidence-bucket reporter).
- *Modify:* `src/lia_graph/ingestion_classifier.py:279-298` (`AutogenerarResult` gains `vigencia: Vigencia | None`), `Makefile` (new target `phase2-extract-vigencia`).

### 2.3 Sub-fix 1C — Materialize vigencia in Supabase + Falkor

**What.** Populate the existing-but-unfilled `documents.vigencia_basis` and `documents.vigencia_ruling_id` columns. Add new columns where needed (`vigente_desde`, `vigente_hasta`, `modificado_por jsonb`, `suspension_actual jsonb`, `regimen_transicion jsonb`). Add `vigencia` properties to `:ArticleNode` in Falkor. Materialize the missing edges: `(:ArticleNode)-[:DEROGATED_BY {fecha, ruling_id}]->(:ArticleNode|:Doc)`, `(:ArticleNode)-[:MODIFIED_BY {fecha, ruling_id}]->(:ArticleNode|:Doc)`, `(:ArticleNode)-[:SUSPENDED_BY {sentencia_id, scope}]->(:Sentencia)`.

**Success criteria.**
- `SELECT COUNT(*) FROM documents WHERE vigencia_ruling_id IS NULL AND vigencia = 'derogada'` returns 0.
- `MATCH (a:ArticleNode {status: 'derogado'}) WHERE NOT EXISTS((a)-[:DEROGATED_BY]->()) RETURN count(a)` returns 0.
- The Vigencia value object round-trips: write to Supabase + Falkor, read back, verify identity on 50 random articles.

**How to test.**
- Migration scripts have unit tests against local Supabase + local Falkor docker.
- Post-deployment audit query: returns the four counts above (each must be 0).

**Effort.** 1 senior engineer × 2 weeks. Weeks 3–4.

**Files.**
- *Read first:* `src/lia_graph/ingestion/supabase_sink.py:639,646` (where `vigencia` is currently written from the binary flag — extend to populate the rest), `src/lia_graph/ingestion/loader.py` (Falkor loader — `:ArticleNode` write path), `src/lia_graph/graph/client.py` (Falkor write client; `stage_detach_delete` + `stage_delete_outbound_edges` patterns from §6.5 already handle staged-write discipline), `scripts/sync_article_secondary_topics_to_falkor.py` (the precedent script for "back-fill a property to existing Falkor nodes without re-ingest").
- *Create:* `supabase/migrations/20260YYYY000000_vigencia_structural.sql` (adds `vigente_desde`, `vigente_hasta`, `modificado_por jsonb`, `suspension_actual jsonb`, `regimen_transicion jsonb` columns; populates from `evals/vigencia_extraction_v1/` extraction output), `scripts/sync_vigencia_to_falkor.py` (mirrors the `sync_article_secondary_topics_to_falkor.py` pattern), `scripts/audit_vigencia_integrity.py` (the four-zero audit).
- *Modify:* `src/lia_graph/ingestion/supabase_sink.py` (write all vigencia fields, not just the binary flag), `src/lia_graph/ingestion/loader.py` (emit `DEROGATED_BY` / `MODIFIED_BY` / `SUSPENDED_BY` edges with full properties from the extraction).
- **Convention reminder:** the migration MUST drop any prior `hybrid_search` overload before re-creating per `docs/learnings/retrieval/hybrid_search-overload-2026-04-27.md` — relevant if Sub-fix 1D's SQL change in §2.4 piggy-backs on the same migration.

### 2.4 Sub-fix 1D — Plumb vigencia into retrieval (the load-bearing change)

**What.** Two changes to `pipeline_d/retriever_supabase.py` and the `hybrid_search` SQL function:

1. **Active demotion.** RRF score is multiplied by `0.0` for `derogado`, `0.1` for `suspendido`, `0.5` for `transicion`, `1.0` for `vigente`. Default factor: `0.0` for derogado (effectively a filter). This works regardless of whether `filter_effective_date_max` is passed (fixing break 3 from §0).
2. **Period-aware retrieval.** A new `vigencia_at_date` planner signal: when the user's question references a year ("para 2024", "antes de 2017"), the retriever filters to articles whose `[vigente_desde, vigente_hasta]` interval contains that date.

The Falkor traversal is updated symmetrically: `MATCH ... WHERE a.vigencia.status = 'vigente'` becomes the default; `[:DEROGATED_BY]` edges are not traversed in the article-neighborhood query unless the planner explicitly asks for historical context.

**Success criteria.**
- For 30 canonical questions about vigente law, **0 derogated articles** appear in the top-5 primary articles.
- For 10 canonical questions about historical law ("¿Qué decía el art. 147 ET antes de la Ley 1819?"), the derogated article is correctly retrieved AND labeled as historical.
- Re-run §1.G (the 36 SME questions): zero `art. 689-1` citations in any answer (currently 4+ answers cite it).

**How to test.**
- 40 question regression set lives in `evals/vigencia_v1/`. Each question carries the expected vigencia status of its top citation.
- CI gate: the 30 vigente-law questions must pass at 100% (zero derogated leaks); the 10 historical questions must correctly label as historical.
- Re-run the §1.G SME 36 questions; the SME re-verifies whether their `⚠️` and `❌` answers shifted to `🟨` or better.

**Effort.** 1.5 senior engineers × 2 weeks. Weeks 5–6.

**Files.**
- *Read first:* `src/lia_graph/pipeline_d/retriever_supabase.py:47-189` (full hybrid-search call site + payload + try/except fallback shape — mirror that for `vigencia_filter`), `src/lia_graph/pipeline_d/retriever_falkor.py` (full — current Cypher BFS), `supabase/migrations/20260427000000_topic_boost.sql` (the precedent for adding a new RPC parameter — copy the structure), `supabase/migrations/20260428000000_drop_legacy_hybrid_search.sql` (the cleanup fix; understand the overload trap), `src/lia_graph/pipeline_d/contracts.py` (the planner contract — `vigencia_at_date` is a new planner signal).
- *Create:* `supabase/migrations/20260YYYY000000_hybrid_search_vigencia.sql` (drops the v5 §1.D 15-arg overload; recreates with the new `vigencia_filter`/`vigencia_at_date` parameters), `evals/vigencia_v1/` (40-question regression set: 30 vigente + 10 historical), `tests/test_retriever_vigencia_demotion.py`.
- *Modify:* `src/lia_graph/pipeline_d/retriever_supabase.py` (add vigencia params to payload), `src/lia_graph/pipeline_d/retriever_falkor.py` (add `WHERE a.vigencia.status = 'vigente'` defaults; gate `[:DEROGATED_BY]` traversal on planner historical-context flag), `src/lia_graph/pipeline_d/planner.py` (extract `vigencia_at_date` from user message — mirrors the `comparative_regime_chain` cue-detection pattern at `pipeline_d/answer_comparative_regime.py`), `src/lia_graph/pipeline_d/contracts.py` (`GraphRetrievalPlan.vigencia_at_date: date | None`).
- **Env matrix bump required:** the new RPC parameters change retrieval shape → version bump + change-log row + `LIA_VIGENCIA_FILTER_MODE` env if you make it toggleable. Default to `enforce` in all three modes per the `project_beta_riskforward_flag_stance` memory.

### 2.5 Sub-fix 1E — User-facing vigencia labeling

**What.** Every cited article in an answer carries a vigencia chip: `vigente` (no chip — default), `derogado por X` (red chip), `suspendido (sentencia Y)` (yellow chip), `régimen de transición — ver art. Z` (blue chip). The composer policy enforces: an answer that cites a `derogado` or `suspendido` article MUST include the chip; an answer about historical regimes MUST display the comparative-regime table.

**Success criteria.**
- 100% of cited derogado/suspendido articles in test answers carry a chip.
- The chip styling matches the existing `subtopicChip.ts` atomic-design pattern (per the `atomic_design_first` memory).

**How to test.**
- Component test: render 5 chip variants in `frontend/tests/`.
- E2E test: the 10 historical questions in §2.4 produce answers with vigencia chips visible.

**Effort.** 0.5 frontend engineer × 2 weeks. Weeks 7–8.

**Files.**
- *Read first:* `frontend/src/shared/ui/atoms/subtopicChip.ts` (mirror this pattern exactly), `frontend/src/shared/ui/molecules/intakeFileRow.ts` (precedent for chip composition into a row), the atomic-design memory (`feedback_atomic_design_first.md`).
- *Create:* `frontend/src/shared/ui/atoms/vigenciaChip.ts` (4 variants: vigente — no chip; derogado — red; suspendido — yellow; transición — blue), `frontend/tests/vigenciaChip.test.ts`.
- *Modify:* whichever existing molecule renders citation labels in `frontend/src/features/chat/` — extend it to consume the new chip atom.
- *Backend contract:* the chat response payload's `citations[].vigencia` field must already be populated by Sub-fix 1D's retriever changes; verify this before touching frontend.

### 2.6 Fix 1 — gate criteria (the kill switch from `makeorbreak_v1.md` week 4)

After §2.4 ships (end of week 6), re-run the §1.G SME questions on `beneficio_auditoria`, `firmeza_declaraciones`, `dividendos_y_distribucion_utilidades`. Required result:

- **Zero** citations of `art. 689-1` (currently appears in 4+ answers).
- **Zero** "6 años" claims for firmeza con pérdidas (currently appears in 3+ answers).
- **Zero** dividend tariff claims at 10% (currently appears in 2+ answers; the post-Ley-2277 tariff is 19%/35% by tramo).

If any of those three persist after week 6, **the project is in trouble**. Per `makeorbreak_v1.md`, this triggers the brand/risk perspective: pause and reassess before continuing.

---

## §3. Fix 2 — Parámetros móviles map (Colombia-specific annual amounts)

Colombia's tax law indexes nearly every monetary threshold to UVT (Unidad de Valor Tributario), which the DIAN re-publishes every December for the following year. Beyond UVT there are SMMLV (salario mínimo), IPC (variation index used in some thresholds), and absolute peso amounts (rare but real — e.g. some Decretos Reglamentarios carry pesos directly). When a document was indexed in 2024, it cites UVT 2024 = $47.065. The same answer in 2026 should cite UVT 2026 = $52.374. Today, LIA cites the stale value because it lives in the document text and never gets refreshed.

### 3.1 Canonical parameter table

**What.** A `config/parametros_moviles/` directory with one YAML file per year, e.g. `2024.yaml`, `2025.yaml`, `2026.yaml`. Each file declares:

```yaml
year: 2026
uvt:
  value_cop: 52374
  source: "Resolución DIAN 000238 de 2025"
  effective_date: "2026-01-01"
smmlv:
  value_cop: 1423500
  source: "Decreto 1572 de 2024"
  effective_date: "2026-01-01"
ipc_anual:
  value: 5.20
  source: "DANE Boletín IPC dic-2025"
  effective_date: "2026-01-01"
# Topical thresholds derived from UVT
beneficio_auditoria:
  inr_minimo_uvt: 71
  inr_minimo_cop: 3718554       # 71 × 52374
  incremento_minimo_pct: 25      # firmeza 12 meses
  incremento_alto_pct: 35        # firmeza 6 meses
  source: "Art. 689-3 ET, par. 2"
firmeza_general_anios: 3
firmeza_perdidas_anios: 5
firmeza_beneficio_alto_meses: 6
firmeza_beneficio_normal_meses: 12
# ... and so on for every parameter that recurs in answers
```

**Success criteria.**
- Files for 2020, 2021, 2022, 2023, 2024, 2025, 2026 exist and are SME-signed.
- ≥ 40 distinct parameters covered (UVT, SMMLV, IPC, all topical thresholds the SME identified as recurring in §1.G).

**How to test.**
- Schema validation script: each YAML must conform to a Pydantic model.
- SME diff: SME reviews the 7-year × 40-parameter matrix and signs each cell.

### 3.2 Resolver module

**What.** `src/lia_graph/parametros.py` exposes:

```python
def resolve(parameter: str, *, year: int) -> ParameterValue
def list_for_year(year: int) -> dict[str, ParameterValue]
def detect_year_from_question(message: str, default: int = ...) -> int
```

`detect_year_from_question` matches patterns like "AG 2025", "para 2026", "del año 2024", "este año" (resolves against today's date in Bogotá), "el año pasado" (resolves to today - 1 year). Default when no signal: current year in Bogotá.

### 3.3 Composer-side rewrite + verification pass

**What.** A new pass in `pipeline_d/answer_synthesis_helpers.py` that runs after retrieval and before the LLM polish. For each numeric value in the candidate answer (`$XX UVT`, `$X.XXX.XXX pesos`, `XX%` against indexed thresholds), look up the canonical value at the question's year. If the candidate value disagrees with canonical:

- If the disagreement is on a value that's clearly UVT-indexed: rewrite the value to canonical, append a footnote `*[valor recalculado para AG {year}]`.
- If the disagreement is on a value that the parameter table doesn't cover: leave alone but log to `parametros_unrecognized.jsonl` for SME review.

The polish prompt is extended with: *"Do NOT change any peso amount or UVT value. Those have already been verified."*

**Success criteria.**
- 8 SME-curated questions whose correct answer requires a 2026 parameter the corpus only has at 2024 value: all 8 produce correct 2026 values after Fix 2 ships.
- Zero false rewrites (parameters that aren't UVT-indexed don't get touched) in a 50-answer regression.

**How to test.**
- Test fixture `evals/parametros_v1/8_uvt_questions.jsonl` with question + expected_value_2026 + expected_value_2024.
- Snapshot test: a 50-answer suite is run pre-and-post Fix 2; diffs are categorized as (a) correct refresh, (b) unchanged, (c) false rewrite. Required: 0% false rewrites.

**Effort.** 1 senior engineer × 4 weeks (weeks 2–6, parallel with Fix 1).

**Files.**
- *Read first:* `src/lia_graph/ui_text_utilities.py:_UVT_REF_RE` (the existing UVT-detection regex — extend rather than duplicate), `src/lia_graph/pipeline_d/answer_synthesis.py` (stable facade — do NOT edit; identify the implementation module to touch instead), `src/lia_graph/pipeline_d/answer_synthesis_helpers.py` (likely landing site for the rewrite pass), `src/lia_graph/pipeline_d/answer_llm_polish.py` (where the polish prompt is constructed — extend with the "do not change peso amounts" rule), `config/subtopic_taxonomy.json` (precedent for SME-curated YAML/JSON config — same loader pattern).
- *Create:* `config/parametros_moviles/{2020,2021,2022,2023,2024,2025,2026}.yaml`, `src/lia_graph/parametros.py` (resolver module), `src/lia_graph/parametros_schema.py` (Pydantic model for YAML validation), `tests/test_parametros_resolver.py`, `tests/test_parametros_year_detection.py`, `evals/parametros_v1/8_uvt_questions.jsonl` (the regression fixture), `scripts/audit_parametros_yaml.py` (validates YAML against schema; runs in CI).
- *Modify:* `src/lia_graph/pipeline_d/answer_synthesis_helpers.py` (insert rewrite pass after retrieval, before polish), `src/lia_graph/pipeline_d/answer_llm_polish.py` (extend polish prompt with parameter-protection rule).
- **Reuse:** the YAML loading + Pydantic-validation pattern likely already exists somewhere in `src/lia_graph/` — search for `from pydantic import` before writing a new loader.

---

## §4. Fix 3 — Anti-hallucination guard on partial mode

Per `src/lia_graph/pipeline_d/answer_policy.py:20-21`, when retrieval can't fill a sub-question the system emits the placeholder `"Cobertura pendiente para esta sub-pregunta..."`. The composer then wraps that placeholder in "Ruta sugerida" / "Riesgos" templates, and the LLM polish pass synthesizes plausible-looking content. The SME observed this content drifts toward facturación electrónica regardless of question.

### 4.1 Typed partial-coverage signal

**What.** Refactor so partial-coverage propagates as a typed `PartialCoverage` object, not a magic string. The composer renders these as a clear, restrained "no encontré evidencia para esta sub-pregunta — recomiendo escalar al SME" stub. NO Ruta sugerida, NO Riesgos, NO articles cited (synthetic or otherwise).

**Success criteria.**
- 12 known partial-mode questions (curated from §1.G + production logs) produce answers where partial sub-questions have ZERO fabricated article references and ZERO Ruta sugerida text.
- The unaffected sub-questions (where evidence was found) still render normally.

### 4.2 Polish-prompt hardening

**What.** The LLM polish prompt is extended with explicit forbidden behaviors:
- *"If a sub-question is marked PartialCoverage, you MUST NOT generate Ruta sugerida or Riesgos for it. Render only the canonical 'no encontré evidencia' line."*
- *"You MUST NOT invent article references. If a citation is not in the supplied evidence list, you MUST NOT cite it."*

Plus a post-polish guard: regex-scan the polished output for article-reference patterns (`art. N ET`, `art. N-N ET`, `paso-a-paso-pr-ctico`, `posiciones-de-expertos`); flag any not present in the evidence bundle as a hallucination, and in `enforce` mode, strip them.

**Success criteria.**
- The hallucination guard fires on a curated 20-question hallucination-bait fixture (pre-Fix-3: > 50% hallucinate; post-Fix-3: 0% hallucinate).
- Composer-level invariant test: when input has ≥ 1 PartialCoverage sub-question, output contains the canonical phrase exactly N times (one per partial sub-question) and zero "Ruta sugerida" tokens for those sub-questions.

**Effort.** 1 senior engineer × 4 weeks (weeks 5–8). Weeks 5–6 overlap Fix 1's retrieval rebuild; week 7–8 handles testing.

**Files.**
- *Read first:* `src/lia_graph/pipeline_d/answer_policy.py:20-21` (the literal "Cobertura pendiente" string — confirmed in §0 audit), `src/lia_graph/pipeline_d/answer_synthesis_sections.py:57-58,290-294` (where partial mode + facturación-electrónica fallback content lives), `src/lia_graph/pipeline_d/answer_synthesis_helpers.py:172-189` (the empty-fallback `fallback_recommendation` path), `src/lia_graph/pipeline_d/answer_llm_polish.py` (polish prompt + post-polish discipline; extend with the "no fabricated article refs" guard), `src/lia_graph/pipeline_d/orchestrator.py:547-549` (where `answer_mode = "graph_native_partial"` + `fallback_reason = pipeline_d_no_graph_primary_articles` is set).
- *Create:* `src/lia_graph/pipeline_d/partial_coverage.py` (the typed `PartialCoverage` value object + propagation helpers), `tests/test_partial_coverage_no_hallucination.py` (the 12-question hallucination-bait fixture + invariant tests), `scripts/audit_polish_hallucinations.py` (the post-polish regex scan + strip).
- *Modify:* `answer_policy.py`, `answer_synthesis_sections.py`, `answer_synthesis_helpers.py`, `answer_llm_polish.py` (granular per-module edits per the `feedback_respect_pipeline_organization` memory — do NOT collapse into a single file).

---

## §5. Fix 4 — Ghost-topic kill + corpus completeness audit

`tarifas_renta_y_ttd` is a **ghost topic**: registered in `config/topic_taxonomy.json` and `config/article_secondary_topics.json` with **zero** documents in `knowledge_base/`. The thin-corpus heartbeat shows it as SERVED only because some chunk mentioning "tarifa" surfaces from any topic. `regimen_cambiario` documents sit in `knowledge_base/CORE ya Arriba/Documents to branch and improve/to_upload/` — i.e., never indexed.

For a tax-advice product, "I do not cover the general tariff of renta" is product-killing.

### 5.1 Audit script + topic-completeness gate

**What.** `scripts/audit_topic_completeness.py` walks every topic in `config/topic_taxonomy.json` and counts documents in `knowledge_base/` tagged with that topic. Output: a table with `topic | doc_count | min_floor | status (ok|underpopulated|ghost)`. Topics under floor (default 5) are flagged.

A new launcher preflight (`dependency_smoke.py` extension) fails when any registered topic has 0 documents.

**Success criteria.**
- The audit runs in < 10 seconds.
- The preflight blocks any deploy where a registered topic has 0 docs.
- After Fix 4 lands, every topic has ≥ 5 docs OR is explicitly de-registered with a `not_in_v1` flag.

### 5.2 Populate the most-critical missing topics (SME work)

**What.** For each topic identified as ghost or underpopulated in §5.1:
- `tarifas_renta_y_ttd` — populate with at least: art. 240 ET (tarifa general 35%), art. 240-1 ET (régimen ZF), art. 241 ET (PN residentes), art. 242 ET (dividendos), Decreto Reglamentario actual, T-section operativa for cálculo TTD per Sección 14 of LIA Contador corpus.
- `regimen_cambiario` — promote `to_upload/cam_*.md` documents into the active corpus, validate retrieval surfaces them.
- Other underpopulated topics — case-by-case SME prioritization.

**Success criteria.**
- Re-run §1.G SME questions on `tarifas_renta_y_ttd`: at least 2/3 answers in 🟨 or better (currently 0/3 — all refused).
- Re-run on `regimen_cambiario`: at least 2/3 in 🟨 or better.

**How to test.**
- The §1.G runner (`scripts/eval/run_sme_validation.py`) re-executes the relevant qids; SME re-classifies.

**Effort.** SME × 0.5 FTE × 5 weeks (weeks 6–11) + 0.5 engineer for index + retrieval validation.

**Files.**
- *Read first:* `config/topic_taxonomy.json` (the 89 registered topics), `config/article_secondary_topics.json` (the topic→article curation per v5 §1.A), `config/citation_allow_list.json` (per-topic allow-list per v5 phase 4–5), `src/lia_graph/dependency_smoke.py` (the existing preflight — extend with topic-completeness check), `knowledge_base/CORE ya Arriba/Documents to branch and improve/to_upload/cam_*.md` (the un-indexed `regimen_cambiario` documents), `docs/learnings/ingestion/coherence-gate-thin-corpus-diagnostic-2026-04-26.md` (the prior thin-corpus inventory — Fix 4 closes the gaps it documented).
- *Create:* `scripts/audit_topic_completeness.py` (the doc-counter), `evals/topic_completeness_v1/baseline.json` (snapshot of pre-Fix-4 doc counts; for measurable delta), per-topic curation files for the populated topics (similar to `config/article_secondary_topics.json` shape).
- *Modify:* `src/lia_graph/dependency_smoke.py` (preflight gate), `config/topic_taxonomy.json` (add `not_in_v1: true` flag to de-registered topics), `knowledge_base/` (move `to_upload/cam_*.md` into the active corpus + add new `tarifas_renta_y_ttd` documents).
- *Re-ingest required:* after corpus changes, run `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` to refresh staging cloud per `CLAUDE.md`. This is a long-running job — apply the detached + heartbeat pattern.

---

## §6. Fix 5 — Golden-answer regression suite (the safety net)

Every fix above can land cleanly and still regress something else. The golden-answer suite is the regression net that catches accidental damage.

### 6.1 Authoring

**What.** SME drafts ≥ 50 canonical questions paced 5/week starting week 1. Each question has:

```yaml
qid: tarifas_renta_general_pj_2025
question: "¿Cuál es la tarifa general de renta para una SAS para AG 2025?"
canonical_answer_md: |
  La tarifa general del impuesto de renta para personas jurídicas en Colombia
  es del **35%** para AG 2025 (art. 240 inc. 1 ET, modificado por art. 10
  Ley 2277/2022).
must_cite:
  - "art. 240 ET"
  - "Ley 2277/2022"
must_not_say:
  - "33%"        # tarifa pre-Ley-2277
  - "32%"
  - "34%"
must_not_cite:
  - "art. 689-1 ET"  # derogated
expected_topic: "tarifas_renta_y_ttd"
expected_class: "served_strong"
sme_signoff: "alejandro_2026-04-30"
```

**Success criteria.**
- ≥ 50 questions authored by week 6, ≥ 100 by week 14.
- Every question is SME-signed.
- Coverage spans all 12 topics (≥ 4 per topic) plus 4 hard cross-topic questions.

### 6.2 Judge + CI gate

**What.** `scripts/eval/judge_golden.py` compares each LIA answer against canonical via:
1. **Hard checks**: every `must_cite` must appear in `citations`; every `must_not_cite` must not appear; every `must_not_say` regex must not match.
2. **Soft check**: LLM judge (Claude Haiku, prompted to be strict) scores semantic alignment between LIA answer and canonical answer on a 0–10 scale; ≥ 7 = PASS, 4–6 = SOFT_FAIL, < 4 = HARD_FAIL.

CI gate: any HARD_FAIL or any failed hard check blocks merge.

**Success criteria.**
- ≥ 90% PASS by week 14.
- Zero HARD_FAIL by week 14.
- Suite runs in < 15 minutes (parallel-safe).

**How to test.**
- Suite is wired into `make test-batched` and into GitHub Actions on every PR.
- Pre-merge gate: PR with any HARD_FAIL cannot be merged.

**Effort.** SME × 0.5 FTE for authoring (weeks 1–14) + 0.5 engineer for judge + CI wiring (weeks 1–4).

**Files.**
- *Read first:* `scripts/eval/engine.py` (**reuse this — do NOT write a third copy of the HTTP/JSONL/manifest plumbing**), `scripts/eval/run_sme_validation.py` (the §1.G runner — copy its parser + runner + classifier shape), `scripts/eval/sme_validation_report.py` (the aggregator + verbatim-doc shape — golden judge mirrors this), `scripts/judge_100qs.py` (the precedent LLM-judge harness; reuse its prompt structure + score parsing), `evals/100qs_accountant.jsonl` (precedent for golden-fixture JSONL shape), `Makefile` (the `eval-c-gold` / `eval-c-full` targets — mirror for `eval-golden`).
- *Create:* `evals/golden_answers_v1/questions/<qid>.yaml` (one per golden question per the YAML schema in §6.1), `scripts/eval/run_golden.py` (chat runner — thin wrapper over `engine.ChatClient`), `scripts/eval/judge_golden.py` (the strict-judge harness), `scripts/eval/golden_report.py` (PASS/SOFT_FAIL/HARD_FAIL dashboard), `.github/workflows/golden_ci.yml` (the merge-blocking CI gate), `Makefile` target `eval-golden`.
- *Modify:* root `CLAUDE.md` Commands section (add `make eval-golden`).
- **Project-wide convention reuse:** the engine's `bogota_now_human()` and `utc_iso()` helpers cover all timestamps; the engine's `ChatClient(auth=False)` matches the `:8787` direct-mode path used in §1.G; the engine's `completed_ids()` resume-on-Ctrl-C is the right primitive for golden re-runs after fixes.

---

## §7. Fix 6 — Internal corpus consistency editorial pass

The SME found three different versions of art. 242 num. 1 (dividend tariff) in three different sections. Internal contradictions defeat any retrieval mechanism.

### 7.1 SME-led editorial pass

**What.** SME walks the 12 §1.G topics + the 8 worst-offender topics from the audit (§5.1). For each topic, identify and reconcile internal contradictions. Mark superseded sections with frontmatter `superseded_by: <doc_id>` and exclude them from retrieval (similar treatment to derogados in Fix 1).

**Success criteria.**
- Re-run a 30-question subset of golden answers: zero contradictions detected (no answer cites two conflicting values from the corpus).
- Each touched document has a clear "canonical | superseded | historical" classification.

**How to test.**
- The judge from §6.2 detects internal contradictions when LIA's answer cites two values that disagree.
- SME spot-check on the 20 reviewed topics.

**Effort.** SME × 0.5 FTE × 5 weeks (weeks 9–13) + 0.5 engineer for the `superseded_by` retrieval support.

**Files.**
- *Read first:* the `knowledge_base/` documents the SME flagged in §1.G (specifically the 3 sections of art. 242 num. 1 and the deprecated/T-section files), `docs/learnings/ingestion/path-veto-rule-based-classifier-correction.md` (precedent for "the LLM ignores curation; need post-hoc rule override" — same shape applies to "the retriever ignores deprecated; need superseded_by demotion"), Sub-fix 1D outputs (Fix 6 piggy-backs on the same demotion machinery — `superseded_by` reuses `derogado_por` plumbing).
- *Create:* `docs/re-engineer/corpus_consistency_audit.md` (SME's per-topic findings + reconciliation decisions), per-document frontmatter additions (`superseded_by: <doc_id>` on the displaced sections), `evals/corpus_consistency_v1/30q_subset.jsonl` (the regression set).
- *Modify:* `knowledge_base/` documents flagged for supersession (frontmatter only — content stays for historical reference); `src/lia_graph/pipeline_d/retriever_supabase.py` + `retriever_falkor.py` (extend Fix 1D demotion to also demote on `superseded_by`); `src/lia_graph/ingestion/parser.py` (read the new `superseded_by` frontmatter field).

---

## §8. Cross-fix dependencies

```
Week:    1  2  3  4  5  6  7  8  9 10 11 12 13 14
Fix 1:   ████████████████  (1A→1B→1C→1D→1E)
Fix 2:      ████████████   (parallel to 1B-1D)
Fix 3:               ██████████   (after retrieval is structural)
Fix 4:                  █████████████   (after vigencia + parametros plumbing)
Fix 5:   █████████████████████████████   (continuous from week 1)
Fix 6:                     ████████████   (after Fix 4 SME bandwidth opens)
                           ↑                                        ↑
                       wk-4 KILL                              wk-14 LAUNCH
                       SWITCH                                   GATE
```

Hard ordering constraints:
- Fix 2 cannot ship its rewrite pass until Fix 1's vigencia layer is in (so the rewrite can use vigencia to pick which canonical value applies).
- Fix 3 cannot finalize until Fix 1D ships (so partial-coverage isn't masking vigencia-induced retrieval failures).
- Fix 6's editorial pass needs SME bandwidth which is consumed by Fix 4 in weeks 6–11; sequencing is tight.

---

## §9. Decision checkpoints

| Week | Gate | Pass criterion | Fail action |
|---|---|---|---|
| **4** | Vigencia ontology + extraction quality | SME spot-check ≥ 95% on 120-article sample | Iterate prompt; if still failing at week 5, escalate — likely a deeper extraction problem |
| **6** | Vigencia kill switch (from `makeorbreak_v1.md`) | Zero `art. 689-1`, zero "6 años", zero 10% dividend tariff in §1.G re-run | **Project in trouble; pause to reassess. Do not extend timeline blindly.** |
| **8** | Anti-hallucination + partial-mode lock | Zero fabricated article refs in 12-question hallucination fixture | Engineer-level fix; not project-threatening |
| **11** | Topic-completeness audit | Every registered topic ≥ 5 docs OR de-registered | SME backlog overflow; consider deferring 3+ topics to v2 |
| **14** | Final pre-launch gate | §1.G re-run ≥ 24/36 in 🟨 or better; zero ❌; golden suite ≥ 90% PASS, zero HARD_FAIL | Soft-launch denied; data-driven extend-or-liquidate decision |

---

## §10. Budget allocation

| Line | Amount (USD K) | Notes |
|---|---|---|
| Engineering: 2 senior backend × 14 wks | 200 | Lead the structural fixes |
| Engineering: 1 senior backend × 8 wks | 60 | Floats across Fix 2 + Fix 3 + Fix 4 |
| Frontend: 0.5 FTE × 4 wks | 25 | Vigencia chips + UI for Fix 1E |
| SME: 0.5 FTE × 14 wks | 90 | Ontology, extraction QC, golden answers, editorial pass |
| LLM extraction (Fix 1B) | 1 | Gemini Flash for 7,883-article re-pass |
| Cloud infra delta (Supabase + Falkor capacity for re-ingest) | 4 | Re-ingest passes for Fix 1 + Fix 4 |
| QA + CI tooling (Fix 5) | 30 | Judge harness + CI runners |
| Tooling: data-eng / ops 0.25 × 14 wks | 30 | Migration ops, deploy gating |
| Reserve / contingency | 60 | Emergent work, vendor surprises, week-14 spillover |
| **Total** | **500** | |

The reserve exists specifically because (per the v5 §1.G hybrid_search-overload incident) infrastructure surprises happen and the budget should not be the constraint that breaks a 14-week plan over a $5K cloud surprise.

---

## §11. What this plan deliberately does NOT do

Same list as `makeorbreak_v1.md §4` — repeated here so the team has it in one place:

- **No more incremental gates** (`§1.H`, `§1.I`...) on `next_v5.md`. The chain is closed; reopen only after Fix 1+2+3 ship.
- **No threshold relaxation.** Per `feedback_thresholds_no_lower`. The bar is and stays "safe to send to a client."
- **No soft-launch with disclaimer.** A disclaimer doesn't transfer the risk.
- **No corpus expansion until Fix 1 lands.** Adding documents to a corpus without vigencia tracking multiplies the contamination surface.
- **No retriever rewrite.** The retriever architecture is sound. Fix 1 changes its inputs (vigencia metadata) and its filter expression — not its algorithm.
- **No LLM model upgrade as first-line fix.** A better model fed contradictory or stale evidence still produces wrong answers.

---

## §12. What "done" looks like

At week 14, the operator runs `make eval-launch-readiness`. The output is:

```
=== Launch Readiness Report ===
Vigencia integrity:
  vigencia_ruling_id NULL on 'derogada' rows: 0 / 1247    ✅
  ArticleNode {status='derogado'} without DEROGATED_BY:    0 / 89    ✅
  Topics with 0 docs:                                       0 / 89    ✅

Retrieval safety:
  art. 689-1 leaks in vigente queries:                      0 / 30    ✅
  Pre-Ley-2277 dividend tariff in vigente queries:          0 / 12    ✅
  6-year firmeza claims in vigente queries:                 0 / 8     ✅

Anti-hallucination:
  Fabricated article refs in partial-mode answers:          0 / 20    ✅

Quality:
  §1.G SME re-run, 🟨 or better:                          26 / 36    ✅ (≥ 24)
  §1.G SME re-run, ❌:                                      0 / 36    ✅
  Golden answers PASS:                                    96 / 100   ✅ (≥ 90%)
  Golden answers HARD_FAIL:                                 0 / 100    ✅

LAUNCH READINESS: GREEN — soft-launch to 10–20 friendly cohort APPROVED.
```

If the report comes back GREEN, soft-launch with explicit beta framing and instrumented client-incident tracking. If it comes back RED on any line, the data tells us exactly what's still broken and what to do next — not panic, but informed iteration.

---

## §13. Glossary — Colombian tax + project terms

A non-Colombian engineer / LLM working on Lia Graph will trip over these. Memorize before week 1.

**Colombian tax law:**
- **AG** — *Año gravable*. The tax year a declaration covers. "AG 2025" = the income earned in 2025; the declaration is presented in 2026.
- **DIAN** — *Dirección de Impuestos y Aduanas Nacionales*. The Colombian tax authority (≈ IRS).
- **ET** — *Estatuto Tributario*. The Colombian Tax Code. References look like "art. 240 ET" or "art. 689-3 ET".
- **UVT** — *Unidad de Valor Tributario*. A tax unit re-published by the DIAN every December for the following year. Most monetary thresholds in Colombian tax law are denominated in UVT, not pesos. **UVT 2024 = $47.065 ; UVT 2025 = $49.799 ; UVT 2026 = $52.374.**
- **SMMLV** — *Salario Mínimo Mensual Legal Vigente*. Colombian minimum monthly wage. Some thresholds (especially labor) are SMMLV-indexed instead of UVT-indexed.
- **IPC** — *Índice de Precios al Consumidor*. CPI. A few legal thresholds adjust by IPC.
- **vigente / derogado / suspendido** — current / repealed / suspended. Articles can be in any state.
- **régimen de transición** — transition regime. When a law changes, articles in the previous regime stay applicable to taxpayers who began under it. Common pattern: "pérdidas pre-2017 keep the previous treatment per art. 290 ET (Ley 1819/2016 transition)."
- **TTD** — *Tasa Tributaria Depurada*. Effective tax rate computation. If TTD < 15%, the taxpayer must liquidate Impuesto a Adicionar.
- **IA** — *Impuesto a Adicionar*. The minimum-tax-style addition that brings TTD up to 15%.
- **INR** — *Impuesto Neto de Renta*. Net income tax (after credits, before retentions).
- **RLG** — *Renta Líquida Gravable*. Taxable income.
- **PN / PJ** — *Persona Natural / Persona Jurídica*. Individual / legal entity.
- **SAS** — *Sociedad por Acciones Simplificada*. The most common Colombian PYME entity type.
- **ZOMAC / ZESE / Zonas Francas** — special tax zones (ZOMAC = post-conflict; ZESE = special economic zones; Zonas Francas = free-trade zones). Articles often have explicit exclusions for these.
- **Concepto DIAN** — non-binding interpretive opinion from DIAN. Sometimes suspended by the Consejo de Estado.
- **Consejo de Estado** — top administrative court. Can suspend or annul DIAN concepts and Decretos.
- **Sentencia C-/T-/SU-** — Constitutional Court rulings. Can declare laws or articles unconstitutional.

**Project-specific terms:**
- **`pipeline_d`** — the served runtime (current generation). `pipeline_c` is the legacy generation, kept wired for contracts; do not edit unless coordinating with the surface owner.
- **`main chat`, `Normativa`, `Interpretación`** — three distinct UX surfaces with parallel orchestration / synthesis / assembly modules. Don't route requirements across them.
- **`graph_native` / `graph_native_partial` / `topic_safety_abstention`** — the three `answer_mode` values returned by the chat endpoint. `graph_native` = full coverage, `graph_native_partial` = coverage with at least one sub-question unanswered, `topic_safety_abstention` = honest refusal.
- **Coherence gate (Cases A/B/C)** — the post-retrieval gate that catches contamination. Case A = primary articles off-topic; Case B = chunks off-topic; Case C = zero evidence. See `docs/orchestration/coherence-gate-runbook.md`.
- **`router_topic` vs `effective_topic`** — what the router classified vs what the retriever actually retrieved against. Divergence is `served_off_topic` in the §1.G rubric.
- **TEMA-first retrieval** — the query strategy that anchors retrieval on the topic's representative articles before broader hybrid search. Toggled by `LIA_TEMA_FIRST_RETRIEVAL`; default `on` since v5 §1.D.
- **Six-gate lifecycle** — see `docs/aa_next/README.md`. Mandatory for every pipeline change.
- **Status emoji convention** — 💡 idea / 🛠 code landed / 🧪 verified locally / ✅ verified in target env / ↩ regressed-discarded.

---

## §14. First-day playbook for a fresh engineer / LLM

If you are starting on this fix plan with zero context, follow this exact sequence.

**Hour 1 — orient**
1. Read `CLAUDE.md` end-to-end (~15 min).
2. Read `docs/re-engineer/exec_summary_v1.md` (~5 min — the founder's view of why this exists).
3. Read `docs/re-engineer/makeorbreak_v1.md §0` ("what happened with vigencia in the graph") + §2 ("five structural defects") (~15 min).
4. Read this document's §0–§0.6 (~10 min).
5. Skim `docs/orchestration/orchestration.md` (just the table of contents + the env matrix at the bottom) (~10 min).

**Hour 2 — hands on, low-risk**
1. Run `make supabase-start && make supabase-status` to bring up local Supabase.
2. Run `npm run dev:check` to verify the launcher preflight passes.
3. Run `PYTHONPATH=src:. uv run pytest tests/test_phase1_runtime_seams.py -q` — should pass; this validates your environment.
4. Open `evals/sme_validation_v1/runs/20260427T003848Z/verbatim.md` and read 5 of the 36 verbatim answers. This is the ground truth your fix has to improve.

**Hour 3 — locate your fix's anchor files**
1. Find your assigned Sub-fix's "Files — Read first" list in §2-§7 above.
2. Open each file. Read enough to orient.
3. Sketch your plan against the gate-1 + gate-2 template in `docs/aa_next/README.md` (idea + plan + measurable success criterion + test plan + greenlight + refine-or-discard).
4. Push the gate-1 + gate-2 sketch to your tech lead for sign-off BEFORE writing any code.

**Day 2 onwards — the discipline**
- Every code change: update the relevant runbook in the same PR (`docs/orchestration/{retrieval,coherence-gate}-runbook.md`).
- Every `LIA_*` flag or migration: bump `docs/orchestration/orchestration.md` env matrix + add a change-log row.
- Every ship: produce gate-3 numeric evidence (not just unit tests) before marking 🧪.
- Every ship: produce gate-5 target-env evidence (re-run §1.G subset, golden suite, or named live measurement) before marking ✅.
- Every status report to operator: Bogotá AM/PM time format, plain language, end with a concrete next-step suggestion.

**When you hit something this document doesn't cover**
- Convention question → `CLAUDE.md` first, then `AGENTS.md`.
- Architecture question → `docs/orchestration/orchestration.md` first, then the relevant runbook.
- Failure-mode question → `docs/orchestration/coherence-gate-runbook.md` for refusals, `docs/orchestration/retrieval-runbook.md` for retrieval issues.
- Lessons from past incidents → `docs/learnings/{retrieval,ingestion,process}/`. Search before you re-invent.
- This document is wrong / incomplete → submit a PR adding the section. Don't work around the gap silently.

---

*v1, drafted 2026-04-26 evening immediately after `makeorbreak_v1.md`. Upgraded same evening with §0.5 / §0.6 / per-sub-fix file inventories / §13 glossary / §14 playbook to be self-sufficient for a zero-context engineer or LLM. Open for amendment by any team member; amend by adding numbered sub-sections rather than overwriting.*
