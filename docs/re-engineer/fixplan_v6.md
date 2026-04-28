# fixplan_v6 — wire SUIN-Juriscol as the primary vigencia source, retire the DIAN-only fallback

> **Status:** drafted 2026-04-28 PM Bogotá right after the fixplan_v5
> cascade closed 187 veredictos / +25 net Postgres rows but exposed a
> single root cause behind the cascade's article-slicing collapse: the
> harness queries the DIAN normograma master page (which the operator
> calls "knowingly unstable") and ignores the 3,387 already-cached
> SUIN-Juriscol HTML files + 2,325 LOC of harvester code that sits one
> directory away. v6 is the focused engineering plan to wire SUIN in
> as the preferred primary source so the next cascade actually works.
>
> **Replaces:** `fixplan_v5.md` as the active forward plan once a fresh
> agent picks up the work. v5 stays in repo as historical context (5
> blockers closed, 4 commits — `38edac3 → 583e925`, plus the
> `4b11cd7` ThreadPoolExecutor concurrency change).
>
> **Authoritative companions:**
>   * `docs/re-engineer/state_fixplan_v6.md` — live progress tracker for v6 work (read this first)
>   * `docs/re-engineer/fixplan_v5.md` §3 — recipes for the 5 already-closed scraper blockers (still load-bearing context for how scrapers are wired in)
>   * `docs/re-engineer/canonicalizer_runv1.md` — per-batch protocol (still current)
>   * `docs/re-engineer/state_canonicalizer_runv1.md` — live per-batch state
>   * `docs/done/suin_harvestv1.md` + `suin_harvestv2.md` — how the SUIN harvester was built, what it produces, where the cached HTML lives
>   * `docs/learnings/sites/suin-juriscol.md` — SUIN site idiosyncrasies (cert chain, robots, internal id format)
>   * `CLAUDE.md` — repo-level operating guide

---

## 0. If you are a fresh agent — read this first

You are picking up a **half-shipped vigencia-extractor pipeline**. The
fixplan_v5 cascade landed correctly through extract → ingest → Falkor sync,
the asyncio + 8-worker concurrency works (commit `4b11cd7`), and the
harness's single-source acceptance is correctly generalized to all
trusted `.gov.co` primaries (commit `583e925`). What broke at runtime is
NOT a bug in those changes — it's that the harness's primary source for
DUR-articulado norms (`decreto.1625.2016.art.X.X.X`,
`decreto.1072.2015.art.X.X.X`, etc) is the **DIAN normograma master page**:

* Each master page is **3 MB** of HTML containing thousands of articles.
* DIAN normograma is **knowingly unstable** per the operator (gateway
  errors, intermittent 404s, no per-article URL pattern).
* The LLM is asked to determine vigencia for a deeply-nested article
  (e.g. `1.6.1.1.10`) inside that 3 MB blob. It refuses with
  `INSUFFICIENT_PRIMARY_SOURCES` ~85% of the time.

Meanwhile, **SUIN-Juriscol has the answer pre-extracted**:

* Per-article body text (`artifacts/suin/jurisprudencia_full/articles.jsonl` — 2,668 rows)
* Per-document modification edges with verbs (`modifica`, `deroga`,
  `reglamenta`, `declara_inhibida`, etc) — `artifacts/suin/laboral-tributario/edges.jsonl` (11,947 rows) + `artifacts/suin/jurisprudencia_full/edges.jsonl` (4,328 rows)
* Raw HTML cache under `cache/suin/` — **3,387 files**, hash-keyed
* A complete harvester: `src/lia_graph/ingestion/suin/` (2,325 LOC across
  `bridge.py` + `fetcher.py` + `harvest.py` + `parser.py`)

But the scraper at `src/lia_graph/scrapers/suin_juriscol.py` is a
**46-line stub** whose `_resolve_url()` returns `None`. The vigencia
harness wires THIS stub into its scraper chain, not the harvester. So
SUIN never participates in vigencia extraction.

**v6 closes that gap in one focused engineering session (~4-6 hours).**

**Read in this order before touching code:**

1. `CLAUDE.md` (loaded automatically) — repo operating guide.
2. **This file** — full read. §3 has the rewire recipe; §4 has the cascade plan.
3. `docs/re-engineer/state_fixplan_v6.md` — live state.
4. `docs/done/suin_harvestv1.md` + `suin_harvestv2.md` — how SUIN was harvested + what shape the data takes.
5. `docs/learnings/sites/suin-juriscol.md` — SUIN cert / robots / internal-id quirks.
6. `src/lia_graph/ingestion/suin/bridge.py` lines 91-103 (`_doc_id_for_source_path`) and lines 233-302 (`build_document_rows` / `build_stub_document_rows`) — these already do canonical-id ↔ SUIN-doc-id mapping. v6 extends that into the scraper interface.
7. `src/lia_graph/scrapers/secretaria_senado.py` — read end-to-end to model the new `suin_juriscol.py` after it (handled_types + `_resolve_url` + `fetch` shape).

**Hot facts you should know before touching anything:**

