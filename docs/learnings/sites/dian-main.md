# dian.gov.co/normatividad/Normatividad/*.pdf — operational notes

**Site:** https://www.dian.gov.co/
**Coverage:** modern DIAN resoluciones (2020+) published as PDF files
under the predictable path `/normatividad/Normatividad/Resolución <NNNNNN> de <DD-MM-YYYY>.pdf`.
Closes the **F2 gap** (`res.dian.13.2021.art.*` and similar) that
SUIN, Senado, Función Pública, and DIAN normograma cannot serve.
**NOT** a source for DIAN conceptos (G1 gap remains open after this
scraper — pre-2020 conceptos predate the modern PDF layout).
**Scraper:** `src/lia_graph/scrapers/dian_pdf.py`
**Status:** **7th primary source** (chain position 5 — after DIAN
normograma, before the jurisprudence sources) since next_v7 P2
(2026-04-29).

## Why we added this source (next_v7 context)

The fixplan_v6 cascade closed at 92.4% pass rate but left **F2**
(81 res.dian.13.2021.art.* refusals) and **G1** (407
concepto.dian.0001.2003 norms) unresolved. None of the prior 6
scrapers host those documents:

* **SUIN-Juriscol** — does not host DIAN-specific resoluciones or conceptos.
* **Secretaría Senado** — only carries leyes / códigos.
* **Función Pública** — covers DURs, not DIAN-specific resoluciones or conceptos.
* **DIAN normograma** — the LLM cannot slice the 3 MB master pages reliably (the original cascade-meltdown root cause that v6 SUIN-first solved).
* **Corte Constitucional / Consejo de Estado** — sentencias only.

The next_v7 §3.6 probe verified that DIAN's main site publishes
resoluciones at a stable, predictable URL pattern with PDF content
that pypdf can extract cleanly. **F2 closes via this scraper. G1
stays open** (probed; pre-2020 conceptos return 404 on the same
path; will need either a Doctrina-archive scraper or operator-
delivered SME veredictos, see next_v7 §3.6 step 2c).

## Known operational facts

### 1. URL pattern + raw spaces
Hrefs in the source HTML look like::

    /normatividad/Normatividad/Resolución 000013 de 11-02-2021.pdf

Notes that bite:
* The filename uses literal `Resolución` (with the actual `ó`
  character, not %C3%B3-encoded) on the page, but %20-encoded spaces
  inside the href.
* `urllib.request.Request` rejects raw spaces in URLs with
  `URL can't contain control characters`. The scraper's `_http_get`
  applies `urllib.parse.quote(parsed.path, safe="/")` before the
  request — preserves the scheme/netloc, encodes only the path.
* Number portion has leading zeros (5 or 6 digits): `000013`,
  `00063`, etc. Canonical norm_id is `res.dian.<int(NUM)>.<YEAR>`
  (e.g. `res.dian.13.2021`).
* Date suffix `DD-MM-YYYY` cannot be reconstructed from the canonical
  id alone — registry is mandatory.

### 2. Cert chain — truststore optional
DIAN's cert chain is well-formed; certifi works in most environments.
The scraper still routes through `truststore` first (when installed)
to delegate to the OS Keychain — same defense-in-depth pattern as
Función Pública.

### 3. Catalog discovery — landing pages, not search
There's no usable search API. Discovery is by walking
"normativa" landing pages. Each has a list of PDF links matching
the URL pattern above. The registry builder
(`scripts/canonicalizer/build_dian_pdf_registry.py`) extracts those
hrefs with a tolerant regex that accepts space, %20, +, -, _ as
inter-token separators.

The MVP landing page covers Factura Electrónica:

    https://www.dian.gov.co/impuestos/factura-electronica/documentacion/Paginas/normativa.aspx

Adds 7 res.dian.* entries including the F2 target `res.dian.13.2021`.
Operators extend the registry by appending more landing-page URLs to
`build_dian_pdf_registry.py::LANDING_PAGES`.

### 4. PDF parsing — pypdf is sufficient
`pypdf>=4.0` ships text extraction good enough for the article
slicing we need. The scraper uses
`pypdf.PdfReader(io.BytesIO(content))`, joins page text, then
splits on a simple `^ART[IÍ]CULO\s+(\d+)\b` regex (multiline,
case-insensitive). First-occurrence wins on duplicate article
numbers (some PDFs repeat them in footers).

For Resolución 13/2021 (4.27 MB PDF, 39 articles), this produces
clean per-article slices: e.g. Article 5 returns 3157 chars with
intact accents and section headings.

If a future DIAN PDF arrives with a layout pypdf can't slice
(graphic-heavy, scanned image), fall back to **pdfminer.six** —
better for layout-aware extraction. Add the dep + branch in
`_extract_text_from_pdf`.

### 5. Live-fetch gate
The scraper inherits the standard `LIA_LIVE_SCRAPER_TESTS=1` gate
from `Scraper.__init__`. In dev/CI, only the SQLite cache and
fixtures are consulted. Operators issuing one-off fetches must
export the env var before invoking `extract_vigencia.py`.

### 6. Three-tier cache + persisted slice cache
Same pattern as SUIN and Función Pública:
1. SQLite cache (shared `var/scraper_cache.db`) keyed by `(source_id, url)`.
2. In-process LRU on `parsed_meta["articles"]` dict (per-URL).
3. Slice dict persisted in `parsed_meta` so parallel processes share
   it via the SQLite cache (Option-2 pattern from v6 §3.7).

### 7. Trusted-source acceptance
`dian_pdf` joins `_TRUSTED_GOVCO_SOURCE_IDS` so the harness can
accept its veredicto under the single-source `.gov.co` rule when
no second primary source returned content for the same norm.

## Maintenance / extension

### Adding a new landing page (covers more resoluciones)
Edit `scripts/canonicalizer/build_dian_pdf_registry.py::LANDING_PAGES`,
add a `(url, label)` tuple, then::

    PYTHONPATH=src:. uv run python scripts/canonicalizer/build_dian_pdf_registry.py --dry-run
    PYTHONPATH=src:. uv run python scripts/canonicalizer/build_dian_pdf_registry.py

Re-run F2 with `--rerun-only-refusals` (next_v7 §3.6 step 2a item 8)::

    EXTRA_EXTRACT_FLAGS="--rerun-only-refusals" \
    LIA_EXTRACT_WORKERS=8 LLM_DEEPSEEK_RPM=240 LIA_LIVE_SCRAPER_TESTS=1 \
    bash scripts/canonicalizer/launch_batch.sh --batch F2 \
        --allow-rerun --skip-post --skip-pre

### Extending to DIAN doctrina (G1 angle)
The next_v7 §3.6 step 2b path: probe
`https://www.dian.gov.co/normatividad/Doctrina/Paginas/Doctrina-Subdireccion-Direccion.aspx`.
If that page lists pre-2020 concepto PDFs at a similar URL pattern,
extend `LANDING_PAGES` and the canonical-id mapping (currently only
`Resolución` → `res.dian.<num>.<year>`; would need `Concepto` →
`concepto.dian.<num>.<year>` mapping).

### Extending to other resolución kinds
The current scraper handles `res.dian.*` only (`handles()` filters
on prefix). For other emisores (`res.minhacienda.*`, etc.), add a
sibling scraper or generalize the prefix filter — but **only if the
URL pattern is the same**, which it generally is not on those sites.
