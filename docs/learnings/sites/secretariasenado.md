# secretariasenado.gov.co — operational notes

**Site:** http://www.secretariasenado.gov.co/senado/basedoc/
**Coverage:** Leyes, ET (segmented), modification notes per artículo.
**Scraper:** `src/lia_graph/scrapers/secretaria_senado.py`
**Index file:** `var/senado_et_pr_index.json`
**Index builder:** `scripts/canonicalizer/build_senado_et_index.py`

## Known operational facts (as of 2026-04-27)

### 1. Use HTTP, not HTTPS
HTTPS port 443 is **persistently unreachable** from at least some networks
(macOS over typical residential / corp VPN here). TCP connect to :443
times out every time. HTTP port 80 works and the site serves the same
content there — *the site does not redirect HTTP → HTTPS*, so we use
plain HTTP without warning the user.

The scraper's `_BASE_URL` is therefore `http://...`, not `https://`.

If your environment can reach :443 fine, plain HTTP still works — there
is no benefit to flipping back to HTTPS for these public Diario Oficial
documents that are signed externally anyway.

### 2. ET is segmented across `_pr001..pr035` files
The Estatuto Tributario is split into ~36 segment HTML pages named
`estatuto_tributario_pr001.html` through `estatuto_tributario_pr035.html`,
each holding ~20-30 articles. There is also `estatuto_tributario.html`
(the table of contents — used for `norm_id == "et"` only).

The article-number → segment mapping is **NOT** a clean numeric formula.
For example:
- pr011 covers articles 261..285
- pr012 covers articles 299..306 (so 286..298 are missing or in a
  different page we haven't found)
- pr023 covers 551..573 (Art. 555 lives here)
- pr028 covers 674..696 (Art. 689-3 lives here)

We ship `var/senado_et_pr_index.json` — a precomputed lookup the scraper
loads at import. Rebuild with:
```
PYTHONPATH=src:. uv run python scripts/canonicalizer/build_senado_et_index.py
```
The build sweeps pr000..pr129 (stops after 5 consecutive 404s), parses
out `ARTÍCULO N(-S)?` mentions, and writes the article → segment map.

### 3. URL path: NO `/codigo/` segment
The correct path is `/senado/basedoc/estatuto_tributario_prNNN.html`
(direct under `basedoc/`). Earlier scraper versions used
`/senado/basedoc/codigo/estatuto_tributario_prNNN.html` — that path
404s.

### 4. Sub-units share the parent article's segment
`et.art.689-3` and `et.art.689-1` both live in the same pr-page as
`et.art.689` (segment pr028). The scraper:
1. Looks up the full sub-unit id ("689-3") in the index — covers cases
   where the index builder enumerated the sub-unit explicitly.
2. Falls back to the integer base ("689") if the sub-unit isn't there.

If a brand-new reform introduced an article like `689-7` that the index
doesn't enumerate yet, the parent fallback still serves the right page.

### 5. Polite rate limit
0.5 s between fetches. The site is small infrastructure; sustained
hammering produces sporadic 5xx that retry handles, but politeness is
the right default.

### 6. CCo (Código de Comercio) anchor-slicing depth gap (v6 cascade)
Wave 2 K3 batch (CCo articles) closed at 50% pass rate. Diagnostic
finding: **all 157 refusals had `single_source_accepted='secretaria_senado'`
but the LLM returned `INSUFFICIENT_PRIMARY_SOURCES`** — i.e. Senado
returned content for the article number but the slice was too thin
for the LLM to determine vigencia.

Root cause hypothesis: the CCo segment-index in `_CST_PR_SEGMENT_BOUNDS`-
style coarse range table doesn't exist for CCo (we don't yet ship
`var/senado_cco_pr_index.json`). Higher-numbered CCo articles fall back
to the master `codigo_comercio.html` page, where the anchor-slicer
(`_slice_article_senado`) finds the article anchor but pulls a fragment
that may be too small (article body cut off by the next `[[ART:N]]`
marker too early, OR the master page doesn't include the full body).

Three remediation paths (v7 candidates):
1. **Build a CCo pr-segment index** (mirror `build_senado_et_index.py`)
   so per-article URLs resolve to the right `codigo_comercio_pr<seg>.html`
   segment, where slicing has more context.
2. **Improve the master-page slicer** to include the full body between
   anchors instead of truncating at the next anchor only.
3. **Wire Función Pública gestor normativo** as a 6th scraper — verified
   to host CCo with cleaner anchors. This is the cheapest path because
   it reuses the SUIN scraper architecture.

Tracked in `docs/re-engineer/state_fixplan_v6.md` §10 closure entry.

## URL patterns used by the scraper

| `norm_id` shape | URL |
|---|---|
| `et` | `…/basedoc/estatuto_tributario.html` |
| `et.art.<N>(-<S>)?` | `…/basedoc/estatuto_tributario_pr<seg>.html` (seg from index) |
| `ley.<NUM>.<YEAR>` | `…/basedoc/ley_<NUM>_<YEAR>.html` |

(Sub-units of `et.art.<N>` like `et.art.<N>.num.<M>` strip the trailing
sub-unit and resolve to the article's URL.)

## Recovery playbooks

### "All ET fetches return None"
1. Check `var/senado_et_pr_index.json` exists and is non-empty.
2. If missing: `uv run python scripts/canonicalizer/build_senado_et_index.py`.
3. If exists but the article you're after isn't in it: rebuild — Senado
   may have added a segment.

### "TCP timeout to www.secretariasenado.gov.co:80"
The site itself is down. Pause the canonicalizer; the
`refusal rate > 25%` stop-condition will trigger anyway.

### "302 redirect to https://"
Re-test:
```
curl -sS -A "Mozilla/5.0" -I http://www.secretariasenado.gov.co/senado/basedoc/estatuto_tributario.html
```
If they've finally switched to forced-HTTPS, flip `_BASE_URL` to
`https://` and resolve the underlying :443 reachability problem (likely
a network policy issue on your side).
