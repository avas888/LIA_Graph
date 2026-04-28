# 02. DUR 1625/2016 Libro 1 (Renta)

**Master:** ../corpus_population_plan.md §4.1 (E1a–E1f)  
**Owner:** unassigned  
**Status:** 🟡 not started  
**Target norm count:** ~500  
**Phase batches affected:** E1a, E1b, E1c, E1d, E1e, E1f

---

## What

The Decreto Único Reglamentario de Tributación (DUR 1625 of 2016) Libro 1 is the master regulatory instrument interpreting the Estatuto Tributario's income tax regime. It contains ~500 articles spanning 8 sub-libros: disposiciones generales (1.1), ingresos no constitutivos de renta (1.2), costos y deducciones (1.3), rentas exentas (1.4), ganancias ocasionales (1.5), régimen tributario especial (1.6), personas naturales (1.7), and retenciones en la fuente (1.8+). The canonicalizer needs all Libro 1 articles parsed and indexed under the canonical `decreto.1625.2016.art.<dotted-decimal>` shape so that batches E1a–E1f can resolve via prefix filter and extract vigencia statements from the LLM.

---

## Source URLs (primary)

| URL | What's there |
|---|---|
| https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm | Full DUR 1625 (master page, contains all three libros) |
| (Libro 1 segments vary by platform; see parsing strategy) | Sub-libro breakpoints via HTML anchors or section headings |

---

## Canonical norm_id shape

```
decreto.1625.2016.art.<dotted-decimal-as-printed>
```

The DUR's articles are numbered with dotted decimals in the source (e.g., "Artículo 1.5.2.1"). Use that number verbatim. The libro / parte / título / capítulo structure is rich metadata for the body field — do not encode it in the id.

**Shape pattern (use the article number AS PRINTED in the source):**

```
decreto.1625.2016.art.<dotted-decimal>          (e.g. art.1.2.1.10, art.1.5.3.4)
decreto.1625.2016.art.<dotted-decimal>-<digit>  (compound articles, e.g. art.1.3.1.10-2)
```

The leading segment after `art.` is always `1.` (DUR 1625's outer numbering); the next segments encode libro / título / capítulo / artículo. Compound articles use `-<digit>` suffix — the canonicalizer accepts hyphen-digit (`-1`, `-2`) but **not** hyphen-letter (`-A`, `-B`).

**To get real article numbers:** open the DIAN normograma DUR 1625 page (`https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm`) and read the article headings. The YAML's E1a–E1f batch regex patterns (`config/canonicalizer_run_v1/batches.yaml`) confirm the prefix shape but list no specific article numbers — do not invent ids; copy them verbatim from the source.

**Round-trip via `canonicalize(...)`:** All norm_ids MUST pass through `lia_graph.canon.canonicalize` returning the same string before ingestion. Non-canonical ids (e.g. uppercase, wrong separators, missing `art.` prefix) will be rejected at write time.

---

## Parsing strategy

1. **Fetch the master DUR 1625 HTML** from the normograma DIAN URL (already live-fetched and cached).

2. **Identify Libro 1 boundaries.** The HTML uses section headings (typically `<h2>` or `<h3>`) to mark each libro and sub-libro. Anchor tags (e.g. `<a name="libro1">`, `<a name="libro1.1">`) may also mark boundaries.

3. **Extract sub-libro markers.** For each sub-libro (1.1 through 1.8+), locate its heading and the subsequent articles until the next sub-libro boundary.

4. **Per-article extraction:**
   - Locate article headings (pattern: `ARTÍCULO <N>` or `ARTICULO <N.-M>` where the hyphen indicates compound numbering).
   - Extract the full verbatim text up to the next article heading or sub-libro boundary.
   - Normalize whitespace (collapse multiple spaces, preserve paragraph breaks).

5. **Emit `parsed_articles.jsonl` rows** (schema per §6.1 of the master plan):
   ```json
   {
     "norm_id": "decreto.1625.2016.art.1.X.Y",
     "norm_type": "decreto_articulo",
     "article_key": "Art. 1.X.Y",
     "body": "<full verbatim text from source>",
     "source_url": "https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm",
     "fecha_emision": "2016-08-02",
     "emisor": "Presidencia de la República",
     "tema": "renta"
   }
   ```

6. **Sub-libro mapping** (verify against source; placeholder here):
   - 1.1 = Disposiciones Generales
   - 1.2 = Ingresos No Constitutivos de Renta y Ganancias Ocasionales
   - 1.3 = Costos y Deducciones
   - 1.4 = Rentas Exentas
   - 1.5 = Ganancias Ocasionales
   - 1.6 = Régimen Tributario Especial
   - 1.7 = Personas Naturales
   - 1.8+ = Retenciones en la Fuente (final articles)

---

## Edge cases observed

- **Compound article numbering.** Articles like "45-1", "45-2" appear as separate articles in the source but are sometimes grouped under a single heading. Emit each as a separate `norm_id`.
- **Modificación/derogación inline.** The source HTML may contain inline notes (e.g., "Modificado por Decreto 1474 de 2025") inside the article body. Keep as raw text — the canonicalizer's vigencia harness extracts modification metadata via Gemini/DeepSeek, not the parser.
- **Segmented articles.** If the source HTML splits a single article across multiple pages (e.g., via `<div class="page-break">`), merge the segments back into one article body before emitting the row.
- **Article cross-references.** Articles often reference other DUR or ET articles (e.g., "Ver también Art. 10 de este Decreto"). Preserve these as-is; the chat backend's retrieval will later use them for navigation.

---

## Smoke verification

After ingest, run the §6.3 batch-size check restricted to E1a–E1f:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path
for bid in ['E1a', 'E1b', 'E1c', 'E1d', 'E1e', 'E1f']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    assert all(n['norm_id'].startswith('decreto.1625.2016.art.1.') for n in norms), 'norm_id prefix mismatch'
    print(f'{bid}: {len(norms)} norms')
"
```

**Acceptance threshold:** Each batch should report ≥50–80 norms (see Appendix A of the master plan for per-batch targets). Total Libro 1 should reach ~500 norms.

---

## Dependencies on other briefs

- **No upstream dependencies.** Libro 1 parsing is self-contained.
- **Downstream:** Briefs 03 (Libro 2) and 04 (Libro 3) follow the same DUR parsing pipeline but restrict to Libros 2 and 3. If you implement a unified DUR parser, it can output all three libros in one pass — in that case, coordinate with briefs 03 and 04 to avoid duplicate parsing effort. The canonical id shapes differ only in the `libro.X` field, so the parser logic is identical.

---

*Last reviewed: 2026-04-28*  
*Canonical id shape verified against: corpus_population_plan.md §5*
