# Structural Work — v1 (SEE NOW)

**Context.** Written after investigating two recurring failure modes: (a) DIAN audit-procedure queries routed to `laboral` because the top-level router's weak list treated `liquidación` as a labor-exclusive bare term, and (b) multi-question turns where one sub-question got `Cobertura pendiente` because the subtopic classifier returned `None`. The narrow fixes landed (see `src/lia_graph/topic_router_keywords.py` — `procedimiento_tributario` vocabulary expansion + `laboral.weak` polysemy removal — and `config/subtopic_taxonomy.json` — audit-procedure aliases on `simplificacion_tramites_administrativos_y_tributarios`). This document catalogs the five **general** weaknesses those single-point fixes only papered over. Each item is a data or design pattern that will keep biting new queries until it's addressed at the pattern level.

**Scope note.** This is a structural backlog, not a refactor plan with batches. Each item is independently actionable; the ordering at the end is a *recommendation*, not a dependency chain — except where stated. Effort estimates are coarse (S = under a day, M = a day to a week, L = multi-week).

**Non-goals.** Not re-opening the `main chat` → `Normativa` / `Interpretación` split. Not changing the retriever contract (hybrid_search RPC stays, Falkor Cypher stays). Not touching answer-synthesis / assembly — those are downstream of everything here.

---

## A. Polysemous bare weak keywords (the "liquidación" anti-pattern)

### Symptom

Query `"¿Cuál es la ruta procesal si escala a requerimiento especial y luego a liquidación oficial?"` routed to `laboral` with confidence 0.3 because `_TOPIC_KEYWORDS["laboral"]["weak"]` contained bare `liquidar` / `liquidacion` / `liquidación` — each of which also means *contract liquidation*, *company dissolution*, *tax self-assessment*, and *DIAN audit liquidation*. The first weak hit, on any topic, wins the keyword scorer when no stronger signal is present. A single polysemous bare term is enough to hijack a whole subdomain of queries.

### Why it's general

The same anti-pattern lives, right now, for these bare entries in `_TOPIC_KEYWORDS["laboral"]["weak"]` (src/lia_graph/topic_router_keywords.py:96-150):

| Bare term | Other senses it still matches |
|---|---|
| `prima` | prima en colocación de acciones (societario), prima de seguros (financial) |
| `aportes` / `aportaciones` | aportes de capital (societario), aportes a fondos de inversión |
| `cotización` | precio cotizado (comercial / bolsa) |
| `planilla` | planilla de cálculo genérica |
| `bonificación` | bonificación comercial, bonificación fiscal |
| `dotación` | dotación de activos fijos (contabilidad) |
| `salud` | sector salud, impuestos saludables, salud financiera |
| `pensión` | pensión alimenticia (civil), pensión hotelera |

Every item on this list is labor-**dominant**, not labor-**exclusive**. For each one there is a foreseeable query where the labor interpretation is wrong and routing will mis-fire exactly like `liquidación` did. The risk is also not confined to `laboral.weak` — any topic's weak list that contains a bare polysemous term inherits the same problem.

### Where to intervene

Two files, one design rule:

1. **`src/lia_graph/topic_router_keywords.py` — audit every topic's `weak` tuple.**
   The function that consumes these is `_score_topic_keywords(message)` at `src/lia_graph/topic_router.py:284-298`. Scoring is `strong_hits × 3 + weak_hits × 1`, gated by `_keyword_in_text(kw, text)` which uses `\bkeyword\b` word boundaries with no proximity context. The weak bucket exists precisely because these are low-confidence signals — the design assumption is that each weak term is topic-characteristic enough that *any* occurrence nudges toward the topic. That assumption fails for polysemous bare terms.

2. **Where polysemous terms should move.** Two valid relocations:
   - **Up to `strong` as compound phrases.** Bare `prima` → `prima de servicios`, `prima de antigüedad`. Bare `aportes` → `aportes parafiscales`, `aportes seguridad social`. The scorer's `\b…\b` boundary is already compound-safe (it matches `prima de servicios` as a single unit).
   - **Down into `_SUBTOPIC_OVERRIDE_PATTERNS`.** Same file, lines 571-667. Each entry is `(compiled_regex, topic_key, search_keywords_tuple)` and runs **before** keyword scoring via `_check_subtopic_overrides` in `topic_router.py:390-396`. The laboral override at `topic_router_keywords.py:656-666` already demonstrates the pattern: `\bliquid\w*\b[^.?!]{0,30}\b(?:emplead[oa]|trabajador[ae]|…)` — proximity window forces the bare term to fire only with labor context. Polysemous terms that need context can become override entries with a similar proximity regex.

