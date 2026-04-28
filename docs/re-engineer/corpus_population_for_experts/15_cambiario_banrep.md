# Brief 15 — Cambiario BanRep — Resolución Externa 1/2018 + DCIN-83 (Manual Cambiario)

**Owner:** unassigned
**Status:** 🟡 not started
**Sprint:** 4 (gap-fill — added 2026-04-28 after first-pass campaign)
**Estimated effort:** 1–2 days

---

## What you are looking for

Two BanRep documents that govern Colombia's cambiario (foreign exchange) regime. Brief 12 already covered the Ley 222/Ley 1258/Código de Comercio side — this brief fills only the BanRep side.

| Topic | What | Count |
|---|---|---:|
| **K1** — Resolución Externa 1 de 2018 (JDBR) | All articles of Resolución Externa 1 de 2018 of the Junta Directiva del Banco de la República — the foundational cambiario regime | ~25 |
| **K2** — DCIN-83 Manual Cambiario | Numerales of DCIN-83 (the BanRep operational manual that organizes cambiario rules into capítulos and numerales) | ~30 |

Total: approximately **55 documents**. Brief 12 already covered K3 (Código de Comercio Libro II) and K4 (Ley 222 + Ley 1258); do **not** re-collect those.

## Where to find the documents

**K1 — Resolución Externa 1/2018 (BanRep):**

- **BanRep landing:** `https://www.banrep.gov.co/es/normatividad/resolucion-externa-1-2018`
- **BanRep compendium (consolidated text + amendments):** `https://www.banrep.gov.co/es/normatividad/compendios/resolucion-externa-1-2018`
- **Direct PDF compendium:** `https://www.banrep.gov.co/sites/default/files/reglamentacion/compendio-res-ext-1-de-2018.pdf`
- **DIAN-hosted version (sometimes more stable):** `https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_banrepublica_jd-0001_2018.htm`

**K2 — DCIN-83:**

- **BanRep normatividad index:** `https://www.banrep.gov.co/es/normatividad` — search for "DCIN 83" or "Manual Cambiario."
- The DCIN-83 is a "manual" (not a law), structured into capítulos and numerales. The version that lives at BanRep is the current one — there are no historical versions to track.

## What to deliver per document

The schema is slightly different per family:

**For K1 (Resolución Externa 1/2018):**

1. Full text per article (the resolución has numbered articles, ARTÍCULO 1 through ~ARTÍCULO 50ish).
2. Article number — just the integer.
3. URL — exact source page.
4. Issued: 2018-MM-DD (verify against the resolución header).
5. Use the **compendium** (consolidated current text), not the original 2018 publication. The compendium URL above gives you the latest consolidated version with all amendments inline.

**For K2 (DCIN-83):**

1. Full text per numeral.
2. Identifier as printed: "Capítulo 5, Numeral 3" — give us **both** the chapter number and the numeral number (capture both separately).
3. URL — exact source page.
4. Issue date: leave blank or use "current as of YYYY-MM-DD" since DCIN-83 is a living manual.

## How to package

**Option B recommended** — one markdown file with two top-level sections:

Filename: `brief_15_cambiario_banrep.md`

Structure:

```
# K1 — Resolución Externa 1 de 2018 (BanRep)
URL: https://www.banrep.gov.co/es/normatividad/compendios/resolucion-externa-1-2018
Issued: 2018-05-25 (verify the actual issue date in the resolución header)

## Artículo 1
[full text]

## Artículo 5
[full text]

---

# K2 — DCIN-83 (Manual Cambiario, BanRep)
URL: https://www.banrep.gov.co/es/normatividad/...
Current as of: 2026-04-28

## Capítulo 1, Numeral 1
[full text]

## Capítulo 1, Numeral 2
[full text]

## Capítulo 5, Numeral 3
[full text]
```

## Special things to watch for

- **K1 has been amended many times.** Use the **compendium** (consolidated current text), not the original 2018 publication. The compendium URL has the latest consolidated version with all modifications inline. If you find inline notes like "[Modificado por Resolución Externa N de YYYY]," keep them in the body.
- **K2 (DCIN-83) is a manual, not a law.** Its sections are "capítulos" and "numerales," not "artículos." Capture **both** identifiers when you note a numeral. A single article-style entry like "Numeral 5.3" is **not** enough — we need "Capítulo 5, Numeral 3" with the chapter and the numeral as separate values.
- **DCIN-83 numerals can have sub-numerals.** A numeral 5.3 might have sub-items 5.3.1, 5.3.2. Treat each as its own entry **only if** the BanRep manual numbers them as separate numerales. If they're part of the parent numeral's body, keep them inside.
- **K1 article numbers don't have letter suffixes** in the original (no "Art. 5-A" style). DCIN-83 may have them — preserve whatever the source uses.
- **PDFs.** K1's compendium is often only available as PDF. If so, save the PDF and use the PDF URL itself as the source URL. Copy the text into the markdown file as best you can.
- **BanRep site stability.** BanRep occasionally restructures its URLs. If a link 404s, try the search index at `https://www.banrep.gov.co/es/normatividad`.

## Verified examples to anchor against

- **K1 — Resolución Externa 1/2018:** the resolución number is "1" and the year is "2018." The Junta Directiva del Banco de la República issued it. The DIAN-mirror URL (`resolucion_banrepublica_jd-0001_2018.htm`) is verified. Article numbers run 1 through ~50.
- **K2 — DCIN-83:** "DCIN-83" is the canonical manual identifier (no year — the manual is updated by amendment). Capítulos and numerales are the unit; specific capítulo/numeral pairs you find on the source.

Do **not** invent specific article or numeral numbers. Read them off the source.

## Notes

- **This brief is fixture-only acceptable.** BanRep does not have a live scraper in our pipeline (Gap #5 in the master plan). Hand-curating these ~55 documents into the corpus is the path forward; periodic re-fetch happens manually if BanRep amends.
- **K1 + K2 are semantically related** (same regulator, same domain) but **structurally different** (one has articles, one has capítulo/numeral pairs). Don't conflate them — they have different identifiers in the database.
- Target is ~55 documents (~25 + ~30). If you find materially fewer, flag the gap.

## When you're done

1. Hand off `brief_15_cambiario_banrep.md` to the coordinator.
2. Update this file: `Status: ✅ delivered` + delivery note.
