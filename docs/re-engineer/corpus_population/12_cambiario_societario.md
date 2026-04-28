# 12. Cambiario + Societario

**Master:** ../corpus_population_plan.md §4.7 (Phase K)  
**Owner:** unassigned  
**Status:** 🟡 not started  
**Target norm count:** ~150 (K1: ~25, K2: ~40, K3: ~60, K4: ~25)  
**Phase batches affected:** K1, K2, K3, K4

---

## What

This brief covers four specialized sub-domains critical for tax + commerce in Colombia, each with distinct sources, canonical shapes, and scraper gaps:

- **K1** (~25 norms): Resolución Externa 1/2018 JDBR (Junta Directiva Banco de la República) — the current international exchange regime covering permitted transactions, intermediaries, forward/spot markets, and sanctions. Foundational for cross-border transactions and foreign currency reporting.
- **K2** (~40 norms): DCIN-83 (Manual del Departamento de Cambios Internacionales, BanRep) — operational manual organizing cambiario rules by capítulo + numeral. Heavily cited by accountants for transaction classification.
- **K3** (~60 norms): Código de Comercio (societies portion, Arts. ~98–514, Libro Segundo) — governing partnerships, S.A., limited partnerships, and general commercial entities (excluding K4's S.A.S. separate regime).
- **K4** (~25 norms): Ley 222/1995 (S.A. reform) + Ley 1258/2008 (S.A.S.) — two separate statutes with orthogonal governance rules. Together they cover the two dominant limited-liability entity types for Colombian PYMEs.

No live scrapers exist for BanRep (K1, K2) or CCo (K3). Ley 222 + Ley 1258 use the DIAN ley.* resolver (working as of 2026-04-27). This is the most complex phase due to scraper gaps #4 (CCo, CST shared) and #5 (BanRep).

---

## Source URLs (primary)

| URL | What | Status | Scraper | Brief dependency |
|---|---|---|---|---|
| https://www.banrep.gov.co/es/normatividad/resolucion-externa-1-2018 | BanRep main landing for Res Ext 1/2018 | ✅ Live | ❌ None | K1 |
| https://www.banrep.gov.co/es/normatividad/compendios/resolucion-externa-1-2018 | BanRep compendium (consolidated text + amendments) | ✅ Live | ❌ None | K1 |
| https://www.banrep.gov.co/sites/default/files/reglamentacion/compendio-res-ext-1-de-2018.pdf | PDF compendium (full text, all amendments) | ✅ Live | ❌ None | K1 |
| https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_banrepublica_jd-0001_2018.htm | DIAN hosts Res Ext 1/2018 for reference | ✅ Live | ⚠️ DIAN scraper may reach it | K1 |
| https://www.banrep.gov.co/es/normatividad | BanRep normatividad index (search for DCIN-83) | ✅ Index | ❌ None | K2 |
| https://www.secretariasenado.gov.co/senado/basedoc/codigo_comercio.html | Senate official Código de Comercio (paginated, full text) | ✅ Live | ❌ None (gap #4) | K3 |
| https://www.secretariasenado.gov.co/senado/basedoc/ley_0222_1995.html | Senate official Ley 222/1995 | ✅ Live | ✅ DIAN ley.* | K4 |
| https://www.secretariasenado.gov.co/senado/basedoc/ley_1258_2008.html | Senate official Ley 1258/2008 (S.A.S.) | ✅ Live | ✅ DIAN ley.* | K4 |
| https://normograma.dian.gov.co/dian/compilacion/docs/ley_222_1995.htm | DIAN mirror of Ley 222 (for consistency) | ✅ Live | ✅ DIAN ley.* | K4 |

---

## Canonical norm_id shape

Per master §5:

- **Resolución BanRep:** `res.banrep.<NUM>.<YEAR>.art.<X>`  
  Example: `res.banrep.1.2018.art.5` (Res Ext 1/2018, article 5).  
  Note: K1 is a single Resolución External with many articles; sub-articles or amendments use `.par.<P>`, `.num.<M>`, etc.  
  Round-trip: `canonicalize("res.banrep.1.2018.art.5")` → `"res.banrep.1.2018.art.5"` ✓

- **DCIN-83:** `dcin.83.cap.<C>.num.<N>`  
  Example: `dcin.83.cap.5.num.3` (DCIN-83, chapter 5, numeral 3).  
  Note: DCIN-83 is the canonical manual identifier (no year, as it is a living manual updated by amendment). Numerals are the article-level unit.  
  Round-trip: `canonicalize("dcin.83.cap.5.num.3")` → `"dcin.83.cap.5.num.3"` ✓

- **Código de Comercio:** `cco.art.<N>`  
  Example: `cco.art.98` (Art. 98 CCo is the well-known opening article of the Libro Segundo "De las sociedades"). For other articles, read the printed article number off the published Código de Comercio (Decreto 410/1971) — do not invent specific article numbers. The published CCo runs through the high-2000s in article count; the YAML K3 batch regex (`^cco\.art\.([1-9]|[1-9]\d|[1-3]\d{2})$`) gates Phase K3 to articles 1–399, but the full code extends beyond that. Sub-articles use `.par.<P>`, `.lit.<L>`, etc.  
  Round-trip: `canonicalize("cco.art.98")` → `"cco.art.98"` ✓

- **Ley 222/1995:** `ley.222.1995.art.<X>`  
  Example: `ley.222.1995.art.1` (Ley 222, art 1 on reform of S.A.).  
  Round-trip: `canonicalize("ley.222.1995.art.1")` → `"ley.222.1995.art.1"` ✓

- **Ley 1258/2008:** `ley.1258.2008.art.<X>`  
  Example: `ley.1258.2008.art.25` (S.A.S. without mandatory board).  
  Round-trip: `canonicalize("ley.1258.2008.art.25")` → `"ley.1258.2008.art.25"` ✓

**Critical:** All IDs must be lowercase and use hyphens, not underscores. E.g., `cco.art.98` not `cco.art_98`.

**BanRep articulación.** Resolución Externa 1/2018 JDBR uses the canonical shape `res.banrep.1.2018.art.<N>`, where `<N>` is the article number as printed (1, 2, 3, …). The "1" between `banrep.` and `.2018` is the resolution number; the article number after `.art.` is the per-article identifier. Sub-paragrafs use `.par.<P>` (e.g. `res.banrep.1.2018.art.5.par.1`). Do not invent a sección or capítulo segment in the id; chapter/section context lives in the body.

---

## Parsing strategy

### K1 — Resolución Externa 1/2018 JDBR

1. **Fetch source:** From BanRep (PDF or HTML compendium). DIAN normograma also hosts it.
2. **Identify articles:** Res Ext 1/2018 has a defined article structure (Arts. 1–50+, depending on the consolidated version).
   - Split by "ARTÍCULO N." headings.
   - Each article is a norm_id = `res.banrep.1.2018.art.<N>`.
3. **Handle amendments:** The resolution has been amended; verify the current consolidated text from BanRep's official compendium to capture all amendments in-place.
4. **Emit rows:**
   - `norm_id`: `res.banrep.1.2018.art.<N>`
   - `norm_type`: `res_banrep`
   - `article_key`: "Artículo <N> — Resolución Externa 1/2018"
   - `body`: full text of the article (verbatim)
   - `source_url`: BanRep compendium or DIAN normograma URL
   - `emisor`: "Banco de la República (Junta Directiva)"
   - `tema`: "Régimen de cambios internacionales" or "Operaciones de cambio"

### K2 — DCIN-83 Manual

1. **Fetch source:** Obtain the DCIN-83 manual from BanRep's normatividad index or via DIAN.
2. **Understand structure:** DCIN-83 is organized by:
   - Capítulos (chapters) — e.g., Cap. 1 (general concepts), Cap. 5 (specific transaction types).
   - Numerales (numerals) — subdivisions within each chapter.
3. **Identify article-level units:** For the canonicalizer, treat each numeral as an independent norm:
   - `norm_id`: `dcin.83.cap.<C>.num.<N>` (e.g., `dcin.83.cap.5.num.3`).
4. **Emit rows:**
   - `norm_id`: `dcin.83.cap.<C>.num.<N>`
   - `norm_type`: `dcin_numeral`
   - `article_key`: "Capítulo <C>, Numeral <N>"
   - `body`: text of the numeral (verbatim)
   - `source_url`: BanRep official manual or URL
   - `emisor`: "Banco de la República (Departamento de Cambios Internacionales)"
   - `tema`: "Manual de operaciones de cambio"

### K3 — Código de Comercio (Societies)

1. **Fetch source:** From Senado official repository at https://www.secretariasenado.gov.co/senado/basedoc/codigo_comercio.html.
   - The Código is paginated (multiple PR segments); ensure full coverage.
   - Relevant range: roughly Arts. 20–100 (general commercial acts), Arts. 98–514 (Libro Segundo, societies proper).
2. **Identify articles:** Split by "ARTÍCULO N." headings (Senado page is HTML with clear article markers).
3. **Sub-articles:** If an article has paragraphs, incisos, literales, they are separate norm_ids:
   - `cco.art.98` (main article)
   - `cco.art.98.par.2` (paragraph 2)
   - `cco.art.98.lit.a` (literal a)
4. **Emit rows:**
   - `norm_id`: `cco.art.<N>` (or sub-unit)
   - `norm_type`: `cco_articulo`
   - `article_key`: "Artículo <N> Código de Comercio"
   - `body`: full text (including paragraphs, incisos, if any)
   - `source_url`: Senado URL segment where the article appears
   - `emisor`: "Congreso de la República"
   - `tema`: "Sociedades comerciales" or "Formas asociativas"

### K4 — Ley 222/1995 + Ley 1258/2008

1. **Ley 222/1995** (S.A. governance reform):
   - Fetch from Senado or DIAN (both are live).
   - Contains ~100+ articles on S.A. structure, board, shareholder rights, dividends.
   - Split by article; emit one row per article:
     - `norm_id`: `ley.222.1995.art.<X>`
     - `norm_type`: `ley_articulo`
     - `article_key`: "Artículo <X> Ley 222/1995"
     - `body`: full text
     - `source_url`: Senado or DIAN
     - `emisor`: "Congreso de la República"
     - `tema`: "Sociedades anónimas"

2. **Ley 1258/2008** (S.A.S.):
   - Fetch from Senado or DIAN (confirmed working).
   - Contains ~46 articles on S.A.S. formation, governance, minority protections.
   - Split by article; emit one row per article:
     - `norm_id`: `ley.1258.2008.art.<X>`
     - `norm_type`: `ley_articulo`
     - `article_key`: "Artículo <X> Ley 1258/2008"
     - `body`: full text
     - `source_url`: Senado or DIAN
     - `emisor`: "Congreso de la República"
     - `tema`: "Sociedad por acciones simplificada"

Both leyes use the DIAN ley.* scraper resolver (working end-to-end as of 2026-04-27); corpus rows should ingest cleanly.

---

## Edge cases observed

- **BanRep scraper gap (#5):** No live resolver exists. Fixture-only path recommended (master §7): hand-curate K1 + K2 rows directly into `tests/fixtures/scrapers/banrep/res_ext_1_2018/` and `tests/fixtures/scrapers/banrep/dcin_83/` with the article/numeral HTML. Periodic re-fetch if BanRep amends the regulations.
- **Código de Comercio scraper gap (#4):** No Senado-style scraper extension for `cco.art.*` IDs exists. Share this gap with CST (Brief 01, J1–J4). Solutions:
  - Implement a new `src/lia_graph/scrapers/senado_codigos.py` that mirrors the existing Senado scraper but handles CCo + CST URL patterns.
  - OR: fixture-only path for both CCo and CST (cheaper for initial release if Senado URLs are stable).
- **Ley 222 + Ley 1258 distinction:** Both are small leyes about S.A. and S.A.S. respectively; they have orthogonal scope (no overlap). Ensure rows are keyed correctly by ley number (222 vs. 1258). The DIAN ley.* scraper handles both.
- **Amendment tracking:** Ley 222 has been modified many times; ensure the fetched source is the current consolidated text (Senado provides this by default). DCIN-83 is a living manual; the version ingested is a snapshot as-of the parse date.
- **Paginated Senado sources:** CCo appears in multiple Senado segments (PR001, PR002, etc.). If splitting the ingest, ensure no articles are duplicated or missed across pages.

**CCo numbering.** The Código de Comercio is numbered flat — `cco.art.<N>` with `<N>` an integer 1–2032. Sub-units use the standard sub-unit suffixes (`.par.<P>`, `.num.<N>`, `.lit.<L>`, `.inciso.<I>`) per the master plan §5. Use lowercase letters for literals (`cco.art.98.lit.a`, not `cco.art.98.lit.A`).

---

## Smoke verification

After ingesting K1–K4 rows, run the §6.3 slice-size check:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path
for bid in ['K1', 'K2', 'K3', 'K4']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    print(f'  {bid}: {len(norms)} norms')
"
```

Expected (from master appendix A):
- **K1**: ≥20 norms (Min 20, target ~25).
- **K2**: ≥30 norms (Min 30, target ~40).
- **K3**: ≥50 norms (Min 50, target ~60).
- **K4**: ≥20 norms (Min 20, target ~25).

If K1 + K2 are significantly under-reported, the BanRep fixture path (gap #5 fallback) is working as expected — proceed. If K3 is under-reported and no scraper is in place, the CCo gap (#4) is the blocker; use fixture-only or coordinate with CST scraper extension.

---

## Dependencies on other briefs

- **Brief 01 (CST):** Shares scraper gap #4 (Senado codes). If CST scraper is built, CCo can reuse the same extension. Recommend: build the scraper once to cover both CST + CCo.
- **Brief 11 (Pensional + Salud):** No direct dependency on K1–K4, but if K4 (S.A.S. entities) ingests first, Brief 11's context on labor/pension obligations for SAS entities is complementary.
- **No forward dependencies:** K is the final phase; nothing downstream depends on it.

---

## Scraper coverage and gaps

**Gap #4 — `cco.art.<N>` + `cst.art.<N>` missing resolver (shared with Brief 01):**

- **Impact:** K3 (~60 norms) + J1–J4 (~170 norms) = ~230 norms blocked.
- **Fix path:** Implement `src/lia_graph/scrapers/senado_codigos.py` (new file) or extend existing `secretaria_senado.py` to map both `cco.art.<N>` and `cst.art.<N>` to their respective Senado URL patterns.
  - CCo: `https://www.secretariasenado.gov.co/senado/basedoc/codigo_comercio_pr00X.html#ARTÍCULO<N>`.
  - CST: `https://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo.html#ARTÍCULO<N>`.
- **Fixture fallback:** Recommended for MVP: hand-curate K3 CCo + J1–J4 CST rows directly into corpus without live scraper. Both codes are stable; periodic manual re-check sufficient.

**Gap #5 — BanRep (`res.banrep.*`, `dcin.*`) missing scraper:**

- **Impact:** K1 (~25 norms) + K2 (~40 norms) = ~65 norms blocked.
- **Fix path:** Implement `src/lia_graph/scrapers/banrep.py` (new file) to fetch from BanRep and parse articles/numerals.
  - Complexity: BanRep site is less structured than DIAN or Senado; articles may not have clean anchor syntax.
- **Fixture fallback (strongly recommended):** Hand-curate K1 + K2 rows. BanRep moves slowly on regulation; a fixture-only path with periodic spot-checks is pragmatic and reduces risk of scraper rot. Store fixtures in `tests/fixtures/scrapers/banrep/res_ext_1_2018/` and `tests/fixtures/scrapers/banrep/dcin_83/`.

---

## Verification notes

- **Round-trip validator (§6.1):** Before committing, run `lia_graph.canon.canonicalize(norm_id)` on all K1–K4 IDs.
- **Source URL spot-checks:** For K1, K2, K3, verify 5 random rows by fetching the source_url and confirming body text matches the source.
- **Fixture consistency:** If using fixture paths for K1–K2, document the as-of date (e.g., "K1 fixtures as of 2026-04-28") in a comment at the top of each fixture file.

---

**Last updated:** 2026-04-28  
**Status:** Ready for K4 ingestion (Ley 222 + Ley 1258 scraper confirmed live via DIAN). K1–K3 blocked on scraper gaps (#4, #5); recommend fixture-only path for MVP.
