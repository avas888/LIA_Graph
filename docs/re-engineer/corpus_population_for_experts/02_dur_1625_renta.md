# Brief 02 — DUR 1625/2016, Libro 1 (renta)

**Owner:** unassigned
**Status:** 🟡 not started
**Sprint:** 2 (priority #5; first of the four DUR briefs)
**Estimated effort:** 1–2 days

---

## What you are looking for

The articles of **Libro 1** of the Decreto Único Reglamentario 1625 of 2016 (the master regulation that interprets the Estatuto Tributario for income tax / renta).

We need approximately **500 articles**, all from Libro 1.

## Where to find the documents

A single page on the DIAN website:

- **Source:** `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm`

This one page contains the full DUR (all three libros). For this brief you only want **Libro 1**. The articles in Libro 1 are numbered with a dotted decimal — you'll see them printed as things like:

- "Artículo 1.1.1.1"
- "Artículo 1.2.1.10"
- "Artículo 1.5.2.4"
- etc.

Anything that starts with "Artículo 1." (and is in Libro 1 according to the page's headers) is what we need. The "1." at the start is part of the article number — keep it.

## What to deliver per article

For **each** article of Libro 1:

1. **Full text** of the article — copied exactly, including the title heading (e.g., "Artículo 1.5.2.4. Determinación de la renta líquida...") and the article body.
2. **Article number** as printed (e.g., "1.5.2.4" — preserve the exact dotted decimal). If the article has a hyphen-suffix like "1.3.45-2", preserve the hyphen.
3. **URL** — the **exact source page** (hard requirement, no exceptions): for DUR 1625 it's the single-page URL `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm`. The same URL repeats for every article in this brief because that's the actual page they all live on — that's correct and required. **Never** substitute the DIAN homepage or the normograma index.
4. **Issue date** — the DUR 1625 itself was issued 2016-08-02; that's the issue date for any article that hasn't been amended. If an article carries an amendment note (e.g., "Modificado por Decreto 1474 de 2025"), keep that note in the text.

## How to package what you deliver

**Option B (recommended)** — one markdown file per brief, with headers per article:

Filename: `brief_02_dur_1625_renta.md`

```
## Artículo 1.1.1.1
URL: https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm
Issued: 2016-08-02

[full article text]

---

## Artículo 1.1.1.2
URL: ...
Issued: 2016-08-02

[full text]
```

Because there are ~500 articles, the file will be large. That's fine — keep it as one file.

## Special things to watch for

- **Compound article numbers.** You may see articles like "Artículo 1.3.45-1" or "Artículo 1.3.45-2". These are SEPARATE articles, even though they share the "45" base number. Treat each as its own entry. Preserve the hyphen exactly.
- **Inline amendment notes.** Same as Brief 01: keep notes like `[Modificado por Decreto 1474 de 2025]` inside the article text. They are critical.
- **Cross-references.** Articles often reference other DUR articles ("Ver también el Artículo 1.5.2.1 de este Decreto"). Preserve these — they are part of the article text.
- **Articles split across HTML page-breaks.** The DIAN page may visually split a long article. If you see a `<div class="page-break">` or similar, concatenate the text — one article = one entry.
- **NEVER invent article numbers.** Only deliver articles whose number you actually saw on the DIAN page. If you're unsure whether something is a separate article or a sub-unit of the previous article, treat it as a sub-unit and include it inside the previous article entry.

## Notes

- **Do not encode the libro / parte / título / capítulo as separate fields.** The hierarchy is already built into the dotted-decimal article number; we don't need it broken out. Just give us the number as printed.
- **Letter suffixes (-A, -B) are very rare in DUR 1625.** If you see one, double-check it's really there in the source — don't invent letter suffixes.
- **What about sub-paragraphs (parágrafos, numerales)?** Keep them inside the article text — they don't get their own entry.

## When you're done

1. Hand off `brief_02_dur_1625_renta.md` to the coordinator.
2. Update this file: `Status: ✅ delivered`, add a note like `2026-MM-DD — delivered ~<actual count> articles via brief_02_dur_1625_renta.md`.
3. Tell the developer team you finished — they will use the same parser approach to handle Briefs 03 and 04 (same DUR, different libros), so coordinate handoff.
