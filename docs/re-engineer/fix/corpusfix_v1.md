# corpusfix_v1.md — Playbook corpus topic-tagging gap

> **Author context (zero-agent-context protocol).** This plan is
> self-contained. A fresh LLM agent with no prior conversation history
> can execute it from the file system as-is. Every file path, function
> name, env flag, registry entry, and command is specified verbatim.
> Verify every artifact against `git ls-files` before acting. If any
> cited path or function does not exist, STOP and report drift — do not
> invent.

---

## §0. TL;DR

**Idea.** Re-ingest the 31 playbook chunks in `knowledge_base/CORE ya
Arriba/**/PLAYBOOKS/*.md` with **correct primary-topic tagging** so the
runtime coherence/safety gate stops abstaining on legitimate playbook
questions whose case-anchor article IS in the topic's allowlist.

**Why now.** Fix_v16 batches 1–3 shipped 25 new playbooks across renta,
IVA, procedimiento, and retención topics. Probe q01_notificaciones_retest
(fix_v16 b3 retest, 2026-05-14) revealed that the **art. 566-1** chunks
ingested for `playbook_renta_notificaciones_electronicas.md` were
classified with a topic that doesn't match `procedimiento_tributario`,
which is the correct topic for art. 566-1. Trace:

- `topic_router.llm.success: llm_primary_topic=procedimiento_tributario` ✅
- `planner.built: plan_anchor_count=1` (our 566-1 anchor) ✅
- `retriever.evidence: seed_article_keys=['566-1', '555', '555-1', '555-2']` ✅
- `safety.misalignment.detect: misaligned=True` ❌
- `coherence.detect: reason=primary_off_topic` ❌
- `coherence.abstention` → engine refuses to answer.

The retrieval finds the right chunks; the gate refuses because the
chunks' stored `topic` field doesn't match the routed topic. The fix is
**corpus-side**: re-tag the chunks. Not a runtime bug.

**Effort.** ~30 min: 1 classifier-rule edit + 1 cloud delta re-ingest.

**Risk.** Low. Additive corpus update; existing chunks get re-tagged via
delta sync; no destructive ops. Per memory
`feedback_lia_graph_cloud_writes_authorized`, cloud writes are
pre-authorized for Lia Graph (announce-before-executing).

---

## §1. Repository state assumed by this plan

Verify before changing the runtime:

| Path | Purpose |
|---|---|
| `src/lia_graph/ingestion_classifier.py` | Filename/path → `knowledge_class` + topic classifier. fix_v16 added a playbook rule (line ~187). |
| `src/lia_graph/ingestion/supabase_sink.py` | Writes `documents.topic` / `document_chunks.topic` to Supabase during ingest. |
| `knowledge_base/CORE ya Arriba/RENTA/PLAYBOOKS/*.md` | 26 renta playbooks (deducciones, descuentos, tarifas, procedimiento). |
| `knowledge_base/CORE ya Arriba/IVA_COMPLETO/PLAYBOOKS/*.md` | 5 IVA playbooks. |
| `knowledge_base/CORE ya Arriba/RETENCION_FUENTE/PLAYBOOKS/*.md` | 1 retención playbook. |
| `config/subtopic_taxonomy.json` | Canonical topic keys for Lia Graph. |
| `config/topic_norm_allowlist.json` | Per-topic article allowlists used by the coherence/safety gate. |
| `Makefile` target `phase2-corpus-additive` | Cloud delta sync entrypoint. |

### Sprint v16 ship state (assumed merged)

- 31 playbook corpus files exist under `knowledge_base/CORE ya
  Arriba/**/PLAYBOOKS/`.
- `ingestion_classifier.py` has a rule that tags
  `playbook` filename/path → `knowledge_class=interpretative_guidance`.
- Cloud (production Supabase + Falkor) has all 31 chunks ingested via
  `make phase2-corpus-additive PHASE2_SUPABASE_TARGET=production`
  across batches 1, 2, and 3.
