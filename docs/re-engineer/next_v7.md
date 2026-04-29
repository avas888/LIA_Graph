# next_v7.md — forward plan after fixplan_v6 close

> **Status:** drafted 2026-04-29 AM Bogotá right after fixplan_v6 + v6.1
> closed. Postgres `norm_vigencia_history`: 783 → **2362** distinct
> verified norms (+1579 net rows from v6 cascade alone). Working tree
> clean, all v6 commits pushed to `origin/main`.
>
> **Audience:** any zero-context agent or engineer who picks up the
> work after this session. Read §0 and §1 first; the rest is
> task-specific.
>
> **Authoritative companions:**
> * `docs/re-engineer/fixplan_v6.md` — v6 plan (closed) + §8b
>   post-launch lessons.
> * `docs/re-engineer/state_fixplan_v6.md` §10 — cascade run log with
>   per-batch outcomes.
> * `docs/learnings/canonicalizer/v6_suin_first_rewire_2026-04-28.md`
>   — 9 engineering lessons from the v6 cycle.
> * `docs/learnings/sites/per-source-fetch-playbook.md` — cross-cutting
>   guide on how each of our 6 scrapers works, how to add a 7th.
> * `CLAUDE.md` — repo-level operating guide.

---

## 0. If you are a zero-context agent — read this first

You are picking up after a successful 11-hour autonomous canonicalizer
cascade run that produced **2,653 verified vigencia veredictos with
0 errors at 92.4% pass rate**. The architecture works. What you're
doing now is **harvesting the value** (cloud promotion) and
**extending coverage** (closing the remaining gaps).

**Hot facts:**

* **DeepSeek-v4-pro is the active LLM.** `LLM_DEEPSEEK_RPM=240` is the
  preferred throttle (the older 80 default was Gemini-derived, see
  commit `a3ee6cd`).
* **Local docker stack must be UP.** `docker ps` must show
  `supabase_db_lia-graph` and `lia-graph-falkor-dev`.
* **Cloud writes for Lia Graph are pre-authorized** by the operator.
  Announce, don't ask. (memory: `feedback_lia_graph_cloud_writes_authorized`)
* **6 scrapers in the canonicalizer chain** (since v6.1):
  `[suin_juriscol, secretaria_senado, funcion_publica, dian_normograma, corte_constitucional, consejo_estado]`.
  Wired in `src/lia_graph/vigencia_extractor.py::default()`.
* **The cascade driver is `scripts/canonicalizer/run_cascade_v5.sh`**
  but for individual batch runs use `scripts/canonicalizer/launch_batch.sh`
  directly with `--allow-rerun --skip-post --skip-pre`.

**Memory-pinned guardrails (do not violate):**

* Cloud writes pre-authorized — announce, don't ask.
* Beta-stance: every non-contradicting improvement flag flips ON.
* Never re-extract Phases A–D — extract once, promote through three stages.
* All canonicalizer runners delegate to `launch_batch.sh`. Do NOT re-implement.
* Project-wide LLM throttle (`LLM_DEEPSEEK_RPM=240`) — never bypass.
* Autonomous progression — proceed without check-ins; stop only on real kill-switches.
* Diagnose before intervene.
* Six-gate lifecycle for pipeline changes — unit tests alone never sufficient.

---

## 1. What v6 + v6.1 delivered

### v6 — SUIN-first scraper rewire (closed 2026-04-28 PM → 2026-04-29 06:22 AM Bogotá)

**Diagnosis:** prior cascades collapsed because the harness queried
DIAN normograma's 3 MB master pages (which the LLM couldn't slice)
and ignored the 3,387 already-cached SUIN-Juriscol HTML files.

**Engineering shipped (9 commits):**

