# Lia — Taxonomy v2 expert brief

> **Purpose of this brief.** Lia (a graph-native RAG for Colombian SMB accountants) is rebuilding its topic taxonomy because the current one has missing categories and overlapping ones. We need 60–90 minutes of expert input from a practicing accountant / abogado tributarista to lock the v2 design. This document is the context you need before that conversation. Read time ≈ 10 minutes.
>
> **Who's asking.** Lia engineering, after a 2026-04-24 audit found 81 % cross-domain contamination on the `iva` topic node and ≥ 2 missing categories. Detail in `docs/aa_next/done/structural_groundtruth_v1.md` (closed cycle; preserved for context).

---

## 1. What Lia is and who it serves

- **Product.** A chat assistant that answers Colombian-accounting questions by retrieving relevant articles, regulations, and guidance from a curated corpus, then composing an answer that cites its sources.
- **Primary user.** The SMB accountant ("contador de PYME") who, in real practice, is also the de-facto labor/payroll advisor, the compliance lead, and sometimes the legal contact for the company. They aren't tax-only or labor-only — they're operational generalists.
- **Question scope.** Tax (renta, IVA, GMF, ICA, retenciones, timbre, INC, gananacia ocasional, patrimonio, …), labor (CST, Ley 100, Ley 2466, parafiscales, UGPP, MinTrabajo), payroll mechanics (liquidación, aportes, PILA), accounting (NIIF PYMES + NIIF Plenas), procedural tax (firmeza, sanciones, devoluciones, RUT), sectoral regulation, and compliance (SAGRILAFT, PTEE, RUB, RNBD).

---

## 2. What we mean by "labels" / "taxonomy"

Lia's retrieval depends on **three orthogonal label axes** attached to every document:

1. **Topic** (the subject area) — e.g. `iva`, `laboral`, `sagrilaft_ptee`. This is where most of the audit damage is.
2. **Subtopic** (a finer slice inside a topic) — e.g. `liquidacion_salario` under `laboral`, `regimen_responsabilidad_iva` under `iva`. Some topics have many; some have none.
3. **Orthogonal axes** (currently lightweight; may need expansion):
   - **Document type** — Ley, Decreto, Resolución, Concepto DIAN, Sentencia, Doctrina, Guía práctica.
   - **Authority / issuer** — DIAN, MinHacienda, MinTrabajo, Supersociedades, Superfinanciera, UGPP, Banrep.
   - **Vigencia** — vigente, derogada, suspendida, modificada-parcialmente.
   - **Effective date** — when this document started applying.

This brief focuses on the **Topic** axis (and lightly the Subtopic axis), because that's where the audit found the most damage.

---

## 3. What "ideal" means — first principles

An ideal topic taxonomy satisfies **four non-negotiables**:

| # | Rule | Why it matters | Failure mode if violated |
|---|---|---|---|
| 1 | **Exhaustive** | Every doc has a place to live; no "miscellaneous" bucket large enough to hide things. | The AI labeler picks the nearest-sounding wrong topic when no right answer exists. We saw this with `impuesto_timbre`: ET Libro 4 (≈30 articles) got dumped into `facturacion_electronica`. |
| 2 | **Mutually exclusive** | Two topics never reasonably claim the same document. | The labeler coin-flips on borderline docs → unstable verdicts → contamination. We see this between `iva` and `procedimiento_tributario`: 435 procedural-tax edges currently live under `iva`. |
| 3 | **User-aligned** | Topic names + scope match how an SMB accountant describes a question. | If the accountant asks about "tarifas mínimas de renta" but the topic key is `tarifas_tasa_minima_renta`, the router has to bridge the gap — increasing miss-classification. |
| 4 | **Machine-pickable** | The labeler is an LLM picking a topic key from the full taxonomy list per document. The list must be enumerable, finite, and disambiguated. | Free-form labeling drifts; pick-from-list is reliable iff the list is a small, well-defined enumeration. |

