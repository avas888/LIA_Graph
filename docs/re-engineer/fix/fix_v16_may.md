# fix_v16_may.md — Playbook Scaling via Expert Brief

> **Author context (zero-agent-context protocol).** This plan is
> self-contained. A fresh LLM agent with no prior conversation history
> can execute it from the file system as-is. Every file path, function
> name, env flag, test name, registry entry, and decision rule is
> specified verbatim. Verify every artifact against `git ls-files`
> before acting. If any cited path or function does not exist, STOP
> and report drift — do not invent.

---

## §0. TL;DR

> **🛑 FIRST TASK FOR ANY AGENT PICKING THIS UP — ship `corpusfix_v1.md`
> BEFORE wiring any new topic batch.** It unblocks 5+ already-FAILed
> probes (the entire exógena family + notificaciones + several
> sanción/devolución playbooks) in one cloud delta sync. Read
> `docs/re-engineer/fix/corpusfix_v1.md` end-to-end; the plan is
> self-contained. Do NOT start batch 6 (or any further topic work) until
> corpusfix_v1 ships, because every new batch you add risks landing on
> top of the same path-based topic-tagging bug and inflating the FAIL
> count for reasons unrelated to the new topic. Concrete sequence:
> (1) extend `_FILENAME_TOPIC_PATTERNS` in
> `src/lia_graph/ingestion_classifier.py` with the §3.1.1 table
> **plus** the new entries in §10b.1–§10b.2 of corpusfix_v1.md;
> (2) `make phase2-graph-artifacts && make phase2-corpus-additive
> PHASE2_SUPABASE_TARGET=production`; (3) restart `npm run dev:staging`;
> (4) re-probe q06–q10 (exógena) + q01_notificaciones via
> `answer-engine-probe`. Only after the pass-rate climbs out of 58 %
> back toward the 75 %+ band, continue with batch 6 per §9.

**Idea.** Scale the v15.5 case-anchor registry from **6 hand-coded
deduction topics** (GMF, ICA, predial, intereses, leasing, primer
empleo) to **~50 topics** spanning deducciones, descuentos
tributarios, tarifas/régimen, procedimiento, IVA, retención en la
fuente, NIIF-fiscal, información exógena, and the full labor/nómina
scope per `project_lia_scope_labor`. Each new topic ships via a
**standardized engineer-side intake** that takes one expert-authored
`.md` playbook and produces (a) a case detector, (b) 5–7 substantive
bullets in `build_recommendations`, (c) an anchor-registry row in
`planner.py`, (d) a search-queries row, (e) a keyword whitelist for
the off-topic filter, (f) a corpus chunk, and (g) tests.

**Why now.** v15.5 validated the registry pattern end-to-end on
2026-05-14 (predial probe went `fail → warn` after a single planner
edit; the other five topics held warn-level on first probe with all
four content criteria met). The bottleneck is no longer architectural
— it is editorial throughput. Per the closing-report
recommendation: *"the cheap win is to keep adding playbooks for the
next 20–30 most-frequent named-topic deduction/beneficio/tarifa
questions. Each one immediately raises answer quality for that
question."*

**Effort.** Per topic: **expert ~2 h** (writing the `.md`) + **engineer
~30–45 min** (extracting + wiring + tests). Across ~50 topics: ~25 h
of engineering work + the expert pipeline.

**Risk.** Low for the engineer-side wiring (additive, flag-able
per-topic via registry order). Medium for editorial drift — handled
by the URL/verification rules in the expert brief and the
acceptance-criteria checklist in §6 below.

---

## §1. Repository state assumed by this plan

Verify these before making changes. If any drift, STOP and report.

### Files that MUST exist

| Path | Purpose | Key symbols this plan references |
|---|---|---|
| `docs/expert_briefs/playbook_generation_brief.md` | Expert-facing brief (Spanish) — what experts produce | sections §3 (template), §4 (GMF worked example), §5 (priority topic list) |
| `src/lia_graph/pipeline_d/case_detectors.py` | Pure case-detector module (no upward deps) | `is_gmf_deduction_case`, `is_ica_deduction_case`, `is_predial_deduction_case`, `is_intereses_deduction_case`, `is_leasing_deduction_case`, `is_primer_empleo_deduction_case` |
| `src/lia_graph/pipeline_d/answer_synthesis_sections.py` | Case bullets + whitelists | `build_recommendations`, `_GMF_CASE_KEYWORDS`, `_ICA_CASE_KEYWORDS`, `_PREDIAL_CASE_KEYWORDS`, `_INTERESES_CASE_KEYWORDS`, `_LEASING_CASE_KEYWORDS`, `_PRIMER_EMPLEO_CASE_KEYWORDS`, `_active_case_keywords`, `_filter_offtopic_bullets_for_case`, `_merge_question_answer_pairs` |
| `src/lia_graph/pipeline_d/answer_synthesis_helpers.py` | Re-exports the detectors so legacy call sites keep working | `from .case_detectors import is_*_deduction_case` block |
| `src/lia_graph/pipeline_d/planner.py` | Case-anchor registry + search-queries registry | `_CASE_ANCHOR_REGISTRY`, `_CASE_SEARCH_QUERIES`, `build_graph_retrieval_plan` |
| `src/lia_graph/pipeline_d/answer_policy.py` | Per-article guidance bullets (generic ICA/GMF/predial map for art. 115) | `ARTICLE_GUIDANCE["115"]` |
| `tests/test_answer_synthesis_gmf_deduction.py` | GMF test template | shape to copy for new topics |
| `tests/test_answer_synthesis_ica_predial.py` | ICA + predial test template | shape to copy |
| `tests/test_answer_synthesis_intereses_leasing_primer_empleo.py` | 3-topic test template | shape to copy |
| `tests/test_planner_case_anchor_registry.py` | Registry-level tests | shape to copy for new registry rows |
| `tests/test_answer_inline_anchors.py` | v15.3 inline-anchor regression suite | must continue passing |
| `.claude/skills/answer-engine-probe/` | Probe skill for staging validation | `references/rubric.md`, `scripts/stage_run.py`, `scripts/probe.py`, `scripts/digest.py`, `scripts/record_verdict.py`, `scripts/write_report.py` |
| `knowledge_base/` | Corpus root — playbooks may also land here as ingested chunks | folder structure varies by category |
| `CLAUDE.md` | Project quickstart | `## Hot Path (main chat)` section, `## Non-Negotiables` |

### Sprint v15.5 ship state (assumed already merged)

- `_CASE_ANCHOR_REGISTRY` lives in `planner.py` with **6 rows**
  (GMF→115, ICA→115+115-1, predial→115, intereses→117+118-1,
  leasing→127-1, primer_empleo→108-5).
- `_CASE_SEARCH_QUERIES` lives in `planner.py` with 6 matching rows
  (each with 2 search queries per case).
- `case_detectors.py` exists and breaks the prior circular import
  (`planner → helpers → support → planner`).
- v15.3 inline-anchor ranking fix is live in
  `answer_inline_anchors.py::select_inline_anchors` (position bonuses
  require any content signal; auto-fallback to `primary[:max_refs]`
  removed).
- v15.2 Q/A merge + off-topic case filter live in
  `answer_synthesis_sections.py::build_recommendations` tail.
