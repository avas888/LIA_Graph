# Corpus population plan — what the canonicalizer needs the ingestion expert to provide

> **Audience.** The corpus-ingestion expert (or the next session of one) who will
> add documents to `knowledge_base/` and re-run the parsed-articles build so
> that the canonicalizer's Phase E–K batches resolve to a non-empty norm slice.
>
> **Context.** As of 2026-04-28 03:00 AM Bogotá, the canonicalizer has verified
> vigencia for **754 unique norms** across Phases A (procedimiento), B (renta),
> C (IVA / retefuente / GMF), and D (reformas Ley). The remaining phases (E
> through K) consistently returned 0 successes during yesterday's autonomous
> campaign because the YAML's batch slices resolved to **0 matching norm_ids
> in the parsed corpus**. This is a corpus-coverage gap, not a canonicalizer
> bug — the harness, scrapers, and prompt are working.
>
> **Decision pending.** Two paths:
> (a) populate the corpus per this document so the canonicalizer can finish
>     Phases E–K, OR
> (b) mark the canonicalizer "done for what we have" (754 norms) and pivot
>     directly to staging promotion of those.
>
> This document supports decision (a). Decision (b) doesn't need it.

---

## 1. The gap, precisely

`scripts/canonicalizer/extract_vigencia.py --batch-id <X>` resolves a slice
by reading the corpus's deduplicated input set
(`evals/vigencia_extraction_v1/input_set.jsonl`, built by
`scripts/canonicalizer/build_extraction_input_set.py` from
`artifacts/parsed_articles.jsonl`) and applying the batch's `norm_filter`
from `config/canonicalizer_run_v1/batches.yaml`.

When we audit batch slice sizes against the current corpus:

| Phase | Audit result |
|---|---|
| A1–A4 | 136 norms (covered) |
| B1–B10 | 404 norms (covered) |
| C1–C4 | 112 norms (covered) |
| D1–D8c | 298 norms (covered after the `ley.*` URL-resolver fix shipped 2026-04-27) |
| **E1a–E6c** | **6 norms total** (E4 only — the IE acid test) — **EXPECTED ~500** |
| **F1–F4** | **2 norms** — **EXPECTED ~140** |
| **G1–G6** | **7 norms** (G6 only — the SP acid test) — **EXPECTED ~390** |
| **H1–H6** | (regex over-matches the corpus — slicing too broad; coverage actually missing) |
| **I1–I4** | **5 norms** (I1 only — sentencias CC reformas) — **EXPECTED ~70** |
| **J1–J8c** | **9 norms** (J5/J6/J7 only — pensional/salud/parafiscales acid tests) — **EXPECTED ~430** |
| **K1–K4** | **2 norms** (K4 only — Ley 222/Ley 1258 acid test) — **EXPECTED ~150** |