3. **The design rule to codify.** Add this to the module docstring at the top of `topic_router_keywords.py` (currently lines 1-22):

   > Weak-bucket entries must be topic-**characteristic** on their own. A bare term that is topic-**dominant** but also appears in other domains (e.g. `liquidación` — labor-dominant, but also means DIAN audit, company dissolution, tax self-assessment) does not belong in `weak`. Promote it to `strong` as a compound phrase (`liquidación de nómina`) or to `_SUBTOPIC_OVERRIDE_PATTERNS` as a proximity regex (`liquidar` within 30 chars of `empleado/trabajador`).

### Test gates

- `tests/test_topic_router_keywords.py` — add parameterized cases for every polysemous term with an *adversarial* example that should NOT route to the current topic (e.g. `prima en colocación de acciones` must not route to laboral; `cotización en bolsa` must not route to laboral; `sociedad en liquidación` must not route to laboral).
- `tests/test_topic_router_llm.py` exists for the LLM fallback path — the rule-based path gets most of the traffic and deserves equivalent adversarial coverage.

### Effort / risk

**M**. The audit is mechanical once the rule is named. Risk is recall loss on queries that used to squeak through on a bare weak hit — mitigated by adding compound strong entries and/or override regexes to cover the real labor phrasings. Run the existing labor test suite (`pytest -k laboral`) after each removal.

---

## B. Curator label-speak vs accountant query-speak in the taxonomy

### Symptom

`_detect_sub_topic_intent` (src/lia_graph/pipeline_d/planner_query_modes.py:58-111) scanned the entire 106-entry taxonomy for the DIAN-audit query and returned **zero** alias hits. Not one. Not because the subtopic wasn't there — `procedimiento_tributario.simplificacion_tramites_administrativos_y_tributarios` existed and semantically covered the query — but because its aliases were `guia_practica_procedimiento_tributario_dian`, `fiscalizacion_y_recursos_tributarios`, `codigo_de_procedimiento_administrativo`. Those are slugified **document titles**, not words an accountant would ever type into a chat.

### Why it's general

This isn't a `procedimiento_tributario`-specific curation oversight. Spot-check the taxonomy:

- `devoluciones_y_compensaciones_de_saldos_a_favor.aliases` = `["compensacion_y_devoluciones_de_saldos_a_favor", "gestion_de_reteiva_y_saldos_a_favor", …]` — label reorderings of the key itself.
- `asistencia_administrativa_mutua_fiscal_internacional.aliases` = `["asistencia_administrativa_mutua_en_materia_fiscal"]` — one alias, same formal phrasing.
- `registro_unico_de_beneficiarios_finales.aliases` = `["marco_normativo_registro_unico_de_beneficiarios_finales"]` — prefix variant.

The curation pattern across the whole file is: take the document's formal title, slugify it, add two or three prefix variants. That produces aliases that match *corpus documents* but not *user queries*. Accountants don't type `guia_practica_procedimiento_tributario_dian`; they type `me llegó un requerimiento`, `tengo que contestar un pliego de cargos`, `me hicieron una liquidación oficial`.

### Where to intervene

1. **`config/subtopic_taxonomy.json` — every subtopic entry's `aliases` array.**
   The loader is `src/lia_graph/subtopic_taxonomy_loader.py`; `SubtopicEntry.all_surface_forms()` at lines 74-97 is what the classifier scans. Adding entries to `aliases` is the canonical extension point — the loader de-duplicates against `key` and `label`, so adding accountant-vernacular forms is safe and additive.

