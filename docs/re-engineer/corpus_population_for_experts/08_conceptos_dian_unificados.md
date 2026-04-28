# Brief 08 — Conceptos DIAN unificados

**Owner:** unassigned
**Status:** 🟡 not started
**Sprint:** 1 (priority #3)
**Estimated effort:** 2–3 days

---

## What you are looking for

The five **unified DIAN doctrinal opinions** ("conceptos unificados"). These are large compilations where DIAN consolidates its position on a tax topic; each unified concepto is split into many numbered sub-questions ("numerales").

We need approximately **390 numerales** in total, drawn from these five unified conceptos:

| Topic | Concepto | Numerales (approx.) |
|---|---|---:|
| **G1** — IVA | Concepto Unificado de IVA (the single doctrinal source for IVA) | ~60 |
| **G2** — Renta | Concepto Unificado de Renta (the single biggest one) | ~100+ |
| **G3** — Retención en la fuente | Concepto Unificado de Retención | ~60 |
| **G4** — Procedimiento + sanciones | Concepto Unificado de Procedimiento Tributario | ~60 |
| **G5** — Régimen Simple | Concepto Unificado de Régimen Simple | ~60 |
| **G6** — pre-existing test (already delivered, do not re-collect) | Concepto 100208192-202 (IA en dividendos NCRGO) | (already in our system) |

For each unified concepto, the DIAN page lists numerales like "Numeral 1.1.1," "Numeral 2.4," etc. We need each numeral as a separate entry.

## Where to find the documents

- **DIAN normograma per-concepto pages:** URL pattern is roughly `https://normograma.dian.gov.co/dian/compilacion/docs/concepto_tributario_dian_<NUM>.htm` — the `<NUM>` is the concepto number.
- **Master index:** `https://www.dian.gov.co/fizcalizacioncontrol/herramienconsulta/NIIF/ConceptosDian/Paginas/default.aspx` — search for "unificado" and you'll find the five compilations.

The exact concepto numbers for each topic vary by year (DIAN periodically issues a new unified concepto). Use the **most recent** unified concepto for each topic that you can find on the index.

## What to deliver per numeral

For each numeral inside each unified concepto:

1. **Full text** of the numeral — its own internal heading (e.g., "Numeral 1.1.1. ¿Qué es el régimen tributario...?") plus the body answer.
2. **Numeral identifier** as printed — typically a dotted-decimal like "1.1.1" or "2.4.7".
3. **Parent concepto identifier** — the full concepto number like "100208192-202" (with the hyphen — DIAN's unified conceptos use a number-hyphen-number format).
4. **URL** — the **exact per-concepto page** on DIAN normograma (hard requirement, no exceptions): URL pattern is `https://normograma.dian.gov.co/dian/compilacion/docs/concepto_tributario_dian_<NUM>.htm` with the actual concepto number filled in. Same URL across every numeral inside one concepto is correct and required (they all live on that page). **Never** substitute the conceptos master index or the DIAN homepage.
5. **Issue date** of the parent concepto.
6. **Topic tag** — which of G1/G2/G3/G4/G5 this concepto belongs to.

## How to package

**Option B recommended** — one markdown file with sections per concepto, sub-sections per numeral:

Filename: `brief_08_conceptos_dian_unificados.md`

Structure:

```
# Concepto Unificado de Renta (G2): Concepto DIAN <NUMBER>
URL: https://normograma.dian.gov.co/.../concepto_tributario_dian_<NUMBER>.htm
Issued: 2024-MM-DD

## Numeral 1.1.1
[full text]

## Numeral 1.1.2
[full text]

## Numeral 2.4.7
[full text]

---

# Concepto Unificado de IVA (G1): Concepto DIAN <NUMBER>
URL: ...
Issued: ...

## Numeral 1.1
[full text]

...
```

## Special things to watch for

- **G6 is already done — DO NOT re-collect it.** Concepto 100208192-202 is in our system already. Skip it.
- **Numeral boundaries are critical.** A wrong numeral split corrupts the entire delivery. When in doubt, **err on the side of including more text in the previous numeral** — better to over-deliver than to bleed text across boundaries. The dev team can clean up over-inclusion later but cannot recover missing text.
- **DIAN's numeral format varies.** Some unified conceptos use "Numeral 1.1.1," others just bold a "1.1.1." at the start of a paragraph. Look for the consistent visual pattern within each concepto and use it as your delimiter.
- **Cross-references between numerales.** A numeral may say "Ver Numeral 2.3.1." Keep these cross-refs in the text.

## Pilot recommendation

Before you tackle G1–G5 in full, **try one numeral split on a single section first** and show the developer team — that confirms your boundary detection is correct before you commit hours to the full extraction. The dev team will tell you within an hour or two whether your split is good.

## Notes

- This is the trickiest brief in Sprint 1 because of the numeral-boundary problem. Take it slow, ask questions early.
- Target is ~390 numerales total. If you find materially fewer per concepto than the table says, your boundary detection may be too coarse (collapsing several numerales into one); if materially more, too fine (splitting a single numeral into pieces). Either way, the dev team can help debug.

## When you're done

1. Hand off `brief_08_conceptos_dian_unificados.md` to the coordinator.
2. Update this file: `Status: ✅ delivered` + delivery note.
