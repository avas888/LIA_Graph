# Brief 09 — Conceptos individuales + Oficios DIAN

**Owner:** unassigned
**Status:** 🟡 not started
**Sprint:** 3 (priority #10)
**Estimated effort:** 2–3 days

---

## What you are looking for

Two kinds of doctrinal documents from DIAN — both in the "long tail" of guidance:

1. **Conceptos individuales (non-unified):** Short opinion pieces on specific tax questions, numbered with a long internal number. Example: "Concepto DIAN 003028."
2. **Oficios DIAN:** Official letters DIAN sends in response to specific taxpayer inquiries. Example: "Oficio DIAN 018424 de 2024."

Together: approximately **430 documents**, spread across topics:

| Topic | Family | Count |
|---|---|---:|
| **H1** — Régimen Simple | Conceptos individuales on RST | ~50 |
| **H2** — Retención en la fuente | Conceptos on retención | ~50 |
| **H3a + H3b** — Renta | Conceptos individuales on renta | ~120 |
| **H4a + H4b** — IVA | Conceptos individuales on IVA | ~80 |
| **H5** — Procedimiento | Conceptos on correcciones, firmeza, devoluciones | ~50 |
| **H6** — Oficios | Oficios DIAN (recurrent topics) | ~80 |

## Where to find the documents

- **Master conceptos index:** `https://www.dian.gov.co/fizcalizacioncontrol/herramienconsulta/NIIF/ConceptosDian/Paginas/default.aspx` — filter by "individual" (not unified).
- **Master oficios index:** `https://www.dian.gov.co/normatividad/Paginas/Oficios.aspx` — by year and topic.
- **Per-concepto URL pattern:** `https://normograma.dian.gov.co/dian/compilacion/docs/concepto_tributario_dian_<NUM>.htm`
- **Per-oficio URL pattern:** `https://normograma.dian.gov.co/dian/compilacion/docs/oficio_dian_<NUM>_<YEAR>.htm`

## What to deliver per document

For each concepto / oficio:

1. **Full text** copied exactly. These are usually short (1–5 pages).
2. **Document type:** "Concepto" or "Oficio" — be explicit.
3. **Document number** as printed:
   - For conceptos: just the number, e.g., "3028" or "100208192" (no year — DIAN doesn't year-suffix individual conceptos).
   - For oficios: number plus year, e.g., "018424" + year "2024".
4. **URL** — the exact per-document page.
5. **Issue date** — visible at the top of most documents.
6. **Topic tag** — H1, H2, H3 (renta), H4 (IVA), H5 (procedimiento), or H6 (oficio).

## How to package

**Option B recommended** — one markdown file per topic if helpful, OR a single big file with sections by topic:

Filename: `brief_09_conceptos_dian_individuales.md` (or split into `_h1.md`, `_h2.md`, etc. if easier).

Structure:

```
# H6 — Oficios DIAN

## Oficio DIAN 018424 de 2024
URL: https://normograma.dian.gov.co/.../oficio_dian_018424_2024.htm
Issued: 2024-MM-DD
Topic: H6

[full text]

---

## Oficio DIAN 008526 de 2005
URL: ...
Issued: 2005-MM-DD
Topic: H6

[full text]

---

# H3 — Conceptos individuales sobre renta

## Concepto DIAN 003028
URL: https://normograma.dian.gov.co/.../concepto_tributario_dian_003028.htm
Issued: 2024-MM-DD
Topic: H3

[full text]

...
```

## Special things to watch for

- **Concepto vs Oficio — different families, do not mix them up.** A concepto is identified by **number only** (no year). An oficio is identified by **number + year**. If a document is titled "Oficio Nº 018424 del 2024," that's an oficio, not a concepto. If a document is titled "Concepto 003028," that's a concepto. Mixing them up will cause problems downstream.
- **Concepto numbers can be small (3–4 digits) or huge (8–9 digits).** Both are real. Don't normalize them; keep whatever the source uses.
- **Oficios from 2005 and earlier may have a different numbering scheme.** Capture whatever the source prints; flag if anything looks unusual.

## A note on completeness

There are thousands of conceptos and oficios in DIAN's database. We don't need all of them — we need the **most-cited** ones, the ones accountants actually look up. Use the master indexes' "most consulted" or "destacados" filters if available, or work down from the most recent year.

If you collect ~430 documents covering the H1–H6 topics, you've hit the target. Don't try to be exhaustive.

## Notes

- This brief is paired with a developer-side task to fix a regex issue (the developers know about it). You don't need to think about it.
- Target is ~430 documents. Materially less is OK if you're focused on the most-cited; materially more (over 700) is probably scope creep.

## When you're done

1. Hand off your file(s) to the coordinator.
2. Update this file: `Status: ✅ delivered` + delivery note.