* **DeepSeek-v4-pro is the active LLM.** No change from v5. Pre-flight: `PYTHONPATH=src:. uv run python -c "from lia_graph.llm_runtime import resolve_llm_adapter; a,i=resolve_llm_adapter(); print(i['selected_provider'])"` should print `deepseek-v4-pro`.
* **Local docker stack must be up.** `docker ps` should show `supabase_db_lia-graph` and `lia-graph-falkor-dev`.
* **Project-wide DeepSeek throttle is enforced.** Default 80 RPM. File-locked at `var/gemini_throttle_state.json`. Never bypass.
* **8-worker asyncio concurrency is wired** (per commit `4b11cd7`). Set `LIA_EXTRACT_WORKERS=8` in env when launching cascade.
* **Cloud writes for Lia Graph are pre-authorized.**
* **Postgres count today: 783** distinct verified norms (758 baseline + 25 from v5 cascade).
* **The cascade driver is at `scripts/canonicalizer/run_cascade_v5.sh`** — keep using it for v6 cascade runs once the SUIN rewire lands. The current trimmed list (F2 → E1a → E1b → E1d → E2a → E2c → E3b → D5) is the right starting set; revisit after SUIN works.

**Memory-pinned guardrails (do not violate):**

* Cloud writes pre-authorized — announce, don't ask. (`feedback_lia_graph_cloud_writes_authorized`)
* Beta-stance: every non-contradicting improvement flag flips ON. (`project_beta_riskforward_flag_stance`)
* Never re-extract Phases A–D — extract once, promote through three stages. (`feedback_extract_once_three_stage_promotion`)
* All canonicalizer runners delegate to `launch_batch.sh`. (`feedback_runners_full_best_practices`)
* Project-wide token bucket throttle (default 80 RPM) — never bypass. (`feedback_canonicalizer_global_throttle`)
* Autonomous progression on canonicalizer batches. (`feedback_canonicalizer_autonomous_progression`)
* Pipeline_d organization is deliberately modular. (`feedback_respect_pipeline_organization`)
* Edit granularly — don't sprawl ≥1000 LOC files. (`feedback_granular_edits`)
* Diagnose before intervene. (`feedback_diagnose_before_intervene`)
* Six-gate lifecycle for pipeline changes. (`feedback_verify_fixes_end_to_end`)

---

## 1. One-paragraph reality check

The fixplan_v5 cascade (this morning, 2026-04-28 AM-PM Bogotá) verified the
end-to-end pipeline is sound: 8-worker asyncio, blocker fixes for
single-source acceptance, scraper handled_types extensions, and the
launcher's EXTRACT_ONLY ledger row all worked correctly. **+25 distinct
norms landed in Postgres** (758 → 783) over 11 closed batches across the
J / K / F / E families. But the binding constraint for the remaining ~3,000
norms in the cascade is article-slicing inadequacy — the harness asks the
LLM to read a 3 MB DIAN master page and find one deeply-nested DUR article.
The LLM (correctly) refuses ~85% of the time with
`INSUFFICIENT_PRIMARY_SOURCES`. Meanwhile SUIN-Juriscol has the per-article
text + the modification graph already on disk. **v6 wires SUIN in as the
preferred source so the LLM gets ~2-5 KB of focused article body instead
of 3 MB of bulk doc.** Estimated outcome of the next cascade with v6 in
place: **~70-85% pass rate, ~1,200-1,500 net new Postgres rows.**

## 2. What v5 accomplished

| Workstream | Outcome | Reference |
|---|---|---|
| 5 blocker fixes | All ✅ — single-source Senado/DIAN, CST+CCo, concepto narrowing, CE fixtures, score-skip | commits `38edac3`, `b1cde16`, `e8ffa09`, `08e73f6`, `c20b3ce` |
| ThreadPoolExecutor concurrency (8 workers) | Working — 10× throughput vs sequential | commit `4b11cd7` |
| Govco single-source generalization | Working — accepts dian_normograma when SUIN is disabled | commit `583e925` |
| Cascade driver + heartbeat + state files | Working — stop-switch on 2 consecutive 0-veredicto batches | commit `af67e56` |
| Cumulative through cascade | 187 veredictos written; +25 distinct norms in Postgres | `evals/canonicalizer_run_v1/ledger.jsonl` |

**Cumulative numbers (start of v6):**

* `parsed_articles.jsonl`: 12 305 rows (no change since v5 — corpus stable)
* Postgres `norm_vigencia_history`: **783** distinct verified norms
* Falkor `(:Norm)`: ~11 700 nodes (TBD — pull a fresh count when v6 starts)
* SUIN HTML cache: **3 387** files at `cache/suin/`
* SUIN documents harvested: 9 (laboral-tributario) + 3 370 (jurisprudencia_full) + 4 (smoke fixtures)
* SUIN modification edges harvested: **16 282** (11 947 + 4 328 + 7) across all scopes

## 3. The v6 fix — file-by-file recipe

### 3.0 Reality-check before you start coding (verified 2026-04-28 PM)

Before reading the steps below, internalize what **does** and **does not**
already exist in the codebase. The first draft of this plan named some
helpers as if they existed in `src/lia_graph/ingestion/suin/parser.py` —
they don't. This subsection corrects the record so a fresh agent doesn't
waste time grepping for symbols that aren't there.

**Exists in `src/lia_graph/ingestion/suin/parser.py` (701 LOC):**
* `parse_document(html, doc_id, ruta)` at line 385 — top-level entry that
  returns a `SuinDocument` with `articles: tuple[SuinArticle, ...]` and
  `edges: tuple[SuinEdge, ...]`. **This is the right entry point** for
  step 2's article-slicing helper.
