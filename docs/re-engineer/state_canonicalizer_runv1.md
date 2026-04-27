# State of execution — canonicalizer_runv1 (the per-batch operational ledger)

> **Status:** stub seeded 2026-04-27 (Bogotá). Tracks the live state of every batch defined in `canonicalizer_runv1.md`.
> **Companion to:** `docs/re-engineer/canonicalizer_runv1.md` (the plan), `docs/re-engineer/state_fixplan_v3.md` (the v3 root state file), `evals/canonicalizer_run_v1/ledger.jsonl` (machine-readable per-batch verdicts).
> **Purpose.** Where each batch is. What's blocked. What was the last action. How to recover. Read §3 first.
> **Living doc.** Updated by the engineer after every batch (pre / extract / ingest / sync / post / score). Cron heartbeats append every 6h once cron is in scope.

---

## §1 — How to use this file

This file mirrors the shape of `state_fixplan_v3.md`: it answers "where is each batch right now?" not "what should we run next?" — that's the plan's job.

### §1.1 — Single source of truth for batch state

When `canonicalizer_runv1.md` and this file disagree:
- Plan (canonicalizer_runv1.md) wins for **what should happen** to each batch.
- This file (state_canonicalizer_runv1.md) wins for **what has happened** to each batch.

### §1.2 — Update protocol per phase of a batch's life

| Phase of a batch | Who updates | What they update |
|---|---|---|
| About to launch | Engineer | §4 row → `pre_running`, §10 run log entry |
| Pre-baseline complete | Engineer | §4 row → `pre_done`, link to `evals/canonicalizer_run_v1/<batch_id>/pre_*.json` |
| Extraction running | Engineer + heartbeat | §4 row → `extracting`, §7 wall-time-so-far counter, §10 heartbeat ticks |
| Extraction complete | Engineer | §4 row → `extracted`, %-veredictos / %-refusals |
| Ingest+sync to local docker | Engineer | §4 row → `ingested_local_docker`, §7 local docker counter |
| Post-verify complete | Engineer | §4 row → `verified`, score (PASS/FAIL/DEFERRED), ledger.jsonl line |
| SME signoff (per Phase) | SME | §4 phase header → `sme_blessed_local_docker`, §10 SME entry |
| Cloud staging promotion | Engineer + operator | §4 row → `promoted_cloud_staging`, §7 cloud staging counter |
| Production promotion | Engineer + operator | §4 row → `production`, §7 production counter |
| Failure | Whoever found it | §4 row → `failed`, §9 open question, §10 entry |

### §1.3 — Conflict resolution

Two engineers updating the same row simultaneously: later timestamp wins, both pinged via §10 to reconcile. Operator is tie-breaker.

### §1.4 — Relationship to other files

| File | Role |
|---|---|
| `canonicalizer_runv1.md` | The plan — what each batch is for, slice + tests + protocol |
| `state_canonicalizer_runv1.md` | **This file** — where each batch is right now |
| `config/canonicalizer_run_v1/batches.yaml` | Machine-readable batch definitions used by the scripts |
| `evals/canonicalizer_run_v1/ledger.jsonl` | Append-only per-batch score outcomes (machine output) |
| `evals/canonicalizer_run_v1/<batch_id>/pre_*.json` | Pre-batch test capture |
| `evals/canonicalizer_run_v1/<batch_id>/post_*.json` | Post-batch test capture |
| `evals/vigencia_extraction_v1/<batch_id>/*.json` | Per-norm veredicto JSONs (the canonical artifact for promotion) |
| `state_fixplan_v3.md` | Parent state file — references this for the canonicalizer pass |

---

## §2 — Fresh-LLM runnable preconditions for this run

A fresh LLM can drive this run end-to-end IF:

