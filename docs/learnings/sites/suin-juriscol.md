# suin-juriscol.gov.co — operational notes

**Site:** https://www.suin-juriscol.gov.co/
**Coverage:** DUR-1625 (tributario), DUR-1072 (laboral), CST consolidado,
Ley 100/1993, ET (decreto 624/1989), recent leyes (2277/2381/2466).
Per-article HTML with anchor-based slicing.
**Scraper:** `src/lia_graph/scrapers/suin_juriscol.py`
**Status:** **PRIMARY source** (chain position 1) since fixplan_v6
(2026-04-28). Slices DUR articles with 96-98% LLM pass-rate.

## fixplan_v6 cascade evidence (2026-04-28 PM)

| Wave | Batches | Successes | Pass rate |
|---|---|---|---|
| Wave 1 (DUR-1625) | E1a/E1b/E1d/E2a/E2c/E3b | 1406 | **96.8%** |
| Wave 2 CST (J1-J4) | J1+J2+J3+J4 | 131 | **100%** |
| Wave 3 (DUR-1072) | E6b/E6c/J8b | 737 | **97.7%** |
| Wave 2 CCo (K3) | K3 | 158 | 50% — see "K3 CCo gap" below |

Total Postgres rows landed: **+1236** (783 → 2019) over ~3 hours,
0 errors across 14 batches. See
`docs/learnings/canonicalizer/v6_suin_first_rewire_2026-04-28.md` for
the engineering arc that got us here.

## Known operational facts (as of 2026-04-28 cascade close)

### 1. Cert is valid; Python's default trust store is the problem
The site's TLS cert is issued by **Sectigo Public Server Authentication
CA EV R36** for `www.suin-juriscol.gov.co` (gov entity, valid Nov 2025
to Dec 2026). This chain is correct in the public Web PKI.

The failure pattern we hit was:
```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate
verify failed: unable to get local issuer certificate (_ssl.c:1006)
```
That's Python on macOS using a default OpenSSL bundle that doesn't ship
the Sectigo intermediate. The fix is to use **certifi**'s maintained CA
bundle:
```python
import ssl, certifi
ctx = ssl.create_default_context(cafile=certifi.where())
urlopen(req, timeout=30, context=ctx)
```
This is implemented in `src/lia_graph/scrapers/base.py::_ssl_context_with_certifi`
and applied to every HTTPS fetch automatically.

### 2. SUIN URL resolution — registry-driven (v6)
SUIN is **id-keyed** — every doc has an opaque numeric id (e.g.
`viewDocument.asp?id=30030361` for DUR-1625). We resolve canonical
norm_ids via `var/suin_doc_id_registry.json`, built by
`scripts/canonicalizer/build_suin_doc_id_registry.py` from the
harvested `artifacts/suin/*/documents.jsonl`. The registry maps
`{decreto.1625.2016 → suin_doc_id 30030361 + URL}`, etc.

Currently 10 entries: 9 SUIN spine docs + `et` alias to decreto 624/1989.
Adding more docs to SUIN coverage = re-harvest + re-build registry.

Article-scoped norms (`decreto.1625.2016.art.1.6.1.1.10`) resolve
through their parent doc URL. The scraper slices the parent's HTML at
fetch time and returns just the article body.

### 3. Three-tier cache strategy (v6)
On `fetch(norm_id)`:
1. **var/scraper_cache.db** (SQLite, process-shared) — primary cache.
2. **cache/suin/<sha1>.html** — 3,387 pre-harvested HTML files on disk.
3. **Live HTTP via SuinFetcher** — only when `live_fetch=True`.

On (2) and (3), the scraper parses the HTML once and stores the per-
article slice dict in `parsed_meta["articles"]`. Subsequent calls
across **any process** read the slice dict from SQLite — no re-parse.
This is the Option-2 persisted slice cache shipped in commit `92c5661`.
**~38× speedup on warm-instance fetches.**

