# Per-source fetch playbook — how Lia Graph scrapes each Colombian primary source

**Audience:** engineers who need to update, debug, or extend a scraper
when Colombian law shifts (new reformas, new resolutions, site
redesigns).

**When this matters:** Colombian tax + labor law changes constantly.
The corpus must absorb new norms without breaking the existing
canonicalizer pipeline. This doc captures the per-site fetch + parse +
slice + LLM-instrumentation patterns so a future engineer can patch
one source without re-learning the whole architecture.

**Companion docs (per-site quirks live in those):**
* [`secretariasenado.md`](secretariasenado.md)
* [`normograma-dian.md`](normograma-dian.md)
* [`suin-juriscol.md`](suin-juriscol.md)
* [`corte-constitucional.md`](corte-constitucional.md)
* [`consejo-de-estado.md`](consejo-de-estado.md)

This doc is the **cross-cutting** playbook. The per-site docs are the
**specific** ones.

---

## Common scraper architecture (every source follows this)

Every scraper in `src/lia_graph/scrapers/` extends the base class:

```python
class FooScraper(Scraper):
    source_id: str = "foo"
    rate_limit_seconds: float = 0.5  # or 1.0 for slow sites
    _handled_types = {"ley", "ley_articulo", ...}   # canon norm_types

    def _resolve_url(self, norm_id: str) -> str | None:
        """Map canonical norm_id → primary-source URL. Return None if
        we can't resolve (caller falls through to next scraper)."""

    def _parse_html(self, content: bytes) -> tuple[str, dict[str, Any]]:
        """Extract plaintext + structured metadata. Override fetch()
        if per-article slicing is needed (see SUIN)."""
```

The base class (`src/lia_graph/scrapers/base.py`) handles:
* Live HTTP via `urllib` with certifi-backed SSL + browser UA + retry.
* Cache lookup in `var/scraper_cache.db` (keyed by `(source, url)`).
* `live_fetch=True` gating (default off; tests use cached fixtures).
* Throttling between requests (`rate_limit_seconds`).

The harness (`src/lia_graph/vigencia_extractor.py::VigenciaSkillHarness`)
wraps scrapers in a `ScraperRegistry` and walks them in order on each
norm:

```
SuinJuriscolScraper → SecretariaSenadoScraper → DianNormogramaScraper
  → CorteConstitucionalScraper → ConsejoEstadoScraper
```

(Order set in `vigencia_extractor.py default()` — fixplan_v6.)

---

## Cross-cutting patterns

### 1. Browser-shaped User-Agent
gov.co sites occasionally rate-limit or 403 bare scraper UAs. We send a
Chrome-on-Mac shape that names ourselves transparently:

```
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
(KHTML, like Gecko) Chrome/120.0 Safari/537.36 Lia-Graph/1.0
(compliance scraper)
```

Implemented in `_http_get` in the base class.

### 2. Certifi-backed SSL
Several gov.co sites (especially SUIN-Juriscol) use Sectigo intermediates
that Python's default OpenSSL bundle on macOS doesn't trust. We use
**certifi**'s maintained CA bundle:

```python
ctx = ssl.create_default_context(cafile=certifi.where())
```

Fallback to OS default if certifi isn't installed. Implemented in
`base.py::_ssl_context_with_certifi`.

