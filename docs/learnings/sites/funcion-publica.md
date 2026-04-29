# funcionpublica.gov.co/eva/gestornormativo — operational notes

**Site:** https://www.funcionpublica.gov.co/eva/gestornormativo/
**Coverage:** Decretos Únicos Reglamentarios (DUR-1625, DUR-1072,
+ ~24 other DURs covering all Colombian sectors), some leyes,
some general gobierno conceptos. **NOT** DIAN-specific resoluciones
or DIAN tributario conceptos (those need a different source).
**Scraper:** `src/lia_graph/scrapers/funcion_publica.py`
**Status:** **6th primary source** (chain position 3 — between Senado
and DIAN normograma) since v6.1 (2026-04-29). Backup for DUR docs
when SUIN doesn't cover them or has issues.

## Why we added this source (v6 cascade context)

The fixplan_v6 cascade (2026-04-28) closed at 91.4% pass rate (97%
excluding K3's CCo gap). The remaining gaps were:

* **F2** (81 res.dian refusals) — DIAN-specific resolutions; SUIN
  doesn't host them.
* **G1** (407 norms, concepto.dian.0001.2003) — DIAN concepto;
  SUIN doesn't host it.
* **K3** (157 CCo refusals) — Senado anchor-slicing depth issue.
* **E5** (104 decreto 417/2020 norms) — not in SUIN harvest.

The alt-DB research fork identified Función Pública's gestor
normativo as the cleanest 6th-scraper candidate because its DUR pages
expose `<a name="N.N.N">` anchors with the DUR key directly — even
cleaner than SUIN's `ver_NNN` indirection. **However, post-build
verification showed Función Pública covers DURs but does NOT host
DIAN-specific res.dian or concepto.dian** at the URLs we tested. So
this scraper closes part of the gap (DUR redundancy) but **F2/G1
remain open** for v7+.

The scraper still earns its place because:
1. DUR redundancy — when SUIN is flaky or a DUR isn't in our SUIN
   harvest, Función Pública catches it.
2. Cleaner anchor format than SUIN — `<a name="1.6.1.1.10">` is
   directly usable; no need for the `ver_NNN` → article-number
   lookup that SUIN requires.
3. Future-proofing — additional Función Pública index pages can be
   walked to extend coverage (e.g. leyes index, conceptos marco
   index, etc.).

## Known operational facts

### 1. Cert chain — truststore mandatory
The site uses a Sectigo intermediate that **certifi 2026.02.25 doesn't
include**. Python on macOS reports:

```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED]
certificate verify failed: unable to get local issuer certificate
```

The fix: use **truststore** (delegates verification to the OS Keychain
on macOS, which fetches the missing intermediate via AIA). Same trick
as `src/lia_graph/ingestion/suin/fetcher.py`. Implemented in
`scrapers/funcion_publica.py::_fp_ssl_context` — falls back to
certifi if truststore isn't installed (will likely fail TLS for this
site, treated as "source returned None" by the harness).

### 2. Search endpoint doesn't filter on `?q=`
The URL `https://.../normasfp.php?nivel=400&q=<query>` returns 200
but **always returns the same default 5 docs** regardless of the
query string. Don't use it for discovery.

Use **index pages** instead — categorized landing pages that link to
specific docs by topic. The DUR index at `i=62255` lists all 26 DURs
in order with anchor titles like `Decreto 1625 de 2016`. Build the
registry by walking these pages (see
`scripts/canonicalizer/build_funcionpublica_registry.py`).

### 3. URL resolution — opaque numeric `i=<N>`
Like SUIN, every Función Pública doc has an opaque numeric id. We
maintain `var/funcionpublica_doc_id_registry.json` mapping canonical
norm_ids to those ids:

```json
{
  "decreto.1625.2016": {
    "funcion_publica_doc_id": "83233",
    "ruta": "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=83233",
    "title": "Decreto 1625 de 2016"
  },
  ...
}
```

Build via:
```bash
PYTHONPATH=src:. uv run python scripts/canonicalizer/build_funcionpublica_registry.py
```

26 entries currently. Extend by adding more index pages to the
script's `INDEX_PAGES` constant.