Engineering owns rules 4 and parts of 1+2. **Experts (you) own rules 1, 2, 3** — only a practitioner knows the real-world boundaries between subject areas, what users actually call things, and what's missing entirely.

---

## 4. What the ideal taxonomy should CONTAIN (per topic row)

For each topic, we need a row with these fields:

| Field | What it is | Example |
|---|---|---|
| `key` | Slug — lowercase, snake_case, used internally | `impuesto_timbre` |
| `label` | Display name in Spanish, accountant-vocabulary | `Impuesto de Timbre Nacional` |
| `definition` | One-line definition. What is this topic about? | "Impuesto sobre actos jurídicos formales (escritos públicos, contratos, etc.) regulado en ET Libro 4." |
| `scope_in` | What KINDS of docs / questions belong here. | "ET arts. 514–540, decretos reglamentarios sobre tarifas y exenciones, conceptos DIAN sobre actos gravados." |
| `scope_out` | What does NOT belong here, with pointer to the right neighbor. | "Notas crédito en factura electrónica → `facturacion_electronica`. Estampillas departamentales o municipales → `sector_administracion_publica` (sub: estampillas)." |
| `typical_sources` | Where in the corpus the docs typically live. | "ET Libro 4 (`RENTA/NORMATIVA/Normativa/17_Libro4_Timbre.md`); decretos 2076/1992, 175/2025; conceptos DIAN; doctrina especializada." |
| `keyword_anchors` | 5–15 phrases the user might say. Used by the keyword router. | `["impuesto de timbre", "timbre nacional", "actos gravados con timbre", "tarifa timbre", "exención de timbre", "ET 514", "ET 519"]` |
| `allowed_et_articles` | Which ET article numbers may legitimately be cited from this topic (per the citation allow-list mechanism). | `["514", "515", "516", ..., "540", "539-1", "539-2", "539-3"]` |
| `parent` | If this is a subtopic, name the parent topic. Else `null`. | `null` for top-level; `"declaracion_renta"` for `firmeza_declaraciones`. |
| `status` | `active`, `deprecated`, `merged_into:<other_key>` for taxonomy-version tracking. | `active` |
| `version_added` | Taxonomy version this entered the schema. | `v2.0 (2026-04-25)` |

The `scope_out` pointer is what makes the taxonomy **mutually exclusive** in practice: every borderline question has a documented "this goes there" arrow.

---

## 5. Current state — what we already have, what's broken

### 5.1 Numbers

- **79 topics** in the current taxonomy (`config/topic_taxonomy.json`).
- **67 of those have at least one document** assigned (in production cloud).
- **12 are empty** — slot exists, no doc routed there.
- **At least 2 corpus domains have no taxonomy slot** — confirmed missing.

### 5.2 The 12 empty topic slots (need RECLASSIFY, not new classes)

| Empty topic | Why it's empty | Likely correct content |
|---|---|---|
| `ingresos_fiscales_renta` | Classifier sends ET Libro 1 Cap 1 (Ingresos) to `iva` instead. | ET arts. 26–57. |
| `patrimonio_fiscal_renta` | Classifier sends ET Libro 1 Título 2 (Patrimonio) to `sector_cultura`. (yes, really.) | ET arts. 261–298. |
| `firmeza_declaraciones` | Has a corpus dir; classifier disperses into 2–3 unrelated topics. | ET art. 714 + reglamentación. |
| `devoluciones_saldos_a_favor` | Has a corpus dir; classifier sends to `iva` (Libro 5 procedimiento dump). | ET arts. 850–865. |
| `ganancia_ocasional` | Probably scattered into `iva` or `declaracion_renta`. | ET Libro 1 Título 3, arts. 299–318. |
| `renta_liquida_gravable` | Probably scattered. | ET Libro 1 T1 Cap 7. |
| `descuentos_tributarios_renta` | Probably scattered. | ET arts. 254–260. |
| `anticipos_retenciones_a_favor` | Probably scattered. | ET arts. 365–371. |
| `tarifas_tasa_minima_renta` | Probably scattered. | ET arts. 240–243. |
| `beneficio_auditoria` | Unclear. | ET art. 689-3. |
| `conciliacion_fiscal` | Unclear. | DUR + formato 2516. |
| `regimen_sancionatorio_extemporaneidad` | Unclear. | ET art. 641. |

