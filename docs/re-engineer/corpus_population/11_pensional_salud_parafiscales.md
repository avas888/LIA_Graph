# 11. Pensional, Salud, y Parafiscales (Ley 100/1993, Ley 2381/2024, Ley 789/2002)

**Master:** ../corpus_population_plan.md §4.6 (Phase J5–J7)  
**Owner:** unassigned  
**Status:** 🟡 not started  
**Target norm count:** ~80 norms  
**Phase batches affected:** J5, J6, J7

---

## What

This brief covers three interconnected Colombian social protection regimes: (1) **Ley 100/1993** (Sistema General de Pensiones — pensional system with 289 articles across five books covering contributory and non-contributory pensions, disability, and survivorship); (2) **Ley 2381/2024** (reforma pensional, sancionada in 2024 but subject to constitutional suspension as of 2026-04-28; introduces a multi-pillar framework scheduled for 2025-07-01, though current application is limited); and (3) **Ley 789/2002** (employment stimulus and parafiscal reforms covering training contributions to SENA, family compensation fund integration, and occupational hazard insurance). For the canonicalizer, we populate the corpus with articles from the DIAN normograma versions of these leyes, enabling batch resolution for J5 (pensional + Ley 2381 reform articles), J6 (health sub-system of Ley 100), and J7 (parafiscal obligations and related licensing). The DIAN `ley.*` URL resolver already works (fix shipped 2026-04-27), so this brief covers standard article-level parsing with no scraper extension needed.

---

## Source URLs (primary)

| URL | What's there |
|---|---|
| https://normograma.dian.gov.co/dian/compilacion/docs/ley_100_1993.htm | Ley 100/1993 — full compiled text from DIAN (master) |
| https://www.secretariasenado.gov.co/senado/basedoc/ley_0100_1993.html | Ley 100/1993 — Senado master index + pagination (backup/verification) |
| https://www.secretariasenado.gov.co/senado/basedoc/ley_0100_1993_pr001.html | Ley 100/1993 — pagination segment pr001 |
| https://normograma.dian.gov.co/dian/compilacion/docs/ley_2381_2024.htm | Ley 2381/2024 — reforma pensional (DIAN compilation, ~100 articles) |
| https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=246356 | Ley 2381/2024 — Gestor Normativo (official source, canonical reference) |
| https://normograma.dian.gov.co/dian/compilacion/docs/ley_0789_2002.htm | Ley 789/2002 — employment stimulus + parafiscales (DIAN compilation) |
| https://www.secretariasenado.gov.co/senado/basedoc/ley_0789_2002.html | Ley 789/2002 — Senado master |
| https://www.secretariasenado.gov.co/senado/basedoc/ley_0789_2002_pr001.html | Ley 789/2002 — pagination segment pr001 |
| https://www.ugpp.gov.co/normas/ley-no-789-de-diciembre-27-de-2002/ | Ley 789/2002 — UGPP official guidance (parafiscales regulator) |

**Note on Ley 2381/2024:** As of 2026-04-28, the Corte Constitucional suspended entry into force (originally 2025-07-01) and ordered procedural reiteration in Congress. For canonicalizer purposes, ingest the text as-is; the vigencia harness will extract suspension status and effective-date context from the article body and external jurisprudencia sources (handled by Phase I batches, not this brief).

---

## Canonical norm_id shape

`ley.<NUM>.<YEAR>.art.<X>` (lowercase, no padding on year or article number)

**Examples:**
- `ley.100.1993.art.10` — Article 10 of Ley 100/1993 (pensional system definition)
- `ley.100.1993.art.47` — Article 47 of Ley 100/1993 (modified by Ley 2381; kept as-is)
- `ley.2381.2024.art.1` — Article 1 of Ley 2381/2024 (reform framework)
- `ley.789.2002.art.12` — Article 12 of Ley 789/2002 (parafiscales training allocation)

**Round-trip:** All examples canonicalize to themselves. No subsections (like `ley.100.1993.art.10.par.2`) are stored as separate rows; full text with sub-units inline is stored in the article body.

---

## Parsing strategy

1. **Fetch** the DIAN normograma HTML for each ley (preferred source for canonicalizer consistency; use Senado as backup if DIAN link drifts).
2. **Extract articles** using regex or DOM parsing for `<h3>ARTÍCULO <N>. <TITLE></h3>` (or similar Senado/DIAN anchor patterns). Continue text until next article boundary.
3. **Handle multi-book structure** (Ley 100 has 5 books; Ley 2381 is flatter; Ley 789 is single-book):
   - Extract the full article text **as-is** without trying to decompose libro/title/chapter into the norm_id. The norm_id is only `ley.100.1993.art.47`, even if Art. 47 is nested in Libro 2, Título 3, Capítulo 5. The book/chapter context lives in the article body.
   - **Exception:** If a ley explicitly uses two-level article numbering (e.g., "Art. 5-A" or "Art. 2bis"), canonicalize as `ley.<NUM>.<YEAR>.art.5-a` or `ley.<NUM>.<YEAR>.art.2bis` (hyphens and suffixes allowed, lowercase).