- The chunks ARE retrievable via `hybrid_search` (`seed_article_keys`
  confirms art. 566-1 surfaces). The problem is purely the `topic` field
  on each chunk row.

---

## §2. Root cause (gate 1 — what's actually wrong)

### What we observe

- Topic router classifies q01 question as `procedimiento_tributario`.
- Planner emits `art. 566-1` anchor via `notificaciones_electronicas_anchor`.
- Retriever's `hybrid_search` returns chunks including 566-1.
- **`coherence.detect`** runs with `mode=enforce` and finds the primary
  articles are tagged with a topic **other than**
  `procedimiento_tributario`, triggers `primary_off_topic`, and the
  safety layer abstains.

### What's actually wrong

`src/lia_graph/ingestion_classifier.py` line ~187 is what we added in
fix_v16 b3:

```python
(re.compile(r"(?:^|[/_-])playbooks?(?:[/_-]|$|\.)", re.I), "interpretative_guidance", 0.96),
```

This rule sets the **knowledge_class** correctly to
`interpretative_guidance`. But **it does NOT set the `topic`** field.

The pipeline's topic-tagging logic for playbook files falls through to:

1. `_FILENAME_TOPIC_PATTERNS` (`IVA[_-]` / `ICA[_-]` / `GMF[_-]` prefixes
   etc.) — but `playbook_renta_notificaciones_electronicas.md` starts
   with `playbook_renta_` which **doesn't match any of those prefixes**.
2. Path-based heuristics on `relative_path` — the playbook lives at
   `CORE ya Arriba/RENTA/PLAYBOOKS/playbook_renta_notificaciones_electronicas.md`.
   "RENTA" in the path resolves to topic `declaracion_renta` (not
   `procedimiento_tributario`), which is incorrect for a sanction /
   notification / firmness playbook.
3. LLM-based topic classification as the final fallback. Depending on
   the LLM's pick, the chunk may get a third topic that matches neither
   the router topic nor the playbook's actual subject.

So for q01_notificaciones, the 566-1 chunk gets stored with `topic =
declaracion_renta` (or similar), and the coherence gate (whose router
says `procedimiento_tributario`) refuses to use it.

### Why we observe this for `notificaciones` but not for every playbook

The other playbooks that probed PASS:
- `playbook_renta_beneficio_auditoria.md` — RENTA/, topic likely
  routed to `declaracion_renta`. Router also classifies questions about
  beneficio de auditoría as `declaracion_renta` or `costos_deducciones_renta`.
  So router topic and chunk topic align by accident.
- `playbook_iva_*.md` files — under `IVA_COMPLETO/PLAYBOOKS/`. Path
  contains `IVA` → topic resolves to `iva`. Router classifies IVA
  questions as `iva`. Aligned.

Notificaciones is the only `RENTA/PLAYBOOKS/` playbook whose subject is
**procedimiento_tributario** rather than `declaracion_renta`. The
ingestion classifier defaults the topic from the PATH (`RENTA/`), not
the subject. Mismatch.

A handful of other RENTA/PLAYBOOKS/ files share the same problem
(silent — they happen not to have been probed yet):

- `playbook_renta_sancion_extemporaneidad.md` (procedimiento_tributario)
- `playbook_renta_sancion_correccion.md` (procedimiento_tributario)
- `playbook_renta_sancion_inexactitud.md` (procedimiento_tributario)
- `playbook_renta_firmeza_declaraciones.md` (procedimiento_tributario)
- `playbook_renta_devolucion_saldos_favor.md` (devoluciones_saldos_a_favor)
- `playbook_renta_beneficio_auditoria.md` (procedimiento_tributario,
  even though it routes OK by coincidence)

The fix needs to address **all** of these so probes on the others don't
hit the same wall later.

---

## §3. Plan (gate 2 — implementation outline)

### §3.1 Map filename → canonical topic explicitly

Add a per-playbook topic table to `ingestion_classifier.py`. Match by
filename stem (without extension) and short-circuit the path-based
fallback when present.

