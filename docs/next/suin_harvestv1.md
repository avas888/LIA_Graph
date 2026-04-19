# SUIN Harvest v1 — Implementation Plan

---

## ⚠️ COLD-START PROTOCOL — READ THIS FIRST

**If you are a fresh agent just told to "implement `docs/next/suin_harvestv1.md`", do these checks in order before any other action. Each check has a copy-paste command and an explicit stop-condition. Skipping this block is how a cold agent trips.**

### 0. You cannot fire any cloud write without explicit user confirmation in this session

Phase 7 writes to production cloud Supabase + production cloud FalkorDB. **That step is irreversible.** If the user has not said "go" or "fire phase 7" in the current conversation, **stop at the end of Phase 6 and ask.** Do not infer approval from context, a TODO, or previous sessions. Cloud writes are a human-in-the-loop gate, always.

### 1. You must be on the right branch with the right base commit

The Phase A + Phase B infrastructure (fetcher, parser, bridge, sink extensions, ingest wiring, tests) already exists on `feat/suin-ingestion`. **On `main` that code does not exist** and you would incorrectly try to re-implement it.

```
git rev-parse --abbrev-ref HEAD
# expected: feat/suin-ingestion
git log --oneline -1 -- src/lia_graph/ingestion/suin/bridge.py
# expected: a commit exists (proves the infrastructure is in this branch)
```

**Stop if either check fails.** Ask the user which branch to switch to — do not `git checkout` or `git stash` on your own.

### 2. Verify the state tracker below — that's your source of truth

Scroll to the "Resumable state tracker" table. Find the **first row whose Status is not `done`**. That is your current phase. If every row says `done`, there is nothing to do — ask the user.

Do not trust chat history, memory, or prior commits over this table. The table's "Proof-of-completion" column is the contract — if it's not verifiable in the repo, that phase is not done regardless of what anyone says.

### 3. Preconditions the plan assumes are true

Run each command. If any fails, capture the failure and **stop**. Ask the user to resolve before you continue. Do not attempt autonomous fixes for environment issues.

```
# a) Dependencies installed (needs httpx, bs4, lxml from Phase A)
PYTHONPATH=src:. uv run python -c "import httpx, bs4, lxml; print('deps ok')"
# if it fails: uv sync --extra dev

# b) Local docker Supabase running (needed for all WIP phases)
supabase status 2>&1 | head -5
# expected: "supabase local development setup is running"
# if it fails: user must run `supabase start`

# c) Local docker Falkor running (needed for phases 2–5)
redis-cli -h 127.0.0.1 -p 6389 PING
# expected: PONG
# if it fails: user must start the lia-falkor-smoke container

# d) Cloud + WIP Supabase credentials present (in .env.staging)
test -f .env.staging && grep -E '^SUPABASE_(URL|WIP_URL|SERVICE_ROLE_KEY|WIP_SERVICE_ROLE_KEY)=' .env.staging | wc -l
# expected: 4
# if it fails: ask the user to provide credentials

# e) SUIN reachability (robots.txt fetch)
LIA_ENV=staging PYTHONPATH=src:. uv run python -c "
from lia_graph.ingestion.suin.fetcher import SuinFetcher
with SuinFetcher(cache_dir='cache/suin', rps=0.5) as f:
    f._load_robots('www.suin-juriscol.gov.co')
    print('suin robots ok')
"
# if it fails: network is blocked — stop and tell the user
```

### 4. Failure protocol (when a phase's acceptance check fails)

- **Do not** silently retry a failed command with different flags.
- **Do not** edit fixtures, pin tests to broken outputs, or weaken assertions to make things green.
- **Do** capture the exact failure (stdout + stderr + any manifest JSON that was produced), leave the state tracker row as `in_progress` (not `done`, not `failed`), write a terse comment in the Proof column describing what broke, and ask the user.
- For unknown SUIN verbs: see "Common failures" at the bottom of this doc.
- For cloud write errors: never retry without user confirmation.

### 5. How to update the state tracker as you work

At the start of a phase: flip Status from `pending` → `in_progress`, set Updated to the current UTC timestamp, commit with `chore(suin): phase <N> start`.

At the end of a phase: fill the Proof column with real artifacts (paths, commit shas, row counts), flip Status to `done`, set Updated, commit with `feat(suin): phase <N> done — <short summary>`.

**Both commits go on `feat/suin-ingestion`, not `main`.** If you need to branch off for an isolated experiment, come back to `feat/suin-ingestion` before flipping the tracker.

### 6. Long-running commands

`make test-batched` and live SUIN harvests can each exceed a single-turn timeout. **Always launch them with `run_in_background`** and stream logs via Monitor. Do not use `sleep` loops to wait for them.

---

**Scope:** this document is the operational playbook for *running* SUIN-Juriscol harvests, now that the ingestion infrastructure (Phase A fetcher/parser + Phase B bridge/sink/ingest wiring) is already live on branch `feat/suin-ingestion`.

Sibling documents:

- `docs/next/ingestion_suin.md` — the infrastructure plan (**built and merged to the feature branch**); original scope was tax-only.
- `docs/guide/corpus.md` — what the existing `CORE ya Arriba` corpus already covers on disk.
- This doc — the **harvest plan**: which scopes to crawl, in what order, against which seeds, with what validation and promotion rules.

The canonical harvest fixture `artifacts/suin/smoke/` is synthetic and is treated as a **plumbing test only** — it must never be promoted to production cloud (would pollute with fake doc IDs). Any row that reaches cloud Supabase or cloud FalkorDB from this plan forward comes from a real SUIN crawl.

## Execution policy — continuous WIP, single cloud fire

Per owner direction, once this plan is approved, execution is continuous:

1. **Harvest every in-scope corpus to WIP** (local docker Supabase + local docker Falkor) back-to-back, no per-scope pauses.
2. **Run embeddings** against the merged WIP generation.
3. **Push the merged, embedded result to cloud** Supabase + cloud FalkorDB in a single promotion step.
4. Optionally flip `is_active=true` after a spot-check.

This removes per-scope cloud-confirm pauses. There is exactly **one** cloud write moment (phase 7), and it requires explicit user confirmation before firing because it is still irreversible. Everything before that is fully local and can be re-run freely.

---

## Why this plan widens past tax

