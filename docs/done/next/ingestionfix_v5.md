# ingestionfix_v5 — Retrieval-graph integration (make the taxonomy actually steer answers)

Forward-looking plan after `ingestionfix_v4` landed the Falkor graph structure (1,943 TEMA edges, 41 TopicNodes, 84 SubTopicNodes). The graph now exists but the hot path barely reads it. v5 wires retrieval to use the graph so end-user answers reflect the taxonomy work.

Also covers **F11** (classifier taxonomy-awareness for the 26 new sector topics) because unblocking sectors is a prerequisite for (a)–(d) paying off.

**Read order for a cold LLM**: §0 → §1 → §2 → §5 (phases in order). §8 is the live state ledger.

---

## §0 Cold-Start Briefing

### 0.1 What Lia_Graph is
Graph-native RAG shell for Colombian accounting/legal content. Served runtime in `src/lia_graph/pipeline_d/`. Two retrieval halves: chunk search in Supabase + graph traversal in FalkorDB.

### 0.2 What v4 delivered
- Prose-only docs become ArticleNodes (relaxed schema + `_graph_article_key`).
- Batches 2-8 ingested through the fixed loader.
- **Falkor post-v4**: ArticleNode 8746, TopicNode 41, TEMA 1,943, HAS_SUBTOPIC 339, PRACTICA_DE 0.
- 25 of 26 new sector TopicNodes still empty because the Gemini classifier doesn't know them (F11).

### 0.3 Why v5 exists
Three concrete signals during v4 showed the graph isn't feeding retrieval:

1. `topic_router` log spam: `topic 'sector_educacion' has no registered keywords — queries in this domain will fall through to fallback routing`. User queries about those topics won't hit the right TopicNode.
2. `src/lia_graph/pipeline_d/retriever_falkor.py` Cypher matches articles by `article_number`, not by starting at a TopicNode and fanning out via TEMA. TEMA edges are decorative until this changes.
3. `SubTopicNode` + `HAS_SUBTOPIC` exist but no consumer reads them — 84 nodes + 339 edges with no downstream user.

### 0.4 Scope guardrails
- **No change to Supabase chunk-level retrieval.** Hybrid search stays as-is.
- **No change to answer tone/organization.** This is a retrieval-only pass; `answer_synthesis.py` / `answer_assembly.py` gain at most a new citation property (topic tag).
- **No new ingestion paths.** v5 consumes the graph v4 produced.
- **Feature-flag every new Cypher path.** Old retrieval stays as fallback until operator validates.

### 0.5 Non-negotiables
- `docs/orchestration/orchestration.md` env matrix gets bumped for any new `LIA_*` flag (per CLAUDE.md rule).
- Retriever changes land behind `LIA_TEMA_FIRST_RETRIEVAL=on|off` (default off → on after ±2 hours of shadow metrics).
- Every new Cypher query passes the `test_retriever_cloud_contracts.py` schema-whitelist gate.
- Keep `main chat`, `Normativa`, `Interpretación` surface boundaries intact — don't fold.

### 0.6 Glossary

| Term | Meaning |
|---|---|
| **Topic routing** | The classifier that reads a user query and decides which `topic_key` it belongs to. Today's router is keyword-based and misses new topics. |
| **TEMA-first retrieval** | A new Cypher path: start at `TopicNode` → traverse `<-[:TEMA]-` to candidate articles → filter by chunk relevance. Scopes the candidate set cleanly. |
| **Subtopic drill-down** | Finer grain: when query matches a SubTopicNode, prefer articles with `HAS_SUBTOPIC` edges to that node over siblings. |
| **Taxonomy tag** | A `{topic_key, topic_label, subtopic_key?}` object attached to each citation in the synthesized answer. Enables future UX (badge the answer by topic). |

---

## §1 Prior work — what v4 left for v5

