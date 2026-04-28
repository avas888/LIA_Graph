# 06. Decretos legislativos COVID + Emergencia económica

**Master:** ../corpus_population_plan.md §4.1 (E5)  
**Owner:** unassigned  
**Status:** 🟡 not started  
**Target norm count:** ~30  
**Phase batches affected:** E5

---

## What

During the COVID-19 pandemic (2020) and subsequent emergency economic period, the Colombian executive issued a series of **decretos legislativos** (legislative decrees) under constitutional emergency powers (Arts. 215, 337, 338 of the Constitución Política de Colombia). These decrees carried the force of law and were later reviewed by the Constitutional Court and Congress.

The decretos legislativos relevant to the tax and labor regimes include:

| Decree | Year | Theme | Status |
|---|---|---|---|
| Decreto Legislativo 417 | 2020 | Declaration of the state of economic emergency (COVID response) | Foundational; many subsequent decrees issued under this authority |
| Decreto Legislativo 444 | 2020 | Alivios tributarios y financieros (tax and financial relief) | Issued under emergency; some articles sustained, others modified |
| Decreto Legislativo 538 | 2020 | Medidas de protección en salud laboral (occupational health — COVID protocols) | Sustained; cross-references DUR 1072 SST section |
| Decreto Legislativo 568 | 2020 | Alivios contributivos y pensionales (pension contribution relief) | **Partially declared unconstitutional by CC** (see Risk #8 below) |
| Decreto Legislativo 658 | 2020 | Alivios fiscales adicionales (additional tax relief — CREE, GMF reductions) | Modified by subsequent reforms |
| Decreto Legislativo 678 | 2020 | Alivios para deudores tributarios (relief for tax debtors — payment plans, discounts) | Partially superseded by Decreto 1474/2025 |
| Decreto Legislativo 682 | 2020 | Temporalidad del IVA (temporary IVA rate reduction) | Expired; historical reference for NIIF-fiscal conciliation |
| Decreto Legislativo 770 | 2020 | PAEF — Programa de Apoyo al Empleo Formal (formal employment support) | Sustained; payroll tax credits, subsidies |
| Decreto Legislativo 772 | 2020 | Alivios para deudores de obligaciones tributarias (extended relief for tax debtors) | Sustained; still in force |
| Decreto Legislativo 803 | 2020 | Medidas de reactivación económica (economic reactivation measures) | Sustained; includes labor protections |

The canonicalizer Phase E5 batch covers **any decretos legislativos issued under state of economic emergency**, not limited to the COVID set above. The expectation is ~30 unique norm articles that feed the E5 batch filter.

---

## Source URLs (primary)

| URL | Coverage | Status |
|---|---|---|
| `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_legislativo_<NUM>_<YEAR>.htm` | Individual decreto legislativo (DIAN normograma pattern) | Primary source; **requires scraper extension** (see Gap #3 note below) |
| `https://www.secretariasenado.gov.co/senado/basedoc/decreto_legislativo_<NUM>_<YEAR>.html` | Legislative archive version (Senado) | Fallback; may contain historical or superseded text |
| Constitutional Court dockets | CC ruling on each decree's constitutionality | Reference (not ingested directly); informs the vigencia harness |

**URL pattern note:** The DIAN normograma pattern for decretos legislativos is:
```
https://normograma.dian.gov.co/dian/compilacion/docs/decreto_legislativo_<NUM>_<YEAR>.htm
```

The scraper currently recognizes `decreto_<NUM>_<YEAR>.htm` URL filenames. Decretos legislativos use the URL filename `decreto_legislativo_<NUM>_<YEAR>.htm`. The scraper needs an explicit case that detects when the source decree was issued under emergencia económica and rewrites the URL filename accordingly — but the canonical norm_id stays as plain `decreto.<NUM>.<YEAR>.art.<X>`. The "legislativo" character lives in the article body and the URL filename, not in the canonical id. See **Gap #3** in master plan §7.

---

## Canonical norm_id shape

```
decreto.<NUM>.<YEAR>.art.<X>
```

Where:
- `<NUM>` = decree number (e.g., 417, 538, 682)
- `<YEAR>` = year of issuance (e.g., 2020)
- `<X>` = article number within the decreto (e.g., 1, 5, 12)

The canonicalizer treats decretos legislativos as ordinary decretos. The "legislativo" character (issued under emergencia económica) is metadata that lives in the article body and the source-URL filename pattern (`decreto_legislativo_<NUM>_<YEAR>.htm`), but it does NOT appear as a segment in the canonical norm_id.

**Verified-real decreto numbers** (from `batches.yaml` E5 regex `^decreto\.(417|444|535|568|573|772)\.2020`):

- `decreto.417.2020` — Decreto Legislativo 417/2020 (declaratoria de emergencia económica, social y ecológica)
- `decreto.444.2020` — Decreto Legislativo 444/2020
- `decreto.535.2020` — Decreto Legislativo 535/2020
- `decreto.568.2020` — Decreto Legislativo 568/2020
- `decreto.573.2020` — Decreto Legislativo 573/2020
- `decreto.772.2020` — Decreto Legislativo 772/2020

**Article-level shape** (use the article number as printed in the source — read the actual article headings off DIAN normograma's `decreto_legislativo_<NUM>_2020.htm`):

```
decreto.<NUM>.2020.art.<X>
```

Do not invent article numbers. The decreto numbers above are pre-vetted by the canonicalizer team; the per-article numbering is the expert's job to read from each source.

**Round-trip rule:** Every `norm_id` must round-trip cleanly through `lia_graph.canon.canonicalize(...)`:

```python
from lia_graph.canon import canonicalize
example = "decreto.682.2020.art.<paste-real-article-number>"
assert canonicalize(example) == example, f"shape error in {example!r}"
```

---

## Parsing strategy

1. **Identify target decretos:** Use the table in §1 above as the master list. Verify each is actually issued under estado de emergencia (not a regular decreto) by checking the opening text ("Considerando que…", "El Presidente de la República de Colombia… en ejercicio de las facultades extraordinarias…", citation of Art. 215, 337, or 338 of the Constitution).

2. **Fetch source:** For each decreto, retrieve the DIAN normograma URL (`decreto_legislativo_<NUM>_<YEAR>.htm`). If the DIAN URL is unavailable (404 or 503), fall back to the Senado legislative base.

3. **Extract articles:** For each article within the decreto, identify:
   - **Article number** (`<X>`): extract the `Art. N` marker (e.g., "Art. 1", "Art. 12").
   - **Article body:** verbatim text, including paragraphs, conditions, effective dates, and any transition rules.
   - **Derogation/modification notes:** if the article is marked "derogado", "modificado", or "suspendido" (especially by a subsequent decreto or CC ruling), include the note verbatim in the body. The vigencia harness will extract the normative status.

4. **Handle Constitutional Court rulings:** If a decreto legislativo or a specific article was declared **inconstitucional** by the CC, the body should note the sentence (e.g., "Declared unconstitutional by Sentencia C-XXX/20XX"). The canonicalizer's vigencia phase will handle the constitutional status; the parser's job is to capture the raw text.

5. **Emit parsed_articles.jsonl rows:** One row per article:
   ```json
   {
     "norm_id": "decreto.<NUM>.<YEAR>.art.<X>",
     "norm_type": "decreto_articulo",
     "article_key": "Art. <X> Decreto Legislativo <NUM>/2020",
     "body": "<full verbatim article text including any modification notes>",
     "source_url": "<URL of the DIAN normograma or Senado page>",
     "fecha_emision": "2020-<MM>-<DD>",  (if known; else null)
     "emisor": "Presidencia",
     "tema": "decreto_legislativo_covid"
   }
   ```

---

## Edge cases observed

- **Multiple derogations in sequence:** Some decretos legislativos (e.g., DL 678, 772) were superseded by later decretos or by Decreto 1474/2025. The baseline text in DUR 1072 or ET may reference them as derogated. **Action:** Ingest the decreto legislativo article verbatim as the norm; the vigencia harness will identify derogation via Gemini/DeepSeek. Do not manually edit the body to say "this is no longer in force"—that's the canonicalizer's job.

- **Decree 568 (pension relief) — partial unconstitutionality:** The Constitutional Court issued **Sentencia C-…/2020** declaring portions of DL 568 unconstitutional. The source text in the DIAN normograma may include a footnote like "Declarado inconstitucional por Sentencia C-XXX/20XX". **Action:** Preserve the note in the body; mark `tema: "Laboral"` to flag the pension context.

- **Effective date / retroactivity:** Many decretos legislativos included retroactive or temporary effective dates (e.g., "vigencia desde el 1 de enero de 2020", "vigencia temporal hasta el 30 de junio de 2020"). These dates are part of the normative content and should be included in the body verbatim.

- **Cross-references to DUR articles:** Several decretos legislativos modify or suspend specific DUR articles (e.g., DL 538 amends DUR 1072 Libro 3 SST articles). When parsing the legislativo, include the reference as-is in the body; downstream retrieval can correlate DL articles with DUR articles via the canonicalizer's unified graph.

---

## Smoke verification

After ingesting decretos legislativos COVID into `parsed_articles.jsonl`, run the phase E5 slice-size check:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path

norms = _resolve_batch_input_set(
    batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
    batch_id='E5',
    corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
    limit=None,
)
print(f'E5 (decretos legislativos COVID): {len(norms)} norms')
"
```

**Acceptance threshold:** Per master plan Appendix A, E5 expects min 20 norms (regex filter). **Target:** ~30 articles total across the listed decretos legislativos.

---

## Dependencies on other briefs

- **Upstream:** None. Decretos legislativos are standalone sources.

- **Downstream:**
  - **Brief 04** (DUR 1625 Libro 3): Some DL articles (e.g., DL 682 on temporary IVA) modify DUR 1625 provisions. No blocking dependency; filtering is independent. Cross-reference via `tema` if helpful.
  - **Brief 05** (DUR 1072): DL 538 (occupational health) cross-references DUR 1072 Libro 3 SST articles. No blocking dependency.
  - **Brief 10** (Jurisprudencia CC): Constitutional Court rulings on decretos legislativos (e.g., C-…/2020 on DL 568) feed Phase I2. No blocking dependency; the CC ruling is ingested separately as a sentencia.cc norm.

---

## Blocked by: Gap #3 (Scraper extension)

**⚠️ CRITICAL BLOCKER:** The DIAN normograma scraper resolves `decreto.<NUM>.<YEAR>` ids by mapping to the URL `decreto_<NUM>_<YEAR>.htm`. For decretos legislativos the URL filename is `decreto_legislativo_<NUM>_<YEAR>.htm`. The scraper needs an explicit case that detects whether the source decree is a "decreto legislativo" (issued under emergencia económica) and rewrites the URL accordingly — but the canonical norm_id stays as `decreto.<NUM>.<YEAR>` regardless. The "legislativo" character lives in the article body and the source-URL metadata, not the id.

**Fix (master plan §7, Gap #3):**
```python
# In dian_normograma.py::_resolve_url
# The canonical id is decree.<NUM>.<YEAR>
# If the decreto is a legislativo, the source URL filename is decreto_legislativo_<NUM>_<YEAR>.htm
# The scraper needs to detect the legislativo character (in article metadata or batch config)
# and rewrite the URL accordingly:
if is_decreto_legislativo(num, year):
    return f"https://normograma.dian.gov.co/dian/compilacion/docs/decreto_legislativo_{num}_{year}.htm"
else:
    return f"https://normograma.dian.gov.co/dian/compilacion/docs/decreto_{num}_{year}.htm"
```

**Fixture fallback (if scraper extension is deferred):** Drop the raw HTML/text of each decreto legislativo into `tests/fixtures/scrapers/dian/decreto_legislativo_<NUM>_<YEAR>.htm` so the canonicalizer can run in fixture-only mode. Pragmatic for initial ingestion; live-fetch can be re-enabled once the scraper is extended.

---

## Schema validation before commit

Run the round-trip check from master plan §6.1:

```bash
PYTHONPATH=src:. uv run python -c "
import json
from lia_graph.canon import canonicalize
with open('artifacts/parsed_articles.jsonl') as f:
    for i, line in enumerate(f, 1):
        row = json.loads(line)
        nid = row['norm_id']
        canon = canonicalize(nid)
        assert canon == nid, f'row {i}: {nid!r} → {canon!r}'
print('OK — all norm_ids round-trip cleanly')
"
```

---

## Notes for the ingestion expert

- **Decreto list completeness:** The table in §1 lists ~10 key decretos legislativos. Search the DIAN normograma index for `decreto_legislativo_*` URL filenames to verify no others are relevant (e.g., any issued in 2021 under lingering emergency powers). The E5 batch matches on the canonical id pattern `^decreto\.(417|444|535|568|573|772)\.2020` (plain decreto, no `.legislativo` segment), so completeness in the parsed-articles rows directly drives slice resolution.

- **Constitutional status:** DL 568 (and possibly others) had portions struck down by the CC. The source text in DIAN normograma may include a footnote or the body may say "suspendido" or "derogado". Preserve that text verbatim; do not suppress articles that were ruled unconstitutional. The vigencia harness will flag the constitutional status.

- **DIAN normograma URL reliability:** The decretos legislativos section of the DIAN normograma may be less frequently updated than the base DUR or ET pages. If the DIAN URL returns 404, the Senado legislative base is an acceptable fallback.

- **Commit strategy:** Per master plan §10.5, commit as `corpus(covid_decretos): ingest 30 articles from 10 decretos legislativos 2020 (E5)`. One commit makes it easy to revert if feedback indicates parsing errors.

- **Scraper dependency:** This brief is **blocked by Gap #3**. Until the DIAN scraper is extended or the fixture fallback is populated, the canonicalizer cannot run Phase E5 end-to-end. Coordinate with the engineering team to prioritize the scraper fix or confirm fixture-only approach before ingestion.

---

## Estimated effort

- **Decreto list verification:** ~30 minutes (confirm each decreto is legislative, issued under emergency authority)
- **Data extraction:** ~2 hours (fetch each decree, extract articles)
- **norm_id canonicalization + validation:** ~30 minutes
- **Scraper extension OR fixture population:** ~1–2 hours (depends on path: live scraper or fixture-only)
- **Round-trip testing + smoke verification:** ~30 minutes
- **Total:** ~5–6 hours (including scraper work)

**Note:** If the scraper extension is deferred and fixture-only path is chosen, effort drops to ~3 hours (corpus work only).