The previous plan framed SUIN ingestion as tax-centric (ET → reform laws → jurisprudence). A mid-conversation clarification from the product owner made the scope wider:

> *"We do labor!"*
> *"Accountants for SMBs are often the de-facto labor advisors with respect to running payroll and all its complexities."*

And the existing corpus already validates this framing. `docs/guide/corpus.md` and the Dropbox `CORE ya Arriba` root carry **five canonical labor clusters** with 16 content files:

- `NOMINA_SEGURIDAD_SOCIAL` — PILA, liquidación de nómina, nómina electrónica, UGPP fiscalización, parafiscales exoneración art 114-1
- `PARAFISCAL_ESPECIAL` — contribuciones parafiscales especiales
- `REFORMA_LABORAL_LEY_2466` — implementation for SMB after the 2025 reform
- `REFORMA_PENSIONAL` — Ley 2381 de 2024
- `TRABAJO_TIEMPO_PARCIAL` — contratación por horas (recent labor reform derivative)

So the product already talks payroll operationally. What it lacks is the underlying legislation as **typed norm with change-history** — the exact thing SUIN provides, and the reason this plan exists.

---

## Resumable state tracker (single source of truth)

Every phase mutates this table at `in_progress` and `done`. If an agent restarts mid-flight, **this table is authoritative**, not conversation context. All timestamps UTC.

| # | Phase | Status | Proof-of-completion | Updated |
|---|---|---|---|---|
| 0 | Scope refactor in `harvest.py` + `Makefile` (add `tributario`, `laboral`, `laboral-tributario`, rename `et`→deprecated alias, keep `jurisprudencia`, keep `full`) | pending | new `_SCOPES` dict, updated Makefile targets, updated `tests/test_suin_*.py`, green `make test-batched` | — |
| 1 | Seed-URL catalog + robots check + dry-run fetch validation on `laboral-tributario` (cap `--max-documents 5`) | pending | `cache/suin/` has 5 HTML blobs; `artifacts/suin/laboral-tributario/_harvest_manifest.json` shows verb_counts and zero unknown_verb_failures; robots.txt allow confirmed | — |
| 2 | Full `laboral-tributario` harvest → merge into WIP (local docker Supabase + local Falkor) | pending | `artifacts/suin/laboral-tributario/*.jsonl`; WIP generation carries the new rows; expected ≥50 articles, ≥300 edges | — |
| 3 | Full `laboral` harvest (CST + Ley 100 + Ley 2466 + Ley 2381 + Ley 1562 + DUR 1072 + reform chain) → merge into same WIP generation | pending | `artifacts/suin/laboral/*.jsonl`; WIP generation grows; expected ≥500 articles, ≥3,000 edges cumulatively | — |
| 4 | Full `tributario` harvest (ET + reform chain + DUR 1625) → merge into same WIP generation | pending | `artifacts/suin/tributario/*.jsonl`; WIP generation grows; expected ≥700 articles, ≥6,000 edges cumulatively | — |
| 5 | `jurisprudencia` harvest (Consejo de Estado + Corte Constitucional cross-refs) → merge into same WIP generation | pending | `artifacts/suin/jurisprudencia/*.jsonl`; WIP generation grows; expected ≥500 sentencia nodes, ≥1,500 cross-ref edges | — |
| 6 | Embedding backfill against WIP for the merged generation (fills every SUIN chunk + the 2,064 pre-existing un-embedded rows) | pending | `SELECT count(*) FROM document_chunks WHERE embedding IS NULL AND sync_generation=<gen>` → 0 on WIP; eval-c-gold dry-run shows measurable lift | — |
| 7 | **Cloud fire** — merged + embedded generation pushed to cloud Supabase + cloud FalkorDB in a single run (`--supabase-target production --execute-load --strict-falkordb`, `--no-supabase-activate`) | pending (**awaits explicit user confirmation before firing — irreversible**) | cloud `corpus_generations` row for the merged generation exists with `is_active=false`; cloud `documents`/`document_chunks`/`normative_edges` counts grew by ≥ WIP delta; cloud Falkor `MATCH (n) RETURN count(n)` grew by ≥ WIP node delta | — |
| 8 | Cloud embedding backfill (parity with WIP — fills any cloud chunks still NULL) | pending | `SELECT count(*) FROM document_chunks WHERE embedding IS NULL` → 0 on cloud | — |
| 9 | Optional: cutover to `is_active=true` for the merged SUIN generation after operator review of a 10-question regression | pending (**awaits user confirmation — flips what `dev:staging` serves**) | `corpus_generations.is_active=true` on the merged generation; 10-question regression passes | — |

### Cloud baselines (filled in at the start of Phase 7 pre-flight — copy exact numbers)

| Backend | Metric | Baseline | Captured at (UTC) |
|---|---|---|---|
| Cloud Supabase (production) | `documents` count | — | — |
| Cloud Supabase (production) | `document_chunks` count | — | — |
| Cloud Supabase (production) | `normative_edges` count | — | — |
| Cloud Supabase (production) | active `generation_id` | — | — |
| Cloud FalkorDB | `MATCH (n) RETURN count(n)` | — | — |

Capture commands:

```
# Supabase
LIA_ENV=staging PYTHONPATH=src:. uv run python -c "
from lia_graph.supabase_client import create_supabase_client_for_target
c = create_supabase_client_for_target('production')
for tbl in ('documents','document_chunks','normative_edges'):
    r = c.table(tbl).select('*', count='exact').limit(0).execute()
    print(tbl, r.count)
g = c.table('corpus_generations').select('generation_id').eq('is_active', True).execute()
print('active_generation', g.data)
"

# Falkor (password from .env.staging)
source <(grep -E '^FALKORDB_URL=' .env.staging | sed 's/^/export /')
redis-cli -u \"$FALKORDB_URL\" GRAPH.QUERY LIA_REGULATORY_GRAPH \"MATCH (n) RETURN count(n)\"
```

Fill the table rows **before** running Phase 7's command. Phase 7's post-flight verification compares growth against these numbers.

### Resume protocol

1. Read this table top-down; find the first row that is not `done`.
2. Confirm the proof-of-completion column against the repo (files, manifest, commit sha).
3. If the proof matches, continue from the next pending row.
4. If the proof is partial (e.g. JSONL exists but manifest shows `unknown_verb_failures > 0`), **repair in place** — do not skip forward.
5. Never flip `done` without verifiable proof; partial work should be `in_progress`.

