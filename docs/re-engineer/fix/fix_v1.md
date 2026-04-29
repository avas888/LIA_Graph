# fix_v1.md — quality regression discovered post next_v7 P1+P8, hand-off for fresh agent

> **Drafted 2026-04-29 ~11:15 AM Bogotá** by claude-opus-4-7,
> immediately after running the §1.G 36-question SME panel against
> production cloud post next_v7 P1 (vigencia-history promotion) +
> P8 (norm_citations backfill). Result: **8/36 served_acceptable+
> vs the 21/36 prior baseline — a 13-question regression, 8 of
> which dropped from served-strong/acceptable to served_off_topic.**
>
> **Audience:** any zero-context agent (fresh LLM or engineer) who
> picks up this work next.
>
> **What this doc is:** the diagnostic hand-off. It tells you what
> we observed, what hypotheses are plausible, what code surface to
> look at, what NOT to do, and how to run the diagnostic itself.
> No fixes are proposed yet — the operator's directive was
> **"STOP and REVIEW"** before any patch. Patch only after the
> diagnostic in §6 isolates which hypothesis is correct.

---

## 0. If you are a zero-context agent — read this first

You are arriving after a long session that just shipped 13 commits
on `main` (see §10). The last one (`f66a7ff`) closed out the
next_v7 cycle on the engineering side. We then ran the **§1.G 36Q
SME panel** as the quality gate against current production cloud,
and the result regressed badly:

| Class | 2026-04-27 baseline | 2026-04-29 today | Δ |
|---|---|---|---|
| served_strong | 9 | 2 | **−7** |
| served_acceptable | 12 | 6 | **−6** |
| served_weak | 2 | 3 | +1 |
| served_off_topic | 4 | 14 | **+10** |
| refused | 9 | 5 | −4 |
| server_error | 0 | 6 | **+6** |
| **served_acceptable+** | **21/36** | **8/36** | **−13** |

**Stop. Diagnose. Do not patch yet.**

The operator memory says **"diagnose before intervene"**
(`feedback_diagnose_before_intervene`). RAG is complex science;
"improvements" misbehave and regress all the time
(`CLAUDE.md` non-negotiable on the six-gate lifecycle). 8/36 is a
real regression, but the cause may be a single calibration knob,
a corpus gap, or a router-keyword shift — and the wrong fix locks
in the wrong story.

**Before doing anything else, read these in order:**