1. It has read `canonicalizer_runv1.md` end-to-end.
2. The local stack is up: Supabase docker on `127.0.0.1:54322`, FalkorDB docker on `127.0.0.1:6389`.
3. The corpus is loaded into local Supabase + Falkor (per `state_fixplan_v3.md` §10 latest entry).
4. `config/canonicalizer_run_v1/batches.yaml` exists (yes — created 2026-04-27).
5. `scripts/extract_vigencia.py` accepts `--batch-id` (yes — wired 2026-04-27).
6. `scripts/run_batch_tests.py` exists (yes — created 2026-04-27).
7. `LIA_GEMINI_API_KEY` is set in the environment (operator-gated).
8. The lia-ui server is running (`npm run dev` against local docker) so `run_batch_tests.py` can hit `http://127.0.0.1:8787/api/chat`.

**What the LLM CANNOT do** (per `state_fixplan_v3.md` §2.4):

- SME signoff at Phase boundaries.
- Decide whether to advance from local docker → cloud staging.
- Approve cloud writes for production.

When a Phase's last batch finishes locally, the LLM stops and surfaces the §1.G fixture results to the operator for SME signoff.

---

## §3 — Current global state

> **Update protocol:** in-place edit on every batch advance; weekly review by operator.

**As of:** 2026-04-27 night Bogotá — initial state file ship; no batches launched yet.

### §3.1 — Run progress

| Field | Value |
|---|---|
| Batches defined | 56 across 12 phases (A → L) |
| Batches launched | 0 |
| Batches completed | 0 |
| Cumulative coverage | 0% (target post-A4: 6%; post-B10: 20%; post-H6: 80% soft-launch floor) |
| Stage | not started |
| Operator decision pending | (a) open `LIA_GEMINI_API_KEY` for the run, (b) approve unattended overnight launches |

### §3.2 — Batch in flight

**None.** Awaiting operator green-light on Gemini API access for the local-env run.

The first three batches in launch order once unblocked: **A1 → A2 → A3** (Phase A — Procedimiento foundation; ~50 min total).

### §3.3 — Blockers

| Blocker | Affects | Owner | Status |
|---|---|---|---|
| Gemini API key authorized for the run | All batches A1–K4 | Operator | **PENDING** |
| Local docker stack running with corpus loaded | All batches | Engineering | ✅ done (per state_fixplan_v3.md §10 2026-04-27 night) |
| `lia-ui` server running for `run_batch_tests.py` | pre/post phases of every batch | Engineer | not started; one-line `npm run dev` |
| SME availability for Phase signoffs | Phase boundaries (A, B, C, D, E, F, G, H, I, J, K) | SME (Alejandro) | scheduling pending |

### §3.4 — Last meaningful state change

| When (Bogotá) | What | Who |
|---|---|---|
| 2026-04-27 evening | `state_canonicalizer_runv1.md` initial ship (this file) | claude-opus-4-7 |
| 2026-04-27 evening | `config/canonicalizer_run_v1/batches.yaml` shipped (56 batches) | claude-opus-4-7 |
| 2026-04-27 evening | `scripts/extract_vigencia.py --batch-id` wired + run-once guard added | claude-opus-4-7 |
| 2026-04-27 evening | `scripts/run_batch_tests.py` shipped | claude-opus-4-7 |
| 2026-04-27 evening | `canonicalizer_runv1.md` title corrected (Canonicalizar → Canonicalizer) | claude-opus-4-7 |

### §3.5 — Next planned step

1. Operator opens `LIA_GEMINI_API_KEY` env for the local-env run.
2. Engineer launches **A1** baseline (`run_batch_tests.py --mode pre`).
3. Engineer launches A1 extraction (`extract_vigencia.py --batch-id A1 ...`).
4. Engineer ingests A1 to local docker (`ingest_vigencia_veredictos.py --target wip --input-dir evals/vigencia_extraction_v1/A1 ...`).
5. Engineer syncs local Falkor mirror.
6. Engineer launches A1 post-verify (`run_batch_tests.py --mode post`).
7. Engineer scores A1 (`run_batch_tests.py --mode score`).
8. If A1 PASS, advance to A2. If A1 FAIL, triage in `evals/canonicalizer_run_v1/A1/failure_report.md` before any further batch.

---

## §4 — Per-batch ledger