---

## Topic catalog — every norm we plan to harvest

This section enumerates **everything in scope** so the plan is self-contained. If a norm is not here, it is not in this plan's scope.

### A) Tributario — tax norms

**Seed documents (primary):**

- Estatuto Tributario — `Decreto 624 de 1989` (the spine of the tax corpus)
- Decreto Único Reglamentario Tributario — `Decreto 1625 de 2016` (the operational reglamentary compendium)

**Reform chain (modifies edges leak outward from ET):**

- `Ley 1607 de 2012` — reforma tributaria
- `Ley 1739 de 2014` — reforma tributaria
- `Ley 1819 de 2016` — reforma tributaria
- `Ley 1943 de 2018` — financiamiento (partially declared inexequible — the edge matters)
- `Ley 2010 de 2019` — crecimiento económico
- `Ley 2155 de 2021` — inversión social
- `Ley 2277 de 2022` — reforma tributaria
- `Ley 2381 de 2024` — partial overlap (withholding on pensions)

**Tax topics the existing corpus already covers** (SUIN anchors these):

- RENTA (113 corpus files — largest cluster; ET arts 5–364-8)
- IVA (ET arts 420–514-6)
- RST Régimen Simple (ET arts 903–916, Ley 1943 → 2010 chain)
- GMF 4×1000 (ET arts 870–881)
- ICA industria y comercio (Ley 14/1983, Ley 100/1913)
- Retención en la fuente (ET arts 365–419)
- Impuesto al patrimonio PN (ET arts 292-3 onward, Ley 2277/2022)
- Dividendos y utilidades (ET arts 30, 48, 49, 242)
- Información exógena (ET arts 631–633, Resolución DIAN anual)
- Precios de transferencia (ET arts 260-1 a 260-11)
- Pérdidas fiscales art 147 (ET art 147)
- Régimen sancionatorio (ET arts 634–680)
- Beneficiario final RUB (ET art 631-5, Resolución DIAN 000164/2021)
- Devoluciones y saldos a favor (ET arts 815–861)
- RUT (ET art 555-2, Decreto 2460/2013)
- ZOMAC / ZESE (Ley 1819/2016 art 235+, Ley 2155/2021)
- Firmeza declaraciones art 714 (ET art 714)
- Calendario tributario (Decreto anual)
- Régimen cambiario PYME (Resolución 1/2018 Banco de la República — borderline SUIN coverage)
- SAGRILAFT / PTEE (Circular Básica Jurídica 100-000010/2021 Supersociedades — borderline)
- Protección datos RNBD (Ley 1581/2012 — cross-domain)
- Facturación electrónica operativa (Resolución DIAN 000042/2020, Decreto 358/2020)

### B) Laboral — payroll + labor + social security norms

**Seed documents (primary):**

- Código Sustantivo del Trabajo — `Decreto-Ley 2663 de 1950` (adopted as permanent law by `Ley 141/1961`); this is the spine of labor
- `Ley 100 de 1993` — Sistema General de Seguridad Social (salud, pensión, riesgos laborales)
- Decreto Único Reglamentario del Sector Trabajo — `Decreto 1072 de 2015` (operational bible for aportes, PILA, SGSST, jornada)

**CST reform chain:**

- `Ley 50 de 1990` — reforma CST (cesantías system — `Ley 50` vs retroactive)
- `Ley 789 de 2002` — flexibilización laboral
- `Ley 1429 de 2010` — formalización y generación de empleo
- `Ley 1846 de 2017` — jornada
- `Ley 2101 de 2021` — reducción jornada (48 → 42 hrs gradualmente)
- `Ley 2466 de 2025` — reforma laboral (the big one — impacts every payroll)

**Social security reform chain:**

- `Ley 797 de 2003` — reforma pensional
- `Ley 1562 de 2012` — Sistema General de Riesgos Laborales (ARL)
- `Decreto 1295 de 1994` — ARL marco (still referenced)
- `Ley 1438 de 2011` — reforma salud
- `Ley 2381 de 2024` — reforma pensional estructural (pilares)

**Labor topics the existing corpus covers** (SUIN anchors these):

- Liquidación de nómina mensual (CST arts 127, 128, 134, 140, 141)
- Prestaciones sociales (CST arts 249+ cesantías, art 306 prima, art 186 vacaciones)
- Auxilios (transporte Ley 15/1959, conectividad Decreto 771/2020)
- Dotación (CST art 230)
- Jornada laboral (CST art 161 + Ley 2101/2021)
- Horas extra / recargos nocturnos / dominicales y festivos (CST arts 168, 179, 180)
- Indemnizaciones por terminación (CST art 64, Ley 789 art 28)
- Tipos de contrato (CST arts 45, 46, 47 + término fijo, obra-labor, aprendizaje Ley 789 art 30)
- Aportes salud / pensión / ARL (Ley 100 arts 161, 204; Ley 1562; tarifas variables por clase de riesgo)
- Parafiscales (SENA 2%, ICBF 3%, Cajas 4% — Ley 789 art 28, Decretos reglamentarios)
- PILA (Planilla Integrada de Liquidación de Aportes — Decreto 1990/2016, Resolución MinSalud 2388/2016)
- Nómina electrónica (Resolución DIAN 000013/2021, Decreto 358/2020) — cross-domain
- Exoneración de parafiscales (Ley 1607/2012 art 25 → ET art 114-1) — cross-domain
- UGPP fiscalización (Decreto 575/2013, circulares UGPP) — **note: UGPP conceptos are out of scope; only the enacting norms are in scope**
- Estabilidad reforzada laboral (fuero materno, fuero sindical, discapacidad — CST arts 239–241 + jurisprudencia constitucional)
- Desnaturalización del contrato de prestación de servicios (jurisprudencia Consejo de Estado + Corte Suprema)
- Contratación por horas y tiempo parcial (Decreto 2616/2013, reform derivatives)
- Reforma laboral PYME implementation (Ley 2466/2025)
- Reforma pensional implementación (Ley 2381/2024)

### C) Laboral-Tributario — the cross-domain seam

This is **the highest-value first harvest** because it lights up edges that span both tax and labor, which is exactly where accountants get confused in practice.

**Seed norms:**