### 1.1 Outstanding from v4
- **F11** — classifier not taxonomy-aware for 26 new sectors. Blocks sectors populating in Falkor.
- **F8** — cross-doc numbered-article key collision (Article 5 of Ley 100 vs Ley 300). v4 preserved this to avoid orphaning 8,106 nodes; v5 will not touch it either. Carry-forward.
- **F9** — 6,805 ArticleNodes still lack TEMA edges. Future cleanup.
- **F10** — `run_topic_backfill_chain.sh` skeleton. Not needed for v5 (no batch work).
- **F12** — G2 validator semantics. Cosmetic; defer.

### 1.2 What Falkor currently has

```
ArticleNode          8746
TopicNode              41
SubTopicNode           84
TEMA edges          1,943
HAS_SUBTOPIC          339
PRACTICA_DE             0
Article without TEMA 6,805
```

### 1.3 What retrieval currently does (condensed)
`retriever_falkor.py` fan-out per user query:
1. Classify query → topic_key (via `topic_router`)
2. Pull seeded article anchors from the chunk-level hybrid search
3. Cypher `MATCH (n:ArticleNode {article_number: key})` to fetch each anchor's graph context
4. Second hop: `MATCH (seed)-[rel]-(other:ArticleNode)` to add connected articles
5. Return result set to synthesizer

**Gap:** the topic_key from step 1 is used only to color diagnostics. Step 3 is anchored on article_number, not topic. Step 4 traverses ANY edge, not TEMA specifically. The graph's topical shape is invisible to retrieval.

---

## §2 Problem summary (TL;DR)

**Goal.** Make the taxonomy drive retrieval. User query about "educación" should route to `sector_educacion` TopicNode and pull articles with TEMA edges to it — not miss because the router has no keyword for that topic and the retriever never looks.

**Four gaps (a–d from the session discussion):**

| Gap | File(s) | Rough effort |
|---|---|---|
| (a) topic_router deaf to new topics | `src/lia_graph/topic_router.py` (+ its config source) | ~1 hr |
| (b) Retriever doesn't traverse TEMA edges | `src/lia_graph/pipeline_d/retriever_falkor.py` | ~3-4 hr |
| (c) SubTopicNodes unused | `retriever_falkor.py` + `planner.py` | ~3-4 hr |
| (d) Answers don't surface taxonomy tag | `answer_synthesis.py` / `answer_inline_anchors.py` | ~2 hr |

Plus **F11** (classifier taxonomy-awareness) — ~2-3 hr. Not strictly a retrieval change, but without it the 25 empty sectors stay empty and gaps (b)/(c)/(d) don't show their value for sector queries.

**Explicitly out of scope:**
- Rewriting the query-classifier (topic_router is keyword-based today; swapping in a semantic classifier is F13, not v5).
- Retiring orphan ArticleNodes (F9).
- Reworking chunk-level hybrid search.
- Changing answer tone or section structure.

---

## §3 Scope + phasing

Five phases. F11 first because it's a prerequisite for testing sector-path behavior end-to-end.

| Phase | Purpose | Effort | Wall | Blocks |
|---|---|---|---|---|
| 1 | F11 — classifier taxonomy-awareness; re-populate sector TopicNodes | ~2-3 hr eng + ~30 min bust/ingest | ~3.5 hr | Phase 4 end-to-end validation |
| 2 | topic_router keywords for all 65 top-level topics | ~1 hr | ~1 hr | Phase 3 |
| 3 | TEMA-first retrieval behind `LIA_TEMA_FIRST_RETRIEVAL=on` | ~4 hr | ~4 hr | Phase 5 |
| 4 | SubTopicNode drill-down | ~3 hr | ~3 hr | Phase 5 |
| 5 | Taxonomy tags in citations + manual retrieval QA | ~2 hr | ~2 hr | v5 close-out |

Total: ~13 hr engineering over ~14 hr wall.

---

## §4 Pre-flight checklist

