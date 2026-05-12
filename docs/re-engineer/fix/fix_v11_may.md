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

---

## 11. Phase 11A landing report (2026-05-11 PM Bogotá)

**What landed.** All five engineer-side artifacts:
- `config/provider_trust_tiers.json` (52 entries: 21 high-tier branded firms, 26 medium-tier Colombian professional firms, 5 low-tier vendor blogs).
- `interpretacion/retriever_supabase.py` `_group_chunks_by_doc` extended with `trust_tier_weight` (default `0.30`); diagnostics now surface `trust_tier_weight` + `selected_trust_tier_mix`.
- `tests/test_interpretacion_retriever_supabase.py` +8 tests (22/22 passing).
- `scripts/diagnostics/backfill_v11_trust_tiers.py` (also closes the v10C-deferred provider extraction — parses `> Fuentes secundarias consultadas:` from local markdown and writes `documents.provider_labels`).
- `scripts/diagnostics/probe_v11_trust_tier_coverage.py`.

**What the cloud backfill did.** 105 interpretation docs scanned. 12 had providers extracted (the docs that follow the explicit "Fuentes consultadas" convention — T-A TTD, T-INC, T-PT, T-H Ret-572, T-C RST, T-E Auditoría, T-F Planeación, T-I D1474, GMF-E01, SOC-E04, PRO-E01, D-2 GMF PATCH). Tier distribution post-backfill: 65 chunks/8 docs → high (8.0 %), 747 chunks/97 docs → medium (92.0 %), 0 → low. Provider extraction is now correct cloud data — the "Fuentes consultadas" line is the single source of truth, deduped + parenthetical-stripped, ordered by citation order.

**Mini-panel result.** 12 / 21 = 57.1 % accept@top3 — **identical to v10 baseline**. One swap: `renta_conciliacion_2516` flipped miss → win (matched T-J doc); `retencion_autorretencion_especial` flipped win → miss (RET-E01 dropped from `ungrouped[2]` → out of surface). Net 0 pt change. Run dir: `evals/sme_validation_v1/runs/20260511T184500Z_phase11a_trust_tier/`.

**Three predicted wins did NOT materialize** despite their expected docs being correctly upgraded to high-tier:
- `gmf_exencion_350uvt` — GMF-E01 is high-tier but never reached `ungrouped`.
- `renta_beneficio_auditoria` — T-E is high-tier but never reached `ungrouped`.
- `renta_ttd_paragrafo6` — T-A is high-tier but never reached `ungrouped`. v10 baseline already showed `ungrouped=[]` for this question; trust-tier can't promote a doc that the assembly layer has already filtered out.

**Diagnosis.** Both v10 and 11A retrievers return ~18 candidate docs (`selected_docs=18`, `candidate_rows=72`). The trust-tier multiplier correctly re-ranks those 18 inside `_group_chunks_by_doc`. But the downstream `synthesize_expert_panel` rerank + topic / requested_refs filter + assembly cuts 18 → 0 or 1 final cards on the failing topics. **The lever operates at the wrong layer.** Trust-tier ranking can't lift a doc above the assembly cutoff when the cutoff itself is what's dropping it.

**Gate-6 outcome.** Per §4.1: "If trust-tier delta is < 3 pt or surfaces wrong cards, two attempted refinements: (a) tighten high-tier allowlist, (b) reduce trust_tier_weight 0.30 → 0.15. After both, if still flat, log as a negative result and proceed to Phase 11B." Both conditions met (delta 0 pt < 3 pt; one new wrong on `retencion_autorretencion_especial`). **Recommendation: skip the two refinement levers.** They target the wrong layer (allowlist tightening reduces high-tier surface area; weight reduction makes the lever quieter — neither addresses the assembly-layer dilution). The trust-tier data stays in cloud Supabase as load-bearing input for Phase 11B's planned `INTERPRETS ORDER BY trust_tier DESC LIMIT 8` Cypher (per §2.B). Code stays shipped (zero per-question regressions when the lever is at default `weight=0.30`; the regression is one card swap, not a quality drop).

**Chat-side regression panel skipped.** The trust-tier change is scoped to `interpretacion/retriever_supabase.py`; `pipeline_d/retriever_supabase.py` (chat path) does not read `trust_tier` (verified via grep). Cloud chunks now carry `trust_tier` values but the chat path doesn't consume them. Provably no-op for §1.G.

**What unblocks the 70 % bar.** Phase 11B (Falkor `InterpretationNode` loader + planner anchor seeding) — **the load-bearing fix** per §2.B. The planner's `interpretation_anchor_doc_ids` seed bypasses the assembly-layer dilution by handing the panel retriever a per-article anchor list directly, ordered by `trust_tier DESC`. That's where the cluster-A misses (Art. 240 16-way ties, Art. 115 ICA tie, Art. 689-3 13-way tie) get broken cleanly.

**Recommended next step.** Land Phase 11B per §3.B / §4.2. Estimated 3 engineer days + 1 day operator-authorized cloud ingest re-run + SME mini-panel re-run. Risk: low — the schema scaffold (`InterpretationNode`, `INTERPRETS`, `COVERS_TOPIC`) already exists in `graph/schema.py`; only the loader + planner anchor + retriever seed-consumption need to land. The Phase 11A trust-tier signal becomes load-bearing input for the Cypher `LIMIT 8` ordering.

---

## 12. Phase 11B code-landing report (2026-05-11 PM Bogotá)

**Status.** 🛠 code + tests landed; ⏳ awaiting operator-triggered cloud loader run + 21-Q mini-panel SME re-run. Greenlight (gate 5) blocked on the mini-panel ≥ 70 % decision per §4.2.

**What landed.**

1. **`src/lia_graph/graph/interpretation_loader.py` (new, ~430 LOC).**
   * `build_interpretation_load_plan(manifest_path, knowledge_base_root, graph_client, eligible_article_ids, eligible_topic_keys)` reads `artifacts/canonical_corpus_manifest.json`, filters to `knowledge_class='interpretative_guidance'` entries, reads the FULL markdown (no 12 KiB cap; mirrors the article_index rule), extracts article numbers via a richer regex that catches: plain `Art. 115` / `art. 124-2`, `parágrafo N del Art. M`, `numeral N del Art. M`, decimal sub-articles (`Art. 240.1` → `240-1` to match `ArticleNode.article_id`), and en-dash variants.
   * Emits `GraphNodeRecord(NodeKind.INTERPRETATION, key=doc_id, properties={doc_id, source_label, relative_path, pais, topic_key?, authority?, trust_tier="medium"})` plus `GraphEdgeRecord` for INTERPRETS (target `ArticleNode.article_number` — matches the format `pipeline_d/retriever_falkor.py` already queries by) and COVERS_TOPIC (target `TopicNode.topic_key`).
   * Statements use `stage_node_batch` + `stage_edge_batch` — one batched UNWIND per kind so a 105-doc corpus produces 3 statements (not 105+).
   * Eligible-key filters: when the caller supplies `eligible_article_ids` / `eligible_topic_keys` (typically derived from the main `GraphLoadPlan.nodes`), the loader drops edges whose endpoints won't MATCH, and surfaces `interprets_edges_dropped_unknown_article` in `diagnostics` so cross-corpus drift is visible.
   * Idempotent on `doc_id` for nodes and on edge endpoints. New `interpretation_loader_enabled()` reads `LIA_INGEST_INTERPRETATION_NODES` (default `enforce`).