**Status legend:**
- `not_started` (default)
- `pre_running` / `pre_done`
- `extracting` (Gemini fired) / `extracted` (JSONs written)
- `ingested_local_docker` / `synced_falkor_local`
- `post_running` / `post_done`
- `verified_PASS` / `verified_FAIL` / `verified_DEFERRED`
- `sme_blessed_local_docker` (set on phase header, not per-batch)
- `promoted_cloud_staging` (after Stage 2 replay)
- `production` (after Stage 3 replay)
- `regressed_discarded` (kept in record; never silently rolled back)

> **Update protocol:** in-place edit per row on every batch advance. Each row's `last_update` is the most recent change.

### §4.1 — Phase A · Procedimiento tributario foundation

| Batch | Status | Owner | Last update (Bogotá) | Norms | Pre score | Post score | Notes |
|---|---|---|---|---|---|---|---|
| A1 | not_started | TBD | — | 25 (resolved) | — | — | First batch in run order |
| A2 | not_started | TBD | — | 9 (resolved) | — | — | depends_on: A1; includes the `art. 689-1` regression marker |
| A3 | not_started | TBD | — | ~50 | — | — | depends_on: A1; sanciones |
| A4 | not_started | TBD | — | ~32 | — | — | depends_on: A1; devoluciones |

**Phase A SME signoff:** not started. Phase A signoff requires the §1.G fixture's procedimiento subset to land cleanly.

### §4.2 — Phase B · ET Renta

| Batch | Status | Owner | Last update | Norms | Pre score | Post score | Notes |
|---|---|---|---|---|---|---|---|
| B1 | not_started | TBD | — | ~20 | — | — | sujetos pasivos + residencia |
| B2 | not_started | TBD | — | ~32 | — | — | dividendos `for_period` test |
| B3 | not_started | TBD | — | ~30 | — | — | costos |
| B4 | not_started | TBD | — | ~30 | — | — | deducciones generales |
| B5 | not_started | TBD | — | ~30 | — | — | **DE acid test** (Art. 158-1) |
| B6 | not_started | TBD | — | ~50 | — | — | renta líquida especial + GO |
| B7 | not_started | TBD | — | 9 (resolved) | — | — | **for_period acid test** (Art. 240; Art. 338 CP shift) |
| B8 | not_started | TBD | — | ~25 | — | — | descuentos |
| B9 | not_started | TBD | — | ~40 | — | — | personas jurídicas + ESAL |
| B10 | not_started | TBD | — | 3 (resolved) | — | — | **V acid test** (Art. 290 numeral 5; sub-unit) |

**Phase B SME signoff:** not started. Soft target: post-B10 cumulative coverage ~20%; SME validates that all renta acid tests (DE, V, VM, EC for Art. 240-1 in B7) render correctly.

### §4.3 — Phase C · IVA + Retefuente + GMF + Patrimonio

| Batch | Status | Owner | Last update | Norms | Pre score | Post score | Notes |
|---|---|---|---|---|---|---|---|
| C1 | not_started | TBD | — | ~30 | — | — | IVA hechos generadores |
| C2 | not_started | TBD | — | ~40 | — | — | IVA tarifas |
| C3 | not_started | TBD | — | ~50 | — | — | retefuente |
| C4 | not_started | TBD | — | ~30 | — | — | GMF + Patrimonio + Timbre |

### §4.4 — Phase D · Reformas tributarias por ley

| Batch | Status | Owner | Last update | Norms | Pre score | Post score | Notes |
|---|---|---|---|---|---|---|---|
| D1 | not_started | TBD | — | 66 (resolved) | — | — | **EC validation** (Ley 2277/2022 Art. 11) |
| D2 | not_started | TBD | — | ~70 | — | — | Ley 2155/2021 |
| D3 | not_started | TBD | — | ~160 | — | — | Ley 2010/2019 |
| D4a | not_started | TBD | — | ~190 | — | — | Ley 1819/2016 (1/2) |
| D4b | not_started | TBD | — | ~190 | — | — | depends_on: D4a |
| D5 | not_started | TBD | — | 39 (resolved) | — | — | **Cascade trigger** (Ley 1943 → C-481/2019) |
| D6a | not_started | TBD | — | ~100 | — | — | Ley 1607/2012 (1/2) |
| D6b | not_started | TBD | — | ~100 | — | — | depends_on: D6a |
| D7 | not_started | TBD | — | ~80 | — | — | Ley 1739/2014 |
| D8a | not_started | TBD | — | ~120 | — | — | Ley 2294/2023 (1/3) |
| D8b | not_started | TBD | — | ~120 | — | — | depends_on: D8a |
| D8c | not_started | TBD | — | ~120 | — | — | depends_on: D8b |

