# Structural Work — v1 (SEE NOW)

**Context.** Written after investigating two recurring failure modes surfaced by two multi-question accountant queries:

1. A DIAN audit-procedure query (`"requerimiento ordinario... ¿términos? ¿pruebas? ¿ruta procesal?"`) where Q1 got `Cobertura pendiente` because the top-level router mis-routed to `laboral` (via bare-polysemous `liquidación` weak keyword), and because the entire 106-entry subtopic taxonomy had zero alias coverage for the procedural-audit vocabulary.
2. A documento-soporte-de-pago query (`"¿requisitos DSE? ¿resoluciones DIAN y info mínima?"`) where Q1 got a full answer but Q2 got `Cobertura pendiente` because Q2's vocabulary (`resoluciones DIAN regulan expedición electrónica información mínima`) scored 0 against every topic's keywords, hit 0 aliases across the taxonomy, and described a facet the taxonomy has no subtopic entry for at all — compounded by the query being cross-topic (Q1 costos_deducciones, Q2 facturacion_electronica), which the single-topic planner doesn't fan out.

The narrow fixes for investigation (1) landed — `src/lia_graph/topic_router_keywords.py` got `procedimiento_tributario` audit-procedure vocabulary + had polysemous bare `liquidación` entries removed from `laboral.weak`; `config/subtopic_taxonomy.json` got audit-procedure aliases on `simplificacion_tramites_administrativos_y_tributarios`. Investigation (2) got no narrow fix — its root causes are all in this document.

This file catalogs the **general** weaknesses those single-point fixes only papered over. Each item is a data or design pattern that will keep biting new queries until it's addressed at the pattern level. Items are split into **easier fixes** (Part 1 — S-to-M effort, mostly data/tooling, low architectural risk) and **complex fixes** (Part 2 — L effort or crosses module contracts / taxonomy curation scope).

**Scope note.** This is a structural backlog, not a refactor plan with batches. Each item is independently actionable. Effort estimates are coarse (S = under a day, M = a day to a week, L = multi-week).

**Non-goals.** Not re-opening the `main chat` → `Normativa` / `Interpretación` split. Not changing the retriever contract (hybrid_search RPC stays, Falkor Cypher stays). Not touching answer-synthesis / assembly — those are downstream of everything here.

---

# Part 1 — Easier fixes

These are additive, low-risk, and unblock or amplify the harder work in Part 2. Do them first.

## E. No standalone CLI for tracing a query through the pipeline

### Symptom

Every time we debug routing, we reconstruct the trace by ad-hoc Python against `resolve_chat_topic` + `_detect_sub_topic_intent`:

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
a diagnostic JSON trace. Does not hit Supabase or Falkor — lexical layers
only, so it runs in dev without env config.

Usage:
  python scripts/debug_query.py "La DIAN le envió un requerimiento..."
  python scripts/debug_query.py --topic renta "..."     # pin requested_topic
  python scripts/debug_query.py --full "..."            # include full plan.to_dict()
  python scripts/debug_query.py --per-sub-question "..." # run each ¿…? separately
