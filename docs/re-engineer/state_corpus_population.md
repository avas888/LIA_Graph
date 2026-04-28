# State — Corpus Population (Phases E–K)

> **Document type.** Live progress tracker for the corpus population effort
> documented in `corpus_population_plan.md`.
>
> **Update cadence.** §4 is updated whenever a brief advances or its blockers
> change. §10 is append-only — every meaningful action gets a timestamped entry.
>
> **Authority.** This file tracks state. The master plan defines scope. Briefs
> in `corpus_population/` define per-source work. Don't change scope here;
> change it in the master plan and update §3 here to reflect.

---

## 1. How to use this file

This file exists so that any human or LLM picking up the corpus population
work can answer four questions in under 60 seconds:

1. **Where are we?** — §3 (global state) and §4 (per-brief table)
2. **What's blocking us?** — §4 "Blockers" column + §5 (recovery playbooks)
3. **What did we just do?** — §10 (run log, most recent entries)
4. **What should I do next?** — §3 "Next action" + §4 status filter

Update protocol:

- When you start a brief, set its status from 🟡 → 🔵 in §4.
- When you finish a brief and the smoke check passes (§9 of master plan), set status to ✅.
- When you hit a blocker, add a row to §10 and update the brief's "Blockers" column.
- When the global state changes (e.g. a phase becomes unblocked), update §3.

---

## 2. Fresh-LLM preconditions

If you are an incoming agent and this is your first contact with the corpus
population work, read in this order:

1. `corpus_population_plan.md` — **the master plan, full read.** Especially §4 (per-phase requirements), §5 (norm-id grammar), §6 (deliverables), §7 (scraper gaps), §8 (priority order), §9 (definition of done).
2. `corpus_population/<NN>_<source>.md` — the brief for whatever you're working on.
3. This file — §3, §4, §10.

If you are touching a brief whose status is 🔵 (in progress), check §10 for the most recent run-log entry on that brief and check the "Owner" column in §4 to avoid stepping on another agent.

---

## 3. Current global state

**As of:** 2026-04-28 04:30 AM Bogotá

| Field | Value |
|---|---|
| Verified vigencia rows in Postgres | **754** (Phases A–D) |
| Target after Phases E–K | **~3,400** |
| Briefs drafted | **12 of 12** |
| Briefs ingested (✅) | **3 of 12** (briefs 11, 01, 08-G1) |
| Briefs in progress (🔵) | **0 of 12** |
| Briefs blocked | **0 of 12** |
| Scraper gaps open | **5** (see §7 of master plan) |
| Compute budget remaining | **~$6** of DeepSeek-v4-pro (within May 5 discount window) |
| Wall-time budget | **~10 hours** at 6 concurrent + 80 RPM |

**Next action.** Assign owners to the priority-1 briefs (§8 of master plan):
**01_cst.md** and **11_pensional_salud_parafiscales.md** unlock the labor regime
(~250 norms). The CST brief is gated by Gap #4 (Senado-style scraper extension)
— the assigned owner should choose between scraper extension and fixture-only
path before starting.

**Recommended sequence for the first sprint:**

1. Assign + ship **11_pensional_salud_parafiscales.md** first — no scraper work,
   just parsed articles. Validates end-to-end pipeline on a small batch (~80 norms).
2. Then **01_cst.md** — same parsing pattern but new scraper. ~170 norms. If
   fixture-only path is chosen, this becomes 4-6 hours of mechanical work.
3. Then **08_conceptos_dian_unificados.md** — ~390 norms; numeral-splitting is
   the technical risk; warrants a small pilot on G6 (already done as fixture)
   to validate the approach before tackling G1–G5.
4. Then **07_resoluciones_dian.md** — ~140 norms; smallest add per phase;
   scraper works today.

After those four briefs land, the corpus jumps from 754 → ~1,500 verified
norms (~44% of target).

---

## 4. Per-brief table

Status legend: 🟡 not started · 🔵 in progress · ✅ ingested · ⛔ blocked

