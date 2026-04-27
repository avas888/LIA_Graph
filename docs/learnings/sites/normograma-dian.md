# normograma.dian.gov.co — operational notes

**Site:** https://normograma.dian.gov.co/dian/compilacion/docs/
**Coverage:** Decretos tributarios, resoluciones DIAN, conceptos DIAN, **and the full ET as one page** (used as the second primary source for any `et.*` norm_id).
**Scraper:** `src/lia_graph/scrapers/dian_normograma.py`

## Known operational facts (as of 2026-04-27)

### 1. HTTPS works fine
Port 443 reachable, certificate validates with the certifi CA bundle.

### 2. The full ET lives at one URL
DIAN normograma hosts the **entire Estatuto Tributario as one ~3.9 MB HTML page**:
```
https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm
```
We use this as the second primary source for every `et.*` norm_id —
the scraper resolves both `et` and `et.art.*` (and any sub-unit) to
this single URL, and Gemini does article-level extraction in the prompt.
This makes the cache hit rate effectively 100% after the first fetch
(every ET norm shares the same blob).

This is intentional and architecturally sound: pairing **Senado's
article-page** (article-scoped HTML) with **DIAN's full-ET dump**
(complete-document text) gives Gemini two independently-shaped views,
which improves its disambiguation when `Notas de Vigencia` panels
disagree.

### 3. URL patterns
| `norm_id` shape | URL |
|---|---|
| `et`, `et.*` | `…/docs/estatuto_tributario.htm` (always; full ET) |
| `decreto.<NUM>.<YEAR>` | `…/docs/decreto_<NUM>_<YEAR>.htm` |
| `decreto.<NUM>.<YEAR>.art.<A>` | same as parent decreto |
| `res.dian.<NUM>.<YEAR>` | `…/docs/resolucion_dian_<NUM>_<YEAR>.htm` |
| `concepto.dian.<NUM>` | `…/docs/concepto_dian_<NUM>.htm` |

### 4. `Notas de Vigencia` panel
The scraper extracts the modification-notes panel into
`parsed_meta["vigencia_notes"]`. This is one of the highest-signal
inputs for the vigencia harness — DIAN keeps this panel current when
reforms land.

### 5. Some doc URLs return tiny 404s
The site's 404 page is ~1245 bytes (vs real content ≥ 20 KB). If you
get a 200 response with a small `parsed_text`, suspect a soft-404 page
that returned 200 but no real content. The scraper does not currently
detect this — improvement opportunity.

### 6. Polite rate limit
0.5 s between fetches. DIAN is more robust than Senado's smaller infra;
this is conservative.

## Recovery playbooks

### "decreto_NNN_YYYY.htm 404s"
DIAN's filename convention occasionally varies — older decretos may use
a different prefix (e.g. some use `decreto_legislativo_*` for COVID-era
emergency decrees). Open the relevant DIAN compilation page and copy
the actual filename; update the resolver if a pattern emerges.

### "ET full-page download stalls / partial content"
The 3.9 MB page can be slow on slow links. The 30 s `urlopen` timeout
is generous; if it still times out, the retry path with longer back-off
usually wins on attempt 2 or 3. If you need to truncate, the canonical
sections have stable `<a name="art_N">` anchors — scope the request
with `Range:` headers if the operator approves.