2. **A curator pass with this concrete question per subtopic:** *"What phrases would a working Colombian SMB accountant type to land on this subtopic?"* Examples of the vocabulary gap:

   | Subtopic key | Label-speak (current) | Query-speak (missing) |
   |---|---|---|
   | `simplificacion_tramites_administrativos_y_tributarios` | `guia_practica_procedimiento_tributario_dian` | `requerimiento`, `pliego_de_cargos`, `auto_de_archivo` (NOW ADDED by the narrow fix) |
   | `actualizacion_normativa_informacion_exogena` | `guia_practica_informacion_exogena` | `formato_1001`, `reportar_exogena`, `medios_magneticos` |
   | `agente_retenedor_bases_y_tarifas_de_retencion_en_la_fuente` | `tablas_y_calculo_de_retencion_en_la_fuente_2026` | `certificado_de_retencion`, `practicar_retencion`, `tarifa_minima_retencion` |
   | `implementacion_retencion_en_la_fuente_pyme` | `regulacion_de_retencion_en_la_fuente` | `exonerado_de_retencion`, `autorretenedor`, `base_minima_retencion` |

3. **Honor Invariant I1 (alias breadth).** The memory at `feedback_subtopic_aliases_breadth.md` is the explicit permission for this pass: *"wide alias lists in config/subtopic_taxonomy.json are intentional semantic-expansion fuel for retrieval; don't auto-tighten them."* Adding query-speak is the canonical breadth-expansion move — this pass is unblocked by policy.

4. **Where *not* to edit.** Do not touch `label`. Labels are the human-readable display string used by the admin UI at `ui/assets/subtopicShell-*.js` (the admin review path). Mutating labels will churn the UI and break curator recognition.

### Test gates

- Extend `tests/test_planner_subtopic_intent.py` with a query-speak fixture: a dict of `{user_query_string: expected_subtopic_key}` grown from the 106-entry taxonomy. The fixture doubles as a curator-facing spec of what *should* route where.
- `tests/test_phase3_graph_planner_retrieval.py` has end-to-end smoke tests that call `run_pipeline_d(request)` — extend with a subtopic-diagnostic assertion for a curated set of queries.

### Effort / risk

**L**. The work is per-subtopic curator judgment; 106 entries × ~10 aliases to add per entry ≈ ~1000 aliases. Cannot be automated safely — an LLM pass would re-introduce the label-speak bias unless prompted carefully. Best shape is a curator UI workflow (or a spreadsheet) that walks each subtopic, shows its current aliases + 3-5 candidate accountant phrases mined from real chat logs, and accepts/rejects. The win is recall across every future query — this is the single highest-leverage item in this backlog.

---

## C. 40+ top-level topics with zero registered keywords

### Symptom

Running a keyword-registration census:

```python
from lia_graph.topic_guardrails import get_supported_topics
from lia_graph.topic_router_keywords import _TOPIC_KEYWORDS
empty = [t for t in get_supported_topics()
         if not (_TOPIC_KEYWORDS.get(t, {}).get("strong") or
                 _TOPIC_KEYWORDS.get(t, {}).get("weak"))]
# len(empty) == 40+
```

Of ~50 supported top-level topics, only ~8 have manually curated keyword entries (`laboral`, `declaracion_renta`, `iva`, `ica`, `facturacion_electronica`, `estados_financieros_niif`, `calendario_obligaciones`, `procedimiento_tributario`). The other 40+ either have to be populated dynamically via `_bootstrap_custom_corpora()` in `topic_router.py:71-179` (which reads `config/corpora_custom.json`) or they simply never route.

### Why it's general

Every query about an unregistered topic is silently vulnerable. Some examples of topics with zero hardcoded keywords:

- `anticipos_retenciones_a_favor` — queries about anticipos de renta, retenciones a favor
- `beneficiario_final_rub` — RUB / beneficiario final
- `comercial_societario` — sociedades, reforma estatutaria, liquidación de sociedades (!)
- `contratacion_estatal` — SECOP, contratos estatales
- `economia_digital_criptoactivos` — criptoactivos, economía digital
- `ganancia_ocasional` — ganancia ocasional (one of the four renta sub-impuestos)
- `informacion_exogena` — exógena (despite being a core accountant workflow!)
- `precios_de_transferencia` — operaciones entre vinculados
- `regimen_simple` — Régimen Simple
- `retencion_en_la_fuente` — retención en la fuente (despite being a daily workflow)
- `sagrilaft_ptee` — SAGRILAFT, PTEE
- `zonas_francas` — zonas francas