* `_extract_article(soup, anchor, ...)` at line 486 — internal; operates
  on a BeautifulSoup `soup` and an `<a>` anchor. Useful as a reference
  for what one article looks like, not as a public helper.
* `normalize_article_key(raw)` at line 169 — public; converts "135 bis",
  "Art. 364-4", "Artículo 1º" etc. to a canonical key string. **Reuse
  this** when matching the requested article against the parsed list.
* `normalize_doc_id(raw)` at line 194 — public; canonicalizes SUIN doc
  ids. Useful in the registry build step.
* `SuinArticle` dataclass at line 338 — has `article_number`, `body_text`,
  `heading`, `article_fragment_id`. Slicing returns one of these.
* `SuinDocument` dataclass at line 358 — what `parse_document` returns.

**Exists in `src/lia_graph/ingestion/suin/bridge.py` (846 LOC):**
* `_doc_id_for_source_path(doc_id_raw)` at line 91 — returns a TUPLE
  `(source_path, relative_path, doc_id_hint)`, NOT a SUIN doc_id. It
  produces a `suin://...` scheme path used by the Supabase sink, plus a
  doc_id_hint that may match the SUIN internal id. **Don't use this for
  the registry — use the `title` regex instead** (see Step 1 below).
* `_iter_jsonl(path)` at line 71 — utility for streaming `documents.jsonl`
  / `articles.jsonl` / `edges.jsonl` rows. Reuse in the registry build.
* `SuinScope.load(root)` at line 60 — loads a harvest scope into a
  parsed view. Useful if you want to walk one scope at a time.

**Does NOT exist (you will write these in Step 2):**
* `_canonical_parent_id(norm_id)` — strip `.art.X[.Y...]` to get parent.
* `_article_key_from_norm_id(norm_id)` — extract dotted DUR article key.
* `_slice_article_from_suin_html(html, article_key, doc_id, ruta)` —
  call `parse_document`, find the `SuinArticle` whose
  `normalize_article_key(article_number) == normalize_article_key(article_key)`,
  return its `body_text` (or `None` if not found).
* `_load_suin_registry()` — JSON loader for `var/suin_doc_id_registry.json`.

**Does NOT exist in launcher (Step 5 needs to add this):**
* `EXTRA_EXTRACT_FLAGS` env var pass-through in
  `scripts/canonicalizer/launch_batch.sh`. The quick-start in §6 assumes
  it works, but it doesn't yet. Add it as part of step 5 (5 LOC change
  in the launcher's nohup-extract command).

**Six-gate lifecycle reminder (`feedback_verify_fixes_end_to_end`):** unit
tests alone are NOT sufficient for a pipeline change. Each step's "Test"
clause below is the technical/criterion gate. The end-user validation
happens at the cascade (steps 5-7) — Wave 1's first batch (E1a) closing
at ≥70% pass is the actual greenlight signal. If E1a still refuses ~85%
under SUIN-first, the slicing helper is wrong; iterate before continuing.

---

### Step 1 — Build the canonical-id → SUIN-doc-id registry

**What.** SUIN's documents are keyed by an internal numeric `doc_id`
(e.g. `1132325` for Decreto 624/1989). Our canonical norm_ids are
`decreto.1625.2016`, `ley.100.1993`, etc. The bridge module
(`src/lia_graph/ingestion/suin/bridge.py:91`) already has
`_doc_id_for_source_path(doc_id_raw)` which derives a canonical-shaped
id from the SUIN ruta — but it returns a tuple, not a registry. v6
needs a flat lookup table.

**Where.** New file: `var/suin_doc_id_registry.json`. Build script:
new file `scripts/canonicalizer/build_suin_doc_id_registry.py`.

**How.** The script walks all SUIN harvest scopes
(`artifacts/suin/*/documents.jsonl`), parses each `doc_id` + `ruta` + `title`
+ `fecha_publicacion`, and emits a JSON map of the form:

```json
{
  "decreto.624.1989":  {"suin_doc_id": "1132325", "ruta": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1132325", "title": "DECRETO 624 DE 1989"},
  "decreto.1625.2016": {"suin_doc_id": "...", "ruta": "...", "title": "..."},
  "decreto.1072.2015": {"suin_doc_id": "...", ...},
  ...
}
```

**Canonical-id derivation strategy (the title regex IS the primary signal):**

```python
import re

_TITLE_PATTERNS = [
    # ("LEY N DE YYYY", "DECRETO N DE YYYY", etc.) → canonical id form
    (re.compile(r"^(?:LEY|Ley)\s+(\d+)\s+(?:DE|de)\s+(\d{4})"),       lambda m: f"ley.{m.group(1)}.{m.group(2)}"),
    (re.compile(r"^(?:DECRETO|Decreto)\s+(\d+)\s+(?:DE|de)\s+(\d{4})"), lambda m: f"decreto.{m.group(1)}.{m.group(2)}"),
    (re.compile(r"^(?:RESOLUCI[ÓO]N|Resoluci[óo]n)(?:\s+(?:DIAN|MINHACIENDA|MINTRABAJO))?\s+(\d+)\s+(?:DE|de)\s+(\d{4})"),
        lambda m: f"res.dian.{m.group(1)}.{m.group(2)}"),  # adjust authority as needed
    (re.compile(r"^CONCEPTO\s+(\d+)\s+(?:DE|de)\s+(\d{4})"),          lambda m: f"concepto.dian.{m.group(1)}.{m.group(2)}"),
    # Add more patterns as you discover them in the harvested titles.
]

def _canonical_from_title(title: str) -> str | None:
    title = title.strip()
    for pattern, builder in _TITLE_PATTERNS:
        m = pattern.match(title)
        if m:
            return builder(m)
    return None
```

