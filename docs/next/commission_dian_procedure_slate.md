# Commission — DIAN-Procedure Practical-Guide Slate

**Commissioning entity:** Lia Graph product team
**Target specialist profile:** Abogado/contador con 7+ años de experiencia en procedimiento tributario DIAN (requerimientos ordinarios, especiales, pliego de cargos, liquidaciones oficiales, devoluciones, firmeza). Experiencia demostrable defendiendo expedientes DIAN para PYMEs.
**Version:** 1.0 — 2026-04-22
**Language of deliverables:** Spanish (Colombian professional register)
**Compensation:** Negotiated separately
**Deliverable deadline:** PRO-N01 + PRO-E01 in 10 business days; PRO-L02 / L03 / L04 staggered over the following 10 business days.

---

## 1. Executive summary

Lia is a graph-native RAG (retrieval-augmented generation) product for Colombian SMB accountants. It answers their questions in natural language by retrieving relevant articles from a curated legal corpus and composing an accountant-voice answer with inline citations. The product is in active use by practicing accountants; its answers are one of several inputs they rely on when advising clients.

An internal measurement pass (the "citation-faithfulness harness," 2026-04-22) confirmed that the system does not fabricate citations — when it cites an article, that article exists in the corpus and was retrieved for the query. However, the same measurement revealed that for several high-traffic accounting procedures, **the underlying articles are present but no practical/doctrinal digest wraps them** — so the system's answers in those areas are thin (a one-line article reference), abstain entirely, or drift to adjacent topics.

**DIAN procedure is the canonical case and our tier-1 commission.** An accountant asking "my client got a requerimiento ordinario — what are the terms, what can they demand as proof, what's the procedural route if I disagree?" should receive a substantive operational answer. Today they get either generic article references or a "coverage pending" response. This commission closes that gap.

You are being asked to author **five documents** that will be ingested into Lia's corpus and will directly shape the answers practicing accountants receive when they ask about DIAN audit procedure.

---

## 2. Why this matters (product + user context)

**Who reads your output.** Not the end user directly. Your documents are consumed by Lia's retrieval pipeline, which extracts passages in response to accountant queries and composes an answer that weaves together (a) passages from your document, (b) underlying statutory articles, and (c) Lia's own template scaffolding. The end accountant sees an answer that looks composed, with inline citations back to your document and to the tax code.

**What that means for your writing:**

- **Every factual claim must be traceable to primary source.** Articles of the Estatuto Tributario, DIAN resolutions, Conceptos DIAN, Consejo de Estado sentencias, Corte Constitucional sentencias, or published decrees. We will mechanically verify that every legal reference in your document exists in our corpus before the document is accepted. Invented or paraphrased-from-memory citations are the single most harmful failure mode — we will reject the document in that case, no exceptions.
- **Prose should be modular.** Short paragraphs (3–5 lines), clear section headings, numbered step-by-step lists where procedural. Long flowing narrative paragraphs retrieve poorly — the system returns a 500-char chunk to the user and a narrative paragraph becomes incoherent mid-sentence.
- **Voice is senior peer-to-peer Colombian accountant.** Not academic, not hedge-heavy, not deferential to DIAN. Write the way you'd explain the procedure to a colleague at the firm next door, not the way a first-year associate drafts a memo.
- **Specificity wins.** "Presente la respuesta dentro del término legal" is useless. "Presente la respuesta al requerimiento especial dentro de los 3 meses siguientes a la notificación (Art. 707 E.T.), prorrogables por 3 meses más a solicitud del contribuyente (Art. 707 E.T., parágrafo)" is what we need.

**What Lia already has.** The full Estatuto Tributario is in the corpus as individual articles. Ley 1819/2016, Ley 2277/2022, and the decrees reglamentarios that bear on procedural matters are in the corpus. Conceptos DIAN from 2018 onward are indexed. Your job is NOT to restate statutory text; it is to produce the operational interpretation and step-by-step guidance that wraps around the statute.

---

## 3. The five deliverables

The slate follows Lia's three-family corpus model: NORMATIVA (marco legal overview), INTERPRETACIÓN (doctrinal digest), PRÁCTICA (step-by-step operational guide). One NORMATIVA, one INTERPRETACIÓN, three PRÁCTICAs.

