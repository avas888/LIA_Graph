# 08. Conceptos DIAN Unificados

**Master:** ../corpus_population_plan.md §4.3 (Phase G)  
**Owner:** unassigned  
**Status:** 🟡 not started  
**Target norm count:** ~390  
**Phase batches affected:** G1, G2, G3, G4, G5, G6

---

## What

Conceptos DIAN Unificados are compendiums of DIAN doctrine on specific tax regimes (IVA, Renta, Retención, Procedimiento, Régimen Simple). Each unified concepto is a long document (typically 100–300 pages) organized by **numerales** — logical subsections that answer specific compliance questions. Phase G requires parsing each unified concepto into per-numeral entries so the canonicalizer can resolve slices like "all numerales of Concepto Unificado de Renta" without materializing the entire 200-page PDF. This is the highest-value doctrinal source accountants consult for interpretations; ~390 numerales across five unified conceptos unlock G1–G6 (G6, Concepto 100208192-202, is already an acid test).

---

## Source URLs (primary)

| URL | What's there |
|---|---|
| https://normograma.dian.gov.co/dian/compilacion/docs/concepto_tributario_dian_<NUM>.htm | Unified concepto full text, organized by numerales |
| https://www.dian.gov.co/fizcalizacioncontrol/herramienconsulta/NIIF/ConceptosDian/Paginas/default.aspx | Master index of conceptos (DIAN portal) |

**Key unified conceptos (verified by existence in DIAN normograma):**
- IVA: `concepto_tributario_dian_0000001_2003.htm` (Concepto General Unificado del IVA, Concepto 1 de 2003) — heavily amended; seek most recent unified version
- Renta: `concepto_tributario_dian_0912_2018.htm` or similar (Concepto Unificado de Renta, typically Concepto ~912 de 2018)
- Retención: TBD — verify exact number in DIAN normograma
- Procedimiento: TBD — verify exact number in DIAN normograma
- Régimen Simple: TBD — verify exact number in DIAN normograma
- G6 (acid test): Concepto 100208192-202 (Octava adición Concepto General Personas Jurídicas — already in corpus as fixture)

---

## Canonical norm_id shape

**Pattern (parent):** `concepto.dian.<NUM>` or `concepto.dian.<NUM>-<SUFFIX>` (for hyphenated unified conceptos)

**Pattern (sub-numeral):** `concepto.dian.<NUM>.num.<X>` where `<X>` is the numeral number (often sequential 1, 2, 3… or formatted like 1.1, 1.2, 2.1, etc. — anchor on what the source document actually uses)

**Examples:**
- `concepto.dian.0000001.2003` (IVA unified — **parent**)
- `concepto.dian.0000001.2003.num.1` (numeral 1 of IVA unified)
- `concepto.dian.0000001.2003.num.1.1` (if source uses nested numeral format like "Numeral 1.1")
- `concepto.dian.100208192-202` (unified concepto with suffix, parent)
- `concepto.dian.100208192-202.num.4` (numeral 4 of the Renta unified)

**Round-trip:** Via `lia_graph.canon.canonicalize(...)` — the hyphenated and numeral formats must round-trip cleanly.

---

## Parsing strategy

1. **Fetch unified concepto HTML page** — e.g., `concepto_tributario_dian_0000001_2003.htm` for IVA.
2. **Identify numeral boundaries** — Unified conceptos use consistent heading markers for numerales. Common patterns:
   - `Numeral 1.`, `Numeral 2.`, etc. (heading level or bold text)
   - `<strong>1.</strong>` or `<h4>1.</h4>` HTML structure
   - Numerales may be nested (1.1, 1.2, 2.1, etc.) — use the exact nesting as it appears in source.
3. **For each numeral:**
   - Extract the numeral heading and all text until the next numeral (or end of document).
   - Emit one `parsed_articles.jsonl` row with:
     ```json
     {
       "norm_id": "concepto.dian.0000001.2003.num.1",
       "norm_type": "concepto_dian",
       "article_key": "Numeral 1",
       "body": "<full verbatim text of numeral 1, including sub-questions if any>",
       "source_url": "https://normograma.dian.gov.co/dian/compilacion/docs/concepto_tributario_dian_0000001_2003.htm",
       "fecha_emision": "2003-XX-XX",
       "emisor": "DIAN",
       "tema": "IVA"
     }
     ```
   - Also emit the **parent entry** (the unified concepto itself) with the full document as body:
     ```json
     {
       "norm_id": "concepto.dian.0000001.2003",
       "norm_type": "concepto_dian",
       "article_key": "Concepto Unificado IVA",
       "body": "<entire document text>",
       "source_url": "https://normograma.dian.gov.co/dian/compilacion/docs/concepto_tributario_dian_0000001_2003.htm",
       "fecha_emision": "2003-XX-XX",
       "emisor": "DIAN",
       "tema": "IVA"
     }
     ```