- All test files above are green: 121 tests across 7 suites as of
  2026-05-14.

### Sprint v16 b1–b5 ship state (current as of 2026-05-14 evening)

- `CASE_REGISTRY` lives in `src/lia_graph/pipeline_d/case_bullets/__init__.py`
  with **51 rows** across 6 batches (1 row per topic). Each row is a
  `CaseSpec` instance imported from its own sibling file under
  `case_bullets/<topic>.py` — `divide and conquer`, no one file
  exceeds 1000 LOC.
- `case_detectors.py` (683 LOC) holds the v15.5 baseline + b1 + b2
  detectors (21 inline) and re-exports b3+b4+b5 detectors from
  sibling modules `case_detectors_extensions.py` (b3+b4, 552 LOC)
  and `case_detectors_b5.py` (b5, 271 LOC).
- `answer_synthesis_helpers.py` re-exports all 51 detectors so the
  synthesis layer's `_active_case_keywords` helper can iterate them.
- `tests/test_planner_case_anchor_registry.py` has 53 tests
  (registry membership + anchor emission per topic). All green
  2026-05-14.
- `LIA_POLISH_UVT_VALIDATOR=enforce` auto-derives its cue list from
  `CASE_REGISTRY.anchor_articles` so each new topic's anchor
  numbers participate in the structural UVT-fabrication guard
  without manual cue extension.
- `compose_polish_rejected_fallback` (A4 substantive fallback) is
  seeded by `CASE_REGISTRY.bullets` when a detector fires, so the
  registry doubles as the rejected-polish content source.

**Shipped topics by batch:**

| Batch | Topics | New rows |
|---|---|---|
| v15.5 baseline | GMF, ICA, predial, intereses, leasing, primer_empleo | 6 |
| v16 b1 (Renta deducciones) | depreciación, atenciones, cartera, donaciones, pagos_efectivo | 5 |
| v16 b2 (Tarifas + procedimiento + descuentos) | exoneración_parafiscales, IVA AF, CTeI, dividendos PN, RST, zona_franca, tarifa_general_pj, beneficio_auditoría, firmeza, devolución_saldos | 10 |
| v16 b3 (Sanciones + IVA + retención salarios) | sanción_extemporaneidad, sanción_corrección, sanción_inexactitud, notificaciones, IVA responsables, IVA descontable, IVA devolución, IVA excluidos vs exentos, IVA hecho_generador, retención_salarios | 10 |
| v16 b4 (Retención + procedimiento + exógena + NIIF concil.) | retención_servicios, anticipo_renta, soporte_factura, compensación_pérdidas, niif_conciliación, exógena 1001/1003/1005/1007/umbrales | 10 |
| v16 b5 (Tier 2 + NIIF) | INC consumo, precios_transferencia, dividendos_no_gravados, capitalización_utilidades, aportes_pensión, renta_cedular_PN, RTE_ESAL, cláusula_antiabuso, impuesto_diferido, NIIF_ingresos | 10 |
| **Total shipped** | | **51** |

**Probe state across batches** (cumulative through batch-5 retest):

- 52 distinct probes total → **30 PASS · 9 WARN · 13 FAIL**
  (≈58 % pass, ≈75 % pass-or-warn).
- The 13 FAILs concentrate in **two systemic patterns**, NOT in
  one-off topic bugs:
  - **Corpus topic-tag drift** (10 of 13): playbook chunks tagged
    with the wrong canonical topic by the ingestion classifier's
    path/LLM fallback. The five exógena formats + notificaciones
    + sanción × 3 + devolución sit here. Detectors and anchors
    are correct; coherence-gate abstains. Documented and ready
    to ship: `docs/re-engineer/fix/corpusfix_v1.md` (extended
    2026-05-14 with §10b new findings).
  - **Cross-domain anchor mismatch** (3 of 13): a topic's anchor
    lives in a different libro than its router-classified topic.
    Pattern surfaced on q18 cláusula antiabuso (router →
    `procedimiento_tributario`, anchor `art. 869` in renta) and
    q19 impuesto diferido (router → `niif_pymes`, anchor `art. 240`
    in renta). Runtime fix landed 2026-05-14 via
    `config/article_secondary_topics.json` additions for arts.
    28, 240, 869, 869-1, 869-2. Re-probe pending server restart.

### Pending Tier 1 topics (~19 remaining)

The §9 list below names the planned ~50-topic scope. Comparing to
the 51 shipped rows above, **the following Tier 1 topics still
need wiring**:

| Group | Pending |
|---|---|
| Renta deducciones | salario integral (CST 132) |
| Renta descuentos | energías renovables (Ley 1715/2014 art. 11), discapacidad (Ley 361/1997 art. 31), mujeres víctimas (Ley 1257/2008 art. 23), factura electrónica 1 % (Ley 2277/2022 art. 7) |
| Retención fuente | bases mínimas Decreto 572/2025, autoretención Decreto 2201/2016 |
| Labor / nómina | liquidación mensual, cesantías, prima de servicios, vacaciones, indemnización, PILA, UGPP, exoneración parafiscales 114-1, nómina electrónica DSPNE, contrato prestación vs laboral, pagos no constitutivos de salario, desalarización (12 topics, all CST + decretos — see §10 for non-ET anchor handling) |
| **Tier 1 pending** | **~19 topics** |

### Pending Tier 2 (~4 remaining)

10 of the original ~14 Tier 2 topics shipped in batch 5
(precios transferencia, INC consumo, dividendos no gravados,
capitalización, aportes pensión, renta cedular, RTE/ESAL,
cláusula antiabuso, impuesto diferido NIIF, NIIF ingresos).
~4 Tier 2 entries still remain — list in
`docs/expert_briefs/playbook_generation_brief.md` §5 Tier 2.

**Total remaining: ~23 topics** (19 Tier 1 + ~4 Tier 2).

### Handoff for a zero-context agent

If you are picking this up cold, the next concrete deliverables are
listed in **mandatory sequential order**. Do not parallelize step 1
with anything else, and do not skip step 1 to start batch 6 — every
new topic added on top of the current corpus tag drift compounds the
diagnostic load.

