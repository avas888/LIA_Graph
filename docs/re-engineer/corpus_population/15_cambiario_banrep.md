# 15. Cambiario BanRep — Resolución Externa 1/2018 + DCIN-83 (gap-fill)

**Master:** ../corpus_population_plan.md §4.7 (Phase K)
**Owner:** unassigned
**Status:** 🟡 not started
**Target norm count:** ~55 (K1: ~25 articles · K2: ~30 numerales)
**Phase batches affected:** K1, K2 (gap-fill; K3 + K4 already covered by Brief 12)

---

## What

Brief 12 (already delivered) covered Ley 222/1995 (S.A.), Ley 1258/2008 (S.A.S.), and Código de Comercio Libro II — the K3 + K4 portions of Phase K. The first-pass campaign smoke check on 2026-04-28 found:

| Batch | Status after Brief 12 | Reason |
|---|---|---|
| K1 (Res Externa 1/2018 BanRep) | MISS (0 norms) | Expert flagged BanRep retrieval as outside delivery — Gap #5 |
| K2 (DCIN-83 Manual Cambiario) | MISS (0 norms) | Same — Gap #5 |
| K3 (Código de Comercio sociedades) | PASS (315/48 norms) | Brief 12 covered it |
| K4 (Ley 222 + Ley 1258) | PASS (2/2 explicit_list norms) | Brief 12 covered it |