A query like *"¿Cómo reporto la exógena 2025?"* has no `informacion_exogena` strong/weak entries to score against; it will either fall through to `None` or be hijacked by whatever weak term happens to match on an adjacent topic.

### Where to intervene

1. **Decide the intended sourcing per unregistered topic.** The bootstrap at `topic_router.py:71-179` is the escape hatch: a custom corpus declared in `config/corpora_custom.json` with a `keywords: {strong: […], weak: […]}` block auto-registers at import time via `register_topic_keywords` (`topic_router.py:56-68`). So there are two legitimate states for a topic to be in:
   - (a) **Static registration in `_TOPIC_KEYWORDS`** — for topics that are load-bearing enough to belong in code.
   - (b) **Dynamic registration via `corpora_custom.json`** — for topics owned by a specific corpus configuration.

   Everything currently sitting at 0/0 is in neither state. The first task is a diagnostic: for each unregistered topic, classify it as (a)-candidate, (b)-candidate, or "not actually a top-level concern (should be a subtopic under another parent)".

2. **Add a boot-time invariant check.** In `topic_router.py`, after `_bootstrap_custom_corpora()` runs (currently line 182), emit a warning log for every entry in `get_supported_topics()` with zero keywords. Right now a 0/0 topic is silently broken; the invariant would surface it the first time the process starts. One-line addition:

   ```python
   for topic in get_supported_topics():
       kw = _TOPIC_KEYWORDS.get(topic, {})
       if not (kw.get("strong") or kw.get("weak")):
           logger.warning("topic_router: topic %r has no registered keywords", topic)
   ```

3. **Populate the (a) bucket.** For topics that must route without depending on a custom-corpus config (common SMB-accountant workflows: `retencion_en_la_fuente`, `informacion_exogena`, `ganancia_ocasional`, `regimen_simple`), add entries directly in `_TOPIC_KEYWORDS`. These are daily-traffic topics; losing them to a config-file oversight is a production hazard.

4. **Subtopic vs. top-level disambiguation.** Some of the 40+ may actually be misplaced — they're subtopics masquerading as top-level topics. `gravamen_movimiento_financiero_4x1000` is an interesting case: it's registered as a top-level topic with 0 keywords, but `_SUBTOPIC_OVERRIDE_PATTERNS` (topic_router_keywords.py:577-588) already owns the routing for GMF queries via regex. Check whether the top-level registration is still load-bearing or whether it's dead weight since the override supersedes it.

### Test gates

- `tests/test_topic_router_keywords.py` — add a parameterized test that asserts every topic in `get_supported_topics()` has at least one keyword after `_bootstrap_custom_corpora()` runs. Fails loudly if a new topic gets registered without keywords.
- Smoke tests for each newly populated (a)-bucket topic: 3-5 representative queries per topic, asserting correct routing.

### Effort / risk