### PRO-N01 — Marco Normativo del Procedimiento Tributario DIAN

**Family:** `normativa`
**Length target:** 3,000–5,000 words
**Purpose:** The single-source overview of the procedural framework. The document a senior accountant reaches for when they need to orient themselves in the procedural landscape before diving into a specific case.

**Coverage:**

1. The procedural framework at a glance — the hierarchy from fiscalización (Art. 684 E.T.) through determinación (Arts. 701–719) through cobro (Arts. 823–843-4).
2. Types of DIAN actions the accountant will encounter and their legal basis:
   - Requerimiento ordinario (Art. 684)
   - Emplazamiento para corregir (Arts. 685, 589)
   - Pliego de cargos (Art. 638)
   - Requerimiento especial (Art. 703)
   - Liquidación oficial de revisión (Art. 710)
   - Liquidación oficial de aforo (Art. 715)
   - Liquidación de corrección aritmética (Art. 697)
3. Key terms and their legal definitions: notificación, firmeza, suspensión, interrupción, cómputo de términos.
4. The timeline map — what happens, in what order, with what term, referencing what article. A table is the right format here.
5. Cross-references to adjacent procedural regimes: procedimiento sancionatorio (Arts. 637–651), régimen probatorio (Arts. 742–752), recursos (Arts. 720–740).

**Explicit exclusions:**
- Do NOT restate article text verbatim. Summarize the article's operative rule in your own words.
- Do NOT write a practitioner's tactical advice section — that goes in PRO-E01.

### PRO-E01 — Interpretación Doctrinal: Defensa del Contribuyente en Procedimientos DIAN

**Family:** `interpretacion`
**Length target:** 4,000–6,000 words
**Purpose:** The doctrinal digest — what the courts and doctrinal authorities have said about the procedural rules, where the DIAN's position and accountant practice diverge, and what the current state of the argument is.

**Coverage:**

1. **Jurisprudencia vigente** — a curated digest of Consejo de Estado sentencias from the last five years that practicing accountants need to know. Include at minimum: sentencias on (a) firmeza y sus interrupciones, (b) carga de la prueba en requerimiento especial, (c) debido proceso en notificación electrónica, (d) reapertura de investigación, (e) silencio administrativo positivo.
2. **Conceptos DIAN relevantes** — which Conceptos DIAN are load-bearing for procedural questions, which were revoked, which are currently in force. Cite Concepto numbers and years (e.g., Concepto DIAN 100208192-202 del 2024).
3. **Posiciones doctrinales en conflicto.** When DIAN's administrative position differs from the Consejo de Estado's judicial position or from widely-accepted academic doctrine, name the conflict. Cite both positions. State which one the practicing accountant should operate under (with reasoning).
4. **Lecturas prácticas no-obvias.** The five most common interpretive mistakes accountants make in DIAN procedural defense, with the correct reading and the authority that supports it.
5. **Literatura académica y profesional** — reference the standing Colombian treatises on procedimiento tributario (e.g., Mauricio Piñeros, Juan Rafael Bravo Arteaga, José Orlando Corredor Alejo). Full bibliographic citation per reference.

**Format note:** Use substantive subsections, numbered rulings, explicit cross-references to the ET articles and sentencias. Avoid footnote-heavy academic prose.

### PRO-L02 — Guía Práctica: Respuesta al Requerimiento Ordinario

**Family:** `practica`
**Length target:** 2,500–4,000 words
**Purpose:** The step-by-step operational guide for handling a DIAN requerimiento ordinario from notification to reply.

**Coverage:**

