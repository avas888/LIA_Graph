# SUIN Harvest v2 — Implementation Plan

---

## ⚠️ COLD-START PROTOCOL — READ THIS FIRST

**If you are a fresh agent just told to "implement `docs/next/suin_harvestv2.md`", do these checks in order before any other action. Each check has a copy-paste command and an explicit stop-condition. Skipping this block is how a cold agent trips.**

### 0. v1 must be live in production before v2 runs

v2 *extends* the v1 corpus. It does **not** repeat v1's spine-doc crawl. The v2 plan assumes `gen_suin_prod_v1` is `is_active=true` on cloud Supabase, carrying the 9 spine docs (ET, CST original + consolidado, Ley 100/1993, DUR 1072/2015, DUR 1625/2016, Ley 2466/2025, Ley 2381/2024, Ley 2277/2022) plus the 1,054 stub docs the two-pass merge created.

```
set -a; source .env.local; source .env.staging; set +a
LIA_ENV=staging PYTHONPATH=src:. uv run python -c "
from lia_graph.supabase_client import create_supabase_client_for_target
c = create_supabase_client_for_target('production')
g = c.table('corpus_generations').select('generation_id,is_active').eq('is_active', True).execute()
print('active:', g.data)
"
# expected: active: [{'generation_id': 'gen_suin_prod_v1', 'is_active': True}]
```

**Stop if v1 is not active.** v2 writes stubs that resolve edges v1 created; running v2 against a pre-v1 corpus produces orphaned nodes.

### 1. You cannot fire v2's production push without explicit user confirmation

Phase 7 of v2 is a single production push that writes to cloud Supabase + cloud FalkorDB, runs the cloud embedding backfill against `gen_suin_prod_v2`, and flips `is_active=true` from `gen_suin_prod_v1` to `gen_suin_prod_v2`. That sequence is irreversible without a rollback flip.

If the user has not said "go" or "fire the v2 production push" in the current conversation, **stop at the end of Phase 6 and ask.** Do not infer approval from context, a TODO, or previous sessions.

### 2. You must be on a fresh v2 branch off `feat/suin-ingestion`

```
git rev-parse --abbrev-ref HEAD
# expected: feat/suin-ingestion-v2  (create from feat/suin-ingestion if missing)
git log --oneline -1 feat/suin-ingestion -- docs/next/suin_harvestv1.md
# expected: a commit exists; v1 state tracker should read `done` on row 7
```

### 3. Verify the state tracker below — that's your source of truth

Scroll to the "Resumable state tracker" table. Find the **first row whose Status is not `done`**. That is your current phase.

### 4. Preconditions the plan assumes are true

```
# a) TLS shim alive (truststore shipped in v1, must still be on pyproject.toml)
PYTHONPATH=src:. uv run python -c "import truststore; print('truststore ok')"

# b) SUIN reachable (stem-based verb matcher + class-based container matcher already landed in v1)
PYTHONPATH=src:. uv run python -c "
from lia_graph.ingestion.suin.fetcher import SuinFetcher
with SuinFetcher(cache_dir='cache/suin', rps=0.5) as f:
    f._load_robots('www.suin-juriscol.gov.co')
    print('suin robots ok')
"

# c) Local docker Supabase + local Falkor up (same as v1)
supabase status 2>&1 | head -3
redis-cli -h 127.0.0.1 -p 6389 PING

# d) Cloud credentials
test -f .env.staging && grep -cE '^SUPABASE_(URL|WIP_URL|SERVICE_ROLE_KEY|WIP_SERVICE_ROLE_KEY)=' .env.staging
# expected: 4

# e) GEMINI_API_KEY resolves (loaded from .env.local via the dev launcher convention)
set -a; source .env.local; source .env.staging; set +a
LIA_ENV=staging GEMINI_API_KEY="$GEMINI_API_KEY" PYTHONPATH=src:. uv run python -c "
from lia_graph.embeddings import is_available
print('embeddings available:', is_available())
"
```

### 5. Failure protocol (unchanged from v1)

- **Do not** silently retry a failed command with different flags.
- **Do not** edit fixtures, pin tests to broken outputs, or weaken assertions to make things green.
- **Do** capture the exact failure, leave the state tracker row as `in_progress`, write a terse comment in the Proof column, and ask the user.
- For unknown SUIN verbs: the v1 stem-based fallback in `normalize_verb` should cover 99%; if a new stem is missing, add it with a test fixture the same way v1 did.
- For parser DOM drift: v1 already supports both the pre-2025 `<ul id="NotasDestino*">` and post-2025 `<ul class="resumenvigencias">` containers. New patterns require a fixture + `_container_kind_from_class` extension.

### 6. How to update the state tracker (same as v1)

At the start of a phase: flip `pending` → `in_progress`, set Updated to UTC, commit with `chore(suin-v2): phase <N> start`.

At the end of a phase: fill the Proof column with real artifacts, flip to `done`, commit with `feat(suin-v2): phase <N> done — <summary>`.

---

**Scope:** this document is the operational playbook for *extending* SUIN coverage past the 9 spine docs v1 landed. It is the next accountant-value frontier: sentencia full text, standalone reglamentary decretos, and accountant-profession norms the spines don't consolidate.