| Commit | What |
|---|---|
| `cfe64bb` | SUIN canonical-id → doc-id registry build script |
| `9940faf` | SUIN scraper + parser regex fix (multi-segment DUR keys) |
| `d00da64` | Chain reorder, SUIN first; trusted .gov.co set expanded |
| `f91401b` | `--rerun-only-refusals` flag + `EXTRA_EXTRACT_FLAGS` in launcher |
| `f6525e1` | Engineering ledger close |
| `a3ee6cd` | `LLM_DEEPSEEK_RPM` env var (Gemini→DeepSeek transition) |
| `3845ee7` | Per-URL parsed-doc cache (48× speedup, fixed memory thrash) |
| `92c5661` | **Persisted slice cache via SQLite (Option 2, 38× speedup, parallel-safe)** |
| `19fd5a1` | 6-lesson learnings doc (later extended to 9) |

**Cascade outcome (14 batches × 11 hours, 0 errors):**

| Wave | Batches | Successes | Pass rate |
|---|---|---|---|
| Wave 1 (DUR-1625) | E1a/E1b/E1d/E2a/E2c/E3b | 1,719 | **96.9%** |
| Wave 2 (CST/CCo) | J1/J2/J3/J4/K3 | 197 | 55.6% (CST 100%, K3 30%) |
| Wave 3 (DUR-1072) | E6b/E6c/J8b | 737 | **97.7%** |
| Plus retries | F2 + D5 | 35 | mixed |
| **Total** | 14 batches | **2,653** | **92.4%** |

### v6.1 — Función Pública 6th scraper (closed 2026-04-29 AM Bogotá)

`34ef8f9` added Función Pública gestor normativo as backup primary
source. Coverage: 26 DURs (incl. DUR-1625, DUR-1072 + 24 others).
Smoke-tested live end-to-end via `extract_vigencia.py`. **Doesn't
close F2 + G1 gaps** — Función Pública doesn't host DIAN-specific
resoluciones / conceptos at predictable URLs.

---

## 2. Current state (2026-04-29 AM)

### Local docker stack

| Resource | Value |
|---|---|
| Postgres `norm_vigencia_history` (distinct) | **2,362 norms** |
| Postgres rows (with history versions) | 3,809 |
| Veredicto JSONs on disk | **4,147** across 40 batch directories |
| Migrations on disk | 17 |
| Migrations applied locally | 17 |
| Falkor `(:Norm)` nodes | ~11,700 (last measured pre-v6) |
| SUIN HTML cache | 3,387 files at `cache/suin/` |
| SUIN registry | 10 entries (`var/suin_doc_id_registry.json`) |
| Función Pública registry | 26 entries (`var/funcionpublica_doc_id_registry.json`) |

### Veredicto inventory by batch family

| Family | Batches | Description |
|---|---|---|
| B | 1 | Sentencias (B10) |
| C | 4 | Conceptos / oficios DIAN (C1-C4) |
| D | 12 | Leyes (D1-D8) |
| **E** | 16 | DUR articulado (E1*/E2*/E3*/E4/E5/E6*) — bulk of the corpus |
| F | 4 | Resoluciones DIAN (F1-F4) — F2 has the 81 unresolved refusals |
| G | 2 | Concepto Unificado (G1=407 norms, G6) |
| J | 8 | CST (J1-J8b) |
| K | 2 | CCo (K3, K4) |

### What's UNcommitted vs cloud (operator concern)

The 1,579 net new rows from v6 are in **local docker** Supabase. They
are NOT in cloud staging Supabase yet. Per operator directive
2026-04-29 AM: cloud promotion must reconcile **everything local has**
that cloud might be missing — not just v6's contribution, but
potentially earlier cycles' (v3/v4/v5) output too. See P1 below for
the audit-first procedure.

### Open gaps after v6.1

