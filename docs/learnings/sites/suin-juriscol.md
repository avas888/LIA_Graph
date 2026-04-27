# suin-juriscol.gov.co — operational notes

**Site:** https://www.suin-juriscol.gov.co/
**Coverage:** Toda la legislación nacional con histórico (cross-check second source).
**Scraper:** `src/lia_graph/scrapers/suin_juriscol.py`

## Known operational facts (as of 2026-04-27)

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

### 2. SUIN URL resolution is currently a placeholder
The scraper's `_resolve_url` returns `None` for ET articles and only
emits a stub `?canonical=<norm_id>` URL for `ley.*` and `decreto.*`.
SUIN's real URL format is **id-keyed** — every doc has an opaque
numeric id (e.g. `viewDocument.asp?ruta=Leyes/123` or
`/Codigos/CST/<docid>.htm`), not a norm-keyed path. To make SUIN a
functional second source we'd need to:
1. Hit SUIN's search RPC (returns JSON with the doc's id).
2. Cache `norm_id → doc_id` in a sidecar table.
3. Then resolve `viewDocument.asp?codigoComp=<doc_id>`.

This is a planned improvement (`fixplan_v3` §0.11.3 second-source
expansion). Until then, **SUIN does NOT contribute to the two-source
quote** for ET articles — that role is filled by DIAN normograma's
full-ET page.

### 3. Polite rate limit at 1.0 s
SUIN is the most conservative of the five — slower TCP responses,
heavier HTML. We default to 1 req/sec.

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