Sibling documents:

- `docs/next/suin_harvestv1.md` — v1 execution record; state tracker all `done`. Do not re-run v1.
- `docs/next/ingestion_dian.md` — DIAN normograma plan (**not on SUIN**; separate scraper).
- `docs/next/ingestion_ugpp.md` — UGPP doctrine plan.
- `docs/next/ingestion_mintrabajo.md` — MinTrabajo conceptos plan.
- `docs/guide/corpus.md` — existing corpus coverage.
- This doc — the **v2 operational plan**: which SUIN content to widen into next and in what order.

## Execution policy — same continuous-WIP shape as v1

1. **Per-tier harvests flow to the same WIP generation** (`gen_suin_wip_v2_<yyyymmdd>`). Each tier merges additively under that generation via `--include-suin <scope>` — the two-pass stub resolver from v1 keeps edge integrity as we grow.
2. **Run embeddings** against the merged WIP generation (backfills any chunks whose text changed from stub→primary).
3. **Production push** — one confirmed `fire_suin_cloud.sh` run against `gen_suin_prod_v2`, write + cumulative-count repair + verify + embed + null-gate + activate + regression + auto-rollback.

Exactly **one** user confirmation gate: before Phase 7. Phases 0–6 can re-run freely; post-Phase-7 is irreversible without a rollback flip.

---

## Why v2 widens past the 9 spines

v1 was forward-from-today: land the consolidated codes (ET, CST, Ley 100, DURs) plus the freshest reforms that hadn't been folded into those codes yet (Ley 2466/2025, 2381/2024, 2277/2022). That covered "what does the law say right now."

But a senior accountant doesn't only quote the code — they cite **what the courts have ruled it means**, and they know **which operational decreto implements the code article**. Today on production:

- The 1,092 `declara_exequible` edges, 298 `declara_inexequible` edges, 614 `inhibida` edges, 279 `estarse_a_lo_resuelto` edges, 170 `struck_down_by` edges — **2,453 sentencia references total** — point at `suin_stub` nodes with **no body text**. Lia can cite the sentencia name but cannot quote its holding. That is a "senior accountant can't trust" moment in every constitutional question.
- The 569 `derogates` and 390 `complements` edges point at decreto stubs where the reglamentary detail lives. Operational questions ("what does PILA actually require by field?") bottom out in these decretos, not in the spine docs. v1 left them as stubs.

v2 fills these two gaps in that order:

1. **Tier A — Jurisprudencia full text** (`sitemapconsejoestado.xml` + Corte Constitucional `sitemapleyes.xml`-listed sentencias).
2. **Tier B — Standalone reglamentary decretos** that never folded into DUR 1072/1625.
3. **Tier C — Accountant-profession base norms** that govern the contador's own work (Ley 43/1990, Ley 1314/2009, Decreto 2420/2015).
4. **Tier D — Late reforms** (Ley 2101/2021 jornada, Ley 2155/2021 inversión social). Lower priority because their text is largely folded into the spines as `modifica` edges; their own body adds marginal value today.

Tiers A and B are the non-negotiable v2 deliverables. Tiers C and D are stretch — do only if time permits before a Phase 7 gate.

---

## Resumable state tracker (single source of truth)

Every phase mutates this table at `in_progress` and `done`. If an agent restarts mid-flight, **this table is authoritative**, not conversation context. All timestamps UTC.