#### §3.1.1 New table in `ingestion_classifier.py`

Insert after the existing `_FILENAME_TOPIC_PATTERNS` block (around line
220, verify):

```python
# fix_corpusfix_v1 (2026-MM-DD) — explicit playbook → topic map.
# Path-based topic inference (RENTA/, IVA_COMPLETO/, etc.) misclassifies
# playbooks whose subject differs from the path. Example: every file
# under RENTA/PLAYBOOKS/ defaults to "declaracion_renta", but
# `playbook_renta_notificaciones_electronicas` is really
# `procedimiento_tributario`. Causes the coherence gate to abstain on
# correct retrievals at runtime. Authoritative table below; keys are
# filename stems (no extension), values are canonical topic keys from
# `config/subtopic_taxonomy.json`.
_PLAYBOOK_FILENAME_TO_TOPIC: dict[str, str] = {
    # Renta — Procedimiento (sanciones + firmeza + notificaciones + devolución)
    "playbook_renta_notificaciones_electronicas": "procedimiento_tributario",
    "playbook_renta_sancion_extemporaneidad": "procedimiento_tributario",
    "playbook_renta_sancion_correccion": "procedimiento_tributario",
    "playbook_renta_sancion_inexactitud": "procedimiento_tributario",
    "playbook_renta_firmeza_declaraciones": "procedimiento_tributario",
    "playbook_renta_beneficio_auditoria": "procedimiento_tributario",
    "playbook_renta_devolucion_saldos_favor": "devoluciones_saldos_a_favor",
    "playbook_renta_anticipo_renta": "procedimiento_tributario",
    # Renta — Deducciones (costos_deducciones_renta)
    "playbook_renta_depreciacion_fiscal": "costos_deducciones_renta",
    "playbook_renta_atenciones_clientes_empleados": "costos_deducciones_renta",
    "playbook_renta_cartera_dificil_recaudo": "costos_deducciones_renta",
    "playbook_renta_donaciones_deducibles": "costos_deducciones_renta",
    "playbook_renta_limitacion_pagos_efectivo": "costos_deducciones_renta",
    "playbook_renta_exoneracion_parafiscales_114_1": "costos_deducciones_renta",
    # Renta — Descuentos tributarios
    "playbook_renta_iva_activos_fijos_productivos": "descuentos_tributarios_renta",
    "playbook_renta_ctei_descuento": "descuentos_tributarios_renta",
    # Renta — Tarifas
    "playbook_renta_tarifa_general_pj_35": "declaracion_renta",
    "playbook_renta_dividendos_pn_residentes": "declaracion_renta",
    "playbook_renta_rst_tarifas": "rst_regimen_simple",
    "playbook_renta_zona_franca_doble_tarifa": "declaracion_renta",
    # IVA — all under IVA_COMPLETO/PLAYBOOKS/, all topic "iva"
    "playbook_iva_hecho_generador": "iva",
    "playbook_iva_responsables": "iva",
    "playbook_iva_descontable_proporcionalidad": "iva",
    "playbook_iva_devolucion_saldos_favor": "iva",
    "playbook_iva_excluidos_vs_exentos": "iva",
    # Retención en la fuente
    "playbook_retencion_salarios_383": "retencion_fuente",
}
```

#### §3.1.2 New helper to apply the table

In the same file, near the existing topic-resolution code, add:

```python
def _playbook_filename_topic_override(file_stem: str) -> str | None:
    """fix_corpusfix_v1 — when ingesting a playbook, look up its
    authoritative topic from ``_PLAYBOOK_FILENAME_TO_TOPIC``. Returns
    None for non-playbook files so the existing path/LLM fallbacks
    keep running for the rest of the corpus.
    """
    return _PLAYBOOK_FILENAME_TO_TOPIC.get(file_stem)
```

#### §3.1.3 Wire the override into the classification path