| Gap | Norms | Why open | v7 path |
|---|---|---|---|
| F2 (res.dian.13.2021.art.*) | 81 refusals | DIAN-specific; not in SUIN, Senado, or FP | P2 (DIAN main site probe) |
| G1 (concepto.dian.0001.2003) | 407 norms | Same | P2 (same investigation) |
| K3 (cco.art.* high-numbered) | 157 refusals | Senado anchor-slicing depth too shallow on master page | P3 (try FP, build CCo segment index) |
| E5 (decreto.417.2020.*) | 104 norms | Not in SUIN harvest | P7 (SUIN harvest extension) |

---

## 3. Forward tasks — ordered

| Order | Priority | Action | Effort | Why this slot |
|---:|---|---|---|---|
| **1** | P1 | **Comprehensive cloud promotion (audit + reconcile + push)** | 1-2 hr | Foundational. Don't just promote v6's 1,579 — audit local-vs-cloud diff and promote ALL local artifacts cloud is missing. |
| **2** | P5 | Falkor edge sync verification post-promotion | 5 min | Confirms cloud Postgres + Falkor stay in parity after P1. |
| **3** | P4 | Embedding backfill on the new cloud rows | 30 min + ~1-2 hr compute | Runs in background after P1; unlocks semantic search on the new vigencias. |
| **4** | P3 | K3 CCo gap close — try Función Pública first, fall back to building a CCo segment index | 1-2 hr | Cheapest gap-close attempt; +~150 norms if FP has CCo. |
| **5** | P6 | Refusal rerun with `--max-source-chars 32000` | 3 hr | Recovers ~50-80 boundary refusals where the LLM was just below context need. |
| **6** | P2 | DIAN main site probe → 7th scraper if viable | 2-8 hr | Investigation. **Parallel-agent friendly** — see §3.6. Closes F2/G1 if DIAN has stable per-doc URLs. |
| **7** | P7 | SUIN harvest extension (decreto 417/2020, missing CCo segments) | 3-5 hr per scope | Last because biggest scope; covers what nothing else does (e.g. E5 COVID decretos). |

After this sequence, the canonicalizer's program is fully operational
on cloud. Remaining gaps become v8 candidates.

---

### 3.1 P1 — Comprehensive cloud promotion (audit + reconcile + push)

**Operator directive (2026-04-29 AM):** "make sure we have promoted
EVERYTHING the local env has to promote, fruit of our labour (not
only the 1579 v6 but all other that may not be in cloud for whatever
reason) and make sure all DB migrations are fully implemented."

This is NOT a one-shot ingest of v6's 1579 rows. This is a **full
local-vs-cloud reconciliation** before any new ingest.

**Step 1.1 — Schema migration parity check (~10 min).**

```bash
# Ensure .env.local does NOT clobber cloud creds; we want staging context.
set -a; . .env.staging; set +a   # cloud creds

# What migrations does cloud have applied?
PYTHONPATH=src:. uv run python -c "
from lia_graph.supabase_client import get_client
c = get_client()
rows = c.rpc('list_applied_migrations').execute().data  # may need to add this RPC OR query supabase_migrations.schema_migrations directly
print(rows)
" 2>&1 | tail -20
```

If cloud is missing migrations that exist on disk
(`supabase/migrations/*.sql`), apply them via the Supabase project
dashboard OR via `supabase db push --linked` if the project is
linked. **Do NOT apply migrations blindly — confirm each one's safety
first.** The squashed baseline (`20260417000000_baseline.sql`) should
already be there; later additive migrations may not be.

**Step 1.2 — Local-vs-cloud `norm_vigencia_history` diff (~15 min).**

```bash
# Local count (already known):
docker exec supabase_db_lia-graph psql -U postgres -tAc \
  "SELECT COUNT(DISTINCT norm_id) FROM norm_vigencia_history"
# → 2362

# Cloud count via supabase_client:
PYTHONPATH=src:. uv run python -c "
from lia_graph.supabase_client import get_client
c = get_client()
rows = c.table('norm_vigencia_history').select('norm_id', count='exact').execute()
print(f'cloud rows: {rows.count}')
# distinct norm_ids:
seen = set(r['norm_id'] for r in c.table('norm_vigencia_history').select('norm_id').execute().data)
print(f'cloud distinct norm_ids: {len(seen)}')
"
```