4. **Batch five families:**
   - **G1** (IVA): Concepto Unificado IVA — extract all numerales.
   - **G2** (Renta): Concepto Unificado Renta (verify exact number; known candidates: Concepto 912 de 2018, or later unified compilation) — likely 100+ numerales.
   - **G3** (Retención): Concepto Unificado Retención en la Fuente — verify number.
   - **G4** (Procedimiento): Concepto Unificado Procedimiento (Concepto 100208221-XXX or similar) — verify exact number.
   - **G5** (Régimen Simple): Concepto Unificado Régimen Simple — verify number.
   - **G6** (acid test): Concepto 100208192-202 already fixtured; ingest 1 row for G6 (parent only, or parent + first few numerales as explicit_list).

---

## Edge cases observed

- **Numeral with sub-structure** — A numeral may contain questions (e.g., "Numeral 5. Preguntas 1), 2), 3)..."). **Keep the entire numeral as one row** — do not split by sub-question. The canonicalizer retrieves by numeral boundary, and sub-questions are context within the numeral.
- **Cross-references to other numerales** — Within numeral text, you may see "ver Numeral 3" or "de conformidad con lo expuesto en el Numeral 7." Keep these as raw text; the canonicalizer does not auto-link them.
- **Amendments inside numeral body** — Some numerales say "Modificado por la Resolución XXX de YYYY." Keep this text as-is; do not try to excise it or create separate rows.
- **Date inconsistencies** — The unified concepto HTML page may not explicitly state the `fecha_emision` for each numeral. Use the page's metadata or header date; if unknown, set `fecha_emision: null`.
- **Formatting loss in plain text** — Tables and structured lists inside conceptos may lose formatting during text extraction. Preserve the semantic content (row/column headers, bullet structure) as ASCII art or plain text equivalents.

---

## Smoke verification

After ingest, run:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path
for bid in ['G1', 'G2', 'G3', 'G4', 'G5', 'G6']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    print(f'{bid}: {len(norms)} norms')
"
```

**Expected:** G1 ≥60, G2 ≥100, G3 ≥60, G4 ≥60, G5 ≥60, G6 ≥1 (combined: ≥310, or 80% of target 390).

---

## Unified concepto identification task

Before ingestion, confirm the **exact norm_id** and URL for each of the five unified conceptos. The corpus plan references these families but did not specify the authoritative document numbers. Create a small research table:

| Capa | Nombre | Número DIAN (to verify) | URL en normograma | Numerales aprox. |
|---|---|---|---|---|
| G1 | Concepto Unificado IVA | Concepto 001/2003? | `concepto_tributario_dian_NNNN.htm` | ~60 |
| G2 | Concepto Unificado Renta | Concepto 912/2018 o 100208192-202? | `concepto_tributario_dian_NNNN.htm` | ~100+ |
| G3 | Concepto Unificado Retención | TBD | `concepto_tributario_dian_NNNN.htm` | ~60 |
| G4 | Concepto Unificado Procedimiento | Concepto 100208221-XXX? | `concepto_tributario_dian_NNNN.htm` | ~60 |
| G5 | Concepto Unificado Régimen Simple | TBD | `concepto_tributario_dian_NNNN.htm` | ~60 |

**Action:** Query DIAN normograma directly for "Concepto Unificado" + {IVA|Renta|Retención|Procedimiento|Régimen Simple} to resolve exact numbers. Link the confirmed URLs in this brief before proceeding to parse.

---

## Dependencies on other briefs

- **No upstream dependencies.** Unified conceptos are primary doctrine; they do not rely on other norm families being parsed first.
- **Downstream:** Unified conceptos are the **foundation** for Phase H (individual conceptos). Many individual conceptos inherit or reference numerals from the unified ones. **Ingest G before H** to avoid ID collisions (both use `concepto.dian.<NUM>` syntax).

---

**Ingestion notes:**

- Schema validation before commit: run §6.1 round-trip check on all `concepto.dian.*` norm_ids (both parent and numeral forms).
- Commit message pattern: `corpus(conceptos-dian-unificados): ingest ~390 numerales from 5 unified conceptos Phase G1-G6`.
- For G6 (Concepto 100208192-202), check if it's already in the corpus as a fixture from prior acid-test runs. If so, you may skip it or overwrite with the full parsed version.

