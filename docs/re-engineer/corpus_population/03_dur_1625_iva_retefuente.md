# 03. DUR 1625/2016 Libro 2 (IVA + Retención en la Fuente)

**Master:** ../corpus_population_plan.md §4.1 (E2a–E2c)  
**Owner:** unassigned  
**Status:** 🟡 not started  
**Target norm count:** ~280  
**Phase batches affected:** E2a, E2b, E2c

---

## What

The Decreto Único Reglamentario (DUR 1625 of 2016) Libro 2 governs two tax regimes: IVA (value-added tax) and retención en la fuente (withholding tax). It contains ~280 articles across sub-libros for IVA mechanics, retención IVA, retención en la fuente, and other indirect tax mechanics. The canonicalizer needs all Libro 2 articles parsed and indexed so that batches E2a–E2c can resolve via prefix filter and run vigencia extraction. The parsing strategy is identical to Libro 1 (brief 02), restricted to Libro 2 scope.

---

## Source URLs (primary)

| URL | What's there |
|---|---|
| https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm | Full DUR 1625 (master page; contains Libros 1, 2, 3) |

---

## Canonical norm_id shape

```
decreto.1625.2016.art.<dotted-decimal-as-printed>
```

Use the article number as printed. For IVA articles the dotted decimal starts with `1.3.*`; for retefuente reglamentado articles it starts with `1.2.4.*`. The brief's title "Libro 2" is a human subject label, NOT a segment in the id.

**Shape pattern (use the article number AS PRINTED in the source):**

```
decreto.1625.2016.art.1.3.<dotted-decimal>          (IVA articles, prefix from YAML E2a/E2b)
decreto.1625.2016.art.1.2.4.<dotted-decimal>        (retefuente reglamentado, prefix from YAML E2c)
```

**To get real article numbers:** open the DIAN normograma DUR 1625 page (`https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm`) and read the article headings under the IVA + retefuente books. Do not invent ids; copy them verbatim from the source.

**Round-trip via `canonicalize(...)`:** All norm_ids MUST pass through `lia_graph.canon.canonicalize` returning the same string.

---

## Parsing strategy

**Same parsing pipeline as 02_dur_1625_renta.md, restricted to Libro 2 scope.** Do not duplicate the parsing code; if you implemented a unified DUR parser in brief 02, reuse it here by invoking it with `libro=2` and `output_filter=lambda row: row['norm_id'].startswith('decreto.1625.2016.art.1.3.') or row['norm_id'].startswith('decreto.1625.2016.art.1.2.4.')`.

### Quick steps:

1. **Fetch master DUR 1625 HTML** (reuse cache from Libro 1 if already fetched).

2. **Locate Libro 2 boundary.** Find the heading for "LIBRO 2" or "LIBRO SEGUNDO" and extract until the start of Libro 3.

3. **Identify Libro 2 sub-libros** (verify against source):
   - 2.1 = IVA (aspectos generales)
   - 2.2 = Retención IVA / Impuesto sobre Valor Agregado – Retención
   - 2.3 = Retención en la Fuente (ingresos y ganancias)
   - 2.4 = Retención en la Fuente (IVA, temas adicionales)
   - 2.5+ = Otros tributos indirectos (GMF, impuestos adicionales, etc.)

4. **Extract articles** per the method in brief 02 (heading anchors, article heading patterns, whitespace normalization).

5. **Emit `parsed_articles.jsonl` rows** using the schema from §6.1 of the master plan, with `norm_id` set to `decreto.1625.2016.art.1.3.<sub>.<art>` (IVA) or `decreto.1625.2016.art.1.2.4.<sub>.<art>` (retefuente) and `tema: "iva"` or `tema: "retefuente"` as appropriate.

---

## Edge cases observed

- **"Libro 2" is a human label.** The brief's title "Libro 2" is a human label for the IVA + retefuente subject area. In the canonical norm_id, this corresponds to the DUR's article-number prefixes `1.3.*` (IVA proper) and `1.2.4.*` (retefuente reglamentado), per `config/canonicalizer_run_v1/batches.yaml` batches E2a/E2b/E2c. Read the article number off the source; do not invent a `libro.2` segment.
- **IVA + retención overlap.** Some articles address both IVA and retención in the fuente mechanics (e.g., tariff rates, base calculations). Keep as single articles; the canonicalizer's context field will disambiguate usage during vigencia extraction.
- **Decreto 1474/2025 interaction.** Libro 2 articles have been modified heavily by Decreto 1474/2025 (emergency tax measures). Inline modification notes are common. Preserve them in the article body; the LLM's vigencia harness will identify the effective date and status.
- **Compound retención bases.** Articles on retención calculation often reference multiple rate tables and conditions. Ensure the full article is captured, including footnotes and cross-references.

---

## Smoke verification

After ingest, run the §6.3 batch-size check restricted to E2a–E2c:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path
for bid in ['E2a', 'E2b', 'E2c']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    assert all(n['norm_id'].startswith('decreto.1625.2016.art.1.3.') or n['norm_id'].startswith('decreto.1625.2016.art.1.2.4.') for n in norms), 'norm_id prefix mismatch'
    print(f'{bid}: {len(norms)} norms')
"
```

**Acceptance threshold:** E2a, E2b, E2c should each report ≥60–80 norms. Total Libro 2 should reach ~280 norms.

---

## Dependencies on other briefs

- **Upstream:** Brief 02 (Libro 1). If you implemented a unified DUR parser there, reuse it.
- **Sibling:** Brief 04 (Libro 3) uses the same parser; coordinate to avoid triple-parsing of the same source.

---

*Last reviewed: 2026-04-28*  
*Canonical id shape verified against: corpus_population_plan.md §5*