1. **`CLAUDE.md`** + **`AGENTS.md`** — repo-level operating guides.
   Pay attention to the **"Fail Fast, Fix Fast — operations canon"**
   section (rules 1-8, esp. rule 6 *"Diagnose at the audit layer,
   not the symptom"*).
2. **`docs/re-engineer/next_v7.md`** — the 7-step plan that landed
   today.
3. **`docs/re-engineer/state_next_v7.md`** — running ledger of what
   shipped today, attempt-by-attempt.
4. **This file (`docs/re-engineer/fix/fix_v1.md`)** — §1 (goal vs
   reality), §3 (per-question diff), §5 (hypotheses), §6 (HOW to
   diagnose), §7 (what NOT to do).
5. **`docs/learnings/retrieval/vigencia-binary-flag-too-coarse.md`**
   — Activity 1's clean before/after measurement showing how a
   binary `vigencia` flag mis-fires; the fix we applied today is
   the unconditional filter from that learning, but the cure may
   have created a new shape of regression.
6. **`docs/learnings/retrieval/coherence-gate-and-contamination.md`**
   — why the v6 evidence-coherence gate exists, what trade-off it
   makes (kills weak chunks → fewer contamination cases AND fewer
   primary seeds).
7. **`docs/aa_next/gate_9_threshold_decision.md`** — the closest
   prior precedent for a "is this regression real or measurement
   strictness?" question, including the §8.4 four-criteria gate
   and the per-Q diagnostic surface (`coherence_misaligned`,
   `effective_topic`, etc.).

**Memory-pinned guardrails (do NOT violate):**

* Cloud writes are pre-authorized (`feedback_lia_graph_cloud_writes_authorized`)
  — but write only what diagnostics demand. Don't bulk-rewrite.
* Don't lower aspirational thresholds
  (`feedback_thresholds_no_lower`) — 24/36 stays as the §1.G gate.
  Document any qualitative-pass exception per case.
* Diagnose before intervene (`feedback_diagnose_before_intervene`).
* Each gate evaluates against its own criteria
  (`feedback_gates_evaluate_independently`) — don't trade
  contamination for seed count, etc.
* Plain-language status reports (`feedback_plain_language_communication`).

---

## 1. The cycle goal vs the result

### Stated goal (per `next_v7.md`)

The next_v7 cycle was **P1 — comprehensive cloud promotion + P2-P7
gap-closing extensions**. Quality acceptance criterion came from
the v3 plan (`fixplan_v3.md` §6.2, sub-fix 1B-ε gate-2): the
§1.G 36-question SME panel **must reach ≥ 24/36
served_acceptable+** with **zero ok→zero regressions**, while
preserving the 4/4 contamination-clean count
(Q11/Q16/Q22/Q27).

### What we got

* served_acceptable+: **8/36** (target ≥ 24/36) — **fail by 16**.
* ok→zero regressions: **13** (target 0) — **fail by 13**.
* Contamination 4/4: **not yet measured** in today's run; 4
  contamination Qs are in the panel and 2 of them appear in the
  regressed list (`firmeza_declaraciones_P2`,
  `regimen_sancionatorio_extemporaneidad_P3`).

### What landed BEFORE this run that could plausibly cause it

In the 2 days between the prior baseline (2026-04-27 02:15 UTC,
`evals/sme_validation_v1/runs/20260427T021512Z_activity1_vigencia_filter`)
and today's run, the changes that touch served retrieval:

* Migrations applied to cloud as part of P1 today
  (commit `9cebd4b` push of pending migrations):
  * `20260427000000_topic_boost.sql` — added `filter_topic_boost` to `hybrid_search`.
  * `20260428000000_drop_legacy_hybrid_search.sql` — dropped the
    14-arg overload; closed the §1.G HTTP-500-on-15-of-36 ambiguity bug.
  * `20260429000000_vigencia_filter_unconditional.sql` — **the v2
    binary `vigencia` filter on `document_chunks` is now applied
    UNCONDITIONALLY**. Pre-fix, it was bypassed when
    `filter_effective_date_max` was non-null (which was almost
    always). This was the *intended* cure for the Art. 689-1
    over-citation failure on the 2026-04-26 SME panel.
  * `20260501000000` … `20260501000005` — the v3 vigencia
    subsystem (`norms`, `norm_vigencia_history`, `norm_citations`,
    resolver functions, `chunk_vigencia_gate_at_date` /
    `chunk_vigencia_gate_for_period`, reverify queue).
  * `20260501000006_norms_norm_type_extend.sql` — extended the
    CHECK constraint to admit cst/cco/decreto-subtype values.
* P1 promotion populated `norm_vigencia_history` with **9,322 rows
  (2,349 distinct norm_ids)**.
* P8 backfill populated `norm_citations` with **52,246 rows
  across 8,062 chunks (41% coverage)**.
* P5 mirrored the new vigencia subgraph into cloud Falkor
  (2,905 `(:Norm)` nodes + ~2,548 vigencia edges).
* No retriever code change shipped today.

The new data + the unconditional-filter migration are the only
things that altered the served retrieval surface between
baseline and today. **Everything else (P2/P3/P6/P7) is build-time
scraper / canonicalizer work that affects the next refresh
cycle, not today's served retrieval.**

---

## 2. State of cloud production right now (2026-04-29 ~11:00 AM Bogotá)

| Surface | Rows / count | When written |
|---|---|---|
| `public.norms` (catalog) | 2,905 | today P1 + P8 ancestor walks |
| `public.norm_vigencia_history` | 9,322 / 2,349 distinct norm_ids | today P1 (4 attempts; idempotency-key scoped) |
| `public.norm_citations` | **52,246 across 8,062 chunks** | today P8 |
| `public.document_chunks` | 19,546 | unchanged — 100% embedded |
| `public.documents` | 6,736 | unchanged |
| `public.normative_edges` | 354,025 | unchanged |
| Cloud Falkor `(:Norm)` | 2,905 | today P5 |
| Cloud Falkor vigencia edges (MODIFIED_BY/DEROGATED_BY/etc) | ~2,548 | today P5 |
| Cloud Falkor pre-existing edges (REFERENCES/MODIFIES/TEMA) | ~25k | unchanged |

Important coverage caveat: **`norm_citations` covers 8,062 of
19,546 chunks (41%)**. The other 59% have NO citation rows on
cloud, so the v3 chunk-vigencia gate cannot demote them — they
get the LEFT-JOIN-NULL → demotion factor 1.0 (no demotion) treatment.

**`et.art.689-1` (the famous derogated article):**
* `norm_citations` rows: 3 (only 3 chunks cite it canonically).
* `norm_vigencia_history` rows: **0** (we never extracted a
  veredicto for it during the v6 SUIN cascade — it doesn't appear
  in the 2,349 norms with vigencia history).
* So the v3 chunk-vigencia gate doesn't fire on its 3 citing
  chunks (no vigencia history → no state → demotion 1.0).
* The OLD binary `vigencia` column on `document_chunks` is what
  filters it now (the unconditional-filter migration is doing the
  Art. 689-1 work, NOT the v3 gate).

---

## 3. Per-question diff (prior 2026-04-27 vs today 2026-04-29)

Source files:
* Prior: `evals/sme_validation_v1/runs/20260427T021512Z_activity1_vigencia_filter/`
* Today: `evals/sme_validation_v1/runs/20260429T153845Z_post_p1_v3/`
* Questions input: `evals/sme_validation_v1/questions_2026-04-26.jsonl` (36 lines).

### 3.1 Regressed (acc+ → not acc+) — 13 questions

| qid | prior | now |
|---|---|---|
| beneficio_auditoria_P2 | served_strong | **served_off_topic** |
| beneficio_auditoria_P3 | served_acceptable | **served_off_topic** |
| descuentos_tributarios_renta_P3 | served_strong | **MISSING** (timed out, file deleted in mid-session sweep) |
| dividendos_y_distribucion_utilidades_P2 | served_strong | **served_off_topic** |
| dividendos_y_distribucion_utilidades_P3 | served_acceptable | **served_off_topic** |
| firmeza_declaraciones_P1 | served_strong | **MISSING** (timeout) |
| firmeza_declaraciones_P2 | served_acceptable | **served_off_topic** |
| firmeza_declaraciones_P3 | served_strong | **MISSING** (timeout) |
| impuesto_patrimonio_personas_naturales_P3 | served_acceptable | served_weak |
| perdidas_fiscales_art147_P2 | served_acceptable | refused |
| perdidas_fiscales_art147_P3 | served_acceptable | served_off_topic |
| precios_de_transferencia_P2 | served_acceptable | refused |
| regimen_sancionatorio_extemporaneidad_P3 | served_acceptable | served_off_topic |

### 3.2 Moved within non-acc+ — 8 questions

| qid | prior | now |
|---|---|---|
| beneficio_auditoria_P1 | refused | MISSING (timeout) |
| conciliacion_fiscal_P2 | served_off_topic | MISSING (timeout) |
| conciliacion_fiscal_P3 | served_off_topic | MISSING (timeout) |
| descuentos_tributarios_renta_P1 | refused | served_off_topic |
| perdidas_fiscales_art147_P1 | refused | served_off_topic |
| tarifas_renta_y_ttd_P1 | refused | served_off_topic |
| tarifas_renta_y_ttd_P2 | refused | served_off_topic |
| tarifas_renta_y_ttd_P3 | refused | served_off_topic |

### 3.3 Concrete worked example — `beneficio_auditoria_P2`

The user prompt (full text):

> *"Tengo una SAS comercializadora con ingresos de $2.800 millones
> en 2025 y un impuesto neto de renta de $95 millones. El año
> pasado pagaron $70 millones. Quieren acogerse a beneficio de
> auditoría. ¿Califican? ¿Y si más adelante toca corregir la
> declaración para meter unos ingresos que se omitieron, pierden
> el beneficio?"*

**Prior (2026-04-27, served_strong):**

```
effective_topic = beneficio_auditoria        ← correct
requested_topic = None
topic_adjusted   = True
answer_mode      = graph_native
fallback_reason  = None
compose_quality  = 0.82
confidence       = {score: 0.55, mode: 'topic_misalignment_hedged'}
citations        = 5
answer_markdown[:600] =
  "**Respuestas directas** - **Tengo una SAS comercializadora con
  ingresos de $2.800 millones en 2025 y un impuesto neto de renta de
  $95 millones. El año pasado pagaron $70 millones. Quieren acogerse
  a beneficio de auditoría. ¿Califican?**   - Para calificar al
  beneficio de auditoría, la SAS debe cumplir con los requisitos del
  Estatuto Tributario. El beneficio aplica si el impuesto neto de
  renta se incrementa en los porcentajes establecidos, comparado con
  el impuesto del año anterior. - En este caso, el impuesto neto de
  renta proyectado para 2025 es de $95 millones, y el pagado en 2024
  fue de $..."
```

**Now (2026-04-29, served_off_topic):**

```
effective_topic = declaracion_renta          ← regressed to parent
requested_topic = None
topic_adjusted   = True
answer_mode      = graph_native
fallback_reason  = None
compose_quality  = 0.82                       ← same
confidence       = {score: 0.82, mode: 'graph_artifact_planner_v1'}
citations        = 5                          ← same count
answer_markdown[:600] =
  "**Respuestas directas** - **Tengo una SAS comercializadora con
  ingresos de $2.800 millones en 2025 y un impuesto neto de renta de
  $95 millones... ¿Califican?**   - Cobertura pendiente para esta
  sub-pregunta. Valida el expediente completo con el cliente antes
  de cerrar cualquier recomendación. - **¿Y si más adelante toca
  corregir la declaración para meter unos ingresos que se omitieron,
  pierden el beneficio?**   - Cobertura pendiente para esta
  sub-pregunta. Valida los hechos y la posición ante la DIAN antes
  de dar una..."
```

**Two simultaneous shifts:**
1. `effective_topic` collapsed `beneficio_auditoria → declaracion_renta`.
2. The retriever found nothing specific; the system gracefully
   degraded to "Cobertura pendiente para esta sub-pregunta"
   (a v6-era boilerplate).

**This is NOT classifier-strictness about topic-key string matching.
The answer literally refuses to give substantive advice.**

---

## 4. The 6 server_errors (orthogonal infra issue)

All 6 timed out at 120-180s on the chat endpoint:

| qid | http | latency |
|---|---|---|
| beneficio_auditoria_P1 | -1 | 120010 ms (sequential runner timeout=120) |
| conciliacion_fiscal_P2 | -1 | 180002 ms (parallel runner timeout=180) |
| conciliacion_fiscal_P3 | -1 | 180001 ms |
| descuentos_tributarios_renta_P3 | -1 | 180003 ms |
| firmeza_declaraciones_P1 | -1 | 120002 ms |
| firmeza_declaraciones_P3 | -1 | 180014 ms |

These timed out **in our runner**, but the lia-ui server is single
Python process and these 6 are heavy graph traversals against
cloud Falkor. Suspect `FALKORDB_QUERY_TIMEOUT_SECONDS=30` per
`CLAUDE.md` runtime knobs is enforced per Cypher call, but the
chat handler issues many sequential calls. The 6 errors are
infrastructure resilience, NOT quality. They are listed as
regressed in §3.1 because the prior baseline had them complete in
~30-60s. Investigate as a separate stream after the quality
diagnosis lands.

The 6 per-Q response files **were deleted** in a mid-session
re-run attempt before the operator stop directive. They need to
be re-captured (see §6 step 3).

---

## 5. Hypotheses (not yet distinguished)

### H1 — topic-router shift between 04-27 and today

**Claim.** The topic router or planner started classifying
`beneficio_auditoria` queries (and similar) as
`declaracion_renta`. Once on the parent topic, retrieval finds
nothing specific.

**Plausibility.** The router is keyword-based
(`config/subtopic_taxonomy.json` + `src/lia_graph/topic_router_keywords.py`)
plus an LLM-deferral path (`docs/learnings/retrieval/router-llm-deferral-architecture.md`).
We did NOT change router code today. But:
* `next_v3.md` shipped the conversational-memory staircase
  (`docs/learnings/retrieval/conversational-memory-staircase.md`)
  that uses `prior_topic` from `ConversationState` as a soft
  tiebreaker. If the SME runner's chat session has any state
  leakage, P2/P3 in a topic family might be biased by P1.
* Router output is also influenced by what chunks the topic-boost
  step finds; if vigencia filtering reduced the candidate set,
  the LLM-deferral path may now defer where it did not before.

**What to check.** The `response.diagnostics.router_*` keys —
`router_emit_topic`, `topic_resolution_path`,
`router_subtopic_match_kind`, `llm_deferred`, and the
conversation-state staircase fields. Compare 04-27 vs today on
the same qid.

### H2 — retrieval filter over-aggressive (the new gate or the unconditional filter)

**Claim.** Either the `vigencia_filter_unconditional` migration is
killing chunks the prior run relied on, OR the new
`apply_demotion` post-pass is demoting them. Without those chunks,
the LLM-deferral or coherence gate fires, the topic gets
re-arbitrated to a parent, and the answer is "Cobertura pendiente".

**Plausibility.** This is the *strongest* hypothesis given:
* The unconditional filter went LIVE today (was in shadow before).
* The new `apply_demotion` step requires `norm_citations` rows;
  P8 just populated 52,246 of them today.
* The `beneficio_auditoria_P2` failure mode ("Cobertura pendiente"
  in answer body) is the v6 boilerplate that fires when the
  retriever returns nothing for a sub-question.

**What to check.**
* `response.diagnostics.vigencia_v3_demotion` — present means the
  new gate fired. Read `kept`, `dropped`, `dropped_chunk_ids`.
* `response.diagnostics.retrieval_backend` — should be `supabase`.
* The OLD `vigencia` column filter is in `hybrid_search` itself;
  to test, compare candidate chunk counts pre- and post-filter
  for the same query.
* Toggle `LIA_VIGENCIA_DEMOTION_ENABLED` (or whatever flag gates
  the apply_demotion call in
  `src/lia_graph/pipeline_d/retriever_supabase.py`) OFF and
  re-ask. If quality recovers → H2 confirmed.

### H3 — corpus completeness gap (filter is correct; replacement chunks missing)

**Claim.** We correctly filter derogated norms (`et.art.689-1`,
`Ley 1429/2010`, etc.), but the corpus doesn't have the
REPLACEMENT articles ingested as chunks. So the retriever
correctly avoids stale law and finds no good substitute.

**Plausibility.** Plausible because:
* `et.art.689-1` has 0 vigencia-history rows (we never extracted
  it). The OLD binary `vigencia` column is what filters it.
* `beneficio_auditoria` was reformed by Ley 2155/2021 and Ley
  2277/2022. Are those laws' relevant articles in
  `document_chunks`? Unknown — needs probing.
* `tarifas_renta_y_ttd` has all 3 profiles regressing at once;
  feels like a topic-coverage cliff rather than a per-query bug.

**What to check.**
* For each off_topic Q, identify the canonical articles that
  *should* answer it (per Colombian tax law for 2024-2025). Then
  query `document_chunks` to see if any chunks reference those
  articles' canonical norm_ids in `norm_citations`. If empty →
  corpus gap.
* Cross-check `norm_citations` coverage for the 13 regressed
  topics specifically.

### H4 — coherence gate fires harder on the new (smaller) candidate sets

**Claim.** The v6 evidence-coherence gate
(`LIA_EVIDENCE_COHERENCE_GATE=enforce` since 2026-04-25, per
`scripts/dev-launcher.mjs:290`) is firing more often because
post-vigencia-filter, the candidate chunks no longer cluster as
tightly around the expected topic.

**Plausibility.** The gate tests
`coherence_misaligned`/`coherence_reason=chunks_off_topic`. The
prior 2026-04-26 SME run had 11/12 seed-zero questions with
this exact reason (per
`docs/aa_next/gate_9_threshold_decision.md`). That doc explicitly
notes: "you can't have the contamination win without the
seed-count loss — they are the same mechanism." Today's filter
change may have shifted that trade-off further toward seed-loss.

**What to check.**
* `response.diagnostics.coherence_misaligned` and
  `coherence_reason` per Q.
* Toggle `LIA_EVIDENCE_COHERENCE_GATE=shadow` on the dev server
  and re-run a single regressed Q.

---

## 6. HOW to diagnose (concrete steps for the next agent)

### Step 0 — orient yourself

Working dir: `/Users/ava-sensas/Developer/Lia_Graph`.
Read order is in §0 above.

The dev server may already be running on `127.0.0.1:8787`
(`npm run dev:staging` mode against cloud Postgres + cloud
Falkor). Probe with:

```bash
curl -sS -o /dev/null -w "HTTP=%{http_code}\n" http://127.0.0.1:8787/api/health
pgrep -af "ui_server|lia-ui" 2>&1 | head -3
```

If not running, start it:

```bash
cd /Users/ava-sensas/Developer/Lia_Graph
nohup npm run dev:staging </dev/null > /tmp/devstaging.log 2>&1 &
disown $!
# wait for ready:
until curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8787/api/health 2>&1 | grep -q 200; do sleep 1; done
```

### Step 1 — capture full diagnostics for 3 representative regressed qids

The three qids most worth deep-diving (one per failure shape):

* `beneficio_auditoria_P2` — prior strong → now off_topic (H1+H2 candidates).
* `tarifas_renta_y_ttd_P2` — prior refused → now off_topic
  (cluster failure: all 3 profiles regressed; H3 candidate).
* `firmeza_declaraciones_P2` — prior acceptable → now off_topic,
  contamination Q (H1+H2 candidates).

For each, dump the full `response.diagnostics` block from both
runs side by side:

```python
import json
PRIOR = 'evals/sme_validation_v1/runs/20260427T021512Z_activity1_vigencia_filter'
NOW = 'evals/sme_validation_v1/runs/20260429T153845Z_post_p1_v3'
for qid in ['beneficio_auditoria_P2','tarifas_renta_y_ttd_P2','firmeza_declaraciones_P2']:
    p = json.loads(open(f'{PRIOR}/{qid}.json').read())['response'].get('diagnostics', {})
    n = json.loads(open(f'{NOW}/{qid}.json').read())['response'].get('diagnostics', {})
    print(f'\n=== {qid} ===')
    keys = sorted(set(p) | set(n))
    for k in keys:
        if p.get(k) != n.get(k):
            print(f'  {k}:\n    prior = {p.get(k)}\n    now   = {n.get(k)}')
```

### Step 2 — identify which keys differ

Look in particular at:
* `retrieval_backend`, `graph_backend`
* `vigencia_v3_demotion` (presence + `kept`/`dropped`/`dropped_chunk_ids`)
* `coherence_misaligned`, `coherence_reason`
* `effective_topic`, `topic_resolution_path`, `topic_adjustment_reason`
* `router_subtopic_match_kind`, `subtopic_anchor_keys`
* `llm_deferred`, `llm_resolver_decision`
* `retrieval_sub_topic_intent`
* Any `*_chunk_count` fields (chunks before / after each filter)

### Step 3 — re-capture the 6 server_errors with longer timeout

The 6 missing per-Q files need to be re-run. The dev server may
just need to absorb a heavier traversal. Use the parallel runner
with `--timeout-seconds 300`:

```bash
RUN_DIR=evals/sme_validation_v1/runs/20260429T153845Z_post_p1_v3
PYTHONPATH=src:. uv run python scripts/eval/run_sme_parallel.py \
    --run-dir "$RUN_DIR" --workers 2 --timeout-seconds 300
```

(Workers=2 to reduce concurrent load on the lia-ui process.)

### Step 4 — run the toggle test (H2 isolation)

Restart `npm run dev:staging` with the demotion gate disabled:

```bash
# Find the env knob — search for LIA_VIGENCIA_DEMOTION or apply_demotion's gate.
grep -rnE "LIA_VIGENCIA|apply_demotion" src/lia_graph/pipeline_d/retriever_supabase.py
```

If a knob exists, set it to `off` (or whatever the negative state
is) in `.env.local` (NOT committed; this is a probe), restart the
dev server, re-run the 3 representative qids, compare answers.
If they recover → H2 confirmed.

If no knob exists, add one in
`src/lia_graph/pipeline_d/retriever_supabase.py` around line
525-555 (where `apply_demotion` is called) gated on a new
`LIA_VIGENCIA_DEMOTION_ENABLED` env. Default `on`. This is a
~10-line change; do not commit until it's clear we'll keep it.

### Step 5 — corpus probe (H3 isolation)

For each of the 13 regressed qids, identify which canonical
articles SHOULD answer the question (the SME presumably had
target citations in mind when authoring the panel). Then probe:

```python
# Per qid, list the chunks whose norm_citations include the expected anchor norms.
from lia_graph.supabase_client import create_supabase_client_for_target
c = create_supabase_client_for_target('production')
expected = ['et.art.689', 'ley.2155.2021.art.51']  # example for beneficio_auditoria post-reform
for n in expected:
    r = c.table('norm_citations').select('chunk_id, role, anchor_strength').eq('norm_id', n).execute()
    print(f'{n}: {len(r.data)} chunks; sample={r.data[:3]}')
```

If the canonical replacement articles have zero citations → H3
confirmed (corpus gap).

### Step 6 — write the diagnosis up

The output of steps 1-5 goes into a follow-up doc
`docs/re-engineer/fix/fix_v1_diagnosis.md` with sections:
* Which hypothesis (H1/H2/H3/H4) the data supports.
* For the supported hypothesis, what the proposed fix shape is.
* What gate criteria the proposed fix must meet (per the
  six-gate lifecycle in `CLAUDE.md`).
* Whether the fix is reversible without a migration.

Only AFTER that doc is written do you propose code or migration
changes. The operator may want a separate review before any
patch ships.

---

## 7. What you must NOT do (until the diagnosis lands)

1. **Don't lower the gate threshold.** 24/36 stays. If the
   diagnosis surfaces that the panel itself is too strict on
   topic-key matching, document the case-by-case qualitative pass
   per `feedback_thresholds_no_lower`; don't move the bar.
2. **Don't disable the unconditional vigencia filter.** It closed
   the Art. 689-1 / Ley 1429-2010 over-citation failure that the
   2026-04-26 SME panel surfaced. Re-enabling the bypass would
   regress that failure. If the filter is too aggressive, the fix
   is more nuance (per-state demotion, not on/off filtering), not
   reverting.
3. **Don't re-promote the post-P6 successes to cloud yet.** P6
   added ~78 new veredicto JSONs locally
   (`evals/vigencia_extraction_v1/{F2,E1a,E1b,E1d,E2a,E2c,D5}/`)
   that are not yet in cloud. Re-promoting them changes the
   dataset mid-diagnosis and contaminates the apples-to-apples
   comparison. After the diagnosis, do it.
4. **Don't re-run the §1.G panel as a "let's see if it's better
   now" probe.** Each run takes 10-15 min and burns LLM calls. The
   diagnostic is per-Q diff, not panel-pass/fail.
5. **Don't fix-fast on the topic router.** Even if H1 is right,
   the router is keyword-driven and changes there ripple across
   the whole product. Any router change is a separate cycle with
   its own gate.
6. **Don't commit speculative migrations.** Migrations are
   CLI-explicit only (`CLAUDE.md` non-negotiable on cloud
   retirements). Even reversible CHECK-constraint changes deserve
   the diagnostic-first treatment.

---

## 8. Future Activities — what we did NOT finish (parked because of the regression)

These were on the `next_v7` plan or surfaced during the cycle but
were paused once the §1.G panel surfaced the regression. Resume
each AFTER the fix_v1 diagnosis lands and the regressed qids
recover.

### 8.1 Re-promote the 78 P6-recovered veredictos to cloud

P6 cascade closed ~78 refusals across 7 batches (F2 +29, E1a +15,
E1b +10, E1d +6, E2a +10, E2c +8, D5 0; see
`docs/re-engineer/state_next_v7.md` §4 for the table). All
new successes are in `evals/vigencia_extraction_v1/<batch>/*.json`
locally, but **not yet on cloud**. Re-running
`scripts/cloud_promotion/run.sh` (the orchestrator from commit
`9cebd4b`) is idempotent and would lift cloud
`norm_vigencia_history` from 9,322 → ~9,400 distinct norm_ids
plus history rows. Estimated effort: ~5 min.

### 8.2 Re-sync cloud Falkor with post-P6 vigencia rows

After 8.1 lands, re-run `sync_vigencia_to_falkor.py --target
production`. Note the **P5 perf finding** in
`state_next_v7.md` §7: the script does ~5,500 sequential cypher
round-trips at ~80-130 ms each (20 min today's run). The
recommended fix is **UNWIND-batched MERGE** (see §7.1 of the
state ledger) — 50-100× speedup, ~2 hr engineering. Do this
fast-follow first if 8.1 will run more than once.

### 8.3 The `--shard X/N` 4-process embedding backfill

Commit `9e6bdcf` shipped a sharded embedding-backfill flow but it
was unused this cycle (P4 was a no-op — all 19,546 chunks
already had embeddings). Stays available for future
embedding-pass needs (e.g. when subtopic_taxonomy v3 ships).
`scripts/cloud_promotion/launch_p4_4shards.sh` is the launcher.

### 8.4 Extend `dian_pdf_registry.json` to more landing pages

The MVP DIAN PDF registry has only 7 entries (Resolución 13/2021
+ 6 others from the factura-electronica landing page). P6 closed
29 of 81 F2 refusals (35%) — most of the 52 remaining are
`res.dian.165.2023.*` and similar resoluciones that are NOT yet
in the registry. Adding more landing pages to
`scripts/canonicalizer/build_dian_pdf_registry.py::LANDING_PAGES`
(per `docs/learnings/sites/dian-main.md` §6 maintenance recipe)
is the path. Then re-run F2 with `--rerun-only-refusals`.
Estimated effort: ~1-2 hr per landing page added.

### 8.5 SUIN harvest extension for any norms still missing

The fork agent finding (see `state_next_v7.md` §3 P7) was that
the 6 COVID decretos are NOT on SUIN-Juriscol but ARE on Senado;
P7 shipped the Senado decreto resolver instead of extending
SUIN. SUIN harvest still has gaps for documents that exist
neither on Senado nor Función Pública (the original next_v7 §3.7
target). Pick this up only if a refusal cluster surfaces that
demands it.

### 8.6 Backfill `norm_vigencia_history` for `et.art.689-1` and other
under-extracted top-priority norms

P8 covered chunk → norm citations (52,246 rows). But the v6
cascade only extracted vigencia for **2,349 distinct norm_ids**;
many high-impact norms (Art. 689-1, Ley 1429/2010 specific articles,
sentencias C-481/2019, etc.) have **0 rows in
`norm_vigencia_history`**. The v3 chunk-vigencia gate cannot
demote chunks citing those norms because the resolver returns
NULL. This is one of the H3 corpus-completeness paths.

Action: identify the top ~50 norms that the §1.G panel + the
2026-04-26 SME failure cited, audit their vigencia-history
coverage, run targeted vigencia extractions for the gaps. Estimated
effort: ~3-5 hr (extraction) + cloud promotion.

### 8.7 Re-run §1.G panel post-fix as the gate

After the diagnosis from §6 lands and a fix is committed, re-run
the §1.G panel with the SAME parallel runner pattern
(`scripts/eval/run_sme_parallel.py --workers 4`). Pass criterion
`≥ 24/36 served_acceptable+` with ZERO ok→zero regressions.
**This is the gate that matters for declaring the next_v7 cycle
closed.** Don't claim closure until this passes apples-to-apples
against the 21/36 baseline.

### 8.8 Document the Activity 1 outcome on the SME triage queue

The 6,981 refusals from the P8 norm_citations backfill landed in
`evals/canonicalizer_refusals_v1/refusals.jsonl`. SME triage (per
the v3 plan §1B-δ flow) would categorize these into "fixable
refusals" vs "real corpus gaps". This was deferred this cycle
but is a known follow-up.

### 8.9 The cosmetic / lower-priority backlog from `next_v7.md` §3.8

Per `next_v7.md` §3.8: heartbeat date format unification, CC/CE
SPA scrapers (live-fetch path), Phase A/B/C JSON regeneration if
ever needed, Falkor cloud schema refresh recipes. None blocking.

---

## 9. Code surface to read (orientation map)

Hot path that produced the served answer:

1. **`src/lia_graph/ui_server.py`** — HTTP entry point.
2. **`src/lia_graph/pipeline_router.py`** — pipeline-D vs legacy router.
3. **`src/lia_graph/topic_router.py`** + **`src/lia_graph/topic_router_keywords.py`**
   — keyword-driven topic emit (H1).
4. **`src/lia_graph/pipeline_d/orchestrator.py`** — the `main chat`
   orchestrator. Coherence-gate hook at line ~456-469 (H4).
5. **`src/lia_graph/pipeline_d/planner.py`** — vigencia-query-kind +
   payload + sub-topic intent.
6. **`src/lia_graph/pipeline_d/retriever_supabase.py`** — calls
   `hybrid_search` RPC, then runs the v3
   `apply_demotion` post-pass. The `apply_demotion` import is at
   line 535-538; the gate-RPC dispatch is in `_at_date` (~545)
   and `_for_period` (~556). **This is the H2 surface.**
7. **`src/lia_graph/pipeline_d/vigencia_resolver.py`** — converts
   planner kind/payload to the right RPC call.
8. **`src/lia_graph/pipeline_d/vigencia_demotion.py`** — `apply_demotion`
   takes chunk_rows + the gate output, multiplies RRF score,
   drops zero-demotion rows. Read for filter semantics.
9. **`src/lia_graph/pipeline_d/_coherence_gate.py`** — coherence
   detector + refusal text. H4 surface.
10. **`config/subtopic_taxonomy.json`** + **`config/canonicalizer_run_v1/batches.yaml`**
    — taxonomy + batch definitions.

Migrations that touch served retrieval:

* **`supabase/migrations/20260427000000_topic_boost.sql`** —
  hybrid_search filter_topic_boost.
* **`supabase/migrations/20260428000000_drop_legacy_hybrid_search.sql`**
  — drops the 14-arg overload.
* **`supabase/migrations/20260429000000_vigencia_filter_unconditional.sql`**
  — the unconditional v2 filter. **Today's biggest behavior change.**
* **`supabase/migrations/20260501000004_chunk_vigencia_gate.sql`**
  — the v3 gate functions.

Backfill / data-maintenance scripts:

* **`scripts/ingestion/backfill_norm_citations.py`** — the P8 script.
* **`scripts/ingestion/audit_norm_citations.py`** — coverage probe.
* **`scripts/canonicalizer/sync_vigencia_to_falkor.py`** — P5 sync (slow).
* **`scripts/cloud_promotion/run.sh`** + **`heartbeat.py`** — the
  P1 driver (next_v7 reference implementation of the
  fail-fast/preflight/risk-first canon).

Eval harnesses:

* **`scripts/eval/run_sme_validation.py`** — sequential canonical runner.
* **`scripts/eval/run_sme_parallel.py`** — 4-worker parallel wrapper
  (today's session, 2.7× speedup observed).
* **`scripts/eval/engine.py`** — `ChatClient` HTTP client, summarizer,
  classifier helpers.
* **`evals/sme_validation_v1/`** — 36 questions + per-run dirs.

---

## 10. Recent commits (this session, 2026-04-29)

```
f66a7ff state_next_v7 — close-out for P1/P2/P3/P4/P5/P7; P6 in flight
9e6bdcf embedding_ops — add --shard X/N for concurrent backfill (next_v7 P4)
1592832 next_v7 P7 — Senado scraper resolves decreto.<num>.<year> URLs
8fd0de1 canon — preflight + risk-first batching as canonical ops doctrine
95e1eb9 secretariasenado.md — mark CCo gap RESOLVED via next_v7 P3
5a0ad15 canon + migration — extend norm_type to Códigos + decreto subtypes
c0f3d3d next_v7 P3 — Senado CCo segment index + scraper resolves to per-pr URL
3b09719 next_v7 P2 — DianPdfScraper (7th source) closes F2 gap
10f0fa8 canon — accept bare 'cst' and 'cco' as whole-code references
2bde298 CLAUDE.md + AGENTS.md — Fail Fast, Fix Fast as core operating canon
9cebd4b next_v7 P1 — cloud promotion orchestrator + canon/writer fixes
```

None of these touch served retrieval code. The retrieval-affecting
changes are all in the pre-existing migrations applied via
`supabase db push --linked` during P1 (see §1).

---

## 11. Environment + flags currently active on `npm run dev:staging`

From `scripts/dev-launcher.mjs` (current defaults, per
`docs/orchestration/orchestration.md` env matrix
`v2026-04-26-additive-no-retire`):

* `LIA_TEMA_FIRST_RETRIEVAL=on` (since 2026-04-25 re-flip).
* `LIA_EVIDENCE_COHERENCE_GATE=enforce` (since 2026-04-25; H4 surface).
* `LIA_POLICY_CITATION_ALLOWLIST=enforce` (since 2026-04-25).
* `LIA_INGEST_CLASSIFIER_TAXONOMY_AWARE=enforce` (since 2026-04-25).
* `LIA_LLM_POLISH_ENABLED=1`.
* `LIA_RERANKER_MODE=live` (since 2026-04-22).
* `LIA_QUERY_DECOMPOSE=on` (multi-`¿…?` fan-out).
* `LIA_SUBTOPIC_BOOST_FACTOR=1.5`.

**Important:** there is currently NO env knob to disable the v3
chunk-vigencia gate (`apply_demotion` post-pass). The diagnostic
in §6 step 4 may need to add one.

---

## 12. Current operator state-of-mind (for tone calibration)

Operator memory:
* Plain-language, boss-level communication
  (`feedback_plain_language_communication`).
* Always suggest what's next at end of every status report
  (`feedback_always_suggest_next`).
* Don't quote money; use action + effort + what it unblocks
  (`feedback_no_money_quoting`).
* Display all times in Bogotá AM/PM (UTC-5 12-hour)
  (`feedback_time_format_bogota`); machine logs stay UTC ISO.
* Six-gate lifecycle on every pipeline change
  (`feedback_verify_fixes_end_to_end`).

Operator just said **"this is, if there ever was, a STOP and
REVIEW WHAT IS HAPPENING IN DETAIL"**. They are unhappy with the
result, calm-and-methodical about the next step, and explicitly
do NOT want a fix-fast patch on top of an unverified diagnosis.

---

*Drafted 2026-04-29 ~11:15 AM Bogotá by claude-opus-4-7
immediately after the §1.G panel returned 8/36. P9 SME run dir at
`evals/sme_validation_v1/runs/20260429T153845Z_post_p1_v3/`.
All other next_v7 streams (P1-P8) closed. Re-promotion of P6
successes deferred. Diagnosis in §6 is the only path forward.*
