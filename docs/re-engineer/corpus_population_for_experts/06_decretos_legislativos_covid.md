# Brief 06 — Decretos legislativos COVID

**Owner:** unassigned
**Status:** 🟡 not started
**Sprint:** 3 (priority #12 — last)
**Estimated effort:** half a day

---

## What you are looking for

The articles of **six specific decretos legislativos** issued during the 2020 COVID emergency under "estado de emergencia económica, social y ecológica."

We need approximately **30 articles total**, across these six decretos:

| Decreto | Topic |
|---|---|
| Decreto 417 de 2020 | Declaración del estado de emergencia |
| Decreto 444 de 2020 | Fondo de Mitigación de Emergencias (FOME) |
| Decreto 535 de 2020 | Devolución del IVA en aerolíneas |
| Decreto 568 de 2020 | Impuesto solidario a empleados públicos (suspended later by CC) |
| Decreto 573 de 2020 | Subsidios PAEF (employment program) |
| Decreto 772 de 2020 | Régimen de insolvencia empresarial |

For each decreto, deliver **all of its articles** (typically ~5 articles per decreto).

## Where to find the documents

DIAN normograma. The URL pattern is **slightly different** from regular decretos — it includes the word "legislativo":

- **URL pattern:** `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_legislativo_<NUM>_<YEAR>.htm`
- For example: `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_legislativo_417_2020.htm`

If a DIAN URL doesn't work, fallback to the Senate site: `https://www.secretariasenado.gov.co/senado/basedoc/decreto_legislativo_<NUM>_<YEAR>.html`

## What to deliver per article

For each article of each decreto:

1. **Full text** copied exactly, including the article heading (e.g., "Artículo 1. Objeto.").
2. **Article number** as printed (just the number, e.g., "1", "5", "12").
3. **URL** — the exact `decreto_legislativo_<NUM>_<YEAR>.htm` page where the article was found.
4. **Issue date** — these decretos all have specific 2020 issue dates printed at the top of the document. Capture that date (in YYYY-MM-DD form).
5. **Which parent decreto** the article belongs to — e.g., "Decreto 417 de 2020". This lets us group correctly.

## How to package

**Option B recommended** — one markdown file with sections per decreto:

Filename: `brief_06_decretos_legislativos_covid.md`

Structure:

```
# Decreto 417 de 2020 (declaratoria de emergencia)
URL: https://normograma.dian.gov.co/.../decreto_legislativo_417_2020.htm
Issued: 2020-03-17

## Artículo 1
[full text]

## Artículo 2
[full text]

---

# Decreto 444 de 2020 (FOME)
URL: ...
Issued: 2020-03-21

## Artículo 1
[full text]

...
```

## Special things to watch for

- **Court rulings on these decretos.** Several of these were challenged in the Corte Constitucional and either upheld, partially struck down, or completely struck down. The DIAN page often carries an inline note ("Declarado Inexequible por Sentencia C-XXX/2020") — **keep that note in the text**. We process the court ruling separately (in Brief 10), but the inline note matters.
- **Decreto 568/2020 in particular was struck down.** Keep the IE note inline.
- **The "legislativo" word.** When you copy article text, you may see references like "el presente Decreto Legislativo." That's the natural language; just keep it.

## Notes

- Six decretos × ~5 articles each = ~30 articles. If you find materially more than 50, you may have grabbed extra decretos — double-check against the list above.
- These decretos are short. The whole brief is well under a day's work.

## When you're done

1. Hand off `brief_06_decretos_legislativos_covid.md` to the coordinator.
2. Update this file: `Status: ✅ delivered` + delivery note.