| # | Brief | Phase batches | Target norms | Scraper status | Status | Owner | Last update | Blockers |
|---:|---|---|---:|---|---|---|---|---|
| 01 | [01_cst.md](corpus_population/01_cst.md) | J1, J2, J3, J4 | ~170 | ❌ Gap #4 | ✅ | claude-opus-4-7 | 2026-04-28 | ingested 200 unique CST articles (50 SUIN duplicates dropped) |
| 02 | [02_dur_1625_renta.md](corpus_population/02_dur_1625_renta.md) | E1a–E1f | ~500 | ✅ DIAN works | 🟡 | unassigned | 2026-04-28 | none — corpus parsing only |
| 03 | [03_dur_1625_iva_retefuente.md](corpus_population/03_dur_1625_iva_retefuente.md) | E2a–E2c | ~280 | ✅ DIAN works | 🟡 | unassigned | 2026-04-28 | depends on parser from brief 02 |
| 04 | [04_dur_1625_procedimiento.md](corpus_population/04_dur_1625_procedimiento.md) | E3a, E3b | ~200 | ✅ DIAN works | 🟡 | unassigned | 2026-04-28 | depends on parser from brief 02 |
| 05 | [05_dur_1072_laboral.md](corpus_population/05_dur_1072_laboral.md) | E6a–E6c, J8a–J8c | ~250 | ✅ DIAN handles URL pattern | 🟡 | unassigned | 2026-04-28 | DIAN URL returned 404 during research; verify primary source before parsing |
| 06 | [06_decretos_legislativos_covid.md](corpus_population/06_decretos_legislativos_covid.md) | E5 | ~30 | ⚠️ Gap #3 | 🟡 | unassigned | 2026-04-28 | Gap #3 (DIAN scraper URL-filename extension; canonical id stays as plain `decreto.<NUM>.<YEAR>`) |
| 07 | [07_resoluciones_dian.md](corpus_population/07_resoluciones_dian.md) | F1, F2, F3, F4 | ~140 | ✅ DIAN works | 🟡 | unassigned | 2026-04-28 | none |
| 08 | [08_conceptos_dian_unificados.md](corpus_population/08_conceptos_dian_unificados.md) | G1–G6 | ~390 | ✅ DIAN works | ✅ (G1) | claude-opus-4-7 | 2026-04-28 | G1 ingested (407 IVA numerales). G2–G5: expert delivered placeholder Renta concepto with 0 numerales — needs follow-up. |
| 09 | [09_conceptos_dian_individuales.md](corpus_population/09_conceptos_dian_individuales.md) | H1, H2, H3a, H3b, H4a, H4b, H5, H6 | ~430 | ⚠️ Gap #2 | 🟡 | unassigned | 2026-04-28 | Gap #2 (oficio.dian.* scraper case) + YAML regex tightening required |
| 10 | [10_jurisprudencia_cc_ce.md](corpus_population/10_jurisprudencia_cc_ce.md) | I1–I4 | ~70 | ⚠️ Gap #1 | 🟡 | unassigned | 2026-04-28 | I1 ✅ done; I2/I3 need parsed sentencias; I4 blocked by Gap #1 (Auto CE scraper) |
| 11 | [11_pensional_salud_parafiscales.md](corpus_population/11_pensional_salud_parafiscales.md) | J5, J6, J7 | ~80 | ✅ DIAN ley.* works | ✅ | claude-opus-4-7 | 2026-04-28 | ingested 442 rows (439 articles + 3 parents) |
| 12 | [12_cambiario_societario.md](corpus_population/12_cambiario_societario.md) | K1, K2, K3, K4 | ~150 | ❌ Gaps #4, #5 | 🟡 | unassigned | 2026-04-28 | Gap #4 (CCo) + Gap #5 (BanRep). K4 (~25 norms) unblocks today; K1/K2/K3 need scraper work or fixtures |

**Roll-up:**

- **Unblocked, ready to start (no scraper work needed):** briefs 02, 03, 04, 05, 07, 08, 11 → ~1,840 norms
- **Partially blocked (scraper extension needed):** briefs 06, 09, 10 → ~530 norms
- **Heavily blocked (new scraper or fixture-only):** briefs 01, 12 → ~320 norms

---

## 5. Recovery playbooks

### 5.1 Corpus row corruption — bad `norm_id` rejected by writer