4. **Normalize** whitespace, strip HTML, preserve inline structure markers (parágrafo, numeral, literal, inciso) as plain text.
5. **Emit rows** to `parsed_articles.jsonl`:
   ```json
   {
     "norm_id": "ley.<NUM>.<YEAR>.art.<X>",
     "norm_type": "ley_articulo",
     "article_key": "Art. <X> Ley <NUM>/<YEAR>",
     "body": "<full article text with sub-units inline>",
     "source_url": "https://normograma.dian.gov.co/dian/compilacion/docs/ley_<NUM>_<YEAR>.htm (or Senado URL)",
     "fecha_emision": "<YYYY-MM-DD if known, else null>",
     "emisor": "Congreso",
     "tema": "pensional | salud | parafiscales"
   }
   ```
6. **Batch grouping for J5–J7:**
   - **J5** (pensional + reforma): Include all articles from Ley 100/1993 Books 1–3 (pensional system proper) + all Ley 2381/2024 articles. Estimated ~35 norms total (Ley 100 pensional portion + Ley 2381 new framework).
   - **J6** (salud / health): Include Ley 100/1993 Books 4 (health system). Estimated ~25 norms.
   - **J7** (parafiscales + related): Include Ley 789/2002 articles on SENA/family compensation/occupational hazard + any Ley 100 articles governing occupational risk system integration. Estimated ~20 norms.

---

## Edge cases observed

- **Article modifications**: Many Ley 100 articles are marked with inline brackets like "[Modificado por Ley 2381/2024 Art. X]" or "[Derogado por...]". Keep these verbatim in the body; the vigencia harness extracts them.
- **Ley 100 Book structure vs. article numbering**: Ley 100 uses book/title/chapter hierarchy, but article numbers are **flat** (Art. 1–289). The norm_id is only `ley.100.1993.art.47`; the book/chapter context is metadata in the article body text.
- **Ley 2381/2024 suspension**: The law was scheduled for 2025-07-01 entry but Corte Constitucional suspended it as of 2026-04-28. Ingest the text as-published; the suspension and procedural reiteration order are jurisprudential facts (Phase I, brief 10).
- **Cross-reference articles**: Ley 789/2002 frequently references Ley 100/1993 and labor-code norms. These are embedded in article text; do not create separate norm_ids for references.
- **Parafiscal contribution details**: Articles 11–13 of Ley 789 specify rates and carve-outs (e.g., exemptions for new hires). Keep full text; canonicalizer will extract the specific rules.

---

## Smoke verification

After ingesting all Ley 100 + Ley 2381 + Ley 789 rows, run the §6.3 check restricted to Phase J5–J7:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path

for bid in ['J5', 'J6', 'J7']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    expected = {'J5': 30, 'J6': 25, 'J7': 20}
    status = '✓' if len(norms) >= int(expected[bid] * 0.8) else '✗'
    print(f'  {bid}: {len(norms):3d} / {expected[bid]} (target 80%) {status}')
"
```

**Acceptance:** Each batch should report ≥80% of target count (J5≥24, J6≥20, J7≥16). Given the uncertainty around Ley 2381 article count (suspended status may reduce parsed rows), J5 flexibility to 18–20 norms is acceptable.

---

## Dependencies on other briefs

- **Phase J8a–J8c** (DUR 1072/2015 laboral, brief 05): Occupational hazard system integration. Ley 789/2002 cross-references the DUR; coordinate so J8 precedes or parallels this brief.
- **Phase I2–I3** (jurisprudencia, brief 10): Corte Constitucional sentencias on Ley 2381 suspension and validity. Those briefs depend on Ley 2381 articles being parsed so the Court's holdings can reference them. Ingest this brief before / in parallel with brief 10.
- No dependency on **Phase J1–J4** (CST); labor and pensional regimes are separate legal families.

---

**Last verified:** 2026-04-28  
**Note on Ley 2381/2024:** Suspended by Corte Constitucional pending procedural reiteration in Congress. Ingestion proceeds with suspension noted in source metadata; vigencia harness will resolve effective-date status.  
**Ready for assignment:** Yes — fixture-only path (no new scraper required; DIAN resolver operational).