1. Qué es y qué no es — differences from requerimiento especial and emplazamiento.
2. Verificación de notificación — canales, tiempos, recálculo si la notificación fue defectuosa.
3. Cómputo del término de respuesta (15 días hábiles desde notificación, Art. 261 Ley 1819/2016 modificó Art. 684-1).
4. Inventario de lo solicitado — cómo leer el requerimiento, qué separar entre información factual, soportes documentales, y justificaciones jurídicas.
5. Preparación de la respuesta — estructura sugerida: encabezado, referencia al requerimiento, respuesta punto por punto, soportes anexos, firma del representante legal y revisor fiscal cuando aplique.
6. Canales de radicación — DIAN Muisca, correo certificado, presencial; ventajas y riesgos de cada uno.
7. Qué hacer si no se puede cumplir el término — solicitud de prórroga, causales aceptables, cómo documentarla.
8. Cierre — confirmación de radicación, seguimiento, próximos pasos probables de DIAN.
9. Checklist final — una lista numerada de 10–15 puntos que el contador debe verificar antes de firmar.

### PRO-L03 — Guía Práctica: Defensa en Requerimiento Especial

**Family:** `practica`
**Length target:** 3,000–5,000 words
**Purpose:** The step-by-step for the more serious requerimiento especial — the procedural step immediately preceding liquidación oficial de revisión.

**Coverage:**

1. Qué cambia respecto del requerimiento ordinario: efectos jurídicos, carga probatoria, plazos.
2. Lectura crítica del requerimiento especial — identificación de los cargos, la liquidación propuesta, y la base jurídica que esgrime DIAN.
3. Evaluación de la posición del contribuyente — when to settle (acogerse a la corrección), when to defend, when to partially settle and partially defend.
4. Preparación de la defensa — acopio probatorio, argumento jurídico, cómo estructurar el escrito de respuesta.
5. Cómputo del término (3 meses, prorrogables 3 meses más, Art. 707 E.T.).
6. Radicación y seguimiento.
7. Qué esperar después de la respuesta — escenarios: liquidación oficial de revisión, archivo del expediente, ampliación del requerimiento.
8. Estrategia subsidiaria — preparación desde ya para el recurso de reconsideración si DIAN profiere liquidación.
9. Checklist final.

### PRO-L04 — Guía Práctica: Recurso de Reconsideración

**Family:** `practica`
**Length target:** 3,000–4,500 words
**Purpose:** The step-by-step for the administrative appeal against a DIAN liquidación oficial.

**Coverage:**

1. Cuándo procede (Art. 720 E.T.) y cuándo no.
2. Término de interposición (2 meses desde la notificación de la liquidación).
3. Requisitos formales — competencia del funcionario que resuelve, legitimación, forma y contenido del escrito.
4. Estructura del escrito — hechos, fundamentos de derecho, petición.
5. Acopio probatorio adicional — qué pruebas son admisibles en sede de reconsideración vs. cuáles debieron haberse aportado antes.
6. Cómputo del término para resolver (Art. 732 E.T., 1 año) y efectos del silencio administrativo positivo.
7. Vías subsidiarias — la acción de nulidad y restablecimiento del derecho (Art. 138 CPACA) y cuándo optar por ella directamente.
8. Checklist final.

---

## 4. Mandatory document template

Every document, regardless of family, must be delivered as a single Markdown file with the following exact structure. The ingestion pipeline **rejects documents that do not match this structure** — our section coercer validates section headers byte-for-byte.