1. **🛑 Ship `corpusfix_v1.md` FIRST.** Highest ROI; unblocks 5+ FAILed
   probes in one cloud delta sync. Read
   `docs/re-engineer/fix/corpusfix_v1.md` end-to-end. The plan is
   self-contained; the executing agent only needs to (a) extend
   `_FILENAME_TOPIC_PATTERNS` in `src/lia_graph/ingestion_classifier.py`
   with the §3.1.1 table (including §10b.1's exógena rows), (b)
   `make phase2-graph-artifacts` + `make phase2-corpus-additive
   PHASE2_SUPABASE_TARGET=production`, (c) restart `npm run
   dev:staging`, (d) re-probe q06–q10 + q01_notificaciones via
   `answer-engine-probe` skill.

2. **Verify cross-domain anchor fix landed**. Restart the server,
   re-probe q18 (cláusula antiabuso) and q19 (impuesto diferido).
   Expected: both PASS. If still abstain, check the cache reset
   (kill the python process completely, not just `Ctrl-C` the
   launcher).

3. **Continue topic batches at the same cadence (~10 per sprint)**.
   The pending list above is ordered by priority. The pattern for
   each topic is fixed:

   a. Read the expert playbook brief for the topic (live under
      `/Users/ava-sensas/Library/CloudStorage/Dropbox/AAA_LOGGRO Ongoing/AI/LIA_contadores/Corpus/to_upload_graph/PLAYBOOKS_LIA/aa_Playbook/`).
      One brief = one topic = one new `CaseSpec` row.

   b. **Lane A** — copy the brief's "Plan" / "Mejores Prácticas" /
      "Conceptos Erróneos" / "Casos" content into a markdown
      playbook at:
      - `knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/playbook_renta_<slug>.md`,
        or whichever folder matches the topic's primary domain
        (`IVA_COMPLETO/PLAYBOOKS/`, `LABORAL/PLAYBOOKS/`,
        `estados_financieros_niif/PLAYBOOKS/`, etc.).
      - One playbook = ~80 lines; if a brief is huge, prefer
        compression to splitting (the planner indexes the file as
        one chunk, not by section).

   c. **Lane B** — wire the topic:
      - Add a detector function in `case_detectors_b5.py` (or the
        next b6 file if creating one — same divide-and-conquer:
        ≤1000 LOC per file). Use simple substring markers, and add
        word-boundary regex for tokens ≤4 chars (e.g. `\binc\b`,
        `\brte\b`) to avoid greedy matches inside unrelated words.
        Pre-emptively add veto guards for common cross-topic phrasing
        (e.g. rte_esal vetoes on `donaci`).
      - Re-export the detector in `case_detectors.py` facade.
      - Re-export in `answer_synthesis_helpers.py` import block.
      - Add a new file `case_bullets/<slug>.py` with a `SPEC =
        CaseSpec(...)` row. **Bullets**: 5–7 short bullets,
        verbatim from the brief, with `**bold**` on key UVT
        thresholds + article numbers; do NOT invent UVT/% values
        outside what the brief provides (the polish UVT validator
        will reject inventions).
      - Register the SPEC in `CASE_REGISTRY` inside
        `case_bullets/__init__.py`. Order matters — put
        specific-anchor topics BEFORE broader anchors (e.g. impuesto
        diferido BEFORE niif_conciliación; rte_esal BEFORE
        donaciones) to win the first-match planner anchor emission.

   d. **Tests** — add one test per new topic in
      `tests/test_planner_case_anchor_registry.py` (template: the
      52 existing tests, each asserts the planner emits the topic's
      anchor for a representative question). `PYTHONPATH=src:. uv
      run pytest tests/test_planner_case_anchor_registry.py -q`.

   e. **Cross-domain check** — if the new topic's anchor article
      lives in a different libro than the natural router topic
      (e.g. anchor is in renta, but the topic itself is
      procedimental / NIIF / cambiario), pre-add a row to
      `config/article_secondary_topics.json` mapping the article
      → its `secondary_topics`. Otherwise the coherence gate will
      abstain at runtime (the exact failure mode seen on q18/q19).

   f. **Local artifact rebuild + cloud sync**:
      `make phase2-graph-artifacts && make phase2-corpus-additive
      PHASE2_SUPABASE_TARGET=production`. Idempotent on natural
      keys.

   g. **Restart the dev:staging server** (the user runs `! kill
      $(pgrep -f lia_graph.ui_server) && npm run dev:staging` and
      says "ready"). DO NOT probe before restart — the python
      process holds module-level caches for `CASE_REGISTRY` and
      `_ARTICLE_TOPICS_CACHE`.

   h. **Probe via `answer-engine-probe` skill** — one question per
      new topic + one regression-probe per most-recently-shipped
      topic. Stop on first FAIL, diagnose, re-ship if needed.

4. **Do NOT touch any module file ≥1000 LOC** — always extract into
   a focused sibling and import. Past examples:
   `answer_synthesis_sections.py` → `answer_direct_answers.py`
   carve-out; `case_detectors.py` → `case_detectors_extensions.py`
   → `case_detectors_b5.py` carve-outs.

5. **Update this fix_v16_may.md ship-state table** when each batch
   lands, so the count and the pending list stay accurate.

---

### v15.5 probe run (anchor — recorded outcome)

- Run dir: `tracers_and_logs/logs/probe_runs/20260514T150753Z_deductions_v15/`.
- 6 questions probed, 1 initial fail (predial, wrong-norm-cited),
  fixed by v15.5 registry edit, re-probed → warn.
- Final scoreboard: **0 fails, 6 warns**. Dominant warn pattern:
  retrieval still surfaces Cap V Deducciones chunk (Arts. 121-177-2),
  polish keeps Arts. 121/122 in allowlist and fabricates
  justifications for them. Not a fix_v16 problem — separate
  follow-up (see §11).

---

## §2. Idea (gate 1)

**One-sentence statement:** establish a deterministic two-lane intake
that converts an expert-authored playbook `.md` into (a) one corpus
chunk in `knowledge_base/` (retrieval-time evidence) and (b) one set
of code edits across `case_detectors.py` + `answer_synthesis_sections.py`
+ `planner.py` (deterministic anchor + bullets), with unit tests
mirroring the existing 6-topic suites, gated through the
`answer-engine-probe` skill before merge.

The two lanes are complementary:

- **Lane A — Corpus chunk.** The playbook `.md` is converted to a
  corpus markdown file in `knowledge_base/`, ingested via the existing
  `make phase2-graph-artifacts-supabase` pipeline. This is what makes
  the playbook content available to hybrid_search retrieval and
  through that to the polish prompt.
- **Lane B — Code-side wiring.** Detector + case bullets + registry
  rows. This is what guarantees the right anchor article is pulled
  even if retrieval ranks the wrong chunk first, AND ensures the
  bullets reach `Recomendaciones Prácticas` regardless of polish
  success/failure.

Both lanes are required for every playbook. Lane A alone leaves the
answer dependent on polish + retrieval quality. Lane B alone leaves
the answer thin if polish has nothing else to draw on. The 6 topics
shipped through v15.1–v15.5 used Lane B only; v16 adds Lane A
systematically.

---

## §3. Plan (gate 2 — implementation outline)

### §3.1 Inputs from the expert

The expert delivers one `.md` file conforming to the template in
`docs/expert_briefs/playbook_generation_brief.md` §3. The file
contains exactly these named sections (verbatim Spanish headings):

1. `# [Topic title]`
2. `> [one-line summary, ≤25 words]`
3. `## Cómo lo pregunta un contador` — 8–15 phrases the contador
   would type
4. `## Norma principal` — primary article with URL
5. `## Normas relacionadas` — table of related norms with URLs
6. `## Respuesta operativa` — 5–7 numbered bullets, each a
   complete answer fragment
7. `## Errores comunes en revisión DIAN` — table of error/severity/mitigation
8. `## Qué NO cubre este playbook` — carve-outs
9. `## Vigencia` — modification status + URL
10. `## Fuentes secundarias consultadas` — secondary URLs

The expert file lands in a delivery folder (Dropbox / Drive — confirm
with operator). The engineer copies it to a project-local intake
folder before working on it:

```
docs/expert_briefs/incoming/<filename>.md
```

Folder `docs/expert_briefs/incoming/` should be created on first use:

```
mkdir -p docs/expert_briefs/incoming
```

### §3.2 Lane A — Corpus chunk

Each playbook becomes a corpus markdown file in the appropriate
knowledge_base subdirectory:

```
knowledge_base/<CATEGORY>/PLAYBOOKS/playbook_<topic-kebab-case>.md
```

Category mapping (verify against `git ls-files knowledge_base/`):

| Category in playbook brief | knowledge_base subdir |
|---|---|
| Renta — Deducciones | `knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/` |
| Renta — Descuentos tributarios | `knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/` |
| Renta — Tarifas y régimen | `knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/` |
| Renta — Procedimiento | `knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/` |
| IVA | `knowledge_base/CORE ya Arriba/IVA_COMPLETO/PLAYBOOKS/` |
| Retención en la fuente | `knowledge_base/CORE ya Arriba/RETENCION_FUENTE/PLAYBOOKS/` |
| Labor / Nómina | `knowledge_base/CORE ya Arriba/LABOR_NOMINA/PLAYBOOKS/` (create on first labor playbook) |
| NIIF — Fiscal | `knowledge_base/estados_financieros_niif/PLAYBOOKS/` |
| Información exógena | `knowledge_base/CORE ya Arriba/INFORMACION_EXOGENA_FORMATOS/PLAYBOOKS/` |

If a subdir does not exist, create it with `mkdir -p` before placing
the file.

#### §3.2.1 Frontmatter for ingestion

The corpus ingestion pipeline expects YAML frontmatter at the top of
each corpus markdown file. Verify the exact field set by reading any
file at depth 3 in `knowledge_base/CORE ya Arriba/RENTA/LOGGRO/*.md`
and `head -20 <file>`. Required fields the playbook file must carry:

```yaml
---
source: lia_playbook
source_relative_path: <CATEGORY>/PLAYBOOKS/playbook_<topic>.md
knowledge_class: normative_base  # use 'interpretative_guidance' if the playbook leans on jurisprudence + concepts DIAN rather than article text
topic: <one of the canonical topic keys, see config/subtopic_taxonomy.json>
sub_topic: <optional, see same taxonomy>
titulo: <human-readable title — usually the H1 of the playbook>
norm_anchors:
  - <article_id>  # e.g. "115" or "115-1" or "108-5"
provider_labels:
  - lia_playbook
  - <author handle if available>
trust_tier: high
---
```

The `topic` field MUST match an existing key in
`config/subtopic_taxonomy.json`. Verify with:

```
grep -i '"<candidate_topic>"' config/subtopic_taxonomy.json
```

If the candidate topic does not exist, route to the closest existing
parent (e.g. `costos_deducciones_renta`, `ica`, `iva`,
`nomina_general`, `retencion_fuente`, `informacion_exogena`).
Do NOT add a new top-level topic in this plan — that is a separate
fix.

#### §3.2.2 Content shape inside the corpus file

After the frontmatter:

1. The H1 from the expert's playbook (the topic name).
2. The one-line summary as the first paragraph.
3. The expert's `## Respuesta operativa` section verbatim — these
   are the bullets retrieval will surface.
4. The `## Normas relacionadas` table verbatim — gives retrieval the
   alternative articles to cross-reference.
5. The `## Errores comunes` section verbatim — useful for `riesgos`
   bullets in the rendered answer.
6. The `## Fuentes secundarias consultadas` URLs at the bottom.

Do NOT include the `## Cómo lo pregunta un contador` section in the
corpus file — those are detector keywords, consumed by Lane B only.
Including them in the corpus would pollute retrieval with question
phrasings that look like answers.

#### §3.2.3 Re-build artifacts after each batch

After landing 5–10 playbooks in `knowledge_base/`, run:

```
make phase2-graph-artifacts
```

This rebuilds the local artifact bundle in `artifacts/`. For staging,
follow with:

```
make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production
```

Verify the playbook chunks were ingested by querying Supabase:

```
PYTHONPATH=src:. uv run python -c "
from lia_graph.supabase_client import supabase_select
rows = supabase_select(
    'documents',
    columns='doc_id,knowledge_class',
    filters={'doc_id__like': '%PLAYBOOKS%'},
    limit=20,
)
for r in rows:
    print(r['doc_id'], r['knowledge_class'])
"
```

### §3.3 Lane B — Code-side wiring

For each playbook, perform the following five edits, in order.

#### §3.3.1 Add the case detector

File: `src/lia_graph/pipeline_d/case_detectors.py`

Pattern (copy the shape of `is_gmf_deduction_case`):

```python
def is_<topic>_case(normalized_message: str) -> bool:
    """v16.X (YYYY-MM-DD) — detect <topic> queries.

    [One-line description of what the detector fires on.
     Reference the playbook file in `knowledge_base/.../PLAYBOOKS/`
     so future readers can find the source of truth.]
    """
    if not normalized_message:
        return False
    markers = (
        # Lifted from the expert's `## Cómo lo pregunta un contador`
        # section in playbook_<topic>.md. Normalize:
        #   - lowercase
        #   - strip accents (NFC → ASCII via unidecode-like rule)
        #   - keep multi-word phrases as-is
        "<phrase 1>",
        "<phrase 2>",
        ...
    )
    return any(marker in normalized_message for marker in markers)
