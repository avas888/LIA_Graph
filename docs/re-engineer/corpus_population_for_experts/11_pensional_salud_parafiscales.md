# Brief 11 — Pensional, Salud, Parafiscales

**Owner:** unassigned
**Status:** 🟡 not started
**Sprint:** 1 (priority #1 — this is the pilot brief)
**Estimated effort:** half a day to one day

---

## What you are looking for

Articles of three foundational laws for Colombia's social-protection system. Approximately **80 articles** total.

| Law | What it covers | Articles to deliver |
|---|---|---|
| **Ley 100 de 1993** | Pension system + health system + occupational risk system. Has 5 books. | All articles in Books I, II, III (pensional + general framework) **and** all articles in Book IV (health). |
| **Ley 2381 de 2024** | Pension reform — introduces the multi-pillar pension framework (currently suspended by the Corte Constitucional). | All articles. |
| **Ley 789 de 2002** | Employment-stimulus law — defines parafiscales (SENA contributions, family compensation funds, occupational hazard insurance). | All articles. |

## Where to find the documents

For all three leyes, multiple sources work — try DIAN first, fall back to others if needed:

- **DIAN normograma (preferred):**
  - Ley 100/1993: `https://normograma.dian.gov.co/dian/compilacion/docs/ley_100_1993.htm`
  - Ley 2381/2024: `https://normograma.dian.gov.co/dian/compilacion/docs/ley_2381_2024.htm`
  - Ley 789/2002: `https://normograma.dian.gov.co/dian/compilacion/docs/ley_0789_2002.htm`
- **Senate (backup):**
  - Ley 100/1993: `https://www.secretariasenado.gov.co/senado/basedoc/ley_0100_1993.html` (paginated `_pr001.html` etc.)
  - Ley 789/2002: `https://www.secretariasenado.gov.co/senado/basedoc/ley_0789_2002.html`
- **Función Pública (Ley 2381 official):** `https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=246356`
- **UGPP (Ley 789 official guidance):** `https://www.ugpp.gov.co/normas/ley-no-789-de-diciembre-27-de-2002/`

## What to deliver per article

For each article of each law:

1. **Full text** copied exactly, including the article heading.
2. **Article number** as printed (e.g., "10", "47", "5-A" if it has a sub-suffix).
3. **Parent law** — e.g., "Ley 100 de 1993," "Ley 2381 de 2024," "Ley 789 de 2002."
4. **URL** — the exact source page.
5. **Issue date:**
   - Ley 100 de 1993 — issued 1993-12-23
   - Ley 2381 de 2024 — issued 2024-07-16 (verify on the source)
   - Ley 789 de 2002 — issued 2002-12-27

## How to package

**Option B recommended** — one markdown file with sections per law:

Filename: `brief_11_pensional_salud_parafiscales.md`

Structure:

```
# Ley 100 de 1993 (Sistema General de Seguridad Social)
URL: https://normograma.dian.gov.co/.../ley_100_1993.htm
Issued: 1993-12-23

## Artículo 1
[full text]

## Artículo 10
[full text]

## Artículo 47
[full text]

## Artículo 162
[full text — this would be from Book IV / health]

---

# Ley 2381 de 2024 (Reforma Pensional)
URL: ...
Issued: 2024-07-16

## Artículo 1
[full text]

...

---

# Ley 789 de 2002 (Estímulo al Empleo + Parafiscales)
URL: ...
Issued: 2002-12-27

## Artículo 1
[full text]

...
```

## Special things to watch for

- **Ley 2381 de 2024 is suspended.** The Corte Constitucional ordered its application suspended pending procedural reiteration in Congress. Copy the text **as published** anyway — the suspension is metadata we track separately. The DIAN page will likely have an inline note about it; keep that note.
- **Ley 100 has 5 books.** We want all articles from Books I, II, III, IV (pensional + health + occupational risk integration). Book V (procedural / administrative) is also useful — include it. The book number is typically printed at the top of each section.
- **Cross-references between Ley 100 and Ley 2381 are common.** Many Ley 100 articles say "Modificado por Ley 2381 de 2024 Art. X." Keep these inline notes.
- **Parafiscales articles in Ley 789 have specific rates and carve-outs** (e.g., exemptions for new hires). Capture the full numerical detail.

## Notes

- **This is the pilot brief.** Sprint 1 starts here because (a) it's the smallest, (b) it requires no scraper work, and (c) it validates that the end-to-end delivery format works. If you hit unexpected friction, tell the coordinator immediately — we want to fix process issues here before scaling to bigger briefs.
- Target is ~80 articles. The three laws together have ~400+ articles total; you're delivering the subset most relevant to pensional, salud, and parafiscales (approximately 35 + 25 + 20 per the table above).
- If you find a Ley 100 article that's hard to classify (is this pensional, salud, or both?), include it — better to over-deliver than miss it.

## When you're done

1. Hand off `brief_11_pensional_salud_parafiscales.md` to the coordinator.
2. Update this file: `Status: ✅ delivered` + delivery note.
3. Tell the coordinator how the pilot went — what was easy, what was hard, what would you tell the next expert before they start their own brief.