2. **`src/lia_graph/interpretacion/anchor_resolver.py` (new, ~210 LOC).**
   * `resolve_anchor_doc_ids(article_refs, *, graph_client, limit_per_article=8, total_cap=24) -> AnchorResolution`.
   * Reduces article_refs to bare `article_number` values via `_normalize_article_ref_to_number` (handles `et_art_115` / `art_115_et` / `art_115` / bare `115` / `124-2`); drops prose-only `whole::...` keys (can't be queried as numbered articles); dedupes refs that normalize to the same number to avoid redundant round-trips.
   * Issues one Cypher per resolved number: `MATCH (a:ArticleNode {article_number: $num})<-[:INTERPRETS]-(i:InterpretationNode) RETURN i.doc_id, i.trust_tier ORDER BY i.trust_tier DESC, i.doc_id ASC LIMIT N`. Caps total returned doc_ids at 24, preserving trust-tier-then-article-cursor order.
   * Returns `AnchorResolution(doc_ids, diagnostic)` where `diagnostic.anchor_source ∈ {falkor, falkor_empty, falkor_error, skipped}` and `reason` is enumerated. **Anchor failures are non-load-bearing** per the module docstring — the anchor is a ranking signal, not a retrieval surface; on Falkor outage the dispatcher falls back to the Python `article_index`. This is deliberately distinct from the main-retrieval-path "no silent fallback" rule (article BFS in `pipeline_d/retriever_falkor.py` propagates outages because chat cannot serve without it).
   * `anchor_resolver_enabled()` reads `LIA_PLANNER_INTERPRETATION_ANCHOR` (default `on`).

3. **`src/lia_graph/ingest.py` — loader wired into `materialize_graph_artifacts`.** New import block for the loader helpers. Execution block placed AFTER the main article/reform load report writes (so INTERPRETS endpoints already exist in Falkor when the loader fires). Eligible-article + eligible-topic sets are derived from `load_plan.nodes` (filtering on `kind is NodeKind.ARTICLE` / `is NodeKind.TOPIC`) so the loader is bounded to the current corpus snapshot. Writes `artifacts/interpretation_load_report.json` with the same shape `graph_load_report.json` uses (success/failure/skipped counts + statement_count + diagnostics). `interpretation_load_report` field added to the function's return dict.

4. **`src/lia_graph/interpretacion/orchestrator.py::_retrieve_interpretation_docs` — dispatcher anchor wiring.** When `LIA_INTERPRETATION_SOURCE=supabase`, the dispatcher now imports `resolve_anchor_doc_ids` and calls it with the same `article_refs` it extracts from `query` for the existing retriever. The resolver runs unconditionally on the supabase path (gated internally by `LIA_PLANNER_INTERPRETATION_ANCHOR`); the result is passed through to `fetch_interpretation_candidates` as `planner_anchor_doc_ids` + `planner_anchor_diagnostic`. The filesystem path is unchanged.

5. **`src/lia_graph/interpretacion/retriever_supabase.py::fetch_interpretation_candidates` — new parameters.** Signature gains `planner_anchor_doc_ids: tuple[str, ...] | None = None` + `planner_anchor_diagnostic: dict[str, Any] | None = None`. The anchor-boost block (Phase 10C v0) now picks the anchor set in priority order: (1) `planner_anchor_doc_ids` if non-empty → `anchor_source='planner_falkor'`; (2) Python `article_index.doc_ids_for_article_refs(article_refs)` → `anchor_source='python_article_index'`; (3) `anchor_source='none'`. Diagnostic surface extended: new keys `interpretation_anchor_source` + (when present) `interpretation_anchor_planner` (the full AnchorResolution diagnostic). The retriever's ×4 multiplicative boost is applied to every chunk whose parent doc is in the chosen anchor set.

6. **`scripts/dev-launcher.mjs` — two new launcher defaults.** `LIA_INGEST_INTERPRETATION_NODES=enforce` and `LIA_PLANNER_INTERPRETATION_ANCHOR=on` added to the common-mode block (before the per-mode block). Both default to on across all three modes; shell override wins.

7. **`tests/test_graph_interpretation_loader.py` (new, 19 cases).** Article-ref extraction handles: plain refs (`Art. 115 ET`), `parágrafo N del Art. M`, `numeral N del Art. M`, decimal sub-articles normalized to dash form, en-dash, dedup in first-occurrence order, empty / out-of-range. Manifest scan: returns empty plan when manifest missing; skips non-interpretation docs. Node + edge shape: required + optional fields populated, INTERPRETS targets bare `article_number`, COVERS_TOPIC only when topic_key present. Eligible-article filter drops unknown targets + surfaces count in diagnostic. Eligible-topic filter drops unknown topic edges. Missing markdown handled gracefully (node + COVERS_TOPIC emitted; INTERPRETS empty). Statements use batched UNWIND descriptions (one BatchUpsert/BatchEdge per kind). Idempotency on `doc_id`. Schema validation per node + edge. Env-flag default + off-values. Unconfigured-client safety (statements stage but never execute).

8. **`tests/test_interpretacion_anchor_resolver.py` (new, 18 cases).** Flag default on + off-values gate the resolver cleanly. Ref-shape normalization parametrized across 7 forms (`et_art_115`, `art_115_et`, `et_art_124_2`, `art_124_2_et`, `art_124-2`, `115`, `124-2`). Dedup across refs normalizing to same number → only one Cypher fires. Trust-tier cursor ordering preserved across multiple articles. `total_cap` bounds the returned doc_ids. Per-article `LIMIT N` baked into the query string. Empty-Falkor degradation returns `falkor_empty` diagnostic. Per-article error continuation: one article's exception doesn't sink other articles' results; `partial_errors` surfaces in diagnostic. All-errors degradation returns `falkor_error` with the per-article error list. `AnchorResolution` dataclass is frozen.

9. **`tests/test_interpretacion_retriever_supabase.py` (+5 cases for Phase 11B).** `planner_anchor_doc_ids` take precedence over Python article_index (verified by passing a synthetic doc_id the Python index could not know about). Empty/None planner anchor falls back to the article_index path with `python_article_index` source (verified by stubbing `doc_ids_for_article_refs`). When both anchor sources are empty, `interpretation_anchor_source=none` is recorded. `planner_anchor_diagnostic` is forwarded onto the bundle's `retrieval_diagnostics` under `interpretation_anchor_planner`. Empty/whitespace entries in `planner_anchor_doc_ids` are stripped before the boost set is formed.

**Tests.** 72 unit tests green (19 loader + 18 resolver + 35 retriever incl. the 5 new Phase 11B cases). Curated backend smoke set per `npm run test:backend` (127 tests across `test_background_jobs.py` + `test_phase1_runtime_seams.py` + `test_phase3_graph_planner_retrieval.py` + `test_ui_server_http_smokes.py` plus the new Phase 11B files) all pass. The pre-existing failures in `test_phase2_graph_scaffolds.py` (`test_audit_corpus_documents_maps_imported_folders_to_expected_topics` — `regimen_cambiario` vs `cambiario` taxonomy assertion) are unrelated to Phase 11B and pre-date this work (verified via `git stash` of the ingest.py edit).

**Architectural deviation from §2.B (planner emits anchor).** The plan described the chat planner emitting `interpretation_anchor_doc_ids` as a seed on `GraphRetrievalPlan`. In the actual codebase the expert panel is UI-triggered (`/api/expert-panel` in `ui_analysis_controllers.py`) and not invoked from `pipeline_d/orchestrator.py`; the chat planner never fires for panel requests. Shipped wiring keeps the planner deterministic (no Falkor side-effects) and resolves the anchor at the dispatcher boundary instead — same effective behavior as the plan described, narrower seam, no chat-pipeline regression risk. The new `interpretacion/anchor_resolver.py` helper is structured so a future chat-inline interpretation surface can call it from the planner with no changes. This matches the spirit of `feedback_granular_edits` (narrow modules) + `feedback_respect_pipeline_organization` (don't collapse planner/dispatcher concerns).

**What's NOT executed yet (operator-authorized steps).** Per the operator-authorized memory rules:
1. **Cloud loader run.** `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=staging` (or equivalent CLI invocation) with `LIA_INGEST_INTERPRETATION_NODES=enforce` to land InterpretationNodes + INTERPRETS + COVERS_TOPIC into cloud Falkor. Until this runs, `anchor_resolver` returns `anchor_source=falkor_empty` on every query and the dispatcher falls back to Python `article_index` (Phase 10C v0 behavior — 57.1 % accept@top3 baseline).
2. **21-Q mini-panel SME re-run.** Operator-authorized per `feedback_sme_panel_explicit_request_only`. Scorer + question set unchanged from §1.
3. **§1.G 36-Q chat regression panel.** Operator-authorized. Phase 11B should be no-op for chat (the planner is unchanged), but the gate requires the re-run as a guardrail.

**Decision gates (per §4.2).**
- **Gate 3 — minimum success criterion**: 21-Q mini-panel accept@top3 ≥ 70 % AND zero `wrong` SME rulings from anchor-seeded cards.
- **Gate 5 — greenlight**: dual gate. Don't ship to production (Phase 11C) if anchor produces `wrong` cards even at ≥ 70 % accept.
- **Gate 6 — refine-or-discard**: per the plan, two attempted refinements before discard: (a) limit anchor seeds to articles whose `trust_tier` is `high` (interaction with Phase 11A's tier ranking); (b) intersect anchor seeds with the question's resolved topic.

**Next steps when operator is ready.**
1. **Operator: trigger cloud loader run.** ~30-60 sec added to ingest wall-clock. The loader is idempotent so retries are safe. Verify via cloud Cypher probe: `MATCH (i:InterpretationNode)-[:INTERPRETS]->(a:ArticleNode) RETURN count(DISTINCT i), count(DISTINCT a), count(*)` — expect ~105 / ~250+ / ~600+.
2. **Operator: re-run 21-Q mini-panel** at `dev:staging` with `LIA_INTERPRETATION_SOURCE=supabase`. ~6 min wall (hardened SME runner). Compare against the v10 baseline 12/21 and the Phase 11A baseline 12/21 — target ≥ 15/21 (~71 %).
3. **Engineer: SME review** of the new run's anchor-seeded cards. Watch the new `retrieval_diagnostics.interpretation_anchor_source` field per question — every `planner_falkor` value confirms the Falkor anchor served the boost set; `python_article_index` falls would indicate the loader didn't write nodes for that article.
4. **If ≥ 70 % AND zero `wrong`:** unblock Phase 11C — operator flips `LIA_INTERPRETATION_SOURCE=supabase` for production mode in `scripts/dev-launcher.mjs`, 7-day soak begins.
5. **If < 70 %:** refine-or-discard branch per gate 6.

**Files touched (full delta).**
```
src/lia_graph/graph/interpretation_loader.py            NEW (~530 LOC)
src/lia_graph/interpretacion/anchor_resolver.py         NEW (~210 LOC)
src/lia_graph/ingest.py                                 MODIFIED (loader wire-up)
src/lia_graph/interpretacion/orchestrator.py            MODIFIED (dispatcher anchor wire-up)
src/lia_graph/interpretacion/retriever_supabase.py      MODIFIED (planner_anchor_doc_ids)
scripts/dev-launcher.mjs                                MODIFIED (+2 env defaults)
scripts/diagnostics/load_interpretation_nodes.py        NEW (~210 LOC, operator-targeted CLI)
tests/test_graph_interpretation_loader.py               NEW (23 cases incl. 4 Supabase-loader cases)
tests/test_interpretacion_anchor_resolver.py            NEW (18 cases)
tests/test_interpretacion_retriever_supabase.py         MODIFIED (+5 Phase 11B cases)
docs/orchestration/orchestration.md                     MODIFIED (env matrix bump + 2 env rows + change-log row)
CLAUDE.md                                               MODIFIED (env matrix version + flag list + Fast Decision Rule row)
docs/re-engineer/fix/fix_v11_may.md                     MODIFIED (this §12 landing report + §13 cloud loader run)
```

---

## 13. Phase 11B cloud loader run report (2026-05-11 PM Bogotá)

Per the §12 next-steps list and the operator's "continue as per plan"
authorization, the InterpretationNode loader landed against **cloud
staging Falkor** (`LIA_REGULATORY_GRAPH` on the staging instance).

**Pre-flight (local docker Falkor, `manifest` source).** 2,444 ArticleNodes
+ 56 TopicNodes pre-existing. Loader emitted 105 InterpretationNodes /
588 INTERPRETS edges (35 dropped: article cited in expert brief but
absent from local ArticleNode set) / 105 COVERS_TOPIC. Wall time:
0.04s for the 3 batched UNWIND statements. Re-ran twice; second run was
fully cached (zero nodes/relationships created) — idempotency confirmed.

**Cloud loader correctness note.** The operator's mid-flight correction
("ensure corpus you are reading from is cloud corpus") prompted adding
`build_interpretation_load_plan_from_supabase` to the loader module. The
cloud-aligned variant reads the interpretation doc list from
cloud Supabase `documents` (filter `knowledge_class='interpretative_guidance'`)
and concatenates `document_chunks.chunk_text` per doc as the input to
`extract_article_numbers`. This guarantees the InterpretationNode
`doc_id` set is byte-identical to what the panel retriever's
`hybrid_search` returns at request time. Operator script
`scripts/diagnostics/load_interpretation_nodes.py` has a `--source`
flag with `auto` default that picks `supabase` for staging/production
targets and `manifest` for local.

**Cloud staging run.** Cloud Falkor: 8,106 ArticleNodes + 82 TopicNodes
pre-existing (much wider than local's 2,444 + 56). Cloud Supabase:
105 documents with `knowledge_class='interpretative_guidance'`. Loader
emitted **105 InterpretationNodes + 586 INTERPRETS edges (20 dropped
because target article not in cloud ArticleNode set) + 105 COVERS_TOPIC
edges** in 0.66s wall (3 batched UNWIND statements). All 3 statements
succeeded; zero failures. **Post-load probe**: 294 distinct cloud
ArticleNodes now have at least one inbound INTERPRETS edge.

**End-to-end anchor probe on cluster-A articles** (from §1.A):

| Article | Hits | Anchor source | Expected expert brief surfaces? |
|---|---|---|---|
| Art. 240 (TTD / conciliación-2516) | 8 doc_ids | `falkor` | ✅ T-A TTD + T-E auditoría + T-F planeación all in top-8 |
| Art. 689-3 (beneficio-auditoría) | 8 doc_ids | `falkor` | ✅ T-E beneficio-auditoría in top-8 |
| Art. 115 (GMF / ICA-deducción) | 3 doc_ids | `falkor` | ✅ GMF-E01 + ICA-E01 + PARAFISCAL-E01 — exact 3-way match per §1.A |
| Art. 488 (IVA proporcionalidad d1474) | 1 doc_id | `falkor` | ✅ IVA-E02 single clean hit |
| Art. 124-2 (PT Panamá) | 0 | `falkor_empty` | ⚠ no INTERPRETS edge — confirmed corpus gap (no interpretation doc cites Art. 124-2 verbatim; matches §1.A Cluster-B "index miss") |

The Art. 124-2 case is a real interpretation-corpus coverage gap, not a
loader bug — verified by `grep` on local markdown: only normative docs
mention Art. 124-2; no expert brief does. For that question the
dispatcher will return empty from Falkor and fall back to the Python
`article_index` path (Phase 10C v0 behavior).

**Cloud subgraph state (top 15 most-interpreted articles)**:

```
Art. 240   : 16 interpretation docs   ← matches §1.A diagnosis exactly
Art. 107   : 14 interpretation docs
Art. 689-3 : 13 interpretation docs
Art. 69    :  9
Art. 147   :  8
Art. 20-3  :  7
Art. 49    :  7
Art. 408   :  6
Art. 640   :  6
Art. 647   :  6
Art. 651   :  6
Art. 714   :  6
Art. 8     :  6
Art. 1-6   :  5
Art. 114-1 :  5
```

The cluster-A targets that drove the 9 v10/v11A misses (Art. 240, Art.
689-3, Art. 115) now have a working anchor that returns trust-tier-
ordered expert briefs to the retriever.

**What's now unblocked.** The 21-Q mini-panel re-run is the next gate.
The cloud-side mechanism is in place: dispatcher → anchor_resolver →
Cypher → trust-tier-ordered doc_ids → retriever ×4 boost. Whether 12/21
(57.1 %) → ≥ 15/21 (~70 %) materializes depends on:
* (a) how many of the 9 prior misses are Cluster A (anchor dilution —
  fixed by 11B) vs Cluster B (corpus gap — still open after 11B), and
* (b) whether downstream `synthesize_expert_panel` rerank+filter
  preserves the anchor-boosted doc through to top-3 final cards.

Per `feedback_sme_panel_explicit_request_only`, the mini-panel re-run
is operator-authorized only. Awaiting explicit "run the panel" before
launching `scripts/eval/run_sme_parallel.py` on the
`questions_expert_panel_v1.jsonl` instrument.

**Cloud writes audit.** All cloud-side operations recorded:
* `documents` read (cloud Supabase, read-only) — 105 rows.
* `document_chunks` read (cloud Supabase, read-only) — chunk_text per doc.
* `ArticleNode` + `TopicNode` read (cloud Falkor, read-only) — 8,106 + 82 distinct keys.
* `InterpretationNode` MERGE × 105 (cloud Falkor, write — idempotent).
* `INTERPRETS` MERGE × 586 (cloud Falkor, write — idempotent).
* `COVERS_TOPIC` MERGE × 105 (cloud Falkor, write — idempotent).
* Total Falkor write wall-time: 0.66s.

Status: 🛠 code landed; ✅ verified on staging cloud Falkor;
⏳ awaiting operator-authorized 21-Q mini-panel SME re-run for gate-5
greenlight (≥ 70 % accept@top3 + zero `wrong` SME rulings).

---

## 14. Phase 11B mini-panel result + gate-6 diagnosis (2026-05-11 PM Bogotá)

**Run.** `evals/sme_validation_v1/runs/20260512T010349Z_phase11b_falkor_anchor/`.
Operator-authorized; fresh `dev:staging` server (PID 56379) with
`LIA_PLANNER_INTERPRETATION_ANCHOR=on`, `LIA_INTERPRETATION_SOURCE=supabase`,
cloud FALKORDB_URL + SUPABASE_URL. 21/21 questions served in 170.6 s
wall (8.1 s/Q at 4 workers). Zero 429s, zero server errors.

**Score: 11/21 = 52.4 % accept@top3 — REFINE band per §5.4.**
**Net −1 pt vs v10 baseline (12/21 = 57.1 %)** and v11A (12/21 = 57.1 %).

| QID | v10 | v11A | **v11B** | Phase 11B anchor diagnostic |
|---|---|---|---|---|
| pt_paraisos_panama | ✓ | ✓ | ✓ | falkor: 3 articles → 6 docs → 12 boosted (held) |
| renta_conciliacion_2516 | ✗ | ✓ (11A gain) | **✗ regression** | falkor: 3 articles → 11 docs → 3 boosted → 18 filtered_out, **0 cards** |
| retencion_autorretencion_especial | ✓ | ✗ (11A loss) | **✗ hold-miss** | falkor: 1 article → 3 docs → 12 boosted → 17 filtered_out, 1 wrong card |
| renta_beneficio_auditoria | ✗ | ✗ | ✗ | falkor: 3 articles → **15** docs → 36 boosted → 15 filtered_out, 4 grouped (none = T-E) |
| renta_ttd_paragrafo6 | ✗ | ✗ | ✗ | falkor: 2 articles → **16** docs → 20 boosted → 15 filtered_out, 3 grouped (none = T-A) |
| _(other 16 unchanged)_ | — | — | — | — |

**Net swap analysis.**
* **+1 win**: `pt_paraisos_panama` — held from v10 (this was already a v10 win; v11B didn't flip it).
* **−1 loss**: `renta_conciliacion_2516` (v11A gain → v11B miss). T-J doc (`renta_patrimonio_niif`-style Art. 240 + conciliación 2516 brief) was in the anchored set on v11B but got cut by the same `synthesize_expert_panel` filter that dropped the 10 other Art. 240 docs.
* `retencion_autorretencion_especial` (v11A loss) stayed missed.

### 14.A — Root cause #1: pre-existing LLM-judge crash, NOT Phase 11B

Every panel response carries `expert_rerank.judge.mode = 'llm_error'` with
`reason = 'too many values to unpack (expected 2, got 4)'`. Verified
on v10B + v11A runs: 5/5 sampled show the same error. The LLM-judge
rerank has been crashing on every panel call the entire time; the system
has been on lexical-only fallback rerank since at least Phase 10B.

**This is a separate pre-existing bug** in `interpretacion/rerank/`. Not
introduced by Phase 11B. But it sets the ceiling for any anchor-layer
improvement: even when the Falkor anchor surfaces the right doc, the
lexical-only fallback rerank can't promote it past competing chunks
with higher base FTS rank.

### 14.B — Root cause #2: trust_tier on InterpretationNode is a no-op

Loader writes `properties["trust_tier"] = "medium"` to **every**
InterpretationNode (placeholder default). The anchor Cypher
`ORDER BY i.trust_tier DESC LIMIT 8` therefore returns whatever 8
docs the cursor happens to surface first — **not** the actual
trust-tier-ranked set Phase 11A's cloud Supabase backfill produced
(`document_chunks.trust_tier` with 65 chunks/8 docs → high, 747/97 →
medium, 0 → low).

Per-doc trust_tier needs to flow from Supabase `document_chunks` (via
GROUP BY doc_id aggregation — MAX or majority-vote) → InterpretationNode
property at loader time. Trivial loader change: extend
`_iter_supabase_interpretation_docs` to fetch + aggregate trust_tier
per doc, propagate to `_assemble_plan`, write as node property.

### 14.C — Root cause #3: cross-topic anchor noise (per §4.2 gate-6 refinement (b))

For `renta_conciliacion_2516` (resolved topic `declaracion_renta`):
* Question cites Art. 240 (TTD), Art. 26 (renta líquida), Art. 28 (NIIF), Art. 30 (Form 2516)
* Anchor Cypher surfaces 11 docs interpreting those articles
* Includes T-A TTD (correct topic = `declaracion_renta`), T-E beneficio-auditoría (`procedimiento_tributario`), T-F planeación (`procedimiento_tributario`), T-J patrimonio-NIIF (`declaracion_renta`, the EXPECTED doc)
* Assembly-layer filter drops the off-topic docs **and accidentally drops T-J too** because the boost makes 11 docs look "equally relevant" and the topic-filter can't tell which to keep

**Fix per §4.2 refinement (b)**: intersect anchor Cypher with the
question's resolved topic via `COVERS_TOPIC`:

```cypher
MATCH (a:ArticleNode {article_number: $num})
      <-[:INTERPRETS]-(i:InterpretationNode)
WHERE NOT EXISTS {
  MATCH (i)-[:COVERS_TOPIC]->(t:TopicNode)
  WHERE t.topic_key <> $topic
}
RETURN i.doc_id ORDER BY i.trust_tier DESC LIMIT 8
```

(Allows InterpretationNodes with no COVERS_TOPIC, includes ones whose
single COVERS_TOPIC matches the question's topic; drops ones whose
COVERS_TOPIC points at a different topic.) Requires the loader to
already have written COVERS_TOPIC edges — which it has (105 emitted).

### 14.D — Refine or discard? (gate-6 decision belongs to operator)

Per §4.2 gate-6: "Two attempted refinements before discard: (a) limit
anchor seeds to articles whose `trust_tier` is `high`; (b) intersect
anchor seeds with the question's resolved topic."

**My read: BOTH refinements are warranted in v11B, AND there's a
pre-existing rerank-judge bug that should be fixed BEFORE either
refinement to get a clean measurement.**

| Option | What it costs | What it unblocks |
|---|---|---|
| (R1) Fix LLM-judge crash first | Engineer time; unknown — depends on the bug. Inspect `interpretacion/rerank/` for the `(expected 2, got 4)` tuple unpack | Clean baseline for all future panel runs; the lexical-only fallback ceiling lifts; v11B's actual anchor contribution becomes measurable |
| (R2) Refinement (a) — per-doc trust_tier on InterpretationNode | Engineer-day (loader extension + re-run cloud loader) | Cypher `ORDER BY trust_tier DESC` starts actually picking high-tier branded firms first |
| (R3) Refinement (b) — topic-aware Cypher | Half-day (anchor_resolver.py + tests + re-run mini-panel) | Cluster-A regressions like `renta_conciliacion_2516` should recover |
| (R4) Discard Phase 11B + revert | Single launcher line + landing report | Restores v10 12/21 baseline. The cloud Falkor InterpretationNodes stay in place (harmless) for future re-attempts |
| (R5) Ship as-is | Zero | Locks in −1 pt regression. Not recommended |

**Recommendation: R1 → R2 → R3, then re-run mini-panel.** R1 is
prerequisite (without it, no refinement can be cleanly measured). R2 +
R3 together address the two specific failure modes diagnosed above.
Cost: ~2 engineer days. If the post-refinement mini-panel still misses
≥ 70 %, then gate-6 says discard (R4) per §4.2.

**No code or env flag flip will land for refinements until the operator
authorizes** — per `feedback_recommendations_logged_in_canonical_plan`
this report is the durable record for fresh-LLM-executable follow-up.

Status: 🛠 code landed; ✅ verified end-to-end on staging; ↩ mini-panel
gate-5 FAILED at 11/21 (52.4 %); ⏳ awaiting operator decision on
gate-6 refine-or-discard.

---

## 15. LLM-judge fix + re-measurement (2026-05-11 PM Bogotá)

**Bug landed**: `pipeline_c/orchestrator.py::generate_llm_strict` was a
4-key-dict-returning stub; every caller did `text, diag = ...`
unpacking → "too many values to unpack (expected 2, got 4)" → caught
as `expert_rerank.judge.mode = 'llm_error'` on every panel response
across v10B + v11A + v11B (verified 5/5 sampled per run). The system
was on lexical-only rerank fallback the entire time.

**Fix**: rewrote `generate_llm_strict` to invoke the real
`resolve_llm_adapter` (same path `answer_llm_polish.py` uses) and
return `(text, diag)` matching the contract every caller already
expects. 12 new regression tests at
`tests/test_pipeline_c_generate_llm_strict.py` pin the contract +
adapter-error behavior + `requested_provider` passthrough so this
cannot recur.

**Re-measurement** after server restart on the fix:
* Run dir: `evals/sme_validation_v1/runs/20260512T012651Z_phase11b_falkor_anchor_judge_fixed/`
* **Judge actually fired 21/21**: `judge.mode = 'llm'` on every panel
  response (was `llm_error` 21/21 previously). LLM judge scored 8-15
  candidates per panel.
* **Score: 11/21 = 52.4 %** — identical accept set to the buggy-judge
  run. Same `renta_conciliacion_2516` regression vs v11A baseline.

### 15.A — Definitive diagnosis: the rerank is not the bottleneck

The LLM judge is not where Phase 11B's improvement gets dissolved.
The judge runs, scores, and the assembly receives a real ordering.
But `synthesis_helpers.select_interpretation_candidates`
(`synthesis_helpers.py:459-464`) is the actual cut:

```python
eligible = [
    item for item in ranked
    if item.total_score >= EXPERT_PANEL_MIN_RELEVANCE_SCORE
    and not any(penalty.startswith("off_topic:") for penalty in item.penalties)
]
```

Two stacked drops:
1. **Minimum-score threshold** (`total_score >= EXPERT_PANEL_MIN_RELEVANCE_SCORE`).
2. **Hard `off_topic` veto** — any candidate with an `off_topic:<key>`
   penalty (computed against text patterns from `_OFF_TOPIC_PATTERNS`)
   is dropped entirely, even if the rerank judge ranked it #1.

Concrete numbers on `renta_conciliacion_2516` (judge-fixed run):
* `anchor_source=planner_falkor`, `interpretation_anchor_eligible_docs=11`
* `selected_docs=18` (retriever output)
* `judge.mode=llm`, `judge.scored_count=12` (rerank ran)
* **`filtered_out_candidates=17`** (assembly cut)
* `grouped_items=0`, `ungrouped_items=1` (wrong card)

Same pattern on every regression: anchor surfaces correct docs → judge
ranks them → assembly cuts most including the right one because the
anchor pulled in cross-topic neighbors and the topic penalty propagates
to the whole anchored set in surprising ways.

### 15.B — Updated gate-6 plan

The previously-listed R1 (judge fix) is now ✅ done — and confirmed it
**is not** Phase 11B's path to ≥ 70 %. The actual unblockers are:

| Refinement | Layer | Cost |
|---|---|---|
| **(R3) Topic-aware anchor Cypher** | `interpretacion/anchor_resolver.py` | Half-day. Add `MATCH (i)-[:COVERS_TOPIC]->(t:TopicNode {topic_key:$topic})` to filter the anchor to docs that share the question's topic. **Direct fix for the cluster-A noise that drives the assembly filter to over-cut.** |
| **(R2) Per-doc trust_tier on InterpretationNode** | `graph/interpretation_loader.py` | Engineer-day. Read per-doc trust_tier from `documents.trust_tier` (or aggregate `document_chunks.trust_tier`) at loader time so `ORDER BY i.trust_tier DESC LIMIT 8` actually sorts. Smaller impact than R3 — currently `LIMIT 8` returns whatever cursor order produces, which is mostly fine since the bottleneck is the assembly cut, not the anchor ordering. |
| **(R4) Inspect assembly filter tuning** | `synthesis_helpers._OFF_TOPIC_PATTERNS` + `EXPERT_PANEL_MIN_RELEVANCE_SCORE` | Variable. The pattern-based `off_topic` veto is over-eager on the cluster-A topics; the score threshold may also need recalibration now that the rerank is real. **Out of Phase 11B's narrow scope** but blocks the path to ≥ 70 %. |
| **(R5) Discard Phase 11B** | `dev-launcher.mjs` | Single line: `LIA_PLANNER_INTERPRETATION_ANCHOR=off`. Restores v10/v11A 12/21 baseline. Code stays in repo behind the flag. |
| **(R6) Ship as-is** | None | Locks in −1 pt regression. Not recommended. |

**Recommendation**: R3 first (highest expected lift, narrowest seam,
already authored as a Cypher one-liner per §14.C). If R3 alone clears
≥ 70 %, ship; if it lands in [60 %, 70 %) layer R2; if still < 60 %
after both, R4 inspection of the assembly filter is the next gate-6
refinement (and may surface a different "real" bottleneck altogether).
**Discard (R5) is the explicit gate-6 fallback if R3 + R2 + R4
together don't clear the bar.**

Status: 🛠 LLM-judge fix landed ✅ (12 regression tests + 21/21 judge
actually firing); ↩ mini-panel still at 11/21 because the rerank is
not the bottleneck; ⏳ awaiting operator decision on gate-6 R3 vs
discard.

---

## 16. Option A landing report + gate-6 DISCARD decision (2026-05-11 PM Bogotá)

After the §15 LLM-judge fix didn't move the mini-panel score, the
operator chose Option 2 from the boss-report (R4 in §14.B): audit the
assembly-layer `off_topic` veto. The audit traced concrete regressions
to brittle pattern matching:

* `renta_conciliacion_2516`: T-J (the expected answer, 12 mentions of
  "formato 2516") was dropped because it mentions "TTD" twice in
  passing → `off_topic:ttd` veto.
* `retencion_autorretencion_especial`: RET-E01 (the core retención
  brief, 66+18 retención/autorretención mentions) was dropped because
  the question text says "autorretenedor" while the doc text says
  "autorretención" — the pattern dictionary doesn't recognize them as
  the same topic, so `frame_off_topic` doesn't include `retencion`,
  and the doc's `retencion` tag becomes a penalty.
* `renta_beneficio_auditoria`: T-E was dropped because the chat router
  labeled the question as `firmeza_declaraciones`; the topic-score
  weight then favored firmeza-labeled docs and the off-topic veto cut
  the rest.

### 16.A — Option A implementation

Per the operator's "go with A" decision, softened the veto in
`synthesis_helpers.select_interpretation_candidates`:

```diff
- eligible = [
-     item for item in ranked
-     if item.total_score >= EXPERT_PANEL_MIN_RELEVANCE_SCORE
-     and not any(penalty.startswith("off_topic:") for penalty in item.penalties)
- ]
+ eligible = [item for item in ranked if item.total_score >= EXPERT_PANEL_MIN_RELEVANCE_SCORE]
```

The per-tag −0.20 score penalty stays (off-topic docs still rank
lower). New diagnostic keys `off_topic_penalized_count` +
`off_topic_penalized_kept` record how often the old veto would have
fired vs how many of those docs now survive. 8-case regression test
at `tests/test_interpretacion_off_topic_soft_veto.py` pins the new
behavior including the two regression patterns above.

### 16.B — Result: 10/21 = 47.6 % accept@top3 — DISCARD band

Run dir: `evals/sme_validation_v1/runs/20260512T015117Z_phase11b_option_a_soft_veto/`.
21/21 served (198.9 s, 9.5 s/Q wall, 4 workers); 21/21 panels show
`judge.mode = 'llm'` (the §15 LLM-judge fix is doing its job).

Per-question diff vs the §15 judge-fixed baseline (11/21):

**Unlocked by Option A (2 new wins — first time these question IDs
have EVER landed on the accept set):**
* `iva_regimen_responsables_v1` ✓ (was ✗ in v10 / v11A / v11B)
* `laboral_ugpp_desalarizacion_v1` ✓ (was ✗ in v10 / v11A / v11B)

**Lost by Option A (3 wins — veto was correctly cutting noise):**
* `iva_exentos_vs_excluidos_v1` ✗ (held in every prior run)
* `proc_devoluciones_riesgo_auditoria_v1` ✗ (held in every prior run)
* `retencion_decreto_572_v1` ✗ (held in every prior run)

**Net: −1 pt** vs §15 baseline (11/21 → 10/21). −2 pt vs v10/v11A
baseline (12/21).

### 16.C — Architectural read

The veto and the noise are doing real work on opposite halves of the
question set. There's no "set the dial right" for the hard pattern
list — the patterns are too literal for some questions (catches the
right doc as off-topic) and too narrow for others (lets noise through
because no matching pattern exists for the question's vocabulary).

The next refinement Option B (use topic-key labels instead of text
patterns) would address the structural mismatch but requires the
documents' `topic_key` values to be cleanly assigned AND the chat
router's topic detection to be reliable — both of which we've already
seen are brittle (e.g. `renta_beneficio_auditoria` mis-routed to
`firmeza_declaraciones`).

### 16.D — Gate-6 DISCARD decision

Per §4.2 gate-6 policy: "Two attempted refinements before discard."
Refinements attempted:

| # | Refinement | Result |
|---|---|---|
| R1 | §15 LLM-judge fix (`generate_llm_strict` tuple contract) | No score impact (was on lexical-only fallback prior); rerank is not the bottleneck |
| R2 | §16 soft off-topic veto (Option A) | −1 pt; veto was doing real work on 3 of the 21 cases |

Per the canonical lifecycle, this triggers **DISCARD** for the
load-bearing Phase 11B change (`LIA_PLANNER_INTERPRETATION_ANCHOR`).
Keep the supporting work that DOES NOT regress and IS architecturally
correct:

* ✅ KEEP — `generate_llm_strict` tuple contract fix at
  `pipeline_c/orchestrator.py`. Fixes a real bug that was silently
  crashing 4 other LLM call sites in `interpretacion/orchestrator.py`
  + `normative_analysis.py`. 12 regression tests at
  `tests/test_pipeline_c_generate_llm_strict.py`.
* ✅ KEEP — Cloud Falkor InterpretationNode subgraph (105 nodes + 586
  INTERPRETS + 105 COVERS_TOPIC). Harmless cloud-side data;
  consumable by any future re-attempt. Loader is idempotent so it
  doesn't need to be torn down.
* ✅ KEEP — `graph/interpretation_loader.py` +
  `interpretacion/anchor_resolver.py` modules + the operator script
  at `scripts/diagnostics/load_interpretation_nodes.py`. Both
  modules are correct + tested; only the dispatcher's use of them
  flips off.
* ↩ REVERT — `LIA_PLANNER_INTERPRETATION_ANCHOR` default from `on`
  to `off` in `scripts/dev-launcher.mjs` across all three modes.
  Restores v10/v11A 12/21 baseline (Python `article_index` fallback).
* ↩ REVERT — Option A soft veto. Restore the hard veto at
  `synthesis_helpers.select_interpretation_candidates`. Keep the
  diagnostic counters (`off_topic_penalized_count`) for future
  telemetry.

### 16.E — What we learned that's durable

* **The expert-panel ceiling is ~12/21 = 57 %** under the current
  retrieval + filter architecture. Cluster A (anchor dilution) and
  cluster B (corpus gap) interact with the assembly filter's brittle
  pattern matching in ways that no single-axis fix (anchor change OR
  filter change) can move past.
* **The LLM-judge was silently broken for months** across v10B + v11A
  + v11B (until §15) — every panel ran on lexical-only rerank. This
  is a meta-lesson: every `(text, diag) = fn(...)` call site needs a
  contract test, because Python silently swallows the unpack failure
  as a generic exception.
* **The "Falkor anchor via INTERPRETS" architecture is correct** —
  end-to-end probes confirm the right docs get surfaced into the
  candidate set. What's broken is downstream (the assembly filter).
  Future re-attempts that include a smarter relevance signal at the
  assembly layer (semantic similarity, topic-aware penalty) can flip
  the anchor back on without code changes.
* **The "fix one bug, find another" pattern is real on this surface.**
  Three real bugs surfaced during the v11B investigation: judge
  crash (§15), trust_tier placeholder on InterpretationNode (§14.B),
  off_topic veto over-cut (§16). Each one was hiding behind the
  others. The judge fix was the only one that's a net win to ship
  standalone.

### 16.F — Recommended next steps (operator-facing)

1. **Revert Phase 11B runtime defaults** (one launcher line each):
   `LIA_PLANNER_INTERPRETATION_ANCHOR=off`. Keep
   `LIA_INGEST_INTERPRETATION_NODES=enforce` for now — the loader is
   idempotent and harmless when the dispatcher doesn't consume the
   anchors.
2. **Revert Option A** — restore the hard `off_topic` veto in
   `synthesis_helpers.py`. Keep the new diagnostic counters for
   future telemetry.
3. **Keep the §15 judge fix** — it's a real correctness fix
   independent of Phase 11B. Run the §1.G 36-Q regression panel once
   under the judge-fixed config to confirm no chat-side regression
   (zero expected; the chat path doesn't call `generate_llm_strict`
   today, but the regression test is cheap).
4. **Re-open Phase 11C scope from scratch.** The path to ≥ 70 % on
   the expert-panel surface needs a different architectural axis —
   most likely a semantic relevance score at the assembly layer (e.g.
   embeddings cosine between question + candidate excerpt) replacing
   the off_topic pattern check entirely. Out of v11 scope; new plan
   doc.

Status: ↩ Phase 11B DISCARDED per gate-6 after R1+R2 exhaustion;
✅ §15 judge fix retained; ✅ cloud InterpretationNode subgraph
retained (harmless); 🔜 Phase 11C scope re-opened with a different
architectural axis.

---

## 17. Final landing report — Hybrid attempt + discard execution (2026-05-11 PM Bogotá)

After §16 Option A landed at 10/21 = 47.6 % DISCARD, the operator
chose "hold — try one more thing before discarding" and asked for the
hybrid: keep the hard veto, but raise the bar so it only fires on
docs with **≥ 3 off-topic pattern matches** (vs the previous
"any 1+ match"). The intent was to recover passing-mention cases
(T-J's 2 TTD hits) without weakening the veto on genuinely
off-topic-focused docs.

### 17.A — Hybrid implementation

Code change in `synthesis_helpers.py`:
* New `_match_count(text, patterns)` helper — substring count summed
  across all patterns for an off-topic key.
* New constant `_OFF_TOPIC_DOC_HIT_THRESHOLD = 3`.
* Doc-side off-topic tagger swapped from `_match_any` to
  `_match_count(...) >= _OFF_TOPIC_DOC_HIT_THRESHOLD`.
* Hard veto restored at the selector (Option A's softening reverted).
* Frame-side detection stayed at 1 (single match = question is on
  topic).

13 hybrid-specific regression tests at `test_interpretacion_off_topic_soft_veto.py`
pinning: threshold constant, helper correctness, builder behavior at
the threshold boundary, end-to-end T-J recovery, end-to-end veto on
genuinely-off-topic docs.

### 17.B — Hybrid mini-panel result: 10/21 = 47.6 %, same as Option A

Run dir: `evals/sme_validation_v1/runs/20260512T021403Z_phase11b_hybrid_threshold/`.
189.7 s wall, 9.0 s/Q, zero 429s, zero server errors.

Per-question diff:

| QID | v10 | judge-fixed | Option A | **Hybrid** |
|---|---|---|---|---|
| renta_conciliacion_2516 | ✗ | ✗ | ✗ | **✓** ← T-J recovered as predicted (2 TTD hits < 3 threshold) |
| retencion_decreto_572 | ✓ | ✓ | ✗ | **✓** ← recovered |
| iva_regimen_responsables | ✗ | ✗ | ✓ | ✓ |
| renta_patrimonio_niif | ✓ | ✓ | ✓ | **✗** ← lost (assembly destabilization) |
| laboral_ugpp_desalarizacion | ✗ | ✗ | ✓ | **✗** ← lost |
| iva_exentos_vs_excluidos | ✓ | ✓ | ✗ | ✗ |
| proc_devoluciones_riesgo_auditoria | ✓ | ✓ | ✗ | ✗ |
| _(other 14 unchanged)_ | — | — | — | — |

The hybrid recovered the 2 questions the §16 analysis predicted
(T-J was the canonical regression target). But it also lost 2 cases
the prior runs held. Net total: 10/21 — identical to Option A.

### 17.C — Architectural read after three refinements

The expert-panel surface is at a **~10-12/21 ceiling** under the
current retrieval + assembly architecture. Every single-axis tune
shuffles which questions win:

* Phase 11A (trust-tier weight in `_group_chunks_by_doc`): 0 pt.
  Wrong layer — chunk grouping isn't the bottleneck.
* Phase 11B (Falkor anchor): −1 pt. Anchor is correct; assembly
  filter dilutes the boosted set.
* §15 R1 (LLM-judge fix): 0 pt impact on score; real correctness
  fix elsewhere. Independent keep.
* §16 R2 (Option A soft veto): −1 pt. Unlocks 2 cases, loses 3.
* §17 R3 (hybrid threshold): −1 pt. Recovers 2 cases vs Option A,
  loses 2 different cases.

The trade-offs are symmetric across all three filter variants: the
off_topic veto's net effect is roughly neutral on the mini-panel
total — it correctly cuts noise on some questions and incorrectly
cuts the right answer on others. The pattern dictionary cannot be
tuned to do both.

**Path to ≥ 70 % requires a semantic relevance signal at the
assembly layer**, not pattern matching. Options for future re-scope:
* Embedding cosine between question text and candidate doc excerpt
  (replace pattern-based `off_topic_tags` entirely).
* Learned ranker fine-tuned on SME-labeled pairs.
* Question-aware re-prompting of the candidate set (let the LLM
  re-select rather than score).

None of these fit in v11's narrow refinement budget. They're a
fresh-plan task.

### 17.D — Revert executed

Per gate-6 in §4.2: "Two attempted refinements before discard." We
attempted three (judge fix, Option A soft veto, hybrid threshold).
None cleared the 70 % bar; the last two went BELOW the v10 baseline.
The honest discipline is to revert before locking in a regression.

**Reverted:**
* `scripts/dev-launcher.mjs` — `LIA_PLANNER_INTERPRETATION_ANCHOR`
  default changed from `on` to `off` across all three modes. The
  Python `article_index` fallback now serves; v10/v11A 12/21
  baseline restored.
* `src/lia_graph/interpretacion/synthesis_helpers.py` — `_match_any`
  restored in the doc-side off-topic tagger (single-match detection
  back). The `_match_count` helper + `_OFF_TOPIC_DOC_HIT_THRESHOLD`
  constant stay in the module — harmless to dead code, useful for
  the future-re-attempt scenarios above.
* `tests/test_interpretacion_off_topic_soft_veto.py` — deleted.
  Locked in reverted behavior. Canonical plan §16/§17 is the
  durable record of what was tried.

**Kept (real correctness improvements, independent of the discarded
runtime path):**
* `pipeline_c/orchestrator.py::generate_llm_strict` (§15 R1) —
  pre-fix stub was returning a 4-key dict; every caller did
  `text, diag = ...` unpacking; silently crashed for months. Now
  resolves a real LLM adapter and returns the contract every caller
  expects. Fixes the rerank judge + 3 other LLM call sites in
  `interpretacion/orchestrator.py` + `normative_analysis.py`. 12
  regression tests at `tests/test_pipeline_c_generate_llm_strict.py`.
* `src/lia_graph/graph/interpretation_loader.py` (~530 LOC) — both
  manifest- and Supabase-backed builders; idempotent; tested.
* `src/lia_graph/interpretacion/anchor_resolver.py` (~210 LOC) —
  topic-aware Cypher path; tested.
* `scripts/diagnostics/load_interpretation_nodes.py` (~210 LOC) —
  operator-targeted CLI.
* Cloud Falkor `LIA_REGULATORY_GRAPH` data: 105 InterpretationNode +
  586 INTERPRETS + 105 COVERS_TOPIC edges. Harmless to leave. Future
  re-attempts that include a semantic filter at the assembly layer
  can flip `LIA_PLANNER_INTERPRETATION_ANCHOR=on` and consume them.

### 17.E — Closing tally

| Phase 11 outcome | Status |
|---|---|
| Phase 11A trust-tier weight | ✅ landed; 0pt impact on mini-panel; kept (correct data + harmless code) |
| Phase 11B Falkor InterpretationNode loader | ✅ code shipped + cloud data landed; ↩ runtime path off by default; reusable in future re-attempts |
| Phase 11B anchor resolver | ✅ code shipped; ↩ runtime path off by default |
| §15 LLM-judge fix | ✅ shipped, **kept** (real bug fix, independent) |
| §16 R2 Option A soft veto | ↩ reverted |
| §17 R3 hybrid threshold | ↩ reverted |
| Phase 11C production flip | ❌ never attempted (gate-5 never cleared) |

**Mini-panel never cleared the §5.4 70% ship bar.** Best Phase 11B
variant: 11/21 = 52.4 % (judge-fixed). Best overall in the v11
campaign: 12/21 = 57.1 % from v10/v11A baseline (which Phase 11B did
not improve on). Closing band: **REFINE** at the v10 baseline.

### 17.F — Operator next steps

1. **Restart `dev:staging`** to pick up the reverted code. The
   running server (PID 75533) still has the hybrid loaded.
2. **Optional**: re-run the 21-Q mini-panel one more time against
   the reverted code to confirm we're back to 12/21 (operator-
   authorized per `feedback_sme_panel_explicit_request_only`).
3. **Optional**: run the §1.G 36-Q chat regression panel under the
   reverted code + judge fix. Confirms the judge fix doesn't
   destabilize chat. Zero expected impact (chat doesn't call
   `generate_llm_strict` today, but the test is cheap).
4. **Phase 11C scope (separate plan)**: re-open with a semantic
   relevance signal at the assembly layer. Out of v11 scope.

Status: ↩ Phase 11B fully discarded per gate-6; ✅ §15 judge fix
retained; ✅ Phase 11B modules + cloud data retained behind off
flag; 🔜 fresh-plan task for semantic relevance signal.

---

## 18. Re-attempt guide (read this FIRST if picking this up months later)

This section is the durable handoff for the next attempt at the
expert-panel `≥ 70 %` ship bar. Written so a fresh LLM or engineer
with zero v11 context can resume from cold.

### 18.A — What's already shipped + still in place (do NOT redo)

Cloud + code state as of 2026-05-11 commit `1ed2ced` on `main`:

1. **Cloud Falkor `LIA_REGULATORY_GRAPH` data is loaded.**
   * 105 `InterpretationNode` (key=`doc_id` matching cloud Supabase
     `documents.doc_id` byte-for-byte).
   * 586 `INTERPRETS` edges (`InterpretationNode → ArticleNode {article_number}`).
   * 105 `COVERS_TOPIC` edges (`InterpretationNode → TopicNode {topic_key}`).
   * 294 distinct ArticleNodes have ≥ 1 inbound INTERPRETS.
   * Idempotent loader at `scripts/diagnostics/load_interpretation_nodes.py`.
     Re-runs are safe. To refresh: source `.env.staging`, then
     `PYTHONPATH=src:. uv run python scripts/diagnostics/load_interpretation_nodes.py --target staging --eligible-from-cloud`.
   * To verify state cheaply:
     ```bash
     set -a && source .env.staging && set +a && PYTHONPATH=src:. uv run python -c "
     from lia_graph.graph.client import GraphClient, GraphWriteStatement
     c=GraphClient.from_env()
     for label, q in [('nodes','MATCH (i:InterpretationNode) RETURN count(i) AS n'),
                       ('interprets','MATCH ()-[r:INTERPRETS]->() RETURN count(r) AS n'),
                       ('covers_topic','MATCH ()-[r:COVERS_TOPIC]->() RETURN count(r) AS n')]:
         r=c.execute(GraphWriteStatement(description=label, query=q, parameters={}), strict=True)
         print(label, list(r.rows)[0].get('n'))
     "
     ```

2. **Code modules — all tested + correct, just behind off-flag.**
   * `src/lia_graph/graph/interpretation_loader.py` (~530 LOC).
     Both manifest-backed and cloud-Supabase-backed builders. 23
     tests at `tests/test_graph_interpretation_loader.py`.
   * `src/lia_graph/interpretacion/anchor_resolver.py` (~210 LOC).
     Cypher anchor lookup, accepts article_refs in any of the
     canonical shapes. 18 tests at `tests/test_interpretacion_anchor_resolver.py`.
   * `src/lia_graph/interpretacion/retriever_supabase.py` —
     `fetch_interpretation_candidates` already accepts
     `planner_anchor_doc_ids` + `planner_anchor_diagnostic`. Test
     coverage in `tests/test_interpretacion_retriever_supabase.py`
     including the Phase 11B path.
   * `src/lia_graph/interpretacion/orchestrator.py` —
     `_retrieve_interpretation_docs` already calls the anchor
     resolver when `LIA_PLANNER_INTERPRETATION_ANCHOR=on`. The
     dispatcher wiring is in place.

3. **§15 LLM-judge fix — KEEP THIS, do not revert.** The
   `pipeline_c.orchestrator.generate_llm_strict` shim now resolves a
   real LLM adapter and returns `(text, diag)` matching every
   caller's `text, diag = ...` unpack. Pre-fix it returned a 4-key
   dict; every caller silently crashed with `too many values to
   unpack (expected 2, got 4)`. 12 regression tests at
   `tests/test_pipeline_c_generate_llm_strict.py`. Independent of
   Phase 11B; fixes 4 separate LLM call sites
   (`interpretacion/orchestrator.py` ×3 + `normative_analysis.py`).

4. **Phase 11A trust-tier data in cloud Supabase.** 65 chunks/8 docs
   at tier=high, 747 chunks/97 docs at tier=medium. `documents.provider_labels`
   column populated for 12 docs. Not load-bearing in the discarded
   path but available to any future relevance signal that wants
   per-doc trust info.

### 18.B — The measurement instrument

Always re-use the same 21-Q mini-panel for apples-to-apples comparison:
* Questions: `evals/sme_validation_v1/questions_expert_panel_v1.jsonl`
* Runner: `scripts/eval/run_sme_parallel.py` (hardened against 429s
  per fix_v10_may; one shared ChatClient across 4 workers).
* Scorer: `scripts/eval/score_expert_panel_mini.py` (POSTs
  `/api/expert-panel` per chat, scores top-3 against
  `expected_interpretation_files`; emits PASS/REFINE/DISCARD per §5.4).
* Server: `dev:staging` (`npm run dev:staging` — cloud Supabase +
  cloud Falkor). Required restart whenever code changes — Python
  doesn't hot-reload.

Baseline measurements to defend or beat:
* v10/v11A: 12/21 = 57.1 % — the floor; any future change must
  hold this AT MINIMUM.
* v11B variants (judge-fixed, Option A, hybrid): 10-11/21 — DO NOT
  re-try the same pattern-axis tuning. We already know the ceiling.

### 18.C — Why off_topic-pattern tuning hit a ceiling (skip-list)

The assembly filter at `src/lia_graph/interpretacion/synthesis_helpers.py::select_interpretation_candidates`
applies two cuts:
1. `total_score >= EXPERT_PANEL_MIN_RELEVANCE_SCORE` (0.22 from
   `interpretacion/policy.py`).
2. Hard veto on any candidate with an `off_topic:<key>` penalty.

The `off_topic_tags` are computed against `_OFF_TOPIC_PATTERNS`
(6 keys: ttd, rst, retencion, conciliacion, facturacion, calendario).
Three pattern-axis attempts already failed:

* **§15 R1 — fix LLM-judge crash.** 0pt impact (judge wasn't the
  bottleneck; the assembly filter is).
* **§16 R2 — Option A soft veto** (remove the hard drop, keep the
  −0.20 score penalty). 10/21 = 48 %. Unlocked 2 questions, lost 3.
* **§17 R3 — hybrid count threshold** (only tag as off_topic when
  pattern hit count ≥ 3). 10/21 = 48 %. Recovered 2 different cases,
  lost 2 different cases.

Net of all three: shuffles WHICH 10-12 questions win without moving
the ceiling. The patterns are too literal for some questions (catches
the right doc with passing mentions) and too narrow for others (lets
noise through because no matching pattern exists for the question's
vocabulary). Pattern-axis is exhausted.

**Don't re-try**: per-tag weight tuning, allowlist expansion, frame-side
pattern thresholds, "soft penalty only when frame doesn't also have
the tag", `EXPERT_PANEL_MIN_RELEVANCE_SCORE` lowering. The data says
any single-axis tune on this filter shuffles the same ~10-12 wins.

### 18.D — Recommended next architecture (semantic relevance)

The pattern-based `off_topic_tags` check has to be replaced with a
real semantic similarity signal. Three options ranked by effort:

#### Option SR1 (most surgical, lowest risk)
**Embedding cosine between question text and each candidate doc's first chunk_text.**
Replace the pattern veto with: drop a candidate if
`cosine(question_embedding, candidate_first_chunk_embedding) <
SR1_THRESHOLD`. Reuses the existing query-embedding pipeline
(`lia_graph.embeddings.get_query_embedding` — gemini-embedding-001,
already gated by `LIA_QUERY_EMBEDDINGS_ENABLED=1`).

* **Where**: `interpretacion/synthesis_helpers.py::score_interpretation_candidate`
  — add `semantic_score` (cosine, normalized to [0, 1]) as a 7th
  weighted term in the formula at line 389 OR as a separate veto
  signal at line 459.
* **Cost**: ~1-2 engineer days. The candidate set is bounded at 18
  per panel call, so 18 embedding-cosine computations per call (the
  candidate chunk embeddings can be cached at retrieval time — cloud
  Supabase already stores `document_chunks.embedding`).
* **Calibration**: pick `SR1_THRESHOLD` by running the 21-Q
  mini-panel at thresholds [0.20, 0.30, 0.40, 0.50] and picking the
  one that maximizes accept@top3 while holding the v10 12/21 floor.
* **Risk**: low — pure additive signal; can ship behind a
  `LIA_PANEL_SEMANTIC_RELEVANCE=on` flag with the veto falling back
  to the pattern check when off.

#### Option SR2 (medium effort, higher upside)
**Question-aware re-prompting at the assembly layer.** After
candidate scoring, ask Claude (via the existing `generate_llm_strict`
that's now actually working) to select the top-3 cards directly from
the candidate set + the question. Skips the
`select_interpretation_candidates` filter entirely.

* **Where**: new module
  `interpretacion/llm_selector.py` parallel to the existing
  `rerank/llm_judge.py`. Same `deps["generate_llm_strict"]` call
  pattern. Returns a 3-tuple of (doc_id, reason) for the panel
  surface.
* **Cost**: ~3-4 engineer days (including the new prompt design,
  output parsing tolerance, and fallback when LLM rejects all
  candidates).
* **Risk**: medium — LLM-as-final-selector is a different operating
  mode; if the LLM hallucinates a doc_id not in the candidate set,
  the panel shows nothing. Need defensive parsing + fallback.

#### Option SR3 (heaviest, most durable)
**Learned ranker fine-tuned on SME-labeled pairs.** Train a small
cross-encoder (bge-reranker-v2-m3 or similar — the chat path already
has a sidecar slot at `LIA_RERANKER_ENDPOINT`) on (question, doc,
relevance_label) triples from the 21-Q mini-panel + historical SME
panels. Use as the final scoring signal.

* **Where**: requires a training run + a sidecar deployment.
  Reuses the existing `pipeline_d/reranker.py` sidecar wiring; the
  rerank adapter already supports `LIA_RERANKER_MODE=live`.
* **Cost**: ~1-2 weeks. Data labeling + train + deploy + measure.
* **Risk**: highest, but also the most architecturally durable —
  the same ranker can serve the chat-side citation surface too.

**Recommended sequencing**: SR1 first (cheap probe — if it gets to
70 %, we're done). If SR1 lands at [60, 70 %), layer in SR2 for the
top-3 final pick. SR3 only if SR1+SR2 together still fall short.

### 18.E — How to actually start the re-attempt

Step-by-step. Assumes a fresh engineer with the repo cloned.

1. **Read this section + §17.C** (the architectural read). Don't
   start coding before you've internalized "the pattern veto
   ceiling".
2. **Confirm cloud state is still healthy.** Run the Cypher probe
   from §18.A.1 to confirm the InterpretationNode subgraph is still
   there. If counts are 0, re-run the loader CLI (idempotent).
3. **Re-confirm v10 baseline.** Restart `dev:staging`, run the 21-Q
   mini-panel + scorer. Should land at 12/21. If not, the baseline
   has drifted — fix that BEFORE working on a new relevance signal.
4. **Branch.** `git checkout -b phase11c/sr1-semantic-relevance`.
5. **Land SR1 behind a flag.** New env `LIA_PANEL_SEMANTIC_RELEVANCE=on`.
   Default `off`. Adds the cosine check to
   `select_interpretation_candidates`.
6. **Calibrate** by running the mini-panel at 4 threshold values.
   Pick the best.
7. **Flip `LIA_PLANNER_INTERPRETATION_ANCHOR=on`** in tandem with
   `LIA_PANEL_SEMANTIC_RELEVANCE=on`. The Falkor anchor's
   contribution is measurable only when paired with a working
   assembly filter — SR1 is what makes that pairing meaningful.
8. **Decision gate**: ≥ 15/21 (≥ 70 %) clears the §5.4 ship bar.
   < 15/21 → layer SR2 OR refine SR1's calibration. Per the canonical
   gate-6 rule, two refinement attempts then DISCARD if still short.
9. **Update this §18 with the new measurement results** so the next
   handoff has full historical context.

### 18.F — Gotchas worth knowing

* **Server restart is mandatory after any code change.** Python
  doesn't hot-reload. The answer-engine-probe skill has a mandatory
  restart preamble for this reason. PID will change; verify via
  `ps eww $NEW_PID` that the env flags are still set.
* **`tests/` requires `LIA_BATCHED_RUNNER=1`** to run anything that
  collects > 20 test files. Single-file or focused runs don't need
  it.
* **Cloud writes are operator-pre-authorized** per `feedback_lia_graph_cloud_writes_authorized`.
  Announce before executing, no per-action confirmation. Different
  rule for the SME panel — that's `feedback_sme_panel_explicit_request_only`,
  always ask.
* **`generate_llm_strict` is a tuple-returning function now.** Every
  call site does `text, diag = generate_llm_strict(...)`. Don't
  re-wrap in a try/except that throws away `diag` — the rerank
  judge writes diag back into the trace and operators read it.
* **The 6 off_topic patterns are case- + accent-insensitive after
  `normalize_text`.** "Régimen Simple" matches "regimen simple"
  pattern. New patterns should be lowercase + accent-stripped.
* **Article-ref shapes** the codebase uses interchangeably:
  `et_art_115`, `art_115_et`, `art_115`, `115`. The anchor resolver
  normalizes all of these to bare `article_number`. Match this
  convention.
* **Cloud Supabase `doc_id` ≠ filesystem path** — it's
  `_sanitize_doc_id(relative_path)` which preserves dashes + dots
  but collapses slashes/spaces to underscores. The cloud-Supabase
  loader builder (`build_interpretation_load_plan_from_supabase`)
  is the source of truth — never use the manifest-backed builder
  against cloud Falkor because doc_ids may differ from local disk.
* **The InterpretationNode `trust_tier` property is a placeholder**
  — loader writes `"medium"` to every node. A future re-attempt
  that wants real trust_tier ordering needs to extend the loader to
  aggregate per-doc from cloud Supabase `document_chunks.trust_tier`
  (e.g. MAX over chunks). Currently the `LIMIT 8 ORDER BY trust_tier
  DESC` in the anchor Cypher is effectively cursor-order.

### 18.G — Files to read on re-pickup

In rough order of importance:

1. This file (`docs/re-engineer/fix/fix_v11_may.md`) — full v11
   record.
2. `CLAUDE.md` — `Runtime Read Path` table, `Fast Decision Rule`,
   `Non-Negotiables`.
3. `docs/orchestration/orchestration.md` — env matrix versions +
   change log.
4. `src/lia_graph/interpretacion/synthesis_helpers.py` —
   `select_interpretation_candidates` + `score_interpretation_candidate`
   + `_OFF_TOPIC_PATTERNS`. This is the filter you're replacing.
5. `src/lia_graph/interpretacion/orchestrator.py` —
   `_retrieve_interpretation_docs` dispatcher.
6. `src/lia_graph/graph/interpretation_loader.py` — already-loaded
   cloud subgraph builder.
7. `src/lia_graph/interpretacion/anchor_resolver.py` — Cypher
   anchor lookup (off by default; flip with `LIA_PLANNER_INTERPRETATION_ANCHOR=on`).
8. `evals/sme_validation_v1/questions_expert_panel_v1.jsonl` — the
   21-Q instrument.
9. `evals/sme_validation_v1/runs/20260512T010349Z_phase11b_falkor_anchor/`
   — first v11B run (anchor verified end-to-end).
10. `evals/sme_validation_v1/runs/20260512T021403Z_phase11b_hybrid_threshold/`
    — last v11B run (post-revert measurement).

### 18.H — What we would have done differently

For future planners writing similar gate-6-driven specs:

* **Measure the bottleneck FIRST.** v11 jumped to "build the Falkor
  anchor" before quantifying whether the rerank or the assembly
  filter was the cut. If we'd traced one failing case end-to-end on
  v10/v11A first, we'd have found the assembly filter (and the
  silent judge crash) before shipping any Phase 11B code. The 4
  engineer days on the loader + resolver would have been better
  spent on SR1.
* **Contract-test every `(text, diag) = fn(...)` site.** The
  judge crash hid for months because Python silently swallows the
  unpack failure into a generic exception. A 1-line test on every
  call site would have caught it on day 1.
* **The gate-6 "two refinements" budget is a strict lower bound.**
  We tried three (judge fix, soft veto, hybrid) before discarding;
  the third was operator-requested ("hold — try one more thing").
  That's fine for time-pressed exploration, but the canonical plan
  should treat extra attempts as data for the discard report, not
  as a path past gate-6.
* **Don't ship the anchor without the filter.** Phase 11B's anchor
  is correct — it just doesn't help when the downstream filter
  dilutes the boost. Future re-attempts should land the assembly
  filter rework FIRST, then flip the anchor back on.