### §4.5 — Phase E · Decretos reglamentarios

| Batch | Status | Owner | Last update | Norms | Pre score | Post score | Notes |
|---|---|---|---|---|---|---|---|
| E1a | not_started | TBD | — | ~85 | — | — | DUR 1625 Libro 1.1+1.2 |
| E1b | not_started | TBD | — | ~85 | — | — | DUR 1625 Libro 1.3+1.4 |
| E1c | not_started | TBD | — | ~85 | — | — | DUR 1625 Libro 1.5 |
| E1d | not_started | TBD | — | ~85 | — | — | DUR 1625 Libro 1.6 |
| E1e | not_started | TBD | — | ~85 | — | — | DUR 1625 Libro 1.7 |
| E1f | not_started | TBD | — | ~85 | — | — | DUR 1625 Libro 1.8+ |
| E2a | not_started | TBD | — | ~100 | — | — | DUR 1625 IVA (1/2) |
| E2b | not_started | TBD | — | ~100 | — | — | DUR 1625 IVA (2/2) |
| E2c | not_started | TBD | — | ~80 | — | — | DUR 1625 retefuente |
| E3a | not_started | TBD | — | ~100 | — | — | DUR 1625 procedimiento (1/2) |
| E3b | not_started | TBD | — | ~100 | — | — | DUR 1625 procedimiento (2/2) |
| E4 | not_started | TBD | — | 4 (resolved) | — | — | **IE acid test** (Decreto 1474/2025) |
| E5 | not_started | TBD | — | ~30 | — | — | Decretos legislativos COVID |
| E6a | not_started | TBD | — | ~80 | — | — | DUR 1072 (1/3) |
| E6b | not_started | TBD | — | ~80 | — | — | DUR 1072 (2/3) |
| E6c | not_started | TBD | — | ~80 | — | — | DUR 1072 (3/3 — SST) |

### §4.6 — Phase F · Resoluciones DIAN clave

| Batch | Status | Owner | Last update | Norms | Pre score | Post score | Notes |
|---|---|---|---|---|---|---|---|
| F1 | not_started | TBD | — | ~50 | — | — | UVT + calendario por año (parameter for_period) |
| F2 | not_started | TBD | — | ~30 | — | — | Factura + nómina electrónica |
| F3 | not_started | TBD | — | ~20 | — | — | Régimen simple |
| F4 | not_started | TBD | — | ~40 | — | — | Cambiario + RUT |

### §4.7 — Phase G · Conceptos DIAN unificados

| Batch | Status | Owner | Last update | Norms | Pre score | Post score | Notes |
|---|---|---|---|---|---|---|---|
| G1 | not_started | TBD | — | ~60 | — | — | Concepto unificado IVA |
| G2 | not_started | TBD | — | ~100 | — | — | Concepto unificado renta |
| G3 | not_started | TBD | — | ~80 | — | — | Concepto unificado retención |
| G4 | not_started | TBD | — | ~80 | — | — | Concepto unificado procedimiento |
| G5 | not_started | TBD | — | ~50 | — | — | Concepto unificado Régimen Simple |
| G6 | not_started | TBD | — | 5 (resolved) | — | — | **SP acid test** (Concepto 100208192-202 num.20) |

### §4.8 — Phase H · Conceptos DIAN individuales (long tail)