| # | Phase | Status | Proof-of-completion | Updated |
|---|---|---|---|---|
| 0 | v2 scope refactor — add `jurisprudencia_full`, `decretos_op`, `contador_profesion` scopes with their seed URLs + sitemap entries; verify v1 infrastructure (truststore, stem matcher, resumenvigencias container, scripts) is intact on the branch | pending | new `_SCOPES` entries; `make test-batched` green; `lia_graph.ingestion.suin.harvest --help` lists new scopes | — |
| 1 | Tier A dry-run — `jurisprudencia_full` with `--max-documents 10 --rps 0.5` to validate `sitemapconsejoestado.xml` parser assumptions + sentencia DOM | pending | 10 sentencia HTML blobs in `cache/suin/`; `artifacts/suin/jurisprudencia_full/_harvest_manifest.json` has zero `unknown_verb_failures`; at least one `NotasOrigen*` or `resumenvigencias`-class block spot-checked in the parser output | — |
| 2 | Tier A full crawl — `jurisprudencia_full` at `rps=0.7` over `sitemapconsejoestado.xml` (filtered to sentencias referenced by existing prod stubs) → WIP merge under `gen_suin_wip_v2_<yyyymmdd>` | pending | `artifacts/suin/jurisprudencia_full/*.jsonl`; WIP generation adds ≥ 500 sentencia docs with non-empty body; SUIN edges under the new gen point into sentencia nodes with actual text (no longer stubs); expected ≥500 articles, ≥1,500 cross-ref edges | — |
| 3 | Tier B seed URLs — hand-curate and land the standalone decretos: 358/2020 (nómina electrónica), 2616/2013 (tiempo parcial), 771/2020 (conectividad), 2229/2017 (parafiscales reglamento), 957/2019 (PYME clasificación), 663/1993 (Estatuto Orgánico Sistema Financiero). Harvest at `rps=1.0` → merge into same WIP | pending | `artifacts/suin/decretos_op/*.jsonl`; WIP grows by 6 docs + their stubs; expected ≥200 articles, ≥400 edges | — |
| 4 | Tier C accountant-profession norms — Ley 43/1990, Ley 1314/2009, Decreto 2420/2015. Harvest → merge into same WIP | pending | `artifacts/suin/contador_profesion/*.jsonl`; WIP grows by 3 docs + their stubs; expected ≥100 articles, ≥300 edges | — |
| 5 | Tier D late reforms (optional; only if Tier C completes cleanly and time permits) — Ley 2101/2021, Ley 2155/2021 | pending | either `done` with artifacts or `skipped` with user-confirmed rationale | — |
| 6 | Embedding backfill against WIP — fills every new chunk (jurisprudence bodies especially — these are the high-value retrieval targets) | pending | `SELECT count(*) FROM document_chunks WHERE embedding IS NULL AND sync_generation=<gen>` → 0 on WIP; eval-c-gold dry-run on a jurisprudence-heavy question subset shows NDCG@10 lift | — |
| 7 | **Production push (end-to-end into active)** — one confirmed sequence: write v2 additions to cloud Supabase + cloud FalkorDB under `gen_suin_prod_v2`, run cloud embedding backfill, activate. Prior `gen_suin_prod_v1` deactivated but not deleted (rollback-ready). | done | `scripts/fire_suin_cloud.sh --target production --generation gen_suin_prod_v2 --scopes jurisprudencia_full --activate --confirm` exited 0. Start 2026-04-20T00:22:45Z, activation flip 2026-04-20T01:16:18Z, total ~54 min. Deltas: `documents` 2,355→6,693 (+4,338 incl. re-tagged corpus); v2-gen has 5,706 docs / 7,380 chunks / 23,930 edges; `document_chunks` cloud-wide 8,427→13,733 (+5,306); `normative_edges` 45,514→69,444 (+23,930 in-v2-gen); NULL embeddings cloud-wide **0**; cloud FalkorDB nodes 6,169→9,498 (+3,329), edges 29,553 total; `corpus_generations.gen_suin_prod_v2.is_active=true`, prior `gen_suin_prod_v1.is_active=false` (rollback-ready). Post-activation regression (shape-only) green. | 2026-04-20T01:18Z |

### Cloud baselines (filled in at the start of Phase 7 pre-flight — copy exact numbers from production at that moment)

| Backend | Metric | Baseline | Captured at (UTC) |
|---|---|---|---|
| Cloud Supabase (production) | `documents` count | 2,355 | 2026-04-19T22:26Z |
| Cloud Supabase (production) | `document_chunks` count | 8,427 | 2026-04-19T22:26Z |
| Cloud Supabase (production) | `normative_edges` count | 45,514 | 2026-04-19T22:26Z |
| Cloud Supabase (production) | active `generation_id` | gen_suin_prod_v1 (activated 2026-04-19T20:36:05Z) | 2026-04-19T22:26Z |
| Cloud FalkorDB | `MATCH (n) RETURN count(n)` | 6,169 | 2026-04-19T22:26Z |

**Reference — end-of-v1 cloud state (2026-04-19T20:36:05Z):**

| Backend | Metric | Value |
|---|---|---|
| Cloud Supabase (production) | `documents` | 2,355 |
| Cloud Supabase (production) | `document_chunks` | 8,427 |
| Cloud Supabase (production) | `normative_edges` | 45,514 |
| Cloud Supabase (production) | active `generation_id` | `gen_suin_prod_v1` |
| Cloud FalkorDB | `MATCH (n) RETURN count(n)` | 6,169 |

Capture commands (same as v1, elided here).

---

## Topic catalog — everything v2 plans to harvest

### Tier A — Jurisprudencia full text (the centerpiece)

**Why this is #1 for a Colombian accountant:**

An SMB accountant is asked "can I deduct X under ET art. Y?" The answer is rarely just the code article — it is "the Corte Constitucional ruled in C-481/2019 that the original wording was inexequible, so the operative text is what Ley 2010/2019 reinstated." Today Lia can name C-481/2019 but not show its holding. Landing the sentencia body converts that citation into a quotable paragraph.

**Scope:**

1. **Corte Constitucional sentencias** referenced by v1-generation edges. Union of:
   - Every sentencia that is the `target_doc_id` of a v1 `declara_exequible`/`declara_inexequible`/`struck_down_by`/`inhibida`/`estarse_a_lo_resuelto` edge.
   - Plus any sentencia in `sitemapleyes.xml` (Corte Constitucional publishes in this sitemap alongside Leyes) whose doc_id is already a `suin_stub` in production.
   
2. **Consejo de Estado sentencias** from `sitemapconsejoestado.xml`:
   - Sala Tercera (tributario / contencioso administrativo) — cited by ET stubs.
   - Sala Segunda (laboral / pensional) — cited by CST and Ley 100 stubs.
   - Filter: only sentencias whose citation text appears in v1 edges. This keeps the crawl proportionate to what the corpus actually cites.

