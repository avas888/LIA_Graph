# Brief 01b — Código Sustantivo del Trabajo, complete consolidated text (v19 structural fix)

**Owner:** delivered 2026-05-15
**Status:** ✅ delivered — 498 articles parsed (504 headings; 4 letter-suffix composites share number with parent due to parser regex quirk), 79 derogated, range 1–492, source: Secretaría del Senado. File copied into `knowledge_base/CORE ya Arriba/LEYES/LABORAL_SEGURIDAD_SOCIAL/consolidado/Codigo_Sustantivo_Trabajo.md` on 2026-05-15.
**Priority:** Sprint 1 — blocks the v19 labor-graph fix. Pick this up only after the campaign coordinator confirms.
**Estimated effort:** 8–12 hours (one full work day).
**Replaces / extends:** [`01_cst.md`](01_cst.md). That brief asked for ~170 articles in four topical ranges. This brief asks for **the entire CST as one consolidated document**. If you have already started 01_cst, talk to the coordinator before continuing — you may want to switch to this one.

---

## 1. One-sentence purpose

- We need a single, complete, copy-faithful markdown file of the **Código Sustantivo del Trabajo** (all 492 articles, current as of today, with every amendment/derogation note preserved inline) so we can load the labor code into the system as one reference document.

## 2. What "complete" means here

- All articles of the CST, from **Artículo 1** through the last article (around **Artículo 492**).
- Includes articles that are **derogated** (`derogado`) — do NOT skip them. Mark them as you would any other; the inline note tells us they're derogated.
- Includes articles that have been **modified** (`modificado por Ley X, art. Y`) — keep the modification note inside the article body, exactly as the source prints it.
- Includes **parágrafos**, **numerales**, and **literales** as part of the parent article they belong to (do NOT split them into separate articles).
- Includes any **transitorios** (transitional articles) the source publishes.

## 3. Where to fetch the text

In this priority order. Try the next source only if the previous one is broken or has a gap.

| Priority | Source | Master URL | Notes |
|---|---|---|---|
| 1 | Senado de la República (Secretaría) | `http://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo.html` | Paginated across files `_pr001.html` through `_pr016.html`. This is the canonical mirror our system already uses for other labor laws. |
| 2 | SUIN-Juriscol | `https://www.suin-juriscol.gov.co/` | Search for "Código Sustantivo del Trabajo". If Senate has a broken page, fill the gap from here. **Always record which source you used** for the gap (see §6). |
| 3 | MinTrabajo (PDF fallback) | `https://www.mintrabajo.gov.co/` | Last resort. Only if 1 and 2 both fail for a given article. The PDF on MinTrabajo is the official consolidated edition; it's fine, but harder to copy from. |

### Senado segment map (already verified to work for the existing 01_cst brief)

- `_pr001.html`, `_pr002.html`, `_pr003.html`, `_pr004.html` → Arts. 1 through ~250
- `_pr005.html`, `_pr006.html`, `_pr007.html` → Arts. ~250 through ~410
- `_pr008.html` through `_pr016.html` → Arts. 416 through 492
- Full URL pattern: `http://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo_pr<NN>.html` where `<NN>` is two digits (01, 02, …, 16).

If you find a Senate segment doesn't load, try `_pr<NN+1>.html` or `_pr<NN-1>.html` first before falling through to SUIN — sometimes Senate re-numbers.

## 4. The single file to deliver

- **One** markdown file. Not a folder of separate files. The entire CST in one document.
- Suggested filename: `brief_01b_cst_consolidado_v19.md`.
- Encoding: UTF-8 with Spanish accents preserved (`í`, `ó`, `ñ`, `á`, etc.).

## 5. Exact shape of the file

### 5.1 Top of the file — metadata block

The very first lines of the file must look like this (in this order, one per line, in Spanish or English — whichever you prefer):