| Batch | Status | Owner | Last update | Norms | Pre score | Post score | Notes |
|---|---|---|---|---|---|---|---|
| H1 | not_started | TBD | — | ~50 | — | — | Conceptos régimen simple |
| H2 | not_started | TBD | — | ~50 | — | — | Conceptos retención |
| H3a | not_started | TBD | — | ~80 | — | — | Conceptos renta (1/2) |
| H3b | not_started | TBD | — | ~80 | — | — | Conceptos renta (2/2) |
| H4a | not_started | TBD | — | ~80 | — | — | Conceptos IVA (1/2) |
| H4b | not_started | TBD | — | ~80 | — | — | Conceptos IVA (2/2) |
| H5 | not_started | TBD | — | ~50 | — | — | Conceptos procedimiento |
| H6 | not_started | TBD | — | ~30 | — | — | Oficios DIAN |

### §4.9 — Phase I · Jurisprudencia (CC + CE)

| Batch | Status | Owner | Last update | Norms | Pre score | Post score | Notes |
|---|---|---|---|---|---|---|---|
| I1 | not_started | TBD | — | 5 (resolved) | — | — | Sentencias CC reformas (cascade triggers) |
| I2 | not_started | TBD | — | ~15 | — | — | Sentencias CC principios CP |
| I3 | not_started | TBD | — | ~30 | — | — | **DT validation** (CE Sección Cuarta) |
| I4 | not_started | TBD | — | ~20 | — | — | Autos CE |

### §4.10 — Phase J · Régimen laboral

| Batch | Status | Owner | Last update | Norms | Pre score | Post score | Notes |
|---|---|---|---|---|---|---|---|
| J1 | not_started | TBD | — | ~30 | — | — | CST contratos |
| J2 | not_started | TBD | — | ~50 | — | — | CST prestaciones sociales |
| J3 | not_started | TBD | — | ~40 | — | — | CST jornada (Ley 2101/2021 transición 42h) |
| J4 | not_started | TBD | — | ~50 | — | — | CST conflictos colectivos |
| J5 | not_started | TBD | — | 3 (resolved) | — | — | Pensional + Ley 2381/2024 reforma |
| J6 | not_started | TBD | — | 3 (resolved) | — | — | Salud |
| J7 | not_started | TBD | — | 3 (resolved) | — | — | Parafiscales + licencias |
| J8a | not_started | TBD | — | ~70 | — | — | DUR 1072 laboral (1/3) |
| J8b | not_started | TBD | — | ~70 | — | — | depends_on: J8a |
| J8c | not_started | TBD | — | ~70 | — | — | depends_on: J8b |

### §4.11 — Phase K · Cambiario + comercial + societario

| Batch | Status | Owner | Last update | Norms | Pre score | Post score | Notes |
|---|---|---|---|---|---|---|---|
| K1 | not_started | TBD | — | ~40 | — | — | Resolución Externa 1/2018 JDBR |
| K2 | not_started | TBD | — | ~30 | — | — | DCIN-83 |
| K3 | not_started | TBD | — | ~50 | — | — | CCo sociedades |
| K4 | not_started | TBD | — | 2 (resolved) | — | — | Ley 222/1995 + Ley 1258/2008 |

### §4.12 — Phase L · Refusal triage + cleanup (SME-led)

| Batch | Status | Owner | Last update | Norms | Pre score | Post score | Notes |
|---|---|---|---|---|---|---|---|
| L1 | not_started | SME + engineer | — | (populated by triage) | — | — | Refusal triage A–E |
| L2 | not_started | SME + engineer | — | (populated by triage) | — | — | Refusal triage F–I |
| L3 | not_started | engineer + operator | — | (populated by L1+L2) | — | — | **ONLY exception to no-double-extraction** |

---

## §5 — Reversibility per batch

Every batch is **R2 reversible** (per `state_fixplan_v3.md` §5):

```bash
# Rollback all writes from a specific run_id of a batch:
docker exec supabase_db_lia-graph psql -U postgres -c \
  "DELETE FROM norm_vigencia_history WHERE extracted_via->>'run_id' LIKE 'canonicalizer-A1-%';"

# Rollback the corresponding Falkor edges (the sync script supports this):
PYTHONPATH=src:. uv run python scripts/sync_vigencia_to_falkor.py --target wip \
    --rebuild-from-postgres --confirm
# (The rebuild reads the now-cleaned Postgres and re-MERGEs everything else.)

# The veredicto JSONs in evals/vigencia_extraction_v1/<batch_id>/ are PRESERVED
# unless the engineer explicitly removes them. They are the canonical artifact.
```