**Symptom.** `ingest_vigencia_veredictos.py` logs `errors_invalid_id` > 0 with
messages like `canonicalize('xyz') != 'xyz'`.

**Recovery.**

1. Identify the offending row(s) in `artifacts/parsed_articles.jsonl` via the
   error log.
2. Run the round-trip validator from master §6.1 against the file to surface
   all bad rows at once.
3. Fix the `norm_id` field in-place. Common fixes:
   - Lowercase the parent prefix; uppercase sentencia type letters.
   - Replace `_` with `-` in compound article numbers (`art.555_2` → `art.555-2`).
   - **Sentencia CC:** prefix `sent.cc.` (not `sentencia.cc.`); type letter uppercase (`sent.cc.C-481.2019`).
   - **Sentencia CE:** keyed by radicado-number + decision date (`sent.ce.<NUM>.<YEAR>.<MM>.<DD>`), not by sección.
   - **Auto CE:** date in `YYYY.MM.DD` is required (`auto.ce.082.2026.04.15`, not `auto.ce.082.2026`).
   - **DUR articles:** flat shape `decreto.<NUM>.<YEAR>.art.<dotted-decimal>`; do not encode libro/parte/título as id segments.
   - **Decretos legislativos:** canonical id is plain `decreto.<NUM>.<YEAR>` (no `.legislativo` segment).
4. Re-run the input-set builder + smoke check (master §6.2, §6.3).
5. Add an entry to §10 documenting what was wrong and what was fixed.

### 5.2 Phase resolves to 0 norms despite ingest

**Symptom.** Brief is marked ✅ but the smoke check still reports 0 norms for
its batches.

**Recovery.**

1. Open `evals/vigencia_extraction_v1/input_set.jsonl` and grep for the
   canonical prefix the brief targeted (e.g. `decreto.1625.2016.art.1.5.`).
2. If 0 matches: the input-set builder didn't pick up the new rows. Re-run
   master §6.2 and confirm the file's mtime advanced.
3. If matches > 0 but the YAML batch still resolves to 0: the YAML's
   `norm_filter` doesn't match the canonical prefix shape used in the corpus.
   Compare the brief's `Canonical norm_id shape` against the YAML — they must
   agree byte-for-byte on the prefix.
4. If both look right but the slice still resolves empty, run
   `_resolve_batch_input_set` directly with `print()` debugging on the regex
   match step.

### 5.3 Scraper drift — source URL changed

**Symptom.** Live fetch returns 404 or HTML structure differs from what the
parser expects.

**Recovery.**

1. Confirm the URL via WebSearch / browsing the source's index page.
2. If the URL pattern changed (e.g. DIAN renamed a normograma file), update
   the scraper's `_resolve_url` function.
3. If the HTML structure changed (e.g. anchor tags renamed), update the
   parser's section-detection logic.
4. **Do not** silently fall back to a cached older version — note the drift
   in §10 and decide whether to re-parse from the new source or pin to the
   cached version with a date stamp.

### 5.4 Gemini/DeepSeek emit non-canonical ids

**Symptom.** Many veredictos rejected at write time because the LLM produced
ids the prompt said to canonicalize but didn't.

**Recovery.**

1. Confirm the prompt explicitly references the §0.5 grammar and gives a
   round-trip example. (It should, after the D5 fix.)
2. Reduce the temperature on the affected provider.
3. If the model can't be coerced, add a post-LLM canonicalization pass in
   `extract_vigencia.py` that rewrites obviously-fixable ids (uppercase →
   lowercase, missing court prefix → add). Reject the rest hard.

### 5.5 Wall-time runaway

**Symptom.** Campaign hours exceed 12, well past the 10-hour budget.

**Recovery.**

1. Check pool-maintainer logs — are workers stuck in a retry loop?
2. Check DeepSeek RPM — if at the 80 RPM ceiling, throttle is normal and the
   only fix is more concurrency (which costs money).
3. Check for a single batch hogging the queue — sometimes one massive batch
   (e.g. G2 with 100+ numerales) needs to be split.
4. Worst case: kill the campaign, ingest what's verified so far, mark partial
   completion in §3, plan a follow-up run.

---

## 6. Brief sequencing dependencies

