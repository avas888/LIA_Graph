# 13. Resoluciones DIAN — UVT + plazos + RST + RUT/exógena (gap-fill)

**Master:** ../corpus_population_plan.md §4.2 (Phase F)
**Owner:** unassigned
**Status:** 🟡 not started
**Target norm count:** ~85 (F1: ~40 · F3: ~15 · F4 supplemental: ~30)
**Phase batches affected:** F1, F3, F4 (gap-fill; F2 already covered by Brief 07)

---

## What

Brief 07 (already delivered) covered DIAN resoluciones for **factura electrónica + nómina** (F2 family) and a partial F4 set. The first-pass campaign smoke check on 2026-04-28 found:

| Batch | Status after Brief 07 | Reason |
|---|---|---|
| F1 (UVT + plazos) | MISS | No UVT-setting or calendario-plazos resoluciones in delivery |
| F2 (factura electrónica + nómina) | PASS (111/30 norms) | Brief 07 covered it |
| F3 (RST) | MISS | No RST-specific resoluciones in delivery |
| F4 (RUT + exógena + cambiario) | MISS at YAML level | YAML uses keyword regex (`rut|obligados|cambiario`) which the canonical id form `res.dian.<NUM>.<YEAR>` doesn't carry. Either YAML repair or specific resolución numbers known to be RUT/exógena |

This brief fills F1 + F3 + supplements F4 with the actual annual UVT, plazos, RST, exógena, RUT-update resoluciones. The DIAN `res.dian.*` URL resolver works end-to-end (per the 2026-04-27 ley.* fix landed concurrently); this is a corpus-only delivery — no scraper extension needed.

---

## Source URLs (primary)

| URL | What's there |
|---|---|
| https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_<NUM>_<YEAR>.htm | Per-resolución consolidated text (canonical source) |
| https://www.dian.gov.co/normatividad/Paginas/Resoluciones.aspx | Master index of all DIAN resoluciones (use to discover the actual annual UVT + plazos + RST numbers) |
| https://www.dian.gov.co/normatividad/Normatividad/ | Official PDF downloads |

**Verified examples** (from existing corpus + INCP/DIAN cross-checks):

- F1 UVT: Resolución DIAN 000193 de 2024 (UVT 2025), Resolución 000042 de 2023 (UVT 2024).
- F1 plazos: Resolución 1729 de 2025 (plazos 2026) — **expected name; verify against the index before pasting into a row**.
- F3 RST + F4 exógena: numbers rotate annually; the expert resolves them off the index. Do not invent.

---

## Canonical norm_id shape

`res.dian.<NUM>.<YEAR>.art.<X>` — **unpadded** NUM (per the 2026-04-28 finding from Brief 07: the YAML's F2 pattern uses unpadded form like `res.dian.165.2023`, so we strip leading zeros from the canonical id while keeping the padded form in the source URL).

**Examples** (round-trip clean through `lia_graph.canon.canonicalize`):

- Parent: `res.dian.193.2024` (UVT 2025) — strip the `000` padding from `000193`.
- Article: `res.dian.193.2024.art.1` (Article 1 of UVT 2025 setting resolución).
- Article: `res.dian.42.2023.art.5`.

**Round-trip rule:** every `norm_id` must round-trip cleanly through `lia_graph.canon.canonicalize`. Strip leading zeros from NUM in the id; keep the padded form in `source_url` (DIAN normograma's filename uses zero-padded form like `resolucion_dian_0193_2024.htm`).

---

## Parsing strategy

1. **Discover annual UVT + plazos resoluciones for 2018 through 2026** by scanning the DIAN normograma index. For each year there are typically two resoluciones: one UVT-setter (issued in December for the following calendar year) and one plazos-calendario (also issued in December). Note both.
2. **For RST (F3),** search the index for "Régimen Simple" — capture the 3–5 resoluciones currently active for inscription, payment, formularios 260/261, sanctions specific to régimen simple.
3. **For F4 supplemental,** capture annual exógena resoluciones for 2024 and 2025 (Brief 07 already shipped 2023, 2021; older ones at 2018, 2019, 2020 are nice-to-have if findable on the DIAN index).
4. **Per resolución,** extract every numbered article (`ARTÍCULO N`, including `12-A` / `12 bis` style suffixes if present) and emit one row per article + one parent row per resolución.
5. **Emit rows** to `parsed_articles.jsonl`:
   ```json
   {
     "norm_id": "res.dian.193.2024.art.1",
     "norm_type": "res_articulo",
     "article_key": "Art. 1 Res. DIAN 193/2024",
     "body": "[CITA: Resolución DIAN 193 de 2024, Artículo 1]\n\n<verbatim article text>",
     "source_url": "https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_0193_2024.htm",
     "fecha_emision": "2024-12-04",
     "emisor": "DIAN",
     "tema": "uvt_calendario | regimen_simple | rut_exogena"
   }
   ```
   Plus one parent row per resolución with `norm_id = res.dian.<NUM>.<YEAR>` and a `[CITA: Resolución DIAN <NUM> de <YEAR>]` body so the YAML's keyword regex (or any future explicit_list) can resolve to it.

The ingester `scripts/canonicalizer/ingest_expert_packet.py` already handles brief 07's shape; brief 13 reuses brief 07's handler verbatim — no code change. Just feed the new packet.

---

## Edge cases observed

- **Year-of-issue vs year-of-applicability.** A plazos calendario resolution issued in December 2025 sets plazos for tax year 2026. The canonical id is keyed by the year the resolución was **issued** (`res.dian.1729.2025`), not the year it applies to.
- **Leading zeros in source URLs.** DIAN normograma's filename uses zero-padded NUM (`resolucion_dian_0193_2024.htm`). Keep that in `source_url`. The canonical id strips zeros (`res.dian.193.2024`).
- **Resolución de corrección de erratas.** If DIAN issues a correction-only resolución, treat it as a separate norm with its own `norm_id`; do not merge into the parent.
- **Anexos técnicos.** Some resoluciones (especially factura electrónica) ship with multiple Anexo Técnico versions (v1.8, v1.9). Keep the resolución body as one row; do NOT split anexos into separate entries.

---

## Smoke verification

After ingest, run:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path
for bid in ['F1', 'F3', 'F4']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    print(f'{bid}: {len(norms)} norms')
"
```

**Expected:** F1 ≥ 30, F3 ≥ 12, F4 ≥ 25 after this brief lands (combined ≥ 67, or ~80% of brief target 85).

**Caveat — YAML keyword patterns.** The current YAML uses keyword regex for F1/F3/F4 (`uvt|plazos|calendario`, `simple|sintributario`, `rut|obligados|cambiario`) which canonical ids do **not** carry. The brief 13 delivery alone may not flip the smoke check to PASS — it may also need a YAML-pattern repair pass to switch from keyword regex to explicit number-list (or to widen ingester `tema` field into the id, if the canon team approves). Document the gap; don't lower the threshold.

---

## Dependencies on other briefs

- **Upstream:** Brief 07 already delivered F2 (factura electrónica + nómina). No upstream blockers.
- **Downstream:** F1/F3/F4 resoluciones are cross-referenced in Phase G (conceptos unificados) and H (conceptos individuales) — populate F before re-running G and H.

---

**Last verified:** 2026-04-28
**Ready for assignment:** Yes — fixture-only path (DIAN resolver operational; no scraper extension required).
