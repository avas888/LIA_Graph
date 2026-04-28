# Corpus Population — Brief ↔ Canon ↔ Batch YAML Reconciliation

> **Document type.** Blocker analysis for the corpus population effort.
> Not a brief; not the master plan. A reconciliation note that must be
> resolved before any of the 12 source briefs in `corpus_population/`
> can produce ingest-able rows.
>
> **Date:** 2026-04-28 Bogotá (drafted after the briefs landed in-repo).
> **Author:** claude-opus-4-7.
> **Status:** Open — operator decision required on §4 before scrape/parse work begins.
> **Authoritative companions:**
>   * `corpus_population_plan.md` — the master plan being reconciled
>   * `corpus_population/01_cst.md` … `12_cambiario_societario.md` — the briefs being reconciled
>   * `src/lia_graph/canon.py` — the canonicalizer grammar (single source of truth for `norm_id` formatting)
>   * `config/canonicalizer_run_v1/batches.yaml` — the YAML the canonicalizer harness reads

---

## 1. The reconciliation problem in one paragraph

The 12 briefs (and the master plan §5) propose canonical id-shapes that
**three places in the repo disagree on**:

* **`canon.py`** — the actual canonicalizer grammar (`_NORM_ID_FULL_RE`).
* **`batches.yaml`** — what the canonicalizer harness's regex/prefix
  filters are searching for.
* **The 12 briefs** — what `parsed_articles.jsonl` rows would carry.

Where all three agree, the brief is workable as-written. Where they
disagree, ingestion produces dead-on-arrival rows: either the writer
rejects them (round-trip fail), the harness's batch filter doesn't
match them (slice resolves to 0), or the body-text discovery in
`build_extraction_input_set.py` never finds them (no `_MENTION_FINDERS`
rule).

This file enumerates the gaps. **No scrape/parse work should start on a
brief flagged red below until its specific gap is closed.**

---

## 2. How `build_extraction_input_set.py` actually works

A second-order finding that compounds §1: the input-set builder does
**not** read a `norm_id` field from each `parsed_articles.jsonl` row.
It reads the body text and runs `canon.find_mentions()` over it,
canonicalizing each mention via the `_RULES` registry and emitting the
**deduplicated set of mentions** as the input set.

```python
# scripts/canonicalizer/build_extraction_input_set.py:55-87
from lia_graph.canon import canonicalize_or_refuse, find_mentions
...
for chunk_id, chunk_text in chunks:
    for mention in find_mentions(chunk_text):
        norm_id, refusal = canonicalize_or_refuse(mention.text)
        ...
        seen[norm_id] = {...}
```

**Implication.** A brief that drops 170 CST articles into the corpus
with `norm_id="cst.art.<N>"` set on each row will produce **zero**
input-set entries — because:

1. `_MENTION_FINDERS` has no CST pattern (only ET, ley, decreto, res,
   concepto/oficio DIAN, sentencia CC, auto generic). It will never
   locate a CST mention in body text.
2. Even if a finder hit, `_RULES` has no `_rule_cst` to canonicalize
   `"Artículo 22 CST"` to `cst.art.22`.

The brief schema in `corpus_population_plan.md §6.1` carries `norm_id`
because it documents intent — but the harness ignores it. The body
text and the canon grammar are what actually drive what lands in
`input_set.jsonl`.

This is a structural mismatch between the briefs' theory of operation
and the harness's actual code path. Fixing it is on the canonicalizer
side, not the corpus-expert side.

---

## 3. Per-brief reconciliation matrix

Tested 2026-04-28 by round-tripping each proposed shape through
`canonicalize()` and cross-checking the YAML's regex/prefix filters.