**Rule of thumb:** clean up the DB rows by run_id; never delete the JSONs unless the entire batch was a mis-fire and the operator explicitly approves a re-extraction (`--allow-rerun`).

The reversibility also covers the **promotion replay**:
- Cloud staging promotion landed but bad? `DELETE FROM norm_vigencia_history WHERE extracted_via->>'run_id' = 'canonicalizer-run-v1-promote-cloud-<ts>'` against staging Supabase. Same shape. The local docker rows + the JSONs are unaffected.

---

## §6 — Test horizons per batch

| Horizon | When | What it validates |
|---|---|---|
| **H_pre** | Before extraction starts | Baseline: what does Lia answer NOW, without this batch's vigencia data? |
| **H_post** | After extraction + ingest + sync complete | Did the batch's data move the answer in the expected direction? |
| **H_score** | After both above | Pass/fail per question; PASS/FAIL/DEFERRED batch verdict |
| **H_phase_signoff** | At phase boundary (A → B, B → C, etc.) | SME runs §1.G fixture subset relevant to that phase; signs off in writing |
| **H_full_signoff** | After Phase L | SME runs full 36-question §1.G fixture; binding gate for cloud promotion |

**Soft FAIL (DEFERRED) rule.** If a question's `must_cite` lists a norm that's NOT in this batch and not yet ingested by an earlier batch, the test is DEFERRED, not FAILED — the dependency just hasn't materialized yet. The score routine flags these explicitly.

---

## §7 — Environment state per batch

> **Update protocol:** in-place edit per row on every replay. Three columns mirror the three-stage promotion path.

**As of:** 2026-04-27 night Bogotá (zero batches launched; environment state pre-populated for the launch step).

| Stage | URL / target | Status | Last sync |
|---|---|---|---|
| **Local docker — Supabase** | `http://127.0.0.1:54321` (target=wip) | ✅ migrations applied; corpus loaded; 7 fixture veredictos landed; 4,757 chunks have citations | 2026-04-27 night |
| **Local docker — FalkorDB** | `redis://127.0.0.1:6389` (graph=`LIA_REGULATORY_GRAPH`) | ✅ corpus loaded; (:Norm) mirror has 11,389 nodes + 41 edges | 2026-04-27 night |
| **Cloud staging — Supabase** | per `.env.staging` SUPABASE_URL | ⏸ on hold per operator directive (no migrations applied yet) | — |
| **Cloud staging — FalkorDB** | per `.env.staging` FALKORDB_URL | ⏸ on hold | — |
| **Production — Supabase** | per `.env` SUPABASE_URL | ⏸ on hold | — |
| **Production — FalkorDB** | per `.env` FALKORDB_URL | ⏸ on hold | — |

When a batch lands in local docker, the engineer marks the local docker row of §7.B (per-batch breakdown — to be added once first batch advances to that state).

---

## §8 — Recovery playbooks

### §8.1 — Batch FAIL — score reports regressions

1. Read the failure rows from `evals/canonicalizer_run_v1/ledger.jsonl` (last entry).
2. Inspect the post-`run_id`.json for the offending question's actual answer.
3. Common causes:
   - **Wrong veredicto in JSON** → edit the JSON, re-replay (NOT re-extract); see `state_fixplan_v3.md` §5.
   - **Cascade not fired for this batch** → check if it was a sentencia_cc batch that should have triggered re-verifications elsewhere; queue them via `vigencia_cascade.queue_reverify`.
   - **Test question references a norm from a future batch** → the question is mis-scoped; mark DEFERRED in the ledger and revise the question in `batches.yaml`.
4. Triage report: `evals/canonicalizer_run_v1/<batch_id>/failure_report.md`. Capture root cause + fix + re-run command.

### §8.2 — Extraction stalls / silent process death