**M**. Classification is quick (1 hour). Populating the (a) bucket is a few hours per topic for ~10 topics. Risk is low — adding keywords can only *add* routing precision, not subtract it (barring accidental cross-topic pollution, caught by A's adversarial tests).

---

## D. Single-intent subtopic classifier caps multi-question queries

### Symptom

`_detect_sub_topic_intent` (src/lia_graph/pipeline_d/planner_query_modes.py:58-111) returns `str | None` — one winning subtopic or nothing. The winner is chosen by greedy longest-alias-match, tiebroken lexicographically on the key (line 95: `matches.sort(key=lambda item: (-item[0], item[1]))`).

This is a latent cap for multi-facet queries. The original triggering query had three sub-questions that landed across different subtopic facets — `plazos` (procedural deadlines), `pruebas` (derecho probatorio), `ruta procesal` (sequence of DIAN actos administrativos). Even after the narrow fix made `simplificacion_tramites_administrativos_y_tributarios` win, the Supabase boost (`filter_subtopic` at `retriever_supabase.py:165-167`) and the Falkor anchor probe (`_retrieve_subtopic_bound_article_keys` at `retriever_falkor.py:66-70`) both steer retrieval toward **one** subtopic. Sub-questions that would benefit from evidence under a sibling subtopic (e.g. `regimen_sancionatorio` for Q2's pruebas admisibles) get starved.

### Why it's general

Multi-question queries aren't rare — they're the standard shape of an accountant prompt. Every `¿…? ¿…? ¿…?` turn will face this cap as soon as the sub-questions span more than one subtopic. The memory at `feedback_multiquestion_answer_shape.md` explicitly commits to "one visible block per `¿…?` with unrestricted multi-bullets inside" — meaning the product promise is that each sub-question gets its own evidence-backed answer. The single-intent classifier breaks that promise structurally, not accidentally.

### Where to intervene

This is the biggest design change in this backlog — it touches the planner contract, both retrievers, the diagnostics schema, and tests. Trace:

1. **Contract change — `src/lia_graph/pipeline_d/contracts.py:107`**
   ```python
   sub_topic_intent: str | None = None
   # becomes
   sub_topic_intents: tuple[str, ...] = ()
   ```
   And at `contracts.py:119`, the `to_dict` emits a list.

2. **Classifier change — `src/lia_graph/pipeline_d/planner_query_modes.py:58-111`**
   Return type becomes `tuple[str, ...]`. The greedy single-winner block (lines 83-111) becomes: for each sub-question emitted by `_extract_user_sub_questions` (already called in planner.py:423), run the same alias scan; union the top-1 result per sub-question. Final return is the de-duplicated tuple. Fall back to the single-winner behavior when there's only one sub-question.

3. **Call site — `src/lia_graph/pipeline_d/planner.py:425-442`**
   Pass `sub_questions` (already available at line 423) into `_detect_intent`. Update the `GraphRetrievalPlan` construction at line 442.

4. **Falkor retriever — `src/lia_graph/pipeline_d/retriever_falkor.py:63-131`**
   Replace single-key probe at lines 66-70 with a loop that unions `_retrieve_subtopic_bound_article_keys` across all intents. Preserve `primary_article_limit` by dividing the budget evenly across intents (floor 1). Rename diagnostic field at line 130 from `retrieval_sub_topic_intent` to `retrieval_sub_topic_intents` (list).

5. **Supabase retriever — `src/lia_graph/pipeline_d/retriever_supabase.py:88, 148-187`**
   The RPC accepts a single `filter_subtopic` today. Either (a) extend the RPC server-side to accept `filter_subtopics` (list) + `subtopic_boosts` (list-parallel floats), or (b) run the RPC N times and union results client-side. (b) is the cheaper landing — no DB migration, retries still work. `_apply_client_side_subtopic_boost` at lines 206-249 already handles post-sort boosting; extend it to check `subtema in sub_topic_intents` instead of scalar equality.

6. **Diagnostics propagation.** `response.diagnostics["retrieval_sub_topic_intent"]` is the contract the `chat-response-architecture.md` guide documents (line 64). Bump to plural everywhere, update `docs/guide/orchestration.md` at the env-matrix version row (currently `v2026-04-21-stv2d` — bump to `-stv3`), and document the field rename in the change log section.

7. **Tests.** `tests/test_planner_subtopic_intent.py` currently asserts single-winner. Split into:
   - single-sub-question behavior (existing cases keep passing, `intents` is 1-tuple)
   - multi-sub-question behavior (new cases: a tri-facet query should emit three subtopic keys in `intents`, covering each facet)
   - end-to-end in `tests/test_phase3_graph_planner_retrieval.py`: assert that Q2 of a multi-facet query gets evidence from its own subtopic, not from the dominant Q1 subtopic's pool.

### Test gates

See the three test splits in (7) above. Also: a regression test that a single-sub-question turn still emits exactly one intent (no accidental multi-fan-out).

### Effort / risk

**M-to-L**. Mechanics are clear (contract + two retrievers + diagnostics rename + tests), but the change crosses module boundaries. Risk: extending Supabase to N RPC calls multiplies request count when the query is tri-facet — if latency matters, extend the RPC server-side instead (option (a) above). Do A, B, and C first: they fix the *data* so multi-intent has something to be intelligent over. Multi-intent on top of a thin alias set just fans out the same miss across more queries.

---

## E. No standalone CLI for tracing a query through the pipeline

### Symptom

Every time we debug routing, we reconstruct it by ad-hoc Python against `resolve_chat_topic` + `_detect_sub_topic_intent`, like:

```python
from lia_graph.topic_router import resolve_chat_topic, _score_topic_keywords
from lia_graph.pipeline_d.planner_query_modes import _detect_sub_topic_intent
query = "..."
routing = resolve_chat_topic(message=query, requested_topic=None)
print(routing.effective_topic, routing.confidence, routing.reason)
print(_score_topic_keywords(query))
print(_detect_sub_topic_intent(query, routing.effective_topic))
```

There's no committed tool for this. Every investigation reinvents it. The test suite at `tests/test_phase3_graph_planner_retrieval.py` comes closest but requires writing a test to probe one query.

### Why it's general

Tooling absence compounds. Every time any of items A-D comes back (during adversarial testing, during a regression, during future curation work), the investigator has to recompose the same 10 lines. The shape of the investigation is: *given a query string, emit the full planner/retriever diagnostic trace as JSON*. That's a 30-line script.

### Where to intervene

New file: `scripts/debug_query.py`. Existing `scripts/` convention (sibling to `scripts/backfill_subtopic.py`, `scripts/mine_subtopic_candidates.py`, etc.) is standalone Python scripts with argparse. Target shape:

```python
# scripts/debug_query.py
"""Run a query through the live planner + subtopic classifier and print
a diagnostic JSON trace. Does not hit Supabase or Falkor — lexical layers only,
so it runs in dev without env config.

Usage:
  python scripts/debug_query.py "La DIAN le envió un requerimiento..."
  python scripts/debug_query.py --topic renta "..."     # pin requested_topic
  python scripts/debug_query.py --full "..."            # include full plan.to_dict()
"""
```

Wire (in order):
1. `lia_graph.topic_router.resolve_chat_topic(message=q, requested_topic=...)` → top-level topic + score breakdown via `_score_topic_keywords`
2. `lia_graph.topic_router._check_subtopic_overrides(q)` → which override pattern fired, if any
3. `lia_graph.pipeline_d.planner_query_modes._detect_sub_topic_intent(q, topic)` → subtopic intent + match form
4. `lia_graph.pipeline_d.planner.build_graph_retrieval_plan(request)` → full plan, including entry points and sub-questions (optional, behind `--full`)
5. `lia_graph.pipeline_d.planner._extract_user_sub_questions(q)` → the `¿…?` splits

Output is a single JSON object. No retrieval, no LLM — so it's safe to run unconditionally.

**Add a Makefile target.** The repo has a Makefile with existing targets like `make phase2-graph-artifacts-supabase`. Add:
```makefile
debug-query:
	@test -n "$(Q)" || (echo "Usage: make debug-query Q='your query here'"; exit 1)
	.venv/bin/python scripts/debug_query.py "$(Q)"
```
So investigation becomes `make debug-query Q="..."`.

### Test gates

- `tests/test_debug_query_cli.py` — one test: run the script on a known query via `subprocess`, parse the JSON, assert the expected topic + subtopic. Prevents the script from silently bit-rotting.

### Effort / risk

**S**. One file, one afternoon. Risk is effectively zero. The only thing to watch is not accidentally importing a module that requires env config (Supabase client, LLM adapter) — the lexical layers don't, and the script must not grow to include retrieval without a `--live` flag that errors clearly when env is missing.

---

## Recommended order

The order below assumes you care about *recall impact per unit of effort*, not chronological convenience.

1. **E (tooling)** — S effort, S risk, unlocks faster iteration on everything else. Do this first unconditionally.
2. **A (weak-list polysemy audit)** — M effort. Mostly mechanical once the rule is named and adversarial tests exist. Fixes a whole class of silent mis-routings.
3. **B (query-speak alias pass)** — L effort, but highest single recall win. Cannot be skipped even if D is done, because D multiplies misses when the alias data is thin.
4. **C (empty top-level topics)** — M effort. Independent of A/B; do in parallel with either if hands are available. Adds the boot-time invariant log as a one-liner so future regressions surface immediately.
5. **D (multi-intent classifier)** — M-to-L effort. **Do last.** Multi-intent on top of thin data (pre-A/B/C) just fans out the same data gaps across more queries. After A/B/C land, the data is rich enough that multi-intent becomes genuinely additive.

---

## Change log

| Version | Date | Notes |
|---|---|---|
| v1 | 2026-04-21 | Initial catalog. Written after the `requerimiento ordinario` / `liquidación` investigation that landed narrow fixes in `topic_router_keywords.py` and `subtopic_taxonomy.json`. |