Some briefs share work or unlock others. Document the dependency graph here so
the next agent doesn't re-do shared work:

```
                                        ┌─────────────────────────┐
                                        │ 02_dur_1625_renta.md    │
                                        │ (DUR parser canonical)  │
                                        └────────┬────────────────┘
                                                 │ shares parser
                          ┌──────────────────────┼──────────────────────┐
                          ▼                      ▼                      ▼
        ┌────────────────────────┐  ┌────────────────────────┐  ┌──────────────────────┐
        │ 03_dur_1625_iva_      │  │ 04_dur_1625_           │  │ 05_dur_1072_         │
        │   retefuente.md       │  │   procedimiento.md     │  │   laboral.md         │
        │ (Libro 2)             │  │ (Libro 3)              │  │ (different DUR but   │
        └────────────────────────┘  └────────────────────────┘  │  same DIAN scraper) │
                                                                 └──────────────────────┘

        ┌────────────────────────┐
        │ 01_cst.md             │ — Gap #4 (Senado-style scraper)
        │ (CST articles)        │ ◀───── shares scraper work with K3 in brief 12
        └────────────────────────┘

        ┌────────────────────────┐
        │ 08_conceptos_dian_    │ ◀───── pilot on G6 (already fixtured) before
        │   unificados.md       │         starting G1–G5; numeral-splitting parser
        │ (numeral-splitting)   │         is the technical risk
        └────────────────────────┘

        ┌────────────────────────┐
        │ 09_conceptos_dian_    │ ◀───── depends on YAML H-batch regex tightening
        │   individuales.md     │         (called out in brief; NOT a separate task)
        └────────────────────────┘
```

Practical implication:

- **Brief 02 should land before 03 + 04** (parser reuse). Same person ideally
  ships all three back-to-back.
- **Brief 08's G6 pilot validates the numeral parser** — if it fails, G1–G5
  shouldn't start until the parser is fixed.
- **Brief 01 and brief 12's K3 share Gap #4.** If brief 01's owner builds the
  Senado-style scraper, K3 inherits it for free.

---

## 10. Run log (append-only)

**Format:** `YYYY-MM-DD HH:MM TZ — <brief or global> — <event>`

---

**2026-04-28 (PM) Bogotá — brief 08 — ingested 408 rows (G1 IVA Unificado complete).**
Concepto General Unificado IVA — 0001 de 2003 fully parsed (1 parent + 406
numerales + 1 second-parent for Concepto 0001/2018). Expert noted Concepto
0001/2018 (Renta) had 0 numerales delivered — placeholder. G2/G3/G4/G5 stay
🟡 pending follow-up delivery. G6 acid test continues to PASS via existing
fixture (5 ids).
*Two related changes shipped in this commit:*
* `src/lia_graph/canon.py` — extended decreto, resolución, and
  concepto/oficio mention-finder regexes with the same optional-art /
  optional-numeral group the ley finder already had. Without this,
  article-level decreto / resolución ids and numeral-level concepto ids
  never reach the input set (find_mentions only captured the parent
  span). Tests: 118/118 still passing.
* `config/canonicalizer_run_v1/batches.yaml` — G1 placeholder regex
  `^concepto\.dian\.001\.2003` (which canon never matched) replaced with
  `^concepto\.dian\.0001-2003(\.|$)` to align with the canonical form
  produced by `_make_parent_row` + the numeral handler.
parsed_articles 8564 → 8972; input set 12 547 → 14 622 unique norm_ids.
Smoke G1=407/60 PASS, G6=5/1 PASS.

**2026-04-28 (PM) Bogotá — brief 01 — ingested 200 CST articles.**
SUIN-Juriscol delivery had 250 article-headings but 50 were repeats (same
article rendered multiple times across SUIN HTML segments) — dedup keeps
first occurrence. Smoke check J1-J4 PASS at all thresholds: J1=29/25,
J2=51/40, J3=44/35, J4=77/60. parsed_articles 8364 → 8564. CST has no
parent norm_id in canon (only `cst.art.<N>`); J1-J4 are regex-filtered on
article number ranges so no parent row needed.