This brief fills K1 + K2 only. Brief 15 is fixture-only — there is no live BanRep scraper (Gap #5) and writing one would be expensive given BanRep's site is sparsely structured. Hand-curated parsed_articles entries are the recommended path.

---

## Source URLs (primary)

| URL | What | Status |
|---|---|---|
| https://www.banrep.gov.co/es/normatividad/resolucion-externa-1-2018 | Res Ext 1/2018 main landing | ✅ Live |
| https://www.banrep.gov.co/es/normatividad/compendios/resolucion-externa-1-2018 | BanRep compendium (consolidated text + amendments) | ✅ Live |
| https://www.banrep.gov.co/sites/default/files/reglamentacion/compendio-res-ext-1-de-2018.pdf | Direct PDF compendium | ✅ Live |
| https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_banrepublica_jd-0001_2018.htm | DIAN-mirrored Res Ext 1/2018 (often more stable than BanRep) | ✅ Live; verified |
| https://www.banrep.gov.co/es/normatividad | BanRep normatividad index — search for DCIN-83 | ✅ Live |

**Recommendation:** for K1, prefer the BanRep compendium URL (consolidated, current). DIAN's mirror is acceptable as a fallback. For K2, only BanRep hosts DCIN-83.

---

## Canonical norm_id shape

Per master plan §5:

- **Resolución BanRep:** `res.banrep.<NUM>.<YEAR>.art.<X>`
  Example: `res.banrep.1.2018.art.5` (Res Ext 1/2018, article 5).
  Sub-paragraphs: `res.banrep.1.2018.art.5.par.1`.
  Round-trip: `canonicalize("res.banrep.1.2018.art.5")` → `"res.banrep.1.2018.art.5"` ✓

- **DCIN-83:** `dcin.83.cap.<C>.num.<N>`
  Example: `dcin.83.cap.5.num.3` (DCIN-83, chapter 5, numeral 3).
  No year segment (DCIN-83 is a living manual updated by amendment).
  Round-trip: `canonicalize("dcin.83.cap.5.num.3")` → `"dcin.83.cap.5.num.3"` ✓

**Critical:** both forms must round-trip cleanly through `lia_graph.canon.canonicalize` or the writer rejects the row at insert time.

**BanRep articulación.** The "1" between `banrep.` and `.2018` is the resolution number; the article number after `.art.` is the per-article identifier. Article numbers are integers as printed (1, 2, 3, …) — do not invent suffixes that don't appear in the source.

---

## Parsing strategy

### K1 — Resolución Externa 1/2018 JDBR

1. **Fetch source.** Prefer the BanRep compendium (consolidated current text). The DIAN mirror is a fallback.
2. **Identify articles.** Res Ext 1/2018 has a defined article structure (Arts. 1–50ish in the consolidated version).
   - Split by `ARTÍCULO N.` headings.
   - Each article gets its own row.
3. **Handle amendments.** The resolución has been amended many times; the BanRep compendium folds amendments inline. If you see `[Modificado por Res Externa N de YYYY]` notes, keep them verbatim — the vigencia harness extracts modification status downstream.
4. **Emit one row per article + one parent row** per the master schema:
   ```json
   {
     "norm_id": "res.banrep.1.2018.art.<N>",
     "norm_type": "res_articulo",
     "article_key": "Art. <N> Res. Externa 1/2018 BanRep",
     "body": "[CITA: Resolución BanRep 1 de 2018, Artículo <N>]\n\n<verbatim article text>",
     "source_url": "https://www.banrep.gov.co/es/normatividad/compendios/resolucion-externa-1-2018 OR DIAN mirror",
     "fecha_emision": "2018-05-25",
     "emisor": "Banco de la República (Junta Directiva)",
     "tema": "regimen_cambios_internacionales"
   }
   ```
   Plus parent: `res.banrep.1.2018` with `[CITA: Resolución BanRep 1 de 2018]` body.

### K2 — DCIN-83 Manual Cambiario

1. **Fetch source.** From BanRep's normatividad index.
2. **Understand structure.** DCIN-83 is organized by:
   - Capítulos (chapters) — typical numbering `Cap. 1` through `Cap. ~10`.
   - Numerales (numerals) — subdivisions within each chapter.
3. **For each numeral, capture:**
   - Chapter number (`<C>`).
   - Numeral number (`<N>`) — integer only; if BanRep uses dotted form like `5.3`, treat the integer prefix as the numeral and store the full identifier in `article_key`.
   - Full numeral text.
4. **Emit one row per numeral:**
   ```json
   {
     "norm_id": "dcin.83.cap.<C>.num.<N>",
     "norm_type": "dcin_numeral",
     "article_key": "Capítulo <C>, Numeral <full-numeral-id-as-printed>",
     "body": "[CITA: DCIN-83 capítulo <C> numeral <N>]\n\n<verbatim numeral text>",
     "source_url": "https://www.banrep.gov.co/...",
     "fecha_emision": null,
     "emisor": "Banco de la República (Departamento de Cambios Internacionales)",
     "tema": "manual_operaciones_cambio"
   }
   ```

The ingester `scripts/canonicalizer/ingest_expert_packet.py` doesn't yet have a `handle_brief_15` — adding one is a 50-line patch (mirror the brief 12 CCo handler with `res.banrep.*` and `dcin.*` shapes). The ingester change should land in the same commit as the brief content.

---

## Edge cases observed

- **DCIN-83 numerals with sub-numerals.** Numeral 5.3 might have items 5.3.1, 5.3.2. Treat each as a separate row **only if** BanRep numbers them as independent numerales (i.e., the source has separate `5.3.1` and `5.3.2` headings). Otherwise keep them inside the parent numeral's body. Note: `dcin.83.cap.5.num.3.<sub>` is **not** a valid canonical form (the canon regex only accepts `cap.<C>.num.<N>`); for sub-numerals, use a sequential integer in `num.<N>` and store the printed identifier (e.g. `5.3.1`) in `article_key`.
- **Capítulo with sub-secciones.** Some chapters have sub-sections (e.g., "Capítulo 5 — Sección 2"). Don't encode the sección in the canonical id; keep it in `article_key` and body.
- **K1 amendment-only resoluciones.** BanRep periodically issues "Resolución Externa N de YYYY" that **amends** Res Externa 1/2018. Those amendment-resoluciones are NOT in scope for this brief — only the consolidated Res Externa 1/2018 itself is. The amendments live as inline notes in the compendium body.
- **PDF-only sources.** K1's compendium is often PDF-only. The expert delivers the PDF URL as `source_url` and copies text into the markdown body.

---

## Smoke verification

After ingest, run:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path
for bid in ['K1', 'K2']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    print(f'{bid}: {len(norms)} norms')
"
```

**Expected:** K1 ≥ 20 (≥80% of brief target 25), K2 ≥ 25 (≥80% of brief target 30).

---

## Dependencies on other briefs

- **Upstream:** Brief 12 already delivered K3 + K4. No upstream blockers for K1 + K2.
- **Downstream:** None. Phase K is the final corpus-population phase.

---

## Scraper coverage and gaps

**Gap #5 (master plan §7) — BanRep scraper:**

- **Impact:** K1 + K2 cannot be live-fetched without a new BanRep scraper.
- **Fix path:** Implement `src/lia_graph/scrapers/banrep.py`. Complexity: BanRep's site is less structured than DIAN or Senado; articles may not have clean anchor syntax.
- **Recommended fixture fallback (this brief assumes this path):** hand-curate K1 + K2 rows. BanRep moves slowly on regulation; a fixture-only path with periodic spot-checks is pragmatic and reduces risk of scraper rot. Fixtures live in `tests/fixtures/scrapers/banrep/res_ext_1_2018/` and `tests/fixtures/scrapers/banrep/dcin_83/`.

---

**Last verified:** 2026-04-28
**Status:** Ready for assignment. Fixture-only path recommended (no scraper extension required for this brief).
