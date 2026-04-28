# Brief 07 — Resoluciones DIAN

**Owner:** unassigned
**Status:** 🟡 not started
**Sprint:** 1 (priority #4)
**Estimated effort:** 1 day

---

## What you are looking for

Key DIAN resoluciones across four topic areas. Approximately **140 resoluciones** in total.

| Topic | What | Count |
|---|---|---:|
| **F1** — UVT + calendario tributario | The annual UVT-setting resolution and calendario de plazos for tax filings, for years 2018 through 2026 | ~50 |
| **F2** — Factura electrónica + nómina electrónica + RADIAN | Resoluciones 165/2023 and 2275/2023 (factura electrónica), 042/2020 and 13/2021 (nómina electrónica), and the RADIAN regulations | ~30 |
| **F3** — Régimen Simple de Tributación (RST) | Resoluciones that regulate the régimen simple | ~20 |
| **F4** — Cambiario, RUT, obligados | RUT-related resoluciones, exógena annual resolutions, RPA, cambiario operations | ~40 |

## Where to find the documents

Three indexes will help:

- **Master index of all DIAN resoluciones:** `https://www.dian.gov.co/normatividad/Paginas/Resoluciones.aspx`
- **Per-resolución HTML on DIAN normograma:** `https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_<NUM>_<YEAR>.htm`
- **Official PDFs:** `https://www.dian.gov.co/normatividad/Normatividad/`

For each resolución, the DIAN normograma usually has the consolidated current-vigencia text — that is what we want.

## What to deliver per resolución

Each resolución is a multi-article document. Deliver **all of its articles**, plus the parent metadata:

1. **Full text** of each article inside the resolución, copied exactly.
2. **Article number** within the resolución (e.g., "1", "5", "12-A").
3. **Resolution number and year** — e.g., "Resolución DIAN 022 de 2025."
4. **URL** — the exact `resolucion_dian_<NUM>_<YEAR>.htm` URL.
5. **Issue date** of the resolución.

## How to package

**Option B recommended** — one markdown file with sections per resolución:

Filename: `brief_07_resoluciones_dian.md`

Structure:

```
# Resolución DIAN 022 de 2025 (UVT 2026)
URL: https://normograma.dian.gov.co/.../resolucion_dian_000022_2025.htm
Issued: 2025-12-05
Topic: F1 (UVT + calendario)

## Artículo 1
[full text]

## Artículo 2
[full text]

---

# Resolución DIAN 165 de 2023 (factura electrónica)
URL: ...
Issued: 2023-MM-DD
Topic: F2 (factura electrónica)

## Artículo 1
[full text]

...
```

## Special things to watch for

- **Resolution numbers may have leading zeros.** DIAN sometimes writes "Resolución 000022" or just "Resolución 22". Preserve whatever form the source uses; tell the coordinator if you see both forms for the same resolución.
- **UVT resoluciones change every year.** Cover years 2018 through 2026 (so eight or nine UVT resoluciones in F1, plus a separate calendario resolución for each year).
- **Modificatorias.** A factura-electrónica resolución may be modified by a later one. If a current consolidated text on the DIAN page has inline notes about modifications, keep them.

## Notes

- F2's four numbered resoluciones (165/2023, 2275/2023, 042/2020, 13/2021) are pre-vetted by the dev team — you can rely on those numbers being correct. Other resoluciones in F1, F3, F4 you discover from the index.
- Target is ~140 resoluciones across F1–F4. If you find materially fewer, flag it.

## When you're done

1. Hand off `brief_07_resoluciones_dian.md` to the coordinator.
2. Update this file: `Status: ✅ delivered` + delivery note.