| Brief | Family | Brief proposes | YAML expects | Canon accepts | Verdict |
|---|---|---|---|---|---|
| 01 | CST | `cst.art.<N>` | `^cst\.art\.\d+$` | ❌ no rule | 🔴 needs canon extension (rule + grammar + finder) |
| 02 | DUR 1625 Libro 1 | `decreto.1625.2016.libro.1.<sub>.<art>` | `^decreto\.1625\.2016\.art\.1\.<sub>\.` | ✅ flat-art form only | 🟡 brief revision (use `art.1.X.Y...`, not `libro.1.X.Y`) |
| 03 | DUR 1625 Libro 2 | `decreto.1625.2016.libro.2.<sub>.<art>` | `^decreto\.1625\.2016\.art\.1\.2\.4\.` etc. | ✅ flat-art form only | 🟡 brief revision (same as 02; YAML doesn't actually have `art.2.*` rows — verify) |
| 04 | DUR 1625 Libro 3 | `decreto.1625.2016.libro.3.<sub>.<art>` | (no E3 rows in YAML grep — verify) | ✅ flat-art form only | 🟡 brief revision + verify YAML |
| 05 | DUR 1072 | `decreto.1072.2015.libro.<L>.parte.<P>.titulo.<T>.art.<art>` | `^decreto\.1072\.2015\.art\.2\.2\.<X>\.` | ✅ flat-art form only | 🟡 brief revision (use `art.<L>.<P>.<T>.<art>`) |
| 06 | Decretos legislativos | `decreto.legislativo.<NUM>.<YEAR>.art.<X>` | `^decreto\.(417\|444\|535\|568\|573\|772)\.2020` | ✅ plain `decreto.<NUM>.<YEAR>` only | 🟡 brief revision (drop `.legislativo` segment — flat is fine) |
| 07 | Resoluciones DIAN | `res.dian.<NUM>.<YEAR>` | `^res\.dian\.…` | ✅ | 🟢 unblocked |
| 08 | Conceptos unificados | `concepto.dian.<NUM>` / `…num.<X>` | `^concepto\.dian\.…` | ✅ | 🟢 unblocked |
| 09 | Conceptos individuales + oficios | `concepto.dian.<NUM>` (✅) **+ `oficio.dian.<NUM>.<YEAR>` (❌)** | `^concepto\.dian\.…` and `^oficio\.dian` | concepto ✅, oficio ❌ no rule | 🔴 needs canon extension OR YAML+brief revision (collapse oficio→concepto) |
| 10 | Jurisprudencia | `sentencia.cc.c-<NUM>.<YEAR>` (lowercase `c`, prefix `sentencia.`) | `^sent\.cc\.C-…` (uppercase `C`, prefix `sent.`) | `sent.cc.C-<NUM>.<YEAR>` only | 🟡 brief revision (use `sent.cc.C-<NUM>.<YEAR>` form) |
| 10 | Autos CE | `auto.ce.<NUM>.<YEAR>` (no date) | `^auto\.ce\.` | `auto.ce.<NUM>.<YEAR>.<MM>.<DD>` (date required) | 🟠 brief + canon decision (drop date requirement, or always emit a date — pick one) |
| 10 | Sentencias CE unificación | `sentencia.ce.<SECCION>.<RADICADO>` | `^sent\.ce\..*` | `sent.ce.<NUM>.<YEAR>.<MM>.<DD>` only | 🟡 brief revision (use `sent.ce.<NUM>.<YEAR>.<MM>.<DD>`) |
| 11 | Ley 100 / 2381 / 789 | `ley.<NUM>.<YEAR>.art.<X>` | `^ley\.…\.art\.…` | ✅ | 🟢 unblocked |
| 12 | Ley 222 / Ley 1258 (S.A.S.) | `ley.<NUM>.<YEAR>.art.<X>` | (verify K4 in YAML) | ✅ | 🟢 unblocked (within K4) |
| 12 | Resolución BanRep | `res.banrep.<NUM>.<YEAR>.art.<X>` | `^res\.banrep\.1\.2018` | ✅ | 🟢 unblocked |
| 12 | DCIN-83 | `dcin.83.cap.<C>.num.<N>` | `^dcin\.83` | ❌ no rule | 🔴 needs canon extension |
| 12 | Código de Comercio | `cco.art.<N>` | `^cco\.art\.\d+$` | ❌ no rule | 🔴 needs canon extension (parallel to CST) |

**Roll-up:**

* 🟢 **unblocked-as-written** — 4 briefs (07, 08, 11) and parts of 12 (Ley 222/1258 + res.banrep parent) — total ~310 norms
* 🟡 **brief-edit only** — 5 briefs (02, 03, 04, 05, 06) and parts of 10 (sentencias CC, sentencias CE) — total ~1,075 norms
* 🟠 **brief + small canon decision** — 1 sub-brief (Autos CE date requirement, ~20 norms)
* 🔴 **canon extension required** — briefs 01 (CST, ~170), 09 (oficio, ~150), and parts of 12 (DCIN ~40, CCo ~60) — total ~420 norms

Of the ~1,690-norm corpus gap:
* ~310 norms can be ingested today after `find_mentions` is exercised against parsed bodies that mention the canonical citations.
* ~1,075 norms unblock with brief edits (no code change).
* ~420 norms require small canon extensions (4 new families: cst, cco, dcin, oficio) plus parallel `_MENTION_FINDERS` patterns.

---

## 4. Three paths forward — operator decides

Each path is internally consistent. Mixing paths is fine but requires
careful sequencing (see §5).

### Path A — Revise briefs to match canon, then extend canon for the 4 missing families

1. Edit briefs 02, 03, 04, 05, 06, 10 to use the canon-and-YAML-aligned
   shapes. ~30 minutes of doc work; no code.
2. Extend `canon.py` for the four missing families: `cst`, `cco`, `dcin`,
   `oficio.<emisor>.<num>.<year>`. New `_rule_*` parsers, new
   `_NORM_ID_PATTERNS` entries, new `_MENTION_FINDERS` patterns, plus
   `display_label` + `norm_type` updates. ~3-4 hours of code + tests.
3. Resolve the auto.ce date question (§3 row 11). Either drop the date
   requirement (relaxing canon) or make ingestion always emit a date
   (tightening briefs). Recommend: keep date required — autos are
   identified by date in the CE relatoria index — and update the brief
   to fixture-emit `auto.ce.<NUM>.<YEAR>.<MM>.<DD>`.
4. THEN start the 12-brief ingestion campaign per the master plan's §8
   priority order.

**Pros.** Single source of truth (`canon.py`) is the authority across
the whole pipeline. Brief revision becomes mechanical. Future families
(say a Resolución SuperFinanciera) get the same treatment. No silent
shape disagreements.

**Cons.** ~½ day of code work before any norm lands in the corpus.

### Path B — Skip the four missing families; ingest only what canon already accepts

1. Edit briefs 02-06 + brief 10 to canon-aligned shapes (same as Path A
   step 1).
2. Drop briefs 01 (CST), 09 oficio sub-brief, and 12 DCIN+CCo
   sub-briefs from this campaign — they sit until the canon extension
   ships.
3. Ingest the ~1,385 unblocked-or-edit-only norms. Canonicalizer can
   then verify vigencia for those.
4. Ship grammar extensions later as a follow-up sprint.

**Pros.** Fastest time to first canonicalizer-verified rows in the new
families (E, F, G, parts of I, J, K).

**Cons.** Labor regime (CST = brief 01 = ~170 norms) is the highest-
priority batch in the master plan §8 (operator's "Lia scope includes
labor" memory). Skipping CST defeats the original prioritization.
Returns ~1,385 of ~1,690 missing norms.

### Path C — Extend canon first, leave briefs as-written, fix the master plan

1. Extend `canon.py` not just for the 4 missing families but also for
   the `libro.<L>.parte.<P>.titulo.<T>.art.<X>` shape that the briefs
   and master plan §5 already document. Means accepting BOTH
   `decreto.X.Y.art.A.B.C.D` (current) AND
   `decreto.X.Y.libro.L.parte.P.titulo.T.art.X` (proposed) — with
   `canonicalize` mapping mentions to whichever the YAML expects.
2. Update `batches.yaml` to use the libro-form prefixes if that's the
   intended canonical, OR keep the flat-art form and have canon emit
   it from any input shape.
3. Then ingest.

**Pros.** Honors the master plan's §5 grammar exactly as drafted.
Better human-readability for DUR norm_ids (you can tell at a glance
that `decreto.1625.2016.libro.1.5.2.1` is in libro 1).

**Cons.** Largest engineering surface. Requires deciding between
"canon emits libro form, batches.yaml accepts libro form" (rewrite
YAML's E1a-E6c filters) and "canon accepts both, normalizes to
flat-art" (extra normalization layer). Touches the most files.
Highest risk of regressing the 754 already-verified Phase A/B/C/D
norms.

### Recommendation

**Path A.** Smallest engineering surface that resolves all the gaps
permanently and keeps the master plan §8 priority order (CST first)
intact. The brief edits are mechanical (find/replace `libro.` →
`art.`, `sentencia.cc.c-` → `sent.cc.C-`, drop `.legislativo`); the
canon extensions are small and parallel to existing `_rule_concepto` /
`_rule_resolucion` patterns. Total: ~½ day of code + ~½ day of brief
revision before scrape/parse work begins.

---

## 5. If Path A is chosen — ordered checklist

Items 1-4 happen before any scraper code runs.

1. **Brief edits** (no code, ~30 min):
   * 02_dur_1625_renta.md — replace `libro.1.<sub>.<art>` with
     `art.1.<sub>.<art>` everywhere; keep human-readable libro
     metadata in body text.
   * 03_dur_1625_iva_retefuente.md — same, with `art.1.2.*`,
     `art.1.3.*`, etc. as appropriate. **Verify against
     batches.yaml E2a/E2b/E2c — there are NO `art.2.*` rows there;
     all DUR 1625 patterns are `art.1.*`. The brief's claim that
     Libro 2 = `decreto.1625.2016.art.2.*` may be wrong; investigate.**
   * 04_dur_1625_procedimiento.md — same.
   * 05_dur_1072_laboral.md — replace `libro.<L>.parte.<P>.titulo.<T>.art.<art>`
     with `art.<L>.<P>.<T>.<art>`. The YAML's E6/J8 patterns are
     `decreto.1072.2015.art.2.2.<X>.` — verify the libro→art
     mapping.
   * 06_decretos_legislativos_covid.md — drop `.legislativo` segment.
   * 10_jurisprudencia_cc_ce.md — `sent.cc.C-<NUM>.<YEAR>`,
     `sent.ce.<NUM>.<YEAR>.<MM>.<DD>`, `auto.ce.<NUM>.<YEAR>.<MM>.<DD>`.

2. **Canon extensions** (~3-4 hours; one PR; tested via tests/test_canon.py):
   * `_rule_cst` — parses `Art. <N> CST` / `Artículo <N> CST` /
     `cst.art.<N>` mentions; emits `cst.art.<N>`.
   * `_rule_cco` — parses `Art. <N> CCo` / `Artículo <N> Código de
     Comercio`; emits `cco.art.<N>`.
   * `_rule_dcin` — parses `DCIN-83 capítulo <C> numeral <N>`;
     emits `dcin.83.cap.<C>.num.<N>`. (Currently the only DCIN —
     scope to that.)
   * `_rule_oficio` — split from `_rule_concepto`. Mention shape
     `Oficio DIAN <NUM> de <YEAR>` → `oficio.dian.<NUM>.<YEAR>`.
     Concepto stays year-less per current grammar.
   * `_NORM_ID_PATTERNS` — add four new regex entries.
   * `_MENTION_FINDERS` — add four new finders (CST, CCo, DCIN,
     oficio-with-year).
   * `display_label` + `norm_type` — add cases.
   * `tests/test_canon.py` — round-trip + finder coverage for each
     new family.

3. **Auto CE date decision** (~30 min discussion; pick one):
   * Option (a): keep canon's date requirement; brief 10's auto.ce
     fixtures emit YYYY.MM.DD from CE relatoria date metadata.
   * Option (b): relax canon to accept dateless `auto.ce.<NUM>.<YEAR>`;
     update batches.yaml's I4 pattern; doc-decision in canon.py.
   * Recommend (a). Autos in CE relatoria always carry a date; absent
     dates are a parsing miss, not a canon flexibility.

4. **Smoke verification** (~10 min):
   * Re-run the §6.3 batch-slice check from the master plan against an
     **empty** input_set.jsonl to confirm canon extensions don't
     regress existing slices (E1a-E6c and J1-J4 should now be
     parseable shapes; the test still expects them to resolve to 0
     until corpus rows land).
   * Run `tests/test_canon.py` — must pass.

5. **THEN start brief 11** (smallest, fully unblocked, ~80 norms,
   validates the body-text-discovery pipeline end-to-end).

6. **Then briefs 07, 08, parts of 12** — also unblocked (or
   unblocked-after-edit).

7. **Then 02/03/04/05/06** (DUR-family — share parser per state file
   §6 dependency graph).

8. **Then 01 (CST), 09 (oficios), 10 (jurisprudencia), 12 remaining**
   — leverage the new canon rules.

9. **Then re-run canonicalizer campaign** for Phases E-K per fixplan_v4
   §6 quick-start. ~10 hours wall, ~$6 DeepSeek.

---

## 6. What this reconciliation does NOT change

* Master plan `corpus_population_plan.md` §8 priority order remains
  correct — labor first, then conceptos, then resoluciones, then DUR.
  Path A only changes the *prerequisite engineering* before that
  ordering kicks in.
* The 754 already-verified Phase A-D norms are unaffected. Their
  shapes (`et.art.*`, `ley.*`, `decreto.<NUM>.<YEAR>` flat,
  `sent.cc.C-*`) are all already canon-compliant; they predate this
  doc.
* The `parsed_articles.jsonl` schema (article_key, body, source_url,
  fecha_emision, emisor, tema) is fine. The `norm_id` field can stay
  for human readability and future tooling — it's just not what
  drives the input set today.
* `vigencia_extractor.py`, `ingest_vigencia_veredictos.py`, and the
  Falkor sync are fine. They consume canonical ids, they don't
  produce them.
* The harness's `extract_vigencia.py --batch-id <X>` flow doesn't
  change. Only the inputs (input_set.jsonl content) change.

---

## 7. Definition of done for this reconciliation

Done when **any one** of:

* (a) Path A executed: briefs 02-06 + 10 edited; canon extended for
  cst, cco, dcin, oficio; tests pass; smoke check confirms slices
  are parseable.
* (b) Path B executed: briefs 02-06 + 10 edited; briefs 01 + 09 +
  parts of 12 explicitly deferred in the state file with rationale.
* (c) Path C executed: canon extended to accept libro-form shapes;
  briefs unchanged; YAML or canon normalization layer reconciled.
* (d) Operator vetoes all three; this file documents the decision and
  the corpus campaign halts at 754 verified norms (path (b) of fixplan_v4
  §10).

When done, this file's status moves from "Open" to "Resolved (Path X
chosen on YYYY-MM-DD)" with a one-line rationale at the top.

---

*Reconciliation drafted 2026-04-28 by claude-opus-4-7 after the 12
briefs landed in `docs/re-engineer/corpus_population/` and the canon
grammar was audited against the briefs and `batches.yaml`.
**Operator: pick Path A, B, or C before scrape/parse work begins.***
