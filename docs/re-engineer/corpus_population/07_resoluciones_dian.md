# 07. Resoluciones DIAN

**Master:** ../corpus_population_plan.md §4.2 (Phase F)  
**Owner:** unassigned  
**Status:** 🟡 not started  
**Target norm count:** ~140  
**Phase batches affected:** F1, F2, F3, F4

---

## What

Resoluciones DIAN are normative instruments issued by the Colombian tax authority (Dirección de Impuestos y Aduanas Nacionales) that establish operational and substantive rules for tax compliance. Phase F covers four families: (F1) annual UVT-setting and calendar resoluciones (2018–2026), (F2) factura electrónica, nómina electrónica, and RADIAN regulations, (F3) Régimen Simple de Tributación (RST) rules, and (F4) cambiario (exchange), RUT (Registro Único Tributario), and información exógena obligaciones. Together, these ~140 norms are the most-cited reference docs accountants use for operational compliance deadlines, technical system requirements, and filing obligations.

---

## Source URLs (primary)

| URL | What's there |
|---|---|
| https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_NNNN_YYYY.htm | Individual resolución full text and amendments (DIAN master normograma) |
| https://www.dian.gov.co/normatividad/Paginas/Resoluciones.aspx | Master index of all active resoluciones by year |
| https://www.dian.gov.co/normatividad/Normatividad/ | Official PDF downloads of each resolución (current vigencia) |

**Canonical reference:** Resolución 000193 de 2024 (UVT 2025) at `https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_0193_2024.htm`; Resolución 000165 de 2023 (factura electrónica) at `https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_0165_2023.htm`

---

## Canonical norm_id shape

**Pattern:** `res.dian.<NUM>.<YEAR>`

**Examples:**
- `res.dian.000193.2024` (UVT 2025)
- `res.dian.000165.2023` (factura electrónica)
- `res.dian.000238.2025` (UVT 2026)
- `res.dian.0193.2024` (zero-padding may be optional — verify existing entries in corpus)

**Round-trip:** Via `lia_graph.canon.canonicalize(...)` before ingesting. The NUM field is typically 6-digit zero-padded in recent years (`000165`, `000193`, `000238`) but may be 1–4 digits in legacy resoluciones (2018–2022). **Check the existing parsed_articles.jsonl corpus for the pattern actually observed — canonical form must match what's already there.**

---

## Parsing strategy

1. **Index phase** — Fetch the DIAN normograma resoluciones index (`/dian/compilacion/docs/resolucion_dian_NNNN_YYYY.htm`).
2. **Extract per-resolución body** — Each resolución HTML page contains the full text (articles, considerandos, diagrams). Extract verbatim body.
3. **Identify articles** — Most resoluciones are organized by `ARTÍCULO <N>`, `PARÁGRAFO`, `NUMERAL`. Emit one row per article (not per numeral — a numeral is sub-content of an article and should remain embedded in the article body for retrieval).
4. **Emit rows** — For each resolución/article pair:
   ```json
   {
     "norm_id": "res.dian.000193.2024",
     "norm_type": "res_dian",
     "article_key": "Art. 1",
     "body": "<full verbatim article text>",
     "source_url": "https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_0193_2024.htm",
     "fecha_emision": "2024-12-04",
     "emisor": "DIAN",
     "tema": "UVT"
   }
   ```
5. **Batch four families:**
   - **F1** (UVT + calendario): Resoluciones 000193/2024, 000042/2023 (or prior years' UVT-setting resolution), annual plazos resoluciones (e.g., 1729/2025 for 2026 plazos — verify exact number).
   - **F2** (factura electrónica + nómina + RADIAN): Resolución 000165/2023 (factura v1.9, documento soporte), Resolución 2275/2023 (nómina electrónica), Resolución 022/2025 (RADIAN — verify exact number).
   - **F3** (RST): Régimen Simple resoluciones (scan DIAN normograma index for keyword "Régimen Simple" — typically 3–5 active resoluciones at any time).
   - **F4** (cambiario + RUT + exógena): Resoluciones on RUT requirements, información exógena annual (resolve by year), cambio de domicilio rules.

---

## Edge cases observed

- **Amendments and modificaciónes** — Many resoluciones are modified by later resoluciones (e.g., Resolución 165/2023 was updated by Resolución XXX/2024). Keep the **original resolución text unchanged** in the corpus body; the canonicalizer's vigencia harness will detect the modification via Gemini/DeepSeek when it sees phrases like "modifica el artículo 5 de la Resolución 165/2023."
- **Resolución de corrección de errores** — Some resoluciones are pure corrections (e.g., "Resolución XXX de corrección de erratas de Resolución YYY"). Treat as a separate resolución with its own norm_id; do not merge into parent.
- **Versioning of anexos técnicos** — Factura electrónica resoluciones often ship with multiple "Anexo Técnico" versions (v1.8, v1.9, etc.). Keep the resolución body as one row; do **not** split anexos into separate entries.
- **Plazos resolution (calendario tributario)** — Usually released late November/early December for the next calendar year. The year in the norm_id is the year the resolución was **issued**, not the year plazos apply to (e.g., Resolución 1729/**2025** sets plazos for **2026**).

---

## Smoke verification

After ingest, run:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path
for bid in ['F1', 'F2', 'F3', 'F4']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    print(f'{bid}: {len(norms)} norms')
"
```

**Expected:** F1 ≥40, F2 ≥25, F3 ≥15, F4 ≥30 (combined: ≥110, or 80% of target 140).

---

## Dependencies on other briefs

- **No upstream dependencies.** Resoluciones DIAN are primary sources; they do not inherit numerals or sub-ids from other families.
- **Downstream:** Resoluciones DIAN are cross-referenced in many DUR articles (E1–E3) and concepto numerales (G1–G6, H1–H6). Populate Phase F before or alongside G/H to ease vigencia verification (the canonicalizer will need to find `res.dian.*` references inside concepto bodies).

---

## Key resolutions to verify before ingest

| Family | Key resolutions | Verify status |
|---|---|---|
| F1 (UVT) | 000193/2024 (UVT 2025), 000238/2025 (UVT 2026), 000042/2023 (UVT 2024) | ✅ confirmed via INCP/DIAN |
| F1 (calendario) | 1729/2025 (plazos 2026) — **to be confirmed in DIAN normograma** | 🟡 pending |
| F2 (FE) | 000165/2023 (factura v1.9), 2275/2023 (nómina electrónica) | ✅ confirmed |
| F2 (RADIAN) | 022/2025 — **verify exact number in DIAN normograma** | 🟡 pending |
| F3 (RST) | Scan DIAN normograma for "Régimen Simple" resoluciones | 🟡 pending |
| F4 (exógena) | Annual exógena resolución (recent: 162/2023, 124/2023 — cycles yearly) | 🟡 pending |

---

**Ingestion notes:**

- Do **not** ingest PDF scans directly. Parse text from DIAN normograma `.htm` pages.
- Schema validation before commit: run §6.1 round-trip check on all norm_ids.
- Commit message pattern: `corpus(resoluciones-dian): ingest ~140 DIAN resolutions Phase F1-F4`.

