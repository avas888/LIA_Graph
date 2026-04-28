# Sprint Brief — Phase E–K Corpus Ingestion

> **Document type.** Single-page campaign-manager view for the corpus-ingestion experts. Aggregates the 12 per-source briefs into a sprint-able plan with concrete deliverables, source URLs, target counts, and validation gates.
>
> **Date:** 2026-04-28 Bogotá.
> **Author:** claude-opus-4-7 (engineer-side).
> **Status:** Open — ready to assign owners and start.
> **Pre-reads (in priority order):**
>   * `corpus_population_plan.md` (master plan — full read on first contact)
>   * `corpus_population_brief_edits.md` (the canonical-id rules every row must obey)
>   * `corpus_population/<NN>_<source>.md` (the brief for whichever source family you own)
>   * `state_corpus_population.md` (live progress tracker — update after each brief)
>   * `config/canonicalizer_run_v1/batches.yaml` (the YAML the canonicalizer harness reads)

---

## 1. Where we are right now

* **754 norms** verified end-to-end across Phases A–D (procedimiento, renta, IVA/retefuente, reformas Ley). These are in production-grade shape — do not re-touch them.
* **~2,650 norms** missing across Phases E–K. The 12 briefs in `corpus_population/` are the work plan to close the gap.
* **0 of 12 briefs ingested** today. Briefs ↔ canon ↔ YAML have just been reconciled (2026-04-28 afternoon Bogotá); the ingestion surface is unblocked.
* **Engineer-side canon extension shipped** — `cst.art.<N>`, `cco.art.<N>`, `dcin.<NUM>.cap.<C>.num.<N>`, `oficio.<emisor>.<NUM>.<YEAR>` are all canonical now. 118/118 canon tests passing.
* **5 scraper gaps still open** (master plan §7): auto.ce URL resolver (Gap #1), oficio.dian URL resolver (Gap #2), decreto.legislativo URL filename rewrite (Gap #3), CST + CCo Senado-style scraper (Gap #4), BanRep scraper (Gap #5). Each affected brief documents its gap; fixture-only paths exist for all of them.

---

## 2. Sprint plan (priority order from master §8 + state file §3)

### Sprint 1 — Pipeline pilot + labor regime (~440 norms target; 4 briefs)

The goal of sprint 1 is to validate the end-to-end pipeline on a small batch and unlock the highest-utility content for end users (accountants asking about labor obligations).

| Order | Brief | Family | Target norms | Scraper status | Why first |
|---:|---|---|---:|---|---|
| 1 | [11_pensional_salud_parafiscales.md](corpus_population/11_pensional_salud_parafiscales.md) | Ley 100/789/2381 (J5–J7) | ~80 | ✅ DIAN ley.* works | smallest, fully unblocked, no scraper work — pipeline pilot |
| 2 | [01_cst.md](corpus_population/01_cst.md) | CST (J1–J4) | ~170 | ❌ Gap #4 (fixture path available) | labor regime is first-class to Lia per operator scope memory |
| 3 | [08_conceptos_dian_unificados.md](corpus_population/08_conceptos_dian_unificados.md) | Conceptos unificados (G1–G6) | ~390 | ✅ DIAN works | most-cited DIAN doctrine — pilot G6 first to validate numeral splitter |
| 4 | [07_resoluciones_dian.md](corpus_population/07_resoluciones_dian.md) | Resoluciones DIAN (F1–F4) | ~140 | ✅ DIAN works | UVT, FE, RST, RUT — small files, scraper works today |

**Gate to advance to Sprint 2:** all four briefs at ✅ in §4 of state file; smoke check (master §6.3) reports ≥80% of target count for every batch in J1–J4, J5–J7, G1–G6, F1–F4. After sprint 1 the corpus jumps from 754 → roughly 1,500 verified-eligible norms.

### Sprint 2 — DUR family (~1,230 norms target; 4 briefs, share parser)

| Order | Brief | Family | Target norms | Scraper status | Notes |
|---:|---|---|---:|---|---|
| 5 | [02_dur_1625_renta.md](corpus_population/02_dur_1625_renta.md) | DUR 1625 Libro 1 (E1a–E1f) | ~500 | ✅ DIAN works | largest single artifact; ship parser first then reuse |
| 6 | [03_dur_1625_iva_retefuente.md](corpus_population/03_dur_1625_iva_retefuente.md) | DUR 1625 IVA + retefuente (E2a–E2c) | ~280 | ✅ DIAN works | reuses parser from 02 |
| 7 | [04_dur_1625_procedimiento.md](corpus_population/04_dur_1625_procedimiento.md) | DUR 1625 procedimiento (E3a–E3b) | ~200 | ✅ DIAN works | reuses parser from 02 |
| 8 | [05_dur_1072_laboral.md](corpus_population/05_dur_1072_laboral.md) | DUR 1072 (E6a–E6c, J8a–J8c) | ~250 | ✅ DIAN handles URL | different DUR but same DIAN scraper; verify primary source first (404 observed during brief research) |

**Gate to advance to Sprint 3:** the four DUR briefs at ✅; smoke check confirms E1a–E3b + E6a–E6c + J8a–J8c batches resolve to ≥80% of target.

### Sprint 3 — Long tail + cambiario + jurisprudencia (~680 norms; 4 briefs)

| Order | Brief | Family | Target norms | Scraper status | Notes |
|---:|---|---|---:|---|---|
| 9 | [12_cambiario_societario.md](corpus_population/12_cambiario_societario.md) | BanRep + DCIN-83 + CCo + Ley 222/1258 (K1–K4) | ~150 | ⚠️ Gaps #4 + #5 | K4 (~25 norms, Ley 222 + 1258) unblocks today; K1/K2/K3 need fixtures |
| 10 | [09_conceptos_dian_individuales.md](corpus_population/09_conceptos_dian_individuales.md) | Conceptos individuales + oficios (H1–H6) | ~430 | ⚠️ Gap #2 | also needs YAML H-batch regex tightening (called out in brief §7) |
| 11 | [10_jurisprudencia_cc_ce.md](corpus_population/10_jurisprudencia_cc_ce.md) | Jurisprudencia CC + CE + autos (I1–I4) | ~70 | ⚠️ Gap #1 (autos) | I1 already fixtured; I2/I3 need parsed sentencias; I4 needs Gap #1 fixed |
| 12 | [06_decretos_legislativos_covid.md](corpus_population/06_decretos_legislativos_covid.md) | Decretos legislativos COVID (E5) | ~30 | ⚠️ Gap #3 | small phase; URL filename rewrite needed |

**Sprint 3 done = corpus campaign done.** Total target: 754 + ~2,650 = ~3,400 verified-eligible norms.

---

## 3. Per-brief specification

For each brief: target count, source URLs (lifted verbatim from each brief's "Source URLs" section — verify before fetching), canonical id shape, scraper status, deliverable, and the validation command that gates ✅ status.

> **Source URLs.** Each URL below is what the brief's author put in the "Source URLs" section. The expert should confirm the URL is reachable before fetching at scale. Some briefs flagged URLs as "to be verified" (e.g. brief 05's DIAN DUR 1072 URL returned a 404 during brief research) — heed those warnings.

> **Canonical id round-trip.** Every `norm_id` you emit must round-trip through `lia_graph.canon.canonicalize()` returning the same string. The §4 validation script in `corpus_population_brief_edits.md` is the gate. Never invent article numbers — read them off the source.

### Sprint 1

#### Brief 11 — Pensional, Salud, Parafiscales (J5–J7)

| Field | Value |
|---|---|
| Target | **~80 norms** (J5 pensional + Ley 2381: ~30; J6 salud: ~25; J7 parafiscales: ~20 — per master §1.3) |
| Canonical shape | `ley.<NUM>.<YEAR>.art.<X>` |
| Verified-real parent ids (from `batches.yaml` J5/J6/J7) | `ley.100.1993`, `ley.797.2003`, `ley.2381.2024`, `ley.1438.2011`, `ley.1751.2015`, `ley.789.2002`, `ley.1822.2017`, `ley.2114.2021` |
| Source URLs | DIAN normograma `ley_100_1993.htm`, `ley_2381_2024.htm`, `ley_0789_2002.htm`. Senado `ley_0100_1993.html`/`_pr001.html` and `ley_0789_2002.html`/`_pr001.html` as backup. Funcion Pública gestor normativo for Ley 2381. (Full URL list in brief §Source URLs.) |
| Scraper | ✅ DIAN's `ley.*` resolver works today — no scraper work needed |
| Deliverable | Append per-article rows to `artifacts/parsed_articles.jsonl` for each article of Ley 100/1993, Ley 2381/2024, Ley 789/2002. Use the article number as printed (e.g. an article printed as "Artículo 47" → `ley.100.1993.art.47`). |
| Validation gate | `_resolve_batch_input_set` returns ≥80% of target for J5/J6/J7 (J5 ≥ 24, J6 ≥ 20, J7 ≥ 16) |
| Special note | Ley 2381/2024 is suspended by Corte Constitucional pending procedural reiteration (per brief). Ingest the text as-published; the vigencia harness extracts suspension status downstream. |

#### Brief 01 — CST (J1–J4)

| Field | Value |
|---|---|
| Target | **~170 norms** (J1 contratos: ~29; J2 prestaciones: ~51; J3 jornada: ~43; J4 colectivos: ~47+ — per master §4.6) |
| Canonical shape | `cst.art.<N>` (engineer-side canon extension shipped) |
| Source URLs | Senado `codigo_sustantivo_trabajo.html` + paginated segments `_pr001.html` … `_pr016.html` (full URL list in brief §Source URLs — 7 pagination segments named by the brief author covering Arts. 1–~492) |
| Scraper | ❌ Gap #4 — no Senado-style scraper for CST exists. Brief recommends fixture-only path (hand-curate parsed_articles entries) since CST changes infrequently. |
| Deliverable | Append per-article rows to `parsed_articles.jsonl` for CST articles in the four ranges: Arts. 22–50 (J1), 51–101 (J2), 158–200 (J3), 416+ (J4). Per the brief, sub-units (`.par.X`, `.lit.X`) stay inline in body text — do **not** create separate rows for them. |
| Validation gate | J1 ≥ 20, J2 ≥ 32, J3 ≥ 28, J4 ≥ 48 (80% of brief's targets) |

#### Brief 08 — Conceptos DIAN Unificados (G1–G6)

| Field | Value |
|---|---|
| Target | **~390 norms** total (G1 IVA: ~60; G2 renta: ~100; G3 retención: ~60; G4 procedimiento: ~60; G5 simple: ~60; G6 acid test: 1) |
| Canonical shape | `concepto.dian.<NUM>` (parent) and `concepto.dian.<NUM>.num.<X>` (per-numeral) |
| Verified-real ids (G6 — already fixtured) | `concepto.dian.100208192-202`, `concepto.dian.100208192-202.num.20`, `concepto.dian.100208192-202.num.12` |
| Source URLs | DIAN normograma `concepto_tributario_dian_<NUM>.htm` (per-concepto). Master index: `https://www.dian.gov.co/fizcalizacioncontrol/herramienconsulta/NIIF/ConceptosDian/Paginas/default.aspx`. |
| Scraper | ✅ DIAN handles `concepto.*` URLs |
| Deliverable | Each unified concepto gets parsed into per-numeral rows. **G6 is already fixtured** — pilot the numeral-splitting parser against G6 first to validate; only then roll out to G1–G5. The Concepto Unificado de Renta alone has 100+ numerales per master §4.3, so the parser must be solid. |
| Validation gate | G1 ≥ 48, G2 ≥ 80, G3 ≥ 48, G4 ≥ 48, G5 ≥ 48 (80% of target) — G6 already passes |
| Special note | Pilot G6's numeral-splitting before tackling G1–G5. If the splitter mis-bounds numerales, all 390 norms downstream are corrupted. |

#### Brief 07 — Resoluciones DIAN (F1–F4)

| Field | Value |
|---|---|
| Target | **~140 norms** total (F1 UVT + plazos: ~50; F2 FE + nómina + RADIAN: ~30; F3 RST: ~20; F4 cambiario + RUT + obligados: ~40) |
| Canonical shape | `res.dian.<NUM>.<YEAR>` (zero-padding allowed where DIAN uses it) |
| Verified-real id (in YAML F2) | `res.dian.165.2023`, `res.dian.2275.2023`, `res.dian.042.2020`, `res.dian.13.2021` |
| Source URLs | DIAN normograma `resolucion_dian_<NUM>_<YYYY>.htm`. Master index: `https://www.dian.gov.co/normatividad/Paginas/Resoluciones.aspx`. PDF downloads: `https://www.dian.gov.co/normatividad/Normatividad/`. |
| Scraper | ✅ DIAN handles `res.dian.*` |
| Deliverable | Per-resolución rows. Each resolución typically has multiple articles — emit one row per article OR one row per resolución (verify against existing veredictos in the corpus how granular). |
| Validation gate | F1 ≥ 40, F2 ≥ 25, F3 ≥ 15, F4 ≥ 30 (80% of target) |

### Sprint 2

#### Brief 02 — DUR 1625/2016 Libro 1 (E1a–E1f)

| Field | Value |
|---|---|
| Target | **~500 norms** spread across sub-libros 1.1 through 1.8+ (per master §4.1) |
| Canonical shape | `decreto.1625.2016.art.<dotted-decimal>` (use article number as printed) |
| Source URL | `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm` (single master page contains all three libros) |
| Scraper | ✅ DIAN handles `decreto.*` URL pattern |
| Deliverable | Parse Libro 1 articles into per-article rows. The leading segment after `art.` is always `1.` (DUR 1625 outer numbering). Use article numbers exactly as printed. |
| Validation gate | E1a ≥ 50, E1b ≥ 50, E1c ≥ 80, E1d ≥ 80, E1e ≥ 80, E1f ≥ 60 (80% of brief's per-batch targets in master Appendix A) |
| Special note | Ship the unified DUR parser here; briefs 03 and 04 reuse it. |

#### Brief 03 — DUR 1625/2016 IVA + retefuente (E2a–E2c)

| Field | Value |
|---|---|
| Target | **~280 norms** (~120 + ~80 + ~80 from Appendix A E2a/E2b/E2c) |
| Canonical shape | `decreto.1625.2016.art.1.3.<dotted-decimal>` (IVA, per YAML E2a/E2b prefix) and `decreto.1625.2016.art.1.2.4.<dotted-decimal>` (retefuente reglamentado, per YAML E2c) |
| Source URL | Same as brief 02 |
| Deliverable | Reuse parser from brief 02; restrict output to the IVA + retefuente sub-libros |
| Validation gate | E2a ≥ 60, E2b ≥ 80, E2c ≥ 60 (80% of brief's per-batch targets) |

#### Brief 04 — DUR 1625/2016 procedimiento + sanciones (E3a–E3b)

| Field | Value |
|---|---|
| Target | **~200 norms** (~80 + ~60 from Appendix A E3a/E3b) |
| Canonical shape | `decreto.1625.2016.art.1.5.<dotted-decimal>` (per YAML E3a/E3b prefix). Compound articles use hyphen-digit suffix (`-1`, `-2`); canon rejects hyphen-letter (`-A`). |
| Source URL | Same as brief 02 |
| Deliverable | Reuse parser from brief 02; restrict output to the procedimiento + sanciones books |
| Validation gate | E3a ≥ 80, E3b ≥ 60 |

#### Brief 05 — DUR 1072/2015 (E6a–E6c, J8a–J8c — shared)

| Field | Value |
|---|---|
| Target | **~250 norms** (E6a/E6b/E6c + J8a/J8b/J8c share rows) |
| Canonical shape | `decreto.1072.2015.art.<dotted-decimal>` (use article number as printed). YAML E6/J8 patterns target `art.2.2.<X>.*` (riesgos + SST). |
| Source URLs | DIAN: `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1072_2015.htm` (**flagged "to be verified — 404 observed" in brief**, so check before fetching at scale). MinTrabajo PDF: `https://www.mintrabajo.gov.co/documents/20147/.../DUR+Decreto+1072+2015+Actualizado.pdf`. Senado fallback: `https://www.secretariasenado.gov.co/senado/basedoc/decreto_1072_2015.html`. |
| Scraper | ✅ DIAN URL pattern works (when reachable) |
| Deliverable | Per-article rows. E6 and J8 share the parsed rows — ingestion only happens once. |
| Validation gate | E6a ≥ 60, E6b ≥ 80, E6c ≥ 80; J8a/J8b/J8c combined ≥ 200 (per Appendix A) |
| Special note | Verify the DIAN URL responds before fetching at scale. If 404, fall back to MinTrabajo PDF. |

### Sprint 3

#### Brief 12 — Cambiario, Societario (K1–K4)

| Field | Value |
|---|---|
| Target | **~150 norms** (K1 BanRep Res Ext 1/2018: ~25; K2 DCIN-83: ~40; K3 CCo: ~60; K4 Ley 222/1258: ~25) |
| Canonical shapes | `res.banrep.<NUM>.<YEAR>` (+ `.art.<X>`); `dcin.<NUM>.cap.<C>.num.<N>`; `cco.art.<N>`; `ley.<NUM>.<YEAR>.art.<X>` |
| Verified-real parent ids (in YAML K4) | `ley.222.1995`, `ley.1258.2008` |
| Source URLs (verified-live by brief author) | BanRep landing `https://www.banrep.gov.co/es/normatividad/resolucion-externa-1-2018`; PDF compendium `https://www.banrep.gov.co/sites/default/files/reglamentacion/compendio-res-ext-1-de-2018.pdf`; Senado CCo `https://www.secretariasenado.gov.co/senado/basedoc/codigo_comercio.html`; Senado Ley 222 `ley_0222_1995.html`; Senado Ley 1258 `ley_1258_2008.html`. (Full list in brief §Source URLs.) |
| Scraper | ⚠️ K1/K2 need BanRep scraper (Gap #5 — fixture-only path recommended). K3 needs Senado-style CCo scraper (Gap #4 — fixture path available, shares with brief 01). K4 ✅ DIAN ley.* works. |
| Deliverable | Per-article rows for each. K4 (~25 norms — Ley 222 + Ley 1258) ships first since unblocked today. K1/K2/K3 follow on the fixture path or after Gap #4/#5 are fixed. |
| Validation gate | K1 ≥ 20, K2 ≥ 30, K3 ≥ 50, K4 ≥ 20 |

#### Brief 09 — Conceptos individuales + Oficios (H1–H6)

| Field | Value |
|---|---|
| Target | **~430 norms** (H1 RST, H2 retención, H3a/b renta, H4a/b IVA, H5 procedimiento, H6 oficios) |
| Canonical shapes | `concepto.dian.<NUM>` (individual concepto); `oficio.dian.<NUM>.<YEAR>` (oficio — engineer-side canon extension shipped) |
| Source URLs (verified-live by brief author) | DIAN per-concepto `concepto_tributario_dian_<NUM>.htm`; per-oficio `oficio_dian_<NUM>_<YEAR>.htm`. Master indexes: `https://www.dian.gov.co/fizcalizacioncontrol/herramienconsulta/NIIF/ConceptosDian/Paginas/default.aspx` and `https://www.dian.gov.co/normatividad/Paginas/Oficios.aspx`. |
| Scraper | ⚠️ Gap #2 — DIAN scraper has no `oficio.dian.*` resolver. Brief specifies the ~10-line scraper extension required. |
| Deliverable | (a) The scraper extension for `oficio.dian.*` (or a fixture-only path on the top-200 oficios), (b) parsed conceptos and oficios in corpus, (c) regex-tightening pass on H-batches in `batches.yaml` to fix the observed 5,608 false-positive over-matches (per brief §7). |
| Validation gate | H1–H6 combined ≥ 350 (Appendix A) |

#### Brief 10 — Jurisprudencia CC + CE + Autos (I1–I4)

| Field | Value |
|---|---|
| Target | **~70 norms** (I1 acid: 5 — already done; I2 principios: ~15; I3 CE unificación: ~30; I4 autos CE: ~20) |
| Canonical shapes | `sent.cc.<TYPE>-<NUM>.<YEAR>` (TYPE uppercase); `sent.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>`; `auto.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>` (date mandatory) |
| Verified-real ids in YAML | `sent.cc.C-481.2019`, `sent.cc.C-079.2026`, `sent.cc.C-384.2023`, `sent.cc.C-101.2025`, `sent.cc.C-540.2023`; `sent.ce.28920.2025.07.03`; `auto.ce.082.2026.04.15`, `auto.ce.084.2026.04.15`, `auto.ce.28920.2024.12.16` |
| Source URLs (verified-live by brief author) | Corte Constitucional relatoria `https://www.corteconstitucional.gov.co/relatoria/<YEAR>/<TYPE>-<NUM>-<YY>.htm`; Consejo de Estado `https://www.consejodeestado.gov.co/decisiones_u/` and `https://www.consejodeestado.gov.co/seccion-cuarta/`; DIAN compilation hosts CE sentencias and autos by radicado. |
| Scraper | ⚠️ Gap #1 (autos CE resolver). I1 ✅ already in YAML explicit_list. I2/I3 need parsed sentencias. I4 needs Gap #1 fix or fixture-only autos. |
| Deliverable | Parsed sentencias for I2 (Art. 363 / Art. 338 principios) and I3 (CE unificación section cuarta). For I4, either implement Gap #1 or fixture the autos directly in `tests/fixtures/scrapers/consejo_estado/autos/<radicado>.html`. |
| Validation gate | I1 = 5 (already done); I2 ≥ 12; I3 ≥ 25; I4 ≥ 15 |

#### Brief 06 — Decretos Legislativos COVID (E5)

| Field | Value |
|---|---|
| Target | **~30 norms** total |
| Canonical shape | `decreto.<NUM>.<YEAR>.art.<X>` (NO `.legislativo.` segment — that's in the URL filename only, not the canonical id) |
| Verified-real parent decreto numbers (from YAML E5 regex) | `decreto.417.2020`, `decreto.444.2020`, `decreto.535.2020`, `decreto.568.2020`, `decreto.573.2020`, `decreto.772.2020` |
| Source URLs | DIAN `decreto_legislativo_<NUM>_<YEAR>.htm`. Senado `decreto_legislativo_<NUM>_<YEAR>.html` as fallback. |
| Scraper | ⚠️ Gap #3 — DIAN scraper needs URL filename rewrite case for `decreto.legislativo.*`. Brief includes the ~5-line patch. |
| Deliverable | Scraper extension + parsed articles. Article numbers use the as-printed value; do not invent. |
| Validation gate | E5 ≥ 20 (regex slice resolves ≥80% of the 6 verified-real decreto ids' articles) |

---

## 4. Cross-cutting requirements

These apply to every brief. Skipping any of them causes silent rejection at insert time or ghost rows in the input set.

### 4.1 Canonical id rules — non-negotiable

* Every `norm_id` must round-trip through `lia_graph.canon.canonicalize()` returning the same string. Test before committing.
* Article numbers go in the id **as printed in the source**. Do not invent compound numbers. Do not add letter suffixes (`-A`, `-B`) — canon accepts hyphen-digit only.
* Sub-units (parágrafo, inciso, numeral, literal) stay inline in the article body for most families. The exceptions are spelled out in each brief.
* For DUR family (1625, 1072): use the dotted-decimal article number from the source. The libro / parte / título / capítulo structure is human metadata for the body field — never encode it as a separate segment.
* For sentencias CC: prefix is `sent.cc.` (NOT `sentencia.cc.`); type letter is uppercase (`C`, `T`, `SU`, `A`).
* For sentencias CE + autos CE: keyed by radicado-number + decision-date in `YYYY.MM.DD` form. The sección lives in body metadata, not the id. Date is required.
* For decretos legislativos COVID: use plain `decreto.<NUM>.<YEAR>` — no `.legislativo.` segment.
* Full grammar in `corpus_population_plan.md §5` and the canonicalizer source `src/lia_graph/canon.py::_NORM_ID_FULL_RE` (last word wins on disagreement).

### 4.2 `parsed_articles.jsonl` row schema

Per master §6.1:

```json
{
  "norm_id": "<canonical-id>",
  "norm_type": "<articulo_et|ley_articulo|decreto_articulo|res_dian|concepto_dian|oficio_dian|sent_cc|sent_ce|auto_ce|cst_articulo|cco_articulo|res_banrep|dcin_numeral>",
  "article_key": "<short label>",
  "body": "<full verbatim text from source>",
  "source_url": "<the gov.co URL the body came from>",
  "fecha_emision": "<YYYY-MM-DD if known, else null>",
  "emisor": "<Congreso, DIAN, CC, CE, BanRep, MinTrabajo, etc.>",
  "tema": "<thematic tag, optional>"
}
```

The `body` field is what `build_extraction_input_set.py` walks via `find_mentions()`. Make sure the article body actually mentions the canonical citation (e.g. "Art. 22 CST" in the text), otherwise the input-set builder won't pick it up — see `corpus_population_reconciliation.md §2` for the full mechanism.

### 4.3 Validation snippet — paste this after every brief

```bash
PYTHONPATH=src:. uv run python -c "
import json
from lia_graph.canon import canonicalize

count = 0
bad = []
with open('artifacts/parsed_articles.jsonl') as f:
    for i, line in enumerate(f, 1):
        row = json.loads(line)
        nid = row.get('norm_id')
        if not nid: continue
        if canonicalize(nid) != nid:
            bad.append((i, nid, canonicalize(nid)))
        count += 1

if bad:
    print(f'FAIL — {len(bad)} of {count} rows have non-canonical norm_id:')
    for line, nid, c in bad[:20]:
        print(f'  line {line}: {nid!r} -> {c!r}')
    raise SystemExit(1)
print(f'OK — all {count} rows have canonical norm_ids.')
"
```

Then run the §6.3 batch-resolution check from `corpus_population_plan.md` for whichever batches your brief covers.

### 4.4 Build the input set after every brief

```bash
PYTHONPATH=src:. uv run python scripts/canonicalizer/build_extraction_input_set.py
```

This regenerates `evals/vigencia_extraction_v1/input_set.jsonl` from the new rows. Confirm the output mtime advances and the per-batch slice sizes match your validation gate.

---

## 5. Definition of done — per brief and per sprint

### Per brief

A brief moves from 🟡 to ✅ when **all six** of these hold:

1. All target rows appended to `artifacts/parsed_articles.jsonl`.
2. The §4.3 validation snippet returns `OK`.
3. The §4.4 input-set builder ran cleanly (mtime advanced).
4. The brief's specific smoke-verification command (in the brief's "Smoke verification" section) reports ≥80% of target for every batch the brief covers.
5. State file `state_corpus_population.md` §4 row updated: status 🟡 → ✅, owner set, last-update timestamp.
6. State file §10 run-log gets one new entry: `YYYY-MM-DD HH:MM TZ — brief NN — ingested <count> rows; smoke check OK.`

### Per sprint

A sprint is done when every brief in the sprint is at ✅. The state file §3 "Briefs ingested" counter advances accordingly.

### End of campaign

Done when the canonicalizer Postgres `norm_vigencia_history` count climbs from 754 to ≥3,000 distinct norm_ids — gate is master plan §9.

---

## 6. Reporting + state-file update protocol

After **every brief** (not at end of sprint):

1. Update `state_corpus_population.md` §4 row for that brief.
2. Append a line to §10 run-log per the format above.
3. Commit one brief per commit using the format `corpus(<source>): ingest <N> rows for brief <NN>` (per master §10.5).
4. If you hit a blocker, add a row to §10 with what's blocking and what you tried, then update the brief's "Blockers" column in §4.

If you advance the state file's §3 global state (e.g. a sprint completes, a scraper gap is closed), edit §3 in the same commit so an incoming agent reads accurate counts.

---

## 7. Out of scope

* Don't change `src/lia_graph/canon.py` — engineer-owned. If a new family needs canonicalization, raise it as a blocker in §10 and the engineer will ship the rule.
* Don't change `config/canonicalizer_run_v1/batches.yaml` slice definitions, **except** brief 09's H-batch regex tightening, which is explicitly called out as part of brief 09's deliverable.
* Don't run the canonicalizer harness yourself. After a brief ships, the engineer / operator runs `bash scripts/canonicalizer/run_full_campaign.sh --phases <X>` to verify vigencia for the new norms. That's the next gate, not yours.
* Don't ingest into Postgres directly. The pipeline is `parsed_articles.jsonl` → `build_extraction_input_set.py` → `extract_vigencia.py` → `ingest_vigencia_veredictos.py` → Postgres `norm_vigencia_history`. Skipping steps breaks the audit trail.

---

## 8. Quick-start (paste this into your terminal to begin sprint 1)

```bash
# Confirm you're in the repo
cd /Users/ava-sensas/Developer/Lia_Graph

# Source env + verify canon is current
set -a; . .env.local; set +a
PYTHONPATH=src:. uv run python -c "from lia_graph.canon import canonicalize; print(canonicalize('cst.art.22'))"
# Expected: cst.art.22  (means the engineer-side canon extension is live)

# Read your brief
cat docs/re-engineer/corpus_population/11_pensional_salud_parafiscales.md  # if you took brief 11

# Append rows to artifacts/parsed_articles.jsonl using your parser
# … (your parser code here; one row per article per the §4.2 schema)

# Validate
PYTHONPATH=src:. uv run python -c "..."   # §4.3 snippet
PYTHONPATH=src:. uv run python scripts/canonicalizer/build_extraction_input_set.py

# Update state file + commit
# (edit docs/re-engineer/state_corpus_population.md §4 + §10)
git add artifacts/parsed_articles.jsonl docs/re-engineer/state_corpus_population.md
git commit -m "corpus(ley_100): ingest <N> rows for brief 11"
```

---

*Sprint brief drafted 2026-04-28 by claude-opus-4-7. Lives next to `corpus_population_plan.md` (master) and `corpus_population_brief_edits.md` (id-shape rules). Scope is the corpus-expert's work for the next 7–10 days; engineer's work (canon extensions, scraper gap fixes, canonicalizer campaign) is tracked separately in `fixplan_v4.md`.*
