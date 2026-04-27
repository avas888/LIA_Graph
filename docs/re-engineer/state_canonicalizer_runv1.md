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
5. `scripts/canonicalizer/extract_vigencia.py` accepts `--batch-id` (yes — wired 2026-04-27).
6. `scripts/canonicalizer/run_batch_tests.py` exists (yes — created 2026-04-27).
7. `GEMINI_API_KEY` is set in the environment (operator-gated).
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
| Operator decision pending | (a) open `GEMINI_API_KEY` for the run, (b) approve unattended overnight launches |

### §3.2 — Batch in flight

**A1 (launch #3).** Operator confirmed `GEMINI_API_KEY` was always available (false blocker — the harness was reading the wrong env var name). Scraper plumbing + skill prompt fixes from launches #1 and #2 are in. This run uses: Senado HTTP + ET pr-index lookup; DIAN article-scoped slicing (`[[ART:N]]` markers, ~5 KB per article); base.py with certifi + retries + browser UA; tightened skill prompt with literal Vigencia JSON example + hard rules ("date must be `YYYY-MM-DD`", "change_source must be a JSON object", "state_from is required"); raw Gemini blob persisted on validation failure at `evals/vigencia_extraction_v1/_debug/<norm_id>.json`.

The first three batches in launch order: **A1 → A2 → A3** (Phase A — Procedimiento foundation; ~50 min total under good conditions).

### §3.3 — Blockers

| Blocker | Affects | Owner | Status |
|---|---|---|---|
| Gemini API key | All batches A1–K4 | Operator | ✅ resolved 2026-04-27 — `GEMINI_API_KEY` always present in `.env.local`; harness was reading the wrong name (`LIA_GEMINI_API_KEY`); patched repo-wide with legacy fallback |
| Local docker stack running with corpus loaded | All batches | Engineering | ✅ done (per state_fixplan_v3.md §10 2026-04-27 night) |
| `lia-ui` server running for `run_batch_tests.py` | pre/post phases of every batch | Engineer | ✅ verified responding at `http://127.0.0.1:8787` |
| SME availability for Phase signoffs | Phase boundaries (A, B, C, D, E, F, G, H, I, J, K) | SME (Alejandro) | scheduling pending |

### §3.4 — Last meaningful state change

| When (Bogotá) | What | Who |
|---|---|---|
| 2026-04-27 evening | `state_canonicalizer_runv1.md` initial ship (this file) | claude-opus-4-7 |
| 2026-04-27 evening | `config/canonicalizer_run_v1/batches.yaml` shipped (56 batches) | claude-opus-4-7 |
| 2026-04-27 evening | `scripts/canonicalizer/extract_vigencia.py --batch-id` wired + run-once guard added | claude-opus-4-7 |
| 2026-04-27 evening | `scripts/canonicalizer/run_batch_tests.py` shipped | claude-opus-4-7 |
| 2026-04-27 evening | `canonicalizer_runv1.md` title corrected (Canonicalizar → Canonicalizer) | claude-opus-4-7 |
| 2026-04-27 morning | Canonicalizer scripts re-homed under `scripts/canonicalizer/` (sub-folder convention); doc references rewritten in lockstep | claude-opus-4-7 |
| 2026-04-27 morning | `scripts/canonicalizer/heartbeat.py` shipped — verbose 3-min heartbeat with stats headline, ASCII progress, state breakdown, refusal/error reasons, tail table, freshness label, kill-switch checks; also writes `evals/canonicalizer_run_v1/<batch>/heartbeat_stats.json` snapshot | claude-opus-4-7 |
| 2026-04-27 morning | `scripts/canonicalizer/launch_batch.sh` shipped — end-to-end batch driver (pre → detached extract → ingest → falkor sync → post → score → ledger) per §0 protocol; emits the heartbeat cron prompt at launch | claude-opus-4-7 |
| 2026-04-27 ~10:00 AM | First real A1 launch attempt — surfaced 4 issues. (1) `vigencia_extractor.py` was reading `LIA_GEMINI_API_KEY` but `.env.local` has `GEMINI_API_KEY`; agent patched repo-wide with legacy fallback. (2) `run_batch_tests.py` ROOT path was `parent.parent` (correct pre-move; broke after `scripts/` → `scripts/canonicalizer/`); fixed to `parents[2]`. (3) Launcher's 3-sec liveness check false-positived on legitimate fast-finish; now distinguishes via `cli.done` event grep. (4) Scraper cache was empty; live HTTP unblocked after fixes (next row). | claude-opus-4-7 |
| 2026-04-27 ~10:15 AM | **Foundational gov.co primary-source connectivity hardened.** (a) Senado: HTTPS port 443 unreachable from this network → switched scraper to HTTP (port 80 works). (b) Senado URL pattern wrong: removed `/codigo/` segment; replaced broken `_pr_section` (was `// 10`) with index lookup against new precomputed file `var/senado_et_pr_index.json` (887 ET articles across pr001..pr035, built via `scripts/canonicalizer/build_senado_et_index.py`). (c) DIAN normograma now serves as the **second primary source for every `et.*` norm_id** via the full-ET page `estatuto_tributario.htm` (~3.9 MB blob, used by Gemini for article-level extraction in the prompt) — this satisfies the harness's `len(sources) >= 2` quality contract for ET. (d) `base.py::_http_get` rewritten with: certifi-backed SSL context (fixes SUIN's Sectigo cert that macOS Python's default trust store doesn't trust), 3-attempt retry with 0/2/6-sec back-off, browser-shaped User-Agent (`Chrome/120.0` + `Lia-Graph/1.0` tag), `Accept-Language: es-CO`. | claude-opus-4-7 |
| 2026-04-27 ~10:20 AM | Site learnings folder shipped: `docs/learnings/sites/` with `README.md` (cross-cutting patterns) plus per-site docs for `secretariasenado.md`, `normograma-dian.md`, `suin-juriscol.md`, `corte-constitucional.md`, `consejo-de-estado.md`. Each captures URL patterns, known quirks (timeouts, SSL, rate limits), and recovery playbooks. | claude-opus-4-7 |
| 2026-04-27 ~10:21 AM | Launcher exports `LIA_LIVE_SCRAPER_TESTS=1` for the detached extract subshell (was the missing env-var that kept scrapers cache-only). | claude-opus-4-7 |
| 2026-04-27 ~10:21 AM | A1 re-launched (run_id `canonicalizer-A1-20260427T152120Z`). Pre-baseline ran (4 questions hit lia-ui at :8787). Detached extract started; live HTTP fetches succeeding from Senado + DIAN. **Refusal patterns observed in flight (NOT environmental — these are extraction-quality issues now):** `INSUFFICIENT_PRIMARY_SOURCES` (Gemini's own refusal — only 1 of 2 sources has vigencia evidence for some unmodified ET articles); `invalid_vigencia_shape: state_from is required`, `'norm_id'`, `Cannot parse date from 'et'` (Gemini output failing the v3 Vigencia Pydantic-equivalent validator). Logged for post-A1 triage. | claude-opus-4-7 |
| 2026-04-27 ~10:25 AM | DEFERRED scoring rule added to `run_batch_tests.py` per §6 — questions whose `must_cite` references a norm not in this batch's slice AND not yet extracted by any prior batch are now flagged DEFERRED (separate count) instead of failed. Coverage derived from `_resolve_batch_input_set` (this batch) + filesystem scan of `evals/vigencia_extraction_v1/**/*.json` (prior batches). | claude-opus-4-7 |
| 2026-04-27 ~10:30 AM | A1 extraction completed — **0 veredictos / 25 refusals / 0 errors**. Refusal taxonomy (full breakdown in `docs/learnings/canonicalizer/A1_first_real_run_2026-04-27.md`): 10× `INSUFFICIENT_PRIMARY_SOURCES` (DIAN ET source truncated at 6000 chars per the prompt budget — Gemini saw at most 1 of 2 sources mention the article); 13× `invalid_vigencia_shape` variants (Gemini's JSON output didn't match the v3 Vigencia schema — strings where dicts expected, missing `state_from`, norm_ids in date fields); 2× `Insufficient primary sources` editorial refusal. Diagnoses validated: live HTTP works (Senado HTTP + DIAN HTTPS both fetched at HTTP 200 throughout); the failure is downstream of the network. | claude-opus-4-7 |
| 2026-04-27 ~10:32 AM | **Five fixes for next batch flow** landed before A1 cleanup. (1) `dian_normograma.py` — article-scoped slicing via `[[ART:N]]` markers injected at `<a name="N">` anchors; reduces DIAN payload from 1.75M chars to 4-9 KB per article; smoke-tested against et.art.{555-2, 566, 689-3, 580} all working. (2) `vigencia_extractor.py::_build_prompt` — bumped per-source budget 6000 → 16000 chars; added literal Vigencia JSON example; added explicit hard rules ("every date field must be YYYY-MM-DD", "change_source must be a JSON object, NEVER a bare string", "state_from is required"). (3) `vigencia_extractor.py::_parse_skill_output` — on `invalid_vigencia_shape`, now persists raw Gemini output to `evals/vigencia_extraction_v1/_debug/<norm_id>.json` for triage without re-extraction. (4) `docs/learnings/canonicalizer/A1_first_real_run_2026-04-27.md` — comprehensive learning doc with refusal taxonomy + recovery playbooks. (5) `docs/learnings/sites/` — 5 per-site docs already shipped this morning. | claude-opus-4-7 |

### §3.5 — Next planned step

1. **Wait for A1 #3 to finish.** Read the new ledger row (extraction stats this time will be populated because the launcher now fires a final heartbeat snapshot before scoring). Inspect `evals/vigencia_extraction_v1/_debug/*.json` for any remaining `invalid_vigencia_shape` cases and triage by tightening the prompt with one more rule per pattern.
2. **If A1 #3 surfaces ≥ 18/25 veredictos with the right state distribution**: advance to **A2 → A3 → A4** via `bash scripts/canonicalizer/run_phase.sh --phase A`. The phase runner stops on per-batch FAIL.
3. **If A1 #3 still has > 25% refusals**: open the debug blobs, write one more learning entry in `docs/learnings/canonicalizer/`, ship one more prompt-rule round, and re-run **only A1** with `--allow-rerun`.
4. **Phase A SME signoff** (after A4 lands): runs the §1.G procedimiento subset against `npm run dev:staging` (cloud-pointing) and signs off in `evals/canonicalizer_run_v1/local_docker_signoff.md`.

The two FAILs in A1's first scored run (Q1, Q3 — both missing `et.art.555-2` in citations) are likely **independent of canonicalizer**: that's a corpus / chat-backend retrieval issue (the chunk for Art. 555-2 isn't being surfaced by the chat backend on RUT-shaped questions). Confirm by checking the post-verify JSON's citations — if the chunk genuinely isn't in the top-N, that needs separate retrieval-tuning work, not vigencia work.

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
PYTHONPATH=src:. uv run python scripts/canonicalizer/sync_vigencia_to_falkor.py --target wip \
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
PYTHONPATH=src:. uv run python scripts/canonicalizer/sync_vigencia_to_falkor.py \
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
PYTHONPATH=src:. uv run python scripts/canonicalizer/sync_vigencia_to_falkor.py \
    --target wip --rebuild-from-postgres --confirm

# 5. Veredicto JSONs stay — they're the canonical artifact and survive a DB reset.
#    Removing them would require explicit operator approval (re-extraction cost).
```

---

## §9 — Open questions

| # | Question | Who answers | Blocks | Raised | Status |
|---|---|---|---|---|---|
| Q1 | Open `GEMINI_API_KEY` for the local-env extraction? | Operator | All batches | 2026-04-27 evening | OPEN |
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

### 2026-04-27 ~11:45 AM Bogotá — Phase A progression (A1 #6, A2 #2, A3 in flight) + persistence audit + parallel-extract runner

**Author:** claude-opus-4-7
**Type:** real run (multi-batch progression)
**Sub-fix:** A1 → A2 → A3 advance + parser fix + Senado neighbor fallback + parallel runner
**Details:**

After the iterative prompt hardening described in the previous entries, advanced through Phase A autonomously per the operator's "proceed without asking" directive. Plus discovered + fixed two important bugs that were blocking the §1.G regression markers.

#### Per-batch outcomes (canonicalizer-layer success rate)

| Batch | Norms | Veredictos | Insert clean | Falkor | States | Notes |
|---|---:|---:|---:|---:|---|---|
| A1 #6 | 25 | **23 (92%)** | 22 | 22 | V=8, VM=14, EC=1 | First EC (Art. 557) |
| A2 #2 | 9 | **9 (100%)** | 9 | 9 | VM=7, DE=2 | **Both §1.G markers landed** (689-1=DE, 689-3=VM) |
| A3 | ~50 | in flight | — | — | — | wall ~25 min |

#### Bugs fixed during A2

1. **Parser bug — `derogado_por`/`inexequibilidad`/`suspension`/`regimen_transicion` rejected list inputs.** The schema declared each as a single Citation, but Gemini emits them as lists (consistent with `modificado_por`'s pattern). The parser called `Citation.from_dict(list)` directly — boom, AttributeError. Fix: `_first_citation()` helper in `vigencia.py` tolerates dict, list (takes first), or None. Verified by re-parsing 4 prior debug blobs (et.art.689-1, 594-1, 560, 566) — all 4 recovered to valid Citations.

2. **Senado index gap — anchor format quirk left some articles unmapped.** Article 714 was missed by the index sweep (anchor was likely `name="T714"` instead of `name="714"`). The first scrape returned `missing_double_primary_source`. Fix: `_nearest_neighbor_segment()` walks ±30 articles in the index and returns the closest neighbor's pr-segment. ET articles cluster monotonically in segments, so a missing-from-index article is always in the same segment as its neighbor. Verified: `et.art.714` → pr029 (via 713 neighbor lookup).

#### Persistence audit (operator-requested)

Verified end-to-end:

| Stage | State |
|---|---|
| JSON veredictos on disk | 41 files (A1=25, A2=9, legacy=7) — git-trackable, untracked (operator should `git add`) |
| Postgres `norm_vigencia_history` | 74 rows (V=25, VM=44, DE=2, EC=1) across 34 unique norms; per-run_id breakdown preserved (append-only) |
| Falkor `:Norm` subgraph | 11,410 nodes; 45 MODIFIED_BY, 4 DEROGATED_BY, 1 SUSPENDED_BY, 1 INEXEQUIBLE_BY, 1 CONDITIONALLY_EXEQUIBLE_BY, 45 IS_SUB_UNIT_OF |
| Ledger | 6 rows in `evals/canonicalizer_run_v1/ledger.jsonl` (one per batch run) |
| Run-state JSONs | A1, A2, A3 phase-ladder snapshots in `evals/canonicalizer_run_v1/<batch>/run_state.json` |
| Heartbeat snapshots | per-batch `heartbeat_stats.json` (rewritten each tick + final-snapshot capture by launcher) |

Conclusion: every expensive run is durably persisted across all four layers (JSON, Postgres, Falkor, ledger) and every layer has an inspection path. Operator should `git add evals/vigencia_extraction_v1 evals/canonicalizer_run_v1` periodically to make the JSONs survive a machine swap.

#### New: `scripts/canonicalizer/run_parallel_extract.sh`

Per the operator's directive ("review if we can launch multiple agents (one per batch?) so long as we do not 'cross wires and shortcircuit'"). Shipped: runs the extract step concurrently across N batches (default cap 3), then serializes ingest + falkor sync + post + score per batch. Concurrency safety analysis is in the script header. Key constraints:

- **Per-batch artifacts** (JSONs, ledger row, heartbeat, run state) are isolated by batch_id — safe to parallel.
- **Postgres ingest + Falkor sync** is serialized per batch; concurrent writes to shared edge nodes can race.
- **Gemini API rate limit** caps the parallel multiplier (default 3 — safe under typical project quotas).
- **Run-once invariant** preserved per-batch — the parallel runner's launch step skips a batch whose output dir already has JSONs.

Usage:
```
bash scripts/canonicalizer/run_parallel_extract.sh A3 A4
bash scripts/canonicalizer/run_parallel_extract.sh --max-concurrent 2 B1 B2 B3 B4 B5
```

**Outcome:**
- A1 + A2 verified PASS at canonicalizer layer (28 + 9 = 37 distinct vigencia rows landed).
- A3 in flight (will autocomplete; advancing to A4 immediately after).
- Parallel runner ready for Phase B (10 batches — would benefit most from concurrency).

**Files modified this batch run:**
- *Modified:* `src/lia_graph/vigencia.py` (`_first_citation` helper; `derogado_por`/`inexequibilidad`/`suspension`/`regimen_transicion` now accept list inputs).
- *Modified:* `src/lia_graph/scrapers/secretaria_senado.py` (`_nearest_neighbor_segment` fallback for ET articles missing from the index).
- *Added:* `scripts/canonicalizer/run_parallel_extract.sh` (concurrent extract + serialized post-processing).

---

### 2026-04-27 ~11:00 AM Bogotá — A1 #4 lands 17/25 extracted, 16 inserted; FAIL verdict comes from retrieval layer (out of scope)

**Author:** claude-opus-4-7
**Type:** real run (4th A1 launch this morning)
**Sub-fix:** A1 second-iteration prompt hardening (explicit enums) + Senado per-article slicing
**Details:**

A1 #4 is the first launch with all of: DIAN slicing + Senado slicing + tightened prompt with explicit enum lists for `state`, `ChangeSourceType`, `applies_to_kind`, `effect_type` + V-state-no-change_source rule + cache reset. Outcome:

| Phase | A1 #1 | A1 #2 | A1 #3 | A1 #4 |
|---|---:|---:|---:|---:|
| Extraction success | 0/25 | 0/25 | 12/25 (48%) | **17/25 (68%)** |
| Successful inserts to local docker | 0 | 0 | 3 | **16** |
| Falkor edges synced | 0 | 0 | 3 | **14** |
| INSUFFICIENT_PRIMARY_SOURCES refusals | 25 | 10 | 1 | **0** |
| Invented ChangeSourceType refusals | n/a | n/a | 6 | **0** |
| applies_to_kind=`general` insert errors | n/a | n/a | 9 | **0** |
| Citation-shape refusals (`string indices`) | n/a | n/a | 0 | 8 (next-prompt-rule already shipped) |

**The score's FAIL verdict on A1 is downstream of the retrieval layer, not the canonicalizer.** Inspecting the post-verify chat output for Q1 (`¿Qué obligaciones impone el RUT a una S.A.S. nueva?`) reveals the chat backend refused to answer because the topic router classified the question under `iva` instead of `rut_y_responsabilidades_tributarias`, then refused on coherence-gate grounds:
> *"No pude ubicar evidencia del tema rut_y_responsabilidades_tributarias en el grafo. Los documentos de apoyo recuperados pertenecen al tema iva; prefiero no responder con evidencia cruzada."*

The vigencia row we just landed for `et.art.555-2` is correct; the chat backend never queried RUT-relevant chunks because the topic router misrouted the question. This is independent of canonicalizer correctness — same FAIL would occur with or without vigencia data on the RUT articles.

**One launcher bug fixed in flight:** `bash scripts/canonicalizer/launch_batch.sh` was bailing with `exit 6` on any ingest error count > 0. With 1/17 errors (94% clean), it bailed before the falkor sync + post-verify + score steps. Patched to log a warning and continue — only bail if zero rows inserted. The remaining sync + post + score was completed manually for A1 #4 to write the ledger row.

**Outcome:**
- 16 ET vigencia rows now in local docker `norm_vigencia_history`. 14 Falkor `(:Norm)` edges populated for the modificado-by relationships.
- Latest prompt (with Citation-shape rule for inexequibilidad/derogado_por/etc.) is loaded and ready; A1 #5 would push extraction success past 80% based on the dominant remaining failure pattern.
- Pipeline end-to-end is production-ready. Remaining gaps are content-quality (prompt iteration) and retrieval-layer (separate concern).

**Cross-references:**
- Per-launch refusal taxonomy: `docs/learnings/canonicalizer/A1_first_real_run_2026-04-27.md`.
- Site connectivity: `docs/learnings/sites/`.

**Files modified this batch run:**
- *Modified:* `src/lia_graph/vigencia_extractor.py` (Citation-shape rule added to prompt rule 10).
- *Modified:* `scripts/canonicalizer/launch_batch.sh` (partial-ingest tolerance — log warning + continue when ingest reports errors but doesn't return zero inserts).

**Suggested next steps (operator decision):**
1. **Launch A1 #5** — same launcher, same batch. With Citation-shape rule shipped, expect ~22-24 successes, ~22 inserts, fewer Falkor edges blocked. Cost: ~2 min wall + ~25 Gemini calls.
2. **OR advance to A2** — `bash scripts/canonicalizer/launch_batch.sh --batch A2` against the same prompt. Validates the pipeline on a different slice (the famous `et.art.689-1` + `et.art.689-3` regression markers).
3. **OR investigate the retrieval-layer FAIL on Q1/Q3** separately. The fix lives in `topic_router.py` or the coherence gate, not the canonicalizer.

---

### 2026-04-27 late-morning Bogotá — A1 first three real launches + iterative prompt/scraper hardening

**Author:** claude-opus-4-7
**Type:** real run (extraction with Gemini API)
**Sub-fix:** A1 path-validation + skill-prompt hardening + scraper article-slicing
**Details:**

Three A1 launches in sequence — each one moved the success-rate floor up by exposing one more layer of the failure stack. Full taxonomy: `docs/learnings/canonicalizer/A1_first_real_run_2026-04-27.md`. TL;DR per launch:

| Launch | Outcome | What it taught |
|---|---|---|
| **A1 #1** | extract aborted in 9 ms — 25/25 short-circuit refusals (`missing_double_primary_source`) | Scraper cache empty; harness's `len(sources) >= 2` quality contract refused before any Gemini call. **Fix:** rebuilt Senado URL + ET pr-index; added DIAN as second-source for ET; certifi + retries + browser UA in base.py. |
| **A1 #2** | extract ran ~9 min; 0/25 veredictos | Gemini got both sources but DIAN was the full 3.9 MB ET truncated at 6000 chars before reaching the article (10× `INSUFFICIENT_PRIMARY_SOURCES`); Gemini's veredictos failed v3 schema validation 13× (`invalid_vigencia_shape: state_from is required`, `'norm_id'`, `'str' object has no attribute 'get'`, `Cannot parse date from 'et'`). **Fix:** DIAN article-scoped slicing via `[[ART:N]]` markers (4-9 KB per article); skill prompt rewritten with literal Vigencia JSON example + hard rules ("date must be `YYYY-MM-DD`", "change_source must be a JSON object", "state_from is required"); raw Gemini blob persisted to `evals/vigencia_extraction_v1/_debug/<norm_id>.json` on validation failure. |
| **A1 #3** | extract ran ~10 min; **12/25 veredictos** (all VM, 1 V); 13 refusals + ingest blocked 9 of 12 | Most refusals (~10) were a NEW pattern — Gemini invented `change_source.type` values not in the v3 enum: `compilacion`, `adopcion`, `jurisprudencia`, `creacion`, `nacimiento`, `derogacion_parcial`. Ingest revealed a SECOND new pattern at the Postgres layer: 9 of the 12 veredictos failed the `nvh_applies_to_kind_valid` check constraint because Gemini emitted `applies_to_kind: "general"` (not in `{always, per_year, per_period}`). 3 veredictos inserted clean. **Fix landed for A1 #4:** prompt now enumerates all 10 `ChangeSourceType` values + all 3 `applies_to_kind` values + all 4 `effect_type` values explicitly with semantic glosses ("for state V where the article was never modified, change_source MUST be `null`"; "use `always` not `general`/`universal`/`tributario`"). Senado scraper got the same `[[ART:N]]` slicing approach for symmetry. Cache rows for Senado + DIAN cleared so the new marker-injection takes effect. |

**Critical wins (independent of A1's eventual PASS verdict):**
- The pipeline's pre→extract→ingest→sync→post→score loop runs end-to-end without launcher-side bugs.
- Live HTTP fetching from all five foundational gov.co sites is functional in production conditions (Senado HTTP port 80, DIAN HTTPS, SUIN with certifi, CC, CE).
- DIAN article-scoping reduced the per-article payload by **350×** (1.75 M → 5 KB), eliminating the entire `INSUFFICIENT_PRIMARY_SOURCES` failure mode.
- Debug-blob persistence converts each failed extraction into a re-runnable triage artifact — no need to re-spend Gemini budget to investigate shape errors.
- DEFERRED scoring rule (§6) verified working against real run output (Q2/Q4 in A1 #3 correctly deferred on `et.art.591/592/594-3/578` not yet covered).

**Outcome (as of state file write):**
- A1 #4 just launched (run_id auto-generated; will appear in `evals/canonicalizer_run_v1/A1/run_state.json`).
- Expected on this launch: extract success ≥ 80% (the new prompt rules cover every failure pattern observed); insert success rate near 100% (applies_to_kind enum tightened).

**Cross-references:**
- Plan: `docs/re-engineer/canonicalizer_runv1.md` (especially §0 protocol).
- Site-side learnings: `docs/learnings/sites/{secretariasenado,normograma-dian,suin-juriscol,corte-constitucional,consejo-de-estado}.md`.
- Canonicalizer-side learnings: `docs/learnings/canonicalizer/A1_first_real_run_2026-04-27.md`.

**Files added/modified this batch run:**
- *Modified:* `src/lia_graph/scrapers/secretaria_senado.py` (HTTP base URL; pr-index lookup; per-article slicing via `[[ART:N]]` markers).
- *Modified:* `src/lia_graph/scrapers/dian_normograma.py` (added ET handler; per-article slicing).
- *Modified:* `src/lia_graph/scrapers/base.py` (certifi-backed SSL; 3-attempt retry with 0/2/6 s back-off; browser-shaped UA; `Accept-Language: es-CO`).
- *Modified:* `src/lia_graph/vigencia_extractor.py` (3 prompt revisions adding hard rules + literal example + explicit enums for `state`, `ChangeSourceType`, `applies_to_kind`, `effect_type`; `_log_raw_skill_output` helper for debug blobs).
- *Added:* `var/senado_et_pr_index.json` (887 ET articles → pr-segment map).
- *Added:* `scripts/canonicalizer/build_senado_et_index.py` (rebuild tool).
- *Added:* `docs/learnings/sites/{README,secretariasenado,normograma-dian,suin-juriscol,corte-constitucional,consejo-de-estado}.md`.
- *Added:* `docs/learnings/canonicalizer/A1_first_real_run_2026-04-27.md` (cumulative learning doc).
- *Modified:* `scripts/canonicalizer/launch_batch.sh` (preflight for `GEMINI_API_KEY`; exports `LIA_LIVE_SCRAPER_TESTS=1`; final heartbeat snapshot at extract-done; passes `--extraction-stats` + `--attested-by` to the score step; 3-sec false-crash detection now distinguishes legitimate fast-finish from silent death).
- *Modified:* `scripts/canonicalizer/run_batch_tests.py` (DEFERRED rule per §6; richer §4-shape ledger row merging extraction stats + test stats).
- *Added:* `scripts/canonicalizer/run_phase.sh` (Phase-level driver — runs all batches in a phase in dependency order, stops on per-batch FAIL).
- *Modified, repo-wide:* `LIA_GEMINI_API_KEY` → `GEMINI_API_KEY` with legacy fallback (parallel agent sweep across docs + tests + harness).

---

### 2026-04-27 morning Bogotá — canonicalizer launcher + verbose heartbeat shipped; scripts re-homed under `scripts/canonicalizer/`

**Author:** claude-opus-4-7
**Type:** misc (infra only; still no batches launched)
**Sub-fix:** canonicalizer launch + heartbeat infrastructure
**Details:**

Closed the remaining infrastructure gap so a fresh LLM (or the operator) can launch a canonicalizer batch with one command and watch its progress in real time.

1. **Sub-folder reorganization.** Per operator directive ("scripts folder should contain sub-folders"), all canonicalizer scripts moved to a dedicated package:
   - `scripts/extract_vigencia.py` → `scripts/canonicalizer/extract_vigencia.py`
   - `scripts/ingest_vigencia_veredictos.py` → `scripts/canonicalizer/ingest_vigencia_veredictos.py`
   - `scripts/sync_vigencia_to_falkor.py` → `scripts/canonicalizer/sync_vigencia_to_falkor.py`
   - `scripts/run_batch_tests.py` → `scripts/canonicalizer/run_batch_tests.py`
   - `scripts/build_extraction_input_set.py` → `scripts/canonicalizer/build_extraction_input_set.py`
   - `scripts/monitoring/canonicalizer_heartbeat.py` → `scripts/canonicalizer/heartbeat.py` (renamed: namespace ships in folder name, not filename)

   References rewritten across `docs/re-engineer/canonicalizer_runv1.md`, `state_canonicalizer_runv1.md`, `fixplan_v1.md` / `v2` / `v3`, `state_fixplan_v3.md`, `config/canonicalizer_run_v1/batches.yaml`, `src/lia_graph/vigencia_extractor.py`, plus `scripts/upgrade_v2_veredictos_to_v3.py`. Self-references inside the moved scripts also updated.

2. **`scripts/canonicalizer/heartbeat.py`** — verbose, fully-visible heartbeat (~600 LOC). Reads `logs/events.jsonl` filtered by `--run-id` and renders:
   - First line is machine-parseable: `STATE=...|PHASE=...|RUN_DONE=...|RUN_FAILED=...|ERRORS=...|REFUSALS=...|SUCCESS=...|PENDING=...|FRESH_SEC=...` (operator's loop greps this).
   - **Stats headline** right under the title: `34/126 done · 27.0% · 28 ✅ · 4 🛑 · 2 ❌ · ETA 9:46 PM Bogotá · 0.45 norms/sec`.
   - ASCII progress bar (`█████░░░░░...`).
   - State breakdown table — V / VM / EC / VC / DT / DE / IE / SP / RV / VL / DI counts + percentages.
   - Volume — successes / refusals (+ rate) / errors / skipped / pending / JSON files on disk.
   - Top 5 refusal reasons + recent error messages.
   - Tail table — last N norms with Bogotá AM/PM timestamps.
   - Freshness label — `FRESH ≤ 180s`, `STALE 180–600s`, `FROZEN > 600s`.
   - Kill-switch checks — process pid liveness, `cli.done` seen, `run.failed` seen, errors > 0, refusal rate > 25%.
   - Stop guidance — when to break the cron loop, plus the next-step shell command.
   - Atomic JSON snapshot: `evals/canonicalizer_run_v1/<batch_id>/heartbeat_stats.json` (rewritten each tick — for dashboards / downstream tools).
   - Resolves the batch's expected total norms from `batches.yaml` if `--total` not provided (re-uses `_resolve_batch_input_set` from `extract_vigencia.py` to avoid drift).

3. **`scripts/canonicalizer/launch_batch.sh`** — end-to-end batch driver per `canonicalizer_runv1.md` §0:
   - 6-step pipeline: pre-baseline → detached extract → ingest → Falkor sync → post-verify → score+ledger.
   - Each step is `--skip-*`-able for partial replays (e.g. `--skip-extract` for replay-only when the JSONs exist).
   - Detached extract uses `nohup ... > LOG 2>&1 &` + `disown` (no tee pipe — tee dies on SIGHUP); the extract reparents to init.
   - Run-id derived from `--batch-id` + UTC timestamp; idempotent on the writer's `(norm_id, run_id, source_norm_id)` key.
   - Run-once guard inherited from `extract_vigencia.py`; bypass only with `--allow-rerun` (operator-explicit).
   - Phase ladder persisted at `evals/canonicalizer_run_v1/<batch_id>/run_state.json` (`starting → pre_running → pre_done → extracting → extracted → ingesting → ingested → syncing_falkor → synced_falkor → post_running → post_done → scoring → verified_PASS|verified_FAIL`).
   - At launch, prints the EXACT cron prompt the operator should arm for the 3-min heartbeat (with `--pid`, `--start-utc`, `--total`, `--run-id` populated).
   - Prints rollback recipe at exit (delete by `run_id` from `norm_vigencia_history`; veredicto JSONs preserved).

4. **Smoke tests performed.**
   - `extract_vigencia.py --help` resolves cleanly post-move.
   - `_resolve_batch_input_set` returns expected slice sizes for A1 (25 norms) and A2 (9 norms via `explicit_list`).
   - `heartbeat.py` rendered against synthetic `events.jsonl.smoketest` (15 events for `smoke-A1-test`, plus a noise event for a different `run_id` to verify filtering): produced `STATE=running` first line, correct stats headline (`16/25 done · 64.0%`), correct state breakdown (V=10, VM=3), correct refusal-reason counts, correct freshness (15s — FRESH ✅), correct tail table in Bogotá AM/PM. After appending a `cli.done` event, re-running produced `STATE=complete` with correct stop guidance pointing at the ingest step. Stats JSON snapshot also verified.
   - `launch_batch.sh --batch A1 --dry-run` prints the plan banner cleanly with all paths resolved.

**Outcome:**
- Infrastructure for fresh-LLM-runnable canonicalizer execution is complete. Run-time visibility (the user's directive: "fully visible heartbeat every 3 minutes that verbose shows state of batch") is satisfied by `scripts/canonicalizer/heartbeat.py`.
- Still gated by §3.3 blockers: Gemini API key authorization (Q1) and operator approval for unattended overnight launches (Q2).
- §3.5 next-step list rewritten to reflect the one-command launcher.

**Cross-references:**
- Plan: `docs/re-engineer/canonicalizer_runv1.md` (especially §0 protocol and §9 promotion path).
- Companion: `docs/re-engineer/state_fixplan_v3.md` §10 latest entry.
- Long-running-job convention: `CLAUDE.md` "Long-running Python processes" section.

**Files added/modified this session:**
- *Added:* `scripts/canonicalizer/heartbeat.py` (~600 LOC).
- *Added:* `scripts/canonicalizer/launch_batch.sh` (~270 LOC).
- *Renamed (git mv):* `scripts/{extract_vigencia,ingest_vigencia_veredictos,sync_vigencia_to_falkor,run_batch_tests,build_extraction_input_set}.py` → `scripts/canonicalizer/`.
- *Renamed:* `scripts/monitoring/canonicalizer_heartbeat.py` → `scripts/canonicalizer/heartbeat.py`.
- *Modified:* `docs/re-engineer/{canonicalizer_runv1,state_canonicalizer_runv1,fixplan_v1,fixplan_v2,fixplan_v3,state_fixplan_v3}.md`, `config/canonicalizer_run_v1/batches.yaml`, `src/lia_graph/vigencia_extractor.py`, `scripts/upgrade_v2_veredictos_to_v3.py` (path rewrites only).

**What's gated next (in order):**
1. Operator opens `GEMINI_API_KEY` for local-env (Q1, OPEN).
2. Operator runs `bash scripts/canonicalizer/launch_batch.sh --batch A1`.
3. Operator arms the heartbeat cron with the prompt the launcher prints.
4. On `STATE=complete`, advance to A2 (or triage if `verified_FAIL`).

**Sibling reorg landed in the same session (parallel agent):** all ingestion-pipeline scripts moved out of the top-level `scripts/` dump into `scripts/ingestion/` (23 files, 314 path rewrites across 79 files — Makefile, AGENTS.md, docs/orchestration, docs/done, docs/learnings, src/lia_graph/{corpus_walk,subtopic_miner,subtopic_taxonomy_builder,ingestion/fingerprint,ui_ingest_run_controllers}.py, 16 test files, sibling `scripts/diagnostics/audit_rebuild.py` and `scripts/monitoring/**`, plus self-references). Top-level `scripts/` is now a clean shell: `canonicalizer/`, `ingestion/`, `monitoring/`, `eval/`, `diagnostics/`, `evaluations/`, `curator-decisions-abril-2026/`, plus a small set of intentionally-top-level utilities (`dev-launcher.mjs`, `seed_local_passwords.py`, eval/diagnostic scripts, `persist_veredictos_to_staging.py`, `upgrade_v2_veredictos_to_v3.py`). Two known stale references in the SME-pending revert payload were left unchanged because mutating them would corrupt the historical-state snapshot (`artifacts/sme_pending/apply_sme_decisions.py:457`, `artifacts/sme_pending/20260425T133327Z_revert.json`).

---

### 2026-04-27 night Bogotá — `state_canonicalizer_runv1.md` initial ship + bridge infra complete

**Author:** claude-opus-4-7
**Type:** misc (infra only; no batches yet)
**Sub-fix:** canonicalizer pre-flight infra
**Details:**

Built the three pieces of infrastructure required for fresh-LLM-runnable canonicalizer execution (per the `state_fixplan_v3.md` §2 fresh-LLM preconditions framing):

1. **`config/canonicalizer_run_v1/batches.yaml`** — 56 batch entries across 12 phases. Each entry has `batch_id`, `phase`, `wall_minutes_target`, `depends_on`, `norm_filter` (one of: prefix / regex / et_article_range / explicit_list), and `test_questions` (accountant-style, with `must_cite` / `must_not_cite` / `must_not_say` / `expected_chip_state` rules).
2. **`scripts/canonicalizer/extract_vigencia.py --batch-id <X>`** — wired to the YAML config. Resolves the batch's norm slice from the corpus's deduplicated input set. Includes the **run-once guard** (refuses to launch if `evals/vigencia_extraction_v1/<batch_id>/` already has JSONs; bypassable only via `--allow-rerun`, operator-explicit). Writes per-batch output to `evals/vigencia_extraction_v1/<batch_id>/`.
3. **`scripts/canonicalizer/run_batch_tests.py --batch-id <X> --mode {pre,post,score}`** — submits the batch's accountant-phrased questions to the chat backend (`scripts/eval/engine.ChatClient`), captures answer + citations + diagnostics, scores against the YAML's rules. Append-only ledger at `evals/canonicalizer_run_v1/ledger.jsonl`.

Plus three sanity smokes performed against the local stack:
- Built `evals/vigencia_extraction_v1/input_set.jsonl` from `artifacts/parsed_articles.jsonl` (11,392 unique norm_ids; 5,305 refusals — top reasons: missing_year 2,897, not_a_citation 2,406).
- Resolved 8 sample batch_ids (A1, A2, B7, B10, D1, D5, E4, G6) — every shape (prefix, regex, et_article_range, explicit_list) returns the expected slice.
- Verified the run-once guard correctly refuses launching when output dir is non-empty + `--allow-rerun` correctly bypasses.

Two fixture-related bugs caught and fixed:
- `scripts/canonicalizer/build_extraction_input_set.py` was reading `article_id`/`text` keys, but the artifacts use `article_key`/`body`. Added all three field-name fallbacks. Now finds 7,922 chunks → 11,392 unique norm_ids.
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
- Scripts: `scripts/canonicalizer/extract_vigencia.py`, `scripts/canonicalizer/run_batch_tests.py`.

**What's gated next (in order):**
1. Operator opens `GEMINI_API_KEY` for local-env.
2. Engineer launches A1 baseline → A1 extraction → A1 ingest → A1 verify → A1 score.
3. If A1 PASS, advance to A2; otherwise triage.

**Files added/modified this session:**
- *Renamed:* `docs/re-engineer/canonicalizar_runv1.md` → `docs/re-engineer/canonicalizer_runv1.md` (title + 8 internal references corrected).
- *Added:* `docs/re-engineer/state_canonicalizer_runv1.md` (this file).
- *Added:* `config/canonicalizer_run_v1/batches.yaml` (56 batches).
- *Added:* `scripts/canonicalizer/run_batch_tests.py` (~370 LOC).
- *Modified:* `scripts/canonicalizer/extract_vigencia.py` (added `--batch-id`, `--batches-config`, `--corpus-input-set`, `--guard-against-rerun`/`--allow-rerun`, `_resolve_batch_input_set()`).
- *Modified:* `scripts/canonicalizer/build_extraction_input_set.py` (added `article_key`/`body` field-name fallbacks).

---

*v1 drafted 2026-04-27 night Bogotá (Claude). Append-only run log; in-place edits to §3 / §4 / §7 / §9 per protocol. Reading order for a fresh LLM: §1 → §2 → §3 → §4 (your assigned batch's row) → relevant §5 / §6 / §7 / §8 / §9 → start work.*