```

**Detector engineering rules (apply to every new detector):**

- **Word-boundary guard for short tokens.** If the topic has an
  ambiguous short token (e.g., `ica` matches `indica` / `publicar`),
  use `re.search(r"\b<token>\b", normalized_message)` instead of
  `in`. Reference: `is_ica_deduction_case` in `case_detectors.py`.
- **Combined-keyword path for phrasings the literal list misses.**
  If the topic has both a name and a verb form (e.g. "intereses" +
  "deducible/deducir/deducción"), add a secondary branch:

  ```python
  if "<topic_noun>" in normalized_message and any(
      verb in normalized_message
      for verb in ("deducible", "deducción", "deduccion", "deducir")
  ):
      return True
  ```

  Reference: `is_intereses_deduction_case` second branch in
  `case_detectors.py`.
- **No imports from `answer_*` modules.** `case_detectors.py` must
  stay pure (only `re` + types). Importing anything from
  `answer_support` / `answer_synthesis_helpers` / `planner` will
  reintroduce the circular import that v15.5 broke. CI must catch
  this — see test in §3.3.5.
- **Append `__all__` entry** for the new detector.

After adding, **also re-export from `answer_synthesis_helpers.py`**
(legacy callers depend on the re-export path):

```python
# in src/lia_graph/pipeline_d/answer_synthesis_helpers.py
from .case_detectors import (
    is_gmf_deduction_case,
    ...
    is_<new_topic>_case,  # ADD HERE
)
```

#### §3.3.2 Add the case bullets in `build_recommendations`

File: `src/lia_graph/pipeline_d/answer_synthesis_sections.py`

Find `def build_recommendations`. The body has a sequence of
`if is_<topic>_case(normalized_message):` branches in this order
(verbatim, as of v15.5):

1. `is_gmf_deduction_case`
2. `is_ica_deduction_case`
3. `is_predial_deduction_case`
4. `is_intereses_deduction_case`
5. `is_leasing_deduction_case`
6. `is_primer_empleo_deduction_case`
7. `is_loss_compensation_case` (older — keep order)
8. `is_refund_balance_case` (older — keep order)

Insert the new branch **immediately after the existing case branch in
its category** (deducciones together, etc.) and **before
`is_loss_compensation_case`**. Pattern (copy the shape of the GMF
branch):

```python
# v16.X (YYYY-MM-DD) — <topic> case.
# Bullet content grounded in:
#   * docs/expert_briefs/incoming/playbook_<topic>.md
#   * knowledge_base/<CATEGORY>/PLAYBOOKS/playbook_<topic>.md
# All numeric facts, articles, and percentages verified against the
# expert-authored playbook and its cited norms before landing.
if is_<topic>_case(normalized_message):
    append_unique(
        lines,
        "<bullet 1 verbatim from playbook ## Respuesta operativa>",
    )
    append_unique(
        lines,
        "<bullet 2 verbatim from playbook ## Respuesta operativa>",
    )
    ...