"""
```

Wire (in order):
1. `lia_graph.topic_router.resolve_chat_topic(message=q, requested_topic=...)` → top-level topic + score breakdown via `_score_topic_keywords`
2. `lia_graph.topic_router._check_subtopic_overrides(q)` → which override pattern fired, if any
3. `lia_graph.pipeline_d.planner_query_modes._detect_sub_topic_intent(q, topic)` → subtopic intent + match form
4. `lia_graph.pipeline_d.planner.build_graph_retrieval_plan(request)` → full plan, including entry points and sub-questions (optional, behind `--full`)
5. `lia_graph.pipeline_d.planner._extract_user_sub_questions(q)` → the `¿…?` splits — when `--per-sub-question` is set, repeat steps 1-3 for each split

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

The second investigation exposed a narrower variant of this: `facturacion_electronica` IS populated with 24 strong + 28 weak keywords, but they all describe *what facturación is* (DSE, CUFE, RADIAN, factura de venta). They don't describe *which regulatory instruments govern it* (resoluciones DIAN, información mínima, expedición). Q2 `"¿Qué resoluciones DIAN regulan su expedición electrónica y qué información mínima debe contener?"` scored 0 on `facturacion_electronica` and fell through to `None`. So "zero keywords" isn't the only failure mode — "incomplete keyword facets" is a subtler one that hits populated topics too.

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

4. **Audit the *incomplete* side too.** The populated topics (`facturacion_electronica`, `laboral`, `declaracion_renta`, `iva`, etc.) each need a facet review: for the question *"does this topic's keyword set cover every face of the domain an accountant asks about?"*. Concrete procedure: sample 20 real queries per topic from `logs/chat_verbose.jsonl`, run them through `_score_topic_keywords`, flag any that score 0 despite being unambiguously on-topic. Each flag is a facet gap to fill.

5. **Subtopic vs. top-level disambiguation.** Some of the 40+ may actually be misplaced — they're subtopics masquerading as top-level topics. `gravamen_movimiento_financiero_4x1000` is an interesting case: it's registered as a top-level topic with 0 keywords, but `_SUBTOPIC_OVERRIDE_PATTERNS` (topic_router_keywords.py:577-588) already owns the routing for GMF queries via regex. Check whether the top-level registration is still load-bearing or whether it's dead weight since the override supersedes it.

### Test gates

- `tests/test_topic_router_keywords.py` — add a parameterized test that asserts every topic in `get_supported_topics()` has at least one keyword after `_bootstrap_custom_corpora()` runs. Fails loudly if a new topic gets registered without keywords.
- Smoke tests for each newly populated (a)-bucket topic: 3-5 representative queries per topic, asserting correct routing.

### Effort / risk

**M**. Classification is quick (1 hour). Populating the (a) bucket is a few hours per topic for ~10 topics. The facet-completeness audit (step 4) is the slower part — needs real query logs and per-topic judgment, but it's per-topic-parallel and a junior contributor can drive it once the procedure is written. Risk is low — adding keywords can only *add* routing precision, not subtract it (barring accidental cross-topic pollution, caught by A's adversarial tests).

---

## A. Polysemous bare weak keywords (the "liquidación" anti-pattern)

### Symptom

Query `"¿Cuál es la ruta procesal si escala a requerimiento especial y luego a liquidación oficial?"` routed to `laboral` with confidence 0.3 because `_TOPIC_KEYWORDS["laboral"]["weak"]` contained bare `liquidar` / `liquidacion` / `liquidación` — each of which also means *contract liquidation*, *company dissolution*, *tax self-assessment*, and *DIAN audit liquidation*. The first weak hit, on any topic, wins the keyword scorer when no stronger signal is present. A single polysemous bare term is enough to hijack a whole subdomain of queries.

### Why it's general

The same anti-pattern lives, right now, for these bare entries still in `_TOPIC_KEYWORDS["laboral"]["weak"]` (src/lia_graph/topic_router_keywords.py:96-150):

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

# Part 2 — Complex fixes

These cross taxonomy curation scope or module contracts. Don't start them before Part 1 lands — the tooling (E) makes this work tractable, and the data fixes (A + C) close enough silent-misses that the returns on B and D become measurable.

## B. Taxonomy alias + coverage gap (label-speak vs query-speak)

### Symptom

`_detect_sub_topic_intent` (src/lia_graph/pipeline_d/planner_query_modes.py:58-111) scanned the entire 106-entry taxonomy for the DIAN-audit query and returned **zero** alias hits. Not one. Not because the subtopic wasn't there — `procedimiento_tributario.simplificacion_tramites_administrativos_y_tributarios` existed and semantically covered the query — but because its aliases were `guia_practica_procedimiento_tributario_dian`, `fiscalizacion_y_recursos_tributarios`, `codigo_de_procedimiento_administrativo`. Those are slugified **document titles**, not words an accountant would ever type into a chat.

The second investigation revealed a harder variant: for the query *"¿Qué resoluciones DIAN regulan su expedición electrónica y qué información mínima debe contener?"* there is no matching entry anywhere in the taxonomy. It isn't that the aliases are wrong — it's that no subtopic exists for "which regulatory instruments govern this + minimum-info requirements". This is a **taxonomy coverage** gap, not just an alias-style gap.

### Why it's general — two compounding sub-gaps

This isn't a single-subtopic curation oversight. Two distinct, compounding patterns:

**Sub-gap B1 — alias style (label-speak vs query-speak).** Spot-check the taxonomy:

- `devoluciones_y_compensaciones_de_saldos_a_favor.aliases` = `["compensacion_y_devoluciones_de_saldos_a_favor", "gestion_de_reteiva_y_saldos_a_favor", …]` — label reorderings of the key itself.
- `asistencia_administrativa_mutua_fiscal_internacional.aliases` = `["asistencia_administrativa_mutua_en_materia_fiscal"]` — one alias, same formal phrasing.
- `registro_unico_de_beneficiarios_finales.aliases` = `["marco_normativo_registro_unico_de_beneficiarios_finales"]` — prefix variant.

The curation pattern across the whole file is: take the document's formal title, slugify it, add two or three prefix variants. That produces aliases that match *corpus documents* but not *user queries*. Accountants don't type `guia_practica_procedimiento_tributario_dian`; they type `me llegó un requerimiento`, `tengo que contestar un pliego de cargos`, `me hicieron una liquidación oficial`.

**Sub-gap B2 — taxonomy coverage (from-corpus-forward vs from-queries-backward).** Even after B1 is fixed, facets without any subtopic entry remain unreachable. The Q2 in investigation (2) is the canonical example — `facturacion_electronica` has 4 subtopics (`factura_como_titulo_valor`, `reforma_tributaria_2003`, `cronograma_documentos_electronicos_dian`, `impuesto_de_timbre_y_papel_sellado`), none of which covers "which DIAN resolutions regulate DSE expedition and what minimum info they require". The taxonomy was built from the existing corpus forward — subtopics exist where documents exist — so any facet the corpus doesn't cover is also absent from the taxonomy. Queries asking about those facets hit 0 aliases no matter how rich the alias lists get.

### Where to intervene

1. **Sub-gap B1 fix — `config/subtopic_taxonomy.json`, every subtopic's `aliases` array.**
   The loader is `src/lia_graph/subtopic_taxonomy_loader.py`; `SubtopicEntry.all_surface_forms()` at lines 74-97 is what the classifier scans. Adding entries to `aliases` is the canonical extension point — the loader de-duplicates against `key` and `label`, so adding accountant-vernacular forms is safe and additive.

2. **A curator pass with this concrete question per subtopic:** *"What phrases would a working Colombian SMB accountant type to land on this subtopic?"* Examples of the vocabulary gap:

   | Subtopic key | Label-speak (current) | Query-speak (missing) |
   |---|---|---|
   | `simplificacion_tramites_administrativos_y_tributarios` | `guia_practica_procedimiento_tributario_dian` | `requerimiento`, `pliego_de_cargos`, `auto_de_archivo` (NOW ADDED by the narrow fix) |
   | `actualizacion_normativa_informacion_exogena` | `guia_practica_informacion_exogena` | `formato_1001`, `reportar_exogena`, `medios_magneticos` |
   | `agente_retenedor_bases_y_tarifas_de_retencion_en_la_fuente` | `tablas_y_calculo_de_retencion_en_la_fuente_2026` | `certificado_de_retencion`, `practicar_retencion`, `tarifa_minima_retencion` |
   | `implementacion_retencion_en_la_fuente_pyme` | `regulacion_de_retencion_en_la_fuente` | `exonerado_de_retencion`, `autorretenedor`, `base_minima_retencion` |

3. **Honor Invariant I1 (alias breadth).** The memory at `feedback_subtopic_aliases_breadth.md` is the explicit permission for this pass: *"wide alias lists in config/subtopic_taxonomy.json are intentional semantic-expansion fuel for retrieval; don't auto-tighten them."* Adding query-speak is the canonical breadth-expansion move — this pass is unblocked by policy.

4. **Sub-gap B2 fix — curator workflow addition.** The existing curation procedure (see `docs/next/subtopic_generationv1.md`) starts from the corpus. Add a reverse pass that starts from real queries. Concrete shape:

   - Sample N=100-200 queries from `logs/chat_verbose.jsonl` across the last quarter.
   - For each query, run it through `scripts/debug_query.py` (from item E) and flag any that produce `sub_topic_intent=None` despite having clear domain intent.
   - Group the flagged queries by domain/facet. Each cluster where no existing subtopic semantically covers the facet is a **new-subtopic candidate** — not an alias addition.
   - Feed those candidates into the existing curator-decisions workflow (`scripts/promote_subtopic_decisions.py`).

5. **Where *not* to edit.** Do not touch `label`. Labels are the human-readable display string used by the admin UI at `ui/assets/subtopicShell-*.js` (the admin review path). Mutating labels will churn the UI and break curator recognition.

### Test gates

- Extend `tests/test_planner_subtopic_intent.py` with a query-speak fixture: a dict of `{user_query_string: expected_subtopic_key}` grown from the 106-entry taxonomy. The fixture doubles as a curator-facing spec of what *should* route where.
- For B2: a separate fixture of known-uncovered queries with `expected_subtopic_key: None` — flipping any of these to a non-None value means a new subtopic has landed, and the test should force-update rather than silently pass.
- `tests/test_phase3_graph_planner_retrieval.py` has end-to-end smoke tests that call `run_pipeline_d(request)` — extend with a subtopic-diagnostic assertion for a curated set of queries.

### Effort / risk

**L**. Sub-gap B1 is per-subtopic curator judgment; 106 entries × ~10 aliases to add per entry ≈ ~1000 aliases. Cannot be automated safely — an LLM pass would re-introduce the label-speak bias unless prompted carefully. Sub-gap B2 requires real query logs and adds net-new taxonomy entries, which also adds corpus curation work (each new subtopic needs documents tagged to it to be useful). Best shape is a curator UI workflow that walks each subtopic, shows its current aliases + 3-5 candidate accountant phrases mined from real chat logs, and accepts/rejects — and surfaces uncovered-facet queries in a separate "propose new subtopic" queue. The win is recall across every future query — this is the single highest-leverage item in this backlog.

---

## D. Single-intent classifier + single-topic retrieval scope

### Symptom

`_detect_sub_topic_intent` (src/lia_graph/pipeline_d/planner_query_modes.py:58-111) returns `str | None` — one winning subtopic or nothing. The winner is chosen by greedy longest-alias-match, tiebroken lexicographically on the key (line 95: `matches.sort(key=lambda item: (-item[0], item[1]))`).

This is a latent cap for multi-facet queries. The original triggering query had three sub-questions that landed across different subtopic facets — `plazos` (procedural deadlines), `pruebas` (derecho probatorio), `ruta procesal` (sequence of DIAN actos administrativos). Even after the narrow fix made `simplificacion_tramites_administrativos_y_tributarios` win, the Supabase boost (`filter_subtopic` at `retriever_supabase.py:165-167`) and the Falkor anchor probe (`_retrieve_subtopic_bound_article_keys` at `retriever_falkor.py:66-70`) both steer retrieval toward **one** subtopic. Sub-questions that would benefit from evidence under a sibling subtopic (e.g. `regimen_sancionatorio` for Q2's pruebas admisibles) get starved.

The second investigation exposed a harder variant: Q1 belongs to `costos_deducciones_renta`, Q2 to `facturacion_electronica`. `resolve_chat_topic(whole_query)` picks one `effective_topic` (`costos_deducciones_renta`, via the subtopic override regex) and retrieval is scoped to it. Q2's evidence lives in a *different top-level topic's corpus*, which is never traversed. Multi-intent at subtopic level doesn't fix cross-topic sub-questions — the scope is wrong one level higher.

### Why it's general — two distinct sub-caps

Multi-question queries aren't rare — they're the standard shape of an accountant prompt. Every `¿…? ¿…? ¿…?` turn will face these caps as soon as the sub-questions span more than one subtopic (sub-cap D1) or more than one top-level topic (sub-cap D2). The memory at `feedback_multiquestion_answer_shape.md` explicitly commits to "one visible block per `¿…?` with unrestricted multi-bullets inside" — meaning the product promise is that each sub-question gets its own evidence-backed answer. The single-intent + single-topic stack breaks that promise structurally, not accidentally.

**Sub-cap D1 — single-intent subtopic classifier.** Within one top-level topic, the classifier emits one `sub_topic_intent`. Multi-facet sub-questions get starved.

**Sub-cap D2 — single-topic retrieval scope.** Across top-level topics, the planner emits one `effective_topic` that the retriever scopes to. Cross-topic sub-questions never see the other topic's corpus. `TopicRoutingResult` (src/lia_graph/topic_router.py:205-229) already has a `secondary_topics: tuple[str, ...]` field — it's populated by `_normalize_secondary_topics` (lines 242-262) and survives through to `to_dict`, but it's currently only used as a fallback hint for downstream display; it does not feed retrieval fan-out.

### Where to intervene

This is the biggest design change in this backlog — it touches the planner contract, both retrievers, the diagnostics schema, topic routing, and tests. Trace in two phases (D1 first, D2 second):

**Phase D1 — multi-intent subtopic classifier (within one topic).**

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

**Phase D2 — multi-topic retrieval scope (across topics).**

7. **Per-sub-question top-level topic classification — `src/lia_graph/pipeline_d/planner.py` (new seam).**
   Today the planner calls `resolve_chat_topic` once, on the whole message. Add a per-sub-question pass: for each `¿…?` split, run `resolve_chat_topic` again and collect distinct `effective_topic` values. Union them with the whole-query result. This catches the case where Q2 alone would have resolved to `facturacion_electronica` even though the whole query resolved to `costos_deducciones_renta`.

8. **Wire `secondary_topics` into retrieval scope.**
   `GraphRetrievalPlan.topic_hints` (contracts.py:102) already exists and flows to both retrievers. Instead of inventing a new field, extend the planner to merge per-sub-question topics into `topic_hints`. Then in `retriever_supabase.py:_build_query_text` (line 106-120), the topic hints are already included in the RPC query text — but more importantly, the classifier/anchor pipeline needs a *retrieval* hook, not just a query-text one. Add a `secondary_topic_probe` in `retriever_falkor.py` that runs a narrower anchor probe for each secondary topic, same shape as the subtopic anchor probe already does.

9. **Supabase scope.** `hybrid_search` RPC currently takes `filter_topic: None` (retriever_supabase.py:149) — the comment at lines 136-141 documents that topic is deliberately *not* a WHERE predicate. Don't change that. Instead: extend the caller to pass the full topic set (primary + secondaries) as additional `query_text` tokens, so FTS ranking surfaces chunks from secondary topics without excluding the primary.

10. **Diagnostics addition.** Add `retrieval_effective_topics: list[str]` alongside `retrieval_sub_topic_intents`, carrying primary + all secondaries. Observable failure mode: the list is length-1 → single-topic retrieval happened → expected for simple queries, flagged for investigation for multi-question ones.

### Test gates

- **D1:** split `tests/test_planner_subtopic_intent.py` into (a) single-sub-question behavior (existing cases keep passing, `intents` is 1-tuple), (b) multi-sub-question behavior (new cases: a tri-facet query should emit three subtopic keys in `intents`).
- **D2:** new test `tests/test_planner_cross_topic_routing.py` — fixture of queries where Q1 and Q2 belong to different top-level topics, assert `retrieval_effective_topics` has length ≥ 2.
- End-to-end in `tests/test_phase3_graph_planner_retrieval.py`: assert that Q2 of a multi-facet cross-topic query gets evidence from its own topic+subtopic, not from the dominant Q1 pool.

### Effort / risk

**L-to-XL**. D1 alone is M-to-L (contract + two retrievers + diagnostics rename + tests). D2 is the bigger change: per-sub-question topic classification is a new planner seam, secondary-topic retrieval fan-out touches both retrievers, and the Supabase RPC query-text path has subtle interactions with `_build_fts_or_query` (retriever_supabase.py:178-199) that need careful rework. Do A, B, and C first: they fix the *data* so multi-intent + multi-topic have something to be intelligent over. Multi-intent on top of thin alias sets just fans out the same misses across more queries.

---

# Recommended order

The order below assumes you care about *recall impact per unit of effort*, not chronological convenience.

**Part 1 — do first unconditionally.**

1. **E (tooling)** — S effort, S risk. Unlocks faster iteration on everything else.
2. **C (empty / incomplete topic keywords)** — M effort. Independent of A; the boot-time invariant log (step 2 of C) is a one-liner that surfaces future regressions automatically. The facet-completeness audit (step 4) depends on E being available.
3. **A (weak-list polysemy audit)** — M effort. Mostly mechanical once the rule is named and adversarial tests exist. Fixes a whole class of silent mis-routings.

**Part 2 — do after Part 1 has landed.**

4. **B (alias style + coverage)** — L effort. Highest single recall win. Sub-gap B1 (alias style) is faster and can start in parallel with B2 (coverage gap requires query-log mining and new subtopics). Cannot be skipped even if D is done — D multiplies misses when the alias data is thin.
5. **D (multi-intent classifier + multi-topic scope)** — L-to-XL effort. **Do last.** Phase D1 (multi-intent within a topic) first, Phase D2 (multi-topic fan-out across topics) second. Both phases amplify the data gains from A/B/C; neither rescues a query whose evidence was never curated in the first place.

---

## Change log

| Version | Date | Notes |
|---|---|---|
| v1 | 2026-04-21 | Initial catalog. Written after the `requerimiento ordinario` / `liquidación` investigation that landed narrow fixes in `topic_router_keywords.py` and `subtopic_taxonomy.json`. |
| v2 | 2026-04-21 | Restructured into Part 1 (easier fixes — E, C, A) and Part 2 (complex fixes — B, D). Folded in two sub-points from the `documento soporte de pago` investigation: B gained sub-gap B2 (taxonomy coverage — facets with no subtopic entry at all); D gained sub-cap D2 (single-topic retrieval scope — cross-topic multi-question queries never see secondary topics' corpora). C picked up the "incomplete-facet" variant from Q2 scoring 0 on `facturacion_electronica`. |