### 4. Per-article slicing via parse_document
The harvester's parser (`src/lia_graph/ingestion/suin/parser.py`)
identifies article boundaries by `<a name="ver_<n>">` anchors and
extracts each article's body via `<div class="articulo_normal">`.

**fixplan_v6 regex fix (commit `9940faf`):** `_ARTICLE_HEADING_RE`
was `\d+(?:[-.]\d+)?` (one optional `[-.]\d+` group), which silently
truncated DUR multi-segment numbers like `1.6.1.1.10` to `1-1`. Fixed
to `\d+(?:[-.]\d+)*` — multi-segment captures supported. Real-corpus
regression test in
`tests/test_suin_juriscol_scraper.py::test_real_dur_article_slice`.

### 5. Memory profile (DUR-1625 reference)
| Stage | RSS |
|---|---|
| Python baseline | 21 MB |
| + lia_graph imports | 47 MB |
| + read 17 MB HTML | 127 MB |
| + parse_document (peak transient) | **308 MB** |
| Steady state with slice dict | ~110 MB |
| Persisted slice dict in SQLite | **3.2 MB** |

Worker count guidance:
* **First parse is the expensive one** — 308 MB transient peak.
* After the slice cache is populated in SQLite, parallel processes
  read it for ~50 MB each.
* Don't fan out 168 workers across 7 processes simultaneously
  (catastrophic memory thrash — see v6 meltdown post-mortem).
* Sweet spot for one parent doc at a time: workers=4-8 per batch,
  multiple batches in parallel after the first batch primes SQLite.

### 6. K3 CCo gap (cascade evidence)
K3 (Wave 2 CCo articles) hit only 30% pass rate. Diagnostic:
**all 157 refusals had `single_source_accepted='secretaria_senado'`**
— SUIN didn't even resolve a URL for them (they're in the
`cco.art.<N>` namespace and CCo is in our SUIN registry, but SUIN's
CCo harvest may be incomplete OR the per-article slicer misses CCo
numbering schemes). Senado returned content for all 157, but the
LLM said `INSUFFICIENT_PRIMARY_SOURCES` — implying the Senado slice
is too thin for vigencia determination.

**This is NOT a v6 bug** — it's a corpus coverage gap. Either:
1. Re-harvest CCo segments from SUIN that aren't currently in
   `cache/suin/`. Sample the missing article numbers first.
2. Improve Senado's CCo segment-index (currently uses a coarse range
   table; high-numbered articles may fall back to the master page,
   where anchor-slicing pulls a fragment too small to be informative).
3. Wire Función Pública gestor normativo as a 6th scraper —
   verified to host CCo with cleaner anchors.

Tracked as v7 candidate. The Wave 1+3 DUR pass rates (96-98%) prove
the SUIN slicer architecture is sound; K3 is specifically a CCo
coverage problem.

### 7. Polite rate limit at 1.0 s
SUIN is the most conservative of the five primary sources — slower
TCP responses, heavier HTML. Default 1 req/sec.

## Recovery playbooks

### "CERTIFICATE_VERIFY_FAILED"
Should not happen with the certifi context, but if it does:
1. Confirm `certifi` is installed: `uv pip show certifi`.
2. If installed but still failing, the site may have rotated to a CA
   not yet in certifi's bundle. Run `uv pip install --upgrade certifi`
   and re-test.
3. If the site is using a self-signed dev cert temporarily, do NOT
   bypass verification — file a ticket; the canonicalizer's quality
   contract requires a verifiable chain.

### "SUIN times out / 503"
The site occasionally serves errors during business-hour peak. Our
retry path (0/2/6 s back-off) usually wins. If sustained, pause the
canonicalizer and resume during off-peak (Bogotá night).

### "I want SUIN as a real second source"
Project work — see `docs/re-engineer/fixplan_v3.md` §0.11.3 backlog.
Until that ships, leverage Senado + DIAN normograma for ET, and
Senado + SUIN-by-id for `ley.*` once SUIN id-resolution lands.
