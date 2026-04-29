# Foundational primary-source sites — operational notes

Lia Graph's vigencia harness requires **two primary sources per norm**
(per `docs/re-engineer/fixplan_v3.md` §0.11.3 — quality contract). The
foundational sources are five Colombian government sites:

| Source | Coverage | Per-site doc |
|---|---|---|
| `secretariasenado.gov.co` | Leyes (incluye ET), modification notes per artículo | [secretariasenado.md](secretariasenado.md) |
| `normograma.dian.gov.co` | Decretos tributarios, resoluciones DIAN, conceptos DIAN, full ET as one page | [normograma-dian.md](normograma-dian.md) |
| `www.suin-juriscol.gov.co` | Toda la legislación nacional con histórico (cross-check second source) | [suin-juriscol.md](suin-juriscol.md) |
| `www.corteconstitucional.gov.co` | Sentencias CC, autos CC | [corte-constitucional.md](corte-constitucional.md) |
| `www.consejodeestado.gov.co` | Sentencias CE, autos CE | [consejo-de-estado.md](consejo-de-estado.md) |
| `www.funcionpublica.gov.co` | Decretos Únicos Reglamentarios (DUR backup), some leyes — added v6.1 | [funcion-publica.md](funcion-publica.md) |

**Cross-cutting fetch playbook:** [`per-source-fetch-playbook.md`](per-source-fetch-playbook.md) — how to add a new scraper, how to refresh the corpus when Colombian law shifts, common failure modes per source. Read this first when extending the scraper layer.

Each per-site doc captures: URL patterns we use, known quirks (timeouts,
SSL, rate limits, site-specific HTML shapes), and the recovery playbooks
when they break.

## Cross-cutting patterns

These apply to every scraper in `src/lia_graph/scrapers/`:

### 1. Browser-shaped User-Agent
gov.co sites occasionally rate-limit or 403 bare scraper UAs. We send
a Chrome-on-Mac shape that also names ourselves transparently:

```
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
(KHTML, like Gecko) Chrome/120.0 Safari/537.36 Lia-Graph/1.0
(compliance scraper)
```

We also send `Accept-Language: es-CO,es;q=0.9,en;q=0.8` since some
sites serve different content based on locale.

### 2. SSL trust via certifi
macOS Python sometimes ships an OS-default OpenSSL bundle that doesn't
trust Sectigo's intermediate CAs (used by SUIN-Juriscol et al). We
prefer the `certifi`-bundled CA list when the package is installed,
falling back to `ssl.create_default_context()` only if certifi is
missing. The fallback emits an INFO log once so the operator knows.

### 3. Retries with backoff
Three attempts at 0 s / 2 s / 6 s back-off. Triggered by:
- `TimeoutError` / `URLError` / `OSError` — transient.
- HTTP 5xx — site temporarily overloaded.

4xx is terminal — the URL is wrong; do not retry.

### 4. Rate limiting
Per-scraper `rate_limit_seconds` (default 0.5 s, SUIN at 1.0 s). The
scraper enforces a minimum gap between fetches to be polite to small
government infrastructure.

### 5. Live-fetch gate
`LIA_LIVE_SCRAPER_TESTS=1` in env enables real HTTP. Without it,
scrapers only return cache hits. The canonicalizer launcher
(`scripts/canonicalizer/launch_batch.sh`) sets this for every batch.

## When a foundational site is unreachable

1. **Check `docs/learnings/sites/<site>.md`** for the current operational
   state and known workarounds.
2. **Try alternate access**: HTTP vs HTTPS, with and without `www.`,
   different port. The site doc records what we've tested.
3. **Bypass briefly**: if one site is down for hours, the harness will
   refuse all norms it backs (since we need *two* sources). The
   canonicalizer doc's stop-condition (`refusal rate > 25%`) catches
   this — pause and resume when the site returns.
4. **Update the per-site doc** with the new finding so the next person
   doesn't start from zero.

The five-site set is intentionally redundant: every norm_id has at
least two sites that claim coverage, so a single-site outage degrades
gracefully rather than blocking the whole pipeline.
