# Brief 12 — Cambiario + societario

**Owner:** unassigned
**Status:** 🟡 not started
**Sprint:** 3 (priority #9)
**Estimated effort:** 2–3 days

---

## What you are looking for

Documents from four very different families, all bundled into this brief because they all relate to cross-border + corporate matters:

| Topic | What | Count |
|---|---|---:|
| **K1** — Cambiario regulation | Articles of Resolución Externa 1 de 2018 of the Junta Directiva del Banco de la República | ~25 |
| **K2** — Cambiario operational manual | Numerales of DCIN-83 (the BanRep operational manual for cambiario) | ~40 |
| **K3** — Código de Comercio (sociedades) | Articles of the Código de Comercio that deal with sociedades (Libro Segundo) | ~60 |
| **K4** — S.A.S. and S.A. corporate laws | All articles of Ley 222 de 1995 and Ley 1258 de 2008 (S.A.S.) | ~25 |

Total: approximately **150 documents**.

## Where to find the documents

**K1 — Resolución Externa 1/2018 (BanRep):**
- BanRep landing: `https://www.banrep.gov.co/es/normatividad/resolucion-externa-1-2018`
- BanRep compendium (consolidated text + amendments): `https://www.banrep.gov.co/es/normatividad/compendios/resolucion-externa-1-2018`
- Direct PDF compendium: `https://www.banrep.gov.co/sites/default/files/reglamentacion/compendio-res-ext-1-de-2018.pdf`
- DIAN-hosted version: `https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_banrepublica_jd-0001_2018.htm`

**K2 — DCIN-83:**
- BanRep normatividad index: `https://www.banrep.gov.co/es/normatividad` — search for "DCIN 83" or "Manual Cambiario"
- The DCIN-83 is a "manual" (not a law), structured into capítulos and numerales. The version that lives at BanRep is the current one — there are no historical versions to track.

**K3 — Código de Comercio:**
- Senate Código de Comercio (paginated): `https://www.secretariasenado.gov.co/senado/basedoc/codigo_comercio.html`
- The Código de Comercio has ~2032 articles total. We need only Libro Segundo (sociedades), which is **roughly Arts. 98–514**.

**K4 — Ley 222/1995 + Ley 1258/2008:**
- Senate Ley 222: `https://www.secretariasenado.gov.co/senado/basedoc/ley_0222_1995.html`
- Senate Ley 1258: `https://www.secretariasenado.gov.co/senado/basedoc/ley_1258_2008.html`

## What to deliver per document

The schema varies a little per family:

**For K1 (Resolución Externa 1/2018):**
1. Full text per article (the resolución has numbered articles).
2. Article number.
3. URL.
4. Issued: 2018-MM-DD.

**For K2 (DCIN-83):**
1. Full text per numeral.
2. Identifier as printed: "Capítulo 5, Numeral 3" — give us **both** the chapter number and the numeral number.
3. URL.
4. Issue date: leave blank or use "current as of YYYY-MM-DD" since DCIN-83 is a living manual.

**For K3 (Código de Comercio articles 98–514, Libro Segundo, sociedades):**
1. Full text per article.
2. Article number (just the integer, e.g., "98", "515").
3. URL — the exact `_prNN.html` segment.
4. Issue date: 1971 (the original Código de Comercio, Decreto 410/1971); respect amendment notes.

**For K4 (Ley 222 + Ley 1258 — full text, all articles):**
1. Full text per article.
2. Article number.
3. URL.
4. Issue dates: Ley 222 de 1995 (issued 1995-12-20); Ley 1258 de 2008 (issued 2008-12-05).

## How to package

**Option B recommended** — one markdown file, four sections (one per topic):

Filename: `brief_12_cambiario_societario.md`

Structure:

```
# K1 — Resolución Externa 1 de 2018 (BanRep)
URL: https://www.banrep.gov.co/...
Issued: 2018-MM-DD

## Artículo 1
[full text]

## Artículo 5
[full text]

---

# K2 — DCIN-83 (Manual Cambiario, BanRep)
URL: https://www.banrep.gov.co/...
Current as of: YYYY-MM-DD

## Capítulo 1, Numeral 1
[full text]

## Capítulo 1, Numeral 2
[full text]

## Capítulo 5, Numeral 3
[full text]

---

# K3 — Código de Comercio, Libro Segundo (sociedades)

## Artículo 98 CCo
URL: https://www.secretariasenado.gov.co/.../codigo_comercio_pr<NN>.html
Issued: 1971 (Decreto 410/1971)

[full text]

---

# K4 — Ley 222 de 1995

## Artículo 1
URL: https://www.secretariasenado.gov.co/.../ley_0222_1995.html
Issued: 1995-12-20

[full text]

---

# K4 — Ley 1258 de 2008 (S.A.S.)

## Artículo 1
URL: https://www.secretariasenado.gov.co/.../ley_1258_2008.html
Issued: 2008-12-05

[full text]
```

## Special things to watch for

- **K1 and K2 are BanRep documents, hosted on BanRep's site.** BanRep's site sometimes restructures — if a URL stops working, try the search index at `https://www.banrep.gov.co/es/normatividad`.
- **K1 (Resolución Externa 1/2018) has been amended many times.** Use the **compendium** (consolidated current text), not the original 2018 publication. The compendium URL above gives you the latest consolidated version.
- **K2 (DCIN-83) is a manual, not a law.** Its sections are "capítulos" and "numerales," not "artículos." Capture **both** identifiers when you note a numeral.
- **K3 (Código de Comercio) is large.** We want **Libro Segundo only** — articles roughly 98 through 514. Skip the rest.
- **K4 is the simplest part of the brief.** Both Ley 222 and Ley 1258 are short and clean.

## Notes

- **The four families have different sources.** You may end up with four separate browsing sessions — one for BanRep, one for DCIN, one for the Senate's Código de Comercio, one for the Senate's Ley 222 + Ley 1258. That's fine.
- **Target is ~150 documents total** (~25 + ~40 + ~60 + ~25). Roughly proportional to the table above. If you find materially fewer in any one family, flag the gap.
- **Sub-paragraphs.** As with other briefs, sub-paragraphs (parágrafos, numerales, literales inside an article) stay inside the article entry — don't split.

## When you're done

1. Hand off `brief_12_cambiario_societario.md` to the coordinator.
2. Update this file: `Status: ✅ delivered` + delivery note.
