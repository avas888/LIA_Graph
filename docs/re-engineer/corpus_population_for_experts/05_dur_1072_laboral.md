# Brief 05 — DUR 1072/2015 (laboral)

**Owner:** unassigned
**Status:** 🟡 not started
**Sprint:** 2 (priority #8)
**Estimated effort:** 1–2 days

---

## What you are looking for

Articles of the Decreto Único Reglamentario 1072 of 2015 — the master regulation for **labor and social security** matters (different DUR from 1625; this one is the labor counterpart).

We need approximately **250 articles**, focused on:

- **Riesgos laborales** (occupational hazards) — articles whose number starts with "2.2.4."
- **SST (Seguridad y Salud en el Trabajo)** — articles whose number starts with "2.2.5."
- Plus a smaller number of general / setup articles whose number starts with other "2.2." prefixes.

## Where to find the documents

Three possible sources, in priority order. **Try them in this order — if one fails, move to the next:**

1. **DIAN (preferred):** `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1072_2015.htm`
   - **Warning:** the brief author observed a 404 on this URL during research. Try it first; if it 404s, skip to source 2.
2. **MinTrabajo PDF (authoritative fallback):** the actual PDF file lives on the Ministerio de Trabajo website. Search for "DUR Decreto 1072 2015 Actualizado" on `https://www.mintrabajo.gov.co/`.
3. **Senate (last-resort fallback):** `https://www.secretariasenado.gov.co/senado/basedoc/decreto_1072_2015.html`

DUR 1072's articles are also numbered with dotted decimals (e.g., "Artículo 2.2.4.6.42"). The leading "2." indicates Libro 2 (régimen laboral).

## What to deliver per article

Same schema as the other DURs:

1. **Full text** copied exactly.
2. **Article number** as printed (e.g., "2.2.4.6.42").
3. **URL** — the **exact source page** of whichever source you ended up using (hard requirement, no exceptions): for DIAN it's `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1072_2015.htm`; for MinTrabajo it's the URL of the PDF file itself (not the page that links to it); for the Senate fallback it's `https://www.secretariasenado.gov.co/senado/basedoc/decreto_1072_2015.html`. **Note in your delivery which source you used.** Never substitute a homepage or index.
4. **Issue date** — DUR 1072 baseline is 2015-05-26; respect amendment notes inside the article text.

## How to package

**Option B recommended** — one markdown file:

Filename: `brief_05_dur_1072_laboral.md`

Add a note at the top of the file saying which source you used (DIAN / MinTrabajo PDF / Senate), and the date you fetched it.

## Special things to watch for

- **The 404 problem.** If DIAN 404s, that's the brief author's known issue. Use the MinTrabajo PDF instead and tell the coordinator. Don't fabricate articles to fill the gap.
- **Many SST articles were modified by Resolution 0312/2019 and other later resolutions.** If you see inline notes like "Modificado por Resolución 0312 de 2019," keep them in the text. We process the modifications downstream.
- **Many DUR 1072 articles were derogated by Decree 472/2015 and subsequent norms.** Same treatment — keep the inline note.
- **PDF format.** If you use the MinTrabajo PDF, you may need to copy text page-by-page. That's fine. Watch for line-break artifacts and clean those up minimally (don't change the meaning).

## Notes

- This brief overlaps in source-URL with phases E6 + J8 of our internal tracking. The developers handle the overlap; you just deliver the articles once.
- Target is ~250 articles. If you find materially fewer, that's likely a parsing-difficulty issue, not a real gap — flag it.

## When you're done

1. Hand off `brief_05_dur_1072_laboral.md` to the coordinator.
2. Update this file: `Status: ✅ delivered` + delivery note.