### 3. Three-attempt retry with backoff
0/2/6 second backoff on 5xx + transient network errors. 4xx is terminal
(URL is wrong; don't retry). Implemented in `base.py::_http_get`.

### 4. Cache-first, live-fetch-gated
On every `fetch(norm_id)`:
1. Resolve URL via `_resolve_url`. None → return None.
2. Look up `(source_id, url)` in `var/scraper_cache.db`.
3. Cache hit → return.
4. Cache miss + `live_fetch=False` → return None (test mode).
5. Cache miss + `live_fetch=True` → HTTP fetch + parse + store + return.

`live_fetch` is gated by `LIA_LIVE_SCRAPER_TESTS=1` env var. The
launcher sets it during canonicalizer runs.

### 5. Per-article slicing (when applicable)
Some norm_ids are article-scoped (`et.art.689-3`,
`decreto.1625.2016.art.1.6.1.1.10`). The scraper resolves to the
**parent doc URL** (e.g. the full ET page or DUR-1625 master page),
then slices to the requested article. Three slicer flavors in tree:

* **SUIN** uses `parse_document` (BeautifulSoup) on `<a name="ver_<n>">`
  anchors. Slices stored in `parsed_meta["articles"]` for cross-process
  share.
* **Senado** injects `[[ART:N]]` text markers before HTML stripping,
  then string-finds the marker.
* **DIAN** uses anchor-based slicing on `<a id="art_N">` shapes.

### 6. Single-source acceptance for trusted .gov.co domains
Per fixplan_v5 §3 #1 + fixplan_v6 §3 step 3, when fewer than 2
scrapers return content but the lone source is in
`_TRUSTED_GOVCO_SOURCE_IDS = {"suin_juriscol", "secretaria_senado",
"dian_normograma"}` AND its body references the article number,
the harness proceeds with a single-source LLM call instead of
refusing with `missing_double_primary_source`. Logic in
`vigencia_extractor.py::_senado_single_source_accepted`.

---

## Per-source quick reference

### `secretaria_senado` (Leyes, ET, CST, CCo)

* **URL pattern:** `http://www.secretariasenado.gov.co/senado/basedoc/<file>`.
  Notable: HTTP not HTTPS (port 443 timeouts; site doesn't redirect).
* **Article slicing:** `<a class="bookmarkaj" name="N">` anchors;
  inject `[[ART:N]]` text marker before stripping HTML.
* **Indexes:** `var/senado_et_pr_index.json` for ET segments
  (article → `pr<NNN>` segment). Build via
  `scripts/canonicalizer/build_senado_et_index.py`.
* **CCo:** no segment index yet (v7 backlog) — falls back to master
  page slicing which loses depth on high-numbered articles.
* **Modification notes:** scraped from "Modificado por…"/"Derogado
  por…" prose patterns into `parsed_meta["modification_notes"]`.
* **Rate limit:** 0.5 s.
* **Quirks:** ley NUM zero-padded to 4 digits in URL filename
  (`ley_0100_1993.html`).

### `dian_normograma` (Decretos, resoluciones, conceptos)

* **URL pattern:** `https://normograma.dian.gov.co/dian/docs/<file>.htm`.
* **Article slicing:** `<a id="art_N">` anchors; for DUR-style dotted
  articles, anchor format includes the dotted form.
* **Stability caveat:** "knowingly unstable" per operator — gateway
  errors, 404s on master pages. SUIN is preferred since fixplan_v6.
* **Modification notes:** structured table on each article; scraped
  into `parsed_meta["modification_notes"]`.
* **Rate limit:** 0.5 s.
* **Quirks:** master pages are 3 MB+ (full ET/DUR consolidados);
  per-article URLs sometimes don't exist; full-page slicing is the
  fallback.

### `suin_juriscol` (Toda la legislación, primary since fixplan_v6)

* **URL pattern:** `https://www.suin-juriscol.gov.co/viewDocument.asp?id=<NUMERIC>`.
* **Article slicing:** `<a name="ver_<n>">` anchors → `<div class="articulo_normal">` body.
  Parsed via `parse_document` from the harvester's parser
  (`src/lia_graph/ingestion/suin/parser.py`).
* **Registry:** `var/suin_doc_id_registry.json` maps canonical
  norm_id → SUIN doc_id. Built by
  `scripts/canonicalizer/build_suin_doc_id_registry.py` from the
  harvested `artifacts/suin/*/documents.jsonl`.
* **Cache strategy:** three-tier (sqlite cache → cache/suin/<sha1>.html
  → live HTTP). Sliced articles persisted in `parsed_meta["articles"]`
  for cross-process share.
* **Rate limit:** 1.0 s (heaviest HTML, slowest TCP).
* **Quirks:** Sectigo cert intermediate not in macOS Python bundle —
  certifi mandatory. Article number regex must allow multi-segment
  DUR forms (`\d+(?:[-.]\d+)*`) — the original `?` form silently
  truncated.

### `corte_constitucional` (Sentencias C-/T-/SU-, autos CC)

* **URL pattern:** `https://www.corteconstitucional.gov.co/relatoria/<YEAR>/<sent-id>.htm`.
* **Resolution:** norm_id `sent.cc.C-481.2019` → relatoria URL by year
  + sentencia id.
* **Modification verbs:** `declara_exequible`, `declara_inexequible`,
  `inhibida`, `estarse_a_lo_resuelto` — affect downstream vigencia
  states (EC, IE, etc.).
* **Rate limit:** 0.5 s.

### `consejo_estado` (Sentencias CE, autos CE)

* **URL pattern:** `https://www.consejodeestado.gov.co/buscador/...?radicado=<NUM>`.
* **Resolution:** search-driven (radicado in URL params).
* **Sentencias de Unificación:** special-case to hit the unification
  index page rather than the per-sentencia URL (those are flaky).
* **Rate limit:** 1.0 s (small infra).

---

## LLM instrumentation patterns

Every successful fetch lands in the harness's `_invoke_skill` path,
which:

1. Calls `acquire_token()` from
   `src/lia_graph/gemini_throttle.py` — file-locked token bucket
   capping project-wide RPM. Default 80 RPM (Gemini-derived); set
   `LLM_DEEPSEEK_RPM=240` for DeepSeek. Cross-process safe.
2. Builds the prompt with up to 16 KB per source × N sources. The
   prompt structure:
   * Hard rules (state vocabulary, schema, refusal criteria).
   * `as_of: <date>` and `periodo: <fiscal context>`.
   * `## Fuente <i>: <source> — <url>` blocks with sliced body.
   * "Output: A single JSON object matching the schema."
3. Calls the LLM adapter (DeepSeek-v4-pro currently). Returns raw text.
4. Parses JSON; validates against `Vigencia` shape; on shape mismatch,
   persists raw output to `evals/vigencia_extraction_v1/_debug/<norm_id>.json`.
5. Returns `VigenciaResult` (veredicto OR refusal_reason + missing_sources).

**Provider switching:** `config/llm_runtime.json` defines provider
order. `LIA_VIGENCIA_PROVIDER=<id>` overrides per call. Adapters all
expose `.generate(prompt) → str` so the parsing path is identical.

**Audit trail:** every call writes to `logs/events.jsonl` with kind
∈ `{run.started, norm.success, norm.refusal, norm.error, cli.done}`.
The heartbeat sidecar (`scripts/canonicalizer/heartbeat.py`) tails
this for live progress.

---

## Adding a new scraper (when Colombian law shifts)

1. **Identify the new source's URL pattern.** Probe with curl + browser
   UA; verify HTTP 200.
2. **Add a new file under `src/lia_graph/scrapers/<source_id>.py`.**
   Subclass `Scraper`. Set `source_id`, `rate_limit_seconds`,
   `_handled_types`. Implement `_resolve_url` + `_parse_html`.
3. **If the source is id-keyed (like SUIN), build a registry.**
   Pattern: walk a sitemap or harvest, derive canonical norm_ids
   from titles via regex, write `var/<source>_doc_id_registry.json`.
   See `scripts/canonicalizer/build_suin_doc_id_registry.py` for the
   shape.
4. **If per-article slicing is needed, override `fetch()`** to slice
   from the parent doc. Reuse the persisted-slice-cache pattern from
   `SuinJuriscolScraper._articles_dict_for_url` —
   `parsed_meta["articles"]` is the persistence shape.
5. **Add to `vigencia_extractor.py::default()` chain** in the right
   order (more authoritative + smaller-payload sources first).
6. **Add to `_TRUSTED_GOVCO_SOURCE_IDS`** if single-source acceptance
   should apply (only for `.gov.co` primary sources).
7. **Update `_norm_id_acceptance_needle`** if the new norm_type uses
   a non-standard identifier shape (article numbers, decreto numbers).
8. **Add tests** in `tests/test_<source>_scraper.py` covering:
   * `_resolve_url` with seeded registry
   * Article slicing on a fixture HTML
   * Cache hit + cache miss paths
   * Top-level (no article suffix) full-doc fetch
9. **Add an operational notes doc** at
   `docs/learnings/sites/<source>.md` covering: cert chain, robots,
   rate limit, URL patterns, slicer quirks, recovery playbooks.
10. **Run the scraper smoke tests** end-to-end with a single norm:
    ```bash
    echo '{"norm_id": "<canonical-id>"}' > /tmp/canary.jsonl
    LIA_LIVE_SCRAPER_TESTS=1 PYTHONPATH=src:. uv run python \
      scripts/canonicalizer/extract_vigencia.py \
      --input-set /tmp/canary.jsonl --output-dir /tmp/canary_out \
      --run-id smoke-<source> --allow-rerun --workers 1
    ```
    Expect a non-null veredicto.

---

## Refresh playbook (Colombian law just shifted, what do I do?)

When a new ley / decreto / resolution lands, the corpus needs to absorb
it. Steps:

1. **Add to canonical norm_ids.** If it's a new norm type (e.g. a new
   ley), check `src/lia_graph/canon.py` `norm_type` covers the form.
   Add a rule if not.
2. **Re-harvest the relevant SUIN scope.**
   `PYTHONPATH=src:. uv run python -m lia_graph.ingestion.suin.harvest --scope <scope>`.
   New documents land in `artifacts/suin/<scope>/documents.jsonl`.
3. **Rebuild the SUIN registry.**
   `scripts/canonicalizer/build_suin_doc_id_registry.py`. New canonical
   ids map to new SUIN doc_ids.
4. **(Optional) Update Senado segment indexes** if the new norm
   touches the ET, CST, or CCo: rerun
   `scripts/canonicalizer/build_senado_et_index.py` (or build the
   missing CCo/CST index — v7 backlog).
5. **Add the new norms to the canonicalizer input set.**
   `scripts/canonicalizer/build_extraction_input_set.py` rebuilds
   `evals/vigencia_extraction_v1/input_set.jsonl` from the corpus.
6. **Define a batch in `config/canonicalizer_run_v1/batches.yaml`**
   with the appropriate `norm_filter` (prefix / regex /
   et_article_range / explicit_list).
7. **Run the batch** via `launch_batch.sh --batch <X> --allow-rerun`.
8. **Monitor** via the heartbeat sidecar; check ledger row on close.

For norms whose primary source ISN'T in our 5-scraper chain, see the
"Adding a new scraper" section above.

---

## Failure-mode quick reference

| Symptom | Likely cause | Fix |
|---|---|---|
| `INSUFFICIENT_PRIMARY_SOURCES` for many norms | Scraper resolved URL but slicer pulled too thin a fragment | Improve segment index OR raise prompt source size cap |
| `missing_double_primary_source` | Scrapers all return None (registry incomplete) | Build/extend the relevant registry |
| `non_json_skill_output` | LLM hallucinating non-JSON | Tighten prompt; check `evals/.../_debug/<norm_id>.json` |
| `invalid_vigencia_shape` | LLM produced JSON but wrong fields | Same as above |
| 0 events in N minutes despite alive workers | Memory thrash (multi-process re-parse without persisted cache) | Verify `parsed_meta["articles"]` populated in SQLite; check macOS memory pressure not GREEN |
| Throttle TimeoutError | RPM cap reached project-wide | Lower worker count OR raise `LLM_DEEPSEEK_RPM` |
| Cache miss + `live_fetch=False` | Test mode without seeded cache | Set `LIA_LIVE_SCRAPER_TESTS=1` OR seed the cache |

---

*Authored 2026-04-28 PM Bogotá by claude-opus-4-7 after the fixplan_v6
SUIN-first cascade close (2340 verified veredictos / 0 errors). Update
this doc when a new scraper ships, when the URL pattern of an existing
source changes, or when a new failure mode is observed in production.*