**Skip rule:** if `_canonical_from_title(title)` returns None, log the
title and skip that document (don't crash the build). The registry is
best-effort — partial coverage is fine for v6 since we only need the
~10 parent documents the cascade actually uses (decreto 1625, 1072, 624,
ley 1943, ley 100, etc).

**Validation:** before writing the registry, dry-run-print the first 20
matched titles + their derived canonical ids so a human can sanity-check.

**Why.** Without this registry the scraper can't map a canonical norm to
a SUIN doc. With it, every harness call is a constant-time lookup.

**Test.** Add `tests/test_suin_doc_id_registry.py`. Assert: registry has
≥3 entries; lookups for `decreto.624.1989`, `decreto.1625.2016` (if
present) return non-empty SUIN doc_ids.

**Estimate.** **60-90 min** (script + walk all scopes + dedup +
fallback heuristics + test).

### Step 2 — Replace the SUIN scraper stub with a real one

**What.** Today `src/lia_graph/scrapers/suin_juriscol.py` is 46 lines, all
of which exist to return `None` and a no-op `_parse_html`. Replace with a
real scraper that reads from the cached HTML on disk OR the SUIN HTTP
fetcher when the cache misses.

**Where.** `src/lia_graph/scrapers/suin_juriscol.py` — full rewrite.

**How.**

```python
class SuinJuriscolScraper(Scraper):
    source_id = "suin_juriscol"
    rate_limit_seconds = 1.0
    _handled_types = {
        "ley", "ley_articulo",
        "decreto", "decreto_articulo",
        "estatuto", "articulo_et",
        "resolucion", "res_articulo",
    }

    def __init__(self, cache):
        super().__init__(cache)
        self._registry = _load_suin_registry()  # var/suin_doc_id_registry.json

    def _resolve_url(self, norm_id: str) -> str | None:
        # Map canonical → SUIN doc_id → SUIN URL
        parent_id = _canonical_parent_id(norm_id)  # "decreto.1625.2016.art.X.Y" → "decreto.1625.2016"
        entry = self._registry.get(parent_id)
        if entry is None:
            return None
        return entry["ruta"]  # already-formed SUIN URL

    def fetch(self, norm_id: str) -> ScraperFetchResult | None:
        # Get the parent doc HTML via the base implementation (which checks cache,
        # then live HTTP via the existing SuinFetcher in src/lia_graph/ingestion/suin/fetcher.py).
        result = super().fetch(_canonical_parent_id(norm_id))
        if result is None:
            return None
        # For article-scoped norms, slice to the article body using the
        # parser from src/lia_graph/ingestion/suin/parser.py (it already
        # knows how to extract per-article text from SUIN HTML).
        if ".art." in norm_id:
            article_key = _article_key_from_norm_id(norm_id)
            sliced = _slice_article_from_suin_html(result.parsed_text, article_key)
            if sliced is None:
                return None
            return ScraperFetchResult(
                source=self.source_id,
                url=result.url,
                parsed_text=sliced,
                meta={"sliced_to_article": article_key, **(result.meta or {})},
            )
        return result
```

Helpers — write these in the new `suin_juriscol.py`. **None exist today;
all four are new code.** Reference the existing parser.py functions
(`parse_document`, `normalize_article_key`, `SuinArticle`) instead of
inventing new ones for the parts they cover.

```python
def _canonical_parent_id(norm_id: str) -> str:
    """decreto.1625.2016.art.X.Y → decreto.1625.2016. ley.100.1993.art.5 → ley.100.1993."""
    if ".art." in norm_id:
        return norm_id.split(".art.")[0]
    return norm_id


def _article_key_from_norm_id(norm_id: str) -> str | None:
    """decreto.1625.2016.art.1.6.1.1.10 → "1.6.1.1.10". None if no .art. suffix."""
    if ".art." not in norm_id:
        return None
    return norm_id.split(".art.")[1]


def _load_suin_registry() -> dict[str, dict]:
    """Load var/suin_doc_id_registry.json. Empty dict if file missing."""
    p = Path("var/suin_doc_id_registry.json")
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _slice_article_from_suin_html(
    html: bytes, article_key: str, *, doc_id: str, ruta: str
) -> str | None:
    """Parse the SUIN page and return the body of the article matching article_key.

    Uses parse_document from the harvester (which returns a SuinDocument with
    typed SuinArticle children). Matches by normalize_article_key on both sides.
    """
    from lia_graph.ingestion.suin.parser import parse_document, normalize_article_key

    doc = parse_document(html, doc_id=doc_id, ruta=ruta)
    target_key = normalize_article_key(article_key)
    for art in doc.articles:
        if normalize_article_key(art.article_number) == target_key:
            return art.body_text
    return None
```

**Note on doc_id:** the SUIN harvest's `documents.jsonl` uses SUIN's
internal numeric id as `doc_id` (e.g. `"1132325"`). The slicing helper
needs that id to invoke `parse_document`. Pull it from the registry
entry: `entry["suin_doc_id"]`.

**Why.** This is the rewire that actually unblocks the cascade. With
SUIN sliced article bodies, the LLM gets ~2-5 KB instead of 3 MB. Pass
rate jumps from ~15% to expected 70-85%.

**Test.** Add `tests/test_suin_juriscol_scraper.py`. At least 4 cases:
* `_resolve_url("decreto.1625.2016.art.1.6.1.1.10")` returns a SUIN URL
* `_resolve_url("decreto.NONEXISTENT.9999.art.1")` returns `None`
* `fetch("decreto.624.1989.art.1")` (using a fixture) returns parsed text
  containing "Artículo 1" and not the bulk of other articles
* `fetch` honors cache (mock `cache.get` to return a CacheEntry, assert no
  HTTP call)

**Estimate.** **2-3 hours** (rewrite + helpers + 4 tests + fixture HTML).

### Step 3 — Reorder the scraper chain in the harness

**What.** `src/lia_graph/vigencia_extractor.py:144-152` currently builds
the registry as `[Senado, DIAN, SUIN, CC, CE]`. SUIN was last because the
stub never returned anything. Move it to FIRST so the harness tries SUIN
before DIAN.

**Where.** `src/lia_graph/vigencia_extractor.py` `default()` classmethod.

**How.**

```python
registry = ScraperRegistry(
    [
        SuinJuriscolScraper(cache),     # ← first: stable + already-cached
        SecretariaSenadoScraper(cache), # leyes/CST/CCo/ET
        DianNormogramaScraper(cache),   # fallback for what SUIN doesn't have
        CorteConstitucionalScraper(cache),
        ConsejoEstadoScraper(cache),
    ]
)
```

Also add `dian_normograma` to the `_TRUSTED_GOVCO_SOURCE_IDS` set if not
already there (it is per commit `583e925`), AND add `suin_juriscol` —
the new scraper deserves single-source acceptance too.

**Why.** Order dictates which source wins on disagreement and which gets
called when only one returns content. SUIN-first means the LLM gets
clean per-article text from the start. DIAN becomes the fallback.

**Test.** Add to `tests/test_vigencia_extractor.py`:
* assert `_TRUSTED_GOVCO_SOURCE_IDS` includes `suin_juriscol`
* live test: `verify_norm("decreto.1625.2016.art.1.1.1")` returns a
  veredicto with `single_source_accepted == "suin_juriscol"` (NOT
  `dian_normograma` as it does today).

**Estimate.** **30 min** (small edit + 2 tests).

### Step 4 — Add `--rerun-only-refusals` to extract_vigencia.py

**What.** v5 produced 187 successful veredictos across the 11 closed batches
(ledger.jsonl). Re-extracting those costs DeepSeek tokens with no benefit — we
already have the answer. Skip them; only re-run the ~1450 refusals.

The existing `--resume-from-checkpoint` flag is too blunt: it skips
ANY JSON on disk, including the refusals we DO want to retry under SUIN.
We need a **success-aware skip**.

**Where.** `scripts/canonicalizer/extract_vigencia.py` — `_process_one()`
function added in commit `4b11cd7`.

**How.** Add a new CLI flag that opens each existing JSON before
deciding to skip:

```python
p.add_argument("--rerun-only-refusals", action="store_true",
               help="If a per-norm JSON already exists with a non-null veredicto, "
                    "skip the norm (success preserved). If it exists with "
                    "veredicto=null (refusal), re-extract under the new pipeline. "
                    "Use this for v6 cascade reruns to avoid wasting tokens on "
                    "already-successful v5 extractions.")
```

In `_process_one`:

```python
if args.rerun_only_refusals and out_path.exists():
    try:
        existing = json.loads(out_path.read_text(encoding="utf-8"))
        if existing.get("result", {}).get("veredicto") is not None:
            return "skipped"
        # else: fall through and re-extract this refusal
    except Exception:
        # malformed JSON → re-extract to be safe
        pass
```

**Why.** Saves compute + DeepSeek tokens. v5 cascade re-extractions
showed ~187 successes mixed in among ~1450 refusals; with this flag the
v6 cascade only processes the 1450, cutting expected wall-time from
~4 hours to **~3 hours** (a 25% saving).

**Test.** Add `tests/test_extract_vigencia_rerun_only_refusals.py`:
* Set up a temp dir with 3 existing JSONs: one V veredicto, one VM
  veredicto, one null+refusal_reason. Run extract with
  `--rerun-only-refusals`. Assert: 2 skipped, 1 re-extracted.

**Estimate.** **30-45 min** (flag + branch + test).

### Step 5 — Cascade rerun + accept the EXTRACT_ONLY rows from v5 as informational

**What.** With SUIN-first wired, rerun the cascade trimmed list
(F2 → E1a → E1b → E1d → E2a → E2c → E3b → D5). The previous v5 EXTRACT_ONLY
ledger rows for these batches stay in the ledger as historical context.
The new run will append fresh rows.

**Where.** `scripts/canonicalizer/run_cascade_v5.sh` — already trimmed
to the right list. Just relaunch with `LIA_EXTRACT_WORKERS=8`.

**How.** Two small edits, then the cascade command:

**5a. Add `EXTRA_EXTRACT_FLAGS` pass-through to `scripts/canonicalizer/launch_batch.sh`.**
Today's launcher doesn't pass through extra flags. Edit the nohup-extract
command (around line 245) to append `${EXTRA_EXTRACT_FLAGS:-}`:

```bash
exec env PYTHONPATH=src:. uv run python scripts/canonicalizer/extract_vigencia.py \\
    --batch-id '${BATCH}' \\
    --run-id '${RUN_ID}' \\
    --output-dir 'evals/vigencia_extraction_v1' \\
    --batches-config '${BATCHES_CONFIG}' \\
    ${GUARD_FLAG} \\
    ${EXTRA_EXTRACT_FLAGS:-}
```

That's it for the launcher — the env var inherits through nohup naturally.

**5b. Cascade run command (after engineering steps 1-4 + 5a all ✅):**

```bash
EXTRA_EXTRACT_FLAGS="--rerun-only-refusals" \
LIA_EXTRACT_WORKERS=8 \
nohup bash scripts/canonicalizer/run_cascade_v5.sh \
    > logs/cascade_v6_driver.log 2>&1 &
disown
echo $! > /tmp/cascade_v6_driver.pid
```

**Why.** With `--rerun-only-refusals`, the cascade re-processes only the
~1 450 v5 refusals — preserving the 187 v5 successes already on disk.
Wall-time drops from ~4 h to ~3 h, DeepSeek tokens drop ~12%.

**Test.** First-batch sanity check: F2 closes with ≥70% pass rate AND
the launcher log shows `skipped > 0` (the 17 v5 successes preserved).

**Estimate.** Wall time **~3 hours** for the trimmed cascade at
8-worker asyncio with `--rerun-only-refusals`. Expected pass rate
**70-85%** of the re-tried refusals → projected **~1 000-1 250 new
veredictos** (on top of v5's 187 preserved).

### Step 6 — Decide whether to re-add G1 / E5 / E6b / E6c / J8b

**What.** Five v5-trimmed batches were skipped because their parent DIAN
URLs returned 404:
* G1 (407 IVA Concepto Unificado numerals — `concepto_dian_0001-2003.htm` 404)
* E5 (104 COVID decretos — `decreto_417_2020.htm` 404)
* E6b/E6c (525 DUR-1072 SST/riesgos articles — `decreto_1072_2015.htm` 404)
* J8b (229 DUR-1072 shared — same 404)

**Where.** `scripts/canonicalizer/run_cascade_v5.sh` BATCHES list.

**How.** With SUIN-first, check whether SUIN's harvest covers these
docs:
* `grep -i "1072 de 2015" artifacts/suin/laboral-tributario/documents.jsonl`
* `grep -i "417 de 2020" artifacts/suin/jurisprudencia_full/documents.jsonl`
* `grep -i "0001 de 2003" artifacts/suin/laboral-tributario/documents.jsonl`

If SUIN has them, re-add to BATCHES and rerun. If not, harvest them via
`src/lia_graph/ingestion/suin/harvest.py` (extend the `SITEMAPS` table
or seed URL list) — but that's its own engineering effort, treat as v7.

**Why.** Each unblocked batch adds 100-500 new norms. Worth the check.

**Estimate.** **30 min** to grep + re-add (if SUIN has them). **3-5 hours**
to harvest if SUIN doesn't.

---

## 4. Cascade plan after the SUIN rewire lands

**Order — re-run v5 failures first, biggest pile of refusals at the
front, batches where SUIN-first directly helps before batches where
SUIN is incidental.** Per operator directive 2026-04-28 PM:
*"in v6 start with re.runing failed norms first."*

`--rerun-only-refusals` (step #4) means each batch only re-processes
the norm_ids whose v5 JSON has `veredicto: null`. The 187 v5 successes
stay on disk untouched.

### Wave 1 — DIAN-routed DUR-articulado reruns (SUIN-first directly fixes these)

The whole reason for v6 — these are the batches where the DIAN master
page is 3 MB and the LLM can't slice. SUIN's per-article text fixes them.

| Order | Batch | v5 outcome | Refusals to retry | Expected new ver. | Notes |
|---:|---|---|---:|---:|---|
| 1 | **E1a** (rerun) | 13 ✅ / 572 🛑 | **572** | ~460 | Largest pile — sanity check that SUIN per-article slicing actually works at scale |
| 2 | **F2** (rerun) | 17 ✅ / 94 🛑 | **94** | ~75 | Smaller — already half-validated; confirms F2 jumps from 17 to ~92 |
| 3 | **E1b** | never run | 95 | ~75 | DUR-renta cont. |
| 4 | **E1d** | never run | 337 | ~270 | DUR-renta cont. |
| 5 | **E2a** | never run | 304 | ~245 | DUR IVA |
| 6 | **E2c** | never run | 228 | ~180 | DUR retefuente |
| 7 | **E3b** | never run | 68 | ~55 | DUR sanciones |
| 8 | **D5** | never run | 39 | ~30 | Ley 1943/2018 articles |

Wave 1 sub-total: **~1 390 new veredictos** if SUIN delivers as expected.

### Wave 2 — Senado-routed CST/CCo reruns (only if SUIN has the doc)

These v5 failures came from **Senado** anchor-slicing inadequacy, not
DIAN. SUIN-first only helps if SUIN's harvest covers CST + CCo. Check
before running:

```bash
grep -i 'codigo sustantivo\|cst\|trabajo' artifacts/suin/*/documents.jsonl | head
grep -i 'codigo de comercio\|cco' artifacts/suin/*/documents.jsonl | head
```

| Order | Batch | v5 outcome | Refusals to retry | Expected new ver. | Notes |
|---:|---|---|---:|---:|---|
| 9 | K3 (rerun) | 92 ✅ / 223 🛑 | **223** | ~180 | CCo articles — IF SUIN has Código de Comercio |
| 10 | J4 (rerun) | 11 ✅ / 66 🛑 | **66** | ~55 | CST collective |
| 11 | J3 (rerun) | 4 ✅ / 40 🛑 | **40** | ~30 | CST cont. |
| 12 | J2 (rerun) | 32 ✅ / 19 🛑 | **19** | ~15 | CST cont. |
| 13 | J1 (rerun) | 23 ✅ / 6 🛑 | **6** | ~5 | CST first batch |

Wave 2 sub-total: **~285 new veredictos** if SUIN has CST + CCo coverage.
Skip this wave entirely if the grep above returns nothing.

### Wave 3 — gated on SUIN coverage check (§3 step 6 of fixplan_v6)

Five batches v5 marked unrunnable because their parent DIAN URLs 404.
Check SUIN coverage:

```bash
grep -i '1072 de 2015' artifacts/suin/laboral-tributario/documents.jsonl
grep -i '417 de 2020' artifacts/suin/jurisprudencia_full/documents.jsonl
grep -i '0001 de 2003' artifacts/suin/laboral-tributario/documents.jsonl
```

| Order | Batch | Slice | Expected | Notes |
|---:|---|---:|---:|---|
| 14 | E5 | 104 | ~80 | COVID decretos — decreto 417/2020 |
| 15 | E6b | 296 | ~235 | DUR 1072 riesgos |
| 16 | E6c | 229 | ~180 | DUR 1072 SST |
| 17 | J8b | 229 | ~0 | DUR 1072 shared — cache-hit fast after E6 |
| 18 | G1 | 407 | ~325 | IVA Concepto Unificado numerals |

Wave 3 sub-total: **~820 new veredictos** — IF SUIN coverage exists.
If SUIN is missing any of these, log harvest extension as v7 and skip.

### v6 grand total expectations

| Outcome | Wave 1 only | + Wave 2 | + Wave 3 (full coverage) |
|---|---:|---:|---:|
| New veredictos | ~1 390 | ~1 675 | **~2 495** |
| Postgres total | ~2 173 | ~2 458 | **~3 278** |
| Wall-time | ~3 hours | ~3.5 hours | ~6-7 hours |

**Worst case (Wave 1 only):** Postgres goes 783 → ~2 173, well above the
v5 cascade outcome and within reach of the original ~3 200 DoD after a
single follow-up wave.

**Best case (all 3 waves):** Postgres goes 783 → ~3 278, exceeding the
original DoD and effectively closing the canonicalizer next-gate.

---

## 5. What v6 does NOT cover (carry-forward backlog)

These items are tracked here but explicitly out of v6 scope:

* **Live-fetch path for CE auto/sent SPA** (fixplan_v5 §3 #2) — fixture-only path is in place; live SPA scraping needs Selenium/playwright. Treat as v7 if expert briefs 14 don't deliver real text.
* **Función Pública scraper** (fixplan_v5 §3 #1 Approach A alternative) — superseded by SUIN-first. Defer indefinitely.
* **Outside-expert deliveries 13/14/15** — operator timing.
* **DIAN concepto lookup table** (`var/dian_concepto_lookup.json`) — superseded by SUIN-first IF SUIN has the concepto coverage. Check at step 6.
* **Senado CCo segment index** (`var/senado_cco_pr_index.json`) — superseded by SUIN-first IF SUIN has CCo article coverage. Otherwise revisit.
* **Article-slicing improvements for DIAN scraper** — superseded by SUIN-first. DIAN becomes fallback only.
* **Pool maintainer counter bug** (fixplan_v4 §5.4) — sequential cascade still avoids the issue. Asyncio in extract_vigencia.py is fine.
* **SME signoff (O-1) → cloud promotion (O-2)** — operator gate, not engineering.

---

## 6. Quick-start for resuming

```bash
# 1. Source env
set -a; . .env.local; set +a

# 2. Confirm provider
PYTHONPATH=src:. uv run python -c "
from lia_graph.llm_runtime import resolve_llm_adapter
a, i = resolve_llm_adapter()
print(f'{i[\"selected_provider\"]} ({i[\"adapter_class\"]}, {i[\"model\"]})')"
# Expected: deepseek-v4-pro

# 3. Confirm docker
docker ps --format '{{.Names}}' | grep -E "(supabase_db_lia-graph|lia-graph-falkor-dev)"

# 4. Confirm SUIN harvest exists
ls cache/suin/ | wc -l         # should be ≥ 3387
ls artifacts/suin/             # should list jurisprudencia_full + laboral-tributario at minimum

# 5. Read state
cat docs/re-engineer/state_fixplan_v6.md
```

**Then for engineering work**, follow §3 step-by-step. After each step,
run `PYTHONPATH=src:. uv run pytest tests/test_suin_juriscol_scraper.py
tests/test_vigencia_extractor.py tests/test_scrapers.py -q` to confirm
no regression.

**For the cascade run after SUIN-first lands**, use the existing trimmed
driver:

```bash
LIA_EXTRACT_WORKERS=8 nohup bash scripts/canonicalizer/run_cascade_v5.sh \
    > logs/cascade_v6_driver.log 2>&1 &
disown
echo $! > /tmp/cascade_v6_driver.pid
```

Heartbeat (3-min cron, identical to v5):

```bash
PYTHONPATH=src:. uv run python scripts/canonicalizer/cascade_heartbeat.py
```

---

## 7. Numbers that matter

**Today (start of v6):**

* Postgres `norm_vigencia_history`: **783** distinct verified norms (758 baseline + 25 from v5 cascade)
* Falkor `(:Norm)`: ~11 700 nodes (TBD precise count)
* SUIN HTML cache: **3 387** files
* SUIN harvested edges: **16 282** (across 3 scopes)

**v6 target (after the rewire + cascade):**

* Postgres: **~3 000+** distinct verified norms (close to the original ~3 400 DoD)
* Falkor edges: **~3 000+** structural edges
* Cascade pass rate: **70-85%** (vs ~15% in v5 trimmed cascade)

**v6 wall-time estimate:**

* Engineering (steps 1-3): **~4-6 hours**
* Cascade run (8 trimmed batches at 8 workers): **~3-4 hours**
* Optional steps 5-6 (re-add G1/E5/E6b/E6c/J8b): **+30 min - 5 hours** depending on SUIN coverage
* **Total: 1-1.5 working days for v6 to reach session-3 target.**

---

## 8. File index — where to look

| Concern | File |
|---|---|
| What does v6 close? | This file §3 |
| Live state for v6 | `docs/re-engineer/state_fixplan_v6.md` |
| Cumulative state through v5 | `docs/re-engineer/state_fixplan_v5.md` |
| Per-batch state | `docs/re-engineer/state_canonicalizer_runv1.md` |
| Per-brief corpus state | `docs/re-engineer/state_corpus_population.md` |
| YAML batch defs | `config/canonicalizer_run_v1/batches.yaml` |
| Cascade driver | `scripts/canonicalizer/run_cascade_v5.sh` |
| Cascade heartbeat | `scripts/canonicalizer/cascade_heartbeat.py` |
| Mandatory runner protocol | `docs/re-engineer/fixplan_v4.md` §6.A |
| Vigencia harness (where source chain lives) | `src/lia_graph/vigencia_extractor.py:144-152` |
| Scraper stub to replace | `src/lia_graph/scrapers/suin_juriscol.py` (46 lines today) |
| SUIN harvester to draw from | `src/lia_graph/ingestion/suin/` (2 325 LOC) |
| SUIN bridge canonical-id mapping | `src/lia_graph/ingestion/suin/bridge.py:91` |
| SUIN article slicing | `src/lia_graph/ingestion/suin/parser.py` (701 LOC) |
| SUIN raw HTML cache | `cache/suin/` (3 387 files) |
| SUIN harvested artifacts | `artifacts/suin/{laboral-tributario,jurisprudencia_full,smoke}/` |
| SUIN site quirks | `docs/learnings/sites/suin-juriscol.md` |
| SUIN harvest design | `docs/done/suin_harvestv1.md` + `suin_harvestv2.md` |
| LLM provider config | `config/llm_runtime.json` |
| Token-bucket throttle | `src/lia_graph/gemini_throttle.py` |
| Adapter retry policy | `src/lia_graph/gemini_runtime.py` |
| Scraper cache (SQLite, WAL) | `var/scraper_cache.db` |
| SUIN doc-id registry to build | `var/suin_doc_id_registry.json` (NEW in v6) |

---

## 9. Decision history + current path

The 2026-04-28 PM v5 cascade halt-point posed: continue trimming the cascade
batch by batch as we discover URL-discoverability gaps, OR step back and
diagnose the root cause? **v6 chosen** because:

* The diagnosis (SUIN-Juriscol stub vs. 2 325 LOC of working harvester)
  pointed to a single-source fix that resolves dozens of downstream
  symptoms at once.
* The operator's two directives mid-cascade (`use SUIN first!` and
  `DIAN normograma is knowingly unstable`) align exactly with the
  rewire scope.
* The SUIN harvest already exists. v6 is wiring, not new harvesting.
  This is the cheapest-by-far path to ~70-85% cascade pass rate.

**Path chosen 2026-04-28 PM:** v6 wires SUIN-Juriscol as the preferred
primary source in the vigencia harness, reorders the scraper chain
SUIN → Senado → DIAN → CC → CE, and reruns the trimmed cascade. Expected
outcome: **~3 000+ Postgres rows**, close enough to the original ~3 400
DoD that the remaining gap is purely the few batches whose docs aren't
yet in SUIN's harvest (which step 6 audits and step 7 — a future v7 —
extends if needed).

**What the next agent will be doing:** open
`state_fixplan_v6.md`, claim a step from §3, edit the relevant file per
this doc, run tests, commit, mark task ✅, claim the next one. After
all 3 engineering steps close, run the §4 cascade. Update
`state_fixplan_v6.md` §10 run log along the way.

**Recommended first step:** #1 (build the SUIN doc_id registry, ~60-90
min). Tiny, isolated, makes step #2 trivial. Then #2 (rewrite the
scraper, ~2-3 hours). Then #3 (chain reorder, ~30 min). Then cascade.

---

*Drafted 2026-04-28 PM Bogotá by claude-opus-4-7 immediately after the
fixplan_v5 cascade halt at E1a (step 2 of 8 trimmed) on operator
directive. v6 supersedes v5 as the active forward plan. v5 stays in
repo as historical context — its §3 blocker recipes + §4 cascade plan
are still load-bearing references for the cascade.*
