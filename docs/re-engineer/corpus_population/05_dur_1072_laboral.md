# 05. DUR 1072/2015 — Labor (Laboral + SST)

**Master:** ../corpus_population_plan.md §4.1 (E6a–E6c + J8a–J8c)  
**Owner:** unassigned  
**Status:** 🟡 not started  
**Target norm count:** ~250  
**Phase batches affected:** E6a, E6b, E6c, J8a, J8b, J8c

---

## What

Decreto Único Reglamentario 1072 of 2015 (issued by the Ministry of Labor) is the Colombian unified regulatory decree consolidating labor law, pension regulation, occupational health and safety (SST — Sistema de Gestión de Seguridad y Salud en el Trabajo), and administrative procedural rules for the labor portfolio.

The decree is structured in three **libros** (books), each with **partes** (sections), **títulos** (titles), and **artículos** (articles):

- **Libro 1** — Estructura del Sector Trabajo (~50 articles): administrative organization of the Ministry of Labor, regulatory branches, decentralized entities.
- **Libro 2** — Régimen reglamentario del trabajo (~200 articles): individual labor contracts, collective agreements, working time, vacation, temporary work, special contracts (domestic service, apprenticeship), labor dispute resolution (conciliation, arbitration), pension-linked deductions, occupational risk insurance (ARL).
- **Libro 3** — Sistema de Gestión de Seguridad y Salud en el Trabajo (SST, ~100 articles): workplace hazard identification, prevention plans, health committees (COPASST), emergency response, incident reporting, occupational risk management, employer and worker duties.

This decree has been heavily modified since 2015; key updates include:
- Decree 472/2015 (partial derogations of the original text, some articles of Libro 1 and procedural sections)
- Decree 1477/2014 (Table of Occupational Diseases — informs SST provisions)
- Resolution 0312/2019 (Standards for occupational health management systems — applies to Libro 3)
- Decree 0171/2024 and subsequent modifications (recent labor regime updates)

For the canonicalizer, DUR 1072 feeds **two phases in parallel**: **Phase E6** (reglamentario suite) and **Phase J8** (labor regime). The parsed rows are ingested once; batch resolution references filter by the same canonical ids.

**DUR 1072 article numbering:** DUR 1072/2015 numbers articles with dotted decimals (e.g., "Artículo 2.2.4.6.42") in the source. The leading `2.` corresponds to libro 2 (régimen laboral); `2.2.4.*` corresponds to riesgos laborales (Sistema de Riesgos); `2.2.5.*` to SST. Use the printed article number verbatim; do not encode the libro/parte/título as separate segments in the canonical id.

---

## Source URLs (primary)

| URL | Coverage | Status |
|---|---|---|
| `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1072_2015.htm` | DUR 1072 full text (all 3 libros) | Primary (DIAN normograma); **to be verified** — 404 observed during brief research |
| `https://www.mintrabajo.gov.co/documents/20147/.../DUR+Decreto+1072+2015+Actualizado.pdf` | MinTrabajo official PDF (libro 1-3) | Authoritative; structure varies by update cycle |
| `https://www.secretariasenado.gov.co/senado/basedoc/decreto_1072_2015.html` | Senado legislative base (compilado) | Fallback if DIAN unreachable |

**Note:** The master plan (§4.1, E6) confirms the DIAN normograma scraper already handles `decreto.<NUM>.<YEAR>.*` URL patterns. If the DIAN URL is inactive, the MinTrabajo PDF is the authoritative current source; the Secretaría Senado version is a legislative archive (may contain historical versions).

---

## Canonical norm_id shape

```
decreto.1072.2015.art.<dotted-decimal-as-printed>
```

DUR 1072 numbers articles with dotted decimals in the source (e.g., "Artículo 2.2.4.6.42"). Use that number verbatim. The libro / parte / título / capítulo structure is already encoded in the dotted decimal; do NOT add separate libro/parte/titulo segments to the id.

**Shape pattern (use the article number AS PRINTED in the source):**

```
decreto.1072.2015.art.<dotted-decimal>              (any DUR 1072 article)
decreto.1072.2015.art.2.2.<dotted-decimal>          (riesgos + SST, the YAML E6a/E6b/E6c + J8a/J8b/J8c prefixes)
```