```markdown
# <Título del documento — usar el título exacto del brief arriba>

## Contexto

<2–4 paragraphs framing the document's scope, the user problem it solves,
and the legal framework it operates in. This is what the retrieval system
shows first when a passage from this document matches a query.>

## Marco normativo

<Hierarchical list of the statutory framework. Each entry names the article
or instrument and states its operative rule in 1–2 sentences. Entries are
ordered from general to specific.>

- **Art. XXX E.T.** — <operative rule in one sentence>.
- **Ley NNNN de YYYY, Art. Z** — <operative rule>.
- **Decreto NNNN de YYYY, Art. Z** — <operative rule>.
- **Resolución DIAN 00XXXX de YYYY** — <operative rule>.

## Procedimiento paso a paso

<Numbered list of operational steps. Each step is 2–6 lines. Include
decision points where the accountant must choose between paths. Every
step that has a legal basis cites the article inline like "(Art. 707 E.T.)".>

1. **<Step name>** — <detail>. Citation at the end of the bullet.
2. **<Step name>** — <detail>.
...

## Formularios y plazos

<Table or structured list of the specific DIAN forms and deadlines that
apply. This section is scanned by a forms-extraction regex, so use the
exact formulario number: "Formulario 110", "Formulario 260", "Formulario
2516", etc.>

| Situación | Formulario | Plazo | Base legal |
|---|---|---|---|
| ... | Formulario XXX | N días hábiles | Art. XXX E.T. |

## Sanciones

<What the accountant and the client face if the procedure is mishandled.
Cite the specific sanction article and the calculation base.>

- **Extemporaneidad** — Art. 641 E.T. — base UVT YYYY: $XXX.
- **Inexactitud** — Art. 647 E.T. — base 100% del mayor valor.
- ...

## Riesgos comunes

<The 5–10 most common mistakes the accountant makes in this procedure, with
the correct reading and the authority that supports it. One paragraph per
risk. This section is what separates a practical guide from a statutory
restatement.>

- **Error frecuente 1:** <description>. **Riesgo:** <consequence>. **Cómo
  evitarlo:** <actionable guidance>. **Base:** <citation>.
- ...

## Interpretación doctrinal

<For N01/L02/L03/L04 documents: a short section (4–8 paragraphs) summarizing
the doctrinal position the rest of the document assumes, with citations to
the Consejo de Estado / Conceptos DIAN that support it. Can be a short
pointer to PRO-E01 for documents in this slate.>

<For E01 specifically: this is where the main doctrinal digest content
lives — ~4,000 words of substantive interpretation.>

## Referencias

<Flat bibliographic list of every legal instrument, sentencia, concepto,
and treatise cited. Format strictly:>

- **Estatuto Tributario** — Artículos X, Y, Z.
- **Ley NNNN de YYYY** — Art. Z.
- **Decreto NNNN de YYYY** — Art. Z.
- **Resolución DIAN 00XXXX de YYYY.**
- **Concepto DIAN NNNNNN de YYYY.**
- **Consejo de Estado, Sección Cuarta, Sentencia NNNNN del DD-MM-YYYY, C.P. <Nombre>.**
- **Corte Constitucional, Sentencia C-XXX/YY.**
- Piñeros, Mauricio. *Procedimiento Tributario.* Legis, 5ª ed., 2023.
- ...
```

**Section order is fixed.** You may not reorder, omit, or rename sections. If a section genuinely does not apply (rare — e.g., no specific forms for a given procedure), write `## Formularios y plazos\n\nNo aplica — este procedimiento no utiliza formularios DIAN específicos; la actuación se adelanta mediante escrito libre.` under the heading. Do not delete the heading.

---

## 5. Citation format — strict

Our system extracts citations by regex. Follow these formats exactly:

- **Articles of the Estatuto Tributario:** `Art. 771-2 E.T.` or `(Art. 771-2 E.T.)` in running prose. Never `artículo 771-2 del Estatuto Tributario` — the regex does not match that form. Hyphens (not underscores) between the base article and its numeric suffix.
- **Paragraphs of articles:** `Art. 240, parágrafo 6 E.T.` or `(Art. 240, par. 6 E.T.)`.
- **Reform laws:** `Ley 2277 de 2022, Art. 7` or `(Ley 2277 de 2022, Art. 7)`. The year is always 4 digits; "Art." is always the abbreviation.
- **Decrees:** `Decreto 1625 de 2016, Art. 1.2.1.1.1`.
- **DIAN resolutions:** `Resolución DIAN 000167 de 2021` — six-digit resolution number, pad with leading zeros to match the official numbering.
- **DIAN concepts:** `Concepto DIAN 006483 de 2024` or for longer-format concepts `Concepto DIAN 100208192-202 de 2024`.
- **Consejo de Estado sentencias:** `Consejo de Estado, Sección Cuarta, Sentencia 28920 del 15-03-2025, C.P. Myriam Stella Gutiérrez Argüello`.
- **Corte Constitucional sentencias:** `Corte Constitucional, Sentencia C-456 de 2020`.

**Every citation must correspond to an actual instrument.** Do not cite articles that don't exist, resolutions with wrong numbers, or sentencias with incorrect radicados. Pre-ingestion validation will compare every citation against our curated article graph; unmatched citations fail the document's acceptance check and require rework.

---

## 6. Quality bar — what "good" looks like