Per `CLAUDE.md` long-running-job convention:
1. Check `logs/events.jsonl` for the last `cli.done` or `run.failed` event for the run_id.
2. If neither: **silent death**. STOP loop. Do NOT retry blindly.
3. Inspect `evals/vigencia_extraction_v1/<batch_id>/` for partial JSONs.
4. Identify failure pattern (rate limit, OOM, network blip).
5. Fix root cause; restart with NEW run_id; the writer's `(norm_id, run_id, source_norm_id)` idempotency key prevents duplicate writes.

### §8.3 — Local docker desync (Supabase ahead, Falkor behind, or vice versa)

```bash
PYTHONPATH=src:. uv run python scripts/sync_vigencia_to_falkor.py \
    --target wip --rebuild-from-postgres --confirm
```
Wholesale rebuild from Postgres source-of-truth. Cheap.

### §8.4 — Refusal queue grows unexpectedly

- Cumulative refusal queue depth > 500 → SME triage session BEFORE the next batch (per `canonicalizer_runv1.md` §7).
- After triage, canonicalizer rule additions land in `src/lia_graph/canon.py`; re-run only the affected norms via L3 (the only sanctioned re-extraction path).

### §8.5 — Operator wants to revert the entire run

```bash
# 1. Pause all writers.
# 2. Drop everything from norm_vigencia_history that this run produced:
docker exec supabase_db_lia-graph psql -U postgres -c \
  "DELETE FROM norm_vigencia_history WHERE extracted_via->>'run_id' LIKE 'canonicalizer-%';"

# 3. Drop the citations for this run:
docker exec supabase_db_lia-graph psql -U postgres -c \
  "DELETE FROM norm_citations WHERE extracted_via LIKE 'canonicalizer-%';"

# 4. Rebuild Falkor mirror from now-cleaned Postgres:
PYTHONPATH=src:. uv run python scripts/sync_vigencia_to_falkor.py \
    --target wip --rebuild-from-postgres --confirm

# 5. Veredicto JSONs stay — they're the canonical artifact and survive a DB reset.
#    Removing them would require explicit operator approval (re-extraction cost).
```

---

## §9 — Open questions

| # | Question | Who answers | Blocks | Raised | Status |
|---|---|---|---|---|---|
| Q1 | Open `LIA_GEMINI_API_KEY` for the local-env extraction? | Operator | All batches | 2026-04-27 evening | OPEN |
| Q2 | Approve unattended overnight launches per the long-running-job protocol? | Operator | A1 launch | 2026-04-27 evening | OPEN |
| Q3 | Schedule Phase A SME signoff session for after A4 completes? | Operator + SME | Phase A → Phase B advance | 2026-04-27 evening | OPEN |
| Q4 | Confirm the placeholder concepto-id patterns in G1–G5 (e.g. `concepto.dian.001.2003`) match the live corpus naming? | SME | G1, G2 launch | 2026-04-27 evening | OPEN |
| Q5 | The CST norm_id grammar (`cst.art.NN`) doesn't appear in fixplan_v3 §0.5 — is it the correct shape? | SME + engineering | J1, J2, J3, J4 | 2026-04-27 evening | OPEN |
| Q6 | Same question for `dcin.83`, `cco.art.N`, `res.banrep.1.2018` — confirm grammar additions or refuse and adjust filter shapes. | SME + engineering | K1, K2, K3 | 2026-04-27 evening | OPEN |

### §9.1 — Resolved