The dotted decimal in DUR 1072 already encodes libro / parte / título / capítulo. As an illustrative-only mapping shape (not a verified article — replace with the actual number you read from the source): an article printed as "Artículo `<N1>.<N2>.<N3>.<N4>.<N5>`" maps to `decreto.1072.2015.art.<N1>.<N2>.<N3>.<N4>.<N5>`. The leading `2.` segment indicates libro 2; per the YAML, `2.2.4.*` is the riesgos block and `2.2.5.*` is SST.

**To get real article numbers:** open the DIAN normograma DUR 1072 page (or MinTrabajo's published DUR 1072) and read the article headings. Do not invent ids.

**Round-trip rule:** Every `norm_id` must round-trip cleanly through `lia_graph.canon.canonicalize(...)` returning the same string. Validate before ingesting into `parsed_articles.jsonl`:

```python
from lia_graph.canon import canonicalize
# Substitute a real article number you actually plan to ingest:
example = "decreto.1072.2015.art.<paste-real-dotted-decimal-here>"
assert canonicalize(example) == example, f"shape error in {example!r}"
```

---

## Parsing strategy

1. **Fetch source:** Retrieve the authoritative DUR 1072 text (DIAN normograma preferred; MinTrabajo PDF as fallback if URL is inactive).

2. **Identify libro boundaries:** Extract the three **libros** as separate sections. If the source uses explicit heading anchors (e.g., "LIBRO PRIMERO — Estructura del Sector Trabajo"), split the text at those markers.

3. **Map parte and título hierarchy:** Within each libro, identify the **partes** (often numbered I, II, III… in Roman numerals or as "PART 1, PART 2…" in headings) and **títulos** (subdivisions within partes, often as "CHAPTER 1, CHAPTER 2…" or explicit "Título I, Título II…").
   - **Note:** The source may not use explicit "Parte" and "Título" labels for every subdivision. Use heading heuristics (ALL-CAPS section heads) and article-number continuity to infer boundaries.
   - If a clear heading is absent, assign `parte` and `titulo` sequentially within the libro, with a comment in the ingestion notes (not in the parsed_articles row).

4. **Extract articles:** For each article, identify:
   - **Article number** (`art`): extract the `Art. N` marker (e.g., "Art. 1", "Art. 45-1").
   - **Article body:** verbatim text from the source, including introductory text, paragraphs, sub-numbered lists, and any modification notes (e.g., "modificado por Decreto 472/2015").
   - **Normative status:** if the article is explicitly marked as derogated or suspended (e.g., "derogado por…"), include that notation in the body as raw text; the canonicalizer's vigencia harness extracts it via Gemini/DeepSeek, not via the parser.

5. **Emit parsed_articles.jsonl rows:** For each article, add one row with the schema:
   ```json
   {
     "norm_id": "decreto.1072.2015.art.<dotted-decimal-as-printed>",
     "norm_type": "decreto_articulo",
     "article_key": "Art. <dotted-decimal> DUR 1072/2015",
     "body": "<full verbatim article text>",
     "source_url": "<URL of the page or PDF the body came from>",
     "fecha_emision": "2015-05-26",
     "emisor": "MinTrabajo",
     "tema": "Laboral | SST"  (optional)
   }
   ```

---

## Edge cases observed

- **Libro 3 SST updates:** The SST section (Libro 3) has been substantially modified by Resolution 0312/2019 and subsequent decrees. The baseline text is DUR 1072, but many articles reference or are superseded by the resolution. **Action:** Ingest the DUR 1072 article verbatim (as the baseline norm); do not conflate with Resolution 0312/2019 articles. Cross-reference in the tema field if helpful.

- **Parte and Título inference:** If the source does not use explicit heading anchors for "Parte" and "Título", the parser must infer them from structural heuristics (section headers in all-caps, article-number continuity gaps, or indentation changes). Document the heuristic used in the ingestion notes; ambiguity here can cause `norm_id` misclassification.

- **Split articles:** Some articles are numbered with a main number and a hyphen-digit sub-suffix (e.g., a hypothetical "Art. X.Y.Z-1"). The canonical form keeps the hyphen: `decreto.1072.2015.art.<X.Y.Z>-1`. Use the printed sub-suffix verbatim; do not invent suffixes that aren't in the source. The canonicalizer accepts hyphen-digit (`-1`/`-2`) but **not** hyphen-letter (`-A`/`-B`).

- **Histórico articles and derogations:** Several articles of DUR 1072 were derogated by Decree 472/2015 and other subsequent norms. The source text may include a "derogado por Decreto 472/2015" note within the article or as a footer. **Action:** Include the full note verbatim in the `body` field; the vigencia harness will parse the derogation marker.

- **Procedural articles spanning labor + pension domains:** Libro 2 includes articles on labor dispute resolution, pension-linked deductions, and occupational risk insurance. These straddle labor + social security. **Action:** Tag all as `tema: "Laboral"` in the parsed row; the canonicalizer's phase J filters (J8 for labor, J5/J6 for pensional) will disambiguate downstream.

---

## Smoke verification

After ingesting DUR 1072 into `parsed_articles.jsonl`, run the phase-specific slice-size check (from master plan §6.3):

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path

for bid in ['E6a', 'E6b', 'E6c']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    print(f'  {bid}: {len(norms)} norms')
"
```

**Acceptance threshold:** Per the master plan Appendix A:
- **E6a:** min 60 norms (Libro 1)
- **E6b:** min 80 norms (Libro 2)
- **E6c:** min 80 norms (Libro 3 SST)
- **J8a–J8c (combined):** min 200 norms (same rows as E6a–c, filtered by J batches)

**Total expected:** ~250 across E6 + J8. Actual may vary ±20% depending on the depth of parte/título subdivision in the source.

---

## Dependencies on other briefs

- **Internal:** The same parsed_articles.jsonl rows feed both Phase E6 and Phase J8; ingestion occurs once. The batches resolve independently, but the canonical ids must satisfy both filter sets.

- **Upstream:** None. DUR 1072 is a standalone source.

- **Downstream:** 
  - **Brief 07** (Resoluciones DIAN): may reference DUR 1072 articles in SST contexts (e.g., Res. 0312/2019 cross-references DUR 1072 Libro 3). No blocking dependency; each brief is independently ingested.
  - **Brief 11** (Pensional + Ley 100/1993): Libro 2 of DUR 1072 contains pension deduction rules that coordinate with Ley 100/1993. Parsing order does not matter (independent filters), but cross-reference is recommended in `tema` fields for retrieval richness.

---

## Schema validation before commit

Before pushing parsed_articles rows to the corpus, run the round-trip check from master plan §6.1:

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

If any rows fail the round-trip check, the writer will reject them at insert time and the campaign will stall.

---

## Notes for the ingestion expert

- **Fetch reliability:** The DIAN normograma URL (`decreto_1072_2015.htm`) may be intermittently unavailable or behind a redirect. Fallback to MinTrabajo's official PDF if needed; both sources are authoritative per Colombian regulatory tradition.

- **Parte/Título granularity:** The master plan does not specify how fine-grained the parte/título split should be. A conservative approach: use explicit heading boundaries from the source; if absent, treat each contiguous article block as a separate título within a default parte=1. This avoids false splits but may flatten the hierarchy. Refine based on ingestion feedback.

- **SST specificity:** Libro 3 is heavily cross-referenced by DIAN resoluciones (e.g., Res. 0312/2019) and Constitutional Court sentencias (labor rights cases). Mark these articles clearly in the `tema` field (`tema: "Laboral | SST"`) so retrieval is precise.

- **Commit strategy:** Per master plan §10.5, commit DUR 1072 ingestion in a single commit with a message like `corpus(dur1072): ingest 250 articles from DUR 1072/2015 Libro 1-3 (E6a-c, J8a-c)`. This makes it easy to revert if downstream feedback indicates parsing errors.

---

## Estimated effort

- **Data extraction:** ~2–3 hours (fetch source, map estructura, extract articles)
- **norm_id canonicalization + validation:** ~1 hour
- **Round-trip testing + smoke verification:** ~30 minutes
- **Total:** ~4 hours for one ingestion expert