Use the following as a mental yardstick: **if a senior accountant at the firm across the street read this document, would they learn something specific that saves them a client error?** If yes, ship. If it reads like a textbook summary, rewrite.

**Good:**
- "Si el contribuyente radica la respuesta al requerimiento especial el día 91 después de la notificación, DIAN la puede rechazar por extemporaneidad (Art. 707 E.T., 3 meses). En la práctica, cuente los 3 meses en días calendario, no hábiles, y siempre radique con al menos 3 días hábiles de holgura porque el canal Muisca se cae recurrentemente en la última semana del plazo — hay Concepto DIAN 1234 de 2022 que aclara que las caídas del sistema no interrumpen el término."
- "El error más común en la respuesta al requerimiento ordinario es anexar los soportes como referencia ('ver libro auxiliar del período X') en lugar de aportarlos físicamente. El Consejo de Estado (Sent. 23456/2023) sostiene que la carga probatoria es del contribuyente y que una referencia sin aportar el documento no la descarga."

**Not good:**
- "Es importante cumplir los términos legales al responder requerimientos DIAN."
- "La jurisprudencia ha señalado que el debido proceso debe observarse."

The difference is specificity: article numbers, sentence numbers, concrete procedural advice, named failure modes.

---

## 7. Review and sign-off process

Each document goes through three gates. You are responsible for the first; Lia's review team handles the other two.

1. **Your self-review.** Before submitting, you confirm:
   - Every article/concepto/sentencia citation has been verified against primary source.
   - Every formulario number is real and applies to the procedure described.
   - Every UVT value or sanction calculation uses the current UVT for 2026.
   - The document follows the mandatory template byte-for-byte.
   - You would sign this document with your professional name.

