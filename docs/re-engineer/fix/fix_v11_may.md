## fix_v11_may.md — close the Phase 10C 57 % → 70 % gap and finish promoting the Interpretación de Expertos panel

> **Drafted 2026-05-11 PM Bogotá** by claude-opus-4-7 at the close
> of the long v10 session that landed Phase 10A (chunk-class
> keystone, cloud backfill, byte-identical-to-baseline §1.G SME
> panel), Phase 10B (Supabase-routed expert panel, 43 % accept@top3
> on the new 21-Q mini-panel), and Phase 10C v0 (anchor-boost +
> article→doc index, **57.1 % accept@top3**). v11 is the closing
> two-phase plan that gets the panel past the §5.4 70 % production
> ship bar and retires the filesystem catalog.
>
> **Audience.** Zero-context fresh LLM or engineer. Self-contained.
> Skim `fix_v10_may.md §4.A` for the chunk-class keystone, §3.B
> for the retriever contract, §4.C for the original 10C scope.
>
> **What this is.** Two phases of focused refinement (11A → 11B)
> that take the mini-panel from 57 % to ≥ 70 % and then re-validate
> 10D (retire filesystem catalog). Each phase carries the six-gate
> lifecycle entry per `docs/aa_next/README.md` policy.
>
> **What this is not.** Not a re-design — 10C's architecture is
> right; 11A is parameter tuning on it and 11B is moving the same
> index out of Python memory into FalkorDB. Not a content
> authoring exercise. Not a backwards step on the §1.G chat panel
> (10A's byte-identical-to-baseline result stays the regression
> floor).
>
> **Scope guard.** Closing bar at the end of phase 11B:
> (a) the 21-Q expert-panel mini-panel returns ≥ 70 % accept@top3
> with **zero** SME `wrong` rulings on anchor-seeded cards;
> AND (b) the §1.G 36-Q chat panel still holds at-or-above the
> post-fix_v8f-temp0 baseline (34/36 acc+);
> AND (c) production `LIA_INTERPRETATION_SOURCE` flips from
> `filesystem` back to `supabase` (the launcher's `production`
> default was set to `filesystem` at the v11 starting point — see
> §5.3 below).

---

## 0. Inheritance from fix_v1..fix_v10 + the v11 starting state

Everything in `fix_v10_may.md §0` carries forward unchanged.
Additional invariants this doc commits to:

- **Phase 10A is production.** `supabase_sink.write_chunks` inherits
  `knowledge_class` from the parent doc; 2,275 cloud chunks are
  correctly retagged; G1/G2/G3 guardrails prevent drift. The cloud
  Supabase migration for `documents.provider_labels (text[])`
  (20260513000000) is applied to both local + cloud.
- **Phase 10B + Phase 10C v0 code is shipped but NOT enabled in
  production.** The `LIA_INTERPRETATION_SOURCE` launcher default
  for `production` mode is `filesystem` (the safety floor). The
  `dev:staging` default stays `supabase` so refinement still
  measures against the cloud path. Operator flips production when
  the §5.4 70 % bar clears.
- **The 21-Q mini-panel
  (`evals/sme_validation_v1/questions_expert_panel_v1.jsonl`) and
  the scorer (`scripts/eval/score_expert_panel_mini.py`) are the
  measurement instruments.** v11 phases re-use the same 21
  questions; comparable across phases. Per
  `feedback_sme_panel_explicit_request_only`, every mini-panel run
  is operator-authorized.
- **Graph schema scaffold for `InterpretationNode` + `INTERPRETS` +
  `COVERS_TOPIC` already landed in `graph/schema.py`.** Phase 11B
  ships the loader against that scaffold — no schema additions.

---

## 1. v10 score trajectory + diagnosis (verified 2026-05-11 PM)

The 21-Q mini-panel was scored five times across the v10 session
against the same chat-response set
(`evals/sme_validation_v1/runs/20260511T195358Z_phase10b_expert_panel_v1/`).
Each measurement isolates one architectural change:

| Stage | Accept@top3 | What changed |
|---|---|---|
| Phase 10B raw | 33 % | Supabase routing only — `filter_knowledge_class='interpretative_guidance'` + topic boost 1.5× |
| Phase 10B + §5.2 levers (a)+(b) | **43 %** | Topic boost 1.5 → 2.5; Python lexical re-rank `(1.0 + 0.25·hits)` on chunks mentioning article refs |
| Phase 10C v0 (hard filter — wrong sanitizer) | 9.5 % | _Bug_: `_sanitize_doc_id` regex stripped dashes/dots → cloud doc_ids never matched index entries → filter ate everything |
| Phase 10C v0 (hard filter — fixed sanitizer) | 28.6 % | Sanitizer matched cloud byte-for-byte; hard-filter regression confirmed — when the index lacks a cited article (e.g. `art_124_2`), filter drops the right doc anyway |
| **Phase 10C v0 (anchor BOOST + fixed sanitizer)** | **57.1 %** | ×4 multiplicative boost on `rrf_score` for chunks whose doc_id is in the index hit set; keep recall, surface index-hit docs |

**The 12 wins** at 57.1 %: `fe_cufe_contingencia`, `fe_nuevos_documentos_dav`,
`iva_exentos_vs_excluidos`, `iva_proporcionalidad_d1474`,
`laboral_reforma_2466`, `proc_devoluciones_riesgo_auditoria`,
`pt_paraisos_panama`, `renta_dividendos_242`, `renta_patrimonio_niif`,
`retencion_autorretencion_especial`, `retencion_decreto_572`,
`rst_elegibilidad_sectores`.

**The 9 misses** at 57.1 %: `gmf_exencion_350uvt`,
`iva_regimen_responsables`, `laboral_parafiscales_especiales`,
`laboral_ugpp_desalarizacion`, `pt_umbrales_pyme`,
`renta_beneficio_auditoria`, `renta_conciliacion_2516`,
`renta_deduccion_ica`, `renta_ttd_paragrafo6`.

### 1.A — Failure-cluster analysis

Forensic walk of the 9 misses suggests two distinct failure modes
that v11 phases 11A and 11B target separately:

**Cluster A — index-dilution** (5 of 9): the question cites a
"crowded" article whose index entry holds many docs, none clearly
dominant. Example: `renta_ttd_paragrafo6` cites Art. 240 ET, which
has **16 docs** in the article→doc index after full-markdown
extraction. The expected file (T-A-tasa-minima-tributacion-TTD) is
in the list but the ×4 boost is applied uniformly to all 16, so
the most-relevant doc isn't distinguishable from the noise. This
hits `gmf_exencion_350uvt` (Art. 115 has 3 docs, expected one is
GMF-E01 but it's tied with ICA-E01 and PARAFISCAL-E01),
`renta_beneficio_auditoria` (Art. 689-3 has 13 docs),
`renta_deduccion_ica` (Art. 115 again — same 3-doc tie),
`renta_conciliacion_2516` (Art. 240 again — 16-way tie).

**Cluster B — index-miss** (4 of 9): the question's expected doc
doesn't show up in the article→doc index at all. Reasons:
(i) the expected doc references the article by NUMBER but the
extractor regex missed the syntactic form;
(ii) the corpus uses a DIFFERENT article number than the question
(e.g., `pt_umbrales_pyme` expects PRT-E01 which references Art.
260-1/-2/-5, not the broader Art. 260 the planner extracts);
(iii) the expected doc is fundamentally topic-based, not
article-based (`laboral_parafiscales_especiales`,
`laboral_ugpp_desalarizacion`,
`renta_patrimonio_niif`'s second-choice T-J), and the planner's
article-ref extraction returns nothing useful.

### 1.B — Why Phase 11A (trust-tier) targets Cluster A

The §5.2 gate-6 ladder pre-defined three refinement levers; v10
landed (a) topic-boost-2.5 and (b) lexical-article-ref boost. Lever
(c) — **trust-tier prioritization** — was reserved for "after a+b
underperform". Trust-tier sorts a tied set: when 16 docs share an
Art. 240 anchor, the Crowe/EY/KPMG branded ones rank above
anonymous blog re-posts. Cluster A is exactly this — index hits
exist but are uniformly weighted; trust-tier breaks the tie.

### 1.C — Why Phase 11B (Falkor loader) targets Cluster B

The Python-side article→doc index built from full-markdown reading
caps at what `extract_article_refs(text)` can pull from inline
mentions. The chunk-level data in cloud Supabase has the same
issue: `concept_tags` carries reform/decreto refs but not always
article numbers in canonical form. Moving the index into Falkor
(via the v10.C schema scaffold already in `graph/schema.py`) opens
two doors:

1. **Loader-time extraction** can be richer than the
   request-path regex. It can run a bigger ML or LLM pass once,
   index the result, and serve it cheap forever.
2. **Cypher anchors travel with the planner.** The chat planner
   ALREADY resolves `primary_article_keys` per turn. With
   `INTERPRETS` edges in Falkor, the expert retriever can pull
   "anchored interpretations for these articles" with one Cypher
   call instead of relying on the question's word-shape.

---

## 2. Target architecture (v11 closing state)

### 2.A — Phase 11A: trust-tier prioritization (Cluster A fix)

Adds a per-doc `trust_tier` ranking signal to the retriever's
score. Source of truth for the tier:

- **High (`trust_tier=high`)**: docs whose `documents.authority`
  (already a first-class column) matches a curated allowlist of
  named professional firms — Crowe, EY, KPMG, Deloitte, PwC,
  Baker McKenzie, Garrigues, BDO, Phillippi, etc. Allowlist lives
  at `config/provider_trust_tiers.json` (new), maintained by hand.
- **Medium (`trust_tier=medium`)**: docs from secondary firms with
  professional brand recognition but smaller authority footprint
  (Crowe Latam regional offices, ContaPyme, Actualícese on staff
  authors, etc.).
- **Low (`trust_tier=low`)**: anonymous blog posts, advertorial
  content, Question-And-Answer transcripts of unclear provenance.

Existing data: every chunk row already carries a `trust_tier`
column (`pre-fix_v10` default was `medium`). For most interp
chunks today the value is `medium`. Phase 11A re-derives it from
the allowlist during a **lightweight UPDATE backfill** (similar
shape to Phase 10A's chunk-class backfill — operator-authorized,
~30 sec).

Retriever change in `interpretacion/retriever_supabase.py`:
- `_group_chunks_by_doc` accepts an optional `trust_tier_weight`
  parameter (default `0.30`).
- Score becomes `base * (1.0 + ref_boost·hits) * (1.0 + tier_weight·tier_bonus)`
  where `tier_bonus ∈ {2.0 (high), 1.0 (medium), 0.0 (low)}`.
- Effect on a 16-way Art. 240 tie: a high-tier Crowe doc gets
  ×1.6, a medium-tier one gets ×1.3, a low-tier one ×1.0. The
  high-tier card rises to top.

### 2.B — Phase 11B: Falkor loader for InterpretationNode (Cluster B fix)

The v10.C schema scaffold already declared `InterpretationNode`,
`INTERPRETS`, `COVERS_TOPIC`. v11.B writes the loader and switches
the retriever from Python-side index to Cypher anchors.

NEW module `src/lia_graph/graph/interpretation_loader.py`:
- Reads `artifacts/canonical_corpus_manifest.json` for
  `knowledge_class=interpretative_guidance` documents.
- For each doc, reads the full markdown (not the 12 KiB preview)
  and extracts articles via `extract_article_refs` AND a richer
  regex pass that also catches `parágrafo N del Art. M` /
  `numeral N del Art. M` / decree-introduced article references.
- For chunk-level enrichment, also queries cloud Supabase
  `document_chunks WHERE knowledge_class='interpretative_guidance'`
  to harvest `concept_tags` (which carry parser-extracted
  reform/article refs).
- Emits MERGE Cypher statements for `InterpretationNode` + every
  `INTERPRETS` edge + every `COVERS_TOPIC` edge via the existing
  `GraphClient.stage_node()` / `.stage_edge()` API
  (`graph/client.py:195+`).
- Idempotent on `(doc_id)` for nodes and on `(source_doc_id,
  target_article_key, relation)` for edges. Same staging pattern
  the article loader uses today.

Wired into `materialize_graph_artifacts` execution alongside
article + reform + concept + parameter loading. New runtime env
`LIA_INGEST_INTERPRETATION_NODES=enforce` defaults the loader on
across all three modes (consistent with the rest of the v10
risk-forward flag stance per memory
`project_beta_riskforward_flag_stance`); set to `off` to skip the
load for diagnostic purposes.

Planner change in `src/lia_graph/pipeline_d/planner.py`:
- When `primary_article_keys` is non-empty AND the chat path is
  about to compose a citation, emit a new planner anchor seed
  named `interpretation_anchor_doc_ids` populated by:
  ```cypher
  MATCH (a:ArticleNode {key:$art})<-[:INTERPRETS]-(i:InterpretationNode)
  RETURN i.doc_id ORDER BY i.trust_tier DESC LIMIT 8
  ```
  per article. Capped at 8 per article (rerank handles final
  ordering); capped at 24 total to keep the seed bounded.

Retriever change:
- `fetch_interpretation_candidates` accepts a new
  `planner_anchor_doc_ids: tuple[str, ...]` parameter.
- When provided, takes precedence over the Python-side
  `article_index.doc_ids_for_article_refs(article_refs)` lookup.
- The Python-side index becomes a fallback used only when the
  planner did not supply anchors (e.g., expert-panel API endpoint
  called directly without a chat anchor, or `LIA_INGEST_INTERPRETATION_NODES=off`).
- Same ×4 multiplicative boost behavior on top.

### 2.C — Phase 11C (closing): re-validate 10D + flip production

After 11A + 11B clear the §5.4 70 % ship bar in staging, **operator
authorizes the production flip**:
- `LIA_INTERPRETATION_SOURCE=supabase` for production mode in the
  launcher (revert v11.0 safety flip).
- 7-day production telemetry on `interpretation_backend` (must be
  100 % `supabase` with zero `filesystem` fallback firings).
- Phase 10D's filesystem catalog stays in code as the deprecated
  safety floor, exactly as the original Phase 10D defines.

---

## 3. Migration phases — 11A through 11C

### Phase 11A — Trust-tier prioritization

**The cheap lift.** Target: 57 % → ~63-65 % on the 21-Q mini-panel
by ranking branded-firm docs above the noise inside crowded
article-anchor sets.

**Modules touched:**
- NEW: `config/provider_trust_tiers.json` — curated
  `{provider_name: trust_tier}` map. ~25 entries (Crowe, EY,
  KPMG, Deloitte, PwC, BDO, Baker, Garrigues, Phillippi, etc.).
- NEW: `scripts/diagnostics/backfill_v11_trust_tiers.py` —
  operator-run, idempotent UPDATE backfill that sets
  `document_chunks.trust_tier` from
  `documents.authority`/`documents.provider_labels` via the new
  allowlist. Defaults missing matches to `medium` (matches today's
  behavior).
- `src/lia_graph/interpretacion/retriever_supabase.py` —
  `_group_chunks_by_doc` accepts `trust_tier_weight` (default
  0.30); score formula extends with the tier-bonus multiplier
  documented in §2.A. Reads `trust_tier` off the chunk row
  (already in hybrid_search return columns).
- `tests/test_interpretacion_retriever_supabase.py` — 3-5 new
  tests covering: tier=high outranks tier=medium-tied; tier=low
  doesn't sink below tied non-anchored docs; trust-tier weight=0
  disables the lever cleanly.

**Verification:**
- After cloud backfill: query
  `SELECT trust_tier, count(*) FROM document_chunks WHERE
  knowledge_class='interpretative_guidance' GROUP BY 1` — expect
  3-5 % high, ~70-80 % medium, balance low.
- Operator-authorized 21-Q mini-panel re-run via the existing
  scorer. Target: ≥ 62 % accept@top3 (5pt uplift over v0).
- §1.G 36-Q chat panel re-run: must stay at-or-above baseline
  34/36 acc+. Trust-tier ranking affects the panel-side retriever
  ONLY (`interpretacion/retriever_supabase.py`); the chat
  retriever uses `pipeline_d/retriever_supabase.py` which is
  untouched by 11A. Regression risk: zero, but the panel canon
  requires the re-run as a gate.

**Risk:** allowlist drift. The hand-curated
`provider_trust_tiers.json` can fall behind as the corpus grows;
new branded firms land in `unknown→medium`. Mitigation: a probe
script (`scripts/diagnostics/probe_v11_trust_tier_coverage.py`)
that lists unique `documents.authority` values not in the
allowlist; operator reviews monthly.

### Phase 11B — Falkor loader for InterpretationNode + INTERPRETS + COVERS_TOPIC

**The architectural lift.** Target: ≥ 70 % on the 21-Q mini-panel
by replacing Python-side article→doc index with Cypher anchors
and giving the chat-side planner first-class control over which
expert briefs surface alongside its citations.

**Modules touched:**
- NEW: `src/lia_graph/graph/interpretation_loader.py` — emits
  MERGE Cypher per §2.B. Idempotent. ~250 LOC.
- `src/lia_graph/ingest.py` — wire the loader into
  `materialize_graph_artifacts` AFTER article + reform loading
  (InterpretationNodes target ArticleNodes; need them present
  first).
- `src/lia_graph/pipeline_d/planner.py` — emit
  `interpretation_anchor_doc_ids` seed when `primary_article_keys`
  is non-empty (§2.B). New `LIA_PLANNER_INTERPRETATION_ANCHOR=on`
  env (default `on`); flip `off` to bypass for diagnostics.
- `src/lia_graph/interpretacion/retriever_supabase.py` —
  `fetch_interpretation_candidates` accepts
  `planner_anchor_doc_ids` and uses it when present, falls back
  to the Python article_index otherwise (§2.B).
- `src/lia_graph/interpretacion/orchestrator.py` — the dispatcher
  reads the planner's anchor from `deps` and passes it through.
- `scripts/dev-launcher.mjs` — add
  `LIA_INGEST_INTERPRETATION_NODES` to the env matrix; default
  `enforce` across all three modes.
- `tests/test_graph_interpretation_loader.py` (new) — schema
  validation of emitted MERGE statements; idempotency check (run
  loader twice → same node/edge counts).
- `tests/test_planner_interpretation_anchor.py` (new) — planner
  emits the anchor seed when `primary_article_keys` is non-empty
  AND `LIA_PLANNER_INTERPRETATION_ANCHOR=on`.

**Verification:**
- Cloud Falkor Cypher probe:
  `MATCH (i:InterpretationNode)-[:INTERPRETS]->(a:ArticleNode)
   RETURN count(i), count(distinct a), count(DISTINCT (i, a))`
  — expect ~105 i nodes, ~250+ a nodes touched, ~600+ edge
  instances.
- 21-Q mini-panel re-run. Target: ≥ 70 % accept@top3 with
  zero `wrong` rulings from anchor-seeded cards.
- §1.G 36-Q chat panel re-run: must hold at baseline. Phase 11B
  CAN affect the chat path because the planner's emit-anchor
  step runs unconditionally when articles are cited — but the
  anchor is only consumed by the expert-panel retriever. Chat
  retrieval (`pipeline_d/retriever_supabase.py`) doesn't read
  the new seed.

**Risk:** loader run cost. 105 docs × ~5 articles each × MERGE
on Falkor is ~525 round-trips per ingest; with batching the
overall add to ingest wall-clock is ~30-60 sec. Acceptable.
Memory risk on the planner's Cypher query: bounded by the
`LIMIT 8` per article cap.

### Phase 11C — Production flip + 7-day soak

**Closing the loop.** Verification is operational, not
feature-driven.

**Modules touched:**
- `scripts/dev-launcher.mjs` — production default flips
  `LIA_INTERPRETATION_SOURCE` from `filesystem` (v11.0 safety
  floor) back to `supabase` ONLY after 11A + 11B clear ≥ 70 %
  AND the operator authorizes.
- `docs/orchestration/orchestration.md` — env matrix mirror
  table row for production flips to `supabase`. Bump env matrix
  version + add change-log entry.
- `CLAUDE.md` mirror — same flip in the Runtime Read Path table.

**Verification:**
- Production telemetry over 7 days: 100 % of served chats with
  expert-panel hits show `diagnostics.interpretation_backend=supabase`
  with zero `filesystem` fallback firings.
- Empty-panel rate on chats that returned ≥ 1 citable normative
  article stays < 5 % (matches Phase 10D's original closing
  bar).
- The §1.G SME panel stays at baseline week-over-week (operator
  re-runs once during the soak window).

---

## 4. Six-gate plan per phase (per `docs/aa_next/README.md` policy)

### 4.1 Gates for Phase 11A

1. **Idea (one sentence).** Add per-doc trust-tier ranking so
   crowded article-anchor sets surface branded-firm docs first.
2. **Plan (narrow module).** Touch
   `interpretacion/retriever_supabase.py` (one helper extension)
   + `config/provider_trust_tiers.json` (new) + a backfill
   script. No DDL. No new SQL.
3. **Minimum success criterion.** 21-Q mini-panel accept@top3
   ≥ 62 % (5pt uplift over 10C v0's 57.1 %). AND zero new
   `wrong` rulings on anchor-seeded cards from the SME review.
4. **Test plan.**
   - Engineer: unit tests on the score formula; cloud SQL probe
     for tier distribution post-backfill.
   - Operator: authorizes backfill + mini-panel re-run.
   - SME: rates each card outcome `accept` / `meh` / `wrong`.
   - Decision rule: PASS iff ≥ 62 % accept AND zero `wrong`
     rulings from cards the boost surfaced.
5. **Greenlight.** Dual gate. SME run is the only one that
   unblocks Phase 11B.
6. **Refine-or-discard.** If trust-tier delta is < 3pt or
   surfaces `wrong` cards, two attempted refinements:
   (a) tighten the high-tier allowlist (fewer firms qualify;
   medium becomes the new default for ambiguous cases);
   (b) reduce the trust-tier weight from 0.30 → 0.15. After
   both, if still flat, log as a negative result in
   `docs/aa_next/next_done.md` and proceed to Phase 11B
   anyway — graph anchors are the load-bearing fix.

### 4.2 Gates for Phase 11B

1. **Idea.** Move the article→doc index from in-process Python
   memory to FalkorDB; let the chat-side planner anchor expert
   retrieval on its resolved articles via `INTERPRETS` edges.
2. **Plan.** New `graph/interpretation_loader.py` emitting MERGE
   Cypher against the existing v10.C schema scaffold; wire into
   `materialize_graph_artifacts`; planner emits anchor seed;
   retriever accepts the seed and prefers it over the
   article_index fallback.
3. **Minimum success criterion.** 21-Q mini-panel accept@top3
   ≥ 70 % (production ship bar) AND zero `wrong` SME rulings
   from anchor-seeded cards.
4. **Test plan.**
   - Engineer: schema-validation tests on the emitted MERGE
     Cypher; idempotency test (run twice → same counts).
   - Operator: full re-ingest with the loader enabled, then
     mini-panel re-run; Cypher probe to confirm graph state.
   - SME: re-runs the rubric on the 21-Q mini-panel.
   - Decision rule: PASS iff ≥ 70 % AND zero `wrong` from
     anchor-seeded cards.
5. **Greenlight.** Dual gate. Don't ship if anchor produces
   `wrong` cards even at ≥ 70 % accept — false positives are
   worse than false negatives in expert content surfaces.
6. **Refine-or-discard.** Two attempted refinements before
   discard:
   (a) limit anchor seeds to articles whose `trust_tier` is
   `high` (interaction with Phase 11A's tier ranking);
   (b) intersect anchor seeds with the question's resolved
   topic (don't anchor on `art_124_2` for a labor-law question
   even if the chat happens to cite it).

### 4.3 Gates for Phase 11C

1. **Idea.** Flip production `LIA_INTERPRETATION_SOURCE` from
   `filesystem` back to `supabase` now that the panel is past
   the ship bar.
2. **Plan.** One launcher line + the orchestration / CLAUDE.md
   mirror updates + a 7-day production soak.
3. **Minimum success criterion.** Production telemetry over 7
   days: 0 fallback firings AND no panel-empty rate
   degradation.
4. **Test plan.** Production telemetry on
   `interpretation_backend` value distribution + panel
   non-empty rate. Operator inspects daily.
5. **Greenlight.** 7 clean days.
6. **Refine-or-discard.** A single fallback firing is a
   diagnostic signal (per "Fail Fast, Fix Fast" canon in
   CLAUDE.md), not a failure — root-cause it before declaring
   shipped.

---

## 5. Schema additions

**Zero new SQL DDL.** All trust-tier work flows through the
existing `documents.authority` + `document_chunks.trust_tier`
columns (both present in the baseline migration).

**Zero new Falkor schema.** `InterpretationNode` +
`INTERPRETS` + `COVERS_TOPIC` already landed in
`graph/schema.py` as part of Phase 10C. Phase 11B only writes
the loader.

**One new config file:** `config/provider_trust_tiers.json` —
hand-curated allowlist of branded firms → trust_tier. ~25
entries at first ship.

---

## 6. Code surface map (full delta)

```
src/lia_graph/
├── interpretacion/
│   ├── retriever_supabase.py                MODIFIED (11A, 11B)
│   │   ├── _group_chunks_by_doc adds trust_tier_weight (11A)
│   │   └── fetch_interpretation_candidates accepts
│   │       planner_anchor_doc_ids; falls back to article_index (11B)
│   └── orchestrator.py                      MODIFIED (11B)
│       └── dispatcher reads planner anchor from deps
├── graph/
│   └── interpretation_loader.py             NEW (11B)
├── pipeline_d/
│   └── planner.py                           MODIFIED (11B)
│       └── emits interpretation_anchor_doc_ids
└── ingest.py                                MODIFIED (11B)
    └── invokes interpretation_loader in materialize_graph_artifacts

config/
└── provider_trust_tiers.json                NEW (11A)

scripts/
├── diagnostics/
│   ├── backfill_v11_trust_tiers.py          NEW (11A)
│   └── probe_v11_trust_tier_coverage.py     NEW (11A)
└── dev-launcher.mjs                         MODIFIED (11B, 11C)

tests/
├── test_interpretacion_retriever_supabase.py    MODIFIED (11A, 11B)
├── test_graph_interpretation_loader.py          NEW (11B)
└── test_planner_interpretation_anchor.py        NEW (11B)

docs/
├── orchestration/orchestration.md           MODIFIED (11A, 11B, 11C)
└── re-engineer/fix/fix_v11_may.md           THIS FILE
```

---

## 7. Risks + mitigations

### 7.1 Trust-tier allowlist subjectivity (Phase 11A)

**Risk.** "Crowe is high-tier" vs "Crowe-Latam-regional is
medium-tier" is a judgment call. Different SMEs disagree.

**Mitigation.** Ship the v0 allowlist conservatively (5-10 names
in high); operator reviews monthly via the coverage probe; tier
demotion is reversible (idempotent backfill).

### 7.2 Loader-ingest contention (Phase 11B)

**Risk.** Adding the interpretation loader to
`materialize_graph_artifacts` extends ingest wall-clock by
30-60 sec and increases peak Falkor batch volume. If running
during a cloud ingest under heavy load (e.g. an SME panel run on
staging), could cause RPC timeouts.

**Mitigation.** Loader runs AFTER article/reform loading and is
batched the same way (`FALKORDB_BATCH_NODES=500`,
`FALKORDB_BATCH_EDGES=1000`). Idempotency means a retry is safe.

### 7.3 Planner anchor over-firing (Phase 11B)

**Risk.** Every chat turn that resolves any article runs the
new Cypher query. If the planner resolves many articles per
turn (rare but possible), the query count spikes.

**Mitigation.** Single Cypher query per turn (one statement
matching `primary_article_keys IN $list`). Per-article LIMIT 8
+ total cap 24 keep the result set small. The query is read-only
on a hot graph; Falkor handles thousands of such queries per
second.

### 7.4 Production flip regression (Phase 11C)

**Risk.** Flipping production to `supabase` after a 70 % staging
result might still surface bad cards on real-world questions
outside the 21-Q mini-panel coverage.

**Mitigation.** Filesystem path stays in code as the deprecated
safety floor (Phase 10D semantics). Operator can revert the env
flag without a code redeploy. 7-day soak with daily check is the
deliberate validation window.

---

## 8. Open questions (decide before code lands)

### 8.1 Should Phase 11A's `trust_tier_weight` be per-tier or scalar?

Current proposal: scalar weight × tier-bonus multiplier
(`{high:2.0, medium:1.0, low:0.0}`). Alternative: per-tier
weight (`high:0.6, medium:0.3, low:0.0`).

**Recommendation:** scalar is simpler and explains the math in
one config knob; per-tier weighting is a v11.1 refinement after
the first 21-Q measurement.

### 8.2 Should the loader run in the SAME ingest that builds
articles, or as a separate step?

Same ingest = simpler operator workflow (one `make
phase2-graph-artifacts-supabase` runs everything). Separate
step = isolates failures and lets the operator backfill
interpretations without re-running the whole ingest.

**Recommendation:** same ingest by default (consistent with
how reforms and parameters are already loaded), AND a separate
CLI entry point `lia-graph-load-interpretations` for
operator-targeted refreshes.

### 8.3 ExpertProviderNode + AUTHORED_BY — still deferred?

The v10.C plan deferred `ExpertProviderNode` to v10.1. v11 has
the same recommendation: defer. The trust-tier work in 11A
exposes the value of provider-as-node (cross-cut "show me all
Crowe analyses of Art. X"), but doesn't require it. v11.2 scope
if and when product wants the cross-cut query.

---

## 9. Order of operations summary

1. **(11A pre-work)** Operator authorizes
   `scripts/diagnostics/backfill_v11_trust_tiers.py` against
   cloud Supabase. ~30 sec, idempotent.
2. **(11A)** Engineer ships
   `retriever_supabase.py` + `config/provider_trust_tiers.json`
   + new unit tests. Server restart for dev:staging.
3. **(11A)** Operator-authorized 21-Q mini-panel re-run via the
   existing scorer. Decision gate: ≥ 62 %.
4. **(11A)** Operator-authorized §1.G 36-Q chat regression
   panel re-run. Decision gate: at-or-above 34/36 acc+ baseline.
5. **(11B)** Engineer ships
   `graph/interpretation_loader.py` + planner edit + retriever
   edit + new unit tests. Local make-phase2 to validate loader
   against local Falkor + Supabase.
6. **(11B pre-cloud-ship)** Operator authorizes
   `make phase2-graph-artifacts-supabase
   PHASE2_SUPABASE_TARGET=staging` with the loader active.
   Cypher probe confirms graph state.
7. **(11B)** Server restart for dev:staging. Mini-panel re-run.
   Decision gate: ≥ 70 % + zero `wrong` from anchor-seeded
   cards.
8. **(11B)** §1.G regression panel re-run.
9. **(11C)** Operator flips production
   `LIA_INTERPRETATION_SOURCE` from `filesystem` to `supabase`
   via dev-launcher + Railway deploy.
10. **(11C)** 7-day production soak with daily telemetry checks.

**Earliest realistic calendar.** Phase 11A: 1 engineer day +
0.5 day for backfill + SME mini-panel review. Phase 11B: 3
engineer days + 1 day for ingest re-run + SME mini-panel review.
Phase 11C: 7 days observation. Total ≈ 6 engineer days + 9 days
operational soak, parallelizable to ≈ 2 weeks calendar.

---

## 10. What to do tomorrow morning

If you want this to start moving without re-reading the whole
document:

1. **Engineer**: draft `config/provider_trust_tiers.json` —
   start with 10 high-tier names (Crowe, EY, KPMG, Deloitte,
   PwC, BDO, Baker McKenzie, Garrigues, Phillippi, Brigard);
   ship the v0 file to repo. ~20 minutes.
2. **Operator**: review the allowlist + tag any v0 omissions.
3. **Engineer + Operator**: schedule the Phase 11A SME
   mini-panel re-run. Operator-authorized, 4-worker, ~6 min
   wall (the hardened runner now handles the auth-session 429
   issue from the v10 session).

**Start with Phase 11A.** It's a 1-day shippable lift expected
to add 5-8pt. If 11A clears 65 %, Phase 11B has less work to
do for the final 5pt to ≥ 70 %.