Find the function that resolves topic during ingestion (likely
`classify_ingestion_document` near line 130 of `ingestion_classifier.py`
or similar). Before returning the topic, call the override:

```python
# fix_corpusfix_v1 — explicit playbook override beats path/LLM inference.
file_stem = ...  # however the function derives it from the doc record
override = _playbook_filename_topic_override(file_stem)
if override:
    topic = override
```

Verify the exact integration point against current code shape — the
override has to land BEFORE the topic is written to the doc record's
metadata.

### §3.2 Re-ingest the playbook chunks with corrected topics

Idempotent additive sync — same path used in batches 1/2/3:

```
make phase2-corpus-additive PHASE2_SUPABASE_TARGET=production DELTA_DRY_RUN=1
```

Expected dry-run output: **31 modified** (the playbook chunks),
**0 added**, **0 removed**. If the dry-run shows `added > 0`, STOP and
investigate — the classifier change should only update topic, not
introduce new docs.

Execute the real sync:

```
make phase2-corpus-additive PHASE2_SUPABASE_TARGET=production
```

### §3.3 Verify the chunks were re-tagged

```
PYTHONPATH=src:. uv run python -c "
from lia_graph.supabase_client import supabase_select
rows = supabase_select(
    'documents',
    columns='doc_id,topic,knowledge_class,source_relative_path',
    filters={'source_relative_path__like': '%PLAYBOOKS%'},
    limit=50,
)
for r in rows:
    print(r['topic'], '|', r['source_relative_path'].split('/')[-1])
"
```

Verify by spot-checking:
- `playbook_renta_notificaciones_electronicas.md` → `procedimiento_tributario`
- `playbook_renta_sancion_*.md` → `procedimiento_tributario`
- `playbook_iva_*.md` → `iva`
- `playbook_renta_rst_tarifas.md` → `rst_regimen_simple`

### §3.4 Re-probe q01_notificaciones_retest on dev:staging

Restart the dev:staging server (server-state non-negotiable, see
`answer-engine-probe` skill runbook). Then:

```
PYTHONPATH=src:. uv run python .claude/skills/answer-engine-probe/scripts/probe.py \
    --run-dir /tmp/corpusfix_v1_smoke \
    --qid q01_notificaciones_smoke \
    --message "¿Cómo me notifica la DIAN ahora y cuándo se entiende notificada una resolución por correo?"
PYTHONPATH=src:. uv run python .claude/skills/answer-engine-probe/scripts/digest.py \
    --run-dir /tmp/corpusfix_v1_smoke --qid q01_notificaciones_smoke 2>&1 | grep -E 'polish_mode|misaligned|reason|abstention' | head -10
```

**Expected**: `polish_mode=llm` (not `skipped`), `misaligned=False`,
no `coherence.abstention` step. Answer body contains the
notificaciones_electronicas bullets (art. 566-1, quinto día hábil, etc.).

---

## §4. Success criterion (gate 3 — measurable minimum)

The fix is considered SHIPPED when ALL of the following hold:

1. `_PLAYBOOK_FILENAME_TO_TOPIC` table exists and covers all 31 playbooks
   shipped through fix_v16 batches 1–3.
2. `_playbook_filename_topic_override` is called BEFORE topic finalization
   in the ingestion classifier path.
3. The additive cloud sync executed with delta showing **N modified,
   0 added, 0 removed** where N = 31.
4. Spot-check via Supabase shows the renta_procedimiento playbooks
   (notificaciones, sanciones, firmeza, beneficio_auditoria) carry
   `topic=procedimiento_tributario`.
5. Re-probe of q01_notificaciones returns `polish_mode=llm` with a
   substantive answer body — no abstention.

---

## §5. Test plan (gate 4 — how to test, who runs what)

