# Brief & Master-Plan Edit Spec — for the corpus-ingestion experts

> **Document type.** A find/replace checklist for the corpus-ingestion experts who own the briefs in `corpus_population/`.
>
> **Date:** 2026-04-28 Bogotá.
> **Author:** claude-opus-4-7 (engineer-side).
> **Status:** Open — experts execute edits in §3; engineer ships canon-side changes in parallel; together they unblock the Phase E–K ingestion campaign.
> **Pre-reads:** `corpus_population_plan.md` (master), `corpus_population_reconciliation.md` (why these edits are needed).

---

## 1. Why this document exists

When the briefs in `docs/re-engineer/corpus_population/01_*.md` … `12_*.md` were drafted on 2026-04-28, several proposed canonical id-shapes (the strings that go in each row's `norm_id` field) **disagreed with what the canonicalizer's grammar and the batch YAML actually accept**. If the briefs ship as-written, the rows the experts produce will either be silently rejected by the writer or never picked up by the input-set builder.

This file lists every find/replace the experts must apply. Most edits are mechanical: change one substring everywhere it appears in a brief.

The **engineer** is, in parallel, extending the canonicalizer code to support four new families (`cst`, `cco`, `dcin`, `oficio.<emisor>.<NUM>.<YEAR>`) so that briefs 01, 09, and the cambiario/societario half of 12 can ship with the shapes they already propose. **No expert edits are required for those families.**

After the edits in §3 land, every `norm_id` example in the briefs must round-trip cleanly through:

```python
from lia_graph.canon import canonicalize
assert canonicalize("<example>") == "<example>"
```

A one-paste validation script that exercises every example is in §4.

---

## 2. Heads-up: what the engineer is changing on the code side (NOT your work)

Listed only so you don't get surprised when you see new test files or new canon rules land:

* `src/lia_graph/canon.py` will gain four new rules + four new mention-finders + four new grammar patterns for: `cst.art.<N>`, `cco.art.<N>`, `dcin.<NUM>.cap.<C>.num.<N>`, `oficio.<emisor>.<NUM>.<YEAR>`.
* `src/lia_graph/canon.py` will gain helper updates in `display_label` and `norm_type` for those families.
* `tests/test_canon.py` will gain round-trip cases.

You don't need to do anything for the families above. Briefs **01_cst.md**, **09_conceptos_dian_individuales.md** (oficio half), and **12_cambiario_societario.md** (DCIN + CCo halves) ship as-written.

---

## 3. The edits, brief by brief

> **🚨 Examples in this section are pattern illustrations, not verified-real norm_ids.**
>
> Wherever you see a concrete article number, oficio number, or sentencia number below
> (e.g. `decreto.1625.2016.art.1.5.2.1`, `oficio.dian.018424.2024`, `sent.cc.C-291.2015`),
> treat it as **a placeholder showing the canonical SHAPE**. Before pasting any such id
> into a real `parsed_articles.jsonl` row, verify against the actual source (DIAN normograma,
> Senado, Corte Constitucional / Consejo de Estado relatoria, BanRep) that the article /
> oficio / sentencia with that exact number exists.
>
> The shape is what's authoritative; the specific number is illustrative. Hallucinated
> numbers will round-trip through `canonicalize()` cleanly (the grammar only checks
> structure) but will produce ghost rows that point at nothing. The §4 validation script
> catches shape errors but cannot catch a well-shaped reference to a non-existent norm.
>
> Verified-real ids you can use safely without re-checking are listed in
> `config/canonicalizer_run_v1/batches.yaml` (the `explicit_list` arrays of every batch);
> those are pre-vetted by the canonicalizer team.

Briefs not listed here need **no changes**: 07, 08, 11, and the Ley 222/Ley 1258/res.banrep portions of brief 12.

### 3.1 `corpus_population_plan.md` (the master plan) — §5 grammar table

**Why:** §5 is the human reference for the canonical norm-id shapes; it currently lists three shapes that the canonicalizer rejects and one that requires a missing date segment. Briefs 02-06 and 10 reference §5 as their source of truth, so the master must be corrected first.

**Find/replace:**

| Find | Replace with | Notes |
|---|---|---|
| `decreto.legislativo.<NUM>.<YEAR>` | `decreto.<NUM>.<YEAR>` | Drop the `.legislativo` segment everywhere in §5. The canonicalizer treats decretos legislativos as ordinary decretos; the "legislativo" character is metadata that lives in the article body, not the id. |
| `decreto.<NUM>.<YEAR>.libro.<L>.parte.<P>.titulo.<T>.art.<X>` | `decreto.<NUM>.<YEAR>.art.<dotted-decimal-as-printed>` | Use the article number **as printed in the source** (e.g., DUR 1625's "Artículo 1.2.1.1" → `decreto.1625.2016.art.1.2.1.1`). The libro/parte/título structure is human metadata for the body field; do not encode it in the id. The example row should change from `decreto.1625.2016.libro.1.5.2.1` to `decreto.1625.2016.art.1.5.2.1`. |
| `sentencia.cc.<TYPE>-<NUM>.<YEAR>` (with `<TYPE>` ∈ `{c, t, su, a}` lowercase) | `sent.cc.<TYPE>-<NUM>.<YEAR>` (with `<TYPE>` ∈ `{C, T, SU, A}` **uppercase**) | Two changes in one row: prefix changes from `sentencia.cc.` to `sent.cc.`, and the type letter is uppercase. The example row should change from `sentencia.cc.c-481.2019` to `sent.cc.C-481.2019`. |
| `sentencia.ce.<SECCION>.<RADICADO>` | `sent.ce.<RADICADO>.<YEAR>.<MM>.<DD>` | The CE id is keyed by the radicado number plus a date, not by sección. Drop the `<SECCION>` segment; add a date. The example row should change from `sentencia.ce.suj.4.002.2022` to `sent.ce.28920.2025.07.03` (or whatever radicado-number+date the source gives). The sección stays as metadata in the body. |
| `auto.ce.<RADICADO>.<DATE>` (with `<DATE>` left unspecified) | `auto.ce.<RADICADO>.<YEAR>.<MM>.<DD>` (with date **always** in `YYYY.MM.DD` shape) | The date is required — autos in CE relatoria always carry a `dd-mm-yyyy` notification date. Read it off the relatoria index and emit `YYYY.MM.DD`. The example row should change from `auto.ce.082.2026` to `auto.ce.082.2026.04.15`. |

**Add to §5** (new rows for the four families the engineer is adding to canon — you can write these in advance so the master plan is internally complete):

| Family | Canonical pattern | Example |
|---|---|---|
| CST article | `cst.art.<N>` | `cst.art.158` |
| Código de Comercio article | `cco.art.<N>` | `cco.art.98` |
| Oficio DIAN | `oficio.<emisor>.<NUM>.<YEAR>` | `oficio.dian.018424.2024` |
| DCIN numeral | `dcin.<NUM>.cap.<C>.num.<N>` | `dcin.83.cap.5.num.3` |

(These rows already exist in §5 — just leave them; the engineer's canon work makes them valid.)

### 3.2 `corpus_population/02_dur_1625_renta.md` — DUR 1625 Libro 1 (renta)

**Why:** The brief uses `decreto.1625.2016.libro.1.<sub>.<art>` everywhere. The canonicalizer accepts only the flat-art form. The YAML's batches E1a–E1f use prefixes like `decreto.1625.2016.art.1.5.` — which is what the rows must produce.

**Find/replace (apply to every occurrence):**

| Find | Replace with |
|---|---|
| `decreto.1625.2016.libro.1.<sub>.<art>` | `decreto.1625.2016.art.<N>` (where `<N>` is the article number **as printed in the source**, e.g. `1.2.1.1`) |
| `decreto.1625.2016.libro.1.5.2.1` (any concrete example with a `libro.` segment) | `decreto.1625.2016.art.1.5.2.1` |

**Header / "Canonical norm_id shape" section.** Replace the whole `decreto.1625.2016.libro.1.<sub>.<art>` block with:

> Canonical shape: `decreto.1625.2016.art.<dotted-decimal-as-printed>`
>
> The DUR's articles are numbered with dotted decimals in the source (e.g., "Artículo 1.5.2.1"). Use that number verbatim. The libro / parte / título / capítulo structure is rich metadata for the body field — do not encode it in the id.
>
> Examples:
> * `decreto.1625.2016.art.1.1.1` — DUR 1625, Art. 1.1.1 (definiciones generales)
> * `decreto.1625.2016.art.1.5.2.1` — DUR 1625, Art. 1.5.2.1 (procedimiento)
> * `decreto.1625.2016.art.1.3.45-2` — DUR 1625, Art. 1.3.45-2 (compound article number)

**Smoke verification.** No change needed — the §6.3 batch-resolution check is parameterized; once the rows carry the new shape they will match the YAML's regexes.

### 3.3 `corpus_population/03_dur_1625_iva_retefuente.md` — DUR 1625 Libro 2 (IVA + retefuente)

**Why:** Same as 3.2. Additionally, the brief equates "Libro 2 IVA" with `libro.2.*`, but the YAML's E2a/E2b/E2c batches actually target `decreto.1625.2016.art.1.3.*` (DUR's libro 3 = IVA in the canonical numbering) and `decreto.1625.2016.art.1.2.4.*` (retefuente reglamentado).

**Find/replace:**

| Find | Replace with |
|---|---|
| `decreto.1625.2016.libro.2.<sub>.<art>` | `decreto.1625.2016.art.<N>` (use the article number as printed) |
| `decreto.1625.2016.libro.2.1.10` | `decreto.1625.2016.art.1.3.1.10` (or whatever the actual printed article number is for that IVA article) |
| `decreto.1625.2016.libro.2.3.85-1` | `decreto.1625.2016.art.1.3.<dotted-decimal>-1` (use the printed article number for retefuente articles) |

**Replace the parsing-strategy line** that says `output_filter=lambda row: 'libro.2.' in row['norm_id']` with `output_filter=lambda row: row['norm_id'].startswith('decreto.1625.2016.art.1.3.') or row['norm_id'].startswith('decreto.1625.2016.art.1.2.4.')`.

**Add a clarifying paragraph** to "What" or to "Edge cases":

> "Libro 2" in this brief's title is a human label for the IVA + retefuente subject area. In the canonical norm_id, this corresponds to the DUR's article-number prefixes `1.3.*` (IVA proper) and `1.2.4.*` (retefuente reglamentado), per `config/canonicalizer_run_v1/batches.yaml` batches E2a/E2b/E2c. Read the article number off the source; do not invent a `libro.2` segment.

### 3.4 `corpus_population/04_dur_1625_procedimiento.md` — DUR 1625 Libro 3 (procedimiento)

**Why:** Same shape problem as 3.2/3.3. The YAML's E3a/E3b batches target `decreto.1625.2016.art.1.5.*` (DUR's libro 5 = procedimiento + sanciones).

**Find/replace:**

| Find | Replace with |
|---|---|
| `decreto.1625.2016.libro.3.<sub>.<art>` | `decreto.1625.2016.art.<N>` (use the article number as printed; for procedimiento these start with `1.5.`) |
| `decreto.1625.2016.libro.3.1.5` | `decreto.1625.2016.art.1.5.1.5` (or whatever the printed number is) |
| `decreto.1625.2016.libro.3.2.125-A` | `decreto.1625.2016.art.1.5.2.125-1` (or whatever the printed number is; the canonicalizer accepts **hyphen-digit** suffixes for compound articles, e.g. `-1`, `-2`, `-3`, but **not hyphen-letter** like `-A`. If the source uses a letter suffix, drop it or substitute the next available digit suffix and document the mapping in the row's body field.) |

**Add a clarifying paragraph**:

> "Libro 3" in this brief's title is the human label for procedimiento + sanciones. In the canonical norm_id, this corresponds to the DUR's article-number prefix `1.5.*`, per `batches.yaml` E3a/E3b. Use the article numbers as printed in the source.

### 3.5 `corpus_population/05_dur_1072_laboral.md` — DUR 1072/2015

**Why:** The brief uses `decreto.1072.2015.libro.<L>.parte.<P>.titulo.<T>.art.<art>`. The canonicalizer rejects this. The YAML's E6a–E6c and J8a–J8c batches target `decreto.1072.2015.art.2.2.<X>.*` (DUR 1072's articles are numbered like "2.2.4.6.42" with the libro/parte/título structure already baked into the dotted decimal).

**Find/replace:**

| Find | Replace with |
|---|---|
| `decreto.1072.2015.libro.<L>.parte.<P>.titulo.<T>.art.<art>` | `decreto.1072.2015.art.<dotted-decimal-as-printed>` |
| `decreto.1072.2015.libro.1.parte.1.titulo.1.art.1` | `decreto.1072.2015.art.1.1.1.1` (or whatever the article number is in the source — DUR 1072 article 1 of libro 1, parte 1, título 1 is printed as "Artículo 1.1.1.1") |
| `decreto.1072.2015.libro.2.parte.2.titulo.5.art.45` | `decreto.1072.2015.art.2.2.5.<rest>` (use the printed article number; DUR 1072's libro 2 corresponds to the leading `2.` segment) |
| `decreto.1072.2015.libro.3.parte.1.titulo.1.art.1` | `decreto.1072.2015.art.<dotted-decimal>` (use printed number) |
| `decreto.1072.2015.libro.2.parte.2.titulo.5.art.45-1` | `decreto.1072.2015.art.<dotted-decimal>-1` (preserve hyphen for sub-numbered articles) |

**Replace the round-trip example block:**

```
assert canonicalize("decreto.1072.2015.libro.3.parte.1.titulo.1.art.1") == "decreto.1072.2015.libro.3.parte.1.titulo.1.art.1"
```

…with:

```
assert canonicalize("decreto.1072.2015.art.2.2.4.6.42") == "decreto.1072.2015.art.2.2.4.6.42"
```

(Replace with whichever printed article number you actually ingest.)

**Replace the row-emit example** (line 87 area) to use `art.<dotted-decimal-as-printed>` instead of `libro.<L>.parte.<P>.titulo.<T>.art.<art>`.

**Add a clarifying paragraph**:

> DUR 1072/2015 numbers articles with dotted decimals (e.g., "Artículo 2.2.4.6.42") in the source. The leading `2.` corresponds to libro 2 (régimen laboral), `2.2.4.*` corresponds to riesgos laborales (Sistema de Riesgos), `2.2.5.*` to SST. Use the printed article number verbatim; do not encode the libro/parte/título as separate segments.

### 3.6 `corpus_population/06_decretos_legislativos_covid.md` — Decretos legislativos COVID

**Why:** The brief uses `decreto.legislativo.<NUM>.<YEAR>.art.<X>`. The canonicalizer rejects the `.legislativo` segment. The YAML's E5 batch uses `^decreto\.(417|444|535|568|573|772)\.2020` — plain decreto, no `.legislativo`.

**Find/replace (apply globally):**

| Find | Replace with |
|---|---|
| `decreto.legislativo.<NUM>.<YEAR>.art.<X>` | `decreto.<NUM>.<YEAR>.art.<X>` |
| `decreto.legislativo.417.2020.art.1` | `decreto.417.2020.art.1` |
| `decreto.legislativo.682.2020.art.3` | `decreto.682.2020.art.3` |
| `decreto.legislativo.772.2020.art.15` | `decreto.772.2020.art.15` |
| `decreto_legislativo_<NUM>_<YEAR>.htm` (URL pattern) | leave as-is — that's the DIAN site's URL filename, which is a separate concern from the canonical id |

**Update the "⚠️ CRITICAL BLOCKER" / Gap #3 section** to read:

> The DIAN normograma scraper resolves `decreto.<NUM>.<YEAR>` ids by mapping to the URL `decreto_<NUM>_<YEAR>.htm`. For decretos legislativos the URL filename is `decreto_legislativo_<NUM>_<YEAR>.htm`. The scraper needs an explicit case that detects whether the source decree is a "decreto legislativo" (issued under emergencia económica) and rewrites the URL accordingly — but the canonical norm_id stays as `decreto.<NUM>.<YEAR>` regardless. The "legislativo" character lives in the article body and the source-URL metadata, not the id.

**Replace the round-trip example** at line 71:

```
assert canonicalize("decreto.legislativo.682.2020.art.3") == "decreto.legislativo.682.2020.art.3"
```

…with:

```
assert canonicalize("decreto.682.2020.art.3") == "decreto.682.2020.art.3"
```

**Update the row-emit example** (line 92 area) to set `norm_id` to `decreto.<NUM>.<YEAR>.art.<X>` and add a `tema: "decreto_legislativo_covid"` field if you want the legislativo character preserved.

### 3.7 `corpus_population/10_jurisprudencia_cc_ce.md` — Jurisprudencia CC + CE + Autos CE

**Why:** Three different sub-shapes are wrong:

* Sentencias CC use `sent.cc.C-<NUM>.<YEAR>` with **uppercase** type letter. The brief currently uses `sentencia.cc.c-*` (wrong prefix + wrong case).
* Sentencias CE are keyed by `sent.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>`, not by sección. The brief currently uses `sentencia.ce.suj.4.<SHORT>.<YEAR>` (wrong prefix + wrong segmentation + missing date).
* Autos CE require a date in `YYYY.MM.DD` form. The brief currently leaves the date "TBD" and gives the example `auto.ce.082.2026` (no date).

**Find/replace (Sentencia CC):**

| Find | Replace with |
|---|---|
| `sentencia.cc.<TYPE>-<NUM>.<YEAR>` (with `<TYPE>` lowercase) | `sent.cc.<TYPE>-<NUM>.<YEAR>` (with `<TYPE>` **uppercase**: `C`, `T`, `SU`, or `A`) |
| `sentencia.cc.c-291.2015` | `sent.cc.C-291.2015` |
| `sentencia.cc.c-481.2019` (anywhere) | `sent.cc.C-481.2019` |
| Any other `sentencia.cc.c-*` example | rewrite as `sent.cc.C-*` |

**Find/replace (Sentencia CE):**

| Find | Replace with |
|---|---|
| `sentencia.ce.<SECCION>.<RADICADO>` | `sent.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>` |
| `sentencia.ce.suj.4.002.2022` (line 43) | `sent.ce.28920.2025.07.03` (or whatever radicado-number + decision-date applies; this is the YAML's G6 acid-test example) |
| `sentencia.ce.suj.4.<SHORT>.<YEAR>` (line 87, 91) | `sent.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>` |
| `sentencia.ce.suj.4.507.2014` (line 88) | replace with the actual radicado-number + decision-date for that sentencia, e.g. `sent.ce.<radicado-num>.2014.<MM>.<DD>` |

**Update the parsing-strategy paragraph** (around line 87) to read:

> Sentencias CE are keyed by the **radicado number** (the integer that uniquely identifies the case in the CE relatoria, e.g. `28920`) plus the **decision date** in `YYYY.MM.DD`. The sección (cuarta, primera, etc.) lives in the body as metadata. Do not encode the sección in the norm_id.

**Find/replace (Auto CE):**

| Find | Replace with |
|---|---|
| `auto.ce.<RADICADO>.<DATE>` (with date format unspecified) | `auto.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>` (date is **required**, in `YYYY.MM.DD` form) |
| `auto.ce.082.2026` (line 48) | `auto.ce.082.2026.04.15` (or whatever the actual notification date is) |

**Replace the round-trip example** at line 50:

```
canonicalize("auto.ce.082.2026") → "auto.ce.082.2026" ✓
```

…with:

```
canonicalize("auto.ce.082.2026.04.15") → "auto.ce.082.2026.04.15" ✓
```

**Update Gap #1 description** to emphasize the date requirement:

> The CE scraper's `_resolve_url` for autos must accept a four-part canonical id `auto.ce.<NUM>.<YEAR>.<MM>.<DD>` and emit a CE search URL keyed by both radicado number and date. The radicado-only form `auto.ce.<NUM>.<YEAR>` is **not** a valid canonical id and will be rejected at write time.

### 3.8 `corpus_population/09_conceptos_dian_individuales.md` — Oficios DIAN

**Why:** The brief is mostly correct — `oficio.dian.<NUM>.<YEAR>` is what the engineer is adding to canon. **No edits required**. One small clarification helps experts produce clean rows:

**Add a clarification paragraph to "Edge cases"** (or wherever fits):

> **Concepto vs Oficio.** Two distinct families with two distinct canonical id shapes: a Concepto DIAN is identified by number only (`concepto.dian.<NUM>`), while an Oficio DIAN is identified by number + year (`oficio.dian.<NUM>.<YEAR>`). Do not collapse them. If a source document is titled "Oficio Nº 018424 del 2024", emit `oficio.dian.018424.2024`; if it's titled "Concepto Unificado de Renta Nº 0912", emit `concepto.dian.0912`. Mixing them will produce non-canonical ids that the writer rejects.

### 3.9 `corpus_population/12_cambiario_societario.md` — Cambiario, Societario, DCIN, CCo

**Why:** Most of the brief is already canonical. The DCIN-83, Código de Comercio, Resolución BanRep, and Ley 222/Ley 1258 shapes the brief proposes are all correct (the engineer's canon work makes DCIN and CCo land in the grammar). **No find/replace edits required.**

**Add one clarification paragraph to "Canonical norm_id shape"** so experts on the cambiario half understand the BanRep articulación:

> Resolución Externa 1/2018 JDBR uses the canonical shape `res.banrep.1.2018.art.<N>`, where `<N>` is the article number as printed (1, 2, 3, …). The "1" between `banrep.` and `.2018` is the resolution number; the article number after `.art.` is the per-article identifier. Sub-paragrafs use `.par.<P>` (e.g. `res.banrep.1.2018.art.5.par.1`). Do not invent a sección or capítulo segment in the id; chapter/section context lives in the body.

**Add one clarification paragraph to "Edge cases"** about CCo:

> The Código de Comercio is numbered flat — `cco.art.<N>` with `<N>` an integer 1–2032. Sub-units use the standard sub-unit suffixes (`.par.<P>`, `.num.<N>`, `.lit.<L>`, `.inciso.<I>`) per the master plan §5. Use lowercase letters for literals (`cco.art.98.lit.a`, not `cco.art.98.lit.A`).

---

## 4. Validation snippet — paste this after every brief edit

After editing any brief, copy each `norm_id` example into this list and paste into a Python REPL with the repo's environment loaded:

```bash
PYTHONPATH=src:. uv run python -c "
from lia_graph.canon import canonicalize

examples = [
    # 02 DUR 1625 Libro 1
    'decreto.1625.2016.art.1.1.1',
    'decreto.1625.2016.art.1.5.2.1',
    'decreto.1625.2016.art.1.3.45-2',

    # 03 DUR 1625 Libro 2
    'decreto.1625.2016.art.1.3.1.10',
    'decreto.1625.2016.art.1.2.4.85-1',

    # 04 DUR 1625 Libro 3
    'decreto.1625.2016.art.1.5.1.5',
    'decreto.1625.2016.art.1.5.2.125-1',

    # 05 DUR 1072
    'decreto.1072.2015.art.1.1.1.1',
    'decreto.1072.2015.art.2.2.4.6.42',
    'decreto.1072.2015.art.2.2.5.1.1',

    # 06 Decretos legislativos COVID
    'decreto.417.2020.art.1',
    'decreto.682.2020.art.3',
    'decreto.772.2020.art.15',

    # 10 Jurisprudencia
    'sent.cc.C-291.2015',
    'sent.cc.C-481.2019',
    'sent.ce.28920.2025.07.03',
    'auto.ce.082.2026.04.15',

    # 09 Oficios DIAN  (engineer-side canon work required)
    # 'oficio.dian.018424.2024',  # uncomment after engineer ships canon extension

    # 12 Cambiario / societario  (DCIN + CCo engineer-side; rest already canonical)
    'res.banrep.1.2018.art.5',
    'ley.222.1995.art.1',
    'ley.1258.2008.art.1',
    # 'dcin.83.cap.5.num.3',     # uncomment after engineer ships canon extension
    # 'cco.art.98',              # uncomment after engineer ships canon extension
]

bad = [e for e in examples if canonicalize(e) != e]
if bad:
    print('FAIL — these did not round-trip:')
    for e in bad:
        print(f'  {e!r} -> {canonicalize(e)!r}')
    raise SystemExit(1)
print(f'OK — all {len(examples)} examples round-trip cleanly.')
"
```

A clean `OK` means every brief example in §3 now matches the canonicalizer. A `FAIL` means at least one example still uses the old shape — go back and re-grep the affected brief.

The four engineer-side families (`cst.art.*`, `cco.art.*`, `dcin.*`, `oficio.dian.*.<YEAR>`) will start round-tripping the moment the engineer's canon extension lands. The expert can leave those lines commented in this validation script until the engineer signals "canon extension shipped," then uncomment them and re-run.

---

## 5. What stays the same (nothing for experts to do)

* Briefs **07** (Resoluciones DIAN), **08** (Conceptos unificados), **11** (Pensional / Salud / Parafiscales) — already canonical, no edits.
* Brief **01** (CST) — engineer extends canon to support `cst.art.<N>`; brief ships as-written.
* Brief **09** (Conceptos individuales) — concepto half already canonical; oficio half waits on the engineer's canon extension; only the §3.8 clarification paragraph is needed.
* Brief **12** (Cambiario / societario) — Ley 222, Ley 1258, and res.banrep are canonical; DCIN + CCo wait on the engineer's canon extension; only the §3.9 clarification paragraphs are needed.
* The `parsed_articles.jsonl` schema stays exactly as documented in `corpus_population_plan.md §6.1`. The `body`, `source_url`, `fecha_emision`, `emisor`, `tema` fields are unchanged.
* The §6.3 batch-resolution smoke check is unchanged.
* The state file `state_corpus_population.md` per-brief table is unchanged in structure; only update each row's `Last update` column when you finish that brief's edits.

---

## 6. Definition of done

Done when, for every brief listed in §3:

1. The find/replace edits in the matching subsection are applied.
2. The new clarification paragraph (where called out) is added.
3. The brief's example `norm_id` strings, when added to the §4 validation script, all return `OK`.
4. The state file's run log gets one entry per brief: `YYYY-MM-DD HH:MM TZ — brief 0X — canonical-id edits applied per corpus_population_brief_edits.md §3.X.`.

When all six §3 briefs (02, 03, 04, 05, 06, 10) have logged that entry, plus the master plan §5 has the §3.1 edits applied, plus this file's §3.8 / §3.9 clarification paragraphs are in briefs 09 and 12, the expert side of the reconciliation is done.

The engineer-side canon extension (cst, cco, dcin, oficio) is tracked separately in `corpus_population_reconciliation.md §5` and lands in `src/lia_graph/canon.py` + `tests/test_canon.py`.

---

*Edit spec drafted 2026-04-28 by claude-opus-4-7 for outside corpus-ingestion experts. Pair this with `corpus_population_reconciliation.md` for context. Any ambiguity: the canonicalizer's `_NORM_ID_FULL_RE` in `src/lia_graph/canon.py` and `config/canonicalizer_run_v1/batches.yaml` are the authoritative ground truth.*
