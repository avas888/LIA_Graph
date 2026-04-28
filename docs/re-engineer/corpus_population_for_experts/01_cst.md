# Brief 01 — Código Sustantivo del Trabajo (CST)

**Owner:** unassigned
**Status:** 🟡 not started
**Sprint:** 1 (priority #2)
**Estimated effort:** 4–6 hours

---

## What you are looking for

The articles of Colombia's labor code, **only specific ranges** — not the whole code.

We need approximately **170 articles**, divided into four ranges:

| Range | Topic | Count |
|---|---|---:|
| Art. 22 to Art. 50 | individual labor contracts (contratos individuales) | ~29 |
| Art. 51 to Art. 101 | social benefits (prestaciones sociales) | ~51 |
| Art. 158 to Art. 200 | working hours and rest (jornada y descansos) | ~43 |
| Art. 416 to Art. 492 | collective conflicts (conflictos colectivos) | ~47 |

Articles outside these ranges are NOT needed for this brief — skip them.

## Where to find the documents

The Senate's official site hosts the CST in paginated segments:

- **Master index:** `https://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo.html`
- The articles you need are spread across these segments:
  - `_pr001.html`, `_pr002.html`, `_pr003.html`, `_pr004.html` (covers Arts. 1 – ~250)
  - `_pr008.html` and onwards through `_pr016.html` (covers Arts. 416+)
- Full URL pattern: `https://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo_pr<NN>.html`

Open each segment, find the articles in the ranges above, copy them out.

## What to deliver per article

For **each** article in the ranges:

1. **Full text** of the article — copied exactly as printed on the Senate page, including title (e.g., "ARTÍCULO 22. DEFINICIÓN DE CONTRATO DE TRABAJO.") and body. Keep paragraph breaks.
2. **Article number** as printed (e.g., "22", or "22-A" if it has a sub-suffix — preserve the exact format).
3. **URL** — the exact `_prNN.html` page where you found the article (not the master index).
4. **Issue date** — leave blank; the CST as a whole was enacted in 1950 but individual articles have been amended over the decades. The amendment notes are inside the text, which is what we need.

## How to package what you deliver

Pick the format that's easier for you (see `README.md` Option A or B). For this brief, we recommend **Option B** (one markdown file with all articles), because the Senate site is a single source.

Filename suggestion: `brief_01_cst.md`

Inside, use headers like:

```
## Artículo 22
URL: https://www.secretariasenado.gov.co/.../codigo_sustantivo_trabajo_pr001.html

[full article text, exactly as published, including title and any amendment notes]

---

## Artículo 23
URL: ...

[full text]
```

## Special things to watch for

- **Amendment notes inside articles.** Many CST articles carry inline notes like `[Modificado por Ley 50 de 1990, Art. 5]` or `[Derogado por Ley 789 de 2002]`. **Keep these in the text exactly.** They are the most important part for us; we use them downstream to track what's currently in force.
- **Sub-paragraphs (parágrafos, numerales, literales).** Many articles have sub-units — keep them all together inside the one article entry. Do not split them into separate files.
- **Articles spanning two pages.** Sometimes Article 50 starts on `_pr001.html` and finishes on `_pr002.html`. Concatenate the text into one entry.
- **Article titles in CAPS.** The Senate publishes article titles in all caps — preserve that.

## Notes

- The CST has 492 articles total. We only need ~170. Don't get distracted by the others.
- The Senate site sometimes re-numbers segments — if `_pr008.html` doesn't have Art. 416, check `_pr009.html` and `_pr010.html`.
- If a Senate URL is broken or won't load, try the alternative source: `https://www.suin-juriscol.gov.co/` — search for "Código Sustantivo del Trabajo" and use that. Note in your delivery which source you used.

## When you're done

1. Hand off your `brief_01_cst.md` (or folder of text files) to the campaign coordinator.
2. Update the top of this file: `Status: ✅ delivered`, add a note like `2026-MM-DD — delivered ~170 articles via brief_01_cst.md`.
3. The developers will load it. If we have questions, we'll come back to you.