**2026-04-28 (PM) Bogotá — brief 11 — ingested 442 rows (3 parent + 439 articles).**
Expert delivered Ley 100/1993 (289 articles), Ley 789/2002 (59 articles), Ley
2381/2024 (91 articles) via DIAN normograma + SUIN + Función Pública. Built
`scripts/canonicalizer/ingest_expert_packet.py` (unified parser for all 12
brief shapes). Round-trip validation: 0 hard rejects across 442 rows. Each
parent ley gets one parent row (`ley.<NUM>.<YEAR>`) so the YAML's
`explicit_list` filter for J5/J6/J7 resolves cleanly. Per-row body carries a
`[CITA: Ley NNN de YYYY, Artículo X]` prefix so `canon.find_mentions()`
picks each row up. Smoke check J5/J6/J7: 3/3 explicit-list ids resolve in the
input set (full match — the YAML's filter is parent-level, not article-level;
the master plan's "target 30/25/20" refers to vigencia history rows the
canonicalizer will produce downstream when it iterates each parent's
articles). `parsed_articles.jsonl` 7922 → 8364 rows; input set 12 366 unique
norm ids.

**2026-04-28 14:00 Bogotá — global — Canonical-id reconciliation edits applied.**
Per `corpus_population_brief_edits.md` §3, every brief now uses a norm_id shape
that round-trips through `lia_graph.canon.canonicalize`. Edits below.

**2026-04-28 14:00 Bogotá — master plan — §3, §4, §5, §7 reconciliation.**
§5 grammar table: dropped `decreto.legislativo.*` row; flattened DUR sub-unit
shape from `decreto.<NUM>.<YEAR>.libro.<L>.parte.<P>.titulo.<T>.art.<X>` to
`decreto.<NUM>.<YEAR>.art.<dotted-decimal>`; sentencia CC prefix `sentencia.cc.`
→ `sent.cc.` with uppercase TYPE; sentencia CE re-keyed from
`sentencia.ce.<SECCION>.<RADICADO>` to `sent.ce.<RADICADO-NUM>.<YEAR>.<MM>.<DD>`;
auto CE date now required in `YYYY.MM.DD` form. §3.3 rejection table updated.
§4 phase descriptions updated to match. §7 Gap #3 description rewritten:
the gap is about URL filename, not canonical id family.

**2026-04-28 14:00 Bogotá — brief 02 — canonical-id edits applied per spec §3.2.**
DUR 1625 Libro 1 norm_id shape `decreto.1625.2016.libro.1.<sub>.<art>` → flat
`decreto.1625.2016.art.<dotted-decimal>`. All examples and smoke verification
updated.

**2026-04-28 14:00 Bogotá — brief 03 — canonical-id edits applied per spec §3.3.**
DUR 1625 Libro 2 (IVA + retefuente) norm_id shape `libro.2.*` → flat `art.*`.
Clarification paragraph added: "Libro 2" is a human label; canonical maps to
`art.1.3.*` (IVA) and `art.1.2.4.*` (retefuente). Parsing-strategy filter
updated to dual-prefix startswith().

**2026-04-28 14:00 Bogotá — brief 04 — canonical-id edits applied per spec §3.4.**
DUR 1625 Libro 3 (procedimiento + sanciones) norm_id shape `libro.3.*` → flat
`art.1.5.*`. Clarification paragraph added.

**2026-04-28 14:00 Bogotá — brief 05 — canonical-id edits applied per spec §3.5.**
DUR 1072 norm_id shape `decreto.1072.2015.libro.<L>.parte.<P>.titulo.<T>.art.<art>`
→ flat `decreto.1072.2015.art.<dotted-decimal>`. Clarification paragraph
added on dotted-decimal encoding (`2.2.4.*` riesgos, `2.2.5.*` SST).

**2026-04-28 14:00 Bogotá — brief 06 — canonical-id edits applied per spec §3.6.**
Decretos legislativos COVID norm_id shape `decreto.legislativo.<NUM>.<YEAR>.art.<X>`
→ plain `decreto.<NUM>.<YEAR>.art.<X>`. URL-filename pattern
`decreto_legislativo_<NUM>_<YEAR>.htm` preserved (handled by scraper, not
encoded in id). Gap #3 description rewritten.

