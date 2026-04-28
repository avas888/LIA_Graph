# 10. Jurisprudencia — CC y CE

**Master:** ../corpus_population_plan.md §4.5 (Phase I)  
**Owner:** unassigned  
**Status:** 🟡 not started  
**Target norm count:** ~70 (5 already in I1 fixture; ~65 to add in I2/I3/I4)  
**Phase batches affected:** I1 (done), I2, I3, I4

---

## What

This brief covers three sub-domains of Colombian jurisprudencia critical for the Lia canonicalizer's Phase I:

- **I2** (~15 norms): Sentencias Corte Constitucional sobre principios tributarios — especially legalidad (C-291/2015), capacidad económica (Art. 363), suficiencia (Art. 338). These set the constitutional floor for all tax legislation.
- **I3** (~30 norms): Sentencias de unificación from Consejo de Estado, Sección Cuarta (tribunal section overseeing tax law). DT validation rules; precedent-setting on devoluciones, compensaciones, IVA treatment, deduction scope (Art. 107 ET).
- **I4** (~20 norms): Autos de suspensión provisional from CE — emergency stays blocking enforcement of specific decrees mid-2026 (e.g., Decreto 1474/2025 IE provisions). These are the volatile regulatory edges the canonicalizer must track.

I1 is already complete (5 acid-test sentencias seeded in the YAML's `explicit_list`). This brief addresses the gap: I2, I3, I4 require corpus population + scraper hardening at the CE level.

---

## Source URLs (primary)

| URL | What | Status |
|---|---|---|
| https://www.corteconstitucional.gov.co/relatoria/<YEAR>/<TYPE>-<NUM>-<YY>.htm | Sentencias CC by year + decision type (c, t, su, a) + 2-digit year. Pattern works; verified C-481-19, C-291-15 live. | ✅ URL pattern confirmed |
| https://www.consejodeestado.gov.co/decisiones_u/ | CE unificación sentencias search/index page. Real radicados like 25000-23-37-000-2014-00507-01. | ⚠️ Index works; article-level fetch needs validation |
| https://www.consejodeestado.gov.co/seccion-cuarta/ | CE Sección Cuarta landing (tax/fiscal section). | ✅ Section page exists |
| https://normograma.dian.gov.co/dian/compilacion/ | DIAN compilation includes CE sentencias and autos by radicado. E.g., `25000-23-37-000-2014-00507-01(23854)_2022CE-SUJ-4-002.htm`. | ✅ Live; canonical radicados verified |

---

## Canonical norm_id shape

Per master §5:

- **Sentencia CC**: `sent.cc.<TYPE>-<NUM>.<YEAR>` where TYPE ∈ {C, T, SU, A} (uppercase).  
  **Verified-real examples** (from `batches.yaml` I1 explicit_list — pre-vetted by the canonicalizer team, safe to paste verbatim): `sent.cc.C-481.2019`, `sent.cc.C-079.2026`, `sent.cc.C-384.2023`, `sent.cc.C-101.2025`, `sent.cc.C-540.2023`. For any sentencia not in that list, verify against the Corte Constitucional relatoria (`https://www.corteconstitucional.gov.co/relatoria/`) before using. Do not invent sentencia numbers.  
  Round-trip: `canonicalize("sent.cc.C-481.2019")` → `"sent.cc.C-481.2019"` ✓

- **Sentencia CE**: `sent.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>`  
  **Verified-real example** (from `batches.yaml` G6 explicit_list): `sent.ce.28920.2025.07.03` (Sección Cuarta unificación, radicado 28920, decision date 2025-07-03).  
  The id is keyed by the **radicado number** plus the **decision date** — NOT by sección. The sección (cuarta, primera, etc.) lives in the body as metadata. Do not encode the sección in the norm_id. Verify each new radicado-number + date pair against the CE relatoria.  
  Round-trip: `canonicalize("sent.ce.28920.2025.07.03")` → `"sent.ce.28920.2025.07.03"` ✓

- **Auto CE**: `auto.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>`  
  **Verified-real examples** (from `batches.yaml` E4 + G6 explicit_lists): `auto.ce.082.2026.04.15`, `auto.ce.084.2026.04.15`, `auto.ce.28920.2024.12.16` (Decreto 1474/2025 IE suspension autos + the I.A. dividendos NCRGO auto).  
  The date in `YYYY.MM.DD` form is **required**; the radicado-only form `auto.ce.082.2026` is NOT a valid canonical id and will be rejected at write time. Read the notification date off the relatoria index.  
  Round-trip: `canonicalize("auto.ce.082.2026.04.15")` → `"auto.ce.082.2026.04.15"` ✓

**Critical:** All sentencia/auto IDs must round-trip cleanly or the writer rejects the row at insert time.

---

## Parsing strategy

### I2 — CC Sentencias on Constitutional Tax Principles

1. **Identify key principles** from ET and Constitution:
   - Art. 363 (legalidad + capacidad económica): C-291/2015, C-913/2003 (referenced in master §4.5 as foundational).
   - Art. 338 (suficiencia + progresividad): C-264/2013, C-748/2009 (referenced).
   - Emergency/reform overrides: C-481/2019, C-079/2026, C-384/2023, C-101/2025, C-540/2023 (from I1 fixture).
2. For each sentencia, fetch from the CC website (URL pattern confirmed):
   - `https://www.corteconstitucional.gov.co/relatoria/<YEAR>/<TYPE>-<NUM>-<YY>.htm`
   - Extract: decision title, date, magnitudes (which articles of the norm under review; constitutional grounds).
   - Split body into introduction, ratio decidendi, and operative part.
3. Emit one `parsed_articles.jsonl` row per sentencia with:
   - `norm_id`: `sent.cc.<TYPE>-<NUM>.<YEAR>` (TYPE uppercase: C, T, SU, A)
   - `norm_type`: `sentencia_cc`
   - `article_key`: "Sentencia C-<NUM>/<YEAR>"
   - `body`: full text of the decision
   - `source_url`: the gov.co URL fetched from
   - `emisor`: "Corte Constitucional"
   - `tema`: "Principios tributarios constitucionales" or "Legalidad tributaria" depending on scope

### I3 — CE Unificación Sentencias (Sección Cuarta)

1. **Identify key unification topics** from tax jurisprudence:
   - Alcance de deducciones (Art. 107 ET): e.g., radicado 25000-23-37-000-2013-00443-01.
   - Corrección de declaraciones y firmeza: radicado 25000-23-37-000-2014-00507-01.
   - Devoluciones de saldos a favor: multiple sentencias (typical K batch).
   - Compensaciones de retención en la fuente: other sentencias.
   - IVA on specific transactions (e.g., arrendamientos): other sentencias.
2. For each, extract the **radicado number** and the **decision date**:
   - Full radicado format: 25000-23-37-000-YYYY-NNNNN-01(index). The canonical id uses only the radicado number (the integer that uniquely identifies the case in the CE relatoria, e.g., `28920`) plus the decision date in `YYYY.MM.DD`.
   - Canonical shape: `sent.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>`.
   - E.g., a Sección Cuarta unificación with radicado number 507 and decision date 2014-08-22 → `sent.ce.507.2014.08.22`. Verify the exact radicado number and date against the CE relatoria.
   - The sección (cuarta, primera, etc.) lives in the body as metadata. Do NOT encode the sección in the norm_id.
3. Fetch from DIAN normograma or CE decisiones_u page.
4. Emit one row per sentencia:
   - `norm_id`: `sent.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>`
   - `norm_type`: `sentencia_ce`
   - `article_key`: "Sentencia de Unificación Radicado 25000-23-37-000-YYYY-NNNNN-01"
   - `body`: full text (ratio decidendi emphasizing the unified doctrine)
   - `source_url`: DIAN or CE URL
   - `emisor`: "Consejo de Estado, Sección Cuarta"
   - `tema`: "Unificación jurisprudencial — Deducciones" (or similar)

### I4 — Autos CE de Suspensión Provisional

1. **Identify live autos**:
   - Auto C-082/2026 y C-084/2026 (Decreto 1474/2025 IE provisions) — mentioned in master §4.5.
   - Other provisional suspension autos on reforms or emergency decrees.
2. For each auto, canonicalize:
   - Extract the auto **radicado number** and the **notification date** from the CE document.
   - Normalize to: `auto.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>`. The date in `YYYY.MM.DD` form is **required**; the radicado-only form is rejected by the writer at insert time.
3. Fetch from CE site (may require search-by-radicado if direct URL not available — see gap #1).
4. Emit one row per auto:
   - `norm_id`: `auto.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>`
   - `norm_type`: `auto_ce`
   - `article_key`: "Auto de Suspensión Provisional — Radicado <RADICADO>"
   - `body`: full text of auto (especially the considerandos and operative part ordering the stay)
   - `source_url`: CE site URL or DIAN normograma if indexed
   - `emisor`: "Consejo de Estado"
   - `tema`: "Medidas cautelares — Suspensión provisional de efectos"

---

## Edge cases observed

- **CC URL year encoding:** The pattern is `https://.../<YEAR>/<TYPE>-<NUM>-<YY>.htm` where YEAR is 4-digit (e.g., 2015) and YY is 2-digit (e.g., 15). Confirmed for C-481-19, C-291-15. Builders must not confuse 19 vs. 2019 in the URL path.
- **CE radicado keying:** Full radicado is 25000-23-37-000-YYYY-NNNNN-01(index). The canonical form uses only the **radicado number** plus the **decision date** in `YYYY.MM.DD` form (e.g., `sent.ce.28920.2025.07.03`). The sección is metadata in the body; it is NOT encoded in the id. Mapping radicado-number → canonical must be 1:1 reversible.
- **Auto numbering:** Autos use sequential numbers (082, 084) within a year or topic. The date in `YYYY.MM.DD` is **required** in the canonical id; the radicado-only form `auto.ce.082.2026` is invalid and rejected at write time.
- **Scraper vs. fixture:** CC scraper works live. CE sentencias scraper works for search but may need hardening for article-level resolution (partial status per master). Autos have no live scraper (gap #1); consider fixture-only path for immediate need.
- **Modificación vs. revocación:** Some sentencias explicitly reverse or limit prior jurisprudencia. Body text must be preserved verbatim; the canonicalizer's Gemini/DeepSeek harness extracts the doctrinal novelty.

---

## Smoke verification

After ingesting I2/I3/I4 rows, run the §6.3 slice-size check restricted to these batches:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path
for bid in ['I2', 'I3', 'I4']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    print(f'  {bid}: {len(norms)} norms')
"
```

Expected:
- **I2**: ≥12 norms (from master appendix A, Min slice size 12).
- **I3**: ≥25 norms.
- **I4**: ≥15 norms (contingent on gap #1 fix or fixture path).

If I4 norms are under-reported, the autos scraper issue (gap #1) is the blocker. Recommend fixture-only path: hand-curate the known autos (C-082/2026, C-084/2026, others) directly into `tests/fixtures/scrapers/consejo_estado/autos/` and re-run.

---

## Dependencies on other briefs

- **Brief 01 (CST)**: No direct dependency, but both I3 (CE Sección Cuarta labor tax precedent) and J1–J4 (CST articles) interpret labor taxation. If J1–J4 populate CST first, I3 corpus may reference CST articles; keep cross-references intact.
- **Brief 11 (Pensional + Salud)**: I3 sentencias may unify doctrines on Ley 100/1993 contributions. If Brief 11 is in progress, coordinate on overlapping radicados.
- **E4 (Decreto 1474 autos)**: I4 depends on E4's autos. If E4 is deferred, I4 is incomplete. Master plan suggests E4 as an acid test for the IE state; I4 should wait for that gate.

---

## Scraper coverage and gaps

**Gap #1 — `auto.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>` missing resolver:**

- **Impact on brief:** I4 autos cannot be live-fetched without CE scraper extension (§7 gap #1). The CE scraper's `_resolve_url` for autos must accept a four-part canonical id `auto.ce.<NUM>.<YEAR>.<MM>.<DD>` and emit a CE search URL keyed by both radicado number and date. The radicado-only form `auto.ce.<NUM>.<YEAR>` is **not** a valid canonical id and will be rejected at write time.
- **Fix path:** Edit `src/lia_graph/scrapers/consejo_estado.py::_resolve_url` to map `auto.ce.<NUM>.<YEAR>.<MM>.<DD>` IDs to CE search-by-radicado RPC or direct URLs.
- **Fixture fallback (recommended):** Add auto text directly to `tests/fixtures/scrapers/consejo_estado/autos/<radicado>.<YYYY>.<MM>.<DD>.html` and configure the scraper to check fixtures first. For a ~20-norm I4 batch, this is faster than scraper extension.

**CE article-level scraper (I3, partial status):**

- The CE scraper resolves search URLs; real article (or in this case, sentencia-level) fetch may return HTML that needs parsing.
- Mitigation: Emit parsed_articles rows with full `body` text (verbatim from the fetched HTML). The builder does not need to slice sentencias by paragrah; Gemini/DeepSeek extract the relevant passages during vigencia extraction.

---

## Verification notes

- **Round-trip validator (§6.1):** Before committing rows, run `lia_graph.canon.canonicalize(norm_id)` on all I2/I3/I4 IDs. Any failure blocks the commit.
- **Source URLs:** Spot-check 5 random rows per batch by fetching the source_url and confirming the body text matches the source.
- **Radicado mapping (I3 only):** Confirm that the abbreviated form (e.g., suj.4.507.2014) is correct by cross-referencing the full radicado in the DIAN normograma.

---

**Last updated:** 2026-04-28  
**Status:** Ready for I2 ingestion (CC scraper confirmed live). I3/I4 conditional on CE scraper hardening or fixture path.
