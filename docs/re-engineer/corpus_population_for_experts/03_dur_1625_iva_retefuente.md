# Brief 03 — DUR 1625/2016, IVA + retefuente

**Owner:** unassigned
**Status:** 🟡 not started
**Sprint:** 2 (priority #6 — comes right after Brief 02)
**Estimated effort:** 1 day

---

## What you are looking for

Articles of DUR 1625/2016 that deal with **IVA (impuesto sobre las ventas)** and **retención en la fuente reglamentada** — the two next big sections of the same DUR you already saw in Brief 02.

We need approximately **280 articles**.

## Where to find the documents

Same page as Brief 02:

- **Source:** `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm`

For this brief, you want articles whose dotted-decimal number starts with **"1.3."** (the IVA block) or **"1.2.4."** (the retefuente reglamentado block). Examples of what to keep:

- "Artículo 1.3.1.1.1"
- "Artículo 1.3.4.5.2"
- "Artículo 1.2.4.1.10"

Skip everything else.

## What to deliver per article

Same as Brief 02:

1. **Full text** copied exactly, including title heading.
2. **Article number** as printed (preserve the dotted decimal exactly, including any hyphen-digit suffix).
3. **URL** — the **exact source page** (hard requirement, no exceptions): the single-page DUR URL `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm`. Same URL across every article in this brief is correct and required. **Never** substitute a homepage or index.
4. **Issue date** — DUR 1625 was issued 2016-08-02 baseline; respect amendment notes in the text.

## How to package

**Option B recommended** — one markdown file:

Filename: `brief_03_dur_1625_iva_retefuente.md`

Same header structure as Brief 02.

## Special things to watch for

- **Coordinate with Brief 02 owner.** Briefs 02, 03, 04 all read the same DUR page. If you and the Brief 02 owner are working separately, you each scan the full page for your assigned blocks. If you and Brief 02 owner are the same person, you can extract all three briefs in one pass and split the output.
- **Same amendment-note rule.** Keep `[Modificado por...]` and `[Derogado por...]` markers inside the text.
- **Compound articles.** Same as Brief 02 — preserve hyphen-digit suffixes.
- **Don't invent ranges.** If you don't find an article with a specific number, that's fine — skip it. Don't fabricate a number to hit a target count.

## Notes

- **Why two prefixes (1.3 and 1.2.4)?** The DUR's organization is funny: IVA articles are under `1.3.*`, but the section that regulates *retención en la fuente para IVA* lives under `1.2.4.*`. Both are in scope for this brief.
- **Target is ~280 articles.** If you find materially fewer (say, under 200) or materially more (over 400), tell the coordinator before delivering — there might be a misalignment in what we're targeting.

## When you're done

1. Hand off `brief_03_dur_1625_iva_retefuente.md` to the coordinator.
2. Update this file: `Status: ✅ delivered`, add a note like `2026-MM-DD — delivered ~<actual count> articles via brief_03_dur_1625_iva_retefuente.md`.
