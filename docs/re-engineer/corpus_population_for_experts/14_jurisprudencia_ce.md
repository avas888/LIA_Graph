# Brief 14 — Jurisprudencia Consejo de Estado (CE) — sentencias de unificación + autos de suspensión

**Owner:** unassigned
**Status:** 🟡 not started
**Sprint:** 4 (gap-fill — added 2026-04-28 after first-pass campaign)
**Estimated effort:** 2 days

---

## What you are looking for

Court documents from the **Consejo de Estado** (CE) — the high administrative court — focused on the **Sección Cuarta** (which handles tax/fiscal matters). Two families:

| Topic | What | Count |
|---|---|---:|
| **I3** — CE sentencias de unificación, Sección Cuarta | Unification rulings on tax law: alcance de deducciones (Art. 107 ET), corrección de declaraciones, devoluciones de saldos a favor, compensaciones, IVA on specific transactions | ~25 |
| **I4** — Autos de suspensión provisional, CE | Provisional-suspension orders blocking enforcement of a tax decreto or resolution while a constitutionality challenge is pending | ~15 |

**What we already have (so do NOT re-collect):** Brief 10 already shipped 16 Corte Constitucional sentencias on tax principles (the I2 family) and the 5-acid-test I1 sentencias. Anything CC-only is out of scope here. **This brief is CE-only.**

## Where to find the documents

CE has a JS-rendered SPA which is hard to navigate by URL alone. Two practical paths:

- **CE relatoría / decisiones index:**
  - `https://www.consejodeestado.gov.co/decisiones_u/` — unification sentencias index
  - `https://www.consejodeestado.gov.co/seccion-cuarta/` — Sección Cuarta landing
  - You may need to **navigate the site interactively** and copy text from the page rather than fetch a URL.
- **DIAN-mirror (often easier):**
  - `https://normograma.dian.gov.co/dian/compilacion/` — DIAN often republishes the full text of CE decisions that affect tax law. Search the normograma index by radicado number.
  - Example URL pattern (verified-real for one Sección Cuarta unification): `https://normograma.dian.gov.co/dian/compilacion/docs/25000-23-37-000-2014-00507-01_2022CE-SUJ-4-002.htm`

Try DIAN first if the sentencia is tax-related — the text is the same and DIAN's URL is stable.

## What to deliver per court document

For each sentencia or auto:

1. **Full text** — the complete decision. CE rulings can be 20–80 pages. Copy everything: case facts, considerations ("considerandos"), and the operative parts ("RESUELVE"). The "RESUELVE" section is the most important; never truncate it.
2. **Document identifier** as the court uses it:
   - **CE sentencia:** the **radicado number** plus the **decision date**. Full radicado looks like `25000-23-37-000-2014-00507-01(28920)`. The internal radicado number (the part the CE uses to identify the case) is the integer in parentheses or the trailing 4–5-digit number — e.g., `28920`. The decision date is the date the court signed the ruling, in `YYYY-MM-DD`.
   - **CE auto:** same as a CE sentencia — radicado number + decision (or notification) date in `YYYY-MM-DD`.
3. **URL** — the exact source page. **Hard requirement, no exceptions:** must point to the exact ruling, not a search results page.
4. **Decision date** — required for both sentencias and autos. Always in `YYYY-MM-DD` form.
5. **Sección** (for CE only) — e.g., "Sección Cuarta," "Sala Plena," "Sala Especial de Decisión." Metadata only.
6. **Topic tag** — which of I3 / I4 the document falls under.

## How to package

**Option B recommended** — one markdown file with sections per court family:

Filename: `brief_14_jurisprudencia_ce.md`

Structure:

```
# I3 — CE Sección Cuarta unificación

## Radicado 28920, decided 2025-07-03
URL: https://normograma.dian.gov.co/.../25000-23-37-000-...
Sección: Cuarta
Decision date: 2025-07-03
Full radicado: 25000-23-37-000-YYYY-NNNNN-01(28920)
Topic: I3 — Unificación · Devoluciones de saldos a favor

[full text — case facts, considerandos, RESUELVE]

---

## Radicado <NNNNN>, decided YYYY-MM-DD
URL: ...
[etc.]

---

# I4 — Autos CE de suspensión provisional

## Auto radicado 082, decided 2026-04-15
URL: ...
Decision date: 2026-04-15
Topic: I4 — Suspensión provisional · Decreto 1474/2025 IE

[full text]
```

## Verified-real examples to anchor against

You can rely on these — they are pre-vetted by the dev team and present in the existing corpus YAML:

- **I3 sentencias CE de unificación:**
  - Radicado **28920**, Sección Cuarta, decided **2025-07-03** — already used as an acid test in the corpus YAML.
- **I4 autos CE de suspensión provisional:**
  - **Auto 082 de 2026**, decided **2026-04-15** — Decreto 1474/2025 IE provisions.
  - **Auto 084 de 2026**, decided **2026-04-15** — Decreto 1474/2025 IE provisions.
  - **Auto radicado 28920**, decided **2024-12-16** — I.A. dividendos NCRGO.

For any sentencia or auto **not** on this list, verify it against the CE relatoría or the DIAN normograma before noting it. Do not invent radicado numbers.

## Special things to watch for

- **Radicado-only is NOT enough.** A CE document must include both the radicado number **and** the decision (or notification) date. Two different rulings from Sección Cuarta in 2022 might share a year but differ in radicado number and date. Always capture both — `auto.ce.082.2026` (radicado-only) is rejected by the database; `auto.ce.082.2026.04.15` (radicado + full date) is the valid form.
- **The "RESUELVE" section.** Court rulings are long. The most important part is the operative section ("RESUELVE..."). Make sure that section is copied in full — that's where the legal effect is.
- **Inline references.** CE rulings reference the laws they're judging (e.g., "Decreto 1474 de 2025," "Ley 2277 de 2022," "Art. 107 ET"). Keep those references verbatim.
- **CE site is JS-rendered.** Don't be surprised if a URL "works" only when you click through the search interface. If you cannot get a stable URL, fetch from the DIAN-hosted mirror and use that URL.
- **PDFs.** Many CE rulings are only available as PDFs. If a ruling is PDF-only, copy the text into your markdown and use the PDF URL itself as the source URL.

## Topics to look for

For **I3** (CE unificación), focus on these tax-law unification topics:

- Alcance de deducciones (Art. 107 ET) — necesidad, causalidad, proporcionalidad.
- Corrección de declaraciones y firmeza.
- Devoluciones de saldos a favor.
- Compensaciones de retención en la fuente.
- IVA on specific transactions (arrendamientos, servicios públicos domiciliarios, etc.).

For **I4** (autos), focus on autos that suspend the operation of a tax decreto or resolución while a constitutionality challenge is pending. These appear when there's a major reform — the I.E. round (Decreto 1474/2025) and the Ley 2277 cycle are recent examples.

## Notes

- This brief is the most "research-y" — finding the right documents takes some judgment. If you're uncertain whether a document is in scope, copy it anyway and tag it with your uncertainty.
- Target is ~40 documents total (25 + 15). Less is OK if you're confident in coverage.
- **CE site navigation is hard.** Set aside time for site exploration. If you find a stable URL pattern that works (e.g., a specific search query parameter), share it with the campaign coordinator — we can use it for future briefs.

## When you're done

1. Hand off `brief_14_jurisprudencia_ce.md` to the coordinator.
2. Update this file: `Status: ✅ delivered` + delivery note.