- Title line — example: `# Código Sustantivo del Trabajo — texto consolidado`
- A line saying the document is the consolidated CST
- A line saying the date you finished compiling it (today's date when you hand off — format `YYYY-MM-DD`)
- A line with the source: `Fuente: Secretaría del Senado` (or whichever source you actually used most)
- A line with the count: `Total de artículos: <NNN>` (the actual count you compiled)
- A line with the range: `Rango: artículo <first> al artículo <last>`
- A line with the derogated count: `Artículos derogados: <NNN>`
- A blank line after the metadata block.

### 5.2 Each article — exactly this heading shape

- **Heading line — must be exactly three hash marks, a space, the word `ARTÍCULO` in capital letters, a space, the article number, a period, a space, and the article title in capital letters.**
- Example of the heading line (verbatim): `### ARTÍCULO 22. DEFINICIÓN DE CONTRATO DE TRABAJO.`
- For composite-numbered articles preserve the exact format the source uses, including hyphens or letter suffixes. Examples: `### ARTÍCULO 127-1. SALARIO INTEGRAL.` or `### ARTÍCULO 22-A. EXCLUSIONES.`
- **No other heading shape will do.** Do NOT use `## Artículo 22` (two hashes, lowercase). Do NOT use `# ARTÍCULO 22`. Do NOT use `### Art. 22`. The system reads only this exact shape.

### 5.3 Immediately after each heading — the URL line

- The very next line after the heading must start with `URL:` and then the exact source page where you copied that article from.
- Example: `URL: http://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo_pr001.html`
- If you used a different source for that specific article (because Senate was broken), put that source's URL here — NOT the Senate URL.
- One URL per article. Mandatory. **A delivery with a missing URL on any article will be rejected and sent back.**

### 5.4 Then a blank line, then the article body

- The full text of the article as published. Copy exactly. Do not paraphrase. Do not summarize. Do not "clean up" wording.
- Keep paragraph breaks.
- Keep numbered sub-points (numerales `1.`, `2.`, …), lettered sub-points (literales `a)`, `b)`, …), and parágrafos exactly as they appear.
- Keep **inline amendment notes** in the body, verbatim. Examples of notes to preserve as-is:
  - `[Modificado por el artículo 5 de la Ley 50 de 1990]`
  - `[Derogado por el artículo 28 de la Ley 789 de 2002]`
  - `[Modificado por el artículo 28 de la Ley 789 de 2002. El nuevo texto es el siguiente:]`
  - `(Nota: Artículo declarado EXEQUIBLE por la Corte Constitucional mediante Sentencia C-481 de 1998)`
- If the source places these notes BEFORE the article body, keep them BEFORE the body. If AFTER, keep them AFTER. Mirror the source.

### 5.5 Separator between articles

- After each article body, leave one blank line, then three hyphens (`---`) on their own line, then one blank line, then the next article's heading.
- The very first article has no separator before it; the very last article has no separator after it.

### 5.6 A worked example of the shape — Articles 22, 23 (text shown is illustrative, not the real article 22)

```
### ARTÍCULO 22. DEFINICIÓN DE CONTRATO DE TRABAJO.
URL: http://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo_pr001.html

1. Contrato de trabajo es aquel por el cual una persona natural se obliga a prestar un servicio personal a otra persona, natural o jurídica, bajo la continuada dependencia o subordinación de la segunda y mediante remuneración.

2. Quien presta el servicio se denomina trabajador, quien lo recibe y remunera, empleador, y la remuneración, cualquiera que sea su forma, salario.

---

### ARTÍCULO 23. ELEMENTOS ESENCIALES.
URL: http://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo_pr001.html

[Modificado por el artículo 1 de la Ley 50 de 1990. El nuevo texto es el siguiente:]

1. Para que haya contrato de trabajo se requiere que concurran estos tres elementos esenciales:

a) La actividad personal del trabajador, es decir, realizada por sí mismo;
b) La continuada subordinación o dependencia del trabajador respecto del empleador, que faculta a éste para exigirle el cumplimiento de órdenes, en cualquier momento, en cuanto al modo, tiempo o cantidad de trabajo, e imponerle reglamentos, la cual debe mantenerse por todo el tiempo de duración del contrato. Todo ello sin que afecte el honor, la dignidad y los derechos mínimos del trabajador en concordancia con los tratados o convenios internacionales que sobre derechos humanos relativos a la materia obliguen al país; y
c) Un salario como retribución del servicio.

2. Una vez reunidos los tres elementos de que trata este artículo, se entiende que existe contrato de trabajo y no deja de serlo por razón del nombre que se le dé ni de otras condiciones o modalidades que se le agreguen.

---
```

(The article 22 text above is hypothetical for illustration — please copy whatever the Senate page actually publishes, do not reuse the example text.)

## 6. End of the file — a short gap report

After the very last article, leave three blank lines, then a `## Notas de cobertura` section with bullet points for:

- Any article number you searched for but could not find in any of the three sources (Senate / SUIN / MinTrabajo). One bullet per missing article: `Artículo <N>: no encontrado en Senado/SUIN/MinTrabajo el <YYYY-MM-DD>`.
- Any article where you had to fall through from Senate to SUIN or MinTrabajo. One bullet per substitution: `Artículo <N>: tomado de SUIN porque Senado _pr<NN>.html no cargó`.
- Any article that the source publishes with no body text (only a derogation note). One bullet per case: `Artículo <N>: sin cuerpo en la fuente — solo nota de derogación, conservada`.
- If everything came from Senate without substitutions and no gaps, write: `Sin gaps. Toda la cobertura proviene de Secretaría del Senado.`

This section is **mandatory** even if it's just the "Sin gaps" line.

## 7. Articles we especially care about (double-check these before handing off)

The full CST is the deliverable, but if any of these are missing or look truncated, that's a defect — please re-check those specific articles before delivery.

| Artículo | Tema | Por qué nos importa |
|---|---|---|
| 22, 23, 24 | Definición de contrato, elementos esenciales, presunción | Punto de partida del contrato individual |
| 45, 46, 47 | Duración del contrato (indefinido, fijo, obra/labor) | Plazos contractuales |
| 61, 62 | Terminación del contrato — causales y justas causas | Una de las consultas más frecuentes del contador |
| 64 | Indemnización por terminación sin justa causa | El artículo más consultado del CST |
| 65 | Indemnización por falta de pago | Sanción moratoria — alto impacto económico |
| 127, 128, 129, 130, 132 | Definición de salario, pagos que no constituyen salario | Base de toda nómina |
| 145, 146, 147, 148 | Salario mínimo legal | Año tras año cambia |
| 158, 161, 162 | Jornada ordinaria y máxima legal | Reformada por la Ley 2101/2021 — el texto vigente debe reflejarlo |
| 168, 169, 173, 174, 175 | Descansos obligatorios, dominical, festivos | Recargos, base de la nómina |
| 179, 180 | Trabajo nocturno, dominical, festivo | Reformados por la Ley 2466/2025 — el texto debe reflejar el estado actual |
| 186, 187, 188, 189, 190, 191, 192 | Vacaciones | Liquidación anual estándar |
| 230, 231, 232, 233, 234, 235, 236 | Calzado y vestido de labor, descanso compensatorio | Prestaciones menores |
| 249, 250, 251, 252, 253 | Cesantías | Núcleo de prestaciones sociales |
| 306, 307 | Prima de servicios | Prestación semestral universal |
| 339, 340 | Auxilio de cesantía (régimen anterior) | Para casos pre-Ley 50/1990 |
| 416 al 492 | Conflictos colectivos, sindicatos, fuero, huelga | Bloque sindical completo |

## 8. Things to watch for as you copy

- **Article 64** in particular has been modified multiple times. The current consolidated text should include the inline note `[Modificado por el artículo 28 de la Ley 789 de 2002]`. If your copy of art. 64 has no such note, you probably have the pre-2002 version — re-fetch.
- **Articles 158-167 (jornada)** were modified by Ley 2101/2021 (gradual reduction of the work week). The current text should reflect 2021 onward.
- **Articles 179-180 (recargo nocturno/dominical)** were modified by Ley 2466/2025. The current text should reflect that 2025 law.
- **Article 127** has had Ley 50/1990 and Ley 1393/2010 modifications. The note should mention at least one of them.
- **Articles 230-258** include several derogations across the years. Keep the derogation notes; do NOT remove derogated articles from the file.
- If you see an article on the Senate page that is **completely empty** (just a number and a derogation note like `Artículo 234. Derogado por la Ley 100 de 1993`), copy it that way — derogation note as the body. Do not skip it.

## 9. Things we do NOT need (please do not include them)

- No interpretation, commentary, doctrine, or "what this means in practice."
- No cross-references to other laws beyond what the Senate page itself prints inline. (If the source mentions "ver Ley 100 de 1993" — keep it. If you want to add your own cross-references — don't.)
- No constitutional court rulings or doctrine, except for the short inline `(Nota: Sentencia C-XXX de YYYY...)` notes that the Senate page already prints inside the article. (Full sentencias go in a different brief.)
- No internal labels, tags, categories, JSON, code, or anything technical.
- No table of contents at the top — the metadata block in §5.1 is enough.
- No summary at the end — the gap report in §6 is the only end-of-file section.

## 10. Quality checklist before handing off

Tick every box. If any box is unticked, fix it before delivery.

- [ ] File is a single markdown file, UTF-8.
- [ ] First lines are the metadata block from §5.1 (title, date, source, count, range, derogated count).
- [ ] Every article uses the exact heading shape from §5.2: `### ARTÍCULO <N>. <TÍTULO EN MAYÚSCULAS>.`
- [ ] Every article has a `URL:` line immediately after the heading, pointing to the exact source page where that article came from.
- [ ] No article is missing its URL.
- [ ] Inline modification / derogation / sentencia notes are preserved verbatim inside each article body.
- [ ] Parágrafos / numerales / literales stay inside the parent article (not split out).
- [ ] Article numbers are in ascending numerical order from first to last.
- [ ] Composite numbers (e.g., `127-1`, `22-A`) preserve the exact format the source uses.
- [ ] Derogated articles are included with their derogation note as body if no other body exists.
- [ ] A `## Notas de cobertura` section closes the file, even if it just says `Sin gaps.`
- [ ] At least the 16 priority blocks from §7 are present and look complete.
- [ ] You spot-checked articles 64, 127, 158, 179, and 249 — each shows current consolidated text with the right modification notes.
- [ ] Total article count in metadata matches the actual number of `### ARTÍCULO` headings in the file (you can verify this by searching the file for `### ARTÍCULO`).

## 11. When you're done

1. Hand off `brief_01b_cst_consolidado_v19.md` to the campaign coordinator.
2. At the top of this brief file, change `Status: 🟡 not started` to `Status: ✅ delivered`, add a line like `2026-MM-DD — delivered <NNN> artículos, <NNN> derogated, source: <Senado / mixed>`.
3. Tell the coordinator: "Brief 01b done — ready for v19 ingestion."
4. The developers will load it into the labor knowledge base. If we find a defect, we will come back to you with the specific article number and what looks wrong.

## 12. If you hit trouble

- Senate page won't load → try SUIN-Juriscol for that specific article range, note the substitution in §6, continue.
- Article you expected to exist is genuinely missing in all three sources → list it in §6 as `no encontrado`, continue.
- Source publishes contradictory versions of the same article → use the most recent consolidated text, and add a `(Nota del compilador: este artículo aparece en dos versiones en la fuente; se conservó la más reciente fechada el YYYY-MM-DD.)` line at the END of that article's body.
- Anything else looks weird or contradicts this brief → stop and ask the coordinator. Don't guess.

---

*Brief drafted 2026-05-15. Owner of v19 fix plan: see `docs/re-engineer/fix/fix_v19_may.md`. If this brief contradicts the campaign-wide [`README.md`](README.md), this brief wins for the CST consolidado specifically — and please tell the coordinator so the README can be updated.*