The delta is what needs to be promoted.

**Step 1.3 — Bulk re-ingest ALL local batch dirs to cloud (~30-45 min).**

```bash
set -a; . .env.staging; set +a

# Iterate all 40 batch dirs that have JSONs. The ingest script is
# idempotent (UPSERT on norm_id) so re-ingesting already-cloud rows
# is a no-op.
for batch in $(ls -d evals/vigencia_extraction_v1/*/ | sed 's|.*/\([^/]*\)/$|\1|' | grep -v "^_"); do
  count=$(ls evals/vigencia_extraction_v1/$batch/*.json 2>/dev/null | wc -l | tr -d ' ')
  [ "$count" = "0" ] && continue
  echo "── Promoting $batch ($count JSONs) ──"
  PYTHONPATH=src:. uv run python scripts/canonicalizer/ingest_vigencia_veredictos.py \
    --target production \
    --run-id "v6-cloud-promotion-$(date -u +%Y%m%dT%H%M%SZ)" \
    --extracted-by ingest@v1 \
    --input-dir "evals/vigencia_extraction_v1/$batch"
done | tee logs/cloud_promotion_$(date +%Y%m%dT%H%M%SZ).log
```

**Step 1.4 — Verify post-ingest count parity (~5 min).**

```bash
# Cloud count should now match local (2362 distinct norms minimum).
PYTHONPATH=src:. uv run python -c "
from lia_graph.supabase_client import get_client
c = get_client()
seen = set(r['norm_id'] for r in c.table('norm_vigencia_history').select('norm_id').execute().data)
print(f'cloud distinct norm_ids after promotion: {len(seen)}')
"
```

**Step 1.5 — Falkor sync (cloud) (~10 min).**

```bash
PYTHONPATH=src:. uv run python scripts/canonicalizer/sync_vigencia_to_falkor.py \
    --target production
```

**Risk:** moderate. UPSERT on norm_id is idempotent so re-promotion
of already-cloud rows is safe. The risk is migrations: applying a new
migration to cloud is harder to roll back than data writes.

**Kill-switch:** if any migration fails to apply OR ingest reports
errors > 0, halt and investigate before continuing.

---

### 3.2 P5 — Falkor edge sync verification (~5 min)

After P1.5, verify cloud Falkor reflects the cloud Postgres state:

```bash
# Cloud Falkor count (via supabase_client or direct redis client):
docker exec lia-graph-falkor-dev redis-cli -p 6379 \
    GRAPH.QUERY LIA_REGULATORY_GRAPH "MATCH (n:Norm) RETURN count(n)"
```

Compare against cloud Postgres `norm_vigencia_history` distinct count.
They should match within a small delta (sentencias get nodes too).

If counts diverge by >50 nodes, re-run sync with `--rebuild`:
```bash
PYTHONPATH=src:. uv run python scripts/canonicalizer/sync_vigencia_to_falkor.py \
    --target production --rebuild
```

---

### 3.3 P4 — Embedding backfill (~30 min orchestration + ~1-2 hr compute)

The new Postgres rows have `chunk_text_embedding = NULL`. The
retrieval path needs them.

```bash
set -a; . .env.staging; set +a

# Run the embedding backfill. It picks up rows where embedding IS NULL.
PYTHONPATH=src:. uv run python -m lia_graph.embedding_ops \
    --target production \
    --batch-size 100 \
    > logs/embedding_backfill_$(date +%Y%m%dT%H%M%SZ).log 2>&1 &
disown
```