- `ET art 114-1` — exoneración de parafiscales (tax code regulating a labor obligation)
- `Ley 1607 de 2012 art 25` — origin of the exoneración (introduced art 114-1)
- `Ley 1819 de 2016` arts that modify ET 114-1
- `ET arts 383 a 388` — retención en la fuente por pagos laborales (procedimientos 1 y 2, tabla, depuración)
- `ET art 385 / 386 / 387 / 388` — depuración de rentas de trabajo, UVT, deducciones
- `ET art 107 y 108` — deducibilidad de gastos de nómina + aportes parafiscales (the link between GAAP and tax)
- `Decreto 1625 de 2016` Libro I Parte 2 Título 1 — regulatory detail for art 114-1
- `Decreto 2229 de 2017` — reglamenta exoneración parafiscales (if SUIN carries it)
- `Resolución DIAN 000013/2021` — nómina electrónica (cross-domain operational)

**Expected edge yield (rough):** ~50 articles, ~300 edges across `modifica`, `adiciona`, `reglamenta`, `references`, `exception_for` (parafiscales exoneración creates one of the clearest `exception_for` relationships in the corpus).

### D) Jurisprudencia — sentencia coverage

**Courts to crawl** (via `sitemapconsejoestado.xml` + cross-references from the legislative sitemaps):

- Consejo de Estado — Sala Tercera (tributario + contencioso administrativo)
- Consejo de Estado — Sala Segunda (laboral + electoral)
- Corte Suprema de Justicia — Sala Laboral (indirectly, via cross-reference mentions)
- Corte Constitucional — C-XXX-AÑO sentencias cited from legislative documents' `NotasDestinoJurisp` blocks

**Expected yield:**

- ~150 tax-related sentencias (C-XXX + Consejo de Estado sala 3)
- ~300 labor-related sentencias (C-XXX + Consejo de Estado sala 2 + Corte Suprema laboral by cross-ref)
- Reciprocal `NotasOrigen` on every sentencia so edges point both ways

### E) Full scope

`full` = `tributario` + `laboral` + `laboral-tributario` + `jurisprudencia` de-duplicated by `doc_id`. Last scope executed; only runs once all narrower scopes pass validation.

---

## Phase 0 — Scope refactor (code change; no SUIN network calls)

### Goal

Replace the current `{et, tax-laws, jurisprudence, full}` scopes with the topic-aware set defined above, while keeping the legacy `et` name working as an alias (so nothing in-flight breaks).

### Files to modify

- `src/lia_graph/ingestion/suin/harvest.py`
  - Replace `_SCOPES` dict with: `tributario`, `laboral`, `laboral_tributario`, `jurisprudencia`, `full`, plus `et` → alias of `tributario` (deprecated marker in help text).
  - Each scope entry gains: a list of `SitemapEntry`, an optional list of **seed URLs** that must be reached regardless of sitemap content (e.g. Decreto 624/1989 direct URL, CST direct URL), and a **topic_anchors** dict giving human-readable names per primary norm.
  - `--scope` argparse choices update accordingly.

- `src/lia_graph/ingestion/suin/fetcher.py`
  - Add a `SEED_URLS` module-level constant documenting the spine documents per scope (each with a `purpose` comment).
  - `SuinFetcher` gains `iter_seeds(scope: str) -> Iterator[str]` that yields the scope's seed URLs up front, then defers to the existing `iter_sitemap` walk.

- `Makefile`
  - Add `phase2-suin-harvest-tributario`, `phase2-suin-harvest-laboral`, `phase2-suin-harvest-laboral-tributario`, `phase2-suin-harvest-jurisprudencia`, `phase2-suin-harvest-full`.
  - Keep `phase2-suin-harvest-et` as an alias of `tributario` with a `@echo "[deprecated: use phase2-suin-harvest-tributario]"` preamble.

- `docs/next/ingestion_suin.md`
  - Add a one-paragraph pointer at the top linking here: "**Operational harvest plan has moved to `suin_harvestv1.md`**; this file owns the infrastructure record only."

### Files to create

- `scripts/verify_suin_merge.py` — shared verification script used by phases 2–5 (against WIP) and phase 7 (against production). Takes `--target` and `--generation`; prints pass/fail per contract defined in "Shared WIP merge contract" above.
- `scripts/supabase_flip_active_generation.py` — thin CLI wrapper over the sink's two-step activation flow. Requires `--confirm` to prevent accidental flips. Used in Phase 9 only.
- `scripts/fire_suin_cloud.sh` — orchestrates the four sequential `--include-suin <scope>` cloud ingests (one per scope, same generation_id) and aborts on first failure. Used in Phase 7 only. Requires an explicit `--confirm` guard before firing.
- **Decision recorded:** `--include-suin` stays single-valued. Sequential merges under the same generation_id is simpler, matches current CLI, and is naturally idempotent.

### Hard deliverables Phase 0 must resolve before any harvest

Phase 0 also performs these discovery tasks. Each has a "must produce X" contract — if the repo already has X, the task is a no-op; if not, Phase 0 **builds** X before any harvest runs.

1. **Confirm or build `scripts/embedding_ops.py`.**
   - Required contract: `--target {wip,production} --generation <id> [--batch-size N] [--json]` — backfills the `embedding` column on `document_chunks` rows belonging to the generation.
   - Check first: `ls scripts/embedding_ops.py 2>/dev/null || echo MISSING`.
   - If missing: build a minimal version that batches over rows with NULL embedding and the matching `sync_generation`, calls the configured embedding provider (check `CLAUDE.md` / `.env.staging` for the provider key), upserts the resulting vector back. Log a manifest at `artifacts/suin/_embedding_<target>_<ts>.json`.
   - Add `tests/test_embedding_ops.py` that mocks the provider and asserts per-batch upsert + final NULL count drop.
2. **Confirm or build `tests/fixtures/chat_regressions/`.**
   - Phase 9 pre-flight needs a 10-question regression suite covering: 3 tax questions hitting ET articles known to be modified post-2012, 3 labor questions hitting CST articles changed by Ley 2466/2025, 2 cross-domain questions on parafiscales exoneración (ET art 114-1), and 2 questions about derogated articles (to exercise vigencia flagging).
   - Check first: `ls tests/fixtures/chat_regressions/ 2>/dev/null || echo MISSING`.
   - If missing: create the 10 fixtures with expected-answer skeleton. The fixtures are product-content and should be reviewed by the user before Phase 9 runs — flag this in the Phase 9 row so the user knows to review.