### 4. Anchor-based per-article slicing
Articles use `<a name="N.N.N">` directly (no `ver_NNN` indirection).
The slicer walks those anchors and extracts the body text between
each anchor and the next.

DUR-key shape: `\d+(?:[-.]\d+)*`. Same regex shape we fixed in the
SUIN parser (commit `9940faf`); reused via `normalize_article_key`.

### 5. Three-tier cache + persisted slice cache
* **Tier 1**: `var/scraper_cache.db` (SQLite) — process-shared.
* **Tier 2**: live HTTP via certifi/truststore — only when
  `live_fetch=True`.
* No on-disk file cache like SUIN's `cache/suin/<sha1>.html` — we
  rely on the SQLite cache being warm before the cascade runs.

Slice dicts persisted in `parsed_meta["articles"]` so parallel
processes share parses (same Option-2 pattern as SUIN, commit
`92c5661`).

### 6. Polite rate limit at 1.0 s
Función Pública is small infrastructure. Default 1 req/sec.
Single-norm fetch wall: ~2-5 seconds (HTTP RTT + slice extract).

### 7. Document size — DUR-1625 example
Same 17 MB shape as SUIN's DUR-1625 page (different HTML markup but
similar content). Memory profile should match SUIN's:
* Read 17 MB HTML: +~80 MB RSS
* Parse anchors via regex (lighter than BeautifulSoup): peak ~150 MB
* Persisted slice dict: ~3 MB JSON in SQLite

Lighter than SUIN's BeautifulSoup parse because the anchor-extraction
is a single regex pass. Worker count guidance: same as SUIN —
`workers=4-8` per batch is the sweet spot.

## Recovery playbooks

### "CERTIFICATE_VERIFY_FAILED"
1. Check `truststore` is installed: `uv pip show truststore`.
2. If missing: `uv pip install truststore`.
3. If installed but still failing: the site may have rotated certs.
   Check via `curl --cacert <chain>.pem <url>`. If curl works but
   Python doesn't, file a ticket — don't bypass verification.

### "Función Pública returns None for every fetch"
1. Check `var/funcionpublica_doc_id_registry.json` exists and has
   entries:
   ```bash
   python3 -c "import json; print(len(json.load(open('var/funcionpublica_doc_id_registry.json'))))"
   ```
2. If 0 or missing: rebuild via
   `scripts/canonicalizer/build_funcionpublica_registry.py`.
3. If the canonical norm_id you expect isn't in the registry: the
   doc isn't in any index page we walk yet. Add the index page that
   contains it to `INDEX_PAGES` in the build script.

### "Slicer returns empty body for an article"
1. Verify the article key shape matches — DUR `1.1.1` should pass
   through `normalize_article_key` to `1-1-1`.
2. Inspect the cached HTML for the `<a name="1.1.1">` anchor:
   ```bash
   sqlite3 var/scraper_cache.db "SELECT length(content) FROM scraper_cache WHERE source='funcion_publica' AND url LIKE '%i=83233%'"
   ```
3. If the anchor is present but the slicer returns empty, the body
   may be in a non-standard structure (table, nested div). File a
   ticket; the slicer is a single regex pass and may need refinement.

### "I want to add a new Función Pública index page"
1. Find the index page's `i=<N>` parameter (browse the site).
2. Add `(<N>, "Description")` to `INDEX_PAGES` in
   `scripts/canonicalizer/build_funcionpublica_registry.py`.
3. Re-run the build script.
4. Verify with `python3 -c "import json; reg = json.load(open('var/funcionpublica_doc_id_registry.json')); print(len(reg))"`.

## Coverage gaps the scraper does NOT close

* **F2** (`res.dian.13.2021.art.*`) — Función Pública doesn't host
  DIAN-specific resoluciones at predictable URLs.
* **G1** (`concepto.dian.0001.2003`) — Función Pública's "Conceptos
  marco" index is for general gobierno conceptos, not DIAN tributario.
* **E5** (`decreto.417.2020.*`) — COVID decretos may be at FP but
  not in our walked indexes; needs a probe.

For these, see [`per-source-fetch-playbook.md`](per-source-fetch-playbook.md)
"Refresh playbook" or extend the SUIN harvest (v7).
