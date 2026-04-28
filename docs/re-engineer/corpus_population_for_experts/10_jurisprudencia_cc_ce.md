# Brief 10 — Jurisprudencia (sentencias CC, CE, autos)

**Owner:** unassigned
**Status:** 🟡 not started
**Sprint:** 3 (priority #11)
**Estimated effort:** 1–2 days

---

## What you are looking for

Three kinds of court documents from Colombia's highest courts:

1. **Sentencias of the Corte Constitucional (CC)** — judgments on constitutionality.
2. **Sentencias of the Consejo de Estado (CE)** — particularly the Sección Cuarta (tax/fiscal section) unification rulings.
3. **Autos of the Consejo de Estado** — provisional-suspension orders.

We need approximately **70 court documents**, broken down:

| Topic | Family | Count |
|---|---|---:|
| **I1** — CC reformas (already done) | 5 specific sentencias on tax reforms | (already done — DO NOT re-collect) |
| **I2** — CC principios | Sentencias on Art. 363 CP, Art. 338 CP, and similar tax principles | ~15 |
| **I3** — CE unificación | Sección Cuarta unification sentencias | ~30 |
| **I4** — CE autos | Provisional-suspension autos | ~20 |

The 5 already-done I1 sentencias (you can skip these): Sentencias C-481 de 2019, C-079 de 2026, C-384 de 2023, C-101 de 2025, C-540 de 2023.

## Where to find the documents

For **sentencias CC:**

- **Relatoría index:** `https://www.corteconstitucional.gov.co/relatoria/`
- **Per-sentencia URL pattern:** `https://www.corteconstitucional.gov.co/relatoria/<YEAR>/<TYPE>-<NUM>-<YY>.htm`
  - `<YEAR>` is 4 digits (e.g., "2019"); `<YY>` is the last 2 digits (e.g., "19").
  - `<TYPE>` is `C`, `T`, `SU`, or `A` (uppercase).
  - Example: `https://www.corteconstitucional.gov.co/relatoria/2019/C-481-19.htm`

For **sentencias CE (Sección Cuarta unification):**

- **CE landing:** `https://www.consejodeestado.gov.co/decisiones_u/`
- **Sección Cuarta:** `https://www.consejodeestado.gov.co/seccion-cuarta/`
- **DIAN-hosted versions:** `https://normograma.dian.gov.co/dian/compilacion/` — search by radicado, e.g. `25000-23-37-000-2014-00507-01_2022CE-SUJ-4-002.htm`

For **autos CE:**

- Same CE site / DIAN hosting. Autos are usually shorter.

## What to deliver per court document

For each sentencia / auto:

1. **Full text** — the complete decision. These can be long (10–50 pages). Copy everything: case facts, considerations ("considerandos"), and the operative parts ("resuelve"). The "resuelve" section is the most important; never truncate it.
2. **Document identifier** as the court uses it:
   - **CC sentencia:** the case identifier like "C-481/2019" or "T-205/2024" (uppercase letter, hyphen, number, slash, year).
   - **CE sentencia:** the radicado number plus the decision date. Radicado example: `25000-23-37-000-2014-00507-01`. We need the **internal radicado number** (the part the CE uses to identify the case — often a 4–5 digit number like "28920") plus the **decision date** in `YYYY-MM-DD` form.
   - **CE auto:** same as a CE sentencia — radicado number + date.
3. **URL** — the exact source page.
4. **Decision date** — the date the court made the ruling. Always required for CE documents (different sentencias from the same year are distinguished by date).
5. **Sección** (for CE only) — e.g., "Sección Cuarta," "Sección Primera." Not part of the identifier; just metadata.
6. **Topic tag** — which of I2 / I3 / I4 the document falls under.

## How to package

**Option B recommended** — one markdown file with sections per court family:

Filename: `brief_10_jurisprudencia_cc_ce.md`

Structure:

```
# I2 — CC sentencias on tax principles

## Sentencia C-XXX/YYYY
URL: https://www.corteconstitucional.gov.co/relatoria/.../C-XXX-YY.htm
Decided: YYYY-MM-DD

[full text]

---

# I3 — CE Sección Cuarta unificación

## Radicado <NNNNN>, decided YYYY-MM-DD
URL: ...
Sección: Cuarta
Radicado: 25000-23-37-000-YYYY-NNNNN-01

[full text]

---

# I4 — Autos CE

## Auto radicado <NNN>, decided YYYY-MM-DD
URL: ...

[full text]
```

## Special things to watch for

- **DO NOT re-collect the 5 I1 sentencias.** They are: C-481/2019, C-079/2026, C-384/2023, C-101/2025, C-540/2023. We have those.
- **CC type letter must be uppercase.** When you copy a sentencia identifier, write it as "C-481" not "c-481". Likewise "T-205," "SU-150," "A-30." This matters.
- **CE keying is by radicado-number + date.** Two different sentencias from Sección Cuarta in 2022 might have the same year but different radicado numbers and different decision dates. Always capture both.
- **The "resuelve" section.** Court rulings are long. The most important part is the operative section ("RESUELVE..."). Make sure that section is copied in full — that's where the legal effect is.
- **Inline references.** Court rulings reference the laws they're judging (e.g., "Ley 1943 de 2018"). Keep those references.

## On finding the right documents

For **I2** (CC principios), look for sentencias that interpret Art. 363 CP or Art. 338 CP — these are the constitutional principles that govern when tax laws can be applied retroactively, etc. The Corte Constitucional's relatoría has a search by article-of-Constitution; that's the fastest path.

For **I3** (CE unificación), Sección Cuarta issues unification sentencias periodically — they say "Sentencia de unificación" in the title. Look for those from 2018 onwards.

For **I4** (autos), focus on autos that suspend the operation of a tax decreto or resolution while the constitutionality challenge is pending. These appear when there's a major reform.

## Notes

- This brief is the most "research-y" — finding the right documents takes some judgment. If you're uncertain whether a document is in scope, copy it anyway and tag it with your uncertainty.
- Target is ~70 documents total. Less is OK if you're confident in coverage.

## When you're done

1. Hand off `brief_10_jurisprudencia_cc_ce.md` to the coordinator.
2. Update this file: `Status: ✅ delivered` + delivery note.