2. **Accountant reviewer** (Lia's in-house practicing accountant). 2–3 business days after submission. Checks for factual errors, outdated rules, missing common cases. You will receive at most one round of revisions; revisions should be resolvable in under 3 hours. Major structural rewrites are rare and will trigger a separate conversation.

3. **Mechanical validation** (automated). The ingestion pipeline runs three checks:
   - Section-structure coercer: all 8 sections present with exact headings.
   - Citation validator: every cited article/resolution/concepto/sentencia matches an entry in Lia's corpus graph or is added to it as a new node.
   - Canonical blessing: the document must pass `canonical_blessing_status = canonical` in `corpus_audit_report.json`.

A document that fails any gate returns to you with a specific list of what to fix. Documents that fail the citation validator are the most common rework cause — take the citation format section seriously.

---

## 8. Compensation and timeline

| Deliverable | Target word count | Delivery deadline | Revision window |
|---|---|---|---|
| PRO-N01 (Marco Normativo) | 3,000–5,000 | Business day 10 | Days 11–13 |
| PRO-E01 (Interpretación Doctrinal) | 4,000–6,000 | Business day 10 | Days 11–13 |
| PRO-L02 (Requerimiento Ordinario) | 2,500–4,000 | Business day 15 | Days 16–18 |
| PRO-L03 (Requerimiento Especial) | 3,000–5,000 | Business day 18 | Days 19–21 |
| PRO-L04 (Recurso Reconsideración) | 3,000–4,500 | Business day 20 | Days 21–23 |

Commissioner acknowledgment of receipt within 24 hours of submission. Accountant review within 3 business days. Revision rounds limited to two per document.

Compensation is negotiated and paid per document upon acceptance (post-sign-off from all three gates). Fee reflects the specialist level the work requires and includes the revision rounds.

---

## 9. Worked example — small excerpt

So you can see what the format looks like in practice. This is a ~200-word sample from what PRO-L02's "Procedimiento paso a paso" section should resemble:

```markdown
## Procedimiento paso a paso

1. **Verificar la notificación.** Confirme por qué canal llegó el
   requerimiento (Muisca, correo certificado, notificación personal).
   La fecha de notificación electrónica efectiva es el día siguiente
   a la fecha en que el mensaje quedó disponible en el buzón del
   contribuyente, no la fecha de envío (Art. 566-1 E.T.). Anote la
   fecha exacta — todo el cómputo de términos depende de ella.

2. **Computar el término de respuesta.** 15 días hábiles desde la
   fecha de notificación (Art. 684-1 E.T., adicionado por Ley 1819
   de 2016, Art. 261). Los días hábiles excluyen sábados, domingos
   y festivos nacionales. No use días calendario — es un error común
   que ha resultado en rechazo por extemporaneidad (Consejo de
   Estado, Sección Cuarta, Sentencia 22345 del 15-04-2023).

3. **Inventariar lo solicitado.** Separe lo que DIAN pide en tres
   grupos: (a) información factual que el contribuyente puede
   responder directamente; (b) soportes documentales que requieren
   acopio; (c) justificaciones jurídicas que requieren análisis.
   El grupo (b) es el que más frecuentemente genera prórrogas y
   debe identificarse de inmediato.

...
```

Note: specific article citations inline, named jurisprudencia with radicado, concrete procedural rules with numbers not adjectives, distinctions that matter for the practitioner.

---

## 10. What to ask us if you need to

Questions about scope, format, or acceptance criteria go to the commissioning contact. Questions about Colombian tax law are yours to resolve — that's the expertise we're buying. If in the course of drafting you uncover a material ambiguity in current law (e.g., DIAN and Consejo de Estado take contradictory positions that affect the practical advice), flag it in the "Interpretación doctrinal" section with both positions cited; do not silently pick one.

If you identify an additional practical guide that should be in this slate (e.g., "Guía de notificación por conducta concluyente" as a prerequisite for L02/L03), raise it with the commissioning contact before investing time. Scope expansion is possible but must be agreed separately.

---

## 11. What happens after ingestion

Within 48 hours of final acceptance, your document is ingested into Lia's corpus. Accountants querying about DIAN procedural topics start seeing passages from your document in Lia's answers. The accountant sees the answer; the citation links back to the document's section, which the accountant can open in full from within Lia.

Your name as author is recorded in the document's metadata and surfaces in Lia's citation panel. You receive a one-page report monthly for the first three months showing (a) how often your document was cited in Lia's answers, (b) which sections were retrieved most often, (c) any accountant feedback flagged on those answers.

This last point is why the specificity bar in section 6 matters. Generic content retrieves and gets ignored; specific content retrieves and gets used.

---

## Appendix A — Existing corpus example for reference

A document already in Lia's corpus that exemplifies the tone and structure we're asking for is `knowledge_base/declaracion_renta/deduccion_factura_electronica_1pct/E01_deduccion_1pct_factura_electronica.md`. Request access to it as a reference before starting your draft. Read it for voice, section rhythm, citation density, and the specificity bar. Do not copy its content or structure verbatim — your deliverables should feel consistent with it while covering different material.

## Appendix B — Common pitfalls from prior commissions

- **Restating the ET verbatim.** The article text is already in the corpus as its own document. Your value-add is interpretation, not transcription.
- **Citing Conceptos DIAN without verifying the current status.** Many Conceptos have been revoked or substituted. Use `estatuto.co` or the DIAN Normograma to confirm the current status before citing.
- **Treating DIAN's administrative position as legally authoritative.** The Consejo de Estado's judicial position overrides DIAN's administrative interpretation when they conflict. Your document must reflect that hierarchy.
- **UVT values from prior years.** UVT for 2026 is the applicable value for sanctions calculations in 2026 — do not cite 2024 or 2025 UVT figures. (UVT 2026 = see Resolución DIAN of late 2025.)
- **Invented procedural timelines.** There is no "legal term" of 10 business days for anything in DIAN procedural law unless you can cite the article that establishes it. When in doubt, look it up.

## Appendix C — Glossary of Lia-specific terms (for your reference only)

- **Canonical corpus** — Lia's curated document library.
- **Canonical blessing** — the editorial status indicating a document has passed all three gates and is available to the retrieval system.
- **Article graph** — Lia's internal graph of ET articles and their cross-references, used for retrieval navigation.
- **Inline anchor / citation** — the `(Art. X E.T.)` reference pattern that appears in answers.
- **Retrieval** — the RAG step that finds document passages matching the accountant's query.
- **Harness** — Lia's automated metric suite that measures answer quality regressions.