3. **Fix the `corpus_generations` cumulative-count subtlety for Phase 7.**
   - When Phase 7 fires four sequential `--include-suin <scope>` calls against the same `--supabase-generation-id gen_suin_prod_v1`, each call invokes `SupabaseCorpusSink.write_generation()` with *its own* `documents` and `chunks` counts, overwriting the row's metadata with the last scope's numbers.
   - Fix: add a `--supabase-skip-generation-row-after-first` flag to `ingest.py` (or equivalent), so calls 2–4 skip `write_generation()` and only upsert into `documents` / `document_chunks` / `normative_edges`. The first call still writes the generation row with best-effort counts; the final verification script reports true cumulative counts from the tables themselves.
   - Alternative (simpler): have `fire_suin_cloud.sh` do a final pass that updates `corpus_generations` with the true cumulative `SELECT count(*)` values after all four scope merges complete.
   - Pick one, document the choice in this section, build the chosen path in Phase 0.
4. **Verify Ley 2466/2025 and Ley 2381/2024 are reachable on SUIN** (Phase 1 dry run covers this — but Phase 0 should pre-flight the doc_ids so Phase 1 knows what to expect). If SUIN has not yet published them, Phase 3's seed list must add a "known-missing" flag so the harvest does not fail loud when they're not found. Do not silently skip — the flag must surface in the manifest.

### Failure-to-safe-state rule for Phase 0

If any hard deliverable cannot be built autonomously (e.g. the embedding provider config is missing, the regression fixtures need product judgment), **stop Phase 0 with the state tracker row still at `in_progress`**, document exactly what's blocking, and ask the user. Do not proceed to Phase 1 with Phase 0 partially done.

### Tests

Added / updated in `tests/test_suin_fetcher.py`:

- `test_scope_catalog_has_every_expected_scope` — asserts each of `{tributario, laboral, laboral_tributario, jurisprudencia, full, et}` is in `_SCOPES` and `et` behaves as an alias of `tributario`.
- `test_scope_seed_urls_are_well_formed` — every seed URL is absolute, `https://`, and on the `suin-juriscol.gov.co` host.
- `test_full_scope_is_union_of_narrower_scopes` — `_SCOPES["full"]` contains every sitemap present in the other narrower scopes (prevents drift).
- `test_fetcher_emits_seeds_before_sitemap_walk` — mocks transport; asserts seeds come before sitemap URLs in `iter_seeds` output.

Added / updated in `tests/test_suin_parser.py`:

- No changes (parser is scope-independent).

New: `tests/test_verify_suin_merge.py`:

- Mocks a Supabase client + a Falkor response and asserts `verify_suin_merge.py` returns pass/fail correctly on each branch (missing docs, missing relations, missing Falkor delta, unknown-verb failure).

New: `tests/test_flip_active_generation.py`:

- Asserts the flip script refuses to run without `--confirm`, and when confirmed calls the sink's two-step deactivate-then-activate flow exactly once each.

### Success criteria

- `uv run python -m lia_graph.ingestion.suin.harvest --help` lists the new scopes.
- `make test-batched` green.
- No network calls made in this phase.

### Commit convention

One commit: `feat(suin): scope refactor — tributario/laboral/laboral-tributario/jurisprudencia/full`.

### State tracker update on completion

Row 0 → `done`, with the commit sha + test summary in the Proof column.

---

## Phase 1 — Dry-run crawl on `laboral-tributario` (5-document cap)

### Goal

First real contact with `suin-juriscol.gov.co`. Exercise the fetcher against live robots.txt, live rate limit, live HTML shapes. Fail loud on anything surprising (unknown verbs, malformed DOM) *before* committing to a full scope crawl.

### Files to modify / create

None — uses the CLI built in Phase 0.

### Command (exact)

```
PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest \
  --scope laboral-tributario \
  --out artifacts/suin/laboral-tributario \
  --cache-dir cache/suin \
  --max-documents 5 \
  --rps 0.5 \
  --json
```

`--rps 0.5` is **intentionally slow** for a first live contact — doubles the rate limit budget so SUIN never sees a burst from us on day one.

### Validation (manual, but checklist)

- [ ] `cache/suin/` has at least 5 `.html` blobs and one `_manifest.jsonl` with 5+ rows.
- [ ] `artifacts/suin/laboral-tributario/_harvest_manifest.json` has `unknown_verb_failures: []` (zero).
- [ ] `articles.jsonl` row count ≥ 5 (each doc produces at least one article).
- [ ] `edges.jsonl` row count > 0 (should be dozens just from the first 5 docs — ET art 114-1 alone has many).
- [ ] Every `verb` value is in the canonical set defined in `parser.py`.
- [ ] Spot-check: open one HTML blob from cache, verify the parser found the `NotasDestino*` blocks.

### Failure modes to expect + recipe

- **Robots disallow on the documents we target.** The current robots.txt (2026-04-19 check) allows crawling. If it doesn't: stop, escalate, do not use an alternative user-agent.
- **Unknown verb raised.** Extend `_VERB_ALIASES` in `parser.py` with the new raw token, add a fixture to `tests/test_suin_parser.py`, re-run. Never silent-fallback.
- **Rate-limit 429.** `--rps 0.5` should avoid this. If it happens, drop to `--rps 0.2` and document.
- **Malformed HTML (DOM schema drift).** The parser hits a `find_all` that returns nothing surprising — capture the offending doc's HTML in `tests/fixtures/suin/`, add a regression test, patch the parser.

### Tests added

- `tests/fixtures/suin/live_snapshot_<yyyymmdd>/` — saved HTML of the 5 docs we crawled (git-tracked, small and auditable).
- `tests/test_suin_live_snapshot.py` — parameterized test that parses each saved HTML and asserts the manifest's verb_counts matches a pinned expectation (guard against silent parser drift).

### State tracker update

Row 1 → `done` with manifest path and verb_counts dictionary in the Proof column.

---

## Shared WIP merge contract (used by phases 2, 3, 4, 5)

All four harvest phases write into **the same WIP generation** — one `generation_id` rolling forward as each scope merges in. This mirrors how a normal `phase2-graph-artifacts-supabase` re-run works: each call upserts its documents/chunks/edges into Supabase keyed on the existing generation_id. No scope is lost; each widens the same merged corpus.

