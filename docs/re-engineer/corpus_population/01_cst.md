# 01. CST (Código Sustantivo del Trabajo)

**Master:** ../corpus_population_plan.md §4.6 (Phase J1–J4)  
**Owner:** unassigned  
**Status:** 🟡 not started  
**Target norm count:** ~170 norms  
**Phase batches affected:** J1, J2, J3, J4

---

## What

The Código Sustantivo del Trabajo (CST) is Colombia's foundational labor code, enacted in 1950 (Law 2363/1950, effective 1951) and consolidated by Decree 2663/1950. It governs individual labor contracts, collective labor relations, social security integration, and dispute resolution across all employment sectors. The CST contains 492 articles organized into five books covering contracts, working conditions, social protection, collective labor law, and administrative procedures. For the canonicalizer, we need to populate the corpus with articles from the specific batches relevant to PYME labor management: contracts (Arts. 22–50), social benefits (Arts. 51–101), working hours (Arts. 158–200), and collective dispute resolution (Arts. 416+). The scraper infrastructure for Senado-hosted codes does not yet exist (Gap #4 in the master plan), so this brief covers the fixture-only path: hand-curated parsing of the Senado HTML pages into per-article `parsed_articles.jsonl` rows.

---

## Source URLs (primary)

| URL | What's there |
|---|---|
| https://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo.html | Master index + landing page (main index, links to pagination) |
| https://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo_pr001.html | Pagination segment pr001 (covers approximately Arts. 1–~50) |
| https://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo_pr002.html | Pagination segment pr002 (covers approximately Arts. ~51–~100) |
| https://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo_pr003.html | Pagination segment pr003 (covers approximately Arts. ~101–~150) |
| https://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo_pr004.html | Pagination segment pr004 (covers approximately Arts. ~151–~250) |
| https://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo_pr008.html | Pagination segment pr008 (covers approximately Arts. ~416+, collective labor) |
| https://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo_pr016.html | Later pagination segment (final articles, including Arts. 490–492 transitive) |

**Note:** Senado uses a "pr" (página representada / represented page) numbering scheme similar to the ET. The exact pagination is not publicly indexed; inspection of each segment reveals article boundaries. Total CST: 492 articles.

---

## Canonical norm_id shape

`cst.art.<N>` (lowercase, no padding)

**Examples:**
- `cst.art.22` — first article of batch J1 (contracts)
- `cst.art.158` — first article of batch J3 (working hours)
- `cst.art.416` — first article of batch J4 (collective conflicts)

**Round-trip:** All examples above canonicalize to themselves via `lia_graph.canon.canonicalize(...)`. No hyphens, no spaces, no subsections at the norm_id level (sub-units like `cst.art.22.par.1` are not ingested as separate rows; the parent article body contains the full text with numbered paragraphs inline).

---

## Parsing strategy

1. **Fetch** each Senado segment (`codigo_sustantivo_trabajo_pr<NN>.html`) via HTTP GET.
2. **Extract article HTML** using an anchor pattern (Senado uses `<h3>ARTÍCULO <N>. <TITLE></h3>` or similar; exact HTML structure to be confirmed during ingest). Parse the heading and body text until the next article boundary (or end of segment).
3. **Normalize text**: clean whitespace, strip HTML tags, preserve structure markers (parágrafo, numeral, literal, inciso) as plain text inside the body.
4. **Emit rows** to `parsed_articles.jsonl` with schema:
   ```json
   {
     "norm_id": "cst.art.<N>",
     "norm_type": "cst_articulo",
     "article_key": "Art. <N> CST",
     "body": "<full normalized article text>",
     "source_url": "https://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo_pr<NN>.html",
     "fecha_emision": null,
     "emisor": "Congreso (1950, Law 2363/Decree 2663)",
     "tema": "labor_contracts | social_benefits | working_hours | collective_labor"
   }
   ```
5. **For batches J1–J4** specifically, filter rows to the expected article ranges:
   - J1: Arts. 22–50 (~29 norms)
   - J2: Arts. 51–101 (~51 norms)
   - J3: Arts. 158–200 (~43 norms)
   - J4: Arts. 416+ (~47+ norms, open-ended to Art. 492)

---

## Edge cases observed

- **Article subdivisions**: Many CST articles are split into numbered paragraphs (parágrafo), numerals (numeral), literals (literal), or incisos (inciso). The Senado HTML encodes these as nested `<p>` or indented plain-text lists. All of this text must be included in the `body` field; **no separate rows are created for sub-units**. The canonicalizer's vigencia harness (Gemini/DeepSeek) extracts sub-numeral-level information from the article body text, not from separate parsed rows.
- **Modifications and derogations**: Many articles carry inline tags like "[Modificado por Ley 50/1990 Art. 5]" or "[Derogado por Ley 789/2002]" embedded in the article text. Keep these as-is in the body; the vigencia prompt will detect and parse them.
- **Cross-page article breaks**: Occasionally an article straddles two pagination segments (e.g., Art. 50 might span pr001–pr002). Concatenate text from both pages to emit one complete row with the article's full text.
- **Titles and article references**: Senado includes article titles (e.g., "ARTÍCULO 22. DEFINICIÓN DE CONTRATO DE TRABAJO."). Include the title in the body for context; the norm_id uniquely identifies the article number.

---

## Smoke verification

After ingesting all CST rows, run the master plan's §6.3 slice-size check restricted to Phase J1–J4:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path

for bid in ['J1', 'J2', 'J3', 'J4']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    expected = {'J1': 25, 'J2': 40, 'J3': 35, 'J4': 60}
    status = '✓' if len(norms) >= int(expected[bid] * 0.8) else '✗'
    print(f'  {bid}: {len(norms):3d} / {expected[bid]} (target 80%) {status}')
"
```

**Acceptance:** Each batch should report ≥80% of target count (J1≥20, J2≥32, J3≥28, J4≥48).

---

## Dependencies on other briefs

None — CST is self-contained. However, **Phase J8a–J8c** (DUR 1072/2015 laboral, brief 05) shares the source URL pattern with Phase E6 (same DUR, renta focus). Coordinate ingest order so E6 is completed first (DUR is fetched once, parsed once); J8 reuses the same rows. This brief (CST) is independent and can be ingested in any order relative to J5–J8.

---

**Last verified:** 2026-04-28  
**Ready for assignment:** Yes — awaiting fixture-only parsing of Senado HTML segments.
