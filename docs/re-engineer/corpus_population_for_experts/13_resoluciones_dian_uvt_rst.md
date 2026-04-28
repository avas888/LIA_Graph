# Brief 13 — Resoluciones DIAN (UVT + plazos + RST + RUT/exógena)

**Owner:** unassigned
**Status:** 🟡 not started
**Sprint:** 4 (gap-fill — added 2026-04-28 after first-pass campaign)
**Estimated effort:** 1 day

---

## What you are looking for

Three families of DIAN resoluciones that the first round (Brief 07) did **not** cover. Approximately **85 resoluciones** in total.

| Topic | What | Count |
|---|---|---:|
| **F1** — UVT + calendario tributario | The annual UVT-setting resolution **and** the annual calendario de plazos resolution, for years 2018 through 2026 (roughly 1 + 1 per year) | ~40 |
| **F3** — Régimen Simple de Tributación (RST) | DIAN resoluciones that regulate the régimen simple — inscription, formularios (260, 261), payment plazos, sanctions specific to RST | ~15 |
| **F4** — RUT, información exógena, cambiario | RUT-related resoluciones (inscription, updates, cancellation), the **annual** información exógena resolution that DIAN publishes each year for the next reporting period, and DIAN cambiario resoluciones | ~30 |

**What we already have (so do NOT re-collect):** Brief 07 already shipped 10 resoluciones — F2-class factura electrónica + nómina (165/2023, 042/2020, 13/2021) and a partial F4 set (162/2023, 124/2021, 117/2024, 085/2022, 151/2012, 019/2016, 220/2014). Anything not on that list is fair game.

## Where to find the documents

Three indexes will help:

- **Master index of all DIAN resoluciones:** `https://www.dian.gov.co/normatividad/Paginas/Resoluciones.aspx`
- **Per-resolución HTML on DIAN normograma:** `https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_<NUM>_<YEAR>.htm`
- **Official PDFs:** `https://www.dian.gov.co/normatividad/Normatividad/`

The DIAN normograma usually has the consolidated current-vigencia text — that is what we want.

## What to deliver per resolución

Each resolución is a multi-article document. Deliver **all of its articles**, plus the parent metadata:

1. **Full text** of each article inside the resolución, copied exactly.
2. **Article number** within the resolución (e.g., "1", "5", "12-A").
3. **Resolution number and year** — e.g., "Resolución DIAN 022 de 2025."
4. **URL** — the exact `resolucion_dian_<NUM>_<YEAR>.htm` URL (or the official PDF URL if HTML is missing).
5. **Issue date** of the resolución.

## How to package

**Option B recommended** — one markdown file with sections per resolución:

Filename: `brief_13_resoluciones_dian_uvt_rst.md`

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

# Resolución DIAN 1729 de 2025 (Plazos 2026)
URL: ...
Issued: 2025-MM-DD
Topic: F1 (UVT + calendario — plazos)

## Artículo 1
[full text]

---

# Resolución DIAN <NUM> de <YEAR> (Régimen Simple)
URL: ...
Topic: F3 (RST)

## Artículo 1
[full text]
```

## Resoluciones we know are real (verified examples)

You can rely on these numbers — they are pre-vetted by the dev team or already cross-referenced in the existing corpus:

- **F1 — UVT-setting:** Resolución DIAN 000193 de 2024 (UVT 2025), Resolución DIAN 000042 de 2023 (UVT 2024). Resolución 022 de 2025 is **expected** for UVT 2026 — verify the actual number when you find it on the index.
- **F1 — plazos calendario:** Resolución 1729 de 2025 (plazos 2026) is the **expected** form — verify the actual number when you find it on the index.
- **F3 — RST:** No specific numbers pre-verified. Search the DIAN normograma index for "Régimen Simple" and capture whatever resoluciones currently regulate inscription, payment, sanctions for the régimen simple. Typical scope: 3–5 active resoluciones.
- **F4 — exógena anuales:** The annual exógena resolution rotates. Recent ones include Resolución DIAN 162 de 2023 and 124 de 2021 (already in corpus from Brief 07) — but every year DIAN publishes a fresh one. Look for 2024, 2025 exógena resoluciones. Typical names: "exógena tributaria," "información exógena."

**Do NOT invent resoluciones we have not verified.** If you cannot find a UVT or plazos resolution for a particular year, leave a one-line note ("UVT 2019 not found at the DIAN normograma index; tried URLs X, Y") and move on. Better to under-deliver than to fabricate.

## Special things to watch for

- **Resolution numbers may have leading zeros.** DIAN sometimes writes "Resolución 000022" or just "Resolución 22". Preserve whatever form the source uses.
- **UVT resoluciones change every year.** Cover years 2018 through 2026. Each year typically has both a UVT-setting resolution (issued in December) **and** a plazos calendario resolution (also issued in December for the following year). So roughly 8–9 UVT-setting resoluciones + 8–9 plazos resoluciones.
- **Modificatorias.** A factura-electrónica or RUT resolución may be modified by a later one. If a current consolidated text on the DIAN page has inline notes about modifications, keep them.
- **Plazos resolution year-vs-applies-to.** The year in the resolution number is the year the resolución was **issued**, not the year plazos apply to (e.g., Resolución 1729/**2025** sets plazos for **2026**).

## Notes

- This brief fills gaps left by Brief 07. Brief 07 hit factura-electrónica thoroughly but skipped UVT, plazos calendario, RST, and most of the annual exógena/RUT resoluciones.
- Target is ~85 resoluciones across F1, F3, F4 supplemental. If you find materially fewer in any one family, flag the gap.

## When you're done

1. Hand off `brief_13_resoluciones_dian_uvt_rst.md` to the coordinator.
2. Update this file: `Status: ✅ delivered` + delivery note.