**Rolling WIP generation_id convention:** `gen_suin_wip_<yyyymmdd>` (chosen once before Phase 2 starts, reused for phases 2–5).

**WIP merge command template** (same command across all four harvest phases, with `<scope>` swapped):

```
LIA_ENV=staging \
  FALKORDB_URL=redis://127.0.0.1:6389 \
  FALKORDB_GRAPH=LIA_REGULATORY_GRAPH \
  PYTHONPATH=src:. uv run python -m lia_graph.ingest \
    --corpus-dir knowledge_base --artifacts-dir artifacts \
    --supabase-sink --supabase-target wip \
    --execute-load --allow-unblessed-load --strict-falkordb \
    --include-suin <scope> \
    --supabase-generation-id <rolling_wip_gen_id> \
    --no-supabase-activate \
    --json | tee artifacts/suin/<scope>/_ingest_wip_<ts>.log
```

**Shared verification script** `scripts/verify_suin_merge.py` (**file to create in Phase 0**) takes `--target {wip|production} --generation <id>` and prints pass/fail on:

- every SUIN doc_id in the scope's manifest is present in `documents` for that generation
- chunk count ≥ articles count in the manifest
- at least one edge landed per `{modifies, complements, references, exception_for, derogates, struck_down_by, revokes}` that the manifest declared
- Falkor node-count delta since the previous scope ≥ (documents + articles added this scope)
- every `unknown_verb_failure` the manifest flagged is absent (manifests must have zero failures before the phase runs)

Each harvest phase runs this script against WIP after its merge; any fail blocks the next phase.

---

## Phase 2 — `laboral-tributario` harvest → WIP merge

### Goal

Produce the complete `laboral-tributario` JSONL bundle, merge into the rolling WIP generation.

### Harvest command

```
PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest \
  --scope laboral-tributario \
  --out artifacts/suin/laboral-tributario \
  --cache-dir cache/suin \
  --rps 1.0 \
  --json | tee artifacts/suin/laboral-tributario/_run_<ts>.log
```

Warm cache from Phase 1 keeps this well under 10 minutes.

### WIP merge

Run the shared WIP merge template with `<scope>=laboral-tributario`.

### Expected volumes (±30%)

- documents: 20–40
- articles: 50–150
- edges: 300–800

### Tests

- `tests/test_suin_harvest_manifest.py::test_laboral_tributario_manifest_expected_shape` — pins doc count range, verb_counts keys, and required source+target doc_ids.

### Success

Verification script passes against WIP.

### State tracker update

Row 2 → `done`.

---

## Phase 3 — `laboral` harvest → WIP merge

### Goal

Crawl every primary labor norm: CST + Ley 100 + Ley 50 + Ley 789 + Ley 1846 + Ley 2101 + Ley 2466 + Ley 797 + Ley 1562 + Ley 2381 + Decreto 1295 + DUR 1072/2015 + cross-references.

### Harvest command

```
PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest \
  --scope laboral \
  --out artifacts/suin/laboral \
  --cache-dir cache/suin \
  --rps 1.0 \
  --json | tee artifacts/suin/laboral/_run_<ts>.log
```

### WIP merge

Run the shared WIP merge template with `<scope>=laboral` (same rolling `generation_id`). The `--include-suin laboral` merge *adds to* the already-merged `laboral-tributario` rows under the same generation. Expected: the WIP generation grows; nothing gets replaced.

### Expected volumes

- documents: ~60 primary + ~300 cross-referenced
- articles: ~500
- edges: ~3,000
- Time: 25–40 min cold, <5 min warm

### Tests

- `tests/test_suin_harvest_manifest.py::test_laboral_manifest_expected_shape` — pinned doc_ids (CST, Ley 100, Ley 2466, Ley 2381, DUR 1072, etc.).

### State tracker update

Row 3 → `done`.

---

## Phase 4 — `tributario` harvest → WIP merge

### Goal

Crawl ET (Decreto 624/1989) + reform chain (Ley 1607, 1739, 1819, 1943, 2010, 2155, 2277) + DUR 1625/2016 + cross-references.

### Harvest command

```
PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest \
  --scope tributario \
  --out artifacts/suin/tributario \
  --cache-dir cache/suin \
  --rps 1.0 \
  --json | tee artifacts/suin/tributario/_run_<ts>.log
```

### WIP merge

Run the shared WIP merge template with `<scope>=tributario`.

### Expected volumes

- documents: ~40 primary + ~300 reglamentary cross-refs
- articles: ~700
- edges: ~6,000
- Time: 30–50 min cold, <5 min warm

### Tests

- `tests/test_suin_harvest_manifest.py::test_tributario_manifest_expected_shape` — pinned doc_ids (ET, DUR 1625, Ley 2277, etc.).

### State tracker update

Row 4 → `done`.

---

## Phase 5 — `jurisprudencia` harvest → WIP merge

### Goal

Crawl Consejo de Estado + Corte Constitucional cross-references (via `NotasDestinoJurisp` / `NotasOrigen*` blocks in the tributario and laboral documents already harvested). The SUIN jurisprudence crawl naturally narrows to the sentencias that cite norms in the prior scopes — no extra filter needed.

### Harvest command

```
PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest \
  --scope jurisprudencia \
  --out artifacts/suin/jurisprudencia \
  --cache-dir cache/suin \
  --rps 0.7 \
  --json | tee artifacts/suin/jurisprudencia/_run_<ts>.log
```

`--rps 0.7` is slightly slower because the sitemap is bigger.

### WIP merge

Run the shared WIP merge template with `<scope>=jurisprudencia`.

### Expected volumes

- documents: ~500 sentencias
- articles: ~500 (one per sentencia)
- edges: ~1,500 (most sentencias cite 2–5 articles)
- Time: 40–80 min cold, <5 min warm

### Tests

- `tests/test_suin_harvest_manifest.py::test_jurisprudencia_manifest_expected_shape` — pinned ranges and at least one sentencia source doc_id.

### State tracker update

Row 5 → `done`.

---

## Phase 6 — Embedding backfill against WIP

### Goal

Populate the `embedding` column for every SUIN chunk written in phases 2–5 **plus** the 2,064 pre-existing un-embedded rows. Embeddings stay in WIP; Phase 7 copies them to cloud via a fresh backfill there. This keeps the embedding cost path rehearsable locally before the cloud spend.