Verify post-run:
```bash
PYTHONPATH=src:. uv run python -c "
from lia_graph.supabase_client import get_client
c = get_client()
total = c.table('document_chunks').select('id', count='exact').execute().count
filled = c.table('document_chunks').select('id', count='exact').not_.is_('chunk_text_embedding', 'null').execute().count
print(f'total chunks: {total}, with embedding: {filled}, gap: {total - filled}')
"
```

Aim for 100% fill of new chunks. Existing pre-v6 chunks may already
have embeddings; the backfill is incremental.

---

### 3.4 P3 — K3 CCo gap close

**Step 3a (cheapest, try first):** add CCo to Función Pública. Probe
whether the gestor normativo has Código de Comercio:

```bash
curl -s -L -H "User-Agent: Mozilla/5.0 Lia-Graph/1.0" \
  "https://www.funcionpublica.gov.co/eva/gestornormativo/" | \
  grep -oE 'norma\.php\?i=[0-9]+"[^>]*>[^<]*[Cc][Oo][Mm][Ee][Rr][Cc][Ii][Oo]' | head
```

If found:
1. Add the doc_id to `INDEX_PAGES` (or directly to `_SEED_OVERRIDES`)
   in `scripts/canonicalizer/build_funcionpublica_registry.py`.
2. Re-run the build script.
3. Smoke-test a single CCo norm via `extract_vigencia.py --workers 1`.
4. Re-run K3 batch with `--rerun-only-refusals` — slices that
   previously refused via Senado now have FP as a viable second
   source.

**Step 3b (fallback):** build the Senado CCo pr-segment index.
Mirror `scripts/canonicalizer/build_senado_et_index.py` for
`codigo_comercio_pr<NNN>.html`. Update Senado scraper to use the
index for CCo article resolution. Re-run K3.

**Decision point:** if 3a recovers ≥100 K3 refusals, ship that and
defer 3b. If 3a recovers <50, ship 3b.

---

### 3.5 P6 — Refusal rerun with bigger context (~3 hr)

Some refusals were boundary cases — the LLM had just-too-thin a slice.
Doubling the per-source character cap may close 50-80 of them.

**Code change:** add `--max-source-chars` flag to
`scripts/canonicalizer/extract_vigencia.py` that overrides the harness's
hardcoded 16000 limit (in `_build_prompt`).

**Run:**
```bash
EXTRA_EXTRACT_FLAGS="--rerun-only-refusals --max-source-chars 32000" \
LIA_EXTRACT_WORKERS=8 LLM_DEEPSEEK_RPM=240 \
nohup bash scripts/canonicalizer/run_cascade_v5.sh \
    > logs/cascade_v6_2_driver.log 2>&1 &
disown
```

**Watch:** the heartbeat sidecars per batch. Same kill-switches as v6
cascade. Don't run E1a long tail again — it already closed at 96.7%.

---

### 3.6 P2 — DIAN main site probe → 7th scraper if viable

**This task is parallel-agent friendly.** The probe phase is pure
investigation work that doesn't compete for local resources.

**Step 2a (probe, parallel-agent friendly).** Launch a fork agent
(or two — one for F2, one for G1) with this prompt template:

```
Probe DIAN's main site (dian.gov.co — NOT the normograma) for stable
per-document URLs for [Resolución 13/2021 | Concepto Unificado IVA
0001/2003]. Report:
* Found URL (HTTP 200 verified)
* Slicing feasibility (HTML anchors? PDF blob? per-article structure?)
* Stability (fetch twice with 30s gap; consistent response?)
* Recommendation: HTML 7th scraper (~3 hr) | PDF 7th scraper (~6-8 hr) | skip
Hard rule: only verify URLs you actually fetched. Government sites only.
```

While the probe agent runs, work on P1-P5 in parallel. The probe
agent's findings inform whether to commit engineering effort to a 7th
scraper.

**Step 2b (if HTML viable):** build a `DianMainSiteScraper` mirroring
the SUIN/FP scraper architecture. Reuse the per-URL parsed-doc cache
+ persisted slice cache patterns.