3. **Corte Suprema Sala Laboral** — cross-referenced indirectly via `NotasOrigen*` blocks on CST articles. Harvest only those called out.

**Expected volumes:**

- ~1,500 Corte Constitucional sentencias (the bulk of v1's jurisprudence edges).
- ~400 Consejo de Estado sentencias (tax + labor combined).
- ~200 Corte Suprema sentencias (labor; cross-referenced only).
- **~2,100 sentencia docs** with body text, **~500 new article rows** (one "body" per sentencia; sentencias have holding + ratio decidendi as primary structure), and **~1,500–2,500 new edges** (most sentencias cite 2–5 articles + prior sentencias).

**Seed discovery strategy (differs from v1):**

v1 populated `SEED_URLS` by hand-searching SUIN's web UI. v2 can automate seed discovery for jurisprudencia because the target doc_ids are already in production Supabase:

```python
# Query production Supabase for all stub docs whose id looks like a sentencia
# (SUIN's numeric scheme: Corte Constitucional ids are 20XXXXXX, Consejo de
# Estado ids are 30XXXXXX or 100XXXXX — confirm the prefix in a 10-doc sample).
SELECT doc_id FROM documents
  WHERE source_type = 'suin_stub'
    AND sync_generation = 'gen_suin_prod_v1'
    AND doc_id ~ '^suin_(20|30|100)\\d{5,}'
```

Then strip the `suin_` prefix and materialize SEED_URLs as
`https://www.suin-juriscol.gov.co/viewDocument.asp?id=<stripped_id>`.

This makes the v2 Tier A scope **self-configuring** — it crawls exactly the sentencias the corpus already thinks it references.

### Tier B — Standalone reglamentary decretos

**Why this matters for an SMB accountant:**

An accountant implementing PILA (nómina electrónica + aportes) asks "what technical XML format does the DIAN require?" The answer is Resolución DIAN 000013/2021 + Decreto 358/2020. The DUR 1072 references these but does not consolidate their technical detail. An accountant asked "how do I classify as PYME for SIMPLE regime?" needs Decreto 957/2019, which the ET cites but does not carry. These decretos are **operational implementation detail** the spines deliberately omit.

**Seed norms (6, hand-curated — not automatable because they don't have a neat category filter):**

| # | Decreto | Purpose | Stub in v1? |
|---|---|---|---|
| 1 | Decreto 358/2020 | Nómina electrónica — reglamenta Resolución DIAN 000013/2021 | yes |
| 2 | Decreto 2616/2013 | Contratación por horas / tiempo parcial — reglamenta CST arts 161, 168 | yes |
| 3 | Decreto 771/2020 | Auxilio de conectividad para trabajadores remotos | yes |
| 4 | Decreto 2229/2017 | Reglamenta exoneración parafiscales — ET art 114-1 | yes |
| 5 | Decreto 957/2019 | Clasificación PYME — afecta ET SIMPLE, Ley 590/2000 modifications | yes |
| 6 | Decreto 663/1993 | Estatuto Orgánico del Sistema Financiero — cross-referenced by IVA, ICA | maybe |

**Expected volumes:** 6 primary docs + ~150 stubs (each decreto references prior articles); ~250 articles; ~400 new edges. Small but high-density value per article.

### Tier C — Accountant-profession base norms

**Why this matters:**

Lia serves contadores. The norms that govern the **contador's own work** are not in our corpus today. When a user asks "what's my responsibility if I sign off on a NIIF-misapplied financial statement?", the answer is Ley 43/1990 art 20–26 (obligaciones del contador) + Ley 1314/2009 (convergencia NIIF) + Decreto 2420/2015 (NIIF reglamento). v1 left these out because they are not tax or labor; v2 puts them in because the profession these accountants practice is governed by them.

**Seed norms (3):**

| # | Norm | Purpose |
|---|---|---|
| 1 | Ley 43/1990 | Estatuto del Contador Público — core professional duties |
| 2 | Ley 1314/2009 | Convergencia a NIIF — framework for IFRS adoption |
| 3 | Decreto 2420/2015 | Reglamento único NIIF — implementation detail |

**Expected volumes:** 3 primary + ~50 stubs; ~100 articles; ~300 new edges.

**Note on Código de Comercio (Decreto 410/1971):** explicitly *not* included. Too broad (books, titles, hundreds of articles) for the marginal accountant value. If an answer ever needs a specific Código de Comercio article, we stub-resolve via v3.

### Tier D — Late reforms (stretch, optional)

| # | Norm | Why low-priority |
|---|---|---|
| 1 | Ley 2101/2021 | Jornada 48→42 — already folded into CST consolidado as `modifica` edges |
| 2 | Ley 2155/2021 | Inversión social — partially absorbed by Ley 2277/2022 |

Include **only** if Tier A/B/C complete without blockers and the user explicitly signals they want them. Otherwise defer to v3.

### Explicitly out of scope for v2

- **DIAN normograma** (Resoluciones DIAN, conceptos, oficios) — separate source, separate plan in `docs/next/ingestion_dian.md`.
- **UGPP doctrine** (conceptos, circulares, resoluciones) — separate plan in `docs/next/ingestion_ugpp.md`.
- **MinTrabajo conceptos** — separate plan in `docs/next/ingestion_mintrabajo.md`.
- **Supersociedades circulares** (SAGRILAFT, PTEE) — needs its own plan after v2 lands.
- **Código de Comercio** — breadth-without-value trap.
- **Municipal norms** (ICA territorial, registros mercantiles) — SUIN is national only.
- **Full-text mirroring of non-SUIN jurisprudence** — sentencias only for now, no Colombian case law database outside SUIN.

---

## Phase 0 — v2 scope refactor (code change; no SUIN network calls)

### Goal

Add three new scopes to `src/lia_graph/ingestion/suin/harvest.py`: `jurisprudencia_full`, `decretos_op`, `contador_profesion`. Each resolves to its seed URLs + the appropriate sitemap. Preserve all v1 scopes as-is; **do not** mutate `laboral-tributario`, `tributario`, `laboral`, `jurisprudencia`, `full`, or `et`.

### Files to modify

- `src/lia_graph/ingestion/suin/fetcher.py`
  - Extend `SEED_URLS` with three new keys matching the new scopes.
  - `jurisprudencia_full` seeds: initially empty — populated at Phase 1 runtime by the auto-discovery query described in the Tier A section.
  - `decretos_op` seeds: 6 hand-curated Decreto URLs (see Tier B table).
  - `contador_profesion` seeds: 3 hand-curated norm URLs (Tier C).

- `src/lia_graph/ingestion/suin/harvest.py`
  - Add three `ScopeDefinition` entries with appropriate `sitemaps`, `seed_urls`, `topic_anchors`.
  - `jurisprudencia_full.sitemaps` = `(SITEMAPS[1],)` (consejoestado) + `(SITEMAPS[0],)` (leyes, for Corte Constitucional which lives here).
  - `decretos_op.sitemaps` = `(SITEMAPS[0],)`.
  - `contador_profesion.sitemaps` = `(SITEMAPS[0],)`.

- `Makefile`
  - Add `phase2-suin-harvest-jurisprudencia-full`, `phase2-suin-harvest-decretos-op`, `phase2-suin-harvest-contador-profesion`.
  - Keep all v1 targets unchanged.

### Files to create

- `scripts/suin_discover_sentencia_seeds.py` — auto-discovery helper for Tier A. Queries production Supabase for `suin_stub` docs whose ids match the sentencia numeric patterns (see the SQL in the Tier A section), strips prefixes, writes the discovered URLs into `artifacts/suin/jurisprudencia_full/_seed_urls.txt`. Phase 1 reads this file as the effective seed set.

### Tests

- `tests/test_suin_fetcher.py` — extend `test_scope_catalog_has_every_expected_scope` to also include the three new scopes.
- `tests/test_suin_fetcher.py` — extend `test_scope_seed_urls_are_well_formed` to assert every seed is a SUIN doc URL.
- `tests/test_suin_discover_sentencia_seeds.py` — new. Mocks the Supabase client, asserts the discovery script filters on the right prefixes and writes the file.

### Success criteria

- `uv run python -m lia_graph.ingestion.suin.harvest --help` lists the new scopes.
- `make test-batched` green.
- No network calls.

### Commit

`feat(suin-v2): scope refactor — jurisprudencia_full / decretos_op / contador_profesion`.

### State tracker update

Row 0 → `done` with commit sha.

---

## Phase 1 — Tier A dry-run on `jurisprudencia_full`

### Goal

First live contact with Corte Constitucional / Consejo de Estado sentencia HTML. Verify: (a) the `NotasOrigen*` blocks (reciprocal references — sentencia side) resolve correctly via the v1 `resumenvigencias`-class matcher; (b) the `ver_*` anchor → article-container lookup works on sentencias (their DOM is slightly different from Leyes — holdings live in `<div class="resuelve">` or similar); (c) no unknown verb families appear in the sentencia vocabulary.

### Pre-step: auto-discover seeds

```
LIA_ENV=staging PYTHONPATH=src:. uv run python scripts/suin_discover_sentencia_seeds.py \
  --target production \
  --generation gen_suin_prod_v1 \
  --out artifacts/suin/jurisprudencia_full/_seed_urls.txt
# Expected: file contains ~1,500-2,500 SUIN viewDocument URLs
```

### Command

```
PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest \
  --scope jurisprudencia_full \
  --out artifacts/suin/jurisprudencia_full \
  --cache-dir cache/suin \
  --max-documents 10 \
  --rps 0.5 \
  --json
```

### Validation (checklist)

- [ ] `cache/suin/` gained 10 new sentencia HTML blobs.
- [ ] `_harvest_manifest.json` has `unknown_verb_failures: []`.
- [ ] At least 5 of the 10 sentencias emit ≥1 outbound edge (sentencias cite the norm they rule on; a sentencia with zero edges is likely a DOM-shape regression).
- [ ] Spot-check one sentencia's parsed `body_text`: it should contain the word "RESUELVE" (holding keyword) somewhere in the first 2,000 chars.
- [ ] Spot-check `verb_counts`: expect high `declara_exequible` / `declara_inexequible` / `estarse_a_lo_resuelto` counts; lower `modifica` / `adiciona` (sentencias rarely modify).

### Expected failure modes

- **Sentencia DOM uses different article container classes** (e.g., `<div class="considerando">`, `<div class="resuelve">`). Fix: extend `_locate_article_container` to match these. Same recipe as v1's DOM fixes.
- **New jurisprudence verbs**: likely candidates — "ordenar", "exhortar", "tutelar", "revocar". Stem-match if they share a root; new canonical if they represent a new edge family.

### Tests added

- `tests/fixtures/suin/sentencia_snapshot_<yyyymmdd>/` — save 3 parsed HTML blobs + their manifest for regression.
- `tests/test_suin_sentencia_snapshot.py` — parameterized parser regression.

### State tracker update

Row 1 → `done` with manifest path and verb_counts.

---

## Phase 2 — Tier A full crawl → WIP merge

### Goal

Crawl the full jurisprudencia seed set discovered in Phase 1. Merge into `gen_suin_wip_v2_<yyyymmdd>`. The key success metric is: **every sentencia that was a stub in `gen_suin_prod_v1` now has body text in WIP**.

### Harvest command

```
PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest \
  --scope jurisprudencia_full \
  --out artifacts/suin/jurisprudencia_full \
  --cache-dir cache/suin \
  --rps 0.7 \
  --json | tee artifacts/suin/jurisprudencia_full/_run_<ts>.log
```

`rps=0.7` matches v1's jurisprudencia plan (sitemapconsejoestado.xml is bigger than sitemapleyes.xml and Corte Constitucional rate-limit tolerance is untested at rps=1.0).

### WIP merge

```
LIA_ENV=staging FALKORDB_URL=redis://127.0.0.1:6389 FALKORDB_GRAPH=LIA_REGULATORY_GRAPH \
  PYTHONPATH=src:. uv run python -m lia_graph.ingest \
    --corpus-dir knowledge_base --artifacts-dir artifacts \
    --supabase-sink --supabase-target wip \
    --execute-load --allow-unblessed-load --strict-falkordb \
    --include-suin jurisprudencia_full \
    --supabase-generation-id gen_suin_wip_v2_<yyyymmdd> \
    --no-supabase-activate \
    --json | tee artifacts/suin/jurisprudencia_full/_ingest_wip_<ts>.log
```

### Expected volumes

- **~2,100 sentencia docs** flip from `source_type=suin_stub` to `source_type=suin_norma` (primary body).
- **~5,000 new chunks** (sentencias are long; each yields multiple chunks at the sink's chunking ratio).
- **~1,500–2,500 new edges** from sentencia `NotasOrigen*` blocks pointing back at the norms they ruled on.

### Verification

```
LIA_ENV=staging PYTHONPATH=src:. uv run python scripts/verify_suin_merge.py \
  --target wip --generation gen_suin_wip_v2_<yyyymmdd> \
  --scope-dir artifacts/suin/jurisprudencia_full --json
```

Plus a v2-specific check (add to `verify_suin_merge.py` as Phase 0 deliverable):

```
# How many prior stubs became primary in this run?
SELECT count(*) FROM documents
  WHERE source_type = 'suin_norma'
    AND sync_generation = '<v2_wip_gen>'
    AND doc_id IN (
      SELECT doc_id FROM documents
        WHERE source_type = 'suin_stub' AND sync_generation = 'gen_suin_prod_v1'
    );
# Expected: ≥ 80% of Phase 1's seed count
```

### State tracker update

Row 2 → `done`.

---

## Phase 3 — Tier B decretos reglamentarios → WIP merge

### Goal

Land the 6 standalone reglamentary decretos. Small crawl (6 seeds + their cross-refs), high density per doc.

### Harvest command

```
PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest \
  --scope decretos_op \
  --out artifacts/suin/decretos_op \
  --cache-dir cache/suin \
  --max-documents 6 \
  --rps 1.0 \
  --json | tee artifacts/suin/decretos_op/_run_<ts>.log
```

### WIP merge

Same template as Phase 2 with `--include-suin decretos_op` into the same `gen_suin_wip_v2_<yyyymmdd>`.

### Expected volumes

- 6 primary docs, ~150 stubs auto-created, ~250 articles, ~400 edges.

### Acceptance

- Decreto 358/2020 articles show `reglamenta` edges into ET 615 (facturación) and CST 127 (pagos laborales).
- Decreto 2229/2017 articles show `reglamenta` edges into ET 114-1 (the cross-domain parafiscales exoneración — previously stub-resolved only).
- `verify_suin_merge.py` returns `ok: true` for the scope.

### State tracker update

Row 3 → `done`.

---

## Phase 4 — Tier C contador profesión → WIP merge

### Goal

Land Ley 43/1990, Ley 1314/2009, Decreto 2420/2015. First time the corpus carries the contador-profession regulatory stack.

### Harvest command

```
PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest \
  --scope contador_profesion \
  --out artifacts/suin/contador_profesion \
  --cache-dir cache/suin \
  --max-documents 3 \
  --rps 1.0 \
  --json | tee artifacts/suin/contador_profesion/_run_<ts>.log
```

### WIP merge

Same template, `--include-suin contador_profesion`, same WIP gen.

### Expected volumes

- 3 primary docs, ~50 stubs, ~100 articles, ~300 edges.

### Acceptance

- Ley 43/1990 art 20–26 land as articles with body text — these are the accountant's core duties.
- `verify_suin_merge.py` returns `ok: true`.

### State tracker update

Row 4 → `done`.

---

## Phase 5 — Tier D late reforms (optional; only with user nod)

### Decision gate

Before running this phase, ask the user: "Tier A/B/C done. Tier D (Ley 2101/2021 + Ley 2155/2021) adds marginal value since their changes are already captured as `modifica` edges in v1. Run it or skip?" If unclear, **skip** and flag in the tracker.

### Harvest command (if go)

Add two URLs to `SEED_URLS["decretos_op"]` (same scope, reused — avoid scope proliferation) or harvest into a new `late_reforms` scope. Prefer the latter so intent stays clean.

### State tracker update

Row 5 → `done` (with artifacts) or `skipped` (with user rationale).

---

## Phase 6 — Embedding backfill against WIP

### Goal

Embed every new chunk written in Phases 2–5. The jurisprudencia chunks are the most valuable targets for embedding: sentencia text is long-form legal reasoning that FTS alone retrieves poorly; dense embeddings are where the retrieval quality lift actually lives.

### Command

```
LIA_ENV=staging GEMINI_API_KEY="$GEMINI_API_KEY" PYTHONPATH=src:. uv run python scripts/embedding_ops.py \
  --target wip --generation gen_suin_wip_v2_<yyyymmdd> \
  --batch-size 100 --json
```

### Validation

- `SELECT count(*) FROM document_chunks WHERE embedding IS NULL AND sync_generation=<v2_wip_gen>` → 0.
- Optional: `make eval-c-gold` on a jurisprudence-heavy question subset — NDCG@10 should lift ≥5 points above `gen_suin_prod_v1` baseline.

### State tracker update

Row 6 → `done`.

---

## Phase 7 — **PRODUCTION PUSH** (irreversible; user gate)

### What this phase does

`scripts/fire_suin_cloud.sh` runs the same orchestrator as v1 but with the v2 scopes and the v2 generation id. The full sequence (mirroring v1 step-for-step):

1. Sequential scope merges under `--supabase-generation-id gen_suin_prod_v2`: `jurisprudencia_full`, `decretos_op`, `contador_profesion`, and `late_reforms` (if Phase 5 ran).
2. Cumulative count repair on `corpus_generations.gen_suin_prod_v2`.
3. `scripts/verify_suin_merge.py --target production --generation gen_suin_prod_v2`.
4. `scripts/embedding_ops.py --target production --generation gen_suin_prod_v2` — backfills the new v2 chunks (legacy chunks are already embedded from v1).
5. Null-embedding gate.
6. Activation flip `gen_suin_prod_v1` → `gen_suin_prod_v2`.
7. Post-activation regression; auto-rollback on failure.

### Pre-flight checklist

- [ ] All Phase 0–6 rows `done` on the state tracker.
- [ ] `verify_suin_merge.py --target wip` passes.
- [ ] Cloud baselines captured in the "Cloud baselines" table (filled with real numbers, not placeholders).
- [ ] `cache/suin/` warm.
- [ ] Chat regression fixtures reviewed — specifically, the 2 derogated-article fixtures should now exercise the jurisprudence full-text path (expectation: answer cites the holding, not just the sentencia name). Adjust `expected_contains` if needed.
- [ ] User has said "go" in writing this session.

### Command

```
LIA_ENV=staging GEMINI_API_KEY="$GEMINI_API_KEY" FALKORDB_URL="$FALKORDB_URL" \
  PYTHONPATH=src:. ./scripts/fire_suin_cloud.sh \
    --target production \
    --generation gen_suin_prod_v2 \
    --scopes jurisprudencia_full,decretos_op,contador_profesion \
    --activate \
    --confirm \
    | tee artifacts/suin/_production_push_v2_<ts>.log
```

Add `,late_reforms` to `--scopes` only if Phase 5 ran.

### Rollback (if needed post-activation)

```
PYTHONPATH=src:. uv run python scripts/supabase_flip_active_generation.py \
  --target production --generation gen_suin_prod_v2 \
  --previous-generation gen_suin_prod_v1 --rollback --confirm
```

Users stop seeing v2 data, v1 becomes active again. No data loss — v2 rows remain in cloud, just inactive.

### State tracker update

Row 7 → `done` with:
- cloud documents / chunks / edges deltas vs. baselines.
- cloud Falkor node delta.
- `gen_suin_prod_v2.is_active=true` + `gen_suin_prod_v1.is_active=false` confirmed.
- regression summary.

---

## Shared WIP merge contract (reuses v1 `scripts/verify_suin_merge.py`)

v1's verification script works as-is against v2 generations — it is generation-id parametric, not scope-parametric. The only v2-specific check (stub→primary flip rate) is an **additive** extension to the script in Phase 0:

```python
# scripts/verify_suin_merge.py — Phase 0 v2 extension
def _stub_to_primary_flip_rate(client, prior_gen, current_gen) -> float:
    # Count docs that were suin_stub under prior_gen and are now suin_norma under current_gen.
    ...
```

Surface this in the report `totals` block. Failure threshold: Phase 2 should flip ≥80% of prior jurisprudence stubs; failing below is a coverage gap worth investigating before proceeding.

---

## Risks and how we address them

- **Corte Constitucional DOM divergence from Leyes.** Sentencias use `<div class="resuelve">` etc., not `<div class="articulo_normal">`. Phase 1 dry-run catches this; fix in `_locate_article_container`.
- **Sentencia length blows up chunk counts.** A single C-XXX sentencia can be 50+ pages. Chunks-per-doc ratio for jurisprudencia will be ≥20 vs. ~140 for the ET. Budget for 50k+ new chunks in Phase 6's embedding backfill.
- **Embedding cost for jurisprudencia.** Tier A is the expensive phase — 5k–10k new chunks at Gemini's embedding price. Still well under $10 at current Gemini rates for `gemini-embedding-001`, but flag to the user if the job runs longer than expected.
- **Stub-flip incompleteness.** Some prior-gen stub sentencias may not be in SUIN at all (wrong doc_id heuristic, deleted by SUIN, etc.). Expected flip rate 80–90%, not 100%. Document the shortfall in the manifest; do not block Phase 7.
- **Rate-limit 429 on Corte Constitucional.** `rps=0.5` for Phase 1 dry-run is conservative; ease to 0.7 for Phase 2 only if the dry-run didn't get 429'd. Do not retry hot.
- **Cloud writes are idempotent but Falkor schema changes are not.** If Phase 3/4 introduces a new `EdgeKind`, schema.py + supabase_sink.py must be updated in Phase 0, not Phase 3. This was v1's pattern.

---

## Handoff checklist

Before implementing:

- Read `AGENTS.md`, `docs/orchestration/orchestration.md`, `docs/guide/env_guide.md`.
- Read v1's state tracker to confirm `gen_suin_prod_v1` is live and all v1 rows are `done`.
- Confirm `cache/suin/` is still gitignored.
- Confirm `feat/suin-ingestion-v2` branch exists off `feat/suin-ingestion`; the v1 branch stays untouched.
- Capture a production Falkor baseline before Phase 7: `GRAPH.QUERY LIA_REGULATORY_GRAPH "MATCH (n) RETURN count(n)"` — v1 end state was **6,169 nodes**.
- For every cloud-touching phase: capture the baseline before firing; wait for user confirmation; never use `--no-verify` or bypass the reconnaissance gate without `--allow-unblessed-load`.

---

## Common failures and their recipes

Most v1 common-failures recipes transfer verbatim. v2-specific additions:

### "Sentencia parser returns zero articles" (Phase 1/2)

- Symptom: 10 sentencia docs fetched, 0 articles parsed.
- Cause: Corte Constitucional or Consejo de Estado uses a container class not in `_locate_article_container`'s match set.
- Recipe: dump the DOM of one zero-article sentencia, identify the article container class (likely `resuelve` or `considerando`), add it to `_locate_article_container`. Add a regression fixture.

### "Stub-flip rate <80% in Phase 2"

- Symptom: fewer than 80% of prior-gen sentencia stubs acquired body in this run.
- Possible causes:
  1. `scripts/suin_discover_sentencia_seeds.py` regex didn't match all sentencia doc_id patterns — audit the prefixes.
  2. Some sentencias are listed in `sitemapleyes.xml` but not in `sitemapconsejoestado.xml` and were excluded. Extend the scope to include both sitemaps.
  3. SUIN returned 404 for some sentencias (deleted / renumbered). Log these; document expected shortfall.
- **Do not** lower the 80% threshold without understanding the root cause.

### "Phase 6 embedding job fails on jurisprudencia chunk length"

- Cause: a sentencia chunk exceeds Gemini's input token limit (8,192 tokens).
- Recipe: the sink's chunker already bounds on characters; if a chunk still exceeds Gemini's limit, log-and-skip (it'll stay NULL-embedded — accept the loss, FTS still retrieves) or lower `LIA_EMBED_CHUNK_CHARS`.

### "v2 activation flip rolled back in Step 7 regression"

- Cause: a chat regression fixture expected a v1-era answer shape that v2 no longer produces.
- Recipe: the rollback leaves `gen_suin_prod_v1` active (no data loss). Diff the failing fixture against the v2 answer; decide whether the new answer is correct (update the fixture) or regressed (fix the new data). Re-fire Phase 7 only after a clean fixture review.

---

## Stop condition

You are done when every row of the v2 state tracker is `done`. At that point `gen_suin_prod_v2` is the active generation; users see v2 answers (sentencia full text, decreto reglamentary detail, contador profession norms) immediately. Do not start v3 planning without the user asking — v2 is a large enough corpus expansion that a post-launch soak is worth a week before the next layer.
