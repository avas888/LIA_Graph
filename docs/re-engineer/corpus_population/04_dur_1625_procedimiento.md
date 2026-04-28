# 04. DUR 1625/2016 Libro 3 (Procedimiento y Sanciones)

**Master:** ../corpus_population_plan.md §4.1 (E3a–E3b)  
**Owner:** unassigned  
**Status:** 🟡 not started  
**Target norm count:** ~200  
**Phase batches affected:** E3a, E3b

---

## What

The Decreto Único Reglamentario (DUR 1625 of 2016) Libro 3 covers the procedimiento tributario (tax administration and compliance procedures) and sanciones (tax penalties and enforcement). It contains ~200 articles spanning procedimiento and régimen sancionatorio, governing taxpayer obligations, audit mechanics, defense rights, penalty structures, and collection procedures. The canonicalizer needs all Libro 3 articles parsed and indexed so that batches E3a–E3b can resolve via prefix filter and run vigencia extraction. The parsing strategy is identical to Libros 1 and 2, restricted to Libro 3 scope.

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

Use the article number as printed. For procedimiento + sanciones articles the dotted decimal starts with `1.5.*`. The brief's title "Libro 3" is a human subject label, NOT a segment in the id.

**Shape pattern (use the article number AS PRINTED in the source):**

```
decreto.1625.2016.art.1.5.<dotted-decimal>          (procedimiento + sanciones, prefix from YAML E3a/E3b)
decreto.1625.2016.art.1.5.<dotted-decimal>-<digit>  (compound articles)
```

The canonicalizer accepts hyphen-digit suffixes for compound articles (`-1`, `-2`, etc.) but **not** hyphen-letter (`-A`, `-B`). If the source uses a letter suffix, document the mapping in the row's `body` field and use the next available digit suffix in the id.

**To get real article numbers:** open the DIAN normograma DUR 1625 page (`https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm`) and read the article headings under the procedimiento book.

**Round-trip via `canonicalize(...)`:** All norm_ids MUST pass through `lia_graph.canon.canonicalize` returning the same string.

---

## Parsing strategy

**Same parsing pipeline as 02_dur_1625_renta.md and 03_dur_1625_iva_retefuente.md, restricted to Libro 3 scope.** Reuse the unified DUR parser if already implemented; invoke with `libro=3`.

### Quick steps:

1. **Fetch master DUR 1625 HTML** (reuse cache from Libros 1–2 if already fetched).

2. **Locate Libro 3 boundary.** Find the heading for "LIBRO 3" or "LIBRO TERCERO" and extract until end of document.

3. **Identify Libro 3 sub-libros** (verify against source):
   - 3.1 = Procedimiento Tributario (obligations, declarations, audits, defenses)
   - 3.2 = Régimen Sancionatorio (penalties, contraventions, enforcement)
   - 3.3+ = Additional procedural/enforcement topics (if any)

4. **Extract articles** per the method in brief 02 (heading anchors, article heading patterns, whitespace normalization).

5. **Emit `parsed_articles.jsonl` rows** using the schema from §6.1 of the master plan, with `norm_id` set to `decreto.1625.2016.art.1.5.<sub>.<art>` (all Libro 3 articles start with `1.5`) and `tema: "procedimiento"` or `tema: "sanciones"` as appropriate.

---

## Edge cases observed

- **"Libro 3" is a human label.** The brief's title "Libro 3" is the human label for procedimiento + sanciones. In the canonical norm_id, this corresponds to the DUR's article-number prefix `1.5.*`, per `batches.yaml` E3a/E3b. Use the article numbers as printed in the source.
- **Penalty escalation tables.** Sanciones articles often include nested penalty structures (e.g., tiered percentages, fixed amounts, disqualification periods). Capture the full article including tables and lists as raw text.
- **Procedimiento cross-references.** Articles frequently reference other procedimiento norms (e.g., "según lo dispuesto en el Art. 10 de este Libro"). Preserve as-is for downstream retrieval.
- **Decreto 1474/2025 + jurisprudencia interaction.** Libro 3 has been heavily modified by emergency decrees and subsequent CC/CE rulings. Inline notes are common. Keep them as body text; the vigencia harness will parse modification dates via Gemini/DeepSeek.
- **Abrogación partial.** Some sanciones articles have been abrogated or superseded by newer decrees. The source HTML may mark these explicitly. Preserve the original article text and let the vigencia extractor determine current status.

---

## Smoke verification

After ingest, run the §6.3 batch-size check restricted to E3a–E3b:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path
for bid in ['E3a', 'E3b']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    assert all(n['norm_id'].startswith('decreto.1625.2016.art.1.5.') for n in norms), 'norm_id prefix mismatch'
    print(f'{bid}: {len(norms)} norms')
"
```

**Acceptance threshold:** E3a and E3b should each report ≥80–100 norms. Total Libro 3 should reach ~200 norms.

---

## Dependencies on other briefs

- **Upstream:** Briefs 02 (Libro 1) and 03 (Libro 2). If you implemented a unified DUR parser, reuse it. Libro 3 parsing is the final segment of a single DUR source, so recommend executing all three briefs (Libros 1, 2, 3) in a single run of the parser to avoid redundant fetches.
- **Sibling:** Briefs 02 and 03 share the same source and parsing approach. Coordinate to emit rows for all three libros in one transaction if possible, then smoke-test all six batches (E1a–f, E2a–c, E3a–b) together.

---

*Last reviewed: 2026-04-28*  
*Canonical id shape verified against: corpus_population_plan.md §5*