Engineering can fix all 12 once the classifier knows where to send the content. **Expert input needed: confirm the "Likely correct content" column and add the user-vocabulary phrases.**

### 5.3 Confirmed missing categories — need NEW classes

| Proposed key | Domain | Evidence we found it missing |
|---|---|---|
| `impuesto_timbre` | Impuesto de timbre nacional | ET Libro 4 (~30 arts.) currently mis-bound to `facturacion_electronica` (the Q11 case). |
| `rut_responsabilidades` | RUT — responsabilidades, códigos, actualización | RUT corpus dir gets bucketed into `beneficiario_final_rub`, but RUT and RUB are distinct registries. |

### 5.4 Maybe-missing categories — need expert verdict

| Proposed key | Domain | Or instead, fits as subtopic of … |
|---|---|---|
| `renta_presuntiva` | Renta presuntiva (ET art. 188-189) | Subtopic of `declaracion_renta`? |
| `proteccion_datos_personales` | Habeas data, RNBD, Ley 1581 | Subtopic of `datos_tecnologia`? |
| `parafiscales` | ICBF, SENA, Cajas, parafiscales especiales | Subtopic of `laboral`? |
| `zomac_incentivos` | ZOMAC + ZESE + zonas estratégicas | Subtopic of `inversiones_incentivos`? |
| `reforma_laboral_2466` | Ley 2466 de 2025 reforma laboral | Subtopic of `laboral`? |
| `reforma_pensional` | Already top-level — boundary with `laboral`? | Existing — confirm boundary. |
| `niif_pymes` vs `niif_plenas` | Currently both in `estados_financieros_niif` | Need split? |

### 5.5 Magnet topics — need MUTUAL-EXCLUSIVITY RULE (boundary calls)

These topics are flooded with content that doesn't belong, because their boundaries are ambiguous:

- **`iva` vs `procedimiento_tributario`** — 435 procedural-tax edges live in `iva`. Where exactly is the line? Probably: IVA topic = substantive law (causal hecho generador, base, tarifa, responsables, exenciones). Procedimiento topic = how you declare/pay/audit/discuss with DIAN. **SME confirm.**
- **`iva` vs the RENTA-family topics** — 252 ET Libro 1 (renta) edges live in `iva`. Likely classifier confusion. **SME confirm: when content is in ET Libro 1, default topic is renta-family, not iva.**
- **`comercial_societario` vs `obligaciones_mercantiles`** — gold file (Q19) shows ambiguity. Are these one topic, two topics, or one is subtopic of the other?
- **`facturacion_electronica` vs (new) `impuesto_timbre`** — once `impuesto_timbre` lands, the boundary is clean (timbre = ET Libro 4; FE = factura/nota crédito mechanics).
- **`beneficiario_final_rub` vs (new) `rut_responsabilidades`** — RUB ≠ RUT. RUB is the beneficial-owner registry under Resolución DIAN 164/2021. RUT is the general taxpayer registry. **Confirm.**
- **`laboral` vs `reforma_pensional` vs (maybe) `reforma_laboral_2466`** — if 2466 is a top-level topic, what's left in `laboral`? **Confirm structure.**

---

## 6. What we need from the expert

Specifically, in priority order:

### 6.1 Mandatory inputs (block the freeze)