```

**Bullet extraction rules:**

- Take all 5–7 bullets from the expert's `## Respuesta operativa`
  section verbatim. Do not rewrite or summarize.
- Each bullet ≤ 280 chars (per
  `clean_support_line_for_answer` truncation; bullets longer than
  this risk being chopped mid-sentence by the rendering chain).
- Bold the subtitle prefix where the playbook uses one (e.g.
  `**Tip de planeación:**`). The `_merge_question_answer_pairs`
  tail helper in `build_recommendations` recognizes
  `_SUBTITLE_PREFIX_RE` matches and protects them from accidental
  merging.
- If a bullet is > 280 chars, ask the expert to tighten it OR split
  it into two bullets — do NOT chop it engineer-side.

#### §3.3.3 Add the case keyword whitelist

File: `src/lia_graph/pipeline_d/answer_synthesis_sections.py`

Find the existing whitelist block (search for `_GMF_CASE_KEYWORDS`).
Append:

```python
_<TOPIC>_CASE_KEYWORDS: tuple[str, ...] = (
    # Topic-name variants
    "<topic noun>", ...,
    # Anchor article numbers (digits only, both formats)
    "<article number>", "<article number with dash>",
    # Deducción mechanics tokens that survive the off-topic filter
    "deducir", "deducible", "deducción", "deduccion",
    "depuración", "depuracion",
    "causa", "causación", "causacion", "causalidad",
    # Topic-specific operative tokens (e.g. for predial: "inmueble",
    # "bodega", "oficina"; for leasing: "canon", "arrendatario",
    # "arrendador")
    "<token 1>", "<token 2>", ...,
)
```

**Whitelist engineering rules:**

- Include both accented and unaccented forms ("deducción",
  "deduccion") — `anchor_query_tokens` strips accents in some paths,
  not others.
- Include digit variants (`"115"`, `"115-1"`) so retrieval/filter
  pass through bullets that mention the article.
- Avoid generic tokens that would let through any deducción-related
  bullet — that defeats the off-topic filter's purpose.
- Length target: 20–35 tokens per whitelist. The 6 existing
  whitelists range from 22 (`_PREDIAL_CASE_KEYWORDS`) to 33
  (`_LEASING_CASE_KEYWORDS`).

#### §3.3.4 Append to `_active_case_keywords`

File: `src/lia_graph/pipeline_d/answer_synthesis_sections.py`

Find `def _active_case_keywords`. Add the new detector after the
existing ones (order matches `build_recommendations`):

```python
def _active_case_keywords(normalized_message: str) -> tuple[str, ...]:
    keywords: list[str] = []
    if is_gmf_deduction_case(normalized_message):
        keywords.extend(_GMF_CASE_KEYWORDS)
    ...
    if is_<topic>_case(normalized_message):  # ADD HERE
        keywords.extend(_<TOPIC>_CASE_KEYWORDS)
    return tuple(keywords)
```

#### §3.3.5 Add the registry rows in `planner.py`

File: `src/lia_graph/pipeline_d/planner.py`

Find `_CASE_ANCHOR_REGISTRY` (top of module, after the imports).
Append a row:

```python
_CASE_ANCHOR_REGISTRY: tuple[tuple[object, tuple[str, ...], str], ...] = (
    (is_gmf_deduction_case,          ("115",),         "gmf_deduction_anchor"),
    ...
    (is_<new>_case,                  ("<art>",),       "<new>_deduction_anchor"),  # ADD
)
```

**Anchor row engineering rules:**

- The article tuple lists the **primary norm(s)** from the
  playbook's `## Norma principal` plus any inciso-specific norm
  (e.g. `("115", "115-1")` for ICA covers both the deducción and
  the descuento-tributario alternative).
- DO NOT include `## Normas relacionadas` here — those go into the
  search-queries row, not the anchor row. Anchor rows are
  load-bearing and must stay precise.
- The source label is `<topic>_deduction_anchor` for deduction
  topics; for non-deduction topics (e.g. labor/nómina), use
  `<topic>_anchor`.

Then find `_CASE_SEARCH_QUERIES` (immediately below
`_CASE_ANCHOR_REGISTRY`). Append a matching row:

```python
_CASE_SEARCH_QUERIES: tuple[tuple[object, tuple[str, ...]], ...] = (
    ...
    (
        is_<new>_case,
        (
            "<search phrase 1: include topic words + anchor article>",
            "<search phrase 2: include alternative angle>",
        ),
    ),
)
```

**Search-queries engineering rules:**

- Each query is a single line with topic-relevant terms in
  unaccented lowercase. Goal: feed text-search half of
  `hybrid_search` enough signal to rank the playbook chunk above
  noise chunks.
- Include the article number AS A DIGIT in at least one query
  (e.g. `"deduccion del ica art 115"`). The text-search half
  weights article-number occurrence.
- Both queries combined should not exceed ~150 characters total.

#### §3.3.6 Update `CLAUDE.md` Hot Path section (only if new file added)

If §3.3.1 created a new file (it should NOT — `case_detectors.py`
already exists), update `CLAUDE.md`'s `## Hot Path (main chat)`
section. For routine v16 work, no `CLAUDE.md` edit is needed.

### §3.4 Tests

#### §3.4.1 Per-topic test file

Create `tests/test_answer_synthesis_<topic>.py`. Copy the structure of
`tests/test_answer_synthesis_gmf_deduction.py` (simplest single-topic
template).

Required test cases per topic:

1. **Detector positives** — at least 3 cases the detector must catch
   (use the expert's phrasings from `## Cómo lo pregunta un contador`).
2. **Detector negatives** — at least 2 cases that look adjacent but
   must NOT fire (use other case topics' phrasings).
3. **Bullet emission** — `build_recommendations` returns bullets
   containing the playbook's key facts (numbers, article references,
   key phrases).
4. **Case isolation** — when the new case fires, bullets from other
   cases (e.g. GMF, ICA) are NOT emitted.
5. **End-to-end Q2 escape from Cobertura pendiente** — using
   `build_direct_answers`, a Q2-style "¿porcentaje + norma +
   registro?" sub-question must get at least one non-pending bullet
   assignment.

Pattern for test (5):

```python
def test_<topic>_q2_no_longer_cobertura_pendiente() -> None:
    from lia_graph.pipeline_d.answer_policy import DIRECT_ANSWER_COVERAGE_PENDING
    from lia_graph.pipeline_d.answer_synthesis_sections import build_direct_answers

    q1 = "<expert's phrasing 1 from playbook>"
    q2 = (
        "¿Qué porcentaje es deducible, en qué norma se fundamenta, y cómo"
        " debe registrarse en la depuración?"
    )
    recs = build_recommendations(
        request=_req(f"{q1} {q2}"),
        temporal_context={},
        primary_articles=(),
        connected_articles=(),
    )
    direct = build_direct_answers(
        sub_questions=(q1, q2),
        recommendations=recs,
        procedure=(),
        paperwork=(),
        precautions=(),
        context_lines=(),
        opportunities=(),
    )
    assert direct[1][1] != (DIRECT_ANSWER_COVERAGE_PENDING,)
```

**Important:** pass `q1` and `q2` as **separate items** in
`sub_questions`. Passing `f"{q1} {q2}"` as a single sub-question
inflates Q1's token set and causes ratio-based assignment to drift —
this was the v15.4 leasing test bug, documented at
`tests/test_answer_synthesis_intereses_leasing_primer_empleo.py::_q2_assignment`.

#### §3.4.2 Registry test row

File: `tests/test_planner_case_anchor_registry.py`

Add:

```python
def test_<topic>_case_anchors_art_<X>() -> None:
    keys = _planner_anchor_keys("<expert phrasing 1>")
    assert "<X>" in keys
    sources = _planner_anchor_sources("<expert phrasing 1>")
    assert "<topic>_deduction_anchor" in sources


def test_<topic>_case_adds_search_queries() -> None:
    queries = _planner_search_queries("<expert phrasing 1>")
    joined = " | ".join(queries).lower()
    assert "<topic-noun>" in joined
    assert "<article number>" in joined
```

#### §3.4.3 Pure-detector test (no answer_* imports leaking)

A single guard test in `tests/test_case_detectors_purity.py` (create
if absent) ensures the detector module stays pure:

```python
"""v15.5+ — `case_detectors.py` must not import from any answer_* or
helper module. Reintroducing such an import would re-create the
circular import `planner → helpers → support → planner`."""
import importlib
import inspect


def test_case_detectors_imports_are_pure() -> None:
    module = importlib.import_module("lia_graph.pipeline_d.case_detectors")
    src = inspect.getsource(module)
    for forbidden in ("answer_support", "answer_synthesis_helpers", "answer_synthesis_sections", "from .planner"):
        assert forbidden not in src, f"case_detectors.py must not import {forbidden}"
```

### §3.5 Probe via `answer-engine-probe` skill

After Lane A + Lane B + tests are green locally, validate end-to-end
on staging using the existing probe skill:

1. **Restart dev:staging server** (mandatory — the skill enforces
   this). Find the PID via `ps aux | grep ui_server | grep -v grep`
   and tell the operator the exact `! kill <PID> && npm run
   dev:staging` command. Wait for ready.
2. **Stage the probe run.** One question per new topic. Use the
   skill's `stage_run.py`:

   ```
   PYTHONPATH=src:. uv run python .claude/skills/answer-engine-probe/scripts/stage_run.py \
       --slug v16_batch_<NNN> --from-jsonl /tmp/v16_questions.jsonl
   ```
3. **Probe + digest + verdict per question.** Stop-on-first-failure
   per skill default.
4. **Acceptance gate:** every topic in the batch must score `pass`
   or `warn`. Any `fail` blocks the merge of that topic's bullets
   until the failure is diagnosed.

The rubric is in `.claude/skills/answer-engine-probe/references/rubric.md`.
Hard gates that MUST pass per topic:

- `H1` HTTP 200
- `H2` answer_mode is `graph_native` (not fallback/error)
- `H7` ≥1 primary-source citation for any normative claim
- `H9` topic routing correct
- `M1` both ¿…? questions covered
- `M2` ≥1 primary source cited
- `M3` numerics bolded
- `M4` Spanish

Warn-level signals (acceptable but worth recording in the verdict):

- `Q2` latency > 15s — current baseline is 23–32 s, so always fires
- Anclaje Legal still includes Cap V noise (Arts. 121-123) — current
  baseline residual, not a v16-introduced regression
- Polish rejected — if it happens, the v15.1 substantive-fallback
  must produce a complete answer (verify in digest)

---

## §4. Success criterion (gate 3 — measurable minimum)

A new topic is considered SHIPPED when ALL of the following hold:

1. The playbook `.md` is in `knowledge_base/<CATEGORY>/PLAYBOOKS/`
   with valid frontmatter.
2. The corpus rebuild ran successfully
   (`make phase2-graph-artifacts-supabase` exit code 0).
3. `case_detectors.py`, `answer_synthesis_sections.py`, and
   `planner.py` carry the new detector / bullets / whitelist /
   registry rows.
4. Unit tests for the topic pass (`pytest tests/test_answer_synthesis_<topic>.py`).
5. Registry tests pass (`pytest tests/test_planner_case_anchor_registry.py`).
6. Detector-purity test passes (`pytest tests/test_case_detectors_purity.py`).
7. The full related sweep passes:
   ```
   PYTHONPATH=src:. uv run pytest \
       tests/test_answer_inline_anchors.py \
       tests/test_answer_synthesis_gmf_deduction.py \
       tests/test_answer_synthesis_ica_predial.py \
       tests/test_answer_synthesis_intereses_leasing_primer_empleo.py \
       tests/test_answer_synthesis_<topic>.py \
       tests/test_planner_case_anchor_registry.py \
       tests/test_answer_polish_rejected_fallback.py \
       tests/test_answer_synthesis_practica.py \
       tests/test_case_detectors_purity.py -q
   ```
   (Existing sweep is 121 tests at v15.5; each new topic adds 5–10.)
8. A staging probe run for the topic produced `pass` or `warn` — never
   `fail`.

**Batch-level success criterion:** ≥ 90 % of attempted topics in a
batch reach SHIPPED state on first probe. Below 90 %, the playbook
template or the engineer intake is leaking somewhere; STOP and
diagnose before pushing the next batch.

---

## §5. Test plan (gate 4 — how to test, who runs what, decision rule)

| Stage | Actor | Environment | What runs | Pass condition |
|---|---|---|---|---|
| 1. Playbook authoring | Expert (contador SME) | n/a — text editor | Writes `.md` per template in `playbook_generation_brief.md` §3 | Conforms to template; every URL resolves to cited text |
| 2. URL verification | Engineer | shell | `curl -sI` each URL in the playbook | Every URL returns 200 or 30x; no 404 / 500 |
| 3. Lane A ingestion | Engineer | local docker | `make phase2-graph-artifacts` | Exit code 0; new doc visible in `artifacts/canonical_corpus_manifest.json` |
| 4. Lane A cloud sync | Engineer | dev:staging | `make phase2-graph-artifacts-supabase PHASE2_SUPABASE_TARGET=production` | Exit code 0; doc queryable via `supabase_select` on `documents` table |
| 5. Lane B unit tests | Engineer | local | `pytest tests/test_answer_synthesis_<topic>.py` | All green |
| 6. Lane B integration | Engineer | local | Full sweep from §4 step 7 | All green |
| 7. Staging probe | Engineer + operator | dev:staging via `answer-engine-probe` skill | One question per topic | `pass` or `warn` (never `fail`) per rubric |
| 8. Operator review | Operator | n/a | Read the rendered answer for the topic on `dev:staging` UI | Subjective: would a senior contador act on this answer? |

**Decision rule per topic:** stages 1–8 must all pass before the topic
is merged. A `fail` at any stage blocks merge until diagnosed and
fixed. Skip stage 8 only when the operator explicitly says "skip
operator review" — that exception is recorded in the topic's verdict
row.

**Decision rule per batch (≥ 5 topics):** if ≥ 1 topic in a batch
fails at stage 7, pause the batch and run a retrospective on the
playbook template before launching the next batch. Per
`feedback_thresholds_no_lower`, do NOT lower the per-topic decision
rule case-by-case; record exceptions in verdict rows, keep the rule
intact.

---

## §6. Greenlight (gate 5 — end-user validation)

Per `feedback_verify_fixes_end_to_end`, unit tests alone are not
sufficient. Each new topic batch requires end-user-layer validation:

- The operator (or designated contador SME) opens dev:staging in a
  browser, types a representative question for each topic in the
  batch, and reads the rendered answer.
- Sign-off criterion (per topic): would the operator forward this
  answer to a paying SMB-contador customer as-is? If yes → greenlight.
  If no → record the specific drag (citation, tone, missing detail)
  and route back to the playbook author or the engineer per cause.

The greenlight step is what separates "tests are green" from
"contador-ready." Do not skip.

---

## §7. Refine-or-discard (gate 6 — what to do if a topic regresses)

Per `feedback_diagnose_before_intervene`, when a topic regresses:

1. **Pinpoint the layer.** Was it (a) playbook content thin /
   incorrect (Lane A or expert), (b) bullets not surfacing in
   `Recomendaciones Prácticas` (Lane B bullet emission), (c) wrong
   anchor article cited (registry / retrieval), (d) polish overriding
   correct content (polish prompt / fallback)? Use
   `response.diagnostics.pipeline_trace` to identify the failing
   layer.
2. **Refine vs discard rules:**
   - Playbook content issue → request playbook revision from expert,
     re-ingest. Keep the code wiring.
   - Wrong anchor article → adjust `_CASE_ANCHOR_REGISTRY` row.
     Code-only change.
   - Retrieval still pulls noise → not a v16 problem; route to the
     fix that addresses topic-allowlist suppression at retrieval
     (§11 below).
   - Polish keeps fabricating wrong-norm justifications → not a v16
     problem; route to polish-prompt fix.
3. **Record the regression** in `docs/aa_next/playbook_regressions.md`
   (create if absent) with: topic, layer, fix applied or
   "discarded with reason." Per
   `feedback_recommendations_logged_in_canonical_plan`.

A topic moves from `🛠 code landed` to `🧪 verified locally` after
§4 acceptance. Promotes to `✅ verified in staging` after §6
greenlight. Demotes to `↩ regressed-discarded` if §7 cannot recover
it in one iteration — never silently roll back.

---

## §8. Rollback

**Per-topic rollback** is achieved by removing the topic's row from
`_CASE_ANCHOR_REGISTRY` and `_CASE_SEARCH_QUERIES` in `planner.py`.
The case detector and bullets can stay (they're behind a `if
is_<topic>_case(...)` guard that no longer surfaces in retrieval).

**Full v16 rollback** (unlikely, listed for completeness) is achieved
by `git revert` of the v16 commits. The v15.5 6-topic state is the
rollback target.

The corpus chunks placed in `knowledge_base/<CATEGORY>/PLAYBOOKS/`
remain in place — they were always retrievable as ordinary chunks,
just with reduced ranking when their anchor registry rows are gone.

---

## §9. Topic priority list (lifted from playbook brief §5)

> See `docs/expert_briefs/playbook_generation_brief.md` §5 for the
> expert-facing version with rationale. This section is the
> engineer-facing extract — bare list, suggested article anchors,
> existing detector if any.

### Already shipped (v15.1–v15.5) — DO NOT re-implement

| Topic | Detector | Anchor articles |
|---|---|---|
| GMF / 4×1000 | `is_gmf_deduction_case` | `("115",)` |
| ICA | `is_ica_deduction_case` | `("115", "115-1")` |
| Predial | `is_predial_deduction_case` | `("115",)` |
| Intereses + subcap | `is_intereses_deduction_case` | `("117", "118-1")` |
| Leasing | `is_leasing_deduction_case` | `("127-1",)` |
| Primer empleo | `is_primer_empleo_deduction_case` | `("108-5",)` |

### Tier 1 — Next wave (~30 topics)

**Renta — Deducciones (7 topics)**

| Topic | Suggested anchor articles |
|---|---|
| Depreciación fiscal de activos | `("137",)` |
| Atenciones a clientes y empleados | `("107-1",)` |
| Cartera de difícil recaudo | `("145", "146")` |
| Donaciones (deducción) | `("125",)` |
| Compensación de pérdidas fiscales | `("147",)` |
| Salario integral — tratamiento fiscal | `("132",)` *(CST, not ET — see §10)* |
| Limitación pagos en efectivo | `("771-5",)` |

**Renta — Descuentos tributarios (7 topics)**

| Topic | Suggested anchor articles |
|---|---|
| Donaciones (descuento) | `("257",)` |
| IVA en activos fijos productivos | `("258-1",)` |
| CTeI | `("158-1",)` |
| Energías renovables | *(Ley 1715/2014 art. 11 — non-ET anchor; see §10)* |
| Discapacidad | *(Ley 361/1997 art. 31 — non-ET anchor)* |
| Mujeres víctimas de violencia | *(Ley 1257/2008 art. 23 — non-ET anchor)* |
| Factura electrónica 1% | *(Ley 2277/2022 art. 7 — non-ET anchor)* |

**Renta — Tarifas y régimen (4 topics)**

| Topic | Suggested anchor articles |
|---|---|
| Tarifa general PJ | `("240",)` |
| TTD (Tasa de Tributación Depurada) | `("240",)` *(par. 6)* |
| Dividendos PN residentes | `("242",)` |
| RST tarifas consolidadas | `("908",)` |

**Renta — Procedimiento (4 topics)**

| Topic | Suggested anchor articles |
|---|---|
| Beneficio de auditoría | `("689-3",)` |
| Firmeza de declaraciones | `("714",)` |
| Anticipo de renta | `("807", "809")` |
| Devolución / compensación saldos a favor | `("850",)` |

**IVA (4 topics)**

| Topic | Suggested anchor articles |
|---|---|
| Hecho generador del IVA | `("420",)` |
| Régimen común vs simplificado | `("437-1", "437-2")` |
| IVA descontable + proporcionalidad | `("488", "491")` |
| Devolución saldos a favor en IVA | `("481",)` |

**Retención en la fuente (4 topics)**

| Topic | Suggested anchor articles |
|---|---|
| Retención por salarios | `("383",)` |
| Retención por servicios | `("392",)` |
| Bases mínimas (Decreto 572/2025) | *(non-ET; decreto)* |
| Autoretención | *(Decreto 2201/2016)* |

**Labor / Nómina — Tier 1 (12 topics)**

| Topic | Suggested anchor articles |
|---|---|
| Liquidación mensual de nómina | *(CST + Ley 100)* |
| Cesantías | *(Ley 50/1990)* |
| Prima de servicios | `("306",)` *(CST)* |
| Vacaciones | `("186",)` *(CST)* |
| Liquidación al terminar contrato — indemnizaciones | `("64",)` *(CST)* |
| PILA | *(Decreto 1990/2016)* |
| UGPP fiscalización | *(Ley 1607/2012 art. 178)* |
| Exoneración parafiscales 114-1 | `("114-1",)` *(ET)* |
| Nómina electrónica DSPNE | *(Resolución DIAN 000013/2021)* |
| Contrato prestación servicios vs laboral | `("23",)` *(CST)* |
| Pagos no constitutivos de salario | `("128",)` *(CST)* |
| Desalarización | *(Sentencia CSJ SL4655/2021)* |

**Information exógena (1 topic at Tier 1)**

| Topic | Suggested anchor articles |
|---|---|
| Información exógena umbrales AG 2025 | *(Resolución DIAN 000162/2023)* |

### Tier 2 — Second wave (~14 topics)

See `docs/expert_briefs/playbook_generation_brief.md` §5 Tier 2 for
the full list. Engineer wires these only after Tier 1 reaches ≥ 80 %
shipped.

---

## §10. Non-ET anchors — handling decretos / leyes / sentencias

The current `_CASE_ANCHOR_REGISTRY` only carries ET article numbers
in the second tuple field (e.g. `("115",)`). For topics whose primary
authority is a non-ET norm (CST article, Ley, decreto, sentencia),
the registry needs an extension.

**Two options. Pick ONE per topic; do not mix:**

#### Option A — Use the closest ET article as the anchor

For labor topics that have an ET tie-in (e.g. exoneración de
parafiscales is in ET art. 114-1, even though most of the labor
mechanics live in CST and Ley 100), anchor the ET article. The
playbook content carries the CST/Ley citations in the body bullets.

#### Option B — Extend the registry to support multi-source anchors

If a topic genuinely has no ET anchor (e.g. cesantías → Ley 50/1990),
extend `_CASE_ANCHOR_REGISTRY` schema to:

```python
# Each row: (detector, ((kind, lookup_value, label), ...), source_label)
_CASE_ANCHOR_REGISTRY = (
    (is_gmf_deduction_case,
     (("article", "115", "Art. 115"),),
     "gmf_deduction_anchor"),
    ...
    (is_cesantias_case,
     (("ley", "50:1990", "Ley 50 de 1990"),),
     "cesantias_anchor"),
)
```

Then the planner loop in `build_graph_retrieval_plan` emits
`PlannerEntryPoint(kind="ley", lookup_value="50:1990", ...)`
for non-article anchors.

The retriever must already understand `kind="ley"` / `kind="decreto"`
/ `kind="sentencia"` — verify by reading
`src/lia_graph/pipeline_d/retriever_supabase.py` for the
`anchor_articles` query shape. If `kind` other than `"article"` is
not supported, that is a prerequisite fix and Option A is the
fallback for v16.

**Recommendation:** ship Tier 1 ET-anchored topics first under
Option A. Then assess whether the retriever supports multi-kind
anchors; if it does, migrate the Ley/Decreto/Sentencia topics to
Option B in a follow-up. If it doesn't, that's a separate
prerequisite fix.

---

## §11. Known residuals (NOT in v16 scope)

Documented here so future agents don't re-discover them and waste
time:

1. **Cap V Deducciones chunk pollutes Anclaje Legal** for predial /
   intereses / leasing / primer empleo answers. The v15.5 registry
   surfaced the right anchor; the noise chunk wasn't suppressed.
   Future fix: topic-allowlist suppression of Arts. 121-123 chunk
   for non-gastos-en-el-exterior queries. Tracked in
   `docs/aa_next/` after v16 lands.
2. **Polish fabricates justifications for off-topic articles.** When
   polish has Arts. 121/122/123 in its ARTÍCULOS PERMITIDOS list, it
   writes invented blurbs ("Este artículo, junto con el art. 115 ET,
   sustenta el principio de causación"). Future fix: tighten polish
   prompt to drop articles whose retrieval score is below a
   threshold. Not a v16 problem.
3. **Latency 23-32 s** is consistent across all probes. Within the
   system's normal range; tracked separately if/when SLA matters.
4. **Polish rejection rate (~33 % of probes)** with
   `invented_periods` / `anchors_stripped`. The v15.1 substantive
   fallback handles it; clean polish would tighten the per-`¿…?`
   shape that polish-success currently loses.
5. **Topic taxonomy may need new keys** for non-tax categories
   (labor sub-topics like "ugpp", "nomina_electronica", "cesantias").
   When a playbook lands in a category that has no matching
   `config/subtopic_taxonomy.json` entry, the engineer routes to the
   closest parent in v16 and notes the gap for a separate taxonomy
   pass.

---

## §12. Change log entry (to be appended after merge)

Append to `docs/orchestration/orchestration.md` under `### Change Log`
the following row (verbatim, with the merge date filled in):

```
- v2026-MM-DD-fix-v16-playbook-scaling
  - Adds `case_detectors.py` registry pattern usable across deduction +
    descuento + retención + labor topics
  - Initial Tier 1 batch: <N> topics shipped (list in
    docs/aa_next/playbook_shipped.md)
  - No env flag changes; no schema changes
  - Rollback: per-topic via `_CASE_ANCHOR_REGISTRY` row removal
```

Mirror this row in `docs/guide/env_guide.md` `## Runtime Retrieval
Flags` mirror table (no flags actually change — note "no flag delta,
content-only batch").

Update `CLAUDE.md`'s `## Runtime Read Path` env-matrix-version chip is
NOT required (no flag changes). The `## Hot Path` section is also
unchanged.

---

## §13. Author notes for the executing agent

- **Idempotency.** Adding a topic is idempotent: re-running the
  intake on the same playbook produces the same code edits. If you
  run the intake twice on the same playbook, the second pass either
  no-ops (already-present registry row) or reports a duplicate
  detector name — both are safe.
- **Granularity.** Per `feedback_granular_edits` and
  `feedback_respect_pipeline_organization`, do NOT append to any
  module already ≥ 1000 LOC. `answer_synthesis_sections.py` is
  currently around 1200 LOC; if your additions push it past 1500,
  pause and extract the case branch into a dedicated sibling module
  before continuing.
- **Verification non-negotiable.** Per `feedback_no_hallucinated_examples`,
  every numeric value, article reference, plazo, monto, or registro
  detail you wire into bullets MUST be verifiable against the
  expert's playbook URLs. If the expert wrote it but you cannot
  verify it via the cited URL, STOP and ask before landing.
- **No new env flags.** The v16 work does not introduce flags. If
  you find yourself adding `LIA_*` flags during a topic intake, you
  are extending scope — stop and surface the question.
- **No money in status reports.** Per `feedback_no_money_quoting`,
  report effort in time + scope, not currency.
- **Plain language in operator updates.** Per
  `feedback_plain_language_communication`, end-of-batch reports to
  the operator are plain language by default; engineering depth only
  when asked.

---

*End of fix_v16_may.md.*