- [ ] `git status` clean on a fresh v5 branch: `feat/ingestionfix-v5-retrieval-graph`
- [ ] v4 PR merged (or at minimum v4 branch's commits available as the base)
- [ ] `.env.staging` sourceable
- [ ] Falkor reachable: `PYTHONPATH=src:. uv run python -c "from lia_graph.graph.client import GraphClient; print(GraphClient.from_env().redacted_url)"`
- [ ] Current Falkor TopicNode + TEMA snapshot captured to `artifacts/graph_state_v5_start.json` (for delta comparison at close-out)
- [ ] `test_retriever_cloud_contracts.py` + `test_retriever_falkor.py` green on branch base

---

## §5 Phases

### Phase 1 — F11: classifier taxonomy-awareness

**Goal.** Make the Gemini classifier pick new sector topics on re-ingest so the 25 empty TopicNodes populate.

#### Phase 1 — Files to inspect
- `src/lia_graph/ingest_classifiers.py` — builds classifier prompt + topic list
- `src/lia_graph/subtopic_taxonomy_loader.py` — taxonomy loader
- `src/lia_graph/ingest_subtopic_pass.py` — batched classifier pass

#### Phase 1 — Files to modify
| Path | Change |
|---|---|
| `config/prefix_parent_topic_map.json` | Add path-prefix rules that auto-route common sector patterns (e.g. `CORE…/SALUD/` → `sector_salud`) so obvious cases skip the LLM. |
| `src/lia_graph/ingest_classifiers.py` | If the classifier prompt pulls topic list from `topic_taxonomy.json` iteratively, no change needed — confirm with a dry classify. If it hardcodes the 39 pre-v3 topics, wire in the 26 sectors (pull from taxonomy loader). |
| `config/topic_taxonomy.json` | Potentially enrich sector entries' `ingestion_aliases` to include Spanish-phrase hints the classifier can surface in its prompt output (e.g. `sector_salud`: add `"ley de salud"`, `"sistema de seguridad social en salud"`). |

#### Phase 1 — Files to create
| Path | Purpose |
|---|---|
| `tests/test_classifier_new_sectors.py` | ~6 unit tests feeding known sector titles (Ley 1098 / infancia, Ley 1122 / salud, Ley 142 / servicios públicos) and asserting the classifier returns the right `sector_*` key rather than `otros_sectoriales`. |

#### Phase 1 — Run
```bash
# after code changes
PYTHONPATH=src:. uv run pytest tests/test_classifier_new_sectors.py -v

# re-run Task E to restore Supabase tema for the 432 docs (they reverted to otros_sectoriales during v4 Phase 3)
set -a; source .env.staging; set +a
PYTHONPATH=src:. uv run python scripts/monitoring/monitor_sector_reclassification/apply_sector_reclassification.py \
  --approved artifacts/sector_classification/sector_reclassification_proposal.approved.json \
  --confirm

# bust + re-ingest the 26 sector topics (classifier now knows them → docs stay put this time)
TOPICS="sector_agropecuario,sector_salud,sector_financiero,sector_vivienda,sector_cultura,sector_administracion_publica,sector_profesiones_liberales,sector_educacion,sector_turismo,sector_inclusion_social,sector_servicios,sector_justicia,sector_energia_mineria,sector_politico,sector_deporte,sector_desarrollo_regional,sector_ciencia,sector_infancia,sector_juegos_azar,sector_economia,sector_transporte,sector_emprendimiento,sector_medio_ambiente,sector_puertos,sector_comercio_internacional,sector_telecomunicaciones"
PYTHONPATH=src:. uv run python scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py \
  --topics "$TOPICS" --target production --confirm --force-multi --tag v5_sectors

# detached additive ingest (same pattern as v4 Phase 4)
bash scripts/launch_batch.sh --topics "$TOPICS"
# or use the sector batches 9/10/11 in plan.json
```

#### Phase 1 — Acceptance
1. `test_classifier_new_sectors.py` green.
2. Post-ingest Falkor shows **TopicNode count ≥ 65** (39 pre-v3 + 26 sectors + any subtopic parents).
3. TEMA edges rise by **~300–500** (rough estimate from §2.2.6 sector doc counts).
4. Supabase `documents.tema` sector_* rows ≥ 320 (post-migration, not reverted).

#### Phase 1 — State log
```yaml
phase_1_f11_classifier:
  status: pending
  started_at:
  completed_at:
  branch:
  tests_passing:
  falkor_topic_count_after:
  falkor_tema_count_after:
  supabase_sector_tema_count:
  notes:
```

---

### Phase 2 — topic_router keywords

**Goal.** Kill the "no registered keywords" log spam by wiring keyword registrations for every top-level topic in `topic_taxonomy.json` (65 after v3). User queries routing improves immediately.

#### Phase 2 — Files to inspect
- `src/lia_graph/topic_router.py` — routing logic + keyword table
- Wherever its keyword table is defined (may be a config JSON or inline dict)

#### Phase 2 — Files to modify
| Path | Change |
|---|---|
| `src/lia_graph/topic_router.py` OR `config/<router-config>.json` | For each of 65 top-level topics, add a keyword list. Start from taxonomy `ingestion_aliases` as a seed. |

#### Phase 2 — Files to create
- `tests/test_topic_router_coverage.py` — one test per taxonomy top-level key asserting a representative Spanish phrase routes to it (parameterize).

#### Phase 2 — Run
```bash
PYTHONPATH=src:. uv run pytest tests/test_topic_router_coverage.py -v

# Probe: grep launch logs for remaining "no registered keywords" warnings
grep "no registered keywords" logs/launch-batch-*.log
# Expected: 0 matches on any post-v5 ingest.
```

#### Phase 2 — Acceptance
1. Every taxonomy top-level key has ≥3 keyword entries.
2. Parameterized test green for all 65.
3. Next ingest launch log shows zero "no registered keywords" warnings.

---

### Phase 3 — TEMA-first retrieval (feature-flagged)

**Goal.** New Cypher path: given a routed `topic_key`, start at `TopicNode` and fan out to candidate articles via `<-[:TEMA]-`. This makes the 1,943 TEMA edges actually steer retrieval.

#### Phase 3 — Design

New flag: `LIA_TEMA_FIRST_RETRIEVAL` (off | shadow | on). Default off.

- **off**: current behavior (article_number lookup + ANY-edge traversal). Baseline.
- **shadow**: run BOTH paths, return old path's result, log both result sets to `logs/events.jsonl` as `retrieval.tema_first_shadow` for ~2 hours of real traffic comparison.
- **on**: return TEMA-first result. Old path stays as fallback if TEMA-first returns empty.

New Cypher:
```cypher
MATCH (t:TopicNode {topic_key: $topic_key})<-[:TEMA]-(a:ArticleNode)
WHERE a.status = 'vigente'
RETURN a.article_id AS article_key,
       a.heading AS heading,
       a.text_current AS text_current,
       a.article_number AS article_number,
       a.is_prose_only AS is_prose_only,
       a.source_path AS source_path
LIMIT $limit
```

#### Phase 3 — Files to modify
| Path | Change |
|---|---|
| `src/lia_graph/pipeline_d/retriever_falkor.py` | Add `tema_first_match()` helper + flag dispatch. Emit `retrieval.tema_first.returned` event with node count. |
| `src/lia_graph/pipeline_d/orchestrator.py` | Read `LIA_TEMA_FIRST_RETRIEVAL` and pass into retriever. |
| `scripts/dev-launcher.mjs` | Default `LIA_TEMA_FIRST_RETRIEVAL=shadow` in dev/staging; flipped to `on` after shadow review (beta risk-forward memo). |
| `docs/orchestration/orchestration.md` env matrix | Bump version + add row. |
| `docs/guide/env_guide.md` env matrix mirror | Mirror. |
| `CLAUDE.md` env matrix mirror | Mirror. |
| `frontend/src/app/orchestration/shell.ts` + `frontend/src/features/orchestration/orchestrationApp.ts` | Add the flag to the /orchestration HTML map status card. |

#### Phase 3 — Files to create
| Path | Purpose |
|---|---|
| `tests/test_retriever_falkor_tema_first.py` | ~8 cases: topic found in Falkor returns articles; topic not found returns empty; is_prose_only flag flows through; limit respected; retired articles excluded; shadow mode returns old path's result. |

#### Phase 3 — Acceptance
1. New tests green.
2. `retriever_cloud_contracts` still green (new Cypher uses only schema-declared properties).
3. Shadow-mode event counts show new path returns > 0 articles for at least 20 of 65 routed topics in a 30-min sample.
4. When flipped on for a laboral query, returned article set grows vs baseline (more TEMA-linked articles in scope).

---

### Phase 4 — SubTopicNode drill-down

**Goal.** Use HAS_SUBTOPIC edges to prefer articles that share the user's subtopic (finer grain than topic).

#### Phase 4 — Design
- Extend query classification to output `(topic_key, subtopic_key?)` tuple when the subtopic is inferrable.
- Cypher:
```cypher
MATCH (st:SubTopicNode {sub_topic_key: $subtopic_key})-[:HAS_SUBTOPIC]-(a:ArticleNode)
RETURN ...
UNION
MATCH (t:TopicNode {topic_key: $topic_key})<-[:TEMA]-(a:ArticleNode)
WHERE NOT (a)-[:HAS_SUBTOPIC]->(:SubTopicNode {sub_topic_key: $subtopic_key})
RETURN ...
```
Returns subtopic-matched articles first, then topic-matched articles without that subtopic.

#### Phase 4 — Files to modify
| Path | Change |
|---|---|
| `src/lia_graph/pipeline_d/retriever_falkor.py` | Add `tema_plus_subtopic_match()`. |
| `src/lia_graph/pipeline_d/planner.py` | Extract subtopic signal from query classification output. |

#### Phase 4 — Files to create
| Path | Purpose |
|---|---|
| `tests/test_retriever_falkor_subtopic.py` | ~5 cases covering subtopic match vs no subtopic match, ranking order, flag-off bypass. |

#### Phase 4 — Acceptance
1. Tests green.
2. For a query like "liquidación de cesantías en 2026" (subtopic `cesantias_intereses`, topic `laboral`), returned article order shows cesantias-tagged articles first.

---

### Phase 5 — Taxonomy tags in citations + retrieval QA

**Goal.** Each cited chunk in the synthesized answer carries its `topic_key` / `topic_label` so future UX (badges, filter chips) has the data to show. Also runs the manual retrieval QA that closes v5.

#### Phase 5 — Files to modify
| Path | Change |
|---|---|
| `src/lia_graph/pipeline_d/answer_inline_anchors.py` | Extend the anchor object with `topic_key` + `topic_label` pulled from the retrieved ArticleNode's TopicNode. |
| `src/lia_graph/pipeline_d/answer_synthesis.py` (facade) | No logic change — just ensure citations pass through anchor metadata unchanged. |

#### Phase 5 — Files to create
| Path | Purpose |
|---|---|
| `tests/test_answer_inline_anchors_topic_tag.py` | Assert the new fields are present and non-empty when available; tolerant of `None` for legacy-path docs. |

#### Phase 5 — Manual QA (operator)
```bash
npm run dev:staging   # → http://localhost:3000
# Ask 5 reference questions, one per bucket:
#  1. laboral: "¿cómo se liquidan las cesantías?"
#  2. tax:     "¿cuándo vence la declaración de renta 2026?"
#  3. sector:  "¿qué dice la Ley 1098 sobre el código de infancia?"
#  4. edge:    "¿Ley 142 servicios públicos domiciliarios?"
#  5. miss:    "¿cómo se calcula un crédito hipotecario?"  (expected: topic_router still routes; answer may be light)
# Confirm each answer shows a topic tag on at least one citation + no console errors.
```

#### Phase 5 — Acceptance
1. New tests green.
2. All 5 manual queries return answers with ≥1 topic-tagged citation.
3. Falkor TEMA traversal is the dominant retrieval path (verify via `retrieval.tema_first.returned` event count in a 30-min sample ≥ 80% of queries).
4. No regression in `npm run test:health:fast`.

---

## §6 End-to-end execution recipe

```bash
git checkout -b feat/ingestionfix-v5-retrieval-graph

# Phase 1 — F11 classifier
# edit config/prefix_parent_topic_map.json + (if needed) ingest_classifiers.py
PYTHONPATH=src:. uv run pytest tests/test_classifier_new_sectors.py -v
set -a; source .env.staging; set +a
PYTHONPATH=src:. uv run python scripts/monitoring/monitor_sector_reclassification/apply_sector_reclassification.py \
  --approved artifacts/sector_classification/sector_reclassification_proposal.approved.json --confirm
PYTHONPATH=src:. uv run python scripts/monitoring/monitor_ingest_topic_batches/fingerprint_bust.py \
  --topics "<26 sectors>" --target production --confirm --force-multi --tag v5_sectors
bash scripts/launch_batch.sh --topics "<26 sectors>"   # detached; heartbeat cron
# wait for cli.done; validate Falkor TopicNode + TEMA bumps

git commit -am "feat(ingestionfix-v5-phase-1): classifier taxonomy-aware; 26 sectors populate"

# Phase 2 — topic_router
# edit topic_router.py / config
PYTHONPATH=src:. uv run pytest tests/test_topic_router_coverage.py -v
git commit -am "feat(ingestionfix-v5-phase-2): topic_router keywords for 65 top-level topics"

# Phase 3 — TEMA-first retrieval
# edit retriever_falkor.py + orchestrator.py + env matrix mirrors
PYTHONPATH=src:. uv run pytest tests/test_retriever_falkor_tema_first.py tests/test_retriever_cloud_contracts.py -v
# flip LIA_TEMA_FIRST_RETRIEVAL=shadow in dev-launcher
# run npm run dev:staging; send a few queries; grep logs/events.jsonl for retrieval.tema_first_shadow
# flip to on
git commit -am "feat(ingestionfix-v5-phase-3): TEMA-first retrieval behind LIA_TEMA_FIRST_RETRIEVAL"

# Phase 4 — SubTopicNode drill-down
# edit retriever_falkor.py + planner.py
PYTHONPATH=src:. uv run pytest tests/test_retriever_falkor_subtopic.py -v
git commit -am "feat(ingestionfix-v5-phase-4): SubTopicNode drill-down"

# Phase 5 — taxonomy tags + manual QA
# edit answer_inline_anchors.py
PYTHONPATH=src:. uv run pytest tests/test_answer_inline_anchors_topic_tag.py -v
# operator runs the 5-query sweep in staging
git commit -am "feat(ingestionfix-v5-phase-5): topic tag on citations; retrieval QA green"

# Close-out
$EDITOR docs/next/ingestionfix_v5.md   # bump plan_version, stamp closed_out_at
```

---

## §7 Rollback + recovery

- **Phase 1** classifier regression — revert the classifier prompt changes; sectors remain empty; sector queries fall back to otros_sectoriales (pre-v5 baseline). No data loss.
- **Phase 3** TEMA-first breaks a query class — flip `LIA_TEMA_FIRST_RETRIEVAL=off`; old path resumes instantly. Shadow-mode data preserved for debugging.
- **Phase 4** subtopic drill-down — unset the subtopic signal in the planner; Cypher UNION degrades to the Phase 3 TEMA-first path.
- **Phase 5** citation tag bug — anchors are additive properties, consumers that don't read them ignore them. Revert is a property removal.

Any Falkor corruption → re-bust affected topics via `launch_batch.sh` (v4 durability contract unchanged).

---

## §8 Global state ledger

```yaml
plan_version: 5.0
plan_last_updated:
plan_supersedes: none  # v5 is additive to v4
plan_signed_off_by:
plan_signed_off_at:

inherits_from_v4:
  shipped:
    - Prose-only ArticleNode eligibility
    - _graph_article_key helper
    - Batches 2-8 ingested (Falkor TEMA 10 → 1943)
  outstanding:
    - F8 cross-doc numbered-article collision (preserved)
    - F9 retire 8074 orphan ArticleNodes (deferred)
    - F11 classifier taxonomy-awareness (v5 Phase 1)

phase_1_f11_classifier:
  status: pending
  started_at:
  completed_at:
  tests_passing:
  falkor_topic_count_after:
  falkor_tema_count_after:
  supabase_sector_tema_count:
  notes:

phase_2_topic_router:
  status: pending
  started_at:
  completed_at:
  tests_passing:
  remaining_no_keyword_warnings:
  notes:

phase_3_tema_first_retrieval:
  status: pending
  started_at:
  completed_at:
  env_flag_state:           # off | shadow | on
  shadow_sample_minutes:
  tema_first_coverage_ratio:
  tests_passing:
  notes:

phase_4_subtopic_drilldown:
  status: pending
  tests_passing:
  notes:

phase_5_citation_tags_and_qa:
  status: pending
  manual_qa_completed_at:
  manual_qa_findings:
  notes:

followups_for_later:
  - id: F13
    source: v5 §2
    description: >
      topic_router is keyword-based. A semantic-embedding classifier would
      route more reliably for paraphrased queries. Separate project.
  - id: F14
    source: v5 §5 Phase 5
    description: >
      Frontend UX for topic badges on citations. Backend data shipped in
      v5; UI surfacing is a follow-on FE ticket.
  - id: F15
    source: v5 Phase 1 production validation
    description: >
      F11 sink-side preservation correctly rewrites `documents.tema` on
      classifier catch-all regression (430 preserves fired on 2026-04-24
      re-ingest; 322 sector docs in Supabase). But the Falkor loader path
      reads `document.topic_key` — the raw classifier output — for
      `article_topics` map construction in `ingest.py:359` and
      `delta_runtime.py:490`. So Falkor still emits TEMA edges to
      `otros_sectoriales` for sector-preserved docs. Fix: apply the
      same preservation pre-Falkor (pass the resolved tema into
      CorpusDocument.topic_key before calling `build_graph_load_plan`),
      OR have the loader read `topic_key` from the sink's preserved
      value (it can consult `_topic_by_doc_id` after sink completes).
      Cheapest path: after `write_documents` returns, mutate each
      CorpusDocument's topic_key to whatever the sink actually wrote.
      Expected delta on next re-run: Falkor TopicNode 41 → 65+,
      sector TEMA edges 65 → ~300+.
```

---

## §9 Carry-forward learnings from v4

1. **Check the hot path, not just the cold one.** v4 built graph structure; no one asked whether retrieval used it. Always trace one user query end-to-end when claiming a feature "ships."
2. **Feature-flag new Cypher paths.** The chain-run httpx timeout showed a single bad call can wedge a 30-min run. Shadow mode + fallback keeps production safe.
3. **Batch PostgREST `.in_()`.** ~200 keys is the URL ceiling. Assume all new consumer queries will hit it and pre-chunk.
4. **Taxonomy-prompt wiring matters.** Adding topics to taxonomy.json isn't enough; wherever the LLM builds its decision space from that config has to get the update too.
5. **Bogotá AM/PM** for user-facing times. Machine logs stay UTC ISO.

---

## §10 Operator cheat-sheet

```bash
# v5 Phase 1 — F11
# code + test the classifier
# run Task E + sector bust/ingest
# watch TopicNode + TEMA rise

# v5 Phase 3 — TEMA-first
# flip LIA_TEMA_FIRST_RETRIEVAL=shadow
# npm run dev:staging → send queries
# check logs/events.jsonl for retrieval.tema_first_shadow
# flip to on once shadow parity looks right

# v5 Phase 5 — retrieval QA
npm run dev:staging
# send 5 reference queries; confirm tag + no console errors
```

---

## §11 Connections to adjacent work

- **v4 graph structure** — the foundation. v5 consumes what v4 produced.
- **v3 Phase 2.5 taxonomy** — v5 Phase 1 fixes the classifier gap that made Phase 2.5 revert during v4.
- **`answer_synthesis.py` / `answer_assembly.py` facades** — v5 Phase 5 adds a field; those facades stay the stable boundary.
- **`orchestration.md` env matrix** — bumped in Phase 3 for `LIA_TEMA_FIRST_RETRIEVAL`.
- **F13** (semantic query classifier) — v5 is keyword-based routing; semantic routing is the natural next step.

---

*End of document. Proceed: Phase 1 is local + one production write pass.*