1. **Confirm or amend the two confirmed-missing classes** — `impuesto_timbre`, `rut_responsabilidades`. Are the names right? Scope correct? Any subtopics needed under them?
2. **Decide each maybe-missing class** — for each row in §5.4, is it (a) a new top-level topic, (b) a subtopic of an existing topic, or (c) doesn't need its own slot?
3. **Resolve each magnet-topic boundary** — for each pair in §5.5, write the "this goes here, that goes there" rule. We'll codify it in each topic's `scope_out` field.
4. **Validate the 12 empty-slot reclassifications** in §5.2 — confirm we're sending the right content to the right slot.

### 6.2 Per-topic data (per row template in §4)

For every topic — both new and existing — the SME provides:

- Definition (one line, accountant-vocabulary).
- `scope_in`: 1–3 sentences on what kinds of docs/questions belong.
- `scope_out`: explicit "NOT this — that goes to `<key>`" pointers for the closest 2–3 neighbor topics.
- `keyword_anchors`: 5–15 phrases. Real ones from how you/your colleagues describe the topic. Including informal ones.
- `allowed_et_articles`: which ET article numbers are legitimately citable (we use this as a defensive filter against retrieval contamination).

For 79 topics, this is the bulk of the work — but most existing topics will only need light review, not full re-authoring.

### 6.3 Optional but high-value

- **Edge-case docs.** Are there documents you know about where the right topic is genuinely unclear? List them. They become test cases.
- **User-question samples.** 30–50 real questions from your professional practice, ideally with the topic you'd assign. We use these to validate the classifier post-rebuild.
- **Currency / vigencia hints.** Documents that frequently change (e.g. UVT, retenciones tarifas, calendario tributario) — flag them. Lia's currency awareness depends on this.

---

## 7. How to give input

Pick whichever is easiest:

- **Markdown / text doc** — fill a copy of this brief's §6 sections inline. Send as a file or in chat.
- **Spreadsheet** — one row per topic, columns matching §4's field list. Send as `.xlsx` or Google Sheets link.
- **Voice / call** — schedule a 60–90 min session; engineering captures the answers into the same format.
- **Iterative** — start with §6.1 (the four blockers); we can do §6.2 in batches per topic family (renta-family one week, procedural another, etc.).

Engineering's commitment: every input the SME provides lands in `config/topic_taxonomy.json` verbatim, with the SME's name in the version change-log, by the next ingest cycle.

---

## 8. What changes after this brief

Once the SME inputs land:

1. Engineering writes `taxonomy_v2.json` from the SME's deliverables.
2. CI gate: every topic in the gold file (`evals/gold_retrieval_v1.jsonl`) must exist in the new taxonomy (per `docs/learnings/retrieval/citation-allowlist-and-gold-alignment.md`).
3. We re-run the cloud full-rebuild at `--classifier-workers 4`; the §J cleanup mechanism wipes the historical mis-classified TEMA edges; the classifier — now with the right list to pick from + path-based veto — produces correct verdicts.
4. We re-run the 30-question staging A/B. If it passes the four gates (seeds ≥ 20/30, mean primary ≥ 2.5, contamination 4/4 clean, no regression), the TEMA-first feature flips back to ON and Lia is structurally healthy.
5. The SME's input is the rate-limiting step. Engineering can do the rest in 1–2 days once we have it.

---

## 9. Background reading (optional)

- `docs/aa_next/done/structural_groundtruth_v1.md` — the full multi-layer plan and first-principles analysis (closed cycle).
- `docs/aa_next/done/next_v2.md §J.6` — the audit data this brief summarizes (closed cycle).
- `docs/learnings/ingestion/corpus-completeness.md` — why corpus + taxonomy completeness matters more than any retrieval tuning.
- `docs/learnings/retrieval/citation-allowlist-and-gold-alignment.md` — the gold-file alignment rule and how `allowed_et_articles` is used.

---

*Drafted 2026-04-25 by Lia engineering. Feedback / SME inputs → this file's §6 sections, or directly into `config/topic_taxonomy.json` v2 draft when it opens.*