### Command

(exact script path confirmed in Phase 0 — `scripts/embedding_ops.py` is the expected location based on the codebase convention; alternative paths captured here if discovered during Phase 0)

```
LIA_ENV=staging \
  PYTHONPATH=src:. uv run python scripts/embedding_ops.py \
  --target wip \
  --generation <rolling_wip_gen_id> \
  --batch-size 100 \
  --json | tee artifacts/suin/_embedding_wip_<ts>.log
```

### Validation

- `SELECT count(*) FROM document_chunks WHERE embedding IS NULL AND sync_generation=<gen>` → 0
- `make eval-c-gold` dry-run (or a SUIN-specific eval subset) shows NDCG@10 lift on questions hitting SUIN-sourced articles

### State tracker update

Row 6 → `done`.

---

## Phase 7 — **CLOUD FIRE** — merged + embedded WIP generation → cloud Supabase + cloud Falkor

### Blast radius and safeguards

- **Irreversible.** Writes new rows to production cloud Supabase + production cloud FalkorDB.
- **Requires explicit user confirmation** immediately before firing. No autonomous fire.
- **`--no-supabase-activate`** keeps the current active generation (`gen_20260418035334` at handoff) serving. Nothing user-visible changes until Phase 9.
- **Idempotent rerun:** the same generation_id can be re-fired safely (upserts on natural keys). If the first fire is interrupted, re-run the same command.

### Pre-flight checklist

- [ ] All four harvest phases (2, 3, 4, 5) are `done` in the state tracker.
- [ ] Phase 6 embedding backfill is `done` on WIP.
- [ ] WIP verification against the rolling generation_id returns pass.
- [ ] Cloud baselines captured: `documents`, `document_chunks`, `normative_edges` counts; Falkor `MATCH (n) RETURN count(n)`. Written into the state tracker as a comment row before the fire.
- [ ] `cache/suin/` warm — the cloud run itself shouldn't hit SUIN at all; it reads from `artifacts/suin/*/` which were materialized in phases 2–5.
- [ ] User has said "go" in writing this session.

### Command

```
LIA_ENV=staging \
  PYTHONPATH=src:. uv run python -m lia_graph.ingest \
    --corpus-dir knowledge_base --artifacts-dir artifacts \
    --supabase-sink --supabase-target production \
    --execute-load --allow-unblessed-load --strict-falkordb \
    --include-suin laboral-tributario \
    --include-suin laboral \
    --include-suin tributario \
    --include-suin jurisprudencia \
    --supabase-generation-id gen_suin_prod_v1 \
    --no-supabase-activate \
    --json | tee artifacts/suin/_ingest_cloud_<ts>.log
```

**Note:** `--include-suin` accepts exactly one scope today. Per the Phase 0 decision, we run the four scopes **sequentially against the same cloud generation_id** — four commands, each with one `--include-suin <scope>` and the same `--supabase-generation-id gen_suin_prod_v1`. Sink upserts make this safe; the merge accumulates. The cloud-fire step is therefore a small script `scripts/fire_suin_cloud.sh` (**file to create in Phase 0**) that runs the four `uv run python -m lia_graph.ingest` calls in order and aborts on the first failure.

### Post-flight validation

```
LIA_ENV=staging PYTHONPATH=src:. uv run python scripts/verify_suin_merge.py \
  --target production --generation gen_suin_prod_v1
```

Must pass. If it fails, **do not retry blindly** — inspect the failure, and if rollback is needed, capture the exact SQL (`DELETE FROM corpus_generations WHERE generation_id='gen_suin_prod_v1'`) and wait for user approval before firing.

### State tracker update

Row 7 → `done` with cloud documents/chunks/edges counts and cloud Falkor node delta in the Proof column.

---

## Phase 8 — Cloud embedding backfill

### Goal

Parity with WIP — fill the `embedding` column for every SUIN chunk now in cloud plus the 2,064 cloud chunks that were NULL at handoff.

### Command

```
LIA_ENV=staging \
  PYTHONPATH=src:. uv run python scripts/embedding_ops.py \
  --target production \
  --generation gen_suin_prod_v1 \
  --batch-size 100 \
  --json | tee artifacts/suin/_embedding_cloud_<ts>.log
```

### Validation

- `SELECT count(*) FROM document_chunks WHERE embedding IS NULL` → 0 on cloud
- Cloud `make eval-c-gold` shows lift vs. baseline

### State tracker update

Row 8 → `done`.

---

## Phase 9 — Optional: activate the merged SUIN generation

**Blast radius: this is what `dev:staging` + production serving reads from.** Flips `is_active=true`, so stale content disappears and SUIN-enriched content appears in answers.

### Pre-flight

- Run a 10-question regression (`tests/fixtures/chat_regressions/`) against a retriever pointed at `gen_suin_prod_v1`. Zero regressions; derogated-article flagging should be measurably better.
- Capture `corpus_generations` snapshot so we can re-activate the prior generation if anything is off.

### Command

```
LIA_ENV=staging \
  PYTHONPATH=src:. uv run python scripts/supabase_flip_active_generation.py \
    --target production \
    --generation gen_suin_prod_v1
```

(**`scripts/supabase_flip_active_generation.py` — file to create in Phase 0.** Tiny wrapper around `SupabaseCorpusSink._activate_generation` with a `--confirm` flag to avoid accidental flips.)

### Rollback

Flip back to the prior generation via the same script. The partial unique index ensures at-most-one active row, so the rollback is safe.

### State tracker update

Row 9 → `done` only after operator confirms answers look right on a spot-check.

---

## Non-SUIN sources explicitly out of scope

These are real gaps but belong to separate plans, not this one:

- **DIAN normograma** (`normograma.dian.gov.co`) — DIAN conceptos, oficios, circulares. Already acknowledged as out of scope in `ingestion_suin.md`.
- **UGPP doctrine** (`ugpp.gov.co/normatividad`) — the labor analog of DIAN conceptos. New gap identified in this plan; should get its own doc (`docs/next/ingestion_ugpp.md`).
- **MinTrabajo conceptos** (`mintrabajo.gov.co/conceptos-juridicos`) — labor administrative doctrine.
- **Supersolidaria / Superfinanciera / Supersociedades circulares** — industry-specific; most relevant for SAGRILAFT/PTEE cluster.
- **CTCP pronouncements** (`ctcp.gov.co`) — accounting standards, NIIF interpretation. Not Colombian state legal material.
- **Municipal norms** (ICA territorial, registros mercantiles) — SUIN is national only.
- **Draft bills** (`proyectos de ley`) — SUIN carries enacted norms only.

