# For the corpus-research experts — start here

Welcome. This folder is **just for you**. Everything here is in plain language. You will not see any code, JSON, or technical jargon — that lives in a different folder for the developers.

## What we need from you

You scour the web for **legal documents** — articles of laws, decrees, resolutions, court rulings, official opinions — and send them to us. We turn what you send into the database.

## What you do NOT need to worry about

* No coding.
* No JSON or other file formats invented for software.
* No "canonical id," "scraper," "regex," "validation snippet," anything technical.
* No re-formatting beyond what each brief asks.

If something in here looks technical or confusing, **stop and ask** — that means the brief is wrong, not you.

## How to pick what to work on

We split the job into **12 source families**, one brief per family. Each brief tells you:

1. **What** legal documents to find (e.g., "all articles of the Código Sustantivo del Trabajo").
2. **Where** to find them online (specific government websites and URLs).
3. **How many** documents we expect (a target count — give or take 20% is fine).
4. **What** to send back (always: the exact text + the article number + the URL + the date if visible).
5. **How** to package what you send back (a folder of text files, or a single markdown document — your choice).

## Priority order — please follow this

We work in three sprints. Pick the lowest-numbered brief that does not have an "Owner" yet.

**Sprint 1 — start here (~440 documents total):**
1. [Brief 11 — Pensional, Salud, Parafiscales](11_pensional_salud_parafiscales.md) — ~80 documents — the smallest, the easiest, the pilot
2. [Brief 01 — Código Sustantivo del Trabajo (CST)](01_cst.md) — ~170 documents — labor code
3. [Brief 08 — Conceptos DIAN unificados](08_conceptos_dian_unificados.md) — ~390 documents — DIAN doctrine
4. [Brief 07 — Resoluciones DIAN](07_resoluciones_dian.md) — ~140 documents — UVT, factura electrónica, etc.

**Sprint 2 — DUR family (~1,230 documents total, single source page):**

5. [Brief 02 — DUR 1625/2016, Libro 1 (renta)](02_dur_1625_renta.md) — ~500 documents
6. [Brief 03 — DUR 1625/2016, IVA + retefuente](03_dur_1625_iva_retefuente.md) — ~280 documents
7. [Brief 04 — DUR 1625/2016, procedimiento + sanciones](04_dur_1625_procedimiento.md) — ~200 documents
8. [Brief 05 — DUR 1072/2015, laboral](05_dur_1072_laboral.md) — ~250 documents

**Sprint 3 — long tail (~680 documents total):**

9. [Brief 12 — Cambiario + societario](12_cambiario_societario.md) — ~150 documents
10. [Brief 09 — Conceptos individuales + Oficios DIAN](09_conceptos_dian_individuales.md) — ~430 documents
11. [Brief 10 — Jurisprudencia (sentencias CC, CE, autos)](10_jurisprudencia_cc_ce.md) — ~70 documents
12. [Brief 06 — Decretos legislativos COVID](06_decretos_legislativos_covid.md) — ~30 documents

## How to claim a brief

1. Pick the lowest-numbered brief without an Owner.
2. At the top of the brief file, change `Owner: unassigned` to your name.
3. Tell whoever's running the campaign that you've started.
4. Get to work.

## How to deliver what you find

For **every** document/article you collect, give us **four pieces of information**:

1. **The full text**, copied exactly as published. Do not paraphrase. Do not summarize. Keep inline notes (e.g. "Modificado por Ley 2277/2022", "Derogado por Decreto X") inside the text — those notes matter to us.
2. **The article number or document identifier** — e.g., "Artículo 22", "Sentencia C-481 de 2019", "Oficio DIAN 018424 de 2024".
3. **The URL** where you found it. **Hard requirement, no exceptions:** the URL must point to the **exact source page** the article came from — not a homepage, not a master index, not a search-results page.
   * ✅ `https://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo_pr001.html` — the specific paginated segment
   * ✅ `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm` — the single-page DUR (same URL across all its articles is fine because that's where they actually live)
   * ❌ `https://normograma.dian.gov.co/` — homepage
   * ❌ `https://www.dian.gov.co/normatividad/Paginas/Resoluciones.aspx` — master index, not the per-resolución page
   * If the document only exists behind a search query and has no stable URL, give us the search URL + the exact query you used + the date you fetched it.
   * If the document is a PDF, the URL is the URL of the PDF file itself, not the page that links to it.
4. **The date the document was issued**, if visible in the source. If not, leave blank.

Two acceptable packaging formats — pick whichever is easier for you:

**Option A — folder of text files.** One file per article/document. Filenames like `art_22.txt`, `sentencia_c-481_2019.txt`. Inside each file: the four pieces above, with a clear separator like `---`.

**Option B — one markdown document.** One file per brief, with a header for each article. Like this:

```
## Artículo 22
URL: https://...
Issued: 1950-08-05

[full text of Article 22 here, exactly as published]

---

## Artículo 23
URL: https://...
Issued: 1950-08-05

[full text of Article 23 here]
```

Either format is fine. Tell us which you used.

## What the developers do with what you send

Once you hand off your folder/document, we (the developers) format it for the database, assign internal identifiers, run quality checks, and load it. You don't see any of that. If we run into a problem with a specific document, we'll come back to you with a question.

## When you're done with a brief

1. Hand off your folder/document to whoever's coordinating the campaign.
2. At the top of the brief file, change `Status: 🟡 not started` to `Status: ✅ delivered`.
3. Add a one-line note saying when you finished and roughly how many documents you delivered.

## When you hit a problem

If the source website is broken, the document is harder to find than expected, or you think you've found the wrong document — **stop and ask**. Don't guess. Add a note to the brief's `Notes` section saying what went wrong, and tag the campaign coordinator. We will help.

## Questions you might have

**"Do I need any technical skills?"** No. You need a web browser, a text editor, and patience. If a brief asks you to do something technical, that brief is wrong — flag it.

**"What if a document is in PDF only?"** Send us the PDF and either copy the text into a `.txt` file as best you can, or note that the text needs OCR. We can OCR ourselves if needed.

**"What if I find a document that is more recent than what the brief says?"** Send it anyway with a note. Newer-than-expected is good; we want current law.

**"What if an article was repealed (derogado)?"** Send it anyway with the inline repeal note. We track what's repealed; we don't skip it.

**"What if I'm not sure I found the right thing?"** Better to send than to skip. Note your uncertainty in the file. We'll review.

---

*Last updated 2026-04-28. Maintained by the developer team. If anything in here contradicts a specific brief, the brief wins for that family — and tell us so we can fix this README.*
