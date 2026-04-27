# consejodeestado.gov.co — operational notes

**Site:** https://www.consejodeestado.gov.co/
**Coverage:** Sentencias CE (Sala de lo Contencioso Administrativo),
autos de suspensión provisional, sentencias de unificación
(Sala Cuarta — tributario).
**Scraper:** `src/lia_graph/scrapers/consejo_estado.py`

## Known operational facts (as of 2026-04-27)

### 1. HTTPS works; cert validates with certifi
Reachable, ~0.4 s typical.

### 2. Resource layout
The CE site is a more conventional CMS than Senado. URLs are
search-driven (`/buscador/...?radicado=<NUM>`); the scraper resolves
norm_ids in the shape `sentencia.ce.<SECCION>.<RADICADO>` and
`auto.ce.<RADICADO>.<DATE>` to those search URLs.

### 3. Sentencias de Unificación are critical
For the DT (derogación tácita) state with a "Sentencia de Unificación
2022CE-SUJ-4-002" shape source, the scraper has a special case to
hit the unification index page directly rather than the per-sentencia
URL — those URLs are flaky.

### 4. Polite rate limit at 1.0 s
CE is a smaller infra than CC; we go slower out of politeness.

## Recovery playbooks

### "Search URL returns 0 hits"
The site's search is sensitive to the exact radicado format
(spaces vs dashes, year-leading vs year-trailing). The scraper
normalizes to the most-common shape; if a specific norm_id keeps
missing, try variant formats by hand and add to the resolver.

### "Captcha appears"
CE doesn't currently rate-limit aggressively in our experience, but
we've seen one production captcha-on-search incident. If it returns,
implement the captcha-bypass via the operator-supplied token (CE will
issue one for compliance research) — do NOT solve programmatically.