*(empty — first batches haven't launched)*

---

## §10 — Run log (append-only, newest first)

Format: same as `state_fixplan_v3.md` §10.

### 2026-04-27 night Bogotá — `state_canonicalizer_runv1.md` initial ship + bridge infra complete

**Author:** claude-opus-4-7
**Type:** misc (infra only; no batches yet)
**Sub-fix:** canonicalizer pre-flight infra
**Details:**

Built the three pieces of infrastructure required for fresh-LLM-runnable canonicalizer execution (per the `state_fixplan_v3.md` §2 fresh-LLM preconditions framing):

1. **`config/canonicalizer_run_v1/batches.yaml`** — 56 batch entries across 12 phases. Each entry has `batch_id`, `phase`, `wall_minutes_target`, `depends_on`, `norm_filter` (one of: prefix / regex / et_article_range / explicit_list), and `test_questions` (accountant-style, with `must_cite` / `must_not_cite` / `must_not_say` / `expected_chip_state` rules).
2. **`scripts/extract_vigencia.py --batch-id <X>`** — wired to the YAML config. Resolves the batch's norm slice from the corpus's deduplicated input set. Includes the **run-once guard** (refuses to launch if `evals/vigencia_extraction_v1/<batch_id>/` already has JSONs; bypassable only via `--allow-rerun`, operator-explicit). Writes per-batch output to `evals/vigencia_extraction_v1/<batch_id>/`.
3. **`scripts/run_batch_tests.py --batch-id <X> --mode {pre,post,score}`** — submits the batch's accountant-phrased questions to the chat backend (`scripts/eval/engine.ChatClient`), captures answer + citations + diagnostics, scores against the YAML's rules. Append-only ledger at `evals/canonicalizer_run_v1/ledger.jsonl`.

Plus three sanity smokes performed against the local stack:
- Built `evals/vigencia_extraction_v1/input_set.jsonl` from `artifacts/parsed_articles.jsonl` (11,392 unique norm_ids; 5,305 refusals — top reasons: missing_year 2,897, not_a_citation 2,406).
- Resolved 8 sample batch_ids (A1, A2, B7, B10, D1, D5, E4, G6) — every shape (prefix, regex, et_article_range, explicit_list) returns the expected slice.
- Verified the run-once guard correctly refuses launching when output dir is non-empty + `--allow-rerun` correctly bypasses.

Two fixture-related bugs caught and fixed:
- `scripts/build_extraction_input_set.py` was reading `article_id`/`text` keys, but the artifacts use `article_key`/`body`. Added all three field-name fallbacks. Now finds 7,922 chunks → 11,392 unique norm_ids.
- The doc filename was misspelled `canonicalizar` (Spanish verb); fixed to `canonicalizer` (English noun) per operator directive 2026-04-27. Renamed file + 8 internal references.

**Outcome:**
- §3 active state: "no batches launched; awaiting operator green-light on Gemini API access."
- §4 ledger seeded with all 56 batches, status = `not_started`.
- §7 environment state reflects the local docker stack post-§10 entry of `state_fixplan_v3.md` (corpus loaded, 7 fixture veredictos in place).
- §9 Q1–Q6 raised (all OPEN).

**Cross-references:**
- Related to `state_fixplan_v3.md` §10 latest entry (full v3 wiring through served retrieval).
- Plan: `canonicalizer_runv1.md`.
- Config: `config/canonicalizer_run_v1/batches.yaml`.
- Scripts: `scripts/extract_vigencia.py`, `scripts/run_batch_tests.py`.

**What's gated next (in order):**
1. Operator opens `LIA_GEMINI_API_KEY` for local-env.
2. Engineer launches A1 baseline → A1 extraction → A1 ingest → A1 verify → A1 score.
3. If A1 PASS, advance to A2; otherwise triage.

**Files added/modified this session:**
- *Renamed:* `docs/re-engineer/canonicalizar_runv1.md` → `docs/re-engineer/canonicalizer_runv1.md` (title + 8 internal references corrected).
- *Added:* `docs/re-engineer/state_canonicalizer_runv1.md` (this file).
- *Added:* `config/canonicalizer_run_v1/batches.yaml` (56 batches).
- *Added:* `scripts/run_batch_tests.py` (~370 LOC).
- *Modified:* `scripts/extract_vigencia.py` (added `--batch-id`, `--batches-config`, `--corpus-input-set`, `--guard-against-rerun`/`--allow-rerun`, `_resolve_batch_input_set()`).
- *Modified:* `scripts/build_extraction_input_set.py` (added `article_key`/`body` field-name fallbacks).

---

*v1 drafted 2026-04-27 night Bogotá (Claude). Append-only run log; in-place edits to §3 / §4 / §7 / §9 per protocol. Reading order for a fresh LLM: §1 → §2 → §3 → §4 (your assigned batch's row) → relevant §5 / §6 / §7 / §8 / §9 → start work.*