**Step 2c (if PDF only):** add pdf2text dependency, build a
`DianPdfScraper` that extracts per-article text by regex on
`ARTÍCULO N` headings.

**Either way, the new scraper:**
1. Goes into `src/lia_graph/scrapers/dian_<...>.py`.
2. Wires into `vigencia_extractor.py default()` chain after Función
   Pública.
3. Joins `_TRUSTED_GOVCO_SOURCE_IDS`.
4. Has tests, docs, and per-source learnings doc.

---

### 3.7 P7 — SUIN harvest extension (~3-5 hr per scope)

Extend the SUIN harvester to cover gaps:
* `decreto.417.2020` (E5: 104 COVID decretos)
* CCo segments not currently in `cache/suin/` (subset of K3)

**Steps per scope:**

1. Identify the SUIN `id=<NUMERIC>` for the missing doc(s) via
   `https://www.suin-juriscol.gov.co/inicio/`.
2. Add to `SEED_URLS` in `src/lia_graph/ingestion/suin/fetcher.py`.
3. Re-run harvest:
   ```bash
   PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest \
       --scope <scope-name>
   ```
4. Rebuild registry:
   `scripts/canonicalizer/build_suin_doc_id_registry.py`.
5. Re-run affected batch (e.g. E5):
   ```bash
   EXTRA_EXTRACT_FLAGS="--rerun-only-refusals" \
     LIA_EXTRACT_WORKERS=8 LLM_DEEPSEEK_RPM=240 \
     bash scripts/canonicalizer/launch_batch.sh --batch E5 \
       --allow-rerun --skip-post --skip-pre
   ```

---

## 4. Parallel-agent friendly tasks

The architecture lets some work parallelize cleanly across forks /
sub-agents because they don't compete for local resources:

| Task | Why parallel works |
|---|---|
| P2 DIAN probe (F2 angle) | Pure investigation — fetches DIAN site, no local writes. |
| P2 DIAN probe (G1 angle) | Same; can run alongside F2 probe. |
| P3a Función Pública CCo probe | Same shape. |
| P7 SUIN doc-id discovery for missing docs | Same — manually browse SUIN to find the right `id=<NUMERIC>`. |
| Documentation tasks | Always parallelizable. |
| Per-norm-batch eval / spot-check | Read-only work against `evals/vigencia_extraction_v1/`. |

**Tasks that should NOT parallelize (resource conflicts):**

| Task | Why serial |
|---|---|
| Cascade extract runs (P6) | Multiple processes share `var/scraper_cache.db` + project-wide LLM throttle; thrashing is real (see v6 cascade meltdown post-mortem). |
| Cloud writes (P1) | Idempotent UPSERT but parallel writes against the same `norm_id` create lock contention. |
| Falkor sync (P5) | Single-writer pattern. |

---

## 5. Operational quick reference

**Activate cloud env:**
```bash
set -a; . .env.staging; set +a
```

**Activate local env:**
```bash
set -a; . .env.local; set +a
```

**Health check:**
```bash
docker ps --format '{{.Names}}' | grep -E "supabase_db_lia-graph|lia-graph-falkor-dev"
PYTHONPATH=src:. uv run python -c "
from lia_graph.llm_runtime import resolve_llm_adapter
a, i = resolve_llm_adapter()
print(f'{i[\"selected_provider\"]} ({i[\"adapter_class\"]}, {i[\"model\"]})')"
# Expected: deepseek-v4-pro
```

**Run a single norm canary** (sanity check pipeline before any cascade):
```bash
echo '{"norm_id": "decreto.1625.2016.art.1.1.1"}' > /tmp/canary.jsonl
LIA_LIVE_SCRAPER_TESTS=1 LLM_DEEPSEEK_RPM=240 \
PYTHONPATH=src:. uv run python scripts/canonicalizer/extract_vigencia.py \
    --input-set /tmp/canary.jsonl \
    --output-dir /tmp/canary_out \
    --run-id smoke-$(date +%s) \
    --allow-rerun --workers 1
```