Each of these should get a parallel ingestion plan with the same phased + state-aware shape as this one.

---

## Risks and how we address them

- **SUIN HTML schema drift mid-harvest.** The `test_suin_live_snapshot.py` regression (Phase 1) pins the parser against real HTML. Any DOM change triggers a loud test failure, not a silent edge drop.
- **Silent normative-drift inside SUIN.** Every scope's manifest records per-verb counts. A sharp count drop between two runs is a regression signal. Phase 2+ add a lint step `make phase2-suin-verify` comparing the latest manifest against the prior.
- **Editorial lag at SUIN.** SUIN's consolidated ET can trail a recent reform by weeks. The merge is idempotent per generation_id, so re-running a newer reform on top is safe. For truly fresh reforms (< 2 weeks old), prefer the raw enactment text already in `CORE ya Arriba` and treat SUIN as the historical-truth backfill.
- **Cloud writes are irreversible until activation.** Every phase 4 / 6 / 8 / 10 writes with `is_active=false` so serving stays on the prior generation. Phase 12 is the only step that flips what users see.
- **Rate-limit misconfiguration.** Every harvest phase sets `--rps` conservatively (0.5 → 1.0 progression). If we get 429'd, we drop by half and re-run — never retry hot.
- **Cross-domain doc_id collisions.** All SUIN doc_ids are prefixed `suin_*` by `_sanitize_doc_id` in `supabase_sink.py`. No collision with the existing 1,292 corpus docs is possible.

---

## Handoff checklist (before starting any phase)

- Read this entire doc + the resume protocol.
- Confirm `cache/suin/` is git-ignored (done in Phase A of `ingestion_suin.md`).
- Confirm the feature branch is `feat/suin-ingestion` and infrastructure is at commit `7b11b86` or later.
- For every cloud-touching phase: capture the baseline before firing; wait for user confirmation; never use `--no-verify` or bypass the reconnaissance gate without `--allow-unblessed-load`.
- Every commit on this branch uses the project's convention: `feat(suin): <phase># — <short>` or `chore(suin): ...` for non-functional edits.

---

## Common failures and their recipes

When a phase's acceptance check fails, match the symptom against this table **before** improvising. Every recipe here leaves the system in a recoverable state.

### "UnknownVerb: <raw token>" during harvest

- The SUIN DOM emitted a verb the canonical vocabulary doesn't know.
- Recipe:
  1. Capture the raw token, the doc URL, and the surrounding DOM snippet into `tests/fixtures/suin/unknown_verb_<sha1(url)>.html`.
  2. Add the new raw token to `_VERB_ALIASES` in `src/lia_graph/ingestion/suin/parser.py` mapping it to the correct canonical verb. If no canonical verb fits, add a new canonical verb *and* its mapping in `bridge.py` to an `EdgeKind`.
  3. Add a test case in `tests/test_suin_parser.py` that parses the new fixture and asserts the mapping.
  4. Re-run `make test-batched` green.
  5. Re-run the failed harvest command — cache makes this cheap.
- Do not pass `--no-strict-verbs` in production runs to sidestep this. The loud-failure is the point.

### "sitemapleyes.xml: malformed XML" or required sitemap unreachable

- SUIN is having an outage or returned HTML instead of XML.
- Recipe: wait 15 minutes, re-run. If still failing, stop and tell the user. Do not swap to an alternative sitemap — the `required=True` flag is deliberate.

### Supabase 429 / rate-limit during sink write

- Batch size too aggressive, or cloud is throttling this service role.
- Recipe: halve `_BATCH_SIZE` in `supabase_sink.py`, add a `time.sleep(0.2)` between batches, re-run. File a follow-up to make batch size configurable via env.

### Falkor "graph not found" or connection refused

- Local docker container died, or `FALKORDB_URL` env var is wrong.
- Recipe: re-check Precondition 3.c; if the container is restarted, Falkor state persists via docker volume — your prior data is still there. If not, stop and ask; do not re-init the graph.

### `normative_edges_relation_check` constraint violation

- Some `EdgeKind` mapped to a DB relation not in `_ALLOWED_RELATIONS`.
- Recipe: check `_RELATION_MAP` in `supabase_sink.py` vs. the baseline migration's CHECK constraint. If `_RELATION_MAP` names a relation not in the CHECK list, either (a) fix the map or (b) add a migration to extend the CHECK — but (b) requires user approval because it's a schema change.

### `normative_edges_idempotency` unique-violation on re-run

- You fired the same generation_id twice and a dedup key collision surfaced.
- Recipe: this is *expected* on re-run and should be a no-op upsert. If Postgres raises instead of upserting, check that the unique index `normative_edges_idempotency` still exists (`\\d+ normative_edges`). If it's missing, re-apply migration `20260418000000_normative_edges_unique.sql`.

### `hybrid_search` returns nothing for a known-present chunk

- FTS column not populated, or the query is filtering `vigencia` implicitly.
- Recipe: `SELECT search_vector, vigencia FROM document_chunks WHERE chunk_id='<id>'`. If `search_vector` is NULL, run a reindex; if `vigencia='derogada'`, the default filter is correctly excluding the chunk (pass `filter_effective_date_max` to the RPC to include historical).

### Cloud write unexpectedly slow / interrupted mid-batch

- Network wobble or long-running batch.
- Recipe: the sink upserts on natural keys so a mid-batch interrupt is safe. Re-run the same command; rows already written are upserted no-op, missing rows are filled. **Never truncate + re-run cold** — the idempotency keys guarantee re-runs are cheap.

### Agent approaches turn limit mid-harvest

- A `laboral` or `tributario` cold-cache crawl can push 30+ minutes.
- Recipe: relaunch the bash command with `run_in_background: true`, monitor via Monitor tool, and do other work in the meantime. Do not split a single harvest across two agent turns without background launch.

---

## Stop condition

You are done when **every row in the state tracker is `done`** AND the user has confirmed Phase 9's activation flip (or explicitly declined it). Do not start new work after that; report completion and wait.