**2026-04-28 14:00 Bogotá — brief 09 — clarification paragraph added per spec §3.8.**
Concepto vs Oficio distinction now explicit. No id-shape edits required (already
canonical).

**2026-04-28 14:00 Bogotá — brief 10 — canonical-id edits applied per spec §3.7.**
Sentencia CC: prefix `sent.cc.` with uppercase TYPE. Sentencia CE: re-keyed by
radicado-number + decision date (`sent.ce.<NUM>.<YEAR>.<MM>.<DD>`), no sección
in id. Auto CE: date in `YYYY.MM.DD` now required. Gap #1 description updated
to emphasize the four-part canonical id.

**2026-04-28 14:00 Bogotá — brief 12 — clarification paragraphs added per spec §3.9.**
BanRep articulación + CCo numbering paragraphs added. No id-shape edits required
(already canonical).

**2026-04-28 (afternoon) Bogotá — engineer — Canon extension for cst/cco/dcin/oficio shipped.**
`src/lia_graph/canon.py` extended with `_rule_cst`, `_rule_cco`, `_rule_dcin`,
`_rule_oficio` (year-mandatory, runs before `_rule_concepto` to preserve no-year
backward compat). Four new `_NORM_ID_PATTERNS` entries + four new `_MENTION_FINDERS`.
`display_label` and `norm_type` updated. `tests/test_canon.py` gained 44 new test
cases (round-trip, free-text canonicalize, display_label, norm_type, find_mentions).
Full canon suite: 118/118 passing — zero regression on the 74 pre-existing tests.

**2026-04-28 (afternoon) Bogotá — engineer — Hallucinated examples in spec + briefs fixed.**
Audit found `decreto.1625.2016.art.1.5.2.125-A` (canon rejects letter-suffix on
DUR articles) plus several illustrative-only article numbers / oficio numbers /
sentencias that the original brief-edit spec had presented as if real. Fixed
brief 04 (used digit suffix `-1` instead of `-A`); replaced illustrative concrete
ids in briefs 02, 03, 04, 05, 06, 09, 10, 12 with either (a) verified-real ids
copied from `batches.yaml` explicit_lists, or (b) clearly-marked
`<dotted-decimal>` placeholders with explicit instructions to read real numbers
off the gov.co source. Master spec `corpus_population_brief_edits.md` got a
prominent §3 caveat. Memory `feedback_no_hallucinated_examples.md` written so
this doesn't recur. Validation: 36/36 verified-real examples round-trip cleanly.

**2026-04-28 (afternoon) Bogotá — global — Reconciliation closed.**
Briefs ↔ canon ↔ `batches.yaml` are now in agreement. All 12 briefs are docs-ready
for the corpus-ingestion campaign. Per-brief table §4 stays 🟡 because no rows
have been ingested yet; the next move is to assign owners per master §8 priority
order and start brief 11 (Ley 100/789/2381, ~80 norms, smallest unblocked) as
the pipeline-validation pilot.

**2026-04-28 03:00 AM Bogotá — global — Master plan drafted.**
`corpus_population_plan.md` written. Documents the 754 → ~3,400 norm gap and
catalogs the 5 scraper gaps, 12 source briefs, definition of done, and risk
register. Author: claude-opus-4-7.

**2026-04-28 04:00 AM Bogotá — briefs — All 12 source briefs drafted.**
Per master §10.1, briefs 01 through 12 produced in `corpus_population/`. Each
matches the §10.2 skeleton: header / What / Source URLs / Canonical shape /
Parsing strategy / Edge cases / Smoke verification / Dependencies. All status
🟡 (not started). Authored by 5 parallel research agents; verified by spot
check on brief 02. Open questions captured per brief (DUR 1072 URL drift,
DIAN unified-concepto numbers, DCIN-83 numeral granularity, Auto CE id
shape).

**2026-04-28 04:30 AM Bogotá — global — State file initialized.**
This file (`state_corpus_population.md`) created with §1–§6 + this run log.
Per-brief table seeded; all 12 entries 🟡. Ready to assign owners and begin
ingestion sprint.

---

*(Append new entries above this line in reverse chronological order, OR below
in append-only style — pick one convention and stick with it. Reverse-chrono
recommended so the most recent entry is always on top.)*
