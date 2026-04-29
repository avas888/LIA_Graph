# v7 next-step recommendations (after fixplan_v6 close)

**As of:** 2026-04-29 AM Bogotá, immediately after the v6 cascade fully
closed (E1a long tail done).

**Postgres state:** 783 → 2362 (+1579 net rows). 92.4% overall pass
rate across 14 v6 batches (97% excluding K3's CCo gap).

**v6 deliverables shipped:** SUIN-Juriscol as primary source, Función
Pública as 6th scraper, per-URL parsed-doc cache, persisted slice
cache (Option-2 SQLite), `LLM_DEEPSEEK_RPM` env var, parser regex fix
for multi-segment DUR keys. Nine learnings logged. Per-source fetch
playbook authored.

This doc lays out what's next, prioritized by leverage.

---

## Priority 1 — Cloud promotion of v6 veredictos (operator gate)

The 1579 new Postgres rows are in **local docker** Supabase. They need
to land in **cloud staging Supabase** for the served retrieval path
to use them. Per memory `feedback_lia_graph_cloud_writes_authorized`,
cloud writes are pre-authorized — operator just needs to confirm SME
signoff is complete.

**Effort:** ~30 min. Replay every batch's veredicto JSONs against
cloud target:

```bash
for batch in F2 D5 E1a E1b E1d E2a E2c E3b J1 J2 J3 J4 K3 E6b E6c J8b; do
  PYTHONPATH=src:. uv run python scripts/canonicalizer/ingest_vigencia_veredictos.py \
    --target production \
    --run-id "v6-cloud-promotion-$(date +%Y%m%dT%H%M%SZ)" \
    --extracted-by ingest@v1 \
    --input-dir "evals/vigencia_extraction_v1/$batch"
done
```

Then sync to cloud Falkor:

```bash
PYTHONPATH=src:. uv run python scripts/canonicalizer/sync_vigencia_to_falkor.py \
    --target production
```

**Unblocks:** the served retrieval path (pipeline_d) sees vigencia
v3 demotion / promotion for the new norms.

**Risk:** moderate — overwriting cloud rows with same norm_ids is
idempotent (UPSERT on norm_id), but operator should verify SME has
spot-checked a sample (Activity 1.7-style).

---

## Priority 2 — F2 + G1 gap closure (DIAN-specific sources)

488 norms still without primary-source coverage:
* **F2** (81 res.dian refusals on factura electrónica resolutions)
* **G1** (407 norms, concepto.dian.0001/2003 unificado IVA)

Función Pública verified to NOT host these at predictable URLs.

**Three paths, in increasing effort:**

### 2a. Probe DIAN main site for per-resolution + per-concepto URLs (~2 hr)
DIAN publishes resolutions on `dian.gov.co/normatividad/...` with PDF
links. Probe whether a stable per-resolution URL exists. If yes, build
a 7th scraper. Likely outcome: PDFs are a single blob; per-article
slicing requires pdf2text + manual anchor logic. Doable but messier
than HTML.

### 2b. Operator-delivered veredictos (manual SME entry) (~varies)
Per the canonicalizer's `outside-expert deliveries` workflow (see
`docs/re-engineer/state_corpus_population.md`), an SME can deliver
veredicto JSONs directly. For 488 norms this is heavy; likely only
done for the highest-traffic concepto (G1's IVA unificado). Consider
expert delivery for G1 only; F2 stays pending.

### 2c. Skip these batches indefinitely (~0 hr)
Mark F2 + G1 as out-of-scope for v7. They represent ~14% of remaining
norms; the product can ship without them by gracefully refusing on
those specific norm_ids.

**Recommendation:** start with 2a probe; if DIAN main site has stable
per-doc URLs, build the scraper (~3-4 hr including tests + docs). If
not, default to 2c and document the gap.

---

## Priority 3 — K3 CCo coverage gap (157 refusals)

Diagnosed in the v6 cascade close: all 157 refusals had
`single_source_accepted='secretaria_senado'` but the LLM said
`INSUFFICIENT_PRIMARY_SOURCES` — Senado's anchor-slicing is too
shallow on higher-numbered CCo articles.

**Three remediation paths:**

### 3a. Build a CCo pr-segment index for Senado (~2 hr)
Mirror `scripts/canonicalizer/build_senado_et_index.py`. Probe
`codigo_comercio_pr<NNN>.html` segments, build
`var/senado_cco_pr_index.json`, update Senado scraper to use it.
Mid-numbered CCo articles route to the right segment instead of
master-page slicing.

### 3b. Improve Senado master-page slicer (~1 hr)
The current `_slice_article_senado` cuts at the next `[[ART:N]]`
marker. For CCo's master page, that boundary may truncate the body
prematurely. Inspect a few K3 refusals' Senado HTML and tune the
slicer.

### 3c. Wire Función Pública for CCo (~1 hr)
Probe whether Función Pública has CCo with `<a name="N">` anchors. If
yes, add to `INDEX_PAGES` in the FP build script. Free win.

**Recommendation:** start with **3c** (cheapest, tests cleanly).
If CCo is on FP, ~150 K3 refusals close. If not, fall back to 3a.

---

## Priority 4 — Embedding backfill for new norms

The 1579 new Postgres rows have `chunk_text_embedding = NULL` per the
squashed migration baseline. The retrieval path needs embeddings.

**Effort:** ~30 min orchestration + 1-2 hr compute.

```bash
PYTHONPATH=src:. uv run python -m lia_graph.embedding_ops \
    --target production \
    --batch-size 100
```

**Unblocks:** semantic retrieval (`hybrid_search` RPC) finds the new
norms; otherwise they'd only surface via lexical search.

---

## Priority 5 — Falkor edge sync verification

Each cli.done batch ran `sync_vigencia_to_falkor.py --target wip`
which mirrors Postgres → local docker Falkor. Cloud Falkor sync is
gated on Priority 1.

**Effort:** ~5 min verification post-promotion.

```bash
docker exec lia-graph-falkor-dev redis-cli -p 6379 \
    GRAPH.QUERY LIA_REGULATORY_GRAPH "MATCH (n:Norm) RETURN count(n)"
```

Compare to Postgres count (2362). They should match within a small
delta (sentencias get nodes too).

---

## Priority 6 — Re-run the v6 refusal set with bigger context

Some refusals (~50-100 norms) may close if the LLM gets MORE source
text. The current prompt caps each source at 16 KB; some K3 / E1a
refusals may have been on articles where the slice was just below
the LLM's context need.

**Effort:** ~1 hr code (add a `--max-source-chars` flag to
extract_vigencia.py) + ~2 hr cascade rerun.

```bash
EXTRA_EXTRACT_FLAGS="--rerun-only-refusals --max-source-chars 32000" \
LIA_EXTRACT_WORKERS=8 LLM_DEEPSEEK_RPM=240 \
nohup bash scripts/canonicalizer/run_cascade_v5.sh \
    > logs/cascade_v6_2_driver.log 2>&1 &
```

**Expected gain:** ~50-80 additional successes (recovery rate ~25-40%
on the boundary refusals).

---

## Priority 7 — SUIN harvest extension (v7 corpus work)

Three known SUIN-coverage gaps:
* `decreto.417.2020` — COVID decretos (E5: 104 norms)
* `concepto.dian.0001.2003` — same as G1
* CCo segments not currently in cache (subset of K3's gap)

**Effort:** ~3-5 hr per scope to extend the SUIN harvester.

```bash
# Add seed URLs to src/lia_graph/ingestion/suin/fetcher.py SEED_URLS
# Then re-harvest:
PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest --scope laboral-tributario
```

**Risk:** re-harvesting may rotate cache file hashes (since URL set
expands). Existing `cache/suin/` files stay valid; just adds new ones.

---

## Lower-priority backlog

* **Outside-expert deliveries 13/14/15** — operator timing.
* **Cosmetic heartbeat Bogotá date format** — fixplan_v4 §5.5.
* **CC + CE live-fetch SPA** — fixture-only path is in place; live
  scraping needs Selenium/playwright. fixplan_v5 §3 #2.
* **Phase A/B/C JSON regeneration** — needed only for staging
  promotion at corpus level (not for vigencia).

---

## Recommended sequence (start here)

| Order | Priority | Action | Effort | Why this slot |
|---:|---|---|---|---|
| 1 | P1 | Cloud-promote 1579 v6 veredictos to staging Supabase | 30 min | Foundational — everything downstream needs cloud data; gated only on SME signoff. |
| 2 | P5 | Falkor edge sync verification post-promotion | 5 min | Quick check that cloud Postgres + Falkor stayed in parity after P1. |
| 3 | P4 | Embedding backfill on the 1579 new rows | 30 min + compute | Runs in background after P1; unlocks semantic search on the new vigencias. |
| 4 | P3c | Función Pública probe for CCo coverage | 1 hr | Cheapest K3 gap-close attempt; if FP has CCo, ~150 refusals close for free. |
| 5 | P6 | Refusal rerun with `--max-source-chars 32000` | 3 hr | Recovers ~50-80 boundary refusals where the LLM was just below context need. |
| 6 | P2a | DIAN main site probe for res.dian + concepto.dian | 2 hr | Investigation step before deciding whether to build a 7th scraper for F2/G1. |
| 7 | P7 | SUIN harvest extension (decreto 417/2020, concepto 0001/2003, missing CCo) | 3-5 hr | Last because biggest scope; covers what nothing else does (e.g. E5 COVID decretos). |

After this sequence, the canonicalizer's v6 program is fully
operational on cloud. Remaining gaps (DIAN-specific norms still
inaccessible after P2a, deep CCo coverage if 3c+3a both miss) become
v8 candidates with clear acceptance criteria.

---

*Authored 2026-04-29 AM Bogotá by claude-opus-4-7 immediately after
the v6 cascade fully closed (E1a long tail done at 528/546). All v6
+ v6.1 commits pushed to origin/main.*