| Stage | Actor | Environment | What runs | Pass condition |
|---|---|---|---|---|
| 1. Override table review | Engineer | n/a | Read `_PLAYBOOK_FILENAME_TO_TOPIC` against `config/subtopic_taxonomy.json` | Every value is a real key in the taxonomy |
| 2. Classifier unit test | Engineer | local | `pytest tests/test_ingestion_classifier_playbook_topic.py -q` (write this test file) | Each playbook stem returns the expected topic |
| 3. Local artifact rebuild | Engineer | local | `make phase2-graph-artifacts` | Exit code 0; `artifacts/canonical_corpus_manifest.json` shows updated `topic` per playbook |
| 4. Cloud delta dry-run | Engineer | dev:staging | `make phase2-corpus-additive PHASE2_SUPABASE_TARGET=production DELTA_DRY_RUN=1` | Shows 31 modified, 0 added, 0 removed |
| 5. Cloud delta execute | Engineer + operator (per `feedback_lia_graph_cloud_writes_authorized` — announce before) | dev:staging | Same command without DRY_RUN | Exit code 0; sink_result shows the 31 docs updated |
| 6. Supabase spot-check | Engineer | dev:staging | Query above (§3.3) | Topics match `_PLAYBOOK_FILENAME_TO_TOPIC` |
| 7. Server restart + probe | Engineer + operator | dev:staging | Restart, then probe q01_notificaciones | `polish_mode=llm`, no abstention, art. 566-1 bullets present |
| 8. Re-probe v16 b3 retest suite | Engineer + operator | dev:staging via `answer-engine-probe` skill | 5-question retest from batch 3 | Pass rate lifts from 3/5 to ≥4/5 (q01 should flip pass) |

**Decision rule**: all 8 stages must complete cleanly before declaring
the corpus fix shipped. Failure at any stage blocks promotion until
diagnosed.

---

## §6. Greenlight (gate 5 — end-user validation)

Per `feedback_verify_fixes_end_to_end`, after the technical pass:

- Operator opens dev:staging in a browser, types
  *"¿Cómo me notifica la DIAN ahora?"* — verifies the rendered answer
  cites art. 566-1, the 5° día hábil rule, and gives the buzón
  electrónico guidance — NOT the safety abstention message.

- Operator repeats with one question per renta_procedimiento topic that
  was silently mis-classified (sanción extemporaneidad, sanción
  corrección, sanción inexactitud, firmeza, beneficio_auditoria) to
  catch any latent abstention on those.

Sign-off: would the operator forward each of these answers to a paying
contador customer as-is? If yes → greenlight. If no → record the
specific drag and iterate.

---

## §7. Refine-or-discard (gate 6 — what to do if a topic regresses)

If, after re-ingest, a playbook still triggers abstention:

1. **Confirm the chunk's stored `topic` in Supabase** matches what the
   override table declared. If not, the override isn't being applied
   correctly — fix the wiring in §3.1.3 and re-ingest.
2. **Confirm the routed topic matches the chunk's topic.** If router
   classifies the question into a different topic than the chunk's
   topic, you need to either:
   - Add a `cross_topic_allowed` entry in
     `config/topic_norm_allowlist.json` so the gate accepts the chunk
     when routed from an adjacent topic, OR
   - Adjust the override to use the topic the router prefers (only if
     the chunk genuinely belongs to that topic).
3. **Never relax the coherence gate threshold** to make a single case
   pass. Per `feedback_thresholds_no_lower`, the qualitative gate stays;
   record the exception in `docs/aa_next/playbook_topic_exceptions.md`
   if persistent.

---

## §8. Rollback

The fix is additive and idempotent. Rollback options:

- **Remove the `_PLAYBOOK_FILENAME_TO_TOPIC` table** from the classifier
  and re-run `make phase2-corpus-additive`. The next sync will restore
  the previous (incorrect) topics.
- **Per-playbook rollback**: remove the specific filename from the
  override table and re-sync. Only that playbook's chunks get retagged.

No destructive operations. Cloud delta sync is always non-destructive.

---

## §9. Why this is corpus-side, not runtime-side

Multiple runtime fixes were considered and rejected:

| Option | Why rejected |
|---|---|
| **Loosen the coherence gate** | Per `feedback_thresholds_no_lower`. Gate exists to prevent off-topic answers; weakening it for one case opens many more wrong answers. |
| **Bypass the gate when a case detector fires** | Couples runtime safety to detector implementation. A detector bug or test gap could silently disable safety for some topics. |
| **Expand the topic's `allowed_prefixes`** in topic_norm_allowlist.json | Already includes art. 566-1 — the issue isn't the article allowlist, it's the chunk's STORED topic. |
| **Force topic at runtime via case-anchor metadata** | Possible but more invasive. The corpus-side fix is canonical, idempotent, and matches how every other chunk type is topic-tagged. |

The corpus tagging is the single source of truth the coherence/safety
layer consults. Fixing tags at the source means every downstream layer
(retrieval, planner, coherence, polish, presentation) gets the correct
topic without bespoke per-case overrides.

---

## §10. Change log entry (after merge)

Append to `docs/orchestration/orchestration.md` under `### Change Log`:

```
- v2026-MM-DD-corpusfix-v1-playbook-topic-tags
  - Adds `_PLAYBOOK_FILENAME_TO_TOPIC` override table in
    ingestion_classifier.py
  - Re-tags 31 playbook chunks via additive Supabase sync
  - Resolves coherence-gate abstention on notificaciones, sanciones,
    firmeza, devolución, beneficio_auditoria playbooks (probe q01
    of v16 b3 retest)
  - No flag changes; no schema changes; corpus-only update
  - Rollback: remove override + re-sync
```

No CLAUDE.md or env-matrix bump required — no flags change.

---

## §10b. New findings from fix_v16 b4/b5 retest probe (2026-05-14)

The 20-question batch-4 + batch-5 retest on dev:staging surfaced **two
new failure modes** that this fix must cover, beyond the original
notificaciones case in §2.

### §10b.1 Exógena family — all five formats blocked (5/20 FAIL)

| qid | Question | Routed topic | Primary articles came back tagged as | Verdict |
|---|---|---|---|---|
| q06 | F1001 — pagos a terceros | `informacion_exogena` | `beneficiario_final_rub` | abstain |
| q07 | F1003 — retenciones practicadas | `informacion_exogena` | `regimen_tributario_especial_esal` | abstain |
| q08 | F1005 — IVA descontable reportado | `informacion_exogena` | `sector_comercio_internacional` | abstain |
| q09 | F1007 — ingresos por terceros | `informacion_exogena` | `beneficiario_final_rub` | abstain |
| q10 | Umbrales exógena AG 2025 | `informacion_exogena` | `beneficiario_final_rub` | abstain |

- Three distinct wrong topics (`beneficiario_final_rub`,
  `regimen_tributario_especial_esal`, `sector_comercio_internacional`)
  → not one stray tag; the chunks for arts. 631 / 365 etc. went
  through different LLM classifications.
- Same root cause as §2: `_FILENAME_TOPIC_PATTERNS` doesn't catch
  `playbook_renta_exogena_*`, path falls through to LLM, LLM
  hallucinated unrelated topics.
- Detectors are working; planner anchors are correct; only the
  corpus-side topic tag is wrong.

**Add to §3.1.1 table** (`_PLAYBOOK_FILENAME_TO_TOPIC`):

```python
    # Renta — Información exógena (informacion_exogena)
    "playbook_renta_exogena_1001_pagos_terceros": "informacion_exogena",
    "playbook_renta_exogena_1003_retenciones_practicadas": "informacion_exogena",
    "playbook_renta_exogena_1005_iva_descontable": "informacion_exogena",
    "playbook_renta_exogena_1007_ingresos_por_terceros": "informacion_exogena",
    "playbook_renta_exogena_umbrales_obligados_2025": "informacion_exogena",
```

### §10b.2 Renta — Compensación pérdidas, NIIF conciliación, retención servicios, soporte factura

The retest also flagged these as PASS but with the same underlying
risk if probed with slight phrasing changes. Pre-emptively add their
filename → topic mappings:

```python
    # Renta — Procedimiento / compensación
    "playbook_renta_compensacion_perdidas_147": "perdidas_fiscales_art147",
    "playbook_renta_niif_conciliacion_fiscal_772_1": "conciliacion_fiscal",
    "playbook_renta_retencion_servicios_392": "retencion_fuente",
    "playbook_renta_soporte_factura_771_2": "facturacion_electronica",
```

### §10b.3 NIIF playbooks (estados_financieros_niif folder)

The batch-5 NIIF playbooks live under
`knowledge_base/estados_financieros_niif/PLAYBOOKS/`. Path-based
inference points to `estados_financieros_niif`, which IS the
expected topic for these playbooks. **No filename override needed
for the playbook chunks themselves** — but see §10b.4 for the
cross-domain anchor problem these surfaced.

### §10b.4 Cross-domain anchor problem (NOT corpus-side — runtime fix landed separately)

q18 (cláusula antiabuso) and q19 (impuesto diferido) failed for a
different reason than §10b.1:

- Topic router classified q18 as `procedimiento_tributario` and q19
  as `niif_pymes` (semantically correct).
- Planner emitted anchors `art. 869` (q18) and `art. 240` (q19).
- Retriever returned the chunks for those ET articles — correctly
  tagged `declaracion_renta` (their owner topic).
- Coherence-gate found `declaracion_renta ≠ procedimiento_tributario`
  / `niif_pymes` → abstain.

**This is NOT a corpus-tag bug.** Art. 869 legitimately lives in
the renta libro and is correctly tagged `declaracion_renta`. The
fix is **runtime-side** via `config/article_secondary_topics.json`:

| article_id | primary_topic | secondary_topics added |
|---|---|---|
| 240 | declaracion_renta | + `estados_financieros_niif`, `niif_pymes` |
| 28 | declaracion_renta | `estados_financieros_niif`, `niif_pymes` (new entry) |
| 869 | declaracion_renta | `procedimiento_tributario` (new entry) |
| 869-1 | declaracion_renta | `procedimiento_tributario` (new entry) |
| 869-2 | declaracion_renta | `procedimiento_tributario` (new entry) |

`retriever_supabase._classify_article_rows` (line ~1082) reads this
file at runtime via `_load_article_topic_index()`. When the router
topic appears in an article's `(primary_topic + secondary_topics)`
union, the chunk gets promoted to primary with
`secondary_topics=(router_topic,)`. Then
`topic_safety.detect_topic_misalignment` (line 148) short-circuits
on the match and bypasses the lexical gate.

**Status:** edits landed in
`config/article_secondary_topics.json` 2026-05-14. Module-level
cache `_ARTICLE_TOPICS_CACHE` requires a server restart to pick up.
No re-ingestion needed (this side reads the JSON directly).

This subsection is documented here for the executing agent's
context — the corpusfix_v1 plan itself is unchanged for these five
article entries. The cross-domain anchor pattern is **expected to
recur** as the registry grows: any Tier-2 topic whose anchor lives
in a different libro than its routing target (NIIF / procedimiento /
cambiario / aduanero) will need a corresponding
`article_secondary_topics.json` entry.

---

## §11. Author notes for the executing agent

- **Idempotency.** Re-running §3.2 with the same classifier state
  produces zero changes. Safe to dry-run + execute multiple times.
- **No new env flags.** This is content/metadata only.
- **Cloud auth.** Per `feedback_lia_graph_cloud_writes_authorized`,
  cloud writes for Lia Graph are pre-authorized; announce before
  triggering the sync, no per-action confirmation required.
- **No money in status reports.** Per `feedback_no_money_quoting`,
  report effort in time + scope.
- **Don't re-extract.** Per
  `feedback_extract_once_three_stage_promotion`, this fix updates
  classification metadata only — no canonicalizer or Gemini bulk
  extraction. The playbook content is unchanged.

---

*End of corpusfix_v1.md.*