**Translation.** ~1,690 norms (~85% of the canonicalizer's intended scope)
are missing from the parsed corpus at the canonical id-shapes the YAML
expects.

The few non-zero E/F/G/I/J/K slices today come from *explicit_list* batch
entries (hand-curated acid-test fixtures). The bulk of each phase uses
*prefix* or *regex* filters that depend on the corpus actually containing
norm_ids in those shapes.

## 2. Reading the YAML's filter shapes

`config/canonicalizer_run_v1/batches.yaml` uses four filter types. To
populate a phase, the corpus's parsed_articles.jsonl needs norm_ids that
match the filter:

| Filter type | Example | Corpus must contain |
|---|---|---|
| `prefix` | `prefix: "decreto.1625.2016.libro.1.5."` | norm_ids starting with that prefix |
| `regex` | `pattern: "^decreto\\.1625\\.2016\\.libro\\.1\\.\\d+\\..+"` | norm_ids matching the regex |
| `et_article_range` | `from: 555, to: 580-2` | `et.art.555` through `et.art.580-2` (works today; ET fully populated) |
| `explicit_list` | `norm_ids: [...]` | exact ids (always works regardless of corpus shape) |

The grammar for each canonical norm_id is defined in
`docs/re-engineer/fixplan_v3.md` §0.5. The canonicalizer enforces it via
`src/lia_graph/canon.py::canonicalize`. Any norm_id added to the corpus
must round-trip through `canonicalize` cleanly — otherwise the
`ingest_vigencia_veredictos` writer rejects it (we hit this in production
yesterday with `sentencia.C-481.2019` → should have been
`sentencia.cc.c-481.2019`).

## 3. Per-phase population requirements

For each phase, the table below names:
- the **family** the corpus must cover
- the **canonical norm_id shape** (from the §0.5 grammar)
- the **representative source URL** (where to fetch the text)
- the **scraper that already handles it** (or a flag if a scraper is missing)
- the **YAML batches** that need it
- the **expected norm count** if fully populated

### Phase E — Decretos reglamentarios (~500 norms)

#### E1a-f — DUR 1625/2016 Libro 1 (renta)

| Field | Value |
|---|---|
| Source | `https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1625_2016.htm` (master URL) and per-libro segments |
| Canonical id shape | `decreto.1625.2016.libro.1.<L>.<art>` (where `L` is 1-9, `art` is the article id within the libro) |
| Scraper | DIAN normograma already handles `decreto.<NUM>.<YEAR>` prefix → working. The article-level slicing already exists for `et.*`; we'd need to extend or rely on Gemini to find the article in the full DUR page. |
| YAML batches | E1a (sub-libros 1.1+1.2), E1b (1.3+1.4), E1c (1.5), E1d (1.6), E1e (1.7), E1f (1.8+) |
| Expected norms | ~500 spread across sub-libros |
| **What ingestion needs to add to corpus** | Parsed articles of DUR 1625/2016 Libro 1, each with `norm_id` field set per the canonical shape above. Either (a) one row per article with `body` text, or (b) seed the input_set.jsonl with the canonical ids and let the canonicalizer's harness fetch text live via DIAN. |

#### E2a-c — DUR 1625/2016 Libro 2 (IVA + retefuente)

Same source. Canonical: `decreto.1625.2016.libro.2.<L>.<art>`. ~280 norms.

#### E3a-b — DUR 1625/2016 Libro 3 (procedimiento + sanciones)

Same source. Canonical: `decreto.1625.2016.libro.3.<L>.<art>`. ~200 norms.

#### E4 — Decreto 1474/2025 + autos relacionados

| Field | Value |
|---|---|
| Source | DIAN normograma + `https://www.consejodeestado.gov.co/` (autos C-082/2026, C-084/2026) |
| Canonical id shape | `decreto.1474.2025.art.<N>`, `auto.ce.082.2026`, `auto.ce.084.2026` |
| Scraper | DIAN normograma covers `decreto.*`. **Consejo de Estado scraper has no resolver for `auto.ce.*` IDs** — needs implementation. |
| YAML batches | E4 (4 norms — explicit list, present in YAML but scraper-blocked) |
| Expected | 4 norms (acid test for IE state) |
| **What ingestion needs** | Parsed text of Decreto 1474/2025 articles. For autos CE: either (a) implement the CE scraper's `_resolve_url` for `auto.ce.<NUM>.<YEAR>` shape, or (b) add the auto text directly to corpus as a primary-source fixture. |

#### E5 — Decretos legislativos COVID + emergencia tributaria

| Field | Value |
|---|---|
| Source | DIAN normograma `decreto_legislativo_NNN_2020.htm` and similar |
| Canonical id shape | `decreto.legislativo.<NUM>.<YEAR>.art.<X>` |
| Scraper | **DIAN scraper's pattern is `decreto_<NUM>_<YEAR>.htm`** — needs an explicit case for `decreto.legislativo.*` to map to `decreto_legislativo_<NUM>_<YEAR>.htm`. |
| YAML batches | E5 |
| Expected | ~30 norms |

#### E6a-c — DUR 1072/2015 (laboral)

| Field | Value |
|---|---|
| Source | `https://normograma.dian.gov.co/.../decreto_1072_2015.htm` (or MinTrabajo's site) |
| Canonical id shape | `decreto.1072.2015.libro.<L>.parte.<P>.titulo.<T>.art.<art>` |
| Scraper | DIAN handles the URL pattern; deep article-level slicing not required for canonicalizer purposes. |
| YAML batches | E6a (libro 1), E6b (libro 2), E6c (libro 3 — SST) |
| Expected | ~250 norms |

### Phase F — Resoluciones DIAN clave (~140 norms)

#### F1 — UVT + calendario tributario (per year)

| Field | Value |
|---|---|
| Source | DIAN normograma resoluciones index |
| Canonical id shape | `res.dian.<NUM>.<YEAR>` (e.g. `res.dian.000022.2025` for the 2025 UVT resolution) |
| Scraper | DIAN normograma handles `res.dian.*` already → working. |
| YAML batches | F1 |
| Expected | ~50 norms (one resolution per year × multiple resolution numbers) |
| **What ingestion needs** | Add parsed Resolución DIAN documents covering UVT-setting + plazos-de-presentación (2018–2026) to corpus. |

#### F2 — Factura + nómina electrónica

| Source URLs | Resolución 165/2023, 2275/2023, RADIAN |
| Canonical | `res.dian.<NUM>.<YEAR>` |
| Scraper | works |
| Expected | ~30 norms |

#### F3 — Régimen simple

Same shape. ~20 norms.

#### F4 — Cambiario + RUT + obligados

Same shape. ~40 norms.

### Phase G — Conceptos DIAN unificados (~390 norms)

| Field | Value |
|---|---|
| Source | DIAN normograma `concepto_dian_<NUM>.htm` |
| Canonical id shape | `concepto.dian.<NUM>` for the parent doc; `concepto.dian.<NUM>.num.<X>` for sub-numerals |
| Scraper | DIAN handles `concepto.dian.*` → working. |
| YAML batches | G1 (IVA), G2 (renta), G3 (retención), G4 (procedimiento), G5 (régimen simple), G6 (Concepto 100208192-202 — already covered) |
| Expected | ~390 norms total across the 5 unified conceptos |
| **What ingestion needs** | Parse the unified conceptos. Each is a long PDF/HTML; needs to be split into numerals so the canonicalizer can verify each numeral's vigencia. Concepto Unificado de Renta alone has 100+ numerales. |

### Phase H — Conceptos DIAN individuales + Oficios (long tail)

Same shape as G. The current YAML uses regex patterns that match too
broadly against the corpus (we observed 5,608 false matches earlier);
the regex needs tightening AND the corpus needs the actual
concepto/oficio entries with canonical norm_ids.

| Source | DIAN normograma + DIAN oficios index |
| Canonical | `concepto.dian.<NUM>`, `oficio.dian.<NUM>.<YEAR>` |
| Scraper | DIAN partly handles; **`oficio.dian.*` needs a DIAN-scraper resolver case** |
| YAML batches | H1 (régimen simple), H2 (retención), H3a/b (renta — 2 sub-batches), H4a/b (IVA), H5 (procedimiento), H6 (oficios DIAN) |
| Expected | ~430 norms |

### Phase I — Jurisprudencia (~70 norms)

#### I1 — Sentencias CC sobre reformas tributarias

| Field | Value |
|---|---|
| Source | `https://www.corteconstitucional.gov.co/relatoria/<YEAR>/<TYPE>-<NUM>-<YY>.htm` |
| Canonical id shape | `sentencia.cc.c-<NUM>.<YEAR>` (lowercase `c`, with `cc` court prefix) |
| Scraper | Corte Constitucional scraper handles this URL pattern. |
| YAML batches | I1 (key reform sentencias: C-481/2019, C-079/2026, C-384/2023, C-101/2025, C-540/2023) |
| Expected | 5 norms (already in explicit_list) |
| **Status** | Works today — 5 norms resolve. |

#### I2 — Sentencias CC sobre principios constitucionales (Art. 363, Art. 338)

Same shape. ~15 norms via prefix/regex. **Corpus needs them added.**

#### I3 — Sentencias CE de unificación (Sección Cuarta) — DT validation

| Source | `https://www.consejodeestado.gov.co/...` |
| Canonical | `sentencia.ce.<SECCION>.<RADICADO>` (e.g. `sentencia.ce.suj.4.002.2022`) |
| Scraper | CE scraper resolves search URLs. Real article-level resolution may need work. |
| YAML batches | I3 |
| Expected | ~30 norms |

#### I4 — Autos CE de suspensión provisional

| Canonical | `auto.ce.<RADICADO>.<DATE>` |
| Scraper | **CE scraper's `_resolve_url` for autos is incomplete** — needs the search-by-radicado RPC or a hand-curated id→URL map. |
| YAML batches | I4 |
| Expected | ~20 norms |

### Phase J — Régimen laboral (~430 norms)

#### J1-J4 — CST (Código Sustantivo del Trabajo)

| Field | Value |
|---|---|
| Source | `https://www.secretariasenado.gov.co/senado/basedoc/codigo_sustantivo_trabajo.html` (paginated similar to ET) |
| Canonical id shape | `cst.art.<N>` (e.g. `cst.art.22`, `cst.art.158`) |
| Scraper | **No scraper exists for CST yet.** The Senado scraper handles `et.art.*` and `ley.*` but not `cst.art.*`. Either extend Senado scraper with a CST URL pattern + per-article slicing, or add CST as a new scraper file. |
| YAML batches | J1 (contratos, Arts. 22-50), J2 (prestaciones sociales, 51-101), J3 (jornada, 158-200), J4 (conflictos colectivos, 416+) |
| Expected | ~170 norms |
| **What ingestion needs** | Either (a) parse CST into corpus + extend Senado scraper to resolve `cst.art.<N>` → segment URL, or (b) add CST text directly to corpus as a parsed_articles.jsonl entry per article. |

#### J5-J7 — Ley 100/1993 + reformas + parafiscales

| Field | Value |
|---|---|
| Source | DIAN normograma `ley_100_1993.htm`, `ley_2381_2024.htm`, `ley_789_2002.htm`, etc. |
| Canonical | `ley.<NUM>.<YEAR>.art.<X>` |
| Scraper | DIAN already handles via the `ley.*` URL pattern fix shipped yesterday. |
| YAML batches | J5 (pensional + Ley 2381/2024), J6 (salud), J7 (parafiscales + licencias) |
| Expected | ~80 norms |
| **Status** | Should work today after corpus has these leyes' parsed articles. |

#### J8a-c — DUR 1072/2015 laboral (relevante)

Same as E6 — needs DUR 1072 parsed into corpus.

### Phase K — Cambiario + comercial + societario (~150 norms)

#### K1 — Resolución Externa 1/2018 JDBR

| Source | Banco de la República |
| Canonical | `res.banrep.<NUM>.<YEAR>.art.<X>` (e.g. `res.banrep.1.2018.art.5`) |
| Scraper | **No scraper exists for BanRep.** Either implement or fixture the parsed text. |

#### K2 — DCIN-83 (Departamento de Cambios Internacionales — Manual Cambiario)

| Source | BanRep |
| Canonical | `dcin.83.cap.<C>.num.<N>` |
| Scraper | **None.** |

#### K3 — Código de Comercio — sociedades

| Source | Senado-style URL pattern |
| Canonical | `cco.art.<N>` |
| Scraper | **None — would extend Senado scraper similar to CST.** |

#### K4 — Ley 222/1995 + Ley 1258/2008 (S.A.S.)

| Source | DIAN/Senado ley pages |
| Canonical | `ley.222.1995.art.<X>`, `ley.1258.2008.art.<X>` |
| Scraper | DIAN ley.* resolver works today. |
| **Status** | Works today after corpus has these leyes' parsed articles. |

## 4. Canonical norm_id grammar — quick reference

The single source of truth is `docs/re-engineer/fixplan_v3.md` §0.5
("norm-id grammar"). Highlights for the families above:

| Family | Canonical pattern |
|---|---|
| ET article | `et.art.<N>` (e.g. `et.art.555-2`) |
| ET sub-unit | `et.art.<N>.par.<P>` / `.num.<M>` / `.inciso.<I>` / `.lit.<L>` |
| Ley | `ley.<NUM>.<YEAR>` (parent) / `ley.<NUM>.<YEAR>.art.<X>` (article) |
| Ley sub-unit | `ley.<NUM>.<YEAR>.art.<X>.par.<P>` etc. |
| Decreto | `decreto.<NUM>.<YEAR>` / `decreto.<NUM>.<YEAR>.art.<X>` |
| Decreto legislativo | `decreto.legislativo.<NUM>.<YEAR>` |
| DUR sub-unit | `decreto.<NUM>.<YEAR>.libro.<L>.parte.<P>.titulo.<T>.art.<X>` |
| Resolución DIAN | `res.dian.<NUM>.<YEAR>` (sometimes zero-padded; check existing entries) |
| Resolución BanRep | `res.banrep.<NUM>.<YEAR>` |
| Concepto DIAN | `concepto.dian.<NUM>` (sometimes hyphenated for unified) |
| Oficio DIAN | `oficio.dian.<NUM>.<YEAR>` |
| Sentencia CC | `sentencia.cc.c-<NUM>.<YEAR>` (also `t-`, `su-`, `a-` for autos) |
| Sentencia CE | `sentencia.ce.<SECCION>.<RADICADO>` |
| Auto CE | `auto.ce.<RADICADO>.<DATE>` |
| CST | `cst.art.<N>` |
| Código de Comercio | `cco.art.<N>` |
| DCIN | `dcin.<NUM>.cap.<C>.num.<N>` |

Every id added to the corpus must round-trip through
`src/lia_graph/canon.py::canonicalize` returning the same string. Any
divergence means the `ingest_vigencia_veredictos` writer rejects the
veredicto at insert time (yesterday's D5 batch hit this — 36 of 39 rows
errored because Gemini emitted `sentencia.C-481.2019` instead of
`sentencia.cc.c-481.2019`).

## 5. Required deliverables from the ingestion expert

For the canonicalizer to extend its coverage from 754 → ~3,400 norms
(the YAML's full intended scope), the ingestion deliverable is:

### 5.1 Update `artifacts/parsed_articles.jsonl`

Append one row per norm in the families above. Each row must have:

```json
{
  "norm_id": "<canonical-id>",
  "norm_type": "<articulo_et|ley_articulo|decreto_articulo|res_dian|...>",
  "article_key": "<short label, e.g. 'Art. 555-2 ET'>",
  "body": "<full text of the article — verbatim from the primary source>",
  "source_url": "<the gov.co URL the body came from>",
  "fecha_emision": "<YYYY-MM-DD if known, else null>",
  "emisor": "<who issued: Congreso, DIAN, etc>",
  "tema": "<thematic tag for retrieval — optional>"
}
```

The `norm_id` field is the **only** field the canonicalizer's
`build_extraction_input_set.py` reads to deduplicate and emit
`input_set.jsonl`. Other fields support the chat backend's retrieval but
don't affect the canonicalizer.

### 5.2 Re-run the input-set builder

After appending rows to `artifacts/parsed_articles.jsonl`:
```
PYTHONPATH=src:. uv run python scripts/canonicalizer/build_extraction_input_set.py
```
Output: `evals/vigencia_extraction_v1/input_set.jsonl` regenerated. This
is what `extract_vigencia.py --batch-id <X>` reads when resolving slices.

### 5.3 Smoke-verify each phase resolves cleanly

For each phase added, run a slice-size check:
```
PYTHONPATH=src:. uv run python -c "
import sys
sys.path.insert(0, 'scripts/canonicalizer')
from extract_vigencia import _resolve_batch_input_set
from pathlib import Path
for bid in ['E1a', 'E1b', 'F1', 'G1', 'G2', 'H1', 'I2', 'J1', 'K1', 'K3']:
    norms = _resolve_batch_input_set(
        batches_config=Path('config/canonicalizer_run_v1/batches.yaml'),
        batch_id=bid,
        corpus_input_set=Path('evals/vigencia_extraction_v1/input_set.jsonl'),
        limit=None,
    )
    print(f'  {bid}: {len(norms)} norms')
"
```

Acceptance: every batch above should report a non-zero count matching
roughly the "Expected" row in §3.

### 5.4 Add scraper coverage for missing families

Three scraper gaps that block phases regardless of corpus:

1. **`auto.ce.<RADICADO>.<DATE>`** — Consejo de Estado autos. Affects
   E4 (acid test, IE state) and I4. Either implement
   `consejo_estado.py::_resolve_url` for `auto.ce.*` or fixture the
   text directly.
2. **`cst.art.<N>`** — CST articles. Affects all of J1-J4 (~170 norms).
   Most pragmatic: add a sibling scraper `secretaria_senado_cst.py` or
   extend the existing Senado scraper with a `cst.*` resolver.
3. **`decreto.legislativo.*`** — DIAN normograma file pattern is
   `decreto_legislativo_<NUM>_<YEAR>.htm`. Extend
   `dian_normograma.py::_resolve_url` to handle this prefix.

For Phase K (BanRep + Código de Comercio), no scrapers exist. These
require either real scraper work or a fixture-only path (parse the text
once, store in `tests/fixtures/scrapers/<source>/...`, never live-fetch).

## 6. Suggested priority order

If the ingestion expert can't do everything at once, the ordering that
maximizes value-per-effort:

1. **J1–J4 CST + J5/J6 Ley 100 + J7 parafiscales** — labor regime is
   first-class to Lia per the operator's product-scope memory; ~250
   norms unlock with minimal scraper work (CST scraper needed).
2. **G1–G6 Conceptos unificados DIAN** — the most-cited doctrine
   accountants reach for; ~390 norms; DIAN scraper already works for
   the URL family — only corpus parsing of the unified conceptos
   needed.
3. **F1–F4 Resoluciones DIAN** — UVT, calendario, factura electrónica;
   ~140 norms; smallest add per phase, scraper works today.
4. **E1–E3 DUR 1625** — the largest single artifact (~500 norms);
   highest absolute volume, scraper works today, but parsing the DUR
   into per-article entries is non-trivial.
5. **K1–K4 Cambiario + Código de Comercio** — ~150 norms; needs new
   scrapers for BanRep and CCo OR fixture-only ingestion.
6. **H1-H6 Conceptos individuales + oficios** — ~430 norms; needs
   `oficio.dian.*` scraper case + tighter regex.
7. **E4, E5, E6, I2, I3, I4** — the smaller specialized phases; mix of
   scraper work + corpus parsing.

## 7. What "done" looks like

After the ingestion expert ships per §5:

- Re-run `bash scripts/canonicalizer/run_full_campaign.sh` (no flags).
- Pool maintainer keeps 6+ workers active.
- DeepSeek-v4-pro processes E-K at the same ~85-95% success rate it
  hit on Phase D.
- Total verified vigencia rows in Postgres climbs from 754 → ~3,400.
- Falkor structural edges climb proportionally (we landed 642 from 754
  norms; Phase E-K should add another ~3,000+ edges for a full
  ~3,500-edge regulatory graph).
- The `evals/canonicalizer_run_v1/campaign_log.md` shows green
  verdicts (>=80%) on every phase.

## 8. Estimated compute cost for full corpus

DeepSeek-v4-pro pricing during the May 5 discount (75% off):
- Input: $0.11 effective per 1M tokens
- Output: $0.22 effective per 1M tokens
- Per-call ~12K input + ~2K output = ~$0.0018/call

At ~3,400 remaining norms × 1 call each = **~$6 in DeepSeek API spend**
to verify the full corpus once.

Wall time at 6 concurrent + 80 RPM project throttle: ~10 hours.

## 9. Document layout — how to organize your own work briefs

This document (`corpus_population_plan.md`) is the **master plan** — keep
it as the index. For your own working notes and to divide the work
across multiple experts (or sessions), follow a one-doc-per-source
convention. The right granularity is **roughly 10–12 .md documents
total**, sized so each is ingestible in one LLM context window
(~3,000–5,000 words / ~15–25 KB) and ownable by one person at a time.

### 9.1 Recommended file layout

Create a sibling directory `docs/re-engineer/corpus_population/` and
place one brief per source family inside it:

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
    ├── 07_resoluciones_dian.md               ← Phase F1-F4 (UVT, factura, etc)
    ├── 08_conceptos_dian_unificados.md       ← Phase G1-G6
    ├── 09_conceptos_dian_individuales.md     ← Phase H1-H6
    ├── 10_jurisprudencia_cc_ce.md            ← Phase I1-I4
    ├── 11_pensional_salud_parafiscales.md    ← Phase J5-J7 (Ley 100, 2381, 789)
    └── 12_cambiario_societario.md            ← Phase K1-K4 (BanRep, DCIN, CCo)
```

That's **12 source briefs + 1 master + 1 state file = 14 documents
total**, each scoped tightly enough that two experts can work in
parallel without stepping on each other. The numeric prefix preserves
priority order from §6.

### 9.2 What each brief should contain

Use this skeleton (~1–2 pages each):

```markdown
# <NN>. <Source family>

**Master:** ../corpus_population_plan.md §3.<phase>
**Owner:** <name | unassigned>
**Status:** 🟡 not started | 🔵 in progress | ✅ ingested
**Target norm count:** ~<N>
**Phase batches affected:** <e.g. J1, J2, J3, J4>

## What

One paragraph describing the source — what it is, why it matters,
what the canonicalizer needs from it.

## Source URLs (primary)

| URL | What's there |
|---|---|
| https://… | full text |

## Canonical norm_id shape

`<family>.art.<N>` (or whatever — copy from §4 of the master)

Round-trip via `lia_graph.canon.canonicalize(...)` BEFORE ingesting.

## Parsing strategy

1. Fetch source.
2. Split per article (anchor / regex / heading).
3. For each, emit a `parsed_articles.jsonl` row with:
   - `norm_id`, `norm_type`, `article_key`, `body`, `source_url`,
     `fecha_emision`, `emisor`.

## Edge cases observed

- Sub-units like `art.555-2` numbered as separate articles vs nested.
- Articles split across two HTML pages (DUR uses `pr001`-style segs).
- Modificación / derogación tags inside the article body — keep as
  raw text; the canonicalizer's vigencia harness extracts them via
  Gemini/DeepSeek, not via the parser.

## Smoke verification

After ingest:

```
PYTHONPATH=src:. uv run python -c "
... slice-size check from §5.3 ..."
```

Expected: phase batches now resolve to ≥80% of `Target norm count`.

## Dependencies on other briefs

- (e.g. `09_conceptos_dian_individuales.md` depends on
  `08_conceptos_dian_unificados.md` because the unified conceptos
  reference numerals that inherit ids from the individual ones)
```

### 9.3 Why this granularity (not bigger, not smaller)

- **Smaller** (one .md per phase batch — e.g. one per E1a, E1b, E1c…):
  too granular. The same source (DUR 1625) covers six batches; splitting
  the brief across them duplicates context and makes it hard to capture
  family-wide invariants like "Libro 1 sub-libros 1.1 through 1.8 share
  one URL pattern."
- **Bigger** (one .md per phase): too coarse. Phase E covers DUR 1625
  + DUR 1072 + COVID legislativos — three completely different sources
  with different scrapers, different URL patterns, different parsing
  strategies. Mixing them makes the brief unwieldy and prevents two
  experts from owning Phase E in parallel.
- **One per source family** (this layout): the brief scopes to one
  scraper, one URL pattern, one canonical id-shape, one parsing
  approach. An expert claims a brief, completes it end-to-end, marks
  ✅. Briefs that share a scraper extension (e.g. CST + Código de
  Comercio both want a Senado-style scraper) coordinate via the
  state file's "blocked-by" notes.

### 9.4 The state file (`state_corpus_population.md`)

Mirror the existing `state_canonicalizer_runv1.md` shape:
- §1 how to use this file
- §2 fresh-LLM preconditions (what an incoming agent needs to read first)
- §3 current global state (briefs done / in flight / blocked)
- §4 per-brief table with status + owner + last update + blockers
- §5 recovery playbooks (corpus-row corruption, scraper drift, etc.)
- §10 append-only run log

Update the state file's §4 row whenever a brief advances. The master
plan doc (this one) stays mostly static — only edit it when the
canonicalizer's expected scope itself changes.

### 9.5 Naming + commit conventions

- Filename: `NN_short-source-name.md` (lowercase, underscores).
- Commit one brief per commit when shipping the corpus rows for it
  ("corpus(cst): ingest 174 CST articles per brief 01"). Easy to revert
  if the parsing has issues without losing other briefs' work.
- Each brief lists its `Target norm count` up front so the smoke test
  in §9.2 has a pass/fail threshold.

## 10. Out of scope for the ingestion expert

These are NOT what we're asking the corpus expert to do:

- Don't rewrite the canonicalizer scripts. They work.
- Don't change `config/canonicalizer_run_v1/batches.yaml` slice
  definitions unless the expected scope is wrong (it isn't — the
  batches reflect the canonicalizer doc's intended phases).
- Don't change the prompt or the `Vigencia` schema. They've been
  hardened across A1-A6 + B1-B10 + C-D and are stable.
- Don't ingest into Postgres directly. The pipeline runs:
  `parsed_articles.jsonl` → `build_extraction_input_set.py` →
  `extract_vigencia.py` (with Gemini/DeepSeek) → `ingest_vigencia_veredictos.py` →
  Postgres `norm_vigencia_history`. Skipping steps breaks the audit
  trail.

---

*Document drafted 2026-04-28. Author: claude-opus-4-7. Source-of-truth
for what the canonicalizer needs from the corpus to extend coverage from
754 → ~3,400 verified norms.*
