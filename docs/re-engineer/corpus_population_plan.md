# Corpus Population Plan — What the Canonicalizer Needs the Ingestion Expert to Provide

> **Document type.** Architectural meta-documentation for the Lia canonicalizer pipeline.
> Not corpus content (NORMATIVA / EXPERTOS / PRACTICA). Lives in `Context/` per
> the standing convention.
>
> **Last verified:** 2026-04-28 03:00 AM Bogotá.
> **Author:** claude-opus-4-7.
> **Status:** Draft 1 — for ingestion expert review.
> **Source of truth for:** what shape the corpus must take so the canonicalizer's
> Phase E–K batches resolve to non-empty norm slices.

---

## Document control

| Field | Value |
|---|---|
| Master plan | This document |
| Companion state file | `docs/re-engineer/state_corpus_population.md` (to be created — see §10.4) |
| Per-source briefs | `docs/re-engineer/corpus_population/NN_<source>.md` (to be created — see §10) |
| Canonical id grammar | `docs/re-engineer/fixplan_v3.md` §0.5 (authoritative) |
| Round-trip enforcer | `src/lia_graph/canon.py::canonicalize` |
| YAML batches | `config/canonicalizer_run_v1/batches.yaml` |
| Input-set builder | `scripts/canonicalizer/build_extraction_input_set.py` |
| Extractor | `scripts/canonicalizer/extract_vigencia.py` |
| Writer | `scripts/canonicalizer/ingest_vigencia_veredictos.py` |

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [The gap, precisely](#2-the-gap-precisely)
3. [How slice resolution works (mechanics)](#3-how-slice-resolution-works-mechanics)
4. [Per-phase population requirements](#4-per-phase-population-requirements)
5. [Canonical norm-id grammar — quick reference](#5-canonical-norm-id-grammar--quick-reference)
6. [Required deliverables from the ingestion expert](#6-required-deliverables-from-the-ingestion-expert)
7. [Scraper coverage gaps (blockers)](#7-scraper-coverage-gaps-blockers)
8. [Suggested priority order](#8-suggested-priority-order)
9. [Definition of done](#9-definition-of-done)
10. [Document layout for ingestion experts](#10-document-layout-for-ingestion-experts)
11. [Estimated compute cost](#11-estimated-compute-cost)
12. [Out of scope](#12-out-of-scope)
13. [Appendix A — Verification matrix](#appendix-a--verification-matrix)
14. [Appendix B — Risk register](#appendix-b--risk-register)

---

## 1. Executive summary

### 1.1 Current state

The canonicalizer has verified vigencia for **754 unique norms** across Phases A
(procedimiento), B (renta), C (IVA / retefuente / GMF), and D (reformas Ley).
Phases E through K consistently returned **0 successes** during yesterday's
autonomous campaign because the YAML's batch slices resolved to **0 matching
norm_ids in the parsed corpus**.

This is a **corpus-coverage gap, not a canonicalizer bug.** The harness,
scrapers, prompt, and writer are working — they have nothing to chew on.

### 1.2 Decision pending

Two paths:

- **(a)** Populate the corpus per this document so the canonicalizer can finish
  Phases E–K, taking total verified vigencia from **754 → ~3,400 norms**.
- **(b)** Mark the canonicalizer "done for what we have" (754) and pivot
  directly to staging promotion of those.

This document supports decision **(a)**. Decision **(b)** does not need it.

### 1.3 Scope at a glance

| Phase | Family | Expected norms | Scraper ready? | Corpus parsing required? |
|---|---|---:|---|---|
| E1–E3 | DUR 1625/2016 (renta + IVA + procedimiento) | ~980 | ✅ | ✅ |
| E4 | Decreto 1474/2025 + autos CE | 4 | ⚠️ partial | ✅ |
| E5 | Decretos legislativos COVID + emergencia | ~30 | ⚠️ partial | ✅ |
| E6 + J8 | DUR 1072/2015 (laboral + SST) | ~250 | ✅ | ✅ |
| F1–F4 | Resoluciones DIAN (UVT, FE, RST, RUT) | ~140 | ✅ | ✅ |
| G1–G6 | Conceptos DIAN unificados | ~390 | ✅ | ✅ |
| H1–H6 | Conceptos individuales + Oficios | ~430 | ⚠️ partial | ✅ |
| I1 | Sentencias CC (reformas) | 5 | ✅ | ✅ done |
| I2 | Sentencias CC (principios) | ~15 | ✅ | ✅ |
| I3 | Sentencias CE de unificación | ~30 | ⚠️ partial | ✅ |
| I4 | Autos CE de suspensión provisional | ~20 | ❌ missing | ✅ |
| J1–J4 | CST (Código Sustantivo del Trabajo) | ~170 | ❌ missing | ✅ |
| J5–J7 | Ley 100/1993 + Ley 2381/2024 + parafiscales | ~80 | ✅ | ✅ |
| K1 | Resolución Externa 1/2018 JDBR | ~25 | ❌ missing | ✅ |
| K2 | DCIN-83 (Manual Cambiario BanRep) | ~40 | ❌ missing | ✅ |
| K3 | Código de Comercio (sociedades) | ~60 | ❌ missing | ✅ |
| K4 | Ley 222/1995 + Ley 1258/2008 | ~25 | ✅ | ✅ |
| **Total** | | **~3,400 - 754 = ~2,650 to add** | | |

**Five scraper gaps** (⚠️ partial / ❌ missing) block ~440 norms regardless of
corpus parsing effort. They are catalogued in §7 and must be resolved (or
fixtured) before the affected phases can complete.

---

## 2. The gap, precisely

`scripts/canonicalizer/extract_vigencia.py --batch-id <X>` resolves a slice by:

1. Reading the corpus's deduplicated input set
   (`evals/vigencia_extraction_v1/input_set.jsonl`, built by
   `scripts/canonicalizer/build_extraction_input_set.py` from
   `artifacts/parsed_articles.jsonl`).
2. Applying the batch's `norm_filter` from
   `config/canonicalizer_run_v1/batches.yaml`.
3. Returning the intersection.

When we audit batch slice sizes against the current corpus:

| Phase | Audit result | Expected |
|---|---|---|
| A1–A4 | 136 norms | ✅ covered |
| B1–B10 | 404 norms | ✅ covered |
| C1–C4 | 112 norms | ✅ covered |
| D1–D8c | 298 norms | ✅ covered (after the `ley.*` URL-resolver fix shipped 2026-04-27) |
| **E1a–E6c** | **6 norms** (E4 acid test only) | ~500 |
| **F1–F4** | **2 norms** | ~140 |
| **G1–G6** | **7 norms** (G6 acid test only) | ~390 |
| **H1–H6** | regex over-matches the corpus (5,608 false positives observed); coverage is actually missing | ~430 |
| **I1–I4** | **5 norms** (I1 acid test only) | ~70 |
| **J1–J8c** | **9 norms** (J5/J6/J7 acid tests only) | ~430 |
| **K1–K4** | **2 norms** (K4 acid test only) | ~150 |

**Translation.** ~1,690–2,650 norms (depending on how deeply we parse the
unified conceptos and DUR libros) are missing from the parsed corpus at the
canonical id-shapes the YAML expects. That is roughly **80–85% of the
canonicalizer's intended scope.**

The few non-zero E/F/G/I/J/K slices today come from `explicit_list` batch
entries — hand-curated acid-test fixtures we seeded for harness validation.
Every batch using `prefix` or `regex` filters depends on the corpus actually
containing norm_ids in those shapes, and that is what is missing.

---

## 3. How slice resolution works (mechanics)

### 3.1 The four filter types

`config/canonicalizer_run_v1/batches.yaml` uses four `norm_filter` shapes. To
populate a phase, the corpus must contain norm_ids that match the filter:

| Filter type | Example | Corpus must contain |
|---|---|---|
| `prefix` | `prefix: "decreto.1625.2016.art.1.5."` | norm_ids starting with that exact prefix |
| `regex` | `pattern: "^decreto\\.1625\\.2016\\.art\\.1\\.\\d+\\..+"` | norm_ids matching the regex |
| `et_article_range` | `from: 555, to: 580-2` | `et.art.555` through `et.art.580-2` (works today; ET fully populated) |
| `explicit_list` | `norm_ids: [...]` | exact ids (always works regardless of corpus shape) |

### 3.2 The round-trip rule

The canonical grammar for each norm_id is defined in
`docs/re-engineer/fixplan_v3.md` §0.5. The canonicalizer enforces it via
`src/lia_graph/canon.py::canonicalize`. Any norm_id added to the corpus must
**round-trip cleanly** through `canonicalize`:

```python
from lia_graph.canon import canonicalize
assert canonicalize("sent.cc.C-481.2019") == "sent.cc.C-481.2019"
```

If `canonicalize(x) != x`, the writer rejects the veredicto at insert time.
Yesterday's D5 batch hit this: 36 of 39 rows errored because Gemini emitted
`sentencia.C-481.2019` (missing `sent.cc.` court prefix) where the
canonical form is `sent.cc.C-481.2019`. The corpus row, the YAML, and any
hand-written id must all use the canonical form.

### 3.3 Common rejection patterns to avoid

| Wrong | Right | Reason |
|---|---|---|
| `sentencia.C-481.2019` | `sent.cc.C-481.2019` | court prefix `cc.` required with `sent` prefix, TYPE uppercase |
| `Decreto.1474.2025.Art.5` | `decreto.1474.2025.art.5` | all lowercase |
| `decreto.1625.2016.libro.1.5.2.1` | `decreto.1625.2016.art.1.5.2.1` | use `.art.` prefix, not `.libro.` for DUR sub-units |
| `concepto.dian.100208192` | `concepto.dian.100208192-202` | unified conceptos use `<NUM>-<SUFFIX>` |
| `ley.1819.2016` | `ley.1819.2016` (parent) **or** `ley.1819.2016.art.7` (article) | parent vs article are distinct ids |

---

## 4. Per-phase population requirements

For each phase below, the table specifies:

- **Source URL** — where to fetch the text
- **Canonical id shape** — per the §5 grammar
- **Scraper status** — whether the existing scraper handles it, needs extension, or is missing
- **YAML batches affected** — which slices unblock when the phase is populated
- **Expected norm count** — the smoke-test pass threshold
- **Ingestion deliverable** — what the expert must add to `parsed_articles.jsonl`

### 4.1 Phase E — Decretos reglamentarios (~980 norms)

#### E1a–E1f — DUR 1625/2016 Libro 1 (renta)

| Field | Value |
|---|---|
| Source | `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm` (master) + per-libro segments |
| Canonical id shape | `decreto.1625.2016.art.<dotted-decimal>` where the decimal sequence represents libro.parte.titulo.article (e.g. `decreto.1625.2016.art.1.5.2.1`) |
| Scraper status | ✅ `dian_normograma.py` already resolves `decreto.<NUM>.<YEAR>.*` URLs. Article-level slicing not built — relies on Gemini/DeepSeek to find the article in the full DUR page, OR the parsed_articles row to carry the article body verbatim. |
| YAML batches | E1a (sub-libros 1.1+1.2), E1b (1.3+1.4), E1c (1.5), E1d (1.6), E1e (1.7), E1f (1.8+) |
| Expected norms | ~500 spread across sub-libros |
| Ingestion deliverable | One `parsed_articles.jsonl` row per article of DUR 1625/2016 Libro 1, `norm_id` set per `decreto.1625.2016.art.<dotted-decimal>` format and `body` containing the verbatim article text. |

#### E2a–E2c — DUR 1625/2016 Libro 2 (IVA + retefuente)

| Field | Value |
|---|---|
| Source | Same as E1 |
| Canonical id shape | `decreto.1625.2016.art.<dotted-decimal>` (libro 2 pattern, e.g. `decreto.1625.2016.art.2.1.1.5`) |
| Scraper status | ✅ same as E1 |
| YAML batches | E2a (sub-libros 2.1+2.2), E2b (2.3+2.4), E2c (2.5+) |
| Expected norms | ~280 |
| Ingestion deliverable | One row per article of DUR 1625/2016 Libro 2. |

#### E3a–E3b — DUR 1625/2016 Libro 3 (procedimiento + sanciones)

| Field | Value |
|---|---|
| Source | Same as E1 |
| Canonical id shape | `decreto.1625.2016.art.<dotted-decimal>` (libro 3 pattern, e.g. `decreto.1625.2016.art.3.1.2.8`) |
| Scraper status | ✅ same as E1 |
| YAML batches | E3a, E3b |
| Expected norms | ~200 |
| Ingestion deliverable | One row per article of DUR 1625/2016 Libro 3. |

#### E4 — Decreto 1474/2025 + autos relacionados

| Field | Value |
|---|---|
| Source | DIAN normograma (`decreto_1474_2025.htm`) + Consejo de Estado (autos C-082/2026, C-084/2026) |
| Canonical id shape | `decreto.1474.2025.art.<N>`, `auto.ce.082.2026.04.15`, `auto.ce.084.2026.MM.DD` (date required) |
| Scraper status | ⚠️ DIAN normograma covers `decreto.*`. **Consejo de Estado scraper has no resolver for `auto.ce.*` IDs** — see §7 gap #1. |
| YAML batches | E4 |
| Expected norms | 4 (acid test for IE state) |
| Ingestion deliverable | (a) parsed text of Decreto 1474/2025 articles, AND (b) for the autos: either implement the CE scraper's `_resolve_url` for `auto.ce.<NUM>.<YEAR>` shape, or fixture the auto text directly in `tests/fixtures/scrapers/consejo_estado/autos/`. |

#### E5 — Decretos legislativos COVID + emergencia tributaria

| Field | Value |
|---|---|
| Source | DIAN normograma `decreto_legislativo_<NUM>_<YEAR>.htm` |
| Canonical id shape | `decreto.<NUM>.<YEAR>.art.<X>` (decretos legislativos use ordinary decreto shape; "legislativo" character is in body, not id) |
| Scraper status | ⚠️ DIAN scraper's pattern is `decreto_<NUM>_<YEAR>.htm` — needs an explicit case for decretos legislativos to map to `decreto_legislativo_<NUM>_<YEAR>.htm`. See §7 gap #3. |
| YAML batches | E5 |
| Expected norms | ~30 |
| Ingestion deliverable | Scraper extension + parsed articles. |

#### E6a–E6c — DUR 1072/2015 (laboral)

| Field | Value |
|---|---|
| Source | `https://normograma.dian.gov.co/.../decreto_1072_2015.htm` (or MinTrabajo's site) |
| Canonical id shape | `decreto.1072.2015.art.<dotted-decimal>` (e.g. `decreto.1072.2015.art.1.2.5.10` for libro.parte.titulo.article) |
| Scraper status | ✅ DIAN handles the URL pattern. Deep article-level slicing not required for canonicalizer purposes — body verbatim is enough. |
| YAML batches | E6a (libro 1), E6b (libro 2), E6c (libro 3 — SST) |
| Expected norms | ~250 (shared with J8a–J8c) |
| Ingestion deliverable | One row per article of DUR 1072/2015. |

### 4.2 Phase F — Resoluciones DIAN clave (~140 norms)

#### F1 — UVT + calendario tributario (annual)

| Field | Value |
|---|---|
| Source | DIAN normograma resoluciones index |
| Canonical id shape | `res.dian.<NUM>.<YEAR>` (e.g. `res.dian.000022.2025`) |
| Scraper status | ✅ DIAN normograma handles `res.dian.*` |
| YAML batches | F1 |
| Expected norms | ~50 (one resolution per year × multiple resolution numbers, 2018–2026) |
| Ingestion deliverable | Parsed Resolución DIAN documents covering UVT-setting + plazos-de-presentación across 2018–2026. |

#### F2 — Factura electrónica + nómina electrónica + RADIAN

| Field | Value |
|---|---|
| Source | DIAN normograma (Resolución 165/2023, 2275/2023, 022/2025 RADIAN) |
| Canonical id shape | `res.dian.<NUM>.<YEAR>` |
| Scraper status | ✅ |
| YAML batches | F2 |
| Expected norms | ~30 |
| Ingestion deliverable | Parsed text of each resolución with all articles. |

#### F3 — Régimen Simple de Tributación (RST)

| Field | Value |
|---|---|
| Source | DIAN normograma |
| Canonical id shape | `res.dian.<NUM>.<YEAR>` |
| Scraper status | ✅ |
| YAML batches | F3 |
| Expected norms | ~20 |
| Ingestion deliverable | Parsed RST resoluciones. |

#### F4 — Cambiario + RUT + obligados (información exógena, RPA, etc.)

| Field | Value |
|---|---|
| Source | DIAN normograma |
| Canonical id shape | `res.dian.<NUM>.<YEAR>` |
| Scraper status | ✅ |
| YAML batches | F4 |
| Expected norms | ~40 |
| Ingestion deliverable | Parsed resoluciones for RUT, exógena annual resolutions, RPA. |

### 4.3 Phase G — Conceptos DIAN unificados (~390 norms)

| Field | Value |
|---|---|
| Source | DIAN normograma `concepto_dian_<NUM>.htm` (long PDF/HTML each) |
| Canonical id shape | `concepto.dian.<NUM>` for the parent doc; `concepto.dian.<NUM>.num.<X>` for sub-numerals |
| Scraper status | ✅ DIAN handles `concepto.dian.*` |
| YAML batches | G1 (IVA), G2 (renta), G3 (retención), G4 (procedimiento), G5 (régimen simple), G6 (Concepto 100208192-202 — already covered as acid test) |
| Expected norms | ~390 total across the 5 unified conceptos |
| Ingestion deliverable | Parse each unified concepto into per-numeral entries. **Concepto Unificado de Renta alone has 100+ numerales.** Each numeral becomes a row with `norm_id = concepto.dian.<NUM>.num.<X>` and `body` = numeral text. |

### 4.4 Phase H — Conceptos DIAN individuales + Oficios (long tail, ~430 norms)

Same canonical shape as G. Two issues compound:

1. The current YAML uses regex patterns that match too broadly against the
   corpus (we observed 5,608 false matches). Tightening the regex is part of
   the YAML hygiene pass that pairs with this ingestion work.
2. The corpus needs the actual concepto/oficio entries with canonical norm_ids.

| Field | Value |
|---|---|
| Source | DIAN normograma + DIAN oficios index |
| Canonical id shape | `concepto.dian.<NUM>` (individual), `oficio.dian.<NUM>.<YEAR>` (oficio) |
| Scraper status | ⚠️ DIAN partly handles. **`oficio.dian.*` needs a DIAN-scraper resolver case** — see §7 gap #2. |
| YAML batches | H1 (régimen simple), H2 (retención), H3a/b (renta), H4a/b (IVA), H5 (procedimiento), H6 (oficios) |
| Expected norms | ~430 |
| Ingestion deliverable | (a) Scraper extension for `oficio.dian.*`, (b) parsed individual conceptos and oficios in corpus, (c) regex tightening pass on `H*` batches in `batches.yaml`. |

### 4.5 Phase I — Jurisprudencia (~70 norms)

#### I1 — Sentencias CC sobre reformas tributarias

| Field | Value |
|---|---|
| Source | `https://www.corteconstitucional.gov.co/relatoria/<YEAR>/<TYPE>-<NUM>-<YY>.htm` |
| Canonical id shape | `sent.cc.<TYPE>-<NUM>.<YEAR>` (TYPE uppercase: C, T, SU, A) |
| Scraper status | ✅ |
| YAML batches | I1 (5 acid sentencias: C-481/2019, C-079/2026, C-384/2023, C-101/2025, C-540/2023) |
| Expected norms | 5 (already in `explicit_list`) |
| Ingestion deliverable | None — works today. |

#### I2 — Sentencias CC sobre principios constitucionales (Art. 363, Art. 338)

| Field | Value |
|---|---|
| Source | Same as I1 |
| Canonical id shape | `sent.cc.<TYPE>-<NUM>.<YEAR>` |
| Scraper status | ✅ |
| YAML batches | I2 |
| Expected norms | ~15 via prefix/regex |
| Ingestion deliverable | Parsed sentencias added to corpus. |

#### I3 — Sentencias CE de unificación (Sección Cuarta) — DT validation

| Field | Value |
|---|---|
| Source | `https://www.consejodeestado.gov.co/...` |
| Canonical id shape | `sent.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>` (e.g. `sent.ce.28920.2025.07.03`) |
| Scraper status | ⚠️ CE scraper resolves search URLs. Real article-level resolution may need work. |
| YAML batches | I3 |
| Expected norms | ~30 |
| Ingestion deliverable | Parsed sentencias + possible CE scraper hardening. |

#### I4 — Autos CE de suspensión provisional

| Field | Value |
|---|---|
| Source | Consejo de Estado |
| Canonical id shape | `auto.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>` (e.g. `auto.ce.082.2026.04.15`) |
| Scraper status | ❌ **CE scraper's `_resolve_url` for autos is incomplete** — see §7 gap #1. |
| YAML batches | I4 |
| Expected norms | ~20 |
| Ingestion deliverable | Scraper extension OR fixture-only path + parsed autos. |

### 4.6 Phase J — Régimen laboral (~430 norms)

#### J1–J4 — CST (Código Sustantivo del Trabajo)

| Field | Value |
|---|---|
| Source | `https://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo.html` (paginated similar to ET) |
| Canonical id shape | `cst.art.<N>` (e.g. `cst.art.22`, `cst.art.158`) |
| Scraper status | ❌ **No scraper exists for CST.** Senado scraper handles `et.art.*` and `ley.*` but not `cst.art.*`. See §7 gap #4. |
| YAML batches | J1 (contratos, Arts. 22–50), J2 (prestaciones sociales, 51–101), J3 (jornada, 158–200), J4 (conflictos colectivos, 416+) |
| Expected norms | ~170 |
| Ingestion deliverable | Either (a) parse CST into corpus + extend Senado scraper to resolve `cst.art.<N>` → segment URL, or (b) add CST text directly to corpus as parsed_articles entries per article (no live-fetch). |

#### J5–J7 — Ley 100/1993 + reformas + parafiscales

| Field | Value |
|---|---|
| Source | DIAN normograma (`ley_100_1993.htm`, `ley_2381_2024.htm`, `ley_789_2002.htm`, etc.) |
| Canonical id shape | `ley.<NUM>.<YEAR>.art.<X>` |
| Scraper status | ✅ DIAN already handles `ley.*` URL pattern (fix shipped 2026-04-27) |
| YAML batches | J5 (pensional + Ley 2381/2024), J6 (salud), J7 (parafiscales + licencias) |
| Expected norms | ~80 |
| Ingestion deliverable | Parsed articles for each ley. Should work end-to-end once corpus rows exist. |

#### J8a–J8c — DUR 1072/2015 laboral (relevante)

Same as E6 — needs DUR 1072 parsed into corpus. Phases E6 and J8 share the
same parsed rows; ingestion only does it once.

### 4.7 Phase K — Cambiario + comercial + societario (~150 norms)

#### K1 — Resolución Externa 1/2018 JDBR

| Field | Value |
|---|---|
| Source | Banco de la República |
| Canonical id shape | `res.banrep.<NUM>.<YEAR>.art.<X>` where article number is as printed (e.g. `res.banrep.1.2018.art.5`); sub-paragraphs use `.par.<P>` |
| Scraper status | ❌ **No scraper exists for BanRep.** See §7 gap #5. |
| YAML batches | K1 |
| Expected norms | ~25 |
| Ingestion deliverable | Implement scraper OR fixture parsed text. |

#### K2 — DCIN-83 (Manual Cambiario, BanRep)

| Field | Value |
|---|---|
| Source | BanRep |
| Canonical id shape | `dcin.83.cap.<C>.num.<N>` |
| Scraper status | ❌ See §7 gap #5. |
| YAML batches | K2 |
| Expected norms | ~40 |
| Ingestion deliverable | Same as K1 — likely fixture-only is the pragmatic path. |

#### K3 — Código de Comercio (sociedades)

| Field | Value |
|---|---|
| Source | Senado-style URL pattern |
| Canonical id shape | `cco.art.<N>` |
| Scraper status | ❌ **None — would extend Senado scraper similar to CST.** See §7 gap #4. |
| YAML batches | K3 |
| Expected norms | ~60 |
| Ingestion deliverable | Same path as CST: scraper extension + parsed articles. |

#### K4 — Ley 222/1995 + Ley 1258/2008 (S.A.S.)

| Field | Value |
|---|---|
| Source | DIAN/Senado ley pages |
| Canonical id shape | `ley.222.1995.art.<X>`, `ley.1258.2008.art.<X>` |
| Scraper status | ✅ DIAN `ley.*` resolver works today |
| YAML batches | K4 |
| Expected norms | ~25 |
| Ingestion deliverable | Parsed articles only. |

---

## 5. Canonical norm-id grammar — quick reference

The single source of truth is `docs/re-engineer/fixplan_v3.md` §0.5. Highlights
for the families above:

| Family | Canonical pattern | Example |
|---|---|---|
| ET article | `et.art.<N>` | `et.art.555-2` |
| ET sub-unit | `et.art.<N>.par.<P>` / `.num.<M>` / `.inciso.<I>` / `.lit.<L>` | `et.art.555-2.par.4` |
| Ley (parent) | `ley.<NUM>.<YEAR>` | `ley.1819.2016` |
| Ley (article) | `ley.<NUM>.<YEAR>.art.<X>` | `ley.1819.2016.art.7` |
| Ley sub-unit | `ley.<NUM>.<YEAR>.art.<X>.par.<P>` etc. | `ley.2277.2022.art.8.par.1` |
| Decreto | `decreto.<NUM>.<YEAR>` / `decreto.<NUM>.<YEAR>.art.<X>` | `decreto.1474.2025.art.5` |
| DUR sub-unit | `decreto.<NUM>.<YEAR>.art.<dotted-decimal>` | `decreto.1625.2016.art.1.5.2.1` |
| Resolución DIAN | `res.dian.<NUM>.<YEAR>` (sometimes zero-padded; check existing) | `res.dian.000022.2025` |
| Resolución BanRep | `res.banrep.<NUM>.<YEAR>` | `res.banrep.1.2018` |
| Concepto DIAN | `concepto.dian.<NUM>` (hyphenated for unified) | `concepto.dian.100208192-202` |
| Concepto sub-numeral | `concepto.dian.<NUM>.num.<X>` | `concepto.dian.100208192-202.num.4` |
| Oficio DIAN | `oficio.dian.<NUM>.<YEAR>` | `oficio.dian.018424.2024` |
| Sentencia CC | `sent.cc.<TYPE>-<NUM>.<YEAR>` (TYPE uppercase: C, T, SU, A) | `sent.cc.C-481.2019` |
| Sentencia CE | `sent.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>` | `sent.ce.28920.2025.07.03` |
| Auto CE | `auto.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>` (date in YYYY.MM.DD form, required) | `auto.ce.082.2026.04.15` |
| CST | `cst.art.<N>` | `cst.art.158` |
| Código de Comercio | `cco.art.<N>` | `cco.art.98` |
| DCIN | `dcin.<NUM>.cap.<C>.num.<N>` | `dcin.83.cap.5.num.3` |

**Round-trip rule.** Every id added to the corpus must round-trip through
`src/lia_graph/canon.py::canonicalize` returning the same string. See §3.2.

---

## 6. Required deliverables from the ingestion expert

For the canonicalizer to extend coverage from 754 → ~3,400 norms, the
ingestion expert ships:

### 6.1 Append rows to `artifacts/parsed_articles.jsonl`

One row per norm, schema:

```json
{
  "norm_id": "<canonical-id>",
  "norm_type": "<articulo_et|ley_articulo|decreto_articulo|res_dian|concepto_dian|oficio_dian|sentencia_cc|sentencia_ce|auto_ce|cst_articulo|cco_articulo|res_banrep|dcin_numeral>",
  "article_key": "<short label, e.g. 'Art. 555-2 ET'>",
  "body": "<full text of the article — verbatim from the primary source>",
  "source_url": "<the gov.co URL the body came from>",
  "fecha_emision": "<YYYY-MM-DD if known, else null>",
  "emisor": "<who issued: Congreso, DIAN, CC, CE, BanRep, MinTrabajo, etc.>",
  "tema": "<thematic tag for retrieval — optional>"
}
```

The `norm_id` field is the **only** field the canonicalizer's
`build_extraction_input_set.py` reads to deduplicate and emit the input set.
Other fields support the chat backend's retrieval but do not affect the
canonicalizer.

**Schema validation.** Before committing, run:

```bash
PYTHONPATH=src:. uv run python -c "
import json
from lia_graph.canon import canonicalize
with open('artifacts/parsed_articles.jsonl') as f:
    for i, line in enumerate(f, 1):
        row = json.loads(line)
        nid = row['norm_id']
        canon = canonicalize(nid)
        assert canon == nid, f'row {i}: {nid!r} → {canon!r}'
print('OK')
"
```

### 6.2 Re-run the input-set builder

```bash
PYTHONPATH=src:. uv run python scripts/canonicalizer/build_extraction_input_set.py
```

Output: `evals/vigencia_extraction_v1/input_set.jsonl` regenerated.

### 6.3 Smoke-verify each phase resolves cleanly

For each phase added, run the slice-size check:

```bash
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path
for bid in ['E1a', 'E1b', 'E1c', 'E1d', 'E1e', 'E1f',
            'E2a', 'E2b', 'E2c', 'E3a', 'E3b',
            'E4', 'E5', 'E6a', 'E6b', 'E6c',
            'F1', 'F2', 'F3', 'F4',
            'G1', 'G2', 'G3', 'G4', 'G5', 'G6',
            'H1', 'H2', 'H3a', 'H3b', 'H4a', 'H4b', 'H5', 'H6',
            'I1', 'I2', 'I3', 'I4',
            'J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8a', 'J8b', 'J8c',
            'K1', 'K2', 'K3', 'K4']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    print(f'  {bid}: {len(norms)} norms')
"
```

**Acceptance.** Every batch above should report a non-zero count matching
roughly the "Expected" row in §4 (within ±20%).

---

## 7. Scraper coverage gaps (blockers)

Five scraper gaps block phases regardless of corpus parsing effort. Each is
listed with the path to fix and the fixture-only fallback if implementation is
deferred.

### Gap #1 — `auto.ce.<RADICADO>.<DATE>` (Consejo de Estado autos)

| Field | Value |
|---|---|
| Affects | E4 (acid test, IE state), I4 |
| File to edit | `src/lia_graph/scrapers/consejo_estado.py::_resolve_url` |
| Fix | Add a regex case for `auto.ce.<NUM>.<YEAR>` that maps to the CE search-by-radicado RPC URL. |
| Fixture fallback | Add auto text directly to `tests/fixtures/scrapers/consejo_estado/autos/<radicado>.html` and never live-fetch. |

### Gap #2 — `oficio.dian.<NUM>.<YEAR>` (DIAN oficios)

| Field | Value |
|---|---|
| Affects | H6 |
| File to edit | `src/lia_graph/scrapers/dian_normograma.py::_resolve_url` |
| Fix | Add a case mapping `oficio.dian.<NUM>.<YEAR>` to `oficio_dian_<NUM>_<YEAR>.htm` (or the equivalent search index URL). |
| Fixture fallback | Same pattern as Gap #1. |

### Gap #3 — Decretos legislativos URL filename (canonical id stays plain)

| Field | Value |
|---|---|
| Affects | E5 |
| File to edit | `src/lia_graph/scrapers/dian_normograma.py::_resolve_url` |
| Fix | The canonical id for a decreto legislativo is plain `decreto.<NUM>.<YEAR>` (no `.legislativo` segment). The DIAN scraper currently maps `decreto.<NUM>.<YEAR>` → `decreto_<NUM>_<YEAR>.htm`, but for decretos issued under emergencia económica the URL filename is `decreto_legislativo_<NUM>_<YEAR>.htm`. Add an explicit case that detects whether the source decree is a "decreto legislativo" (via metadata or a known number list) and rewrites the URL filename accordingly — but the canonical norm_id is unchanged. The "legislativo" character lives in the article body and source-URL metadata, not the id. |
| Fixture fallback | Drop in `tests/fixtures/scrapers/dian/decreto_legislativo_<NUM>_<YEAR>.htm` (URL filename keeps `legislativo`); the `parsed_articles.jsonl` row keeps the canonical id `decreto.<NUM>.<YEAR>.art.<X>`. |

### Gap #4 — `cst.art.<N>` and `cco.art.<N>` (Senado-hosted codes)

| Field | Value |
|---|---|
| Affects | J1–J4 (~170 norms), K3 (~60 norms) |
| File to edit | New scraper `src/lia_graph/scrapers/senado_codigos.py`, OR extend existing `secretaria_senado.py` |
| Fix | Implement URL pattern + per-article slicing for the Senado-hosted CST and Código de Comercio HTML pages. |
| Fixture fallback | Hand-curate parsed_articles entries directly without a live scraper. Pragmatic for codes that change infrequently. |

### Gap #5 — BanRep (`res.banrep.*`, `dcin.*`)

| Field | Value |
|---|---|
| Affects | K1 (~25 norms), K2 (~40 norms) |
| File to edit | New scraper `src/lia_graph/scrapers/banrep.py` |
| Fix | Implement a BanRep scraper covering Resoluciones Externas JDBR and the DCIN-83 manual. |
| Fixture fallback | **Recommended.** BanRep's site is sparsely structured; fixture-only ingestion is the cheapest path, with periodic re-fetch if regulation changes. |

---

## 8. Suggested priority order

If the ingestion expert can't do everything at once, the ordering that
maximizes value-per-effort:

1. **J1–J4 CST + J5/J6 Ley 100 + J7 parafiscales.** Labor regime is
   first-class to Lia per the operator's product-scope memory; ~250 norms
   unlock with one scraper extension (CST) and parsed articles for the leyes.
2. **G1–G6 Conceptos unificados DIAN.** Most-cited doctrine accountants reach
   for; ~390 norms; DIAN scraper already works for the URL family — only
   corpus parsing of the unified conceptos needed (split by numeral).
3. **F1–F4 Resoluciones DIAN.** UVT, calendario, factura electrónica, RST,
   RUT; ~140 norms; smallest add per phase, scraper works today.
4. **E1–E3 DUR 1625.** Largest single artifact (~980 norms); highest absolute
   volume; scraper works today; parsing the DUR into per-article entries is
   non-trivial but mechanical.
5. **K1–K4 Cambiario + Código de Comercio.** ~150 norms; needs new scrapers
   for BanRep and CCo OR fixture-only ingestion (recommended for BanRep).
6. **H1–H6 Conceptos individuales + oficios.** ~430 norms; needs
   `oficio.dian.*` scraper case + tighter regex on H batches.
7. **E4, E5, E6, I2, I3, I4.** Smaller specialized phases; mix of scraper
   work + corpus parsing.

This ordering also has the property that the first three priority blocks
(J + G + F) are the highest-utility content for end users (contadores asking
Lia about labor obligations, DIAN doctrine, and current resoluciones), so even
a partial ingestion delivers product value.

---

## 9. Definition of done

After the ingestion expert ships per §6 and §7:

| Criterion | Threshold | How to measure |
|---|---|---|
| Slice resolution | All 50+ batch IDs in the §6.3 smoke check report ≥80% of expected count | `extract_vigencia.py` slice-size script |
| Round-trip integrity | 0 rejections from `ingest_vigencia_veredictos.py` due to malformed `norm_id` | Writer log, `errors_invalid_id` count |
| Campaign success rate | DeepSeek-v4-pro processes E–K at ≥85% verdict-success rate (matching Phase D performance) | `evals/canonicalizer_run_v1/campaign_log.md` |
| Verified vigencia rows | Postgres `norm_vigencia_history` count climbs from 754 → ≥3,000 | `SELECT COUNT(DISTINCT norm_id) FROM norm_vigencia_history` |
| Falkor structural edges | ≥3,000 new edges added (proportional to norm count; 642 from 754 baseline → ~3,500 total) | Falkor edge count |
| Phase log | `campaign_log.md` shows green verdict (≥80%) on every phase A through K | manual review |

When all six pass, the canonicalizer is "done for v1 corpus" and the next
gate is staging promotion.

---

## 10. Document layout for ingestion experts

This document (`corpus_population_plan.md`) is the **master plan** — it stays
as the index. For working notes and to divide work across multiple experts (or
sessions), follow a one-doc-per-source convention.

The right granularity is **roughly 12 .md briefs**, sized so each is
ingestible in one LLM context window (~3,000–5,000 words / ~15–25 KB) and
ownable by one person at a time.

### 10.1 Recommended file layout

Create a sibling directory `docs/re-engineer/corpus_population/` and place
one brief per source family inside it:

```
docs/re-engineer/
├── corpus_population_plan.md                 ← THIS doc (master index)
├── state_corpus_population.md                ← live progress tracker
└── corpus_population/
    ├── 01_cst.md                             ← Phase J1-J4 (CST articles)
    ├── 02_dur_1625_renta.md                  ← Phase E1a-f (DUR Libro 1)
    ├── 03_dur_1625_iva_retefuente.md         ← Phase E2a-c (DUR Libro 2)
    ├── 04_dur_1625_procedimiento.md          ← Phase E3a-b (DUR Libro 3)
    ├── 05_dur_1072_laboral.md                ← Phase E6a-c + J8a-c
    ├── 06_decretos_legislativos_covid.md     ← Phase E5
    ├── 07_resoluciones_dian.md               ← Phase F1-F4
    ├── 08_conceptos_dian_unificados.md       ← Phase G1-G6
    ├── 09_conceptos_dian_individuales.md     ← Phase H1-H6
    ├── 10_jurisprudencia_cc_ce.md            ← Phase I1-I4
    ├── 11_pensional_salud_parafiscales.md    ← Phase J5-J7
    └── 12_cambiario_societario.md            ← Phase K1-K4
```

12 source briefs + 1 master + 1 state file = **14 documents total**, each
scoped tightly enough that two experts can work in parallel without stepping
on each other. The numeric prefix preserves priority order from §8.

### 10.2 What each brief should contain

Use this skeleton (~1–2 pages each):

```markdown
# <NN>. <Source family>

**Master:** ../corpus_population_plan.md §4.<phase>
**Owner:** <name | unassigned>
**Status:** 🟡 not started | 🔵 in progress | ✅ ingested
**Target norm count:** ~<N>
**Phase batches affected:** <e.g. J1, J2, J3, J4>

## What

One paragraph describing the source — what it is, why it matters, what the
canonicalizer needs from it.

## Source URLs (primary)

| URL | What's there |
|---|---|
| https://… | full text |

## Canonical norm_id shape

`<family>.art.<N>` (or whatever — copy from §5 of the master)

Round-trip via `lia_graph.canon.canonicalize(...)` BEFORE ingesting.

## Parsing strategy

1. Fetch source.
2. Split per article (anchor / regex / heading).
3. For each, emit a `parsed_articles.jsonl` row with the §6.1 schema.

## Edge cases observed

- Sub-units like `art.555-2` numbered as separate articles vs nested.
- Articles split across two HTML pages (DUR uses `pr001`-style segments).
- Modificación / derogación tags inside the article body — keep as raw text;
  the canonicalizer's vigencia harness extracts them via Gemini/DeepSeek, not
  via the parser.

## Smoke verification

After ingest, run the §6.3 slice-size check restricted to this brief's
batches. Expected: ≥80% of `Target norm count`.

## Dependencies on other briefs

- (e.g. `09_conceptos_dian_individuales.md` depends on
  `08_conceptos_dian_unificados.md` because the unified conceptos reference
  numerals that inherit ids from the individual ones)
```

### 10.3 Why this granularity (not bigger, not smaller)

- **Smaller** (one .md per phase batch — e.g. one per E1a, E1b, E1c…): too
  granular. The same source (DUR 1625) covers six batches; splitting the brief
  across them duplicates context and makes it hard to capture family-wide
  invariants like "Libro 1 sub-libros 1.1 through 1.8 share one URL pattern."
- **Bigger** (one .md per phase): too coarse. Phase E covers DUR 1625 + DUR
  1072 + COVID legislativos — three different sources with different scrapers,
  URL patterns, and parsing strategies. Mixing them makes the brief unwieldy
  and prevents two experts from owning Phase E in parallel.
- **One per source family** (this layout): the brief scopes to one scraper,
  one URL pattern, one canonical id-shape, one parsing approach. An expert
  claims a brief, completes it end-to-end, marks ✅. Briefs that share a
  scraper extension (e.g. CST + Código de Comercio both want a Senado-style
  scraper) coordinate via the state file's "blocked-by" notes.

### 10.4 The state file (`state_corpus_population.md`)

Mirror the existing `state_canonicalizer_runv1.md` shape:

- **§1** how to use this file
- **§2** fresh-LLM preconditions (what an incoming agent needs to read first)
- **§3** current global state (briefs done / in flight / blocked)
- **§4** per-brief table with status + owner + last update + blockers
- **§5** recovery playbooks (corpus-row corruption, scraper drift, etc.)
- **§10** append-only run log

Update §4 whenever a brief advances. The master plan (this doc) stays mostly
static — only edit it when the canonicalizer's expected scope itself changes.

### 10.5 Naming + commit conventions

- Filename: `NN_short-source-name.md` (lowercase, underscores).
- Commit one brief per commit when shipping the corpus rows for it
  (`corpus(cst): ingest 174 CST articles per brief 01`). Easy to revert if the
  parsing has issues without losing other briefs' work.
- Each brief lists its `Target norm count` up front so the smoke test in §6.3
  has a pass/fail threshold.

---

## 11. Estimated compute cost

DeepSeek-v4-pro pricing during the May 5 discount window (75% off):

| Item | Value |
|---|---|
| Input rate | $0.11 effective per 1M tokens |
| Output rate | $0.22 effective per 1M tokens |
| Per-call avg | ~12K input + ~2K output tokens |
| Cost per call | ~$0.0018 |
| Remaining norms | ~2,650 |
| Calls needed (1× each) | ~2,650 |
| **Total API spend** | **~$5–6** |

**Wall time** at 6 concurrent workers + 80 RPM project throttle: **~10 hours**
end-to-end for the full Phase E–K campaign.

If the run fails partway and needs replays, budget 2× ($10–12) and 20 hours.

---

## 12. Out of scope

These are **not** what we're asking the corpus expert to do:

- Don't rewrite the canonicalizer scripts. They work.
- Don't change `config/canonicalizer_run_v1/batches.yaml` slice definitions
  unless the expected scope is wrong (it isn't — the batches reflect the
  canonicalizer doc's intended phases). The H-batch regex tightening called
  out in §4.4 is the one allowed exception.
- Don't change the prompt or the `Vigencia` schema. They've been hardened
  across A1–A6 + B1–B10 + C–D and are stable.
- Don't ingest into Postgres directly. The pipeline runs:
  `parsed_articles.jsonl` → `build_extraction_input_set.py` →
  `extract_vigencia.py` (with Gemini/DeepSeek) →
  `ingest_vigencia_veredictos.py` → Postgres `norm_vigencia_history`.
  Skipping steps breaks the audit trail.

---

## Appendix A — Verification matrix

Consolidated pass/fail thresholds for every phase. Use this as the single
acceptance checklist when reviewing the ingestion expert's deliverable.

| Batch ID | Filter type | Min slice size | Notes |
|---|---|---:|---|
| E1a | prefix | 50 | DUR 1625 sub-libros 1.1+1.2 |
| E1b | prefix | 50 | DUR 1625 sub-libros 1.3+1.4 |
| E1c | prefix | 80 | DUR 1625 sub-libro 1.5 |
| E1d | prefix | 80 | DUR 1625 sub-libro 1.6 |
| E1e | prefix | 80 | DUR 1625 sub-libro 1.7 |
| E1f | prefix | 60 | DUR 1625 sub-libro 1.8+ |
| E2a | prefix | 60 | DUR 1625 Libro 2 sub-libros 2.1+2.2 |
| E2b | prefix | 80 | DUR 1625 Libro 2 sub-libros 2.3+2.4 |
| E2c | prefix | 60 | DUR 1625 Libro 2 sub-libro 2.5+ |
| E3a | prefix | 80 | DUR 1625 Libro 3 (procedimiento) |
| E3b | prefix | 60 | DUR 1625 Libro 3 (sanciones) |
| E4 | explicit_list | 4 | Decreto 1474/2025 + autos CE — acid test |
| E5 | regex | 20 | Decretos legislativos COVID |
| E6a | prefix | 60 | DUR 1072 Libro 1 |
| E6b | prefix | 80 | DUR 1072 Libro 2 |
| E6c | prefix | 80 | DUR 1072 Libro 3 (SST) |
| F1 | regex | 40 | Resoluciones UVT + calendario |
| F2 | regex | 25 | Resoluciones FE + nómina + RADIAN |
| F3 | regex | 15 | Resoluciones RST |
| F4 | regex | 30 | Resoluciones cambiario + RUT + obligados |
| G1 | prefix | 60 | Concepto Unificado IVA |
| G2 | prefix | 100 | Concepto Unificado Renta |
| G3 | prefix | 60 | Concepto Unificado Retención |
| G4 | prefix | 60 | Concepto Unificado Procedimiento |
| G5 | prefix | 60 | Concepto Unificado RST |
| G6 | explicit_list | 1 | Concepto 100208192-202 |
| H1–H6 | regex | 350 (combined) | Tighten regex first — see §4.4 |
| I1 | explicit_list | 5 | CC reformas — already passing |
| I2 | regex | 12 | CC principios constitucionales |
| I3 | regex | 25 | CE unificación |
| I4 | regex | 15 | CE autos suspensión — needs Gap #1 fixed |
| J1 | et_article_range-style | 25 | CST Arts. 22–50 |
| J2 | et_article_range-style | 40 | CST Arts. 51–101 |
| J3 | et_article_range-style | 35 | CST Arts. 158–200 |
| J4 | et_article_range-style | 60 | CST Arts. 416+ |
| J5 | regex | 30 | Pensional + Ley 2381/2024 |
| J6 | regex | 25 | Salud |
| J7 | regex | 20 | Parafiscales + licencias |
| J8a–J8c | prefix | 200 (combined) | DUR 1072 (shared with E6) |
| K1 | regex | 20 | Resolución Externa 1/2018 JDBR |
| K2 | regex | 30 | DCIN-83 |
| K3 | et_article_range-style | 50 | Código de Comercio sociedades |
| K4 | regex | 20 | Ley 222/1995 + Ley 1258/2008 |

The "Min slice size" column is set at ~80% of the §1.3 expected count (a
permissive threshold — slight under-population is acceptable as long as the
canonicalizer can run end-to-end on the slice).

---

## Appendix B — Risk register

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Ingestion expert emits non-canonical norm_ids and writer rejects veredictos at insert time | Medium | High (blocks campaign mid-run) | Run §6.1 round-trip validation before committing rows; add a pre-commit hook on `parsed_articles.jsonl` |
| R2 | DUR 1625 article-level parsing produces wrong libro/parte/titulo nesting | Medium | Medium (mis-classified ids slip through canonicalize because the grammar accepts them) | Cross-check a sample of 50 parsed articles against the source HTML manually before bulk ingest |
| R3 | Senado URL pattern for CST changes between now and ingest | Low | Medium (scraper extension breaks) | Use fixture-only path for CST initially; revisit live scraper later |
| R4 | BanRep page restructures; scraper rot | Medium | Low (fixture-only path is recommended anyway) | Document the as-of date on each fixtured BanRep entry |
| R5 | Concepto unificado numeral splitting is wrong (numerales bleed across) | Medium | Medium (Gemini/DeepSeek confused by mid-article context) | Validate numeral boundaries via a heuristic check: numeral text starts with `<NUM>.` heading |
| R6 | DeepSeek-v4-pro discount expires before run completes | Low | Low ($5 → $20 worst case) | Run within May 5 discount window; if missed, run anyway — full price still under $25 |
| R7 | Wall-time budget overruns due to RPM throttle | Medium | Low (campaign just takes longer) | Run overnight; pool maintainer recovers stalled workers automatically |
| R8 | YAML H-regex stays too broad and false-positive matches inflate the slice | High | High (campaign reports false success on H1–H6) | Tighten regex first as part of Phase H ingestion brief — non-negotiable gate |
| R9 | Ingestion expert ships in a non-incremental way and a single bad commit corrupts the whole `parsed_articles.jsonl` | Medium | High | Per §10.5, commit one brief per commit so reverts are surgical |
| R10 | Phase ordering inverted (e.g., H ingested before G) and unified conceptos' numerals collide with individual conceptos' ids | Low | Medium | Follow §8 priority order; G before H is enforced there |

---

*Document drafted 2026-04-28. Last verified 2026-04-28 03:00 AM Bogotá.*
*Author: claude-opus-4-7. Source-of-truth for what the canonicalizer needs*
*from the corpus to extend coverage from 754 → ~3,400 verified norms.*