**Inspect a batch's outcome:**
```bash
PYTHONPATH=src:. uv run python -c "
import json, glob
ok = ref = 0
for p in sorted(glob.glob('evals/vigencia_extraction_v1/<BATCH>/*.json')):
    d = json.loads(open(p).read())
    if d.get('result',{}).get('veredicto') is not None: ok += 1
    else: ref += 1
print(f'{ok} successes + {ref} refusals = {ok+ref}')"
```

---

## 6. File index — where to look

| Concern | File |
|---|---|
| This forward plan | `docs/re-engineer/next_v7.md` (you are here) |
| v6 plan + lessons | `docs/re-engineer/fixplan_v6.md` |
| v6 cascade ledger | `docs/re-engineer/state_fixplan_v6.md` §10 |
| v6 engineering learnings | `docs/learnings/canonicalizer/v6_suin_first_rewire_2026-04-28.md` |
| Per-source fetch playbook | `docs/learnings/sites/per-source-fetch-playbook.md` |
| Per-site operational notes | `docs/learnings/sites/<source>.md` |
| Vigencia harness | `src/lia_graph/vigencia_extractor.py` |
| Active scrapers | `src/lia_graph/scrapers/{suin_juriscol,secretaria_senado,funcion_publica,dian_normograma,corte_constitucional,consejo_estado}.py` |
| Registry build scripts | `scripts/canonicalizer/build_{suin_doc_id,funcionpublica}_registry.py` |
| Cascade driver | `scripts/canonicalizer/run_cascade_v5.sh` |
| Per-batch launcher | `scripts/canonicalizer/launch_batch.sh` |
| Per-norm extract driver | `scripts/canonicalizer/extract_vigencia.py` |
| Cloud ingest | `scripts/canonicalizer/ingest_vigencia_veredictos.py` |
| Falkor sync | `scripts/canonicalizer/sync_vigencia_to_falkor.py` |
| Embedding backfill | `src/lia_graph/embedding_ops.py` |
| Throttle | `src/lia_graph/gemini_throttle.py` (legacy module name; provider-agnostic) |
| LLM provider config | `config/llm_runtime.json` |
| Cache (SQLite, WAL) | `var/scraper_cache.db` |
| SUIN cache (HTML) | `cache/suin/` (3,387 files) |

---

## 7. Decision history

* fixplan_v6 closed because SUIN-first delivered 92.4% pass rate
  across 14 batches with 0 errors. The only meaningful gap is K3
  (CCo coverage), which is a Senado anchor-slicing depth issue, not
  a SUIN problem.
* v6.1 Función Pública added because it's the cheapest 6th-source
  candidate (per-article anchors are cleaner than SUIN), but it
  doesn't close F2/G1 — those need DIAN-specific sourcing.
* The cloud promotion was deferred during the autonomous cascade run
  to keep all writes local until the cascade fully closed; it's now
  the highest priority because served retrieval needs the new
  vigencias.

**Operator preferences captured during v6 (apply going forward):**

* No money quoted in status reports — name action + effort + what it
  unblocks (memory: `feedback_no_money_quoting`).
* Always suggest what's next at end of every status (memory:
  `feedback_always_suggest_next`).
* Don't lower aspirational thresholds (memory:
  `feedback_thresholds_no_lower`).
* Display all times in Bogotá AM/PM (memory:
  `feedback_time_format_bogota`).
* Plain-language, boss-level communication; engineering depth only
  when explicitly asked (memory:
  `feedback_plain_language_communication`).

---

*Drafted 2026-04-29 AM Bogotá by claude-opus-4-7 immediately after the
v6 cascade fully closed (E1a long tail done at 528/546). All v6 +
v6.1 commits pushed to origin/main. Ready for the next agent.*
